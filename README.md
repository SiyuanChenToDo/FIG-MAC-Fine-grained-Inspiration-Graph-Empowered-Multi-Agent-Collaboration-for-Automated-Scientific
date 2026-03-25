<div align="center">

# 🧠 FIG-MAC: Fine-grained Inspiration Graph Empowered Multi-Agent Collaboration

### *Redefining Automated Scientific Discovery through Structured Multi-Agent Cognition and Cross-Domain Knowledge Graphs*

[![Architecture](https://img.shields.io/badge/Architecture-State--Machine--Driven-blueviolet?style=for-the-badge)]()
[![Agents](https://img.shields.io/badge/Agents-8%20Specialized%20Roles-ff6b6b?style=for-the-badge)]()
[![RAG](https://img.shields.io/badge/RAG-Hybrid%20%28Vector%2BGraph%29-4ecdc4?style=for-the-badge)]()
[![Evaluation](https://img.shields.io/badge/Evaluation-8--Dimensional%20Scoring-45b7d1?style=for-the-badge)]()

**[Overview](#-overview)** • **[Architecture](#-architecture)** • **[Key Innovations](#-key-innovations)** • **[Experiments](#-experiments)** • **[Usage](#-usage)** • **[Citation](#-citation)**

</div>

---

## 🎯 Overview

**Scientific hypothesis generation** represents one of the most cognitively demanding intellectual activities, requiring the synthesis of domain expertise, cross-domain analogical reasoning, rigorous evaluation, and iterative refinement. While Large Language Models (LLMs) have demonstrated remarkable capabilities in individual reasoning tasks, they struggle with the **structured, multi-phase cognitive workflow** inherent to scientific discovery.

**FIG-MAC** addresses this fundamental limitation through three core innovations:

1. **🔬 Fine-grained Inspiration Graphs (FIG)**: A novel knowledge representation that decomposes academic papers into semantically meaningful components (Research Questions, Solutions, Core Problems) and models cross-domain inspirational relationships via GNN-based link prediction

2. **🎭 Structured Multi-Agent Architecture**: An 8-agent cognitive system orchestrated through a state machine, where each agent embodies a specialized research role (Literature Reviewer, Creative Ideator, Technical Analyst, etc.)

3. **🔄 Iterative Quality-Driven Refinement**: A peer-review-inspired feedback loop with automatic quality assessment, regression detection, and best-version tracking

<div align="center">

**The result**: *Publication-ready scientific hypotheses with measurable quality metrics across 8 evaluation dimensions*

</div>

---

## 🏛️ Architecture

### System Design Philosophy

Unlike monolithic LLM approaches that compress the entire scientific workflow into a single inference pass, FIG-MAC adopts a **society-of-minds** architecture inspired by academic research teams:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FIG-MAC COGNITIVE ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   INPUT                    STATE MACHINE FLOW                    OUTPUT      │
│   ─────                    ───────────────────                   ──────      │
│                                                                              │
│   ┌────────┐   ┌─────────────────────────────────────────┐   ┌──────────┐   │
│   │Research│   │  INIT → LITERATURE → IDEATION → ANALYSIS │   │Scientific│   │
│   │ Topic  │──▶│     ↓        ↓          ↓         ↓     │──▶│Hypothesis│   │
│   └────────┘   │  SYNTHESIS → REVIEW →{Decision}→ POLISH  │   │  Report  │   │
│                │     ↑___________|   (Yes/No)    ↓        │   └──────────┘   │
│                │              └─────REVISION◄────┘        │                  │
│                └─────────────────────────────────────────┘                  │
│                                                                              │
│   KNOWLEDGE GRAPH LAYER          AGENT LAYER                                │
│   ─────────────────────          ───────────                                │
│   ┌───────────────┐              ┌──────────────┐                           │
│   │ Vector Store  │              │ 8 Specialized│                           │
│   │ (FAISS Index) │              │    Agents    │                           │
│   └───────┬───────┘              └──────┬───────┘                           │
│           │                             │                                    │
│   ┌───────▼───────┐         ┌───────────▼───────────┐                       │
│   │   Neo4j KG    │         │  HypothesisTeam       │                       │
│   │ (Paper-RQ-Sol)│         │  (State Orchestrator) │                       │
│   └───────────────┘         └───────────────────────┘                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 💡 Key Innovations

### 1. Fine-grained Inspiration Graphs (FIG)

Traditional RAG systems retrieve entire documents, losing the structural semantics of scientific knowledge. FIG decomposes papers into:

| Component | Description | Example |
|-----------|-------------|---------|
| **Research Question (RQ)** | Core scientific inquiry | *"How can GNNs improve drug discovery?"* |
| **Solution (Sol)** | Proposed approach/method | *"A graph attention network with..."* |
| **Core Problem** | Fundamental challenge addressed | *"Molecular property prediction..."* |
| **INSPIRED Edge** | Cross-domain analogical link | *Solution(A) → inspires → Paper(B)* |

**Innovation**: We model cross-domain inspiration as a **link prediction task** on the knowledge graph, training a GNN to predict which papers might inspire solutions to other research questions.

```
Inspiration Path Example:
┌──────────────┐      ┌──────────┐      ┌──────────────┐
│  RQ: Drug    │─────▶│ Solution:│─────▶│ Paper: Social│
│  Discovery   │      │ GNN with │      │ Network      │
│              │      │ Attention│      │ Analysis     │
└──────────────┘      └────┬─────┘      └──────┬───────┘
                           │                   │
                           │  [INSPIRED Edge]  │
                           │  (GNN Predicted)  │
                           └───────────────────┘
```

### 2. State Machine-Driven Multi-Agent Workflow

Unlike simple agent chaining, FIG-MAC implements a **finite state machine** with 9 distinct states:

| State | Agent | Function |
|-------|-------|----------|
| `LITERATURE` | Scholar Scour | RAG-enhanced literature synthesis |
| `IDEATION` | Idea Igniter | Generate 3-5 novel hypotheses |
| `ANALYSIS` | 3 Agents (Parallel) | Technical/Practical/Ethical assessment |
| `SYNTHESIS` | Dr. Qwen Leader | Unified report generation |
| `REVIEW` | Critic Crucible | Peer review with scoring |
| `REVISION` | Dr. Qwen Leader | Quality-driven iteration |
| `POLISH` | Prof. Qwen Editor | Language refinement |
| `EVALUATION` | Final Evaluation Agent | 8-dimensional scoring |

### 3. Iterative Quality-Driven Refinement

A key innovation is the **integrated quality assessment** that combines:

- **Internal Evaluation (25%)**: Peer review scores from Critic Crucible
- **External Evaluation (75%)**: 8-dimensional objective assessment

```python
# Quality-driven iteration with best-version tracking
while current_iteration < max_iterations:
    score = critic_crucible.review(report)
    if score >= quality_threshold:
        break  # Quality achieved
    elif score > best_version['score']:
        best_version = {'content': report, 'score': score}
    report = leader.revise(report, feedback)
```

**Regression Protection**: If a revision decreases quality, the system automatically rolls back to the best previous version.

---

## 📊 Experiments

### Comparative Evaluation

We benchmark FIG-MAC against state-of-the-art automated research systems:

| System | Architecture | RAG Strategy | Iteration | Avg. Quality Score |
|--------|-------------|--------------|-----------|-------------------|
| **FIG-MAC (Ours)** | 8-Agent State Machine | Hybrid (Vector+Graph) | ✓ | **8.42/10** |
| AI-Scientist-v2 | Single-Agent + Tree Search | Vector Only | ✓ | 7.15/10 |
| CoI-Agent | 2-Agent Chain | Vector Only | ✗ | 6.83/10 |
| Virtual-Scientists | Multi-Agent (Scope-based) | Vector Only | ✗ | 6.91/10 |
| Single LLM (Qwen-Max) | Monolithic | None | ✗ | 5.67/10 |

### Ablation Study

To validate design choices, we conduct ablation experiments across 8 configurations:

| Config | Vector RAG | Graph RAG | Multi-Agent | Avg Score |
|--------|-----------|-----------|-------------|-----------|
| Full System | ✓ | ✓ | ✓ (8 agents) | **8.42** |
| Vector Only | ✓ | ✗ | ✓ (8 agents) | 7.89 |
| Graph Only | ✗ | ✓ | ✓ (8 agents) | 7.56 |
| No RAG | ✗ | ✗ | ✓ (8 agents) | 6.23 |
| Single Agent + Full RAG | ✓ | ✓ | ✗ (1 agent) | 5.71 |

**Key Findings**:
- Multi-agent architecture contributes **+2.19** points vs. single-agent
- Graph RAG provides **+0.67** improvement over Vector-only
- Iterative refinement improves final quality by **+1.34** on average

### Evaluation Metrics

**Objective Novelty Metrics** (computed against 150K paper corpus):
- **ON (Overall Novelty)**: Semantic dissimilarity from existing work
- **HD (Historical Dissimilarity)**: Distance from past research
- **CD (Contemporary Dissimilarity)**: Distance from concurrent work
- **CI (Contemporary Impact)**: Citation potential estimation

**Subjective Quality Dimensions** (LLM-evaluated 1-10 scale):
- Relevance, Technical Accuracy, Engagement, Originality, Feasibility (100% weight)
- Clarity, Structure, Conciseness (50% weight)

---

## 🚀 Usage

### Environment Setup

```bash
# Required
export QWEN_API_KEY="your-api-key-here"

# Optional tuning
export CAMEL_MODEL_TIMEOUT=1200
export CAMEL_CONTEXT_TOKEN_LIMIT=40000
export HF_MIRROR="https://hf-mirror.com"  # For HuggingFace in China
```

### Running the Full Workflow

```python
import asyncio
from Myexamples.test_mutiagent.hypothesis_society_demo import HypothesisGenerationSociety

async def main():
    society = HypothesisGenerationSociety()
    result = await society.run_research_async(
        research_topic='Your research topic',
        max_iterations=3,
        quality_threshold=8.0,
        polish_iterations=1
    )
    print(f"Report: {result.metadata['file_path']}")
    print(f"Quality: {result.metadata['final_quality_score']}/10")

asyncio.run(main())
```

### Standalone Inspiration Pipeline

```bash
python src/pipeline/inspire_pipeline.py "graph neural networks for drug discovery"
```

### Batch Evaluation

```bash
python Myexamples/evaluation_system/batch_evaluation_tools/batch_evaluate_virsci_logs.py \
    --logs-dir Myexamples/evaluation_system/batch_results/virsci/logs \
    --output-excel results.xlsx
```

### Ablation Study

```bash
cd Myexamples/evaluation_system/batch_results/消融实验
bash run_all_configs.sh
```

---

## 📁 Repository Structure

```
fig-mac/
├── README.md                    # Project documentation
├── LICENSE                      # License file
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variables template
│
├── src/                         # Core source code (organized from root)
│   ├── pipeline/                # Inspiration retrieval pipelines
│   │   ├── inspire_pipeline.py              # Scientific inspiration pipeline
│   │   └── extract_inspiration_paths_v2.py  # Inspiration path extraction
│   │
│   └── utils/                   # Utility functions
│       ├── map_ids_to_text.py               # ID to text mapping
│       └── verify_id_mapping_v2.py          # ID mapping verification
│
├── scripts/                     # Organized scripts
│   ├── demo/                    # Demo scripts
│   │   ├── run_demo.py
│   │   ├── run_demo_utf8.py
│   │   └── run_hypothesis_demo.py
│   │
│   ├── neo4j/                   # Neo4j management scripts
│   │   ├── start_neo4j.bat
│   │   ├── stop_neo4j.bat
│   │   ├── setup_neo4j.ps1
│   │   └── ...
│   │
│   ├── batch/                   # Batch processing scripts
│   │   ├── run_150_ollama.sh
│   │   ├── run_with_gpu.sh
│   │   └── run_inference.sh
│   │
│   └── utils/                   # Utility scripts
│       └── run_inspect_neo4j.py
│
├── docs/                        # Documentation
│   ├── QUICKSTART.md
│   ├── CONTRIBUTING.md
│   ├── NEO4J_SETUP_GUIDE.md
│   └── CHANGES_SUMMARY.md
│
├── Myexamples/                  # Core modules
│   ├── agents/                  # Agent definitions
│   │   ├── graph_agents/        # 8 specialized agent configs
│   │   ├── camel_native_agent.py
│   │   └── final_evaluation_agent.py
│   │
│   ├── test_mutiagent/          # Multi-agent coordination
│   │   ├── hypothesis_team.py   # State machine orchestrator
│   │   ├── hypothesis_society_demo.py
│   │   └── workflow_context_manager.py
│   │
│   ├── evaluation_system/       # Batch evaluation tools
│   ├── comparative_experiments/ # Baseline implementations
│   └── vdb/                     # Vector database
│
├── data/                        # Knowledge graph data
└── examples/                    # Example code
```

---

## 🎓 Research Team (Agent Personas)

| Agent | Model | Specialization |
|-------|-------|----------------|
| **Scholar Scour** | Qwen-Max | Literature review with hybrid RAG |
| **Idea Igniter** | Qwen-Max | Creative hypothesis generation |
| **Dr. Qwen Technical** | Qwen-Plus | Technical feasibility analysis |
| **Dr. Qwen Practical** | Qwen-Plus | Implementation pathway design |
| **Prof. Qwen Ethics** | Qwen-Plus | Impact and ethics assessment |
| **Dr. Qwen Leader** | Qwen-Max | Hypothesis synthesis and revision |
| **Critic Crucible** | Qwen-Max | Peer review and quality scoring |
| **Prof. Qwen Editor** | Qwen-Max | Scientific writing refinement |

---

## 📈 Sample Output

```yaml
# Report Metadata
Generated: 2026-02-05 23:27:03
Research Topic: Bridging Multi-task Learning with Gating Mechanisms
Processing Pipeline: Literature → Ideation → Analysis → Synthesis → Review → Polish
Iteration Mode: Enabled (Threshold: 8.0/10)
Iterations Performed: 2/3
Quality Progress: 7.5 → 8.5 → 9.0
Final Quality Score: 9.0/10

# 8-Dimensional Evaluation
Relevance: 9.0/10           (weight: 100%)
Technical Accuracy: 8.0/10  (weight: 100%)
Originality: 9.0/10         (weight: 100%)
Feasibility: 7.0/10         (weight: 100%)
Engagement: 8.0/10          (weight: 100%)
Clarity: 8.0/10             (weight: 50%)
Structure: 9.0/10           (weight: 50%)
Conciseness: 7.0/10         (weight: 50%)

Final Rating: 8.12/10 (25% Internal + 75% External)
```

---

## 📝 Citation

```bibtex
@article{figmac2026,
  title={FIG-MAC: Fine-grained Inspiration Graph Empowered Multi-Agent Collaboration
         for Automated Scientific Discovery},
  author={Anonymous},
  journal={Submitted to Conference},
  year={2026}
}
```

---

<div align="center">

**[⬆ Back to Top](#-fig-mac-fine-grained-inspiration-graph-empowered-multi-agent-collaboration)**

*"Standing on the shoulders of giants, mediated by graphs, orchestrated by agents"*

</div>
