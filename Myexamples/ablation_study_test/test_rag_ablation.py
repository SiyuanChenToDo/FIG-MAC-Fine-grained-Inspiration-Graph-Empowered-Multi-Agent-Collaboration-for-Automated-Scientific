#图谱的检索存在冗余
#为muti-agent系统提供信息
#可以评估rag指标，做消融实验，证明数据集的价值
import sys
print(f"Python Version: {sys.version}")
print(f"Sys Path: {sys.path}")

from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.configs import MistralConfig, OllamaConfig, QwenConfig
from camel.loaders import UnstructuredIO
from camel.storages import Neo4jGraph
from camel.retrievers import AutoRetriever
from camel.embeddings import OpenAICompatibleEmbedding
from camel.types import StorageType
from camel.agents import ChatAgent, KnowledgeGraphAgent
from camel.messages import BaseMessage
from camel.storages import FaissStorage, VectorRecord, VectorDBQuery


import json
import os
from getpass import getpass
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
    url="bolt://localhost:17687",
    username="neo4j",
    password="ai4sci123456",
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
kg_result = []
for node in ans_element.nodes:
    # 这里的 `node.id` 应该对应你的知识图谱中的某个节点主键，例如 `file_id`
    # Cypher 查询需要根据你的实际数据模型进行修改
    
    # Cypher 查询匹配实际的图谱结构
    n4j_query = f"""
    // 搜索包含关键词的节点
    MATCH (n)
    WHERE any(key IN keys(n) WHERE toLower(toString(n[key])) CONTAINS toLower('{node.id}'))

    // 查找其相关节点
    OPTIONAL MATCH (n)-[r]-(m)

    WITH n, r, m
    LIMIT 5

    RETURN
        'Found a ' + labels(n)[0] + ' node. ' +
        CASE
            WHEN 'Paper' IN labels(n) THEN 
                'Title: ' + coalesce(n.title, 'N/A') + '. ' +
                'Core Problem: ' + coalesce(n.core_problem, 'N/A') + '. ' +
                'Abstract: ' + coalesce(n.abstract, 'N/A') + '. ' +
                'Related Work: ' + coalesce(n.related_work, 'N/A') + '. ' +
                'Framework Summary: ' + coalesce(n.framework_summary, 'N/A')
            WHEN 'ResearchQuestion' IN labels(n) THEN 
                'Research Question: ' + coalesce(n.text, 'N/A')
            WHEN 'Solution' IN labels(n) THEN 
                'Solution: ' + coalesce(n.text, 'N/A')
            ELSE 'Unknown node type'
        END +
        CASE
            WHEN m IS NOT NULL THEN
                ' This node has a ' + type(r) + ' relationship with a ' + labels(m)[0] + ' node. ' +
                CASE
                    WHEN 'Paper' IN labels(m) THEN 'The related paper title is: ' + coalesce(m.title, 'N/A') + '.'
                    WHEN 'ResearchQuestion' IN labels(m) THEN 'The related research question is: ' + coalesce(m.text, 'N/A') + '.'
                    WHEN 'Solution' IN labels(m) THEN 'The related solution is: ' + coalesce(m.text, 'N/A') + '.'
                    ELSE ''
                END
            ELSE ''
        END
    AS Description
    """
    
    result = n4j.query(query=n4j_query)
    # The result is a list of dicts, e.g., [{'Description': '...'}].
    # We extract the string values before extending the list.
    kg_result.extend([item['Description'] for item in result])

# Remove duplicates from the knowledge graph results list of strings
kg_result = list(dict.fromkeys(kg_result))

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
    embedding_model
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

    # 2. Knowledge Graph Search (if applicable)
    kg_result_list = []
    if mode in ["kg_only", "hybrid"]:
        print("--- Performing Knowledge Graph Search ---")
        query_element = uio.create_element_from_text(text=query, element_id="1")
        ans_element = kg_agent.run(query_element, parse_graph_elements=True)
        for node in ans_element.nodes:
            n4j_query = f"""
            // 搜索包含关键词的节点
            MATCH (n)
            WHERE any(key IN keys(n) WHERE toLower(toString(n[key])) CONTAINS toLower('{node.id}'))
            
            // 查找其相关节点
            OPTIONAL MATCH (n)-[r]-(m)
            
            WITH n, r, m
            LIMIT 5
            
            RETURN
                'Found a ' + labels(n)[0] + ' node. ' +
                CASE
                    WHEN 'Paper' IN labels(n) THEN 
                        'Title: ' + coalesce(n.title, 'N/A') + '. ' +
                        'Core Problem: ' + coalesce(n.core_problem, 'N/A') + '. ' +
                        'Abstract: ' + coalesce(n.abstract, 'N/A') + '. ' +
                        'Related Work: ' + coalesce(n.related_work, 'N/A') + '. ' +
                        'Framework Summary: ' + coalesce(n.framework_summary, 'N/A')
                    WHEN 'ResearchQuestion' IN labels(n) THEN 
                        'Research Question: ' + coalesce(n.text, 'N/A')
                    WHEN 'Solution' IN labels(n) THEN 
                        'Solution: ' + coalesce(n.text, 'N/A')
                    ELSE 'Unknown node type'
                END +
                CASE
                    WHEN m IS NOT NULL THEN
                        ' This node has a ' + type(r) + ' relationship with a ' + labels(m)[0] + ' node. ' +
                        CASE
                            WHEN 'Paper' IN labels(m) THEN 'The related paper title is: ' + coalesce(m.title, 'N/A') + '.'
                            WHEN 'ResearchQuestion' IN labels(m) THEN 'The related research question is: ' + coalesce(m.text, 'N/A') + '.'
                            WHEN 'Solution' IN labels(m) THEN 'The related solution is: ' + coalesce(m.text, 'N/A') + '.'
                            ELSE ''
                        END
                    ELSE ''
                END
            AS Description
            """
            result = n4j.query(query=n4j_query)
            kg_result_list.extend([item['Description'] for item in result])
        kg_result_list = list(dict.fromkeys(kg_result_list))

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
    advanced_system_prompt = """You are an expert AI research assistant specialized in computer vision, machine learning, and related technical domains. Your mission is to provide comprehensive, accurate, and well-structured answers to technical research questions.

## Core Capabilities:
- Deep understanding of computer vision, machine learning, and AI research methodologies
- Ability to synthesize information from multiple sources with different reliability levels
- Expert knowledge in technical concepts, algorithms, frameworks, and experimental designs
- Skilled in identifying and prioritizing the most relevant information for answering complex queries

## Response Strategy:
1. **Information Prioritization**: 
   - PRIMARY: Focus primarily on "Primary Evidence" which contains highly relevant, semantically matched content
   - SUPPLEMENTARY: Use "Supplementary Context" only if it adds valuable insights not covered in primary evidence
   - FILTERING: Ignore any information that is clearly irrelevant to the query domain or topic

2. **Answer Structure**:
   - Begin with a direct, concise answer based *strictly* on the provided evidence.
   - Then, create a clearly marked "### Expert Elaboration" section. In this section, if the evidence mentions a technical concept (e.g., 'channel attention') but lacks implementation details, elaborate on its typical mechanism and how it plausibly works in this specific context.
   - Use formatting (bullet points, emphasis) to structure technical details for clarity.
   - Conclude with a summary of key insights.

3. **Quality Assurance**:
   - In the main answer, ensure technical accuracy based *only* on the evidence.
   - In the "Expert Elaboration" section, clearly state that this is a reasoned inference based on established principles, as the source text lacks full detail.
   - Avoid speculation beyond what is plausible for an expert in the field.

4. **Communication Style**:
   - Use clear, professional academic language
   - Structure information logically with proper technical terminology
   - Provide sufficient detail for technical understanding while remaining accessible
   - Use formatting (bullet points, emphasis) to enhance clarity when helpful

## Critical Guidelines:
- Never fabricate technical details not present in the provided evidence
- Prioritize evidence quality over quantity
- Focus on answering the specific question asked rather than providing general background
- If multiple approaches are mentioned in evidence, compare and contrast them appropriately"""
    
    sys_msg = BaseMessage.make_assistant_message(
        role_name="Expert Research Assistant",
        content=advanced_system_prompt,
    )
    camel_agent = ChatAgent(system_message=sys_msg, model=qwen_model)

    user_prompt = f"""## Research Query:
{query}

## Available Evidence:
{structured_context}

## Task:
Please provide a comprehensive answer to the research query using the evidence above. Follow your response strategy to prioritize the most relevant information and provide a well-structured, technically accurate answer."""
    
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
    query, qwen_model, n4j, kg_agent, uio, attribute_storages, embedding_model
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
)

print("finished!")