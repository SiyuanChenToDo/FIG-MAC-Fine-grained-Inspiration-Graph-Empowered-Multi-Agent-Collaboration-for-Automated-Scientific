# 批量运行脚本总结

## 概述

已为三个对比项目创建了完整的批量运行脚本，用于处理 `all_research_questions.json` 中的所有研究问题。

## 三个批量运行脚本

### 1. Virtual Scientists 批量运行脚本

**脚本位置**：
```
/root/autodl-tmp/Myexamples/evaluation_system/batch_run_virsci.py
```

**功能**：
- 批量运行Virtual Scientists的 `run_comparative.py`
- 自动收集生成的日志文件（`*_dialogue.log`）
- 保存到规范的日志目录

**输出目录**：
```
/root/autodl-tmp/Myexamples/evaluation_system/batch_results/virsci/
├── summary.json
├── {question_id}.txt
└── logs/{question_id}/*.log
```

**使用方法**：
```bash
python /root/autodl-tmp/Myexamples/evaluation_system/batch_run_virsci.py
```

**文档**：
- `/root/autodl-tmp/Myexamples/evaluation_system/VIRSCI_LOGS_STRUCTURE.md`

---

### 2. CoI-Agent 批量运行脚本

**脚本位置**：
```
/root/autodl-tmp/Myexamples/evaluation_system/batch_run_coi.py
```

**功能**：
- 批量运行CoI-Agent的 `run_comparative.py`
- 保存JSON格式的结果文件
- 生成完整的运行报告

**输出目录**：
```
/root/autodl-tmp/Myexamples/evaluation_system/batch_results/coi/
├── summary.json
├── {question_id}.txt
└── results/{question_id}/result.json
```

**使用方法**：
```bash
python /root/autodl-tmp/Myexamples/evaluation_system/batch_run_coi.py
```

**文档**：
- `/root/autodl-tmp/Myexamples/evaluation_system/BATCH_RUN_COI_README.md`

---

### 3. AI-Scientist-v2 批量运行脚本

**脚本位置**：
```
/root/autodl-tmp/Myexamples/evaluation_system/batch_run_ai_scientist.py
```

**功能**：
- 批量运行AI-Scientist-v2的 `run_comparative.py`
- 保存JSON格式的结果和想法列表
- 生成完整的运行报告

**输出目录**：
```
/root/autodl-tmp/Myexamples/evaluation_system/batch_results/ai_scientist/
├── summary.json
├── {question_id}.txt
└── results/{question_id}/
    ├── result.json
    ├── ideas.json
    └── workshop_topic.md
```

**使用方法**：
```bash
python /root/autodl-tmp/Myexamples/evaluation_system/batch_run_ai_scientist.py
```

**文档**：
- `/root/autodl-tmp/Myexamples/evaluation_system/BATCH_RUN_AI_SCIENTIST_README.md`

---

## 功能对比表

| 功能 | Virtual Scientists | CoI-Agent | AI-Scientist-v2 |
|------|-------------------|-----------|-----------------|
| **脚本位置** | `batch_run_virsci.py` | `batch_run_coi.py` | `batch_run_ai_scientist.py` |
| **输出目录** | `batch_results/virsci/` | `batch_results/coi/` | `batch_results/ai_scientist/` |
| **结果格式** | `*_dialogue.log` | `result.json` | `result.json` + `ideas.json` |
| **平均耗时/问题** | 30-60秒 | 30-60秒 | 60-180秒 |
| **进度显示** | ✓ | ✓ | ✓ |
| **实时统计** | ✓ | ✓ | ✓ |
| **中断恢复** | ✓ | ✓ | ✓ |
| **日志收集** | ✓ | ✗ | ✗ |
| **多想法支持** | ✗ | ✗ | ✓ |

---

## 共同特性

### 1. 实时进度显示
所有脚本都显示：
- 当前处理的问题序号和总数
- 百分比进度
- 问题ID和问题文本

### 2. 实时统计信息
每个问题完成后显示：
- 成功/失败数量
- 最终成功率

### 3. 完整的输出管理
- 运行报告：每个问题一个 `.txt` 文件
- 结果文件：JSON格式的结果
- 汇总报告：`summary.json` 包含所有统计

### 4. 错误处理
- 超时检测（600秒）
- 用户中断支持（Ctrl+C）
- 异常捕获和记录

### 5. 实时输出显示
- 禁用Python输出缓冲
- 行缓冲模式的subprocess
- 每行都立即刷新

---

## 输出目录结构对比

### Virtual Scientists
```
virsci/
├── summary.json
├── {question_id_1}.txt
├── {question_id_2}.txt
└── logs/
    ├── {question_id_1}/
    │   ├── {timestamp}_1,1_dialogue.log
    │   └── {timestamp}_2,1_dialogue.log
    └── {question_id_2}/
        ├── {timestamp}_1,1_dialogue.log
        └── {timestamp}_2,1_dialogue.log
```

### CoI-Agent
```
coi/
├── summary.json
├── {question_id_1}.txt
├── {question_id_2}.txt
└── results/
    ├── {question_id_1}/
    │   └── result.json
    └── {question_id_2}/
        └── result.json
```

### AI-Scientist-v2
```
ai_scientist/
├── summary.json
├── {question_id_1}.txt
├── {question_id_2}.txt
└── results/
    ├── {question_id_1}/
    │   ├── result.json
    │   ├── ideas.json
    │   └── workshop_topic.md
    └── {question_id_2}/
        ├── result.json
        ├── ideas.json
        └── workshop_topic.md
```

---

## 运行时间估计

### 单个问题的运行时间

| 项目 | 最小 | 平均 | 最大 |
|------|------|------|------|
| Virtual Scientists | 20秒 | 45秒 | 120秒 |
| CoI-Agent | 20秒 | 45秒 | 120秒 |
| AI-Scientist-v2 | 60秒 | 120秒 | 300秒 |

### 全部513个问题的总运行时间

| 项目 | 最小 | 平均 | 最大 |
|------|------|------|------|
| Virtual Scientists | 2.8小时 | 6.4小时 | 17小时 |
| CoI-Agent | 2.8小时 | 6.4小时 | 17小时 |
| AI-Scientist-v2 | 8.5小时 | 17小时 | 42.5小时 |

---

## 使用建议

### 快速测试
如果只想快速测试，建议：
1. 先运行Virtual Scientists或CoI-Agent（更快）
2. 处理前10-20个问题
3. 检查输出质量

### 完整运行
如果要完整处理所有513个问题：
1. 使用 `screen` 或 `tmux` 保持会话
2. 在后台运行脚本
3. 定期检查进度

### 对比评估
如果要进行三个系统的对比：
1. 依次运行三个脚本
2. 使用评估工具进行对比
3. 生成对比报告

---

## 后续处理

### 提取想法文本

```python
import json

# Virtual Scientists
with open("batch_results/virsci/{question_id}.txt", "r") as f:
    content = f.read()
    # 从日志中提取想法

# CoI-Agent
with open("batch_results/coi/results/{question_id}/result.json", "r") as f:
    result = json.load(f)
    idea = result["idea"]

# AI-Scientist-v2
with open("batch_results/ai_scientist/results/{question_id}/result.json", "r") as f:
    result = json.load(f)
    idea = result["idea"]
```

### 对比评估

```bash
python /root/autodl-tmp/Myexamples/evaluation_system/batch_evaluation_tools/sample_and_evaluate.py \
    --virsci_dir "batch_results/virsci/logs" \
    --coi_dir "batch_results/coi/results" \
    --ai_scientist_dir "batch_results/ai_scientist/results" \
    --output_dir "evaluation_results"
```

---

## 相关文档

### 脚本文档
- `VIRSCI_LOGS_STRUCTURE.md` - Virtual Scientists日志结构说明
- `BATCH_RUN_COI_README.md` - CoI-Agent使用指南
- `BATCH_RUN_AI_SCIENTIST_README.md` - AI-Scientist-v2使用指南

### 通用文档
- `REALTIME_OUTPUT_GUIDE.md` - 实时输出显示指南
- `BATCH_RUN_IMPROVEMENTS.md` - 脚本改进说明

### 评估工具
- `/root/autodl-tmp/Myexamples/evaluation_system/batch_evaluation_tools/`

---

## 快速开始

### 运行所有三个脚本

```bash
# 1. Virtual Scientists
python /root/autodl-tmp/Myexamples/evaluation_system/batch_run_virsci.py

# 2. CoI-Agent
python /root/autodl-tmp/Myexamples/evaluation_system/batch_run_coi.py

# 3. AI-Scientist-v2
python /root/autodl-tmp/Myexamples/evaluation_system/batch_run_ai_scientist.py
```

### 查看结果

```bash
# 查看汇总报告
cat /root/autodl-tmp/Myexamples/evaluation_system/batch_results/virsci/summary.json
cat /root/autodl-tmp/Myexamples/evaluation_system/batch_results/coi/summary.json
cat /root/autodl-tmp/Myexamples/evaluation_system/batch_results/ai_scientist/summary.json

# 查看特定问题的结果
ls /root/autodl-tmp/Myexamples/evaluation_system/batch_results/virsci/
ls /root/autodl-tmp/Myexamples/evaluation_system/batch_results/coi/results/
ls /root/autodl-tmp/Myexamples/evaluation_system/batch_results/ai_scientist/results/
```

---

## 故障排除

### 通用问题

**问题**：脚本无法找到项目

**解决方案**：
1. 检查项目路径是否正确
2. 确保 `run_comparative.py` 文件存在
3. 检查文件权限

**问题**：API调用失败

**解决方案**：
1. 检查API密钥是否正确设置
2. 检查网络连接
3. 检查API配额

**问题**：输出不显示

**解决方案**：
1. 确保设置了 `PYTHONUNBUFFERED=1`
2. 检查是否使用了输出重定向
3. 查看错误日志

---

## 版本信息

- **创建日期**：2025-12-10
- **Python版本**：3.7+
- **依赖**：json, os, sys, subprocess, time, pathlib, datetime

---

## 联系和支持

如有问题或建议，请查看相应的脚本文档或评估工具文档。
