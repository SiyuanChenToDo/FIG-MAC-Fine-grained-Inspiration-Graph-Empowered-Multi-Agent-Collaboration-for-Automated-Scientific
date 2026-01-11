"""
JSON标注文件转Excel工具
=========================
功能：
1. 将JSON格式的标注文件转换为Excel格式
2. 方便在Excel中进行标注
3. 支持将标注完成的Excel转回JSON格式
"""

import json
import os
from typing import Dict, List
import pandas as pd

# =================================================================================
# 1. JSON转Excel
# =================================================================================
def json_to_excel(json_file_path: str, output_excel_path: str):
    """
    将JSON标注文件转换为Excel
    
    Args:
        json_file_path: 输入的JSON文件路径
        output_excel_path: 输出的Excel文件路径
    """
    print(f"读取JSON文件: {json_file_path}")
    
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 提取samples
    samples = data.get("samples", [])
    
    if not samples:
        print("⚠️ 没有找到样本数据")
        return
    
    # 转换为DataFrame
    df = pd.DataFrame(samples)
    
    # 调整列顺序，将重要信息放在前面
    priority_columns = [
        "sample_id", "validation_type",
        "paper_a_id", "paper_a_abstract", "paper_a_core_problem",
        "paper_b_id", "solution_text",
        "llm_classification", "llm_reasoning",
        "human_classification", "notes"
    ]
    
    # 保留存在的列
    ordered_columns = [col for col in priority_columns if col in df.columns]
    other_columns = [col for col in df.columns if col not in priority_columns]
    final_columns = ordered_columns + other_columns
    
    df = df[final_columns]
    
    # 保存为Excel
    with pd.ExcelWriter(output_excel_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='标注数据', index=False)
        
        # 添加元数据sheet
        if "metadata" in data:
            metadata_df = pd.DataFrame([data["metadata"]])
            metadata_df.to_excel(writer, sheet_name='元数据', index=False)
    
    print(f"✅ Excel文件已保存到: {output_excel_path}")
    print(f"   共 {len(df)} 条数据")

# =================================================================================
# 2. Excel转JSON
# =================================================================================
def excel_to_json(excel_file_path: str, output_json_path: str, original_json_path: str = None):
    """
    将标注完成的Excel转回JSON格式
    
    Args:
        excel_file_path: 输入的Excel文件路径
        output_json_path: 输出的JSON文件路径
        original_json_path: 原始JSON文件路径（用于保留元数据）
    """
    print(f"读取Excel文件: {excel_file_path}")
    
    # 读取Excel
    df = pd.read_excel(excel_file_path, sheet_name='标注数据')
    
    # 转换为字典列表
    samples = df.to_dict('records')
    
    # 处理NaN值
    for sample in samples:
        for key, value in sample.items():
            if pd.isna(value):
                sample[key] = ""
    
    # 构建输出数据
    output_data = {
        "samples": samples
    }
    
    # 尝试加载原始元数据
    if original_json_path and os.path.exists(original_json_path):
        with open(original_json_path, 'r', encoding='utf-8') as f:
            original_data = json.load(f)
            if "metadata" in original_data:
                output_data["metadata"] = original_data["metadata"]
    else:
        # 尝试从Excel的元数据sheet读取
        try:
            metadata_df = pd.read_excel(excel_file_path, sheet_name='元数据')
            output_data["metadata"] = metadata_df.to_dict('records')[0]
        except:
            pass
    
    # 保存为JSON
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ JSON文件已保存到: {output_json_path}")
    print(f"   共 {len(samples)} 条数据")

# =================================================================================
# 3. 批量转换
# =================================================================================
def batch_convert_json_to_excel(data_dir: str):
    """批量将目录下的所有JSON文件转换为Excel"""
    print(f"扫描目录: {data_dir}")
    
    files = os.listdir(data_dir)
    json_files = [f for f in files if f.endswith('.json') and not f.startswith('标注')]
    
    if not json_files:
        print("⚠️ 未找到JSON文件")
        return
    
    print(f"找到 {len(json_files)} 个JSON文件")
    
    for json_file in json_files:
        json_path = os.path.join(data_dir, json_file)
        excel_path = json_path.replace('.json', '.xlsx')
        
        try:
            json_to_excel(json_path, excel_path)
        except Exception as e:
            print(f"❌ 转换失败 {json_file}: {e}")
    
    print("\n✅ 批量转换完成")

def batch_convert_excel_to_json(data_dir: str):
    """批量将目录下的所有Excel文件转回JSON"""
    print(f"扫描目录: {data_dir}")
    
    files = os.listdir(data_dir)
    excel_files = [f for f in files if f.endswith('.xlsx')]
    
    if not excel_files:
        print("⚠️ 未找到Excel文件")
        return
    
    print(f"找到 {len(excel_files)} 个Excel文件")
    
    for excel_file in excel_files:
        excel_path = os.path.join(data_dir, excel_file)
        json_path = excel_path.replace('.xlsx', '_标注完成.json')
        original_json_path = excel_path.replace('.xlsx', '.json')
        
        try:
            excel_to_json(excel_path, json_path, original_json_path)
        except Exception as e:
            print(f"❌ 转换失败 {excel_file}: {e}")
    
    print("\n✅ 批量转换完成")

# =================================================================================
# 4. 命令行接口
# =================================================================================
def main():
    """主函数 - 提供简单的命令行交互"""
    print("="*80)
    print("JSON ↔ Excel 转换工具")
    print("="*80)
    
    print("\n请选择操作:")
    print("1. JSON转Excel (单个文件)")
    print("2. Excel转JSON (单个文件)")
    print("3. 批量JSON转Excel (整个目录)")
    print("4. 批量Excel转JSON (整个目录)")
    
    choice = input("\n请输入选项 (1-4): ").strip()
    
    if choice == "1":
        json_path = input("请输入JSON文件路径: ").strip()
        excel_path = json_path.replace('.json', '.xlsx')
        json_to_excel(json_path, excel_path)
    
    elif choice == "2":
        excel_path = input("请输入Excel文件路径: ").strip()
        json_path = excel_path.replace('.xlsx', '_标注完成.json')
        original_json = excel_path.replace('.xlsx', '.json')
        excel_to_json(excel_path, json_path, original_json)
    
    elif choice == "3":
        data_dir = input("请输入目录路径 (默认: Myexamples/build_graph_connections/annotation_data): ").strip()
        if not data_dir:
            data_dir = "Myexamples/build_graph_connections/annotation_data"
        batch_convert_json_to_excel(data_dir)
    
    elif choice == "4":
        data_dir = input("请输入目录路径 (默认: Myexamples/build_graph_connections/annotation_data): ").strip()
        if not data_dir:
            data_dir = "Myexamples/build_graph_connections/annotation_data"
        batch_convert_excel_to_json(data_dir)
    
    else:
        print("❌ 无效选项")

# =================================================================================
# 5. 快捷函数
# =================================================================================
def convert_all_annotators_to_excel():
    """快捷函数：转换所有博士生目录下的JSON为Excel"""
    base_dir = "Myexamples/build_graph_connections/annotation_data"
    annotators = ["博士生A", "博士生B", "博士生C"]
    
    print("="*80)
    print("批量转换所有博士生的标注数据为Excel")
    print("="*80)
    
    for annotator in annotators:
        annotator_dir = os.path.join(base_dir, annotator)
        if os.path.exists(annotator_dir):
            print(f"\n处理 {annotator} 的数据...")
            batch_convert_json_to_excel(annotator_dir)
        else:
            print(f"\n⚠️ 未找到 {annotator} 的目录")
    
    print("\n" + "="*80)
    print("✅ 所有博士生的数据转换完成")
    print("="*80)

def convert_all_annotators_to_json():
    """快捷函数：转换所有博士生目录下的Excel为JSON"""
    base_dir = "Myexamples/build_graph_connections/annotation_data"
    annotators = ["博士生A", "博士生B", "博士生C"]
    
    print("="*80)
    print("批量转换所有博士生的Excel为JSON")
    print("="*80)
    
    for annotator in annotators:
        annotator_dir = os.path.join(base_dir, annotator)
        if os.path.exists(annotator_dir):
            print(f"\n处理 {annotator} 的数据...")
            batch_convert_excel_to_json(annotator_dir)
        else:
            print(f"\n⚠️ 未找到 {annotator} 的目录")
    
    print("\n" + "="*80)
    print("✅ 所有博士生的数据转换完成")
    print("="*80)

def quick_convert_all_to_excel():
    """快捷函数：转换annotation_data目录下所有JSON为Excel（包括所有博士生）"""
    convert_all_annotators_to_excel()

def quick_convert_all_to_json():
    """快捷函数：转换annotation_data目录下所有Excel为JSON（包括所有博士生）"""
    convert_all_annotators_to_json()

if __name__ == "__main__":
    # 可以直接调用快捷函数，或运行交互式界面
    
    # 方式1：交互式
    # main()
    
    # 方式2：直接批量转换（注释掉main()，取消下面的注释）
    quick_convert_all_to_excel()  # 生成Excel
    # quick_convert_all_to_json()   # 转回JSON
