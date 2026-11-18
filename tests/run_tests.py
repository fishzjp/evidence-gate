#!/usr/bin/env python3
"""Test runner for the Evidence Gate skill.

Runs every fixture in tests/cases/ through the gate script and checks
decision, evidence level, and reason content against expectations.
Writes tests/TEST-REPORT.md with the results.

Usage:
    python3 tests/run_tests.py [--report]

Exit code: 0 if all cases pass, 1 otherwise.
"""
import json
import subprocess
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
GATE_SCRIPT = TESTS_DIR.parent / "scripts" / "gate_check.py"
CASES_DIR = TESTS_DIR / "cases"
REPORT_PATH = TESTS_DIR / "TEST-REPORT.md"

# Decision -> expected exit code (documented contract of gate_check.py)
EXIT_CODES = {"PASS": 0, "PASS_WITH_CAVEAT": 0, "VERIFY_REQUIRED": 10,
              "ABSTAIN": 15, "REJECT": 20}

STRENGTH_ORDER = ["hypothesis", "possibly", "likely", "judged", "verified", "cross_verified", "absolute"]


def run_case(case: dict) -> dict:
    """Run one case through gate_check.py, return a result record."""
    cmd = [sys.executable, str(GATE_SCRIPT), "--json", "--no-log", "-"] \
        + case.get("args", [])
    proc = subprocess.run(
        cmd,
        input=json.dumps(case["input"], ensure_ascii=False),
        capture_output=True,
        text=True,
        cwd=TESTS_DIR.parent,
    )
    result = {
        "case": case["case"],
        "name": case["name"],
        "scenario": case["scenario"],
        "input": case["input"],
        "expected": case["expected"],
        "exit_code": proc.returncode,
        "stderr": proc.stderr.strip(),
        "checks": [],
        "ok": True,
    }
    if proc.returncode == 2:  # input error
        result["ok"] = False
        result["checks"].append(("run", False, f"gate script rejected input: {proc.stderr.strip()}"))
        result["actual"] = {"decision": "INPUT_ERROR", "evidence_level": "?", "reason": ""}
        return result
    try:
        result["actual"] = json.loads(proc.stdout)
    except json.JSONDecodeError:
        result["ok"] = False
        result["checks"].append(("run", False, f"no JSON on stdout: {proc.stdout[:200]}"))
        result["actual"] = {"decision": "PARSE_ERROR", "evidence_level": "?", "reason": ""}
        return result

    exp = case["expected"]
    act = result["actual"]

    if "decision" in exp:
        ok = act.get("decision") == exp["decision"]
        result["checks"].append((f"decision == {exp['decision']}", ok, act.get("decision")))
        result["ok"] &= ok
        code_ok = proc.returncode == EXIT_CODES[exp["decision"]]
        result["checks"].append((f"exit code == {EXIT_CODES[exp['decision']]}", code_ok, proc.returncode))
        result["ok"] &= code_ok
    if "evidence_level" in exp:
        ok = act.get("evidence_level") == exp["evidence_level"]
        result["checks"].append((f"evidence_level == {exp['evidence_level']}", ok, act.get("evidence_level")))
        result["ok"] &= ok
    for needle in exp.get("reason_contains", []):
        ok = needle.lower() in (act.get("reason") or "").lower()
        result["checks"].append((f"reason contains '{needle}'", ok, (act.get("reason") or "")[:160]))
        result["ok"] &= ok
    if "allowed_strength_max" in exp:
        allowed = act.get("allowed_strength")
        cap = exp["allowed_strength_max"]
        ok = allowed in (None, cap) or STRENGTH_ORDER.index(allowed) <= STRENGTH_ORDER.index(cap)
        result["checks"].append((f"allowed_strength <= {cap}", ok, allowed))
        result["ok"] &= ok
    return result


def render_report(results: list) -> str:
    lines = [
        "# Evidence Gate — 测试报告",
        "",
        f"- 测试时间：{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"- 被测脚本：`scripts/gate_check.py`",
        f"- 用例数：{len(results)}，通过：{sum(1 for r in results if r['ok'])}，失败：{sum(1 for r in results if not r['ok'])}",
        "",
        "## 结果总表",
        "",
        "| Case | 输入结论 | 证据情况 | Evidence Level | Gate Decision | 预期结果 | 实际结果 |",
        "|------|----------|----------|----------------|---------------|----------|----------|",
    ]
    for r in results:
        inp = r["input"]
        kinds = ", ".join(sorted({e["kind"] for e in inp.get("evidence", [])})) or "无"
        ver = "有执行验证" if inp.get("verification", {}).get("executed") else "未执行"
        counters = len(inp.get("counter_evidence", []))
        evidence_desc = f"{kinds}；{ver}；反证 {counters} 条"
        exp_d = r["expected"]["decision"]
        act_d = r["actual"]["decision"] + ("" if r["ok"] else " ✗")
        concl = inp["conclusion"]
        if len(concl) > 38:
            concl = concl[:38] + "…"
        lines.append(
            f"| {r['case']} ({r['name']}) | {concl} | {evidence_desc} | "
            f"{r['actual'].get('evidence_level', '?')} | {act_d} | {exp_d} @ {r['expected'].get('evidence_level', '—')} | "
            f"{'✅ 通过' if r['ok'] else '❌ 见明细'} |"
        )
    lines += ["", "## 各用例明细", ""]
    for r in results:
        lines.append(f"### Case {r['case']} — {r['name']}")
        lines.append("")
        lines.append(f"**场景**：{r['scenario']}")
        lines.append("")
        lines.append("```")
        lines.append(f"Evidence Level : {r['actual'].get('evidence_level')}")
        lines.append(f"Decision       : {r['actual'].get('decision')} (exit {r['exit_code']})")
        lines.append(f"Confidence     : {r['actual'].get('confidence')}")
        lines.append(f"Allowed wording: {r['actual'].get('allowed_wording') or r['actual'].get('allowed_strength')}")
        lines.append(f"Reason         : {r['actual'].get('reason')}")
        req = r["actual"].get("required_actions")
        if req:
            lines.append(f"Required actions: {'; '.join(req)}")
        lines.append("```")
        lines.append("")
        for label, ok, detail in r["checks"]:
            mark = "✅" if ok else "❌"
            d = detail if not ok else detail
            lines.append(f"- {mark} {label} → {d}")
        lines.append("")
    return "\n".join(lines) + "\n"


def run_cli_checks() -> list:
    """P0-5: audit log + calibration loop CLI behaviors."""
    import tempfile
    checks = []
    log = tempfile.mktemp(suffix=".jsonl")
    inp = {"conclusion": "CLI 冒烟测试结论", "type": "FACT", "claimed_strength": "judged",
           "risk_tier": "low",
           "evidence": [{"kind": "official_doc",
                         "detail": "tests/fixtures/fastify-server.md",
                         "anchor": "tests/fixtures/fastify-server.md",
                         "quote": "server.listen() returns a Promise"}],
           "verification": {"executed": False, "env_independent": "unknown",
                            "validates_target": "unknown"},
           "counter_evidence": [], "generalization": None}
    base = [sys.executable, str(GATE_SCRIPT)]
    # 1. log entry written with gate_id + decision
    subprocess.run(base + ["--json", "--log", log, "-"],
                   input=json.dumps(inp, ensure_ascii=False),
                   capture_output=True, text=True, cwd=TESTS_DIR.parent)
    try:
        entries = [json.loads(l) for l in Path(log).read_text().splitlines() if l.strip()]
        ok = bool(entries) and entries[-1].get("gate_id") and entries[-1].get("decision") == "PASS"
        gate_id = entries[-1]["gate_id"] if entries else None
    except Exception as exc:
        ok, gate_id = False, None
        entries = []
    checks.append(("audit log entry (gate_id+decision)", ok, gate_id))
    # 2. mark-outcome updates the entry
    if gate_id:
        subprocess.run(base + ["--mark-outcome", gate_id, "correct", "--log", log],
                       capture_output=True, text=True, cwd=TESTS_DIR.parent)
        entries = [json.loads(l) for l in Path(log).read_text().splitlines() if l.strip()]
        ok = entries[-1].get("outcome") == "correct"
        checks.append((f"--mark-outcome {gate_id} correct", ok, entries[-1].get("outcome")))
    # 3. calibration report reflects the outcome
    proc = subprocess.run(base + ["--calibration", "--log", log],
                          capture_output=True, text=True, cwd=TESTS_DIR.parent)
    ok = "L2" in proc.stdout and "100" in proc.stdout
    checks.append(("--calibration reports per-level accuracy", ok,
                   proc.stdout.strip().splitlines()[:3]))
    try:
        Path(log).unlink(missing_ok=True)
    except OSError:
        pass
    return checks


def main() -> int:
    if not GATE_SCRIPT.exists():
        print(f"FATAL: gate script not found at {GATE_SCRIPT}", file=sys.stderr)
        return 1
    cases = sorted(CASES_DIR.glob("case*.json"))
    if not cases:
        print("FATAL: no case files found", file=sys.stderr)
        return 1
    results = []
    failures = 0
    for path in cases:
        case = json.loads(path.read_text(encoding="utf-8"))
        r = run_case(case)
        results.append(r)
        status = "PASS" if r["ok"] else "FAIL"
        if not r["ok"]:
            failures += 1
        print(f"[{status}] case {r['case']:02d} {r['name']}: decision={r['actual']['decision']} "
              f"level={r['actual'].get('evidence_level')}")
        for label, ok, detail in r["checks"]:
            if not ok:
                print(f"       ✗ {label} (got: {detail})")
    report = render_report(results)
    if "--report" in sys.argv:
        cli = run_cli_checks()
        report += "\n## CLI 行为子测试（审计日志 / 校准回路，P0-5）\n\n"
        for label, ok, detail in cli:
            report += f"- {'✅' if ok else '❌'} {label} → {detail}\n"
        REPORT_PATH.write_text(report, encoding="utf-8")
        print(f"\nReport written to {REPORT_PATH}")
    cli = run_cli_checks()
    cli_fail = 0
    for label, ok, detail in cli:
        if not ok:
            cli_fail += 1
        print(f"[{'PASS' if ok else 'FAIL'}] cli: {label}")
    total = len(results) + len(cli)
    passed = len(results) - failures + len(cli) - cli_fail
    print(f"\n{passed}/{total} checks passed")
    return 0 if failures == 0 and cli_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
