# THE HANDOFF — armature advisor seat, 2026-08-10

Written by the outgoing advisor at the Director's instruction. Measured at write time, not
recalled. Where this document states a fact, it was checked; where it states a doubt, the doubt
is real.

---

## 1. What armature is, and the one line that matters

**You block the shot. The model shoots it.** A canonical character mesh is staged and animated
in headless Blender; the render becomes a per-frame **control sequence** a video model must
obey, so AI-generated video carries one persistent character whose position and pose are known
every frame.

`mcp-tool-shop-org/armature` · local `E:\AI\armature` · live at
https://mcp-tool-shop-org.github.io/armature/ (200) · PyPI name reserved as `armature-studio`,
Trusted Publisher configured against workflow **`release.yml`** — that filename is
OIDC-authenticated and cannot be repurposed.

**armature is downstream of facet** (`E:\AI\facet`). facet cuts and paints the figure; armature
stages and performs it. armature never writes into facet's tree.

⚠ **The single most important thing to protect: armature is a VIDEO tool.** It exists so a
character can *perform* — walk, turn his head, swing a blade — and stay the same man. The
outgoing advisor drifted into framing it as a turnaround producer after one trivial experiment,
and the Director stopped it. See [E02-CORRECTION-not-a-turnaround-tool.md](docs/experiments/E02-CORRECTION-not-a-turnaround-tool.md).
**If you ever find yourself proposing a smaller scope that fits a result, stop — check whether
the result is the test design reflected back.**

## 2. THREE SESSIONS IN FLIGHT — measured 2026-08-10, verify before acting

### (a) E02 closing — armature, branch `E02-first-contact`, **7 commits ahead of main**

A paste block was issued to an executor covering **two tasks only**: run the **A1b** arm (depth
polarity inverted to near-dark, one generation, 4 credits, everything else identical to A1a),
and add a pointer header to seven E02 documents. **A3 is deferred by ruling — do not run it.**

When their report lands, **you write `E02-closing-ruling.md`** consolidating eight scattered
documents, then merge the branch. The sprawl is the outgoing advisor's fault — a formal ruling
was written per message instead of accumulating and closing once. **Do not repeat that.**

### (b) E03 — armature, specified, **NOT started — and there is an ambiguity you must resolve**

Spec is on main: [E03-authored-motion.md](docs/experiments/E03-authored-motion.md). One
question: *if the subject itself moves, does the output move with it, at the right time?* Three
arms (B1 animated control · B2 no control · B3 static control — B3 is the discriminator).
Ceiling 4 generations.

⚠ **A branch named `E03-authored-motion` EXISTS, and it contains E02's work rebased** — its
commits are E02's (A0 floor, Gate B, the bridge, the report) with different hashes from
`E02-first-contact`. It is **not** a fresh E03. Establish whether that is a mis-named rebase by
the E02 executor or a session that branched wrong, **before anyone builds on it.** Do not assume.

### (c) E32 — facet, **RUNNING RIGHT NOW, uncommitted work in the tree**

Spec: `E:\AI\facet\docs\experiments\E32-armature-mark-through-the-route.md`. Putting armature's
own clay logo plate through facet's mesh route — a **thin-tube lattice**, a subject class facet
has never measured (its shell findings rest on longswords, a dragon and a galleon; the character
class is explicitly unmeasured).

**Already produced, untracked in `E:\AI\facet`:** `docs/experiments/E32-report.md`,
`E32-gate0-predictions.md`, `tools/diagnostics/e32_*.py`, `tests/test_t64_plate_geometry.py`,
a modified `tools/mask_geometry.py`, and in `E:\AI\training\facet_E32\`: **`armature.glb`
(35 MB)** and a **6.6 MB Gate 0 sheet**. facet also has **1 unpushed commit**.

⚠ **Steps 5–7 of the turnaround pipeline are OUT OF SCOPE** and the spec says why in its first
section — per-view restylize is a measured-wrong architecture whose blocking gate has not run,
*and* it is irrelevant to a subject with no garment and no face. If any instruction tells you to
run it, that is the exact conflict the skill says to raise **before** executing.

## 3. The discipline — what actually makes this seat work

Read `E:\AI\armature\CLAUDE.md` in full. It ports facet's law book, where every rule was paid
for. The ones that earned their keep *today*:

- **An inherited claim is a hypothesis wearing a fact's clothes** — including claims in your own
  dispatch. Mark every premise `MEASURED` or `ASSUMED`, and **`MEASURED` only if you measured
  the property the spec depends on**, not merely that the thing exists.
- **When a spec sentence contains "so", "therefore" or "which means", the clause after it is a
  SEPARATE premise** and needs its own row. Three of four falsified premises today were exactly
  that construction.
- **Enumerate the resource before commissioning one.** A flag, a tool, a node, a model may
  already exist. One grep separates a commission from a thing already built.
- **A check that cannot fail is not a check.** Applied twice today to gates the advisor wrote.
- **Bytes are not content.** A file-size change is not a content change; a byte-hash pin
  produces false halts. Pin the parsed object.
- **A `dry_run` PASS proves nothing about runnability** — amended today after it validated a
  structurally invalid graph. It may not be cited as evidence.
- **Metrics are diagnostics; the Director's eye is the verifier of record.** No metric
  approximates whether the figure is the right man.
- **Gate 0: the control | output | reference | provenance sheet before any number is quoted.**
- **A negative result is a full success.** Say so and stop.

**Working practice, non-negotiable while any executor is live:** author your commits in a
**detached `git worktree` on `origin/main`**. The outgoing advisor contaminated executor seats
**three times** — `git add -A` sweeping their file, committing onto their branch twice — before
adopting this. It removes the failure by construction rather than by remembering to check `HEAD`,
which had already gone stale twice.

**And ship the paste block in the same message as the dispatch, unasked.** The Director had to
ask twice today. The ask is the defect.

## 4. The outgoing advisor's error record — for your calibration

CLAUDE.md keeps this section because a future advisor should know which parts of the record to
distrust. Today's tally, honestly:

| error | what happened |
|---|---|
| **4 falsified premises** | Pages "unresolved org-wide" (measured 2 repos, truth 71 of 71) · "mirror anchor's config" (it does not build) · `longsword_hero.glb` "the natural primary" (it is a sword, 15.8:1) · "encoding is the only bridge" (video upload is refused by extension) |
| **A gate that could not fire** | Specified Gate B on output frame count; `WanVaceToVideo` pads/truncates to `length`, so the quantity cannot move. The executor caught it before implementing. |
| **A floor that measured the codec** | Reported "the Cloud path is NOT deterministic" with a caveat the conclusion could not survive. Model variance is **zero**; the entire floor, including its shape, was H.264 nondeterminism. |
| **A conflation** | Inferred *byte-exact transport* from *no lossy codec*. The bridge applies `max(src−1,0)`. |
| **3 cross-seat contaminations** | Fixed by the worktree practice above. |
| **The shrinking pattern** | Framed armature as possibly a turnaround tool. The Director caught it. |
| **A confounded instrument** | A coverage metric that counted a lit background gradient as subject. Caught and dropped rather than reported. |

**What the seat was good at:** ruling once evidence was in, killing options with reasons,
verifying claims independently before acting on them, and correcting in place rather than
quietly. **Deciding is the job. Predicting is not.**

## 5. State you can rely on — measured, not recalled

**armature.** main `7e63972`. Branches: `main`, `E01-control-sequence-exporter` (merged),
`E02-first-contact` (+7), `E03-authored-motion` (see the ambiguity above). CI and Pages green.
The org-wide `/favicon.svg` 404 is fixed **here only** — the cause is upstream in
`@mcptoolshop/site-theme`, whose `BaseLayout.astro` hardcodes the link with no prop or slot, so
every repo on the theme has the same bug and the same one-file fix.

**E02's measured results** (provisional until the closing ruling): control governs **where, at
what scale, and when**; prompt + reference supply **who**. Model repeat-variance is **zero** on
lossless frames. Generation costs **4 credits** (Director's balance delta, 14,284 → 14,280).
The bridge is 33 PNGs → `BatchImagesNode`, carrying a deterministic, common-mode
`max(src−1,0)`. **6 of 12 generations spent.**

**Licence gate.** `docs/license-map.md` — Wan 2.x is the default route (Apache across base,
VACE and Fun-Control). **OpenPose is CMU non-commercial. Depth Anything V2 Small is Apache and
Large is CC-BY-NC.** Rendering control from geometry removes that whole tier by construction —
protect that property. Four rows remain UNVERIFIED and are treated as NO.

**Known gap that blocks a future experiment:** no asset on this rig has anatomically named
bones — both rigged GLBs use `bone_0…bone_29` — so the blackguard cannot be posed on purpose.
E03 routes around it with the procedural wire armature (`tools/make_test_armature.py`, which we
authored, so every joint is known). **Identity-through-motion needs that gap closed first.**

## 6. Standing Director preferences, learned today

- **Review artifacts at 0.5×** — 8 fps, same frames, built from `lossless/` not re-encoded video.
- **"Dark" means tone, not black.** Rich shadow with colour in it.
- **This is a marathon.** Do not race, do not draw project-level conclusions from single runs,
  and do not carve provisional findings into doctrine. E02 is explicitly marked EXPERIMENTING.
- He judges artifacts by eye at full size and his reading is often better than the advisor's —
  he corrected "hold placement" to "A2 is a dramatic render, A1 is a turnaround," which was the
  more useful distinction and the thing that exposed the shrinking pattern.

## 7. What to do first

1. **Read** `CLAUDE.md`, then `E02-STATUS.md`, then this file's §2 and verify each session's
   state yourself. Do not inherit it.
2. **Resolve the `E03-authored-motion` branch ambiguity** before anyone builds on it.
3. **Wait for the E02 A1b report**, then write the closing ruling and merge.
4. **E32's report is in facet's working tree, uncommitted.** When that session reports, rule on
   it there — facet has its own CLAUDE.md and its own discipline.
5. E03 launches from a clean branch off main once E02 is closed. Its paste block is in the spec's
   terms; write it fresh and ship it **in the same message** as whatever dispatch precedes it.
