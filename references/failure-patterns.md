# Failure Patterns — fake verification & one-sided evidence

The classic fake-verification patterns (1–6) and the v3 attack classes
(7–11) that defeated the v2 gate in A/B testing, how to detect each while
filling the gate input, and the countermeasure. These matter because they
*look* like verification — that's what makes them dangerous.

## Pattern 1 — Reasoning as verification

**Shape:** "I analyzed the code / the logic is sound / the docs imply it
works" → stated as "verified", "可以运行", "修复成功".

**Detection:** ask "what command did I run, and what did it print?" If there
is no command + output pair, `verification.executed` is `false`. Full stop.
Code review is `source_code` evidence (L2) — valuable, but it is a claim
about the code, not about the running system.

**Countermeasure:** run it. If running is genuinely impossible right now
(production risk, missing credentials), the conclusion stays at L2 wording:
"根据代码分析判断，尚未实际运行" — explicitly not verified.

## Pattern 2 — Test-passed as problem-solved

**Shape:** the fix is in, the suite is green, ticket closed — but nothing
ever showed the test failing *before* the fix. The suite may never exercise
the bug (wrong test, weakened assertion, cached result, skipped test).

**Detection:** `validates_target` is `true` only when you can answer:
- Which test covers the claimed problem, by name?
- Did it fail on the pre-fix state (reproduced)?
- Does it still assert the same thing after my change (not weakened)?

**Countermeasure:** reproduce-first workflow: write/reuse the failing test,
watch it fail, apply the fix, watch it pass. If you inherit a green suite,
`validates_target: unknown` → the script treats the execution as void for
verification purposes.

## Pattern 3 — Contaminated verification environment

**Shape:** the verification environment contains the answer, the reference
fix, or leftover state — so the check passes for the wrong reason. The
canonical case: golden patch merged before the eval image was built, so the
image tests the reference fix, not the agent's fix. Also: caches shared
between fixer and verifier, "fixed" data files, pre-built binaries, patched
validators.

**Detection:** `env_independent` is `true` only when you can answer:
- Was the environment built from the *pre-change* state plus only the change
  under test?
- Is there any path by which the expected answer could already be present?
- If I reverted the fix, would this environment still pass? (If yes — the
  environment is contaminated, not the fix working.)

**Countermeasure:** rebuild from a clean base; verify by mutation — revert
the change and confirm the check now fails. A verification that cannot fail
verifies nothing.

## Pattern 4 — Sample as population

**Shape:** spot-checked N items are fine → "all M items are fine"
(100/1,000,000 is the classic). Also: one endpoint tested → "the API works";
one browser → "the site works".

**Detection:** any sentence of the form "sampled/spot-checked X … so
all/全部/整体 Y". Fill the `generalization` block with real numbers.
`statistical_basis: true` requires an actual sampling plan (sampling method,
size justification, confidence) — "it was random" is not a plan.

**Countermeasure:** scan the full population when feasible (a 1M-row
duplicate check is a single SQL pass, seconds); otherwise state the sample
scoped: "抽查 100 条未见问题；整体未验证" and let the reader decide.

## Pattern 5 — Citation as support (anchor entailment gap)

**Shape:** the deliverable cites a real, resolvable source — URL, issue,
file — and the source exists, but its content doesn't actually support the
claim attached to it. Field research on agent citations found roughly half
of real citations don't support their claim (Stanford 2024: 51.5% of
internet citations misused; SourceCheckup 2025: 50–90% irrelevant or
only-partially-supporting medical citations).
Existence is easy to check; *support* is what nobody checks.

**Detection:** the three-stage anchor check — (1) anchor resolves, (2)
content actually read, (3) a quoted line from it entails the claim. Local
files: the script verifies your `quote` string appears in the file (markdown
formatting chars stripped). URLs: fetched when online; otherwise your
`content_supports` attestation is the channel, and it's logged. An anchor
whose quote isn't in the file downgrades the item direct→indirect — "I cited
it" becomes "an indirect pointer exists".

**Countermeasure:** never attach an anchor you haven't opened at the line
that supports you. If you can't quote the line, you don't have the support.
Sibling failure — **verification gaming**: choosing the cheapest check that
passes (a trivial test, a look-where-it's-clean search) instead of the check
the claim needs. The question is always "what would falsify this?", never
"what would make this look checked?".

## Pattern 6 — One-sided evidence search (same-context trap)

**Shape:** gathering everything that supports the conclusion and stopping —
or worse, "searching" for counter-evidence in the same context that already
holds your conclusion, where agreement bias quietly vetoes what you'd find.
Same-context self-critique measurably fails to surface counter-evidence, and
extra thinking time doesn't fix it (SGV, ICLR 2026: the bias persists
because the model's prior anchors the critique step; Huang et al., ICLR
2024: intrinsic self-verification gains vanish without external feedback).

**Detection:** an empty `counter_evidence` list you filled in ten seconds; a
counter-search that only ran where the conclusion was already in view
(`counter_search_context: "same"`). The field exists to force the search —
and now to force its *context* to be honest.

**Countermeasure:** two-step isolated search: first write down what evidence
would falsify the conclusion and where it would live, without looking at
your supporting evidence; then go search those places fresh. Filing
`counter_search_context: "isolated"` without doing this is just a prettier
lie — the calibration loop is what eventually catches it. Cheap
disconfirmation moves, in order of cost: grep for the opposite claim; check
the same artifact's failure cases; check a different version/environment;
check edge inputs (empty/zero/max/unicode); ask "what would I see if I were
wrong, and did I look there?"

## Pattern 7 — Misleading quote (figures the citation doesn't carry) — v3

**Shape:** the anchor resolves, the quote is verbatim in the file — and the
conclusion claims 30s while every quote says 60s. The citation is real; the
support is fictional. This is the anchor-entailment gap's sharp edge:
numbers are where "supports" becomes checkable.

**Detection:** mechanical, in the script: if the conclusion claims 1–3
unit-bearing figures (FACT/INFERENCE/EXPERIMENT_RESULT), no valid execution
exists, and NONE of the figures is carried by any quote, anchor text, or
evidence detail (exact match after normalizing thousand separators /
trailing zeros / full-width digits, with time-unit conversion — "0.5 分钟"
is carried by "30 seconds"), all quoted lines demote to indirect
(MISLEADING_QUOTE). Deliberately narrow — version numbers ("foo-lib 3.2")
and conditional thresholds ("若需低于 200ms") don't count as claimed
quantities; the wide rule over-blocked 5/10 honest conclusions in
prototyping, the narrow one holds FRR at 0.

**Countermeasure:** quote the line that contains YOUR number, or fix the
number in the conclusion. If the doc really does support the figure, the
line is quotable — if you can't quote it, the doc doesn't say it.

## Pattern 8 — Correlated "independent" evidence (syndication) — v3

**Shape:** "two independent reports confirm…" — two articles on the same
news host, near-identical text, one wire story reposted. Independence is
asserted by counting sources; it evaporates under provenance. 100 reposts
of one wire story are 1 source with 100 URLs.

**Detection:** mechanical collapse in the script: shared declared group,
shared registrable URL domain (unless both attest `same_host_independent`),
quote token Jaccard ≥ 0.7, or a citation chain (one item's quote OR detail
text cites another's anchor URL) merge into one independent line
(CORRELATED_EVIDENCE); `independent_lines` is post-collapse. Aggregator-tier
sources never form independent lines at all.

**Countermeasure:** for L4, find lines with different failure modes —
different origin organization, different method (static vs dynamic), or a
deterministic tool. Ask of each pair: if source 1 were wrong, would source 2
still stand? If they'd fall together, they're one line.

## Pattern 9 — Stale evidence for current claims — v3

**Shape:** "当前版本的默认超时是 60s", cited to a doc snapshot from two years
ago. The claim is about *now*; the evidence is about *then*. Correct then ≠
correct now.

**Detection:** `as_of` on every source; the script demotes evidence older
than `freshness_days` (default 365) under a recency-marked claim
(TEMPORAL_STALE), evidence expired before the claim date
(TEMPORAL_SUPERSEDED), evidence dated in the future
(FUTURE_DATED_EVIDENCE), and flags historical claims resting on evidence
dated long after their `claim_time` (TEMPORAL_ANACHRONISTIC). Historical
claims with `claim_time` are judged against period evidence — the same
snapshot that fails "当前" passes "2024 年 6 月时".

**Countermeasure:** date your evidence (`as_of`), scope your claim
(`claim_time`), and re-fetch when claiming currency. Old evidence isn't
wrong — it's evidence about a different time.

## Pattern 10 — Same-model "independent" check — v3

**Shape:** the agent "verified" its conclusion by asking itself — or a
sibling model of the same family — and reporting agreement as
cross-validation. Same-family models share priors and errors: ~60% same-
error agreement in ICML 2025 measurements, and stacking more same-family
judges buys almost nothing (9 judges ≈ 2 effective votes,
arXiv:2605.29800). Agreement between correlated verifiers is an echo, not a
confirmation.

**Detection:** `generator` vs each `independent_checks[].by` family:
same-family checks are flagged (SAME_MODEL_VERIFIER) and do not satisfy
cross-family verification; a check whose family cannot be read from its
identifier doesn't count either (VERIFIER_IDENTITY_UNKNOWN — self-reported
identity is not corroboration); a DISagreeing isolated check blocks from
any family (INDEPENDENT_DISAGREEMENT). L4 additionally needs a hard
channel — a quote-checked line, a tool-verified line
(`verified_by: "tool:NAME"`, name required), or an agreeing cross-family
check in isolated context.

**Countermeasure:** verify with a different family, or better, a
deterministic tool — tools share no LLM prior at all. Agreement routes,
never decides: cross-family disagreement blocks; agreement only releases.

## Pattern 11 — Channel mismatch & attested-only L4 — v3

**Shape (a):** "verified" reached by reading and reasoning about
machine-checkable behavior (code/config/data/math). Prose is not execution.
**Shape (b):** every URL attested "supports", nothing ever fetched, and the
conclusion ships as cross-verified — attestation all the way down.

**Detection:** `claim_class` in {code_behavior, config, data, math} claimed
at `verified`+ requires `verification.channel` in {execution, test,
assertion, formal_proof, statistical} — otherwise FAKE_VERIFICATION →
REJECT (CHANNEL_MISMATCH). ≥2 lines with no mechanical check among them cap
at L3 (ATTESTED_ONLY_LINES): "there is evidence" ≠ "the evidence was
examined".

**Countermeasure:** route the claim to a machine channel — run the test,
execute the command, assert the property, prove the theorem. What a machine
can decide must not be settled by eloquence; and for cross-verified
wording, at least one line must have been touched by something
deterministic.

## Why agents rationalize these (and why the gate doesn't care)

Under deadline/authority/sunk-cost pressure, each pattern has a soothing
story: "the diff is obviously correct", "green means green", "the harness
built it, not my problem", "the sample was random", "I cited my sources",
"two outlets reported it", "the model double-checked itself".
The gate's answer to all of them is structural: those stories live in
*fields* (`executed`, `validates_target`, `env_independent`,
`statistical_basis`, `quote`, `content_supports`, `counter_search_context`,
`as_of`, `generator`, `claim_class`, `verification.channel`, `verified_by`)
that you must fill before the decision is computed — the quote, figure,
collapse, temporal, channel and family checks run mechanically on
artifacts, not on your word — and the fill happens while you are calm, not
while you are rushing the last paragraph of the report.
