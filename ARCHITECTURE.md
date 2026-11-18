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
Claim Classification
  ↓ FACT | INFERENCE | HYPOTHESIS
  │  | RECOMMENDATION | EXPERIMENT_RESULT
Verification (verify-first)
  ↓ 能执行就执行；执行是 L3 的唯一来源
Evidence Collection
  ↓ 每条带锚点+引文                     ┌─ G3 pre-action 升档（--gate-point）
Counter-Evidence (isolated search)    ├─ 文本扫描：绝对化/因果/works/风险关键词
  ↓                                    ├─ 锚点三段式机械核查 ─────────────┐
Gate input (JSON) ──────────────────→  ├─ 验证有效性（executed×env×target）│
                                       ├─ 证据等级 L0–L4 推导              │
                                       ├─ 所需等级 vs 实际等级             │
                                       ├─ 反证状态 + 隔离要求              │
                                       ├─ 样本→总体拦截                    │
                                       ├─ 决策（五类，按序求值）            │
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

### 4. 验证有效性（脚本）

- **输入**：`verification{executed, env_independent, validates_target}`
- **输出**：valid_execution 布尔 + ENV_CONTAMINATED / TEST_NOT_TARGETED findings
- **职责**：三个真值同时成立才算有效执行 —— 跑过 × 环境干净 × 测试真的
  覆盖目标。任何一项缺失，"已验证"措辞被 FAKE_VERIFICATION 拒绝
- **失败情况**：三项本身是自报的（边界：与 3 同，靠审计+校准）

### 5. 证据等级推导（脚本）

- **输入**：核查后的证据条目（含降级）、valid_execution、独立分组数
- **输出**：L0–L4
- **职责**：`L = max(间接=1, 带锚点直接=2, 有效执行=3, ≥2独立组=4)`；
  锚点核查失败的条目按其状态降级为间接
- **失败情况**：同源性误判（两篇互相转载被当两个组 → L4 虚高；对策：
  references/evidence-levels.md 的独立性判据"来源 1 错时来源 2 还成立吗"，
  机械层无法验证同源）

### 6. 所需等级（脚本）

- **输入**：escalated claimed_strength、type、causal/works、risk、gate_point
- **输出**：req L0–L4
- **职责**：结论强度的等级要价。例：works 声明 ≥likely → L3；
  pre-action 模式 works_floor 降到 possibly（不可逆动作前任何 works 声明
  都要执行过）；absolute 恒为 L4
- **失败情况**：等级要价与实际风险错配（过度阻塞的来源；对策：风险分级 +
  降级重跑永远合法 + benchmark 的 FRR 门禁）

### 7. 反证与隔离（脚本 + Agent 侧）

- **输入**：`counter_evidence[]`（status/contradicts）+
  `counter_search_context`
- **输出**：FACT+活矛盾 → REJECT；未处理矛盾+高风险 → VERIFY_REQUIRED；
  其余 → 强制 caveat；隔离缺失 + 强声明 → VERIFY_REQUIRED
- **职责**：反证字段必须存在（可为空但显式）；cross_verified/绝对化/高风险
  空反证要求 isolated 搜索上下文
- **失败情况**：`isolated` 虚报（对策：校准回路 —— 系统性虚报者的 L4 准确率
  会先崩）；真正没找过反证且措辞弱 → 只带 caveat 放行（设计取舍：低风险
  弱声明不强制反证，避免过度阻塞）

### 8. 样本→总体拦截（脚本）

- **输入**：`generalization{sample_size, population_size, statistical_basis}`
- **输出**：无统计基础的总体声明 → REJECT（若措辞 absolute/verified）
- **失败情况**：不用 generalization 字段直接在文本里说全量（对策：绝对化
  文本扫描兜底 → absolute → L4 要价 → 拦截）

### 9. 决策求值（脚本，按序短路）

```
FAKE_VERIFICATION → REJECT
FACT_CONTRADICTED → REJECT
ABSOLUTE_OVERREACH → REJECT
SAMPLE_TO_POPULATION → REJECT
shortfall + evidence_obtainable=no → ABSTAIN
shortfall → VERIFY_REQUIRED
（隔离缺失 / 锚点强声明未核 → VERIFY_REQUIRED）
活矛盾+高风险 → VERIFY_REQUIRED
有未处理/已解释反证 → PASS_WITH_CAVEAT
否则 → PASS
```

- **失败情况**：规则次序 bug（回归用例按序锁定全部五类决策路径）

### 10. 审计与校准（脚本）

- **输入**：每次运行（--log JSONL）；事后 `--mark-outcome`；`--calibration`
- **输出**：gate_id 可追溯记录；按等级的 runs/known/correct/accuracy 表
- **职责**：把"自报等级→实际对错"变成可测量数据；等级的绝对映射不可信
  直到测量
- **失败情况**：被动闭环（需要人工/外部标记 outcome）；冷启动无数据

## 已知设计取舍（诚实清单）

| 取舍 | 理由 |
|------|------|
| 机械核查只覆盖本地文件 + 在线 URL，issue-id 仅 trace-only | 强行打开不可打开的锚点会造成离线误降级（过度阻塞） |
| attestation 字段可撒谎但全部落日志 | 静态闸门无法读心；显式谎言 + 校准回路是能力边界内的最优解 |
| 低风险弱声明不强制隔离反证 | 反证搜寻有成本，预算跟随 风险×声明强度（risk-tiers.md） |
| 关键词扫描而非语义模型 | 零依赖、确定性、毫秒级；漏报由等级算术兜底 |
