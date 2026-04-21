# Virtual Scientists 日志文件结构说明

## 概述

批量运行脚本 `batch_run_virsci.py` 现已支持自动收集和组织Virtual Scientists生成的日志文件，确保与评估工具完全对齐。

## 目录结构

```
/root/autodl-tmp/Myexamples/evaluation_system/batch_results/virsci/
├── summary.json                                          # 汇总报告
├── {question_id_1}.txt                                  # 运行报告
├── {question_id_2}.txt
├── ...
└── logs/                                                # 日志文件目录
    ├── {question_id_1}/                                 # 问题1的日志
    │   ├── {timestamp}_1,1_dialogue.log                # Scientist 1的对话日志
    │   └── {timestamp}_2,1_dialogue.log                # Scientist 2的对话日志
    ├── {question_id_2}/                                 # 问题2的日志
    │   ├── {timestamp}_1,1_dialogue.log
    │   └── {timestamp}_2,1_dialogue.log
    └── ...
```

## 文件说明

### 1. 运行报告 (`{question_id}.txt`)

位置：`/root/autodl-tmp/Myexamples/evaluation_system/batch_results/virsci/{question_id}.txt`

包含内容：
- 问题ID和问题文本
- 运行时间戳
- Virtual Scientists程序的实时输出
- 运行耗时和返回码

### 2. 日志文件 (`*_dialogue.log`)

位置：`/root/autodl-tmp/Myexamples/evaluation_system/batch_results/virsci/logs/{question_id}/{timestamp}_*_dialogue.log`

格式说明：
- `{timestamp}`: 运行时间戳，格式为 `YYYYMMDD_HHMMSS`
- `{team_id}`: 团队ID，通常为 `1,1` 或 `2,1`
- 文件内容：包含完整的科学猜想对话和推理过程

### 3. 汇总报告 (`summary.json`)

位置：`/root/autodl-tmp/Myexamples/evaluation_system/batch_results/virsci/summary.json`

包含内容：
```json
{
  "总数": 513,
  "成功": 510,
  "失败": 3,
  "成功率": "99.42%",
  "运行时间": "2024-12-10T16:30:00",
  "输出目录": "/root/autodl-tmp/Myexamples/evaluation_system/batch_results/virsci",
  "日志目录": "/root/autodl-tmp/Myexamples/evaluation_system/batch_results/virsci/logs",
  "详情": [
    {
      "索引": 1,
      "问题ID": "HAGEN_Homophily-Aware...",
      "状态": "成功",
      "日志路径": "/root/autodl-tmp/Myexamples/evaluation_system/batch_results/virsci/logs/HAGEN_Homophily-Aware..."
    },
    ...
  ]
}
```

## 与评估工具的对齐

### 日志提取工具

评估工具 `extract_baseline_from_log.py` 期望的日志格式：
- 文件名模式：`*_1,1_dialogue.log`
- 文件位置：任意目录（通过 `--log_dir` 参数指定）

### 使用示例

```bash
# 批量提取特定问题的日志
python /root/autodl-tmp/Myexamples/evaluation_system/batch_evaluation_tools/extract_baseline_from_log.py \
    --log_dir "/root/autodl-tmp/Myexamples/evaluation_system/batch_results/virsci/logs/{question_id}" \
    --output_dir "/root/autodl-tmp/Myexamples/evaluation_system/batch_results/virsci/extracted_baselines"

# 批量提取所有问题的日志
for question_dir in /root/autodl-tmp/Myexamples/evaluation_system/batch_results/virsci/logs/*/; do
    question_id=$(basename "$question_dir")
    python /root/autodl-tmp/Myexamples/evaluation_system/batch_evaluation_tools/extract_baseline_from_log.py \
        --log_dir "$question_dir" \
        --output_dir "/root/autodl-tmp/Myexamples/evaluation_system/batch_results/virsci/extracted_baselines/$question_id"
done
```

## 日志内容示例

### 科学猜想提取

从 `{timestamp}_1,1_dialogue.log` 中可以提取：

1. **Title**: 研究假设的标题
2. **Idea**: 核心科学猜想（摘要）
3. **Experiment**: 实验设计方案
4. **Clarity**: 清晰度评分（1-10）
5. **Feasibility**: 可行性评分（1-10）
6. **Novelty**: 新颖性评分（1-10）

### 对话过程

日志文件包含完整的多轮对话：
- 初始问题讨论
- 逐步深化的研究方向
- 最终的科学猜想JSON对象

## 注意事项

1. **时间戳匹配**：脚本使用运行时的时间戳来查找对应的日志文件，确保准确性
2. **日志完整性**：所有生成的日志文件都会被自动复制到规范目录，不会丢失
3. **文件编码**：所有日志文件使用UTF-8编码，支持中英文混合内容
4. **目录权限**：确保有足够的权限创建和写入日志目录

## 故障排除

### 问题：找不到日志文件

**原因**：时间戳不匹配或Virtual Scientists运行失败

**解决方案**：
1. 检查Virtual Scientists是否成功运行（查看运行报告中的返回码）
2. 检查 `/root/autodl-tmp/Myexamples/comparative_experiments/Virtual-Scientists/logs_qwen/` 目录中是否有新生成的文件
3. 确保时间戳格式正确（YYYYMMDD_HHMMSS）

### 问题：日志文件为空

**原因**：Virtual Scientists运行过程中出错或未完成

**解决方案**：
1. 查看运行报告（.txt文件）中的标准输出和错误信息
2. 检查API密钥是否正确设置
3. 检查网络连接是否正常

## 后续处理流程

```
批量运行脚本
    ↓
生成运行报告 (.txt)
    ↓
收集日志文件 (*_dialogue.log)
    ↓
提取基线文本 (extract_baseline_from_log.py)
    ↓
计算评估指标 (sample_and_evaluate.py)
    ↓
生成对比报告
```

## 相关文件

- **批量运行脚本**: `/root/autodl-tmp/Myexamples/evaluation_system/batch_run_virsci.py`
- **日志提取工具**: `/root/autodl-tmp/Myexamples/evaluation_system/batch_evaluation_tools/extract_baseline_from_log.py`
- **评估工具**: `/root/autodl-tmp/Myexamples/evaluation_system/batch_evaluation_tools/sample_and_evaluate.py`
- **原始日志源**: `/root/autodl-tmp/Myexamples/comparative_experiments/Virtual-Scientists/logs_qwen/`
