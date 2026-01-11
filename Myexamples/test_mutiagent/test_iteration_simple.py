"""
简单的迭代功能测试脚本
用于验证多轮迭代是否正常工作
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from hypothesis_society_demo import HypothesisGenerationSociety
from Myexamples.test_mutiagent.camel_logger_formatter import OutputFormatter


async def test_iteration():
    """测试迭代功能"""
    
    OutputFormatter.header("迭代功能测试")
    
    # 创建系统
    society = HypothesisGenerationSociety()
    team = society.create_research_team()
    
    # 使用简单的测试主题
    test_topic = "Graph neural networks for drug discovery"
    
    print("\n" + "="*80)
    print("测试配置:")
    print(f"  主题: {test_topic}")
    print(f"  最大迭代次数: 3")
    print(f"  质量阈值: 7.5/10")
    print("="*80 + "\n")
    
    # 运行研究
    result = await society.run_research_async(
        research_topic=test_topic,
        max_iterations=3,
        quality_threshold=7.5
    )
    
    # 显示结果
    print("\n" + "="*80)
    print("测试结果:")
    print("="*80)
    
    if not result.failed:
        OutputFormatter.success("✓ 假设生成成功!")
        
        # 显示迭代统计
        if hasattr(team, 'iteration_scores') and team.iteration_scores:
            print(f"\n迭代统计:")
            print(f"  执行的迭代次数: {team.current_iteration}")
            print(f"  质量分数进展: {' → '.join([f'{s:.2f}' for s in team.iteration_scores])}")
            print(f"  最终质量分数: {team.iteration_scores[-1]:.2f}/10")
            print(f"  质量阈值: {team.quality_threshold}/10")
            
            # 判断是否进行了迭代
            if team.current_iteration > 0:
                OutputFormatter.success(f"✓ 迭代功能正常! 执行了 {team.current_iteration} 次迭代")
                improvement = team.iteration_scores[-1] - team.iteration_scores[0]
                print(f"  质量提升: +{improvement:.2f}分")
            else:
                OutputFormatter.info("第一次就达到质量阈值,无需迭代")
        else:
            OutputFormatter.warning("⚠ 未找到迭代统计信息")
            print("可能的原因:")
            print("  1. 质量分数提取失败")
            print("  2. 评审阶段出错")
            print("  3. 迭代功能未正确启用")
        
        # 显示报告路径
        if "file_path" in result.metadata:
            print(f"\n报告保存位置: {result.metadata['file_path']}")
    else:
        OutputFormatter.error("✗ 假设生成失败")
        print(f"错误信息: {result.content}")
    
    print("="*80 + "\n")


async def test_low_threshold():
    """测试低阈值(应该不触发迭代)"""
    
    OutputFormatter.header("低阈值测试 - 预期无迭代")
    
    society = HypothesisGenerationSociety()
    team = society.create_research_team()
    
    test_topic = "Machine learning applications"
    
    print("\n测试配置: 质量阈值 = 5.0 (很低,预期第一次就通过)")
    
    result = await society.run_research_async(
        research_topic=test_topic,
        max_iterations=3,
        quality_threshold=5.0  # 很低的阈值
    )
    
    if not result.failed and hasattr(team, 'iteration_scores'):
        if team.current_iteration == 0:
            OutputFormatter.success("✓ 符合预期: 低阈值无需迭代")
        else:
            OutputFormatter.warning(f"⚠ 意外: 低阈值仍然迭代了 {team.current_iteration} 次")


async def test_high_threshold():
    """测试高阈值(应该触发多次迭代)"""
    
    OutputFormatter.header("高阈值测试 - 预期多次迭代")
    
    society = HypothesisGenerationSociety()
    team = society.create_research_team()
    
    test_topic = "Quantum computing algorithms"
    
    print("\n测试配置: 质量阈值 = 9.0 (很高,预期多次迭代)")
    
    result = await society.run_research_async(
        research_topic=test_topic,
        max_iterations=3,
        quality_threshold=9.0  # 很高的阈值
    )
    
    if not result.failed and hasattr(team, 'iteration_scores'):
        if team.current_iteration >= 2:
            OutputFormatter.success(f"✓ 符合预期: 高阈值触发了 {team.current_iteration} 次迭代")
        else:
            OutputFormatter.warning(f"⚠ 意外: 高阈值只迭代了 {team.current_iteration} 次")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("迭代功能测试套件")
    print("="*80 + "\n")
    
    try:
        # 运行基本测试
        asyncio.run(test_iteration())
        
        # 可选: 运行其他测试
        # asyncio.run(test_low_threshold())
        # asyncio.run(test_high_threshold())
        
    except KeyboardInterrupt:
        OutputFormatter.warning("\n用户中断测试")
    except Exception as e:
        OutputFormatter.error(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
