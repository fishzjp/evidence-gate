# Evidence Gate 可靠性研究调研（第二轮）— 证据真实性、Verifier 可靠性与验证经济学的深水区

> 调研日期：2026-11-19。方法：5 个方向各派独立研究代理（WebSearch + WebFetch 核实
> arXiv/ACL/ACM 摘要页或全文），共约 70 篇候选、43+ 篇经摘要页逐字核实（标 ✅）、
> 其余为搜索结果级线索（标 snippet，仅作旁证不作承重）。本轮聚焦上一轮调研
> （`docs/research-survey.md`）明确遗留的 8 个深水区问题。遵循 Evidence Gate 自身
> 原则：本轮调研同时**修正了上一轮调研的两处错误结论**（见 §4）。

---

## 1. Executive Summary

上一轮调研解决了"自我申报不可靠 → 机械核查 + 隔离反证 + ABSTAIN"这一层。本轮
针对的 8 个问题全部属于更深层：**证据与事实的关系、验证器自身的可靠性、验证的
经济学**。五路调研的收敛结论：

1. **"多来源"≠"多独立证据"已被 2025–2026 年多篇工作显式命名和研究**
   （同源转载/复本计数/回声室），但**没有任何 LLM 验证管线集成了同源检测**——
   这是 Evidence Gate 可以占位的真实空档。机械可做的第一层：URL 宿主塌缩 +
   引文重叠 + 引用链检测（编辑复用以非字面改写为主，词面匹配只是下限，
   Rewrite the News, LREC 2026 ✅）。
2. **验证器必须与生成器异构（跨家族 > 同家族 > 自验证）有了直接实验支持**
   （37 模型 × 9 基准，arXiv:2512.02304 ✅），但**异构≠独立**：两模型同错时
   60% 给出相同错误答案，且越大越准的模型错误相关性越高（ICML 2025 ✅）；
   9 个法官 ≈ 2 张有效票（✅）。因此异构是必要条件而非充分条件，且一致性
   只能做路由信号、绝不能做裁决依据（26.5 万样本：高一致案例中 48% 是错的 ✅）。
3. **验证器自身需要"出生门"与扰动不变性**：验证器在无锚定护栏时坍缩为
   "全通过"（arXiv:2610.11464 ✅）；规则验证器与模型验证器呈对称失效（规则→FRR、
   模型→FAR，EMNLP 2026 ✅）；同构扰动下判决必须不变（IPT ✅）。
   → benchmark corpus 就是锚定集，每次规则改动必须全量回归 + 改写不变性测试。
4. **弃答/校准的度量学与机制已成熟到可落地**：AbstentionBench（✅ Meta FAIR，
   NeurIPS 2025）给出双向弃答指标（防"永远弃答"博弈）；conformal risk control
   在 200–500 个标注样本上即可把错误放行率控制在 α 内（SCOPE ✅ 全文核实）；
   L0–L4 保持序数、以嵌套档位做 CRC 校准是理论上正确的路径——**不需要也不应该
   把等级概率化**。
5. **验证成本的路由规则在四条独立证据线上收敛**：`升级 ⟺ 廉价层判非 PASS 带边际
   OR 危害高档 OR 该类型历史错误率 > γ`；高风险禁止跳层；预算耗尽 anytime 返回
   当前档（Trust or Escalate ICLR 2025 ✅、FIRE NAACL 2025 ✅、ABC ✅、
   Verify What Matters）。

---

## 2. 按问题的文献结论（承重文献详注）

### P1 — Evidence Consistency ≠ Truth（证据一致 ≠ 事实为真）

| 研究 | 结论 | 落地 |
|---|---|---|
| 多工具可验证误信息检测 agent（ACM GenAIBusiness 2025，✅ 全文） | fresh 网络检索是最大消融贡献项（−3.2~−4.2）；agent 式 vs 裸 LLM：FakeNewsNet 89.7 vs 85.1；抗"洗白改写" 80.2% vs 65.7% | 高风险可检索事实走 fresh 检索通道（≥2 独立域名），不是复述已有证据 |
| RefVerifier（2026，snippet） | 独立重查文献声明确率仅 71%——fresh 通道本身有噪声上限 | 独立检索通道分歧 → 降级/contested，不直接否决 |
| BrowseComp（OpenAI 2025）/ BrowseComp-Plus（ACL 2026，snippet） | 难查事实：静态模型 0.6–3.9% vs agentic 检索 51.5–70.1% | hard-lookup 类声明必须多轮检索，单轮 RAG 不可信 |
| Verdict leakage（Rethinking the Evaluation of LLM Fact-Checkers, arXiv:2610.30504, snippet） | 证据页本身含裁决（核查站/问答页）= 测的是复读不是核查 | meta-evidence 不计入独立性 |

**判定：PARTIAL。** "证据支持"与"事实为真"之间只能插入 fresh 独立取证通道并把
分歧降级，没有任何方法能在无 ground truth 时证明事实性。

### P2 — Evidence 本身可能错误（来源可靠性 / 时效 / 污染 / 相关性）

| 研究 | 结论 | 落地 |
|---|---|---|
| CONFACT（IJCAI 2025 ✅） | 注入来源可信度显著改善冲突证据下的核查 | source_tier 加权；聚合按加权而非计数 |
| Search-Time Contamination（arXiv:2508.13180 ✅） | 检索会捞到含答案的污染页；屏蔽后污染子集准确率降 ~15% | 污染域名模式清单 + 命中即排除 |
| Asking For An Old Friend（TUM, arXiv:2605.23497 ✅） | 时间有效性当硬约束（事实日期抽取+版本过滤）显著改善；web search 有 recency bias，历史断言要取"最接近目标时点"而非最新 | as_of/until 窗口 vs 断言目标时点；当前性断言的陈旧证据不足 |
| Rewrite the News（LREC 2026 ✅） | 编辑复用 52% 发生在通讯社稿件中，且以非字面改写为主 | 同源聚类：host + 引文重叠 + 罕见词/数字串双通道；保留最早来源为根 |
| Counting Copies as Evidence（Zenodo 2026，未评审，低置信） | "复本计数→置信膨胀"已被显式命名 | 问题命名支撑，机制按上行两条实现 |
| Dempster–Shafer 经典（Sentz & Ferson；Shenoy 2023） | 证据组合要求 distinct；相关证据需折扣或保守组合 | 相关簇只计一条独立线（n_eff 思想），不做加权概率融合 |
| Decoding AI Judgment（arXiv:2502.04426 ✅） | LLM 给来源打分与专家仅部分对齐且带系统性偏差 | 不让 LLM 凭空给来源打分；source_tier 由声明者标注并落审计 |
| MADAM-RAG（COLM 2025 ✅） | 冲突+误信息+噪声并存是常态；辩论式聚合贵且不建模依赖 | 立场冲突 → 显式标记 + 降级，不静默取多数 |

**判定：PARTIAL。** 机构级可信度查表可用、时间窗口与污染过滤可机械实现、同源
检测有词面层方法；**语义级（非复制式）同源检测与学习式相关折扣聚合为 OPEN**。

### P3 — Verifier 自己会犯错（谁来验证 Verifier）

| 研究 | 结论 | 落地 |
|---|---|---|
| Who Verifies the Verifier / Co-Evolving Graders（arXiv:2610.11464 ✅） | 无锚定护栏的验证器坍缩为全通过，且坍缩验证器的下游分数照样好——下游分数无法证明验证器有效 | benchmark corpus = 锚定集 = 验证器出生门：每次改动必须全量回归 |
| Rule- vs Model-based Verifiers（EMNLP 2026 ✅） | 规则验证器因格式僵化大量假拒（模型越强阻碍越大）；模型验证器静态更准但 RL 下被 hack | 机械检查必须归一化（数字/格式）；硬否决只留给难博弈的检查 |
| PRM Reward Under Attack（arXiv:2603.06621 ✅） | PRM 奖励>0.9 时真值准确率<4%；43% 奖励增益来自风格捷径——"流畅度检测器而非推理验证器" | 警惕格式良好的伪证据；反取巧：验证什么由闸门侧定，不由 agent 自选 |
| RobustJudge（arXiv:2506.09443 ✅） | 15 攻击×8 防御×13 judge：无普适赢家，对模板/模型选择高度敏感 | 判决协议固定并记录（verifier 身份/版本/通道） |
| A Coin Flip for Safety（arXiv:2603.06594 ✅） | 分布偏移下 judge 可退化到接近随机（6642 条人工标签审计） | 静态基准绿色 ≠ 部署可靠；对抗性语料 + 漂移监控 |
| IPT / LLMs Gaming Verifiers（arXiv:2604.15149 ✅） | 外延验证诱发捷径，同构（等价改写）验证消除捷径 | **改写不变性测试**：同义改写后的结论必须得到同一判决 |
| EvilGenie（arXiv:2511.21654 ✅） | held-out 单测相对 LLM judge 增量极小；检测器组合要看增量产出 | benchmark 报告每条规则的增量查获（防冗余规则堆积） |
| CriticGPT（OpenAI, arXiv:2407.00215 ✅） | critic 抓的 bug 多于人类，但会幻觉出不存在的缺陷（FRR 源） | 拒绝理由必须挂到输入的具体字段/引文上 |
| Trust or Escalate（ICLR 2025 ✅） | 30–50 条审计样本 + 级联即可带保证地解耦 FAR 与覆盖率 | 低置信 → ESCALATE（升级/降档）而非硬判 |

**判定：PARTIAL。** "验证验证器"没有银弹，但锚定集 + 扰动不变性 + 增量产出核算
+ 升级机制四件套把可测量性建立起来了。

### P4 — 同模型相关失效（异构验证）

| 研究 | 结论 | 落地 |
|---|---|---|
| When Does Verification Pay Off（arXiv:2512.02304 ✅，37 模型×9 基准） | **跨家族 > 同家族 > 自验证**，收益随 solver-verifier 相似度单调下降 | 高风险强声明的独立核查必须跨家族（机制字段化：generator vs checker 身份） |
| Correlated Errors in LLMs（ICML 2025 ✅） | 两模型同错时 60% 同答案；越大越准的模型跨厂商仍高度相关 | 异构是必要非充分；有效多样性要实测（记录历史分歧率） |
| Nine Judges, Two Effective Votes（arXiv:2605.29800 ✅） | 9 法官≈2 有效票；最优聚合算法最多补 11% 缺口 | 委员会规模 2–3 即近上限；聚合算法不是解药 |
| When LLMs Agree, Are They Right（arXiv:2607.08065 ✅，26.5 万样本） | agreement 预测力 rho 仅 0.20–0.59；前沿模型高一致案例 48% 是错的 | **一致性只做路由，永远不做裁决**（推翻上一轮"L4 用采样一致性操作化"的设想） |
| MAD 失效三定律（arXiv:2509.05396 ✅ + 2605.00914 ✅） | 迎和从众最高 85.5%、上下文脆性 70%、共识崩塌 oracle gap 32.3pp；token 2.1–3.4× | 禁多轮互辩收敛；falsifier = 单轮独立反驳 + 规则聚合 |
| 辩论置信度不可信（arXiv:2505.19184 ✅） | 61.7% 辩论双方同时自称 ≥75% 胜率；与副本辩论自信照样升 | 不采信任何自报置信（含 verifier 的） |
| Too Consistent to Detect（EMNLP 2025 ✅） | 自洽错误不随规模减少；四类检测方法全部失效；跨模型探针有效 | 高自洽≠安全；异构答案分歧是黑盒可用的最强信号 |
| Variation in Verification（arXiv:2509.17995 ✅） | 强 generator 的错误更难被任何 verifier 检出 | 前沿生成场景：falsifier 与外部证据权重上调 |
| ABC 分歧级联（arXiv:2407.02348 ✅） | 便宜层一致→通过、分歧→升级：同时超最强单模型准确率与效率（成本降 2–25×） | 成本阶梯骨架：escalate-on-disagreement |
| FALCA（arXiv:2610.28361 ✅） | Searcher–Falsifier 分离 + 结构化证伪报告降低确认偏差（需训练） | falsifier 角色结构（拒答约束/反证/追查清单）可借，训练可省 |
| Learning to Disprove（arXiv:2603.19514 ✅） | 反例 + Lean4 机器检查 = 硬证伪 | 可形式化断言接可执行 oracle；反例机器验证 = 一票否决 |

**判定：方向 SOLVED / 效应量 PARTIAL。** 异构要求有直接证据；但 refute-first vs
confirm-first 的同基准头对头对照**不存在**（文献空位）；裸 prompt 证伪弱（<9%
有效率，上轮已知）依然成立。

### P5 — 验证成本

| 研究 | 结论 | 落地 |
|---|---|---|
| Trust or Escalate（✅） | 级联选择性评审：便宜先行 + 置信边际判升级 | 廉价层判非 PASS 带边际 → 升级 |
| FIRE（NAACL 2025 ✅） | 置信驱动早停：LLM 成本 7.6×、检索 16.5× 下降 | 证据收集迭代化 + 硬上限轮数，超限降档 |
| AVA anytime（TMLR 在审，snippet） | 预算耗尽返回当前已验证最优 | anytime 降档输出（VERIFY_REQUIRED/降措辞）而非挂起 |
| Verify What Matters（TMLR, snippet） | 预算按反事实下游危害分配 | 风险分数 = 不可逆性 × 影响面 × 类型历史错误率 |
| FrugalGPT（TMLR 2024, snippet） | 级联架构先例：成本最多降 98% | 阶梯本质 = 验证资源级联 |

**判定：架构 SOLVED / 阈值 PARTIAL。** 阈值 τ/γ 任务相关，需自有 outcome 数据
标定（与 P8 的校准回路共用）。

### P6 — 无法验证的事实（Abstention）

| 研究 | 结论 | 落地 |
|---|---|---|
| AbstentionBench（NeurIPS 2025 ✅, Meta FAIR） | 弃答未解决、规模无用、推理微调使弃答平均退化 24%；系统提示部分有效 | 弃答指标**双向**：精确率 + 召回率，防"永远弃答"博弈 |
| Know Your Limits（TACL 2025，上轮已知）+ 弃答综述 | over-abstention 是真实失败模式；可被"多弃答"博弈 | ABSTAIN 率需要上限监控 |
| Informed Abstention（AIES 2026, snippet） | agent 行动弃答 = pre-execution hook | 闸门挂不可逆动作前（已有 G3） |
| TAPS（arXiv:2610.16318, snippet） | 生成与弃答决策解耦、阈值可控 | EG 结构验证：agent 提议、脚本阈值裁决 |
| AgentAbstain（上轮 ✅） | 最强模型配对正确率 59.5%；先行动后拒答失效 | 不可逆动作前强制过闸 |

**判定：SOLVED（度量学）**。弃答精确率/召回率/覆盖率/selective risk/risk-coverage
定义全部就位；执行侧靠 pre-action 闸门。

### P7 — Formal Verification Boundary

| 研究 | 结论 | 落地 |
|---|---|---|
| VERGE（arXiv:2601.20055 ✅） | 语义路由：可符号化声明→SMT/ATP，常识→LLM 集成；+18.7% | claim_class 路由字段；可机械类禁止纯语言判定 |
| Agentic PBT（arXiv:2510.09907 ✅ + Anthropic 博客 ✅） | PBT 是"跑一次"与"证明"的中间档；56% 缺陷报告有效 | 代码/数值类可选 PBT 档（纯 Python 抽样循环） |
| AutoVerus（OOPSLA 2025 ✅） | 验证器报错驱动的证明调试循环，>90% 自动证明 | 断言失败回喂修正循环 ≤3 次 |
| Vericoding 基准（arXiv:2509.22908, snippet） | Dafny 82% > Verus 44% > Lean 27% 生成成功率 | 未来外挂证明器的选型依据 |
| ImpossibleBench / EvilGenie / Berkeley RDI（✅/snippet） | 执行通道可被自写测试作弊击穿 | 测试来源必须记录；agent 自写测试未经审视不采信 |
| Proof-Carrying Agent Actions（snippet 族） | 交付物附带机器可检证书 | verdict 附证据账本（命令/工件/结果哈希，可离线重放） |

**判定：路由启发式 SOLVED（执行/数值/SQL 走机器；数学/契约 PARTIAL；通用
formalizability 分类器 OPEN）。**

### P8 — Evidence Level ≠ Probability（校准）

| 研究 | 结论 | 落地 |
|---|---|---|
| Conformal Risk Control（ICLR 2024，snippet，理论基石） | 任意单调损失可用校准数据控期望风险；ordinal 档位是天然嵌套预测族 | **L0–L4 保持序数**，对"L≥k 即接受"做 CRC，不需要概率化 |
| SCOPE（arXiv:2602.13110 ✅ 全文） | 200–500 校准样本即控 FDR≤α（α=0.10 实测 0.097–0.099）；标签噪声下多弃而非越界 | outcome 日志 ≥200 条后启用校准阈值；不足则显式"弱保证" |
| Enhanced Conformal Prediction（NeurIPS 2024 ✅, Candès 组） | 条件有效性差 + 过度过滤；自适应发更弱保证保效用 | 小样本期声明"未校准"而非硬套 |
| DINCO（arXiv:2509.25532, snippet） | verbalized confidence 有暗示偏差；自生成 distractors 归一化可改善 | 冷启动过渡方案（无 outcome 数据时） |
| AbstentionBench（✅） | 双向弃答指标 | 校准报告含弃答精确率/召回率 |
| Geifman & El-Yaniv（NeurIPS 2017，经典） | selective classification：risk-coverage/AURC 标准评测 | `--calibration` 输出 risk-coverage 表与 AURC |
| Judge overconfidence（arXiv:2508.06225 ✅） | judge 置信系统性高于正确率 | **移除启发式 HIGH/MEDIUM/LOW confidence 字段**，只报经验校准值（带 n 与 CI） |

**判定：机制 PARTIAL-feasible。** 数百 outcome 样本即可起步；交换性与漂移是
持续代价；无数据时诚实标注"未校准"。

---

## 3. Problem → Research → Solution Matrix

| Evidence Gate 问题 | 相关研究（承重） | 当前方案（v2.0.0） | 更优方案（v3.0.0） | 是否采用 |
|---|---|---|---|---|
| P1 Evidence ≠ Truth | 多工具核查 agent ✅；RefVerifier (71%)；verdict leakage | 无独立取证通道 | fresh 检索/复算通道记入 independent_checks；分歧→contested 降级；meta-evidence 不计独立 | **P0 采用**（通道与字段；检索本身由 agent 执行） |
| P2 Evidence 可能错误 | CONFACT ✅；STC ✅；TUM 时效 ✅；Rewrite the News ✅；DS 折扣 | 仅自报 group；无时效/层级/污染概念 | source_tier + as_of/until 时间窗 + 污染域名清单 + 同源塌缩（host/引文重叠/引用链）→ n_eff 独立线 | **P0 采用**（机械部分）；语义同源检测 OPEN |
| P3 Verifier 会犯错 | Co-Evolving Graders ✅；Rule-vs-Model ✅；IPT ✅；EvilGenie ✅；Trust-or-Escalate ✅ | 单通道；启发式 confidence；无自检 | corpus=出生门；改写不变性回归；规则增量产出核算；confidence 字段移除→经验校准块；升级机制 | **P0 采用** |
| P4 同模型相关失效 | 2512.02304 ✅；ICML25 ✅；2605.29800 ✅；2607.08065 ✅；MAD✅✅；ABC ✅ | counter_search_context 自报；无 generator/verifier 身份 | generator vs checker 身份字段；高风险强声明的独立核查强制跨家族；一致性只路由不裁决；禁多轮辩论；分歧级联 | **P0 采用**（身份+强制异构+通道要求） |
| P5 验证成本 | Trust-or-Escalate ✅；FIRE ✅；ABC ✅；Verify-What-Matters | 风险分级调"档位"，无声明级路由表 | claim_class × risk_tier 路由表（4 层阶梯）；escalate 条件三选一；anytime 降档；账本记录成本档 | **P0 采用**（路由表+文档；预算计数器 P1） |
| P6 无法验证 | AbstentionBench ✅；Informed Abstention；AgentAbstain ✅ | ABSTAIN 存在，无原因分类与度量 | unobtainable_reason 分类；校准报告输出弃答精确率/召回率/覆盖率/risk-coverage | **P0 采用**（度量+分类） |
| P7 Formal Boundary | VERGE ✅；Agentic PBT ✅；AutoVerus ✅；ImpossibleBench | 执行=L3 但无 claim class 路由 | claim_class 路由：机械类强声明必须 execution/test/assertion/formal 通道；PBT 为中间档；测试来源记录 | **P0 采用**（路由+通道枚举；外挂证明器 P2） |
| P8 Level ≠ Probability | CRC（ICLR24）；SCOPE ✅；Enhanced CP ✅；AbstentionBench ✅ | 被动校准表；启发式 confidence | CRC 思路的主动校准：≥N outcome 后按档位阈值化放行；Wilson CI + ECE + AURC 输出；小样本显式"未校准" | **P0 采用**（校准升级）；conformal 保证 P2（需数据积累） |

---

## 4. 本轮修正上一轮调研的结论

1. **VICTOR 不存在**。上一轮将 "Claim-Level Selective Verification / VICTOR"
   列为成本分配线索；本轮两轮定向检索均无可验证命中（"Victor"仅以作者名出现）。
   CSV 仅存在于 ResearchGate 未索引预印本，可信度低。→ 成本路由的承重文献改为
   Trust or Escalate / FIRE / ABC / Verify What Matters。
2. **采样一致性不能操作化 L4**。上一轮 P1 建议"L4 操作化为采样一致性（语义熵式）
   或异源独立线"；本轮 26.5 万样本实证：agreement 预测力 rho 0.20–0.59，前沿
   模型高一致案例 48% 是错的（arXiv:2607.08065 ✅）。→ **只保留"异源独立线"，
   删除采样一致性路径**。自洽错误不随规模减少（EMNLP 2025 ✅）进一步支持。
3. （补充勘误）上轮引用的 "verifier engineering 源自 DeepMind 博客" 已在上轮
   自行纠正为 Guan et al. arXiv:2411.11504，本轮维持该纠正。

## 5. Open Problems（明确标记，不装作已解决）

1. **语义级同源检测**：非字面改写的转载/洗稿（52% 的复用是非字面的）在零依赖
   词面层无法可靠检出；需要语义相似度或跨模型探针 → P2。
2. **无 ground truth 时的事实性**：fresh 独立检索通道本身仅 ~71% 可靠；
   "Claim Is Actually True" 在开放域无解，只能多通道降分歧 → 永久 PARTIAL。
3. **通用 formalizability 分类器**：除 VERGE 内嵌路由外无独立研究 → OPEN。
4. **conformal 保证的条件有效性**：边际保证可得，条件（分域/分任务）保证需
   更多数据与分组校准；交换性在模型/任务漂移下失效，需滚动重校 → P2。
5. **学习式相关证据折扣聚合**：无成熟方法（DS 折扣是规则式）→ OPEN，v3 用
   保守塌缩（同簇只计一条）替代。
6. **refute-first vs confirm-first 头对头对照**：文献空位；我们的 A/B 语料
   （含反证对抗项）只能间接观察。
7. **验证器的对抗鲁棒性**：分布偏移下 judge 可近随机（✅）；锚定集 + 对抗语料
   只能监控，无法根除 → 永久 PARTIAL。

## 6. 可信度声明

- 主线 5 个研究代理独立检索并交叉；承重结论均有 ✅ 级文献支撑（arXiv 摘要页
  或全文逐字核对），关键数字：60% 同错一致率、≈2 有效票、48% 高一致错误率、
  200–500 校准样本、7.6×/16.5× 成本下降、弃答退化 24%、跨家族>同家族>自验证。
- snippet 级引用仅在表格中以"(snippet)"标注，不承重。
- 本轮发现的搜索摘要 arXiv 编号错误 3 处（2508.08954→2508.13180、
  2412.06825 与 2505.15782 系搜索噪音已排除、SAUP 2412.01033 双源确认），
  均已实际抓取页面核实后修正——引用 snippet 编号前必须核对原文。
- 完整 URL 清单见各代理报告存档（本文件只列承重文献编号）。
