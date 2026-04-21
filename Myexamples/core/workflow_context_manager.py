"""
Workflow Context Manager - Workflow-level Memory Management
Solve context truncation issues using CAMEL's memory system

This module provides a workflow-level context manager that:
1. Stores phase results as independent messages in ChatHistoryMemory
2. Utilizes ScoreBasedContextCreator for intelligent truncation
3. Automatically prioritizes latest messages via timestamp-based scoring
4. Dynamically adjusts token limits for different phases

Key Design:
- Independent from agent's internal memory
- Latest messages automatically get highest score (1.0)
- Older messages decay with keep_rate=0.9 (CAMEL default)
- No manual priority parameter needed
"""

import logging
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime

from camel.memories import ChatHistoryMemory, ScoreBasedContextCreator, MemoryRecord
from camel.messages import BaseMessage
from camel.types import OpenAIBackendRole, ModelType
from camel.utils import OpenAITokenCounter
from camel.types import UnifiedModelType


class WorkflowContextManager:
    """
    Workflow-level context manager using CAMEL's memory system
    
    This manager handles cross-phase context passing by:
    1. Storing each phase result as an independent MemoryRecord
    2. Using ScoreBasedContextCreator for intelligent truncation
    3. Leveraging timestamp-based score decay (latest=highest priority)
    4. Supporting dynamic token limit adjustment
    
    Unlike agent's internal memory, this is shared across the entire workflow.
    """
    
    def __init__(self, token_limit: int = 32768, model_type=None):
        """
        Initialize workflow context manager
        
        Args:
            token_limit: Maximum token limit for context (default: 32768)
            model_type: Model type for token counting (default: QWEN_MAX, can be string for custom models)
        """
        self.logger = logging.getLogger(f"{__name__}.WorkflowContextManager")
        
        # Handle string model types (for custom models like kimi-k2-5)
        if model_type is None:
            model_type = ModelType.QWEN_MAX
        elif isinstance(model_type, str):
            # Convert string to UnifiedModelType for OpenAITokenCounter
            model_type = UnifiedModelType(model_type)
        
        # Create token counter
        self._token_counter = OpenAITokenCounter(model_type)
        model_name = model_type.value if hasattr(model_type, 'value') else str(model_type)
        self.logger.info(f"Created token counter for {model_name}")
        
        # Create context creator with token limit
        self._context_creator = ScoreBasedContextCreator(
            token_counter=self._token_counter,
            token_limit=token_limit
        )
        self.logger.info(f"Created ScoreBasedContextCreator with token_limit={token_limit}")
        
        # Create workflow memory
        self._workflow_memory = ChatHistoryMemory(
            context_creator=self._context_creator
        )
        self.logger.info("Created ChatHistoryMemory for workflow-level context")
        
        # Track current token limit
        self._current_token_limit = token_limit
        
        # Track phase results for debugging
        self._phase_history: List[Dict[str, Any]] = []
        
        self.logger.info(f"WorkflowContextManager initialized (token_limit={token_limit})")
        
        # CRITICAL: Force update ScoreBasedContextCreator's token limit
        # Direct assignment to ensure it takes effect
        self._context_creator._token_limit = token_limit
        
        # DEBUG: Verify ScoreBasedContextCreator's token limit
        actual_limit = self._context_creator.token_limit
        if actual_limit != token_limit:
            self.logger.error(f"CRITICAL: Token limit mismatch! Expected {token_limit}, got {actual_limit}")
        else:
            self.logger.info(f"✅ Verified: ScoreBasedContextCreator token_limit = {actual_limit}")
    
    def add_phase_result(
        self, 
        phase_name: str, 
        content: str, 
        role_name: Optional[str] = None
    ) -> None:
        """
        Add phase result to workflow memory
        
        The latest added message automatically gets the highest score (1.0)
        due to CAMEL's timestamp-based score decay mechanism.
        
        Args:
            phase_name: Name of the phase (e.g., "literature", "ideation")
            content: Content of the phase result
            role_name: Optional agent role name (default: phase_name)
        """
        if not role_name:
            role_name = phase_name.replace("_", " ").title()
        
        # Create BaseMessage for this phase result
        message = BaseMessage(
            role_name=role_name,
            role_type=OpenAIBackendRole.ASSISTANT,
            meta_dict={
                "phase": phase_name,
                "timestamp": datetime.now().isoformat(),
                "content_length": len(content)
            },
            content=content
        )
        
        # ✅ 修正：将 BaseMessage 包装为 MemoryRecord
        # 参考：官方文档和 camel_memory_output_manager.py:152-159
        record = MemoryRecord(
            message=message,
            role_at_backend=OpenAIBackendRole.ASSISTANT
        )
        
        # Write to workflow memory
        # CAMEL's ChatHistoryMemory will automatically assign score=1.0 to latest message
        self._workflow_memory.write_records([record])
        
        # Track phase history for debugging
        self._phase_history.append({
            "phase": phase_name,
            "role": role_name,
            "content_length": len(content),
            "timestamp": datetime.now().isoformat()
        })
        
        self.logger.info(
            f"Added phase result: {phase_name} (role={role_name}, length={len(content)})"
        )
    
    def add_structured_context(self, context_items: List[Dict[str, str]]) -> None:
        """
        Add multiple context items in order
        
        Items added later get higher scores automatically due to timestamp.
        This is useful for REVISION phase where you want to prioritize
        review feedback over synthesis content.
        
        Args:
            context_items: List of dicts with keys: phase_name, content, role_name
        
        Example:
            context_items = [
                {"phase_name": "synthesis_summary", "content": summary, "role_name": "Dr. Qwen Leader"},
                {"phase_name": "review_feedback", "content": review, "role_name": "Critic Crucible"}
            ]
            # review_feedback gets score=1.0 (highest) as it's added last
        """
        for item in context_items:
            phase_name = item.get("phase_name", "unknown")
            content = item.get("content", "")
            role_name = item.get("role_name", phase_name.title())
            
            self.add_phase_result(phase_name, content, role_name)
        
        self.logger.info(f"Added {len(context_items)} structured context items in order")
    
    def get_context_as_string(self, for_phase: Optional[str] = None) -> Tuple[str, int]:
        """
        Get intelligently truncated context as a single string
        
        CAMEL's ScoreBasedContextCreator will:
        1. Keep system messages (none in our case)
        2. Delete low-score (old) messages first when over token_limit
        3. Preserve high-score (recent) messages
        4. Maintain temporal order in output
        
        Args:
            for_phase: Optional phase name for logging
        
        Returns:
            Tuple of (context_string, token_count)
        """
        try:
            # Get context from workflow memory
            # This returns List[OpenAIMessage] after intelligent truncation
            context_messages, token_count = self._workflow_memory.get_context()
            
            # Convert messages to string
            context_parts = []
            for msg in context_messages:
                # Extract content from OpenAIMessage
                content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
                if content:
                    context_parts.append(content)
            
            context_string = "\n\n".join(context_parts)
            
            self.logger.info(
                f"Retrieved context for phase '{for_phase}': "
                f"{len(context_messages)} messages, {token_count} tokens, "
                f"{len(context_string)} chars"
            )
            
            # Check if truncation occurred
            usage_percent = (token_count / self._current_token_limit) * 100
            if usage_percent > 95:
                self.logger.warning(
                    f"Token usage very high: {token_count}/{self._current_token_limit} "
                    f"({usage_percent:.1f}%)"
                )
            
            return context_string, token_count
            
        except Exception as e:
            self.logger.error(f"Failed to get context as string: {e}")
            return "", 0
    
    def get_context_messages(self) -> Tuple[List[Any], int]:
        """
        Get context as list of messages (for advanced use)
        
        Returns:
            Tuple of (message_list, token_count)
        """
        try:
            context_messages, token_count = self._workflow_memory.get_context()
            return context_messages, token_count
        except Exception as e:
            self.logger.error(f"Failed to get context messages: {e}")
            return [], 0
    
    def get_token_usage(self) -> Tuple[int, int]:
        """
        Get current token usage statistics
        
        Returns:
            Tuple of (current_token_count, token_limit)
        """
        try:
            _, token_count = self._workflow_memory.get_context()
            return token_count, self._current_token_limit
        except Exception as e:
            self.logger.error(f"Failed to get token usage: {e}")
            return 0, self._current_token_limit
    
    @property
    def token_limit(self) -> int:
        """
        Get current token limit.
        
        This property provides read access to the maximum token limit
        for the workflow context.
        
        Returns:
            int: Current token limit
            
        Example:
            >>> manager = WorkflowContextManager(token_limit=16384)
            >>> print(manager.token_limit)
            16384
        """
        return self._current_token_limit
    
    @property
    def effective_token_limit(self) -> int:
        """
        Get the effective token limit from ScoreBasedContextCreator.
        
        This is the actual limit used for truncation, which should match
        the configured token_limit.
        
        Returns:
            int: Effective token limit from context creator
        """
        return self._context_creator.token_limit
    
    @token_limit.setter
    def token_limit(self, value: int) -> None:
        """
        Set new token limit.
        
        Updates the maximum token limit for the workflow context.
        The new limit will be used for future context creation operations.
        
        Args:
            value: New token limit value (must be positive)
            
        Raises:
            ValueError: If value is not positive
            
        Example:
            >>> manager = WorkflowContextManager(token_limit=16384)
            >>> manager.token_limit = 32768
            >>> print(manager.token_limit)
            32768
        """
        if value <= 0:
            raise ValueError(f"Token limit must be positive, got {value}")
        
        old_limit = self._current_token_limit
        self._current_token_limit = value
        
        # CRITICAL: Also update the ScoreBasedContextCreator's token limit
        # This is necessary because the context creator is what actually performs truncation
        self._context_creator._token_limit = value
        
        self.logger.info(f"Token limit updated: {old_limit} -> {value} (including ScoreBasedContextCreator)")
    
    def get_phase_history(self) -> List[Dict[str, Any]]:
        """
        Get phase history for debugging
        
        Returns:
            List of phase information dicts
        """
        return self._phase_history.copy()
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive memory statistics
        
        Returns:
            Dict with memory statistics
        """
        token_count, token_limit = self.get_token_usage()
        usage_percent = (token_count / token_limit * 100) if token_limit > 0 else 0
        
        return {
            "token_count": token_count,
            "token_limit": token_limit,
            "usage_percent": usage_percent,
            "phase_count": len(self._phase_history),
            "phases": [p["phase"] for p in self._phase_history],
            "total_content_length": sum(p["content_length"] for p in self._phase_history)
        }
    
    def clear_memory(self) -> None:
        """
        Clear all workflow memory (for testing or reset)
        """
        self._workflow_memory.clear()
        self._phase_history.clear()
        self.logger.info("Workflow memory cleared")
    
    def __str__(self) -> str:
        """String representation of context manager state"""
        stats = self.get_memory_stats()
        return (
            f"WorkflowContextManager("
            f"phases={stats['phase_count']}, "
            f"tokens={stats['token_count']}/{stats['token_limit']}, "
            f"usage={stats['usage_percent']:.1f}%)"
        )
    
    def __repr__(self) -> str:
        """Detailed representation"""
        return self.__str__()


# Example usage (for testing)
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
    
    # Create manager
    manager = WorkflowContextManager(token_limit=8192)
    print(f"Created: {manager}")
    
    # Add some phase results
    manager.add_phase_result("literature", "This is literature review content " * 100, "Scholar Scour")
    manager.add_phase_result("ideation", "This is ideation content " * 100, "Idea Igniter")
    manager.add_phase_result("analysis", "This is analysis content " * 100, "Analysis Team")
    
    # Get context
    context, tokens = manager.get_context_as_string("test")
    print(f"\nContext: {len(context)} chars, {tokens} tokens")
    
    # Get stats
    stats = manager.get_memory_stats()
    print(f"\nStats: {stats}")
    
    # Test token limit adjustment
    manager.token_limit = 16384
    print(f"\nAfter adjustment: {manager}")
