# Architecture

Evidence Gate 的判定管线。核心设计原则来自一个经过验证的分工：
**LM 提议，确定性检查器裁决**（AlphaProof / Anthropic×Theorem 路线；也继承了
其警告 —— 奖励可被 hack，所以机械核查不信任自报字段）。Agent 负责填结构化
输入（证据、锚点、验证状态），脚本负责算术与机械核查，二者职责不重叠。

## 管线总览

```
Agent 侧（判断性）                    脚本侧（确定性，scripts/gate_check.py）
══════════════════                    ══════════════════════════════════════
Task
  ↓
Claim Extraction                      load_input / schema 校验
  ↓ 提取将要输出的结论                   （缺字段/非法枚举 → exit 2）
Claim Classification + 路由
  ↓ FACT | INFERENCE | HYPOTHESIS
  │  | RECOMMENDATION | EXPERIMENT_RESULT
  │  + claim_class（机械可判类→机械通道）
Verification (verify-first, 按通道)
  ↓ 能执行就执行；执行是 L3 的唯一来源
Evidence Collection + 溯源
  ↓ 每条带锚点+引文+as_of+来源层级       ┌─ G3 pre-action 升档（--gate-point）
Counter-Evidence (isolated search)    ├─ 文本扫描：绝对化/因果/works/风险关键词
  ↓                                    ├─ 锚点三段式机械核查 ─────────────┐
Independent Check（异构：跨家族/工具）  ├─ 验证有效性（executed×env×target×channel）
  ↓                                    ├─ 通道路由（机械类声明×机械通道）  │
Gate input (JSON) ──────────────────→  ├─ 数字一致性（结论数字∈引文数字）  │
                                       ├─ 时间有效性（as_of/until×claim_time）│
                                       ├─ 同源塌缩（组/宿主/Jaccard/引用链）│
                                       ├─ 异构核查（generator×检查者家族） │
                                       ├─ 证据等级 L0–L4 推导（塌缩后）     │
                                       ├─ 所需等级 vs 实际等级             │
                                       ├─ 反证状态 + 隔离要求              │
                                       ├─ 样本→总体拦截                    │
                                       ├─ 决策（五类，按序求值）            │
                                       ├─ 账本（ledger，逐线审计）          │
                                       ├─ 审计日志（JSONL, gate_id）       │
Verdict ←──────────────────────────────┘
  ↓ 服从决策（措辞上限/caveat/动作）
Final Answer
```

## 模块明细

### 1. Claim Extraction / Classification（Agent 侧）

- **输入**：任务上下文、草稿结论
- **输出**：`conclusion`（原样文本）+ `type` 五分类
- **职责**：提取真正要出口的那句话；分类决定类型下限（FACT≥L2、
  EXPERIMENT_RESULT≥L3）
- **失败情况**：拆分强声明为多个弱句逃闸（对策：评审按交付物整体信息强度
  过闸，写入 decision-rules.md 边界条款）；结论改写后与闸门输入不同（流程
  约束，脚本无法比较"最终输出"与"过闸结论"）

### 2. 文本扫描（anti-bypass，脚本）

- **输入**：`conclusion` 原文
- **输出**：escalations（absolute / causal / works / risk）
- **职责**：不看自报字段，直接扫文本。`claimed_strength: judged` +
  文本含"100%/全部" → 按 absolute 判定；"可以正常运行/已修复/不会中断"
  → works 声明
- **失败情况**：关键词启发式的边界误报（中文"均匀"曾被"均"误伤，已修为
  `均(?!匀)`）；同义改写可能漏报（漏报的兜底是等级算术 —— 措辞再花哨，
  证据等级不够照样拦）

### 3. 锚点三段式核查（脚本，v2 核心）

- **输入**：`evidence[]` 每条（kind/detail/anchor/quote/content_supports）
- **输出**：逐条判定 `mechanical_ok | attested | partial | trace-only |
  quote_missing | missing | contradicted | unresolved | content_unchecked`
- **职责**：引用存在 ≠ 引用支持。本地文件：打开文件、剥 Markdown 格式符、
  比对引文是否在文中；URL：在线抓取（--offline 时走证明通道）；
  issue-id/commit：trace-only
- **失败情况**：URL 抓取失败且无 content_supports → unresolved（强声明被拦，
  弱声明放行带 finding）；证明通道可被虚报（对策：attested 路径全部落审计
  日志，校准回路事后统计）

### 4. 验证有效性 + 通道路由（脚本）

- **输入**：`verification{executed, env_independent, validates_target,
  channel}` + `claim_class`
- **输出**：valid_execution 布尔 + ENV_CONTAMINATED / TEST_NOT_TARGETED /
  CHANNEL_MISMATCH findings
- **职责**：四个真值同时成立才算有效执行 —— 跑过 × 环境干净 × 测试真的
  覆盖目标 × 通道匹配声明类别。机械可判类（code_behavior/config/data/
  math）声明 `verified`+ 而通道是 reasoning → 执行被作废（CHANNEL_MISMATCH
  → FAKE_VERIFICATION → REJECT）：机器能判的事不由雄辩裁决
- **失败情况**：三项本身是自报的（边界：与 3 同，靠审计+校准）；
  claim_class 是自报的（漏报时走通用通道，不比 v2 更差）

### 5. v3 机械核查四件套（脚本，先于等级推导）

- **数字一致性（MISLEADING_QUOTE）**：结论声称 1–3 个带单位数字 + 全部
  无任何引文/锚点/详情背书（含千分位/尾零归一化与时间单位换算）+ 无有效
  执行 → 引文线全部降级为间接。刻意窄化（全部无背书+类型限定）：宽规则
  原型 FRR 5/10，窄规则 FRR 0
- **时间有效性（TEMPORAL_STALE / SUPERSEDED / FUTURE_DATED /
  ANACHRONISTIC）**：证据 as_of 早于 claim_time 或超新鲜度窗口（recency
  标记声明）→ 降级为间接；until 早于声明时点 → 降级为间接；as_of 在
  未来 → 降级（来源存疑）；回溯性证据远晚于历史声明的 claim_time →
  标记 anachronistic。历史声明锚定 claim_time 后用同时期证据评判 ——
  旧≠错，但旧≠当前
- **同源塌缩（CORRELATED_EVIDENCE）**：并查集合并 —— 同声明组 / 同 URL
  宿主（除非双方证明 same_host_independent）/ 引文 token Jaccard≥0.7 /
  引用链（A 引 B 的锚点）。独立线数按塌缩后计：100 家转载 = 1 条线；
  aggregator 层级来源只支持限定声明、永不构成独立线
- **异构核查（SAME_MODEL_VERIFIER + cross_family）**：generator 与
  independent_checks[].by 的家族对比；同家族 = 相关失效不计数
  （cross-family > same-family > self, arXiv:2512.02304；同家族同错率
  ~60%，ICML 2025）。`verified_by: "tool:NAME"` 的确定性工具线天然异构。
  ≥2 独立线但无一机械核实 → ATTESTED_ONLY_LINES 压到 L3

### 6. 证据等级推导（脚本）

- **输入**：核查后的证据条目（含降级）、valid_execution、**塌缩后**独立线数
- **输出**：L0–L4
- **职责**：`L = max(间接=1, 带锚点直接=2, 有效执行=3, ≥2独立线且含
  硬通道=4)`；锚点核查失败/数字缺失/时间失效的条目降级为间接；纯
  attested 的多线封顶 L3
- **失败情况**：同源判据是语法性的（宿主/Jaccard/引用链），语义级改写
  转载（同一通稿的不同措辞版本）可能漏塌缩（Open Problem：非字面
  syndication 检测）

### 7. 所需等级（脚本）

- **输入**：escalated claimed_strength、type、causal/works、risk、gate_point
- **输出**：req L0–L4 + cross_family_required（cross_verified×高/极高风险）
- **职责**：结论强度的等级要价。例：works 声明 ≥likely → L3；
  pre-action 模式 works_floor 降到 possibly（不可逆动作前任何 works 声明
  都要执行过）；absolute 恒为 L4；高强度+高风险额外要求异构验证
- **失败情况**：等级要价与实际风险错配（过度阻塞的来源；对策：风险分级 +
  降级重跑永远合法 + benchmark 的 FRR 门禁）

### 8. 反证与隔离（脚本 + Agent 侧）

- **输入**：`counter_evidence[]`（status/contradicts）+
  `counter_search_context`
- **输出**：FACT+活矛盾 → REJECT；未处理矛盾+高风险 → VERIFY_REQUIRED；
  其余 → 强制 caveat；隔离缺失 + 强声明 → VERIFY_REQUIRED
- **职责**：反证字段必须存在（可为空但显式）；cross_verified/绝对化/高风险
  空反证要求 isolated 搜索上下文
- **失败情况**：`isolated` 虚报（对策：校准回路 —— 系统性虚报者的 L4 准确率
  会先崩）；真正没找过反证且措辞弱 → 只带 caveat 放行（设计取舍：低风险
  弱声明不强制反证，避免过度阻塞）

### 9. 样本→总体拦截（脚本）

- **输入**：`generalization{sample_size, population_size, statistical_basis}`
- **输出**：无统计基础的总体声明 → REJECT（若措辞 absolute/verified）
- **失败情况**：不用 generalization 字段直接在文本里说全量（对策：绝对化
  文本扫描兜底 → absolute → L4 要价 → 拦截）

### 10. 决策求值（脚本，按序短路）

```
FAKE_VERIFICATION（含通道错配）→ REJECT
FACT_CONTRADICTED → REJECT
ABSOLUTE_OVERREACH → REJECT
SAMPLE_TO_POPULATION → REJECT
cross_family_required 且未满足 → VERIFY_REQUIRED
shortfall + evidence_obtainable=no → ABSTAIN（记录 unobtainable_reason）
shortfall → VERIFY_REQUIRED
（隔离缺失 / 锚点强声明未核 → VERIFY_REQUIRED）
活矛盾+高风险 → VERIFY_REQUIRED
有未处理/已解释反证 → PASS_WITH_CAVEAT
否则 → PASS
```

- **失败情况**：规则次序 bug（回归用例按序锁定全部五类决策路径；
  改写不变性用例 case20–22 锁定"同义改写不翻转判定"）

### 11. 审计与校准（脚本）

- **输入**：每次运行（--log JSONL）；事后 `--mark-outcome`；`--calibration`
- **输出**：gate_id 可追溯记录 + ledger（逐线：锚点/通道/来源层级/as_of/
  塌缩关系）；按等级准确率 + Wilson 置信区间 + 单调性检查 + 风险-覆盖
  曲线（AURC）+ 弃权 P/R + 错误归因（哪个 finding 放走了错的结论）；
  `--emit-overrides`（每级 ≥10 标记）产出强制措辞上限
- **职责**：把"自报等级→实际对错"变成可测量数据；等级是序数不是概率，
  校准只来自真实结局；v3 移除了启发式 confidence 字段 —— 规则推出来的
  "信心"本身就是一个未验证声明
- **失败情况**：被动闭环（需要人工/外部标记 outcome）；冷启动无数据

## 已知设计取舍（诚实清单）

| 取舍 | 理由 |
|------|------|
| 机械核查只覆盖本地文件 + 在线 URL，issue-id 仅 trace-only | 强行打开不可打开的锚点会造成离线误降级（过度阻塞） |
| attestation 字段可撒谎但全部落日志 | 静态闸门无法读心；显式谎言 + 校准回路是能力边界内的最优解 |
| 低风险弱声明不强制隔离反证 | 反证搜寻有成本，预算跟随 风险×声明强度（risk-tiers.md 五级阶梯） |
| 关键词扫描而非语义模型 | 零依赖、确定性、毫秒级；漏报由等级算术兜底 |
| 同源判据是语法性的（宿主/Jaccard/引用链） | 语义级转载检测（同一通稿的不同措辞）无可靠零依赖方案（Open Problem）；语法判据已覆盖 A/B 中的全部攻击且 FRR=0 |
| 数字一致性只查"1–3 个带单位数字全部无背书+无执行" | 宽规则原型误伤 5/10 正例；窄规则保 FRR=0。更多数字/无单位声明的漏报由等级算术与反证要求兜底 |
| 同家族核查按家族名首词判定 | 版本混杂的家族边界无法零依赖精确判定；漏判后果 = 退回 v2 行为（不比现状差） |
| freshness 窗口默认 365 天（可调） | 时效性是连续谱；硬默认 + freshness_days 字段 + claim_time 历史豁免是可解释折中 |
