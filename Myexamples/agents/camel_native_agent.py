#!/usr/bin/env python3
"""
CAMEL Native Agent Implementation
Based on FIG-MAC SciAgent_Async pattern, fully adopts CAMEL framework native mechanisms
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from camel.agents import BaseAgent
from camel.messages import BaseMessage
from camel.models import BaseModelBackend, ModelFactory
from camel.types import ModelPlatformType, ModelType, OpenAIBackendRole, UnifiedModelType
from camel.responses import ChatAgentResponse
from camel.memories import ChatHistoryMemory, MemoryRecord, ScoreBasedContextCreator
from camel.configs import QwenConfig, ZhipuAIConfig


class HypothesisTaskResult(BaseModel):
    """Standardized hypothesis generation task result format"""
    content: str = Field(description="Task execution result content")
    failed: bool = Field(default=False, description="Whether task failed")
    task_type: str = Field(default="hypothesis_generation", description="Task type")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class CamelNativeAgent(BaseAgent):
    """
    Agent based on CAMEL native mechanisms
    References FIG-MAC SciAgent_Async design pattern
    """
    
    def __init__(
        self,
        role_name: str,
        model_type: ModelType = ModelType.QWEN_PLUS,
        model_config: Optional[Dict[str, Any]] = None,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Any]] = None,
        memory_config: Optional[Dict[str, Any]] = None,
        model_platform: Optional[ModelPlatformType] = None,
    ):
        """
        Initialize CAMEL native agent
        
        Args:
            role_name: Agent role name
            model_type: Model type (can be ModelType enum or string for custom models)
            model_config: Model configuration
            system_prompt: System prompt
            tools: Tool list
            memory_config: Memory configuration
            model_platform: Model platform (default: QWEN, can be MOONSHOT for Kimi)
        """
        # Use CAMEL standard QwenConfig configuration (reference FIG-MAC best practices)
        model_config = model_config or {}
        
        # Detect platform and model type
        platform = model_platform or ModelPlatformType.QWEN
        
        # Handle string model types (for custom models like kimi-k2-5 or glm-5)
        if isinstance(model_type, str):
            model_type_str = model_type
            # For Kimi models, use OpenAI compatibility mode
            if "kimi" in model_type_str.lower():
                platform = ModelPlatformType.OPENAI_COMPATIBLE_MODEL
            # For GLM-5 models, use ZhipuAI platform
            elif "glm-5" in model_type_str.lower():
                platform = ModelPlatformType.ZHIPU
        else:
            model_type_str = model_type.value if hasattr(model_type, 'value') else str(model_type)
        
        # Create configuration based on platform type
        if platform == ModelPlatformType.ZHIPU or (isinstance(model_type, str) and "glm-5" in model_type_str.lower()):
            # Use ZhipuAIConfig for GLM-5
            config = ZhipuAIConfig(
                temperature=model_config.get("temperature", 0.7),
                max_tokens=model_config.get("max_tokens", 8192),
                top_p=model_config.get("top_p", None),
                stream=model_config.get("stream", None),
                stop=model_config.get("stop", None),
                thinking=model_config.get("thinking", None),
            )
        else:
            # Create CAMEL standard Qwen configuration
            # 注意：Qwen API max_tokens 上限为 8192
            config = QwenConfig(
                temperature=model_config.get("temperature", 0.7),
                max_tokens=min(model_config.get("max_tokens", 8192), 8192),  # 确保不超过 8192
                top_p=model_config.get("top_p", None),
                presence_penalty=model_config.get("presence_penalty", None),
                stream=model_config.get("stream", None),
                seed=model_config.get("seed", None),
                stop=model_config.get("stop", None),
                response_format=model_config.get("response_format", None),
                extra_body=model_config.get("extra_body", None)
            )
        
        try:
            # Get timeout from environment variable or use default (1200s = 20min for complex tasks)
            import os
            default_timeout = float(os.environ.get("CAMEL_MODEL_TIMEOUT", 1200.0))
            
            self.model_backend: BaseModelBackend = ModelFactory.create(
                model_platform=platform,
                model_type=model_type_str,
                model_config_dict=config.as_dict(),
                # Pass retry and timeout parameters to constructor rather than model_config_dict
                max_retries=model_config.get("max_retries", 3),
                timeout=model_config.get("timeout", default_timeout)
            )
            print(f"✅ Model backend created successfully: {model_type_str} on {platform.value}")
        except Exception as e:
            # Throw exception when model creation fails, do not use mock backend
            print(f"❌ Model creation failed: {e}")
            raise RuntimeError(f"Failed to create model backend: {e}. Please check your API keys and model configuration.")
        
        # Set role management (FIG-MAC mode)
        self.role_type = OpenAIBackendRole.ASSISTANT
        
        # Store configuration information (BaseAgent is abstract class, no need to call super().__init__)
        self.role_name = role_name
        self.system_prompt = system_prompt
        self.tools = tools or []
        
        # For Workforce compatibility, add system_message and model attributes
        self.system_message = BaseMessage(
            role_name=role_name,
            role_type=self.role_type,
            meta_dict={},
            content=system_prompt or ""
        )
        self.model = self.model_backend  # model attribute expected by Workforce
        self.memory = None  # memory attribute expected by Workforce, temporarily set to None
        
        # Initialize CAMEL native memory system (based on FIG-MAC mode)
        memory_config = memory_config or {}
        if self.model_backend:
            # Create token counter (FIG-MAC reference)
            from camel.utils import OpenAITokenCounter
            # Convert string model_type to UnifiedModelType if needed
            if isinstance(model_type, str):
                token_counter_model = UnifiedModelType(model_type)
            else:
                token_counter_model = model_type
            token_counter = OpenAITokenCounter(token_counter_model)
            
            # Create context creator (FIG-MAC reference)
            self.context_creator: ScoreBasedContextCreator = ScoreBasedContextCreator(
                token_counter=token_counter,
                token_limit=memory_config.get('token_limit', 8192)
            )
            
            # Dual memory architecture (FIG-MAC mode) - use correct CAMEL API parameters
            self.personality_memory: ChatHistoryMemory = ChatHistoryMemory(
                context_creator=self.context_creator
            )
            
            self.memory: ChatHistoryMemory = ChatHistoryMemory(
                context_creator=self.context_creator
            )
            
            # Maintain backward compatibility
            self.chat_history = self.memory
        else:
            self.context_creator = None
            self.personality_memory = None
            self.memory = None
            self.chat_history = None
    
    def reset(self, *args: Any, **kwargs: Any) -> None:
        """
        Reset agent to initial state (BaseAgent abstract method)
        """
        self.clear_memory()
        # Can add other reset logic
    
    def step(
        self, 
        input_message: Union[str, BaseMessage],
        **kwargs
    ) -> ChatAgentResponse:
        """
        Synchronous execution step (BaseAgent abstract method)
        """
        # Real AI model execution implementation
        if isinstance(input_message, str):
            message = BaseMessage(
                role_name=self.role_name,
                role_type=self.role_type,
                meta_dict={},
                content=input_message
            )
        else:
            message = input_message
        
        # Call real model backend for AI generation
        if not self.model_backend:
            raise RuntimeError("Model backend not initialized. Cannot perform real AI generation.")
        
        try:
            # Convert BaseMessage to OpenAI message format for model backend
            openai_message = message.to_openai_message(OpenAIBackendRole.USER)
            
            # Use CAMEL native model backend for real AI generation
            response = self.model_backend.run([openai_message])
            
            # Extract response content from CAMEL ModelResponse or ChatCompletion
            if hasattr(response, 'choices') and response.choices:
                # Handle ChatCompletion object (from Qwen/OpenAI API)
                response_content = response.choices[0].message.content
            elif hasattr(response, 'output_messages') and response.output_messages:
                # Get the first output message content
                response_content = response.output_messages[0].content
            elif hasattr(response, 'content'):
                response_content = response.content
            elif hasattr(response, 'text'):
                response_content = response.text
            elif isinstance(response, str):
                response_content = response
            else:
                response_content = str(response)
            
            response_message = BaseMessage(
                role_name=self.role_name,
                role_type=OpenAIBackendRole.ASSISTANT,
                meta_dict={"real_ai_generation": True},
                content=response_content
            )
            
            return ChatAgentResponse(
                msgs=[response_message],
                terminated=False,
                info={"status": "success", "real_ai": True, "model_type": str(self.model_backend)}
            )
            
        except Exception as e:
            print(f"❌ Real AI generation failed: {e}")
            raise RuntimeError(f"AI model execution failed: {e}")
    
    async def step_async(
        self, 
        input_message: Union[str, BaseMessage],
        **kwargs
    ) -> ChatAgentResponse:
        """
        Asynchronous execution step (FIG-MAC mode)
        
        Args:
            input_message: Input message
            **kwargs: Additional parameters
            
        Returns:
            ChatAgentResponse: CAMEL native response object
        """
        # Convert input to CAMEL message format
        if isinstance(input_message, str):
            message = BaseMessage(
                role_name=self.role_name,
                role_type=self.role_type,
                meta_dict={},
                content=input_message
            )
        elif isinstance(input_message, BaseMessage):
            message = input_message
        else:
            # Handle other types of input
            message = BaseMessage(
                role_name=self.role_name,
                role_type=self.role_type,
                meta_dict={},
                content=str(input_message)
            )
        
        # Add to chat history
        if self.chat_history:
            self.chat_history.write_record(
                MemoryRecord(
                    message=message,
                    role_at_backend=self.role_type
                )
            )
        
        # Convert BaseMessage to OpenAI message format for model backend
        openai_message = message.to_openai_message(OpenAIBackendRole.USER)
        
        # Use real async AI generation
        import asyncio
        if asyncio.iscoroutinefunction(self.model_backend.run):
            # If model backend supports async
            try:
                response_data = await self.model_backend.run([openai_message])
            except Exception as e:
                print(f"❌ Async AI generation failed: {e}")
                raise RuntimeError(f"Async AI model execution failed: {e}")
        else:
            # Fallback to sync execution in async context
            try:
                response_data = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: self.model_backend.run([openai_message])
                )
            except Exception as e:
                print(f"❌ Sync-in-async AI generation failed: {e}")
                raise RuntimeError(f"AI model execution failed: {e}")
        
        # Process response from CAMEL ModelResponse or ChatCompletion
        if hasattr(response_data, 'choices') and response_data.choices:
            # Handle ChatCompletion object (from Qwen/OpenAI API)
            response_content = response_data.choices[0].message.content
        elif hasattr(response_data, 'output_messages') and response_data.output_messages:
            # Get the first output message content
            response_content = response_data.output_messages[0].content
        elif hasattr(response_data, 'content'):
            response_content = response_data.content
        elif hasattr(response_data, 'text'):
            response_content = response_data.text
        elif isinstance(response_data, str):
            response_content = response_data
        else:
            response_content = str(response_data)
        
        response_message = BaseMessage(
            role_name=self.role_name,
            role_type=OpenAIBackendRole.ASSISTANT,
            meta_dict={"real_ai_generation": True, "async_execution": True},
            content=response_content
        )
        
        response = ChatAgentResponse(
            msgs=[response_message],
            terminated=False,
            info={"status": "success", "real_ai": True, "async": True}
        )
        
        # Record response to history
        if response.msgs and self.chat_history:
            self.chat_history.write_record(
                MemoryRecord(
                    message=response.msgs[-1],
                    role_at_backend=OpenAIBackendRole.ASSISTANT
                )
            )
        
        return response
    
    def process_task_with_structured_output(
        self, 
        task_content: str,
        response_format: type = HypothesisTaskResult,
        **kwargs
    ) -> HypothesisTaskResult:
        """
        Use CAMEL native structured output to handle tasks
        
        Args:
            task_content: Task content
            response_format: Response format (Pydantic model)
            **kwargs: Additional parameters
            
        Returns:
            HypothesisTaskResult: Structured task result
        """
        try:
            # Use CAMEL's structured output mechanism
            # Should integrate FunctionCallingMessage and other mechanisms here
            # Temporarily use simplified version, can be extended later
            
            message = BaseMessage(
                role_name=self.role_name,
                role_type=self.role_type,
                meta_dict={},
                content=task_content
            )
            
            # Synchronous call (can be changed to asynchronous)
            response = self.step(message)
            
            if response.msgs:
                content = response.msgs[-1].content
                return HypothesisTaskResult(
                    content=content,
                    failed=False,
                    metadata={"response_info": response.info}
                )
            else:
                return HypothesisTaskResult(
                    content="No response generated",
                    failed=True,
                    metadata={"error": "Empty response"}
                )
                
        except Exception as e:
            return HypothesisTaskResult(
                content=f"Task execution failed: {str(e)}",
                failed=True,
                metadata={"error": str(e)}
            )
    
    def get_memory_summary(self) -> str:
        """Get memory summary"""
        if not self.chat_history:
            return "No chat history available (model backend not initialized)"
            
        records = self.chat_history.get_records()
        if not records:
            return "No conversation history"
        
        # Use context creator to generate summary
        if self.context_creator:
            context = self.context_creator.create_context(records)
            return f"Conversation summary: {len(records)} messages, latest context: {context[:200]}..."
        else:
            return f"Conversation summary: {len(records)} messages (no context creator available)"
    
    def update_memory(self, message: BaseMessage, role: OpenAIBackendRole) -> None:
        """
        FIG-MAC mode memory update (synchronous method)
        Based on investigation report's correct API usage
        """
        if not self.memory or not self.personality_memory:
            return
        
        try:
            # Import MemoryRecord (FIG-MAC reference)
            from camel.memories import MemoryRecord
            
            # Create memory record
            record = MemoryRecord(
                message=message,
                role_at_backend=role
            )
            
            # Dual memory architecture separate management (FIG-MAC mode)
            if role == OpenAIBackendRole.SYSTEM:
                self.personality_memory.write_record(record)
            else:
                self.memory.write_record(record)
                
        except Exception as e:
            print(f"[WARNING] Failed to update memory for {self.role_name}: {e}")
    
    def get_context_with_tokens(self) -> tuple:
        """
        Get CAMEL native intelligent context (FIG-MAC mode)
        Returns: (complete context message list, total token count)
        """
        if not self.memory or not self.personality_memory:
            return [], 0
            
        try:
            # Suppress EmptyMemoryWarning for initial empty state
            import warnings
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=UserWarning, message=".*ChatHistoryMemory.*empty.*")
                
                # Get CAMEL native intelligent context
                openai_messages, token_count = self.memory.get_context()
                personality_info, info_tokens = self.personality_memory.get_context()
            
            # FIG-MAC mode dynamic context combination
            full_context = personality_info + openai_messages
            total_tokens = token_count + info_tokens
            
            return full_context, total_tokens
            
        except Exception as e:
            print(f"[WARNING] Failed to get context for {self.role_name}: {e}")
            return [], 0

    def clear_memory(self) -> None:
        """Clear memory (FIG-MAC mode)"""
        if self.memory:
            self.memory.clear()
        if self.personality_memory:
            self.personality_memory.clear()
        print(f"[INFO] Memory cleared for {self.role_name}")


def create_camel_native_agent(
    role_name: str,
    system_prompt: str = "",
    model_type: ModelType = ModelType.QWEN_TURBO,
    **kwargs
) -> CamelNativeAgent:
    """
    Factory function to create CAMEL native agent
    
    Args:
        role_name: Role name
        system_prompt: System prompt
        model_type: Model type
        **kwargs: Other configuration parameters
        
    Returns:
        CamelNativeAgent: Configured agent instance
    """
    return CamelNativeAgent(
        role_name=role_name,
        model_type=model_type,
        system_prompt=system_prompt,
        **kwargs
    )
