# E03 — does the control sequence govern authored motion?

**Seat:** executor · **Spec written:** 2026-08-10, before any work · **Advisor rules after the
report** · **Director judges the sheet** · **Credit ceiling: 4 generations.**

E02 answered *does control govern placement at all* — yes — using a static mesh on a camera
orbit. That was the cheapest possible question and it used the most trivial possible scene.
**E03 asks the next one, and only the next one.**

---

## The question, and what it is not

**If the subject itself moves, does the output move with it, at the right time?**

E02's control contained exactly one kind of motion: a camera going round a stationary object.
Nothing in it asked the subject to *do* anything, so nothing tested whether the model will
follow an authored performance. This experiment authors one.

**It is NOT asking:** whether identity survives motion (that needs a character and a bone
mapping we do not have — see §Deferred), how much the model may improvise on top (that is a
strength question and is premature until authored motion exists), or anything about cuts,
length or reference stacks.

One question. That is the whole scope.

## The subject: the procedural wire armature, and why it is the right one here

`tools/make_test_armature.py` generates a wire figure from parameters, so **we know the true
3D position of every joint at every frame**. For a motion experiment that is decisive: the
ground truth is authored, not inferred.

It also sidesteps a real blocker. E02's P2b measured **0 of 4** rigged GLBs with anatomically
identifiable bones — both real rigs name theirs `bone_0…bone_29` — so we cannot currently pose
the blackguard on purpose. We can pose a figure we generated ourselves.

⚠ **This subject carries no identity** — no face, no costume. It can answer *did the structure
move as instructed* and it can say nothing about whether a character survived. That is the
correct division: E03 is about motion, identity is a later experiment with a real character.

**Thickness:** use `t030` (limb ~23 px at 480×832, measured). The bracket exists if a thin-limb
question arises; it is not this experiment's variable.

## The motion: authored to be checkable by eye, not by instrument

**The figure raises its right arm from T-pose to overhead across the 33 frames, while the camera
holds still.**

Chosen deliberately for three properties:

1. **Unambiguous.** An arm is either up or it is not. Whether the output raised it at the same
   time is answerable by looking at a sheet — **no pose estimator required**, which also keeps
   the banned-preprocessor tier out of the experiment entirely.
2. **Camera static.** E02 varied the camera; this varies the subject. **One thing changes** —
   otherwise a result could not be apportioned between camera motion and subject motion.
3. **Monotonic.** The arm goes up and does not come back, so "at the right time" is a single
   readable quantity — the frame index at which it passes horizontal — rather than a waveform.

The generator needs a small addition: a `--pose-arc` argument writing a per-frame joint pose,
plus the true per-frame joint positions into the existing `.joints.json`. Tests ride that commit.

## Arms — 3 generations, ceiling 4

| arm | control | purpose |
|---|---|---|
| **B1** | the animated control sequence | does the output follow the authored motion |
| **B2** | **no `control_video`**, same prompt, same seed | the null. E02 proved this row is not optional |
| **B3** | a **static** control sequence — the same figure, T-pose, held for all 33 frames | discriminates *"the model follows our motion"* from *"the model animates whatever it is given"* |

**B3 is the arm that makes this an experiment.** Without it, a moving output under B1 could just
be the model's habit of adding motion (which E02's A2 showed it has). If B1's arm goes up and
B3's does not, the motion came from the control.

The fourth generation stays unspent unless a gate fires and a re-run is ruled.

## Predictions — register before looking, state whether blind

- **P1** — at which frame index does the output's arm pass horizontal, against the control's?
  State the tolerance you would accept as "same time" **before** measuring.
- **P2** — does B3 (static control) produce a moving figure anyway? Predict yes/no and say why.
- **P3** — does B1's figure keep the wire-armature *look*, or does the model dress it as
  something else? *Not identity — the subject has none — but a plain observation about what the
  model does with a shape that is not a person.*

## Gates

Inherited and already built; nothing new is required:

- **Gate L** — frame legality (480×832, 4n+1). Raises inside the tool.
- **Gate B** — batch count off `BatchImagesNode`.
- **Lossless tap** — enforced by `verify_topology`; a floor cannot be measured through a codec
  by accident again.
- **Gate 0** — **control | output | reference | provenance sheet before any number is quoted.**
- **Gate C** — credits are now observable: **4 credits/generation, measured.** State the
  projected spend before submitting and halt if it exceeds 4 generations.

**The noise floor is zero on lossless frames** (E02, 3/3 pairs bit-identical), so a single run
per arm reads directly. No repeat runs are needed for the floor.

## Review artifacts

**0.5× by default** — 8 fps, same frames — and built from `lossless/`, not from re-encoded
video. The Director judges at half speed.

## Deferred, deliberately

- **A3 / Fun-Control cross-check** (from E02) — a cross-implementation check is worth most when
  there is a finding worth confirming. Deferred until there is one.
- **Identity through motion** — needs a real character and an anatomical bone mapping that no
  asset on this rig currently has. That gap is now a named prerequisite for a later experiment,
  not a blocker here.
- **Control strength** — only askable once authored motion exists. It will be, after this.

## Report

Predictions with blind/not-blind first, then the Gate 0 sheet, then measurements beside
predictions, then every gate with a verdict. A gate that did not run is written **NOT YET RUN**.
No judgement words. **A negative result — the output ignores authored motion — is a full
success and the most important thing this experiment could find.**

---

## Amendment 1 — 2026-08-10, advisor: the noise-floor justification is HALF WRONG

**Appended before E03 ran, on evidence from E02's A1b arm. It does not change E03's question,
its arms, or its ceiling — it changes what a result may be read to mean.**

The "Gates" section says:

> *"The noise floor is zero on lossless frames (E02, 3/3 pairs bit-identical), so a single run
> per arm reads directly. No repeat runs are needed for the floor."*

**The measurement is right and the inference from it is wrong.** E02 measured the floor for
**re-running the same submission** — identical payload, identical seed — and found it bit-identical,
three pairs out of three. That is a *reproducibility* floor. It is **not** the floor for **drawing a
second sample from the model**, which has never been measured on this route.

E02 A1b is why this matters. A1a and A1b differ by one operation on the control, and their timing
correlations came out +0.521 and +0.581. That gap has **zero measurement variance** — repeat runs
are bit-identical — and it is still **two numbers from two single generations**. E02's closing
ruling refused to read it as an ordering, and the same refusal binds here.

**What this changes for E03, concretely:**

1. **P1 and P2 are safe as written, because they are CATEGORICAL.** *Does the arm go up.* *At which
   frame does it pass horizontal.* A categorical difference between B1 and B3 — arm rises vs arm
   does not — is not a small numeric gap and does not need a between-generation floor to be read.
   **This is why the spec's arm design survives its own broken justification**, and it is worth
   noticing that the design was better than the reasoning offered for it.
2. **Any MAGNITUDE comparison between arms is out of bounds** on one generation each. If B1's arm
   passes horizontal at frame 18 and the control at frame 16, that two-frame gap may **not** be
   reported as "close tracking" or compared against any other arm's gap as an ordering. Report the
   numbers; do not rank them.
3. **If a result turns out to hinge on a small numeric gap, that is a HALT** — report it with its
   evidence and stop. The remedy is a measured between-generation floor, which is its own
   experiment with its own ceiling, and it is not to be improvised out of E03's spare generation.
   The fourth generation stays reserved for a fired gate, exactly as the spec says.

**Nothing measured in E02 is withdrawn by this amendment.** The zero floor stands as what it is —
the reason a lossless tap is mandatory and the reason a codec can never again be mistaken for model
variance. What is withdrawn is the sentence "a single run per arm reads directly," which is true for
a categorical read and false for a numeric one.
