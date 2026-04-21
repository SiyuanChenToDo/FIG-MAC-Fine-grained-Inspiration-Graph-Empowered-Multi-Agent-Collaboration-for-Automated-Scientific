# 评估系统输入输出说明文档

## 📥 输入 (Input)

### 1. 命令行参数
```bash
python run_evaluation.py \
  --report_path <目标报告路径> \
  --comparison_text <基线文本> \
  --vdb_path <向量数据库路径> \
  --json_data <元数据JSON路径> \
  --output_dir <输出目录>
```

### 2. 输入内容提取逻辑

#### 目标报告提取 (`extract_core_content`)
从Markdown报告中提取核心内容，优先级如下：

1. **Executive Summary 章节** (首选)
   - 查找 `## 1. Executive Summary` 或 `## Executive Summary`
   - 提取该章节到下一个 `##` 之前的内容

2. **Detailed Hypothesis 章节** (次选)
   - 查找 `**Detailed Hypothesis**`
   - 提取到下一个 `---` 之前的内容

3. **前2000字符** (兜底策略)
   - 如果以上都未找到，直接截取报告前2000字符

#### 用于评估的文本长度
- **Embedding计算**: 前2000字符
- **LLM主观评分**: 前4000字符
- **对比评估**: 各取前2000字符

### 3. 基线文本格式
基线文本应包含以下内容（推荐格式）：
```
Title: <论文标题>

Abstract: <研究摘要，包含：背景、方法、创新点、实验设计>

Experiment Design: <实验方案>

Quality Metrics:
- Clarity: X/10
- Feasibility: X/10
- Novelty: X/10
```

---

## 📤 输出 (Output)

### 1. JSON结果文件
**路径**: `{output_dir}/{safe_name}_eval_v2.json`

**结构**:
```json
{
  "metadata": {
    "source": "报告文件名",
    "timestamp": "2025-12-03T15:43:21"
  },
  "metrics": {
    "objective": {
      "Fluency_Score": 0.8,  // 0-1, LLM评估的文本流畅性
      "Novelty_Metrics": {
        "HD (Historical Dissimilarity)": 0.45,      // 与历史论文的差异度
        "CD (Contemporary Dissimilarity)": 0.32,    // 与当代论文的差异度
        "CI (Contemporary Impact)": 2.5,            // 相似当代论文的平均影响力(log(citations))
        "ON (Overall Novelty)": 4.92,               // 综合新颖性 = HD × (CI+1) / CD
        "Stats": {
          "Past_Neighbors_Found": 234,
          "Contemp_Neighbors_Found": 156
        }
      }
    },
    "subjective_llm": {
      "Novelty": 8,        // 1-10, 新颖性
      "Significance": 7,    // 1-10, 重要性
      "Effectiveness": 6,   // 1-10, 有效性
      "Clarity": 7,         // 1-10, 清晰度
      "Feasibility": 6,     // 1-10, 可行性
      "Reasoning": "简要理由说明"
    }
  },
  "comparison": {  // 可选，仅当提供baseline时
    "baseline_metrics": {
      "Fluency_Score": 0.8,
      "Novelty_Metrics": {...}
    },
    "llm_comparison": {
      "Winner": "A" | "B" | "Tie",
      "Reason": "胜出原因",
      "A_Strengths": "系统A优势",
      "B_Strengths": "系统B优势"
    }
  }
}
```

### 2. Markdown中文分析报告
**路径**: `{output_dir}/{safe_name}_analysis_report.md`

**结构**:
```markdown
# 科学猜想生成系统对比评估报告

## 1. 核心结论 (Executive Summary)
[1-2句话总结胜负和关键原因]

## 2. 详细得分对比 (Detailed Comparison)
| 指标 | System A (Ours) | System B (Baseline) |
|------|-----------------|---------------------|
| 流畅性分数 | 0.8 | 0.8 |
| 新颖性指标-HD | 0.45 | 0.38 |
| 主观LLM评分-新颖性 | 8 | - |
| ... | ... | ... |

## 3. 深度分析 (In-depth Analysis)
### System A 表现分析
- 优势: ...
- 劣势: ...

### System B 表现分析
- 优势: ...
- 劣势: ...

### 胜负关键因素
[分析决定性因素]

## 4. 改进建议 (Actionable Recommendations)
1. [建议1]
2. [建议2]
3. [建议3]
```

---

## 🔬 评估算法详解

### 1. 流畅性评分 (Fluency Score)
**算法**: LLM as Judge
- 输入: 文本前1000字符
- 方法: Qwen-Max评估语法流畅性和逻辑连贯性
- 输出: 1-10分，归一化为0-1

### 2. 新颖性指标 (Novelty Metrics)

#### HD (Historical Dissimilarity) - 历史差异度
- **定义**: 与历史论文（<2022年）的平均语义距离
- **计算步骤**:
  1. 用embedding模型编码生成的摘要
  2. 在向量库中检索Top-500相似论文
  3. 筛选出年份<2022的论文
  4. 计算Top-5历史论文的平均dissimilarity: `1 - cosine_similarity`
- **范围**: 0-1 (越大越新颖)

#### CD (Contemporary Dissimilarity) - 当代差异度
- **定义**: 与当代论文（≥2022年）的平均语义距离
- **计算步骤**:
  1. 从Top-500检索结果中筛选年份≥2022的论文
  2. 计算Top-5当代论文的平均dissimilarity
- **范围**: 0-1 (越大越新颖，但也可能表示脱离主流)

#### CI (Contemporary Impact) - 当代影响力
- **定义**: 与生成摘要相似的当代论文的平均引用数（对数尺度）
- **计算步骤**:
  1. 取Top-5相似当代论文
  2. 获取其引用数，计算平均值
  3. 进行log转换: `log(1 + avg_citations)`
- **意义**: 如果生成的想法与高引论文相似，说明方向有潜力

#### ON (Overall Novelty) - 综合新颖性
- **公式**: `ON = HD × (CI + 1) / CD`
- **解释**:
  - 分子 `HD × (CI+1)`: 与历史差异大 + 当代影响力高 → 高分
  - 分母 `CD`: 与当代差异太大会降低分数（避免天马行空）
  - **理想状态**: HD高（历史创新）、CD适中（贴近前沿）、CI高（方向有影响力）

### 3. 主观LLM评分 (Subjective Metrics)
**算法**: LLM as Judge (Qwen-Max, temperature=0.2)
- 输入: 报告前4000字符
- 评估维度:
  1. **Novelty**: 与现有文献相比的原创性
  2. **Significance**: 成功后的潜在影响力
  3. **Effectiveness**: 方法论的证明能力
  4. **Clarity**: 写作清晰度和科学严谨性
  5. **Feasibility**: 当前技术条件下的可行性
- 输出: 每个维度1-10分 + 理由说明

### 4. 对比评估 (Comparative Evaluation)
**算法**: Head-to-Head LLM Judge
- 输入: System A前2000字符 + System B前2000字符
- 评估重点: 新颖性和科学严谨性
- 输出: 
  - Winner: A/B/Tie
  - Reason, A_Strengths, B_Strengths

---

## 💡 使用示例

### 单独评估（无对比）
```bash
python run_evaluation.py \
  --report_path "Scientific_Hypothesis_Reports/my_report.md"
```

### 对比评估
```bash
python run_evaluation.py \
  --report_path "Scientific_Hypothesis_Reports/my_report.md" \
  --comparison_text "$(cat baseline_system_output.txt)"
```

### 批量评估（配合自动化脚本）
```bash
python batch_comparative_evaluation.py \
  --our_system_reports "Scientific_Hypothesis_Reports/*.md" \
  --baseline_system "Virtual-Scientists" \
  --topics_file "research_questions.txt"
```

---

## ⚠️ 注意事项

1. **元数据缺失**: 如果 `final_custom_kg_papers.json` 不存在或损坏，HD/CD/CI将无法计算，只返回Fluency Score
2. **向量库路径**: 确保 `vdb_path` 下存在 `paper/abstract/` 或 `abstract/` 子目录
3. **API配置**: 需要设置 `QWEN_API_KEY` 和 `QWEN_API_BASE_URL` 环境变量
4. **文本长度**: 评估系统只使用报告的前部分内容，确保核心信息在前2000字符内

---

## 📈 性能优化建议

1. **加速Embedding计算**: 使用本地embedding模型替代API调用
2. **缓存向量库查询**: 对于相同文本不重复检索
3. **并行批量评估**: 多个报告可以并行处理
4. **LLM调用优化**: 使用更快的模型（如Qwen-Plus）进行非关键评估

