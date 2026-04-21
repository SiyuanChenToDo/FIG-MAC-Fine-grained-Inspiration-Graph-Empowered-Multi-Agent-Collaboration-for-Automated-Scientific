#!/usr/bin/env python3
"""
Ollama 本地模型配置
支持 Llama、Qwen、Mistral 等开源模型本地运行
"""

import os
import subprocess
import json

# Ollama 默认地址
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

# 推荐的本地模型配置
# 模型越大越强大，但需要更多内存和显存
OLLAMA_MODELS = {
    "llama3.1:8b": {
        "name": "Llama 3.1 8B",
        "description": "Meta 开源模型，速度快，质量良好，适合大多数任务",
        "size": "约 4.7GB",
        "memory_required": "8GB+ RAM",
        "pull_command": "ollama pull llama3.1:8b",
        "model_type": "llama3.1:8b"
    },
    "llama3.1:70b": {
        "name": "Llama 3.1 70B",
        "description": "最强大的 Llama 3.1 模型，质量极佳但速度慢",
        "size": "约 40GB",
        "memory_required": "64GB+ RAM",
        "pull_command": "ollama pull llama3.1:70b",
        "model_type": "llama3.1:70b"
    },
    "qwen2.5:14b": {
        "name": "Qwen 2.5 14B",
        "description": "阿里巴巴开源模型，中文支持优秀",
        "size": "约 9GB",
        "memory_required": "16GB+ RAM",
        "pull_command": "ollama pull qwen2.5:14b",
        "model_type": "qwen2.5:14b"
    },
    "qwen2.5:32b": {
        "name": "Qwen 2.5 32B",
        "description": "更强的 Qwen 模型，适合复杂任务",
        "size": "约 20GB",
        "memory_required": "32GB+ RAM",
        "pull_command": "ollama pull qwen2.5:32b",
        "model_type": "qwen2.5:32b"
    },
    "mistral:7b": {
        "name": "Mistral 7B",
        "description": "法国 Mistral AI 开源模型，速度快",
        "size": "约 4.1GB",
        "memory_required": "8GB+ RAM",
        "pull_command": "ollama pull mistral:7b",
        "model_type": "mistral:7b"
    },
    "mixtral:8x7b": {
        "name": "Mixtral 8x7B",
        "description": "Mistral 的 MoE 模型，性能强大",
        "size": "约 26GB",
        "memory_required": "32GB+ RAM",
        "pull_command": "ollama pull mixtral:8x7b",
        "model_type": "mixtral:8x7b"
    },
    "deepseek-coder:33b": {
        "name": "DeepSeek Coder 33B",
        "description": "专为代码生成优化的模型",
        "size": "约 18GB",
        "memory_required": "24GB+ RAM",
        "pull_command": "ollama pull deepseek-coder:33b",
        "model_type": "deepseek-coder:33b"
    },
    "phi4": {
        "name": "Phi-4",
        "description": "Microsoft 开源模型，小巧但强大",
        "size": "约 9GB",
        "memory_required": "16GB+ RAM",
        "pull_command": "ollama pull phi4",
        "model_type": "phi4"
    },
    "gemma2:27b": {
        "name": "Gemma 2 27B",
        "description": "Google 开源模型，性能优秀",
        "size": "约 16GB",
        "memory_required": "24GB+ RAM",
        "pull_command": "ollama pull gemma2:27b",
        "model_type": "gemma2:27b"
    }
}


def check_ollama_status():
    """检查 Ollama 服务状态"""
    try:
        import requests
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            return True, models
        return False, []
    except Exception as e:
        return False, str(e)


def list_local_models():
    """列出本地已安装的模型"""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return result.stdout
        return f"Error: {result.stderr}"
    except Exception as e:
        return f"Error: {e}"


def pull_model(model_name: str):
    """拉取模型"""
    print(f"正在拉取模型: {model_name}")
    print(f"命令: ollama pull {model_name}")
    print("这可能需要几分钟到几十分钟，取决于模型大小和网络速度...")
    print()
    
    try:
        # 使用 subprocess 实时显示输出
        process = subprocess.Popen(
            ["ollama", "pull", model_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        for line in process.stdout:
            print(line, end='')
        
        process.wait()
        if process.returncode == 0:
            print(f"\n✅ 模型 {model_name} 拉取成功！")
            return True
        else:
            print(f"\n❌ 模型 {model_name} 拉取失败")
            return False
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        return False


def get_recommended_model():
    """根据系统资源推荐模型"""
    import psutil
    
    memory = psutil.virtual_memory()
    memory_gb = memory.total / (1024**3)
    
    print(f"系统内存: {memory_gb:.1f} GB")
    print()
    
    if memory_gb >= 64:
        return "llama3.1:70b", "您的内存充足，可以使用最强大的 Llama 3.1 70B 模型"
    elif memory_gb >= 32:
        return "qwen2.5:32b", "推荐使用 Qwen 2.5 32B 或 Mixtral 8x7B"
    elif memory_gb >= 16:
        return "qwen2.5:14b", "推荐使用 Qwen 2.5 14B 或 Llama 3.1 8B"
    else:
        return "llama3.1:8b", "内存有限，建议使用 Llama 3.1 8B 或 Mistral 7B"


def main():
    """主函数"""
    print("=" * 60)
    print("Ollama 本地模型配置工具")
    print("=" * 60)
    print()
    
    # 检查 Ollama 服务
    print("检查 Ollama 服务状态...")
    is_running, models = check_ollama_status()
    
    if is_running:
        print("✅ Ollama 服务正在运行")
        print(f"   地址: {OLLAMA_HOST}")
        print(f"   已安装模型数: {len(models)}")
        
        if models:
            print("\n已安装模型:")
            for model in models:
                print(f"  - {model.get('name', 'Unknown')}")
    else:
        print("❌ Ollama 服务未运行")
        print("正在尝试启动...")
        os.system("nohup ollama serve > /tmp/ollama.log 2>&1 &")
        import time
        time.sleep(3)
        
        is_running, models = check_ollama_status()
        if is_running:
            print("✅ Ollama 服务已启动")
        else:
            print("❌ 启动失败，请手动运行: ollama serve")
            return
    
    print()
    print("=" * 60)
    print("模型推荐")
    print("=" * 60)
    
    recommended_model, reason = get_recommended_model()
    print(f"\n根据您的系统配置：{reason}")
    print(f"推荐模型: {recommended_model}")
    
    if recommended_model in OLLAMA_MODELS:
        info = OLLAMA_MODELS[recommended_model]
        print(f"模型名称: {info['name']}")
        print(f"模型大小: {info['size']}")
        print(f"内存需求: {info['memory_required']}")
        print(f"模型描述: {info['description']}")
    
    print()
    print("=" * 60)
    print("可用模型列表")
    print("=" * 60)
    print()
    
    for model_id, info in OLLAMA_MODELS.items():
        print(f"{model_id}")
        print(f"  名称: {info['name']}")
        print(f"  大小: {info['size']}")
        print(f"  内存: {info['memory_required']}")
        print(f"  描述: {info['description']}")
        print()
    
    print("=" * 60)
    print("使用说明")
    print("=" * 60)
    print()
    print("1. 拉取模型:")
    print(f"   ollama pull {recommended_model}")
    print()
    print("2. 测试模型:")
    print(f"   ollama run {recommended_model}")
    print()
    print("3. 运行批量任务:")
    print(f"   python ollama_batch_runner.py --model {recommended_model}")
    print()


if __name__ == "__main__":
    main()
