#!/usr/bin/env python3
"""
将节点ID映射回原始文本内容
"""
import json
import pandas as pd
from pathlib import Path

print("=" * 100)
print("节点ID到原始文本映射工具")
print("=" * 100)

# 1. 加载原始数据
print("\n[1/4] 加载原始数据...")
NEO4J_EXPORT_DIR = Path('/root/autodl-tmp/data/neo4j_export')

# 加载papers
papers_file = NEO4J_EXPORT_DIR / 'papers.parquet'
papers_df = pd.read_parquet(papers_file)
print(f"  ✓ 加载Papers: {len(papers_df)} 个")

# 加载research questions
rqs_file = NEO4J_EXPORT_DIR / 'research_questions.parquet'
rqs_df = pd.read_parquet(rqs_file)
print(f"  ✓ 加载Research Questions: {len(rqs_df)} 个")

# 加载solutions
solutions_file = NEO4J_EXPORT_DIR / 'solutions.parquet'
solutions_df = pd.read_parquet(solutions_file)
print(f"  ✓ 加载Solutions: {len(solutions_df)} 个")

# 2. 创建ID到文本的映射
print("\n[2/4] 创建ID映射字典...")

# 经过验证：预测结果中的ID是类型内部ID（DataFrame索引）
# Paper ID = Paper在DataFrame中的索引（0-26915）
# RQ ID = RQ在DataFrame中的索引（0-77905）
# Solution ID = Solution在DataFrame中的索引（0-77905）
print(f"  使用DataFrame索引作为节点ID（已验证）")

# 直接使用DataFrame，通过iloc访问
print(f"  ✓ Papers: {len(papers_df)} 条")
print(f"  ✓ RQs: {len(rqs_df)} 条")
print(f"  ✓ Solutions: {len(solutions_df)} 条")

# 3. 加载灵感链路
print("\n[3/4] 加载灵感链路...")
paths_file = Path('/root/autodl-tmp/workspace/best_models/rgcn_advanced_20251103_173559/inspiration_paths.json')
with open(paths_file, 'r') as f:
    paths_data = json.load(f)

paths = paths_data['top_100_paths']
print(f"  加载了 {len(paths)} 条路径")

# 4. 映射并保存结果
print("\n[4/4] 映射节点ID到原始文本...")

enriched_paths = []
unmapped_count = 0

for path in paths:
    paper_id = path['paper_id']
    rq_id = path['rq_id']
    sol_id = path['solution_id']
    
    # 直接使用iloc访问DataFrame
    try:
        paper_row = papers_df.iloc[paper_id]
        rq_row = rqs_df.iloc[rq_id]
        sol_row = solutions_df.iloc[sol_id]
        
        enriched_paths.append({
            'paper_id': int(paper_id),
            'paper_title': str(paper_row['title']),
            'paper_doi': str(paper_row.get('doi_norm', paper_row.get('entity_name', ''))),
            'paper_year': int(paper_row['year']) if pd.notna(paper_row.get('year')) else None,
            'paper_abstract': str(paper_row.get('abstract', ''))[:200] if pd.notna(paper_row.get('abstract')) else '',
            'rq_id': int(rq_id),
            'research_question': str(rq_row.get('research_question', rq_row.get('simplified_research_question', ''))),
            'rq_original_id': str(rq_row.get('rq_id', '')),
            'solution_id': int(sol_id),
            'solution': str(sol_row.get('solution', sol_row.get('simplified_solution', ''))),
            'solution_original_id': str(sol_row.get('sol_id', '')),
            'paper_rq_rank': int(path['paper_rq_rank']),
            'rq_sol_rank': int(path['rq_sol_rank']),
            'total_score': int(path['total_score'])
        })
    except (IndexError, KeyError) as e:
        unmapped_count += 1
        print(f"  警告: 无法映射路径 (Paper:{paper_id}, RQ:{rq_id}, Sol:{sol_id}): {e}")
        continue

print(f"  成功映射: {len(enriched_paths) - unmapped_count}/{len(enriched_paths)}")
if unmapped_count > 0:
    print(f"  警告: {unmapped_count} 条路径包含未映射的节点ID")

# 保存为JSON
output_json = Path('/root/autodl-tmp/workspace/best_models/rgcn_advanced_20251103_173559/inspiration_paths_with_text.json')
with open(output_json, 'w', encoding='utf-8') as f:
    json.dump(enriched_paths, f, indent=2, ensure_ascii=False)
print(f"\n  ✓ 带文本的JSON已保存: {output_json}")

# 保存为CSV
df = pd.DataFrame(enriched_paths)
output_csv = Path('/root/autodl-tmp/workspace/best_models/rgcn_advanced_20251103_173559/inspiration_paths_with_text.csv')
df.to_csv(output_csv, index=False, encoding='utf-8-sig')
print(f"  ✓ 带文本的CSV已保存: {output_csv}")

# 保存为易读的Markdown格式
output_md = Path('/root/autodl-tmp/workspace/best_models/rgcn_advanced_20251103_173559/inspiration_paths_readable.md')
with open(output_md, 'w', encoding='utf-8') as f:
    f.write("# 灵感链路分析结果\n\n")
    f.write(f"总计: {len(enriched_paths)} 条高质量灵感链路\n\n")
    f.write("---\n\n")
    
    for i, path in enumerate(enriched_paths[:50], 1):  # 只显示前50条
        f.write(f"## 路径 {i} (总分: {path['total_score']})\n\n")
        f.write(f"### 📄 Paper (图ID: {path['paper_id']})\n")
        f.write(f"**标题**: {path['paper_title']}\n\n")
        f.write(f"**DOI**: {path['paper_doi']}\n\n")
        f.write(f"**年份**: {path['paper_year']}\n\n")
        if path['paper_abstract']:
            f.write(f"**摘要**: {path['paper_abstract']}...\n\n")
        f.write(f"↓ **预测排名: {path['paper_rq_rank']}**\n\n")
        f.write(f"### ❓ Research Question (图ID: {path['rq_id']})\n")
        f.write(f"{path['research_question']}\n\n")
        f.write(f"*原始ID: {path['rq_original_id']}*\n\n")
        f.write(f"↓ **预测排名: {path['rq_sol_rank']}**\n\n")
        f.write(f"### 💡 Solution (图ID: {path['solution_id']})\n")
        f.write(f"{path['solution']}\n\n")
        f.write(f"*原始ID: {path['solution_original_id']}*\n\n")
        f.write("---\n\n")

print(f"  ✓ 可读Markdown已保存: {output_md}")

# 显示示例
print("\n" + "=" * 100)
print("示例：排名最好的3条灵感链路")
print("=" * 100)

for i, path in enumerate(enriched_paths[:3], 1):
    print(f"\n{'=' * 100}")
    print(f"路径 {i} (总分: {path['total_score']})")
    print(f"{'=' * 100}")
    print(f"\n📄 Paper (图ID: {path['paper_id']}, P→RQ排名: {path['paper_rq_rank']})")
    print(f"   标题: {path['paper_title']}")
    print(f"   DOI: {path['paper_doi']}")
    print(f"   年份: {path['paper_year']}")
    print(f"\n❓ Research Question (图ID: {path['rq_id']}, RQ→S排名: {path['rq_sol_rank']})")
    print(f"   {path['research_question'][:200]}...")
    print(f"\n💡 Solution (图ID: {path['solution_id']})")
    print(f"   {path['solution'][:200]}...")

print("\n" + "=" * 100)
print("完成！")
print("=" * 100)
print("\n生成的文件:")
print(f"  1. {output_json.name} - 完整JSON数据")
print(f"  2. {output_csv.name} - Excel可打开的CSV")
print(f"  3. {output_md.name} - 易读的Markdown格式")
print("\n你现在可以:")
print("  1. 打开CSV文件进行人工审核")
print("  2. 阅读Markdown文件查看详细内容")
print("  3. 基于这些高质量预测进行下游的灵感链路分析")
print("=" * 100)
