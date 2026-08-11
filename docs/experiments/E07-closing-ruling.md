# E07 closing ruling — the skeleton stands, the binding is provisional, and seven rounds bought five laws

**Seat:** advisor · **Ruled:** 2026-08-11 · **Spec:**
[E07-the-skeleton.md](E07-the-skeleton.md) (with Amendments 1–4 in place) · **Reports:**
E07-report.md, rounds 1–7 corrected in place · **Status: CLOSED, EXPERIMENTING** ·
**Credits: 0 spent across all seven rounds.**

## The Director's rulings, verbatim, in order

1. Skeleton: *"This looks good, but make a note to make a more detailed skeleton in the
   future so that we can move the fingers. It's approved, but I'm not really happy with it."*
2. Bindings (a) envelope and (b) rigid-per-segment: *"This is a hard fail."*
3. Arm (c) rigid parts: *"This is not a pass."*
4. QuadRemesher: *"it's not fit for the pipeline, as it isn't non-commercial safe."*
5. Arm (d) final (repair + bone heat): *"This is better, but we're far from good"* — and the
   instruction that closes this experiment into the next: put the rigged GLB through the
   pipeline for a 4-second authored shot.

**Disposition: the skeleton is APPROVED (with reservation 1 standing). The binding — arm (d),
repaired shell + bone heat, weights normalized — is ACCEPTED PROVISIONALLY for E08's purpose,
under ruling 5's words.** Quality ledger below; nothing here is promoted to CLAUDE.md.

## The deliverable E08 inherits

```
rigged GLB   E:\AI\armature-E07\outputs\E07\rig-repaired\performer_auto.glb
sha256       7f56c9ac101218db78c10aa5764b9a72a7d8b6f4b539f035b7739351ed6e2a24
             12,961,704 bytes · 114,610 verts / 147,020 faces · one shell · original atlas
             (no unwrap, no bake) · 22 named bones on measured ball centers · weights
             normalized to 1.000000 · isolation: 11 unposed bones at exactly 0.0
repaired     ...\repaired\performer_repaired.glb (unrigged shell, 8221900e…) + manifests
```

## What seven rounds measured

| route | verdict |
|---|---|
| Bone heat on the raw import | zero weights — and the round-7 five-row table settles why: **bone heat is all-or-nothing against manifoldness** (125 bad vertices in 73,684 zero all 17 bones). The glTF importer's UV-seam split alone breaks it; welding is necessary, nowhere near sufficient. Rounds 1 and 6 were both right, measuring different distances from the same cliff |
| Envelope (defaults, measured radii) | tears the figure / refused at Gate N — both in the record |
| Rigid per segment (weights) | coherent, steps at every joint — hard fail |
| Rigid parts (objects) | joints read as true ball joints; the torso inner wall rode the arm; radial bounds halved it; a limb part needs a radial bound about its own axis — made moot by (d). `rig_parts` stays runnable |
| Voxel→QuadriFlow retopo | **falsified for this character**: the voxel pass trenches the mouth at every density while global deviation reads 0.14–0.34% — a metric that cannot see the face. `rig_retopo.py` stays runnable with its measurements |
| **Repair, not resample** | **the route**: weld + one repair pass to 0/0/0 manifold at 0.40% face cost, original UVs and atlas untouched, bone heat binds fully, liveness passes, the arc arrives whole |

## Laws earned, folded here

1. **Gate P's liveness clause** (executor's addition, adopted): rest-pose fidelity reads
   perfect on an unbound mesh; every binding gate must include a can-it-move clause.
2. **A crashed `blender -b -P` exits 0.** Three live instances this arc. Every Blender
   invocation verifies a success sentinel in output, never the exit code.
3. **Bone heat is all-or-nothing against manifoldness** — and the importer's UV-seam split is
   sufficient to break it. `rig_character` welds on import unconditionally.
4. **A global deviation statistic cannot see a face.** Local features need local measurement
   or the Director's zoom — the voxel route shipped three "excellent" deviation numbers around
   a ruined mouth.
5. **The gate protects the pipeline, not the rig** (licence, Director's ruling 4): a canonical
   route stage cannot ride a proprietary paid addon regardless of seat ownership. Recorded in
   the licence map's retopo section with the advisor's wrong YES corrected in place.

**Also on the record:** the seat's three unflagged substitutions (a standing habit, twice
caught by its own gates); the export OBJ gate (no unregistered object ships — the "stray
Icosphere" was Blender's importer's hidden collection, proven not the seat's); labels on
sheets are derived from the mesh, never hand-written, after round 6 mislabelled its own
artifact.

## The quality ledger — his eye's standing debts, none blocking E08

ear-rim notches + nose speck (the 593 repaired faces — consider steering repair fill away
from face features, or a texture touch-up) · armpit/thigh-root bone-heat creases · the elbow
ball softening under bend (smooth skinning vs the mechanical ball read — a character
question) · the weak `neck` bone · **the atlas holes** (the E33 brush pass never ran — the
"tiny triangle artifacts" the Director flagged are unfilled texels, in every render since
the twins) · the wood-grain finish note · **skeleton v2: articulated fingers** (needs an
F-series hand-mesh iteration first).

## What E07 establishes

A facet-line character can be given a named-bone skeleton on its own sculpted joint markers
and a live, normalized, isolated smooth-skin binding — at zero credits, entirely local,
entirely commercially clean — sufficient to author performances for control rendering. The
quality bar for footage is the Director's, his ruling 5 stands, and E08 is where the
deliverable meets the model.
