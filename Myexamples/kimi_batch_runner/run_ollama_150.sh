#!/bin/bash
# 运行全部 150 个研究问题 - Ollama Mixtral 8x7B 版本

# 设置 Ollama 环境变量（解除内存限制）
export OLLAMA_HOST="http://localhost:11434"
export OLLAMA_MODEL="mixtral:8x7b"

# 检查 Ollama 是否运行
if ! curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "❌ Ollama 服务未运行，正在启动..."
    nohup ollama serve > /tmp/ollama.log 2>&1 &
    sleep 5
fi

# 检查模型是否存在
if ! ollama list | grep -q "mixtral:8x7b"; then
    echo "❌ mixtral:8x7b 模型未找到"
    echo "请先下载: ollama pull mixtral:8x7b"
    exit 1
fi

echo "=================================="
echo "FIG-MAC Ollama Batch Runner"
echo "=================================="
echo "Model: mixtral:8x7b (Mixtral MoE)"
echo "Total Questions: 150"
echo "Output: Myexamples/ollama_batch_results/"
echo "=================================="
echo ""

# 运行批量任务（分批运行，避免内存问题）
# 每批 10 个问题，间隔 10 秒

echo "开始处理 150 个研究问题..."
echo ""

cd /root/autodl-tmp

python Myexamples/kimi_batch_runner/ollama_batch_runner.py \
    --model mixtral:8x7b \
    --questions-file Myexamples/evaluation_system/batch_results/ours/all_research_questions.json \
    --output-dir Myexamples/ollama_batch_results \
    --start-idx 0 \
    --end-idx 150 \
    --max-iterations 2 \
    --quality-threshold 7.5 \
    --delay 10

echo ""
echo "=================================="
echo "批量运行完成！"
echo "=================================="
echo "结果目录: Myexamples/ollama_batch_results/"
echo "报告目录: Myexamples/ollama_batch_results/reports/"
echo "=================================="
