# CoI-Agent 集成说明

## 概述

本目录包含 CoI-Agent 的适配版本，已修改为使用用户的实际向量数据库（VDB）数据，而不是原始的 Semantic Scholar API。

## 文件说明

### 核心适配文件

1. **`searcher/coi_searcher_qwen.py`**
   - 自定义 Searcher 类，使用 CAMEL FaissStorage 进行检索
   - 替换原始的 `SementicSearcher`，使用用户的实际 VDB 数据
   - 兼容原始 `SementicSearcher` 的接口

2. **`searcher/__init__.py`**
   - 修改为自动使用 `CoISearcherQwen`（当环境变量 `COI_USE_REAL_VDB=1` 时）
   - 保持向后兼容

3. **`run_comparative.py`**
   - 对比运行脚本，用于批量评估
   - 自动配置环境变量和 API Keys
   - 输出结果到 `result.json` 和 `final_idea.txt`

## 使用方法

### 1. 单独运行 CoI-Agent

```bash
cd /root/autodl-tmp/Myexamples/comparative_experiments/CoI-Agent
python run_comparative.py --topic "您的研究问题"
```

### 2. 批量评估（集成到评估系统）

CoI-Agent 已集成到批量评估流程中，运行：

```bash
python Myexamples/evaluation_system/batch_evaluation_tools/sample_and_evaluate.py \
    --num_samples 10 \
    --output_dir Myexamples/evaluation_system/batch_results
```

系统会自动：
- 运行您的系统
- 运行 Virtual-Scientists
- 运行 CoI-Agent
- 对每个基线系统进行对比评估

## 环境变量配置

### 必需的 API Keys

- `QWEN_API_KEY` 或 `OPENAI_COMPATIBILITY_API_KEY`: Qwen API 密钥
- `QWEN_API_BASE_URL`: API 基础 URL（默认：`https://dashscope.aliyuncs.com/compatible-mode/v1`）

### LLM 模型配置

- `MAIN_LLM_MODEL`: 主 LLM 模型（默认：`gpt-4o`）
- `CHEAP_LLM_MODEL`: 廉价 LLM 模型（默认：`gpt-4o-mini`）

### VDB 配置

- `COI_USE_REAL_VDB`: 是否使用真实 VDB（默认：`1`）
- `COI_VDB_PATH`: VDB 路径（默认：`/root/autodl-tmp/Myexamples/vdb/camel_faiss_storage`）

## 输出格式

### 结果文件

- `result.json`: 完整的 CoI-Agent 输出（包含 idea, experiment, entities 等）
- `final_idea.txt`: 提取的最终假说（用于评估）

### 评估结果

评估结果保存在：
```
evaluations/
  rq_01_virsci/  # 与 Virtual-Scientists 的对比
  rq_01_coi/     # 与 CoI-Agent 的对比
```

## 与原始 CoI-Agent 的区别

1. **数据源**：
   - 原始：Semantic Scholar API
   - 适配：用户的实际 VDB（CAMEL FaissStorage）

2. **PDF 解析**：
   - 原始：下载并解析 PDF（使用 scipdf）
   - 适配：直接使用 VDB 中的 title 和 abstract（不需要 PDF）

3. **接口兼容性**：
   - 保持与原始 `SementicSearcher` 的接口兼容
   - 所有 `search_async` 和 `search_related_paper_async` 方法的行为保持一致

## 故障排除

### 问题：VDB 未初始化

**错误信息**：`Warning: VDB not initialized. Returning empty results`

**解决方案**：
1. 检查 `COI_VDB_PATH` 环境变量是否正确
2. 确认 VDB 路径存在且包含 `paper/abstract` 或 `abstract` 目录
3. 确认 CAMEL 库已正确安装

### 问题：API Key 未设置

**错误信息**：`MAIN_LLM_MODEL is not set`

**解决方案**：
1. 设置 `QWEN_API_KEY` 环境变量
2. 或在 `config.yaml` 中配置 API Keys

### 问题：导入错误

**错误信息**：`ImportError: cannot import name 'CoISearcherQwen'`

**解决方案**：
1. 确认 `searcher/coi_searcher_qwen.py` 文件存在
2. 检查 CAMEL 库是否正确安装：`pip install camel-ai`

## 评估指标

CoI-Agent 的输出会使用与 Virtual-Scientists 相同的评估指标：

- **客观指标**：
  - ON_raw (Overall Novelty - Raw)
  - ON_normalized (Overall Novelty - Normalized)
  - P (Provenance-Adjusted Novelty)
  - HD (Historical Dissimilarity)
  - CD (Contemporary Dissimilarity)
  - CI (Contemporary Impact)
  - S_src (Source Similarity)
  - U_src (Source Diversity)
  - G (Provenance Factor)

- **主观指标**：
  - Novelty
  - Significance
  - Effectiveness
  - Clarity
  - Feasibility

## 参考

- 原始 CoI-Agent 仓库：https://github.com/DAMO-NLP-SG/CoI-Agent
- 论文：Chain of Ideas: Revolutionizing Research via Novel Idea Development with LLM Agents

