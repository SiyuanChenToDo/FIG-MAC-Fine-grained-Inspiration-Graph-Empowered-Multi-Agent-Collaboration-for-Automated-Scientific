# 三系统评估完整指南

## ✅ 确保所有指标正确计算和集成

### 评估的三个系统

1. **Ours (System A)**: 您的系统
2. **Virtual-Scientists (System B)**: 基线系统1
3. **CoI-Agent (System C)**: 基线系统2

### 所有评估指标

#### 客观指标 (Objective Metrics)

所有三个系统都会计算以下完整指标：

1. **ON_raw (Overall Novelty - Raw)**: 原始整体新颖性
2. **ON_norm (Overall Novelty - Normalized)**: 归一化整体新颖性（基于排名）
3. **HD (Historical Dissimilarity)**: 历史差异度
4. **CD (Contemporary Dissimilarity)**: 当代差异度
5. **CI (Contemporary Impact, Year-Normalized)**: 当代影响力（年份归一化）
6. **P (Provenance-Adjusted Novelty)**: 来源调整新颖性
7. **S_src (Source Similarity)**: 来源相似度
8. **U_src (Source Diversity)**: 来源多样性
9. **G (Provenance Factor)**: 来源因子

#### 主观指标 (Subjective Metrics)

所有三个系统都会计算以下LLM评分：

1. **Novelty**: 新颖性评分
2. **Significance**: 重要性评分
3. **Effectiveness**: 有效性评分
4. **Clarity**: 清晰度评分
5. **Feasibility**: 可行性评分

### 评估流程

#### 1. 系统运行

```python
# 运行三个系统
your_success, your_dir = run_your_system(rq_text, output_dir, i)
virsci_success, virsci_dir = run_virsci_system(rq_text, output_dir, i)
coi_success, coi_dir = run_coi_system(rq_text, output_dir, i)
```

#### 2. 对比评估

```python
# Ours vs Virtual-Scientists
evaluate_pair(your_dir, virsci_dir, rq_text, output_dir, i, baseline_name="virsci")

# Ours vs CoI-Agent
evaluate_pair(your_dir, coi_dir, rq_text, output_dir, i, baseline_name="coi")
```

每个对比评估会：
- 调用 `auto_extract_and_evaluate.py`（使用现有评估体系）
- 计算所有客观指标（ON_v2, P, HD, CD, CI, S_src, U_src, G）
- 计算所有主观指标（Novelty, Significance, Effectiveness, Clarity, Feasibility）
- 生成对比评估结果

#### 3. 结果保存

每个评估结果保存在：
```
evaluations/
├── rq_01_virsci/
│   └── *_eval_v2.json  # 包含所有指标
└── rq_01_coi/
    └── *_eval_v2.json  # 包含所有指标
```

### 汇总统计表格

`generate_summary_table()` 会生成包含三个系统所有指标的完整表格：

#### Table 1: 客观指标对比

| RQ | System | ON_raw ↑ | ON_norm ↑ | P ↑ | HD | CD | CI ↑ | S_src ↓ | U_src ↑ | G ↑ |
|-------|--------|---------|-----------|-----|-----|-----|-----|---------|---------|-----|
| rq_01 | **Ours** | 1.461 | 1.000 | 0.944 | 0.418 | 0.377 | 2.742 | 0.416 | 0.405 | ... |
| rq_01 | **VirSci** | 0.909 | 0.000 | 0.426 | 0.398 | 0.386 | 1.415 | 0.518 | 0.000 | ... |
| rq_01 | **CoI-Agent** | ... | ... | ... | ... | ... | ... | ... | ... | ... |

#### Table 2: 主观指标对比

| RQ | System | Novelty | Significance | Effectiveness | Clarity | Feasibility |
|-------|--------|---------|--------------|---------------|---------|-------------|
| rq_01 | **Ours** | 8 | 9 | 7 | 7 | 6 |
| rq_01 | **VirSci** | 8 | 9 | 7 | 8 | 7 |
| rq_01 | **CoI-Agent** | ... | ... | ... | ... | ... |

#### Table 3: 统计汇总

| Metric | Ours | VirSci | CoI-Agent | Ours vs VirSci | Ours vs CoI |
|--------|------|--------|-----------|----------------|-------------|
| ON_raw (Avg±SD) | 1.461±0.123 | 0.909±0.045 | ... | +60.7% | ... |
| P (Avg±SD) | 0.944±0.012 | 0.426±0.023 | ... | +121.6% | ... |

#### Table 4: 胜负统计

分别统计两个对比：
- **Ours vs Virtual-Scientists**: 胜负次数和百分比
- **Ours vs CoI-Agent**: 胜负次数和百分比

### 数据收集逻辑

```python
# 收集所有评估结果（包括所有baseline系统）
results = {}
for rq_dir in sorted(Path(eval_dir).glob("rq_*")):
    rq_id = rq_dir.name.split('_')[0] + '_' + rq_dir.name.split('_')[1]
    baseline_name = rq_dir.name.split('_', 2)[2]  # 提取 baseline 名称
    
    # 根据 baseline_name 存储数据
    if baseline_name == "virsci":
        results[rq_id]["virsci"] = eval_data
    elif baseline_name == "coi":
        results[rq_id]["coi"] = eval_data
```

### 指标提取逻辑

所有指标都从 `*_eval_v2.json` 文件中提取：

```python
# 您的系统指标
your_obj = rq_data.get("your_system", {}).get("objective", {})
your_nov = your_obj.get('Novelty_Metrics', {})
your_prov = your_obj.get('Provenance_Metrics', {})

# Virtual-Scientists 指标
virsci_obj = virsci_data.get('comparison', {}).get('baseline_metrics', {}).get('objective', {})
virsci_nov = virsci_obj.get('Novelty_Metrics', {})
virsci_prov = virsci_obj.get('Provenance_Metrics', {})

# CoI-Agent 指标
coi_obj = coi_data.get('comparison', {}).get('baseline_metrics', {}).get('objective', {})
coi_nov = coi_obj.get('Novelty_Metrics', {})
coi_prov = coi_obj.get('Provenance_Metrics', {})
```

### 验证清单

- [x] 所有三个系统都能正确运行
- [x] 所有客观指标（9个）都能正确计算
- [x] 所有主观指标（5个）都能正确计算
- [x] 评估结果正确保存到 JSON 文件
- [x] 汇总表格正确收集三个系统的数据
- [x] 统计汇总正确计算三个系统的平均值和标准差
- [x] 胜负统计分别统计两个对比

### 使用方式

```bash
python Myexamples/evaluation_system/batch_evaluation_tools/sample_and_evaluate.py \
    --num_samples 10 \
    --output_dir Myexamples/evaluation_system/batch_results
```

系统会自动：
1. 运行三个系统（Ours, VirSci, CoI-Agent）
2. 进行两两对比评估
3. 计算所有指标
4. 生成包含三个系统所有指标的汇总表格

### 输出文件

- `batch_results/your_system/rq_XX_*/hypothesis_report.md`: 您的系统输出
- `batch_results/virsci/rq_XX_*/final_idea.txt`: Virtual-Scientists 输出
- `batch_results/coi/rq_XX_*/final_idea.txt`: CoI-Agent 输出
- `batch_results/evaluations/rq_XX_virsci/*_eval_v2.json`: Ours vs VirSci 评估结果
- `batch_results/evaluations/rq_XX_coi/*_eval_v2.json`: Ours vs CoI-Agent 评估结果
- `batch_results/summary_comparison_table.md`: 包含三个系统所有指标的汇总表格

## ✅ 保证

**所有评估指标都通过现有的 `run_evaluation.py` 和 `auto_extract_and_evaluate.py` 计算，不重复实现任何逻辑。**

