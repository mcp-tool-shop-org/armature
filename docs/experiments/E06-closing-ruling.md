# E06 closing ruling — the reference paints the tubes, and the rigging gap is confirmed rather than routed around

**Seat:** advisor · **Ruled:** 2026-08-10 · **Spec:**
[E06-reference-onto-schematic.md](E06-reference-onto-schematic.md) ·
**Report:** [E06-report.md](E06-report.md) · **Status:** EXPERIMENTING

## Ruling 1 — P2 is met, and it is the headline

**D1 and D2 both raise the arm across all 33 frames while carrying a painted character.** B1, the
same control with no reference, carried none. The named risk — that a still A-pose reference would
freeze an animated control at strength 1.0 — **did not occur**.

So the reference does not fight the control's motion. **A schematic control can carry both a
performance and a painted surface at once.** That is a real capability and it was not previously
demonstrated anywhere in this record.

## Ruling 2 — But the rigging gap is CONFIRMED, not routed around

E06 was dispatched to test whether a reference could supply the body while a posable wire armature
supplied the performance — which, if true, would have made authored motion available **without
rigging anything**. Read off the discriminator sheet and the structure zoom by this seat:

**It cannot. The control owns the outline.** Figure width tracks the control within 0.007 of frame
width at every frame in every arm, the limbs are the wire's cylinder segments, and at the Director's
zoom **both arms terminate in bristled cylinder ends rather than hands**. D1 and D2 are a stick
figure wearing armour.

**Ruled: authored motion on a real character still requires a control whose silhouette is the
character's — which means rigging.** E03's ruling promoted the rigging gap to armature's blocking
dependency; **E06 was the attempt to go around it and the attempt failed on measurement.** That is
a full result and it is worth what it cost: the alternative was discovering the same thing after
building a pipeline on a wire figure.

## Ruling 3 — ⭐ And the mechanism it measured is the actual prize

**Control owns the outline. Reference owns surface, material and costume.**

That division is precisely what armature's thesis requires — *you block the shot, the model shoots
it* — and until now it was assumed. It is now measured on one subject, with the null (B1) in hand
and every other input byte-identical.

**The consequence is constructive, not consoling:** get the silhouette right and the reference
supplies the rest. The work is therefore in the control's geometry, not in coaxing the model.

## Ruling 4 — The crack, and it is precise: the reference CAN extend a silhouette the control leaves silent

D2's **horns are in the outline** — mask bbox 228 px against the control's 195 — and both arms carry
a hem mass at the hips that the control does not.

So the boundary is sharper than "the control owns the outline":

* Where the control **speaks** (the limbs), it governs and the reference cannot override it.
* Where the control is **silent** (above the head, below the hips), the reference and prompt **can
  add** silhouette.

That is a new, usable fact, and it was only available because the executor wrote P3's clauses apart.

## Ruling 5 — P3's split score is upheld

The load-bearing clause held; the absolute clause — *"nothing from the reference's shape survives
into the outline"* — is falsified by the horns. The executor **named the split branch in advance and
refused to let that convert a miss into a hit.** Upheld exactly as scored. An absolute clause is
falsified by one counterexample, and that is what an absolute clause is for.

## Ruling 6 — The flagged executor choice is ACCEPTED, and its limit is recorded

"Names the character" was read as **name plus canon attributes**, not a bare proper name. Accepted —
the spec did not constrain it, and the richer reading is the configuration we would actually ship.

**But the limit is real and goes on the record: D2 answers *"does naming with attributes change the
figure"* — yes, it added the horned helm and segmented pauldrons, two of the five elements E02's
canon ruling named as carrying — and it does NOT answer *"does a bare proper name suffice."* That
question is UNANSWERED.** It is not worth a generation today; it is worth not pretending it was
asked.

## Ruling 7 — ⚑ MY ERROR, and it was live under two seats spending credits

E06's spec told two concurrent seats:

> *"The regression net is real, not hope: `tests/test_build_payload.py` pins E02's payload bytes, so
> a merge that corrupts the builder fails the suite before it can spend a credit."*

**That was false, and the executor found it.** Verified by this seat:
`test_E02_payload_bytes_have_not_moved` carries
`@pytest.mark.skipif(not HAVE_E02_UPLOADS, reason="E02 upload records are gitignored output")`, and
`outputs/` is gitignored — **so the pin skips in every fresh worktree**, which is exactly what both
the E04 and E06 seats created. The net I instructed two credit-spending seats to rely on **was not
running**, over the one file both of them are editing.

**I asserted a safety property without checking it.** That is the same failure as citing a resource
without enumerating it, in its most expensive form: the assertion was load-bearing for someone
else's work.

**And it is a law, one layer past a familiar one.** *A check that cannot fail is not a check* — a
check that **silently skips** is worse, because a skip is a pass-shaped absence. A seat reading
"206 passed" does not see that the load-bearing pin was not among them.

**Ruled, and it is mine because the surface is shared:**

1. The E02 and E03 upload records are **98 B – 2.7 KB of JSON**. They are committed as **test
   fixtures** so the pin becomes **unconditional**, rather than reading a gitignored output path.
2. Any remaining skip on a **regression pin** must be **loud** — the suite reports it, or the
   condition is removed.
3. **The E04 seat is live and must be told now.** It has been editing that builder under a pin that
   was not running.

## Ruling 8 — The byte-versus-pixel catch is upheld

A byte hash said the two control batches differed; **pixels are 33/33 identical**, and the 73-byte
delta is PNG metadata carrying the differing prompt. This repo's own law — *a file-hash mismatch is
not evidence a render changed; compare pixels* — firing on the executor mid-session, on the exact
quantity the experiment holds constant. **Caught and reported rather than propagated.**

## Ruling 9 — Instrument hygiene, and E03's lesson applied

The silhouette instrument's subject fraction ran **0.0586–0.0877** across all arms, never
approaching E03's confounded **0.456**, and a **mask evidence sheet** was built so the segmentation
is checkable by eye. The band was fixed before any number was read.

That is E03's confounded-classifier lesson applied by the next seat without being told to. Adopted.

**Also upheld:** premises 4, 5 and 6 moved from assumed to **measured** — B1's submitted payload
verified by recorded sha256, and all **34 assets** re-uploaded with every one returning the name
already recorded, confirming content addressing rather than inferring it from a single sample.

## Ruling 10 — Disposition

**E06 is CLOSED and stays EXPERIMENTING.** Two generations of a three-generation ceiling; reserve
unspent; **no gate fired and nothing was re-run to get past one.** Gate C was stated before the
first submission and D2 was held until D1 reached a terminal state, so a systematic failure would
have cost 4 credits rather than 8.

**Open, and the Director's alone:** whether either figure is the same man as the reference. No
sentence in the report or this ruling answers it, and no metric here approximates it.

**What E06 establishes:** a reference paints a schematic control's figure without stopping its
performance; control owns the outline, reference owns the surface; and the reference can extend a
silhouette only where the control is silent.

**What it forecloses:** routing around the rigging gap with a wire armature. That door is measured
shut.

**Next:** rigging is the blocking dependency, unchanged and now confirmed twice — **and nothing
governs against it.** See E03's closing ruling, Ruling 7, for the retraction of the "June decision"
framing this seat raised three times. There is no permission to obtain. The next step is to rig a
character.
