#!/usr/bin/env python3
"""
FIG-MAC Batch Evaluation Runner

One-click batch evaluation for multiple hypothesis generation methods.

Usage:
    python run_batch_evaluation.py \
        --methods ours ai_scientist coi virsci \
        --results-dir Myexamples/evaluation_system/batch_results \
        --vdb-path Myexamples/vdb/camel_faiss_storage \
        --csv-data "data/all_merged (1).csv"

Note: Uses CSV metadata file (not JSON) for paper citations and years.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation_framework.core.batch_evaluator import BatchEvaluator


def load_research_questions(rq_file: str) -> Optional[Dict[str, str]]:
    """Load research questions mapping from JSON file."""
    if not os.path.exists(rq_file):
        return None
    
    try:
        with open(rq_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Support different formats
        if isinstance(data, dict):
            return data
        elif isinstance(data, list) and len(data) > 0:
            # Convert list to dict using index or title
            return {item.get("title", f"RQ_{i}"): item.get("question", "")
                   for i, item in enumerate(data)}
        
        return None
        
    except Exception as e:
        print(f"⚠️ Error loading RQ file: {e}")
        return None


def setup_environment():
    """Setup API keys from environment or config."""
    # Set default API config if not present
    if not os.environ.get("OPENAI_COMPATIBILITY_API_KEY"):
        os.environ["OPENAI_COMPATIBILITY_API_KEY"] = "sk-c1a6b588f7d543adb0412c5bc61bdd7b"
    
    if not os.environ.get("OPENAI_COMPATIBILITY_API_BASE_URL"):
        os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    
    # Sync with QWEN env vars
    os.environ["QWEN_API_KEY"] = os.environ["OPENAI_COMPATIBILITY_API_KEY"]
    os.environ["QWEN_API_BASE_URL"] = os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"]
    
    print("✓ Environment configured")


def main():
    parser = argparse.ArgumentParser(
        description="FIG-MAC Batch Evaluation Framework v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Evaluate all methods
  python run_batch_evaluation.py
  
  # Evaluate specific methods only
  python run_batch_evaluation.py --methods ours ai_scientist
  
  # Custom paths
  python run_batch_evaluation.py \\
      --methods ours \\
      --results-dir /path/to/results \\
      --vdb-path /path/to/vdb \\
      --csv-data "/path/to/metadata.csv"
        """
    )
    
    # Required arguments
    parser.add_argument(
        "--methods",
        nargs="+",
        choices=["ours", "ai_scientist", "coi", "virsci"],
        default=["ours", "ai_scientist", "coi", "virsci"],
        help="Methods to evaluate (default: all)"
    )
    
    # Path arguments
    parser.add_argument(
        "--results-dir",
        default="Myexamples/evaluation_system/batch_results",
        help="Base directory containing method subdirectories"
    )
    parser.add_argument(
        "--vdb-path",
        default="Myexamples/vdb/camel_faiss_storage",
        help="Path to FAISS vector database"
    )
    parser.add_argument(
        "--csv-data",
        default="data/all_merged (1).csv",
        help="Path to metadata CSV file (with citationCount, year columns)"
    )
    parser.add_argument(
        "--output-dir",
        default="Myexamples/evaluation_framework/results",
        help="Output directory for evaluation results"
    )
    
    # Optional arguments
    parser.add_argument(
        "--rq-file",
        help="JSON file with research questions mapping"
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=None,
        help="Limit evaluation to N samples per method (default: all files)"
    )
    
    args = parser.parse_args()
    
    # Validate CSV path
    if not os.path.exists(args.csv_data):
        # Try alternative paths
        alt_paths = [
            "/root/autodl-tmp/data/all_merged (1).csv",
            "data/all_merged (1).csv",
            "../data/all_merged (1).csv",
        ]
        for alt_path in alt_paths:
            if os.path.exists(alt_path):
                args.csv_data = alt_path
                break
        else:
            print(f"❌ CSV data file not found: {args.csv_data}")
            print("Please specify the correct path with --csv-data")
            return 1
    
    # Setup
    print("="*70)
    print("🚀 FIG-MAC Batch Evaluation Framework v2.0")
    print("="*70)
    
    setup_environment()
    
    print(f"\nConfiguration:")
    print(f"  Methods: {', '.join(args.methods)}")
    print(f"  Results dir: {args.results_dir}")
    print(f"  VDB path: {args.vdb_path}")
    print(f"  CSV data: {args.csv_data}")
    print(f"  Output dir: {args.output_dir}")
    if args.sample_size:
        print(f"  Sample size: {args.sample_size} per method")
    
    # Load research questions
    research_questions = None
    if args.rq_file:
        research_questions = load_research_questions(args.rq_file)
        if research_questions:
            print(f"  RQs loaded: {len(research_questions)}")
    
    # Initialize evaluator
    print("\n[Setup] Initializing evaluator...")
    evaluator = BatchEvaluator(
        vdb_path=args.vdb_path,
        csv_data_path=args.csv_data,
        output_dir=args.output_dir,
    )
    
    # Run evaluation
    print("\n" + "="*70)
    print("📊 Starting Batch Evaluation")
    print("="*70)
    
    all_results = evaluator.evaluate_all_methods(
        base_results_dir=args.results_dir,
        methods=args.methods,
        research_questions=research_questions,
        max_samples=args.sample_size
    )
    
    # Normalize ON scores across all methods
    print("\n" + "="*70)
    print("📈 Normalizing ON Scores")
    print("="*70)
    
    normalized_results = evaluator.normalize_all_on_scores(all_results)
    
    # Generate aggregate statistics
    print("\n" + "="*70)
    print("📋 Generating Statistics")
    print("="*70)
    
    summary = evaluator.aggregate_statistics(normalized_results)
    
    # Generate comparison report
    print("\n" + "="*70)
    print("📝 Generating Report")
    print("="*70)
    
    report = evaluator.generate_comparison_report(normalized_results)
    
    # Print summary
    print("\n" + "="*70)
    print("✅ Evaluation Complete!")
    print("="*70)
    print(f"\nResults saved to: {args.output_dir}")
    print("\nGenerated files:")
    for method in args.methods:
        print(f"  - {method}_raw_results.json")
    print(f"  - aggregate_statistics.json")
    print(f"  - comparison_report.md")
    
    print("\nQuick Stats:")
    print("-" * 70)
    print(f"{'Method':<20} {'Count':<8} {'ON_mean':<12} {'P_mean':<12}")
    print("-" * 70)
    for method, stats in summary.get("methods", {}).items():
        name = stats.get("name", method)[:18]
        count = stats['count']
        on_mean = stats.get("ON_mean", 0)
        on_str = f"{on_mean:.3f}" if on_mean else "N/A"
        p_mean = stats.get("P_mean")
        p_str = f"{p_mean:.3f}" if p_mean else "N/A"
        print(f"{name:<20} {count:<8} {on_str:<12} {p_str:<12}")
    print("-" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
