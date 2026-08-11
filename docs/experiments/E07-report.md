# E07 report — the skeleton: 22 named bones stand on him, and nothing is attached to them

**Seat:** executor · **Run:** 2026-08-11 · **Spec:**
[E07-the-skeleton.md](E07-the-skeleton.md) · **Registrations:**
[E07-predictions.md](E07-predictions.md), [E07-site-list.md](E07-site-list.md), both
committed before the subject was imported once · **Credits spent: 0. Nothing went to any
cloud.** · **Advisor rules on this report; the Director rules on the sheet.**

> ## ⛔ HALTED — Gate P fired, and the experiment's central premise is falsified
>
> **`ARMATURE_AUTO` produced no weights on this mesh. Not a poor deform — no deform.**
> All 17 deform vertex groups were created and every one is empty: **0 of 399,140 vertices
> carry any weight at all.** `parent_set` reports this as an INFO-level warning and returns
> success.
>
> The run stopped inside the first build pass. **No rigged GLB exists. No manifest was
> written. No export was attempted.** Gates N and D are **NOT YET RUN** — not passed.
> Record: `outputs/E07/rig/halt.json`, exit code 2.
>
> Nothing was re-parameterised to get past this.

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

## 2. Gates — verdicts

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
