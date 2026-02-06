#!/usr/bin/env python3
"""
Final Evaluation Agent for Scientific Hypothesis Assessment
Based on CAMEL BaseAgent architecture with FIG-MAC evaluation standards
"""

import json
from typing import Dict, Any, List
from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelType, ModelPlatformType
from camel.configs import QwenConfig
from camel.responses import ChatAgentResponse


class FinalEvaluationAgent(ChatAgent):
    """
    Final evaluation agent based on CAMEL BaseAgent architecture
    Implements FIG-MAC evaluation standards with 8-dimensional scoring
    """

    # 权重设置：如需调整，可修改该字典
    EVALUATION_WEIGHTS = {
        "clarity": 0.5,
        "relevance": 1.0,
        "structure": 0.5,
        "conciseness": 0.5,
        "technical_accuracy": 1.0,
        "engagement": 1.0,
        "originality": 1.0,
        "feasibility": 1.0,
    }

    def __init__(self, model_type: ModelType = ModelType.QWEN_PLUS):
        """Initialize the evaluation agent with CAMEL native components"""
        
        # Create evaluation system message
        system_message = self._create_evaluation_prompt()
        
        # Create model using CAMEL ModelFactory
        model = ModelFactory.create(
            model_type=model_type,
            model_platform=ModelPlatformType.QWEN,
            model_config_dict=QwenConfig().as_dict()
        )
        
        # Initialize with CAMEL ChatAgent architecture
        super().__init__(
            system_message=system_message,
            model=model
        )
        
        self.agent_name = "Final Evaluation Agent"
        self.role_name = "Scientific Hypothesis Evaluator"
    
    def _create_evaluation_prompt(self) -> BaseMessage:
        """Create evaluation prompt based on FIG-MAC standards"""
        
        # Carefully designed prompt to avoid f-string and escape character issues
        prompt_content = """You are a Final Evaluation Agent for scientific hypothesis assessment.

EVALUATION CRITERIA (8 dimensions, all 1-10 scale):
1. Clarity (1-10): Content clarity and comprehensibility
2. Relevance (1-10): Coverage of research topics and significance  
3. Structure (1-10): Well-structured with intro, objectives, methods, results, conclusions
4. Conciseness (1-10): Concise yet comprehensive
5. Technical Accuracy (1-10): Correct scientific terminology and methods
6. Engagement (1-10): Reader engagement and readability
7. Originality (1-10): Novel ideas, methods, or models
8. Feasibility (1-10): Implementation feasibility

SCORING STANDARDS (1-10 scale):
10: Award quality - Technically flawless with groundbreaking impact
9: Very Strong Accept - Excellent impact on multiple areas
8: Strong Accept - Technically strong with novel ideas
7: Accept - Solid with high impact on at least one sub-area
6: Weak Accept - Solid with moderate-to-high impact
5: Borderline accept - Reasons to accept outweigh reject
4: Borderline reject - Reasons to reject outweigh accept
3: Reject - Technical flaws, weak evaluation
2: Strong Reject - Major technical flaws, limited impact
1: Very Strong Reject - Trivial results or ethical issues

OUTPUT FORMAT (JSON only):
{
  "evaluation_scores": {
    "clarity": {"score": X, "justification": "..."},
    "relevance": {"score": X, "justification": "..."},
    "structure": {"score": X, "justification": "..."},
    "conciseness": {"score": X, "justification": "..."},
    "technical_accuracy": {"score": X, "justification": "..."},
    "engagement": {"score": X, "justification": "..."},
    "originality": {"score": X, "justification": "..."},
    "feasibility": {"score": X, "justification": "..."}
  },
  "total_score": X,
  "final_rating": X,
  "overall_assessment": "..."
}

Be critical and cautious in your decision."""
        
        return BaseMessage.make_assistant_message(
            role_name="System",
            content=prompt_content
        )
    
    def evaluate_hypothesis(self, hypothesis_content: str) -> Dict[str, Any]:
        """
        Evaluate scientific hypothesis using FIG-MAC standards
        
        Args:
            hypothesis_content: The scientific hypothesis content to evaluate
            
        Returns:
            Dict containing evaluation scores and assessment
        """
        try:
            # Create evaluation request message
            evaluation_request = BaseMessage.make_user_message(
                role_name="Evaluator",
                content=f"Please evaluate the following scientific hypothesis according to the 8-dimensional criteria:\n\n{hypothesis_content}"
            )
            
            # Get evaluation response using CAMEL native step method
            response = self.step(evaluation_request)
            
            # Extract and parse JSON response
            evaluation_result = self._parse_evaluation_response(response.msg.content)
            
            return evaluation_result
            
        except Exception as e:
            # Return error evaluation if parsing fails
            return {
                "evaluation_scores": {
                    "clarity": {"score": 3, "justification": "Evaluation failed due to parsing error"},
                    "relevance": {"score": 3, "justification": "Unable to assess relevance"},
                    "structure": {"score": 3, "justification": "Unable to assess structure"},
                    "conciseness": {"score": 3, "justification": "Unable to assess conciseness"},
                    "technical_accuracy": {"score": 3, "justification": "Unable to assess technical accuracy"},
                    "engagement": {"score": 3, "justification": "Unable to assess engagement"},
                    "originality": {"score": 3, "justification": "Unable to assess originality"},
                    "feasibility": {"score": 3, "justification": "Unable to assess feasibility"}
                },
                "total_score": 24,
                "final_rating": 3.0,
                "overall_assessment": f"Evaluation failed: {str(e)}",
                "evaluation_error": str(e)
            }
    
    def _parse_evaluation_response(self, response_content: str) -> Dict[str, Any]:
        """Parse JSON evaluation response from the agent"""
        try:
            # Clean response content to extract JSON
            cleaned_content = response_content.strip()
            
            # Find JSON content between braces
            start_idx = cleaned_content.find('{')
            end_idx = cleaned_content.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_content = cleaned_content[start_idx:end_idx]
                evaluation_data = json.loads(json_content)
                
                # Validate and calculate final metrics
                return self._validate_evaluation_data(evaluation_data)
            else:
                raise ValueError("No valid JSON found in response")
                
        except (json.JSONDecodeError, ValueError) as e:
            raise Exception(f"Failed to parse evaluation response: {str(e)}")
    
    def _validate_evaluation_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and enhance evaluation data"""
        
        # Ensure all required fields exist
        evaluation_scores = data.get("evaluation_scores", {})

        weighted_total = 0.0
        sum_weights = 0.0

        for dimension, weight in self.EVALUATION_WEIGHTS.items():
            dimension_entry = evaluation_scores.get(dimension, {})
            raw_score = dimension_entry.get("score", 3)

            try:
                score = float(raw_score)
            except (TypeError, ValueError):
                score = 3.0

            # Clamp score to 1-10 区间
            score = max(1.0, min(10.0, score))

            dimension_entry["score"] = round(score, 2)
            evaluation_scores[dimension] = dimension_entry

            weighted_total += score * weight
            sum_weights += weight

        if sum_weights == 0:
            average_score = 5.0
            total_score = 0.0
        else:
            average_score = weighted_total / sum_weights
            total_score = weighted_total

        data["evaluation_scores"] = evaluation_scores
        data["total_score"] = round(total_score, 2)
        data["total_score_max"] = round(sum_weights * 10, 2)
        data["final_rating"] = round(average_score, 2)

        return data
    


def create_final_evaluation_agent() -> FinalEvaluationAgent:
    """Factory function to create FinalEvaluationAgent instance"""
    return FinalEvaluationAgent(model_type=ModelType.QWEN_PLUS)


# Test function for development
if __name__ == "__main__":
    # Simple test
    agent = create_final_evaluation_agent()
    
    test_hypothesis = """
    # Test Scientific Hypothesis
    
    This is a test hypothesis for evaluating the multi-dimensional scoring system.
    The hypothesis proposes a novel approach to machine learning optimization.
    """
    
    result = agent.evaluate_hypothesis(test_hypothesis)
    print("Evaluation Result:")
    print(json.dumps(result, indent=2))
