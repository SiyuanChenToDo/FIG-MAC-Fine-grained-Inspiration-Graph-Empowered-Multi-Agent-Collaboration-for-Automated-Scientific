# from .arxiv_reader import Arxiv_Reader
# from .google_crawl import GoogleCrawler
from .sementic_search import SementicSearcher, Result
# from .ResearchAgentSearch import ResearchSearcher

# 如果环境变量COI_USE_REAL_VDB存在，使用真实VDB的Searcher
import os
# 默认使用真实VDB（除非明确设置为0）
if os.environ.get("COI_USE_REAL_VDB", "1") == "1":
    try:
        from .coi_searcher_qwen import CoISearcherQwen
        # 替换SementicSearcher为CoISearcherQwen（保持接口兼容）
        _original_SementicSearcher = SementicSearcher
        
        class SementicSearcher(CoISearcherQwen):
            """包装器，使CoISearcherQwen兼容原始SementicSearcher接口"""
            def __init__(self, save_file="papers/", ban_paper=[]):
                real_vdb_path = os.environ.get("COI_VDB_PATH", "/root/autodl-tmp/Myexamples/vdb/camel_faiss_storage")
                super().__init__(save_file=save_file, ban_paper=ban_paper, real_vdb_path=real_vdb_path)
    except (ImportError, Exception) as e:
        # 如果导入失败，使用原始的SementicSearcher
        print(f"Warning: Failed to load CoISearcherQwen, using original SementicSearcher: {e}")
        pass