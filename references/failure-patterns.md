# Failure Patterns — fake verification & one-sided evidence

The classic fake-verification patterns, how to detect each while filling
the gate input, and the countermeasure. These matter because they *look*
like verification — that's what makes them dangerous.

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
only-partially-supporting medical citations; see `docs/research-survey.md`).
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

## Why agents rationalize these (and why the gate doesn't care)

Under deadline/authority/sunk-cost pressure, each pattern has a soothing
story: "the diff is obviously correct", "green means green", "the harness
built it, not my problem", "the sample was random", "I cited my sources".
The gate's answer to all of them is structural: those stories live in
*fields* (`executed`, `validates_target`, `env_independent`,
`statistical_basis`, `quote`, `content_supports`, `counter_search_context`)
that you must fill before the decision is computed — the quote and
absolute-wording checks run mechanically on artifacts, not on your word —
and the fill happens while you are calm, not while you are rushing the last
paragraph of the report.
