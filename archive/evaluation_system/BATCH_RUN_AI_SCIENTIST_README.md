# AI-Scientist-v2 批量运行脚本使用指南

## 概述

`batch_run_ai_scientist.py` 是一个自动化脚本，用于批量运行AI-Scientist-v2项目，处理 `all_research_questions.json` 中的所有研究问题，并将结果保存到规范的输出目录。

## 脚本位置

```
/root/autodl-tmp/Myexamples/evaluation_system/batch_run_ai_scientist.py
```

## 功能特性

### 1. 自动化批量处理
- 自动加载 `all_research_questions.json` 中的所有问题
- 逐个运行AI-Scientist-v2的 `run_comparative.py`
- 支持中断恢复（Ctrl+C中断后可查看已完成的结果）

### 2. 实时进度显示
```
============================================================
📊 进度: [1/513] (0.2%)
============================================================
🔬 问题ID: HAGEN_Homophily-Aware_Graph_Convolutional_Recurrent_Network_for_Crime_Forecasting_RQ_3
❓ 问题文本: How can we integrate spatial crime dependencies with temporal dynamics...
============================================================
```

### 3. 实时统计信息
每个问题完成后显示当前统计：
```
📈 当前统计: 成功 1/1, 失败 0/1
```

### 4. 完整的输出管理
- 运行报告：每个问题一个 `.txt` 文件，包含完整的运行日志
- 结果文件：每个问题的JSON结果文件
- 汇总报告：`summary.json` 包含所有问题的运行统计

## 输出目录结构

```
/root/autodl-tmp/Myexamples/evaluation_system/batch_results/ai_scientist/
├── summary.json                                    # 汇总报告
├── {question_id_1}.txt                            # 运行报告
├── {question_id_2}.txt
├── ...
└── results/                                        # 结果目录
    ├── {question_id_1}/
    │   ├── result.json                            # AI-Scientist生成的结果
    │   ├── ideas.json                             # 生成的想法列表
    │   └── workshop_topic.md                      # Workshop描述
    ├── {question_id_2}/
    │   ├── result.json
    │   ├── ideas.json
    │   └── workshop_topic.md
    └── ...
```

## 使用方法

### 基本运行

```bash
python /root/autodl-tmp/Myexamples/evaluation_system/batch_run_ai_scientist.py
```

### 预期输出

#### 开始信息
```
============================================================
AI-Scientist-v2 批量运行脚本
============================================================
✓ 输出目录已准备: /root/autodl-tmp/Myexamples/evaluation_system/batch_results/ai_scientist
✓ 日志目录已准备: /root/autodl-tmp/Myexamples/evaluation_system/batch_results/ai_scientist/logs
✓ 成功加载 513 个问题

============================================================
🚀 开始批量运行 513 个研究问题的对比实验
============================================================
```

#### 运行过程
```
============================================================
📊 进度: [1/513] (0.2%)
============================================================
🔬 问题ID: HAGEN_Homophily-Aware_Graph_Convolutional_Recurrent_Network_for_Crime_Forecasting_RQ_3
❓ 问题文本: How can we integrate spatial crime dependencies with temporal dynamics...
============================================================

================================================================================
🔬 AI-Scientist-v2 Comparative Runner
================================================================================
Topic: How can we integrate spatial crime dependencies with temporal dynamics...
Model: qwen-plus (via Qwen API)
API Key: sk-17fc6cc742c844a...
Base URL: https://dashscope.aliyuncs.com/compatible-mode/v1
================================================================================

✅ LLM Client created: qwen-plus (via Qwen API at https://dashscope.aliyuncs.com/compatible-mode/v1)

🚀 Starting idea generation...
   Max generations: 3
   Reflections per idea: 3

[AI-Scientist运行日志...]

✅ Idea generation completed!
   Generated 3 ideas
   Selected best idea: Spatiotemporal Graph Transformer with Adaptive Temporal Point Processes

✅ Result saved to: /root/autodl-tmp/Myexamples/evaluation_system/batch_results/ai_scientist/results/HAGEN_Homophily-Aware.../result.json

================================================================================
Final Idea:
================================================================================
**Title:** Spatiotemporal Graph Transformer with Adaptive Temporal Point Processes
**Hypothesis:** ...
[想法详情]
================================================================================

============================================================
✓ 成功 (耗时: 120.45秒)

📈 当前统计: 成功 1/1, 失败 0/1
```

#### 完成信息
```
============================================================
✅ 批量运行完成!
============================================================

📊 最终统计:
  总数:   513
  成功:   510 ✓
  失败:   3 ✗
  成功率: 99.42%

📁 输出位置:
  - 运行报告:   /root/autodl-tmp/Myexamples/evaluation_system/batch_results/ai_scientist/*.txt
  - 结果文件:   /root/autodl-tmp/Myexamples/evaluation_system/batch_results/ai_scientist/results/{question_id}/result.json
  - 汇总报告:   /root/autodl-tmp/Myexamples/evaluation_system/batch_results/ai_scientist/summary.json

============================================================
```

## 输出文件说明

### 1. 运行报告 (`{question_id}.txt`)

包含内容：
- 问题ID和问题文本
- 运行时间戳
- AI-Scientist程序的实时输出
- 运行耗时和返回码

### 2. 结果文件 (`results/{question_id}/result.json`)

AI-Scientist-v2生成的JSON结果，包含：
- `idea`: 生成的研究想法（字符串格式）
- `idea_dict`: 最佳想法的详细字典
- `all_ideas`: 前3个生成的想法
- `topic`: 研究问题
- `timestamp`: 生成时间戳

### 3. 想法列表 (`results/{question_id}/ideas.json`)

包含所有生成的想法的详细信息，每个想法包括：
- `Title`: 想法标题
- `Short Hypothesis`: 简短假设
- `Abstract`: 摘要
- `Related Work`: 相关工作
- `Experiments`: 提议的实验
- 其他元数据

### 4. Workshop描述 (`results/{question_id}/workshop_topic.md`)

从研究问题生成的workshop描述，用于指导想法生成过程。

### 5. 汇总报告 (`summary.json`)

```json
{
  "总数": 513,
  "成功": 510,
  "失败": 3,
  "成功率": "99.42%",
  "运行时间": "2024-12-10T17:30:00",
  "输出目录": "/root/autodl-tmp/Myexamples/evaluation_system/batch_results/ai_scientist",
  "结果目录": "/root/autodl-tmp/Myexamples/evaluation_system/batch_results/ai_scientist/results",
  "详情": [
    {
      "索引": 1,
      "问题ID": "HAGEN_Homophily-Aware...",
      "状态": "成功",
      "结果路径": "/root/autodl-tmp/Myexamples/evaluation_system/batch_results/ai_scientist/results/HAGEN_Homophily-Aware.../result.json"
    },
    ...
  ]
}
```

## 中断和恢复

### 中断脚本
按 `Ctrl+C` 可以安全地中断脚本。脚本会：
1. 保存已完成的结果到 `summary.json`
2. 显示当前的统计信息
3. 优雅地退出

### 恢复运行
重新运行脚本时，会覆盖之前的结果。如果需要保留之前的结果，请先备份输出目录。

## 脚本参数

AI-Scientist-v2脚本使用以下默认参数：

- `--max_generations 3`: 最大想法生成数（推荐3-5）
- `--num_reflections 3`: 每个想法的反思轮数（推荐3-5，最少2）

如果需要调整这些参数，可以修改脚本中的以下行：

```python
cmd = [
    "python", RUN_SCRIPT,
    "--topic", question_text,
    "--save_file", save_dir,
    "--output_file", "result.json",
    "--max_generations", "3",      # 修改这里
    "--num_reflections", "3"       # 修改这里
]
```

## 故障排除

### 问题：脚本无法找到AI-Scientist-v2项目

**解决方案**：
1. 确保AI-Scientist-v2项目路径正确：`/root/autodl-tmp/Myexamples/comparative_experiments/AI-Scientist-v2/`
2. 检查 `run_comparative.py` 文件是否存在

### 问题：某个问题运行失败

**解决方案**：
1. 查看对应的 `.txt` 运行报告，了解失败原因
2. 检查API密钥是否正确设置
3. 检查网络连接是否正常
4. 检查VDB路径是否正确

### 问题：运行速度很慢

**原因**：
- AI-Scientist-v2需要调用LLM API进行多轮反思
- 每个问题可能需要60-180秒
- 总运行时间取决于问题数量和网络速度

**优化建议**：
- 确保网络连接稳定
- 检查API配额是否充足
- 考虑减少 `--max_generations` 和 `--num_reflections` 的值

### 问题：内存不足

**原因**：
- 长时间运行导致内存累积

**解决方案**：
1. 分批运行（修改脚本只处理部分问题）
2. 定期重启脚本
3. 增加系统内存

## 与其他脚本的对比

| 功能 | Virtual Scientists | CoI-Agent | AI-Scientist-v2 |
|------|-------------------|-----------|-----------------|
| 脚本位置 | `batch_run_virsci.py` | `batch_run_coi.py` | `batch_run_ai_scientist.py` |
| 输出目录 | `batch_results/virsci/` | `batch_results/coi/` | `batch_results/ai_scientist/` |
| 结果格式 | `*_dialogue.log` | `result.json` | `result.json` + `ideas.json` |
| 平均耗时/问题 | 30-60秒 | 30-60秒 | 60-180秒 |
| 进度显示 | ✓ | ✓ | ✓ |
| 实时统计 | ✓ | ✓ | ✓ |
| 中断恢复 | ✓ | ✓ | ✓ |

## 后续处理

### 提取想法文本

从 `result.json` 中提取 `idea` 字段用于评估：

```python
import json

with open("result.json", "r") as f:
    result = json.load(f)
    idea_text = result["idea"]
    print(idea_text)
```

### 对比评估

使用评估工具对三个系统的结果进行对比：

```bash
python /root/autodl-tmp/Myexamples/evaluation_system/batch_evaluation_tools/sample_and_evaluate.py \
    --virsci_dir "batch_results/virsci/logs" \
    --coi_dir "batch_results/coi/results" \
    --ai_scientist_dir "batch_results/ai_scientist/results" \
    --output_dir "evaluation_results"
```

## 相关文件

- **Virtual Scientists脚本**: `/root/autodl-tmp/Myexamples/evaluation_system/batch_run_virsci.py`
- **CoI-Agent脚本**: `/root/autodl-tmp/Myexamples/evaluation_system/batch_run_coi.py`
- **问题文件**: `/root/autodl-tmp/Myexamples/evaluation_system/batch_results/ours/all_research_questions.json`
- **评估工具**: `/root/autodl-tmp/Myexamples/evaluation_system/batch_evaluation_tools/`
- **实时输出指南**: `/root/autodl-tmp/Myexamples/evaluation_system/REALTIME_OUTPUT_GUIDE.md`
