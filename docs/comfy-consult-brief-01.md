# Comfy consult brief #1 — armature E02 (control-sequence → video)

**Project:** `armature` (mcp-tool-shop-org/armature). Commercial game studio. **Hard licence
rule: nothing non-commercial anywhere in the pipeline, including experiments** — CC-BY-NC,
research-only and academic-only are banned outright, so please flag any component whose
commercial grant you are unsure of rather than assuming.

**What armature does.** A canonical character mesh (GLB) is staged and animated in **headless
Blender**; the render becomes a per-frame **control sequence** that a video model must obey, so
generated video carries one persistent character whose position and pose are known every frame.
The previz scene is ground truth; the model paints life over it.

---

## The exact stack, as measured (not assumed)

**Upstream (built and passing, this week):** `tools/stage_render.py`, Blender **5.2.0 LTS**
headless, 103 tests. Per shot it emits, from one camera pass:

| channel | what it is | encoding |
|---|---|---|
| `depth` | perpendicular camera-Z from the Z-buffer, **not** an estimator | 8-bit PNG for consumers + 16-bit/EXR master retained |
| `normal` | camera-space normals | 8-bit RGB |
| `mask` | exact alpha silhouette | binary (measured exactly binary at `filter_size=0.01`) |
| `edge` | geometric discontinuity derived from depth+normal, **not Canny** | 8-bit near-binary |
| `pose` | **not emitted** — see the constraint below | — |

**No ML estimator is anywhere in the pipeline.** Depth comes from the renderer, so we never run
MiDaS/Depth-Anything, and we never run OpenPose. That is deliberate: **OpenPose is CMU
non-commercial** and **Depth Anything V2 Small is Apache while V2 Large and all V3 weights are
CC-BY-NC** — we verified both from the licence documents on 2026-08-10. Rendering control from
geometry removes that whole banned tier by construction.

**Reference stack available:** a sibling tool produces self-consistent **8-view character
turnarounds** of the same canonical asset, so we can supply many true reference views of the
subject rather than one lucky still.

**Determinism measured:** two runs from fresh processes are **byte-identical and pixel-identical**
across 6 channel directories × 33 frames. So our inputs are reproducible; what we do not know is
how reproducible the *generation* side is.

## What we already measured or retrieved — please correct us, don't re-derive

- **Champ (arXiv:2403.14781):** dense 3D-parametric guidance (depth + normal + **semantic**)
  beat 2D-skeleton-only — FVD 192.34 → 170.20; dropping the skeleton entirely still beat
  skeleton-only. This is why our channel order is depth/normal first and pose last.
- **Wan licensing (our map):** Wan 2.1 T2V/VACE/Fun-Control all Apache-2.0 with an explicit
  output disclaimer. Our local knowledge base additionally records **Wan2.2-Fun-A14B-Control**,
  **Wan2.2-VACE-Fun-A14B** and **Wan2.2-Animate-14B** as Apache-2.0 / commercial-yes.
  HunyuanVideo excludes the EU/UK/South Korea by territory, so it is out for us.
- **Constraints we have from docs, unconfirmed against a live node:** width/height divisible by
  **16**, frame count **4n+1**, Wan2.1-Fun-Control documented at 512/768/1024, ≤81 frames @16fps.
- **Depth convention we have from docs:** ControlNet-family depth is *inverse relative* depth
  (near = bright), per-frame min-max normalised, 8-bit. **We do not know whether Wan/VACE expects
  the same polarity and normalisation**, and getting it backwards would invalidate our first
  generation run silently.
- **A measured open question of our own:** per-frame min-max normalisation re-maps the depth
  range every frame, so on a moving camera *static geometry changes brightness while standing
  still*. We measured mean-abs per-pixel difference between per-frame and per-shot
  normalisation at **0.060** (a prop) and **0.085** (a character), crossover at level 56–112 of
  255. We ship both and have deliberately not chosen.

## A constraint that may change your recommendation

**We cannot currently emit an OpenPose-style skeleton.** Measured across our four rigged GLBs:
two carry a real armature, and **both name their bones `bone_0…bone_29`** — no anatomical joint
is identifiable by name in any asset we have. A third carries its "skeleton" as 30 `EMPTY`
objects, not a glTF skin. So pose conditioning needs a joint-naming/retarget step we have not
built. Please assume **depth + normal + mask + edge are what we can supply today**, and tell us
if that materially changes which route you'd pick.

---

## Questions — only things local measurement cannot settle

**Q0 (calibration, please answer even though it's cheap).** State verbatim the input names and
types of the core `WanVaceToVideo` node as Cloud currently exposes it, and the `control_video`
(or equivalent) input of the Wan Fun-Control path. *We will check this against the live schema
ourselves before acting on anything below — same discipline as last consult, no offence
intended.*

**Q1 — what is actually runnable on Cloud, today.** Of `Wan2.1-VACE-14B`,
`Wan2.1-Fun-14B-Control`, `Wan2.2-Fun-A14B-Control`, `Wan2.2-VACE-Fun-A14B` and
`Wan2.2-Animate-14B` — which are available on Comfy **Cloud** (not merely on HF), and which is
the current best-supported control-video path there? Template names if any exist.

**Q2 — the control-input contract.** For that path: how is a control **sequence** supplied
(frame folder, video file, batched IMAGE tensor)? **What depth polarity and normalisation does
it expect** — near-bright or near-dark, per-frame or per-clip, 8-bit? Does it accept **multiple
stacked control channels** (e.g. depth + edge together), and if so how are they combined and
weighted?

**Q3 — is there a control-strength schedule.** Our image-side lesson from your last consult was
that **releasing control early frees surface while structure stays locked** (0.80 / 0.0 / 0.45,
which we tested and adopted). Does the video path expose an equivalent start/end schedule, or
only a flat strength? If flat, is there a known-good value for *synthetic, clean* control input
as opposed to noisy extracted control?

**Q4 — reference images for identity.** How are reference images attached on this path, how many
does it accept, and does supplying **several true orthographic views** of one subject help or
hurt versus one frontal reference? (We can supply 8.) If Cloud's `Wan2.2-Animate` "animate a
still with a driving video" mode is a better fit for *our* shape — where the driving video is a
**clean CG render we authored** rather than filmed footage — say so.

**Q5 — frame/resolution legality on the live nodes.** Confirm or correct: dims divisible by 16,
frame count 4n+1, and the resolution buckets that are actually native rather than merely
accepted. A frame that is one pixel off decodes short and breaks every downstream pairing for us,
so we would rather over-verify this one.

**Q6 — reproducibility.** Does a fixed seed + fixed payload on this Cloud path return
bit-identical video, or is there nondeterminism we must measure a noise floor against before
reading any A/B difference? We need to know whether to budget a repeat-variance run.

---

## Optional build — only if you want it, and only under these rules

If you'd like to stand up a starting graph, we'd take **one**: the license-clean Wan control-video
path wired for a folder of pre-rendered control frames plus a reference image, at a legal frame
size. If you build, these eight rules are binding and are stated because holes in a previous
spec — not your freelancing — cost us work:

1. **Tabs** — new, empty tabs only. Never open, edit, repurpose, rename or overwrite an existing
   tab, however much it looks like a draft. Assume every tab holds work.
2. **Out of tabs → STOP.** Never reuse or clear one to make room. Partial delivery is fine.
3. **Never delete or rewire a node in a graph you did not create this session.** Report what
   looks broken and leave it alone; it may be deliberate.
4. **Named models/nodes are NOT substitutable.** Unavailable, deprecated, or you think something
   is better → stop and ask. A silent swap is a different deliverable.
5. **Exact names, saved.** Graphs are addressed by name later; a renamed graph is lost.
6. **Build only what is listed.** No adjacent tidying.
7. **Report precisely** — tabs created, nodes added, anything left alone under rule 3, and any
   deviation stated at the TOP of the reply.
8. **Halt conditions** — missing named model, wiring the named node won't accept, a template with
   baked-in settings that contradict the stated config, or anything touching existing work.
   *(Your catch last time that two templates shipped with a Lightning 4-step LoRA and cfg-1 baked
   in — which would have silently fought our config — is exactly what rule 8 exists to produce.
   That was a real save.)*

**Feedback from last consult, since results are more useful to you than questions:** your depth
schedule 0.80/0.0/0.45 was tested against five approved plates and **confirmed** — closer on both
metrics than our 0.65/0.0/0.70, and authored layout adherence held despite releasing control at
0.45. Adopted as standing. Your Q7 *inference-side* levers (shift 3.1 → 4.5 → 6.0, partial-denoise
0.6) were **falsified** — all four came back clean photoreal, no house style. Your own mechanism
explanation predicts that, though: if the LoRA's delta is ~zero off the scene manifold, no
scheduling change moves the latent onto it. Good mechanism, wrong fallback; your recommendation
#1 was the right answer and is what we built.
