#!/usr/bin/env python3
"""Evidence Gate v3 — deterministic conclusion-quality gate.

Evaluates one conclusion against its evidence and decides whether the
conclusion may be output, at what strength, and with what caveats.

Core rule: CONCLUSION STRENGTH MUST NOT EXCEED EVIDENCE STRENGTH.

v3 upgrades (research-driven; "EG 2.0" in the reliability report):

  P0-A MISLEADING_QUOTE — a quoted line that exists in the anchor but
       states DIFFERENT figures than the conclusion claims is caught by a
       numeric-consistency check (quote-in-file != quote-supports-claim;
       SourceCheckup 2025 + rule-verifier FRR lesson: narrow, normalized).
  P0-B CORRELATED_EVIDENCE — "N sources" collapse to the number of
       INDEPENDENT lines: same URL host, same local file, quote overlap,
       or quote-cites-quote chains merge into one line (Rewrite the News
       LREC 2026; Counting Copies 2026; Dempster-Shafer distinctness).
       Aggregator-tier / meta-evidence / contaminated sources never count
       as an independent line (CONFACT IJCAI 2025; verdict-leakage).
  P0-C TEMPORAL_STALE — evidence with an as_of date cannot support a
       recency-marked "current" claim past the freshness window; `until`
       dates hard-invalidate superseded evidence (TUM 2026).
  P0-D SAME_MODEL_VERIFIER — cross_verified at high/extreme risk requires
       an independent check by a model of a DIFFERENT family than the
       generator (cross-family > same-family > self, arXiv:2512.02304).
  P0-E attested-only L4 cap — "cross-verified" can never rest purely on
       unfetched self-attested URLs: L4 needs a mechanical line or a valid
       independent check.
  P0-F CHANNEL_MISMATCH — mechanical claim classes (code/config/data/math)
       at verified+ strength require a mechanical verification channel
       (execution/test/assertion/formal_proof/statistical); reasoning
       about code never becomes "verified" (VERGE 2026; Agentic PBT 2025;
       ImpossibleBench: execution channel needs test-provenance honesty).
  P0-G abstention taxonomy — unobtainable_reason is recorded and reported;
       calibration reports abstention precision/recall both ways
       (AbstentionBench, NeurIPS 2025: bidirectional, anti-gaming).
  P0-H calibration, not confidence — the heuristic confidence field is
       REMOVED (judges are systematically overconfident, arXiv:2508.06225);
       --calibration now emits Wilson CIs, risk-coverage/AURC, abstention
       P/R, per-finding error attribution, and (once n>=min per level)
       wording-cap overrides so the L0-L4 wording map is data-calibrated
       (conformal risk control direction, SCOPE 2026: 200-500 samples).
       Levels stay ORDINAL — never presented as probabilities.

v2 upgrades (still in force): anchor three-stage check, counter-search
isolation (SGV), ABSTAIN, pre-action gate, audit log + calibration loop.

Usage:
    gate_check.py INPUT.json [flags]     # file argument
    ... | gate_check.py - [flags]        # stdin
    gate_check.py --mark-outcome ID correct|incorrect|unknown [--log P]
    gate_check.py --calibration [--emit-overrides] [--log P]

Flags: --json  --log PATH  --no-log  --offline
       --gate-point conclusion|pre-action

Exit codes:
      0  PASS / PASS_WITH_CAVEAT
     10  VERIFY_REQUIRED
     15  ABSTAIN                (evidence not obtainable — refuse to conclude)
     20  REJECT
      2  input error

Input schema (JSON; v1/v2 fields remain valid; v3 fields optional):
{
  "conclusion": "...",                    # required
  "type": "FACT|INFERENCE|HYPOTHESIS|RECOMMENDATION|EXPERIMENT_RESULT",
  "claimed_strength": "hypothesis|possibly|likely|judged|verified|cross_verified|absolute",
  "risk_tier": "low|medium|high|extreme",           # default medium
  "evidence_obtainable": "yes|no|unknown",          # no -> ABSTAIN on shortfall
  "unobtainable_reason": "no_access|nonexistent|unreproducible|undecidable",  # v3
  "counter_search_context": "isolated|same",        # cross_verified needs isolated
  "generator": "model/agent id that produced the conclusion",   # v3
  "claim_class": "code_behavior|config|data|math|fact|judgment", # v3 routing
  "claim_time": "current|YYYY-MM-DD",               # v3 temporal target
  "freshness_days": 365,                            # v3 staleness window (default)
  "verifier": {"id": "...", "protocol": "..."},     # optional, logged for audit
  "evidence": [
    {"kind": "...", "detail": "...", "group": "optional",
     "anchor": "path-or-url",            # explicit anchor overrides detection
     "quote": "text the anchor must contain",   # mechanical entailment check
     "content_supports": "supported|partial|unsupported|not_checked",
     "as_of": "YYYY-MM-DD",              # v3: when this content was true
     "until": "YYYY-MM-DD",              # v3: when it stopped being true
     "source_tier": "primary|secondary|aggregator|unknown",  # v3
     "meta_evidence": false,             # v3: page itself renders a verdict
     "same_host_independent": false,     # v3: attested independence on shared host
     "verified_by": "self|tool:NAME|agent:ID"}  # v3: who verified this line
  ],
  "verification": {"executed": bool, "detail": "...",
                   "env_independent": true|false|"unknown",
                   "validates_target": true|false|"unknown",
                   "channel": "execution|test|assertion|formal_proof|statistical|reasoning"},
  "independent_checks": [                 # v3: re-derivations by other agents
    {"by": "model/tool id", "channel": "execution|retrieval_fresh|formal|statistical|reasoning",
     "agree": true, "context": "isolated|same", "detail": "..."}
  ],
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
import math
import re
import subprocess  # noqa: F401  (kept for future tool bridges)
import sys
import time
import urllib.request
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlsplit

__version__ = "3.0.0"
DEFAULT_LOG = ".evidence-gate-log.jsonl"
DEFAULT_OVERRIDES = ".evidence-gate-calibration.json"
MIN_CAL_N = 10          # min known outcomes before a wording cap is emitted
WORDING_PROMISE = {0: 0.5, 1: 0.6, 2: 0.75, 3: 0.9, 4: 0.95}
# ^ what each level's wording is understood to promise; empirical accuracy
#   below the promise triggers a wording cap suggestion (never silently).

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
SOURCE_TIERS = {"primary", "secondary", "aggregator", "unknown"}
CLAIM_CLASSES = {"code_behavior", "config", "data", "math", "fact", "judgment"}
MECH_CLASSES = {"code_behavior", "config", "data", "math"}
MECH_VERIF_CHANNELS = {"execution", "test", "assertion", "formal_proof",
                       "statistical"}
VERIF_CHANNELS = MECH_VERIF_CHANNELS | {"reasoning"}
CHECK_CHANNELS = {"execution", "retrieval_fresh", "formal", "statistical",
                  "reasoning"}
UNOBTAINABLE_REASONS = {"no_access", "nonexistent", "unreproducible",
                        "undecidable"}

# Hosts whose /datasets pages leak answers/verdicts or carry benchmark data
# (Search-Time Contamination, arXiv:2508.13180; verdict-leakage). Matched as
# exact host + path prefix, NOT substring (hf.co blog posts are fine).
CONTAMINATED_HOSTS = ("huggingface.co", "hf.co")

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
RECENCY_MARKERS = [
    r"当前", r"目前", r"现在", r"最新", r"至今", r"目前已", r"现阶段",
    r"现今", r"今天",
    r"\bcurrently\b", r"\bas of now\b", r"\bas of writing\b", r"\blatest\b",
    r"\bnow\b", r"\btoday\b",
]
# verified/cross-verified WORDING in the conclusion text escalates the claim
# even when the field says less (same philosophy as ABSOLUTE_WORDING: the
# gate reads the text, not the self-report)
VERIFIED_PATTERNS = [r"已交叉验证", r"已验证", r"已核实", r"\bcross-verified\b",
                     r"\bverified\b"]
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


# ---------------------------------------------------------------- helpers ---

def family(identity: str) -> str:
    """Model family: last path segment, first alpha token, lowercase
    ('zai/GLM-5.3' -> 'glm'; '12345' -> '' (unrecognized))."""
    ident = str(identity or "").strip().split("/")[-1]
    m = re.search(r"[A-Za-z]+", ident)
    return m.group(0).lower() if m else ""


_WIDE_DIGITS = str.maketrans("０１２３４５６７８９，．", "0123456789,.")


def _norm_figure(tok: str) -> str:
    """Normalize a numeric token: strip thousand separators and leading
    zeros, drop trailing fraction zeros ('030'->'30', '60.0'->'60',
    '10,000'->'10000', '30.50'->'30.5')."""
    tok = tok.translate(_WIDE_DIGITS).replace(",", "")
    whole, _, frac = tok.partition(".")
    whole = whole.lstrip("0") or "0"
    frac = frac.rstrip("0")
    return f"{whole}.{frac}" if frac else whole


def extract_figures(text: str) -> set:
    """All numeric figure tokens, normalized (see _norm_figure)."""
    t = (text or "").translate(_WIDE_DIGITS)
    return {_norm_figure(m) for m in
            re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?", t)}


UNIT_TOKENS = ("seconds", "minutes", "percent", "second", "minute", "hours",
               "days", "rows", "users", "items", "毫秒", "分钟", "小时",
               "秒", "天", "年", "月", "周", "次", "个", "条", "行", "万",
               "亿", "元", "倍", "%", "ms", "kb", "mb", "gb", "tb", "qps",
               "km", "kg", "sec", "min", "day", "row", "user", "item",
               "point", "s", "h", "d")

# time units convertible to seconds — '1 分钟' must match a quote's
# '60 seconds', or honest unit-converted conclusions get falsely blocked
UNIT_SECONDS = {"秒": 1.0, "s": 1.0, "sec": 1.0, "second": 1.0,
                "seconds": 1.0, "ms": 0.001, "毫秒": 0.001, "分钟": 60.0,
                "min": 60.0, "minute": 60.0, "minutes": 60.0, "小时": 3600.0,
                "h": 3600.0, "hour": 3600.0, "hours": 3600.0, "天": 86400.0,
                "d": 86400.0, "day": 86400.0, "days": 86400.0}


def quantity_pairs(text: str) -> list:
    """(value, unit) pairs for figures followed by a unit marker.

    '默认超时是 30 秒' -> [('30', '秒')]; 'foo-lib 3.2 存在…' -> []
    (3.2 is an identifier, exempt from the numeric-support check).
    """
    t = (text or "").translate(_WIDE_DIGITS)
    out = []
    for m in re.finditer(r"\d+(?:,\d{3})*(?:\.\d+)?", t):
        tail = (t[m.end():m.end() + 8] or "").lstrip()
        for u in UNIT_TOKENS:            # longest-first: 'ms' before 's'
            if tail.startswith(u):
                out.append((_norm_figure(m.group(0)), u))
                break
    return out


def figure_carried(claimed_pair, ev_values: set, ev_pairs: list) -> bool:
    """Is a claimed (value, unit) figure carried by the quoted evidence?
    Exact value match against ANY figure in quotes/anchors, or a
    unit-converted match ('1 分钟' vs '60 seconds') against unit pairs."""
    v, u = claimed_pair
    if v in ev_values:
        return True
    for v2, u2 in ev_pairs:
        if u in UNIT_SECONDS and u2 in UNIT_SECONDS \
                and abs(float(v) * UNIT_SECONDS[u]
                        - float(v2) * UNIT_SECONDS[u2]) < 1e-9:
            return True
    return False


def token_set(text: str) -> set:
    """Overlap tokens: latin words + digits + CJK bigrams (a CJK sentence
    is otherwise ONE unsegmentable token, which defeats Jaccard collapse)."""
    t = (text or "").lower()
    out = set(re.findall(r"[a-z0-9]+", t))
    for run in re.findall(r"[\u4e00-\u9fff]+", t):
        if len(run) == 1:
            out.add(run)
        out |= {run[i:i + 2] for i in range(len(run) - 1)}
    return out


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def url_host(anchor: str):
    """Hostname, lowercased, port stripped, 'www.' dropped."""
    try:
        host = (urlsplit(str(anchor)).hostname or "").lower()
    except ValueError:
        return None
    return host[4:] if host.startswith("www.") else host or None


PUBLIC_SUFFIX_2LD = {"co", "com", "org", "net", "gov", "edu", "ac", "or"}


def reg_domain(host: str):
    """Approximate registrable domain: 'a.news.example.com' -> 'example.com';
    'x.co.uk' keeps three labels under country-code second levels."""
    if not host:
        return None
    parts = host.split(".")
    if len(parts) >= 3 and parts[-2] in PUBLIC_SUFFIX_2LD and len(parts[-1]) == 2:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def line_label(ev: dict) -> str:
    """Human-readable label for one evidence line (merge reasons, ledger)."""
    a = extract_anchor(ev.get("detail", ""), ev.get("anchor"))
    h = url_host(a) if a and str(a).startswith("http") else None
    return f"{ev.get('kind')}@{h or a or ev.get('group') or '?'}"


def parse_date(s):
    try:
        return datetime.strptime(str(s).strip(), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def wilson_ci(k: int, n: int, z: float = 1.96):
    """Wilson score interval for k successes in n trials."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


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
        return Path(path).expanduser().read_text(encoding="utf-8",
                                                 errors="replace")
    except OSError:
        return None


def norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def quote_in(quote: str, text: str) -> bool:
    # strip markdown emphasis chars: `code`, **bold** — formatting, not content
    clean = lambda t: norm_ws(re.sub(r"[`*_]", "", t or ""))
    return clean(quote) in clean(text)


def check_anchor(ev: dict, offline: bool):
    """Three-stage anchor check.

    Returns (status, message, anchor_text_or_None).
    status in: mechanical_ok / attested / no_candidate / unresolved /
    content_unchecked / quote_missing / missing / contradicted / partial
    """
    supports = ev.get("content_supports", "not_checked")
    if supports == "unsupported":
        return "contradicted", ("anchor content attested to NOT support the "
                                "claim (content_supports=unsupported)"), None
    detail = ev.get("detail", "")
    anchor = extract_anchor(detail, ev.get("anchor"))
    if anchor is None:
        return "no_candidate", "no mechanically checkable anchor in detail", None
    quote = ev.get("quote")
    if anchor.startswith(("http://", "https://")):
        text = fetch_url(anchor, offline)
        if text is None:
            if supports in ("supported", "partial"):
                return "attested", f"URL not fetched here; agent attests content (channel=attested): {anchor}", None
            return "unresolved", (f"URL could not be fetched and content is "
                                  f"not attested: {anchor}"), None
    else:
        text = read_local(anchor)
        if text is None:
            return "missing", f"anchor path does not exist / unreadable: {anchor}", None
    if quote:
        if quote_in(quote, text):
            return "mechanical_ok", f"quote verified in anchor: {anchor}", text
        return "quote_missing", (f"anchor resolved but does NOT contain the "
                                 f"quoted support “{quote[:50]}”: {anchor}"), text
    # resolved but nothing to compare
    if supports in ("supported", "partial"):
        return ("attested" if supports == "supported" else "partial"), \
            f"anchor resolved; agent attests content ({supports}): {anchor}", text
    return "content_unchecked", (f"anchor resolved but its content was never "
                                 f"checked against the claim (no quote, no "
                                 f"attestation): {anchor}"), text


# ------------------------------------------------------------------ input ---

def die_input(msg: str):
    print(f"INPUT ERROR: {msg}", file=sys.stderr)
    print("Run gate_check.py --help for the schema.", file=sys.stderr)
    sys.exit(2)


def parse_args(argv):
    opts = {"json": False, "no_log": False, "offline": False,
            "gate_point": "conclusion", "log": DEFAULT_LOG,
            "mark_outcome": None, "calibration": False, "emit_overrides": False,
            "file": "-"}
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
            if i >= len(argv):
                die_input("--log needs a PATH")
            opts["log"] = argv[i]
        elif a == "--mark-outcome":
            i += 2
            if i >= len(argv):
                die_input("--mark-outcome needs ID and VERDICT")
            opts["mark_outcome"] = (argv[i - 1], argv[i])
        elif a == "--calibration":
            opts["calibration"] = True
        elif a == "--emit-overrides":
            opts["emit_overrides"] = True
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
    if data.get("unobtainable_reason") is not None \
            and data["unobtainable_reason"] not in UNOBTAINABLE_REASONS:
        die_input(f"unobtainable_reason must be one of "
                  f"{sorted(UNOBTAINABLE_REASONS)}")
    if data.get("counter_search_context", "same") not in ("isolated", "same"):
        die_input("counter_search_context must be isolated|same")
    if data.get("claim_class") is not None \
            and data["claim_class"] not in CLAIM_CLASSES:
        die_input(f"claim_class must be one of {sorted(CLAIM_CLASSES)}")
    ct = data.get("claim_time", "current")
    if ct != "current" and parse_date(ct) is None:
        die_input("claim_time must be 'current' or YYYY-MM-DD")
    fd = data.get("freshness_days")
    if fd is not None and (not isinstance(fd, int) or isinstance(fd, bool)
                           or fd < 0):
        die_input("freshness_days must be a non-negative integer")
    if "evidence" in data and not isinstance(data["evidence"], list):
        die_input("evidence must be a list of objects")
    for i, ev in enumerate(data.get("evidence") or []):
        if not isinstance(ev, dict):
            die_input(f"evidence[{i}] must be an object")
        if ev.get("kind") not in ALL_KINDS:
            die_input(f"evidence[{i}].kind must be one of {sorted(ALL_KINDS)}, "
                      f"got: {ev.get('kind')}")
        if not isinstance(ev.get("detail"), str) or not ev["detail"].strip():
            die_input(f"evidence[{i}].detail must be a non-empty string")
        if ev.get("quote") is not None and not isinstance(ev["quote"], str):
            die_input(f"evidence[{i}].quote must be a string")
        if ev.get("content_supports", "not_checked") not in CONTENT_SUPPORTS:
            die_input(f"evidence[{i}].content_supports must be one of "
                      f"{sorted(CONTENT_SUPPORTS)}")
        if ev.get("source_tier", "unknown") not in SOURCE_TIERS:
            die_input(f"evidence[{i}].source_tier must be one of "
                      f"{sorted(SOURCE_TIERS)}")
        for df in ("as_of", "until"):
            if ev.get(df) is not None and parse_date(ev[df]) is None:
                die_input(f"evidence[{i}].{df} must be YYYY-MM-DD")
    ver = data.get("verification") or {}
    if not isinstance(ver, dict):
        die_input("verification must be an object")
    if ver.get("channel") is not None and ver["channel"] not in VERIF_CHANNELS:
        die_input(f"verification.channel must be one of {sorted(VERIF_CHANNELS)}")
    if "independent_checks" in data \
            and not isinstance(data["independent_checks"], list):
        die_input("independent_checks must be a list of objects")
    for i, ic in enumerate(data.get("independent_checks") or []):
        if not isinstance(ic, dict):
            die_input(f"independent_checks[{i}] must be an object")
        if not str(ic.get("by", "")).strip():
            die_input(f"independent_checks[{i}].by must be non-empty")
        if ic.get("channel", "reasoning") not in CHECK_CHANNELS:
            die_input(f"independent_checks[{i}].channel must be one of "
                      f"{sorted(CHECK_CHANNELS)}")
        if ic.get("context", "same") not in ("isolated", "same"):
            die_input(f"independent_checks[{i}].context must be isolated|same")
    if "counter_evidence" in data and not isinstance(data["counter_evidence"], list):
        die_input("counter_evidence must be a list of objects")
    for i, ce in enumerate(data.get("counter_evidence") or []):
        if not isinstance(ce, dict):
            die_input(f"counter_evidence[{i}] must be an object")
        if not isinstance(ce.get("detail"), str) or not ce["detail"].strip():
            die_input(f"counter_evidence[{i}].detail must be a non-empty string")
        if ce.get("status", "unaddressed") not in COUNTER_STATUS:
            die_input(f"counter_evidence[{i}].status must be one of "
                      f"{sorted(COUNTER_STATUS)}")
    gen = data.get("generalization")
    if gen is not None:
        if not isinstance(gen, dict):
            die_input("generalization must be an object or null")
        for k in ("sample_size", "population_size"):
            if gen.get(k) is not None and (not isinstance(gen[k], int)
                                           or isinstance(gen[k], bool)):
                die_input(f"generalization.{k} must be an integer")


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


def read_log_entries(opts):
    path = log_path(opts)
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def cmd_calibration(opts):
    """Per-level accuracy (Wilson CI), monotonicity, risk-coverage/AURC,
    abstention precision/recall, per-finding error attribution, and optional
    wording-cap overrides. Levels stay ordinal — no probabilities emitted."""
    entries = read_log_entries(opts)
    if not entries:
        print(f"No gate log at {log_path(opts)}. Run gates without --no-log "
              f"to build one.")
        sys.exit(0)
    levels, decisions, known, correct = {}, {}, 0, 0
    for e in entries:
        lv = e.get("evidence_level", "?")
        levels.setdefault(lv, {"n": 0, "known": 0, "correct": 0})
        levels[lv]["n"] += 1
        decisions[e.get("decision", "?")] = decisions.get(
            e.get("decision", "?"), 0) + 1
        if e.get("outcome") in ("correct", "incorrect"):
            levels[lv]["known"] += 1
            known += 1
            if e["outcome"] == "correct":
                levels[lv]["correct"] += 1
                correct += 1

    print("Evidence Gate calibration (from gate log)")
    print("=" * 78)
    print("caliber: accuracy/CI over MARKED outcomes only; answered = "
          "PASS/PASS_WITH_CAVEAT; coverage = answered/known")
    print(f"{'level':<7}{'runs':>6}{'known':>7}{'correct':>9}"
          f"{'accuracy':>10}  {'95% CI (Wilson)':<20}promise")
    promise_break = []
    for lv in sorted(levels, key=lambda x: (len(x), x)):
        s = levels[lv]
        acc = s["correct"] / s["known"] if s["known"] else None
        acc_s = f"{acc:.0%}" if acc is not None else "—"
        lo, hi = wilson_ci(s["correct"], s["known"]) if s["known"] else (0, 1)
        ci_s = f"[{lo:.2f}, {hi:.2f}]" if s["known"] else "—"
        lvnum = int(lv[1]) if re.fullmatch(r"L[0-4]", lv) else None
        prom = (f"≥{WORDING_PROMISE[lvnum]:.0%}" if lvnum is not None else "")
        mark = ""
        if lvnum is not None and acc is not None:
            if hi < WORDING_PROMISE[lvnum]:       # CI wholly below promise
                mark = "  ← BELOW promise"
                promise_break.append((lvnum, s["known"], acc))
        print(f"{lv:<7}{s['n']:>6}{s['known']:>7}{s['correct']:>9}"
              f"{acc_s:>10}  {ci_s:<20}{prom}{mark}")
    print("-" * 78)
    print("decisions:", json.dumps(decisions, ensure_ascii=False))

    # monotonicity of level accuracies (ordinal validity of the scale)
    seq = []
    for lvnum in range(5):
        s = levels.get(f"L{lvnum}")
        if s and s["known"]:
            seq.append((lvnum, s["correct"] / s["known"]))
    if len(seq) >= 2:
        viol = sorted({f"L{a}->{b}" for (a, ra), (b, rb) in zip(seq, seq[1:])
                       if rb < ra})
        print("monotonicity:", "OK (accuracy rises with level)"
              if not viol else f"VIOLATED at {', '.join(viol)} — "
              "levels are not yet ordinally valid on this data")

    # risk-coverage over level thresholds (answered = PASS/PASS_WITH_CAVEAT)
    print("\nrisk-coverage (threshold: PASS only at level ≥ k):")
    rc_points = []
    for k in range(5, 0, -1):
        answered = [e for e in entries
                    if e.get("decision") in ("PASS", "PASS_WITH_CAVEAT")
                    and isinstance(e.get("evidence_level_num"), int)
                    and e["evidence_level_num"] >= k
                    and e.get("outcome") in ("correct", "incorrect")]
        if not answered:
            continue
        risk = sum(1 for e in answered if e["outcome"] == "incorrect") \
            / len(answered)
        cov = len(answered) / max(1, known)
        rc_points.append((k, len(answered), risk, cov))
        print(f"  L≥{k}: answered {len(answered):>4}  risk {risk:.2f}  "
              f"coverage {cov:.2f}")
    if len(rc_points) >= 2:
        aurc = sum(r for _, _, r, _ in rc_points) / len(rc_points)
        print(f"  AURC (mean risk across thresholds): {aurc:.3f}")

    # abstention precision/recall (bidirectional, AbstentionBench protocol)
    abst = [e for e in entries if e.get("decision") == "ABSTAIN"]
    abst_known = [e for e in abst if e.get("outcome") in ("correct", "incorrect")]
    if abst_known:
        ap = sum(1 for e in abst_known if e["outcome"] == "correct") \
            / len(abst_known)
        print(f"\nabstention precision: {ap:.2f} "
              f"({sum(1 for e in abst_known if e['outcome']=='correct')}/"
              f"{len(abst_known)} abstentions were right)")
        should = [e for e in entries if e.get("outcome") == "incorrect"]
        caught = sum(1 for e in should if e.get("decision") == "ABSTAIN")
        print(f"abstention recall:    {caught}/{len(should)} wrong conclusions "
              f"were abstained on"
              + (f" ({caught/len(should):.2f})" if should else ""))
    else:
        print("\nabstention precision/recall: no marked ABSTAIN outcomes yet "
              "(mark abstention outcomes correct|incorrect to measure)")

    # per-finding error attribution: finding codes preceding wrong accepts
    wrong_accepts = [e for e in entries
                     if e.get("decision") in ("PASS", "PASS_WITH_CAVEAT")
                     and e.get("outcome") == "incorrect"]
    if wrong_accepts:
        cnt = {}
        for e in wrong_accepts:
            for c in e.get("findings") or []:
                cnt[c] = cnt.get(c, 0) + 1
        print("\nfindings on wrongly-accepted conclusions (rule yield audit):",
              json.dumps(cnt, ensure_ascii=False))

    if known == 0:
        print("\nNo outcomes recorded yet. After conclusions are confirmed or "
              "falsified, run:\n  gate_check.py --mark-outcome <gate_id> "
              "correct|incorrect --log <path>")
    else:
        print(f"\noverall accuracy on known outcomes: "
              f"{100.0 * correct / known:.0f}% ({correct}/{known})")

    if opts["emit_overrides"]:
        caps = {}
        for lvnum, n, acc in promise_break:
            # drop wording one rung below the level whose promise broke;
            # L0 has no rung below — its promise cannot be capped, only kept
            if n >= MIN_CAL_N and lvnum >= 1:
                caps[str(lvnum)] = {"n": n, "accuracy": round(acc, 3),
                                    "cap_level": lvnum - 1}
        payload = {"generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
                   "log": str(log_path(opts)), "level_caps": caps,
                   "note": "wording caps from measured per-level accuracy; "
                           "levels stay ordinal"}
        Path(DEFAULT_OVERRIDES).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        print(f"\noverrides written to {DEFAULT_OVERRIDES}: "
              + (", ".join(f"L{k}->cap L{v['cap_level']}"
                           for k, v in caps.items()) or "(none qualify yet)"))
    sys.exit(0)


def load_overrides(opts) -> dict:
    """Active calibration: wording caps from measured accuracy, if present."""
    for cand in (Path(DEFAULT_OVERRIDES),
                 log_path(opts).parent / DEFAULT_OVERRIDES):
        try:
            if cand.exists():
                data = json.loads(cand.read_text(encoding="utf-8"))
                if data.get("level_caps"):
                    return data["level_caps"]
        except (OSError, json.JSONDecodeError):
            continue
    return {}


# ------------------------------------------------------- correlation (P0-B) ---

def correlation_analysis(direct_items):
    """Union-find collapse of direct items into independent lines.

    Signals (Rewrite the News 2026; Counting Copies 2026; DS distinctness):
    same declared group · same local anchor path · same URL host (unless both
    attest same_host_independence) · quote token-Jaccard >= 0.7 · one quote
    citing another item's anchor URL (syndication chain).
    Returns (merged_groups: list of lists of indices, merge_reasons: list).
    """
    parent = list(range(len(direct_items)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    reasons = []

    def meta(i):
        ev = direct_items[i]
        return {
            "group": ev.get("group"),
            "anchor": extract_anchor(ev.get("detail", ""), ev.get("anchor")),
            "quote": ev.get("quote") or "",
            "text": ev.get("detail", "") or "",
            "indep_attested": bool(ev.get("same_host_independent")),
        }

    infos = [meta(i) for i in range(len(direct_items))]
    labels = [line_label(direct_items[i]) for i in range(len(direct_items))]
    for i in range(len(infos)):
        for j in range(i + 1, len(infos)):
            a, b = infos[i], infos[j]
            why = None
            if a["group"] and b["group"] and a["group"] == b["group"]:
                why = "same declared group"
            elif a["anchor"] and a["anchor"] == b["anchor"]:
                why = "same anchor"
            elif (a["anchor"] and b["anchor"]
                  and a["anchor"].startswith("http")
                  and b["anchor"].startswith("http")):
                ra, rb = reg_domain(url_host(a["anchor"])), \
                    reg_domain(url_host(b["anchor"]))
                if ra and ra == rb and not (a["indep_attested"]
                                            and b["indep_attested"]):
                    why = (f"same registrable domain ({ra}) — syndication "
                           f"risk; attest same_host_independent on BOTH "
                           f"items to override")
            if not why and a["quote"] and b["quote"]:
                if jaccard(token_set(a["quote"]), token_set(b["quote"])) >= 0.7:
                    why = "quotes overlap ≥0.7 (same quoted passage)"
            if not why:
                for x, y in ((a, b), (b, a)):
                    if x["quote"] and y["anchor"] \
                            and y["anchor"].startswith("http") \
                            and y["anchor"].rstrip("/") in x["quote"]:
                        why = "quote cites the other item's anchor (chain)"
                        break
            if not why:
                # a detail TEXT citing the other item's URL is the same
                # syndication chain, even when the quote is silent about it
                for x, y in ((a, b), (b, a)):
                    if y["anchor"] and y["anchor"].startswith("http") \
                            and y["anchor"].rstrip("/") in x["text"]:
                        why = "detail text cites the other item's anchor (chain)"
                        break
            if why:
                union(i, j)
                reasons.append(f"{labels[i]} + {labels[j]}: {why}")
    groups = {}
    for i in range(len(infos)):
        groups.setdefault(find(i), []).append(i)
    return [groups[k] for k in sorted(groups)], reasons


# ----------------------------------------------------------------- assess ---

def assess(data: dict, gate_point: str = "conclusion", offline: bool = False,
           level_caps: dict = None):
    conclusion = data["conclusion"]
    ctype = data["type"]
    claimed = data["claimed_strength"]
    risk = data.get("risk_tier", "medium")
    findings = []
    caveats = []
    actions = []
    ledger = []
    injected_counters = []   # derived counter-evidence (input not mutated)

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
    if matches_any(conclusion, VERIFIED_PATTERNS) \
            and STRENGTHS.index(claimed) < STRENGTHS.index("verified"):
        up = "cross_verified" if matches_any(
            conclusion, [r"已交叉验证", r"cross-verified"]) else "verified"
        finding("high", "VERIFIED_WORDING",
                f"verified wording in conclusion; claimed_strength escalated "
                f"'{claimed}' -> '{up}' (the gate reads the text, not the "
                f"field)")
        claimed = up

    # -- 2. evidence assessment with P0-1 anchor three-stage check ----------
    direct_items, indirect_items = [], []
    evidence_lines = []
    anchor_strict_fail = False
    mechanical_channel = False
    attested_channel = False
    for ev in data.get("evidence") or []:
        status, msg, anchor_text = check_anchor(ev, offline)
        ev_kind = ev["kind"]
        if ev_kind in INDIRECT_KINDS:
            indirect_items.append(ev)
            evidence_lines.append(f"[indirect] {ev_kind} — {ev['detail']}")
            if ev_kind in ("memory", "assumption"):
                finding("info", "NON_EVIDENCE_KIND",
                        f"evidence kind '{ev_kind}' is not evidence, only a "
                        f"prior (L0/L1 at most)")
            continue
        # -- P0-C temporal validity (before channel bookkeeping) -----------
        as_of = parse_date(ev.get("as_of"))
        until = parse_date(ev.get("until"))
        claim_time = data.get("claim_time", "current")
        claim_date = parse_date(claim_time) if claim_time != "current" \
            else date.today()
        window = data.get("freshness_days")
        window = window if isinstance(window, int) and not isinstance(
            window, bool) else 365
        temporal_bad = False
        if as_of and as_of > date.today():
            finding("high", "FUTURE_DATED_EVIDENCE",
                    f"evidence as_of {as_of.isoformat()} is in the future: "
                    f"a source cannot have been true before it existed — "
                    f"treated as mistaken or fabricated provenance")
            temporal_bad = True
        elif until and claim_date and claim_date > until:
            finding("high", "TEMPORAL_SUPERSEDED",
                    f"evidence valid only until {until.isoformat()} but the "
                    f"claim targets {claim_date.isoformat()}: superseded "
                    f"evidence cannot support it")
            temporal_bad = True
        elif (claim_time == "current" and as_of
              and matches_any(conclusion, RECENCY_MARKERS)
              and (date.today() - as_of).days > window):
            age = (date.today() - as_of).days
            finding("high", "TEMPORAL_STALE",
                    f"recency-marked 'current' claim rests on evidence "
                    f"dated {as_of.isoformat()} ({age} days old > "
                    f"freshness window {window}d): current state is NOT "
                    f"confirmed — check the current source or drop the "
                    f"recency marker")
            temporal_bad = True
        elif (claim_time != "current" and as_of and claim_date
              and (as_of - claim_date).days > window):
            lag = (as_of - claim_date).days
            finding("medium", "TEMPORAL_ANACHRONISTIC",
                    f"historical claim targets {claim_date.isoformat()} but "
                    f"the evidence dates {as_of.isoformat()} — {lag} days "
                    f"AFTER the fact: retrospective sources may include "
                    f"later changes; prefer period evidence (as_of closest "
                    f"to claim_time)")
            temporal_bad = True
        if temporal_bad:
            indirect_items.append(ev)
            evidence_lines.append(f"[indirect*] {ev_kind} — temporally "
                                  f"invalid for this claim")
            continue
        # direct-kind item: anchor stages decide its fate
        if status == "mechanical_ok":
            direct_items.append((ev, anchor_text))
            mechanical_channel = True
            evidence_lines.append(f"[direct·mech✓] {ev_kind} — {msg}")
        elif status == "attested":
            direct_items.append((ev, None))
            attested_channel = True
            evidence_lines.append(f"[direct·attested] {ev_kind} — {msg}")
        elif status == "partial":
            direct_items.append((ev, None))
            attested_channel = True
            evidence_lines.append(f"[direct·partial] {ev_kind} — {msg}")
            caveats.append(f"anchor only partially supports the claim: {msg[:120]}")
        elif status == "no_candidate":
            # v1 rule still applies: a direct claim needs a trace anchor
            if matches_any(ev["detail"], TRACE_PATTERNS):
                direct_items.append((ev, None))
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
            injected_counters.append({
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
            direct_items.append((ev, None))
            evidence_lines.append(f"[direct·unchecked!] {ev_kind} — {msg}")

    # -- 3. verification validity -------------------------------------------
    ver = data.get("verification") or {}
    executed = bool(ver.get("executed"))
    env_ok = ver.get("env_independent") is True
    target_ok = ver.get("validates_target") is True
    ver_channel = ver.get("channel")
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

    # -- 3b. P0-F channel routing for mechanical claim classes --------------
    claim_class = data.get("claim_class")
    channel_ok = True
    if claim_class in MECH_CLASSES \
            and STRENGTHS.index(claimed) >= STRENGTHS.index("verified") \
            and (not executed or ver_channel not in MECH_VERIF_CHANNELS):
            channel_ok = False
            finding("high", "CHANNEL_MISMATCH",
                    f"claim_class '{claim_class}' is machine-checkable: "
                    f"'{claimed}' strength requires a mechanical verification "
                    f"channel ({sorted(MECH_VERIF_CHANNELS)}), not language "
                    f"reasoning — let the machine decide what words can only "
                    f"argue about (VERGE 2026; Agentic PBT 2025)")
            actions.append(f"rerun the verification through a mechanical "
                           f"channel: execute it / test it / assert it / "
                           f"prove it, then file verification.channel")

    # -- 4. P0-A misleading-quote numeric consistency -----------------------
    # figures claimed in the conclusion but carried by NO evidence line
    # (exact value anywhere in details/quotes/anchors, or a time-unit
    # conversion '1 分钟' ~ '60 seconds'); narrow rule (1–3 figures, ALL
    # uncarried, no execution) to stay low-FRR.
    context_figs, context_pairs = set(), []
    for ev in data.get("evidence") or []:
        context_figs |= extract_figures(ev.get("detail", ""))
        context_figs |= extract_figures(ev.get("quote") or "")
        context_pairs += quantity_pairs(ev.get("detail", ""))
        context_pairs += quantity_pairs(ev.get("quote") or "")
    claimed_pairs = list(dict.fromkeys(
        (v, u) for v, u in quantity_pairs(conclusion)
        if v not in context_figs))
    missing = [p for p in claimed_pairs
               if not figure_carried(p, context_figs, context_pairs)]
    if (1 <= len(missing) <= 3 and not valid_execution and direct_items
            and ctype in ("FACT", "INFERENCE", "EXPERIMENT_RESULT")):
        carried_in_lines = False
        for ev, anchor_text in direct_items:
            ev_vals = extract_figures(ev.get("quote") or "")
            ev_pairs = quantity_pairs(ev.get("quote") or "")
            if anchor_text:
                ev_vals |= extract_figures(anchor_text)
                ev_pairs += quantity_pairs(anchor_text)
            if any(figure_carried(p, ev_vals, ev_pairs) for p in missing):
                carried_in_lines = True
                break
        if not carried_in_lines:
            want = ", ".join(f"{v} {u}".strip() for v, u in missing)
            finding("high", "MISLEADING_QUOTE",
                    f"the conclusion's figure(s) {want} appear in NONE of the "
                    f"quoted evidence or their anchors — the quotes exist but "
                    f"do not carry the claimed number(s) (citation exists ≠ "
                    f"citation supports)")
            actions.append(f"quote the line that actually contains {want}, "
                           f"or correct the figure in the conclusion")
            # quoted items claimed mechanical support they don't render;
            # they downgrade to indirect; unquoted items keep their status
            kept_direct, demoted = [], []
            for ev, anchor_text in direct_items:
                (demoted if ev.get("quote") else kept_direct).append(
                    (ev, anchor_text))
            for ev, _t in demoted:
                indirect_items.append(ev)
                evidence_lines.append(
                    f"[indirect*] {ev.get('kind')} — quote does not carry the "
                    f"claimed figure(s) {want} (misleading quote)")
            direct_items = kept_direct
            mechanical_channel = False
            attested_channel = True

    # -- 5. P0-B correlation collapse & line qualification ------------------
    # three buckets: contaminated (excluded entirely) · support-only
    # (meta/aggregator: counts for L2 support, never as an independent
    # line) · line-eligible (full qualification). Channel flags are
    # recomputed from surviving lines: an item excluded here must not keep
    # the hard-channel status it earned before exclusion.
    line_items, support_only = [], []
    for idx, (ev, anchor_text) in enumerate(direct_items):
        anchor_url = extract_anchor(ev.get("detail", ""), ev.get("anchor"))
        host = url_host(anchor_url or "")
        if host and host in CONTAMINATED_HOSTS:
            path = (urlsplit(anchor_url).path or "/") if anchor_url else "/"
            if path.startswith("/datasets") or path in ("", "/"):
                finding("high", "CONTAMINATED_SOURCE",
                        f"evidence anchor host '{host}' is a known "
                        f"contamination source (benchmark/dataset mirrors "
                        f"leak answers): excluded from the evidence base")
                continue
        elif ev.get("meta_evidence"):
            finding("info", "META_EVIDENCE",
                    f"evidence item is itself a verdict about the claim "
                    f"(fact-check/Q&A page): usable as a lead, NOT as an "
                    f"independent line (verdict leakage)")
            support_only.append((idx, ev, "meta-evidence"))
        elif ev.get("source_tier", "unknown") == "aggregator":
            finding("info", "AGGREGATOR_SOURCE",
                    f"aggregator-tier source cannot count as an independent "
                    f"line (syndication/circular reporting risk); fine for "
                    f"L2 support, never for cross-verification")
            support_only.append((idx, ev, "aggregator"))
        else:
            line_items.append((idx, ev, anchor_text))
    if line_items:
        mechanical_channel = any(t is not None
                                 for _i, _ev, t in line_items)
        attested_channel = any(t is None for _i, _ev, t in line_items)

    merged_groups, merge_reasons = correlation_analysis(
        [ev for _idx, ev, _t in line_items])
    for r in merge_reasons:
        finding("medium", "CORRELATED_EVIDENCE",
                f"evidence lines merged — {r}; independent-line count is "
                f"after collapse (100 reposts of one wire story = 1 line)")
    for idx, ev, why in support_only:
        evidence_lines.append(f"[line✗] {ev.get('kind')} — support only, "
                              f"not an independent line ({why})")
    independent_lines = len(merged_groups)
    qualified = line_items  # naming compatibility below

    # -- 6. P0-D heterogeneous verification (cross-family / tool) ------------
    generator = str(data.get("generator") or "")
    gen_family = family(generator)
    checks = data.get("independent_checks") or []
    valid_checks, same_model, unknown_checks = [], [], []
    for ic in checks:
        if ic.get("context") != "isolated":
            continue
        fam = family(str(ic.get("by", "")))
        if gen_family and fam and fam == gen_family:
            same_model.append(ic)
        elif not fam or not gen_family:
            unknown_checks.append(ic)   # identity unverifiable: not heterogeneous
        else:
            valid_checks.append(ic)
    agree_checks = [ic for ic in valid_checks if ic.get("agree") is True]
    # agreement must be cross-family to count; DISagreement blocks from ANY
    # isolated check (same/unknown family included) — a warning needs no
    # pedigree (P1-2)
    disagree_checks = [ic for ic in checks
                       if ic.get("context") == "isolated"
                       and ic.get("agree") is False]
    if same_model:
        finding("high", "SAME_MODEL_VERIFIER",
                f"independent_check by '{same_model[0].get('by')}' shares the "
                f"generator's family ('{gen_family}'): same-model agreement "
                f"is correlated failure, not cross-validation (cross-family "
                f"> same-family > self, arXiv:2512.02304)")
        actions.append("redo the independent check with a model of a "
                       "DIFFERENT family, or a mechanical re-derivation")
    if unknown_checks:
        finding("warn", "VERIFIER_IDENTITY_UNKNOWN",
                f"independent_check by '{unknown_checks[0].get('by')}' has no "
                f"recognizable model family (or the generator is unnamed): "
                f"heterogeneity cannot be confirmed from the identifier — "
                f"not counted toward cross-family verification")
    for ic in disagree_checks:
        finding("high", "INDEPENDENT_DISAGREEMENT",
                f"isolated independent check by '{ic.get('by')}' DISAGREES "
                f"with the conclusion: agreement cannot be cherry-picked, and "
                f"a warning needs no pedigree")
        actions.append("resolve the disagreement: find which side is wrong, "
                       "or downgrade the conclusion to what both sides "
                       "support")
    # a line verified by a deterministic tool or a different agent breaks
    # model correlation by construction (tool output shares no LLM prior)
    tool_verified = False
    for _idx, ev, _t in qualified:
        vb = str(ev.get("verified_by", "self") or "self").strip()
        if vb.startswith("tool:") and vb[5:].strip():
            tool_verified = True
        elif vb.startswith("agent:") and gen_family \
                and family(vb[6:]) and family(vb[6:]) != gen_family:
            tool_verified = True
    verifier = dict(data.get("verifier") or {})
    verifier.setdefault("id", "unspecified")
    verifier.setdefault("protocol", f"gate_check/{__version__}")
    if generator and family(str(verifier.get("id", ""))) == gen_family \
            and gen_family:
        finding("warn", "VERIFIER_SAME_ORIGIN",
                f"verifier '{verifier['id']}' is the same family as the "
                f"generator '{generator}': its judgment alone cannot support "
                f"cross-verified wording")
    cross_family_ok = bool(agree_checks) or tool_verified

    # -- 7. evidence level ----------------------------------------------------
    level = 0
    if indirect_items:
        level = max(level, 1)
    if line_items or support_only:
        level = max(level, 2)
    if valid_execution:
        level = max(level, 3)
    # L4: ≥2 independent lines AND one hard channel among them
    # (mechanical quote check, a tool/agent-verified line, or a valid
    # agreeing cross-family check). Pure attestation never reaches L4 (P0-E).
    hard_channel = mechanical_channel or tool_verified or bool(agree_checks)
    if independent_lines >= 2 and hard_channel:
        level = max(level, 4)
    elif independent_lines >= 2 and not hard_channel:
        finding("medium", "ATTESTED_ONLY_LINES",
                "≥2 independent lines exist but NONE is mechanically "
                "verified (no checked quote, no tool-verified line) and no "
                "valid agreeing cross-family check exists: cross-verified "
                "wording rests on self-attestation alone — capped at L3")

    # -- 8. required level -----------------------------------------------------
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
    # cross_verified at high/extreme additionally demands HETEROGENEOUS
    # verification (P0-D): a cross-family independent check, or a line
    # verified by a deterministic tool / different agent. Same-model
    # self-judgment alone cannot constitute "cross-verification".
    cross_family_required = (claimed == "cross_verified"
                             and risk in ("high", "extreme"))

    # -- 9. counter-evidence ------------------------------------------------
    # declared counters plus ones the gate itself derived (contradicted
    # anchors); the caller's input dict is never mutated
    counters = list(data.get("counter_evidence") or []) + injected_counters
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

    # -- 10. generalization ------------------------------------------------------
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

    # -- 11. decision ------------------------------------------------------------
    decision = None

    # effective claimed (post wording-escalation): "已验证" prose with a
    # 'judged' field is still a verification claim and is judged as one
    if claimed in ("verified", "cross_verified") and (
            not valid_execution or not channel_ok):
        why = ("claimed 'verified' but no VALID execution exists"
               + (" — reasoning/reading/analysis is NOT verification"
                  if not executed
                  else " — the executed verification was voided: "
                       "verification environment not independent, "
                       "or test does not validate the target"))
        if executed and not channel_ok:
            why += ("; verification channel is not mechanical for a "
                    "machine-checkable claim class")
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

    if decision is None and cross_family_required and not cross_family_ok:
        finding("high", "CROSS_FAMILY_MISSING",
                "cross-verified wording at high/extreme risk without "
                "heterogeneous verification: same-model agreement is "
                "correlated failure, not cross-validation")
        decision = "VERIFY_REQUIRED"
        actions.append("cross-verified wording at high/extreme risk needs "
                       "heterogeneous verification: an isolated independent "
                       "check by a DIFFERENT model family, or an evidence "
                       "line verified by a deterministic tool "
                       "(evidence[].verified_by='tool:...') — agreement "
                       "within one model is correlated failure")

    # an isolated cross-family check that DISAGREES blocks the conclusion:
    # agreement cannot be cherry-picked from a mixed set of checks (P1-2)
    if decision is None and disagree_checks:
        decision = "VERIFY_REQUIRED"

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
            reason_field = data.get("unobtainable_reason")
            actions.append("state the gap explicitly: “目前无法确认” + what "
                           "evidence is missing and who can provide it; do "
                           "not output the conclusion at any strength"
                           + (f" (unobtainable: {reason_field})"
                              if reason_field else ""))
        else:
            decision = "VERIFY_REQUIRED"
            if not executed and (works or causal or claimed in
                                 ("verified", "cross_verified")):
                actions.append("execute the actual verification: run the "
                               "program / tests / benchmark instead of "
                               "reasoning about it")
            if ctype == "FACT" and level < 2:
                actions.append("locate an authoritative source (official "
                               "docs, source code, config, data) and cite it "
                               "with a resolvable anchor + quote")
            if req == 4 and independent_lines < 2:
                actions.append("add at least one INDEPENDENT evidence line "
                               "(different tool / method / host / environment) "
                               "for cross-validation — correlated reposts "
                               "do not count")
            if req == 4 and not hard_channel:
                actions.append("mechanically verify one line (quote check) "
                               "or add a cross-family independent check: "
                               "attested-only lines cannot reach cross-verified")
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

    # -- allowed wording (with active calibration caps) --------------------------
    allowed_strength = LEVEL_STRENGTH[level]
    if (causal or works) and not valid_execution:
        allowed_strength = min(allowed_strength, "possibly", key=STRENGTHS.index)
    if claimed == "absolute":
        allowed_strength = min(allowed_strength, "cross_verified",
                               key=STRENGTHS.index)
    cap_note = None
    for lv_str, cap in (level_caps or {}).items():
        # a stale/hand-edited overrides file must never index out of range
        cap_lv = min(4, max(0, int(cap.get("cap_level", 0))))
        if int(lv_str) == level and STRENGTHS.index(allowed_strength) > cap_lv:
            allowed_strength = LEVEL_STRENGTH[cap_lv]
            cap_note = (f"active calibration: L{lv_str} measured accuracy "
                        f"{cap['accuracy']:.0%} (n={cap['n']}) is below its "
                        f"wording promise — wording capped at "
                        f"{allowed_strength}")
            finding("info", "CALIBRATION_DOWNGRADE", cap_note)
    allowed_wording = LEVEL_WORDING[STRENGTH_REQ[allowed_strength]]
    if allowed_strength == "possibly" and (causal or works) and not valid_execution:
        allowed_wording += " — 未实际运行验证 (not actually executed/verified)"
    if decision == "ABSTAIN":
        allowed_wording = "目前无法确认 (cannot confirm) — state the gap"

    # -- evidence ledger (proof-carrying output) ---------------------------------
    for g_idx, group in enumerate(merged_groups):
        for i in group:
            idx, ev, t = qualified[i]
            ledger.append({
                "line": f"line{g_idx + 1}", "kind": ev.get("kind"),
                "anchor": extract_anchor(ev.get("detail", ""), ev.get("anchor")),
                "channel": "mechanical" if t is not None else "attested",
                "source_tier": ev.get("source_tier", "unknown"),
                "as_of": ev.get("as_of"),
                "collapsed_with": [line_label(qualified[j][1])
                                   for j in group if j != i],
            })

    verifier["entailment_channel"] = ("mechanical" if mechanical_channel
                                      else "attested" if attested_channel
                                      else "none")
    verifier["independent_checks"] = {
        "valid_agreeing": len(agree_checks),
        "cross_family_required": cross_family_required,
        "cross_family_ok": cross_family_ok if cross_family_required else None}

    return {
        "conclusion": conclusion,
        "type": ctype,
        "claimed_strength": claimed,
        "risk_tier": risk,
        "gate_point": gate_point,
        "evidence_level": f"L{level}",
        "evidence_level_num": level,
        "required_level_num": req,
        "independent_lines": independent_lines,
        "decision": decision,
        "reason": reason,
        "findings": findings,
        "evidence_lines": evidence_lines,
        "ledger": ledger,
        "allowed_strength": allowed_strength,
        "allowed_wording": allowed_wording,
        "caveats": caveats,
        "required_actions": actions,
        "counter_search_context": ctx,
        "unobtainable_reason": data.get("unobtainable_reason"),
        "calibration_note": ("levels are ordinal, not probabilities; empirical "
                             "per-level accuracy via --calibration"
                             + (f"; {cap_note}" if cap_note else "")),
        "verification": {"executed": executed, "valid": valid_execution,
                         "env_independent": ver.get("env_independent", "unknown"),
                         "validates_target": ver.get("validates_target", "unknown"),
                         "channel": ver_channel},
        "generator": generator or None,
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
                 f"L{r['required_level_num']}; independent lines: "
                 f"{r['independent_lines']})")
    lines.append("Evidence (anchor three-stage check):")
    for ev in r.get("evidence_lines") or ["(none listed)"]:
        lines.append(f"  - {ev}")
    v = r["verification"]
    lines.append(f"  execution: executed={v['executed']} valid={v['valid']} "
                 f"env_independent={v['env_independent']} "
                 f"validates_target={v['validates_target']} "
                 f"channel={v['channel']}")
    lines.append(f"Counter-evidence search context: {r['counter_search_context']}")
    if r.get("unobtainable_reason"):
        lines.append(f"Unobtainable: {r['unobtainable_reason']}")
    lines.append("Findings:")
    for f in r["findings"]:
        lines.append(f"  [{f['severity']}] {f['code']}: {f['message']}")
    lines.append(f"Decision: {r['decision']}  (exit {DECISION_EXIT[r['decision']]})")
    lines.append(f"Reason:\n  {r['reason']}")
    lines.append(f"Allowed wording: {r['allowed_wording']}")
    lines.append(f"Calibration: {r['calibration_note']}")
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
    level_caps = load_overrides(opts)
    result = assess(data, gate_point=opts["gate_point"], offline=opts["offline"],
                    level_caps=level_caps)
    ts = time.strftime("%Y-%m-%dT%H:%M:%S")
    result["ts"] = ts
    result["gate_id"] = hashlib.sha1(
        (ts + "|" + result["conclusion"]).encode("utf-8")).hexdigest()[:8]
    result["script_version"] = __version__
    append_log(opts, {
        "ts": ts, "gate_id": result["gate_id"],
        "script_version": __version__, "gate_point": opts["gate_point"],
        "decision": result["decision"], "evidence_level": result["evidence_level"],
        "evidence_level_num": result["evidence_level_num"],
        "independent_lines": result["independent_lines"],
        "claimed_strength": result["claimed_strength"], "type": result["type"],
        "risk_tier": result["risk_tier"], "verifier": result["verifier"],
        "findings": [f["code"] for f in result["findings"]],
        "allowed_strength": result["allowed_strength"],
        "unobtainable_reason": result["unobtainable_reason"],
        "conclusion": result["conclusion"], "outcome": None, "input": data,
    })
    if opts["json"]:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_text(result))
    sys.exit(DECISION_EXIT[result["decision"]])


if __name__ == "__main__":
    main()
