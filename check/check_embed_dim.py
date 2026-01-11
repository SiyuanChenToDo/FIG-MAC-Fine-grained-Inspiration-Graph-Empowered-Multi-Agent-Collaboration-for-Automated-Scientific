import os
from camel.embeddings import OpenAICompatibleEmbedding

# Set keys
# Hardcoded key as fallback from previous context
os.environ["QWEN_API_KEY"] = "sk-c1a6b588f7d543adb0412c5bc61bdd7b"
os.environ["QWEN_API_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"

try:
    embedder = OpenAICompatibleEmbedding(
        model_type="text-embedding-v2",
        api_key=os.environ["QWEN_API_KEY"],
        url=os.environ["QWEN_API_BASE_URL"]
    )
    
    vec = embedder.embed("test")
    print(f"Embedding Dimension: {len(vec)}")
except Exception as e:
    print(f"Error: {e}")

