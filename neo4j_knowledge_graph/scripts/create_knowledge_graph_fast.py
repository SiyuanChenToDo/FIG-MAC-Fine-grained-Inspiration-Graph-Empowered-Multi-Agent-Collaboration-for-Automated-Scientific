#!/usr/bin/env python3
"""
Neo4j 知识图谱创建脚本 - 优化版本（使用批量导入）
根据CSV文件创建 Paper -> ResearchQuestion -> Solution 的层级结构
"""

import csv
import sys
import time
from neo4j import GraphDatabase
from tqdm import tqdm

# Neo4j 连接配置
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "neo4j123"

# CSV 文件路径
CSV_FILE = "/root/autodl-tmp/data/all_merged (1).csv"

# 批量大小
BATCH_SIZE = 100


def get_paper_properties(row):
    """提取 Paper 实体的属性 (列 1-5, 7-11, 28)"""
    return {
        "doi": row[0],
        "title": row[1],
        "authors": row[2],
        "year": row[3],
        "conference": row[4],
        "citationcount": row[6] if row[6] else "0",
        "abstract": row[7],
        "core_problem": row[8],
        "related_work": row[9],
        "preliminary_innovation_analysis": row[10],
        "framework_summary": row[27]
    }


def create_batch_nodes(tx, batch_data):
    """批量创建节点"""
    # 批量创建 Paper 节点
    paper_query = """
    UNWIND $papers as paper
    MERGE (p:Paper {doi: paper.doi})
    SET p.title = paper.title,
        p.authors = paper.authors,
        p.year = paper.year,
        p.conference = paper.conference,
        p.citationcount = paper.citationcount,
        p.abstract = paper.abstract,
        p.core_problem = paper.core_problem,
        p.related_work = paper.related_work,
        p.preliminary_innovation_analysis = paper.preliminary_innovation_analysis,
        p.framework_summary = paper.framework_summary
    """
    tx.run(paper_query, papers=batch_data['papers'])
    
    # 批量创建 ResearchQuestion 节点
    rq_query = """
    UNWIND $rqs as rq
    MERGE (r:ResearchQuestion {doi: rq.doi, idx: rq.idx})
    SET r.name = rq.name, r.research_question = rq.text
    """
    tx.run(rq_query, rqs=batch_data['rqs'])
    
    # 批量创建 Solution 节点
    sol_query = """
    UNWIND $sols as sol
    MERGE (s:Solution {doi: sol.doi, idx: sol.idx})
    SET s.name = sol.name, s.solution = sol.text
    """
    tx.run(sol_query, sols=batch_data['sols'])
    
    # 批量创建 raise 关系
    raise_query = """
    UNWIND $relations as rel
    MATCH (p:Paper {doi: rel.doi}), (r:ResearchQuestion {doi: rel.doi, idx: rel.idx})
    MERGE (p)-[:raise]->(r)
    """
    tx.run(raise_query, relations=batch_data['relations'])
    
    # 批量创建 raised_by 关系
    raised_by_query = """
    UNWIND $relations as rel
    MATCH (p:Paper {doi: rel.doi}), (r:ResearchQuestion {doi: rel.doi, idx: rel.idx})
    MERGE (r)-[:raised_by]->(p)
    """
    tx.run(raised_by_query, relations=batch_data['relations'])
    
    # 批量创建 solved_by 关系
    solved_by_query = """
    UNWIND $relations as rel
    MATCH (r:ResearchQuestion {doi: rel.doi, idx: rel.idx}), (s:Solution {doi: rel.doi, idx: rel.idx})
    MERGE (r)-[:solved_by]->(s)
    """
    tx.run(solved_by_query, relations=batch_data['relations'])


def process_csv_batch(driver, limit=None):
    """批量处理CSV文件"""
    
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)
        
        rows = list(reader)
        if limit:
            rows = rows[:limit]
        
        total = len(rows)
        print(f"开始处理 {total} 条记录...")
        
        # 预创建约束和索引
        with driver.session() as session:
            print("创建约束和索引...")
            try:
                session.run("CREATE CONSTRAINT paper_doi IF NOT EXISTS FOR (p:Paper) REQUIRE p.doi IS UNIQUE")
                session.run("CREATE CONSTRAINT rq_doi_idx IF NOT EXISTS FOR (r:ResearchQuestion) REQUIRE (r.doi, r.idx) IS UNIQUE")
                session.run("CREATE CONSTRAINT sol_doi_idx IF NOT EXISTS FOR (s:Solution) REQUIRE (s.doi, s.idx) IS UNIQUE")
                session.run("CREATE INDEX paper_year IF NOT EXISTS FOR (p:Paper) ON (p.year)")
                session.run("CREATE INDEX paper_conference IF NOT EXISTS FOR (p:Paper) ON (p.conference)")
            except Exception as e:
                print(f"约束/索引创建警告（可能已存在）: {e}")
        
        # 批量处理
        batch_data = {'papers': [], 'rqs': [], 'sols': [], 'relations': []}
        processed = 0
        
        with driver.session() as session:
            for row in tqdm(rows, desc="处理中"):
                if len(row) < 28:
                    continue
                
                doi = row[0]
                if not doi or not doi.startswith('10.'):
                    continue
                
                # Paper 数据
                paper_props = get_paper_properties(row)
                batch_data['papers'].append(paper_props)
                
                # RQ 和 Solution 数据
                rq_cols = [(11, 13), (15, 17), (19, 21), (23, 25)]
                for idx, (rq_col, sol_col) in enumerate(rq_cols, 1):
                    rq_text = row[rq_col].strip() if rq_col < len(row) else ""
                    sol_text = row[sol_col].strip() if sol_col < len(row) else ""
                    
                    if rq_text and sol_text:
                        batch_data['rqs'].append({
                            'doi': doi,
                            'idx': idx,
                            'name': f'rq{idx}',
                            'text': rq_text
                        })
                        batch_data['sols'].append({
                            'doi': doi,
                            'idx': idx,
                            'name': f'sol{idx}',
                            'text': sol_text
                        })
                        batch_data['relations'].append({'doi': doi, 'idx': idx})
                
                # 达到批量大小则提交
                if len(batch_data['papers']) >= BATCH_SIZE:
                    session.execute_write(create_batch_nodes, batch_data)
                    processed += len(batch_data['papers'])
                    batch_data = {'papers': [], 'rqs': [], 'sols': [], 'relations': []}
            
            # 处理剩余数据
            if batch_data['papers']:
                session.execute_write(create_batch_nodes, batch_data)
                processed += len(batch_data['papers'])
        
        print(f"✅ 成功处理 {processed} 条记录")


def verify_graph(driver):
    """验证图谱创建结果"""
    with driver.session() as session:
        print("\n" + "="*60)
        print("知识图谱验证结果")
        print("="*60)
        
        result = session.run("MATCH (p:Paper) RETURN count(p) as count")
        paper_count = result.single()["count"]
        print(f"📄 Paper 节点数量: {paper_count:,}")
        
        result = session.run("MATCH (rq:ResearchQuestion) RETURN count(rq) as count")
        rq_count = result.single()["count"]
        print(f"❓ ResearchQuestion 节点数量: {rq_count:,}")
        
        result = session.run("MATCH (sol:Solution) RETURN count(sol) as count")
        sol_count = result.single()["count"]
        print(f"💡 Solution 节点数量: {sol_count:,}")
        
        result = session.run("MATCH ()-[r:raise]->() RETURN count(r) as count")
        raise_count = result.single()["count"]
        print(f"\n🔗 raise 关系数量: {raise_count:,}")
        
        result = session.run("MATCH ()-[r:raised_by]->() RETURN count(r) as count")
        raised_by_count = result.single()["count"]
        print(f"🔗 raised_by 关系数量: {raised_by_count:,}")
        
        result = session.run("MATCH ()-[r:solved_by]->() RETURN count(r) as count")
        solved_by_count = result.single()["count"]
        print(f"🔗 solved_by 关系数量: {solved_by_count:,}")
        
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


def main():
    print("="*60)
    print("Neo4j 知识图谱创建工具 (优化版)")
    print("="*60)
    print(f"连接地址: {NEO4J_URI}")
    print(f"CSV文件: {CSV_FILE}")
    print(f"批量大小: {BATCH_SIZE}")
    print("="*60)
    
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        
        with driver.session() as session:
            result = session.run("RETURN '连接成功' as message")
            print(result.single()["message"])
        
        response = input("\n是否清空现有数据? (y/n): ").lower()
        if response == 'y':
            with driver.session() as session:
                session.run("MATCH (n) DETACH DELETE n")
                print("✅ 已清空现有数据")
        
        limit_input = input("\n限制处理记录数（直接回车处理全部）: ").strip()
        limit = int(limit_input) if limit_input.isdigit() else None
        
        start_time = time.time()
        process_csv_batch(driver, limit)
        elapsed = time.time() - start_time
        
        print(f"\n⏱️  处理时间: {elapsed/60:.1f} 分钟")
        
        verify_graph(driver)
        
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
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
