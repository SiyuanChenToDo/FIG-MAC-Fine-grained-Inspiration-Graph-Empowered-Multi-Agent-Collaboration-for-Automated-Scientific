#!/usr/bin/env python3
"""
AI-Scientist-v2 对比运行脚本 - 使用用户的实际VDB数据和Qwen API
复用CoI-Agent的配置逻辑
"""
import os
import sys
import argparse
import json
from datetime import datetime

# 设置环境变量
os.environ['PYTHONUNBUFFERED'] = '1'

# ========== 复用CoI-Agent的API配置逻辑 ==========
# 使用您的实际 API 配置（与 hypothesis_society_demo.py 一致）
USER_API_KEY = "sk-17fc6cc742c844aaa05e1fb68eb0ed67"
DASH_SCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# 优先使用环境变量中的值，如果没有则使用默认值
if "QWEN_API_KEY" not in os.environ:
    compat_key = os.environ.get("OPENAI_COMPATIBILITY_API_KEY")
    if compat_key:
        os.environ["QWEN_API_KEY"] = compat_key
        print(f"Set QWEN_API_KEY from OPENAI_COMPATIBILITY_API_KEY")
    else:
        os.environ["QWEN_API_KEY"] = USER_API_KEY
        print(f"Using configured QWEN_API_KEY")
else:
    print(f"Using existing QWEN_API_KEY from environment")

# 设置所有相关的 API Key 环境变量
os.environ["OPENAI_API_KEY"] = os.environ["QWEN_API_KEY"]
os.environ["OPENAI_COMPATIBILITY_API_KEY"] = os.environ["QWEN_API_KEY"]

# 设置 Base URL
if "QWEN_API_BASE_URL" not in os.environ:
    os.environ["QWEN_API_BASE_URL"] = DASH_SCOPE_BASE_URL
if "OPENAI_BASE_URL" not in os.environ:
    os.environ["OPENAI_BASE_URL"] = DASH_SCOPE_BASE_URL
if "OPENAI_COMPATIBILITY_API_BASE_URL" not in os.environ:
    os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"] = DASH_SCOPE_BASE_URL

# 强制设置关键配置
os.environ["is_azure"] = "False"  # 使用 OpenAI 兼容接口，不是 Azure
os.environ["OPENAI_API_KEY"] = os.environ["QWEN_API_KEY"]  # 确保使用我们的 API Key
os.environ["OPENAI_BASE_URL"] = DASH_SCOPE_BASE_URL  # 确保使用我们的 Base URL

# 设置embedding（用于VDB搜索）
if "EMBEDDING_API_KEY" not in os.environ or os.environ["EMBEDDING_API_KEY"] == "":
    os.environ["EMBEDDING_API_KEY"] = os.environ["QWEN_API_KEY"]
if "EMBEDDING_MODEL" not in os.environ or os.environ["EMBEDDING_MODEL"] == "":
    os.environ["EMBEDDING_MODEL"] = "text-embedding-v2"

# 设置LLM模型（使用Qwen模型名称，与CoI-Agent一致）
if "MODEL_IDEATION" not in os.environ or os.environ["MODEL_IDEATION"] == "":
    os.environ["MODEL_IDEATION"] = "qwen-plus"
if "MODEL_WRITEUP" not in os.environ or os.environ["MODEL_WRITEUP"] == "":
    os.environ["MODEL_WRITEUP"] = "qwen-plus"
if "MODEL_CITATION" not in os.environ or os.environ["MODEL_CITATION"] == "":
    os.environ["MODEL_CITATION"] = "qwen-plus"
if "MODEL_REVIEW" not in os.environ or os.environ["MODEL_REVIEW"] == "":
    os.environ["MODEL_REVIEW"] = "qwen-plus"
if "MODEL_AGG_PLOTS" not in os.environ or os.environ["MODEL_AGG_PLOTS"] == "":
    os.environ["MODEL_AGG_PLOTS"] = "qwen-plus"

# 设置VDB路径
os.environ["AI_SCIENTIST_VDB_PATH"] = os.environ.get(
    "AI_SCIENTIST_VDB_PATH",
    "/root/autodl-tmp/Myexamples/vdb/camel_faiss_storage"
)
os.environ["AI_SCIENTIST_USE_VDB"] = "1"  # 启用VDB工具

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入AI-Scientist-v2模块
from ai_scientist.llm import create_client
from ai_scientist.perform_ideation_temp_free import generate_temp_free_idea


def create_workshop_description_from_topic(topic: str) -> str:
    """从研究问题创建workshop描述"""
    return f"""# Research Topic: {topic}

## Keywords
research, hypothesis generation, scientific discovery

## TL;DR
Generate novel research ideas and hypotheses related to: {topic}

## Abstract
This research aims to explore and generate novel hypotheses related to the following topic: {topic}

The goal is to propose innovative research directions that address this topic through novel approaches, methodologies, or insights. We seek ideas that are:
- Novel and not trivial extensions of existing work
- Feasible to test with reasonable resources
- Potentially high-impact for the research community
- Clearly distinguishable from related work
"""


def main():
    parser = argparse.ArgumentParser(description="AI-Scientist-v2 Comparative Runner")
    parser.add_argument(
        "--topic",
        type=str,
        required=True,
        help="Research question/topic to explore"
    )
    parser.add_argument(
        "--save_file",
        type=str,
        default="Myexamples/comparative_experiments/AI-Scientist-v2/results",
        help="Directory to save results (default: Myexamples/comparative_experiments/AI-Scientist-v2/results)"
    )
    parser.add_argument(
        "--output_file",
        type=str,
        default="result.json",
        help="Output JSON filename"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="qwen-plus",
        help="LLM model to use (default: qwen-plus, will use Qwen API via OpenAI-compatible interface)"
    )
    parser.add_argument(
        "--max_generations",
        type=int,
        default=5,
        help="Maximum number of idea generations (recommended: 3-5)"
    )
    parser.add_argument(
        "--num_reflections",
        type=int,
        default=3,
        help="Number of reflection rounds per idea (recommended: 3-5, minimum 2)"
    )
    
    args = parser.parse_args()
    
    print("="*80)
    print("🔬 AI-Scientist-v2 Comparative Runner")
    print("="*80)
    print(f"Topic: {args.topic}")
    print(f"Model: {args.model} (via Qwen API)")
    print(f"API Key: {os.environ.get('QWEN_API_KEY', 'Not set')[:20]}...")
    print(f"Base URL: {os.environ.get('QWEN_API_BASE_URL', os.environ.get('OPENAI_BASE_URL', 'Not set'))}")
    print("="*80)
    
    # 创建输出目录
    os.makedirs(args.save_file, exist_ok=True)
    
    # 创建workshop描述
    workshop_description = create_workshop_description_from_topic(args.topic)
    
    # 保存workshop描述到临时文件
    workshop_file = os.path.join(args.save_file, "workshop_topic.md")
    with open(workshop_file, 'w', encoding='utf-8') as f:
        f.write(workshop_description)
    
    # 创建LLM客户端（使用已配置的Qwen API，通过OpenAI兼容接口）
    # 模型名称使用gpt-4o格式，但实际会通过base_url路由到Qwen API
    try:
        client, actual_model = create_client(args.model)
        print(f"✅ LLM Client created: {actual_model} (via Qwen API at {os.environ.get('OPENAI_BASE_URL')})")
    except Exception as e:
        print(f"⚠️  Warning: Failed to create client for {args.model}: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # 生成想法
    idea_fname = os.path.join(args.save_file, "ideas.json")
    
    print("\n🚀 Starting idea generation...")
    print(f"   Max generations: {args.max_generations}")
    print(f"   Reflections per idea: {args.num_reflections}")
    print()
    
    try:
        ideas = generate_temp_free_idea(
            idea_fname=idea_fname,
            client=client,
            model=actual_model,  # 使用实际模型名称
            workshop_description=workshop_description,
            max_num_generations=args.max_generations,
            num_reflections=args.num_reflections,
            reload_ideas=False
        )
        
        if not ideas:
            print("❌ No ideas generated")
            return 1
        
        # 选择最好的想法（第一个）
        best_idea = ideas[0] if isinstance(ideas[0], dict) else json.loads(ideas[0])
        
        print("\n✅ Idea generation completed!")
        print(f"   Generated {len(ideas)} ideas")
        print(f"   Selected best idea: {best_idea.get('Name', 'Unknown')}")
        
        # 提取Final Idea文本（用于评估系统）
        idea_text = ""
        if best_idea.get("Title"):
            idea_text += f"**Title:** {best_idea.get('Title')}\n\n"
        if best_idea.get("Short Hypothesis"):
            idea_text += f"**Hypothesis:** {best_idea.get('Short Hypothesis')}\n\n"
        if best_idea.get("Abstract"):
            idea_text += f"**Abstract:**\n{best_idea.get('Abstract')}\n\n"
        if best_idea.get("Related Work"):
            idea_text += f"**Related Work:**\n{best_idea.get('Related Work')}\n\n"
        if best_idea.get("Experiments"):
            idea_text += f"**Proposed Experiments:**\n{best_idea.get('Experiments')}\n\n"
        
        idea_text = idea_text.strip()
        
        # 保存结果
        result = {
            "idea": idea_text,
            "idea_dict": best_idea,
            "all_ideas": ideas[:3] if len(ideas) > 3 else ideas,  # 保存前3个想法
            "topic": args.topic,
            "timestamp": datetime.now().isoformat()
        }
        
        output_path = os.path.join(args.save_file, args.output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Result saved to: {output_path}")
        
        # 输出Final Idea（用于评估系统提取）
        print("\n" + "="*80)
        print("Final Idea:")
        print("="*80)
        print(idea_text)
        print("="*80)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error during idea generation: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
