"""
Scientific Metrics Calculator - Core Module (FIXED VERSION)
Implements ON_v3 (Overall Novelty) and P (Provenance-Adjusted) metrics.

CHANGES FROM ON_v2:
1. HD: Now takes MAXIMUM dissimilarity (not minimum) - measures true historical divergence
2. CI: Uses citation percentile rank (not year-normalized) - eliminates temporal bias  
3. ON_raw: Linear formula without log compression - respects citation differences
4. All text preserved without truncation

Metrics Overview:
- HD: Historical Dissimilarity - distance from past research [0, 1], higher = more novel vs history
- CD: Contemporary Dissimilarity - distance from current research [0, 1], lower = more feasible
- CI: Contemporary Impact - citation percentile rank [0, 1], higher = more important topic
- ON_raw: Overall Novelty raw score = HD * CI / (CD + delta)
- ON: Normalized novelty score (rank-based) = rank / N

Provenance Metrics (for RAG-based systems):
- S_src: Source similarity [0, 1], lower = less replication of sources
- U_src: Source diversity [0, 1], higher = more cross-domain sources
- G: Provenance factor [0, 1], combined quality of source usage
- P: Provenance-adjusted novelty = ON_raw * (gamma * G + (1 - gamma))

Note: This implementation uses CSV metadata file instead of JSON.
"""

import os
import re
import csv
import numpy as np
from typing import List, Dict, Tuple, Optional
from camel.storages import FaissStorage, VectorDBQuery
from camel.embeddings import OpenAICompatibleEmbedding


class ScientificMetricsCalculator:
    """
    Calculator for objective scientific hypothesis metrics.
    
    Implements the ON_v3 evaluation scheme with citation percentile ranking
    and provenance-adjusted novelty (P metric) for RAG-based systems.
    
    Key improvements over ON_v2:
    1. HD calculation uses maximum dissimilarity to measure true historical divergence
    2. CI uses citation percentile rank to eliminate year-based normalization bias
    3. Linear ON_raw formula without logarithmic compression
    """
    
    # Default configuration
    DEFAULT_K = 10  # Increased from 5 for more stable estimates
    DEFAULT_SEARCH_K = 500  # Initial retrieval size
    CONTEMPORARY_CUTOFF = 2022  # Year threshold for contemporary papers
    DEFAULT_DELTA = 1e-6  # Small constant to prevent division by zero
    
    def __init__(self, 
                 vdb_path: str, 
                 csv_data_path: str,
                 embedding_model: Optional[OpenAICompatibleEmbedding] = None,
                 k: int = DEFAULT_K,
                 contemporary_cutoff: int = CONTEMPORARY_CUTOFF):
        """
        Initialize the metrics calculator.
        
        Args:
            vdb_path: Path to FAISS vector database
            csv_data_path: Path to metadata CSV with citation/year info
            embedding_model: Pre-initialized embedding model (optional)
            k: Top-K neighbors for metric calculation (default: 10)
            contemporary_cutoff: Year threshold for contemporary papers
        """
        self.vdb_path = vdb_path
        self.csv_data_path = csv_data_path
        self.embedding_model = embedding_model
        self.k = k
        self.contemporary_cutoff = contemporary_cutoff
        
        # Storage and lookups
        self.abstract_storage: Optional[FaissStorage] = None
        self.citation_lookup: Dict[str, int] = {}
        self.year_lookup: Dict[str, int] = {}
        self.year_citation_distributions: Dict[int, List[int]] = {}  # For percentile calculation
        
        # Initialize resources
        self._load_resources()
    
    def _load_resources(self):
        """Load vector database and metadata from CSV."""
        print(f"[MetricsCalculator] Loading resources...")
        
        # 1. Load metadata from CSV
        self._load_metadata_from_csv()
        
        # 2. Load vector database
        self._load_vector_db()
        
        print(f"[MetricsCalculator] Resources loaded successfully.")
    
    def _load_metadata_from_csv(self):
        """Load citation and year metadata from CSV file with citation distribution for percentile calculation."""
        if not os.path.exists(self.csv_data_path):
            print(f"⚠️ Metadata CSV not found: {self.csv_data_path}")
            return
        
        try:
            year_citations: Dict[int, List[int]] = {}
            count = 0
            
            with open(self.csv_data_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Use DOI or title as paper ID
                    paper_id = row.get('doi', '') or row.get('title', '')
                    if not paper_id:
                        continue
                    
                    count += 1
                    
                    # Parse citations
                    try:
                        citations = int(row.get('citationcount', 0))
                    except (ValueError, TypeError):
                        citations = 0
                    self.citation_lookup[paper_id] = citations
                    
                    # Parse year
                    try:
                        year = int(row.get('year', 2020))
                    except (ValueError, TypeError):
                        year = 2020
                    self.year_lookup[paper_id] = year
                    
                    # Also index by title for matching
                    title = row.get('title', '')
                    if title:
                        self.citation_lookup[title] = citations
                        self.year_lookup[title] = year
                    
                    # Collect citation distribution by year for percentile calculation
                    if year not in year_citations:
                        year_citations[year] = []
                    year_citations[year].append(citations)
            
            # Store citation distributions for percentile calculation
            self.year_citation_distributions = year_citations
            
            print(f"  ✓ Loaded metadata for {count} papers from CSV")
            print(f"  ✓ Built citation distributions for {len(year_citations)} years")
            
        except Exception as e:
            print(f"⚠️ Error loading CSV metadata: {e}")
    
    def _get_citation_percentile(self, citations: int, year: int) -> float:
        """
        Calculate citation percentile rank for a given paper.
        
        Args:
            citations: Number of citations
            year: Publication year
            
        Returns:
            Percentile rank [0, 1] - 1.0 means top 1% most cited
        """
        if year not in self.year_citation_distributions:
            return 0.5  # Default neutral if year not found
        
        distribution = self.year_citation_distributions[year]
        if not distribution:
            return 0.5
        
        # Calculate percentile: proportion of papers with fewer citations
        count_below = sum(1 for c in distribution if c < citations)
        percentile = count_below / len(distribution)
        
        return percentile
    
    def _load_vector_db(self):
        """Load FAISS vector database."""
        # Try different paths
        possible_paths = [
            os.path.join(self.vdb_path, "paper", "abstract"),
            os.path.join(self.vdb_path, "abstract"),
            self.vdb_path,
        ]
        
        for storage_path in possible_paths:
            if os.path.exists(storage_path):
                try:
                    # Determine collection name
                    collection_name = "paper_abstract"
                    if not os.path.exists(os.path.join(storage_path, "paper_abstract.index")):
                        collection_name = "abstract"
                    
                    self.abstract_storage = FaissStorage(
                        vector_dim=1536,
                        storage_path=storage_path,
                        collection_name=collection_name
                    )
                    self.abstract_storage.load()
                    print(f"  ✓ Loaded vector DB from {storage_path}")
                    return
                except Exception as e:
                    print(f"  ⚠️ Failed to load from {storage_path}: {e}")
                    continue
        
        print(f"⚠️ Could not load vector database from {self.vdb_path}")
    
    def calculate_novelty_metrics(self, hypothesis_text: str) -> Dict:
        """
        Calculate ON_v3 novelty metrics with corrected formulas.
        
        KEY FIXES:
        1. HD now uses MAXIMUM dissimilarity (measures true historical divergence)
        2. CI uses citation percentile rank (eliminates year bias)
        3. ON_raw uses linear formula without log compression
        
        Args:
            hypothesis_text: The hypothesis text to evaluate
            
        Returns:
            Dictionary containing HD, CD, CI, ON_raw metrics
        """
        if not self.abstract_storage:
            return {"error": "Vector database not loaded"}
        
        if not self.embedding_model:
            return {"error": "Embedding model not provided"}
        
        # 1. Embed hypothesis (limit to 4000 chars for efficiency)
        text_to_embed = hypothesis_text[:4000] if len(hypothesis_text) > 4000 else hypothesis_text
        query_vec = self.embedding_model.embed(obj=text_to_embed)
        query_vec = np.array(query_vec, dtype=np.float32)
        
        # 2. Retrieve neighbors
        query_obj = VectorDBQuery(query_vector=query_vec, top_k=self.DEFAULT_SEARCH_K)
        results = self.abstract_storage.query(query_obj)
        
        # 3. Partition by time period
        past_dissimilarities = []
        contemp_dissimilarities = []
        contemp_papers = []  # (dissimilarity, citations, paper_id, year, citation_percentile)
        
        for res in results:
            payload = res.record.payload
            paper_id = payload.get("paper_id") or payload.get("source_id") or payload.get("title", "")
            
            year = self.year_lookup.get(paper_id, 2020)
            citations = self.citation_lookup.get(paper_id, 0)
            
            # Calculate citation percentile (NEW: replaces year-normalized CI)
            citation_percentile = self._get_citation_percentile(citations, year)
            
            # Calculate dissimilarity
            similarity = res.similarity
            dissimilarity = max(0.0, 1.0 - similarity)
            
            if year >= self.contemporary_cutoff:
                contemp_dissimilarities.append(dissimilarity)
                contemp_papers.append((dissimilarity, citations, paper_id, year, citation_percentile))
            else:
                past_dissimilarities.append(dissimilarity)
        
        # 4. Calculate metrics with FIXED formulas
        metrics = self._compute_metrics_fixed(
            past_dissimilarities,
            contemp_dissimilarities,
            contemp_papers
        )
        
        return metrics
    
    def _compute_metrics_fixed(self, 
                               past_dissimilarities: List[float],
                               contemp_dissimilarities: List[float],
                               contemp_papers: List[Tuple[float, int, str, int, float]]) -> Dict:
        """
        Compute HD, CD, CI, ON_raw with CORRECTED formulas.
        
        FIXED FORMULAS:
        - HD = mean(top-K LARGEST past dissimilarities)  [FIXED: was taking smallest]
        - CD = mean(top-K smallest contemporary dissimilarities)  [unchanged]
        - CI = mean(citation_percentiles)  [FIXED: was year-normalized raw citations]
        - ON_raw = HD * CI / (CD + delta)  [FIXED: removed log compression]
        
        Args:
            past_dissimilarities: List of dissimilarities to past papers
            contemp_dissimilarities: List of dissimilarities to contemporary papers
            contemp_papers: List of (dissimilarity, citations, paper_id, year, citation_percentile)
            
        Returns:
            Dictionary with corrected metrics
        """
        # HD: Historical Dissimilarity - FIXED: use K LARGEST (most different from history)
        if past_dissimilarities and len(past_dissimilarities) >= self.k:
            past_dissimilarities.sort(reverse=True)  # Sort descending for maximum
            hd = np.mean(past_dissimilarities[:self.k])
            past_count = len(past_dissimilarities)
        elif past_dissimilarities:
            hd = np.mean(past_dissimilarities)
            past_count = len(past_dissimilarities)
        else:
            hd = 0.5  # Default neutral value
            past_count = 0
        
        # CD and CI: Contemporary metrics
        if contemp_papers and len(contemp_papers) >= self.k:
            # Sort by dissimilarity (ascending - most similar first)
            contemp_papers.sort(key=lambda x: x[0])
            top_contemp = contemp_papers[:self.k]
            
            # CD: Average dissimilarity of top-K contemporary papers
            cd = np.mean([x[0] for x in top_contemp])
            
            # CI: FIXED - Use citation percentile rank (not year-normalized raw citations)
            ci_values = [x[4] for x in top_contemp]  # citation_percentile
            raw_citations = [x[1] for x in top_contemp]  # For reporting only
            
            ci_percentile = np.mean(ci_values)
            raw_ci = np.mean(raw_citations)
            contemp_count = len(contemp_papers)
            
        elif contemp_papers:
            # Not enough papers, use all available
            cd = np.mean([x[0] for x in contemp_papers])
            ci_percentile = 0.5  # Neutral value
            raw_ci = 0
            contemp_count = len(contemp_papers)
        else:
            cd = 0.5
            ci_percentile = 0.0
            raw_ci = 0.0
            contemp_count = 0
        
        # ON_raw: FIXED - Linear formula without log compression
        # Formula: reward high HD (different from past), high CI (important topic), low CD (close to current)
        on_raw = (hd * ci_percentile) / (cd + self.DEFAULT_DELTA)
        
        return {
            "HD": float(hd),
            "CD": float(cd),
            "CI": float(ci_percentile),  # Now [0, 1] percentile rank
            "ON_raw": float(on_raw),
            "stats": {
                "past_papers": past_count,
                "contemp_papers": contemp_count,
                "top_contemp_citations": float(raw_ci),
                "ci_calculation_method": "percentile_rank",  # Document the fix
            }
        }
    
    def calculate_provenance_metrics(self,
                                     hypothesis_text: str,
                                     source_documents: Optional[List[str]] = None,
                                     alpha: float = 0.5,
                                     beta: float = 0.5,
                                     gamma: float = 0.7) -> Optional[Dict]:
        """
        Calculate provenance-adjusted metrics (P metric) for RAG-based systems.
        
        This measures whether the hypothesis shows genuine cross-source innovation
        versus simple replication of source documents.
        
        Formulas:
        - S_src = mean(cosine_similarity(hypothesis, sources)) - lower is better (less replication)
        - U_src = mean(dissimilarity between source pairs) - higher is better (more diverse)
        - G = alpha * (1 - S_src) + beta * U_src - provenance quality factor
        - P = ON_raw * (gamma * G + (1 - gamma)) - adjusted novelty
        
        Args:
            hypothesis_text: The generated hypothesis
            source_documents: List of source document texts (from RAG retrieval)
            alpha: Weight for source similarity (avoid replication), default 0.5
            beta: Weight for source diversity (cross-domain), default 0.5
            gamma: Weight for combining ON with G, default 0.7
            
        Returns:
            Dictionary with S_src, U_src, G, and P metrics, or None if no sources
        """
        if not source_documents or len(source_documents) == 0:
            return None
        
        if not self.embedding_model:
            return {"error": "Embedding model not provided"}
        
        # Limit hypothesis text length
        h_text = hypothesis_text[:4000] if len(hypothesis_text) > 4000 else hypothesis_text
        
        # Embed hypothesis
        h_emb = np.array(self.embedding_model.embed(obj=h_text), dtype=np.float32)
        h_emb = h_emb / (np.linalg.norm(h_emb) + 1e-10)
        
        # Embed sources (limit to top 20 for efficiency)
        source_embs = []
        for doc in source_documents[:20]:
            doc_text = doc[:1000] if len(doc) > 1000 else doc  # Limit each source
            emb = np.array(self.embedding_model.embed(obj=doc_text), dtype=np.float32)
            emb = emb / (np.linalg.norm(emb) + 1e-10)
            source_embs.append(emb)
        
        M = len(source_embs)
        if M == 0:
            return None
        
        # S_src: Source similarity - how much does hypothesis replicate sources?
        # Lower is better (avoid simple replication)
        similarities = [np.dot(h_emb, s_emb) for s_emb in source_embs]
        S_src = np.mean(similarities)
        
        # U_src: Source diversity - how diverse are the sources themselves?
        # Higher is better (promote cross-domain innovation)
        if M > 1:
            diversities = []
            for i in range(M):
                for j in range(i + 1, M):
                    dissim = max(0.0, 1.0 - np.dot(source_embs[i], source_embs[j]))
                    diversities.append(dissim)
            U_src = np.mean(diversities) if diversities else 0.0
        else:
            U_src = 0.0  # Single source has no diversity
        
        # G: Provenance factor - combine low replication and high diversity
        S_src_norm = np.clip(S_src, 0.0, 1.0)
        U_src_norm = np.clip(U_src, 0.0, 1.0)
        G = alpha * (1.0 - S_src_norm) + beta * U_src_norm
        G = np.clip(G, 0.0, 1.0)
        
        return {
            "S_src": float(S_src),
            "U_src": float(U_src),
            "G": float(G),
            "alpha": alpha,
            "beta": beta,
            "gamma": gamma,
            "source_count": M,
        }
    
    def evaluate(self,
                 hypothesis_text: str,
                 source_documents: Optional[List[str]] = None,
                 calculate_p: bool = True) -> Dict:
        """
        Complete evaluation with all metrics using FIXED formulas.
        
        Args:
            hypothesis_text: The hypothesis to evaluate
            source_documents: Optional source documents for P metric
            calculate_p: Whether to calculate provenance metrics
            
        Returns:
            Complete evaluation results with corrected ON_v3 metrics
        """
        # Objective metrics with fixed formulas
        novelty_metrics = self.calculate_novelty_metrics(hypothesis_text)
        
        # Provenance metrics
        provenance_metrics = None
        if calculate_p and source_documents:
            provenance_metrics = self.calculate_provenance_metrics(
                hypothesis_text, source_documents
            )
            
            # Calculate P if we have both ON_raw and G
            if provenance_metrics and "error" not in provenance_metrics:
                on_raw = novelty_metrics.get("ON_raw")
                G = provenance_metrics.get("G")
                gamma = provenance_metrics.get("gamma", 0.7)
                
                if on_raw is not None and G is not None:
                    P = on_raw * (gamma * G + (1 - gamma))
                    provenance_metrics["P"] = float(P)
        
        return {
            "novelty": novelty_metrics,
            "provenance": provenance_metrics,
        }
    
    @staticmethod
    def normalize_on_scores(results: List[Dict]) -> List[Dict]:
        """
        Apply rank-based normalization to ON scores across multiple hypotheses.
        
        Formula: ON_normalized = rank / N
        where rank=1 is lowest (worst), rank=N is highest (best)
        Range: [1/N, 1] - ensures all hypotheses get non-zero scores
        
        Args:
            results: List of evaluation results with ON_raw values
            
        Returns:
            Results with added ON_normalized field
        """
        # Extract ON_raw values with indices
        on_raw_list = []
        for idx, result in enumerate(results):
            novelty = result.get("novelty", {})
            on_raw = novelty.get("ON_raw")
            if on_raw is not None and isinstance(on_raw, (int, float)) and not isinstance(on_raw, str):
                on_raw_list.append((on_raw, idx))
        
        if len(on_raw_list) < 2:
            print("⚠️ Need at least 2 results for normalization")
            return results
        
        # Sort by ON_raw (ascending - lowest first)
        sorted_list = sorted(on_raw_list, key=lambda x: x[0])
        
        # Assign ranks and normalize
        N = len(sorted_list)
        for rank, (on_raw, original_idx) in enumerate(sorted_list, start=1):
            # Formula: rank / N (range [1/N, 1])
            normalized_on = rank / N
            results[original_idx]["novelty"]["ON"] = normalized_on
            results[original_idx]["novelty"]["rank"] = rank
            results[original_idx]["novelty"]["N"] = N
        
        print(f"✅ Normalized {N} ON scores (range: [{1/N:.4f}, 1.0])")
        return results
