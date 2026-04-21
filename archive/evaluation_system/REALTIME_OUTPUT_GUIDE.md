# 实时输出显示指南

## 概述

两个批量运行脚本（`batch_run_virsci.py` 和 `batch_run_coi.py`）都已优化为实时显示程序运行输出。

## 实现原理

### 1. 禁用Python输出缓冲

```python
os.environ['PYTHONUNBUFFERED'] = '1'
```

这确保Python不会缓冲标准输出，所有输出都会立即显示。

### 2. 使用Popen进行实时流处理

```python
process = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,              # 行缓冲模式
    universal_newlines=True # 使用文本模式
)
```

关键参数说明：
- `bufsize=1`: 行缓冲模式，每行输出都会立即处理
- `universal_newlines=True`: 自动处理不同系统的换行符
- `stderr=subprocess.STDOUT`: 将错误流合并到标准输出

### 3. 实时读取和刷新

```python
for line in process.stdout:
    # 实时输出到控制台
    sys.stdout.write(line)
    sys.stdout.flush()      # 立即刷新缓冲区
    
    # 同时写入报告文件
    report_f.write(line)
    report_f.flush()        # 立即刷新文件缓冲区
```

关键点：
- 使用 `sys.stdout.write()` 而不是 `print()` 以避免额外的换行
- 每行都调用 `flush()` 确保立即显示
- 同时将输出保存到文件

## 实时输出示例

### Virtual Scientists运行

```
============================================================
📊 进度: [1/513] (0.2%)
============================================================
🔬 问题ID: HAGEN_Homophily-Aware_Graph_Convolutional_Recurrent_Network_for_Crime_Forecasting_RQ_3
❓ 问题文本: How can we integrate spatial crime dependencies with temporal dynamics...
============================================================

Initializing PlatformQwen with Real Data...
2025-12-10 16:39:45.427 | INFO | agentscope.manager._model:load_model_configs:115 - Load configs for model wrapper: qwen_plus, qwen_max, qwen_embedding
2025-12-10 16:39:45.434 | INFO | agentscope.models.model:__init__:203 - Initialize model by configuration [qwen_plus]
...
[更多实时输出]
...
============================================================
✓ 成功 (耗时: 45.32秒)

📈 当前统计: 成功 1/1, 失败 0/1
```

### CoI-Agent运行

```
============================================================
📊 进度: [1/513] (0.2%)
============================================================
🔬 问题ID: HAGEN_Homophily-Aware_Graph_Convolutional_Recurrent_Network_for_Crime_Forecasting_RQ_3
❓ 问题文本: How can we integrate spatial crime dependencies with temporal dynamics...
============================================================

🚀 Launching CoI-Agent with Real VDB on Topic: 'How can we integrate...'
📁 VDB Path: /root/autodl-tmp/Myexamples/vdb/camel_faiss_storage
begin to generate idea and experiment of topic How can we integrate...
...
[更多实时输出]
...
============================================================
✓ 成功 (耗时: 45.32秒)

📈 当前统计: 成功 1/1, 失败 0/1
```

## 输出特性

### ✓ 完全实时
- 每一行输出都立即显示在控制台
- 无延迟，无缓冲

### ✓ 双重保存
- 同时显示在控制台
- 同时保存到报告文件（`.txt`）

### ✓ 完整记录
- 所有输出都被记录
- 包括标准输出和错误输出
- 便于后续分析和调试

## 性能考虑

### 优点
- 实时反馈，用户可以看到程序进度
- 便于调试和问题诊断
- 完整的运行日志

### 缺点
- 频繁的I/O操作（写入文件）
- 可能对性能有轻微影响（通常可以忽略）

### 优化建议
如果需要提高性能，可以：
1. 增加缓冲区大小（但会失去实时性）
2. 异步写入文件（增加复杂性）
3. 定期批量写入（平衡实时性和性能）

## 故障排除

### 问题：输出不显示

**原因**：
1. 子进程的输出缓冲未禁用
2. 文件描述符被重定向

**解决方案**：
1. 确保设置了 `PYTHONUNBUFFERED=1`
2. 检查是否使用了 `> /dev/null` 重定向
3. 使用 `script` 命令记录终端会话

### 问题：输出顺序混乱

**原因**：
1. 多线程输出竞争
2. 缓冲区未正确刷新

**解决方案**：
1. 确保每行都调用了 `flush()`
2. 避免多线程并发输出
3. 使用锁保护输出操作

### 问题：文件中的输出不完整

**原因**：
1. 程序异常终止
2. 文件缓冲未刷新

**解决方案**：
1. 确保异常处理中也刷新了文件
2. 在程序结束前刷新所有缓冲区
3. 使用 `with` 语句自动关闭文件

## 相关文件

- **Virtual Scientists脚本**: `/root/autodl-tmp/Myexamples/evaluation_system/batch_run_virsci.py`
- **CoI-Agent脚本**: `/root/autodl-tmp/Myexamples/evaluation_system/batch_run_coi.py`
- **Virtual Scientists指南**: `/root/autodl-tmp/Myexamples/evaluation_system/VIRSCI_LOGS_STRUCTURE.md`
- **CoI-Agent指南**: `/root/autodl-tmp/Myexamples/evaluation_system/BATCH_RUN_COI_README.md`

## 使用建议

### 在终端中运行
```bash
# 直接运行，查看实时输出
python /root/autodl-tmp/Myexamples/evaluation_system/batch_run_virsci.py

# 或使用screen/tmux保持会话
screen -S batch_run
python /root/autodl-tmp/Myexamples/evaluation_system/batch_run_virsci.py

# 或使用nohup后台运行（同时保存输出）
nohup python /root/autodl-tmp/Myexamples/evaluation_system/batch_run_virsci.py > batch_run.log 2>&1 &
```

### 监控运行进度
```bash
# 在另一个终端查看实时日志
tail -f batch_run.log

# 或查看输出目录
ls -lh /root/autodl-tmp/Myexamples/evaluation_system/batch_results/virsci/
```

### 查看完整报告
```bash
# 查看汇总报告
cat /root/autodl-tmp/Myexamples/evaluation_system/batch_results/virsci/summary.json

# 查看特定问题的报告
cat /root/autodl-tmp/Myexamples/evaluation_system/batch_results/virsci/{question_id}.txt
```
