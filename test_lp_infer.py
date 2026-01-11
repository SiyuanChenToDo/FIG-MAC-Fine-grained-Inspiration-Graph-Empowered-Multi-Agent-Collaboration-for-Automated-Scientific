#!/usr/bin/env python3
"""测试链路预测推理是否保存结果"""
import sys
sys.path.insert(0, '/root/autodl-tmp/graphstorm/python')

import torch as th
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 模拟检查配置
from graphstorm.config import GSConfig

# 创建一个简单的参数对象
class Args:
    def __init__(self):
        self.yaml_config_file = '/root/autodl-tmp/workspace/best_models/rgcn_advanced_20251103_173559/config.yaml'
        self.inference = True
        self.restore_model_path = '/root/autodl-tmp/workspace/best_models/rgcn_advanced_20251103_173559/eval_models/epoch-8'
        self.part_config = '/root/autodl-tmp/data/graphstorm_partitioned/custom_kg.json'
        self.ip_config = '/tmp/ip_list.txt'
        self.num_trainers = 1
        self.num_servers = 1
        self.num_samplers = 0
        self.ssh_port = 22
        self.save_model_path = '/root/autodl-tmp/workspace/best_models/rgcn_advanced_20251103_173559/eval_models'

args = Args()
config = GSConfig(args)

print(f"\n=== 配置检查 ===")
print(f"save_prediction_path: {config.save_prediction_path}")
print(f"save_embed_path: {config.save_embed_path}")
print(f"task_type: {config.task_type}")
print(f"eval_etype: {config.eval_etype}")
