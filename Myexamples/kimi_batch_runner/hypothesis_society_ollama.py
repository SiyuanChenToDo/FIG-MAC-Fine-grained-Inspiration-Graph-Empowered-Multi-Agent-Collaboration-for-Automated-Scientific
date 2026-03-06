"""
Scientific Hypothesis Generation Society - Ollama Local Models Version
使用本地运行的 Ollama 模型（Llama、Qwen、Mistral 等）
完全免费，无需 API Key，数据不离开本地
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

warnings.filterwarnings("ignore", category=FutureWarning, module="transformers")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path = [p for p in sys.path if 'autodl-tmp' not in p and p != '']

from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

sys.path.insert(0, str(PROJECT_ROOT))

import Myexamples.tests.context_dump_patch

SHOW_BOOT_LOGS = False

def _boot_print(message: str):
    if SHOW_BOOT_LOGS:
        print(message)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(level=logging.WARNING, force=True)

for logger_name in ['httpx', 'faiss', 'faiss.loader', 'camel']:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.WARNING)
    logger.handlers.clear()
    logger.propagate = False

from Myexamples.agents.camel_native_agent import (
    create_camel_native_agent, 
    HypothesisTaskResult,
    CamelNativeAgent
)
import sys
sys.path.insert(0, str(Path(__file__).parent))
from hypothesis_team_kimi import HypothesisTeam, TeamState
from Myexamples.agents.graph_agents import (
    get_scholar_scour_config, 
    get_qwen_leader_config, 
    get_qwen_editor_config, 
    get_idea_igniter_config, 
    get_prof_qwen_ethics_config,
    get_dr_qwen_technical_config,
    get_dr_qwen_practical_config,
    get_critic_crucible_config,
)

from Myexamples.test_mutiagent.camel_logger_formatter import OutputFormatter


def adapt_tools_for_native_agent(tools: Optional[List[Any]]) -> List[Any]:
    """Adapt tools for CAMEL native agent format"""
    if not tools:
        return []
    
    adapted_tools = []
    for tool_item in tools:
        if hasattr(tool_item, 'get_tools'):
            adapted_tools.extend(tool_item.get_tools())
        else:
            adapted_tools.append(tool_item)
    return adapted_tools


class HypothesisGenerationSociety:
    """
    Scientific Hypothesis Generation Society - Ollama Local Version
    使用本地 Ollama 模型，完全免费，数据安全
    """

    def __init__(self, model_name: str = "llama3.1:8b"):
        self.team = None
        self.agent_configs = {}
        self.model_name = model_name
        self.platform = ModelPlatformType.OLLAMA
        OutputFormatter.success(f"Scientific Hypothesis Generation Society initialized (Ollama - {model_name})")

    def create_ollama_agent(
        self, role_name: str, system_prompt: str = None, persona: str = None, 
        specialization: str = None, tools: Optional[List[Any]] = None,
        model_config: Optional[Dict[str, Any]] = None, memory_config: Optional[Dict[str, Any]] = None
    ) -> CamelNativeAgent:
        """Create a CAMEL native agent using Ollama local models"""

        config = {
            "role_name": role_name,
            "model_type": self.model_name,
            "specialization": specialization or "General research",
            "prompt_length": len(system_prompt) if system_prompt else len(persona or "") + 200
        }
        self.agent_configs[role_name] = config

        if system_prompt:
            msg_content = textwrap.dedent(system_prompt).strip()
        else:
            msg_content = textwrap.dedent(f"""
            You are {role_name}, a distinguished researcher in the scientific community.

            Your persona: {persona}

            Your specialization: {specialization}

            You are part of an elite collaborative research team dedicated to generating novel, 
            testable scientific hypotheses that advance human knowledge.
            """).strip()

        # Ollama 本地模型配置
        default_model_config = {
            "max_tokens": 2048,
            "temperature": 0.7,
        }
        if model_config:
            default_model_config.update(model_config)

        default_memory_config = {
            "window_size": 10,
            "token_limit": 8192,  # 本地模型上下文通常较小
        }
        if memory_config:
            default_memory_config.update(memory_config)
        
        return create_camel_native_agent(
            role_name=role_name,
            system_prompt=msg_content,
            model_type=self.model_name,
            model_config=default_model_config,
            tools=adapt_tools_for_native_agent(tools),
            memory_config=default_memory_config,
            model_platform=self.platform
        )

    def display_agent_configs(self):
        """Display all agent configurations"""
        OutputFormatter.section("SCIENTIFIC HYPOTHESIS GENERATION TEAM CONFIGURATION")
        
        print(f"\nPlatform: OLLAMA (Local)")
        print(f"Model: {self.model_name}")
        print(f"💡 完全免费，数据不离开本地机器")
        print()
        
        for i, (agent_name, config) in enumerate(self.agent_configs.items(), 1):
            print(f"{i}. {agent_name}")
            print(f"   Model: {config['model_type']}")
            print(f"   Role: {config['specialization']}")
        
        print("=" * 80)

    def create_research_team(self) -> HypothesisTeam:
        """Create the collaborative hypothesis generation team"""
        OutputFormatter.info(f"Creating Research Team with Ollama - {self.model_name}")

        leader_conf = get_qwen_leader_config()
        leader = self.create_ollama_agent(
            role_name=leader_conf["role_name"],
            system_prompt=leader_conf["system_prompt"],
            model_config={"max_tokens": 4096}
        )

        ethics_conf = get_prof_qwen_ethics_config()
        ethicist = self.create_ollama_agent(
            role_name=ethics_conf["role_name"],
            system_prompt=ethics_conf["system_prompt"])

        technical_conf = get_dr_qwen_technical_config()
        technical = self.create_ollama_agent(
            role_name=technical_conf["role_name"],
            system_prompt=technical_conf["system_prompt"])

        practical_conf = get_dr_qwen_practical_config()
        practical = self.create_ollama_agent(
            role_name=practical_conf["role_name"],
            system_prompt=practical_conf["system_prompt"])

        scholar_conf = get_scholar_scour_config()
        scholar = self.create_ollama_agent(
            role_name=scholar_conf["role_name"],
            system_prompt=scholar_conf["system_prompt"],
            tools=scholar_conf["tools"],
        )

        igniter_conf = get_idea_igniter_config()
        igniter = self.create_ollama_agent(
            role_name=igniter_conf["role_name"],
            system_prompt=igniter_conf["system_prompt"],
            tools=igniter_conf["tools"],
        )

        critic_conf = get_critic_crucible_config()
        critic = self.create_ollama_agent(
            role_name=critic_conf["role_name"],
            system_prompt=critic_conf["system_prompt"])

        editor_conf = get_qwen_editor_config()
        editor = self.create_ollama_agent(
            role_name=editor_conf["role_name"],
            system_prompt=editor_conf["system_prompt"],
            tools=editor_conf["tools"],
            model_config={"max_tokens": 4096}
        )

        agents = [
            leader, scholar, igniter, technical, 
            practical, ethicist, critic, editor
        ]

        self.team = HypothesisTeam(agents)
        
        OutputFormatter.success(
            f"Research Team created with 8 agents using Ollama - {self.model_name}")
        return self.team

    async def run_research_async(self, research_topic: str, max_iterations: int = 3,
                                quality_threshold: float = 8.0, polish_iterations: int = 1) -> HypothesisTaskResult:
        """Run collaborative research"""
        if not self.team:
            self.create_research_team()

        self.display_agent_configs()

        OutputFormatter.header(f"Starting research on: {research_topic}")
        print("=" * 80)
        
        try:
            result = await self.team.execute_hypothesis_generation(
                research_topic,
                max_iterations=max_iterations,
                quality_threshold=quality_threshold,
                polish_iterations=polish_iterations
            )
            
            if result.failed:
                raise Exception(f"Hypothesis generation failed: {result.content}")
            
            final_content = result.content
            
            OutputFormatter.section("SCIENTIFIC HYPOTHESIS GENERATION COMPLETE")
            OutputFormatter.success(f"Completed using Ollama - {self.model_name}")
            
            extracted_content = self._extract_ai_content(final_content)
            cleaned_content = self._clean_and_format_content(extracted_content)
            
            final_report = self._structure_final_report(cleaned_content, research_topic, result.metadata)
            file_path = self.save_research_report(research_topic, final_report)
            OutputFormatter.success(f"Report saved to: {file_path}")
            
            merged_metadata = {}
            if hasattr(result, "metadata") and isinstance(result.metadata, dict):
                merged_metadata.update(result.metadata)
            merged_metadata.update({
                "topic": research_topic,
                "file_path": file_path,
                "model": self.model_name,
                "platform": "ollama"
            })

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
                metadata={"error": str(e), "topic": research_topic, "model": self.model_name, "platform": "ollama"}
            )
    
    def _extract_ai_content(self, raw_response) -> str:
        """Extract pure text content from CAMEL response"""
        try:
            if isinstance(raw_response, str):
                return raw_response
            
            if hasattr(raw_response, 'choices') and raw_response.choices:
                return raw_response.choices[0].message.content
            
            return str(raw_response)
            
        except Exception as e:
            OutputFormatter.warning(f"Failed to extract AI content: {e}")
            return str(raw_response)
    
    def _clean_and_format_content(self, content: str) -> str:
        """Clean and format AI-generated content"""
        if not content:
            return ""
        
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            cleaned_line = line.rstrip()
            if cleaned_line.strip():
                if cleaned_line.lstrip().startswith(('- ', '* ', '+ ', '1. ', '```', '    ')):
                    cleaned_lines.append(cleaned_line)
                else:
                    cleaned_line = re.sub(r'[ \t]+', ' ', cleaned_line)
                    cleaned_lines.append(cleaned_line)
            else:
                cleaned_lines.append('')
        
        final_lines = []
        prev_empty = False
        for line in cleaned_lines:
            if line.strip():
                final_lines.append(line)
                prev_empty = False
            elif not prev_empty:
                final_lines.append('')
                prev_empty = True
        
        while final_lines and not final_lines[0].strip():
            final_lines.pop(0)
        while final_lines and not final_lines[-1].strip():
            final_lines.pop()
        
        return '\n'.join(final_lines)
    
    def _structure_final_report(self, content: str, research_topic: str, metadata: dict = None) -> str:
        """Structure final report"""
        from datetime import datetime
        
        metadata_header = f"""# Scientific Hypothesis Generation Report
**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Research Topic**: {research_topic}  
**Generated by**: Scientific Hypothesis Generation Society  
**AI Research Team**: 8 Specialized Agents
**Platform**: OLLAMA (Local)  
**Model**: {self.model_name}
**Note**: 💚 完全免费，数据不离开本地机器

---

"""
        
        return metadata_header + content
    
    def save_research_report(self, research_topic: str, report_content: str) -> str:
        """Save the research report"""
        reports_dir = "Scientific_Hypothesis_Reports"
        if not os.path.exists(reports_dir):
            os.makedirs(reports_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_topic = re.sub(r'[^\w\s-]', '', research_topic)
        clean_topic = re.sub(r'\s+', '_', clean_topic.strip())
        
        filename = f"{timestamp}_{clean_topic[:50]}_ollama.md"
        filepath = os.path.join(reports_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        return filepath

    def run_research(self, research_topic: str, max_iterations: int = 3,
                     quality_threshold: float = 8.0, polish_iterations: int = 1):
        """Synchronous wrapper"""
        import asyncio
        return asyncio.run(self.run_research_async(research_topic, max_iterations, quality_threshold, polish_iterations))


if __name__ == "__main__":
    import asyncio
    
    society = HypothesisGenerationSociety()
    team = society.create_research_team()
    
    async def interactive_main():
        if len(sys.argv) > 1:
            topic = " ".join(sys.argv[1:])
            result = await society.run_research_async(topic, max_iterations=3, quality_threshold=8.0)
            if not result.failed:
                print(f"Report saved: {result.metadata.get('file_path', 'N/A')}")
            return
        
        topic = input("Enter research question: ").strip()
        if topic:
            result = await society.run_research_async(topic, max_iterations=3, quality_threshold=8.0)
            if not result.failed:
                print(f"Report saved: {result.metadata.get('file_path', 'N/A')}")
    
    try:
        asyncio.run(interactive_main())
    except KeyboardInterrupt:
        pass
