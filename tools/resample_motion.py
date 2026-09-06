#!/usr/bin/env python
"""resample_motion — the same dance, more in-betweens.

    python tools\\resample_motion.py --motion=<lifted_ema.motion.json> --frames=81
           --out=<dir> [--fps-src=16]

E10's commission. It resamples a motion record from its native sample count to another
over the **identical duration** — slerp on every bone's local rotation along the shortest
arc, linear on the root translation, endpoints exact — so a video model can be driven at a
higher frame count without the performance slowing down or the poses being invented.

**No Blender, no numpy.** Everything decidable by arithmetic is decided in
`armature_core.resample`, whose tests check the in-betweens against closed-form answers
rather than against a render. This shell reads a file, runs the gates, writes a file.

The other reason this exists is the movement library: a motion record that can be resampled
to any legal frame count is a library-ready asset, where one baked at 65 frames is a clip
that fits one generator setting.

--------------------------------------------------------------------------------
The gates — all raise, in-process, before the output file exists

* **RESAMPLE/rotation** — every stored 3x3 in the SOURCE really is a rotation. A matrix
  that is merely near one converts to a quaternion that is silently wrong and lands a body
  slightly sheared on every in-between frame, with every count still right.
* **RESAMPLE/monotonic** — the resampled timeline runs strictly forwards and spans the
  source's first and last sample exactly. Nothing else in the chain looks at time.
* **RESAMPLE/endpoints** — the first and last output frames are the source's own, value
  for value. An off-by-one in the index map shifts the whole performance by a fraction of
  a frame; the clip plays, the count is right, and the dance starts late.
* **SOLVE/validate** — `lift_solve.validate_motion_record` on the OUTPUT: contiguous frame
  numbering from 0 and every registered bone present on every frame. A gap is filled
  downstream by the neighbouring pose and reads as detector noise.

Diagnostics that gate nothing: per-bone step angles before and after. They are reported as
a distribution rather than a mean, because slerp densifies the path BETWEEN the source's
samples and leaves the turns AT them exactly where they were — a single number hides
precisely the thing being measured.

Compensator (NAMED_COMPENSATORS): the only world-touching act is writing JSON under
`outputs/`. Compensator: delete the directory; owner: the executor session. The input is
opened read-only.

Prints `RESAMPLE_MOTION_OK`.
Halt contract: exit 0 on success, 2 on a deliberate refusal (one <TOOL>_HALT JSON line; evidence.clause is the branch word), 1 on a crash. See README §"Reading a halt" and armature_core.parts.run_tool_main.
"""

import argparse
import hashlib
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from encode_control import runtime_provenance  # noqa: E402

from armature_core import lift_solve, resample  # noqa: E402
from armature_core.errors import ArmatureError, GateFailure  # noqa: E402


TOOL_VERSION = "E10.1"

#: Bones whose step angles are reported by name. The limbs the Director's eye reads chop
#: on — arms mid-swing — plus the root chain, so a report can say WHERE the driving signal
#: changed rather than quoting one number for the whole body.
DIAGNOSTIC_BONES = ("hips", "chest", "head",
                    "shoulder.L", "elbow.L", "wrist.L",
                    "shoulder.R", "elbow.R", "wrist.R",
                    "hip.L", "knee.L", "ankle.L", "hip.R", "knee.R", "ankle.R")


#: The smallest destination sample count that describes a timeline. `positions(n_src,
#: n_dst)` and `sample_interval_ratio` both divide by `n_dst - 1`.
MIN_DST_FRAMES = 2



HALT_EPILOG = 'Halt contract: exit 0 on success, 2 on a deliberate refusal (one <TOOL>_HALT JSON line; evidence.clause is the branch word), 1 on a crash. See README §"Reading a halt".'

class ResampleArgError(ArmatureError):
    """A flag this tool was given is not a value it can resample with.

    It defines no constructor. The wave-14 note here read "carries its own
    `(message, evidence)` constructor: `ArmatureError` has none" — measured false on this
    tree, where `armature_core/errors.py::ArmatureError.__init__` defines exactly that shape and stores the
    dict as passed. What the local copy added was `evidence or {}`, which normalises a bare
    refusal's null receipt into an empty dict and so contradicts the base's own rule
    (`errors.py:27-33`). Deleted wave 16; the two raises below reach the base unchanged.
    """


def parse_args(argv=None):
    ap = argparse.ArgumentParser(
        description="the same dance, more in-betweens: resample a motion record to a new "
                    "sample count without changing the performance's duration",
        epilog=HALT_EPILOG)
    ap.add_argument("--motion", required=True,
                    help="a motion record: {frames: [{frame, local: {bone: 3x3}, root}]}")
    ap.add_argument("--frames", type=int, required=True,
                    help="destination sample count (argparse eats leading minus signs, so "
                         "pass flags as --flag=value)")
    ap.add_argument("--out", required=True,
                    help="directory for the resampled motion record")
    ap.add_argument("--fps-src", type=float, default=16.0,
                    help="the source record's sampling rate; used only to report the "
                         "playback rate that preserves the performance's duration")
    ap.add_argument("--name", default=None, help="output basename (default: derived)")
    return ap.parse_args(argv)


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main(argv=None):
    started = time.time()
    a = parse_args(argv)
    out_dir = os.path.abspath(a.out)

    # ---- ANDON, before anything is read or written: the destination sample count is a
    #      count of samples. `--frames=1` reached `resample.positions(n_src, 1)` and
    #      `sample_interval_ratio = (n_src - 1) / (n_dst - 1)`, both of which divide by
    #      `n_dst - 1`, and died with a bare ZeroDivisionError naming neither the flag nor
    #      the value. A resampled timeline needs two endpoints to span anything at all.
    if a.frames < MIN_DST_FRAMES:
        raise ResampleArgError(
            f"--frames={a.frames} is not a timeline; this tool resamples a path between "
            f"its endpoints, so the destination needs at least {MIN_DST_FRAMES} samples "
            f"(the index-space rule divides by n_dst - 1)",
            {"gate": "ARGS", "andon": "ResampleArgError",
             "clause": "destination_frame_count_below_two",
             "frames": a.frames, "minimum": MIN_DST_FRAMES})

    # ---- ANDON, the same block, the OTHER divisor (F-981fe49d, wave 16). `--frames` was
    #      gated in wave 14 because `positions` and `sample_interval_ratio` divide by
    #      `n_dst - 1`; `--fps-src` divides three of the same block's derived quantities
    #      and was left open. Measured on the base tree, on a 4-frame record that passes
    #      every gate: `--fps-src=0` raised a bare `ZeroDivisionError` at
    #      `(n_src - 1) / a.fps_src` — untyped, so the `__main__` handler classified it
    #      exit 1 ("an unhandled error") rather than the exit 2 a deliberate refusal earns,
    #      and the message named neither the flag nor the value. `--fps-src=-16` ran to
    #      COMPLETION, printed `RESAMPLE_MOTION_OK` and wrote the record with
    #      `fps_dst_true_tempo: -37.333`, `span_s_first_to_last_sample: -0.1875` and
    #      `clip_s_src_frames_over_fps: -0.25`; `--fps-src=nan` wrote NaN into all three.
    #      `fps_dst_true_tempo` exists so a later tool or operator can pick the generator's
    #      frame rate from it, so a negative or NaN value there is read out of a file the
    #      record says reproduced cleanly.
    #
    #      The clause is `> 0` AND finite, in that order, because the two directions are
    #      different: `nan > 0` is False and is caught here, while `inf > 0` is True and
    #      would pass a positivity test while making every derived duration zero.
    if not math.isfinite(a.fps_src) or a.fps_src <= 0:
        raise ResampleArgError(
            f"--fps-src={a.fps_src} is not a sampling rate; the source's rate divides "
            f"three quantities in the record this tool writes "
            f"(fps_dst_true_tempo, span_s_first_to_last_sample, "
            f"clip_s_src_frames_over_fps), and a rate that is zero, negative or non-finite "
            f"puts a value no reader can use into the field whose whole purpose is to pick "
            f"the generator's frame rate",
            {"gate": "ARGS", "andon": "ResampleArgError",
             "clause": ("source_rate_not_finite" if not math.isfinite(a.fps_src)
                        else "source_rate_not_positive"),
             "fps_src": a.fps_src, "minimum_exclusive": 0.0})

    # ---- ANDON, the same block, the flag that names the OUTPUT (F-db1de39d, wave 18).
    #      `--name` is pasted into `os.path.join(out_dir, name + ".motion.json")` below,
    #      and it was checked for nothing. Third measured instance of one family in this
    #      domain; `pack_pose_pack --name` is the second and is fixed in the same wave,
    #      `make_review_clip --run` is the first and is a DEFERRED Stage B item. The
    #      refusal sits HERE, above `os.makedirs` and above the record read, because a
    #      refused run must leave no directory behind: that is the ordering rule the
    #      `--frames` andon above was moved for (F-6a18f6d5).
    #
    #      The guard is TRUTHINESS, not `is not None`, because that is exactly the
    #      population the paste happens for: the write site reads `a.name or (derived)`,
    #      so a falsy `--name` never reaches the join. Measured on the base tree,
    #      `--name=` (empty) wrote the derived `motion.6.motion.json`; refusing it here
    #      would refuse an input this tool accepts today, and a bound belongs where the
    #      value is READ.
    if a.name:
        # WAVE 22, SEAM 1: the ONE home for this check, adopted BY IMPORT (the two
        # byte-identical copies this domain held are deleted). The import is at the
        # CALL SITE rather than at module scope for one reason, stated so it is not
        # read as a cycle break: the helper lands on core-solvers' branch in the same
        # parallel wave, and a module-scope import makes this file uncollectable on
        # any tree where that branch has not merged yet. Same object either way.
        from armature_core.parts import single_path_segment

        single_path_segment(a.name, "--name", ResampleArgError,
                            extra={"tool": "resample_motion",
                                   "out": out_dir, "motion": a.motion})

    with open(a.motion, encoding="utf-8") as fh:
        src = json.load(fh)
    frames = src["frames"]
    n_src, n_dst = len(frames), a.frames

    gate_in = lift_solve.validate_motion_record(frames)
    gate_time = resample.monotonic(n_src, n_dst)
    out_frames = resample.resample_frames(frames, n_dst)
    gate_ends = resample.endpoints_match(frames, out_frames)
    gate_out = lift_solve.validate_motion_record(out_frames)

    present = [b for b in DIAGNOSTIC_BONES if b in frames[0]["local"]]
    fps_dst = resample.fps_for(a.fps_src, n_src, n_dst)

    payload = {
        "tool": "resample_motion",
        "tool_version": TOOL_VERSION,
        "module_version": resample.TOOL_VERSION,
        "source": {"path": os.path.abspath(a.motion), "sha256": _sha256(a.motion),
                   "tool": src.get("tool"), "tool_version": src.get("tool_version"),
                   "clip_source": src.get("source"),
                   "ema_alpha": src.get("ema_alpha"),
                   "note": ("the smoothing configuration is CARRIED, not re-run: this tool "
                            "densifies the path the record already describes and changes "
                            "nothing about how that record was smoothed")},
        "resample": {
            "n_src": n_src, "n_dst": n_dst,
            "rule": ("index-space: destination sample j reads source position "
                     "j * (n_src - 1) / (n_dst - 1); rotations by shortest-arc slerp per "
                     "bone between adjacent keys, root translation linear, endpoints "
                     "returned verbatim"),
            "source_positions_first8": resample.positions(n_src, n_dst)[:8],
            "sample_interval_ratio": (n_src - 1) / (n_dst - 1),
            "fps_src": a.fps_src,
            "fps_dst_true_tempo": fps_dst,
            "span_s_first_to_last_sample": (n_src - 1) / a.fps_src,
            "clip_s_src_frames_over_fps": n_src / a.fps_src,
            "clip_s_dst_frames_over_fps": n_dst / fps_dst,
            "tempo_note": ("`fps_dst_true_tempo` is the rate at which the FIRST-TO-LAST "
                           "sample span is unchanged, which is what endpoint-exact "
                           "resampling preserves. Quoting frames/fps instead gives a clip "
                           "length differing by less than one frame; both are reported so "
                           "no reader has to guess which convention a tempo claim used"),
        },
        "gates": {
            "SOLVE_input": gate_in, "RESAMPLE_monotonic": gate_time,
            "RESAMPLE_endpoints": gate_ends, "SOLVE_output": gate_out,
        },
        "diagnostics": {
            "step_angles_src_deg": resample.step_angles(frames, present),
            "step_angles_dst_deg": resample.step_angles(out_frames, present),
            "note": ("per-bone geodesic angle between consecutive frames. A DIAGNOSTIC; it "
                     "gates nothing. On a smooth passage the median step scales with the "
                     "sample interval; at a turn in the source path it does not, because "
                     "slerp densifies the path between the source's samples and leaves the "
                     "turns at them exactly where they were"),
        },
        "frames": out_frames,
        "elapsed_s": time.time() - started,
    }

    name = a.name or (os.path.splitext(os.path.basename(a.motion))[0] + f".{n_dst}")
    path = os.path.join(out_dir, name + ".motion.json")
    # ---- the output directory is created BELOW every andon above it (F-6a18f6d5): the
    #      `--frames` bound, `lift_solve.validate_motion_record(frames)`,
    #      `resample.monotonic`, `resample.endpoints_match` and
    #      `validate_motion_record(out_frames)`. It used to sit at the top of `main`, so a
    #      record whose frames carry no `local` rotations raised SolveGate [SOLVE] and left
    #      `--out` on disk, existing and empty — which a later reader, or a re-run into the
    #      same `--out`, reads as an attempt that produced nothing rather than one that was
    #      refused. Nothing irreversible is at stake; the ordering rule is.
    os.makedirs(out_dir, exist_ok=True)      # scripts create their own output directories
    with open(path, "w", encoding="utf-8") as fh:
        payload.update(runtime_provenance())
        json.dump(payload, fh, indent=2)

    med = {b: {"src": payload["diagnostics"]["step_angles_src_deg"][b]["median_deg"],
               "dst": payload["diagnostics"]["step_angles_dst_deg"][b]["median_deg"]}
           for b in present[:4]}
    print("RESAMPLE_MOTION_OK " + json.dumps({
        "out": path, "sha256": _sha256(path)[:32],
        "n_src": n_src, "n_dst": n_dst,
        "fps_src": a.fps_src, "fps_dst_true_tempo": fps_dst,
        "endpoints": gate_ends["verdict"], "timeline": gate_time["verdict"],
        "median_step_deg_sample": med}))
    return 0


if __name__ == "__main__":
    # WAVE 22, SEAM 1: the ONE `__main__` halt handler, adopted BY IMPORT from
    # `armature_core.parts` (core-solvers' file, posted to the wave-22 seams inbox). Never
    # copied — the whole point of the seam is that this block is one function with one home.
    from armature_core.parts import run_tool_main  # noqa: E402

    run_tool_main(main, "RESAMPLE_MOTION")
