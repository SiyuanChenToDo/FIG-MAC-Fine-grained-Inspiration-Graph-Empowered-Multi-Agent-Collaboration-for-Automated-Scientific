"""
HypothesisTeam - FIG-MAC style Team + Channel Architecture
Scientific hypothesis generation team collaboration system based on CAMEL framework

Referencing FIG-MAC Team class design, implementing state machine driven multi-agent collaboration
"""

import asyncio
import json
import logging
import os
import re
import time
import warnings
from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

# Suppress transformers FutureWarning about deprecated environment variables
warnings.filterwarnings("ignore", category=FutureWarning, module="transformers")

from camel.messages import BaseMessage
from camel.types import OpenAIBackendRole, ModelType
from Myexamples.agents.camel_native_agent import CamelNativeAgent, HypothesisTaskResult
from Myexamples.core.camel_logger_formatter import OutputFormatter
from Myexamples.core.workflow_helper import WorkflowHelper, TeamState as WorkflowTeamState
from Myexamples.core.simple_result_processor import SimpleResultProcessor
# Enhanced result extractor removed in Stage 3.7 - replaced by CAMEL memory system
# from Myexamples.core.enhanced_result_extractor import EnhancedResultExtractor
from Myexamples.core.workflow_output_manager import WorkflowOutputManager
from Myexamples.core.camel_memory_output_manager import CAMELMemoryOutputManager
from Myexamples.agents.final_evaluation_agent import FinalEvaluationAgent
# Import RAG functionality for fine-grained knowledge retrieval
from Myexamples.agents.graph_agents.local_rag import run_local_rag
# Import WorkflowContextManager for workflow-level memory management
from Myexamples.core.workflow_context_manager import WorkflowContextManager


# Pre-compiled regex patterns for performance (avoid re-compiling on every call)
_QUALITY_SCORE_PATTERNS = [
    re.compile(r'Quality Score[:\s=]+(\d+(?:\.\d+)?)\s*/\s*10', re.IGNORECASE),
    re.compile(r'Quality Score[:\s=]+(\d+(?:\.\d+)?)', re.IGNORECASE),
    re.compile(r'\*\*Quality Score\*\*[:\s=]+(\d+(?:\.\d+)?)', re.IGNORECASE),
    re.compile(r'\*Quality Score\*[:\s=]+(\d+(?:\.\d+)?)', re.IGNORECASE),
    re.compile(r'Quality Score\s+of\s+(\d+(?:\.\d+)?)', re.IGNORECASE),
]
_QUALITY_SCORE_FALLBACK = re.compile(r'(\d+(?:\.\d+)?)\s*/\s*10')
_QUALITY_SCORE_JSON = re.compile(r'"overall_quality_score"[:\s]+(\d+(?:\.\d+)?)')

_ACTIONABLE_ITEM_PATTERNS = {
    "suggestion_headers": re.compile(
        r'(?:Suggestion|Improvement)\s*\d+[\s:.-]+([^\n]+(?:\n(?!(?:Suggestion|Improvement)\s*\d+|#{1,4}\s|#{1,4}\s(?:Missing|Quality|Strengths|Weaknesses))[^\n]+)*)',
        re.IGNORECASE | re.MULTILINE
    ),
    "markdown_headers": re.compile(
        r'####\s+[^\n]+\n+([^#]+?)(?=\n####|\n#{1,3}\s|$)',
        re.MULTILINE
    ),
    "missing_elements": re.compile(
        r'(?:Missing Elements|What is Missing)[^:]*:?\s*\n((?:\s*[-*]\s*[^\n]+\n?)+)',
        re.IGNORECASE
    ),
    "critical_concerns": re.compile(
        r'(?:Critical Concerns|Major Issues)[^:]*:?\s*\n((?:\s*[-*]\s*[^\n]+\n?)+)',
        re.IGNORECASE
    ),
    "weaknesses": re.compile(
        r'(?:Weaknesses|Limitations)[^:]*:?\s*\n((?:\s*[-*]\s*[^\n]+\n?)+)',
        re.IGNORECASE
    ),
    "imperative_sentences": re.compile(
        r'(?:^|\n)\s*[-*]?\s*([^\n]*(?:should|need to|must|add|include|provide|specify)[^\n]{10,200})',
        re.IGNORECASE
    ),
}
_ACTIONABLE_BULLET_SPLIT = re.compile(r'[-*]\s*([^\n]+)')
_ACTIONABLE_FIRST_SENTENCE = re.compile(r'[.!?]\s+')
_ACTIONABLE_WHITESPACE_NORM = re.compile(r'\s+')

_INTERNAL_SCORE_PATTERNS = [
    re.compile(r'Quality Score[:\s*]+(\d+(?:\.\d+)?)\s*(?:/\s*10)?', re.IGNORECASE),
    re.compile(r'\*\*Quality Score\*\*[:\s]+(\d+(?:\.\d+)?)', re.IGNORECASE),
    re.compile(r'Technical Soundness[:\s*]+(\d+(?:\.\d+)?)', re.IGNORECASE),
    re.compile(r'Novelty Assessment[:\s*]+(\d+(?:\.\d+)?)', re.IGNORECASE),
    re.compile(r'Clarity Score[:\s*]+(\d+(?:\.\d+)?)', re.IGNORECASE),
    re.compile(r'overall_quality_score["\']?\s*:\s*["\']?(\d+(?:\.\d+)?)["\']?', re.IGNORECASE),
    re.compile(r'technical_soundness["\']?\s*:\s*["\']?(\d+(?:\.\d+)?)["\']?', re.IGNORECASE),
    re.compile(r'novelty_assessment["\']?\s*:\s*["\']?(\d+(?:\.\d+)?)["\']?', re.IGNORECASE),
    re.compile(r'clarity_score["\']?\s*:\s*["\']?(\d+(?:\.\d+)?)["\']?', re.IGNORECASE),
]
_INTERNAL_SCORE_FALLBACK = re.compile(r'(\d+(?:\.\d+)?)\s*/\s*10')

_DETAILED_SCORE_PATTERNS = {
    'overall_quality_score': [
        re.compile(r'Quality Score[:\s*]+(\d+(?:\.\d+)?)\s*(?:/\s*10)?', re.IGNORECASE),
        re.compile(r'\*\*Quality Score\*\*[:\s]+(\d+(?:\.\d+)?)'),
        re.compile(r'overall_quality_score["\']?\s*:\s*["\']?(\d+(?:\.\d+)?)["\']?', re.IGNORECASE),
    ],
    'technical_soundness': [
        re.compile(r'Technical Soundness[:\s*]+(\d+(?:\.\d+)?)', re.IGNORECASE),
        re.compile(r'technical_soundness["\']?\s*:\s*["\']?(\d+(?:\.\d+)?)["\']?', re.IGNORECASE),
    ],
    'novelty_assessment': [
        re.compile(r'Novelty Assessment[:\s*]+(\d+(?:\.\d+)?)', re.IGNORECASE),
        re.compile(r'novelty_assessment["\']?\s*:\s*["\']?(\d+(?:\.\d+)?)["\']?', re.IGNORECASE),
    ],
    'clarity_score': [
        re.compile(r'Clarity (?:Score|and Presentation)[:\s*]+(\d+(?:\.\d+)?)', re.IGNORECASE),
        re.compile(r'clarity_score["\']?\s*:\s*["\']?(\d+(?:\.\d+)?)["\']?', re.IGNORECASE),
    ],
}


class TeamState(Enum):
    """Team state enumeration - Similar to FIG-MAC state machine design with iteration support"""
    INIT = "init"
    LITERATURE = "literature"  # Literature review phase
    IDEATION = "ideation"      # Creative ideation phase
    ANALYSIS = "analysis"      # Analysis and evaluation phase
    SYNTHESIS = "synthesis"    # Synthesis and integration phase
    REVIEW = "review"          # Peer review phase
    REVISION = "revision"      # Revision phase (iterative improvement)
    POLISH = "polish"          # Final polishing phase
    EVALUATION = "evaluation"  # Final evaluation phase (FIG-MAC standards)
    FINISH = "finish"


class HypothesisChannel:
    """
    Asynchronous communication channel - Similar to FIG-MAC Channel class
    Responsible for message passing and coordination between agents
    """
    
    def __init__(self):
        self.receive_queue: asyncio.Queue = asyncio.Queue()
        self.send_dict: Dict[str, Any] = {}  # Similar to AsyncSafeDict
        self.message_history: List[Dict] = []
        self.logger = logging.getLogger(f"{__name__}.HypothesisChannel")
    
    async def send_message(self, sender_id: str, receiver_id: str, message: BaseMessage):
        """Send message to specified agent - Integrated CAMEL native message passing"""
        message_data = {
            "timestamp": datetime.now(),
            "sender": sender_id,
            "receiver": receiver_id,
            "message": message,
            "message_id": f"{sender_id}_{receiver_id}_{len(self.message_history)}",
            "camel_native": True,  # Mark as CAMEL native message
            "message_type": message.role_type.value if hasattr(message, 'role_type') else "unknown"
        }
        
        self.message_history.append(message_data)
        await self.receive_queue.put(message_data)
        self.logger.info(f"CAMEL native message sent from {sender_id} to {receiver_id}")
    
    async def broadcast_message(self, sender_id: str, message: BaseMessage, receivers: List[str]):
        """Broadcast message to multiple agents"""
        for receiver_id in receivers:
            await self.send_message(sender_id, receiver_id, message)
    
    async def receive_message(self) -> Optional[Dict]:
        """Receive message"""
        try:
            message_data = await asyncio.wait_for(self.receive_queue.get(), timeout=1.0)
            return message_data
        except asyncio.TimeoutError:
            return None
    
    def get_message_history(self, agent_id: Optional[str] = None) -> List[Dict]:
        """Get message history"""
        if agent_id:
            return [msg for msg in self.message_history 
                   if msg["sender"] == agent_id or msg["receiver"] == agent_id]
        return self.message_history.copy()


class HypothesisTeam:
    """
    Scientific hypothesis generation team - Similar to FIG-MAC Team class
    Using state machine driven multi-agent collaboration mechanism
    """
    
    def __init__(self, agents: List[CamelNativeAgent]):
        self.agents: Dict[str, CamelNativeAgent] = {agent.role_name: agent for agent in agents}
        self.channel = HypothesisChannel()
        self.state = TeamState.INIT
        self.current_topic: Optional[str] = None
        self.results: Dict[str, HypothesisTaskResult] = {}
        self.logger = logging.getLogger(f"{__name__}.HypothesisTeam")
        self.debug_context_dir = Path("debug_context")
        
        # Iteration control parameters (FIG-MAC style)
        self.max_iterations: int = 3
        self.quality_threshold: float = 8.0
        self.current_iteration: int = 0
        self.iteration_scores: List[float] = []
        self.polish_iterations: int = 1
        self.polish_rounds_completed: int = 0
        
        # Quality improvement tracking
        self.improvement_history: List[Dict[str, Any]] = []  # Track improvements per iteration
        self.actionable_items_per_iteration: List[List[str]] = []  # Store actionable items extracted each iteration
        
        # Track best version for rollback on regression
        self.best_version: Dict[str, Any] = {
            "score": 0.0,
            "iteration": -1,
            "synthesis": None,
            "review": None
        }
        
        # 工作流辅助器 - 简化状态转换逻辑
        self.workflow_helper = WorkflowHelper()
        
        # 结果处理器 - 简化结果处理逻辑
        self.result_processor = SimpleResultProcessor()
        
        # Enhanced result extractor removed in Stage 3.7 - replaced by CAMEL memory system
        # self.enhanced_extractor = EnhancedResultExtractor()
        
        # 工作流输出管理器 - 阶段3完整流程输出
        self.output_manager = WorkflowOutputManager()
        
        # CAMEL记忆系统输出管理器 - 阶段3.7重构 (基于FIG-MAC经验)
        self.camel_memory_manager = CAMELMemoryOutputManager()
        
        # Workflow-level context manager - Solve context truncation issues
        # INCREASED token limit to reduce truncation of early phase results (Literature with RAG evidence)
        self.workflow_context = WorkflowContextManager(token_limit=40000, model_type=ModelType.QWEN_MAX)
        self.logger.info("Initialized WorkflowContextManager with token_limit=40000, model=QWEN_MAX")
        
        # CRITICAL: Force update token limit to ensure ScoreBasedContextCreator uses the correct value
        # This is necessary because CAMEL's internal cache may use default 32768
        self.workflow_context.token_limit = 40000
        effective_limit = self.workflow_context.effective_token_limit
        self.logger.info(f"✅ Effective token limit confirmed: {effective_limit}")
        
        # Fixed agent mapping - Stage 3 architecture fix (from planner specifications)
        self.FIXED_AGENT_MAPPING = {
            "literature": "Scholar Scour",
            "ideation": "Idea Igniter",
            "analysis": {
                "technical": "Dr. Qwen Technical",
                "practical": "Dr. Qwen Practical", 
                "ethics": "Prof. Qwen Ethics"
            },
            "synthesis": "Dr. Qwen Leader",
            "review": "Critic Crucible",
            "polish": "Prof. Qwen Editor"
        }
        
        # Confirmed 8 agent names (from unified_agent_configs.yaml)
        self.CONFIRMED_AGENTS = [
            "Scholar Scour",           # Literature review expert
            "Idea Igniter",           # Creative generation expert
            "Dr. Qwen Technical",     # Technical analysis expert
            "Dr. Qwen Practical",     # Practical analysis expert
            "Prof. Qwen Ethics",      # Ethics impact expert
            "Dr. Qwen Leader",        # Synthesis leadership expert
            "Critic Crucible",        # Critical review expert
            "Prof. Qwen Editor"       # Editorial refinement expert
        ]
        
        # Workflow phases specification (from planner specifications)
        self.WORKFLOW_PHASES = {
            "LITERATURE": {
                "agent": "Scholar Scour",
                "output_format": "markdown",
                "execution": "sequential"
            },
            "IDEATION": {
                "agent": "Idea Igniter", 
                "output_format": "markdown",
                "execution": "sequential"
            },
            "ANALYSIS": {
                "agents": ["Dr. Qwen Technical", "Dr. Qwen Practical", "Prof. Qwen Ethics"],
                "output_format": "json",
                "execution": "parallel"
            },
            "SYNTHESIS": {
                "agent": "Dr. Qwen Leader",
                "output_format": "markdown", 
                "execution": "sequential"
            },
            "REVIEW": {
                "agent": "Critic Crucible",
                "output_format": "markdown",
                "execution": "sequential"
            },
            "POLISH": {
                "agent": "Prof. Qwen Editor",
                "output_format": "markdown",
                "execution": "sequential"
            }
        }
        
        # State machine mapping - Similar to FIG-MAC state_action design with iteration support
        self.state_actions = {
            TeamState.INIT: self._init_phase,
            TeamState.LITERATURE: self._literature_phase,
            TeamState.IDEATION: self._ideation_phase,
            TeamState.ANALYSIS: self._analysis_phase,
            TeamState.SYNTHESIS: self._synthesis_phase,
            TeamState.REVIEW: self._review_phase,
            TeamState.REVISION: self._revision_phase,
            TeamState.POLISH: self._polish_phase,
            TeamState.EVALUATION: self._evaluation_phase,
            TeamState.FINISH: self._finish_phase,
        }
        
        # Validate agent names against confirmed list
        self._validate_agent_names()
        
        self.logger.info(f"HypothesisTeam initialized with {len(self.agents)} agents")
    
    def _validate_agent_names(self):
        """Validate that all agent names match the confirmed agent list"""
        # self.agents is a dictionary {role_name: agent}
        agent_names = list(self.agents.keys())
        
        for agent_name in agent_names:
            if agent_name not in self.CONFIRMED_AGENTS:
                raise ValueError(f"Agent name '{agent_name}' not in confirmed agent list: {self.CONFIRMED_AGENTS}")
        
        # Check that we have all required agents
        missing_agents = [name for name in self.CONFIRMED_AGENTS if name not in agent_names]
        if missing_agents:
            self.logger.warning(f"Missing agents: {missing_agents}")
    
    def _get_current_phase_name(self) -> str:
        """Get standardized name for current phase"""
        phase_mapping = {
            TeamState.LITERATURE: "literature",
            TeamState.IDEATION: "ideation", 
            TeamState.ANALYSIS: "analysis",
            TeamState.SYNTHESIS: "synthesis",
            TeamState.REVIEW: "review",
            TeamState.POLISH: "polish"
        }
        return phase_mapping.get(self.state, "unknown")
    
    async def execute_hypothesis_generation(self, topic: str, max_iterations: int = 3,
                                           quality_threshold: float = 8.0,
                                           polish_iterations: int = 1) -> HypothesisTaskResult:
        """
        Execute complete hypothesis generation workflow
        State machine driven asynchronous execution - Similar to FIG-MAC execution mechanism
        """
        self.current_topic = topic
        self.state = TeamState.INIT
        
        # Set iteration parameters (FIG-MAC style)
        self.max_iterations = max_iterations
        self.quality_threshold = quality_threshold
        self.current_iteration = 0
        self.iteration_scores = []
        self.polish_iterations = max(1, polish_iterations)
        self.polish_rounds_completed = 0
        
        # Reset improvement tracking for new workflow
        self.improvement_history = []
        self.actionable_items_per_iteration = []
        
        # Reset best version tracking
        self.best_version = {
            "score": 0.0,
            "iteration": -1,
            "synthesis": None,
            "review": None
        }
        
        # 开始工作流跟踪 (阶段3新功能)
        workflow_id = self.output_manager.start_workflow_tracking(topic)
        
        OutputFormatter.info(
            f"[ITERATION CONFIG] Max iterations: {max_iterations}, Quality threshold: {quality_threshold}, "
            f"Polish iterations: {self.polish_iterations}"
        )
        
        # 开始CAMEL记忆系统跟踪 (阶段3.7重构)
        camel_workflow_id = self.camel_memory_manager.start_workflow_memory_tracking(topic)
        
        self.logger.info(f"Starting hypothesis generation for topic: {topic} (Workflow ID: {workflow_id}, CAMEL Memory ID: {camel_workflow_id})")
        
        try:
            while self.state != TeamState.FINISH:
                # 显示当前进度
                workflow_state = WorkflowTeamState(self.state.value)
                progress = self.workflow_helper.get_state_progress(workflow_state)
                self.logger.info(f"Executing state: {self.state.value} (Progress: {progress['progress_percentage']:.1f}%)")
                
                # Execute action corresponding to current state
                action = self.state_actions.get(self.state)
                if action:
                    await action()
                else:
                    raise ValueError(f"No action defined for state: {self.state}")
                
                # State transition using workflow helper
                self.state = self._get_next_state()
            
            # Return final result
            final_result = self.results.get("final_synthesis")
            if final_result:
                # 完成工作流跟踪 (阶段3新功能)
                workflow_summary = self.output_manager.finalize_workflow(
                    final_result.content, success=True
                )
                self.logger.info("Hypothesis generation completed successfully")
                
                # 生成智能优化报告 (阶段3新功能)
                intelligent_report = self.output_manager.generate_intelligent_report()
                complete_report = self.output_manager.generate_complete_workflow_report()
                
                # 将报告信息添加到结果元数据
                enhanced_metadata = final_result.metadata.copy() if hasattr(final_result, 'metadata') else {}
                enhanced_metadata.update({
                    "workflow_summary": workflow_summary,
                    "complete_report_length": len(complete_report),
                    "intelligent_report_length": len(intelligent_report),
                    "workflow_id": workflow_id,
                    "intelligent_report": intelligent_report[:1000] + "..." if len(intelligent_report) > 1000 else intelligent_report
                })
                enhanced_metadata.setdefault("polish_iterations", self.polish_iterations)
                enhanced_metadata.setdefault("polish_rounds_completed", self.polish_rounds_completed)

                evaluation_result = self.results.get("evaluation")
                if evaluation_result and hasattr(evaluation_result, "metadata"):
                    enhanced_metadata.setdefault("evaluation_metadata", evaluation_result.metadata)
                    integrated_score = evaluation_result.metadata.get("integrated_score") if evaluation_result.metadata else None
                    if integrated_score is not None:
                        enhanced_metadata.setdefault("integrated_score", integrated_score)
                    external_rating = evaluation_result.metadata.get("external_rating") if evaluation_result.metadata else None
                    if external_rating is not None:
                        enhanced_metadata.setdefault("external_rating", external_rating)

                final_eval = self.results.get("final_evaluation")
                if final_eval and isinstance(final_eval, dict):
                    enhanced_metadata.setdefault("final_evaluation", final_eval)
                
                # 创建增强的最终结果
                enhanced_final_result = self.result_processor.create_hypothesis_result(
                    content=final_result.content,
                    failed=False,
                    task_type="complete_hypothesis_generation",
                    metadata=enhanced_metadata
                )
                
                return enhanced_final_result
            else:
                raise RuntimeError("Final synthesis not found in results")
                
        except Exception as e:
            self.logger.error(f"Error during hypothesis generation: {e}")
            
            # 记录失败的工作流
            self.output_manager.finalize_workflow(
                f"Hypothesis generation failed: {str(e)}", success=False
            )
            
            return self.result_processor.create_hypothesis_result(
                content=f"Hypothesis generation failed: {str(e)}",
                failed=True,
                task_type="hypothesis_generation",
                metadata={"error": str(e), "topic": topic, "workflow_id": workflow_id}
            )
    
    def _get_next_state(self) -> TeamState:
        """State transition logic with iteration support - FIG-MAC style"""
        # Special handling for REVIEW state - check if iteration is needed
        if self.state == TeamState.REVIEW:
            return self._decide_after_review()
        
        # Special handling for REVISION state - return to SYNTHESIS
        if self.state == TeamState.REVISION:
            return TeamState.REVIEW
        
        # Standard state transitions
        state_map = {
            TeamState.INIT: TeamState.LITERATURE,
            TeamState.LITERATURE: TeamState.IDEATION,
            TeamState.IDEATION: TeamState.ANALYSIS,
            TeamState.ANALYSIS: TeamState.SYNTHESIS,
            TeamState.SYNTHESIS: TeamState.REVIEW,
            TeamState.POLISH: TeamState.EVALUATION,
            TeamState.EVALUATION: TeamState.FINISH,
            TeamState.FINISH: TeamState.FINISH
        }
        
        return state_map.get(self.state, TeamState.FINISH)
    
    def _decide_after_review(self) -> TeamState:
        """Decide next state after review - implement iteration logic with quality improvement tracking and regression detection (FIG-MAC style)"""
        # Extract quality score from review results
        review_result = self.results.get("review")
        if not review_result or review_result.failed:
            OutputFormatter.warning("[ITERATION] Review failed, proceeding to polish")
            return TeamState.POLISH
        
        # Try to extract quality score from review content
        quality_score = self._extract_quality_score(review_result.content)
        
        if quality_score is not None:
            self.iteration_scores.append(quality_score)
            
            # Update best version tracking
            synthesis_result = self.results.get("synthesis")
            if quality_score > self.best_version["score"]:
                self.best_version = {
                    "score": quality_score,
                    "iteration": self.current_iteration,
                    "synthesis": synthesis_result,
                    "review": review_result
                }
                OutputFormatter.success(f"[BEST VERSION] New best score: {quality_score:.2f}/10 at iteration {self.current_iteration + 1}")
            
            # Calculate improvement trend
            improvement_info = self._analyze_improvement_trend()
            
            OutputFormatter.info(f"[ITERATION] Quality score: {quality_score:.2f}/10 (Threshold: {self.quality_threshold})")
            if improvement_info["has_previous"]:
                OutputFormatter.info(f"[ITERATION] Improvement: {improvement_info['delta']:+.2f} (Trend: {improvement_info['trend']})")
            
            # Check for regression (score decreased significantly)
            if improvement_info["trend"] == "regression":
                OutputFormatter.warning(f"[REGRESSION DETECTED] Score dropped by {abs(improvement_info['delta']):.2f} points!")
                if self.best_version["iteration"] >= 0:
                    OutputFormatter.info(f"[ROLLBACK] Reverting to best version from iteration {self.best_version['iteration'] + 1} (score: {self.best_version['score']:.2f})")
                    self._rollback_to_best_version()
                OutputFormatter.info(f"[ITERATION] Stopping iteration due to quality regression.")
                return TeamState.POLISH
            
            # Check if max iterations reached
            if self.current_iteration >= self.max_iterations - 1:
                OutputFormatter.warning(f"[ITERATION] Max iterations ({self.max_iterations}) reached. Proceeding to polish.")
                # If best version is not current, rollback before polishing
                if self.best_version["iteration"] != self.current_iteration and self.best_version["iteration"] >= 0:
                    OutputFormatter.info(f"[ROLLBACK] Using best version from iteration {self.best_version['iteration'] + 1} (score: {self.best_version['score']:.2f})")
                    self._rollback_to_best_version()
                return TeamState.POLISH
            
            # Check if quality threshold is met
            if quality_score >= self.quality_threshold:
                # Even if threshold is met, check if we can still improve
                if improvement_info["can_continue_improving"] and self.current_iteration < self.max_iterations - 1:
                    OutputFormatter.success(f"[ITERATION] Threshold met ({quality_score:.2f} >= {self.quality_threshold}), but further improvement possible!")
                    self.current_iteration += 1
                    OutputFormatter.info(f"[ITERATION] Continuing to iteration {self.current_iteration + 1}/{self.max_iterations} for quality optimization")
                    return TeamState.REVISION
                else:
                    OutputFormatter.success(f"[ITERATION] Quality threshold met! Proceeding to final polish.")
                    # If best version is not current, rollback before polishing
                    if self.best_version["iteration"] != self.current_iteration and self.best_version["iteration"] >= 0:
                        OutputFormatter.info(f"[ROLLBACK] Using best version from iteration {self.best_version['iteration'] + 1} (score: {self.best_version['score']:.2f})")
                        self._rollback_to_best_version()
                    return TeamState.POLISH
            
            # Need another iteration to reach threshold
            self.current_iteration += 1
            OutputFormatter.info(f"[ITERATION] Starting iteration {self.current_iteration + 1}/{self.max_iterations}")
            return TeamState.REVISION
        else:
            OutputFormatter.warning("[ITERATION] Could not extract quality score, proceeding to polish")
            return TeamState.POLISH
    
    def _rollback_to_best_version(self):
        """Rollback synthesis and review to the best version"""
        if self.best_version["synthesis"] is not None:
            self.results["synthesis"] = self.best_version["synthesis"]
            OutputFormatter.info(f"[ROLLBACK] Synthesis restored to iteration {self.best_version['iteration'] + 1}")
        if self.best_version["review"] is not None:
            self.results["review"] = self.best_version["review"]
            OutputFormatter.info(f"[ROLLBACK] Review restored to iteration {self.best_version['iteration'] + 1}")
        # Update current score to best score for final report
        if self.iteration_scores:
            self.iteration_scores[-1] = self.best_version["score"]
    
    def _analyze_improvement_trend(self) -> dict:
        """Analyze quality improvement trend across iterations"""
        scores = self.iteration_scores
        if len(scores) < 2:
            return {
                "has_previous": False,
                "delta": 0.0,
                "trend": "initial",
                "can_continue_improving": True
            }
        
        current = scores[-1]
        previous = scores[-2]
        delta = current - previous
        
        # Determine trend
        if delta >= 0.5:
            trend = "significant_improvement"
        elif delta > 0:
            trend = "modest_improvement"
        elif delta == 0:
            trend = "stagnant"
        else:
            trend = "regression"
        
        # Determine if we can continue improving
        # Continue if: making good progress, not yet at diminishing returns
        can_continue = (
            trend in ["significant_improvement", "modest_improvement"] and
            current < 9.5 and  # Don't push beyond 9.5 (excellent)
            len(scores) < self.max_iterations
        )
        
        return {
            "has_previous": True,
            "delta": delta,
            "trend": trend,
            "can_continue_improving": can_continue,
            "all_scores": scores.copy()
        }
    
    def _extract_actionable_items(self, review_content: str) -> List[str]:
        """Extract actionable improvement items using pre-compiled regex patterns."""
        actionable_items = []
        
        try:
            for key in ("suggestion_headers", "markdown_headers"):
                pattern = _ACTIONABLE_ITEM_PATTERNS[key]
                matches = pattern.findall(review_content)
                for match in matches:
                    item = match.strip() if isinstance(match, str) else match[0].strip()
                    if item and len(item) > 20:
                        first_sentence = _ACTIONABLE_FIRST_SENTENCE.split(item)[0]
                        actionable_items.append(first_sentence[:200])
            
            for key in ("missing_elements", "critical_concerns", "weaknesses"):
                pattern = _ACTIONABLE_ITEM_PATTERNS[key]
                match = pattern.search(review_content)
                if match:
                    bullets = match.group(1)
                    bullet_items = _ACTIONABLE_BULLET_SPLIT.findall(bullets)
                    for item in bullet_items:
                        item = item.strip()
                        if item and len(item) > 10:
                            actionable_items.append(item[:200])
            
            pattern = _ACTIONABLE_ITEM_PATTERNS["imperative_sentences"]
            matches = pattern.findall(review_content)
            for match in matches:
                item = match.strip() if isinstance(match, str) else match[0].strip()
                if item and item not in actionable_items:
                    actionable_items.append(item[:200])
            
            seen = set()
            unique_items = []
            for item in actionable_items:
                normalized = _ACTIONABLE_WHITESPACE_NORM.sub(' ', item.lower())
                if normalized not in seen and len(item) > 15:
                    seen.add(normalized)
                    unique_items.append(item)
            
            return unique_items[:15]
            
        except Exception as e:
            self.logger.warning(f"Failed to extract actionable items: {e}")
            return []
    
    def _extract_quality_score(self, review_content: str) -> Optional[float]:
        """Extract quality score from Markdown review content using pre-compiled patterns."""
        try:
            for pattern in _QUALITY_SCORE_PATTERNS:
                match = pattern.search(review_content)
                if match:
                    score = float(match.group(1))
                    if 0 <= score <= 10:
                        self.logger.info(f"✅ Quality score extracted from Markdown: {score}/10")
                        return score
                    else:
                        self.logger.warning(f"Invalid score range: {score}")
            
            fallback_match = _QUALITY_SCORE_FALLBACK.search(review_content)
            if fallback_match:
                score = float(fallback_match.group(1))
                if 0 <= score <= 10:
                    self.logger.warning(f"Score extracted from fallback pattern: {score}/10")
                    return score
            
            json_match = _QUALITY_SCORE_JSON.search(review_content)
            if json_match:
                score = float(json_match.group(1))
                if 0 <= score <= 10:
                    self.logger.info(f"Score extracted from legacy JSON format: {score}/10")
                    return score
            
            self.logger.error("❌ Failed to extract quality score from review")
            return None
            
        except (ValueError, TypeError) as e:
            self.logger.warning(f"Failed to extract quality score: {e}")
            return None
    
    async def _init_phase(self):
        """Initialization phase"""
        self.logger.info("Initializing hypothesis generation team")
        # Clear previous results
        self.results.clear()
        
        # Broadcast initialization message to all agents
        init_message = BaseMessage(
            role_name="Team Coordinator",
            role_type=OpenAIBackendRole.ASSISTANT,
            meta_dict={},
            content=f"Starting hypothesis generation for topic: {self.current_topic}"
        )
        
        await self.channel.broadcast_message(
            "Team Coordinator", 
            init_message, 
            list(self.agents.keys())
        )
    
    async def _literature_phase(self):
        """Literature review phase - executed by Scholar Scour with RAG integration"""
        
        OutputFormatter.section("PHASE 1: LITERATURE REVIEW (RAG-Enhanced)")
        OutputFormatter.info("[AGENT] Scholar Scour executing comprehensive literature review")
        
        scholar_agent = self.agents.get("Scholar Scour")
        if not scholar_agent:
            raise ValueError("Scholar Scour agent not found")
        
        # ===== RAG INTEGRATION: Retrieve fine-grained knowledge =====
        OutputFormatter.info("[RAG] Retrieving fine-grained knowledge from local knowledge base...")
        rag_evidence = ""
        try:
            import time
            import os
            rag_start = time.time()
            # 检查环境变量以支持消融实验
            enable_vector = os.environ.get("DISABLE_VECTOR_RETRIEVAL", "").lower() not in ("1", "true", "yes")
            enable_graph = os.environ.get("DISABLE_GRAPH_RETRIEVAL", "").lower() not in ("1", "true", "yes")
            
            rag_evidence = run_local_rag(
                query=self.current_topic,
                json_file_path='Myexamples/data/final_custom_kg_papers.json',
                base_vdb_path='Myexamples/vdb/camel_faiss_storage',
                build_if_missing=False,  # Don't build during execution to avoid delays
                enable_vector_retrieval=enable_vector,
                enable_graph_retrieval=enable_graph
            )
            rag_time = time.time() - rag_start
            OutputFormatter.success(f"[RAG] Retrieved {len(rag_evidence)} chars of evidence in {rag_time:.2f}s")
            
            # RAG evidence summary (avoid heavy console I/O)
            OutputFormatter.info(f"[RAG] Evidence summary: {len(rag_evidence)} chars retrieved in {rag_time:.2f}s")
            
            # Store RAG evidence for later use
            self.results["rag_evidence"] = self.result_processor.create_hypothesis_result(
                content=rag_evidence,
                failed=False,
                task_type="rag_retrieval",
                metadata={
                    "query": self.current_topic,
                    "evidence_length": len(rag_evidence),
                    "retrieval_time": rag_time
                }
            )
        except Exception as e:
            OutputFormatter.warning(f"[RAG] Failed to retrieve evidence: {e}")
            OutputFormatter.warning("[RAG] Continuing without RAG evidence (agent will use internal knowledge)")
            rag_evidence = "No RAG evidence available. Please rely on your internal knowledge and search tools."
        
        # Create detailed literature review task with RAG evidence
        literature_task = f"""
        Conduct a comprehensive literature review on '{self.current_topic}'. 
        
        ## RAG Evidence (Structured Context):
        {rag_evidence}
        
        ## Your Task:
        Please provide:
        1. Overview of existing research in this area (integrate RAG evidence with your knowledge)
        2. Key findings and methodologies from recent studies (extract from RAG evidence)
        3. Identified research gaps and limitations
        4. Theoretical frameworks and models
        5. Future research directions
        
      
        **CRITICAL INSTRUCTIONS**:
        - If Knowledge Graph Inspiration Paths are provided, use them as the **skeleton** (main structure) for your analysis.
        - Use Vector Search Evidence as **supporting details** to enrich each inspiration path.
        - Extract specific details: paper titles, authors, years, technical approaches, experimental results, datasets, core problems.
        - Maintain fine-grained technical details throughout.
        - Ensure traceability: reference specific sources from the evidence.
        -Extract specific details like:
        - Paper titles, authors, years from the evidence
        - Technical approaches and methodologies mentioned
        - Experimental results and datasets
        - Core problems and innovations
        
        Output should be a structured markdown report with clear sections and detailed citations.
        """
        
        OutputFormatter.info(f"Created RAG-enhanced literature review task for topic: {self.current_topic}")
        
        # Execute task with timing and detailed logging
        start_time = time.time()
        
        try:
            result = await self._execute_camel_native_task(scholar_agent, literature_task, "literature_review")
            execution_time = time.time() - start_time
            
            self.results["literature_review"] = result
            
            if not result.failed:
                OutputFormatter.success(f"Literature review completed in {execution_time:.2f} seconds")
                
                # Add result to workflow context manager
                self.workflow_context.add_phase_result(
                    phase_name="literature",
                    content=result.content,
                    role_name="Scholar Scour"
                )
                OutputFormatter.info("[CONTEXT] Added literature review to workflow context")
                
                # Debug info (aligned with backup version debug output)
                # raw_content = result.content
                # OutputFormatter.warning(f"[DEBUG] Raw result length: {len(raw_content)} chars")
                # OutputFormatter.info("Literature Review Content Preview:")
                # preview = raw_content[:500] + "..." if len(raw_content) > 500 else raw_content
                # print(f"{preview}")
                
            else:
                OutputFormatter.error(f"Literature review failed: {result.content}")
                raise RuntimeError(f"Literature review execution failed: {result.content}")
                
        except Exception as e:
            OutputFormatter.error(f"Error during literature review: {e}")
            # Create failure result
            self.results["literature_review"] = self.result_processor.create_hypothesis_result(
                content=f"Literature review failed: {str(e)}",
                failed=True,
                task_type="literature_review",
                metadata={"error": str(e), "agent": "Scholar Scour"}
            )
            raise
    
    async def _ideation_phase(self):
        """Creative ideation phase - executed by Idea Igniter with fine-grained context"""
        
        OutputFormatter.section("PHASE 2: CREATIVE IDEATION (Context-Preserved)")
        OutputFormatter.info("[AGENT] Idea Igniter executing creative hypothesis generation")
        
        idea_agent = self.agents.get("Idea Igniter")
        if not idea_agent:
            raise ValueError("Idea Igniter agent not found")
        
        # Get literature review results (real AI content transfer)
        literature_result = self.results.get("literature_review")
        if not literature_result or literature_result.failed:
            raise RuntimeError("Literature review not available or failed")
        
        literature_content = literature_result.content
        OutputFormatter.info(f"Using literature review input ({len(literature_content)} characters)")
        
        # Get RAG evidence to preserve fine-grained information
        rag_result = self.results.get("rag_evidence")
        rag_context = ""
        if rag_result and not rag_result.failed:
            rag_context = f"""
        
        ## Fine-Grained Reference Context (RAG Evidence):
        {rag_result.content}
        
        **NOTE**: The above RAG evidence contains specific technical details, datasets, 
        experimental results, and methodologies. Use these fine-grained details to ground 
        your creative ideas in concrete technical foundations.
        """
            OutputFormatter.info(f"Including RAG context ({len(rag_result.content)} characters) for grounding")
        
        # Create detailed creative ideation task (aligned with backup version)
        ideation_task = f"""
        Based on the literature review below, generate diverse and novel mechanisms and analogies for '{self.current_topic}'.
        
        Literature Review:
        {literature_content}
        {rag_context}
        
        Please provide:
        1. Novel theoretical frameworks or models (grounded in specific techniques from RAG evidence)
        2. Creative analogies from other domains (reference specific papers and approaches)
        3. Innovative methodological approaches (build upon datasets and experiments mentioned)
        4. Potential breakthrough hypotheses (cite specific technical details)
        5. Cross-disciplinary connections (leverage fine-grained knowledge)
        
        **CRITICAL**: Maintain fine-grained technical details throughout your ideation. 
        Reference specific papers, techniques, datasets, and results from the context above.
        
        Output should be a markdown list of creative ideas and potential hypotheses with detailed explanations.
        """
        
        OutputFormatter.info(f"Created ideation task based on literature review")
        
        # Execute task with timing and detailed logging
        start_time = time.time()
        
        try:
            result = await self._execute_camel_native_task(idea_agent, ideation_task, "ideation")
            execution_time = time.time() - start_time
            
            self.results["ideation"] = result
            
            if not result.failed:
                OutputFormatter.success(f"Creative ideation completed in {execution_time:.2f} seconds")
                
                # Add result to workflow context manager
                self.workflow_context.add_phase_result(
                    phase_name="ideation",
                    content=result.content,
                    role_name="Idea Igniter"
                )
                OutputFormatter.info("[CONTEXT] Added ideation to workflow context")
                
                # Debug info (aligned with backup version)
                # raw_content = result.content
                # OutputFormatter.warning(f"[DEBUG] Raw result length: {len(raw_content)} chars")
                # OutputFormatter.info("Generated Ideas Preview:")
                # preview = raw_content[:500] + "..." if len(raw_content) > 500 else raw_content
                # print(f"{preview}")
                
            else:
                OutputFormatter.error(f"Creative ideation failed: {result.content}")
                raise RuntimeError(f"Creative ideation execution failed: {result.content}")
                
        except Exception as e:
            OutputFormatter.error(f"Error during creative ideation: {e}")
            # Create failure result
            self.results["ideation"] = self.result_processor.create_hypothesis_result(
                content=f"Creative ideation failed: {str(e)}",
                failed=True,
                task_type="ideation",
                metadata={"error": str(e), "agent": "Idea Igniter"}
            )
            raise
    
    async def _analysis_phase(self):
        """Analysis and evaluation phase - three analysis agents execute in parallel with fine-grained context"""
        
        OutputFormatter.section("PHASE 3: PARALLEL ANALYSIS & EVALUATION (Context-Preserved)")
        OutputFormatter.info("[PARALLEL] Three analysis agents executing simultaneously")
        OutputFormatter.info("[AGENTS] Dr. Qwen Technical | Dr. Qwen Practical | Prof. Qwen Ethics")
        
        # Get ideation results (real AI content transfer)
        ideation_result = self.results.get("ideation")
        if not ideation_result or ideation_result.failed:
            raise RuntimeError("Ideation results not available or failed")
        
        ideation_content = ideation_result.content
        OutputFormatter.info(f"Analyzing generated ideas ({len(ideation_content)} characters)")
        
        # Get RAG evidence for fine-grained technical grounding
        rag_result = self.results.get("rag_evidence")
        rag_reference = ""
        if rag_result and not rag_result.failed:
            rag_reference = f"""
        
        ## Technical Reference Context (RAG Evidence):
        {rag_result.content}
        
        **NOTE**: Use the above fine-grained technical details to ground your analysis.
        Reference specific papers, methodologies, datasets, and results when evaluating feasibility.
        """
            OutputFormatter.info(f"Including RAG reference ({len(rag_result.content)} chars) for analysis grounding")
        
        # Define detailed analysis task configurations (aligned with backup version)
        analysis_configs = [
            {
                "agent_key": "Dr. Qwen Technical",
                "result_key": "technical_analysis",
                "task_prompt": f"""
                You are Dr. Qwen Technical, a senior technical analysis expert with deep expertise in scientific methodology and technical feasibility assessment.

                ## Your Task
                Perform comprehensive technical analysis of the scientific ideas provided below. Your analysis should be rigorous, evidence-based, and actionable.

                ## Ideas to Analyze
                {ideation_content}
                {rag_reference}

                ## Analysis Framework
                Evaluate the ideas across these critical dimensions:

                1. **Technical Plausibility** (1-10 scale): Assess scientific soundness and theoretical foundation
                2. **Methodological Consistency**: Evaluate internal logic and methodological coherence  
                3. **Implementation Complexity**: Analyze technical challenges and resource requirements
                4. **Technical Risk Assessment**: Identify potential failure points and mitigation strategies
                5. **Resource Requirements**: Specify expertise, equipment, and timeline needs

                ## Output Requirements
                **CRITICAL**: You must provide your analysis in the exact JSON format below. Do not include any text before or after the JSON.

                ```json
                {{
                  "technical_plausibility": {{
                    "score": "1-10",
                    "justification": "Detailed scientific reasoning for the score"
                  }},
                  "methodological_consistency": {{
                    "assessment": "Overall consistency evaluation",
                    "issues": ["List specific methodological concerns"]
                  }},
                  "implementation_complexity": {{
                    "level": "low/medium/high",
                    "details": "Specific technical challenges and requirements"
                  }},
                  "technical_risks": {{
                    "high_risks": ["List major technical risks"],
                    "mitigation_strategies": ["Corresponding mitigation approaches"]
                  }},
                  "required_resources": {{
                    "expertise": ["Required technical expertise areas"],
                    "equipment": ["Necessary equipment and infrastructure"],
                    "timeline": "Estimated development timeline"
                  }}
                }}
                ```

                Ensure your JSON is valid and complete. Focus on actionable insights that advance scientific understanding.
                """
            },
            {
                "agent_key": "Dr. Qwen Practical", 
                "result_key": "practical_analysis",
                "task_prompt": f"""
                You are Dr. Qwen Practical, a senior practical analysis expert specializing in experimental design, resource planning, and real-world implementation of scientific research.

                ## Your Task
                Perform comprehensive practical analysis of the scientific ideas provided below. Focus on experimental feasibility, resource requirements, and implementation roadmap.

                ## Ideas to Analyze
                {ideation_content}
                {rag_reference}

                ## Analysis Framework
                Evaluate the ideas across these practical dimensions:

                1. **Falsifiability Assessment** (1-10 scale): Can the hypothesis be empirically tested?
                2. **Experimental Feasibility**: What experiments are needed and how feasible are they?
                3. **Resource Requirements**: Detailed budget, personnel, and equipment analysis
                4. **Timeline Planning**: Realistic phases, milestones, and duration estimates
                5. **Risk Management**: Identify obstacles and provide practical solutions

                ## Output Requirements
                **CRITICAL**: You must provide your analysis in the exact JSON format below. Do not include any text before or after the JSON.

                ```json
                {{
                  "falsifiability": {{
                    "score": "1-10",
                    "justification": "Detailed reasoning for falsifiability score"
                  }},
                  "experimental_feasibility": {{
                    "assessment": "Overall feasibility evaluation",
                    "challenges": ["List specific experimental challenges"]
                  }},
                  "resource_requirements": {{
                    "budget": "Estimated budget range and breakdown",
                    "personnel": ["Required team members and expertise"],
                    "equipment": ["Necessary equipment and facilities"]
                  }},
                  "timeline": {{
                    "phases": ["List project phases"],
                    "milestones": ["Key milestones and deliverables"],
                    "total_duration": "Realistic project duration"
                  }},
                  "obstacles_solutions": {{
                    "potential_obstacles": ["List major implementation obstacles"],
                    "proposed_solutions": ["Corresponding practical solutions"]
                  }}
                }}
                ```

                Focus on actionable implementation strategies and realistic resource planning.
                """
            },
            {
                "agent_key": "Prof. Qwen Ethics",
                "result_key": "significance_analysis", 
                "task_prompt": f"""
                You are Prof. Qwen Ethics, a distinguished ethics and impact assessment expert with extensive experience in evaluating the broader implications of scientific research and technological innovation.

                ## Your Task
                Perform comprehensive significance and ethical analysis of the scientific ideas provided below. Evaluate scientific impact, societal implications, and ethical considerations with rigorous attention to responsible research practices.

                ## Ideas to Analyze
                {ideation_content}
                {rag_reference}

                ## Analysis Framework
                Evaluate the ideas across these critical dimensions:

                1. **Scientific Significance** (1-10 scale): Assess potential contribution to scientific knowledge
                2. **Broader Impact Assessment**: Evaluate positive and negative societal implications
                3. **Ethical Analysis**: Identify ethical concerns and necessary safeguards
                4. **Risk-Benefit Evaluation**: Balance potential benefits against risks
                5. **Long-term Consequences**: Consider future implications and uncertainties

                ## Output Requirements
                **CRITICAL**: You must provide your analysis in the exact JSON format below. Do not include any text before or after the JSON.

                ```json
                {{
                  "scientific_significance": {{
                    "score": "1-10",
                    "justification": "Detailed assessment of scientific contribution and novelty"
                  }},
                  "broader_impact": {{
                    "positive_impacts": ["List potential positive societal impacts"],
                    "negative_impacts": ["List potential negative consequences"]
                  }},
                  "ethical_implications": {{
                    "concerns": ["List specific ethical concerns and dilemmas"],
                    "safeguards": ["Recommended ethical safeguards and guidelines"]
                  }},
                  "societal_benefits_risks": {{
                    "benefits": ["List concrete societal benefits"],
                    "risks": ["List potential societal risks"],
                    "mitigation": ["Risk mitigation strategies"]
                  }},
                  "long_term_consequences": {{
                    "predictions": ["Long-term impact predictions"],
                    "uncertainty_factors": ["Key uncertainties and unknowns"]
                  }}
                }}
                ```

                Focus on responsible research practices and comprehensive impact assessment.
                """
            }
        ]
        
        # Execute parallel analysis with timing
        start_time = time.time()
        
        try:
            # Create parallel tasks
            parallel_tasks = []
            for config in analysis_configs:
                agent = self._get_agent_by_role_pattern(config["agent_key"])
                if agent:
                    OutputFormatter.info(f"Starting {config['agent_key']} analysis...")
                    task = self._execute_camel_native_task(
                        agent, 
                        config["task_prompt"],
                        config["result_key"]
                    )
                    parallel_tasks.append((config, task))
                else:
                    raise ValueError(f"Agent not found: {config['agent_key']}")
            
            # Execute all analysis tasks in parallel
            OutputFormatter.info("Executing parallel analysis tasks...")
            results = await asyncio.gather(*[task for _, task in parallel_tasks], return_exceptions=True)
            
            execution_time = time.time() - start_time
            
            # Process parallel execution results
            analysis_results = []
            for i, (config, result) in enumerate(zip([config for config, _ in parallel_tasks], results)):
                if isinstance(result, Exception):
                    OutputFormatter.error(f"{config['agent_key']} analysis failed: {result}")
                    raise result
                else:
                    OutputFormatter.success(f"{config['agent_key']} analysis completed")
                    analysis_results.append(result.content)
                    
                    # Debug info for each analysis (aligned with backup version)
                    # OutputFormatter.warning(f"[DEBUG] {config['agent_key']} result length: {len(result.content)} chars")
                    # OutputFormatter.info(f"{config['agent_key']} Analysis Preview:")
                    # preview = result.content[:300] + "..." if len(result.content) > 300 else result.content
                    # print(f"{preview}")
            
            # Combine all analysis results
            combined_analysis = "\n\n".join([
                f"## {config['agent_key']} Analysis\n{result}" 
                for config, result in zip([config for config, _ in parallel_tasks], analysis_results)
            ])
            
            self.results["analysis"] = self.result_processor.create_hypothesis_result(
                content=combined_analysis,
                failed=False,
                task_type="parallel_analysis",
                metadata={
                    "agents": [config["agent_key"] for config, _ in parallel_tasks],
                    "execution_mode": "parallel",
                    "timestamp": datetime.now().isoformat(),
                    "execution_time": execution_time
                }
            )
            
            OutputFormatter.success(f"Parallel analysis completed in {execution_time:.2f} seconds")
            
            # Add combined analysis to workflow context manager (CRITICAL - was missing in V1!)
            self.workflow_context.add_phase_result(
                phase_name="analysis",
                content=combined_analysis,
                role_name="Analysis Team"
            )
            OutputFormatter.info("[CONTEXT] Added parallel analysis to workflow context")
            
            OutputFormatter.info("Combined Analysis Preview:")
            preview = combined_analysis[:500] + "..." if len(combined_analysis) > 500 else combined_analysis
            print(f"{preview}")
                    
        except Exception as e:
            OutputFormatter.error(f"Parallel analysis execution failed: {e}")
            # Create failure result
            self.results["analysis"] = self.result_processor.create_hypothesis_result(
                content=f"Parallel analysis failed: {str(e)}",
                failed=True,
                task_type="parallel_analysis",
                metadata={"error": str(e)}
            )
            raise
    
    async def _execute_camel_native_task(self, agent: CamelNativeAgent, task_content: str, result_key: str) -> HypothesisTaskResult:
        """
        CAMEL native task execution method - Based on FIG-MAC step_async mechanism
        Utilizing BaseAgent's native asynchronous methods and ChatAgentResponse mechanism
        Integrated CAMEL native error handling and timeout mechanisms
        """
        try:
            # Create CAMEL native message
            task_message = BaseMessage(
                role_name="Team Coordinator",
                role_type=OpenAIBackendRole.USER,
                meta_dict={
                    "task_id": result_key,
                    "team_state": self.state.value,
                    "timestamp": datetime.now().isoformat()
                },
                content=task_content
            )
            
            # Use correct CAMEL native API for memory updates (FIG-MAC mode)
            if hasattr(agent, 'update_memory'):
                agent.update_memory(task_message, OpenAIBackendRole.USER)
                self.logger.info(f"Updated CAMEL memory with task message for {agent.role_name}")
            
            # Get CAMEL native intelligent context (FIG-MAC mode)
            if hasattr(agent, 'get_context_with_tokens'):
                full_context, total_tokens = agent.get_context_with_tokens()
                self.logger.info(f"CAMEL context: {total_tokens} tokens for {agent.role_name}")
                max_input_tokens = self.workflow_context.token_limit
                if total_tokens > max_input_tokens:
                    debug_path = self._dump_context_debug(agent.role_name, full_context, total_tokens)
                    self.logger.warning(
                        "Context tokens exceed %d for %s (tokens=%s). Dumped to %s",
                        max_input_tokens,
                        agent.role_name,
                        total_tokens,
                        debug_path,
                    )
            
            # Use CAMEL native step_async method (FIG-MAC mode)
            # 注意：已移除超时限制，允许任务完整运行
            # 如果环境变量设置了超时，则使用；否则不设置超时（None表示无超时）
            task_timeout_str = os.environ.get("AGENT_TASK_TIMEOUT")
            camel_timeout = os.environ.get("CAMEL_MODEL_TIMEOUT", "600 (default)")
            
            if task_timeout_str:
                task_timeout = int(task_timeout_str)
                OutputFormatter.info(f"[TIMEOUT] Using AGENT_TASK_TIMEOUT: {task_timeout}s | CAMEL_MODEL_TIMEOUT: {camel_timeout}s")
                response = await asyncio.wait_for(
                    agent.step_async(task_message),
                    timeout=task_timeout
                )
            else:
                # 无超时限制，直接执行
                OutputFormatter.info(f"[TIMEOUT] No task timeout set | CAMEL_MODEL_TIMEOUT: {camel_timeout}s")
                response = await agent.step_async(task_message)
            
            # Also add response to CAMEL native memory history (FIG-MAC mode)
            if hasattr(agent, 'update_memory'):
                agent.update_memory(response.msg, OpenAIBackendRole.ASSISTANT)
                self.logger.info(f"Updated CAMEL memory with response for {agent.role_name}")
            
            # CAMEL记忆系统记录 (阶段3.7重构 - 基于FIG-MAC经验)
            phase = self._get_current_phase_name()
            memory_id = self.camel_memory_manager.record_agent_conversation(
                phase=phase,
                agent_name=agent.role_name,
                message=task_message,
                response=response
            )
            
            # 简单内容提取 (FIG-MAC方法：从复杂提取转向简单保存)
            ai_content = response.msgs[0].content if response.msgs else ""
            is_real_ai = ai_content and not ai_content.startswith("Response to:")
            
            if not is_real_ai:
                self.logger.warning(f"Detected simulated response from {agent.role_name}: {ai_content[:100]}...")
                raise RuntimeError(f"Agent {agent.role_name} returned simulated response instead of real AI generation")
            
            # 创建简化结果 (基于CAMEL原生响应)
            result = self.result_processor.create_hypothesis_result(
                content=ai_content,
                failed=False,
                task_type="camel_native_task",
                metadata={
                    "agent_name": agent.role_name,
                    "phase": phase,
                    "memory_id": memory_id,
                    "response_info": response.info if hasattr(response, 'info') else {},
                    "content_length": len(ai_content),
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # 兼容性：仍然记录到原有工作流管理器
            output_id = self.output_manager.record_phase_output(
                phase=phase,
                agent_name=agent.role_name,
                content=ai_content,
                metadata=result.metadata,
                structured_sections={}
            )
            
            # Store result to team results dictionary
            self.results[result_key] = result
            
            self.logger.info(
                f"CAMEL native task completed for {agent.role_name} -> {result_key} "
                f"(Memory ID: {memory_id}, Output ID: {output_id})"
            )
            return result
            
        except asyncio.TimeoutError:
            # CAMEL native timeout handling (仅在设置了超时的情况下才会触发)
            task_timeout_str = os.environ.get("AGENT_TASK_TIMEOUT", "无限制")
            self.logger.warning(f"Task timeout for agent {agent.role_name} after {task_timeout_str} seconds")
            
            timeout_result = self.result_processor.create_hypothesis_result(
                content=f"Task execution timed out after {task_timeout_str} seconds",
                failed=True,
                task_type="camel_native_task",
                metadata={
                    "agent": agent.role_name,
                    "result_key": result_key,
                    "error": "timeout",
                    "execution_mode": "camel_native_parallel",
                    "timestamp": datetime.now().isoformat(),
                    "timeout_seconds": task_timeout_str
                }
            )
            
            self.results[result_key] = timeout_result
            return timeout_result
            
        except Exception as e:
            # CAMEL native exception handling - BaseAgent automatically handles common exceptions and retries
            error_msg = str(e)
            self.logger.error(f"CAMEL native task failed for {agent.role_name}: {e}")
            
            # Detect API timeout (DashScope / OpenAI style) and return graceful failure instead of crashing
            if "timeout" in error_msg.lower() or "timed out" in error_msg.lower() or "RequestTimeOut" in error_msg:
                self.logger.warning(
                    f"API timeout detected for {agent.role_name}. Returning failed result instead of raising."
                )
                timeout_result = self.result_processor.create_hypothesis_result(
                    content=f"API request timed out: {error_msg}",
                    failed=True,
                    task_type="camel_native_task",
                    metadata={
                        "agent": agent.role_name,
                        "result_key": result_key,
                        "error": "api_timeout",
                        "error_detail": error_msg,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                self.results[result_key] = timeout_result
                return timeout_result
            
            # Create failure result using result processor for non-timeout errors
            failed_result = self.result_processor.create_hypothesis_result(
                content=f"Task execution failed: {str(e)}",
                failed=True,
                task_type="camel_native_task",
                metadata={
                    "agent": agent.role_name,
                    "result_key": result_key,
                    "error": str(e),
                    "execution_mode": "camel_native_parallel",
                    "camel_native_retry": True  # Mark as using CAMEL native retry
                }
            )
            
            # Store result even if failed
            self.results[result_key] = failed_result
            return failed_result

    def _dump_context_debug(self, agent_name: str, context_messages: List[Any], total_tokens: int) -> Path:
        """Dump oversized context to a JSON file for inspection."""
        try:
            self.debug_context_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_agent = agent_name.replace(" ", "_")
            file_path = self.debug_context_dir / f"context_{safe_agent}_{timestamp}.json"

            serializable_msgs: List[Any] = []
            for msg in context_messages:
                if hasattr(msg, "to_dict"):
                    serializable_msgs.append(msg.to_dict())
                elif isinstance(msg, dict):
                    serializable_msgs.append(msg)
                else:
                    serializable_msgs.append(str(msg))

            payload = {
                "agent": agent_name,
                "total_tokens": total_tokens,
                "message_count": len(context_messages),
                "messages": serializable_msgs,
            }

            with file_path.open("w", encoding="utf-8") as fout:
                json.dump(payload, fout, ensure_ascii=False, indent=2)

            return file_path
        except Exception as exc:
            self.logger.error("Failed to dump context debug for %s: %s", agent_name, exc)
            return Path()
    
    def _get_agent_by_role_pattern(self, role_pattern: str) -> CamelNativeAgent:
        """
        Strict agent matching system - EXACT MATCH ONLY
        No fuzzy matching to prevent incorrect agent selection
        """
        # ONLY exact match allowed
        if role_pattern in self.agents:
            agent = self.agents[role_pattern]
            self.logger.info(f"[AGENT MATCH] Exact match found: {role_pattern}")
            return self._validate_agent(agent, role_pattern)
        
        # No match found - STRICT ERROR REPORTING
        self.logger.error(f"[AGENT MATCH ERROR] No exact match found for: '{role_pattern}'")
        self.logger.error(f"[AGENT MATCH ERROR] Available agents: {list(self.agents.keys())}")
        self._log_agent_details()
        
        # Raise exception instead of returning None
        raise ValueError(f"Agent '{role_pattern}' not found. Available agents: {list(self.agents.keys())}")
    
    def _validate_agent(self, agent: CamelNativeAgent, pattern: str) -> CamelNativeAgent:
        """Validate agent functionality and readiness"""
        try:
            # Check if agent has required methods
            required_methods = ['step_async', 'role_name']
            for method in required_methods:
                if not hasattr(agent, method):
                    self.logger.warning(f"[AGENT VALIDATION] Agent {pattern} missing method: {method}")
            
            # Check agent status
            if hasattr(agent, 'role_name'):
                self.logger.info(f"[AGENT VALIDATION] Agent {pattern} validated successfully: {agent.role_name}")
            
            return agent
        except Exception as e:
            self.logger.error(f"[AGENT VALIDATION] Agent {pattern} validation failed: {e}")
            return agent
    
    def _log_agent_details(self):
        """Log detailed information about all available agents"""
        self.logger.info("[AGENT DETAILS] Complete agent inventory:")
        for i, (key, agent) in enumerate(self.agents.items(), 1):
            role_name = getattr(agent, 'role_name', 'Unknown')
            agent_type = type(agent).__name__
            self.logger.info(f"  {i}. Key: '{key}' | Role: '{role_name}' | Type: {agent_type}")
    
    async def _synthesis_phase(self):
        """Synthesis phase - executed by Dr. Qwen Leader with fine-grained context preservation"""
        
        OutputFormatter.section("PHASE 4: HYPOTHESIS SYNTHESIS (Fine-Grained Context Preserved)")
        OutputFormatter.info("[AGENT] Dr. Qwen Leader executing comprehensive synthesis")
        
        leader_agent = self.agents.get("Dr. Qwen Leader")
        if not leader_agent:
            raise ValueError("Dr. Qwen Leader agent not found")
        
        # Get context from workflow context manager instead of string concatenation
        context_string, context_tokens = self.workflow_context.get_context_as_string("synthesis")
        token_count, token_limit = self.workflow_context.get_token_usage()
        usage_percent = (token_count / token_limit) * 100 if token_limit > 0 else 0
        
        OutputFormatter.info(f"[TOKEN] SYNTHESIS: {token_count}/{token_limit} ({usage_percent:.1f}%)")
        if usage_percent > 95:
            OutputFormatter.warning(f"[CRITICAL] Token usage exceeds 95%!")
        OutputFormatter.info(f"[CONTEXT] Retrieved workflow context: {context_tokens} tokens")
        
        # Include RAG evidence separately (not in workflow context to avoid duplication)
        rag_context = ""
        rag_result = self.results.get("rag_evidence")
        if rag_result and not rag_result.failed:
            rag_context = f"""
        
        ## Fine-Grained Technical Foundation (RAG Evidence):
        {rag_result.content}
        
        **CRITICAL INSTRUCTIONS**:
        - If Knowledge Graph Inspiration Paths are provided, use them as the **skeleton** for organizing your synthesis.
        - Use Vector Search Evidence to provide **supporting details** (specific papers, methods, datasets, results).
        - Synthesize both sources: combine cross-domain insights (from graph) with specific technical details (from vector).
        
        **CRITICAL**: The above RAG evidence contains specific technical details that MUST be preserved 
        in your synthesis. Include concrete references to:
        - Specific papers, authors, and publication years
        - Exact technical approaches and methodologies
        - Specific datasets and experimental results
        - Precise technical terminology and frameworks
        """
            OutputFormatter.info(f"Including RAG context ({len(rag_result.content)} chars) for synthesis grounding")
        
        # Create detailed synthesis task using workflow context
        # STRATEGY: Pass RAG evidence directly (not through context manager) to avoid truncation
        synthesis_task = f"""
You are Dr. Qwen Leader, Chief Researcher. Synthesize a comprehensive scientific hypothesis for '{self.current_topic}'.

## 1. WORKFLOW CONTEXT (Previous Phase Results):
{context_string}

{rag_context}

## 2. SYNTHESIS REQUIREMENTS

Create a publication-ready scientific hypothesis report with the following structure:

### Executive Summary
- 2-3 sentences capturing the core hypothesis
- Reference the most important source paper from RAG evidence

### Background and Rationale  
- Synthesize the research gap identified in literature
- Cite specific papers and their limitations
- Build the logical case for your hypothesis

### Detailed Hypothesis (THIS SECTION IS CRITICAL)

**Core Mechanism** (2-3 paragraphs - SYNTHESIZE FROM MULTIPLE IDEAS):
- **Integrate mechanisms from multiple ideas**: Don't just describe one idea's mechanism; show how mechanisms from different ideas can work together
- What are the key components? How do they interact?
- Use LaTeX for mathematical formulations
- Reference specific techniques from RAG evidence AND from different ideas (e.g., "Combining the hierarchical gating from Idea 1 with the attention mechanism from Idea 3...")
- Example: If Idea 1 proposes gating mechanism G and Idea 2 proposes attention mechanism A, describe a hybrid G+A approach

**Technical Innovations** (INTEGRATE FROM ALL IDEAS - Bullet points with explanations):
**CRITICAL**: Do NOT limit yourself to a single idea from the ideation phase. Extract and synthesize technical innovations from ALL promising ideas:

List 5-8 specific technical innovations. For each:
- **What**: The specific technique/method (can be from Idea 1, Idea 2, etc.)
- **Why**: How it addresses the research gap
- **How**: Concrete implementation details from RAG (algorithms, equations, architectures)
- **Source**: Which idea(s) this innovation comes from

**Integration Strategy**:
- If Idea 1 proposes mechanism X and Idea 3 proposes mechanism Y, consider: "Can X and Y work together?"
- Combine complementary approaches into hybrid mechanisms
- Layer multiple innovations: foundation technique + enhancement A + enhancement B

**Testable Predictions** (Quantitative where possible):
- Prediction 1: "X will achieve Y% improvement over baseline Z"
- Prediction 2: "Mechanism A will show B effect under C conditions"
- Include expected effect sizes, performance thresholds

### Supporting Analysis
- Integrate technical feasibility assessment
- Reference specific implementation challenges from RAG
- Build unified argument for plausibility

### Methodology
- Proposed experimental approach
- Specific datasets (cite from RAG)
- Baselines for comparison (cite from RAG)
- Evaluation metrics

### Expected Outcomes
- Predicted results grounded in prior work
- Implications for the field

### Limitations & Future Directions
- Acknowledged constraints
- Clear next steps

## 3. CRITICAL SUCCESS CRITERIA

1. **TECHNICAL DEPTH**: The Detailed Hypothesis section should be the longest and most detailed section (minimum 40% of total content)

2. **RAG INTEGRATION**: Every subsection must reference specific papers, methods, or findings from the RAG evidence provided above

3. **NO VAGUE CLAIMS**: Instead of "improved performance", say "F1 score improvement of 5-8% over Cross-Stitch Networks baseline"

4. **CONCRETE MECHANISMS**: Describe exactly HOW your proposed mechanism works, not just WHAT it does

## 4. ANTI-PATTERNS (AVOID THESE)

❌ BAD: "We propose a novel gating mechanism that improves performance"
✅ GOOD: "We propose HGAN, which extends GBM's [cite] hierarchical gating with layer-wise attention scores computed as $a_l = {{\\sigma}}(W_a h_l + b_a)$, enabling fine-grained information routing..."

❌ BAD: "Our method will perform better than existing approaches"
✅ GOOD: "HGAN is expected to achieve 85-87% F1 on SemEval-2014 Task 4, compared to 82% for GBM [cite] and 79% for Cross-Stitch Networks [cite]"

---

**OUTPUT**: Complete scientific hypothesis report following the structure above.
"""
        
        OutputFormatter.info("Created comprehensive synthesis task")
        
        # Execute synthesis with timing
        start_time = time.time()
        
        try:
            result = await self._execute_camel_native_task(leader_agent, synthesis_task, "synthesis")
            execution_time = time.time() - start_time
            
            self.results["synthesis"] = result
            
            if not result.failed:
                OutputFormatter.success(f"Hypothesis synthesis completed in {execution_time:.2f} seconds")
                
                # Add synthesis result to workflow context manager
                self.workflow_context.add_phase_result(
                    phase_name="synthesis",
                    content=result.content,
                    role_name="Dr. Qwen Leader"
                )
                OutputFormatter.info("[CONTEXT] Added synthesis to workflow context")
                
                # Debug info (aligned with backup version)
                raw_content = result.content
                # OutputFormatter.warning(f"[DEBUG] Raw result length: {len(raw_content)} chars")
                # OutputFormatter.info("Synthesized Hypothesis Preview:")
                # preview = raw_content[:500] + "..." if len(raw_content) > 500 else raw_content
                # print(f"{preview}")
                
            else:
                OutputFormatter.error(f"Hypothesis synthesis failed: {result.content}")
                raise RuntimeError(f"Synthesis execution failed: {result.content}")
                
        except Exception as e:
            OutputFormatter.error(f"Error during hypothesis synthesis: {e}")
            # Create failure result
            self.results["synthesis"] = HypothesisTaskResult(
                content=f"Hypothesis synthesis failed: {str(e)}",
                failed=True,
                task_type="synthesis",
                metadata={"error": str(e), "agent": "Dr. Qwen Leader"}
            )
            raise
    
    async def _review_phase(self):
        """Peer review phase - executed by Critic Crucible"""
        
        OutputFormatter.section("PHASE 5: PEER REVIEW")
        OutputFormatter.info("[AGENT] Critic Crucible executing peer review")
        
        critic_agent = self.agents.get("Critic Crucible")
        if not critic_agent:
            raise ValueError("Critic Crucible agent not found")
        
        # FIX: Clear Critic Crucible's chat history to ensure independent evaluation each time
        # IMPORTANT: Only clear memory (chat history), NOT personality_memory (system prompt)
        # personality_memory contains the agent's role definition ("Senior Reviewer for top-tier journal...")
        # Clearing it would make the agent forget its role and evaluation standards
        if hasattr(critic_agent, 'memory') and critic_agent.memory:
            critic_agent.memory.clear()
            self.logger.info("[ITERATION FIX] Critic Crucible chat history cleared (personality/system prompt preserved)")
        
        # Get synthesis from workflow context
        # We only need the latest synthesis, so retrieve it from workflow context
        synthesis_result = self.results.get("synthesis")
        if not synthesis_result or synthesis_result.failed:
            raise RuntimeError("Synthesis result not available or failed")
        
        synthesis_content = synthesis_result.content
        OutputFormatter.info(f"Reviewing synthesized hypothesis ({len(synthesis_content)} characters)")
        
        # Create detailed review task (aligned with backup version, including JSON format requirements)
        review_task = f"""
        Perform comprehensive peer review of the following scientific hypothesis. Provide detailed feedback and quality assessment.
        
        Hypothesis to Review:
        {synthesis_content}
        
        Please provide a thorough peer review that includes:
        1. **Overall Quality Score** (1-10 scale): Overall assessment of hypothesis quality
        2. **Strengths**: What are the strong points of this hypothesis?
        3. **Weaknesses**: What are the limitations or problems?
        4. **Technical Soundness** (1-10 scale): Is the methodology technically sound?
        5. **Novelty Assessment** (1-10 scale): How novel and original is this work?
        6. **Clarity and Presentation** (1-10 scale): How clear and well-presented is it?
        7. **Detailed Improvement Suggestions**: For each issue, provide:
           - The specific problem
           - Concrete, actionable solution with implementation steps
           - Expected impact on hypothesis quality
           - Specific technical details (algorithms, datasets, baselines, equations, etc.)
        8. **Missing Elements**: What important aspects are completely absent?
        9. **Recommendation**: Accept/Revise/Reject with detailed justification
        
        **CRITICAL for Improvement Suggestions**: 
        - Each suggestion MUST be actionable and specific (not vague like "add more details")
        - Include concrete steps: what sections to add, what equations to include, what baselines to compare against
        - Provide technical details: specific algorithm names, dataset names, hyperparameter ranges, evaluation metrics
        
        **BAD Examples** (too vague): ❌
        - "Include more empirical evidence"
        - "Provide more details on implementation"
        - "Add more references"
        
        **GOOD Examples** (specific and actionable): ✅
        - "Add Baseline Comparison subsection comparing GBM against: (1) Cross-stitch Networks [Ruder+ 2017], (2) MMoE [Ma+ 2018], (3) Hard Parameter Sharing. Include architectural diagrams and expected performance ranges for each."
        - "In Section 3.2 'Gate Mechanisms', add mathematical formulations for reset gate (Equation 1) and update gate (Equation 2) with explicit dimensionality notation (e.g., h ∈ R^d)"
        - "Expand Dataset section to specify: (a) SemEval-2014 Task 4 exact splits (train: 3,045, test: 800), (b) preprocessing steps (tokenization method, max sequence length), (c) data augmentation strategies if any"
        
        Please structure your review as a detailed markdown report with clear sections and specific feedback.
        
        **CRITICAL OUTPUT REQUIREMENT**: 
        Include "Quality Score: X.X/10" in the Overall Assessment section at the beginning of your review.
        This score is essential for our iterative improvement system to determine whether revision is needed.
        """
        
        OutputFormatter.info("Created comprehensive peer review task")
        
        # Execute review with timing
        start_time = time.time()
        
        try:
            result = await self._execute_camel_native_task(critic_agent, review_task, "review")
            execution_time = time.time() - start_time
            
            self.results["review"] = result
            
            if not result.failed:
                OutputFormatter.success(f"Peer review completed in {execution_time:.2f} seconds")
                
                # Add review result to workflow context manager
                self.workflow_context.add_phase_result(
                    phase_name="review",
                    content=result.content,
                    role_name="Critic Crucible"
                )
                OutputFormatter.info("[CONTEXT] Added review to workflow context")
                
                # Debug info (aligned with backup version)
                raw_content = result.content
                # OutputFormatter.warning(f"[DEBUG] Raw result length: {len(raw_content)} chars")
                
                # Extract quality score from Markdown review
                quality_score = self._extract_quality_score(raw_content)
                if quality_score:
                    OutputFormatter.success(f"Review complete. Quality score: {quality_score}/10")
                else:
                    OutputFormatter.warning("Could not extract quality score from review")
                
                # Content preview
                OutputFormatter.info("Peer Review Preview:")
                preview = raw_content[:500] + "..." if len(raw_content) > 500 else raw_content
                print(f"{preview}")
                
            else:
                OutputFormatter.error(f"Peer review failed: {result.content}")
                raise RuntimeError(f"Review execution failed: {result.content}")
                
        except Exception as e:
            OutputFormatter.error(f"Error during peer review: {e}")
            # Create failure result
            self.results["review"] = HypothesisTaskResult(
                content=f"Peer review failed: {str(e)}",
                failed=True,
                task_type="review",
                metadata={"error": str(e), "agent": "Critic Crucible"}
            )
            raise
    
    async def _revision_phase(self):
        """Revision phase - iterative improvement based on review feedback (FIG-MAC style)"""
        
        OutputFormatter.section(f"PHASE 5.{self.current_iteration + 1}: ITERATIVE REVISION (Iteration {self.current_iteration + 1}/{self.max_iterations})")
        OutputFormatter.info("[AGENT] Dr. Qwen Leader executing hypothesis revision")
        
        leader_agent = self.agents.get("Dr. Qwen Leader")
        if not leader_agent:
            raise ValueError("Dr. Qwen Leader agent not found")
        
        # Get current synthesis and review results
        synthesis_result = self.results.get("synthesis")
        review_result = self.results.get("review")
        
        if not synthesis_result or synthesis_result.failed:
            raise RuntimeError("Synthesis result not available or failed")
        if not review_result or review_result.failed:
            raise RuntimeError("Review result not available or failed")
        
        synthesis_content = synthesis_result.content
        review_content = review_result.content
        
        # Extract specific feedback for revision
        quality_score = self._extract_quality_score(review_content)
        
        OutputFormatter.info(f"Revising hypothesis based on peer review feedback")
        if quality_score is not None:
            OutputFormatter.info(f"Current quality score: {quality_score:.2f}/10")
        else:
            OutputFormatter.warning("Current quality score: N/A (extraction failed)")
        OutputFormatter.info(f"Target threshold: {self.quality_threshold}/10")
        OutputFormatter.info(f"Original hypothesis: {len(synthesis_content)} characters")
        OutputFormatter.info(f"Review feedback: {len(review_content)} characters")
        
        # Use workflow context to provide structured context with proper prioritization
        # Pass complete synthesis to WorkflowContextManager
        # Let CAMEL's ScoreBasedContextCreator intelligently manage truncation
        # Review feedback gets highest score (1.0) as it's added last, ensuring it's prioritized
        
        # Add structured context: complete synthesis first, then full review feedback
        self.workflow_context.add_structured_context([
            {
                "phase_name": "synthesis_for_revision",
                "content": synthesis_content,  # Pass complete synthesis without hardcoded truncation
                "role_name": "Dr. Qwen Leader"
            },
            {
                "phase_name": "review_feedback",
                "content": review_content,
                "role_name": "Critic Crucible"
            }
        ])
        OutputFormatter.info("[CONTEXT] Added complete synthesis and review feedback to workflow context")
        OutputFormatter.info(f"[CONTEXT] Synthesis length: {len(synthesis_content)} chars, Review length: {len(review_content)} chars")
        
        # Get context from workflow context manager
        context_string, context_tokens = self.workflow_context.get_context_as_string("revision")
        token_count, token_limit = self.workflow_context.get_token_usage()
        usage_percent = (token_count / token_limit) * 100 if token_limit > 0 else 0
        
        OutputFormatter.info(f"[TOKEN] REVISION: {token_count}/{token_limit} ({usage_percent:.1f}%)")
        if usage_percent > 95:
            OutputFormatter.warning(f"[CRITICAL] Token usage exceeds 95%! Context truncation will occur!")
        elif usage_percent > 85:
            OutputFormatter.warning(f"[WARNING] Token usage exceeds 85%! Risk of losing early context!")
        elif usage_percent > 70:
            OutputFormatter.info(f"[INFO] Token usage is high ({usage_percent:.1f}%). Consider reducing iteration count.")
            
        OutputFormatter.info(f"[CONTEXT] Retrieved workflow context for revision: {context_tokens} tokens")
        OutputFormatter.info(f"[CONTEXT] Context string length: {len(context_string)} chars")
        
        # Log if truncation occurred
        original_total_length = len(synthesis_content) + len(review_content)
        if len(context_string) < original_total_length:
            truncated_amount = original_total_length - len(context_string)
            truncation_percent = (truncated_amount / original_total_length) * 100
            OutputFormatter.warning(f"[CONTEXT] Content truncated: {truncated_amount} chars ({truncation_percent:.1f}%)")
            OutputFormatter.info("[CONTEXT] Note: CAMEL's ScoreBasedContextCreator prioritizes review_feedback (highest score)")
        else:
            OutputFormatter.success("[CONTEXT] Complete content preserved (no truncation)")
        
        # Extract actionable items from review for tracking
        actionable_items = self._extract_actionable_items(review_content)
        if actionable_items:
            OutputFormatter.info(f"[REVISION] Extracted {len(actionable_items)} actionable improvement items from review")
            for i, item in enumerate(actionable_items[:5], 1):  # Show first 5
                OutputFormatter.info(f"  {i}. {item[:80]}...")
        
        # Create detailed revision task with strict improvement requirements
        revision_task = f"""
        You are Dr. Qwen Leader, the chief researcher responsible for synthesizing and refining scientific hypotheses.
        
        **REVISION ITERATION {self.current_iteration + 1}/{self.max_iterations}**
        
        Current quality score: {quality_score:.2f}/10 | Target: {self.quality_threshold}/10 | Goal: EXCEED target with SUBSTANTIAL improvements
        
        ## Context (Current Hypothesis + Full Review Feedback):
        {context_string}
        
        ## Your Task:
        Produce a SUBSTANTIALLY IMPROVED hypothesis that addresses ALL review feedback. **Surface-level changes are NOT acceptable.**
        
        ### Mandatory Improvement Checklist:
        
        For EACH item below, you MUST explicitly implement concrete changes:
        
        **1. Critical Issues (Must Fix)**
        - [ ] All "Critical Concerns" from review are resolved with specific technical solutions
        - [ ] Every "Weakness" has been addressed with concrete improvements
        
        **2. Detailed Suggestions (Implement ALL)**
        {chr(10).join([f"        - [ ] Suggestion {i+1}: {item[:100]}..." for i, item in enumerate(actionable_items[:8])]) if actionable_items else "        - [ ] All detailed improvement suggestions from review implemented with specific technical details"}
        
        **3. Missing Elements (Add ALL)**
        - [ ] All missing components identified in review are added
        - [ ] Specific datasets, methods, or baselines mentioned are included
        
        **4. Quality Dimensions Improvement (Target +1.0 for each)**
        - [ ] Technical Soundness: Enhanced with rigorous methodology
        - [ ] Novelty: Strengthened innovative aspects
        - [ ] Feasibility: Concrete implementation details added
        - [ ] Clarity: Improved explanation and structure
        
        ### Strict Requirements for SUBSTANTIAL Revision:
        
        1. **NO COSMETIC CHANGES**: Don't just rephrase sentences. Add NEW content, NEW analysis, NEW technical details.
        
        2. **SPECIFIC TECHNICAL ADDITIONS Required**:
           - If review mentions "add baselines", include: method names, expected performance numbers, comparison tables
           - If review mentions "add equations", include: LaTeX-formatted mathematical formulations with variable definitions
           - If review mentions "more details on datasets", include: dataset sizes, preprocessing steps, train/val/test splits
           - If review mentions "experimental protocol", include: hyperparameters, training procedures, evaluation metrics
        
        3. **Measurable Improvements**:
           - Add at least 3-5 new technical elements (equations, algorithms, comparisons, datasets)
           - Expand each section by 20-30% with substantive content
           - Include specific citations and references where suggested
        
        4. **Quality Score Target**: Aim for {min(quality_score + 1.0, 9.5):.1f}/10 or higher (current: {quality_score:.2f}/10)
        
        ### Example of SUBSTANTIAL vs Cosmetic Changes:
        
        **COSMETIC (UNACCEPTABLE)**:
        - Original: "We use a neural network for prediction."
        - Bad Revision: "We utilize a deep neural network architecture for making predictions." (Just rewording!)
        
        **SUBSTANTIAL (REQUIRED)**:
        - Original: "We use a neural network for prediction."
        - Good Revision: "We employ a 12-layer Transformer architecture with 768 hidden dimensions, 12 attention heads, and GELU activation. Training uses AdamW optimizer with learning rate 1e-4, β1=0.9, β2=0.999, warmup steps 1000, and batch size 32. We compare against ResNet-50 (78.5% accuracy) and ViT-Base (81.2% accuracy) baselines on ImageNet-1K dataset (1.28M training images, 50K validation)."
        
        **Output**: Complete revised hypothesis document with ALL required improvements implemented. The revised version should be noticeably more comprehensive, rigorous, and detailed than the original.
        """
        
        OutputFormatter.info("Created comprehensive revision task")
        
        # Execute revision with timing
        start_time = time.time()
        
        try:
            result = await self._execute_camel_native_task(leader_agent, revision_task, "synthesis")
            execution_time = time.time() - start_time
            
            # Update synthesis result with revised version
            # FIX: Save intermediate version for tracking
            self.results[f"synthesis_v{self.current_iteration}"] = result
            self.results["synthesis"] = result
            
            if not result.failed:
                OutputFormatter.success(f"Hypothesis revision completed in {execution_time:.2f} seconds")
                
                # Record improvement history
                self.actionable_items_per_iteration.append(actionable_items)
                improvement_record = {
                    "iteration": self.current_iteration,
                    "quality_score_before": quality_score,
                    "actionable_items_count": len(actionable_items),
                    "actionable_items": actionable_items[:5],  # Store top 5
                    "execution_time": execution_time,
                    "content_length_before": len(synthesis_content),
                    "content_length_after": len(result.content)
                }
                self.improvement_history.append(improvement_record)
                
                # Show improvement summary
                OutputFormatter.info(f"[IMPROVEMENT TRACKING] Iteration {self.current_iteration + 1}:")
                OutputFormatter.info(f"  - Actionable items identified: {len(actionable_items)}")
                OutputFormatter.info(f"  - Content expansion: {len(synthesis_content)} → {len(result.content)} chars")
                
                # Show iteration progress
                if self.iteration_scores:
                    OutputFormatter.info(f"[ITERATION PROGRESS] Scores: {' -> '.join([f'{s:.2f}' for s in self.iteration_scores])}")
                
            else:
                # Graceful degradation: revision failed (e.g., API timeout), keep previous synthesis
                OutputFormatter.warning(f"Hypothesis revision failed: {result.content}")
                OutputFormatter.warning("Graceful degradation: retaining previous synthesis version and continuing to next phase")
                # Restore previous synthesis so the pipeline can continue
                self.results["synthesis"] = synthesis_result
                # Record the failure for reporting
                self.results["revision_error"] = self.result_processor.create_hypothesis_result(
                    content=f"Revision skipped: {result.content}",
                    failed=True,
                    task_type="revision",
                    metadata={"error": result.content, "agent": "Dr. Qwen Leader", "iteration": self.current_iteration, "degraded": True}
                )
                
        except Exception as e:
            # Graceful degradation: unexpected exception during revision
            OutputFormatter.error(f"Error during hypothesis revision: {e}")
            OutputFormatter.warning("Graceful degradation: retaining previous synthesis version and continuing to next phase")
            # Create failure result but do NOT raise — keep pipeline alive
            self.results["revision_error"] = self.result_processor.create_hypothesis_result(
                content=f"Hypothesis revision failed: {str(e)}",
                failed=True,
                task_type="revision",
                metadata={"error": str(e), "agent": "Dr. Qwen Leader", "iteration": self.current_iteration, "degraded": True}
            )
            # Restore previous synthesis so downstream phases have valid content
            self.results["synthesis"] = synthesis_result
    
    async def _polish_phase(self):
        """Final polishing phase - executed by Prof. Qwen Editor"""
        
        OutputFormatter.section("PHASE 6: FINAL POLISHING")
        OutputFormatter.info("[AGENT] Prof. Qwen Editor executing final polishing")
        
        editor_agent = self.agents.get("Prof. Qwen Editor")
        if not editor_agent:
            # If no editor agent available, use original synthesis result
            OutputFormatter.warning("Prof. Qwen Editor not found, using original synthesis")
            self.results["final_synthesis"] = self.results.get("synthesis")
            return
        
        # Get synthesis and review results (real AI content transfer)
        synthesis_result = self.results.get("synthesis")
        review_result = self.results.get("review")
        
        if not synthesis_result or synthesis_result.failed:
            raise RuntimeError("Synthesis result not available or failed")
        if not review_result or review_result.failed:
            raise RuntimeError("Review result not available or failed")
        
        synthesis_content = synthesis_result.content
        review_content = review_result.content
        
        OutputFormatter.info(f"Polishing hypothesis based on peer review feedback")
        OutputFormatter.info(f"Original hypothesis: {len(synthesis_content)} characters")
        OutputFormatter.info(f"Review feedback: {len(review_content)} characters")
        
        try:
            rounds_required = self.polish_iterations - self.polish_rounds_completed
            OutputFormatter.info(f"[POLISH] Starting polish phase (rounds remaining: {rounds_required})")
            
            for round_idx in range(rounds_required):
                current_round = self.polish_rounds_completed + 1
                OutputFormatter.section(f"[POLISH ROUND {current_round}/{self.polish_iterations}]")
                
                # For the first round, use full content directly to avoid context truncation
                # For subsequent rounds, use the result from previous round
                if current_round == 1:
                    # Use full synthesis content directly (not through context manager to avoid truncation)
                    full_content = synthesis_content
                    full_review = review_content
                    OutputFormatter.info(f"[POLISH] Using full synthesis content: {len(full_content)} chars")
                else:
                    # For subsequent rounds, use the polished result from previous round
                    prev_result = self.results.get("final_synthesis")
                    if prev_result and not prev_result.failed:
                        full_content = prev_result.content
                    else:
                        full_content = synthesis_content
                    full_review = review_content
                    OutputFormatter.info(f"[POLISH] Using previous polished content: {len(full_content)} chars")
                
                # Create detailed polishing task with FULL content
                polish_task = f"""
You are Prof. Qwen Editor, an expert scientific editor. Polish and refine the scientific hypothesis below based on the comprehensive peer review feedback.

## FULL SCIENTIFIC HYPOTHESIS (to be polished):
{full_content}

## PEER REVIEW FEEDBACK:
{full_review}

## Your Task:
Produce a final polished version that:
1. **Addresses ALL Review Comments**: Systematically incorporate every specific feedback and suggestion
2. **Improves Clarity**: Enhance readability, flow, and presentation throughout the entire document
3. **Strengthens Arguments**: Reinforce weak points identified in review with additional evidence or reasoning
4. **Corrects ALL Issues**: Fix any technical, methodological, or formatting problems
5. **Maintains Complete Structure**: Keep the comprehensive scientific format with ALL sections intact
6. **Adds Missing Elements**: Include every important aspect noted as missing in the review

## CRITICAL REQUIREMENTS:
- You MUST output the COMPLETE document, not a summary or excerpt
- Preserve ALL sections: Executive Summary, Background, Hypothesis, Methodology, Analysis, etc.
- Ensure the output is publication-ready and professionally formatted
- The output should be a standalone scientific hypothesis document suitable for submission

Output the complete, polished scientific hypothesis document below:
"""
                
                OutputFormatter.info("Created comprehensive polishing task with full content")
                
                # Execute polishing with timing
                import time
                start_time = time.time()
                
                try:
                    result = await self._execute_camel_native_task(editor_agent, polish_task, "final_synthesis")
                    execution_time = time.time() - start_time
                    
                    if not result.failed:
                        self.results["final_synthesis"] = result
                        OutputFormatter.success(f"Final polishing round {current_round} completed in {execution_time:.2f} seconds")
                        # 更新上下文供下一轮使用
                        self.workflow_context.add_phase_result(
                            phase_name="polish",
                            content=result.content,
                            role_name=f"Prof. Qwen Editor (Round {current_round})"
                        )
                    else:
                        OutputFormatter.error(f"Final polishing round {current_round} failed: {result.content}")
                        OutputFormatter.warning("Using previous synthesis as final result for this round")
                        self.results["final_synthesis"] = synthesis_result
                        break
                    
                except Exception as e:
                    OutputFormatter.error(f"Error during final polishing round {current_round}: {e}")
                    OutputFormatter.warning("Using previous synthesis as final result due to error")
                    self.results["final_synthesis"] = synthesis_result
                    break
                
                self.polish_rounds_completed += 1
                
        finally:
            if self.polish_rounds_completed < self.polish_iterations:
                OutputFormatter.warning(
                    f"[CONTEXT] Polish phase ended early ({self.polish_rounds_completed}/{self.polish_iterations} rounds completed)"
                )
            else:
                OutputFormatter.info(f"[CONTEXT] Polish phase completed ({self.polish_rounds_completed}/{self.polish_iterations})")
    
    async def _evaluation_phase(self):
        """Final evaluation phase using FIG-MAC standards"""
        
        OutputFormatter.section("PHASE 7: FINAL EVALUATION")
        OutputFormatter.info("[EVALUATION] Executing FIG-MAC multi-dimensional assessment")
        
        # Get final synthesis result for evaluation
        final_synthesis = self.results.get("final_synthesis")
        if not final_synthesis or final_synthesis.failed:
            OutputFormatter.error("Final synthesis not available for evaluation")
            # Create default evaluation result
            self.results["evaluation"] = HypothesisTaskResult(
                content="Evaluation skipped due to missing synthesis",
                failed=True,
                task_type="evaluation",
                metadata={"error": "No final synthesis available"}
            )
            return
        
        # Implement retry mechanism for evaluation
        max_retries = 3
        evaluation_result = None
        evaluation_agent = None
        execution_time = 0
        
        for attempt in range(max_retries):
            try:
                # Create FinalEvaluationAgent instance
                evaluation_agent = FinalEvaluationAgent()
                OutputFormatter.info(f"Created FinalEvaluationAgent with FIG-MAC standards (attempt {attempt + 1}/{max_retries})")
                
                # Extract content for evaluation
                hypothesis_content = final_synthesis.content
                OutputFormatter.info(f"Evaluating hypothesis content: {len(hypothesis_content)} characters")
                
                # Execute evaluation with timing
                import time
                start_time = time.time()
                
                # Perform multi-dimensional evaluation
                evaluation_result = evaluation_agent.evaluate_hypothesis(hypothesis_content)
                execution_time = time.time() - start_time
                
                OutputFormatter.success(f"Evaluation completed in {execution_time:.2f} seconds")
                break  # Success, exit retry loop
                
            except Exception as e:
                OutputFormatter.error(f"Evaluation attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    # Final attempt failed, handle gracefully
                    OutputFormatter.error(f"All {max_retries} evaluation attempts failed. Skipping evaluation phase.")
                    evaluation_result = None
                    break
                else:
                    # Wait before retry
                    import time
                    time.sleep(1)
                    continue
        
        # Process evaluation result
        if evaluation_result is not None:
            
            # Extract scores for integration with internal scores
            external_scores = evaluation_result.get("evaluation_scores", {})
            final_rating = evaluation_result.get("final_rating", 5.0)
            
            # Get internal scores from review phase for integration
            internal_scores = self._extract_internal_scores()
            
            # Calculate integrated final score (25% internal + 75% external)
            # Pass final_rating from FinalEvaluationAgent (already correctly weighted)
            integrated_score = self._calculate_final_score(internal_scores, external_scores, final_rating)
            
            # Create comprehensive evaluation result
            evaluation_metadata = {
                "evaluation_agent": "FinalEvaluationAgent",
                "evaluation_standards": "FIG-MAC",
                "execution_time": execution_time,
                "external_rating": final_rating,
                "internal_scores": internal_scores,
                "integrated_score": integrated_score,
                "evaluation_dimensions": 8
            }
            
            # Store evaluation result
            self.results["evaluation"] = HypothesisTaskResult(
                content=str(evaluation_result),
                failed=False,
                task_type="evaluation",
                metadata=evaluation_metadata
            )
            
            # Store final evaluation for report generation
            self.results["final_evaluation"] = evaluation_result
            self.results["evaluation_summary"] = self._format_evaluation_summary(evaluation_result, integrated_score)
            
            # Display evaluation summary
            OutputFormatter.info("=== EVALUATION SUMMARY ===")
            OutputFormatter.info(f"External Rating: {final_rating:.2f}/10")
            OutputFormatter.info(f"Internal Average: {sum(internal_scores)/len(internal_scores) if internal_scores else 'N/A':.2f}/10")
            OutputFormatter.info(f"Integrated Score: {integrated_score:.2f}/10")
            OutputFormatter.info(f"Overall Assessment: {evaluation_result.get('overall_assessment', 'No assessment')}")
            
        else:
            # All evaluation attempts failed
            OutputFormatter.error("Evaluation phase skipped due to repeated failures")
            # Create error evaluation result
            self.results["evaluation"] = HypothesisTaskResult(
                content="Evaluation failed after multiple attempts",
                failed=True,
                task_type="evaluation",
                metadata={"error": "Multiple evaluation attempts failed", "evaluation_agent": "FinalEvaluationAgent", "max_retries": max_retries}
            )
    
    def _extract_internal_scores(self) -> List[float]:
        """Extract internal scores from review phase using pre-compiled patterns."""
        try:
            review_result = self.results.get("review")
            if not review_result or review_result.failed:
                return [5.0]
            
            review_content = review_result.content
            internal_scores = []
            
            for pattern in _INTERNAL_SCORE_PATTERNS:
                matches = pattern.findall(review_content)
                for match in matches:
                    try:
                        score = float(match)
                        if 0 <= score <= 10:
                            internal_scores.append(score)
                    except ValueError:
                        continue
            
            if not internal_scores:
                fallback_matches = _INTERNAL_SCORE_FALLBACK.findall(review_content)
                for match in fallback_matches:
                    try:
                        score = float(match)
                        if 0 <= score <= 10:
                            internal_scores.append(score)
                    except ValueError:
                        continue

            if internal_scores:
                return list(dict.fromkeys(internal_scores))
            
            self.logger.warning("No internal scores extracted, defaulting to 5.0")
            return [5.0]
            
        except Exception as e:
            self.logger.warning(f"Failed to extract internal scores: {e}")
            return [5.0]  # Default score
    
    def _calculate_final_score(self, internal_scores: List[float], external_scores: dict, 
                               external_rating: float = None) -> float:
        """Calculate final score using 25% internal + 75% external weighting
        
        Args:
            internal_scores: List of internal quality scores from peer review
            external_scores: Dict of 8-dimensional evaluation scores from FinalEvaluationAgent
            external_rating: Pre-calculated external rating from FinalEvaluationAgent (preferred)
        
        Note:
            FinalEvaluationAgent already applies weights and calculates final_rating correctly:
            - Weights: clarity(0.5), relevance(1.0), structure(0.5), conciseness(0.5), 
                      technical_accuracy(1.0), engagement(1.0), originality(1.0), feasibility(1.0)
            - Total weight = 6.5, final_rating = weighted_total / 6.5 (1-10 scale)
        """
        try:
            # Calculate internal score average (already normalized to 1-10)
            internal_avg = sum(internal_scores) / len(internal_scores) if internal_scores else 5.0
            
            # Use pre-calculated external rating if available (correctly weighted by FinalEvaluationAgent)
            if external_rating is not None and isinstance(external_rating, (int, float)):
                external_avg = float(external_rating)
                OutputFormatter.info(f"[SCORING] Using FinalEvaluationAgent rating: {external_avg:.2f}/10")
            else:
                # Fallback: Calculate external average directly from 8 dimensions
                # All dimensions are on 1-10 scale, use simple average
                scores = []
                for dimension, dimension_data in external_scores.items():
                    if isinstance(dimension_data, dict) and 'score' in dimension_data:
                        score = dimension_data['score']
                        if isinstance(score, (int, float)) and 1 <= score <= 10:
                            scores.append(float(score))
                
                external_avg = sum(scores) / len(scores) if scores else 5.0
                OutputFormatter.info(f"[SCORING] Calculated external average: {external_avg:.2f}/10")
            
            # Apply 25% internal + 75% external weighting
            final_score = internal_avg * 0.25 + external_avg * 0.75
            
            OutputFormatter.info(f"[SCORING] Internal: {internal_avg:.2f} × 25% + External: {external_avg:.2f} × 75% = {final_score:.2f}")
            
            return round(final_score, 2)
            
        except Exception as e:
            OutputFormatter.warning(f"Failed to calculate final score: {e}")
            return 5.0  # Default score
    
    def _format_evaluation_summary(self, evaluation_result: dict, integrated_score: float) -> str:
        """Format evaluation summary for report header"""
        try:
            final_rating = evaluation_result.get("final_rating", 5.0)
            total_score = evaluation_result.get("total_score", 40)
            overall_assessment = evaluation_result.get("overall_assessment", "No assessment available")
            
            # Create concise summary for report header
            summary = f"Rating: {final_rating:.1f}/10, Total: {total_score}/80, Integrated: {integrated_score:.1f}/10"
            
            # Add quality indicator
            if integrated_score >= 8.0:
                quality = "Excellent"
            elif integrated_score >= 7.0:
                quality = "Good"
            elif integrated_score >= 6.0:
                quality = "Acceptable"
            elif integrated_score >= 5.0:
                quality = "Moderate"
            else:
                quality = "Needs Improvement"
            
            return f"{summary} | Quality: {quality}"
            
        except Exception as e:
            return f"Evaluation summary unavailable: {str(e)}"
    
    async def _finish_phase(self):
        """Completion phase"""
        self.logger.info("Hypothesis generation completed")
        # Ensure final result exists
        if "final_synthesis" not in self.results:
            self.results["final_synthesis"] = self.results.get("synthesis")
    


# Configure logging
logging.basicConfig(level=logging.INFO)
