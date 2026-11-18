# Agent-Level Benchmark Protocol — 尚未运行

> **状态：NOT MEASURED。** 本文档描述如何测量 Evidence Gate 对 Agent 端到端
> 结论可靠性的影响。在真实运行数据产生之前，本项目**不宣称**任何端到端
> 准确率提升。已测量的只有 gate-level 结果（见 [RESULTS.md](RESULTS.md)）。

## 目标问题

Evidence Gate 的设计目标是降低未经验证的错误结论进入最终输出的风险。
要验证这个目标，需要对比：

```
Baseline Agent  ──直接回答──▶  Answer
Agent + Evidence Gate ──过闸后回答──▶  Answer
```

## 任务集

- 每个任务包含一个诱惑性场景（诱导 agent 输出过度声明），并带有可判分的
  真值（ground truth）。
- 建议任务类型（每类 ≥20 题）：
  1. **可验证技术事实**（本地文件/文档可查，含陷阱版本）
  2. **需要执行才能确认的 works 声明**（测试通过 ≠ 覆盖目标）
  3. **样本→整体诱惑**（给部分数据，诱导全量结论）
  4. **相关→因果诱惑**
  5. **证据不可得场景**（正确行为是 ABSTAIN，不是硬答）
  6. **引用支持检查**（给真实存在但不支持结论的引用，诱导照引）

## 指标（两类 agent 各测一遍）

| 指标 | 定义 |
|------|------|
| Accuracy | 最终答案与真值一致的比例 |
| Unsupported Claim Rate | 输出中无证据支撑的强声明占比 |
| Hallucination Rate | 输出中与真值矛盾的虚构内容占比 |
| Abstention Rate | 拒答/弃权比例（在证据不可得场景中为正确行为） |
| Verification Success Rate | 声称已验证的结论中真实被验证的比例 |
| **False Acceptance Rate** | 错误结论被输出（未被拦截）的比例 |
| **False Rejection Rate** | 正确结论被拦截/降级的比例 |
| Cost | 每 task 的 token / API 费用 |
| Latency | 每 task 墙钟时间 |

## 控制变量

- 同一模型、同一温度（建议 0）、同一任务呈现顺序；只切换
  "是否加载 Evidence Gate skill"。
- 每配置 ≥3 次重复，报告均值与标准差。
- 评审者判分时盲测（不知道答案来自哪个配置）。

## 为什么还没有运行

端到端 benchmark 需要：(a) 一个可重复的 agent harness，(b) 判分人力或
可靠的 LLM-judge 校准，(c) 足够预算跑重复实验。本仓库目前只包含
gate-level 基准（`run_benchmark.py`，确定性、可复现、已运行）。
如果你运行了本协议，欢迎提交结果与语料 —— 见
[CONTRIBUTING.md](../CONTRIBUTING.md)。
