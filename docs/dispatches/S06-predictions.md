# S06 — the executor's predictions, committed before the first render

**Written and committed before any render, any survey panel, any sheet, and before any
tool edit.** No S06 output existed on this rig when this file was committed.

## Blindness, disclosed honestly

**Not blind to facet's numbers.** Task A required reading `E34-ruling.md`, so this seat
knew, when writing every line below:

* holes into finalize 927,492 → **157,228**; largest DILATION component 22,457 → **7,390**;
  styled/valid 62.1% → 93.6%; finalize source distance median 2.974 → 1.822 edges
* the two pole views (0/4) reproduce their E33 **projection-registration** numbers to the
  digit — a statement about the projection run's own measurements, not a claim that the
  rendered pixels of views 0/4 are unchanged
* Ruling 2's three accepted observations, held as **pre-known** and quarantined from the
  word "new": smoother surface with less fine sculpted hatching · brow/eye more defined on
  views 1/7 · a faint vertical tonal boundary down the back of the head and neck on views 3/5

**Blind to everything on armature's own instrument.** No E34 render exists on this rig at
write time; no S06 survey number, panel or shot-set cell has been seen. The prior record
consulted for baselines: S03's `turnaround_manifest.json`, S03's report and ruling, S04's
report and ruling, and S04's `outputs/S04/ortho/turnaround_manifest.json`.

Three quantities were measured before this file and are stated as measurements, not
predictions, so they cannot be scored as hits: the watchdog heartbeat advanced across an
8 s read pair; both GLB hashes match their relayed values; and
`make_hole_survey.figure_mask_old` marks 100% of an S03 RGBA master as figure against a
true opaque fraction of 0.2255.

## The predictions

A **view** is one rendered azimuth cell at the stated preset. Each clause is scored
separately; a conjunction is never scored as one line.

### Task B — the E34 turnaround, and the instrument control

| id | clause | prediction | confidence |
|---|---|---|---|
| P1a | re-rendering **E33** through today's `render_turnaround.py` (`S05.1`) at S03's arguments reproduces S03's eight recorded PNGs **pixel-identically** (exact array equality, all 8) | YES | 75% |
| P1b | that same re-render is also **sha256-identical** to S03's eight files | YES | 55% — pixels are the contract; encoder or metadata drift would break bytes without breaking the comparison |
| P2a | E34 renders 8 views; alpha extrema `(0, 255)` on all eight; Gate ALPHA green 8/8 | YES | 90% |
| P2b | Gate TURN reports 8 distinct sha256; Gate WHOLE green on all eight | YES | 92% |
| P3a | E34's `import_info.total_vertices` equals S03's recorded **399,140** exactly | YES | 80% — texture-space repair, geometry unmodified by construction; a re-export could still renumber |
| P3b | E34's solved orbit `radius` equals S03's **1.7282408682988102** to within 1e-9 | YES | 78% |
| P3c | per-view `height_frac` and `width_frac` match S03's to within 1e-6 on all eight views | YES | 75% |

### Task C — the survey panels

| id | clause | prediction | confidence |
|---|---|---|---|
| P4a | eroded-interior low-saturation fraction at cut 0.20 **falls** (E33 → E34) on all six previously-affected views 1,2,3,5,6,7 | YES | 85% |
| P4b | on views 0 and 4 that same quantity moves by \|Δ\| < 0.01 | YES | 60% — S03 read them clean by eye, which does not force "unchanged by number" when the whole atlas is new |
| P5 | at full size, **no** unpainted patch is present at any of the five named landmarks (jaw, temple, shoulder, ribcage, flank) on any of the six affected E34 views | YES | 78% |
| P6 | any residual unpainted texels visible on our E34 panels read **grey**, not white — S03 R3 measured that our staging re-colours them | YES, conditional on residuals existing at all | 85% |
| P7 | per-view interior `mean_value` on the E34 side sits within ±6 of the E33 side on all eight views — facet measured texture-space mean luma 112.82 vs 112.73, and our staging is identical on both sides | YES | 70% |
| P8 | at least one of Ruling 2's three pre-known observations is visible on our panels; it is recorded as pre-known and never as a finding | YES | 80% |

### Task D — the re-proof at the S04 preset

| id | clause | prediction | confidence |
|---|---|---|---|
| P9a | ortho and perspective each render 8/8; Gate ALPHA green **16/16** across the two sets | YES | 90% |
| P9b | Gate CROP is silent on the ortho path | YES | 85% |
| P9c | the solved shared `ortho_scale` for E34 equals S04's E33 value **1.1235359256161628** to within 1e-9 | YES | 78% |
| P9d | the ortho standoff `radius` equals S04's **2.0507605025880484** to within 1e-9 | YES | 78% |
| P9e | both sheets build — `--mode=shotset` and `--mode=compare` — with no refusal raised | YES | 90% |
| P10 | at the S04-profile landmarks that carried the seam the Director's zoom found on the E33 ortho cells, the E34 ortho cells carry no unpainted patch | YES | 75% |

### The suite

| id | clause | prediction | confidence |
|---|---|---|---|
| P11a | worktree skips = **48** — main's 13 plus S04-ruling R4's measured 35 gitignored-artifact skips, asserting nothing beyond that grouping | YES | 88% |
| P11b | worktree passing = **1296 − 35 + N**, where N is the number of tests this run adds | YES | 80% |
| P11c | N is between 3 and 8 inclusive | YES | 70% |
| P11d | the `-O` pass reports the same counts as the ordinary pass | YES | 90% |

### The gates

| id | clause | prediction | confidence |
|---|---|---|---|
| P12 | no gate raises anywhere in S06 | YES | 82% — the dispatch expects no raise on any arm; this line exists so that a raise is scored as a miss rather than absorbed as ordinary |

## A named risk this seat carries into the run

**Task C's instrument does not fit Task C's inputs as the tool stands.**
`make_hole_survey` was built for *flat-alpha old beside RGBA new*: it masks the old side
by colour difference from a baked void and writes that side to the panel uncomposited.
S06's "before" is S03's **RGBA master**, so as the tool stands the old side would be masked
at 100% of frame and the two panels would sit on different backdrops — the exact confound
the tool's own docstring exists to prevent.

Intended repair: a minimal `--old-rgba` branch that composites and masks both sides
identically, leaving behaviour unchanged when the flag is absent, with tests riding the
same commit (the `--ortho` pattern — the branch is one testable object).

| id | clause | prediction | confidence |
|---|---|---|---|
| P13 | with `--old-rgba` absent, the tool's output is unchanged from today's behaviour | YES | 90% |
