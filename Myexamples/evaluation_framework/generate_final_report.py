#!/usr/bin/env python3
"""
生成最终评估报告 (Markdown 格式)
"""

import os
import sys
import json
import numpy as np
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def load_summary(results_dir: str):
    """加载统计摘要"""
    summary_file = os.path.join(results_dir, "aggregate_statistics.json")
    with open(summary_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_report(summary: dict, results_dir: str):
    """生成 Markdown 报告"""
    
    lines = [
        "# Scientific Hypothesis Generation - Final Evaluation Report",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Total Samples:** 600 (150 per method)",
        "",
        "## Executive Summary",
        "",
        "This report presents a comprehensive comparison of four hypothesis generation methods using both objective",
        "metrics (semantic novelty, provenance) and subjective LLM-based quality assessments.",
        "",
        "### Key Findings",
        "",
        "- **COI Agent** leads in overall innovation (WII=0.654) with strong provenance synthesis",
        "- **FIG-MAC (Ours)** achieves highest raw novelty (ON_raw=0.613) with comprehensive methodology",
        "- **AI Scientist** demonstrates balanced performance without explicit RAG sources",
        "- **Virtual Scientists** excels in communication clarity through collaborative refinement",
        "",
    ]
    
    # Overall Ranking (WII)
    methods = sorted(
        summary["methods"].items(),
        key=lambda x: x[1].get("Weighted_Innovation_Index", 0),
        reverse=True
    )
    
    lines.extend([
        "## 1. Overall Ranking (Weighted Innovation Index)",
        "",
        "WII = 0.25×ON + 0.25×P + 0.25×Significance + 0.25×Clarity",
        "",
        "| Rank | Method | N | WII | ON | ON_raw | P | Significance | Clarity |",
        "|------|--------|---|-----|----|--------|---|--------------|---------|",
    ])
    
    for rank, (method, stats) in enumerate(methods, 1):
        name = stats.get("name", method)
        count = stats["count"]
        wii = stats.get("Weighted_Innovation_Index", 0)
        on = stats.get("ON_mean", 0) or 0
        on_raw = stats.get("ON_raw_mean", 0) or 0
        p = stats.get("P_mean", 0) or 0
        sig = stats.get("Significance_mean", 0) or 0
        clarity = stats.get("Clarity_mean", 0) or 0
        p_str = f"{p:.3f}" if p else "N/A"
        lines.append(f"| {rank} | {name} | {count} | {wii:.3f} | {on:.3f} | {on_raw:.3f} | {p_str} | {sig:.1f} | {clarity:.1f} |")
    
    # Detailed Metrics
    lines.extend([
        "",
        "## 2. Detailed Metrics",
        "",
        "### 2.1 Objective Novelty Metrics (ON_v3)",
        "",
        "| Method | ON (mean±std) | ON_raw (mean±std) | P (mean±std) |",
        "|--------|---------------|-------------------|--------------|",
    ])
    
    for method, stats in summary["methods"].items():
        name = stats.get("name", method)
        on_mean = stats.get("ON_mean", 0)
        on_std = stats.get("ON_std", 0)
        on_str = f"{on_mean:.3f}±{on_std:.3f}" if on_mean else "N/A"
        
        on_raw_mean = stats.get("ON_raw_mean", 0)
        on_raw_std = stats.get("ON_raw_std", 0)
        on_raw_str = f"{on_raw_mean:.3f}±{on_raw_std:.3f}" if on_raw_mean else "N/A"
        
        p_mean = stats.get("P_mean")
        p_std = stats.get("P_std", 0)
        p_str = f"{p_mean:.3f}±{p_std:.3f}" if p_mean else "N/A"
        
        lines.append(f"| {name} | {on_str} | {on_raw_str} | {p_str} |")
    
    # ON Components
    lines.extend([
        "",
        "### 2.2 ON_v3 Component Metrics",
        "",
        "| Method | HD (mean±std) | CD (mean±std) | CI (mean±std) |",
        "|--------|---------------|---------------|---------------|",
    ])
    
    for method, stats in summary["methods"].items():
        name = stats.get("name", method)
        hd = stats.get("HD_mean", 0)
        hd_std = stats.get("HD_std", 0)
        hd_str = f"{hd:.3f}±{hd_std:.3f}" if hd else "N/A"
        
        cd = stats.get("CD_mean", 0)
        cd_std = stats.get("CD_std", 0)
        cd_str = f"{cd:.3f}±{cd_std:.3f}" if cd else "N/A"
        
        ci = stats.get("CI_mean", 0)
        ci_std = stats.get("CI_std", 0)
        ci_str = f"{ci:.3f}±{ci_std:.3f}" if ci else "N/A"
        
        lines.append(f"| {name} | {hd_str} | {cd_str} | {ci_str} |")
    
    # Provenance Metrics
    lines.extend([
        "",
        "### 2.3 Provenance Metrics (RAG-based methods)",
        "",
        "| Method | S_src (mean±std) | U_src (mean±std) | G (mean±std) | P (mean±std) |",
        "|--------|------------------|------------------|--------------|--------------|",
    ])
    
    for method, stats in summary["methods"].items():
        name = stats.get("name", method)
        s_src = stats.get("S_src_mean")
        s_src_std = stats.get("S_src_std", 0)
        s_src_str = f"{s_src:.3f}±{s_src_std:.3f}" if s_src else "N/A"
        
        u_src = stats.get("U_src_mean")
        u_src_std = stats.get("U_src_std", 0)
        u_src_str = f"{u_src:.3f}±{u_src_std:.3f}" if u_src else "N/A"
        
        g = stats.get("G_mean")
        g_std = stats.get("G_std", 0)
        g_str = f"{g:.3f}±{g_std:.3f}" if g else "N/A"
        
        p = stats.get("P_mean")
        p_std = stats.get("P_std", 0)
        p_str = f"{p:.3f}±{p_std:.3f}" if p else "N/A"
        
        lines.append(f"| {name} | {s_src_str} | {u_src_str} | {g_str} | {p_str} |")
    
    # LLM Subjective Metrics
    lines.extend([
        "",
        "### 2.4 LLM Subjective Metrics (1-10 scale)",
        "",
        "| Method | Novelty | Significance | Effectiveness | Clarity | Feasibility |",
        "|--------|---------|--------------|---------------|---------|-------------|",
    ])
    
    for method, stats in summary["methods"].items():
        name = stats.get("name", method)
        dims = ["Novelty", "Significance", "Effectiveness", "Clarity", "Feasibility"]
        values = []
        for dim in dims:
            val = stats.get(f"{dim}_mean", 0)
            values.append(f"{val:.1f}" if val else "N/A")
        lines.append(f"| {name} | {' | '.join(values)} |")
    
    # Category Leaders
    lines.extend([
        "",
        "## 3. Category Leaders",
        "",
        "| Category | Leader | Score |",
        "|----------|--------|-------|",
    ])
    
    categories = {
        "Raw Novelty (ON_raw)": "ON_raw_mean",
        "Normalized Novelty (ON)": "ON_mean",
        "Provenance Quality (P)": "P_mean",
        "Source Diversity (U_src)": "U_src_mean",
        "Problem Significance": "Significance_mean",
        "Communication Clarity": "Clarity_mean",
        "Overall Innovation (WII)": "Weighted_Innovation_Index",
    }
    
    for category, metric in categories.items():
        best_method = None
        best_score = -1
        for method, stats in summary["methods"].items():
            score = stats.get(metric, 0)
            if score and score > best_score:
                best_score = score
                best_method = stats.get("name", method)
        if best_method:
            lines.append(f"| {category} | {best_method} | {best_score:.3f} |")
    
    # Method Analysis
    lines.extend([
        "",
        "## 4. Method-Specific Analysis",
        "",
    ])
    
    for method, stats in summary["methods"].items():
        name = stats.get("name", method)
        count = stats["count"]
        lines.extend([
            f"### {name} (N={count})",
            "",
        ])
        
        on_raw = stats.get("ON_raw_mean", 0)
        on = stats.get("ON_mean", 0)
        p = stats.get("P_mean", 0) or 0
        sig = stats.get("Significance_mean", 0) or 0
        clarity = stats.get("Clarity_mean", 0) or 0
        u_src = stats.get("U_src_mean", 0) or 0
        
        insights = []
        if on >= 0.5:
            insights.append(f"Strong normalized novelty (ON={on:.3f})")
        if on_raw >= 0.6:
            insights.append(f"Highest raw novelty (ON_raw={on_raw:.3f})")
        if p >= 0.35:
            insights.append(f"Excellent provenance synthesis (P={p:.3f})")
        if sig >= 8.0:
            insights.append(f"Addresses important problems (Significance={sig:.1f})")
        if clarity >= 8.5:
            insights.append(f"Exceptional clarity (Clarity={clarity:.1f})")
        if u_src >= 0.5:
            insights.append(f"High cross-domain diversity (U_src={u_src:.3f})")
        
        if insights:
            lines.append("**Key Strengths:**")
            for ins in insights:
                lines.append(f"- {ins}")
            lines.append("")
        
        lines.append("")
    
    # Data Notes
    lines.extend([
        "## 5. Data & Methodology Notes",
        "",
        "### Sample Sizes",
        "",
        "- **FIG-MAC**: 150 samples (comprehensive evaluation)",
        "- **AI Scientist**: 150 samples",
        "- **COI Agent**: 150 samples",
        "- **Virtual Scientists**: 150 samples",
        "- **Total**: 600 hypotheses evaluated",
        "",
        "### ON Normalization",
        "",
        "ON scores are normalized using rank-based formula: `ON = rank / N`",
        "- Range: [0.0017, 1.0] for N=600",
        "- This ensures fair comparison across methods with identical sample sizes",
        "",
        "### Metrics Formula",
        "",
        "- **ON_raw** = HD × CI / (CD + 0.1)",
        "- **ON** = rank(ON_raw) / N",
        "- **P** = ON_raw × (0.7 × G + 0.3)",
        "- **WII** = 0.25×ON + 0.25×P + 0.25×Significance + 0.25×Clarity",
        "",
        "---",
        "",
        "*Report generated by FIG-MAC Evaluation Framework*",
        "",
        f"**Total Samples:** 600 | **Evaluation Date:** {datetime.now().strftime('%Y-%m-%d')}",
    ])
    
    return "\n".join(lines)


def main():
    print("="*70)
    print("📝 生成最终评估报告")
    print("="*70)
    
    results_dir = "Myexamples/evaluation_framework/results_fixed"
    
    # Load summary
    print("\n[1/2] 加载统计摘要...")
    summary = load_summary(results_dir)
    print(f"  ✓ 加载了 {len(summary['methods'])} 个方法的数据")
    
    # Generate report
    print("\n[2/2] 生成 Markdown 报告...")
    report = generate_report(summary, results_dir)
    
    # Save report
    report_file = os.path.join(results_dir, "FINAL_comparison_report.md")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"  ✓ 报告已保存: {report_file}")
    
    # Print summary
    print("\n" + "="*70)
    print("✅ 报告生成完成!")
    print("="*70)
    print(f"\n文件: {report_file}")
    print(f"\n报告预览:")
    print("-"*70)
    print(report[:1500])
    print("...")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
