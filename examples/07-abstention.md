# 示例 7 · 弃权：证据不可得时说“无法确认”

**教训：当决定性证据无法获得时，正确答案是 ABSTAIN（说明缺口），不是带保留的猜测。**

“生产环境 payments_v2 flag 现在是开是关？” —— Agent 没有生产配置系统访问权限，唯一的依据是上周听值班同事说了一句。`evidence_obtainable: no`。

## 闸门输入（gate-input.json）

```json
{
  "conclusion": "生产环境当前生效的 feature-flag payments_v2 是开启状态",
  "type": "FACT",
  "claimed_strength": "judged",
  "risk_tier": "medium",
  "evidence_obtainable": "no",
  "evidence": [
    {
      "kind": "memory",
      "detail": "上周听值班同事说这个 flag 已经开了"
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
生产环境当前生效的 feature-flag payments_v2 是开启状态
Type: FACT
Claimed strength: judged  (risk: medium)
Evidence Level: L1  (claim requires L2; independent lines: 0)
Evidence (anchor three-stage check):
  - [indirect] memory — 上周听值班同事说这个 flag 已经开了
  execution: executed=False valid=False env_independent=unknown validates_target=unknown channel=None
Counter-evidence search context: same
Findings:
  [info] NON_EVIDENCE_KIND: evidence kind 'memory' is not evidence, only a prior (L0/L1 at most)
Decision: ABSTAIN  (exit 15)
Reason:
  required evidence is not obtainable (evidence_obtainable='no'): conclusion cannot be confirmed or denied here — abstain and state the gap
Allowed wording: 目前无法确认 (cannot confirm) — state the gap
Calibration: levels are ordinal, not probabilities; empirical per-level accuracy via --calibration
Mandatory caveats (must appear in output):
  - counter-evidence search was same-context; coverage may be limited by agreement bias
Required actions:
  - state the gap explicitly: “目前无法确认” + what evidence is missing and who can provide it; do not output the conclusion at any strength
Verifier: {"id": "unspecified", "protocol": "gate_check/3.0.0", "entailment_channel": "none", "independent_checks": {"valid_agreeing": 0, "cross_family_required": false, "cross_family_ok": null}}
```

## 服从决策后应这样表述

**“目前无法确认生产环境 payments_v2 的当前状态：我没有生产配置系统的访问权限，唯一依据是同事上周的口头说法（不可作为证据）。需要 SRE 查询配置中心或提供只读快照。”**

## 为什么

ABSTAIN 与降级不同：降级是“证据弱但有，用弱措辞”；ABSTAIN 是“决定性证据不存在且拿不到，任何措辞都不该输出”。带保留的猜测（“应该是开的”）会诱导读者以为这个问题本可以回答。研究显示 agent 在不该答的问题上硬答比例很高，ABSTAIN 就是为此设计的第五类决策。v3 起可附 `unobtainable_reason`（no_access / nonexistent / unreproducible / undecidable）说明缺口类型，随输出与审计日志落档（tests case26 演示，输出里有 `Unobtainable:` 行）。
