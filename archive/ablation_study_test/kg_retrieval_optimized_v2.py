#!/usr/bin/env python3
"""
优化版知识图谱检索 V2
针对消融实验结果改进：
1. 语义匹配优先（而非关键词匹配）
2. RQ-focused 检索策略
3. 相关性过滤
4. 智能融合排序
"""

import sys
sys.path.insert(0, '/root/autodl-tmp')
sys.path.insert(0, '/root/autodl-tmp/Myexamples/ablation_study_test')

from neo4j import GraphDatabase
from camel.embeddings import OpenAICompatibleEmbedding
from camel.storages import FaissStorage, VectorDBQuery
from typing import List, Dict, Any, Tuple
import os
import numpy as np
from dataclasses import dataclass

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "neo4j123"


@dataclass
class KGRetrievalResult:
    """KG检索结果"""
    paper_doi: str
    paper_title: str
    paper_year: str
    paper_conference: str
    core_problem: str
    abstract: str
    rq_idx: int
    rq_name: str
    research_question: str
    solution: str
    relevance_score: float  # 与查询的相关性分数
    match_type: str  # 'semantic', 'keyword', 'hybrid'


class OptimizedKGRetriever:
    """
    优化版KG检索器
    核心改进：
    1. 使用向量相似度进行语义匹配
    2. RQ-focused 检索（RQ是核心）
    3. 多级相关性过滤
    4. 智能重排序
    """
    
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        
        # 初始化嵌入模型
        self.embedding_model = OpenAICompatibleEmbedding(
            model_type="text-embedding-v2",
            api_key=os.environ.get("OPENAI_COMPATIBILITY_API_KEY", "sk-c1a6b588f7d543adb0412c5bc61bdd7b"),
            url=os.environ.get("OPENAI_COMPATIBILITY_API_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        )
        
        # 加载向量存储
        self._load_vector_storages()
    
    def _load_vector_storages(self):
        """加载FAISS向量存储"""
        base_path = '/root/autodl-tmp/Myexamples/vdb/camel_faiss_storage'
        
        self.storages = {}
        configs = [
            ('paper', 'abstract'),
            ('paper', 'core_problem'),
            ('research_question', 'research_question'),
            ('solution', 'solution'),
        ]
        
        for entity_type, attr in configs:
            storage_path = os.path.join(base_path, entity_type, attr)
            index_file = os.path.join(storage_path, f"{entity_type}_{attr}.index")
            
            if os.path.exists(index_file):
                storage = FaissStorage(
                    vector_dim=self.embedding_model.get_output_dim(),
                    storage_path=storage_path,
                    collection_name=f"{entity_type}_{attr}",
                )
                storage.load()
                self.storages[f"{entity_type}_{attr}"] = storage
                print(f"✅ 加载: {entity_type}.{attr}")
    
    def close(self):
        self.driver.close()
    
    def semantic_search_rq(self, query: str, top_k: int = 10) -> List[Dict]:
        """
        语义检索：直接在ResearchQuestion上进行向量搜索
        这是最核心的检索方式
        """
        query_embedding = self.embedding_model.embed(obj=query)
        
        # 在RQ向量空间中搜索
        storage = self.storages.get('research_question_research_question')
        if not storage or storage.status().vector_count == 0:
            return []
        
        db_query = VectorDBQuery(query_vector=query_embedding, top_k=top_k)
        results = storage.query(query=db_query)
        
        matched_rqs = []
        for res in results:
            payload = res.record.payload
            matched_rqs.append({
                'paper_id': payload.get('paper_id'),
                'rq_text': payload.get('text', ''),
                'similarity': res.similarity,
            })
        
        return matched_rqs
    
    def get_paper_hierarchy_by_doi(self, doi: str, rq_text_filter: str = None) -> List[KGRetrievalResult]:
        """
        根据DOI获取Paper完整层级
        可选：只返回匹配特定RQ的层级
        """
        query = """
        MATCH (p:Paper {doi: $doi})
        OPTIONAL MATCH (p)-[:raise]->(rq:ResearchQuestion)-[:solved_by]->(sol:Solution)
        RETURN 
            p.doi as paper_doi,
            p.title as paper_title,
            p.year as paper_year,
            p.conference as paper_conference,
            p.core_problem as core_problem,
            p.abstract as abstract,
            rq.idx as rq_idx,
            rq.name as rq_name,
            rq.research_question as research_question,
            sol.solution as solution
        """
        
        with self.driver.session() as session:
            result = session.run(query, doi=doi)
            records = []
            for record in result:
                rec = dict(record)
                # 如果指定了RQ过滤，只返回匹配的
                if rq_text_filter and rq_text_filter not in rec.get('research_question', ''):
                    continue
                
                records.append(KGRetrievalResult(
                    paper_doi=rec['paper_doi'],
                    paper_title=rec['paper_title'],
                    paper_year=rec['paper_year'],
                    paper_conference=rec['paper_conference'],
                    core_problem=rec['core_problem'] or '',
                    abstract=rec['abstract'] or '',
                    rq_idx=rec['rq_idx'] or 0,
                    rq_name=rec['rq_name'] or '',
                    research_question=rec['research_question'] or '',
                    solution=rec['solution'] or '',
                    relevance_score=0.0,
                    match_type='semantic'
                ))
            return records
    
    def calculate_semantic_similarity(self, query: str, text: str) -> float:
        """计算两个文本的语义相似度"""
        query_emb = np.array(self.embedding_model.embed(obj=query))
        text_emb = np.array(self.embedding_model.embed(obj=text))
        
        # 余弦相似度
        similarity = np.dot(query_emb, text_emb) / (np.linalg.norm(query_emb) * np.linalg.norm(text_emb))
        return float(similarity)
    
    def retrieve_v2(self, query: str, top_k: int = 5) -> List[KGRetrievalResult]:
        """
        优化的检索流程 V2
        
        步骤：
        1. 语义检索：在RQ向量空间找最相似的RQ
        2. 获取完整层级：根据匹配的RQ获取Paper→RQ→Solution
        3. 相关性重算：用嵌入模型计算精确相似度
        4. 过滤排序：只保留高相关性的结果
        """
        print(f"\n🔍 优化检索 V2: {query[:50]}...")
        
        # Step 1: 语义检索RQ
        print("  Step 1: 语义检索 Research Questions...")
        matched_rqs = self.semantic_search_rq(query, top_k=top_k * 2)
        print(f"    找到 {len(matched_rqs)} 个相似RQ")
        
        if not matched_rqs:
            return []
        
        # Step 2: 获取完整层级
        print("  Step 2: 获取Paper完整层级...")
        all_results = []
        seen_dois = set()
        
        for rq_match in matched_rqs:
            doi = rq_match['paper_id']
            rq_text = rq_match['rq_text']
            rq_similarity = rq_match['similarity']
            
            if doi in seen_dois:
                continue
            seen_dois.add(doi)
            
            # 获取该Paper的完整层级
            hierarchy = self.get_paper_hierarchy_by_doi(doi, rq_text_filter=rq_text)
            
            for item in hierarchy:
                # 使用RQ的相似度作为基础分数
                item.relevance_score = rq_similarity
                item.match_type = 'semantic'
                all_results.append(item)
        
        print(f"    获取 {len(seen_dois)} 个Paper的层级")
        
        # Step 3: 精排 - 计算更精确的相似度
        print("  Step 3: 精确重排序...")
        for item in all_results:
            # 综合多个字段的相似度
            rq_sim = self.calculate_semantic_similarity(query, item.research_question)
            core_sim = self.calculate_semantic_similarity(query, item.core_problem) if item.core_problem else 0
            
            # 加权综合分数
            item.relevance_score = rq_sim * 0.6 + core_sim * 0.4
        
        # Step 4: 过滤和排序
        # 只保留相关性足够高的结果
        threshold = 0.5
        filtered_results = [r for r in all_results if r.relevance_score >= threshold]
        
        # 按相关性排序
        filtered_results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        print(f"    过滤后剩余 {len(filtered_results)} 个结果 (阈值: {threshold})")
        
        return filtered_results[:top_k]
    
    def retrieve_with_diversity(self, query: str, top_k: int = 5, diversity_weight: float = 0.3) -> List[KGRetrievalResult]:
        """
        带多样性的检索
        确保返回的Paper来自不同年份/会议
        """
        # 先获取更多候选
        candidates = self.retrieve_v2(query, top_k=top_k * 3)
        
        if not candidates:
            return []
        
        # MMR (Maximal Marginal Relevance) 算法实现简化版
        selected = []
        remaining = candidates.copy()
        
        # 首先选择最相关的
        selected.append(remaining.pop(0))
        
        while len(selected) < top_k and remaining:
            max_score = -1
            best_idx = 0
            
            for i, item in enumerate(remaining):
                # 相关性分数
                relevance = item.relevance_score
                
                # 多样性分数（与已选结果的差异）
                diversity = 0
                for sel in selected:
                    # 会议不同增加多样性
                    if item.paper_conference != sel.paper_conference:
                        diversity += 0.1
                    # 年份不同增加多样性
                    if item.paper_year != sel.paper_year:
                        diversity += 0.05
                
                # MMR分数
                mmr_score = (1 - diversity_weight) * relevance + diversity_weight * diversity
                
                if mmr_score > max_score:
                    max_score = mmr_score
                    best_idx = i
            
            selected.append(remaining.pop(best_idx))
        
        return selected
    
    def format_results(self, results: List[KGRetrievalResult]) -> str:
        """格式化结果为可读文本"""
        if not results:
            return "未找到相关结果"
        
        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"\n{'='*70}")
            lines.append(f"[{i}] {r.paper_title}")
            lines.append(f"    DOI: {r.paper_doi}")
            lines.append(f"    {r.paper_year} | {r.paper_conference} | Score: {r.relevance_score:.3f} | Match: {r.match_type}")
            lines.append("")
            lines.append(f"🔍 Core Problem: {r.core_problem[:180]}...")
            lines.append("")
            lines.append(f"❓ [{r.rq_name}] {r.research_question[:180]}...")
            lines.append("")
            lines.append(f"💡 Solution: {r.solution[:220]}...")
        
        return "\n".join(lines)


def main():
    """测试优化版检索"""
    retriever = OptimizedKGRetriever()
    
    test_queries = [
        "How can contrastive learning be used to enhance the discriminability of dialogue act embeddings in a self-supervised manner?",
        "How to improve person re-identification with infrared images?",
    ]
    
    for query in test_queries:
        print(f"\n{'='*70}")
        print(f"📝 查询: {query[:60]}...")
        print(f"{'='*70}")
        
        # 基础检索
        results = retriever.retrieve_v2(query, top_k=5)
        print(retriever.format_results(results))
        
        # 多样性检索
        print(f"\n{'='*70}")
        print("📝 多样性检索结果:")
        diverse_results = retriever.retrieve_with_diversity(query, top_k=5)
        print(retriever.format_results(diverse_results))
    
    retriever.close()


if __name__ == "__main__":
    main()
