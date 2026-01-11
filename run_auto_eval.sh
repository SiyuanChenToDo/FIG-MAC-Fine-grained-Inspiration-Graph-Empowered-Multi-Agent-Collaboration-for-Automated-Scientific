#!/bin/bash

# 加载环境变量
source /root/.bashrc 2>/dev/null || true

# 从.env文件加载
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# 设置API keys（如果还没有）
export QWEN_API_KEY="${QWEN_API_KEY:-sk-17b29aac8c554bb1bf3ad28fa932ed67}"
export QWEN_API_BASE_URL="${QWEN_API_BASE_URL:-https://dashscope.aliyuncs.com/compatible-mode/v1}"

# 运行评估
python Myexamples/evaluation_system/batch_evaluation_tools/auto_extract_and_evaluate.py \
  --report_path "Scientific_Hypothesis_Reports/20251203_154321_How_can_we_design_a_multi-task_learning_framework_.md" \
  --inspiration_report "inspiration_report.md" \
  --comparison_text "Myexamples/comparative_experiments/baseline_virsci_nscrel.txt" \
  --research_topic "How can we design a multi-task learning framework that effectively mitigates negative transfer in aspect-based sentiment analysis?"
