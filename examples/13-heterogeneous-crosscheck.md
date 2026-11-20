# 示例 13 · 异构交叉验证：诚实申报如何拿到 L4

**教训：跨模型家族 + 机械引文线 + 隔离上下文 —— "已交叉验证"的正确姿势。**

v3 反误伤正例。与示例 12 同样的结论、同样的风险等级，但证据结构不同：本地机械引文线 + 跨家族独立核查（claude 复查 glm 的结论，隔离会话）。全部 v3 规则不触发，L4 放行。

## 闸门输入（benchmark/corpus/p11-heterogeneous-crosscheck.json）

```json
{
  "conclusion": "foo-lib 3.2 存在连接池泄漏，已交叉验证",
  "type": "EXPERIMENT_RESULT",
  "claimed_strength": "cross_verified",
  "risk_tier": "high",
  "generator": "glm-5.3",
  "evidence": [
    {
      "kind": "test_result",
      "detail": "本地复现脚本泄漏计数上升 run#771",
      "group": "local-run"
    },
    {
      "kind": "official_doc",
      "detail": "foo-lib 配置参考（tests/fixtures/docs/api-timeout.md）中 timeouts 章节列出连接池上限语义",
      "group": "foo-docs",
      "anchor": "tests/fixtures/docs/api-timeout.md",
      "quote": "retries | 2 | 重试次数"
    },
    {
      "kind": "official_doc",
      "detail": "https://gitlab.com/foo-lib/issues/991 issue 报告泄漏",
      "content_supports": "supported",
      "group": "issue"
    }
  ],
  "verification": {
    "executed": true,
    "detail": "本地脚本复现泄漏",
    "env_independent": true,
    "validates_target": true
  },
  "independent_checks": [
    {
      "by": "claude-sonnet-4.5",
      "channel": "retrieval_fresh",
      "agree": true,
      "context": "isolated",
      "detail": "隔离会话中独立检索 issue #991 与上游 commit，确认泄漏存在"
    }
  ],
  "counter_evidence": [],
  "counter_search_context": "isolated",
  "evidence_obtainable": "yes",
  "generalization": null
}
```

## 实际运行输出（`--offline`，PASS）

```text
Evidence Gate Result

Conclusion:
foo-lib 3.2 存在连接池泄漏，已交叉验证
Type: EXPERIMENT_RESULT
Claimed strength: cross_verified  (risk: high)
Evidence Level: L4  (claim requires L4; independent lines: 3)
Evidence (anchor three-stage check):
  - [direct·trace-only] test_result — 本地复现脚本泄漏计数上升 run#771 (anchor not mechanically checkable)
  - [direct·mech✓] official_doc — quote verified in anchor: tests/fixtures/docs/api-timeout.md
  - [direct·attested] official_doc — URL not fetched here; agent attests content (channel=attested): https://gitlab.com/foo-lib/issues/991
  execution: executed=True valid=True env_independent=True validates_target=True channel=None
Counter-evidence search context: isolated
Findings:
Decision: PASS  (exit 0)
Reason:
  evidence L4 supports claimed strength 'cross_verified' (requires L4)
Allowed wording: 已交叉验证 (cross-verified)
Calibration: levels are ordinal, not probabilities; empirical per-level accuracy via --calibration
Verifier: {"id": "unspecified", "protocol": "gate_check/3.0.0", "entailment_channel": "mechanical", "independent_checks": {"valid_agreeing": 1, "cross_family_required": true, "cross_family_ok": true}}
```

## 服从决策后应这样表述

**"foo-lib 3.2 存在连接池泄漏，已交叉验证：本地脚本复现（run#771）+ 配置文档机械核对 + 跨模型独立检索确认（隔离会话）。"** —— "已交叉验证"此时名副其实。

## 为什么

对照示例 12，L4 的三块拼图在这里齐了：**独立线**（三个不同宿主/组，塌缩后仍 3 条）；**硬通道**（本地文档引文被机械核验 `[direct·mech✓]` + 跨家族核查 agreeing）；**异构性**（generator=glm-5.3，检查者=claude-sonnet-4.5，家族不同 → cross_family_ok=true）。同家族的检查不算数（cross-family > same-family > self；同家族模型同错率约 60%，堆 9 个同家族裁判只相当于 2 票）。确定性工具（`verified_by: "tool:trivy"`）天然异构 —— 工具不共享语言模型的先验。这就是 v3 的升级方向：不是把门槛抬高，而是把"谁验证的、验的是哪条线、在什么上下文里验的"变成可检查的申报结构。
