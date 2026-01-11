"""Probe script to inspect CAMEL native agent token configuration."""

import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from camel.types import ModelType, OpenAIBackendRole
from camel.messages import BaseMessage

from agents.camel_native_agent import create_camel_native_agent


def main() -> None:
    agent = create_camel_native_agent(
        role_name="Probe Agent",
        system_prompt="You are a probe agent for token limit testing.",
        model_type=ModelType.QWEN_MAX,
        model_config={"max_tokens": 32768},
        memory_config={"window_size": 10, "token_limit": 32768},
    )

    full_context, total_tokens = agent.get_context_with_tokens()
    print(f"Initial context tokens: {total_tokens}")

    long_text = "Lorem ipsum dolor sit amet, " * 4000
    message = BaseMessage(
        role_name="Tester",
        role_type=OpenAIBackendRole.USER,
        meta_dict={},
        content=long_text,
    )
    agent.update_memory(message, OpenAIBackendRole.USER)

    _, tokens_after_update = agent.get_context_with_tokens()
    print(f"Context tokens after update: {tokens_after_update}")

    reply = agent.model_backend.run([message.to_openai_message(OpenAIBackendRole.USER)])
    print(f"Model backend type: {type(reply)}")


if __name__ == "__main__":
    main()
