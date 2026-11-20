# Evidence Gate 可靠性升级最终报告 — 从"证据结构检查器"到"结论验证系统"

- 日期：2026-11-19
- 范围：文献调研（2024–2026，重 2025/2026）→ 设计 → 实现（v3.0.0）→ 基准 → A/B 实验 → 文档
- 版本对照：**本文"1.0" = 仓库 v2.0.0**（升级前，快照存于 `benchmark/legacy/`）；**"2.0" = 仓库 v3.0.0**（本次升级）

---

## 1. Executive Summary

**结论一句话：升级成立，且有实验证据。** 在按 v3 认识论构造的对抗语料上，
Evidence Gate 1.0 的 FAR = **100%**（6/6 攻击全部穿透），2.0 的 FAR = **0%**
且 FRR = **0%**（4 条诚实正例零误伤）；core 语料（v2 时代原始标签、原始输入）
两版双双 100% —— 完全向后兼容；代价是平均每条多几毫秒的相关性/时间/账本计算（确定性脚本内，相对
Agent 验证成本可忽略）。升级不是把门槛抬高，而是回答了 1.0 没有问的四个问题：
**谁验证的（异构性）、验证的是哪条线（独立性）、什么时候的证据（时效）、
证据里的数字和结论里的是否同一个（蕴含）**。

八个根问题的处置（详见 §4 矩阵）：P1/P2 证据真实性与来源可靠性 → 5 个新机械
检查（数字一致性、同源塌缩、时间有效性、attested-only 封顶、污染检测）；
P3/P4 verifier 自身出错与同模型相关失效 → 异构验证要求（跨家族或确定性工具）
+ 改写不变性测试 + 校准回路（谁验证验证者：结局数据）；P5 成本 → 五级验证
阶梯与通道路由；P6 不可验证 → 带分类学的弃答（unobtainable_reason 四类）；
P7 形式化边界 → claim_class 机械通道强制；P8 等级≠概率 → 移除启发式
confidence 字段，只认测量校准（Wilson CI / 风险-覆盖曲线 / --emit-overrides）。

诚实边界：对抗语料由维护者构造（构造者偏差，已在 benchmark 报告声明）；
本基准只测闸门层，不测端到端 Agent 准确率（协议已写、未运行）；语义级
转载检测、无真值事实性上限等问题明确标记为 Open Problem（§9）。成熟度
评级：**Beta**（论证与依据见 §10）。

---

## 2. 文献综述（Literature Review, 2024–2026）

两轮调研（`docs/research-survey.md` 第一轮；`docs/research-survey-2.md` 本轮），
五个并行方向约 70 篇候选、43+ 篇验证后承重。方法纪律：每篇标注 ✅（摘要/
全文核实）或（仅片段）；不可核实的一律标注，两处上一轮错误被纠正（见 §2.3）。
按主题的承重结论（完整文献注记见调研文档 §2）：

**（a）证据一致 ≠ 事实为真 / 引用蕴含。** 真实 Agent 引用中约一半不支持其
结论（Stanford 2024：51.5% 互联网引用误用；SourceCheckup 2025：50–90% 医疗
引用不相关或仅部分支持）。RefVerifier（2026，snippet 级核实）：无真值场景下检索式核查的
准确率上限约 71% —— 蕴含判断本身会错，所以 v3 把"数字"这个可机械判定的
子集交给脚本而不是语言判断。

**（b）相关性与独立性。** 同家族模型同错率约 60%，且模型越大越相关
（arXiv:2506.07962, ICML 2025）；9 个同分布裁判 ≈ 2 票有效，聚合最多挽回
约 11%（arXiv:2605.29800）；前沿模型间一致性 rho 0.20–0.59，且高一致案例中
48% 是错的（arXiv:2607.08065）——**一致只配路由，不配裁决**。跨家族显著
优于同家族优于自检（arXiv:2512.02304）。新闻转载：52% 编辑内容为复用，
且大多非逐字（Rewrite-the-News 2026）→ 同源判据不能只靠逐字匹配。

**（c）Verifier 自己会错。** 规则型与模型型验证器对称失效：规则偏向 FRR、
模型偏向 FAR（arXiv:2505.22203, EMNLP 2026）→ v3 保持"规则裁决 + 语言模型
提议"的分工并给每条规则配正例防误伤。同构扰动测试（arXiv:2604.15149）：
判决对等价改写翻转 = 可被措辞博弈 → 新增改写不变性测试用例。Verifier
自身的出生门槛与锚定集（arXiv:2610.11464）；FALCA 的 Searcher–Falsifier
分工与 GauntletScore 的双边矛盾规则。

**（d）弃权与校准。** AbstentionBench（2025）：推理微调使弃权质量降 24%，
弃权需双向度量（该弃的弃了 / 不该弃的别乱弃）；AgentAbstain：模型回答了
59.5% 不该碰的风险问题。SCOPE（2026）：200–500 个校准样本即可把 FDR 控到
α；Conformal Risk Control（ICLR 2024）：序数等级 → 嵌套集合的保序映射，
不需要概率。

**（e）验证经济学与形式化边界。** FIRE：置信驱动的提前停机省 7.6–16.5 倍
成本；ABC：一致性级联；Trust-or-Escalate（2024）。PBT 作为语言验证与形式
验证之间的中间档（Agentic PBT 2025）；能形式化的交给机器（VERGE 语义路由
2026）；执行通道本身可被自写测试博弈（ImpossibleBench/EvilGenie 2025）→
工具验证要问"测试有没有牙齿"，这正是 v2 就有的 validates_target 字段。

**（f）时效与污染。** 时效性需硬约束而非提示词（TUM 2026）；基准污染宿主
（huggingface datasets）可机械识别（STC 2025）。

### 2.3 对上一轮调研的纠错（不装作没错过）

1. **VICTOR 不存在**：仅能找到 ResearchGate 上一份未被收录的 CSV 预印本，
   不可作为承重文献 —— 已从结论中移除。
2. **采样一致性不能操作化 L4**：上一轮曾设想"多次采样一致 → 高可信"；
   2607.08065 的高一致-高错误率数据否定了这条路（一致是相关性的函数，
   不是正确性的函数）。L4 硬通道改为机械核实（引文核对 / 工具 / 跨家族核查）。

---

## 3. 问题分析（1.0 为什么不够）

实证起点：升级前先构造 6 类攻击跑 1.0 —— **全部穿透**（`benchmark/AB-RESULTS.md`
逐条对照）。根因是 1.0 的四个盲区，对应任务书的 P1–P8：

| 盲区 | 实证（1.0 判定） | 根因 |
|------|------------------|------|
| 蕴含只查"引文在文件里" | b14：结论 30s、引文 60s → PASS L2 | 三段式核查验存在性，不验数字蕴含 |
| 独立性靠自报 group | b15：同宿主两篇 → PASS L4/HIGH | 无同源塌缩，转载当独立线 |
| 无时间维度 | b16：2024 快照撑"当前版本" → PASS | 证据没有 as_of，声明没有 claim_time |
| 验证者身份不可见 | b17：glm 验 glm → PASS L4/HIGH | generator/检查者家族不在输入里 |
| （连带）attested 即 L4 | b18：从未抓取的 URL ×3 → PASS L4 | ≥2 组即 L4，不问有没有一条被机械核实 |
| （连带）通道不问类别 | b19：读代码推理当 verified → PASS L3 | executed=true 即算执行，不问通道 |

结构性诊断：1.0 是**证据结构检查器**（字段齐、锚点真、措辞不越级），它把
"证据存在且形式合格"当作"证据可靠且蕴含结论"。四段认识论链
**存在 → 可靠 → 蕴含 → 为真**里，1.0 只把守了第一段和第四段的措辞侧；
2.0 补第二、三段的机械检查与第四段的验证者侧检查。

---

## 4. Research → Solution 映射（问题→研究→方案矩阵）

完整矩阵见 `docs/research-survey-2.md` §3（8 行：相关研究 / v2.0.0 现状 /
v3.0.0 方案 / 是否采用）。摘要：

| 问题 | 承重研究 | v3 落地机制 | 状态 |
|------|----------|-------------|------|
| P1 蕴含缺口 | Stanford 2024 / SourceCheckup / RefVerifier | MISLEADING_QUOTE：结论单数字（带单位）必须出现在引文/锚点文本 | ✅ 采用（窄规则） |
| P2a 来源相关 | 2605.29800 / Rewrite-the-News / CONFACT | CORRELATED_EVIDENCE：组/宿主/Jaccard≥0.7/引用链并查集塌缩；aggregator 永不独立 | ✅ 采用（语法判据） |
| P2b 时效 | TUM 2026 | TEMPORAL_STALE / SUPERSEDED + claim_time 历史豁免 + freshness_days | ✅ 采用 |
| P2c 污染 | STC 2025 | 污染宿主黑名单 → 证据作废 | ✅ 采用 |
| P3 verifier 出错 | 2505.22203 / 2604.15149 / 2610.11464 | 规则+模型分工不变；每条新规则配正例；改写不变性用例；校准回路归因 | ✅ 采用 |
| P4 同模型相关 | 2512.02304 / 2506.07962 / 2607.08065 | SAME_MODEL_VERIFIER + cross_family_required；工具线天然异构；ATTESTED_ONLY 封顶 L3 | ✅ 采用 |
| P5 成本 | FIRE / ABC / Trust-or-Escalate | 五级验证阶梯 + claim_class 通道路由（risk-tiers.md） | ✅ 采用（阶梯为文档约定，非脚本强制） |
| P6 弃权 | AbstentionBench / AgentAbstain | ABSTAIN + unobtainable_reason 四类分类学 + 弃权 P/R 校准指标 | ✅ 采用 |
| P7 形式化边界 | Agentic PBT / VERGE / ImpossibleBench | MECH_CLASSES×MECH_VERIF_CHANNELS 强制（错配 → REJECT） | ✅ 采用 |
| P8 校准 | SCOPE / Conformal RC | 移除 confidence 字段；Wilson CI + 单调性 + AURC + --emit-overrides | ✅ 采用 |
| — 语义级转载检测 | 无可靠零依赖方案 | — | ❌ Open Problem |
| — 无真值事实性上限 | RefVerifier ~71% | — | ❌ Open Problem |

每个升级项的五问（为什么改/研究依据/现状缺陷/如何降 FAR·FRR·成本/如何实验
验证）在 `docs/research-survey-2.md` §2 逐问题文献注记与 `ARCHITECTURE.md`
模块明细中逐条可查；实验验证见 §8。

---

## 5. Evidence Gate 2.0（v3.0.0）设计

不变的骨架：LM 提议、确定性检查器裁决；结论强度 ≤ 证据强度；五类决策
（PASS / PASS_WITH_CAVEAT / VERIFY_REQUIRED / ABSTAIN / REJECT，exit
0/0/10/15/20）；锚点三段式；隔离反证；pre-action 升档。新增八个机制
（P0-A…P0-H，`scripts/gate_check.py` 模块头注释与 `ARCHITECTURE.md` §5）：

- **P0-A MISLEADING_QUOTE**：结论（FACT/INFERENCE/EXPERIMENT_RESULT）声称
  1–3 个带单位数字 + 全部无任何引文/锚点/详情背书 + 无有效执行 → 引文线
  全部降级间接。数字匹配含归一化（千分位/尾零/全角）与时间单位换算。
  窄化的原因：宽规则原型 FRR 5/10（版本号、条件阈值被误伤）。
- **P0-B CORRELATED_EVIDENCE**：并查集塌缩（同组 / 同注册域名，除非双方
  证明 same_host_independent / 引文 token Jaccard≥0.7 / 引用链——引文或
  detail 文本引用对方锚点）；independent_lines 按塌缩后计。
- **P0-C 时间有效性**：as_of/until 对比 claim_time；recency 标记 + 超
  freshness_days（默认 365）→ 降级；未来日期证据降级；远晚于声明时点的
  回溯性证据标记 anachronistic；历史声明锚定时点后用同期证据评判。
- **P0-D 异构验证**：cross_verified × 高/极高风险 → 需要跨家族
  independent_check（isolated 上下文、agree）或 `verified_by: "tool:NAME"`
  工具线；同家族 → SAME_MODEL_VERIFIER；家族不可辨不计；任何家族的
  不同意检查一票阻断；不满足 → VERIFY_REQUIRED。
- **P0-E ATTESTED_ONLY_LINES**：塌缩后 ≥2 独立线但无一条硬通道（机械
  引文核验 / 工具线 / 跨家族核查）→ 封顶 L3（存在证据 ≠ 证据被检验）。
- **P0-F CHANNEL_MISMATCH**：MECH_CLASSES（code_behavior/config/data/math）
  × verified+ 强度 → 通道必须是 MECH_VERIF_CHANNELS
  （execution/test/assertion/formal_proof/statistical）；否则执行作废 →
  FAKE_VERIFICATION → REJECT。
- **P0-G 弃答分类学**：unobtainable_reason ∈ {no_access, nonexistent,
  unreproducible, undecidable}，写入输出与审计日志。
- **P0-H 校准而非信心**：移除 confidence 字段；校准命令输出 per-level
  准确率 + Wilson CI、单调性检查、风险-覆盖曲线与 AURC、弃权 P/R、
  错误归因（哪个 finding 放走了错结论）；--emit-overrides（每级 ≥10 标记）
  生成强制措辞上限。
- **账本（ledger）**：逐线记录锚点/通道/来源层级/as_of/塌缩关系 —— 每个
  决策可回放。

输入 schema 向后兼容：v2 输入原样通过（新字段缺省不触发新规则），A/B 实验
依赖这一点（同一份语料喂两个版本）。

---

## 6. Benchmark 设计

- **gate-level 标注语料**（`benchmark/corpus/`，33 条）：core 23 条（v2 时代
  原始标签；22 条输入未改动，p03 增补可选 v3 字段——`verified_by:
  "tool:..."` 及 detail 点名工具，使其诚实的工具验证线对 v3 可见；v2 忽略
  新字段、两版均 PASS L4；未适配输入上 v3 判 VERIFY_REQUIRED（工具线不可见，
  从严）。标签不变，判定从严）+ adversarial 10 条（6 攻击 + 4 正例，v3
  认识论）。
- **9 类声明覆盖**：Correct（p01/p03/p09…）、Incorrect（b01–b05…）、
  Insufficient（b02…）、Misleading（b14）、Correlated（b15）、Outdated（b16）、
  Adversarial/伪验证（b17/b19）、Unverifiable（b08、case26）、Contradictory
  （b06–b08…）。
- **每条新规则配正例防误伤**：p11 异构交叉验证（PASS L4）、p12 历史声明
  （旧证据正当）、p13 聚合源限定声明（scoped L2 PASS）、p14 机械通道配对
  （test 通道 PASS）。规则与模型型验证器对称失效（2505.22203）的工程回应。
- **指标**：FAR / FRR 为一等公民（Accuracy 附带）；suite 分组报告
  （`benchmark/run_benchmark.py`）；CI 门禁 = FAR==0 且 FRR==0。
- **A/B**（`benchmark/run_ab.py`）：1.0 快照（`benchmark/legacy/
  gate_check_v2.0.0.py`，升级前原样拷贝）与 2.0 逐字节同输入对比 +
  adversarial 逐条 diff（FIXED/REGRESSION 标签）。
- **改写不变性**（arXiv:2604.15149）：tests case20–22 —— 攻击改写不掉级、
  诚实改写不升降、相关塌缩在改写下稳定（连 independent_lines 计数一致）。
- **诚实边界（语料报告内声明）**：语料由维护者构造，存在构造者偏差；
  对抗语料的 should_block 预期按 v3 认识论标注（这正是升级本身，core 语料
  保留 v2 标签以保兼容性公平）；欢迎社区扩充（CONTRIBUTING）。
- **未测量**：端到端 Agent 准确率（AGENT-PROTOCOL.md 已写，未运行）——
  本报告不宣称任何端到端数字。

---

## 7. 实现说明

- `scripts/gate_check.py`：~1500 行，零第三方依赖，Python 3.10+；新增
  correlation_analysis / quantity_figures（单位词表）/ wilson_ci / 家族判定
  等纯函数；assess() 管线在 v2 阶段前插入 v3 四件套（见 ARCHITECTURE.md §5）。
- 测试：`tests/run_tests.py` 26 用例 + 3 CLI 子测试 = **29/29**；新增
  output_equals 断言（independent_lines、unobtainable_reason 可直接锁定）。
- 文档：SKILL.md（4 核心规则、7 步 Gate Loop、新字段全表、11 类伪造验证、
  新合理化对照表）；references×4（decision-rules 新增 v3 机械检查与决策序、
  evidence-levels 重写等级推导、risk-tiers 五级阶梯+通道路由、
  failure-patterns 模式 7–11）；ARCHITECTURE.md 管线图与 11 模块、7 条设计
  取舍；examples 10 个全部用 v3 真实输出重新生成 + 新增 11/12/13/14（误导
  引文/相关证据/异构正例/带强制保留的放行），示例输出均为脚本逐字输出。
- 一处设计决定值得记录：b19（读代码推理当 verified）最初设计为独立
  CHANNEL_MISMATCH 决策，最终并入 FAKE_VERIFICATION → REJECT —— 语义上
  "错误通道的验证"就是"没有验证"，且避免了决策分支增殖。

---

## 8. 实验结果

**回归**：tests 29/29；benchmark 33/33（FAR 0/19、FRR 0/14；单条时延
60–130ms 含解释器启动，随机器负载浮动）。

**A/B（同输入喂两版，`benchmark/AB-RESULTS.md`）**：

| suite | Gate | Accuracy | FAR | FRR | 延迟* |
|-------|------|----------|-----|-----|------|
| adversarial（6 攻击 + 4 正例） | 1.0 (v2.0.0) | 40.0% | **6/6 (100%)** | 0/4 (0%) | 102ms |
| adversarial | **2.0 (v3.0.0)** | **100.0%** | **0/6 (0%)** | **0/4 (0%)** | 105ms |
| core（23 条，v2 原标签） | 1.0 | 100.0% | 0/13 | 0/10 | 103ms |
| core | 2.0 | 100.0% | 0/13 | 0/10 | 113ms |

*单机测量，含 Python 进程启动，绝对值随负载浮动；相对差异（v3 每条多
几毫秒的相关性/时间/账本计算）才是稳定量。

逐条：6 条攻击全部 FIXED（1.0 放行 → 2.0 拦截，判定分别为 VERIFY_REQUIRED×5、
REJECT×1），0 REGRESSION（1.0 放行的诚实正例 2.0 全部保持放行）。
改写不变性：case20 ≡ case15（连级别 L1 一致）、case21 保持 PASS L4、
case22 ≡ case16（连 independent_lines=2 一致）。

**解读纪律**：adversarial 套件按 v3 认识论构造，1.0 在其上 FAR 100% 是
升级目标的度量而非对 1.0 的标签不公 —— 佐证是 core 套件（v2 时代的标签，
输入除 p03 的可选字段增补外原封不动，见 §6 披露）上 2.0 无任何回归：新规则
只对 v3 才能识别的攻击形态起作用，
没有为拦截新攻击付出旧能力的代价。

---

## 9. Remaining Limitations / Open Problems（明确不装作已解决）

1. **构造者偏差**：对抗语料由升级者本人构造；"6/6 拦截"证明机制生效，
   不证明对抗未知攻击形态的泛化。缓解：语料结构公开、贡献通道开放；
   下一步应由第三方构造红队语料复跑。
2. **gate-level ≠ end-to-end**：闸门对申报输入的判定是确定性的，但申报
   本身可撒谎（attestation 边界，v2 起已知）；端到端（baseline agent vs
   agent+gate 的准确率/幻觉率/成本）协议已写未跑。**本报告不宣称端到端
   准确率提升。**
3. **语义级转载检测**（Open Problem）：同一通稿的非逐字改写版本可绕过
   Jaccard 判据；宿主/引用链判据是语法性的。零依赖语义判据目前无可靠方案。
4. **无真值事实性上限**（Open Problem）：RefVerifier ~71% 的上限意味着
   "证据是否真支持结论"的语言判断本身有不可消除的误差；v3 的对策是把
   可机械化的子集（数字、存在性、日期、宿主）交给脚本，其余显式标为
   attested 并落日志 —— 是风险收缩，不是解决。
5. **家族判定按首词**：glm-5.3 与 glm-4 的家族边界用标识符首词近似；
   混合架构/蒸馏模型可能误判。漏判后果 = 退回 v2 行为（不比现状差）。
6. **freshness 窗口是硬编码默认**：365 天对软件文档偏松、对安全通告偏紧；
   已开放 freshness_days 字段，但最优值需要按领域的结局数据校准。
7. **改写不变性只测三类**：case20–22 覆盖误导/相关/诚实三形态的同义改写；
   系统性扰动测试（2604.15149 的 IPT 全流程）未做。
8. **校准回路冷启动**：--emit-overrides 需要每级 ≥10 个标记结局；真实项目
   冷启动期间退化为静态上限。

---

## 10. 最终建议（Final Recommendation）

**成熟度评级：Beta**（Experimental → **Beta** → Production Candidate）。

- 不是 Experimental：机制全部有承重文献依据 + 33 条标注语料 100% +
  26 用例回归 + A/B 显示明确的 FAR 收益且零回归 + 完整审计/校准回路。
- 还不是 Production Candidate：对抗语料自构造（偏差未消）、端到端未测、
  语义级攻击面（非逐字转载、跨语言改写）未覆盖、校准数据为零冷启动。

**建议采用路径**：个人/低风险团队现在就可以用（core 行为与 1.0 完全兼容，
只是多了对伪验证形态的拦截）；生产采用前建议完成三件事——① 第三方红队
语料复跑对抗套件；② 跑一次 AGENT-PROTOCOL 端到端对照；③ 积累 ≥200 条
标记结局后启用 --emit-overrides 校准上限。

**对任务书最高优先级原则的回应**：研究证明错了的设计没有保留
（同报组即独立、attested 即 L4、reasoning 当验证，均已废除或封顶）；
四段认识论链成为输出结构（ledger 逐线可审计）；验证者不再被视为无错
（异构要求 + 校准归因）；同源不再计独立（塌缩）；等级不是概率（confidence
字段已删除）；没有靠全拒降 FAR（core 100% 保持，每条新规则配正例）；
现实目标是预算内最大化可靠性 + 可靠弃权（五级阶梯 + 弃答分类学）——
达成的部分有实验证据，未达成的部分在 §9 逐条署名。
