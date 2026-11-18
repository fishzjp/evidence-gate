---
name: evidence-gate
version: 2.0.0
description: Use when about to state or deliver any key conclusion — facts, causal explanations, verification/success claims ("verified", "fixed", "it works"), data-quality or benchmark judgments, environment-cleanliness claims, estimates, or absolute statements (100%, 全部, 一定, guaranteed) — and before closing tickets, sending final reports, or executing irreversible actions (deploy, delete, send, merge, purchase). Also use when evidence looks thin, one-sided, or comes only from code reading/memory, when tests pass but coverage is unclear, when a citation might not actually support the claim, or when verification ran in a possibly contaminated environment.
---

# Evidence Gate

A conclusion quality gate that runs **before** key conclusions reach the user.
It does not make you more careful with words — it mechanically prevents
conclusion strength from exceeding evidence strength.

**Core rules:**

1. **Verify first, conclude second.** If a tool, test, or command can check
   the claim, run it before asserting anything about it.
2. **Conclusion strength ≤ evidence strength.** Always, mechanically, via
   `scripts/gate_check.py`.
3. **Cannot confirm → say so.** "目前无法确认" is a valid answer; an
   unverified-but-plausible claim presented as fact is not.

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
               | RECOMMENDATION | EXPERIMENT_RESULT
2. VERIFY FIRST  If a tool/run/test can check it → run it NOW, don't reason on.
               能执行就执行，能查询就查询，能读源码就读源码，能查数据就查数据.
3. COLLECT     List evidence items with anchors. For any doc/URL claim, the
               check is three-stage: (a) anchor resolves, (b) you actually
               read the content, (c) a quoted line from it supports the
               claim. "The citation exists" ≠ "the citation supports it" —
               half of real citations don't (see docs/research-survey.md). For
               local files give anchor + quote; the script verifies the
               quote mechanically.
4. FALSIFY     Two-step ISOLATED counter-search (SGV pattern): first write
               what evidence would falsify the conclusion and where it would
               live — WITHOUT looking at your supporting evidence again —
               then go search those places. Same-context counter-search
               (asking in the context that already contains your conclusion)
               measurably fails to surface counter-evidence: agreement bias
               survives extra compute. To claim cross_verified you must set
               counter_search_context: "isolated".
5. GATE        Run the script with the input below. Read the decision.
6. OBEY        Follow the decision exactly, including caveats and wording.
```

**Step 4 questions** (answer them in the input, not just in your head):
如果结论是错的，最可能是什么？有没有证据能推翻它？有没有第二种解释？
有没有遗漏的前提、边界条件、版本/环境/配置差异？有没有反例？
Only-searching-for-support is the failure mode; the input schema forces the
counter-evidence field to exist, even if the list is empty.

**Pre-action gate (G3):** about to execute something irreversible — deploy,
delete, send, merge, purchase, close a ticket? Run the gate with
`--gate-point pre-action`. In that mode risk escalates one tier, any "works /
won't break" claim requires actual execution, and the default decision is
VERIFY_REQUIRED, not PASS_WITH_CAVEAT. Concluding too late is the same as not
concluding: a wrong claim that slips out in the deploy message does its damage
even if the next gate would have caught it.

## Gate input

Write the JSON to a temp file (or stdin), then run:

```bash
python3 scripts/gate_check.py gate-input.json     # human-readable
... | python3 scripts/gate_check.py --json -      # machine-readable
... | python3 scripts/gate_check.py --json --gate-point pre-action -
```

```json
{
  "conclusion": "the exact conclusion you are about to output",
  "type": "FACT",
  "claimed_strength": "judged",
  "risk_tier": "medium",
  "evidence": [
    {"kind": "official_doc", "detail": "what it says + why it matters",
     "anchor": "https://... or tests/fixtures/foo.md", "quote": "exact line",
     "content_supports": "supported"},
    {"kind": "source_code", "detail": "src/foo.py:123 — ...", "group": "code"}
  ],
  "verification": {"executed": false, "detail": "",
                   "env_independent": "unknown", "validates_target": "unknown"},
  "counter_evidence": [
    {"detail": "...", "status": "unaddressed", "contradicts": true}
  ],
  "counter_search_context": "isolated",
  "evidence_obtainable": "yes",
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
  indirect. `content_supports: supported|unsupported|partial` is your
  attestation that you read the content AND it supports the claim — writing
  `unsupported` auto-injects contradicting counter-evidence. An anchor you
  never resolved is not an anchor.
- `evidence[].group` — independence group. Two items from the same tool/run/
  repo are one group. L4 needs ≥2 direct groups.
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
- `evidence_obtainable` — `yes | no | unknown`. `no` means the evidence
  needed to settle the claim does not exist or is not accessible (closed
  system, unreproducible event, data you cannot touch). Then the decision is
  ABSTAIN, not a hedged guess.
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
| L4 | ≥2 independent evidence lines agree, counter-search run isolated | 已交叉验证 (cross-verified) |

Forbidden escalations: L0→any assertion, L1→absolute claims, L2→"已验证".
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
  Evidence Level: L0–L4        (claim requires L?)
  Evidence:                    per item, with the anchor three-stage verdict:
                               [direct·mech✓] quote verified in anchor
                               [direct·attested] content attested (logged)
                               [direct·trace-only] anchor not checkable here
                               [indirect*] downgraded (no anchor / quote absent)
  Findings:                    ABSOLUTE_WORDING, FAKE_VERIFICATION,
                               SAMPLE_TO_POPULATION, ANCHOR_QUOTE_MISSING, ...
  Decision: (exit code)        ← the verdict you must obey
  Reason:                      why — includes every finding
  Allowed wording:             the ceiling for this evidence level
  Mandatory caveats:           must appear in your output (CAVEAT decisions)
  Required actions:            what unblocks the claim (VERIFY decisions)
  Verifier:                    who decided (protocol/version, channel)
```

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
python3 scripts/gate_check.py --mark-outcome <gate_id> correct|wrong   # close the loop
python3 scripts/gate_check.py --calibration                             # per-level accuracy table
```

Use `--calibration` periodically. Self-reported evidence levels are ordinal
(L2 > L1) but their absolute mapping to "actually right" is untrustworthy
until measured — if L3 conclusions turn out right only 60% of the time, the
fix is to stop saying 已验证 at L3, and the table is the thing that tells
you. Use `--log <path>` to keep per-project logs separate.

## Fake verification — the five classics

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

**Red flags — stop and rerun the gate:** you wrote "应该/probably" in the draft
but plan to say "确定"; the word 已验证/verified appears with no command
output behind it; all evidence comes from one run/tool; the counter-evidence
list is empty because you didn't look.

## References (read on demand)

- `references/evidence-levels.md` — full L0–L4 definitions, wording rules,
  worked level-assessment examples.
- `references/decision-rules.md` — exact decision matrix the script
  implements, type-specific standards, edge cases, v2 rules (anchor check,
  ABSTAIN, isolated counter-search, pre-action mode, exit codes).
- `references/failure-patterns.md` — the five fake-verification patterns in
  depth + real-world countermeasures.
- `references/risk-tiers.md` — which claims are high/extreme risk and what
  verification depth each tier requires (benchmark, data quality, docker
  cleanliness, estimates, schedule, acceptance...).
- `examples/` — ten worked examples with real gate inputs and outputs,
  every decision class.
- `docs/research-survey.md` — the 2024–2026 research this design
  was rebuilt against, with verified citations.
- `tests/` (project root, if present) — 14 runnable regression cases:
  `python3 tests/run_tests.py --report`.
