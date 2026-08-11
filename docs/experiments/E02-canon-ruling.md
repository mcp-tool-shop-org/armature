> **E02 is closed. Read [E02-closing-ruling.md](E02-closing-ruling.md) first — this
> document is retained for its corrections and is not the current statement.**

# E02 — canon ruling: the reference plates and the mesh are the same character

**Director's ruling, 2026-08-10.** Asked whether `blackguard_apose_{0..3}.png` depict the same
man as the mesh E02 renders control from, the Director looked at the sheet and ruled them
**the same man.**

Evidence sheet: [E02-identity-sheet.png](../assets/E02-identity-sheet.png).

This is canon, not a measurement. No metric was consulted and none should be — whether the
figure on screen is the right character is a ground truth the Director holds, and this repo has
twice recorded the cost of substituting a measurable proxy for that question.

## What the sheet showed, and why it is built the way it is

Three reference plates beside the mesh at **frame 25**, chosen because it carries the widest
silhouette of the 33-frame orbit (226 px against the narrowest at 112 px) and is therefore the
most frontal — a fair match to the plates' A-pose.

**The first version of this sheet was wrong and is worth recording.** It used frame 0, which is
near-profile. A side-on silhouette against four frontal plates is not a comparison; it is an
invitation to a false negative. The fix was to derive the frontal frame from the mask widths
rather than assume frame 0 was representative.

Carrying across the sheet: the horned helm, the tattered cape to mid-calf, segmented pauldrons,
splayed-finger gauntlets, and a ragged hem. The **mask** panel is the clearest single piece of
evidence — the two curved horns and the torn skirt read as the plate's silhouette with no
texture involved at all.

## Two limits stated rather than glossed

1. **This is a FORM comparison only.** The mesh is untextured. The plates are near-black armour
   with warm metal horns, and nothing in a normal/mask/edge render can confirm or deny colour,
   material or surface detail. Identity below the level of silhouette and major forms is
   **not** covered by this ruling.
2. **The poses differ slightly.** The plates hold the arms lower and closer to the body; the mesh
   is a wider A. Irrelevant to identity, but it means the reference stack and the control
   sequence are not showing the same pose — a different axis, and one that matters for E05's
   reference conditioning.

## Amendment to E02 — a pre-registered alternative hypothesis

The subject occupies **226 px of the 480 px frame width** at its widest, so roughly half the
frame is empty background on either side. The portrait bucket is doing its job vertically and
the character is still small in frame.

**Ruling: the framing does NOT change for E02.** Re-framing now would mean re-rendering and
re-verifying a control sequence that has already passed G1, G2 and G4, and — more importantly —
there is no calibration for what framing is "enough", so a tighter crop would be a number picked
from nothing. Tuning before measuring is the move this repo exists to avoid.

**Instead it is pre-registered as an alternative explanation.** If the arms show control doing
nothing — that is, if A2 (no control) is indistinguishable from the better of A1a/A1b — then
**"the subject is too small in frame for the control signal to bite" is a named candidate cause
that must be checked before the thesis is called dead.** Registering it now, before the result,
is what stops it from becoming an excuse invented afterwards to explain away a negative.

A negative result remains a full success. This amendment does not soften that; it distinguishes
*the thesis failed* from *this framing failed*, which are different findings with different
consequences.
