#!/usr/bin/env python3
"""
批量评估 Virtual-Scientists 生成结果

功能：
1. 从 virsci 日志目录中提取所有 Final Idea
2. 计算完整的评估指标（ON_v2, P指标, LLM主观评分）
3. 将结果导出为 Excel 表格

评估指标包括：
- 客观指标：
  * ON_raw (Overall Novelty - Raw)
  * ON_norm (Overall Novelty - Normalized)
  * HD (Historical Dissimilarity)
  * CD (Contemporary Dissimilarity)
  * CI (Contemporary Impact)
  * P (Provenance-Adjusted Novelty)
  * S_src (Source Similarity)
  * U_src (Source Diversity)
  * G (Provenance Factor)
- 主观指标（LLM评分）：
  * Novelty (1-10)
  * Significance (1-10)
  * Effectiveness (1-10)
  * Clarity (1-10)
  * Feasibility (1-10)

用法：
    # 基本用法
    python batch_evaluate_virsci_logs.py \
        --logs-dir "Myexamples/evaluation_system/batch_results/virsci/logs" \
        --output-excel "Myexamples/evaluation_system/batch_results/virsci_metrics.xlsx"
    
    # 跳过 LLM 评估（仅计算客观指标，更快）
    python batch_evaluate_virsci_logs.py \
        --logs-dir "Myexamples/evaluation_system/batch_results/virsci/logs" \
        --output-excel "virsci_metrics.xlsx" \
        --skip-llm
    
    # 限制处理数量（测试用）
    python batch_evaluate_virsci_logs.py \
        --logs-dir "Myexamples/evaluation_system/batch_results/virsci/logs" \
        --output-excel "virsci_metrics.xlsx" \
        --limit 10
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 项目内部导入 - 复用现有函数
from Myexamples.evaluation_system.run_evaluation import extract_core_content
from Myexamples.evaluation_system.metrics_calculator import ScientificMetricsCalculator
from Myexamples.evaluation_system.llm_evaluator import ScientificLLMEvaluator
from camel.embeddings import OpenAICompatibleEmbedding

# Import vector retrieval functionality
try:
    from camel.storages import FaissStorage, VectorDBQuery
    import numpy as np
    VECTOR_RETRIEVAL_AVAILABLE = True
except ImportError:
    print("⚠️  Vector retrieval module not available")
    VECTOR_RETRIEVAL_AVAILABLE = False


def ensure_env_defaults() -> None:
    """为评估脚本准备必需的环境变量。"""
    if not os.environ.get("OPENAI_COMPATIBILITY_API_KEY"):
        os.environ["OPENAI_COMPATIBILITY_API_KEY"] = "sk-c1a6b588f7d543adb0412c5bc61bdd7b"
    if not os.environ.get("OPENAI_COMPATIBILITY_API_BASE_URL"):
        os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    os.environ.setdefault("QWEN_API_KEY", os.environ["OPENAI_COMPATIBILITY_API_KEY"])
    os.environ.setdefault("QWEN_API_BASE_URL", os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"])


def extract_final_idea_json(log_content: str) -> Optional[Dict[str, Any]]:
    """
    从日志内容中提取 Final Idea JSON对象
    支持多种格式：
    1. 包含 "Idea": 字段的完整 JSON 对象
    2. 在 "New Idea:" 或 "```json" 标记后的 JSON
    """
    lines = log_content.split('\n')
    json_lines = []
    in_json = False
    brace_count = 0
    found_start = False
    
    # 方法1: 查找包含 "Idea": 的 JSON 对象
    for i, line in enumerate(lines):
        # 查找 "Idea": 开头的行，表示JSON开始
        if '"Idea":' in line:
            if '{' in line:
                in_json = True
                found_start = True
                brace_count = line.count('{') - line.count('}')
                json_lines.append(line.strip())
            elif not in_json:
                # 如果这一行有 "Idea": 但没有 {，可能在前一行
                # 向前查找包含 { 的行
                for j in range(max(0, i-5), i):
                    if '{' in lines[j]:
                        in_json = True
                        found_start = True
                        brace_count = lines[j].count('{') - lines[j].count('}')
                        json_lines.append(lines[j].strip())
                        json_lines.append(line.strip())
                        brace_count += line.count('{') - line.count('}')
                        break
        elif in_json:
            json_lines.append(line.strip())
            brace_count += line.count('{') - line.count('}')
            # 当大括号平衡时，JSON结束
            if brace_count == 0:
                break
    
    if json_lines and found_start:
        json_str = '\n'.join(json_lines)
        # 清理可能的标记
        json_str = json_str.replace('```json', '').replace('```', '').strip()
        try:
            data = json.loads(json_str)
            # 验证是否包含必要的字段
            if 'Idea' in data or 'Title' in data:
                return data
        except json.JSONDecodeError:
            # 如果解析失败，尝试修复常见的 JSON 问题
            # 移除末尾可能的点号
            json_str = json_str.rstrip('.').strip()
            try:
                data = json.loads(json_str)
                if 'Idea' in data or 'Title' in data:
                    return data
            except json.JSONDecodeError:
                pass
    
    return None


def extract_idea_text_fallback(log_content: str) -> Optional[Dict[str, Any]]:
    """
    回退方案：使用正则表达式提取各个字段
    """
    extracted = {}
    
    # 提取 Title
    title_pattern = r'"Title":\s*"([^"]+)"'
    title_match = re.search(title_pattern, log_content)
    if title_match:
        extracted['Title'] = title_match.group(1)
    
    # 提取 Idea (Abstract)
    idea_pattern = r'"Idea":\s*"(.*?)"(?:\s*,\s*"Title"|$)'
    idea_match = re.search(idea_pattern, log_content, re.DOTALL)
    if idea_match:
        extracted['Idea'] = idea_match.group(1)
    
    # 提取 Experiment
    exp_pattern = r'"Experiment":\s*"(.*?)"(?:\s*,\s*"Clarity"|$)'
    exp_match = re.search(exp_pattern, log_content, re.DOTALL)
    if exp_match:
        extracted['Experiment'] = exp_match.group(1)
    
    # 提取评分
    for metric in ['Clarity', 'Feasibility', 'Novelty']:
        pattern = rf'"{metric}":\s*(\d+)'
        match = re.search(pattern, log_content)
        if match:
            extracted[metric] = int(match.group(1))
    
    return extracted if extracted else None


def extract_idea_from_log(log_path: Path) -> Optional[Dict[str, Any]]:
    """
    从单个日志文件中提取 Final Idea
    """
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            log_content = f.read()
    except Exception as e:
        print(f"   ⚠️ 读取日志文件失败: {e}")
        return None
    
    # 尝试提取JSON
    data = extract_final_idea_json(log_content)
    
    if not data:
        # 回退方案
        data = extract_idea_text_fallback(log_content)
    
    return data


def format_idea_as_text(data: Dict[str, Any]) -> str:
    """
    将提取的 Idea 数据格式化为评估用的文本
    """
    title = data.get('Title', 'Unknown Title')
    idea = data.get('Idea', 'No abstract available')
    experiment = data.get('Experiment', 'No experiment design provided')
    
    # 组合成评估友好的格式
    text = f"""Title: {title}

Abstract: {idea}

Experiment Design: {experiment}
"""
    return text


def extract_paper_ids_from_text(text: str) -> List[str]:
    """
    从文本中提取引用的 Paper ID（如 10.1609/aaai.v36i4.20338）。
    """
    # 匹配 DOI 格式的 Paper ID
    doi_pattern = r'10\.\d{4,}/[^\s\)]+(?:\.[0-9]+)?'
    paper_ids = re.findall(doi_pattern, text)
    
    # 去重并保持顺序
    seen = set()
    unique_ids = []
    for pid in paper_ids:
        if pid not in seen:
            seen.add(pid)
            unique_ids.append(pid)
    
    return unique_ids


def extract_papers_from_log(log_path: Path) -> List[Dict[str, str]]:
    """
    从 virsci 日志中提取实际使用的 Paper Title 和 Abstract。
    
    日志格式示例：
    References: Paper 1:
    Title: GDA: Grammar-based Data Augmentation...
    Abstract: Recent studies propose...
    
    Paper 2:
    Title: ...
    Abstract: ...
    
    Returns:
        List of dicts with 'title' and 'abstract' keys (去重后)
    """
    papers = []
    seen_titles = set()  # 用于去重，避免重复提取相同的Paper
    
    if not log_path.exists():
        return papers
    
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取所有virsci实际使用的Paper，包括：
        # 1. "References:" 中的Paper（用于idea生成阶段）
        # 2. "The possible related papers are" 中的Paper（用于novelty检查阶段）
        # 合并去重，因为P指标需要所有实际使用的源文献
        
        # 1. 提取所有 "References:" 中的Paper
        # 注意：References后面可能有多个Paper（Paper 1, Paper 2, Paper 3...），需要匹配到所有Paper
        # 停止条件：遇到下一个References、Epoch、The possible related papers are或文件结尾
        ref_pattern = r'References:\s*(Paper\s+\d+:.*?)(?=References:|Epoch:|The possible related papers are|$)'
        ref_matches = list(re.finditer(ref_pattern, content, re.DOTALL))
        
        for match in ref_matches:
            block_text = match.group(1)
            paper_pattern = r'Paper\s+(\d+):\s*Title:\s*([^\n]+)\s*Abstract:\s*([^\n]+(?:\n(?!Paper\s+\d+:|Title:|Abstract:)[^\n]+)*)'
            paper_matches = re.finditer(paper_pattern, block_text, re.MULTILINE | re.DOTALL)
            
            for pm in paper_matches:
                title = pm.group(2).strip()
                abstract = pm.group(3).strip()
                abstract = re.sub(r'}\s*$', '', abstract).strip()
                
                # 去重：只添加未出现过的Title
                title_normalized = title.lower().strip()
                if title and abstract and title_normalized not in seen_titles:
                    seen_titles.add(title_normalized)
                    papers.append({
                        'title': title,
                        'abstract': abstract  # 保留完整abstract，不截断
                    })
        
        # 2. 提取所有 "The possible related papers are" 中的Paper（用于novelty检查）
        primary_pattern = r'The possible related papers are\s*(Paper\s+\d+:.*?)(?=Epoch:|The possible related papers are|$)'
        primary_matches = list(re.finditer(primary_pattern, content, re.DOTALL))
        
        if primary_matches:
            # 合并所有位置的Paper（virsci会为多个idea检索，然后合并去重）
            for match in primary_matches:
                block_text = match.group(1)
                paper_pattern = r'Paper\s+(\d+):\s*Title:\s*([^\n]+)\s*Abstract:\s*([^\n]+(?:\n(?!Paper\s+\d+:|Title:|Abstract:)[^\n]+)*)'
                paper_matches = re.finditer(paper_pattern, block_text, re.MULTILINE | re.DOTALL)
                
                for pm in paper_matches:
                    title = pm.group(2).strip()
                    abstract = pm.group(3).strip()
                    abstract = re.sub(r'}\s*$', '', abstract).strip()
                    
                    # 去重：只添加未出现过的Title（合并所有位置的Paper）
                    title_normalized = title.lower().strip()
                    if title and abstract and title_normalized not in seen_titles:
                        seen_titles.add(title_normalized)
                        papers.append({
                            'title': title,
                            'abstract': abstract  # 保留完整abstract，不截断
                        })
        
    except Exception as e:
        print(f"   ⚠️  从日志提取 Paper 失败: {e}")
        if 'DEBUG' in os.environ:
            import traceback
            traceback.print_exc()
    
    return papers


def find_paper_id_by_title(
    title: str,
    vector_storage,
    embedding_model,
    max_candidates: int = 10
) -> Optional[str]:
    """
    通过 Title 在向量数据库中查找对应的 Paper ID。
    
    Args:
        title: Paper 标题
        vector_storage: 向量数据库存储对象
        embedding_model: 嵌入模型
        max_candidates: 最大候选数量
    
    Returns:
        Paper ID (DOI) 或 None
    """
    try:
        # 使用 Title 进行向量检索
        query_vec = np.array(embedding_model.embed(obj=title), dtype=np.float32)
        results = vector_storage.query(VectorDBQuery(query_vector=query_vec, top_k=max_candidates))
        
        if not results:
            return None
        
        # 精确匹配 Title（忽略大小写和标点）
        title_normalized = re.sub(r'[^\w\s]', '', title.lower()).strip()
        
        for res in results:
            payload = res.record.payload
            stored_title = payload.get("title", "")
            stored_title_normalized = re.sub(r'[^\w\s]', '', stored_title.lower()).strip()
            
            # 如果标题匹配（允许部分匹配，因为可能有副标题等）
            if title_normalized and stored_title_normalized:
                # 检查是否包含主要部分（至少70%的单词匹配）
                title_words = set(title_normalized.split())
                stored_words = set(stored_title_normalized.split())
                
                if len(title_words) > 0 and len(stored_words) > 0:
                    overlap = len(title_words & stored_words)
                    similarity_ratio = overlap / max(len(title_words), len(stored_words))
                    
                    if similarity_ratio >= 0.7:  # 70% 相似度阈值
                        # 提取 Paper ID
                        paper_id = payload.get("paper_id") or payload.get("id") or payload.get("doi") or payload.get("source_id")
                        if paper_id:
                            return str(paper_id)
        
        # 如果没有精确匹配，返回相似度最高的候选的 Paper ID
        if results:
            best_result = results[0]
            payload = best_result.record.payload
            paper_id = payload.get("paper_id") or payload.get("id") or payload.get("doi") or payload.get("source_id")
            if paper_id:
                return str(paper_id)
        
    except Exception as e:
        if 'DEBUG' in os.environ:
            print(f"      ⚠️  查找 Paper ID 失败 (Title: {title[:50]}...): {e}")
    
    return None


def collect_source_documents_for_virsci(
    idea_text: str,
    research_topic: str,
    calculator: Optional[ScientificMetricsCalculator],
    log_path: Optional[Path] = None,
    max_docs: int = 20,
    vdb_path: Optional[str] = None
) -> tuple[List[str], str]:
    """
    为 virsci Final Idea 收集源文献（溯源实际RAG调用的文献）
    
    优先级：
    1. 从日志中提取实际使用的 Paper Title，然后通过 Title 查找 Paper ID（溯源）
    2. 从 Idea 文本中提取 Paper ID
    3. 使用向量检索检索相关文献（基于研究问题和 idea 文本，仅作为备选）
    
    Args:
        idea_text: Idea 文本
        research_topic: 研究问题（从目录名提取）
        calculator: 评估器（可选，用于向量检索）
        log_path: virsci 日志文件路径（用于溯源实际使用的Paper）
        max_docs: 最大检索数量
        vdb_path: 向量数据库路径（可选）
    
    Returns:
        tuple: (paper_ids列表, 溯源方式标识)
        溯源方式标识: "日志溯源" | "Idea文本提取" | "RAG向量检索" | "未找到"
    """
    collected: List[str] = []
    source_type = "未找到"  # 溯源方式标识

    # 1. 优先从日志中提取实际使用的 Paper（溯源）
    if log_path and log_path.exists():
        print("   🔍 从日志中溯源实际RAG调用的文献...")
        try:
            papers_from_log = extract_papers_from_log(log_path)
            
            if papers_from_log:
                print(f"   ✅ 从日志中提取到 {len(papers_from_log)} 篇实际使用的 Paper")
                
                # 设置向量数据库路径
                if not vdb_path:
                    base_vdb_path = os.path.join(PROJECT_ROOT, 'Myexamples/vdb/camel_faiss_storage')
                else:
                    base_vdb_path = vdb_path
                
                # 初始化 embedding 模型和向量数据库
                storage_path = os.path.join(base_vdb_path, "paper/abstract")
                if not os.path.exists(storage_path):
                    storage_path = os.path.join(base_vdb_path, "abstract")
                
                if os.path.exists(storage_path):
                    embedding_model = OpenAICompatibleEmbedding(
                        model_type="text-embedding-v2",
                        api_key=os.environ.get("QWEN_API_KEY"),
                        url=os.environ.get("QWEN_API_BASE_URL")
                    )
                    
                    vector_storage = FaissStorage(
                        vector_dim=1536,
                        storage_path=storage_path,
                        collection_name="paper_abstract"
                    )
                    vector_storage.load()
                    
                    # 通过 Title 查找每篇 Paper 的 ID
                    found_count = 0
                    for paper in papers_from_log:
                        title = paper['title']
                        abstract = paper.get('abstract', '')
                        # 使用Title和Abstract的前200字符一起查找，提高匹配准确度
                        query_text = f"{title}\n{abstract[:200]}" if abstract else title
                        paper_id = find_paper_id_by_title(query_text, vector_storage, embedding_model)
                        if paper_id:
                            if paper_id not in collected:
                                collected.append(paper_id)
                                found_count += 1
                    
                    if found_count > 0:
                        source_type = "日志溯源"
                        print(f"   ✅ 成功溯源 {found_count} 篇文献的 Paper ID (方式: {source_type})")
                    else:
                        print(f"   ⚠️  未能通过 Title 找到 Paper ID，将使用备选方案")
                else:
                    print(f"   ⚠️  向量数据库路径不存在，无法溯源 Paper ID")
        except Exception as e:
            print(f"   ⚠️  从日志溯源失败: {e}")
            if 'DEBUG' in os.environ:
                import traceback
                traceback.print_exc()
    
    # 2. 从 Idea 文本中提取 Paper ID（备选方案）
    if not collected:
        paper_ids = extract_paper_ids_from_text(idea_text)
        if paper_ids:
            # 去重：只添加不在collected中的ID
            new_ids = [pid for pid in paper_ids if pid not in collected]
            if new_ids:
                source_type = "Idea文本提取"
                print(f"   ✅ 从 Idea 文本中提取 {len(new_ids)} 个 Paper ID (方式: {source_type})")
                collected.extend(new_ids)

    # 3. 如果还没有找到源文献，使用向量检索检索相关文献（仅作为最后备选）
    # 注意：如果已经从日志溯源到实际使用的Paper，就不再使用向量检索，避免虚假的相似度计算
    if not collected and VECTOR_RETRIEVAL_AVAILABLE and research_topic:
        print("   🔍 使用向量检索检索相关文献...")
        try:
            # 构建查询（参考 batch_evaluate_ai_scientist.py：使用研究主题和idea的前500字符）
            query = f"{research_topic}\n\n{idea_text[:500]}"
            
            # 设置向量数据库路径
            if not vdb_path:
                base_vdb_path = os.path.join(PROJECT_ROOT, 'Myexamples/vdb/camel_faiss_storage')
            else:
                base_vdb_path = vdb_path
            
            # 初始化 embedding 模型
            embedding_model = OpenAICompatibleEmbedding(
                model_type="text-embedding-v2",
                api_key=os.environ.get("QWEN_API_KEY"),
                url=os.environ.get("QWEN_API_BASE_URL")
            )
            
            # 加载向量数据库（paper/abstract）
            storage_path = os.path.join(base_vdb_path, "paper/abstract")
            if not os.path.exists(storage_path):
                storage_path = os.path.join(base_vdb_path, "abstract")
            
            if not os.path.exists(storage_path):
                print(f"   ⚠️  向量数据库路径不存在: {storage_path}")
            else:
                vector_storage = FaissStorage(
                    vector_dim=1536,
                    storage_path=storage_path,
                    collection_name="paper_abstract"
                )
                vector_storage.load()
                
                # 向量检索（动态计算检索数量，基于相似度分数）
                # 参考 metrics_calculator.py：使用较大的 search_k 获取候选，然后根据相似度动态过滤
                query_vec = np.array(embedding_model.embed(obj=query), dtype=np.float32)
                
                # 获取足够多的候选（参考 metrics_calculator.py 使用 search_k=500）
                # 使用较大的值以确保有足够的候选进行动态筛选，避免硬编码限制
                search_k = 200  # 获取200个候选，然后根据相似度动态筛选
                results = vector_storage.query(VectorDBQuery(query_vector=query_vec, top_k=search_k))
                
                if not results:
                    print("   ℹ️  向量检索未返回结果")
                else:
                    # 提取结果并计算相似度分数
                    candidate_papers = []
                    for res in results:
                        payload = res.record.payload
                        similarity = res.similarity
                        
                        # 优先从 payload 中提取 Paper ID
                        paper_id = payload.get("paper_id") or payload.get("id") or payload.get("doi") or payload.get("source_id")
                        if not paper_id:
                            # 如果没有直接的 ID，尝试从其他字段提取
                            for key in ["title", "abstract", "text"]:
                                text = payload.get(key, "")
                                if text:
                                    doi_matches = re.findall(r'10\.\d{4,}/[^\s\)]+', str(text))
                                    if doi_matches:
                                        paper_id = doi_matches[0]  # 取第一个匹配的 DOI
                                        break
                        
                        if paper_id:
                            candidate_papers.append({
                                "paper_id": str(paper_id),
                                "similarity": similarity
                            })
                    
                    if candidate_papers:
                        # 先对 candidate_papers 去重（保留相似度最高的）
                        paper_id_to_best = {}
                        for paper in candidate_papers:
                            paper_id = paper["paper_id"]
                            if paper_id not in paper_id_to_best or paper["similarity"] > paper_id_to_best[paper_id]["similarity"]:
                                paper_id_to_best[paper_id] = paper
                        candidate_papers = list(paper_id_to_best.values())
                        
                        # 按相似度排序
                        candidate_papers.sort(key=lambda x: x["similarity"], reverse=True)
                        
                        # 使用Elbow方法（肘部法则）找到最佳截断点
                        # 计算相似度的变化率，找到变化率突然增大的点（elbow point）
                        similarities = [p["similarity"] for p in candidate_papers]
                        max_sim = similarities[0] if similarities else 0
                        min_sim = similarities[-1] if similarities else 0
                        min_papers = 5  # 最少保留5篇（参考virsci的cite_number通常是3-8）
                        
                        if len(candidate_papers) <= min_papers:
                            # 如果候选太少，全部保留
                            selected_papers = candidate_papers
                            filter_reason = "候选数量不足，全部保留"
                        else:
                            # 计算相似度的变化率（一阶导数）
                            changes = []
                            for i in range(1, len(candidate_papers)):
                                prev_sim = candidate_papers[i-1]["similarity"]
                                curr_sim = candidate_papers[i]["similarity"]
                                change = prev_sim - curr_sim
                                changes.append(change)
                            
                            # 使用滑动窗口计算平均变化率，找到变化率突然增大的点
                            window_size = max(5, min(15, len(changes) // 4))  # 窗口大小为总数的1/4，范围5-15
                            
                            # 计算每个位置的平均变化率
                            avg_changes = []
                            for i in range(len(changes)):
                                start = max(0, i - window_size // 2)
                                end = min(len(changes), i + window_size // 2 + 1)
                                window_changes = changes[start:end]
                                if window_changes:
                                    avg_change = np.mean(window_changes)
                                    avg_changes.append(avg_change)
                                else:
                                    avg_changes.append(0)
                            
                            # 找到elbow point：变化率超过阈值的位置
                            # 使用更宽松的阈值：均值 + 1.0倍标准差（而不是1.5倍）
                            if len(avg_changes) > 0:
                                mean_change = np.mean(avg_changes)
                                std_change = np.std(avg_changes) if len(avg_changes) > 1 else 0.01
                                # 使用更宽松的阈值，避免过早截断
                                threshold_change = mean_change + 1.0 * std_change
                                
                                # 找到第一个超过阈值的变化点（elbow point）
                                # 但要求变化率明显大于平均值（至少是平均值的1.5倍）
                                elbow_idx = None
                                for i, avg_change in enumerate(avg_changes):
                                    # 确保至少有min_papers篇，且变化率明显超过阈值
                                    if avg_change > threshold_change and avg_change > mean_change * 1.5 and (i + 1) >= min_papers:
                                        elbow_idx = i + 1  # +1 因为changes的索引对应candidate_papers的i+1位置
                                        break
                                
                                # 如果没找到elbow point，使用相对阈值方法
                                if elbow_idx is None:
                                    # 方法1：保留相似度 >= (最高相似度 - 0.12) 的文献（更宽松）
                                    relative_threshold = max_sim - 0.12
                                    elbow_idx = len(candidate_papers)
                                    for i, paper in enumerate(candidate_papers):
                                        if paper["similarity"] < relative_threshold and i >= min_papers:
                                            elbow_idx = i
                                            break
                                    
                                    # 方法2：如果相对阈值方法还是保留了太多，使用百分位数
                                    if elbow_idx > 50:  # 如果还是超过50篇
                                        # 保留前80%的相似度范围（而不是75%）
                                        percentile_80 = np.percentile(similarities, 80)
                                        for i, paper in enumerate(candidate_papers):
                                            if paper["similarity"] < percentile_80 and i >= min_papers:
                                                elbow_idx = i
                                                break
                                
                                # 确保至少保留min_papers篇，但不超过合理范围
                                elbow_idx = max(min_papers, min(elbow_idx, len(candidate_papers)))
                                selected_papers = candidate_papers[:elbow_idx]
                                
                                filter_reason = f"Elbow方法截断 (位置: {elbow_idx}, 阈值: {threshold_change:.3f})"
                            else:
                                # 降级：使用简单的相对阈值
                                relative_threshold = max_sim - 0.12
                                selected_papers = [p for p in candidate_papers if p["similarity"] >= relative_threshold]
                                if len(selected_papers) < min_papers:
                                    selected_papers = candidate_papers[:min_papers]
                                filter_reason = f"相对阈值过滤 (>= {relative_threshold:.2f})"
                        
                        paper_ids = [p["paper_id"] for p in selected_papers]
                        # 去重：只添加不在collected中的ID
                        new_ids = [pid for pid in paper_ids if pid not in collected]
                        if new_ids:
                            source_type = "RAG向量检索"
                            sim_range_str = f"{selected_papers[-1]['similarity']:.3f}-{selected_papers[0]['similarity']:.3f}" if selected_papers else "N/A"
                            print(f"   ✅ 从向量检索找到 {len(new_ids)} 篇相关文献 (方式: {source_type}, {filter_reason}, 相似度: {sim_range_str})")
                            collected.extend(new_ids)
                        else:
                            print(f"   ℹ️  向量检索找到的文献均已存在，跳过添加")
                    else:
                        print("   ℹ️  向量检索未返回有效的 Paper ID")
        
        except Exception as e:
            print(f"   ⚠️ 向量检索失败: {e}")
            if 'DEBUG' in os.environ:
                import traceback
                traceback.print_exc()

    # 去重
    deduped = []
    seen = set()
    for doc in collected:
        doc_clean = doc.strip()
        if doc_clean and doc_clean not in seen:
            seen.add(doc_clean)
            deduped.append(doc_clean)

    if not deduped:
        print("   ⚠️ 未能提取到源文献，P 指标将缺失")
        source_type = "未找到"
    else:
        print(f"   📊 共收集 {len(deduped)} 篇源文献用于 P 指标计算 (溯源方式: {source_type})")

    # 参考 batch_evaluate_ai_scientist.py：不限制数量，返回所有找到的源文献
    # 它从 RAG 结果中提取所有 Paper ID，不限制数量
    return deduped, source_type


def extract_core_content_for_virsci(idea_text: str, min_length: int = 2000) -> str:
    """
    专门为 virsci Final Idea 格式提取核心内容
    
    策略：
    1. 优先提取 Abstract（最重要的内容，包含完整的研究想法）
    2. 如果 Abstract 不够长，补充 Experiment Design 的前半部分
    3. 确保提取的文本包含完整的核心信息，至少 min_length 字符
    
    Args:
        idea_text: 格式化的 Idea 文本
        min_length: 最小提取长度（默认2000字符）
    
    Returns:
        提取的核心文本，用于 embedding 计算
    """
    # 提取 Abstract 部分（最重要的内容）
    abstract_match = re.search(r'Abstract:\s*(.+?)(?=\n(?:Experiment|Quality|$))', idea_text, re.DOTALL)
    abstract = abstract_match.group(1).strip() if abstract_match else ""
    
    # 提取 Experiment Design 部分
    experiment_match = re.search(r'Experiment Design:\s*(.+?)(?=\n(?:Quality|$))', idea_text, re.DOTALL)
    experiment = experiment_match.group(1).strip() if experiment_match else ""
    
    # 提取 Title
    title_match = re.search(r'Title:\s*(.+?)(?=\n(?:Abstract|$))', idea_text, re.DOTALL)
    title = title_match.group(1).strip() if title_match else ""
    
    # 构建核心文本：优先使用 Abstract，如果不够长则补充 Experiment
    core_parts = []
    
    # 1. 添加 Title（简短，提供上下文）
    if title:
        core_parts.append(f"Title: {title}")
    
    # 2. 添加完整的 Abstract（最重要，包含研究想法的核心内容）
    if abstract:
        core_parts.append(f"Abstract: {abstract}")
    
    # 3. 如果总长度不够 min_length，补充 Experiment Design 的前半部分
    current_text = "\n\n".join(core_parts)
    if len(current_text) < min_length and experiment:
        # 计算需要补充多少 Experiment 内容
        needed_length = min_length - len(current_text) + 200  # 多取一些，避免截断
        if needed_length > 0:
            # 优先取 Experiment 的前半部分（通常包含更重要的设计思路）
            experiment_to_add = experiment[:needed_length]
            # 尝试在句子边界截断
            last_period = experiment_to_add.rfind('.')
            if last_period > needed_length * 0.7:  # 如果句号位置合理
                experiment_to_add = experiment_to_add[:last_period + 1]
            core_parts.append(f"Experiment Design: {experiment_to_add}")
    
    result = "\n\n".join(core_parts)
    
    # 如果还是不够长，使用原始文本（但优先保证 Abstract 完整）
    if len(result) < min_length:
        # 如果 Abstract 存在，至少保证 Abstract 完整
        if abstract and len(abstract) > 500:
            # Abstract 足够长，直接使用
            result = f"Title: {title}\n\nAbstract: {abstract}" if title else f"Abstract: {abstract}"
            # 如果还是不够，补充 Experiment 的开头
            if len(result) < min_length and experiment:
                remaining = min_length - len(result) + 200
                result += f"\n\nExperiment Design: {experiment[:remaining]}"
        else:
            # Abstract 太短或不存在，使用原始文本
            result = idea_text[:min_length]
    
    return result


def find_latest_log_file(log_dir: Path) -> Optional[Path]:
    """
    在目录中找到最新的日志文件（通常是 *_2,1_dialogue.log 或 *_1,1_dialogue.log）
    """
    log_files = list(log_dir.glob("*_*_dialogue.log"))
    if not log_files:
        return None
    
    # 优先选择 *_2,1_dialogue.log（通常是最终版本）
    priority_files = [f for f in log_files if "_2,1_dialogue.log" in f.name]
    if priority_files:
        # 返回最新的
        return max(priority_files, key=lambda f: f.stat().st_mtime)
    
    # 否则返回最新的任意日志文件
    return max(log_files, key=lambda f: f.stat().st_mtime)


def extract_research_question_from_txt(txt_file: Path) -> Optional[str]:
    """
    从txt文件中提取研究问题（格式：问题文本: How can...）
    
    Args:
        txt_file: txt文件路径
        
    Returns:
        研究问题文本，如果找不到则返回None
    """
    try:
        with open(txt_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找"问题文本:"后面的内容
        # 匹配格式：问题文本: How can...
        pattern = r'问题文本:\s*(How[^\n]+(?:\?|\.))'
        match = re.search(pattern, content, re.IGNORECASE)
        
        if match:
            research_question = match.group(1).strip()
            # 确保以How开头
            if research_question.startswith('How'):
                return research_question
        
        # 如果没找到，尝试更宽松的匹配
        pattern2 = r'问题文本:\s*(.+?)(?:\n|$)'
        match2 = re.search(pattern2, content)
        if match2:
            research_question = match2.group(1).strip()
            if research_question.startswith('How'):
                return research_question
        
        return None
    except Exception as e:
        print(f"   ⚠️ 读取txt文件失败: {e}")
        return None


def collect_virsci_ideas(logs_dir: Path) -> List[Dict[str, Any]]:
    """
    收集所有 virsci 日志目录中的 Final Idea
    """
    ideas = []
    
    # 查找对应的txt文件目录（batch_results/virsci）
    # logs_dir 通常是 batch_results/virsci/logs
    # txt文件在 batch_results/virsci/ 目录下
    txt_dir = logs_dir.parent if logs_dir.name == "logs" else logs_dir.parent / "virsci"
    
    # 遍历所有子目录
    for rq_dir in sorted(logs_dir.iterdir()):
        if not rq_dir.is_dir():
            continue
        
        print(f"\n📁 处理目录: {rq_dir.name}")
        
        # 查找最新的日志文件
        log_file = find_latest_log_file(rq_dir)
        if not log_file:
            print(f"   ⚠️ 未找到日志文件，跳过")
            continue
        
        print(f"   📄 读取日志: {log_file.name}")
        
        # 提取 Final Idea
        idea_data = extract_idea_from_log(log_file)
        if not idea_data:
            print(f"   ⚠️ 无法提取 Final Idea，跳过")
            continue
        
        # 提取研究问题（从对应的txt文件）
        rq_match = re.search(r'_RQ_(\d+)$', rq_dir.name)
        rq_number = rq_match.group(1) if rq_match else "Unknown"
        
        # 查找对应的txt文件（格式：目录名.txt）
        txt_file = txt_dir / f"{rq_dir.name}.txt"
        research_question = None
        
        if txt_file.exists():
            print(f"   📝 从txt文件提取研究问题: {txt_file.name}")
            research_question = extract_research_question_from_txt(txt_file)
            if research_question:
                print(f"   ✅ 提取到研究问题: {research_question[:80]}...")
            else:
                print(f"   ⚠️ 未能在txt文件中找到研究问题")
        else:
            print(f"   ⚠️ 未找到对应的txt文件: {txt_file}")
            # 降级：从目录名提取（去掉 _RQ_X 后缀，将下划线替换为空格）
            research_question = rq_dir.name
            if rq_match:
                research_question = research_question[:rq_match.start()]
            research_question = research_question.replace("_", " ").strip()
            print(f"   ℹ️ 使用目录名作为研究问题: {research_question[:80]}...")
        
        ideas.append({
            "rq_dir": rq_dir.name,
            "rq_number": rq_number,
            "log_file": str(log_file),
            "log_path": log_file,  # 添加 log_path 用于溯源
            "idea_data": idea_data,
            "idea_text": format_idea_as_text(idea_data),
            "research_topic": research_question or ""  # 使用从txt文件提取的研究问题
        })
        
        print(f"   ✅ 成功提取 Final Idea (Title: {idea_data.get('Title', 'N/A')[:50]}...)")
    
    return ideas


def flatten_dict(data: Any, parent_key: str = "", sep: str = ".", output: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """递归扁平化字典/列表结果，便于写入表格。"""
    if output is None:
        output = {}
    
    if isinstance(data, dict):
        for key, value in data.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else str(key)
            flatten_dict(value, new_key, sep, output)
    elif isinstance(data, list):
        output[parent_key] = json.dumps(data, ensure_ascii=False)
    else:
        output[parent_key] = data
    return output


def evaluate_virsci_ideas(
    ideas: List[Dict[str, Any]],
    calculator: ScientificMetricsCalculator,
    llm_evaluator: Optional[ScientificLLMEvaluator],
    skip_llm: bool = False
) -> List[Dict[str, Any]]:
    """
    评估所有收集到的 virsci ideas
    """
    evaluations = []
    
    for idx, idea_info in enumerate(ideas, 1):
        print("\n" + "=" * 80)
        print(f"[{idx}/{len(ideas)}] 评估: {idea_info['rq_dir']}")
        print("=" * 80)
        
        idea_text = idea_info['idea_text']
        idea_data = idea_info['idea_data']
        
        # 使用专门为 virsci 设计的提取函数
        core_text = extract_core_content_for_virsci(idea_text, min_length=2000)
        print(f" - 核心文本长度: {len(core_text)}")
        print(f" - 文本预览: {core_text[:150]}...")
        
        # 获取研究问题（从目录名提取，参考 batch_evaluate_ai_scientist.py）
        research_topic = idea_info.get('research_topic', '')
        if not research_topic:
            # 如果没有，使用 Title 作为备选
            research_topic = idea_data.get('Title', '') or idea_data.get('Idea', '')[:200]
        print(f" - 研究问题: {research_topic[:80]}..." if research_topic else " - 研究问题: 未知")
        
        # 收集源文献（优先从日志溯源实际RAG调用的文献）
        vdb_path = os.path.join(PROJECT_ROOT, 'Myexamples/vdb/camel_faiss_storage')
        log_path = idea_info.get('log_path')
        if log_path:
            log_path = Path(log_path)
        source_docs, source_type = collect_source_documents_for_virsci(
            idea_text=idea_text,
            research_topic=research_topic,
            calculator=calculator,
            log_path=log_path,  # 传递日志路径用于溯源
            max_docs=20,
            vdb_path=vdb_path
        )
        
        print(f" - 溯源文档数: {len(source_docs)} (溯源方式: {source_type})")
        
        # 计算客观指标（ON_v2 和 P 指标）
        # 注意：即使 source_docs 为空，也应该传入，让 calculator 处理
        print(" - 计算客观指标...")
        objective_metrics = calculator.evaluate_text(
            core_text, 
            source_documents=source_docs if source_docs else None
        )
        
        # 计算主观指标（LLM 评分）
        subjective_metrics: Dict[str, Any]
        if llm_evaluator and not skip_llm:
            print(" - 计算主观指标（LLM评分）...")
            subjective_metrics = llm_evaluator.absolute_evaluation(core_text)
        else:
            subjective_metrics = {"Skipped": True}
        
        evaluation_payload = {
            "metadata": {
                "rq_dir": idea_info['rq_dir'],
                "rq_number": idea_info['rq_number'],
                "log_file": idea_info['log_file'],
                "title": idea_data.get('Title', 'Unknown'),
                "clarity": idea_data.get('Clarity', 'N/A'),
                "feasibility": idea_data.get('Feasibility', 'N/A'),
                "novelty": idea_data.get('Novelty', 'N/A'),
                "source_document_count": len(source_docs),
                "source_trace_method": source_type,  # 溯源方式标识
                "timestamp": datetime.now().isoformat(),
            },
            "metrics": {
                "objective": objective_metrics,
                "subjective_llm": subjective_metrics,
            },
        }
        
        evaluations.append(evaluation_payload)
        print(f"   ✅ 评估完成")
    
    # ON 归一化
    try:
        evaluations = ScientificMetricsCalculator.normalize_on_scores(evaluations)
        print("\n✅ ON 归一化完成")
    except Exception as exc:
        print(f"\n⚠️ ON 归一化失败: {exc}")
    
    return evaluations


def export_to_excel(evaluations: List[Dict[str, Any]], excel_path: Path) -> None:
    """导出评估结果到 Excel"""
    rows: List[Dict[str, Any]] = []
    
    for item in evaluations:
        row: Dict[str, Any] = {}
        row.update(item.get("metadata", {}))
        metrics = item.get("metrics", {})
        flatten_dict(metrics.get("objective", {}), parent_key="objective", output=row)
        flatten_dict(metrics.get("subjective_llm", {}), parent_key="subjective_llm", output=row)
        row["raw_json"] = json.dumps(item, ensure_ascii=False)
        rows.append(row)
    
    df = pd.DataFrame(rows)
    excel_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(excel_path, index=False)
    
    # 输出完整路径
    full_path = excel_path.resolve()
    print(f"\n✅ 指标写入 Excel")
    print(f"   文件路径: {full_path}")
    print(f"   共写入 {len(df)} 行，字段数 {len(df.columns)}")
    print(f"   文件大小: {full_path.stat().st_size / 1024:.2f} KB")


def main() -> None:
    parser = argparse.ArgumentParser(description="批量评估 Virtual-Scientists 生成结果")
    parser.add_argument("--logs-dir", type=str, required=True,
                        help="virsci 日志目录路径")
    parser.add_argument("--output-excel", type=str, required=True,
                        help="输出 Excel 路径")
    parser.add_argument("--json-data", type=str, 
                        default="Myexamples/data/final_data/final_custom_kg_papers.json",
                        help="包含年份/引文元数据的 JSON")
    parser.add_argument("--vdb-path", type=str, 
                        default="Myexamples/vdb/camel_faiss_storage",
                        help="向量数据库路径")
    parser.add_argument("--skip-llm", action="store_true",
                        help="跳过 LLM 主观评估（仅测试用途）")
    parser.add_argument("--start-index", type=int, default=1,
                        help="起始序号（默认 1）")
    parser.add_argument("--end-index", type=int, default=None,
                        help="结束序号（默认处理全部）")
    parser.add_argument("--limit", type=int, default=None,
                        help="限定最多处理的日志数量")
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("🚀 批量评估 Virtual-Scientists 生成结果")
    print("=" * 80)
    print(f"日志目录: {args.logs_dir}")
    print(f"输出 Excel: {args.output_excel}")
    print(f"跳过 LLM: {args.skip_llm}")
    print("=" * 80)
    
    # 准备环境
    ensure_env_defaults()
    
    # 检查目录
    logs_dir = Path(args.logs_dir)
    if not logs_dir.exists():
        raise FileNotFoundError(f"日志目录不存在: {logs_dir}")
    
    # 收集所有 Final Ideas
    print("\n📚 收集所有 Final Ideas...")
    all_ideas = collect_virsci_ideas(logs_dir)
    
    if not all_ideas:
        print("❌ 未找到任何有效的 Final Idea")
        return
    
    print(f"\n✅ 共收集到 {len(all_ideas)} 个 Final Ideas")
    
    # 根据索引范围裁剪
    start_idx = max(args.start_index, 1)
    end_idx = args.end_index or len(all_ideas)
    selected = all_ideas[start_idx - 1:end_idx]
    if args.limit is not None:
        selected = selected[:args.limit]
    
    print(f"📊 准备处理 {len(selected)} 个 Final Ideas")
    
    # 初始化评估器
    print("\n🔧 初始化评估器...")
    embedding_model = OpenAICompatibleEmbedding(
        model_type="text-embedding-v2",
        api_key=os.environ.get("OPENAI_COMPATIBILITY_API_KEY"),
        url=os.environ.get("OPENAI_COMPATIBILITY_API_BASE_URL"),
    )
    calculator = ScientificMetricsCalculator(args.vdb_path, embedding_model)
    calculator.load_resources(args.json_data)
    
    llm_evaluator: Optional[ScientificLLMEvaluator] = None
    if not args.skip_llm:
        llm_evaluator = ScientificLLMEvaluator()
    
    # 评估所有 ideas
    evaluations = evaluate_virsci_ideas(
        selected,
        calculator,
        llm_evaluator,
        skip_llm=args.skip_llm
    )
    
    # 导出到 Excel
    excel_path = Path(args.output_excel)
    # 如果是相对路径，转换为绝对路径
    if not excel_path.is_absolute():
        excel_path = (Path.cwd() / excel_path).resolve()
    
    export_to_excel(evaluations, excel_path)
    
    print("\n" + "=" * 80)
    print("🎉 批量评估完成！")
    print("=" * 80)
    print(f"\n📊 Excel 文件已生成:")
    print(f"   {excel_path.resolve()}")
    print("=" * 80)


if __name__ == "__main__":
    main()

