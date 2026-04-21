#!/usr/bin/env python3
"""
从假说报告中提取源文献信息

用途：
1. 从你的系统生成的报告中提取RAG检索到的论文摘要
2. 为P指标计算准备source_documents JSON文件
3. 支持多种报告格式和系统类型

用法:
    python extract_source_docs.py --report path/to/report.md --output sources.json
    
对于非RAG系统（如纯LLM）:
    python extract_source_docs.py --prompt "your prompt text" --output sources.json

参数说明：
    - alpha (α): 源相似度权重，默认0.5，范围[0,1]
    - beta (β): 源多样性权重，默认0.5，范围[0,1]
    - gamma (γ): 溯源因子权重，默认0.7，范围[0,1]
"""

import json
import re
import sys
import argparse
from pathlib import Path


def extract_from_inspiration_report(report_path: str) -> list:
    """
    从 inspiration_report.md 中提取源论文摘要
    适用于你的系统生成的报告
    """
    with open(report_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    abstracts = []
    
    # 匹配所有"论文摘要:"后面的内容
    # 格式: 论文摘要: <abstract text>
    pattern = r'论文摘要:\s*([^\n]+(?:\n(?!\*\*|###)[^\n]+)*)'
    matches = re.findall(pattern, content, re.MULTILINE)
    
    for match in matches:
        abstract = match.strip()
        if len(abstract) > 50:  # 过滤太短的文本
            abstracts.append(abstract)
    
    return abstracts


def extract_from_hypothesis_report(report_path: str) -> list:
    """
    从 hypothesis_society_demo.py 生成的报告中提取RAG证据
    适用于你的多智能体系统报告
    """
    with open(report_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    abstracts = []
    
    # 方法1: 查找"PRIMARY EVIDENCE"或"SUPPLEMENTARY CONTEXT"部分
    evidence_pattern = r'(?:PRIMARY EVIDENCE|SUPPLEMENTARY CONTEXT)[^\n]*\n+(.*?)(?=\n##|\Z)'
    evidence_sections = re.findall(evidence_pattern, content, re.DOTALL)
    
    for section in evidence_sections:
        # 提取论文标题和摘要
        paper_pattern = r'\*\*([^*]+)\*\*[^\n]*\n+([^\n]+(?:\n(?!\*\*)[^\n]+)*)'
        papers = re.findall(paper_pattern, section)
        
        for title, abstract in papers:
            if len(abstract.strip()) > 50:
                abstracts.append(f"{title.strip()}: {abstract.strip()}")
    
    # 方法2: 直接查找所有引用的论文片段
    if not abstracts:
        # 查找类似 "[Paper: xxx]" 或 "根据xxx论文" 的引用
        citation_pattern = r'(?:根据|参考|引用)([^。\n]+(?:论文|研究|文献))'
        citations = re.findall(citation_pattern, content)
        abstracts.extend([c.strip() for c in citations if len(c.strip()) > 30])
    
    return abstracts


def create_source_docs_json(source_docs: list, output_path: str, metadata: dict = None):
    """创建标准格式的source_documents JSON文件"""
    data = {
        "source_documents": source_docs,
        "count": len(source_docs),
        "metadata": metadata or {}
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 提取到 {len(source_docs)} 个源文献")
    print(f"✅ 已保存到: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Extract source documents for P metric calculation")
    parser.add_argument("--report", type=str, help="Path to the hypothesis report markdown file")
    parser.add_argument("--inspiration_report", type=str, help="Path to inspiration_report.md")
    parser.add_argument("--prompt", type=str, help="For non-RAG systems: use prompt as source")
    parser.add_argument("--output", type=str, required=True, help="Output JSON path")
    parser.add_argument("--system_type", type=str, choices=["ours", "virsci", "non_rag", "auto"], 
                       default="auto", help="Type of system that generated the report")
    
    args = parser.parse_args()
    
    source_docs = []
    metadata = {"system_type": args.system_type}
    
    # 场景1: 使用inspiration report（你的GNN+RAG系统）
    if args.inspiration_report:
        print(f"Extracting from inspiration report: {args.inspiration_report}")
        source_docs = extract_from_inspiration_report(args.inspiration_report)
        metadata["source_type"] = "inspiration_pipeline"
    
    # 场景2: 使用hypothesis report（多智能体系统）
    elif args.report:
        print(f"Extracting from hypothesis report: {args.report}")
        source_docs = extract_from_hypothesis_report(args.report)
        metadata["source_type"] = "hypothesis_report"
    
    # 场景3: 非RAG系统（如GPT-4 baseline），使用prompt作为source
    elif args.prompt:
        print("Using prompt as source document (non-RAG system)")
        source_docs = [args.prompt]
        metadata["source_type"] = "prompt_only"
        metadata["note"] = "Non-RAG system: P metric will reflect novelty vs. prompt"
    
    else:
        print("❌ 错误: 必须提供 --report, --inspiration_report, 或 --prompt 之一")
        sys.exit(1)
    
    # 去重
    source_docs = list(dict.fromkeys(source_docs))  # 保持顺序的去重
    
    if not source_docs:
        print("⚠️  警告: 未提取到任何源文献")
        print("   可能原因:")
        print("   1. 报告格式不符合预期")
        print("   2. 报告中未包含论文摘要")
        print("   3. 正则表达式需要调整")
        print("\n   建议: 手动创建 JSON 文件，格式如下:")
        print('   {"source_documents": ["abstract1", "abstract2", ...]}')
        sys.exit(1)
    
    create_source_docs_json(source_docs, args.output, metadata)
    
    # 打印预览
    print("\n" + "="*80)
    print("源文献预览 (前3个):")
    print("="*80)
    for i, doc in enumerate(source_docs[:3], 1):
        preview = doc[:150] + "..." if len(doc) > 150 else doc
        print(f"\n[{i}] {preview}")
    
    if len(source_docs) > 3:
        print(f"\n... 还有 {len(source_docs) - 3} 个源文献")


if __name__ == "__main__":
    main()

