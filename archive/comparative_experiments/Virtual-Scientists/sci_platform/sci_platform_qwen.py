import sys
import os
import numpy as np
import random
from unittest.mock import MagicMock
from functools import partial
from enum import Enum

# 1. Mock 'ollama' module BEFORE importing sci_platform
sys.modules["ollama"] = MagicMock()

# Add project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir, '../agentscope-main/src'))

# Import original Platform
from sci_platform import Platform
import agentscope
from agentscope.agents import SciAgent
from agentscope.message import Msg

# Import CAMEL components for Real RAG
try:
    from camel.storages import FaissStorage, VectorDBQuery
    from camel.embeddings import OpenAICompatibleEmbedding
    from camel.types import ModelType
except ImportError:
    print("Warning: CAMEL not installed or path incorrect. Real retrieval will fail.")

class DynamicPaperDict:
    """
    A dict-like object that caches and dynamically fetches paper data from vector DB.
    This allows the original sci_platform code to access papers via paper_dicts[index].
    """
    def __init__(self, platform):
        self.platform = platform
        self.cache = {}  # Cache fetched papers to avoid redundant queries
        
    def __getitem__(self, index):
        """Get paper by index. If not cached, return a placeholder."""
        if index not in self.cache:
            # Return a placeholder - the actual data should be populated by reference_paper
            return {"title": f"Paper_{index}", "abstract": "Content will be retrieved dynamically."}
        return self.cache[index]
    
    def __len__(self):
        return 100000  # Large number to avoid index errors
    
    def update_cache(self, index, title, abstract):
        """Update cache with retrieved paper data."""
        self.cache[index] = {"title": title, "abstract": abstract}

class PlatformQwen(Platform):
    def __init__(self, 
                 mock_data_dir, # Kept only for file paths logic, data will be ignored
                 model_config_path,
                 real_vdb_path, # NEW: Path to your real vector DB
                 topic,         # NEW: The fixed topic for comparison
                 agent_num=2,
                 **kwargs):
        
        self.topic_input = topic
        self.real_vdb_path = real_vdb_path
        
        # 1. Setup Fake Paths just to satisfy SciPlatform's __init__ checks
        # We won't actually read data from them for retrieval
        self.mock_data_dir = mock_data_dir
        paper_folder_path = os.path.join(mock_data_dir, "papers")
        future_paper_folder_path = os.path.join(mock_data_dir, "papers_future")
        author_info_dir = os.path.join(mock_data_dir, "books")
        adjacency_matrix_dir = os.path.join(mock_data_dir, "adjacency")
        
        # 2. Config Names
        agent_model_config_name = 'qwen_plus'
        review_model_config_name = 'qwen_max'
        
        # 3. Mock FAISS to bypass original __init__ crash
        import faiss
        original_read_index = getattr(faiss, 'read_index', None)
        original_gpu_resources = getattr(faiss, 'StandardGpuResources', None)
        original_index_cpu_to_gpu = getattr(faiss, 'index_cpu_to_gpu', None)
        
        try:
            # Mock specific functions used by agentscope/sci_platform init
            faiss.read_index = MagicMock()
            faiss.StandardGpuResources = MagicMock()
            faiss.index_cpu_to_gpu = MagicMock()
            
            # Init AgentScope
            agentscope.init(model_configs=model_config_path)
            
            # Manual Init of Platform attributes
            self.agent_num = agent_num
            self.paper_folder_path = paper_folder_path
            self.paper_future_folder_path = future_paper_folder_path
            self.author_info_dir = author_info_dir
            self.adjacency_matrix_dir = adjacency_matrix_dir
            
            # Copy kwargs
            self.group_max_discuss_iteration = kwargs.get('group_max_discuss_iteration', 2)
            self.recent_n_team_mem_for_retrieve = kwargs.get('recent_n_team_mem_for_retrieve', 1)
            self.team_limit = kwargs.get('team_limit', 2)
            self.check_iter = kwargs.get('check_iter', 5)
            self.reviewer_num = kwargs.get('review_num', 1)
            self.max_teammember = kwargs.get('max_teammember', 2)
            self.cite_number = kwargs.get('cite_number', 3)
            self.default_mark = kwargs.get('default_mark', 4)
            self.skip_check = kwargs.get('skip_check', False)
            self.over_state = kwargs.get('over_state', 8)
            self.begin_state = kwargs.get('begin_state', 1)
            self.log_dir = kwargs.get('log_dir', 'logs_qwen')
            self.info_dir = kwargs.get('info_dir', 'team_info_qwen')
            self.think_times = self.max_teammember + 1
            
            # Create logs directory explicitly
            if not os.path.exists(self.log_dir):
                os.makedirs(self.log_dir)
            if not os.path.exists(self.info_dir):
                os.makedirs(self.info_dir)
            
            # Load Mock Adjacency (Required for agent count)
            self.adjacency_matrix = np.loadtxt(
                os.path.join(self.adjacency_matrix_dir, 'adjacency.txt'), dtype=int)
            
            # Mock Knowledge Bank (We use our own RAG)
            self.knowledge_bank = MagicMock()
            self.knowledge_bank.equip = MagicMock() 
            
            # Init Agent Pool (Using Mock Profiles but Qwen Model)
            self.agent_pool = [self.init_agent(str(agent_id), agent_model_config_name, 
                                             os.path.join(self.author_info_dir, f'author_{agent_id}.txt')) 
                             for agent_id in range(min(self.agent_num, len(self.adjacency_matrix)))]
            
            self.reviewer_pool = [self.init_reviewer(str(agent_id), review_model_config_name) 
                                for agent_id in range(self.reviewer_num)]
            
            self.id2agent = {agent.name: agent for agent in self.agent_pool}
            
            # Team Pool
            from sci_team.SciTeam import Team
            self.team_pool = []
            agent_id = 1
            for agent in self.agent_pool[:self.agent_num]:
                team_agent = []
                team_index = [agent.name]
                team_dic = Team(team_name=str(agent_id)+','+str(1),
                                log_dir=self.log_dir,
                                info_dir=self.info_dir)
                team_dic.teammate = team_index
                team_agent.append(team_dic)
                self.team_pool.append(team_agent)
                agent_id += 1
                
            self.HostMsg = partial(Msg, name="user", role="user", echo=True)
            
            # Create a dynamic paper dict that fetches from real VDB on access
            self.paper_dicts = DynamicPaperDict(self)
            self.paper_future_dicts = DynamicPaperDict(self)
            
            # Mock GPU Indexes (We will intercept search calls)
            self.gpu_index = MagicMock()
            self.gpu_future_index = MagicMock()
            
        finally:
            # Restore faiss BEFORE initializing Real RAG
            if original_read_index: faiss.read_index = original_read_index
            if original_gpu_resources: faiss.StandardGpuResources = original_gpu_resources
            if original_index_cpu_to_gpu: faiss.index_cpu_to_gpu = original_index_cpu_to_gpu

        # --- REAL RAG INITIALIZATION (Now with real FAISS) ---
        print(f"Initializing Real RAG from: {self.real_vdb_path}")
        
        # Use raw string to avoid JSON serialization issues with Enums
        self.embedding_model = OpenAICompatibleEmbedding(
            model_type="text-embedding-v2",
            api_key=os.environ.get("QWEN_API_KEY"),
            url=os.environ.get("QWEN_API_BASE_URL")
        )
        
        # Try to load abstract collection
        storage_path = os.path.join(self.real_vdb_path, "paper/abstract")
        if not os.path.exists(storage_path):
             storage_path = os.path.join(self.real_vdb_path, "abstract")
        
        self.vector_storage = FaissStorage(
            vector_dim=1536,
            storage_path=storage_path,
            collection_name="paper_abstract"
        )
        self.vector_storage.load()
        print(f"Real Vector DB Loaded.")
        
        # Load metadata cache for titles and abstracts
        self.title_cache = {}
        self.year_cache = {}
        self.citation_cache = {}
        self._load_metadata_cache()

    def init_agent(self, agent_id, agent_model_config_name, information_path):
        with open(information_path, 'r') as file:
            prompt = file.read()
        # Inject the fixed topic into the system prompt to force the agent to focus
        prompt += f"\n\nYour current research focus is specifically: '{self.topic_input}'."
        
        agent = SciAgent(
            name='Scientist{}'.format(agent_id),
            model_config_name=agent_model_config_name,
            sys_prompt=prompt,
        )
        return agent
    
    def _load_metadata_cache(self):
        """从JSON文件加载元数据缓存（标题、年份、引用数）"""
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
            print(f"⚠️  Could not load metadata cache: {e}")

    # --- THE KEY FUNCTION: Real Retrieval ---
    def reference_paper(self, key_string, cite_number):
        """
        Overrides the original retrieval to use CAMEL FaissStorage with real data.
        Updates paper_dicts cache so that subsequent access to paper_dicts[index] returns real data.
        """
        print(f"[RAG] Searching for: {key_string[:50]}...")
        
        # 1. Embed query
        query_vec = self.embedding_model.embed(obj=key_string)
        query_vec = np.array(query_vec, dtype=np.float32)
        
        # 2. Query Vector DB
        query_results = self.vector_storage.query(
            VectorDBQuery(query_vector=query_vec, top_k=cite_number)
        )
        
        # 3. Format Results and Update Cache
        paper_reference = ""
        indices = []
        
        for idx, res in enumerate(query_results):
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
            
            # 从缓存获取标题（尝试所有可能的paper_id）
            title = ""
            for pid in [paper_id, payload.get("source_id"), payload.get("doi_norm")]:
                if pid and pid in self.title_cache:
                    title = self.title_cache[pid]
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
            
            # Use idx as the "index" for this result
            # Update paper_dicts cache with real data
            self.paper_dicts.update_cache(idx, title, abstract)
            
            paper_reference += f"Paper {idx+1}:\nTitle: {title}\nAbstract: {abstract}\n\n"
            indices.append(idx)
            
        return paper_reference, indices

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", type=str, default="Machine Learning", help="Research Topic")
    args = parser.parse_args()

    mock_dir = "/root/autodl-tmp/Myexamples/comparative_experiments/Virtual-Scientists/mock_data"
    config_path = "/root/autodl-tmp/Myexamples/comparative_experiments/Virtual-Scientists/sci_platform/configs/model_configs_qwen.json"
    real_vdb = "/root/autodl-tmp/Myexamples/vdb/camel_faiss_storage"
    
    print("Initializing PlatformQwen with Real Data...")
    platform = PlatformQwen(
        mock_data_dir=mock_dir,
        model_config_path=config_path,
        real_vdb_path=real_vdb,
        topic=args.topic,
        agent_num=2,
        epochs=3,  # Reduced to 3 to speed up testing
        team_limit=1
    )
    
    print(f"Starting Experiment on Topic: {args.topic}")
    platform.running(epochs=3)
