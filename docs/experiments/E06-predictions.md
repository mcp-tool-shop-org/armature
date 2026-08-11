# E06 — registered predictions

**Registered 2026-08-10, before any submission to any generator and before any E06 tooling was
written.** Committed on its own so its timestamp is git's and not a seat's.

---

## Blindness disclosure — precise, because "blind" is a claim

**Blind to:** D1 and D2. Nothing has been submitted. No video model has rendered anything for E06.
D1 and D2 do not exist.

**Blind to, additionally, at the moment of writing — and this is a stronger claim than E03 could
make:** I have not yet opened a single pixel of any E06 input. I have not viewed E02's reference
plate, E03's 33 control frames, B1's output video, or A1a's output. This file was written from the
spec and from `E03-closing-ruling.md` only, before the first `ls` into any `outputs/` directory and
before `tools/build_payload.py` was read.

**NOT blind to, and each of these could bias a prediction:**

1. **Prose descriptions of both prior outputs**, from the spec and the E03 ruling: A1a is "a fully
   painted armoured knight — cape, plate, plinth, studio light, cast shadow"; B1 is "a black stick
   figure on grey" whose arm rises 85.0° while B3's does not. I know the answer for both endpoints
   of the thing I am predicting *between*. I have not seen either image.
2. **The subject's construction**, from E03's ruling: ~30 cylinders, no volume, no face, no costume,
   authored 0° → 90° right-arm raise over 33 frames at 16 fps.
3. **`strength` = 1.0 in every payload armature has ever submitted** (E03 Ruling 6), and that this
   was named there as the most likely cause of B1's passthrough. E06 does not move it, so this
   knowledge shapes my *reasoning* about why the control dominates without changing what I can
   observe.
4. **That the rigging gap is the blocking dependency** and that P2 is the clause which decides
   whether it can be routed around. Knowing what hangs on a prediction is a pressure on it; I am
   recording that pressure rather than pretending it is absent.

**I have not read `E05-control-strength.md`**, per the dispatch. It is withdrawn and was never run.

---

## The mechanism I am predicting from, stated so it can be wrong

WAN VACE takes a control video and an optional reference image on the same node. Reference-to-video
is one of the tasks it was trained for, and the composite task — *put the referenced subject into
the controlled motion* — is the one E06 is asking about. So the model plausibly **can** do this.

My reasoning splits the figure into two properties that different inputs own:

* **Outline** — at `strength` 1.0 a depth-like control pins the near/far boundary per pixel. That
  boundary **is** the silhouette. A1a's control was a solid mesh, so its control already carried a
  knight-shaped outline and the reference never had to widen one.
* **Surface** — colour, material, costume detail. The control says nothing about these, so a
  reference has room to act here without contradicting anything.

**The prediction that follows: the reference paints the tubes, it does not thicken them.** If that
is right, D1 is a thin figure wearing armour's *colours*. If it is wrong, the reference overrides
the control's outline and the answer to the whole experiment is yes.

---

## P1 — what does D1 produce?

**Categorical bucket, committed: BETWEEN.**

**Named before looking, as the spec requires:** a thin humanoid — recognisably the same stick
proportions as B1 — but no longer flat black. It carries the reference's palette and material cues:
dark metal, some specular highlight along the limb tubes, a slightly more head-like head. The
background moves from B1's flat grey toward a lit studio with a floor. **Not** a fully-bodied
armoured knight; **not** B1's bare diagram either.

**Confidence: moderate.** The competing outcome I take most seriously (~30%) is that VACE's
reference-to-video pathway is simply stronger than I am giving it credit for and D1 comes back a
properly painted knight. A third outcome (~15%) is that the reference arrives as a *ghost* — the
plate's figure visible as a separate presence, a doubled subject, or a first-frame bleed — rather
than being fused onto the control at all.

**Where I expect to be wrong if I am wrong:** here, and in the direction of the reference doing
*more* than I predict. My reasoning is built on control-dominance, and control-dominance is exactly
the belief B1 installed in me one generation ago.

## P2 — does D1's arm rise?

**Prediction: YES.** Registered on its own, not inside P1.

Reasoning: the control is byte-identical to B1's, at the same `strength` 1.0, and B1's arm rose
85.0° against a static arm's 0.062°. The reference is appearance conditioning; it is not on the
motion path. For this to come back NO, the reference would have to *suppress* motion the control is
explicitly carrying.

**Confidence: high** — the highest of the four. **The named risk, and it is real:** the reference is
a **still** A-pose plate. Video models conditioned on a still can freeze toward it. If D1 comes back
static, that is the mechanism, and it would mean a reference and an animated control are not
composable at strength 1.0 — a decisive negative, and the single most important way this prediction
can miss.

**Corollary I am also committing to:** if the arm rises, it rises on roughly B1's schedule rather
than a new one. I am not predicting a frame number; E04's floor is unmeasured and no magnitude is
readable.

## P3 — which input owns the silhouette?

**Prediction: THE CONTROL. Thin tubes.**

D1's outline stays essentially B1's: no cape, no helm bulk, no plate volume, no shoulder mass. I
will allow a few pixels of thickening — a soft edge where the model pads the cylinders into
limb-like forms — but the figure remains a thin figure, and nothing from the reference's *shape*
survives into the outline.

**This is the mechanism question and it is the one I most want to be wrong about.** If the
silhouette comes from the reference, a posable wire armature plus a reference is a working route
around the rigging gap, and armature's blocking dependency stops blocking.

**How this could fail in a way that is neither answer:** the silhouette could come from the control
in the *limbs* and from the reference in the *torso and head* — the regions where the wire subject
has the least structure to pin. A split answer is a real outcome and I am naming it in advance so
it is not retro-fitted into whichever clause it flatters.

## P4 — does naming the character in D2 change anything against D1?

**Prediction: SURFACE, NOT IDENTITY.**

Clause A — **surface: YES, it changes.** The named prompt pulls material and costume vocabulary that
the generic prompt does not, and surface is the property I have already argued the control leaves
free. Expect a shift in palette, material specificity, and possibly attempted costume detail on the
tubes.

Clause B — **identity: NO, it does not change.** Predicted separately. Two reasons: the reference is
already the strongest identity signal in D1 and the prompt is redundant with it; and there is not
enough figure — no face-sized region, no costume-carrying volume — for an identity to be *carried*
by, whatever names it. I predict neither arm produces a recognisable face.

**Confidence: low on A, moderate on B.** "Neither" is a live outcome for the whole prediction: if
the control dominates as hard as B1 suggests, the prompt may move nothing visible and D2 ≈ D1. I
considered predicting that and did not, because I think text conditioning survives control
dominance better than I think reference conditioning does — but I am recording that I nearly
predicted the opposite, so a miss here is a real miss and not a hedge cashed in.

⚠ **Clause B is not an identity ruling and cannot become one.** *Whether it is the same man* is the
Director's call. Clause B predicts only whether D2 **differs from D1** in that respect — a
difference question, answerable from the sheet. It says nothing about whether either arm succeeded.

---

## What is NOT predicted

- Whether any output is **good**, or whether the figure **is the same man**. Both are the Director's,
  off the sheet.
- Any ranking of D1 against D2, or of either against B1 or A1a, **on a magnitude**. E04's
  between-generation floor is unmeasured; a result that turns on a small numeric gap is a halt.
- Anything about control strength, control modality, rigging, frame counts, or `control_masks`.
  All out of scope.
