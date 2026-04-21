#!/usr/bin/env python3
"""
完整流程脚本：
1. 抽取 140 条新的研究问题（加上已有的 10 条共 150 条）
2. 使用最佳参数 (2,2) 生成科学假说报告
3. 评估所有报告并生成结果表

使用示例：
    python generate_ours_results.py \
        --num_new_samples 140 \
        --output_dir Myexamples/evaluation_system/batch_results/ours \
        --max_iterations 2 \
        --polish_iterations 2
"""

import os
import sys
import json
import random
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# 设置环境变量
os.environ['PYTHONUNBUFFERED'] = '1'

# 将项目根目录加入 sys.path
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Myexamples.evaluation_system.batch_evaluation_tools.sample_and_evaluate import load_research_questions, sample_research_questions
from Myexamples.test_mutiagent.hypothesis_society_demo import HypothesisGenerationSociety


def load_existing_questions(existing_file: str) -> List[Dict[str, Any]]:
    """加载已有的采样研究问题"""
    if os.path.exists(existing_file):
        print(f"✅ 加载已有的研究问题: {existing_file}")
        with open(existing_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def generate_new_questions(num_new: int, existing_questions: List[Dict[str, Any]], 
                          vdb_path: str, json_data_path: str) -> List[Dict[str, Any]]:
    """生成新的研究问题（避免与已有的重复）"""
    print(f"\n📚 加载所有研究问题数据库...")
    all_questions = load_research_questions(vdb_path, json_data_path)
    
    if not all_questions:
        print("❌ 无法加载研究问题数据库")
        return []
    
    # 获取已有问题的集合
    existing_ids = {q['id'] for q in existing_questions}
    existing_texts = {q['question'] for q in existing_questions}
    
    # 过滤出新的问题
    new_candidates = [q for q in all_questions 
                      if q['id'] not in existing_ids and q['question'] not in existing_texts]
    
    print(f"  总问题数: {len(all_questions)}")
    print(f"  已有问题数: {len(existing_questions)}")
    print(f"  新候选问题数: {len(new_candidates)}")
    
    if len(new_candidates) < num_new:
        print(f"⚠️ 新候选问题数 ({len(new_candidates)}) 少于需求数 ({num_new})")
        num_new = len(new_candidates)
    
    # 随机采样新问题
    print(f"\n🎲 随机采样 {num_new} 个新研究问题...")
    random.seed(42)
    new_questions = random.sample(new_candidates, num_new)
    
    return new_questions


def run_hypothesis_generation(questions: List[Dict[str, Any]], 
                             output_dir: Path,
                             max_iterations: int = 2,
                             polish_iterations: int = 2,
                             quality_threshold: float = 8.5) -> List[Dict[str, Any]]:
    """运行假说生成系统"""
    print(f"\n{'='*80}")
    print(f"🚀 开始生成科学假说报告 (max_iter={max_iterations}, polish_iter={polish_iterations})")
    print(f"{'='*80}")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    
    for idx, q in enumerate(questions, 1):
        print(f"\n[{idx}/{len(questions)}] 处理研究问题: {q['question'][:60]}...")
        
        try:
            society = HypothesisGenerationSociety()
            result = society.run_research(
                research_topic=q['question'],
                max_iterations=max_iterations,
                quality_threshold=quality_threshold,
                polish_iterations=polish_iterations,
            )
            
            metadata = result.metadata if hasattr(result, "metadata") and isinstance(result.metadata, dict) else {}
            report_path = metadata.get("file_path")
            
            # 如果报告在默认位置，复制到我们的输出目录
            if report_path and os.path.exists(report_path):
                import shutil
                report_name = os.path.basename(report_path)
                new_report_path = output_dir / report_name
                shutil.copy(report_path, new_report_path)
                report_path = str(new_report_path)
                print(f"  ✅ 报告已保存: {report_name}")
            
            record = {
                "question_id": q.get('id', ''),
                "question": q['question'],
                "report_path": report_path,
                "success": not result.failed,
                "max_iterations": max_iterations,
                "polish_iterations": polish_iterations,
                "timestamp": datetime.now().isoformat(),
            }
            
            if isinstance(metadata, dict):
                record["integrated_score"] = metadata.get("integrated_score")
                record["external_rating"] = metadata.get("external_rating")
            
            records.append(record)
            
        except Exception as e:
            print(f"  ❌ 错误: {e}")
            records.append({
                "question_id": q.get('id', ''),
                "question": q['question'],
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            })
    
    return records


def save_results(existing_questions: List[Dict[str, Any]],
                new_questions: List[Dict[str, Any]],
                generation_records: List[Dict[str, Any]],
                output_dir: Path):
    """保存所有结果"""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存所有研究问题（已有 + 新的）
    all_questions = existing_questions + new_questions
    questions_file = output_dir / "all_research_questions.json"
    with open(questions_file, 'w', encoding='utf-8') as f:
        json.dump(all_questions, f, ensure_ascii=False, indent=2)
    print(f"✅ 已保存所有研究问题: {questions_file}")
    
    # 保存生成记录
    records_file = output_dir / "generation_records.json"
    with open(records_file, 'w', encoding='utf-8') as f:
        json.dump(generation_records, f, ensure_ascii=False, indent=2)
    print(f"✅ 已保存生成记录: {records_file}")
    
    # 统计信息
    print(f"\n📊 生成统计:")
    print(f"  总研究问题数: {len(all_questions)}")
    print(f"  成功生成报告数: {sum(1 for r in generation_records if r.get('success'))}")
    print(f"  失败数: {sum(1 for r in generation_records if not r.get('success'))}")


def main():
    parser = argparse.ArgumentParser(description="生成 OURS 方法的结果")
    parser.add_argument("--num_new_samples", type=int, default=140,
                       help="新采样的研究问题数")
    parser.add_argument("--existing_file", type=str, 
                       default="Myexamples/evaluation_system/batch_results/sampled_research_questions.json",
                       help="已有研究问题文件")
    parser.add_argument("--output_dir", type=str,
                       default="Myexamples/evaluation_system/batch_results/ours",
                       help="输出目录")
    parser.add_argument("--vdb_path", type=str,
                       default="Myexamples/data/final_data",
                       help="VDB 数据路径")
    parser.add_argument("--json_data_path", type=str,
                       default="Myexamples/data/final_data/final_custom_kg_papers.json",
                       help="JSON 数据路径")
    parser.add_argument("--max_iterations", type=int, default=2,
                       help="最大迭代次数")
    parser.add_argument("--polish_iterations", type=int, default=2,
                       help="润色轮数")
    parser.add_argument("--quality_threshold", type=float, default=8.5,
                       help="质量阈值")
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    
    print("="*80)
    print("🎯 OURS 方法结果生成流程")
    print("="*80)
    
    # 步骤 1: 加载已有的研究问题
    print("\n[步骤 1] 加载已有的研究问题...")
    existing_questions = load_existing_questions(args.existing_file)
    print(f"✅ 已加载 {len(existing_questions)} 个已有问题")
    
    # 步骤 2: 生成新的研究问题
    print("\n[步骤 2] 生成新的研究问题...")
    new_questions = generate_new_questions(
        args.num_new_samples,
        existing_questions,
        args.vdb_path,
        args.json_data_path
    )
    print(f"✅ 生成了 {len(new_questions)} 个新问题")
    
    # 步骤 3: 运行假说生成系统
    print("\n[步骤 3] 运行假说生成系统...")
    generation_records = run_hypothesis_generation(
        new_questions,
        output_dir / "reports",
        args.max_iterations,
        args.polish_iterations,
        args.quality_threshold
    )
    print(f"✅ 完成假说生成")
    
    # 步骤 4: 保存结果
    print("\n[步骤 4] 保存结果...")
    save_results(existing_questions, new_questions, generation_records, output_dir)
    
    print("\n" + "="*80)
    print("✅ OURS 方法结果生成完成！")
    print("="*80)
    print(f"输出目录: {output_dir}")
    print(f"报告目录: {output_dir / 'reports'}")


if __name__ == "__main__":
    main()
