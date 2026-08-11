# E07 — registered predictions

**Registered 2026-08-11, before `tools/rig_character.py` was written, before the subject GLB was
imported into Blender even once, and before any measurement of its geometry was taken.**
Committed on its own so its timestamp is git's and not a seat's.

---

## Blindness disclosure — precise, because "blind" is a claim

**Blind to:** every property of the subject mesh that was not handed to me in prose. I have not
imported `performer_textured.glb`. I have not rendered it, opened it, or run `probe_glb.py` on
it. I have not looked at the cast-survey sheet, at any facet E33 output, or at any image of this
character. At the moment of writing, the only thing I have done to this file is compute its
sha256 and its byte length.

**NOT blind to, and each of these could bias a prediction:**

1. **The prose asset facts, from the spec's UNBLOCKED banner and the dispatch:** a terracotta
   clay-mannequin character, 299,956 tris, **one** mesh object, one embedded 4096 atlas,
   unrigged, **67 interior shells, watertight false**, a TRELLIS shell asset. I know the shell
   count before predicting how weighting behaves on it, and that is the single largest pressure
   on P1.
2. **That UniRig shreds faced characters** (E03 Ruling 12) — a measured limit of a different
   tool on this asset class. It is evidence about auto-rigging generally being hard here, and I
   am recording that it pushes P1 pessimistic.
3. **That the deform question is what the experiment exists to measure**, and that a
   "usable" verdict is the Director's. Knowing which prediction the experiment hangs on is a
   pressure on it.
4. **That "clay mannequin" implies a smooth featureless head.** This is the largest pressure on
   P2 and I am naming it before P2 rather than after.

**I have not read any facet E33 report, manifest, or sheet.** The only facet-side fact in my
possession is the one in the banner.

---

## The mechanism I am predicting from, stated so it can be wrong

Blender's `ARMATURE_AUTO` is **bone heat weighting** — it solves a heat-diffusion problem over
the mesh surface with each bone as a heat source, and assigns each vertex the equilibrium
distribution. Two properties of that algorithm decide everything below:

* **It is a surface-connectivity solve, not a distance solve.** Heat flows along edges. Two
  vertices a millimetre apart in space but on *different disconnected shells* exchange no heat
  at all.
* **When it cannot solve for a vertex it falls back**, historically to a nearest-bone
  assignment or to leaving the vertex unweighted, and Blender surfaces the failure as *"Bone
  Heat Weighting: failed to find solution for one or more bones"* rather than as an error.

**The subject has 67 interior shells and is not watertight.** Under the mechanism above, that is
not a cosmetic property — it is 67 pieces of geometry that may be thermally isolated from the
outer skin. Whether they are *inside* the body volume (and therefore invisible however they are
weighted) or *poking through* is the thing I cannot know without looking.

---

## P1 — does `ARMATURE_AUTO` produce a usable deform on this mesh?

**"Usable" is defined in the spec as: the Director does not reject the sheet outright.** I am
predicting the Director's rejection, not grading the mesh. Clauses predicted separately.

**Clause A — does the bone-heat solve COMPLETE without falling back?**
**Prediction: NO. It reports a failure for at least one bone.**
Reasoning: 67 disconnected interior shells give the heat solve 67 opportunities to find an
isolated component with no bone inside it. Confidence: **moderate-high**.

**Clause B — does the OUTER SKIN deform coherently at the shoulder and elbow when the arm
raises?**
**Prediction: YES.** The outer skin of a TRELLIS shell is one large connected surface, and a
single connected humanoid surface is the case bone heat was designed for. Confidence:
**moderate**. This clause is where I most expect to be wrong, and the direction I expect to be
wrong in is **worse than predicted** — specifically that the shoulder collapses or the arm
detaches, because a clay mannequin's arms may be modelled *against* the torso with the armpit
surfaces nearly touching, and bone heat bleeds weight across near-contact surfaces.

**Clause C — do the 67 interior shells produce a VISIBLE artifact when posed?**
**Prediction: NO, not visibly.** Predicted on the reasoning that interior shells are interior:
whatever they do, the outer skin occludes them. Confidence: **low-moderate**. The named failure
mode: if a shell is weighted to a different bone than the skin around it, posing pushes it
*through* the skin and it appears as a shard. I rate that ~30%.

**Clause D — overall, does the Director reject the sheet outright?**
**Prediction: NO — he does not reject it outright.** This is a conjunction of B holding and C
not firing, so it is weaker than either. Confidence: **moderate, and lower than B alone.**

## P2 — does any site fail to map cleanly to the mesh's actual topology?

**Prediction: YES — at least one site fails to map cleanly. Named in advance, in rank order of
how much I expect it:**

1. **`ear.L` / `ear.R`.** A clay mannequin is the archetype of a head with no ears. If there is
   no ear on the mesh, there is no anatomical location to place the bone head at, and the site
   maps to a *guessed* position rather than a measured one. I expect this most.
2. **`eye.L` / `eye.R` and `nose`.** Same mechanism, one step less likely — a mannequin may
   carry a nose ridge where it carries no ears.
3. **`wrist.L` / `wrist.R`.** Not because the wrist is absent but because a TRELLIS hand may be
   a fused mitten with no separable hand end to aim the tail at.

**What I predict does NOT fail:** shoulder, elbow, hip, knee, ankle, neck, and the four
structural bones. Those are gross skeletal landmarks and any humanoid silhouette has them.

**The clause I am predicting separately, because it is a different question:** does a site
failing to map cleanly cause **Gate N** to fire? **Prediction: NO.** Gate N checks *names*, not
placement quality — a bone placed at a guessed position still carries its name. A site that maps
badly is a diagnostic finding and a note on the sheet, not a gate. I am registering this
distinction in advance so a P2 hit is not later read as a gate failure, or a gate pass as a P2
miss.

## P3 — does Gate P hold at 1e-4 × bbox diagonal on the FIRST export?

**Prediction: YES.**

Reasoning, stated so it can be wrong: linear-blend skinning evaluated at the bind pose is
mathematically the identity map when the weights on each vertex sum to 1 — every bone's matrix
is its own rest matrix, so the weighted sum reduces to the vertex's original position regardless
of *what* the weights are. Rest-pose fidelity therefore does not depend on the weighting being
any good, which is why I can predict it confidently while predicting P1's clauses cautiously.
Confidence: **high**.

**The two named ways this can miss, both of which are real:**

1. **Unnormalised weights.** Vertices whose weights sum to something other than 1 — the exact
   output of a *partially failed* bone-heat solve, which is what P1 clause A predicts — do not
   reduce to the identity. A vertex weighted 0.5 total collapses halfway toward the origin.
   **If P1 clause A hits and P3 misses, this is the mechanism, and the two predictions are
   linked through it.** I am registering the link now rather than discovering it afterwards.
2. **Zero-weight vertices.** A vertex weighted to nothing may be left at its original position
   (harmless) or collapsed to the object origin (a catastrophic displacement, and it would fire
   Gate P on the first export). Which of the two Blender does, I do not know.

**A fired Gate P is a HALT, and I will report it rather than re-parameterise past it.** I am
writing that here so the commitment predates the result.

---

## What is NOT predicted

- Whether the character **is the same character** after rigging, or whether the deform is
  **good**. Both are the Director's, off the sheet. No metric here approximates either.
- Any number for per-structure deformation displacement. Those are diagnostics with no
  registered threshold, and inventing one now would be exactly the pass-condition failure this
  repo has a law about.
- Whether Gate D holds. It is a determinism check on a tool that does not exist yet; I have no
  mechanism to predict from, and a prediction with no mechanism is a coin flip wearing a
  hypothesis's clothes. **Registered as NOT PREDICTED rather than guessed.**
- Anything about generation, control sequences, strength, or E08. Out of scope, zero credits.
