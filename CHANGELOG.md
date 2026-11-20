# Changelog

本文件记录对外发布版本。格式遵循 [Keep a Changelog](https://keepachangelog.com/)，
版本遵循 [SemVer](https://semver.org/)。

## [3.0.0] - 2026-11-19

可靠性专项升级（"Evidence Gate 2.0"）：从证据结构检查器到结论验证系统。
设计依据为 2024–2026 文献调研（约 70 篇候选、43+ 篇承重，引用逐条核实，
允许推翻既有设计）。**破坏性变更仅一处：
`--json` 输出移除 `confidence` 字段**（见下）；输入 schema 完全向后兼容。

### 能力（新增机制，每条附 A/B 实证）

- **MISLEADING_QUOTE 数字一致性**：结论声称的 1–3 个带单位数字全部
  无任何引文/锚点/详情背书时，引文线降级间接（引文真实存在但说 60s、
  结论说 30s → 降级）。数字匹配做归一化（千分位/小数尾零/全角）与
  时间单位换算（0.5 分钟 ≙ 30 seconds）。刻意窄化（全部无背书 + 未执行
  + FACT/INFERENCE/EXPERIMENT_RESULT），宽规则原型 FRR 5/10，窄规则 FRR 0
- **CORRELATED_EVIDENCE 独立性塌缩**：同声明组 / 同注册域名（可双方
  attestation 申诉）/ 引文 token Jaccard≥0.7 / 引用链（引文或 detail
  文本引用对方锚点 URL）→ 并查集合并；
  `independent_lines` 按塌缩后计数；`source_tier: aggregator` 支持限定
  声明但永不构成独立线。100 家转载 = 1 条独立线
- **时间有效性（TEMPORAL_STALE / SUPERSEDED / FUTURE_DATED /
  ANACHRONISTIC）**：证据 `as_of`/`until` 对比声明时点；recency 标记声明
  超 `freshness_days`（默认 365）降级；未来日期证据视为来源存疑降级；
  历史声明以 `claim_time` 锚定后用同期证据评判（旧≠错，旧≠当前，
  远晚于声明时点的回溯性证据标记 anachronistic）
- **SAME_MODEL_VERIFIER + 异构验证要求**：cross_verified × 高/极高风险
  需要跨模型家族 `independent_checks`（isolated、agree）或
  `verified_by: "tool:NAME"`（须有名有姓）工具线（工具天然异构）；
  同家族核查不计；家族不可辨的核查不计（自报身份非佐证）；任何家族的
  isolated 不同意检查一票阻断（INDEPENDENT_DISAGREEMENT）
- **ATTESTED_ONLY_LINES L4 封顶**：≥2 独立线但无一条机械核实 → L3
  （"存在证据" ≠ "证据被检验"）
- **CHANNEL_MISMATCH 通道路由**：`claim_class`（code_behavior/config/
  data/math）× verified+ 强度必须走机械验证通道（execution/test/
  assertion/formal_proof/statistical），语言推理作废 → REJECT
- **污染检测**：基准污染宿主（huggingface datasets 等）上的证据不作数
- **弃答分类学**：`unobtainable_reason` ∈ {no_access, nonexistent,
  unreproducible, undecidable}，随 ABSTAIN 输出并落审计日志
- **校准升级**：per-level 准确率 + Wilson 置信区间 + 单调性检查 +
  风险-覆盖曲线（AURC）+ 弃权 P/R + 错误归因（哪个 finding 放走了
  错结论）；`--emit-overrides`（每级 ≥10 标记）生成强制措辞上限
- **证据账本（ledger）**：逐线记录锚点/通道/来源层级/as_of/塌缩关系，
  每个决策可回放

### 变更（可能影响下游）

- **移除**：`--json` 输出的 `confidence` 字段（启发式信心标签本身是
  未验证声明；等级是序数，校准只来自测量）
- 新输入字段（全部可选，缺省不触发新规则）：`generator`、`claim_time`、
  `claim_class`、`freshness_days`、`evidence[].as_of|until|source_tier|
  verified_by|same_host_independent`、`verification.channel`、
  `independent_checks[]`、`unobtainable_reason`
- 发布前经过一轮独立红队 + 代码审查 + 文档一致性核查（约 50 项发现），
  落地修复包括：输入 schema 类型校验（畸形输入 exit 2 而非崩溃）、
  结论文本的"已验证"措辞升级（gate 读文本不读字段）、被排除证据线
  （污染/聚合）不再贡献硬通道、账本与塌缩原因改用可读行标签、
  `--offline` 测试隔离、校准输出注明口径
- 证据等级语义：L4 现要求"塌缩后 ≥2 独立线 **且** 至少一条硬通道"；
  多条纯 attested 线封顶 L3

### Benchmark

- 语料 23 → 33 条：core 23（v2 原标签原输入，回归保护）+ adversarial
  10（6 攻击 + 4 防误伤正例）；suite 分组报告，CI 门禁 FAR==0 且 FRR==0
- **A/B**（`benchmark/run_ab.py`，v2 快照 `benchmark/legacy/`）：对抗套件
  v2 FAR 6/6 (100%) → v3 0/6 (0%)，FRR 两版均 0/4；core 两版均 100%
  （零回归）；v3 每条多若干毫秒的相关性/时间/账本计算，相对 Agent 验证
  成本可忽略。core 中 p03 增补了可选 v3 字段（`verified_by` 等），
  v2 忽略之、判定不变；未适配输入上 v3 从严判 VERIFY_REQUIRED
- 测试 14 → 26 用例（+3 CLI 子测试 = 29 checks）：每个新机制一例 +
  改写不变性三例（攻击改写不掉级、诚实改写不升降、塌缩计数稳定）

### 已知问题（Known Issues）

- 对抗语料由维护者构造（构造者偏差）；语义级转载检测（同一通稿非逐字
  改写）无可靠零依赖方案 —— Open Problem
- 无真值场景下蕴含判断存在 ~71% 准确率上限（RefVerifier 2026，snippet 级核实）；
  v3 的对策是把可机械化子集交给脚本、其余显式 attested 落日志——
  是风险收缩，不是解决
- 家族判定按标识符首词近似（混合架构/蒸馏模型可能误判；漏判退回 v2 行为）
- 校准回路冷启动：`--emit-overrides` 需每级 ≥10 标记结局
- Agent-level 端到端效果仍未测量（对比协议已定义、尚未运行）

### 设计依据

第二轮文献调研（约 70 篇候选、43+ 篇承重，引用逐条核实，含对第一轮
两处纠错：VICTOR 不存在；采样一致性不能操作化 L4）。

## [2.0.0] - 2026-11-18

首个公开发布版本（initial public release）。1.x 为内部迭代，未发布。

### 能力

- **结论强度 ≤ 证据强度** 机械执行：L0–L4 证据等级 → 措辞上限映射；
  结论文本扫描（绝对化/因果/works/风险关键词）不信任自评字段
- **五类决策**：PASS / PASS_WITH_CAVEAT / VERIFY_REQUIRED / ABSTAIN /
  REJECT，exit codes 0/0/10/15/20（输入错误 2），可直接接入 CI
- **锚点三段式核查**：锚点可解析 → 内容实读 → 引文在文中（本地文件
  机械比对，剥 Markdown 格式符）；引用存在 ≠ 引用支持
- **隔离反证要求**：cross_verified / 绝对化声明及高风险空反证要求
  `counter_search_context: "isolated"`（同上下文搜索 → VERIFY_REQUIRED）
- **ABSTAIN**：`evidence_obtainable: no` 时输出"目前无法确认 + 缺口说明"，
  禁止带保留的猜测
- **不可逆动作前置闸门（G3）**：`--gate-point pre-action`，风险升档、
  works 声明必须执行过、CAVEAT 降为 VERIFY_REQUIRED
- **假验证模式识别**：推理冒充验证 / 测试通过≠问题解决 / 环境污染 /
  样本冒充总体 / 引用冒充支持（含 verification gaming）
- **审计与校准回路**：JSONL 日志（gate_id）+ `--mark-outcome` +
  `--calibration` 按等级统计真实准确率
- **Gate-level benchmark**：23 条真值标注语料，实测 Accuracy 100%、
  FAR 0/13、FRR 0/10（见 benchmark/RESULTS.md；agent-level 端到端对比
  协议已定义、尚未运行）

### 工程属性

- `scripts/gate_check.py`：Python 3.10+，仅标准库，零依赖，确定性输出
- 测试：14 个回归用例 + 3 个 CLI 子测试（tests/run_tests.py）
- CI：单元测试 / benchmark 门禁（FAR/FRR=0）/ secret 扫描 / skill 校验

### 已知问题（Known Issues）

- 自报字段（`content_supports`、`counter_search_context`、
  `evidence_obtainable`）可被虚报；闸门的对策是显式记录 + 被动校准回路，
  冷启动阶段校准不构成约束
- 校准回路需要事后人工/外部标记 outcome，无自动采集（P1）
- 关键词启发式存在边界误报可能（如中文绝对化词的邻近措辞）；漏报由
  等级算术兜底，误报的救济是改写措辞
- `--gate-point` 依赖调用方自觉传入，脚本无法拦截进程外的工具调用
- Agent-level 端到端效果未测量，任何"提高准确率"的说法均无数据支持

### 设计依据

2024–2026 文献调研（引用逐条核实，允许推翻既有设计）。
