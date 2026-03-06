#!/usr/bin/env python3
"""
Re-evaluate existing results with fixed source extraction for 'ours' method.

This script re-runs evaluation for the 'ours' method only, with improved
source extraction from the report Background sections.

Usage:
    python reEvaluate_fix_sources.py --sample-size 10
"""

import os
import sys
import json
import argparse

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from Myexamples.evaluation_framework.core.batch_evaluator import BatchEvaluator


def setup_environment():
    """Setup API keys."""
    if not os.environ.get("OPENAI_COMPATIBILITY_API_KEY"):
        os.environ["OPENAI_COMPATIBILITY_API_KEY"] = "sk-c1a6b588f7d543adb0412c5bc61bdd7b"
    if not os.environ.get("OPENAI_COMPATIBILITY_API_BASE_URL"):
        os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    os.environ["QWEN_API_KEY"] = os.environ["OPENAI_COMPATIBILITY_API_KEY"]
    os.environ["QWEN_API_BASE_URL"] = os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"]


def main():
    parser = argparse.ArgumentParser(description="Re-evaluate 'ours' method with fixed source extraction")
    parser.add_argument("--sample-size", type=int, default=10, help="Number of samples")
    parser.add_argument("--output-dir", default="Myexamples/evaluation_framework/results", help="Output directory")
    args = parser.parse_args()
    
    print("="*70)
    print("🔄 Re-evaluating 'ours' method with fixed source extraction")
    print("="*70)
    
    setup_environment()
    
    # Check for existing results
    existing_results_path = os.path.join(args.output_dir, "ai_scientist_raw_results.json")
    if os.path.exists(existing_results_path):
        print(f"\n✓ Found existing results in: {args.output_dir}")
        with open(existing_results_path, 'r') as f:
            existing = json.load(f)
        print(f"  Existing ai_scientist results: {len(existing)} files")
    
    # Initialize evaluator
    print("\n[Setup] Initializing evaluator...")
    evaluator = BatchEvaluator(
        vdb_path="Myexamples/vdb/camel_faiss_storage",
        csv_data_path="data/all_merged (1).csv",
        output_dir=args.output_dir,
    )
    
    # Evaluate only 'ours' method
    print("\n" + "="*70)
    print("📊 Evaluating 'ours' method with fixed source extraction")
    print("="*70)
    
    method_dir = "Myexamples/evaluation_system/batch_results/ours/reports"
    
    if not os.path.exists(method_dir):
        print(f"❌ Directory not found: {method_dir}")
        return 1
    
    results = evaluator.evaluate_method(method_dir, "ours", max_samples=args.sample_size)
    
    # Save results
    output_file = os.path.join(args.output_dir, "ours_raw_results.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Saved to: {output_file}")
    
    # Check results
    print("\n" + "="*70)
    print("📋 Verification")
    print("="*70)
    
    valid_results = [r for r in results if "error" not in r]
    has_sources = sum(1 for r in valid_results if r.get("has_sources"))
    has_p = sum(1 for r in valid_results 
                if r.get("metrics", {}).get("objective", {}).get("provenance", {}).get("P") is not None)
    
    print(f"Total evaluated: {len(results)}")
    print(f"Successful: {len(valid_results)}")
    print(f"Has sources: {has_sources}/{len(valid_results)}")
    print(f"Has P metric: {has_p}/{len(valid_results)}")
    
    if valid_results:
        import numpy as np
        p_scores = [r["metrics"]["objective"]["provenance"]["P"] 
                   for r in valid_results 
                   if r.get("metrics", {}).get("objective", {}).get("provenance", {}).get("P")]
        if p_scores:
            print(f"P scores: {np.mean(p_scores):.4f} ± {np.std(p_scores):.4f}")
    
    print("\n✅ Re-evaluation complete!")
    print(f"\nNext step: Re-run full comparison with:")
    print(f"  python Myexamples/evaluation_framework/run_batch_evaluation.py --sample-size {args.sample_size}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
