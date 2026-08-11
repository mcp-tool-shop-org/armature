# E09 — calibration ruling: Stages A and B1 ruled, the B2 halt upheld, the clean graph commissioned

**Advisor ruling, 2026-08-11.** Report: `docs/experiments/E09-report.md` on `E09-run` @
`0c2b3cd` (pushed). **E09 remains OPEN** — Stage B2 runs under amendment A2 of the spec.

**Verified by this seat before ruling, not taken from the summary:** the suite
(**417 passed / 35 skipped**, run with the repo venv in the worktree); the sheet's sha256
(`9c74074d86ebbd28…`, exact match); the route-gate evidence JSON (all four counts present as
reported, including the pinned-vs-randomized split across the two samplers); the branch
shape (predictions commit first, four commits, zero credits — queue read empty at halt).

## R1 — Stage A stands; the solver is admitted as pipeline machinery

Round-trips close at < 1e-9, the solve is idempotent, and the gates were exercised broken
under `-O` and `PYTHONOPTIMIZE=1` — the gates-raise law, tested rather than recited. The
pass condition earned its keep twice: the root double-count (0.0036, invisible without root
rotation) and the hinge matched as a ray (178.9° of twist on a clean swing, positions
perfect throughout) were both bugs, found because a miss was defined as a bug in advance.
The corrected claim is adopted as the module's honest boundary: **a parent's twist is not
measured by positions; it is recovered only under the stated hinge assumption**, and
`twist_conditioning` (sine of observed bend, per bone per frame) rides every future lift
report in place of a boolean.

## R2 — B1's three-gap decomposition is the chain's measured floor

Adopted as stated: **7.37°** median is the representational floor on this fixture (33
landmarks + stated assumptions carrying 22-bone motion); the detector contributes the bulk
(**34.33°** with an oracle axis); the deployable chain reads **34.87°**, and one EMA pass —
the single recorded lever — takes it to **31.17°** (jitter 16.69° → 7.08° against the
authored 0.46°). The axis convention's cost (median offset 16.26°) lands almost entirely on
the root (`hips` 27.98° vs 19.14°) and nowhere else — measured, with the mechanism
(parent-relative rotations absorb a global mis-rotation at the root) demonstrated rather
than reasoned.

**The finding this seat weights highest: arms are the worst group in every arm of the
decomposition, including the detector-free one** (model gap: arms 40.00° vs legs 14.72°).
For a first shot whose performance is a **dance**, the arms are the performance. B2's sheet
inspects arms first, and any B2 judgement names them explicitly.

## R3 — the invalid foot ratio is upheld as refused, and the metric is population-scoped

`walk.foot_slip`'s denominator (the hips' path) is pinned near zero by the hip-origin
landmark convention, so the 19.756 ratio measures the convention, not the lift. The
executor's refusal to quote it is exactly the instrument law. Ruled: the metric is **valid
on world-rooted motion, invalid on hip-origin lifted motion**; a lifted-population foot
instrument is named instrument work for a future commit — not invented while looking at the
numbers it would judge.

## R4 — the axis-convention offset is a parked lever, not a blocker

A fixture-derived axis correction is a candidate calibration constant — adopted only if a
second fixture with different motion shows the offset stable; otherwise it is
motion-dependent and stays uncorrected. B2 does not depend on it (dance-in-place; root
motion out of scope), so the lever is parked with its condition written down.

## R5 — the prediction ledger is part of the calibration

Seven blind or disclosed clauses hit; two blind clauses missed, both on *which* thing is
weak rather than magnitude — the blank face detected at 0.9999 (the weak landmarks are the
occluded far-side arm: geometry, not surface), and arms worse than legs, reversed. Both
misses feed forward: occlusion is the detection risk to stage around in B2's prompt (a
dancer mid-shot, limbs unoccluded, per the model card's own bounds), and the face's
detection strength says nothing yet about identity — that question stays E08's.

## R6 — the B2 halt is upheld; premise 6 is falsified and amended in place

The saved E02 route is a VACE control graph, not a T2V shape; the served T2V template fails
Gate ROUTE on four counts (the map's excluded lightx2v 4-step LoRAs wired at strength 1.0,
not bypassed; a randomizing seed — Gate S unarmable; no length or seed slot — the spec's
832×480×65 cannot be set on it; both samplers on the excluded 4-step/cfg-1 trajectory).
Reaching B2 through that graph would have been rebuilding a route mid-experiment — the
shape that cost E08 twice. **The stop was the rule working.** Spec amendment A2 records the
falsification and the corrected route.

## R7 — Gate ROUTE is adopted pipeline-wide, and the template law lands

`tools/armature_core/route_gates.py` (+ 16 tests) is adopted as the **graph-admission
gate**: every graph this repo submits passes Gate ROUTE before Gates S and L arm — it walks
subgraph blueprints, so nothing hides in a wrapper. The served-template pattern is now
measured twice in one day (the Animate template wires the banned detector tier; the T2V
template wires the excluded trajectory), so the law lands in CLAUDE.md: **a served template
is a reference, never a route.**

## R8 — the clean T2V graph is commissioned

Built in-repo from pieces the licence map already covers: the two Wan 2.2 T2V UNETs
(high/low noise — the fp8-scaled files are Comfy-Org repacks of the mapped Apache weights;
repack ruling recorded in the map), umt5 CLIP, Wan 2.1 VAE, two `CLIPTextEncode`, two
`KSamplerAdvanced` at the **model's reference full-step trajectory** (values taken from the
Wan 2.2 reference defaults and recorded in the payload — never from the served template),
no speed LoRAs, seeds pinned `fixed` from a committed Gate S list,
`EmptyHunyuanLatentVideo` at 832×480×65. Admission: Gate ROUTE green on our own graph →
Gate S → Gate L on the actual graph → `save_workflow`, then the saved file submitted
verbatim. Ceiling unchanged: 8 credits, one probe, then reserve only on a defect with a
named cause.

## R9 — standing

E09 stays open for B2 under amendment A2; the same executor seat may continue in the same
worktree. The branch is pushed; the advisor merges when E09 truly closes. E08's rewrite
waits on B2's report. **No quality verdict is made here** — B1's purpose was measurement,
and the chain's worth-a-shot call belongs to the Director at B2's sheet on the true
population; if his eye rules the B1 sheet's third column disqualifying before B2 runs, that
ruling overrides this one's sequencing.
