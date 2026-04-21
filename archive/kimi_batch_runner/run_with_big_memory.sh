#!/bin/bash
# 使用大内存配置运行 Ollama 批量任务

# 设置大内存环境变量
export OLLAMA_HOST="http://127.0.0.1:11434"
export OLLAMA_MODELS="/root/.ollama/models"

# 解除 Python 内存限制
export PYTHONUNBUFFERED=1
export MALLOC_ARENA_MAX=2

# 设置 Ollama 使用更多内存
export OLLAMA_NUM_PARALLEL=1
export OLLAMA_MAX_LOADED_MODELS=1
export OLLAMA_CONTEXT_LENGTH=4096

# 清理 Python 缓存
cd /root/autodl-tmp
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

echo "=================================="
echo "FIG-MAC Ollama (大内存模式)"
echo "=================================="
echo "Model: mixtral:8x7b"
echo "Memory: 90GB"
echo "=================================="
echo ""

# 检查 Ollama
if ! pgrep -x "ollama" > /dev/null; then
    echo "启动 Ollama 服务..."
    nohup ollama serve > /tmp/ollama.log 2>&1 &
    sleep 5
fi

echo "可用模型:"
ollama list
echo ""

# 运行单个测试
echo "先测试单个问题..."
python3 << 'EOF'
import sys
sys.path.insert(0, '/root/autodl-tmp')

import asyncio
import gc
from Myexamples.kimi_batch_runner.hypothesis_society_ollama import HypothesisGenerationSociety

async def test():
    # 强制垃圾回收
    gc.collect()
    
    society = HypothesisGenerationSociety(model_name="mixtral:8x7b")
    team = society.create_research_team()
    
    result = await society.run_research_async(
        "How can we improve crime forecasting accuracy?",
        max_iterations=1,
        quality_threshold=7.0
    )
    
    if not result.failed:
        print("✅ 测试成功！")
        print(f"报告: {result.metadata.get('file_path', 'N/A')}")
    else:
        print(f"❌ 测试失败: {result.content}")

asyncio.run(test())
EOF

echo ""
echo "测试完成！"
