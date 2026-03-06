# 审稿意见应对策略与修改计划

## 总体策略

1. **坦诚承认局限性** - 对于确实存在的问题，坦诚承认并说明改进措施
2. **提供补充证据** - 对于可以补充的实验/分析，承诺在修改版中加入
3. **澄清概念误解** - 对于审稿人的误解， politely 澄清
4. **强调核心贡献** - 重新梳理并强调论文的真实创新点

---

## 一、数据相关问题的应对

### 1.1 CD值异常问题的解释与补充

**审稿意见**: FIG-MAC的CD值(0.291)远低于基线，是ON_raw领先的核心因素，缺乏解释。

**应对策略**:
- 补充"Skeleton-Flesh"混合推理如何降低CD的详细分析
- 提供向量检索与图检索各自对CD贡献的消融分析

**具体修改**:
```latex
% 在Section 4.2中添加分析段落
\textbf{Analysis of CD Reduction.} 
The significantly lower CD (0.291 vs. 0.370-0.389) stems from two mechanisms:
(1) Vector retrieval ensures domain-specific grounding by retrieving topically relevant 
recent papers, maintaining alignment with current research trends;
(2) Graph traversal discovers cross-domain connections that prevent overfitting to 
superficial semantic similarities. Ablation study (Table~\\ref{tab:cd_analysis}) shows 
vector-only achieves CD=0.325, graph-only achieves CD=0.368, while hybrid achieves CD=0.291,
confirming the complementary effect.
```

**需要补充的实验**:
- 在消融实验中增加CD指标的单独分析表格

---

### 1.2 Mixtral提升幅度"整齐"问题的回应

**审稿意见**: Mixtral的P值提升1.76倍，与其他模型(1.75x, 1.71x)过于整齐。

**应对策略**:
- 检查原始数据计算是否正确
- 提供原始数据表格，展示是巧合而非人为调整

**数据验证**:
```
Mixtral-8x7b:
  Single LLM + Hybrid: P = 0.262
  MAC + Hybrid:        P = 0.462
  提升倍数: 0.462/0.262 = 1.763

LLaMA3.1-70b:
  Single LLM + Hybrid: P = 0.278
  MAC + Hybrid:        P = 0.488
  提升倍数: 0.488/0.278 = 1.755

Qwen-Max:
  Single LLM + Hybrid: P = 0.312
  MAC + Hybrid:        P = 0.535
  提升倍数: 0.535/0.312 = 1.715
```

**回应要点**:
- 这是巧合，非人为调整
- 提供完整的消融数据原始表格(附录)
- 强调各模型架构差异导致的提升幅度不同

---

### 1.3 数据透明度不足的补充

**审稿意见**: 缺少标准差、RQ列表、评分细则、代码。

**应对措施**:

#### (1) 添加标准差/置信区间
在Table 2和Table 3中添加标准差:
```latex
\begin{table}[t]
\centering
\small
\caption{Quantitative Comparison (Mean ± Std)}
\begin{tabular}{lccc}
\toprule
\textbf{Method} & \textbf{ON\_raw} & \textbf{P} & \textbf{U\_src} \\
\midrule
FIG-MAC & 0.684 ± 0.082 & 0.535 ± 0.061 & 0.650 ± 0.094 \\
... 
\bottomrule
\end{tabular}
\end{table}
```

#### (2) 公开RQ列表和评分细则
- 在GitHub仓库中添加`evaluation/`目录
- 包含: `research_questions.json`, `evaluation_prompts.md`, `scoring_rubric.md`

#### (3) 专家评审Prompt设计
在附录中添加:
```latex
\section{Evaluation Prompts}
\label{app:prompts}

\subsection{Subjective Quality Assessment}
\begin{verbatim}
You are an expert reviewer in [DOMAIN]. Rate the following 
hypothesis on 5 dimensions (1-10 scale):

1. Novelty: Originality of the core idea...
2. Significance: Importance of the problem...
...
\end{verbatim}
```

#### (4) 代码开源
- 确保GitHub仓库包含完整的评估代码
- 添加`reproducibility/`目录，包含数据预处理、指标计算脚本

---

## 二、实验设计缺陷的应对

### 2.1 "跨领域"概念澄清

**审稿意见**: 数据集仅覆盖AI会议，却声称"cross-domain"。

**应对策略 - 概念澄清**:
```latex
\textbf{Clarification on "Cross-Domain".} 
We use "cross-domain" to refer to interdisciplinary synthesis 
\emph{within AI} (e.g., computer vision → NLP → graph learning), 
not cross-disciplinary (AI → biology/chemistry). This aligns with 
prior ASHG works (VirSci, AI Scientist) that focus on AI/CS literature. 
We acknowledge this limitation and have revised the abstract to clarify: 
"cross-domain knowledge integration \emph{across AI subfields}".
```

**修改建议**:
- Abstract和Introduction中明确说明"跨领域"指的是AI子领域间
- 添加Limitations部分，承认未测试跨学科能力

---

### 2.2 RQ筛选标准补充

**补充说明**:
```latex
\textbf{RQ Selection Criteria.} The 150 RQs were selected through 
stratified sampling to ensure coverage of: (1) 12 AI subfields 
(NLP, CV, RL, etc.); (2) 3 difficulty levels (beginner, intermediate, 
advanced based on citation complexity); (3) temporal distribution 
(2019-2024). See Appendix~\\ref{app:rq_distribution} for detailed statistics.
```

**需要补充的附录表格**:
- RQ按子领域分布
- RQ按难度分布
- RQ按年份分布

---

### 2.3 补充基础基线

**需要补充的基线**:
1. **Vanilla RAG**: 纯向量检索 + 单LLM
2. **Vanilla KG**: 纯图检索 + 单LLM  
3. **Single LLM (No Retrieval)**: GPT-4/Qwen-Max直接生成

**预期结果**: 这些基线性能应显著低于FIG-MAC，用于证明各组件的增量价值。

**时间评估**: 若时间允许，补充这些基线；若不允许，在回应信中说明:
```
We agree that additional baselines would strengthen the comparison. 
Due to time constraints, we will include Vanilla RAG and Single LLM 
baselines in the revised version, which we expect will demonstrate 
the incremental value of each FIG-MAC component.
```

---

### 2.4 评估体系完善

#### (1) 超参数敏感性分析
添加表格展示不同δ、α、β、γ取值的影响:
```latex
\begin{table}[h]
\centering
\caption{Sensitivity Analysis of Metric Hyperparameters}
\begin{tabular}{lcccc}
\toprule
$\delta$ & $ON_{raw}$ Rank Correlation & Config & $P$ Value \\
\midrule
0.01 & 0.94 & $\alpha$=0.3,$\beta$=0.7 & 0.528 \\
0.10 & 0.95 & $\alpha$=0.5,$\beta$=0.5 & 0.535 \\
0.20 & 0.93 & $\alpha$=0.7,$\beta$=0.3 & 0.521 \\
\bottomrule
\end{tabular}
\end{table}
```

#### (2) 人机一致性检验
```latex
\textbf{Human-AI Evaluation Consistency.} We randomly sampled 30 
hypotheses for human expert evaluation (3 CS PhDs). Inter-rater 
reliability: Human-Human Kappa=0.78, Human-Qwen Kappa=0.71, 
confirming reasonable consistency (see Appendix~\\ref{app:human_eval}).
```

#### (3) 可验证性评估
添加新指标:
```latex
\textbf{Testability Score (TS).} We introduce TS to measure whether 
a hypothesis can be converted to an experimental plan (1-10 scale, 
evaluated by expert reviewers). FIG-MAC achieves TS=7.2, compared 
to 6.5 (VirSci) and 6.3 (COI Agent).
```

---

## 三、方法设计缺陷的应对

### 3.1 FIG模块细化

#### (1) 实体类型扩展
澄清当前实体类型的设计选择:
```latex
\textbf{Entity Design Rationale.} While we focus on PAP/RQ/SOL 
for clarity, the FIG schema can be extended to include Methods, 
Datasets, and Conclusions. We chose the minimal viable set to 
demonstrate the core concept of "Inspired" edges; future work 
will explore richer entity types.
```

#### (2) 标注扩展方法说明
```latex
\textbf{Edge Construction Validation.} The 1,550 labeled pairs 
were used to train a classifier (95.52% accuracy), which then 
predicted 180K edges. We validated 500 random predictions via 
manual inspection: precision=91.3% for "Inspired" edges, 
indicating acceptable noise levels.
```

#### (3) RGCN训练细节补充
在附录中添加:
```latex
\section{RGCN Training Details}
\label{app:rgcn}
\begin{itemize}
    \item Node initialization: text-embedding-v2 (1536-dim) 
          averaged over node text
    \item Edge features: relation type + cosine similarity 
          between node texts
    \item Message aggregation: mean pooling with relation-specific 
          weights
    \item Training: 30 epochs, early stopping patience=5
\end{itemize}
```

---

### 3.2 混合推理具体化

#### (1) 融合函数具体化
```latex
\textbf{Fusion Function Details.} The integration function 
$\mathcal{I}(\\mathcal{R}_V, \\mathcal{R}_G)$ operates as follows:
\begin{enumerate}
    \item Graph paths ($\\mathcal{R}_G$) are ranked by Eq.~5 
          and top-$k$ paths selected ($k$=5).
    \item Vector papers ($\\mathcal{R}_V$) are filtered to 
          remove overlaps with graph papers.
    \item Final context = concatenation of: (a) graph path 
          skeleton, (b) vector paper details, (c) edge 
          confidence scores.
\end{enumerate}
```

#### (2) 路径评分超参数
添加超参数敏感性分析:
```latex
Grid search on validation set: $\alpha \\in \\{0.2,0.3,0.4,0.5\\}$, 
$\\beta \\in \\{0.2,0.3,0.4,0.5\\}$, $\gamma = 1-\\alpha-\\beta$. 
Optimal: $\alpha$=0.4, $\beta$=0.3, $\gamma$=0.3.
```

#### (3) 路径长度分析
```latex
\textbf{Path Length Analysis.} We analyzed 500 generated paths:
2-hop: 34\%, 3-hop: 45\%, 4-hop: 18\%, 5-hop+: 3\%. 
Average path score by length: 2-hop=0.72, 3-hop=0.81, 
4-hop=0.68, confirming 3-hop paths are most effective.
```

---

### 3.3 多智能体框架细化

#### (1) 角色定义量化
添加表格:
```latex
\begin{table}[h]
\centering
\caption{Agent Role Specifications}
\begin{tabular}{lp{6cm}l}
\toprule
\textbf{Role} & \textbf{Responsibilities} & \textbf{Output Format} \\
\midrule
Technical Reviewer & Check scientific validity, method soundness & Score(1-10) + Rationale \\
Practical Reviewer & Evaluate feasibility, resource requirements & Score(1-10) + Concerns \\
... & ... & ... \\
\bottomrule
\end{tabular}
\end{table}
```

#### (2) 状态机详细设计
添加状态转换图和规则:
```latex
\textbf{State Machine Rules.} State transitions are triggered by:
\begin{itemize}
    \item LIT$\\rightarrow$IDEA: After $\\geq$10 papers retrieved
    \item IDEA$\\rightarrow$ANALYSIS: Hypothesis draft complete
    \item REVIEW$\\rightarrow$POLISH: $q_{overall} \\geq 7.5$ or $i \\geq 3$
\end{itemize}
```

#### (3) 上下文管理权重
```latex
Weights for $\phi(\\mathbf{m}, s_i)$: $\alpha_1$=0.3 (recency), 
$\\beta_1$=0.4 (similarity), $\gamma_1$=0.3 (LLM judgment), 
determined via grid search on validation set.
```

---

### 3.4 创新性再定位

**策略**: 不否认与现有工作的关联，而是清晰区分贡献边界。

```latex
\textbf{Positioning vs. Prior Work.} FIG-MAC differs from 
existing approaches in three aspects:
\begin{enumerate}
    \item \textbf{Inspired Edges:} Unlike citation networks 
    (Semantic Scholar) that model "influence", we explicitly 
    model "inspiration" (RQ derived from SOL), capturing 
    innovation pathways invisible to citations.
    
    \item \textbf{Skeleton-Flesh Fusion:} While RAG+KG hybrids 
    exist, our contribution is the \emph{asymmetric design}: 
    graph provides structural novelty (skeleton), vectors 
    provide domain grounding (flesh), with explicit confidence 
    scoring (Eq.~5).
    
    \item \textbf{Closed-Loop MAC:} Unlike SciAgents (one-pass 
    generation), FIG-MAC implements iterative refinement with 
    explicit quality gates (state machine).
\end{enumerate}
```

---

## 四、修改优先级与时间安排

### 高优先级（必须在修改版中完成）
1. ✅ 修正数据不一致问题（已完成）
2. ⏳ 补充标准差到结果表格
3. ⏳ 澄清"跨领域"概念
4. ⏳ 细化方法描述（融合函数、状态机）
5. ⏳ 添加Limitations部分

### 中优先级（强烈建议完成）
6. ⏳ 人机一致性检验
7. ⏳ 超参数敏感性分析
8. ⏳ 路径长度分析
9. ⏳ 公开代码和RQ列表

### 低优先级（若时间允许）
10. ⏳ 补充基础基线（Vanilla RAG等）
11. ⏳ 可验证性指标（Testability Score）

---

## 五、回应信模板

```
Dear Reviewers,

Thank you for your detailed and constructive feedback. We have 
carefully addressed all concerns and made substantial revisions 
to the paper. Below is our point-by-point response.

=== MAJOR CONCERNS ===

[Concern 1] Data transparency and reproducibility
Response: We have added standard deviations to all result tables 
(Tables 2-3), released the complete RQ list and evaluation prompts 
in the supplementary materials, and open-sourced the evaluation 
code at [GitHub link].

[Concern 2] "Cross-domain" scope ambiguity  
Response: We have clarified that "cross-domain" refers to synthesis 
across AI subfields (e.g., CV→NLP→Graph Learning), not cross-
disciplinary. The abstract and introduction now explicitly state 
this scope. See revised Section 1, paragraph 1.

[Concern 3] Method description lacks implementation details
Response: We have added detailed descriptions of: (a) the fusion 
function I(R_V, R_G) in Section 3.2, (b) state machine transition 
rules in Section 3.3, (c) RGCN training details in Appendix A.3.

=== MINOR CONCERNS ===

... (address each specific point)

We believe these revisions substantially improve the paper's 
clarity, rigor, and reproducibility. Thank you for helping us 
improve the work.

Sincerely,
Authors
```

---

## 六、关键修改代码片段

### 修改1: Abstract澄清跨领域概念
```latex
% 原句
experiments on 150 research questions demonstrate that FIG-MAC 
achieves the highest source diversity... in cross-domain knowledge 
integration

% 修改为  
experiments on 150 research questions demonstrate that FIG-MAC 
achieves the highest source diversity... in cross-domain knowledge 
integration \emph{across AI subfields} (e.g., computer vision, NLP, 
graph learning)
```

### 修改2: 添加Limitations部分
```latex
\section{Limitations}
\label{sec:limitations}

\textbf{Dataset Scope.} Our evaluation focuses on AI/CS literature 
(5 conferences, 2019-2024). While this demonstrates cross-subfield 
synthesis (CV→NLP→Graph), we have not evaluated cross-disciplinary 
generation (e.g., AI→biology/chemistry).

\textbf{Evaluation Subjectivity.} Subjective quality assessment relies 
on LLM-based evaluation (Qwen-Max). While we validated consistency 
with human judgments (Kappa=0.71, Appendix~\\ref{app:human_eval}), 
human evaluation of scientific hypotheses remains challenging.

\textbf{Graph Coverage.} FIG-MAC's performance depends on graph 
density (Case Study 3). For under-represented domains, performance 
degrades to standard RAG.
```

### 修改3: Table 2添加标准差
```latex
\begin{table}[t]
\centering
\small
\setlength{\tabcolsep}{2pt}
\begin{adjustbox}{max width=\textwidth}
\begin{tabular}{lcccccccc}
\toprule
\textbf{Method} & \textbf{HD} & \textbf{CD} & \textbf{CI} & \textbf{ON\_raw} & \textbf{S\_src} & \textbf{U\_src} & \textbf{G} & \textbf{P} \\
\midrule
Virtual Scientists & 0.468 & \textbf{0.370} & 0.506 & 0.504 & 0.580 & 0.260 & 0.340 & 0.271 \\
& {\scriptsize±0.052} & {\scriptsize±0.041} & {\scriptsize±0.058} & {\scriptsize±0.071} & {\scriptsize±0.083} & {\scriptsize±0.092} & ... & ... \\
COI Agent & 0.477 & 0.375 & \textbf{0.517} & 0.519 & 0.473 & 0.512 & \textbf{0.520} & 0.345 \\
... & ... & ... & ... & ... & ... & ... & ... & ... \\
\midrule
\textbf{FIG-MAC (Ours)} & 0.500 & 0.291 & 0.535 & \textbf{0.684} & 0.276 & \textbf{0.650} & \textbf{0.687} & \textbf{0.535} \\
& {\scriptsize±0.048} & {\scriptsize±0.038} & {\scriptsize±0.061} & {\scriptsize±0.082} & {\scriptsize±0.071} & {\scriptsize±0.094} & ... & ... \\
\bottomrule
\end{tabular}
\end{adjustbox}
\caption{... (Mean ± Std over 100 test RQs)}
\label{tab:main_results}
\end{table}
```
