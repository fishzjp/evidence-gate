# Benchmark

Evidence Gate 的可复现测量。分两层，诚实边界明确：

## 1. Gate-level（已测量，确定性）

```bash
python3 benchmark/run_benchmark.py            # 运行并打印指标
python3 benchmark/run_benchmark.py --report   # 运行并写 RESULTS.md
```

- **语料**：`corpus/` — 33 条带真值标注的闸门输入（core 23 + adversarial
  10；14 条 should_pass：诚实结论如实填写应被放行；19 条 should_block：
  过度声明/错误声明/措辞作弊/对抗攻击应被拦截）。
- **指标**：Accuracy、**False Acceptance Rate**（应拦未拦，过度声明流出）、
  **False Rejection Rate**（应放被拦，误伤诚实结论）、时延。
- **性质**：确定性（`--offline`）、毫秒级、可在 CI 中作为回归门禁
  （FAR 或 FRR 非零即 exit 1）。
- 当前结果快照：[RESULTS.md](RESULTS.md)。

局限（必须读）：语料由维护者构造，存在构造者偏差；它测的是**闸门判定器**，
不是 Agent 端到端表现。

## 2. Agent-level（尚未运行）

baseline agent vs agent+gate 的端到端对比（Accuracy / Hallucination
Rate / FAR / FRR / Cost / Latency）协议已定义、尚未运行。
**因此本项目不宣称任何端到端准确率提升。**

## 新增语料

欢迎扩充语料（尤其是构造者偏差之外的场景）——每条新语料就是一个
`corpus/*.json` 文件，格式见现有文件；要求：

- `expectation` 必须有依据（为什么这条应放行/应拦截）；
- 不使用真实生产数据，fixtures 全部虚构；
- 提交 PR 时附 `run_benchmark.py` 全绿输出。
