# Evidence Gate

**面向 AI Agent 的结论质量闸门（Agent Skill）：在 Agent 输出重要结论之前，
强制执行 证据核查 → 反证分析 → 验证要求 → 可信度分级，让结论强度不超过
证据强度。**

它不是一个"请认真检查"的提示词，而是一个可执行机制：结构化证据输入 +
确定性判定脚本（`gate_check.py`，Python 标准库、零依赖）+ 五类决策
（PASS / PASS_WITH_CAVEAT / VERIFY_REQUIRED / ABSTAIN / REJECT）+ 审计与校准回路。

> Evidence Gate 是**验证与质量控制机制**，不是正确性证明器。它降低"未经验证
> 的错误结论进入最终输出"的风险；它不保证结论正确（见 [Limitations](#limitations)）。

## Why Evidence Gate?

Agent 输出关键结论时有五类高频失效，每一类都*看起来*像验证过：

| 失效 | 样子 | 实质 |
|------|------|------|
| 推理冒充验证 | "我分析了代码，它能正常运行" | 阅读是 L2 证据；"正常运行"需要真的运行过 |
| 测试通过≠问题解决 | 套件全绿，关闭工单 | 测试可能从未覆盖那个 bug |
| 小样本冒充全量 | 抽查 100 条没问题 → "100 万条全部合格" | 样本不能证明总体 |
| 相关冒充因果 | 发布后错误率上升 → "新版本导致的" | 时间相关是间接证据 |
| 引用冒充支持 | 附了一个真实链接 | 实测约半数真实引用并不支持其结论（见 [docs/research-survey.md](docs/research-survey.md)） |

既有研究还表明：Agent 在不该回答的高风险问题上会硬答（实验中 59.5%），
同上下文的自我检查受"同意偏差"支配、加算力也不消失。Evidence Gate 把这些
结论变成了显式、机械、可审计的判定。

## Core Concept

```
规则 → 检查 → 判断 → 决策
```

三个核心规则，全部由脚本机械执行而非靠自觉：

1. **先验证再下结论** —— 能执行就执行、能查询就查询、能读源码就读源码；
2. **结论强度 ≤ 证据强度** —— L0–L4 证据等级映射措辞上限，脚本扫描结论
   *文本*（不是自评字段）识别绝对化措辞，字段撒谎会被抓；
3. **无法确认就明说** —— 证据不可得时输出 ABSTAIN（"目前无法确认"+缺口
   说明），而不是带保留的猜测。

### Evidence Levels（L0–L4）

| Level | 含义 | 措辞上限 |
|-------|------|----------|
| L0 | 无证据（猜测、记忆、"应该行"） | 假设/推测 |
| L1 | 间接信号（日志症状、时间相关、小样本） | 可能/初步判断 |
| L2 | 带锚点直接证据，且内容真的支持结论（引文机械核验） | 根据现有证据可以判断 |
| L3 | 实际执行并观察（跑过、测过） | 已通过实际验证 |
| L4 | ≥2 独立证据线一致 + 隔离反证搜寻 | 已交叉验证 |

### 五类决策

| Decision | 含义 | Agent 义务 |
|----------|------|-----------|
| PASS | 证据支撑 | 按允许措辞输出 |
| PASS_WITH_CAVEAT | 可输出但受限 | 强制附带上限条件 |
| VERIFY_REQUIRED | 证据不足 | 执行验证，或降级措辞重跑；不得原样输出 |
| ABSTAIN | 所需证据无法获得 | 说"目前无法确认"+缺口说明；禁止任何强度的猜测版 |
| REJECT | 结论不能成立 | 改写为限定措辞或放弃 |

Exit codes：`0` / `0` / `10` / `15` / `20`（输入错误 `2`），可直接接入 CI。

## How It Works

每条关键结论走一遍闸门循环（详见 [SKILL.md](SKILL.md)）：

```
1 IDENTIFY      提取结论，分类 FACT/INFERENCE/HYPOTHESIS/RECOMMENDATION/EXPERIMENT_RESULT
2 VERIFY FIRST  能执行就先执行，不靠推理
3 COLLECT       证据带锚点；引用过三关：锚点可解析 → 内容实读 → 引文在文中
4 FALSIFY       两步隔离反证：先写"什么能推翻我"（不看支持证据），再去搜
5 GATE          跑 scripts/gate_check.py
6 OBEY          服从决策：措辞上限、强制 caveat、验证动作
```

架构与各判定模块的输入/输出/失败情况见 [ARCHITECTURE.md](ARCHITECTURE.md)；
判定矩阵见 [references/decision-rules.md](references/decision-rules.md)。

## Installation

**依赖**：Python ≥ 3.8，仅标准库，零第三方依赖（CI 覆盖 3.9–3.13）。

**作为 Agent Skill 安装**（本仓库即 skill，SKILL.md 在根目录）：

```bash
# 通用：克隆/复制到你的 agent 运行时技能目录，例如
git clone https://github.com/fishzjp/evidence-gate.git ~/.agents/skills/evidence-gate
# Claude Code:   ~/.claude/skills/evidence-gate
# 项目级:        <project>/.agents/skills/evidence-gate
```

安装后 Agent 按 SKILL.md 的触发条件自动使用；也可以只把 SKILL.md 内容贴进
系统提示词，效果是流程性的（但会失去脚本机械核查）。

**作为独立 CLI 使用**（不需要 agent 框架）：

```bash
git clone https://github.com/fishzjp/evidence-gate.git && cd evidence-gate
python3 scripts/gate_check.py --help
```

## Quick Start

一分钟完成第一次判定。创建 `gate-input.json`（下例锚点用仓库内真实文件，
可直接复现）：

```json
{
  "conclusion": "foo-lib 的默认请求超时是 60 秒",
  "type": "FACT",
  "claimed_strength": "judged",
  "risk_tier": "medium",
  "evidence": [
    {"kind": "official_doc", "detail": "foo-lib 配置参考（本地副本）：timeout 默认 60 秒",
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

运行：

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

引文机械核验通过了（那行字真的在文件里），反证被核实排除，PASS。
如果引文写错成 "30 seconds"，同一命令会给出
`ANCHOR_QUOTE_MISSING` → 降级 → `VERIFY_REQUIRED (exit 10)` —— 亲手试一下。

## Examples

十个带**真实脚本输出**的完整示例（[examples/](examples/README.md)），覆盖全部
五类决策：事实判断 / 理论≠验证 / 小样本≠全量 / 相关≠因果 / 反证搜寻 /
引用≠支持 / ABSTAIN / 不可逆动作前置闸门 / BAD-vs-GOOD 对照 / 完整 Agent
工作流（Task→Reasoning→Gate→Verification→Answer）。

## Verification Flow

- **何时必须实际执行**：works/因果/EXPERIMENT_RESULT 声明、verified 措辞、
  高风险主题、不可逆动作前 —— 阅读永远是 L2。
- **锚点三段式**：锚点可解析 → 内容实读 → 引文支持；引文不在文件中即降级
  （"引用存在"只过了第一关）。
- **隔离反证**：cross_verified / 绝对化声明要求反证搜寻与结论不同上下文；
  同上下文搜索 → VERIFY_REQUIRED。
- **不可逆动作（G3）**：`--gate-point pre-action`，风险升档，"不会中断"类
  声明必须执行过。
- **审计与校准**：每次运行落 JSONL 日志（gate_id/决策/等级）；
  `--mark-outcome` 事后标记对错，`--calibration` 按等级统计真实准确率。

## Benchmark

**已测量（gate-level，确定性可复现）** —— [benchmark/RESULTS.md](benchmark/RESULTS.md)：

| 指标 | 结果（23 条真值标注语料） |
|------|--------------------------|
| Accuracy | 23/23 (100%) |
| False Acceptance Rate（应拦未拦） | 0/13 (0%) |
| False Rejection Rate（应放被拦） | 0/10 (0%) |
| 时延 | ~75 ms/条（含解释器启动，单机） |

局限：语料由维护者构造（存在构造者偏差）；测的是**闸门判定器**。

**未测量（agent-level）** —— baseline agent vs agent+gate 的端到端对比协议
已定义（[benchmark/AGENT-PROTOCOL.md](benchmark/AGENT-PROTOCOL.md)）但**尚未
运行**。因此本项目**不宣称**"提高 Agent 准确率"；设计目标是降低未经验证的
错误结论进入最终输出的风险。

复现：`python3 benchmark/run_benchmark.py`（FAR/FRR 非零即 exit 1，可作 CI 门禁）。

## Limitations

必须先读这部分再看上面的一切：

1. **不能保证绝对正确。** 闸门判定的是*结论强度与证据结构的匹配*，不是
   结论与事实的一致。所有证据都指向 A 而 A 为假时，闸门会放行一个精心
   措辞的错误结论。
2. **证据本身可能错误。** 文档会过时，源码有 bug，基准数据可能被污染。
   L2/L3 措辞（"根据现有证据"）正是为此保留的谦逊。
3. **验证器也会犯错。** 判定规则是启发式（关键词、引文匹配、等级算术），
   存在误报与漏报（已知：中文绝对化关键词的边界措辞可能误触发；实测
   FAR/FRR 为 0 但语料有构造者偏差）。
4. **同模型验证存在相关性失效。** 隔离反证要求缓解同意偏差，但同一模型
   的先验会同时污染支持面与反证面 —— 这是缓解，不是根除。
5. **验证有成本。** 每条关键结论多一次脚本运行（~75ms）+ 填写输入的
   token/时间；过度验证浪费，欠验证危险，风险分级就是为了花对地方。
6. **有些事实无法用现有工具验证**（权限、不可复现事件、数据不可及）。
   此时正确行为是 ABSTAIN，而不是闸门逼出一个猜测。
7. **不替代形式化验证。** 它不证明程序正确性、不证明定理；对可形式化的
   性质请用模型检查器/定理证明器。
8. **Evidence Level 不是概率置信度。** L0–L4 是措辞天花板（序数），不是
   校准过的 P(正确)。校准回路（`--calibration`）是被动闭环，需要事后
   outcome 数据，冷启动阶段不构成约束。

另有一条结构性边界：**自报字段可以被撒谎**（`content_supports`、
`counter_search_context`）。脚本把谎言变成显式、可审计、可校准的记录 ——
这是任何静态闸门的能力边界。

## Architecture

判定管线、每个模块的输入/输出/职责/失败情况：
[ARCHITECTURE.md](ARCHITECTURE.md)。设计依据的 2024–2026 文献调研（引用
逐条核实）：[docs/research-survey.md](docs/research-survey.md)。

## Tests & Regression

```bash
python3 tests/run_tests.py --report    # 14 个回归用例 + 3 个 CLI 子测试
python3 benchmark/run_benchmark.py    # 23 条真值语料（FAR/FRR 门禁）
```

回归重点：修改规则不得让原本 REJECT 的错误结论变成 PASS（FAR 门禁），
也不得把诚实结论全部拦截（FRR 门禁）。

## Contributing

PR 必须附带测试与全绿输出；**修改核心判定规则必须同时新增对应回归用例
与 benchmark 语料**。流程与规范见 [CONTRIBUTING.md](CONTRIBUTING.md)；
行为准则见 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。

## License

[MIT](LICENSE) © Evidence Gate contributors。第三方引用（研究文献）仅为
事实性引用并附原始链接，不构成内容再分发。
