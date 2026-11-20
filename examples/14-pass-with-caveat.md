# 示例 14 · 带强制保留的放行：结论成立，但边界必须说出口

**教训：PASS_WITH_CAVEAT = 证据撑得起结论、撑得起的前提是保留条件必须出现在输出里。**

有了解释过的反证（status=explained）时，闸门不放行"干净版本"的结论，而是放行 + 强制保留。这与 VERIFY_REQUIRED 的区别：证据等级够、不需要更多验证，但已知边界必须随结论一起说出，否则读者拿到的是被剪裁过的结论。

## 闸门输入（benchmark/corpus/p06-recommendation-conditioned.json）

```json
{
  "conclusion": "若 P95 需稳定低于 200ms，建议保留缓存层并为其增加预热任务",
  "type": "RECOMMENDATION",
  "claimed_strength": "judged",
  "risk_tier": "medium",
  "evidence": [
    {
      "kind": "data",
      "detail": "上线后两周 P95 稳定在 178-181ms（本地副本 metrics 表）",
      "anchor": "tests/fixtures/metrics/p95-2026-11.csv",
      "quote": "after cache layer",
      "content_supports": "supported",
      "group": "metrics"
    }
  ],
  "verification": {
    "executed": false,
    "detail": "",
    "env_independent": "unknown",
    "validates_target": "unknown"
  },
  "counter_evidence": [
    {
      "detail": "缓存层带来一致性维护成本，需权衡",
      "status": "explained",
      "contradicts": false
    }
  ],
  "counter_search_context": "isolated",
  "evidence_obtainable": "yes",
  "generalization": null
}
```

## 实际运行输出（`--offline`，PASS_WITH_CAVEAT）

```text
Evidence Gate Result

Conclusion:
若 P95 需稳定低于 200ms，建议保留缓存层并为其增加预热任务
Type: RECOMMENDATION
Claimed strength: judged  (risk: medium)
Evidence Level: L2  (claim requires L2; independent lines: 1)
Evidence (anchor three-stage check):
  - [direct·mech✓] data — quote verified in anchor: tests/fixtures/metrics/p95-2026-11.csv
  execution: executed=False valid=False env_independent=unknown validates_target=unknown channel=None
Counter-evidence search context: isolated
Findings:
Decision: PASS_WITH_CAVEAT  (exit 0)
Reason:
  pass with mandatory caveats: evidence L2 supports claimed strength 'judged' (requires L2)
Allowed wording: 根据现有证据可以判断 (judged from evidence)
Calibration: levels are ordinal, not probabilities; empirical per-level accuracy via --calibration
Mandatory caveats (must appear in output):
  - boundary condition (from counter-evidence): 缓存层带来一致性维护成本，需权衡
Verifier: {"id": "unspecified", "protocol": "gate_check/3.0.0", "entailment_channel": "mechanical", "independent_checks": {"valid_agreeing": 0, "cross_family_required": false, "cross_family_ok": null}}
```

## 服从决策后应这样表述

**"若 P95 需稳定低于 200ms，建议保留缓存层并为其增加预热任务（上线后两周 P95 稳定在 178–181ms）。注意：缓存层带来一致性维护成本，需权衡。"** —— 保留条件不是脚注，是结论的一部分。

## 为什么

反证的 status 决定走向：`unaddressed` + contradictions → REJECT/VERIFY_REQUIRED（FACT 直接 REJECT）；`explained` → 结论可以输出，但解释必须随行（Mandatory caveats）。exit code 与 PASS 相同（都是 0），区别全在输出结构 —— 调用方（Agent/CI）若吞掉 caveats 字段，等于放弃了这层保护。这是"结论强度 ≤ 证据强度"的措辞面：证据支持的是带边界条件的那个结论，不是剪掉边界后的版本。
