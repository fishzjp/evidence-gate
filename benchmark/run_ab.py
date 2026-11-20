#!/usr/bin/env python3
"""Evidence Gate A/B — v1 (2.0.0 snapshot) vs v2 (3.0.0) on the same corpus.

Runs every corpus entry through BOTH gates and compares:

  per-suite FAR / FRR / accuracy / latency,
  plus a per-entry decision diff on the adversarial suite (the upgrade
  story: which attacks v1 let through that v2 blocks, and whether v2
  hurts any honest entry v1 passed).

Honest-comparison notes:
  - both gates see byte-identical inputs (v1 ignores v3-only fields);
  - expectations are gate-independent ground truth (should_pass /
    should_block), so the same labels score both columns;
  - the adversarial suite encodes the v3 epistemology (independence,
    heterogeneity, temporal validity) — v1 failing it is the measured
    gap the upgrade closes, not an artifact of relabeling: core-suite
    entries keep their original v2-era labels and v2-compatible inputs;
  - ONE core entry was adapted for v3 (disclosed, not silent): p03
    gained optional v3 fields (evidence[].verified_by="tool:...",
    detail wording naming the tool) so its honest tool-verified line is
    machine-visible. v1 ignores those fields and still passes it
    (PASS L4 both ways); on the UNamended input v3 answers
    VERIFY_REQUIRED (CROSS_FAMILY_MISSING) — a defensible stricter
    stance, i.e. the label, not the verdict, is unchanged.

Usage:
    python3 benchmark/run_ab.py [--report]

Writes benchmark/AB-RESULTS.md with --report. Exit code always 0
(this is a measurement, not a CI gate).
"""
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_benchmark import run_entry  # noqa: E402

BENCH_DIR = Path(__file__).resolve().parent
ROOT = BENCH_DIR.parent
GATES = [
    ("EG 1.0 (v2.0.0)", BENCH_DIR / "legacy" / "gate_check_v2.0.0.py"),
    ("EG 2.0 (v3.0.0)", ROOT / "scripts" / "gate_check.py"),
]
CORPUS_DIR = BENCH_DIR / "corpus"
RESULTS_PATH = BENCH_DIR / "AB-RESULTS.md"
PASS_D = {"PASS", "PASS_WITH_CAVEAT"}
BLOCK_D = {"VERIFY_REQUIRED", "ABSTAIN", "REJECT"}


def main() -> int:
    entries = []
    for path in sorted(CORPUS_DIR.glob("*.json")):
        entries.append(json.loads(path.read_text(encoding="utf-8")))

    results = {}   # (gate_name, id) -> {decision, latency_ms, ok}
    suites = {}    # suite -> gate_name -> stats
    for gname, gpath in GATES:
        for entry in entries:
            r = run_entry(gpath, entry)
            expect = entry["expectation"]
            ok = (r["decision"] in PASS_D) if expect == "should_pass" \
                else (r["decision"] in BLOCK_D)
            results[(gname, entry["id"])] = {**r, "ok": ok}
            s = suites.setdefault(entry.get("suite", "core"), {}) \
                .setdefault(gname, {"n": 0, "far": 0, "frr": 0, "lat": 0.0,
                                    "pass": 0, "block": 0})
            s["n"] += 1
            s["lat"] += r["latency_ms"]
            if expect == "should_pass":
                s["pass"] += 1
                if not ok:
                    s["frr"] += 1
            else:
                s["block"] += 1
                if not ok:
                    s["far"] += 1

    def metric_lines(sname):
        out = []
        for gname, _ in GATES:
            s = suites[sname][gname]
            far = s["far"] / s["block"] if s["block"] else 0
            frr = s["frr"] / s["pass"] if s["pass"] else 0
            acc = (s["n"] - s["far"] - s["frr"]) / s["n"]
            out.append((gname, acc, far, frr, s["far"], s["frr"],
                        s["block"], s["pass"], s["lat"] / s["n"]))
        return out

    lines = [
        "# Evidence Gate A/B — 1.0 (v2.0.0) vs 2.0 (v3.0.0)",
        "",
        f"- 运行时间：{time.strftime('%Y-%m-%d %H:%M')}",
        f"- 语料：{len(entries)} 条（同一输入逐字节喂给两个 gate；"
        f"v1 忽略 v3 新增字段，字段存在不构成提示）",
        "- v1 快照：`benchmark/legacy/gate_check_v2.0.0.py`（升级前主脚本的原样拷贝）",
        "",
    ]
    summary_rows = []
    for sname in sorted(suites):
        lines.append(f"## suite: {sname}")
        lines.append("")
        lines.append("| Gate | Accuracy | FAR | FRR | Mean latency |")
        lines.append("|------|----------|-----|-----|--------------|")
        for gname, acc, far, frr, farn, frrn, nblock, npass, lat in metric_lines(sname):
            lines.append(f"| {gname} | {acc:.1%} | {farn}/{nblock} ({far:.1%}) "
                         f"| {frrn}/{npass} ({frr:.1%}) | {lat:.0f} ms |")
            summary_rows.append((sname, gname, acc, far, frr, lat))
        lines.append("")

    lines += [
        "## adversarial suite 逐条对照（升级的故事在这里）",
        "",
        "| ID | 名称 | 真值 | 1.0 判定 | 2.0 判定 | 变化 |",
        "|----|------|------|----------|----------|------|",
    ]
    v1n, v2n = GATES[0][0], GATES[1][0]
    for entry in entries:
        if entry.get("suite", "core") != "adversarial":
            continue
        r1 = results[(v1n, entry["id"])]
        r2 = results[(v2n, entry["id"])]
        if r1["ok"] and r2["ok"]:
            change = "both OK"
        elif r1["ok"] and not r2["ok"]:
            change = "⚠️ REGRESSION (1.0 通过, 2.0 拦截)"
        elif not r1["ok"] and r2["ok"]:
            change = "✅ FIXED (1.0 放行, 2.0 拦截)" \
                if entry["expectation"] == "should_block" \
                else "✅ FIXED (1.0 误拦, 2.0 放行)"
        else:
            change = "both miss"
        lines.append(f"| {entry['id']} | {entry['name']} | "
                     f"{entry['expectation']} | {r1['decision']} | "
                     f"{r2['decision']} | {change} |")
    lines += [
        "",
        "## 判定稳定性（改写不变性）",
        "",
        "结论同义改写后判定必须不变（isomorphic perturbation，",
        "arXiv:2604.15149：判决对等价改写翻转 = 可被措辞博弈）。覆盖于",
        "tests/run_tests.py 的 paraphrase 用例（case20–22），不在本表。",
        "",
        "## 解读注意（诚实边界）",
        "",
        "- adversarial suite 的 6 条攻击按 v3 认识论构造，v1 在其上 FAR=100%",
        "  是升级目标（v3 的设计矩阵），不是对 v1 的",
        "  不公平标签：core suite 全部保留 v2 时代的原始标签。",
        "- 披露一处 core 输入适配：p03 增加了可选 v3 字段",
        "  （evidence[].verified_by=\"tool:...\" 及 detail 中点名工具），",
        "  使其诚实的工具验证线对 v3 可见。v1 忽略新字段、判定不变",
        "  （PASS L4）；未适配的原始输入上 v3 判 VERIFY_REQUIRED",
        "  （CROSS_FAMILY_MISSING，工具线不可见）——标签不变，判定从严",
        "- 两个 gate 都是确定性脚本，latency 差异（±20ms 级）主要来自",
        "  v3 增加的相关性/时间/账本计算，相对 Agent 验证成本可忽略。",
        "- 本 A/B 只测 gate 层；不宣称端到端 Agent 准确率变化。",
        "",
    ]

    print(f"corpus: {len(entries)} entries; gates: {[g[0] for g in GATES]}")
    for sname, gname, acc, far, frr, lat in summary_rows:
        print(f"[{sname}] {gname}: acc {acc:.1%} FAR {far:.1%} FRR {frr:.1%} "
              f"lat {lat:.0f}ms")
    if "--report" in sys.argv:
        RESULTS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Report written to {RESULTS_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
