#!/usr/bin/env python3
"""
批量运行科学假设生成系统，遍历迭代次数与润色轮数组合，并将最终评估得分汇总到 Excel。

功能概述：
1. 对指定的 10 个主题，逐一运行 `HypothesisGenerationSociety`。
2. 对每个主题执行 `max_iterations` ∈ {1,2,3} 与 `polish_iterations` ∈ {1,2,3} 的网格搜索。
3. 收集每次运行的关键元数据（集成得分、外部评分、报告路径等）。
4. 生成包含所有运行记录的 Excel 文件，便于分析比较。

使用示例：
    python Myexamples/test_mutiagent/batch_parameter_search.py \
        --topics-file Myexamples/test_mutiagent/topics.txt \
        --quality-threshold 9.5 \
        --output-dir Myexamples/evaluation_system/batch_results

若未提供 `--topics-file`，脚本将使用内置的 10 个示例主题。
"""

import argparse
import itertools
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Union

try:
    import pandas as pd
except ImportError as exc:  # pragma: no cover
    raise SystemExit("需要先安装 pandas 才能运行批量参数搜索脚本。请执行 pip install pandas") from exc

# 将项目根目录加入 sys.path，确保可导入项目内模块
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Myexamples.test_mutiagent.hypothesis_society_demo import HypothesisGenerationSociety  # noqa: E402


def load_topics(topics_file: Union[str, None]) -> List[Dict[str, Any]]:
    """从文件或内置列表加载 10 个研究主题。

    返回的每个元素均为包含 `id` 与 `question` 字段的字典，便于后续记录。
    """
    if topics_file:
        path = Path(topics_file)
        if not path.exists():
            raise FileNotFoundError(f"未找到主题文件: {topics_file}")

        if path.suffix.lower() == ".json":
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                raise ValueError(f"JSON 文件 {topics_file} 格式错误，应为数组")
            topics: List[Dict[str, Any]] = []
            for idx, item in enumerate(data):
                if not isinstance(item, dict) or "question" not in item:
                    raise ValueError(f"JSON 第 {idx + 1} 条缺少 question 字段")
                topics.append({
                    "id": item.get("id") or f"topic_{idx+1}",
                    "question": item["question"],
                    "simplified": item.get("simplified"),
                    "source_id": item.get("source_id"),
                })
            if len(topics) < 10:
                raise ValueError(f"JSON 文件 {topics_file} 中的主题数量不足 10 个")
            return topics[:10]

        # 普通文本文件：每行一个主题
        with path.open("r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        if len(lines) < 10:
            raise ValueError(f"主题文件 {topics_file} 中的主题数量不足 10 个")
        topics: List[Dict[str, Any]] = []
        for idx, line in enumerate(lines[:10]):
            topics.append({
                "id": f"topic_{idx+1}",
                "question": line,
                "simplified": None,
                "source_id": None,
            })
        return topics

    # 默认主题列表，可根据需要自行调整
    default_questions = [
        "Microbiome-Brain Communication and Neuroplasticity",
        "Quantum Error Correction for Near-Term Noise Models",
        "Counterfactual Domain Adaptation for Informal Language Translation",
        "Multi-task Learning with Dynamic Gating Mechanisms",
        "Explainable AI for Clinical Decision Support",
        "Energy-efficient Federated Learning for IoT Devices",
        "Adaptive Graph Neural Networks for Knowledge Discovery",
        "High-throughput Materials Discovery via Generative Models",
        "Robust Reinforcement Learning under Distribution Shift",
        "Autonomous Laboratory Systems for Hypothesis Generation",
    ]
    topics = []
    for idx, question in enumerate(default_questions):
        topics.append({
            "id": f"default_topic_{idx+1}",
            "question": question,
            "simplified": None,
            "source_id": None,
        })
    return topics


def ensure_output_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def flatten_dict(prefix: str, data: Dict[str, Any], out: Dict[str, Any]) -> None:
    """将嵌套字典展开为扁平键，方便写入表格。"""
    for key, value in data.items():
        flat_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flatten_dict(flat_key, value, out)
        else:
            out[flat_key] = value


def run_single_experiment(topic: str, max_iterations: int, polish_iterations: int,
                           quality_threshold: float, topic_meta: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """执行一次假设生成实验并返回记录。"""
    society = HypothesisGenerationSociety()
    topic_meta = topic_meta or {}
    record: Dict[str, Any] = {
        "topic": topic,
        "topic_id": topic_meta.get("id"),
        "topic_simplified": topic_meta.get("simplified"),
        "topic_source_id": topic_meta.get("source_id"),
        "max_iterations": max_iterations,
        "polish_iterations": polish_iterations,
        "quality_threshold": quality_threshold,
        "timestamp": datetime.now().isoformat(),
    }

    try:
        result = society.run_research(
            research_topic=topic,
            max_iterations=max_iterations,
            quality_threshold=quality_threshold,
            polish_iterations=polish_iterations,
        )
        record["success"] = not result.failed
        metadata = result.metadata if hasattr(result, "metadata") and isinstance(result.metadata, dict) else {}
        record["report_path"] = metadata.get("file_path")
        record["polish_rounds_completed"] = metadata.get("polish_rounds_completed")
        record["integrated_score"] = metadata.get("integrated_score")
        record["external_rating"] = metadata.get("external_rating")

        final_eval = metadata.get("final_evaluation")
        if isinstance(final_eval, dict):
            record["final_rating"] = final_eval.get("final_rating")
            record["final_total_score"] = final_eval.get("total_score")

        evaluation_metadata = metadata.get("evaluation_metadata")
        if isinstance(evaluation_metadata, dict):
            flat_eval: Dict[str, Any] = {}
            flatten_dict("evaluation", evaluation_metadata, flat_eval)
            record.update(flat_eval)

        record["raw_metadata_json"] = json.dumps(metadata, ensure_ascii=False)

    except Exception as exc:  # pragma: no cover
        record["success"] = False
        record["error"] = str(exc)

    return record


def main() -> None:
    parser = argparse.ArgumentParser(description="批量运行科学假设生成并汇总评分")
    parser.add_argument("--topics-file", type=str, default=None,
                        help="包含至少 10 个主题的文本文件，每行一个主题")
    parser.add_argument("--quality-threshold", type=float, default=8.5,
                        help="评审阶段质量阈值，默认为 8.5")
    parser.add_argument("--output-dir", type=str, default="Myexamples/evaluation_system/batch_results",
                        help="结果输出目录")
    parser.add_argument("--excel-name", type=str, default=None,
                        help="输出 Excel 文件名（可选，若未提供将自动生成带时间戳的文件名）")
    args = parser.parse_args()

    topics = load_topics(args.topics_file)
    output_dir = ensure_output_dir(Path(args.output_dir))

    iteration_values = [1, 2, 3]
    polish_values = [1, 2, 3]

    records: List[Dict[str, Any]] = []

    total_tasks = len(topics) * len(iteration_values) * len(polish_values)
    print("=" * 80)
    print(f"批量参数搜索启动，共 {total_tasks} 次运行")
    print("=" * 80)

    counter = 0
    for topic_idx, topic_entry in enumerate(topics, start=1):
        question_text = topic_entry.get("question") if isinstance(topic_entry, dict) else str(topic_entry)
        topic_identifier = topic_entry.get("id") if isinstance(topic_entry, dict) else None
        print(f"\n>>> 处理主题 {topic_idx}/ {len(topics)}: {question_text}")
        for max_iterations, polish_iterations in itertools.product(iteration_values, polish_values):
            counter += 1
            print(f"  - 运行组合 {counter}/{total_tasks}: max_iter={max_iterations}, polish_iter={polish_iterations}")
            record = run_single_experiment(
                topic=question_text,
                max_iterations=max_iterations,
                polish_iterations=polish_iterations,
                quality_threshold=args.quality_threshold,
                topic_meta=topic_entry if isinstance(topic_entry, dict) else None,
            )
            record["topic_index"] = topic_idx
            records.append(record)

    if not records:
        print("未生成任何记录，退出。")
        return

    df = pd.DataFrame(records)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_name = args.excel_name or f"batch_scores_{timestamp}.xlsx"
    excel_path = output_dir / excel_name

    df.to_excel(excel_path, index=False)
    print("\n" + "=" * 80)
    print(f"批量运行完成，结果已保存至: {excel_path}")
    print("记录条目数: ", len(df))
    print("成功次数: ", int(df["success"].sum() if "success" in df else 0))
    print("=" * 80)


if __name__ == "__main__":
    main()
