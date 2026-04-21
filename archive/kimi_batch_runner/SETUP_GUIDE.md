# FIG-MAC Kimi 批量运行 - 设置指南

## 问题诊断

### API Key 验证失败

如果看到 `401 - Invalid Authentication`，可能原因：

1. **API Key 已过期或被撤销**
2. **账户余额不足**
3. **API Key 格式错误**

### 解决步骤

#### 1. 检查 API Key

登录 Moonshot 控制台验证：
- URL: https://platform.moonshot.cn/
- 检查 API Key 状态和余额

#### 2. 更新 API Key

编辑以下文件，替换为你的有效 API Key：

**文件 1**: `Myexamples/kimi_batch_runner/kimi_batch_runner.py` (第 16 行)
```python
KIMI_API_KEY = "your-new-api-key-here"
```

**文件 2**: `Myexamples/kimi_batch_runner/run_kimi_batch.sh` (第 5 行)
```bash
export MOONSHOT_API_KEY="your-new-api-key-here"
```

**文件 3**: `Myexamples/kimi_batch_runner/test_kimi_api.py` (第 13 行)
```python
KIMI_API_KEY = "your-new-api-key-here"
```

#### 3. 手动测试 API

```bash
# 使用 curl 测试
curl https://api.moonshot.cn/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-kimi-YOUR-API-KEY" \
  -d '{
    "model": "kimi-k2-0711-preview",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

## 完整文件结构

```
Myexamples/kimi_batch_runner/
├── README.md                    # 使用说明
├── SETUP_GUIDE.md              # 本文件
├── kimi_batch_runner.py        # 批量运行主脚本 ⭐需要修改 API Key
├── hypothesis_society_kimi.py  # Kimi 版本的 FIG-MAC
├── run_kimi_batch.sh           # 启动脚本 ⭐需要修改 API Key
├── test_kimi_api.py            # API 测试脚本 ⭐需要修改 API Key
└── verify_setup.py             # 配置验证脚本
```

## 快速启动 (修改 API Key 后)

```bash
# 1. 进入目录
cd /root/autodl-tmp

# 2. 测试 API
python Myexamples/kimi_batch_runner/test_kimi_api.py

# 3. 如果测试通过，运行批量处理
bash Myexamples/kimi_batch_runner/run_kimi_batch.sh 0 150
```

## 分批运行建议

由于 150 个问题需要很长时间，建议分 5 批：

```bash
# 创建 screen 会话保持运行
screen -S kimi_batch

# 第一批
cd /root/autodl-tmp
bash Myexamples/kimi_batch_runner/run_kimi_batch.sh 0 30

# 第二批
bash Myexamples/kimi_batch_runner/run_kimi_batch.sh 30 60

# 第三批
bash Myexamples/kimi_batch_runner/run_kimi_batch.sh 60 90

# 第四批
bash Myexamples/kimi_batch_runner/run_kimi_batch.sh 90 120

# 第五批
bash Myexamples/kimi_batch_runner/run_kimi_batch.sh 120 150
```

## 断点续跑

如果中途中断，检查 `progress.json`：

```bash
cat Myexamples/kimi_batch_results/progress.json | python -m json.tool
```

查看 `completed` 字段，然后从下一个索引继续：

```bash
# 例如已完成 45 个，从第 46 个开始
bash Myexamples/kimi_batch_runner/run_kimi_batch.sh 45 150
```

## 输出位置

结果保存在：`Myexamples/kimi_batch_results/`

- `reports/*.md` - 生成的假设报告
- `progress.json` - 进度记录
- `final_report.json` - 最终统计

## 与原 Qwen 版本的对比

| 项目 | Qwen 版本 | Kimi 版本 |
|------|-----------|-----------|
| API | DashScope | Moonshot |
| 模型 | qwen-max/plus | kimi-k2-0711-preview |
| 上下文 | 32K | 256K |
| 价格 | 输入 4元/M tokens<br>输出 12元/M tokens | 输入 12元/M tokens<br>输出 60元/M tokens |

## 技术支持

- Moonshot 文档: https://platform.moonshot.cn/docs
- Kimi 模型说明: https://platform.moonshot.cn/docs/models
