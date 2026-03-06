# GLM-5 Batch Runner 使用说明

## 概述

GLM-5 Batch Runner 是一个基于 CAMEL 框架的多智能体科学假设生成系统，使用智谱 AI 的 GLM-5 模型。

## 配置要求

### 1. 设置 API Key

在使用之前，需要设置 ZhipuAI API Key：

```bash
export ZHIPUAI_API_KEY="your-api-key"
```

或者修改 `glm5_batch_runner.py` 文件中的配置：

```python
GLM5_API_KEY = "your-api-key"
```

### 2. 文件结构

```
Myexamples/kimi_batch_runner/
├── glm5_batch_runner.py          # 批量运行主程序
├── hypothesis_society_glm5.py    # GLM-5 版本的假设生成社会
├── hypothesis_team_kimi.py       # Team 架构（与 Kimi 版本共享）
└── README_GLM5.md               # 本说明文件
```

## 使用方法

### 命令行参数

```bash
python glm5_batch_runner.py \
    --questions-file path/to/questions.json \
    --output-dir Myexamples/glm5_batch_results \
    --start-idx 0 \
    --end-idx 10 \
    --max-iterations 3 \
    --quality-threshold 8.0 \
    --delay 2.0
```

### 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--questions-file` | `Myexamples/evaluation_system/batch_results/ours/all_research_questions.json` | 研究问题 JSON 文件路径 |
| `--output-dir` | `Myexamples/glm5_batch_results` | 输出目录 |
| `--start-idx` | 0 | 开始索引（从0开始） |
| `--end-idx` | None | 结束索引（不包含） |
| `--max-iterations` | 3 | 假设生成的最大迭代次数 |
| `--quality-threshold` | 8.0 | 质量阈值（1-10分） |
| `--delay` | 2.0 | 每次运行之间的延迟（秒） |

### 直接运行单个研究问题

```bash
python hypothesis_society_glm5.py "Your research question here"
```

## GLM-5 特性

### 支持的配置参数

GLM-5 模型支持以下配置参数（在 `hypothesis_society_glm5.py` 中设置）：

```python
default_model_config = {
    "max_tokens": 8192,        # 最大输出 tokens（GLM-5 支持最高 65536）
    "temperature": 0.7,        # 采样温度
    "thinking": {"type": "enabled"},  # 可选：启用深度思考模式
}
```

### 思考模式（Deep Thinking）

GLM-5 支持深度思考模式，可以通过以下方式启用：

```python
model_config = {
    "max_tokens": 65536,
    "temperature": 1.0,
    "thinking": {"type": "enabled"},
}
```

## CAMEL 框架修改

为了支持 GLM-5，以下文件已被修改：

### 1. `/root/autodl-tmp/camel/types/enums.py`

- 添加 `GLM_5 = "glm-5"` 到 `ModelType` 枚举
- 更新 `is_zhipuai` 属性包含 GLM-5
- 更新 `token_limit` 属性为 GLM-5 设置 128,000 tokens

### 2. `/root/autodl-tmp/camel/configs/zhipuai_config.py`

- 添加 `thinking` 参数支持深度思考模式

### 3. `/root/autodl-tmp/Myexamples/agents/camel_native_agent.py`

- 添加 `ZhipuAIConfig` 导入
- 添加 GLM-5 模型检测逻辑
- 根据平台类型自动选择配置类（QwenConfig 或 ZhipuAIConfig）

## 输出结果

运行完成后，结果将保存在以下位置：

```
Myexamples/glm5_batch_results/
├── reports/              # 生成的科学假设报告（Markdown 格式）
├── progress.json         # 进度文件
└── final_report.json     # 最终汇总报告
```

## 注意事项

1. **API Key 安全**：不要将 API Key 硬编码在代码中，建议使用环境变量
2. **速率限制**：GLM-5 API 有速率限制，请根据需要调整 `--delay` 参数
3. **Token 限制**：GLM-5 支持最高 65536 输出 tokens，但默认设置为 8192

## 故障排除

### 问题：ModuleNotFoundError: No module named 'camel'

**解决方案**：确保 CAMEL 框架已安装：

```bash
pip install camel-ai
```

### 问题：API Key 错误

**解决方案**：检查环境变量是否正确设置：

```bash
echo $ZHIPUAI_API_KEY
```

### 问题：模型创建失败

**解决方案**：检查 API Key 和网络连接，并确保 ZhipuAI 服务可访问。

## 参考

- [智谱 AI 开放平台](https://open.bigmodel.cn/)
- [GLM-5 API 文档](https://open.bigmodel.cn/dev/api#glm-5)
- [CAMEL-AI 文档](https://docs.camel-ai.org/)
