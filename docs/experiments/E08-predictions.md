# E08 — predictions, registered BLIND before the first submission

**Seat: executor.** Written and committed before `run_saved_workflow` was called on
`armature-e08-probe-animate`, and before any E08 output existed anywhere. Nothing in this
file was written after looking at a generated frame. The git timestamp on this commit is the
evidence; the probe's `prompt_id` appears only in the report.

The spec's hypotheses are H-E08a–d and it asks the executor to state **degrees** blind. Each
clause of each conjunction is predicted separately — nine consecutive facet arcs missed on
exactly that, and E09's own H5a split (right on the clause, wrong on the magnitude) is the
most recent instance.

## What I have and have not seen

**Seen:** the 65 pose-stick frames; the overlay of those sticks on the E09 previz; the
letterboxed reference; the built and saved graphs; every gate's evidence.
**Not seen:** any output of this model, on this route, at all. No E08 generation exists.

## H-E08a — motion adherence

*The painted figure performs the rig's dance, read at the sheet against the previz.*

- **The gross body pose tracks the sticks at every sampled frame — 80%.** The driving signal
  is rendered from the rig rather than detected, so it carries no extraction error (G9's
  first half is removed by construction), and G11 records the render-don't-detect pattern
  working elsewhere. What I am less sure of is not whether it follows, but how *strongly*.
- **The limb TIMING matches frame for frame rather than drifting — 65%.** `pose_video` is
  VAE-encoded and attached to both conditionings, which is a per-frame signal; but it is
  conditioning, not control, and nothing forces frame-exact adherence.
- **The stick width is the risk I would name first — and I predict it costs something
  visible: 55%.** The convention's own formula gives `stickwidth = 1` at 832×480. Wan-Animate
  is normally driven at 720p+, where the same formula gives 3–4 px. A one-pixel skeleton
  after an 8× VAE downsample is close to nothing; if adherence is weak, this is where I would
  look before the convention or the proportions.

## H-E08b — identity

*Is it the same character?* **The Director judges; no number here is a prediction of his
ruling.** What I will predict is the mechanism, because it is checkable:

- **The terracotta material and the bald jointed-mannequin read survive — 70%.**
- **The FACE survives as the twin's face — 30%.** G13 puts stylized/3D references in a
  documented degraded class, the reference is now ~20% of the frame after letterboxing, and
  the face inside that is a few dozen pixels. I expect a mannequin, and I do not expect his
  face.
- **The reference's flat grey margin leaks into the output as a grey field — 40%.** This is a
  cost of the letterbox that the as-is crop would not have had, and it is the thing I would
  check first if clause 3 comes back weak.

## H-E08c — scene from prompt

*How much bar arrives from text alone, with `background_video` unconnected?*

- **Some scene arrives — 75%.** The background plane is uniform mid-grey with an all-ones
  concat mask, so the model is free to paint everything; the prompt is the only thing telling
  it what.
- **A recognisable BAR — a counter, bottles, warm light — 45%.** G15 records that the model
  card's own guidance treats text as secondary to the motion signal.
- **Other people in the scene, as the prompt asks — 25%.** Wan's own negative prompt, which
  this graph uses verbatim, contains 杂乱的背景 ("cluttered background") and 背景人很多
  ("many people in the background"). **The inherited negative actively fights this clause of
  the positive.** I noticed this while building and did not change it: the negative is
  Wan's own documented default, changing it would move two variables, and the contradiction
  is worth measuring once rather than assuming. If the crowd is absent, this is the first
  named cause and it is named here, before the run, not after.

## H-E08d — proportions

*The non-human skeleton is out-of-distribution (G9, G10). Does the model humanise him?*

- **Some humanisation at the limbs — 60%.** The rig's proportions are the mannequin's, and
  they are not a human's; G8 says the model rescales per-limb between driving and reference
  skeletons, and here both are the same figure, so the retarget should be a no-op — but the
  *painting* is not bound by that.
- **The elbows and knees keep their sculpted ball joints — 35%.**
- **The hands come back malformed — 80%.** They are ~23 px across in the driving signal,
  drawn at hand-stick-width 1, and they are synthesised mitten fans rather than measured
  fingers. Wan's negative prompt names bad hands three times over, which tells me the failure
  is common enough to be worth a default negative.
- **The skull reads as a smooth bald head rather than a haired one — 65%.**

## What would make me say the route does not work

Stated in advance so it cannot be adjusted afterwards: **if the painted figure's limbs do not
follow the sticks at the sampled frames** — that is, if the pose signal is not visibly
driving the body — then the route as configured has not carried the performance, whatever
else the frame contains. That is a negative result and a full success, and the named
candidate causes, in the order I would rank them today, are: (1) one-pixel sticks at 480p;
(2) the reference's grey margin dominating a 20%-of-frame reference; (3) the convention
itself.

## Meters

Recorded before the run so the delta is measurable: `estimate_credits` returns **0 credits —
no paid API nodes**, which is the honest answer for an all-OSS graph and means it cannot arm
a numeric ceiling. The effective meter is GPU time. Baseline from `get_usage_report`
(2026-07-12 → 2026-08-12): GPU Hours Product **$17.166467** for the period, of which the
2026-08-12 00:00–08:00 bucket is **$0.552448**. The ceiling is therefore enforced by
counting generations — 1 probe, 2 reserve, `specs/E08-seeds.json`.
