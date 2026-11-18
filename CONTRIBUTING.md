# Contributing to Evidence Gate

感谢愿意贡献。这个项目的核心是一套**判定规则**，所以贡献流程的重点是：
规则改动必须被测试锁定，行为变化必须被版本号记录。

## 流程

```
Fork → Branch → Modify → Test → Commit → PR
```

```bash
git clone https://github.com/<you>/evidence-gate.git && cd evidence-gate
git checkout -b feat/your-topic
# ... 修改 ...
python3 tests/run_tests.py            # 必须全绿
python3 benchmark/run_benchmark.py    # 必须全绿（FAR/FRR 为 0）
git commit -m "..."
git push -u origin feat/your-topic    # 然后开 PR
```

## 测试要求（硬性）

- 任何 `scripts/gate_check.py` 行为改动：**必须**新增或修改
  `tests/cases/*.json` 回归用例锁定该行为。
- **修改核心判定规则**（决策顺序、等级映射、锚点核查、反证/隔离要求、
  ABSTAIN 条件、pre-action 行为）：除回归用例外，**必须**在
  `benchmark/corpus/` 增加能区分新旧行为的真值语料
  （`expectation: should_pass | should_block`，需在 PR 描述中说明真值依据）。
- PR 描述必须附两个命令的全绿输出：
  `python3 tests/run_tests.py` 与 `python3 benchmark/run_benchmark.py`。

## 回归红线

两条不可破（CI 会拦）：

1. **FAR 门禁**：原本应拦截的错误结论不得变成 PASS/PASS_WITH_CAVEAT。
2. **FRR 门禁**：诚实结论（如实填写的 should_pass 语料）不得被误伤。

放宽规则请同时证明没有引入两类错误，并在 PR 中明示取舍。

## 文档要求

- 规则改动同步更新：`SKILL.md`（行为说明）、`references/decision-rules.md`
  （判定矩阵）、`ARCHITECTURE.md`（模块职责）。
- 新增示例：放 `examples/`，输出必须是脚本**真实运行**的节选（本项目自身
  遵守 Evidence Gate 原则：不写未经核验的行为描述）。

## Commit 规范

```
<type>: <subject>

feat:      新能力（如新增决策类、新核查通道）
fix:       修复判定错误（附回归用例）
docs:      文档
test:      测试/语料
refactor:  不改行为的重构
```

Subject 用祈使句、不超过 50 字符；正文说明 why（PR 讨论放在描述里）。

## 版本规范（SemVer）

- **MAJOR**：决策语义变化 —— 同一输入得出不同决策类、字段含义/删除、
  exit code 语义变化
- **MINOR**：新增能力且向后兼容（新字段可选、新 finding 不改变既有决策）
- **PATCH**：bug 修复、文档、不改变判定的调整

版本号同步出现在：`SKILL.md` frontmatter、`scripts/gate_check.py` 的
`__version__`、`CHANGELOG.md`。

## 行为准则

见 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。简言之：对事不对人，
证据说话 —— 这本来就是本项目的主题。
