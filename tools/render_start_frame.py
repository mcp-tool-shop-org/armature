#!/usr/bin/env python
r"""render_start_frame — the one frame E11 hands an image-to-video model.

    blender -b -P tools\render_start_frame.py -- --glb=<performer.glb>
            --out=<dir> [--frame=0] [--width=832] [--height=480] [--height-frac=0.90]
            --composite=r,g,b --composite-why="..." [--plate=<plate.png> --plate-why="..."]
            [--set=<set.glb> ...] [--frames=i,j]

E11's commission. armature is image-to-video with a GLB instead of an image; this tool is
where the GLB becomes the image. It stages one frame of a performance, lights it, and
writes it at the **generation's own resolution**, so nothing scales, letterboxes or
centre-crops it on the way to the model.

Wave 34: `--set` (appendable) imports owned 3D scenery excluded from the subject framing
solve but included in the render (F-91411b51). `--frames=i,j` (or `--end-frame`) stages a
matched FLF2V first/last pair under one lighting, framing, composite and provenance lock
(F-d7f9fed5).

**Why native size, stated as a decision.** E08 handed `WanAnimateToVideo` a 352x1024
portrait reference and measured what the node did to it: `common_upscale(..., "area",
"center")` kept 204 of its 1024 rows — hips and thighs, no head. The Director ruled
letterbox, and E08's own report named the fix this tool implements: a native 832x480 frame
with the figure filling it. Authoring the frame at the model's size removes the whole class
of failure rather than compensating for it.

**The staging is E09/E10's, reused verbatim rather than re-invented** — the same two suns,
the same 0.16/0.16/0.18 world, the same EEVEE + Standard view transform, the same ground
plane, the same 225 deg / 6 deg / 50 mm / 36 mm camera convention. One consequence is worth
naming before anybody reads a result off it: this staging is a grey studio, not a bar. On
the no-control route the start frame is the model's only picture of the world, so a scene
prompt is asking it to *replace* what the image shows rather than to fill a silence. That
is a property of the experiment, recorded here so the report does not have to discover it.

--------------------------------------------------------------------------------
The gates

* **the fps andon** — the scene rate is pinned on an empty scene before the import, or
  `blender_scene.import_glb` raises. glTF key times are SECONDS.
* **Gate WHOLE** (`armature_core.startframe`) — the entire silhouette is inside the frame
  with margin, measured UNCLIPPED on every evaluated vertex. This is the gate the tool
  exists for; the module docstring carries why `solve_camera`'s own `in_frame` cannot do
  it (it is solved over landmarks, which under-report the silhouette).
* **the coverage andon** — the rendered frame differs from an empty plate of the same
  camera, lights and floor with the character hidden. Bounds the other direction: WHOLE
  says nothing left the frame, COVERAGE says somebody is in it. A render of a floor passes
  every count-, size- and legality-based check ever written.
* **the pose andon** — the requested frame index exists inside the action's own range. A
  frame past the end holds the last pose and looks like a perfectly good render.
* **Gate BACKDROP** (`armature_core.startframe`, only when `--plate` is given) — the plate
  really is what stands behind the performer in the submitted file. Nothing else looks
  there: a compositor that failed to wire still writes a right-sized file containing the
  whole performer at healthy coverage, and the provenance still records a plate.

**The plate route, added by E12.** `--plate` replaces the flat void with a picture of a
world, and only that: `--composite` still names the world colour that LIGHTS the scene, the
floor is still geometry, the camera and pose are untouched, and the flat composite is still
rendered and kept beside the submitted one as the counterfactual. The plate must already be
at the frame's exact size — `make_plate.py` does the fit, so the fit is an artifact with a
hash and a recorded transform instead of a resize hidden inside a render.

Prints `RENDER_START_FRAME_OK`. A crashed `blender -b -P` exits 0, so that line is the
contract and `$LASTEXITCODE` proves nothing.

Compensator (NAMED_COMPENSATORS): the only world-touching act is writing PNGs and a
sidecar under `outputs/`. Compensator: delete the directory; owner: the executor session.
Inputs are opened read-only.
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

from armature_core import blender_scene, framing, parts, pngio, startframe as SF  # noqa: E402
# F-a2630f86: `render_target_snapshot` / `require_render_target_moved` are
# `export_target_snapshot`'s twins and live beside it. The idiom is
# `rig_bake`'s and `make_parts_sheet`'s -- one implementation, imported.
import rig_character as rc  # noqa: E402
from armature_core.errors import ArmatureError, GateFailure  # noqa: E402
# Helpers live in render_performer; import LAZILY inside main to avoid the
# render_performer -> render_turnaround -> render_start_frame cycle (F-5b7048d5).

TOOL_VERSION = "E11.2"

#: The camera convention, carried verbatim from `render_performer` (E09/E10) so this frame
#: shows the performer from the angle the rest of the arc has been looking at him from.
#: 225 deg is a true three-quarter front on a performer who faces -Y; a profile would
#: occlude one arm and one leg outright.
AZIMUTH_DEG = 225.0
ELEVATION_DEG = 6.0
LENS_MM = 50.0
SENSOR_MM = 36.0

#: The generation's own frame. Both dimensions are divisible by 16 and this is the model
#: family's documented 480p bucket; Gate L checks it again downstream against the graph.
WIDTH, HEIGHT = 832, 480

#: Of the frame, over the performer's own silhouette at this pose — not over a landmark
#: cloud, and not over a whole performance. A composition decision, and it is E08's named
#: lever: its identity result was explicitly a FLOOR because the letterboxed reference put
#: the figure at ~165x480 with a face too small to hold. 0.90 leaves ~24 px of margin top
#: and bottom, which is headroom for Gate WHOLE and room for the model to put a room in.
HEIGHT_FRAC = 0.90
CENTRE_X_FRAC = 0.50
CENTRE_Y_FRAC = 0.50

#: Gate WHOLE's clearance. Small enough that it is not a second composition knob, large
#: enough that a body actually touching the border cannot creep under it.
MARGIN_PX = 8

#: A frame whose subject covers less of it than this is not a picture of the performer.
MIN_SUBJECT_FRAC = 0.01

#: Gate BACKDROP's two thresholds, in 8-bit levels, measured over the master's transparent
#: region only. The submitted composite reaches the plate through Blender's compositor, so
#: the plate is linearised on load and re-encoded by the Standard view transform on save;
#: that round trip is near-identity but not bit-exact, and `TOL` is the room it needs.
#: `MIN_SEPARATION` is the vacuity guard: below it, the plate and the flat fallback are the
#: same picture over that region and a PASS would be proving nothing. Both are calibrated
#: against the measured round trip in `tests/blender/check_plate_composite.py`, not guessed.
PLATE_TOL_255 = 2.0
PLATE_MIN_SEPARATION_255 = 4.0

#: Points handed to the framing solve. The solve is approximate by construction (see
#: `startframe.framing_cloud`); Gate WHOLE then runs on every vertex, so an under-report
#: here costs margin, never correctness.
FRAMING_CLOUD_CAP = 1500


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
    raise RenderGate(
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


class RenderGate(GateFailure):
    """A gate specific to rendering the start frame."""

    gate = "STARTFRAME"


#: The generator's frame rule for this model family. Both dimensions of `WIDTH, HEIGHT`
#: above are divisible by 16, and CLAUDE.md's environment block states the constraint as a
#: standing one: "Every video model constrains resolution and frame count (divisibility
#: rules, fixed buckets, frame-count forms) ... record the constraint per model in the spec
#: that first uses it." This is that constraint, in the tool whose output IS the
#: conditioning image a paid generation is submitted with.
FRAME_DIVISOR = 16


def require_frame_size(width, height, *, who="render_start_frame",
                       module_frame=None, gate=None, gate_id="STARTFRAME"):
    """`(width, height)` if a generator would accept them, else raise the caller's gate.

    F-34a858f5, wave 12. `--width` / `--height` were bare `type=int` with no bound and
    reached `SF.silhouette_extent` and `SF.gate_whole` unvalidated. MEASURED over the real
    `armature_core.startframe` functions with a three-point cloud: (832, 480) PASSes with a
    smallest margin of 54.2 px; (-832, 480) and (1, 1) both raise the typed `StartFrameGate`
    naming the failing sides -- so Gate WHOLE is NOT walked past and the false-PASS half of
    the routed question is REFUTED, because an integer flag cannot deliver a NaN. The
    residue this closes is the zero case: (0, 480) and (832, 0) both raise a bare, untyped
    `ZeroDivisionError` from inside `silhouette_extent`, which the halt contract records as
    "FAILED -- an unhandled error" at exit 1 -- and it happens AFTER
    `scene.render.resolution_x = 0` has already been assigned. An operator typo on the one
    tool whose output conditions a paid I2V submission got a stack trace naming a
    projection helper instead of a refusal naming the flag.

    The divisibility clause rides here rather than being left to Gate L downstream for the
    reason the finding gives: this refusal is the natural place to state the generator-legal
    constraint, instead of letting an arbitrary size reach the render and be caught (or
    not) by a graph check much later.

    WAVE 14, F-267361f5. `render_turnaround` — the tool that produces the PINNED shot-set,
    where one scale across characters is the entire product — had none of this, and its
    `--width`/`--height` reached the framing solvers unvalidated: measured on its own
    solvers with a three-point cloud, `(0, 1024)` and `(1024, 0)` each raise a bare
    `ZeroDivisionError` out of `startframe.silhouette_extent` AFTER
    `scene.render.resolution_x` has been set to zero, and `(-1024, 1024)` returns the same
    radius as `1024x1024` and only surfaces one render later inside Gate WHOLE. So this is
    now ONE implementation with two callers, parameterised only in what it says about
    itself — `who`, the module's own frame, and the caller's gate class — never in what it
    checks. `armature_core.startframe` is where the one implementation belongs and is
    outside this domain's globs, so the lift is FILED, not done.
    """
    gate = gate or RenderGate
    module_frame = list(module_frame or (WIDTH, HEIGHT))
    # F-6381b9ff, wave 22: `evidence["gate"]` is the RAISING CLASS's id, so the halt
    # line's `[<gate>]` prefix, `exc.gate` and this key are ONE id; the caller's
    # declared `gate_id` is the SUB-id and says which clause of that andon pulled.
    # Until wave 22 a single halt event printed two different gate ids, and
    # "TURNAROUND_FRAME" belonged to no class at all.
    ev = {"gate": gate.gate, "sub_gate": gate_id, "andon": gate.__name__, "who": who,
          "width": width, "height": height,
          "divisor": FRAME_DIVISOR, "module_frame": module_frame}
    bad = [name for name, v in (("width", width), ("height", height))
           if not isinstance(v, int) or isinstance(v, bool) or v <= 0]
    if bad:
        ev["non_positive"] = bad
        raise gate(
            f"--width={width!r} --height={height!r}: {' and '.join(bad)} must be a "
            f"positive integer. A zero dimension divides by zero inside the silhouette "
            f"solve and reaches the halt line as an unhandled error naming a projection "
            f"helper, after the scene resolution has already been set to it", ev)
    off = [name for name, v in (("width", width), ("height", height))
           if v % FRAME_DIVISOR]
    if off:
        ev["not_divisible"] = off
        raise gate(
            f"--width={width} --height={height}: {' and '.join(off)} is not divisible by "
            f"{FRAME_DIVISOR}. {who}'s output is submitted to, or conditions, a generation, "
            f"and the model family's frame buckets are multiples of {FRAME_DIVISOR} (this "
            f"tool's own frame is {module_frame[0]}x{module_frame[1]}); a frame it will not "
            f"accept is better refused here than after the render", ev)
    return int(width), int(height)


def require_shot_fraction(name, value, *, who="render_start_frame", gate=None,
                          gate_id="STARTFRAME_FRACTION"):
    """`float(value)` if `name` is a fraction of the frame, else raise the caller's gate.

    F-f0c261c1, wave 18, and the residue of the `require_frame_size` sweep. That sweep
    bounded `--width`/`--height` on both renderers and never reached the framing FRACTION
    on either — the one remaining flag that composes the shot on the tool whose plate
    conditions a paid I2V submission was a bare `type=float` with no bound.

    **A NaN walked past every clause below it.** MEASURED 2026-09-04 on the repo venv over
    a four-point cloud: `framing.solve_camera(cloud, cloud, 270, 8, 50.0, 36.0, 832, 480,
    height_frac=nan, end_x_frac=0.5)` RETURNS `radius=40.0` — the bisection ceiling — and
    no refusal, where `height_frac=0.0`, `-0.5` and `inf` each raise `FramingError` ("the
    requested framing is not reachable between 0.5 and 40.0"). The reachability clause
    cannot fire because `nan <= x` and `nan > x` are both False, so the search terminates
    at its own ceiling and hands the caller a number. Everything after that passes:
    `require_frame_size` has already ruled on width and height, the render is a
    correctly-sized RGBA PNG, and `SF.gate_whole` reads a subject a handful of pixels wide
    near the frame centre — well inside every margin — so Gate WHOLE returns its strongest
    verdict, "whole silhouette in frame; smallest margin 206.1 px", over a figure occupying
    0.1011 of the frame. The record then publishes `height_frac_requested: NaN`.

    **The band is `0 < f <= 1`**, because a fraction of the frame height is that by
    construction. `1.0` is INSIDE — the subject exactly filling the frame is the tightest
    legal request, not an illegal one; refusing it would repeat F-2a564189, where
    `parts.tightened` refused the exact match it existed to accept. Above 1 is not a
    tighter fit but a subject taller than the picture, and `render_turnaround` returns a
    solved radius for `1.5` with no refusal at all.

    **Finiteness is spelled through `armature_core.parts.require_finite`**, the repo's ONE
    implementation of wave 10's rule 4, rather than as another copy of `math.isfinite`;
    only the upper clause is new, because `require_finite` bounds no ceiling. The evidence
    dict is the caller's, so each caller keeps its own gate id and its own andon name.

    ONE implementation with two callers, parameterised only in what it says about ITSELF —
    `who`, the caller's gate class, the caller's gate id — never in what it checks. This is
    the shape `require_frame_size` above already has, and for the same reason:
    `armature_core.startframe` is where the one implementation belongs and is outside this
    domain's globs, so the lift is FILED, not done.
    """
    gate = gate or RenderGate
    # F-6381b9ff: the class's id under "gate", the caller's declared id under
    # "sub_gate" — see `require_frame_size` above.
    ev = {"gate": gate.gate, "sub_gate": gate_id, "andon": gate.__name__, "who": who,
          "flag": name, "clause": "not_a_finite_positive_fraction"}
    v = parts.require_finite(name, value, gate, ev, positive=True)
    if v > 1.0:
        # The operand rides the evidence in BOTH clauses. `require_finite` writes
        # `ev[name] = v` on its own way out; this branch never reaches it, and an evidence
        # dict that names the flag without carrying the value it refused is a refusal a
        # reader cannot check.
        ev["clause"] = "above_one"
        ev[name] = v
        raise gate(
            f"{name}={v!r} is not a fraction of the frame. A framing fraction is "
            f"0 < f <= 1 by construction: 1.0 is the subject exactly filling the picture, "
            f"and anything above it asks for a figure taller than the frame it is being "
            f"solved into. The solve does not refuse that — measured on "
            f"render_turnaround's own solver, 1.5 returns a radius and the run renders "
            f"eight well-formed views of a subject cropped on every one", ev)
    return v


#: WAVE 28, F-2b8afc38 -- the two operator-facing lines of `--help`, DERIVED, not typed.
#:
#: `prog` defaults to `os.path.basename(sys.argv[0])`, which under `blender -b -P` is the
#: BLENDER BINARY: every parser in this domain printed `usage: blender.exe [-h] --glb GLB
#: ...` and omitted the `-b -P tools/<name>.py --` prologue that every flag below requires,
#: so the string an operator would copy is not an invocation that works. README.md:181 is
#: the route line this spells. `description` was absent on all 20 parsers here, so `--help`
#: could not say what any tool does; it is read off this module's own docstring rather than
#: retyped, because two spellings of one sentence is how the other one goes stale.
HELP_PROG = "blender -b -P tools/render_start_frame.py --"
HELP_DESCRIPTION = ((__doc__ or "").strip().splitlines() or [None])[0]


def gate_output_overwrite(out, planned, overwrite, gate_cls):
    """`(pre_existed, already_present, strays)` for `--out`, refusing a silent overwrite.

    WAVE 28, F-8b7f48a8 (panel CRITICAL). MEASURED on `3380ae2` over the 21 Blender-side
    instruments: **36 `os.makedirs` call sites, every one `exist_ok=True`, no refusal, no
    numbering, and no line in any record saying the directory already existed.** The three
    renderers that author the images a generation is conditioned on -- `render_turnaround`,
    `render_start_frame` and `preview_glb` -- also had no `unexpected_files_in_out_dir`
    sweep, where `render_performer.py:511` and `preview_walk.py:365` both derive one and
    say in their own comments why. All three write FIXED names, so a re-run always lands on
    the previous run's: a re-run with fewer views or a different name left the earlier run's
    masters beside this run's, the manifest named only its own, and every consumer that
    reads the directory as a set (`encode_control.py:138`, `build_payload.py:363`, both a
    bare listdir) picked up both.

    THE POLICY, stated rather than defaulted: a run that would land on its own earlier
    output REFUSES, by name, ABOVE `os.makedirs` -- so a declined run leaves nothing behind
    -- unless `--overwrite` says to replace it. When it does replace, the success record
    and the success line both carry `out_dir_pre_existed` and `overwrote`, which is what
    makes two runs into one `--out` distinguishable in a scrollback.

    SEAM 1 (`wave-28/seams-inbox.md`): builders' `F-5fd16451` is the same mechanism at
    `build_assembly_payload.py:831`. The flag name, the clause word, the sentence and the
    two record keys are agreed across both domains. `armature_core.parts` is where a shared
    helper would live and is another domain's owned file this wave, so these three
    Blender-side copies are held to ONE text by `tests/test_instruments_amend_w28.py`
    instead -- the arrangement `_render_status`'s nine copies already have.

    `strays` is a DIAGNOSTIC: it gates nothing here either.
    """
    pre_existed = os.path.isdir(out)
    already_present = sorted(f for f in planned
                             if os.path.isfile(os.path.join(out, f))
                             ) if pre_existed else []
    strays = sorted(f for f in os.listdir(out)
                    if f.lower().endswith(".png") and f not in set(planned)
                    ) if pre_existed else []
    if already_present and not overwrite:
        raise gate_cls(
            f"{len(already_present)} of the {len(planned)} files this run writes: already "
            f"on disk from an earlier run; this run would replace what is there. Pass "
            f"--overwrite to replace it, or point --out at a directory of its own",
            {"clause": "output_already_exists", "out": os.path.abspath(out),
             "already_present": already_present, "planned": len(planned),
             "unexpected_files_in_out_dir": strays,
             "compensator": "delete --out; owner: the executor session"})
    return pre_existed, already_present, strays


def parse_args(argv=None):
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser(
        prog=HELP_PROG, description=HELP_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--glb", action="append", required=True,
                    help="the performer GLB whose frame becomes the model's picture of "
                         "the world; read only")
    ap.add_argument("--out", required=True,
                    help="the directory the RGBA master, the composites and "
                         "start_frame_provenance.json are written into. Compensator: "
                         "delete it; owner: the executor session")
    ap.add_argument("--frame", type=int, default=0,
                    help="which frame of the action to stage, 0-based (argparse eats "
                         "leading minus signs: pass flags as --flag=value). Ignored when "
                         "--frames is set; used as the first index with --end-frame")
    ap.add_argument("--frames", default=None,
                    help="FLF2V pair as `i,j` (0-based). Stages BOTH indices in one "
                         "session under one lighting/framing/composite lock and writes a "
                         "`pair` block in provenance (F-d7f9fed5). Refuses when i == j")
    ap.add_argument("--end-frame", type=int, default=None,
                    help="alternate FLF2V spelling: pair (--frame, --end-frame). Refuses "
                         "when equal to --frame")
    ap.add_argument("--fps", type=int, default=16,
                    help="frame rate --frame is counted in (default 16); glTF key times "
                         "are SECONDS, so a mismatch stages a different moment")
    ap.add_argument("--width", type=int, default=WIDTH,
                    help=f"submitted frame width in pixels (default {WIDTH}). It must be "
                         f"a size the generator accepts -- see the model's own "
                         f"divisibility rule -- and Gate WHOLE bounds the figure in it")
    ap.add_argument("--height", type=int, default=HEIGHT,
                    help=f"submitted frame height in pixels (default {HEIGHT}); same "
                         f"generator-legality rule as --width")
    ap.add_argument("--height-frac", type=float, default=HEIGHT_FRAC,
                    help=f"how tall the FIGURE stands as a fraction of the frame height "
                         f"(default {HEIGHT_FRAC}) -- the camera distance is solved to "
                         f"put it there. Bounded: it is a fraction, not a multiplier")
    ap.add_argument("--overwrite", action="store_true",
                    help="replace this run's own files where --out already holds them "
                         "from an earlier run. WITHOUT it the run REFUSES rather than "
                         "overwriting, by name, before the output directory is touched")
    ap.add_argument("--composite", default=None,
                    help="the submitted RGB composite's background, as linear floats "
                         "`r,g,b`. THE ALPHA LAW: the render is authored RGBA with a real "
                         "alpha channel and this names the deliberate choice composited "
                         "behind it. Required — there is no default, because a default is "
                         "how a grey void becomes accidental (argparse eats leading minus "
                         "signs: pass as --composite=r,g,b)")
    ap.add_argument("--composite-why", default=None,
                    help="one sentence, into the provenance, on why that colour. A choice "
                         "nobody wrote down is indistinguishable from a leftover")
    ap.add_argument("--plate", default=None,
                    help="a PLATE image, already at the generation's exact frame size (see "
                         "make_plate.py), composited BEHIND the authored master instead of "
                         "the flat colour. The flat composite is still rendered and kept as "
                         "the counterfactual, and --composite still names the world that "
                         "LIGHTS the scene, so the plate is the only thing that changes")
    ap.add_argument("--plate-why", default=None,
                    help="one sentence, into the provenance, on why THIS plate")
    ap.add_argument("--camera-path", default=None,
                    help="optional keyframed orbit JSON (F-82f88f23); default solve_camera")
    ap.add_argument("--set", action="append", default=None,
                    help="owned 3D set/prop GLB imported as non-deforming scenery "
                         "(F-91411b51). Appendable. Excluded from subject framing solve; "
                         "included in the render. --plate remains the 2D fallback")
    ap.add_argument("--floor", type=int, default=1,
                    help="1 draws a ground plane; recorded either way")
    ap.add_argument("--shadow-layer", type=int, default=0,
                    help="1 drops the rendered floor from the picture and keeps only the "
                         "shadow it catches, multiplied onto the plate — so the figure "
                         "rides the WHOLE plate instead of a band above our own floor. "
                         "Needs --floor=1 (the plane must exist to catch anything) and "
                         "--plate. The alternative treatment, an EEVEE shadow catcher, was "
                         "measured shut on this build: see armature_core.startframe."
                         "shadow_ratio")
    ap.add_argument("--floor-material", default="default",
                    choices=("default", "wood"),
                    help="`default` leaves the plane unshaded, as every wave before E12 had "
                         "it — a pale studio slab. `wood` builds a PROCEDURAL dark-wood "
                         "material from shader nodes: no image file is read, so it adds no "
                         "licence surface of any kind")
    return ap.parse_args(argv)


def resolve_frame_indices(args):
    """Return the 0-based frame indices this run stages.

    Single-frame: ``(--frame,)``. FLF pair: two distinct indices from ``--frames=i,j``
    or ``(--frame, --end-frame)``. Refuses a pair whose ends are the same index
    (F-d7f9fed5).
    """
    if args.frames is not None and args.end_frame is not None:
        raise ArmatureError(
            "--frames and --end-frame both name the FLF pair; pass one spelling",
            {"clause": "frames_and_end_frame_both_set",
             "frames": args.frames, "end_frame": args.end_frame})
    if args.frames is not None:
        parts = [p.strip() for p in str(args.frames).split(",")]
        if len(parts) != 2 or any(p == "" for p in parts):
            raise ArmatureError(
                f"--frames={args.frames!r} must be exactly two integers as i,j",
                {"clause": "frames_pair_shape", "frames": args.frames})
        try:
            i, j = int(parts[0]), int(parts[1])
        except ValueError as exc:
            raise ArmatureError(
                f"--frames={args.frames!r} must be integers i,j",
                {"clause": "frames_pair_not_int", "frames": args.frames}) from exc
        if i == j:
            raise RenderGate(
                f"--frames={args.frames!r} names the same index twice; an FLF2V pair "
                f"needs two distinct authored keys under one lock",
                {"clause": "flf_pair_same_index", "frames": [i, j]})
        return (i, j)
    if args.end_frame is not None:
        i, j = int(args.frame), int(args.end_frame)
        if i == j:
            raise RenderGate(
                f"--frame={i} and --end-frame={j} are the same index; an FLF2V pair "
                f"needs two distinct authored keys under one lock",
                {"clause": "flf_pair_same_index", "frames": [i, j]})
        return (i, j)
    return (int(args.frame),)


def frame_role_prefix(indices, index):
    """Filename stem for one staged index: start_frame / end_frame."""
    if len(indices) == 1:
        return "start_frame"
    if index == indices[0]:
        return "start_frame"
    if index == indices[-1]:
        return "end_frame"
    return f"frame_{index:05d}"


def plan_output_files(indices, *, backdrop, shadow_layer):
    """Derive the fixed names this run writes (overwrite gate population)."""
    planned = ["start_frame_provenance.json", "empty_plate.png"]
    for idx in indices:
        stem = frame_role_prefix(indices, idx)
        planned.append(f"{stem}_rgba.png")
        planned.append(f"{stem}_flat.png" if backdrop else f"{stem}.png")
        if backdrop:
            planned.append(f"{stem}.png")
        if shadow_layer:
            planned += [f"{stem}_shadow_lit.png", f"{stem}_shadow_cast.png",
                        f"{stem}_plate_shadowed.png"]
    seen, out = set(), []
    for name in planned:
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out


#: The procedural floor, as numbers rather than as a picture. Kept out of the node-building
#: code so the values can be read and changed without a Blender session, and so the one
#: claim that matters for the licence map — *no image is involved* — is checkable by looking
#: at a dict rather than by trusting a comment.
WOOD = {
    "plank_scale": 3.0,        # bands across the plane; low = wide boards
    "grain_scale": 12.0,       # noise driving the grain within a board
    "grain_distortion": 2.2,   # how far the grain bends the bands
    "grain_detail": 6.0,
    "dark_linear": (0.0130, 0.0072, 0.0038),   # linear, in the plate's own key
    "light_linear": (0.0420, 0.0245, 0.0132),
    # Rough and barely specular, because of the CAMERA and not because of taste. The shot
    # sits at 6 degrees of elevation, a grazing view of the floor, and at grazing incidence
    # Fresnel drives the specular lobe toward 1.0: the first values here (roughness 0.55,
    # specular 0.30) measured a floor mean of 0.0999 looking down at 80 degrees and 0.3515
    # at the angle the pipeline actually shoots from — a dark wood washed pale by reflected
    # world. A rough surface scatters that grazing lobe instead of mirroring it.
    "roughness": 0.95,
    "specular": 0.02,
}


def build_wood_material(spec=WOOD):
    """A dark-wood floor material built entirely from procedural nodes.

    **The licence reason this is procedural.** A wood texture is the most ordinary asset in
    the world to download, and the most ordinary way for a CC-BY-NC or a
    research-only-derived image to enter a pipeline that has banned both outright. A shader
    graph of noise and waves has no provenance to check because there is no third-party work
    in it: the andon below refuses to return a material that reads any image at all, so the
    claim on the record is enforced rather than asserted.

    The colours are linear and dark on purpose. The plate this floor sits under is a dim bar;
    a floor lit to studio brightness would read as a lit stage in front of a photograph,
    which is the thing the Director's eye rejected in the band-only composite.
    """
    mat = bpy.data.materials.new("previz_floor_wood")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (spec["plank_scale"],) * 3

    grain = nt.nodes.new("ShaderNodeTexNoise")
    grain.inputs["Scale"].default_value = spec["grain_scale"]
    grain.inputs["Detail"].default_value = spec["grain_detail"]

    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "Y"
    wave.inputs["Scale"].default_value = 1.0
    wave.inputs["Distortion"].default_value = spec["grain_distortion"]
    wave.inputs["Detail"].default_value = spec["grain_detail"]

    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*spec["dark_linear"], 1.0)
    ramp.color_ramp.elements[1].color = (*spec["light_linear"], 1.0)

    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = spec["roughness"]
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = spec["specular"]

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(coord.outputs["Object"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], grain.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], wave.inputs["Vector"])
    nt.links.new(grain.outputs["Fac"], wave.inputs["Distortion"])
    nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    image_nodes = [n.bl_idname for n in nt.nodes if "TexImage" in n.bl_idname
                   or "TexEnvironment" in n.bl_idname]
    if image_nodes:
        raise RenderGate(
            "the procedural floor material reads an image, which is the one thing it exists "
            "not to do: an image carries a licence, and this pipeline bans non-commercial "
            "and research-only assets outright",
            {"clause": "floor_material_reads_an_image", "image_nodes": image_nodes})
    return mat, {"kind": "procedural", "reads_image_file": False,
                 "node_types": sorted({n.bl_idname for n in nt.nodes}),
                 "spec": {k: list(v) if isinstance(v, tuple) else v
                          for k, v in spec.items()},
                 "licence_surface": ("none — no image, no third-party asset, no downloaded "
                                     "texture; the material is shader nodes only")}


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _alpha_channel(path, width, height):
    """The alpha plane of a rendered RGBA PNG, top row first."""
    img = bpy.data.images.load(path)
    try:
        buf = np.empty(width * height * 4, dtype=np.float32)
        img.pixels.foreach_get(buf)
        return np.ascontiguousarray(buf.reshape(height, width, 4)[::-1, :, 3])
    finally:
        bpy.data.images.remove(img)


def _pixels(path, width, height):
    """A rendered PNG as a top-down (H, W, 3) float array.

    `image.pixels` is bottom-up; the flip is what makes the reported bbox agree with the
    coordinates every other tool in this repo — and with the file a human opens — uses.

    Every image Gate BACKDROP compares is read through THIS function, so whatever colour
    convention Blender applies on load applies identically to all of them and the
    differences between them stay meaningful.
    """
    img = bpy.data.images.load(path)
    try:
        buf = np.empty(width * height * 4, dtype=np.float32)
        img.pixels.foreach_get(buf)
        return np.ascontiguousarray(buf.reshape(height, width, 4)[::-1, :, :3])
    finally:
        bpy.data.images.remove(img)


def _image_size(path):
    """(width, height) of an image on disk, without decoding it into numpy."""
    img = bpy.data.images.load(path)
    try:
        return int(img.size[0]), int(img.size[1])
    finally:
        bpy.data.images.remove(img)


def wire_plate_composite(scene, plate_path):
    """Point the render at `master OVER plate`, done by Blender's own compositor.

    Alpha-over in the renderer rather than by hand in byte space, for the same reason the
    flat composite is a second render rather than a numpy fill: the sRGB transfer is the
    renderer's, and the performer's antialiased edge has to blend against the plate in
    linear light or it acquires a fringe. The plate is declared sRGB on load so it is
    linearised going in and the Standard view transform re-encodes it going out.

    **The API here is Blender 5.x's, read off the running build rather than remembered.**
    `Scene.node_tree` and `CompositorNodeComposite` are gone: the scene's compositor is a
    `CompositorNodeTree` datablock hung on `Scene.compositing_node_group`, and its result
    leaves through a group output socket. `Alpha Over` names its sockets now, and its
    premultiply switch is the `Straight Alpha` boolean — left False, because Render Layers
    hands this node an already-premultiplied foreground and converting it again would
    darken every antialiased edge pixel against the plate.

    Sockets are addressed by NAME throughout. The one place this file ever used positional
    socket indices, it was addressing a node whose widget order had to be re-confirmed
    empirically at every size change; names survive a release, positions do not.
    """
    scene.render.film_transparent = True          # the render layer must carry its alpha
    scene.render.use_compositing = True

    tree = bpy.data.node_groups.new("start_frame_plate", "CompositorNodeTree")
    tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    scene.compositing_node_group = tree

    rl = tree.nodes.new("CompositorNodeRLayers")
    rl.scene = scene
    img = tree.nodes.new("CompositorNodeImage")
    plate_img = bpy.data.images.load(plate_path)
    plate_img.colorspace_settings.name = "sRGB"
    img.image = plate_img
    over = tree.nodes.new("CompositorNodeAlphaOver")
    over.inputs["Straight Alpha"].default_value = False
    out = tree.nodes.new("NodeGroupOutput")

    tree.links.new(img.outputs["Image"], over.inputs["Background"])
    tree.links.new(rl.outputs["Image"], over.inputs["Foreground"])
    tree.links.new(over.outputs["Image"], out.inputs["Image"])
    return plate_img


def action_frame_range():
    """(first, last) scene frames the imported actions actually key, or None.

    The pose andon's quantity. `frame_set` past the end of an action holds the last pose
    and renders it without complaint, so a frame index that misses the performance
    produces a well-formed picture of the wrong moment.
    """
    lo = hi = None
    for act in bpy.data.actions:
        try:
            a, b = act.frame_range
        except (AttributeError, TypeError):
            continue
        lo = a if lo is None else min(lo, a)
        hi = b if hi is None else max(hi, b)
    if lo is None:
        return None
    return float(lo), float(hi)


def main():
    started = time.time()
    a = parse_args()
    from render_performer import (  # noqa: E402  — lazy; see import note above
        load_camera_path, subject_glbs, glb_provenance_records)
    glbs = subject_glbs(a)
    primary_glb = glbs[0]
    subjects_prov = glb_provenance_records(glbs, _sha256)
    cam_keys = load_camera_path(getattr(a, 'camera_path', None))
    out = os.path.abspath(a.out)
    indices = resolve_frame_indices(a)
    width, height = require_frame_size(int(a.width), int(a.height))
    height_frac = require_shot_fraction("--height-frac", a.height_frac)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    blender_scene.set_frame_rate(scene, a.fps)
    meshes, arms, info = blender_scene.import_glb(primary_glb, expected_fps=a.fps)
    for extra in glbs[1:]:
        blender_scene.import_glb(extra, expected_fps=a.fps)

    # F-91411b51: owned 3D sets — scenery, not the framing subject.
    set_records = []
    set_meshes = []
    set_arms = []
    for sp in (a.set or []):
        path = os.path.abspath(sp)
        if not os.path.isfile(path):
            raise RenderGate(
                f"--set={sp!r} is not a file at {path}",
                {"clause": "set_glb_is_not_a_file", "set": path, "set_as_typed": sp})
        sm, sa, sinfo = blender_scene.import_glb(path, expected_fps=a.fps)
        for arm in sa:
            arm.hide_render = True  # non-deforming scenery; armature not drawn
            set_arms.append(arm)
        visible = blender_scene.render_visible_meshes(scene, sm)
        set_meshes.extend(visible)
        set_records.append({
            "glb": path, "sha256": _sha256(path),
            "meshes": [o.name for o in visible],
            "armatures_hidden": [o.name for o in sa],
            "import_info": sinfo,
        })

    engine = select_engine(scene)
    scene.render.resolution_x, scene.render.resolution_y = width, height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "Standard"
    composite_rgb = SF.composite_colour(a.composite)

    backdrop = os.path.abspath(a.plate) if a.plate else None
    if a.shadow_layer and not (backdrop and a.floor):
        raise RenderGate(
            "--shadow-layer needs both --floor=1 and --plate: the plane has to exist to "
            "catch a shadow, and the shadow has to be multiplied onto something",
            {"clause": "shadow_layer_needs_floor_and_plate", "floor": a.floor, "plate": backdrop})
    if backdrop:
        if not os.path.isfile(backdrop):
            raise RenderGate(
                f"--plate={a.plate!r} is not a file; nothing exists at {backdrop}. The "
                f"plate is the image composited BEHIND the authored master, so there is "
                f"no frame to submit without it: check the path, or run make_plate.py to "
                f"produce one at this frame's exact size",
                {"clause": "plate_is_not_a_file", "plate": backdrop,
                 "plate_as_typed": a.plate})
        pw, ph = _image_size(backdrop)
        if (pw, ph) != (width, height):
            raise RenderGate(
                f"the plate is {pw}x{ph} and the frame is {width}x{height}. Fitting is not "
                f"this tool's job precisely so that the fit is an artifact with its own "
                f"hash and a recorded transform: run make_plate.py first",
                {"clause": "plate_size_does_not_match_the_frame",
                 "plate": backdrop, "plate_size": [pw, ph],
                 "frame_size": [width, height]})

    subject = blender_scene.render_visible_meshes(scene, meshes)
    if not subject:
        raise RenderGate(
            f"{primary_glb} imported {len(meshes)} mesh object(s) and none of them is "
            f"render-visible ({[o.name for o in meshes]}); there is no figure to stage, "
            f"and framing against hidden geometry would compose a frame of an object the "
            f"renderer will not draw",
            {"clause": "glb_has_no_render_visible_mesh", "glb": primary_glb,
             "mesh_objects_all": [o.name for o in meshes],
             "mesh_objects_render_visible": []})

    span = action_frame_range()
    scene.frame_start, scene.frame_end = 1, max(1, int(span[1]) if span else 1)

    # Per-index silhouette clouds (subject only — sets excluded from framing solve).
    clouds_by_index = {}
    for idx in indices:
        blender_scene.set_scene_frame(scene, idx)
        if span is not None and not (span[0] <= scene.frame_current <= span[1]):
            raise RenderGate(
                f"frame {idx} maps to scene frame {scene.frame_current}, outside the "
                f"action's own keyed range {span}. Blender holds the nearest pose and renders "
                f"it with no error, so the start frame would be a well-formed picture of a "
                f"moment the performance never had",
                {"clause": "frame_outside_the_keyed_range",
                 "requested_frame": idx, "scene_frame": scene.frame_current,
                 "action_range": list(span)})
        verts = blender_scene.evaluated_world_vertices(scene, subject)
        if verts.shape[0] == 0:
            raise RenderGate(
                f"the subject evaluates to no vertices at --frame={idx} (scene frame "
                f"{scene.frame_current}, action range {list(span) if span else None}): the "
                f"{len(subject)} render-visible mesh(es) "
                f"{[o.name for o in subject]} produce an empty evaluated geometry there, so "
                f"there is nothing to frame and nothing to light",
                {"clause": "subject_has_no_vertices_at_this_frame",
                 "requested_frame": idx, "scene_frame": scene.frame_current,
                 "action_range": list(span) if span else None,
                 "subject_render_visible": [o.name for o in subject]})
        clouds_by_index[idx] = [tuple(map(float, p)) for p in verts]

    # Shared camera lock: union of subject silhouettes across the staged indices.
    cloud = []
    for idx in indices:
        cloud.extend(clouds_by_index[idx])
    solve_cloud = SF.framing_cloud(cloud, cap=FRAMING_CLOUD_CAP)
    sol = framing.solve_camera(solve_cloud, solve_cloud, AZIMUTH_DEG, ELEVATION_DEG,
                               LENS_MM, SENSOR_MM, width, height,
                               height_frac=height_frac,
                               end_x_frac=CENTRE_X_FRAC, target_y_frac=CENTRE_Y_FRAC)
    target, radius = tuple(sol["target"]), float(sol["radius"])

    # Gate WHOLE on every staged index (shared camera).
    gates_whole = {}
    extents = {}
    for idx in indices:
        extent = SF.silhouette_extent(clouds_by_index[idx], target, radius, AZIMUTH_DEG,
                                      ELEVATION_DEG, LENS_MM, SENSOR_MM, width, height)
        extents[idx] = extent
        gates_whole[idx] = SF.gate_whole(extent, width, height, MARGIN_PX)

    world = bpy.data.worlds.new("performer")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (
        composite_rgb[0], composite_rgb[1], composite_rgb[2], 1.0)

    key = bpy.data.lights.new("key", type="SUN")
    key.energy = 3.2
    ko = bpy.data.objects.new("key", key)
    scene.collection.objects.link(ko)
    ko.rotation_euler = (math.radians(58), 0.0, math.radians(-25))
    fill = bpy.data.lights.new("fill", type="SUN")
    fill.energy = 1.1
    fo = bpy.data.objects.new("fill", fill)
    scene.collection.objects.link(fo)
    fo.rotation_euler = (math.radians(65), 0.0, math.radians(150))

    floor_material = {"applied": None}
    gob = None
    if a.floor:
        ground = bpy.data.meshes.new("ground")
        ground.from_pydata([(-20, -20, 0), (20, -20, 0), (20, 20, 0), (-20, 20, 0)], [],
                           [(0, 1, 2, 3)])
        gob = bpy.data.objects.new("ground", ground)
        scene.collection.objects.link(gob)
        zs = [(o.matrix_world @ Vector(c)).z for o in subject for c in o.bound_box]
        gob.location = (0.0, 0.0, min(zs))
        if a.floor_material == "wood":
            mat, floor_material = build_wood_material()
            ground.materials.append(mat)
            floor_material["applied"] = "ground"
        else:
            floor_material = {"applied": None, "kind": "default",
                              "note": ("no material assigned; Blender's default surface — "
                                       "the pale studio slab every wave before E12 had")}

    cam_data = bpy.data.cameras.new("start_cam")
    cam_data.lens, cam_data.sensor_fit, cam_data.sensor_width = LENS_MM, "AUTO", SENSOR_MM
    cam_data.clip_start, cam_data.clip_end = 0.01, 100.0
    cam = bpy.data.objects.new("start_cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.matrix_world = blender_scene.orbit_matrix(Vector(target), radius,
                                                  ELEVATION_DEG, AZIMUTH_DEG)

    if a.shadow_layer:
        gob.hide_render = True

    planned = plan_output_files(indices, backdrop=bool(backdrop),
                                shadow_layer=bool(a.shadow_layer))
    out_dir_pre_existed, already_present, strays = gate_output_overwrite(
        out, planned, a.overwrite, RenderGate)
    if already_present:
        print("[overwrite] " + json.dumps(
            {"out": os.path.abspath(out), "overwrote": already_present}))
    os.makedirs(out, exist_ok=True)

    def _render_still(path):
        _before = rc.render_target_snapshot(path)
        scene.render.filepath = path
        render_result = bpy.ops.render.render(write_still=True)
        _status = _render_status(render_result)
        if "FINISHED" not in _status:
            raise RenderGate(
                f"the render operator did not report FINISHED for "
                f"{os.path.basename(path)}; it returned {_status!r}, and any file at "
                f"that path is then the previous run's",
                {"clause": "operator_status", "status": _status,
                 "path": os.path.abspath(path),
                 "out": os.path.dirname(os.path.abspath(path)),
                 "compensator": "delete --out; owner: the executor session"})
        rc.require_render_target_moved(
            path, _before, RenderGate,
            {"gate": RenderGate.gate, "sub_gate": "RENDER_TARGET",
             "who": "render_start_frame"})

    per_frame = []
    # Empty plate once under the shared camera (character hidden; sets stay — they are world).
    blender_scene.set_scene_frame(scene, indices[0])
    for o in subject + arms:
        o.hide_render = True
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGB"
    plate_path = os.path.join(out, "empty_plate.png")
    _render_still(plate_path)
    for o in subject + arms:
        o.hide_render = False

    for idx in indices:
        stem = frame_role_prefix(indices, idx)
        blender_scene.set_scene_frame(scene, idx)

        if a.shadow_layer:
            gob.hide_render = True

        rgba_path = os.path.join(out, f"{stem}_rgba.png")
        scene.render.film_transparent = True
        scene.render.image_settings.color_mode = "RGBA"
        _render_still(rgba_path)
        alpha_plane = _alpha_channel(rgba_path, width, height)
        gate_alpha = SF.gate_alpha(float((alpha_plane < 0.5).mean()), composite_rgb,
                                   a.composite_why, master_path=rgba_path)

        scene.render.film_transparent = False
        scene.render.image_settings.color_mode = "RGB"
        flat_path = os.path.join(out, f"{stem}_flat.png" if backdrop else f"{stem}.png")
        _render_still(flat_path)

        frame_px = _pixels(flat_path, width, height)
        plate_px = _pixels(plate_path, width, height)
        diff = np.abs(frame_px - plate_px).max(axis=2) > (1.0 / 255.0)
        frac = float(diff.mean())

        shadow = None
        if a.shadow_layer:
            gob.hide_render = False
            for o in subject + arms:
                o.hide_render = True
            lit_path = os.path.join(out, f"{stem}_shadow_lit.png")
            _render_still(lit_path)
            for o in subject + arms:
                o.hide_render = False
            cast_path = os.path.join(out, f"{stem}_shadow_cast.png")
            _render_still(cast_path)
            gob.hide_render = True
            ratio = SF.shadow_ratio(_pixels(cast_path, width, height),
                                    _pixels(lit_path, width, height))
            ratio[alpha_plane > 0.0] = 1.0
            shadowed = SF.apply_shadow(_pixels(backdrop, width, height), ratio)
            shadowed_path = os.path.join(out, f"{stem}_plate_shadowed.png")
            pngio.write_png(shadowed_path,
                            np.clip(shadowed * 255.0, 0, 255).round().astype(np.uint8))
            darkened = ratio < 0.99
            shadow = {
                "treatment": "authored shadow layer (ratio of two floor renders, in linear)",
                "why_not_a_shadow_catcher": (
                    "measured 2026-08-12 on this build: Object.is_shadow_catcher exists and "
                    "EEVEE ignores it — the catcher render came back byte-identical to the "
                    "ordinary opaque floor (mean alpha 0.7105664 both) — and Cycles is not in "
                    "this build's engine list. The alternative the spec allows was shut, so "
                    "this is the branch it left"),
                "lit_reference": {"path": lit_path, "sha256": _sha256(lit_path)},
                "cast_reference": {"path": cast_path, "sha256": _sha256(cast_path)},
                "shadowed_plate": {"path": shadowed_path, "sha256": _sha256(shadowed_path)},
                "darkened_fraction_of_frame": float(darkened.any(axis=2).mean()),
                "min_ratio": float(ratio.min()), "mean_ratio_where_darkened": (
                    float(ratio[darkened].mean()) if darkened.any() else None),
                "held_at_one_over_the_figure": True,
                "eps": SF.SHADOW_FLOOR_EPS,
            }
            backdrop_for_composite = shadowed_path
        else:
            backdrop_for_composite = backdrop

        frame_path, gate_backdrop = flat_path, None
        if backdrop:
            wire_plate_composite(scene, backdrop_for_composite)
            frame_path = os.path.join(out, f"{stem}.png")
            _render_still(frame_path)
            void = alpha_plane < 0.5
            sub_px = _pixels(frame_path, width, height)
            back_px = _pixels(backdrop_for_composite, width, height)
            gate_backdrop = SF.gate_backdrop(
                void_vs_plate_255=float(np.abs(sub_px[void] - back_px[void]).mean() * 255.0),
                plate_vs_flat_255=float(np.abs(back_px[void] - frame_px[void]).mean() * 255.0),
                transparent_fraction=float(void.mean()),
                why=a.plate_why, tol_255=PLATE_TOL_255,
                min_separation_255=PLATE_MIN_SEPARATION_255,
                plate=backdrop_for_composite,
                plate_sha256=_sha256(backdrop_for_composite))

        ev_cov = {
            "gate": RenderGate.gate, "sub_gate": "COVERAGE",
            "min_fraction": MIN_SUBJECT_FRAC, "subject_fraction": frac,
            "empty_plate": plate_path,
            "note": ("fraction of pixels differing from an empty-plate render of the same "
                     "camera, lights and floor with the character hidden. Sets stay in the "
                     "empty plate — they are world. It INCLUDES the figure's shadow on the "
                     "ground plane, so its bbox bounds subject+shadow and is a diagnostic; "
                     "Gate WHOLE is what bounds the body"),
            "out": os.path.abspath(out),
            "written_so_far": sorted(f for f in os.listdir(out)
                                     if os.path.isfile(os.path.join(out, f))),
            "compensator": "delete --out; owner: the executor session"}
        if frac < MIN_SUBJECT_FRAC:
            raise RenderGate(
                f"the render differs from the empty plate over only {frac:.5f} of the image "
                f"(floor {MIN_SUBJECT_FRAC}); the performer is not in it, and a frame of an "
                f"empty floor would condition the whole generation", ev_cov)
        ev_cov["verdict"] = f"subject covers {frac:.4f} of the frame"
        ys, xs = np.nonzero(diff)
        rendered_bbox = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
        per_frame.append({
            "index": idx, "stem": stem, "scene_frame": scene.frame_current,
            "rgba_path": rgba_path, "flat_path": flat_path, "frame_path": frame_path,
            "gate_alpha": gate_alpha, "gate_backdrop": gate_backdrop,
            "gate_whole": gates_whole[idx], "extent": extents[idx],
            "ev_cov": ev_cov, "frac": frac, "rendered_bbox": rendered_bbox,
            "shadow": shadow,
            "pose_signature": blender_scene.evaluated_geometry_signature(
                subject, scene=scene),
        })

    first = per_frame[0]
    provenance = {
        "tool": "render_start_frame", "tool_version": TOOL_VERSION,
        "blender": blender_scene.blender_provenance(),
        "source": {"glb": os.path.abspath(primary_glb), "sha256": _sha256(primary_glb),
                   "subjects": subjects_prov,
                   "camera_path": getattr(a, "camera_path", None),
                   "frame_index": first["index"], "scene_frame": first["scene_frame"],
                   "action_frame_range": list(span) if span else None,
                   "frame_indices": list(indices),
                   "pose_signature": first["pose_signature"],
                   "pose_signature_selection": "render_visible_meshes"},
        "sets": set_records,
        "resolution": [width, height], "fps": a.fps, "floor_drawn": bool(a.floor),
        "floor_material": floor_material,
        "out_dir_pre_existed": out_dir_pre_existed,
        "overwrote": already_present,
        "unexpected_files_in_out_dir": strays,
        "unexpected_files_rule": ("every file in --out whose name ends in .png, compared case-INSENSITIVELY, that this run did not plan to write. A DIAGNOSTIC: it gates nothing. The sibling renderers render_performer.py and preview_walk.py derive the same population"),
        "staging": {
            "inherited_from": ("render_performer (E09/E10) for lights, lens and framing; "
                               "the world background is NO LONGER inherited — see alpha"),
            "world_background": list(composite_rgb) + [1.0],
            "key_sun_energy": 3.2, "fill_sun_energy": 1.1,
            "engine": engine, "view_transform": "Standard",
            "sets_in_framing_solve": False,
            "sets_in_render": bool(set_records),
            "consequence": ("on the no-control route this frame is the model's only "
                            "picture of the world, so whatever it shows is what the prompt "
                            "must either keep or replace. What it shows is now a recorded "
                            "choice rather than an inherited studio grey"),
            "residual_not_changed": ("the floor plane is still lit by the two studio suns "
                                     "and reads pale. Only the world void moved under the "
                                     "alpha law; re-lighting the floor would be a second "
                                     "variable this wave did not authorise")},
        "alpha": {
            "law": ("CLAUDE.md, the Director's ruling 2026-08-12 — authored image inputs "
                    "carry alpha, never a baked void"),
            "authored_master": {"path": first["rgba_path"],
                                "sha256": _sha256(first["rgba_path"]),
                                "color_mode": "RGBA", "film_transparent": True},
            "submitted_composite": {
                "path": first["frame_path"], "color_mode": "RGB",
                "backdrop": "plate" if backdrop else "flat colour",
                "film_transparent": bool(backdrop),
                "background_linear_rgb": list(composite_rgb),
                "why": a.composite_why,
                "composited_by": (
                    ("Blender's compositor, alpha-over the plate on a second render of the "
                     "identical scene — the plate linearised on load and re-encoded by the "
                     "Standard view transform, so the performer's edge blends in linear "
                     "light rather than by hand in byte space")
                    if backdrop else
                    ("Blender's own colour management on a second render of the identical "
                     "scene, not by hand in byte space — the sRGB transfer is the "
                     "renderer's, not this tool's"))},
            "flat_counterfactual": {
                "path": first["flat_path"],
                "role": ("the image this route would have submitted with no plate; kept as "
                         "Gate BACKDROP's separation reference and as the COVERAGE source"
                         if backdrop else "this run submitted the flat composite itself")},
            "plate": ({"path": backdrop, "sha256": _sha256(backdrop),
                       "size": [width, height], "why": a.plate_why,
                       "note": ("the world the performer stands in. It changes the void "
                                "only: the lights, the floor geometry, the camera and the "
                                "pose are the flat route's")}
                      if backdrop else None),
            "shadow_layer": first["shadow"],
            "gate_ALPHA": first["gate_alpha"],
            "gate_BACKDROP": first["gate_backdrop"]},
        "camera": {
            "azimuth_deg": AZIMUTH_DEG, "elevation_deg": ELEVATION_DEG,
            "lens_mm": LENS_MM, "sensor_mm": SENSOR_MM,
            "target": list(target), "radius": radius,
            "position": list(framing.camera_position(target, radius,
                                                     ELEVATION_DEG, AZIMUTH_DEG)),
            "height_frac_requested": height_frac,
            "centre_x_frac": CENTRE_X_FRAC, "centre_y_frac": CENTRE_Y_FRAC,
            "solver_achieved": sol["achieved"], "solver_in_frame": sol["in_frame"],
            "framing_cloud": {"n_vertices": len(cloud), "n_solved_against": len(solve_cloud),
                              "cap": FRAMING_CLOUD_CAP,
                              "indices_unioned": list(indices)},
            "shared_across_pair": len(indices) > 1},
        "import_info": info,
        "outputs": {
            "start_frame_rgba": {"path": first["rgba_path"],
                                 "sha256": _sha256(first["rgba_path"]),
                                 "role": "the authored master (RGBA)"},
            "start_frame": {"path": first["frame_path"],
                            "sha256": _sha256(first["frame_path"]),
                            "role": "the submitted composite (RGB)"},
            "start_frame_flat": ({"path": first["flat_path"],
                                  "sha256": _sha256(first["flat_path"]),
                                  "role": "the flat-colour composite, not submitted"}
                                 if backdrop else None),
            "empty_plate": {"path": plate_path, "sha256": _sha256(plate_path)}},
        "measured": {
            "silhouette_extent_px": first["extent"],
            "rendered_subject_bbox_px": first["rendered_bbox"],
            "rendered_bbox_includes_shadow": True,
            "subject_fraction": first["frac"]},
        "gates": {
            "fps_ordering": {"verdict": "PASS", "detail": "import_glb(expected_fps)"},
            "POSE": {"verdict": "PASS", "scene_frame": first["scene_frame"],
                     "action_frame_range": list(span) if span else None,
                     "frame_indices": list(indices)},
            "WHOLE": first["gate_whole"],
            "ALPHA": first["gate_alpha"],
            "BACKDROP": first["gate_backdrop"] or {"verdict": "NOT APPLICABLE",
                                          "detail": "no --plate; the void is a flat colour"},
            "COVERAGE": first["ev_cov"]},
        "elapsed_s": time.time() - started,
    }
    if len(per_frame) > 1:
        last = per_frame[-1]
        provenance["pair"] = {
            "kind": "FLF2V",
            "indices": list(indices),
            "shared": {
                "camera": provenance["camera"],
                "composite_why": a.composite_why,
                "composite_rgb": list(composite_rgb),
                "plate_sha256": _sha256(backdrop) if backdrop else None,
                "plate_why": a.plate_why,
                "engine": engine,
                "sets": [{"glb": r["glb"], "sha256": r["sha256"]} for r in set_records],
            },
            "start": {
                "index": first["index"], "stem": first["stem"],
                "rgba": {"path": first["rgba_path"], "sha256": _sha256(first["rgba_path"])},
                "submitted": {"path": first["frame_path"],
                              "sha256": _sha256(first["frame_path"])},
                "gate_WHOLE": first["gate_whole"]["verdict"],
                "gate_ALPHA": first["gate_alpha"]["verdict"],
                "gate_COVERAGE": first["ev_cov"]["verdict"],
            },
            "end": {
                "index": last["index"], "stem": last["stem"],
                "rgba": {"path": last["rgba_path"], "sha256": _sha256(last["rgba_path"])},
                "submitted": {"path": last["frame_path"],
                              "sha256": _sha256(last["frame_path"])},
                "gate_WHOLE": last["gate_whole"]["verdict"],
                "gate_ALPHA": last["gate_alpha"]["verdict"],
                "gate_COVERAGE": last["ev_cov"]["verdict"],
            },
        }
        provenance["outputs"]["end_frame_rgba"] = {
            "path": last["rgba_path"], "sha256": _sha256(last["rgba_path"]),
            "role": "FLF2V end authored master (RGBA)"}
        provenance["outputs"]["end_frame"] = {
            "path": last["frame_path"], "sha256": _sha256(last["frame_path"]),
            "role": "FLF2V end submitted composite (RGB)"}
        provenance["gates"]["WHOLE_end"] = last["gate_whole"]
        provenance["gates"]["ALPHA_end"] = last["gate_alpha"]
        provenance["gates"]["COVERAGE_end"] = last["ev_cov"]
        provenance["gates"]["BACKDROP_end"] = last["gate_backdrop"] or {
            "verdict": "NOT APPLICABLE", "detail": "no --plate"}

    side = os.path.join(out, "start_frame_provenance.json")
    with open(side, "w", encoding="utf-8") as fh:
        json.dump(provenance, fh, indent=2)

    ok = {
        "frame": first["frame_path"],
        "sha256": provenance["outputs"]["start_frame"]["sha256"][:32],
        "resolution": [width, height], "scene_frame": first["scene_frame"],
        "figure_height_frac": round(first["gate_whole"]["height_frac"], 4),
        "smallest_margin_px": round(min(first["gate_whole"]["margins_px"].values()), 1),
        "subject_fraction": round(first["frac"], 4),
        "gate_WHOLE": first["gate_whole"]["verdict"],
        "gate_COVERAGE": first["ev_cov"]["verdict"],
        "gate_ALPHA": first["gate_alpha"]["verdict"],
        "gate_BACKDROP": (first["gate_backdrop"] or {}).get("verdict", "NOT APPLICABLE"),
        "out_dir_pre_existed": out_dir_pre_existed, "overwrote": already_present,
        "unexpected_files_in_out_dir": strays,
        "sets": len(set_records),
        "frame_indices": list(indices),
        "provenance": side,
    }
    if len(per_frame) > 1:
        ok["end_frame"] = per_frame[-1]["frame_path"]
        ok["pair"] = True
    print("RENDER_START_FRAME_OK " + json.dumps(ok))
    return 0



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
    # WAVE 22, F-897a3329: the VALUE clause, beside the key clause this walk was written
    # for. `json.dumps`'s `default=` applies to values Python cannot encode, never to a
    # float it CAN, and `allow_nan` defaults True -- so a non-finite operand that
    # `armature_core.parts.require_finite` wrote into the evidence (`ev[name] = v`)
    # reached the halt line as the bare token `NaN`. MEASURED end-to-end on `e8263a3`:
    # a sentinel of that shape serialises to `{"evidence": {"max_displacement": NaN}}`;
    # `json.loads(payload)` ACCEPTS it -- which is why every reader in this suite was
    # green -- and `json.loads(payload, parse_constant=<raise>)` REJECTS it naming the
    # constant, as would JS `JSON.parse`, Go `encoding/json` and serde. The halt contract
    # promises "stdout EXACTLY ONE line `<STEM>_HALT <json object>`", and for exactly the
    # refusal family wave 16 added -- the NaN andons -- the object was not JSON.
    #
    # The operand stays READABLE: `repr` gives "nan" / "inf" / "-inf", which is the same
    # text `require_finite`'s own message carries, rather than a null that erases which
    # non-finite value it was. `json.dumps(..., allow_nan=False)` below then cannot raise,
    # so the guard around the sentinel keeps its meaning.
    if isinstance(value, float) and (value != value
                                     or value in (float("inf"), float("-inf"))):
        return repr(value)
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
            "tool": "render_start_frame", "outcome": _outcome, "gate": None,
            "error": type(exc).__name__,
            "message": "the halt line could not be built", "evidence": None}
        _line = json.dumps(_sentinel)
        try:
            traceback.print_exc()
            _detail = getattr(exc, "evidence", None)
            _sentinel = {
                "tool": "render_start_frame", "outcome": _outcome,
                "gate": getattr(exc, "gate", None),
                "error": type(exc).__name__, "message": str(exc),
                "evidence": (_halt_keysafe(_detail)
                             if isinstance(_detail, dict) else None)}
            # `allow_nan=False` (F-897a3329): strict JSON, and it cannot raise here because
            # `_halt_keysafe` above has already replaced every non-finite float with its repr.
            _line = json.dumps(_sentinel, default=str, allow_nan=False)
        except BaseException:                                         # noqa: BLE001
            pass
        finally:
            print("RENDER_START_FRAME_HALT " + _line)
            sys.exit(_code)
