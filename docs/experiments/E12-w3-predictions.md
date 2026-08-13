# E12 wave 3 — predictions, registered before submission

**Executor seat, 2026-08-12, branch `E12-run`. Committed BEFORE `submit_workflow` is called
on any wave-3 graph.**

**Blindness, disclosed.** Blind with respect to **every wave-3 generation** — none exists.
**Not** blind with respect to: wave 2's two clips, which this seat measured and looked at at
full size; the advisor's H-E12b, sealed in the spec (*deformation REDUCED · hands still
fail*); or the catalog's recommendation, re-read today. This is the weakest blindness of any
prediction set in this experiment, because wave 3 is a re-run of a clip I have already seen
with two fields changed — said plainly rather than implied.

**The rung.** Same A2w start frame (same server image, Gate-B-verified at wave 2), same two
seeds, same everything, with exactly two generation-reaching fields moved:

| field | wave 2 | wave 3 | source |
|---|---|---|---|
| `cfg` | 3.5 | **6.0** | the catalog's `recommended` for these exact weight files |
| `sampler_name` | `euler` | **`uni_pc`** | same read |

Steps 20, split 10, shift 8.0, scheduler `simple`, 1024×576 × 81 @ 16 fps, prompt and
negative: byte-pinned to wave 2.

## The lever under test (H-E12b, the advisor's)

| # | claim | degree |
|---|---|---|
| b1 | limb/arm deformation at f40–f80 is **visibly reduced** against wave 2, seed …233 | 55 % |
| b2 | the same on seed …241 — specifically, no arm elongated the way …241's right arm was | 50 % |
| b3 | hands still fail at f80 on both seeds | 85 % |
| b4 | seed …233's f80 head-loss does **not** recur (a face is present at f80) | 45 % |

b1/b2 sit near a coin-flip on purpose. cfg 6.0 is a *stronger* guidance term, and stronger
guidance is as capable of hardening a deformity as of removing it; `uni_pc` at 20 steps is
the catalog's pairing for that cfg, not an independent quality lever. This seat does not have
a mechanism that predicts reduction, only a catalog recommendation — and the whole point of
the rung is that a recommendation is not a measurement.

## The world (the thing wave 2 actually established)

| # | claim | degree |
|---|---|---|
| w1 | the bar still holds to f80 on both seeds | 85 % |
| w2 | the world result is **not** degraded by the settings change | 80 % |
| w3 | the crowd still churns frame-to-frame | 85 % |

Higher than wave 2's equivalents, because wave 2 measured world-holding on two seeds and this
wave changes nothing about the conditioning image.

## Mechanics

| # | claim | degree |
|---|---|---|
| q1 | `estimate_credits` 0 | 95 % |
| q2 | Gate B pixel-identical on both | 90 % |
| q3 | 81/81 distinct on both | 90 % |
| q4 | no gate fires after submission | 80 % |
| q5 | horizon detector still returns 0/81 — the instrument, not the camera | 85 % |
| q6 | frame-delta median moves by less than 1.0 against wave 2's 4.454 / 3.947 | 50 % |

## What would make this seat wrong in an interesting way

If deformation is visibly reduced on both seeds, the catalog's recommendation was worth more
than a wave of held trajectory and the arc's five-generation habit of holding wave 1's numbers
has been costing quality since E11. If it is visibly *worse*, the ASSUMED premise resolves the
other way and the held trajectory is vindicated as the better of the two — which is equally
useful and equally a full success. If nothing visibly changes, the honest report is that the
rung cost two generations to close a premise that never mattered, and that is worth knowing
before it is carried into every future shot.

**A negative result is a full success. This seat will not tune toward a number, and there are
no re-runs: a gate that fires ends the wave where it stands.**
