# 科学灵感发现流水线说明文档

`inspire_pipeline.py` 是一个集成了语义检索、图神经网络链路预测和结构化报告生成的端到端系统。它能够根据用户输入的模糊研究主题，在知识图谱中定位起点，并预测跨领域的潜在启发关系，最终生成可供科研人员参考的灵感链路报告。

## 功能特点

1.  **语义检索定位 (Semantic Retrieval)**:
    *   使用 `SentenceTransformer` 对用户输入的 Topic/Question 进行编码。
    *   利用 `FAISS` 向量索引在 7.7 万个 Research Question 中快速找到语义最相似的起点。

2.  **跨论文链路预测 (Cross-Paper Link Prediction)**:
    *   基于 GraphStorm 训练的 RGCN 模型，利用 `INSPIRED` 边（由 LLM 构建的硬编码关系）进行推理。
    *   探索路径：`RQ(A) -> Sol(A) --[预测]--> Paper(B)`，发现潜在的跨领域启发。

3.  **结构化报告生成 (Structured Reporting)**:
    *   自动生成 Markdown 格式的报告，包含完整的推理链条、置信度评分和相关文献摘要。
    *   输出格式对下游的大模型（LLM）非常友好，可直接作为 Prompt 上下文使用。

## 使用方法

### 1. 准备环境与数据

确保您已经按照之前的步骤完成了图数据的构建和模型的训练。
需要确认以下路径存在：
*   图数据: `/root/autodl-tmp/data/graphstorm_partitioned`
*   原始数据: `/root/autodl-tmp/data/neo4j_export/*.parquet`
*   模型输出: `/root/autodl-tmp/workspace/best_models/.../infer_outputs`

### 2. 运行流水线

直接运行脚本，脚本会提示输入研究问题：

```bash
python /root/autodl-tmp/inspire_pipeline.py
```

或者直接通过命令行参数传入问题：

```bash
python /root/autodl-tmp/inspire_pipeline.py "How to improve graph neural networks efficiency?"
```

### 3. 查看结果

脚本运行结束后，会在当前目录下生成 `inspiration_report.md`。
您可以直接查看，或将其内容喂给 ChatGPT/Claude 等大模型进行进一步的润色和扩展。

## 代码结构

*   `ScientificInspirationPipeline`: 主类，负责协调各个模块。
    *   `_load_raw_data_and_build_index`: 加载数据并构建 FAISS 索引。
    *   `_load_predictions`: 加载 GraphStorm 的推理结果。
    *   `retrieve_relevant_nodes`: 阶段1 - 语义检索。
    *   `find_inspiration_paths`: 阶段2 - 图推理与路径搜索。
    *   `generate_structured_output`: 阶段3 - 生成 Markdown 报告。

## 扩展建议

*   **接入 LLM API**: 可以在 `generate_structured_output` 之后直接调用 OpenAI API，自动根据链路生成一段完整的“科学猜想”文本。
*   **更深层的图遍历**: 目前实现了 `RQ->Sol->Paper`，如果数据中包含完整的 `Paper->RQ` 映射表，可以轻松扩展到 `RQ(A)->...->RQ(B)->Sol(B)` 的完整 5 跳路径。

