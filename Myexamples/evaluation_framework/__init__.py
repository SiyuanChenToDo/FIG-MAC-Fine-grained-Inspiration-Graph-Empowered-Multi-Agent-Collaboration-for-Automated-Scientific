"""
FIG-MAC Evaluation Framework v2.0

Unified evaluation system for scientific hypothesis generation.
Supports multi-method batch evaluation with comprehensive metrics.

Key Metrics:
- ON_v2: Overall Novelty (HD, CD, CI, ON_raw, ON_normalized)
- P: Provenance-Adjusted Novelty (S_src, U_src, G, P) for RAG systems
- LLM: 5-dimensional subjective evaluation (Novelty, Significance, Effectiveness, Clarity, Feasibility)

Author: FIG-MAC Team
"""

__version__ = "2.0.0"
__author__ = "FIG-MAC Team"

from .core.metrics_calculator import ScientificMetricsCalculator
from .core.llm_evaluator import ScientificLLMEvaluator
from .core.batch_evaluator import BatchEvaluator

__all__ = [
    "ScientificMetricsCalculator",
    "ScientificLLMEvaluator", 
    "BatchEvaluator",
]
