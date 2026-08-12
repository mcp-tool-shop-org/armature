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
"""

import argparse
import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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


def parse_args(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--motion", required=True,
                    help="a motion record: {frames: [{frame, local: {bone: 3x3}, root}]}")
    ap.add_argument("--frames", type=int, required=True,
                    help="destination sample count (argparse eats leading minus signs, so "
                         "pass flags as --flag=value)")
    ap.add_argument("--out", required=True)
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
    os.makedirs(out_dir, exist_ok=True)      # scripts create their own output directories

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
    with open(path, "w", encoding="utf-8") as fh:
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
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 - the halt must be legible and loud
        import traceback
        traceback.print_exc()
        detail = getattr(exc, "evidence", None)
        print("RESAMPLE_MOTION_HALT " + json.dumps({
            "error": type(exc).__name__, "message": str(exc),
            "evidence": detail if isinstance(detail, dict) else None}, default=str))
        sys.exit(2 if isinstance(exc, (GateFailure, ArmatureError)) else 1)
