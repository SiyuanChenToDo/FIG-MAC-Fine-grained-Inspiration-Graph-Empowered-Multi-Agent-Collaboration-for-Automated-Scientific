import torch
import dgl
import json
import numpy as np
from pathlib import Path
import faiss
import pandas as pd
from typing import List, Dict, Tuple, Optional
import logging
import os
import re
from collections import defaultdict
import pickle

# ===== SET HUGGINGFACE MIRROR BEFORE IMPORTING SENTENCE_TRANSFORMERS =====
# Set HuggingFace mirror early to ensure it's used when sentence-transformers loads models
hf_mirror = os.environ.get("HF_MIRROR", "https://hf-mirror.com")
os.environ["HF_ENDPOINT"] = hf_mirror
os.environ["HUGGINGFACE_HUB_CACHE"] = os.environ.get("HUGGINGFACE_HUB_CACHE",
    os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub"))

# Try to set huggingface_hub endpoint directly
try:
    import huggingface_hub
    if hasattr(huggingface_hub, 'constants'):
        huggingface_hub.constants.ENDPOINT = hf_mirror
except (ImportError, AttributeError):
    pass

# Set cache directories
cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "huggingface")
os.makedirs(cache_dir, exist_ok=True)
os.environ["HF_HOME"] = cache_dir
os.environ["TRANSFORMERS_CACHE"] = cache_dir
os.environ["SENTENCE_TRANSFORMERS_HOME"] = cache_dir
# ===== END EARLY MIRROR SETUP =====

# Now import sentence_transformers after setting up mirror
from sentence_transformers import SentenceTransformer

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ScientificInspirationPipeline:
    def __init__(self, 
                 graph_path: str,
                 node_map_path: str,
                 model_path: str,
                 raw_data_path: str,
                 embedding_model_name: str = 'all-MiniLM-L6-v2'):
        """
        初始化科学灵感发现流水线
        
        Args:
            graph_path: GraphStorm分区图数据路径
            node_map_path: 节点ID映射文件路径
            model_path: 训练好的链路预测模型路径
            raw_data_path: 原始文本数据路径 (parquet/csv)
        """
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # ===== SET HUGGINGFACE MIRROR BEFORE LOADING MODEL =====
        # Set HuggingFace mirror to avoid network issues when downloading models
        hf_mirror = os.environ.get("HF_MIRROR", "https://hf-mirror.com")
        
        # Set multiple environment variables for different libraries
        os.environ["HF_ENDPOINT"] = hf_mirror
        os.environ["HUGGINGFACE_HUB_CACHE"] = os.environ.get("HUGGINGFACE_HUB_CACHE", 
            os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub"))
        
        # Also set for huggingface_hub library directly
        try:
            import huggingface_hub
            # Set the endpoint for huggingface_hub
            huggingface_hub.constants.ENDPOINT = hf_mirror
            logger.info(f"Setting HuggingFace mirror via huggingface_hub: {hf_mirror}")
        except (ImportError, AttributeError):
            # If huggingface_hub is not available or doesn't have ENDPOINT, use env var
            logger.info(f"Setting HuggingFace mirror via HF_ENDPOINT: {hf_mirror}")
        
        # Set cache directories for transformers and sentence-transformers
        cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "huggingface")
        os.makedirs(cache_dir, exist_ok=True)
        os.environ["HF_HOME"] = cache_dir
        os.environ["TRANSFORMERS_CACHE"] = cache_dir
        os.environ["SENTENCE_TRANSFORMERS_HOME"] = cache_dir
        # ===== END MIRROR SETUP =====
        
        # 1. 加载文本编码模型 (本地 SentenceTransformer)
        logger.info(f"加载文本编码模型: {embedding_model_name}")
        try:
            # Try to load from local cache first
            try:
                self.encoder = SentenceTransformer(embedding_model_name, local_files_only=True)
                logger.info("Model loaded from local cache")
            except (OSError, ValueError) as local_error:
                # If not in cache, try to download (will use mirror if set)
                logger.info("Model not in local cache, attempting to download (will use mirror if configured)...")
                self.encoder = SentenceTransformer(embedding_model_name)
                logger.info("Model downloaded successfully")
        except Exception as e:
            logger.error(f"Failed to load SentenceTransformer model '{embedding_model_name}': {e}")
            logger.error("This may be due to network issues. Try setting HF_MIRROR environment variable.")
            logger.error("Or ensure the model is already downloaded to local cache.")
            raise
        
        # 2. 加载原始文本数据和构建/加载索引
        self._load_raw_data_and_build_index(raw_data_path)
        
        # 3. 加载图结构关系映射 (Hard Links)
        self._load_graph_structure(raw_data_path)
        
        # 4. 加载链路预测结果 (Predicted Links)
        self.predictions = self._load_predictions(model_path)
        
        logger.info("流水线初始化完成")

    def _load_raw_data_and_build_index(self, raw_data_path: str):
        """加载原始数据并构建FAISS索引"""
        logger.info("加载原始数据并构建向量索引...")
        raw_path = Path(raw_data_path)
        
        # 读取 Parquet 文件
        try:
            self.papers_df = pd.read_parquet(raw_path / 'neo4j_export/papers.parquet')
            self.rqs_df = pd.read_parquet(raw_path / 'neo4j_export/research_questions.parquet')
            self.sols_df = pd.read_parquet(raw_path / 'neo4j_export/solutions.parquet')
        except Exception as e:
            logger.error(f"读取Parquet文件失败: {e}")
            raise

        # 建立原始ID -> DataFrame索引的映射
        self.paper_id_lookup = pd.Series(self.papers_df.index, index=self.papers_df['entity_name']).to_dict()
        self.rq_id_lookup = pd.Series(self.rqs_df.index, index=self.rqs_df['rq_id']).to_dict()
        self.sol_id_lookup = pd.Series(self.sols_df.index, index=self.sols_df['sol_id']).to_dict()
        
        # 使用本地 SentenceTransformer 构建/加载索引
        index_path = raw_path / 'rq_faiss.index'
        if index_path.exists():
            logger.info(f"加载本地缓存的 FAISS 索引: {index_path}")
            self.rq_index = faiss.read_index(str(index_path))
        else:
            logger.info(f"为 {len(self.rqs_df)} 个 RQ 构建索引 (实时计算)...")
            rq_texts = self.rqs_df['research_question'].fillna("").tolist()
            embeddings = self.encoder.encode(rq_texts, convert_to_numpy=True, show_progress_bar=True)
            dim = embeddings.shape[1]
            self.rq_index = faiss.IndexFlatL2(dim)
            self.rq_index.add(embeddings)
            logger.info(f"保存索引到 {index_path}")
            faiss.write_index(self.rq_index, str(index_path))

    def _load_graph_structure(self, raw_data_path: str):
        """
        加载硬编码的图结构关系 (RQ->Sol, Paper->RQ 等)
        这里使用 Pandas DataFrame 模拟图的邻接表查询
        """
        logger.info("加载图结构关系...")
        base_dir = Path(raw_data_path) / 'neo4j_export'
        paper_rq_edges = pd.read_parquet(base_dir / 'paper_rq_edges.parquet')
        rq_sol_edges = pd.read_parquet(base_dir / 'rq_solution_edges.parquet')
        
        self.paper_to_rqs: Dict[int, List[int]] = defaultdict(list)
        self.rq_to_solutions: Dict[int, List[int]] = defaultdict(list)
        self.solution_to_rq: Dict[int, int] = {}
        
        # Paper -> RQ
        missing_papers = missing_rqs = 0
        for _, row in paper_rq_edges.iterrows():
            paper_idx = self.paper_id_lookup.get(row['src_id'])
            rq_idx = self.rq_id_lookup.get(row['tgt_id'])
            if paper_idx is None:
                missing_papers += 1
                continue
            if rq_idx is None:
                missing_rqs += 1
                continue
            self.paper_to_rqs[paper_idx].append(rq_idx)
        logger.info("Paper->RQ 关系加载完成 (缺失Paper:%d, 缺失RQ:%d)", missing_papers, missing_rqs)
        
        # RQ -> Solution
        missing_rqs = missing_solutions = 0
        for _, row in rq_sol_edges.iterrows():
            rq_idx = self.rq_id_lookup.get(row['src_id'])
            sol_idx = self.sol_id_lookup.get(row['tgt_id'])
            if rq_idx is None:
                missing_rqs += 1
                continue
            if sol_idx is None:
                missing_solutions += 1
                continue
            self.rq_to_solutions[rq_idx].append(sol_idx)
            self.solution_to_rq[sol_idx] = rq_idx
        logger.info("RQ->Solution 关系加载完成 (缺失RQ:%d, 缺失Solution:%d)", missing_rqs, missing_solutions)

    def _normalize_markdown_text(self, text: str) -> str:
        """
        规范化包含 LaTeX/Markdown 的文本，避免因符号导致的渲染异常。
        """
        if not isinstance(text, str):
            return ""
        
        # 1. 基础清理
        normalized = text.replace("\t", " ").replace("\r\n", "\n")
        
        # 2. 修复 LaTeX 公式中的常见问题
        normalized = normalized.replace(r'\[', '$$').replace(r'\]', '$$')
        normalized = normalized.replace(r'\(', '$').replace(r'\)', '$')

        # 3. 确保块级公式独立成段 ($$ ... $$)
        # 如果 $$ 前面不是换行，加换行
        normalized = re.sub(r'([^\n])\s*(\$\$)', r'\1\n\n\2', normalized)
        # 如果 $$ 后面不是换行，加换行
        normalized = re.sub(r'(\$\$)\s*([^\n])', r'\1\n\2', normalized)

        # 4. 行内公式 ($ ... $) 前后加空格，避免粘连
        # 使用负向先行/后行断言，确保不是 $$ (即不匹配前面有$或后面有$的情况)
        normalized = re.sub(r'(?<![\s\$])(\$[^$]+\$)(?!\$)', r' \1', normalized)
        normalized = re.sub(r'(?<!\$)(\$[^$]+\$)(?![\s\$])', r'\1 ', normalized)

        # 5. 压缩多余空行
        normalized = re.sub(r'\n{3,}', '\n\n', normalized)
        
        return normalized.strip()

    def _load_predictions(self, model_path: str) -> Dict:
        """加载链路预测的分数"""
        logger.info("加载预测模型输出...")
        infer_dir = Path(model_path)
        preds = {}
        
        # 关注 INSPIRED 边的预测
        # 注意：这里的目录名需要与实际训练输出一致
        # 假设是 'solution_inspired_paper'
        target_etype = 'solution_inspired_paper'
        
        # 检查可能的目录名变体
        possible_names = [target_etype, 'solution_inspired_paper'] # 可以添加更多
        
        found = False
        for name in possible_names:
            path = infer_dir / name
            if path.exists():
                logger.info(f"找到预测结果: {name}")
                preds['inspired'] = {
                    'pred': torch.load(path / 'predict-00000.pt'),
                    'src': torch.load(path / 'src_nids-00000.pt'),
                    'dst': torch.load(path / 'dst_nids-00000.pt')
                }
                found = True
                break
        
        if not found:
            logger.warning(f"未找到 {target_etype} 的预测结果，将跳过预测步骤。")
            
        return preds

    def retrieve_relevant_nodes(self, query: str, top_k: int = 5) -> List[Dict]:
        """阶段1: 检索 (SentenceTransformer + FAISS)"""
        logger.info(f"检索相关节点: '{query}'")
        query_vec = self.encoder.encode([query], convert_to_numpy=True)
        distances, indices = self.rq_index.search(query_vec, top_k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < 0 or idx >= len(self.rqs_df):
                continue
            rq_row = self.rqs_df.iloc[idx]
            results.append({
                'type': 'research_question',
                'id': int(idx),
                'text': rq_row.get('research_question', ''),
                'distance': float(distances[0][i])
            })
        return results

    def find_inspiration_paths(self, start_rq_id: int, top_k_paths: int = 3, inspired_top_k: int = 10) -> List[Dict]:
        """
        阶段2: 链路推理
        目标路径: RQ(A) -> Sol(A) --[INSPIRED]--> Paper(B) -> RQ(B) -> Sol(B)
        """
        logger.info(f"从 RQ ID {start_rq_id} 开始寻找灵感路径...")
        paths = []
        
        candidate_solutions = self.rq_to_solutions.get(start_rq_id, [])
        if not candidate_solutions and start_rq_id < len(self.sols_df):
            candidate_solutions = [start_rq_id]

        if not candidate_solutions:
            logger.warning("RQ %d 未找到关联 Solution，无法继续推理。", start_rq_id)
            return []

        for sol_a_id in candidate_solutions:
            if sol_a_id >= len(self.sols_df):
                continue

            sol_a_text = self.sols_df.iloc[sol_a_id].get('solution', 'Unknown')

            # 2. Sol(A) -> Paper(B) [Predicted INSPIRED Link]
            inspired_papers = self._get_predicted_inspired_papers(sol_a_id, top_k=inspired_top_k)
            
            for paper_b_id, score in inspired_papers:
                if paper_b_id >= len(self.papers_df): 
                    continue
                
                paper_b = self.papers_df.iloc[paper_b_id]
                paper_b_title = paper_b.get('title', 'Unknown')

                # 3. Paper(B) -> RQ(B) -> Sol(B) [Hard Link]
                rq_b_ids = self.paper_to_rqs.get(paper_b_id, [])
                rq_b_texts = [self.rqs_df.iloc[rq]['research_question'] for rq in rq_b_ids[:2]] if rq_b_ids else []
                sol_b_texts = []
                for rq_b in rq_b_ids:
                    for sol_b in self.rq_to_solutions.get(rq_b, []):
                        if sol_b < len(self.sols_df):
                            sol_b_texts.append(self.sols_df.iloc[sol_b]['solution'])
                # 构造路径对象
                path = {
                    'score': float(score), # 转换为 float 以便序列化
                    'start_node': {
                        'type': 'RQ',
                        'id': start_rq_id,
                        'text': self.rqs_df.iloc[start_rq_id].get('research_question', '')
                    },
                    'current_solution': {
                        'type': 'Solution',
                        'id': sol_a_id,
                        'text': sol_a_text
                    },
                    'inspired_paper': {
                        'type': 'Paper',
                        'id': paper_b_id,
                        'title': paper_b_title,
                        'abstract': paper_b.get('abstract', '')
                    },
                    'target_rqs': rq_b_texts,
                    'target_solutions': sol_b_texts,
                    'inference_chain': [
                        f"Original Problem: {self.rqs_df.iloc[start_rq_id].get('research_question', '')[:50]}...",
                        f"Current Solution: {sol_a_text[:50]}...",
                        f"--> INSPIRED (Rank: {score:.1f}) -->",
                        f"Target Paper: {paper_b_title}"
                    ]
                }
                paths.append(path)
            
        return sorted(paths, key=lambda x: x['score'])[:top_k_paths]

    def _get_predicted_inspired_papers(self, sol_id: int, top_k: int = 5) -> List[Tuple[int, float]]:
        """获取被 Sol(A) 启发的 Paper(B)"""
        if 'inspired' not in self.predictions:
            return []
            
        data = self.predictions['inspired']
        # 找到 src == sol_id 的所有预测
        # 注意：这里是在 CPU 上操作张量
        mask = data['src'] == sol_id
        
        if not mask.any():
            return []
            
        dsts = data['dst'][mask]
        ranks = data['pred'][mask]
        
        # 转换为 list
        pairs = list(zip(dsts.tolist(), ranks.tolist()))
        # Rank 越小越好
        pairs.sort(key=lambda x: x[1])
        
        return pairs[:top_k]

    def generate_structured_output(self, paths: List[Dict]) -> str:
        """
        阶段3: 结构化输出
        生成 Markdown 格式的报告，供下游 LLM 使用
        """
        if not paths:
            return "未发现有效的灵感路径。"
            
        output = []
        output.append("# 科学灵感推理报告")
        output.append(f"生成时间: {pd.Timestamp.now()}")
        output.append("")
        
        for i, path in enumerate(paths, 1):
            output.append(f"## 🔗 灵感链路 {i} (置信度 Rank: {path['score']})")
            output.append("")
            rq_text = self._normalize_markdown_text(path['start_node']['text'])
            sol_text = self._normalize_markdown_text(path['current_solution']['text'])
            paper_title = self._normalize_markdown_text(path['inspired_paper']['title'])
            paper_abs = self._normalize_markdown_text(path['inspired_paper']['abstract'])
            target_rqs = [self._normalize_markdown_text(t) for t in path.get('target_rqs', []) if t]
            target_sols = [self._normalize_markdown_text(t) for t in path.get('target_solutions', []) if t]
            inference_chain = " > ".join(self._normalize_markdown_text(step) for step in path['inference_chain'])

            output.append("### 1. 起始点 (Source Context)")
            output.append(f"- **研究问题 (RQ)**: {rq_text}")
            output.append(f"- **现有方案 (Sol)**: {sol_text}")
            output.append("")
            output.append("### 2. 跨领域启发 (Cross-Domain Inspiration)")
            output.append(f"- **关联论文**: 《{paper_title}》")
            output.append(f"- **论文摘要**: {paper_abs}")
            output.append("")
            if target_rqs:
                output.append("### 3. 目标论文的研究问题")
                for rq_text in target_rqs:
                    output.append(f"- {rq_text}")
                output.append("")
            if target_sols:
                output.append("### 4. 目标论文的方案/方法")
                for sol_text in target_sols:
                    output.append(f"- {sol_text}")
                output.append("")
            output.append("### 3. 推理逻辑 (Reasoning Chain)")
            output.append(inference_chain)
            output.append("")
            output.append("---")
            output.append("")
            
        return "\n".join(output)

    def get_report(self, query: str, min_paths: int = 3, start_top_k: int = 5) -> str:
        """获取灵感报告内容（字符串形式）"""
        start_nodes = self.retrieve_relevant_nodes(query, top_k=start_top_k)
        
        if not start_nodes:
            return "未找到匹配的研究问题。"
            
        paths_pool = []
        seen_pairs = set()
        
        def collect_paths(node, per_node_limit=5, inspired_top_k=20):
            node_paths = self.find_inspiration_paths(
                node['id'],
                top_k_paths=per_node_limit,
                inspired_top_k=inspired_top_k
            )
            for path in node_paths:
                key = (path['start_node']['id'], path['inspired_paper']['id'])
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)
                path['source_node_distance'] = node.get('distance', 0.0)
                paths_pool.append(path)
        
        # Logic copied from run()
        for node in start_nodes[:3]:
            collect_paths(node, per_node_limit=max(min_paths, 5), inspired_top_k=25)
        
        if len(paths_pool) < min_paths:
            for node in start_nodes[3:]:
                collect_paths(node, per_node_limit=max(min_paths, 5), inspired_top_k=30)
                if len(paths_pool) >= min_paths * 2:
                    break
        
        if len(paths_pool) < min_paths and start_nodes:
            collect_paths(start_nodes[0], per_node_limit=min_paths * 3, inspired_top_k=50)
        
        if not paths_pool:
            return "未找到有效的灵感路径。"
        
        paths_pool.sort(key=lambda x: (x['score'], x.get('source_node_distance', 0)))
        paths = paths_pool[:max(min_paths, len(paths_pool))]
        
        return self.generate_structured_output(paths)

    def run(self, query: str, output_file: str = 'inspiration_report.md',
            min_paths: int = 3, start_top_k: int = 5):
        """执行完整流程，确保至少输出 min_paths 条灵感链路"""
        print(f"\n[1] 正在检索与 '{query}' 相关的研究问题...")
        start_nodes = self.retrieve_relevant_nodes(query, top_k=start_top_k)
        
        if not start_nodes:
            print("未找到匹配的研究问题。")
            return
            
        print(f"   匹配到前 {min(len(start_nodes), start_top_k)} 个候选 RQ。")
        
        print(f"\n[2] 正在图谱上进行链路预测与推理...")
        paths_pool = []
        seen_pairs = set()
        
        def collect_paths(node, per_node_limit=5, inspired_top_k=20):
            node_paths = self.find_inspiration_paths(
                node['id'],
                top_k_paths=per_node_limit,
                inspired_top_k=inspired_top_k
            )
            for path in node_paths:
                key = (path['start_node']['id'], path['inspired_paper']['id'])
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)
                path['source_node_distance'] = node.get('distance', 0.0)
                paths_pool.append(path)
        
        # 首先处理最相关的前三个起点
        for node in start_nodes[:3]:
            collect_paths(node, per_node_limit=max(min_paths, 5), inspired_top_k=25)
        
        # 如果不足，再尝试其他起点
        if len(paths_pool) < min_paths:
            for node in start_nodes[3:]:
                collect_paths(node, per_node_limit=max(min_paths, 5), inspired_top_k=30)
                if len(paths_pool) >= min_paths * 2:
                    break
        
        # 仍不足时，放宽当前最佳起点的搜索范围
        if len(paths_pool) < min_paths and start_nodes:
            collect_paths(start_nodes[0], per_node_limit=min_paths * 3, inspired_top_k=50)
        
        if not paths_pool:
            print("未找到有效的灵感路径。")
            return
        
        paths_pool.sort(key=lambda x: (x['score'], x.get('source_node_distance', 0)))
        paths = paths_pool[:max(min_paths, len(paths_pool))]
        
        print(f"\n[3] 生成结构化报告 (共 {len(paths)} 条灵感链路)...")
        report = self.generate_structured_output(paths)
        
        with open(output_file, 'w') as f:
            f.write(report)
            
        print(f"   报告已保存至: {output_file}")
        print("\n预览:")
        print("-" * 50)
        print(report[:500] + "...\n(更多内容见文件)")
        print("-" * 50)

if __name__ == "__main__":
    # 配置路径 (请根据实际环境修改)
    BASE_DIR = Path('/root/autodl-tmp')
    GRAPH_DIR = BASE_DIR / 'data/graphstorm_partitioned'
    RAW_DIR = BASE_DIR / 'data'
    MODEL_DIR = BASE_DIR / 'workspace/inference_results/best_model_v1/predictions' 
    
    pipeline = ScientificInspirationPipeline(
        graph_path=str(GRAPH_DIR),
        node_map_path=str(GRAPH_DIR / 'raw_id_mappings'),
        model_path=str(MODEL_DIR),
        raw_data_path=str(RAW_DIR)
    )
    
    # 交互式运行
    import sys
    if len(sys.argv) > 1:
        query = sys.argv[1]
    else:
        query = input("请输入研究问题或Topic: ")
        
    pipeline.run(query)
