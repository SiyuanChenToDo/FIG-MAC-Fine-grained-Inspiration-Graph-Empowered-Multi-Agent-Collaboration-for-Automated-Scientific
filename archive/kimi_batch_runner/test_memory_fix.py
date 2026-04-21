#!/usr/bin/env python3
"""
测试并修复内存问题
"""

import os
import sys
import gc

# 设置环境变量
os.environ["OLLAMA_HOST"] = "http://127.0.0.1:11434"
os.environ["PYTHONUNBUFFERED"] = "1"

# 清理缓存
gc.collect()

PROJECT_ROOT = "/root/autodl-tmp"
sys.path.insert(0, PROJECT_ROOT)

print("=" * 70)
print("🔧 内存问题诊断与修复")
print("=" * 70)
print()

# 1. 检查系统内存
print("1. 检查系统内存...")
try:
    import psutil
    mem = psutil.virtual_memory()
    print(f"   总内存: {mem.total / (1024**3):.1f} GB")
    print(f"   可用内存: {mem.available / (1024**3):.1f} GB")
    print(f"   使用百分比: {mem.percent}%")
except Exception as e:
    print(f"   ⚠️ 无法获取内存信息: {e}")

print()

# 2. 检查 Ollama 状态
print("2. 检查 Ollama 状态...")
try:
    import requests
    response = requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
    if response.status_code == 200:
        models = response.json().get("models", [])
        print(f"   ✅ Ollama 运行中")
        print(f"   可用模型: {len(models)} 个")
        for m in models:
            size_gb = m.get('size', 0) / (1024**3)
            print(f"     - {m['name']} ({size_gb:.1f} GB)")
    else:
        print(f"   ❌ Ollama 响应异常: {response.status_code}")
except Exception as e:
    print(f"   ❌ 无法连接 Ollama: {e}")

print()

# 3. 尝试直接调用 Ollama API
print("3. 测试 Ollama API 调用...")
try:
    import requests
    
    # 简单的生成请求
    response = requests.post(
        "http://127.0.0.1:11434/api/generate",
        json={
            "model": "mixtral:8x7b",
            "prompt": "Hello, this is a test.",
            "stream": False,
            "options": {
                "num_ctx": 2048,
                "num_predict": 100
            }
        },
        timeout=60
    )
    
    if response.status_code == 200:
        result = response.json()
        print("   ✅ API 调用成功")
        print(f"   响应: {result.get('response', 'N/A')[:50]}...")
    else:
        print(f"   ❌ API 调用失败: {response.status_code}")
        print(f"   错误: {response.text[:200]}")
except Exception as e:
    print(f"   ❌ API 调用异常: {e}")

print()

# 4. 尝试使用 CAMEL
print("4. 测试 CAMEL + Ollama...")
try:
    # 清理 sys.path 避免冲突
    sys.path = [p for p in sys.path if 'autodl-tmp' not in p]
    sys.path.insert(0, PROJECT_ROOT)
    
    from camel.models import ModelFactory
    from camel.types import ModelPlatformType
    from camel.configs import OllamaConfig
    
    print("   创建模型实例...")
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OLLAMA,
        model_type="mixtral:8x7b",
        model_config_dict=OllamaConfig(
            temperature=0.7,
            num_ctx=2048
        ).as_dict()
    )
    
    print("   测试模型运行...")
    from camel.messages import BaseMessage
    
    msg = BaseMessage.make_user_message(
        role_name="User",
        content="Say 'Hello from CAMEL' in one sentence."
    )
    
    response = model.run([msg.to_openai_message()])
    
    if hasattr(response, 'choices') and response.choices:
        content = response.choices[0].message.content
        print(f"   ✅ CAMEL 调用成功")
        print(f"   响应: {content[:100]}...")
    else:
        print(f"   ⚠️  响应格式异常: {response}")
        
except Exception as e:
    print(f"   ❌ CAMEL 调用失败: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 70)
print("诊断完成！")
print("=" * 70)
