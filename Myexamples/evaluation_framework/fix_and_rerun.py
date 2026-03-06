#!/usr/bin/env python3
"""
Fix and re-run evaluation for methods with source extraction issues.

Usage:
    python fix_and_rerun.py --sample-size 10
"""

import os
import sys
import json
import time
import argparse

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def setup_env():
    if not os.environ.get("OPENAI_COMPATIBILITY_API_KEY"):
        os.environ["OPENAI_COMPATIBILITY_API_KEY"] = "sk-c1a6b588f7d543adb0412c5bc61bdd7b"
    if not os.environ.get("OPENAI_COMPATIBILITY_API_BASE_URL"):
        os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    os.environ["QWEN_API_KEY"] = os.environ["OPENAI_COMPATIBILITY_API_KEY"]
    os.environ["QWEN_API_BASE_URL"] = os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-size", type=int, default=10)
    parser.add_argument("--methods", nargs="+", default=["ours", "coi"], choices=["ours", "ai_scientist", "coi", "virsci"])
    args = parser.parse_args()
    
    print("="*70)
    print("🔄 Re-running evaluation with fixed source extraction")
    print("="*70)
    print(f"Methods: {', '.join(args.methods)}")
    print(f"Sample size: {args.sample_size}")
    
    setup_env()
    
    # Delay import to ensure env is set
    from Myexamples.evaluation_framework.core.batch_evaluator import BatchEvaluator
    
    evaluator = BatchEvaluator(
        vdb_path="Myexamples/vdb/camel_faiss_storage",
        csv_data_path="data/all_merged (1).csv",
        output_dir="Myexamples/evaluation_framework/results",
    )
    
    # Load existing results for methods not being re-evaluated
    all_results = {}
    
    # Load existing results
    for method in ["ours", "ai_scientist", "coi", "virsci"]:
        if method not in args.methods:
            result_file = f"Myexamples/evaluation_framework/results/{method}_raw_results.json"
            if os.path.exists(result_file):
                with open(result_file, 'r') as f:
                    all_results[method] = json.load(f)
                print(f"✅ Loaded existing {method}: {len(all_results[method])} records")
    
    # Re-evaluate specified methods
    for method in args.methods:
        print(f"\n{'='*70}")
        print(f"📊 Evaluating {method}")
        print(f"{'='*70}")
        
        method_dir = f"Myexamples/evaluation_system/batch_results/{method}"
        if method == "ours":
            method_dir = os.path.join(method_dir, "reports")
        
        if not os.path.exists(method_dir):
            print(f"⚠️ Directory not found: {method_dir}")
            continue
        
        results = evaluator.evaluate_method(method_dir, method, max_samples=args.sample_size)
        all_results[method] = results
        
        # Save
        output_file = f"Myexamples/evaluation_framework/results/{method}_raw_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        print(f"💾 Saved to {output_file}")
        
        # Verify sources
        valid = [r for r in results if "error" not in r]
        has_sources = sum(1 for r in valid if r.get("has_sources"))
        has_p = sum(1 for r in valid if r.get("metrics", {}).get("objective", {}).get("provenance", {}).get("P") is not None)
        print(f"✓ Valid: {len(valid)}, Has sources: {has_sources}, Has P: {has_p}")
    
    # Re-normalize and regenerate report
    print("\n" + "="*70)
    print("📈 Re-normalizing ON scores")
    print("="*70)
    
    normalized = evaluator.normalize_all_on_scores(all_results)
    
    print("\n" + "="*70)
    print("📋 Generating updated report")
    print("="*70)
    
    summary = evaluator.aggregate_statistics(normalized)
    report = evaluator.generate_comparison_report(normalized)
    
    # Print summary
    print("\n" + "="*70)
    print("📊 Updated Results Summary")
    print("="*70)
    print(f"\n{'Method':<20} {'N':<6} {'ON':<12} {'P':<12} {'Sources%':<10}")
    print("-"*70)
    
    for method, stats in summary.get("methods", {}).items():
        name = stats.get("name", method)[:18]
        count = stats['count']
        on = stats.get("ON_mean", 0)
        on_str = f"{on:.3f}" if on else "N/A"
        p = stats.get("P_mean")
        p_str = f"{p:.3f}" if p else "N/A"
        src_pct = stats.get("has_sources_pct", 0)
        print(f"{name:<20} {count:<6} {on_str:<12} {p_str:<12} {src_pct:.0f}%")
    
    print("="*70)
    print("✅ Done! Check comparison_report.md for full results")
    print("="*70)


if __name__ == "__main__":
    main()
