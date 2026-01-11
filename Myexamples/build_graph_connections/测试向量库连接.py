"""
测试向量数据库连接
===================
用于验证向量数据库是否正确加载，以及数据量是否充足
"""

import os
from camel.storages import FaissStorage
from camel.embeddings import OpenAICompatibleEmbedding

# 配置
os.environ["OPENAI_COMPATIBILITY_API_KEY"] = "sk-875e0cf57dd34df59d3bcaef4ee47f80"
os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"

BASE_VDB_PATH = "Myexamples/vdb/camel_faiss_storage"

def test_storage_connection():
    """测试向量存储连接"""
    print("="*80)
    print("测试向量数据库连接")
    print("="*80)
    
    # 初始化embedding模型
    print("\n【步骤1】初始化Embedding模型...")
    embedding_model = OpenAICompatibleEmbedding(
        model_type="text-embedding-v2",
        api_key=os.environ["OPENAI_COMPATIBILITY_API_KEY"],
        url=os.environ["OPENAI_COMPATIBILITY_API_BASE_URL"],
    )
    print(f"✅ Embedding维度: {embedding_model.get_output_dim()}")
    
    # 测试各个存储
    storages_to_test = [
        ("paper", "abstract"),
        ("paper", "core_problem"),
        ("solution", "solution"),
    ]
    
    print("\n【步骤2】测试各个向量存储...")
    
    results = {}
    for entity_type, attribute in storages_to_test:
        storage_path = os.path.join(BASE_VDB_PATH, entity_type, attribute)
        collection_name = f"{entity_type}_{attribute}"
        index_file = os.path.join(storage_path, f"{collection_name}.index")
        
        print(f"\n--- 测试: {entity_type}.{attribute} ---")
        print(f"路径: {storage_path}")
        
        # 检查文件是否存在
        if not os.path.exists(index_file):
            print(f"❌ 索引文件不存在: {index_file}")
            results[f"{entity_type}.{attribute}"] = {
                "status": "失败",
                "reason": "索引文件不存在"
            }
            continue
        
        # 尝试加载
        try:
            storage = FaissStorage(
                vector_dim=embedding_model.get_output_dim(),
                storage_path=storage_path,
                collection_name=collection_name,
            )
            storage.load()
            
            status = storage.status()
            vector_count = status.vector_count
            
            print(f"✅ 加载成功")
            print(f"   向量数量: {vector_count}")
            
            results[f"{entity_type}.{attribute}"] = {
                "status": "成功",
                "vector_count": vector_count
            }
            
            # 尝试读取一个样本
            if vector_count > 0:
                import numpy as np
                from camel.storages import VectorDBQuery
                
                dummy_vector = np.zeros(storage.vector_dim)
                query = VectorDBQuery(query_vector=dummy_vector, top_k=1)
                result = storage.query(query=query)
                
                if result:
                    sample = result[0].record.payload
                    print(f"   样本示例:")
                    print(f"     - paper_id: {sample.get('paper_id', 'N/A')}")
                    print(f"     - text长度: {len(sample.get('text', ''))}")
            
        except Exception as e:
            print(f"❌ 加载失败: {e}")
            results[f"{entity_type}.{attribute}"] = {
                "status": "失败",
                "reason": str(e)
            }
    
    # 总结
    print("\n" + "="*80)
    print("测试总结")
    print("="*80)
    
    success_count = sum(1 for r in results.values() if r["status"] == "成功")
    total_count = len(results)
    
    print(f"\n成功: {success_count}/{total_count}")
    
    for name, result in results.items():
        if result["status"] == "成功":
            print(f"✅ {name}: {result['vector_count']} 条向量")
        else:
            print(f"❌ {name}: {result['reason']}")
    
    # 检查是否足够生成1550条配对
    if all(r["status"] == "成功" for r in results.values()):
        paper_count = results["paper.abstract"]["vector_count"]
        solution_count = results["solution.solution"]["vector_count"]
        
        # 估算可能的跨论文配对数
        # 假设每篇paper平均有2-3个solution
        estimated_pairs = paper_count * (solution_count // 2)
        
        print(f"\n📊 配对估算:")
        print(f"   Paper数量: {paper_count}")
        print(f"   Solution数量: {solution_count}")
        print(f"   预估可生成配对数: {estimated_pairs:,}")
        print(f"   需求配对数: 1,550")
        
        if estimated_pairs >= 1550:
            print("   ✅ 数据量充足")
        else:
            print("   ⚠️  数据量可能不足，建议检查")
    
    print("\n✅ 测试完成！")

if __name__ == "__main__":
    test_storage_connection()
