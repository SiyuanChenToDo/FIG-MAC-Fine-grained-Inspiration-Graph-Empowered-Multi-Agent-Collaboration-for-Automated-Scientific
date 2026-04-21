# Ollama 本地模型使用指南

## 📦 安装状态

✅ **Ollama 已安装** (`/root/miniconda3/bin/ollama`)
✅ **Ollama 服务已启动**
✅ **Python 客户端已安装**

## 🚀 快速开始

### 1. 检查 Ollama 状态

```bash
# 检查服务状态
ollama --version

# 查看已安装模型
ollama list

# 查看下载进度（如果正在下载）
ps aux | grep ollama
```

### 2. 拉取模型

根据您的内存大小选择模型：

**8GB 内存推荐：**
```bash
ollama pull llama3.1:8b
```

**16GB 内存推荐：**
```bash
ollama pull qwen2.5:14b
```

**32GB+ 内存推荐：**
```bash
ollama pull qwen2.5:32b
# 或
ollama pull llama3.1:70b
```

### 3. 测试模型

```bash
ollama run llama3.1:8b
```

输入问题测试，按 `Ctrl+D` 退出。

### 4. 运行批量任务

```bash
# 使用默认模型 (llama3.1:8b)
python ollama_batch_runner.py \
    --questions-file Myexamples/evaluation_system/batch_results/ours/all_research_questions.json \
    --start-idx 0 \
    --end-idx 10

# 指定模型
python ollama_batch_runner.py \
    --model qwen2.5:14b \
    --questions-file Myexamples/evaluation_system/batch_results/ours/all_research_questions.json \
    --start-idx 0 \
    --end-idx 10
```

## 📋 可用模型列表

| 模型 | 大小 | 内存需求 | 特点 |
|------|------|----------|------|
| `llama3.1:8b` | 4.7GB | 8GB+ | 速度快，质量良好 |
| `llama3.1:70b` | 40GB | 64GB+ | 最强大的 Llama 模型 |
| `qwen2.5:14b` | 9GB | 16GB+ | 中文支持优秀 |
| `qwen2.5:32b` | 20GB | 32GB+ | 更强的中文模型 |
| `mistral:7b` | 4.1GB | 8GB+ | 法国 Mistral AI，速度快 |
| `mixtral:8x7b` | 26GB | 32GB+ | MoE 架构，性能强大 |
| `phi4` | 9GB | 16GB+ | Microsoft 开源，小巧强大 |
| `gemma2:27b` | 16GB | 24GB+ | Google 开源 |
| `deepseek-coder:33b` | 18GB | 24GB+ | 代码生成优化 |

## 🔧 高级配置

### 修改默认模型

```bash
export OLLAMA_MODEL="qwen2.5:14b"
python ollama_batch_runner.py
```

### 修改 Ollama 地址

如果 Ollama 不在本地运行：

```bash
export OLLAMA_HOST="http://your-server:11434"
python ollama_batch_runner.py
```

### 配置模型参数

在 `ollama_batch_runner.py` 中修改：

```python
# 默认配置
default_model_config = {
    "max_tokens": 4096,  # 减少以适应本地模型
    "temperature": 0.7,
}
```

## 💡 使用建议

### 1. 内存管理
- 本地模型需要大量内存，建议关闭其他程序
- 如果内存不足，系统会使用 swap，速度会变慢
- 可以使用更小的模型（如 8B 参数模型）

### 2. 速度优化
- 第一次运行需要加载模型到内存，较慢
- 后续运行会更快（模型已缓存）
- SSD 硬盘比 HDD 快很多

### 3. 批量任务建议
- 本地模型比 API 慢，建议减少并发
- 使用 `--delay 5` 给模型休息时间
- 建议先测试单个问题再批量运行

## 🛠️ 故障排除

### 问题：Ollama 服务未运行

```bash
# 手动启动
ollama serve

# 后台启动
nohup ollama serve > /tmp/ollama.log 2>&1 &
```

### 问题：模型下载失败

```bash
# 重新拉取
ollama pull llama3.1:8b

# 检查网络连接
curl -I https://ollama.com
```

### 问题：内存不足

```bash
# 查看内存使用
free -h

# 使用更小的模型
ollama pull llama3.1:8b  # 代替 70b
```

### 问题：CAMEL 无法连接 Ollama

```bash
# 检查 Ollama 是否响应
curl http://localhost:11434/api/tags

# 检查防火墙设置
```

## 📊 性能对比

| 平台 | 速度 | 成本 | 隐私 | 质量 |
|------|------|------|------|------|
| **Ollama 本地** | 慢 | 免费 | 最高 | 取决于模型 |
| **Groq** | 极快 | 免费 | 中 | 高 |
| **GLM-5** | 快 | 低 | 中 | 高 |
| **Kimi** | 快 | 中 | 中 | 高 |

## 🎯 推荐场景

**使用 Ollama 本地模型：**
- ✅ 数据隐私要求高（数据不离开本地）
- ✅ 没有 API Key 或预算有限
- ✅ 需要离线工作
- ✅ 有大量计算资源（GPU/内存）

**使用云端 API：**
- ✅ 需要快速响应
- ✅ 计算资源有限
- ✅ 需要最新的超大模型
