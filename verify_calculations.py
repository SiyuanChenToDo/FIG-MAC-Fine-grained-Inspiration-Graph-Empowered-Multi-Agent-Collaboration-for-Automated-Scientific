import pandas as pd
import numpy as np
import os

# 文件路径
files = {
    'Ours': '/root/autodl-tmp/Myexamples/evaluation_system/batch_results/ours/metrics_summary.xlsx',
    'VirSci': '/root/autodl-tmp/virsci_metrics.xlsx',
    'COI': '/root/autodl-tmp/Myexamples/evaluation_system/batch_results/coi/coi_metrics_test_final.xlsx',
    'AI Scientist': '/root/autodl-tmp/Myexamples/evaluation_system/batch_results/ai_scientist/ai_scientist_metrics_test_final.xlsx'
}

print("=" * 80)
print("详细检查计算结果")
print("=" * 80)

# 列名映射
column_mapping = {
    'objective.Fluency_Score': 'Fluency_Score',
    'objective.Novelty_Metrics.HD (Historical Dissimilarity)': 'HD',
    'objective.Novelty_Metrics.CD (Contemporary Dissimilarity)': 'CD',
    'objective.Novelty_Metrics.CI (Contemporary Impact, Year-Normalized)': 'CI',
    'objective.Novelty_Metrics.ON_raw (Overall Novelty - Raw)': 'ON_raw',
    'objective.Novelty_Metrics.ON (Overall Novelty - Normalized)': 'ON_normalized',
    'objective.Provenance_Metrics.S_src (Source Similarity)': 'S_src',
    'objective.Provenance_Metrics.U_src (Source Diversity)': 'U_src',
    'objective.Provenance_Metrics.G (Provenance Factor)': 'G',
    'objective.Provenance_Metrics.P (Provenance-Adjusted Novelty)': 'P',
    'subjective_llm.Novelty': 'Novelty',
    'subjective_llm.Significance': 'Significance',
    'subjective_llm.Effectiveness': 'Effectiveness',
    'subjective_llm.Clarity': 'Clarity',
    'subjective_llm.Feasibility': 'Feasibility',
}

metrics_of_interest = [
    'Fluency_Score', 'HD', 'CD', 'CI', 'ON_raw', 'ON_normalized',
    'S_src', 'U_src', 'G', 'P',
    'Novelty', 'Significance', 'Effectiveness', 'Clarity', 'Feasibility'
]

results = {}

for method_name, file_path in files.items():
    print(f"\n{'='*80}")
    print(f"【{method_name}】详细分析")
    print(f"{'='*80}")
    
    if not os.path.exists(file_path):
        print(f"警告: 文件不存在: {file_path}")
        continue
    
    try:
        df = pd.read_excel(file_path)
        print(f"\n数据形状: {df.shape}")
        
        # 创建列名映射
        method_column_mapping = {}
        for old_col in df.columns:
            if old_col in column_mapping:
                method_column_mapping[old_col] = column_mapping[old_col]
            elif old_col in metrics_of_interest:
                method_column_mapping[old_col] = old_col
        
        df_renamed = df.rename(columns=method_column_mapping)
        
        # 详细检查每个指标
        method_stats = {}
        for metric in metrics_of_interest:
            if metric in df_renamed.columns:
                col_data = pd.to_numeric(df_renamed[metric], errors='coerce')
                valid_data = col_data.dropna()
                
                if len(valid_data) > 0:
                    mean_val = valid_data.mean()
                    median_val = valid_data.median()
                    std_val = valid_data.std()
                    min_val = valid_data.min()
                    max_val = valid_data.max()
                    count = len(valid_data)
                    missing = len(col_data) - count
                    
                    method_stats[metric] = {
                        'mean': mean_val,
                        'median': median_val,
                        'std': std_val,
                        'min': min_val,
                        'max': max_val,
                        'count': count,
                        'missing': missing
                    }
                    
                    print(f"\n{metric}:")
                    print(f"  有效数据: {count}/{len(col_data)} (缺失: {missing})")
                    print(f"  平均值: {mean_val:.4f}")
                    print(f"  中位数: {median_val:.4f}")
                    print(f"  标准差: {std_val:.4f}")
                    print(f"  范围: [{min_val:.4f}, {max_val:.4f}]")
                    
                    # 检查是否有异常值
                    if std_val > 0:
                        z_scores = np.abs((valid_data - mean_val) / std_val)
                        outliers = (z_scores > 3).sum()
                        if outliers > 0:
                            print(f"  警告: 发现 {outliers} 个异常值 (|z-score| > 3)")
                    
                    # 显示前5个值
                    print(f"  前5个值: {valid_data.head().tolist()}")
                else:
                    print(f"\n{metric}: 无有效数据")
                    method_stats[metric] = None
            else:
                print(f"\n{metric}: 列不存在")
                method_stats[metric] = None
        
        results[method_name] = {
            'dataframe': df,
            'stats': method_stats
        }
        
    except Exception as e:
        print(f"错误: {str(e)}")
        import traceback
        traceback.print_exc()

# 对比分析
print("\n" + "=" * 80)
print("对比分析 - Ours vs 其他方法")
print("=" * 80)

if 'Ours' in results:
    ours_stats = results['Ours']['stats']
    
    for metric in metrics_of_interest:
        if metric in ours_stats and ours_stats[metric] is not None:
            ours_mean = ours_stats[metric]['mean']
            print(f"\n{metric}:")
            print(f"  Ours: {ours_mean:.4f}")
            
            for method_name in ['VirSci', 'COI', 'AI Scientist']:
                if method_name in results:
                    method_stats = results[method_name]['stats']
                    if metric in method_stats and method_stats[metric] is not None:
                        method_mean = method_stats[metric]['mean']
                        diff = method_mean - ours_mean
                        diff_pct = (diff / ours_mean * 100) if ours_mean != 0 else 0
                        print(f"  {method_name}: {method_mean:.4f} (差异: {diff:+.4f}, {diff_pct:+.2f}%)")
                    else:
                        print(f"  {method_name}: N/A")
            
            # 找出最高和最低
            all_means = {'Ours': ours_mean}
            for method_name in ['VirSci', 'COI', 'AI Scientist']:
                if method_name in results:
                    method_stats = results[method_name]['stats']
                    if metric in method_stats and method_stats[metric] is not None:
                        all_means[method_name] = method_stats[metric]['mean']
            
            if len(all_means) > 1:
                best_method = max(all_means, key=all_means.get)
                worst_method = min(all_means, key=all_means.get)
                print(f"  最佳: {best_method} ({all_means[best_method]:.4f})")
                print(f"  最差: {worst_method} ({all_means[worst_method]:.4f})")
                if best_method != 'Ours':
                    print(f"  ⚠️  Ours不是最佳方法，差距: {all_means[best_method] - ours_mean:.4f}")

# 检查数据分布
print("\n" + "=" * 80)
print("数据分布检查 - 查看是否有数据质量问题")
print("=" * 80)

for method_name in ['Ours', 'VirSci']:
    if method_name in results:
        print(f"\n【{method_name}】")
        df = results[method_name]['dataframe']
        
        # 检查关键指标的数据分布
        key_metrics = [
            'objective.Fluency_Score',
            'subjective_llm.Novelty',
            'subjective_llm.Significance',
            'subjective_llm.Effectiveness',
            'subjective_llm.Clarity',
            'subjective_llm.Feasibility'
        ]
        
        for metric in key_metrics:
            if metric in df.columns:
                col_data = pd.to_numeric(df[metric], errors='coerce')
                valid_data = col_data.dropna()
                if len(valid_data) > 0:
                    print(f"\n{metric}:")
                    print(f"  有效数据: {len(valid_data)}/{len(df)}")
                    print(f"  唯一值数量: {valid_data.nunique()}")
                    print(f"  值分布: {valid_data.value_counts().head(10).to_dict()}")

