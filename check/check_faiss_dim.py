import faiss
import os

index_file = "/root/autodl-tmp/Myexamples/vdb/camel_faiss_storage/paper/abstract/paper_abstract.index"

if os.path.exists(index_file):
    print(f"Reading index from: {index_file}")
    index = faiss.read_index(index_file)
    print(f"Index Dimension (d): {index.d}")
    print(f"Total Vectors (ntotal): {index.ntotal}")
else:
    print(f"Index file not found at: {index_file}")
