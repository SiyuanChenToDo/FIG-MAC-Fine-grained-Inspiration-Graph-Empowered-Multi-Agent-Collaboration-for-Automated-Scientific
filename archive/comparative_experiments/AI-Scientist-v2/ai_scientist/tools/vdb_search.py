"""
Vector DB Search Tool - 使用用户的实际Vector DB替代Semantic Scholar
"""
import os
import sys
import numpy as np
from typing import Dict, List, Optional
import warnings
import json

# 添加CAMEL路径
sys.path.append("/root/autodl-tmp")

try:
    from camel.storages import FaissStorage, VectorDBQuery
    from camel.embeddings import OpenAICompatibleEmbedding
except ImportError:
    print("Warning: CAMEL not installed. VDB search will fail.")
    FaissStorage = None
    VectorDBQuery = None
    OpenAICompatibleEmbedding = None

from ai_scientist.tools.base_tool import BaseTool


class VDBSearchTool(BaseTool):
    """
    使用用户实际Vector DB的搜索工具，替代Semantic Scholar
    """
    def __init__(
        self,
        name: str = "SearchSemanticScholar",  # 保持名称兼容，这样AI-Scientist-v2不需要修改
        description: str = (
            "Search for relevant literature using our vector database. "
            "Provide a search query to find relevant papers."
        ),
        max_results: int = 10,
        vdb_path: Optional[str] = None,
    ):
        parameters = [
            {
                "name": "query",
                "type": "str",
                "description": "The search query to find relevant papers.",
            }
        ]
        super().__init__(name, description, parameters)
        self.max_results = max_results
        
        # 初始化Vector DB
        self.vdb_path = vdb_path or os.getenv(
            "AI_SCIENTIST_VDB_PATH",
            "/root/autodl-tmp/Myexamples/vdb/camel_faiss_storage"
        )
        self.embedding_model = None
        self.vector_storage = None
        self.title_cache = {}
        self.year_cache = {}
        self.citation_cache = {}
        
        self._init_vdb()
        self._load_metadata_cache()
    
    def _init_vdb(self):
        """初始化向量数据库"""
        if FaissStorage is None or OpenAICompatibleEmbedding is None:
            warnings.warn("CAMEL not available. VDB search will not work.")
            return
        
        try:
            # 初始化embedding模型
            api_key = (os.getenv("OPENAI_COMPATIBILITY_API_KEY") or 
                      os.getenv("QWEN_API_KEY") or 
                      os.getenv("OPENAI_API_KEY"))
            api_url = (os.getenv("OPENAI_COMPATIBILITY_API_BASE_URL") or 
                      os.getenv("QWEN_API_BASE_URL") or 
                      os.getenv("OPENAI_BASE_URL"))
            
            if not api_key:
                warnings.warn("No API key found for embedding model. Set OPENAI_API_KEY or QWEN_API_KEY.")
                return
            
            self.embedding_model = OpenAICompatibleEmbedding(
                model_type="text-embedding-v2",
                api_key=api_key,
                url=api_url,
            )
            
            # 初始化向量存储
            storage_path = os.path.join(self.vdb_path, "paper", "abstract")
            if not os.path.exists(storage_path):
                storage_path = os.path.join(self.vdb_path, "abstract")
            
            if os.path.exists(storage_path):
                self.vector_storage = FaissStorage(
                    vector_dim=1536,
                    storage_path=storage_path,
                    collection_name="paper_abstract" if os.path.exists(
                        os.path.join(storage_path, "paper_abstract.index")
                    ) else "abstract"
                )
                self.vector_storage.load()
                print(f"✅ Vector DB loaded from {storage_path}")
            else:
                warnings.warn(f"Vector DB not found at {storage_path}")
        except Exception as e:
            warnings.warn(f"Failed to initialize VDB: {e}")
    
    def _load_metadata_cache(self):
        """从JSON文件加载元数据缓存"""
        try:
            json_path = "/root/autodl-tmp/Myexamples/data/final_data/final_custom_kg_papers.json"
            if os.path.exists(json_path):
                import json
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for entity in data.get("entities", []):
                    if entity.get("entity_type") == "paper":
                        paper_id = entity.get("source_id") or entity.get("doi_norm")
                        if paper_id:
                            title = entity.get("title", "")
                            if title:
                                self.title_cache[paper_id] = title
                            
                            year = entity.get("year")
                            if year:
                                try:
                                    year_int = int(year)
                                    self.year_cache[paper_id] = year_int
                                except (ValueError, TypeError):
                                    pass
                            
                            citation_count = entity.get("citationCount") or entity.get("citation_count") or entity.get("citations")
                            if citation_count:
                                try:
                                    citation_int = int(citation_count)
                                    self.citation_cache[paper_id] = citation_int
                                except (ValueError, TypeError):
                                    pass
                
                print(f"✅ Loaded {len(self.title_cache)} paper titles from JSON")
        except Exception as e:
            warnings.warn(f"Could not load metadata cache: {e}")
    
    def use_tool(self, query: str) -> Optional[str]:
        """使用工具搜索论文"""
        papers = self.search_for_papers(query)
        if papers:
            return self.format_papers(papers)
        else:
            return "No papers found."
    
    def search_for_papers(self, query: str) -> Optional[List[Dict]]:
        """从Vector DB搜索论文"""
        if not query:
            return None
        
        if not self.vector_storage or not self.embedding_model:
            warnings.warn("Vector DB not initialized. Cannot search.")
            return None
        
        try:
            # 1. Embed query
            query_vec = self.embedding_model.embed(obj=query)
            query_vec = np.array(query_vec, dtype=np.float32)
            
            # 2. Query Vector DB
            query_obj = VectorDBQuery(query_vector=query_vec, top_k=self.max_results * 2)
            results = self.vector_storage.query(query_obj)
            
            # 3. 格式化为与Semantic Scholar兼容的格式
            papers = []
            for res in results:
                payload = res.record.payload
                
                # 尝试多种可能的paper_id字段名
                paper_id = (payload.get("paper_id") or 
                           payload.get("source_id") or 
                           payload.get("id") or 
                           payload.get("doi_norm") or 
                           "")
                
                # 提取abstract（尝试多种字段名）
                abstract = (payload.get("text") or 
                           payload.get("abstract") or 
                           payload.get("content") or 
                           "")
                
                # 从缓存获取元数据（尝试所有可能的paper_id）
                title = ""
                year = None
                citation_count = 0
                
                # 尝试从缓存查找（使用所有可能的paper_id）
                for pid in [paper_id, payload.get("source_id"), payload.get("doi_norm")]:
                    if pid and pid in self.title_cache:
                        title = self.title_cache[pid]
                        year = self.year_cache.get(pid)
                        citation_count = self.citation_cache.get(pid, 0)
                        break
                
                # 如果缓存中没有，尝试从payload直接获取
                if not title:
                    title = payload.get("title", "")
                
                # 如果还是没有title，尝试从abstract提取
                if not title:
                    if abstract and len(abstract) > 50:
                        # 尝试提取第一句作为标题
                        first_sentence = abstract.split('.')[0].strip()
                        if len(first_sentence) > 20 and len(first_sentence) < 200:
                            title = first_sentence
                        else:
                            title = abstract[:100] + "..."
                    elif paper_id:
                        title = f"Paper: {paper_id[:50]}"
                    else:
                        title = "Unknown Title"
                
                # 如果还是没有abstract，使用默认值
                if not abstract:
                    abstract = "No abstract available."
                
                # 如果year和citation_count还没有，尝试从payload获取
                if year is None:
                    year = payload.get("year")
                if citation_count == 0:
                    citation_count = (payload.get("citationCount") or 
                                     payload.get("citation_count") or 
                                     payload.get("citations") or 
                                     0)
                
                # 创建与Semantic Scholar兼容的格式
                paper_dict = {
                    "title": title,
                    "abstract": abstract,
                    "year": year,
                    "citationCount": citation_count,
                    "authors": [],  # VDB中没有作者信息
                    "venue": "Unknown Venue",  # VDB中没有venue信息
                    "paperId": paper_id,
                }
                papers.append(paper_dict)
            
            # 按引用数排序（降序）
            papers.sort(key=lambda x: x.get("citationCount", 0), reverse=True)
            return papers[:self.max_results]
            
        except Exception as e:
            warnings.warn(f"Error searching VDB: {e}")
            return None
    
    def format_papers(self, papers: List[Dict]) -> str:
        """格式化论文为字符串（与Semantic Scholar格式兼容）"""
        paper_strings = []
        for i, paper in enumerate(papers):
            authors = ", ".join(
                [author.get("name", "Unknown") for author in paper.get("authors", [])]
            ) if paper.get("authors") else "Unknown Authors"
            
            year = paper.get("year", "Unknown Year")
            venue = paper.get("venue", "Unknown Venue")
            citation_count = paper.get("citationCount", "N/A")
            abstract = paper.get("abstract", "No abstract available.")
            
            paper_strings.append(
                f"""{i + 1}: {paper.get("title", "Unknown Title")}. {authors}. {venue}, {year}.
Number of citations: {citation_count}
Abstract: {abstract}"""
            )
        return "\n\n".join(paper_strings)

