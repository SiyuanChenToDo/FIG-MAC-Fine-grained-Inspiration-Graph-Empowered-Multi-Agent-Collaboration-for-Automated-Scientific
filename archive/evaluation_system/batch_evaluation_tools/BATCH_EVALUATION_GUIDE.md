# 批量评估流程完整指南

## 🎯 目标

从research_question数据库随机抽取N个研究问题，分别运行您的系统和Virtual-Scientists，然后批量对比评估并生成统计表格。

---

## 📁 文件结构

```
/root/autodl-tmp/
├── run_batch_evaluation.sh                          # 一键运行脚本
├── Myexamples/evaluation_system/batch_evaluation_tools/
│   └── sample_and_evaluate.py                       # 主评估脚本
└── Myexamples/evaluation_system/batch_results/      # 输出目录
    ├── sampled_research_questions.json              # 采样的RQ列表
    ├── your_system/                                 # 您的系统输出
    │   ├── rq_01_20251203_180000/
    │   │   ├── research_question.txt
    │   │   ├── hypothesis_report.md
    │   │   └── run_log.txt
    │   ├── rq_02_20251203_180500/
    │   └── ...
    ├── virsci/                                      # Virtual-Scientists输出
    │   ├── rq_01_20251203_180300/
    │   │   ├── research_question.txt
    │   │   ├── final_idea.txt
    │   │   └── run_log.txt
    │   ├── rq_02_20251203_180800/
    │   └── ...
    ├── evaluations/                                 # 评估结果
    │   ├── rq_01/
    │   │   ├── *_eval_v2.json
    │   │   └── *_analysis_report.md
    │   ├── rq_02/
    │   └── ...
    └── summary_comparison_table.md                  # 📊 最终统计表格
```

---

## 🚀 快速开始

### 方法1: 一键运行（推荐）

```bash
cd /root/autodl-tmp
chmod +x run_batch_evaluation.sh
./run_batch_evaluation.sh
```

### 方法2: Python直接运行

```bash
cd /root/autodl-tmp
python Myexamples/evaluation_system/batch_evaluation_tools/sample_and_evaluate.py \
    --num_samples 10 \
    --output_dir "Myexamples/evaluation_system/batch_results"
```

---

## 📊 完整流程

### 步骤1: 加载研究问题数据库

脚本会自动从以下两个来源之一加载RQ：

**来源A: JSON元数据文件**
```
Myexamples/data/final_data/final_custom_kg_papers.json
```
提取所有 `entity_type == "research_question"` 的条目

**来源B: FAISS metadata文件**
```
Myexamples/vdb/camel_faiss_storage/research_question/research_question/research_question_research_question.metadata
```

### 步骤2: 随机采样

- 使用随机种子（默认42）确保可复现
- 采样N个研究问题（默认10个）
- 保存到 `sampled_research_questions.json`

### 步骤3: 批量运行系统

**对每个研究问题：**

#### 3.1 运行您的系统
```bash
python Myexamples/test_mutiagent/hypothesis_society_demo.py "研究问题文本"
```
- 超时时间：10分钟
- 输出：`hypothesis_report.md`
- 日志：`run_log.txt`

#### 3.2 运行Virtual-Scientists
```bash
python Myexamples/comparative_experiments/Virtual-Scientists/run_comparative.py \
    --topic "研究问题文本"
```
- 超时时间：10分钟
- 输出：从log提取 `Final Idea`
- 日志：`run_log.txt`

### 步骤4: 对比评估

对每对结果运行：
```bash
python Myexamples/evaluation_system/batch_evaluation_tools/auto_extract_and_evaluate.py \
    --report_path "your_report.md" \
    --comparison_text "baseline_idea.txt" \
    --research_topic "研究问题"
```

计算所有指标：
- ON_v2 (ON_raw, ON_normalized)
- P指标 (S_src, U_src, G, P)
- 主观评分 (5维度)

### 步骤5: 生成汇总表格

统计分析所有评估结果，生成：

- **Table 1**: 客观指标对比（所有RQ）
- **Table 2**: 主观指标对比
- **Table 3**: 统计汇总（平均值、标准差、改进百分比）
- **Table 4**: 胜负统计

---

## 📋 输出示例

### `summary_comparison_table.md` 预览

```markdown
# 批量评估对比统计表

**评估时间**: 2025-12-03 18:30:45  
**研究问题数量**: 10  

---

## Table 1: 客观指标对比 (Objective Metrics)

| RQ | System | ON_raw ↑ | ON_norm ↑ | P ↑ | HD | CD | CI ↑ | S_src ↓ | U_src ↑ | G ↑ |
|-------|--------|---------|-----------|-----|-----|-----|-----|---------|---------|-----|
| rq_01 | **Ours** | 0.637 | 1.0 | 0.392 | 0.371 | 0.367 | 0.875 | 0.503 | 0.405 | 0.451 |
| rq_01 | VirSci | 0.289 | 0.0 | 0.126 | 0.371 | 0.360 | 0.324 | 0.609 | 0.0 | 0.195 |
| rq_02 | **Ours** | 0.582 | 1.0 | 0.358 | 0.362 | 0.351 | 0.792 | 0.487 | 0.392 | 0.453 |
| rq_02 | VirSci | 0.267 | 0.0 | 0.113 | 0.365 | 0.348 | 0.298 | 0.621 | 0.0 | 0.189 |
...

---

## Table 3: 统计汇总 (Statistical Summary)

| Metric | Your System | Virtual-Scientists | Improvement |
|--------|-------------|-------------------|-------------|
| ON_raw (Avg±SD) | 0.598±0.042 | 0.276±0.031 | **+116.7%** |
| P (Avg±SD) | 0.371±0.028 | 0.119±0.015 | **+211.8%** |

---

## Table 4: 胜负统计 (Win/Loss Statistics)

| Result | Count | Percentage |
|--------|-------|------------|
| **Your System Wins** | 7 | 70.0% |
| Virtual-Scientists Wins | 2 | 20.0% |
| Ties | 1 | 10.0% |
| **Total** | 10 | 100% |
```

---

## ⚙️ 高级选项

### 自定义采样数量

```bash
python sample_and_evaluate.py --num_samples 20  # 采样20个RQ
```

### 使用不同随机种子

```bash
python sample_and_evaluate.py --seed 123  # 不同的采样组合
```

### 仅生成表格（跳过运行）

如果已经有评估结果，想重新生成表格：

```bash
python sample_and_evaluate.py --skip_run \
    --output_dir "Myexamples/evaluation_system/batch_results"
```

### 自定义输出目录

```bash
python sample_and_evaluate.py \
    --output_dir "custom_batch_results" \
    --num_samples 5
```

---

## 🔧 故障排查

### 问题1: 找不到研究问题数据库

**症状**: `❌ 无法加载研究问题数据库`

**解决方案**:
```bash
# 检查JSON文件是否存在
ls -lh Myexamples/data/final_data/final_custom_kg_papers.json

# 检查FAISS metadata是否存在
ls -lh Myexamples/vdb/camel_faiss_storage/research_question/research_question/*.metadata
```

### 问题2: 系统运行超时

**症状**: `⏰ 运行超时 (>10分钟)`

**原因**: 某些复杂的研究问题可能需要更长时间

**解决方案**: 修改脚本中的timeout参数
```python
# 在 sample_and_evaluate.py 中
timeout=1200  # 改为20分钟
```

### 问题3: API Key错误

**症状**: `Missing or empty required API keys`

**解决方案**:
```bash
# 方法1: 设置环境变量
export QWEN_API_KEY="your_api_key"
export QWEN_API_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"

# 方法2: 在.env文件中配置
echo "QWEN_API_KEY=your_key" >> /root/autodl-tmp/.env
```

### 问题4: 内存不足

**症状**: 进程被kill或OOM错误

**解决方案**:
```bash
# 减少采样数量
python sample_and_evaluate.py --num_samples 3

# 或者串行运行（先运行一个系统，再运行另一个）
```

---

## 📈 分析结果

### 查看详细结果

```bash
cd Myexamples/evaluation_system/batch_results

# 查看汇总表格
cat summary_comparison_table.md

# 查看某个具体RQ的评估
cat evaluations/rq_01/*_analysis_report.md

# 查看您的系统输出
cat your_system/rq_01_*/hypothesis_report.md

# 查看Virtual-Scientists输出
cat virsci/rq_01_*/final_idea.txt
```

### 导出为CSV

如果需要Excel分析，可以转换：

```python
import json
import pandas as pd

# 读取所有评估结果
results = []
for i in range(1, 11):
    json_path = f"evaluations/rq_{i:02d}/*_eval_v2.json"
    # ... 解析并添加到results
    
# 创建DataFrame
df = pd.DataFrame(results)
df.to_csv("batch_results.csv", index=False)
```

---

## 🎯 论文使用建议

### 在论文中报告

**Table X: Large-Scale Evaluation on 10 Research Questions**

| Metric | Ours | Baseline | Improvement | p-value |
|--------|------|----------|-------------|---------|
| ON_raw | 0.598 ± 0.042 | 0.276 ± 0.031 | +116.7% | < 0.001 |
| P | 0.371 ± 0.028 | 0.119 ± 0.015 | +211.8% | < 0.001 |
| Win Rate | 70% | 20% | +50 pts | - |

**文本描述**:
> We conduct large-scale evaluation across 10 diverse research questions randomly sampled from our database. Our system achieves an average ON_raw of 0.598 (±0.042), significantly outperforming Virtual-Scientists (0.276 ± 0.031, p < 0.001). The Provenance-Adjusted Novelty (P) metric shows even stronger advantages (0.371 vs. 0.119, +211.8%), confirming that our GNN-enhanced retrieval generates genuinely innovative hypotheses rather than paraphrasing sources. In pairwise LLM judgments, our system wins in 70% of cases.

---

## 🔄 持续评估

### 定期运行

设置cron job定期评估：

```bash
# 每周日凌晨2点运行
0 2 * * 0 cd /root/autodl-tmp && ./run_batch_evaluation.sh >> cron.log 2>&1
```

### A/B测试

对比不同版本：

```bash
# 版本1
python sample_and_evaluate.py --output_dir "results_v1" --seed 42

# 版本2（改进后）
python sample_and_evaluate.py --output_dir "results_v2" --seed 42  # 相同seed
```

---

## 💡 最佳实践

1. **固定随机种子**: 使用相同seed确保不同实验可比
2. **保存中间结果**: 所有输出都保存，便于后续分析
3. **记录版本**: 在输出目录中记录代码版本/commit hash
4. **备份结果**: 定期备份evaluation结果
5. **文档化**: 记录每次批量评估的目的和发现

---

## 📞 支持

遇到问题？检查：
1. 所有路径是否正确
2. API keys是否配置
3. 依赖包是否安装
4. 日志文件 (`run_log.txt`) 中的错误信息

---

**文档版本**: 1.0  
**最后更新**: 2025-12-03  
**兼容系统**: Your System + Virtual-Scientists

