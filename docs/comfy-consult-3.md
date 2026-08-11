# Comfy consult #3 — findings, calibrated 2026-08-10

Consult brief: prose-only, no build order, nothing fetched into a tab. Answers relayed by the
Director. **This document records what was verified, what is credible-but-unverified, and what
the channel explicitly refused to guess.**

## Calibration — PASSED, and this is why the rest is weighted credible

Standing practice: verify one cheap independently-checkable claim before acting on expensive ones.
The consult declared `WanVaceToVideo`'s complete socket list. Checked against our own submitted
payload (`outputs/E02/payloads/A1b.json`):

| declared | ours |
|---|---|
| required: `positive` `negative` `vae` `width` `height` `length` `batch_size` `strength` | **all 8 present, exact** |
| optional: `control_video` (IMAGE), `reference_image` (IMAGE) | **both present, exact** |
| optional: `control_masks` (MASK, **plural**) | **absent — we have never wired it.** Name not independently confirmable from our payload |
| frame count 4n+1 | **33 = 4·8+1 ✓** |
| width/height multiples of 16 | **480/16 = 30 ✓, 832/16 = 52 ✓** |

Ten of ten socket names we can check match exactly. **Also confirmed while checking: our payload
contains no LoRA loader of any kind**, so the CausVid non-commercial trap has never been present
in an armature submission.

The channel was explicit about its own gaps — it declined to invent a native max frame count, a
max resolution, or a mechanism for the PNG-bridge decrement. That refusal is part of why the rest
is credible.

## ⭐ The finding with the most leverage: `control_masks`

**VACE accepts a per-frame mask defining where the control signal applies.** Where the mask is
active the model is bound by control; where it is inactive the model is free.

**armature has the exact subject silhouette every frame, for free, from geometry** — no estimator,
no licence exposure. That means we can say: *obey the depth control on the character, invent
everything else.* A model-painted world around a control-locked character.

Contract, to be verified empirically before anything is built on it:

* type `MASK`, single channel, float **1.0 = active, 0.0 = free** — so subject silhouette white.
  **Verify polarity on a one-frame test; if control leaks into the background, invert.**
* **per-frame**, a sequence matching `length` — a single static mask would be wrong for a moving
  character. Padded/truncated to `length` the same way `control_video` is.
* values in [0,1] — probe that an 8-bit matte arrives as 0/1 and not 0/255.

This is the highest-value under-used input in our stack and it is a candidate experiment.

## Length — 33 frames is well under the trained horizon

* The ceiling is **soft and governed by the training distribution**, not a hard cap. Wan 2.1 VACE
  14B was trained around the **81-frame class (~5 s at 16 fps)** at 480p/720p. The node accepts
  more; coherence and identity degrade past the trained horizon.
* **VRAM is the hard wall** on Cloud and is a stop, not a degradation.
* **81 frames (4·20+1) is the cheapest available win** — one widget value. We run 33 (~1.4 s).
* The consult **declined to state an exact native max** or a max resolution. Unknown, not assumed.

⚠ **A floor measured at 33 frames is not automatically the floor at 81.** Length changes the
population; see E04's scope note.

## Chaining — the architectural finding for a video tool

**Control does NOT carry across a chained seam.** VACE consumes a `control_video` of exactly
`length` for the clip it is generating and has no memory of a previous chunk.

**For armature this is the clean case**, because we author the control for the whole shot in
Blender: we slice our own depth sequence per chunk (with a frame of overlap at the seam) and hand
each chunk its own byte-exact slice. **The geometry does not drift across a seam — only what the
model invents does.**

**And the load-bearing rule:** re-anchor every chunk to the **one canonical reference image**,
never to the previous chunk's output. Anchoring to the previous output **compounds** drift;
anchoring every chunk to one reference is what keeps the man the same man.

## Control scheduling — the lever does not exist for video

Our best image-side win was the depth schedule (0.80 / 0.0 / 0.45, release control early).
**There is no video analogue and it cannot currently be tested.**

* `WanVaceToVideo` exposes only a scalar `strength`. No start/end percent, no per-frame weighting.
* **Neither** `WanFunControlToVideo` **nor** `Wan22FunControlToVideo` exposes a schedule either.
* Community nodes hinting at richer strength control (`WanVaceAdvanced` tier) are
  **licence-unverified — treated as NO**.

**Mechanism, and the consult was careful to mark it as reasoning rather than fact:** the image
insight is *per-frame*. Releasing control mid-denoise also removes the anchor keeping successive
frames consistent with each other, which has no still-image analogue and would read as **temporal
drift/shimmer**. Its honest position: *it does not know that it transfers, has a mechanism reason
to expect it does not, and the tool to measure it is not on the licence-clean list.*

**Ruled: `strength` stays 1.0 on VACE.** Any scheduling experiment is gated on first finding a
schedulable, licence-clean node.

## Wan 2.2 Animate — a native continuation contract, but the wrong input shape for us today

`WanAnimateToVideo` factors conditioning that VACE fuses: `reference_image` (who), `pose_video`
(body), `face_video` (face), `background_video`, `character_mask` (where), plus
**`continue_motion` / `continue_motion_max_frames` / `video_frame_offset`** — a purpose-built
chunk-continuation contract, which is exactly the long-form mechanism VACE lacks.

**But it wants a pose skeleton, not depth.** Our control is a geometry-rendered depth pass. We
would have to emit Animate's expected pose representation from Blender — which we *can* do, since
we own the bone transforms, and doing so sidesteps the detector tier entirely.

**Read: VACE for single clips up to the trained horizon; evaluate Animate specifically for the
chaining problem**, and only after confirming we can author its pose input without touching a
non-commercial detector.

⚠ **OVERTURNED by consult #4 — see "Animate is DEFERRED" below.** The sentence above treats
"we own the bone transforms, so we can author the pose" as sufficient. It is not: the socket is
clean, but the *drawing convention* the model responds to is only documented by the
licence-unverified preprocessor tier, and a wrong convention **fails silently**. Read the #4
section before acting on this paragraph.

## Identity — mechanism only, outcome to be measured here

* `reference_image` is an IMAGE socket and IMAGE is a batch tensor, so it accepts a **stack**.
  Extra references are **appearance anchors**, not per-frame identity control. A small consistent
  stack of the same man from several angles is more robust than one frontal still — it gives
  appearance evidence for profile and back, which matters exactly when our armature turns him.
* **Character LoRA binds identity into the weights**, reasserting it every frame and every clip
  regardless of reference; a reference stack carries identity per generation and can still drift.
  Suggested combination: LoRA trained on our canonical mesh renders **plus** a small reference
  stack at inference.
* ⭐ **A LoRA trained on our own canonical mesh renders is licence-clean by construction.** That is
  a real structural advantage of this pipeline and worth protecting.

**All of this is mechanism. What actually happens to identity gets measured here, not asked.**

## Licence flags raised — all treated as NO until retrieved

| item | status |
|---|---|
| `FL_WanVaceToVideoMultiRef` / Fill custom-node pack | **UNVERIFIED → NO** |
| `WanVaceAdvanced` tier (`VaceStrengthTester`, `VaceAdvancedModelPatch`) | **UNVERIFIED → NO** |
| `WanAnimatePreprocess` detector tier (ViTPose / DWPose weights) | **UNVERIFIED → NO** — and it forced a correction to our own map, below |
| `Wan2.2-VACE-Fun-A14B` **Cloud node availability** | **UNCONFIRMED** — the weight name is on our licence map, but the consult found no node by that name; the 2.2 control route presents as Fun-Control and Animate |

### ⚑ A correction to our own licence map, earned by this consult

Our DWPose row read **Apache 2.0 → YES**, citing
`raw.githubusercontent.com/IDEA-Research/DWPose/onnx/LICENSE`. **That document is the code
licence.** The consult flagged the detector *weights* tier as a non-commercial minefield, and it
is right that the two are separable — **this is the identical trap our own map already records for
`rembg`** ("MIT covers code only — bundled weights carry separate licenses, not yet fetched").

**The row is narrowed:** DWPose **code** is Apache; DWPose **weights** are **NOT FETCHED, therefore
UNVERIFIED, therefore NO.** Nothing in armature depends on it — we render pose from geometry — so
this costs us nothing and closes a hole that would have opened the moment someone reached for a
pose preprocessor.

## Platform behaviours we reported back

* **Determinism at fixed seed** — consistent with the schema; nondeterminism lives in the encoder,
  not the sampler. Our H.264 conclusion is endorsed, not independently re-measured.
* **`dry_run` PASS then submit refusal** — structurally expected: a schema/enum validator can pass
  a graph whose *link topology* is still illegal at execution. Our practice of checking topology in
  code and refusing to cite `dry_run` as evidence of runnability stands.
* **PNG-batch `max(src−1,0)`** — the consult **does not know** the cause and declined to guess. Its
  general remedy: **fewer encode/decode hops** between Blender and `control_video` — hand VACE a
  single IMAGE batch without a per-image round-trip, rather than a PNG re-encode per frame.

## What this opens — candidates, not yet specified

Named here so they are not lost, and deliberately not specced while E03 is mid-flight:

1. **`control_masks` + geometry silhouette** — control-locked character, model-invented world.
2. **81 frames** — one widget value, ~5 s, inside the trained horizon.
3. **Chained clips at one canonical reference** — the long-form performance test.
4. **The Blender→`control_video` hop count** — whether a lower-hop path removes the −1.

Related: [[E04-the-between-generation-floor]] · `docs/license-map.md`

---

# Consult #4 — both proposed unlocks came back CLOSED, and that is the value

Round 4 answered the two follow-ups #3 set up. **Both are weaker than they looked, and the route
that survives is the one we already had.** Recording the closures, because a path ruled out
cheaply is worth more than a path opened expensively.

**My own framing was too optimistic and I am correcting it in place:** brief #4 called Animate's
continuation contract *"the single unlock for long-form performance on our stack."* It is not an
unlock. It is a real socket behind an unverified convention behind an unverified licence.

## ⚑ THE LAW THIS ROUND EARNED — a non-commercial tier can re-enter as a SPEC dependency

`pose_video` on `WanAnimateToVideo` is an **IMAGE** socket (verified) — a rendered pose sequence,
not structured keypoints. We own every bone transform, so authoring it needs no detector at
runtime. **That part is clean.**

**But the pixel convention that makes the model actually respond** — joint set, limb-colour table,
line widths — is empirically whatever the `WanAnimatePreprocess` tier emits (`DrawViTPose`,
`PoseAndFaceDetection`, `FaceComposite`). That tier is already **UNVERIFIED → NO** on our map.
The consult's sharp point:

> *It is not just an alternative to authoring `pose_video`, it is also the **only reference for the
> drawing convention** `pose_video` expects. So it re-enters your pipeline as a **spec dependency**
> even if you never run the nodes. Verify its licence before reading its drawing code, not just
> before wiring it.*

**This is our own "a bypassed non-commercial node is still present" ruling, one layer up.** We
ruled that bypassing is not removal because the workflow JSON still cites the model. The same
logic reaches further than we had noticed: **a non-commercial implementation consulted as a
specification is a form of presence**, and "we re-implemented it ourselves" does not obviously
launder a colour table lifted from it.

**Ruled, and bounded honestly:** this is a **risk to surface, not a settled legal conclusion**.
Licences govern copying and distribution; learning a fact is not automatically a derivative work,
and a verbatim colour table is a different object from a fact. **The safe path is to determine any
such convention empirically rather than by reading non-commercial source**, and where that is
impractical the licence gets retrieved and the question goes to the Director. Added to the licence
map's procedure.

**And the failure mode is the worst kind:** a wrong pose convention **fails silently** — the model
just obeys weakly. There is no gate that fires. That alone disqualifies it as a near-term route.

## Ruling — Animate is DEFERRED, and VACE chaining is the route

Animate buys a **purpose-built** continuation contract (`continue_motion`,
`continue_motion_max_frames`, `video_frame_offset` in **and** out, so chunks thread by design).
VACE buys **do-it-yourself** chaining, which consult #3 already established we can do: slice our
own authored control per chunk, re-anchor every chunk to one canonical reference.

**VACE chaining is available today, licence-clean, with no new node, no new convention and no new
licence question.** Animate is a possibly-better mechanism gated behind two unknowns, one of
which fails silently.

**Ruled: test VACE chaining first. Reach for Animate only if VACE chaining measurably fails at the
seam** — and if it does, the first step is retrieving the `WanAnimatePreprocess` licence, not
reverse-engineering a colour table. *Enumerate the resource before commissioning one*: the
resource here is our own authored control, and it already exists.

*(Recorded from the schema: `face_video` is optional and the node runs on body pose alone —
verified structurally, with quality impact explicitly NOT verified.)*

## FLF2V — assessed, and it probably solves a problem we do not have

The consult **corrected its own #3 imprecision unprompted**: `video_wan_vace_flf2v` is a
*template filename*, not a node. The node is **`WanFirstLastFrameToVideo`**, a **separate
conditioning node from VACE**, not a VACE mode.

Verified schema: `start_image` **and** `end_image` are both optional IMAGE sockets — so it does
pin both sides. **And it has no `control_video` and no `control_masks` socket at all.**

So "FLF2V + dense authored control" is **two conditioning nodes stacked**, and whether they
compose or fight is **unverified**.

**The reasoning that actually closes it** — the consult's, and it argues against the idea I
proposed:

> FLF2V pins two frames and lets the model invent the interior. **Your whole thesis is that you
> already author every interior frame as dense control.** If dense control is working, the seam is
> not drifting because the endpoints are unknown — it drifts in what the model invents. So FLF2V
> risks solving a problem your dense control already solves, while adding an unverified
> composition question.

Our one genuine advantage — **our endpoints are authored geometry, not guesses**, so we can render
the exact first and last frame of every chunk — is real and specific to armature, and it still
does not make the path necessary.

⚑ **THIS RULING IS SUPERSEDED — Director, 2026-08-10.** FLF2V is kept as a **random route**:
[docs/random-routes.md](random-routes.md) RR-1. The reasoning below grades FLF2V on how well it
duplicates the dense-control arm, which is judging a capability by our own test design — the
shrinking family. Stated properly it is a **different instrument**: authored keys with
model-invented in-betweens, where a shot costs *two poses* instead of a full animation, and where
we can supply the best endpoints anyone could (authored geometry, not guesses). It is not on the
critical path and it is not closed. The identity risk is real and is the thing it must be
measured on. **Read RR-1 rather than the paragraph below.**

**Superseded ruling, kept because the correction is more useful than the original: FLF2V is at
most a one-generation probe, and only after VACE chaining has been tried.**
If it is ever run, the cheapest discriminator comes first: *does the two-node stack produce
coherent output at all, or do the two conditionings fight?* If they fight, the path is closed
regardless of the endpoint advantage.

## Licence position after #4

| item | status |
|---|---|
| `WanAnimatePreprocess` tier | **UNVERIFIED → NO**, and now also flagged as a **spec dependency**, not only a runtime one |
| `FL_WanFirstLastFrameToVideo` (Fill Nodes) | **UNVERIFIED → NO.** Use core `WanFirstLastFrameToVideo` if ever needed |
| `WanAnimateToVideo`, `WanFirstLastFrameToVideo` (core nodes) | **ASSUMED-FROM-CATEGORY, NOT VERIFIED** — the consult placed them in the Wan/Apache tier by category and was explicit that it did not retrieve either licence this turn. Per our own gate, assumed is not verified; neither gets used without a retrieved row |

## What survives, and it is the simple thing

**VACE + our own authored control, sliced per chunk, every chunk re-anchored to one canonical
reference.** No new node, no new convention, no new licence question, and it was already in hand
after #3. The two exotic routes were worth asking about precisely so they could be closed cheaply
instead of discovered expensively.

Unchanged and still the first thing to build: **`control_masks` + the geometry silhouette.**

---

# Consult #5 — can GLB metadata annotations influence video generation?

**Core answer ACCEPTED:** no node reads glTF `extras`; ComfyUI never sees the `.glb`, because
Blender has already rasterized the mesh into an IMAGE sequence upstream. There is no
`extras` → conditioning socket. **We are the compiler between the annotation and the tensor.**

Route 2's principle is the keeper and it is exactly where armature already lives:
**don't hand the model the annotation, hand it the render of the annotation.** Our depth pass is
already metadata-as-channel — the Z-buffer is the mesh's own geometry rendered into a tensor the
model was trained to obey. The pattern is proven; the question is only what else gets rendered.

**Four things the consult missed or under-weighted**, because it read "influence generation" as
"reach the sampler."

## 1. ⭐ The highest-value use is not conditioning at all — it is GATING

Annotations are **authored, exact and machine-readable**. That makes them the right input to a
gate we do not have.

**Nothing today prevents submitting the right control sequence with the wrong reference image.**
The "same man" invariant — the thing this whole repo exists to protect — is currently held by
nobody. If the mesh declares its canonical character id, the payload builder can **raise** when
the reference does not match it.

Per the standing law: the check lives **inside** the tool performing the submission, it `raise`s,
no shell chain, no `assert`, no skip flag. That converts identity from a hope into an andon. It
costs zero credits and it is the first thing I would build out of this idea.

## 2. And provenance — annotations pin MEANING, where hashes pin bytes

*A recipe that does not reproduce its output is not a recipe.* Today our record pins control-input
hashes. **A hash tells you the input changed; an annotation tells you what it was** — which
character, which canonical mesh version, which shot. That is the difference between a record that
detects drift and a record that explains it.

## 3. Route 3 is not "out-of-band" for us — it is native

The consult framed build-time graph decisions as legitimate-but-decoupled. For armature it is the
**main** route: we build payloads programmatically and no tab is ever in the path. An
annotation-driven build is **more** reproducible than a hand-set one, not less — that is
`PIN_PER_STEP` exactly.

## 4. ⚠ Route 1 carries facet's recorded identity failure, and the consult called it merely "soft"

Metadata → positive prompt is not just advisory. E02 measured that **prompt and reference supply
*who***, and facet's law is sharper still: *"if a canon element is not named in the prompt, it is
arriving by accident and will leave the same way"* — learned when a registration improvement
**silently replaced the character**, because identity was riding in an artifact nobody had
declared was carrying it.

**Auto-concatenating annotations into the positive prompt recreates that exact failure**: identity
riding in a data file nobody reviewed. An auto-generated prompt is an **unreviewed** prompt.

**Ruled:** annotations may **propose** prompt text. Canon elements are named in a **versioned,
reviewed** prompt. Material and mood may be assembled; identity may not.

## 5. A constraint the consult glossed — Route 2 has socket contention

`WanVaceToVideo` has **one** `control_video`, and depth is already in it. A segmentation / ID pass
is therefore **not additive — it competes**, and consult #3 established there is no
`ControlNetApplyAdvanced` equivalent for VACE. A second dense control would have to *replace*
depth or be composited into a single image, which is its own experiment.

**`control_masks` is a separate socket, so masks ARE additive.** That is precisely why the mask
route is the cheap one and the ID-pass route is not — and it is another reason `control_masks`
stays the first thing to build.

## 6. Declining the offered `Load3D` round, with the reason

The consult offered to verify whether any `Load3D`-family node exposes glTF `extras`. **Not worth
a round.**

Even if one did, using it would mean routing the `.glb` **to Cloud** — an upload path, a
glTF-parsing custom node with an unretrieved licence, and a new dependency — **to obtain data we
already hold locally in Python.** Our architecture rasterizes locally by design (*generation runs
on Comfy Cloud; rendering and measurement run locally*). We are the compiler, and the compiler
runs here. The answer would be interesting and would change nothing.

---

# Consult #6 — and its top-priority experiment was already on disk

The consult decomposed E03's B1 into **two sufficient, confounded explanations**: the **subject**
(a wire armature is ~30 cylinders with no body — even perfect interpretation of that depth yields
sticks) and **OOD-copy** (a sparse high-contrast control far from the training manifold degrades
toward literal reproduction). It was explicit that it could not verify the second, and its key
structural point:

> These two explanations are **not separable by a strength sweep**, and they **are** separable by a
> single control/subject swap. Priority 1: *solid figure, depth control, reference on — one
> generation.*

## ⭐ That experiment is E02's A1a, and it ran on 2026-08-10. Zero credits needed.

A1a **is** solid figure + depth control + reference on + strength 1.0. Read off
`outputs/E02/sheets/E02-thesis-A1a-vs-A2.png` by this seat:

**A1a produced a fully painted armoured knight** — horned helm, cape, plate, standing on a plinth in
a lit studio with a cast shadow. Material, light, staging and ground **invented by the model**,
silhouette and placement **obeyed from the control**. It is emphatically **not** a re-drawn depth map.

**Ruled — the subject explanation dominates and OOD-copy is a red herring:**

* **At `strength` 1.0, with a body to paint, the model paints.** No copying problem exists on a real
  subject.
* **E03's B1 returned sticks because a wire armature is sticks**, not because the control was
  out-of-distribution and not because strength was too high.
* *Enumerate the resource before commissioning one* — the deciding generation was already in hand,
  and the consult's own #1 cost nothing.

## ⛔ E05 (the strength sweep) is WITHDRAWN, not deferred

E05's premise was *"the model may be copying rather than painting; that behaviour lives below 1.0."*
**A1a falsifies the premise.** Withdrawn rather than re-derived, per the standing law — withdrawing
is not choosing a new number, and that is the whole difference.

**What survives as a demoted candidate:** A1a's figure is small and plinth-bound where A2's (no
control) is large and dynamic, so control at 1.0 does appear to constrain **composition and scale**.
That is a *refinement* question, not the thesis question, and it waits.

## The modality answer, kept for when it is needed

Ranked by appearance freedom, all authorable from geometry we own with **no estimator and no licence
exposure** — the payoff of the from-geometry decision, and the consult confirmed the whole set stays
clear of the DWPose/Depth-Anything tier by construction:

**drawn skeleton** (loosest — pins joints, says nothing about silhouette) → **flat-shaded
segmentation/ID** (pins silhouette and region, no depth gradient, surface free) → **canny/edge** →
**normals** → **dense depth** (tightest; encodes full 3D form).

Its recommendation was **segmentation/ID** as the "constrain geometry, free surface" candidate,
with the honest caveat that it **cannot promise VACE responds to seg as strongly as to depth**. And
for a drawn skeleton it **does not know the convention Wan's pose channel expects** — the same
unverified-convention wall as consult #4's `pose_video`. Recorded for later; not the next move.

*Also recorded, unverified but useful:* `strength` 0 is reasoned to be plain t2v — i.e. **A2** — so
no arm is ever spent at 0.

---

# Consult #7 — rigging. The Cloud class is CLOSED, and that settles the route.

## ⛔ Tripo is OUT — licence conflict. Director, 2026-08-10.

The consult identified Tripo as the one Cloud vendor able to rig **a mesh we supply** — its import
node takes `FILE_3D_GLB` and returns a `MODEL_TASK_ID`, which its rig node consumes. **The Director
ruled it out on a licence conflict before any spec was written and before any credit was spent.**

**The warning was already in the record I had read this session.** Comfy consult #1 (2026-08-01)
left open: *"Licence verification: Fun ControlNet 2602 and **Tripo P1** — both decisive for
commercial use, both explicitly NOT verified by the consult."* And its round-2 note: *"swapped Tripo
P1 → v3.1 for licence reasons — which didn't even work, same vendor, same ToS: the licence question
**moved**, it didn't resolve."*

**That is *enumerate the resource before commissioning one*, missed again**, and caught by the
Director rather than by this seat. Zero credits lost.

## The consequence: there is NO Cloud rigging route at all

| vendor | rig node? | takes our mesh? | status |
|---|---|---|---|
| **Tripo** | yes | **yes — the only one** | ⛔ **OUT — licence conflict** |
| **Meshy** | yes | **no** — its rig node takes a `MESHY_TASK_ID`, obtainable only from a Meshy *generation* node | cannot take our character |
| **Rodin** | **no rig node** | — | — |
| **Tencent / Hunyuan3D** | **no rig node** | — | — |

Verified by absence: **there is no open-weights auto-rig on Cloud.** That tier generates geometry,
never skeletons.

**Ruled: the Cloud rigging class is closed. Rigging happens locally.**

## And that is the better answer, not a consolation

The Cloud route was already disqualified for our work on its own terms:

* **The pose vocabulary is a fixed preset enum** — `walk / run / slash / jump`, plus quadruped and
  serpentine gaits — **not arbitrary keyframes.** armature authors performances; a preset list only
  ever reached shots that happened to fit it.
* It traded away the **estimator-free, licence-clean-by-construction** property — armature's
  structural advantage — for a per-vendor ToS dependency.
* Its go/no-go was **unknowable without spending**: no schema exposes the skeleton a vendor writes,
  so the bone names could not be established in advance.

**Local rigging has none of those problems:** arbitrary poses, no licence question, no vendor
dependency, and the rig is an asset owned outright. It costs crew time, once, on one character.

## What this consult is worth — the route it CLOSED, and the hazards

1. **Foreclosure by enumeration.** From live schemas rather than assumption: no Cloud rigging path
   survives our gate. That ends the search instead of leaving it open.
2. **Wan Animate stays NO**, reaffirmed — no licence-clean statement of its pose convention exists,
   and reading `WanAnimatePreprocess` to learn it makes that tier a **spec dependency even if the
   node is never run.**
3. **The Q4 hazards**, which bind on whoever authors control from a posed mesh.

## ⚑ Q4 — control-authoring hazards, and one CORRECTS an earlier consult

1. **Self-occlusion is the top risk, *because of* our horns result.** When an arm crosses the torso,
   **depth** separates them by Z; a **flat silhouette/segmentation** control merges them into one
   blob. We measured that the reference **invents silhouette where the control is silent** — a
   merged blob is exactly that, and it may resolve differently frame to frame.
   ⚑ **This corrects consult #3's segmentation recommendation.** Seg/ID frees surface but discards
   the front/back information depth carries. **Prefer depth wherever occlusion or foreshortening is
   in play.** Our depth-from-Z-buffer path was right and stays.
2. **Foreshortening reads as "small," not "toward camera."** A limb aimed at the lens collapses to a
   stub with no cue it is foreshortened rather than truncated. Depth mitigates — the stub is
   *bright*. Watch thrusts and reaches toward camera.
3. **Frame-coherence is where ambiguity bites.** One ambiguous frame survives; the model resolving it
   *differently* across frames reads as flicker even though our control is deterministic. **Author a
   few degrees of stand-off** between limb and body across transitions.
4. **Extreme poses fail on the SURFACE while the outline stays correct** — smeared plate, a cape
   doing nothing sensible. **We would misread that as control failure if we did not separate the
   two.** Named in advance so we do not.
5. **Whatever terminates a limb in the control becomes the hand or foot.** Our bristled cylinder ends
   generalise. A real posed mesh helps — but **fingers sit below silhouette resolution at 480×832**,
   so expect mitten-hands and do not author shots depending on finger pose.
6. **Scale consistency is a gift.** Figure width tracked control within **0.007 of frame width**, so
   consistent framing in Blender yields consistent framing out — and an inconsistent camera distance
   between shots shows as the character changing size, which the reference will not correct. **Lock
   camera framing per character like a real shoot.**
