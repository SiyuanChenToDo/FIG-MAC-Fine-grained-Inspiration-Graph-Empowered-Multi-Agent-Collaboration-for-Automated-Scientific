#!/bin/bash
# 使用 curl 测试 Kimi API

API_KEY="${MOONSHOT_API_KEY:-sk-kimi-DqvKI9FbhJtOp0GWTuBW6D9VL4LzmoojwwWEchqLueN3Ev6qhoJf1feiOpQM486B}"

echo "=================================="
echo "测试 Kimi API (使用 curl)"
echo "=================================="
echo ""

# 测试模型列表
echo "1. 获取模型列表..."
curl -s https://api.moonshot.cn/v1/models \
  -H "Authorization: Bearer ${API_KEY}" | head -50

echo ""
echo ""

# 测试简单对话
echo "2. 测试简单对话..."
curl -s https://api.moonshot.cn/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${API_KEY}" \
  -d '{
    "model": "kimi-k2-5",
    "messages": [
      {"role": "user", "content": "Hello, reply with OK in Chinese"}
    ],
    "max_tokens": 50
  }'

echo ""
echo ""

# 测试余额查询（如果支持）
echo "3. 检查余额..."
curl -s https://api.moonshot.cn/v1/users/me/balance \
  -H "Authorization: Bearer ${API_KEY}" 2>/dev/null || echo "余额查询接口不可用"

echo ""
echo "=================================="
