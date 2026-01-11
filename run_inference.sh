#!/bin/bash
set -e

# 最佳模型路径 (Run 001, Epoch 8)
BEST_MODEL_PATH="/root/autodl-tmp/workspace/tuning_v2/rgcn_inspired_finetune/runs/run_001__decoder=distmult__lr=0.0005__neg=32__drop=0.1__fanout=25-20__rgcn_edge_feat_mp_op=add__epochs=30/models/epoch-8-iter-399"

# 推理输出路径
INFER_OUTPUT_PATH="/root/autodl-tmp/workspace/inference_results/best_model_v1"

# 配置文件路径 (复用训练时的配置)
CONFIG_PATH="/root/autodl-tmp/workspace/tuning_v2/rgcn_inspired_finetune/runs/run_001__decoder=distmult__lr=0.0005__neg=32__drop=0.1__fanout=25-20__rgcn_edge_feat_mp_op=add__epochs=30/models/GRAPHSTORM_RUNTIME_UPDATED_TRAINING_CONFIG.yaml"

# 确保输出目录存在
mkdir -p $INFER_OUTPUT_PATH

echo "开始全图推理..."
echo "模型: $BEST_MODEL_PATH"
echo "输出: $INFER_OUTPUT_PATH"

# 运行 GraphStorm 推理
# 注意：我们需要指定 task_type 为 link_prediction，并开启 inference
python -m graphstorm.run.gs_link_prediction \
    --inference \
    --restore-model-path $BEST_MODEL_PATH \
    --save-embed-path $INFER_OUTPUT_PATH/embeddings \
    --save-prediction-path $INFER_OUTPUT_PATH/predictions \
    --cf $CONFIG_PATH \
    --part-config /root/autodl-tmp/data/graphstorm_partitioned/custom_kg.json \
    --ip-config /tmp/ip_list.txt \
    --num-trainers 1 \
    --num-servers 1 \
    --num-samplers 0 \
    --ssh-port 22

echo "推理完成！结果保存在 $INFER_OUTPUT_PATH"

