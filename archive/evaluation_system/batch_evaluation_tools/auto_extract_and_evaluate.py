#!/usr/bin/env python3
"""
全自动化提取源文献并计算P指标

功能：
1. 自动从您的系统输出（inspiration_report.md）提取真实源文献
2. 自动从hypothesis报告提取RAG证据（如果有）
3. 自动模拟Virtual-Scientists的RAG输出（基于相同topic的向量检索）
4. 自动运行完整评估（包括P指标）
5. 生成对比报告

用法：
    python auto_extract_and_evaluate.py \
        --report_path "path/to/hypothesis.md" \
        --inspiration_report "path/to/inspiration_report.md" \
        --comparison_text "baseline hypothesis text" \
        --research_topic "your research question" \
        --output_dir "results"
"""

import os
import sys
import json
import re
import argparse
import subprocess
from pathlib import Path
import numpy as np

# Load environment variables from .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Ensure API keys are set
if not os.environ.get("QWEN_API_KEY"):
    # Try alternative names
    if os.environ.get("OPENAI_COMPATIBILITY_API_KEY"):
        os.environ["QWEN_API_KEY"] = os.environ["OPENAI_COMPATIBILITY_API_KEY"]
    
if not os.environ.get("QWEN_API_BASE_URL"):
    if os.environ.get("OPENAI_COMPATIBILITY_API_BASE_URL"):
        os.environ["QWEN_API_BASE_URL"] = os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"]
    elif not os.environ.get("QWEN_API_BASE_URL"):
        os.environ["QWEN_API_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"


class SourceDocumentExtractor:
    """自动提取源文献"""
    
    @staticmethod
    def extract_from_inspiration_report(report_path: str) -> list:
        """
        从inspiration_report.md提取论文摘要
        这是您的GNN+RAG系统的真实输出
        """
        print(f"📖 从Inspiration Report提取源文献: {report_path}")
        
        if not os.path.exists(report_path):
            print(f"⚠️  文件不存在: {report_path}")
            return []
        
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        abstracts = []
        
        # 方法1: 提取"论文摘要:"部分（中文报告）
        pattern1 = r'\*\*论文摘要\*\*:\s*([^\n]+(?:\n(?!\*\*|###|##)[^\n]+)*)'
        matches1 = re.findall(pattern1, content, re.MULTILINE)
        for match in matches1:
            abstract = match.strip()
            if len(abstract) > 100:
                abstracts.append(abstract)
        
        # 方法2: 提取"Abstract:"部分（英文报告）
        pattern2 = r'\*\*Abstract\*\*:\s*([^\n]+(?:\n(?!\*\*|###|##)[^\n]+)*)'
        matches2 = re.findall(pattern2, content, re.MULTILINE)
        for match in matches2:
            abstract = match.strip()
            if len(abstract) > 100:
                abstracts.append(abstract)
        
        # 方法3: 提取列表格式的摘要
        pattern3 = r'-\s*\*\*(?:论文摘要|Abstract)\*\*:\s*(.+?)(?=\n-|\n###|\n##|\Z)'
        matches3 = re.findall(pattern3, content, re.DOTALL)
        for match in matches3:
            abstract = re.sub(r'\n+', ' ', match.strip())
            if len(abstract) > 100:
                abstracts.append(abstract)
        
        # 去重
        abstracts = list(dict.fromkeys(abstracts))
        
        print(f"✅ 提取到 {len(abstracts)} 个真实源文献")
        return abstracts
    
    @staticmethod
    def extract_from_hypothesis_report(report_path: str) -> list:
        """
        从hypothesis_society_demo生成的报告提取RAG证据
        适用于包含"PRIMARY EVIDENCE"的报告
        """
        print(f"📖 从Hypothesis Report提取RAG证据: {report_path}")
        
        if not os.path.exists(report_path):
            return []
        
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        abstracts = []
        
        # 查找PRIMARY EVIDENCE或SUPPLEMENTARY CONTEXT
        evidence_pattern = r'(?:PRIMARY EVIDENCE|SUPPLEMENTARY CONTEXT)[^\n]*\n+(.*?)(?=\n##|\Z)'
        evidence_sections = re.findall(evidence_pattern, content, re.DOTALL)
        
        for section in evidence_sections:
            # 提取论文标题和内容
            paper_pattern = r'\*\*([^*]+)\*\*[^\n]*\n+([^\n]+(?:\n(?!\*\*)[^\n]+)*)'
            papers = re.findall(paper_pattern, section)
            
            for title, abstract in papers:
                if len(abstract.strip()) > 100:
                    abstracts.append(f"{title.strip()}: {abstract.strip()}")
        
        abstracts = list(dict.fromkeys(abstracts))
        print(f"✅ 提取到 {len(abstracts)} 个RAG证据")
        return abstracts
    
    @staticmethod
    def simulate_virsci_rag(research_topic: str, vdb_path: str, top_k: int = 10) -> list:
        """
        模拟Virtual-Scientists的RAG输出
        使用相同的向量数据库进行纯向量检索
        """
        print(f"🔍 模拟Virtual-Scientists的RAG检索...")
        print(f"   Research Topic: {research_topic[:80]}...")
        
        try:
            from camel.storages import FaissStorage, VectorDBQuery
            from camel.embeddings import OpenAICompatibleEmbedding
            
            # 初始化embedding模型
            embedding_model = OpenAICompatibleEmbedding(
                model_type="text-embedding-v2",
                api_key=os.environ.get("QWEN_API_KEY"),
                url=os.environ.get("QWEN_API_BASE_URL")
            )
            
            # 加载向量数据库
            storage_path = os.path.join(vdb_path, "paper/abstract")
            if not os.path.exists(storage_path):
                storage_path = os.path.join(vdb_path, "abstract")
            
            vector_storage = FaissStorage(
                vector_dim=1536,
                storage_path=storage_path,
                collection_name="paper_abstract"
            )
            vector_storage.load()
            
            # 向量检索
            query_vec = np.array(embedding_model.embed(obj=research_topic), dtype=np.float32)
            results = vector_storage.query(VectorDBQuery(query_vector=query_vec, top_k=top_k))
            
            # 提取摘要
            abstracts = []
            for res in results:
                payload = res.record.payload
                title = payload.get("title", "Unknown")
                abstract = payload.get("abstract", "")
                if abstract and len(abstract) > 50:
                    abstracts.append(f"{title}: {abstract}")
            
            print(f"✅ Virtual-Scientists RAG模拟完成，检索到 {len(abstracts)} 篇论文")
            return abstracts
            
        except Exception as e:
            print(f"❌ Virtual-Scientists RAG模拟失败: {e}")
            print("   使用fallback方案（仅用research topic作为源）")
            return [f"Research Prompt: {research_topic}"]


def save_source_docs(abstracts: list, output_path: str, metadata: dict = None):
    """保存源文献JSON"""
    data = {
        "source_documents": abstracts,
        "count": len(abstracts),
        "metadata": metadata or {}
    }
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 已保存到: {output_path}")


def run_evaluation_with_p_metric(report_path: str, source_docs_path: str,
                                 comparison_text: str, baseline_source_docs_path: str,
                                 output_dir: str, json_data_path: str, vdb_path: str):
    """运行完整评估（包括P指标）"""
    print("\n" + "="*80)
    print("🔬 运行完整评估系统（含ON_v2 + P指标）")
    print("="*80)
    
    cmd = [
        "python", "Myexamples/evaluation_system/run_evaluation.py",
        "--report_path", report_path,
        "--source_docs", source_docs_path,
        "--comparison_text", comparison_text,
        "--baseline_source_docs", baseline_source_docs_path,
        "--json_data", json_data_path,
        "--vdb_path", vdb_path,
        "--output_dir", output_dir
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ 评估完成")
        print(result.stdout)
    else:
        print("❌ 评估失败")
        print(result.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="全自动提取源文献并计算P指标")
    parser.add_argument("--report_path", type=str, required=True, help="主假说报告路径")
    parser.add_argument("--inspiration_report", type=str, help="Inspiration报告路径（您的GNN输出）")
    parser.add_argument("--comparison_text", type=str, help="基线假说文本（直接文本或文件路径）")
    parser.add_argument("--research_topic", type=str, required=True, help="研究问题（用于模拟Virtual-Scientists RAG）")
    parser.add_argument("--vdb_path", type=str, default="Myexamples/vdb/camel_faiss_storage", help="向量数据库路径")
    parser.add_argument("--json_data", type=str, default="Myexamples/data/final_data/final_custom_kg_papers.json", help="元数据路径")
    parser.add_argument("--output_dir", type=str, default="Myexamples/evaluation_system/results", help="输出目录")
    parser.add_argument("--virsci_rag_top_k", type=int, default=10, help="Virtual-Scientists RAG检索数量")
    
    args = parser.parse_args()
    
    print("="*80)
    print("🤖 全自动化P指标评估流程")
    print("="*80)
    
    extractor = SourceDocumentExtractor()
    
    # Step 1: 提取您的系统的源文献
    print("\n[步骤1/5] 提取您的系统源文献...")
    our_sources = []
    
    if args.inspiration_report and os.path.exists(args.inspiration_report):
        our_sources = extractor.extract_from_inspiration_report(args.inspiration_report)
    
    # 备用：从hypothesis报告提取
    if not our_sources:
        our_sources = extractor.extract_from_hypothesis_report(args.report_path)
    
    if not our_sources:
        print("⚠️  警告：未找到您的系统源文献，P指标将为None")
    
    our_sources_path = os.path.join(args.output_dir, "sources_our_system_auto.json")
    save_source_docs(our_sources, our_sources_path, {
        "system": "ours",
        "extraction_method": "auto_from_inspiration_report",
        "source_file": args.inspiration_report or args.report_path
    })
    
    # Step 2: 模拟Virtual-Scientists的RAG
    print("\n[步骤2/5] 模拟Virtual-Scientists的RAG检索...")
    virsci_sources = extractor.simulate_virsci_rag(
        args.research_topic, 
        args.vdb_path, 
        args.virsci_rag_top_k
    )
    
    virsci_sources_path = os.path.join(args.output_dir, "sources_virsci_simulated_auto.json")
    save_source_docs(virsci_sources, virsci_sources_path, {
        "system": "virtual_scientists",
        "extraction_method": "simulated_vector_retrieval",
        "research_topic": args.research_topic,
        "top_k": args.virsci_rag_top_k
    })
    
    # Step 3: 准备比较文本
    print("\n[步骤3/5] 准备基线假说文本...")
    if os.path.isfile(args.comparison_text):
        with open(args.comparison_text, 'r', encoding='utf-8') as f:
            comparison_text = f.read()
    else:
        comparison_text = args.comparison_text
    
    # Step 4: 运行评估
    print("\n[步骤4/5] 运行完整评估...")
    run_evaluation_with_p_metric(
        report_path=args.report_path,
        source_docs_path=our_sources_path,
        comparison_text=comparison_text,
        baseline_source_docs_path=virsci_sources_path,
        output_dir=args.output_dir,
        json_data_path=args.json_data,
        vdb_path=args.vdb_path
    )
    
    # Step 5: 总结
    print("\n[步骤5/5] 评估完成！")
    print("="*80)
    print("📊 生成的文件:")
    print(f"   - 您的系统源文献: {our_sources_path}")
    print(f"   - Virtual-Scientists源文献: {virsci_sources_path}")
    print(f"   - 评估结果: {args.output_dir}/*_eval_v2.json")
    print(f"   - 分析报告: {args.output_dir}/*_analysis_report.md")
    print("="*80)


if __name__ == "__main__":
    main()

