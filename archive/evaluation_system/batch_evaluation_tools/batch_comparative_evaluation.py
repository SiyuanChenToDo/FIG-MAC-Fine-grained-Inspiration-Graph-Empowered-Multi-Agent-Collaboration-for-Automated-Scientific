#!/usr/bin/env python3
"""
批量对比评估脚本
用于大规模对比 Hypothesis Society 和 Virtual-Scientists 在相同研究问题上的表现
"""

import os
import sys
import json
import glob
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple

class BatchComparativeEvaluator:
    def __init__(self, output_dir: str = "Myexamples/evaluation_system/batch_results"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
    def extract_baseline_from_log(self, log_file: str) -> str:
        """
        从 Virtual-Scientists 日志文件中提取 Final Idea
        """
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 查找 Final Idea JSON
            if 'Final Idea:' in content or '"Idea":' in content:
                # 尝试提取完整的JSON对象
                lines = content.split('\n')
                json_lines = []
                in_json = False
                brace_count = 0
                
                for line in lines:
                    if '"Idea":' in line and '{' in line:
                        in_json = True
                        brace_count = line.count('{') - line.count('}')
                        json_lines.append(line.strip())
                    elif in_json:
                        json_lines.append(line.strip())
                        brace_count += line.count('{') - line.count('}')
                        if brace_count == 0:
                            break
                
                if json_lines:
                    json_str = '\n'.join(json_lines)
                    try:
                        data = json.loads(json_str)
                        # 格式化为评估友好的文本
                        baseline_text = f"""Title: {data.get('Title', 'Unknown')}

Abstract: {data.get('Idea', '')}

Experiment Design: {data.get('Experiment', '')}

Quality Metrics:
- Clarity: {data.get('Clarity', 'N/A')}/10
- Feasibility: {data.get('Feasibility', 'N/A')}/10
- Novelty: {data.get('Novelty', 'N/A')}/10
"""
                        return baseline_text
                    except json.JSONDecodeError as e:
                        print(f"⚠️ JSON解析失败: {e}")
                        # 如果JSON解析失败，尝试提取纯文本
                        return self._extract_idea_text_fallback(content)
            
            print(f"⚠️ 未找到 Final Idea 在日志文件: {log_file}")
            return None
            
        except Exception as e:
            print(f"❌ 读取日志文件失败 {log_file}: {e}")
            return None
    
    def _extract_idea_text_fallback(self, content: str) -> str:
        """回退方案：从日志中提取Idea文本段落"""
        # 查找 "Idea": 开头的段落
        import re
        pattern = r'"Idea":\s*"([^"]*)"'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return f"Abstract: {match.group(1)}"
        return ""
    
    def find_matching_baseline_log(self, our_report_path: str, baseline_logs_dir: str) -> str:
        """
        根据报告时间戳查找对应的基线日志文件
        假设文件命名格式: 20251203_154321_*.md 对应 logs_qwen/20251203_155525_*.log
        """
        # 从报告文件名提取日期
        report_name = os.path.basename(our_report_path)
        date_str = report_name[:8]  # 20251203
        
        # 查找同一天的所有日志
        log_pattern = os.path.join(baseline_logs_dir, f"{date_str}_*_1,1_dialogue.log")
        matching_logs = glob.glob(log_pattern)
        
        if matching_logs:
            # 返回最新的日志
            matching_logs.sort(reverse=True)
            return matching_logs[0]
        
        print(f"⚠️ 未找到匹配的基线日志，日期: {date_str}")
        return None
    
    def run_single_comparison(self, our_report: str, baseline_text: str, 
                            research_question: str = None) -> Dict:
        """
        运行单次对比评估
        """
        print(f"\n{'='*60}")
        print(f"📊 评估报告: {os.path.basename(our_report)}")
        if research_question:
            print(f"📝 研究问题: {research_question[:80]}...")
        print(f"{'='*60}")
        
        # 构建评估命令
        cmd = [
            "python", "Myexamples/evaluation_system/run_evaluation.py",
            "--report_path", our_report,
            "--comparison_text", baseline_text,
            "--output_dir", self.output_dir
        ]
        
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=300,  # 5分钟超时
                cwd="/root/autodl-tmp"
            )
            
            if result.returncode == 0:
                print("✅ 评估完成")
                # 解析输出，查找生成的JSON文件路径
                output_lines = result.stdout.split('\n')
                for line in output_lines:
                    if "JSON Results saved to:" in line:
                        json_path = line.split(":")[-1].strip()
                        return {"status": "success", "json_path": json_path}
            else:
                print(f"❌ 评估失败: {result.stderr}")
                return {"status": "failed", "error": result.stderr}
                
        except subprocess.TimeoutExpired:
            print("❌ 评估超时")
            return {"status": "timeout"}
        except Exception as e:
            print(f"❌ 评估出错: {e}")
            return {"status": "error", "error": str(e)}
    
    def batch_evaluate(self, our_reports: List[str], baseline_logs_dir: str,
                      research_questions: List[str] = None) -> Dict:
        """
        批量评估
        
        Args:
            our_reports: 我们系统生成的报告列表
            baseline_logs_dir: 基线系统日志目录
            research_questions: 可选，研究问题列表（与报告一一对应）
        """
        results_summary = {
            "timestamp": datetime.now().isoformat(),
            "total_evaluations": len(our_reports),
            "successful": 0,
            "failed": 0,
            "results": []
        }
        
        for idx, report_path in enumerate(our_reports):
            print(f"\n\n{'#'*70}")
            print(f"# 进度: {idx+1}/{len(our_reports)}")
            print(f"{'#'*70}")
            
            # 1. 查找对应的基线日志
            baseline_log = self.find_matching_baseline_log(report_path, baseline_logs_dir)
            
            if not baseline_log:
                print(f"⚠️ 跳过（未找到基线日志）: {report_path}")
                results_summary["failed"] += 1
                results_summary["results"].append({
                    "report": report_path,
                    "status": "no_baseline",
                    "error": "No matching baseline log found"
                })
                continue
            
            # 2. 提取基线文本
            baseline_text = self.extract_baseline_from_log(baseline_log)
            
            if not baseline_text:
                print(f"⚠️ 跳过（基线提取失败）: {report_path}")
                results_summary["failed"] += 1
                results_summary["results"].append({
                    "report": report_path,
                    "baseline_log": baseline_log,
                    "status": "extraction_failed"
                })
                continue
            
            # 3. 运行评估
            research_q = research_questions[idx] if research_questions else None
            eval_result = self.run_single_comparison(report_path, baseline_text, research_q)
            
            if eval_result.get("status") == "success":
                results_summary["successful"] += 1
            else:
                results_summary["failed"] += 1
            
            results_summary["results"].append({
                "report": report_path,
                "baseline_log": baseline_log,
                "research_question": research_q,
                **eval_result
            })
        
        # 4. 保存汇总结果
        summary_path = os.path.join(self.output_dir, f"batch_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(results_summary, f, indent=2, ensure_ascii=False)
        
        print(f"\n\n{'='*70}")
        print(f"📊 批量评估完成")
        print(f"{'='*70}")
        print(f"✅ 成功: {results_summary['successful']}/{results_summary['total_evaluations']}")
        print(f"❌ 失败: {results_summary['failed']}/{results_summary['total_evaluations']}")
        print(f"📁 汇总报告: {summary_path}")
        print(f"{'='*70}\n")
        
        return results_summary
    
    def generate_aggregate_report(self, batch_summary_path: str) -> str:
        """
        生成批量评估的汇总分析报告
        """
        with open(batch_summary_path, 'r', encoding='utf-8') as f:
            summary = json.load(f)
        
        # 读取所有成功评估的JSON结果
        all_results = []
        for result in summary["results"]:
            if result.get("status") == "success" and "json_path" in result:
                try:
                    with open(result["json_path"], 'r', encoding='utf-8') as f:
                        eval_data = json.load(f)
                        all_results.append({
                            "report": result["report"],
                            "data": eval_data
                        })
                except Exception as e:
                    print(f"⚠️ 读取评估结果失败: {result['json_path']}, {e}")
        
        # 统计分析
        wins_a = 0
        wins_b = 0
        ties = 0
        avg_novelty_a = []
        avg_novelty_b = []
        
        for res in all_results:
            data = res["data"]
            
            # 胜负统计
            if "comparison" in data and "llm_comparison" in data["comparison"]:
                winner = data["comparison"]["llm_comparison"].get("Winner", "")
                if winner == "A":
                    wins_a += 1
                elif winner == "B":
                    wins_b += 1
                else:
                    ties += 1
            
            # 新颖性统计
            if "metrics" in data:
                our_novelty = data["metrics"].get("subjective_llm", {}).get("Novelty")
                if our_novelty:
                    avg_novelty_a.append(our_novelty)
                
                if "comparison" in data and "baseline_metrics" in data["comparison"]:
                    baseline_on = data["comparison"]["baseline_metrics"].get("Novelty_Metrics", {}).get("ON")
                    if baseline_on and isinstance(baseline_on, (int, float)):
                        avg_novelty_b.append(baseline_on)
        
        # 生成Markdown报告
        report_md = f"""# 批量对比评估汇总报告

**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**评估总数**: {summary['total_evaluations']}  
**成功评估**: {summary['successful']}  
**失败评估**: {summary['failed']}

---

## 📊 总体胜负统计

| 系统 | 胜出次数 | 胜率 |
|------|---------|------|
| **System A (Ours - Hypothesis Society)** | {wins_a} | {wins_a/(wins_a+wins_b+ties)*100:.1f}% |
| **System B (Baseline - Virtual-Scientists)** | {wins_b} | {wins_b/(wins_a+wins_b+ties)*100:.1f}% |
| **平局 (Tie)** | {ties} | {ties/(wins_a+wins_b+ties)*100:.1f}% |

---

## 📈 平均指标对比

### 新颖性得分
- **System A 平均新颖性**: {sum(avg_novelty_a)/len(avg_novelty_a):.2f}/10 (主观LLM评分)
- **System B 平均新颖性**: {sum(avg_novelty_b)/len(avg_novelty_b):.2f} (ON客观指标)

*注：两个系统使用不同的新颖性指标，直接比较需谨慎*

---

## 📋 详细结果列表

"""
        for idx, res in enumerate(all_results, 1):
            report_name = os.path.basename(res["report"])
            data = res["data"]
            
            winner = "N/A"
            if "comparison" in data and "llm_comparison" in data["comparison"]:
                winner = data["comparison"]["llm_comparison"].get("Winner", "N/A")
            
            novelty_a = data["metrics"].get("subjective_llm", {}).get("Novelty", "N/A")
            
            report_md += f"""
### {idx}. {report_name}
- **胜者**: System {winner}
- **System A 新颖性**: {novelty_a}/10
- **详细报告**: `{data['metadata']['source']}`

"""
        
        report_md += f"""
---

## 💡 结论与建议

基于 {len(all_results)} 次成功评估的结果：

1. **优势领域**: {"System A" if wins_a > wins_b else "System B"} 在本批次评估中表现更优
2. **改进方向**: {"继续保持当前策略" if wins_a > wins_b else "需要提升创新性和方法论深度"}
3. **下一步建议**: 
   - 分析失败/平局案例的共性问题
   - 针对性优化弱势维度（新颖性、可行性、清晰度等）
   - 扩大评估样本量，验证结果稳定性

---

*本报告由批量评估系统自动生成*
"""
        
        # 保存报告
        report_path = os.path.join(self.output_dir, f"aggregate_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_md)
        
        print(f"📄 汇总分析报告已生成: {report_path}")
        return report_path


def main():
    parser = argparse.ArgumentParser(description="批量对比评估 Hypothesis Society vs Virtual-Scientists")
    parser.add_argument("--our_reports_dir", type=str, default="Scientific_Hypothesis_Reports",
                       help="我们系统生成的报告目录")
    parser.add_argument("--baseline_logs_dir", type=str, default="/root/autodl-tmp/logs_qwen",
                       help="Virtual-Scientists日志目录")
    parser.add_argument("--output_dir", type=str, default="Myexamples/evaluation_system/batch_results",
                       help="批量评估结果输出目录")
    parser.add_argument("--topics_file", type=str, default=None,
                       help="研究问题列表文件（每行一个问题，与报告顺序对应）")
    parser.add_argument("--report_pattern", type=str, default="*.md",
                       help="报告文件匹配模式")
    
    args = parser.parse_args()
    
    # 1. 查找所有报告
    report_pattern = os.path.join(args.our_reports_dir, args.report_pattern)
    our_reports = sorted(glob.glob(report_pattern))
    
    if not our_reports:
        print(f"❌ 未找到任何报告文件: {report_pattern}")
        return
    
    print(f"✅ 找到 {len(our_reports)} 份报告文件")
    
    # 2. 读取研究问题（可选）
    research_questions = None
    if args.topics_file and os.path.exists(args.topics_file):
        with open(args.topics_file, 'r', encoding='utf-8') as f:
            research_questions = [line.strip() for line in f if line.strip()]
        print(f"✅ 读取 {len(research_questions)} 个研究问题")
    
    # 3. 初始化评估器
    evaluator = BatchComparativeEvaluator(output_dir=args.output_dir)
    
    # 4. 运行批量评估
    summary = evaluator.batch_evaluate(
        our_reports=our_reports,
        baseline_logs_dir=args.baseline_logs_dir,
        research_questions=research_questions
    )
    
    # 5. 生成汇总报告
    if summary["successful"] > 0:
        summary_path = os.path.join(args.output_dir, 
                                   f"batch_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        # 重新保存一次以确保路径正确
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        evaluator.generate_aggregate_report(summary_path)
    else:
        print("❌ 没有成功的评估，无法生成汇总报告")


if __name__ == "__main__":
    main()

