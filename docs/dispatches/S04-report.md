# S04 — report: the turnaround instrument at parallel projection

**Executor session, 2026-08-13, on `S04-run` at `E:\AI\armature-S04`. Zero credits, zero
cloud calls of any kind — no upload, no estimate, no submission surface touched. Nothing
left the rig.** Four commits, unmerged, pushed. No gate fired at any point; nothing was
improvised past.

This report contains measurements and sheets. It rules on nothing. The words the executor
rules forbid do not appear in it, and the cells go to the Director's eye.

## Conduct

| step | state |
|---|---|
| binding documents read from `main`, not from the worktree checkout | CLAUDE.md, the S04 spec, the S03 ruling — before any edit |
| VRAM watchdog | checked at session start (`_watchdog_start.ps1`, "watchdog UP") and re-checked before the Task-C batch: heartbeat **1 s** old, 7,672 / 32,607 MiB in use |
| all Blender work | PowerShell, headless `-b -P` only |
| interfaces enumerated before extending | `render_turnaround.py`, `armature_core.turnaround`, `framing.project`, `startframe.silhouette_extent` / `framing_cloud` / `gate_whole` / **`mask_bbox`**, and the `sheet_compose` family |
| predictions | committed at `1441ded`, **before any S04 measurement was read** |
| memory store | not written to |
| gates fired | none |

**Enumeration paid twice.** `startframe.mask_bbox` already existed, Blender-free and for
exactly this purpose, so Gate CROP's measurement reuses it instead of commissioning a
second bbox implementation. `sheet_compose` already sized a sheet to its text and pasted
panels 1:1 without resampling, which is the property a constant-scale claim needs, so the
new sheet tool adds only the cell treatment and hands layout to it.

## Task A — the flag

`render_turnaround --ortho` renders a parallel-projection shot-set. One `ortho_scale` is
shared by every cell, solved by bisection through `framing.project` from the **largest**
silhouette over the whole azimuth set — the same doctrine the radius solve already follows,
so the composition the solve returns and the composition Gate WHOLE measures cannot
disagree. Under parallel projection screen size does not depend on distance, so the radius
keeps only a standoff role and is derived from the subject's own bounding sphere
(`ORTHO_STANDOFF_SPHERES = 4.0`) rather than from a constant in metres.

**The branch is `turnaround.projection_plan` and nothing else.** Task A's structural
invariant is therefore a property of one pure, importable object rather than of a careful
reading of the render loop. `framing.project` and `startframe.silhouette_extent` take
`ortho_scale=None` as the path they already had; the perspective arithmetic is untouched
and is pinned against a hand-written copy of the pre-S04 formula across three frames and
three angles. The default-branch test runs through the **real parser**, so flipping the
flag's default cannot leave it green.

Provenance records `projection`, `blender_camera_type`, `shared_across_views`, the shared
`ortho_scale` and its solve record, the per-view subject bbox, and a predicted-vs-measured
delta. **One manifest key is added on the perspective side too** — `projection: "PERSP"` —
which changes no pixel and no camera parameter; a manifest that does not say which
projection produced it seemed worse than the one-key difference. Flagged rather than
assumed.

## Task B — Gate CROP

`turnaround.gate_view_crop` raises in-tool, per view, on the ortho path.

The shared scale is fitted to `silhouette_extent` over a cloud `framing_cloud` has already
decimated to its cap, so the solve sees a **lower bound** on the silhouette and geometry
falling between strides crops the cell. Every other check passes on that cell: Gate ALPHA
passes on a cropped figure, Gate TURN passes on eight distinct cropped views, and **Gate
WHOLE passes by construction**, because it reads the same decimated projection the solve
was fitted to — it is structurally incapable of seeing this. CROP reads the rendered alpha,
which is the only place the real silhouette exists.

Two clauses, and the vacuity one comes first: a cell nobody rendered into touches no border
and would sail through a contact-only gate, passing *because* the failure was total. That
clause does not lean on Gate ALPHA having run, because an andon that is load-bearing only
in another andon's presence is not an andon.

Red tests fire on each of the four borders, with the right and bottom cases at the
**inclusive last index** — a gate written `x1 >= width` passes a cell whose right side is
sheared off. Three CROP cases joined the existing `-O` / `PYTHONOPTIMIZE=1` probe.

### The one scope reading this seat made, surfaced rather than settled

**Gate CROP arms on the ortho path only.** Task B's rationale is the shared-scale solve,
and Task A's invariant is that the perspective path is untouched when the flag is absent —
a new raising gate there is a behaviour change to it. The border-contact measurement is
taken on **both** paths and rides both manifests either way, so ruling that CROP should arm
on perspective too needs no re-run to decide. The perspective set's measured clearances are
in the table below; the tightest is 58 px.

## The calibration — the spec's ASSUMED premise, resolved

The spec marks "Blender 5.2 headless supports `camera.type='ORTHO'` + `ortho_scale`" as
ASSUMED, to be settled by the first unit render. `tests/blender/check_ortho_convention.py` is
that render, kept as a fixture. It runs at **352x1024**, because the Task-C preset is square
and a square frame cannot distinguish the two candidate ortho fits at all.

| claim | measured |
|---|---|
| Blender accepts ORTHO and keeps the scale | `type` reads back `ORTHO`, `ortho_scale` reads back `2.0` on Blender 5.2.0 LTS `fbe6228777e7` |
| `ortho_scale` spans the **longer** axis | a 0.4-unit cube measures **203 px** wide against the repo convention's predicted 204.8. The transposed convention predicts 70.4 — a 2.9x separation, so this could not come out ambiguous |
| a square world span renders square | 203 x 203 px |
| parallel projection is distance-independent | radius 3 and radius 30 return the **byte-identical** bbox `[74, 794, 277, 997]` |
| `Image.pixels` row order | **bottom-up.** The cube sits high in the world; the projector puts it at rows 25.6..230.4 top-down and the raw array returns 794..997, which is that box reflected through the frame (1023−230.4 = 792.6, 1023−25.6 = 997.4) |
| `ortho_scale` is read, not merely accepted | doubling it to 4.0 halves the subject to 101 x 101 px |

**Why the row order needed its own instrument, measured rather than argued.** The first
attempt asserted the predicted-vs-measured delta would expose a flipped read. It does not,
at any aspect: the solve centres the figure, so a vertical flip maps the box to itself — at
`height_frac` 0.831 in 1024 rows the flipped box differs by **one pixel**. The replacement
probe (where does the subject's crown fall *within* the measured box) fails for the same
reason — the box flipped too — and it failed its own red test before reaching the tree. What
is in the tree instead is a decomposition: `_measure_alpha_plane` is Blender-free and tested
against a synthetic plane whose subject sits in the last three rows, and the premise it
rests on is measured by the calibration above. Get this wrong and Gate CROP fires correctly
and names the wrong border in every report it ever writes.

## Task C — the proof shot-set

Verbatim invocations, pinned:

```
blender -b -P tools\render_turnaround.py -- --glb="E:\AI\training\facet_E33\out\performer_textured.glb" --out="E:\AI\armature-S04\outputs\S04\ortho" --views=8 --sweep=360 --elevation=30 --width=1024 --height=1024 --prefix=ortho --ortho
```
```
blender -b -P tools\render_turnaround.py -- --glb="E:\AI\training\facet_E33\out\performer_textured.glb" --out="E:\AI\armature-S04\outputs\S04\persp" --views=8 --sweep=360 --elevation=30 --width=1024 --height=1024 --prefix=persp
```
```
<venv-python> tools\make_shotset_sheet.py --ortho=outputs/S04/ortho --out=outputs/S04/sheets --mode=shotset
<venv-python> tools\make_shotset_sheet.py --ortho=outputs/S04/ortho --persp=outputs/S04/persp --out=outputs/S04/sheets --mode=compare
```

**The GLB was re-hashed at start**, as the spec requires:
`E:\AI\training\facet_E33\out\performer_textured.glb`, 21,588,628 bytes, sha256
`9e20ea7d800c0ffd2cff101a5e1bcc01fa13c620bbbe3ef05ae23b093547b1aa` — matching the premise
row's `9e20ea7d…` and the S03 ruling's lineage. `E:\AI\training` was opened read-only.
**The texture holes and the S03 patches on this asset are pre-known (facet's arc) and are
not S04 findings**; they are visible in the beauty cells.

### The perspective sibling had to be rendered, not reused — disclosed

The spec asks for a second sheet placing the ortho cells "beside the existing perspective
turnaround at the same elevation." The existing kit
(`E:\AI\armature-S03\outputs\S03\turn_rgba`, read-only) is at **elevation 0.0 and
352x1024** — its manifest records `radius 1.7282408682988102`, `height_frac 0.831`, the
same GLB. Pairing it against a 30° 1024x1024 ortho set would confound elevation and frame
with projection. So the perspective sibling was re-rendered at the **identical** preset with
the flag absent, making projection the only difference — which also exercises the perspective
path live. `make_shotset_sheet` refuses a cross-elevation comparison in code, with a test.

### Gates

| gate | ortho set | perspective set |
|---|---|---|
| ALPHA | 8/8, extrema (0, 255) on every view | 8/8, extrema (0, 255) on every view |
| TURN | 8 distinct views, as many as asked for | 8 distinct views, as many as asked for |
| WHOLE | 8/8 | 8/8 |
| CROP | **8/8, armed**; tightest clearance 62 px | not armed (see the scope reading above); measured, tightest clearance 58 px |

Shared `ortho_scale` = **1.1235359256161628**, one number across all eight cells.
Ortho radius 2.050761 (standoff only); perspective radius 1.619121. Ortho run 7.03 s
wall-clock for 8 views; perspective 7.25 s.

### Per view

`h` is Gate WHOLE's projected height fraction; `px h` and `px w` are the **rendered** alpha
bbox; `ctr` is the rendered silhouette's vertical centre row in a 1024-row frame.

| view | az | ORTHO h | px h | px w | rows | ctr | PERSP h | px h | px w | rows | ctr |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 270 | 0.8094 | 829 | 305 | 108..937 | 522.5 | 0.8033 | 822 | 300 | 59..881 | 470.0 |
| 1 | 315 | 0.8310 | 855 | 230 | 106..961 | 533.5 | 0.8310 | 853 | 222 | 58..911 | 484.5 |
| 2 | 360 | 0.8274 | 849 | 149 | 108..957 | 532.5 | 0.8265 | 847 | 132 | 59..906 | 482.5 |
| 3 | 405 | 0.8058 | 834 | 248 | 111..945 | 528.0 | 0.8036 | 829 | 232 | 60..889 | 474.5 |
| 4 | 450 | 0.8072 | 829 | 305 | 112..941 | 526.5 | 0.8030 | 823 | 304 | 61..884 | 472.5 |
| 5 | 495 | 0.8192 | 841 | 230 | 112..953 | 532.5 | 0.8161 | 839 | 219 | 61..900 | 480.5 |
| 6 | 540 | 0.8247 | 849 | 149 | 109..958 | 533.5 | 0.8199 | 848 | 136 | 60..908 | 484.0 |
| 7 | 585 | 0.8125 | 841 | 248 | 106..947 | 526.5 | 0.8071 | 834 | 238 | 59..893 | 476.0 |

Per-view ortho clearances (px): 86, 62, 66, 78, 82, 70, 65, 76.
Per-view perspective clearances (px): 59, 58, 59, 60, 61, 61, 60, 59.

### One difference nobody predicted

The two sets place the figure at **different heights in the frame**: mean rendered
silhouette centre **529.4** (ortho) against **478.1** (perspective), in a frame whose centre
is 511.5 — a 51-row separation, larger than the entire per-view height spread of either set.
Both cameras look at the same target and the target projects to frame centre in both. Under
perspective at 30° of elevation the crown is nearer the lens than the feet and subtends more,
which moves the silhouette up; parallel projection has no such term. Reported as measured;
what it means for a sprite cell is the Director's.

## Predictions, scored

Registered at `1441ded` before any measurement was read. Blindness disclosed in that file:
not blind to the spec or its three hypotheses, not blind to the Task A/B code this session
wrote, blind to every measurement.

**A defect in the pre-registration, disclosed rather than repaired.**
`docs/dispatches/S04-predictions.md` line 29 contains one of the forbidden words — it
describes the proof GLB's hash as "re-verified this session." It is a statement about a
hash comparison and not a judgement of any output, but the executor rule is flat and the
word should not have been written. **The file has not been edited.** S03's ruling settled
this case: disclosing a forbidden word in a pre-registration is the only correct repair,
because editing a pre-registered document after seeing results is the thing pre-registration
exists to prevent. The report's own text was corrected before commit, where no such
constraint applies.

| id | clause | outcome |
|---|---|---|
| P-C1 | ORTHO + scale readback | **HIT** both clauses |
| P-C2a/b/c | 195–215 px wide; transposed 70.4 excluded; as tall as wide | **HIT** all three (203 / excluded / 203) |
| P-C3 | direction: bottom-up, raw rows above the midline | **HIT** |
| P-C3 | numeric sub-clause: raw rows ≈ 844..946 | **MISS** — measured 794..997. This seat's hand arithmetic halved the cube's half-height twice; the tool's projector had 25.6..230.4 right the whole time. Scored as written |
| P-C4 | identical bbox at 10x the standoff | **HIT** — byte-identical |
| P-C5 | ≈102 px at double the scale | **HIT** — 101 px |
| P-T1 | 8/8 ortho views, ALPHA green | **HIT** |
| P-T2 | Gate CROP silent on all 8 | **HIT** — tightest clearance 62 px |
| P-T3a | `abs(delta_px) ≤ 10` on all sides of all 8 | **HIT** — worst 7.93 px |
| P-T3b | measured-wider sign pattern on ≥6 of 8 | **MISS** — 4 of 8, and the split is structured: it holds on all four **45° views** (1, 3, 5, 7) and fails on all four **axis-aligned** ones (0, 2, 4, 6), where `framing_cloud` keeps the world-axis extremes that *are* the screen extremes, the projection is near-exact, and the residual (−0.6 to −0.93 px) is anti-aliasing pulling the thresholded silhouette in rather than decimation pushing it out |
| P-T4 | perspective sibling ALPHA 8/8 and WHOLE 8/8 | **HIT** both clauses |
| P-T5 | exactly one ortho view at 0.831, none above | **HIT** — view 1 at 0.8310, all others below |
| P-T6 | `min(height_frac)` higher for ortho than perspective | **HIT, and the margin is small** — 0.8058 vs 0.8030. Rendered pixel-height spread points the same way and is also small: **26 px** (ortho) against **31 px** (perspective). One run, no repeat-variance measured. The direction is as predicted; the magnitude does not carry much on its own |
| P-T7 | 5–30 s per view | **MISS** — 7.03 s for the whole 8-view run, about 0.88 s per view |

**H-S04c gets no verdict from this seat**, per the E14 law the spec cites. The cells are on
the sheets.

## For the advisor

1. **Gate CROP's arming.** Ortho-only, for the reason above. The perspective measurement is
   already in the manifest if the ruling goes the other way; no re-run needed.
2. **The one perspective-side manifest key** (`projection: "PERSP"`), added deliberately.
3. **P-T6's small margin.** The instrument's own purpose came out in the predicted
   direction on a single run with no noise floor measured. A lay figure is close to
   axisymmetric and a 50 mm lens at radius 1.62 is not a strong perspective; a subject with
   more depth variation would be a harder test of the same clause.
4. **The 51-row placement difference**, unpredicted and unexplained by anything the spec
   anticipated.

## Suite

| tree | passed | skipped | collected |
|---|---|---|---|
| `S04-run` worktree | **1207** | **48** | 1255 |
| `S04-run` worktree, `-O` | **1207** | **48** | 1255 |
| `main` @ `7e37ca2` | **1183** | **13** | 1196 |

S04 adds **59** tests (40 `test_turnaround_ortho.py`, 8 `test_ortho_convention.py`, 11
`test_make_shotset_sheet.py`), which is exactly the collected delta. The `-O` pass is
identical to the plain pass, and the three new Gate CROP cases ride the existing
optimization probe.

**The skew, reported and not asserted about.** The worktree carries 35 more skips than
main. Every one of the 35 is in three files — `test_gate_s.py` (16),
`test_build_payload.py` (16), `test_measure_tracking.py` (3) — and every one names a
gitignored output artifact ("E02 payloads are gitignored output", "E03 upload records are
gitignored output", "E02 runs are gitignored output"). main's 13 skips are a strict subset
of the worktree's 48. 35 is the same gap E13 flagged and S03 sighted a second time. **This
seat asserts nothing about the cause**; the grouping above is the measurement, and the
ruling is the advisor's.

## Credits and disclosure

**0 credits. 0 cloud calls.** No upload, no estimate call, no submission surface touched;
no partner API, no saved workflow, no Comfy interaction of any kind. This route is fully
local: the GLB is read from the rig, Blender renders on the rig, the sheets are composed on
the rig, and **nothing leaves it**. No new model, weight, LoRA, preprocessor or code
dependency entered the pipeline, so **no licence row is introduced**; Blender is the
standing tool.

## Compensators

| act | compensator | owner |
|---|---|---|
| PNGs + manifests under `outputs/S04/` | delete the directory | executor session |
| calibration PNGs under `outputs/_test_ortho_convention/` | delete the directory | executor session |
| four commits on `S04-run`, pushed, unmerged | `git revert`, or delete the branch | executor session |
| `E:\AI\training` | none needed — opened read-only, never written |

## Standards compliance

| standard | score | evidence |
|---|---|---|
| PIN_PER_STEP | 3 | GLB hash re-measured at start; tool + Blender + numpy versions, per-view sha256, the shared ortho_scale, both solve records, and the verbatim invocations all in `outputs/S04/S04-manifest.json` and above. The calibration is a committed fixture that re-runs on demand |
| ANDON_AUTHORITY | 3 | Gate CROP raises in-tool with a vacuity clause and red tests on all four borders at the inclusive last index; it joins the `-O`/`PYTHONOPTIMIZE` probe. Watchdog checked before the batch. No gate fired and none was improvised past |
| NAMED_COMPENSATORS | 3 | table above; every act reversible by directory delete or `git revert`; zero credits and zero uploads by construction, so nothing irreversible was reachable |
| DECOMPOSE_BY_SECRETS | 3 | the projection branch isolates in one pure function; the alpha measurement splits from the Blender load so the row flip is testable; layout stays in `sheet_compose` and only cell treatment is new; `mask_bbox` reused rather than reimplemented |
| UNCERTAINTY_GATED_HUMANS | 3 | two sheets to the Director's eye before anything consumes the set; H-S04c left to him explicitly; four items surfaced to the advisor contrastively rather than settled by this seat |
| EXTERNAL_VERIFIER | 2 | alpha arithmetic, border contact and the calibration are mechanical and Blender-side rather than self-reported; the advisor (a different seat) rules on this report; the standing human verifier judges the cells. Not 3: no second model family checked this seat's work |

## What is for the Director's eye

`outputs/S04/sheets/S04-shotset.png` — the eight ortho cells, 8426 x 1326.
`outputs/S04/sheets/S04-ortho-vs-perspective.png` — parallel above perspective at the same
elevation, same GLB, same frame, 8426 x 2476.

Cells are pasted 1:1 and never resampled, composited over RGB(38, 38, 42) with a 1 px
border so a figure touching its cell edge reads as touching it, and every cell on a sheet
carries horizontal rules at the same two frame rows as a ruler. Sheets locate; full size
decides. The texture holes are pre-known and are not findings here.
