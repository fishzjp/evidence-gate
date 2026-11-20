---
name: evidence-gate
version: 3.0.0
description: Use when about to state or deliver any key conclusion — facts, causal explanations, verification/success claims ("verified", "fixed", "it works"), data-quality or benchmark judgments, environment-cleanliness claims, estimates, or absolute statements (100%, 全部, 一定, guaranteed) — and before closing tickets, sending final reports, or executing irreversible actions (deploy, delete, send, merge, purchase). Also use when evidence looks thin, one-sided, correlated (same-origin reposts), outdated for a "current" claim, or comes only from code reading/memory; when "independent" verification might be the same model checking itself; when tests pass but coverage is unclear; when a citation might not actually support the claim (quote exists but numbers disagree); or when verification ran in a possibly contaminated environment or the wrong channel (reasoning about machine-checkable claims).
---

# Evidence Gate

A conclusion quality gate that runs **before** key conclusions reach the user.
It does not make you more careful with words — it mechanically prevents
conclusion strength from exceeding evidence strength.

**Core rules:**

1. **Verify first, conclude second.** If a tool, test, or command can check
   the claim, run it before asserting anything about it — through the channel
   the claim class requires (machine-checkable claims get machines, not prose).
2. **Conclusion strength ≤ evidence strength.** Always, mechanically, via
   `scripts/gate_check.py`. Evidence *strength* is counted after independence
   collapse and temporal validity — 100 reposts of one wire story are 1 line,
   and a 2024 snapshot cannot confirm a "current" claim.
3. **Cannot confirm → say so.** "目前无法确认" is a valid answer; an
   unverified-but-plausible claim presented as fact is not.
4. **Who verified matters.** Agreement routes, it never decides: a same-model
   "independent check" is correlated failure wearing a costume (cross-family
   model or mechanical tool, or it does not count).

Violating the letter of these rules is violating their spirit. If you catch
yourself reasoning around the gate, that is the gate working — rerun it with
the honest input.

## When to gate

Gate a conclusion when ANY of these hold:

- It asserts a **fact** (API behavior, library semantics, data contents)
- It asserts or implies **causation** (A 导致 B / A caused B)
- It claims **verification or success** ("已修复", "works", "tests pass so the
  bug is fixed", "已验证")
- It is a **quality/quantity judgment** (data clean, benchmark pass, image
  clean, no duplicates) or an **estimate** (cost, schedule, feasibility)
- It uses **absolute language** (100%, 全部, 所有, 一定, 完全, guaranteed)
- It goes into a **final deliverable** (report, PR description, ticket close)

## When NOT to gate

Skipping is correct, not lazy, in these cases:

- **Subjective preferences and taste** ("the API feels clunky").
- **Intermediate reasoning already hedged as such** ("assuming X for now,
  will verify before final"). Gate it when it graduates into the output.
- **Statements verified in the same breath** ("the file has 42 lines — I
  just counted"). Re-verification of verified things is a failure mode too.
- **Pure questions to the user** (asking ≠ asserting).
- **Low-risk trivia** where being wrong costs nothing and wording is
  already hedged. Depth scales with risk tier
  (see `references/risk-tiers.md`): low → wording-table check only;
  medium → gate script; high/extreme → gate script + actual verification +
  isolated counter-search + independent second line.

The gate calibrates; it does not silence. Blocking legitimate judgment is
as much a gate failure as letting an overclaim through.

## The Gate Loop (per key conclusion)

```
1. IDENTIFY    Extract the conclusion; classify: FACT | INFERENCE | HYPOTHESIS
               | RECOMMENDATION | EXPERIMENT_RESULT. Route by claim class:
               code_behavior / config / data / math claims are
               machine-checkable — plan a mechanical channel (execution, test,
               assertion, formal proof, statistics), not prose.
2. VERIFY FIRST  If a tool/run/test can check it → run it NOW, don't reason on.
               能执行就执行，能查询就查询，能读源码就读源码，能查数据就查数据.
               Record verification.channel; for machine-checkable classes it
               must be mechanical or 'verified' is voided (CHANNEL_MISMATCH).
3. COLLECT     List evidence items with anchors + provenance. For any doc/URL
               claim, the check is three-stage: (a) anchor resolves, (b) you
               actually read the content, (c) a quoted line from it supports
               the claim. "The citation exists" ≠ "the citation supports it" —
               half of real citations don't (see docs/research-survey.md). For
               local files give anchor + quote; the script verifies the
               quote mechanically AND that quoted figures match the figures
               the conclusion claims (MISLEADING_QUOTE). Date every source
               (as_of); if the conclusion is time-scoped, set claim_time; a
               "current"-marked claim on stale evidence is blocked
               (TEMPORAL_STALE), a historical claim on period evidence passes.
               Mark aggregator/repost sources (source_tier) — they support
               but never count as independent lines.
4. FALSIFY     Two-step ISOLATED counter-search (SGV pattern): first write
               what evidence would falsify the conclusion and where it would
               live — WITHOUT looking at your supporting evidence again —
               then go search those places. Same-context counter-search
               (asking in the context that already contains your conclusion)
               measurably fails to surface counter-evidence: agreement bias
               survives extra compute. To claim cross_verified you must set
               counter_search_context: "isolated".
5. INDEPENDENT CHECK  For verified/cross_verified at high+ risk: have a
               DIFFERENT-FAMILY model (or a deterministic tool) check the
               claim in an isolated context and file it under
               independent_checks (or verified_by: "tool:NAME" on the line).
               Same-family agreement is correlated failure, not verification.
6. GATE        Run the script with the input below. Read the decision.
7. OBEY        Follow the decision exactly, including caveats and wording.
```

**Step 4 questions** (answer them in the input, not just in your head):
如果结论是错的，最可能是什么？有没有证据能推翻它？有没有第二种解释？
有没有遗漏的前提、边界条件、版本/环境/配置差异？有没有反例？
Only-searching-for-support is the failure mode; the input schema forces the
counter-evidence field to exist, even if the list is empty.

**Pre-action gate (G3):** about to execute something irreversible — deploy,
delete, send, merge, purchase, close a ticket? Run the gate with
`--gate-point pre-action`. In that mode low/medium risk escalates to high
(high/extreme stay as filed) and ANY "works / won't break" claim requires
actual execution (works_floor drops to `possibly`) — code-reading alone never
clears a works claim at the point of no return. Concluding too late is the
same as not concluding: a wrong claim that slips out in the deploy message
does its damage even if the next gate would have caught it.

## Gate input

Write the JSON to a temp file (or stdin), then run:

```bash
python3 scripts/gate_check.py gate-input.json     # human-readable
... | python3 scripts/gate_check.py --json -      # machine-readable
... | python3 scripts/gate_check.py --json --gate-point pre-action -
... | python3 scripts/gate_check.py --offline -   # never fetch URL anchors:
                                                  # unfetchable URLs take the
                                                  # attested/unresolved path
                                                  # (deterministic, CI-safe)
```

```json
{
  "conclusion": "the exact conclusion you are about to output",
  "type": "FACT",
  "claimed_strength": "judged",
  "risk_tier": "medium",
  "generator": "glm-5.3",
  "claim_class": "code_behavior",
  "claim_time": "2024-06-01",
  "evidence": [
    {"kind": "official_doc", "detail": "what it says + why it matters",
     "anchor": "https://... or tests/fixtures/foo.md", "quote": "exact line",
     "content_supports": "supported", "as_of": "2026-11-01",
     "source_tier": "primary", "group": "docs"},
    {"kind": "test_result", "detail": "pytest run #882 — ...", "group": "run-882",
     "verified_by": "tool:pytest"}
  ],
  "verification": {"executed": false, "detail": "",
                   "env_independent": "unknown", "validates_target": "unknown",
                   "channel": "test"},
  "independent_checks": [
    {"by": "claude-sonnet-4.5", "channel": "retrieval_fresh", "agree": true,
     "context": "isolated", "detail": "re-derived the number from source"}
  ],
  "counter_evidence": [
    {"detail": "...", "status": "unaddressed", "contradicts": true}
  ],
  "counter_search_context": "isolated",
  "evidence_obtainable": "yes",
  "unobtainable_reason": null,
  "generalization": null
}
```

Field rules (the script enforces these — fill them honestly the first time):

- `type` — FACT (needs a source) / INFERENCE (needs a logic chain) /
  HYPOTHESIS (must be labeled as such) / RECOMMENDATION (needs stated basis
  and conditions) / EXPERIMENT_RESULT (needs actual execution).
- `claimed_strength` — what your draft wording actually asserts:
  `hypothesis | possibly | likely | judged | verified | cross_verified`.
  The script auto-escalates to `absolute` if the conclusion text contains
  absolute wording — claim "judged" all you like, “全部/100%” will be caught.
- `evidence[].kind` — direct: `official_doc, source_code, config, data, log,
  test_result, sample`; indirect: `observation, time_correlation, memory,
  assumption, anecdote`. `memory` and `assumption` are NOT evidence (L0).
- `evidence[].anchor` + `quote` — the three-stage check for direct evidence.
  For a local file the script opens it and verifies your quote actually
  appears in it; a missing/contradicted quote downgrades the item direct→
  indirect. **The quote must also carry the conclusion's numbers**: a
  conclusion claiming "30 秒" whose quotes all say "60 seconds" trips
  MISLEADING_QUOTE — the citation exists but does not support the claim.
  `content_supports: supported|unsupported|partial` is your attestation that
  you read the content AND it supports the claim — writing `unsupported`
  auto-injects contradicting counter-evidence. An anchor you never resolved
  is not an anchor.
- `evidence[].group` — independence group. Two items from the same tool/run/
  repo are one group. **The script additionally collapses lines that share a
  URL host, near-identical quotes (Jaccard ≥ 0.7), a declared group, or cite
  each other's anchors** — syndicated reposts are one source, not N
  (CORRELATED_EVIDENCE; 100 reposts of one wire story = 1 line). Two items
  genuinely independent on the same host may attest
  `same_host_independent: true` on both.
- `evidence[].as_of` / top-level `claim_time` — provenance dates. Evidence
  valid `until` a date before the claim, or a recency-marked "当前/最新"
  claim resting on evidence older than `freshness_days` (default 365), is
  demoted to indirect (TEMPORAL_STALE / TEMPORAL_SUPERSEDED). Historical
  claims with `claim_time` are judged against period evidence — old ≠ wrong.
- `evidence[].source_tier` — `primary | secondary | aggregator | unknown`.
  Aggregators/repost mills support a scoped "据转载报道" claim at L2 but never
  count as an independent verification line.
- `evidence[].verified_by` — `"self" | "tool:NAME" | "agent:ID"`: who
  mechanically verified this line. A `tool:` attribution counts as a
  heterogeneous hard channel (deterministic tools share no LLM prior).
- `generator` + `independent_checks[]` — for high/extreme verified claims,
  the generator's family and each independent check's `by` model are
  compared: a same-family check is flagged SAME_MODEL_VERIFIER and does NOT
  satisfy cross-family verification. Valid heterogeneous checks:
  cross-family model agreeing in `context: isolated`, or tool-verified lines.
- `claim_class` + `verification.channel` — `code_behavior | config | data |
  math` claims asserted at `verified`+ require a mechanical channel
  (`execution | test | assertion | formal_proof | statistical`); reasoning/
  reading is voided as a verification channel (CHANNEL_MISMATCH → REJECT).
- `verification` — `executed` only if you actually ran something;
  `env_independent: false` when the environment could be contaminated
  (golden patch baked in, cache shared with dev, etc.); `validates_target:
  false/unknown` when tests pass but you haven't confirmed they cover the
  claimed problem.
- `counter_evidence[].status` — `unaddressed | explained | refuted`.
  `contradicts: true` for direct contradictions (a counter-example, an
  official doc saying otherwise).
- `counter_search_context` — `isolated` (falsifiers derived before
  re-examining support, searched in a fresh context) or `same` (searched
  where the conclusion was already in view). Strong claims (cross_verified,
  absolutes) or empty counters with high/extreme risk REQUIRE isolated
  search; `same` → VERIFY_REQUIRED.
- `evidence_obtainable` + `unobtainable_reason` — `yes | no | unknown`.
  `no` means the evidence needed to settle the claim does not exist or is
  not accessible (closed system, unreproducible event, data you cannot
  touch). Then the decision is ABSTAIN, not a hedged guess — and record WHY
  it is unobtainable: `no_access | nonexistent | unreproducible |
  undecidable`, so refusals are auditable and classifiable, not a shrug.
- `generalization` — set it whenever you infer from a sample to a population.

**Fill the input as a skeptical reviewer would, not as the claim's author.**
The script mechanically verifies what it can (quote-in-file, absolute-wording
scan, works-claims, strength arithmetic) and turns the rest into explicit,
reviewable attestation — but you can still write a fabricated quote for a
real file you never opened, or `content_supports: supported` without reading.
The gate's value is that the lie becomes explicit and auditable, and the
calibration loop catches systematically over-optimistic attestation later.

## When actual verification (execution) is required

Reading, reasoning, and analysis never rise above L2. You must have
**executed something and observed the result** whenever the claim is:

- any **works/viability claim** ("可以正常运行", "已修复", "won't break")
  asserted at `likely` or above;
- any **causal claim** ("A 导致 B") asserted at `judged` or above;
- an **EXPERIMENT_RESULT** (that's what the type means);
- `verified`/`cross_verified` at any strength — FAKE_VERIFICATION rejects
  these claims without valid execution;
- **high/extreme risk** topics asserted at `judged`+ (benchmarks, data
  quality, environment cleanliness, estimates, acceptance);
- **any works claim at all** right before an irreversible action
  (`--gate-point pre-action`).

If execution is genuinely impossible right now, the wording ceiling drops
to L2 — "根据代码分析判断，尚未实际运行" — or, if the settling evidence
cannot be obtained at all, ABSTAIN.

## Evidence levels → allowed wording

| Level | Meaning | You may say |
|-------|---------|-------------|
| L0 | nothing (guess, memory, "should work") | 假设/推测 (hypothesis only) |
| L1 | indirect signals (logs, time correlation, small samples) | 可能/初步判断 (possibly) |
| L2 | direct evidence with trace anchor (docs, source, config, data) | 根据现有证据可以判断 (judged) |
| L3 | actually executed and observed (ran it, tested it) | 已通过实际验证 (verified) |
| L4 | ≥2 INDEPENDENT lines (after same-origin collapse) agree AND at least one is a hard channel (quote-checked / tool-verified / valid agreeing cross-family check). Isolated counter-search and cross-family verification are decision requirements on strong claims, not level arithmetic | 已交叉验证 (cross-verified) |

Forbidden escalations: L0→any assertion, L1→absolute claims, L2→"已验证",
L3→"已交叉验证" on attestation alone (≥2 lines that nobody mechanically
checked cap at L3 — ATTESTED_ONLY_LINES: "there is evidence" ≠ "the evidence
was examined").
Details and examples: `references/evidence-levels.md`.

## Decisions and what they obligate

| Decision | Meaning | Your obligation |
|----------|---------|-----------------|
| PASS | evidence supports the claim | output at allowed wording |
| PASS_WITH_CAVEAT | output allowed, bounded | include every listed caveat verbatim in spirit |
| VERIFY_REQUIRED | evidence insufficient | do the listed actions OR downgrade wording and rerun the gate; never output the original claim as-is |
| ABSTAIN | the evidence needed cannot be obtained (`evidence_obtainable: no`) | say 目前无法确认 and state exactly what's missing and why it can't be obtained; do not output a hedged version of the claim — a hedge implies you could know |
| REJECT | claim as stated cannot stand | restate at allowed wording (scoped, hedged) or drop it; do not shop for friendlier wording |

Exit codes (script): 0 pass · 10 verify-required · 15 abstain · 20 reject · 2 input error.

## Reading the output

Human-readable mode prints one structured block; `--json` prints the same
fields as an object:

```
Evidence Gate Result
  Conclusion: / Type: / Claimed strength (+risk)
  Evidence Level: L0–L4        (claim requires L?; independent lines: N
                               — AFTER same-origin collapse)
  Evidence:                    per item, with the anchor three-stage verdict:
                               [direct·mech✓] quote verified in anchor
                               [direct·attested] content attested (logged)
                               [direct·trace-only] anchor not checkable here
                               [indirect*] downgraded (no anchor / quote absent
                               / temporally stale / misleading figure)
  Findings:                    ABSOLUTE_WORDING, FAKE_VERIFICATION,
                               SAMPLE_TO_POPULATION, ANCHOR_QUOTE_MISSING,
                               MISLEADING_QUOTE, CORRELATED_EVIDENCE,
                               TEMPORAL_STALE, SAME_MODEL_VERIFIER,
                               ATTESTED_ONLY_LINES, CHANNEL_MISMATCH, ...
  Decision: (exit code)        ← the verdict you must obey
  Reason:                      why — includes every finding
  Allowed wording:             the ceiling for this evidence level
  Calibration:                 levels are ordinal, not probabilities
  Mandatory caveats:           must appear in your output (CAVEAT decisions)
  Required actions:            what unblocks the claim (VERIFY decisions)
  Verifier:                    who decided (protocol/version, channel,
                               cross-family status)
  Unobtainable:                why, when ABSTAIN (no_access/nonexistent/...)
```

The full per-line **ledger** (anchor, channel, source tier, as_of,
collapsed_with) is in `--json` output under `ledger` — the replayable audit
trail.

The two lines that change your behavior are **Decision** and **Allowed
wording**; Findings is the review trail; Required actions is your TODO.

## Combining with other skills

- **Debugging skills**: a root-cause conclusion is type INFERENCE — the
  gate enforces "初步判断" vs "已验证", so the rollback/repro experiment
  happens before L3 wording.
- **Verification-before-completion skills**: the gate is their executor —
  it provides the structured evidence record and the mechanical verdict.
- **Report/delivery flows**: attach the Evidence Gate Result to each key
  conclusion; a conclusion without one is treated as ungated.
- **CI / automation**: exit codes are pipeline assertions (0/10/15/20);
  `--no-log` for ephemeral runs, `--log` per project.

## Audit log and calibration

Every gate run is appended (JSONL) to `.evidence-gate-log.jsonl` in the
project root unless `--no-log`. Each entry has a `gate_id`, the decision,
and the evidence level. Later you learn whether the conclusion was actually
right, and feed it back:

```bash
python3 scripts/gate_check.py --mark-outcome <gate_id> correct|incorrect|unknown  # close the loop
python3 scripts/gate_check.py --calibration                             # per-level accuracy table
```

Use `--calibration` periodically. Self-reported evidence levels are ordinal
(L2 > L1) but their absolute mapping to "actually right" is untrustworthy
until measured — if L3 conclusions turn out right only 60% of the time, the
fix is to stop saying 已验证 at L3, and the table is the thing that tells
you. v3 calibration adds Wilson confidence intervals, monotonicity checks,
a risk-coverage curve, abstention precision/recall, and per-finding error
attribution; with ≥10 marked outcomes per level it can emit calibrated
wording caps (`--emit-overrides` → `.evidence-gate-calibration.json`), which
the gate then enforces automatically. Levels are ordinal and calibration
comes only from measured outcomes — never treat L-numbers as probabilities.
Use `--log <path>` to keep per-project logs separate.

## Fake verification — the six classics + five v3 classes

These pass casual review; the gate is built to catch them
(details: `references/failure-patterns.md`):

1. **Reasoning as verification** — "I analyzed the code, it will work" ≠
   "verified". Analysis is L2 at best. `verified` requires `executed: true`.
2. **Test-passed as problem-solved** — tests pass but never covered the bug?
   `validates_target` must be `false`/`unknown`. Reproduce first, then fix.
3. **Contaminated environment** — golden patch/reference fix baked into the
   image, shared caches, "fixed" data — results from it count as nothing:
   `env_independent: false`.
4. **Sample as population** — 100 checked rows say nothing certifying
   1,000,000. Use the `generalization` field; without statistical basis the
   universal claim is REJECTed.
5. **Citation as support** — a real link that exists is not the same as a
   link that supports the claim. In real agent citations roughly half don't
   support what they're attached to. The anchor/quote/content_supports
   three-stage check exists for exactly this; a quote that isn't in the file
   downgrades the evidence. And a sibling failure: **verification gaming** —
   choosing the cheapest thing that passes (trivial tests, a check you know
   will succeed) instead of the check the claim needs. Verify what would
   FALSIFY the claim, not what would decorate it.
6. **One-sided evidence search (same-context trap)** — hunting only for
   support, or searching for disproof while the conclusion sits in your
   context. Agreement bias survives extra compute; strong claims need the
   isolated two-step counter-search (`counter_search_context: "isolated"`).

The v3 upgrade adds five classes that defeated the v2 gate in A/B testing
(all six adversarial attacks passed v2 at 100%; v3 blocks all with zero
false rejects — `benchmark/AB-RESULTS.md`):

7. **Misleading quote** — the quote is real, the anchor is real, but the
   numbers disagree: conclusion says 30s, quote says 60s. Existence of the
   citation is checked against what it actually carries (MISLEADING_QUOTE).
8. **Correlated "independent" sources** — two articles, same host: one wire
   story reposted. Independence is computed, not asserted — same-host /
   near-duplicate-quote / shared-group lines collapse before counting
   (CORRELATED_EVIDENCE).
9. **Stale evidence for current claims** — a 2024 snapshot supporting
   "当前版本…" is demoted; historical claims pinned with `claim_time` pass on
   the same snapshot. Old is not wrong — but it is not *current* either
   (TEMPORAL_STALE / TEMPORAL_SUPERSEDED).
10. **Self-family "independent check"** — glm verifying glm. Same-family
   agreement is correlated failure (models share priors and errors: 60%
   same-error agreement in ICML25 measurements); cross-family model or
   deterministic tool, or no L4 (SAME_MODEL_VERIFIER).
11. **Channel mismatch** — "verified" code behavior reached by reading and
    reasoning about the code. Machine-checkable claims need machine channels;
    prose about code is argument, not verification (CHANNEL_MISMATCH →
    REJECT). Plus its quiet sibling: **attested-only L4** — every URL
    "supports" and nobody fetched anything; ≥2 attested lines without one
    mechanical check cap at L3 (ATTESTED_ONLY_LINES).

## Rationalizations — all rejected

| Excuse | Reality |
|--------|---------|
| "I read the code carefully, it works" | Reading is L2. `verified` means executed. |
| "Tests pass, so it's fixed" | Were the tests failing before the fix? If you didn't check, `validates_target: unknown`. |
| "The env is probably clean" | Probably ≠ verified. `env_independent` stays `unknown` until shown clean. |
| "The sample is random, that's statistical" | Random ≠ sufficient size + method. `statistical_basis` needs a real sampling plan. |
| "Everyone knows this API does X" | Everyone-knows is `memory` → L0. Find the doc. |
| "It's urgent / user wants a yes" | Urgency changes wording, not evidence. Say what is verified vs not. |
| "I already verified this earlier" | Then rerunning the gate is cheap. Evidence unchanged → same result. |
| "I looked for counter-evidence and found none" | Where did you look? If the conclusion was in view while you searched, that's `same` context — agreement bias ate your search. `cross_verified` demands isolated. |
| "I ran a check and it passed" | Did the check have teeth? A trivially-passing test proves nothing. Verify what would falsify the claim. |
| "I have the doc link right here" | Link resolves ≠ link supports. Quote the line that supports you. |
| "Two sources say so, cross-verified" | Same host? Same wire story? Near-identical text? The script collapses correlated lines before counting — reposts are 1 source, not N. |
| "The independent check agreed" | Which model ran it? Same family as the generator = correlated failure, not verification. Cross-family or tool, or no L4. |
| "The doc says 60s, I said 30s, close enough" | The quote must carry the conclusion's numbers. "Exists" ≠ "supports" — MISLEADING_QUOTE. |
| "I checked the docs, it's still true" | When were the docs written? A recency-marked claim on evidence older than the freshness window is stale — re-fetch or drop "当前". |
| "The model double-checked itself and confirmed" | Self-agreement is the cheapest agreement there is. Agreement routes; it never decides. |
| "I verified the code by reading it very carefully" | Machine-checkable claim, prose channel — CHANNEL_MISMATCH. Run the test. |

**Red flags — stop and rerun the gate:** you wrote "应该/probably" in the draft
but plan to say "确定"; the word 已验证/verified appears with no command
output behind it; all evidence comes from one run/tool; the counter-evidence
list is empty because you didn't look.

## References (read on demand)

- `references/evidence-levels.md` — full L0–L4 definitions (v3: L4 needs
  post-collapse independence + a hard channel), wording rules, worked
  level-assessment examples.
- `references/decision-rules.md` — exact decision matrix the script
  implements, type-specific standards, edge cases, v2 rules (anchor check,
  ABSTAIN, isolated counter-search, pre-action mode, exit codes) and v3
  rules (misleading-quote figures, correlation collapse, temporal validity,
  same-model verifier, attested-only cap, channel routing, abstention
  taxonomy).
- `references/failure-patterns.md` — the fake-verification patterns in
  depth (six classics + five v3 attack classes) + real-world
  countermeasures.
- `references/risk-tiers.md` — which claims are high/extreme risk and what
  verification depth each tier requires (benchmark, data quality, docker
  cleanliness, estimates, schedule, acceptance...), with the v3 cost ladder
  (cheap check → evidence check → independent check → heterogeneous/
  external/formal) and claim-class routing.
- `examples/` — worked examples with real gate inputs and outputs, every
  decision class, including the v3 mechanisms.
- `docs/research-survey.md` + `docs/research-survey-2.md` — the 2024–2026
  research this design was rebuilt against, with verified citations; the
  second round covers correlation, heterogeneity, temporal validity,
  abstention and calibration, and corrects two errors in the first.
- `benchmark/AB-RESULTS.md` — the 1.0-vs-2.0 A/B: adversarial FAR 100% → 0%
  at FRR 0, core suite unchanged (full backward compatibility).
- `tests/` (project root, if present) — 26 runnable regression cases
  (incl. paraphrase-invariance: semantically equivalent rewrites must not
  flip decisions): `python3 tests/run_tests.py --report`.
