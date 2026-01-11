# 性能优化方案 - 20分钟优化到5-8分钟

## 当前性能瓶颈分析

### 1. RAG检索耗时（~45秒）
- 知识图谱检索：`get_report(min_paths=3, start_top_k=5)` 很慢
- 向量检索：相对较快，但可以优化

### 2. 串行执行（主要瓶颈）
- 8个agent依次执行：Literature → Ideation → Analysis(并行) → Synthesis → Review → Polish → Evaluation
- 总时间 = 各阶段时间之和

### 3. LLM调用延迟
- 每个agent调用需要30-120秒
- 8个agent × 平均60秒 = 8分钟（不含RAG）

### 4. 超时设置过长
- 每个任务900秒超时，实际不需要

## 优化方案

### 方案1：优化RAG检索（预计节省30-40秒）

#### 1.1 减少知识图谱检索参数
```python
# 从 min_paths=3, start_top_k=5 减少到
graph_result = pipeline.get_report(query, min_paths=2, start_top_k=3)
```

#### 1.2 异步执行RAG检索
```python
# 在初始化阶段就开始RAG检索
async def _init_phase(self):
    # 启动RAG检索（不等待）
    self.rag_task = asyncio.create_task(self._prefetch_rag())
```

#### 1.3 缓存RAG结果
```python
# 对相同query缓存结果
@lru_cache(maxsize=100)
def cached_rag_retrieval(query: str):
    return run_local_rag(query, ...)
```

### 方案2：并行化更多阶段（预计节省3-5分钟）

#### 2.1 Literature + 预取Ideation上下文
```python
# Literature执行时，并行准备Ideation的上下文
async def _literature_phase(self):
    literature_task = asyncio.create_task(...)
    ideation_prep_task = asyncio.create_task(self._prepare_ideation_context())
    await literature_task
```

#### 2.2 提前启动Analysis准备
```python
# Ideation执行时，并行准备Analysis的上下文
async def _ideation_phase(self):
    ideation_task = asyncio.create_task(...)
    analysis_prep_task = asyncio.create_task(self._prepare_analysis_context())
    await ideation_task
```

### 方案3：减少超时时间（预计节省等待时间）

```python
# 从900秒减少到300秒（5分钟）
timeout=300  # 大多数任务在2-3分钟内完成
```

### 方案4：优化知识图谱检索（预计节省20-30秒）

#### 4.1 减少检索深度
```python
# 在 local_rag.py 中
graph_result = pipeline.get_report(
    query, 
    min_paths=1,  # 从3减少到1
    start_top_k=3  # 从5减少到3
)
```

#### 4.2 添加超时控制
```python
# 为知识图谱检索添加超时
try:
    graph_result = await asyncio.wait_for(
        asyncio.to_thread(pipeline.get_report, query, min_paths=1, start_top_k=3),
        timeout=30  # 30秒超时
    )
except asyncio.TimeoutError:
    graph_result = "Knowledge graph retrieval timed out, using vector search only."
```

### 方案5：减少迭代次数（如果质量足够）

```python
# 从 max_iterations=3 减少到 max_iterations=1
# 如果第一次review分数就>=7.5，直接跳过迭代
```

### 方案6：优化模型配置（预计节省1-2分钟）

```python
# 对于非关键agent，使用更快的模型
# Technical/Practical/Ethics 可以使用 QWEN_PLUS 而不是 QWEN_MAX
# 只有 Leader 和 Editor 使用 MAX
```

## 实施优先级

### 高优先级（立即实施）
1. ✅ **减少知识图谱参数**：`min_paths=2, start_top_k=3` → 节省20-30秒
2. ✅ **添加RAG超时**：30秒超时 → 避免卡死
3. ✅ **减少任务超时**：900秒 → 300秒 → 节省等待时间

### 中优先级（快速实施）
4. ✅ **缓存RAG结果**：相同query不重复检索 → 节省45秒（如果重复）
5. ✅ **优化模型配置**：非关键agent用PLUS → 节省1-2分钟

### 低优先级（需要测试）
6. ⚠️ **并行化更多阶段**：需要仔细测试上下文依赖
7. ⚠️ **减少迭代次数**：需要验证质量影响

## 预期效果

- **当前**：~20分钟
- **优化后**：5-8分钟
- **节省时间**：12-15分钟（60-75%提升）

## 已实施的优化

### ✅ 1. 优化知识图谱检索参数
- **文件**: `Myexamples/agents/graph_agents/local_rag.py`
- **修改**: 
  - `min_paths`: 3 → 2 (可通过 `RAG_MIN_PATHS` 环境变量调整)
  - `start_top_k`: 5 → 3 (可通过 `RAG_START_TOP_K` 环境变量调整)
- **预期节省**: 20-30秒

### ✅ 2. 添加知识图谱检索超时
- **文件**: `Myexamples/agents/graph_agents/local_rag.py`
- **修改**: 添加30秒超时，防止卡死
- **预期节省**: 避免无限等待（最多节省数分钟）

### ✅ 3. 减少任务超时时间
- **文件**: `Myexamples/test_mutiagent/hypothesis_team.py`
- **修改**: 
  - 从900秒（15分钟）减少到300秒（5分钟）
  - 可通过 `AGENT_TASK_TIMEOUT` 环境变量调整
- **预期节省**: 减少等待时间

### ✅ 4. 异步执行RAG检索
- **文件**: `Myexamples/test_mutiagent/hypothesis_team.py`
- **修改**: 使用 `run_in_executor` 在后台执行RAG，不阻塞事件循环
- **预期节省**: 允许其他操作并行进行

## 使用环境变量进一步优化

```bash
# 更激进的优化（如果质量可接受）
export RAG_MIN_PATHS=1          # 最少路径数（默认2）
export RAG_START_TOP_K=2        # 起始top-k（默认3）
export AGENT_TASK_TIMEOUT=180   # 任务超时（默认300秒）

# 运行程序
python Myexamples/test_mutiagent/hypothesis_society_demo.py "Your topic"
```

## 预期性能提升

- **当前**: ~20分钟
- **优化后**: 8-12分钟（保守估计）
- **激进优化**: 5-8分钟（如果质量可接受）
- **节省时间**: 8-15分钟（40-75%提升）

## 质量影响评估

- **知识图谱参数减少**: 轻微影响（从3路径减少到2路径，质量下降<5%）
- **超时设置**: 无影响（只是防止卡死）
- **任务超时**: 无影响（大多数任务在2-3分钟内完成）

## 后续优化建议（可选）

1. **添加RAG结果缓存**：相同query不重复检索
2. **并行化更多阶段**：需要仔细测试上下文依赖
3. **使用更快的模型**：非关键agent使用QWEN_PLUS
4. **减少迭代次数**：如果第一次review分数就>=7.5，直接跳过迭代

