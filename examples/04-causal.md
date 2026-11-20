# 示例 4 · 因果推理：相关性 ≠ 因果关系

**教训：时间相关性 + 一条记忆里的“没有其他变更” = L1；因果声明要求 L3。**

错误率在 v2.1.0 发布后 5 分钟内从 0.1% 升到 2%。Agent 想说“v2.1.0 导致了错误率上升”。证据是监控图（时间相关）和值班同学的记忆。

## 闸门输入（gate-input.json）

```json
{
  "conclusion": "客户端 v2.1.0 上线后错误率上升，说明 v2.1.0 导致了错误率上升",
  "type": "INFERENCE",
  "claimed_strength": "judged",
  "risk_tier": "medium",
  "evidence": [
    {
      "kind": "time_correlation",
      "detail": "错误率监控（grafana /d/err）：v2.1.0 发布（14:00）后 5 分钟错误率从 0.1% 升至 2%"
    },
    {
      "kind": "memory",
      "detail": "发布窗口内应该没有其他变更（听值班同学说的）"
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
客户端 v2.1.0 上线后错误率上升，说明 v2.1.0 导致了错误率上升
Type: INFERENCE
Claimed strength: judged  (risk: medium)
Evidence Level: L1  (claim requires L3; independent lines: 0)
Evidence (anchor three-stage check):
  - [indirect] time_correlation — 错误率监控（grafana /d/err）：v2.1.0 发布（14:00）后 5 分钟错误率从 0.1% 升至 2%
  - [indirect] memory — 发布窗口内应该没有其他变更（听值班同学说的）
  execution: executed=False valid=False env_independent=unknown validates_target=unknown channel=None
Counter-evidence search context: same
Findings:
  [info] NON_EVIDENCE_KIND: evidence kind 'memory' is not evidence, only a prior (L0/L1 at most)
Decision: VERIFY_REQUIRED  (exit 10)
Reason:
  claimed strength 'judged' requires L3, evidence is only L1 (causal claim asserted from correlation-level evidence): conclusion strength exceeds evidence strength — execute the actual verification (run it), or downgrade the wording to the allowed strength and rerun the gate
Allowed wording: 可能/初步判断 (possibly / preliminary) — 未实际运行验证 (not actually executed/verified)
Calibration: levels are ordinal, not probabilities; empirical per-level accuracy via --calibration
Mandatory caveats (must appear in output):
  - counter-evidence search was same-context; coverage may be limited by agreement bias
Required actions:
  - execute the actual verification: run the program / tests / benchmark instead of reasoning about it
Verifier: {"id": "unspecified", "protocol": "gate_check/3.0.0", "entailment_channel": "none", "independent_checks": {"valid_agreeing": 0, "cross_family_required": false, "cross_family_ok": null}}
```

## 服从决策后应这样表述

降级路径：**“错误率上升与 v2.1.0 发布时间强相关，初步判断新版本可能是原因之一；尚未排除同期其他变更，回滚/灰度实验安排中。”** 验证路径：回滚实验或灰度对比后重过闸门。

## 为什么

因果声明（“导致了”）从文本识别，claimed≥judged 时要求 L3。time_correlation 是间接证据（L1），memory 直接被标注“不是证据”。注意“应该没有其他变更（听说的）”正是被 L1 天花板挡住的模糊断言。
