#!/usr/bin/env python3
"""
从 Virtual-Scientists 日志文件中提取基线文本
用于手动准备对比评估的基线数据
"""

import os
import sys
import json
import argparse
import re
from pathlib import Path


def extract_final_idea_json(log_content: str) -> dict:
    """
    从日志内容中提取 Final Idea JSON对象
    """
    # 方法1: 直接查找完整的JSON对象
    lines = log_content.split('\n')
    json_lines = []
    in_json = False
    brace_count = 0
    
    for i, line in enumerate(lines):
        # 查找 "Idea": 开头的行，表示JSON开始
        if '"Idea":' in line and '{' in line:
            in_json = True
            brace_count = line.count('{') - line.count('}')
            json_lines.append(line.strip())
        elif in_json:
            json_lines.append(line.strip())
            brace_count += line.count('{') - line.count('}')
            # 当大括号平衡时，JSON结束
            if brace_count == 0:
                break
    
    if json_lines:
        json_str = '\n'.join(json_lines)
        try:
            # 尝试解析JSON
            data = json.loads(json_str)
            return data
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON解析失败: {e}")
            print(f"尝试的JSON字符串:\n{json_str[:500]}...")
            return None
    
    return None


def extract_idea_text_fallback(log_content: str) -> dict:
    """
    回退方案：使用正则表达式提取各个字段
    """
    extracted = {}
    
    # 提取 Title
    title_pattern = r'"Title":\s*"([^"]+)"'
    title_match = re.search(title_pattern, log_content)
    if title_match:
        extracted['Title'] = title_match.group(1)
    
    # 提取 Idea (Abstract)
    idea_pattern = r'"Idea":\s*"(.*?)"(?:\s*,\s*"Title"|$)'
    idea_match = re.search(idea_pattern, log_content, re.DOTALL)
    if idea_match:
        extracted['Idea'] = idea_match.group(1)
    
    # 提取 Experiment
    exp_pattern = r'"Experiment":\s*"(.*?)"(?:\s*,\s*"Clarity"|$)'
    exp_match = re.search(exp_pattern, log_content, re.DOTALL)
    if exp_match:
        extracted['Experiment'] = exp_match.group(1)
    
    # 提取评分
    for metric in ['Clarity', 'Feasibility', 'Novelty']:
        pattern = rf'"{metric}":\s*(\d+)'
        match = re.search(pattern, log_content)
        if match:
            extracted[metric] = int(match.group(1))
    
    return extracted if extracted else None


def format_as_baseline_text(data: dict) -> str:
    """
    将提取的数据格式化为评估友好的基线文本
    """
    baseline_text = f"""Title: {data.get('Title', 'Unknown Title')}

Abstract: {data.get('Idea', 'No abstract available')}

Experiment Design: {data.get('Experiment', 'No experiment design provided')}

Quality Metrics:
- Clarity: {data.get('Clarity', 'N/A')}/10
- Feasibility: {data.get('Feasibility', 'N/A')}/10
- Novelty: {data.get('Novelty', 'N/A')}/10
"""
    return baseline_text


def process_log_file(log_path: str, output_path: str = None, verbose: bool = False) -> str:
    """
    处理单个日志文件
    
    Args:
        log_path: 日志文件路径
        output_path: 输出文件路径（如果为None，则自动生成）
        verbose: 是否输出详细信息
    
    Returns:
        生成的基线文本内容
    """
    print(f"📖 读取日志文件: {log_path}")
    
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            log_content = f.read()
    except Exception as e:
        print(f"❌ 读取失败: {e}")
        return None
    
    # 尝试提取JSON
    print("🔍 尝试提取 Final Idea JSON...")
    data = extract_final_idea_json(log_content)
    
    if not data:
        print("⚠️ JSON提取失败，尝试回退方案...")
        data = extract_idea_text_fallback(log_content)
    
    if not data:
        print("❌ 无法从日志中提取有效数据")
        return None
    
    if verbose:
        print(f"✅ 提取成功！字段: {list(data.keys())}")
        print(f"   Title: {data.get('Title', 'N/A')[:50]}...")
        print(f"   Idea length: {len(data.get('Idea', ''))} chars")
    
    # 格式化为基线文本
    baseline_text = format_as_baseline_text(data)
    
    # 确定输出路径
    if output_path is None:
        # 自动生成：在日志文件同目录下创建txt文件
        log_dir = os.path.dirname(log_path)
        log_basename = os.path.basename(log_path).replace('.log', '')
        output_path = os.path.join(log_dir, f"{log_basename}_baseline.txt")
    
    # 保存到文件
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(baseline_text)
        print(f"✅ 基线文本已保存到: {output_path}")
        return baseline_text
    except Exception as e:
        print(f"❌ 保存失败: {e}")
        return baseline_text  # 即使保存失败，也返回文本内容


def batch_process_logs(log_dir: str, output_dir: str = None, pattern: str = "*_1,1_dialogue.log"):
    """
    批量处理日志目录中的所有日志文件
    """
    import glob
    
    log_pattern = os.path.join(log_dir, pattern)
    log_files = sorted(glob.glob(log_pattern))
    
    if not log_files:
        print(f"❌ 未找到匹配的日志文件: {log_pattern}")
        return
    
    print(f"✅ 找到 {len(log_files)} 个日志文件")
    print(f"{'='*60}\n")
    
    # 确定输出目录
    if output_dir is None:
        output_dir = os.path.join(log_dir, "extracted_baselines")
    os.makedirs(output_dir, exist_ok=True)
    
    success_count = 0
    fail_count = 0
    
    for log_file in log_files:
        log_basename = os.path.basename(log_file).replace('.log', '')
        output_path = os.path.join(output_dir, f"{log_basename}_baseline.txt")
        
        result = process_log_file(log_file, output_path, verbose=False)
        
        if result:
            success_count += 1
        else:
            fail_count += 1
        
        print()  # 空行分隔
    
    print(f"{'='*60}")
    print(f"📊 批量处理完成")
    print(f"✅ 成功: {success_count}/{len(log_files)}")
    print(f"❌ 失败: {fail_count}/{len(log_files)}")
    print(f"📁 输出目录: {output_dir}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description="从 Virtual-Scientists 日志中提取基线文本用于对比评估"
    )
    parser.add_argument("--log_file", type=str, help="单个日志文件路径")
    parser.add_argument("--log_dir", type=str, help="日志目录路径（批量处理）")
    parser.add_argument("--output", type=str, help="输出文件路径（单文件模式）")
    parser.add_argument("--output_dir", type=str, help="输出目录（批量模式）")
    parser.add_argument("--pattern", type=str, default="*_1,1_dialogue.log",
                       help="日志文件匹配模式（批量模式）")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    
    args = parser.parse_args()
    
    if not args.log_file and not args.log_dir:
        print("❌ 错误: 必须指定 --log_file 或 --log_dir")
        parser.print_help()
        return
    
    # 单文件模式
    if args.log_file:
        if not os.path.exists(args.log_file):
            print(f"❌ 文件不存在: {args.log_file}")
            return
        
        result = process_log_file(args.log_file, args.output, args.verbose)
        
        if result and not args.output:
            # 如果没有指定输出文件，打印到终端
            print("\n" + "="*60)
            print("📄 提取的基线文本:")
            print("="*60)
            print(result)
            print("="*60)
    
    # 批量模式
    elif args.log_dir:
        if not os.path.isdir(args.log_dir):
            print(f"❌ 目录不存在: {args.log_dir}")
            return
        
        batch_process_logs(args.log_dir, args.output_dir, args.pattern)


if __name__ == "__main__":
    main()

