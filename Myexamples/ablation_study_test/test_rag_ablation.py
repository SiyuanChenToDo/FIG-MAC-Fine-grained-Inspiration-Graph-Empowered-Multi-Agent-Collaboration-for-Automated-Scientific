#图谱的检索存在冗余
#为muti-agent系统提供信息
#可以评估rag指标，做消融实验，证明数据集的价值
import sys
print(f"Python Version: {sys.version}")
print(f"Sys Path: {sys.path}")

from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.configs import QwenConfig
from camel.loaders import UnstructuredIO
from camel.storages import Neo4jGraph
from camel.retrievers import AutoRetriever
from camel.embeddings import OpenAICompatibleEmbedding
from camel.types import StorageType
from camel.agents import ChatAgent, KnowledgeGraphAgent
from camel.messages import BaseMessage
from camel.storages import FaissStorage, VectorRecord, VectorDBQuery

# 导入优化版检索模块
sys.path.insert(0, '/root/autodl-tmp/Myexamples/ablation_study_test')
from kg_retrieval_optimized_v2 import OptimizedKGRetriever, KGRetrievalResult

import json
import os

import logging

# Suppress verbose Neo4j warnings
logging.getLogger("neo4j").setLevel(logging.ERROR)


# # Prompt for the API key securely
# mistral_api_key = "amPLA3bl3H42UZSZaW9vL1qBEFo8P3KK"
# os.environ["MISTRAL_API_KEY"] = mistral_api_key

os.environ["OPENAI_COMPATIBILITY_API_KEY"] = "sk-c1a6b588f7d543adb0412c5bc61bdd7b"
os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"


os.environ["QWEN_API_KEY"] = os.environ["OPENAI_COMPATIBILITY_API_KEY"]
os.environ["QWEN_API_BASE_URL"] = os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"]


# Set Neo4j instance
n4j = Neo4jGraph(
    url="bolt://localhost:7687",
    username="neo4j",
    password="neo4j123",
)


# Set up model
qwen_model = ModelFactory.create(
    model_platform=ModelPlatformType.QWEN,
    model_type=ModelType.COMETAPI_QWEN3_CODER_PLUS_2025_07_22, # Assuming Qwen3 maps to QWEN_TURBO, adjust if needed
    model_config_dict=QwenConfig(temperature=0.2).as_dict(),
    api_key=os.environ["QWEN_API_KEY"],
    url=os.environ["QWEN_API_BASE_URL"],
)


# Set instance
uio = UnstructuredIO()
kg_agent = KnowledgeGraphAgent(model=qwen_model)

# 初始化知识图谱检索器
print("--- Initializing KG Retriever ---")
optimized_kg_retriever = OptimizedKGRetriever()
print("✅ KG Retriever initialized\n")

# Set retriever
camel_retriever = AutoRetriever(
    vector_storage_local_path="local_data/embedding_storage",
    storage_type=StorageType.QDRANT,
    embedding_model=OpenAICompatibleEmbedding(
        model_type="text-embedding-v2", # 使用阿里云DashScope支持的embedding模型
        api_key=os.environ["OPENAI_COMPATIBILITY_API_KEY"],
        url=os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"],
    ),
)

# Set one user query
query="How can contrastive learning be used to enhance the discriminability of dialogue act embeddings in a self-supervised manner?"

# ================== Vector Search Logic Start ==================

# 1. Setup paths and parameters
JSON_FILE_PATH = 'D:\Backup\Downloads\camel-master2\camel-master\Myexamples\data//final_data//final_custom_kg_papers.json'
BASE_VDB_PATH = 'Myexamples/vdb/camel_faiss_storage'
node_attributes_to_vectorize = {
    "paper": [
        "abstract", "core_problem", "related_work",
        "preliminary_innovation_analysis", 
        "framework_summary"
    ],
    "research_question": ["research_question"],
    "solution": ["solution"],
}

# 2. Build or load FAISS indexes for each attribute
attribute_storages = {}
embedding_model = camel_retriever.embedding_model

print("--- Initializing Vector Database ---")
for entity_type, attributes in node_attributes_to_vectorize.items():
    for attr in attributes:
        # Use a unique key for each entity type and attribute combination
        storage_key = (entity_type, attr)
        
        # Create nested directory structure: BASE_VDB_PATH/entity_type/attr
        storage_path = os.path.join(BASE_VDB_PATH, entity_type, attr)
        collection_name = f"{entity_type}_{attr}"
        
        # Check if storage exists by looking for the index file
        index_file_path = os.path.join(storage_path, f"{collection_name}.index")
        if os.path.exists(index_file_path):
            print(f"Loading existing FAISS storage for '{entity_type}.{attr}' from {storage_path}")
            storage = FaissStorage(
                vector_dim=embedding_model.get_output_dim(),
                storage_path=storage_path,
                collection_name=collection_name,
            )
            storage.load()
        else:
            print(f"Building FAISS storage for '{entity_type}.{attr}'...")
            os.makedirs(storage_path, exist_ok=True)
            storage = FaissStorage(
                vector_dim=embedding_model.get_output_dim(),
                storage_path=storage_path,
                collection_name=collection_name,
            )
            
            try:
                with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                print(f"Error: Could not load or parse {JSON_FILE_PATH}: {e}")
                continue

            records_to_add = []
            texts_to_embed = []
            metadata_for_records = []

            for entity in data.get("entities", []):
                if entity.get("entity_type") == entity_type:
                    entity_id = entity.get("source_id")
                    attribute_text = entity.get(attr)
                    if entity_id and attribute_text and isinstance(attribute_text, str) and attribute_text.strip():
                        texts_to_embed.append(attribute_text)
                        metadata_for_records.append({
                            "paper_id": entity_id,  # Keep original key for consistency
                            "entity_type": entity_type,
                            "attribute_name": attr,
                            "text": attribute_text
                        })
            
            if texts_to_embed:
                print(f"Embedding {len(texts_to_embed)} texts for '{entity_type}.{attr}'...")
                
                # 分批处理，每批最多25个文本（阿里云DashScope的限制）
                batch_size = 25
                embeddings = []
                
                for i in range(0, len(texts_to_embed), batch_size):
                    batch_texts = texts_to_embed[i:i + batch_size]
                    print(f"  Processing batch {i//batch_size + 1}/{(len(texts_to_embed) + batch_size - 1)//batch_size}")
                    batch_embeddings = embedding_model.embed_list(objs=batch_texts)
                    embeddings.extend(batch_embeddings)
                
                for i, embedding in enumerate(embeddings):
                    records_to_add.append(
                        VectorRecord(vector=embedding, payload=metadata_for_records[i])
                    )
                
                print(f"Adding {len(records_to_add)} records to '{entity_type}.{attr}' storage...")
                storage.add(records_to_add) # This also saves to disk
                print(f"Successfully built and saved storage for '{entity_type}.{attr}'.")
        
        attribute_storages[storage_key] = storage
print("--- Vector Database Initialized ---\n")

# 3. Perform search and format results
print("--- Performing Vector Search ---")
query_embedding = embedding_model.embed(obj=query)

all_results = []
for (entity_type, attr), storage in attribute_storages.items():
    if storage.status().vector_count > 0:
        db_query = VectorDBQuery(query_vector=query_embedding, top_k=1)
        results = storage.query(query=db_query)
        if results:
            for res in results:
                payload = res.record.payload
                res_text = (
                    f"Found in {payload.get('entity_type', 'N/A')} attribute '{payload.get('attribute_name', 'N/A')}':\n"
                    f"  - Similarity Score: {res.similarity:.4f}\n"
                    f"  - Paper ID: {payload.get('paper_id', 'N/A')}\n"
                    f"  - Content Snippet: {payload.get('text', '')}"
                )
                all_results.append(res_text)

vector_result = "\n\n".join(all_results)
if not vector_result:
    vector_result = "No relevant documents found in the local vector database."

# Show the result from vector search
print(vector_result)
print("====================================================\n")

# =================== Vector Search Logic End ===================

# Create an element from user query
query_element = uio.create_element_from_text(
    text=query, element_id="1"
)
print(query_element)
print("====================================================")
# Let Knowledge Graph Agent extract node and relationship information from the qyery
ans_element = kg_agent.run(query_element, parse_graph_elements=True)
print(ans_element)
print("====================================================")


# Match the entity got from query in the knowledge graph storage content
# 使用层级检索：先找Paper，再获取关联的RQ和Solution
kg_result = []

# 从KG Agent提取的节点构建关键词列表
extracted_keywords = [node.id for node in ans_element.nodes if node.id]
print(f"\n🔍 从查询中提取的关键词: {extracted_keywords}")

if extracted_keywords:
    # 构建关键词匹配条件（针对Paper的多个属性）
    paper_match_conditions = []
    rq_match_conditions = []
    
    for keyword in extracted_keywords:
        # Paper属性匹配
        paper_match_conditions.append(f"toLower(p.title) CONTAINS toLower('{keyword}')")
        paper_match_conditions.append(f"toLower(p.abstract) CONTAINS toLower('{keyword}')")
        paper_match_conditions.append(f"toLower(p.core_problem) CONTAINS toLower('{keyword}')")
        # RQ内容匹配
        rq_match_conditions.append(f"toLower(rq.research_question) CONTAINS toLower('{keyword}')")
    
    paper_where = " OR ".join(paper_match_conditions)
    rq_where = " OR ".join(rq_match_conditions)
    
    # 策略1：通过Paper属性检索完整层级
    n4j_query_paper = f"""
    // 找到匹配的Paper及其完整层级
    MATCH (p:Paper)
    WHERE {paper_where}
    
    // 获取关联的RQ和Solution
    OPTIONAL MATCH (p)-[:raise]->(rq:ResearchQuestion)-[:solved_by]->(sol:Solution)
    
    WITH p, rq, sol
    LIMIT 10
    
    RETURN 
        '=== Paper: ' + coalesce(p.title, 'N/A') + ' ===' + '\n' +
        'DOI: ' + coalesce(p.doi, 'N/A') + '\n' +
        'Year: ' + coalesce(p.year, 'N/A') + ', Conference: ' + coalesce(p.conference, 'N/A') + '\n' +
        'Core Problem: ' + coalesce(p.core_problem, 'N/A') + '\n' +
        'Abstract: ' + substring(coalesce(p.abstract, 'N/A'), 0, 300) + '...' + '\n' +
        CASE 
            WHEN rq IS NOT NULL THEN
                '\n[' + coalesce(rq.name, 'N/A') + '] ' + coalesce(rq.research_question, 'N/A') + '\n' +
                '  → Solution: ' + substring(coalesce(sol.solution, 'N/A'), 0, 200) + '...'
            ELSE ''
        END
    AS Description
    """
    
    result_paper = n4j.query(query=n4j_query_paper)
    kg_result.extend([item['Description'] for item in result_paper])
    
    # 策略2：通过RQ内容检索（如果Paper策略结果不足）
    if len(kg_result) < 3:
        n4j_query_rq = f"""
        // 找到匹配RQ的Paper层级
        MATCH (rq:ResearchQuestion)
        WHERE {rq_where}
        
        MATCH (p:Paper)-[:raise]->(rq)-[:solved_by]->(sol:Solution)
        
        WITH p, rq, sol
        LIMIT 10
        
        RETURN 
            '=== Paper: ' + coalesce(p.title, 'N/A') + ' ===' + '\n' +
            'DOI: ' + coalesce(p.doi, 'N/A') + '\n' +
            'Year: ' + coalesce(p.year, 'N/A') + ', Conference: ' + coalesce(p.conference, 'N/A') + '\n' +
            'Core Problem: ' + coalesce(p.core_problem, 'N/A') + '\n' +
            '\n[' + coalesce(rq.name, 'N/A') + '] ' + coalesce(rq.research_question, 'N/A') + '\n' +
            '  → Solution: ' + substring(coalesce(sol.solution, 'N/A'), 0, 200) + '...'
        AS Description
        """
        
        result_rq = n4j.query(query=n4j_query_rq)
        kg_result.extend([item['Description'] for item in result_rq])

# Remove duplicates and limit results
kg_result = list(dict.fromkeys(kg_result))[:5]  # 限制返回5个最相关结果

# Show the result from knowledge graph database
print(kg_result)


# === Ablation Study & Evaluation Functions Start ===

def run_rag_pipeline(
    query: str,
    mode: str,
    qwen_model,
    n4j,
    kg_agent,
    uio,
    attribute_storages,
    embedding_model,
    optimized_kg_retriever=None
) -> str:
    """
    运行可配置的 RAG 流水线，用于消融研究。

    Args:
        query (str): 用户查询。
        mode (str): 运行模式。可选值为 "llm_only", "vector_only", 
                    "kg_only", "hybrid"。
        qwen_model: 用于生成答案的语言模型。
        n4j: Neo4jGraph 实例。
        kg_agent: KnowledgeGraphAgent 实例。
        uio: UnstructuredIO 实例。
        attribute_storages (dict): 预初始化的向量存储。
        embedding_model: 嵌入模型实例。

    Returns:
        str: 生成的答案。
    """
    print(f"\n--- Running pipeline in '{mode}' mode ---")

    # 1. Vector Search (if applicable)
    vector_result = "Vector search was not performed in this mode."
    if mode in ["vector_only", "hybrid"]:
        print("--- Performing Vector Search (Enriched) ---")
        query_embedding = embedding_model.embed(obj=query)
        all_results = []
        seen_papers = set()
        
        # 优先检索关键属性，增加top_k
        priority_attrs = [
            ('paper', 'abstract'),
            ('paper', 'core_problem'),
            ('research_question', 'research_question'),
            ('solution', 'solution'),
        ]
        
        for entity_type, attr in priority_attrs:
            storage_key = (entity_type, attr)
            if storage_key not in attribute_storages:
                continue
                
            storage = attribute_storages[storage_key]
            if storage.status().vector_count == 0:
                continue
            
            # 增加top_k到3，获取更多结果
            db_query = VectorDBQuery(query_vector=query_embedding, top_k=3)
            results = storage.query(query=db_query)
            
            for res in results:
                payload = res.record.payload
                paper_id = payload.get('paper_id', 'N/A')
                
                # 去重：每个paper只保留一次
                if paper_id in seen_papers:
                    continue
                seen_papers.add(paper_id)
                
                # 构建更丰富的结果
                res_text = (
                    f"=== Vector Search Result (from {entity_type}.{attr}) ===\n"
                    f"Paper ID: {paper_id}\n"
                    f"Similarity Score: {res.similarity:.4f}\n"
                    f"Content:\n{payload.get('text', '')[:800]}..."
                )
                all_results.append(res_text)
        
        vector_result = "\n\n".join(all_results[:5])  # 保留top 5
        if not vector_result:
            vector_result = "No relevant documents found in the local vector database."

    # 2. Knowledge Graph Search (if applicable)
    kg_result_list = []
    if mode in ["kg_only", "hybrid"]:
        print("--- Performing Knowledge Graph Search (Optimized V2+) ---")
        
        # 使用优化版检索器 V2（语义检索 + 精确重排）
        if optimized_kg_retriever:
            print("  -> Using optimized semantic search (RQ-focused, enriched)")
            
            # 增加检索数量到10，获取更多上下文
            retrieved_items = optimized_kg_retriever.retrieve_with_diversity(
                query=query,
                top_k=10,  # 增加到10个
                diversity_weight=0.2  # 降低多样性权重，优先相关性
            )
            
            print(f"  -> Retrieved {len(retrieved_items)} items")
            
            # 获取完整Paper信息（包含更多字段）
            for item in retrieved_items:
                # 获取更完整的Paper信息
                full_paper = optimized_kg_retriever.get_paper_hierarchy_by_doi(item.paper_doi)
                
                # 构建更丰富的上下文
                desc_parts = [f"=== Paper: {item.paper_title} ==="]
                desc_parts.append(f"DOI: {item.paper_doi}")
                desc_parts.append(f"Year: {item.paper_year} | Conference: {item.paper_conference} | Relevance: {item.relevance_score:.3f}")
                desc_parts.append("")
                desc_parts.append(f"🔍 CORE PROBLEM:\n{item.core_problem[:400]}")
                desc_parts.append("")
                desc_parts.append(f"📝 ABSTRACT:\n{item.abstract[:500]}...")
                desc_parts.append("")
                desc_parts.append(f"❓ RESEARCH QUESTION [{item.rq_name}]:\n{item.research_question[:400]}")
                desc_parts.append("")
                desc_parts.append(f"💡 SOLUTION:\n{item.solution[:500]}...")
                
                kg_result_list.append("\n".join(desc_parts))
        
        if not kg_result_list:
            kg_result_list = ["No relevant papers found in knowledge graph."]

    # 3. Build Context based on mode
    kg_result_str = chr(10).join(kg_result_list) if kg_result_list else "No relevant graph relations found."
    
    if mode == "llm_only":
        structured_context = "No external context provided. The answer should be generated based on the model's internal knowledge."
    elif mode == "vector_only":
        structured_context = f"=== PRIMARY EVIDENCE (Vector Search Results) ===\n{vector_result}"
    elif mode == "kg_only":
        structured_context = f"=== SUPPLEMENTARY CONTEXT (Knowledge Graph Relations) ===\n{kg_result_str}"
    else:  # hybrid
        structured_context = f"""=== PRIMARY EVIDENCE (Vector Search Results) ===
{vector_result}

=== SUPPLEMENTARY CONTEXT (Knowledge Graph Relations) ===
{kg_result_str}"""

    # 4. Generate Answer
    advanced_system_prompt = """You are an expert AI research assistant specialized in computer vision, machine learning, and NLP research. Your task is to provide comprehensive, well-supported answers based on the retrieved research papers.

## Source Material Analysis:
You have been provided with:
- **Vector Search Results**: Semantic matches from paper abstracts and core problems
- **Knowledge Graph Results**: Structured paper information including Core Problem → Research Question → Solution hierarchies

## Answer Requirements:

### 1. Direct Answer (First 2-3 sentences)
Provide a concise, direct answer to the query based **exclusively** on the evidence provided. State the key approach/method clearly.

### 2. Detailed Technical Explanation
Expand on the answer with specific details from the papers:
- **Problem Definition**: What challenge does the paper address? (cite Core Problem)
- **Proposed Solution**: What is the main technical contribution? (cite Research Question and Solution)
- **Implementation Details**: How does the method work in practice?
- **Key Insights**: What are the main findings or innovations?

### 3. Evidence Citations
- Reference specific papers by title and year
- Quote key technical details when relevant
- Distinguish between different approaches if multiple papers are relevant

### 4. Critical Assessment
Briefly discuss:
- Strengths of the proposed approach
- Limitations or assumptions
- Applicability to the query context

## Critical Rules:
- ✅ Base your answer **only** on the provided evidence
- ✅ Include specific technical details (algorithms, architectures, metrics)
- ✅ Cite paper titles when referencing specific work
- ✅ If evidence is insufficient, clearly state what information is missing
- ❌ Do not introduce external knowledge not present in the evidence
- ❌ Do not speculate beyond what the papers support

Use clear academic language and structured formatting (sections, bullet points) for readability."""
    
    sys_msg = BaseMessage.make_assistant_message(
        role_name="Expert Research Assistant",
        content=advanced_system_prompt,
    )
    camel_agent = ChatAgent(system_message=sys_msg, model=qwen_model)

    user_prompt = f"""## Research Query:
{query}

## Retrieved Research Papers:
{structured_context}

## Instructions:
Based on the research papers provided above, answer the query following these steps:

1. **Direct Answer**: State the main approach/conclusion in 2-3 sentences
2. **Technical Details**: Explain the methodology with specific details from the papers
3. **Evidence**: Cite specific paper titles and key findings
4. **Critical Notes**: Mention any limitations or important caveats

Focus on synthesizing information from ALL relevant papers provided, not just the first one. If multiple papers address the query, compare their approaches."""
    
    user_msg = BaseMessage.make_user_message(role_name="CAMEL User", content=user_prompt)
    agent_response = camel_agent.step(user_msg)
    
    return agent_response.msg.content if agent_response.msg else "Failed to get a response."


def evaluate_responses_with_llm(query: str, responses: dict, llm) -> str:
    """
    使用大语言模型（LLM）来评估和比较不同 RAG 模式下的响应。

    Args:
        query (str): 原始的用户查询。
        responses (dict): 包含不同模式及其生成答案的字典。
        llm: 用于评估的语言模型。

    Returns:
        str: LLM 生成的评估分析报告。
    """
    evaluation_prompt = f"""
You are an expert evaluator for Retrieval-Augmented Generation (RAG) systems. Your task is to analyze and compare four different answers to a given research query. Each answer was generated using a different method.

**Research Query:**
"{query}"

**Generated Answers:**

---
### Answer 1: LLM Only (Baseline)
This answer was generated by the language model without any external knowledge.
```
{responses.get("llm_only", "N/A")}
```
---
### Answer 2: Vector Search Only
This answer was generated using context retrieved from a vector database.
```
{responses.get("vector_only", "N/A")}
```
---
### Answer 3: Knowledge Graph Only
This answer was generated using context retrieved from a knowledge graph.
```
{responses.get("kg_only", "N/A")}
```
---
### Answer 4: Hybrid (Vector + Knowledge Graph)
This answer was generated using a combination of context from both vector search and the knowledge graph.
```
{responses.get("hybrid", "N/A")}
```
---

**Your Evaluation Task:**

Please provide a structured analysis comparing these four answers. Evaluate them based on the following criteria:
1.  **Faithfulness & Grounding (1-5):** How well does the answer adhere to the provided context (if any)? A high score means no hallucinated facts. For "LLM Only", assess its general accuracy.
2.  **Relevance (1-5):** How relevant is the answer to the original query?
3.  **Completeness (1-5):** How comprehensively does the answer address all aspects of the query?
4.  **Clarity (1-5):** How clear, concise, and well-structured is the answer?

**Output Format:**

1.  **Comparison Table:** Create a markdown table summarizing the scores for each method.
2.  **Detailed Analysis:** For each method, provide a brief paragraph explaining its strengths and weaknesses based on your scoring.
3.  **Final Recommendation:** Conclude with a summary of which method performed best for this specific query and why. Explain the value contributed by vector search and the knowledge graph.
"""
    
    sys_msg = BaseMessage.make_assistant_message(
        role_name="RAG Evaluator",
        content="You are an expert evaluator for RAG systems.",
    )
    evaluator_agent = ChatAgent(system_message=sys_msg, model=llm)
    user_msg = BaseMessage.make_user_message(role_name="User", content=evaluation_prompt)
    
    print("\n--- Evaluating responses with LLM ---")
    evaluation_response = evaluator_agent.step(user_msg)
    
    return evaluation_response.msg.content if evaluation_response.msg else "Failed to get evaluation."

# === Ablation Study & Evaluation Functions End ===


def run_ablation_study(
    query, qwen_model, n4j, kg_agent, uio, attribute_storages, embedding_model, optimized_kg_retriever
):
    """主函数，运行消融实验并输出评估结果。"""
    
    modes = ["llm_only", "vector_only", "kg_only", "hybrid"]
    responses = {}

    for mode in modes:
        response = run_rag_pipeline(
            query=query,
            mode=mode,
            qwen_model=qwen_model,
            n4j=n4j,
            kg_agent=kg_agent,
            uio=uio,
            attribute_storages=attribute_storages,
            embedding_model=embedding_model,
            optimized_kg_retriever=optimized_kg_retriever,
        )
        responses[mode] = response
        print(f"--- Response for '{mode}' ---")
        print(response)
        print("====================================================\n")

    # 使用 LLM 进行评估
    evaluation_result = evaluate_responses_with_llm(query, responses, qwen_model)
    
    print("\n--- Final Evaluation Report ---")
    print(evaluation_result)
    print("====================================================\n")


# ================== Main Execution ==================

# 运行消融研究
run_ablation_study(
    query=query,
    qwen_model=qwen_model,
    n4j=n4j,
    kg_agent=kg_agent,
    uio=uio,
    attribute_storages=attribute_storages,
    embedding_model=camel_retriever.embedding_model,
    optimized_kg_retriever=optimized_kg_retriever,
)

print("finished!")