#!/usr/bin/env python3
"""
根据您的硬件配置（RTX 4080 SUPER 16GB + 90GB 内存）
推荐适合的 Ollama 大参数模型
"""

# 您的硬件配置
HARDWARE = {
    "GPU": "NVIDIA GeForce RTX 4080 SUPER",
    "VRAM": "16 GB",
    "CPU": "12 核心",
    "RAM": "90 GB",
    "Storage": "100 GB 数据盘"
}

# Ollama 支持的大参数模型（按质量排序）
POWERFUL_MODELS = {
    # ========== 顶级大模型（70B+ 参数）==========
    "llama3.1:70b": {
        "name": "Llama 3.1 70B",
        "params": "70B",
        "size_gb": 40,
        "memory_required": "64GB+ RAM",
        "vram_fit": "❌ 不完全适合",
        "description": "Meta 最强开源模型，推理质量接近 GPT-4",
        "speed": "慢（主要在 CPU 运行）",
        "quality": "⭐⭐⭐⭐⭐",
        "best_for": "最高质量的科学假设生成",
        "pull_command": "ollama pull llama3.1:70b",
        "recommendation": "🥇 首选推荐 - 您的 90GB 内存完美支持"
    },
    
    "mixtral:8x7b": {
        "name": "Mixtral 8x7B (MoE)",
        "params": "47B (激活 12B)",
        "size_gb": 26,
        "memory_required": "32GB+ RAM",
        "vram_fit": "⚠️ 部分适合",
        "description": "Mistral MoE 架构，推理质量优秀，性价比高",
        "speed": "中等",
        "quality": "⭐⭐⭐⭐⭐",
        "best_for": "高质量推理，速度质量平衡",
        "pull_command": "ollama pull mixtral:8x7b",
        "recommendation": "🥈 次选 - MoE 架构高效"
    },
    
    "qwen2.5:72b": {
        "name": "Qwen 2.5 72B",
        "params": "72B",
        "size_gb": 45,
        "memory_required": "64GB+ RAM",
        "vram_fit": "❌ 不完全适合",
        "description": "阿里巴巴最强模型，中文能力顶尖",
        "speed": "慢",
        "quality": "⭐⭐⭐⭐⭐",
        "best_for": "中文科学假设生成",
        "pull_command": "ollama pull qwen2.5:72b",
        "recommendation": "🥉 中文首选"
    },
    
    # ========== 中大型模型（32B-40B 参数）==========
    "qwen2.5:32b": {
        "name": "Qwen 2.5 32B",
        "params": "32B",
        "size_gb": 20,
        "memory_required": "32GB+ RAM",
        "vram_fit": "✅ 适合",
        "description": "Qwen 2.5 中高端型号，中文优秀",
        "speed": "中等",
        "quality": "⭐⭐⭐⭐",
        "best_for": "平衡速度和质量的中文任务",
        "pull_command": "ollama pull qwen2.5:32b",
        "recommendation": "✅ 性价比之选"
    },
    
    "llama3.1:405b": {
        "name": "Llama 3.1 405B",
        "params": "405B",
        "size_gb": 230,
        "memory_required": "256GB+ RAM",
        "vram_fit": "❌ 不适合",
        "description": "Meta 最大模型，开源界最强",
        "speed": "极慢",
        "quality": "⭐⭐⭐⭐⭐ 顶级",
        "best_for": "您的内存不足以运行此模型",
        "pull_command": "❌ 不推荐",
        "recommendation": "❌ 内存不足（需 256GB+）"
    },
    
    # ========== 专业模型 ==========
    "deepseek-coder:33b": {
        "name": "DeepSeek Coder 33B",
        "params": "33B",
        "size_gb": 18,
        "memory_required": "24GB+ RAM",
        "vram_fit": "✅ 适合",
        "description": "专为代码生成优化，逻辑推理强",
        "speed": "快",
        "quality": "⭐⭐⭐⭐",
        "best_for": "需要强逻辑推理的科学假设",
        "pull_command": "ollama pull deepseek-coder:33b",
        "recommendation": "✅ 逻辑推理强"
    },
    
    "phi4": {
        "name": "Microsoft Phi-4",
        "params": "14B",
        "size_gb": 9,
        "memory_required": "16GB+ RAM",
        "vram_fit": "✅ 完全适合",
        "description": "Microsoft 最新开源模型，小但强大",
        "speed": "很快",
        "quality": "⭐⭐⭐⭐",
        "best_for": "快速原型验证",
        "pull_command": "ollama pull phi4",
        "recommendation": "✅ 速度最快"
    },
    
    "gemma2:27b": {
        "name": "Google Gemma 2 27B",
        "params": "27B",
        "size_gb": 16,
        "memory_required": "24GB+ RAM",
        "vram_fit": "✅ 适合",
        "description": "Google 开源模型，质量稳定",
        "speed": "中等",
        "quality": "⭐⭐⭐⭐",
        "best_for": "稳定可靠的推理",
        "pull_command": "ollama pull gemma2:27b",
        "recommendation": "✅ 稳定可靠"
    },
}


def get_recommended_for_your_hardware():
    """根据您的硬件配置推荐模型"""
    print("=" * 80)
    print("🖥️  您的硬件配置")
    print("=" * 80)
    for key, value in HARDWARE.items():
        print(f"  {key}: {value}")
    print()
    
    print("=" * 80)
    print("🎯 为您推荐的模型（按优先级排序）")
    print("=" * 80)
    print()
    
    recommendations = [
        ("llama3.1:70b", "🥇 首选 - 质量最高"),
        ("mixtral:8x7b", "🥈 次选 - 速度质量平衡"),
        ("qwen2.5:72b", "🥉 中文任务首选"),
        ("qwen2.5:32b", "备选 - 更快的中文模型"),
        ("phi4", "备选 - 速度最快"),
    ]
    
    for model_id, reason in recommendations:
        if model_id in POWERFUL_MODELS:
            model = POWERFUL_MODELS[model_id]
            print(f"{reason}")
            print(f"  模型: {model['name']}")
            print(f"  参数量: {model['params']}")
            print(f"  大小: {model['size_gb']} GB")
            print(f"  质量: {model['quality']}")
            print(f"  描述: {model['description']}")
            print(f"  拉取命令: {model['pull_command']}")
            print()
    
    return [m[0] for m in recommendations]


def print_all_models():
    """打印所有可用模型"""
    print("=" * 80)
    print("📚 Ollama 支持的大参数模型大全")
    print("=" * 80)
    print()
    
    categories = {
        "70B+ 参数（顶级）": ["llama3.1:70b", "qwen2.5:72b"],
        "MoE 架构（高效）": ["mixtral:8x7b"],
        "30-40B 参数（中高端）": ["qwen2.5:32b", "deepseek-coder:33b"],
        "20-30B 参数（中端）": ["gemma2:27b"],
        "14-20B 参数（高效）": ["phi4"],
    }
    
    for category, model_ids in categories.items():
        print(f"\n{category}")
        print("-" * 80)
        
        for model_id in model_ids:
            if model_id in POWERFUL_MODELS:
                model = POWERFUL_MODELS[model_id]
                print(f"\n{model['name']} ({model_id})")
                print(f"  参数: {model['params']} | 大小: {model['size_gb']} GB")
                print(f"  质量: {model['quality']} | 速度: {model['speed']}")
                print(f"  显存适配: {model['vram_fit']}")
                print(f"  描述: {model['description']}")
                print(f"  推荐: {model['recommendation']}")
                print(f"  命令: {model['pull_command']}")


def main():
    print("\n")
    recommended = get_recommended_for_your_hardware()
    
    print()
    print("=" * 80)
    print("⚡ 快速开始命令")
    print("=" * 80)
    print()
    print("1. 下载推荐模型（选择其一）:")
    for i, model_id in enumerate(recommended[:3], 1):
        model = POWERFUL_MODELS[model_id]
        print(f"   {i}. {model['pull_command']}  # {model['name']}")
    
    print()
    print("2. 运行批量任务:")
    print(f"   python ollama_batch_runner.py --model {recommended[0]} --start-idx 0 --end-idx 5")
    
    print()
    print("3. 查看所有模型详情:")
    print("   python ollama_powerful_models.py --all")
    
    print()
    print("=" * 80)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        print_all_models()
    else:
        main()
