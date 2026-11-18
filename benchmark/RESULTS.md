# Evidence Gate Benchmark — Results

- 运行时间：2026-11-18 12:35
- 语料：`benchmark/corpus/`（23 条：should_pass 10 · should_block 13）
- 模式：gate-level（确定性检查器对带真值输入的判定），`--offline`
- 指标定义：FAR = 应拦截而被放行（过度声明流出）；FRR = 应放行而被拦截（误伤诚实结论）

| 指标 | 结果 |
|------|------|
| Accuracy | 23/23 (100.0%) |
| **False Acceptance Rate (FAR)** | 0/13 (0.0%) |
| **False Rejection Rate (FRR)** | 0/10 (0.0%) |
| Mean latency | 97 ms/entry（含 Python 进程启动，本地单机） |

决策分布：ABSTAIN 1 · PASS 7 · PASS_WITH_CAVEAT 3 · REJECT 6 · VERIFY_REQUIRED 6

## 明细

| ID | 名称 | 真值 | 判定 | 耗时(ms) | 结果 |
|----|------|------|------|----------|------|
| b01 | fact-error | should_block | REJECT | 67 | ✅ |
| b02 | insufficient-evidence | should_block | VERIFY_REQUIRED | 75 | ✅ |
| b03 | causal-jump | should_block | VERIFY_REQUIRED | 136 | ✅ |
| b04 | env-contamination | should_block | REJECT | 251 | ✅ |
| b05 | sample-to-population | should_block | REJECT | 127 | ✅ |
| b06 | theory-not-verified | should_block | VERIFY_REQUIRED | 102 | ✅ |
| b07 | live-counterexample | should_block | REJECT | 67 | ✅ |
| b08 | abstain-gap | should_block | ABSTAIN | 70 | ✅ |
| b09 | quote-not-in-anchor | should_block | VERIFY_REQUIRED | 69 | ✅ |
| b10 | same-context-counter-search | should_block | VERIFY_REQUIRED | 70 | ✅ |
| b11 | pre-action-unexecuted | should_block | VERIFY_REQUIRED | 68 | ✅ |
| b12 | lying-field-absolute | should_block | REJECT | 66 | ✅ |
| b13 | cross-verified-no-execution | should_block | REJECT | 73 | ✅ |
| p01 | fact-anchored | should_pass | PASS | 68 | ✅ |
| p02 | experiment-verified | should_pass | PASS | 71 | ✅ |
| p03 | cross-verified-isolated | should_pass | PASS | 67 | ✅ |
| p04 | hedged-correlation | should_pass | PASS_WITH_CAVEAT | 71 | ✅ |
| p05 | hypothesis-labeled | should_pass | PASS | 65 | ✅ |
| p06 | recommendation-conditioned | should_pass | PASS_WITH_CAVEAT | 154 | ✅ |
| p07 | benefit-with-boundary | should_pass | PASS_WITH_CAVEAT | 184 | ✅ |
| p08 | url-anchor-attested | should_pass | PASS | 121 | ✅ |
| p09 | works-claim-executed | should_pass | PASS | 109 | ✅ |
| p10 | simple-fact-low-risk | should_pass | PASS | 75 | ✅ |

## 未测量的部分（诚实边界）

- 本基准只测**闸门本身**（确定性判定器 + 输入真值），不测 Agent 端到端准确率。
- Agent-level 基准（baseline agent vs agent+gate 的 Accuracy / Hallucination Rate / Cost 等）协议见 `benchmark/AGENT-PROTOCOL.md`，**尚未运行**，因此本项目不宣称任何端到端准确率提升。
- FAR/FRR 仅对本语料成立；语料由维护者构造，存在构造者偏差，欢迎社区扩充语料（见 CONTRIBUTING.md）。

