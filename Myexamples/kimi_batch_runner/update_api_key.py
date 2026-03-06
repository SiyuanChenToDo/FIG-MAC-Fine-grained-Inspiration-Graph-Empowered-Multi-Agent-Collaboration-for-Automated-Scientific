#!/usr/bin/env python3
"""
批量更新 Kimi API Key
使用方式: python update_api_key.py <新的API_KEY>
"""

import sys
import re
from pathlib import Path

def update_file(filepath, old_pattern, new_key, description):
    """更新文件中的 API Key"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 替换 API Key
        new_content = re.sub(old_pattern, new_key, content)
        
        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"  ✓ 已更新: {description}")
            return True
        else:
            print(f"  - 无需更新: {description}")
            return False
    except Exception as e:
        print(f"  ✗ 更新失败: {description} - {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("用法: python update_api_key.py <新的API_KEY>")
        print("示例: python update_api_key.py sk-kimi-xxxxxxxxxxxx")
        sys.exit(1)
    
    new_api_key = sys.argv[1].strip()
    
    # 验证 Key 格式
    if not new_api_key.startswith("sk-"):
        print("错误: API Key 应该以 'sk-' 开头")
        sys.exit(1)
    
    if len(new_api_key) < 20:
        print("错误: API Key 太短，请检查")
        sys.exit(1)
    
    print("="*70)
    print("更新 Kimi API Key")
    print("="*70)
    print(f"\n新 Key: {new_api_key[:15]}...{new_api_key[-4:]}")
    print(f"长度: {len(new_api_key)} 字符\n")
    
    base_dir = Path(__file__).parent
    
    # 定义要更新的文件
    files_to_update = [
        # (文件路径, 正则模式, 替换模板, 描述)
        (
            base_dir / "kimi_batch_runner.py",
            r'KIMI_API_KEY = "[^"]+"',
            f'KIMI_API_KEY = "{new_api_key}"',
            "kimi_batch_runner.py"
        ),
        (
            base_dir / "run_kimi_batch.sh",
            r'export MOONSHOT_API_KEY="[^"]+"',
            f'export MOONSHOT_API_KEY="{new_api_key}"',
            "run_kimi_batch.sh"
        ),
        (
            base_dir / "test_kimi_api.py",
            r'KIMI_API_KEY = "[^"]+"',
            f'KIMI_API_KEY = "{new_api_key}"',
            "test_kimi_api.py"
        ),
        (
            base_dir / "check_api_key.py",
            r'KIMI_API_KEY = os\.environ\.get\("MOONSHOT_API_KEY", "[^"]*"\)',
            f'KIMI_API_KEY = os.environ.get("MOONSHOT_API_KEY", "{new_api_key}")',
            "check_api_key.py"
        ),
    ]
    
    updated_count = 0
    for filepath, pattern, replacement, description in files_to_update:
        if filepath.exists():
            if update_file(filepath, pattern, replacement, description):
                updated_count += 1
        else:
            print(f"  ✗ 文件不存在: {description}")
    
    print(f"\n{'='*70}")
    print(f"更新完成: {updated_count}/{len(files_to_update)} 个文件已更新")
    print("="*70)
    print("\n下一步:")
    print("1. 测试新 Key: python check_api_key.py")
    print("2. 运行批量处理: bash run_kimi_batch.sh 0 150")

if __name__ == "__main__":
    main()
