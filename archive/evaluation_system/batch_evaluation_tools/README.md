# 批量对比评估工具集

本目录包含用于大规模对比 **Hypothesis Society** 和 **Virtual-Scientists** 两个科学假设生成系统的自动化评估工具。

---

## 📁 目录结构

```
batch_evaluation_tools/
├── README.md                           # 本文档
├── batch_comparative_evaluation.py     # 批量对比评估主脚本
├── extract_baseline_from_log.py        # 基线文本提取工具
└── examples/                           # 示例配置和脚本（可选创建）
```

---

## 🚀 快速开始

### 1. 准备工作

#### 运行两个系统生成数据

**步骤 1: 运行 Hypothesis Society**
```bash
cd /root/autodl-tmp
python Myexamples/test_mutiagent/hypothesis_society_demo.py "你的研究问题"
```
生成的报告会保存在 `Scientific_Hypothesis_Reports/` 目录。

**步骤 2: 运行 Virtual-Scientists**
```bash
cd /root/autodl-tmp
python Myexamples/comparative_experiments/Virtual-Scientists/run_comparative.py \
  --topic "你的研究问题"
```
生成的日志会保存在 `/root/autodl-tmp/logs_qwen/` 目录。

---

### 2. 单次对比评估

如果只需要对比一次，使用评估系统的基础命令：

```bash
# 步骤1: 从日志提取基线文本
python batch_evaluation_tools/extract_baseline_from_log.py \
  --log_file /root/autodl-tmp/logs_qwen/20251203_155525_1,1_dialogue.log \
  --output baseline_output.txt

# 步骤2: 运行对比评估
python run_evaluation.py \
  --report_path Scientific_Hypothesis_Reports/your_report.md \
  --comparison_text "$(cat baseline_output.txt)"
```

---

### 3. 批量对比评估（推荐）

#### 方式 A: 自动匹配（按日期）

系统会自动根据报告的时间戳查找对应日期的基线日志：

```bash
python batch_evaluation_tools/batch_comparative_evaluation.py \
  --our_reports_dir "Scientific_Hypothesis_Reports" \
  --baseline_logs_dir "/root/autodl-tmp/logs_qwen" \
  --output_dir "batch_evaluation_tools/results"
```

**输出：**
- `batch_results/`: 包含每个报告的详细评估JSON和Markdown
- `batch_summary_YYYYMMDD_HHMMSS.json`: 批量评估汇总
- `aggregate_report_YYYYMMDD_HHMMSS.md`: 中文分析报告

#### 方式 B: 指定研究问题列表

如果你有对应的研究问题列表，可以提供：

```bash
# 1. 创建研究问题列表文件 topics.txt，每行一个问题：
# 问题1：How can we design...
# 问题2：What is the best approach...

# 2. 运行批量评估
python batch_evaluation_tools/batch_comparative_evaluation.py \
  --our_reports_dir "Scientific_Hypothesis_Reports" \
  --baseline_logs_dir "/root/autodl-tmp/logs_qwen" \
  --topics_file "topics.txt" \
  --output_dir "batch_evaluation_tools/results"
```

---

## 🔧 工具详解

### 1. `extract_baseline_from_log.py`

从 Virtual-Scientists 日志文件中提取结构化的基线文本。

#### 单文件提取
```bash
python batch_evaluation_tools/extract_baseline_from_log.py \
  --log_file /path/to/log.log \
  --output baseline.txt \
  --verbose
```

#### 批量提取
```bash
python batch_evaluation_tools/extract_baseline_from_log.py \
  --log_dir /root/autodl-tmp/logs_qwen \
  --output_dir extracted_baselines \
  --pattern "*_1,1_dialogue.log"
```

**参数说明：**
- `--log_file`: 单个日志文件路径
- `--log_dir`: 日志目录（批量模式）
- `--output`: 输出文件路径（单文件模式）
- `--output_dir`: 输出目录（批量模式）
- `--pattern`: 日志文件匹配模式，默认 `*_1,1_dialogue.log`
- `--verbose`: 显示详细提取信息

**提取格式：**
```
Title: <论文标题>

Abstract: <研究摘要>

Experiment Design: <实验设计>

Quality Metrics:
- Clarity: X/10
- Feasibility: X/10
- Novelty: X/10
```

---

### 2. `batch_comparative_evaluation.py`

批量对比评估的主控脚本。

#### 完整参数列表
```bash
python batch_evaluation_tools/batch_comparative_evaluation.py \
  --our_reports_dir "Scientific_Hypothesis_Reports" \
  --baseline_logs_dir "/root/autodl-tmp/logs_qwen" \
  --output_dir "batch_evaluation_tools/results" \
  --topics_file "research_questions.txt" \
  --report_pattern "*.md"
```

**参数说明：**
- `--our_reports_dir`: 你的系统生成的报告目录
- `--baseline_logs_dir`: Virtual-Scientists 日志目录
- `--output_dir`: 批量评估结果输出目录
- `--topics_file`: 研究问题列表文件（可选）
- `--report_pattern`: 报告文件匹配模式，默认 `*.md`

**输出结构：**
```
batch_results/
├── 20251203_154321_..._eval_v2.json          # 每个报告的JSON结果
├── 20251203_154321_..._analysis_report.md    # 每个报告的中文分析
├── batch_summary_20251203_160530.json        # 批量汇总JSON
└── aggregate_report_20251203_160530.md       # 批量汇总中文报告
```

---

## 📊 输出报告解读

### 单次评估报告

每次评估生成两个文件：

1. **JSON结果** (`*_eval_v2.json`)
   - 客观指标：流畅性、新颖性（HD/CD/CI/ON）
   - 主观LLM评分：新颖性、重要性、有效性、清晰度、可行性
   - 对比结果：胜者、理由、双方优势

2. **中文分析报告** (`*_analysis_report.md`)
   - 核心结论：谁赢了，为什么
   - 详细得分对比表
   - 深度分析：双方优劣势
   - 改进建议：3条具体建议

### 批量汇总报告

`aggregate_report_*.md` 包含：
- 总体胜负统计（胜率）
- 平均指标对比
- 详细结果列表
- 结论与建议

---

## 💡 使用场景

### 场景1: 论文对比实验

**目标**: 为论文生成大规模对比实验数据

```bash
# 1. 准备10个研究问题
cat > research_questions.txt << EOF
Question 1: How can we design...
Question 2: What is the optimal...
...
EOF

# 2. 批量运行两个系统（手动或脚本）
for question in $(cat research_questions.txt); do
    python hypothesis_society_demo.py "$question"
    python run_comparative.py --topic "$question"
done

# 3. 批量评估
python batch_comparative_evaluation.py \
  --our_reports_dir "Scientific_Hypothesis_Reports" \
  --baseline_logs_dir "/root/autodl-tmp/logs_qwen" \
  --topics_file "research_questions.txt"

# 4. 查看汇总报告
cat batch_results/aggregate_report_*.md
```

### 场景2: 快速原型测试

**目标**: 快速测试系统改进效果

```bash
# 1. 单次运行
python hypothesis_society_demo.py "测试问题"
python run_comparative.py --topic "测试问题"

# 2. 快速评估
python batch_comparative_evaluation.py \
  --our_reports_dir "Scientific_Hypothesis_Reports" \
  --baseline_logs_dir "/root/autodl-tmp/logs_qwen"
```

### 场景3: 补充基线数据

**目标**: 之前只运行了你的系统，现在补充基线对比

```bash
# 1. 批量提取历史基线
python extract_baseline_from_log.py \
  --log_dir /root/autodl-tmp/logs_qwen \
  --output_dir extracted_baselines

# 2. 手动对比评估
for report in Scientific_Hypothesis_Reports/*.md; do
    date=$(basename $report | cut -d'_' -f1)
    baseline="extracted_baselines/${date}*_baseline.txt"
    if [ -f $baseline ]; then
        python run_evaluation.py \
          --report_path "$report" \
          --comparison_text "$(cat $baseline)"
    fi
done
```

---

## ⚙️ 配置与优化

### 环境变量

确保以下环境变量已设置：
```bash
export QWEN_API_KEY="your-api-key"
export QWEN_API_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
```

### 性能优化

1. **并行评估**: 可修改脚本支持多进程并行处理
2. **缓存向量**: 相同文本的embedding计算可缓存
3. **快速模式**: 使用 Qwen-Plus 替代 Qwen-Max 加速评估

---

## 🐛 常见问题

### Q1: 找不到匹配的基线日志？
**A**: 检查日志文件命名格式是否为 `YYYYMMDD_HHMMSS_1,1_dialogue.log`，确保日期部分与报告一致。

### Q2: 基线提取失败？
**A**: 运行 `extract_baseline_from_log.py --verbose` 查看详细错误。常见原因：
- 日志不完整（系统未运行到 Epoch 2）
- JSON格式损坏

### Q3: 评估超时？
**A**: 默认超时5分钟。可在 `batch_comparative_evaluation.py` 中修改 `timeout` 参数。

### Q4: 元数据文件找不到？
**A**: 确保 `Myexamples/data/final_custom_kg_papers.json` 存在。如果缺失，新颖性指标（HD/CD/CI）将无法计算。

---

## 📚 相关文档

- [评估系统输入输出详解](../EVALUATION_INPUT_OUTPUT.md)
- [评估方案说明](../EVALUATION_SCHEME.md)
- [核心评估算法](../metrics_calculator.py)
- [LLM评估器](../llm_evaluator.py)

---

## 🤝 贡献与反馈

如遇到问题或有改进建议，请：
1. 检查日志文件和错误信息
2. 参考上述文档
3. 联系开发者

---

**最后更新**: 2025-12-03  
**版本**: v1.0

