#!/usr/bin/env python3
"""
重新计算单个报告的指标，用于调试异常值问题
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import os
import json
from Myexamples.evaluation_system.run_evaluation import extract_core_content
from Myexamples.evaluation_system.metrics_calculator import ScientificMetricsCalculator
from Myexamples.evaluation_system.llm_evaluator import ScientificLLMEvaluator
from camel.embeddings import OpenAICompatibleEmbedding

# 设置环境变量
if not os.environ.get("OPENAI_COMPATIBILITY_API_KEY"):
    os.environ["OPENAI_COMPATIBILITY_API_KEY"] = "sk-c1a6b588f7d543adb0412c5bc61bdd7b"
if not os.environ.get("OPENAI_COMPATIBILITY_API_BASE_URL"):
    os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
os.environ.setdefault("QWEN_API_KEY", os.environ["OPENAI_COMPATIBILITY_API_KEY"])
os.environ.setdefault("QWEN_API_BASE_URL", os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"])

# 异常报告路径
report_path = Path("Scientific_Hypothesis_Reports/20251209_065850_How_does_pre-expansion_pruning_in_trie-constrained.md")

print("=" * 80)
print("重新计算异常报告的指标")
print("=" * 80)
print(f"报告路径: {report_path}")

if not report_path.exists():
    print(f"错误: 文件不存在")
    sys.exit(1)

# 读取报告
with report_path.open("r", encoding="utf-8") as f:
    report_text = f.read()

print(f"\n报告长度: {len(report_text)} 字符")

# 提取核心内容
core_text = extract_core_content(report_text)
print(f"核心文本长度: {len(core_text)} 字符")

if len(core_text) < 100:
    print("⚠️ 警告: 核心文本太短，可能无法正确评估")

# 初始化计算器
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

# 计算客观指标
print("\n计算客观指标...")
try:
    objective_metrics = calculator.evaluate_text(core_text, source_documents=None)
    print("客观指标结果:")
    print(json.dumps(objective_metrics, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"❌ 客观指标计算失败: {e}")
    import traceback
    traceback.print_exc()
    objective_metrics = {}

# 计算主观指标
print("\n计算主观指标（LLM评估）...")
llm_evaluator = ScientificLLMEvaluator()
try:
    subjective_metrics = llm_evaluator.absolute_evaluation(core_text)
    print("主观指标结果:")
    print(json.dumps(subjective_metrics, indent=2, ensure_ascii=False))
    
    # 检查是否有错误
    if "Error" in subjective_metrics:
        print(f"\n⚠️ LLM评估返回错误: {subjective_metrics['Error']}")
    else:
        # 检查是否有0值
        zero_keys = [k for k, v in subjective_metrics.items() if isinstance(v, (int, float)) and v == 0]
        if zero_keys:
            print(f"\n⚠️ 发现0值指标: {zero_keys}")
        else:
            print("\n✅ 所有主观指标都有有效值")
            
except Exception as e:
    print(f"❌ 主观指标计算失败: {e}")
    import traceback
    traceback.print_exc()
    subjective_metrics = {"Error": str(e)}

# 检查Excel中的原始数据
print("\n" + "=" * 80)
print("检查Excel中的原始数据")
print("=" * 80)

import pandas as pd
excel_path = "Myexamples/evaluation_system/batch_results/ours/metrics_summary.xlsx"
if Path(excel_path).exists():
    df = pd.read_excel(excel_path)
    row_81 = df.iloc[81]
    print(f"\nExcel第81行数据:")
    print(f"  report_name: {row_81.get('report_name', 'N/A')}")
    print(f"  Fluency_Score: {row_81.get('objective.Fluency_Score', 'N/A')}")
    print(f"  Novelty: {row_81.get('subjective_llm.Novelty', 'N/A')}")
    print(f"  Significance: {row_81.get('subjective_llm.Significance', 'N/A')}")
    print(f"  Effectiveness: {row_81.get('subjective_llm.Effectiveness', 'N/A')}")
    print(f"  Clarity: {row_81.get('subjective_llm.Clarity', 'N/A')}")
    print(f"  Feasibility: {row_81.get('subjective_llm.Feasibility', 'N/A')}")
    
    # 检查raw_json
    if 'raw_json' in row_81:
        try:
            raw_data = json.loads(row_81['raw_json'])
            print(f"\n原始JSON数据中的主观指标:")
            subjective = raw_data.get('metrics', {}).get('subjective_llm', {})
            print(json.dumps(subjective, indent=2, ensure_ascii=False))
        except:
            print("无法解析raw_json")

