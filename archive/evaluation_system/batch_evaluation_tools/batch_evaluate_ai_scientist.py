#!/usr/bin/env python3
"""
批量评估 AI-Scientist 生成的报告，并汇总结果到 Excel

此脚本基于 evaluate_ai_scientist.py 的逻辑，针对批量处理进行了优化：
- 从 /batch_results/ai_scientist/results/{question_id}/result.json 读取结果
- 提取 idea 文本进行评估
- 调用 run_evaluation.py 进行完整评估（包含RAG系统）
- 收集所有评估结果并汇总到 Excel 表格

使用示例：
    python batch_evaluate_ai_scientist.py \
        --results-dir /root/autodl-tmp/Myexamples/evaluation_system/batch_results/ai_scientist/results \
        --output-excel /root/autodl-tmp/Myexamples/evaluation_system/batch_results/ai_scientist/ai_scientist_metrics.xlsx
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import numpy as np

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 项目内部导入
try:
    from Myexamples.agents.graph_agents.local_rag import run_local_rag
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    print("⚠️  RAG module not available")


def ensure_env_defaults() -> None:
    """为评估脚本准备必需的环境变量。"""
    if not os.environ.get("OPENAI_COMPATIBILITY_API_KEY"):
        os.environ["OPENAI_COMPATIBILITY_API_KEY"] = "sk-c1a6b588f7d543adb0412c5bc61bdd7b"
    if not os.environ.get("OPENAI_COMPATIBILITY_API_BASE_URL"):
        os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    os.environ.setdefault("QWEN_API_KEY", os.environ["OPENAI_COMPATIBILITY_API_KEY"])
    os.environ.setdefault("QWEN_API_BASE_URL", os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"])


def extract_source_documents_via_rag(idea_text: str, research_topic: str, vdb_path: str, json_data_path: str) -> List[str]:
    """使用RAG系统从idea文本和研究主题中提取源文献（仅向量检索）"""
    if not RAG_AVAILABLE:
        print("   ⚠️  RAG不可用，跳过源文献提取")
        return []
    
    try:
        print("   🔍 使用RAG系统提取源文献（向量检索）...")
        
        # 构建查询
        query = f"{research_topic}\n\n{idea_text[:500]}"  # 使用主题和idea的前500字符
        
        # 调用RAG系统
        rag_results = run_local_rag(
            query=query,
            json_file_path=json_data_path,
            base_vdb_path=vdb_path,
            max_index_size_mb=512,
            return_structured=True
        )
        
        # 解析RAG结果（返回字符串）
        source_docs = []
        if isinstance(rag_results, str):
            import re
            
            # 只提取 PART 1 的向量检索结果
            # 查找 "[PART 1: PRIMARY EVIDENCE - Vector Search Results]" 部分
            # 使用更精确的正则表达式，匹配到下一个 [PART 或 "---" 分隔符
            part1_match = re.search(
                r'\[PART 1: PRIMARY EVIDENCE - Vector Search Results\](.*?)(?=\[PART 2:|\n---|\Z)',
                rag_results,
                re.DOTALL
            )
            
            if part1_match:
                part1_content = part1_match.group(1)
                # 从 PART 1 中提取所有 Paper ID（格式：10.xxxx/xxxxx）
                # 只在 "Paper ID:" 后面的内容中提取
                paper_id_matches = re.findall(r'Paper ID:\s*(10\.\d{4,}/[^\s\n]+)', part1_content)
                source_docs.extend(paper_id_matches)
            else:
                # 如果找不到 PART 1 标记，尝试从整个结果中提取 Paper ID
                # 但只提取在 "Paper ID:" 标签后的 ID
                paper_id_matches = re.findall(r'Paper ID:\s*(10\.\d{4,}/[^\s\n]+)', rag_results)
                source_docs.extend(paper_id_matches)
            
            # 也提取中文书名（格式：《标题》），但只从 PART 1 中提取
            if part1_match:
                part1_content = part1_match.group(1)
                book_titles = re.findall(r'《([^》]+)》', part1_content)
                source_docs.extend(book_titles)
        
        # 去重
        source_docs = list(set(source_docs))
        
        if source_docs:
            print(f"   ✅ 从向量检索找到 {len(source_docs)} 篇源文献")
        else:
            print("   ℹ️  向量检索未返回源文献")
        
        return source_docs
        
    except Exception as e:
        print(f"   ⚠️  RAG提取失败: {e}")
        return []


def save_source_docs_to_json(source_docs: List[str], output_path: str, json_data_path: str) -> None:
    """将源文献保存为JSON文件，供run_evaluation.py使用
    
    Args:
        source_docs: Paper ID列表
        output_path: 输出JSON文件路径
        json_data_path: 原始数据JSON文件路径（用于查找摘要）
    """
    try:
        # 从原始JSON数据中查找对应的摘要
        abstracts = []
        
        if source_docs and os.path.exists(json_data_path):
            try:
                with open(json_data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 构建 paper_id -> abstract 的映射
                paper_map = {}
                for entity in data.get("entities", []):
                    if entity.get("entity_type") == "paper":
                        paper_id = entity.get("source_id")
                        abstract = entity.get("abstract", "")
                        if paper_id and abstract:
                            paper_map[paper_id] = abstract
                
                # 查找每个source_doc对应的摘要
                for doc_id in source_docs:
                    if doc_id in paper_map:
                        abstracts.append(paper_map[doc_id])
                    else:
                        # 如果找不到摘要，使用Paper ID本身作为文本
                        abstracts.append(f"Paper: {doc_id}")
            except Exception as e:
                print(f"   ⚠️  查找摘要失败: {e}")
                # 降级：直接使用Paper ID
                abstracts = [f"Paper: {doc_id}" for doc_id in source_docs]
        else:
            # 降级：直接使用Paper ID
            abstracts = [f"Paper: {doc_id}" for doc_id in source_docs]
        
        # 保存为run_evaluation.py期望的格式
        data = {"source_documents": abstracts}
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        if abstracts:
            print(f"   ✅ 保存 {len(abstracts)} 篇源文献摘要到JSON")
    except Exception as e:
        print(f"   ⚠️  保存源文献JSON失败: {e}")


def extract_idea_from_json(json_path: str) -> str:
    """从 result.json 提取 idea 文本"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        idea = data.get("idea", "")
        
        if isinstance(idea, str) and len(idea.strip()) > 50:
            return idea
        
        idea_dict = data.get("idea_dict", {})
        if idea_dict:
            idea_text = ""
            if idea_dict.get("Title"):
                idea_text += f"**Title:** {idea_dict.get('Title')}\n\n"
            if idea_dict.get("Short Hypothesis"):
                idea_text += f"**Hypothesis:** {idea_dict.get('Short Hypothesis')}\n\n"
            if idea_dict.get("Abstract"):
                idea_text += f"**Abstract:**\n{idea_dict.get('Abstract')}\n\n"
            if idea_dict.get("Related Work"):
                idea_text += f"**Related Work:**\n{idea_dict.get('Related Work')}\n\n"
            if idea_dict.get("Experiments"):
                experiments = idea_dict.get("Experiments", [])
                if isinstance(experiments, list):
                    idea_text += f"**Proposed Experiments:**\n"
                    for exp in experiments:
                        idea_text += f"- {exp}\n"
            return idea_text.strip() if idea_text else str(idea_dict)
        
        return str(idea) if idea else str(idea_dict)
        
    except Exception as e:
        print(f"❌ 读取 JSON 文件失败: {e}")
        return ""


def flatten_dict(data: Any, parent_key: str = "", sep: str = ".", output: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """递归扁平化字典/列表结果，便于写入表格。"""
    if output is None:
        output = {}
    
    if isinstance(data, dict):
        for k, v in data.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            flatten_dict(v, new_key, sep, output)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            new_key = f"{parent_key}[{i}]"
            flatten_dict(item, new_key, sep, output)
    else:
        output[parent_key] = data
    
    return output


def evaluate_ai_scientist_results(args: argparse.Namespace) -> List[Dict[str, Any]]:
    """批量评估 AI-Scientist 的结果，使用 run_evaluation.py 进行完整评估"""
    
    ensure_env_defaults()
    
    results_dir = Path(args.results_dir)
    if not results_dir.exists():
        print(f"❌ 结果目录不存在: {results_dir}")
        return []
    
    # 查找所有 result.json 文件
    result_files = sorted(list(results_dir.glob("*/result.json")))
    
    # 如果指定了限制数量，只处理前 N 个
    if args.limit and args.limit > 0:
        result_files = result_files[:args.limit]
        print(f"\n🧾 共发现 {len(list(results_dir.glob('*/result.json')))} 份报告，当前准备处理 {len(result_files)} 份（限制模式）。")
    else:
        print(f"\n🧾 共发现 {len(result_files)} 份报告，当前准备处理 {len(result_files)} 份。")
    
    if not result_files:
        print("❌ 未找到任何 result.json 文件")
        return []
    
    vdb_path = os.path.join(PROJECT_ROOT, 'Myexamples/vdb/camel_faiss_storage')
    json_data_path = os.path.join(PROJECT_ROOT, 'Myexamples/data/final_data/final_custom_kg_papers.json')
    
    evaluations = []
    temp_dir = Path(args.output_excel).parent / "temp_evaluations"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    for idx, result_file in enumerate(result_files, 1):
        question_id = result_file.parent.name
        print(f"\n[{idx}/{len(result_files)}] 评估报告: {question_id}")
        
        try:
            # 提取 idea 文本
            idea_text = extract_idea_from_json(str(result_file))
            if not idea_text or len(idea_text.strip()) < 50:
                print(f"   ⚠️ 无法提取有效的 idea 文本")
                continue
            
            print(f"   📄 Idea 文本长度: {len(idea_text)} 字符")
            
            # 创建临时输出目录
            eval_output_dir = temp_dir / question_id
            eval_output_dir.mkdir(parents=True, exist_ok=True)
            
            # 使用RAG系统提取源文献
            research_topic = question_id.replace("_", " ")
            source_docs = extract_source_documents_via_rag(idea_text, research_topic, vdb_path, json_data_path)
            
            # 保存源文献到JSON文件
            source_docs_json_path = str(eval_output_dir / "source_documents.json")
            if source_docs:
                save_source_docs_to_json(source_docs, source_docs_json_path, json_data_path)
            
            # 调用 run_evaluation.py 进行评估
            cmd = [
                "python", "Myexamples/evaluation_system/run_evaluation.py",
                "--input_text", idea_text,
                "--vdb_path", vdb_path,
                "--json_data", json_data_path,
                "--output_dir", str(eval_output_dir)
            ]
            
            # 如果有源文献，传给run_evaluation.py
            if source_docs:
                cmd.extend(["--source_docs", source_docs_json_path])
            
            print(f"   🚀 调用 run_evaluation.py...")
            result = subprocess.run(
                cmd,
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                # 查找生成的 JSON 结果文件
                json_files = list(eval_output_dir.glob("*_eval_v2.json"))
                if json_files:
                    with open(json_files[0], 'r', encoding='utf-8') as f:
                        eval_result = json.load(f)
                    
                    # 提取关键指标
                    evaluation = {
                        "metadata": {
                            "question_id": question_id,
                            "system": "ai_scientist",
                            "evaluation_time": datetime.now().isoformat(),
                            "idea_length": len(idea_text)
                        },
                        "metrics": eval_result.get("metrics", {})
                    }
                    evaluations.append(evaluation)
                    print(f"   ✅ 评估完成")
                else:
                    print(f"   ⚠️ 未找到评估结果文件")
            else:
                print(f"   ❌ 评估失败: {result.stderr[:200]}")
                
        except subprocess.TimeoutExpired:
            print(f"   ❌ 评估超时")
        except Exception as e:
            print(f"   ❌ 评估异常: {e}")
            import traceback
            traceback.print_exc()
    
    return evaluations


def export_to_excel(evaluations: List[Dict[str, Any]], excel_path: Path) -> None:
    """将评估结果导出为 Excel"""
    
    rows = []
    
    for item in evaluations:
        row: Dict[str, Any] = {}
        
        # 元数据
        row.update(item.get("metadata", {}))
        
        # 目标指标
        metrics = item.get("metrics", {})
        
        # 处理两种可能的结构：
        # 1. 旧结构：metrics.objective.Novelty_Metrics / Provenance_Metrics
        # 2. 新结构：metrics 直接包含各种指标
        objective = metrics.get("objective", {})
        
        # 新颖性指标
        if objective:
            novelty = objective.get("Novelty_Metrics", {})
        else:
            novelty = metrics.get("Novelty_Metrics", {})
        
        if novelty:
            # 处理两种可能的键名
            row["ON_raw"] = novelty.get("ON_raw (Overall Novelty - Raw)", novelty.get("ON (Overall Novelty - Raw)", np.nan))
            row["ON_normalized"] = novelty.get("ON (Overall Novelty - Normalized)", np.nan)
            row["Rank"] = novelty.get("Rank", np.nan)
            row["Total_Hypotheses"] = novelty.get("Total_Hypotheses", np.nan)
            # 处理 HD/CD/CI 的不同键名
            row["HD"] = novelty.get("HD (Historical Dissimilarity)", novelty.get("HD (Hamming Distance)", np.nan))
            row["CD"] = novelty.get("CD (Contemporary Dissimilarity)", novelty.get("CD (Cosine Distance)", np.nan))
            row["CI"] = novelty.get("CI (Contemporary Impact, Year-Normalized)", novelty.get("CI (Concept Innovation)", np.nan))
        
        # 溯源指标
        if objective:
            provenance = objective.get("Provenance_Metrics")
        else:
            provenance = metrics.get("Provenance_Metrics")
        
        if provenance and isinstance(provenance, dict):
            # 处理两种可能的键名格式
            row["P"] = provenance.get("P (Provenance-Adjusted Novelty)", provenance.get("P", np.nan))
            row["S_src"] = provenance.get("S_src (Source Similarity)", provenance.get("S_src", np.nan))
            row["U_src"] = provenance.get("U_src (Source Diversity)", provenance.get("U_src", np.nan))
            row["G"] = provenance.get("G (Provenance Factor)", provenance.get("G", np.nan))
        else:
            row["P"] = np.nan
            row["S_src"] = np.nan
            row["U_src"] = np.nan
            row["G"] = np.nan
        
        # 主观评审（支持两种键名：subjective 和 subjective_llm）
        subjective = metrics.get("subjective", {}) or metrics.get("subjective_llm", {})
        if subjective:
            row["Novelty"] = subjective.get("Novelty", np.nan)
            row["Significance"] = subjective.get("Significance", np.nan)
            row["Effectiveness"] = subjective.get("Effectiveness", np.nan)
            row["Clarity"] = subjective.get("Clarity", np.nan)
            row["Feasibility"] = subjective.get("Feasibility", np.nan)
        
        rows.append(row)
    
    # 创建 DataFrame
    df = pd.DataFrame(rows)
    
    # 确保输出目录存在
    excel_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 导出到 Excel
    df.to_excel(excel_path, index=False, engine='openpyxl')
    print(f"\n✅ 结果已导出到 Excel: {excel_path}")
    print(f"   共 {len(df)} 行数据")
    print(f"   共 {len(df.columns)} 列指标")


def main():
    parser = argparse.ArgumentParser(description="批量评估 AI-Scientist 生成的报告")
    parser.add_argument("--results-dir", type=str, required=True, help="AI-Scientist 结果目录")
    parser.add_argument("--output-excel", type=str, required=True, help="输出 Excel 文件路径")
    parser.add_argument("--skip-llm", action="store_true", help="跳过 LLM 主观评审（加快速度）")
    parser.add_argument("--limit", type=int, default=None, help="限制处理的报告数量（用于测试）")
    
    args = parser.parse_args()
    
    print("="*80)
    print("🔬 AI-Scientist 批量评估工具")
    print("="*80)
    
    # 评估所有报告
    evaluations = evaluate_ai_scientist_results(args)
    
    if evaluations:
        # 导出到 Excel
        export_to_excel(evaluations, Path(args.output_excel))
        print("\n" + "="*80)
        print("🎉 评估完成！")
        print("="*80)
    else:
        print("\n❌ 没有成功评估任何报告")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
