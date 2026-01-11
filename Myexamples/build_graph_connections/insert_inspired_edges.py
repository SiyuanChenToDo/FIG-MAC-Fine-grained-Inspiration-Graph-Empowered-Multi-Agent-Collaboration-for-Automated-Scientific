import csv
import re
import time
import sys
from camel.storages import Neo4jGraph
from concurrent.futures import ThreadPoolExecutor, as_completed

# 配置 Neo4j 连接
# 注意：多线程环境下每个线程最好有独立的 session 或者使用 driver 提供的线程安全机制
# Camel 的 Neo4jGraph 内部实现可能不是完全线程优化的，但 driver 本身是线程安全的。
n4j = Neo4jGraph(
    url="bolt://localhost:17687",
    username="neo4j",
    password="ai4sci123456",
)

# CSV 文件路径
csv_file_path = "/root/autodl-tmp/Myexamples/build_graph_connections/corrected_predictions_with_reasoning_20251112_final.csv"

def tokenize(text):
    if not text:
        return set()
    stopwords = {
        'the', 'a', 'an', 'and', 'or', 'of', 'to', 'in', 'on', 'at', 'is', 'are', 'was', 'were', 
        'this', 'that', 'it', 'be', 'has', 'have', 'from', 'by', 'as', 'for', 'with', 'paper',
        'proposed', 'proposes', 'method', 'solution', 'we', 'our', 'can', 'which'
    }
    tokens = set(re.findall(r'[a-z0-9]+', text.lower()))
    return tokens - stopwords

def calculate_similarity(text1, text2):
    tokens1 = tokenize(text1)
    tokens2 = tokenize(text2)
    if not tokens1 or not tokens2:
        return 0.0
    return len(tokens1 & tokens2) / len(tokens1 | tokens2)

def fetch_all_inspired_rows():
    print("正在读取 CSV 并筛选 INSPIRED 数据...")
    inspired_rows = []
    with open(csv_file_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('prediction', '').strip() == 'INSPIRED':
                inspired_rows.append(row)
    print(f"筛选完成，共有 {len(inspired_rows)} 条 INSPIRED 记录待处理。")
    return inspired_rows

# 全局缓存字典，用于减少数据库查询
# 预先加载所有 Solution 节点信息到内存会非常快，如果内存允许的话
# 假设 Solution 节点有 7.8万个，完全可以放入内存
global_solution_cache = {}

def preload_solutions():
    print("正在预加载所有 Solution 节点到内存缓存...")
    start = time.time()
    # 一次性拉取所有 Solution 的关键字段
    query = """
    MATCH (s:Solution)
    RETURN elementId(s) as id, s.sol_id as sol_id, s.text as text, s.simplified as simplified
    """
    results = n4j.query(query)
    
    count = 0
    for rec in results:
        sol_id = rec['sol_id']
        # Store by DOI prefix for fast lookup
        # sol_id format e.g.: 10.18653/v1/2020.acl-main.173_sol1
        if '_' in sol_id:
            doi_prefix = sol_id.rsplit('_', 1)[0]
        else:
            doi_prefix = sol_id # Fallback
            
        if doi_prefix not in global_solution_cache:
            global_solution_cache[doi_prefix] = []
        
        # Pre-tokenize text to save time during comparison?
        # Calculating tokens once is better.
        rec['tokens'] = tokenize((rec.get('simplified') or "") + " " + (rec.get('text') or ""))
        global_solution_cache[doi_prefix].append(rec)
        count += 1
        
    print(f"预加载完成！缓存了 {count} 个 Solution 节点，耗时 {time.time() - start:.2f} 秒。")

def process_batch(batch_rows):
    """
    处理一小批数据，返回生成的 Cypher 插入语句列表。
    而不是每条都去查库、插库。
    """
    insert_params_list = []
    
    for row in batch_rows:
        solution_id_csv = row.get('solution_id', '').strip()
        paper_id_csv = row.get('question_paper_id', '').strip()
        reasoning = row.get('INSPIRED_reasoning', '').strip()
        thinking = row.get('thinking', '').strip()
        match_text = reasoning if reasoning else thinking
        
        if not solution_id_csv or not paper_id_csv:
            continue

        if '_' in solution_id_csv:
            solution_doi_prefix = solution_id_csv.rsplit('_', 1)[0]
        else:
            solution_doi_prefix = solution_id_csv
            
        # 1. In-memory lookup
        candidate_solutions = global_solution_cache.get(solution_doi_prefix, [])
        if not candidate_solutions:
            continue
            
        # 2. In-memory matching
        match_tokens = tokenize(match_text)
        best_match_sol = None
        best_score = -1.0
        
        for sol in candidate_solutions:
            sol_tokens = sol['tokens']
            if not match_tokens or not sol_tokens:
                score = 0.0
            else:
                score = len(match_tokens & sol_tokens) / len(match_tokens | sol_tokens)
                
            if score > best_score:
                best_score = score
                best_match_sol = sol
        
        if best_match_sol:
            target_sol_suffix = best_match_sol['sol_id'].split('_')[-1] if '_' in best_match_sol['sol_id'] else "unknown"
            
            # Prepare params for batch insertion
            insert_params_list.append({
                'paper_doi': paper_id_csv,
                'sol_element_id': best_match_sol['id'],
                'reasoning': reasoning,
                'orig_csv_id': solution_id_csv,
                'score': best_score,
                'suffix': target_sol_suffix
            })
            
    return insert_params_list

def main():
    print("=" * 60)
    print("开始加速处理 INSPIRED 关系插入 (内存缓存 + 批量插入)...")
    print("=" * 60)

    # 1. Load Data
    inspired_rows = fetch_all_inspired_rows()
    
    # 2. Preload Graph Data
    preload_solutions()
    
    total_rows = len(inspired_rows)
    print(f"开始处理 {total_rows} 条数据...")
    
    batch_size = 2000 # Python 处理批次
    db_batch_size = 1000 # 写入 DB 的批次 (UNWIND)
    
    # Thread pool for parallel processing of text similarity
    # CPU intensive part
    max_workers = 16 
    
    processed_count = 0
    success_count = 0
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Split into chunks
        chunks = [inspired_rows[i:i + batch_size] for i in range(0, total_rows, batch_size)]
        
        futures = {executor.submit(process_batch, chunk): chunk for chunk in chunks}
        
        # Collect results and write to DB
        pending_writes = []
        
        for future in as_completed(futures):
            result_params = future.result()
            pending_writes.extend(result_params)
            
            processed_count += len(futures[future])
            
            # Update Progress Bar (CPU processing part)
            # Note: This is just processing progress, not DB write progress
            pass

            # If we have enough pending writes, flush to DB
            while len(pending_writes) >= db_batch_size:
                batch_to_write = pending_writes[:db_batch_size]
                pending_writes = pending_writes[db_batch_size:]
                
                # Batch Insert Query
                # Using UNWIND is much faster than individual queries
                cypher = """
                UNWIND $batch AS row
                MATCH (p:Paper), (s:Solution)
                WHERE (p.doi = row.paper_doi OR p.doi_norm = row.paper_doi)
                  AND elementId(s) = row.sol_element_id
                MERGE (s)-[r:INSPIRED]->(p)
                SET r.INSPIRED_reasoning = row.reasoning,
                    r.created_at = timestamp(),
                    r.source = 'csv_import_accelerated',
                    r.original_csv_solution_id = row.orig_csv_id,
                    r.match_method = 'text_similarity',
                    r.match_score = row.score,
                    r.matched_sol_suffix = row.suffix
                """
                try:
                    n4j.query(cypher, params={'batch': batch_to_write})
                    success_count += len(batch_to_write)
                except Exception as e:
                    print(f"\n❌ DB Write Error: {e}")

                # Progress Bar update
                elapsed = time.time() - start_time
                progress = success_count / total_rows * 100 # Approximate
                sys.stdout.write(f'\r[Processing & Writing] {progress:.1f}% | Writes: {success_count} | Time: {elapsed:.1f}s')
                sys.stdout.flush()
        
        # Flush remaining
        if pending_writes:
            cypher = """
            UNWIND $batch AS row
            MATCH (p:Paper), (s:Solution)
            WHERE (p.doi = row.paper_doi OR p.doi_norm = row.paper_doi)
              AND elementId(s) = row.sol_element_id
            MERGE (s)-[r:INSPIRED]->(p)
            SET r.INSPIRED_reasoning = row.reasoning,
                r.created_at = timestamp(),
                r.source = 'csv_import_accelerated',
                r.original_csv_solution_id = row.orig_csv_id,
                r.match_method = 'text_similarity',
                r.match_score = row.score,
                r.matched_sol_suffix = row.suffix
            """
            try:
                n4j.query(cypher, params={'batch': pending_writes})
                success_count += len(pending_writes)
            except Exception as e:
                 print(f"\n❌ DB Write Error: {e}")

    print("\n" + "=" * 60)
    print(f"全部完成！总耗时: {time.time() - start_time:.2f}s")
    print(f"成功插入关系数: {success_count}")
    print("=" * 60)

if __name__ == "__main__":
    main()

