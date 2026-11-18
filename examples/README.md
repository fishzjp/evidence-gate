# Examples — 十个带真实输出的示例

每个示例 = 场景 + 完整闸门输入 JSON + **脚本真实运行输出（节选）** + 服从决策后的
正确表述 + 原因。所有输出均为 `scripts/gate_check.py` 实际打印内容，可复现
（输入 JSON 即 benchmark 语料或示例内嵌，锚点文件在 `tests/fixtures/`）。

| # | 文件 | 场景 | 核心教训 | 决策 |
|---|------|------|----------|------|
| 1 | [01-fact-check.md](01-fact-check.md) | 事实判断 | 带锚点引文的事实声明；反证核实排除 | PASS |
| 2 | [02-theory-vs-verified.md](02-theory-vs-verified.md) | 技术结论 | 理论上可行 ≠ 已实际验证 | VERIFY_REQUIRED |
| 3 | [03-sample-to-population.md](03-sample-to-population.md) | 数据质量 | 小样本通过 ≠ 全量合格 | REJECT |
| 4 | [04-causal.md](04-causal.md) | 因果推理 | 相关性 ≠ 因果关系 | VERIFY_REQUIRED |
| 5 | [05-counter-evidence.md](05-counter-evidence.md) | 反证搜寻 | 主动找反例（在同一份数据里找到） | REJECT |
| 6 | [06-citation-entailment.md](06-citation-entailment.md) | 引用蕴含 | 有引用 ≠ 引用支持结论 | VERIFY_REQUIRED |
| 7 | [07-abstention.md](07-abstention.md) | 弃权 | 证据不可得 → 说“无法确认” | ABSTAIN |
| 8 | [08-high-risk-preaction.md](08-high-risk-preaction.md) | 高风险/不可逆 | pre-action 模式：必须实际执行 | VERIFY_REQUIRED |
| 9 | [09-bad-good.md](09-bad-good.md) | BAD/GOOD 对照 | 同一数据两种表述；字段撒谎被文本扫描识破 | REJECT → PASS |
| 10 | [10-agent-workflow.md](10-agent-workflow.md) | 完整工作流 | Task → 推理 → 闸门 → 验证 → 最终回答 | VERIFY_REQUIRED → PASS |

覆盖全部五类决策：PASS / PASS_WITH_CAVEAT（见 1、9-GOOD）/ VERIFY_REQUIRED /
ABSTAIN / REJECT。

## 亲手复现

语料文件带标注 wrapper（`id`/`expectation`/`input`），先取出 `input`：

```bash
# 任意示例（以示例 1 为例）：
cat benchmark/corpus/p01-fact-anchored.json | python3 -c \
  "import json,sys; print(json.dumps(json.load(sys.stdin)['input']))" | \
  python3 scripts/gate_check.py -

# 示例 8 需要 pre-action 模式：
cat benchmark/corpus/b11-pre-action-unexecuted.json | python3 -c \
  "import json,sys; print(json.dumps(json.load(sys.stdin)['input']))" | \
  python3 scripts/gate_check.py --gate-point pre-action -
```
