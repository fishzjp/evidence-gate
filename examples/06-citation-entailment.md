# 示例 6 · 引用蕴含：有引用 ≠ 引用支持结论

**教训：引用存在且真实，但引用的内容说的是 60 秒不是 30 秒 —— 引文核验拦住了它。**

Agent 引用了一份真实存在的文档（tests/fixtures/docs/api-timeout.md）来支撑“默认超时 30 秒”。文档是真的，引用是错的：文档写的是 60 秒。

## 闸门输入（gate-input.json）

```json
{
  "conclusion": "foo-lib 的默认超时是 30 秒，官方文档明确写明",
  "type": "FACT",
  "claimed_strength": "judged",
  "risk_tier": "medium",
  "evidence": [
    {
      "kind": "official_doc",
      "detail": "foo-lib 配置参考（本地副本 tests/fixtures/docs/api-timeout.md），文档写明 default timeout is 30 seconds",
      "group": "foo-docs",
      "anchor": "tests/fixtures/docs/api-timeout.md",
      "quote": "default timeout is 30 seconds"
    }
  ],
  "verification": {
    "executed": false,
    "detail": "",
    "env_independent": "unknown",
    "validates_target": "unknown"
  },
  "counter_evidence": [],
  "generalization": null
}
```

## 实际运行输出（真实输出节选）

```text
Evidence Gate Result

Conclusion:
foo-lib 的默认超时是 30 秒，官方文档明确写明
Type: FACT
Claimed strength: judged  (risk: medium)
Evidence Level: L1  (claim requires L2; independent lines: 0)
Evidence (anchor three-stage check):
  - [indirect*] official_doc — anchor resolved but does NOT contain the quoted support “default timeout is 30 seconds”: tests/fixtures/docs/api-timeout.md
  execution: executed=False valid=False env_independent=unknown validates_target=unknown channel=None
Counter-evidence search context: same
Findings:
  [high] ANCHOR_QUOTE_MISSING: citation does not support the claim — anchor resolved but does NOT contain the quoted support “default timeout is 30 seconds”: tests/fixtures/docs/api-timeout.md
Decision: VERIFY_REQUIRED  (exit 10)
Reason:
  citation does not support the claim — anchor resolved but does NOT contain the quoted support “default timeout is 30 seconds”: tests/fixtures/docs/api-timeout.md; claimed strength 'judged' requires L2, evidence is only L1: conclusion strength exceeds evidence strength — execute the actual verification (run it), or downgrade the wording to the allowed strength and rerun the gate
Allowed wording: 可能/初步判断 (possibly / preliminary)
Calibration: levels are ordinal, not probabilities; empirical per-level accuracy via --calibration
Mandatory caveats (must appear in output):
  - counter-evidence search was same-context; coverage may be limited by agreement bias
Required actions:
  - locate an authoritative source (official docs, source code, config, data) and cite it with a resolvable anchor + quote
Verifier: {"id": "unspecified", "protocol": "gate_check/3.0.0", "entailment_channel": "none", "independent_checks": {"valid_agreeing": 0, "cross_family_required": false, "cross_family_ok": null}}
```

## 服从决策后应这样表述

先不改措辞 —— 先重读文档。修正后：**“默认超时是 60 秒（docs/api-timeout.md）”**并以正确引文重过闸门（即示例 1）。

## 为什么

这是 v2 的核心机制（锚点三段式第三段）：脚本打开文件比对引文，“default timeout is 30 seconds” 不在文件中 → ANCHOR_QUOTE_MISSING → 证据降级 direct→indirect → L1 < L2 → VERIFY_REQUIRED。实测约半数真实引用并不支持其结论，引用存在只完成了三段中的第一段。
