# The first-arc audit — called by the Director, 2026-08-11

**Seat:** advisor (incoming 2026-08-11) · **Trigger — his words:** *"These experiments all seem
very repetitive and basic… we're going to need to audit the entire repo before proceeding and
weigh whether it's best to start from scratch, with everything we've learned so far."*

**Why this seat grades it:** the founding rule — the seat that designs an experiment does not
grade its results. This seat designed nothing in the arc; every document cited below was read
this session, and every number was re-measured from payloads, ledgers and git rather than
inherited from the handoff.

**What this audit may not judge:** whether any figure is the same man, and whether any output
is good. Those are the Director's, and two artifacts still await his eye (§6). No sentence here
answers them.

---

## 1. The finding, re-measured

**22 generations. 88 credits. Zero authored shots.**

| experiment | generations | staged input | credits |
|---|---|---|---|
| E02 | 7 — A1a, bridge probe, A0 ×3, A2, A1b | static blackguard, turntable orbit (A2: same scene, control absent) | 28 |
| E04 | 10 — C-bright s2–s6, C-dark s2–s6 | **E02's two payloads re-submitted**, seed varied | 40 |
| E03 | 3 — B1, B2, B3 | wire armature, one arm raise | 12 |
| E06 | 2 — D1, D2 | E03's control + reference | 8 |

Verified from payload JSONs on disk (`outputs/*/payloads/` — 4+10+3+2 files, E02's seven
reconstructed from its report's ledger lines at "6 of 12"/"7 of 12"), and from each closing
ruling's Gate C count. Credits are 4 per generation, measured once via the Director's balance
delta (14,284 → 14,280); `estimate_credits` returns 0 on the open-weights route, so the balance
remains the only instrument.

**Sixteen generations carried the turntable control or a re-run of it; one was its no-control
twin; five were the wire armature.** In the repo's whole life, exactly **two scenes** have ever
been staged: a static character on a plinth, and a wire figure raising one arm. `specs/` holds
five files — two E01 anchors, the E02 turntable, E03's posearc and static. **No authored shot
spec exists. No lighting design exists. No facet canonical asset was ever staged in a scene.**
Not one frame of a character performing has ever been generated, and the tool's product is
footage.

*(Provenance note: `outputs/E03`, `outputs/E04`, `outputs/E06` were consolidated into this tree
on 2026-08-11 from the executor worktrees before those were pruned — per-directory file counts
verified at copy time; cross-worktree duplicates preserved under `outputs/_recovered/`.)*

## 2. The mechanism — how a disciplined system bought nothing

The arc's hygiene was real: predictions registered blind, gates that raised and held (Gate S
10/10), misses harvested into laws, licence bans enforced, contaminations caught and named.
**None of that failed. What failed is one layer up: every instrument in this repo bounds
validity, and nothing bounds value.** The gates ask *is this measurement clean* — no gate, no
template row, no ritual asks *what does this spend advance*. The system has excellent brakes
and no steering. The studio's own constitution names this exact pattern at studio scale — its
discriminator says tool counts and test counts are not the success metric, and its named
anti-pattern is `built` that never becomes `filled`. This arc is that pattern at experiment
scale: 262 passing tests, five closed experiments, zero frames of the product.

Five specific mechanisms, each with its evidence:

**2a. The steering instrument existed and was abandoned.** `docs/ROADMAP.md` is the
drift-prevention document — its own header says *"read it at the start of every session"* and
*"a phase that gets re-cut records why in this file."* It has **two commits, both from founding
day** (`ef0b1b0`, `fc2f2c2`). As planned → as run: E03 *control modality* → authored motion;
E04 *control strength* → the seed floor; E05 *identity, reference stack* → a strength sweep,
withdrawn; E06 *identity, LoRA vs zero-shot* → reference-onto-schematic. Every re-cut went
unrecorded because nobody was reading the file that required the recording. **Phase E —
identity, the planned experiment closest to the product — never ran**, while two unplanned
proxies did. And control strength, scheduled fourth on day one, has still never been varied:
`strength` is 1.0 in every payload ever submitted (E03 closing, Ruling 6).

**2b. Corrections have no enforcement surface.** When seed-shopping was the risk, it got
**Gate S** — a check that raises inside the submitting tool. When scope-shrinking was the risk,
it got **prose** — `E02-CORRECTION-not-a-turnaround-tool.md`. The E04 spec then specified ten
more turntable generations, and the word "turnaround" appears in that spec **zero times**: the
violation was not argued past, it was invisible in the spec's own vocabulary, because "re-submit
E02's payloads byte-identical with one field moved" is a complete description at the hygiene
level and an empty one at the product level. The spec template marks every premise MEASURED or
ASSUMED — premises are *facts*; no row exists for *purpose*. A law that must bind gets a gate.
A correction that lives as prose in a closed experiment's folder binds nobody.

**2c. The alternative was never put to the Director contrastively.** He un-deferred E04 —
his credits, his call, and the deferral had been framed to him as a *priority* question. What
was never framed: *"these 40 credits can buy ten re-runs of the turntable for a noise floor, or
the first authored shot — the seat recommends which and why."* The studio's own standard
(UNCERTAINTY_GATED_HUMANS) requires exactly that shape. The removed credit ceiling made the
portfolio question *more* important, and it was never asked once.

**2d. The pace made the portfolio question unaskable.** The entire arc — E01 through E06, S01,
S02, four consults, two handoffs — ran in roughly 36 hours, under a standing instruction that
*"this is a marathon."* At sprint pace each seat optimised its own experiment; no session ever
stepped back to ask what the last three spends had bought toward footage. The Director's
*"horrible night"* is that cost surfacing.

**2e. The setup work never happened, and the subject sabotaged the judge.** Every judgment
artifact in the repo's life shows a **black-armoured figure on grey or white** — the palette
that crushes exactly the material, face and silhouette-edge information the identity question
needs, against his standing rule that *dark means tone with colour in the shadows*. Read with
this seat's own eyes on `E06-discriminator.png` and `E04-C-bright-s4.png`: the provenance
columns are genuinely strong (hashes, seeds, gate verdicts on the sheet), but panel scales are
mixed, labels are 8-px grey, there are no zoom insets on hands or face — the regions every
ruling says decide — and internal debug states (`Gate B NOT YET RUN`) print on artifacts meant
for his eye. These are evidence grids, not dailies. The subject was chosen on day one and never
upgraded, because no session was ever dispatched to stage anything.

## 3. What the 88 credits actually bought — the ledger, both columns honest

**Bought, and it survives** (each traceable to a closing ruling and its payloads):

1. A rendered control sequence governs **where** the figure is, at what scale, and when it
   moves (E02).
2. It governs **authored subject motion, categorically** — 85.0° against 0.062° (E03).
3. **Control owns the outline; the reference owns surface, material and costume** — and the
   reference can extend a silhouette only where the control is silent (E06). This division of
   labour *is* the thesis mechanism, previously assumed, now measured on one subject.
4. The between-generation floor on the tracking statistic is **SD ≈ 0.16 at 33 frames**,
   portable across both polarities, against a fixed-seed floor of exactly zero (E04) — and
   paired seeds cut comparison noise 2.5× for free (E04 Ruling 4).
5. **At strength 1.0, with a body to paint, the model paints** (E02 A1a) — and with no body it
   traces (E03 B1). The wire-armature door to rig-free motion is measured shut (E06).

Plus the non-credit capital: the exporter and payload/bridge toolchain with **262 tests passing
under `-O`** (README said 206 — corrected in this commit); instruments with anchor legs that
caught a wrong attribution in a published number (E04 Ruling 8); a licence map whose
architectural moat — control rendered from owned geometry, no estimator tier in the pipeline at
all — is a real advantage; live public surfaces; S02's index awaiting merge; and a set of earned
laws (the weak-datum law, skip-is-a-pass-shaped-absence, gates-on-ground-truth-not-distinctness,
rulings-interact-check-the-join, paired-seeds-by-default).

**Not bought, at any price:**

- **Identity evidence: zero.** The one canon question — *is this the same man* — has no data.
  E03 had no "who" anywhere in it by construction (Ruling 5); E06's two figures await his eye.
- **A staged shot: zero frames.** The product is footage; none exists.
- **The strength curve: untouched** — planned day one, never varied, E05's withdrawal correct
  but its surviving question (how much control at 1.0 constrains composition and scale) waits.
- **Anything at 81 frames**, the trained-horizon length consult #3 identified as the cheapest
  win.

**The shape of the spend:** after E03, the mechanism was not in serious doubt. E04 then re-ran
the same staging ten times — **45% of every credit ever spent** — to calibrate a ruler whose own
ruling forbids using it as a threshold, while the first authored shot still cost zero staged
scenes. E04 is well-designed, honestly reported, correctly ruled — and it is the arc's direction
failure in its purest form. The vindications it produced (E02's refusal, twice) are real and are
kept separate from this framing, per the handoff.

## 4. The weighing — start from scratch, or continue

**What a restart buys.** A tree whose first commit is a shot; escape from a record that is
already 27 experiment documents deep after two days; a psychological clean break.

**What a restart costs.** The provenance chains behind every number above (the record *is* what
the 88 credits bought); 262 tests and the toolchain; the licence map; the PyPI Trusted-Publisher
binding (OIDC is bound to `mcp-tool-shop-org/armature` + `release.yml` — a renamed repo starts
that over); S02's cross-repo index adoption mid-flight; the public surfaces; and the studio law
that **failures stay in the repo** — a falsified approach that leaves the tree becomes doctrine
again. The sprawl problem is real but is a *reading-order* problem, already solved once at E02
scale by the closing-ruling pattern; it does not require a migration.

**What a restart does not fix — and this is the decisive clause.** The failure is not stored in
the tree. It is in the **dispatch criterion** — what a seat chooses to spend the next session
on — and that travels with the seats, not the repo. The proof is in §2b: the correction *was in
the tree*, quoted by the seat that violated it. A fresh tree has strictly fewer bindings, not
more.

**Recommendation — the Director may have expected "scrap it" or "keep it"; this seat recommends
neither pole:** keep the repo, **end the E-series**. Close the arc as the record of a mechanism
now measured, and open a new series whose unit is **the shot** — numbered SH01, SH02, … — under
the conditions in §5. The E-numbering does not continue; an experiment may exist afterward only
as a child of a shot's named unknown, spawned when that unknown blocks the shot and closed back
into it.

The call is his. This document gives him the ledger to make it, and nothing here presumes it.

## 5. Conditions any continuation must satisfy

1. **The unit of dispatch is the shot.** Every credit-spending spec carries a "what shot does
   this advance" line with the same force as its licence row — a spec that cannot fill the line
   does not spend.
2. **The rigging gap closes before the next credit.** Twice confirmed as *the* blocking
   dependency (E03 Ruling 7, E06 Ruling 2), zero credits to close (local Blender work), and
   nothing governs against it (E03 Ruling 12 — the "June decision" blocker was invented and is
   retracted). Route evidence already in hand: UniRig is falsified on faced characters, so the
   route is hand-rigging or transfer from a named-bone skeleton.
3. **The first credit after that buys the first authored shot.** Staged, lit, on a facet
   canonical asset, with a shot spec in `specs/`. Rig → stage → shoot, in that order — the
   sequence the Director named (*"shouldn't there be a process of creating the skeleton before
   trying to move the limbs?"*) and the arc never ran.
4. **Corrections get enforcement surfaces.** The spec template gains a standing-corrections row
   the advisor checks at dispatch, the way premises are checked now. A correction that matters
   more than that gets a gate. Prose is not a binding.
5. **The roadmap is re-cut once, honestly, or withdrawn.** A steering document nobody reads is
   worse than none — it lends the *appearance* of a plan to an arc that has left it. If kept,
   re-cuts are recorded in it per its own header, and the advisor reads it at every dispatch.
6. **Sheets become dailies.** Uniform panel scale; the reference at judgment size; zoom insets
   on hands, face, and whatever region the experiment turns on; labels readable at review
   distance; no internal gate states on Director-facing artifacts. And the judgment subject must
   carry judgment information — colour in the shadows, a face, material variety. *These are
   studio artifacts and they should look like a studio made them.*
7. **Public surfaces stay true.** The README simultaneously said 12 and 22 generations, and 206
   tests where the suite reports 262. Both corrected in the commit that lands this audit; the
   standing rule is that the store window is re-read whenever a closing ruling lands.

## 6. Open items this audit queues

**His eye (deferred to fresh eyes by his own instruction, paths valid in this tree):**
- `outputs/E06/sheets/E06-discriminator.png` and `E06-structure-zoom.png` — whether either
  figure is the same man. Nothing in the record answers it.
- `outputs/E04/sheets/E04-C-bright-s4.png` — the lowest value in the floor experiment, on a
  sheet that reads like every other one: the clearest available statement of what the floor is.

**His call:**
- This audit's §4 recommendation — or a restart, which this document does not foreclose.
- The publish chain go: `release.yml` in record-index → tag 0.1.0 → OIDC publish → push facet
  `c0031c1` → merge armature `S02-run`. Mechanical once he says go; a PyPI version is permanent,
  and the two caveats from the handoff (record-index has no tests of its own; certificate logic
  exists twice) argue the next version should follow soon, not that 0.1.0 waits.

**Advisor queue (after his read):** the five S02 ruling questions (`S02-report.md` §7); E02
Ruling 5's disposition of `tools/invert_frames.py` (adoptable by separate advisor commit, still
untracked); the roadmap re-cut per §5.5 once §4 is decided.

**Standing hazard:** the VRAM watchdog was found dead this session (heartbeat 7.5 h stale). No
GPU work — Blender renders included — until
`pwsh -NoProfile -File E:\AI\training\_watchdog_start.ps1` shows a live heartbeat.

---

## AMENDMENT 1 — 2026-08-11, advisor, on the Director's reading

The Director restated the audit's target in his words, and they are sharper than §2's framing:
the drift shrank *"a complete professional glb to video pipeline that we could use to make
movies, game cutscenes, game character poses and movement"* into a turnaround repo, and he had
to correct it twice in two sessions. That is the finding; the validity/value mechanics in §2
are the anatomy of it, not a substitute for it.

**His direction going forward is ruled and supersedes §4's renumbering proposal:** the method
stays **experiments** — aimed at the full pipeline, consulting the Comfy Agent as needed,
trajectory held true. The SH-series is therefore **DROPPED**; the E-series continues under §5's
conditions, which stand in full. §5.1's trajectory requirement and the scope block now bind
mechanically in `CLAUDE.md` (this commit) rather than living as prose here. E07 (the skeleton)
is the first spec dispatched under them; E08 (the first authored performance of the character)
follows it and is where credits next flow.
