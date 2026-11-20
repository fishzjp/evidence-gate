# 示例 11 · 误导性引文：引用真实存在，但不支持结论的数字

**教训：引文存在 ≠ 引文支持 —— 数字是"支持"变成可检查事实的地方。**

v3 新增对抗类。锚点可解析、引文逐字在文件里，v2 的三段式核查全部通过——但结论声称 30 秒，引文说的是 60 秒。v2 放行（A/B 实测 6 类攻击全部穿透），v3 的数字一致性检查拦截。

## 闸门输入（benchmark/corpus/b14-misleading-quote.json）

```json
{
  "conclusion": "foo-lib 的默认超时是 30 秒，配置参考明确写明",
  "type": "FACT",
  "claimed_strength": "judged",
  "risk_tier": "medium",
  "evidence": [
    {
      "kind": "official_doc",
      "detail": "foo-lib 配置参考（tests/fixtures/docs/api-timeout.md）",
      "group": "foo-docs",
      "anchor": "tests/fixtures/docs/api-timeout.md",
      "quote": "default timeout is 60 seconds"
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
  "generalization": null
}
```

## 实际运行输出（`--offline`，VERIFY_REQUIRED）

```text
Evidence Gate Result

Conclusion:
foo-lib 的默认超时是 30 秒，配置参考明确写明
Type: FACT
Claimed strength: judged  (risk: medium)
Evidence Level: L1  (claim requires L2; independent lines: 0)
Evidence (anchor three-stage check):
  - [direct·mech✓] official_doc — quote verified in anchor: tests/fixtures/docs/api-timeout.md
  - [indirect*] official_doc — quote does not carry the claimed figure(s) 30 秒 (misleading quote)
  execution: executed=False valid=False env_independent=unknown validates_target=unknown channel=None
Counter-evidence search context: isolated
Findings:
  [high] MISLEADING_QUOTE: the conclusion's figure(s) 30 秒 appear in NONE of the quoted evidence or their anchors — the quotes exist but do not carry the claimed number(s) (citation exists ≠ citation supports)
Decision: VERIFY_REQUIRED  (exit 10)
Reason:
  the conclusion's figure(s) 30 秒 appear in NONE of the quoted evidence or their anchors — the quotes exist but do not carry the claimed number(s) (citation exists ≠ citation supports); claimed strength 'judged' requires L2, evidence is only L1: conclusion strength exceeds evidence strength — execute the actual verification (run it), or downgrade the wording to the allowed strength and rerun the gate
Allowed wording: 可能/初步判断 (possibly / preliminary)
Calibration: levels are ordinal, not probabilities; empirical per-level accuracy via --calibration
Required actions:
  - quote the line that actually contains 30 秒, or correct the figure in the conclusion
  - locate an authoritative source (official docs, source code, config, data) and cite it with a resolvable anchor + quote
Verifier: {"id": "unspecified", "protocol": "gate_check/3.0.0", "entailment_channel": "attested", "independent_checks": {"valid_agreeing": 0, "cross_family_required": false, "cross_family_ok": null}}
```

## 服从决策后应这样表述

**"foo-lib 的默认超时待核对：本地文档副本写明 60 秒（'default timeout is 60 seconds'），我此前记忆中的 30 秒与文档不符。"** —— 引用真实数字，不引用自己想要的数字。

## 为什么

注意输出的两条证据判定并行出现：`[direct·mech✓]`（引文确实在文件里）和 `[indirect*]`（引文不携带结论声称的数字）。这正是 P0-A 的设计：三段式核查管"引文真实"，数字一致性管"引文支持"——两个都过才算直接证据。规则刻意窄化（结论声称 1–3 个带单位数字、全部无人背书 + 无有效执行 + 类型限定 FACT/INFERENCE/EXPERIMENT_RESULT）：宽规则原型曾误伤 5/10 条诚实结论（版本号、条件阈值被当声明数字），窄规则 FRR=0。数字匹配做了归一化（千分位、小数尾零、全角字符）与时间单位换算（结论说 0.5 分钟、引文说 30 seconds 算携带）。同义改写不改变判定（tests case20 锁定：换措辞说"缺省连接超时时间为 30 秒"照样拦截）。
