# Changelog

本文件记录对外发布版本。格式遵循 [Keep a Changelog](https://keepachangelog.com/)，
版本遵循 [SemVer](https://semver.org/)。

## [2.0.0] - 2026-11-18

首个公开发布版本（initial public release）。1.x 为内部迭代，未发布。

### 能力

- **结论强度 ≤ 证据强度** 机械执行：L0–L4 证据等级 → 措辞上限映射；
  结论文本扫描（绝对化/因果/works/风险关键词）不信任自评字段
- **五类决策**：PASS / PASS_WITH_CAVEAT / VERIFY_REQUIRED / ABSTAIN /
  REJECT，exit codes 0/0/10/15/20（输入错误 2），可直接接入 CI
- **锚点三段式核查**：锚点可解析 → 内容实读 → 引文在文中（本地文件
  机械比对，剥 Markdown 格式符）；引用存在 ≠ 引用支持
- **隔离反证要求**：cross_verified / 绝对化声明及高风险空反证要求
  `counter_search_context: "isolated"`（同上下文搜索 → VERIFY_REQUIRED）
- **ABSTAIN**：`evidence_obtainable: no` 时输出"目前无法确认 + 缺口说明"，
  禁止带保留的猜测
- **不可逆动作前置闸门（G3）**：`--gate-point pre-action`，风险升档、
  works 声明必须执行过、CAVEAT 降为 VERIFY_REQUIRED
- **假验证模式识别**：推理冒充验证 / 测试通过≠问题解决 / 环境污染 /
  样本冒充总体 / 引用冒充支持（含 verification gaming）
- **审计与校准回路**：JSONL 日志（gate_id）+ `--mark-outcome` +
  `--calibration` 按等级统计真实准确率
- **Gate-level benchmark**：23 条真值标注语料，实测 Accuracy 100%、
  FAR 0/13、FRR 0/10（见 benchmark/RESULTS.md；agent-level 端到端对比
  协议已定义、尚未运行）

### 工程属性

- `scripts/gate_check.py`：Python 3.10+，仅标准库，零依赖，确定性输出
- 测试：14 个回归用例 + 3 个 CLI 子测试（tests/run_tests.py）
- CI：单元测试 / benchmark 门禁（FAR/FRR=0）/ secret 扫描 / skill 校验

### 已知问题（Known Issues）

- 自报字段（`content_supports`、`counter_search_context`、
  `evidence_obtainable`）可被虚报；闸门的对策是显式记录 + 被动校准回路，
  冷启动阶段校准不构成约束
- 校准回路需要事后人工/外部标记 outcome，无自动采集（P1）
- 关键词启发式存在边界误报可能（如中文绝对化词的邻近措辞）；漏报由
  等级算术兜底，误报的救济是改写措辞
- `--gate-point` 依赖调用方自觉传入，脚本无法拦截进程外的工具调用
- Agent-level 端到端效果未测量，任何"提高准确率"的说法均无数据支持

### 设计依据

2024–2026 文献调研（引用逐条核实，允许推翻既有设计）：见
[docs/research-survey.md](docs/research-survey.md)。
