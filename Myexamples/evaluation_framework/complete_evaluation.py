#!/usr/bin/env python3
"""
完成评估流程
1. 继续 Virsci 评估
2. 归一化 ON 分数
3. 生成统计和报告
"""

import os
import sys
import json
import numpy as np
from collections import defaultdict
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def setup_env():
    """Setup API keys"""
    if not os.environ.get("OPENAI_COMPATIBILITY_API_KEY"):
        os.environ["OPENAI_COMPATIBILITY_API_KEY"] = "sk-c1a6b588f7d543adb0412c5bc61bdd7b"
    if not os.environ.get("OPENAI_COMPATIBILITY_API_BASE_URL"):
        os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    os.environ["QWEN_API_KEY"] = os.environ["OPENAI_COMPATIBILITY_API_KEY"]
    os.environ["QWEN_API_BASE_URL"] = os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"]


def normalize_on_scores(results_dir: str):
    """归一化所有方法的 ON 分数"""
    print("\n" + "="*80)
    print("📈 归一化 ON 分数")
    print("="*80)
    
    all_results = {}
    for method in ["ours", "ai_scientist", "coi", "virsci"]:
        file_path = os.path.join(results_dir, f"{method}_raw_results.json")
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                all_results[method] = json.load(f)
            print(f"  ✓ 加载 {method}: {len(all_results[method])} 个结果")
    
    # Collect all valid ON_raw values
    all_novelty = []
    for method, results in all_results.items():
        for result in results:
            if "error" not in result and "metrics" in result:
                novelty = result["metrics"]["objective"]["novelty"]
                on_raw = novelty.get("ON_raw")
                if on_raw is not None and isinstance(on_raw, (int, float)):
                    all_novelty.append((on_raw, method, result))
    
    if len(all_novelty) < 2:
        print("  ⚠️ 有效结果不足，跳过归一化")
        return
    
    # Sort and assign ranks
    sorted_novelty = sorted(all_novelty, key=lambda x: x[0])
    N = len(sorted_novelty)
    
    for rank, (on_raw, method, result) in enumerate(sorted_novelty, start=1):
        normalized = rank / N
        result["metrics"]["objective"]["novelty"]["ON"] = normalized
        result["metrics"]["objective"]["novelty"]["rank"] = rank
        result["metrics"]["objective"]["novelty"]["N"] = N
    
    # Save updated results
    for method, results in all_results.items():
        output_file = os.path.join(results_dir, f"{method}_raw_results.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
    
    print(f"  ✓ 归一化完成: {N} 个结果")
    print(f"  ✓ ON 范围: [{1/N:.4f}, 1.0]")


def aggregate_statistics(results_dir: str):
    """生成统计摘要"""
    print("\n" + "="*80)
    print("📊 生成统计摘要")
    print("="*80)
    
    METHOD_CONFIGS = {
        "ours": {"name": "FIG-MAC (Ours)", "has_sources": True},
        "ai_scientist": {"name": "AI Scientist", "has_sources": False},
        "coi": {"name": "COI Agent", "has_sources": True},
        "virsci": {"name": "Virtual Scientists", "has_sources": True},
    }
    
    def calculate_wii(stats):
        on = stats.get("ON_mean", 0) or 0
        p = stats.get("P_mean", 0) or 0
        sig = (stats.get("Significance_mean", 0) or 0) / 10
        clarity = (stats.get("Clarity_mean", 0) or 0) / 10
        if not stats.get("P_mean"):
            return 0.4 * on + 0.3 * sig + 0.3 * clarity
        else:
            return 0.25 * on + 0.25 * p + 0.25 * sig + 0.25 * clarity
    
    summary = {"timestamp": datetime.now().isoformat(), "methods": {}}
    
    for method in ["ours", "ai_scientist", "coi", "virsci"]:
        file_path = os.path.join(results_dir, f"{method}_raw_results.json")
        if not os.path.exists(file_path):
            continue
        
        with open(file_path, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        valid = [r for r in results if "error" not in r and "metrics" in r]
        if not valid:
            continue
        
        config = METHOD_CONFIGS.get(method, {"name": method})
        stats = {"name": config["name"], "count": len(valid)}
        
        metrics = defaultdict(list)
        for r in valid:
            novelty = r["metrics"]["objective"]["novelty"]
            for key in ["ON", "ON_raw", "HD", "CD", "CI"]:
                if novelty.get(key) is not None:
                    metrics[key].append(novelty[key])
            
            prov = r["metrics"]["objective"].get("provenance") or {}
            if prov:
                for key in ["P", "S_src", "U_src", "G"]:
                    if prov.get(key) is not None:
                        metrics[key].append(prov[key])
            
            subj = r["metrics"].get("subjective", {})
            for dim in ["Novelty", "Significance", "Effectiveness", "Clarity", "Feasibility"]:
                if subj.get(dim) is not None:
                    metrics[dim].append(subj[dim])
        
        for key, vals in metrics.items():
            if vals:
                stats[f"{key}_mean"] = float(np.mean(vals))
                stats[f"{key}_std"] = float(np.std(vals))
        
        stats["Weighted_Innovation_Index"] = calculate_wii(stats)
        summary["methods"][method] = stats
        print(f"  ✓ {config['name']}: {len(valid)} 个有效结果")
    
    # Save summary
    summary_file = os.path.join(results_dir, "aggregate_statistics.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    
    print(f"  ✓ 统计摘要已保存")
    return summary


def print_comparison_table(summary: dict):
    """打印对比表格"""
    print("\n" + "="*80)
    print("📊 方法对比表")
    print("="*80)
    
    methods = sorted(
        summary["methods"].items(),
        key=lambda x: x[1].get("Weighted_Innovation_Index", 0),
        reverse=True
    )
    
    print(f"\n{'Rank':<6}{'Method':<25}{'N':<8}{'WII':<10}{'ON':<10}{'ON_raw':<10}{'P':<10}")
    print("-"*80)
    
    for rank, (method, stats) in enumerate(methods, 1):
        name = stats.get("name", method)[:24]
        count = stats["count"]
        wii = stats.get("Weighted_Innovation_Index", 0)
        on = stats.get("ON_mean", 0) or 0
        on_raw = stats.get("ON_raw_mean", 0) or 0
        p = stats.get("P_mean", 0) or 0
        p_str = f"{p:.3f}" if p else "N/A"
        print(f"{rank:<6}{name:<25}{count:<8}{wii:<10.3f}{on:<10.3f}{on_raw:<10.3f}{p_str:<10}")


def main():
    print("="*80)
    print("🚀 完成评估流程")
    print("="*80)
    
    setup_env()
    results_dir = "Myexamples/evaluation_framework/results_fixed"
    
    # Step 1: Continue Virsci evaluation
    print("\n" + "="*80)
    print("1️⃣ 继续 Virsci 评估")
    print("="*80)
    
    # Check if we need to run Virsci
    virsci_file = os.path.join(results_dir, "virsci_raw_results.json")
    if os.path.exists(virsci_file):
        with open(virsci_file, 'r') as f:
            virsci_results = json.load(f)
        valid_count = len([r for r in virsci_results if "error" not in r])
        print(f"   当前 Virsci 进度: {valid_count}/150")
        
        if valid_count < 150:
            print("   需要继续评估...")
            import subprocess
            result = subprocess.run([
                sys.executable,
                "Myexamples/evaluation_framework/run_virsci_resume.py"
            ], cwd="/root/autodl-tmp")
            if result.returncode != 0:
                print("  ❌ Virsci 评估失败")
                return 1
        else:
            print("   ✓ Virsci 已完成")
    else:
        print("   未找到 Virsci 结果，需要完整运行")
        # Run full evaluation for virsci only
        from Myexamples.evaluation_framework.core.batch_evaluator import BatchEvaluator
        evaluator = BatchEvaluator(
            vdb_path="Myexamples/vdb/camel_faiss_storage",
            csv_data_path="data/all_merged (1).csv",
            output_dir=results_dir,
        )
        results = evaluator.evaluate_method(
            method_dir="Myexamples/evaluation_system/batch_results/virsci",
            method="virsci",
            max_samples=None
        )
        print(f"   ✓ Virsci 评估完成: {len(results)} 个结果")
    
    # Step 2: Normalize ON scores
    normalize_on_scores(results_dir)
    
    # Step 3: Generate statistics
    summary = aggregate_statistics(results_dir)
    
    # Step 4: Print comparison
    print_comparison_table(summary)
    
    print("\n" + "="*80)
    print("✅ 所有流程完成!")
    print("="*80)
    print(f"\n结果目录: {results_dir}")
    print("文件:")
    print(f"  - *_raw_results.json: 各方法原始结果")
    print(f"  - aggregate_statistics.json: 统计摘要")
    return 0


if __name__ == "__main__":
    sys.exit(main())
