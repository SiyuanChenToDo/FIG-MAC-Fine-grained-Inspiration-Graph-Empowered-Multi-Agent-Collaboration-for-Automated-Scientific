# 📁 FIG-MAC Project Structure

> Complete project directory layout and module documentation for FIG-MAC: Fine-grained Inspiration Graph Empowered Multi-Agent Collaboration.

---

## 🎯 Project Overview

| Attribute | Value |
|:----------|:------|
| **Name** | FIG-MAC |
| **Full Title** | Fine-grained Inspiration Graph Empowered Multi-Agent Collaboration for Automated Scientific Discovery |
| **Language** | Python 3.12 |
| **Core Framework** | CAMEL-AI + FastAPI |
| **LLM Backend** | Qwen-Max / Qwen-Plus (via DashScope) |
| **Total Core LOC** | ~10,000+ lines (Python) |
| **License** | See `LICENSE` |

---

## 🌳 Directory Tree (Production Files)

```
fig-mac/
│
├── 📄 Root Configuration
│   ├── README.md                          # Main project documentation
│   ├── QUICKSTART.md                      # Quick start guide
│   ├── CONTRIBUTING.md                    # Contribution guidelines
│   ├── LICENSE                            # License file
│   ├── requirements.txt                   # Python dependencies
│   ├── .env.example                       # Environment variables template
│   ├── .gitignore                         # Git ignore rules
│   └── .gitattributes                     # Git attributes (Git LFS config)
│
├── 🌐 web_demo/                           # Interactive Web Interface
│   ├── app.py                             # FastAPI backend (180 LOC)
│   ├── templates/
│   │   └── index.html                     # SPA frontend (single page)
│   ├── static/
│   │   ├── css/style.css                  # Glassmorphism UI styles
│   │   ├── js/app.js                      # Frontend logic & SSE handler
│   │   ├── js/animations.js               # Particle background animations
│   │   └── data/demo_workflow.json        # Pre-recorded demo data
│   ├── streamers/
│   │   ├── demo_streamer.py               # Demo mode SSE generator (198 LOC)
│   │   └── realtime_streamer.py           # Realtime mode SSE generator (345 LOC)
│   └── Scientific_Hypothesis_Reports/     # Generated reports from web demo
│
├── 🤖 Myexamples/                         # Core Application Modules
│   │
│   ├── test_mutiagent/                    # Multi-Agent Orchestration (~6,600 LOC)
│   │   ├── hypothesis_team.py             # State machine orchestrator (2,364 LOC)
│   │   ├── hypothesis_society_demo.py     # Main entry point & society factory (1,000 LOC)
│   │   ├── workflow_output_manager.py     # Workflow output persistence (531 LOC)
│   │   ├── workflow_context_manager.py    # Context & token management (395 LOC)
│   │   ├── camel_memory_output_manager.py # CAMEL memory integration (444 LOC)
│   │   ├── camel_message_coordinator.py   # Message routing coordinator (280 LOC)
│   │   ├── simple_result_processor.py     # Result parsing & cleaning (417 LOC)
│   │   ├── intelligent_report_generator.py # Report generation (454 LOC)
│   │   ├── camel_logger_formatter.py      # Custom logging formatter (201 LOC)
│   │   ├── workflow_helper.py             # Workflow utilities (173 LOC)
│   │   ├── investigate_score_issue.py     # Score debugging tool (410 LOC)
│   │   ├── diagnose_iteration.py          # Iteration diagnostics (226 LOC)
│   │   ├── verify_chatcompletion.py       # API verification (85 LOC)
│   │   └── workflow_config.yaml           # Workflow configuration
│   │
│   ├── agents/                            # Agent Definitions (~2,400 LOC)
│   │   ├── camel_native_agent.py          # CAMEL native agent wrapper (494 LOC)
│   │   ├── final_evaluation_agent.py      # 8-dimension evaluation agent (237 LOC)
│   │   └── graph_agents/                  # 8 specialized agent configs
│   │       ├── scholar_scour.py           # Literature reviewer
│   │       ├── idea_igniter.py            # Creative ideator
│   │       ├── dr_qwen_technical.py       # Technical analyst
│   │       ├── dr_qwen_practical.py       # Practical reviewer
│   │       ├── prof_qwen_ethics.py        # Ethics reviewer
│   │       ├── qwen_leader.py             # Synthesis coordinator
│   │       ├── critic_crucible.py         # Quality critic
│   │       ├── qwen_editor.py             # Scientific editor
│   │       └── local_rag.py               # Hybrid RAG pipeline (559 LOC)
│   │
│   ├── evaluation_framework/              # Evaluation Framework (~2,000 LOC)
│   │   ├── core/
│   │   │   ├── batch_evaluator.py         # Batch evaluation orchestrator
│   │   │   ├── llm_evaluator.py           # LLM-based subjective scoring
│   │   │   └── metrics_calculator.py      # Objective novelty metrics
│   │   ├── utils/
│   │   │   ├── file_utils.py              # File I/O utilities
│   │   │   └── text_utils.py              # Text processing utilities
│   │   ├── complete_evaluation.py         # Full evaluation pipeline
│   │   ├── run_batch_evaluation.py        # Batch evaluation runner
│   │   ├── generate_final_report.py       # Aggregate report generator
│   │   ├── compat_wrapper.py              # Compatibility wrapper
│   │   └── results_fixed/                 # Evaluation results storage
│   │       ├── aggregate_statistics.json
│   │       └── FINAL_comparison_report.md
│   │
│   ├── evaluation_system/                 # Batch Evaluation System
│   │   ├── batch_evaluation_tools/        # Evaluation scripts
│   │   │   ├── batch_evaluate_virsci_logs.py
│   │   │   ├── batch_evaluate_ai_scientist.py
│   │   │   ├── batch_evaluate_coi_agent.py
│   │   │   ├── batch_comparative_evaluation.py
│   │   │   ├── metrics_calculator.py
│   │   │   └── llm_evaluator.py
│   │   ├── batch_results/                 # Evaluation outputs
│   │   │   ├── ai_scientist/              # AI-Scientist-v2 outputs
│   │   │   ├── coi_agent/                 # CoI-Agent outputs
│   │   │   ├── virsci/                    # Virtual-Scientists outputs
│   │   │   └── ours/                      # FIG-MAC outputs
│   │   └── *.md                           # Multiple evaluation guides
│   │
│   ├── comparative_experiments/           # Baseline Systems (Git submodules)
│   │   ├── AI-Scientist-v2/               # The AI Scientist baseline
│   │   ├── CoI-Agent/                     # Chain of Ideas baseline
│   │   └── Virtual-Scientists/            # Virtual Scientists baseline
│   │
│   ├── kimi_batch_runner/                 # Kimi API Batch Runner
│   │   ├── kimi_batch_runner.py           # Main batch runner
│   │   ├── hypothesis_society_kimi.py     # Kimi API society variant
│   │   ├── hypothesis_team_kimi.py        # Kimi API team variant
│   │   ├── glm5_batch_runner.py           # GLM-5 batch runner
│   │   ├── hypothesis_society_glm5.py     # GLM-5 society variant
│   │   ├── ollama_batch_runner.py         # Ollama batch runner
│   │   ├── hypothesis_society_ollama.py   # Ollama society variant
│   │   └── *.sh, *.md                     # Scripts & guides
│   │
│   ├── ablation_study_test/               # Ablation Study Scripts
│   ├── build_graph_connections/           # KG Edge Building Tools
│   ├── tests/                             # Unit & Integration Tests
│   └── vdb/                               # Vector Database Storage
│
├── 📊 data/                               # Knowledge Graph Data
│   ├── all_merged (1).csv                 # Raw paper dataset
│   ├── graph_data/                        # Neo4j database files
│   ├── graphstorm_data/                   # GraphStorm training data
│   │   ├── custom_kg.dgl                  # DGL graph object
│   │   ├── id_maps.json                   # Node/edge ID mappings
│   │   └── meta.json                      # Graph metadata
│   ├── graphstorm_partitioned/            # Partitioned graph for distributed training
│   ├── neo4j_export/                      # Neo4j export files (Parquet)
│   │   ├── nodes_*.parquet                # Node tables
│   │   ├── edges_*.parquet                # Edge tables
│   │   └── papers.parquet                 # Paper metadata
│   └── rq_faiss.index                     # FAISS vector index for RQ retrieval
│
├── 🔬 graphstorm/                         # GraphStorm GNN Framework (Submodule)
│   ├── python/                            # Python API
│   ├── tools/                             # CLI tools
│   ├── examples/                          # Example notebooks
│   ├── docs/                              # Documentation
│   └── tests/                             # Unit tests
│
├── 🐪 camel_local_backup/                 # CAMEL Framework Local Copy
│   ├── agents/                            # Agent implementations
│   ├── memories/                          # Memory management
│   ├── messages/                          # Message schemas
│   ├── models/                            # LLM model wrappers
│   ├── prompts/                           # Prompt templates
│   ├── retrievers/                        # Retrieval components
│   ├── societies/                         # Multi-agent societies
│   ├── storages/                          # Storage backends
│   ├── tasks/                             # Task definitions
│   └── ...
│
├── 🧠 neo4j_knowledge_graph/              # Neo4j KG Management
│   ├── scripts/
│   │   ├── create_knowledge_graph.py      # KG builder
│   │   ├── create_knowledge_graph_fast.py # Fast KG builder
│   │   └── test_neo4j_connection.py       # Connection test
│   ├── logs/                              # KG creation logs
│   └── docs/                              # KG documentation
│
├── 📝 Scientific_Hypothesis_Reports/      # Generated Reports (300+)
│   └── YYYYMMDD_HHMMSS_*.md               # Timestamped hypothesis reports
│
├── 🎬 assets/                             # README Assets
│   ├── screenshot_landing.png             # Landing page screenshot
│   ├── screenshot_think.png               # Think page screenshot
│   ├── screenshot_result.png              # Result page screenshot
│   └── demo.webm                          # Demo video (Git LFS)
│
├── 🔧 Root-Level Scripts
│   ├── inspire_pipeline.py                # Standalone inspiration pipeline (24K LOC)
│   ├── extract_inspiration_paths_v2.py    # Inspiration path extraction
│   ├── map_ids_to_text.py                 # ID-to-text mapping utility
│   ├── verify_id_mapping_v2.py            # ID mapping verification
│   ├── capture_screenshots.py             # Playwright screenshot automation
│   ├── record_demo.py                     # Demo video recording script
│   ├── run_training_v*.sh                 # GraphStorm training scripts (v2-v6c)
│   ├── run_inference.sh                   # Inference script
│   ├── run_inference_v6c.sh               # Inference v6c script
│   ├── run_150_ollama.sh                  # 150-batch Ollama evaluation
│   ├── run_with_gpu.sh                    # GPU training runner
│   └── check_ours_progress.sh             # Progress checker
│
├── 📂 workflow_outputs/                   # Workflow Execution Outputs
│   ├── complete_workflow_*.json           # Complete workflow dumps
│   └── phases/                            # Phase-by-phase outputs
│
└── 📂 debug_context/                      # Debug Context Dumps
    └── raw_context_*.json                 # Raw LLM context for debugging
```

---

## 🔑 Core Module Breakdown

### 1. Multi-Agent Orchestration (`Myexamples/test_mutiagent/`)

| File | LOC | Role |
|:-----|:---:|:-----|
| `hypothesis_team.py` | 2,364 | **State Machine Core** — Drives 9-phase workflow (INIT → LITERATURE → IDEATION → ANALYSIS → SYNTHESIS → REVIEW → REVISION → POLISH → EVALUATION → FINISH) |
| `hypothesis_society_demo.py` | 1,000 | **Entry Point** — Creates 8 CAMEL agents, configures models, runs `run_research_async()` |
| `workflow_output_manager.py` | 531 | **Output Persistence** — Saves phase outputs, generates workflow summaries, manages report files |
| `workflow_context_manager.py` | 395 | **Context Management** — Token counting, context window management, message history |
| `camel_memory_output_manager.py` | 444 | **Memory Integration** — Bridges CAMEL memory system with workflow outputs |
| `simple_result_processor.py` | 417 | **Result Parsing** — Cleans markdown, extracts scores, handles agent responses |
| `intelligent_report_generator.py` | 454 | **Report Generation** — Formats final hypothesis into publication-ready markdown |
| `camel_logger_formatter.py` | 201 | **Logging** — Custom colored log formatter for agent activities |
| `camel_message_coordinator.py` | 280 | **Message Routing** — (Legacy) Coordinates inter-agent messages |
| `workflow_helper.py` | 173 | **Utilities** — (Legacy) Helper functions for workflow execution |

### 2. Agent Definitions (`Myexamples/agents/`)

| File | LOC | Role |
|:-----|:---:|:-----|
| `camel_native_agent.py` | 494 | **Agent Wrapper** — CAMEL native agent with `step()`/`step_async()`, memory management, response parsing |
| `final_evaluation_agent.py` | 237 | **Evaluator** — 8-dimension quality scoring (Novelty, Significance, Effectiveness, Engagement, Feasibility, Clarity, Structure, Conciseness) |
| `graph_agents/local_rag.py` | 559 | **RAG Pipeline** — Hybrid FAISS vector + GraphStorm KG retrieval with logging-gated output |
| `graph_agents/scholar_scour.py` | 121 | **Literature Reviewer** — RAG-enhanced evidence synthesis |
| `graph_agents/idea_igniter.py` | 92 | **Creative Ideator** — Generates 3-5 novel hypotheses |
| `graph_agents/dr_qwen_technical.py` | 151 | **Technical Reviewer** — Scientific validity assessment |
| `graph_agents/dr_qwen_practical.py` | 175 | **Practical Reviewer** — Implementation pathway design |
| `graph_agents/prof_qwen_ethics.py` | 145 | **Ethics Reviewer** — Societal impact assessment |
| `graph_agents/qwen_leader.py` | 107 | **Coordinator** — Hypothesis synthesis & revision |
| `graph_agents/critic_crucible.py` | 156 | **Quality Critic** — Peer review with scoring |
| `graph_agents/qwen_editor.py` | 80 | **Scientific Editor** — Language refinement & polish |

### 3. Web Demo (`web_demo/`)

| File | LOC | Role |
|:-----|:---:|:-----|
| `app.py` | 180 | **FastAPI Backend** — `/api/demo/start` & `/api/realtime/start` SSE endpoints |
| `streamers/demo_streamer.py` | 198 | **Demo Streamer** — Pre-recorded workflow playback from JSON |
| `streamers/realtime_streamer.py` | 345 | **Realtime Streamer** — Live CAMEL pipeline SSE streaming |
| `templates/index.html` | ~1,500 | **SPA Frontend** — 4-page flow: Landing → Input → Think → Result |
| `static/css/style.css` | ~2,000 | **Styles** — Glassmorphism, animations, responsive layout |
| `static/js/app.js` | ~1,800 | **Frontend Logic** — State management, SSE client, Chart.js/KaTeX integration |
| `static/js/animations.js` | ~300 | **Animations** — Particle background, SVG round-table |

### 4. Evaluation Framework (`Myexamples/evaluation_framework/`)

| File | Role |
|:-----|:-----|
| `core/batch_evaluator.py` | Orchestrates batch evaluation across all baselines |
| `core/llm_evaluator.py` | LLM-based subjective quality scoring (1-10 scale) |
| `core/metrics_calculator.py` | Objective novelty metrics (HD, CD, CI, ON_raw, S_src, U_src, P) |
| `complete_evaluation.py` | Full evaluation pipeline combining objective + subjective |
| `run_batch_evaluation.py` | CLI runner for batch evaluations |
| `generate_final_report.py` | Aggregates results into comparison reports |

### 5. Knowledge Graph Pipeline (`data/` + `neo4j_knowledge_graph/`)

| Component | Technology | Purpose |
|:----------|:-----------|:--------|
| Neo4j Database | `graph_data/` | Stores Paper-RQ-Solution nodes & INSPIRED edges |
| FAISS Index | `rq_faiss.index` | Vector retrieval for Research Questions (all-MiniLM-L6-v2) |
| GraphStorm Data | `graphstorm_data/` | DGL graph + id_maps + metadata for GNN training |
| Partitioned Graph | `graphstorm_partitioned/` | Distributed training partition files |
| Neo4j Exports | `neo4j_export/` | Parquet exports for analysis |

---

## 🔄 Data Flow Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Research Topic │────▶│  Hybrid RAG      │────▶│  8-Agent State  │
│  (User Input)   │     │  (Vector + Graph)│     │  Machine        │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                              │                           │
                              ▼                           ▼
                        ┌──────────┐              ┌──────────────┐
                        │ FAISS    │              │ INIT         │
                        │ Index    │              │ LITERATURE   │
                        │ (Vector) │              │ IDEATION     │
                        └──────────┘              │ ANALYSIS     │
                        ┌──────────┐              │ SYNTHESIS    │
                        │ Neo4j    │              │ REVIEW       │
                        │ KG       │              │ REVISION     │
                        │ (Graph)  │              │ POLISH       │
                        └──────────┘              │ EVALUATION   │
                                                  └──────────────┘
                                                           │
                                                           ▼
                                                  ┌──────────────┐
                                                  │ Scientific   │
                                                  │ Hypothesis   │
                                                  │ Report (.md) │
                                                  └──────────────┘
```

---

## ⚙️ Environment Variables

```bash
# Required
export DASHSCOPE_API_KEY="sk-..."          # Or QWEN_API_KEY

# Optional tuning
export CAMEL_MODEL_TIMEOUT=1200              # Model call timeout (seconds)
export CAMEL_CONTEXT_TOKEN_LIMIT=40000       # Context window size
export HF_MIRROR="https://hf-mirror.com"     # HuggingFace mirror (China)
export LOCAL_RAG_DEBUG=1                     # Enable RAG debug output
```

---

## 📦 Dependencies

| Category | Key Packages |
|:---------|:-------------|
| **Framework** | `camel-ai>=0.2.0` |
| **LLM** | `openai>=1.0.0`, `qwen-agent>=0.1.0` |
| **Web** | `fastapi`, `uvicorn`, `sse-starlette` |
| **Vector DB** | `faiss-cpu>=1.7.4` |
| **KG** | `neo4j>=5.0.0`, `networkx>=3.0` |
| **GNN** | `graphstorm` (local), `dgl` |
| **Data** | `numpy>=1.24.0`, `pandas>=2.0.0` |
| **Frontend** | Chart.js, KaTeX, marked.js (CDN) |

---

## 🚀 Quick Entry Points

```bash
# 1. Run Web Demo
cd web_demo && uvicorn app:app --host 0.0.0.0 --port 8080

# 2. Run Full Pipeline (CLI)
export DASHSCOPE_API_KEY=sk-...
python Myexamples/test_mutiagent/hypothesis_society_demo.py

# 3. Run Standalone Inspiration Pipeline
python inspire_pipeline.py "graph neural networks for drug discovery"

# 4. Run Batch Evaluation
python Myexamples/evaluation_framework/run_batch_evaluation.py

# 5. Run Ablation Study
cd Myexamples/evaluation_system/batch_results/消融实验
bash run_all_configs.sh
```

---

## 📊 Scale Metrics

| Metric | Value |
|:-------|:------|
| Papers in KG | 26,917 |
| Research Questions | 76,933 |
| Solutions | 76,933 |
| Semantic Units per Paper | 21 |
| Generated Reports | 300+ |
| Core Python LOC | ~10,000 |
| Web Demo LOC | ~4,500 |
| Evaluation LOC | ~2,000 |
| Total Project LOC | ~20,000+ |

---

*Last updated: 2026-04-20*
