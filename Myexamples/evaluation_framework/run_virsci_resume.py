#!/usr/bin/env python3
"""
断点续跑 Virsci 评估
从已完成的 10 个结果继续，完成剩余的 140 个
"""

import os
import sys
import json
import time
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from Myexamples.evaluation_framework.core.batch_evaluator import BatchEvaluator


def main():
    print("="*80)
    print("🚀 Virsci 评估断点续跑")
    print("="*80)
    
    # Setup environment
    if not os.environ.get("OPENAI_COMPATIBILITY_API_KEY"):
        os.environ["OPENAI_COMPATIBILITY_API_KEY"] = "sk-c1a6b588f7d543adb0412c5bc61bdd7b"
    if not os.environ.get("OPENAI_COMPATIBILITY_API_BASE_URL"):
        os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    os.environ["QWEN_API_KEY"] = os.environ["OPENAI_COMPATIBILITY_API_KEY"]
    os.environ["QWEN_API_BASE_URL"] = os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"]
    
    results_dir = "Myexamples/evaluation_framework/results_fixed"
    
    # Load existing virsci results
    virsci_file = os.path.join(results_dir, "virsci_raw_results.json")
    existing_results = []
    completed_files = set()
    
    if os.path.exists(virsci_file):
        with open(virsci_file, 'r', encoding='utf-8') as f:
            existing_results = json.load(f)
        completed_files = {r['file_path'] for r in existing_results if 'error' not in r}
        print(f"\n✓ 已加载 {len(existing_results)} 个已有结果")
        print(f"✓ 其中 {len(completed_files)} 个成功完成")
    else:
        print(f"\n⚠️ 未找到已有结果，将从头开始")
    
    # Get all virsci files
    virsci_dir = "Myexamples/evaluation_system/batch_results/virsci"
    import glob
    all_files = glob.glob(os.path.join(virsci_dir, "*.txt"))
    all_files = [f for f in all_files if "inspiration" not in os.path.basename(f).lower()]
    all_files = [f for f in all_files if os.path.dirname(f) == virsci_dir]
    all_files.sort()
    
    print(f"\n📊 文件统计:")
    print(f"   总文件数: {len(all_files)}")
    print(f"   已完成: {len(completed_files)}")
    print(f"   待处理: {len(all_files) - len(completed_files)}")
    
    # Filter out completed files
    pending_files = [f for f in all_files if f not in completed_files]
    
    if not pending_files:
        print("\n✅ 所有文件已完成！")
        return 0
    
    print(f"\n🎯 将处理 {len(pending_files)} 个待处理文件")
    
    # Initialize evaluator
    print("\n[Setup] Initializing evaluator...")
    evaluator = BatchEvaluator(
        vdb_path="Myexamples/vdb/camel_faiss_storage",
        csv_data_path="data/all_merged (1).csv",
        output_dir=results_dir,
    )
    print("  ✓ Evaluator initialized")
    
    # Process pending files
    print("\n" + "="*80)
    print("📊 Starting Evaluation (Resumed)")
    print("="*80)
    
    start_time = time.time()
    new_results = []
    
    for i, file_path in enumerate(pending_files, 1):
        print(f"\n[{i}/{len(pending_files)}] {os.path.basename(file_path)}")
        
        try:
            result = evaluator.evaluate_single(file_path, "virsci")
            new_results.append(result)
            
            # Save progress every 5 files
            if i % 5 == 0:
                all_results = existing_results + new_results
                with open(virsci_file, 'w', encoding='utf-8') as f:
                    json.dump(all_results, f, indent=2)
                print(f"  💾 进度已保存 ({len(existing_results) + i} 个完成)")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
            new_results.append({
                "file_path": file_path,
                "method": "virsci",
                "error": str(e),
            })
    
    # Final save
    all_results = existing_results + new_results
    with open(virsci_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2)
    
    elapsed = time.time() - start_time
    print("\n" + "="*80)
    print("✅ Virsci 评估完成!")
    print("="*80)
    print(f"\n本次处理: {len(new_results)} 个文件")
    print(f"总计完成: {len(all_results)} 个文件")
    print(f"用时: {elapsed // 60:.0f}m {elapsed % 60:.0f}s")
    print(f"\n结果保存: {virsci_file}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
