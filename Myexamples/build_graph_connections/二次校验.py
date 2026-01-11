"""
跨论文关系LLM二次校验脚本
========================================
用途：
1. 读取`annotation_data/`目录下已生成的LLM初评结果
2. 再次调用LLM，根据论文A(abstract+core_problem)与论文B(solution)重新判定关系
3. 对比初次判定，输出“确认/修正” verdict 及二次推理
4. 生成带有校验信息的JSON文件，并汇总统计
"""

import os
import json
import time
import importlib.util
from datetime import datetime
from collections import Counter
from typing import Dict, List, Tuple

import pandas as pd

from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.configs import QwenConfig
from camel.agents import ChatAgent
from camel.messages import BaseMessage

# ================================================================
# 1. 基础配置
# ================================================================
# 复用与生成脚本相同的环境变量，以确保调用同一模型
os.environ.setdefault("OPENAI_COMPATIBILITY_API_KEY", "sk-875e0cf57dd34df59d3bcaef4ee47f80")
os.environ.setdefault("OPENAI_COMPATIBILITY_API_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
os.environ.setdefault("QWEN_API_KEY", os.environ["OPENAI_COMPATIBILITY_API_KEY"])
os.environ.setdefault("QWEN_API_BASE_URL", os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"])

VALIDATION_CONFIG = {
    "ANNOTATION_BASE_DIR": "Myexamples/build_graph_connections/annotation_data",
    "OUTPUT_DIR": "Myexamples/build_graph_connections/annotation_data_llm_validation",
    "CHECKPOINT_INTERVAL": 50,
    "SLEEP_BETWEEN_CALLS": 0.0,  # 用户要求：不等待
    "MAX_SAMPLES_PER_FILE": None,  # 维持无限制
}

def load_primary_prompt() -> str:
    """动态加载`人工标注数据生成.py`中的LLM提示，确保标准一致"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    primary_script = os.path.join(current_dir, "人工标注数据生成.py")
    if not os.path.exists(primary_script):
        raise FileNotFoundError(f"未找到主脚本: {primary_script}")

    spec = importlib.util.spec_from_file_location("manual_generation", primary_script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore

    if not hasattr(module, "LLM_EVALUATION_PROMPT"):
        raise AttributeError("主脚本中缺少 LLM_EVALUATION_PROMPT 定义")
    return getattr(module, "LLM_EVALUATION_PROMPT")


PRIMARY_LLM_PROMPT = load_primary_prompt()


SECONDARY_PROMPT_SUFFIX = """

══════════════════════════════════════════════════════════════════════
【第一次LLM判定（供参考，但你必须独立判断）】
══════════════════════════════════════════════════════════════════════════
初次分类：{first_label}
初次理由：{first_reasoning}

请**独立**完成新的判定，并在必要时推翻上述结论。若原结论正确，请明确给出确认。
⚠️ 请忽略上文中关于输出`relationship_type`与`reasoning`字段的旧格式要求，改为以下JSON输出：
{{
  "secondary_classification": "INSPIRED" | "RELATED" | "NONE",
  "secondary_reasoning": "保持与原prompt相同的分析风格，至少30字，具体说明判定依据",
  "verdict": "CONFIRM" | "REVISE",
  "confidence": "HIGH" | "MEDIUM" | "LOW",
  "notes": "如与初次结论不一致，请解释冲突点；若一致，可填写简短确认"
}}

请勿输出除上述JSON外的任何内容。
"""
def initialize_llm_model():
    """初始化二次校验所需的LLM模型"""
    llm_model = ModelFactory.create(
        model_platform=ModelPlatformType.QWEN,
        model_type=ModelType.COMETAPI_QWEN3_CODER_PLUS_2025_07_22,
        model_config_dict=QwenConfig(temperature=0.1).as_dict(),
        api_key=os.environ["QWEN_API_KEY"],
        url=os.environ["QWEN_API_BASE_URL"],
    )
    return llm_model


def build_secondary_prompt(
    paper_abstract: str,
    paper_core_problem: str,
    solution_text: str,
    first_label: str,
    first_reasoning: str,
) -> str:
    paper_content = f"Abstract: {paper_abstract.strip()}\n\nCore Problem: {paper_core_problem.strip()}"
    base_prompt = PRIMARY_LLM_PROMPT.format(
        paper_content=paper_content,
        solution_text=solution_text.strip(),
    )
    suffix = SECONDARY_PROMPT_SUFFIX.format(
        first_label=first_label.strip() if first_label else "UNKNOWN",
        first_reasoning=first_reasoning.strip() if first_reasoning else "无理由",
    )
    return base_prompt + suffix


def call_llm_secondary_validation(
    llm_model,
    paper_abstract: str,
    paper_core_problem: str,
    solution_text: str,
    first_label: str,
    first_reasoning: str,
) -> Dict:
    """调用LLM进行二次校验，返回解析后的结果字典"""
    prompt = build_secondary_prompt(
        paper_abstract=paper_abstract,
        paper_core_problem=paper_core_problem,
        solution_text=solution_text,
        first_label=first_label,
        first_reasoning=first_reasoning,
    )

    try:
        agent = ChatAgent(
            system_message=BaseMessage.make_assistant_message(
                role_name="LLMSecondaryValidator",
                content="你是严谨的科研关系校验专家。"
            ),
            model=llm_model
        )
        user_msg = BaseMessage.make_user_message(role_name="User", content=prompt)
        agent_response = agent.step(user_msg)

        if agent_response and not agent_response.terminated and agent_response.msg:
            response_text = agent_response.msg.content
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                # 尝试从文本中截取JSON片段
                import re
                match = re.search(r"\{.*\}", response_text, re.DOTALL)
                if match:
                    return json.loads(match.group(0))
        return {
            "secondary_classification": "NONE",
            "secondary_reasoning": "LLM响应解析失败，默认记为NONE。",
            "verdict": "REVISE",
            "confidence": "LOW",
            "notes": "无法解析LLM输出，需人工复核。"
        }
    except Exception as exc:
        return {
            "secondary_classification": "NONE",
            "secondary_reasoning": f"LLM调用异常: {exc}",
            "verdict": "REVISE",
            "confidence": "LOW",
            "notes": "调用失败，需要人工复核。"
        }


# ================================================================
# 3. 读取与保存数据
# ================================================================
def collect_annotation_files(base_dir: str) -> List[str]:
    """遍历目录，收集需要二次校验的JSON文件"""
    targets = []
    for root, _, files in os.walk(base_dir):
        for filename in files:
            if not filename.endswith(".json"):
                continue
            if filename.startswith("标注任务总览"):
                continue
            if filename == "similarity_statistics.json":
                continue
            targets.append(os.path.join(root, filename))
    targets.sort()
    return targets


def load_json(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_parent_dir(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def save_json(data: Dict, path: str):
    ensure_parent_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ================================================================
# 3.1 同步写入Excel
# ================================================================
def update_excel_with_secondary_results(json_path: str, updated_data: Dict):
    """将二次校验结果写回同目录下的Excel标注文件"""
    excel_path = json_path.replace(".json", ".xlsx")
    if not os.path.exists(excel_path):
        print(f"  ⚠️ 未找到对应的Excel文件，跳过写入: {excel_path}")
        return False

    try:
        df = pd.read_excel(excel_path, sheet_name="标注数据")
    except Exception as exc:
        print(f"  ⚠️ 读取Excel失败，跳过写入: {excel_path} -> {exc}")
        return False

    # 以sample_id为键，构建映射
    secondary_map = {}
    for sample in updated_data.get("samples", []):
        sample_id = sample.get("sample_id")
        validation = sample.get("llm_secondary_validation", {})
        if sample_id:
            secondary_map[sample_id] = {
                "classification": validation.get("secondary_classification", ""),
                "reasoning": validation.get("secondary_reasoning", ""),
            }

    def map_classification(sample_id):
        return secondary_map.get(sample_id, {}).get("classification", "")

    def map_reasoning(sample_id):
        return secondary_map.get(sample_id, {}).get("reasoning", "")

    new_cols = ["llm_secondary_classification", "llm_secondary_reasoning"]

    for col in new_cols:
        if col not in df.columns:
            df[col] = ""

    df["llm_secondary_classification"] = df["sample_id"].map(map_classification)
    df["llm_secondary_reasoning"] = df["sample_id"].map(map_reasoning)

    # 调整列顺序，将新列放在末尾
    existing_cols = [c for c in df.columns if c not in new_cols]
    df = df[existing_cols + new_cols]

    # 写回Excel（保持元数据sheet）
    metadata = updated_data.get("metadata", {})
    try:
        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="标注数据", index=False)
            if metadata:
                pd.DataFrame([metadata]).to_excel(writer, sheet_name="元数据", index=False)
    except Exception as exc:
        print(f"  ⚠️ 写回Excel失败: {excel_path} -> {exc}")
        return False

    print(f"  ✅ Excel已更新二次校验列: {excel_path}")
    return True


# ================================================================
# 4. 主流程
# ================================================================
def validate_single_file(json_path: str, llm_model) -> Tuple[Dict, Dict]:
    """对单个标注文件执行二次校验，返回(更新数据, 统计信息)"""
    original_data = load_json(json_path)
    samples = original_data.get("samples", [])

    total_samples = len(samples)
    print(f"  -> 待处理样本数: {total_samples}")

    max_samples = VALIDATION_CONFIG.get("MAX_SAMPLES_PER_FILE")
    if max_samples is not None and max_samples > 0 and max_samples < total_samples:
        samples = samples[:max_samples]
        print(f"  -> 已限制为前 {len(samples)} 条样本 (调试用)")
    effective_total = len(samples)

    file_stats = Counter()
    validated_samples = []

    for idx, sample in enumerate(samples, start=1):
        print(f"    [样本 {idx}/{effective_total}] 调用LLM复核...", end="", flush=True)
        result = call_llm_secondary_validation(
            llm_model=llm_model,
            paper_abstract=sample.get("paper_a_abstract", ""),
            paper_core_problem=sample.get("paper_a_core_problem", ""),
            solution_text=sample.get("solution_text", ""),
            first_label=sample.get("llm_classification", ""),
            first_reasoning=sample.get("llm_reasoning", ""),
        )

        verdict = result.get("verdict", "REVISE")
        secondary_label = result.get("secondary_classification", "NONE")

        file_stats["total"] += 1
        file_stats[f"verdict_{verdict}"] += 1
        file_stats[f"secondary_{secondary_label}"] += 1

        sample["llm_secondary_validation"] = result
        validated_samples.append(sample)
        print(f" 完成 -> verdict={verdict}, secondary={secondary_label}, confidence={result.get('confidence', 'UNKNOWN')}")

        sleep_seconds = VALIDATION_CONFIG.get("SLEEP_BETWEEN_CALLS", 0.0)
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    updated_data = {
        "metadata": original_data.get("metadata", {}),
        "samples": validated_samples,
        "llm_secondary_stats": {
            "total": file_stats["total"],
            "verdict_confirm": file_stats.get("verdict_CONFIRM", 0),
            "verdict_revise": file_stats.get("verdict_REVISE", 0),
            "secondary_INSPIRED": file_stats.get("secondary_INSPIRED", 0),
            "secondary_RELATED": file_stats.get("secondary_RELATED", 0),
            "secondary_NONE": file_stats.get("secondary_NONE", 0),
        },
    }
    return updated_data, updated_data["llm_secondary_stats"]


def run_secondary_validation():
    print("=" * 80)
    print("跨论文关系 LLM 二次校验 - 启动")
    print("=" * 80)

    llm_model = initialize_llm_model()
    print("✅ LLM模型已就绪")

    target_files = collect_annotation_files(VALIDATION_CONFIG["ANNOTATION_BASE_DIR"])
    print(f"共发现 {len(target_files)} 个待校验文件")

    # 确保输出目录存在
    os.makedirs(VALIDATION_CONFIG["OUTPUT_DIR"], exist_ok=True)

    overall_stats = Counter()
    per_file_summary = []

    for idx, json_path in enumerate(target_files, start=1):
        print(f"\n[{idx}/{len(target_files)}] 处理: {json_path}")
        updated_data, stats = validate_single_file(json_path, llm_model)

        rel_path = os.path.relpath(json_path, VALIDATION_CONFIG["ANNOTATION_BASE_DIR"])
        output_path = os.path.join(VALIDATION_CONFIG["OUTPUT_DIR"], rel_path)
        save_json(updated_data, output_path)
        print(f"  ✅ 校验结果已保存: {output_path}")

        # 同步写入Excel
        update_excel_with_secondary_results(json_path, updated_data)

        per_file_summary.append({
            "file": rel_path,
            "stats": stats,
        })

        overall_stats.update({
            "total": stats["total"],
            "verdict_confirm": stats["verdict_confirm"],
            "verdict_revise": stats["verdict_revise"],
            "secondary_INSPIRED": stats["secondary_INSPIRED"],
            "secondary_RELATED": stats["secondary_RELATED"],
            "secondary_NONE": stats["secondary_NONE"],
        })

    summary = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_files": len(target_files),
        "overall_stats": dict(overall_stats),
        "files": per_file_summary,
    }

    summary_path = os.path.join(VALIDATION_CONFIG["OUTPUT_DIR"], "llm_secondary_validation_summary.json")
    save_json(summary, summary_path)
    print("\n=" * 80)
    print("✅ 二次校验完成，汇总结果已生成")
    print(f"  -> {summary_path}")
    print("=" * 80)


if __name__ == "__main__":
    run_secondary_validation()
