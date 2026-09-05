#!/usr/bin/env python
"""render_turnaround — an RGBA-true N-view turnaround of a static character GLB.

    blender -b -P tools\\render_turnaround.py -- --glb=<textured.glb> --out=<dir>

Note the `--key=value` form: argparse eats leading minus signs, and `--azimuth-start=-90`
is the shape that survives.

S03 Task A's instrument. A turnaround is the reference kit a route is *handed* when it has
to bind identity, so this tool's whole product is eight pictures of one character that a
route can actually consume — which means **authored RGBA, per the Director's ruling of
2026-08-12**, and not the thing that ruling was made against.

**What it is not.** It is not `stage_render` (control channels — depth/normal/mask/edge —
orbiting a subject, no shaded pass), and it is not `render_performer` or
`render_start_frame` (both shade and light beautifully, both stand at ONE azimuth, both
render a *performance* frame). The orbit machinery lives in `blender_scene`
(`orbit_azimuth`, `orbit_matrix`, `auto_radius`) and the alpha law lives in
`armature_core.turnaround`; this file is the place they meet. Nothing here is re-invented:
the staging — two suns, the 0.16/0.16/0.18 world, EEVEE, the Standard view transform, the
50 mm lens on a 36 mm sensor — is E09/E10's, carried through `render_start_frame` verbatim.

Prints `RENDER_TURNAROUND_OK`. A crashed `blender -b -P` exits 0, so that line is the
contract and `$LASTEXITCODE` proves nothing.

--------------------------------------------------------------------------------
The gates

* **Gate ALPHA, per view** (`turnaround.gate_view_alpha`) — the view carries transparent
  pixels AND opaque ones. The defect it exists for is the reason S03 exists: the eight
  views of `facet_E33/turn_final/` are RGBA files whose alpha extrema are (255, 255), a
  flat grey void baked into the RGB, and no check anywhere reported it.
* **Gate TURN** (`turnaround.gate_set_distinct`) — as many views as were asked for, and no
  two byte-identical. A camera that never moved writes a well-formed set of N copies of the
  front view, and every per-view gate passes on every one of them.
* **Gate WHOLE, per view** (`startframe.gate_whole`) — the silhouette is inside the frame,
  measured **unclipped**. A turnaround's widest view is not its narrowest, so a radius that
  frames the front can still amputate the arms at three-quarter; this is the check that
  binds the axis the height fit does not.

  ⚠ **This paragraph claimed a property this file did not have, and the correction is kept
  in place with the measurement that overturned it (F-553c8bc0, wave 22).** Until then
  `main` built ONE cloud — `cloud = SF.framing_cloud(verts)`, decimated to 1500 points —
  and handed it to the radius / ortho-scale solve AND to the per-view
  `SF.silhouette_extent` this gate rules on. `framing_cloud` carries only the six
  WORLD-axis extremes across its reduction, and the SCREEN-space silhouette extreme at an
  arbitrary azimuth is neither of those, so the samples the gate read were a lower bound on
  the silhouette at every view but the axis-aligned ones. MEASURED 2026-09-05 on a
  20,001-point cloud (a cylinder of radius R plus one point at (0.9R, 0.9R) — 1.27 R from
  the axis, and no world-axis extreme): the decimated cloud over-reported the clearance by
  38 px, and at two of eight azimuths `SF.gate_whole` returned a PASS over the decimated
  cloud while REFUSING the full one with clause `silhouette_does_not_clear_the_border`.
  The sibling `render_start_frame` does the opposite and says why at its own :120-122; this
  file now does the same — `framing_clouds` below returns both populations, the gate reads
  the full one, the solve reads the reduction, and the manifest's camera block records
  which was which.
* **Gate CROP, per view** (`turnaround.gate_view_crop`) — S04, and it arms on the
  `--ortho` path. Gate WHOLE reads the projected cloud, which is a projection of geometry
  rather than of pixels: anti-aliasing, the alpha threshold and the shading of a thin limb
  all live between the two. Gate CROP reads the **rendered alpha**. Border contact there is
  the failure the projection does not bound.

Gate ALPHA and Gate TURN run after the frames and **before the manifest**, because the
manifest is what makes a run look finished (`stage_render`'s doctrine, and why its G2 sits
exactly there). All of them `raise`; none is an `assert` (deleted by -O / PYTHONOPTIMIZE=1)
and none takes a skip flag.

--------------------------------------------------------------------------------
`--ortho`: the sprite shot-set (S04)

Absent the flag nothing below applies and the perspective path above is what runs. The
branch itself is `turnaround.projection_plan` and nothing else, so the untouched-when-absent
claim is a property of one testable object rather than of a careful reading of this loop.

With the flag, the camera is parallel and **one `ortho_scale` is shared by every view**,
solved from the LARGEST silhouette over the whole azimuth set. Constant scale across the
sheet is the sprite property — a per-view solve would give eight correctly-framed cells that
cannot be laid beside each other, which is the one thing a shot-set is for. Screen size
under parallel projection does not depend on distance, so the radius keeps only a
positional role and is set to a clipping-safe standoff derived from the subject's own
bounding sphere rather than from a constant in metres.

--------------------------------------------------------------------------------
`--ortho-scale`: the roster pin (S05)

Absent the pin nothing below applies and the solve above is what runs; the branch is
`turnaround.projection_plan` again, so "the solved path is untouched when no pin is given"
is a property of one testable object rather than of a second careful reading of this loop.

With the pin, **the solve does not run and the given number is used verbatim for every
view**. The solve shares one scale across the views of ONE subject; the pin shares one
scale across RUNS, which is what a cast needs and what a solve structurally cannot give:
solved per character, a nine-foot brute and a halfling are each fitted to the same frame
height and drawn the same size, every cell correctly framed and the relation between them —
the thing a roster sheet exists to show — gone with no symptom anywhere.

**`--height-frac` does not participate in a pinned run** and the manifest says so instead
of carrying the value as though it had. There is no solve for a target height to target,
and a recorded `height_frac` beside a pinned scale describes a fit that never happened.

**The pin is not fitted to its subject, and that is the point and the exposure.** Gate CROP
already stands on exactly that direction: it reads the rendered alpha, so a pin too tight
for the character in front of it raises there. Gate WHOLE is upstream of it and reads the
*projected* cloud, which the solve could never push out of frame (it fits to `height_frac`
by construction) and a pin can — so on a pinned run Gate WHOLE is live in a direction it is
not on a solved one.

--------------------------------------------------------------------------------
**`predicted_vs_measured` rides each view as a diagnostic and gates nothing.** It sets the
projector's extent against the rendered alpha's bbox — two independent measurements of one
silhouette, and the pair that exposes a wrong ortho aspect convention, which no gate here
can see. It does NOT see a flipped row order, at any aspect: the solve centres the figure,
and a centred box maps to itself under a vertical flip to within a pixel. Nothing derived
from the box can see that, so the row order is settled by the orientation calibration and
by `_measure_alpha_plane`'s own test rather than by a per-view number. No calibrated
tolerance for the delta exists on this rig, so it is reported and the Director's eye reads
it.

--------------------------------------------------------------------------------
Why the radius is solved and not typed in

`auto_radius` fits the subject's bounding SPHERE, which is rotation-invariant and correct
for a control orbit whose framing must not breathe. It is wrong for a *portrait* turnaround
frame: fitting a sphere into a 352-wide, 1024-tall frame is bounded by the narrow axis and
spends two thirds of the frame on empty air. So the radius here is solved on the subject's
own projected HEIGHT — the axis that barely moves as the camera goes round — to a target
fraction of the frame, and the width is left to vary and gated per view.

The solve runs through `framing.project`, the same projector `startframe.silhouette_extent`
and Gate WHOLE use, rather than a closed form derived here. A hand-derived formula that
disagreed with the projector by a few percent would produce a composition that passes its
own arithmetic and fails the gate, and the disagreement would be invisible.

--------------------------------------------------------------------------------
Compensator (NAMED_COMPENSATORS)

The only world-touching act is writing PNGs and a manifest under `outputs/`. Compensator:
delete the directory; owner: the executor session. Inputs are opened read-only —
`E:\\AI\\training` and `E:\\AI\\facet` are not in git, have no revert, and are never
written to.
"""

import argparse
import hashlib
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

from armature_core import blender_scene, framing, parts  # noqa: E402
from armature_core import startframe as SF  # noqa: E402
from armature_core import turnaround as TA  # noqa: E402
from armature_core.errors import ArmatureError, GateFailure  # noqa: E402
# CARRIED, not copied (F-267361f5): `render_start_frame.require_frame_size` is the sibling
# instrument's bound on `--width`/`--height`, and it is ONE implementation with two callers
# rather than a second copy here. The same idiom as `check_relift` importing
# `action_frame_range` from this module and `make_rig_sheet` importing
# `make_parts_sheet.shoot`. Stage B: it belongs in `armature_core.startframe`.
from render_start_frame import require_frame_size, require_shot_fraction  # noqa: E402

TOOL_VERSION = "S05.1"

#: The staging, inherited verbatim from E09/E10 via `render_start_frame`. Every one of
#: these is a decision and belongs in the report rather than in a reader's assumptions.
LENS_MM = 50.0
SENSOR_MM = 36.0
KEY_ENERGY, FILL_ENERGY = 3.2, 1.1
#: The world colour LIGHTS the scene; it does not appear in the picture, because
#: `film_transparent` makes the world background alpha 0. Linear RGB.
WORLD_LINEAR = (0.16, 0.16, 0.18)

#: The frame. 352x1024 is `turn_final`'s size, measured on the old set this one is rendered
#: to stand beside — matching it is what makes the Task-B comparison a comparison rather
#: than a resize.
WIDTH, HEIGHT = 352, 1024

#: Of the frame height, over the widest view. Derived from the old set by measurement
#: (`turn_final` figures span rows 86..937 of 1024 = 0.831), so the new figure is drawn at
#: the same scale as the one it is compared against.
HEIGHT_FRAC = 0.831

#: The performer faces -Y — MEASURED, not assumed: `rig_manifest_auto.json` records
#: `facing_y_sign: -1.0` from the feet-primary instrument with the head cross-check
#: agreeing. A camera at azimuth 270 therefore stands in front of him, which is view 0.
AZIMUTH_START_DEG = 270.0
SWEEP_DEG = 360.0
ELEVATION_DEG = 0.0

#: Gate WHOLE's margin. The figure must clear every border by this much.
MARGIN_PX = 2.0

#: Points handed to the framing SOLVE, and to nothing else. Carried verbatim from
#: `render_start_frame.FRAMING_CLOUD_CAP`, together with the sentence that makes it safe:
#: the solve is approximate by construction (see `startframe.framing_cloud`), Gate WHOLE
#: then runs on every vertex, so an under-report here costs margin, never correctness.
#: F-553c8bc0 is what happens when the second half of that sentence is not true.
FRAMING_CLOUD_CAP = 1500


def framing_clouds(verts, cap=FRAMING_CLOUD_CAP):
    """`(cloud, solve_cloud)` — every vertex for the GATE, a reduction for the SOLVE.

    Named rather than spelled inline (the sibling spells it inline) so the separation is a
    testable object: `tests/test_instruments_amend_w22_optics.py` asks it for both
    populations without standing up a Blender scene, and an AST census beside it asks
    `main` which of the two names each caller receives.

    Both are lists of plain float triples. `framing.project` does its own arithmetic on
    whatever it is handed, and a numpy row carried into a pure-Python bisection is a
    per-point object allocation the solve does not need.
    """
    cloud = [tuple(float(c) for c in p) for p in verts]
    return cloud, SF.framing_cloud(cloud, cap=cap)

#: ORTHO standoff, in multiples of the subject's OWN bounding-sphere radius. A global
#: constant must not govern a local feature, so this is a fraction of the structure's own
#: size rather than a distance in metres — the same subject at half the scale stands off
#: half as far, and the clearance in front of the near surface is 3 sphere-radii either way.
#: Parallel projection makes screen size independent of distance, so this number cannot
#: affect the composition; it only has to keep the whole subject in front of the lens, which
#: Gate WHOLE's `n_behind` clause is what actually enforces.
ORTHO_STANDOFF_SPHERES = 4.0


#: The engine identifiers this tool will accept, in the order it tries them.
#:
#: WAVE 14, F-0bf74152. This module pinned the single literal `'BLENDER_EEVEE'`. The
#: candidate list exists in the four SHEET tools precisely because that identifier is not
#: stable across Blender versions, and their `except TypeError: continue` is this repo's own
#: recorded evidence that an invalid enum name RAISES rather than being ignored -- so on a
#: Blender where the other spelling is the live one, the diagnostic sheets kept working and
#: the four tools whose pixels become control sequences and reference stacks died with an
#: untyped `TypeError`, recorded by the halt contract as "FAILED - an unhandled error" at
#: exit 1 naming a bpy property assignment. The order is the sheets' order, so a sheet and
#: a render made beside each other cannot be drawn by different engines.
ENGINE_CANDIDATES = ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE")


def select_engine(scene, candidates=ENGINE_CANDIDATES):
    """Set the render engine and RETURN the one actually set, else raise.

    Carried from `preview_glb.select_engine` (F-bba38f1c) rather than reinvented: the loop
    has an `else` branch, because a loop that completes without setting anything leaves the
    render on whatever the factory settings put there with no field in any record able to
    say so. `armature_core.blender_scene` is where the one implementation belongs and is
    outside this domain's globs, so the lift is FILED, not done.
    """
    for eng in candidates:
        try:
            scene.render.engine = eng
        except TypeError:
            continue
        return eng
    raise RenderTurnaroundGate(
        "none of the candidate render engines is valid on this Blender, so the render "
        "would be drawn by whatever the factory settings left in place",
        {"clause": "engine", "candidates": list(candidates),
         "blender": bpy.app.version_string})


def _render_status(result):
    """The render operator's status set as a sorted list of strings, `[]` if unreadable.

    WAVE 14, F-6a9a0f72. `bpy.ops.render.render(write_still=True)` returns an operator
    STATUS SET and can return `{'CANCELLED'}` without raising -- the premise this repo
    recorded in wave 12 and then read at none of its 14 render call sites. Every check
    those call sites have downstream (`os.path.isfile`, `getsize`, a re-read of the pixels)
    is a property a PREVIOUS run's file at the same path satisfies, so the operator's own
    verdict is the only clause that distinguishes "this call drew nothing" from "an older
    file is sitting where this call's output was supposed to land". An unreadable return is
    `[]`, which FAILS the `'FINISHED' in ...` clause rather than passing it.

    It is spelled once per tool rather than imported, because these modules share no
    parent inside `tools/` -- `armature_core` is where one implementation belongs and it is
    outside this domain's globs (FILED, see the wave-14 report). The census in
    `tests/test_instruments_amend_w14.py` asserts every copy is byte-identical, so the
    duplication cannot drift.
    """
    try:
        return sorted(str(s) for s in result)
    except TypeError:
        return []


class RenderTurnaroundGate(GateFailure):
    """The turnaround could not be composed at all.

    MEASURED 2026-09-04 (F-99b7b59a): this derived from `ArmatureError`, which carries no
    `gate` attribute and whose `__init__` takes no evidence dict. It was the only andon
    class among the 21 Blender-side tools that was not a `GateFailure` (13 of the other 14
    declare a gate id), and all five of its raise sites passed a message only — so this
    file's own handler, which prints `getattr(exc, "gate", None)` and the evidence dict,
    emitted `"gate": null, "evidence": null` for every halt it could produce. An eight-view
    turnaround halted and the log named no gate, leaving a reader to reconstruct which of
    five refusals fired from free text.

    One id rather than five: every site here is the same andon — the turnaround could not
    be composed — and the evidence dict below says WHICH clause, with its measurement.
    """

    gate = "TURNAROUND"


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--glb", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--views", type=int, default=8)
    ap.add_argument("--azimuth-start", type=float, default=AZIMUTH_START_DEG,
                    help="degrees; view 0 sits here. 270 puts the camera in front of a "
                         "performer who faces -Y")
    ap.add_argument("--sweep", type=float, default=SWEEP_DEG,
                    help="degrees of the CLOSED path; view `views` would coincide with 0")
    ap.add_argument("--elevation", type=float, default=ELEVATION_DEG)
    ap.add_argument("--width", type=int, default=WIDTH)
    ap.add_argument("--height", type=int, default=HEIGHT)
    ap.add_argument("--height-frac", type=float, default=HEIGHT_FRAC)
    ap.add_argument("--lens", type=float, default=LENS_MM)
    ap.add_argument("--sensor", type=float, default=SENSOR_MM)
    ap.add_argument("--fps", type=int, default=16,
                    help="pinned before the import because glTF key times are SECONDS; a "
                         "static subject has no action, and this keeps that true rather "
                         "than assumed")
    ap.add_argument("--prefix", default="turn")
    ap.add_argument("--ortho", action="store_true",
                    help="parallel projection with ONE ortho_scale shared by every view "
                         "— the sprite shot-set. Absent, the perspective path runs "
                         "unchanged (S04)")
    ap.add_argument("--ortho-scale", type=float, default=None,
                    help="pin the shared ortho_scale instead of solving it: one recorded "
                         "number a whole ROSTER renders on, so relative character heights "
                         "survive into the sheet. Used verbatim; --height-frac does not "
                         "participate. Requires --ortho (S05)")
    a = ap.parse_args(argv)

    # ---- F-cc1d17aa, wave 18. THE NUMBERS THAT COMPOSE THE SHOT, bounded beside the
    # `--ortho-scale` clause below because that is where this file already states the
    # predicate: a length that composes a picture is finite and strictly positive.
    #
    # `--ortho-scale` was pinned in S05 under a paragraph explaining that a non-finite span
    # "still writes a well-formed, correctly-sized RGBA PNG that no later check reports
    # on". The two flags declared on the lines above it — the ones `projection_plan`
    # describes as what "composes the shot" on the perspective path — got no clause at all,
    # and `projection_plan` passes them through as `float(lens_mm)` / `float(sensor_mm)`
    # with no check either. MEASURED 2026-09-04 on the repo venv, `solve_radius_for_height`
    # over a four-point cloud and eight azimuths:
    #
    #   --lens=nan      -> RETURNS radius=0.001, no refusal. `SF.silhouette_extent` gives
    #                      y0=nan, y1=nan; `tallest`'s `max(best, nan)` keeps `best` at
    #                      0.0, so the growth loop breaks on its first probe and the
    #                      80-step bisection converges on `lo`. The camera sits ONE
    #                      MILLIMETRE from the target for all eight views — and those eight
    #                      views are the reference stack a paid generation is conditioned
    #                      on, with nothing downstream measuring the lens.
    #   --lens=0.0      -> bare `ZeroDivisionError` out of `armature_core.framing.project`,
    #                      which the halt contract records as "FAILED - an unhandled error"
    #                      at exit 1: the exact outcome `require_frame_size` was written to
    #                      stop for `--width`/`--height` six lines up.
    #   --lens=-50.0    -> RETURNS the same radius as +50.0. A mirrored projection, silent.
    #   --sensor=nan    -> RETURNS radius=0.001.   --sensor=inf -> RETURNS radius=0.001.
    #   --sensor=-36.0  -> RETURNS the same radius as +36.0.
    #
    # A CORRECTION to the finding that routed this, kept in place rather than deleted: it
    # states that `lens=0.0`, `sensor=0.0` and `lens=inf` "each raise a bare
    # ZeroDivisionError". Only `lens=0.0` does. `sensor=0.0` and `lens=inf` reach
    # `RenderTurnaroundGate` through the growth loop's own 1.6e60 ceiling — an accident of
    # a different search, not a bound — and `sensor=inf` returns 0.001 silently, a third
    # silent case the finding did not name.
    #
    # WHY THIS RAISES THE ANDON RATHER THAN CALLING `ap.error`: `parse_args` is called from
    # inside `main`'s try, so a raised `RenderTurnaroundGate` reaches the halt contract and
    # prints RENDER_TURNAROUND_HALT with the gate id, the clause and the operand, where
    # `ap.error`'s `SystemExit(2)` is re-raised untouched by the `__main__` block and leaves
    # an argparse usage message no log reader can key on. (CORRECTED IN PLACE, wave 22,
    # F-0befca53: this paragraph used to end "`--ortho-scale`'s older clause still uses
    # `ap.error`; changing a shipped refusal is a separate decision and is not smuggled in
    # under this finding." That decision was taken and measured — both `--ortho-scale`
    # clauses below are typed raises now, and the domain holds ZERO `ap.error` call sites.)
    # ONE FINGERPRINT ACROSS THE FLAG AND THE SOLVER. The clause words below are the ones
    # `armature_core.framing.half_fovs`, its `blender_scene` byte-twin and
    # `turnaround.projection_plan`'s perspective branch use for the same two numbers, so a
    # reader grepping a halt record finds the flag refusal and the solver refusal under one
    # string. The two halves are complementary, not redundant: this one refuses before a
    # Blender scene exists, that one is inside the function performing the step.
    for _flag, _value, _clause in (("--lens", a.lens, "lens_mm_not_finite_and_positive"),
                                   ("--sensor", a.sensor,
                                    "sensor_mm_not_finite_and_positive")):
        parts.require_finite(
            _flag, _value, RenderTurnaroundGate,
            {"gate": RenderTurnaroundGate.gate, "sub_gate": "TURNAROUND_OPTICS",
             "andon": RenderTurnaroundGate.__name__,
             "who": "render_turnaround", "flag": _flag, "clause": _clause},
            positive=True)

    # THE SIBLINGS, enumerated and closed in the same wave (wave-18 rule 2). The three
    # remaining `type=float` flags on this parser are the orbit's angles, and they carry
    # the same disease one predicate weaker. MEASURED the same session:
    # `TA.orbit_azimuths(8, nan, 360)` and `(8, 270, nan)` each return EIGHT NaN azimuths
    # with no refusal; `sweep=inf` returns `[nan, inf, inf, ...]`; `elevation=nan` drives
    # `solve_radius_for_height` to the same radius=0.001 a NaN lens does, and
    # `elevation=inf` reaches a bare `ValueError` out of a projection helper. An angle may
    # legitimately be zero or negative — `--elevation=0` is this tool's own default and a
    # negative azimuth start is an ordinary way to name a direction — so the clause here is
    # FINITENESS only, and `positive=False` says so rather than a comment saying so.
    for _flag, _value in (("--elevation", a.elevation),
                          ("--azimuth-start", a.azimuth_start),
                          ("--sweep", a.sweep)):
        parts.require_finite(
            _flag, _value, RenderTurnaroundGate,
            {"gate": RenderTurnaroundGate.gate, "sub_gate": "TURNAROUND_ORBIT",
             "andon": RenderTurnaroundGate.__name__,
             "who": "render_turnaround", "flag": _flag,
             "clause": "not_a_finite_angle"},
            positive=False)

    # The two refusals, at the parser, where the mistake is still free. `projection_plan`
    # refuses the same two for callers who never reach this function, so the clause words
    # are shared and one grep finds both halves.
    #
    # F-0befca53, wave 22 — WHY THESE ARE RAISES AND NO LONGER `ap.error`. The comment six
    # lines above this block used to say "`--ortho-scale`'s older clause still uses
    # `ap.error`; changing a shipped refusal is a separate decision and is not smuggled in
    # under this finding". This IS that decision, filed and measured rather than smuggled.
    # `ap.error` raises `SystemExit(2)` from inside `parse_args`, and the `__main__` block
    # re-raises `SystemExit` untouched — so the two refusals guarding the ortho pin, the
    # number a whole ROSTER's shared frame span stands on, exited with the SAME code the
    # halt contract uses for a gate refusal while printing NO halt record at all. MEASURED
    # on `e8263a3` through `blender_stub.exit_code_of_main_block('render_turnaround.py')`:
    # a typed `RenderTurnaroundGate` gives exit 2 AND `RENDER_TURNAROUND_HALT {...
    # "gate": "TURNAROUND", "evidence": {"clause": "ortho_scale_not_finite_positive", ...}}`;
    # `ap.error`'s `SystemExit(2)` gives exit 2 and stdout EMPTY — no sentinel, no gate id,
    # no clause, no evidence. An operator keying on the halt line saw a run that refused
    # nothing; one keying on the exit code could not tell a gate refusal from an argparse
    # usage error. An AST walk over the 21 owned tools finds these two the ONLY `ap.error`
    # refusals in the domain; every other refusal was already typed.
    if a.ortho_scale is not None:
        if not a.ortho:
            raise RenderTurnaroundGate(
                "--ortho-scale pins the parallel-projection frame span, and there is no "
                "such span on the perspective path — what is shared there is the radius. "
                "Accepting it here would render a perspective turnaround that silently "
                "ignored the one number the run was pinned on. Pass --ortho, or drop the "
                "pin",
                {"gate": RenderTurnaroundGate.gate,
                 "sub_gate": "TURNAROUND_ORTHO_SCALE",
                 "andon": RenderTurnaroundGate.__name__, "who": "render_turnaround",
                 "flag": "--ortho-scale",
                 "clause": "ortho_scale_pinned_without_ortho",
                 "ortho_scale": a.ortho_scale, "ortho": bool(a.ortho)})
        if not (math.isfinite(a.ortho_scale) and a.ortho_scale > 0.0):
            raise RenderTurnaroundGate(
                f"--ortho-scale={a.ortho_scale!r} is not a finite positive world span. A "
                "non-positive span collapses every point onto the frame centre and a "
                "non-finite one sends them nowhere at all; both still write a well-formed, "
                "correctly-sized RGBA PNG that no later check reports on",
                {"gate": RenderTurnaroundGate.gate,
                 "sub_gate": "TURNAROUND_ORTHO_SCALE",
                 "andon": RenderTurnaroundGate.__name__, "who": "render_turnaround",
                 "flag": "--ortho-scale",
                 "clause": "ortho_scale_not_finite_positive",
                 "ortho_scale": a.ortho_scale, "ortho": bool(a.ortho)})

    #: What was typed, kept beside what was parsed. `float(repr(x)) == x` already makes the
    #: recorded double re-typable on its own; this is the other half of the recipe law —
    #: the roster's next character is rendered by retyping a command line, and a manifest
    #: that records only the parsed value cannot show that the two ever agreed.
    a.ortho_scale_text = _pinned_text(argv)
    return a


def _pinned_text(argv):
    """The `--ortho-scale` value exactly as it was typed, or None.

    Blender-free and separately testable, because the thing it exists to preserve is a
    string that no other measurement in this tool can reconstruct.
    """
    for i, tok in enumerate(argv):
        if tok.startswith("--ortho-scale="):
            return tok.split("=", 1)[1]
        if tok == "--ortho-scale" and i + 1 < len(argv):
            return argv[i + 1]
    return None


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _measure_alpha_plane(plane_bottom_up):
    """Extrema, transparent fraction and the subject's TOP-DOWN bbox of an alpha plane.

    Takes the plane as Blender hands it back — **row 0 at the BOTTOM of the picture** —
    and flips it, because `framing.project` returns y increasing downward and
    `startframe.mask_bbox` reads its input row-major from the top.

    Split out of `_alpha_stats` so the flip is testable without Blender, which is the only
    way it gets tested at all. It needs to be: the extrema and the transparent fraction are
    orientation-invariant and would never notice, a bbox is not, and an unflipped one makes
    Gate CROP name `top` when the figure was amputated at the `bottom` — a gate that fires
    correctly and lies about where. **Neither the predicted-vs-measured delta nor any
    crown-position probe can catch this**, and that was measured rather than assumed: the
    solve centres the figure, so at `height_frac` 0.831 in 1024 rows the flipped box
    differs from the true one by ONE pixel and every quantity derived from it agrees.

    That leaves the premise "`Image.pixels` is bottom-up" carrying the flip on its own, so
    it is measured directly by the orientation calibration rather than trusted.

    The subject mask is `alpha >= TRANSPARENT_BELOW`, the module's existing convention, so
    the bbox and the reported transparent fraction partition the same frame.
    """
    a = plane_bottom_up[::-1]
    counts = np.rint(a * 255.0).astype(np.int32)
    mask = a >= TA.TRANSPARENT_BELOW
    return {
        "alpha_min": int(counts.min()),
        "alpha_max": int(counts.max()),
        "transparent_fraction": float((a < TA.TRANSPARENT_BELOW).mean()),
        "subject_bbox": SF.mask_bbox(mask.tolist()),
        "subject_pixels": int(mask.sum()),
    }


#: What `_alpha_stats` hands back as the second element, and what Gate TURN's pixel clause
#: is therefore comparing. Recorded in the manifest so the number the gate quotes has a
#: unit and an orientation attached rather than being a bare float.
PIXEL_PLANE = {
    "dtype": "float32", "shape": "(height, width, 4)", "channels": "RGBA",
    "origin": "top-down (row 0 is the top of the image, as the PNG reads)",
    "range": "0.0-1.0, the values Blender's image buffer holds",
    "source": "the WRITTEN PNG, re-loaded — not the render buffer",
    "compare_stride": TA.PIXEL_COMPARE_STRIDE,
}


def _alpha_stats(path, width, height):
    """`(_measure_alpha_plane(alpha), the whole RGBA plane)` of the WRITTEN PNG.

    Measured off the file rather than off the render buffer. The buffer is what the
    renderer believes it produced; the file is what a route is handed, and the two differ
    exactly when the file format or the colour-mode setting drops the channel — which is
    the failure this whole tool is aimed at.

    WAVE 16, F-1e564267 — A CLAUSE WITH NO CALLER. `turnaround.gate_set_distinct` grew a
    pixel clause in wave 14 (core-solvers, F-c4cf355d) that is armed only by a caller which
    attaches `pixels` to each view record, and this file — the gate's ONLY caller —
    attached none: measured in this tree, `grep -n '"pixels"' tools/render_turnaround.py`
    returned zero hits, so the gate took its `else` branch on every run
    (`n_views_compared_in_pixels: 0`, `min_adjacent_pixel_distance: None`) and ruled on the
    bytes alone. The defect the byte clause provably cannot see is an orbit helper that
    advances by a rounding error rather than by zero — a collapsed int/float step, a
    `sweep_deg` of 1e-4 — which writes N files with N different digests over visually one
    picture, and the PINNED shot set that is the whole product ships as the front view
    eight times.

    The plane was already in hand and thrown away one line later: this function loaded the
    file into a `(height, width, 4)` buffer and kept `[..., 3]`. It now returns both. The
    RGBA half is flipped to top-down, the orientation the PNG reads in, so a plane quoted
    in a record and a plane opened in a viewer are the same picture; the alpha measurement
    is unchanged, because `_measure_alpha_plane` does its own flip.
    """
    img = bpy.data.images.load(path)
    try:
        buf = np.empty(width * height * 4, dtype=np.float32)
        img.pixels.foreach_get(buf)
        frame_bottom_up = buf.reshape(height, width, 4)
        plane = frame_bottom_up[..., 3].copy()
        rgba = frame_bottom_up[::-1].copy()
    finally:
        bpy.data.images.remove(img)
    return _measure_alpha_plane(plane), rgba


def attach_pixels(rec, plane):
    """Put the measured RGBA plane on a view record, ARMING Gate TURN's pixel clause.

    One line, and named, because the clause it arms is the whole point: a census can find
    this call, and a fixture can build the two records the gate refuses without
    re-implementing what the loop does with the plane.
    """
    rec["pixels"] = plane
    return rec


def manifest_views(views):
    """The view records as the MANIFEST carries them — every plane dropped.

    The planes are `numpy` arrays and the manifest is `json.dump`ed, so they cannot ride
    it; they are also (height x width x 4) floats per view, which is not a thing to write
    to disk beside eight PNGs that already hold it. `PIXEL_PLANE` above records what was
    compared, and Gate TURN's own evidence records how many views it reached.
    """
    return [{k: v for k, v in rec.items() if k != "pixels"} for rec in views]


def _border_contact(bbox, width, height):
    """Which frame borders the rendered subject touches. A measurement, not a verdict."""
    if bbox is None:
        return {"subject_bbox_px": None,
                "note": "no subject pixels; border contact is undefined"}
    x0, y0, x1, y1 = (int(v) for v in bbox)
    clear = {"left": x0, "right": (int(width) - 1) - x1,
             "top": y0, "bottom": (int(height) - 1) - y1}
    return {"subject_bbox_px": [x0, y0, x1, y1], "clearance_px": clear,
            "touching": sorted(s for s, c in clear.items() if c <= 0)}


def _predicted_vs_measured(extent, bbox):
    """The projector's silhouette against the rendered alpha's — DIAGNOSTIC, gates nothing.

    Two independent measurements of one silhouette: `silhouette_extent` projects the
    subject's every evaluated vertex through `framing.project`, and the bbox comes off the written
    PNG's alpha. Nothing else in this tool compares them, and a wrong ortho aspect
    convention is invisible to every gate here while showing up in this delta immediately —
    on a SQUARE frame it is invisible even here, which is what the non-square calibration
    render is for. A flipped row order is invisible to this delta too, at any aspect, and
    `_orientation_probe` is what binds it.

    No calibrated threshold for acceptable disagreement exists on this rig. Anti-aliasing
    widens the rendered edge, the 0.5 alpha threshold pulls it back, and a shaded thin limb
    can fall under it entirely — three effects of unmeasured relative size.
    So the numbers are reported and the Director's eye reads them; inventing a tolerance
    here would be a pass condition this tool could move.
    """
    if bbox is None:
        return {"measured_px": None,
                "note": "no subject pixels rendered; nothing to compare"}
    x0, y0, x1, y1 = (int(v) for v in bbox)
    pred = {k: float(extent[k]) for k in ("x0", "x1", "y0", "y1")}
    meas = {"x0": x0, "x1": x1, "y0": y0, "y1": y1}
    return {
        "predicted_px": {k: round(v, 2) for k, v in pred.items()},
        "measured_px": meas,
        "delta_px": {k: round(meas[k] - pred[k], 2) for k in pred},
        "note": ("measured minus predicted. The rendered silhouette is expected to be the "
                 "WIDER of the two (decimation under-reports, anti-aliasing over-reports), "
                 "so negative on x0/y0 and positive on x1/y1 is the ordinary sign pattern"),
    }


def ortho_scale_record(plan, ortho_scale, height_frac, given_text, sphere_radius):
    """The manifest's account of WHERE this run's shared scale came from, as the two
    mutually exclusive sub-blocks `(solved_for, pinned_as)`. At most one is not None.

    **Split out of `main` for the reason `_measure_alpha_plane` was**: the property that
    matters here is which block is *absent*, and a block that is absent inside a Blender-
    only function is a property nothing can test. The defect is one changed condition —
    the pre-S05 code keyed the solve record off `ortho_scale is None`, and a pinned run has
    a scale, so it would write a full solve record naming the `height_frac` the run never
    targeted. The manifest would then describe a fit that never happened, in the same shape
    a real fit is described in, and every gate would still be green.

    So the condition is the SOURCE, and `height_frac` reaches the pinned block only as the
    statement that it did not participate — never as a value.
    """
    if plan["ortho_scale_source"] == TA.SOLVED:
        return {
            "height_frac": float(height_frac),
            "over": "the tallest projected view of the set",
            "shared": True,
            "why": ("one scale across every cell is the sprite property; a per-view solve "
                    "frames each cell correctly and destroys the sheet, because a "
                    "genuinely narrower profile view would be enlarged to match the front "
                    "view's height"),
            "subject_sphere_radius": sphere_radius,
            "standoff_spheres": ORTHO_STANDOFF_SPHERES,
        }, None
    if plan["ortho_scale_source"] == TA.PINNED:
        return None, {
            "value": ortho_scale,
            "given_text": given_text,
            "used": "verbatim for every view; no solve ran",
            "shared": True,
            "height_frac_participates": False,
            "height_frac_role": (
                "--height-frac targets the solve, and a pinned run does not solve. Whatever "
                "was on the command line did not reach this render and its VALUE is "
                "deliberately not recorded here; recording it would describe a fit that "
                "never happened"),
            "why": ("one recorded number shared across every run of a roster is what keeps "
                    "a nine-foot brute and a halfling in relation inside the sheet. Solved "
                    "per character they would each be fitted to the same frame height and "
                    "drawn the same size — every cell correctly framed, the roster's whole "
                    "point gone"),
            "unbounded_direction": (
                "a pin is not fitted to this subject, so nothing in the solve keeps it wide "
                "enough for him; Gate CROP reads the rendered alpha and is where that "
                "direction is bound"),
            "subject_sphere_radius": sphere_radius,
            "standoff_spheres": ORTHO_STANDOFF_SPHERES,
        }
    return None, None


def solve_radius_for_height(cloud, target, azimuths, elevation_deg, lens_mm, sensor_mm,
                            width, height, height_frac):
    """Orbit radius whose WIDEST-view projected height is `height_frac` of the frame.

    Bisected through `framing.project` — the projector Gate WHOLE also uses — so the
    composition this returns and the composition the gate measures cannot disagree. The
    maximum is taken over every azimuth the run will actually render, so a view that
    happens to project taller than view 0 (perspective: the near shoulder at three-quarter
    sits closer to the lens than the front shoulder does) still fits.
    """
    def tallest(radius):
        best = 0.0
        for az in azimuths:
            ext = SF.silhouette_extent(cloud, target, radius, az, elevation_deg,
                                       lens_mm, sensor_mm, width, height)
            best = max(best, (ext["y1"] - ext["y0"]) / float(height))
        return best

    lo, hi = 1e-3, 1.0
    for _ in range(200):                      # grow until the figure is small enough
        if tallest(hi) <= height_frac:
            break
        hi *= 2.0
    else:                                     # pragma: no cover - unreachable in practice
        raise RenderTurnaroundGate(
            f"no orbit radius up to {hi:g} draws the subject at or below "
            f"{height_frac:g} of the frame height",
            {"clause": "orbit radius", "grew_to": float(hi),
             "height_frac": float(height_frac), "tallest_at_hi": float(tallest(hi)),
             "azimuths": list(azimuths)})
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if tallest(mid) > height_frac:
            lo = mid
        else:
            hi = mid
    return hi


def solve_ortho_scale_for_height(cloud, target, radius, azimuths, elevation_deg,
                                 width, height, height_frac):
    """The ONE ortho_scale whose TALLEST view is `height_frac` of the frame.

    The sprite property is that this number is shared. A per-view solve would frame each
    cell beautifully and destroy the sheet: the figure would be the same height in all
    eight, so a character who is genuinely narrower from the side would be silently
    enlarged until he matched his own front view. Solving once over the maximum makes the
    largest view the one that fits and lets every other cell be honestly smaller.

    Bisected through `framing.project` for the same reason the radius solve is — a closed
    form derived here would be a second implementation of Blender's AUTO ortho fit, and a
    few percent of disagreement produces a composition that passes its own arithmetic and
    fails the gate with nothing pointing at why. Monotone for the same reason too: a larger
    span draws the subject smaller.

    `radius` is passed through only because the projector needs a camera position; under
    parallel projection it cannot move the result, and the run's own manifest records the
    invariance rather than asserting it.
    """
    def tallest(scale):
        best = 0.0
        for az in azimuths:
            ext = SF.silhouette_extent(cloud, target, radius, az, elevation_deg,
                                       None, None, width, height, ortho_scale=scale)
            best = max(best, (ext["y1"] - ext["y0"]) / float(height))
        return best

    lo, hi = 1e-6, 1.0
    for _ in range(200):                      # grow the span until the figure is small
        if tallest(hi) <= height_frac:
            break
        hi *= 2.0
    else:                                     # pragma: no cover - unreachable in practice
        raise RenderTurnaroundGate(
            f"no ortho_scale up to {hi:g} draws the subject at or below {height_frac:g} "
            f"of the frame height",
            {"clause": "ortho_scale", "grew_to": float(hi),
             "height_frac": float(height_frac), "tallest_at_hi": float(tallest(hi)),
             "azimuths": list(azimuths)})
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if tallest(mid) > height_frac:
            lo = mid
        else:
            hi = mid
    return hi


def main():
    started = time.time()
    a = parse_args()
    out = os.path.abspath(a.out)
    # ABOVE the `scene.render.resolution_x` assignment, never below it — the ordering
    # clause F-34a858f5 earned, and the reason it matters here is that the zero case used
    # to reach `silhouette_extent` as a bare `ZeroDivisionError` AFTER the scene resolution
    # had already been set to zero. The 16-divisibility clause DOES apply to this tool: its
    # eight views are the reference stack a paid generation is conditioned on, and its own
    # default frame (352x1024) is a multiple of 16 on both axes.
    width, height = require_frame_size(
        int(a.width), int(a.height), who="render_turnaround",
        module_frame=(WIDTH, HEIGHT), gate=RenderTurnaroundGate, gate_id="TURNAROUND_FRAME")
    # F-f0c261c1's sibling half, carried here rather than copied. Bounded ON BOTH PATHS,
    # including the PINNED ortho run where `projection_plan` says the fraction does not
    # participate: `ortho_scale_record` still writes `float(height_frac)` into the manifest
    # there, and a NaN in a recipe is a recipe that does not reproduce its output. Read
    # ONCE, here; every use below is of this value.
    #
    # This tool's own solve happens to refuse a NaN by growing to 1.6e60 and raising
    # `RenderTurnaroundGate` — an accident of a different search, not a bound. MEASURED
    # 2026-09-04 on the same solver: `height_frac=0.0` RETURNS 4.25e16, `1.5` RETURNS 1.68
    # and `inf` RETURNS 0.001, all three without a word.
    height_frac = require_shot_fraction(
        "--height-frac", a.height_frac, who="render_turnaround",
        gate=RenderTurnaroundGate, gate_id="TURNAROUND_FRACTION")

    azimuths = TA.orbit_azimuths(a.views, a.azimuth_start, a.sweep)

    # ---- fps FIRST, on an empty scene, before the import. glTF key times are seconds.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    blender_scene.set_frame_rate(scene, a.fps)
    meshes, arms, info = blender_scene.import_glb(a.glb, expected_fps=a.fps)
    if not meshes:
        raise RenderTurnaroundGate(
            f"{a.glb} imported no mesh objects; nothing to render",
            {"clause": "import", "glb": a.glb, "mesh_objects": [],
             "armatures": [o.name for o in arms]})

    engine = select_engine(scene)
    scene.render.resolution_x, scene.render.resolution_y = width, height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "Standard"

    # The subject is STATIC: the scene frame is pinned so anything the asset carries cannot
    # move it while the camera does. A turnaround of a walking figure is eight views of
    # eight different poses, and nothing downstream could tell that from a bad mesh.
    scene.frame_start = scene.frame_end = 1
    scene.frame_set(1)

    world = bpy.data.worlds.new("turnaround")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (*WORLD_LINEAR, 1.0)

    key = bpy.data.lights.new("key", type="SUN")
    key.energy = KEY_ENERGY
    ko = bpy.data.objects.new("key", key)
    scene.collection.objects.link(ko)
    ko.rotation_euler = (math.radians(58), 0.0, math.radians(-25))
    fill = bpy.data.lights.new("fill", type="SUN")
    fill.energy = FILL_ENERGY
    fo = bpy.data.objects.new("fill", fill)
    scene.collection.objects.link(fo)
    fo.rotation_euler = (math.radians(65), 0.0, math.radians(150))

    # NO floor. A ground plane is real geometry and renders opaque, so it would fill the
    # lower frame with exactly the kind of baked, non-transparent backdrop this tool exists
    # to stop shipping — and `turn_final`, the set this stands beside, has none either.

    # `render_visible_meshes` and not `type == "MESH"` — CARRIED from
    # `render_start_frame.py:435`, the sibling this file already inherits its staging
    # from. Blender's glTF importer drops a 42-vertex Icosphere of world radius 1.0 into
    # a hidden `glTF_not_exported` collection; measuring it inflates the bbox, the orbit
    # target, the framing cloud and therefore the solved radius / shared `ortho_scale`.
    # NO gate below can see that: Gate WHOLE reads the same inflated cloud, and Gate CROP
    # reads the rendered alpha, which a hide_render decoy never reaches — a figure drawn
    # too SMALL moves away from every border, so CROP passes more easily, not less.
    # E02-report.md:34 measured the decoy turning a 3.23:1 figure into a 1.05:1 near-cube.
    subject = blender_scene.render_visible_meshes(scene, meshes)
    excluded = [o.name for o in meshes if o not in subject]
    if not subject:
        raise RenderTurnaroundGate(
            f"{a.glb} imported {len(meshes)} mesh object(s) and none of them is "
            f"render-visible ({[o.name for o in meshes]}); there is nothing to turn "
            f"around, and framing against hidden geometry would compose a shot of an "
            f"object the renderer will not draw",
            {"clause": "render visibility", "glb": a.glb,
             "mesh_objects_all": [o.name for o in meshes],
             "mesh_objects_render_visible": []})

    verts = blender_scene.evaluated_world_vertices(scene, subject)
    lo = verts.min(axis=0)
    hi = verts.max(axis=0)
    target = ((lo[0] + hi[0]) * 0.5, (lo[1] + hi[1]) * 0.5, (lo[2] + hi[2]) * 0.5)
    # TWO populations, F-553c8bc0. `cloud` is every evaluated vertex and is what Gate WHOLE
    # rules on; `solve_cloud` is the reduction and reaches the solvers and nothing else. One
    # name for both is the defect: `framing_cloud` carries the six WORLD-axis extremes over
    # its reduction and a SCREEN-space silhouette extreme at an arbitrary azimuth is not one
    # of those, so the gate was measuring a lower bound on the thing it exists to bound.
    cloud, solve_cloud = framing_clouds(verts)

    # ---- THE BRANCH, and the only one. Everything that differs between a perspective
    # turnaround and an ortho shot-set is decided by `projection_plan` and read out below.
    plan = TA.projection_plan(a.ortho, a.lens, a.sensor, ortho_scale_pin=a.ortho_scale)

    if plan["projection"] == TA.ORTHOGRAPHIC:
        # Standoff from the subject's OWN bounding sphere: parallel projection cannot let
        # this number reach the composition, so its only job is keeping the whole figure in
        # front of the lens — which Gate WHOLE's `n_behind` clause is what enforces.
        sphere_radius = float(
            np.linalg.norm(verts - np.asarray(target, dtype=verts.dtype), axis=1).max())
        radius = sphere_radius * ORTHO_STANDOFF_SPHERES
        if plan["ortho_scale_source"] == TA.PINNED:
            # VERBATIM. Not a starting point, not a hint to a solve, not clamped to
            # anything: the pin's whole value is that the same number governs every run of
            # a roster, and a tool that adjusted it "a little" for one subject would put
            # that character back on his own private scale with nothing reporting it.
            ortho_scale = plan["ortho_scale_pin"]
        else:
            ortho_scale = solve_ortho_scale_for_height(
                solve_cloud, target, radius, azimuths, a.elevation, width, height,
                height_frac)
    else:
        sphere_radius, ortho_scale = None, None
        radius = solve_radius_for_height(solve_cloud, target, azimuths, a.elevation,
                                         a.lens, a.sensor, width, height, height_frac)

    # Every refusal above this line can fire before a single pixel exists; the output
    # directory is created HERE so a halt does not leave an empty one behind for a
    # later run to read as a used one (F-8d2b9d7d). Nothing between the old site and
    # this one writes.
    #
    # WAVE 12, F-244b2ad5: the line was ABOVE the projection branch, and BOTH solvers in
    # it raise — `solve_ortho_scale_for_height` and `solve_radius_for_height` refuse a
    # subject they cannot frame. Neither needs a directory. The wave-10 census reported
    # this file clean because it recognised a refusal by the callee's NAME, and neither
    # solver is called `gate_*`.
    os.makedirs(out, exist_ok=True)          # scripts create their own output directories

    cam_data = bpy.data.cameras.new("turn_cam")
    cam_data.type = plan["blender_camera_type"]
    cam_data.lens, cam_data.sensor_fit, cam_data.sensor_width = a.lens, "AUTO", a.sensor
    if ortho_scale is not None:
        cam_data.ortho_scale = ortho_scale
    cam_data.clip_start, cam_data.clip_end = 0.01, 1000.0
    cam = bpy.data.objects.new("turn_cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    # THE ALPHA LAW (CLAUDE.md, the Director's ruling 2026-08-12). `film_transparent`
    # makes the WORLD background alpha 0 while the subject's own geometry stays opaque,
    # so what becomes transparent is exactly the void the law is about and nothing else.
    # There is no composite here on purpose: this tool's deliverable IS the RGBA master,
    # and the RGB each consuming route submits is that route's own recorded choice.
    scene.render.film_transparent = True
    scene.render.image_settings.color_mode = "RGBA"

    views = []
    for i, az in enumerate(azimuths):
        cam.matrix_world = blender_scene.orbit_matrix(Vector(target), radius,
                                                      a.elevation, az)
        path = os.path.join(out, f"{a.prefix}_{i}.png")
        scene.render.filepath = path
        render_result = bpy.ops.render.render(write_still=True)
        # WAVE 14, F-6a9a0f72: the render operator's STATUS SET, read. The existence and
        # size checks below are properties a PREVIOUS run's file at the same path satisfies;
        # only the operator's own verdict says whether THIS call drew anything. Shape carried
        # from `rig_bake.py`'s `if 'FINISHED' not in result`.
        _status = _render_status(render_result)
        if "FINISHED" not in _status:
            raise RenderTurnaroundGate(
                f"the render operator did not report FINISHED for "
                f"{os.path.basename(path)}; it returned {_status!r}, and any file at "
                f"that path is then the previous run's",
                {"clause": "operator_status", "status": _status,
                 "path": os.path.abspath(path)})
        if not os.path.isfile(path):          # pragma: no cover - Blender-side failure
            raise RenderTurnaroundGate(
                f"view {i} rendered no file at {path}",
                {"clause": "write", "view": i, "azimuth_deg": az, "path": path,
                 "views_written": [v["path"] for v in views]})

        m, plane = _alpha_stats(path, width, height)
        extent = SF.silhouette_extent(cloud, target, radius, az, a.elevation, a.lens,
                                      a.sensor, width, height, ortho_scale=ortho_scale)
        rec = {
            "view": i, "azimuth_deg": az, "path": path,
            "bytes": os.path.getsize(path), "sha256": _sha256(path),
            "gate_ALPHA": TA.gate_view_alpha(i, m["alpha_min"], m["alpha_max"],
                                             m["transparent_fraction"], path),
            "gate_WHOLE": SF.gate_whole(extent, width, height, MARGIN_PX),
            "subject_bbox_px": (list(m["subject_bbox"])
                                if m["subject_bbox"] is not None else None),
            "subject_pixels": m["subject_pixels"],
            "predicted_vs_measured": _predicted_vs_measured(extent, m["subject_bbox"]),
        }
        # Gate CROP arms on the ORTHO path. It is the shared-scale solve's andon, and
        # Task A's structural invariant is that the perspective path is untouched when the
        # flag is absent — a new raising gate there would be a behaviour change to it. The
        # same measurement is taken on both paths either way and rides the manifest, so
        # ruling that CROP should arm on perspective too needs no re-run to decide.
        if plan["projection"] == TA.ORTHOGRAPHIC:
            rec["gate_CROP"] = TA.gate_view_crop(
                i, m["subject_bbox"], width, height, path,
                alpha_threshold=TA.TRANSPARENT_BELOW)
        else:
            rec["gate_CROP"] = {
                "gate": "CROP", "view": i, "armed": False,
                "why_not_armed": ("the shared-scale solve this andon bounds does not run "
                                  "on the perspective path; the measurement is reported"),
                "border_contact": _border_contact(m["subject_bbox"], width, height),
            }
        # WAVE 16, F-1e564267: the plane rides the record, so Gate TURN's pixel clause is
        # ARMED rather than "armed only when". It is dropped again by `manifest_views`
        # below, after the gate and before the manifest is written.
        views.append(attach_pixels(rec, plane))

    # ---- the set-level andon, after the frames and BEFORE the manifest.
    gate_turn = TA.gate_set_distinct(views, a.views)

    solved_for, pinned_as = ortho_scale_record(
        plan, ortho_scale, height_frac, a.ortho_scale_text, sphere_radius)

    manifest = {
        "tool": "render_turnaround", "tool_version": TOOL_VERSION,
        "blender": blender_scene.blender_provenance(),
        "numpy": np.__version__,
        "source": {"glb": os.path.abspath(a.glb), "sha256": _sha256(a.glb),
                   "bytes": os.path.getsize(a.glb)},
        "import_info": dict(info, subject_render_visible=[o.name for o in subject],
                            subject_excluded_not_render_visible=excluded),
        "resolution": [width, height],
        "camera": {
            "type": "orbit", "n_views": int(a.views),
            "projection": plan["projection"],
            "blender_camera_type": plan["blender_camera_type"],
            "shared_across_views": plan["shared_across_views"],
            "radius_role": plan["radius_role"],
            "azimuth_start_deg": float(a.azimuth_start), "sweep_deg": float(a.sweep),
            "azimuths_deg": azimuths, "elevation_deg": float(a.elevation),
            "lens_mm": plan["lens_mm"], "sensor_mm": plan["sensor_mm"],
            "sensor_fit": "AUTO",
            "ortho_scale": ortho_scale,
            "ortho_scale_source": plan["ortho_scale_source"],
            "shared_across_runs": plan["shared_across_runs"],
            "height_frac_participates": plan["height_frac_participates"],
            # Both keyed off the SOURCE — never off `ortho_scale is None`, which a pinned
            # run satisfies too. See `ortho_scale_record`, where the absence is testable.
            "ortho_scale_solved_for": solved_for,
            "ortho_scale_pinned_as": pinned_as,
            "radius": radius, "radius_solved_for": (None if ortho_scale is not None else {
                "height_frac": height_frac,
                "over": "the tallest projected view of the set",
                "why": ("a bounding-sphere fit is bounded by the narrow axis of a "
                        "352x1024 frame and would spend most of it on empty air; the "
                        "height is the axis that barely moves as the camera goes round"),
            }),
            "target": list(target),
            # F-553c8bc0, the shape `render_start_frame.py:1012` already records. Without
            # it `subject.n_vertices` said 20,000 while the gate had measured 1500 and no
            # field in the record could say so.
            "framing_cloud": {"n_vertices": len(cloud),
                              "n_solved_against": len(solve_cloud),
                              "cap": FRAMING_CLOUD_CAP,
                              "gate_WHOLE_measured": "n_vertices"},
        },
        "subject": {
            "animation": "static",
            "bbox_lo": [float(v) for v in lo], "bbox_hi": [float(v) for v in hi],
            "n_vertices": int(verts.shape[0]),
            "facing": ("-Y, MEASURED in rig_manifest_auto.json (facing_y_sign -1.0, feet "
                       "primary, head cross-check agrees) on this GLB's rigged descendant"),
        },
        "staging": {
            "inherited_from": ("E09/E10 via render_start_frame — the same two suns, the "
                               "same world, EEVEE, Standard view transform"),
            "world_linear_rgb": list(WORLD_LINEAR),
            "key_sun_energy": KEY_ENERGY, "fill_sun_energy": FILL_ENERGY,
            # the engine ACTUALLY set (F-0bf74152), never the literal.
            "engine": engine, "view_transform": "Standard",
            "floor_drawn": False,
            "floor_why": ("a ground plane is opaque geometry and would bake a non-"
                          "transparent backdrop into the lower frame, which is the defect "
                          "this tool exists to stop shipping"),
        },
        "alpha": {
            "law": "authored image inputs carry alpha, never a baked void",
            "master": {"color_mode": "RGBA", "film_transparent": True},
            "composite": ("NONE submitted by this tool. The deliverable is the RGBA "
                          "master; the RGB composite is the consuming route's own "
                          "recorded choice, per the law"),
        },
        "views": manifest_views(views),
        "pixel_plane": PIXEL_PLANE,
        "gates": {"TURN": gate_turn,
                  "ALPHA": [v["gate_ALPHA"]["verdict"] for v in views],
                  "WHOLE": [v["gate_WHOLE"]["verdict"] for v in views],
                  "CROP": [v["gate_CROP"].get("verdict", "NOT ARMED (perspective path)")
                           for v in views]},
        "elapsed_s": round(time.time() - started, 2),
    }
    with open(os.path.join(out, "turnaround_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)

    for v in views:
        pvm = v["predicted_vs_measured"].get("delta_px")
        print(f"view {v['view']} az={v['azimuth_deg']:7.2f}  "
              f"alpha={tuple(v['gate_ALPHA']['alpha_extrema'])}  "
              f"transparent={v['gate_ALPHA']['transparent_fraction']:.4f}  "
              f"h={v['gate_WHOLE']['height_frac']:.4f} w={v['gate_WHOLE']['width_frac']:.4f}"
              + (f"  bbox={v['subject_bbox_px']}" if v["subject_bbox_px"] else "")
              + (f"  d(meas-pred)={pvm}" if pvm else ""))
    print(f"projection {plan['projection']}   radius {radius:.6f}"
          + ("" if ortho_scale is None else
             f"   ortho_scale {ortho_scale!r} ({plan['ortho_scale_source']}, shared)")
          + f"   {gate_turn['verdict']}")
    # The success sentinel carries a payload like its twenty siblings: the rule every
    # Blender invocation is bound to is "verify a success sentinel in the output, never
    # the exit code alone", and a bare token tells the caller nothing about what it
    # succeeded at (F-161b09fc).
    print("RENDER_TURNAROUND_OK " + json.dumps({
        "out": os.path.abspath(out), "views": [v["view"] for v in views],
        "projection": plan["projection"], "radius": round(radius, 6)}))


def _halt_keysafe(value, _seen=None):
    """`value` with every mapping key stringified, at every depth.

    `json.dumps(..., default=str)` applies `default` to VALUES ONLY: a tuple key or a
    `numpy.int64` key raises `TypeError` from inside the halt handler below, the new
    exception leaves the whole `try` statement, `sys.exit` never runs -- and `blender -b -P`
    then exits **0** on a fired andon, with no sentinel line at all. MEASURED 2026-09-04
    against all 21 handlers: 21 of 21 escaped that way. Pinned by
    `tests/test_instruments_amend_w10.py`.

    STAGE B: this belongs in `armature_core.errors` beside the halt vocabulary, as one
    implementation with 21 call sites (together with `halt_outcome`, which lives in
    `rig_character.py` today and is inlined as a ternary in the other twenty).
    `armature_core` is outside the instruments domain's globs, so the lift is FILED, not
    done -- see the wave-10 `skipped[]` entry for F-ce3a471d.
    """
    # WAVE-10 MERGE (coordinator, 2026-09-04): a SELF-REFERENCING evidence dict recursed here until
    # `RecursionError` escaped the handler — measured on the merged tree by
    # `tests/test_instrument_exits.py` (the "circular" direction), 21 of 21. Containers already
    # on the path are written as the literal "<circular>" instead of re-entered.
    if _seen is None:
        _seen = set()
    if isinstance(value, (dict, list, tuple)):
        if id(value) in _seen:
            return "<circular>"
        _seen = _seen | {id(value)}
    if isinstance(value, dict):
        return {str(k): _halt_keysafe(v, _seen) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_halt_keysafe(v, _seen) for v in value]
    return value


if __name__ == "__main__":
    # THE HALT CONTRACT — one shape across all 21 Blender-side tools (wave 8; pinned by
    # `tests/test_instruments_amend_w8.py`). `blender -b -P` exits **0** when the script's
    # exception propagates (E07, measured three times: rig_character.py, rig_parts.py,
    # author_walk.py), so a halt that does not exit deliberately is reported as a success.
    #
    # THREE outcomes, not two. A typed `GateFailure` is an andon that fired and names
    # itself; a bare `ArmatureError` is a deliberate refusal with no gate behind it (an
    # unknown flag, an unknown `--mode=`); anything else is a crash. Recording a crash as
    # "a gate fired" is a false record — F-c3f86abc measured `rig_character` writing one.
    # A deliberate refusal exits 2; a crash exits 1.
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 - the halt must be legible and loud
        import traceback
        # THE HALT CONTRACT'S OWN GUARD (F-586822bf, wave 12). Wave 10 moved `json.dumps`
        # inside a try/except/finally so a sentinel that cannot serialise could no longer
        # delete `sys.exit` — but the sentinel's CONSTRUCTION stayed ABOVE that guard, and
        # so did `traceback.print_exc()`. MEASURED 2026-09-04 by driving
        # `blender_stub.exit_code_of_main_block` over all 21 WITH_MAIN tools with a
        # `GateFailure` whose evidence carried (a) a key whose `__str__` raises and (b) 6000
        # levels of non-cyclic nesting: 21 of 21 returned code None, with `RuntimeError` /
        # `RecursionError` escaping the handler and ZERO sentinel lines printed — which is
        # `blender -b -P` reporting exit 0 on a fired andon, the E07 failure this contract
        # exists to end.
        #
        # Stated plainly: neither trigger is reachable from today's raise sites (an AST scan
        # of all 21 finds no non-string-literal evidence key, and every `raise` passes an
        # already-materialised f-string, so `str(exc)` cannot fail). The measured defect was
        # in the CLAIM `tests/test_instrument_exits.py` makes about this block — that any
        # secondary failure in a handler still yields a sentinel and an exit code — and the
        # claim is made TRUE here rather than weakened there.
        #
        # Everything below that can fail is inside the guard. What is above it cannot:
        # `isinstance` on an exception, `type(exc).__name__`, and a `json.dumps` of six
        # values that are already strings or None.
        _code = 2 if isinstance(exc, (GateFailure, ArmatureError)) else 1
        _outcome = ("HALTED — a gate fired" if isinstance(exc, GateFailure)
                    else "REFUSED — the tool declined to proceed"
                    if isinstance(exc, ArmatureError)
                    else "FAILED — an unhandled error")
        _sentinel = {
            "tool": "render_turnaround", "outcome": _outcome, "gate": None,
            "error": type(exc).__name__,
            "message": "the halt line could not be built", "evidence": None}
        _line = json.dumps(_sentinel)
        try:
            traceback.print_exc()
            _detail = getattr(exc, "evidence", None)
            _sentinel = {
                "tool": "render_turnaround", "outcome": _outcome,
                "gate": getattr(exc, "gate", None),
                "error": type(exc).__name__, "message": str(exc),
                "evidence": (_halt_keysafe(_detail)
                             if isinstance(_detail, dict) else None)}
            _line = json.dumps(_sentinel, default=str)
        except BaseException:                                         # noqa: BLE001
            pass
        finally:
            print("RENDER_TURNAROUND_HALT " + _line)
            sys.exit(_code)
