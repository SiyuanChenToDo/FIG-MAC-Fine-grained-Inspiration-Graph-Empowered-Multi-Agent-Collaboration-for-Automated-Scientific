# FIG-MAC Kimi 批量运行器

使用 Moonshot Kimi K2 模型批量运行 FIG-MAC 假设生成

## 配置信息

- **API**: Moonshot (Kimi)
- **模型**: `kimi-k2-5` (Kimi K2.5)
- **API Key**: `sk-kimi-DqvKI9FbhJtOp0GWTuBW6D9VL4LzmoojwwWEchqLueN3Ev6qhoJf1feiOpQM486B`
- **Base URL**: `https://api.moonshot.cn/v1`

## 文件说明

| 文件 | 说明 |
|------|------|
| `kimi_batch_runner.py` | 批量运行主脚本 |
| `hypothesis_society_kimi.py` | Kimi 版本的 FIG-MAC (修改自原 demo) |
| `run_kimi_batch.sh` | 启动脚本 |

## 使用方法

### 1. 运行全部 150 个问题

```bash
cd /root/autodl-tmp
bash Myexamples/kimi_batch_runner/run_kimi_batch.sh 0 150
```

### 2. 分批运行 (推荐)

由于处理 150 个问题需要很长时间，建议分批运行：

```bash
# 第一批：0-30
bash Myexamples/kimi_batch_runner/run_kimi_batch.sh 0 30

# 第二批：30-60
bash Myexamples/kimi_batch_runner/run_kimi_batch.sh 30 60

# 第三批：60-90
bash Myexamples/kimi_batch_runner/run_kimi_batch.sh 60 90

# 第四批：90-120
bash Myexamples/kimi_batch_runner/run_kimi_batch.sh 90 120

# 第五批：120-150
bash Myexamples/kimi_batch_runner/run_kimi_batch.sh 120 150
```

### 3. 直接运行 Python 脚本

```bash
cd /root/autodl-tmp

# 全部运行
python Myexamples/kimi_batch_runner/kimi_batch_runner.py \
    --start-idx 0 \
    --end-idx 150

# 只运行前 5 个测试
python Myexamples/kimi_batch_runner/kimi_batch_runner.py \
    --start-idx 0 \
    --end-idx 5
```

## 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--start-idx` | 0 | 开始索引 (0-based) |
| `--end-idx` | None | 结束索引 (exclusive) |
| `--max-iterations` | 3 | 最大迭代次数 |
| `--quality-threshold` | 8.0 | 质量阈值 (1-10) |
| `--delay` | 2.0 | 每个问题间的延迟 (秒) |

## 输出目录

结果保存在：`Myexamples/kimi_batch_results/`

```
Myexamples/kimi_batch_results/
├── reports/              # 生成的假设报告 (markdown)
├── progress.json         # 进度记录
└── final_report.json     # 最终报告
```

## 注意事项

1. **API 限制**: Kimi API 有速率限制，脚本已设置 2 秒延迟
2. **运行时间**: 每个问题约 5-10 分钟，150 个问题约 12-25 小时
3. **进度保存**: 每完成一个问题会自动保存进度到 `progress.json`
4. **断点续跑**: 如果中断，可以查看 `progress.json` 确定已完成的数量，然后从断点继续

## 与原始 Qwen 版本的区别

| 特性 | Qwen 版本 | Kimi 版本 |
|------|-----------|-----------|
| API | DashScope | Moonshot |
| 模型 | qwen-max / qwen-plus | kimi-k2-0711-preview |
| 上下文窗口 | 32K | 256K |
| Token 限制 | 8192 | 8192 |

## 成本估算

Kimi K2 价格：
- 输入: ~12元/百万 tokens
- 输出: ~60元/百万 tokens

单个假设生成约消耗 50K-100K tokens，150 个问题预计成本约 500-1000 元。
