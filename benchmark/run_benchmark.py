#!/usr/bin/env python3
"""Evidence Gate benchmark — labeled-corpus, gate-level evaluation.

Runs every entry in benchmark/corpus/ through scripts/gate_check.py and
scores the decision against the entry's ground-truth expectation:

  should_pass  — the claim is honest and properly evidenced AS FILED; the
                 gate should let it through (PASS / PASS_WITH_CAVEAT).
  should_block — the claim overclaims, is contradicted, or is unevidenced;
                 the gate should block it (VERIFY_REQUIRED / ABSTAIN / REJECT).

Suites (entry field "suite", default "core"):
  core        — the original v2 corpus: regression protection.
  adversarial — v3 attack/defense entries: misleading quotes, correlated
                evidence, outdated evidence, same-model false verification,
                attested-only L4, channel mismatch + honest counterparts
                (FRR guards for every new rule).

Core metrics:

  False Acceptance Rate (FAR) — should_block entries the gate let through.
                                An overclaim shipped as a conclusion.
  False Rejection Rate (FRR)  — should_pass entries the gate blocked.
                                Over-blocking punishes honest conclusions.

This is a GATE-level benchmark: it measures the deterministic checker on
inputs with known ground truth. It does NOT measure end-to-end agent
accuracy (that requires an agent-level protocol — defined but not yet
run; see docs for what is and is not measured).

All entries run with --offline so URL anchors take the attestation path;
results are deterministic and network-independent.

Usage:
    python3 benchmark/run_benchmark.py [--report] [--gate PATH]

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


def run_entry(gate: Path, entry: dict) -> dict:
    """Run one corpus entry through the gate; return decision + latency."""
    cmd = [sys.executable, str(gate), "--json", "--no-log", "--offline", "-"] \
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
    gate = GATE_SCRIPT
    if "--gate" in sys.argv:
        i = sys.argv.index("--gate")
        if i + 1 >= len(sys.argv):
            print("FATAL: --gate requires a path argument", file=sys.stderr)
            return 1
        gate = Path(sys.argv[i + 1])
        if not gate.exists():
            print(f"FATAL: gate script not found: {gate}", file=sys.stderr)
            return 1
    entries = sorted(CORPUS_DIR.glob("*.json"))
    if not entries:
        print("FATAL: no corpus entries found", file=sys.stderr)
        return 1

    rows = []
    suites = {}
    for path in entries:
        entry = json.loads(path.read_text(encoding="utf-8"))
        expect = entry["expectation"]
        suite = entry.get("suite", "core")
        result = run_entry(gate, entry)
        decision = result["decision"]
        s = suites.setdefault(suite, {"n": 0, "pass": 0, "block": 0,
                                      "far": 0, "frr": 0, "lat": 0.0, "dist": {}})
        s["n"] += 1
        s["lat"] += result["latency_ms"]
        s["dist"][decision] = s["dist"].get(decision, 0) + 1

        if expect == "should_pass":
            s["pass"] += 1
            ok = decision in PASS_DECISIONS
            if not ok:
                s["frr"] += 1
        else:  # should_block
            s["block"] += 1
            ok = decision in BLOCK_DECISIONS
            if not ok:
                s["far"] += 1
        rows.append((entry["id"], entry["name"], suite, expect, decision,
                     result["latency_ms"], ok))

    total = len(rows)
    correct = sum(1 for r in rows if r[6])
    far = sum(s["far"] for s in suites.values())
    frr = sum(s["frr"] for s in suites.values())
    n_block = sum(s["block"] for s in suites.values())
    n_pass = sum(s["pass"] for s in suites.values())
    mean_ms = sum(s["lat"] for s in suites.values()) / total

    lines = [
        "# Evidence Gate Benchmark — Results",
        "",
        f"- 运行时间：{time.strftime('%Y-%m-%d %H:%M')}",
        f"- Gate：`{gate.relative_to(ROOT) if gate.is_relative_to(ROOT) else gate}`",
        f"- 语料：`benchmark/corpus/`（{total} 条："
        + " · ".join(f"{name} {s['n']}" for name, s in sorted(suites.items()))
        + "）",
        "- 模式：gate-level（确定性检查器对带真值输入的判定），`--offline`",
        "- 指标定义：FAR = 应拦截而被放行（过度声明流出）；FRR = 应放行而被拦截（误伤诚实结论）",
        "",
        "| 指标 | 结果 |",
        "|------|------|",
        f"| Accuracy | {correct}/{total} ({correct/total:.1%}) |",
        f"| **False Acceptance Rate (FAR)** | {far}/{n_block} "
        f"({far/n_block:.1%}) |" if n_block else
        "| **False Acceptance Rate (FAR)** | n/a (no should_block entries) |",
        f"| **False Rejection Rate (FRR)** | {frr}/{n_pass} "
        f"({frr/n_pass:.1%}) |" if n_pass else
        "| **False Rejection Rate (FRR)** | n/a (no should_pass entries) |",
        f"| Mean latency | {mean_ms:.0f} ms/entry（含 Python 进程启动，本地单机） |",
        "",
    ]
    for name, s in sorted(suites.items()):
        far_r = s["far"] / s["block"] if s["block"] else 0.0
        frr_r = s["frr"] / s["pass"] if s["pass"] else 0.0
        acc = (s["n"] - s["far"] - s["frr"]) / s["n"]
        lines += [
            f"## suite: {name}（{s['n']} 条：should_pass {s['pass']} · should_block {s['block']}）",
            "",
            f"Accuracy {acc:.1%} · FAR {s['far']}/{s['block']} ({far_r:.1%}) · "
            f"FRR {s['frr']}/{s['pass']} ({frr_r:.1%}) · "
            f"latency {s['lat']/s['n']:.0f} ms",
            "",
            "| ID | 名称 | 真值 | 判定 | 耗时(ms) | 结果 |",
            "|----|------|------|------|----------|------|",
        ]
        for eid, name2, suite, expect, decision, ms, ok in rows:
            if suite != name:
                continue
            lines.append(f"| {eid} | {name2} | {expect} | {decision} | {ms:.0f} | "
                         f"{'✅' if ok else '❌'} |")
        lines.append("")

    lines += [
        "## 未测量的部分（诚实边界）",
        "",
        "- 本基准只测**闸门本身**（确定性判定器 + 输入真值），不测 Agent 端到端准确率。",
        "- Agent-level 基准（baseline agent vs agent+gate 的 Accuracy / Hallucination "
        "Rate / Cost 等）协议已定义、**尚未运行**，"
        "因此本项目不宣称任何端到端准确率提升。",
        "- FAR/FRR 仅对本语料成立；语料由维护者构造，存在构造者偏差，"
        "欢迎社区扩充语料（见 CONTRIBUTING.md）。",
        "- adversarial suite 的预期（should_block/should_pass）按 v3 认识论标准"
        "构造（异构验证、独立性、时效），与 core suite 的 v2 标准在'何谓充分"
        "证据'上存在哲学差异——这正是升级本身；1.0 vs 2.0 的对照可用 "
        "`python3 benchmark/run_ab.py` 复现。",
        "",
    ]
    report = "\n".join(lines) + "\n"

    print(f"gate: {gate}")
    print(f"corpus: {total} entries "
          + ", ".join(f"{name} {s['n']}" for name, s in sorted(suites.items())))
    print(f"Accuracy: {correct}/{total} ({correct/total:.1%})")
    print(f"False Acceptance Rate (FAR): {far}/{n_block} "
          f"({far/n_block:.1%})" if n_block else "FAR: n/a")
    print(f"False Rejection Rate (FRR): {frr}/{n_pass} "
          f"({frr/n_pass:.1%})" if n_pass else "FRR: n/a")
    print(f"Mean latency: {mean_ms:.0f} ms/entry (incl. interpreter startup)")
    for name, s in sorted(suites.items()):
        dist = " · ".join(f"{k} {v}" for k, v in sorted(s["dist"].items()))
        print(f"[{name}] FAR {s['far']}/{s['block']} FRR {s['frr']}/{s['pass']} "
              f"decisions: {dist}")
    for row in rows:
        if not row[6]:
            print(f"  ✗ {row[0]} {row[1]}: expected {row[3]}, got {row[4]}")

    if "--report" in sys.argv:
        RESULTS_PATH.write_text(report, encoding="utf-8")
        print(f"\nReport written to {RESULTS_PATH}")

    # CI gate: zero false accepts AND zero false rejects on the labeled corpus.
    return 0 if far == 0 and frr == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
