# Neo4j 知识图谱项目

## 📁 项目结构

```
neo4j_knowledge_graph/
├── scripts/                    # 脚本文件
│   ├── create_knowledge_graph.py       # 单条处理版本
│   └── create_knowledge_graph_fast.py  # 批量处理版本（推荐）
├── docs/                       # 文档
│   └── README.md              # 本文件
├── logs/                       # 日志文件
│   └── kg_fast.log           # 创建日志
└── data/                       # 数据文件（可选）
```

## 🌐 浏览器访问指南

### 1. 确认Neo4j服务状态

```bash
neo4j status
```

如果未运行，启动服务：
```bash
neo4j start
```

### 2. 访问Neo4j Browser

打开浏览器，访问：**http://localhost:7474**

### 3. 连接配置

| 配置项 | 值 |
|-------|-----|
| Connect URL | `bolt://localhost:7687` |
| Username | `neo4j` |
| Password | `neo4j123` |

### 4. 常用查询语句

```cypher
-- 查看图谱概览（显示所有类型节点）
MATCH (n) RETURN n LIMIT 25

-- 查看Paper节点
MATCH (p:Paper) RETURN p LIMIT 10

-- 查看完整的Paper->RQ->Solution层级
MATCH (p:Paper)-[:raise]->(rq:ResearchQuestion)-[:solved_by]->(sol:Solution)
RETURN p, rq, sol LIMIT 10

-- 按年份筛选Paper
MATCH (p:Paper {year: '2024'}) RETURN p LIMIT 10

-- 按会议筛选Paper
MATCH (p:Paper {conference: 'AAAI'}) RETURN p LIMIT 10

-- 查看特定论文的完整层级
MATCH path = (p:Paper {doi: '10.1609/aaai.v33i01.330110001'})-[:raise]->(rq)-[:solved_by]->(sol)
RETURN path

-- 统计各类节点数量
MATCH (p:Paper) RETURN count(p) as paper_count
MATCH (rq:ResearchQuestion) RETURN count(rq) as rq_count
MATCH (sol:Solution) RETURN count(sol) as sol_count

-- 查看关系类型
CALL db.relationshipTypes()

-- 查看节点标签
CALL db.labels()
```

## 📊 图谱统计

| 实体/关系 | 数量 |
|----------|------|
| Paper | 26,917 |
| ResearchQuestion | 77,909 |
| Solution | 77,909 |
| raise 关系 | 77,909 |
| raised_by 关系 | 77,909 |
| solved_by 关系 | 77,909 |

## 🚀 重新创建图谱

如果需要重新创建图谱：

```bash
cd /root/autodl-tmp/neo4j_knowledge_graph/scripts
python3 create_knowledge_graph_fast.py
```

输入 `y` 清空现有数据，然后直接回车处理全部记录。
