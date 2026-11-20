# 示例 9 · BAD / GOOD 对照：同一份数据，两种表述

**教训：BAD 不是数据造假，是措辞越权 —— 而闸门读的是结论文本，不是自评字段。**

同一份 QA 抽样记录（tests/fixtures/qa/records-2026-11-17.csv），两种交付表述。

## BAD（REJECT）

```json
{
  "conclusion": "100 万条数据 100% 全部合格，可以直接交付",
  "type": "FACT",
  "claimed_strength": "judged",
  "risk_tier": "medium",
  "evidence": [
    {
      "kind": "sample",
      "detail": "抽查 100 条无重复、字段完整（记录表 tests/fixtures/qa/records-2026-11-17.csv）",
      "anchor": "tests/fixtures/qa/records-2026-11-17.csv",
      "quote": "随机抽样 100 条：无重复、关键字段无空值",
      "content_supports": "supported",
      "group": "qa-sample"
    }
  ],
  "verification": {
    "executed": false,
    "detail": "",
    "env_independent": "unknown",
    "validates_target": "unknown"
  },
  "counter_evidence": [],
  "counter_search_context": "isolated",
  "evidence_obtainable": "yes",
  "generalization": {
    "sample_size": 100,
    "population_size": 1000000,
    "statistical_basis": false
  }
}
```

实际输出（节选）：

```text
Evidence Gate Result

Conclusion:
100 万条数据 100% 全部合格，可以直接交付
Type: FACT
Claimed strength: absolute  (risk: high)
Evidence Level: L2  (claim requires L4; independent lines: 1)
Evidence (anchor three-stage check):
  - [direct·mech✓] sample — quote verified in anchor: tests/fixtures/qa/records-2026-11-17.csv
  execution: executed=False valid=False env_independent=unknown validates_target=unknown channel=None
Counter-evidence search context: isolated
Findings:
  [high] ABSOLUTE_WORDING: absolute wording detected in conclusion; claimed_strength escalated 'judged' -> 'absolute'
  [high] SAMPLE_TO_POPULATION: generalizing a sample of 100 to a population of 1,000,000 without statistical basis: the sample cannot certify the whole
  [reject] ABSOLUTE_OVERREACH: absolute claim requires cross-validated evidence (L4); current evidence is L2. No amount of confidence justifies absolute wording — restate at allowed strength with explicit scope
Decision: REJECT  (exit 20)
Reason:
  absolute claim requires cross-validated evidence (L4); current evidence is L2. No amount of confidence justifies absolute wording — restate at allowed strength with explicit scope; absolute wording detected in conclusion; claimed_strength escalated 'judged' -> 'absolute'; generalizing a sample of 100 to a population of 1,000,000 without statistical basis: the sample cannot certify the whole
Allowed wording: 根据现有证据可以判断 (judged from evidence)
Calibration: levels are ordinal, not probabilities; empirical per-level accuracy via --calibration
Required actions:
  - scan the full population, or use a statistically valid sampling plan, or restate scoped to the sample (“100 sampled, no issues found; whole not verified”)
Verifier: {"id": "unspecified", "protocol": "gate_check/3.0.0", "entailment_channel": "mechanical", "independent_checks": {"valid_agreeing": 0, "cross_family_required": false, "cross_family_ok": null}}
```

**为什么错误**：① 结论文本含 “100%/全部” → ABSOLUTE_WORDING（字段填的 judged
被无视）；② generalization 100 → 1,000,000 无统计基础 → SAMPLE_TO_POPULATION；
③ absolute 要求 L4，证据 L2 → REJECT。错误不在抽查本身，在把抽查说成普查。

## GOOD（PASS）

```json
{
  "conclusion": "抽查的 100 条记录未发现重复或关键字段缺失；整体 100 万条未验证",
  "type": "FACT",
  "claimed_strength": "judged",
  "risk_tier": "high",
  "evidence": [
    {
      "kind": "sample",
      "detail": "QA 抽样记录（本地副本）",
      "anchor": "tests/fixtures/qa/records-2026-11-17.csv",
      "quote": "随机抽样 100 条：无重复、关键字段无空值",
      "content_supports": "supported",
      "group": "qa-sample"
    }
  ],
  "verification": {
    "executed": true,
    "detail": "运行去重与空值检查脚本于 100 条样本",
    "env_independent": true,
    "validates_target": true
  },
  "counter_evidence": [],
  "counter_search_context": "isolated",
  "evidence_obtainable": "yes",
  "generalization": null
}
```

实际输出（节选）：

```text
Evidence Gate Result

Conclusion:
抽查的 100 条记录未发现重复或关键字段缺失；整体 100 万条未验证
Type: FACT
Claimed strength: judged  (risk: high)
Evidence Level: L3  (claim requires L3; independent lines: 1)
Evidence (anchor three-stage check):
  - [direct·mech✓] sample — quote verified in anchor: tests/fixtures/qa/records-2026-11-17.csv
  execution: executed=True valid=True env_independent=True validates_target=True channel=None
Counter-evidence search context: isolated
Findings:
Decision: PASS  (exit 0)
Reason:
  evidence L3 supports claimed strength 'judged' (requires L3)
Allowed wording: 已通过实际验证 (verified)
Calibration: levels are ordinal, not probabilities; empirical per-level accuracy via --calibration
Verifier: {"id": "unspecified", "protocol": "gate_check/3.0.0", "entailment_channel": "mechanical", "independent_checks": {"valid_agreeing": 0, "cross_family_required": false, "cross_family_ok": null}}
```

**为什么正确**：① 措辞限定在样本内（“抽查的 100 条”），不使用 全部/均/100%；
② 明示“整体 100 万条未验证”，把不确定性交给读者；③ 抽样检查本身是执行过的
（executed=true 且 validates_target=true）→ L3。结论强度 ≤ 证据强度，通过。
