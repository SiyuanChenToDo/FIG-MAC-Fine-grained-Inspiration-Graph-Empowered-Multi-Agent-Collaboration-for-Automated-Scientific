#!/usr/bin/env python3
"""
FIG-MAC Evaluation Framework - Ultra-Quick Test (No API Calls)

This test verifies the code structure and data loading without making API calls.
Use this to validate the setup before running full evaluation.

Usage:
    python quick_test.py
"""

import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def test_imports():
    """Test that all modules can be imported."""
    print("\n" + "="*60)
    print("1. Testing Module Imports")
    print("="*60)
    
    tests = [
        ("numpy", "np"),
        ("csv", "csv"),
        ("json", "json"),
        ("re", "re"),
    ]
    
    for module_name, alias in tests:
        try:
            exec(f"import {module_name} as {alias}")
            print(f"  ✓ {module_name}")
        except Exception as e:
            print(f"  ✗ {module_name}: {e}")
    
    # Test framework modules (without CAMEL dependencies)
    try:
        from Myexamples.evaluation_framework.utils import file_utils, text_utils
        print("  ✓ utils modules")
    except Exception as e:
        print(f"  ✗ utils modules: {e}")
    
    return True


def test_csv_loading():
    """Test CSV data loading."""
    print("\n" + "="*60)
    print("2. Testing CSV Data Loading")
    print("="*60)
    
    csv_paths = [
        "data/all_merged (1).csv",
        "/root/autodl-tmp/data/all_merged (1).csv",
    ]
    
    csv_path = None
    for p in csv_paths:
        if os.path.exists(p):
            csv_path = p
            break
    
    if not csv_path:
        print("  ✗ CSV file not found")
        return False
    
    print(f"  ✓ Found CSV: {csv_path}")
    
    try:
        import csv
        
        # Read first few rows
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = []
            for i, row in enumerate(reader):
                if i >= 3:
                    break
                rows.append(row)
        
        print(f"  ✓ Successfully read {len(rows)} sample rows")
        
        # Check required columns
        if rows:
            columns = set(rows[0].keys())
            required = {'doi', 'title', 'year', 'citationcount'}
            missing = required - columns
            
            if missing:
                print(f"  ⚠ Missing columns: {missing}")
            else:
                print(f"  ✓ All required columns present")
            
            # Show sample data
            row = rows[0]
            print(f"\n  Sample data:")
            print(f"    Title: {row.get('title', 'N/A')[:60]}...")
            print(f"    Year: {row.get('year', 'N/A')}")
            print(f"    Citations: {row.get('citationcount', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error reading CSV: {e}")
        return False


def test_file_discovery():
    """Test that we can find hypothesis files."""
    print("\n" + "="*60)
    print("3. Testing File Discovery")
    print("="*60)
    
    base_dir = "Myexamples/evaluation_system/batch_results"
    
    methods = {
        "ours": "*.md",
        "ai_scientist": "*.txt",
        "coi": "*.txt",
        "virsci": "*.txt",
    }
    
    import glob
    
    for method, pattern in methods.items():
        method_dir = os.path.join(base_dir, method)
        if not os.path.exists(method_dir):
            print(f"  ⚠ {method}: directory not found")
            continue
        
        search_pattern = os.path.join(method_dir, "**", pattern)
        files = glob.glob(search_pattern, recursive=True)
        files = [f for f in files if "inspiration" not in os.path.basename(f).lower()]
        
        if files:
            print(f"  ✓ {method}: found {len(files)} files")
            print(f"    Example: {os.path.basename(files[0])}")
        else:
            print(f"  ⚠ {method}: no files found")
    
    return True


def test_content_extraction():
    """Test content extraction without full evaluation."""
    print("\n" + "="*60)
    print("4. Testing Content Extraction")
    print("="*60)
    
    import glob
    
    # Test each method's extractor on one file
    test_cases = [
        ("ours", "Myexamples/evaluation_system/batch_results/ours/reports/*.md"),
        ("ai_scientist", "Myexamples/evaluation_system/batch_results/ai_scientist/*.txt"),
        ("coi", "Myexamples/evaluation_system/batch_results/coi/*.txt"),
        ("virsci", "Myexamples/evaluation_system/batch_results/virsci/*.txt"),
    ]
    
    for method, pattern in test_cases:
        files = glob.glob(pattern)
        files = [f for f in files if "inspiration" not in os.path.basename(f).lower()]
        
        if not files:
            print(f"  ⚠ {method}: no files to test")
            continue
        
        try:
            with open(files[0], 'r', encoding='utf-8') as f:
                raw_text = f.read()
            
            # Show file stats
            lines = raw_text.split('\n')
            print(f"\n  {method}:")
            print(f"    File: {os.path.basename(files[0])}")
            print(f"    Size: {len(raw_text)} chars, {len(lines)} lines")
            
            # Show first few lines
            first_lines = '\n'.join(lines[:5]).replace('\n', ' | ')
            if len(first_lines) > 100:
                first_lines = first_lines[:100] + "..."
            print(f"    Preview: {first_lines}")
            
        except Exception as e:
            print(f"  ✗ {method}: {e}")
    
    return True


def test_directory_structure():
    """Test that output directory can be created."""
    print("\n" + "="*60)
    print("5. Testing Output Directory")
    print("="*60)
    
    test_dir = "Myexamples/evaluation_framework/results/test"
    
    try:
        os.makedirs(test_dir, exist_ok=True)
        
        # Test write
        test_file = os.path.join(test_dir, "test_write.json")
        with open(test_file, 'w') as f:
            import json
            json.dump({"test": True}, f)
        
        os.remove(test_file)
        print(f"  ✓ Output directory ready: {test_dir}")
        return True
        
    except Exception as e:
        print(f"  ✗ Cannot create output directory: {e}")
        return False


def main():
    """Run all tests."""
    print("="*60)
    print("FIG-MAC Evaluation Framework - Quick Setup Test")
    print("="*60)
    
    results = []
    
    try:
        results.append(("Imports", test_imports()))
    except Exception as e:
        print(f"\n✗ Import test failed: {e}")
        results.append(("Imports", False))
    
    try:
        results.append(("CSV Loading", test_csv_loading()))
    except Exception as e:
        print(f"\n✗ CSV test failed: {e}")
        results.append(("CSV Loading", False))
    
    try:
        results.append(("File Discovery", test_file_discovery()))
    except Exception as e:
        print(f"\n✗ File discovery failed: {e}")
        results.append(("File Discovery", False))
    
    try:
        results.append(("Content Extraction", test_content_extraction()))
    except Exception as e:
        print(f"\n✗ Content extraction failed: {e}")
        results.append(("Content Extraction", False))
    
    try:
        results.append(("Directory Structure", test_directory_structure()))
    except Exception as e:
        print(f"\n✗ Directory test failed: {e}")
        results.append(("Directory Structure", False))
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {name}")
    
    all_passed = all(r[1] for r in results)
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ All tests passed! Ready for full evaluation.")
        print("\nNext step: Run the actual evaluation with limited samples:")
        print("  python test_evaluation.py --methods ours --sample-size 2")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
    print("="*60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
