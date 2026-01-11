#!/bin/bash

#######################################
# 批量评估运行脚本
# 
# 功能：
# 1. 从research_question数据库随机抽取10个RQ
# 2. 分别运行您的系统和Virtual-Scientists
# 3. 批量评估并生成对比表格
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

# 从.env加载（如果存在）
if [ -f /root/autodl-tmp/.env ]; then
    export $(grep -v '^#' /root/autodl-tmp/.env | xargs)
fi

# 进入项目目录
cd /root/autodl-tmp

echo "========================================"
echo "🚀 批量评估流程启动"
echo "========================================"
echo "采样数量: 10个研究问题"
echo "输出目录: Myexamples/evaluation_system/batch_results"
echo "========================================"
echo ""

# 运行主脚本
python Myexamples/evaluation_system/batch_evaluation_tools/sample_and_evaluate.py \
    --num_samples 10 \
    --output_dir "Myexamples/evaluation_system/batch_results" \
    --seed 42

echo ""
echo "========================================"
echo "✅ 批量评估完成！"
echo "========================================"
echo ""
echo "📊 查看结果:"
echo "   cd Myexamples/evaluation_system/batch_results"
echo "   cat summary_comparison_table.md"
echo ""

