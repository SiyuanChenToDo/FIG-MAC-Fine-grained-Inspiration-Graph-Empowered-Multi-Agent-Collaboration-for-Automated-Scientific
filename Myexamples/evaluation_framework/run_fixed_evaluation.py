#!/usr/bin/env python3
"""
FIG-MAC Evaluation Framework - Fixed ON_v3 Evaluation Runner

Runs evaluation with corrected metrics:
1. HD: Now uses MAXIMUM dissimilarity (true historical divergence)
2. CI: Uses citation percentile rank (eliminates year bias)
3. ON_raw: Linear formula without log compression

Usage:
    python run_fixed_evaluation.py --sample-size 10
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def setup_environment():
    """Setup API keys from environment or config."""
    if not os.environ.get("OPENAI_COMPATIBILITY_API_KEY"):
        os.environ["OPENAI_COMPATIBILITY_API_KEY"] = "sk-c1a6b588f7d543adb0412c5bc61bdd7b"
    if not os.environ.get("OPENAI_COMPATIBILITY_API_BASE_URL"):
        os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    os.environ["QWEN_API_KEY"] = os.environ["OPENAI_COMPATIBILITY_API_KEY"]
    os.environ["QWEN_API_BASE_URL"] = os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"]


def main():
    parser = argparse.ArgumentParser(
        description="FIG-MAC Evaluation with FIXED ON_v3 Metrics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
CHANGES FROM ON_v2:
  1. HD: Uses MAXIMUM dissimilarity (not minimum) - measures true historical divergence
  2. CI: Uses citation percentile rank (not year-normalized) - eliminates temporal bias
  3. ON_raw: Linear formula without log compression - respects citation differences
  4. K: Increased from 5 to 10 for more stable estimates

Examples:
  # Evaluate all methods with fixed metrics (all files)
  python run_fixed_evaluation.py
  
  # Evaluate with limited samples (for quick testing)
  python run_fixed_evaluation.py --sample-size 10
  
  # Evaluate specific methods
  python run_fixed_evaluation.py --methods ours ai_scientist
        """
    )
    
    parser.add_argument(
        "--methods",
        nargs="+",
        choices=["ours", "ai_scientist", "coi", "virsci"],
        default=["ours", "ai_scientist", "coi", "virsci"],
        help="Methods to evaluate (default: all)"
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=None,
        help="Number of files to evaluate per method (default: None = all files)"
    )
    parser.add_argument(
        "--results-dir",
        default="Myexamples/evaluation_system/batch_results",
        help="Base directory containing method subdirectories"
    )
    parser.add_argument(
        "--csv-data",
        default="data/all_merged (1).csv",
        help="Path to metadata CSV"
    )
    parser.add_argument(
        "--vdb-path",
        default="Myexamples/vdb/camel_faiss_storage",
        help="Path to FAISS vector database"
    )
    parser.add_argument(
        "--output-dir",
        default="Myexamples/evaluation_framework/results_fixed",
        help="Output directory for evaluation results"
    )
    
    args = parser.parse_args()
    
    # Validate CSV path
    if not os.path.exists(args.csv_data):
        alt_paths = [
            "/root/autodl-tmp/data/all_merged (1).csv",
            "data/all_merged (1).csv",
        ]
        for alt in alt_paths:
            if os.path.exists(alt):
                args.csv_data = alt
                break
        else:
            print(f"❌ CSV file not found: {args.csv_data}")
            return 1
    
    # Setup
    print("="*80)
    print("🚀 FIG-MAC Evaluation with FIXED ON_v3 Metrics")
    print("="*80)
    print("\nFIXES APPLIED:")
    print("  1. HD: Uses MAXIMUM dissimilarity (true historical divergence)")
    print("  2. CI: Uses citation percentile rank (eliminates year bias)")
    print("  3. ON_raw: Linear formula without log compression")
    print("  4. K: Increased from 5 to 10 for stability")
    
    print(f"\nConfiguration:")
    print(f"  Methods: {', '.join(args.methods)}")
    print(f"  Sample size: {args.sample_size if args.sample_size else 'All files (no limit)'}")
    print(f"  CSV data: {args.csv_data}")
    print(f"  Output: {args.output_dir}")
    
    setup_environment()
    
    # Import after env setup
    from Myexamples.evaluation_framework.core.batch_evaluator import BatchEvaluator
    
    # Initialize evaluator
    print("\n[Setup] Initializing evaluator...")
    start_time = time.time()
    
    evaluator = BatchEvaluator(
        vdb_path=args.vdb_path,
        csv_data_path=args.csv_data,
        output_dir=args.output_dir,
    )
    print("  ✓ Evaluator initialized")
    
    # Run evaluation
    print("\n" + "="*80)
    print("📊 Starting Evaluation with Fixed Metrics")
    print("="*80)
    
    all_results = evaluator.evaluate_all_methods(
        base_results_dir=args.results_dir,
        methods=args.methods,
        max_samples=args.sample_size
    )
    
    # Normalize ON scores
    print("\n" + "="*80)
    print("📈 Normalizing ON Scores")
    print("="*80)
    normalized_results = evaluator.normalize_all_on_scores(all_results)
    
    # Generate statistics
    print("\n" + "="*80)
    print("📋 Generating Statistics")
    print("="*80)
    summary = evaluator.aggregate_statistics(normalized_results)
    
    # Generate report
    print("\n" + "="*80)
    print("📝 Generating Report")
    print("="*80)
    report = evaluator.generate_comparison_report(normalized_results)
    
    # Print summary
    total_time = time.time() - start_time
    
    print("\n" + "="*80)
    print("✅ Evaluation Complete!")
    print("="*80)
    print(f"\nTotal time: {total_time // 60:.0f}m {total_time % 60:.0f}s")
    print(f"\nResults saved to: {args.output_dir}")
    
    print("\n" + "="*80)
    print("📊 COMPARISON: ON_v2 vs ON_v3 (Expected Changes)")
    print("="*80)
    print("""
METRIC     | ON_v2 (Old)        | ON_v3 (Fixed)          | Impact
-----------|--------------------|------------------------|------------------
HD         | mean(min-K)        | mean(max-K)            | ↑ Higher scores
CD         | mean(min-K)        | mean(min-K)            | No change
CI         | year-normalized    | percentile rank [0,1]  | More stable
ON_raw     | HD*ln(1+CI)/CD     | HD*CI/CD               | ↑ Higher scores
K          | 5                  | 10                     | More stable
    """)
    
    print("\n" + "="*80)
    print("📈 Quick Stats (FIXED Metrics)")
    print("="*80)
    print(f"{'Method':<20} {'N':<6} {'ON':<12} {'ON_raw':<12} {'P':<12}")
    print("-"*80)
    
    for method, stats in summary.get("methods", {}).items():
        name = stats.get("name", method)[:18]
        count = stats['count']
        on = stats.get("ON_mean", 0)
        on_str = f"{on:.3f}" if on else "N/A"
        on_raw = stats.get("ON_raw_mean", 0)
        on_raw_str = f"{on_raw:.3f}" if on_raw else "N/A"
        p = stats.get("P_mean")
        p_str = f"{p:.3f}" if p else "N/A"
        print(f"{name:<20} {count:<6} {on_str:<12} {on_raw_str:<12} {p_str:<12}")
    
    print("="*80)
    print("\n✨ Check comparison_report.md for detailed results!")
    print("="*80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
