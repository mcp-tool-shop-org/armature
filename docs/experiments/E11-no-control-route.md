# E11 — the no-control route: GLB to video, the model generates everything

**Seat: executor (run on Opus) · new branch `E11-nocontrol` from `main`, fresh worktree
`E:\AI\armature-E11`** · **Ceiling: ≤ 3 generations wave 1** (1 probe + 2 reserve on named
causes); `estimate_credits` recorded before submission; both meters reported. **Spec
written 2026-08-12 by the advisor, before the work, at the Director's direction.
DISPATCH HOLDS until E10 closes** — his sequencing: the density experiment runs to its end
first. **HOLD RELEASED 2026-08-12** — E10 closed on the Director's A/B verdict
([E10-closing-ruling.md](E10-closing-ruling.md)). One reading rule folded at release: E11's
scene and identity observations are read under the **two-seed rule** (E10 ruling R3) — a
single-seed scene outcome is an observation, never a route property.

## Trajectory

The Director commissioned a second pipeline: skirt the skeleton entirely — the GLB hands
the model its **image** (renders of the performer from any angle we choose), and the model
generates everything else: motion, scene, camera. Prompt shapes the shot; reference images
join only as scene control demands. The skeletal route is **parked, not superseded** — it
remains the future power route, to be built up with AI-generated animation across many
experiments. This is the posture working as ruled: two pipelines in one monorepo, measured
against each other, the map redrawn by what the experiments prove. E11 buys the first
controlled evidence of **what the skeleton buys** (identity hold, camera and blocking
authority) **against what it costs** (motion texture, deterministic machinery) — the record
notes honestly that the skeletal route carries AI at both ends (a model generated its
dance, a model painted its shot); what E11 removes is the deterministic middle.

## The question

From a performer render and a prompt, with **no driving signal of any kind**: (1)
**identity** — does he stay HIM across the clip? Unconstrained generation is free to morph
a stylized figure toward the human prior; this is the route's headline risk and its
headline learning. The Director's eye rules; identity diagnostics ride and gate nothing.
(2) **Motion character** — the Director's hypothesis, recorded as his: freed from choppy
driving, the model's own motion may read smoother and livelier than the driven route's.
Judged on true-tempo clips beside E08's probe. (3) **Scene** — the prompt paints the bar
(E08 already proved this partially, with the same empty-bar caveat and its known cause).
(4) **The route's price, named up front:** whatever camera and blocking emerge are the
model's choice — on this route that is a characteristic, not a defect.

## Arms — one axis: how the GLB enters

- **A1 (the probe): I2V start frame.** Wan 2.2 I2V-A14B (Apache, mapped 2026-08-12): the
  first frame IS a render of the performer — full body, native 832×480, staged and lit
  from the GLB (no letterbox needed; we author the frame). Prompt: he dances in a crowded,
  warmly lit bar. This is the scope sentence made literal: image-to-video where the GLB
  supplies the image.
- **A2 (reserve arm, on the Director's word after A1's sheet): no-control VACE
  reference.** The E02 A2 payload shape — reference + prompt, control absent — on the
  mapped Wan VACE route. The historical shape, now run deliberately as a comparison point:
  reference-conditioning vs start-frame-conditioning is the axis.

## Premises — marked

| # | premise | status |
|---|---|---|
| 1 | Wan 2.2 I2V-A14B weights | **MEASURED** — Apache 2.0, fetched 2026-08-12, map row (output-freedom clause) |
| 2 | Core I2V conditioning node (`WanImageToVideo` or as served) — schema + licence | node code covered by the ComfyUI-core GPL row; **socket schema ASSUMED — verify via `get_node` before building**; the served I2V template is a reference, never a route (the standing law) |
| 3 | The start frame: a performer render at 832×480 | **COMMISSION** — staged render from the GLB (watchdog, headless, PowerShell); **looked at at full size before upload** (the standing law); hashed into the payload record |
| 4 | Frame legality 832×480×65 on the I2V route | **ASSUMED — verify** against the actual graph (Gate L with supplied values; the zero-latent gate behavior ships with E10) |
| 5 | Billing 0 credits / GPU-hours metered | **MEASURED** (E08/E09 pattern) — re-confirm `estimate_credits` |
| 6 | Comparability to E08's probe | **BOUNDED HONESTLY:** same prompt and negative verbatim where the route allows, same resolution and length — but a different model (I2V-A14B vs Animate-14B) and no control channel make this a **route comparison, not a single-variable one**. The spec says so; nobody reads it otherwise. |

## Hypotheses — blind degrees stated before submission

- **H-E11a (identity):** the executor states a blind prediction on identity hold (frames
  until visible drift, if any). The stylized figure with no structural constraint is the
  named risk (the grounding's G13 class, now without a skeleton holding shape).
- **H-E11b (motion, the Director's):** free generation reads smoother than the driven
  probe. Degree blind; his eye rules on true-tempo A/B.
- **H-E11c (scene):** the bar arrives as in E08 (same prompt, same default-negative
  caveat).
- **H-E11d (the price):** camera/framing drift from the authored start frame — measured
  (start-frame similarity over time as a diagnostic), not judged.

## Gates

Gate ROUTE on built AND saved graph (zero-latent behavior live from E10) · Gate S
(`specs/E11-seeds.json` committed pre-submission) · Gate L via supplied frame values ·
Gate B on the uploaded start frame (bit-identical server-side) · ceiling by generation
count · watchdog before renders · a fired gate halts. No overlay gate — there are no
sticks; its analogue is the full-size look at the start frame before upload.

## Deliverables and the report

The two-pipeline sheet the whole experiment exists for: **E08's painted probe beside
E11's**, same prompt, true tempo, with the start frame and provenance — the first
side-by-side of the studio's two routes. Plus the standard Gate 0 sheet, 0.5× / 8 fps
review pair from lossless, stills at the face, hands, and wherever identity strains.
Report `docs/experiments/E11-report.md`: measurements, both meters, gate states,
predictions vs outcomes, blindness disclosed. The advisor rules; the Director judges
identity and motion.

## Out of scope (wave 1)

The A2 arm (until his word) · crowd surgery (prompt stays pinned for comparability) ·
aspect · any driving signal · scene reference images (named for a later wave "as needed,"
per the direction) · touching the skeletal route's tooling.

## Standards compliance

| Standard | Score | Evidence |
|---|---|---|
| PIN_PER_STEP | 2 | prompt/negative pinned verbatim to E08's; seeds pre-registered; start frame hashed |
| ANDON_AUTHORITY | 3 | ROUTE/S/L/B raise in-tool; ceiling by count; dispatch itself held on E10's close |
| NAMED_COMPENSATORS | 2 | one upload, deletable server-side; bounded spend; worktree/branch table as before |
| DECOMPOSE_BY_SECRETS | 2 | the render commission is scene-side; the payload builder reuses the gated pattern |
| UNCERTAINTY_GATED_HUMANS | 2 | blind H-degrees; H-E11d prices the route's cost as a measurement, not a verdict |
| EXTERNAL_VERIFIER | 2 | gates + the Director's eye on the two-pipeline sheet; the executor judges nothing |

## The probe's verdicts (the Director's eye, 2026-08-12)

**Identity HELD** — the face held up across the clip with no anchor; R1's re-pricing is
confirmed. **Motion read as drunken wobble, not a dance** — his diagnosis: the bar language
in the prompt pulled the performance toward it; the route's semantic gravity owns the
performer as well as the world. **Hands read as a polygonal claw.** His ruling: fixable
with prompt and polish; wave 2 proceeds with the acquired techniques.

## WAVE 2 — camera held, performance clause dominant (dispatched 2026-08-12)

A **composed** wave, said plainly: two levers move together (the camera embedding and the
prompt surgery) because the Director ruled the probe's defects fixable-by-prompt and
directed the acquired techniques applied — attribution between the two levers is not
claimed, the probe remains the baseline, and the target is the shot.

1. **Camera held:** the graph moves to `WanCameraImageToVideo` + `WanCameraEmbedding`
   (`camera_pose = "Static"`) — both core, weights mapped Apache (consult #7 ruling). The
   route-gate table extends for the new classes, per the E11 pattern.
2. **Prompt surgery:** the performance clause leads and dominates — explicit dance
   vocabulary, energy, rhythm — and the bar demotes to set-dressing clauses. **The open
   fetch lands here:** the executor fetches and banks the official Wan prompting guidance
   (zero spend), records its operative lines in the payload record, and crafts the prompt
   per it. Negative extended against the named hand defect (claw/deformed-hand terms) —
   prompt-side mitigation only; the hand **geometry** fix stays on the F-series ledger,
   out of scope.
3. **Held constant:** the same authored start frame (hash-pinned), same resolution and
   length, seed freshly registered (Gate S).
4. **Ceiling:** the two reserves — probe first, the second only on a named cause.
5. **Blind predictions before submission:** camera held (horizon persistence vs the
   probe's 4/65); dance-not-drunk (the Director's diagnosis under test); hands
   improved-by-prompt-alone (genuinely uncertain — the mitten geometry may bind).
6. **Deliverables:** A/B vs the wave-1 probe at true tempo, the Gate 0 sheet, zooms at
   hands and face, the horizon-persistence diagnostic beside the camera claim.
