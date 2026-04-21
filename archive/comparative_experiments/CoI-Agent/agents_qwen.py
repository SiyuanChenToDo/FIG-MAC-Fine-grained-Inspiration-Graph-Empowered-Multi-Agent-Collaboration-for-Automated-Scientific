"""
CoI-Agent适配器 - 使用用户的实际VDB数据
修改agents.py以使用CoISearcherQwen替代SementicSearcher
"""
import json
import time
import asyncio
import os
import sys

# 在导入searcher之前，先导入我们的自定义searcher
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from searcher.coi_searcher_qwen import CoISearcherQwen, Result
# 保留原始导入以兼容其他功能
from searcher.sementic_search import Result as OriginalResult

# 导入原始agents模块的其他部分
from LLM import openai_llm
from prompts import *
from utils import extract


def get_llm(model="gpt4o-0513"):
    return openai_llm(model)


def get_llms():
    if "MAIN_LLM_MODEL" not in os.environ or os.environ["MAIN_LLM_MODEL"] == "":
        raise ValueError("MAIN_LLM_MODEL is not set")
    if "CHEAP_LLM_MODEL" not in os.environ or os.environ["CHEAP_LLM_MODEL"] == "":
        raise ValueError("CHEAP_LLM_MODEL is not set")
    main_llm = os.environ.get("MAIN_LLM_MODEL", "gpt4o-0513")
    cheap_llm = os.environ.get("CHEAP_LLM_MODEL", "gpt-4o-mini")
    main_llm = get_llm(main_llm)
    cheap_llm = get_llm(cheap_llm)
    return main_llm, cheap_llm


async def judge_idea(i, j, idea0, idea1, topic, llm):
    prompt = get_judge_idea_all_prompt(idea0, idea1, topic)
    messages = [{"role": "user", "content": prompt}]
    response = await llm.response_async(messages)
    novelty = extract(response, "novelty")
    relevance = extract(response, "relevance")
    significance = extract(response, "significance")
    clarity = extract(response, "clarity")
    feasibility = extract(response, "feasibility")
    effectiveness = extract(response, "effectiveness")
    return i, j, novelty, relevance, significance, clarity, feasibility, effectiveness


class ReviewAgent:
    def __init__(self, save_file="saves/", llm=None, cheap_llm=None, 
                 publicationData=None, real_vdb_path=None, **kwargs):
        self.paper_save_file = os.path.join(save_file, "review_papers")
        self.log_save_file = os.path.join(save_file, "review_logs")
        if not os.path.exists(self.paper_save_file):
            os.makedirs(self.paper_save_file)
        if not os.path.exists(self.log_save_file):
            os.makedirs(self.log_save_file)
        self.llm = llm
        self.cheap_llm = cheap_llm
        
        # 使用自定义Searcher
        self.reader = CoISearcherQwen(
            save_file=self.paper_save_file,
            real_vdb_path=real_vdb_path
        )
        self.read_papers = set()
        self.begin_time = time.time()
        self.review_suggestions = []
        self.review_idea_suggestions = []
        self.review_experiment_suggestions = []
        self.check_novel_results = []
        self.publicationData = publicationData

    def wrap_messages(self, prompt):
        return [{"role": "user", "content": prompt}]

    async def get_openai_response_async(self, messages):
        return await self.llm.response_async(messages)
    
    async def get_cheap_openai_response_async(self, messages):
        return await self.cheap_llm.response_async(messages)

    async def get_search_query(self, idea, topic):
        prompt = get_review_search_related_paper_prompt(idea, topic)
        messages = self.wrap_messages(prompt)
        response = await self.get_openai_response_async(messages)
        search_query = extract(response, "queries")
        try:
            search_query = json.loads(search_query)
        except:
            search_query = []
        return search_query
    
    async def get_suggestions_from_papers(self, papers, topic, idea):
        paper_content = ""
        for i, paper in enumerate(papers):
            paper_content += f"{i}.Title: {paper.title}, Abstract: {paper.abstract}\n"

        prompt = get_review_suggestions_from_papers_prompt(idea, topic, paper_content)
        messages = self.wrap_messages(prompt)
        response = await self.get_openai_response_async(messages)
        suggestions = extract(response, "suggestions")
        print(f"successfully get suggestions from paper {paper.title}")
        return suggestions

    async def review_experiment(self, idea, experiment, entities):
        prompt = get_review_experiment_design_suggestions_prompt(idea, experiment, entities)
        messages = self.wrap_messages(prompt)
        response = await self.get_cheap_openai_response_async(messages)
        suggestions = extract(response, "suggestion")
        review_suggestion = {"idea": idea, "experiment": experiment, "suggestions": suggestions}
        self.review_experiment_suggestions.append(review_suggestion)
        with open(os.path.join(self.log_save_file, "review_experiment_suggestions.json"), "w") as f:
            json.dump(self.review_experiment_suggestions, f)
        return suggestions


class DeepResearchAgent:
    def __init__(self, save_file="saves/", llm=None, cheap_llm=None, 
                 publicationData=None, ban_paper=[], real_vdb_path=None, **kwargs):
        self.paper_save_file = os.path.join(save_file, "deep_papers")
        self.log_save_file = os.path.join(save_file, "deep_logs")
        if not os.path.exists(self.paper_save_file):
            os.makedirs(self.paper_save_file)
        if not os.path.exists(self.log_save_file):
            os.makedirs(self.log_save_file)
        
        # 使用自定义Searcher
        self.reader = CoISearcherQwen(
            save_file=self.paper_save_file,
            ban_paper=ban_paper,
            real_vdb_path=real_vdb_path
        )
        self.begin_time = time.time()
        self.llm = llm
        self.cheap_llm = cheap_llm
        self.read_papers = set()
        self.paper_storage = []
        self.paper_info_for_refine_experiment = []
        self.search_qeuries = []
        self.deep_research_chains = []
        self.deep_ideas = []
        self.check_novel_results = []
        self.score_results = []
        self.topic = None

        self.publicationData = publicationData
        self.improve_cnt = kwargs.get("improve_cnt", 1)
        self.max_chain_length = kwargs.get("max_chain_length", 5)
        self.min_chain_length = kwargs.get("min_chain_length", 3)
        self.max_chain_numbers = kwargs.get("max_chain_numbers", 10)

    def wrap_messages(self, prompt):
        return [{"role": "user", "content": prompt}]

    async def get_openai_response_async(self, messages):
        return await self.llm.response_async(messages)
    
    async def get_cheap_openai_response_async(self, messages):
        return await self.cheap_llm.response_async(messages, max_tokens=16000)

    async def get_search_query(self, topic=None, query=None):
        prompt = get_deep_search_query_prompt(topic, query)
        messages = self.wrap_messages(prompt)
        response = await self.get_openai_response_async(messages)
        search_query = extract(response, "queries")
        try:
            search_query = json.loads(search_query)
            self.search_qeuries.append({"query": query, "search_query": search_query})
            with open(os.path.join(self.log_save_file, "search_queries.json"), "w") as f:
                json.dump(self.search_qeuries, f)
        except:
            search_query = [query]
        return search_query

    # 其他方法保持原样，但使用self.reader（已经是CoISearcherQwen）
    # 为了简化，我们直接导入原始agents.py的其他方法
    # 但需要确保所有使用self.reader的地方都能正常工作

    # 由于agents.py很长，我们采用另一种策略：
    # 在运行时动态替换SementicSearcher为CoISearcherQwen
    # 这样就不需要复制所有代码

