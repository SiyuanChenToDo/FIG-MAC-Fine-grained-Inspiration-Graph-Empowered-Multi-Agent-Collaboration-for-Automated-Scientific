#!/usr/bin/env python3
"""
Simplified Result Processor
Based on CAMEL native message system, provides simplified result processing functionality for existing HypothesisTeam

This is an auxiliary processor for simplifying result extraction and formatting while maintaining all existing functionality
"""

import re
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

from camel.messages import BaseMessage
from camel.responses import ChatAgentResponse
from Myexamples.core.camel_logger_formatter import OutputFormatter

# Import existing result types to maintain compatibility
try:
    from Myexamples.agents.camel_native_agent import HypothesisTaskResult
except ImportError:
    OutputFormatter.warning("Cannot import HypothesisTaskResult, will use simplified version")
    from pydantic import BaseModel, Field
    
    class HypothesisTaskResult(BaseModel):
        """Simplified version of hypothesis generation task result format"""
        content: str = Field(description="Task execution result content")
        failed: bool = Field(default=False, description="Whether task failed")
        task_type: str = Field(default="unknown", description="Task type")
        metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata")


class SimpleResultProcessor:
    """
    Simplified Result Processor - based on CAMEL native message system
    
    Provides simple and effective result processing methods, supports:
    1. CAMEL native ChatAgentResponse processing
    2. BaseMessage content extraction
    3. Standardized result formatting
    4. Compatible with existing HypothesisTaskResult
    """
    
    @staticmethod
    def extract_content_from_response(response: ChatAgentResponse) -> str:
        """
        Use CAMEL native method to extract content from ChatAgentResponse
        
        Args:
            response: CAMEL native response object
            
        Returns:
            str: Extracted content
        """
        try:
            if response and response.msgs and len(response.msgs) > 0:
                # Get content of first message
                content = response.msgs[0].content
                return str(content) if content else ""
            else:
                OutputFormatter.warning("ChatAgentResponse is empty or has no messages")
                return ""
                
        except Exception as e:
            OutputFormatter.error(f"Failed to extract content from ChatAgentResponse: {e}")
            return ""
    
    @staticmethod
    def extract_content_from_message(message: BaseMessage) -> str:
        """
        Extract content from BaseMessage
        
        Args:
            message: CAMEL native message object
            
        Returns:
            str: Extracted content
        """
        try:
            if message and hasattr(message, 'content'):
                return str(message.content) if message.content else ""
            else:
                OutputFormatter.warning("BaseMessage is empty or has no content")
                return ""
                
        except Exception as e:
            OutputFormatter.error(f"Failed to extract content from BaseMessage: {e}")
            return ""
    
    @staticmethod
    def create_hypothesis_result(content: str, failed: bool = False, 
                               task_type: str = "unknown", 
                               metadata: Optional[Dict[str, Any]] = None) -> HypothesisTaskResult:
        """
        Create standardized hypothesis task result
        
        Args:
            content: Result content
            failed: Whether failed
            task_type: Task type
            metadata: Metadata
            
        Returns:
            HypothesisTaskResult: Standardized result object
        """
        try:
            return HypothesisTaskResult(
                content=content,
                failed=failed,
                task_type=task_type,
                metadata=metadata or {}
            )
        except Exception as e:
            OutputFormatter.error(f"Failed to create HypothesisTaskResult: {e}")
            # Return failure result
            return HypothesisTaskResult(
                content=f"Result creation failed: {str(e)}",
                failed=True,
                task_type="error",
                metadata={"error": str(e)}
            )
    
    @staticmethod
    def format_markdown_content(content: str, title: str = "Result") -> str:
        """
        Simple Markdown formatting
        
        Args:
            content: Raw content
            title: Title
            
        Returns:
            str: Formatted Markdown content
        """
        try:
            # Clean content
            cleaned_content = SimpleResultProcessor.clean_content(content)
            
            # Add title and timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            formatted = f"## {title}\n\n"
            formatted += f"*Generated: {timestamp}*\n\n"
            formatted += f"{cleaned_content}\n\n"
            
            return formatted
            
        except Exception as e:
            OutputFormatter.error(f"Markdown formatting failed: {e}")
            return f"## {title}\n\n{content}\n\n"
    
    @staticmethod
    def clean_content(content: str) -> str:
        """
        Clean and standardize content while preserving markdown structure.
        
        Args:
            content: Raw content
            
        Returns:
            str: Cleaned content
        """
        try:
            if not content:
                return ""
            
            # Remove control characters only (preserve whitespace structure)
            cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', content.strip())
            
            # Collapse 3+ consecutive newlines to 2 (preserve paragraph breaks)
            cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
            
            # Ensure content is not empty
            if not cleaned:
                return "Content is empty"
            
            return cleaned
            
        except Exception as e:
            OutputFormatter.error(f"Content cleaning failed: {e}")
            return str(content) if content else "Content processing failed"
    
    @staticmethod
    def extract_key_information(content: str, keys: List[str]) -> Dict[str, str]:
        """
        Extract key information from content
        
        Args:
            content: Content text
            keys: List of keywords to extract
            
        Returns:
            Dict[str, str]: Extracted key information
        """
        extracted = {}
        
        try:
            for key in keys:
                # Simple keyword matching
                pattern = rf"{key}[：:]\s*([^\n]*)"
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    extracted[key] = match.group(1).strip()
                else:
                    extracted[key] = ""
            
            return extracted
            
        except Exception as e:
            OutputFormatter.error(f"Key information extraction failed: {e}")
            return {key: "" for key in keys}
    
    @staticmethod
    def validate_content_quality(content: str, min_length: int = 50) -> Dict[str, Any]:
        """
        Validate content quality
        
        Args:
            content: Content text
            min_length: Minimum length requirement
            
        Returns:
            Dict[str, Any]: Quality validation result
        """
        try:
            validation = {
                "is_valid": True,
                "length": len(content),
                "issues": []
            }
            
            # Length check
            if len(content) < min_length:
                validation["is_valid"] = False
                validation["issues"].append(f"Content too short, less than {min_length} characters")
            
            # Empty content check
            if not content.strip():
                validation["is_valid"] = False
                validation["issues"].append("Content is empty")
            
            # Repetition check
            words = content.split()
            if len(words) > 10:
                unique_words = set(words)
                repetition_ratio = 1 - (len(unique_words) / len(words))
                if repetition_ratio > 0.7:
                    validation["is_valid"] = False
                    validation["issues"].append("Content repetition rate too high")
            
            return validation
            
        except Exception as e:
            OutputFormatter.error(f"Content quality validation failed: {e}")
            return {
                "is_valid": False,
                "length": 0,
                "issues": [f"Validation failed: {str(e)}"]
            }
    
    @staticmethod
    def merge_results(results: List[HypothesisTaskResult], 
                     merge_title: str = "Merged Results") -> HypothesisTaskResult:
        """
        Merge multiple results
        
        Args:
            results: List of results
            merge_title: Merge title
            
        Returns:
            HypothesisTaskResult: Merged result
        """
        try:
            if not results:
                return SimpleResultProcessor.create_hypothesis_result(
                    "No results to merge", 
                    failed=True, 
                    task_type="merge_error"
                )
            
            # Check for failed results
            failed_results = [r for r in results if r.failed]
            if failed_results:
                failed_content = "\n".join([f"- {r.content}" for r in failed_results])
                return SimpleResultProcessor.create_hypothesis_result(
                    f"Some results failed:\n{failed_content}",
                    failed=True,
                    task_type="partial_failure",
                    metadata={"failed_count": len(failed_results), "total_count": len(results)}
                )
            
            # Merge successful results
            merged_content = f"# {merge_title}\n\n"
            for i, result in enumerate(results, 1):
                merged_content += f"## Result {i}\n\n{result.content}\n\n"
            
            return SimpleResultProcessor.create_hypothesis_result(
                merged_content,
                failed=False,
                task_type="merged_results",
                metadata={"merged_count": len(results)}
            )
            
        except Exception as e:
            OutputFormatter.error(f"Result merge failed: {e}")
            return SimpleResultProcessor.create_hypothesis_result(
                f"Result merge failed: {str(e)}",
                failed=True,
                task_type="merge_error",
                metadata={"error": str(e)}
            )
    
    @staticmethod
    def get_processing_summary(results: Dict[str, HypothesisTaskResult]) -> Dict[str, Any]:
        """
        Get processing summary
        
        Args:
            results: Results dictionary
            
        Returns:
            Dict[str, Any]: Processing summary
        """
        try:
            summary = {
                "total_results": len(results),
                "successful_results": 0,
                "failed_results": 0,
                "total_content_length": 0,
                "result_types": {},
                "processing_time": datetime.now().isoformat()
            }
            
            for key, result in results.items():
                if result.failed:
                    summary["failed_results"] += 1
                else:
                    summary["successful_results"] += 1
                
                summary["total_content_length"] += len(result.content)
                
                task_type = getattr(result, 'task_type', 'unknown')
                summary["result_types"][task_type] = summary["result_types"].get(task_type, 0) + 1
            
            return summary
            
        except Exception as e:
            OutputFormatter.error(f"Processing summary generation failed: {e}")
            return {
                "total_results": 0,
                "error": str(e)
            }


# Compatibility functions to maintain compatibility with existing code
def extract_ai_content(response: Union[ChatAgentResponse, BaseMessage, str]) -> str:
    """
    Compatibility function: Extract AI content
    
    Args:
        response: Response object or string
        
    Returns:
        str: Extracted content
    """
    if isinstance(response, str):
        return response
    elif isinstance(response, ChatAgentResponse):
        return SimpleResultProcessor.extract_content_from_response(response)
    elif isinstance(response, BaseMessage):
        return SimpleResultProcessor.extract_content_from_message(response)
    else:
        OutputFormatter.warning(f"Unknown response type: {type(response)}")
        return str(response)


def create_standard_result(content: str, failed: bool = False, 
                         task_type: str = "unknown") -> HypothesisTaskResult:
    """
    Compatibility function: Create standard result
    
    Args:
        content: Content
        failed: Whether failed
        task_type: Task type
        
    Returns:
        HypothesisTaskResult: Standard result object
    """
    return SimpleResultProcessor.create_hypothesis_result(content, failed, task_type)


# Test functionality
if __name__ == "__main__":
    print("=== Simplified Result Processor Test ===")
    
    # Test content cleaning
    test_content = "  This is test content  \n\n  Contains extra whitespace  "
    cleaned = SimpleResultProcessor.clean_content(test_content)
    print(f"Content cleaning test: '{test_content}' -> '{cleaned}'")
    
    # Test Markdown formatting
    formatted = SimpleResultProcessor.format_markdown_content(cleaned, "Test Result")
    print(f"Markdown formatting test:\n{formatted}")
    
    # Test result creation
    result = SimpleResultProcessor.create_hypothesis_result(
        "Test content", 
        failed=False, 
        task_type="test"
    )
    print(f"Result creation test: {result}")
    
    # Test quality validation
    validation = SimpleResultProcessor.validate_content_quality(cleaned)
    print(f"Quality validation test: {validation}")
    
    OutputFormatter.success("Simplified Result Processor test completed")
