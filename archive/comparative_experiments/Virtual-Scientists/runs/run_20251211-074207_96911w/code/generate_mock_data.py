import os
import numpy as np
import json

# Define base path
base_path = "/root/autodl-tmp/Myexamples/comparative_experiments/Virtual-Scientists/mock_data"
os.makedirs(base_path, exist_ok=True)

# 1. Mock Adjacency Matrix (5 agents)
adj_dir = os.path.join(base_path, "adjacency")
os.makedirs(adj_dir, exist_ok=True)
adj_matrix = np.ones((5, 5), dtype=int) # Fully connected for simplicity
np.savetxt(os.path.join(adj_dir, "adjacency.txt"), adj_matrix, fmt='%d')

# 2. Mock Author Info (books)
author_dir = os.path.join(base_path, "books")
os.makedirs(author_dir, exist_ok=True)
for i in range(5):
    with open(os.path.join(author_dir, f"author_{i}.txt"), "w") as f:
        f.write(f"You are Scientist {i}. Your research interest is Artificial Intelligence and Machine Learning.")

# 3. Mock Papers - Format expected by read_txt_files_as_dict is a Python dict string (eval-able)
paper_dir = os.path.join(base_path, "papers")
os.makedirs(paper_dir, exist_ok=True)

for i in range(10):
    paper_data = {
        "title": f"Mock Paper {i}",
        "abstract": f"This is a mock abstract for paper {i} about AI and Machine Learning concepts.",
        "year": 2020,
        "citation": 10 * i
    }
    with open(os.path.join(paper_dir, f"paper_{i}.txt"), "w") as f:
        f.write(str(paper_data))

# 4. Mock Future Papers
future_paper_dir = os.path.join(base_path, "papers_future")
os.makedirs(future_paper_dir, exist_ok=True)

for i in range(5):
    paper_data = {
        "title": f"Future Paper {i}",
        "abstract": f"Future work on AI and Robotics for paper {i}.",
        "year": 2024,
        "citation": 5 * i
    }
    with open(os.path.join(future_paper_dir, f"future_paper_{i}.txt"), "w") as f:
        f.write(str(paper_data))

print("Mock data generated successfully at", base_path)
