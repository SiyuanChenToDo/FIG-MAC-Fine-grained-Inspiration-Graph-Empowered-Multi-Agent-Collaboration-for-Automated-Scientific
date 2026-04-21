#!/usr/bin/env python3
"""
测试 Kimi API 配置
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# 设置 Kimi API
KIMI_API_KEY = "ae12cedbcaa64d2892dae304a0232869.b0DLvSt3dEF1SlW4"
KIMI_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

os.environ["MOONSHOT_API_KEY"] = KIMI_API_KEY
os.environ["OPENAI_API_KEY"] = KIMI_API_KEY
os.environ["OPENAI_COMPATIBILITY_API_KEY"] = KIMI_API_KEY
os.environ["MOONSHOT_API_BASE_URL"] = KIMI_BASE_URL
os.environ["OPENAI_API_BASE_URL"] = KIMI_BASE_URL
os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"] = KIMI_BASE_URL

print("="*60)
print("Kimi API 配置测试")
print("="*60)
print(f"API Key: {KIMI_API_KEY[:15]}...{KIMI_API_KEY[-4:]}")
print(f"Base URL: {KIMI_BASE_URL}")
print()

# 测试导入
try:
    from camel.types import ModelType
    print("✓ camel.types 导入成功")
    print(f"  - MOONSHOT_KIMI_K2: {ModelType.MOONSHOT_KIMI_K2.value}")
except Exception as e:
    print(f"✗ camel.types 导入失败: {e}")
    sys.exit(1)

# 使用 OpenAI 兼容客户端测试
try:
    from openai import OpenAI
    
    print("\n✓ openai 导入成功")
    
    # 创建客户端
    client = OpenAI(
        api_key=KIMI_API_KEY,
        base_url=KIMI_BASE_URL,
    )
    print("✓ OpenAI 客户端创建成功")
    
    # 测试简单调用
    print("\n发送测试消息...")
    response = client.chat.completions.create(
        model="kimi-k2-5",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, please reply with 'Kimi API test successful' in Chinese."}
        ],
        max_tokens=100,
    )
    
    print(f"\n✓ API 调用成功!")
    print(f"响应: {response.choices[0].message.content}")
    print(f"模型: {response.model}")
    print(f"Tokens: {response.usage.total_tokens} (input: {response.usage.prompt_tokens}, output: {response.usage.completion_tokens})")
    
except Exception as e:
    print(f"\n✗ 测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*60)
print("Kimi API 配置测试通过!")
print("可以开始批量运行 FIG-MAC")
print("="*60)
