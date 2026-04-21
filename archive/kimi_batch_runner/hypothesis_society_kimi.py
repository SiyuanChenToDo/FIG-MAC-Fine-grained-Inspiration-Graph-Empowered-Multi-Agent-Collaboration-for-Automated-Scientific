"""
Scientific Hypothesis Generation Society - FIG-MAC Architecture
Multi-agent system for scientific hypothesis generation based on CAMEL framework

Refactored version: Uses HypothesisTeam + Channel architecture, completely removes Workforce dependency
"""

import asyncio
import os
import re
import sys
import textwrap
from pathlib import Path
from typing import List, Optional, Any, Dict
from datetime import datetime
import logging
import warnings

# Suppress transformers FutureWarning about deprecated environment variables
warnings.filterwarnings("ignore", category=FutureWarning, module="transformers")

# 路径处理：确保能同时找到 pip 安装的 camel 和本地的 Myexamples
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# 步骤1：清理 sys.path 中所有包含 autodl-tmp 的路径（避免找到本地不完整的 camel）
sys.path = [p for p in sys.path if 'autodl-tmp' not in p and p != '']

# 步骤2：导入 pip 安装的 camel
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

# 步骤3：添加 PROJECT_ROOT 以找到 Myexamples
sys.path.insert(0, str(PROJECT_ROOT))

# Enable context dump debugging before other CAMEL imports
import Myexamples.tests.context_dump_patch  # noqa: F401

# Environment variable loading
SHOW_BOOT_LOGS = False

def _boot_print(message: str):
    """Helper to control whether boot-time logs are emitted."""
    if SHOW_BOOT_LOGS:
        print(message)

# Globally suppress noisy third-party warnings
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    module="torchdata.datapipes"
)

try:
    from dotenv import load_dotenv
    load_dotenv()
    _boot_print("[INFO] Environment variables loaded from .env file")
except ImportError:
    _boot_print("[WARNING] python-dotenv not installed, .env file will not be loaded automatically")

# --- KIMI API KEY CONFIGURATION ---
# 使用 Moonshot/Kimi API
KIMI_API_KEY = os.environ.get("MOONSHOT_API_KEY", "")
KIMI_BASE_URL = os.environ.get("MOONSHOT_API_BASE_URL", "https://api.moonshot.cn/v1")

if not KIMI_API_KEY:
    _boot_print("[WARNING] MOONSHOT_API_KEY not set in environment")
else:
    os.environ["OPENAI_API_KEY"] = KIMI_API_KEY
    os.environ["OPENAI_COMPATIBILITY_API_KEY"] = KIMI_API_KEY
    
    os.environ["OPENAI_API_BASE_URL"] = KIMI_BASE_URL
    os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"] = KIMI_BASE_URL
    
    _boot_print(f"[CONFIG] Kimi API configured: {KIMI_API_KEY[:8]}...{KIMI_API_KEY[-4:]}")
    _boot_print(f"[CONFIG] Base URL: {KIMI_BASE_URL}")
# -----------------------------------

# 修复日志重复输出问题：清除重复的 handlers 并配置日志级别
logging.basicConfig(level=logging.WARNING, force=True)  # 改为 WARNING，隐藏 INFO 级别的技术日志

# 只保留重要的错误和警告日志，隐藏底层技术细节
for logger_name in ['httpx', 'faiss', 'faiss.loader', 'camel', 'camel.camel.storages.vectordb_storages.faiss']:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.WARNING)  # 设置为 WARNING，只显示警告和错误
    logger.handlers.clear()
    logger.propagate = False

# camel 已在前面导入，这里不需要重复导入

# Import CAMEL native agents
from Myexamples.agents.camel_native_agent import (
    create_camel_native_agent, 
    HypothesisTaskResult,
    CamelNativeAgent
)
# Import new Team architecture
# 使用 Kimi 版本的 hypothesis_team
import sys
sys.path.insert(0, str(Path(__file__).parent))
from hypothesis_team_kimi import HypothesisTeam, TeamState
from Myexamples.agents.graph_agents import (
    get_scholar_scour_config, 
    get_qwen_leader_config, 
    get_qwen_editor_config, 
    get_idea_igniter_config, 
    # New agent configurations
    get_prof_qwen_ethics_config,
    get_dr_qwen_technical_config,
    get_dr_qwen_practical_config,
    get_critic_crucible_config,
)


# Import CAMEL native logger formatter
from Myexamples.test_mutiagent.camel_logger_formatter import OutputFormatter


def adapt_tools_for_native_agent(tools: Optional[List[Any]]) -> List[Any]:
    """Adapt tools for CAMEL native agent format"""
    if not tools:
        return []
    
    adapted_tools = []
    for tool_item in tools:
        if hasattr(tool_item, 'get_tools'):  # SearchToolkit
            adapted_tools.extend(tool_item.get_tools())
        else:
            adapted_tools.append(tool_item)
    return adapted_tools


class HypothesisGenerationSociety:
    """
    A streamlined collaborative CAMEL society using 8 specialized Qwen agents
    for generating novel scientific hypotheses through multi-agent collaboration.
    
    Uses FIG-MAC architecture: HypothesisTeam + Channel asynchronous communication
    
    Agents:
    - Dr. Qwen Leader: Chief researcher and synthesis expert
    - Scholar Scour: Literature review expert with RAG integration
    - Idea Igniter: Advanced creative innovation specialist
    - Dr. Qwen Technical: Technical rigor specialist  
    - Dr. Qwen Practical: Applied research specialist
    - Prof. Qwen Ethics: Impact and significance analyst
    - Critic Crucible: Peer review specialist
    - Prof. Qwen Editor: Scientific writing and style specialist
    """

    def __init__(self):
        self.team = None  # Use HypothesisTeam instead of Workforce
        self.agent_configs = {}  # Store agent configurations
        OutputFormatter.success("Scientific Hypothesis Generation Society initialized successfully")

    def create_qwen_agent(
        self, role_name: str, system_prompt: str = None, persona: str = None, 
        specialization: str = None, model_type: str = None, tools: Optional[List[Any]] = None,
        model_config: Optional[Dict[str, Any]] = None, memory_config: Optional[Dict[str, Any]] = None
    ) -> CamelNativeAgent:
        """Create a CAMEL native agent with specific role and complete system prompt"""

        # Record agent configuration
        config = {
            "role_name": role_name,
            "model_type": model_type or "plus",
            "specialization": specialization or "General research",
            "prompt_length": len(system_prompt) if system_prompt else len(persona or "") + 200
        }
        self.agent_configs[role_name] = config

        # If a complete system prompt is provided, use it directly
        if system_prompt:
            msg_content = textwrap.dedent(system_prompt).strip()
        else:
            # Fallback to the old method for backward compatibility
            msg_content = textwrap.dedent(f"""
            You are {role_name}, a distinguished researcher in the scientific community.

            Your persona: {persona}

            Your specialization: {specialization}

            You are part of an elite collaborative research team dedicated to generating novel, 
            testable scientific hypotheses that advance human knowledge. Your team follows 
            rigorous scientific methodology and interdisciplinary thinking.

            Your responsibilities:
            - Provide expert analysis in your specialization area
            - Collaborate effectively with other team members
            - Ensure all hypotheses are scientifically grounded and testable
            - Contribute to the iterative refinement of research ideas
            - Maintain the highest standards of scientific rigor

            Always structure your responses clearly and provide evidence-based reasoning.
            When collaborating, build upon others' ideas constructively and identify potential 
            improvements or alternative approaches.
            """).strip()

        # 使用 Kimi K2 模型
        # CAMEL 预定义的 K2 模型名称
        from camel.types import ModelType
        kimi_model_type = ModelType.MOONSHOT_KIMI_K2  # "kimi-k2-0711-preview"

        # 设置默认的模型配置（Kimi K2.5 支持 256K 上下文）
        default_model_config = {
            "max_tokens": 8192,
            "temperature": 0.7,
        }
        if model_config:
            default_model_config.update(model_config)

        # 设置默认记忆配置（Kimi K2.5 支持更大的上下文）
        default_memory_config = {
            "window_size": 10,
            "token_limit": 128000,  # Kimi K2.5 支持 256K，这里使用 128K 以确保安全
        }
        if memory_config:
            default_memory_config.update(memory_config)
        
        # Use CAMEL native agent creation method (FIG-MAC mode) with Kimi
        # 使用 OPENAI_COMPATIBILITY 平台以支持 Kimi API
        from camel.types import ModelPlatformType
        return create_camel_native_agent(
            role_name=role_name,
            system_prompt=msg_content,
            model_type=kimi_model_type,
            model_config=default_model_config,
            tools=adapt_tools_for_native_agent(tools),
            memory_config=default_memory_config,
            model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL
        )

    def display_agent_configs(self):
        """Display all agent configurations before running"""
        OutputFormatter.section("SCIENTIFIC HYPOTHESIS GENERATION TEAM CONFIGURATION")
        
        # Model display name mapping
        MODEL_DISPLAY_NAMES = {
            "max": "Qwen3 MAX",
            "plus": "Kimi K2",
            "turbo": "Kimi K2"
        }
        
        for i, (agent_name, config) in enumerate(self.agent_configs.items(), 1):
            print(f"\n{i}. {agent_name}")
            model_display = MODEL_DISPLAY_NAMES.get(
                config['model_type'], 
                "Kimi K2"
            )
            print(f"   Model: {model_display}")
            print(f"   Role: {config['specialization']}")
            print(f"   Prompt Length: ~{config['prompt_length']} chars")
        
        # Model distribution summary
        print("\nModel Distribution:")
        print(f"   - Moonshot Kimi K2: {len(self.agent_configs)} agents")
        
        print("=" * 80)

    def create_research_team(self) -> HypothesisTeam:
        """Create the collaborative hypothesis generation team using CAMEL native agents"""
        OutputFormatter.info("Creating Scientific Hypothesis Generation Team with CAMEL native agents")

        # Create Qwen agents using encapsulated configurations
        leader_conf = get_qwen_leader_config()
        qwen_lead = self.create_qwen_agent(
            role_name=leader_conf["role_name"],
            system_prompt=leader_conf["system_prompt"],
            model_type=leader_conf["model_type"],
            tools=leader_conf["tools"],
            model_config={"max_tokens": 8192}  # Leader generates long documents (Qwen3-MAX limit 8192)
            # memory_config uses default configuration (token_limit=32768)
        )

        # Create Prof. Qwen Ethics using modular configuration
        ethics_conf = get_prof_qwen_ethics_config()
        qwen_ethicist = self.create_qwen_agent(
            role_name=ethics_conf["role_name"],
            system_prompt=ethics_conf["system_prompt"],
            model_type=ethics_conf["model_type"])

        # Create Dr. Qwen Technical using modular configuration
        technical_conf = get_dr_qwen_technical_config()
        qwen_technical = self.create_qwen_agent(
            role_name=technical_conf["role_name"],
            system_prompt=technical_conf["system_prompt"],
            model_type=technical_conf["model_type"])

        # Create Dr. Qwen Practical using modular configuration
        practical_conf = get_dr_qwen_practical_config()
        qwen_practical = self.create_qwen_agent(
            role_name=practical_conf["role_name"],
            system_prompt=practical_conf["system_prompt"],
            model_type=practical_conf["model_type"])

        # Create new specialized agents for hypothesis generation (extracted module)
        scholar_conf = get_scholar_scour_config()
        scholar_scour = self.create_qwen_agent(
            role_name=scholar_conf["role_name"],
            system_prompt=scholar_conf["system_prompt"],
            model_type=scholar_conf["model_type"],
            tools=scholar_conf["tools"],
        )

        # Create Idea Igniter agent using extracted configuration
        igniter_conf = get_idea_igniter_config()
        idea_igniter = self.create_qwen_agent(
            role_name=igniter_conf["role_name"],
            system_prompt=igniter_conf["system_prompt"],
            model_type=igniter_conf["model_type"],
            tools=igniter_conf["tools"],
        )

        # Create Critic Crucible using modular configuration
        critic_conf = get_critic_crucible_config()
        critic_crucible = self.create_qwen_agent(
            role_name=critic_conf["role_name"],
            system_prompt=critic_conf["system_prompt"],
            model_type=critic_conf["model_type"])

        # Create Prof. Qwen Editor using extracted configuration
        editor_conf = get_qwen_editor_config()
        qwen_editor = self.create_qwen_agent(
            role_name=editor_conf["role_name"],
            system_prompt=editor_conf["system_prompt"],
            model_type=editor_conf["model_type"],
            tools=editor_conf["tools"],
            model_config={"max_tokens": 8192}  # Editor also generates long documents (Qwen3-MAX limit 8192)
            # memory_config uses default configuration (token_limit=32768)
        )

        # Collect all agents into list
        agents = [
            qwen_lead,      # Dr. Qwen Leader (Chief Researcher & Synthesis Expert)
            scholar_scour,  # Scholar Scour (Literature Analysis Expert)
            idea_igniter,   # Idea Igniter (Creative Innovation Specialist)
            qwen_technical, # Dr. Qwen Technical (Technical Rigor Specialist)
            qwen_practical, # Dr. Qwen Practical (Applied Research Specialist)
            qwen_ethicist,  # Prof. Qwen Ethics (Impact & Significance Analyst)
            critic_crucible,# Critic Crucible (Peer Review Specialist)
            qwen_editor,    # Prof. Qwen Editor (Scientific Writing Specialist)
        ]

        # Create HypothesisTeam (FIG-MAC mode)
        self.team = HypothesisTeam(agents)
        
        OutputFormatter.success(
            "Scientific Hypothesis Generation Team created with 8 "
            "CAMEL native agents using FIG-MAC architecture")
        return self.team

    async def run_research_async(self, research_topic: str, max_iterations: int = 3,
                                quality_threshold: float = 8.0, polish_iterations: int = 1) -> HypothesisTaskResult:
        """
        Run collaborative research using FIG-MAC state machine architecture
        All phases are executed by the HypothesisTeam state machine with real AI processing
        """
        if not self.team:
            self.create_research_team()

        self.display_agent_configs()

        OutputFormatter.header(f"Starting scientific hypothesis generation on: {research_topic}")
        print("=" * 80)
        
        # Display agent execution plan (aligned with backup version)
        OutputFormatter.info(
            "[AGENT PLAN] Subtask 1: Scholar Scour | "
            "Subtask 2: Idea Igniter | "
            "Subtask 3: Dr. Qwen Technical | "
            "Subtask 4: Dr. Qwen Practical | "
            "Subtask 5: Prof. Qwen Ethics | "
            "Subtask 6: Dr. Qwen Leader | "
            "Subtask 7: Critic Crucible | "
            "Subtask 8: Prof. Qwen Editor"
        )
        
        try:
            # Directly call state machine to execute complete workflow with iteration support
            # State machine internally handles all phases: Literature→Ideation→Analysis→Synthesis→Review→(Revision)→Polish
            # Iteration logic: Review phase checks quality score and decides whether to iterate
            result = await self.team.execute_hypothesis_generation(
                research_topic,
                max_iterations=max_iterations,
                quality_threshold=quality_threshold,
                polish_iterations=polish_iterations
            )
            
            if result.failed:
                raise Exception(f"Hypothesis generation failed: {result.content}")
            
            # Get final AI-generated content
            final_content = result.content
            
            # COMPLETION
            OutputFormatter.section("SCIENTIFIC HYPOTHESIS GENERATION COMPLETE")
            OutputFormatter.success("Hypothesis generation completed using FIG-MAC architecture")
            
            # First extract and clean AI-generated content
            extracted_content = self._extract_ai_content(final_content)
            cleaned_content = self._clean_and_format_content(extracted_content)
            
            # Structure and save real AI-generated content, pass model parameter information
            final_report = self._structure_final_report(cleaned_content, research_topic, result.metadata)
            file_path = self.save_research_report(research_topic, final_report)
            OutputFormatter.success(f"Report saved to: {file_path}")
            
            # Merge metadata from team result with additional fields
            merged_metadata = {}
            if hasattr(result, "metadata") and isinstance(result.metadata, dict):
                merged_metadata.update(result.metadata)
            merged_metadata.update({
                "topic": research_topic,
                "file_path": file_path,
                "max_iterations": max_iterations,
                "quality_threshold": quality_threshold,
                "polish_iterations": polish_iterations
            })
            merged_metadata.setdefault("polish_rounds_completed", getattr(self.team, "polish_rounds_completed", None))
            merged_metadata.setdefault("workflow_id", getattr(self.team, "output_manager", None).current_workflow_id if hasattr(self.team, "output_manager") and hasattr(self.team.output_manager, "current_workflow_id") else None)

            return HypothesisTaskResult(
                content=final_report,
                failed=False,
                task_type="hypothesis_generation",
                metadata=merged_metadata
            )
            
        except Exception as e:
            OutputFormatter.error(f"Error during hypothesis generation: {e}")
            return HypothesisTaskResult(
                content=f"Hypothesis generation failed: {str(e)}",
                failed=True,
                task_type="hypothesis_generation",
                metadata={"error": str(e), "topic": research_topic}
            )
    
    def _extract_ai_content(self, raw_response) -> str:
        """
        Extract pure text content from CAMEL response - ensure only message.content plain text is returned
        """
        try:
            # If it's a string, return directly
            if isinstance(raw_response, str):
                return raw_response
            
            # If it's a ChatCompletion object, directly extract content plain text
            if hasattr(raw_response, 'choices') and raw_response.choices:
                return raw_response.choices[0].message.content  # Return plain text directly
            
            # If it's another object, convert to string
            return str(raw_response)
            
        except Exception as e:
            OutputFormatter.warning(f"Failed to extract AI content: {e}")
            return str(raw_response)
    
    def _clean_and_format_content(self, content: str) -> str:
        """
        Clean and format AI-generated content - enhanced escape character parsing
        Ensure AI content becomes readable markdown format
        """
        if not content:
            return ""
        
        # First parse escape characters - key step (Stage 1.1 optimization)
        # REMOVED aggressive replacements that break LaTeX formulas
        # content = content.replace('\\n', '\n').replace('\\t', '\t')
        # content = content.replace('\\"', '"').replace("\\'", "'")
        # content = content.replace('\\\\', '\\')  # Handle double backslashes
        
        # Process line by line
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Remove leading and trailing whitespace, but maintain indentation structure
            cleaned_line = line.rstrip()
            # Compress multiple spaces to single space, but maintain markdown indentation
            if cleaned_line.strip():
                # Maintain indentation for markdown lists and code blocks
                if cleaned_line.lstrip().startswith(('- ', '* ', '+ ', '1. ', '2. ', '3. ', '4. ', '5. ', '6. ', '7. ', '8. ', '9. ', '```', '    ', '$', '\\')):
                    cleaned_lines.append(cleaned_line)
                else:
                    # Compress internal spaces but maintain basic structure
                    cleaned_line = re.sub(r'[ \t]+', ' ', cleaned_line)
                    cleaned_lines.append(cleaned_line)
            else:
                cleaned_lines.append('')
        
        # Remove consecutive empty lines, but maintain paragraph separation
        final_lines = []
        prev_empty = False
        for line in cleaned_lines:
            if line.strip():
                final_lines.append(line)
                prev_empty = False
            elif not prev_empty:
                final_lines.append('')
                prev_empty = True
        
        # Remove leading and trailing empty lines
        while final_lines and not final_lines[0].strip():
            final_lines.pop(0)
        while final_lines and not final_lines[-1].strip():
            final_lines.pop()
        
        return '\n'.join(final_lines)
    
    def _structure_final_report(self, content: str, research_topic: str, metadata: dict = None) -> str:
        """
        Structure final report, separate metadata and AI content
        Add model parameter information to metadata header, ensure AI content section is completely pure
        """
        from datetime import datetime
        
        # Validate content quality
        if len(content) < 500:
            OutputFormatter.warning(f"Generated content seems short ({len(content)} chars)")
        
        if not any(keyword in content.lower() for keyword in ['hypothesis', 'research', 'analysis', 'methodology']):
            OutputFormatter.warning("Content may not be a proper scientific hypothesis")
        
        # Extract model parameter information
        model_info = self._extract_model_info(metadata) if metadata else {}
        
        # Extract iteration information
        iteration_info = self._extract_iteration_info() if hasattr(self, 'team') and self.team else {}
        
        # Create enhanced metadata header, including model parameter information and iteration info
        metadata_header = f"""# Scientific Hypothesis Generation Report
            **Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
            **Research Topic**: {research_topic}  
            **Generated by**: Scientific Hypothesis Generation Society (CAMEL + FIG-MAC)  
            **AI Research Team**: 8 Specialized CAMEL Native Agents
            **Processing Pipeline**: Literature Review → Creative Ideation → Parallel Analysis → Synthesis → Peer Review"""
        
        # Add iteration information if available
        if iteration_info:
            if iteration_info.get('iterations_performed', 0) > 0:
                metadata_header += f" → Iterative Revision ({iteration_info['iterations_performed']} iterations)"
            metadata_header += " → Final Polishing"
            
            # Add iteration details
            metadata_header += f"\n**Iteration Mode**: Enabled (Quality Threshold: {iteration_info.get('quality_threshold', 7.5)}/10)"
            metadata_header += f"\n**Iterations Performed**: {iteration_info['iterations_performed']}/{iteration_info.get('max_iterations', 3)}"
            
            if iteration_info.get('quality_scores'):
                scores_str = ' → '.join([f"{s:.2f}" for s in iteration_info['quality_scores']])
                metadata_header += f"\n**Quality Score Progress**: {scores_str}"
                
                if iteration_info.get('final_quality_score'):
                    metadata_header += f"\n**Final Quality Score**: {iteration_info['final_quality_score']:.2f}/10"
                    if iteration_info.get('best_iteration'):
                        metadata_header += f" (from iteration {iteration_info['best_iteration']})"
        else:
            metadata_header += " → Final Polishing"

        # Add model parameter information to header
        if model_info:
            if model_info.get('model_name'):
                metadata_header += f"\n**Model**: {model_info['model_name']}"
            if model_info.get('total_tokens'):
                completion_tokens = model_info.get('completion_tokens', 'N/A')
                prompt_tokens = model_info.get('prompt_tokens', 'N/A')
                metadata_header += f"\n**Tokens Used**: {model_info['total_tokens']} (completion: {completion_tokens}, prompt: {prompt_tokens})"
            if model_info.get('processing_time'):
                metadata_header += f"\n**Processing Time**: {model_info['processing_time']}"

        # Add evaluation information to header (PHASE 7: FINAL EVALUATION)
        OutputFormatter.info(f"Team results available: {list(self.team.results.keys()) if hasattr(self, 'team') and self.team else 'No team'}")
        
        # Check evaluation status and display accordingly
        if hasattr(self, 'team') and self.team and 'final_evaluation' in self.team.results:
            evaluation = self.team.results["final_evaluation"]
            evaluation_task_result = self.team.results.get("evaluation")
            
            # Get evaluation metadata for integrated scores and internal scores
            evaluation_metadata = {}
            if evaluation_task_result and hasattr(evaluation_task_result, 'metadata') and evaluation_task_result.metadata:
                evaluation_metadata = evaluation_task_result.metadata
            
            # Extract key evaluation data
            external_rating = evaluation.get("final_rating", "N/A")
            external_total_score = evaluation.get("total_score", "N/A")
            integrated_score = evaluation_metadata.get("integrated_score", "N/A")
            internal_scores = evaluation_metadata.get("internal_scores", [])
            
            # 1. Display Final Rating (integrated score)
            metadata_header += f"\n**Final Rating**: {integrated_score}/10 (25% Internal + 75% External)"
            
            # 2. Display Internal Evaluation Scores
            metadata_header += f"\n**Internal Evaluation Scores** (PHASE 5: PEER REVIEW):"
            if internal_scores:
                # Extract detailed internal scores from review content
                review_result = self.team.results.get("review")
                detailed_scores = self._extract_detailed_internal_scores(review_result) if review_result else {}
                
                # Display specific internal evaluation dimensions
                if detailed_scores:
                    if 'overall_quality_score' in detailed_scores:
                        metadata_header += f"\n  - Overall Quality Score: {detailed_scores['overall_quality_score']:.2f}/10"
                    if 'technical_soundness' in detailed_scores:
                        metadata_header += f"\n  - Technical Soundness: {detailed_scores['technical_soundness']:.2f}/10"
                    if 'novelty_assessment' in detailed_scores:
                        metadata_header += f"\n  - Novelty Assessment: {detailed_scores['novelty_assessment']:.2f}/10"
                    if 'clarity_score' in detailed_scores:
                        metadata_header += f"\n  - Clarity Score: {detailed_scores['clarity_score']:.2f}/10"
                else:
                    # Fallback: display raw scores if detailed extraction fails
                    for i, score in enumerate(internal_scores, 1):
                        metadata_header += f"\n  - Internal Score {i}: {score:.2f}/10"
                
                # Display average internal score
                internal_avg = sum(internal_scores) / len(internal_scores)
                metadata_header += f"\n  - Average Internal Score: {internal_avg:.2f}/10"
            else:
                metadata_header += f"\n  - Average Internal Score: N/A/10"
            
            # 3. Display External Evaluation
            metadata_header += f"\n**External Evaluation** (PHASE 7: FINAL EVALUATION):"
            
            # Calculate weight-adjusted external total score for display
            evaluation_scores = evaluation.get("evaluation_scores", {})
            if evaluation_scores:
                # Calculate actual weighted total score
                weighted_external_total = 0
                original_5point_dimensions = {"clarity", "structure", "conciseness"}
                
                for dimension, score_data in evaluation_scores.items():
                    if isinstance(score_data, dict) and 'score' in score_data:
                        score = score_data['score']
                        if isinstance(score, (int, float)):
                            if dimension in original_5point_dimensions:
                                weighted_external_total += score / 2  # Apply 50% weight
                            else:
                                weighted_external_total += score  # Full weight
                
                metadata_header += f"\n  - External Total Score: {weighted_external_total:.1f}/65 (weight-adjusted)"
                # Calculate correct external average: weighted_total/65*10
                external_average = (weighted_external_total / 65) * 10
                metadata_header += f"\n  - External Average: {external_average:.2f}/10"
                
                # 4. Display 8-Dimensional Evaluation Scores
                metadata_header += f"\n**8-Dimensional Evaluation Scores** (All displayed as 1-10 scale):"
                metadata_header += f"\n*Note: Clarity, Structure, Conciseness use 50% weight in final calculation*"
                
                # Define actual program dimensions with their max scores (unified to 1-10 scale)
                dimension_max_scores = {
                    "clarity": 10,
                    "relevance": 10,
                    "structure": 10,
                    "conciseness": 10,
                    "technical_accuracy": 10,
                    "engagement": 10,
                    "originality": 10,
                    "feasibility": 10
                }
                
                for dimension, max_score in dimension_max_scores.items():
                    weight_note = " (50% weight)" if dimension in original_5point_dimensions else ""
                    
                    if dimension in evaluation_scores:
                        score_data = evaluation_scores[dimension]
                        if isinstance(score_data, dict):
                            score = score_data.get('score', 'N/A')
                            metadata_header += f"\n  - {dimension.title()}: {score}/{max_score}{weight_note}"
                        else:
                            metadata_header += f"\n  - {dimension.title()}: N/A/{max_score}{weight_note}"
                    else:
                        metadata_header += f"\n  - {dimension.title()}: N/A/{max_score}{weight_note}"
            else:
                metadata_header += f"\n  - External Total Score: {external_total_score}/65"
                # Calculate correct external average from total score
                if external_total_score != "N/A" and isinstance(external_total_score, (int, float)):
                    backup_external_average = (external_total_score / 65) * 10
                    metadata_header += f"\n  - External Average: {backup_external_average:.2f}/10"
                else:
                    metadata_header += f"\n  - External Average: N/A/10"
                metadata_header += f"\n  - 8-Dimensional Scores: Not available"
            
            # 5. Add overall assessment if available
            overall_assessment = evaluation.get("overall_assessment", "")
            if overall_assessment:
                metadata_header += f"\n**Overall Assessment**: {overall_assessment}"
                    
        elif hasattr(self, 'team') and self.team and 'evaluation' in self.team.results:
            # Check if evaluation failed
            evaluation_result = self.team.results["evaluation"]
            if hasattr(evaluation_result, 'failed') and evaluation_result.failed:
                metadata_header += f"\n**Evaluation Status**: Failed"
                if hasattr(evaluation_result, 'metadata') and evaluation_result.metadata:
                    error_info = evaluation_result.metadata.get("error", "Unknown error")
                    max_retries = evaluation_result.metadata.get("max_retries", "N/A")
                    metadata_header += f"\n**Error**: {error_info}"
                    if max_retries != "N/A":
                        metadata_header += f"\n**Retry Attempts**: {max_retries}"
            else:
                metadata_header += f"\n**Evaluation Status**: Completed (no detailed scores available)"
        else:
            metadata_header += f"\n**Evaluation Status**: Not performed"  

        metadata_header += "\n\n---\n\n"
        
        # Combine final report: metadata + cleaned AI content
        final_report = metadata_header + content
        
        # Final validation
        OutputFormatter.info(f"Final report structured: {len(final_report)} characters")
        OutputFormatter.info("Report contains clean AI-generated content without raw objects")
        
        return final_report
    
    def _extract_detailed_internal_scores(self, review_result) -> dict:
        """Extract detailed internal scores from review content - Enhanced for Markdown"""
        detailed_scores = {}
        if not review_result or review_result.failed:
            return detailed_scores
        
        try:
            import re
            review_content = review_result.content
            
            # Define patterns for specific internal evaluation dimensions (Markdown + JSON)
            score_patterns = {
                'overall_quality_score': [
                    r'Quality Score[:\s*]+(\d+(?:\.\d+)?)\s*(?:/\s*10)?',
                    r'\*\*Quality Score\*\*[:\s]+(\d+(?:\.\d+)?)',
                    r'overall_quality_score["\']?\s*:\s*["\']?(\d+(?:\.\d+)?)["\']?'
                ],
                'technical_soundness': [
                    r'Technical Soundness[:\s*]+(\d+(?:\.\d+)?)',
                    r'technical_soundness["\']?\s*:\s*["\']?(\d+(?:\.\d+)?)["\']?'
                ],
                'novelty_assessment': [
                    r'Novelty Assessment[:\s*]+(\d+(?:\.\d+)?)',
                    r'novelty_assessment["\']?\s*:\s*["\']?(\d+(?:\.\d+)?)["\']?'
                ],
                'clarity_score': [
                    r'Clarity (?:Score|and Presentation)[:\s*]+(\d+(?:\.\d+)?)',
                    r'clarity_score["\']?\s*:\s*["\']?(\d+(?:\.\d+)?)["\']?'
                ]
            }
            
            for dimension, patterns in score_patterns.items():
                for pattern in patterns:
                    matches = re.findall(pattern, review_content, re.IGNORECASE)
                    if matches:
                        try:
                            score = float(matches[0])  # Take first match
                            # Normalize score to 1-10 scale if needed (unlikely with new prompt but safe)
                            if 1 <= score <= 10:
                                detailed_scores[dimension] = score
                                break # Found valid score for this dimension
                        except (ValueError, IndexError):
                            continue
            
            return detailed_scores
            
        except Exception as e:
            return detailed_scores
    
    def _extract_iteration_info(self) -> dict:
        """
        Extract iteration information from team state
        """
        iteration_info = {}
        
        try:
            if hasattr(self.team, 'current_iteration'):
                iteration_info['iterations_performed'] = self.team.current_iteration
            
            if hasattr(self.team, 'max_iterations'):
                iteration_info['max_iterations'] = self.team.max_iterations
            
            if hasattr(self.team, 'quality_threshold'):
                iteration_info['quality_threshold'] = self.team.quality_threshold
            
            if hasattr(self.team, 'iteration_scores') and self.team.iteration_scores:
                iteration_info['quality_scores'] = self.team.iteration_scores
                # Use best version score if available, otherwise use last score
                if hasattr(self.team, 'best_version') and self.team.best_version['iteration'] >= 0:
                    iteration_info['final_quality_score'] = self.team.best_version['score']
                    iteration_info['best_iteration'] = self.team.best_version['iteration'] + 1
                else:
                    iteration_info['final_quality_score'] = self.team.iteration_scores[-1]
            
        except Exception as e:
            OutputFormatter.warning(f"Failed to extract iteration info: {e}")
        
        return iteration_info
    
    def _extract_model_info(self, metadata: dict) -> dict:
        """
        Extract model parameter information from metadata
        """
        model_info = {}
        
        try:
            # Extract model information from intelligent_report
            if 'intelligent_report' in metadata:
                intelligent_report = metadata['intelligent_report']
                if 'model=' in intelligent_report:
                    import re
                    model_match = re.search(r"model='([^']*)'", intelligent_report)
                    if model_match:
                        model_info['model_name'] = model_match.group(1)
                
                # Extract token usage information
                if 'usage=' in intelligent_report:
                    usage_match = re.search(r'completion_tokens=(\d+)[^)]*prompt_tokens=(\d+)[^)]*total_tokens=(\d+)', intelligent_report)
                    if usage_match:
                        model_info['completion_tokens'] = int(usage_match.group(1))
                        model_info['prompt_tokens'] = int(usage_match.group(2))
                        model_info['total_tokens'] = int(usage_match.group(3))
            
            # Extract processing time information from workflow_summary
            if 'workflow_summary' in metadata:
                workflow_summary = metadata['workflow_summary']
                if isinstance(workflow_summary, dict) and 'total_execution_time' in workflow_summary:
                    model_info['processing_time'] = f"{workflow_summary['total_execution_time']:.2f}s"
            
        except Exception as e:
            OutputFormatter.warning(f"Failed to extract model info: {e}")
        
        return model_info

    def save_research_report(self, research_topic: str, report_content: str) -> str:
        """Save the research report to a file with timestamp and topic information"""
        import os
        import re
        from datetime import datetime
        from pathlib import Path
        
        # 优先使用环境变量指定的保存路径（用于消融实验）
        save_path = os.environ.get("ABLATION_REPORT_SAVE_PATH")
        if save_path:
            # 直接保存到指定路径
            try:
                filepath = Path(save_path)
                # 确保父目录存在
                filepath.parent.mkdir(parents=True, exist_ok=True)
                # 写入文件
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(report_content)
                return str(filepath)
            except Exception as e:
                # 如果保存失败，输出错误但继续使用默认路径
                OutputFormatter.warning(f"保存到指定路径失败 ({save_path}): {e}")
                OutputFormatter.info("回退到默认保存位置")
                # 继续执行默认保存逻辑
        
        # 默认行为：保存到 Scientific_Hypothesis_Reports 目录
        reports_dir = "Scientific_Hypothesis_Reports"
        if not os.path.exists(reports_dir):
            os.makedirs(reports_dir)
            OutputFormatter.info(f"Created reports directory: {reports_dir}")
        
        # Generate timestamp and clean topic name for filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_topic = re.sub(r'[^\w\s-]', '', research_topic)
        clean_topic = re.sub(r'\s+', '_', clean_topic.strip())
        
        # Generate filename
        filename = f"{timestamp}_{clean_topic[:50]}.md"  # Limit length to avoid filesystem issues
        filepath = os.path.join(reports_dir, filename)
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        return filepath

    def run_research(self, research_topic: str, max_iterations: int = 3,
                     quality_threshold: float = 8.0, polish_iterations: int = 1):
        """
        Synchronous wrapper - backward compatible with existing code
        """
        import asyncio
        return asyncio.run(self.run_research_async(research_topic, max_iterations, quality_threshold, polish_iterations))


# Main program entry point
if __name__ == "__main__":
    import asyncio
    
    # Initialize system
    society = HypothesisGenerationSociety()
    team = society.create_research_team()
    
    # Interactive main process with predefined topics
    async def interactive_main():
        """Interactive main process with 4 predefined research topics"""
        
        # Check for command line argument
        if len(sys.argv) > 1:
            topic = " ".join(sys.argv[1:])
            OutputFormatter.info(f"Received topic from command line: {topic}")
            # Execute directly
            result = await society.run_research_async(
                topic,
                max_iterations=3,      # 最大迭代次数
                quality_threshold=8.0  # 质量阈值 (1-10分) - Strong Accept级别
            )
             # Display results
            if not result.failed:
                OutputFormatter.success("Hypothesis generation completed successfully!")
                if "file_path" in result.metadata:
                    OutputFormatter.success(f"Report saved to: {result.metadata['file_path']}")
            else:
                OutputFormatter.error("Hypothesis generation failed")
                print(f"Error message: {result.content}")
            return
        
        # Define sample topics from backup version
        sample_topics = {
            1: {
                "topic": "Bridging Towers of Multi-task Learning with a Gating Mechanism for Aspect-based Sentiment Analysis and Sequential Metaphor Identification",
                "questions": """
                - How can a gating mechanism be designed to selectively filter and fuse information from auxiliary task towers into a main task tower, ensuring that only useful information is absorbed while irrelevant data is rejected?
                - How can the features from multiple Transformer layers within a task-specific tower be optimally combined to ensure the best use of information for downstream tasks?
                """
            },
            2: {
                "topic": "Bridging the Domain Gap: Improve Informal Language Translation via Counterfactual Domain Adaptation",
                "questions": """
                - How can counterfactual representations be generated to guide the NMT model to explore the target-domain distribution's latent space?
                - How can the generalization gap between source and target domains be bridged by constructing counterfactual interpolations?
                - How can the usefulness of source-domain samples be leveraged within a counterfactual framework to improve target-domain translation?
                """
            },
            3: {
                "topic": "Microbiome-Brain Communication and Neuroplasticity",
                "questions": """
                - What are the precise molecular mechanisms by which gut microbiota influence brain function and behavior?
                - Could microbial metabolites directly modulate synaptic plasticity and learning?
                - How might dysbiosis contribute to neurodevelopmental and neurodegenerative disorders?
                - What therapeutic interventions could leverage the microbiome-brain axis for treating neurological conditions?
                """
            }
        }
        
        OutputFormatter.section("SCIENTIFIC HYPOTHESIS GENERATION SOCIETY")
        print("Choose a research question or provide your own:")
        print()
        
        for num, info in sample_topics.items():
            print(f"{num}. {info['topic']}")
        print("4. Custom research topic")
        print()
        
        try:
            choice = input("Enter your choice (1-4): ").strip()
            
            if choice in ['1', '2', '3']:
                topic_info = sample_topics[int(choice)]
                topic = topic_info["topic"]
                OutputFormatter.info(f"Selected topic: {topic}")
            elif choice == '4':
                topic = input("Enter your scientific research question: ").strip()
                if not topic:
                    OutputFormatter.warning("No topic provided. Using default.")
                    topic = sample_topics[1]["topic"]
            else:
                OutputFormatter.warning("Invalid choice. Running default hypothesis generation")
                topic = sample_topics[1]["topic"]
            
            # Execute research with iteration parameters
            # 标准模式: 最多3次迭代,质量阈值7.5分
            result = await society.run_research_async(
                topic,
                max_iterations=3,      # 最大迭代次数
                quality_threshold=8.0  # 质量阈值 (1-10分) - Strong Accept级别
            )
            
            # Display results
            if not result.failed:
                OutputFormatter.success("Hypothesis generation completed successfully!")
                if "file_path" in result.metadata:
                    OutputFormatter.success(f"Report saved to: {result.metadata['file_path']}")
            else:
                OutputFormatter.error("Hypothesis generation failed")
                print(f"Error message: {result.content}")
                
        except Exception as e:
            OutputFormatter.error(f"Error during execution: {e}")
    
    # Run interactive main process
    try:
        asyncio.run(interactive_main())
    except KeyboardInterrupt:
        OutputFormatter.warning("User interrupted execution")
    except Exception as e:
        OutputFormatter.error(f"System error: {e}")
