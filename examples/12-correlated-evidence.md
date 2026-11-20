# 示例 12 · 相关证据：两篇"独立报道"，一个宿主

**教训：独立性是算出来的，不是数出来的 —— 100 家转载 = 1 条独立线。**

v3 新增对抗类。三条证据线：本地复现 + 两篇"独立报道"。v2 按三个组授予 L4"已交叉验证"；v3 发现两篇报道同宿主（news.example.com），塌缩成一条线，加上全是 attested 无人核实，压到 L3 拦截。

## 闸门输入（benchmark/corpus/b15-correlated-evidence.json）

```json
{
  "conclusion": "foo-lib 3.2 存在连接池泄漏，已交叉验证",
  "type": "EXPERIMENT_RESULT",
  "claimed_strength": "cross_verified",
  "risk_tier": "high",
  "evidence": [
    {
      "kind": "test_result",
      "detail": "本地复现脚本泄漏计数上升 run#771",
      "group": "local-run"
    },
    {
      "kind": "official_doc",
      "detail": "https://news.example.com/tech/foo-lib-leak 报道连接池泄漏",
      "content_supports": "supported",
      "group": "news-a"
    },
    {
      "kind": "official_doc",
      "detail": "https://news.example.com/tech/foo-lib-leak-confirmed 转载确认连接池泄漏",
      "content_supports": "supported",
      "group": "news-b"
    }
  ],
  "verification": {
    "executed": true,
    "detail": "本地脚本复现泄漏",
    "env_independent": true,
    "validates_target": true
  },
  "counter_evidence": [],
  "counter_search_context": "isolated",
  "evidence_obtainable": "yes",
  "generalization": null
}
```

## 实际运行输出（`--offline`，VERIFY_REQUIRED）

```text
Evidence Gate Result

Conclusion:
foo-lib 3.2 存在连接池泄漏，已交叉验证
Type: EXPERIMENT_RESULT
Claimed strength: cross_verified  (risk: high)
Evidence Level: L3  (claim requires L4; independent lines: 2)
Evidence (anchor three-stage check):
  - [direct·trace-only] test_result — 本地复现脚本泄漏计数上升 run#771 (anchor not mechanically checkable)
  - [direct·attested] official_doc — URL not fetched here; agent attests content (channel=attested): https://news.example.com/tech/foo-lib-leak
  - [direct·attested] official_doc — URL not fetched here; agent attests content (channel=attested): https://news.example.com/tech/foo-lib-leak-confirmed
  execution: executed=True valid=True env_independent=True validates_target=True channel=None
Counter-evidence search context: isolated
Findings:
  [medium] CORRELATED_EVIDENCE: evidence lines merged — official_doc@news.example.com + official_doc@news.example.com: same registrable domain (example.com) — syndication risk; attest same_host_independent on BOTH items to override; independent-line count is after collapse (100 reposts of one wire story = 1 line)
  [medium] ATTESTED_ONLY_LINES: ≥2 independent lines exist but NONE is mechanically verified (no checked quote, no tool-verified line) and no valid agreeing cross-family check exists: cross-verified wording rests on self-attestation alone — capped at L3
  [high] CROSS_FAMILY_MISSING: cross-verified wording at high/extreme risk without heterogeneous verification: same-model agreement is correlated failure, not cross-validation
Decision: VERIFY_REQUIRED  (exit 10)
Reason:
  cross-verified wording at high/extreme risk without heterogeneous verification: same-model agreement is correlated failure, not cross-validation; claimed strength 'cross_verified' requires L4, evidence is only L3: conclusion strength exceeds evidence strength — execute the actual verification (run it), or downgrade the wording to the allowed strength and rerun the gate
Allowed wording: 已通过实际验证 (verified)
Calibration: levels are ordinal, not probabilities; empirical per-level accuracy via --calibration
Required actions:
  - cross-verified wording at high/extreme risk needs heterogeneous verification: an isolated independent check by a DIFFERENT model family, or an evidence line verified by a deterministic tool (evidence[].verified_by='tool:...') — agreement within one model is correlated failure
Verifier: {"id": "unspecified", "protocol": "gate_check/3.0.0", "entailment_channel": "attested", "independent_checks": {"valid_agreeing": 0, "cross_family_required": true, "cross_family_ok": false}}
```

## 服从决策后应这样表述

**"foo-lib 3.2 存在连接池泄漏：本地脚本已复现（L3，已通过实际验证）；两家媒体宿主的转载报道方向一致，但同源转载不构成独立验证。已交叉验证的说法暂不成立。"** —— 或者按 Required actions 补一条真正异构的验证线再重跑。

## 为什么

三条 finding 各自拦掉一层：CORRELATED_EVIDENCE 把 3 条线塌缩成 2 条（同注册域 = 通稿转载风险；两个 URL 同宿主，"独立报道"的独立性是数 URL 数出来的幻觉）；ATTESTED_ONLY_LINES 封顶 L3 —— 塌缩后的线没有任何一条被机械核实（引文未查、URL 未抓、无工具线），"存在证据"≠"证据被检验"；CROSS_FAMILY_MISSING 指出连异构验证也不存在。塌缩判据是语法性的：同声明组 / 同注册域（可双方证明 same_host_independent 覆盖）/ 引文 token Jaccard≥0.7 / 引用链（引文或 detail 里出现对方的 URL）。语义级改写转载（同一通稿的不同措辞版本）目前检测不了 —— Open Problem。
