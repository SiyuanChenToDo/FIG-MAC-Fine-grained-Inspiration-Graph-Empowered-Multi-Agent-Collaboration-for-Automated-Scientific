#!/usr/bin/env python3
"""
FIG-MAC Batch Runner with Ollama Local Models
使用本地运行的开源模型（Llama、Qwen、Mistral 等）
完全免费，无需 API Key
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

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# Ollama 配置
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")

print(f"🔧 Ollama 配置:")
print(f"   地址: {OLLAMA_HOST}")
print(f"   模型: {OLLAMA_MODEL}")
print()

# 检查 Ollama 是否可用
try:
    import requests
    response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
    if response.status_code == 200:
        models = response.json().get("models", [])
        model_names = [m.get("name") for m in models]
        if OLLAMA_MODEL in model_names:
            print(f"✅ 模型 {OLLAMA_MODEL} 已就绪")
        else:
            print(f"⚠️  模型 {OLLAMA_MODEL} 未找到")
            print(f"   已安装模型: {', '.join(model_names) if model_names else '无'}")
            print(f"   请先拉取模型: ollama pull {OLLAMA_MODEL}")
            print()
    else:
        print(f"⚠️  Ollama 服务响应异常 (状态码: {response.status_code})")
except Exception as e:
    print(f"⚠️  无法连接到 Ollama 服务: {e}")
    print(f"   请确保 Ollama 正在运行: ollama serve")
    print()

# 导入 FIG-MAC
sys.path.insert(0, str(PROJECT_ROOT / "Myexamples" / "kimi_batch_runner"))
from hypothesis_society_ollama import HypothesisGenerationSociety


class OllamaBatchRunner:
    """批量运行 FIG-MAC 假设生成（使用 Ollama 本地模型）"""
    
    def __init__(self, model: str = OLLAMA_MODEL, output_dir: str = "Myexamples/ollama_batch_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建结果子目录
        self.reports_dir = self.output_dir / "reports"
        self.reports_dir.mkdir(exist_ok=True)
        
        self.results_log = []
        self.model = model
        
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
        print(f"Model: {self.model} (Ollama Local)")
        print(f"{'='*80}")
        
        start_time = time.time()
        
        try:
            # 初始化 FIG-MAC
            society = HypothesisGenerationSociety(model_name=self.model)
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
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_id = "".join(c for c in question_id if c.isalnum() or c == '_')[:50]
                new_filename = f"{timestamp}_{safe_id}.md"
                final_report_path = str(self.reports_dir / new_filename)
                
                import shutil
                shutil.copy2(report_path, final_report_path)
                print(f"✓ Report saved: {final_report_path}")
            
            result_record = {
                "question_id": question_id,
                "research_question": research_question,
                "success": not result.failed,
                "report_path": final_report_path,
                "original_path": report_path,
                "elapsed_time": elapsed_time,
                "timestamp": datetime.now().isoformat(),
                "metadata": result.metadata,
                "model": self.model,
                "platform": "ollama",
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
                "model": self.model,
                "platform": "ollama",
                "error": str(e)
            }
            self.results_log.append(result_record)
            return result_record
    
    async def run_batch(
        self,
        questions_file: str,
        start_idx: int = 0,
        end_idx: Optional[int] = None,
        max_iterations: int = 2,      # 减少迭代次数以节省内存
        quality_threshold: float = 7.5, # 稍微降低质量阈值
        delay_between: float = 15.0   # 增加间隔让模型释放内存
    ):
        """批量运行研究问题"""
        
        with open(questions_file, 'r', encoding='utf-8') as f:
            questions = json.load(f)
        
        total = len(questions)
        end_idx = end_idx or total
        questions_to_run = questions[start_idx:end_idx]
        
        print(f"\n{'='*80}")
        print(f"FIG-MAC Ollama Batch Runner")
        print(f"{'='*80}")
        print(f"Model: {self.model} (Local)")
        print(f"Total questions in file: {total}")
        print(f"Running: {start_idx} to {end_idx} ({len(questions_to_run)} questions)")
        print(f"Output directory: {self.output_dir}")
        print(f"Max iterations: {max_iterations}")
        print(f"Quality threshold: {quality_threshold}")
        print(f"{'='*80}\n")
        
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
            
            self._save_progress()
            
            if i < len(questions_to_run) - 1:
                print(f"Waiting {delay_between}s before next...")
                await asyncio.sleep(delay_between)
        
        self._save_final_report()
        
    def _save_progress(self):
        """保存进度"""
        progress_file = self.output_dir / "progress.json"
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump({
                "completed": len(self.results_log),
                "results": self.results_log,
                "model": self.model,
                "platform": "ollama"
            }, f, indent=2, ensure_ascii=False)
    
    def _save_final_report(self):
        """保存最终报告"""
        final_report = {
            "timestamp": datetime.now().isoformat(),
            "model": self.model,
            "platform": "ollama",
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
    
    parser = argparse.ArgumentParser(description="FIG-MAC Ollama Batch Runner")
    parser.add_argument(
        "--questions-file",
        default="Myexamples/evaluation_system/batch_results/ours/all_research_questions.json",
        help="Path to research questions JSON file"
    )
    parser.add_argument(
        "--output-dir",
        default="Myexamples/ollama_batch_results",
        help="Output directory for results"
    )
    parser.add_argument(
        "--model",
        default=OLLAMA_MODEL,
        help="Ollama model name (e.g., llama3.1:8b, qwen2.5:14b)"
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
        default=5.0,
        help="Delay between runs (seconds)"
    )
    
    args = parser.parse_args()
    
    runner = OllamaBatchRunner(model=args.model, output_dir=args.output_dir)
    
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
