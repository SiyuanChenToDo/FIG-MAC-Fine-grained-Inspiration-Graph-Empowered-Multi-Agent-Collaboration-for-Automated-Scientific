#!/usr/bin/env python3
"""
运行全部 150 个研究问题 - Ollama Mixtral 8x7B
带有内存优化和错误恢复
"""

import asyncio
import json
import os
import sys
import time
import gc
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# 配置
MODEL = "mixtral:8x7b"
QUESTIONS_FILE = "Myexamples/evaluation_system/batch_results/ours/all_research_questions.json"
OUTPUT_DIR = "Myexamples/ollama_batch_results"
BATCH_SIZE = 5  # 每批处理 5 个，然后休息
REST_TIME = 30  # 每批之间休息 30 秒

def log_memory():
    """记录内存使用情况"""
    try:
        import psutil
        mem = psutil.virtual_memory()
        print(f"💾 内存使用: {mem.percent}% | 可用: {mem.available / (1024**3):.1f} GB")
    except:
        pass

async def main():
    from ollama_batch_runner import OllamaBatchRunner
    
    # 加载问题列表
    with open(QUESTIONS_FILE, 'r', encoding='utf-8') as f:
        questions = json.load(f)
    
    total = len(questions)
    print("=" * 80)
    print("🔬 FIG-MAC Ollama Batch Runner - 150 Questions")
    print("=" * 80)
    print(f"Model: {MODEL}")
    print(f"Total Questions: {total}")
    print(f"Batch Size: {BATCH_SIZE}")
    print(f"Rest Time: {REST_TIME}s between batches")
    print("=" * 80)
    print()
    
    log_memory()
    
    # 分批处理
    for batch_start in range(0, total, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total)
        
        print(f"\n{'='*80}")
        print(f"📦 Processing Batch: {batch_start+1} - {batch_end} / {total}")
        print(f"{'='*80}\n")
        
        runner = OllamaBatchRunner(
            model=MODEL,
            output_dir=OUTPUT_DIR
        )
        
        try:
            await runner.run_batch(
                questions_file=QUESTIONS_FILE,
                start_idx=batch_start,
                end_idx=batch_end,
                max_iterations=2,
                quality_threshold=7.5,
                delay_between=10
            )
            
            print(f"\n✅ Batch {batch_start+1}-{batch_end} completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Batch {batch_start+1}-{batch_end} failed: {e}")
            print("   Continuing to next batch...")
        
        # 强制垃圾回收
        gc.collect()
        log_memory()
        
        # 休息一段时间，让系统释放内存
        if batch_end < total:
            print(f"\n😴 Resting for {REST_TIME}s to free up memory...")
            await asyncio.sleep(REST_TIME)
    
    print("\n" + "=" * 80)
    print("🎉 All batches completed!")
    print("=" * 80)
    print(f"Results saved to: {OUTPUT_DIR}/")
    print()

if __name__ == "__main__":
    asyncio.run(main())
