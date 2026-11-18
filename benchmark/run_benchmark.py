#!/usr/bin/env python3
"""Evidence Gate benchmark — labeled-corpus, gate-level evaluation.

Runs every entry in benchmark/corpus/ through scripts/gate_check.py and
scores the decision against the entry's ground-truth expectation:

  should_pass  — the claim is honest and properly evidenced AS FILED; the
                 gate should let it through (PASS / PASS_WITH_CAVEAT).
  should_block — the claim overclaims, is contradicted, or is unevidenced;
                 the gate should block it (VERIFY_REQUIRED / ABSTAIN / REJECT).

Core metrics:

  False Acceptance Rate (FAR) — should_block entries the gate let through.
                                An overclaim shipped as a conclusion.
  False Rejection Rate (FRR)  — should_pass entries the gate blocked.
                                Over-blocking punishes honest conclusions.

This is a GATE-level benchmark: it measures the deterministic checker on
inputs with known ground truth. It does NOT measure end-to-end agent
accuracy (that requires the agent-level protocol in AGENT-PROTOCOL.md,
not yet run — see docs for what is and is not measured).

All entries run with --offline so URL anchors take the attestation path;
results are deterministic and network-independent.

Usage:
    python3 benchmark/run_benchmark.py [--report]

Exit code: 0 if FAR == 0 and FRR == 0 (CI gate), 1 otherwise.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parent
ROOT = BENCH_DIR.parent
GATE_SCRIPT = ROOT / "scripts" / "gate_check.py"
CORPUS_DIR = BENCH_DIR / "corpus"
RESULTS_PATH = BENCH_DIR / "RESULTS.md"

PASS_DECISIONS = {"PASS", "PASS_WITH_CAVEAT"}
BLOCK_DECISIONS = {"VERIFY_REQUIRED", "ABSTAIN", "REJECT"}


def run_entry(entry: dict) -> dict:
    """Run one corpus entry through the gate; return decision + latency."""
    cmd = [sys.executable, str(GATE_SCRIPT), "--json", "--no-log", "--offline", "-"] \
        + entry.get("args", [])
    t0 = time.perf_counter()
    proc = subprocess.run(
        cmd,
        input=json.dumps(entry["input"], ensure_ascii=False),
        capture_output=True, text=True, cwd=ROOT,
    )
    latency_ms = (time.perf_counter() - t0) * 1000
    if proc.returncode == 2:
        return {"decision": "INPUT_ERROR", "latency_ms": latency_ms}
    try:
        decision = json.loads(proc.stdout).get("decision")
    except json.JSONDecodeError:
        decision = "PARSE_ERROR"
    return {"decision": decision, "latency_ms": latency_ms}


def main() -> int:
    entries = sorted(CORPUS_DIR.glob("*.json"))
    if not entries:
        print("FATAL: no corpus entries found", file=sys.stderr)
        return 1

    rows, dist = [], {}
    n_pass = n_block = far = frr = 0
    lat_total = 0.0
    for path in entries:
        entry = json.loads(path.read_text(encoding="utf-8"))
        expect = entry["expectation"]
        result = run_entry(entry)
        decision = result["decision"]
        dist[decision] = dist.get(decision, 0) + 1
        lat_total += result["latency_ms"]

        if expect == "should_pass":
            n_pass += 1
            ok = decision in PASS_DECISIONS
            if not ok:
                frr += 1
        else:  # should_block
            n_block += 1
            ok = decision in BLOCK_DECISIONS
            if not ok:
                far += 1
        rows.append((entry["id"], entry["name"], expect, decision,
                     result["latency_ms"], ok))

    total = len(rows)
    correct = sum(1 for r in rows if r[5])
    accuracy = correct / total
    far_rate = far / n_block if n_block else 0.0
    frr_rate = frr / n_pass if n_pass else 0.0
    mean_ms = lat_total / total

    lines = [
        "# Evidence Gate Benchmark — Results",
        "",
        f"- 运行时间：{time.strftime('%Y-%m-%d %H:%M')}",
        f"- 语料：`benchmark/corpus/`（{total} 条：should_pass {n_pass} · should_block {n_block}）",
        "- 模式：gate-level（确定性检查器对带真值输入的判定），`--offline`",
        "- 指标定义：FAR = 应拦截而被放行（过度声明流出）；FRR = 应放行而被拦截（误伤诚实结论）",
        "",
        "| 指标 | 结果 |",
        "|------|------|",
        f"| Accuracy | {correct}/{total} ({accuracy:.1%}) |",
        f"| **False Acceptance Rate (FAR)** | {far}/{n_block} ({far_rate:.1%}) |",
        f"| **False Rejection Rate (FRR)** | {frr}/{n_pass} ({frr_rate:.1%}) |",
        f"| Mean latency | {mean_ms:.0f} ms/entry（含 Python 进程启动，本地单机） |",
        "",
        "决策分布：" + " · ".join(f"{k} {v}" for k, v in sorted(dist.items())),
        "",
        "## 明细",
        "",
        "| ID | 名称 | 真值 | 判定 | 耗时(ms) | 结果 |",
        "|----|------|------|------|----------|------|",
    ]
    for eid, name, expect, decision, ms, ok in rows:
        lines.append(f"| {eid} | {name} | {expect} | {decision} | {ms:.0f} | "
                     f"{'✅' if ok else '❌'} |")
    lines += [
        "",
        "## 未测量的部分（诚实边界）",
        "",
        "- 本基准只测**闸门本身**（确定性判定器 + 输入真值），不测 Agent 端到端准确率。",
        "- Agent-level 基准（baseline agent vs agent+gate 的 Accuracy / Hallucination "
        "Rate / Cost 等）协议见 `benchmark/AGENT-PROTOCOL.md`，**尚未运行**，"
        "因此本项目不宣称任何端到端准确率提升。",
        "- FAR/FRR 仅对本语料成立；语料由维护者构造，存在构造者偏差，"
        "欢迎社区扩充语料（见 CONTRIBUTING.md）。",
        "",
    ]
    report = "\n".join(lines) + "\n"

    print(f"corpus: {total} entries (should_pass {n_pass} / should_block {n_block})")
    print(f"Accuracy: {correct}/{total} ({accuracy:.1%})")
    print(f"False Acceptance Rate (FAR): {far}/{n_block} ({far_rate:.1%})")
    print(f"False Rejection Rate (FRR): {frr}/{n_pass} ({frr_rate:.1%})")
    print(f"Mean latency: {mean_ms:.0f} ms/entry (incl. interpreter startup)")
    print("Decisions: " + " · ".join(f"{k} {v}" for k, v in sorted(dist.items())))
    for eid, name, expect, decision, ms, ok in rows:
        if not ok:
            print(f"  ✗ {eid} {name}: expected {expect}, got {decision}")

    if "--report" in sys.argv:
        RESULTS_PATH.write_text(report, encoding="utf-8")
        print(f"\nReport written to {RESULTS_PATH}")

    # CI gate: zero false accepts AND zero false rejects on the labeled corpus.
    return 0 if far == 0 and frr == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
