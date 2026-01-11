#!/usr/bin/env python3
"""
重新计算所有报告的指标，修复异常值问题
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import os
import json
import pandas as pd
from datetime import datetime
from Myexamples.evaluation_system.run_evaluation import extract_core_content
from Myexamples.evaluation_system.metrics_calculator import ScientificMetricsCalculator
from Myexamples.evaluation_system.llm_evaluator import ScientificLLMEvaluator
from Myexamples.evaluation_system.aggregate_metrics_to_excel import (
    collect_source_documents,
    extract_topic_from_report,
    flatten_dict
)
from camel.embeddings import OpenAICompatibleEmbedding

# 设置环境变量
if not os.environ.get("OPENAI_COMPATIBILITY_API_KEY"):
    os.environ["OPENAI_COMPATIBILITY_API_KEY"] = "sk-c1a6b588f7d543adb0412c5bc61bdd7b"
if not os.environ.get("OPENAI_COMPATIBILITY_API_BASE_URL"):
    os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
os.environ.setdefault("QWEN_API_KEY", os.environ["OPENAI_COMPATIBILITY_API_KEY"])
os.environ.setdefault("QWEN_API_BASE_URL", os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"])

def main():
    print("=" * 80)
    print("重新计算所有报告的指标（修复异常值问题）")
    print("=" * 80)
    
    # 读取原始Excel
    excel_path = Path("Myexamples/evaluation_system/batch_results/ours/metrics_summary.xlsx")
    if not excel_path.exists():
        print(f"错误: Excel文件不存在: {excel_path}")
        return
    
    df_original = pd.read_excel(excel_path)
    print(f"原始数据: {len(df_original)} 行")
    
    # 找出需要重新计算的报告（核心文本为空的或主观指标为0的）
    reports_to_recalculate = []
    for idx, row in df_original.iterrows():
        report_path = row.get('report_path', '')
        if not report_path or not Path(report_path).exists():
            continue
        
        # 检查是否有异常值
        novelty = row.get('subjective_llm.Novelty', None)
        fluency = row.get('objective.Fluency_Score', None)
        
        # 如果主观指标为0或Fluency_Score异常低，需要重新计算
        if (novelty == 0) or (fluency is not None and fluency < 0.5):
            reports_to_recalculate.append((idx, report_path, row.get('report_name', '')))
    
    print(f"\n发现 {len(reports_to_recalculate)} 个需要重新计算的报告:")
    for idx, path, name in reports_to_recalculate[:10]:  # 只显示前10个
        print(f"  [{idx}] {name}")
    if len(reports_to_recalculate) > 10:
        print(f"  ... 还有 {len(reports_to_recalculate) - 10} 个")
    
    if not reports_to_recalculate:
        print("\n✅ 没有发现需要重新计算的报告")
        return
    
    # 初始化评估器
    print("\n初始化评估器...")
    embedding_model = OpenAICompatibleEmbedding(
        model_type="text-embedding-v2",
        api_key=os.environ.get("OPENAI_COMPATIBILITY_API_KEY"),
        url=os.environ.get("OPENAI_COMPATIBILITY_API_BASE_URL"),
    )
    calculator = ScientificMetricsCalculator(
        "Myexamples/vdb/camel_faiss_storage",
        embedding_model
    )
    calculator.load_resources("Myexamples/data/final_data/final_custom_kg_papers.json")
    llm_evaluator = ScientificLLMEvaluator()
    
    # 重新计算
    print(f"\n开始重新计算 {len(reports_to_recalculate)} 个报告...")
    updated_count = 0
    
    for idx, report_path, report_name in reports_to_recalculate:
        print(f"\n[{updated_count + 1}/{len(reports_to_recalculate)}] 处理: {report_name}")
        
        try:
            report_file = Path(report_path)
            if not report_file.exists():
                print(f"  ⚠️ 文件不存在，跳过")
                continue
            
            with report_file.open("r", encoding="utf-8") as f:
                report_text = f.read()
            
            # 提取核心内容（使用改进后的函数）
            core_text = extract_core_content(report_text)
            topic_text = extract_topic_from_report(report_text)
            
            print(f"  - 核心文本长度: {len(core_text)} 字符")
            
            if len(core_text) < 100:
                print(f"  ⚠️ 警告: 核心文本仍然太短 ({len(core_text)} 字符)")
                # 使用完整文本作为后备
                core_text = report_text[:4000]
                print(f"  - 使用完整文本前4000字符")
            
            # 收集源文档
            source_docs = collect_source_documents(
                report_file, report_text, topic_text, core_text, calculator
            )
            
            # 计算客观指标
            objective_metrics = calculator.evaluate_text(
                core_text, 
                source_documents=source_docs if source_docs else None
            )
            
            # 计算主观指标
            subjective_metrics = llm_evaluator.absolute_evaluation(core_text)
            
            # 检查主观指标是否有效
            if "Error" in subjective_metrics:
                print(f"  ⚠️ LLM评估返回错误: {subjective_metrics['Error']}")
            else:
                # 更新DataFrame
                for key, value in flatten_dict({"objective": objective_metrics}, parent_key="objective").items():
                    if key in df_original.columns:
                        df_original.at[idx, key] = value
                
                for key, value in flatten_dict({"subjective_llm": subjective_metrics}, parent_key="subjective_llm").items():
                    if key in df_original.columns:
                        df_original.at[idx, key] = value
                
                # 更新raw_json
                evaluation_payload = {
                    "metadata": {
                        "report_path": str(report_path),
                        "report_name": report_name,
                        "topic": topic_text,
                        "timestamp": datetime.now().isoformat(),
                    },
                    "metrics": {
                        "objective": objective_metrics,
                        "subjective_llm": subjective_metrics,
                    },
                }
                df_original.at[idx, 'raw_json'] = json.dumps(evaluation_payload, ensure_ascii=False)
                
                print(f"  ✅ 更新完成")
                updated_count += 1
        
        except Exception as e:
            print(f"  ❌ 处理失败: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # 保存更新后的Excel
    if updated_count > 0:
        output_path = excel_path.parent / "metrics_summary_recalculated.xlsx"
        df_original.to_excel(output_path, index=False)
        print(f"\n✅ 已更新 {updated_count} 个报告")
        print(f"✅ 结果已保存到: {output_path}")
        print(f"\n建议: 检查新文件后，如果结果正确，可以替换原文件")
    else:
        print("\n⚠️ 没有成功更新任何报告")

if __name__ == "__main__":
    main()

