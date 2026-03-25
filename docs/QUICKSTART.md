# 🚀 Quick Start Guide

Get started with FIG-MAC in 5 minutes!

## 📦 Installation

### Step 1: Clone Repository
```bash
git clone https://github.com/yourusername/fig-mac.git
cd fig-mac
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment
```bash
cp .env.example .env
# Edit .env and add your QWEN_API_KEY
```

## 🎯 First Run

### Option 1: Command Line
```bash
export QWEN_API_KEY="your-api-key"
export CAMEL_CONTEXT_TOKEN_LIMIT=40000

python -c "
import asyncio
from Myexamples.test_mutiagent.hypothesis_society_demo import HypothesisGenerationSociety

async def main():
    society = HypothesisGenerationSociety()
    result = await society.run_research_async(
        research_topic='How can graph neural networks improve drug discovery?',
        max_iterations=2,
        quality_threshold=8.0
    )
    print(f'Report: {result.metadata[\"file_path\"]}')
    print(f'Quality: {result.metadata[\"final_quality_score\"]}/10')

asyncio.run(main())
"
```

### Option 2: Python Script
Create `run_research.py`:

```python
#!/usr/bin/env python3
import asyncio
import os
from Myexamples.test_mutiagent.hypothesis_society_demo import HypothesisGenerationSociety

# Set environment variables
os.environ["QWEN_API_KEY"] = "your-api-key"
os.environ["CAMEL_MODEL_TIMEOUT"] = "1200"
os.environ["CAMEL_CONTEXT_TOKEN_LIMIT"] = "40000"

async def main():
    """Run scientific hypothesis generation"""
    
    # Initialize the research society
    society = HypothesisGenerationSociety()
    
    # Define your research topic
    topic = """
    How can pseudo-parallel data generated from structurally informative 
    regions of the unmatched target KG improve the training of a collective 
    relation integration model?
    """
    
    # Run the workflow
    result = await society.run_research_async(
        research_topic=topic,
        max_iterations=3,          # Maximum revision rounds
        quality_threshold=8.0,     # Target quality score
        polish_iterations=1        # Final polishing rounds
    )
    
    # Display results
    if not result.failed:
        print("\n" + "="*60)
        print("✅ Research Completed Successfully!")
        print("="*60)
        print(f"📄 Report: {result.metadata['file_path']}")
        print(f"⭐ Quality: {result.metadata.get('final_quality_score', 'N/A')}/10")
        print(f"🔄 Iterations: {result.metadata.get('iterations_performed', 'N/A')}")
        print("="*60)
    else:
        print(f"❌ Failed: {result.content}")

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:
```bash
python run_research.py
```

## 📊 Understanding Output

### Generated Files

1. **Scientific Report** (`Scientific_Hypothesis_Reports/*.md`)
   - Complete hypothesis document
   - Executive summary, background, methodology
   - Evaluation scores and metadata

2. **Workflow Logs** (`workflow_outputs/`)
   - Complete execution trace
   - Agent conversations
   - Intermediate results

### Quality Metrics

The system evaluates hypotheses across 8 dimensions:

| Metric | Weight | Description |
|--------|--------|-------------|
| Clarity | 50% | Content comprehensibility |
| Relevance | 100% | Topic significance |
| Structure | 50% | Organization quality |
| Conciseness | 50% | Information density |
| Technical Accuracy | 100% | Methodological soundness |
| Engagement | 100% | Reader captivation |
| Originality | 100% | Novel contribution |
| Feasibility | 100% | Implementation viability |

**Final Score** = 25% Internal (Peer Review) + 75% External (8-Dimensional)

## 🔧 Common Configurations

### Fast Mode (Quick Results)
```python
result = await society.run_research_async(
    research_topic="Your topic",
    max_iterations=1,          # No revision
    quality_threshold=7.0,     # Lower threshold
    polish_iterations=0        # No polishing
)
```

### Deep Research Mode (High Quality)
```python
result = await society.run_research_async(
    research_topic="Your topic",
    max_iterations=5,          # More iterations
    quality_threshold=9.0,     # High threshold
    polish_iterations=2        # Extra polishing
)
```

### Custom RAG Sources
```python
# Set in .env or environment
export KG_PATH="path/to/your/knowledge_graph.json"
export VDB_PATH="path/to/your/vector_db"
```

## 🐛 Troubleshooting

### Issue: Token Truncation
**Solution**: Increase context limit
```bash
export CAMEL_CONTEXT_TOKEN_LIMIT=60000
```

### Issue: Timeout Errors
**Solution**: Increase timeout
```bash
export CAMEL_MODEL_TIMEOUT=1800  # 30 minutes
```

### Issue: API Rate Limits
**Solution**: Add delays between requests
```python
import time
time.sleep(5)  # Between API calls
```

### Issue: Memory Errors
**Solution**: Reduce parallel workers
```bash
export PARALLEL_WORKERS=1
```

## 📚 Next Steps

- [Architecture Guide](docs/ARCHITECTURE.md)
- [Agent Configuration](docs/AGENTS.md)
- [Advanced Workflows](docs/WORKFLOWS.md)
- [API Reference](docs/API.md)

## 💬 Getting Help

- **Issues**: [GitHub Issues](https://github.com/yourusername/fig-mac/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/fig-mac/discussions)
- **Email**: figmac-team@example.com

Happy Researching with FIG-MAC! 🔬🤖
