# E07 — the skeleton: a named-bone rig on the canonical character

**Seat:** executor · **Spec written:** 2026-08-11, before the work · **Advisor rules after the
report** · **Director judges the sheet** · **Credit ceiling: 0 generations. This experiment
spends no credits.**

> ## ✅ UNBLOCKED 2026-08-11 — F01 delivered as facet E33; premise 1 carries the hash
>
> The performer exists: `E:\AI\training\facet_E33\out\performer_textured.glb`, sha256
> `9e20ea7d…b1aa`, 21,588,628 bytes, 299,956 tris, one mesh object, one embedded 4096
> atlas, terracotta register (Director's r3 ruling), **unrigged** — hash re-verified
> independently by the dispatching seat before this banner lifted. Known asset facts the
> rig work inherits: **67 interior shells, watertight false** (a TRELLIS shell asset —
> premise 5/6's measurement is exactly how skinning behaves on it), and the brush stage
> was declared not-run, so hand-interior texels are dilation fill (irrelevant to rigging).
>
> **AMENDED 2026-08-11, same day, before any work:** the subject is no longer the blackguard.
> The Director ruled the first performer comes **fresh off the facet line** — *"I want to use
> something from the facet pipeline, not an old glb"* — and he was right about the blackguard
> twice over: the audit's own §2e names a black-armoured figure as the palette that starves
> the judgment, and this spec reused it anyway. The subject is now the **F01 deliverable**
> ([F01-the-first-performer.md](../dispatches/F01-the-first-performer.md)). A rig-wide survey
> of the 284 existing GLBs (eight rendered: `outputs/E07/cast-survey/`) found no
> facet-canonical character, which is the enumeration that justifies the commission. Nothing
> else in this spec changes: the gates, the site-list rule, the probe arc and the dailies
> sheet all bind on whichever character F01 delivers.

## Trajectory

**armature is image-to-video with a GLB instead of an image** — movies, cutscenes, character
poses and movement, any footage. Every one of those requires posing the canonical character
*on purpose*, and no asset on this rig can be posed on purpose: E01 measured the blackguard's
rig importing as 30 `EMPTY` objects named `bone_0…bone_29`, **zero of 18 anatomical sites
identifiable by name**. That gap was ruled armature's blocking dependency (E03 closing,
Ruling 7), the attempt to route around it with a wire proxy failed on measurement (E06 closing,
Ruling 2), and nothing governs against closing it (E03 closing, Ruling 12). The Director named
this exact sequence: *"shouldn't there be a process of creating the skeleton before trying to
move the limbs?"*

E07 builds the skeleton. Its follow-on, E08, stages the first authored performance **of the
character** — the first frames of the actual product.

## The question

**Can the canonical character be given a rig with anatomically named bones that (a) covers the
registered site list completely, (b) preserves the rest pose, and (c) deforms without shredding
when posed** — so that authored performances are staged on *him*, not on a wire proxy?

(c) is judged by the Director on the sheet. (a) and (b) are gated in code.

## Premises — marked

| # | premise | status |
|---|---|---|
| 1 | The subject is the **F01 deliverable** — a facet-line painted character GLB from the Director-picked concept | **MEASURED 2026-08-11** — `E:\AI\training\facet_E33\out\performer_textured.glb`, sha256 `9e20ea7d800c0ffd2cff101a5e1bcc01fa13c620bbbe3ef05ae23b093547b1aa`, hash re-verified by the dispatcher; full provenance in facet E33's manifest (117 files, per-file sha256) |
| 2 | The delivered GLB carries no pre-existing rig (facet's route emits unrigged painted meshes) | **ASSUMED** — verify on import; if a rig exists, report what it is before touching it |
| 3 | No existing GLB on this rig qualifies as the subject | **MEASURED 2026-08-11** — 284 GLBs surveyed, eight rendered with stats (`outputs/E07/cast-survey/E07-cast-survey.png`); Director ruled the performer comes off the facet line, new |
| 4 | Blender 5.2 slotted-action API shape | **MEASURED** — `tools/make_test_armature.py` `_action_fcurves`, measured on this rig 2026-08-10 |
| 5 | `ARMATURE_AUTO` automatic weights produce a usable, non-shredding deform on this mesh | **ASSUMED — this is the thing the experiment measures.** UniRig's shredding of faced characters is a measured property of UniRig, not of skinning in general; whether Blender's bone-heat weighting fails the same way here is unknown |
| 6 | The delivered mesh is skinnable as imported (object count, loose parts, manifoldness) | **ASSUMED** — measure on import, report per-object stats before rigging |

## Instruments — enumerated first, one commission justified

**Enumerated in `tools/`:** `make_test_armature.py` (procedural armature + slotted-action
handling — the rhyme for this work), `stage_render.py` (renders any staged scene; E01),
`compare_runs.py`, the sheet builders. **No rigging tool exists** — grepped `tools/` for
`rig|skin|weight|bone` beyond the test armature; nothing. **COMMISSION: `tools/rig_character.py`**
— given a source GLB and a site list, builds a named-bone armature, skins the mesh, authors the
probe action, exports the rigged GLB + manifest. **Tests ride the commit.** Each fixture answers:
what would this look like if the code were wrong in the way this check exists to catch?

## The site list — registered before the first bone

E01's report is re-read at build time. **If it enumerates the 18 sites, that list governs. If it
does not, the executor registers a list before any rigging begins** (Blender humanoid
convention: hips, spine, chest, neck, head; L/R shoulder, upper_arm, forearm, hand, thigh,
shin, foot — adjusted to whatever count E01's "18" actually denotes, with the discrepancy
reported rather than reconciled silently). Either way the list is committed **before** the
first bone is placed. A site list chosen after seeing what was easy to rig is name-shopping.

## Build order

1. **Verify the watchdog** (`pwsh -NoProfile -File E:\AI\training\_watchdog_start.ps1` — live
   heartbeat confirmed) before any Blender/GPU step. It was found dead 2026-08-11.
2. Verify the F01 delivery: premise 1's hash against the file on disk; copy it into
   `outputs/E07/subject/` and work from the copy.
3. Import; measure premises 2 and 6; set scene fps **before** any animation work (E03
   closing, Ruling 9 — the fps-ordering law).
4. Build the armature: named bones per the registered list, joint heads/tails placed to the
   mesh; parent with `ARMATURE_AUTO`.
5. Author the probe action: the **E03 arm arc** — one arm, 0→90°, 33 keys at 16 fps — the same
   authored ground truth E03 used, so E08 can compare wire-control against character-control on
   a known arc. Additional probe poses at the executor's discretion, each recorded.
6. Export rigged GLB + manifest (sha256 of source, of output, site→bone map, tool version).
7. Render the deformation sheet (below) via `stage_render.py` — **PowerShell, headless, local**.

## Gates — all raise inside `rig_character.py`; none can be skipped from a shell

- **Gate N — names.** Export raises unless every registered site maps to exactly one bone with
  exactly that name. The invariant unbounded elsewhere: nothing else prevents a half-named rig
  from shipping.
- **Gate P — rest-pose fidelity.** With the armature modifier live and no pose applied, max
  vertex displacement against the source mesh ≤ **1e-4 × the mesh's own bbox diagonal**
  (bounded by the structure's own size, per the global-constant law; linear-blend skinning at
  bind pose with normalized weights should be identity, so this is tight by design). Raises on
  breach.
- **Gate P, second clause — evaluation liveness.** *(Amendment 1, 2026-08-11 — see below.)*
  Before the fidelity clause is read, a bone is posed and the mesh is re-evaluated: max vertex
  displacement must **exceed** the same threshold. Raises if it does not.
- **Gate D — determinism.** A second run from the same inputs reproduces bone heads, tails,
  parents and weights within float tolerance — compared as **parsed objects, never bytes**
  (bytes-are-not-content law). Raises on mismatch.
- **A fired gate halts the session and is reported with its evidence.** Never re-parameterize
  past one.

**Deformation under pose is deliberately NOT a gate.** Per-bone vertex-displacement stats are
reported **per structure** as diagnostics; whether the deform is acceptable — whether he still
looks like *him* when his arm is up — is the Director's, on the sheet, at his zoom. No metric
here approximates it.

## Predictions

Registered by the executor **before step 4**, blind status disclosed, **each clause
separately**: (P1) does `ARMATURE_AUTO` produce a usable deform on this mesh — usable meaning
the Director does not reject the sheet outright; (P2) does any site fail to map cleanly to the
mesh's actual topology; (P3) does Gate P hold at the stated epsilon on the first export.
A miss with its mechanism is worth more than a hit.

## The sheet — first artifact under the dailies standard (audit §5.6)

`rest pose | posed frames of the arc | insets` — **uniform panel scale, the deforming regions
(shoulder, elbow, hand, hip) inset-zoomed at 1:1, labels readable at review distance, no
internal gate states printed on it.** Rendered from the character with material and light, not
a schematic: the sheet's job is to let his eye rule on deformation in one look. Sheets locate;
full size decides.

## Out of scope

Finger and face bones; weapon bones; a retargeting library; **any generation** (zero credits —
E08's job); any write into `E:\AI\facet` or `E:\AI\training` (sources are read-only; the rigged
GLB and everything else land in armature's tree, big binaries gitignored with sha256 manifests
committed); any promotion of rigging upstream into facet's pipeline (a later Director call,
foreclosed by nothing here).

## Licence rows introduced

None. Blender 5.2.0 LTS is already mapped (`docs/license-map.md`, Services and tools — fetched
from the installed build's own licence documents). No model, weight, or preprocessor enters.

## Report

Predictions with blind status first; premises re-verified with what moved; the source-choice
record; gates with verdicts (a gate that has not run is written **NOT YET RUN**); per-structure
deformation diagnostics; the sheet; manifest hashes. **No judgement words.** The Director
decides whether the skeleton is fit to perform.

## Standards compliance

| Standard | Score | Evidence |
|---|---|---|
| PIN_PER_STEP | **2** | Source pinned by sha256; tool + spec versioned; output manifest carries the site→bone map and hashes. Not 3: no byte-replay of Blender internals is claimed, and the manifest says so |
| ANDON_AUTHORITY | **3** | Gates N/P/D raise inside the exporting tool, no skip flag; the watchdog precondition guards the GPU step |
| NAMED_COMPENSATORS | **3** | Nothing irreversible: zero credits, all outputs new files under `outputs/E07/` (`rm -r` undoes), sources opened read-only |
| DECOMPOSE_BY_SECRETS | **2** | Rigging, rendering, and measurement are separate tools; the site list is data, not code |
| UNCERTAINTY_GATED_HUMANS | **3** | The one question that matters — is the deform acceptable — goes to the Director on a sheet built for the judgment; diagnostics gate nothing |
| EXTERNAL_VERIFIER | **1** | Standing pipeline weakness, named not inflated: advisor ruling + Director's eye, a different kind of check rather than a different model family |

**14 / 18.** Sub-3 scores carry their reasons above rather than remediation theater; the two 2s
are honest ceilings for a local build experiment.

---

## Amendment 1 — 2026-08-11, after the first run halted. Executor's clause, adopted into law by the advisor.

**Gate P as originally written could not fail on this subject, and that is how the halt was
found.** The fidelity clause read a max displacement of **exactly 0.0**. That reading has two
causes and only one of them is the good one: either skinning is genuinely the identity at
bind, or the evaluated mesh never carried the armature modifier at all. **Both read 0.0.**

On this subject it was the second. `ARMATURE_AUTO` created all 17 deform vertex groups and
left every one empty — 0 of 399,140 vertices weighted — and `parent_set` reported that as an
INFO-level warning while returning success. Without a second clause, the run would have
exported a rigged GLB with all 22 names correct, a perfect rest pose and **no skinning
whatsoever**, and every gate in this spec would have reported green.

**The clause, now binding:** before the fidelity clause is read, the tool poses a deform bone
and re-evaluates the mesh. Max vertex displacement must **exceed** 1e-4 × the mesh's own bbox
diagonal. If it does not, the deform is not live and the fidelity reading is vacuous — a
perfect identity is what an unbound mesh always reports. Raises inside the tool, no skip flag.

**Why it belongs here rather than in the executor's notes:** it is *put the andon on the
direction the invariant does not bound*, applied one level deeper than the spec had it. The
fidelity clause bounds displacement from **above**. Nothing bounded it from **below**, and
zero is the value both success and total failure take. A check that cannot fail is not a check.

### Standing hazard, same date — an exit code from Blender is not a verdict

**An unhandled exception inside `blender -b -P script.py` prints its traceback and Blender
still exits 0.** Measured on this rig 2026-08-11. A caller reading `$LASTEXITCODE` — a shell
chain, a CI step, a later session's `if` — would have read this experiment's halt as a
success, which is the same defect class as a gate behind a shell `&&`.

**Binding on every Blender invocation in this repo's tools:** verify a **success sentinel in
the output** (`RIG_OK`, `MEASURE_OK`, `SHEET_OK`, `PANELS_OK`, `DIAGNOSIS_OK`, …), never the
exit code alone. Tools additionally catch their own `GateFailure`, write a `halt.json` beside
the outputs they did not produce, and call `sys.exit(2)` — a halt that returns success is not
a halt.

### Amendment 2 — 2026-08-11, advisor ruling on the halt: the arm is amended, not abandoned

**Premise 5 stays FALSIFIED and is not retried.** Bone heat is dead on this mesh as delivered;
the mechanism sweep (`tools/diagnose_bone_heat.py`) rules out bone count, seam fragmentation,
interior shells, and scale from 0.1× to 100×.

**The non-manifold repair route is NOT taken this arm.** It mutates paid-for geometry and its
UV atlas. Recorded as a fallback only.

**Two candidate bindings run instead, both through the full gated pipeline** — Gate N, Gate P
with the liveness clause, Gate D, the probe arc, and per-structure deformation diagnostics
each:

- **(a) ENVELOPE** — `ARMATURE_ENVELOPE`, measured at 100% vertex coverage in the sweep.
  Exactly what was applied is recorded in the manifest.
- **(b) RIGID-PER-SEGMENT** — procedural weights: each vertex assigned to its limb-segment
  bone by nearest bone segment, with a small blend band at the joints. The assignment rule is
  recorded in the manifest. **Rationale on the record:** the subject is a jointed clay
  mannequin. Rigid segments articulating at drawn joints are not a fallback for this
  character — they are what the character *is*.

**The Director picks the binding from the sheet. No metric picks it.** The dailies sheet
becomes a comparison sheet — rest | arc frames | 1:1 joint insets, arm (a) beside arm (b),
uniform panels, no gate states printed.

**Also accepted in the same ruling:** the site→bone disposition (18 keypoint sites + 4
structural, facial markers non-deforming); the P2 joint-versus-limb correction; and the
glTF-split-versus-welded units finding — the last two noted for the closing ruling.

### Amendment 3 — 2026-08-11, Director's catch at 1:1, and the hard gate that follows

**The Director zoomed the halt sheet's joint insets and ruled:**

> *"This looks like it's not lined up properly."*

He was right, and the measurement is not close: **the elbow pivots sat 27–28 % of the upper
arm's own length away from the mannequin's sculpted elbow balls.** Wrists 16–19 %, knees
8–10 %, shoulders 6 %, hips 4 %, ankles under 2 %.

**The named finding: placement by proportion when the subject carries its own markers.**
E07's first skeleton put the elbow at 0.44 along the arm's measured centreline because a
figure standing with straight limbs presents no *bend* to read a joint from. That reasoning
was right about silhouettes and wrong about this subject — he is a clay artist's mannequin
and he is covered in sculpted ball-joints. The balls were in the mesh the whole time.

**Instrument or subject, ruled from the spread rather than asserted.** A projection or overlay
error applies one transform to every marker and produces near-equal offsets. These differ by a
factor of **18.2** between joints, and removing the best single translation still leaves
0.0539 of error. **The subject.** The renderer was not at fault.

**The standing method for this character class, now binding:** where the subject carries a
sculpted marker, **the marker is the pivot**. Proportion heuristics are the fallback for sites
that genuinely have no marker, and every such site is named in the report rather than left to
look measured. Implemented in `armature_core/joints.py`; the offset table rides every manifest.

---

## ⛔ HARD GATE — the Director approves the skeleton before anything downstream runs

> *"Nothing moves forward until I approve the skeleton."* — Director, 2026-08-11

**Binding, and it supersedes the sequencing in the ruling above.** The two candidate bindings
of Amendment 2 — ENVELOPE and RIGID-PER-SEGMENT — **do not run** until the Director has ruled
on the skeleton-approval sheet. Neither does the probe arc, the deformation diagnostics, E08,
or anything else downstream of E07.

Consequences, so the record does not have to infer them:

- Gate P's **liveness clause is NOT YET RUN** this round *by design, not by omission* — there
  is no binding for it to be about, and a liveness reading on an unbound mesh would report on
  a thing that does not exist yet.
- The probe action is **NOT AUTHORED** — an arc on an unbound skeleton moves no geometry.
- **Deformation diagnostics are NOT YET RUN** — they require weights.
- `rig_character.py --mode=skeleton` is the mode this gate defines. `--mode=full` remains in
  the tree and runnable, and is what resumes after approval.

The approval artifact is `outputs/E07/approval/E07-skeleton-approval.png`: the figure with the
skeleton in place, and a per-joint 1:1 inset row showing every pivot **before | after** at the
same camera. No metric approximates this judgement and none is printed on the sheet.

---

## ✅ SKELETON APPROVED — 2026-08-11 — **with reservations, and the difference is on the record**

**Director, verbatim:**

> *"This looks good, but make a note to make a more detailed skeleton in the future so that we
> can move the fingers. It's approved, but I'm not really happy with it."*

**The gate lifts.** The binding arms of Amendment 2 may run.

**An approved-with-reservations is not a clean approval, and this section exists so no later
reader can flatten the two together.** The skeleton passes for what E07 asked of it — 22 named
bones, every limb pivot on its own sculpted ball. It does **not** satisfy the Director, and the
sentence that says so is quoted above rather than paraphrased into a checkmark. Anything
downstream that cites "the skeleton was approved" must carry the second half of his sentence
with it.

### Named future item — **skeleton v2: articulated fingers**

Joins the standing-notes ledger beside the **wood-grain finish** and the **not-run brush pass**.

**What it needs, honestly stated — it is not only a rig iteration:**

1. **Finger bones.** E07's registered site list puts finger and face bones explicitly out of
   scope, and the list is 18 keypoint sites + 4 structural. A hand that articulates needs a new
   registration: at minimum 3 phalanx bones × 4 fingers + 3 for the thumb per hand, which is
   **30 additional bones** and a site list roughly 2.4× the size of E07's.
2. **A hand mesh that separates the fingers, which this subject does not have.** Measured on
   this performer: the hand reads as a **mitten with a thumb** — the arm column runs unbroken
   to z = −0.2455 with no per-finger separation in any Z band, and the joint-ball search finds
   a wrist ball and nothing below it. **No rig can articulate fingers that the mesh does not
   sculpt as separate forms.** Weighting a mitten to five finger chains moves one lump five
   ways.
3. **Therefore v2 is likely an F-series mesh iteration first, and a rig iteration second.** The
   order matters: commissioning finger bones against the current mesh would produce a rig whose
   every gate passes and whose fingers cannot move — the same shape of defect as E01's
   `bone_0 … bone_29`, one level further in.

**Not scheduled here.** E07 does not open it, and nothing in E07 forecloses it.

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

## Amendment 4 — 2026-08-11: arm (c), the rigid-parts armature, on consult #5's ranking

**E07 un-parks.** Comfy Agent consult #5 ([comfy-consult-5.md](../comfy-consult-5.md), brief
[comfy-consult-5-brief.md](../comfy-consult-5-brief.md)) ranked the rigid-parts route first
**"and it's not close"**, and its load-bearing promise was calibrated on this performer before
any of it was scripted:

> full-mesh bisect, faces far from the cut: **298,366 → 298,366 with byte-identical UVs, 0
> changed, 0 missing**; 1,590 cut-band faces split to 1,980 with interpolated UVs. **PASS.**

**The arm:** a real stop-motion armature in software — separate rigid parts articulating at
the sculpted balls, **no deformation anywhere**. No armature modifier, no vertex weights.
It sidesteps every measured failure at once: no bone heat to fail silently, no manifold
requirement, no weights to blend into shards or steps.

**The consult's two shell-class prescriptions are binding:**

1. **Face assignment by spatial region, never `Separate → By Loose Parts`.** 67 interior
   shells would explode a connectivity split into 67 anatomy-free fragments. Every face —
   interior shells included — is assigned by a nearest-bone-segment test on its centroid.
2. **Collar overlap at every joint.** Each part reaches *past* the joint plane into its
   neighbour so the two interpenetrate, exactly as a physical ball-jointed armature does, and
   no gap opens under articulation. The collar is **a fixed fraction of that joint's own
   measured ball radius** — per structure, never a length in metres — recorded per joint.

**Gates, all raising inside `tools/rig_parts.py`:** PARTS accounting (every face assigned
exactly once, the part list is the registered segment list, nothing unassigned — the direction
nothing else bounds) · part↔bone registration, pre-export and on the re-imported GLB · P
(bone parenting moved nothing at bind) · **RIGID arrival** (each part lands exactly on its own
bone's rest-to-pose transform, and every part's internal distances are invariant) · D
determinism · **ATLAS untouched** (the embedded image is byte-identical in the export — for
this asset the image bytes ARE the contract, because "no re-bake" is the promise the route was
ranked on).

**Arms (a) envelope and (b) rigid-per-segment stay in the record** as the measured failures
that motivated the consult, per the Director's ruling: *"This is a hard fail."*

**E07 status:** skeleton APPROVED with its reservation intact · binding **arm (c) delivered,
awaiting the Director's eye on the joint-seam read** · arms (a) and (b) FAILED · the standing
item **skeleton v2 — articulated fingers** unchanged.
