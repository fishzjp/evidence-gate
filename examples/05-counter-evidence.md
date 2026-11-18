# 示例 5 · 反证搜寻：主动找推翻自己的证据

**教训：反证不是流程装饰 —— 同一份数据里的 #17 号用例直接推翻了“均优于”。**

Agent 声称新正则引擎“在所有基准用例上均优于旧引擎”。它做对了流程（真的去找了反证），并且在自己引用的结果文件里发现了矛盾用例 #17 —— 如实填写为未处理矛盾反证。

## 闸门输入（gate-input.json）

```json
{
  "conclusion": "新正则库 re2-lite 在全部 20 个基准用例上性能均优于 JavaScript 内置 RegExp",
  "type": "FACT",
  "claimed_strength": "judged",
  "risk_tier": "high",
  "evidence": [
    {
      "kind": "test_result",
      "detail": "基准测试结果：20 个用例中 19 个 re2-lite 快 1.5–3 倍（bench/results-2026-11-16.json）",
      "group": "bench"
    }
  ],
  "verification": {
    "executed": true,
    "detail": "运行基准套件 bench/run.js --all，结果写入 results-2026-11-16.json",
    "env_independent": true,
    "validates_target": true
  },
  "counter_evidence": [
    {
      "detail": "同一份结果文件：用例 #17（长回溯模式）re2-lite 慢 40%，与『均优于』直接矛盾",
      "status": "unaddressed",
      "contradicts": true
    }
  ],
  "generalization": null
}
```

## 实际运行输出（真实输出节选）

```text
Evidence Gate Result
Conclusion:
Type: FACT
Claimed strength: absolute  (risk: high)
Evidence Level: L3  (claim requires L4)
Evidence (anchor three-stage check):
  - [indirect*] test_result — anchor path does not exist / unreadable: bench/results-2026-11-16.json
  execution: executed=True valid=True env_independent=True validates_target=True
Counter-evidence search context: same
Findings:
Confidence: LOW
Decision: REJECT  (exit 20)
Reason:
Allowed wording: 已通过实际验证 (verified)
Required actions:
  - address or refute the contradicting counter-evidence before asserting this conclusion
  - rerun the counter-evidence search in an isolated context (fresh session without the conclusion, or an independent agent), or attempt mechanical falsification
Verifier: {"id": "unspecified", "protocol": "gate_check/2.0.0", "entailment_channel": "none"}
```

## 服从决策后应这样表述

**“新引擎在 19/20 个基准用例上更快；用例 #17（长回溯模式）慢 40%，该场景需保留旧引擎或加长度回退。”** —— 把反例写进结论，而不是删掉它。

## 为什么

未处理且 contradicts 的反证 + FACT 类型 → FACT_CONTRADICTED → REJECT。这是闸门最硬的一条规则：带着活的矛盾不能输出事实。另外注意本例还暴露了两个次生问题：“均”触发绝对化；声称的基准结果文件路径不存在（anchor 无法解析）。反证搜寻的价值恰恰在此：找到的矛盾往往连带暴露证据本身的问题。
