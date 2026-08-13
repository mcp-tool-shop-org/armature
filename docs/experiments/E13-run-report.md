# E13 (re-armed) — the run report

**Executor session, 2026-08-13.** Worktree `E:\AI\armature-E13`, branch `E13-run`.
Spec: [E13-composed-route-probe.md](E13-composed-route-probe.md) with its RE-ARM
amendment. Predictions: [E13-rerun-predictions.md](E13-rerun-predictions.md), committed
at `d46d3fe` **before the probe was built and before any reference was composited**.

**This report is appended BESIDE the halt record, not over it.**
[E13-report.md](E13-report.md) and [E13-predictions.md](E13-predictions.md) are the
halt-era session's and are untouched. Nothing in either file is rewritten, rescored, or
softened by anything here.

**Nothing in this report is a judgement of output quality.** The Director's eye is the
verdict; every number here is a diagnostic and gates nothing.

---

## 0. Dispatch checks, in the order the dispatch ordered them

| check | result |
|---|---|
| `git merge origin/main` in the worktree | **done** — 23 files, docs-only as expected (translations, SECURITY/SCORECARD/SHIP_GATE, the S03 dispatch + ruling, the E13 halt ruling, licence-map and publishing edits) |
| the branched spec contains the RE-ARM amendment | **yes** — `grep -c "RE-ARM"` → 1 |
| binding documents read from `main`, not the worktree | CLAUDE.md blob `b6b9c61d…` is byte-identical between `main` and the merged worktree (the whole-file `diff` is CRLF in the checkout against LF in the object store, the same artefact the halt report recorded). Read in full: CLAUDE.md · the E13 spec with all four amendments · [E13-halt-ruling.md](E13-halt-ruling.md) · [S03-ruling.md](../dispatches/S03-ruling.md) · the S03 report from `S03-run` · E12 w2/w3 §7 |
| VRAM watchdog | **alive** at session start (heartbeat fresh, 6951/32607 MiB, 24249 below the 31200 ceiling). No GPU work ran this session — no Blender, no local weights; compositing and measurement are CPU |
| `E:\AI\armature-S03`, `E:\AI\armature-E12`, `E:\AI\training`, `E:\AI\facet` | **read only.** Nothing written to any of them |

## 1. The fresh credit re-estimate — the ordered first act

Run before anything was built and before any submission, as the dispatch requires.

| | |
|---|---|
| instrument | `estimate_credits`, template `api_wan2_7_r2v` |
| result | **106–211 credits per generation** (1 paid API node: `Wan2ReferenceVideoApi`) |
| four submissions | **424–844** |
| two submissions (the stills-only branch) | **212–422** |
| the 900-credit halt | **RAN — did not fire** under either branch |
| meter artifact | **none on this path.** The dispatch pre-ruled a `0` reading a meter artifact; this path returned the bracket, as it did for the halt-era session. The four-submission ceiling binds regardless |

Bounded the same way the halt report bounded it: this is a template-resolved figure, not an
override-exact one. The spec's pins (720P · 16:9 · duration 5) include the node's own
default duration of 5, and the per-generation bracket has not moved from the bundled
catalog's 2026-08-12 figure.

## 2. The node contract, re-measured

`Wan2ReferenceVideoApi` re-measured with `get_node`, 2026-08-13, because it is the contract
any graph is built against and a premise of this seat's own dispatch. **Byte-consistent
with the spec's premise row and with the halt report's re-measurement:** `model.prompt`,
`model.negative_prompt`, `model.resolution` ∈ {720P, 1080P}, `model.ratio` ∈ {16:9, 9:16,
1:1, 4:3, 3:4}, `model.duration` INT default 5 (min 2, max 10), `model.reference_images.
image1…image5`, `model.reference_videos.video1…video3`, `seed` INT (max 2147483647),
`watermark` BOOLEAN default false, one `VIDEO` output, `api_node: true`,
`output_node: false`.

**One measurement artefact, recorded because it nearly became a finding.** `get_node` on
five classes at once returned `LoadImage`'s `image` COMBO with an **empty** option list;
`get_node` on `LoadImage` alone returned a populated list of several hundred
content-addressed uploads. The empty list is a property of the multi-name query, not
evidence that uploads were purged. Recorded so the next seat does not read a batched query
as an outage.

---

## 3. Stage 0 — the cascade-batch probe

**Zero partner credits.** The RE-ARM amendment's deterministic branch selector: can 81
frames reach `CreateVideo` if no single `BatchImagesNode` is loaded above the cap S03's
failure implies?

### The instrument

`tools/build_cascade_payload.py` (`E13.1`) and the cascade half of
`tools/armature_core/assembly.py`, merged from `S03-run` rather than re-written — see §8.

    81 x LoadImage -> 3 x BatchImagesNode(27) -> BatchImagesNode(3)
                   -> CreateVideo(fps=16) -> SaveVideo

87 nodes, four classes, all `api_node: false`. The graph is built in-repo; the served
template is a reference, never a route.

**The cap is treated as the inference it is.** S03's error named `images.image50` as
unexpected and 8 slots executed, which reads as `image0…image49`. No submission was made
at 49, 50 or 51, so the boundary is **not located**. The cascade therefore builds to 27
and the gate's ceiling sits at 27, not at 50: a gate placed on an inferred number inherits
that number's uncertainty. The payload record carries the cap as `INFERRED … not a
measurement`, and a test pins that wording.

### Gates, before submission

| gate | status |
|---|---|
| **ASSEMBLY (paid nodes)** | **PASSED** — 87 nodes across 4 classes, all named by the allowlist, none reading as a partner class. The allowlist is the binding clause; the name pattern is a second opinion on the allowlist, and its recall is unknown and stated as such |
| **CASCADE (slot ceiling)** | **PASSED** — 4 batch nodes, largest carries 27 slots, ceiling 27. New this run; the andon points UPWARD, which is the direction the invariant does not bound |
| **CASCADE (topology)** | **PASSED** — 81 distinct `LoadImage` nodes across 3 groups in frame order, dotted slot keys, groups wired to the final batch in order, every link resolved |
| **ROUTE** | **PASSED** — 0 components, 0 seeds, 0 latents; frame legality decided on the supplied (1024, 576, 81) |
| **ROUTE / licence clause** | ran on an empty set: the graph loads **no weights**, so none can be banned. Reported for what it examined, not as a green tick |
| **ROUTE / Gate PAIR** | ran on an empty set: **no conditioning node**, so none can be unpaired |
| **Gate S (seed registration)** | **n/a — not claimed as passed.** No noise-bearing node exists in this graph, so `require_pinned_seeds=False` was passed deliberately. A green "0 seeds, all pinned" here is the vacuous shape the halt-era executor was ruled right to refuse |
| **Gate L (frame legality)** | ran on a **supplied** frame, not a graph-read one — this graph pins no latent. It decides 1024×576×81 legal for the `wan` rules; it does not check the graph |
| **Credit-ceiling halt (> 0 partner credits)** | **RAN — did not fire.** `estimate_credits` on this exact 87-node graph: *"0 credits - no paid API nodes found in this workflow"* |
| **Round-trip table** | **no new class to teach.** The cascade re-uses the five classes S03 already taught (`LoadImage`, `BatchImagesNode`, `CreateVideo`, `SaveVideo` — `BatchImagesNode` is S03's `{}` row). A test asserts every class in the built graph has a row rather than adding a row for its own sake; the table is looked up with `is None`, so an absent class halts |

### Pre-flight, recorded as a diagnostic and not as a gate

`dry_run` returned `{"status":"validated","warnings":[]}` — **zero warnings, exactly as
S03's 81-slot flat graph did before dying at execution.** It is recorded here for one
narrow reason: it is the same signal that preceded the failure this probe exists to route
around, and the standing law that a `dry_run` PASS does not prove link sanity is what
makes it a diagnostic rather than evidence.

One weak reading rides along, marked weak: zero warnings means no COMBO advisory fired on
any of the 81 upload names, which is consistent with S03's uploads still being resolvable.
Pre-flight validates against a bundled catalog that can lag the cloud, so this is
consistent-with, not established-by.

### The submission

`prompt_id` **`c3547512-a5e3-4953-9875-3313a7bce0ed`** — status `completed`, zero
warnings, zero partner credits. One output: `6a143745b3…mp4`, downloaded to
`outputs/E13/route/cascade81.mp4`, 1,118,346 bytes, sha256
`a65f0bf31ea062b773b54a4a1d32213ab70d78ca92f4dc89cb251a91134a5f16`.

### The decode comparison

`tools/measure_cascade_clip.py` (`E13.1`) against the same 81 source frames S03 pinned
(`E:\AI\armature-E12\outputs\E12\probe\w3-seed1\lossless`, read-only), with the repo's
pinned ffmpeg. Full record: `outputs/E13/route/cascade_decode_compare.json`.

| | measured |
|---|---|
| stream | **h264 (High), yuv420p (progressive), 1024×576, 1732 kb/s, 16 fps** |
| decoded frame count | **81** for 81 submitted |
| frames bit-exact against source | **0 of 81** |
| mean absolute error per frame | **2.1795 … 2.4190**; largest single-pixel delta 83 |
| gradient split, frame 0 | top-decile gradient **4.05** against flat-half **1.76** |
| gradient split, frame 40 | top-decile gradient **4.23** against flat-half **1.67** |
| frame order | **81 of 81 on the diagonal**, 0 displaced; min margin 4.599, median 6.619 |

**One honest difference from S03, not smoothed.** S03 reported 12.19 against 5.28 on
frame 0 of its 8-frame probe; this run reads 4.05 against 1.76 on the same source frame.
The *ratio* is nearly identical (2.31 against 2.30), the absolute values are not. The two
numbers come from **different instruments** — S03's was computed inline, this one by
`clipcompare.gradient_split` — and no attempt was made to reconcile them by tuning either.
Recorded as a discrepancy between instruments, not as a reproduction and not as a
contradiction. The median-formula trap S03 recorded is the standing reason a number that
nearly matches is not treated as a match.

### Predictions, scored

| id | prediction | outcome |
|---|---|---|
| Q1 | the cascade executes | **HELD** — completed, no execution error |
| Q2 | a batch node concatenates an already-batched input | **HELD** — the clause with no prior measurement |
| Q3 | 81 decoded frames | **HELD** — exactly 81 |
| Q4 | 16 fps | **HELD** — 16 fps read off the stream |
| Q5 | frame order preserved | **HELD** — 81/81 on the diagonal |
| Q6 | not bit-exact, error structured at edges | **HELD** — 0 of 81 identical; 4.05 vs 1.76 |
| Q7 | `estimate_credits` reads 0 | **HELD** — "no paid API nodes found" |

### THE BRANCH, SELECTED AND RECORDED BEFORE ANY SUBMISSION

**The probe passed.** Per the RE-ARM amendment's first branch, **E13 runs two arms × two
seeds = 4 submissions**, with A2 = the constructed VIDEO into
`model.reference_videos.video1`. Credit bracket **424–844**, halt above 900 unchanged.
The stills-only branch (2 submissions, 212–422) is **not** taken, and the ambiguous-error
halt did not arise: every clause of the probe returned a clean, classifiable result.

**What the probe does NOT settle.** Whether `reference_videos.video1` accepts a VIDEO
constructed this way **at runtime** remains the link S03 left ASSUMED. It is typed-
compatible and has never been executed. It is prediction S1, and only the first A2
submission can answer it.

---

## 4. The tier's two vacuous gates, taught

The halt ruling (R6) owed both instruments to "the first spec that arms this tier". They
ride the commit that arms it, with their fixtures.

**Gate S — `SEED_NODES` learns `Wan2ReferenceVideoApi`.** Before this the seed table knew
only the two KSampler classes, so `seeds()` returned empty on an r2v graph and
`gate_s_registration` reported *"0 noise-bearing seed(s), all pinned"* having examined
nothing. Its save-format widget indices are **read off the file the cloud converted**, not
derived — the standard the camera rows were held to — and the two readings agree:

| reading | order |
|---|---|
| `get_node` declaration order, link inputs dropped | model, prompt, negative_prompt, resolution, ratio, duration, **seed**, watermark |
| the converted file's own `widgets_values` | `["wan2.7-r2v", <prompt>, <negative>, "720P", "16:9", 5, 2026081351, "fixed", false]` |

`control_after_generate` is inserted at index 7, immediately after the seed, so `watermark`
sits at **8** and not the 7 a positional zip would give it — the third class in the table to
carry that insertion, and exactly the off-by-one the table exists to catch.

**Gate L — a hosted tier has no pixels.** The `wan` rules describe a dim multiple of 16 and
a 4n+1 frame count; this tier takes a resolution enum, a ratio enum and an integer duration,
and never receives a pixel dimension from us. `verify(hosted_tier=…)` now records the pixel
clause **INAPPLICABLE** — not passed, not skipped — and checks the tier's own constraints
instead. It is not a skip flag: an unknown tier raises, an illegal enum raises, a graph
carrying no such node raises, a graph that *does* pin a latent raises, and a `frame` passed
alongside it raises because those are two answers to one question. Five fixtures, one per
clause.

**Gate CASCADE learns its consumer.** `gate_cascade_topology` took `save_id` and asserted
`SaveVideo`; in A2 the constructed VIDEO's consumer is the generator's reference slot.
Hard-coding the save class would have left this gate silently inapplicable to the arm that
spends credits.

**The round trip, on the A1 seed-1 graph.** Saved to the cloud, fetched back, gated:
15 values compared and equal · 5 links compared, none lost and none invented · Gate S found
a real seed (`2026081351`, `control_after_generate: fixed`) and matched it to the committed
list · Gate L reported `INAPPLICABLE — hosted tier, enum clause instead`, 720P 16:9 5s legal.

**What the round trip covers and what it does not.** One graph per arm was round-tripped, not
all four: within an arm the only difference is the seed literal, and the widget row pins
exactly where the seed lands. That is a reasoned scope, not a measurement — the seed-2 graphs
were built by the same tool from the same registration and were **not** independently
round-tripped, and the A2 graph was not round-tripped at all (its 88 nodes are the probe's own
87-node cascade, byte-identical minus its `SaveVideo`, plus the two nodes A1 round-tripped).

---

## 5. A1 — the references

The four kit views, composited and looked at at full size before upload.

| slot | view | azimuth | source sha256 (manifest) | composited sha256 | upload name |
|---|---|---|---|---|---|
| image1 | `turn_0` front | 270° | `83ab99d19162b3dd…` | `037db48d7ab8cf4a…` | `da4a5a39f7099824…` |
| image2 | `turn_1` three-quarter | 315° | `f61e2071444fd8d1…` | `00fdf501f2636e9f…` | `94dee805b09756cb…` |
| image3 | `turn_2` profile | 360° | `42fd871b280bcb9a…` | `3cac8285d9f6a6c8…` | `16abe4136b8ba525…` |
| image4 | `turn_4` back | 450° | `8772ad21b6c711b3…` | `8bfe59150b2875f4…` | `dc360c75fa67a0f6…` |

Every source sha256 was recomputed and compared against `turnaround_manifest.json` in full,
not by prefix (Gate PIN). Gate ALPHA re-measured extrema (0, 255) on all four rather than
inheriting S03's manifest. Gate FLAT measured 0.159–0.260 of each frame off-plate.

**The plate: sRGB (154, 154, 157)** — `make_hole_survey.OLD_VOID_RGB`, the presentation the
Director's eye passed. Straight-alpha composite, `rgb*a + plate*(1-a)`; the submitted PNGs
carry no alpha channel, because a video VAE is RGB and raw transparency cannot reach the model.

**What the four plates show, looked at at full size, described and not judged.** All four
carry the whole figure inside the frame, head and feet unclipped, on a uniform grey ground
with no gradient and no letterbox pad. `turn_0` and `turn_4` show no unpainted patches, only
small dark speckles on limbs and torso. `turn_1` carries pale patches at the right jaw and
neck, right shoulder and upper chest, the left hip, both hands and the left foot. `turn_2`
carries them on the skull crown, along the jaw and under the chin, down the near arm and
forearm, at the hip, across the hand and on the foot. That matches S03's own inventory.

**Seeds and prompt, both committed before the first submission:**
[`specs/E13-seeds.json`](../../specs/E13-seeds.json) (`2026081351`, `2026081352`) and
[`specs/E13-prompt.json`](../../specs/E13-prompt.json). One pinned performance-led wording
using `character1`, no scene named, no quoted dialogue. The negative prompt is
`blurry, low quality, extra limbs, text overlay`, recorded verbatim — and **"watermark" is
deliberately absent from it**, so that an absent watermark has only one possible cause and
the clause asking about `watermark=false` stays measurable.

---

## 6. The four submissions

Every one at `wan2.7-r2v` · 720P · 16:9 · duration 5 · `watermark=false` · the same pinned
prompt and negative. Full payloads, slot orders, seeds, reference hashes and gate evidence:
`outputs/E13/route/E13-{arm}-seed{seed}-payload-record.json`.

| arm | seed | prompt_id | status | output sha256 | bytes |
|---|---|---|---|---|---|
| A1 | 2026081351 | `dc336bf0-8cad-495e-bc6f-f72b9284354a` | completed | `e97b2c27a3c256c2…` | 1,644,669 |
| A1 | 2026081352 | `750df69f-1011-4aef-b6f4-cbf8b7218506` | completed | `8b70fc2bcc830ce0…` | 1,515,078 |
| A2 | 2026081351 | `537fb847-12be-4a90-b2db-abe0ea4c6e25` | completed | `2dfcf0c4733403a4…` | 1,440,584 |
| A2 | 2026081352 | `d9719a23-65a1-4d9b-8a24-4ada6fb1fbad` | completed | `ce24cffb2eb9e060…` | 2,087,373 |

No platform rejection occurred on any arm, so the halt-that-arm clause never fired. **A2 seed 1
was submitted alone and its result read before seed 2 was spent** — a rejection at the video
socket would have ended the arm one submission in rather than two.

**The A2 arm carries no video upload.** `model.reference_videos.video1` is fed by the
cascade's own `CreateVideo` inside the same graph (node 420 → node 500). E02 and the E13 halt
both measured that no video loader exists on this API surface; the halt ruling's rescue was
never to upload a clip but to construct one. **S1 held: the socket accepted a constructed
VIDEO at runtime.** That is the link S03 left ASSUMED, and it is now executed rather than
typed-compatible.

### What every clip is, measured

All four: **h264 (High), yuv420p, 1280×720, 30 fps, 150 frames, 150 of 150 distinct.** A
720P 16:9 request returns a 1280×720 stream at 30 fps — read off the container, not assumed
from the request. 150 frames at 30 fps is the 5-second duration that was pinned.

---

## 7. The sheets, and what is in them

A references | output | provenance sheet per submission, built before any number below was
quoted: `outputs/E13/sheets/E13-{arm}-seed{seed}.png`. A1's reference band is the four
composited plates in slot order; A2's is four sampled frames of the constructed clip. The
provenance band derives every line from the run's own records and prints `NOT RECORDED`
where a record does not carry a field.

**Frames looked at at full size** (recorded because nothing here is described unlooked-at):
A1 s1 — 0, 37, 75, 112, 149 · A1 s2 — 0, 75, 112 · A2 s1 — 0, 100, 149 · A2 s2 — 75 ·
all four composited references · all four sheets · four sampled frames of the constructed
reference clip.

### Observations, stated as observations

**None of this is a judgement of quality or of identity. Identity is canon and the
Director's; no metric here approximates it and every number gates nothing.**

- **Material and articulation.** In every frame looked at, on all four submissions, the
  figure reads as a jointed wooden/clay lay figure: ball joints at shoulder, elbow, hip and
  knee, matte terracotta tone, bald ovoid cranium with small protruding ears.
- **Proportions.** In the frames looked at, the figure is long-limbed with a small ovoid head
  — the reference's proportion class rather than a human one. This is the clause I predicted
  would fail and it did not visibly fail; see §8.
- **The unpainted patches propagated, on both A1 seeds.** A1 s2 f75 carries pale grey patches
  at the right jaw and temple, on the shoulder, and a large one on the ribcage. A1 s1 f112
  carries one on the left flank. Their locations correspond to `turn_1` and `turn_2`'s own
  patch inventory. **This is the confound the prediction named**: a model painting a hole
  faithfully and a model failing at identity are not distinguishable by looking at the patch.
- **Worlds differ across seeds within each arm** — A1 s1 is a grey studio with a bright floor
  pool and vignette, A1 s2 a lighter grey studio with a reflective floor; A2 s1 a warm beige
  room with a visible wall/floor junction, A2 s2 a paler grey-beige room.
- **⚠ The worlds also differ BETWEEN arms, and the difference co-varies with the reference's
  own ground.** Both A1 outputs place the figure in a grey studio-like space; both A2 outputs
  place it in a warm-toned interior, and the constructed reference clip is a warm-lit bar
  scene. No scene was named in the prompt. **This is an observation on four generations with
  no measured repeat-variance floor on this tier, and it is not a causal claim** — "the grey
  plate's ground bled" and "an unspecified scene defaults to a studio" both fit it, and this
  run cannot separate them. Flagged prominently because it bears directly on R6, on the
  authored-RGBA law's composite choice, and on what a future spec would have to isolate.
- **The bar itself did not reproduce.** A2's worlds carry no crowd, no dance floor and no
  figures other than the character; the source clip's scene is a crowded bar. Warm tone
  is not the scene.
- **No watermark was visible in any frame looked at**, on any of the four.

### `measure_clip` diagnostics — they gate nothing

| clip | frames | distinct | frame-delta median | luma-delta median | mean abs vs f0 (last) | corr vs f0 (last) |
|---|---|---|---|---|---|---|
| A1 seed 1 | 150 | 150 | 1.306 | 0.237 | 48.148 | 0.183 |
| A1 seed 2 | 150 | 150 | 1.366 | 0.226 | 15.366 | 0.127 |
| A2 seed 1 | 150 | 150 | 0.616 | 0.175 | 8.296 | 0.822 |
| A2 seed 2 | 150 | 150 | 1.353 | 0.113 | 15.449 | 0.597 |

No clip froze. Beyond that these are diagnostics with no calibrated threshold on this tier
and no measured noise floor to read them against, so nothing is concluded from them.

---

## 8. Predictions, scored

Committed at `d46d3fe` before the probe was built and before any reference was composited.
Scored honestly, including the three I got wrong.

### The probe (Q1–Q7) — all seven held; scored in §3.

### A1, the stills arm

| id | prediction | outcome |
|---|---|---|
| R1 | jointed wooden/clay mannequin reads, 2 of 2 | **HELD** in every frame looked at |
| R2 | proportions **FAIL** on 2 of 2 | **WRONG.** The figure is long-limbed with a small ovoid head in every frame looked at. I predicted the human-performer training would overwrite a non-human proportion and it did not visibly do so |
| R3 | the head **FAILS** to read as the carved cranium on ≥1 of 2 | **WRONG as written.** At close range (s1 f75, f149; s2 f75) the head carries the carved brow, the protruding ears, the long straight nose and a closed curved mouth. It is modelled more softly than the reference plate and the mouth reads wider, but it does not read as a rendered human face. Whether it is the same character is his eye, not this clause |
| R4 | the unpainted patches propagate on ≥1 of 2 | **HELD, and on 2 of 2** — s2 f75 (jaw, temple, shoulder, ribcage) and s1 f112 (left flank) |
| R5 | worlds differ across seeds | **HELD** |
| R6 | the mid-grey plate does **not** become the world, 2 of 2 | **NOT SUPPORTED.** Both A1 worlds are grey studio-like spaces. The clause cannot be scored clean either way from four generations — see the ⚠ observation in §7 — so it is recorded as unresolved rather than as held or failed |
| R7 | `watermark=false` honored | **HELD** in every frame looked at |
| R8 | the kit's darker staging does not carry into the output key | **HELD** — both A1 outputs are high-key |

### A2, the clip arm

| id | prediction | outcome |
|---|---|---|
| S1 | the socket accepts a constructed VIDEO at runtime | **HELD** — both A2 submissions completed |
| S2 | material class holds, 2 of 2 | **HELD** in every frame looked at |
| S3 | proportions fail on ≥1 of 2, and on **strictly fewer** seeds than A1 | **UNSCOREABLE as written.** A1 did not visibly fail (R2), so "strictly fewer than A1" has no room below it. The comparison the clause was built to make cannot be made from this evidence, and inventing a rescoring after seeing the outputs would be the retuning CLAUDE.md forbids |
| S4 | the head fails to read as the carved cranium on ≥1 of 2 | **WRONG as written**, same reading as R3 |
| S5 | worlds differ across seeds | **HELD** |
| S6 | the source clip's bar **does not** reproduce as A2's world | **HELD** in its literal clause — no crowd, no dance floor. The warm tone is recorded separately in §7 and is not what this clause claimed |

**Three misses in one direction.** R2, R3 and S4 all predicted the tier would lose the
stylized figure's non-human structure, and in the frames looked at it did not. That is a
prediction family, not three independent misses, and it is recorded as one.

---

## 9. Uploads, cloud artifacts, and their deletes

| artifact | delete |
|---|---|
| 4 uploaded A1 reference plates (`outputs/E13/A1_refs/A1-reference-record.json`) | **no delete endpoint on this API surface** — content-addressed, inert unless a graph names them, persisting service-side (the E12 w2/w3 §7 convention) |
| 81 uploaded PNG frames, **reused from S03** — no new upload | same; S03 already recorded them. This run accepted **4** new uploads, not 85 |
| saved cloud workflow `e13-a1-seed2026081351.json` (round-trip admission only; never executed from the cloud) | delete via the workflows UI/API; owner: the executor session |
| 5 submitted jobs (1 free cascade probe, 4 paid generations) and their outputs | no delete offered by this surface |
| local `outputs/E13/**` | delete the directory; owner: the executor session |

**Disclosure, per the per-route disclosure law.** Everything in §5's compositing, every
extraction and every measurement is local. What left the rig: four authored reference plates
of the studio's character, the pinned prompt and negative, and the full payload — to Comfy
Cloud and thence to the hosted `wan2.7-r2v` partner tier. The A2 arm sent no new bytes: its
81 frames were already service-side from S03, and they are frames of a clip Comfy Cloud
generated. The trade a user of this route inherits is the one the spec's disclosure note
states — Comfy's contractual no-training clause and Alibaba's published API-tier posture on
one side, the wan.video consumer terms' training-use licence and the unseeable reseller
agreement on the other, accepted by the Director's CONDITIONAL of 2026-08-12. Every payload
pinned `watermark=false`; no watermark appeared, so the "a mark that appears stays on the
artifact" clause was not exercised.

---

## 10. The meters

| | |
|---|---|
| `estimate_credits`, template | **106–211 per generation** |
| `estimate_credits`, the exact A1 graph | **106–211** (1 paid node) — override-exact, the gap the halt report left open |
| `estimate_credits`, the cascade probe graph | **0 — no paid API nodes** |
| generations submitted | **4 of 4** (the selected branch's full ceiling) |
| estimated spend | **424–844 credits**, inside the 900 halt |
| free jobs submitted | 1 (the cascade probe) |
| uploads accepted | **4** (S03's 81 reused, not re-uploaded) |
| saved cloud workflows | 1 |
| suite, this worktree (`E13-run`) | **1112 passed, 48 skipped** |
| suite, `main` | **1005 passed, 13 skipped** |

**Both counts are reported and nothing is asserted about the gap.** This branch adds 107
tests over `main` (1005 + 107 = 1112). The 35-test skip skew between worktree and `main` is
the instrument item the halt report flagged and S03 sighted a second time at the same size;
this session did not chase it either, and nothing here depended on those 35.

---

## 11. The result, stated plainly

**The composed route ran end to end, four submissions, and the mechanical questions it was
blocked on are now answered by execution rather than by typing:**

1. **81 frames reach a VIDEO through cascaded batching**, at zero partner credits, in order,
   at the right frame count and frame rate. The S03 wall is a per-node arity limit and it is
   routed around rather than argued with.
2. **`reference_videos.video1` accepts a VIDEO constructed that way at runtime.** The r2v
   tier's video slot is reachable from this pipeline after all — the halt report's Finding 1
   said no clip of any format could reach the slot, and that was true of *uploading* one and
   is not true of *constructing* one. **That finding is corrected in place here rather than
   deleted**, and the correction is the more useful half.
3. **The tier's two gates that could not fail can now fail**, with fixtures.

**What this run does not establish, and will not be read as establishing.** Whether the
figure on screen is the same character is canon and the Director's; nothing here approximates
it. The tier's repeat-variance floor is unmeasured, so no difference quoted above has a floor
to be read against. Four generations, two seeds per arm, one prompt: the world observation in
§7 is an observation about four clips, not a property of the route. And the arm comparison the
spec was built on — stills against clip, everything else pinned — is weaker than intended for
an honest reason: the clause that was supposed to separate them (S3 against R2) had no room
below it once A1 did not fail.

**The unpainted texture patches are now measured propagating into generated output**, on both
A1 seeds. They are facet's projection-coverage arc, they were known before this run, and they
are the reason a reader of these clips cannot tell a faithful hole from an identity failure by
looking at the patch alone.
