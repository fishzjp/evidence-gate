# Evidence Gate A/B — 1.0 (v2.0.0) vs 2.0 (v3.0.0)

- 运行时间：2026-11-20 10:53
- 语料：33 条（同一输入逐字节喂给两个 gate；v1 忽略 v3 新增字段，字段存在不构成提示）
- v1 快照：`benchmark/legacy/gate_check_v2.0.0.py`（升级前主脚本的原样拷贝）

## suite: adversarial

| Gate | Accuracy | FAR | FRR | Mean latency |
|------|----------|-----|-----|--------------|
| EG 1.0 (v2.0.0) | 40.0% | 6/6 (100.0%) | 0/4 (0.0%) | 102 ms |
| EG 2.0 (v3.0.0) | 100.0% | 0/6 (0.0%) | 0/4 (0.0%) | 105 ms |

## suite: core

| Gate | Accuracy | FAR | FRR | Mean latency |
|------|----------|-----|-----|--------------|
| EG 1.0 (v2.0.0) | 100.0% | 0/13 (0.0%) | 0/10 (0.0%) | 103 ms |
| EG 2.0 (v3.0.0) | 100.0% | 0/13 (0.0%) | 0/10 (0.0%) | 113 ms |

## adversarial suite 逐条对照（升级的故事在这里）

| ID | 名称 | 真值 | 1.0 判定 | 2.0 判定 | 变化 |
|----|------|------|----------|----------|------|
| b14 | misleading-quote-figures | should_block | PASS | VERIFY_REQUIRED | ✅ FIXED (1.0 放行, 2.0 拦截) |
| b15 | correlated-evidence-same-host | should_block | PASS | VERIFY_REQUIRED | ✅ FIXED (1.0 放行, 2.0 拦截) |
| b16 | outdated-evidence-current-claim | should_block | PASS | VERIFY_REQUIRED | ✅ FIXED (1.0 放行, 2.0 拦截) |
| b17 | same-model-false-verification | should_block | PASS | VERIFY_REQUIRED | ✅ FIXED (1.0 放行, 2.0 拦截) |
| b18 | attested-only-cross-verified | should_block | PASS | VERIFY_REQUIRED | ✅ FIXED (1.0 放行, 2.0 拦截) |
| b19 | channel-mismatch-verified | should_block | PASS | REJECT | ✅ FIXED (1.0 放行, 2.0 拦截) |
| p11 | heterogeneous-crosscheck-pass | should_pass | PASS | PASS | both OK |
| p12 | historical-claim-old-evidence | should_pass | PASS | PASS | both OK |
| p13 | aggregator-scoped-claim | should_pass | PASS | PASS | both OK |
| p14 | mechanical-channel-verified | should_pass | PASS | PASS | both OK |

## 判定稳定性（改写不变性）

结论同义改写后判定必须不变（isomorphic perturbation，
arXiv:2604.15149：判决对等价改写翻转 = 可被措辞博弈）。覆盖于
tests/run_tests.py 的 paraphrase 用例（case20–22），不在本表。

## 解读注意（诚实边界）

- adversarial suite 的 6 条攻击按 v3 认识论构造，v1 在其上 FAR=100%
  是升级目标（见 docs/research-survey-2.md §3 矩阵），不是对 v1 的
  不公平标签：core suite 全部保留 v2 时代的原始标签。
- 披露一处 core 输入适配：p03 增加了可选 v3 字段
  （evidence[].verified_by="tool:..." 及 detail 中点名工具），
  使其诚实的工具验证线对 v3 可见。v1 忽略新字段、判定不变
  （PASS L4）；未适配的原始输入上 v3 判 VERIFY_REQUIRED
  （CROSS_FAMILY_MISSING，工具线不可见）——标签不变，判定从严
- 两个 gate 都是确定性脚本，latency 差异（±20ms 级）主要来自
  v3 增加的相关性/时间/账本计算，相对 Agent 验证成本可忽略。
- 本 A/B 只测 gate 层；不宣称端到端 Agent 准确率变化。

