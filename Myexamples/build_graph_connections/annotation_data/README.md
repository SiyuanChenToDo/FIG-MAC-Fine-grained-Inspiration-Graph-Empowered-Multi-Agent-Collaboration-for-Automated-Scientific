# 跨论文关系人工标注系统

## 📚 项目概述

本项目提供了一套完整的工具链，用于生成、管理和分析跨论文Paper-Solution关系的人工标注数据。系统结合LLM自动分类和人工校验，确保数据质量。

---

## 🎯 主要功能

### 1. **自动化数据生成**
- 从FAISS向量数据库读取Paper和Solution数据
- 随机生成1550条跨论文配对
- LLM自动进行三分类(INSPIRED/RELATED/NONE)
- 智能分配标注任务给三位博士生

### 2. **灵活的标注方式**
- JSON格式：便于程序处理和中文显示
- Excel格式：方便人工标注
- 支持格式互转

### 3. **质量控制**
- 50条共同校验数据评估标注一致性
- 区分精确校验(100条/人)和大致校验(400条/人)
- 自动计算Fleiss' Kappa和一致性指标

### 4. **结果分析**
- LLM准确率评估
- 困难样本识别
- 混淆矩阵分析
- 自动生成改进建议

---

## 📂 文件结构

```
build_graph_connections/
├── 人工标注数据生成.py        # 主脚本：生成标注数据
├── 分析标注结果.py            # 分析标注一致性和质量
├── json转excel工具.py         # JSON↔Excel格式转换
├── 使用说明.md                # 详细使用文档
├── README.md                  # 本文件
└── annotation_data/           # 标注数据输出目录
    ├── 标注任务总览_*.json
    ├── 共同校验数据_*.json
    ├── 博士生A_标注任务_*.json
    ├── 博士生B_标注任务_*.json
    ├── 博士生C_标注任务_*.json
    └── 标注分析报告.json
```

---

## 🚀 快速开始

### 步骤1: 环境准备

```bash
# 安装依赖
pip install camel-ai numpy pandas openpyxl

# 确认向量数据库已建立
# 路径: Myexamples/vdb/camel_faiss_storage/
```

### 步骤2: 生成标注数据

```bash
cd Myexamples/build_graph_connections
python 人工标注数据生成.py
```

**预计运行时间**: 15-30分钟（包含1550次LLM API调用）

**输出**:
- 1个总览文件
- 1个共同校验文件
- 3个标注员任务文件

### 步骤3: 转换为Excel（可选）

```bash
# 交互式转换
python json转excel工具.py

# 或直接批量转换
python -c "from json转excel工具 import quick_convert_all_to_excel; quick_convert_all_to_excel()"
```

### 步骤4: 人工标注

- 打开各标注员的JSON或Excel文件
- 填写`human_classification`字段
- 可选：在`notes`字段记录备注

### 步骤5: 分析结果

```bash
python 分析标注结果.py
```

**输出**:
- Fleiss' Kappa（标注一致性）
- LLM准确率统计
- 困难样本列表
- 改进建议

---

## 📊 数据格式说明

### 标注样本结构

```json
{
  "sample_id": "博士生A_PRECISE_001",
  "validation_type": "精确校验",
  "paper_a_id": "10.xxx/xxx",
  "paper_a_abstract": "论文A的摘要...",
  "paper_a_core_problem": "论文A的核心问题...",
  "paper_b_id": "10.yyy/yyy",
  "solution_text": "论文B的解决方案...",
  "llm_classification": "INSPIRED",
  "llm_reasoning": "LLM的判断理由...",
  "human_classification": "",  // 人工标注填写此处
  "notes": ""                  // 可选备注
}
```

### 关系类型定义

| 类型 | 说明 |
|------|------|
| **INSPIRED** | 论文B的解决方案能直接或间接解决论文A的问题，提供新思路 |
| **RELATED** | 两者在领域/技术上相似，但无直接启发关系 |
| **NONE** | 无明显关系 |

---

## 🔧 配置说明

### 修改样本数量

编辑`人工标注数据生成.py`中的`CONFIG`：

```python
CONFIG = {
    "TOTAL_SAMPLES": 1550,              # 总样本数
    "COMMON_SAMPLES": 50,               # 共同校验
    "SAMPLES_PER_PERSON": 500,          # 每人总量
    "PRECISE_SAMPLES_PER_PERSON": 100,  # 精确校验
    "ROUGH_SAMPLES_PER_PERSON": 400,    # 大致校验
    "ANNOTATORS": ["博士生A", "博士生B", "博士生C"],
    "SEED": 42,  # 随机种子
}
```

### 修改LLM Prompt

编辑`人工标注数据生成.py`中的`LLM_EVALUATION_PROMPT`变量。

---

## 📈 质量指标

### Fleiss' Kappa解释

| Kappa值 | 一致性水平 |
|---------|-----------|
| < 0.0 | 差：低于随机 |
| 0.0-0.2 | 轻微 |
| 0.2-0.4 | 一般 |
| 0.4-0.6 | 中等 |
| 0.6-0.8 | 较高 ✅ |
| 0.8-1.0 | 很高 ✅✅ |

**目标**: Kappa > 0.6（较高一致性）

### LLM准确率基准

- **良好**: > 70%
- **优秀**: > 85%
- **需优化**: < 70%

---

## 🛠️ 常见问题

### Q1: 向量数据库路径错误？

**解决**：检查`CONFIG["BASE_VDB_PATH"]`是否正确指向：
```
Myexamples/vdb/camel_faiss_storage/
```

### Q2: LLM API调用失败？

**解决**：
1. 检查API密钥是否有效
2. 检查网络连接
3. 查看是否触发限流（脚本已内置限流机制）

### Q3: 如何修改标注员数量？

**解决**：修改`CONFIG["ANNOTATORS"]`列表，并相应调整样本分配逻辑。

### Q4: Excel文件打开乱码？

**解决**：使用支持UTF-8的Excel版本，或使用WPS Office。

---

## 📝 工作流程示例

### 完整流程

```bash
# 1. 生成标注数据
python 人工标注数据生成.py

# 2. 转换为Excel（便于标注）
python json转excel工具.py
# 选择选项3：批量JSON转Excel

# 3. 分发给标注员
# - 博士生A_标注任务_*.xlsx
# - 博士生B_标注任务_*.xlsx
# - 博士生C_标注任务_*.xlsx
# - 共同校验数据_*.xlsx

# 4. 标注完成后，转回JSON
python json转excel工具.py
# 选择选项4：批量Excel转JSON

# 5. 分析标注结果
python 分析标注结果.py

# 6. 根据分析报告调整标注策略
```

---

## 📚 扩展功能

### 导出到Neo4j

标注完成后，可以将确认的关系导入知识图谱：

```python
from camel.storages import Neo4j Graph

# 读取标注结果
with open('博士生A_标注任务_标注完成.json', 'r') as f:
    data = json.load(f)

# 导入到Neo4j
n4j = Neo4jGraph(url="...", username="...", password="...")

for sample in data['samples']:
    if sample['human_classification'] in ['INSPIRED', 'RELATED']:
        query = f"""
        MATCH (a:paper {{source_id: '{sample['paper_a_id']}'}}),
              (b:paper {{source_id: '{sample['paper_b_id']}'}})
        MERGE (a)-[r:{sample['human_classification']}]->(b)
        SET r.reasoning = '{sample['llm_reasoning']}'
        """
        n4j.query(query)
```

### 训练分类模型

使用标注数据微调分类模型：

```python
from sklearn.model_selection import train_test_split
from transformers import AutoModelForSequenceClassification

# 准备训练数据
texts = []
labels = []

for sample in all_samples:
    if sample['human_classification']:
        text = f"{sample['paper_a_combined']}\n[SEP]\n{sample['solution_text']}"
        texts.append(text)
        labels.append(sample['human_classification'])

# 训练模型...
```

---

## 📞 技术支持

如遇到问题：

1. 查看`使用说明.md`的详细文档
2. 检查日志输出的错误信息
3. 确认向量数据库完整性
4. 验证API配置正确性

---

## 📄 许可证

本项目遵循CAMEL-AI框架的许可证。

---

## 🎉 更新日志

### v1.0.0 (2025-01-20)
- ✅ 初始版本发布
- ✅ 支持自动化数据生成
- ✅ 集成LLM三分类
- ✅ 提供一致性分析工具
- ✅ 支持JSON↔Excel转换

---

**开发者**: CAMEL-AI Team  
**最后更新**: 2025-01-20
