# 示例 2 · 技术结论：理论上可行 ≠ 已实际验证

**教训：代码审阅是 L2 证据；说“可以正常运行”需要真的运行过（L3）。**

Agent 逐行审阅了重构 diff，接口签名兼容、调用点全部更新，于是想宣称“重构后服务可以正常运行”。

## 闸门输入（gate-input.json）

```json
{
  "conclusion": "这个重构方案可以正常运行，不会破坏现有功能",
  "type": "INFERENCE",
  "claimed_strength": "judged",
  "risk_tier": "medium",
  "evidence": [
    {
      "kind": "source_code",
      "detail": "逐行审阅重构 diff（PR #77，src/ 目录 12 个文件）：接口签名兼容、调用点全部更新",
      "group": "code-review"
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
Claimed strength: judged  (risk: medium)
Evidence Level: L2  (claim requires L3)
Evidence (anchor three-stage check):
  - [direct·trace-only] source_code — 逐行审阅重构 diff（PR #77，src/ 目录 12 个文件）：接口签名兼容、调用点全部更新 (anchor not mechanically checkable)
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
Verifier: {"id": "unspecified", "protocol": "gate_check/2.0.0", "entailment_channel": "none"}
```

## 服从决策后应这样表述

降级路径：**“根据代码审阅，重构在接口层面兼容、调用点已全部更新；尚未实际运行验证。”** 或执行验证路径：跑测试套件后带执行证据重过闸门。

## 为什么

“可以正常运行”是 works 声明，脚本从结论文本识别出来（不依赖字段诚实），要求 L3。审阅再仔细也是关于代码的判断，不是关于运行系统的观察 —— 这是最常见的假验证模式（推理冒充验证）。
