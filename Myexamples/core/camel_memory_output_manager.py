#!/usr/bin/env python3
"""
CAMEL Memory-Based Output Manager
Based on FIG-MAC experience and CAMEL native memory system integration

Core Design Philosophy:
- From "Complex Extraction" to "Simple Storage"
- Utilize CAMEL ChatHistoryMemory and MemoryRecord for complete conversation history
- Structured output extraction via extract_between_json_tags()
- Multi-layer storage strategy: memory + file storage + checkpoint mechanism
- Intelligent fault tolerance with fallback mechanisms
- Prompt-driven design for output format control
"""

import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict

from camel.memories import ChatHistoryMemory, MemoryRecord
from camel.messages import BaseMessage
from camel.responses import ChatAgentResponse
# Note: extract_between_json_tags may not be available in current CAMEL version
# We'll implement a simple JSON extraction method

from Myexamples.core.camel_logger_formatter import OutputFormatter


def extract_json_from_text(text: str) -> Optional[str]:
    """
    Simple JSON extraction from text (FIG-MAC inspired)
    Extracts JSON content between ```json and ``` or { and }
    """
    import re
    
    # Try to find JSON blocks marked with ```json
    json_pattern = r'```json\s*(\{.*?\})\s*```'
    match = re.search(json_pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1)
    
    # Try to find standalone JSON objects
    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    matches = re.findall(json_pattern, text, re.DOTALL)
    if matches:
        # Return the largest JSON object found
        return max(matches, key=len)
    
    return None


@dataclass
class HypothesisMemoryRecord:
    """Hypothesis generation memory record based on CAMEL MemoryRecord"""
    phase: str
    agent_name: str
    timestamp: str
    message_content: str
    response_content: str
    structured_data: Optional[Dict[str, Any]] = None
    extraction_success: bool = True
    memory_id: Optional[str] = None


class CAMELMemoryOutputManager:
    """
    CAMEL Memory-Based Output Manager
    
    Based on FIG-MAC successful experience:
    1. CAMEL ChatHistoryMemory for complete conversation history
    2. extract_between_json_tags() for structured content extraction
    3. Multi-layer storage: memory + file + checkpoint
    4. Intelligent fault tolerance with fallback mechanisms
    5. Prompt-driven output format control
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        """Initialize CAMEL memory-based output manager"""
        self.output_dir = Path(output_dir) if output_dir else Path("workflow_outputs")
        self.output_dir.mkdir(exist_ok=True)
        
        # CAMEL native memory system
        # ChatHistoryMemory requires context_creator parameter
        from camel.memories.context_creators.score_based import ScoreBasedContextCreator
        from camel.utils import OpenAITokenCounter
        from camel.types import ModelType
        
        context_creator = ScoreBasedContextCreator(
            token_counter=OpenAITokenCounter(ModelType.GPT_4O_MINI),
            token_limit=8192,
        )
        self.chat_memory = ChatHistoryMemory(context_creator=context_creator)
        
        # Hypothesis-specific memory records
        self.hypothesis_records: List[HypothesisMemoryRecord] = []
        
        # Phase tracking
        self.current_workflow_id: Optional[str] = None
        self.phase_order = [
            "literature", "ideation", "analysis", 
            "synthesis", "review", "polish"
        ]
        
        # FIG-MAC inspired extraction patterns
        self.json_extraction_patterns = {
            "analysis": ["technical_analysis", "practical_analysis", "significance_analysis"],
            "structured_output": ["hypothesis", "methodology", "evaluation"]
        }
        
        self.logger = logging.getLogger(f"{__name__}.CAMELMemoryOutputManager")
        OutputFormatter.info("CAMEL Memory Output Manager initialized")
    
    def start_workflow_memory_tracking(self, topic: str) -> str:
        """Start workflow memory tracking with CAMEL memory system"""
        workflow_id = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.current_workflow_id = workflow_id
        
        # Create initial memory record
        init_message = BaseMessage.make_user_message(
            role_name="HypothesisTeam",
            content=f"Starting scientific hypothesis generation workflow for topic: {topic}"
        )
        
        # Add to CAMEL memory
        memory_record = MemoryRecord(
            message=init_message,
            role_at_backend="user"
        )
        self.chat_memory.write_records([memory_record])
        
        OutputFormatter.info(f"Started workflow memory tracking: {topic} (ID: {workflow_id})")
        return workflow_id
    
    def record_agent_conversation(self, phase: str, agent_name: str, 
                                 message: BaseMessage, response: ChatAgentResponse) -> str:
        """
        Record agent conversation using CAMEL memory system
        
        Based on FIG-MAC experience:
        1. Store complete conversation in ChatHistoryMemory
        2. Extract structured content using extract_between_json_tags
        3. Create hypothesis-specific memory record
        4. Implement intelligent fallback for extraction failures
        """
        timestamp = datetime.now().isoformat()
        memory_id = f"{phase}_{agent_name}_{datetime.now().strftime('%H%M%S')}"
        
        try:
            # Store in CAMEL ChatHistoryMemory
            message_record = MemoryRecord(message=message, role_at_backend="user")
            response_message = BaseMessage.make_assistant_message(
                role_name=agent_name,
                content=response.msg.content
            )
            response_record = MemoryRecord(message=response_message, role_at_backend="assistant")
            
            self.chat_memory.write_records([message_record, response_record])
            
            # Extract structured content (FIG-MAC approach)
            structured_data = self._extract_structured_content(response.msg.content, phase)
            
            # Create hypothesis memory record
            hypothesis_record = HypothesisMemoryRecord(
                phase=phase,
                agent_name=agent_name,
                timestamp=timestamp,
                message_content=message.content,
                response_content=response.msg.content,
                structured_data=structured_data,
                extraction_success=structured_data is not None,
                memory_id=memory_id
            )
            
            self.hypothesis_records.append(hypothesis_record)
            
            # Save to file (checkpoint mechanism)
            self._save_memory_record_to_file(hypothesis_record)
            
            OutputFormatter.success(
                f"Recorded conversation: {phase} - {agent_name} "
                f"(Memory ID: {memory_id}, Structured: {structured_data is not None})"
            )
            
            return memory_id
            
        except Exception as e:
            OutputFormatter.error(f"Failed to record conversation: {e}")
            # Fallback: create basic record without structured data
            fallback_record = HypothesisMemoryRecord(
                phase=phase,
                agent_name=agent_name,
                timestamp=timestamp,
                message_content=str(message),
                response_content=str(response.msg.content),
                structured_data=None,
                extraction_success=False,
                memory_id=memory_id
            )
            self.hypothesis_records.append(fallback_record)
            return memory_id
    
    def _extract_structured_content(self, content: str, phase: str) -> Optional[Dict[str, Any]]:
        """
        Extract structured content using FIG-MAC approach
        
        Uses CAMEL's extract_between_json_tags for robust JSON extraction
        """
        try:
            # Try to extract JSON content (FIG-MAC inspired method)
            json_content = extract_json_from_text(content)
            if json_content:
                try:
                    return json.loads(json_content)
                except json.JSONDecodeError:
                    # JSON extraction found but parsing failed - this is expected
                    # when agents output non-JSON content (most phases use markdown)
                    pass
            
            # Fallback: look for specific patterns based on phase
            if phase == "analysis":
                return self._extract_analysis_patterns(content)
            elif phase in ["synthesis", "review", "polish"]:
                return self._extract_markdown_sections(content)
            
            return None
            
        except Exception as e:
            # Log as debug since this is expected behavior for non-structured content
            self.logger.debug(f"Structured content extraction skipped for phase '{phase}': {e}")
            return None
    
    def _extract_analysis_patterns(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract analysis-specific patterns for JSON output phases"""
        patterns = {
            "technical_plausibility": r"technical[_\s]plausibility[\"']?\s*:\s*{([^}]+)}",
            "practical_feasibility": r"practical[_\s]feasibility[\"']?\s*:\s*{([^}]+)}",
            "significance_score": r"significance[_\s]score[\"']?\s*:\s*(\d+)"
        }
        
        extracted = {}
        for key, pattern in patterns.items():
            import re
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                extracted[key] = match.group(1) if len(match.groups()) > 0 else match.group(0)
        
        return extracted if extracted else None
    
    def _extract_markdown_sections(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract markdown sections for structured phases"""
        sections = {}
        current_section = None
        current_content = []
        
        for line in content.split('\n'):
            if line.startswith('#'):
                if current_section:
                    sections[current_section] = '\n'.join(current_content).strip()
                current_section = line.strip('#').strip().lower().replace(' ', '_')
                current_content = []
            else:
                current_content.append(line)
        
        if current_section:
            sections[current_section] = '\n'.join(current_content).strip()
        
        return sections if sections else None
    
    def get_phase_memories(self, phase: str) -> List[HypothesisMemoryRecord]:
        """Get all memory records for a specific phase"""
        return [record for record in self.hypothesis_records if record.phase == phase]
    
    def get_agent_memories(self, agent_name: str) -> List[HypothesisMemoryRecord]:
        """Get all memory records for a specific agent"""
        return [record for record in self.hypothesis_records if record.agent_name == agent_name]
    
    def get_complete_conversation_history(self) -> List[MemoryRecord]:
        """Get complete conversation history from CAMEL memory"""
        return self.chat_memory.retrieve()
    
    def generate_memory_based_report(self) -> str:
        """
        Generate comprehensive report based on memory records
        
        FIG-MAC inspired approach:
        1. Retrieve complete conversation history
        2. Organize by phases and agents
        3. Include both raw content and structured extractions
        4. Provide memory statistics and quality metrics
        """
        if not self.hypothesis_records:
            return "No memory records available for report generation."
        
        report_sections = []
        
        # Report header
        report_sections.append("# Scientific Hypothesis Generation Memory Report")
        report_sections.append(f"**Workflow ID**: {self.current_workflow_id}")
        report_sections.append(f"**Generated**: {datetime.now().isoformat()}")
        report_sections.append(f"**Total Memory Records**: {len(self.hypothesis_records)}")
        report_sections.append("")
        
        # Memory statistics
        report_sections.append("## Memory Statistics")
        phase_counts = {}
        structured_count = 0
        
        for record in self.hypothesis_records:
            phase_counts[record.phase] = phase_counts.get(record.phase, 0) + 1
            if record.extraction_success:
                structured_count += 1
        
        report_sections.append(f"- **Total Conversations**: {len(self.hypothesis_records)}")
        report_sections.append(f"- **Structured Extractions**: {structured_count}/{len(self.hypothesis_records)}")
        report_sections.append(f"- **Extraction Success Rate**: {structured_count/len(self.hypothesis_records)*100:.1f}%")
        report_sections.append("")
        
        # Phase-by-phase breakdown
        report_sections.append("## Phase Memory Records")
        
        for phase in self.phase_order:
            phase_records = self.get_phase_memories(phase)
            if not phase_records:
                continue
                
            report_sections.append(f"### {phase.title()} Phase")
            
            for record in phase_records:
                report_sections.append(f"#### {record.agent_name}")
                report_sections.append(f"**Time**: {record.timestamp}")
                report_sections.append(f"**Memory ID**: {record.memory_id}")
                report_sections.append(f"**Structured Data**: {'✅' if record.extraction_success else '❌'}")
                
                # Content preview
                content_preview = record.response_content[:300] + "..." if len(record.response_content) > 300 else record.response_content
                report_sections.append(f"**Response Preview**:")
                report_sections.append(f"```\n{content_preview}\n```")
                
                # Structured data if available
                if record.structured_data:
                    report_sections.append(f"**Extracted Structure**:")
                    report_sections.append(f"```json\n{json.dumps(record.structured_data, indent=2)}\n```")
                
                report_sections.append("")
        
        # CAMEL memory system summary
        camel_records = self.get_complete_conversation_history()
        report_sections.append("## CAMEL Memory System Summary")
        report_sections.append(f"- **Total CAMEL Records**: {len(camel_records)}")
        report_sections.append(f"- **Memory System**: ChatHistoryMemory")
        report_sections.append(f"- **Storage Method**: In-memory + File checkpoints")
        report_sections.append("")
        
        return "\n".join(report_sections)
    
    def export_memory_data(self, format: str = "json") -> str:
        """Export all memory data in specified format"""
        if not self.current_workflow_id:
            OutputFormatter.warning("No workflow data available for export")
            return ""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == "json":
            # Export comprehensive memory data
            export_data = {
                "workflow_id": self.current_workflow_id,
                "export_timestamp": datetime.now().isoformat(),
                "hypothesis_records": [asdict(record) for record in self.hypothesis_records],
                "camel_memory_records": [
                    {
                        "message_content": record.message.content,
                        "role": record.message.role_name,
                        "role_at_backend": record.role_at_backend
                    } for record in self.get_complete_conversation_history()
                ],
                "memory_statistics": {
                    "total_records": len(self.hypothesis_records),
                    "structured_extractions": sum(1 for r in self.hypothesis_records if r.extraction_success),
                    "phases_covered": len(set(r.phase for r in self.hypothesis_records)),
                    "agents_involved": len(set(r.agent_name for r in self.hypothesis_records))
                }
            }
            
            filename = f"camel_memory_export_{timestamp}.json"
            filepath = self.output_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
                
        elif format == "markdown":
            # Export markdown report
            report_content = self.generate_memory_based_report()
            
            filename = f"camel_memory_report_{timestamp}.md"
            filepath = self.output_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report_content)
        
        OutputFormatter.success(f"Memory data exported: {filepath}")
        return str(filepath)
    
    def _save_memory_record_to_file(self, record: HypothesisMemoryRecord):
        """Save individual memory record to file (checkpoint mechanism)"""
        try:
            memory_dir = self.output_dir / "memory_records" / record.phase
            memory_dir.mkdir(parents=True, exist_ok=True)
            
            filename = f"{record.memory_id}.json"
            filepath = memory_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(asdict(record), f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save memory record: {e}")
    
    def clear_workflow_memory(self):
        """Clear current workflow memory (for new workflow start)"""
        self.chat_memory.clear()
        self.hypothesis_records.clear()
        self.current_workflow_id = None
        OutputFormatter.info("Workflow memory cleared")


# Test functionality
if __name__ == "__main__":
    print("=== CAMEL Memory Output Manager Test ===")
    
    # Create manager instance
    manager = CAMELMemoryOutputManager()
    
    # Test workflow tracking
    workflow_id = manager.start_workflow_memory_tracking("AI Applications in Medical Diagnosis")
    print(f"Workflow ID: {workflow_id}")
    
    # Test memory export
    export_path = manager.export_memory_data("json")
    print(f"Memory data exported: {export_path}")
    
    OutputFormatter.success("CAMEL Memory Output Manager test completed")
