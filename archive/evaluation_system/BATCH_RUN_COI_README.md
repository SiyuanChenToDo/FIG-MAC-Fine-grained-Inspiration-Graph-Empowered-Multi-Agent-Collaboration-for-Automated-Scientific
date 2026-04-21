# CoI-Agent 批量运行脚本使用指南

## 概述

`batch_run_coi.py` 是一个自动化脚本，用于批量运行CoI-Agent项目，处理 `all_research_questions.json` 中的所有研究问题，并将结果保存到规范的输出目录。

## 脚本位置

```
/root/autodl-tmp/Myexamples/evaluation_system/batch_run_coi.py
```

## 功能特性

### 1. 自动化批量处理
- 自动加载 `all_research_questions.json` 中的所有问题
- 逐个运行CoI-Agent的 `run_comparative.py`
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
/root/autodl-tmp/Myexamples/evaluation_system/batch_results/coi/
├── summary.json                                    # 汇总报告
├── {question_id_1}.txt                            # 运行报告
├── {question_id_2}.txt
├── ...
└── results/                                        # 结果目录
    ├── {question_id_1}/
    │   └── result.json                            # CoI-Agent生成的结果
    ├── {question_id_2}/
    │   └── result.json
    └── ...
```

## 使用方法

### 基本运行

```bash
python /root/autodl-tmp/Myexamples/evaluation_system/batch_run_coi.py
```

### 预期输出

#### 开始信息
```
============================================================
CoI-Agent 批量运行脚本
============================================================
✓ 输出目录已准备: /root/autodl-tmp/Myexamples/evaluation_system/batch_results/coi
✓ 日志目录已准备: /root/autodl-tmp/Myexamples/evaluation_system/batch_results/coi/logs
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

[CoI-Agent运行日志...]

============================================================
✓ 成功 (耗时: 45.32秒)

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
  - 运行报告:   /root/autodl-tmp/Myexamples/evaluation_system/batch_results/coi/*.txt
  - 结果文件:   /root/autodl-tmp/Myexamples/evaluation_system/batch_results/coi/results/{question_id}/result.json
  - 汇总报告:   /root/autodl-tmp/Myexamples/evaluation_system/batch_results/coi/summary.json

============================================================
```

## 输出文件说明

### 1. 运行报告 (`{question_id}.txt`)

包含内容：
- 问题ID和问题文本
- 运行时间戳
- CoI-Agent程序的实时输出
- 运行耗时和返回码

### 2. 结果文件 (`results/{question_id}/result.json`)

CoI-Agent生成的JSON结果，包含：
- `idea`: 生成的研究想法（字符串格式）
- `idea_dict`: 原始想法字典（如果有）
- `experiment`: 实验设计
- `related_experiments`: 相关实验
- `entities`: 提取的实体
- `idea_chain`: 想法链
- `ideas`: 多个想法
- `trend`: 趋势分析
- `future`: 未来方向
- `year`: 年份信息
- `human`: 人类相关信息

### 3. 汇总报告 (`summary.json`)

```json
{
  "总数": 513,
  "成功": 510,
  "失败": 3,
  "成功率": "99.42%",
  "运行时间": "2024-12-10T17:30:00",
  "输出目录": "/root/autodl-tmp/Myexamples/evaluation_system/batch_results/coi",
  "结果目录": "/root/autodl-tmp/Myexamples/evaluation_system/batch_results/coi/results",
  "详情": [
    {
      "索引": 1,
      "问题ID": "HAGEN_Homophily-Aware...",
      "状态": "成功",
      "结果路径": "/root/autodl-tmp/Myexamples/evaluation_system/batch_results/coi/results/HAGEN_Homophily-Aware.../result.json"
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

## 故障排除

### 问题：脚本无法找到CoI-Agent项目

**解决方案**：
1. 确保CoI-Agent项目路径正确：`/root/autodl-tmp/Myexamples/comparative_experiments/CoI-Agent/`
2. 检查 `run_comparative.py` 文件是否存在

### 问题：某个问题运行失败

**解决方案**：
1. 查看对应的 `.txt` 运行报告，了解失败原因
2. 检查API密钥是否正确设置
3. 检查网络连接是否正常

### 问题：运行速度很慢

**原因**：
- CoI-Agent需要调用LLM API，每个问题可能需要30-60秒
- 总运行时间取决于问题数量和网络速度

**优化建议**：
- 确保网络连接稳定
- 检查API配额是否充足

## 与Virtual Scientists脚本的对比

| 功能 | Virtual Scientists | CoI-Agent |
|------|-------------------|-----------|
| 脚本位置 | `batch_run_virsci.py` | `batch_run_coi.py` |
| 输出目录 | `batch_results/virsci/` | `batch_results/coi/` |
| 日志位置 | `virsci/logs/{question_id}/` | `coi/results/{question_id}/` |
| 日志格式 | `*_dialogue.log` | `result.json` |
| 进度显示 | ✓ | ✓ |
| 实时统计 | ✓ | ✓ |
| 中断恢复 | ✓ | ✓ |

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

使用评估工具对CoI-Agent和Virtual Scientists的结果进行对比：

```bash
python /root/autodl-tmp/Myexamples/evaluation_system/batch_evaluation_tools/sample_and_evaluate.py \
    --virsci_dir "batch_results/virsci/logs" \
    --coi_dir "batch_results/coi/results" \
    --output_dir "evaluation_results"
```

## 相关文件

- **Virtual Scientists脚本**: `/root/autodl-tmp/Myexamples/evaluation_system/batch_run_virsci.py`
- **问题文件**: `/root/autodl-tmp/Myexamples/evaluation_system/batch_results/ours/all_research_questions.json`
- **评估工具**: `/root/autodl-tmp/Myexamples/evaluation_system/batch_evaluation_tools/`
