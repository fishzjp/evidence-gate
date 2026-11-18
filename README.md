# Evidence Gate

[![CI](https://github.com/fishzjp/evidence-gate/actions/workflows/ci.yml/badge.svg)](https://github.com/fishzjp/evidence-gate/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Dependencies](https://img.shields.io/badge/dependencies-0-green.svg)](#安装)

> A deterministic conclusion-quality gate for AI agents — evidence levels,
> counter-evidence checks, and wording ceilings enforced **before** a
> conclusion ships.

**面向 AI Agent 的结论质量闸门（Agent Skill）：在重要结论出口之前，强制走
证据核查 → 反证分析 → 验证要求 → 可信度分级，让结论强度不超过证据强度。**

它不是一段"请认真检查"的提示词，而是一个可执行机制：结构化证据 JSON +
确定性判定脚本（`gate_check.py`，Python 标准库、零依赖、~75ms）+ 五类决策
+ 审计与校准回路。

> Evidence Gate 是**验证与质量控制机制**，不是正确性证明器 —— 它降低
> "未经验证的错误结论进入最终输出"的风险，不保证结论正确
> （[Limitations](#limitations必须先读)）。

## 30 秒看懂

同一个 agent，同一份数据（抽查了 100 万条中的 100 条）：

```text
闸门前   "100 万条数据 100% 全部合格，可以直接交付。"     ← 样本冒充总体
                ↓ scripts/gate_check.py
闸门后   "抽查的 100 条未发现重复或字段缺失；              ← 强度≤证据
          整体 100 万条未验证。"                            + 缺口明示
                ↓ 若证据根本拿不到（而不是懒得查）
        "目前无法确认：……（缺口与原因）"                    ← ABSTAIN
```

闸门到底拦了什么：结论文本里的 "100%/全部" 被机械识别（**不信任自评字段**
——你把强度填成 `judged` 也没用），样本→总体无统计基础被拦，绝对化措辞
要求 L4 证据。放行的条件不是"更谦虚的语气"，是**证据真的够**。

## 目录

- [为什么需要](#为什么需要-evidence-gate)
- [核心机制](#核心机制)
- [安装](#安装)
- [快速开始](#快速开始)
- [十个示例](#示例)
- [CLI 速查](#cli-速查)
- [Benchmark](#benchmark)
- [局限（必须先读）](#limitations必须先读)
- [FAQ](#faq)
- [架构与仓库结构](#架构与仓库结构)
- [参与贡献](#参与贡献) · [License](#license)

## 为什么需要 Evidence Gate？

Agent 输出关键结论时有五类高频失效，每一类都*看起来*像验证过：

| 失效 | 样子 | 实质 |
|------|------|------|
| 推理冒充验证 | "我分析了代码，它能正常运行" | 阅读是 L2 证据；"正常运行"需要真的运行过 |
| 测试通过≠问题解决 | 套件全绿，关闭工单 | 测试可能从未覆盖那个 bug |
| 小样本冒充全量 | 抽查 100 条没问题 → "100 万条全部合格" | 样本不能证明总体 |
| 相关冒充因果 | 发布后错误率上升 → "新版本导致的" | 时间相关是间接证据 |
| 引用冒充支持 | 附了一个真实链接 | 实测约半数真实引用并不支持其结论 |

这不是态度问题，是机制问题。2024–2026 的研究结论（引用逐条核实，见
[docs/research-survey.md](docs/research-survey.md)）：

- **自我验证靠不住**：没有外部反馈时，让模型自查自己的答案几乎无增益
  （Huang et al., ICLR 2024）；
- **同上下文反证搜寻被"同意偏差"支配**：边看着结论边找反例，加再多算力
  也找不到（SGV, ICLR 2026）；
- **引用存在 ≠ 引用支持**：对真实 agent 引用的实测中，51.5% 的网络引用
  被误用，医学场景 50–90% 不支持或仅部分支持（Stanford 2024 / SourceCheckup 2025）；
- **agent 会在不该答的问题上硬答**：实验中 59.5% 的高风险不可答问题被
  莽撞作答（AgentAbstain 2025）。

所以 Evidence Gate 把"请仔细"换成**结构**：LM 提议（填结构化输入），确定性
检查器裁决（脚本机械核查），这是 AlphaProof 等已验证有效的分工。

## 核心机制

三条核心规则，全部由脚本机械执行而非靠自觉：

1. **先验证再下结论** —— 能执行就执行、能查询就查询、能读源码就读源码；
2. **结论强度 ≤ 证据强度** —— L0–L4 证据等级映射措辞上限；脚本扫描结论
   *文本*识别绝对化/因果/"可以运行"类声明，字段撒谎会被抓；
3. **无法确认就明说** —— 证据不可得时 ABSTAIN（"目前无法确认"+缺口），
   而不是带保留的猜测。

每条关键结论走一遍闸门循环（Agent 侧职责 + 脚本侧判定，详见
[SKILL.md](SKILL.md)）：

```
Agent 侧                                脚本侧（确定性）
────────                                ──────────────
1 IDENTIFY   结论分类                    ① 文本扫描：绝对化/因果/works/风险
2 VERIFY     能执行就先执行              ② 锚点三段式：解析→实读→引文在文中
3 COLLECT    证据带锚点+引文             ③ 验证有效性：跑过×环境干净×测对目标
4 FALSIFY    隔离反证搜寻                ④ 等级推导 L0–L4 与所需等级
5 GATE       跑脚本       ─────────────→ ⑤ 反证/隔离/样本→总体检查
6 OBEY       服从决策                    ⑥ 五类决策（按序求值）+ 审计日志
```

### 证据等级 L0–L4 → 措辞上限

| Level | 含义 | 措辞上限 |
|-------|------|----------|
| L0 | 无证据（猜测、记忆、"应该行"） | 假设/推测 |
| L1 | 间接信号（日志症状、时间相关、小样本） | 可能/初步判断 |
| L2 | 带锚点直接证据，且内容真的支持（引文机械核验） | 根据现有证据可以判断 |
| L3 | 实际执行并观察（跑过、测过） | 已通过实际验证 |
| L4 | ≥2 独立证据线一致 + 隔离反证搜寻 | 已交叉验证 |

### 五类决策

| Decision | 含义 | Agent 义务 | exit |
|----------|------|-----------|------|
| PASS | 证据支撑 | 按允许措辞输出 | 0 |
| PASS_WITH_CAVEAT | 可输出但受限 | 强制附带上限条件 | 0 |
| VERIFY_REQUIRED | 证据不足 | 执行验证，或降级措辞重跑；不得原样输出 | 10 |
| ABSTAIN | 所需证据无法获得 | 说"目前无法确认"+缺口；禁止任何猜测版 | 15 |
| REJECT | 结论不能成立 | 改写为限定措辞或放弃 | 20 |

输入错误 exit 2。非零码可直接接入 CI 断言。

### 四个进阶机制

- **锚点三段式** —— 引用要过三关：锚点可解析 → 内容实读 → 引文真的在
  文中（本地文件机械比对）。只过第一关的"引用存在"会被降级。
- **隔离反证要求** —— cross_verified / 绝对化声明的反证搜寻必须与结论
  不同上下文（先写"什么能推翻我"，不看支持证据，再去找）；同上下文
  搜索 → VERIFY_REQUIRED。
- **不可逆动作前置闸门（G3）** —— `--gate-point pre-action`：风险升档，
  "不会中断"类声明必须实际演练过，PASS_WITH_CAVEAT 降为 VERIFY_REQUIRED。
- **审计与校准回路** —— 每次运行落 JSONL 日志（gate_id/决策/等级）；
  `--mark-outcome` 事后标记对错，`--calibration` 按等级统计真实准确率
  （自报等级的绝对映射不可信，直到测量）。

## 安装

**依赖**：Python 3.10+，仅标准库，零第三方依赖（CI 矩阵 3.10–3.13）。

**作为 Agent Skill**（本仓库即 skill，[SKILL.md](SKILL.md) 在根目录）：

```bash
# 克隆/复制到你的 agent 运行时技能目录，例如：
git clone https://github.com/fishzjp/evidence-gate.git ~/.agents/skills/evidence-gate
# Claude Code:  ~/.claude/skills/evidence-gate
# 项目级:       <project>/.agents/skills/evidence-gate
```

安装后 Agent 按 SKILL.md 触发条件自动使用。也可只把 SKILL.md 贴进系统
提示词（保留流程指引，但失去脚本机械核查）。

**作为独立 CLI**（不需要任何 agent 框架）：

```bash
git clone https://github.com/fishzjp/evidence-gate.git && cd evidence-gate
python3 scripts/gate_check.py --help
```

## 快速开始

一分钟完成第一次判定。创建 `gate-input.json`（锚点是仓库内真实文件，
可直接复现）：

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

```bash
python3 scripts/gate_check.py gate-input.json
```

输出（真实输出节选）：

```text
Evidence Level: L2  (claim requires L2)
Evidence (anchor three-stage check):
  - [direct·mech✓] official_doc — quote verified in anchor: tests/fixtures/docs/api-timeout.md
Decision: PASS  (exit 0)
Allowed wording: 根据现有证据可以判断 (judged from evidence)
```

引文机械核验通过（那行字真的在文件里），反证被核实排除，PASS。
**亲手试一下**：把引文改成 `"default timeout is 30 seconds"` 再跑 ——
同一命令会给出 `ANCHOR_QUOTE_MISSING` → 证据降级 → `VERIFY_REQUIRED
(exit 10)`。这就是"引用存在 ≠ 引用支持"的机械执行。

## 示例

十个带**真实脚本输出**的完整示例（[examples/](examples/README.md)），覆盖
全部五类决策：

| 主题 | 教训 |
|------|------|
| [事实判断](examples/01-fact-check.md) | 带锚点引文的事实声明（PASS） |
| [技术结论](examples/02-theory-vs-verified.md) | 理论上可行 ≠ 已实际验证 |
| [数据质量](examples/03-sample-to-population.md) | 小样本通过 ≠ 全量合格 |
| [因果推理](examples/04-causal.md) | 相关性 ≠ 因果关系 |
| [反证搜寻](examples/05-counter-evidence.md) | 在自己的数据里找到反例 |
| [引用蕴含](examples/06-citation-entailment.md) | 有引用 ≠ 引用支持结论 |
| [弃权](examples/07-abstention.md) | 证据不可得 → "无法确认" |
| [高风险/不可逆](examples/08-high-risk-preaction.md) | pre-action 闸门 |
| [BAD vs GOOD](examples/09-bad-good.md) | 同一数据两种表述（REJECT→PASS） |
| [完整工作流](examples/10-agent-workflow.md) | Task→Reasoning→Gate→验证→Answer |

## CLI 速查

```bash
python3 scripts/gate_check.py <input.json>          # 人类可读结果
... | python3 scripts/gate_check.py --json -        # 机器可读（CI）
... | python3 scripts/gate_check.py --gate-point pre-action -   # 不可逆动作前
... | python3 scripts/gate_check.py --offline -     # 不抓 URL（离线/敏感网络）
python3 scripts/gate_check.py --no-log ...          # 一次性运行不落日志
python3 scripts/gate_check.py --log PATH ...        # 独立日志文件
python3 scripts/gate_check.py --mark-outcome <gate_id> correct|wrong   # 校准回路
python3 scripts/gate_check.py --calibration         # 按等级的真实准确率表
```

开发与回归：

```bash
python3 tests/run_tests.py --report     # 14 个回归用例 + 3 个 CLI 子测试
python3 benchmark/run_benchmark.py      # 23 条真值语料（FAR/FRR 门禁）
python3 tests/validate_skill.py         # SKILL.md 结构与引用完整性
```

## Benchmark

**已测量（gate-level，确定性、可复现）** —— [benchmark/RESULTS.md](benchmark/RESULTS.md)：

| 指标 | 结果（23 条真值标注语料） |
|------|--------------------------|
| Accuracy | 23/23 (100%) |
| **False Acceptance Rate**（应拦未拦，过度声明流出） | 0/13 (0%) |
| **False Rejection Rate**（应放被拦，误伤诚实结论） | 0/10 (0%) |
| 时延 | ~75 ms/条（含解释器启动，单机） |

复现：`python3 benchmark/run_benchmark.py`（FAR/FRR 非零即 exit 1，是 CI
门禁）。局限：语料由维护者构造（构造者偏差），测的是**闸门判定器**本身。

**未测量（agent-level）** —— baseline agent vs agent+gate 的端到端对比
协议已定义（[benchmark/AGENT-PROTOCOL.md](benchmark/AGENT-PROTOCOL.md)）但
**尚未运行**。因此本项目**不宣称**"提高 Agent 准确率"——设计目标是降低
未经验证的错误结论进入最终输出的风险。

## Limitations（必须先读）

1. **不能保证绝对正确。** 闸门判定的是*结论强度与证据结构的匹配*，不是
   结论与事实的一致。所有证据都指向 A 而 A 为假时，闸门会放行一个精心
   措辞的错误结论。
2. **证据本身可能错误。** 文档会过时，源码有 bug，基准数据可能被污染。
   L2/L3 措辞（"根据现有证据"）正是为此保留的谦逊。
3. **验证器也会犯错。** 判定规则是启发式（关键词、引文匹配、等级算术），
   存在误报与漏报（已知：中文绝对化关键词的边界措辞可能误触发；实测
   FAR/FRR 为 0 但语料有构造者偏差）。
4. **同模型验证存在相关性失效。** 隔离反证缓解同意偏差，但同一模型的
   先验会同时污染支持面与反证面 —— 是缓解，不是根除。
5. **验证有成本。** 每条关键结论多一次脚本运行（~75ms）+ 填写输入的
   token/注意力；过度验证浪费、欠验证危险，风险分级就是为了花对地方。
6. **有些事实无法用现有工具验证**（权限、不可复现事件、数据不可及）。
   此时正确行为是 ABSTAIN，而不是闸门逼出一个猜测。
7. **不替代形式化验证。** 不证明程序正确性、不证明定理；可形式化的性质
   请用模型检查器/定理证明器。
8. **Evidence Level 不是概率置信度。** L0–L4 是措辞天花板（序数），不是
   校准过的 P(正确)。校准回路是被动闭环，冷启动阶段不构成约束。

结构性边界：**自报字段可以被撒谎**（`content_supports`、
`counter_search_context`）。脚本把谎言变成显式、可审计、可校准的记录 ——
这是任何静态闸门的能力边界（[ARCHITECTURE.md](ARCHITECTURE.md) 末节
"已知设计取舍"）。

## FAQ

**会显著拖慢 agent 吗？**
脚本本身 ~75ms/条；主要成本是填写结构化输入的注意力。所以闸门按风险
分级：低风险结论只对照措辞表，不跑脚本（SKILL.md "When NOT to gate"）。

**支持哪些 agent 框架？**
框架无关：任何能执行 shell 命令、能读 Markdown 的 agent（ZCode、Claude
Code、通用 CLI agent…）都能用；不需要任何运行时集成。也可以完全不用
agent，纯 CLI 人工过闸。

**中文结论支持吗？**
支持。绝对化/因果/"可以运行"类关键词扫描覆盖中英文，措辞上限表是双语
的（`假设/推测` ~ `已交叉验证`）。

**已经有 verification-before-completion 类 skill，还需要这个吗？**
互补而非替代：闸门提供它们缺少的机械判定器、结构化证据格式和审计
回路，可以直接作为其执行层（SKILL.md "Combining with other skills"）。

**为什么不直接在提示词里写"请仔细验证再回答"？**
因为研究反复证明这无效：没有外部反馈的自我验证不产生增益，同上下文
自我批评被同意偏差支配。"请仔细"改变语气，"确定性脚本 + 结构化输入"
改变行为。

**它会让 agent 变得过度谨慎吗？**
有专门的防过度阻塞设计：When NOT to gate 白名单、风险分级、降级重跑
永远合法、简单事实简单检查。实测 FRR 0/10（诚实结论零误伤）；若你发现
误伤用例，欢迎提交语料（这就是 benchmark 存在的原因）。

## 架构与仓库结构

判定管线与每个模块的输入/输出/职责/失败情况：
[ARCHITECTURE.md](ARCHITECTURE.md)。设计依据的文献调研（引用逐条核实）：
[docs/research-survey.md](docs/research-survey.md)。

```
evidence-gate/
├── SKILL.md              # Agent 读的主文档（触发条件 + 闸门工作流）
├── scripts/gate_check.py # 确定性判定器（零依赖 Python）
├── references/           # 等级定义 / 判定矩阵 / 失效模式 / 风险分级
├── examples/             # 10 个带真实输出的示例
├── benchmark/            # 23 条真值语料 + 运行器 + agent 级协议
├── tests/                # 14 个回归用例 + CLI 子测试 + skill 校验
└── docs/research-survey.md
```

## 参与贡献

PR 必须附测试与全绿输出；**修改核心判定规则必须同时新增回归用例与
benchmark 语料**。流程、commit 规范与 SemVer 策略见
[CONTRIBUTING.md](CONTRIBUTING.md)；行为准则见
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。安全相关问题请走私下渠道：
[SECURITY.md](SECURITY.md)。

## License

[MIT](LICENSE) © Evidence Gate contributors。第三方引用（研究文献）仅为
事实性引用并附原始链接，不构成内容再分发。
