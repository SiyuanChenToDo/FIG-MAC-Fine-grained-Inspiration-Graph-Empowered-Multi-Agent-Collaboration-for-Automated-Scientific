import os
import json
import numpy as np
import torch
from typing import List, Dict, Tuple
from camel.storages import FaissStorage, VectorDBQuery
from camel.embeddings import OpenAICompatibleEmbedding
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.configs import QwenConfig
from camel.agents import ChatAgent
from camel.messages import BaseMessage

class ScientificMetricsCalculator:
    def __init__(self, vdb_path: str, embedding_model=None):
        self.vdb_path = vdb_path
        self.embedding_model = embedding_model
        self.abstract_storage = None
        self.citation_lookup = {}
        self.year_lookup = {}
        self.year_avg_citations = {}  # Cache for year-wise average citations
        
        # Configuration for "Contemporary"
        self.current_year = 2025
        self.contemporary_cutoff = 2022 # Papers >= 2022 are contemporary
        
        # LLM for Text Quality Evaluation (replacing Perplexity)
        self.eval_model = None

    def load_resources(self, json_data_path: str):
        """Load citation and year metadata from the main JSON file with error tolerance."""
        print(f"Loading metadata from {json_data_path}...")
        
        raw_data = None
        try:
            with open(json_data_path, 'r', encoding='utf-8') as f:
                # Attempt standard load
                raw_data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"⚠️ Warning: JSON file is corrupted at line {e.lineno}, col {e.colno}. Attempting to recover valid data...")
            # Try to read file content as string and fix or parse partially
            try:
                with open(json_data_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Use the successfully parsed content up to the error? 
                    # Without complex parsing logic, this is hard.
                    # Instead, let's rely on whatever data we might have loaded if using a stream parser
                    # For now, we fail gracefully for metadata.
                    print("  -> Could not recover automatically. Metadata (Year/Citations) will be unavailable.")
            except Exception as sub_e:
                print(f"  -> Recovery failed: {sub_e}")
        except Exception as e:
            print(f"Error loading metadata: {e}")

        if raw_data:
            self._process_metadata(raw_data)
        
        # Load Vector DB (assuming abstract collection exists)
        print("Loading Abstract Vector Storage...")
        storage_path = os.path.join(self.vdb_path, "paper", "abstract")
        if not os.path.exists(storage_path):
             storage_path = os.path.join(self.vdb_path, "abstract") # Fallback to old structure
        
        if os.path.exists(storage_path):
            self.abstract_storage = FaissStorage(
                vector_dim=1536, 
                storage_path=storage_path,
                collection_name="paper_abstract" if os.path.exists(os.path.join(storage_path, "paper_abstract.index")) else "abstract"
            )
            self.abstract_storage.load()
        else:
            print(f"Warning: Abstract storage not found at {storage_path}")

    def _process_metadata(self, data):
        """Helper to process loaded JSON data"""
        count = 0
        year_citations = {}  # Temporary storage for computing year averages
        
        for entity in data.get("entities", []):
            if entity.get("entity_type") == "paper":
                paper_id = entity.get("source_id") or entity.get("title")
                if paper_id:
                    count += 1
                    citations = entity.get("citationCount", 0)
                    self.citation_lookup[paper_id] = citations
                    
                    # Handle string years
                    try:
                        year = int(entity.get("year", 2020))
                    except:
                        year = 2020
                    self.year_lookup[paper_id] = year
                    
                    # Collect for year-wise average
                    if year not in year_citations:
                        year_citations[year] = []
                    year_citations[year].append(citations)
        
        # Compute year-wise average citations (for CI normalization in ON_v2)
        for year, citations in year_citations.items():
            self.year_avg_citations[year] = np.mean(citations) if citations else 1.0
        
        print(f"✅ Successfully loaded metadata for {count} papers.")
        print(f"   Computed average citations for {len(self.year_avg_citations)} years.")

    def _evaluate_text_quality(self, text: str) -> float:
        """
        Estimate text quality (Fluency/Coherence) using LLM as a Judge.
        Returns a score from 0 to 1.
        """
        if self.eval_model is None:
            print("Initializing LLM for Text Quality Evaluation...")
            try:
                self.eval_model = ModelFactory.create(
                    model_platform=ModelPlatformType.QWEN,
                    model_type=ModelType.QWEN_MAX,
                    model_config_dict=QwenConfig(temperature=0.1).as_dict(),
                    api_key=os.environ.get("QWEN_API_KEY"),
                    url=os.environ.get("QWEN_API_BASE_URL"),
                )
            except Exception as e:
                print(f"Failed to load Evaluation Model: {e}")
                return 0.0

        # Increased from 1000 to 2000 for more comprehensive fluency evaluation
        text_sample = text[:2000] if len(text) > 2000 else text
        prompt = f"""
        Evaluate the linguistic quality of the following scientific text snippet comprehensively.
        Focus ONLY on:
        1. Fluency (Is it grammatical and natural? Are sentences well-formed?)
        2. Coherence (Do the sentences flow logically? Is the structure clear?)
        
        Text:
        "{text_sample}"
        
        Rate the overall quality on a scale of 1 to 10 (10 being perfect academic English).
        Consider the complete text structure, technical precision, and academic writing standards.
        Return ONLY the number.
        """
        
        try:
            agent = ChatAgent(
                system_message=BaseMessage.make_assistant_message(
                    role_name="Linguist", 
                    content="You are an expert linguistic evaluator."
                ),
                model=self.eval_model
            )
            msg = BaseMessage.make_user_message(role_name="User", content=prompt)
            response = agent.step(msg)
            
            content = response.msg.content.strip()
            import re
            match = re.search(r'\d+(\.\d+)?', content)
            if match:
                score = float(match.group(0))
                return min(max(score, 1.0), 10.0) / 10.0
            return 0.5
            
        except Exception as e:
            print(f"Error in text quality evaluation: {e}")
            return 0.0

    def calculate_novelty_metrics(self, generated_abstract: str, k: int = 20) -> Dict:
        """
        Compute HD, CD, CI, ON based on the generated abstract.
        """
        if not self.abstract_storage or not self.embedding_model:
            return {"error": "Storage or Model not initialized"}

        # Check if we have metadata
        if not self.year_lookup:
            return {
                "Error": "Metadata (Year/Citation) not loaded. Cannot compute HD/CD/CI.",
                "Fluency_Score": 0.0, # Placeholder
                "Stats": {"Vectors_Found": 0}
            }

        # 1. Embed the generated abstract
        query_vec = self.embedding_model.embed(obj=generated_abstract)
        query_vec = np.array(query_vec, dtype=np.float32)

        # 2. Aggressive Search
        search_k = 500
        query_obj = VectorDBQuery(query_vector=query_vec, top_k=search_k)
        results = self.abstract_storage.query(query_obj)

        past_dists = []
        contemp_dists = []
        contemp_citations = []
        contemp_paper_ids = []  # Track paper IDs for year-normalized CI

        for res in results:
            payload = res.record.payload
            paper_id = payload.get("paper_id") or payload.get("source_id")
            
            # IMPORTANT: If paper_id is not in metadata, we default to 2020 (Past)
            # This might skew results if metadata is partial.
            year = self.year_lookup.get(paper_id, 2020)
            citations = self.citation_lookup.get(paper_id, 0)
            
            similarity = res.similarity
            dissimilarity = 1.0 - similarity 
            if dissimilarity < 0: dissimilarity = 0

            if year >= self.contemporary_cutoff:
                contemp_dists.append(dissimilarity)
                contemp_citations.append(citations)
                contemp_paper_ids.append(paper_id)
            else:
                past_dists.append(dissimilarity)

        # 3. Compute Metrics (ON_v2 Implementation)
        top_k_metric = 5
        
        # HD (Historical Dissimilarity)
        past_dists.sort()
        if past_dists:
            final_past_dists = past_dists[:top_k_metric]
            hd = np.mean(final_past_dists)
        else:
            hd = 0.5

        # CD & CI (Contemporary Dissimilarity & Citation Impact)
        contemp_tuples = []
        if len(contemp_dists) > 0:
            # Create tuples of (dissimilarity, citations, paper_id)
            for d, c, pid in zip(contemp_dists, contemp_citations, contemp_paper_ids):
                contemp_tuples.append((d, c, pid))
            
            # Sort by dissimilarity (ascending)
            contemp_tuples.sort(key=lambda x: x[0])
            top_contemp = contemp_tuples[:top_k_metric]
            
            # CD: Average dissimilarity of top-K
            cd = np.mean([x[0] for x in top_contemp])
            
            # CI (ON_v2 with year normalization): Average of (citations / μ_year)
            ci_normalized_values = []
            raw_citations = []
            for d, c, pid in top_contemp:
                year = self.year_lookup.get(pid, self.contemporary_cutoff)
                year_avg = self.year_avg_citations.get(year, 1.0)
                # Normalize citation by year average
                ci_normalized_values.append(c / max(year_avg, 1.0))
                raw_citations.append(c)
            
            # CI is the average of normalized citations
            ci_normalized = np.mean(ci_normalized_values)
            raw_ci = np.mean(raw_citations)  # For stats reporting
            
        else:
            cd = 0.5 
            ci_normalized = 0.0
            raw_ci = 0.0

        # ON_v2 Formula: ON_raw = HD × log(1 + CI_normalized) / (CD + δ)
        delta = 1e-6  # Small constant to prevent division by zero
        on_raw = (hd * np.log1p(ci_normalized)) / (cd + delta) 

        return {
            "HD (Historical Dissimilarity)": float(hd),
            "CD (Contemporary Dissimilarity)": float(cd),
            "CI (Contemporary Impact, Year-Normalized)": float(ci_normalized),
            "ON_raw (Overall Novelty - Raw)": float(on_raw),
            "ON (Overall Novelty - Normalized)": None,  # Will be computed after ranking
            "Stats": {
                "Past_Neighbors_Found": len(past_dists),
                "Contemp_Neighbors_Found": len(contemp_dists),
                "Top_Contemporary_Raw_Citations": float(raw_ci),
                "Top_Contemporary_Normalized_CI": float(ci_normalized)
            }
        }

    def calculate_provenance_metrics(self, hypothesis_text: str, source_documents: List[str] = None, 
                                    alpha: float = 0.5, beta: float = 0.5, gamma: float = 0.7) -> Dict:
        """
        Calculate Provenance-Adjusted Novelty (P) metrics.
        
        Args:
            hypothesis_text: The generated hypothesis text
            source_documents: List of source document texts used in generation
                            - For RAG systems: retrieved paper abstracts/content
                            - For non-RAG systems: prompt text or empty list
            alpha (α): Weight for source similarity (避免复述), default 0.5, range [0, 1]
                      - Lower S_src is better (avoid simple copying)
                      - Can be adjusted based on application scenario
            beta (β): Weight for source diversity (来源多样), default 0.5, range [0, 1]
                     - Higher U_src is better (promote cross-domain innovation)
                     - Can be adjusted based on application scenario
            gamma (γ): Weight for combining ON with G, default 0.7, range [0, 1]
                      - Controls how much provenance quality affects final P score
                      - Higher γ means provenance quality is more important
            
        Returns:
            Dict with P, S_src, U_src, G metrics
        """
        if not self.embedding_model:
            return {"Error": "Embedding model not initialized"}
        
        # If no source documents provided, treat as non-RAG system
        if not source_documents or len(source_documents) == 0:
            return {
                "P (Provenance-Adjusted Novelty)": None,
                "S_src (Source Similarity)": 0.0,
                "U_src (Source Diversity)": 0.0,
                "G (Provenance Factor)": 1.0,
                "Note": "No source documents provided (non-RAG system)"
            }
        
        # Embed hypothesis
        h_emb = np.array(self.embedding_model.embed(obj=hypothesis_text), dtype=np.float32)
        h_emb = h_emb / (np.linalg.norm(h_emb) + 1e-10)  # Normalize
        
        # Embed source documents
        source_embs = []
        for doc in source_documents[:20]:  # Limit to top 20 sources for efficiency
            emb = np.array(self.embedding_model.embed(obj=doc[:1000]), dtype=np.float32)
            emb = emb / (np.linalg.norm(emb) + 1e-10)
            source_embs.append(emb)
        
        M = len(source_embs)
        
        # 1. Source Similarity: How much does hypothesis replicate sources?
        #    S_src = (1/M) × Σ cos(e_h, e_p_j)
        similarities = [np.dot(h_emb, s_emb) for s_emb in source_embs]
        S_src = np.mean(similarities) if similarities else 0.0
        
        # 2. Source Diversity: How diverse are the sources themselves?
        #    U_src = (2 / M(M-1)) × Σ_{i<j} d(e_p_i, e_p_j)
        if M > 1:
            diversities = []
            for i in range(M):
                for j in range(i+1, M):
                    dissimilarity = 1.0 - np.dot(source_embs[i], source_embs[j])
                    dissimilarity = max(0.0, dissimilarity)  # Ensure non-negative
                    diversities.append(dissimilarity)
            U_src = np.mean(diversities)
        else:
            U_src = 0.0  # Single source has no diversity
        
        # Normalize S_src and U_src to [0, 1] for stable G computation
        S_src_norm = np.clip(S_src, 0.0, 1.0)
        U_src_norm = np.clip(U_src, 0.0, 1.0)
        
        # 3. Provenance Factor G: Reward low replication + high source diversity
        #    G = α(1 - S_src') + β U_src'
        G = alpha * (1.0 - S_src_norm) + beta * U_src_norm
        G = np.clip(G, 0.0, 1.0)  # Ensure [0, 1]
        
        return {
            "S_src (Source Similarity)": float(S_src),
            "U_src (Source Diversity)": float(U_src),
            "G (Provenance Factor)": float(G),
            "Source_Count": M,
            "Params": {
                "alpha": alpha,
                "beta": beta,
                "gamma": gamma
            }
        }

    def evaluate_text(self, text: str, source_documents: List[str] = None) -> Dict:
        """
        Universal evaluation method.
        
        Args:
            text: Text to evaluate
            source_documents: Optional list of source documents for P metric calculation
        """
        # Increased from 2000 to 4000 for more comprehensive evaluation
        # This ensures we capture more complete information for better metrics
        eval_text = text[:4000]
        print(f"Extracted text for embedding (length {len(eval_text)})...")

        fluency_score = self._evaluate_text_quality(eval_text)
        novelty = self.calculate_novelty_metrics(eval_text)
        
        # Calculate Provenance metrics if sources provided
        provenance = None
        if source_documents is not None:
            print(f"Calculating Provenance metrics with {len(source_documents)} source documents...")
            provenance = self.calculate_provenance_metrics(eval_text, source_documents)
            
            # Compute P if we have ON_raw
            on_raw = novelty.get("ON_raw (Overall Novelty - Raw)")
            if on_raw is not None and provenance.get("G (Provenance Factor)") is not None:
                gamma = provenance["Params"]["gamma"]
                G = provenance["G (Provenance Factor)"]
                P = on_raw * (gamma * G + (1 - gamma))
                provenance["P (Provenance-Adjusted Novelty)"] = float(P)

        return {
            "Fluency_Score": fluency_score,
            "Novelty_Metrics": novelty,
            "Provenance_Metrics": provenance
        }
    
    @staticmethod
    def normalize_on_scores(results_list: List[Dict]) -> List[Dict]:
        """
        Apply rank-based normalization to ON scores across multiple hypotheses.
        Formula: ON_normalized = rank / N
        where rank=1 is worst, rank=N is best.
        Range: [1/N, 1] instead of [0, 1]
        
        Args:
            results_list: List of evaluation results, each containing 'metrics'['objective']['Novelty_Metrics']
        
        Returns:
            Updated results_list with normalized ON scores
        """
        # Extract ON_raw values and their indices
        on_raw_values = []
        valid_indices = []
        
        for idx, result in enumerate(results_list):
            try:
                novelty = result.get('metrics', {}).get('objective', {}).get('Novelty_Metrics', {})
                on_raw = novelty.get('ON_raw (Overall Novelty - Raw)')
                
                if on_raw is not None and not isinstance(on_raw, str):  # Valid numeric value
                    on_raw_values.append((on_raw, idx))
                    valid_indices.append(idx)
            except:
                continue
        
        if len(on_raw_values) == 0:
            print("⚠️ No valid ON_raw values found for normalization.")
            return results_list
        
        # Sort by ON_raw (ascending)
        sorted_values = sorted(on_raw_values, key=lambda x: x[0])
        
        # Assign ranks and compute normalized ON
        N = len(sorted_values)
        # Maps original index to a tuple of (normalized_on, rank)
        score_and_rank_map = {}
        
        for rank, (on_raw, original_idx) in enumerate(sorted_values, start=1):
            # Rank starts from 1, so rank/N gives [1/N, 1]
            normalized_on = rank / N
            score_and_rank_map[original_idx] = (normalized_on, rank)
        
        # Update results with correct rank and score
        for idx in valid_indices:
            normalized_on, rank = score_and_rank_map[idx]
            novelty_metrics = results_list[idx]['metrics']['objective']['Novelty_Metrics']
            novelty_metrics['ON (Overall Novelty - Normalized)'] = normalized_on
            novelty_metrics['Rank'] = rank
            novelty_metrics['Total_Hypotheses'] = N
        
        print(f"✅ Normalized {N} ON scores using improved formula: ON = rank / N")
        return results_list
