import os
import json
from typing import Dict, List
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.configs import QwenConfig
from camel.agents import ChatAgent
from camel.messages import BaseMessage

class ScientificLLMEvaluator:
    """
    LLM-based scientific hypothesis evaluator.
    Uses Qwen-Max model for high-quality subjective evaluation.
    """
    def __init__(self):
        # Use Qwen-Max for high quality evaluation
        self.model = ModelFactory.create(
            model_platform=ModelPlatformType.QWEN,
            model_type=ModelType.QWEN_MAX,
            model_config_dict=QwenConfig(temperature=0.2).as_dict(),
            api_key=os.environ.get("QWEN_API_KEY"),
            url=os.environ.get("QWEN_API_BASE_URL"),
        )

    def absolute_evaluation(self, report_text: str) -> Dict:
        """
        Score the report on 1-10 scale for 5 dimensions.
        Uses up to 8000 characters for comprehensive evaluation.
        """
        # Use more content for better evaluation (increased from 4000 to 12000 for comprehensive coverage)
        # Prioritize key sections: Executive Summary, Detailed Hypothesis, Methodology
        content_length = min(len(report_text), 12000)
        
        # Smart truncation: Try to keep complete sections rather than cutting mid-sentence
        if len(report_text) > content_length:
            # Find the last complete sentence or paragraph before the limit
            truncated = report_text[:content_length]
            # Try to end at a sentence boundary
            last_period = truncated.rfind('.')
            last_newline = truncated.rfind('\n')
            if last_period > content_length * 0.9:  # If we're close to a sentence end
                report_content = truncated[:last_period + 1]
            elif last_newline > content_length * 0.9:  # Or at least at a paragraph boundary
                report_content = truncated[:last_newline]
            else:
                report_content = truncated
            report_content += "\n\n[Note: Content truncated for length. Evaluation based on provided portion.]"
        else:
            report_content = report_text
        
        prompt = f"""
        You are a senior scientific reviewer with expertise in evaluating research hypotheses. Your task is to provide a comprehensive and fair evaluation of the following research hypothesis report.

        Report Content:
        {report_content}
        {"[Note: Content may be truncated. Evaluate based on the provided portion.]" if len(report_text) > content_length else ""}
        
        Evaluation Criteria (Rate each on a scale of 1-10):
        
        1. **Novelty** (1-10): How new and original is the idea compared to standard literature?
           - Score 8-10: Highly innovative integration of methods, novel theoretical contributions, or creative frameworks that advance the field
           - Score 5-7: Moderate novelty with some innovative elements or interesting combinations
           - Score 1-4: Largely derivative or incremental improvements
           - Consider: Integration of multiple methods, theoretical contributions, innovative frameworks, cross-domain insights
        
        2. **Significance** (1-10): If successful, how much impact would this have?
           - Score 8-10: High potential for significant theoretical or practical impact, addresses important problems, broad applications
           - Score 5-7: Moderate impact potential, addresses relevant problems with limited scope
           - Score 1-4: Limited impact, narrow scope, or unclear benefits
           - Consider: Theoretical implications, practical applications, societal benefits, problem importance
        
        3. **Effectiveness** (1-10): Does the methodology seem capable of proving the hypothesis?
           - Score 8-10: Well-designed methodology with clear validation protocols, appropriate experimental design, strong feasibility
           - Score 5-7: Reasonable methodology with some gaps or unclear validation
           - Score 1-4: Weak methodology, unclear validation, or significant feasibility concerns
           - Consider: Experimental design quality, validation protocols, methodological rigor, logical flow
        
        4. **Clarity** (1-10): Is the writing clear, structured, and scientifically precise?
           - Score 8-10: Excellent organization, precise technical language, clear structure, easy to follow
           - Score 5-7: Generally clear with some organizational issues or minor imprecision
           - Score 1-4: Unclear, poorly organized, or imprecise communication
           - Consider: Organization, technical accuracy, communication quality, logical flow
        
        5. **Feasibility** (1-10): Is the proposed plan realistic with current technology?
           - Score 8-10: Highly feasible with current resources, clear implementation path, realistic requirements
           - Score 5-7: Generally feasible with some challenges or resource constraints
           - Score 1-4: Significant feasibility concerns, unrealistic requirements, or unclear implementation
           - Consider: Computational requirements, data availability, practical constraints, resource needs
        
        **EVALUATION GUIDELINES:**
        - Base your evaluation on the COMPLETE content provided above
        - Be fair and objective: Do not artificially inflate or deflate scores
        - Consider the full context: Methodology sections, experimental design, theoretical grounding, and implementation details
        - Higher scores (8-10) should reflect genuinely strong work with comprehensive methodology, detailed design, and clear contributions
        - Lower scores (1-4) should reflect significant weaknesses or missing critical elements
        - If content appears truncated, evaluate based on what is provided but note any limitations in your reasoning
        
        Return ONLY a JSON object (no markdown, no additional text):
        {{
            "Novelty": <integer 1-10>,
            "Significance": <integer 1-10>,
            "Effectiveness": <integer 1-10>,
            "Clarity": <integer 1-10>,
            "Feasibility": <integer 1-10>,
            "Reasoning": "Brief justification for each score, highlighting strengths and any concerns"
        }}
        """
        
        agent = ChatAgent(
            system_message=BaseMessage.make_assistant_message(role_name="Judge", content="You are a strict scientific judge."),
            model=self.model
        )
        msg = BaseMessage.make_user_message(role_name="User", content=prompt)
        response = agent.step(msg)
        
        try:
            content = response.msg.content
            # Clean up potential markdown
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                 content = content.split("```")[1].split("```")[0]
            return json.loads(content)
        except Exception as e:
            print(f"Error parsing LLM score: {e}")
            return {"Error": str(e)}

    def comparative_evaluation(self, hypothesis_a: str, hypothesis_b: str) -> Dict:
        """
        Compare two hypotheses (A vs B) and declare a winner.
        Useful for Head-to-Head evaluation against a baseline.
        """
        prompt = f"""
        Compare the following two scientific hypotheses for Novelty and Scientific Rigor.
        
        Hypothesis A:
        {hypothesis_a[:2000]}
        
        Hypothesis B:
        {hypothesis_b[:2000]}
        
        Which one is better?
        Return JSON:
        {{
            "Winner": "A" or "B" or "Tie",
            "Reason": "Explanation",
            "A_Strengths": "...",
            "B_Strengths": "..."
        }}
        """
        agent = ChatAgent(
            system_message=BaseMessage.make_assistant_message(role_name="Judge", content="You are a comparative scientific reviewer."),
            model=self.model
        )
        msg = BaseMessage.make_user_message(role_name="User", content=prompt)
        response = agent.step(msg)
        
        try:
            content = response.msg.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            return json.loads(content)
        except Exception as e:
            return {"Error": str(e)}

    def generate_analysis_report(self, evaluation_results: Dict) -> str:
        """
        Generate a comprehensive Markdown analysis report in Chinese based on evaluation metrics.
        """
        results_json = json.dumps(evaluation_results, indent=2)
        
        prompt = f"""
        Please perform a comprehensive analysis of the scientific hypothesis evaluation results provided below and generate a professional report in **Chinese**.
        
        Evaluation Data (JSON):
        {results_json}
        
        Input Context:
        - System A (Ours): The user's multi-agent system output.
        - System B (Baseline): The baseline system output (e.g., Virtual-Scientists).
        - Objective Metrics include Fluency and Novelty scores (ON, HD, CD).
        - Subjective Metrics are LLM ratings (1-10).
        
        Please generate a Markdown report with the following structure:
        
        # 科学猜想生成系统对比评估报告
        
        ## 1. 核心结论 (Executive Summary)
        [Summarize who won and the key reason in 1-2 sentences]
        
        ## 2. 详细得分对比 (Detailed Comparison)
        [Create a comparison table for objective and subjective metrics]
        
        ## 3. 深度分析 (In-depth Analysis)
        - **System A (Ours) 表现分析**: Strengths and weaknesses.
        - **System B (Baseline) 表现分析**: Strengths and weaknesses.
        - **胜负关键因素**: Why did the winner win? (e.g., methodological depth, novelty, clarity)
        
        ## 4. 改进建议 (Actionable Recommendations)
        [Provide 3 specific suggestions for System A to surpass System B in the next iteration]
        
        Use professional academic tone. Be objective and critical.
        """
        
        agent = ChatAgent(
            system_message=BaseMessage.make_assistant_message(role_name="Analyst", content="You are a bilingual scientific analyst."),
            model=self.model
        )
        msg = BaseMessage.make_user_message(role_name="User", content=prompt)
        response = agent.step(msg)
        
        return response.msg.content
