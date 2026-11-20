# Evidence Gate Benchmark — Results

- 运行时间：2026-11-20 10:52
- Gate：`scripts/gate_check.py`
- 语料：`benchmark/corpus/`（33 条：adversarial 10 · core 23）
- 模式：gate-level（确定性检查器对带真值输入的判定），`--offline`
- 指标定义：FAR = 应拦截而被放行（过度声明流出）；FRR = 应放行而被拦截（误伤诚实结论）

| 指标 | 结果 |
|------|------|
| Accuracy | 33/33 (100.0%) |
| **False Acceptance Rate (FAR)** | 0/19 (0.0%) |
| **False Rejection Rate (FRR)** | 0/14 (0.0%) |
| Mean latency | 107 ms/entry（含 Python 进程启动，本地单机） |

## suite: adversarial（10 条：should_pass 4 · should_block 6）

Accuracy 100.0% · FAR 0/6 (0.0%) · FRR 0/4 (0.0%) · latency 110 ms

| ID | 名称 | 真值 | 判定 | 耗时(ms) | 结果 |
|----|------|------|------|----------|------|
| b14 | misleading-quote-figures | should_block | VERIFY_REQUIRED | 137 | ✅ |
| b15 | correlated-evidence-same-host | should_block | VERIFY_REQUIRED | 108 | ✅ |
| b16 | outdated-evidence-current-claim | should_block | VERIFY_REQUIRED | 119 | ✅ |
| b17 | same-model-false-verification | should_block | VERIFY_REQUIRED | 106 | ✅ |
| b18 | attested-only-cross-verified | should_block | VERIFY_REQUIRED | 97 | ✅ |
| b19 | channel-mismatch-verified | should_block | REJECT | 105 | ✅ |
| p11 | heterogeneous-crosscheck-pass | should_pass | PASS | 96 | ✅ |
| p12 | historical-claim-old-evidence | should_pass | PASS | 101 | ✅ |
| p13 | aggregator-scoped-claim | should_pass | PASS | 101 | ✅ |
| p14 | mechanical-channel-verified | should_pass | PASS | 125 | ✅ |

## suite: core（23 条：should_pass 10 · should_block 13）

Accuracy 100.0% · FAR 0/13 (0.0%) · FRR 0/10 (0.0%) · latency 106 ms

| ID | 名称 | 真值 | 判定 | 耗时(ms) | 结果 |
|----|------|------|------|----------|------|
| b01 | fact-error | should_block | REJECT | 124 | ✅ |
| b02 | insufficient-evidence | should_block | VERIFY_REQUIRED | 101 | ✅ |
| b03 | causal-jump | should_block | VERIFY_REQUIRED | 89 | ✅ |
| b04 | env-contamination | should_block | REJECT | 106 | ✅ |
| b05 | sample-to-population | should_block | REJECT | 105 | ✅ |
| b06 | theory-not-verified | should_block | VERIFY_REQUIRED | 104 | ✅ |
| b07 | live-counterexample | should_block | REJECT | 90 | ✅ |
| b08 | abstain-gap | should_block | ABSTAIN | 89 | ✅ |
| b09 | quote-not-in-anchor | should_block | VERIFY_REQUIRED | 94 | ✅ |
| b10 | same-context-counter-search | should_block | VERIFY_REQUIRED | 88 | ✅ |
| b11 | pre-action-unexecuted | should_block | VERIFY_REQUIRED | 104 | ✅ |
| b12 | lying-field-absolute | should_block | REJECT | 100 | ✅ |
| b13 | cross-verified-no-execution | should_block | REJECT | 170 | ✅ |
| p01 | fact-anchored | should_pass | PASS | 99 | ✅ |
| p02 | experiment-verified | should_pass | PASS | 96 | ✅ |
| p03 | cross-verified-isolated | should_pass | PASS | 105 | ✅ |
| p04 | hedged-correlation | should_pass | PASS_WITH_CAVEAT | 122 | ✅ |
| p05 | hypothesis-labeled | should_pass | PASS | 121 | ✅ |
| p06 | recommendation-conditioned | should_pass | PASS_WITH_CAVEAT | 104 | ✅ |
| p07 | benefit-with-boundary | should_pass | PASS_WITH_CAVEAT | 111 | ✅ |
| p08 | url-anchor-attested | should_pass | PASS | 103 | ✅ |
| p09 | works-claim-executed | should_pass | PASS | 104 | ✅ |
| p10 | simple-fact-low-risk | should_pass | PASS | 108 | ✅ |

## 未测量的部分（诚实边界）

- 本基准只测**闸门本身**（确定性判定器 + 输入真值），不测 Agent 端到端准确率。
- Agent-level 基准（baseline agent vs agent+gate 的 Accuracy / Hallucination Rate / Cost 等）协议见 `benchmark/AGENT-PROTOCOL.md`，**尚未运行**，因此本项目不宣称任何端到端准确率提升。
- FAR/FRR 仅对本语料成立；语料由维护者构造，存在构造者偏差，欢迎社区扩充语料（见 CONTRIBUTING.md）。
- adversarial suite 的预期（should_block/should_pass）按 v3 认识论标准构造（异构验证、独立性、时效），与 core suite 的 v2 标准在'何谓充分证据'上存在哲学差异——这正是升级本身；1.0 vs 2.0 的对照见 AB-RESULTS.md。

