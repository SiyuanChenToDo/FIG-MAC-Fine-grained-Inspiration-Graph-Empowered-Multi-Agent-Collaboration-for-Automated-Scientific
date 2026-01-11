from typing import List, Optional

import os
import json
import sys

# Add project root to sys.path to import inspire_pipeline
PROJECT_ROOT = '/root/autodl-tmp'
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from camel.retrievers import AutoRetriever
from camel.types import StorageType
from camel.storages import FaissStorage, VectorRecord, VectorDBQuery
from camel.embeddings import OpenAICompatibleEmbedding
from camel.storages import Neo4jGraph
from camel.agents import ChatAgent, KnowledgeGraphAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.configs import QwenConfig

# Import the Inspiration Pipeline
try:
    from inspire_pipeline import ScientificInspirationPipeline
except ImportError:
    ScientificInspirationPipeline = None
    print("Warning: Could not import ScientificInspirationPipeline from inspire_pipeline.py")

# Global singleton for the pipeline
_INSPIRATION_PIPELINE = None

def build_rag_prompt_for_agent(
    query: str,
    primary_evidence: str,
    graph_inspiration: str,
    agent_role: str = "Research Agent",
    task_description: str = "analyze and synthesize the provided evidence"
) -> str:
    """
    Build a high-quality prompt for the next agent using RAG evidence.
    Uses graph inspiration as skeleton, primary evidence as supporting details.
    
    Args:
        query: The research query
        primary_evidence: Vector search results (supporting details)
        graph_inspiration: Knowledge graph inspiration paths (skeleton)
        agent_role: Role of the agent receiving this prompt
        task_description: Description of what the agent should do
    
    Returns:
        Formatted prompt string optimized for the agent
    """
    if graph_inspiration and len(graph_inspiration) > 0 and "未找到" not in graph_inspiration and "Error" not in graph_inspiration:
        # Case 1: Both graph and vector evidence available
        # Use graph as skeleton, vector as flesh
        prompt = f"""## Research Query
{query}

## 🔗 KNOWLEDGE GRAPH INSPIRATION PATHS (Core Skeleton - Follow This Structure)
{graph_inspiration}

## 📚 VECTOR SEARCH EVIDENCE (Supporting Details - Enrich the Skeleton)
{primary_evidence}

## Your Task
{task_description}

## Critical Instructions
1. **Structure**: Use the Knowledge Graph Inspiration Paths as your **skeleton** (main analytical framework).
   - Each inspiration path represents a potential research direction or connection.
   - Follow the structure suggested by the graph paths.

2. **Enrichment**: Use the Vector Search Evidence as **flesh** (supporting details).
   - Extract specific papers, methods, datasets, and results from vector evidence.
   - Match vector evidence to relevant inspiration paths.
   - Provide fine-grained technical details for each path.

3. **Synthesis**: 
   - For each inspiration path, identify relevant supporting evidence from vector search.
   - Combine cross-domain insights (from graph) with specific technical details (from vector).
   - Build a coherent narrative that leverages both sources.

4. **Quality Standards**:
   - Maintain fine-grained technical details (paper titles, authors, methods, datasets).
   - Reference specific sources from both graph and vector evidence.
   - Ensure traceability: every claim should be grounded in the provided evidence.
   - Avoid redundancy: don't repeat the same information multiple times.

5. **Output Format**:
   - Organize your response following the structure suggested by the inspiration paths.
   - For each path, provide: (1) Core insight from graph, (2) Supporting details from vector, (3) Synthesis.
   - Use clear section headers and bullet points for readability.
"""
    else:
        # Case 2: Only vector evidence available (no graph inspiration)
        prompt = f"""## Research Query
{query}

## 📚 VECTOR SEARCH EVIDENCE (Primary Source)
{primary_evidence}

## Your Task
{task_description}

## Critical Instructions
1. **Analysis**: Systematically analyze the vector search evidence above.
   - Extract key papers, methods, datasets, and results.
   - Identify research gaps and opportunities.

2. **Structure**: Organize your response logically:
   - Overview of existing research
   - Key findings and methodologies
   - Research gaps and limitations
   - Future directions

3. **Quality Standards**:
   - Maintain fine-grained technical details (paper titles, authors, methods, datasets).
   - Reference specific sources from the evidence.
   - Ensure traceability: every claim should be grounded in the provided evidence.

4. **Output Format**:
   - Use clear section headers and bullet points.
   - Provide detailed citations and technical specifics.
"""
    
    return prompt

def get_inspiration_pipeline():
    global _INSPIRATION_PIPELINE
    if _INSPIRATION_PIPELINE is None and ScientificInspirationPipeline:
        from pathlib import Path
        BASE_DIR = Path('/root/autodl-tmp')
        GRAPH_DIR = BASE_DIR / 'data/graphstorm_partitioned'
        RAW_DIR = BASE_DIR / 'data'
        MODEL_DIR = BASE_DIR / 'workspace/inference_results/best_model_v1/predictions' 
        
        # ===== SET HUGGINGFACE MIRROR BEFORE INITIALIZATION =====
        # Set HuggingFace mirror to avoid network issues
        hf_mirror = os.environ.get("HF_MIRROR", "https://hf-mirror.com")
        
        # Set multiple environment variables for different libraries
        os.environ["HF_ENDPOINT"] = hf_mirror
        os.environ["HUGGINGFACE_HUB_CACHE"] = os.environ.get("HUGGINGFACE_HUB_CACHE",
            os.path.join(BASE_DIR, ".cache", "huggingface", "hub"))
        
        # Also set for huggingface_hub library directly (if available)
        try:
            import huggingface_hub
            # Set the endpoint for huggingface_hub
            if hasattr(huggingface_hub, 'constants'):
                huggingface_hub.constants.ENDPOINT = hf_mirror
            print(f"[RAG] Setting HuggingFace mirror via huggingface_hub: {hf_mirror}")
        except (ImportError, AttributeError):
            # If huggingface_hub is not available, use env var only
            print(f"[RAG] Setting HuggingFace mirror via HF_ENDPOINT: {hf_mirror}")
        
        # Set cache directories for transformers and sentence-transformers
        cache_dir = os.path.join(BASE_DIR, ".cache", "huggingface")
        os.makedirs(cache_dir, exist_ok=True)
        os.environ["HF_HOME"] = cache_dir
        os.environ["TRANSFORMERS_CACHE"] = cache_dir
        os.environ["SENTENCE_TRANSFORMERS_HOME"] = cache_dir
        # ===== END MIRROR SETUP =====
        
        try:
            _INSPIRATION_PIPELINE = ScientificInspirationPipeline(
                graph_path=str(GRAPH_DIR),
                node_map_path=str(GRAPH_DIR / 'raw_id_mappings'),
                model_path=str(MODEL_DIR),
                raw_data_path=str(RAW_DIR)
            )
        except Exception as e:
            print(f"[RAG][ERROR] Failed to initialize ScientificInspirationPipeline: {e}")
            print(f"[RAG][ERROR] This may be due to network issues downloading models from HuggingFace.")
            print(f"[RAG][ERROR] You can set HF_MIRROR environment variable to use a mirror, e.g., export HF_MIRROR=https://hf-mirror.com")
            return None
    return _INSPIRATION_PIPELINE

def run_local_rag(
    query: str,
    json_file_path: str = 'D:\Backup\Downloads\camel-master2\camel-master\Myexamples\data/final_data/final_custom_kg_papers.json',
    base_vdb_path: str = 'Myexamples/vdb/camel_faiss_storage',
    paper_attributes: List[str] | None = None,
    attributes_to_vectorize: dict | None = None,
    neo4j_url: Optional[str] = None,
    neo4j_username: Optional[str] = None,
    neo4j_password: Optional[str] = None,
    build_if_missing: bool = True,
    use_new_structure: bool = None,
    max_index_size_mb: int | None = 512,
    enabled_attributes: dict | None = None,
    return_structured: bool = True,
    enable_vector_retrieval: bool = True,
    enable_graph_retrieval: bool = True,
) -> str | dict:
    """运行本地向量库检索并返回结构化文本结果。
    
    支持两种存储结构：
    1. 旧结构（向后兼容）: base_vdb_path/attribute_name/
    2. 新结构（推荐）: base_vdb_path/entity_type/attribute_name/

    - 若本地 FAISS 库已存在，则直接查询；
    - 若不存在，将跳过构建并返回提示信息（避免工具在无数据时阻塞）。
    - 仅依赖 DashScope/OpenAI 兼容 embedding 接口（通过环境变量提供）。
    
    Args:
        query: 查询文本
        json_file_path: JSON数据文件路径
        base_vdb_path: 向量数据库基础路径
        paper_attributes: 旧参数，用于向后兼容（仅paper实体类型）
        attributes_to_vectorize: 新参数，支持多实体类型的属性字典
        use_new_structure: 是否使用新的分层结构。None=自动检测，True=强制新结构，False=强制旧结构
        enable_vector_retrieval: 是否启用向量检索（默认True）
        enable_graph_retrieval: 是否启用知识图谱灵感链路检索（默认True）
    """
    
    # 检查环境变量（用于消融实验，环境变量优先级高于参数）
    if os.environ.get("DISABLE_VECTOR_RETRIEVAL", "").lower() in ("1", "true", "yes"):
        enable_vector_retrieval = False
    if os.environ.get("DISABLE_GRAPH_RETRIEVAL", "").lower() in ("1", "true", "yes"):
        enable_graph_retrieval = False
    
    # 自动检测使用哪种结构
    if use_new_structure is None:
        # 检查是否存在新结构的目录
        new_structure_exists = os.path.exists(os.path.join(base_vdb_path, "paper")) or \
                              os.path.exists(os.path.join(base_vdb_path, "research_question")) or \
                              os.path.exists(os.path.join(base_vdb_path, "solution"))
        use_new_structure = new_structure_exists
    
    # 设置属性配置
    if attributes_to_vectorize is None:
        if use_new_structure:
            # 新结构：支持多实体类型
            attributes_to_vectorize = {
                "paper": [
                    "abstract", "core_problem", "related_work",
                    "preliminary_innovation_analysis", "framework_summary"
                ],
                "research_question": ["research_question"],
                "solution": ["solution"],
            }
        else:
            # 旧结构：仅paper实体类型（向后兼容）
            if paper_attributes is None:
                paper_attributes = [
                    "abstract", "core_problem", "related_work",
                    "preliminary_innovation_analysis", "framework_summary"
                ]
            attributes_to_vectorize = {"paper": paper_attributes}

    env_enabled_attrs = os.environ.get("LOCAL_RAG_ENABLED_ATTRIBUTES")
    if enabled_attributes is None and env_enabled_attrs:
        enabled_attributes = {}
        for token in env_enabled_attrs.split(','):
            token = token.strip()
            if not token:
                continue
            if '.' in token:
                entity_type, attr_name = token.split('.', 1)
            else:
                entity_type, attr_name = 'paper', token
            enabled_attributes.setdefault(entity_type.strip(), set()).add(attr_name.strip())

    if enabled_attributes:
        filtered_attributes: dict[str, list[str]] = {}
        for entity_type, attrs in attributes_to_vectorize.items():
            allowed = enabled_attributes.get(entity_type)
            if not allowed:
                continue
            filtered = [attr for attr in attrs if attr in allowed]
            if filtered:
                filtered_attributes[entity_type] = filtered
        if filtered_attributes:
            attributes_to_vectorize = filtered_attributes

    max_index_bytes = None if max_index_size_mb in (None, 0) else max_index_size_mb * 1024 * 1024
    if max_index_bytes is None:
        env_limit = os.environ.get("LOCAL_RAG_MAX_INDEX_MB")
        if env_limit:
            try:
                max_index_mb_env = int(env_limit)
                if max_index_mb_env > 0:
                    max_index_bytes = max_index_mb_env * 1024 * 1024
            except ValueError:
                pass

    # Explicitly hardcode API Key/URL (consistent with test_graph.py), ensure this function is independently usable
    os.environ["OPENAI_COMPATIBILITY_API_KEY"] = "sk-f97b45fe14844ba98d405488499434b7"
    os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    os.environ["QWEN_API_KEY"] = os.environ["OPENAI_COMPATIBILITY_API_KEY"]
    os.environ["QWEN_API_BASE_URL"] = os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"]

    # Initialize embedding model (requires external OPENAI_COMPATIBILITY_API_KEY/URL to be set)
    DEBUG = str(os.environ.get("LOCAL_RAG_DEBUG", "")).lower() in ("1", "true", "yes", "y")
    if DEBUG:
        print(f"[RAG][DEBUG] run_local_rag called with query: {query}")
    try:
        embedding_model = OpenAICompatibleEmbedding(
            model_type="text-embedding-v2",
            api_key=os.environ.get("OPENAI_COMPATIBILITY_API_KEY") or os.environ.get("QWEN_API_KEY"),
            url=os.environ.get("OPENAI_COMPATIBILITY_API_BASE_URL") or os.environ.get("QWEN_API_BASE_URL"),
        )
    except Exception as e:
        if DEBUG:
            print("[RAG][DEBUG] Embedding model init failed:", repr(e))
        raise

    # 载入或按需构建 FAISS 索引（支持新旧两种结构）
    attribute_storages = {}
    built_attrs: List[str] = []
    loaded_attrs: List[str] = []

    # 如果禁用向量检索，跳过索引加载
    if not enable_vector_retrieval:
        print("[RAG] Vector retrieval disabled (ablation experiment)")
    else:
        for entity_type, attributes in attributes_to_vectorize.items():
            for attr in attributes:
                # 根据结构类型确定存储路径和键
                if use_new_structure:
                    storage_key = (entity_type, attr)
                    storage_path = os.path.join(base_vdb_path, entity_type, attr)
                    collection_name = f"{entity_type}_{attr}"
                    attr_display = f"{entity_type}.{attr}"
                else:
                    # 旧结构：直接使用属性名作为键（向后兼容）
                    storage_key = attr
                    storage_path = os.path.join(base_vdb_path, attr)
                    collection_name = f"paper_{attr}"
                    attr_display = attr
                
                index_file_path = os.path.join(storage_path, f"{collection_name}.index")

                if os.path.exists(index_file_path):
                    # 加载已存在的索引
                    try:
                        storage = FaissStorage(
                            vector_dim=embedding_model.get_output_dim(),
                            storage_path=storage_path,
                            collection_name=collection_name,
                        )
                        storage.load()
                        attribute_storages[storage_key] = storage
                        loaded_attrs.append(attr_display)
                    except (UnicodeDecodeError, Exception) as e:
                        print(f"Warning: Failed to load FAISS storage for {attr_display}: {e}")
                        print(f"Skipping {attr_display} attribute for now.")
                        continue
                elif build_if_missing:
                    # 构建新索引
                    os.makedirs(storage_path, exist_ok=True)
                    storage = FaissStorage(
                        vector_dim=embedding_model.get_output_dim(),
                        storage_path=storage_path,
                        collection_name=collection_name,
                    )
                    # 从 JSON 构建
                    try:
                        with open(json_file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                    except (FileNotFoundError, json.JSONDecodeError):
                        # 如果无法构建则跳过该属性
                        continue
                    texts_to_embed: List[str] = []
                    metadata_for_records: List[dict] = []
                    for entity in data.get("entities", []):
                        if entity.get("entity_type") == entity_type:
                            entity_id = entity.get("source_id")
                            attribute_text = entity.get(attr)
                            if entity_id and attribute_text and isinstance(attribute_text, str) and attribute_text.strip():
                                texts_to_embed.append(attribute_text)
                                metadata_for_records.append({
                                    "paper_id": entity_id,
                                    "entity_type": entity_type,
                                    "attribute_name": attr,
                                    "text": attribute_text,
                                })
                    if texts_to_embed:
                        batch_size = 25
                        embeddings: List[List[float]] = []
                        for i in range(0, len(texts_to_embed), batch_size):
                            batch_texts = texts_to_embed[i:i + batch_size]
                            batch_embeddings = embedding_model.embed_list(objs=batch_texts)
                            embeddings.extend(batch_embeddings)
                        records_to_add: List[VectorRecord] = []
                        for i, embedding in enumerate(embeddings):
                            records_to_add.append(
                                VectorRecord(vector=embedding, payload=metadata_for_records[i])
                            )
                        if records_to_add:
                            storage.add(records_to_add)
                    attribute_storages[storage_key] = storage
                    built_attrs.append(attr_display)
    # 结束向量检索部分

    if not attribute_storages:
        # Neither available index nor allowed to build, directly try graph retrieval and answer generation later
        if DEBUG:
            print("[RAG][DEBUG] No FAISS storages available (none loaded/built)")
        pass
    elif DEBUG:
        print(f"[RAG][DEBUG] FAISS storages -> loaded: {loaded_attrs}, built: {built_attrs}")

    # 向量检索查询
    all_results: List[str] = []
    if enable_vector_retrieval and attribute_storages:
        try:
            query_embedding = embedding_model.embed(obj=query)
        except Exception as e:
            if DEBUG:
                print("[RAG][DEBUG] Embedding query failed:", repr(e))
            query_embedding = None
        
        for storage_key, storage in attribute_storages.items():
            if storage.status().vector_count > 0:
                results = []
                if query_embedding is not None:
                    db_query = VectorDBQuery(query_vector=query_embedding, top_k=1)
                    try:
                        results = storage.query(query=db_query)
                    except Exception as e:
                        # 格式化存储键用于错误信息
                        key_str = f"{storage_key[0]}.{storage_key[1]}" if isinstance(storage_key, tuple) else storage_key
                        if DEBUG:
                            print(f"[RAG][DEBUG] Vector query failed for attr='{key_str}':", repr(e))
                if results:
                    for res in results:
                        payload = res.record.payload
                        # 支持新旧两种payload格式
                        if use_new_structure and 'entity_type' in payload:
                            # 新格式：包含entity_type
                            res_text = (
                                f"Found in {payload.get('entity_type', 'N/A')} attribute '{payload.get('attribute_name', 'N/A')}':\n"
                                f"  - Similarity Score: {res.similarity:.4f}\n"
                                f"  - Paper ID: {payload.get('paper_id', 'N/A')}\n"
                                f"  - Content Snippet: {payload.get('text', '')}"
                            )
                        else:
                            # 旧格式：仅attribute_name（向后兼容）
                            attr_name = payload.get('attribute_name', storage_key if isinstance(storage_key, str) else storage_key[1])
                            res_text = (
                                f"Found in '{attr_name}':\n"
                                f"  - Similarity: {res.similarity:.4f}\n"
                                f"  - Paper ID: {payload.get('paper_id', 'N/A')}\n"
                                f"  - Content: {payload.get('text', '')}"
                            )
                        all_results.append(res_text)
    else:
        if not enable_vector_retrieval:
            print("[RAG] Vector retrieval skipped (ablation experiment)")

    vector_result = "\n\n".join(all_results) if all_results else "No relevant documents found in the local vector database."
    if DEBUG:
        print(f"[RAG][DEBUG] Vector search hits: {len(all_results)}")

    # === Graph Inspiration Pipeline Integration ===
    graph_result = ""
    if enable_graph_retrieval:
        try:
            print("\n[RAG] 🔗 Starting Knowledge Graph Inspiration Pipeline...")
            print("[RAG] Query for graph retrieval:", query[:100] + "..." if len(query) > 100 else query)
            pipeline = get_inspiration_pipeline()
            if pipeline:
                print("[RAG] ✅ ScientificInspirationPipeline initialized successfully")
                # Run the pipeline and get the report content
                # We use default min_paths=3, start_top_k=5 as per user preference
                print("[RAG] Running graph retrieval (min_paths=3, start_top_k=5)...")
                graph_result = pipeline.get_report(query, min_paths=3, start_top_k=5)
                print(f"[RAG] ✅ Knowledge graph inspiration report generated ({len(graph_result)} chars)")
                if len(graph_result) > 0 and "未找到" not in graph_result and "未发现" not in graph_result:
                    print(f"[RAG] Graph result preview (first 300 chars):\n{graph_result[:300]}...")
                elif len(graph_result) == 0:
                    print("[RAG] ⚠️ Warning: Graph result is empty (no inspiration paths found)")
                else:
                    print(f"[RAG] ⚠️ Warning: Graph result indicates no paths found: {graph_result[:100]}")
            else:
                graph_result = "ScientificInspirationPipeline could not be initialized (pipeline is None)."
                print("[RAG] ❌ Warning: ScientificInspirationPipeline initialization failed (returned None)")
                print("[RAG] This may be due to:")
                print("  - Missing data files (graphstorm_partitioned, neo4j_export, etc.)")
                print("  - Network issues downloading HuggingFace models")
                print("  - Import errors in inspire_pipeline.py")
        except Exception as e:
            import traceback
            graph_result = f"Error during inspiration generation: {str(e)}"
            print(f"[RAG] ❌ Error during inspiration generation: {e}")
            print(f"[RAG] Error traceback:")
            print(traceback.format_exc()[:500])
    else:
        print("[RAG] Graph retrieval disabled (ablation experiment)")
        graph_result = ""

    # ===== STRUCTURE THREE PARTS =====
    # Part 1: Primary Evidence (Vector Search Results)
    primary_evidence = vector_result if vector_result and len(vector_result) > 0 else "No relevant documents found in the local vector database."
    
    # Part 2: Knowledge Graph Inspiration Paths (Skeleton)
    graph_inspiration = graph_result if graph_result and len(graph_result) > 0 and "未找到" not in graph_result and "Error" not in graph_result else ""
    
    # Part 3: Structured Context for LLM (Graph as skeleton, Vector as flesh)
    # Build structured context with graph inspiration as the skeleton
    if graph_inspiration:
        # Use graph inspiration as the main structure, enrich with vector evidence
        structured_context = (
            "## 🔗 KNOWLEDGE GRAPH INSPIRATION PATHS (Core Skeleton)\n"
            f"{graph_inspiration}\n\n"
            "---\n\n"
            "## 📚 VECTOR SEARCH EVIDENCE (Supporting Details)\n"
            f"{primary_evidence}\n\n"
            "---\n\n"
            "## 📋 USAGE INSTRUCTIONS\n"
            "**CRITICAL**: Use the Knowledge Graph Inspiration Paths as the **skeleton** (main structure) for your analysis. "
            "The Vector Search Evidence provides **flesh** (supporting details, specific papers, methods, datasets) to enrich each inspiration path. "
            "Synthesize them together to form a comprehensive, fine-grained understanding."
        )
    else:
        # Fallback: if no graph inspiration, use vector evidence as primary
        structured_context = (
            "## 📚 VECTOR SEARCH EVIDENCE (Primary Source)\n"
            f"{primary_evidence}\n\n"
            "**Note**: No knowledge graph inspiration paths were retrieved. Please rely on the vector search evidence above."
        )
    
    # ===== PRINT FOR INSPECTION =====
    print("\n" + "=" * 100)
    print("🔍 RAG RETRIEVAL - THREE STRUCTURED PARTS")
    print("=" * 100)
    print(f"Query: {query}")
    print(f"Part 1 (Primary Evidence) Length: {len(primary_evidence)} chars")
    print(f"Part 2 (Graph Inspiration) Length: {len(graph_inspiration)} chars")
    print(f"Part 3 (Structured Context) Length: {len(structured_context)} chars")
    print("=" * 100)
    
    print("\n[PART 1: PRIMARY EVIDENCE - Vector Search Results]")
    print("-" * 100)
    print(primary_evidence)  # 完整打印，不截断
    print("-" * 100)
    
    print("\n[PART 2: GRAPH INSPIRATION PATHS - Knowledge Graph Skeleton]")
    print("-" * 100)
    if graph_inspiration:
        print("✅ Knowledge graph inspiration paths retrieved:")
        print(graph_inspiration)  # 完整打印，不截断
    else:
        print("⚠️ No knowledge graph inspiration paths retrieved")
    print("-" * 100)
    
    print("\n[PART 3: STRUCTURED CONTEXT - For Next Agent]")
    print("-" * 100)
    print(structured_context)  # 完整打印，不截断
    print("-" * 100)
    print("=" * 100 + "\n")
    # ===== END PRINT =====
    
    # Return structured context (ready for next agent, with graph as skeleton)
    return structured_context
