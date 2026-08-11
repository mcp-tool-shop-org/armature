# E07 report — the skeleton: 22 named bones, now standing on his own sculpted joints

**Seat:** executor · **Run:** 2026-08-11 · **Spec:**
[E07-the-skeleton.md](E07-the-skeleton.md) · **Registrations:**
[E07-predictions.md](E07-predictions.md), [E07-site-list.md](E07-site-list.md), both
committed before the subject was imported once · **Credits spent: 0. Nothing went to any
cloud.** · **Advisor rules on this report; the Director rules on the sheet.**

> ## ⛔ ROUND 1 HALTED — Gate P fired, and the experiment's central premise is falsified
>
> **`ARMATURE_AUTO` produced no weights on this mesh. Not a poor deform — no deform.**
> All 17 deform vertex groups were created and every one is empty: **0 of 399,140 vertices
> carry any weight at all.** `parent_set` reports this as an INFO-level warning and returns
> success.
>
> The run stopped inside the first build pass. **No rigged GLB existed. No manifest was
> written. No export was attempted.** Gates N and D were **NOT YET RUN** — not passed.
> Record: `outputs/E07/rig/halt.json`, exit code 2.
>
> Nothing was re-parameterised to get past this.

> ## ⏸ ROUND 2 — the skeleton, corrected and standing at the Director's hard gate
>
> The advisor upheld the halt and adopted Gate P's liveness clause into law. **Then the
> Director zoomed the halt sheet's joint insets** and ruled: *"This looks like it's not
> lined up properly."* He was right, and §12 is the measurement: **the elbow pivots sat
> 27–28 % of the upper arm's own length away from the mannequin's sculpted elbow balls.**
>
> Round 2 replaced every proportion-placed limb pivot with the subject's own sculpted
> ball-joint, and ends where he gated it — *"Nothing moves forward until I approve the
> skeleton."* **No binding arm ran.** On the corrected skeleton, Gate N passes both
> clauses, Gate P's round-trip clause passes, Gate D passes. **Gate P's liveness clause is
> NOT YET RUN by design**, because nothing is bound for it to be about.
>
> Approval artifact: `outputs/E07/approval/E07-skeleton-approval.png`.

---

## 1. Predictions, scored — blind status first

All three were registered in `E07-predictions.md` and committed at `80c69e5` **before**
`tools/rig_character.py` existed, before the GLB was imported, and before any measurement of
its geometry. Blindness disclosure is in that file; the prose asset facts I was not blind to
are listed there, and the largest of them — "67 interior shells" — turns out to have been
describing a different object than the one I measured (§3, premise 6).

### P1 — does `ARMATURE_AUTO` produce a usable deform on this mesh?

| clause | registered | measured | |
|---|---|---|---|
| **A** · does the bone-heat solve complete without falling back? | **NO** — expected a reported failure for at least one bone | **failed for all 17**, 0/399,140 vertices weighted | **hit, and worse than registered** |
| **B** · does the outer skin deform coherently at shoulder and elbow? | **YES** | it does not deform at all | **miss** |
| **C** · do the 67 interior shells produce a visible artifact when posed? | **NO** | — | **VACUOUS — withdrawn, not scored** |
| **D** · does the Director reject the sheet outright? | **NO** | the Director's, on the sheet | **unresolved by construction** |

**A is a hit and its mechanism is falsified.** I registered the reason as *"67 disconnected
interior shells give the heat solve 67 opportunities to find an isolated component with no
bone inside it."* §4 measures that welding the mesh down to exactly those 67 shells still
yields zero weights, and that isolating the single outer shell still yields zero weights.
The prediction was right and the reasoning behind it was wrong, which is the less useful of
the two ways to be right.

**C is withdrawn rather than claimed.** It reads "no visible artifact", and there is none —
because nothing moves. The clause takes the same value when the deform is perfect and when
there is no deform, so it is not measuring what it was written to measure. *Grade an arm only
on what it can move.*

### P2 — does any site fail to map cleanly to the mesh's actual topology?

**Registered: YES, at least one — ranked (1) ears, (2) eyes and nose, (3) wrists.**

**Hit on the headline. Measured: 10 of the 18 registered sites have no measurable feature on
this mesh** and are placed at a fraction of their own structure's measured size, each
labelled `DERIVED(<rule>)` in the manifest rather than presented as a measurement.

| ranked | site | measured outcome | |
|---|---|---|---|
| 1 | `ear.L` / `ear.R` | no ear feature exists on the mesh | **hit** |
| 2 | `eye.L` / `eye.R` | no eye feature exists on the mesh | **hit** |
| 2 | `nose` | **a nose is present and was measured** — furthest head vertex in the measured facing direction | **miss** |
| 3 | `wrist.L` / `wrist.R` | no measurable wrist — but not for the registered reason | **hit on the clause, miss on the mechanism** |
| — | `elbow.L` / `elbow.R` | no measurable elbow | **MISS — registered as "does NOT fail"** |
| — | `knee.L` / `knee.R` | no measurable knee | **MISS — registered as "does NOT fail"** |

**The registered mechanism for the wrists was "a TRELLIS hand may be a fused mitten with no
separable hand end."** The hand is present, the arm column runs to z = −0.2455, and the hand
end is measured. What is unmeasurable is the *wrist joint*, for the same reason the elbow and
knee are: **this figure stands with straight limbs, so there is no bend to find**, and a
smooth clay mannequin offers no reliable radius minimum either. I registered elbow and knee
under "what I predict does NOT fail — those are gross skeletal landmarks and any humanoid
silhouette has them." A silhouette has a *limb*; it does not have a *joint* unless the joint
is bent. That is the correction, and it is the most useful thing P2 produced.

**P2's second clause — "does a site failing to map cleanly cause Gate N to fire? NO."**
**NOT YET RUN.** Gate N is downstream of the fired gate. The distinction it registered still
holds by construction: Gate N tests names, and a bone placed at a derived position carries
its name.

### P3 — does Gate P hold at 1e-4 × bbox diagonal on the first export?

**Registered: YES, high confidence. Scored: VACUOUS, not a hit.**

Gate P's rest-pose clause recorded **max displacement exactly 0.0** against a threshold of
1.069e-4 in the `--measure-only` pass. That looks like the registered hit. It is not one:
the liveness clause added to Gate P (§5) measures that the mesh does not move when a bone is
posed, so the rest-pose reading was taken on a mesh bound to nothing. **A perfect identity is
what an unbound mesh always reports.** There was also no export, so the clause "on the first
export" has no referent.

**Both mechanisms I registered for how P3 could fail were measured and neither fired:**

1. *Unnormalised weights contracting vertices toward the origin.* Blender's armature deform
   divides by the accumulated weight, so it self-normalises; the mechanism I linked P1 clause
   A to in advance cannot produce this failure in Blender. The registered link is broken and
   is recorded as broken.
2. *Zero-weight vertices collapsed to the object origin.* Measured: Blender takes the
   harmless branch and leaves them where they are. This is why 399,140 unweighted vertices
   produce a displacement of 0.0 rather than a catastrophe.

**Gate D was registered NOT PREDICTED** — no mechanism to predict from. Status: NOT YET RUN.

---

## 2. Gates — verdicts, ROUND 1

**These are round 1's verdicts and they are left as they stood.** Round 2 re-ran the gates on
the corrected skeleton; those verdicts are in **§13** and do not overwrite these.

| gate | verdict | evidence |
|---|---|---|
| **N** — names, pre-export | **NOT YET RUN** | downstream of the fired gate |
| **N** — names, on the re-imported export | **NOT YET RUN** | no export was attempted |
| **P** — evaluation liveness | **⛔ FIRED** | max displacement **0.0** ≤ threshold 1.069e-04 across 399,140 vertices when `shoulder.L` was posed 30° |
| **P** — rest-pose fidelity | **NOT YET RUN in the gated pipeline** | recorded 0.0 in the earlier `--measure-only` pass; that reading is vacuous — see P3 |
| **D** — determinism | **NOT YET RUN** | the second build pass was never reached |

**A fired gate halts and is reported with its evidence. It was not re-parameterised past.**
The mechanism sweep in §4 changes no pipeline parameter and produced no asset; which route
E07 should take, if any, is the advisor's ruling and the Director's call.

---

## 3. Premises — re-measured, and what moved

| # | premise | status after measurement |
|---|---|---|
| 1 | subject is the F01 deliverable, sha256 `9e20ea7d…b1aa` | **HELD** — hash and byte length re-computed independently on the source (21,588,628 bytes) and again on the worktree copy; all three agree |
| 2 | the GLB carries no pre-existing rig | **HELD, now MEASURED** — 0 armatures, 0 empties, 0 actions, 0 vertex groups, 0 modifiers, one mesh object, identity world matrix |
| 3 | no existing GLB on this rig qualifies | not re-tested; outside this run |
| 4 | Blender 5.2 slotted-action API shape | **HELD** — `_action_fcurves` walked both shapes; the probe action authored 33 keys on 8 F-curves |
| 5 | `ARMATURE_AUTO` produces a usable, non-shredding deform | **⛔ FALSIFIED** — it produces **no weights at all** |
| 6 | the mesh is skinnable as imported | **MOVED, substantially — see below** |

### Premise 6 moved, and the discrepancy is a units-and-population finding, not an error

The dispatch carried **"67 interior shells, watertight false"** as a known asset fact.
Measured on the GLB as Blender imports it:

| quantity | dispatch | measured as imported | measured after merge-by-distance 1e-6 |
|---|---|---|---|
| shells | 67 | **21,514** | **67** |
| vertices | — | 399,140 | 149,643 |
| triangles | — | 299,956 | 299,956 |
| boundary edges | — | 532,074 | 165 |
| non-manifold edges | — | 532,074 | — |
| watertight | false | **false** | false |

**Both numbers are correct and they count different objects.** glTF stores attributes
per-corner, so Blender's importer splits a vertex at every UV and normal seam; the file as
loaded is 2.7 vertices per triangle and 74% of its edges are boundaries. Weld those seams and
the topology underneath is exactly the 67 shells facet E33 recorded. The dispatch's number
describes the welded surface; mine describes what `ARMATURE_AUTO` is actually handed.

This is the repo's own family — *check the unit, the population, and the object being counted*
— and it is recorded here rather than reconciled silently. **Neither number explains the
weighting failure** (§4).

---

## 4. Why bone heat failed — the mechanism sweep

Reproducible: `tools/diagnose_bone_heat.py`, output `outputs/E07/diagnosis/bone_heat_diagnosis.json`.
Every arm removes one candidate. **No arm is a pipeline stage and none produced an asset.**

| arm | mesh handed to the solve | weighted vertices | reads out |
|---|---|---|---|
| **A** as imported, all 22 bones | 399,140 v · 21,514 shells | **0 / 399,140** | the baseline |
| **B** as imported, **2 bones only** (`hips`, `spine`) | 399,140 v | **0 / 399,140** | not bone count, not this armature's layout |
| **C** same mesh, same armature, **`ARMATURE_ENVELOPE`** | 399,140 v | **399,140 / 399,140** | the mesh *can* be weighted; the failure is specific to bone heat |
| **D** welded 1e-6 → the 67-shell topology | 149,643 v · 165 boundary edges | **0 / 149,643** | **not shell fragmentation** |
| **D** welded 1e-4 | 149,622 v | **0 / 149,622** | same |
| **E** largest shell only — the outer skin alone | 73,684 v · 34 boundary · 98 non-manifold | **0 / 73,684** | **not the interior shells** |
| **F** scale 0.1× / 2× / 10× / 100× | 399,140 v | **0 in every one** | **not scale**, a known bone-heat sensitivity |

**Ruled out: bone count, armature layout, seam fragmentation, interior shells, mesh scale.**
**Not ruled out:** intrinsic geometry quality — 98 non-manifold edges survive on the isolated
outer shell, and a singular Laplacian is consistent with a heat solve that fails for every
bone at once. That candidate was not isolated further; going after it means editing the
subject's geometry, which is a change of route and not this seat's call.

**What the asset contains, measured.** Post-weld, the 67 shells are dominated by two: the
outer body (73,684 v, spanning the full figure) and a second shell of 50,605 v spanning
z ∈ [+0.026, +0.499] — **a torso-and-head-sized body inside the body, 33.8% of the mesh.**
Four more sit at the shoulders and upper arms, two at the lower legs.

---

## 5. Instrument defects found and closed during the run

Three, all recorded because the next session needs to know which parts of the record to
distrust. Each carries a regression fixture that reproduces it.

**1 · The limb tracer read raw clusters while the region map read a median-filtered count.**
On this subject, bands 109–110 merge the right arm into the torso — the arm passes within the
2%-of-width gap threshold there. The tracer returned a trunk-plus-arm blob centred at
x = −0.004 instead of the arm's −0.150; that single point added ≈0.30 of spurious arc length
to a 0.55-long limb, and `elbow.R`, placed at 0.44 along, landed at x = −0.020 — almost on the
spine, while `elbow.L` sat correctly at +0.147. **Every count and every gate stayed green.**
Fixed by dropping bands whose raw clustering disagrees with their region, plus a continuity
bound tied to each limb's own median width. After the fix the sides mirror to within 0.003 in
x. Fixture: `test_a_band_where_a_limb_touches_the_body_does_not_drag_the_joint_off_it`.

**2 · Short cluster-count runs were dropped without absorbing them into their neighbours**,
so an interrupted region became two runs and a perfectly ordinary figure read as an
unrecognisable silhouette. Fixed by absorbing then re-encoding.

**3 · Gate P as specced could not fail on this subject, and that is how the halt was found.**
The spec defines Gate P as rest-pose fidelity alone. It read exactly 0.0 — which has two
causes and only one is the good one: skinning is genuinely the identity at bind, *or* the
evaluated mesh never carried the armature. Both read 0.0. A **liveness clause** was added
inside Gate P: pose a bone, require the mesh to respond. It fired immediately. Without it,
this run would have exported a rigged GLB with all 22 names correct, a perfect rest pose, and
**no skinning whatsoever**, and every gate in the spec would have reported green.

**Also measured, and it is a hazard beyond this experiment:** an unhandled exception inside
`blender -b -P script.py` prints its traceback and **Blender still exits 0**. A caller reading
the exit code would have read this halt as a success. `rig_character.py` now writes
`halt.json` and exits 2.

---

## 6. Per-structure diagnostics

**Deformation-under-pose statistics are undefined for this run.** They require weights, and
there are none; a displacement table of 22 zeros would be a placeholder shaped like evidence.
What exists per structure is below.

### Weights, per structure — the measurement that replaced them

All 17 deform groups created, all 17 empty. Weight sum: min 0.000, mean 0.000, **399,140 of
399,140 vertices at zero**. The five registered non-deforming markers (`nose`, `eye.L/R`,
`ear.L/R`) correctly received no group, by registration.

### Bone lengths, per structure (world units; the figure stands 1.0018 tall)

| bone | length | | bone | length | | bone | length |
|---|---|---|---|---|---|---|---|
| `hips` | 0.0977 | | `shoulder.L` | 0.2694 | | `hip.L` | 0.2532 |
| `spine` | 0.0977 | | `elbow.L` | 0.1589 | | `knee.L` | 0.2395 |
| `chest` | 0.0977 | | `wrist.L` | 0.1149 | | `ankle.L` | 0.1055 |
| `neck` | 0.0501 | | `shoulder.R` | 0.2506 | | `hip.R` | 0.2415 |
| `head` | 0.1327 | | `elbow.R` | 0.1809 | | `knee.R` | 0.2555 |
| markers ×5 | 0.0243 | | `wrist.R` | 0.1707 | | `ankle.R` | 0.0905 |

### Landmark provenance, per structure — 8 measured regions, 10 derived sites

**MEASURED from a feature of this mesh:** ground and top (bbox); `crotch` z = +0.0250 (the
band where the two legs merge); `armpit` z = +0.2604 (where the arms merge into the trunk);
`neck` minimum z = +0.3431, width 0.0387, flanked above and below at ≥2× that width;
`head_base` z = +0.3681; `ankle` z = −0.4634 (where the foot flares to ≥1.6× the shin's median
width); `hand_end` z = −0.2455 (the lowest band at which an arm column exists); every limb's
x and y from its own centroid trace; `toe` and `nose` from the furthest vertex in the measured
facing direction.

**DERIVED at a fraction of the structure's own size, never of standing height:** `elbow`
(0.44 of that arm's own centreline), `wrist` (0.75 of it), `knee` (0.50 of that leg's own
hip→ankle centreline), `eye` and `ear` (fractions of that head's own half-width and height —
**no eye or ear feature is present on this mesh to measure against**), the two interior spine
joints (1/3 and 2/3 of the measured crotch→neck span), and the shoulder line's z (midpoint of
the measured armpit→neck-base span).

### Facing, measured — and it decides which arm the probe moves

`facing_y_sign = −1.0` from the toes (the feet extend 0.1163 behind the shin centre against
0.0481 in front), **so the character's left is +X**. The head cross-check agrees, on a much
smaller margin (0.0686 vs 0.0588) and is reported as advisory only.

**E03's `arm_r_raise` moves the +X-side arm** — its own docstring defines the limb that way,
as a label on a planar wire figure rather than as anatomy. On this character the +X side is
**his left**. The probe action therefore binds to `shoulder.L`, and the letter `r` in E03's
arc name does not carry over. Named rather than silently reconciled.

### Stance, measured

The feet are not symmetric: the +X foot spans y ∈ [−0.084, +0.037] and the −X foot
y ∈ [−0.028, +0.081] — **his right foot is set back and his left forward**, a walking stance,
with the ankles differing by 0.0396 in y and 0.0258 in x. The shin traces run smooth and
continuous through it, so this is the figure's pose and not a tracer artifact.

---

## 7. The site list — three discrepancies, reported not reconciled

Full registration in [E07-site-list.md](E07-site-list.md), committed before the first bone.

1. **E01's report does not enumerate the 18 sites.** Its instrument does —
   `tools/probe_glb.py::SITES`, the dict every `0 / 18` in that report was computed against.
   That list governs.
2. **E01's 18 are keypoints, not bones** — joint *locations* versus *segments*. The site→bone
   rule was fixed in advance: one bone per site, bearing that name, **head** at that location.
3. **Five of the 18 are facial**, which the spec puts out of scope. They are registered as
   `use_deform = False` markers so the naming gap closes under E01's own instrument without
   authoring any facial deformation. A reconciliation, disclosed as one.

Separately: the spec's own parenthetical humanoid convention counts **19**, not 18, and is
neither a subset nor a superset of E01's list.

**The registered diagnostic, run with E01's own matcher on E07's 22 bone names:**
**18 / 18 sites found**, none missing. E01 measured **0 / 18** on four files. It gates
nothing — Gate N is the andon and it is NOT YET RUN.

---

## 8. Artifacts

| artifact | path | sha256 | bytes |
|---|---|---|---|
| **the sheet** | `E:\AI\armature-E07\outputs\E07\sheet\E07-rig-sheet.png` | `92cf7cead4727b73a1fa3fca6a520524fa77c515fd141f8666d2339deea7792d` | 2,569,943 |
| halt record | `outputs/E07/rig/halt.json` | `cd59fdf6a3c2b3ba8683441e0ed01301e3eee4833e06785c745e1dc7250512a8` | 1,164 |
| mechanism sweep | `outputs/E07/diagnosis/bone_heat_diagnosis.json` | `670aa04295795b8770b0bc6d9db0b028302b1b681943d3720a14a4d800579c24` | 6,760 |
| premise measurements | `outputs/E07/measure/measure.json` | `daf2eb38a06c983e65098162ed1db10d7e32d80479f9df8a8525a0fcc29db49f` | 11,351 |
| subject (worktree copy) | `outputs/E07/subject/performer_textured.glb` | `9e20ea7d800c0ffd2cff101a5e1bcc01fa13c620bbbe3ef05ae23b093547b1aa` | 21,588,628 |
| **rigged GLB** | — | **NOT PRODUCED — the run halted before export** | — |
| **rig manifest** | — | **NOT PRODUCED** | — |

**The sheet** is `rest | the skeleton in place | the arc | 1:1 insets`, rendered from the
terracotta body with material and light, never as a schematic. Every camera is orthographic
and every panel in a row shares one `ortho_scale`, so a millimetre of character is the same
number of pixels across a row and the four joint insets are true 1:1, pasted at their rendered
size and never resampled. No gate state is printed on it. Frames 1 and 33 of the authored arc
sit side by side, body only.

## 9. Tests

`tests/test_sitelist.py`, `tests/test_rig_gates.py`, `tests/test_landmarks.py` — **46 new,
273 passed / 35 skipped across the whole suite.** Each gate is driven with the input it exists
to catch, and E01's measured result is used verbatim as one of them: an armature naming its
bones `bone_0 … bone_21` must fire Gate N at 0/22 mapped. Landmark derivation is tested against
a synthetic figure whose anatomy is known by construction, because the real subject has no
ground truth anywhere — if a joint were placed wrongly there, the rig would still build, Gate N
would still pass, Gate P would still read zero, and Gate D would reproduce the wrong joint
perfectly.

## 10. Standards compliance

| Standard | Score | Evidence |
|---|---|---|
| PIN_PER_STEP | **2** | source pinned by sha256 and re-computed three times; tool version and per-file tool hashes written into the manifest path; Blender build string recorded. Not 3: no byte-replay of Blender internals is claimed |
| ANDON_AUTHORITY | **3** | Gates N/P/D raise inside the tool with no skip flag; **the andon fired and the run stopped**; the halt is recorded and exits 2 |
| NAMED_COMPENSATORS | **3** | nothing irreversible: 0 credits, all outputs new files under `outputs/E07/` (`rm -r` undoes), sources opened read-only, no write into `E:\AI\facet` or `E:\AI\training` |
| DECOMPOSE_BY_SECRETS | **3** | the site list is data; landmarks, gates and the Blender driver are separate modules, the first three importable and testable without bpy; rendering and compositing split because they need different interpreters |
| UNCERTAINTY_GATED_HUMANS | **3** | the one question that matters goes to the Director on a sheet built for it; every diagnostic gates nothing; the site-list reconciliation is surfaced contrastively rather than assumed |
| EXTERNAL_VERIFIER | **1** | standing pipeline weakness, named not inflated: advisor ruling plus the Director's eye, a different kind of check rather than a different model family |

**15 / 18.**

## 11. Where this stopped

At Gate P's liveness clause, inside the first of two build passes, before Gate N, before
Gate D, before any export. **A negative result, and it is a full result:** the spec's
premise 5 — the thing E07 existed to measure — is falsified, and the mechanism sweep narrows
why to something that survives welding, shell isolation and every scale from 0.1× to 100×.

**What did stand up, measured:** 22 anatomically named bones placed from landmarks measured on
this mesh, 18/18 findable by E01's own matcher against E01's 0/18, sides mirroring to within
0.003, and the Director's sheet showing where every one of them sits inside him.

**What did not:** anything is attached to them.

Open questions belong to the advisor and the Director, not to this seat: whether E07 re-runs
on a different weighting route, whether the subject's geometry is cleaned upstream in facet,
and whether the 18-site list's five facial markers survive review.

---

# ROUND 2 — the Director's catch, and the skeleton that came out of it

## 12. The placement finding: proportion used where the subject carried markers

**The Director, at 1:1 on the halt sheet's joint insets:** *"This looks like it's not lined up
properly."* Two hypotheses were on the table and the addendum required they be discriminated
by measurement, not by reasoning: either the bones were genuinely misplaced, or the sheet's
overlay projector was wrong — the same instrument class as the tracer defect caught in §5.

### The instrument, ruled out by the shape of the error rather than by inspection

**A projection or overlay error applies one transform to every marker.** If the overlay were
the defect, every offset would be near-equal. Measured:

| quantity | value |
|---|---|
| joints matched to a sculpted ball | **12 / 12** |
| smallest offset | 0.00417 (`ankle.R`) |
| largest offset | 0.07598 (`elbow.R`) |
| **spread ratio** | **18.2 ×** |
| best single translation that would explain all of it | (−0.0000, +0.0014, +0.0221) |
| error still left after removing that translation | **0.0539** |

**Ruled: the subject.** No one transform produces an 18-fold spread. The renderer was not at
fault and was not changed.

### The offset table — verbatim, per site

Offset is the distance from the pivot as E07 first placed it to the centre of that joint's
sculpted ball. The fraction is of **that segment's own length**, never of standing height.

| site | offset | % of its segment | segment | segment length | ball radius | ball verts | matched |
|---|---|---|---|---|---|---|---|
| `shoulder.L` | 0.01643 | **6.1 %** | shoulder→elbow | 0.27057 | 0.02422 | 3495 | yes |
| `elbow.L` | 0.07398 | **27.3 %** | shoulder→elbow | 0.27057 | 0.01565 | 130 | yes |
| `wrist.L` | 0.02500 | **15.8 %** | elbow→wrist | 0.15806 | 0.01633 | 146 | yes |
| `hip.L` | 0.01022 | **4.1 %** | hip→knee | 0.24709 | 0.02424 | 289 | yes |
| `knee.L` | 0.02406 | **9.7 %** | hip→knee | 0.24709 | 0.02282 | 266 | yes |
| `ankle.L` | 0.00430 | **1.7 %** | knee→ankle | 0.24638 | 0.01695 | 151 | yes |
| `shoulder.R` | 0.01690 | **6.2 %** | shoulder→elbow | 0.27241 | 0.02413 | 3480 | yes |
| `elbow.R` | 0.07598 | **27.9 %** | shoulder→elbow | 0.27241 | 0.01534 | 123 | yes |
| `wrist.R` | 0.03102 | **19.3 %** | elbow→wrist | 0.16099 | 0.01620 | 143 | yes |
| `hip.R` | 0.01033 | **4.3 %** | hip→knee | 0.24072 | 0.02409 | 285 | yes |
| `knee.R` | 0.01986 | **8.2 %** | hip→knee | 0.24072 | 0.02295 | 278 | yes |
| `ankle.R` | 0.00417 | **1.6 %** | knee→ankle | 0.25608 | 0.01695 | 145 | yes |

The Director estimated 15–20 % from the knee inset. Measured, the knees are 8–10 % and **the
elbows are 27–28 %** — he read the right defect off a joint carrying less than half the worst
case.

### The named finding

**Placement by proportion when the subject carries its own markers.** E07's first skeleton put
the elbow at 0.44 along the arm's measured centreline because a figure standing with straight
limbs presents no *bend* to read a joint from. §1's P2 correction recorded that as "10 of 18
sites have no measurable feature," and that sentence was **wrong about this subject**: he is a
clay artist's mannequin and he is covered in sculpted ball-joints. The features existed. The
derivation looked for a bend and never asked whether the sculptor had already marked the joint.

**Standing method for this character class, now in the spec (Amendment 3):** where the subject
carries a sculpted marker, **the marker is the pivot**. Proportion is the fallback for sites
that genuinely have none, and those sites are named rather than left to look measured.

### How a ball is found, and what still has none

The joints are separate shells. Welding the glTF seam-splits collapses the file's 21,514
vertex-split shells to the asset's real **67 pieces**, and among those the joints stand out by
bbox aspect (≥ 0.58) and by residual around a least-squares sphere fit (≤ 0.20). **15
candidates** passed; **12 were claimed, each by exactly one site**, with a search radius bounded
by that segment's own length and a size window expressed as a multiple of that limb's own
measured cross-section radius — so the face's 0.006-radius pieces cannot be claimed as elbows
without a length in metres appearing anywhere.

**Sites that still carry no measured marker, named:** the torso chain (`hips`, `spine`,
`chest`), `neck`, `head`, the five facial markers (`nose`, `eye.L/R`, `ear.L/R`), and the limb
ends (`hand_end`, `toe`, `head_top`). This mannequin sculpts no ball at any of them, and their
provenance strings say so.

## 13. Round 2 gates — on the corrected skeleton

| gate | verdict | evidence |
|---|---|---|
| **N** — names, pre-export | **PASS** | 22 / 22 registered sites map to exactly one bone |
| **N** — names, on the re-imported export | **PASS** | 22 / 22, read back out of the GLB |
| **P** — round-trip positions | **PASS** | 149,643 unique positions in, 149,643 out, identical at float32; vertex count 399,140 → 399,903 |
| **P** — evaluation liveness | **NOT YET RUN** | by design: nothing is bound, so there is no deform for it to be about |
| **D** — determinism | **PASS** | two builds agree on bones, hierarchy and weights; the offset table is reproduced identically by the second build |
| probe action | **NOT AUTHORED** | an arc on an unbound skeleton moves no geometry |
| deformation diagnostics | **NOT YET RUN** | they require weights |

## 14. Two more instrument defects, both found by a gate declining to fire

**1 · A gate silently opted out, which is worse than one that fails.** Gate P's round-trip
clause selected the re-imported subject with `type == "MESH"` and skipped itself when the count
was not 1. The count is **2**: Blender's glTF importer drops a decoy `Icosphere` into a hidden
`glTF_not_exported` collection — the same decoy E01's G4 fired on, documented in
`probe_subject.py`, and walked into anyway. The manifest carried
`"P_rest_pose_round_trip": null`, and nothing downstream could tell that from a pass. Selection
is now render-visibility, and an ambiguous subject **raises**.

**2 · Gate P's fidelity clause is the wrong instrument for an export round trip.** With the
decoy filtered out it fired: 399,140 vertices in, **399,903** out. That is not damage — glTF
re-splits vertices at attribute discontinuities, and multiplicity is the exporter's business.
The property that must hold is that the **set of positions** is unchanged, and it is exactly:
149,643 unique positions both ways, identical to the last float32 bit. A new round-trip clause
compares position sets; the index-wise clause stays where vertex order genuinely is preserved,
which is the armature modifier. **The first version of that comparison was reading two
different arrays against each other, and it raised and said so rather than returning a number.**

## 15. Round 2 artifacts

| artifact | path | sha256 | bytes |
|---|---|---|---|
| **the approval sheet** | `E:\AI\armature-E07\outputs\E07\approval\E07-skeleton-approval.png` | `1cfb65a719c6518fe1391dbab6aa59d8f911779bf0a830b4cf901ac6f965e11d` | 3,379,616 |
| **skeleton GLB** | `E:\AI\armature-E07\outputs\E07\skeleton\performer_skeleton.glb` | `4ccb7837a3a93e983597906173e4dd7b71c00e83e759485b5688107af83e88ff` | 21,619,240 |
| skeleton manifest | `outputs/E07/skeleton/skeleton_manifest.json` | `0fc42e5b38ff5301583bde93d5f42ee4d66815eb17a91184bc5cc9900e0ea446` | 40,969 |
| subject (unchanged) | `outputs/E07/subject/performer_textured.glb` | `9e20ea7d800c0ffd2cff101a5e1bcc01fa13c620bbbe3ef05ae23b093547b1aa` | 21,588,628 |

**The sheet** is `the figure with the skeleton in place | before | after`. Full-body front and
side carry the skeleton over the lit terracotta body; the six joint insets are framed on the
**ball centre**, so the camera is identical in both rows and the only thing that moves between
them is the pivot. Every camera is orthographic and every panel in a row shares one
`ortho_scale`; panels are pasted at their rendered size and never resampled. The inset zoom was
widened once, before the Director saw it, because at the first zoom the *before* elbow pivot
fell outside the frame entirely — a panel showing a bone and no pivot reads as a missing render
rather than as the 27 % error it is. No gate state is printed on the sheet and no debug text.

## 16. Tests, round 2

**291 passed / 35 skipped**, 18 new. `tests/test_joints.py` drives the instrument-versus-subject
ruling in **both** directions — a uniform offset must read as the instrument and a spread must
read as the subject, because a discriminator that only ever sees one answer is not a
discriminator. It also fixes the uniqueness property (one ball cannot be claimed by two sites)
and the size window (a facial fragment near a wrist must not become the wrist pivot just
because it is round and close). `tests/test_rig_gates.py` gains the round-trip clause, driven
with the measured case: identical positions at changed multiplicity must pass, one moved
position must fire.

## 17. Where round 2 stopped

**At the Director's hard gate, with the skeleton built, gated and exported.** Round 1's halt
stands and is not reopened: premise 5 remains falsified, and no binding arm ran this round.

**Waiting on his word:** the two candidate bindings (ENVELOPE and RIGID-PER-SEGMENT), the probe
arc, the deformation diagnostics, and everything downstream of E07. The rigid-per-segment arm
will key on the measured joint boundaries this round produced, per the addendum.

**Open and not this seat's to close:** whether the corrected pivots are right by eye; whether
the torso chain, neck and head — which carry no sculpted ball — are acceptable on heuristics;
and whether the five facial markers survive review.

---

# ROUND 3 — the skeleton approved with reservations, and the two bindings run

## 18. The approval, and what it does not say

**Director, 2026-08-11, verbatim:** *"This looks good, but make a note to make a more detailed
skeleton in the future so that we can move the fingers. It's approved, but I'm not really happy
with it."*

Recorded in the spec as an **approved-with-reservations**, with the second half of the sentence
kept beside the first so no later reader can flatten them together. The named future item —
**skeleton v2: articulated fingers** — joins the standing-notes ledger beside the wood-grain
finish and the not-run brush pass, with the honest cost attached: **it is not only a rig
iteration.** Measured on this performer, the hand reads as a **mitten with a thumb** — the arm
column runs unbroken to z = −0.2455 with no per-finger separation in any Z band, and the ball
search finds a wrist ball and nothing below it. No rig articulates fingers a mesh does not
sculpt as separate forms, so v2 is likely an F-series mesh iteration first.

## 19. Three binding runs, not two — and the third is a halt

| arm | configuration | outcome |
|---|---|---|
| **(a1)** envelope, **measured** radii | head/tail radius = that structure's own measured cross-section; falloff 1.0 × it | **⛔ HALTED at Gate N** |
| **(a2)** envelope, **Blender defaults** | absolute radii, untouched — the configuration the mechanism sweep measured at 100 % coverage | all gates pass |
| **(b)** rigid per segment | nearest bone segment normalised by that bone's own radius, blend band 0.35 in normalised units | all gates pass |

### (a1) halted, and Gate N's second clause is what caught it

**`GateNNames: 1 bone(s) that no committed list registered: ['neutral_bone']`** — 22/22
registered sites mapped, plus one extra.

The mechanism, measured: envelope radii sized from the mesh leave **1,162 of 399,140 vertices
(0.29 %) with no weight at all**, all of them in the fingers and toes that stick out past every
envelope (unweighted bbox z ∈ [−0.494, −0.136], x ∈ [−0.149, +0.145]). Blender's glTF exporter
then invents a `neutral_bone` to bind them to, so the skin stays valid — and the rig ships with
a bone nobody registered holding the extremities.

**This is the clause added beyond the spec earning its keep.** Gate N as specced checks that
every registered site maps to a bone; coverage alone would have passed this export. The
unregistered-bone direction is what fired.

**Not re-parameterised past.** The envelope falloff multiple was not tuned upward until coverage
reached 100 %. Instead the arm the advisor's ruling actually named — Blender's defaults, which
is what the sweep measured at 100 % — was run as **(a2)** and reported separately.

⚑ **Flagged for the advisor:** this seat substituted measured radii for Blender's defaults on
the global-constant law **without flagging it before running**. That substitution is what moved
coverage off 100 %. Both configurations are now runnable (`--envelope-radii=measured|default`)
and both are reported; the choice of which is "arm (a)" is the advisor's, not this seat's.

## 20. Gates — per arm

| gate | (a2) envelope | (b) rigid |
|---|---|---|
| **N** pre-export | **PASS** 22/22 | **PASS** 22/22 |
| **N** on re-imported GLB | **PASS** 22/22 | **PASS** 22/22 |
| **P** rest-pose fidelity | **PASS** — max 1.68e-08 (threshold 1.069e-04) | **PASS** — max 6.21e-08 |
| **P** evaluation liveness | **PASS** — 395,711 vertices respond, max 0.02351 | **PASS** — 37,961 respond, max 0.08076 |
| **D** determinism | **PASS** | **PASS** |
| probe arc | authored — `shoulder.L`, 33 keys @ 16 fps | authored — same |

The probe is E03's arc on both: the **+X-side arm, which is measured to be the character's
LEFT**, 0°→90° about +Y, 33 keys at 16 fps.

## 21. Per-structure deformation diagnostics — DIAGNOSTIC, gating nothing

### Weights

| | (a2) envelope | (b) rigid |
|---|---|---|
| vertices with no weight | 0 | 0 |
| mean weight sum | **7.7164** | **1.0000** |
| mean bone influences per vertex | **9.86** (max 15) | 1.88 by construction |
| vertices rigid / blended | — | 330,117 / **69,023 (17.29 %)** |
| shells spanning >1 dominant bone | 679 | 577 |

### Cross-talk — bones that moved when only the LEFT ARM was authored to move

**(a2) envelope — 11 bones off the authored chain moved more than 0.01:**
`ankle.R`, `chest`, `elbow.R`, `head`, `hip.R`, `hips`, `knee.R`, `neck`, `shoulder.R`,
`spine`, `wrist.R`. The largest are `knee.L` 0.2211, `ankle.L` 0.1701, `hip.L` 0.1694,
`hip.R` 0.1054, `knee.R` 0.1054, `head` 0.0561.

**(b) rigid — one, and it is small:** `chest`, max 0.0186 with a **mean of 0.00033 and a p95 of
0.00007** — a handful of vertices inside the shoulder blend band, not the chest moving.

### Magnitude of the authored arc actually delivered

| | (a2) envelope | (b) rigid |
|---|---|---|
| whole-mesh max displacement, frame 1 → 33 (in-process) | 0.2211 | **0.7622** |
| same, measured on the re-imported GLB | 0.3699 | **0.7622** |
| `wrist.L`-dominated vertices | **49** | **5,555** |

E03 Ruling 9's family, one step over: **a gate that fires on the right axis can still be blind
to the axis that matters.** Every gate passes on (a2), and the authored 90° raise arrives as a
fraction of itself because each vertex is averaged across ~10 bones, most of which do not move.
The number is a diagnostic; the sheet is where it is judged.

## 22. ⚑ What this seat can already see, flagged rather than left to be found

The dispatching seat will examine every inset before the Director does. These are visible in
the sheet now:

1. **(a2) is torn, not merely soft.** At frames 17 and 33 the figure carries shards flying out
   of the torso and hip, the face is split down the middle, and the character's left leg is
   dislocated and broken into separate pieces. This is visible at full-body scale, not only at
   1:1.
2. **(a2)'s `hand` inset is an empty grey panel.** The camera is framed on the *authored*
   position of the wrist at frame 33 — identical in both rows by construction — and (a2)'s hand
   is not there, because that arm delivers a fraction of the arc. The panel is truthful and it
   reads like a missing render. Flagged rather than re-framed: widening the inset to find the
   hand would destroy the 1:1 the comparison depends on, and the full-body arc panels already
   show where the hand went.
3. **(b) shows a legible seam at the elbow and at the wrist.** The blend band is 0.35 in
   normalised units and 17.29 % of vertices sit in it; where two rigid segments meet, the
   transition is a visible step at 1:1 rather than a smooth bend. On a jointed mannequin that
   may be correct and it may not — it is the Director's call, and it is the single thing about
   (b) most likely to draw his eye.
4. **(b) pulls slightly at the armpit.** `chest`'s 0.0186 max is a small group of vertices at
   the shoulder boundary following the arm; visible in the `shoulder` inset as a slight drag
   where the arm meets the torso.
5. **Small dark speckles on the torso and legs are in the SOURCE asset, not the binding.** They
   appear identically in both rest-pose panels and in every earlier render of the unbound mesh.
   Named so they are not read as a binding artifact.

None of these is a verdict. The Director's eye picks the binding.

## 23. Round 3 artifacts

| artifact | path | sha256 | bytes |
|---|---|---|---|
| **the comparison sheet** | `E:\AI\armature-E07\outputs\E07\compare\E07-binding-comparison.png` | `7006ad51ad23c845e08670241a30b906030f2be238c09deef74ae52915364880` | 3,191,947 |
| **(b) rigid GLB** | `outputs\E07\bind\performer_rigid.glb` | `c5e0677e0d20f4d289ecfcd0738a803a74f4427d9e2dee645b329c96fa7bd05b` | 29,633,120 |
| **(a2) envelope GLB** | `outputs\E07\bind\performer_envelope_default.glb` | `1c134db715ec15af3a5136908617763343dc87fbf2cd1bf4a6efc9036c091457` | 29,633,120 |
| (b) manifest | `outputs\E07\bind\rig_manifest_rigid.json` | `67007a555047168873737ab91752085341bc8138728a3f4a730592a31013f02a` | 47,885 |
| (a2) manifest | `outputs\E07\bind\rig_manifest_envelope_default.json` | `458012757c7aa0860aa11cdd5d9dfd21c87c2160c6fb0c0aaac14c90da421ce4` | 51,761 |
| (a1) halt record | `outputs\E07\bind\halt.json` | `85ecdb68cf6adcfc7468c35a4f7973135aa8497f3b1030870b4436b816ec8975` | 1,047 |

**The sheet** is `rest | the arc at frames 17 and 33 | 1:1 joint insets`, arm (a) above arm (b),
uniform panels, no gate states and no debug text. Every camera is orthographic and every panel
in a row shares one `ortho_scale`. The joint insets are framed on the **posed bone position at
frame 33, read from the armature rather than from either mesh** — both arms carry the same
authored action on the same skeleton, so that point is identical in both and a difference in
where the body ends up reads as the difference it is. The builder **raises** if a re-imported
GLB comes back identical at frames 1 and 33, so a sheet can never quietly show a binding that
did not move.

## 24. The rigid arm's assignment rule, recorded

For each vertex and each deforming bone with segment `head → tail` and measured cross-section
radius `r`:

1. `d` = distance to the segment, clamped at both ends.
2. `u = d / r` — **normalised by that bone's own measured radius**, so a thin arm bone cannot
   capture torso flesh that merely happens to be nearer to it than to the thick chest bone.
3. The vertex goes to the bone with the smallest `u`. If the second-smallest belongs to a bone
   **adjacent in the hierarchy** and `u₂ − u₁ < 0.35`, the two share it:
   `w₁ = 0.5 + 0.5 (u₂ − u₁)/0.35`, `w₂ = 1 − w₁`.

**The boundary lands on the sculpted ball** because adjacent limb bones now share a head and
tail that are measured ball centres, so for near-collinear bones the surface where `u` ties is
the plane through that ball. The band is dimensionless — `u` is already divided by each
structure's own radius — so no length in metres governs it. Weights sum to **exactly 1.0** on
every vertex (measured min and max both 1.0), which is what keeps skinning the identity at bind
and is the property Gate P reads. Blend-band weights are quantised at 1e-3 and the rigid
majority is exactly 1.0; the quantisation is recorded in the manifest.

## 25. Where round 3 stopped

**Both arms are built, gated, exported and on one sheet.** The Director's eye picks the binding;
no metric here picks it, and the diagnostics in §21 gate nothing.

**Not merged.** The advisor closes E07.

**Open, and not this seat's to close:** which binding; whether (a) is worth another
configuration at all given §22.1; whether (b)'s joint seams are correct for a jointed mannequin
or want a wider blend band; and the standing item **skeleton v2 — articulated fingers**, which
needs a mesh that sculpts fingers before it needs a rig that names them.

---

## ⛔ BOTH BINDING ARMS FAILED — Director's ruling, 2026-08-11

**Director, on the binding comparison sheet, verbatim:**

> *"This is a hard fail."*

**Both arms failed at his eye.** Arm **(a2) ARMATURE_ENVELOPE** for the tearing; arm **(b)
rigid-per-segment** for the joint stepping. Neither is a route forward.

**The advisor's recommendation of (b) is OVERRULED, and it is recorded as the advisor's error.**
It graded **relative improvement** — (b) is measurably cleaner than (a2) on every diagnostic in
the report's §21 — where the question was **shippability**. A binding that is the better of two
failures is still a failure, and no diagnostic in this experiment was ever entitled to make that
call. *Metrics are diagnostics; the Director's eye is the judge.*

### E07 status

| | |
|---|---|
| **skeleton** | **APPROVED**, with the reservation recorded verbatim above (*"I'm not really happy with it"*) |
| **binding** | **UNRESOLVED — both arms failed** |
| **experiment** | **OPEN**, and PARKED |

### Parked pending an ecosystem consult

The route decision now waits on the consult's answer, not on another arm from this seat.
Brief: **`docs/comfy-consult-5-brief.md`** (on `main` once pushed).

**Explicitly NOT to be done while parked:**

- no further binding arms
- **no tuning of the blend band** — retuning a parameter after seeing the result it would be
  judged by is exactly what this repo has a law against, and the fact that (b) came close makes
  the temptation stronger, not weaker
- no merge

**What stands and does not need re-running:** the 22-bone named skeleton with every limb pivot
on its own sculpted ball; Gates N, P and D on it; the joint-ball offset table; the measured
method for this character class (*where the subject carries a sculpted marker, the marker is the
pivot*); and the standing item **skeleton v2 — articulated fingers**.

---

# ROUND 4 — arm (c): the rigid-parts armature

**E07 un-parked on Comfy Agent consult #5**, which ranked the rigid-parts route first *"and
it's not close"*, with its atlas-survives promise calibrated on this performer before any
scripting: full-mesh bisect left **298,366 of 298,366 far-from-cut faces byte-identical**, 0
changed, 0 missing.

## 26. What was built

**17 rigid parts, one per deforming bone, each bone-parented. No armature modifier, no vertex
group, no weight anywhere.** The figure articulates the way a physical ball-jointed mannequin
does, which is what this character *is*.

| quantity | value |
|---|---|
| parts | **17** |
| faces before the joint cuts | 299,956 |
| faces after | **306,110** (+6,154 created by 16 planar cuts) |
| face assignment | **plain nearest bone segment** to the face centroid — the consult's prescription |
| collar | **0.9 × that joint's own radius**, 12 of 16 joints sized from a measured sculpted ball |
| atlas | 1 embedded image, sha `e76671b5…`, **byte-identical through the route** |

### ⛔ A halt on the way in, and it was my substitution

The first run **fired Gate PARTS**: `neck` was assigned **zero of 306,110 faces**.

I had carried arm (b)'s normalisation — dividing each distance by that bone's own measured
radius — into the assignment without flagging it. That rule is right where it came from: it
stops a thin arm bone stealing torso flesh that merely happens to be nearer. **It is wrong
here**, and the mechanism is exact: the neck bone is 0.05 long and thin, sits between the
chest and the head which are both far fatter, and normalisation squeezes a short thin bone
*between two fat ones* out entirely. The consult and the dispatch both specify **plain nearest
bone segment**; that is what shipped, and both rules stay runnable behind `--assignment=`.

⚑ **This is the third time this seat has substituted a rule for the specified one without
flagging it first** — measured envelope radii in round 3, and this. The pattern is that the
substitution is always locally defensible and always unflagged. Recorded as a standing habit
to watch, not as a one-off.

## 27. Gates — all raising inside `tools/rig_parts.py`

| gate | verdict | measured |
|---|---|---|
| **PARTS** accounting | **PASS** | 306,110 faces partitioned across 17 parts, each exactly once, none unassigned, no empty part |
| **N** part↔bone, pre-export | **PASS** | 17 / 17 |
| **N** part↔bone, on the re-imported GLB | **PASS** | 17 / 17 |
| **P** bind pose | **PASS** | bone parenting moved nothing: max 4.03e-08 against 1.069e-04 |
| **RIGID** arrival | **PASS** | worst transform error **2.70e-07**, worst internal-distance change **1.25e-07**, figure max displacement **0.76223** |
| **D** determinism | **PASS** | 17 parts identical across two full builds |
| **ATLAS** untouched | **PASS** | the embedded 4096 atlas is byte-identical in the export |

**The arc arrives whole.** 0.76223 is the same figure displacement arm (b) produced — and arm
(a) delivered 0.2211 of it. Each part lands on its own bone's rest-to-pose transform to within
2.7e-07, and no part's internal distances move by more than 1.25e-07: **nothing deforms**,
measured rather than asserted.

## 28. ⚑ What this seat can already see

1. **A flat shard protrudes from the character's left armpit**, visible at full-body scale in
   frames 17 and 33 and dominating the `shoulder` inset. **Measured mechanism:** the mesh is
   double-walled and **50.84 % of all faces (152,506 of 299,956) are interior**. `shoulder.L`
   is assigned **21,664 interior faces**, 52.8 % of its total, spanning x ∈ [0.032, 0.165] and
   z ∈ [0.096, 0.313] — torso *inner wall* reaching up to **0.0638 from the shoulder bone,
   4.2× that bone's own 0.0151 radius**. When the arm swings 90°, that inner sheet rotates out
   of the torso and becomes visible. **Gate PARTS cannot see this**: the partition is
   perfectly valid, and interior geometry is assigned exactly like any other face. This is the
   single largest thing on the sheet and it is the first thing to look at.
2. **A torn, jagged seam on the chest where `shoulder.L` was taken**, visible along the left
   edge of the `shoulder` inset. The collar reaches along the *limb axis*; the shoulder/chest
   boundary on the torso surface is a broad irregular region the collar does not close.
3. **The elbow, wrist and hip insets read as ball joints** — no stepping, no tearing, no gap.
   The collar appears to be doing its job on the limb joints, which are the ones it was sized
   from.
4. **Four of 16 joints have no sculpted ball** (hips→spine, spine→chest, chest→neck,
   neck→head) and their collars fall back to that bone's own cross-section radius. Labelled
   `FALLBACK` in the manifest. None of them articulates in this probe, so the sheet does not
   test them.
5. **The dark speckles are in the source asset**, as recorded in round 3 — present in every
   render of the unbound mesh.

None of this is a verdict. The joint-seam read is the Director's.

## 29. Round 4 artifacts

| artifact | path | sha256 | bytes |
|---|---|---|---|
| **the sheet** | `E:\AI\armature-E07\outputs\E07\parts-sheet\E07-parts-armature.png` | `207f834ba7fcdb37f94a3491a0b359496ccf6142f47e686100009d7ce6a6697f` | 1,719,569 |
| **parts GLB** | `outputs\E07\parts\performer_parts.glb` | `ac46e65bc3f624f2081bb97aeea9382c5e4d8fd03b507b510f5f6cb4660f31d4` | 53,521,656 |
| manifest | `outputs\E07\parts\parts_manifest.json` | `54e146b1646145f78fbaf38f1f6c6fc06ef682eb4dc027fb37284e1d8b9e0c97` | 44,580 |

**The sheet** is `rest | frame 17 | frame 33 | 1:1 insets on the joints under articulation`.
The insets are framed on the **posed bone position at frame 33** — where the collar is doing
its work — rather than at rest, where every seam is closed by definition. Orthographic
throughout, uniform scale per row, panels never resampled, no gate states and no debug text.
The builder **raises** if a re-imported GLB sits still at frame 33, so a sheet can never
quietly show a route that did not move.

## 30. Tests, round 4

**338 pass / 35 skipped**, 32 new across `tests/test_parts.py` and `tests/test_glb.py`. The
load-bearing ones: the neck-squeeze regression (a hollow-tube fixture, because a volume-filled
one hands the neck its on-axis points for free and the defect never reproduces); Gate PARTS
fired with a face assigned to nothing and with a part left empty; the collar proven to reach
past the joint in **both** directions and to borrow nothing at zero width; and the atlas gate
fired on a single flipped byte — after two earlier versions of that fixture "changed" a byte
to the value it already held and passed while comparing a file with itself.

One real code defect was found by its own test: `joint_planes`'s no-radius branch raised
`TypeError` instead of the `ArmatureError` it exists to raise, so the failure path was broken
in exactly the case it was written for.

## 31. Where round 4 stopped

**At the Director's eye, on the joint-seam read.** The route clears every gate, the atlas is
untouched, the arc arrives whole and nothing deforms. Whether the seams read — and what to do
about the armpit shard in §28.1 — is his.

**Not merged.** The advisor closes E07.
