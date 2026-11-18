# 示例 8 · 高风险结论：不可逆动作前必须实际执行验证

**教训：同样的输入在普通模式下只是 PASS_WITH_CAVEAT，在 pre-action 模式下被拦下。**

Agent 准备执行 `kubectl apply` 上线，附带声明“服务不会中断”。证据是Dockerfile 代码审阅（锚点+引文都真实），没有实际演练。运行时加了 `--gate-point pre-action`。

## 闸门输入（gate-input.json）

```json
{
  "conclusion": "现在直接执行 kubectl apply 上线，服务不会中断",
  "type": "INFERENCE",
  "claimed_strength": "possibly",
  "risk_tier": "medium",
  "evidence": [
    {
      "kind": "source_code",
      "detail": "审阅部署定义（tests/fixtures/infra/Dockerfile 本地副本）：基础镜像不变、仅新增副本，无删除",
      "group": "code-review",
      "anchor": "tests/fixtures/infra/Dockerfile",
      "quote": "FROM python:3.12-slim"
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
Type: INFERENCE
Claimed strength: possibly  (risk: high, gate-point: pre-action)
Evidence Level: L2  (claim requires L3)
Evidence (anchor three-stage check):
  - [direct·mech✓] source_code — quote verified in anchor: tests/fixtures/infra/Dockerfile
  execution: executed=False valid=False env_independent=unknown validates_target=unknown
Counter-evidence search context: same
Findings:
Confidence: LOW
Decision: VERIFY_REQUIRED  (exit 10)
Reason:
Allowed wording: 可能/初步判断 (possibly / preliminary) — 未实际运行验证 (not actually executed/verified)
Mandatory caveats (must appear in output):
  - counter-evidence search was same-context; coverage may be limited by agreement bias
Required actions:
  - execute the actual verification: run the program / tests / benchmark instead of reasoning about it
  - or downgrade the wording and rerun the gate with the lower claim
  - for irreversible actions: verify in a reversible/staged setting first (dry-run, canary, staging) before executing
Verifier: {"id": "unspecified", "protocol": "gate_check/2.0.0", "entailment_channel": "mechanical"}
```

## 服从决策后应这样表述

不 apply。先做可逆验证：**“代码审阅认为可以平滑上线，但未实际演练；建议先灰度 5% 观察 30 分钟再全量。”** 演练后带执行证据重过闸门。

## 为什么

pre-action 模式把风险升一档（medium→high），“不会中断”这类 works 声明的门槛降到“任何 works 声明都必须执行过”（works_floor=possibly）。理由：错误结论在不可逆动作里即时致害，事后闸门没有意义。对照：同一输入不加 --gate-point 时决策是 PASS_WITH_CAVEAT —— 位置不同，标准不同。
