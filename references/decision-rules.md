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
- `--gate-point pre-action` → risk is escalated to high if it was low/medium
  (high/extreme stay as filed) and any works claim requires execution
  (works_floor = possibly): code-reading alone never clears a "won't break"
  claim right before an irreversible action.

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

## Mechanical checks (v3) — added before decisions

- **MISLEADING_QUOTE (numeric consistency)** — if the conclusion (type
  FACT/INFERENCE/EXPERIMENT_RESULT) claims 1–3 quantity figures with units
  (30 秒 / 60s / 2.5 倍 / 95%…) and NONE of them is carried by any quote,
  anchor text, or evidence detail (exact value, after normalizing
  thousand separators / trailing zeros / full-width digits; time units are
  converted — a conclusion's "0.5 分钟" is carried by a quote's
  "30 seconds"), and no valid execution exists, every quoted line is
  demoted to indirect: the citations exist but do not carry the claimed
  numbers. Deliberately narrow (all-uncarried figures + no execution) — a
  broader rule measurably over-blocks honest conclusions (FRR 5/10 in
  prototyping; the narrow rule holds FRR at 0).
- **CORRELATED_EVIDENCE (independence collapse)** — evidence lines merge
  into one independent line when they: share a declared `group`; share a
  registrable URL domain (unless BOTH attest `same_host_independent:
  true`); have near-identical quotes (token Jaccard ≥ 0.7); or one cites
  another's anchor URL (in its quote OR its detail text — syndication
  chain). `independent_lines` is counted AFTER collapse — 100 reposts of
  one wire story = 1 line. Aggregator-tier sources (`source_tier:
  aggregator`) support a scoped L2 claim but never form an independent
  line.
- **TEMPORAL_STALE / TEMPORAL_SUPERSEDED / FUTURE_DATED_EVIDENCE /
  TEMPORAL_ANACHRONISTIC** — evidence with `until` earlier than the claim
  date is demoted to indirect; a recency-marked claim (当前/最新/现在…)
  on evidence whose `as_of` is older than `freshness_days` (default 365)
  is demoted to indirect; evidence dated in the future (as_of after
  today) is demoted as mistaken or fabricated provenance; a historical
  claim (`claim_time` set) resting on evidence dated long AFTER the
  claim time (more than `freshness_days` past it) is flagged
  anachronistic — prefer period evidence. Historical claims with
  `claim_time` are judged against period evidence: old ≠ wrong, but
  old ≠ current.
- **SAME_MODEL_VERIFIER + cross-family requirement** — cross_verified at
  high/extreme risk requires heterogeneous verification: an agreeing
  `independent_check` by a model of a DIFFERENT family than `generator`
  (run in `context: isolated`), or at least one line `verified_by:
  "tool:NAME"` (a tool with an actual name — `"tool:"` alone counts for
  nothing). A same-family check is flagged and does not count; a check
  whose family cannot be read from its identifier (or with no declared
  generator) does not count either — self-reported identity is not
  corroboration. DISagreement is the opposite: an isolated check with
  `agree: false` blocks the conclusion from ANY family (agreement must
  be cross-family; a warning needs no pedigree). Same-model agreement is
  correlated failure: cross-family > same-family > self,
  arXiv:2512.02304; 60% same-error agreement between same-family models,
  ICML 2025. Deterministic tools are heterogeneous by construction —
  they share no LLM prior.
- **ATTESTED_ONLY_LINES (L4 hard-channel cap)** — ≥2 post-collapse lines
  but NONE mechanically verified (no quote-checked local line, no
  tool-verified line, no valid agreeing check) caps the level at L3:
  "there is evidence" ≠ "the evidence was examined".
- **CHANNEL_MISMATCH (claim-class routing)** — claim_class in
  {code_behavior, config, data, math} asserted at `verified`+ requires
  `verification.channel` in {execution, test, assertion, formal_proof,
  statistical}; a `reasoning`/reading channel voids the execution →
  FAKE_VERIFICATION → REJECT. Machine-checkable claims are settled by
  machines, not argued in prose.
- **CONTAMINATION** — evidence anchored to a known benchmark-contamination
  host (huggingface.co / hf.co dataset paths) is excluded from the
  evidence base entirely: contaminated data cannot verify claims built
  on it.

## Decision, in evaluation order

1. **FAKE_VERIFICATION → REJECT** — claimed `verified`/`cross_verified`
   (as filed OR as escalated from verified wording in the text — the gate
   reads the text, not the field) but no valid execution exists. Covers
   both "analyzed but never ran" and "ran but voided" (contaminated env /
   untargeted test / channel mismatch on a machine-checkable claim class).
2. **FACT_CONTRADICTED → REJECT** — FACT type with an *unaddressed*
   counter-evidence item marked `contradicts`. A fact with a live
   contradiction is not outputtable; address or refute it first.
3. **ABSOLUTE_OVERREACH → REJECT** — absolute claim with level < required
   (L4). More evidence never legitimizes "一定"; scope the claim instead.
4. **SAMPLE_TO_POPULATION → REJECT** — generalization from sample to
   population without `statistical_basis` while claiming the whole
   (absolute/verified). Restate scoped to the sample.
5. **Cross-family shortfall → VERIFY_REQUIRED** — cross_verified at
   high/extreme risk without heterogeneous verification
   (`cross_family_required` true, `cross_family_ok` false): the missing
   ingredient is WHO checked, not more lines of the same kind.
6. **Independent disagreement → VERIFY_REQUIRED** — an isolated
   independent_check with `agree: false` (any family). Agreement cannot
   be cherry-picked from a mixed set of checks.
7. **Counter-search not isolated → VERIFY_REQUIRED** — strong claims with
   a same-context counter-evidence search (see the v2 mechanical check
   above).
8. **Anchor strictness → VERIFY_REQUIRED** — unresolved/unchecked anchors
   on strong claims (≥ verified, or FACT at high/extreme risk).
9. **Shortfall → VERIFY_REQUIRED or ABSTAIN** — required level > evidence
   level. Normally VERIFY_REQUIRED. But if `evidence_obtainable: "no"` —
   the settling evidence does not exist or is not accessible — the decision
   is **ABSTAIN**: say 目前无法确认, state the gap and why it can't be
   closed, and the output records `unobtainable_reason`
   (no_access / nonexistent / unreproducible / undecidable) so refusals
   are auditable. A hedged guess is not an abstention; a hedge implies you
   could know. (`unknown`/`yes` behave as v1.)
   The output lists concrete actions (execute it / find a source / add an
   independent line) and the downgrade option. Downgrading is always
   legitimate: rerun the gate with the lower claim.
10. **Counter-evidence caps** — otherwise-passing conclusions:
    - unaddressed contradicting counter + (high/extreme risk OR strong claim)
      → VERIFY_REQUIRED;
    - any unaddressed or explained counter → PASS_WITH_CAVEAT, caveats are
      mandatory content in the output;
    - refuted counters don't cap.

Pre-action mode is not a separate step: it escalates risk and lowers the
works floor *before* the rules above run (see auto-escalations), which is
how an unexecuted works claim reaches shortfall at pre-action while the
same input in conclusion mode may pass.

## Type-specific standards

| Type | Must have | Classic failure |
|------|-----------|-----------------|
| FACT | authoritative source (L2+), anchor + quote verified | "everyone knows" (memory, L0) |
| INFERENCE | each logic step supported; alternatives sought | correlation → causation |
| HYPOTHESIS | labeled as hypothesis in the output | hypothesis stated as finding |
| RECOMMENDATION | stated basis + applicability conditions | advice without conditions |
| EXPERIMENT_RESULT | actual execution (L3+, valid) | narrative of a run that never happened |

## Calibration, not confidence (v3)

The heuristic `confidence` field was REMOVED in v3: a rule-of-thumb
confidence label is itself an unverified claim. What replaces it:

- the **evidence level** (ordinal, mechanically derived, per-line ledger);
- **measured calibration** — per-level accuracy with Wilson CIs,
  monotonicity checks, a risk-coverage curve + AURC, abstention precision/
  recall, and per-finding attribution on wrongly-accepted conclusions, from
  `--mark-outcome` records;
- `--emit-overrides` (needs ≥10 marked outcomes per level) writes
  `.evidence-gate-calibration.json` with level_caps the gate then enforces
  as active wording ceilings.

Levels are ordinal and calibration comes only from measured outcomes —
never treat L-numbers as probabilities.

## Exit codes

`0` PASS / PASS_WITH_CAVEAT · `10` VERIFY_REQUIRED · `15` ABSTAIN ·
`20` REJECT · `2` input error. CI-friendly: non-zero blocks the conclusion
from shipping as-is.

## Audit log and calibration (v3)

Every run appends a JSONL entry (gate_id, decision, evidence level,
independent_lines, finding codes, allowed_strength, unobtainable_reason,
the full input, and more) to `.evidence-gate-log.jsonl` (or `--log PATH`;
`--no-log` for one-off runs). Close the loop when you learn the true
outcome:

```
--mark-outcome <gate_id> correct|incorrect|unknown
--calibration      # per-level accuracy + Wilson CI, risk-coverage/AURC,
                   # abstention P/R, per-finding error attribution
--emit-overrides   # write calibrated level_caps (≥10 outcomes/level)
```

Calibration exists because self-reported levels are ordinal but their
absolute "actually right" rate is unknown until measured. A level whose
measured accuracy is poor becomes an enforced wording ceiling
(`.evidence-gate-calibration.json`), not a vibe.

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
- **Same-host items that really are independent** (two distinct databases
  on one company domain): attest `same_host_independent: true` on BOTH
  items; the host-collapse rule then leaves them separate. The attestation
  is logged and auditable like every other.
- **Version numbers are not quantities** — "foo-lib 3.2" does not trip
  MISLEADING_QUOTE (only unit-bearing figures do); and a recommendation's
  conditional threshold ("若需稳定低于 200ms…") is not a claimed figure —
  the rule is scoped to FACT/INFERENCE/EXPERIMENT_RESULT for exactly this
  reason.
- **Paraphrase invariance** — semantically equivalent rewrites of the
  conclusion must not flip the decision (tests case20–22 pin this):
  a gate that can be reworded around is a wording game, not a gate
  (isomorphic-perturbation testing, arXiv:2604.15149).
- **Aggregator-scoped claims** — "据聚合转载报道…" at `judged` with
  `source_tier: aggregator` evidence passes at L2: the aggregator supports
  the scoped claim but never counts as an independent verification line,
  so it cannot carry verified/cross_verified wording.
