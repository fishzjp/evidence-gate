# Risk Tiers — verification depth vs. cost

Not everything deserves the same scrutiny. Tier the conclusion, then spend
verification effort accordingly. The point is *calibration*: cheap checks
for cheap mistakes, real verification for expensive ones.

## Tier definitions

| Tier | Definition | Required depth |
|------|-----------|----------------|
| low | wrong claim is easily caught later, costs little | mental check against the wording table; gate optional |
| medium | wrong claim misleads decisions or wastes someone's time | gate script + counter-evidence question |
| high | wrong claim causes bad decisions, rework, or false assurance | gate + active counter-evidence hunt + actual verification for any claim ≥ judged |
| extreme | wrong claim is contractual/production/security-critical, or hard to reverse | everything + independent second line (L4) for strong claims |

## The verification cost ladder (v3)

Risk buys verification depth — and depth is spent on the *right channel*,
not on more of the same channel. The ladder (risk-based routing, per
FIRE/ABC cascades: escalate only when the cheap rung fails to settle it):

| Rung | Cost | What runs | When (tier × claim) |
|------|------|-----------|---------------------|
| 1. Cheap check | ~free | wording-table / level arithmetic; anchor+quote mechanical check | low tier, any claim; every tier's first pass |
| 2. Evidence check | one command | resolve the anchor, read the content, quote the supporting line; figure consistency; temporal validity | medium tier; rung-1 leftovers |
| 3. Actual verification | minutes | execute it: run the test/benchmark/command in a clean env; `--gate-point pre-action` for irreversible actions | high tier ≥ judged; any works/causal claim; EXPERIMENT_RESULT |
| 4. Independent verification | one extra session | isolated counter-search + cross-family model check or deterministic tool re-derivation | high/extreme ≥ verified; extreme ≥ judged |
| 5. Multi-model / external / formal | budget | ≥2 cross-family verifiers with aggregation rules; external oracle (CI, authority, spec); formal proof for decidable classes | extreme ≥ verified; any formalizable high-stakes claim |

Rung 5 rules: agreement routes, never decides — cross-family disagreement
blocks; agreement only releases. For finite populations prefer census; for
machine-checkable classes (below) rung 3+ must be mechanical regardless of
how cheap prose is.

## Claim-class routing (v3: channel must match the claim)

| claim_class | Machine-checkable? | Required channel for `verified`+ |
|-------------|--------------------|----------------------------------|
| `code_behavior` / `config` / `data` / `math` | yes | any of `execution` / `test` / `assertion` / `formal_proof` / `statistical` — one uniform set for all four classes |
| (default / behavioral / reporting) | no | any — language reasoning allowed at its level |

Reasoning/reading is a legitimate channel for non-mechanical claims — but
for machine-checkable ones it is voided (CHANNEL_MISMATCH → REJECT): what a
machine can decide must not be settled by eloquence. Set `claim_class` and
`verification.channel` whenever the conclusion is about code behavior,
configuration, data, or mathematics.

## High-risk conclusion topics (never language-reasoning only)

Data quality / dedup judgments · benchmark validity · model consistency /
official-model checks · data authenticity · Docker/environment cleanliness ·
golden-patch contamination · test coverage of the actual problem · cost /
scale / quantity estimates · schedule feasibility · technical feasibility ·
customer acceptance · anything with 100% / 全部 / 一定 / 完全.

These auto-escalate in the script (keywords) — but keywords are a floor, not
a ceiling: tier up on your own judgment whenever being wrong is expensive.

## Pre-action escalation (G3, v2)

The tier above applies to conclusions. The same math applies to *actions*:
deploy, delete, send, merge, purchase, ticket-close are the moments where a
wrong claim converts into damage with no take-back. Run the gate with
`--gate-point pre-action` for the claim embedded in the action ("现在直接
apply，服务不会中断"). Effects: low/medium risk is escalated to high
(high/extreme stay as filed); any works/won't-break claim requires actual
execution (works_floor drops to `possibly`) — reading the config is never
enough. Abstention research (AgentAbstain, 2025) shows this is where agents
fail: a model that answers 59.5% of risky questions it shouldn't touch at
all. The irreversible-action gate is the mechanism that catches those
before the harm, not after.

## Per-tier playbook

**low** — Is the wording within the level table? Done. Don't gate "the
config file has 12 lines" when you can see it.

**medium** — Run the gate. One counter-evidence question ("what would
disprove this?"). If VERIFY_REQUIRED and the check is a single command away,
just run the check.

**high** — Verify-first applies literally: before asserting ≥ judged, you
should have *executed* something. Counter-evidence hunt is mandatory and
recorded. Check version/environment/configuration boundaries explicitly —
"works on my machine" is L3 for *your* machine only, scope it.

**extreme** — Two independent lines with different failure modes (static
audit + dynamic run; own tool + independent tool; local + CI), at least one
mechanically verified, and heterogeneity actually checked: the independent
line must not be the generator's own family re-reading its own output
(cross-family model or deterministic tool). For finite populations, prefer
census over sample. Write down what would change the answer (dependencies,
versions) as explicit caveats.

## Anti-overblocking rules (equally binding)

The gate exists to calibrate, not to silence:

1. **Don't re-verify what's verified.** A conclusion that passed at L3+ in
   this session stays passed while its evidence is unchanged. Rerunning is
   for changed evidence, not for nerves.
2. **"Cannot 100% confirm" is not "insufficient evidence".** If L1–L2
   evidence supports a preliminary judgment, *make it* — with alternatives
   named. Blocking legitimate judgment is a gate failure mode too.
3. **Simple facts get simple checks.** Demanding L4 for "this file exists"
   is waste. The wording table, not anxiety, sets the bar.
4. **Hedged intermediate reasoning is not gated.** "I'm assuming X for now,
   will verify before final" — assumption labeled, no gate needed *yet*.
   Gate it when it graduates into the final output.
5. **Cost-benefit is explicit.** If the required verification is genuinely
   disproportionate (cost, risk of running it) and the user accepts the
   uncertainty, output at the allowed lower wording with the gap named —
   that's the gate working, not being bypassed. What's never OK is silently
   claiming the higher rung.

## Verification budget (spend where it pays)

Over-verification is a real failure mode (agents re-checking resolved facts
burn time and erode trust). Allocation heuristics:

- Budget follows **tier × claim strength**, not nervousness. Low tier +
  hedged claim = zero extra spend.
- **The log is the cache.** A conclusion gated at L3+ this session with
  unchanged evidence is settled — rerun only what changed.
- **One good falsifier beats three confirmations.** Spend the marginal
  action on the isolated counter-search, not on a third supporting doc.
- **Escalate the check, not the doubt.** When VERIFY_REQUIRED fires, the
  listed action is usually one command; run it instead of re-weighting the
  existing evidence again.
