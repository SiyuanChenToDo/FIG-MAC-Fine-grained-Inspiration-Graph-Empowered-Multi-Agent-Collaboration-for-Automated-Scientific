import os
import sys
import json
import time
import re
import numpy as np
from itertools import product

from camel.storages import Neo4jGraph
from camel.embeddings import OpenAICompatibleEmbedding
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.configs import QwenConfig
from camel.agents import ChatAgent
from camel.messages import BaseMessage

# =================================================================================
# 1. 环境与数据库配置 (Environment and Database Configuration)
# =================================================================================
# --- 请确保您的环境变量已正确设置 ---
os.environ["OPENAI_COMPATIBILITY_API_KEY"] = "sk-875e0cf57dd34df59d3bcaef4ee47f80"
os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# 关键修复：完全复制 test_graph.py 的工作配置
os.environ["QWEN_API_KEY"] = os.environ["OPENAI_COMPATIBILITY_API_KEY"]
os.environ["QWEN_API_BASE_URL"] = os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"]

# --- Neo4j 数据库连接信息 ---
# 注意：密码已替换为占位符，请使用您自己的真实密码。
n4j = Neo4jGraph(
    url="neo4j+s://b3980610.databases.neo4j.io",
    username="neo4j",
    password="ta_T6_9gzxTfrTiWjRuUhO7Lm6fBbQG8TwxnSqHpoqk",
)

# --- 嵌入模型初始化 ---
embedding_model = OpenAICompatibleEmbedding(
    model_type="text-embedding-v2",
    api_key=os.environ["OPENAI_COMPATIBILITY_API_KEY"],
    url=os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"],
)

# --- 新增: LLM 评估模型初始化 ---
# 使用与 test_graph.py 一致的、经过验证的配置
llm_model = ModelFactory.create(
    model_platform=ModelPlatformType.QWEN,
    model_type=ModelType.COMETAPI_QWEN3_CODER_PLUS_2025_07_22,
    model_config_dict=QwenConfig(temperature=0.1).as_dict(),
    api_key=os.environ["QWEN_API_KEY"],
    url=os.environ["QWEN_API_BASE_URL"],
)

print("✅ 环境和数据库配置完成。")

# =================================================================================
# 2. 核心参数配置 (Core Parameter Configuration)
# =================================================================================
CONFIG = {
    "WEIGHTS": {
        "abstract": 0.4,
        "core_problem": 0.6
    },
    "SIMILARITY_THRESHOLD": 0.7,
    # --- 更新: 定义新的关系类型 ---
    "RELATIONSHIP_TYPES": {
        "INSPIRED": "POSSIBLY_INSPIRED", # A的solution能启发/解决B的问题
        "RELATED": "POSSIBLY_RELATED"   # A的solution/领域与B的问题/领域相似
    },
    # --- 缓存路径和维度配置 ---
    # 文件将保存为 embedding_cache.json 和 embedding_cache.npy
    "EMBEDDING_CACHE_BASE_PATH": "embedding_cache", 
    "EMBEDDING_MODEL_DIM": 1536, # DashScope text-embedding-v2 的维度通常为 1536
    
    # --- 新增: LLM评估相关的配置 ---
    "LLM_EVALUATION_PROMPT": """
你是一个专业的科研助理，任务是分析两篇不同论文的核心内容，并判断它们之间的深层联系。

**背景信息:**
- **论文 A**: 提供了以下解决方案（Solution）。
- **论文 B**: 正在研究其核心问题（Core Problem）和摘要（Abstract）中描述的内容。

**你的任务:**
请基于以下内容，判断论文 A 的解决方案是否能够对论文 B 的研究产生启发或存在关联。

---
**论文 A 的解决方案 (Solution from Paper A):**
{solution_text}
---
**论文 B 的核心问题 (Core Problem from Paper B):**
{paper_core_problem}
---
**论文 B 的摘要 (Abstract from Paper B):**
{paper_abstract}
---

**判断标准:**
1.  **启发关系 (INSPIRED)**: 如果论文 A 的解决方案可以直接或间接地应用于解决论文 B 的核心问题，或者为其提供一种新的思路、方法或技术路径，请判断为“启发关系”。
2.  **相关关系 (RELATED)**: 如果论文 A 的解决方案所涉及的研究领域、技术、或问题与论文 B 的核心问题或摘要内容高度相似，但不能直接用于解决问题，而是属于同一范畴或相关领域，请判断为“相关关系”。
3.  **无明确关系 (NONE)**: 如果两者之间没有明显的启发或相关性，请判断为“无明确关系”。

**输出格式:**
请严格按照以下 JSON 格式返回你的判断，不要包含任何额外的解释或代码块标记。
{{
  "relationship_type": "INSPIRED" | "RELATED" | "NONE",
  "reasoning": "请在这里用一句话简要解释你的判断理由。"
}}
"""
}
print(f"✅ 核心参数配置完成，权重: {CONFIG['WEIGHTS']}, 阈值: {CONFIG['SIMILARITY_THRESHOLD']}")

# =================================================================================
# 3. 辅助及缓存函数 (Helper and Caching Functions)
# =================================================================================
def cosine_similarity(vec1, vec2):
    """计算两个向量之间的余弦相似度。"""
    dot_product = np.dot(vec1, vec2)
    norm_vec1 = np.linalg.norm(vec1)
    norm_vec2 = np.linalg.norm(vec2)
    if norm_vec1 == 0 or norm_vec2 == 0:
        return 0
    return dot_product / (norm_vec1 * norm_vec2)

def embed_text_batch(texts_to_embed):
    """分批处理文本并生成嵌入。"""
    batch_size = 25
    all_embeddings = []
    for i in range(0, len(texts_to_embed), batch_size):
        batch_texts = texts_to_embed[i:i + batch_size]
        print(f"  > 正在为 {len(batch_texts)} 个文本调用 API... (批次 {i//batch_size + 1})")
        try:
            batch_embeddings = embedding_model.embed_list(objs=batch_texts)
            all_embeddings.extend(batch_embeddings)
        except Exception as e:
            print(f"  ❌ 批次处理失败: {e}")
            # 确保即使失败，也能保持列表长度一致，使用 None 占位
            all_embeddings.extend([None] * len(batch_texts))
    return all_embeddings

def load_embedding_cache(base_path, dim):
    """从文件加载嵌入缓存 (JSON for keys, NumPy for vectors)。"""
    json_path = base_path + ".json"
    npy_path = base_path + ".npy"
    
    cache = {}
    
    if os.path.exists(json_path) and os.path.exists(npy_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # 1. Load keys (text) and indices from JSON
            text_to_index = metadata.get('text_to_index', {})
            
            # 2. Load vectors array from .npy file
            vectors_array = np.load(npy_path)
            
            # 检查文件完整性
            if vectors_array.shape[0] != len(text_to_index) or vectors_array.shape[1] != dim:
                print(f"⚠️ 缓存文件 '{npy_path}' 结构不一致 ({vectors_array.shape})，忽略缓存。")
                return {}

            # 3. Reconstruct cache (text: vector list)
            for text, index in text_to_index.items():
                # 存储为 list 以便在缓存字典中保持一致性
                cache[text] = vectors_array[index].tolist() 
            
            print(f"✅ 成功从 '{base_path}.json/.npy' 加载 {len(cache)} 条嵌入缓存。")
            return cache
        
        except Exception as e:
            print(f"❌ 加载缓存文件失败: {e}。返回空缓存。")
            return {}
    
    print(f"💡 未找到完整缓存文件 '{base_path}.json/.npy'，返回空缓存。")
    return {}

def save_embedding_cache(base_path, cache):
    """将嵌入缓存保存到文件 (JSON for keys, NumPy for vectors)。"""
    json_path = base_path + ".json"
    npy_path = base_path + ".npy"
    
    if not cache:
        print("⚠️ 缓存为空，跳过保存。")
        return

    # 1. Prepare metadata and vectors array
    text_to_index = {}
    vectors_list = []
    
    for i, (text, vector_list) in enumerate(cache.items()):
        text_to_index[text] = i
        vectors_list.append(vector_list)
        
    vectors_array = np.array(vectors_list)
    metadata = {
        'text_to_index': text_to_index,
        'count': len(cache),
        'timestamp': int(time.time()),
        'vector_dim': vectors_array.shape[1] if vectors_array.size > 0 else 0
    }
    
    try:
        # 2. Save vectors using NumPy binary format (速度更快)
        np.save(npy_path, vectors_array)

        # 3. Save metadata using JSON
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
            
        print(f"✅ 嵌入缓存已更新并保存到 '{base_path}.json/.npy'。")
        
    except Exception as e:
        print(f"❌ 写入缓存文件失败: {e}")


def get_embeddings_with_caching(texts, cache):
    """
    为文本列表获取嵌入，优先使用缓存。
    返回与输入文本顺序一致的嵌入列表（numpy arrays）和更新后的缓存。
    """
    texts_to_embed_map = {} # 使用 map 保证唯一性
    for i, text in enumerate(texts):
        if text not in cache:
            texts_to_embed_map[text] = None
            
    if texts_to_embed_map:
        print(f"  > 缓存未命中 {len(texts_to_embed_map)} 个唯一文本，准备生成新嵌入...")
        unique_texts_to_embed = list(texts_to_embed_map.keys())
        new_embeddings = embed_text_batch(unique_texts_to_embed)
        
        for text, embedding in zip(unique_texts_to_embed, new_embeddings):
            if embedding is not None:
                cache[text] = np.array(embedding).tolist() # 转为 list 以便 JSON 序列化
    else:
        print("  > 缓存命中所有文本！无需 API 调用。")

    # 从缓存中构建与原始输入顺序一致的结果列表
    final_embeddings = [np.array(cache.get(text)) if cache.get(text) is not None else None for text in texts]
    return final_embeddings, cache

# --- 新增: LLM 评估函数 ---
def evaluate_relationship_with_llm(llm_model, solution_text, paper_abstract, paper_core_problem):
    """使用 ChatAgent 判断两个文本片段之间的关系 (模仿 test_graph.py 的工作模式)。"""

    prompt = CONFIG["LLM_EVALUATION_PROMPT"].format(
        solution_text=solution_text,
        paper_abstract=paper_abstract,
        paper_core_problem=paper_core_problem
    )

    response_content = "" # 初始化在这里，以确保在异常处理中可用
    try:
        # 1. 创建一个 ChatAgent，模仿 test_graph.py 的调用方式
        agent = ChatAgent(
            system_message=BaseMessage.make_assistant_message(
                role_name="Evaluator",
                content="You are an AI assistant that follows instructions precisely and returns JSON."
            ),
            model=llm_model
        )

        # 2. 创建用户消息
        user_msg = BaseMessage.make_user_message(role_name="User", content=prompt)

        # 3. 使用 agent.step() 获取响应
        print("DEBUG_LLM: Calling ChatAgent.step() with prompt...")
        agent_response = agent.step(user_msg)
        print(f"DEBUG_LLM: Raw response from agent.step(): {agent_response!r}")

        # 4. 从响应中提取内容
        if agent_response and not agent_response.terminated and agent_response.msg:
            response_content = agent_response.msg.content
        else:
            print(f"  - ⚠️ Agent 响应终止或为空。响应: {agent_response!r}")
            return "NONE", ""

        print(f"DEBUG_LLM: Extracted response content: {response_content!r}")

        result_dict = {} # 初始化为一个空字典

        # 尝试直接解析整个响应内容为JSON
        try:
            parsed_json = json.loads(response_content)
            if isinstance(parsed_json, dict): # 确认解析结果是一个字典
                result_dict = parsed_json
            else:
                raise json.JSONDecodeError("Parsed JSON is not a dictionary", response_content, 0)
        except json.JSONDecodeError:
            json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                try:
                    parsed_json = json.loads(json_str)
                    if isinstance(parsed_json, dict):
                        result_dict = parsed_json
                    else:
                        print(f"  - ⚠️ 提取的JSON片段解析后不是字典。片段: {json_str!r}, 结果: {parsed_json!r}")
                except json.JSONDecodeError:
                    print(f"  - ⚠️ 提取的JSON片段无法解析。片段: {json_str!r}")
            else:
                print(f"  - ⚠️ LLM响应中未找到有效的JSON格式。响应内容: {response_content!r}")
        
        if result_dict:
            return result_dict.get("relationship_type", "NONE"), result_dict.get("reasoning", "")
        else:
            print(f"  - ⚠️ 最终LLM解析结果不是有效的JSON对象。原始响应: {response_content!r}")
            return "NONE", ""

    except Exception as e:
        # 捕获其他未知错误，并打印详细信息
        print(f"  - ❌ 调用LLM评估时出错: {e}. 原始响应: {response_content!r}")
        return "NONE", ""

print("✅ 辅助及缓存函数已定义。")

# =================================================================================
# 4. 主逻辑 (Main Logic)
# =================================================================================
def main():
    """执行节点获取、嵌入、加权比较和链接创建的整个流程。"""
    
    # --- 新增: 加载嵌入缓存 (使用新的 base path 和 dim) ---
    embedding_cache = load_embedding_cache(CONFIG["EMBEDDING_CACHE_BASE_PATH"], CONFIG["EMBEDDING_MODEL_DIM"])

    # --- 步骤 1: 获取 Paper 节点和 Solution 节点 (关键: 添加 file_id) ---
    print("\n🚀 步骤 1: 开始从 Neo4j 获取 Paper 和 Solution 节点...")
    try:
        # **更新点 1: Paper 查询中添加 p.file_id**
        paper_query = """
        MATCH (p:paper)
        WHERE p.abstract IS NOT NULL AND p.core_problem IS NOT NULL AND p.file_id IS NOT NULL
        RETURN elementId(p) AS node_id, p.abstract AS abstract, p.core_problem AS core_problem, p.file_id AS file_id
        """
        paper_nodes = n4j.query(query=paper_query)
        print(f"  - 成功获取 {len(paper_nodes)} 个 Paper 节点。")

        # **更新点 2: Solution 查询中添加 s.file_id**
        # 假设 Solution 节点也直接有 file_id 属性，与 Paper 节点一致。
        solution_query = """
        MATCH (s)
        WHERE (s:solution_1 OR s:solution_2 OR s:solution_3 OR s:solution_4) AND s.file_id IS NOT NULL
        WITH s, labels(s)[0] AS label
        WITH s, label, s.file_id AS file_id,
             CASE label
               WHEN 'solution_1' THEN s.solution_1
               WHEN 'solution_2' THEN s.solution_2
               WHEN 'solution_3' THEN s.solution_3
               WHEN 'solution_4' THEN s.solution_4
               ELSE null
             END AS text_content
        WHERE text_content IS NOT NULL
        RETURN elementId(s) AS node_id, label, text_content AS text, file_id
        """
        solution_nodes = n4j.query(query=solution_query)
        print(f"  - 成功获取 {len(solution_nodes)} 个 Solution 节点。")
        
        if not paper_nodes or not solution_nodes:
            print("⚠️ 缺少 Paper 或 Solution 节点，无法继续。请检查数据库。")
            return
            
    except Exception as e:
        print(f"❌ Neo4j 查询失败: {e}")
        return

    # --- 步骤 2: 使用缓存机制为节点属性生成或获取向量嵌入 ---
    print("\n🚀 步骤 2: 开始为节点属性生成或获取向量嵌入...")
    
    all_paper_texts = [text for p in paper_nodes for text in (p['abstract'], p['core_problem'])]
    all_solution_texts = [s['text'] for s in solution_nodes]
    
    # 一次性处理所有文本
    all_paper_embeddings, embedding_cache = get_embeddings_with_caching(all_paper_texts, embedding_cache)
    all_solution_embeddings, embedding_cache = get_embeddings_with_caching(all_solution_texts, embedding_cache)

    # 将嵌入向量分配回对应的节点
    for i, p_node in enumerate(paper_nodes):
        p_node['vectors'] = {
            "abstract": all_paper_embeddings[i*2],
            "core_problem": all_paper_embeddings[i*2 + 1]
        }
    for i, s_node in enumerate(solution_nodes):
        s_node['vector'] = all_solution_embeddings[i]
        
    print("✅ 向量嵌入已全部分配给对应节点。")

    # --- 步骤 3: 计算加权相似度并创建链接 (关键: 过滤 file_id) ---
    print("\n🚀 步骤 3: 开始计算加权相似度并创建链接...")
    
    link_creation_count = 0
    
    for paper, solution in product(paper_nodes, solution_nodes):
        
        # **关键过滤逻辑: 确保 Paper 和 Solution 来自不同的论文**
        if paper['file_id'] == solution['file_id']:
            continue 

        if paper['vectors']['abstract'] is None or paper['vectors']['core_problem'] is None or solution['vector'] is None:
            continue

        sim_abstract = cosine_similarity(paper['vectors']['abstract'], solution['vector'])
        sim_core_problem = cosine_similarity(paper['vectors']['core_problem'], solution['vector'])
        
        weighted_score = (sim_abstract * CONFIG['WEIGHTS']['abstract'] + 
                          sim_core_problem * CONFIG['WEIGHTS']['core_problem'])
        
        # --- 阶段 1: 基于相似度进行初筛 ---
        if weighted_score >= CONFIG['SIMILARITY_THRESHOLD']:
            print(f"\n  ✨ 初筛通过 (总分: {weighted_score:.4f})，准备进行LLM深度评估...")
            print(f"     - 论文 A (Solution): {solution['file_id']} (Node: {solution['node_id']})")
            print(f"     - 论文 B (Paper): {paper['file_id']} (Node: {paper['node_id']})")
            
            # --- 阶段 2: 调用 LLM 进行精细化判断 ---
            relationship_type, reasoning = evaluate_relationship_with_llm(
                llm_model=llm_model,
                solution_text=solution['text'],
                paper_abstract=paper['abstract'],
                paper_core_problem=paper['core_problem']
            )
            
            if relationship_type in CONFIG["RELATIONSHIP_TYPES"]:
                link_creation_count += 1
                rel_type_str = CONFIG["RELATIONSHIP_TYPES"][relationship_type]
                print(f"  - 🧠 LLM 判断结果: {relationship_type} ({rel_type_str})")
                print(f"  - 💬 LLM 理由: {reasoning}")

                # 使用 MERGE 语句在 Neo4j 中创建关系
                merge_query = f"""
                MATCH (p:paper), (s)
                WHERE elementId(p) = '{paper['node_id']}' AND elementId(s) = '{solution['node_id']}'
                MERGE (p)-[r:{rel_type_str}]->(s)
                SET r.weightedScore = {weighted_score:.4f},
                    r.abstractSimilarity = {sim_abstract:.4f},
                    r.coreProblemSimilarity = {sim_core_problem:.4f},
                    r.llmReasoning = "{reasoning.replace('"', "'")}",
                    r.llmJudgement = "{relationship_type}",
                    r.createdAt = timestamp()
                """
                try:
                    n4j.query(query=merge_query)
                    print(f"     ✅ 成功在图中创建 '{rel_type_str}' 关系。")
                except Exception as e:
                    print(f"     ❌ 创建关系失败: {e}")
            else:
                print(f"  - ⏭️ LLM 判断为无明确关系，跳过链接创建。")

    if link_creation_count == 0:
        print("\n✅ 完成计算，未发现符合条件并经LLM确认的跨论文 Paper-Solution 对。")
    else:
        print(f"\n🎉 流程结束！总共创建了 {link_creation_count} 条经LLM确认的新的跨论文关系。")
        
    # --- 新增: 保存更新后的缓存 ---
    save_embedding_cache(CONFIG["EMBEDDING_CACHE_BASE_PATH"], embedding_cache)

# =================================================================================
# 5. 脚本入口 (Script Entrypoint)
# =================================================================================
if __name__ == "__main__":
    print("=====================================================")
    print("=== Neo4j Paper-Solution 智能链接脚本 (LLM增强版) ===")
    print("=====================================================")
    main()
