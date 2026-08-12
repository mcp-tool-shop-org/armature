# E10 — densified driving: the same dance, more in-betweens

**Seat: executor (run on Opus) · new branch `E10-density` from `main`, fresh worktree
`E:\AI\armature-E10`** · **Ceiling: ≤ 2 generations** (1 probe + 1 reserve on a named
cause); the route bills GPU-hours (`estimate_credits` re-confirmed 0 before submission);
both meters reported. **Spec written 2026-08-12 by the advisor, before the work, at the
Director's direction: densify the in-betweens with proper rotation interpolation and drive
81-frame sticks.**

## Trajectory

The Director's eye named the first shot's motion choppy. The motion is 3D and ours, so the
cheapest lever is upstream of the model: give it denser driving. This experiment measures
that one lever — it teaches whether driving density moves painted smoothness, which prices
every future shot's stick budget, and it exercises the movement-library format (a motion
record that can be resampled to any legal frame count is a library-ready asset).

## The one-variable statement (the discipline)

**Everything except driving density is pinned to the E08 probe by hash:** the same motion
record (the E09 A3 lift, EMA config unchanged), the same prompt and negative verbatim, the
same letterboxed reference (`fit_reference` output, same pad treatment), the same
unconnected sockets, the same model files, sampler values and resolution. The only deltas:
65 sticks → **81 sticks resampled over the identical time span** (~19.95 fps sampling), a
fresh pre-registered seed (a new frame count is a new generation regardless), and the
output encoded at the **matching true tempo** so the dance plays at its own speed — more
in-betweens, not slow motion. Smoothing variants, the crowd, aspect, and the reference set
are explicitly OUT — they are their own experiments.

## The commission — `tools/resample_motion.py` (+ pure module; tests ride)

Resample the motion record from its 65 native samples to 81 samples spanning the identical
duration: **slerp on rotations** (shortest-arc, per bone, between adjacent keys), linear
interpolation on root translation, endpoints exact. Tests: endpoint identity (frame 0 and
the last frame byte-equal to source), analytic midpoint correctness on a constructed 90°
arc, monotonic time, shortest-arc sign handling (the q/−q double-cover), and a golden
resample of a synthetic two-bone motion. The stick renderer then draws the 81 frames
through the standing pre-spend **overlay gate** (sticks over the densified previz, pinned
camera) before anything uploads.

## Instrument work riding this experiment (commissioned by the E08 closing ruling)

**`route_gates.py` must raise on zero-latent examination** — on the Animate route Gate L
passed having checked nothing. The fix: when `latents()` finds no checkable latent, the
gate reports INDETERMINATE and `verify()` treats the frame-legality clause as **unproven,
raising** unless the caller supplies the frame values for direct legality checking (which
`build_animate_payload` does — 832×480×**81**, 4n+1 ✓, ≤ 81 ✓). A test proves the gate goes
red on a graph with no latent and no supplied frame values.

## Premises — marked

| # | premise | status |
|---|---|---|
| 1 | The E08 probe's exact inputs (motion record, prompt, reference, payload values), by hash from its payload record | **MEASURED** — re-verify hashes at use |
| 2 | 81 @ 832×480 is generator-legal on this route | **MEASURED** (4n+1, ≤ 81 — the model card's own horizon; E09/E08 record) — Gate L still runs with supplied frame values per the fix above |
| 3 | The output's fps is carried at encode/presentation, not inside the generation | **ASSUMED — verify** how the save/`CreateVideo` stage carries fps before claiming tempo; the true-tempo encode is a deliverable, so this premise gates it |
| 4 | The motion record's rotation representation supports slerp directly | **ASSUMED — verify** at commission (convert through quaternions if stored otherwise; conversion tested) |
| 5 | Billing: 0 credits, GPU-hours metered | **MEASURED** (E08) — re-confirm `estimate_credits` before submission |

## Hypotheses — blind degrees stated before submission

- **H-E10a (the driving signal):** the densified sticks measure smoother — per-keypoint
  second-difference drops vs the 65-frame sticks (the diagnostic that makes attribution
  causal rather than vibes). Executor predicts the drop blind.
- **H-E10b (the painted result):** chop visibly reduced at the Director's eye, judged on
  true-tempo A/B clips. No threshold invented; his eye rules.
- **H-E10c (tempo):** the E10 clip's dance duration matches E08's within one frame at true
  tempo — densification did not slow the performance.
- **H-E10d (risk, named):** slerp through the same EMA texture densifies the *path*, not
  its noise — if stick jitter barely drops, painted chop may not either; that outcome
  prices the smoothing lever as the next experiment and is a full result.

## Gates

Gate ROUTE on built AND saved graph (with the zero-latent fix live and tested) · Gate S
(`specs/E10-seeds.json` committed pre-submission) · Gate L via supplied frame values ·
the standing overlay pre-spend gate on the 81 sticks · Gate B (bit-identical driving
frames server-side, all 81) · Gate R on the APNG pack (order + pixels; the E08 bridge
pattern) · ceiling by generation count · watchdog before local renders. A fired gate halts.

## Deliverables and the report

The A/B the Director judges: **true-tempo encodes side by side** — E08's painted probe vs
E10's — plus the standard 0.5× / 8 fps review pair from lossless, the Gate 0 sheet
(previz | sticks | painted | reference, provenance block), stills at arms mid-swing where
chop lived. Report `docs/experiments/E10-report.md`: the stick-level smoothness numbers
(H-E10a) beside the eye's verdict space, both meters, gate states, predictions vs outcomes
with blindness disclosed. The advisor rules; the Director judges the motion.

## Out of scope

Smoothing/filter variants beyond the pinned EMA config · the crowd (prompt surgery) · the
pad A/B · aspect / figure size · the reference set · anything touching identity.

## Standards compliance

| Standard | Score | Evidence |
|---|---|---|
| PIN_PER_STEP | 3 | every non-varied input pinned BY HASH to the E08 payload record; seeds pre-registered; resample golden-tested |
| ANDON_AUTHORITY | 3 | the zero-latent Gate L fix ships here with its red test; overlay gate pre-spend; ceiling by count |
| NAMED_COMPENSATORS | 2 | uploads deletable server-side; bounded spend; worktree/branch table as E08's |
| DECOMPOSE_BY_SECRETS | 2 | resampler = pure module apart from render/encode shells |
| UNCERTAINTY_GATED_HUMANS | 2 | blind H-degrees; H-E10d names the null outcome as a priced result |
| EXTERNAL_VERIFIER | 2 | analytic slerp tests + the Director's eye on true-tempo A/B; the executor judges nothing |
