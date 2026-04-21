#!/usr/bin/env python3
"""
验证 FIG-MAC Kimi 批量运行配置
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

print("="*70)
print("FIG-MAC Kimi 批量运行 - 配置验证")
print("="*70)

# 1. 检查文件结构
print("\n[1/5] 检查文件结构...")
required_files = [
    "Myexamples/kimi_batch_runner/kimi_batch_runner.py",
    "Myexamples/kimi_batch_runner/hypothesis_society_kimi.py",
    "Myexamples/kimi_batch_runner/run_kimi_batch.sh",
    "Myexamples/kimi_batch_runner/test_kimi_api.py",
    "Myexamples/evaluation_system/batch_results/ours/all_research_questions.json",
]

all_exist = True
for file in required_files:
    path = PROJECT_ROOT / file
    if path.exists():
        print(f"  ✓ {file}")
    else:
        print(f"  ✗ {file} (缺失)")
        all_exist = False

if not all_exist:
    print("\n错误: 部分文件缺失，请检查安装")
    sys.exit(1)

# 2. 检查研究问题文件
print("\n[2/5] 检查研究问题文件...")
questions_file = PROJECT_ROOT / "Myexamples/evaluation_system/batch_results/ours/all_research_questions.json"
try:
    import json
    with open(questions_file, 'r', encoding='utf-8') as f:
        questions = json.load(f)
    print(f"  ✓ 成功加载 {len(questions)} 个研究问题")
    print(f"  ✓ 第一个问题 ID: {questions[0]['id'][:50]}...")
except Exception as e:
    print(f"  ✗ 加载失败: {e}")
    sys.exit(1)

# 3. 检查 API Key 配置
print("\n[3/5] 检查 API Key 配置...")
# 读取 batch_runner 中的 API Key
batch_runner_file = PROJECT_ROOT / "Myexamples/kimi_batch_runner/kimi_batch_runner.py"
with open(batch_runner_file, 'r') as f:
    content = f.read()
    if 'KIMI_API_KEY = "sk-kimi-' in content:
        # 提取 API Key
        import re
        match = re.search(r'KIMI_API_KEY = "(sk-kimi-[^"]+)"', content)
        if match:
            api_key = match.group(1)
            print(f"  ✓ API Key 已配置: {api_key[:15]}...{api_key[-4:]}")
        else:
            print("  ✗ 无法解析 API Key")
    else:
        print("  ✗ API Key 未配置或格式不正确")

# 4. 检查依赖
print("\n[4/5] 检查依赖...")
try:
    from camel.types import ModelType
    print(f"  ✓ CAMEL 已安装")
    print(f"  ✓ Kimi K2 模型: {ModelType.MOONSHOT_KIMI_K2.value}")
    print(f"  ✓ 将使用模型: kimi-k2-5 (K2.5)")
except ImportError as e:
    print(f"  ✗ CAMEL 导入失败: {e}")

try:
    from openai import OpenAI
    print(f"  ✓ OpenAI SDK 已安装")
except ImportError as e:
    print(f"  ✗ OpenAI SDK 未安装: {e}")
    print(f"    请运行: pip install openai")

# 5. 检查输出目录
print("\n[5/5] 检查输出目录...")
output_dir = PROJECT_ROOT / "Myexamples/kimi_batch_results"
if output_dir.exists():
    print(f"  ✓ 输出目录已存在: {output_dir}")
    # 检查已有文件
    existing_reports = list((output_dir / "reports").glob("*.md")) if (output_dir / "reports").exists() else []
    if existing_reports:
        print(f"  ⚠ 注意: 目录中已有 {len(existing_reports)} 个报告文件")
else:
    print(f"  ✓ 输出目录将在首次运行时创建: {output_dir}")

# 总结
print("\n" + "="*70)
print("验证完成!")
print("="*70)
print("\n下一步操作:")
print("1. 确保 API Key 有效 (在 Moonshot 控制台检查)")
print("2. 运行测试: python Myexamples/kimi_batch_runner/test_kimi_api.py")
print("3. 开始批量运行: bash Myexamples/kimi_batch_runner/run_kimi_batch.sh 0 150")
print("\n或者分批运行:")
print("  bash Myexamples/kimi_batch_runner/run_kimi_batch.sh 0 30    # 第一批")
print("  bash Myexamples/kimi_batch_runner/run_kimi_batch.sh 30 60   # 第二批")
print("  ...")
print("="*70)
