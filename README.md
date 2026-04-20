<div align="center">

# 🧠 FIG-MAC: Fine-grained Inspiration Graph Empowered Multi-Agent Collaboration

### *Redefining Automated Scientific Discovery through Structured Multi-Agent Cognition and Cross-Domain Knowledge Graphs*

[![Architecture](https://img.shields.io/badge/🏛️_Architecture-State--Machine--Driven-blueviolet?style=for-the-badge)]()
[![Agents](https://img.shields.io/badge/🎭_Agents-8%20Specialized%20Roles-ff6b6b?style=for-the-badge)]()
[![Reasoning](https://img.shields.io/badge/🧠_RAG-Hybrid%20%28Vector%2BGraph%29-4ecdc4?style=for-the-badge)]()
[![Evaluation](https://img.shields.io/badge/📊_Evaluation-8--Dimensional%20Scoring-45b7d1?style=for-the-badge)]()
[![Knowledge](https://img.shields.io/badge/📚_Knowledge_Graph-26K%2B_Papers-orange?style=for-the-badge)]()
[![Novelty](https://img.shields.io/badge/✨_Novelty-+31.8%25_Improvement-success?style=for-the-badge)]()
[![Web Demo](https://img.shields.io/badge/🌐_Web_Demo-Live-success?style=for-the-badge)]()

**[Overview](#-overview)** • **[Architecture](#-architecture)** • **[Key Innovations](#-key-innovations)** • **[Experiments](#-experiments)** • **[Web Demo](#-live-web-demo)** • **[Usage](#-usage)** • **[Citation](#-citation)**

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

### 🗂️ Fine-grained Paper Dataset (FPD)

| 📚 Source | 📝 Papers | 🎯 Research Questions | 💡 Solutions |
|:---------:|:---------:|:---------------------:|:------------:|
| ACL | 5,877 | 16,542 | 16,542 |
| EMNLP | 7,539 | 21,263 | 21,263 |
| NAACL | 2,086 | 5,882 | 5,882 |
| EACL | 991 | 2,792 | 2,792 |
| AAAI | 10,424 | 29,454 | 29,454 |
| **📊 Total** | **26,917** | **76,933** | **76,933** |

*Dataset spans 2019-2024, covering NLP and AI research with 21 semantic units per paper*

```mermaid
flowchart TB
    subgraph Input["📥 Input"]
        RT[Research Topic]
    end

    subgraph KGLayer["📚 Knowledge Graph Layer"]
        VS[Vector Store<br/>FAISS Index]
        NK[Neo4j KG<br/>Paper-RQ-Sol]
        VS <-->|Hybrid RAG| NK
    end

    subgraph AgentLayer["🤖 Agent Layer - 8 Specialized Roles"]
        subgraph StateMachine["State Machine Workflow"]
            INIT([INIT])
            LIT[Literature Review]
            IDE[Ideation]
            ANA[Analysis]
            SYN[Synthesis]
            REV[Review]
            DEC{Quality >=<br/>Threshold?}
            POL[Polish]
            REB[Revision]

            INIT --> LIT --> IDE --> ANA --> SYN --> REV --> DEC
            DEC -->|Yes| POL
            DEC -->|No| REB --> SYN
        end
        HT[HypothesisTeam<br/>State Orchestrator]
    end

    subgraph Output["📤 Output"]
        SR[Scientific<br/>Hypothesis Report]
    end

    RT --> LIT
    VS --> LIT
    NK --> LIT
    StateMachine --> HT
    POL --> SR

    style INIT fill:#e1f5ff
    style DEC fill:#fff3cd
    style POL fill:#d4edda
    style REB fill:#f8d7da
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

```mermaid
flowchart LR
    subgraph Source["🌐 Source Domain"]
        RQ["📋 RQ: Drug Discovery"]
        SOL["💡 Solution: GNN with Attention"]
    end

    subgraph Target["🎯 Target Domain"]
        PAP["📄 Paper: Social Network Analysis"]
    end

    RQ -->|has_solution| SOL
    SOL -.->|inspired_by| PAP
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

## 🦴 "Skeleton-Flesh" Hybrid Reasoning

At the heart of FIG-MAC lies our dual-path retrieval paradigm that combines **structural skeletons** with **semantic flesh**:

| Component | Mechanism | Purpose | Output |
|:---------:|:---------:|:-------:|:------:|
| 🦴 **Skeleton** | Graph Traversal on FIG | Discover cross-domain knowledge evolution paths | Traceable inspiration chains |
| 🥩 **Flesh** | Vector Retrieval (Qwen-emb-v2) | Enrich paths with domain-specific technical details | Semantic grounding |
| 🔗 **Fusion** | Hybrid Integration ℐ(𝒯ᵥ, 𝒯ɢ) | Combine structural novelty with technical feasibility | Enriched context for agents |

### Path Scoring Function

Each inspiration chain π = (RQ₀ → SOL → PAPₖ) is ranked by:

```
score(π) = α·sim(Q, RQ₀) + β·conf(RQₘ → SOLⱼ) + γ·conf(SOLⱼ → PAPₖ)
```

Where:
- **sim(Q, RQ₀)**: Cosine similarity between query and entry node
- **conf(·)**: RGCN-predicted relation confidence via DistMult decoder
- **α, β, γ**: Weighting hyperparameters (tuned on validation set)

### Performance Impact

| Retrieval Mode | ON_raw ↑ | P ↑ | U_src ↑ | CD ↓ |
|:--------------:|:--------:|:---:|:-------:|:----:|
| Vector Only | 0.385 | 0.268 | 0.156 | 0.375 |
| Graph Only | 0.410 | 0.225 | 0.210 | 0.389 |
| **Hybrid Skeleton-Flesh** | **0.684** | **0.535** | **0.650** | **0.291** |
| Improvement | **+77.7%** | **+99.6%** | **+209%** | **-22.4%** |

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

### 🏆 Performance Highlights

| 🏅 Metric | FIG-MAC | Best Baseline | 🚀 Improvement |
|:---------:|:-------:|:-------------:|:--------------:|
| 📊 Source Diversity (U_src) | **0.650** | 0.512 | **+26.9%** 🎯 |
| ✨ Provenance-Adjusted Novelty (P) | **0.535** | 0.345 | **+55.1%** 🚀 |
| 🆕 Raw Overall Novelty (ON_raw) | **0.684** | 0.519 | **+31.8%** ⭐ |
| 📅 Contemporary Alignment (CD) | **0.291** | 0.375 | **-22.4%** ✅ |

### 🎖️ Statistical Significance

Paired Wilcoxon signed-rank tests across 150 RQs confirm all improvements are statistically significant (p < 0.001) with large effect sizes (Cohen's d > 0.8).

### 📊 Detailed Evaluation Framework

**🎯 Objective Novelty Metrics** (computed against 150K paper corpus):

| Metric | Symbol | Formula | Interpretation |
|:------:|:------:|:-------:|:--------------:|
| 📜 Historical Dissimilarity | HD | 1 - cos(eₕ, eₚₐₛₜ) | ↑ Higher = More novel vs. past work |
| 📅 Contemporary Dissimilarity | CD | 1 - cos(eₕ, eₚᵣₑₛₑₙₜ) | ↓ Lower = More aligned with current trends |
| 📈 Contemporary Impact | CI | PercentileRank(citations) | ↑ Higher = More impactful topic |
| ✨ Overall Novelty | ON_raw | (HD × CI) / CD | ↑ Higher = Better novelty-feasibility balance |

**Provenance-Adjusted Metrics**:
- **Source Similarity (S_src)**: Measures hypothesis-source divergence
- **Source Diversity (U_src)**: Captures cross-domain retrieval diversity
- **Adjusted Novelty (P)**: ON_raw × [γ(1-S_src) + (1-γ)U_src]

**🎭 Subjective Quality Assessment** (LLM-evaluated 1-10 scale):

| Dimension | Weight | Description |
|:---------:|:------:|:-----------:|
| 🆕 Novelty | 100% | Innovation degree vs. existing work |
| 🎯 Significance | 100% | Potential impact on the field |
| ⚡ Effectiveness | 100% | Expected performance improvement |
| 🎨 Engagement | 100% | Reader interest and accessibility |
| ✅ Feasibility | 100% | Implementation practicality |
| 📖 Clarity | 50% | Expressive precision |
| 🏗️ Structure | 50% | Logical organization |
| ✂️ Conciseness | 50% | Information density |

---

## ⚙️ Technical Configuration

### 🧠 Model Architecture

| Component | Configuration | Details |
|:---------:|:-------------:|:-------:|
| 🎯 RGCN Encoder | 2-layer, dim=256 | Relation-aware graph convolution |
| 🔗 Link Decoder | DistMult | Multi-relation link prediction |
| 📊 Edge Features | Additive aggregation | Combined node + edge features |
| 🌐 Training | Fanout=[25,20], BS=512 | Mini-batch neighborhood sampling |
| ⚡ Optimization | Adam, LR=5e-4 | Early stopping (patience=5) |

### 📈 Graph Neural Network Performance

| Metric | Validation | Test |
|:------:|:----------:|:----:|
| 📉 MRR (Mean Reciprocal Rank) | 0.4563 | 0.4599 |
| 🎯 Hits@1 | 0.3124 | 0.3156 |
| 🎯 Hits@3 | 0.5241 | 0.5278 |
| 🎯 Hits@10 | 0.7892 | 0.7914 |

*Trained for 30 epochs on NVIDIA RTX 5090 (32GB)*

### 🌐 Cross-Model Generalization

FIG-MAC achieves consistent improvements across diverse LLM backbones:

| 🤖 Backbone | Method | ON_raw ↑ | P ↑ | U_src ↑ |
|:-----------:|:------:|:--------:|:---:|:-------:|
| **Mixtral-8x7b** | Virtual Scientists | 0.438 | 0.318 | 0.275 |
| | CoI-Agent | 0.462 | 0.348 | 0.305 |
| | AI Scientist | 0.485 | N/A | N/A |
| | **FIG-MAC** | **0.585** | **0.462** | **0.565** |
| **LLaMA3.1-70b** | Virtual Scientists | 0.508 | 0.372 | 0.342 |
| | CoI-Agent | 0.538 | 0.408 | 0.375 |
| | AI Scientist | 0.562 | N/A | N/A |
| | **FIG-MAC** | **0.622** | **0.488** | **0.595** |
| **Qwen-Max** ⭐ | Virtual Scientists | 0.504 | 0.271 | 0.260 |
| | CoI-Agent | 0.519 | 0.345 | 0.512 |
| | AI Scientist | 0.504 | N/A | N/A |
| | **FIG-MAC** 🏆 | **0.684** | **0.535** | **0.650** |

*Consistent gains across all backbones demonstrate framework robustness*

---

## ✨ Key Features at a Glance

| 🎯 Feature | 💡 Description | 🚀 Impact |
|:----------:|:--------------:|:---------:|
| 🦴 **Skeleton-Flesh Reasoning** | Graph paths + Vector enrichment | +77% novelty improvement |
| 🎭 **8 Specialized Agents** | Role-based collaboration | +2.19 quality points |
| 🔄 **Iterative Refinement** | Quality-driven feedback loop | +1.34 final quality boost |
| 📊 **8-Dimensional Evaluation** | Objective + Subjective metrics | Publication-ready assessment |
| 🌐 **Cross-Model Support** | Mixtral, LLaMA, Qwen | Framework robustness |
| ⚡ **Regression Protection** | Best-version tracking | Quality guarantee |

---

## 🌐 Live Web Demo

Experience FIG-MAC through an interactive web interface — no API key required for demo mode!

### Demo Preview

<p align="center">
  <img src="assets/screenshot_landing.png" width="32%" alt="Landing Page" />
  <img src="assets/screenshot_think.png" width="32%" alt="Agent Round-Table" />
  <img src="assets/screenshot_result.png" width="32%" alt="Final Report" />
</p>

<p align="center">
  <b>🏠 Landing</b> &nbsp;|&nbsp; <b>🤖 Agent Collaboration</b> &nbsp;|&nbsp; <b>📊 Results & Visualization</b>
</p>

<p align="center">
  <a href="https://github.com/SiyuanChenToDo/FIG-MAC-Fine-grained-Inspiration-Graph-Empowered-Multi-Agent-Collaboration-for-Automated-Scientific/releases/download/demo-video/demo.webm">
    ▶️ Watch Full Demo Video (2:20)
  </a>
</p>

### Quick Start (Web Demo)

```bash
cd web_demo
pip install fastapi uvicorn sse-starlette
python -c "import uvicorn; from app import app; uvicorn.run(app, host='0.0.0.0', port=8080)"
# Open http://localhost:8080 in your browser
```

### Two Modes

| Mode | Backend | API Key Required | Duration | Best For |
|:-----|:--------|:-----------------|:---------|:---------|
| 🎬 **Demo** | Pre-recorded workflow data | ❌ No | ~45s | First-time exploration, UI showcase |
| ⚡ **Realtime** | Live CAMEL multi-agent pipeline | ✅ Yes (Qwen/DashScope) | 5-10 min | Actual hypothesis generation |

### UI Highlights

- **🎨 Glassmorphism Design** — Premium frosted-glass interface with animated particle background
- **🎯 Agent Round-Table** — Live visualization of 8 agents collaborating in real-time
- **📊 Interactive Charts** — Radar charts (8-dimension quality) and bar charts (agent contribution) via Chart.js
- **🧮 LaTeX Math Rendering** — Publication-ready formulas with KaTeX
- **📱 Responsive Layout** — Works on desktop and tablet

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
├── web_demo/                    # 🌐 Interactive web interface
│   ├── app.py                   # FastAPI backend (SSE streaming)
│   ├── templates/
│   │   └── index.html           # SPA frontend
│   ├── static/
│   │   ├── css/style.css        # Glassmorphism UI styles
│   │   ├── js/app.js            # Frontend logic
│   │   ├── js/animations.js     # Particle background animations
│   │   └── data/demo_workflow.json  # Pre-recorded demo data
│   └── streamers/
│       ├── demo_streamer.py     # Demo mode SSE generator
│       └── realtime_streamer.py # Realtime mode SSE generator
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

| 🎭 Agent | 🤖 Backbone | 🎯 Role Function | 📝 Key Responsibilities |
|:--------:|:-----------:|:----------------:|:-----------------------:|
| 📚 **Scholar Scour** | Qwen-Max | 🔍 Research Assistant | Literature gathering with hybrid RAG |
| 💡 **Idea Igniter** | Qwen-Max | ✨ Innovator | Creative hypothesis generation |
| ⚙️ **Dr. Qwen Technical** | Qwen-Plus | 🔬 Technical Reviewer | Scientific validity assessment |
| 🛠️ **Dr. Qwen Practical** | Qwen-Plus | 📋 Practical Reviewer | Implementation pathway design |
| ⚖️ **Prof. Qwen Ethics** | Qwen-Plus | 🌍 Ethical Reviewer | Societal impact assessment |
| 🎯 **Dr. Qwen Leader** | Qwen-Max | 🎪 Coordinator | Hypothesis synthesis & revision |
| 🔍 **Critic Crucible** | Qwen-Max | 🏛️ Quality Controller | Peer review & quality scoring |
| ✍️ **Prof. Qwen Editor** | Qwen-Max | 🖊️ Quality Controller | Scientific writing refinement |

### 🔄 Role Collaboration Matrix

| Phase | Primary Role | Supporting Roles | Output |
|:-----:|:------------:|:----------------:|:------:|
| 📖 Literature | Scholar Scour | Vector Store, Neo4j KG | Evidence synthesis |
| 💭 Ideation | Idea Igniter | Research Assistant | 3-5 candidate hypotheses |
| 🔍 Analysis | 3 Reviewers (Parallel) | Technical/Practical/Ethical | Multi-perspective assessment |
| 🎨 Synthesis | Dr. Qwen Leader | All reviewers | Unified hypothesis report |
| ✅ Review | Critic Crucible | Leader (feedback receiver) | Quality score + feedback |
| 🔄 Revision | Dr. Qwen Leader | Editor | Improved hypothesis |
| ✨ Polish | Prof. Qwen Editor | Leader | Publication-ready report |

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
