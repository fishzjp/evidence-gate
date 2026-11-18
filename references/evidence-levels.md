# Evidence Levels (L0–L4)

The single scale used to rate every conclusion's support. The gate script
derives the level mechanically from your input; this file explains how to
classify evidence items so the derivation is honest.

## The scale

| Level | Name | What qualifies | Allowed wording |
|-------|------|----------------|-----------------|
| L0 | Unsupported | Guesses, common sense, "experience", model memory, intuition | 假设/推测 (hypothesis only) — never as fact |
| L1 | Indirect evidence | Log symptoms, time correlation, small samples, second-hand observation | 可能/初步判断 (possibly / preliminary) |
| L2 | Direct evidence | Official docs, source code, config, data, logs, test artifacts — each with a trace anchor **whose content was actually checked against the claim** (quote verified, or content attested) | 根据现有证据可以判断 (judged from evidence) |
| L3 | Experimental verification | You executed something and observed the result: ran code, started the container, called the API, ran the benchmark/test | 已通过实际验证 (verified) |
| L4 | Independent cross validation | ≥2 independent evidence lines (different tool/method/environment) agree, **and** the counter-evidence search ran isolated (falsifiers derived before re-examining the support) | 已交叉验证 (cross-verified) |

## Classification guide per evidence kind

**Direct kinds (need a trace anchor or they downgrade to L1):**

- `official_doc` — vendor docs, specs, RFCs, changelogs. Anchor = URL +
  section. A doc you "remember" is `memory`, not `official_doc`.
- `source_code` — the code itself, local or in dependencies. Anchor = path +
  line. Reading the actual `node_modules` beats recalling the README.
- `config` — the live config file, not your intended edit. Anchor = path.
- `data` — query results, exports, diffs. Anchor = file or query.
- `log` — actual log lines with timestamps/source. Anchor = log path or
  pasted lines with enough context to be found again.
- `test_result` — output of a test run. Anchor = run id / CI link. Passing
  is L2 evidence *that the tests passed*; whether that verifies your claim
  is the `validates_target` question.
- `sample` — you inspected part of the population. Direct evidence about
  the sample; claims about the whole go through `generalization`.

**Indirect kinds (cap at L1 by themselves):**

- `observation` — behavior seen but not captured ("the page felt slow").
- `time_correlation` — B happened after A. Never causation by itself.
- `memory` — yours or a teammate's recollection; model knowledge. L0.
- `assumption` — things you're taking as given. L0. Make them explicit;
  assumptions unlisted are where reports go to die.
- `anecdote` — one-off stories, "worked on my machine".

## How the script derives the level

```
L = max over:
  1  any indirect item
  2  any direct item WITH trace anchor  (downgraded to 1 if the anchor's
     content fails the check: quote not in file / anchor missing /
     content attested as unsupported)
  3  valid execution  (executed AND env_independent AND validates_target)
  4  ≥2 distinct direct groups  (only claimable with isolated counter-search)
```

Groups = independence lines. Two entries from the same run, same tool, or
same repo belong in ONE group. `docs + source + own-run` is 3 groups → L4.
`doc A + doc A's tutorial` is 1 group. When unsure whether two sources are
independent, ask: *if source 1 were wrong, would source 2 still stand?*

**Why the anchor content check exists:** field research on agent citations
found roughly half of real, resolvable citations do not actually support the
claim they're attached to (see `docs/research-survey.md`). An anchor proves the
source exists; only reading it proves it helps you. A direct item whose
content was never opened (no quote, no attestation) counts as unresolved for
strong claims.

**Why L4 requires isolated counter-search:** same-context counter-search —
looking for disproof while the conclusion sits in your context — is
measurably worse at surfacing counter-evidence, and agreement bias survives
extra compute (SGV, ICLR 2026). `cross_verified` is only claimable after
deriving falsifiers fresh, then searching.

## Wording discipline

The mapping is a ceiling, not a target:

- L1 + "初步判断 A 是主要原因" → allowed, provided alternatives are named.
- L2 + "已验证" → forbidden. L2 never uses verified language.
- L3 + "已验证" → allowed, scoped to what you ran: "在测试环境跑通并复测通过".
- Absolute wording (100%/全部/一定/完全) is not reachable by pumping up
  confidence — it needs L4 AND scope ("这 20 个用例全部…" not "全部用例").

**"Cannot 100% confirm" ≠ "insufficient evidence".** If evidence genuinely
supports a preliminary judgment, make it — hedging into silence is as wrong
as overclaiming. The gate blocks overclaiming, not judgment.

## Common misclassifications

| Reality | Wrong call | Right call |
|---------|-----------|------------|
| "I remember the docs say X" | `official_doc` (L2) | `memory` (L0) |
| Read the fix diff, tests were run by CI yesterday by someone else | `test_result` | `source_code` only; the CI run isn't yours to claim |
| Sampled 100 rows, all clean → "data is clean" | direct `data` | `sample` + `generalization` |
| Ran the app once, looked fine | L3 "verified" | L3 only if `validates_target` — did it exercise the claimed behavior? |
| Docs say X; I also believe X | 2 sources, L4 | 1 source — belief is not a second line |
| Link exists and loads | content checked | existence ≠ support — quote the supporting line or attest content |
| Found a second source that copied the first | 2 groups, L4 | 1 group — independence asks: if source 1 were wrong, would source 2 still stand? |
| Counters searched in the same context that holds the conclusion | isolated search | `same` context → no L4, no cross_verified |
