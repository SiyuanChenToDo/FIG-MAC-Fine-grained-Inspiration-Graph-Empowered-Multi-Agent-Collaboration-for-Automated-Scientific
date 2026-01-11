#!/usr/bin/env python3
"""
提取灵感链路 V2：
1. 支持从INSPIRED关系中提取灵感
2. 动态加载最新模型预测结果
3. 支持根据用户输入的研究问题进行针对性预测
"""
import torch
import json
import pandas as pd
from pathlib import Path
import sys
import argparse
from typing import Dict, List, Optional

def load_predictions(infer_dir: Path) -> Dict[str, Dict]:
    """加载预测结果"""
    print("\n[1/4] 加载链路预测结果...")
    preds = {}
    
    # 定义关注的边类型
    target_etypes = [
        'paper_has_rq_research_question',
        'research_question_has_solution_solution',
        'solution_inspired_paper'  # 新增：INSPIRED 关系
    ]
    
    for etype in target_etypes:
        etype_dir = infer_dir / etype
        if not etype_dir.exists():
            print(f"  警告: 未找到边类型预测: {etype}")
            continue
            
        try:
            preds[etype] = {
                'pred': torch.load(etype_dir / 'predict-00000.pt'),
                'src': torch.load(etype_dir / 'src_nids-00000.pt'),
                'dst': torch.load(etype_dir / 'dst_nids-00000.pt')
            }
            print(f"  已加载 {etype}: {len(preds[etype]['pred'])} 条预测")
        except Exception as e:
            print(f"  加载 {etype} 失败: {e}")
            
    return preds

def filter_predictions(preds: Dict, rank_threshold: int = 5) -> Dict[str, List[Dict]]:
    """筛选高质量预测"""
    print(f"\n[2/4] 筛选高质量预测 (Rank <= {rank_threshold})...")
    filtered = {}
    
    for etype, data in preds.items():
        mask = data['pred'] <= rank_threshold
        # 使用 torch.nonzero 找到符合条件的索引
        indices = torch.nonzero(mask).squeeze()
        
        # 转换为 Python 列表
        filtered_links = []
        if indices.dim() == 0 and indices.numel() == 1: # 处理只有一个匹配的情况
             indices = [indices.item()]
        elif indices.numel() == 0:
             indices = []
        else:
             indices = indices.tolist()

        for idx in indices:
            filtered_links.append({
                'src_id': data['src'][idx].item(),
                'dst_id': data['dst'][idx].item(),
                'rank': data['pred'][idx].item()
            })
            
        filtered[etype] = filtered_links
        print(f"  {etype}: {len(filtered_links)} 条高质量链接")
        
    return filtered

def build_paths(links: Dict[str, List[Dict]]) -> List[Dict]:
    """构建多跳灵感链路"""
    print("\n[3/4] 构建多跳灵感链路...")
    
    # 1. 构建索引以加速查找
    # Paper -> RQ
    paper_to_rq = {}
    for l in links.get('paper_has_rq_research_question', []):
        if l['src_id'] not in paper_to_rq: paper_to_rq[l['src_id']] = []
        paper_to_rq[l['src_id']].append(l)
        
    # RQ -> Solution
    rq_to_sol = {}
    for l in links.get('research_question_has_solution_solution', []):
        if l['src_id'] not in rq_to_sol: rq_to_sol[l['src_id']] = []
        rq_to_sol[l['src_id']].append(l)

    # Solution -> Inspired Paper (闭环或延伸)
    sol_to_inspired = {}
    for l in links.get('solution_inspired_paper', []):
         if l['src_id'] not in sol_to_inspired: sol_to_inspired[l['src_id']] = []
         sol_to_inspired[l['src_id']].append(l)
    
    paths = []
    
    # 2. 构建 Paper -> RQ -> Solution 路径
    for paper_id, rq_links in paper_to_rq.items():
        for rq_link in rq_links:
            rq_id = rq_link['dst_id']
            if rq_id in rq_to_sol:
                for sol_link in rq_to_sol[rq_id]:
                    sol_id = sol_link['dst_id']
                    
                    # 基础路径
                    path = {
                        'type': 'standard',
                        'paper_id': paper_id,
                        'rq_id': rq_id,
                        'solution_id': sol_id,
                        'scores': {
                            'p_rq': rq_link['rank'],
                            'rq_s': sol_link['rank']
                        },
                        'total_score': rq_link['rank'] + sol_link['rank'],
                        'inspired_paper_id': None
                    }
                    paths.append(path)

                    # 扩展路径：Solution -> Inspired Paper
                    if sol_id in sol_to_inspired:
                        for insp_link in sol_to_inspired[sol_id]:
                            insp_path = path.copy()
                            insp_path['type'] = 'extended_inspiration'
                            insp_path['inspired_paper_id'] = insp_link['dst_id']
                            insp_path['scores']['s_insp'] = insp_link['rank']
                            insp_path['total_score'] += insp_link['rank']
                            paths.append(insp_path)
    
    return sorted(paths, key=lambda x: x['total_score'])

def save_results(paths: List[Dict], output_dir: Path):
    """保存结果"""
    print("\n[4/4] 保存结果...")
    
    # JSON
    with open(output_dir / 'inspiration_paths_v2.json', 'w', encoding='utf-8') as f:
        json.dump({
            'total_paths': len(paths),
            'top_100': paths[:100]
        }, f, indent=2)
        
    # CSV
    pd.DataFrame(paths).to_csv(output_dir / 'inspiration_paths_v2.csv', index=False)
    
    print(f"  已保存到: {output_dir}")

def main():
    parser = argparse.ArgumentParser(description="提取灵感链路")
    parser.add_argument("--model-path", type=str, required=True, help="模型推理输出目录")
    parser.add_argument("--rank-threshold", type=int, default=5, help="排名阈值")
    parser.add_argument("--rq-filter", type=str, help="可选：仅筛选特定研究问题ID")
    
    args = parser.parse_args()
    
    infer_dir = Path(args.model_path)
    if not infer_dir.exists():
        print(f"错误: 目录不存在 {infer_dir}")
        return

    # 加载和处理
    preds = load_predictions(infer_dir)
    links = filter_predictions(preds, args.rank_threshold)
    paths = build_paths(links)
    
    # 用户过滤
    if args.rq_filter:
        print(f"\n正在筛选 RQ ID: {args.rq_filter}...")
        target_rq = int(args.rq_filter)
        paths = [p for p in paths if p['rq_id'] == target_rq]
        print(f"  找到 {len(paths)} 条相关路径")
    
    # 显示统计
    print(f"\n总共发现 {len(paths)} 条灵感链路")
    if paths:
        print("\nTop 5 路径示例:")
        for i, p in enumerate(paths[:5]):
            print(f"[{i+1}] P:{p['paper_id']} -> Q:{p['rq_id']} -> S:{p['solution_id']} "
                  f"(Score: {p['total_score']}) "
                  f"{'-> Inspired P:' + str(p['inspired_paper_id']) if p['inspired_paper_id'] else ''}")

    save_results(paths, infer_dir)

if __name__ == "__main__":
    main()

