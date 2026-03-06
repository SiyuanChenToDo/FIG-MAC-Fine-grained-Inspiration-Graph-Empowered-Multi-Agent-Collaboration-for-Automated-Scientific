#!/usr/bin/env python3
"""
FIG-MAC Evaluation Framework - Limited Sample Evaluation

Runs evaluation on a small number of samples per method for testing.
This is useful for:
- Validating the pipeline works correctly
- Estimating total runtime
- Checking metric calculations

Usage:
    # Test with 2 samples per method (fastest)
    python run_limited_evaluation.py --sample-size 2
    
    # Test with 5 samples per method
    python run_limited_evaluation.py --sample-size 5 --methods ours ai_scientist
    
    # Test only FIG-MAC with 3 samples
    python run_limited_evaluation.py --methods ours --sample-size 3
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
    """Setup API keys."""
    if not os.environ.get("OPENAI_COMPATIBILITY_API_KEY"):
        os.environ["OPENAI_COMPATIBILITY_API_KEY"] = "sk-c1a6b588f7d543adb0412c5bc61bdd7b"
    if not os.environ.get("OPENAI_COMPATIBILITY_API_BASE_URL"):
        os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    os.environ["QWEN_API_KEY"] = os.environ["OPENAI_COMPATIBILITY_API_KEY"]
    os.environ["QWEN_API_BASE_URL"] = os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"]


def estimate_time(num_methods, samples_per_method):
    """Estimate total evaluation time."""
    # Rough estimates per file:
    # - Embedding + VDB query: ~5-10 seconds
    # - LLM evaluation: ~15-30 seconds (depends on API response time)
    time_per_file = 30  # Conservative estimate
    total_files = num_methods * samples_per_method
    estimated_seconds = total_files * time_per_file
    
    print(f"\n⏱️  Time Estimate:")
    print(f"   Methods: {num_methods}")
    print(f"   Samples per method: {samples_per_method}")
    print(f"   Total files: {total_files}")
    print(f"   Estimated time: {estimated_seconds // 60}m {estimated_seconds % 60}s")
    print(f"   (Actual time depends on API response speed)\n")
    
    return estimated_seconds


def main():
    parser = argparse.ArgumentParser(
        description="Limited sample evaluation for testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick test (2 samples x 4 methods = ~4 minutes)
  python run_limited_evaluation.py
  
  # Medium test (5 samples x 2 methods = ~5 minutes)
  python run_limited_evaluation.py --sample-size 5 --methods ours ai_scientist
  
  # Single method test (3 samples = ~1.5 minutes)
  python run_limited_evaluation.py --methods ours --sample-size 3
        """
    )
    
    parser.add_argument(
        "--methods",
        nargs="+",
        choices=["ours", "ai_scientist", "coi", "virsci"],
        default=["ours"],  # Default to just ours for safety
        help="Methods to evaluate (default: ours only)"
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=2,
        help="Number of files to evaluate per method (default: 2)"
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
    parser.add_argument(
        "--output-dir",
        default="Myexamples/evaluation_framework/results/limited",
        help="Output directory"
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt"
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
    
    # Header
    print("="*70)
    print("🧪 FIG-MAC Limited Sample Evaluation")
    print("="*70)
    print(f"\nConfiguration:")
    print(f"  Methods: {', '.join(args.methods)}")
    print(f"  Samples per method: {args.sample_size}")
    print(f"  CSV data: {args.csv_data}")
    print(f"  Output: {args.output_dir}")
    
    # Time estimate
    estimate_time(len(args.methods), args.sample_size)
    
    # Confirmation
    if not args.yes:
        response = input("Continue? [Y/n]: ").strip().lower()
        if response and response not in ('y', 'yes'):
            print("Aborted.")
            return 0
    
    # Setup
    setup_environment()
    
    # Import and initialize
    print("\n[Setup] Initializing evaluator...")
    start_time = time.time()
    
    try:
        from Myexamples.evaluation_framework.core.batch_evaluator import BatchEvaluator
        
        evaluator = BatchEvaluator(
            vdb_path=args.vdb_path,
            csv_data_path=args.csv_data,
            output_dir=args.output_dir,
        )
        print("  ✓ Evaluator initialized")
    except Exception as e:
        print(f"  ✗ Failed to initialize: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Run evaluation for each method
    all_results = {}
    
    for method in args.methods:
        method_dir = os.path.join(args.results_dir, method)
        if method == "ours":
            method_dir = os.path.join(method_dir, "reports")  # ours files are in reports/
        
        if not os.path.exists(method_dir):
            print(f"\n⚠️  Skipping {method}: directory not found")
            continue
        
        # Find files
        import glob
        config = BatchEvaluator.METHOD_CONFIGS.get(method, {})
        pattern = os.path.join(method_dir, "**", config.get("file_pattern", "*.txt"))
        files = glob.glob(pattern, recursive=True)
        files = [f for f in files if "inspiration" not in os.path.basename(f).lower()]
        
        if not files:
            print(f"\n⚠️  Skipping {method}: no files found")
            continue
        
        sample_files = files[:args.sample_size]
        
        print(f"\n{'='*70}")
        print(f"📁 {method.upper()}: {len(sample_files)} files")
        print(f"{'='*70}")
        
        method_results = []
        for i, file_path in enumerate(sample_files, 1):
            print(f"\n[{i}/{len(sample_files)}] {os.path.basename(file_path)}")
            
            file_start = time.time()
            try:
                result = evaluator.evaluate_single(file_path, method)
                method_results.append(result)
                
                file_time = time.time() - file_start
                
                if "error" not in result:
                    novelty = result.get("metrics", {}).get("objective", {}).get("novelty", {})
                    subjective = result.get("metrics", {}).get("subjective", {})
                    
                    print(f"  ✓ Completed in {file_time:.1f}s")
                    print(f"    ON_raw: {novelty.get('ON_raw', 'N/A'):.4f}" if novelty.get('ON_raw') else "    ON_raw: N/A")
                    
                    if subjective:
                        scores = [subjective.get(d, 0) for d in ['Novelty', 'Significance', 'Effectiveness', 'Clarity', 'Feasibility']]
                        avg_score = sum(scores) / len([s for s in scores if s])
                        print(f"    LLM Avg: {avg_score:.1f}/10")
                    
                    has_p = result.get("metrics", {}).get("objective", {}).get("provenance") is not None
                    print(f"    P metric: {'✓' if has_p else '✗'}")
                else:
                    print(f"  ✗ Error: {result.get('error', 'Unknown')}")
                    
            except Exception as e:
                print(f"  ✗ Exception: {e}")
                import traceback
                traceback.print_exc()
        
        all_results[method] = method_results
        
        # Save intermediate results
        os.makedirs(args.output_dir, exist_ok=True)
        output_file = os.path.join(args.output_dir, f"{method}_results.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(method_results, f, indent=2)
        print(f"\n  💾 Saved to {output_file}")
    
    # Final summary
    total_time = time.time() - start_time
    
    print("\n" + "="*70)
    print("📊 Summary")
    print("="*70)
    
    total_files = sum(len(r) for r in all_results.values())
    successful = sum(1 for results in all_results.values() for r in results if "error" not in r)
    
    print(f"\nTotal time: {total_time // 60:.0f}m {total_time % 60:.0f}s")
    print(f"Files processed: {total_files}")
    print(f"Successful: {successful}")
    print(f"Failed: {total_files - successful}")
    
    if len(all_results) > 1:
        print(f"\nPer-method breakdown:")
        for method, results in all_results.items():
            valid = [r for r in results if "error" not in r]
            if valid:
                on_scores = [r["metrics"]["objective"]["novelty"]["ON_raw"] 
                           for r in valid 
                           if r.get("metrics", {}).get("objective", {}).get("novelty", {}).get("ON_raw")]
                if on_scores:
                    import numpy as np
                    print(f"  {method}: {len(valid)} files, ON_raw = {np.mean(on_scores):.4f} ± {np.std(on_scores):.4f}")
    
    print(f"\nResults saved to: {args.output_dir}")
    print("\n" + "="*70)
    print("✅ Limited evaluation complete!")
    print("="*70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
