# Virtual Scientists 批量运行脚本

## 概述

`batch_run_virsci.py` 是一个批量运行Virtual Scientists对比实验的脚本。它会根据 `all_research_questions.json` 中的所有问题，逐个运行 `run_comparative.py`，并将结果保存到指定目录。

## 功能特性

- ✓ 自动从JSON文件加载所有研究问题
- ✓ 为每个问题创建独立的输出目录
- ✓ 捕获每次运行的标准输出和错误信息
- ✓ 记录每个问题的运行日志
- ✓ 生成汇总报告（summary.json）
- ✓ 支持超时控制（默认10分钟）
- ✓ 显示实时进度和统计信息

## 使用方法

### 基本用法

```bash
python /root/autodl-tmp/Myexamples/evaluation_system/batch_run_virsci.py
```

### 输入文件

- **问题源文件**: `/root/autodl-tmp/Myexamples/evaluation_system/batch_results/ours/all_research_questions.json`
  - 包含所有研究问题的JSON数组
  - 每个问题包含: `id`, `question`, `simplified`, `source_id`

### 运行脚本

- **脚本路径**: `/root/autodl-tmp/Myexamples/comparative_experiments/Virtual-Scientists/run_comparative.py`
  - 接受 `--topic` 参数来指定研究问题

### 输出目录

- **输出根目录**: `/root/autodl-tmp/Myexamples/evaluation_system/batch_results/virsci/`
- **每个问题的输出**: `virsci/{question_id}/`
  - `run.log`: 该问题的运行日志
  - 其他由 `run_comparative.py` 生成的文件
- **汇总报告**: `virsci/summary.json`

## 输出结构

```
virsci/
├── summary.json                          # 汇总报告
├── HAGEN_Homophily-Aware.../
│   └── run.log                          # 运行日志
├── Expert_Guided_Rule_Based.../
│   └── run.log
└── ...
```

## 汇总报告格式

```json
{
  "总数": 513,
  "成功": 510,
  "失败": 3,
  "成功率": "99.42%",
  "运行时间": "2024-12-10T16:30:00",
  "详情": [
    {
      "索引": 1,
      "问题ID": "HAGEN_Homophily-Aware...",
      "状态": "成功"
    },
    ...
  ]
}
```

## 日志格式

每个问题的 `run.log` 包含：

```
问题ID: HAGEN_Homophily-Aware...
问题文本: How can we integrate spatial crime dependencies...
运行时间: 45.23秒
返回码: 0
运行时间: 2024-12-10T16:15:30

=== 标准输出 ===
[脚本的标准输出内容]

=== 标准错误 ===
[脚本的错误输出内容]
```

## 配置参数

可以在脚本中修改以下参数：

```python
QUESTIONS_FILE = "..."      # 问题JSON文件路径
RUN_SCRIPT = "..."          # 运行脚本路径
OUTPUT_DIR = "..."          # 输出目录路径
timeout = 600               # 超时时间（秒）
```

## 注意事项

1. **API密钥**: 确保 `QWEN_API_KEY` 或 `OPENAI_COMPATIBILITY_API_KEY` 已正确设置
2. **磁盘空间**: 确保有足够的磁盘空间存储所有输出结果
3. **网络连接**: 脚本需要网络连接来调用API
4. **运行时间**: 批量运行所有问题可能需要较长时间，建议在后台运行
5. **错误处理**: 单个问题的失败不会影响其他问题的运行

## 示例

### 查看汇总报告

```bash
cat /root/autodl-tmp/Myexamples/evaluation_system/batch_results/virsci/summary.json
```

### 查看特定问题的日志

```bash
cat /root/autodl-tmp/Myexamples/evaluation_system/batch_results/virsci/HAGEN_Homophily-Aware.../run.log
```

### 统计成功率

```bash
python -c "
import json
with open('/root/autodl-tmp/Myexamples/evaluation_system/batch_results/virsci/summary.json') as f:
    data = json.load(f)
    print(f'成功: {data[\"成功\"]}/{data[\"总数\"]}')
    print(f'成功率: {data[\"成功率\"]}')
"
```

## 故障排除

### 问题：脚本无法找到问题文件

**解决方案**: 检查 `QUESTIONS_FILE` 路径是否正确，确保文件存在

### 问题：API密钥错误

**解决方案**: 设置环境变量
```bash
export QWEN_API_KEY="your-api-key"
# 或
export OPENAI_COMPATIBILITY_API_KEY="your-api-key"
```

### 问题：某些问题运行失败

**解决方案**: 查看对应的 `run.log` 文件了解失败原因

## 性能优化建议

1. 可以修改脚本以支持并行运行（使用 `multiprocessing` 或 `concurrent.futures`）
2. 可以添加重试机制来处理临时性失败
3. 可以添加进度条来更好地显示运行进度

## 许可证

与Virtual Scientists项目相同
