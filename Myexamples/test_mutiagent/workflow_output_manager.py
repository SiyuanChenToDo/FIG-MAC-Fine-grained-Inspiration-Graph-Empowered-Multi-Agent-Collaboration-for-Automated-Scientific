#!/usr/bin/env python3
"""
Workflow Output Manager
Based on CAMEL native messaging system, provides complete workflow output management for Stage 3 output separation fix

Based on Stage 2 modular architecture, ensures complete workflow of 8-agent collaboration has clear output records
"""

import json
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path

from camel.messages import BaseMessage
from camel.responses import ChatAgentResponse
from Myexamples.test_mutiagent.camel_logger_formatter import OutputFormatter
from Myexamples.test_mutiagent.intelligent_report_generator import IntelligentReportGenerator

# Import existing result types for compatibility
try:
    from Myexamples.agents.camel_native_agent import HypothesisTaskResult
except ImportError:
    OutputFormatter.warning("Cannot import HypothesisTaskResult, using simplified version")
    from pydantic import BaseModel, Field
    
    class HypothesisTaskResult(BaseModel):
        """Simplified version of hypothesis generation task result format"""
        content: str = Field(description="Task execution result content")
        failed: bool = Field(default=False, description="Whether task failed")
        task_type: str = Field(default="unknown", description="Task type")
        metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata")


@dataclass
class PhaseOutput:
    """Phase output record"""
    phase: str
    agent_name: str
    content: str
    metadata: Dict[str, Any]
    timestamp: str
    success: bool
    content_length: int
    structured_sections: Dict[str, str]


@dataclass
class AgentInteraction:
    """Agent interaction record"""
    sender: str
    receiver: str
    message_content: str
    response_content: str
    interaction_type: str
    timestamp: str
    metadata: Dict[str, Any]


@dataclass
class WorkflowExecution:
    """Workflow execution record"""
    topic: str
    start_time: str
    end_time: Optional[str]
    total_phases: int
    completed_phases: int
    success: bool
    final_result: Optional[str]
    execution_metadata: Dict[str, Any]


class WorkflowOutputManager:
    """
    Workflow Output Manager - Based on Stage 2 modular architecture
    
    Features:
    1. Record output from each phase
    2. Track interactions between agents
    3. Manage complete workflow execution records
    4. Generate structured process reports
    5. Integrate CAMEL message history
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize workflow output manager
        
        Args:
            output_dir: Output directory path, defaults to workflow_outputs in current directory
        """
        self.output_dir = Path(output_dir) if output_dir else Path("workflow_outputs")
        self.output_dir.mkdir(exist_ok=True)
        
        # Core data structures
        self.phase_outputs: Dict[str, PhaseOutput] = {}
        self.interaction_logs: List[AgentInteraction] = []
        self.final_report_sections: Dict[str, str] = {}
        self.workflow_execution: Optional[WorkflowExecution] = None
        
        # Phase order definition
        self.phase_order = [
            "literature", "ideation", "analysis", 
            "synthesis", "review", "polish"
        ]
        
        # Agent role mapping
        self.agent_roles = {
            "Scholar Scour": "Literature Research Expert",
            "Idea Igniter": "Innovation Thinking Expert", 
            "Analysis Ace": "Analysis Evaluation Expert",
            "Theory Tester": "Theory Verification Expert",
            "Experiment Explorer": "Experiment Design Expert",
            "Data Detective": "Data Analysis Expert",
            "Synthesis Sage": "Synthesis Evaluation Expert",
            "Review Rigor": "Peer Review Expert",
            "Polish Pro": "Document Optimization Expert"
        }
        
        # Intelligent report generator - Stage 3 report quality optimization
        self.report_generator = IntelligentReportGenerator()
        
        OutputFormatter.info("Workflow Output Manager initialized")
    
    def start_workflow_tracking(self, topic: str) -> str:
        """
        Start workflow tracking
        
        Args:
            topic: Research topic
            
        Returns:
            str: Workflow execution ID
        """
        workflow_id = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.workflow_execution = WorkflowExecution(
            topic=topic,
            start_time=datetime.now().isoformat(),
            end_time=None,
            total_phases=len(self.phase_order),
            completed_phases=0,
            success=False,
            final_result=None,
            execution_metadata={
                "workflow_id": workflow_id,
                "agents_count": len(self.agent_roles),
                "expected_phases": self.phase_order.copy()
            }
        )
        
        OutputFormatter.info(f"Starting workflow tracking: {topic} (ID: {workflow_id})")
        return workflow_id
    
    def record_phase_output(self, phase: str, agent_name: str, 
                          content: str, metadata: Dict[str, Any],
                          structured_sections: Optional[Dict[str, str]] = None) -> str:
        """
        Record phase output
        
        Args:
            phase: Phase name
            agent_name: Agent name
            content: Output content
            metadata: Metadata
            structured_sections: Structured sections
            
        Returns:
            str: Output record ID
        """
        timestamp = datetime.now().isoformat()
        output_id = f"{phase}_{agent_name}_{datetime.now().strftime('%H%M%S')}"
        
        # Create phase output record
        phase_output = PhaseOutput(
            phase=phase,
            agent_name=agent_name,
            content=content,
            metadata=metadata,
            timestamp=timestamp,
            success=len(content.strip()) > 0,
            content_length=len(content),
            structured_sections=structured_sections or {}
        )
        
        # Store record
        self.phase_outputs[output_id] = phase_output
        
        # Update workflow execution status
        if self.workflow_execution and phase in self.phase_order:
            phase_index = self.phase_order.index(phase)
            if phase_index + 1 > self.workflow_execution.completed_phases:
                self.workflow_execution.completed_phases = phase_index + 1
        
        # Save to file
        self._save_phase_output_to_file(output_id, phase_output)
        
        OutputFormatter.success(
            f"Recording phase output: {phase} - {agent_name} "
            f"({len(content)} characters)"
        )
        
        # Phase output recorded successfully
        return output_id
    
    def finalize_workflow(self, final_result: str, success: bool = True) -> Dict[str, Any]:
        """
        Finalize workflow tracking
        
        Args:
            final_result: Final result
            success: Whether successful
            
        Returns:
            Dict[str, Any]: Workflow summary
        """
        if not self.workflow_execution:
            OutputFormatter.warning("Workflow execution record does not exist, cannot complete tracking")
            return {}
        
        # Update workflow execution status
        self.workflow_execution.end_time = datetime.now().isoformat()
        self.workflow_execution.success = success
        self.workflow_execution.final_result = final_result
        
        # Generate workflow summary
        summary = self.generate_workflow_summary()
        
        # Save complete workflow record
        self._save_complete_workflow_record()
        
        OutputFormatter.success(
            f"Workflow tracking completed: {self.workflow_execution.topic} "
            f"(Success: {success}, Phases: {self.workflow_execution.completed_phases}/{self.workflow_execution.total_phases})"
        )
        
        return summary
    
    def generate_complete_workflow_report(self) -> str:
        """
        Generate complete workflow report
        
        Returns:
            str: Complete workflow report
        """
        if not self.workflow_execution:
            return "Workflow execution record does not exist"
        
        report_sections = []
        
        # Report title and summary
        report_sections.append(f"# Scientific Hypothesis Generation Workflow Report")
        report_sections.append(f"**Research Topic**: {self.workflow_execution.topic}")
        report_sections.append(f"**Execution Time**: {self.workflow_execution.start_time} - {self.workflow_execution.end_time}")
        report_sections.append(f"**Execution Status**: {'Success' if self.workflow_execution.success else 'Failed'}")
        report_sections.append(f"**Completed Phases**: {self.workflow_execution.completed_phases}/{self.workflow_execution.total_phases}")
        report_sections.append("")
        
        # Execution summary
        report_sections.append("## Execution Summary")
        summary = self.generate_workflow_summary()
        report_sections.append(f"- **Total Outputs**: {summary.get('total_outputs', 0)}")
        report_sections.append(f"- **Successful Outputs**: {summary.get('successful_outputs', 0)}")
        report_sections.append(f"- **Agent Interactions**: {summary.get('total_interactions', 0)}")
        report_sections.append(f"- **Average Content Length**: {summary.get('average_content_length', 0):.0f} characters")
        report_sections.append("")
        
        # Organize output by phases
        report_sections.append("## Detailed Phase Outputs")
        
        for phase in self.phase_order:
            phase_outputs = [
                output for output in self.phase_outputs.values() 
                if output.phase == phase
            ]
            
            if phase_outputs:
                report_sections.append(f"### {phase.title()} Phase")
                
                for output in phase_outputs:
                    agent_role = self.agent_roles.get(output.agent_name, output.agent_name)
                    report_sections.append(f"#### {agent_role} ({output.agent_name})")
                    report_sections.append(f"**Time**: {output.timestamp}")
                    report_sections.append(f"**Status**: {'Success' if output.success else 'Failed'}")
                    report_sections.append(f"**Content Length**: {output.content_length} characters")
                    
                    # Add structured sections
                    if output.structured_sections:
                        report_sections.append("**Structured Sections**:")
                        for section_name, section_content in output.structured_sections.items():
                            if section_content.strip():
                                report_sections.append(f"- **{section_name}**: {len(section_content)} characters")
                    
                    # Add content preview
                    content_preview = output.content[:300] + "..." if len(output.content) > 300 else output.content
                    report_sections.append("**Content Preview**:")
                    report_sections.append(f"```\n{content_preview}\n```")
                    report_sections.append("")
        
        # Agent interaction records
        if self.interaction_logs:
            report_sections.append("## Agent Interaction Records")
            
            for i, interaction in enumerate(self.interaction_logs[-10:], 1):  # Only show last 10 interactions
                sender_role = self.agent_roles.get(interaction.receiver, interaction.receiver)
                report_sections.append(f"### Interaction {i}: {sender_role}")
                report_sections.append(f"**Time**: {interaction.timestamp}")
                report_sections.append(f"**Type**: {interaction.interaction_type}")
                report_sections.append(f"**Message Length**: {interaction.metadata.get('message_length', 0)} characters")
                report_sections.append(f"**Response Length**: {interaction.metadata.get('response_length', 0)} characters")
                report_sections.append("")
        
        # Final result
        if self.workflow_execution.final_result:
            report_sections.append("## Final Result")
            final_preview = self.workflow_execution.final_result[:500] + "..." if len(self.workflow_execution.final_result) > 500 else self.workflow_execution.final_result
            report_sections.append(f"```\n{final_preview}\n```")
        
        return "\n".join(report_sections)
    
    def generate_intelligent_report(self) -> str:
        """
        Generate intelligent optimized report (Stage 3 new feature)
        
        Returns:
            str: Intelligent optimized scientific report
        """
        try:
            return self.report_generator.generate_report_from_manager(self)
        except Exception as e:
            OutputFormatter.error(f"Intelligent report generation failed: {e}")
            return self.generate_complete_workflow_report()  # Fallback to basic report
    
    def generate_workflow_summary(self) -> Dict[str, Any]:
        """Generate workflow summary statistics"""
        summary = {
            "total_outputs": len(self.phase_outputs),
            "successful_outputs": sum(1 for output in self.phase_outputs.values() if output.success),
            "failed_outputs": sum(1 for output in self.phase_outputs.values() if not output.success),
            "total_interactions": len(self.interaction_logs),
            "phases_completed": len(set(output.phase for output in self.phase_outputs.values())),
            "agents_involved": len(set(output.agent_name for output in self.phase_outputs.values())),
            "total_content_length": sum(output.content_length for output in self.phase_outputs.values()),
            "average_content_length": 0,
            "phase_distribution": {},
            "agent_contribution": {}
        }
        
        # 计算平均内容长度
        if summary["total_outputs"] > 0:
            summary["average_content_length"] = summary["total_content_length"] / summary["total_outputs"]
        
        # 阶段分布统计
        for output in self.phase_outputs.values():
            phase = output.phase
            if phase not in summary["phase_distribution"]:
                summary["phase_distribution"][phase] = 0
            summary["phase_distribution"][phase] += 1
        
        # 智能体贡献统计
        for output in self.phase_outputs.values():
            agent = output.agent_name
            if agent not in summary["agent_contribution"]:
                summary["agent_contribution"][agent] = {
                    "outputs": 0,
                    "total_length": 0,
                    "phases": set()
                }
            summary["agent_contribution"][agent]["outputs"] += 1
            summary["agent_contribution"][agent]["total_length"] += output.content_length
            summary["agent_contribution"][agent]["phases"].add(output.phase)
        
        # Convert sets to lists for JSON serialization
        for agent_stats in summary["agent_contribution"].values():
            agent_stats["phases"] = list(agent_stats["phases"])
        
        return summary
    
    def get_phase_outputs(self, phase: str) -> List[PhaseOutput]:
        """Get all outputs for specified phase"""
        return [
            output for output in self.phase_outputs.values() 
            if output.phase == phase
        ]
    
    def get_agent_outputs(self, agent_name: str) -> List[PhaseOutput]:
        """Get all outputs for specified agent"""
        return [
            output for output in self.phase_outputs.values() 
            if output.agent_name == agent_name
        ]
    
    def export_workflow_data(self, format: str = "json") -> str:
        """
        Export workflow data
        
        Args:
            format: Export format ("json" or "markdown")
            
        Returns:
            str: Export file path
        """
        if not self.workflow_execution:
            OutputFormatter.warning("No workflow data available for export")
            return ""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == "json":
            # Export JSON format
            export_data = {
                "workflow_execution": asdict(self.workflow_execution),
                "phase_outputs": {k: asdict(v) for k, v in self.phase_outputs.items()},
                "interaction_logs": [asdict(interaction) for interaction in self.interaction_logs],
                "summary": self.generate_workflow_summary()
            }
            
            filename = f"workflow_data_{timestamp}.json"
            filepath = self.output_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
                
        elif format == "markdown":
            # Export Markdown format
            report_content = self.generate_complete_workflow_report()
            
            filename = f"workflow_report_{timestamp}.md"
            filepath = self.output_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report_content)
        
        OutputFormatter.success(f"Workflow data exported: {filepath}")
        return str(filepath)
    
    def _save_phase_output_to_file(self, output_id: str, phase_output: PhaseOutput):
        """Save phase output to file"""
        try:
            phase_dir = self.output_dir / "phases" / phase_output.phase
            phase_dir.mkdir(parents=True, exist_ok=True)
            
            filename = f"{output_id}.json"
            filepath = phase_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(asdict(phase_output), f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            OutputFormatter.error(f"Failed to save phase output: {e}")
    
    def _save_interaction_to_file(self, interaction_id: str, interaction: AgentInteraction):
        """Save interaction record to file"""
        try:
            interaction_dir = self.output_dir / "interactions"
            interaction_dir.mkdir(parents=True, exist_ok=True)
            
            filename = f"{interaction_id}.json"
            filepath = interaction_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(asdict(interaction), f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            OutputFormatter.error(f"Failed to save interaction record: {e}")
    
    def _save_complete_workflow_record(self):
        """Save complete workflow record"""
        try:
            if not self.workflow_execution:
                return
            
            workflow_id = self.workflow_execution.execution_metadata.get("workflow_id", "unknown")
            filename = f"complete_workflow_{workflow_id}.json"
            filepath = self.output_dir / filename
            
            complete_record = {
                "workflow_execution": asdict(self.workflow_execution),
                "phase_outputs": {k: asdict(v) for k, v in self.phase_outputs.items()},
                "interaction_logs": [asdict(interaction) for interaction in self.interaction_logs],
                "summary": self.generate_workflow_summary(),
                "export_timestamp": datetime.now().isoformat()
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(complete_record, f, ensure_ascii=False, indent=2)
                
            OutputFormatter.success(f"Complete workflow record saved: {filepath}")
            
        except Exception as e:
            OutputFormatter.error(f"Failed to save complete workflow record: {e}")


# Test functionality
if __name__ == "__main__":
    print("=== Workflow Output Manager Test ===")
    
    # Create manager instance
    manager = WorkflowOutputManager()
    
    # Test workflow tracking
    workflow_id = manager.start_workflow_tracking("AI Applications in Medical Diagnosis")
    print(f"Workflow ID: {workflow_id}")
    
    # Test phase output recording
    output_id = manager.record_phase_output(
        phase="literature",
        agent_name="Scholar Scour",
        content="This is test content for literature review, containing comprehensive analysis of related research.",
        metadata={"agent_type": "research", "quality_score": 0.8},
        structured_sections={"introduction": "Introduction section", "findings": "Findings section"}
    )
    print(f"Output ID: {output_id}")
    
    # Test workflow summary
    summary = manager.generate_workflow_summary()
    print(f"Workflow summary: {summary}")
    
    # Test report generation
    report = manager.generate_complete_workflow_report()
    print(f"Report length: {len(report)} characters")
    
    # Test workflow completion
    final_summary = manager.finalize_workflow("Test workflow completed", True)
    print(f"Final summary: {final_summary}")
    
    OutputFormatter.success("Workflow Output Manager test completed")
