# 示例 1 · 事实判断：带锚点引文的事实声明

**教训：事实声明需要可追溯的来源，且引用内容必须真的支持结论。**

Agent 需要回答 foo-lib 的默认超时配置。它找到了本地文档副本，引用了确切的一行，并主动核查了旧版本差异（反证已核实排除）。

## 闸门输入（gate-input.json）

```json
{
  "conclusion": "foo-lib 的默认请求超时是 60 秒",
  "type": "FACT",
  "claimed_strength": "judged",
  "risk_tier": "medium",
  "evidence": [
    {
      "kind": "official_doc",
      "detail": "foo-lib 配置参考（本地副本）：timeout 默认 60 秒",
      "anchor": "tests/fixtures/docs/api-timeout.md",
      "quote": "default timeout is 60 seconds",
      "content_supports": "supported",
      "group": "docs"
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
      "detail": "旧版本 v1.x 默认 30 秒；已核对锁文件确认项目固定 v2.3.1，v1.x 行为不适用",
      "status": "refuted",
      "contradicts": true
    }
  ],
  "counter_search_context": "isolated",
  "evidence_obtainable": "yes",
  "generalization": null
}
```

## 实际运行输出（真实输出节选）

```text
Evidence Gate Result
Conclusion:
Type: FACT
Claimed strength: judged  (risk: medium)
Evidence Level: L2  (claim requires L2)
Evidence (anchor three-stage check):
  - [direct·mech✓] official_doc — quote verified in anchor: tests/fixtures/docs/api-timeout.md
  execution: executed=False valid=False env_independent=unknown validates_target=unknown
Counter-evidence search context: isolated
Findings:
Confidence: MEDIUM
Decision: PASS  (exit 0)
Reason:
Allowed wording: 根据现有证据可以判断 (judged from evidence)
Verifier: {"id": "unspecified", "protocol": "gate_check/2.0.0", "entailment_channel": "mechanical"}
```

## 服从决策后应这样表述

**“根据 foo-lib 配置参考，默认请求超时是 60 秒（v2.3.1；v1.x 为 30 秒，本项目不受影响）。”** —— 用“根据现有证据可以判断”级别措辞。

## 为什么

锚点三段式全部通过：锚点可解析（本地文件存在）→ 内容实读 → 引文“default timeout is 60 seconds” 机械核验在文件中。反证（旧版本差异）不是被忽略而是被核实排除（锁文件确认版本）。L2 直接证据支撑 judged 措辞。
