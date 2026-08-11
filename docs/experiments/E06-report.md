# E06 report — a reference onto a schematic control

**Seat:** executor · **Run:** 2026-08-10 · **Spec:**
[E06-reference-onto-schematic.md](E06-reference-onto-schematic.md) ·
**Predictions:** [E06-predictions.md](E06-predictions.md), committed at `07fd37a` before any
tooling was read · **Advisor rules after this report** · **The Director judges the sheets.**

**Two generations submitted, ceiling three, one reserve unspent. No gate fired.**

---

## 1. Predictions, and whether they were blind

Registered in `E06-predictions.md` and committed **before** `tools/build_payload.py` was read,
before the first `ls` into any `outputs/` directory, and before a single pixel of any E06 input
was opened. The commit is the timestamp.

**Blind to:** D1, D2 — neither existed.
**Blind to, additionally:** E02's reference plate, E03's 33 control frames, B1's output. All were
opened only after registration.
**NOT blind to:** the prose descriptions of A1a ("painted armoured knight") and B1 ("black stick
figure"), which are the two endpoints I was predicting between; the subject's construction; that
`strength` has never left 1.0; and that P2 is the clause the rigging gap turns on. All four
disclosed in the file.

`E05-control-strength.md` was not read, per the dispatch.

---

## 2. Gate 0 — the sheets, built before any number was quoted

| sheet | what it is |
|---|---|
| [`E06-D1-gate0.png`](../../outputs/E06/sheets/E06-D1-gate0.png) | control \| output \| reference \| provenance, D1, native resolution |
| [`E06-D2-gate0.png`](../../outputs/E06/sheets/E06-D2-gate0.png) | same, D2 |
| [`E06-discriminator.png`](../../outputs/E06/sheets/E06-discriminator.png) | **the panel this experiment exists to produce** — one control row, then B1 / D1 / D2 under it |
| [`E06-all-frames.png`](../../outputs/E06/sheets/E06-all-frames.png) | all 33 frames of all three arms |
| [`E06-structure-zoom.png`](../../outputs/E06/sheets/E06-structure-zoom.png) | native pixels at 3× NEAREST — gauntlet and head |
| [`E06-mask-evidence.png`](../../outputs/E06/sheets/E06-mask-evidence.png) | what the silhouette instrument actually segmented |

The discriminator is the one that carries the experiment: **the control row is byte-identical
across all three arms, the seed is the same, the negative is the same, `strength` is 1.0
throughout.** B1 has no reference; D1 adds one; D2 adds one and names the character.

---

## 3. What the arms produced

Described, not graded. **Whether either figure is the same man is the Director's call and no
sentence here answers it.**

**B1 (E03, no reference, carried forward as the baseline)** — a black stick figure on flat grey:
tubes with ball joints, no surface, no costume, no ground.

**D1 (+ reference, prompt unchanged)** — a dark figure carrying segmented plate on the torso, a
gorget, a helm with two small points and no face, a tattered dark cape falling behind, and a
ragged hem at the hips. It stands in a lit studio with a floor and a cast reflection. The arms are
tubes with banded cuffs; at 3× zoom the raised arm terminates in a bristled cylinder end, **not a
hand** — no fingers, no thumb.

**D2 (+ reference, prompt names the character)** — the same tube-limbed figure, now with **two
large warm-metal horns** above the helm, an amber-lit visor slit, silver-rimmed pauldrons, a
chainmail-textured torso, a red-brown belt, a tattered skirt, and a white circular plinth under
the feet. The raised arm terminates in the same bristled cylinder end, again **not a hand**.

---

## 4. Predictions against outcomes

### P1 — what does D1 produce? **Registered: BETWEEN. Outcome: MET.**

Registered verbatim: *"a thin humanoid — recognisably the same stick proportions as B1 — but no
longer flat black … dark metal, some specular highlight along the limb tubes, a slightly more
head-like head. The background moves from B1's flat grey toward a lit studio with a floor. Not a
fully-bodied armoured knight; not B1's bare diagram either."*

Every clause of that is what came back. **One qualification against my own hit:** I predicted
"palette and material cues," and what arrived is articulated costume — plate segmentation, a
gorget, a cape with a torn edge. The surface did more than recolour the tubes. The prediction was
right about the category and understated the degree.

### P2 — does D1's arm rise? **Registered: YES. Outcome: MET.**

Read **by eye** off [`E06-all-frames.png`](../../outputs/E06/sheets/E06-all-frames.png) and the
Gate 0 sheets, per the spec's instruction — not by E03's arm-angle classifier, which was measured
confounded on B2 and is not quoted here for any purpose.

Across all 33 frames the raised arm travels monotonically from horizontal to vertical in **both**
D1 and D2, on the control's schedule. **The named risk did not occur:** a still A-pose reference
did not freeze the sequence. A reference image and an animated control are composable at
`strength` 1.0 on this route.

### P3 — which input owns the silhouette? **Registered: THE CONTROL, thin tubes. Outcome: MET on the load-bearing clause, MISSED on the absolute one.**

**Met.** The control owns the outline's extent. Figure width as a fraction of frame, per frame:

| frame | CONTROL | B1 | D1 | D2 |
|---|---|---|---|---|
| f000 | 0.5979 | 0.5979 | 0.6000 | 0.6042 |
| f008 | 0.5875 | 0.5875 | 0.5875 | 0.5896 |
| f016 | 0.5458 | 0.5458 | 0.5458 | 0.5500 |
| f024 | 0.4771 | 0.4729 | 0.4708 | 0.4813 |
| f032 | 0.4000 | 0.4021 | 0.3917 | 0.4062 |

Every arm sits within 0.007 of the control at every frame. The limbs are the control's cylinders
in all three arms — visible at 3× zoom as banded tubes, and in the mask evidence as tubes with ball
joints.

**Missed.** I wrote *"nothing from the reference's shape survives into the outline"* and *"no cape,
no helm bulk."* That is false. D2's **horns** are in the outline — the mask bbox is 228 px tall at
f000 against the control's 195 — and **both** D1 and D2 carry a hem/skirt mass at the hips that the
control has no geometry for. The reference's shape reaches the outline at the head and the hem
while the control holds the limbs.

I named this split branch in advance — *"the silhouette could come from the control in the limbs
and from the reference in the torso and head"* — and naming it does not convert a miss into a hit.
**The headline clause was right; the absolute clause was wrong.**

Supporting diagnostic, **and it gates nothing**: fill ratio inside the figure's own bbox —
CONTROL 0.230–0.277, B1 0.237–0.281, D1 0.299–0.365, D2 0.289–0.352. **No arm is ranked against
another on this number.** E04's between-generation floor is unmeasured, so a D1-versus-D2
comparison here (0.299 against 0.291) is a gap I decline to read.

### P4 — does naming the character change anything? **Clause A MET, clause B MISSED.**

**Clause A — surface changes: MET.** D2 differs from D1 in palette, material and costume detail:
horns, amber visor slit, silver pauldron rims, chainmail texture, red-brown belt, plinth.

**Clause B — identity does not change: MISSED, and this is the more important half.** I predicted
naming the character would not produce an identity-relevant difference, on the reasoning that the
reference already carried identity and there was too little figure to carry it. D2 carries the
**horned helm** and **segmented pauldrons**; D1 carries neither. Both are elements the Director's
own [E02 canon ruling](E02-canon-ruling.md) named as the carrying evidence, alongside the tattered
cape and ragged hem that both arms do carry.

⚠ **This is a difference report and not an identity ruling.** Whether D1 is the same man, whether
D2 is, and whether they are each other, is canon and the Director's alone. Nothing above answers
it, and the fill-ratio and width numbers approximate it in no way.

---

## 5. Gates

| gate | arm | verdict | evidence |
|---|---|---|---|
| **Gate L** — frame legality | D1, D2 | **PASS** | raised inside `build()`; 480×832×33 against wan-vace 16-divisor / 4n+1 |
| **Gate B** — batch intact | D1 | **PASS (33 of 33)** | `gate_b_batching(33, 33)` on the node-301 probe |
| **Gate B** — batch intact | D2 | **PASS (33 of 33)** | same |
| **`expects_reference`** — this experiment's own variable | D1, D2 | **PASS** | bound `True` for E06; driven to failure in a new test |
| **The lossless tap** | D1, D2 | **PASS** | node 302 wired to VAEDecode; all measurement read `lossless/`, never the mp4 |
| **Gate 0** — sheet before any number | D1, D2 | **PASS** | six sheets above, built before section 4 existed |
| **Gate C** — spend stated before submitting | — | **PASS** | 2 of 3 ceiling, stated before the first submission |
| **Gate R** — round trip | — | **N/A for this route** | no codec in the path |
| **Gate G6** — frame distinctness | — | **N/A** | no Blender render in this experiment |

**No gate fired. Nothing was re-run to get past one.**

### Control fidelity — the batch the sampler actually received

Both arms' 33 probe frames equal `max(src − 1, 0)` of E03's control frames, **pixel by pixel, on
all 33** — E02's measured, uniform, one-sided bridge offset. 0 frames byte-exact, 33 under the
offset, 0 neither, for D1 and for D2. So the control D1 and D2 ran on **is** B1's control, and
this also confirms the 33 server filenames transcribed into the submission correctly.

---

## 6. Premises, as measured rather than as assumed

| # | premise | spec status | outcome |
|---|---|---|---|
| 1 | `EXPERIMENTS` carries a per-experiment `reference` field | MEASURED | confirmed on read |
| 2 | `verify_topology` binds reference presence both ways | MEASURED | confirmed, and driven to failure in a test |
| 3 | `test_build_payload.py` pins E02's payload bytes | MEASURED | confirmed — **see the finding in §8** |
| 4 | B1's submitted payload is on disk and re-submittable | **ASSUMED** | **now MEASURED.** `B1.json` recomputes to `c9534db6…`, matching its recorded meta. D1 differs from it by exactly one sampler-reaching input |
| 5 | E02's reference plate is still resident server-side | **ASSUMED** | **now MEASURED** — see below |
| 6 | E03's 33 posearc frames are still resident | **ASSUMED** | **now MEASURED** — see below |
| 7 | a reference does not loosen control authority over position | ASSUMED (P3's question) | width tracks the control within 0.007 at every frame in both arms |
| 8 | generation costs 4 credits | MEASURED (E02) | not re-measured here; the Director's balance is the instrument |

### How residency was verified, and it is worth stating plainly

There is no read-only residency endpoint on this route, and **`dry_run` cannot answer it** — E02
measured `dry_run` accepting a `LoadImage` naming a file that does not exist, without a warning.
So residency was established the only way available: **all 34 assets were re-uploaded**, and
every one returned **the exact name already recorded in the manifests** — the reference plate as
`71836f47…`, and all 33 control frames matching `uploads_posearc.json` 33/33. Upload is
content-addressed, so this is simultaneously the verification and the guarantee.

**Nothing was re-uploaded because it was missing. Nothing was missing.** No manifest was rewritten.

---

## 7. Provenance

| | D1 | D2 |
|---|---|---|
| prompt_id | `531bfd03-ce8b-488f-adf4-5c44863d21c4` | `63b3d3f3-fcb4-41fd-8c8b-8b140c48cd3d` |
| payload sha256 | `68e902cd3522196dfea833c3e0a814a2…` | `8db98670597d5edabb1e3079e11113a3…` |
| reference | `71836f47…png` (`blackguard_apose_0.png`) | same |
| control | E03 posearc, 33 distinct, window pinned `[3.181118, 3.363516]` | same |
| seed / strength | 654654950714624 / 1.0 | same |
| models | `wan2.1_vace_14B_fp16` · `umt5_xxl_fp16` · `wan_2.1_vae` | same |
| positive | E03's, inherited literally | E03's scene sentence, subject clause replaced |

Full file-level record: `outputs/E06/sha256-manifest.json` (147 files).

**D2's positive, in full:** *"The blackguard, a lone armored warrior in dark plate armor, horned
helm and heavy cloak, stands in the centre of an empty studio. Plain grey seamless background,
even neutral lighting, full body in frame."* The second sentence is byte-identical to D1's.

**Executor choice, flagged for the advisor to overrule.** "Names the character" was read as *name
plus canon attributes*, not a bare proper name, on the reasoning that a bare name is not a canon
element to a text encoder — it resolves tokens, not lore. The attributes chosen are the ones E02's
own prompt used for this subject. The prompt still names **no motion**, holding E03's discriminator
hygiene constant between D1 and D2. If the advisor wanted the bare-name form, D2 answers a
different question than intended and the arm should be re-read accordingly.

---

## 8. Findings that are not about the arms

**① The E02 byte pin skips by default in a fresh worktree, and a pin that skips is not a pin.**
`HAVE_E02_UPLOADS` / `HAVE_E03_UPLOADS` test `os.path.isfile` against gitignored output paths, so
in a clean checkout `test_E02_payload_bytes_have_not_moved` — the test the module docstring calls
load-bearing — **silently skips**, along with the whole `TestE03Arms` class. It is the regression
net protecting a shared builder during a round when two seats are editing that builder, and by
default it is not running. Staging the manifests locally turned it on; it then passed unchanged.

**I have not fixed this.** It is the shared regression net, E04 is live in the same file, and a
skip-condition change is exactly the kind of shared-surface edit the dispatch reserves. **Named,
not touched.**

**② Partial staging is its own hazard, and I hit it.** Copying E03's posearc manifest turned
`HAVE_E03_UPLOADS` true and un-skipped tests whose *other* inputs I had not staged — 5 failures
that were artifacts of my own staging, not defects. Staging the rest returned the suite to green.
The general shape: a skip guard keyed on one file can un-gate checks that need several.

**③ A byte-hash said the two control batches differed; the pixels said they are identical.**
Comparing D1's and D2's probe frames by sha256: 0/33 match. By decoded pixels: **33/33 identical**.
The 73-byte delta is PNG metadata carrying the differing prompt. This repo's law — *a file-hash
mismatch is not evidence a render changed; compare pixels* — fired on me inside this session, and
the false signal was on the exact quantity the experiment holds constant.

**④ The silhouette instrument was checked before it was quoted.** Band subject-fraction across all
four arms and all measured frames sits in 0.0586–0.0877, with no arm approaching the 0.456 that
marked E03's confounded classifier on B2, and
[`E06-mask-evidence.png`](../../outputs/E06/sheets/E06-mask-evidence.png) shows what was actually
segmented in every case. The analysis band (top 55%) was fixed **before** any number was read,
because the floor and plinth are the obvious confound here and choosing the band afterwards would
have been choosing the answer.

---

## 9. Credits

| | |
|---|---|
| ceiling (spec) | 3 generations / 12 credits |
| **submitted** | **2 — D1, D2** |
| projected spend | **8 credits** at E02's measured rate, stated before the first submission |
| reserve | 1 generation, **unspent** |

The Director's balance is the instrument of record. Workspace GPU-hours before submission:
$0.7246 on 2026-08-10, $0.5377 on the 2026-08-11 partial bucket — recorded as context, not as a
credit measurement.

---

## 10. Tooling that rode this commit

`tools/build_payload.py` — an `EXPERIMENTS["E06"]` entry with arms D1 and D2, plus **one**
structural change: a per-arm `positive` override, so the two arms can differ in the prompt alone.
D1 carries no override and therefore **inherits** E03's positive literally rather than by copy; a
retyped prompt is a second variable no report would catch. No E02 or E03 arm carries an override.

**No gate was commissioned.** `verify_topology(expects_reference=…)`, written for E03, already
binds this experiment's only axis in both directions. Enumerating the file turned a commission
into a config entry.

`tests/test_build_payload.py` — 9 new tests. `TestE06Arms` asserts D1's control is B1's node for
node; that D1 differs from B1 in the reference and nothing else (`added == {"134"}`, and the VACE
node equal after popping `reference_image`); that D2 differs from D1 in node 6 and the output
prefixes only; that both arms share E02's plate; and that D2's prompt names the character while
naming no motion. Two more drive the existing checks to failure.

**206 pass, and 206 under `-O`.** The E02 byte pin passes unchanged.

---

## 11. Concurrency

Rebased on `origin/main` before editing `tools/build_payload.py`, again before committing the
tooling, and the suite ran green after each. **`origin/main` did not move during this session** —
E04's seat had pushed nothing, so no gate of theirs was present to preserve, and nothing of theirs
was refactored, renamed or removed.

**No foreign files appeared in this tree.** `git status` was clean at every checkpoint.

**Collisions named, untouched:** the test-count surface (197 → 206 here) and the `HAVE_E02_UPLOADS`
skip guard in §8① are both shared with E04's edit surface. Neither is reconciled here.

Work happened only in `E:/AI/armature-E06`. Nothing was written into another seat's tree. E03's
outputs were **read** and copied *into* this tree; nothing was written back.

---

## 12. What this report does not claim

- That either output is good, correct, or usable. **The Director's eye judges.**
- That either figure is the same man as the reference. Canon, and his alone.
- Any ranking of D1 against D2, or of either against B1 or A1a, **on a magnitude**. E04's
  between-generation floor is unmeasured; every number here is a diagnostic and gates nothing.
- That control strength, control modality, or rigging were tested. None were touched.
