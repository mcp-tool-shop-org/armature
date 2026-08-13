# E13 (re-armed) — the executor's predictions

**Written 2026-08-13 by the re-armed executor session, before the cascade probe was
built or submitted and before any reference was composited.** They sit **beside**
[E13-predictions.md](E13-predictions.md) — the halt-era session's predictions — which are
not touched, not restated, and not scored here.

Committed at the head of this run because a prediction written after a look is not a
prediction.

## Blindness, stated exactly

**I have looked at no image and no video this session.** Not one frame of the S03
turnaround kit, not one frame of the A2 clip, not one survey sheet. Every composite,
every upload and every sheet in this run comes after this file is committed.

**I am not blind to other seats' written descriptions of the inputs.** Before writing
this I read, in full: the S03 report (which lists per-view patch locations, the
interior-mean darkness of the new set against the old, the alpha extrema, and the
coherence look), the S03 ruling, the E13 halt report, and the E13 halt ruling. So the
predictions below about *reference defects* — R4 especially — are informed by another
seat's prose, not by foresight and not by my own eye. Marked where it matters.

**Blind with respect to every output of this route.** No `wan2.7-r2v` generation exists
anywhere in this repo's record; no seat has seen one. Nothing on the output side of this
run has been seen by anyone.

**Two measurements already taken before this file, because the dispatch ordered them
first:** the fresh credit re-estimate and the `Wan2ReferenceVideoApi` node-contract
re-measurement. Their results are recorded in the report as acts, not predicted here as
foresight.

---

## Part 1 — the cascade-batch probe (Stage 0, zero partner credits)

The design under test: 81 pinned frames → three `BatchImagesNode` group nodes of 27 slots
each → one `BatchImagesNode` of 3 slots → `CreateVideo(fps=16)` → `SaveVideo`. No node
carries more than 27 auto-grow slots, against S03's inferred cap of 50.

| id | clause | prediction | reasoning |
|---|---|---|---|
| **Q1** | the cascade executes — no `unexpected keyword argument` and no execution error at any batch link | **PASSES** | S03's failure names a *keyword slot* (`images.image50`), an arity limit on the node's `execute()` signature. Nothing in that error describes tensor size, and 8 slots execute. A 27-slot node sits inside the measured-executing region |
| **Q2** | a `BatchImagesNode` accepts an input that is **already a batch** (B > 1) and concatenates rather than truncating | **CONCATENATES** | batch concatenation along dim 0 is the core semantic of this node class, and all 81 frames are identically 1024×576 so no resize path is entered. This is the clause that kills the cascade if it is wrong, and it is the one I have no direct measurement for |
| **Q3** | the produced VIDEO decodes to **exactly 81 frames** | **81** | follows Q1 ∧ Q2; stated separately so a partial concatenation (e.g. 3 frames, one per group) is scoreable as its own outcome |
| **Q4** | the decoded stream reads **16 fps** | **16 fps** | S03 measured exactly this at 8 frames through the same `CreateVideo(fps=16)` → `SaveVideo` pair |
| **Q5** | **frame order is preserved** — decoded frame *i* is nearest to source frame *i*, not to some permutation | **PRESERVED** | slot order is explicit in the payload and group order is explicit at the final node; recorded separately because a cascade is exactly where an ordering bug hides while every count still reads correctly |
| **Q6** | the decoded frames are **not** bit-exact against their sources, and the error is **structured at edges** (gradient-decile mean > flat-region mean) | **NOT bit-exact; structured** | the save path is `yuv420p`; S03 measured 12.19 against 5.28 at 8 frames. Predicted to reproduce at 81 |
| **Q7** | `estimate_credits` on the cascade graph reads **0 / no paid API nodes** | **0** | all five classes report `api_node: false` on today's `get_node`. The probe halts on anything else, so this is predicted rather than assumed |

**Branch prediction, committed:** the probe **passes**, so E13 runs **two arms × two
seeds = 4 submissions**, bracket 424–844. If Q2 is wrong I expect the failure to be
legible as structural — a type or shape error at a batch link — rather than ambiguous.
If it is ambiguous I halt, and that is not an outcome I get to steer.

---

## Part 2 — A1, the stills arm (runs under either branch)

References: four views of the S03 kit — `turn_0` front, `turn_1` three-quarter, `turn_2`
profile, `turn_4` back — RGB composited over the survey's neutral mid-grey. One pinned
performance-led prompt, `character1`, two seeds.

| id | clause | prediction | reasoning |
|---|---|---|---|
| **R1** | the generated figure reads as a **jointed wooden/clay mannequin** — material and visible articulation | **HOLDS on 2 of 2 seeds** | material class is the coarsest property in the references and the one a reference-lock tier should carry most cheaply |
| **R2** | the figure's **proportions** hold — small ovoid head on a long-limbed body, the mesh's actual shin and thigh length | **FAILS on 2 of 2 seeds** | the tier is trained on human performers; a non-human proportion is the clause I expect to separate "identity locked" from "a mannequin-flavoured person" |
| **R3** | the **head** reads as the kit's carved ovoid cranium with small protruding ears and a thin closed mouth, rather than a human face | **FAILS on at least 1 of 2 seeds** | a carved non-face is the hardest thing for a human-trained tier to preserve, and two of the four references carry unpainted patches at exactly the jaw and crown |
| **R4** | the **unpainted grey patches** on `turn_1` / `turn_2` propagate into output as blotches, material discontinuities, or a bleached limb | **APPEAR on at least 1 of 2 seeds** | **not blind** — I have read S03's per-view patch inventory, though I have not seen the views. Recorded because it is the specific confound between "the model failed at identity" and "the model painted a hole faithfully" |
| **R5** | model-decided worlds **differ** across the two seeds within the arm | **DIFFER** | the seed-volatility law, twice sighted in this repo |
| **R6** | the composite's **neutral mid-grey plate does not become the generated world** — no grey void or grey studio backdrop as the scene | **DOES NOT BLEED on 2 of 2 seeds** | these enter a *reference-image* slot, not a start-frame latent; E11's bleed came through an i2v start frame, a different mechanism. If grey backdrops appear anyway that is a finding about what this tier does with reference plates, and it is worth being wrong about in writing |
| **R7** | `watermark=false` is honored — no visible watermark on any frame | **YES** | the node's own default; no fetched clause conditions it |
| **R8** | the darker E09/E10 staging of the kit shows up as a **dark overall key** in the output world | **NO — the world's key is model-decided and unrelated to the reference's exposure** | separated from R6 because "the plate's colour bleeds" and "the plate's exposure bleeds" are different failures, and a compound would be unscoreable |

---

## Part 3 — A2, the clip arm (runs only if the probe passes)

Reference: the constructed VIDEO built from the 81 pinned frames of E12 wave-3 seed 1,
into `model.reference_videos.video1`. Same prompt, same two seeds as A1.

| id | clause | prediction | reasoning |
|---|---|---|---|
| **S1** | `reference_videos.video1` **accepts a VIDEO constructed this way at runtime** — the link S03 left ASSUMED | **ACCEPTED** | typed-compatible, and produced by a core class the same server executes. Predicted rather than assumed: this is the first time anything reaches that socket, and a rejection is a finding that ends the arm |
| **S2** | A2's figure reads as a jointed wooden/clay mannequin (material class) | **HOLDS on 2 of 2 seeds** | same reasoning as R1, with a richer signal |
| **S3** | A2's **proportions** hold | **FAILS on at least 1 of 2 seeds**, and **on strictly fewer seeds than A1** | the advisor's H-E13b expects the clip to bind; I expect it to bind *better than stills* without expecting it to bind *well*. Stated as a comparison so it stays scoreable even if both arms fail outright |
| **S4** | A2's head reads as the carved ovoid cranium rather than a human face | **FAILS on at least 1 of 2 seeds** | the source clip's own figure came apart in its late frames (E12 w3), so the reference is not uniformly clean about the head |
| **S5** | A2's model-decided worlds **differ** across the two seeds | **DIFFER** | same law as R5 |
| **S6** | the **bar interior** of the source clip reproduces as A2's world | **DOES NOT — the world is model-decided and unrelated to the clip's scene** | the slot is documented as a reference for the person or object, not a scene. If the bar comes back, the tier carries scene as well as subject, which is a larger finding than the one this arm was built to make |

---

## What separates the outcomes

**R2 ∧ R3 are the load-bearing pair for the product claim.** If both hold, the tier
carries a non-human stylized identity from four authored stills — the strongest result
available to the composed route. If R1 holds while R2 and R3 fail, the tier carries
*material* but not *character*: a much weaker claim, and one that looks nearly identical
to the strong one on a contact sheet. That is why the sheets are read at full size and
why the verdict is the Director's eye rather than any number in the report.

**S3 against R2 is the arm comparison** — reference modality is the one variable, and
that clause is the whole reason two arms exist. If the probe fails and E13 runs
stills-only, S1–S6 go unscored with the reason recorded, and the comparison the spec was
built on is not made on this tier at all.
