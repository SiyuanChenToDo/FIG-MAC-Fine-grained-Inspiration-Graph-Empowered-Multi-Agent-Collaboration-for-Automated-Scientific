#!/usr/bin/env python3
"""
Local RAG 向量检索移植测试脚本
从 /root/autodl-tmp/Myexamples/agents/graph_agents/local_rag.py 移植
用于与 test_rag_ablation.py 中的检索对比质量
"""

import os
import sys
import json
from typing import List, Dict, Optional, Tuple
from pathlib import Path

# 添加项目路径
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 优先使用 pip 安装的 camel
sys.path = [p for p in sys.path if 'autodl-tmp' not in p or 'Myexamples' in p or 'ablation' in p]

from camel.storages import FaissStorage, VectorRecord, VectorDBQuery
from camel.embeddings import OpenAICompatibleEmbedding


class LocalRAGVectorRetriever:
    """
    从 local_rag.py 移植的向量检索类
    保持与原代码一致的检索逻辑
    """
    
    def __init__(
        self,
        base_vdb_path: str = '/root/autodl-tmp/Myexamples/vdb/camel_faiss_storage',
        json_file_path: str = '/root/autodl-tmp/Myexamples/data/final_data/final_custom_kg_papers.json',
        api_key: str = None,
        api_url: str = None
    ):
        self.base_vdb_path = base_vdb_path
        self.json_file_path = json_file_path
        
        # API 配置
        self.api_key = api_key or os.environ.get(
            "OPENAI_COMPATIBILITY_API_KEY", 
            "sk-f97b45fe14844ba98d405488499434b7"
        )
        self.api_url = api_url or os.environ.get(
            "OPENAI_COMPATIBILITY_API_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        
        # 初始化嵌入模型
        self.embedding_model = OpenAICompatibleEmbedding(
            model_type="text-embedding-v2",
            api_key=self.api_key,
            url=self.api_url,
        )
        
        # 存储配置
        self.attribute_storages = {}
        self.use_new_structure = self._detect_structure()
        
    def close(self):
        """关闭资源（兼容 OptimizedKGRetriever 接口）"""
        # Local RAG Vector Retriever 不需要显式关闭资源
        # 此方法仅为兼容性而添加
        pass
    
    def _detect_structure(self) -> bool:
        """检测存储结构类型"""
        new_structure_exists = (
            os.path.exists(os.path.join(self.base_vdb_path, "paper")) or
            os.path.exists(os.path.join(self.base_vdb_path, "research_question")) or
            os.path.exists(os.path.join(self.base_vdb_path, "solution"))
        )
        return new_structure_exists
    
    def _get_attributes_config(self) -> Dict[str, List[str]]:
        """获取属性配置（与原代码一致）"""
        if self.use_new_structure:
            return {
                "paper": [
                    "abstract", "core_problem", "related_work",
                    "preliminary_innovation_analysis", "framework_summary"
                ],
                "research_question": ["research_question"],
                "solution": ["solution"],
            }
        else:
            return {
                "paper": [
                    "abstract", "core_problem", "related_work",
                    "preliminary_innovation_analysis", "framework_summary"
                ]
            }
    
    def load_storages(self, build_if_missing: bool = False) -> Dict:
        """
        加载 FAISS 存储（对应原代码的索引加载部分）
        
        Args:
            build_if_missing: 如果索引不存在是否构建（默认False，与原代码一致）
        """
        attributes_to_vectorize = self._get_attributes_config()
        loaded_attrs = []
        built_attrs = []
        
        for entity_type, attributes in attributes_to_vectorize.items():
            for attr in attributes:
                # 确定存储路径
                if self.use_new_structure:
                    storage_key = (entity_type, attr)
                    storage_path = os.path.join(self.base_vdb_path, entity_type, attr)
                    collection_name = f"{entity_type}_{attr}"
                    attr_display = f"{entity_type}.{attr}"
                else:
                    storage_key = attr
                    storage_path = os.path.join(self.base_vdb_path, attr)
                    collection_name = f"paper_{attr}"
                    attr_display = attr
                
                index_file_path = os.path.join(storage_path, f"{collection_name}.index")
                
                if os.path.exists(index_file_path):
                    # 加载已存在的索引
                    try:
                        storage = FaissStorage(
                            vector_dim=self.embedding_model.get_output_dim(),
                            storage_path=storage_path,
                            collection_name=collection_name,
                        )
                        storage.load()
                        self.attribute_storages[storage_key] = storage
                        loaded_attrs.append(attr_display)
                    except Exception as e:
                        print(f"Warning: Failed to load FAISS storage for {attr_display}: {e}")
                        continue
                elif build_if_missing:
                    # 构建新索引（简化版，原代码有更复杂的构建逻辑）
                    print(f"Index not found for {attr_display}, skipping (build_if_missing=True not fully implemented)")
                else:
                    print(f"Index not found for {attr_display}, skipping")
        
        return {
            "loaded": loaded_attrs,
            "built": built_attrs,
            "storage_count": len(self.attribute_storages)
        }
    
    def retrieve(
        self, 
        query: str, 
        top_k: int = 1,
        debug: bool = False
    ) -> Tuple[str, List[Dict]]:
        """
        执行向量检索（对应原代码 run_local_rag 的向量检索部分）
        
        Args:
            query: 查询文本
            top_k: 每个属性返回的结果数（原代码默认为1）
            debug: 是否打印调试信息
            
        Returns:
            (formatted_result, raw_results)
            - formatted_result: 格式化后的文本（与原代码输出格式一致）
            - raw_results: 原始结果列表
        """
        if not self.attribute_storages:
            load_info = self.load_storages()
            if debug:
                print(f"[DEBUG] Loaded storages: {load_info}")
        
        if not self.attribute_storages:
            return "No FAISS storages available.", []
        
        # 生成查询嵌入
        try:
            query_embedding = self.embedding_model.embed(obj=query)
        except Exception as e:
            print(f"[ERROR] Embedding query failed: {e}")
            return f"Error: {e}", []
        
        # 执行检索（与原代码一致）
        all_results: List[str] = []
        raw_results: List[Dict] = []
        
        for storage_key, storage in self.attribute_storages.items():
            if storage.status().vector_count > 0:
                db_query = VectorDBQuery(query_vector=query_embedding, top_k=top_k)
                try:
                    results = storage.query(query=db_query)
                except Exception as e:
                    key_str = f"{storage_key[0]}.{storage_key[1]}" if isinstance(storage_key, tuple) else storage_key
                    if debug:
                        print(f"[DEBUG] Vector query failed for attr='{key_str}': {e}")
                    continue
                
                for res in results:
                    payload = res.record.payload
                    
                    # 构建结果文本 - 输出 payload 中的全部属性
                    lines = []
                    storage_key_str = storage_key if isinstance(storage_key, str) else f"{storage_key[0]}.{storage_key[1]}"
                    lines.append(f"Found in '{storage_key_str}':")
                    lines.append(f"  - Similarity Score: {res.similarity:.4f}")
                    
                    # 动态输出 payload 中的所有字段
                    for key, value in payload.items():
                        if isinstance(value, str) and len(value) > 200:
                            # 对于长文本，显示前200字符并加上省略号
                            display_value = value[:200] + "..."
                        else:
                            display_value = value
                        lines.append(f"  - {key}: {display_value}")
                    
                    res_text = "\n".join(lines)
                    
                    all_results.append(res_text)
                    
                    # raw_results 包含完整的 payload 和所有元数据
                    raw_result_entry = {
                        'similarity': res.similarity,
                        'storage_key': storage_key,
                    }
                    raw_result_entry.update(payload)  # 添加 payload 中的所有字段
                    raw_results.append(raw_result_entry)
        
        # 格式化最终结果（与原代码一致）
        vector_result = "\n\n".join(all_results) if all_results else "No relevant documents found in the local vector database."
        
        if debug:
            print(f"[DEBUG] Vector search hits: {len(all_results)}")
        
        return vector_result, raw_results
    
    def compare_with_optimized(
        self, 
        query: str,
        optimized_retriever,
        debug: bool = True
    ) -> Dict:
        """
        与优化版检索器对比
        
        Args:
            query: 查询文本
            optimized_retriever: OptimizedKGRetriever 实例
            debug: 是否打印对比信息
            
        Returns:
            对比结果字典
        """
        print(f"\n{'='*70}")
        print(f"🔍 检索质量对比测试")
        print(f"{'='*70}")
        print(f"查询: {query}\n")
        
        # 1. Local RAG 向量检索
        print("[1] Local RAG 向量检索结果:")
        local_result, local_raw = self.retrieve(query, top_k=1, debug=debug)
        print(local_result[:800] + "..." if len(local_result) > 800 else local_result)
        print(f"\n📊 Local RAG 检索到 {len(local_raw)} 条结果\n")
        
        # 2. 优化版检索
        print("[2] 优化版 (OptimizedKGRetriever) 结果:")
        optimized_results = optimized_retriever.retrieve_v2(query, top_k=5)
        for i, item in enumerate(optimized_results[:3], 1):
            print(f"\n[{i}] {item.paper_title}")
            print(f"    Relevance: {item.relevance_score:.3f}")
            print(f"    RQ: {item.research_question[:100]}...")
        print(f"\n📊 优化版检索到 {len(optimized_results)} 条结果\n")
        
        # 3. 对比分析
        print("[3] 对比分析:")
        
        # 计算平均相似度/相关性
        local_avg_sim = sum(r['similarity'] for r in local_raw) / len(local_raw) if local_raw else 0
        optimized_avg_rel = sum(r.relevance_score for r in optimized_results) / len(optimized_results) if optimized_results else 0
        
        print(f"    Local RAG 平均相似度: {local_avg_sim:.3f}")
        print(f"    优化版平均相关性: {optimized_avg_rel:.3f}")
        
        # 检查是否有重叠的 Paper
        local_papers = set(r['paper_id'] for r in local_raw)
        optimized_papers = set(r.paper_doi for r in optimized_results)
        common_papers = local_papers & optimized_papers
        
        print(f"    Local RAG Paper 数: {len(local_papers)}")
        print(f"    优化版 Paper 数: {len(optimized_papers)}")
        print(f"    重叠 Paper 数: {len(common_papers)}")
        if common_papers:
            print(f"    重叠 Paper IDs: {list(common_papers)[:3]}")
        
        return {
            'query': query,
            'local_rag': {
                'result_count': len(local_raw),
                'avg_similarity': local_avg_sim,
                'paper_ids': list(local_papers),
                'raw_results': local_raw
            },
            'optimized': {
                'result_count': len(optimized_results),
                'avg_relevance': optimized_avg_rel,
                'paper_ids': list(optimized_papers),
                'raw_results': optimized_results
            },
            'common_papers': list(common_papers),
            'overlap_ratio': len(common_papers) / max(len(local_papers), len(optimized_papers), 1)
        }


def main():
    """测试主函数"""
    print("="*70)
    print("Local RAG Vector Retriever - 移植测试")
    print("="*70)
    
    # 初始化检索器
    retriever = LocalRAGVectorRetriever()
    
    # 加载存储
    load_info = retriever.load_storages()
    print(f"\n✅ 存储加载完成: {load_info}\n")
    
    # 测试查询
    test_queries = [
        "How can contrastive learning be used to enhance the discriminability of dialogue act embeddings in a self-supervised manner?",
        "How to improve person re-identification with infrared images?",
    ]
    
    for query in test_queries:
        print(f"\n{'='*70}")
        print(f"查询: {query[:60]}...")
        print(f"{'='*70}\n")
        
        result, raw = retriever.retrieve(query, top_k=1, debug=True)
        print("\n--- 检索结果 ---")
        print(result[:1000] + "..." if len(result) > 1000 else result)
        print(f"\n📊 总计检索到 {len(raw)} 条结果")
        print("\n" + "="*70)


if __name__ == "__main__":
    main()
