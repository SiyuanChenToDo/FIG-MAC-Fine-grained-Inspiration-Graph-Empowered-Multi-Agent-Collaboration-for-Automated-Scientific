#!/usr/bin/env python3
"""
FIG-MAC Batch Runner with GLM-5 API (ZhipuAI)
批量运行 FIG-MAC 假设生成，使用 GLM-5 模型
"""

import asyncio
import json
import os
import sys
import time
import warnings
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# 路径处理
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# 设置 GLM-5 API 环境变量
GLM5_API_KEY = os.environ.get("ZHIPUAI_API_KEY", "your-api-key")  # 请填写您自己的 API Key
GLM5_BASE_URL = os.environ.get("ZHIPUAI_API_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")

os.environ["ZHIPUAI_API_KEY"] = GLM5_API_KEY
os.environ["ZHIPUAI_API_BASE_URL"] = GLM5_BASE_URL

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# 导入 FIG-MAC GLM-5 版本
sys.path.insert(0, str(PROJECT_ROOT / "Myexamples" / "kimi_batch_runner"))
from hypothesis_society_glm5 import HypothesisGenerationSociety
from camel.types import ModelType


class GLM5BatchRunner:
    """批量运行 FIG-MAC 假设生成"""
    
    def __init__(self, output_dir: str = "Myexamples/glm5_batch_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建结果子目录
        self.reports_dir = self.output_dir / "reports"
        self.reports_dir.mkdir(exist_ok=True)
        
        self.results_log = []
        
    async def run_single(
        self, 
        research_question: str, 
        question_id: str,
        max_iterations: int = 3,
        quality_threshold: float = 8.0
    ) -> Dict:
        """运行单个研究问题"""
        
        print(f"\n{'='*80}")
        print(f"Processing: {question_id}")
        print(f"Question: {research_question[:80]}...")
        print(f"{'='*80}")
        
        start_time = time.time()
        
        try:
            # 初始化 FIG-MAC
            society = HypothesisGenerationSociety()
            team = society.create_research_team()
            
            # 运行研究
            result = await society.run_research_async(
                research_question,
                max_iterations=max_iterations,
                quality_threshold=quality_threshold,
                polish_iterations=1
            )
            
            elapsed_time = time.time() - start_time
            
            # 获取生成的报告路径
            report_path = result.metadata.get("file_path", "")
            
            # 复制报告到输出目录
            final_report_path = ""
            if report_path and Path(report_path).exists():
                # 生成新的文件名
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_id = "".join(c for c in question_id if c.isalnum() or c == '_')[:50]
                new_filename = f"{timestamp}_{safe_id}.md"
                final_report_path = str(self.reports_dir / new_filename)
                
                # 复制文件
                import shutil
                shutil.copy2(report_path, final_report_path)
                print(f"✓ Report saved: {final_report_path}")
            
            # 记录结果
            result_record = {
                "question_id": question_id,
                "research_question": research_question,
                "success": not result.failed,
                "report_path": final_report_path,
                "original_path": report_path,
                "elapsed_time": elapsed_time,
                "timestamp": datetime.now().isoformat(),
                "metadata": result.metadata,
                "error": None if not result.failed else result.content
            }
            
            self.results_log.append(result_record)
            
            if result.failed:
                print(f"✗ Failed: {result.content[:200]}")
            else:
                print(f"✓ Success ({elapsed_time:.1f}s)")
                
            return result_record
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"✗ Exception: {e}")
            
            result_record = {
                "question_id": question_id,
                "research_question": research_question,
                "success": False,
                "report_path": "",
                "original_path": "",
                "elapsed_time": elapsed_time,
                "timestamp": datetime.now().isoformat(),
                "metadata": {},
                "error": str(e)
            }
            self.results_log.append(result_record)
            return result_record
    
    async def run_batch(
        self,
        questions_file: str,
        start_idx: int = 0,
        end_idx: Optional[int] = None,
        max_iterations: int = 3,
        quality_threshold: float = 8.0,
        delay_between: float = 2.0
    ):
        """批量运行研究问题"""
        
        # 加载问题列表
        with open(questions_file, 'r', encoding='utf-8') as f:
            questions = json.load(f)
        
        total = len(questions)
        end_idx = end_idx or total
        questions_to_run = questions[start_idx:end_idx]
        
        print(f"\n{'='*80}")
        print(f"FIG-MAC GLM-5 Batch Runner")
        print(f"{'='*80}")
        print(f"Total questions in file: {total}")
        print(f"Running: {start_idx} to {end_idx} ({len(questions_to_run)} questions)")
        print(f"Output directory: {self.output_dir}")
        print(f"Max iterations: {max_iterations}")
        print(f"Quality threshold: {quality_threshold}")
        print(f"{'='*80}\n")
        
        # 批量运行
        for i, item in enumerate(questions_to_run, start=start_idx):
            question_id = item.get("id", f"question_{i}")
            question_text = item.get("question", "")
            
            print(f"\n[{i+1}/{total}] Processing {question_id}")
            
            await self.run_single(
                research_question=question_text,
                question_id=question_id,
                max_iterations=max_iterations,
                quality_threshold=quality_threshold
            )
            
            # 保存进度
            self._save_progress()
            
            # 延迟避免 API 限制
            if i < len(questions_to_run) - 1:
                print(f"Waiting {delay_between}s before next...")
                await asyncio.sleep(delay_between)
        
        # 最终保存
        self._save_final_report()
        
    def _save_progress(self):
        """保存进度"""
        progress_file = self.output_dir / "progress.json"
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump({
                "completed": len(self.results_log),
                "results": self.results_log
            }, f, indent=2, ensure_ascii=False)
    
    def _save_final_report(self):
        """保存最终报告"""
        final_report = {
            "timestamp": datetime.now().isoformat(),
            "total_processed": len(self.results_log),
            "successful": sum(1 for r in self.results_log if r["success"]),
            "failed": sum(1 for r in self.results_log if not r["success"]),
            "results": self.results_log
        }
        
        report_file = self.output_dir / "final_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(final_report, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*80}")
        print(f"Batch processing complete!")
        print(f"Total: {final_report['total_processed']}")
        print(f"Successful: {final_report['successful']}")
        print(f"Failed: {final_report['failed']}")
        print(f"Report saved: {report_file}")
        print(f"{'='*80}")


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="FIG-MAC GLM-5 Batch Runner")
    parser.add_argument(
        "--questions-file",
        default="Myexamples/evaluation_system/batch_results/ours/all_research_questions.json",
        help="Path to research questions JSON file"
    )
    parser.add_argument(
        "--output-dir",
        default="Myexamples/glm5_batch_results",
        help="Output directory for results"
    )
    parser.add_argument(
        "--start-idx",
        type=int,
        default=0,
        help="Start index (0-based)"
    )
    parser.add_argument(
        "--end-idx",
        type=int,
        default=None,
        help="End index (exclusive)"
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=3,
        help="Max iterations for hypothesis generation"
    )
    parser.add_argument(
        "--quality-threshold",
        type=float,
        default=8.0,
        help="Quality threshold (1-10)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay between runs (seconds)"
    )
    
    args = parser.parse_args()
    
    runner = GLM5BatchRunner(output_dir=args.output_dir)
    
    await runner.run_batch(
        questions_file=args.questions_file,
        start_idx=args.start_idx,
        end_idx=args.end_idx,
        max_iterations=args.max_iterations,
        quality_threshold=args.quality_threshold,
        delay_between=args.delay
    )


if __name__ == "__main__":
    asyncio.run(main())
