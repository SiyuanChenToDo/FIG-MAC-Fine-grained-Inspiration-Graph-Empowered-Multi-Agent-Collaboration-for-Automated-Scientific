"""
跨论文Paper-Solution关系人工标注数据生成脚本
===================================================
功能：
1. 从向量数据库读取Paper的abstract+core_problem和Solution数据
2. 随机生成1550条跨论文配对
3. 调用LLM进行初步三分类(INSPIRED/RELATED/NONE)
4. 分配数据给三位博士生进行人工校验：
   - 50条共同校验
   - 每人500条独立校验(100条精确+400条大致)
5. 生成JSON格式的标注文件，便于中文翻译
"""

import os
import sys
import json
import random
import time
from datetime import datetime
from typing import List, Dict, Tuple
import numpy as np

from camel.storages import FaissStorage, VectorDBQuery
from camel.embeddings import OpenAICompatibleEmbedding
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.configs import QwenConfig
from camel.agents import ChatAgent
from camel.messages import BaseMessage

# =================================================================================
# 1. 环境配置
# =================================================================================
os.environ["OPENAI_COMPATIBILITY_API_KEY"] = "sk-875e0cf57dd34df59d3bcaef4ee47f80"
os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
os.environ["QWEN_API_KEY"] = os.environ["OPENAI_COMPATIBILITY_API_KEY"]
os.environ["QWEN_API_BASE_URL"] = os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"]

# 配置参数
CONFIG = {
    "TOTAL_SAMPLES": 1550,  # 总样本数
    "COMMON_SAMPLES": 50,   # 三人共同校验的样本数
    "SAMPLES_PER_PERSON": 500,  # 每人校验的总样本数(包括共同的50条)
    "PRECISE_SAMPLES_PER_PERSON": 100,  # 每人精确校验的样本数
    "ROUGH_SAMPLES_PER_PERSON": 400,    # 每人大致校验的样本数
    "ANNOTATORS": ["博士生A", "博士生B", "博士生C"],
    "BASE_VDB_PATH": "Myexamples/vdb/camel_faiss_storage",
    "OUTPUT_DIR": "Myexamples/build_graph_connections/annotation_data",
    "JSON_FILE_PATH": "Myexamples/data/final_data/final_custom_kg_papers.json",
    "SEED": 42,  # 随机种子，确保可复现
    
    # 相似度初筛配置
    "USE_SIMILARITY_FILTER": True,  # 是否启用相似度初筛
    "AUTO_TUNE_THRESHOLD": True,  # 是否自动调优阈值（基于统计分析）
    "SIMILARITY_THRESHOLD": 0.3,  # 相似度阈值（加权分数，如果AUTO_TUNE_THRESHOLD=False则使用此值）
    "SIMILARITY_WEIGHTS": {
        "abstract": 0.4,  # abstract的权重
        "core_problem": 0.6,  # core_problem的权重
    },
    "CANDIDATE_POOL_SIZE": 5000,  # 初筛后的候选池大小（从中抽取1550条）
    "SAMPLE_SIZE_FOR_STATS": 10000,  # 用于统计分析的样本数量
}

# LLM评估prompt - 增强版
LLM_EVALUATION_PROMPT = """你是一位资深的人工智能与计算机科学领域的科研专家，具有深厚的跨学科分析能力。你的任务是精确评估两篇不同科研论文之间的技术关联性，判断一篇论文的解决方案是否能对另一篇论文的研究问题产生启发或存在学术关联。

═══════════════════════════════════════════════════════════════════════
【分析对象】
═══════════════════════════════════════════════════════════════════════

📄 **论文 A（问题方）**
研究焦点：正在尝试解决以下核心问题
{paper_content}

💡 **论文 B（方案方）**
技术贡献：提出了以下解决方案
{solution_text}

═══════════════════════════════════════════════════════════════════════
【分析框架：请按以下步骤进行系统性思考】
═══════════════════════════════════════════════════════════════════════

## 第一步：技术要素提取
1. 从论文A中识别：
   - 核心研究问题的本质（如：性能优化、准确率提升、可解释性等）
   - 目标应用领域（如：计算机视觉、自然语言处理、推荐系统等）
   - 面临的技术挑战（如：数据稀疏、维度灾难、计算复杂度等）

2. 从论文B中识别：
   - 解决方案的核心技术（如：注意力机制、图神经网络、对比学习等）
   - 适用的问题类型（如：序列建模、关系推理、表示学习等）
   - 创新点和技术优势（如：参数高效、可扩展性、理论保证等）

## 第二步：关系类型判断

### 🔥 **INSPIRED（启发关系）** - 满足以下任一条件：

**核心标准**：论文B的方案能够直接或间接地帮助解决论文A的问题

**具体判断依据**：
1. **方法可迁移性**：B的技术方法可以直接应用或经过适配后应用于A的问题场景
   - 示例：A研究图像分类准确率提升 ← B提出的自注意力机制可直接用于特征增强
   
2. **思路启发性**：B的解决思路为A提供了新的研究方向或优化策略
   - 示例：A研究少样本学习 ← B提出的元学习框架提供了可借鉴的训练范式
   
3. **技术组件复用**：B中的某个模块/组件可以作为A问题的解决方案的一部分
   - 示例：A研究多模态融合 ← B提出的跨模态对齐模块可作为关键组件
   
4. **问题分解启发**：B解决的子问题是A核心问题的重要组成部分
   - 示例：A研究端到端对话系统 ← B解决的意图识别问题是对话系统的关键环节

**判断关键**：
- ✅ 如果能具体描述"B的XX技术/方法可以用来解决/改进A的YY问题"
- ✅ 如果A的研究者看到B的工作后很可能会说"这个方法对我的问题有用"
- ❌ 仅仅是研究领域相同但技术路径完全不同，不构成启发

---

### 🔗 **RELATED（相关关系）** - 满足以下特征：

**核心标准**：两者在研究领域、技术栈或问题类型上高度相似，但B的方案不能直接解决A的问题

**具体判断依据**：
1. **同一研究领域**：都属于相同的技术领域但解决不同子问题
   - 示例：A研究图像语义分割 ↔ B研究图像目标检测（都是计算机视觉，但任务不同）
   
2. **技术栈重叠**：使用相似的基础技术但应用于不同目标
   - 示例：A用Transformer做机器翻译 ↔ B用Transformer做文本摘要（技术相同，应用不同）
   
3. **问题类型相似**：面临类似的技术挑战但在不同应用场景
   - 示例：A研究电商推荐中的冷启动 ↔ B研究视频推荐中的冷启动（场景不同）
   
4. **并行研究方向**：属于同一大类问题的不同研究分支
   - 示例：A研究监督学习的过拟合 ↔ B研究半监督学习的标签噪声（都关注学习鲁棒性）

**判断关键**：
- ✅ 两者可能出现在同一学术会议的同一track中
- ✅ A和B的研究者会相互引用对方的相关工作（related work）
- ✅ 如果描述为"A和B都在研究XX领域，但侧重点不同"
- ❌ 如果B的方法能解决A的问题，应判断为INSPIRED而非RELATED

---

### ⭕ **NONE（无明确关系）** - 满足以下特征：

**核心标准**：两者在技术路径、应用领域、问题类型上缺乏显著关联

**具体判断依据**：
1. **领域隔离**：属于完全不同的研究领域
   - 示例：A研究计算机视觉 ↔ B研究数据库查询优化
   
2. **技术异构**：使用的技术栈和方法论完全不同
   - 示例：A基于深度学习 ↔ B基于传统数学优化方法
   
3. **问题无交集**：解决的问题类型完全不相关
   - 示例：A研究图像生成 ↔ B研究时间序列预测
   
4. **抽象层次差异**：一个是理论研究，一个是应用实现，且无桥接关系
   - 示例：A研究神经网络的泛化理论 ↔ B开发具体的移动端应用

**判断关键**：
- ✅ 如果A的研究者不太可能阅读或引用B的论文
- ✅ 两者的关键词、技术术语几乎没有重叠
- ✅ 无法找到任何技术或方法上的连接点

═══════════════════════════════════════════════════════════════════════
【边界情况处理指南】
═══════════════════════════════════════════════════════════════════════

⚠️ **INSPIRED vs RELATED 的区分**：
- 关键问题："B能帮助解决A吗？"
  - 能 → INSPIRED
  - 不能，但在相似领域 → RELATED

⚠️ **RELATED vs NONE 的区分**：
- 关键问题："它们在学术上有交集吗？"
  - 有（同领域、同技术、同问题类型）→ RELATED
  - 无（完全不同的研究方向）→ NONE

⚠️ **通用技术的判断**：
- 如果B提出的是非常通用的技术（如Dropout、Batch Normalization），而A是任何需要神经网络的任务：
  - 应判断为 **INSPIRED**（因为确实可以应用）

⚠️ **同一问题的不同方法**：
- 如果A和B都在解决"图像分类"问题但用完全不同的方法：
  - 应判断为 **RELATED**（问题相同但方案不同）

═══════════════════════════════════════════════════════════════════════
【输出要求】
═══════════════════════════════════════════════════════════════════════

请严格按照以下JSON格式输出你的判断结果，**不要添加markdown代码块标记**，**不要添加任何额外文字**：

{{
  "relationship_type": "INSPIRED" | "RELATED" | "NONE",
  "reasoning": "用1-2句话清晰说明判断理由，必须包含：(1)识别出的关键技术/问题；(2)两者的具体关联或差异。控制在100字以内。"
}}

**reasoning字段要求**：
- ✅ 具体：明确指出技术名称、问题类型
- ✅ 逻辑：说明为什么判断为该类型
- ❌ 避免：模糊的表述如"有一定关联"、"可能有用"
- ❌ 避免：重复题目内容

**示例输出**：
{{
  "relationship_type": "INSPIRED",
  "reasoning": "论文B提出的多头注意力机制可以直接应用于论文A的序列建模任务中，用于捕获长距离依赖关系，从而提升模型性能。"
}}

现在请开始分析上述两篇论文的关系。
"""

print("✅ 环境配置完成")

# =================================================================================
# 2. 初始化模型和存储
# =================================================================================
def initialize_models():
    """初始化LLM模型和embedding模型"""
    llm_model = ModelFactory.create(
        model_platform=ModelPlatformType.QWEN,
        model_type=ModelType.COMETAPI_QWEN3_CODER_PLUS_2025_07_22,
        model_config_dict=QwenConfig(temperature=0.1).as_dict(),
        api_key=os.environ["QWEN_API_KEY"],
        url=os.environ["QWEN_API_BASE_URL"],
    )
    
    embedding_model = OpenAICompatibleEmbedding(
        model_type="text-embedding-v2",
        api_key=os.environ["OPENAI_COMPATIBILITY_API_KEY"],
        url=os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"],
    )
    
    return llm_model, embedding_model

def load_vector_storage(entity_type: str, attribute: str, embedding_model):
    """加载指定的向量存储"""
    storage_path = os.path.join(CONFIG["BASE_VDB_PATH"], entity_type, attribute)
    collection_name = f"{entity_type}_{attribute}"
    index_file_path = os.path.join(storage_path, f"{collection_name}.index")
    
    if not os.path.exists(index_file_path):
        raise FileNotFoundError(f"向量索引文件不存在: {index_file_path}")
    
    print(f"加载向量存储: {entity_type}.{attribute}")
    storage = FaissStorage(
        vector_dim=embedding_model.get_output_dim(),
        storage_path=storage_path,
        collection_name=collection_name,
    )
    storage.load()
    
    status = storage.status()
    print(f"  - 向量数量: {status.vector_count}")
    
    return storage

# =================================================================================
# 3. 数据提取和配对生成
# =================================================================================
def extract_random_sample_from_storage(storage, sample_size: int, seed: int = 42, include_vector: bool = False) -> List[Dict]:
    """
    从存储中随机抽样指定数量的记录，避免加载全部数据
    
    Args:
        storage: 向量存储对象
        sample_size: 抽样数量
        seed: 随机种子
        include_vector: 是否包含vector（如果为True，返回的dict中会包含'vector'字段）
    
    Returns:
        记录列表，每条记录包含payload（和可选的vector）
    """
    records = []
    status = storage.status()
    vector_count = status.vector_count
    
    if vector_count == 0:
        return records
    
    # 如果数据量小于需要的样本量，则全部提取
    actual_sample_size = min(sample_size, vector_count)
    
    print(f"  - 从 {vector_count} 条记录中随机抽样 {actual_sample_size} 条...")
    
    # 生成随机索引
    random.seed(seed)
    random_indices = random.sample(range(vector_count), actual_sample_size)
    random_indices_set = set(random_indices)
    
    # 使用dummy query获取数据，但只保留随机选中的索引
    dummy_vector = np.zeros(storage.vector_dim)
    query = VectorDBQuery(query_vector=dummy_vector, top_k=vector_count)
    results = storage.query(query=query)
    
    # 只提取随机选中的记录
    for idx, res in enumerate(results):
        if idx in random_indices_set:
            record_data = res.record.payload.copy()
            if include_vector:
                record_data['vector'] = res.record.vector
            records.append(record_data)
        if len(records) >= actual_sample_size:
            break
    
    print(f"  ✅ 成功抽样 {len(records)} 条记录")
    
    return records

def extract_papers_by_ids(storage, paper_ids: set, include_vector: bool = True) -> List[Dict]:
    """
    根据paper_id列表从存储中提取对应的记录
    
    Args:
        storage: 向量存储对象
        paper_ids: 要提取的paper_id集合
        include_vector: 是否包含vector
    
    Returns:
        记录列表
    """
    records = []
    status = storage.status()
    vector_count = status.vector_count
    
    if vector_count == 0 or len(paper_ids) == 0:
        return records
    
    print(f"  - 从存储中提取 {len(paper_ids)} 个指定paper的数据...")
    
    # 使用dummy query获取所有数据
    dummy_vector = np.zeros(storage.vector_dim)
    query = VectorDBQuery(query_vector=dummy_vector, top_k=vector_count)
    results = storage.query(query=query)
    
    # 只提取指定paper_id的记录
    for res in results:
        payload = res.record.payload
        if payload.get("paper_id") in paper_ids:
            record_data = payload.copy()
            if include_vector:
                record_data['vector'] = res.record.vector
            records.append(record_data)
        if len(records) >= len(paper_ids):
            break
    
    print(f"  ✅ 成功提取 {len(records)} 条记录")
    
    return records

def cosine_similarity(vec1, vec2):
    """计算两个向量的余弦相似度"""
    if vec1 is None or vec2 is None:
        return 0.0
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)

def analyze_similarity_distribution(
    abstract_storage,
    core_problem_storage,
    solution_storage,
    paper_abstracts: List[Dict],
    paper_core_problems: List[Dict],
    solutions: List[Dict],
    sample_size: int,
    weights: Dict[str, float],
    seed: int = 42
) -> Dict:
    """
    统计分析相似度分布，为阈值选择提供科学依据
    
    返回:
    {
        "statistics": {统计信息},
        "recommended_threshold": 推荐的阈值,
        "distribution": 相似度分布数据
    }
    """
    print("\n" + "="*80)
    print("【相似度分布统计分析】")
    print("="*80)
    
    random.seed(seed)
    
    # 构建paper数据映射
    paper_data_map = {}
    for abstract_record in paper_abstracts:
        paper_id = abstract_record.get("paper_id")
        if paper_id:
            if paper_id not in paper_data_map:
                paper_data_map[paper_id] = {}
            paper_data_map[paper_id]["abstract"] = abstract_record.get("text", "")
    
    for core_problem_record in paper_core_problems:
        paper_id = core_problem_record.get("paper_id")
        if paper_id:
            if paper_id not in paper_data_map:
                paper_data_map[paper_id] = {}
            paper_data_map[paper_id]["core_problem"] = core_problem_record.get("text", "")
    
    valid_papers = {
        pid: content for pid, content in paper_data_map.items()
        if "abstract" in content and "core_problem" in content
    }
    
    print(f"\n有效Paper数量: {len(valid_papers)}")
    print(f"Solution数量: {len(solutions)}")
    
    # 直接从抽样数据中提取embeddings（数据已包含vector）
    print(f"\n正在从抽样数据中提取embeddings...")
    paper_embeddings = {}
    solution_embeddings = {}
    
    # 从paper_abstracts中提取embeddings（数据已包含vector字段）
    for abstract_record in paper_abstracts:
        paper_id = abstract_record.get("paper_id")
        if paper_id and paper_id in valid_papers:
            if paper_id not in paper_embeddings:
                paper_embeddings[paper_id] = {}
            paper_embeddings[paper_id]["abstract_vec"] = abstract_record.get("vector")
    
    # 从paper_core_problems中提取embeddings
    for core_problem_record in paper_core_problems:
        paper_id = core_problem_record.get("paper_id")
        if paper_id and paper_id in valid_papers and paper_id in paper_embeddings:
            paper_embeddings[paper_id]["core_problem_vec"] = core_problem_record.get("vector")
    
    # 从solutions中提取embeddings
    for solution in solutions:
        solution_paper_id = solution.get("paper_id")
        if solution_paper_id:
            solution_embeddings[solution_paper_id] = solution.get("vector")
    
    print(f"  ✅ 获取到 {len(paper_embeddings)} 个paper的embeddings (目标: {len(valid_papers)})")
    print(f"  ✅ 获取到 {len(solution_embeddings)} 个solution的embeddings (目标: {len(solutions)})")
    
    # 检查是否成功获取embeddings
    if len(paper_embeddings) == 0:
        print(f"  ❌ 错误: 未能获取到任何paper的embeddings")
        print(f"  提示: 请确保抽样时使用了include_vector=True参数")
        return {
            "statistics": {},
            "recommended_threshold": 0.3,
            "distribution": {}
        }
    
    if len(solution_embeddings) == 0:
        print(f"  ❌ 错误: 未能获取到任何solution的embeddings")
        return {
            "statistics": {},
            "recommended_threshold": 0.3,
            "distribution": {}
        }
    
    # 随机抽样计算相似度
    print(f"\n正在随机抽样 {sample_size} 对进行相似度计算...")
    
    valid_paper_ids = [pid for pid in valid_papers.keys() if pid in paper_embeddings]
    valid_solution_ids = list(solution_embeddings.keys())
    
    similarity_scores = []
    sim_abstract_list = []
    sim_core_problem_list = []
    
    sampled_count = 0
    attempts = 0
    max_attempts = sample_size * 10
    
    while sampled_count < sample_size and attempts < max_attempts:
        attempts += 1
        
        # 随机选择一对
        paper_id = random.choice(valid_paper_ids)
        solution_id = random.choice(valid_solution_ids)
        
        # 确保跨论文
        if paper_id == solution_id:
            continue
        
        abstract_vec = paper_embeddings[paper_id].get("abstract_vec")
        core_problem_vec = paper_embeddings[paper_id].get("core_problem_vec")
        solution_vec = solution_embeddings[solution_id]
        
        if abstract_vec is None or core_problem_vec is None or solution_vec is None:
            continue
        
        # 计算相似度
        sim_abstract = cosine_similarity(abstract_vec, solution_vec)
        sim_core_problem = cosine_similarity(core_problem_vec, solution_vec)
        weighted_score = sim_abstract * weights["abstract"] + sim_core_problem * weights["core_problem"]
        
        similarity_scores.append(weighted_score)
        sim_abstract_list.append(sim_abstract)
        sim_core_problem_list.append(sim_core_problem)
        
        sampled_count += 1
        
        if sampled_count % 1000 == 0:
            print(f"  进度: {sampled_count}/{sample_size}")
    
    # 统计分析
    similarity_scores = np.array(similarity_scores)
    sim_abstract_array = np.array(sim_abstract_list)
    sim_core_problem_array = np.array(sim_core_problem_list)
    
    print("\n" + "="*80)
    print("【统计结果】")
    print("="*80)
    
    print(f"\n📊 加权相似度分布 (权重: abstract={weights['abstract']}, core_problem={weights['core_problem']}):")
    print(f"  - 样本数: {len(similarity_scores)}")
    print(f"  - 最小值: {np.min(similarity_scores):.4f}")
    print(f"  - 最大值: {np.max(similarity_scores):.4f}")
    print(f"  - 平均值: {np.mean(similarity_scores):.4f}")
    print(f"  - 中位数: {np.median(similarity_scores):.4f}")
    print(f"  - 标准差: {np.std(similarity_scores):.4f}")
    print(f"\n  百分位数:")
    for p in [50, 60, 70, 75, 80, 85, 90, 95, 99]:
        percentile_value = np.percentile(similarity_scores, p)
        count_above = np.sum(similarity_scores >= percentile_value)
        print(f"    {p}%: {percentile_value:.4f} (≥此值的配对数: {count_above})")
    
    print(f"\n📊 Abstract相似度分布:")
    print(f"  - 平均值: {np.mean(sim_abstract_array):.4f}")
    print(f"  - 中位数: {np.median(sim_abstract_array):.4f}")
    print(f"  - 标准差: {np.std(sim_abstract_array):.4f}")
    
    print(f"\n📊 Core Problem相似度分布:")
    print(f"  - 平均值: {np.mean(sim_core_problem_array):.4f}")
    print(f"  - 中位数: {np.median(sim_core_problem_array):.4f}")
    print(f"  - 标准差: {np.std(sim_core_problem_array):.4f}")
    
    # 推荐阈值
    print(f"\n" + "="*80)
    print("【阈值推荐】")
    print("="*80)
    
    # 计算不同阈值下能获得的配对数量
    total_possible_pairs = len(valid_paper_ids) * len(valid_solution_ids)
    
    print(f"\n基于统计分析，以下是不同阈值的预估结果:")
    print(f"(总可能配对数: {total_possible_pairs:,})\n")
    
    recommended_thresholds = []
    
    for percentile in [70, 75, 80, 85, 90]:
        threshold = np.percentile(similarity_scores, percentile)
        estimated_count = int(total_possible_pairs * (100 - percentile) / 100)
        
        print(f"  阈值 {threshold:.4f} (第{percentile}百分位):")
        print(f"    - 预估可获得配对数: {estimated_count:,}")
        
        if estimated_count >= 5000:
            print(f"    - 评估: ✅ 足够 (>5000)")
            recommended_thresholds.append((threshold, estimated_count, percentile))
        elif estimated_count >= 1550:
            print(f"    - 评估: ⚠️ 勉强够用 (>1550)")
            recommended_thresholds.append((threshold, estimated_count, percentile))
        else:
            print(f"    - 评估: ❌ 不足 (<1550)")
    
    # 选择推荐阈值
    if recommended_thresholds:
        # 选择能获得5000+配对的最高阈值
        good_thresholds = [(t, c, p) for t, c, p in recommended_thresholds if c >= 5000]
        if good_thresholds:
            recommended_threshold, est_count, percentile = max(good_thresholds, key=lambda x: x[0])
        else:
            recommended_threshold, est_count, percentile = recommended_thresholds[0]
        
        print(f"\n💡 推荐阈值: {recommended_threshold:.4f} (第{percentile}百分位)")
        print(f"   预估可获得 {est_count:,} 个高质量配对")
    else:
        recommended_threshold = np.percentile(similarity_scores, 50)
        print(f"\n💡 推荐阈值: {recommended_threshold:.4f} (中位数)")
        print(f"   ⚠️ 警告: 可能需要增加抽样数量")
    
    print("\n" + "="*80)
    
    return {
        "statistics": {
            "mean": float(np.mean(similarity_scores)),
            "median": float(np.median(similarity_scores)),
            "std": float(np.std(similarity_scores)),
            "min": float(np.min(similarity_scores)),
            "max": float(np.max(similarity_scores)),
            "percentiles": {p: float(np.percentile(similarity_scores, p)) for p in [50, 70, 75, 80, 85, 90, 95, 99]},
        },
        "recommended_threshold": float(recommended_threshold),
        "distribution": {
            "weighted_scores": similarity_scores.tolist(),
            "abstract_scores": sim_abstract_array.tolist(),
            "core_problem_scores": sim_core_problem_array.tolist(),
        }
    }

def generate_cross_paper_pairs_with_similarity_filter(
    abstract_storage,
    core_problem_storage,
    solution_storage,
    paper_abstracts: List[Dict],
    paper_core_problems: List[Dict],
    solutions: List[Dict],
    num_pairs: int,
    candidate_pool_size: int,
    similarity_threshold: float,
    weights: Dict[str, float],
    seed: int = 42
) -> List[Dict]:
    """
    生成跨论文的配对数据（优化版：相似度初筛 + 随机抽样）
    
    流程:
    1. 从向量数据库中获取embedding
    2. 计算相似度并初筛出高相似度的配对
    3. 从初筛结果中随机抽样num_pairs条
    """
    random.seed(seed)
    
    print(f"\n开始相似度初筛...")
    print(f"  - 相似度阈值: {similarity_threshold}")
    print(f"  - 权重配置: abstract={weights['abstract']}, core_problem={weights['core_problem']}")
    
    # 构建paper_id到数据的映射
    paper_data_map = {}
    
    for abstract_record in paper_abstracts:
        paper_id = abstract_record.get("paper_id")
        if paper_id:
            if paper_id not in paper_data_map:
                paper_data_map[paper_id] = {}
            paper_data_map[paper_id]["abstract"] = abstract_record.get("text", "")
    
    for core_problem_record in paper_core_problems:
        paper_id = core_problem_record.get("paper_id")
        if paper_id:
            if paper_id not in paper_data_map:
                paper_data_map[paper_id] = {}
            paper_data_map[paper_id]["core_problem"] = core_problem_record.get("text", "")
    
    # 只保留同时有abstract和core_problem的paper
    valid_papers = {
        pid: content for pid, content in paper_data_map.items()
        if "abstract" in content and "core_problem" in content
    }
    
    print(f"\n有效Paper数量: {len(valid_papers)}")
    print(f"Solution数量: {len(solutions)}")
    
    # 直接从抽样数据中提取embeddings（数据已包含vector）
    print(f"\n正在从抽样数据中提取embeddings...")
    paper_embeddings = {}
    solution_embeddings = {}
    
    # 从paper_abstracts中提取embeddings
    for abstract_record in paper_abstracts:
        paper_id = abstract_record.get("paper_id")
        if paper_id and paper_id in valid_papers:
            if paper_id not in paper_embeddings:
                paper_embeddings[paper_id] = {}
            paper_embeddings[paper_id]["abstract_vec"] = abstract_record.get("vector")
    
    # 从paper_core_problems中提取embeddings
    for core_problem_record in paper_core_problems:
        paper_id = core_problem_record.get("paper_id")
        if paper_id and paper_id in valid_papers and paper_id in paper_embeddings:
            paper_embeddings[paper_id]["core_problem_vec"] = core_problem_record.get("vector")
    
    # 从solutions中提取embeddings
    for solution in solutions:
        solution_paper_id = solution.get("paper_id")
        solution_text = solution.get("text", "")
        if solution_paper_id:
            solution_embeddings[solution_paper_id] = {
                "vector": solution.get("vector"),
                "text": solution_text
            }
    
    print(f"  ✅ 获取到 {len(paper_embeddings)} 个paper的embeddings (目标: {len(valid_papers)})")
    print(f"  ✅ 获取到 {len(solution_embeddings)} 个solution的embeddings (目标: {len(solutions)})")
    
    # 计算相似度并初筛
    print(f"\n正在计算相似度并初筛...")
    candidate_pairs = []
    
    total_combinations = len(valid_papers) * len(solutions)
    processed = 0
    
    for paper_id, paper_content in valid_papers.items():
        if paper_id not in paper_embeddings:
            continue
        
        abstract_vec = paper_embeddings[paper_id].get("abstract_vec")
        core_problem_vec = paper_embeddings[paper_id].get("core_problem_vec")
        
        if abstract_vec is None or core_problem_vec is None:
            continue
        
        for solution_paper_id, solution_data in solution_embeddings.items():
            processed += 1
            if processed % 10000 == 0:
                print(f"\r  进度: {processed}/{total_combinations}", end="", flush=True)
            
            # 确保是跨论文配对
            if solution_paper_id == paper_id:
                continue
            
            solution_vec = solution_data["vector"]
            if solution_vec is None:
                continue
            
            # 计算加权相似度
            sim_abstract = cosine_similarity(abstract_vec, solution_vec)
            sim_core_problem = cosine_similarity(core_problem_vec, solution_vec)
            
            weighted_score = (
                sim_abstract * weights["abstract"] + 
                sim_core_problem * weights["core_problem"]
            )
            
            # 初筛：只保留高相似度的配对
            if weighted_score >= similarity_threshold:
                candidate_pairs.append({
                    "paper_a_id": paper_id,
                    "paper_a_abstract": paper_content["abstract"],
                    "paper_a_core_problem": paper_content["core_problem"],
                    "paper_a_combined": f"Abstract: {paper_content['abstract']}\n\nCore Problem: {paper_content['core_problem']}",
                    "paper_b_id": solution_paper_id,
                    "solution_text": solution_data["text"],
                    "similarity_score": weighted_score,
                    "sim_abstract": sim_abstract,
                    "sim_core_problem": sim_core_problem,
                })
    
    print(f"\n\n  ✅ 初筛完成，获得 {len(candidate_pairs)} 个高相似度配对")
    
    # 按相似度排序，保留top candidate_pool_size
    candidate_pairs.sort(key=lambda x: x["similarity_score"], reverse=True)
    candidate_pairs = candidate_pairs[:candidate_pool_size]
    
    print(f"  - 保留前 {len(candidate_pairs)} 个最高相似度的配对")
    
    if len(candidate_pairs) < num_pairs:
        print(f"  ⚠️ 警告: 候选池数量({len(candidate_pairs)}) < 需要数量({num_pairs})")
        print(f"  建议: 降低相似度阈值或增加抽样数量")
        return candidate_pairs
    
    # 从候选池中随机抽样
    selected_pairs = random.sample(candidate_pairs, num_pairs)
    
    print(f"  ✅ 从候选池中随机抽样 {len(selected_pairs)} 条配对")
    print(f"  - 相似度范围: [{min(p['similarity_score'] for p in selected_pairs):.4f}, {max(p['similarity_score'] for p in selected_pairs):.4f}]")
    
    return selected_pairs

def generate_cross_paper_pairs(
    paper_abstracts: List[Dict],
    paper_core_problems: List[Dict],
    solutions: List[Dict],
    num_pairs: int,
    seed: int = 42
) -> List[Dict]:
    """
    生成跨论文的配对数据（优化版：从抽样数据中按需生成）
    
    Args:
        paper_abstracts: Paper的abstract数据列表（已抽样）
        paper_core_problems: Paper的core_problem数据列表（已抽样）
        solutions: Solution数据列表（已抽样）
        num_pairs: 需要生成的配对数量
        seed: 随机种子
    
    Returns:
        配对数据列表
    """
    random.seed(seed)
    
    # 构建paper_id到abstract和core_problem的映射
    paper_content_map = {}
    
    for abstract_record in paper_abstracts:
        paper_id = abstract_record.get("paper_id")
        if paper_id:
            if paper_id not in paper_content_map:
                paper_content_map[paper_id] = {}
            paper_content_map[paper_id]["abstract"] = abstract_record.get("text", "")
    
    for core_problem_record in paper_core_problems:
        paper_id = core_problem_record.get("paper_id")
        if paper_id:
            if paper_id not in paper_content_map:
                paper_content_map[paper_id] = {}
            paper_content_map[paper_id]["core_problem"] = core_problem_record.get("text", "")
    
    # 只保留同时有abstract和core_problem的paper
    valid_papers = {
        pid: content for pid, content in paper_content_map.items()
        if "abstract" in content and "core_problem" in content
    }
    
    # 转为列表便于随机索引
    valid_paper_ids = list(valid_papers.keys())
    
    print(f"有效Paper数量: {len(valid_paper_ids)}")
    print(f"Solution数量: {len(solutions)}")
    
    if len(valid_paper_ids) == 0 or len(solutions) == 0:
        print("❌ 错误: 没有有效的paper或solution数据")
        return []
    
    # 按需随机生成配对
    selected_pairs = []
    used_pairs = set()  # 记录已使用的(paper_id, solution_paper_id)组合，避免重复
    
    print(f"开始生成 {num_pairs} 条配对...")
    attempts = 0
    max_attempts = num_pairs * 20  # 防止无限循环
    
    while len(selected_pairs) < num_pairs and attempts < max_attempts:
        attempts += 1
        
        # 随机选择一个paper和一个solution
        paper_id = random.choice(valid_paper_ids)
        solution = random.choice(solutions)
        solution_paper_id = solution.get("paper_id")
        
        # 确保是跨论文配对且未使用过
        pair_key = (paper_id, solution_paper_id)
        if solution_paper_id and solution_paper_id != paper_id and pair_key not in used_pairs:
            paper_content = valid_papers[paper_id]
            pair = {
                "paper_a_id": paper_id,
                "paper_a_abstract": paper_content["abstract"],
                "paper_a_core_problem": paper_content["core_problem"],
                "paper_a_combined": f"Abstract: {paper_content['abstract']}\n\nCore Problem: {paper_content['core_problem']}",
                "paper_b_id": solution_paper_id,
                "solution_text": solution.get("text", ""),
            }
            selected_pairs.append(pair)
            used_pairs.add(pair_key)
            
            # 每生成100条打印一次进度
            if len(selected_pairs) % 100 == 0:
                print(f"  已生成: {len(selected_pairs)}/{num_pairs}")
    
    if len(selected_pairs) < num_pairs:
        print(f"⚠️ 警告: 仅生成了 {len(selected_pairs)} 条配对（目标 {num_pairs} 条）")
        print(f"   提示: 可能需要增加抽样数量以获得足够的跨论文配对")
    
    print(f"✅ 成功生成 {len(selected_pairs)} 条配对")
    return selected_pairs

# =================================================================================
# 4. LLM三分类
# =================================================================================
def evaluate_relationship_with_llm(
    llm_model, 
    paper_combined_content: str, 
    solution_text: str
) -> Tuple[str, str]:
    """使用LLM判断两个文本片段之间的关系"""
    
    prompt = LLM_EVALUATION_PROMPT.format(
        paper_content=paper_combined_content,
        solution_text=solution_text
    )
    
    try:
        agent = ChatAgent(
            system_message=BaseMessage.make_assistant_message(
                role_name="Evaluator",
                content="You are an AI assistant that follows instructions precisely and returns JSON."
            ),
            model=llm_model
        )
        
        user_msg = BaseMessage.make_user_message(role_name="User", content=prompt)
        agent_response = agent.step(user_msg)
        
        if agent_response and not agent_response.terminated and agent_response.msg:
            response_content = agent_response.msg.content
            
            # 尝试解析JSON
            try:
                result_dict = json.loads(response_content)
            except json.JSONDecodeError:
                # 尝试提取JSON片段
                import re
                json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
                if json_match:
                    result_dict = json.loads(json_match.group(0))
                else:
                    return "NONE", ""
            
            return result_dict.get("relationship_type", "NONE"), result_dict.get("reasoning", "")
        else:
            return "NONE", ""
            
    except Exception as e:
        print(f"  ❌ LLM调用失败: {e}")
        return "NONE", ""

def batch_llm_classification(pairs: List[Dict], llm_model, output_dir: str, checkpoint_interval: int = 50) -> List[Dict]:
    """批量调用LLM进行三分类，支持分批保存和断点续传"""
    print(f"\n开始批量LLM分类，共{len(pairs)}条数据...")
    
    # 创建检查点目录
    checkpoint_dir = os.path.join(output_dir, "checkpoints")
    os.makedirs(checkpoint_dir, exist_ok=True)
    
    # 检查是否有已完成的检查点
    checkpoint_file = os.path.join(checkpoint_dir, "classification_progress.json")
    start_idx = 0
    
    if os.path.exists(checkpoint_file):
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            checkpoint_data = json.load(f)
            checkpoint_count = checkpoint_data.get("completed_count", 0)
            
            # 检查检查点是否与当前任务匹配
            if checkpoint_count > len(pairs):
                print(f"  ⚠️ 检查点数据不匹配（检查点:{checkpoint_count}条, 当前:{len(pairs)}条）")
                print(f"  清理旧检查点，从头开始...")
                os.remove(checkpoint_file)
                start_idx = 0
            elif checkpoint_count == 0 or len(pairs) == 0:
                print(f"  检查点为空或当前无数据，从头开始...")
                start_idx = 0
            else:
                start_idx = checkpoint_count
                print(f"  发现检查点，从第 {start_idx + 1} 条继续...")
                # 恢复已分类的数据
                for i in range(min(start_idx, len(pairs))):
                    if i < len(checkpoint_data.get("pairs", [])):
                        pairs[i]["llm_classification"] = checkpoint_data["pairs"][i]["llm_classification"]
                        pairs[i]["llm_reasoning"] = checkpoint_data["pairs"][i]["llm_reasoning"]
    
    for i in range(start_idx, len(pairs)):
        print(f"\r进度: {i + 1}/{len(pairs)}", end="", flush=True)
        
        relationship_type, reasoning = evaluate_relationship_with_llm(
            llm_model=llm_model,
            paper_combined_content=pairs[i]["paper_a_combined"],
            solution_text=pairs[i]["solution_text"]
        )
        
        pairs[i]["llm_classification"] = relationship_type
        pairs[i]["llm_reasoning"] = reasoning
        
        
        
        # 每checkpoint_interval条保存一次检查点
        if (i + 1) % checkpoint_interval == 0 or (i + 1) == len(pairs):
            checkpoint_data = {
                "completed_count": i + 1,
                "total_count": len(pairs),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "pairs": pairs[:i + 1]
            }
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
            print(f"\n  ✅ 检查点已保存: {i + 1}/{len(pairs)} 条")
    
    print("\n✅ LLM分类完成")
    # 清理检查点文件
    if os.path.exists(checkpoint_file):
        os.remove(checkpoint_file)
    
    return pairs

# =================================================================================
# 5. 数据分配策略
# =================================================================================
def allocate_annotation_tasks(classified_pairs: List[Dict]) -> Dict:
    """
    分配标注任务
    
    返回结构:
    {
        "common": [50条共同校验的数据],
        "博士生A": {
            "precise": [100条精确校验],
            "rough": [400条大致校验]
        },
        "博士生B": {...},
        "博士生C": {...}
    }
    """
    random.seed(CONFIG["SEED"])
    random.shuffle(classified_pairs)
    
    allocation = {
        "common": [],
        "博士生A": {"precise": [], "rough": []},
        "博士生B": {"precise": [], "rough": []},
        "博士生C": {"precise": [], "rough": []},
    }
    
    # 1. 分配50条共同校验数据
    allocation["common"] = classified_pairs[:CONFIG["COMMON_SAMPLES"]]
    
    # 2. 剩余数据分配给三位博士生
    remaining_pairs = classified_pairs[CONFIG["COMMON_SAMPLES"]:]
    
    # 每人500条独立数据
    pairs_per_person = CONFIG["SAMPLES_PER_PERSON"]
    
    for i, annotator in enumerate(CONFIG["ANNOTATORS"]):
        start_idx = i * pairs_per_person
        end_idx = start_idx + pairs_per_person
        person_pairs = remaining_pairs[start_idx:end_idx]
        
        # 前100条为精确校验，后400条为大致校验
        allocation[annotator]["precise"] = person_pairs[:CONFIG["PRECISE_SAMPLES_PER_PERSON"]]
        allocation[annotator]["rough"] = person_pairs[CONFIG["PRECISE_SAMPLES_PER_PERSON"]:]
    
    return allocation

# =================================================================================
# 6. 生成标注文件（为每个博士生创建独立目录）
# =================================================================================
def generate_annotation_files(allocation: Dict, output_dir: str):
    """生成标注文件，为每个博士生创建独立目录，包含共同校验和独立校验数据"""
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. 生成总览文件（放在根目录）
    overview = {
        "metadata": {
            "生成时间": timestamp,
            "总样本数": CONFIG["TOTAL_SAMPLES"],
            "共同校验样本数": CONFIG["COMMON_SAMPLES"],
            "每人独立校验样本数": CONFIG["SAMPLES_PER_PERSON"],
            "标注员": CONFIG["ANNOTATORS"],
        },
        "数据分配说明": {
            "共同校验": f"{CONFIG['COMMON_SAMPLES']}条数据，三位博士生都需要标注",
            "独立校验": f"每人{CONFIG['SAMPLES_PER_PERSON']}条独立数据",
            "精确校验": f"每人{CONFIG['PRECISE_SAMPLES_PER_PERSON']}条，需仔细分析",
            "大致校验": f"每人{CONFIG['ROUGH_SAMPLES_PER_PERSON']}条，快速判断即可",
        },
        "标注说明": {
            "关系类型": {
                "INSPIRED": "论文B的解决方案能够启发或解决论文A的问题",
                "RELATED": "两者在领域/方法上相似但无直接启发关系",
                "NONE": "无明显关系"
            },
            "标注格式": "每条数据需填写human_classification字段，可选值为INSPIRED/RELATED/NONE",
            "目录结构": "每位博士生有独立目录，包含50条共同校验数据和500条独立校验数据"
        }
    }
    
    overview_path = os.path.join(output_dir, f"标注任务总览_{timestamp}.json")
    with open(overview_path, 'w', encoding='utf-8') as f:
        json.dump(overview, f, ensure_ascii=False, indent=2)
    print(f"✅ 总览文件已生成: {overview_path}")
    
    # 2. 为每位博士生创建独立目录和文件
    for annotator in CONFIG["ANNOTATORS"]:
        # 创建博士生的独立目录
        annotator_dir = os.path.join(output_dir, annotator)
        os.makedirs(annotator_dir, exist_ok=True)
        
        # 2.1 生成该博士生的共同校验文件（50条）
        common_data = {
            "metadata": {
                "标注员": annotator,
                "任务类型": "共同校验",
                "样本数": len(allocation["common"]),
                "说明": "这50条数据需要三位博士生都进行标注，用于评估标注一致性"
            },
            "samples": []
        }
        
        for idx, pair in enumerate(allocation["common"], 1):
            sample = {
                "sample_id": f"COMMON_{idx:03d}",
                "paper_a_id": pair["paper_a_id"],
                "paper_a_abstract": pair["paper_a_abstract"],
                "paper_a_core_problem": pair["paper_a_core_problem"],
                "paper_b_id": pair["paper_b_id"],
                "solution_text": pair["solution_text"],
                "llm_classification": pair["llm_classification"],
                "llm_reasoning": pair["llm_reasoning"],
                "human_classification": "",
                "notes": ""
            }
            common_data["samples"].append(sample)
        
        common_path = os.path.join(annotator_dir, f"共同校验数据_{timestamp}.json")
        with open(common_path, 'w', encoding='utf-8') as f:
            json.dump(common_data, f, ensure_ascii=False, indent=2)
        print(f"✅ {annotator}/共同校验数据 已生成 (50条)")
        
        # 2.2 生成该博士生的独立校验文件（500条）
        independent_data = {
            "metadata": {
                "标注员": annotator,
                "任务类型": "独立校验",
                "总样本数": CONFIG["SAMPLES_PER_PERSON"],
                "精确校验数": CONFIG["PRECISE_SAMPLES_PER_PERSON"],
                "大致校验数": CONFIG["ROUGH_SAMPLES_PER_PERSON"],
                "说明": "前100条为精确校验（需仔细分析），后400条为大致校验（快速判断即可）"
            },
            "samples": []
        }
        
        # 精确校验数据（100条）
        for idx, pair in enumerate(allocation[annotator]["precise"], 1):
            sample = {
                "sample_id": f"{annotator}_PRECISE_{idx:03d}",
                "validation_type": "精确校验",
                "paper_a_id": pair["paper_a_id"],
                "paper_a_abstract": pair["paper_a_abstract"],
                "paper_a_core_problem": pair["paper_a_core_problem"],
                "paper_b_id": pair["paper_b_id"],
                "solution_text": pair["solution_text"],
                "llm_classification": pair["llm_classification"],
                "llm_reasoning": pair["llm_reasoning"],
                "human_classification": "",
                "notes": ""
            }
            independent_data["samples"].append(sample)
        
        # 大致校验数据（400条）
        for idx, pair in enumerate(allocation[annotator]["rough"], 1):
            sample = {
                "sample_id": f"{annotator}_ROUGH_{idx:03d}",
                "validation_type": "大致校验",
                "paper_a_id": pair["paper_a_id"],
                "paper_a_abstract": pair["paper_a_abstract"],
                "paper_a_core_problem": pair["paper_a_core_problem"],
                "paper_b_id": pair["paper_b_id"],
                "solution_text": pair["solution_text"],
                "llm_classification": pair["llm_classification"],
                "llm_reasoning": pair["llm_reasoning"],
                "human_classification": "",
                "notes": ""
            }
            independent_data["samples"].append(sample)
        
        independent_path = os.path.join(annotator_dir, f"独立校验数据_{timestamp}.json")
        with open(independent_path, 'w', encoding='utf-8') as f:
            json.dump(independent_data, f, ensure_ascii=False, indent=2)
        print(f"✅ {annotator}/独立校验数据 已生成 (500条: 100精确 + 400大致)")
    
    print(f"\n✅ 所有标注文件已生成到目录: {output_dir}")
    print(f"\n目录结构:")
    print(f"  {output_dir}/")
    print(f"  ├── 标注任务总览_{timestamp}.json")
    for annotator in CONFIG["ANNOTATORS"]:
        print(f"  ├── {annotator}/")
        print(f"  │   ├── 共同校验数据_{timestamp}.json (50条)")
        print(f"  │   └── 独立校验数据_{timestamp}.json (500条)")

# =================================================================================
# 7. 主流程
# =================================================================================
def main():
    """主流程"""
    print("="*80)
    print("跨论文Paper-Solution关系人工标注数据生成脚本")
    print("="*80)
    
    # 1. 初始化模型
    print("\n【步骤1】初始化模型...")
    llm_model, embedding_model = initialize_models()
    print("✅ 模型初始化完成")
    
    # 2. 加载向量存储
    print("\n【步骤2】加载向量存储...")
    try:
        abstract_storage = load_vector_storage("paper", "abstract", embedding_model)
        core_problem_storage = load_vector_storage("paper", "core_problem", embedding_model)
        solution_storage = load_vector_storage("solution", "solution", embedding_model)
    except Exception as e:
        print(f"❌ 加载向量存储失败: {e}")
        return
    print("✅ 向量存储加载完成")
    
    # 3. 随机抽样数据（确保abstract和core_problem来自同一篇论文）
    print("\n【步骤3】随机抽样数据...")
    # 计算需要抽样的数量：为了生成1550条配对，抽样适量的paper和solution
    paper_sample_size = 100  # 抽样100个paper
    solution_sample_size = 2000  # 抽样2000个solution
    
    # 步骤1: 先从abstract中随机抽样，获取paper_id列表（包含vector）
    print("  步骤3.1: 随机抽样paper（包含embeddings）...")
    sampled_abstracts = extract_random_sample_from_storage(abstract_storage, paper_sample_size, CONFIG["SEED"], include_vector=True)
    
    # 提取这些paper的ID
    sampled_paper_ids = set()
    for abstract in sampled_abstracts:
        paper_id = abstract.get("paper_id")
        if paper_id:
            sampled_paper_ids.add(paper_id)
    
    print(f"  - 获得 {len(sampled_paper_ids)} 个唯一的paper_id")
    
    # 步骤2: 根据这些paper_id，从core_problem存储中提取对应的记录（包含vector）
    print("  步骤3.2: 提取对应的core_problem（包含embeddings）...")
    sampled_core_problems = extract_papers_by_ids(core_problem_storage, sampled_paper_ids)
    
    # 步骤3: 独立抽样solution（来自其他论文，包含vector）
    print("  步骤3.3: 随机抽样solution（包含embeddings）...")
    sampled_solutions = extract_random_sample_from_storage(solution_storage, solution_sample_size, CONFIG["SEED"] + 1, include_vector=True)
    
    print(f"✅ 数据抽样完成: {len(sampled_abstracts)}个abstract, {len(sampled_core_problems)}个core_problem, {len(sampled_solutions)}个solution")
    
    # 验证数据一致性
    abstract_paper_ids = set(a.get("paper_id") for a in sampled_abstracts if a.get("paper_id"))
    core_problem_paper_ids = set(c.get("paper_id") for c in sampled_core_problems if c.get("paper_id"))
    matched_ids = abstract_paper_ids & core_problem_paper_ids
    print(f"  - 验证: {len(matched_ids)} 个paper同时拥有abstract和core_problem")
    
    # 4. 相似度分布统计分析（如果启用自动调优）
    similarity_threshold = CONFIG["SIMILARITY_THRESHOLD"]
    
    if CONFIG["USE_SIMILARITY_FILTER"] and CONFIG["AUTO_TUNE_THRESHOLD"]:
        print("\n【步骤4】相似度分布统计分析...")
        stats_result = analyze_similarity_distribution(
            abstract_storage=abstract_storage,
            core_problem_storage=core_problem_storage,
            solution_storage=solution_storage,
            paper_abstracts=sampled_abstracts,
            paper_core_problems=sampled_core_problems,
            solutions=sampled_solutions,
            sample_size=CONFIG["SAMPLE_SIZE_FOR_STATS"],
            weights=CONFIG["SIMILARITY_WEIGHTS"],
            seed=CONFIG["SEED"]
        )
        
        # 使用推荐的阈值
        similarity_threshold = stats_result["recommended_threshold"]
        print(f"\n✅ 将使用推荐阈值: {similarity_threshold:.4f}")
        
        # 保存统计结果
        stats_file = os.path.join(CONFIG["OUTPUT_DIR"], "similarity_statistics.json")
        os.makedirs(CONFIG["OUTPUT_DIR"], exist_ok=True)
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats_result, f, ensure_ascii=False, indent=2)
        print(f"✅ 统计结果已保存到: {stats_file}")
    
    # 5. 生成配对（使用相似度初筛）
    print("\n【步骤5】生成跨论文配对...")
    
    if CONFIG["USE_SIMILARITY_FILTER"]:
        print("  使用相似度初筛策略")
        print(f"  阈值: {similarity_threshold:.4f}")
        pairs = generate_cross_paper_pairs_with_similarity_filter(
            abstract_storage=abstract_storage,
            core_problem_storage=core_problem_storage,
            solution_storage=solution_storage,
            paper_abstracts=sampled_abstracts,
            paper_core_problems=sampled_core_problems,
            solutions=sampled_solutions,
            num_pairs=CONFIG["TOTAL_SAMPLES"],
            candidate_pool_size=CONFIG["CANDIDATE_POOL_SIZE"],
            similarity_threshold=similarity_threshold,
            weights=CONFIG["SIMILARITY_WEIGHTS"],
            seed=CONFIG["SEED"]
        )
    else:
        print("  使用随机抽样策略")
        pairs = generate_cross_paper_pairs(
            paper_abstracts=sampled_abstracts,
            paper_core_problems=sampled_core_problems,
            solutions=sampled_solutions,
            num_pairs=CONFIG["TOTAL_SAMPLES"],
            seed=CONFIG["SEED"]
        )
    print(f"✅ 配对生成完成: {len(pairs)}条")
    
    # 6. LLM分类（支持分批保存）
    print("\n【步骤6】LLM三分类...")
    classified_pairs = batch_llm_classification(pairs, llm_model, CONFIG["OUTPUT_DIR"], checkpoint_interval=50)
    
    # 统计分类结果
    classification_stats = {}
    for pair in classified_pairs:
        cls = pair["llm_classification"]
        classification_stats[cls] = classification_stats.get(cls, 0) + 1
    print(f"分类统计: {classification_stats}")
    
    # 7. 分配任务
    print("\n【步骤7】分配标注任务...")
    allocation = allocate_annotation_tasks(classified_pairs)
    print("✅ 任务分配完成")
    
    # 8. 生成文件
    print("\n【步骤8】生成标注文件...")
    generate_annotation_files(allocation, CONFIG["OUTPUT_DIR"])
    
    print("\n" + "="*80)
    print("✅ 所有任务完成！")
    print("="*80)

if __name__ == "__main__":
    main()
