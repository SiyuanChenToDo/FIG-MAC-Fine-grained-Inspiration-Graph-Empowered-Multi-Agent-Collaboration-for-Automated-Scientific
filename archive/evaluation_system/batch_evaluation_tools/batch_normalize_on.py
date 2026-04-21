#!/usr/bin/env python3
"""
批量归一化 ON_v2 分数

用法:
    python batch_normalize_on.py results/*.json
    
功能:
    - 读取多个评估结果JSON文件
    - 提取ON_raw分数
    - 使用排序归一化: ON = (rank - 1) / (N - 1)
    - 更新所有JSON文件
"""

import json
import sys
import os
from pathlib import Path
from typing import List, Dict


def load_evaluation_results(json_paths: List[str]) -> List[Dict]:
    """加载所有评估结果"""
    results = []
    for path in json_paths:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                results.append({
                    'path': path,
                    'data': data
                })
        except Exception as e:
            print(f"⚠️  跳过 {path}: {e}")
    
    print(f"✅ 成功加载 {len(results)} 个评估结果文件")
    return results


def extract_on_raw_values(results: List[Dict]) -> List[tuple]:
    """提取ON_raw值及其索引"""
    on_values = []
    
    for idx, result in enumerate(results):
        try:
            # 主假说的ON_raw
            main_novelty = result['data'].get('metrics', {}).get('objective', {}).get('Novelty_Metrics', {})
            on_raw = main_novelty.get('ON_raw (Overall Novelty - Raw)')
            
            if on_raw is not None and not isinstance(on_raw, str):
                on_values.append({
                    'index': idx,
                    'on_raw': float(on_raw),
                    'path': result['path'],
                    'target': 'main',
                    'source': result['data'].get('metadata', {}).get('source', 'unknown')
                })
            
            # 如果有比较基线，也提取其ON_raw
            baseline_novelty = result['data'].get('comparison', {}).get('baseline_metrics', {}).get('Novelty_Metrics', {})
            baseline_on = baseline_novelty.get('ON_raw (Overall Novelty - Raw)')
            
            if baseline_on is not None and not isinstance(baseline_on, str):
                on_values.append({
                    'index': idx,
                    'on_raw': float(baseline_on),
                    'path': result['path'],
                    'target': 'baseline',
                    'source': f"{result['data'].get('metadata', {}).get('source', 'unknown')} (baseline)"
                })
                
        except Exception as e:
            print(f"⚠️  无法从 {result['path']} 提取ON_raw: {e}")
    
    return on_values


def normalize_on_scores(on_values: List[dict]) -> dict:
    """
    排序归一化ON分数
    返回: {(index, target): normalized_on, rank}
    """
    # 按ON_raw排序（升序）
    sorted_values = sorted(on_values, key=lambda x: x['on_raw'])
    
    N = len(sorted_values)
    normalization_map = {}
    
    print("\n" + "="*80)
    print("📊 ON_v2 排序归一化结果")
    print("="*80)
    print(f"{'Rank':<6} {'ON_raw':<12} {'ON_norm':<12} {'Source':<50}")
    print("-"*80)
    
    for rank, item in enumerate(sorted_values):
        # 计算归一化分数
        if N == 1:
            normalized_on = 1.0
        else:
            normalized_on = rank / (N - 1)
        
        # 存储映射
        key = (item['index'], item['target'])
        normalization_map[key] = {
            'normalized_on': normalized_on,
            'rank': rank + 1,
            'total': N,
            'on_raw': item['on_raw']
        }
        
        # 打印排名信息
        print(f"{rank+1:<6} {item['on_raw']:<12.4f} {normalized_on:<12.4f} {item['source'][:48]}")
    
    print("="*80)
    return normalization_map


def update_results(results: List[Dict], normalization_map: dict):
    """更新结果文件中的ON归一化分数"""
    updated_count = 0
    
    for idx, result in enumerate(results):
        modified = False
        
        # 更新主假说
        main_key = (idx, 'main')
        if main_key in normalization_map:
            novelty = result['data']['metrics']['objective']['Novelty_Metrics']
            norm_data = normalization_map[main_key]
            novelty['ON (Overall Novelty - Normalized)'] = norm_data['normalized_on']
            novelty['Rank'] = norm_data['rank']
            novelty['Total_Hypotheses'] = norm_data['total']
            modified = True
        
        # 更新基线
        baseline_key = (idx, 'baseline')
        if baseline_key in normalization_map:
            baseline_novelty = result['data']['comparison']['baseline_metrics']['Novelty_Metrics']
            norm_data = normalization_map[baseline_key]
            baseline_novelty['ON (Overall Novelty - Normalized)'] = norm_data['normalized_on']
            baseline_novelty['Rank'] = norm_data['rank']
            baseline_novelty['Total_Hypotheses'] = norm_data['total']
            modified = True
        
        # 保存更新后的文件
        if modified:
            try:
                with open(result['path'], 'w', encoding='utf-8') as f:
                    json.dump(result['data'], f, indent=2, ensure_ascii=False)
                updated_count += 1
            except Exception as e:
                print(f"❌ 无法更新 {result['path']}: {e}")
    
    print(f"\n✅ 成功更新 {updated_count} 个文件")


def main():
    if len(sys.argv) < 2:
        print("用法: python batch_normalize_on.py <json_file1> <json_file2> ...")
        print("示例: python batch_normalize_on.py results/*_eval_v2.json")
        sys.exit(1)
    
    json_paths = sys.argv[1:]
    
    print("="*80)
    print("🔬 ON_v2 批量归一化工具")
    print("="*80)
    print(f"输入文件数: {len(json_paths)}")
    print()
    
    # 1. 加载所有结果
    results = load_evaluation_results(json_paths)
    
    if not results:
        print("❌ 没有有效的评估结果文件")
        sys.exit(1)
    
    # 2. 提取ON_raw值
    on_values = extract_on_raw_values(results)
    
    if not on_values:
        print("❌ 没有找到有效的ON_raw值")
        sys.exit(1)
    
    print(f"📊 提取到 {len(on_values)} 个ON_raw值")
    
    # 3. 排序归一化
    normalization_map = normalize_on_scores(on_values)
    
    # 4. 更新文件
    update_results(results, normalization_map)
    
    print("\n" + "="*80)
    print("✨ 归一化完成！")
    print("="*80)
    print("\n💡 提示:")
    print("  - ON_normalized 现在可以跨系统比较")
    print("  - 分数范围: [0.0, 1.0]")
    print("  - Rank=1 表示最低新颖性, Rank=N 表示最高新颖性")
    print(f"  - 本次共处理 {len(on_values)} 个假说")


if __name__ == "__main__":
    main()

