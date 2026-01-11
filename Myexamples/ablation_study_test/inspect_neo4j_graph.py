"""
Neo4j 知识图谱检查脚本
用于诊断图谱结构、节点属性和关系
"""

from camel.storages import Neo4jGraph
import json

# 连接到 Neo4j
print("=" * 60)
print("连接到 Neo4j 数据库...")
print("=" * 60)

n4j = Neo4jGraph(
    url="bolt://localhost:17687",
    username="neo4j",
    password="ai4sci123456",
)

print("✅ 连接成功!\n")

# 1. 查看所有节点标签
print("=" * 60)
print("1. 数据库中的所有节点标签")
print("=" * 60)

label_query = """
CALL db.labels() YIELD label
RETURN label
ORDER BY label
"""
labels = n4j.query(label_query)
print(f"共有 {len(labels)} 种节点标签:\n")
for item in labels:
    print(f"  - {item['label']}")

# 2. 查看每种标签的节点数量
print("\n" + "=" * 60)
print("2. 每种标签的节点数量")
print("=" * 60)

for item in labels:
    label = item['label']
    count_query = f"MATCH (n:{label}) RETURN count(n) as count"
    result = n4j.query(count_query)
    count = result[0]['count'] if result else 0
    print(f"  {label}: {count} 个节点")

# 3. 查看所有关系类型
print("\n" + "=" * 60)
print("3. 数据库中的所有关系类型")
print("=" * 60)

rel_query = """
CALL db.relationshipTypes() YIELD relationshipType
RETURN relationshipType
ORDER BY relationshipType
"""
rels = n4j.query(rel_query)
print(f"共有 {len(rels)} 种关系类型:\n")
for item in rels:
    print(f"  - {item['relationshipType']}")

# 4. 查看每种关系类型的数量
print("\n" + "=" * 60)
print("4. 每种关系类型的数量")
print("=" * 60)

for item in rels:
    rel_type = item['relationshipType']
    count_query = f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count"
    result = n4j.query(count_query)
    count = result[0]['count'] if result else 0
    print(f"  {rel_type}: {count} 条关系")

# 5. 查看 paper 节点的属性示例
print("\n" + "=" * 60)
print("5. Paper 节点的属性示例 (前3个)")
print("=" * 60)

paper_sample_query = """
MATCH (n:Paper)
RETURN n
LIMIT 3
"""
papers = n4j.query(paper_sample_query)
for i, item in enumerate(papers, 1):
    node = item['n']
    print(f"\n--- Paper #{i} ---")
    print(f"属性列表: {list(node.keys())}")
    
    # 只显示部分关键属性，避免输出过长
    key_attrs = ['title', 'core_problem', 'file_id']
    for attr in key_attrs:
        if attr in node:
            value = node[attr]
            # 截断过长的文本
            if isinstance(value, str) and len(value) > 100:
                value = value[:100] + "..."
            print(f"  {attr}: {value}")

# 6. 查看 solution 节点的属性示例
print("\n" + "=" * 60)
print("6. Solution 节点的属性示例 (前3个)")
print("=" * 60)

solution_labels = [l['label'] for l in labels if 'solution' in l['label'].lower()]
if solution_labels:
    solution_label = solution_labels[0]
    solution_sample_query = f"""
    MATCH (n:{solution_label})
    RETURN n
    LIMIT 3
    """
    solutions = n4j.query(solution_sample_query)
    for i, item in enumerate(solutions, 1):
        node = item['n']
        print(f"\n--- Solution #{i} (Label: {solution_label}) ---")
        print(f"属性列表: {list(node.keys())}")
        
        # 显示所有属性
        for key, value in node.items():
            if isinstance(value, str) and len(value) > 100:
                value = value[:100] + "..."
            print(f"  {key}: {value}")
else:
    print("未找到 solution 相关的节点标签")

# 7. 测试关键词搜索
print("\n" + "=" * 60)
print("7. 测试关键词搜索")
print("=" * 60)

test_keywords = ["gating", "multi-task", "attention", "fusion", "filter"]

for keyword in test_keywords:
    search_query = f"""
    MATCH (n)
    WHERE any(key IN keys(n) WHERE toLower(toString(n[key])) CONTAINS toLower('{keyword}'))
    RETURN labels(n) as labels, count(n) as count
    """
    results = n4j.query(search_query)
    total = sum([r['count'] for r in results]) if results else 0
    print(f"\n关键词 '{keyword}': 找到 {total} 个匹配节点")
    if results and total > 0:
        for r in results[:5]:  # 只显示前5个
            print(f"  - {r['labels']}: {r['count']} 个节点")

# 8. 查看图谱结构示例 (一个完整的 paper -> research_question -> solution 路径)
print("\n" + "=" * 60)
print("8. 图谱结构示例 (Paper -> Research Question -> Solution)")
print("=" * 60)

structure_query = """
MATCH path = (p:paper)-[r1]->(rq)-[r2]->(s)
WHERE labels(rq)[0] CONTAINS 'research_question' AND labels(s)[0] CONTAINS 'solution'
RETURN 
    p.title as paper_title,
    labels(rq)[0] as rq_label,
    labels(s)[0] as solution_label,
    type(r1) as rel1_type,
    type(r2) as rel2_type
LIMIT 3
"""
paths = n4j.query(structure_query)
if paths:
    for i, path in enumerate(paths, 1):
        print(f"\n路径 #{i}:")
        print(f"  Paper: {path['paper_title'][:60]}...")
        print(f"  --[{path['rel1_type']}]--> {path['rq_label']}")
        print(f"  --[{path['rel2_type']}]--> {path['solution_label']}")
else:
    print("未找到 paper -> research_question -> solution 路径")

# 9. 检查节点属性名称的实际情况
print("\n" + "=" * 60)
print("9. 检查节点的实际属性名称")
print("=" * 60)

# 检查 research_question 节点的属性
rq_labels = [l['label'] for l in labels if 'research_question' in l['label'].lower()]
if rq_labels:
    for rq_label in rq_labels[:3]:  # 只检查前3个
        check_query = f"""
        MATCH (n:{rq_label})
        RETURN keys(n) as properties
        LIMIT 1
        """
        result = n4j.query(check_query)
        if result:
            print(f"\n{rq_label} 节点的属性: {result[0]['properties']}")

# 检查 solution 节点的属性
solution_labels = [l['label'] for l in labels if 'solution' in l['label'].lower()]
if solution_labels:
    for sol_label in solution_labels[:3]:
        check_query = f"""
        MATCH (n:{sol_label})
        RETURN keys(n) as properties
        LIMIT 1
        """
        result = n4j.query(check_query)
        if result:
            print(f"{sol_label} 节点的属性: {result[0]['properties']}")

print("\n" + "=" * 60)
print("检查完成!")
print("=" * 60)
