# E12 wave 1 — report: the tooling, the baseline, and the band the plate actually gets

**Executor seat, 2026-08-12, branch `E12-run` at `E:\AI\armature-E12`, cut from `main` at
`775abe6`.** The no-spend wave. **Zero generations submitted, zero uploads, zero credits.**
The run is **HALTED at Gate PLATE**, which is where the spec puts it: no composite, no
upload, no submission until the Director's word names the plate.

**No judgement of quality is offered or implied.** Wave 1 tests no hypothesis — the
advisor's four (H-E12a…d) are about generations that do not exist yet, and nothing here has
been read against them. What follows is what was enumerated, what was re-checked, what was
measured, and the two facts the pick turns on.

**Look first:** `outputs/E12/plate/E12-plate-candidates.png` — six candidates with the crop
and the visible band drawn on each; and `outputs/E12/plate/E12-plate-band.png`, the band
alone at 2× native, which is where the whole decision lives and which the contact sheet is
too small to settle.

---

## 1. The enumeration, before anything was commissioned

The spec marked one premise ASSUMED here: *compositing over a plate image may need a small
extension*. Enumerated first, as instructed.

| module | what it turned out to be |
|---|---|
| `armature_core/startframe.py` | pure geometry and gates — no compositing at all |
| `tools/render_start_frame.py` | where the composite lives: a **second render** with `film_transparent=False` over a flat world colour |
| `tools/fit_reference.py` | a **contain/letterbox** fitter — it pads by design, which is the disease, so **not** the resource for a backdrop |
| `tools/make_crop_strip.py` | already does caller-stated native crops across frames — **used as-is**, no zoom tool commissioned |
| `tools/make_sheet.py`, `make_cast_sheet.py`, `make_startframe_sheet.py` | none is a candidate grid |

**The premise resolves ASSUMED → MEASURED: an extension was needed.** It is three pieces.

- **`startframe.cover_fit`** — scale to fill, crop the overhang, **never pad**. The sibling
  fitter pads on purpose because the Director ruled an identity reference must arrive whole;
  a padded *backdrop* is the opposite case, and this repo carries that disease on file twice
  (E08's letterbox bands; the baked grey void the alpha law ended). What the crop discards is
  reported in both source and resized pixels.
- **`tools/make_plate.py`** — does the conversion once, from either a clip frame or a file
  (the spec's two plate origins, neither a default), and writes it as an artifact with its
  own sha256 and a recorded transform.
- **`render_start_frame.py --plate`** — the authored master alpha-over the plate through
  Blender's compositor. `--composite` still names the world that **lights** the scene, the
  floor is still geometry, the camera and pose are untouched, and the flat composite is still
  rendered and kept beside the submitted one. Only what fills the void moves.

**No new model, weight, LoRA, preprocessor or code dependency enters** — `cv2`, `numpy`,
`PIL` and `bpy` were all already in the tree. **No new licence row is required by wave 1.**

### Gate BACKDROP — the andon, on the direction nothing bounded

Gate WHOLE says the body is in frame; COVERAGE says somebody is in it; ALPHA says the master
carries real transparency. **None of them looks at what fills the transparent part**, which
is this experiment's entire variable. A compositor that fails to wire still writes a
right-sized file holding the whole performer at healthy coverage, while the provenance
records a plate.

Two measured numbers, because either alone can be fooled: the void against the plate, and —
the vacuity guard — the plate against the flat fallback it replaces. When those two are the
same picture, the first number is near zero whether the compositing worked or not, so the
gate raises and says so rather than passing.

**COVERAGE keeps measuring the flat composite.** Against a scene-bearing plate, an
empty-plate difference would count the backdrop as subject and pass on a picture of an empty
bar.

### The thresholds are measured, not chosen

Blender 5.2 has deleted `Scene.node_tree` and the Composite node and renamed Alpha Over's
sockets; the remembered API raised, and the wiring was read off the running build.
`tests/blender/check_plate_composite.py` then drove the real write path:

| quantity | measured |
|---|---|
| plate → submitted composite, over the void | **0.328 / 255** |
| the same measurement on the flat render (an un-wired compositor) | **92.043 / 255** |
| plate vs the flat fallback (the separation the guard needs) | **92.043 / 255** |
| the performer's own region, plate composite vs flat | 0.881 / 255 (antialiased silhouette) |
| `PLATE_TOL_255` / `PLATE_MIN_SEPARATION_255` | 2.0 / 4.0 |

The discrimination margin is ≈280×. That falsifier ships as a test: a fixture that cannot
tell a working compositor from a broken one is not a fixture.

Every clause of ALPHA, WHOLE, BACKDROP and `cover_fit` is exercised under `-O` and
`PYTHONOPTIMIZE=1`, with the guard that the optimization actually took effect.

## 2. The w3 baseline, re-checked against its own records

Recomputed this session; every value is the record's own.

| artifact | recorded (first 16) | recomputed | |
|---|---|---|---|
| `start_frame_rgba.png` | `d7295c499f8f3e7c` | `d7295c499f8f3e7c` | match |
| `start_frame.png` | `47cf3fecd37691e0` | `47cf3fecd37691e0` | match |
| `empty_plate.png` | `935ffebded5ffe25` | `935ffebded5ffe25` | match |
| source GLB | `cd4e2f6ee85ef536` | `cd4e2f6ee85ef536` | match |
| `alpha.authored_master` | `d7295c499f8f3e7c` | `d7295c499f8f3e7c` | match |
| `gate_LEDGER_W3.start_frame.wave_3_local_sha256` | `47cf3fecd37691e0` | `47cf3fecd37691e0` | match |

Both payload hashes recompute from their graphs: w3
`165fd06537161d33ad52a371…` and w1 `5cecb774d6d2fc75fc5ea6d1…`. **No mismatch. No halt on
this clause.** Pinned from the records, never re-derived: **1024×576 · 81 @ 16 fps**, seed
`2026081233`, cfg 3.5 / euler.

> ⚠ **One number in the w3 report does not match the record it cites, noted for the advisor
> rather than acted on.** The w3 report's comparison column gives wave 1's mean luma as
> `180.8 → ~60`. Wave 1's own `measure/E11-clip.json` gives f0 = **180.76** and f64 =
> **36.20** (57.25 occurs at f32). It is a wave-1 figure quoted in a wave-3 comparison and is
> **not load-bearing for E12**, which pins w3's payload and artifact hashes — both of which
> match. Correction in place is the advisor's call.

## 3. Gate PLATE — the two facts the pick turns on

Both measured off w3's own RGBA master, not assumed.

**(a) A plate does not become the world. It becomes a band.**
The master's transparent region is **rows 0–181 of 576**. From row 182 down the frame is
`0.000` transparent — opaque studio floor. Overall transparent fraction **0.2960**, which
reproduces w3's recorded Gate ALPHA exactly. Mapped back through the cover fit, that is
**candidate rows 5.7 – 153.6 of 480**.

So the submitted start frame would be: **the picked bar across the top ~32% of the rows, and
w3's pale studio floor across the bottom ~68%**, unchanged. That follows from the spec's own
one-variable rule — the floor is geometry, and w3's provenance already recorded re-lighting
it as a second variable no wave has authorised. **Surfacing it, not proposing it.**

**(b) Inside that band, the plate is nearly all of what shows — and every candidate carries
wave 1's own mannequin.**

| | measured |
|---|---|
| the authored figure's share of the band | **0.0718** |
| therefore the plate's share of the band | **92.8 %** |
| the figure's head, at band rows 40–120 | columns **476–547** of 1024 |
| the figure's full band extent | columns 267–755, first opaque band row 29 |

The authored character occupies a narrow column near centre in that band. The wave-1
mannequin's head sits near centre too, and would **not** be covered by it. A candidate from
wave 1 therefore puts **a second figure's head in the conditioning image**. That is a fact,
not an objection — the spec's default plate source is wave 1's clips, and the spec's
alternative is a photograph the Director owns.

## 4. The candidates

From wave 1's 65 painted frames (`prompt_id ecedbe1c-8658-4119-8151-cfa693db1c50`, seed
`2026081231`, 832×480), read from that run's payload record rather than typed.

| frame | sharpness | motion | luma | framing |
|---|---|---|---|---|
| **f12** | 93 | 8.944 | 62.9 | widest; most counter and most patrons in the band |
| **f20** | 85 | **2.382** | 61.6 | lowest motion in the bright band |
| **f24** | **106** | 2.461 | 61.3 | sharpest with low motion; back-bar bottles legible |
| **f30** | **107** | 3.823 | 60.6 | sharpest of the set |
| **f38** | 98 | 6.468 | 52.4 | last frame before the clip darkens; mid push-in |
| **f57** | 65 | **1.868** | 37.4 | the pushed-in, dark end; softest back-bar |

Read at 2× native, the band holds: back-bar shelving with bottles and glassware, patrons at
screen-left, the counter edge, a yellow-green under-counter light strip running the full
width, and standing figures at screen-right. By f57 the camera has pushed in — the back-bar
is softer and the light strip dominates.

> **Sharpness is variance of a discrete Laplacian and scales with contrast**, so it ranks
> frames *within* a brightness band and never across one. This clip darkens from luma 181 to
> 36; a ranking on sharpness alone would call its dark half blurry. Luma is printed beside
> it for that reason, and a test pins the quartering so the sheet is not later "fixed" by
> sorting on it. **These are diagnostics. They locate candidates; they rank nothing.**

## 5. Gate states

| gate | state |
|---|---|
| **Gate PLATE** | **HALTED — open, the Director's** |
| the w3 baseline hash check | all 6 artifacts + 2 payload hashes match |
| Gate BACKDROP | built, calibrated against a measured round trip, `-O`-exercised — **not yet run on a plate** |
| Gates WHOLE / COVERAGE / ALPHA | unchanged, untouched by this wave |
| Gate ROUTE / PAIR / L / S, the saved round-trip, the pin check | **NOT YET RUN** — wave 2 |

## 6. The meters

| | |
|---|---|
| generations submitted | **0 of the 4-submission ceiling** |
| uploads | **none** |
| saved cloud workflows | **none** |
| credits | **0** — nothing was sent |
| suite | **910 passed, 48 skipped** (from w3's 827 / 46) |
| commits | `354996d` (the extension + its tests), `663d0cb` (the pick sheet + its tests) |

**Compensators.** Everything wave 1 wrote is local and reversible: `outputs/E12/plate/` (the
sheet, the band strip, their sidecars) and `outputs/_test_plate_composite/` (the calibration
renders). Compensator for both: delete the directory; owner: the executor session. Two
commits on a branch, revertable. **No irreversible act has been performed.**

## 7. What wave 2 needs from the Director

**The plate.** Either a frame index from the six above, or a photograph he owns. Nothing
else is blocking; the payload, frame spec, seeds and settings are all pinned from the
records.

Two things are worth his eye before he names one, both measured above and neither a
recommendation: that the plate becomes the **top ~32% of rows** rather than the world, with
w3's pale studio floor unchanged beneath it; and that a wave-1 candidate puts a **second
mannequin's head** in the band, which a photograph would not.

**This seat has not composited, uploaded or submitted anything, and will not until his word
names the plate.**
