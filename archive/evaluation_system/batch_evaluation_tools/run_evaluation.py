import os
import sys
import json
import argparse
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

# --- Environment Configuration ---
# Use env var if set, otherwise fallback to known working key
if not os.environ.get("OPENAI_COMPATIBILITY_API_KEY"):
    os.environ["OPENAI_COMPATIBILITY_API_KEY"] = "sk-c1a6b588f7d543adb0412c5bc61bdd7b"

if not os.environ.get("OPENAI_COMPATIBILITY_API_BASE_URL"):
    os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"

os.environ["QWEN_API_KEY"] = os.environ["OPENAI_COMPATIBILITY_API_KEY"]
os.environ["QWEN_API_BASE_URL"] = os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"]
# -------------------------------------------------------------

from Myexamples.evaluation_system.metrics_calculator import ScientificMetricsCalculator
from Myexamples.evaluation_system.llm_evaluator import ScientificLLMEvaluator
from camel.embeddings import OpenAICompatibleEmbedding

def extract_core_content(text: str) -> str:
    """
    Extract complete core hypothesis content for comprehensive evaluation.
    
    Strategy: Extract all key sections to ensure complete information:
    1. Executive Summary (## 1. Executive Summary)
    2. Background and Rationale (## 2. Background)
    3. Detailed Hypothesis (## 3. Detailed Hypothesis)
    4. Supporting Analysis (## 4. Supporting Analysis)
    5. Methodology (## 5. Methodology)
    6. Expected Outcomes (## 6. Expected Outcomes)
    
    This ensures all critical information is included for accurate evaluation.
    
    Returns:
        Complete core hypothesis text for evaluation (up to 8000 chars for comprehensive coverage)
    """
    # Find the start of the main content (skip metadata)
    lines = text.split('\n')
    start_idx = 0
    for i, line in enumerate(lines):
        if line.startswith('# Scientific Hypothesis') or line.startswith('## 1. Executive Summary'):
            start_idx = i
            break
    
    if start_idx > 0:
        text = '\n'.join(lines[start_idx:])
    
    # Extract key sections in order
    sections = []
    
    # 1. Executive Summary
    if "## 1. Executive Summary" in text:
        parts = text.split("## 1. Executive Summary")
        if len(parts) > 1:
            content = parts[1]
            # Extract until next major section
            next_section = content.find("## 2")
            if next_section > 0:
                sections.append(content[:next_section].strip())
            elif "## 3" in content:
                next_section = content.find("## 3")
                if next_section > 0:
                    sections.append(content[:next_section].strip())
            else:
                sections.append(content.split("##")[0].strip())
    
    # 2. Background and Rationale (important for context)
    if "## 2. Background" in text or "## 2. Background and Rationale" in text:
        marker = "## 2. Background and Rationale" if "## 2. Background and Rationale" in text else "## 2. Background"
        parts = text.split(marker)
        if len(parts) > 1:
            content = parts[1]
            next_section = content.find("## 3")
            if next_section > 0:
                sections.append(content[:next_section].strip())
            else:
                sections.append(content.split("##")[0].strip())
    
    # 3. Detailed Hypothesis (core content)
    if "## 3. Detailed Hypothesis" in text:
        parts = text.split("## 3. Detailed Hypothesis")
        if len(parts) > 1:
            content = parts[1]
            next_section = content.find("## 4")
            if next_section > 0:
                sections.append(content[:next_section].strip())
            else:
                sections.append(content.split("##")[0].strip())
    
    # 4. Supporting Analysis (methodological justification)
    if "## 4. Supporting Analysis" in text:
        parts = text.split("## 4. Supporting Analysis")
        if len(parts) > 1:
            content = parts[1]
            next_section = content.find("## 5")
            if next_section > 0:
                sections.append(content[:next_section].strip())
            else:
                sections.append(content.split("##")[0].strip())
    
    # 5. Methodology (implementation details)
    if "## 5. Methodology" in text:
        parts = text.split("## 5. Methodology")
        if len(parts) > 1:
            content = parts[1]
            next_section = content.find("## 6")
            if next_section > 0:
                sections.append(content[:next_section].strip())
            else:
                sections.append(content.split("##")[0].strip())
    
    # Combine all sections
    if sections:
        combined = "\n\n".join(sections)
        # Limit to 8000 chars for comprehensive but manageable evaluation
        if len(combined) > 8000:
            # Prioritize: keep Executive Summary + Detailed Hypothesis + Methodology
            # Truncate Background and Supporting Analysis if needed
            priority_text = ""
            if "## 1. Executive Summary" in text:
                exec_part = text.split("## 1. Executive Summary")[1].split("## 2")[0] if "## 2" in text.split("## 1. Executive Summary")[1] else text.split("## 1. Executive Summary")[1].split("##")[0]
                priority_text += exec_part.strip() + "\n\n"
            
            if "## 3. Detailed Hypothesis" in text:
                hyp_part = text.split("## 3. Detailed Hypothesis")[1].split("## 4")[0] if "## 4" in text.split("## 3. Detailed Hypothesis")[1] else text.split("## 3. Detailed Hypothesis")[1].split("##")[0]
                priority_text += hyp_part.strip() + "\n\n"
            
            if "## 5. Methodology" in text:
                method_part = text.split("## 5. Methodology")[1].split("## 6")[0] if "## 6" in text.split("## 5. Methodology")[1] else text.split("## 5. Methodology")[1].split("##")[0]
                priority_text += method_part.strip()
            
            return priority_text[:8000] if len(priority_text) > 8000 else priority_text
        return combined
    
    # Fallback: Use comprehensive prefix (increased to 8000 for better coverage)
    return text[:8000] if len(text) > 8000 else text

def main():
    parser = argparse.ArgumentParser(description="Scientific Hypothesis Evaluation System")
    parser.add_argument("--report_path", type=str, help="Path to the markdown report file")
    parser.add_argument("--input_text", type=str, help="Direct input text string (alternative to file)")
    parser.add_argument("--comparison_text", type=str, help="Optional: Baseline text to compare against")
    parser.add_argument("--source_docs", type=str, help="Path to JSON file with source documents (for P metric)")
    parser.add_argument("--baseline_source_docs", type=str, help="Path to JSON file with baseline source documents")
    parser.add_argument("--vdb_path", type=str, default="Myexamples/vdb/camel_faiss_storage", help="Path to FAISS storage")
    parser.add_argument("--json_data", type=str, default="Myexamples/data/final_data/final_custom_kg_papers.json", help="Path to metadata JSON")
    parser.add_argument("--output_dir", type=str, default="Myexamples/evaluation_system/results", help="Output directory")
    
    args = parser.parse_args()
    
    print("="*60)
    print("🧪 Scientific Hypothesis Evaluation System v2.0")
    print("="*60)
    
    # 1. Get Content
    target_text = ""
    source_name = "Input"
    
    if args.report_path and os.path.exists(args.report_path):
        with open(args.report_path, 'r', encoding='utf-8') as f:
            raw_text = f.read()
            target_text = extract_core_content(raw_text)
            source_name = os.path.basename(args.report_path)
    elif args.input_text:
        target_text = args.input_text
        source_name = "Direct_Input_Text"
    else:
        print("Error: Must provide either --report_path or --input_text")
        return
    
    print(f"\nEvaluating: {source_name}")
    print(f"Content Preview: {target_text[:100]}...")

    # 2. Initialize Embedding Model
    print("\nInitializing Embedding Model...")
    embedding_model = OpenAICompatibleEmbedding(
        model_type="text-embedding-v2",
        api_key=os.environ.get("OPENAI_COMPATIBILITY_API_KEY"),
        url=os.environ.get("OPENAI_COMPATIBILITY_API_BASE_URL"),
    )
    
    # 3. Initialize Calculator
    calculator = ScientificMetricsCalculator(args.vdb_path, embedding_model)
    calculator.load_resources(args.json_data)
    
    # 3.5 Load Source Documents (for P metric)
    source_docs = None
    if args.source_docs and os.path.exists(args.source_docs):
        print(f"Loading source documents from {args.source_docs}...")
        try:
            with open(args.source_docs, 'r', encoding='utf-8') as f:
                source_data = json.load(f)
                # Expected format: {"source_documents": ["abstract1", "abstract2", ...]}
                source_docs = source_data.get("source_documents", [])
                print(f"  Loaded {len(source_docs)} source documents")
        except Exception as e:
            print(f"⚠️  Failed to load source documents: {e}")
    
    # 4. Calculate Objective Metrics
    print("\nCalculating Objective Metrics...")
    obj_metrics = calculator.evaluate_text(target_text, source_documents=source_docs)
    
    # 5. LLM Judge
    print("\nRunning LLM Judge...")
    judge = ScientificLLMEvaluator()
    llm_metrics = judge.absolute_evaluation(target_text)
    
    # 6. Comparison (Optional)
    comparison_result = None
    if args.comparison_text:
        print("\nRunning Comparative Evaluation (Head-to-Head)...")
        
        # Load baseline source documents if provided
        baseline_source_docs = None
        if args.baseline_source_docs and os.path.exists(args.baseline_source_docs):
            print(f"Loading baseline source documents from {args.baseline_source_docs}...")
            try:
                with open(args.baseline_source_docs, 'r', encoding='utf-8') as f:
                    baseline_source_data = json.load(f)
                    baseline_source_docs = baseline_source_data.get("source_documents", [])
                    print(f"  Loaded {len(baseline_source_docs)} baseline source documents")
            except Exception as e:
                print(f"⚠️  Failed to load baseline source documents: {e}")
        
        # Calc objective metrics for baseline
        baseline_obj_metrics = calculator.evaluate_text(args.comparison_text, source_documents=baseline_source_docs)
        
        # Calc subjective metrics for baseline
        print("Running LLM Judge for Baseline...")
        baseline_llm_metrics = judge.absolute_evaluation(args.comparison_text)
        
        # Safe access for ON metric
        baseline_on = baseline_obj_metrics.get("Novelty_Metrics", {}).get("ON_raw (Overall Novelty - Raw)", "N/A")
        if isinstance(baseline_on, float):
            print(f"Baseline ON_raw: {baseline_on:.4f}")
        else:
            print(f"Baseline ON_raw: {baseline_on}")
        
        # LLM Comparison
        comparison_eval = judge.comparative_evaluation(target_text, args.comparison_text)
        comparison_result = {
            "baseline_metrics": {
                "objective": baseline_obj_metrics,
                "subjective_llm": baseline_llm_metrics
            },
            "llm_comparison": comparison_eval
        }

    # 7. Prepare Final Results
    final_results = {
        "metadata": {
            "source": source_name,
            "timestamp": datetime.now().isoformat(),
        },
        "metrics": {
            "objective": obj_metrics,
            "subjective_llm": llm_metrics
        }
    }
    
    if comparison_result:
        final_results["comparison"] = comparison_result
    
    # 7.5. Apply ON_v2 Normalization
    main_novelty = obj_metrics.get("Novelty_Metrics", {})
    main_on_raw = main_novelty.get("ON_raw (Overall Novelty - Raw)")
    
    # Check if we have a comparison (2 hypotheses to rank)
    if comparison_result and comparison_result.get("baseline_metrics"):
        baseline_obj = comparison_result["baseline_metrics"].get("objective", {})
        baseline_novelty = baseline_obj.get("Novelty_Metrics", {})
        baseline_on_raw = baseline_novelty.get("ON_raw (Overall Novelty - Raw)")
        
        # If both have valid ON_raw, perform ranking normalization
        if main_on_raw is not None and baseline_on_raw is not None:
            # Rank by ON_raw (ascending: lower score = rank 1)
            if main_on_raw < baseline_on_raw:
                # Main is lower (worse)
                main_rank = 1
                baseline_rank = 2
            elif main_on_raw > baseline_on_raw:
                # Main is higher (better)
                main_rank = 2
                baseline_rank = 1
            else:
                # Tie
                main_rank = 1
                baseline_rank = 1
            
            # Calculate normalized scores: ON_norm = rank / N (improved formula)
            N = 2
            main_novelty["ON (Overall Novelty - Normalized)"] = main_rank / N
            main_novelty["Rank"] = main_rank
            main_novelty["Total_Hypotheses"] = N
            
            baseline_novelty["ON (Overall Novelty - Normalized)"] = baseline_rank / N
            baseline_novelty["Rank"] = baseline_rank
            baseline_novelty["Total_Hypotheses"] = N
            
            print(f"✅ Ranked 2 hypotheses using improved formula ON = rank / N:")
            print(f"   System A: ON_raw={main_on_raw:.4f}, Rank={main_rank}, ON_norm={main_novelty['ON (Overall Novelty - Normalized)']:.4f}")
            print(f"   System B: ON_raw={baseline_on_raw:.4f}, Rank={baseline_rank}, ON_norm={baseline_novelty['ON (Overall Novelty - Normalized)']:.4f}")
        else:
            # Fallback to single hypothesis mode
            if main_on_raw is not None:
                main_novelty["ON (Overall Novelty - Normalized)"] = 0.5
                main_novelty["Rank"] = 1
                main_novelty["Total_Hypotheses"] = 1
            if baseline_on_raw is not None:
                baseline_novelty["ON (Overall Novelty - Normalized)"] = 0.5
                baseline_novelty["Rank"] = 1
                baseline_novelty["Total_Hypotheses"] = 1
    else:
        # Single hypothesis mode: assign median score (0.5)
        if main_on_raw is not None and main_novelty.get("ON (Overall Novelty - Normalized)") is None:
            main_novelty["ON (Overall Novelty - Normalized)"] = 0.5
            main_novelty["Rank"] = 1
            main_novelty["Total_Hypotheses"] = 1
            print("ℹ️  Single hypothesis mode: ON_normalized set to 0.5 (no ranking context)")

    # 8. Save JSON Results
    os.makedirs(args.output_dir, exist_ok=True)
    # Safe filename
    safe_name = "".join([c if c.isalnum() else "_" for c in source_name])[:50]
    json_out_path = os.path.join(args.output_dir, f"{safe_name}_eval_v2.json")
    
    with open(json_out_path, 'w', encoding='utf-8') as f:
        json.dump(final_results, f, indent=2)
        
    print(f"\n✅ JSON Results saved to: {json_out_path}")
    
    # 9. Generate & Save Chinese Analysis Report
    print("\nGenerating Chinese Analysis Report...")
    analysis_report = judge.generate_analysis_report(final_results)
    
    md_out_path = os.path.join(args.output_dir, f"{safe_name}_analysis_report.md")
    with open(md_out_path, 'w', encoding='utf-8') as f:
        f.write(analysis_report)
        
    print(f"✅ Report saved to: {md_out_path}")
    print("\n" + "="*60)
    print(analysis_report)
    print("="*60)

if __name__ == "__main__":
    main()
