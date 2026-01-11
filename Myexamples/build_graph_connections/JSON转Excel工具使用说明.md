# JSON转Excel工具使用说明

## 📋 功能概述

本工具用于在JSON和Excel格式之间转换标注数据，方便博士生在Excel中进行标注。

## 🚀 快速开始

### 方式1：一键批量转换（推荐）

```python
# 在Python中运行
from json转excel工具 import quick_convert_all_to_excel

# 转换所有博士生的JSON文件为Excel
quick_convert_all_to_excel()
```

这会自动处理：
- `博士生A/共同校验数据.json` → `博士生A/共同校验数据.xlsx`
- `博士生A/独立校验数据.json` → `博士生A/独立校验数据.xlsx`
- `博士生B/...` 
- `博士生C/...`

### 方式2：交互式界面

```bash
python json转excel工具.py
```

然后按提示选择操作：
1. JSON转Excel (单个文件)
2. Excel转JSON (单个文件)
3. 批量JSON转Excel (整个目录)
4. 批量Excel转JSON (整个目录)

## 📊 Excel文件结构

转换后的Excel包含两个工作表：

### 1. 标注数据（主表）

| 列名 | 说明 | 是否需要填写 |
|------|------|-------------|
| sample_id | 样本ID | ❌ 只读 |
| validation_type | 校验类型（精确/大致） | ❌ 只读 |
| paper_a_id | 论文A的DOI | ❌ 只读 |
| paper_a_abstract | 论文A的摘要 | ❌ 只读 |
| paper_a_core_problem | 论文A的核心问题 | ❌ 只读 |
| paper_b_id | 论文B的DOI | ❌ 只读 |
| solution_text | 论文B的解决方案 | ❌ 只读 |
| llm_classification | LLM的分类结果 | ❌ 只读（参考） |
| llm_reasoning | LLM的推理过程 | ❌ 只读（参考） |
| **human_classification** | **人工分类结果** | ✅ **需要填写** |
| **notes** | **备注** | ✅ 可选填写 |

### 2. 元数据

包含任务的基本信息（标注员、样本数等）

## ✍️ 标注流程

### 步骤1：转换为Excel

```python
from json转excel工具 import quick_convert_all_to_excel
quick_convert_all_to_excel()
```

### 步骤2：在Excel中标注

1. 打开对应的Excel文件（如`博士生A/共同校验数据.xlsx`）
2. 阅读每一行的论文内容
3. 在`human_classification`列填写分类结果：
   - `INSPIRED` - 启发关系
   - `RELATED` - 相关关系
   - `NONE` - 无关系
4. 如有疑问，在`notes`列记录

**提示：**
- 可以参考`llm_classification`和`llm_reasoning`列
- 如果同意LLM的判断，直接复制即可
- 如果不同意，填写自己的判断

### 步骤3：转回JSON

标注完成后，将Excel转回JSON：

```python
from json转excel工具 import quick_convert_all_to_json
quick_convert_all_to_json()
```

这会生成带`_标注完成`后缀的JSON文件：
- `共同校验数据_标注完成.json`
- `独立校验数据_标注完成.json`

## 📝 标注示例

### Excel中的一行数据：

| human_classification | notes |
|---------------------|-------|
| INSPIRED | 论文B的注意力机制可以直接应用于论文A的图像分类问题 |

或

| human_classification | notes |
|---------------------|-------|
| NONE | 两篇论文领域完全不同，无关联 |

## ⚠️ 注意事项

### 1. 不要修改以下列
- `sample_id`
- `paper_a_id`
- `paper_b_id`
- `paper_a_abstract`
- `paper_a_core_problem`
- `solution_text`

### 2. 分类值必须是以下之一
- `INSPIRED`
- `RELATED`
- `NONE`

拼写错误会导致数据无效！

### 3. 保存文件格式
- 必须保存为`.xlsx`格式
- 不要改变文件名
- 不要删除"元数据"工作表

## 🔧 高级用法

### 单个文件转换

```python
from json转excel工具 import json_to_excel, excel_to_json

# JSON转Excel
json_to_excel(
    "博士生A/共同校验数据.json",
    "博士生A/共同校验数据.xlsx"
)

# Excel转JSON
excel_to_json(
    "博士生A/共同校验数据.xlsx",
    "博士生A/共同校验数据_标注完成.json",
    "博士生A/共同校验数据.json"  # 原始JSON（保留元数据）
)
```

### 指定目录批量转换

```python
from json转excel工具 import batch_convert_json_to_excel

# 只转换博士生A的数据
batch_convert_json_to_excel("annotation_data/博士生A")
```

## 📊 数据验证

转换完成后，建议检查：

1. **行数是否一致**
   - 共同校验：50行
   - 独立校验：500行

2. **必填列是否完整**
   - `human_classification`列不应有空值

3. **分类值是否正确**
   - 只能是`INSPIRED`、`RELATED`、`NONE`

## ❓ 常见问题

### Q1: Excel文件打开后中文乱码怎么办？
**A**: 使用Excel 2016或更高版本，或使用WPS Office。如果仍有问题，在Excel中选择"数据" → "从文本/CSV" → 选择UTF-8编码。

### Q2: 转换后的JSON文件在哪里？
**A**: 与原Excel文件同目录，文件名后缀为`_标注完成.json`。

### Q3: 可以在Excel中添加新列吗？
**A**: 可以，但转回JSON时新列会被保留。建议只在`notes`列记录额外信息。

### Q4: 标注到一半可以保存吗？
**A**: 可以！随时保存Excel文件，标注完成后再转回JSON。

### Q5: 如何批量检查标注完成情况？
**A**: 在Excel中使用筛选功能，筛选`human_classification`列为空的行。

## 📞 技术支持

如遇到问题：
1. 检查Python版本（建议3.8+）
2. 确保安装了`pandas`和`openpyxl`：
   ```bash
   pip install pandas openpyxl
   ```
3. 检查文件路径是否正确
4. 查看控制台错误信息
