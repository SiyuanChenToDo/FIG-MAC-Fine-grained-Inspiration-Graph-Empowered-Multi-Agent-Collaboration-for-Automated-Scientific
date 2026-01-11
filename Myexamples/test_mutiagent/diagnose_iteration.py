"""
迭代功能诊断脚本
帮助诊断为什么没有看到多轮迭代
"""

import asyncio
import sys
import os
import re
import json

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from hypothesis_society_demo import HypothesisGenerationSociety
from Myexamples.test_mutiagent.camel_logger_formatter import OutputFormatter


def diagnose_review_content(review_content: str):
    """诊断评审内容,检查是否包含质量分数"""
    
    print("\n" + "="*80)
    print("评审内容诊断")
    print("="*80)
    
    print(f"\n1. 内容长度: {len(review_content)} 字符")
    
    # 检查 JSON 格式
    print("\n2. JSON 格式检查:")
    json_match = re.search(r'\{[^{}]*"overall_quality_score"[^{}]*\}', review_content, re.DOTALL)
    if json_match:
        print("   ✓ 找到 JSON 格式的质量分数")
        try:
            feedback_json = json.loads(json_match.group())
            score = feedback_json.get("overall_quality_score")
            print(f"   ✓ 成功解析: overall_quality_score = {score}")
        except json.JSONDecodeError as e:
            print(f"   ✗ JSON 解析失败: {e}")
    else:
        print("   ✗ 未找到 JSON 格式的质量分数")
    
    # 检查文本格式
    print("\n3. 文本格式检查:")
    score_patterns = [
        (r'overall[_\s]quality[_\s]score[:\s]+([0-9.]+)', "overall_quality_score"),
        (r'quality[_\s]score[:\s]+([0-9.]+)', "quality_score"),
        (r'overall[_\s]score[:\s]+([0-9.]+)', "overall_score"),
    ]
    
    found_any = False
    for pattern, name in score_patterns:
        match = re.search(pattern, review_content, re.IGNORECASE)
        if match:
            print(f"   ✓ 找到 {name}: {match.group(1)}")
            found_any = True
    
    if not found_any:
        print("   ✗ 未找到任何文本格式的质量分数")
    
    # 显示内容预览
    print("\n4. 内容预览 (前500字符):")
    print("-" * 80)
    preview = review_content[:500]
    print(preview)
    if len(review_content) > 500:
        print("...")
    print("-" * 80)
    
    # 诊断建议
    print("\n5. 诊断建议:")
    if not json_match and not found_any:
        print("   ⚠ 评审内容中没有质量分数!")
        print("   可能原因:")
        print("     - Critic Crucible 的 prompt 没有要求输出质量分数")
        print("     - AI 模型没有按照要求输出")
        print("     - 输出格式不符合预期")
        print("\n   建议:")
        print("     1. 检查 _review_phase() 中的 review_task prompt")
        print("     2. 确保 prompt 明确要求 JSON 格式输出")
        print("     3. 查看实际的 AI 输出内容")


async def run_diagnostic_test():
    """运行诊断测试"""
    
    OutputFormatter.header("迭代功能诊断测试")
    
    print("\n这个脚本会:")
    print("  1. 运行一次假设生成")
    print("  2. 检查迭代参数是否正确设置")
    print("  3. 检查评审内容是否包含质量分数")
    print("  4. 诊断为什么没有触发迭代")
    print()
    
    # 创建系统
    society = HypothesisGenerationSociety()
    team = society.create_research_team()
    
    # 使用简单主题
    test_topic = "AI safety research"
    
    print("="*80)
    print("运行假设生成...")
    print("="*80 + "\n")
    
    # 设置较高的阈值以触发迭代
    max_iterations = 3
    quality_threshold = 8.0
    
    print(f"配置:")
    print(f"  max_iterations = {max_iterations}")
    print(f"  quality_threshold = {quality_threshold}")
    print()
    
    result = await society.run_research_async(
        research_topic=test_topic,
        max_iterations=max_iterations,
        quality_threshold=quality_threshold
    )
    
    # 诊断 1: 检查迭代参数
    print("\n" + "="*80)
    print("诊断 1: 迭代参数检查")
    print("="*80)
    
    if hasattr(team, 'max_iterations'):
        print(f"✓ team.max_iterations = {team.max_iterations}")
    else:
        print("✗ team.max_iterations 未设置")
    
    if hasattr(team, 'quality_threshold'):
        print(f"✓ team.quality_threshold = {team.quality_threshold}")
    else:
        print("✗ team.quality_threshold 未设置")
    
    if hasattr(team, 'current_iteration'):
        print(f"✓ team.current_iteration = {team.current_iteration}")
    else:
        print("✗ team.current_iteration 未设置")
    
    if hasattr(team, 'iteration_scores'):
        print(f"✓ team.iteration_scores = {team.iteration_scores}")
    else:
        print("✗ team.iteration_scores 未设置")
    
    # 诊断 2: 检查评审结果
    print("\n" + "="*80)
    print("诊断 2: 评审结果检查")
    print("="*80)
    
    if hasattr(team, 'results') and 'review' in team.results:
        review_result = team.results['review']
        print(f"✓ 找到评审结果")
        print(f"  - failed: {review_result.failed}")
        print(f"  - content length: {len(review_result.content)} 字符")
        
        if not review_result.failed:
            # 诊断评审内容
            diagnose_review_content(review_result.content)
        else:
            print("✗ 评审失败")
    else:
        print("✗ 未找到评审结果")
    
    # 诊断 3: 迭代执行情况
    print("\n" + "="*80)
    print("诊断 3: 迭代执行情况")
    print("="*80)
    
    if hasattr(team, 'iteration_scores') and team.iteration_scores:
        print(f"✓ 执行了迭代")
        print(f"  - 迭代次数: {team.current_iteration}")
        print(f"  - 质量分数: {team.iteration_scores}")
        print(f"  - 最终分数: {team.iteration_scores[-1]:.2f}/10")
        
        if team.current_iteration > 0:
            print(f"\n✓✓✓ 迭代功能正常工作! ✓✓✓")
        else:
            print(f"\n⚠ 第一次就达到阈值 ({team.iteration_scores[0]:.2f} >= {quality_threshold})")
    else:
        print("✗ 未执行迭代")
        print("\n可能的原因:")
        print("  1. 质量分数提取失败 (见诊断2)")
        print("  2. 评审阶段出错")
        print("  3. _decide_after_review() 逻辑问题")
    
    # 诊断 4: 状态转换检查
    print("\n" + "="*80)
    print("诊断 4: 状态转换检查")
    print("="*80)
    
    if hasattr(team, 'results'):
        states_found = list(team.results.keys())
        print(f"执行的状态: {states_found}")
        
        if 'revision' in states_found:
            print("✓ 找到 REVISION 状态 - 迭代已执行")
        else:
            print("✗ 未找到 REVISION 状态 - 迭代未执行")
            print("  状态转换可能是: REVIEW → POLISH (跳过了 REVISION)")
    
    # 总结
    print("\n" + "="*80)
    print("诊断总结")
    print("="*80)
    
    if hasattr(team, 'iteration_scores') and team.iteration_scores and team.current_iteration > 0:
        print("✓✓✓ 迭代功能正常! ✓✓✓")
    else:
        print("⚠⚠⚠ 迭代功能可能有问题 ⚠⚠⚠")
        print("\n请检查:")
        print("  1. Critic Crucible 的 prompt 是否要求输出质量分数")
        print("  2. 质量分数提取逻辑是否正确")
        print("  3. _decide_after_review() 是否被正确调用")
        print("  4. 查看上面的诊断详情")


if __name__ == "__main__":
    try:
        asyncio.run(run_diagnostic_test())
    except KeyboardInterrupt:
        OutputFormatter.warning("\n用户中断诊断")
    except Exception as e:
        OutputFormatter.error(f"\n诊断失败: {e}")
        import traceback
        traceback.print_exc()
