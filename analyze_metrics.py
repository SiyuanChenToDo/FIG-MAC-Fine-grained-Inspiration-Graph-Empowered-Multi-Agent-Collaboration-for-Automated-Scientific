import pandas as pd
import numpy as np
import os

# 文件路径
files = {
    'Ours': '/root/autodl-tmp/Myexamples/evaluation_system/batch_results/ours/metrics_summary_test_5.xlsx',
    'VirSci': '/root/autodl-tmp/virsci_metrics.xlsx',
    'COI': '/root/autodl-tmp/Myexamples/evaluation_system/batch_results/coi/coi_metrics_test_final.xlsx',
    'AI Scientist': '/root/autodl-tmp/Myexamples/evaluation_system/batch_results/ai_scientist/ai_scientist_metrics_test.xlsx'
}

# 列名映射：将不同格式的列名统一为标准名称
column_mapping = {
    # Ours和VirSci的列名 -> 标准列名
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
    # COI和AI Scientist的列名已经是标准格式，但需要确认
    'ON_normalized': 'ON_normalized',  # 保持
    'HD': 'HD',
    'CD': 'CD',
    'CI': 'CI',
    'P': 'P',
    'S_src': 'S_src',
    'U_src': 'U_src',
    'G': 'G',
}

# 我们关心的指标列（标准列名）
metrics_of_interest = [
    'Fluency_Score',
    'HD',
    'CD',
    'CI',
    'ON_raw',
    'ON_normalized',
    'S_src',
    'U_src',
    'G',
    'P',
    'Novelty',
    'Significance',
    'Effectiveness',
    'Clarity',
    'Feasibility'
]

print("=" * 80)
print("1. 检查各表列名并分析")
print("=" * 80)

results = {}

for method_name, file_path in files.items():
    if not os.path.exists(file_path):
        print(f"\n警告: 文件不存在: {file_path}")
        continue
    
    print(f"\n【{method_name}】")
    print(f"文件路径: {file_path}")
    
    try:
        # 读取Excel文件
        df = pd.read_excel(file_path)
        
        print(f"\n数据形状: {df.shape} (行数: {df.shape[0]}, 列数: {df.shape[1]})")
        print(f"\n列名列表:")
        for i, col in enumerate(df.columns, 1):
            print(f"  {i}. {col}")
        
        # 创建列名映射字典
        method_column_mapping = {}
        for old_col in df.columns:
            if old_col in column_mapping:
                method_column_mapping[old_col] = column_mapping[old_col]
            elif old_col in metrics_of_interest:
                method_column_mapping[old_col] = old_col
        
        # 重命名列
        df_renamed = df.rename(columns=method_column_mapping)
        
        # 提取数值列并计算平均值
        method_means = {}
        for metric in metrics_of_interest:
            if metric in df_renamed.columns:
                col_data = pd.to_numeric(df_renamed[metric], errors='coerce')
                if col_data.notna().any():
                    method_means[metric] = col_data.mean()
        
        results[method_name] = {
            'dataframe': df,
            'dataframe_renamed': df_renamed,
            'means': method_means,
            'columns': df.columns.tolist()
        }
        
        print(f"\n各指标平均值:")
        for metric, mean_val in sorted(method_means.items()):
            print(f"  {metric}: {mean_val:.4f}")
        
    except Exception as e:
        print(f"\n错误: 读取文件时出错 - {str(e)}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 80)
print("2. 统一列名并计算平均值")
print("=" * 80)

# 创建汇总表
summary_data = {}
for method_name, data in results.items():
    summary_data[method_name] = data['means']

# 创建DataFrame，确保所有方法都有所有指标
summary_df = pd.DataFrame(summary_data).T
summary_df = summary_df.reindex(columns=metrics_of_interest)

print("\n汇总表 (平均值):")
print(summary_df.to_string())

print("\n" + "=" * 80)
print("3. 生成三线表 (LaTeX格式)")
print("=" * 80)

# 生成LaTeX三线表
latex_table = "\\begin{table}[htbp]\n"
latex_table += "\\centering\n"
latex_table += "\\caption{实验结果对比}\n"
latex_table += "\\label{tab:results}\n"

# 计算列数
num_cols = len(metrics_of_interest) + 1  # +1 for Method column
latex_table += "\\begin{tabular}{l" + "c" * len(metrics_of_interest) + "}\n"
latex_table += "\\toprule\n"

# 表头 - 使用简化的列名
header_labels = {
    'Fluency_Score': 'Fluency',
    'HD': 'HD',
    'CD': 'CD',
    'CI': 'CI',
    'ON_raw': 'ON\\_raw',
    'ON_normalized': 'ON\\_norm',
    'S_src': 'S\\_src',
    'U_src': 'U\\_src',
    'G': 'G',
    'P': 'P',
    'Novelty': 'Novelty',
    'Significance': 'Significance',
    'Effectiveness': 'Effectiveness',
    'Clarity': 'Clarity',
    'Feasibility': 'Feasibility'
}

header = "Method"
for metric in metrics_of_interest:
    label = header_labels.get(metric, metric.replace('_', '\\_'))
    header += f" & {label}"
header += " \\\\\n"
latex_table += header
latex_table += "\\midrule\n"

# 数据行
for method_name in ['Ours', 'VirSci', 'COI', 'AI Scientist']:
    if method_name in summary_df.index:
        row = method_name
        for metric in metrics_of_interest:
            val = summary_df.loc[method_name, metric]
            if pd.isna(val):
                row += " & -"
            else:
                row += f" & {val:.4f}"
        row += " \\\\\n"
        latex_table += row

latex_table += "\\bottomrule\n"
latex_table += "\\end{tabular}\n"
latex_table += "\\end{table}\n"

print("\nLaTeX三线表代码:")
print(latex_table)

# 保存到文件
output_file = "/root/autodl-tmp/results_table.tex"
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(latex_table)
print(f"\n三线表已保存到: {output_file}")

# 同时生成Markdown格式的表格
print("\n" + "=" * 80)
print("4. 生成Markdown格式表格")
print("=" * 80)

markdown_table = "| Method"
for metric in metrics_of_interest:
    label = header_labels.get(metric, metric)
    markdown_table += f" | {label}"
markdown_table += " |\n"

markdown_table += "|" + "---|" * (len(metrics_of_interest) + 1) + "\n"

for method_name in ['Ours', 'VirSci', 'COI', 'AI Scientist']:
    if method_name in summary_df.index:
        row = f"| {method_name}"
        for metric in metrics_of_interest:
            val = summary_df.loc[method_name, metric]
            if pd.isna(val):
                row += " | -"
            else:
                row += f" | {val:.4f}"
        row += " |\n"
        markdown_table += row

print("\nMarkdown表格:")
print(markdown_table)

# 保存Markdown表格
md_output_file = "/root/autodl-tmp/results_table.md"
with open(md_output_file, 'w', encoding='utf-8') as f:
    f.write("# 实验结果对比表\n\n")
    f.write("## 说明\n\n")
    f.write("- **Ours**: 我们的实验方法结果\n")
    f.write("- **VirSci**: VirSci方法结果\n")
    f.write("- **COI**: COI方法结果\n")
    f.write("- **AI Scientist**: AI Scientist方法结果\n\n")
    f.write(markdown_table)
print(f"\nMarkdown表格已保存到: {md_output_file}")

# 保存汇总数据到Excel
excel_output = "/root/autodl-tmp/results_summary.xlsx"
with pd.ExcelWriter(excel_output, engine='openpyxl') as writer:
    summary_df.to_excel(writer, sheet_name='Summary')
    # 同时保存每个方法的详细数据
    for method_name, data in results.items():
        data['dataframe_renamed'].to_excel(writer, sheet_name=method_name, index=False)
print(f"\n汇总数据已保存到Excel: {excel_output}")

# 生成更简洁的三线表（只包含主要指标）
print("\n" + "=" * 80)
print("5. 生成简化版三线表（主要指标）")
print("=" * 80)

# 选择主要指标
main_metrics = [
    'Fluency_Score',
    'HD',
    'CD',
    'CI',
    'ON_normalized',
    'P',
    'Novelty',
    'Significance',
    'Effectiveness',
    'Clarity',
    'Feasibility'
]

latex_table_simple = "\\begin{table}[htbp]\n"
latex_table_simple += "\\centering\n"
latex_table_simple += "\\caption{实验结果对比（主要指标）}\n"
latex_table_simple += "\\label{tab:results_main}\n"
latex_table_simple += "\\begin{tabular}{l" + "c" * len(main_metrics) + "}\n"
latex_table_simple += "\\toprule\n"

header_simple = "Method"
for metric in main_metrics:
    label = header_labels.get(metric, metric.replace('_', '\\_'))
    header_simple += f" & {label}"
header_simple += " \\\\\n"
latex_table_simple += header_simple
latex_table_simple += "\\midrule\n"

for method_name in ['Ours', 'VirSci', 'COI', 'AI Scientist']:
    if method_name in summary_df.index:
        row = method_name
        for metric in main_metrics:
            val = summary_df.loc[method_name, metric]
            if pd.isna(val):
                row += " & -"
            else:
                row += f" & {val:.4f}"
        row += " \\\\\n"
        latex_table_simple += row

latex_table_simple += "\\bottomrule\n"
latex_table_simple += "\\end{tabular}\n"
latex_table_simple += "\\end{table}\n"

print("\n简化版LaTeX三线表代码:")
print(latex_table_simple)

simple_output_file = "/root/autodl-tmp/results_table_simple.tex"
with open(simple_output_file, 'w', encoding='utf-8') as f:
    f.write(latex_table_simple)
print(f"\n简化版三线表已保存到: {simple_output_file}")
