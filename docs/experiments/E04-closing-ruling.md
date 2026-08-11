# E04 closing ruling — the floor exists, E02's refusal is vindicated twice over, and E04 gives a unit but not a threshold

**Seat:** advisor · **Ruled:** 2026-08-10 · **Spec:**
[E04-the-between-generation-floor.md](E04-the-between-generation-floor.md) ·
**Report:** [E04-report.md](E04-report.md) · **Status:** EXPERIMENTING

## Ruling 1 — The floor is measured, and it is portable

| | C-bright | C-dark |
|---|---|---|
| **SD** | **0.1689** | **0.1571** |
| mean | 0.5400 | 0.6688 |
| range | [0.2296, 0.6933] | [0.3977, 0.8149] — **overlapping** |

**SD ratio 0.93.** Condition-dependence was pre-registered as a possible finding and **it is not
there**, so a single floor number is portable across these two conditions. That is a real result
and it was not guaranteed.

**And the two floors are different objects, which is the whole point of the experiment:** the
**fixed-seed** floor on this same statistic is **exactly zero** (E02 A0, 3/3 bit-identical); the
**between-generation** floor is **~0.16**. E02's closing ruling asserted they were different without
being able to say by how much. Now it can.

## Ruling 2 — ⭐ E02's refusal is vindicated under BOTH readings, which is stronger than either

E02 measured A1a at +0.521 and A1b at +0.581 and **declined to read the 0.0606 gap as an ordering**.
E04 tests that refusal two ways and it survives both:

**Unpaired:** 0.0606 is **0.37 SD**. Nowhere near readable.

**Paired** — and this is the reading the executor surfaced against its own prediction: A1a and A1b
ran on the **same seed**, so their difference was never two independent noise terms. It was a
*paired* difference, the low-noise quantity. The six paired differences are:

```
+0.0606   +0.1216   +0.1830   +0.1681   +0.2458   −0.0063
```

**E02's gap is the smallest positive value in that set, and the set contains a sign reversal.** So
under the paired reading, E02's 0.0606 is one draw from a distribution whose own observed range
crosses zero.

**Ruled: E02's refusal stands, and stands twice.** A single paired observation cannot establish an
ordering when the paired distribution itself contains a reversal. Had the ruling read that gap as a
result, E04 would now be retracting it.

## Ruling 3 — ⚠ E04 gives a UNIT. It does not give a THRESHOLD, and I am not inventing one.

This is the ruling most likely to be misread later, so it is stated flatly.

**What E04 licences:** any future gap between two arms is now quotable **in units of the measured
spread** — "0.37 SD" instead of "0.060, we don't know." That converts a shrug into a quantified
statement, and it is what the experiment was bought for.

**What E04 does NOT licence:** a significance test, a "counts if it exceeds N SD" rule, or any pass
condition derived from these numbers. **Inventing one here would be this repo's most expensive
recorded error** — a pass condition manufactured from a quantity measured for another purpose,
after seeing the results it would judge.

**The standing rule, unchanged:** report the gap and the spread side by side, in SD units, and the
**Director's eye rules on the artifact.** Metrics are diagnostics. E04 makes the diagnostic
honest; it does not promote it to a judge.

## Ruling 4 — Pairing is a DESIGN choice, and E04 makes it a cheap one

Measured: cross-condition correlation across seeds **r = 0.848**; paired differences vary **2.5×
less** than independence would predict (unpaired difference SD ≈ 0.231 against a paired ≈ 0.091).

**Ruled: future arm comparisons SHOULD share their seeds unless there is a reason not to.** Pairing
buys a 2.5× reduction in the noise against which a difference is read, at **zero credit cost** — it
is a line in the payload builder.

Two bounds on that, both real:

* **Pairing narrows what a result generalises to.** Arms sharing seeds are not independent samples
  of the model's behaviour; they are one sample compared two ways.
* **n=1 paired is still not enough**, per Ruling 2. The paired distribution contains a reversal at
  n=6.

**Any spec that compares arms now states, explicitly, whether its arms are paired**, because the
floor that applies depends on it and the two differ by 2.5×.

## Ruling 5 — P4b's miss is the most useful thing in the report

The executor predicted that averaging six per side would shrink the gap below E02's single-pair
0.0606. **It doubled**, to 0.1288.

The mechanism was backwards, and the executor found and reported it rather than explaining the
number away: **averaging reduces the noise on each side's mean, but the quantity E02 reported was
never a two-noise-term difference** — it was paired, and 0.0606 was the smallest of six such
differences rather than a typical one.

**A prediction that fails and returns the correct structure of the problem is worth more than a
hit.** This one reorganised how every future comparison in this repo must be designed (Ruling 4).

## Ruling 6 — ⚑ A law, from the executor's own account of its miss

The executor underestimated the spread by ~2×, and explained exactly how:

> *I had a theory estimate (~0.125) and an n=1 empirical hint (~0.054), wrote that the n=1 was
> "worth very little," and then let it pull my number to 0.08 anyway. **Theory alone would have
> landed inside its own band.***

**Adopted as a law: a datum you have declared worth very little must not move your estimate.**
Writing "this is weak evidence" and then averaging it in anyway is the opposite of what the sentence
claims to do — it launders a weak number into a strong one by acknowledging its weakness in prose
while granting it weight in arithmetic. **Either the datum counts and you defend it, or it does not
and you drop it.** Splitting the difference is the failure mode, and it cost this prediction its
band.

## Ruling 7 — The two byte-pin defects, disposed

Both are mine, both follow from Ruling 7 of E06, and the executor's finding makes the hazard worse
than I stated.

**7a — the guard is cwd-relative as well as gitignored.** It is
`os.path.isfile("outputs/E02/uploads_depth_pershot.json")` — so it skips **in CI, and from any
working directory that is not the repo root**. **Green in CI means "did not run."** My E06 ruling
prescribed committing the upload records as fixtures; that fix must **also** resolve the path
relative to the test file rather than to `cwd`, or it leaves half the hazard standing.

**7b — the pin's key says `A1a`; its bytes are `A0`'s.** A1a was submitted *before* the lossless tap
existed, carries no node 302, and **the current builder cannot emit it**. The recorded hash is A0's.
Substantively the condition is the same — A0 is A1a's condition plus the tap — but **a pin whose key
names one artifact and whose bytes are another is a mislabelled instrument**, and this repo has a
law about exactly that: *a number that reproduces exactly can still be measured against the wrong
object.* **Relabel the key to name what it actually pins**, in the commit that makes the fixture fix.

**The E04 seat did the right thing on both:** it staged E02's uploads *before its first commit*
because it saw the guard, verified the pin **ran** rather than trusting a green suite, and reported
the label defect rather than renaming a key on a shared surface.

## Ruling 8 — A published attribution is CORRECTED IN PLACE

The commissioned instrument's anchor found it: **E02's `+0.521` was computed on A0r1's *lossless*
frames, not on A1a's own.** A1a predates the lossless tap; its H.264 frames read **+0.545**.

**The number is valid for the condition it measured** — A0 is A1a's condition plus the tap — **and
the attribution was wrong.** Every armature document quoting `+0.521` as "A1a's" should be read as
*A1a's condition, measured on A0r1's lossless frames*. Correction recorded here rather than by
editing the closed rulings' numbers, because the measurement did not move.

**This is precisely what an anchor leg is for**, and it is the argument for Ruling 4's commission
having ridden this experiment: the instrument that reproduces a published number is the instrument
that catches what that number was actually of.

## Ruling 9 — Gates and spend

**S 10/10 · L 10/10 · B 10/10 · Gate 0 12/12 · C PASS · lossless tap 10/10 · anchor 5/5. No gate
fired.** Gate S — the seed pre-registration andon — held across all ten submissions; no seed
outside the committed list ever reached the server, which is the property it was built for.

**10 generations, 40 credits of a 48 ceiling, 2 unspent.** A **1-generation probe ran first** and
verified end-to-end before the other nine went as a batch — not required by the spec, and correct.

## Ruling 10 — Disposition

**E04 is CLOSED and stays EXPERIMENTING.**

**What it establishes:** the between-generation floor on the tracking statistic at 33 frames is
**SD ≈ 0.16**, portable across both control polarities (ratio 0.93), against a fixed-seed floor of
**exactly zero**. Arm gaps are henceforth quoted in units of it.

**What it does not:** any threshold, any significance rule, or any licence to rank arms without the
Director's eye.

**Carried forward:** the floor is measured **at 33 frames**, and every number from it carries that.
If armature moves to 81 frames — well inside Wan's trained horizon per consult #3 — this floor does
not automatically travel.

**For the Director:** `C-bright-s4` is the panel to zoom — the lowest value in the experiment, and
the executor reports its sheet looks like every other one. If a run that reads as ordinary sits at
the bottom of the spread, that is the clearest available statement of what the floor *is*.
