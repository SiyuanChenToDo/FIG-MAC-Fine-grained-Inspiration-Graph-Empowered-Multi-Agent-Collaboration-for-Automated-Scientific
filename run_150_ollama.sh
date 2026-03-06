#!/bin/bash
# 使用 screen 运行 150 个问题，防止 SSH 断开

cd /root/autodl-tmp

echo "=================================="
echo "FIG-MAC Ollama - 150 Questions"
echo "=================================="
echo "Model: mixtral:8x7b"
echo "Memory: 90GB"
echo "=================================="

# 检查 screen
if ! command -v screen &> /dev/null; then
    echo "安装 screen..."
    apt-get update && apt-get install -y screen
fi

# 创建运行脚本
cat > /tmp/run_batch.py << 'PYEOF'
import asyncio
import sys
sys.path.insert(0, '/root/autodl-tmp')

from Myexamples.kimi_batch_runner.ollama_batch_runner import OllamaBatchRunner

async def main():
    runner = OllamaBatchRunner(
        model="mixtral:8x7b",
        output_dir="Myexamples/ollama_batch_results"
    )
    
    await runner.run_batch(
        questions_file="Myexamples/evaluation_system/batch_results/ours/all_research_questions.json",
        start_idx=0,
        end_idx=150,
        max_iterations=2,
        quality_threshold=7.5,
        delay_between=15
    )

asyncio.run(main())
PYEOF

# 使用 screen 运行
echo "启动 screen 会话: ollama_150"
screen -dmS ollama_150 bash -c "cd /root/autodl-tmp && python3 /tmp/run_batch.py 2>&1 | tee /tmp/ollama_150.log"

echo ""
echo "✅ 任务已在后台启动"
echo ""
echo "查看日志:"
echo "  tail -f /tmp/ollama_150.log"
echo ""
echo "重新连接 screen:"
echo "  screen -r ollama_150"
echo ""
echo "查看所有 screen 会话:"
echo "  screen -ls"
