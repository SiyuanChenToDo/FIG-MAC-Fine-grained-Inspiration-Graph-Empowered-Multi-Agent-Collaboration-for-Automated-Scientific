#!/usr/bin/env python3
"""
Intelligent Report Generator
Based on CAMEL and Stage 2 architecture, provides high-quality scientific report generation for Stage 3 output separation fix

Enhances structure, quality and readability of final scientific hypothesis reports
"""

import re
import json
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from dataclasses import dataclass

from Myexamples.core.camel_logger_formatter import OutputFormatter


@dataclass
class ReportSection:
    """Report section data class"""
    title: str
    content: str
    agent_name: str
    phase: str
    order: int
    quality_score: float


class ReportTemplateManager:
    """Report template manager"""
    
    def __init__(self):
        self.template = self._create_scientific_template()
    
    def _create_scientific_template(self) -> Dict[str, Any]:
        """Create scientific report template"""
        return {
            "title": "# Scientific Hypothesis Generation Report",
            "sections": [
                {
                    "id": "executive_summary",
                    "title": "## Executive Summary",
                    "description": "Research topic, core hypothesis, main findings",
                    "required": True,
                    "order": 1
                },
                {
                    "id": "literature_review", 
                    "title": "## 1. Literature Review",
                    "description": "Current research status, key findings, research gaps",
                    "agent": "Scholar Scour",
                    "phase": "literature",
                    "required": True,
                    "order": 2
                },
                {
                    "id": "innovation",
                    "title": "## 2. Innovation Ideas",
                    "description": "Innovation perspectives, hypothesis proposal, theoretical foundation",
                    "agent": "Idea Igniter",
                    "phase": "ideation", 
                    "required": True,
                    "order": 3
                },
                {
                    "id": "analysis",
                    "title": "## 3. Multi-dimensional Analysis",
                    "description": "Theoretical analysis, experimental design, data analysis",
                    "phase": "analysis",
                    "required": True,
                    "order": 4,
                    "subsections": [
                        {"title": "### 3.1 Theoretical Analysis", "agent": "Theory Tester"},
                        {"title": "### 3.2 Experimental Design", "agent": "Experiment Explorer"},
                        {"title": "### 3.3 Data Analysis", "agent": "Data Detective"}
                    ]
                },
                {
                    "id": "synthesis",
                    "title": "## 4. Comprehensive Evaluation",
                    "description": "Hypothesis integration, feasibility analysis, impact assessment",
                    "agent": "Synthesis Sage",
                    "phase": "synthesis",
                    "required": True,
                    "order": 5
                },
                {
                    "id": "review",
                    "title": "## 5. Peer Review",
                    "description": "Methodology evaluation, potential issues, improvement suggestions",
                    "agent": "Review Rigor",
                    "phase": "review",
                    "required": True,
                    "order": 6
                },
                {
                    "id": "polish",
                    "title": "## 6. Final Refinement",
                    "description": "Expression optimization, logic improvement, final recommendations",
                    "agent": "Polish Pro",
                    "phase": "polish",
                    "required": True,
                    "order": 7
                },
                {
                    "id": "conclusion",
                    "title": "## Conclusion and Outlook",
                    "description": "Research conclusions, future directions, practical significance",
                    "required": True,
                    "order": 8
                }
            ]
        }


class ContentProcessor:
    """Content processor"""
    
    @staticmethod
    def remove_content_duplication(sections: Dict[str, str]) -> Dict[str, str]:
        """Remove content duplication"""
        processed_sections = {}
        seen_content = set()
        
        for section_id, content in sections.items():
            # Sentence processing
            sentences = re.split(r'[。！？.!?]', content)
            unique_sentences = []
            
            for sentence in sentences:
                sentence = sentence.strip()
                if sentence and sentence not in seen_content:
                    unique_sentences.append(sentence)
                    seen_content.add(sentence)
            
            processed_sections[section_id] = '。'.join(unique_sentences)
        
        return processed_sections
    
    @staticmethod
    def enhance_logical_flow(report_content: str) -> str:
        """Enhance logical coherence"""
        # Add transition words and connectors
        transitions = {
            r'## \d+\.': lambda m: f"\n{m.group(0)}",  # Add blank line before sections
            r'### \d+\.\d+': lambda m: f"\n{m.group(0)}",  # Add blank line before subsections
            r'(\.)\s*(However|But|Therefore|So|In summary)': r'\1\n\n\2',  # Add paragraph separation before logical transitions
        }
        
        enhanced_content = report_content
        for pattern, replacement in transitions.items():
            enhanced_content = re.sub(pattern, replacement, enhanced_content)
        
        return enhanced_content


class ReportQualityValidator:
    """Report quality validator"""
    
    @staticmethod
    def validate_report_quality(report: str) -> Dict[str, Any]:
        """Validate report quality"""
        validation = {
            "overall_score": 0.0,
            "completeness": 0.0,
            "structure": 0.0,
            "content_quality": 0.0,
            "issues": [],
            "suggestions": []
        }
        
        # Completeness check
        required_sections = ["Executive Summary", "Literature Review", "Innovation Ideas", "Multi-dimensional Analysis", "Comprehensive Evaluation", "Peer Review", "Conclusion"]
        found_sections = sum(1 for section in required_sections if section in report)
        validation["completeness"] = found_sections / len(required_sections)
        
        # Structure check
        title_count = len(re.findall(r'^#{1,3}\s+', report, re.MULTILINE))
        validation["structure"] = min(1.0, title_count / 8)  # Expect at least 8 titles
        
        # Content quality check
        word_count = len(report.split())
        validation["content_quality"] = min(1.0, word_count / 2000)  # Expect at least 2000 words
        
        # Calculate total score
        validation["overall_score"] = (
            validation["completeness"] * 0.4 +
            validation["structure"] * 0.3 +
            validation["content_quality"] * 0.3
        )
        
        # Generate suggestions
        if validation["completeness"] < 0.8:
            validation["issues"].append("Report sections incomplete")
            validation["suggestions"].append("Add missing section content")
        
        if validation["structure"] < 0.7:
            validation["issues"].append("Report structure unclear")
            validation["suggestions"].append("Add section titles and subtitles")
        
        if validation["content_quality"] < 0.6:
            validation["issues"].append("Content length insufficient")
            validation["suggestions"].append("Add detailed explanations and analysis")
        
        return validation


class IntelligentReportGenerator:
    """
    Intelligent Report Generator - Based on CAMEL and Stage 2 architecture
    
    Functions:
    1. Generate structured scientific reports
    2. Remove content duplication
    3. Enhance logical coherence
    4. Validate report quality
    """
    
    def __init__(self):
        """Initialize intelligent report generator"""
        self.template_manager = ReportTemplateManager()
        self.content_processor = ContentProcessor()
        self.quality_validator = ReportQualityValidator()
        
        OutputFormatter.info("Intelligent Report Generator initialized")
    
    def generate_structured_report(self, workflow_outputs: Dict[str, Any]) -> str:
        """
        Generate structured scientific report
        
        Args:
            workflow_outputs: Workflow output data
            
        Returns:
            str: Generated structured report
        """
        try:
            # Extract workflow data
            workflow_execution = workflow_outputs.get("workflow_execution", {})
            phase_outputs = workflow_outputs.get("phase_outputs", {})
            summary = workflow_outputs.get("summary", {})
            
            # Build report sections
            report_sections = self._build_report_sections(workflow_execution, phase_outputs, summary)
            
            # Remove duplicate content
            deduplicated_sections = self.content_processor.remove_content_duplication(report_sections)
            
            # Generate complete report
            complete_report = self._assemble_report(deduplicated_sections, workflow_execution)
            
            # Enhance logical coherence
            enhanced_report = self.content_processor.enhance_logical_flow(complete_report)
            
            # Validate report quality
            quality_result = self.quality_validator.validate_report_quality(enhanced_report)
            
            OutputFormatter.success(
                f"Structured report generation completed (quality score: {quality_result['overall_score']:.2f})"
            )
            
            return enhanced_report
            
        except Exception as e:
            OutputFormatter.error(f"Structured report generation failed: {e}")
            return f"Report generation failed: {str(e)}"
    
    def _build_report_sections(self, workflow_execution: Dict[str, Any], 
                             phase_outputs: Dict[str, Any], 
                             summary: Dict[str, Any]) -> Dict[str, str]:
        """Build report sections"""
        sections = {}
        
        # Executive summary
        sections["executive_summary"] = self._generate_executive_summary(workflow_execution, summary)
        
        # Organize content by phases
        phase_mapping = {
            "literature": "literature_review",
            "ideation": "innovation", 
            "analysis": "analysis",
            "synthesis": "synthesis",
            "review": "review",
            "polish": "polish"
        }
        
        for phase, section_id in phase_mapping.items():
            phase_content = self._extract_phase_content(phase_outputs, phase)
            if phase_content:
                sections[section_id] = phase_content
        
        # Conclusion and outlook
        sections["conclusion"] = self._generate_conclusion(workflow_execution, summary)
        
        return sections
    
    def _generate_executive_summary(self, workflow_execution: Dict[str, Any], 
                                  summary: Dict[str, Any]) -> str:
        """Generate executive summary"""
        topic = workflow_execution.get("topic", "Unknown Topic")
        success = workflow_execution.get("success", False)
        completed_phases = summary.get("phases_completed", 0)
        total_outputs = summary.get("total_outputs", 0)
        
        summary_text = f"""
**Research Topic**: {topic}

**Execution Status**: {'Successfully Completed' if success else 'Partially Completed'}

**Core Results**:
- Research phases completed: {completed_phases}
- Generated outputs: {total_outputs}
- Agents involved: {summary.get('agents_involved', 0)}

**Main Findings**: This research conducted comprehensive and in-depth analysis of "{topic}" through multi-agent collaboration, forming systematic research results from literature review, innovative thinking, multi-dimensional analysis to comprehensive evaluation.
        """.strip()
        
        return summary_text
    
    def _extract_phase_content(self, phase_outputs: Dict[str, Any], phase: str) -> str:
        """Extract phase content"""
        phase_content_parts = []
        
        for output_id, output_data in phase_outputs.items():
            if output_data.get("phase") == phase:
                content = output_data.get("content", "")
                agent_name = output_data.get("agent_name", "Unknown Agent")
                
                if content.strip():
                    # Add agent identification
                    formatted_content = f"### {agent_name} Contribution\n\n{content}\n"
                    phase_content_parts.append(formatted_content)
        
        return "\n".join(phase_content_parts) if phase_content_parts else "No content available for this phase."
    
    def _generate_conclusion(self, workflow_execution: Dict[str, Any], 
                           summary: Dict[str, Any]) -> str:
        """Generate conclusion and outlook"""
        topic = workflow_execution.get("topic", "Unknown Topic")
        success = workflow_execution.get("success", False)
        
        conclusion_text = f"""
## Conclusion and Outlook

This research conducted comprehensive and in-depth analysis of "{topic}" through multi-agent system collaboration.

**Main Results**:
- Completed {summary.get('phases_completed', 0)} research phases
- Generated {summary.get('total_outputs', 0)} research outputs
- Involved {summary.get('agents_involved', 0)} professional agents

**Future Directions**:
1. Further deepen theoretical research
2. Conduct experimental validation work
3. Explore cross-domain application possibilities

This research provides valuable reference and insights for the development of related fields.
        """.strip()
        
        return conclusion_text
    
    def _assemble_report(self, sections: Dict[str, str], 
                        workflow_execution: Dict[str, Any]) -> str:
        """Assemble complete report"""
        template = self.template_manager.template
        report_parts = []
        
        # Report title
        topic = workflow_execution.get("topic", "Scientific Hypothesis Generation")
        timestamp = datetime.now().strftime("%Y-%m-%d")
        
        report_parts.append(f"# {topic} - Research Report")
        report_parts.append(f"*Generated: {timestamp}*")
        report_parts.append("")
        
        # Add sections in template order
        for section_config in template["sections"]:
            section_id = section_config["id"]
            section_title = section_config["title"]
            
            if section_id in sections:
                report_parts.append(section_title)
                report_parts.append("")
                report_parts.append(sections[section_id])
                report_parts.append("")
        
        return "\n".join(report_parts)
    
    def generate_report_from_manager(self, output_manager) -> str:
        """Generate report from workflow output manager"""
        try:
            # Export workflow data
            if hasattr(output_manager, 'workflow_execution') and output_manager.workflow_execution:
                workflow_data = {
                    "workflow_execution": output_manager.workflow_execution.__dict__,
                    "phase_outputs": {k: v.__dict__ for k, v in output_manager.phase_outputs.items()},
                    "summary": output_manager.generate_workflow_summary()
                }
                
                return self.generate_structured_report(workflow_data)
            else:
                return "No available workflow data to generate report"
                
        except Exception as e:
            OutputFormatter.error(f"Failed to generate report from manager: {e}")
            return f"Report generation failed: {str(e)}"


# Test functionality
if __name__ == "__main__":
    print("=== Intelligent Report Generator Test ===")
    
    # Create generator instance
    generator = IntelligentReportGenerator()
    
    # Create mock workflow data
    mock_workflow_data = {
        "workflow_execution": {
            "topic": "Application of Artificial Intelligence in Medical Diagnosis",
            "success": True,
            "start_time": "2025-10-05T11:00:00",
            "end_time": "2025-10-05T12:00:00"
        },
        "phase_outputs": {
            "lit_001": {
                "phase": "literature",
                "agent_name": "Scholar Scour", 
                "content": "Current medical AI diagnostic technology has achieved breakthrough progress in multiple fields, especially in imaging diagnosis and pathological analysis.",
                "timestamp": "2025-10-05T11:10:00"
            },
            "idea_001": {
                "phase": "ideation",
                "agent_name": "Idea Igniter",
                "content": "Proposed intelligent diagnostic hypothesis based on multimodal fusion, combining imaging, genetic and clinical data.",
                "timestamp": "2025-10-05T11:20:00"
            }
        },
        "summary": {
            "total_outputs": 2,
            "phases_completed": 2,
            "agents_involved": 2,
            "success_rate": 1.0
        }
    }
    
    # Test report generation
    report = generator.generate_structured_report(mock_workflow_data)
    print(f"Generated report length: {len(report)} characters")
    
    # Test quality validation
    quality = generator.quality_validator.validate_report_quality(report)
    print(f"Report quality score: {quality['overall_score']:.2f}")
    
    OutputFormatter.success("Intelligent report generator test completed")
