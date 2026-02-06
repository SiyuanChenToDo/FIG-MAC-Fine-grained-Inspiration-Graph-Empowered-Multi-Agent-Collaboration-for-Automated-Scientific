#!/usr/bin/env python3
"""
Neo4j 连接测试脚本
用于测试本地到远程Neo4j数据库的连接和查询

使用说明:
1. 先建立 SSH 隧道: ssh -N -L 7687:localhost:7687 root@<服务器IP>
2. 运行脚本: python test_neo4j_connection.py
"""

import sys
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError

# 连接配置
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "neo4j123"


def test_connection():
    """测试基本连接"""
    print("=" * 60)
    print("🔌 测试 Neo4j 连接")
    print("=" * 60)
    print(f"连接地址: {NEO4J_URI}")
    print(f"用户名: {NEO4J_USER}")
    print("-" * 60)
    
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
        print("✅ 连接成功!")
        driver.close()
        return True
    except ServiceUnavailable as e:
        print(f"❌ 连接失败: 服务不可用")
        print(f"   错误信息: {e}")
        print("\n💡 请检查:")
        print("   1. SSH 隧道是否已建立: ssh -N -L 7687:localhost:7687 root@<服务器IP>")
        print("   2. Neo4j 服务是否运行: neo4j status")
        return False
    except AuthError as e:
        print(f"❌ 认证失败: 用户名或密码错误")
        print(f"   错误信息: {e}")
        return False
    except Exception as e:
        print(f"❌ 未知错误: {e}")
        return False


def test_basic_queries(driver):
    """测试基本查询"""
    print("\n" + "=" * 60)
    print("📊 基本统计查询")
    print("=" * 60)
    
    queries = [
        ("总节点数", "MATCH (n) RETURN count(n) as count"),
        ("Paper 节点数", "MATCH (p:Paper) RETURN count(p) as count"),
        ("ResearchQuestion 节点数", "MATCH (rq:ResearchQuestion) RETURN count(rq) as count"),
        ("Solution 节点数", "MATCH (sol:Solution) RETURN count(sol) as count"),
    ]
    
    with driver.session() as session:
        for name, query in queries:
            try:
                result = session.run(query)
                count = result.single()["count"]
                print(f"  {name}: {count:,}")
            except Exception as e:
                print(f"  {name}: 查询失败 - {e}")


def test_relationships(driver):
    """测试关系查询"""
    print("\n" + "=" * 60)
    print("🔗 关系统计")
    print("=" * 60)
    
    queries = [
        ("raise 关系", "MATCH ()-[r:raise]->() RETURN count(r) as count"),
        ("raised_by 关系", "MATCH ()-[r:raised_by]->() RETURN count(r) as count"),
        ("solved_by 关系", "MATCH ()-[r:solved_by]->() RETURN count(r) as count"),
    ]
    
    with driver.session() as session:
        for name, query in queries:
            try:
                result = session.run(query)
                count = result.single()["count"]
                print(f"  {name}: {count:,}")
            except Exception as e:
                print(f"  {name}: 查询失败 - {e}")


def test_sample_data(driver):
    """测试样本数据查询"""
    print("\n" + "=" * 60)
    print("📋 样本数据")
    print("=" * 60)
    
    with driver.session() as session:
        # 查询一个Paper样本
        print("\n📄 Paper 样本:")
        result = session.run("""
            MATCH (p:Paper)
            RETURN p.doi as doi, p.title as title, p.year as year, p.conference as conf
            LIMIT 1
        """)
        for record in result:
            print(f"  DOI: {record['doi']}")
            print(f"  Title: {record['title'][:80]}...")
            print(f"  Year: {record['year']}, Conference: {record['conf']}")
        
        # 查询层级结构
        print("\n🔗 层级结构样本 (Paper -> RQ -> Solution):")
        result = session.run("""
            MATCH (p:Paper)-[:raise]->(rq:ResearchQuestion)-[:solved_by]->(sol:Solution)
            RETURN p.title as paper, rq.name as rq_name, rq.research_question as rq_text,
                   sol.name as sol_name
            LIMIT 2
        """)
        for i, record in enumerate(result, 1):
            print(f"\n  示例 {i}:")
            print(f"    Paper: {record['paper'][:60]}...")
            print(f"    {record['rq_name']}: {record['rq_text'][:60]}...")
            print(f"    {record['sol_name']}: solved_by 关系已建立")


def test_year_distribution(driver):
    """测试年份分布"""
    print("\n" + "=" * 60)
    print("📅 Paper 年份分布 (Top 5)")
    print("=" * 60)
    
    with driver.session() as session:
        result = session.run("""
            MATCH (p:Paper)
            WHERE p.year IS NOT NULL AND p.year <> ''
            RETURN p.year as year, count(p) as count
            ORDER BY count DESC
            LIMIT 5
        """)
        for record in result:
            print(f"  {record['year']}: {record['count']:,} 篇")


def test_conference_distribution(driver):
    """测试会议分布"""
    print("\n" + "=" * 60)
    print("🏛️  Paper 会议分布 (Top 5)")
    print("=" * 60)
    
    with driver.session() as session:
        result = session.run("""
            MATCH (p:Paper)
            WHERE p.conference IS NOT NULL AND p.conference <> ''
            RETURN p.conference as conf, count(p) as count
            ORDER BY count DESC
            LIMIT 5
        """)
        for record in result:
            print(f"  {record['conf']}: {record['count']:,} 篇")


def search_paper_by_keyword(driver, keyword="neural"):
    """按关键词搜索论文"""
    print("\n" + "=" * 60)
    print(f"🔍 搜索论文 (关键词: '{keyword}')")
    print("=" * 60)
    
    with driver.session() as session:
        result = session.run("""
            MATCH (p:Paper)
            WHERE p.title CONTAINS $keyword
            RETURN p.doi as doi, p.title as title, p.year as year
            LIMIT 3
        """, keyword=keyword)
        
        count = 0
        for record in result:
            count += 1
            print(f"\n  [{count}] {record['year']} - {record['title'][:70]}...")
            print(f"      DOI: {record['doi']}")
        
        if count == 0:
            print(f"  未找到包含 '{keyword}' 的论文")


def interactive_search(driver):
    """交互式搜索"""
    print("\n" + "=" * 60)
    print("💬 交互式论文搜索")
    print("=" * 60)
    print("输入关键词搜索论文 (或输入 'q' 退出):")
    
    while True:
        keyword = input("\n关键词: ").strip()
        if keyword.lower() == 'q':
            break
        if not keyword:
            continue
        
        with driver.session() as session:
            result = session.run("""
                MATCH (p:Paper)
                WHERE p.title CONTAINS $keyword
                RETURN p.doi as doi, p.title as title, p.year as year
                LIMIT 5
            """, keyword=keyword)
            
            records = list(result)
            if not records:
                print(f"  未找到包含 '{keyword}' 的论文")
            else:
                print(f"  找到 {len(records)} 篇论文:")
                for i, record in enumerate(records, 1):
                    print(f"  {i}. [{record['year']}] {record['title'][:60]}...")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("🚀 Neo4j 连接测试工具")
    print("=" * 60)
    
    # 测试连接
    if not test_connection():
        sys.exit(1)
    
    # 建立连接
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        # 运行各项测试
        test_basic_queries(driver)
        test_relationships(driver)
        test_sample_data(driver)
        test_year_distribution(driver)
        test_conference_distribution(driver)
        search_paper_by_keyword(driver, "neural")
        search_paper_by_keyword(driver, "learning")
        
        # 询问是否进入交互式搜索
        print("\n" + "=" * 60)
        response = input("是否进入交互式搜索模式? (y/n): ").strip().lower()
        if response == 'y':
            interactive_search(driver)
        
        print("\n" + "=" * 60)
        print("✅ 所有测试完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试过程中出错: {e}")
    finally:
        driver.close()


if __name__ == "__main__":
    main()
