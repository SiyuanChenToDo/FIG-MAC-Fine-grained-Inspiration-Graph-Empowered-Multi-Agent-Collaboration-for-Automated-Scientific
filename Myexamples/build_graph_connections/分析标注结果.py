"""
标注结果分析脚本
==================
功能：
1. 统计标注一致性（Kappa系数）
2. 对比LLM与人工标注的准确率
3. 生成分析报告
4. 识别困难样本和边界案例
"""

import json
import os
import glob
from typing import Dict, List, Tuple
from collections import Counter, defaultdict

import pandas as pd
import numpy as np

# =================================================================================
# 1. 数据加载
# =================================================================================
def find_latest_excel(pattern: str) -> str:
    files = [path for path in glob.glob(pattern) if not os.path.basename(path).startswith("~$")]
    if not files:
        return ""
    files.sort()
    return files[-1]


def read_annotation_excel(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name="标注数据")
    df.columns = [str(col).strip() for col in df.columns]

    # 修正可能存在的无命名列（通常是二次校验列）
    if "llm_secondary_classification" not in df.columns and len(df.columns) >= 10:
        secondary_candidates = [col for col in df.columns if col.startswith("Unnamed")]
        if len(secondary_candidates) >= 2:
            df = df.rename(columns={secondary_candidates[0]: "llm_secondary_classification",
                                    secondary_candidates[1]: "llm_secondary_reasoning"})
        elif len(secondary_candidates) == 1:
            df = df.rename(columns={secondary_candidates[0]: "llm_secondary_classification"})

    # 若存在其他未命名列包含标注结果，尝试识别为人工标注列
    human_col = "human_classification"
    unnamed_cols = [col for col in df.columns if col.startswith("Unnamed")]
    for col in unnamed_cols:
        col_values = df[col].astype(str).str.strip()
        if col_values.replace("", pd.NA).isna().all():
            continue
        if human_col not in df.columns or df[human_col].astype(str).str.strip().replace("", pd.NA).isna().all():
            df[human_col] = col_values
        df = df.drop(columns=[col])

    # 若未提供人工标注列，则回退到二次LLM结果
    if human_col not in df.columns:
        if "llm_secondary_classification" in df.columns:
            df[human_col] = df["llm_secondary_classification"].astype(str)
        else:
            df[human_col] = ""
    else:
        human_series = df[human_col].astype(str).str.strip()
        if human_series.replace("", pd.NA).isna().all() and "llm_secondary_classification" in df.columns:
            df[human_col] = df["llm_secondary_classification"].astype(str)

    df = df.fillna("")

    return df


def add_secondary_validation_column(sample: Dict) -> Dict:
    if "llm_secondary_validation" not in sample:
        secondary_cls = sample.get("llm_secondary_classification", "")
        secondary_reason = sample.get("llm_secondary_reasoning", "")
        if secondary_cls or secondary_reason:
            sample["llm_secondary_validation"] = {
                "secondary_classification": secondary_cls,
                "secondary_reasoning": secondary_reason
            }
    sample.pop("llm_secondary_classification", None)
    sample.pop("llm_secondary_reasoning", None)
    # 清理Excel可能出现的无命名列
    for key in list(sample.keys()):
        if key.startswith("Unnamed"):
            sample.pop(key, None)
    return sample


def load_annotation_files(data_dir: str) -> Dict:
    """从Excel文件加载标注数据"""

    annotator_names = ["博士生A", "博士生B", "博士生C"]
    annotator_suffix = {"博士生A": "A", "博士生B": "B", "博士生C": "C"}

    common_dfs: Dict[str, pd.DataFrame] = {}
    annotator_data: Dict[str, Dict] = {}

    for name in annotator_names:
        annotator_dir = os.path.join(data_dir, name)
        if not os.path.isdir(annotator_dir):
            print(f"⚠️ 未找到标注员目录: {annotator_dir}")
            continue

        common_path = find_latest_excel(os.path.join(annotator_dir, "共同校验数据_*.xls*"))
        independent_path = find_latest_excel(os.path.join(annotator_dir, "独立校验数据_*.xls*"))

        if not common_path:
            print(f"⚠️ 未找到{ name }的共同校验Excel文件")
            continue
        if not independent_path:
            print(f"⚠️ 未找到{ name }的独立校验Excel文件")
            continue

        common_df = read_annotation_excel(common_path)
        independent_df = read_annotation_excel(independent_path)

        if "human_classification" not in common_df.columns:
            print(f"⚠️ 文件{common_path}缺少human_classification列，已使用llm_secondary_classification代替")
            common_df["human_classification"] = common_df.get("llm_secondary_classification", "")
        if "human_classification" not in independent_df.columns:
            print(f"⚠️ 文件{independent_path}缺少human_classification列，已使用llm_secondary_classification代替")
            independent_df["human_classification"] = independent_df.get("llm_secondary_classification", "")

        common_dfs[name] = common_df

        independent_records = []
        independent_records = independent_df.to_dict(orient="records")
        processed_records = []
        for record in independent_records:
            processed = add_secondary_validation_column(record)
            processed_records.append(processed)

        annotator_data[name] = {
            "samples": processed_records,
            "source_file": independent_path
        }

    if not common_dfs:
        raise FileNotFoundError("未找到任何共同校验Excel文件")

    # 构造共同校验样本，包含初次LLM与人工（二次LLM）标注
    samples_by_id = {}
    for name, df in common_dfs.items():
        suffix = annotator_suffix.get(name, name)
        for record in df.to_dict(orient="records"):
            sample_id = record["sample_id"]
            if sample_id not in samples_by_id:
                base_record = add_secondary_validation_column({k: record.get(k, "") for k in record})
                samples_by_id[sample_id] = {
                    "sample_id": sample_id,
                    "paper_a_id": base_record.get("paper_a_id", ""),
                    "paper_a_abstract": base_record.get("paper_a_abstract", ""),
                    "paper_a_core_problem": base_record.get("paper_a_core_problem", ""),
                    "paper_b_id": base_record.get("paper_b_id", ""),
                    "solution_text": base_record.get("solution_text", ""),
                    "llm_classification": base_record.get("llm_classification", ""),
                    "llm_reasoning": base_record.get("llm_reasoning", ""),
                    "llm_secondary_validation": base_record.get("llm_secondary_validation", {}),
                }
            samples_by_id[sample_id][f"human_classification_{suffix}"] = record.get("human_classification", "")

    # 补齐缺失的人工标注列
    for sample in samples_by_id.values():
        for name, suffix in annotator_suffix.items():
            column_name = f"human_classification_{suffix}"
            if column_name not in sample:
                sample[column_name] = ""

    common_data = {
        "samples": list(samples_by_id.values()),
        "source_files": {name: find_latest_excel(os.path.join(data_dir, name, "共同校验数据_*.xls*")) for name in common_dfs}
    }

    return {
        "common": common_data,
        "annotators": annotator_data
    }

# =================================================================================
# 2. 一致性分析
# =================================================================================
def calculate_fleiss_kappa(annotations: List[List[str]]) -> float:
    """
    计算Fleiss' Kappa（多标注员一致性）
    
    Args:
        annotations: [[标注员1结果, 标注员2结果, 标注员3结果], ...]
    
    Returns:
        Kappa值 (-1到1，越高越好)
    """
    n_items = len(annotations)  # 样本数
    n_raters = len(annotations[0])  # 标注员数
    
    # 统计类别
    all_categories = set()
    for item_annotations in annotations:
        all_categories.update(item_annotations)
    categories = sorted(list(all_categories))
    n_categories = len(categories)
    
    # 构建评分矩阵
    category_to_idx = {cat: i for i, cat in enumerate(categories)}
    matrix = np.zeros((n_items, n_categories))
    
    for i, item_annotations in enumerate(annotations):
        for annotation in item_annotations:
            if annotation:  # 忽略空标注
                matrix[i, category_to_idx[annotation]] += 1
    
    # 计算P_i（每个样本的一致性）
    P_i = []
    for i in range(n_items):
        sum_n_ij_squared = np.sum(matrix[i] ** 2)
        P_i.append((sum_n_ij_squared - n_raters) / (n_raters * (n_raters - 1)))
    
    P_bar = np.mean(P_i)  # 平均一致性
    
    # 计算P_j（每个类别的边际概率）
    P_j = []
    for j in range(n_categories):
        P_j.append(np.sum(matrix[:, j]) / (n_items * n_raters))
    
    P_e_bar = np.sum(np.array(P_j) ** 2)  # 期望一致性
    
    # 计算Kappa
    if P_e_bar == 1:
        return 1.0
    kappa = (P_bar - P_e_bar) / (1 - P_e_bar)
    
    return kappa

def calculate_pairwise_agreement(annotations: List[List[str]]) -> Dict:
    """计算两两标注员之间的一致率"""
    n_raters = len(annotations[0])
    agreements = {}
    
    for i in range(n_raters):
        for j in range(i + 1, n_raters):
            pair_name = f"标注员{i+1} vs 标注员{j+1}"
            agree_count = 0
            total_count = 0
            
            for item_annotations in annotations:
                if item_annotations[i] and item_annotations[j]:  # 都有标注
                    total_count += 1
                    if item_annotations[i] == item_annotations[j]:
                        agree_count += 1
            
            agreement = agree_count / total_count if total_count > 0 else 0
            agreements[pair_name] = {
                "agreement": agreement,
                "agree_count": agree_count,
                "total_count": total_count
            }
    
    return agreements

def analyze_common_annotations(common_data: Dict) -> Dict:
    """分析共同校验数据的一致性并统计LLM与多数票一致情况"""
    samples = common_data["samples"]

    annotations: List[List[str]] = []
    majority_labels: List[str] = []
    primary_labels: List[str] = []
    sample_ids: List[str] = []
    llm_vs_majority_match = 0
    samples_with_majority = 0
    samples_without_majority = 0
    samples_missing_votes = 0

    for sample in samples:
        votes = [
            sample.get("human_classification_A", ""),
            sample.get("human_classification_B", ""),
            sample.get("human_classification_C", "")
        ]

        valid_votes = [v for v in votes if v]

        if len(valid_votes) < 3:
            samples_missing_votes += 1
            continue

        annotations.append(votes)
        sample_ids.append(sample.get("sample_id", ""))

        llm_cls = sample.get("llm_classification", "")
        primary_labels.append(llm_cls)

        vote_counter = Counter(valid_votes)
        if not vote_counter:
            majority = ""
        else:
            most_common = vote_counter.most_common()
            if len(most_common) > 1 and most_common[0][1] == most_common[1][1]:
                majority = ""
            else:
                majority = most_common[0][0]
        majority_labels.append(majority)

        if majority:
            samples_with_majority += 1
            if llm_cls and llm_cls == majority:
                llm_vs_majority_match += 1
        else:
            samples_without_majority += 1

    if not annotations:
        return {"error": "没有找到任何标注数据"}

    kappa = calculate_fleiss_kappa(annotations)
    pairwise_agreements = calculate_pairwise_agreement(annotations)

    full_agreement_count = 0
    for votes in annotations:
        non_empty = [v for v in votes if v]
        if len(non_empty) == 3 and len(set(non_empty)) == 1:
            full_agreement_count += 1

    total_samples = len(annotations)

    return {
        "fleiss_kappa": kappa,
        "pairwise_agreements": pairwise_agreements,
        "full_agreement_count": full_agreement_count,
        "total_samples": total_samples,
        "llm_vs_majority_match": llm_vs_majority_match,
        "llm_vs_majority_rate": (
            llm_vs_majority_match / samples_with_majority if samples_with_majority else 0
        ),
        "majority_labels": majority_labels,
        "primary_labels": primary_labels,
        "sample_ids": sample_ids,
        "samples_with_majority": samples_with_majority,
        "samples_without_majority": samples_without_majority,
        "samples_missing_votes": samples_missing_votes,
    }

# =================================================================================
# 3. LLM准确率分析
# =================================================================================
def compute_cohen_kappa(pairs: List[Tuple[str, str]]) -> float:
    """计算两类标注之间的Cohen's Kappa"""
    filtered_pairs = [(a, b) for a, b in pairs if a and b]
    total = len(filtered_pairs)
    if total == 0:
        return 0.0

    categories = sorted({label for pair in filtered_pairs for label in pair})
    idx_map = {label: i for i, label in enumerate(categories)}
    confusion = np.zeros((len(categories), len(categories)), dtype=float)

    for a, b in filtered_pairs:
        confusion[idx_map[a], idx_map[b]] += 1

    observed = np.trace(confusion) / total
    row_marginals = confusion.sum(axis=1)
    col_marginals = confusion.sum(axis=0)
    expected = float(np.sum(row_marginals * col_marginals)) / (total ** 2)

    if expected == 1.0:
        return 1.0
    if expected == 0.0:
        return 0.0

    return (observed - expected) / (1 - expected)


def calculate_llm_performance(annotator_data: Dict, consistency_analysis: Dict) -> Dict:
    """比较初次LLM与人工（由二次列代替）的一致性"""
    results = {}

    for annotator_name, data in annotator_data.items():
        samples = data.get("samples", [])
        stats = {
            "primary_vs_human": {
                "correct": 0,
                "total": 0,
                "confusion_matrix": defaultdict(lambda: defaultdict(int)),
                "pairs": [],
                "skipped_due_to_missing_llm": 0,
                "skipped_due_to_missing_human": 0,
            }
        }

        for sample in samples:
            human_cls = sample.get("human_classification", "").strip()
            if not human_cls:
                stats["primary_vs_human"]["skipped_due_to_missing_human"] += 1
                continue

            primary_cls = sample.get("llm_classification", "").strip()
            if not primary_cls:
                stats["primary_vs_human"]["skipped_due_to_missing_llm"] += 1
                continue

            stats["primary_vs_human"]["total"] += 1
            stats["primary_vs_human"]["confusion_matrix"][primary_cls][human_cls] += 1
            stats["primary_vs_human"]["pairs"].append((primary_cls, human_cls))
            if primary_cls == human_cls:
                stats["primary_vs_human"]["correct"] += 1

        total = stats["primary_vs_human"]["total"]
        correct = stats["primary_vs_human"]["correct"]
        stats["primary_vs_human"]["accuracy"] = correct / total if total > 0 else 0
        stats["primary_vs_human"]["confusion_matrix"] = dict(stats["primary_vs_human"]["confusion_matrix"])
        stats["primary_vs_human"]["kappa"] = compute_cohen_kappa(stats["primary_vs_human"]["pairs"])
        stats["primary_vs_human"].pop("pairs", None)

        results[annotator_name] = stats

    results["COMMON"] = {
        "primary_vs_majority": {
            "accuracy": consistency_analysis.get("llm_vs_majority_rate", 0),
            "correct": consistency_analysis.get("llm_vs_majority_match", 0),
            "total": consistency_analysis.get("samples_with_majority", 0),
            "skipped_no_majority": consistency_analysis.get("samples_without_majority", 0),
            "skipped_missing_votes": consistency_analysis.get("samples_missing_votes", 0),
        }
    }

    return results

# =================================================================================
# 4. 困难样本识别
# =================================================================================
def identify_difficult_samples(common_data: Dict) -> List[Dict]:
    """识别标注不一致的困难样本"""
    difficult_samples = []
    
    for sample in common_data["samples"]:
        annotations = [
            sample.get("human_classification_A", ""),
            sample.get("human_classification_B", ""),
            sample.get("human_classification_C", "")
        ]
        
        # 过滤空标注
        valid_annotations = [a for a in annotations if a]
        
        if len(valid_annotations) >= 2:  # 至少两人标注
            # 检查是否有不一致
            if len(set(valid_annotations)) > 1:
                difficult_samples.append({
                    "sample_id": sample["sample_id"],
                    "paper_a_id": sample["paper_a_id"],
                    "paper_b_id": sample["paper_b_id"],
                    "llm_classification": sample["llm_classification"],
                    "annotations": annotations,
                    "disagreement_level": len(set(valid_annotations))  # 不同意见的数量
                })
    
    # 按不一致程度排序
    difficult_samples.sort(key=lambda x: x["disagreement_level"], reverse=True)
    
    return difficult_samples

# =================================================================================
# 5. 生成报告
# =================================================================================
def generate_analysis_report(
    consistency_analysis: Dict,
    llm_performance: Dict,
    difficult_samples: List[Dict],
    output_path: str
):
    """生成分析报告"""
    
    report = {
        "生成时间": __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        
        "一致性分析": {
            "Fleiss_Kappa": consistency_analysis.get("fleiss_kappa", 0),
            "Kappa解释": interpret_kappa(consistency_analysis.get("fleiss_kappa", 0)),
            "完全一致样本数": consistency_analysis.get("full_agreement_count", 0),
            "总样本数": consistency_analysis.get("total_samples", 0),
            "完全一致率": consistency_analysis.get("full_agreement_count", 0) / consistency_analysis.get("total_samples", 1),
            "两两一致率": consistency_analysis.get("pairwise_agreements", {})
        },
        
        "LLM表现对比": {
            annotator: {
                "初次与人工准确率": data["primary_vs_human"].get("accuracy", 0),
                "初次与人工Kappa": data["primary_vs_human"].get("kappa", 0),
                "初次正确数": data["primary_vs_human"].get("correct", 0),
                "统计总数": data["primary_vs_human"].get("total", 0),
                "混淆矩阵": data["primary_vs_human"].get("confusion_matrix", {}),
            }
            for annotator, data in llm_performance.items() if annotator != "COMMON"
        },
        "共同样本初次-多数票一致率": llm_performance.get("COMMON", {}).get("primary_vs_majority", {}),
        
        "困难样本": {
            "总数": len(difficult_samples),
            "详细列表": difficult_samples[:20]  # 只保存前20个最困难的
        },
        
        "建议": generate_recommendations(consistency_analysis, llm_performance, difficult_samples)
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 分析报告已保存到: {output_path}")
    return report

def interpret_kappa(kappa: float) -> str:
    """解释Kappa值"""
    if kappa < 0:
        return "差（小于0）：一致性低于随机"
    elif kappa < 0.2:
        return "轻微（0-0.2）：一致性很低"
    elif kappa < 0.4:
        return "一般（0.2-0.4）：一致性较低"
    elif kappa < 0.6:
        return "中等（0.4-0.6）：一致性中等"
    elif kappa < 0.8:
        return "较高（0.6-0.8）：一致性较好"
    else:
        return "很高（0.8-1.0）：一致性很好"

def generate_recommendations(
    consistency_analysis: Dict,
    llm_accuracy: Dict,
    difficult_samples: List[Dict]
) -> List[str]:
    """生成改进建议"""
    recommendations = []
    
    kappa = consistency_analysis.get("fleiss_kappa", 0)
    if kappa < 0.6:
        recommendations.append("标注一致性较低，建议：1) 明确标注规则；2) 对困难样本进行讨论；3) 增加标注培训")
    
    accuracies = [
        stats["primary_vs_human"].get("accuracy", 0)
        for name, stats in llm_accuracy.items()
        if name != "COMMON" and stats["primary_vs_human"].get("total", 0) > 0
    ]
    if accuracies:
        avg_accuracy = np.mean(accuracies)
        if avg_accuracy < 0.7:
            recommendations.append(f"LLM与人工平均一致率为{avg_accuracy:.2%}，建议优化prompt或更新模型")
        elif avg_accuracy > 0.85:
            recommendations.append(f"LLM与人工平均一致率为{avg_accuracy:.2%}，表现优秀，可考虑减少人工复核比例")
    
    if len(difficult_samples) > 20:
        recommendations.append(f"发现{len(difficult_samples)}个困难样本，建议组织讨论会统一标准")
    
    return recommendations

# =================================================================================
# 6. 主流程
# =================================================================================
def main():
    """主流程"""
    print("="*80)
    print("标注结果分析脚本")
    print("="*80)
    
    data_dir = "Myexamples/build_graph_connections/annotation_data"
    
    # 1. 加载数据
    print("\n【步骤1】加载标注数据...")
    try:
        data = load_annotation_files(data_dir)
        print("✅ 数据加载完成")
    except Exception as e:
        print(f"❌ 加载失败: {e}")
        return
    
    # 2. 分析共同校验数据的一致性
    print("\n【步骤2】分析标注一致性...")
    consistency_analysis = analyze_common_annotations(data["common"])
    if "error" in consistency_analysis:
        print(f"⚠️ {consistency_analysis['error']}")
    else:
        print(f"✅ Fleiss' Kappa: {consistency_analysis['fleiss_kappa']:.3f}")
        print(f"✅ 完全一致率: {consistency_analysis['full_agreement_count']}/{consistency_analysis['total_samples']}")
    
    # 3. 计算LLM准确率
    print("\n【步骤3】计算LLM准确率...")
    llm_performance = calculate_llm_performance(data["annotators"], consistency_analysis)
    for annotator, stats in llm_performance.items():
        if annotator == "COMMON":
            common_stats = stats.get("primary_vs_majority", {})
            print(
                f"🤝 共同样本：初次LLM与多数票一致率 {common_stats.get('accuracy', 0):.2%} "
                f"({common_stats.get('correct', 0)}/{common_stats.get('total', 0)})"
            )
            skipped_no_majority = common_stats.get("skipped_no_majority", 0)
            skipped_missing_votes = common_stats.get("skipped_missing_votes", 0)
            if skipped_no_majority or skipped_missing_votes:
                print(
                    f"   ⏭️ 跳过样本：无多数 {skipped_no_majority} 条，缺失标注 {skipped_missing_votes} 条"
                )
            continue

        primary_stats = stats["primary_vs_human"]
        primary_acc = primary_stats.get("accuracy", 0)
        primary_kappa = primary_stats.get("kappa", 0)
        print(
            f"✅ {annotator}: 初次LLM vs 人工 一致率 {primary_acc:.2%} "
            f"(κ={primary_kappa:.3f}, {primary_stats.get('correct', 0)}/{primary_stats.get('total', 0)})"
        )
    
    # 4. 识别困难样本
    print("\n【步骤4】识别困难样本...")
    difficult_samples = identify_difficult_samples(data["common"])
    print(f"✅ 发现{len(difficult_samples)}个标注不一致的样本")
    
    # 5. 生成报告
    print("\n【步骤5】生成分析报告...")
    output_path = os.path.join(data_dir, "标注分析报告.json")
    report = generate_analysis_report(
        consistency_analysis,
        llm_performance,
        difficult_samples,
        output_path
    )
    
    # 6. 打印关键发现
    print("\n" + "="*80)
    print("关键发现")
    print("="*80)
    print(f"📊 标注一致性: {interpret_kappa(consistency_analysis.get('fleiss_kappa', 0))}")
    valid_stats = [stats for name, stats in llm_performance.items() if name != "COMMON" and stats["primary_vs_human"].get("total", 0) > 0]
    if valid_stats:
        avg_primary = np.mean([s["primary_vs_human"].get("accuracy", 0) for s in valid_stats])
        avg_primary_kappa = np.mean([s["primary_vs_human"].get("kappa", 0) for s in valid_stats])
        print(f"🤖 LLM与人工平均一致率: {avg_primary:.2%}")
        print(f"🤖 LLM与人工平均Kappa: {avg_primary_kappa:.3f}")
    common_stats = llm_performance.get("COMMON", {}).get("primary_vs_majority", {})
    if common_stats:
        print(f"🤝 初次LLM与多数票一致率: {common_stats.get('accuracy', 0):.2%}")
    print(f"⚠️  困难样本数: {len(difficult_samples)}")
    
    if report["建议"]:
        print("\n💡 改进建议:")
        for i, rec in enumerate(report["建议"], 1):
            print(f"   {i}. {rec}")
    
    print("\n✅ 分析完成！")

if __name__ == "__main__":
    main()
