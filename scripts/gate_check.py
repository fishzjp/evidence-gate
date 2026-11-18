#!/usr/bin/env python3
"""Evidence Gate v2 — deterministic conclusion-quality gate.

Evaluates one conclusion against its evidence and decides whether the
conclusion may be output, at what strength, and with what caveats.

Core rule: CONCLUSION STRENGTH MUST NOT EXCEED EVIDENCE STRENGTH.

v2 upgrades (research-driven, see RESEARCH-SURVEY.md in the project root):
  P0-1 Anchor three-stage check — an anchor must (a) resolve (file/URL),
       (b) have its actual content inspected, and (c) contain the quoted
       support. "Citation exists" no longer counts as evidence
       (SourceCheckup 2025: 50-90% of cited answers not fully supported).
  P0-2 Counter-search isolation — a "cross_verified" claim requires the
       counter-evidence search to have run in an isolated context
       (SGV, ICLR 2026: agreement bias resists more compute).
  P0-3 ABSTAIN — when required evidence is not obtainable, refuse the
       conclusion and state the gap (R-Tuning / AgentAbstain line).
  P0-4 Pre-irreversible-action gate — `--gate-point pre-action` tightens
       requirements before deploy/delete/send/merge (AgentAbstain 2026:
       agents act irreversibly before realizing they should abstain).
  P0-5 Audit log + calibration loop — every gate run is appended to a
       JSONL log with a gate_id and verifier identity; outcomes can be
       marked later (`--mark-outcome`) and aggregated (`--calibration`)
       so the L0-L4 wording map is validated against reality, not vibes.

Usage:
    gate_check.py INPUT.json [flags]     # file argument
    ... | gate_check.py - [flags]        # stdin
    gate_check.py --mark-outcome ID correct|incorrect|unknown [--log P]
    gate_check.py --calibration [--log P]

Flags: --json  --log PATH  --no-log  --offline  --gate-point conclusion|pre-action

Exit codes:
      0  PASS / PASS_WITH_CAVEAT
     10  VERIFY_REQUIRED
     15  ABSTAIN                (evidence not obtainable — refuse to conclude)
     20  REJECT
      2  input error

Input schema (JSON; v1 fields remain valid):
{
  "conclusion": "...",                    # required
  "type": "FACT|INFERENCE|HYPOTHESIS|RECOMMENDATION|EXPERIMENT_RESULT",
  "claimed_strength": "hypothesis|possibly|likely|judged|verified|cross_verified|absolute",
  "risk_tier": "low|medium|high|extreme",           # default medium
  "evidence_obtainable": "yes|no|unknown",          # no -> ABSTAIN on shortfall
  "counter_search_context": "isolated|same",        # cross_verified needs isolated
  "verifier": {"id": "...", "protocol": "..."},     # optional, logged for audit
  "evidence": [
    {"kind": "...", "detail": "...", "group": "optional",
     "anchor": "path-or-url",            # explicit anchor overrides detection
     "quote": "text the anchor must contain",   # mechanical entailment check
     "content_supports": "supported|partial|unsupported|not_checked"}
  ],
  "verification": {"executed": bool, "detail": "...",
                   "env_independent": true|false|"unknown",
                   "validates_target": true|false|"unknown"},
  "counter_evidence": [ {"detail": "...", "status": "unaddressed|explained|refuted",
                         "contradicts": bool} ],
  "generalization": {"sample_size": int, "population_size": int,
                     "statistical_basis": bool}      # or null
}

Evidence kinds:
  direct   : official_doc, source_code, config, data, log, test_result, sample
  indirect : observation, time_correlation, memory, assumption, anecdote

Direct evidence requires BOTH a resolvable anchor AND content-level support
(mechanical quote match, or explicit `content_supports` attestation). A
`quote` that is absent from the anchor, or an anchor that cannot be
resolved, downgrades the item to indirect — citing is not supporting.
"""
import hashlib
import html as html_lib
import json
import os
import re
import subprocess  # noqa: F401  (kept for future tool bridges)
import sys
import time
import urllib.request
from pathlib import Path

__version__ = "2.0.0"
DEFAULT_LOG = ".evidence-gate-log.jsonl"

DIRECT_KINDS = {"official_doc", "source_code", "config", "data", "log",
                "test_result", "sample"}
INDIRECT_KINDS = {"observation", "time_correlation", "memory", "assumption",
                  "anecdote"}
ALL_KINDS = DIRECT_KINDS | INDIRECT_KINDS
TYPES = {"FACT", "INFERENCE", "HYPOTHESIS", "RECOMMENDATION", "EXPERIMENT_RESULT"}
STRENGTHS = ["hypothesis", "possibly", "likely", "judged", "verified",
             "cross_verified", "absolute"]
RISK_TIERS = ["low", "medium", "high", "extreme"]
COUNTER_STATUS = {"unaddressed", "explained", "refuted"}
CONTENT_SUPPORTS = {"supported", "partial", "unsupported", "not_checked"}

STRENGTH_REQ = {"hypothesis": 0, "possibly": 1, "likely": 1, "judged": 2,
                "verified": 3, "cross_verified": 4, "absolute": 4}
LEVEL_WORDING = {
    0: "假设/推测 (hypothesis only)",
    1: "可能/初步判断 (possibly / preliminary)",
    2: "根据现有证据可以判断 (judged from evidence)",
    3: "已通过实际验证 (verified)",
    4: "已交叉验证 (cross-verified)",
}
LEVEL_STRENGTH = {0: "hypothesis", 1: "possibly", 2: "judged", 3: "verified",
                  4: "cross_verified"}
DECISION_EXIT = {"PASS": 0, "PASS_WITH_CAVEAT": 0, "VERIFY_REQUIRED": 10,
                 "ABSTAIN": 15, "REJECT": 20}

ABSOLUTE_PATTERNS = [
    r"100%", r"全部", r"所有", r"一定", r"完全", r"绝对", r"肯定",
    r"均(?!匀)", r"guarantee", r"\balways\b", r"\bnever\b", r"\bevery\b",
    r"\ball\b",
]
CAUSAL_PATTERNS = [
    r"导致", r"引起", r"是因为", r"归因", r"caused", r"because\s+of",
    r"results\s+in", r"due\s+to",
]
WORKS_PATTERNS = [
    r"可以运行", r"能运行", r"能正常", r"应该能", r"可正常", r"正常运行",
    r"正常工作", r"已修复", r"修复成功", r"已被修复", r"问题已解决", r"已解决",
    r"不会中断", r"不会破坏", r"不会影响", r"\bfixed\b", r"\bworks\b",
    r"will\s+work", r"\bresolved\b", r"\bsucceeds\b",
]
RISK_KEYWORDS = [
    r"benchmark", r"基准", r"数据质量", r"质量", r"去重", r"重复", r"docker",
    r"镜像", r"golden", r"成本", r"预算", r"工期", r"按期", r"验收", r"干净",
    r"合格", r"\bclean\b", r"官方模型",
]
# v1 trace-anchor patterns: prove the agent can POINT at the evidence.
TRACE_PATTERNS = [
    r"https?://",
    r"\w+\.(py|js|ts|go|rs|java|rb|sh|bash|yaml|yml|json|md|conf|config|ini|csv|tsv|txt|log|sql|toml|xml|lock|xlsx|png|jpg)\b",
    r"#[0-9]+",
    r"\bCI\b", r"\bcommit\b", r"\b[0-9a-f]{7,40}\b",
    r"/[a-zA-Z0-9_.-]+(/[a-zA-Z0-9_.-]+)+",
]
URL_RE = re.compile(r"https?://[^\s)）>\"'，。；]+")
PATH_PREFIXES = ("/", "./", "../", "~/")


def matches_any(text: str, patterns) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


# ---------------------------------------------------------------- anchors ---

def extract_anchor(detail: str, anchor_field):
    """Pick the mechanical-check candidate: explicit field > URL > local path."""
    if anchor_field:
        return anchor_field.strip()
    m = URL_RE.search(detail)
    if m:
        return m.group(0)
    for token in re.split(r"[\s（()）,，;；'\"\[\]]+", detail):
        if "/" in token and (re.search(
                r"\.\w{1,8}$", token) or token.startswith(PATH_PREFIXES)):
            return token.rstrip(".,;:。；：")
    return None


def fetch_url(url: str, offline: bool):
    """Fetch URL text (tags stripped). Returns None when offline/failed."""
    if offline:
        return None
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": f"evidence-gate/{__version__}"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            raw = resp.read(200_000).decode("utf-8", errors="replace")
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw,
                      flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        return html_lib.unescape(text)
    except Exception:
        return None


def read_local(path: str):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def quote_in(quote: str, text: str) -> bool:
    # strip markdown emphasis chars: `code`, **bold** — formatting, not content
    clean = lambda t: norm_ws(re.sub(r"[`*_]", "", t or ""))
    return clean(quote) in clean(text)


def check_anchor(ev: dict, offline: bool):
    """Three-stage anchor check. Returns (status, message) where status in:
    mechanical_ok / attested / no_candidate / unresolved / content_unchecked /
    quote_missing / missing / contradicted / partial"""
    supports = ev.get("content_supports", "not_checked")
    if supports == "unsupported":
        return "contradicted", ("anchor content attested to NOT support the "
                                "claim (content_supports=unsupported)")
    detail = ev.get("detail", "")
    anchor = extract_anchor(detail, ev.get("anchor"))
    if anchor is None:
        return "no_candidate", "no mechanically checkable anchor in detail"
    quote = ev.get("quote")
    if anchor.startswith(("http://", "https://")):
        text = fetch_url(anchor, offline)
        if text is None:
            if supports in ("supported", "partial"):
                return "attested", f"URL not fetched here; agent attests content (channel=attested): {anchor}"
            return "unresolved", (f"URL could not be fetched and content is "
                                  f"not attested: {anchor}")
    else:
        text = read_local(anchor)
        if text is None:
            return "missing", f"anchor path does not exist / unreadable: {anchor}"
    if quote:
        if quote_in(quote, text):
            return "mechanical_ok", f"quote verified in anchor: {anchor}"
        return "quote_missing", (f"anchor resolved but does NOT contain the "
                                 f"quoted support “{quote[:50]}”: {anchor}")
    # resolved but nothing to compare
    if supports in ("supported", "partial"):
        return ("attested" if supports == "supported" else "partial"), \
            f"anchor resolved; agent attests content ({supports}): {anchor}"
    return "content_unchecked", (f"anchor resolved but its content was never "
                                 f"checked against the claim (no quote, no "
                                 f"attestation): {anchor}")


# ------------------------------------------------------------------ input ---

def die_input(msg: str):
    print(f"INPUT ERROR: {msg}", file=sys.stderr)
    print("Run gate_check.py --help for the schema.", file=sys.stderr)
    sys.exit(2)


def parse_args(argv):
    opts = {"json": False, "no_log": False, "offline": False,
            "gate_point": "conclusion", "log": DEFAULT_LOG,
            "mark_outcome": None, "calibration": False, "file": "-"}
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--json":
            opts["json"] = True
        elif a == "--no-log":
            opts["no_log"] = True
        elif a == "--offline":
            opts["offline"] = True
        elif a == "--gate-point":
            i += 1
            if i >= len(argv) or argv[i] not in ("conclusion", "pre-action"):
                die_input("--gate-point must be conclusion or pre-action")
            opts["gate_point"] = argv[i]
        elif a == "--log":
            i += 1
            opts["log"] = argv[i]
        elif a == "--mark-outcome":
            i += 2
            if i >= len(argv):
                die_input("--mark-outcome needs ID and VERDICT")
            opts["mark_outcome"] = (argv[i - 1], argv[i])
        elif a == "--calibration":
            opts["calibration"] = True
        elif a in ("-", "--help", "-h"):
            opts["file"] = a
        elif a.startswith("-"):
            die_input(f"unknown flag: {a}")
        else:
            opts["file"] = a
        i += 1
    return opts


def load_input(path: str) -> dict:
    if path in ("--help", "-h"):
        print(__doc__)
        sys.exit(0)
    if path == "-":
        raw = sys.stdin.read()
    else:
        try:
            raw = Path(path).read_text(encoding="utf-8")
        except OSError as exc:
            die_input(f"cannot read input file: {exc}")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        die_input(f"invalid JSON: {exc}")
    if not isinstance(data, dict):
        die_input("input must be a JSON object")
    return data


def validate(data: dict):
    for field in ("conclusion", "type", "claimed_strength"):
        if not str(data.get(field, "")).strip():
            die_input(f"missing required field: {field}")
    if data["type"] not in TYPES:
        die_input(f"type must be one of {sorted(TYPES)}, got: {data['type']}")
    if data["claimed_strength"] not in STRENGTHS:
        die_input(f"claimed_strength must be one of {STRENGTHS}, "
                  f"got: {data['claimed_strength']}")
    if data.get("risk_tier", "medium") not in RISK_TIERS:
        die_input(f"risk_tier must be one of {RISK_TIERS}")
    if data.get("evidence_obtainable", "unknown") not in ("yes", "no", "unknown"):
        die_input("evidence_obtainable must be yes|no|unknown")
    if data.get("counter_search_context", "same") not in ("isolated", "same"):
        die_input("counter_search_context must be isolated|same")
    for i, ev in enumerate(data.get("evidence") or []):
        if ev.get("kind") not in ALL_KINDS:
            die_input(f"evidence[{i}].kind must be one of {sorted(ALL_KINDS)}, "
                      f"got: {ev.get('kind')}")
        if not str(ev.get("detail", "")).strip():
            die_input(f"evidence[{i}].detail must be non-empty")
        if ev.get("content_supports", "not_checked") not in CONTENT_SUPPORTS:
            die_input(f"evidence[{i}].content_supports must be one of "
                      f"{sorted(CONTENT_SUPPORTS)}")
    for i, ce in enumerate(data.get("counter_evidence") or []):
        if ce.get("status", "unaddressed") not in COUNTER_STATUS:
            die_input(f"counter_evidence[{i}].status must be one of "
                      f"{sorted(COUNTER_STATUS)}")


# ------------------------------------------------------- audit log (P0-5) ---

def log_path(opts) -> Path:
    return Path(opts["log"])


def append_log(opts, entry: dict):
    if opts["no_log"]:
        return
    try:
        with log_path(opts).open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as exc:
        print(f"WARN: could not write gate log: {exc}", file=sys.stderr)


def cmd_mark_outcome(opts):
    gate_id, verdict = opts["mark_outcome"]
    if verdict not in ("correct", "incorrect", "unknown"):
        die_input("outcome verdict must be correct|incorrect|unknown")
    path = log_path(opts)
    if not path.exists():
        die_input(f"log file not found: {path}")
    lines = path.read_text(encoding="utf-8").splitlines()
    updated = 0
    for idx in range(len(lines) - 1, -1, -1):
        if not lines[idx].strip():
            continue
        try:
            entry = json.loads(lines[idx])
        except json.JSONDecodeError:
            continue
        if entry.get("gate_id") == gate_id:
            entry["outcome"] = verdict
            entry["outcome_ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            lines[idx] = json.dumps(entry, ensure_ascii=False)
            updated += 1
            break
    if not updated:
        die_input(f"gate_id not found in log: {gate_id}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"marked {gate_id} -> {verdict}")
    sys.exit(0)


def cmd_calibration(opts):
    path = log_path(opts)
    if not path.exists():
        print(f"No gate log at {path}. Run gates without --no-log to build one.")
        sys.exit(0)
    levels, decisions, known, correct = {}, {}, 0, 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        lv = e.get("evidence_level", "?")
        levels.setdefault(lv, {"n": 0, "known": 0, "correct": 0})
        levels[lv]["n"] += 1
        decisions[e.get("decision", "?")] = decisions.get(e.get("decision", "?"), 0) + 1
        if e.get("outcome") in ("correct", "incorrect"):
            levels[lv]["known"] += 1
            known += 1
            if e["outcome"] == "correct":
                levels[lv]["correct"] += 1
                correct += 1
    print("Evidence Gate calibration (from gate log)")
    print("=" * 52)
    print(f"{'level':<7}{'runs':>6}{'known':>7}{'correct':>9}{'accuracy':>10}")
    for lv in sorted(levels):
        s = levels[lv]
        acc = f"{100.0 * s['correct'] / s['known']:.0f}%" if s["known"] else "—"
        print(f"{lv:<7}{s['n']:>6}{s['known']:>7}{s['correct']:>9}{acc:>10}")
    print("-" * 52)
    print("decisions:", json.dumps(decisions, ensure_ascii=False))
    if known == 0:
        print("\nNo outcomes recorded yet. After conclusions are confirmed or "
              "falsified, run:\n  gate_check.py --mark-outcome <gate_id> "
              "correct|incorrect --log <path>")
    else:
        print(f"\noverall accuracy on known outcomes: "
              f"{100.0 * correct / known:.0f}% ({correct}/{known})")
    sys.exit(0)


# ----------------------------------------------------------------- assess ---

def assess(data: dict, gate_point: str = "conclusion", offline: bool = False):
    conclusion = data["conclusion"]
    ctype = data["type"]
    claimed = data["claimed_strength"]
    original_claimed = claimed
    risk = data.get("risk_tier", "medium")
    findings = []
    caveats = []
    actions = []

    def finding(sev, code, msg):
        findings.append({"severity": sev, "code": code, "message": msg})

    # -- P0-4: pre-irreversible-action gate --------------------------------
    if gate_point == "pre-action":
        if risk in ("low", "medium"):
            finding("info", "G3_PRE_ACTION",
                    "irreversible action pending: risk escalated to 'high'")
            risk = "high"
        else:
            finding("info", "G3_PRE_ACTION",
                    "irreversible action pending (--gate-point pre-action)")

    # -- 1. anti-bypass auto-escalation from the conclusion text ------------
    if matches_any(conclusion, ABSOLUTE_PATTERNS) and claimed != "absolute":
        finding("high", "ABSOLUTE_WORDING",
                f"absolute wording detected in conclusion; claimed_strength "
                f"escalated '{claimed}' -> 'absolute'")
        claimed = "absolute"
    if claimed == "absolute":
        risk = "high" if risk in ("low", "medium") else risk
    if matches_any(conclusion, RISK_KEYWORDS) and risk in ("low", "medium"):
        finding("info", "RISK_KEYWORD",
                "risk-topic keyword in conclusion; risk_tier escalated to 'high'")
        risk = "high"
    causal = matches_any(conclusion, CAUSAL_PATTERNS)
    works = matches_any(conclusion, WORKS_PATTERNS)

    # -- 2. evidence assessment with P0-1 anchor three-stage check ----------
    direct_items, indirect_items = [], []
    evidence_lines = []
    anchor_strict_fail = False
    mechanical_channel = False
    attested_channel = False
    for ev in data.get("evidence") or []:
        status, msg = check_anchor(ev, offline)
        ev_kind = ev["kind"]
        if ev_kind in INDIRECT_KINDS:
            indirect_items.append(ev)
            evidence_lines.append(f"[indirect] {ev_kind} — {ev['detail']}")
            if ev_kind in ("memory", "assumption"):
                finding("info", "NON_EVIDENCE_KIND",
                        f"evidence kind '{ev_kind}' is not evidence, only a "
                        f"prior (L0/L1 at most)")
            continue
        # direct-kind item: anchor stages decide its fate
        if status in ("mechanical_ok",):
            direct_items.append(ev)
            mechanical_channel = True
            evidence_lines.append(f"[direct·mech✓] {ev_kind} — {msg}")
        elif status == "attested":
            direct_items.append(ev)
            attested_channel = True
            evidence_lines.append(f"[direct·attested] {ev_kind} — {msg}")
        elif status == "partial":
            direct_items.append(ev)
            attested_channel = True
            evidence_lines.append(f"[direct·partial] {ev_kind} — {msg}")
            caveats.append(f"anchor only partially supports the claim: {msg[:120]}")
        elif status == "no_candidate":
            # v1 rule still applies: a direct claim needs a trace anchor
            if matches_any(ev["detail"], TRACE_PATTERNS):
                direct_items.append(ev)
                evidence_lines.append(
                    f"[direct·trace-only] {ev_kind} — {ev['detail']} "
                    f"(anchor not mechanically checkable)")
            else:
                trunc = ev["detail"][:60] + ("…" if len(ev["detail"]) > 60 else "")
                finding("warn", "UNTRACEABLE_EVIDENCE",
                        f"direct evidence ('{ev_kind}') has no trace anchor; "
                        f"downgraded to indirect: “{trunc}”")
                indirect_items.append(ev)
                evidence_lines.append(f"[indirect*] {ev_kind} — {trunc} "
                                      f"(downgraded: no trace anchor)")
        elif status == "quote_missing":
            finding("high", "ANCHOR_QUOTE_MISSING",
                    f"citation does not support the claim — {msg}")
            indirect_items.append(ev)
            evidence_lines.append(f"[indirect*] {ev_kind} — {msg}")
        elif status == "missing":
            finding("high", "ANCHOR_MISSING", f"anchor not resolvable — {msg}")
            indirect_items.append(ev)
            evidence_lines.append(f"[indirect*] {ev_kind} — {msg}")
        elif status == "contradicted":
            finding("high", "CONTENT_CONTRADICTS",
                    f"anchor content attested NOT to support claim — {msg}; "
                    f"treated as contradicting counter-evidence")
            indirect_items.append(ev)
            evidence_lines.append(f"[indirect*] {ev_kind} — CONTENT CONTRADICTS")
            data.setdefault("counter_evidence", []).append({
                "detail": f"anchor content does not support the claim: {msg}",
                "status": "unaddressed", "contradicts": True})
        else:  # unresolved / content_unchecked
            anchor_strict_fail = True
            sev = "medium"
            code = "ANCHOR_UNRESOLVED" if status == "unresolved" \
                else "ANCHOR_CONTENT_UNCHECKED"
            finding(sev, code,
                    f"anchor not verified end-to-end — {msg} (citation may "
                    f"exist without supporting the claim)")
            direct_items.append(ev)
            evidence_lines.append(f"[direct·unchecked!] {ev_kind} — {msg}")

    direct_groups = {ev.get("group") or ev["kind"] for ev in direct_items}
    has_direct = bool(direct_items)
    has_indirect = bool(indirect_items)

    # -- 3. verification validity -------------------------------------------
    ver = data.get("verification") or {}
    executed = bool(ver.get("executed"))
    env_ok = ver.get("env_independent") is True
    target_ok = ver.get("validates_target") is True
    valid_execution = executed and env_ok and target_ok
    if executed and not env_ok:
        finding("high", "ENV_CONTAMINATED",
                "verification environment is NOT independent (contaminated): "
                "test results from it are untrustworthy and count as no "
                "verification")
        actions.append("redo the verification in a clean, independent "
                       "environment (rebuild image from the pre-change "
                       "state; isolate from golden/reference patches)")
    if executed and not target_ok:
        finding("high", "TEST_NOT_TARGETED",
                "tests pass but are not confirmed to validate the target "
                "claim (coverage unknown): test-passed != problem-solved")
        actions.append("confirm the failing case is actually covered: "
                       "reproduce first, then verify the fix on it")

    # -- 4. evidence level ----------------------------------------------------
    level = 0
    if has_indirect:
        level = max(level, 1)
    if has_direct:
        level = max(level, 2)
    if valid_execution:
        level = max(level, 3)
    if len(direct_groups) >= 2:
        level = max(level, 4)

    # -- 5. required level -----------------------------------------------------
    req = STRENGTH_REQ[claimed]
    if ctype == "FACT":
        req = max(req, 2)
    if ctype == "EXPERIMENT_RESULT":
        req = max(req, 3)
    if causal and STRENGTHS.index(claimed) >= STRENGTHS.index("judged"):
        req = max(req, 3)
    works_floor = "likely"
    if gate_point == "pre-action":
        works_floor = "possibly"   # any works claim before an irreversible act
    if works and STRENGTHS.index(claimed) >= STRENGTHS.index(works_floor):
        req = max(req, 3)
    if risk == "high" and STRENGTHS.index(claimed) >= STRENGTHS.index("judged"):
        req = max(req, 3)
    if risk == "extreme":
        if STRENGTHS.index(claimed) >= STRENGTHS.index("verified"):
            req = max(req, 4)
        elif STRENGTHS.index(claimed) >= STRENGTHS.index("judged"):
            req = max(req, 3)

    # -- 6. counter-evidence ------------------------------------------------
    counters = data.get("counter_evidence") or []
    unaddr_contra = [ce for ce in counters
                     if ce.get("status", "unaddressed") == "unaddressed"
                     and ce.get("contradicts", False)]
    unaddr_other = [ce for ce in counters
                    if ce.get("status", "unaddressed") == "unaddressed"
                    and not ce.get("contradicts", False)]
    explained = [ce for ce in counters if ce.get("status") == "explained"]
    for ce in unaddr_contra:
        finding("high", "CONTRA_EVIDENCE_UNADDRESSED",
                f"unaddressed CONTRADICTING counter-evidence: “{ce['detail'][:80]}”")
        actions.append("address or refute the contradicting counter-evidence "
                       "before asserting this conclusion")
    for ce in unaddr_other:
        finding("medium", "COUNTER_UNADDRESSED",
                f"unaddressed counter-evidence: “{ce['detail'][:80]}”")
    for ce in explained:
        caveats.append(f"boundary condition (from counter-evidence): "
                       f"{ce['detail'][:120]}")

    # P0-2: counter-search isolation requirement (SGV)
    ctx = data.get("counter_search_context", "same")
    search_cap = False
    if ctx != "isolated":
        strong_claim = claimed in ("cross_verified", "absolute")
        empty_high = (not counters) and risk in ("high", "extreme") \
            and STRENGTHS.index(claimed) >= STRENGTHS.index("verified")
        if strong_claim or empty_high:
            search_cap = True
            finding("high", "COUNTER_SEARCH_NOT_ISOLATED",
                    "counter-evidence search ran in the SAME context as the "
                    "conclusion (agreement bias): a cross-verified claim "
                    "requires an isolated-context search or a mechanical "
                    "falsification attempt (SGV, ICLR 2026)")
            actions.append("rerun the counter-evidence search in an isolated "
                           "context (fresh session without the conclusion, or "
                           "an independent agent), or attempt mechanical "
                           "falsification")
        elif not counters:
            caveats.append("counter-evidence search was same-context; "
                           "coverage may be limited by agreement bias")

    # -- 7. generalization ------------------------------------------------------
    gen = data.get("generalization")
    if gen and gen.get("population_size") and gen.get("sample_size") \
            and gen["population_size"] > gen["sample_size"] \
            and not gen.get("statistical_basis"):
        finding("high", "SAMPLE_TO_POPULATION",
                f"generalizing a sample of {gen['sample_size']:,} to a "
                f"population of {gen['population_size']:,} without "
                f"statistical basis: the sample cannot certify the whole")
        actions.append(
            f"scan the full population, or use a statistically valid sampling "
            f"plan, or restate scoped to the sample "
            f"(“{gen['sample_size']:,} sampled, no issues found; whole not verified”)")

    # -- 8. decision ------------------------------------------------------------
    decision = None

    if original_claimed in ("verified", "cross_verified") and not valid_execution:
        why = ("claimed 'verified' but no VALID execution exists"
               + (" — reasoning/reading/analysis is NOT verification"
                  if not executed else " — the executed verification was voided: "
                                      "verification environment not independent, "
                                      "or test does not validate the target"))
        finding("reject", "FAKE_VERIFICATION", why)
        decision = "REJECT"
        actions.append("either actually execute the verification (run it) or "
                       "downgrade the claim to judged/possibly and rerun the gate")

    if decision != "REJECT" and ctype == "FACT" and unaddr_contra:
        finding("reject", "FACT_CONTRADICTED",
                "a FACT conclusion cannot be output while a direct "
                "contradiction is unaddressed")
        decision = "REJECT"

    if decision != "REJECT" and claimed == "absolute" and level < req:
        finding("reject", "ABSOLUTE_OVERREACH",
                f"absolute claim requires cross-validated evidence (L{req}); "
                f"current evidence is L{level}. No amount of confidence "
                f"justifies absolute wording — restate at allowed strength "
                f"with explicit scope")
        decision = "REJECT"

    if decision != "REJECT" and gen and not gen.get("statistical_basis") \
            and gen.get("population_size", 0) > gen.get("sample_size", 0) \
            and claimed in ("absolute", "verified", "cross_verified"):
        decision = "REJECT"

    if decision is None and search_cap:
        decision = "VERIFY_REQUIRED"

    # anchor strictness: strong claims need end-to-end verified anchors
    if decision is None and anchor_strict_fail and (
            STRENGTHS.index(claimed) >= STRENGTHS.index("verified")
            or (ctype == "FACT" and risk in ("high", "extreme"))):
        decision = "VERIFY_REQUIRED"
        actions.append("verify the anchor end-to-end: resolve it, read its "
                       "actual content, and confirm it supports the claim "
                       "(quote it in `quote`)")

    if decision is None and req > level:
        if data.get("evidence_obtainable", "unknown") == "no":
            decision = "ABSTAIN"
            actions.append("state the gap explicitly: “目前无法确认” + what "
                           "evidence is missing and who can provide it; do "
                           "not output the conclusion at any strength")
        else:
            decision = "VERIFY_REQUIRED"
            if not executed and (works or causal or original_claimed in
                                 ("verified", "cross_verified")):
                actions.append("execute the actual verification: run the "
                               "program / tests / benchmark instead of "
                               "reasoning about it")
            if ctype == "FACT" and level < 2:
                actions.append("locate an authoritative source (official "
                               "docs, source code, config, data) and cite it "
                               "with a resolvable anchor + quote")
            if req == 4 and len(direct_groups) < 2:
                actions.append("add at least one independent evidence line "
                               "(different tool / method / environment) for "
                               "cross-validation")
            if level >= 2:
                actions.append(f"or downgrade the wording and rerun the gate "
                               f"with the lower claim")
            if gate_point == "pre-action":
                actions.append("for irreversible actions: verify in a "
                               "reversible/staged setting first (dry-run, "
                               "canary, staging) before executing")

    if decision is None:
        if unaddr_contra and (risk in ("high", "extreme")
                              or STRENGTHS.index(claimed) >= STRENGTHS.index("verified")):
            decision = "VERIFY_REQUIRED"
        elif unaddr_contra or unaddr_other or explained:
            decision = "PASS_WITH_CAVEAT"
        else:
            decision = "PASS"

    if decision == "PASS_WITH_CAVEAT":
        for ce in unaddr_contra:
            caveats.append(f"known counter-example that limits the claim: "
                           f"{ce['detail'][:120]}")
        for ce in unaddr_other:
            caveats.append(f"unaddressed counter-evidence (mention it): "
                           f"{ce['detail'][:120]}")

    # -- reason -----------------------------------------------------------------
    if decision == "REJECT":
        reject_msgs = [f["message"] for f in findings if f["severity"] == "reject"]
        high_msgs = [f["message"] for f in findings if f["severity"] == "high"]
        seen, ordered = set(), []
        for m in reject_msgs + high_msgs:
            if m not in seen:
                seen.add(m)
                ordered.append(m)
        reason = "; ".join(ordered) or "unsupported conclusion"
    elif decision == "ABSTAIN":
        reason = ("required evidence is not obtainable (evidence_obtainable="
                  "'no'): conclusion cannot be confirmed or denied here — "
                  "abstain and state the gap")
    else:
        parts = [f["message"] for f in findings
                 if f["severity"] in ("high", "reject")]
        if req > level:
            ctx_notes = []
            if causal:
                ctx_notes.append("causal claim asserted from correlation-level "
                                 "evidence")
            if works:
                ctx_notes.append("works/viability claim without execution")
            if gate_point == "pre-action":
                ctx_notes.append("irreversible action pending "
                                 "(--gate-point pre-action)")
            suffix = (f" ({'; '.join(ctx_notes)})" if ctx_notes else "")
            parts.append(f"claimed strength '{claimed}' requires L{req}, "
                         f"evidence is only L{level}{suffix}: conclusion "
                         f"strength exceeds evidence strength — execute the "
                         f"actual verification (run it), or downgrade the "
                         f"wording to the allowed strength and rerun the gate")
        reason = "; ".join(parts) or (
            f"evidence L{level} supports claimed strength '{claimed}' "
            f"(requires L{req})")
        if decision == "PASS_WITH_CAVEAT":
            reason = "pass with mandatory caveats: " + reason

    # -- allowed wording ------------------------------------------------------------
    allowed_strength = LEVEL_STRENGTH[level]
    if (causal or works) and not valid_execution:
        allowed_strength = min(allowed_strength, "possibly", key=STRENGTHS.index)
    if claimed == "absolute":
        allowed_strength = min(allowed_strength, "cross_verified",
                               key=STRENGTHS.index)
    allowed_wording = LEVEL_WORDING[STRENGTH_REQ[allowed_strength]]
    if allowed_strength == "possibly" and (causal or works) and not valid_execution:
        allowed_wording += " — 未实际运行验证 (not actually executed/verified)"
    if decision == "ABSTAIN":
        allowed_wording = "目前无法确认 (cannot confirm) — state the gap"

    # -- confidence -------------------------------------------------------------------
    if decision in ("REJECT", "VERIFY_REQUIRED", "ABSTAIN"):
        confidence = "LOW"
    elif decision == "PASS_WITH_CAVEAT":
        confidence = "MEDIUM" if level >= 2 else "LOW"
    elif level >= 3 and not unaddr_contra:
        confidence = "HIGH"
    elif level >= 4:
        confidence = "HIGH"
    elif level == 2:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    verifier = dict(data.get("verifier") or {})
    verifier.setdefault("id", "unspecified")
    verifier.setdefault("protocol", f"gate_check/{__version__}")
    verifier["entailment_channel"] = ("mechanical" if mechanical_channel
                                      else "attested" if attested_channel
                                      else "none")

    return {
        "conclusion": conclusion,
        "type": ctype,
        "claimed_strength": claimed,
        "risk_tier": risk,
        "gate_point": gate_point,
        "evidence_level": f"L{level}",
        "evidence_level_num": level,
        "required_level_num": req,
        "decision": decision,
        "confidence": confidence,
        "reason": reason,
        "findings": findings,
        "evidence_lines": evidence_lines,
        "allowed_strength": allowed_strength,
        "allowed_wording": allowed_wording,
        "caveats": caveats,
        "required_actions": actions,
        "counter_search_context": ctx,
        "verification": {"executed": executed, "valid": valid_execution,
                         "env_independent": ver.get("env_independent", "unknown"),
                         "validates_target": ver.get("validates_target", "unknown")},
        "verifier": verifier,
    }


# ------------------------------------------------------------------ render ---

def render_text(r: dict) -> str:
    lines = ["Evidence Gate Result", ""]
    lines.append(f"Conclusion:\n{r['conclusion']}")
    lines.append(f"Type: {r['type']}")
    lines.append(f"Claimed strength: {r['claimed_strength']}  (risk: {r['risk_tier']}"
                 + (f", gate-point: {r['gate_point']}" if r['gate_point'] != "conclusion" else "") + ")")
    lines.append(f"Evidence Level: {r['evidence_level']}  (claim requires "
                 f"L{r['required_level_num']})")
    lines.append("Evidence (anchor three-stage check):")
    for ev in r.get("evidence_lines") or ["(none listed)"]:
        lines.append(f"  - {ev}")
    v = r["verification"]
    lines.append(f"  execution: executed={v['executed']} valid={v['valid']} "
                 f"env_independent={v['env_independent']} "
                 f"validates_target={v['validates_target']}")
    lines.append(f"Counter-evidence search context: {r['counter_search_context']}")
    lines.append("Findings:")
    for f in r["findings"]:
        lines.append(f"  [{f['severity']}] {f['code']}: {f['message']}")
    lines.append(f"Confidence: {r['confidence']}")
    lines.append(f"Decision: {r['decision']}  (exit {DECISION_EXIT[r['decision']]})")
    lines.append(f"Reason:\n  {r['reason']}")
    lines.append(f"Allowed wording: {r['allowed_wording']}")
    if r["caveats"]:
        lines.append("Mandatory caveats (must appear in output):")
        for c in r["caveats"]:
            lines.append(f"  - {c}")
    if r["required_actions"]:
        lines.append("Required actions:")
        for a in r["required_actions"]:
            lines.append(f"  - {a}")
    lines.append(f"Verifier: {json.dumps(r['verifier'], ensure_ascii=False)}")
    return "\n".join(lines)


def main():
    opts = parse_args(sys.argv)
    if opts["mark_outcome"]:
        cmd_mark_outcome(opts)
    if opts["calibration"]:
        cmd_calibration(opts)
    data = load_input(opts["file"])
    validate(data)
    result = assess(data, gate_point=opts["gate_point"], offline=opts["offline"])
    ts = time.strftime("%Y-%m-%dT%H:%M:%S")
    result["ts"] = ts
    result["gate_id"] = hashlib.sha1(
        (ts + "|" + result["conclusion"]).encode("utf-8")).hexdigest()[:8]
    result["script_version"] = __version__
    append_log(opts, {
        "ts": ts, "gate_id": result["gate_id"],
        "script_version": __version__, "gate_point": opts["gate_point"],
        "decision": result["decision"], "evidence_level": result["evidence_level"],
        "claimed_strength": result["claimed_strength"], "type": result["type"],
        "risk_tier": result["risk_tier"], "verifier": result["verifier"],
        "findings": [f["code"] for f in result["findings"]],
        "allowed_strength": result["allowed_strength"],
        "conclusion": result["conclusion"], "outcome": None, "input": data,
    })
    if opts["json"]:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_text(result))
    sys.exit(DECISION_EXIT[result["decision"]])


if __name__ == "__main__":
    main()
