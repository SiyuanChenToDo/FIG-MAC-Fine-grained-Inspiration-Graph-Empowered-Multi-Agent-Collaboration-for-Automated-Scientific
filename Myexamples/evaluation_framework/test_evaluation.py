#!/usr/bin/env python3
"""
FIG-MAC Evaluation Framework - Quick Test Script

Tests the evaluation pipeline on a small sample (3-5 files per method)
to verify functionality before full batch evaluation.

Usage:
    python test_evaluation.py [--methods ours ai_scientist ...] [--sample-size 3]
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Add project root to path
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


def find_sample_files(method_dir: str, method: str, sample_size: int = 3):
    """Find a small sample of files for testing."""
    import glob
    
    config = BatchEvaluator.METHOD_CONFIGS.get(method, {})
    pattern = os.path.join(method_dir, "**", config.get("file_pattern", "*.txt"))
    files = glob.glob(pattern, recursive=True)
    
    # Filter out inspiration reports
    files = [f for f in files if "inspiration" not in os.path.basename(f).lower()]
    
    return files[:sample_size]


def test_single_method(evaluator: BatchEvaluator, method: str, base_dir: str, sample_size: int):
    """Test evaluation on a single method with limited samples."""
    method_dir = os.path.join(base_dir, method)
    if not os.path.exists(method_dir):
        print(f"⚠️  Directory not found: {method_dir}")
        return None
    
    # Find sample files
    sample_files = find_sample_files(method_dir, method, sample_size)
    if not sample_files:
        print(f"⚠️  No files found for {method}")
        return None
    
    print(f"\n{'='*60}")
    print(f"🧪 Testing {method}: {len(sample_files)} files")
    print(f"{'='*60}")
    
    results = []
    for i, file_path in enumerate(sample_files, 1):
        print(f"\n[{i}/{len(sample_files)}] {os.path.basename(file_path)}")
        
        try:
            result = evaluator.evaluate_single(file_path, method)
            results.append(result)
            
            # Print quick summary
            if "error" not in result:
                novelty = result.get("metrics", {}).get("objective", {}).get("novelty", {})
                subjective = result.get("metrics", {}).get("subjective", {})
                
                print(f"  ✓ ON_raw: {novelty.get('ON_raw', 'N/A'):.4f}" if novelty.get('ON_raw') else "  ✓ ON_raw: N/A")
                
                if subjective:
                    nov_score = subjective.get('Novelty', 'N/A')
                    print(f"  ✓ LLM Novelty: {nov_score}/10")
                
                has_p = result.get("metrics", {}).get("objective", {}).get("provenance") is not None
                print(f"  ✓ Has P metric: {has_p}")
            else:
                print(f"  ✗ Error: {result.get('error', 'Unknown')}")
                
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            import traceback
            traceback.print_exc()
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Quick test of evaluation framework")
    parser.add_argument(
        "--methods",
        nargs="+",
        choices=["ours", "ai_scientist", "coi", "virsci"],
        default=["ours"],  # Just test "ours" by default
        help="Methods to test (default: ours only)"
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=2,
        help="Number of files to test per method (default: 2)"
    )
    parser.add_argument(
        "--results-dir",
        default="Myexamples/evaluation_system/batch_results",
        help="Base results directory"
    )
    parser.add_argument(
        "--csv-data",
        default="data/all_merged (1).csv",
        help="Path to metadata CSV"
    )
    parser.add_argument(
        "--vdb-path",
        default="Myexamples/vdb/camel_faiss_storage",
        help="Path to VDB"
    )
    
    args = parser.parse_args()
    
    print("="*70)
    print("🧪 FIG-MAC Evaluation Framework - Quick Test")
    print("="*70)
    print(f"\nConfiguration:")
    print(f"  Methods: {', '.join(args.methods)}")
    print(f"  Sample size: {args.sample_size} files per method")
    print(f"  CSV data: {args.csv_data}")
    
    # Validate paths
    if not os.path.exists(args.csv_data):
        alt_paths = [
            "/root/autodl-tmp/data/all_merged (1).csv",
            "data/all_merged (1).csv",
        ]
        for alt in alt_paths:
            if os.path.exists(alt):
                args.csv_data = alt
                print(f"  ✓ Found CSV at: {alt}")
                break
        else:
            print(f"❌ CSV file not found: {args.csv_data}")
            return 1
    else:
        print(f"  ✓ CSV file exists")
    
    if not os.path.exists(args.vdb_path):
        print(f"⚠️  VDB path not found: {args.vdb_path}")
        print(f"   (This is expected if not on target machine)")
    else:
        print(f"  ✓ VDB path exists")
    
    # Setup
    setup_environment()
    
    # Initialize evaluator
    print("\n[Setup] Initializing evaluator...")
    try:
        evaluator = BatchEvaluator(
            vdb_path=args.vdb_path,
            csv_data_path=args.csv_data,
            output_dir="Myexamples/evaluation_framework/results/test",
        )
        print("  ✓ Evaluator initialized")
    except Exception as e:
        print(f"  ✗ Failed to initialize evaluator: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Test each method
    all_results = {}
    for method in args.methods:
        results = test_single_method(evaluator, method, args.results_dir, args.sample_size)
        if results:
            all_results[method] = results
    
    # Summary
    print("\n" + "="*70)
    print("📊 Test Summary")
    print("="*70)
    
    for method, results in all_results.items():
        valid = [r for r in results if "error" not in r]
        errors = [r for r in results if "error" in r]
        
        print(f"\n{method}:")
        print(f"  Total: {len(results)}, Success: {len(valid)}, Errors: {len(errors)}")
        
        if valid:
            on_scores = [r["metrics"]["objective"]["novelty"]["ON_raw"] 
                        for r in valid 
                        if r.get("metrics", {}).get("objective", {}).get("novelty", {}).get("ON_raw")]
            if on_scores:
                import numpy as np
                print(f"  ON_raw: {np.mean(on_scores):.4f} ± {np.std(on_scores):.4f}")
            
            # Check P metric availability
            has_p = sum(1 for r in valid if r.get("metrics", {}).get("objective", {}).get("provenance") is not None)
            print(f"  Has P metric: {has_p}/{len(valid)}")
    
    # Save test results
    if all_results:
        output_file = "Myexamples/evaluation_framework/results/test/test_results.json"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2)
        print(f"\n💾 Test results saved to: {output_file}")
    
    print("\n" + "="*70)
    print("✅ Test Complete!")
    print("="*70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
