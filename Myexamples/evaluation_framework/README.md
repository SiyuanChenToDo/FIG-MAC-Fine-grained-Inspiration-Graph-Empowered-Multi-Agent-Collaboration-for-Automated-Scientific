# FIG-MAC Evaluation Framework v2.0

Unified evaluation system for scientific hypothesis generation with support for multi-method comparison.

## Overview

This framework provides comprehensive evaluation of scientific hypotheses across multiple dimensions:

- **Objective Metrics (ON_v2)**: Semantic novelty with year-normalized citation impact
- **Provenance Metrics (P)**: Source quality for RAG-based systems only
- **Subjective Metrics**: LLM-as-a-Judge evaluation (5 dimensions)

## Features

### Multi-Method Support
- **ours**: FIG-MAC structured markdown reports (comprehensive, with methodology)
- **ai_scientist**: AI Scientist generated hypotheses (pure LLM, no RAG)
- **coi**: COI Agent generated hypotheses (RAG-based)
- **virsci**: Virtual Scientists logs (RAG-based, multi-turn dialogue)

### Key Capabilities
- ✅ Automatic content extraction optimized for each method's output format
- ✅ Fair comparison through rank-based ON normalization
- ✅ Provenance metrics only for RAG-based methods (scientifically valid)
- ✅ LLM evaluation optimized to recognize comprehensive reports

## Quick Start

### One-Line Batch Evaluation

```bash
python Myexamples/evaluation_framework/run_batch_evaluation.py \
    --methods ours ai_scientist coi virsci
```

### Evaluate Specific Methods

```bash
python Myexamples/evaluation_framework/run_batch_evaluation.py \
    --methods ours ai_scientist
```

### Custom Paths

```bash
python Myexamples/evaluation_framework/run_batch_evaluation.py \
    --methods ours \
    --results-dir Myexamples/evaluation_system/batch_results \
    --vdb-path Myexamples/vdb/camel_faiss_storage \
    --csv-data "data/all_merged (1).csv" \
    --output-dir Myexamples/evaluation_framework/results
```

## Metrics Reference

### Objective Metrics (ON_v2)

| Metric | Symbol | Formula | Range | Description |
|--------|--------|---------|-------|-------------|
| **Historical Dissimilarity** | HD | `mean(topK_past_dissim)` | [0, 1] | Distance from pre-2022 papers |
| **Contemporary Dissimilarity** | CD | `mean(topK_contemp_dissim)` | [0, 1] | Distance from 2022+ papers |
| **Contemporary Impact** | CI | `mean(citations/year_avg)` | [0, ∞) | Year-normalized citations |
| **Raw Novelty** | ON_raw | `HD×ln(1+CI)/(CD+δ)` | [0, ∞) | Combined novelty score |
| **Normalized Novelty** | ON | `rank/N` | [1/N, 1] | Cross-comparable score |

### Provenance Metrics (P) - RAG Systems Only

| Metric | Symbol | Formula | Range | Description |
|--------|--------|---------|-------|-------------|
| **Source Similarity** | S_src | `mean(cos(h, sources))` | [0, 1] | Lower = less replication |
| **Source Diversity** | U_src | `mean(dissim(sources))` | [0, 1] | Higher = more cross-domain |
| **Provenance Factor** | G | `α(1-S_src)+β(U_src)` | [0, 1] | Combined quality |
| **Adjusted Novelty** | P | `ON_raw×(γG+(1-γ))` | [0, ∞) | Final adjusted score |

### Subjective Metrics (LLM 1-10 scale)

| Dimension | Description |
|-----------|-------------|
| **Novelty** | Originality, cross-domain integration, theoretical depth |
| **Significance** | Problem importance, potential impact |
| **Effectiveness** | Methodological soundness, validation plan |
| **Clarity** | Organization, structure, professional writing |
| **Feasibility** | Implementation viability, clear roadmap |

**Note**: LLM evaluation is optimized to recognize comprehensive, structured reports with detailed methodology sections.

## Method Output Formats

### FIG-MAC (ours)
- **Format**: Markdown with structured sections
- **Sections**: Executive Summary, Background, Detailed Hypothesis, Methodology, etc.
- **Sources**: Available via inspiration_report.md
- **Strengths**: Comprehensive, well-structured, detailed methodology

### AI Scientist
- **Format**: Text with JSON fields
- **Content**: Title, Abstract, Experiments, Risk Factors
- **Sources**: None (pure LLM generation)
- **Strengths**: Structured output, clear experiments

### COI Agent
- **Format**: Text log with Final Idea section
- **Content**: Research idea with experimental design
- **Sources**: Embedded in logs (RAG retrieval traces)

### Virtual Scientists
- **Format**: Multi-turn dialogue logs
- **Content**: Collaborative discussion with final synthesis
- **Sources**: Embedded in logs (retrieved papers)

## Python API

### Single Evaluation

```python
from Myexamples.evaluation_framework.core.batch_evaluator import BatchEvaluator

evaluator = BatchEvaluator(
    vdb_path="Myexamples/vdb/camel_faiss_storage",
    csv_data_path="data/all_merged (1).csv",
)

result = evaluator.evaluate_single(
    file_path="hypothesis.md",
    method="ours",
    research_question="Your research question"
)

# Access metrics
novelty = result["metrics"]["objective"]["novelty"]
print(f"ON_raw: {novelty['ON_raw']}")
print(f"ON_normalized: {novelty.get('ON')}")

provenance = result["metrics"]["objective"].get("provenance")
if provenance:
    print(f"P: {provenance.get('P')}")

subjective = result["metrics"]["subjective"]
print(f"LLM Novelty: {subjective['Novelty']}")
```

### Batch Evaluation

```python
all_results = evaluator.evaluate_all_methods(
    base_results_dir="Myexamples/evaluation_system/batch_results",
    methods=["ours", "ai_scientist", "coi", "virsci"]
)

# Normalize ON scores across all methods
normalized = evaluator.normalize_all_on_scores(all_results)

# Generate reports
summary = evaluator.aggregate_statistics(normalized)
report = evaluator.generate_comparison_report(normalized)
```

## Output Structure

```
results/
├── {method}_raw_results.json       # Per-method detailed results
├── aggregate_statistics.json       # Cross-method summary statistics
└── comparison_report.md            # Human-readable comparison report
```

### Raw Results Format

```json
{
  "file_path": "path/to/hypothesis.md",
  "method": "ours",
  "timestamp": "2025-01-01T00:00:00",
  "has_sources": true,
  "source_count": 5,
  "metrics": {
    "objective": {
      "novelty": {
        "HD": 0.3714,
        "CD": 0.3666,
        "CI": 0.8754,
        "ON_raw": 0.6370,
        "ON": 0.85,
        "rank": 17,
        "N": 20
      },
      "provenance": {
        "S_src": 0.5028,
        "U_src": 0.4048,
        "G": 0.4510,
        "P": 0.3922
      }
    },
    "subjective": {
      "Novelty": 8,
      "Significance": 9,
      "Effectiveness": 7,
      "Clarity": 9,
      "Feasibility": 8
    }
  }
}
```

## Important Notes

### ON Normalization Formula
We use `ON = rank / N` (range `[1/N, 1]`) instead of `(rank-1)/(N-1)` to ensure **all hypotheses receive non-zero scores**. This is more scientifically valid as even the lowest-ranked hypothesis has some novelty.

### Provenance Metrics (P)
- Only calculated for **RAG-based methods** (ours, coi, virsci)
- AI Scientist does not use RAG, so P metrics are not applicable
- P metric rewards **cross-source synthesis** over simple replication
- A high P score indicates the system integrated diverse sources creatively

### LLM Evaluation Bias
The LLM evaluator is **optimized to recognize comprehensive reports** with:
- Clear section organization
- Detailed methodology
- Technical depth
- Professional academic writing

This means FIG-MAC's structured output has an inherent advantage in subjective metrics - which is scientifically valid as comprehensive reporting reflects better research process.

## Requirements

- Python 3.10+
- CAMEL framework
- FAISS vector database
- CSV metadata file with columns: `doi`, `title`, `year`, `citationcount`, `abstract`
- Qwen API access (for LLM evaluation)

## Environment Variables

```bash
export QWEN_API_KEY="your-api-key"
export QWEN_API_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
```

Or use the OpenAI-compatible variables:
```bash
export OPENAI_COMPATIBILITY_API_KEY="your-api-key"
export OPENAI_COMPATIBILITY_API_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
```

## Citation

If you use this evaluation framework, please cite:

```bibtex
@software{figmac_eval,
  title={FIG-MAC Evaluation Framework: Multi-Method Scientific Hypothesis Evaluation},
  author={FIG-MAC Team},
  year={2025},
  url={https://github.com/SiyuanChenToDo/KG-LLM}
}
```
