#!/usr/bin/env python3
"""
Compatibility wrapper for old batch_evaluation_tools scripts.

This wrapper allows you to use the new evaluation_framework
while maintaining compatibility with existing workflows.
"""

import os
import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation_framework.core.batch_evaluator import BatchEvaluator


def normalize_on_compat(json_paths):
    """
    Compatibility wrapper for batch_normalize_on.py
    
    Usage: python compat_wrapper.py normalize results/*.json
    """
    import json
    import numpy as np
    
    print("="*80)
    print("🔬 ON_v2 Batch Normalization (Compatibility Mode)")
    print("="*80)
    
    # Load all results
    results = []
    for path in json_paths:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                results.append({'path': path, 'data': data})
        except Exception as e:
            print(f"⚠️  Skipping {path}: {e}")
    
    if not results:
        print("❌ No valid results found")
        return
    
    # Extract ON_raw values
    on_values = []
    for idx, result in enumerate(results):
        try:
            novelty = result['data'].get('metrics', {}).get('objective', {}).get('Novelty_Metrics', {})
            on_raw = novelty.get('ON_raw (Overall Novelty - Raw)')
            if on_raw is not None and not isinstance(on_raw, str):
                on_values.append({
                    'index': idx,
                    'on_raw': float(on_raw),
                    'path': result['path'],
                })
        except:
            pass
    
    if not on_values:
        print("❌ No valid ON_raw values found")
        return
    
    # Sort and normalize using NEW formula (rank / N)
    sorted_values = sorted(on_values, key=lambda x: x['on_raw'])
    N = len(sorted_values)
    
    print(f"\n📊 Normalizing {N} hypotheses using formula: ON = rank / N")
    print("-"*80)
    print(f"{'Rank':<6} {'ON_raw':<12} {'ON_norm':<12} {'File':<40}")
    print("-"*80)
    
    for rank, item in enumerate(sorted_values, start=1):
        # NEW formula: rank / N (range [1/N, 1])
        normalized_on = rank / N
        
        # Update result
        idx = item['index']
        novelty = results[idx]['data']['metrics']['objective']['Novelty_Metrics']
        novelty['ON (Overall Novelty - Normalized)'] = normalized_on
        novelty['Rank'] = rank
        novelty['Total_Hypotheses'] = N
        
        # Save
        try:
            with open(results[idx]['path'], 'w', encoding='utf-8') as f:
                json.dump(results[idx]['data'], f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Failed to save {results[idx]['path']}: {e}")
        
        print(f"{rank:<6} {item['on_raw']:<12.4f} {normalized_on:<12.4f} {Path(item['path']).name[:38]}")
    
    print("="*80)
    print("✅ Normalization complete!")
    print(f"💡 Range: [{1/N:.4f}, 1.0] (all hypotheses receive non-zero scores)")


def evaluate_method_compat(method, input_dir, output_dir=None):
    """
    Compatibility wrapper for batch_evaluate_*.py scripts.
    
    Usage: python compat_wrapper.py eval --method ai_scientist --input_dir ...
    """
    method_mapping = {
        'ai_scientist': 'ai_scientist',
        'coi': 'coi',
        'coi_agent': 'coi',
        'virsci': 'virsci',
        'virtual_scientists': 'virsci',
        'ours': 'ours',
    }
    
    method_key = method_mapping.get(method.lower())
    if not method_key:
        print(f"❌ Unknown method: {method}")
        print(f"Supported: {list(method_mapping.keys())}")
        return
    
    print(f"Evaluating {method_key} from {input_dir}...")
    
    evaluator = BatchEvaluator(
        vdb_path=os.environ.get('VDB_PATH', 'Myexamples/vdb/camel_faiss_storage'),
        json_data_path=os.environ.get('JSON_DATA_PATH', 'Myexamples/data/final_data/final_custom_kg_papers.json'),
        output_dir=output_dir or 'Myexamples/evaluation_framework/results',
    )
    
    results = evaluator.evaluate_method(
        method_dir=input_dir,
        method=method_key,
    )
    
    print(f"✅ Evaluated {len(results)} files")


def main():
    parser = argparse.ArgumentParser(
        description="Compatibility wrapper for old evaluation scripts"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Normalize command
    norm_parser = subparsers.add_parser('normalize', help='Normalize ON scores')
    norm_parser.add_argument('json_files', nargs='+', help='JSON result files')
    
    # Evaluate command
    eval_parser = subparsers.add_parser('eval', help='Evaluate a method')
    eval_parser.add_argument('--method', required=True, help='Method name')
    eval_parser.add_argument('--input_dir', required=True, help='Input directory')
    eval_parser.add_argument('--output_dir', help='Output directory')
    
    args = parser.parse_args()
    
    if args.command == 'normalize':
        normalize_on_compat(args.json_files)
    elif args.command == 'eval':
        evaluate_method_compat(args.method, args.input_dir, args.output_dir)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
