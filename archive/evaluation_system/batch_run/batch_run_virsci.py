#!/usr/bin/env python3
"""
批量运行Virtual Scientists对比实验脚本
根据all_research_questions.json中的问题，批量运行run_comparative.py
"""

import json
import os
import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime

# 禁用Python输出缓冲，确保实时显示
os.environ['PYTHONUNBUFFERED'] = '1'

# 配置路径
QUESTIONS_FILE = "/root/autodl-tmp/Myexamples/evaluation_system/batch_results/ours/all_research_questions.json"
RUN_SCRIPT = "/root/autodl-tmp/Myexamples/comparative_experiments/Virtual-Scientists/run_comparative.py"
OUTPUT_DIR = "/root/autodl-tmp/Myexamples/evaluation_system/batch_results/virsci"
VIRSCI_LOGS_DIR = "/root/autodl-tmp/Myexamples/comparative_experiments/Virtual-Scientists/logs_qwen"
# 日志输出目录（为每个问题单独保存）
LOGS_OUTPUT_DIR = os.path.join(OUTPUT_DIR, "logs")

def setup_output_directory():
    """创建输出目录"""
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    Path(LOGS_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    print(f"✓ 输出目录已准备: {OUTPUT_DIR}")
    print(f"✓ 日志目录已准备: {LOGS_OUTPUT_DIR}")

def load_questions():
    """从JSON文件加载问题"""
    try:
        with open(QUESTIONS_FILE, 'r', encoding='utf-8') as f:
            questions = json.load(f)
        print(f"✓ 成功加载 {len(questions)} 个问题")
        return questions
    except Exception as e:
        print(f"✗ 加载问题文件失败: {e}")
        sys.exit(1)

def collect_and_save_logs(question_id, run_start_time):
    """
    收集Virtual Scientists生成的日志文件并保存到规范目录
    
    Args:
        question_id: 问题ID
        run_start_time: 运行开始时间（Unix时间戳）
    """
    import glob
    
    # 获取logs_qwen目录中的所有日志文件
    if not os.path.exists(VIRSCI_LOGS_DIR):
        print(f"    ⚠ Virtual Scientists日志目录不存在: {VIRSCI_LOGS_DIR}")
        return False
    
    # 获取所有 *_dialogue.log 文件
    all_log_files = sorted(glob.glob(os.path.join(VIRSCI_LOGS_DIR, "*_dialogue.log")))
    
    if not all_log_files:
        print(f"    ⚠ 未找到任何日志文件")
        return False
    
    # 获取最新的日志文件（假设最新的是刚才运行生成的）
    # 按修改时间排序，取最新的几个
    log_files_with_time = [(f, os.path.getmtime(f)) for f in all_log_files]
    log_files_with_time.sort(key=lambda x: x[1], reverse=True)
    
    # 取在运行开始时间之后修改的日志文件
    # 给予30秒的缓冲时间（考虑到时间同步问题）
    recent_logs = [f for f, mtime in log_files_with_time if mtime >= run_start_time - 30]
    
    if not recent_logs:
        print(f"    ⚠ 未找到运行时间范围内的日志文件")
        print(f"      运行开始时间: {datetime.fromtimestamp(run_start_time)}")
        print(f"      最新日志修改时间: {datetime.fromtimestamp(log_files_with_time[0][1]) if log_files_with_time else 'N/A'}")
        # 降级处理：取最新的2个文件（通常是1,1和2,1）
        print(f"    ℹ 使用降级方案：取最新的日志文件")
        recent_logs = [f for f, _ in log_files_with_time[:2]]
        if not recent_logs:
            return False
    
    # 为该问题创建日志子目录
    question_log_dir = os.path.join(LOGS_OUTPUT_DIR, question_id)
    Path(question_log_dir).mkdir(parents=True, exist_ok=True)
    
    # 复制日志文件到规范目录
    try:
        copied_count = 0
        for log_file in recent_logs:
            log_basename = os.path.basename(log_file)
            dest_path = os.path.join(question_log_dir, log_basename)
            
            # 读取源文件并写入目标文件
            with open(log_file, 'r', encoding='utf-8') as src:
                content = src.read()
            with open(dest_path, 'w', encoding='utf-8') as dst:
                dst.write(content)
            
            print(f"    ✓ 日志已保存: {log_basename}")
            copied_count += 1
        
        if copied_count > 0:
            return True
        else:
            print(f"    ✗ 未能复制任何日志文件")
            return False
    except Exception as e:
        print(f"    ✗ 日志保存失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_comparative_for_question(question_id, question_text, index, total):
    """为单个问题运行对比实验"""
    # 计算进度百分比
    progress_percent = (index / total) * 100
    
    # 打印进度信息
    print(f"\n{'='*60}")
    print(f"📊 进度: [{index}/{total}] ({progress_percent:.1f}%)")
    print(f"{'='*60}")
    print(f"🔬 问题ID: {question_id}")
    print(f"❓ 问题文本: {question_text[:100]}{'...' if len(question_text) > 100 else ''}")
    print("=" * 60)
    
    # 构建命令
    cmd = [
        "python", RUN_SCRIPT,
        "--topic", question_text
    ]
    
    # 打开报告文件用于实时写入
    report_file = os.path.join(OUTPUT_DIR, f"{question_id}.txt")
    
    try:
        # 运行脚本，实时输出到控制台和文件
        start_time = time.time()
        
        with open(report_file, 'w', encoding='utf-8') as report_f:
            # 写入报告头
            report_f.write(f"问题ID: {question_id}\n")
            report_f.write(f"问题文本: {question_text}\n")
            report_f.write(f"开始时间: {datetime.now().isoformat()}\n")
            report_f.write("=" * 60 + "\n\n")
            report_f.flush()
            
            # 运行子进程，实时输出
            # 使用unbuffered模式确保实时输出
            process = subprocess.Popen(
                cmd,
                cwd=os.path.dirname(RUN_SCRIPT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # 实时读取和输出
            for line in process.stdout:
                # 实时输出到控制台
                sys.stdout.write(line)
                sys.stdout.flush()
                # 同时写入报告文件
                report_f.write(line)
                report_f.flush()
            
            # 等待进程完成
            returncode = process.wait(timeout=600)
            elapsed_time = time.time() - start_time
            
            # 写入结尾信息
            report_f.write("\n" + "=" * 60 + "\n")
            report_f.write(f"运行耗时: {elapsed_time:.2f}秒\n")
            report_f.write(f"返回码: {returncode}\n")
            report_f.write(f"结束时间: {datetime.now().isoformat()}\n")
        
        print("=" * 60)
        
        # 收集和保存日志文件
        print("📁 收集Virtual Scientists日志文件...")
        logs_saved = collect_and_save_logs(question_id, start_time)
        
        if returncode == 0:
            print(f"✓ 成功 (耗时: {elapsed_time:.2f}秒)\n")
            return True
        else:
            print(f"✗ 失败 (返回码: {returncode})\n")
            return False
            
    except subprocess.TimeoutExpired:
        print("=" * 60)
        print(f"✗ 超时 (超过600秒)\n")
        with open(report_file, 'a', encoding='utf-8') as f:
            f.write("\n" + "=" * 60 + "\n")
            f.write(f"状态: 超时 (超过600秒)\n")
        return False
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print(f"⚠ 用户中断\n")
        with open(report_file, 'a', encoding='utf-8') as f:
            f.write("\n" + "=" * 60 + "\n")
            f.write(f"状态: 用户中断\n")
        raise
    except Exception as e:
        print("=" * 60)
        print(f"✗ 异常: {e}\n")
        with open(report_file, 'a', encoding='utf-8') as f:
            f.write("\n" + "=" * 60 + "\n")
            f.write(f"错误: {str(e)}\n")
        return False

def save_summary(questions, results):
    """保存运行摘要"""
    summary_file = os.path.join(OUTPUT_DIR, "summary.json")
    
    summary = {
        "总数": len(questions),
        "成功": sum(results),
        "失败": len(results) - sum(results),
        "成功率": f"{sum(results)/len(results)*100:.2f}%",
        "运行时间": datetime.now().isoformat(),
        "输出目录": OUTPUT_DIR,
        "日志目录": LOGS_OUTPUT_DIR,
        "详情": []
    }
    
    for i, (question, success) in enumerate(zip(questions, results)):
        summary["详情"].append({
            "索引": i + 1,
            "问题ID": question["id"],
            "状态": "成功" if success else "失败",
            "日志路径": os.path.join(LOGS_OUTPUT_DIR, question["id"])
        })
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ 摘要已保存: {summary_file}")

def main():
    """主函数"""
    print("=" * 60)
    print("Virtual Scientists 批量运行脚本")
    print("=" * 60)
    
    # 设置输出目录
    setup_output_directory()
    
    # 加载问题
    questions = load_questions()
    
    # 运行对比实验
    print(f"\n{'='*60}")
    print(f"🚀 开始批量运行 {len(questions)} 个研究问题的对比实验")
    print(f"{'='*60}\n")
    
    results = []
    try:
        for i, question in enumerate(questions, 1):
            success = run_comparative_for_question(
                question["id"],
                question["question"],
                i,
                len(questions)
            )
            results.append(success)
            
            # 实时显示当前统计
            success_count = sum(results)
            print(f"\n📈 当前统计: 成功 {success_count}/{i}, 失败 {i - success_count}/{i}")
    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("⚠ 批量运行已被用户中断")
        print("=" * 60)
        # 保存已完成的结果
        if results:
            save_summary(questions[:len(results)], results)
        sys.exit(1)
    
    # 保存摘要
    print("\n" + "=" * 60)
    save_summary(questions, results)
    
    # 打印最终统计信息
    success_count = sum(results)
    total_count = len(results)
    fail_count = total_count - success_count
    success_rate = (success_count / total_count * 100) if total_count > 0 else 0
    
    print("\n" + "=" * 60)
    print("✅ 批量运行完成!")
    print("=" * 60)
    print(f"\n📊 最终统计:")
    print(f"  总数:   {total_count}")
    print(f"  成功:   {success_count} ✓")
    print(f"  失败:   {fail_count} ✗")
    print(f"  成功率: {success_rate:.2f}%")
    
    print(f"\n📁 输出位置:")
    print(f"  - 运行报告:   {OUTPUT_DIR}/*.txt")
    print(f"  - 日志文件:   {LOGS_OUTPUT_DIR}/{{question_id}}/*_dialogue.log")
    print(f"  - 汇总报告:   {os.path.join(OUTPUT_DIR, 'summary.json')}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
