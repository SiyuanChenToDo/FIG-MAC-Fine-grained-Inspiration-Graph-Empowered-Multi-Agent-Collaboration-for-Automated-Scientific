#!/bin/bash
# FIG-MAC Kimi Batch Runner 启动脚本

# 设置 Kimi API 环境变量
export MOONSHOT_API_KEY="sk-sHrxCSJDJ72L6UlXKRNEbbe8aUx05LkqroaoHeRbkmZEHpKU"
export MOONSHOT_API_BASE_URL="https://api.moonshot.cn/v1"
export OPENAI_API_KEY="${MOONSHOT_API_KEY}"
export OPENAI_COMPATIBILITY_API_KEY="${MOONSHOT_API_KEY}"
export OPENAI_API_BASE_URL="${MOONSHOT_API_BASE_URL}"
export OPENAI_COMPATIBILITY_API_BASE_URL="${MOONSHOT_API_BASE_URL}"

cd /root/autodl-tmp

echo "=================================="
echo "FIG-MAC Kimi Batch Runner"
echo "=================================="
echo "API: Kimi (Moonshot)"
echo "Model: kimi-k2-5 (K2.5)"
echo "Output: Myexamples/kimi_batch_results/"
echo "=================================="
echo ""

# 运行参数
QUESTIONS_FILE="Myexamples/evaluation_system/batch_results/ours/all_research_questions.json"
OUTPUT_DIR="Myexamples/kimi_batch_results"
START_IDX=${1:-0}      # 默认从 0 开始
END_IDX=${2:-150}      # 默认到 150 (处理全部)
MAX_ITERATIONS=3
QUALITY_THRESHOLD=8.0
DELAY=2.0

echo "Configuration:"
echo "  Start Index: ${START_IDX}"
echo "  End Index: ${END_IDX}"
echo "  Max Iterations: ${MAX_ITERATIONS}"
echo "  Quality Threshold: ${QUALITY_THRESHOLD}"
echo "  Delay Between: ${DELAY}s"
echo ""

python Myexamples/kimi_batch_runner/kimi_batch_runner.py \
    --questions-file "${QUESTIONS_FILE}" \
    --output-dir "${OUTPUT_DIR}" \
    --start-idx ${START_IDX} \
    --end-idx ${END_IDX} \
    --max-iterations ${MAX_ITERATIONS} \
    --quality-threshold ${QUALITY_THRESHOLD} \
    --delay ${DELAY}

echo ""
echo "Batch processing completed!"
echo "Results saved to: ${OUTPUT_DIR}"
