# S06 — report: the repaired performer on armature's own instrument

**Executor session, 2026-08-14, worktree `E:\AI\armature-S06`, branch `S06-run`.**
Binding documents were read from `main` at dispatch time, not from this worktree's
checkout: `CLAUDE.md`, `docs/dispatches/S06-repaired-performer-resurvey.md`,
`docs/dispatches/S03-ruling.md`, and facet's `docs/experiments/E34-ruling.md` (read-only).

**Zero credits. No cloud interaction of any kind** — no upload, no estimate call, no
submission surface touched. Every render, measurement and sheet ran locally.

Predictions were committed at `a6352e6` **before the first render** and are scored in §7
without a band moved. Nothing below judges whether the repair is good: facet's acceptance
is the standing verdict and the Director's eye is the judge of these panels and cells.

---

## 1. Task A — ground truth

### A1 · the watchdog, required ADVANCING rather than merely present

`pwsh -NoProfile -File E:\AI\training\_watchdog_start.ps1` reported an existing watchdog
2 s old, stopped it via sentinel, and brought up a new one at the standing ceiling
(VRAM 31200 MiB / RAM 90% / 87 °C, ×3 consecutive @ 2 s).

The heartbeat was then read twice, 8 s apart. **Both the file mtime and the timestamp
written inside the file moved**, which is the clause the dispatch hardened after the
measured 13.2-hour silent death:

| read | mtime (UTC) | content |
|---|---|---|
| 1 | `2026-08-14T17:14:05.699Z` | `2026-08-14T13:14:05.697-04:00` |
| 2 | `2026-08-14T17:14:14.381Z` | `2026-08-14T13:14:14.381-04:00` |

Δ = **8.682 s** across an 8 s sleep. Re-checked at session close: Δ = **6.48 s**,
advancing. Gate green at open and at close.

### A2 · both GLBs re-hashed

| asset | recorded | measured | bytes | verdict |
|---|---|---|---|---|
| E34 `facet_E34\out\performer_textured_8view.glb` | `ce793064…0113c5` | `ce7930643e573b475737eca676d9118b036d5e131c8b7af66a65b3b7ae0113c5` | 22,284,208 | **MATCH** |
| E33 `facet_E33\out\performer_textured.glb` | `9e20ea7d…b1aa` | `9e20ea7d800c0ffd2cff101a5e1bcc01fa13c620bbbe3ef05ae23b093547b1aa` | 21,588,628 | **MATCH** |

The relay's byte-unchanged claim for E33 is a measurement here, not an inheritance.

### A3 · the facet trees, read-only in both directions

Checked at open and at close — every manifest entry re-hashed, and the tree walked for
files the manifest does not list:

| tree | listed | missing | changed | unlisted | at open | at close |
|---|---|---|---|---|---|---|
| `facet_E33` | 117 | 0 | 0 | 0 | 0/0/0 | 0/0/0 |
| `facet_E34` | 84 | 0 | 0 | 0 | 0/0/0 | 0/0/0 |

E33's manifest records **itself** at `f8164e25…` / 14,008 B where the file now hashes
`18d264c5…` / 17,991 B. This is the known self-reference the dispatch named, reported
separately and never folded into the count; E34's manifest excludes itself by construction.
armature wrote nothing into either tree.

### A4 · the pre-known, quarantined before any Task-C note was written

facet's E34-ruling, Ruling 2, records three observations the Director accepted **with** the
repair. They were written into this seat's notes as pre-known before the survey ran:

1. the surface reads smoother, with less of the fine sculpted hatching
2. the brow/eye region on views 1/7 is more defined
3. a faint vertical tonal boundary runs down the back of the head and neck on views 3/5

None of the three is reported below as new. §3.4 records where each was seen.

---

## 2. Task B — the RGBA-true turnaround, and an instrument control

### 2.1 What was run

S03's `turn_rgba` manifest was enumerated first. **Every framing value it records equals the
tool's current module-level default** (352×1024 · 8 views · azimuth start 270° · sweep 360° ·
elevation 0° · 50 mm on 36 mm · `height_frac` 0.831), so S03 passed no framing overrides,
and reproducing it verbatim means passing none either. That is also the **more sensitive**
choice: an explicit flag would mask a drifted default, where relying on the default surfaces
it in the manifest comparison.

```
blender -b -P tools\render_turnaround.py -- --glb="E:\AI\training\facet_E34\out\performer_textured_8view.glb" --out="E:\AI\armature-S06\outputs\S06\turn_rgba_e34"
```

Output `outputs/S06/turn_rgba_e34/` — eight PNGs plus `turnaround_manifest.json` in S03's
shape (tool + Blender versions, GLB hash, per-view sha256, alpha extrema, gate records).
Blender 5.2.0 LTS `fbe6228777e7`, numpy 2.3.4, tool `S05.1`, elapsed 9.12 s.

### 2.2 Gate ALPHA, per view — no view failed, no view withheld

| view | az | alpha extrema | transparent | sha256 (first 16) |
|---|---|---|---|---|
| 0 | 270° | (0, 255) | 0.761441 | `df3c7420aac9a8a2` |
| 1 | 315° | (0, 255) | 0.757760 | `b0103cc259fc0407` |
| 2 | 360° | (0, 255) | 0.847248 | `5fc3dc35c1e0940f` |
| 3 | 405° | (0, 255) | 0.756356 | `bb18088c52f64984` |
| 4 | 450° | (0, 255) | 0.754131 | `2bd5e6d6b6c95e43` |
| 5 | 495° | (0, 255) | 0.756134 | `d22b1f3ca3675075` |
| 6 | 540° | (0, 255) | 0.846080 | `49656267a132a528` |
| 7 | 585° | (0, 255) | 0.760332 | `64a21cd987ceced7` |

Gate TURN: 8 distinct sha256 of 8 expected. Gate WHOLE: green on all eight.

### 2.3 The framing reproduced bit-exactly, and the geometry is unmodified by measurement

Against S03's recorded E33 manifest:

| quantity | delta |
|---|---|
| `import_info.total_vertices` | 399,140 both — **equal** |
| solved orbit `radius` | `1.7282408682988102` both — **0.000e+00** |
| per-view `height_frac`, `width_frac` (8 views) | worst **0.000e+00** |
| subject bbox lo/hi, camera target | 0.0 on all six components |
| camera type / n_views / azimuths / elevation / lens / sensor / fit | all MATCH |
| `staging` block | identical |

And the stronger form, measured on pixels rather than on the manifest: across all eight
views, **the number of pixels whose alpha differs between the E33 and E34 renders is 0**.
The silhouette is identical view for view. The premise "geometry unmodified by construction"
is therefore measured here, not carried. RGB differs on 16.1–26.0% of each frame — the figure
interior and its antialiased rim, i.e. the paint.

### 2.4 The instrument control — an addition to the dispatch, and the reason for it

Task C asks for S03's E33 renders beside S06's E34 renders, "same instrument both sides".
S03 ran tool version `S03.1`; the tool on `main` is now `S05.1`, three commits later
(`--ortho` in S04, `--ortho-scale` in S05). The dispatch's premise that the two sides share
one instrument was therefore inherited rather than measured, so it was measured: **E33 was
re-rendered through today's tool at S03's arguments** into `outputs/S06/control_e33/`.

| clause | result |
|---|---|
| pixel-identical to S03's eight recorded PNGs | **8/8**, max abs difference 0, differing pixels 0 |
| sha256-identical to the same eight files | **0/8** |

The pixels are bit-equal and the bytes are not. This is the standing law's own shape — *a
file-hash mismatch is not evidence a render changed; compare pixels* — sighted here on a
render that provably did not change. The comparison in §3 is instrument-controlled.

---

## 3. Task C — the survey panels, before beside after

### 3.1 The instrument did not fit the input, and what was done about it

`make_hole_survey` was built for S03's job: a **flat-alpha** old set with a baked grey void
beside an RGBA new set. It masks the old side by colour difference from `(154, 154, 157)` and
writes it to the panel uncomposited. S06's "before" is S03's **RGBA master**, and measured
before anything was changed:

* `figure_mask_old` marks **100% of the frame** as figure on an S03 master, against a true
  opaque fraction of **0.2255** — every interior number would be computed over the
  background as well as the figure
* the old side would sit on near-black while the new side sits on grey, putting a difference
  of backdrop into every panel — the confound the tool's own docstring exists to prevent

Running the tool as it stood would have reported the masking method as if it were texture.
The repair was pre-registered in the predictions commit before the run, not improvised: a
minimal `--old-rgba` branch, isolated in one function `old_side_plan` on the `--ortho`
pattern, so "the default path is untouched when the flag is absent" is a property of a
testable object. `--tag`, `--old-label` and `--new-label` were added alongside so the sheets
carry S06's provenance; all three default to S03's exact wording. Tool version `S03.1` →
`S06.1`.

**Five tests ride the same commit** (`tests/test_make_hole_survey.py`, 10 → 15), each written
against the specific way this code could be wrong: the colour reading swallowing an RGBA
master; the alpha reading being used with the flag; both sides landing on the same ground;
the default path byte-unchanged; and a symmetry test that fails if the flag is ignored.

**One test was written with a wrong expectation and is recorded rather than hidden.** Its
second half asserted the two readings *agree* on a flat-alpha input. They do not, and the
code was right: on a flat set the alpha is 255 everywhere, so the alpha mask marks the whole
frame — which is the entire reason `figure_mask_old` exists. The corrected assertion states
the true fact, which is sharper than the one intended: **each reading swallows the frame on
the input the other was built for.** The docstring carries that history.

### 3.2 What was run

```
<venv-python> tools\make_hole_survey.py --old="E:\AI\armature-S03\outputs\S03\turn_rgba"
  --new="E:\AI\armature-S06\outputs\S06\turn_rgba_e34" --out="…\outputs\S06\survey"
  --old-prefix=turn --new-prefix=turn --old-rgba
  --tag="S06 Task C - BEFORE E33 performer_textured.glb (9e20ea7d) beside AFTER E34 performer_textured_8view.glb (ce793064)"
  --old-label="BEFORE E33 turn_{i}" --new-label="AFTER E34 turn_{i}"
<venv-python> tools\sheet_compose.py …\_panels_view_{0..7}.json    (and _panels_contact.json)
```

Eight full-size per-view panels + one contact sheet in `outputs/S06/survey/`.

**A first composition was discarded and re-run.** With the GLB names as panel labels, the
two labels overlapped illegibly under a 352 px panel — the provenance, which is the reason
the label exists, was the thing that disappeared, on a sheet that still saved and still
looked finished. Provenance moved to the full-width title and the labels shortened.

### 3.3 The numbers — a locator, gating nothing

Low-saturation fraction at cut 0.20 over the eroded interior, and interior mean value:

| view | BEFORE sat<0.20 | AFTER sat<0.20 | Δ | BEFORE mean value | AFTER mean value | Δ |
|---|---|---|---|---|---|---|
| 0 | 0.00058 | 0.00028 | −0.00030 | 107.5 | 111.4 | +3.9 |
| 1 | 0.02594 | 0.00041 | −0.02553 | 77.0 | 83.1 | +6.1 |
| 2 | 0.03979 | 0.00024 | −0.03955 | 77.0 | 74.0 | −3.0 |
| 3 | 0.01966 | 0.00037 | −0.01929 | 88.5 | 79.2 | −9.3 |
| 4 | 0.00104 | 0.00053 | −0.00051 | 83.5 | 80.8 | −2.7 |
| 5 | 0.04905 | 0.00119 | −0.04786 | 69.7 | 74.0 | +4.3 |
| 6 | 0.05988 | 0.00142 | −0.05846 | 91.8 | 95.9 | +4.1 |
| 7 | 0.04144 | 0.00036 | −0.04108 | 115.4 | 119.4 | +4.0 |

Split into the named landmark bands as fractions of each view's **own** bbox height (a global
constant must not govern a local feature), reporting total and largest 4-connected component
together — the two-number form, so speckle and a patch are distinguishable
(`outputs/S06/survey/landmark_bands.json`):

* summed over all views and bands: **15,311 → 311** low-saturation interior pixels
* largest single cluster anywhere: **1,162 → 33**
* at the five named landmarks specifically, the largest surviving cluster is **23 px**
  (view 5, jaw/temple band)

Because saturation is also low on *dark* pixels, the residual was split by value — an
unpainted texel composited over `(154,154,157)` reads pale, a painted speck or crevice reads
dark. Of the 311 surviving pixels, the pale ones (value ≥ 130) concentrate on views 4/5/6 and
sit at **0.87–0.96 of figure height — the feet**, plus 3–15 px clusters at 0.08–0.10 inside
the ear concha on views 1/2/3.

### 3.4 The landmark notes, made at 3× native pixels

Read at native resolution magnified with NEAREST, BEFORE beside AFTER, crop boxes recorded in
`outputs/S06/survey/zoom/crop_boxes.json`. **Presence/absence at the five named landmarks —
jaw, temple, shoulder, ribcage, flank:**

| view | BEFORE | AFTER |
|---|---|---|
| 0 (front) | none at the five | none |
| 1 | pale region around the ear, across the jaw and down the neck | none |
| 2 (profile) | the largest in the set — temple, around the ear, jaw, neck | none |
| 3 | broad pale band over the crown/temple, behind the ear, down the neck; flank | none |
| 4 (back) | none at the five | none |
| 5 | temple; a long band down the shoulder blade and flank; hand | none |
| 6 (profile) | temple/crown, a wedge under the jaw down the neck; hand | none |
| 7 | temple; a band down the shoulder blade and armpit; flank | none |

**No pale unpainted patch reads at any of the five named landmarks on any of the six
previously-affected views.** The residual clusters counted in §3.3 read dark rather than
pale at those landmarks and are stated with their sizes there. What remains pale sits at the
feet and, at 3–15 px, inside the ear concha; whether the ear pixels are residual unpainted
texel or a lit surface is not this seat's call and is put in front of the Director's eye
with its size and location.

Where residual pale texels do appear, they read **grey, not white** — consistent with S03 R3,
which attributed the re-colouring to our staging.

**Pre-known observations, seen and recorded as pre-known** (§A4), not as findings:

* the smoother surface with less fine sculpted hatching — clearly present, most legible on
  the view 2 profile
* the more defined brow/eye on views 1/7 — present on view 1
* the faint vertical tonal boundary down the back of the head and neck on views 3/5 —
  present, and on our staging it reads as a distinct wavy vertical edge rather than a faint
  one, which is a statement about our lighting and not a new observation

**One factual observation this seat declines to classify.** Tonal boundaries of the same
visual character as pre-known observation 3 also appear away from the head and neck — on
view 7's shoulder blade, view 4's thighs, view 5's back, and down the flank on several views.
Whether these are the same phenomenon as the accepted seam or a different one is an
interpretation, and interpretation is not this seat's to make; they are recorded here so the
Director's eye has them, and they are **not** claimed as new.

---

## 4. Task D — the re-proof at the S04 preset

S04's Task-C invocations verbatim, GLB and output paths swapped, nothing else:

```
blender -b -P tools\render_turnaround.py -- --glb="E:\AI\training\facet_E34\out\performer_textured_8view.glb" --out="E:\AI\armature-S06\outputs\S06\ortho"  --views=8 --sweep=360 --elevation=30 --width=1024 --height=1024 --prefix=ortho --ortho
blender -b -P tools\render_turnaround.py -- --glb="E:\AI\training\facet_E34\out\performer_textured_8view.glb" --out="E:\AI\armature-S06\outputs\S06\persp" --views=8 --sweep=360 --elevation=30 --width=1024 --height=1024 --prefix=persp
<venv-python> tools\make_shotset_sheet.py --ortho=outputs/S06/ortho --out=outputs/S06/sheets --mode=shotset
<venv-python> tools\make_shotset_sheet.py --ortho=outputs/S06/ortho --persp=outputs/S06/persp --out=outputs/S06/sheets --mode=compare
```

### 4.1 Gates, all armed as they stand

| gate | result |
|---|---|
| ALPHA | **16/16** views across both sets at extrema (0, 255) |
| TURN | 8 distinct sha256 on each set |
| WHOLE | green, 8 rows each set |
| **CROP** (ortho path) | **silent on all eight cells** — tightest clearance 62 px (cell 1); range 62–86 px |

No gate raised anywhere in S06.

### 4.2 The pinned values reproduce S04 exactly

| quantity | S04 (E33) | S06 (E34) | delta |
|---|---|---|---|
| shared `ortho_scale`, solved | `1.1235359256161628` | `1.1235359256161628` | **0.0** |
| ortho standoff `radius` | `2.0507605025880484` | `2.0507605025880484` | **0.0** |

`projection: ORTHO`, `shared_across_views: ortho_scale`, `blender_camera_type: ORTHO`;
perspective sibling at radius 1.619121. Source hash `ce793064…` on both sets.

Sheets: `outputs/S06/sheets/S04-shotset.png` (8426×1326) and
`S04-ortho-vs-perspective.png` (8426×2476), both built with no refusal raised.

### 4.3 The seam line, at the cells the Director's zoom ruled on

S04's ruling recorded his eye reading the pale seam on the profile cells at **jaw, ear, neck,
shoulder, flank, knee**. Those cells, E33 beside E34 through one instrument
(`outputs/S06/sheets/zoom/`):

| ortho cell | E33 low-sat interior (pale) | E34 low-sat interior (pale) |
|---|---|---|
| 0 | 70 (45) | 20 (7) |
| 1 | 1412 (125) | 33 (3) |
| 2 — profile | 1463 (63) | 51 (12) |
| 3 | 1043 (110) | 33 (15) |
| 4 | 226 (119) | 57 (42) |
| 5 | 3002 (631) | 63 (50) |
| 6 — profile | 2171 (649) | 58 (49) |
| 7 | 2343 (883) | 50 (36) |

At 3× on the profile cells: the E33 cell carries pale strips at temple, around the ear, along
the jaw, down the neck and across the shoulder; **the E34 cell carries none of them at those
sites.** The pale pixels that remain on the E34 cells sit at the feet (0.87–0.96 of figure
height) on cells 0/4/5/6/7, and at 3–15 px inside the ear concha on cells 1/2/3.

### 4.4 Two observations on the sheets themselves

1. **The shotset sheet's standing caption now points at the wrong state.** It reads
   *"texture holes on the subject are pre-known (facet's arc) and are not findings here"* —
   written for S04's unrepaired subject and now captioning repaired paint. It was **left
   unchanged deliberately**: the dispatch asked for the S04 preset verbatim, and S04's record
   depends on that text. Flagged for the advisor rather than edited mid-run.
2. The 51-row placement difference is untouched by this run and rides to the Director with
   H-S04c, as S04-ruling R2.4 deferred it.

### 4.5 The two deferred verdicts

Both are the Director's alone, per the E14 law, and no seat grades them here:

* **H-S04c** — whether the ortho cells read as sprite cells, now on repaired paint.
  Artifacts: `outputs/S06/sheets/S04-shotset.png` at full size, and the eight
  `outputs/S06/ortho/ortho_{0..7}.png` cells at his own zoom.
* **the 51-row placement question** — `outputs/S06/sheets/S04-ortho-vs-perspective.png`.

---

## 5. The suite

| pass | result |
|---|---|
| ordinary (`pytest -q`) | **1266 passed, 48 skipped**, 32.2 s, exit 0 |
| optimized (`python -O -m pytest -q`) | **1266 passed, 48 skipped**, 29.7 s, exit 0 |
| main at the S05 close-merge | 1296 passed, 13 skipped |

The worktree count is stated beside main's and **asserts nothing beyond S04-ruling R4's
measured grouping**: main's checkout carries historical gitignored `outputs/` artifacts that
no worktree does, so 35 tests that pass on main skip here, and 13 + 35 = **48**. Passing then
reads 1296 − 35 + 5 = **1266**, where 5 is the tests this run adds. Both passes agree, which
is the clause that matters for a repo whose gates must survive `-O`.

## 6. Compensators

Nothing irreversible ran. Zero credits, zero uploads, no external surface touched. Outputs
delete by directory (`outputs/S06/`, gitignored); the branch reverts by `git revert`; facet's
trees were opened read-only and measured 0/0/0 at open and close. Owner: this executor
session.

## 7. Predictions, scored — 23 of 25 clauses

Scored against `docs/dispatches/S06-predictions.md` at `a6352e6`. No band was moved.

| id | prediction | outcome |
|---|---|---|
| P1a | control pixel-identical 8/8 | **HIT** — 8/8, max abs diff 0 |
| P1b | control sha-identical 8/8 | **MISS** — 0/8; pixels bit-equal, bytes differ |
| P2a | alpha (0,255) 8/8 | **HIT** |
| P2b | TURN 8 distinct, WHOLE green | **HIT** |
| P3a | vertices = 399,140 | **HIT** |
| P3b | radius within 1e-9 | **HIT** — delta 0.0 |
| P3c | height/width frac within 1e-6 | **HIT** — delta 0.0 |
| P4a | sat<0.20 falls on views 1,2,3,5,6,7 | **HIT** — all six |
| P4b | \|Δ\| < 0.01 on views 0 and 4 | **HIT** — 0.00030, 0.00051 |
| P5 | no unpainted patch at the five landmarks on the six affected views | **HIT** at the eye and at 3×; residual cluster sizes reported beside it in §3.3 |
| P6 | residual pale texels read grey, not white | **HIT**, conditional clause held where residuals exist |
| P7 | interior mean value within ±6 on all eight views | **MISS** — 6 of 8 within; view 1 at +6.1 and view 3 at −9.3 exceed |
| P8 | ≥1 pre-known observation visible, recorded as pre-known | **HIT** — all three were |
| P9a | ALPHA 16/16 | **HIT** |
| P9b | CROP silent on ortho | **HIT** |
| P9c | ortho_scale within 1e-9 | **HIT** — delta 0.0 |
| P9d | ortho radius within 1e-9 | **HIT** — delta 0.0 |
| P9e | both sheets build | **HIT** |
| P10 | no unpainted patch at the S04 profile-seam landmarks on the E34 ortho cells | **HIT** at 3× |
| P11a | worktree skips = 48 | **HIT** |
| P11b | passing = 1296 − 35 + N | **HIT** — 1266 with N = 5 |
| P11c | 3 ≤ N ≤ 8 | **HIT** — N = 5 |
| P11d | `-O` same counts | **HIT** |
| P12 | no gate raises anywhere | **HIT** |
| P13 | default path unchanged with `--old-rgba` absent | **HIT** — asserted by test |

**The two misses, owned.** P1b was written at 55% and named its own resolution in advance:
pixels are the contract, bytes are not, and a byte difference on a render whose pixels are
bit-equal is the standing law being illustrated rather than broken. **P7 is the substantive
miss.** It was reasoned from facet's texture-space measurement (mean luma 112.82 vs 112.73,
same material) to a *rendered interior* mean, and those are different populations: the
eroded interior of a render is dominated by which texels are visible at that azimuth, and
replacing a large pale unpainted band with paint moves that mean by more than the material's
own luma moved. Views 1 and 3 are two of the views that carried the largest bands. This is
the unit/population family again — the object being averaged was not the object facet
measured.

## 8. Standing items this run did not touch

The hosted-tier revalidation remains out of scope and unspent — the Director's pricing
decision, standing estimate 106–211 credits per generation, unchanged. No texture work, no
generation, no edit to either facet tree, no route created or displaced.

## 9. Artifacts

```
outputs/S06/turn_rgba_e34/   8 RGBA masters + turnaround_manifest.json   (Task B)
outputs/S06/control_e33/     8 RGBA masters + manifest                   (instrument control)
outputs/S06/survey/          8 per-view panels, contact.png, survey.json,
                             landmark_bands.json, panels/, zoom/         (Task C)
outputs/S06/ortho/           8 cells + manifest                          (Task D)
outputs/S06/persp/           8 cells + manifest                          (Task D)
outputs/S06/sheets/          S04-shotset.png, S04-ortho-vs-perspective.png, zoom/
```

Big binaries stay out of git; the record is this report, the predictions, the manifests and
the per-view sha256 they carry.
