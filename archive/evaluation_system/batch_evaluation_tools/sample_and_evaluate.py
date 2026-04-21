#!/usr/bin/env python3
"""
批量采样研究问题并评估系统性能

功能：
1. 从research_question数据库中随机抽取N条研究问题
2. 对每个RQ分别运行您的系统和Virtual-Scientists
3. 保存各自的结果
4. 批量评估并生成对比统计表格

用法：
    python sample_and_evaluate.py --num_samples 10 --output_dir batch_results
"""

import os
import sys
import json
import random
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
import pickle

# 设置环境变量：强制使用本地缓存的模型（不联网下载）
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_DATASETS_OFFLINE'] = '1'
# 强制Python无缓冲输出，避免输出卡住
os.environ['PYTHONUNBUFFERED'] = '1'
print("🔒 已设置离线模式：使用本地缓存的HuggingFace模型")
print("📤 已启用无缓冲输出模式")


def load_research_questions(vdb_path: str, json_data_path: str):
    """从数据库中加载所有研究问题"""
    print("="*80)
    print("📚 加载研究问题数据库...")
    print("="*80)
    
    # 方法1: 从JSON元数据文件提取
    if os.path.exists(json_data_path):
        print(f"从JSON文件加载: {json_data_path}")
        try:
            with open(json_data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            research_questions = []
            for entity in data.get("entities", []):
                if entity.get("entity_type") == "research_question":
                    rq = entity.get("research_question", "").strip()
                    if rq and len(rq) > 20:  # 过滤太短的问题
                        research_questions.append({
                            "id": entity.get("entity_name", ""),
                            "question": rq,
                            "simplified": entity.get("simplified_research_question", rq),
                            "source_id": entity.get("source_id", "")
                        })
            
            print(f"✅ 成功加载 {len(research_questions)} 个研究问题")
            return research_questions
            
        except Exception as e:
            print(f"⚠️ JSON加载失败: {e}")
    
    # 方法2: 从FAISS metadata文件加载
    metadata_path = os.path.join(vdb_path, "research_question/research_question/research_question_research_question.metadata")
    if os.path.exists(metadata_path):
        print(f"从FAISS metadata加载: {metadata_path}")
        try:
            with open(metadata_path, 'rb') as f:
                metadata = pickle.load(f)
            
            research_questions = []
            for record in metadata.get("payloads", []):
                rq = record.get("research_question", "").strip()
                if rq and len(rq) > 20:
                    research_questions.append({
                        "id": record.get("id", ""),
                        "question": rq,
                        "simplified": record.get("simplified_research_question", rq)
                    })
            
            print(f"✅ 成功加载 {len(research_questions)} 个研究问题")
            return research_questions
            
        except Exception as e:
            print(f"⚠️ FAISS metadata加载失败: {e}")
    
    print("❌ 无法加载研究问题数据库")
    return []


def sample_research_questions(all_rqs, num_samples, seed=42):
    """随机采样N个研究问题"""
    print(f"\n🎲 随机采样 {num_samples} 个研究问题 (seed={seed})...")
    
    random.seed(seed)
    sampled = random.sample(all_rqs, min(num_samples, len(all_rqs)))
    
    print(f"✅ 采样完成")
    print("\n采样的研究问题:")
    print("-"*80)
    for i, rq in enumerate(sampled, 1):
        preview = rq['question'][:100] + "..." if len(rq['question']) > 100 else rq['question']
        print(f"[{i}] {preview}")
    print("-"*80)
    
    return sampled

def run_cmd_realtime(cmd, log_file, cwd=None):
    """实时运行命令，同时输出到终端和日志文件"""
    import sys
    
    # 设置环境变量强制Python无缓冲输出
    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    
    with open(log_file, "w", encoding="utf-8") as f:
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=0,  # 无缓冲
            universal_newlines=True,
            env=env
        )

        # 使用iter避免阻塞，实时读取每一行
        try:
            for line in iter(process.stdout.readline, ""):
                if not line:
                    break
                # 立即输出并刷新
                print(line, end="", flush=True)
                f.write(line)
                f.flush()  # 立即写入文件
        except Exception as e:
            print(f"读取输出时出错: {e}")
        
        process.stdout.close()
        returncode = process.wait()
        return returncode

def run_your_system(rq_text: str, output_dir: str, index: int):
    """运行您的hypothesis_society_demo系统"""
    print(f"\n🔬 [Your System] 运行研究问题 #{index}...")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_subdir = os.path.join(output_dir, "your_system", f"rq_{index:02d}_{timestamp}")
    os.makedirs(output_subdir, exist_ok=True)
    
    # 保存研究问题
    rq_file = os.path.join(output_subdir, "research_question.txt")
    with open(rq_file, 'w', encoding='utf-8') as f:
        f.write(rq_text)
    
    # 运行您的系统
    
    cmd = ["python", "Myexamples/test_mutiagent/hypothesis_society_demo.py", rq_text]
    log_file = os.path.join(output_subdir, "run_log.txt")

    returncode = run_cmd_realtime(cmd, log_file, cwd="/root/autodl-tmp")

    try:
        
        
        if returncode == 0:
            print(f"\n   ✅ 运行成功")
            
            # 查找生成的报告
            report_dir = "/root/autodl-tmp/Scientific_Hypothesis_Reports"
            if os.path.exists(report_dir):
                # 找到最新生成的报告
                reports = sorted(Path(report_dir).glob("*.md"), key=os.path.getmtime, reverse=True)
                if reports:
                    latest_report = reports[0]
                    # 复制到输出目录
                    import shutil
                    shutil.copy(latest_report, os.path.join(output_subdir, "hypothesis_report.md"))
                    print(f"   📄 报告已保存")
            
            return True, output_subdir
        else:
            print(f"   ❌ 运行失败 (退出码: {returncode})")
            return False, output_subdir
            
    except subprocess.TimeoutExpired:
        print(f"   ⏰ 运行超时 (>10分钟)")
        return False, output_subdir
    except Exception as e:
        print(f"   ❌ 运行出错: {e}")
        return False, output_subdir


def run_virsci_system(rq_text: str, output_dir: str, index: int):
    """运行Virtual-Scientists系统"""
    print(f"\n🔬 [Virtual-Scientists] 运行研究问题 #{index}...")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_subdir = os.path.join(output_dir, "virsci", f"rq_{index:02d}_{timestamp}")
    os.makedirs(output_subdir, exist_ok=True)
    
    # 保存研究问题
    rq_file = os.path.join(output_subdir, "research_question.txt")
    with open(rq_file, 'w', encoding='utf-8') as f:
        f.write(rq_text)
    
    # 运行Virtual-Scientists
    # 准备命令
    cmd = [
        "python", "Myexamples/comparative_experiments/Virtual-Scientists/run_comparative.py",
        "--topic", rq_text
    ]

    log_file = os.path.join(output_subdir, "run_log.txt")
    
    try:
        # 使用tee同时输出到终端和文件（用户能看到输出，同时保存到文件）
        print(f"   🚀 命令: {' '.join(cmd)}")
        print(f"   📋 输出将实时显示并保存到日志...\n")
        
        # 设置环境变量强制Python无缓冲输出
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        
        with open(log_file, "w", encoding="utf-8") as log_f:
            process = subprocess.Popen(
                cmd,
                cwd="/root/autodl-tmp",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=0,  # 无缓冲
                env=env
            )

            # 实时读取输出
            try:
                for line in iter(process.stdout.readline, ""):
                    if not line:
                        break
                    # 立即输出并刷新
                    print(line, end="", flush=True)
                    log_f.write(line)
                    log_f.flush()  # 立即写入文件
            except Exception as e:
                print(f"读取输出时出错: {e}")

            process.stdout.close()
            returncode = process.wait()
        
        if returncode == 0:
            print(f"\n   ✅ Virtual-Scientists运行成功")
            
            # 从日志文件中提取Final Idea
            try:
                if os.path.exists(log_file):
                    with open(log_file, 'r', encoding='utf-8') as f:
                        log_content = f.read()
                    
                    # 查找Final Idea部分
                    if "Final Idea:" in log_content:
                        start_idx = log_content.find("Final Idea:")
                        # 查找结束标记（通常是多个等号或空行）
                        end_markers = ["====================", "Epoch:", "RESPONSE:"]
                        end_idx = len(log_content)
                        for marker in end_markers:
                            marker_pos = log_content.find(marker, start_idx + 100)
                            if marker_pos > start_idx and marker_pos < end_idx:
                                end_idx = marker_pos
                        
                        if end_idx > start_idx:
                            final_idea = log_content[start_idx:end_idx].strip()
                            
                            # 保存Final Idea
                            idea_file = os.path.join(output_subdir, "final_idea.txt")
                            with open(idea_file, 'w', encoding='utf-8') as f:
                                f.write(final_idea)
                            print(f"   📄 Final Idea已提取并保存到: {idea_file}")
                        else:
                            print(f"   ⚠️ 无法确定Final Idea的结束位置")
                    else:
                        print(f"   ⚠️ 日志中未找到Final Idea标记")
            except Exception as e:
                print(f"   ⚠️ 提取Final Idea失败: {e}")
            
            return True, output_subdir
        else:
            print(f"   ❌ 运行失败 (退出码: {returncode})")
            return False, output_subdir
            
    except subprocess.TimeoutExpired:
        print(f"   ⏰ 运行超时 (>10分钟)")
        return False, output_subdir
    except Exception as e:
        print(f"   ❌ 运行出错: {e}")
        return False, output_subdir


def run_ai_scientist_system(rq_text: str, output_dir: str, index: int):
    """运行AI-Scientist-v2系统"""
    print(f"\n🔬 [AI-Scientist-v2] 运行研究问题 #{index}...")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_subdir = os.path.join(output_dir, "ai_scientist", f"rq_{index:02d}_{timestamp}")
    os.makedirs(output_subdir, exist_ok=True)
    
    # 保存研究问题
    rq_file = os.path.join(output_subdir, "research_question.txt")
    with open(rq_file, 'w', encoding='utf-8') as f:
        f.write(rq_text)
    
    # 运行AI-Scientist-v2
    cmd = [
        "python", "Myexamples/comparative_experiments/AI-Scientist-v2/run_comparative.py",
        "--topic", rq_text,
        "--save_file", output_subdir,
        "--output_file", "result.json",
        "--max_generations", "3",  # 减少生成数量以加快速度
        "--num_reflections", "2"
    ]
    
    log_file = os.path.join(output_subdir, "run_log.txt")
    
    try:
        print(f"   🚀 命令: {' '.join(cmd)}")
        print(f"   📋 输出将实时显示并保存到日志...\n")
        
        # 设置环境变量
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        env['AI_SCIENTIST_VDB_PATH'] = '/root/autodl-tmp/Myexamples/vdb/camel_faiss_storage'
        
        with open(log_file, "w", encoding="utf-8") as log_f:
            process = subprocess.Popen(
                cmd,
                cwd="/root/autodl-tmp",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=0,
                env=env
            )
            
            # 实时读取输出
            try:
                for line in iter(process.stdout.readline, ""):
                    if not line:
                        break
                    print(line, end="", flush=True)
                    log_f.write(line)
                    log_f.flush()
            except Exception as e:
                print(f"读取输出时出错: {e}")
            
            process.stdout.close()
            returncode = process.wait()
        
        if returncode == 0:
            print(f"\n   ✅ AI-Scientist-v2运行成功")
            
            # 从result.json中提取idea
            try:
                result_json = os.path.join(output_subdir, "result.json")
                idea_extracted = False
                
                if os.path.exists(result_json):
                    with open(result_json, 'r', encoding='utf-8') as f:
                        result_data = json.load(f)
                    
                    idea = result_data.get("idea", "")
                    
                    if idea and len(idea.strip()) > 50:
                        idea_file = os.path.join(output_subdir, "final_idea.txt")
                        with open(idea_file, 'w', encoding='utf-8') as f:
                            f.write(idea)
                        print(f"   📄 Final Idea已从result.json提取并保存到: {idea_file}")
                        idea_extracted = True
                
                # 如果从JSON提取失败，尝试从日志中提取
                if not idea_extracted and os.path.exists(log_file):
                    with open(log_file, 'r', encoding='utf-8') as f:
                        log_content = f.read()
                    
                    if "Final Idea:" in log_content:
                        start_idx = log_content.find("Final Idea:")
                        start_content = log_content.find("\n", start_idx) + 1
                        end_markers = ["="*80, "✅ Result saved"]
                        end_idx = len(log_content)
                        
                        for marker in end_markers:
                            marker_pos = log_content.find(marker, start_content)
                            if marker_pos > start_content and marker_pos < end_idx:
                                end_idx = marker_pos
                        
                        if end_idx > start_content:
                            final_idea = log_content[start_content:end_idx].strip()
                            final_idea = final_idea.rstrip("=").strip()
                            
                            if len(final_idea) > 50:
                                idea_file = os.path.join(output_subdir, "final_idea.txt")
                                with open(idea_file, 'w', encoding='utf-8') as f:
                                    f.write(final_idea)
                                print(f"   📄 Final Idea已从日志提取并保存到: {idea_file}")
                                idea_extracted = True
                
                if not idea_extracted:
                    print(f"   ⚠️ 无法提取Final Idea（result.json和日志中都没有找到有效内容）")
                    
            except Exception as e:
                print(f"   ⚠️ 提取Final Idea失败: {e}")
                import traceback
                traceback.print_exc()
            
            return True, output_subdir
        else:
            print(f"   ❌ 运行失败 (退出码: {returncode})")
            return False, output_subdir
            
    except Exception as e:
        print(f"   ❌ 运行出错: {e}")
        return False, output_subdir


def run_coi_system(rq_text: str, output_dir: str, index: int):
    """运行CoI-Agent系统"""
    print(f"\n🔬 [CoI-Agent] 运行研究问题 #{index}...")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_subdir = os.path.join(output_dir, "coi", f"rq_{index:02d}_{timestamp}")
    os.makedirs(output_subdir, exist_ok=True)
    
    # 保存研究问题
    rq_file = os.path.join(output_subdir, "research_question.txt")
    with open(rq_file, 'w', encoding='utf-8') as f:
        f.write(rq_text)
    
    # 运行CoI-Agent
    cmd = [
        "python", "Myexamples/comparative_experiments/CoI-Agent/run_comparative.py",
        "--topic", rq_text,
        "--save_file", output_subdir,
        "--output_file", "result.json"
    ]

    log_file = os.path.join(output_subdir, "run_log.txt")
    
    try:
        print(f"   🚀 命令: {' '.join(cmd)}")
        print(f"   📋 输出将实时显示并保存到日志...\n")
        
        # 设置环境变量
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        env['COI_USE_REAL_VDB'] = '1'
        env['COI_VDB_PATH'] = '/root/autodl-tmp/Myexamples/vdb/camel_faiss_storage'
        
        with open(log_file, "w", encoding="utf-8") as log_f:
            process = subprocess.Popen(
                cmd,
                cwd="/root/autodl-tmp",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=0,
                env=env
            )

            # 实时读取输出
            try:
                for line in iter(process.stdout.readline, ""):
                    if not line:
                        break
                    print(line, end="", flush=True)
                    log_f.write(line)
                    log_f.flush()
            except Exception as e:
                print(f"读取输出时出错: {e}")

            process.stdout.close()
            returncode = process.wait()
        
        if returncode == 0:
            print(f"\n   ✅ CoI-Agent运行成功")
            
            # 从result.json或日志中提取idea
            try:
                result_json = os.path.join(output_subdir, "result.json")
                idea_extracted = False
                
                if os.path.exists(result_json):
                    with open(result_json, 'r', encoding='utf-8') as f:
                        result_data = json.load(f)
                    
                    # idea 可能是字符串或字典
                    idea = result_data.get("idea", "")
                    
                    if idea:
                        # 如果是字典，转换为文本格式
                        if isinstance(idea, dict):
                            # 构建完整的 Final Idea 文本
                            idea_text = ""
                            if idea.get("title"):
                                idea_text += f"**Title:** {idea.get('title')}\n\n"
                            if idea.get("motivation"):
                                idea_text += f"**Origins and Motivation:**\n{idea.get('motivation')}\n\n"
                            if idea.get("novelty"):
                                idea_text += f"**Novelty and Differences from Prior Work:**\n{idea.get('novelty')}\n\n"
                            if idea.get("method"):
                                idea_text += f"**Core Methodology:**\n{idea.get('method')}\n\n"
                            idea = idea_text.strip() if idea_text else str(idea)
                        elif isinstance(idea, str):
                            # 已经是字符串，直接使用
                            pass
                        else:
                            # 其他类型，转换为字符串
                            idea = str(idea)
                        
                        if idea and len(idea.strip()) > 50:
                            idea_file = os.path.join(output_subdir, "final_idea.txt")
                            with open(idea_file, 'w', encoding='utf-8') as f:
                                f.write(idea)
                            print(f"   📄 Final Idea已从result.json提取并保存到: {idea_file}")
                            idea_extracted = True
                
                # 如果从JSON提取失败，尝试从日志中提取
                if not idea_extracted and os.path.exists(log_file):
                    with open(log_file, 'r', encoding='utf-8') as f:
                        log_content = f.read()
                    
                    if "Final Idea:" in log_content:
                        start_idx = log_content.find("Final Idea:")
                        # 查找结束标记（跳过开头的分隔符）
                        start_content = log_content.find("\n", start_idx) + 1
                        end_markers = ["="*80, "✅ Result saved", "succeed to generate"]
                        end_idx = len(log_content)
                        
                        for marker in end_markers:
                            marker_pos = log_content.find(marker, start_content)
                            if marker_pos > start_content and marker_pos < end_idx:
                                end_idx = marker_pos
                        
                        if end_idx > start_content:
                            final_idea = log_content[start_content:end_idx].strip()
                            # 移除末尾的分隔符
                            final_idea = final_idea.rstrip("=").strip()
                            
                            if len(final_idea) > 50:
                                idea_file = os.path.join(output_subdir, "final_idea.txt")
                                with open(idea_file, 'w', encoding='utf-8') as f:
                                    f.write(final_idea)
                                print(f"   📄 Final Idea已从日志提取并保存到: {idea_file}")
                                idea_extracted = True
                
                if not idea_extracted:
                    print(f"   ⚠️ 无法提取Final Idea（result.json和日志中都没有找到有效内容）")
                    
            except Exception as e:
                print(f"   ⚠️ 提取Final Idea失败: {e}")
                import traceback
                traceback.print_exc()
            
            return True, output_subdir
        else:
            print(f"   ❌ 运行失败 (退出码: {returncode})")
            return False, output_subdir
            
    except Exception as e:
        print(f"   ❌ 运行出错: {e}")
        return False, output_subdir


def evaluate_pair(your_result_dir: str, baseline_result_dir: str, rq_text: str, output_dir: str, index: int, baseline_name="virsci"):
    """对比评估两个系统的结果"""
    print(f"\n📊 评估研究问题 #{index}...")
    
    # 为不同基线系统创建不同的评估目录
    eval_output_dir = os.path.join(output_dir, "evaluations", f"rq_{index:02d}_{baseline_name}")
    os.makedirs(eval_output_dir, exist_ok=True)
    
    # 查找报告文件
    your_report = os.path.join(your_result_dir, "hypothesis_report.md")
    baseline_report = os.path.join(baseline_result_dir, "final_idea.txt")
    
    if not os.path.exists(your_report):
        print(f"   ⚠️ 找不到您的系统报告: {your_report}")
        return False
    
    if not os.path.exists(baseline_report):
        print(f"   ⚠️ 找不到{baseline_name}报告: {baseline_report}")
        baseline_report = None
    
    # 读取baseline文本
    if baseline_report and os.path.exists(baseline_report):
        with open(baseline_report, 'r', encoding='utf-8') as f:
            baseline_text = f.read()
    else:
        baseline_text = f"No {baseline_name} output available"
    
    # 运行自动评估
    cmd = [
        "python", "Myexamples/evaluation_system/batch_evaluation_tools/auto_extract_and_evaluate.py",
        "--report_path", your_report,
        "--inspiration_report", "/root/autodl-tmp/inspiration_report.md",  # 如果存在
        "--comparison_text", baseline_text,
        "--research_topic", rq_text,
        "--output_dir", eval_output_dir
    ]
    
    try:
        result = subprocess.run(
            cmd,
            cwd="/root/autodl-tmp",
            capture_output=True,
            # 不设置超时，让评估完整运行完成
            text=True
        )
        
        if result.returncode == 0:
            print(f"   ✅ 评估完成")
            return True
        else:
            print(f"   ❌ 评估失败")
            print(f"   错误: {result.stderr[:200]}")
            return False
            
    except Exception as e:
        print(f"   ❌ 评估出错: {e}")
        return False


def generate_summary_table(output_dir: str):
    """生成汇总统计表格"""
    print("\n" + "="*80)
    print("📊 生成汇总统计表格...")
    print("="*80)
    
    eval_dir = os.path.join(output_dir, "evaluations")
    if not os.path.exists(eval_dir):
        print("❌ 找不到评估结果目录")
        return
    
    # 收集所有评估结果（包括所有baseline系统）
    results = {}
    for rq_dir in sorted(Path(eval_dir).glob("rq_*")):
        rq_id = rq_dir.name.split('_')[0] + '_' + rq_dir.name.split('_')[1]  # 提取 rq_01 格式
        baseline_name = rq_dir.name.split('_', 2)[2] if len(rq_dir.name.split('_')) > 2 else "virsci"  # 提取 baseline 名称
        
        # 查找eval_v2.json文件
        json_files = list(rq_dir.glob("*_eval_v2.json"))
        if json_files:
            try:
                with open(json_files[0], 'r', encoding='utf-8') as f:
                    eval_data = json.load(f)
                    
                    if rq_id not in results:
                        results[rq_id] = {
                            "your_system": None,
                            "virsci": None,
                            "coi": None,
                            "ai_scientist": None
                        }
                    
                    # 根据 baseline_name 存储数据
                    if baseline_name == "virsci":
                        results[rq_id]["virsci"] = eval_data
                    elif baseline_name == "coi":
                        results[rq_id]["coi"] = eval_data
                    elif baseline_name == "ai_scientist":
                        results[rq_id]["ai_scientist"] = eval_data
                    
                    # 您的系统数据（从任意一个评估结果中提取）
                    if results[rq_id]["your_system"] is None:
                        results[rq_id]["your_system"] = eval_data.get("metrics", {})
                        
            except Exception as e:
                print(f"⚠️ 读取 {json_files[0]} 失败: {e}")
    
    if not results:
        print("❌ 没有找到有效的评估结果")
        return
    
    print(f"✅ 收集到 {len(results)} 个研究问题的评估结果\n")
    
    # 生成Markdown表格
    md_output = os.path.join(output_dir, "summary_comparison_table.md")
    
    with open(md_output, 'w', encoding='utf-8') as f:
        f.write("# 批量评估对比统计表\n\n")
        f.write(f"**评估时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
        f.write(f"**研究问题数量**: {len(results)}  \n\n")
        
        f.write("---\n\n")
        
        # Table 1: 客观指标汇总（三个系统）
        f.write("## Table 1: 客观指标对比 (Objective Metrics)\n\n")
        f.write("| RQ | System | ON_raw ↑ | ON_norm ↑ | P ↑ | HD | CD | CI ↑ | S_src ↓ | U_src ↑ | G ↑ |\n")
        f.write("|-------|--------|---------|-----------|-----|-----|-----|-----|---------|---------|-----|\n")
        
        for rq_id, rq_data in sorted(results.items()):
            # Your system metrics
            your_obj = rq_data.get("your_system", {}).get("objective", {})
            your_nov = your_obj.get('Novelty_Metrics', {})
            your_prov = your_obj.get('Provenance_Metrics', {})
            
            f.write(f"| {rq_id} | **Ours** | ")
            f.write(f"{your_nov.get('ON_raw (Overall Novelty - Raw)', 0):.3f} | ")
            f.write(f"{your_nov.get('ON (Overall Novelty - Normalized)', 0):.3f} | ")
            f.write(f"{your_prov.get('P (Provenance-Adjusted Novelty)', 0) if your_prov else 0:.3f} | ")
            f.write(f"{your_nov.get('HD (Historical Dissimilarity)', 0):.3f} | ")
            f.write(f"{your_nov.get('CD (Contemporary Dissimilarity)', 0):.3f} | ")
            f.write(f"{your_nov.get('CI (Contemporary Impact, Year-Normalized)', 0):.3f} | ")
            f.write(f"{your_prov.get('S_src (Source Similarity)', 0) if your_prov else 0:.3f} | ")
            f.write(f"{your_prov.get('U_src (Source Diversity)', 0) if your_prov else 0:.3f} | ")
            f.write(f"{your_prov.get('G (Provenance Factor)', 0) if your_prov else 0:.3f} |\n")
            
            # Virtual-Scientists metrics
            virsci_data = rq_data.get("virsci")
            if virsci_data:
                virsci_obj = virsci_data.get('comparison', {}).get('baseline_metrics', {}).get('objective', {})
                virsci_nov = virsci_obj.get('Novelty_Metrics', {})
                virsci_prov = virsci_obj.get('Provenance_Metrics', {})
                
                f.write(f"| {rq_id} | **VirSci** | ")
                f.write(f"{virsci_nov.get('ON_raw (Overall Novelty - Raw)', 0):.3f} | ")
                f.write(f"{virsci_nov.get('ON (Overall Novelty - Normalized)', 0):.3f} | ")
                f.write(f"{virsci_prov.get('P (Provenance-Adjusted Novelty)', 0) if virsci_prov else 0:.3f} | ")
                f.write(f"{virsci_nov.get('HD (Historical Dissimilarity)', 0):.3f} | ")
                f.write(f"{virsci_nov.get('CD (Contemporary Dissimilarity)', 0):.3f} | ")
                f.write(f"{virsci_nov.get('CI (Contemporary Impact, Year-Normalized)', 0):.3f} | ")
                f.write(f"{virsci_prov.get('S_src (Source Similarity)', 0) if virsci_prov else 0:.3f} | ")
                f.write(f"{virsci_prov.get('U_src (Source Diversity)', 0) if virsci_prov else 0:.3f} | ")
                f.write(f"{virsci_prov.get('G (Provenance Factor)', 0) if virsci_prov else 0:.3f} |\n")
            
            # CoI-Agent metrics
            coi_data = rq_data.get("coi")
            if coi_data:
                coi_obj = coi_data.get('comparison', {}).get('baseline_metrics', {}).get('objective', {})
                coi_nov = coi_obj.get('Novelty_Metrics', {})
                coi_prov = coi_obj.get('Provenance_Metrics', {})
                
                f.write(f"| {rq_id} | **CoI-Agent** | ")
                f.write(f"{coi_nov.get('ON_raw (Overall Novelty - Raw)', 0):.3f} | ")
                f.write(f"{coi_nov.get('ON (Overall Novelty - Normalized)', 0):.3f} | ")
                f.write(f"{coi_prov.get('P (Provenance-Adjusted Novelty)', 0) if coi_prov else 0:.3f} | ")
                f.write(f"{coi_nov.get('HD (Historical Dissimilarity)', 0):.3f} | ")
                f.write(f"{coi_nov.get('CD (Contemporary Dissimilarity)', 0):.3f} | ")
                f.write(f"{coi_nov.get('CI (Contemporary Impact, Year-Normalized)', 0):.3f} | ")
                f.write(f"{coi_prov.get('S_src (Source Similarity)', 0) if coi_prov else 0:.3f} | ")
                f.write(f"{coi_prov.get('U_src (Source Diversity)', 0) if coi_prov else 0:.3f} | ")
                f.write(f"{coi_prov.get('G (Provenance Factor)', 0) if coi_prov else 0:.3f} |\n")
            
            # AI-Scientist-v2 metrics
            ai_scientist_data = rq_data.get("ai_scientist")
            if ai_scientist_data:
                ai_scientist_obj = ai_scientist_data.get('comparison', {}).get('baseline_metrics', {}).get('objective', {})
                ai_scientist_nov = ai_scientist_obj.get('Novelty_Metrics', {})
                ai_scientist_prov = ai_scientist_obj.get('Provenance_Metrics', {})
                
                f.write(f"| {rq_id} | **AI-Scientist-v2** | ")
                f.write(f"{ai_scientist_nov.get('ON_raw (Overall Novelty - Raw)', 0):.3f} | ")
                f.write(f"{ai_scientist_nov.get('ON (Overall Novelty - Normalized)', 0):.3f} | ")
                f.write(f"{ai_scientist_prov.get('P (Provenance-Adjusted Novelty)', 0) if ai_scientist_prov else 0:.3f} | ")
                f.write(f"{ai_scientist_nov.get('HD (Historical Dissimilarity)', 0):.3f} | ")
                f.write(f"{ai_scientist_nov.get('CD (Contemporary Dissimilarity)', 0):.3f} | ")
                f.write(f"{ai_scientist_nov.get('CI (Contemporary Impact, Year-Normalized)', 0):.3f} | ")
                f.write(f"{ai_scientist_prov.get('S_src (Source Similarity)', 0) if ai_scientist_prov else 0:.3f} | ")
                f.write(f"{ai_scientist_prov.get('U_src (Source Diversity)', 0) if ai_scientist_prov else 0:.3f} | ")
                f.write(f"{ai_scientist_prov.get('G (Provenance Factor)', 0) if ai_scientist_prov else 0:.3f} |\n")
        
        f.write("\n---\n\n")
        
        # Table 2: 主观指标汇总（三个系统）
        f.write("## Table 2: 主观指标对比 (Subjective Metrics)\n\n")
        f.write("| RQ | System | Novelty | Significance | Effectiveness | Clarity | Feasibility |\n")
        f.write("|-------|--------|---------|--------------|---------------|---------|-------------|\n")
        
        for rq_id, rq_data in sorted(results.items()):
            # Your system
            your_subj = rq_data.get("your_system", {}).get("subjective_llm", {})
            f.write(f"| {rq_id} | **Ours** | ")
            f.write(f"{your_subj.get('Novelty', '-')} | ")
            f.write(f"{your_subj.get('Significance', '-')} | ")
            f.write(f"{your_subj.get('Effectiveness', '-')} | ")
            f.write(f"{your_subj.get('Clarity', '-')} | ")
            f.write(f"{your_subj.get('Feasibility', '-')} |\n")
            
            # Virtual-Scientists
            virsci_data = rq_data.get("virsci")
            if virsci_data:
                virsci_subj = virsci_data.get('comparison', {}).get('baseline_metrics', {}).get('subjective_llm', {})
                f.write(f"| {rq_id} | **VirSci** | ")
                f.write(f"{virsci_subj.get('Novelty', '-')} | ")
                f.write(f"{virsci_subj.get('Significance', '-')} | ")
                f.write(f"{virsci_subj.get('Effectiveness', '-')} | ")
                f.write(f"{virsci_subj.get('Clarity', '-')} | ")
                f.write(f"{virsci_subj.get('Feasibility', '-')} |\n")
            
            # CoI-Agent
            coi_data = rq_data.get("coi")
            if coi_data:
                coi_subj = coi_data.get('comparison', {}).get('baseline_metrics', {}).get('subjective_llm', {})
                f.write(f"| {rq_id} | **CoI-Agent** | ")
                f.write(f"{coi_subj.get('Novelty', '-')} | ")
                f.write(f"{coi_subj.get('Significance', '-')} | ")
                f.write(f"{coi_subj.get('Effectiveness', '-')} | ")
                f.write(f"{coi_subj.get('Clarity', '-')} | ")
                f.write(f"{coi_subj.get('Feasibility', '-')} |\n")
            
            # AI-Scientist-v2
            ai_scientist_data = rq_data.get("ai_scientist")
            if ai_scientist_data:
                ai_scientist_subj = ai_scientist_data.get('comparison', {}).get('baseline_metrics', {}).get('subjective_llm', {})
                f.write(f"| {rq_id} | **AI-Scientist-v2** | ")
                f.write(f"{ai_scientist_subj.get('Novelty', '-')} | ")
                f.write(f"{ai_scientist_subj.get('Significance', '-')} | ")
                f.write(f"{ai_scientist_subj.get('Effectiveness', '-')} | ")
                f.write(f"{ai_scientist_subj.get('Clarity', '-')} | ")
                f.write(f"{ai_scientist_subj.get('Feasibility', '-')} |\n")
        
        f.write("\n---\n\n")
        
        # Table 3: 统计汇总（三个系统）
        f.write("## Table 3: 统计汇总 (Statistical Summary)\n\n")
        
        # 计算平均值和标准差（三个系统）
        your_on_raws, your_ps = [], []
        virsci_on_raws, virsci_ps = [], []
        coi_on_raws, coi_ps = [], []
        
        for rq_id, rq_data in results.items():
            # Your system
            your_obj = rq_data.get("your_system", {}).get("objective", {})
            your_nov = your_obj.get('Novelty_Metrics', {})
            your_prov = your_obj.get('Provenance_Metrics', {})
            
            on_raw = your_nov.get('ON_raw (Overall Novelty - Raw)', 0)
            if on_raw > 0:
                your_on_raws.append(on_raw)
            if your_prov:
                p = your_prov.get('P (Provenance-Adjusted Novelty)', 0)
                if p > 0:
                    your_ps.append(p)
            
            # Virtual-Scientists
            virsci_data = rq_data.get("virsci")
            if virsci_data:
                virsci_obj = virsci_data.get('comparison', {}).get('baseline_metrics', {}).get('objective', {})
                virsci_nov = virsci_obj.get('Novelty_Metrics', {})
                virsci_prov = virsci_obj.get('Provenance_Metrics', {})
                
                on_raw = virsci_nov.get('ON_raw (Overall Novelty - Raw)', 0)
                if on_raw > 0:
                    virsci_on_raws.append(on_raw)
                if virsci_prov:
                    p = virsci_prov.get('P (Provenance-Adjusted Novelty)', 0)
                    if p > 0:
                        virsci_ps.append(p)
            
            # CoI-Agent
            coi_data = rq_data.get("coi")
            if coi_data:
                coi_obj = coi_data.get('comparison', {}).get('baseline_metrics', {}).get('objective', {})
                coi_nov = coi_obj.get('Novelty_Metrics', {})
                coi_prov = coi_obj.get('Provenance_Metrics', {})
                
                on_raw = coi_nov.get('ON_raw (Overall Novelty - Raw)', 0)
                if on_raw > 0:
                    coi_on_raws.append(on_raw)
                if coi_prov:
                    p = coi_prov.get('P (Provenance-Adjusted Novelty)', 0)
                    if p > 0:
                        coi_ps.append(p)
        
        # 导入 numpy（如果可用）
        try:
            import numpy as np
        except ImportError:
            print("⚠️  numpy 未安装，使用基础统计方法")
            # 使用基础方法计算均值和标准差
            def mean(x): return sum(x) / len(x) if x else 0
            def std(x): 
                if not x: return 0
                m = mean(x)
                return (sum((xi - m) ** 2 for xi in x) / len(x)) ** 0.5
            np = type('np', (), {'mean': mean, 'std': std})()
        
        f.write("| Metric | Ours | VirSci | CoI-Agent | Ours vs VirSci | Ours vs CoI |\n")
        f.write("|--------|------|--------|-----------|----------------|-------------|\n")
        
        # ON_raw 统计
        if your_on_raws:
            your_mean = np.mean(your_on_raws)
            your_std = np.std(your_on_raws)
            
            virsci_str = "-"
            coi_str = "-"
            vs_virsci = "-"
            vs_coi = "-"
            
            if virsci_on_raws:
                virsci_mean = np.mean(virsci_on_raws)
                virsci_std = np.std(virsci_on_raws)
                virsci_str = f"{virsci_mean:.3f}±{virsci_std:.3f}"
                vs_virsci = f"+{((your_mean - virsci_mean) / virsci_mean * 100):.1f}%"
            
            if coi_on_raws:
                coi_mean = np.mean(coi_on_raws)
                coi_std = np.std(coi_on_raws)
                coi_str = f"{coi_mean:.3f}±{coi_std:.3f}"
                vs_coi = f"+{((your_mean - coi_mean) / coi_mean * 100):.1f}%"
            
            f.write(f"| ON_raw (Avg±SD) | {your_mean:.3f}±{your_std:.3f} | {virsci_str} | {coi_str} | {vs_virsci} | {vs_coi} |\n")
        
        # P 统计
        if your_ps:
            your_mean = np.mean(your_ps)
            your_std = np.std(your_ps)
            
            virsci_str = "-"
            coi_str = "-"
            vs_virsci = "-"
            vs_coi = "-"
            
            if virsci_ps:
                virsci_mean = np.mean(virsci_ps)
                virsci_std = np.std(virsci_ps)
                virsci_str = f"{virsci_mean:.3f}±{virsci_std:.3f}"
                vs_virsci = f"+{((your_mean - virsci_mean) / virsci_mean * 100):.1f}%"
            
            if coi_ps:
                coi_mean = np.mean(coi_ps)
                coi_std = np.std(coi_ps)
                coi_str = f"{coi_mean:.3f}±{coi_std:.3f}"
                vs_coi = f"+{((your_mean - coi_mean) / coi_mean * 100):.1f}%"
            
            f.write(f"| P (Avg±SD) | {your_mean:.3f}±{your_std:.3f} | {virsci_str} | {coi_str} | {vs_virsci} | {vs_coi} |\n")
        
        f.write("\n---\n\n")
        
        # Table 4: 胜负统计（分别统计两个对比）
        f.write("## Table 4: 胜负统计 (Win/Loss Statistics)\n\n")
        
        # Ours vs VirSci
        wins_virsci = 0
        losses_virsci = 0
        ties_virsci = 0
        
        # Ours vs CoI-Agent
        wins_coi = 0
        losses_coi = 0
        ties_coi = 0
        
        for rq_id, rq_data in results.items():
            # Ours vs VirSci
            virsci_data = rq_data.get("virsci")
            if virsci_data:
                winner = virsci_data.get('comparison', {}).get('llm_comparison', {}).get('Winner', '')
                if winner == 'A':
                    wins_virsci += 1
                elif winner == 'B':
                    losses_virsci += 1
                else:
                    ties_virsci += 1
            
            # Ours vs CoI-Agent
            coi_data = rq_data.get("coi")
            if coi_data:
                winner = coi_data.get('comparison', {}).get('llm_comparison', {}).get('Winner', '')
                if winner == 'A':
                    wins_coi += 1
                elif winner == 'B':
                    losses_coi += 1
                else:
                    ties_coi += 1
        
        total_virsci = wins_virsci + losses_virsci + ties_virsci
        total_coi = wins_coi + losses_coi + ties_coi
        
        f.write("### Ours vs Virtual-Scientists\n\n")
        f.write(f"| Result | Count | Percentage |\n")
        f.write(f"|--------|-------|------------|\n")
        if total_virsci > 0:
            f.write(f"| **Ours Wins** | {wins_virsci} | {wins_virsci/total_virsci*100:.1f}% |\n")
            f.write(f"| VirSci Wins | {losses_virsci} | {losses_virsci/total_virsci*100:.1f}% |\n")
            f.write(f"| Ties | {ties_virsci} | {ties_virsci/total_virsci*100:.1f}% |\n")
            f.write(f"| **Total** | {total_virsci} | 100% |\n")
        else:
            f.write(f"| No data available | - | - |\n")
        
        f.write("\n### Ours vs CoI-Agent\n\n")
        f.write(f"| Result | Count | Percentage |\n")
        f.write(f"|--------|-------|------------|\n")
        if total_coi > 0:
            f.write(f"| **Ours Wins** | {wins_coi} | {wins_coi/total_coi*100:.1f}% |\n")
            f.write(f"| CoI-Agent Wins | {losses_coi} | {losses_coi/total_coi*100:.1f}% |\n")
            f.write(f"| Ties | {ties_coi} | {ties_coi/total_coi*100:.1f}% |\n")
            f.write(f"| **Total** | {total_coi} | 100% |\n")
        else:
            f.write(f"| No data available | - | - |\n")
    
    print(f"\n✅ 汇总表格已保存到: {md_output}")
    
    # 显示表格预览
    with open(md_output, 'r', encoding='utf-8') as f:
        print("\n" + "="*80)
        print(f.read()[:1000])
        print("...")
        print("="*80)


def main():
    parser = argparse.ArgumentParser(description="批量采样研究问题并评估系统性能")
    parser.add_argument("--num_samples", type=int, default=10, help="采样的研究问题数量")
    parser.add_argument("--vdb_path", type=str, default="Myexamples/vdb/camel_faiss_storage", help="向量数据库路径")
    parser.add_argument("--json_data", type=str, default="Myexamples/data/final_data/final_custom_kg_papers.json", help="元数据JSON路径")
    parser.add_argument("--output_dir", type=str, default="Myexamples/evaluation_system/batch_results", help="输出目录")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    parser.add_argument("--skip_run", action="store_true", help="跳过运行，只生成表格")
    
    args = parser.parse_args()
    
    print("="*80)
    print("🚀 批量采样与评估流程")
    print("="*80)
    print(f"采样数量: {args.num_samples}")
    print(f"输出目录: {args.output_dir}")
    print(f"随机种子: {args.seed}")
    print("="*80)
    
    # 创建输出目录
    os.makedirs(args.output_dir, exist_ok=True)
    
    if not args.skip_run:
        # 步骤1: 加载所有研究问题
        all_rqs = load_research_questions(args.vdb_path, args.json_data)
        
        if not all_rqs:
            print("❌ 无法加载研究问题，退出")
            return
        
        # 步骤2: 随机采样
        sampled_rqs = sample_research_questions(all_rqs, args.num_samples, args.seed)
        
        # 保存采样的RQ列表
        sampled_file = os.path.join(args.output_dir, "sampled_research_questions.json")
        with open(sampled_file, 'w', encoding='utf-8') as f:
            json.dump(sampled_rqs, f, indent=2, ensure_ascii=False)
        print(f"\n✅ 采样列表已保存到: {sampled_file}")
        
        # 步骤3: 批量运行系统
        for i, rq_data in enumerate(sampled_rqs, 1):
            rq_text = rq_data['question']
            
            print("\n" + "="*80)
            print(f"处理研究问题 {i}/{len(sampled_rqs)}")
            print("="*80)
            print(f"问题: {rq_text[:150]}...")
            
            # 运行您的系统
            your_success, your_dir = run_your_system(rq_text, args.output_dir, i)
            
            # 运行Virtual-Scientists
            virsci_success, virsci_dir = run_virsci_system(rq_text, args.output_dir, i)
            
            # 运行CoI-Agent
            coi_success, coi_dir = run_coi_system(rq_text, args.output_dir, i)
            
            # 运行AI-Scientist-v2
            ai_scientist_success, ai_scientist_dir = run_ai_scientist_system(rq_text, args.output_dir, i)
            
            # 评估：您的系统 vs Virtual-Scientists
            if your_success and virsci_success:
                evaluate_pair(your_dir, virsci_dir, rq_text, args.output_dir, i, baseline_name="virsci")
            else:
                print(f"   ⚠️ 跳过VirSci评估（至少一个系统运行失败）")
            
            # 评估：您的系统 vs CoI-Agent
            if your_success and coi_success:
                evaluate_pair(your_dir, coi_dir, rq_text, args.output_dir, i, baseline_name="coi")
            else:
                print(f"   ⚠️ 跳过CoI-Agent评估（至少一个系统运行失败）")
            
            # 评估：您的系统 vs AI-Scientist-v2
            if your_success and ai_scientist_success:
                evaluate_pair(your_dir, ai_scientist_dir, rq_text, args.output_dir, i, baseline_name="ai_scientist")
            else:
                print(f"   ⚠️ 跳过AI-Scientist-v2评估（至少一个系统运行失败）")
    
    # 步骤4: 生成汇总统计表格
    generate_summary_table(args.output_dir)
    
    print("\n" + "="*80)
    print("🎉 批量评估流程完成！")
    print("="*80)
    print(f"\n📁 结果保存在: {args.output_dir}")
    print(f"   - your_system/: 您的系统输出")
    print(f"   - virsci/: Virtual-Scientists输出")
    print(f"   - coi/: CoI-Agent输出")
    print(f"   - evaluations/: 评估结果")
    print(f"   - summary_comparison_table.md: 汇总统计表格")


if __name__ == "__main__":
    main()

