# Decision Rules — what gate_check.py implements

The script is the source of truth; this file restates its logic so you can
predict outcomes and fill inputs correctly. Rule order matters.

## Required level computation

```
req = {hypothesis:0, possibly:1, likely:1, judged:2, verified:3,
       cross_verified:4, absolute:4}[claimed_strength]
req = max(req, 2)                          if type == FACT
req = max(req, 3)                          if type == EXPERIMENT_RESULT
req = max(req, 3)                          if causal claim  and claimed ≥ judged
req = max(req, 3)                          if works claim   and claimed ≥ likely
req = max(req, 3)                          if risk high     and claimed ≥ judged
req = max(req, 4) if claimed ≥ verified    if risk extreme
   else max(req, 3) if claimed ≥ judged    if risk extreme
```

Auto-escalations applied to the input first (anti-bypass):

- Absolute wording in the conclusion text (100%, 全部, 所有, 一定, 完全,
  绝对, 肯定, 均, guaranteed, always, never, every, all) → `claimed_strength`
  becomes `absolute`, risk ≥ high — regardless of what the field says.
- Risk-topic keywords (benchmark/基准, 数据质量, 去重, docker, 镜像, golden,
  成本, 工期, 验收, 干净, 合格...) → risk ≥ high.
- Causal wording (导致, 引起, 是因为, caused by...) → causal claim.
- Works/success wording (可以运行, 正常运行, 不会中断, 不会破坏, 已修复,
  修复成功, 已解决, fixed, works, resolved...) → works claim.
- `--gate-point pre-action` → risk escalates one tier (medium→high,
  high→extreme) and any works claim requires execution (works_floor =
  possibly): code-reading alone never clears a "won't break" claim right
  before an irreversible action.

## Mechanical checks (v2) — run before decisions

These don't depend on your attestation fields; they check artifacts and text:

- **Anchor three-stage check** (direct items with a local-file/URL anchor):
  (1) does the anchor resolve? (2) is a quote provided? (3) is the quote
  actually in the file? Quote missing / anchor missing / quote contradicts
  the file → item downgrades direct→indirect. `content_supports:
  "unsupported"` → auto-injects a contradicting counter-evidence item.
- **Conclusion text scan** — absolute wording, causal wording, works wording
  are detected in the text regardless of the fields you filed.
- **Counter-search context cap** — `cross_verified` / absolute claims, and
  empty counter lists at high/extreme risk with claimed ≥ verified, require
  `counter_search_context: "isolated"`. `same` or missing →
  COUNTER_SEARCH_NOT_ISOLATED → VERIFY_REQUIRED (L4 cannot stand on
  same-context searching; agreement bias survives extra compute).

## Decision, in evaluation order

1. **FAKE_VERIFICATION → REJECT** — claimed `verified`/`cross_verified`
   (as filed) but no valid execution exists. Covers both "analyzed but never
   ran" and "ran but voided" (contaminated env / untargeted test).
2. **FACT_CONTRADICTED → REJECT** — FACT type with an *unaddressed*
   counter-evidence item marked `contradicts`. A fact with a live
   contradiction is not outputtable; address or refute it first.
3. **ABSOLUTE_OVERREACH → REJECT** — absolute claim with level < required
   (L4). More evidence never legitimizes "一定"; scope the claim instead.
4. **SAMPLE_TO_POPULATION → REJECT** — generalization from sample to
   population without `statistical_basis` while claiming the whole
   (absolute/verified). Restate scoped to the sample.
5. **Shortfall → VERIFY_REQUIRED or ABSTAIN** — required level > evidence
   level. Normally VERIFY_REQUIRED. But if `evidence_obtainable: "no"` —
   the settling evidence does not exist or is not accessible — the decision
   is **ABSTAIN**: say 目前无法确认, state the gap and why it can't be
   closed. A hedged guess is not an abstention; a hedge implies you could
   know. (`unknown`/`yes` behave as v1.)
   The output lists concrete actions (execute it / find a source / add an
   independent line) and the downgrade option. Downgrading is always
   legitimate: rerun the gate with the lower claim.
6. **Counter-evidence caps** — otherwise-passing conclusions:
   - unaddressed contradicting counter + (high/extreme risk OR strong claim)
     → VERIFY_REQUIRED;
   - any unaddressed or explained counter → PASS_WITH_CAVEAT, caveats are
     mandatory content in the output;
   - refuted counters don't cap.
7. **Pre-action mode default** — at `--gate-point pre-action`, a conclusion
   that would PASS_WITH_CAVEAT on unexecuted evidence becomes
   VERIFY_REQUIRED: irreversible actions need the verification done first,
   not promised alongside.

## Type-specific standards

| Type | Must have | Classic failure |
|------|-----------|-----------------|
| FACT | authoritative source (L2+), anchor + quote verified | "everyone knows" (memory, L0) |
| INFERENCE | each logic step supported; alternatives sought | correlation → causation |
| HYPOTHESIS | labeled as hypothesis in the output | hypothesis stated as finding |
| RECOMMENDATION | stated basis + applicability conditions | advice without conditions |
| EXPERIMENT_RESULT | actual execution (L3+, valid) | narrative of a run that never happened |

## Confidence

- REJECT / VERIFY_REQUIRED / ABSTAIN → LOW
- PASS_WITH_CAVEAT → ≤ MEDIUM
- PASS → L3+ without live counters: HIGH · L2: MEDIUM · L0/L1: LOW

## Exit codes

`0` PASS / PASS_WITH_CAVEAT · `10` VERIFY_REQUIRED · `15` ABSTAIN ·
`20` REJECT · `2` input error. CI-friendly: non-zero blocks the conclusion
from shipping as-is.

## Audit log and calibration (v2)

Every run appends a JSONL entry (gate_id, conclusion, decision, level,
timestamp) to `.evidence-gate-log.jsonl` (or `--log PATH`; `--no-log` for
one-off runs). Close the loop when you learn the true outcome:

```
--mark-outcome <gate_id> correct|wrong
--calibration      # per-level: runs / known / correct / accuracy
```

Calibration exists because self-reported levels are ordinal but their
absolute "actually right" rate is unknown until measured. A level whose
accuracy is poor is a wording ceiling you've been exceeding.

## Edge cases

- **Two docs, one source of truth** (official doc + blog quoting it) → one
  group; L2, not L4.
- **Execution that repeats the same evidence** (you ran the bench that
  produced the only direct artifact) → still one group; L3, not L4.
- **Counter-evidence refuted** must say *how* it was refuted in `detail`;
  "refuted" without a refutation is addressing it in name only.
- **Downgrade-then-inflate** — rerunning with `claimed_strength: hypothesis`
  but keeping absolute prose in `conclusion` gets caught by the text
  escalation; the conclusion text is checked, not just the field.
- **Splitting one claim** into many small ones to duck the gate: if the
  deliverable's overall message needs the strong claim, gate the strong
  claim.
- **Issue-id anchors** (#8842, commit sha without a local checkout) are
  trace-only: they count as anchors for L2 but the script can't open them,
  so quote verification doesn't apply — content attestation
  (`content_supports`) is the channel, and it lands in the audit log.
- **URL anchors offline or unfetchable** (`--offline`, network failure):
  mechanical check is skipped; with `content_supports: supported|partial`
  the item stands as attested (logged as channel=attested); with no
  attestation it's an unresolved anchor — medium finding, and strong claims
  (≥ verified, or FACT at high risk) fail anchor strictness.
