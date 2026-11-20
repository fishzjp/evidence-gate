# Evidence Gate

[![CI](https://github.com/fishzjp/evidence-gate/actions/workflows/ci.yml/badge.svg)](https://github.com/fishzjp/evidence-gate/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Dependencies](https://img.shields.io/badge/dependencies-0-green.svg)](#安装)

> A deterministic conclusion-quality gate for AI agents — evidence levels,
> counter-evidence checks, and wording ceilings enforced **before** a
> conclusion ships. v3 adds independence collapse, heterogeneous
> verification, temporal validity, and quote-figure consistency.

Evidence Gate 是一个面向 AI Agent 的结论质量闸门（Agent Skill）。它工作在
结论出口处：当 Agent 即将输出一条重要结论时，先核对这条结论背后的证据，
再决定它允许以什么强度的措辞说出口。整个项目只坚持一条原则——
**结论强度不得超过证据强度**。

它不靠提示词里的"请认真检查"起作用，而是把要求落成可执行的机制。Agent
为每条关键结论填写一份结构化证据清单；判定脚本 `gate_check.py` 对清单做
机械核查，输出五类决策之一，并给出允许的措辞上限。脚本是纯 Python 标准库
实现，没有第三方依赖，单次运行约 70 毫秒。每次运行都会写入审计日志，
事后可以回标结论的对错，从而统计各个证据等级的真实准确率。

v3.0.0（"Evidence Gate 2.0"）是一次可靠性专项升级：不是把门槛抬高，而是
补上 v2 没有问的四个问题——**谁验证的**（同模型自检是相关失效，不算交叉
验证）、**验证的是哪条线**（100 家转载 = 1 条独立线）、**什么时候的证据**
（2024 年的快照撑不起"当前版本"）、**证据里的数字和结论里的是否同一个**
（引文真实存在 ≠ 引文支持结论）。A/B 实测：6 类针对性攻击在 v2 上全部
穿透（FAR 100%），v3 全部拦截且诚实正例零误伤，旧语料完全向后兼容
（`python3 benchmark/run_ab.py` 可复现）。

> Evidence Gate 是验证与质量控制机制，不是正确性证明器。它能降低
> "未经验证的错误结论流入最终输出"的风险，但不能保证结论一定正确。
> 使用前请先读 [Limitations](#limitations必须先读)。

## 30 秒看懂

设想一个场景：Agent 抽查了 100 万条数据里的 100 条，没有发现问题，然后
准备向用户报告。

```text
过闸前   "100 万条数据 100% 全部合格，可以直接交付。"
             ↓  gate_check.py
过闸后   "抽查的 100 条未发现重复或字段缺失；整体 100 万条未验证。"
```

第一句的问题不在抽查本身，而在措辞越权：它把 100 条的结论说成了 100 万
条的结论。闸门拦下它，靠的是三条硬规则。其一，结论文本里的"100%"和
"全部"会被机械识别，此时无论自评字段怎么填都没用，因为脚本检查的是结论
原文。其二，从 100 条推断 100 万条属于"样本冒充总体"，没有统计基础就
直接拒绝。其三，绝对化措辞要求交叉验证级别的证据，凑不够就必须改写。

如果需要的证据根本拿不到——比如系统无权访问、事件不可复现——正确的
输出不是降低语气的猜测，而是第五类决策 ABSTAIN：明确说"目前无法确认"，
并讲清缺什么证据、为什么拿不到。

## 目录

- [为什么需要 Evidence Gate](#为什么需要-evidence-gate)
- [核心机制](#核心机制)
- [安装](#安装)
- [快速开始](#快速开始)
- [示例](#示例)
- [CLI 速查](#cli-速查)
- [Benchmark](#benchmark)
- [Limitations（必须先读）](#limitations必须先读)
- [FAQ](#faq)
- [架构与仓库结构](#架构与仓库结构)
- [参与贡献](#参与贡献)
- [License](#license)

## 为什么需要 Evidence Gate？

Agent 输出关键结论时有五类高频失效。危险之处在于，这五类结论每一类
都*看起来*像验证过：

| 失效 | 样子 | 实质 |
|------|------|------|
| 推理冒充验证 | "我分析了代码，它能正常运行" | 阅读只能算 L2 证据；说"正常运行"必须真的运行过 |
| 测试通过≠问题解决 | 套件全绿，关闭工单 | 测试可能从未覆盖那个 bug |
| 小样本冒充全量 | 抽查 100 条没问题，于是说"100 万条全部合格" | 样本不能证明总体 |
| 相关冒充因果 | 发布后错误率上升，于是说"新版本导致的" | 时间相关只是间接证据 |
| 引用冒充支持 | 附上一个真实链接 | 实测约半数真实引用并不支持其结论 |

v3 又补上五类更隐蔽的（v2 全部放行、v3 全部拦截，均有 A/B 实证）：

| 失效（v3 新增识别） | 样子 | 实质 |
|--------------------|------|------|
| 误导性引文 | 引文逐字在文件里，但结论说 30s、引文说 60s | 引用存在 ≠ 引用支持结论的数字 |
| 相关证据冒充独立 | 同一宿主两篇"独立报道" | 通稿转载：100 家转载 = 1 条独立线 |
| 过期证据冒充现状 | 2024 年快照撑"当前版本" | 旧证据对历史断言成立，对"当前"不成立 |
| 同模型自检冒充交叉验证 | glm 生成、glm"独立"复查 | 同家族模型同错率约 60%；一致只配路由，不配裁决 |
| 通道错配冒充验证 | 读代码推理后宣布"已验证" | 机器可判的声明必须走机器通道 |

这不是态度问题，而是机制问题。2024–2026 年的研究反复验证了几个结论
（设计时逐条核实原始论文，并允许证据推翻既有设计）：

- **自我验证靠不住。** 让模型检查自己的答案，在没有外部反馈的情况下几乎
  不会产生增益（Huang et al., ICLR 2024）。
- **同上下文找反例会被"同意偏差"吃掉。** 边看着结论边找反例，即使加更多
  算力，也基本找不到（SGV, ICLR 2026）。
- **引用存在不等于引用支持。** 对真实 Agent 引用的实测显示，51.5% 的网络
  引用被误用；医学场景中 50%–90% 的引用不支持或仅部分支持其结论
  （Stanford 2024；SourceCheckup 2025）。
- **同家族验证是相关失效。** 同家族模型同错率约 60%，模型越大越相关；
  9 个同分布裁判 ≈ 2 票有效；高一致案例中近半数是错的（ICML 2025；
  arXiv:2605.29800；arXiv:2607.08065）——所以跨家族模型或确定性工具
  才算异构验证。
- **Agent 会在不该回答的问题上硬答。** 实验中 59.5% 的高风险不可答问题
  被莽撞作答（AgentAbstain 2025）。

所以 Evidence Gate 不去说服模型"更认真"，而是换一种结构：语言模型负责
提议（填写结构化证据清单），确定性脚本负责裁决（机械核查与判定）。
"LM 提议、确定性检查器裁决"是被 AlphaProof 等系统验证过的有效分工。

## 核心机制

四条核心规则，全部由脚本机械执行，不依赖任何自觉：

1. **先验证再下结论，且走对通道。** 能执行就执行，能查询就查询，能读源码
   就读源码；机器可判的声明（代码行为/配置/数据/数学）必须走机器通道，
   语言推理不算验证。
2. **结论强度不超过证据强度。** 证据分为 L0–L4 五个等级，每个等级对应
   一个措辞上限。脚本会扫描结论*原文*来识别绝对化措辞、因果断言和
   "可以正常运行"类声明；自评字段填得再低，原文里的"全部""100%"照样
   会被抓出来。证据强度按**独立性塌缩后**计数——同宿主转载、近似引文、
   互相引用的证据线合并成一条。
3. **无法确认就明说。** 当决定性的证据无法获得时，输出 ABSTAIN，明确
   说"目前无法确认"并说明缺口在哪里（以及为什么拿不到），而不是给一个
   语气温和的猜测。
4. **谁验证的很重要。** "已交叉验证"要求异构验证：跨模型家族的独立核查，
   或确定性工具的核实。同模型自检的一致是相关失效，不是验证。

每条关键结论都要走一遍闸门循环。左侧是 Agent 的职责，右侧是脚本的
判定步骤，完整说明见 [SKILL.md](SKILL.md)：

```
Agent 侧                    脚本侧（确定性）
────────                    ──────────────
1 识别结论、分类类型+路由     ① 文本扫描：绝对化 / 因果 / works / 风险关键词
2 先执行能执行的验证（按通道） ② 锚点三段式：锚点可解析 → 内容实读 → 引文在文中
3 收集带锚点+溯源的证据       ③ 验证有效性：执行过 × 环境干净 × 覆盖目标 × 通道匹配
4 隔离式反证搜寻             ④ 数字一致性：结论的数字必须出现在引文里
5 异构独立核查（跨家族/工具）  ⑤ 时间有效性 + 同源塌缩（独立线按塌缩后计）
6 运行判定脚本  ──────────→  ⑥ 等级推导：实际等级 vs 所需等级
7 服从决策                   ⑦ 反证状态、隔离要求、样本推总体、五类决策 + 账本 + 日志
```

### 证据等级 L0–L4 与措辞上限

| Level | 含义 | 措辞上限 |
|-------|------|----------|
| L0 | 无证据（猜测、记忆、"应该行"） | 假设 / 推测 |
| L1 | 间接信号（日志症状、时间相关、小样本） | 可能 / 初步判断 |
| L2 | 带锚点的直接证据，且内容确实支持结论（引文经机械核验） | 根据现有证据可以判断 |
| L3 | 实际执行并观察过（跑过、测过）；多条 attested 证据线也止步于此 | 已通过实际验证 |
| L4 | 塌缩后 ≥2 条独立线一致，至少一条经机械核实（引文核对/工具/跨家族核查），反证搜寻在隔离上下文完成 | 已交叉验证 |

### 五类决策

| Decision | 含义 | Agent 的义务 | exit |
|----------|------|--------------|------|
| PASS | 证据支撑结论 | 按允许的措辞输出 | 0 |
| PASS_WITH_CAVEAT | 可以输出但受限 | 必须附上全部限定条件 | 0 |
| VERIFY_REQUIRED | 证据不足 | 先执行验证，或降级措辞后重跑；不得原样输出 | 10 |
| ABSTAIN | 所需证据无法获得 | 说"目前无法确认"并说明缺口；禁止输出任何版本的猜测 | 15 |
| REJECT | 结论不能成立 | 改写为限定措辞，或放弃这条结论 | 20 |

输入格式错误时 exit 2。非零退出码可以直接接入 CI 断言。

### 进阶机制

v2 的四个机制之上，v3 新增五个（每条都有防误伤正例）：

- **锚点三段式核查。** 一条引用要过三关：锚点可以解析、内容被实际读过、
  引文确实出现在文中（本地文件由脚本机械比对）。只过第一关的"引用存在"
  会被降级为间接证据。
- **数字一致性（MISLEADING_QUOTE）。** 结论声称的数字必须出现在引文里：
  结论说 30 秒而引文都说 60 秒时，引文线降级为间接证据。规则刻意窄化
  （单个带单位数字 + 未执行 + 特定类型），宽规则曾误伤 5/10 条诚实结论。
- **独立性塌缩（CORRELATED_EVIDENCE）。** 同声明组、同 URL 宿主（可申诉）、
  近似引文（Jaccard≥0.7）、互相引用的证据线合并为一条独立线；聚合源
  （转载站）支持限定声明但永不构成独立线。100 家转载 = 1 条独立线。
- **时间有效性。** 证据带 as_of；"当前版本"类时效声明建立在过期快照上
  会被降级。历史断言锚定时点（claim_time）后用同期证据评判——旧≠错，
  但旧≠当前。
- **异构验证要求 + attested 封顶。** "已交叉验证"（高风险）需要跨家族
  模型核查或工具核实（`verified_by: "tool:..."`）；全是"我看过、支持"
  的自报证据线封顶 L3——存在证据 ≠ 证据被检验。
- **隔离反证要求。** 声明"已交叉验证"或使用绝对化措辞时，反证搜寻必须在
  与结论不同的上下文中进行：先写下"什么证据能推翻我"，此时不看支持性
  证据，然后再去搜索。同上下文的搜索会直接得到 VERIFY_REQUIRED。
- **不可逆动作前置闸门（G3）。** 加上 `--gate-point pre-action` 运行时，
  低/中风险自动升为高风险（高/极高保持不变）；任何"不会中断"类 works
  声明都必须实际演练过（works 门槛降到 possibly）。
- **审计与校准回路。** 每次运行都追加一条 JSONL 日志（含逐线账本
  ledger：锚点/通道/来源层级/日期/塌缩关系）。事后用 `--mark-outcome`
  回标对错，用 `--calibration` 统计各等级真实准确率（v3 附 Wilson 置信
  区间、单调性检查、风险-覆盖曲线、弃权 P/R、错误归因），`--emit-overrides`
  可把校准结果变成强制措辞上限。v3 移除了启发式 confidence 字段——
  规则推出来的"信心"本身就是未验证的声明；等级是序数，校准只来自测量。

## 安装

运行只依赖 Python 3.10+，全部使用标准库，零第三方依赖。CI 在 3.10–3.13
矩阵上验证。

**方式一：skills CLI 一键安装（推荐）。** 本仓库已收录进开放 Agent skills
生态，一条命令即可安装到 Claude Code、Cursor、Codex、GitHub Copilot 等
35 个 Agent 运行时（19 个通用路径 + 16 个符号链接适配，以实际安装输出
为准）：

```bash
npx skills add fishzjp/evidence-gate
```

安装后可用 `npx skills update` 统一升级，`npx skills check` 检查更新。

**方式二：Claude Code 插件安装。** 仓库自带 plugin marketplace 清单
（`.claude-plugin/`），在 Claude Code 会话里执行：

```text
/plugin marketplace add fishzjp/evidence-gate
/plugin install evidence-gate@evidence-gate
```

**方式三：手动克隆。** 本仓库本身就是一个 skill，[SKILL.md](SKILL.md)
位于仓库根目录，克隆或复制到你的 Agent 运行时技能目录即可：

```bash
# 通用路径示例：
git clone https://github.com/fishzjp/evidence-gate.git ~/.agents/skills/evidence-gate
# Claude Code 使用：~/.claude/skills/evidence-gate
# 项目级安装：      <project>/.agents/skills/evidence-gate
```

安装后，Agent 会按 SKILL.md 里的触发条件自动使用它。如果运行时不支持
skill 机制，也可以把 SKILL.md 的内容贴进系统提示词：流程指引仍然有效，
只是失去了脚本的机械核查能力。

**作为独立命令行工具使用。** 不需要任何 agent 框架：

```bash
git clone https://github.com/fishzjp/evidence-gate.git && cd evidence-gate
python3 scripts/gate_check.py --help
```

## 快速开始

一分钟完成第一次判定。先创建 `gate-input.json`。下面的例子引用的是仓库
内的真实文件，可以直接复现：

```json
{
  "conclusion": "foo-lib 的默认请求超时是 60 秒",
  "type": "FACT",
  "claimed_strength": "judged",
  "risk_tier": "medium",
  "evidence": [
    {"kind": "official_doc", "detail": "foo-lib 配置参考：timeout 默认 60 秒",
     "anchor": "tests/fixtures/docs/api-timeout.md",
     "quote": "default timeout is 60 seconds", "content_supports": "supported",
     "group": "docs"}
  ],
  "verification": {"executed": false, "detail": "",
                   "env_independent": "unknown", "validates_target": "unknown"},
  "counter_evidence": [
    {"detail": "旧版本 v1.x 默认 30 秒；已核对锁文件确认项目固定 v2.3.1",
     "status": "refuted", "contradicts": true}
  ],
  "counter_search_context": "isolated",
  "evidence_obtainable": "yes",
  "generalization": null
}
```

然后运行：

```bash
python3 scripts/gate_check.py gate-input.json
```

输出如下（真实输出的节选）：

```text
Evidence Level: L2  (claim requires L2; independent lines: 1)
Evidence (anchor three-stage check):
  - [direct·mech✓] official_doc — quote verified in anchor: tests/fixtures/docs/api-timeout.md
Decision: PASS  (exit 0)
Allowed wording: 根据现有证据可以判断 (judged from evidence)
```

这个例子能通过，是因为三个条件都成立：引文机械核验通过（那行字确实在
文件里）、反证被核实排除（锁文件确认了版本）、声明强度与证据等级匹配。

不妨亲手试两个变体：把引文改成 `"default timeout is 30 seconds"` 再运行
同一命令，会得到 `ANCHOR_QUOTE_MISSING`，证据被降级，决策变为
`VERIFY_REQUIRED (exit 10)`。或者保持引文不变、把结论改成"默认请求超时
是 30 秒"——引文真实存在，但结论的数字不在任何引文里，v3 的
`MISLEADING_QUOTE` 照样拦截。这就是"引用存在不等于引用支持"的机械执行。

## 示例

仓库提供十四个完整示例，全部附带脚本的真实输出，覆盖全部五类决策与
v3 新机制。入口在 [examples/](examples/README.md)：

| 主题 | 教训 |
|------|------|
| [事实判断](examples/01-fact-check.md) | 带锚点引文的事实声明（PASS） |
| [技术结论](examples/02-theory-vs-verified.md) | 理论上可行不等于已实际验证 |
| [数据质量](examples/03-sample-to-population.md) | 小样本通过不等于全量合格 |
| [因果推理](examples/04-causal.md) | 相关性不等于因果关系 |
| [反证搜寻](examples/05-counter-evidence.md) | 在自己的数据里找到反例 |
| [引用蕴含](examples/06-citation-entailment.md) | 有引用不等于引用支持结论 |
| [弃权](examples/07-abstention.md) | 证据不可得时说"无法确认" |
| [高风险与不可逆动作](examples/08-high-risk-preaction.md) | pre-action 前置闸门 |
| [BAD 与 GOOD 对照](examples/09-bad-good.md) | 同一份数据的两种表述（REJECT 到 PASS） |
| [完整工作流](examples/10-agent-workflow.md) | 从任务到最终回答的全过程 |
| [误导性引文](examples/11-misleading-quote.md) | 引文真实存在 ≠ 引文支持结论的数字（v3） |
| [相关证据](examples/12-correlated-evidence.md) | 同宿主转载塌缩：100 家转载 = 1 条独立线（v3） |
| [异构交叉验证](examples/13-heterogeneous-crosscheck.md) | 跨家族核查 + 机械引文线 = 名副其实的 L4（v3） |
| [带强制保留的放行](examples/14-pass-with-caveat.md) | 结论成立，但解释过的反证必须随结论输出（PASS_WITH_CAVEAT） |

## CLI 速查

```bash
python3 scripts/gate_check.py <input.json>          # 人类可读结果
... | python3 scripts/gate_check.py --json -        # JSON 输出（适合 CI）
... | python3 scripts/gate_check.py --gate-point pre-action -   # 不可逆动作前
... | python3 scripts/gate_check.py --offline -     # 不抓取 URL（离线或敏感网络）
python3 scripts/gate_check.py --no-log ...          # 一次性运行，不写日志
python3 scripts/gate_check.py --log PATH ...        # 指定日志文件
python3 scripts/gate_check.py --mark-outcome <gate_id> correct|incorrect|unknown  # 校准回标
python3 scripts/gate_check.py --calibration         # 各等级真实准确率（含 Wilson CI）
python3 scripts/gate_check.py --calibration --emit-overrides  # 校准→强制措辞上限
```

开发与回归用四条命令：

```bash
python3 tests/run_tests.py --report     # 26 个回归用例（含改写不变性）+ 3 个 CLI 子测试
python3 benchmark/run_benchmark.py      # 33 条真值语料（FAR/FRR 门禁）
python3 benchmark/run_ab.py             # v2 vs v3 A/B 对照（升级效果实测）
python3 tests/validate_skill.py         # SKILL.md 结构与引用完整性
```

## Benchmark

**已测量：闸门级基准。** 它是确定性的，可以随时复现，结果快照在
[benchmark/RESULTS.md](benchmark/RESULTS.md)。语料分两个套件：core 23 条
（v2 时代的原始标签；22 条输入未改动，p03 增补了可选 v3 字段——见下）
+ adversarial 10 条（v3 攻击/正例）：

| 指标 | core（23 条） | adversarial（10 条） |
|------|---------------|----------------------|
| Accuracy | 23/23 (100%) | 10/10 (100%) |
| False Acceptance Rate（应拦未拦） | 0/13 (0%) | 0/6 (0%) |
| False Rejection Rate（应放被拦） | 0/10 (0%) | 0/4 (0%) |
| 时延 | 约 60–130 ms/条（含解释器启动，单机，随负载浮动） | 同左 |

用 `python3 benchmark/run_benchmark.py` 即可复现。这个命令同时也是 CI
门禁：只要 FAR 或 FRR 不为零，就退出非零。

**v2 vs v3 A/B（同一输入喂两版，`python3 benchmark/run_ab.py` 可复现）：**

| 套件 | Gate | Accuracy | FAR | FRR |
|------|------|----------|-----|-----|
| adversarial | v2.0.0（升级前快照） | 40.0% | **6/6 (100%)** | 0/4 |
| adversarial | **v3.0.0** | **100%** | **0/6 (0%)** | **0/4** |
| core | v2.0.0 | 100% | 0/13 | 0/10 |
| core | v3.0.0 | 100% | 0/13 | 0/10 |

解读纪律：adversarial 套件按 v3 认识论构造（独立性/异构性/时效），v2 在其上
全穿透是升级目标的度量；core 套件保留 v2 标签，v3 零回归说明新规则没有为
拦截新攻击付出旧能力的代价。**披露一处 core 输入适配**：p03 增补了可选
v3 字段（`verified_by: "tool:..."` 及 detail 点名工具），使其诚实的工具
验证线对 v3 可见——v2 忽略新字段、判定不变（两版都 PASS L4）；未适配的
原始输入上 v3 判 VERIFY_REQUIRED（工具线不可见，从严），标签不变。
需要说明的局限：语料由维护者构造，存在构造者
偏差；并且它测的是闸门判定器本身，而不是端到端的 Agent 表现。

**未测量：Agent 级对比。** baseline agent 与 agent+gate 的端到端对比
（Accuracy / Hallucination Rate / FAR / FRR / Cost / Latency）协议已定义、
尚未实际运行。因此在端到端效果上，本项目不宣称"提高 Agent 准确率"
这样的结论；它目前能主张的只有设计目标——降低未经验证的错误结论流入
最终输出的风险。

## Limitations（必须先读）

1. **不能保证绝对正确。** 闸门判定的是"结论强度与证据结构是否匹配"，
   而不是"结论与事实是否一致"。如果所有证据都指向 A 而 A 实际为假，
   闸门会放行一个措辞严谨的错误结论。
2. **证据本身可能错误。** 文档会过时，源码有 bug，基准数据可能被污染。
   L2、L3 的措辞上限（"根据现有证据""已通过实际验证"）正是为此保留的
   谦逊。
3. **验证器也会犯错。** 判定规则是启发式的，包括关键词扫描、引文匹配和
   等级算术，因此存在误报和漏报。已知中文绝对化关键词可能在个别边界
   措辞上误触发；实测 FAR/FRR 为零，但语料存在构造者偏差。
4. **同模型验证存在相关性失效（v3 已部分缓解）。** v3 起高风险"已交叉
   验证"要求跨家族模型或确定性工具核查，同家族自检不再计数。但家族判定
   按标识符首词近似（glm-5.3 与 glm-4 同家族），混合架构可能误判；且
   异构验证降低的是相关失效概率，不是零。这是缓解的深化，不是根除。
5. **验证有成本。** 每条关键结论多一次脚本运行（约 0.1 秒），外加填写
   证据清单的注意力开销。过度验证浪费，验证不足危险，风险分级（五级
   验证阶梯 + 通道路由）就是为了把预算花在对的地方。
6. **有些事实无法用现有工具验证。** 例如没有权限、事件不可复现、数据
   不可及。此时正确行为是 ABSTAIN，而不是被闸门逼出一个猜测。
7. **不替代形式化验证。** 它不证明程序正确性，也不证明定理。可形式化的
   性质请交给模型检查器或定理证明器。
8. **Evidence Level 不是概率意义上的置信度。** L0–L4 是措辞天花板（序数
   刻度），不是校准过的正确概率——v3 因此移除了启发式 confidence 字段。
   校准回路是被动闭环，依赖事后回标的 outcome 数据，冷启动阶段不构成
   约束。语义级转载检测（同一通稿的非逐字改写）、无真值场景下蕴含判断
   ~71% 的准确率上限等，仍是本项目的开放问题。

除以上八条，还有一个结构性边界：**自报字段可以造假**。`content_supports`
和 `counter_search_context` 这类字段由填写者声明，脚本无法核实其真伪；
它做得到的是把每一次声明变成显式、可审计、可校准的记录。这也是任何
静态闸门共同的能力边界。[ARCHITECTURE.md](ARCHITECTURE.md) 末尾的
"已知设计取舍"对此有完整讨论。

## FAQ

**会显著拖慢 Agent 吗？**
脚本本身每次运行约 75 毫秒，主要成本其实是填写证据清单所占用的注意力。
因此闸门按风险分级：低风险结论只需对照措辞表，不必跑脚本（见 SKILL.md
的 "When NOT to gate" 一节）。

**支持哪些 Agent 框架？**
框架无关。任何能执行 shell 命令、能读 Markdown 的 Agent 都可以使用，
包括 ZCode、Claude Code 和各类通用 CLI Agent，不需要运行时集成。也
完全可以脱离 Agent，把它当作命令行工具人工使用。

**支持中文结论吗？**
支持。绝对化、因果、"可以正常运行"类关键词的扫描同时覆盖中英文，
措辞上限表也是双语的（从"假设/推测"到"已交叉验证"）。

**已经有 verification-before-completion 类 skill 了，还需要这个吗？**
两者互补。那类 skill 回答"完成之前要不要再查一遍"，而 Evidence Gate
提供它们缺少的部分：机械判定器、结构化证据格式和审计回路。它可以直接
充当那类 skill 的执行层（见 SKILL.md 的 "Combining with other skills"）。

**为什么不直接在提示词里写"请仔细验证再回答"？**
因为研究反复证明这没有效果：没有外部反馈的自我验证不产生增益，同上下文
的自我批评被同意偏差支配。提示词改变的是语气；"确定性脚本加结构化输入"
改变的是行为。

**它会让 Agent 变得过度谨慎吗？**
项目专门做了防过度阻塞设计：When NOT to gate 白名单、风险分级、降级
重跑永远合法、简单事实简单检查，且每条 v3 新规则都配了防误伤正例
（异构交叉验证正例、历史声明正例、聚合源限定声明正例、机械通道正例）。
实测 FRR 为 0/14，诚实结论零误伤；改写不变性用例锁定同义改写不翻转判定。
如果你发现了误伤用例，欢迎提交语料——benchmark 存在的意义就在于此。

## 架构与仓库结构

完整的判定管线，以及每个模块的输入、输出、职责和失败情况，写在
[ARCHITECTURE.md](ARCHITECTURE.md) 里。

```
evidence-gate/
├── SKILL.md              # Agent 阅读的主文档（触发条件 + 闸门工作流）
├── scripts/gate_check.py # 确定性判定器（零依赖 Python）
├── references/           # 等级定义 / 判定矩阵 / 失效模式 / 风险分级
├── examples/             # 十四个带真实输出的示例
├── benchmark/            # 真值语料（core+adversarial）+ 运行器 + A/B 对照
│   └── legacy/           # v2.0.0 判定器快照（A/B 基线）
├── tests/                # 回归用例（含改写不变性）+ CLI 子测试 + skill 校验
└── .claude-plugin/       # Claude Code 插件清单（marketplace + plugin manifest）
```

## 参与贡献

PR 必须附带测试与全绿输出。如果修改核心判定规则，必须同时新增对应的
回归用例和 benchmark 语料。完整的流程、commit 规范与版本策略见
[CONTRIBUTING.md](CONTRIBUTING.md)；行为准则见
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)；安全问题请走私下渠道，见
[SECURITY.md](SECURITY.md)。

## License

[MIT](LICENSE) © Evidence Gate contributors。文中对研究文献的引用属于
事实性引用并附原始链接，不构成内容再分发。
