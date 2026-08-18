# Research grounding — verification gates, abstention, and the identity line

**Study-swarm, 2026-08-17, armature advisor seat.** Fired on the Director's ruling that the
atom / identity distinction holds, which unlocked a pixel-gate path this studio had never
inventoried. Four parallel research agents; findings gated through an external citation
verifier before anything below became load-bearing.

## ⚑ Verification status — read this before trusting any finding

Every citation ran through `prism verify --type citations`, caller family `anthropic`,
verifier `mistral-small:24b` via local Ollama — a **different model family from the seat that
commissioned the research**, with the commissioning reasoning stripped.

**Result: 21 citations, all 21 existence-`resolved`, 14 `supported`, 7 `not_addressed`,
0 `contradicted`, 0 fabricated.**

- **`supported` (14) — load-bearing.** The oracle resolved the identifier and the verifier
  found the claim supported at source.
- **`not_addressed` (7) — existence-verified, groundedness-UNVERIFIED.** The oracle reads
  title + abstract only, so a figure living in a results table reads as unaddressed. This is
  documented runner behaviour, **not** evidence the finding is wrong — and equally **not**
  evidence it is right. Marked per finding below. Read at source before building on one.
- **`contradicted` — none.** This is the halt condition and it did not fire.

**Three instrument defects were found by running the instrument, and they matter more than any
single citation:**

1. The **first gate run exited 0 while refusing to run** (missing signing key). A verification
   tool reporting success while verifying nothing — the same defect class this whole arc is
   about. Never read a zero exit from this tool as a pass without reading its body.
2. The **second run's groundedness lens returned `provider_error: "Ollama API not reachable"`
   on all 15 lenses** while the top-level verdict read `revise` — which looks like a judgment
   about the citations. It was not. The verifier was down. **A top-level verdict here can be
   produced by an absent verifier; check `lens_results` before believing one.**
3. A **signing key already existed** and was not picked up from the environment; `prism keygen`
   minted a second one to stdout rather than reporting the first.

⚠ Also recorded: `prism` 1.6.0's CLI is known to ignore its routing registry, so the
*family-different* property holds here (anthropic caller, local verifier) but the **pinning
does not**. Do not quote this run as a pinned-verifier result.

## A. The atom / identity line — the Director's ruling, and what evidence says

**A1 · `supported`. Identity encoders mistake a palette change for identity drift.** StyleID:
A Perception-Aware Dataset and Metric for Stylization-Agnostic Facial Identity Recognition
(arXiv:2604.21689). Standard identity encoders are brittle under stylization and confuse
texture/colour change with identity drift.

> **Design implication, and it is the strongest result of this swarm.** On the same afternoon,
> independently, a build seat found `prompt-craft`'s repair router substring-matching atom ids
> against `("face", "sigil", "identity", "insignia", "palette")` and sending any match to
> identity-plate repair. A **palette** atom was being routed as a likeness miss. The literature
> and our own code produced the same confusion, and neither seat knew about the other. The
> Director's ruling held in the contract and was collapsing in the router; the router is fixed
> and pinned by test.

**A2 · `supported`. A detector that cannot find the face still returns a number.** Bringing
Cartoons to Life: Towards Improved Cartoon Face Detection and Recognition Systems
(arXiv:1804.01753). Face detectors trained on photographs often fail to fire at all on
stylized faces.

> **Implication.** armature's CLAUDE.md already says a diagnostic returning numbers on a face
> it cannot find is noise wearing a unit. That line now has a citation. Any identity diagnostic
> quoted here ships with evidence its detector actually fired.

**A3 · `not_addressed` (groundedness unverified). FaceSim-style similarity is inflated by pose
and gaze rather than identity.** Meta-LoRA (arXiv:2503.22352).

**A4 · No source found.** No paper tests the attribute-vs-identity separation as a hypothesis.
The research agent said so plainly rather than assembling one from adjacent work.

> **Implication, stated so nobody overclaims later.** The Director's ruling is a **design
> decision supported by adjacent failure evidence, not a cited empirical separation.** It does
> not need a paper to be binding. It does need us not to claim literature backing we do not
> have — the precise failure a sibling repo already committed on a public surface.

## B. The gate's exit contract

**B1 · Engineering practice, NOT gated as research.** The following are documented practice,
labelled as such by the research agent and passed through no citation gate: the Nagios plugin
API's mandatory four-way verdict (0 OK / 1 WARNING / 2 CRITICAL / **3 UNKNOWN**, where UNKNOWN
means the check could not determine status and CRITICAL is never overloaded for "could not
run"); `sysexits.h`'s `EX_UNAVAILABLE`/`EX_TEMPFAIL` split; Terraform's
`plan -detailed-exitcode` gating an irreversible `apply`; and the OCSP hard-fail/soft-fail
history, where hard-fail caused repeated real availability harm precisely because it
**conflated "could not check" with "checked and it is bad."**

> **Implication — this corrects a shipped design.** `prompt-craft`'s new exit contract puts
> `GATE_UNAVAILABLE` (could not run) and `GATE_FAIL` (ran, a required atom failed) **both on
> exit 2**. That is the OCSP conflation one level up: the original defect merged three states
> into exit 0; the fix merges two of them into exit 2. The error *codes* already distinguish
> them, so no information is lost — only the machine-readable signal a CI branch reads.
> `GATE_UNAVAILABLE` needs its own exit code.

**B2 · `supported`. Abstention is a distinct and harder skill than the underlying check.** Know
What You Don't Know: Unanswerable Questions for SQuAD (arXiv:1806.03822). A model at 86% F1
when forced to always answer fell to 66% once required to correctly abstain.

**B3 · `supported`. A component's own confidence is a poor abstention signal.** Selective
Question Answering under Domain Shift (arXiv:2006.09462). A separately trained calibrator
reached 56% coverage at 80% accuracy versus 48% for raw confidence.

> **Implication.** A tier's internal confidence must not double as the gate's overall UNCERTAIN
> signal. The roll-up needs its own logic.

**B4 · `supported`. Selective classification can guarantee a target risk by rejecting at
inference.** arXiv:1705.08500.

**B5 · `not_addressed`. Abstention is its own axis, separate from correctness.** Know Your
Limits (arXiv:2407.18418).

**B6 · `supported`. A confident output up front produces rubber-stamping.** To Trust or to
Think: Cognitive Forcing Functions Can Reduce Overreliance on AI (arXiv:2102.09692).

> **Implication.** Do not present UNCERTAIN inside a dashboard of reassuring green passes.

**B7 · Engineering practice, ungated.** The Prometheus always-firing Watchdog pattern: the
*absence* of a signal is what reveals the pipeline died.

> **Implication.** The gate should emit a positive **"N of M tiers actually executed"** count
> independent of its verdict. This swarm's own instrument failure (§⚑ item 2) is the argument:
> a verdict was produced while every lens was failing, and nothing in the headline said so.

## C. The verifier stack

**C1 · `supported`. Holistic judges drift from human judgment as models improve — up to 17.7%
absolute error; per-atom decomposition with soft aggregation is the fix.** GenEval 2:
Addressing Benchmark Drift in T2I Evaluation (arXiv:2512.16853).

> **Implication.** This directly validates the contract's atomic-claim decomposition. The
> architecture's central bet is evidenced.

**C2 · `supported`. No single metric performs consistently across compositional tasks; VQA-based
metrics are not uniformly superior to embedding-based ones.** arXiv:2509.21227.

> **Implication.** A point *for* tiering, against collapsing to one verifier.

**C3 · `supported`. CLIP's object-attribute binding failure is a training-data property, not
fixable by scaling batch size or adding hard negatives.** arXiv:2507.07985.

> **Implication.** The CLIPScore ban stands. Note the honest limit: this was measured on CLIP,
> not SigLIP2; same contrastive family, transfer plausible, **unconfirmed**.

**C4 · `not_addressed`. A single RL-trained generative verifier outperforms GPT-4o on its own
benchmark.** OmniVerifier (arXiv:2510.13804).

> **Implication, and it is a live tension.** The leading edge is trending toward one generative
> verifier, while our architecture bans generative verifiers. The ban's actual wording is that
> a generative VLM is never *its own* gate — a separate generative verifier of a different
> family may not violate it at all. That distinction has never been written down carefully and
> should be, before someone resolves it in either direction by accident.

**C5 · No source found. Absence/negation verification is an unfilled gap.** TNG-CLIP
(arXiv:2505.18434, `supported`) confirms CLIP remains limited at negation. **No source
benchmarks a sigmoid zero-shot score as a negation/absence verifier.**

> **Implication.** `prompt-craft` carries four **required** negations — `no_human_face`,
> `no_rival_colours`, `no_modern_gear`, `no_shield` — resting on a capability nobody has
> measured. A research agent also surfaced an untraceable vendor claim of 92/87/95% negation
> accuracy and **discarded it as marketing copy rather than cite it**; that discipline is
> recorded here because it is the behaviour we want.

## D. Two of our own standards are overclaimed

The swarm audited this studio's EXTERNAL_VERIFIER standard, and both findings are corrections
to us rather than to the field.

**D1 · "A generative VLM is never its own gate" — convergent inference, not a measured law.**
Supporting and `supported`: discriminative yes/no hallucination polling is markedly more stable
than open-ended generative captioning (POPE, arXiv:2305.10355); LLMs cannot reliably self-correct
without external feedback (arXiv:2310.01798); self-recognition accuracy correlates linearly with
self-preference bias strength (arXiv:2404.13076); judges are heavily moved by persuasiveness
rather than correctness (arXiv:2402.06782). `not_addressed`: vision-language models give
near-100% verbalized confidence on hallucinated content (arXiv:2405.02917).

> **No single study runs the doctrine's head-to-head** — one generative VLM against one
> discriminative model, same object-presence case, confidence compared both sides. The doctrine
> is well-grounded inference. It should stop being written as though a paper proved it.

**D2 · "Hide the generator's reasoning from the verifier" — no direct evidence located.** There
is strong mechanism evidence for why *exposure* is risky — generative judges are fooled into
false positives by reasoning-shaped, content-free tokens (arXiv:2507.08794, `not_addressed`).
But **no controlled ablation of one verifier with reasoning shown versus hidden was found.**

> **Implication.** The practice is probably right and costs nothing. It is currently justified
> by inference from adjacent findings, and the standard should say so.

## What this does not cover

Video verification beyond the identity question; control-conditioned verification (re-running
pose estimation on generated frames and diffing against the control skeleton) surfaced as a real
technique class and is **not** pursued here. Neither is logging design or path containment.
