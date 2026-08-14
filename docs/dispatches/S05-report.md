# S05 — report: the roster scale pin

**Executor session, 2026-08-13, on `S05-run` at `E:\AI\armature-S05`. Zero credits, zero
cloud calls of any kind — no upload, no estimate, no submission surface touched. Nothing
left the rig.** One andon fired, on the arm the spec wrote it for; it was **not the andon
the spec named**, and nothing was improvised past it.

This report contains measurements and one sheet. It rules on nothing. The words the
executor rules forbid do not appear in it, and the cells go to the Director's eye.

## Conduct

| step | state |
|---|---|
| binding documents read from `main`, not from the worktree checkout | CLAUDE.md, the S05 spec, the S04 report, the S04 ruling — before any edit |
| VRAM watchdog | `_watchdog_start.ps1` at session start reported a stale heartbeat from a previous run, cleared it and re-armed: **"watchdog UP — kill@ VRAM 31200 MiB"**. Re-checked immediately before the first render: heartbeat **1.6 s** old, 7,235 / 32,607 MiB in use |
| all Blender work | PowerShell, headless `-b -P` only |
| interfaces enumerated before extending | `render_turnaround`'s parser / branch / manifest writer, `armature_core.turnaround` (`projection_plan`, `gate_view_crop`), `framing.project` / `ortho_half_spans`, `startframe.silhouette_extent` / `gate_whole` / `mask_bbox`, `make_shotset_sheet`'s `load_set` / `row_title` / `build`, and **both** existing `-O` probes |
| predictions | committed at `75b943e`, **before any Blender run of this session** |
| memory store | not written to |
| andons fired | **one — Gate WHOLE, arm PINNED-TIGHT, view 0.** Recorded and the arm stopped; no retry, no pin adjusted, no sweep continued |

**Enumeration paid twice again.** The `-O` probe already existed in two places, so S05's
plan refusals joined `test_turnaround.py`'s rather than getting a third harness — under
their own `except`, because widening the existing one to `ArmatureError` would have turned
every `WRONG_ERROR` outcome already in it into a silent pass. And `sheet_compose`'s layout
and `make_shotset_sheet`'s cell treatment both stood; the new mode adds tag derivation and
three refusals and nothing else.

**The venv, disclosed.** The worktree has no `.venv`; the suite and the sheet ran on the
repo venv at `E:\AI\armature\.venv\Scripts\python.exe`, which is the one CLAUDE.md names.

## Task A — the pin

`render_turnaround --ortho --ortho-scale=<float>` skips the solve and uses the given number
verbatim for every view.

**The branch is `turnaround.projection_plan` and nothing else** — S04's doctrine applied a
second time, so "the solved path is untouched when no pin is given" is a property of one
importable object rather than of a second careful reading of the render loop. The
default-path test goes through the **real parser**, so giving `--ortho-scale` a default
cannot leave it green. The plan grew four keys: `ortho_scale_source`
(`"pinned"` / `"solved"` / `None` on perspective), `ortho_scale_pin`, `shared_across_runs`,
and `height_frac_participates`.

**Refused twice, and the second refusal is not redundant.** The parser refuses a pin without
`--ortho` and a pin that is not a finite positive span; `TurnaroundPlanRefusal` refuses the
same two inside the plan, for every caller who never reaches the parser — which is the
caller this repo keeps commissioning, since the plan is the documented branch object. A pin
silently dropped there renders a roster on per-character scales with every gate green. It is
deliberately **not** a `GateFailure`: it refuses before a camera exists, and giving it a gate
letter would put a fifth andon into the vocabulary the manifests use for measured views.

**`math.isfinite` is load-bearing, and that was checked rather than assumed.**
`framing.ortho_half_spans` guards `<= 0` downstream, but `inf > 0` is `True` and
`nan <= 0` is `False`, so both walk straight through it. A test pins that fact directly.

**The manifest defect this could have shipped with, and where it is now testable.** The
pre-S05 code keyed its solve record off `ortho_scale is None` — which a pinned run does not
satisfy. The natural non-edit therefore writes a full solve record naming a `height_frac`
the run never targeted, in exactly the shape a real fit is described in, with every gate
green. Both records now key off the **source**, and `ortho_scale_record` is split out of
`main` for the reason `_measure_alpha_plane` was: the property that matters is which block
is **absent**, and absence inside a Blender-only function is untestable. The red test
asserts the `height_frac` **value** appears nowhere in a pinned record, not merely that the
key is gone.

### One deviation from the spec's letter, disclosed

The spec asks for the two-arm sheet via `make_shotset_sheet` **compare mode**. Compare mode
hard-tags its rows `ORTHO` and `PERSP` **by position**: pointed at two ortho sets it prints
`PERSP` over a row whose own manifest says `ORTHO`, and that sheet saves, opens, rules
itself, labels itself and looks finished. So a `--mode=scale` was added instead, reading
both tags off the manifests. It refuses a non-ORTHO set, refuses across elevations, and
refuses two sets whose tags would collide — cells are written as `<tag>_<view>.png`, so a
collision overwrites them and the sheet shows **one set twice**. Row titles carry the full
`repr` rather than `.6f`, because `1.123536` is a different world span from
`1.1235359256161628` and on a pinned row that number is the recipe.

### One scope reading this seat made, surfaced rather than settled

**`--height-frac` passed together with `--ortho-scale` is accepted, not refused.** The spec's
clause 5 chose manifest disclosure over refusal and that is what was built: the manifest
records `height_frac_participates: false` and the value reaches no record. A parser refusal
of the combination would need a sentinel default on `--height-frac`, since argparse cannot
otherwise tell "not given" from "given as 0.831". Decidable without a re-run either way.

## Task B — the three arms

The GLB was **re-hashed at start**: `E:\AI\training\facet_E33\out\performer_textured.glb`,
21,588,628 bytes, sha256
`9e20ea7d800c0ffd2cff101a5e1bcc01fa13c620bbbe3ef05ae23b093547b1aa` — matching the premise
row and S04's measurement. `E:\AI\training` was opened read-only. **The texture holes on
this asset are pre-known (facet's arc) and are not S05 findings.**

Verbatim invocations, pinned:

```
blender -b -P tools\render_turnaround.py -- --glb="E:\AI\training\facet_E33\out\performer_textured.glb" --out="E:\AI\armature-S05\outputs\S05\solved" --views=8 --sweep=360 --elevation=30 --width=1024 --height=1024 --prefix=solved --ortho
```
```
blender -b -P tools\render_turnaround.py -- --glb="E:\AI\training\facet_E33\out\performer_textured.glb" --out="E:\AI\armature-S05\outputs\S05\pinned_roomy" --views=8 --sweep=360 --elevation=30 --width=1024 --height=1024 --prefix=roomy --ortho --ortho-scale=1.4044199070202035
```
```
blender -b -P tools\render_turnaround.py -- --glb="E:\AI\training\facet_E33\out\performer_textured.glb" --out="E:\AI\armature-S05\outputs\S05\pinned_tight" --views=8 --sweep=360 --elevation=30 --width=1024 --height=1024 --prefix=tight --ortho --ortho-scale=0.8988287404929303
```
```
<venv-python> tools\make_shotset_sheet.py --ortho=outputs/S05/solved --second=outputs/S05/pinned_roomy --out=outputs/S05/sheets --mode=scale
```

Both pins were computed **from arm 1's manifest float**, as the spec requires, not by hand.

### Arm SOLVED reproduces S04 at every published number

`ortho_scale` came back **`1.1235359256161628`** — the same double S04 recorded, bit for
bit. Every per-view rendered bbox, every `height_frac`, every clearance and the worst
predicted-vs-measured delta (7.93 px, view 3, `y1`) reproduce S04's table exactly. Radius
2.0507605025880484 (standoff only), Blender 5.2.0 LTS `fbe6228777e7`, numpy 2.3.4, tool
`S05.1`. Run 7.16 s wall-clock for 8 views.

**A byte-level comparison against S04's PNGs was not made** — S04's per-view digests are not
in its report, and no other worktree was opened. What is measured is that every number S04
published reproduces exactly.

### The andon that fired — arm PINNED-TIGHT, and it was Gate WHOLE

The pin was `0.8988287404929303` (0.80 × solved). The run rendered view 0, wrote its PNG,
and halted:

```
armature_core.startframe.StartFrameGate: [WHOLE] the performer's silhouette does not
clear the frame border by 2.0 px on: bottom (-20.5 px). This frame IS the conditioning
image, so a body cut by the border is a cut body for the whole generation — and every
downstream check passes on it: the file is the right size, the render is not empty, the
coverage fraction is healthy and Gate L only asks whether the frame is legal
```

Raised at `render_turnaround.py:620`, `SF.gate_whole(extent, width, height, MARGIN_PX)`.
`RENDER_TURNAROUND_OK` does not appear in the arm's stdout (captured verbatim to
`outputs/S05/pinned_tight_stdout.txt`). Partial output, listed:

| path | bytes |
|---|---|
| `outputs/S05/pinned_tight/tight_0.png` | 627,320 |

No manifest was written. **Nothing was retried and the pin was not touched.**

Measured off that one written PNG, read-only: alpha extrema **(0, 255)** — so Gate ALPHA
passed on it and the cell is a real render of a real figure, not an empty frame;
transparent fraction 0.8555; rendered bbox `[321, 7, 702, 1023]`, 1016 px tall, 381 px wide;
clearances left 321, right 321, top 7, **bottom 0**.

**Bottom clearance 0 is Gate CROP's own raising condition.** The cell *is* cropped — the
figure's feet are cut off at row 1023, confirmed by eye at full size — and both andons were
live on it. The one that reported it is the upstream one.

**Why WHOLE and not CROP, structurally.** Gate WHOLE reads the **projected decimated
cloud** and is evaluated inside the view record's dict literal; Gate CROP reads the
**rendered alpha** and is called after that record is assigned. On a *solved* run Gate WHOLE
cannot fail on the height axis — the solve fits that same projection to `height_frac ≤ 0.831`
by construction, which is S04's "Gate WHOLE passes by construction" and the argument
that made CROP the andon on the direction the solve does not bound. **A pin is fitted to
nothing, so it re-opens the direction the solve had closed.** S04's view 0 projected at
`height_frac` 0.8094; at 1.25× that is 1.0118 — taller than the frame itself, which no
placement can make clear both borders by 2 px.

The band of pins where CROP fires and WHOLE does not is the **decimation gap**: measured on
this subject at ≤ 7.93 px against per-view clearances of 62–86 px, so roughly 1–2 % of pin
wide, and subject-dependent. A 0.80× pin is 25 % in. Reported as measured; what it means for
demonstrating CROP on a real render is the advisor's.

### Arm SOLVED and arm PINNED-ROOMY, per view

`h` is Gate WHOLE's projected height fraction; `px h` / `px w` are the **rendered** alpha
bbox; `ctr` is the rendered silhouette's vertical centre row in a 1024-row frame; `clear` is
the tightest of the four per-border clearances.

| view | az | SOLVED h | px h | px w | rows | ctr | clear | ROOMY h | px h | px w | rows | ctr | clear |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 270 | 0.8094 | 829 | 305 | 108..937 | 522.5 | 86 | 0.6475 | 663 | 243 | 189..852 | 520.5 | 171 |
| 1 | 315 | 0.8310 | 855 | 230 | 106..961 | 533.5 | 62 | 0.6648 | 684 | 184 | 187..871 | 529.0 | 152 |
| 2 | 360 | 0.8274 | 849 | 149 | 108..957 | 532.5 | 66 | 0.6619 | 679 | 119 | 189..868 | 528.5 | 155 |
| 3 | 405 | 0.8058 | 834 | 248 | 111..945 | 528.0 | 78 | 0.6447 | 667 | 199 | 191..858 | 524.5 | 165 |
| 4 | 450 | 0.8072 | 829 | 305 | 112..941 | 526.5 | 82 | 0.6458 | 663 | 243 | 192..855 | 523.5 | 168 |
| 5 | 495 | 0.8192 | 841 | 230 | 112..953 | 532.5 | 70 | 0.6553 | 673 | 184 | 192..865 | 528.5 | 158 |
| 6 | 540 | 0.8247 | 849 | 149 | 109..958 | 533.5 | 65 | 0.6597 | 679 | 119 | 190..869 | 529.5 | 154 |
| 7 | 585 | 0.8125 | 841 | 248 | 106..947 | 526.5 | 76 | 0.6500 | 672 | 199 | 188..860 | 524.0 | 163 |

Gate ALPHA extrema were (0, 255) on all sixteen cells. Gate TURN passed both arms — 8
distinct digests each, and **no digest is shared between the two arms**, so the two sets are
sixteen distinct renders rather than one set counted twice.

### The pin scales the projection exactly; the rendered edge follows to within a pixel

| view | rendered `px h` ratio | projected `h` ratio |
|---|---|---|
| 0 | 0.79976 | 0.80000 |
| 1 | 0.80000 | 0.80000 |
| 2 | 0.79976 | 0.80000 |
| 3 | 0.79976 | 0.80000 |
| 4 | 0.79976 | 0.80000 |
| 5 | 0.80024 | 0.80000 |
| 6 | 0.79976 | 0.80000 |
| 7 | 0.79905 | 0.80000 |

The projected ratio is 0.80000 on all eight to the recorded precision — parallel projection
scales as `1/ortho_scale` with no residual. The rendered thresholded silhouette departs from
it by at most 0.00095 (view 7, ≈0.8 px), which is the anti-aliased edge crossing the 0.5
alpha threshold. Diagnostic; gates nothing.

### One measurement nobody asked for

**A pinned run is faster by the cost of the solve it skips**: 7.16 s (solved) against 3.78 s
(pinned), same 8 renders, same frame — a 3.38 s difference that is the bisection's
pure-Python projection cost. One run each, no repeat-variance measured.

## Predictions, scored

Registered at `75b943e` before any Blender run. Blindness disclosed in that file: not blind
to the spec, the S04 report's full per-view table, or the Task A code this seat wrote today;
blind to every S05 measurement. **Most clauses are arithmetic on S04's published numbers
rather than guesses, and the file says so per clause — the scoring below is not evidence of
foresight where it is evidence of derivation.**

| id | clause | outcome |
|---|---|---|
| P-1a | solved scale bit-identical to `1.1235359256161628` | **HIT** |
| P-1b | ALPHA 8/8, TURN distinct, WHOLE 8/8, CROP silent 8/8 | **HIT** all four |
| P-1c | manifest records `"solved"`, `pinned_as: null`, solve record at 0.831 | **HIT** all three |
| P-1d | per-view `px h` reproduces S04's eight values exactly | **HIT** 8 of 8 |
| P-1e | tightest clearance 62 px on view 1 | **HIT** |
| P-1f | 5–10 s wall-clock | **HIT** — 7.16 s |
| P-2a | roomy: ALPHA 8/8, WHOLE 8/8, CROP silent 8/8 | **HIT** |
| P-2b | largest view `px h` = 684 ± 3 | **HIT** — 684 exactly |
| P-2c | all eight `px h` within ±3 of the 0.8× values | **HIT** on the stated band; the point predictions were exact on 7 of 8, and **view 7 came in at 672 against 673 predicted** |
| P-2d | mean centre row ≈ 526 | **HIT** — 526.0 |
| P-2e | every view's minimum clearance > 140 px | **HIT** — 152 to 171 |
| P-2f | `"pinned"`, exact `given_text`, `solved_for: null`, no `height_frac` value | **HIT** all four |
| P-3a | an andon raises on view 0 and the run halts there | **HIT** |
| P-3b | the andon is **Gate WHOLE, not Gate CROP** | **HIT — and this contradicts the spec's H-S05c** |
| P-3c | on the **bottom** border | **HIT** |
| P-3d | bottom margin −15 to −26 px, top margin stays positive | **HIT** both — −20.5 px, and WHOLE named bottom only, so top cleared 2.0 px |
| P-3e | Gate ALPHA passes on that view before WHOLE raises | **HIT** — extrema (0, 255) |
| P-3f | partial output is exactly one PNG and no manifest | **HIT** |
| P-3g | no `RENDER_TURNAROUND_OK` in the arm's stdout | **HIT** |
| P-4a | sheet rows tag `SOLVED` and `PINNED` off the manifests | **HIT** |
| P-4b | same cell size, the pinned row's figure smaller in the same frame | **HIT** |

**A defect in the pre-registration, disclosed rather than repaired.** `S05-predictions.md`
writes the tight pin as `0.8988287404929302`. The pin actually typed was
`0.8988287404929303` — the machine product of arm 1's manifest float, which is what the
spec requires and what the run used. The pre-registration's value was this seat's hand
arithmetic and is one ULP low. **The file has not been edited**; S03's precedent, third
application — editing a pre-registered document after seeing results is the thing
pre-registration exists to prevent. It is the same hand-arithmetic family as S04's P-C3
miss. Nothing downstream used the wrong value.

**H-S05d gets no verdict from this seat.** The cells are on the sheet.

## For the advisor

1. **The tight arm demonstrated an andon firing on a real render — Gate WHOLE, not Gate
   CROP.** The spec wrote the arm to show CROP firing, and the structural reason it could
   not is in §"The andon that fired": a pin re-opens the height direction the solve closes
   by construction, and WHOLE sits upstream of CROP. The cell was genuinely cropped (bottom
   clearance 0 on the rendered alpha, feet amputated at row 1023), so the spec's *intent* is
   measured; the *attribution* in H-S05c is not.
2. **The band where CROP fires alone is the decimation gap** — ≤ 7.93 px against 62–86 px of
   clearance on this subject, ≈1–2 % of pin, and subject-dependent. Whether S05 owes a
   further arm inside that band, and whether Gate CROP's anti-vacuity claim needs a
   real-render demonstration at all given its red tests, is the advisor's.
3. **`--height-frac` beside `--ortho-scale` is accepted, not refused** (spec clause 5 chose
   disclosure). A refusal needs a sentinel default on `--height-frac`; decidable without a
   re-run.
4. **`make_shotset_sheet` gained a mode rather than reusing `compare`**, with its reason
   above. Compare mode itself is untouched and its S04 behaviour is unchanged.
5. **The `-O` probe was extended under a second `except` rather than a widened one.**
   Widening to `ArmatureError` would have turned every existing `WRONG_ERROR` outcome in
   that probe into a silent pass — a real weakening, avoided.
6. **The bpy-stub fixture moved to `conftest.py`** so the pin tests share S04's copy.
   `test_turnaround_ortho.py` still collects 40, unchanged.

## Suite

| tree | passed | skipped | collected |
|---|---|---|---|
| `S05-run` worktree | **1261** | **48** | **1309** |
| `S05-run` worktree, `-O` + `PYTHONOPTIMIZE=1` | **1261** | **48** | **1309** |
| `main` post-S04-merge (as recorded at `55dc0b5`) | 1242 | 13 | 1255 |

S05 adds **54** tests — 44 in `test_turnaround_pin.py`, 7 in `test_make_shotset_sheet.py`,
3 in `test_turnaround.py` — which is exactly the collected delta (1309 − 1255). The `-O`
pass is identical to the plain pass.

**The passing counts are not comparable directly and no claim is made from their
difference.** The worktree's 48 skips against main's 13 is the 35-skip grouping S04-ruling
R4 already measured and closed: the main checkout carries the historical gitignored E01–E07
artifacts and a worktree carries only its own, so tests requiring them skip precisely where
they are absent. Nothing here is asserted beyond that ruling.

## Credits and disclosure

**0 credits. 0 cloud calls.** No upload, no estimate call, no submission surface touched; no
partner API, no saved workflow, no Comfy interaction of any kind. This route is fully local:
the GLB is read from the rig, Blender renders on the rig, the sheet is composed on the rig,
and **nothing leaves it**. No new model, weight, LoRA, preprocessor or code dependency
entered the pipeline, so **no licence row is introduced**; Blender is the standing tool.

## Compensators

| act | compensator | owner |
|---|---|---|
| PNGs, manifests and captured stdout under `outputs/S05/` | delete the directory | executor session |
| inspection crops under the session scratchpad | delete the directory; nothing there is a deliverable | executor session |
| commits on `S05-run`, pushed, unmerged | `git revert`, or delete the branch | executor session |
| `E:\AI\training` | none needed — opened read-only, never written |

## Standards compliance

| standard | score | evidence |
|---|---|---|
| PIN_PER_STEP | 3 | GLB re-hashed at start and matching; both pins computed from arm 1's manifest float rather than by hand; tool + Blender + numpy versions, per-view sha256, the scale, **its source**, and the typed text all in each manifest; verbatim invocations above; the tight arm's stdout captured to a file |
| ANDON_AUTHORITY | 3 | one andon fired and the arm stopped at it — no retry, no adjusted pin, no continued sweep — and it fired on the arm the spec wrote for a raise. Two new refusals raise rather than `assert`, and joined the `-O`/`PYTHONOPTIMIZE` probe under their own catch so the existing cases were not weakened. Watchdog checked at session start and again immediately before the first render |
| NAMED_COMPENSATORS | 3 | table above; every act reversible by directory delete or `git revert`; zero credits and zero uploads by construction, so nothing irreversible was reachable |
| DECOMPOSE_BY_SECRETS | 3 | the pin lands in `projection_plan` beside S04's flag; `ortho_scale_record` splits the manifest's scale account out of the Blender-only `main` so the block that must be **absent** is testable; sheet layout stays in `sheet_compose` and only tag derivation is new |
| UNCERTAINTY_GATED_HUMANS | 3 | the compare sheet goes to the Director's eye before anything consumes the set; H-S05d is left to him explicitly; six items surfaced to the advisor contrastively rather than settled by this seat, including the one where this seat's arithmetic contradicts the spec |
| EXTERNAL_VERIFIER | 2 | the alpha arithmetic, border contact and the gate's own message are mechanical and Blender-side rather than self-reported; the projected-vs-rendered ratio table is two independent measurements of one silhouette; the advisor (a different seat) rules on this report; the standing human verifier judges the cells. Not 3: no second model family checked this seat's work |

## What is for the Director's eye

`outputs/S05/sheets/S05-solved-vs-pinned.png` — the solved row above the pinned row, same
GLB, same preset, same elevation, same 1024×1024 cell; **the scale source is the only
difference**. 8426 × 2476.

Cells are pasted 1:1 and never resampled, composited over RGB(38, 38, 42) with a 1 px border
so a figure touching its cell edge reads as touching it, and every cell carries horizontal
rules at the same two frame rows (106 and 961) as a fixed ruler. Each row title names its
scale at full precision and says where the number came from. Sheets locate; full size
decides. The texture holes are pre-known and are not findings here.

The tight arm has no sheet, per the spec — a halted run does not sheet. Its evidence is the
gate message, the partial output listing and the single-frame measurement above.
