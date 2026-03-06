#!/bin/bash
# Ollama GPU 批处理运行脚本
# 使用方式: ./run_with_gpu.sh [模型名称]

MODEL=${1:-"qwen2.5:7b"}  # 默认使用轻量级模型

# 等待 Ollama 安装完成
echo "=== 等待 Ollama 安装完成 ==="
while pgrep -f "curl.*ollama" > /dev/null || pgrep -f "tar.*ollama" > /dev/null; do
    echo -n "."
    sleep 5
done
echo "✅ Ollama 安装完成"

# 停止旧服务
pkill -9 ollama 2>/dev/null
sleep 3

# 启动新 Ollama（强制使用 GPU）
export PATH="/usr/local/bin:$PATH"
export OLLAMA_CUDA_VISIBLE_DEVICES=0
export OLLAMA_NUM_GPU=1

nohup ollama serve > /tmp/ollama_gpu.log 2>&1 &
sleep 5

# 检查 GPU 是否被检测到
echo "=== 检查 GPU 状态 ==="
if grep -q "cuda\|nvidia\|GPU" /tmp/ollama_gpu.log 2>/dev/null; then
    echo "✅ GPU 已检测到"
    nvidia-smi | grep -A 2 "GPU  Name"
else
    echo "⚠️ GPU 未检测到，使用 CPU 模式"
fi

# 拉取模型（如果未下载）
echo "=== 检查模型: $MODEL ==="
if ! ollama list | grep -q "$MODEL"; then
    echo "正在拉取模型..."
    ollama pull "$MODEL"
fi

# 测试模型速度
echo "=== 测试模型速度 ==="
time ollama run "$MODEL" "Hello, are you working?" 2>&1 | tail -5

# 运行批处理
echo "=== 启动批处理 ==="
python3 Myexamples/kimi_batch_runner/ollama_batch_runner.py \
    --model "$MODEL" \
    --questions-file Myexamples/evaluation_system/batch_results/ours/all_research_questions.json \
    --start-idx 0 --end-idx 150

echo "✅ 批处理完成"
