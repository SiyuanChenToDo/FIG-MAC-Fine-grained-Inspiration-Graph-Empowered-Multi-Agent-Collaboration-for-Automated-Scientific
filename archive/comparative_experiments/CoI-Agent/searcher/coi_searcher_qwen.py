"""
CoI-Agent Searcher适配器 - 使用用户的实际VDB数据
替换原始的SementicSearcher，使用CAMEL FaissStorage进行检索
"""
import os
import sys
import numpy as np
from typing import List, Optional

# 添加CAMEL路径
sys.path.append("/root/autodl-tmp")

try:
    from camel.storages import FaissStorage, VectorDBQuery
    from camel.embeddings import OpenAICompatibleEmbedding
except ImportError:
    print("Warning: CAMEL not installed. Real retrieval will fail.")
    FaissStorage = None
    VectorDBQuery = None
    OpenAICompatibleEmbedding = None

from .sementic_search import Result


class CoISearcherQwen:
    """
    使用用户实际VDB数据的Searcher，兼容CoI-Agent的SementicSearcher接口
    """
    def __init__(self, save_file="papers/", ban_paper=[], real_vdb_path=None):
        """
        Args:
            save_file: 保存PDF的目录（保留接口兼容性，但实际不使用）
            ban_paper: 禁止的论文列表
            real_vdb_path: 用户的实际向量数据库路径
        """
        self.save_file = save_file
        self.ban_paper = ban_paper
        self.real_vdb_path = real_vdb_path or "/root/autodl-tmp/Myexamples/vdb/camel_faiss_storage"
        
        # 初始化embedding模型
        self.embedding_model = None
        self.vector_storage = None
        self.title_cache = {}  # 缓存 paper_id -> title 映射
        self.year_cache = {}  # 缓存 paper_id -> year 映射
        self.citation_cache = {}  # 缓存 paper_id -> citation_count 映射
        self._init_vdb()
        self._load_metadata_cache()
    
    def _init_vdb(self):
        """初始化向量数据库"""
        if not FaissStorage or not OpenAICompatibleEmbedding:
            print("Warning: CAMEL not available. Using mock searcher.")
            return
        
        try:
            print(f"Initializing CoI-Agent Real RAG from: {self.real_vdb_path}")
            
            # 初始化embedding模型
            self.embedding_model = OpenAICompatibleEmbedding(
                model_type="text-embedding-v2",
                api_key=os.environ.get("QWEN_API_KEY") or os.environ.get("OPENAI_COMPATIBILITY_API_KEY"),
                url=os.environ.get("QWEN_API_BASE_URL") or os.environ.get("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
            )
            
            # 加载向量数据库
            storage_path = os.path.join(self.real_vdb_path, "paper/abstract")
            if not os.path.exists(storage_path):
                storage_path = os.path.join(self.real_vdb_path, "abstract")
            
            if not os.path.exists(storage_path):
                print(f"Warning: Vector DB path not found: {storage_path}")
                return
            
            self.vector_storage = FaissStorage(
                vector_dim=1536,
                storage_path=storage_path,
                collection_name="paper_abstract"
            )
            self.vector_storage.load()
            print(f"✅ CoI-Agent Real Vector DB Loaded.")
            
        except Exception as e:
            print(f"Error initializing VDB: {e}")
            self.embedding_model = None
            self.vector_storage = None
    
    def _load_metadata_cache(self):
        """从JSON文件加载 paper_id -> title, year, citation_count 映射"""
        try:
            json_path = "/root/autodl-tmp/Myexamples/data/final_data/final_custom_kg_papers.json"
            if os.path.exists(json_path):
                import json
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 构建 paper_id -> title, year, citation_count 映射
                for entity in data.get("entities", []):
                    if entity.get("entity_type") == "paper":
                        paper_id = entity.get("source_id") or entity.get("doi_norm")
                        if paper_id:
                            # Title
                            title = entity.get("title", "")
                            if title:
                                self.title_cache[paper_id] = title
                            
                            # Year
                            year = entity.get("year")
                            if year:
                                try:
                                    year_int = int(year)
                                    self.year_cache[paper_id] = year_int
                                except (ValueError, TypeError):
                                    pass
                            
                            # Citation count
                            citation_count = entity.get("citationCount") or entity.get("citation_count") or entity.get("citations")
                            if citation_count:
                                try:
                                    citation_int = int(citation_count)
                                    self.citation_cache[paper_id] = citation_int
                                except (ValueError, TypeError):
                                    pass
                
                print(f"✅ Loaded {len(self.title_cache)} paper titles from JSON")
                print(f"✅ Loaded {len(self.year_cache)} paper years from JSON")
                print(f"✅ Loaded {len(self.citation_cache)} paper citations from JSON")
        except Exception as e:
            print(f"⚠️ Warning: Could not load metadata cache: {e}")
            import traceback
            traceback.print_exc()
    
    async def search_async(self, query, max_results=5, paper_list=None, 
                          rerank_query=None, llm=None, year=None, 
                          publicationDate=None, need_download=True, 
                          fields=None):
        """
        搜索论文 - 使用实际VDB数据
        兼容原始SementicSearcher的接口
        """
        if not self.vector_storage or not self.embedding_model:
            print(f"Warning: VDB not initialized. Returning empty results for query: {query}")
            return []
        
        print(f"[CoI-Agent RAG] Searching for: {query[:80]}...")
        
        # 过滤已读论文
        readed_papers = []
        if paper_list:
            if isinstance(paper_list, set):
                paper_list = list(paper_list)
            if len(paper_list) > 0:
                if isinstance(paper_list[0], str):
                    readed_papers = paper_list
                elif isinstance(paper_list[0], Result):
                    readed_papers = [paper.title for paper in paper_list]
        
        try:
            # 1. Embed query
            query_vec = self.embedding_model.embed(obj=query)
            query_vec = np.array(query_vec, dtype=np.float32)
            
            # 2. Query Vector DB
            query_results = self.vector_storage.query(
                VectorDBQuery(query_vector=query_vec, top_k=max_results * 2)  # 获取更多候选以便过滤
            )
            
            # 3. 过滤和格式化结果
            final_results = []
            for res in query_results:
                payload = res.record.payload
                
                # 调试：检查 payload 结构
                if not payload:
                    print(f"⚠️ Warning: Empty payload for result")
                    continue
                
                # 根据实际的 payload 结构提取数据
                # payload 结构: {'paper_id': '...', 'entity_type': 'paper', 'attribute_name': 'abstract', 'text': '...'}
                paper_id = payload.get("paper_id", "")
                abstract = payload.get("text", "") or payload.get("abstract", "") or "No abstract available."
                
                # 从缓存中获取 title，如果没有则使用 paper_id
                title = self.title_cache.get(paper_id, "")
                if not title:
                    # 如果缓存中没有，使用 paper_id 或 abstract 的前部分
                    if paper_id:
                        title = f"Paper: {paper_id}"
                    elif abstract and abstract != "No abstract available.":
                        title = abstract[:100] + "..."
                    else:
                        title = "Unknown Title"
                
                # 过滤禁止的论文和已读论文
                if title in self.ban_paper or title in readed_papers:
                    continue
                
                # 提取年份和引用数（优先从缓存，然后从payload）
                year_val = self.year_cache.get(paper_id) or payload.get("year") or payload.get("publication_year")
                citation_count = self.citation_cache.get(paper_id) or payload.get("citations") or payload.get("citation_count", 0)
                
                # 创建模拟的 article 对象（包含 title 和 abstract，兼容原始接口）
                # 确保 sections 至少包含一个 section（使用 abstract 作为内容）
                article_dict = {
                    "title": title,
                    "abstract": abstract,
                    "sections": [
                        {
                            "heading": "Abstract",
                            "text": abstract,
                            "publication_ref": []
                        }
                    ],
                    "references": []  # 空 references，因为我们没有 PDF 解析
                }
                
                # 创建Result对象（包含模拟的 article）
                result = Result(
                    title=title,
                    abstract=abstract,
                    article=article_dict,  # 使用模拟的 article 对象
                    citations_conut=citation_count,
                    year=year_val
                )
                
                final_results.append(result)
                
                if len(final_results) >= max_results:
                    break
            
            print(f"✅ Found {len(final_results)} papers from VDB")
            return final_results
            
        except Exception as e:
            print(f"Error searching VDB: {e}")
            return []
    
    async def search_related_paper_async(self, title, need_citation=True, 
                                        need_reference=True, rerank_query=None, 
                                        llm=None, paper_list=[]):
        """
        搜索相关论文 - 使用实际VDB数据
        通过标题搜索，然后基于相似度查找相关论文
        """
        if not self.vector_storage or not self.embedding_model:
            print(f"Warning: VDB not initialized. Cannot find related papers for: {title}")
            return None
        
        print(f"[CoI-Agent RAG] Searching related papers for: {title[:80]}...")
        
        try:
            # 1. 先通过标题搜索找到目标论文
            title_vec = self.embedding_model.embed(obj=title)
            title_vec = np.array(title_vec, dtype=np.float32)
            
            query_results = self.vector_storage.query(
                VectorDBQuery(query_vector=title_vec, top_k=10)
            )
            
            # 2. 找到最匹配的论文（通过 paper_id 从缓存中查找 title）
            target_paper = None
            for res in query_results:
                payload = res.record.payload
                paper_id = payload.get("paper_id", "")
                # 从缓存中获取 title
                cached_title = self.title_cache.get(paper_id, "")
                if cached_title and title.lower() in cached_title.lower():
                    target_paper = res
                    break
                # 也检查 payload 中的其他字段
                res_title = payload.get("title", "")
                if res_title and title.lower() in res_title.lower():
                    target_paper = res
                    break
            
            if not target_paper:
                # 如果找不到精确匹配，使用第一个结果
                if query_results:
                    target_paper = query_results[0]
                else:
                    return None
            
            # 3. 基于目标论文的embedding查找相似论文
            target_vec = np.array(target_paper.record.vector, dtype=np.float32)
            
            # 搜索更多相关论文
            related_results = self.vector_storage.query(
                VectorDBQuery(query_vector=target_vec, top_k=5)
            )
            
            # 4. 过滤并返回第一个相关论文（排除目标论文本身）
            target_paper_id = target_paper.record.payload.get("paper_id", "")
            target_title = self.title_cache.get(target_paper_id, "")
            
            for res in related_results:
                payload = res.record.payload
                paper_id = payload.get("paper_id", "")
                related_abstract = payload.get("text", "") or payload.get("abstract", "")
                
                # 从缓存中获取 title
                related_title = self.title_cache.get(paper_id, "")
                if not related_title:
                    if paper_id:
                        related_title = f"Paper: {paper_id}"
                    elif related_abstract:
                        related_title = related_abstract[:100] + "..."
                    else:
                        related_title = "Unknown Title"
                
                # 跳过目标论文本身（通过 paper_id 比较）和已读论文
                if paper_id == target_paper_id or related_title in paper_list:
                    continue
                
                year_val = self.year_cache.get(paper_id) or payload.get("year") or payload.get("publication_year")
                citation_count = self.citation_cache.get(paper_id) or payload.get("citations") or payload.get("citation_count", 0)
                
                # 创建模拟的 article 对象
                article_dict = {
                    "title": related_title,
                    "abstract": related_abstract,
                    "sections": [
                        {
                            "heading": "Abstract",
                            "text": related_abstract,
                            "publication_ref": []
                        }
                    ],
                    "references": []
                }
                
                result = Result(
                    title=related_title,
                    abstract=related_abstract,
                    article=article_dict,
                    citations_conut=citation_count,
                    year=year_val
                )
                
                print(f"✅ Found related paper: {related_title[:60]}...")
                return result
            
            return None
            
        except Exception as e:
            print(f"Error searching related papers: {e}")
            return None
    
    def cal_cosine_similarity(self, vec1, vec2):
        """计算余弦相似度"""
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    
    def cal_cosine_similarity_matric(self, matric1, matric2):
        """计算余弦相似度矩阵"""
        if isinstance(matric1, list):
            matric1 = np.array(matric1)
        if isinstance(matric2, list):
            matric2 = np.array(matric2)
        if len(matric1.shape) == 1:
            matric1 = matric1.reshape(1, -1)
        if len(matric2.shape) == 1:
            matric2 = matric2.reshape(1, -1)
        dot_product = np.dot(matric1, matric2.T)
        norm1 = np.linalg.norm(matric1, axis=1)
        norm2 = np.linalg.norm(matric2, axis=1)
        cos_sim = dot_product / np.outer(norm1, norm2)
        scores = cos_sim.flatten()
        return scores.tolist()
    
    def rerank_papers(self, query_embedding, paper_list, llm):
        """重排序论文（如果需要）"""
        if len(paper_list) == 0:
            return []
        
        # 如果llm有embedding功能，使用它
        if llm and hasattr(llm, 'get_embbeding'):
            paper_contents = []
            for paper in paper_list:
                if isinstance(paper, dict):
                    paper_content = f"Title: {paper.get('title', '')}\nAbstract: {paper.get('abstract', '')}\n"
                else:
                    paper_content = f"Title: {paper.title}\nAbstract: {paper.abstract}\n"
                paper_contents.append(paper_content)
            
            try:
                paper_contents_embedding = llm.get_embbeding(paper_contents)
                paper_contents_embedding = np.array(paper_contents_embedding)
                scores = self.cal_cosine_similarity_matric(query_embedding, paper_contents_embedding)
                
                paper_list = sorted(zip(paper_list, scores), key=lambda x: x[1], reverse=True)
                paper_list = [paper[0] for paper in paper_list]
            except Exception as e:
                print(f"Error in reranking: {e}")
        
        return paper_list
    
    # 实现原始 SementicSearcher 的所有方法，确保完全兼容
    def read_paper_title_abstract(self, article):
        """读取论文的 title 和 abstract"""
        if isinstance(article, dict):
            title = article.get("title", "")
            abstract = article.get("abstract", "")
        else:
            title = getattr(article, "title", "")
            abstract = getattr(article, "abstract", "")
        
        paper_content = f"""
Title: {title}
Abstract: {abstract}
        """
        return paper_content
    
    def read_paper_title_abstract_introduction(self, article):
        """读取论文的 title、abstract 和 introduction"""
        if isinstance(article, dict):
            title = article.get("title", "")
            abstract = article.get("abstract", "")
            sections = article.get("sections", [])
            # 如果有 sections，使用第一个 section 的 text；否则使用 abstract
            if sections:
                introduction = sections[0].get("text", "") if isinstance(sections[0], dict) else getattr(sections[0], "text", "")
            else:
                introduction = abstract  # 如果没有 sections，使用 abstract 作为 introduction
        else:
            title = getattr(article, "title", "")
            abstract = getattr(article, "abstract", "")
            sections = getattr(article, "sections", [])
            if sections:
                introduction = sections[0].get("text", "") if isinstance(sections[0], dict) else getattr(sections[0], "text", "")
            else:
                introduction = abstract
        
        paper_content = f"""
Title: {title}
Abstract: {abstract}
Introduction: {introduction}
        """
        return paper_content
    
    def read_paper_content(self, article):
        """读取论文的完整内容"""
        paper_content = self.read_paper_title_abstract(article)
        
        if isinstance(article, dict):
            sections = article.get("sections", [])
        else:
            sections = getattr(article, "sections", [])
        
        # 如果 sections 为空，至少添加 abstract 作为内容
        if not sections:
            abstract = article.get("abstract", "") if isinstance(article, dict) else getattr(article, "abstract", "")
            paper_content += f"section: Abstract\n content: {abstract}\n ref_ids: []\n"
        else:
            for section in sections:
                if isinstance(section, dict):
                    heading = section.get("heading", "")
                    text = section.get("text", "")
                    ref_ids = section.get("publication_ref", [])
                    if isinstance(ref_ids, list):
                        ref_ids = str(ref_ids)
                else:
                    heading = getattr(section, "heading", "")
                    text = getattr(section, "text", "")
                    ref_ids = getattr(section, "publication_ref", [])
                    if isinstance(ref_ids, list):
                        ref_ids = str(ref_ids)
                
                paper_content += f"section: {heading}\n content: {text}\n ref_ids: {ref_ids}\n"
        
        return paper_content
    
    def read_paper_content_with_ref(self, article):
        """读取论文内容和参考文献"""
        paper_content = self.read_paper_content(article)
        paper_content += "<References>\n"
        
        if isinstance(article, dict):
            references = article.get("references", [])
        else:
            references = getattr(article, "references", [])
        
        for refer in references:
            if isinstance(refer, dict):
                ref_id = refer.get("ref_id", "")
                title = refer.get("title", "")
                year = refer.get("year", "")
            else:
                ref_id = getattr(refer, "ref_id", "")
                title = getattr(refer, "title", "")
                year = getattr(refer, "year", "")
            
            paper_content += f"Ref_id:{ref_id} Title: {title} Year: ({year})\n"
        
        paper_content += "</References>\n"
        return paper_content
    
    def read_arxiv_from_path(self, pdf_path):
        """读取 PDF 文件（兼容接口，但我们不使用 PDF）"""
        # 返回 None，因为我们不使用 PDF
        return None
    
    async def read_arxiv_from_link_async(self, pdf_link, filename):
        """从链接读取 PDF（兼容接口，但我们不使用 PDF）"""
        # 返回 None，因为我们不使用 PDF
        return None

