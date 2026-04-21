#!/bin/bash
cd /root/autodl-tmp

export PYTHONPATH=/root/miniconda3/lib/python3.12/site-packages:$PYTHONPATH
export OMP_NUM_THREADS=28

python -m graphstorm.run.gs_link_prediction \
  --workspace /root/autodl-tmp \
  --num-trainers 1 \
  --num-servers 1 \
  --num-samplers 0 \
  --part-config /root/autodl-tmp/data/graphstorm_partitioned/custom_kg.json \
  --ip-config /root/autodl-tmp/workspace/ip_list.txt \
  --cf /root/autodl-tmp/workspace/configs/custom_kg_lp_v6c_infer.yaml \
  --logging-level info \
  --inference
