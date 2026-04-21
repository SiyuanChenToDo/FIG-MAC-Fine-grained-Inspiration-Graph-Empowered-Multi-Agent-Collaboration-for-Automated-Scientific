#!/usr/bin/env python3
"""
CoI-Agent对比运行脚本 - 使用用户的实际VDB数据
在运行时替换SementicSearcher为CoISearcherQwen
"""
import os
import sys
import argparse
import yaml
import json

# 设置环境变量
os.environ['PYTHONUNBUFFERED'] = '1'

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

# 加载config.yaml并设置环境变量（但不会覆盖我们已设置的关键配置）
config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
if os.path.exists(config_path):
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)
    for key, value in config.items():
        if value == "":
            continue
        else:
            # 跳过会覆盖我们配置的关键项
            if key not in ["is_azure", "OPENAI_API_KEY", "OPENAI_BASE_URL"]:
                os.environ[key] = str(value)

# 强制设置关键配置（在 config.yaml 之后，确保不被覆盖）
os.environ["is_azure"] = "False"  # 使用 OpenAI 兼容接口，不是 Azure
os.environ["OPENAI_API_KEY"] = os.environ["QWEN_API_KEY"]  # 确保使用我们的 API Key
os.environ["OPENAI_BASE_URL"] = DASH_SCOPE_BASE_URL  # 确保使用我们的 Base URL

# 设置LLM模型（使用Qwen模型名称）
if "MAIN_LLM_MODEL" not in os.environ or os.environ["MAIN_LLM_MODEL"] == "":
    os.environ["MAIN_LLM_MODEL"] = "qwen-plus"  # 使用Qwen模型
if "CHEAP_LLM_MODEL" not in os.environ or os.environ["CHEAP_LLM_MODEL"] == "":
    os.environ["CHEAP_LLM_MODEL"] = "qwen-plus"  # 使用Qwen模型

# 设置embedding（如果未设置，使用主LLM的配置）
if "EMBEDDING_API_KEY" not in os.environ or os.environ["EMBEDDING_API_KEY"] == "":
    os.environ["EMBEDDING_API_KEY"] = os.environ["QWEN_API_KEY"]
# 注意：EMBEDDING_API_ENDPOINT 只在 Azure 模式下使用，我们使用 OPENAI_BASE_URL
if "EMBEDDING_MODEL" not in os.environ or os.environ["EMBEDDING_MODEL"] == "":
    os.environ["EMBEDDING_MODEL"] = "text-embedding-v2"

# 设置VDB相关环境变量（在导入之前）
os.environ["COI_USE_REAL_VDB"] = "1"
os.environ["COI_VDB_PATH"] = os.environ.get("COI_VDB_PATH", "/root/autodl-tmp/Myexamples/vdb/camel_faiss_storage")

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 现在导入searcher（__init__.py会自动使用CoISearcherQwen）
# 注意：由于我们已经修复了scipdf导入问题，这里应该可以正常导入
from searcher import SementicSearcher, Result

# 导入agents（它会使用我们替换的Searcher）
from agents import DeepResearchAgent, ReviewAgent, get_llms
import asyncio
import nest_asyncio

nest_asyncio.apply()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", type=str, required=True, help="research topic")
    parser.add_argument("--anchor_paper_path", type=str, default=None, help="PDF path of the anchor paper")
    parser.add_argument("--save_file", type=str, default="saves/", help="save file path")
    parser.add_argument("--improve_cnt", type=int, default=1, help="experiment refine count")
    parser.add_argument("--max_chain_length", type=int, default=5, help="max chain length")
    parser.add_argument("--min_chain_length", type=int, default=3, help="min chain length")
    parser.add_argument("--max_chain_numbers", type=int, default=1, help="max chain numbers")
    parser.add_argument("--output_file", type=str, default="result.json", help="output result file")
    
    args = parser.parse_args()

    main_llm, cheap_llm = get_llms()

    topic = args.topic
    anchor_paper_path = args.anchor_paper_path

    print(f"🚀 Launching CoI-Agent with Real VDB on Topic: '{topic}'...")
    print(f"📁 VDB Path: {os.environ.get('COI_VDB_PATH', '/root/autodl-tmp/Myexamples/vdb/camel_faiss_storage')}")

    # 创建agents（会自动使用我们替换的Searcher）
    review_agent = ReviewAgent(save_file=args.save_file, llm=main_llm, cheap_llm=cheap_llm)
    deep_research_agent = DeepResearchAgent(
        llm=main_llm, 
        cheap_llm=cheap_llm,
        **vars(args)
    )

    print(f"begin to generate idea and experiment of topic {topic}")
    idea, related_experiments, entities, idea_chain, ideas, trend, future, human, year = asyncio.run(
        deep_research_agent.generate_idea_with_chain(topic, anchor_paper_path)
    )
    experiment = asyncio.run(
        deep_research_agent.generate_experiment(idea, related_experiments, entities)
    )

    for i in range(args.improve_cnt):
        experiment = asyncio.run(
            deep_research_agent.improve_experiment(review_agent, idea, experiment, entities)
        )
        
    print(f"succeed to generate idea and experiment of topic {topic}")
    
    # 保存结果
    # 确保 idea 是字符串格式（用于评估系统）
    idea_text = idea
    if isinstance(idea, dict):
        # 如果是字典，转换为完整的文本格式
        idea_text = ""
        if idea.get("title"):
            idea_text += f"**Title:** {idea.get('title')}\n\n"
        if idea.get("motivation"):
            idea_text += f"**Origins and Motivation:**\n{idea.get('motivation')}\n\n"
        if idea.get("novelty"):
            idea_text += f"**Novelty and Differences from Prior Work:**\n{idea.get('novelty')}\n\n"
        if idea.get("method"):
            idea_text += f"**Core Methodology:**\n{idea.get('method')}\n\n"
        idea_text = idea_text.strip()
    elif not isinstance(idea, str):
        idea_text = str(idea)
    
    res = {
        "idea": idea_text,  # 保存为字符串格式，便于评估系统提取
        "idea_dict": idea if isinstance(idea, dict) else None,  # 同时保存原始字典（如果有）
        "experiment": experiment,
        "related_experiments": related_experiments,
        "entities": entities,
        "idea_chain": idea_chain,
        "ideas": ideas,
        "trend": trend,
        "future": future,
        "year": year,
        "human": human
    }
    
    output_path = os.path.join(args.save_file, args.output_file) if args.save_file else args.output_file
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Result saved to: {output_path}")
    
    # 输出Final Idea（用于评估系统提取）
    print("\n" + "="*80)
    print("Final Idea:")
    print("="*80)
    print(idea_text)
    print("="*80)

