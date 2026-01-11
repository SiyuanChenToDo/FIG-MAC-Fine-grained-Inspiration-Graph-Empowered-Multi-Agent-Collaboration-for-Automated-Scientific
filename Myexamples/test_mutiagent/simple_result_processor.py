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
from Myexamples.test_mutiagent.camel_logger_formatter import OutputFormatter

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
        Clean and standardize content
        
        Args:
            content: Raw content
            
        Returns:
            str: Cleaned content
        """
        try:
            if not content:
                return ""
            
            # Remove excess whitespace characters
            cleaned = re.sub(r'\s+', ' ', content.strip())
            
            # Remove special characters and control characters
            cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', cleaned)
            
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
        从内容中提取关键信息
        
        Args:
            content: 内容文本
            keys: 要提取的关键词列表
            
        Returns:
            Dict[str, str]: 提取的关键信息
        """
        extracted = {}
        
        try:
            for key in keys:
                # 简单的关键词匹配
                pattern = rf"{key}[：:]\s*([^\n]*)"
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    extracted[key] = match.group(1).strip()
                else:
                    extracted[key] = ""
            
            return extracted
            
        except Exception as e:
            OutputFormatter.error(f"关键信息提取失败: {e}")
            return {key: "" for key in keys}
    
    @staticmethod
    def validate_content_quality(content: str, min_length: int = 50) -> Dict[str, Any]:
        """
        验证内容质量
        
        Args:
            content: 内容文本
            min_length: 最小长度要求
            
        Returns:
            Dict[str, Any]: 质量验证结果
        """
        try:
            validation = {
                "is_valid": True,
                "length": len(content),
                "issues": []
            }
            
            # 长度检查
            if len(content) < min_length:
                validation["is_valid"] = False
                validation["issues"].append(f"内容过短，少于{min_length}字符")
            
            # 空内容检查
            if not content.strip():
                validation["is_valid"] = False
                validation["issues"].append("内容为空")
            
            # 重复内容检查
            words = content.split()
            if len(words) > 10:
                unique_words = set(words)
                repetition_ratio = 1 - (len(unique_words) / len(words))
                if repetition_ratio > 0.7:
                    validation["is_valid"] = False
                    validation["issues"].append("内容重复率过高")
            
            return validation
            
        except Exception as e:
            OutputFormatter.error(f"内容质量验证失败: {e}")
            return {
                "is_valid": False,
                "length": 0,
                "issues": [f"验证失败: {str(e)}"]
            }
    
    @staticmethod
    def merge_results(results: List[HypothesisTaskResult], 
                     merge_title: str = "合并结果") -> HypothesisTaskResult:
        """
        合并多个结果
        
        Args:
            results: 结果列表
            merge_title: 合并标题
            
        Returns:
            HypothesisTaskResult: 合并后的结果
        """
        try:
            if not results:
                return SimpleResultProcessor.create_hypothesis_result(
                    "无结果可合并", 
                    failed=True, 
                    task_type="merge_error"
                )
            
            # 检查是否有失败的结果
            failed_results = [r for r in results if r.failed]
            if failed_results:
                failed_content = "\n".join([f"- {r.content}" for r in failed_results])
                return SimpleResultProcessor.create_hypothesis_result(
                    f"部分结果失败:\n{failed_content}",
                    failed=True,
                    task_type="partial_failure",
                    metadata={"failed_count": len(failed_results), "total_count": len(results)}
                )
            
            # 合并成功的结果
            merged_content = f"# {merge_title}\n\n"
            for i, result in enumerate(results, 1):
                merged_content += f"## 结果 {i}\n\n{result.content}\n\n"
            
            return SimpleResultProcessor.create_hypothesis_result(
                merged_content,
                failed=False,
                task_type="merged_results",
                metadata={"merged_count": len(results)}
            )
            
        except Exception as e:
            OutputFormatter.error(f"结果合并失败: {e}")
            return SimpleResultProcessor.create_hypothesis_result(
                f"结果合并失败: {str(e)}",
                failed=True,
                task_type="merge_error",
                metadata={"error": str(e)}
            )
    
    @staticmethod
    def get_processing_summary(results: Dict[str, HypothesisTaskResult]) -> Dict[str, Any]:
        """
        获取处理摘要
        
        Args:
            results: 结果字典
            
        Returns:
            Dict[str, Any]: 处理摘要
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
            OutputFormatter.error(f"处理摘要生成失败: {e}")
            return {
                "total_results": 0,
                "error": str(e)
            }


# 兼容性函数，保持与现有代码的兼容
def extract_ai_content(response: Union[ChatAgentResponse, BaseMessage, str]) -> str:
    """
    兼容性函数：提取AI内容
    
    Args:
        response: 响应对象或字符串
        
    Returns:
        str: 提取的内容
    """
    if isinstance(response, str):
        return response
    elif isinstance(response, ChatAgentResponse):
        return SimpleResultProcessor.extract_content_from_response(response)
    elif isinstance(response, BaseMessage):
        return SimpleResultProcessor.extract_content_from_message(response)
    else:
        OutputFormatter.warning(f"未知响应类型: {type(response)}")
        return str(response)


def create_standard_result(content: str, failed: bool = False, 
                         task_type: str = "unknown") -> HypothesisTaskResult:
    """
    兼容性函数：创建标准结果
    
    Args:
        content: 内容
        failed: 是否失败
        task_type: 任务类型
        
    Returns:
        HypothesisTaskResult: 标准结果对象
    """
    return SimpleResultProcessor.create_hypothesis_result(content, failed, task_type)


# 测试功能
if __name__ == "__main__":
    print("=== 简化结果处理器测试 ===")
    
    # 测试内容清理
    test_content = "  这是一个测试内容  \n\n  包含多余空白  "
    cleaned = SimpleResultProcessor.clean_content(test_content)
    print(f"内容清理测试: '{test_content}' -> '{cleaned}'")
    
    # 测试Markdown格式化
    formatted = SimpleResultProcessor.format_markdown_content(cleaned, "测试结果")
    print(f"Markdown格式化测试:\n{formatted}")
    
    # 测试结果创建
    result = SimpleResultProcessor.create_hypothesis_result(
        "测试内容", 
        failed=False, 
        task_type="test"
    )
    print(f"结果创建测试: {result}")
    
    # 测试质量验证
    validation = SimpleResultProcessor.validate_content_quality(cleaned)
    print(f"质量验证测试: {validation}")
    
    OutputFormatter.success("简化结果处理器测试完成")
