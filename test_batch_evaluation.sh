#!/bin/bash

#######################################
# 测试批量评估（仅2个样本，快速验证）
#######################################

# 设置完全离线模式（彻底禁用HuggingFace联网）
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_DATASETS_OFFLINE=1

echo "🔒 已启用完全离线模式（禁用HuggingFace联网）"

# 设置API环境变量
export QWEN_API_KEY="${QWEN_API_KEY:-sk-17b29aac8c554bb1bf3ad28fa932ed67}"
export QWEN_API_BASE_URL="${QWEN_API_BASE_URL:-https://dashscope.aliyuncs.com/compatible-mode/v1}"
export OPENAI_COMPATIBILITY_API_KEY="${QWEN_API_KEY}"
export OPENAI_COMPATIBILITY_API_BASE_URL="${QWEN_API_BASE_URL}"

if [ -f /root/autodl-tmp/.env ]; then
    export $(grep -v '^#' /root/autodl-tmp/.env | xargs)
fi

cd /root/autodl-tmp

echo "========================================"
echo "🧪 测试批量评估（2个样本）"
echo "========================================"

python Myexamples/evaluation_system/batch_evaluation_tools/sample_and_evaluate.py \
    --num_samples 2 \
    --output_dir "Myexamples/evaluation_system/test_batch_results" \
    --seed 123

echo ""
echo "✅ 测试完成！查看结果:"
echo "   cat Myexamples/evaluation_system/test_batch_results/summary_comparison_table.md"

