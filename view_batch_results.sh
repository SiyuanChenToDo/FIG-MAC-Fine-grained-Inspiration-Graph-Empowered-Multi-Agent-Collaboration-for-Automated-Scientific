#!/bin/bash

####################################
# 查看批量评估结果
####################################

RESULT_DIR="${1:-Myexamples/evaluation_system/batch_results}"

echo "========================================"
echo "📊 批量评估结果查看器"
echo "========================================"
echo "结果目录: $RESULT_DIR"
echo ""

if [ ! -d "$RESULT_DIR" ]; then
    echo "❌ 目录不存在: $RESULT_DIR"
    echo ""
    echo "可用选项:"
    echo "  ./view_batch_results.sh Myexamples/evaluation_system/test_batch_results"
    echo "  ./view_batch_results.sh Myexamples/evaluation_system/batch_results"
    exit 1
fi

cd /root/autodl-tmp

# 1. 检查文件
echo "1️⃣  文件检查"
echo "----------------------------------------"
if [ -f "$RESULT_DIR/summary_comparison_table.md" ]; then
    echo "✅ 汇总表格: 已生成"
else
    echo "❌ 汇总表格: 未找到"
fi

if [ -f "$RESULT_DIR/sampled_research_questions.json" ]; then
    RQ_COUNT=$(cat "$RESULT_DIR/sampled_research_questions.json" | python3 -c "import json, sys; print(len(json.load(sys.stdin)))")
    echo "✅ 采样RQ数: $RQ_COUNT"
else
    echo "❌ 采样RQ列表: 未找到"
    RQ_COUNT=0
fi

YOUR_COUNT=$(ls -d "$RESULT_DIR"/your_system/rq_* 2>/dev/null | wc -l)
echo "✅ 您的系统输出: $YOUR_COUNT 个"

VIRSCI_COUNT=$(ls -d "$RESULT_DIR"/virsci/rq_* 2>/dev/null | wc -l)
echo "✅ VirSci输出: $VIRSCI_COUNT 个"

EVAL_COUNT=$(ls -d "$RESULT_DIR"/evaluations/rq_* 2>/dev/null | wc -l)
echo "✅ 评估结果: $EVAL_COUNT 个"

echo ""

# 2. 显示采样的RQ
echo "2️⃣  采样的研究问题"
echo "----------------------------------------"
if [ -f "$RESULT_DIR/sampled_research_questions.json" ]; then
    cat "$RESULT_DIR/sampled_research_questions.json" | python3 << 'EOF'
import json, sys
data = json.load(sys.stdin)
for i, rq in enumerate(data[:5], 1):
    q = rq['question']
    preview = q[:80] + "..." if len(q) > 80 else q
    print(f"[{i}] {preview}")
if len(data) > 5:
    print(f"... 还有 {len(data)-5} 个")
EOF
fi

echo ""

# 3. 显示Table 3（统计汇总）
echo "3️⃣  统计汇总 (Table 3)"
echo "----------------------------------------"
if [ -f "$RESULT_DIR/summary_comparison_table.md" ]; then
    grep -A 6 "## Table 3" "$RESULT_DIR/summary_comparison_table.md" | tail -5
fi

echo ""

# 4. 显示Table 4（胜负统计）
echo "4️⃣  胜负统计 (Table 4)"
echo "----------------------------------------"
if [ -f "$RESULT_DIR/summary_comparison_table.md" ]; then
    grep -A 8 "## Table 4" "$RESULT_DIR/summary_comparison_table.md" | tail -6
fi

echo ""
echo "========================================"
echo "📄 查看完整报告:"
echo "   cat $RESULT_DIR/summary_comparison_table.md"
echo ""
echo "📂 查看详细结构:"
echo "   tree -L 2 $RESULT_DIR"
echo ""
echo "🔍 查看某个RQ详情:"
echo "   cat $RESULT_DIR/evaluations/rq_01/*_analysis_report.md"
echo "========================================"

