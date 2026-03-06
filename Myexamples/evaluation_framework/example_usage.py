#!/usr/bin/env python3
"""
FIG-MAC Evaluation Framework - Example Usage

This script demonstrates how to use the evaluation framework
to evaluate a single hypothesis or compare multiple methods.
"""

import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation_framework.core.batch_evaluator import BatchEvaluator


def example_single_evaluation():
    """Example: Evaluate a single hypothesis."""
    print("="*70)
    print("Example 1: Single Hypothesis Evaluation")
    print("="*70)
    
    # Initialize evaluator
    evaluator = BatchEvaluator(
        vdb_path="Myexamples/vdb/camel_faiss_storage",
        json_data_path="Myexamples/data/final_data/final_custom_kg_papers.json",
        output_dir="Myexamples/evaluation_framework/results/example",
    )
    
    # Evaluate a single file
    result = evaluator.evaluate_single(
        file_path="Myexamples/evaluation_system/batch_results/ours/reports/example_report.md",
        method="ours",
        research_question="Example research question"
    )
    
    # Print results
    print("\n📊 Results:")
    print(f"  Novelty Metrics:")
    novelty = result.get("metrics", {}).get("objective", {}).get("novelty", {})
    for key, value in novelty.items():
        if not isinstance(value, dict):
            print(f"    {key}: {value}")
    
    print(f"\n  Subjective Metrics:")
    subjective = result.get("metrics", {}).get("subjective", {})
    for key, value in subjective.items():
        if key != "Reasoning":
            print(f"    {key}: {value}")


def example_batch_evaluation():
    """Example: Batch evaluation of multiple methods."""
    print("\n" + "="*70)
    print("Example 2: Batch Evaluation")
    print("="*70)
    
    evaluator = BatchEvaluator(
        vdb_path="Myexamples/vdb/camel_faiss_storage",
        json_data_path="Myexamples/data/final_data/final_custom_kg_papers.json",
        output_dir="Myexamples/evaluation_framework/results/batch",
    )
    
    # Evaluate all methods
    methods = ["ours", "ai_scientist", "coi", "virsci"]
    
    all_results = evaluator.evaluate_all_methods(
        base_results_dir="Myexamples/evaluation_system/batch_results",
        methods=methods,
    )
    
    # Normalize scores
    normalized = evaluator.normalize_all_on_scores(all_results)
    
    # Generate report
    report = evaluator.generate_comparison_report(normalized)
    
    print("\n✅ Batch evaluation complete!")
    print(f"Results saved to: {evaluator.output_dir}")


def example_quick_cli():
    """Example: Using the CLI runner."""
    print("\n" + "="*70)
    print("Example 3: CLI Usage")
    print("="*70)
    
    print("""
# Evaluate all methods:
python Myexamples/evaluation_framework/run_batch_evaluation.py

# Evaluate specific methods only:
python Myexamples/evaluation_framework/run_batch_evaluation.py \\
    --methods ours ai_scientist

# Custom paths:
python Myexamples/evaluation_framework/run_batch_evaluation.py \\
    --methods ours \\
    --results-dir /path/to/results \\
    --vdb-path /path/to/vdb \\
    --json-data /path/to/metadata.json

# With research questions:
python Myexamples/evaluation_framework/run_batch_evaluation.py \\
    --methods ours \\
    --rq-file research_questions.json
""")


def main():
    """Run examples."""
    print("\n" + "#"*70)
    print("# FIG-MAC Evaluation Framework - Usage Examples")
    print("#"*70)
    
    # Example 1: Single evaluation
    # Uncomment to run:
    # example_single_evaluation()
    
    # Example 2: Batch evaluation
    # Uncomment to run (takes time):
    # example_batch_evaluation()
    
    # Example 3: CLI usage
    example_quick_cli()
    
    print("\n" + "#"*70)
    print("# End of Examples")
    print("#"*70)


if __name__ == "__main__":
    main()
