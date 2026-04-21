
# 指标计算问题修复建议

## 问题1：P指标缺失 (优先级：🔴 高)

### 现象
- Excel中P指标列为空或NaN
- 影响所有150个报告

### 根本原因
1. 源文献提取失败，导致source_documents为None
2. P指标计算被跳过

### 修复方案

#### 步骤1：改进源文献提取
在 `aggregate_metrics_to_excel.py` 中修改：

```python
# 原代码
source_docs = collect_source_documents(report_path, report_text, topic_text, core_text, calculator)
objective_metrics = calculator.evaluate_text(core_text, source_documents=source_docs if source_docs else None)

# 修复后
source_docs = collect_source_documents(report_path, report_text, topic_text, core_text, calculator)
# 即使source_docs为空，也应该传入，让calculator处理
objective_metrics = calculator.evaluate_text(core_text, source_documents=source_docs)
```

#### 步骤2：添加向量检索备选方案
在 `collect_source_documents()` 函数中添加第4个备选方案：

```python
# 4. 向量检索备选方案
if len(collected) < max_docs and calculator and core_text:
    collected = improve_source_document_collection(
        core_text, calculator, collected, max_docs
    )
```

### 预期效果
- ✓ P指标完整
- ✓ 源文献数量增加
- ✓ 所有报告都有溯源评估

---

## 问题2：源文献提取不完整 (优先级：🔴 高)

### 现象
- 多个报告的源文献数量为0
- 导致P指标无法计算

### 根本原因
1. Paper ID提取可能失败
2. RAG证据提取可能失败
3. inspiration_report.md可能不存在
4. 没有向量检索备选方案

### 修复方案

使用 `improve_source_document_collection()` 函数添加向量检索：

```python
from fix_metrics_issues import improve_source_document_collection

# 在collect_source_documents中添加
source_docs = improve_source_document_collection(
    core_text=core_text,
    calculator=calculator,
    existing_docs=collected,
    max_docs=20
)
```

### 预期效果
- ✓ 源文献数量增加
- ✓ 覆盖率提高到100%
- ✓ P指标可计算

---

## 问题3：ON_normalized=0 (优先级：🟡 中)

### 现象
- 150个报告中，有1个ON_normalized = 0.0

### 是否合理？
- ✓ 数学上合理（排名最低）
- ✗ 评估上可能不合理（0值易被误解）

### 修复方案

#### 选项A：改进归一化公式（推荐）
在 `metrics_calculator.py` 中修改：

```python
# 原公式
normalized_on = rank / (N - 1)  # 范围 [0, 1]

# 改进公式
normalized_on = (rank + 1) / N  # 范围 [1/N, 1]
```

#### 选项B：添加说明文档
在Excel中添加说明：
```
ON_normalized = 0.0 表示该报告的相对新颖性在所有报告中排名最低，
但不表示绝对新颖性为零。
```

### 预期效果
- ✓ 所有报告都得到非零值
- ✓ 避免误解
- ✓ 更合理的评估

---

## 问题4：参数文档缺失 (优先级：🟡 中)

### 现象
- 参数 (α=0.5, β=0.5, γ=0.7) 硬编码
- 没有文档说明含义和取值范围

### 修复方案

1. 生成参数说明文档：
   ```bash
   python fix_metrics_issues.py
   ```
   生成 `PROVENANCE_PARAMETERS_GUIDE.md`

2. 在代码中添加参数验证：
   ```python
   from fix_metrics_issues import validate_provenance_params
   
   params = validate_provenance_params({
       "alpha": 0.5,
       "beta": 0.5,
       "gamma": 0.7
   })
   ```

### 预期效果
- ✓ 参数含义清晰
- ✓ 参数可验证
- ✓ 代码更健壮

---

## 修复优先级和时间表

### 第1阶段（立即）- 高优先级问题
- [ ] 修复P指标缺失（步骤1-2）
- [ ] 改进源文献提取（添加向量检索）
- 预计时间：2-4小时

### 第2阶段（本周）- 中优先级问题
- [ ] 改进ON_normalized公式
- [ ] 生成参数说明文档
- 预计时间：1-2小时

### 第3阶段（本月）- 长期改进
- [ ] 添加参数配置和验证
- [ ] 完善测试和文档
- 预计时间：4-8小时

---

## 修复验证清单

修复完成后，请检查以下项目：

- [ ] P指标不再为空或NaN
- [ ] 所有报告都有源文献（Source_Count > 0）
- [ ] ON_normalized范围为 [1/N, 1]，无0值
- [ ] 参数说明文档完整
- [ ] 参数验证函数可用
- [ ] Excel文件可正常打开和查看
- [ ] 指标值在合理范围内

---

## 相关文件

- 审查报告：`METRICS_REVIEW_REPORT.md`
- 参数指南：`PROVENANCE_PARAMETERS_GUIDE.md`
- 修复工具：`fix_metrics_issues.py`
- 原脚本：`aggregate_metrics_to_excel.py`
- 计算器：`metrics_calculator.py`
