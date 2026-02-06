#!/usr/bin/env python3
"""
Neo4j 知识图谱创建脚本
根据CSV文件创建 Paper -> ResearchQuestion -> Solution 的层级结构
"""

import csv
import sys
from neo4j import GraphDatabase
from tqdm import tqdm

# Neo4j 连接配置
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "neo4j123"  # 请根据实际情况修改密码

# CSV 文件路径
CSV_FILE = "/root/autodl-tmp/data/all_merged (1).csv"


def get_paper_properties(row):
    """
    提取 Paper 实体的属性 (列 1-5, 7-11, 28)
    列索引: 0=doi, 1=title, 2=authors, 3=year, 4=conference, 
           6=citationcount, 7=abstract, 8=core_problem, 9=related_work, 
           10=preliminary_innovation_analysis, 27=framework_summary
    """
    return {
        "doi": row[0],
        "title": row[1],
        "authors": row[2],
        "year": row[3],
        "conference": row[4],
        "citationcount": row[6],
        "abstract": row[7],
        "core_problem": row[8],
        "related_work": row[9],
        "preliminary_innovation_analysis": row[10],
        "framework_summary": row[27]
    }


def get_research_question_properties(row, idx):
    """
    提取 ResearchQuestion 实体的属性
    idx: 1, 2, 3, 4 对应 research_question_1~4
    列索引: 11=rq1, 15=rq2, 19=rq3, 23=rq4
    """
    rq_cols = {1: 11, 2: 15, 3: 19, 4: 23}
    col_idx = rq_cols.get(idx)
    if col_idx is None or col_idx >= len(row):
        return None
    rq_text = row[col_idx].strip()
    if not rq_text:
        return None
    return {
        "doi": row[0],
        f"research_question_{idx}": rq_text
    }


def get_solution_properties(row, idx):
    """
    提取 Solution 实体的属性
    idx: 1, 2, 3, 4 对应 solution_1~4
    列索引: 13=sol1, 17=sol2, 21=sol3, 25=sol4
    """
    sol_cols = {1: 13, 2: 17, 3: 21, 4: 25}
    col_idx = sol_cols.get(idx)
    if col_idx is None or col_idx >= len(row):
        return None
    sol_text = row[col_idx].strip()
    if not sol_text:
        return None
    return {
        "doi": row[0],
        f"solution_{idx}": sol_text
    }


def create_paper_node(tx, properties):
    """创建 Paper 节点"""
    query = """
    MERGE (p:Paper {doi: $doi})
    SET p.title = $title,
        p.authors = $authors,
        p.year = $year,
        p.conference = $conference,
        p.citationcount = $citationcount,
        p.abstract = $abstract,
        p.core_problem = $core_problem,
        p.related_work = $related_work,
        p.preliminary_innovation_analysis = $preliminary_innovation_analysis,
        p.framework_summary = $framework_summary
    RETURN p
    """
    tx.run(query, **properties)


def create_research_question_node(tx, doi, idx, properties):
    """创建 ResearchQuestion 节点"""
    node_name = f"rq{idx}"
    query = f"""
    MERGE (rq:ResearchQuestion {{doi: $doi, idx: $idx}})
    SET rq.name = $node_name,
        rq.research_question = $rq_text
    RETURN rq
    """
    tx.run(query, doi=doi, idx=idx, node_name=node_name, 
           rq_text=properties.get(f"research_question_{idx}", ""))


def create_solution_node(tx, doi, idx, properties):
    """创建 Solution 节点"""
    node_name = f"sol{idx}"
    query = f"""
    MERGE (sol:Solution {{doi: $doi, idx: $idx}})
    SET sol.name = $node_name,
        sol.solution = $sol_text
    RETURN sol
    """
    tx.run(query, doi=doi, idx=idx, node_name=node_name,
           sol_text=properties.get(f"solution_{idx}", ""))


def create_relationships(tx, doi, rq_count):
    """
    创建关系:
    - Paper -> ResearchQuestion (raise)
    - ResearchQuestion -> Paper (raised_by)
    - ResearchQuestion -> Solution (solved_by)
    """
    for i in range(1, rq_count + 1):
        # Paper -> ResearchQuestion (raise)
        query1 = """
        MATCH (p:Paper {doi: $doi}), (rq:ResearchQuestion {doi: $doi, idx: $idx})
        MERGE (p)-[:raise]->(rq)
        """
        tx.run(query1, doi=doi, idx=i)
        
        # ResearchQuestion -> Paper (raised_by)
        query2 = """
        MATCH (p:Paper {doi: $doi}), (rq:ResearchQuestion {doi: $doi, idx: $idx})
        MERGE (rq)-[:raised_by]->(p)
        """
        tx.run(query2, doi=doi, idx=i)
        
        # ResearchQuestion -> Solution (solved_by)
        query3 = """
        MATCH (rq:ResearchQuestion {doi: $doi, idx: $idx}), (sol:Solution {doi: $doi, idx: $idx})
        MERGE (rq)-[:solved_by]->(sol)
        """
        tx.run(query3, doi=doi, idx=i)


def process_csv(driver, limit=None):
    """处理CSV文件并创建知识图谱"""
    
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)  # 跳过表头
        
        rows = list(reader)
        if limit:
            rows = rows[:limit]
        
        print(f"开始处理 {len(rows)} 条记录...")
        
        with driver.session() as session:
            # 首先创建约束和索引
            print("创建约束和索引...")
            try:
                session.run("CREATE CONSTRAINT paper_doi IF NOT EXISTS FOR (p:Paper) REQUIRE p.doi IS UNIQUE")
                session.run("CREATE INDEX paper_year IF NOT EXISTS FOR (p:Paper) ON (p.year)")
                session.run("CREATE INDEX paper_conference IF NOT EXISTS FOR (p:Paper) ON (p.conference)")
            except Exception as e:
                print(f"约束/索引创建警告（可能已存在）: {e}")
            
            # 处理每一行
            for row in tqdm(rows, desc="创建节点"):
                if len(row) < 28:
                    continue
                
                doi = row[0]
                if not doi or not doi.startswith('10.'):
                    continue
                
                # 1. 创建 Paper 节点
                paper_props = get_paper_properties(row)
                session.execute_write(create_paper_node, paper_props)
                
                # 2. 创建 ResearchQuestion 和 Solution 节点
                rq_count = 0
                for i in range(1, 5):
                    rq_props = get_research_question_properties(row, i)
                    sol_props = get_solution_properties(row, i)
                    
                    if rq_props and sol_props:
                        session.execute_write(create_research_question_node, doi, i, rq_props)
                        session.execute_write(create_solution_node, doi, i, sol_props)
                        rq_count += 1
                
                # 3. 创建关系
                if rq_count > 0:
                    session.execute_write(create_relationships, doi, rq_count)
        
        print(f"✅ 成功处理 {len(rows)} 条记录")


def verify_graph(driver):
    """验证图谱创建结果"""
    with driver.session() as session:
        print("\n" + "="*60)
        print("知识图谱验证结果")
        print("="*60)
        
        # 统计各类节点数量
        result = session.run("MATCH (p:Paper) RETURN count(p) as count")
        paper_count = result.single()["count"]
        print(f"📄 Paper 节点数量: {paper_count:,}")
        
        result = session.run("MATCH (rq:ResearchQuestion) RETURN count(rq) as count")
        rq_count = result.single()["count"]
        print(f"❓ ResearchQuestion 节点数量: {rq_count:,}")
        
        result = session.run("MATCH (sol:Solution) RETURN count(sol) as count")
        sol_count = result.single()["count"]
        print(f"💡 Solution 节点数量: {sol_count:,}")
        
        # 统计关系数量
        result = session.run("MATCH ()-[r:raise]->() RETURN count(r) as count")
        raise_count = result.single()["count"]
        print(f"\n🔗 raise 关系数量: {raise_count:,}")
        
        result = session.run("MATCH ()-[r:raised_by]->() RETURN count(r) as count")
        raised_by_count = result.single()["count"]
        print(f"🔗 raised_by 关系数量: {raised_by_count:,}")
        
        result = session.run("MATCH ()-[r:solved_by]->() RETURN count(r) as count")
        solved_by_count = result.single()["count"]
        print(f"🔗 solved_by 关系数量: {solved_by_count:,}")
        
        # 显示样本数据
        print("\n📊 样本数据预览:")
        result = session.run("""
            MATCH (p:Paper)-[:raise]->(rq:ResearchQuestion)-[:solved_by]->(sol:Solution)
            RETURN p.doi as doi, p.title as title, rq.name as rq_name, sol.name as sol_name
            LIMIT 3
        """)
        for record in result:
            print(f"  - DOI: {record['doi'][:40]}...")
            print(f"    Title: {record['title'][:50]}...")
            print(f"    {record['rq_name']} -> {record['sol_name']}")
            print()


def main():
    print("="*60)
    print("Neo4j 知识图谱创建工具")
    print("="*60)
    print(f"连接地址: {NEO4J_URI}")
    print(f"CSV文件: {CSV_FILE}")
    print("="*60)
    
    try:
        # 连接 Neo4j
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        
        # 测试连接
        with driver.session() as session:
            result = session.run("RETURN '连接成功' as message")
            print(result.single()["message"])
        
        # 清空现有数据（可选）
        response = input("\n是否清空现有数据? (y/n): ").lower()
        if response == 'y':
            with driver.session() as session:
                session.run("MATCH (n) DETACH DELETE n")
                print("✅ 已清空现有数据")
        
        # 处理CSV
        limit_input = input("\n限制处理记录数（直接回车处理全部）: ").strip()
        limit = int(limit_input) if limit_input.isdigit() else None
        
        process_csv(driver, limit)
        
        # 验证结果
        verify_graph(driver)
        
        # 显示浏览器访问地址
        print("\n" + "="*60)
        print("🌐 浏览器访问地址")
        print("="*60)
        print("Neo4j Browser: http://localhost:7474")
        print(f"用户名: {NEO4J_USER}")
        print(f"密码: {NEO4J_PASSWORD}")
        print("\n常用查询语句:")
        print("  - 查看所有节点: MATCH (n) RETURN n LIMIT 25")
        print("  - 查看Paper节点: MATCH (p:Paper) RETURN p LIMIT 10")
        print("  - 查看关系: MATCH (p:Paper)-[r]->(n) RETURN p, r, n LIMIT 10")
        print("="*60)
        
        driver.close()
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        print("\n请检查:")
        print("  1. Neo4j 服务是否已启动 (neo4j status)")
        print("  2. 连接配置是否正确 (URI, 用户名, 密码)")
        print("  3. CSV 文件路径是否正确")
        sys.exit(1)


if __name__ == "__main__":
    main()
