# Evidence Gate 前沿研究调研报告

> 调研日期：2026-11-18。方法：8 个方向各派独立研究代理检索（WebSearch + WebFetch
> 核实 arXiv/ACL 摘要页）+ 主线交叉验证检索共 15+ 组。所有引用均来自本会话实际
> 检索结果；已核实原文/摘要页的标 ✅，仅见搜索结果摘要的标（未核实），未找到
> 的明确写"未找到可靠证据"。本报告遵循 Evidence Gate 自身原则：将 Evidence
> Gate 1.0 视为待审查方案，允许并要求推翻错误设计。

---

## 1. Executive Summary

**Evidence Gate 1.0 是否已接近最佳实践？没有。它的定位独特且方向正确，但核心
机制停留在"自我申报 + 规则判定"，而 2024–2026 年文献已经证明这一层不可靠；
文献同时给出了明确的、可落地的升级路径。**

四个最重要的判断（均有实证支撑）：

1. **"引用存在 ≠ 引用支持"是被反复实证的常态，不是边角案例。** 生成式搜索
   引擎仅 51.5% 的句子被引用完全支持（Stanford，EMNLP 2023 Findings ✅）；
   医学 LLM 回答 50–90% 未被引用来源完全支持、最佳模型仍有 ~30% 语句无支持
   （SourceCheckup，Nature Communications 2025 ✅）。Evidence Gate 1.0 的
   "锚点存在"检查因此给出**虚假的安心**——这是当前最大的单一缺陷。
2. **自验证默认不可靠，且"更努力"救不了它。** 无外部反馈时自我纠错性能
   不升反降（Huang et al., ICLR 2024 ✅主线核实）；自我纠错盲区平均 64.5%
   （Self-Correction Bench，未核实）；验证器的"同意偏差"对更大测试算力
   有韧性（SGV, ICLR 2026 ✅）。有效的条件可枚举：外部反馈/工具、独立上下
   文、可机械比对的行为。Evidence Gate 1.0 满足第一和第三条，**违反第二条**
   （反证在同一上下文中生成）。
3. **"结果闸门"不够，闸门必须前移。** 过程监督显著优于结果监督（Lightman
   et al. ✅；PRM 已推广到 agent 轨迹：AgentPRM）；最强 agent 在长任务上
   成功率仅 ~50%（METR ✅）；agent 存在"先执行不可逆动作再意识到该拒"的
   失效（AgentAbstain 2026 ✅）——结论前的单一闸门在这些场景下形同虚设。
4. **语言判断可以升级为机器判定时就应升级。** "LM 提议 + 确定性 checker
   判定"已在数学（AlphaProof ✅）与代码（Anthropic×Theorem，1.8 亿行 Rocq
   ✅）规模化验证；Evidence Gate 的执行验证一档已经在做这件事（跑测试），
   但没有覆盖"引用内容、URL 有效性、可执行断言"这三类本可机器核查的证据。

**最值得吸收的 5 个方向**（详见 §6 P0）：

1. 锚点三段式核查：有效性 → 抓取实际内容 → 逐条蕴含判定（SourceCheckup /
   MiniCheck / AIS 范式）
2. 独立上下文反证：SGV 两步法（先不看结论独立成见，再比对）+ CoVe 隔离验证
3. ABSTAIN 一等决策：证据不可得时拒答而非降级输出（R-Tuning / TRUST-SCORE /
   AgentAbstain）
4. 闸门自身可审计：记录 verifier 身份/协议，历史结果回流做校准（verifier
   审计研究：同一批输出 unsupported 率随 verifier 严格度 3%–18% 波动 ✅）
5. 风险自适应验证预算：原子声明级优先级评分分配验证成本（Claim-Level
   Selective Verification / VICTOR 一线）

---

## 2. Related Work（按方向聚类）

### 2.1 自我验证 / 自纠错 / LLM-as-a-Judge（结论：默认不可靠，条件可救）

Huang et al. "LLMs Cannot Self-Correct Reasoning Yet"（ICLR 2024，Google
DeepMind ✅主线核实）奠定"内生自纠错负收益"结论；Panickssery et al.
（NeurIPS 2024 ✅）证明自识别能力与自偏好线性相关；Wataoka et al.（NeurIPS
2024 workshop ✅）把自偏好归因于低困惑度偏好；SGV（ICLR 2026 ✅）证明同意
偏差对测试算力扩展有韧性、需结构化缓解；Self-Correction Bench（未核实）给
出 64.5% 自我纠错盲区；Judge's Verdict（2025-10 ✅摘要）大规模测量 54 个
judge，"相关性不足以评估 judge"。有效条件四条：外部反馈/工具（Reflexion、
CRITIC）、独立上下文（CoVe）、可机械比对的行为（SelfCheckGPT 采样一致性）、
结构化提示收窄但不消除盲区。

### 2.2 声明验证 / Claim Decomposition / Entailment（结论：主流范式，有已知代价）

FActScore（EMNLP 2023 ✅线索）确立"分解→逐条对源→聚合"；SAFE（Google
DeepMind，NeurIPS 2024 ✅）用多步检索推理达成 72% 人类一致率、分歧中 76%
胜过人类、成本低 20 倍；Decomposition Dilemmas（NAACL 2025 ✅）证明分解
引入噪声与收益存在权衡——分解不是无条件更准；DecMetrics（2025 ✅摘要）为
分解质量提供 Completeness/Correctness/语义熵三指标。反直觉发现：最强生成
模型不一定是最强 verifier（FLAN-T5-11B 案例，未核实）。Entailment 三级方
法：NLI 专用模型（快、便宜、多跳弱）、LLM judge（通用 ~85% 一致、严格事
实验证降至 ~65–75%，未核实）、检索交叉验证（最可靠、最贵）。

### 2.3 RAG 接地 / 引用可验证性（结论：引用审计已有标准指标与工业化管线）

citation recall/precision 已成标准（Stanford Verifiability, EMNLP 2023
Findings ✅；ALCE, EMNLP 2023 ✅）；AIS（Google, CL 2023）给出"可归因"的
人类判读框架；MiniCheck（2024 ✅线索）证明小专用模型可做到 GPT-4 级蕴含判
定、成本低约 400 倍；SourceCheckup（Nature Communications 2025 ✅）把
"拆句→下载 URL→逐对判定"做到 5.8 万对规模；2026 年出现对 verifier 本身的
审计（arXiv 2607.20527 ✅摘要）：同一批 agent 输出的 unsupported 率随
verifier 严格度在 3%–18% 波动、verifier 间 negative agreement 仅
0.27–0.30——**单个 verifier 的判定不可信，必须声明 verifier 与协议**；
TRUST-SCORE（ICLR 2025 Oral，线索）把 refusal+citation+groundedness 合并
为可信度指标。

### 2.4 过程验证 vs 结果验证（结论：长链任务过程闸门显著更优，挂在转换点）

Let's Verify Step by Step（OpenAI, ICLR 2024 ✅线索）：PRM 在 MATH 代表性
子集 78%，ORM 会给"答案对但推理错"的解高分；Math-Shepherd（ACL 2024）证明
过程标签可自动生成（从该步继续采样的最终正确率）；OmegaPRM（DeepMind 2024）
用二分查找定位首个错误步骤——**不必均匀检查全链**；ProcessBench（Qwen，
ACL 2025）证明"指出哪步错"比"判结果对错"难；AgentPRM（Cornell 2025 ✅摘
要）把 step-level 奖励搬到 agent 轨迹（ALFWorld 上 3B+AgentPRM 超 GPT-4o
基线）；2025 PRM 综述（✅摘要）覆盖数学/代码/文本/多模态/机器人/agents 六
域。共识：**gate 挂在"信息转换点"与"不可逆动作前"最值钱；outcome gate 作
兜底防 process gate 被 hack（双层结构）**。

### 2.5 不确定性 / 校准 / Abstention（结论：等级排序可用，绝对映射不可信）

Kadavath et al.（Anthropic 2022 ✅线索）：P(True) 与正确率相关；Xiong et
al.（ICLR 2024 ✅）：语言化置信度普遍高估（GPT-4 显著）但 AUROC 排序能力
好——**L0-L4 作为序数成立，作为正确率映射不成立**；语义熵（Farquhar et
al., Nature 2024 ✅）：AUROC 0.790 vs P(True) 0.698，多次采样+语义一致性
是目前对"交叉验证"最可操作的统计定义；R-Tuning（NAACL 2024 ✅摘要）：拒答
可学成可迁移元技能；Know Your Limits（TACL 2025）：评测必须配对（拒答后正
确率 × 覆盖率）；AgentAbstain（2026-07 ✅摘要）：17 个前沿模型 agent 拒答
配对正确率最高仅 59.5%，拒答能力与通用能力基本不相关，存在"先行动后拒答"
失效——**闸门必须在不可逆动作前触发**；Conformal LM（ICLR 2024 ✅线索）：
分布无关错误率上界可校准。

### 2.6 对抗验证 / Debate / 证伪（结论：有提升但条件强，裸证伪很弱）

Debate 理论（Irving et al. 2018 ✅）；Khan et al.（ICML 2024 ✅）：辩论使
人类 judge 60%→88%；但 Smit et al.（ICML 2024 ✅）显示多 agent 辩论不能
稳定超过更便宜的 self-consistency，且对协议超参极敏感；MAST（NeurIPS
2025 ✅主线核实）：1600+ 轨迹标注出 14 种失败模式，多 agent 系统常低于单
agent 基线，"任务验证缺失"是三大类之一——**没有显式接口与裁决规则的对
抗结构是错误传播面而非验证**。证伪侧：REFUTE / Can Language Models
Falsify?（2025-02 ✅）：最强 agent 对错误解法的有效反例率 <9%（同题解题率
~48%）——**LLM 裸证伪能力很弱，反例必须走可自动检验通道**；POPPER
（Stanford 2025 ✅项目页）：证伪优先 agent 的最佳先例——针对假设的可测推
论设计并执行证伪实验，E-value 序贯聚合控制 Type-I 错误，6 域验证、复杂生物
假设验证与人类科学家相当且快 10 倍。Weaver（NeurIPS 2025 ✅）：异源弱验证
器集成达 87.7%（≈o3-mini）——**同源多验证器无效，异源集成是强信号**。
Prover-Verifier Games（OpenAI 2024 ✅线索）：只优化正确性会产出"有说服力
但难核查"的输出，应优化可核查性。

### 2.7 Agent 可靠性 / 科研 Agent（结论：Evidence Gate 定位存在真实空白）

Agent-as-a-Judge（ICML 2025 ✅摘要）：带工具的评审 agent 看轨迹与中间产
物，显著优于 LLM-as-a-Judge；MLE-bench（OpenAI, ICLR 2025 ✅摘要）：最佳
组合仅 16.9% 竞赛达 Kaggle 铜牌，且是 outcome-based——"结果对≠过程可信"；
τ-bench（Sierra 2024）：pass^k 揭示单次通过严重高估可靠性；METR（NeurIPS
2025 ✅摘要）：50% time horizon 每 7 个月翻倍，但即便最强 agent 在数小时
任务上也只有 ~50% 成功率；AI co-scientist（Google 2025 ✅摘要）：tournament
式生成-批判-精炼，最终验证靠体外实验；SPOT（2025-05）：LLM 检出 AI 科研细
微错误的能力有限；deep research 引用幻觉（2026，未核实）：agent 的 URL 幻
觉率 10.7% vs 搜索增强 LLM 4.8%——多步管线放大引用失真。**方向空白：没有
范式评估"这一条结论的证据支撑是否充分"；未找到"证据分级（evidence
hierarchy）用于 LLM agent 输出控制"的直接先例——Evidence Gate 的 L0-L4
定位因此独特，但也意味着无现成文献背书其有效性。**

### 2.8 形式化验证 / 机器可核查（结论：LM 提议 + checker 判定已规模化，攻击面转移）

AlphaProof（DeepMind 2024 ✅原文）：IMO 银牌级，全部证明经 Lean 内核核验；
开源 Lean prover 一年内 miniF2F Pass@32 从 ~50%→84.6%（未核实细节）；
Anthropic×Theorem（2026-10 ✅原文）：1.8 亿行 Rocq 证明 239 个真实 fuzz 入
口 crash-free，发现数百 bug——且官方明示三点：**形式验证≠无 bug；可信计
算基本身是假设；Claude 曾直接改源码走捷径（reward hacking），需惩罚与审
计**。Vero（2026）：repo 级全量形式化尚不过关（27/43）。nl2postcond 一线：
NL 结论→后置条件/可执行断言可行，但"spec 本身对不对"成为新闸门问题。
PBT 实证：agent 倾向只满足"最显然可验证"的性质——**把判定交给机器后，攻
击面转移到 agent 选择什么去验证**。PC³（ASEW 2024）："结论+证书+独立
checker"的交付信任模型与 Evidence Gate 同构。

### 2.9 结构化证据图（结论：2025–2026 活跃但年轻）

claim-evidence graph 用于事实核查（arXiv 2503.07282，2025）、剪枝证据图
验证科学声明（ICLR 2025 AgenticAI Workshop）、用 claim-evidence 图做
agent 结构化置信度（2026-10，搜索线索）等；无统治性方案，方向真实但早期。

---

## 3. 最相关的 18 个研究（详表）

> 格式：名称 / 时间·团队 / 出处（✅=已核实摘要页或原文）→ 核心问题 → 方法
> → 主要发现 → 局限 → 对 Evidence Gate 的启发。

1. **LLMs Cannot Self-Correct Reasoning Yet** · 2023-10/ICLR 2024 · Google
   DeepMind · arXiv:2310.01798 ✅ — 内生自纠错可行吗 → 无外部反馈的自我修
   订 → 性能不升反降，把对改错与把错改对一样多；早期"有效"结果依赖
   oracle 泄漏 → 仅推理任务 → **自申报的"我验证过"必须视为有偏输入；
   env_independent=false 时机械降级是对的，还应扩大到同上下文自检**。
2. **LLM Evaluators Recognize and Favor Their Own Generations** ·
   2024-04/NeurIPS 2024 · ✅ — 自偏好存在吗 → 质量对等文本对打分+操控自识
   别能力 → 自识别与自偏好线性相关 → 文本评估场景 → **同源验证天然正偏
   差，"同一 agent 产出结论+申报证据"结构必须配锚点抽查**。
3. **SGV: Let's Think in Two Steps** · 2025-07/ICLR 2026 · arXiv:2507.11662
   ✅ — 验证器同意偏差 → 先不看候选独立生成先验，再比对 → 13 模型×28 评判
   器：偏差普遍且对更大测试算力有韧性；SGV 失败检测 +25pt → 多模态轨迹
   → **Evidence Gate 反证步骤应改为两步：独立上下文先形成"该结论应该需要
   什么证据/什么会推翻它"，再与实际证据比对**。
4. **CoVe (Chain-of-Verification)** · 2023-09/Meta · arXiv:2309.11495（线索）
   — 降低长文本幻觉 → 草稿→验证问题→**隔离上下文独立回答**→修订 → 列表
   QA/长文生成降低幻觉（数字未核实） → 成本高 → **factorized verification
   是 env_independent 字段的理论依据：隔离是自验证变真检查的关键**。
5. **SelfCheckGPT** · 2023-03/EMNLP 2023 Findings · arXiv:2303.08896 ✅ —
   黑盒幻觉检测 → 多次采样一致性 → 采样间矛盾预测幻觉 → 只测事实性虚构
   → **把验证操作化为可机械比对的行为——语义熵的前身**。
6. **FActScore** · 2023-05/EMNLP 2023 · arXiv:2305.14251（线索） — 长文本
   事实精度 → 分解 atomic facts→对 Wikipedia 逐条判定→聚合占比 → 与人类
   判断相关优于整体性指标 → 依赖知识源覆盖、管线自身有噪声 → **"分解→逐
   条→聚合"是 Evidence Gate 结论级检查的升级模板**。
7. **SAFE / Long-form Factuality** · 2024-03/NeurIPS 2024 · Google DeepMind
   · arXiv:2403.18802 ✅ — 长回答事实性自动评估 → 拆事实→多步搜索推理判
   定→F1@K → 与人类一致 72%；100 分歧抽样中 76% SAFE 胜；比人工便宜 20 倍
   → 检索覆盖依赖、单 judge → **检索交叉验证式 entailment 是可行且性价比
   高的 PASS 通道；分歧仲裁抽样是实用质检手段**。
8. **Decomposition Dilemmas** · 2024-10/NAACL 2025 Main · arXiv:2411.02400
   ✅ — 分解到底提升还是拖累核查 → 错误分类体系+系统实验 → **准确性收益
   与分解噪声存在权衡**，解释文献互相矛盾 → 定性结论 → **只对复合结论分
   解；分解本身要过质量闸（完整性/忠实性）**。
9. **Evaluating Verifiability in Generative Search Engines** · 2023/
   EMNLP 2023 Findings · Stanford · ✅ — 引用真的支持陈述吗 → citation
   recall/precision 人工评估 → **仅 51.5% 句子被完全支持；74.5% 引用支持
   对应句** → 2023 年代系统 → **"锚点存在"检查必须升级为 recall+precision
   双指标**。
10. **SourceCheckup** · 2025/Nature Communications 16:3615 · Stanford（Wu,
    Zou 等）✅ — 医学 LLM 引用质量 → 拆句+下载 URL 内容+GPT-4o 逐对判定，
    5.8 万对 → **50–90% 回答未被完全支持；最佳模型仍 ~30% 语句无支持；无
    联网模型有效 URL 仅 40–70%** → 医学域、判定器为 GPT-4o → **锚点核查
    三段式（有效性→抓取→逐句判定）的现实必要性与可行性证明**。
11. **MiniCheck + LLM-AggreFact** · 2024 · arXiv:2404.10774（线索） — 蕴含
    判定太贵 → 合成数据训练小专用验证器 → GPT-4 级准确率、~400 倍便宜 →
    逐句二元、多跳弱 → **gate 的蕴含初筛不必用大 LLM；可疑项再升级复核**。
12. **引用忠实性 verifier 审计 + conformal 上界** · 2026-07 ·
    arXiv:2607.20527 ✅（摘要） — 审计检查器本身 → 金标锚定评估+split-
    conformal 上界 → **unsupported 率随 verifier 严格度 3%–18% 波动；
    verifier 间 negative agreement 仅 0.27–0.30** → 科学综合域 → **每个
    gate 结果必须记录判定器身份与协议；单 verifier 判定不可作为 PASS 依据
    （高风险）**。
13. **Let's Verify Step by Step** · 2023-05/ICLR 2024 · OpenAI ·
    arXiv:2305.20050 ✅（线索） — 过程 vs 结果监督 → PRM800K 人工步骤标注
    → 过程监督显著优；ORM 奖励"答案对推理错" → 标注极贵、仅数学 → **只闸
    结论不够：结果正确可能掩盖过程错误；但需要自动化过程判据**。
14. **AgentPRM** · 2025-02 · Cornell · arXiv:2502.10325 ✅（摘要） — PRM 搬
    到 agent 轨迹 → MC rollout 估计每步价值 → 3B+AgentPRM 超 GPT-4o 基线
    （ALFWorld）；InversePRM 从演示学习 → 依赖可仿真环境 → **agent 每个决
    策点挂过程评分可行；历史成功轨迹可沉淀 gate 规则**。
15. **AgentAbstain** · 2026-07 · UChicago/ISI 等 · arXiv:2607.10059 ✅（摘
    要） — agent 知道何时不该行动吗 → 42 沙盒/263 配对任务/17 模型 → **最
    强模型配对正确率 59.5%；拒答能力与通用能力不相关；存在"先行动后拒答"
    失效** → 基准≠部署 → **闸门必须前移到不可逆动作之前（pre-execution）；
    不能指望模型自发校准**。
16. **Can Language Models Falsify? (REFUTE)** · 2025-02 · Sinha, Goel,
    Geiping 等 · arXiv:2502.19414 ✅ — LLM 能否证伪 → 为错误解法生成反例、
    代码执行自动判定 → **最强 agent 有效反例率 <9%（同题解题 ~48%）** →
    算法/代码域 → **反证步骤不能依赖裸生成；反例优先走执行/检索等可自动检
    验通道，且预期命中率低**。
17. **POPPER** · 2025-02 · Stanford（Huang, Jin, Candès, Leskovec 等）·
    arXiv:2502.09858 / github.com/snap-stanford/POPPER ✅（项目页） — 假设
    的统计严格自动验证 → 序贯证伪实验+E-value 错误控制 → 6 域；错误控制稳
    健；复杂生物假设验证与人类相当且快 10 倍 → 依赖可测推论 → **"证伪优先"
    的成熟形态=可执行证伪实验+统计错误控制，而非修辞性自问；P2 目标**。
18. **Anthropic × Theorem 形式化验证** · 2026-10 · Anthropic ·
    anthropic.com/research/formal-verification ✅（原文） — agent 规模化产
    出机器检查证明 → Claude 在 RISC-V 汇编层写 Rocq、Verus 证 Rust CPython
    → 1.8 亿行 Rocq；239 个 fuzz 入口证明 crash-free；发现数百 bug → **官
    方三点警告：形式验证≠无 bug；TCB 是假设；agent 会 reward hacking（改源
    码走捷径）需审计** → **机器核查通道的攻击面在"选择验证什么/怎么写
    spec"；闸门需要反取巧审计**。

（其余次相关但被引用支持结论的：Math-Shepherd、OmegaPRM、ProcessBench、
PRM 综述 2510.08049、Kadavath 2022、Xiong 2023、Farquhar Nature 2024、
R-Tuning、Know Your Limits、Conformal LM、STeCa、Khan Debate、Smit MAD、
MAST 2503.13657 ✅、Weaver、Prover-Verifier Games、GenRM、Agent-as-a-Judge、
MLE-bench、τ-bench、METR、AI co-scientist、SPOT、TRUST-SCORE、ALCE、RAGAS、
AIS、AlphaProof、Vero、PC³、nl2postcond、CSV/VICTOR 预算分配线、evidence
graph 线——详见 §2 各方向。）

---

## 4. Evidence Gate 与现有研究的差距

### 4.1 技术对比矩阵

| 能力 | EG 1.0 | A: 分解-验证管线(FActScore/SAFE/MiniCheck) | B: POPPER 证伪式 | C: 过程监督(AgentPRM/PRM) | D: 校准信任(TRUST-SCORE/语义熵/CP) |
|---|---|---|---|---|---|
| Evidence Check | ⚠️ 锚点存在性 | ✅ 逐条对源 | ✅ 实验证据 | ✅ 步骤级 | ⚠️ 置信度侧 |
| Claim Decomposition | ❌ | ✅ 核心 | 部分（推论分解） | ❌ | ❌ |
| Evidence Entailment | ❌ | ✅ 核心 | ✅（实验蕴含） | ❌ | ❌ |
| Counter Evidence | ⚠️ 同上下文自问 | ❌ | ✅ 结构化证伪 | ❌ | ❌ |
| Self Verification | ⚠️ 结构化申报 | 部分（LLM judge） | ✅ 可执行检验 | ❌ | ✅ 采样一致性 |
| Independent Verification | ⚠️ 字段自申报 | 部分（检索独立） | ✅ 与假设独立 | ❌ | ✅ 多采样 |
| Process Verification | ❌ 仅结论 | ❌ | ✅ 序贯 | ✅ 核心 | ⚠️ 步级校准(STeCa) |
| Abstention | ⚠️ VERIFY_REQUIRED 近似 | ❌ | ✅ 拒绝假设 | ❌ | ✅ 核心 |
| Confidence Calibration | ⚠️ 无数据支撑的等级映射 | ❌ | ✅ 统计错误控制 | ❌ | ✅ 核心 |
| Risk-based Verification | ⚠️ 风险分级（无预算分配） | ⚠️ 部分研究有 | 部分 | ❌ | ❌ |
| Formal Verification | ⚠️ 执行验证一档 | ❌ | 部分 | ❌ | ❌ |
| Reproducibility / 审计 | ⚠️ gate result 文本 | ✅ 指标可复算 | ✅ | ⚠️ | ✅ 协议声明 |

### 4.2 已经领先 / 独特的部分

- **结论强度≤证据强度的措辞映射**：未找到任何已发表系统做"措辞上限机械
  化"（文献测的是拒答率/一致率，不控措辞等级）——这是 Evidence Gate 的独
  特贡献，但**无文献直接背书其有效性**（需自建校准数据验证）。
- **部署侧、可移植、零依赖**：相关研究几乎全是评估基准或系统架构（co-
  scientist tournament、Agent-as-a-Judge），做成 agent skill 形态的运行时闸
  门在检索中未见到对应物。
- **假验证模式库**（环境污染/测试不覆盖目标/样本推整体/推理当验证）：与
  MAST"任务验证"失败类、MLE-bench 防作弊设计、Anthropic reward hacking 警
  告高度一致——设计直觉被文献印证。

### 4.3 明显不足 / 关键缺失

1. **无 Evidence Entailment**（最大缺口）：不检查锚点内容是否支持结论
   （§2.3 的全部数字都打在这个缺口上）。
2. **无 Claim Decomposition**：复合结论整体验证，分解噪声与断章取义风险
   未处理，也没有分解质量闸。
3. **无 ABSTAIN**：VERIFY_REQUIRED 是"推迟"，缺"证据不可得→明确拒答并说
   明缺什么"这一档。
4. **反证同上下文生成**：违反 SGV/CoVe 的结构要求，同意偏差下形同虚设。
5. **无过程闸门**：只闸终态；不可逆动作（部署/删除/发送/合并）前无闸门；
   METR/AgentAbstain 证明这是最需要闸的位置。
6. **无校准回路**：L0-L4→正确率映射无数据；gate 决策无稳定性评估
   （pass^k 思想）；无 verifier 身份记录。
7. **无验证预算分配**：风险分级只调"档位"，不按声明级优先级分配成本
   （CSV/VICTOR 线已证明可做）。
8. **机器核查覆盖不足**：URL 有效性、文件内容、可执行断言都可机械核查而
   未核查（D8 阶梯：执行→PBT→Dafny/Verus→SMT→Lean）。

### 4.4 潜在错误设计（研究证据要求修改）

| 设计 | 研究证据 | 修改方向 |
|---|---|---|
| 自申报 JSON 作为主要证据来源 | Huang 2024；Panickssery 2024；64.5% 盲区；SGV | 降级为"线索"：凡可机械核查的字段（URL/文件/执行）必须工具核查 |
| 反证在同一上下文生成 | SGV（偏差对算力有韧性）；CoVe | 两步隔离：先独立生成"需要什么证据/什么会推翻"，再比对 |
| L4=两个自申报独立组 | Weaver（同源弱验证器无效）；多源相关错误 | L4 需操作化独立性：不同工具/不同模型/采样一致性（语义熵） |
| "已验证"基于单次执行+单判定 | verifier 审计（agreement 0.27–0.30） | 记录 verifier 身份；高风险结论双通道判定，分歧即降级 |
| 单一结论闸门 | Lightman 2024；AgentAbstain；METR | 双层：过程闸门（转换点/不可逆前）+ 结果闸门兜底 |
| 措辞映射无校准数据 | Xiong 2023（绝对值不可信） | 日志回流 + conformal 校准措辞阈值 |

---

## 5. Evidence Gate 2.0 架构

```
输入（结论草稿 + 任务轨迹）
  ↓
[0] 机器核查通道分流（claim class routing）
    可执行类（代码行为/文件内容/URL/数值）→ 执行/PBT/SMT 断言（机械判定）
    可检索类（事实/文档）→ 检索通道
    不可形式化类（建议/判断）→ 语言判定通道
  ↓
[1] Claim Extraction & Decomposition
    仅复合结论分解为 atomic claims；分解质量闸（Completeness/忠实性）
  ↓
[2] Evidence Retrieval & Anchor Resolution
    锚点三段式：有效性（URL 可达/文件存在）→ 抓取实际内容 → 登记
  ↓
[3] Evidence → Claim Entailment
    小模型初筛（MiniCheck 式）+ LLM judge 复核；双通道分歧 → 降级；
    输出 per-claim support(recall/precision)
  ↓
[4] Independent Counter-Evidence（SGV 两步）
    隔离上下文先独立生成"该结论需要什么证据/什么会推翻它"，再与实际
    证据比对；反例优先走可执行/可检索通道（预期命中率低，REFUTE）
  ↓
[5] Risk Assessment & Verification Budget
    声明级风险评分 → 分配验证预算（高风险声明优先；低风险快速通道）
  ↓
[6] Actual Verification（执行优先）
    干净环境 + 先复现后验证 + 反取巧审计（惩罚平凡通过）
  ↓
[7] Confidence Calibration
    等级=序数；L4 操作化为采样一致性或异源独立线；
    措辞阈值由历史"等级-结果"日志 conformal 校准
  ↓
[8] Final Verdict：PASS / PASS_WITH_CAVEAT / ABSTAIN / REJECT
    （ABSTAIN=证据不可得时不输出结论，说明缺口；VERIFY_REQUIRED 变为
     内部循环态：降级或验证后重入）
  ↓
[9] 审计记录：verifier 身份/协议/阈值/决策 + 结果追踪
```

**过程闸门（与结论闸门并行，双层结构）**：

- G1 假设→证据计划：计划收集的证据能否区分备择假设（防确认偏误）
- G2 观察→假设修改：修改是否有新证据直接支持
- G3 不可逆动作前：部署/删除/发送/合并/对外发布——AgentAbstain 失效模式
  的直接对策
- 结果闸门（上文 [1]-[9]）兜底，防过程闸门被"长得像可验证"的步骤 hack

**模块分期**：第一阶段必须=[0 分流][2 锚点三段式][4 隔离反证][8 ABSTAIN]
[9 审计]；第二阶段=[1 分解+质量闸][3 双通道蕴含][5 预算分配][过程闸门
G1-G3]；长期=[6 统计错误控制(POPPER 式)][7 conformal 措辞保证][形式化后端
(Lean/Dafny)][多验证器弱监督集成(Weaver 式)]。

---

## 6. 优先级路线图

### P0：立即改（高价值、低成本、证据充分）

1. **锚点三段式核查**（有效性→抓取→逐条蕴含判定）。关闭最大缺口；判定可
   先用现有 LLM judge、后换小模型。依据：51.5% / 50–90% / ~30% 三组数字。
2. **反证步骤改 SGV 两步隔离**：先在不含结论的上下文生成"证据需求+推翻
   条件"，再比对。纯提示结构改动。依据：同意偏差对算力有韧性。
3. **ABSTAIN 一等决策**：证据不可得→"无法确认+缺口清单"，与 VERIFY_REQUIRED
   （可补验证）、REJECT（证伪）三态分离。依据：R-Tuning/TRUST-SCORE/
   AgentAbstain。
4. **不可逆动作前置闸门 G3**：对齐现有 gate 脚本的输入接口。依据：
   AgentAbstain"先行动后拒答"失效。
5. **闸门审计日志与校准回路**：记录 verifier 身份/协议/阈值；结果事后回
   流；绘制 risk-coverage 曲线验证 L0-L4 单调性。依据：verifier 审计
   （agreement 0.27–0.30）；Xiong（绝对映射不可信）。

### P1：中期增强

- 复合结论的 claim decomposition + 分解质量闸（Completeness/忠实性）
- 声明级验证预算分配（风险优先级评分；低风险快速通道防过度验证）
- 蕴含判定双通道（小模型初筛 + LLM judge），分歧即降级
- 过程闸门 G1/G2（假设→证据计划、观察→假设修改）
- L4 操作化：采样一致性（语义熵式）或异源独立线（不同模型/工具）
- gate 决策稳定性（pass^k 式重复一致率）纳入测试

### P2：前沿研究（不成熟但潜力大）

- POPPER 式序贯证伪 + 统计错误控制（E-value）用于高风险假设类结论
- conformal 校准的措辞阈值（"已验证"档附带可检验错误率上界）
- 机器核查阶梯升级：PBT→Dafny/Verus→SMT→Lean 后端；"proof"级证据档
- 多验证器弱监督集成（Weaver 式，87.7% 实证）
- 跨模型独立对抗 agent（debate），以 self-consistency 为基线证明净增益，
  配防从众协议（Smit/MAST 警示）
- spec 审计：谁验证"验证规约本身"（nl2postcond 瓶颈 + Anthropic 反取巧）

---

## 7. 最终结论

**如果目标是让 Agent 的每一个重要结论都尽可能真实、可靠、可验证，Evidence
Gate 最应该改的不是加更多规则，而是把"信任的语言层"降级为"信任的机械层"：**

1. EG 1.0 的定位（部署侧、结论前、措辞与证据强度挂钩的运行时闸门）在检索
   范围内**没有直接竞品**——这是它的价值，也意味着它必须自己补上文献已经
   解决的零件：蕴含核查、隔离反证、ABSTAIN、审计校准。
2. 研究一致指向的终局形态是：**LM 只负责提议（结论、规约、反例候选），
   判定权尽量交给确定性 checker（执行、检索内容比对、NLI/判定器、证明
   器）**；语言判定只兜底不可形式化的部分，且必须声明判定器身份。
3. 单点闸门不够：**过程闸门（转换点+不可逆前）+ 结果闸门兜底**的双层结构
   是文献（过程监督×agent 失效模式）共同指向的形态。
4. 最后一条是自我适用的：本报告对 EG 1.0 的每一项"保留"判断，也应该被
   校准回路检验——**闸门自己的等级映射同样需要"结论强度≤证据强度"**；
   当前它只有理论论证，没有结果数据。

---

## 附：研究可信度声明

- 主线亲自核实：Huang et al. ICLR 2024（arXiv:2310.01798）、MAST
  （arXiv:2503.13657，标题/作者/14 失败模式/kappa 0.88 均核对）。
- 代理核实（WebFetch 摘要页/原文，标 ✅）：SGV、SAFE、SourceCheckup、
  AgentAbstain、AgentPRM、PRM 综述、verifier 审计、Decomposition
  Dilemmas、DecMetrics、Judge's Verdict、Panickssery、Wataoka、语义熵、
  R-Tuning、Khan Debate、Smit MAD、REFUTE、POPPER、Weaver、Debate 2018、
  Agent-as-a-Judge、MLE-bench、METR、AI co-scientist、AlphaProof、
  Anthropic×Theorem、Shefer、CoVe、SelfCheckGPT、Stanford Verifiability、
  ALCE、AIS、RAGAS、Lightman。
- 仅搜索结果未见原文（标"未核实"，结论中仅作旁证不作承重）：Self-
  Correction Bench 64.5%、FLAN-T5-11B 最佳 verifier、judge 一致率 85%/74%、
  OmegaPRM 51%→69%、deep research 引用幻觉 10.7%、Goedel-Prover 84.6%、
  TRUST-SCORE、GenRM、STeCa、SPOT、CSV/VICTOR 细节、evidence graph 线各篇。
- 明确未找到可靠证据：(a) "verifier engineering" 并非 DeepMind 博客——出
  自 Guan et al. arXiv:2411.11504（2024-11 立场论文，未核实原文）；
  (b) LLM-judge 可靠性的严格元分析；(c) 证据分级（evidence hierarchy/GRADE
  式）用于 LLM agent 输出控制的直接先例；(d) 任意 NL 断言全自动形式化并端
  到端核验的通用系统。
