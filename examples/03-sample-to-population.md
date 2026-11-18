# 示例 3 · 数据质量：小样本通过 ≠ 全量合格

**教训：抽查 100 条说明不了 100 万条；“100%/全部”措辞自动升级为绝对化声明。**

QA 抽查了 100 万条记录中的 100 条，没有发现问题。Agent 起草的交付结论是“100 万条数据 100% 全部合格”。注意：`claimed_strength` 填的是 judged —— 字段在撒谎，闸门扫描的是结论文本。

## 闸门输入（gate-input.json）

```json
{
  "conclusion": "抽检 100 条数据没有发现问题，所以 100 万条数据 100% 全部合格",
  "type": "INFERENCE",
  "claimed_strength": "judged",
  "risk_tier": "medium",
  "evidence": [
    {
      "kind": "sample",
      "detail": "随机抽样 100 条人工检查（QA 记录表 tests/fixtures/qa/records-2026-11-17.csv）",
      "group": "qa-sample",
      "anchor": "tests/fixtures/qa/records-2026-11-17.csv",
      "quote": "无重复、关键字段无空值"
    }
  ],
  "verification": {
    "executed": false,
    "detail": "",
    "env_independent": "unknown",
    "validates_target": "unknown"
  },
  "counter_evidence": [],
  "generalization": {
    "sample_size": 100,
    "population_size": 1000000,
    "statistical_basis": false
  }
}
```

## 实际运行输出（真实输出节选）

```text
Evidence Gate Result
Conclusion:
Type: INFERENCE
Claimed strength: absolute  (risk: high)
Evidence Level: L2  (claim requires L4)
Evidence (anchor three-stage check):
  - [direct·mech✓] sample — quote verified in anchor: tests/fixtures/qa/records-2026-11-17.csv
  execution: executed=False valid=False env_independent=unknown validates_target=unknown
Counter-evidence search context: same
Findings:
Confidence: LOW
Decision: REJECT  (exit 20)
Reason:
Allowed wording: 根据现有证据可以判断 (judged from evidence)
Required actions:
  - rerun the counter-evidence search in an isolated context (fresh session without the conclusion, or an independent agent), or attempt mechanical falsification
  - scan the full population, or use a statistically valid sampling plan, or restate scoped to the sample (“100 sampled, no issues found; whole not verified”)
Verifier: {"id": "unspecified", "protocol": "gate_check/2.0.0", "entailment_channel": "mechanical"}
```

## 服从决策后应这样表述

**“抽查的 100 条记录未发现重复或关键字段缺失；整体 100 万条未验证。”**（完整可过的对照输入见示例 9 的 GOOD 版本）

## 为什么

三层拦截同时触发：①“100%/全部”触发 ABSOLUTE_WORDING，字段声明的 judged 被忽略，按 absolute 判定；② SAMPLE_TO_POPULATION：样本 100 → 总体 1,000,000 无统计基础；③ absolute 要求 L4，证据只有 L2 → REJECT。救济永远是改措辞或补验证（全量扫描一条 SQL 的事）。
