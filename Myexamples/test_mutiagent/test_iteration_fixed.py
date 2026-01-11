"""
测试修复后的迭代功能
验证 REVISION 状态是否正常工作
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from hypothesis_society_demo import HypothesisGenerationSociety
from Myexamples.test_mutiagent.camel_logger_formatter import OutputFormatter


async def test_iteration_fixed():
    """测试修复后的迭代功能"""
    
    print("\n" + "="*80)
    print("测试修复后的迭代功能")
    print("="*80)
    print("\n修复内容:")
    print("  1. ✓ 统一评分标准为 1-10 分制 (critic_crucible.py)")
    print("  2. ✓ 在 WorkflowHelper 中添加 REVISION 状态 (workflow_helper.py)")
    print("  3. ✓ 显式传递迭代参数 (hypothesis_society_demo.py)")
    print()
    
    # 创建系统
    society = HypothesisGenerationSociety()
    team = society.create_research_team()
    
    # 使用简单主题
    test_topic = "Deep learning for medical diagnosis"
    
    print("="*80)
    print("测试配置:")
    print(f"  主题: {test_topic}")
    print(f"  最大迭代次数: 3")
    print(f"  质量阈值: 8.5/10 (较高,应该触发迭代)")
    print("="*80 + "\n")
    
    print("关键输出标志:")
    print("  ✓ [ITERATION CONFIG] - 参数配置")
    print("  ✓ [ITERATION] Quality score - 质量分数")
    print("  ✓ PHASE 5.X: ITERATIVE REVISION - 修订阶段")
    print("  ✓ [ITERATION] Starting iteration X/3 - 迭代开始")
    print("\n" + "="*80 + "\n")
    
    # 运行
    try:
        result = await society.run_research_async(
            research_topic=test_topic,
            max_iterations=3,
            quality_threshold=8.5  # 高阈值,强制触发迭代
        )
        
        # 分析结果
        print("\n" + "="*80)
        print("测试结果")
        print("="*80 + "\n")
        
        if not result.failed:
            OutputFormatter.success("✓ 程序执行成功!")
            
            # 检查迭代统计
            if hasattr(team, 'iteration_scores') and team.iteration_scores:
                print(f"\n迭代统计:")
                print(f"  执行次数: {team.current_iteration}")
                print(f"  分数进展: {' → '.join([f'{s:.2f}' for s in team.iteration_scores])}")
                print(f"  最终分数: {team.iteration_scores[-1]:.2f}/10")
                print(f"  质量阈值: {team.quality_threshold}/10")
                
                if team.current_iteration > 0:
                    improvement = team.iteration_scores[-1] - team.iteration_scores[0]
                    print(f"\n✓✓✓ 迭代功能正常! ✓✓✓")
                    print(f"执行了 {team.current_iteration} 次迭代")
                    print(f"质量提升: +{improvement:.2f}分")
                else:
                    print(f"\n⚠ 第一次就达标")
                    print(f"初始分数 {team.iteration_scores[0]:.2f} >= 阈值 {team.quality_threshold}")
                    print("这说明初始质量很高!")
            else:
                print("✗ 没有找到迭代分数")
                print("可能原因: 质量分数提取失败")
            
            # 显示报告路径
            if "file_path" in result.metadata:
                print(f"\n报告已保存: {result.metadata['file_path']}")
        else:
            OutputFormatter.error("✗ 程序执行失败")
            print(f"错误信息: {result.content}")
        
        print("\n" + "="*80)
        
    except Exception as e:
        print("\n" + "="*80)
        print("错误")
        print("="*80)
        print(f"\n{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(test_iteration_fixed())
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n\n致命错误: {e}")
        import traceback
        traceback.print_exc()
