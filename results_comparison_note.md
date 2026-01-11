# 实验结果对比说明

## 数据质量检查结果

### 发现的问题

1. **Ours数据中有1行异常数据**（第81行）：
   - 所有主观评价指标（Novelty, Significance, Effectiveness, Clarity, Feasibility）均为0
   - Fluency_Score异常低（0.1，正常范围0.8-0.9）
   - 这可能是评估失败或数据缺失导致的

2. **异常值的影响**：
   - 去除异常值后，Ours的主观评价指标平均值提升约0.67%
   - 影响相对较小，但建议在论文中说明

### 建议

1. **方案A（推荐）**：使用去除异常值后的结果
   - 文件：`results_table_cleaned.tex` 或 `results_table_simple_cleaned.tex`
   - 在论文中说明："我们排除了1个评估失败的样本"

2. **方案B**：使用原始数据
   - 文件：`results_table_original.tex` 或 `results_table_simple_original.tex`
   - 在论文中说明："包含所有150个样本，其中1个样本评估失败"

## Ours方法的优势指标

即使在原始数据中，Ours在以下指标上表现最佳或接近最佳：

- **ON_normalized**: 0.5033（最佳）
- **G (Provenance Factor)**: 0.6850（最佳）
- **U_src (Source Diversity)**: 0.5566（第二，仅次于AI Scientist的0.5817）
- **P (Provenance-Adjusted Novelty)**: 0.5077（与VirSci的0.5086非常接近）

## 对比结果总结

| 指标类别 | Ours表现 | 说明 |
|---------|---------|------|
| 客观指标 | 良好 | ON_normalized和G最佳，其他指标接近最佳 |
| 主观指标 | 略低 | 去除异常值后有所提升，但仍略低于VirSci和COI |
