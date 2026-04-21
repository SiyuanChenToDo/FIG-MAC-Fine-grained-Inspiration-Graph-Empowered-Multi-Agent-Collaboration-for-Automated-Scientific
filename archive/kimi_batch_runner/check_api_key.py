#!/usr/bin/env python3
"""
检查 Kimi API Key 状态和可用模型
"""

import os
import sys

# 尝试从环境变量或脚本获取 API Key
KIMI_API_KEY = os.environ.get("MOONSHOT_API_KEY", "")

if not KIMI_API_KEY:
    # 尝试从脚本读取
    import re
    script_path = os.path.join(os.path.dirname(__file__), "kimi_batch_runner.py")
    if os.path.exists(script_path):
        with open(script_path, 'r') as f:
            content = f.read()
            match = re.search(r'KIMI_API_KEY = "([^"]+)"', content)
            if match:
                KIMI_API_KEY = match.group(1)

print("="*70)
print("Kimi API Key 诊断工具")
print("="*70)
print(f"\n当前 API Key: {KIMI_API_KEY[:15]}...{KIMI_API_KEY[-4:] if len(KIMI_API_KEY) > 4 else 'N/A'}")
print(f"Key 长度: {len(KIMI_API_KEY)} 字符")

# 检查 Key 格式
print("\n格式检查:")
if KIMI_API_KEY.startswith("sk-"):
    print("  ✓ Key 以 'sk-' 开头")
else:
    print("  ✗ Key 格式不正确，应该以 'sk-' 开头")

if "kimi" in KIMI_API_KEY.lower():
    print("  ✓ Key 包含 'kimi' 标识")
else:
    print("  ⚠ Key 不包含 'kimi' 标识，这可能不是 Kimi 的 Key")

# 尝试列出可用模型
print("\n尝试获取模型列表...")
try:
    from openai import OpenAI
    
    client = OpenAI(
        api_key=KIMI_API_KEY,
        base_url="https://api.moonshot.cn/v1",
    )
    
    try:
        models = client.models.list()
        print("  ✓ API Key 有效!")
        print("\n可用模型:")
        for model in models.data[:5]:  # 只显示前5个
            print(f"  - {model.id}")
    except Exception as e:
        print(f"  ✗ 获取模型列表失败: {e}")
        
        # 尝试简单调用
        print("\n尝试简单调用...")
        try:
            response = client.chat.completions.create(
                model="kimi-k2-5",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10,
            )
            print("  ✓ API 调用成功!")
        except Exception as e2:
            print(f"  ✗ API 调用失败: {e2}")
            
            if "401" in str(e2) or "Unauthorized" in str(e2):
                print("\n" + "="*70)
                print("错误分析: 401 Unauthorized")
                print("="*70)
                print("""
可能原因:
1. API Key 已过期或被撤销
2. 账户余额不足
3. API Key 被禁用

解决方案:
1. 登录 Moonshot 控制台检查 Key 状态:
   https://platform.moonshot.cn/

2. 在控制台确认:
   - API Key 是否显示为"正常"
   - 账户是否有足够余额
   - Key 是否有调用权限

3. 如果 Key 有问题，需要:
   - 生成新的 API Key
   - 或充值账户余额
   - 然后更新所有脚本中的 Key

4. 更新以下文件中的 API Key:
   - Myexamples/kimi_batch_runner/kimi_batch_runner.py
   - Myexamples/kimi_batch_runner/run_kimi_batch.sh
   - Myexamples/kimi_batch_runner/test_kimi_api.py
""")

except ImportError:
    print("  ✗ OpenAI SDK 未安装")
    print("    运行: pip install openai")

print("\n" + "="*70)
