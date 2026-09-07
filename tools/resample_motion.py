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
        description="the same dance, densified or decimated: --mode=densify (default) "
                    "resamples to more in-betweens; --mode=decimate keeps a geodesic "
                    "budget of keyframes with endpoints exact (F-2e3c2374)",
        epilog=HALT_EPILOG)
    ap.add_argument("--mode", default="densify", choices=("densify", "decimate"),
                    help="densify (default): more samples over the same duration. "
                         "decimate: keep --budget keyframes (endpoints always kept) "
                         "(F-2e3c2374)")
    ap.add_argument("--motion", required=True,
                    help="a motion record: {frames: [{frame, local: {bone: 3x3}, root}]}")
    ap.add_argument("--frames", type=int, default=None,
                    help="destination sample count for --mode=densify (required there)")
    ap.add_argument("--budget", type=int, default=None,
                    help="kept keyframe count for --mode=decimate (including endpoints); "
                         "required when decimating")
    ap.add_argument("--out", required=True,
                    help="directory for the resampled motion record")
    ap.add_argument("--fps-src", type=float, default=16.0,
                    help="the source record's sampling rate; used only to report the "
                         "playback rate that preserves the performance's duration")
    ap.add_argument("--name", default=None, help="output basename (default: derived)")
    return ap.parse_args(argv)


def decimate_indices(frames, budget):
    """Keep endpoints + highest per-step geodesic cost interiors (F-2e3c2374).

    Reuses armature_core.resample.geodesic_deg over DIAGNOSTIC_BONES present in the
    record. Endpoints are always kept; budget < 2 is refused by the caller.
    """
    n = len(frames)
    if budget >= n:
        return list(range(n))
    present = [b for b in DIAGNOSTIC_BONES if b in (frames[0].get("local") or {})]
    if not present:
        present = list((frames[0].get("local") or {}).keys())[:8]
    costs = []
    for i in range(n - 1):
        cost = 0.0
        for b in present:
            a = frames[i]["local"].get(b)
            c = frames[i + 1]["local"].get(b)
            if a is None or c is None:
                continue
            cost += resample.geodesic_deg(
                tuple(tuple(float(v) for v in row) for row in a),
                tuple(tuple(float(v) for v in row) for row in c))
        # Candidate interior = right endpoint of the step.
        costs.append((cost, i + 1))
    keep = {0, n - 1}
    for _cost, idx in sorted(costs, key=lambda t: t[0], reverse=True):
        if len(keep) >= budget:
            break
        if 0 < idx < n - 1:
            keep.add(idx)
    if len(keep) < budget:
        for i in range(1, n - 1):
            if len(keep) >= budget:
                break
            keep.add(i)
    return sorted(keep)


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
    mode = a.mode

    if mode == "densify":
        if a.frames is None:
            raise ResampleArgError(
                "--frames is required for --mode=densify",
                {"gate": "ARGS", "andon": "ResampleArgError",
                 "clause": "densify_requires_frames", "mode": mode})
        if a.budget is not None:
            raise ResampleArgError(
                "--budget belongs to --mode=decimate",
                {"gate": "ARGS", "andon": "ResampleArgError",
                 "clause": "budget_requires_decimate", "budget": a.budget})
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
    else:
        if a.budget is None:
            raise ResampleArgError(
                "--budget is required for --mode=decimate",
                {"gate": "ARGS", "andon": "ResampleArgError",
                 "clause": "decimate_requires_budget", "mode": mode})
        if a.frames is not None:
            raise ResampleArgError(
                "--frames belongs to --mode=densify; decimate takes --budget=",
                {"gate": "ARGS", "andon": "ResampleArgError",
                 "clause": "frames_requires_densify", "frames": a.frames})
        if a.budget < MIN_DST_FRAMES:
            raise ResampleArgError(
                f"--budget={a.budget} is not a timeline; decimate keeps endpoints so the "
                f"budget needs at least {MIN_DST_FRAMES}",
                {"gate": "ARGS", "andon": "ResampleArgError",
                 "clause": "decimate_budget_below_two",
                 "budget": a.budget, "minimum": MIN_DST_FRAMES})

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

    if a.name:
        from armature_core.parts import single_path_segment

        single_path_segment(a.name, "--name", ResampleArgError,
                            extra={"tool": "resample_motion",
                                   "out": out_dir, "motion": a.motion})

    with open(a.motion, encoding="utf-8") as fh:
        src = json.load(fh)
    frames = src["frames"]
    n_src = len(frames)
    gate_in = lift_solve.validate_motion_record(frames)
    kept_indices = None

    if mode == "decimate":
        kept_indices = decimate_indices(frames, a.budget)
        out_frames = []
        for j, src_i in enumerate(kept_indices):
            fr = frames[src_i]
            out_frames.append({
                "frame": j,
                "local": {b: [list(r) for r in fr["local"][b]] for b in fr["local"]},
                "root": list(fr["root"]),
            })
        n_dst = len(out_frames)
        # Endpoint-match against the SOURCE endpoints (indices 0 and n_src-1), which
        # decimate_indices always keeps as out_frames[0] and out_frames[-1].
        gate_ends = resample.endpoints_match(
            [frames[0], frames[-1]],
            [out_frames[0], out_frames[-1]])
        gate_time = {
            "verdict": f"decimate kept {n_dst} of {n_src} (budget={a.budget})",
            "gate": "RESAMPLE", "mode": "decimate",
            "kept_indices": kept_indices, "budget": a.budget,
        }
        fps_dst = a.fps_src  # same sample times as kept source frames; tempo unchanged
        resample_block = {
            "mode": "decimate",
            "n_src": n_src, "n_dst": n_dst,
            "budget": a.budget,
            "kept_indices": kept_indices,
            "rule": ("geodesic-budget decimate: endpoints always kept; interiors chosen "
                     "by largest per-step geodesic over DIAGNOSTIC_BONES; frame indices "
                     "renumbered 0..n_dst-1; endpoint poses match source endpoints"),
            "fps_src": a.fps_src,
            "fps_dst_true_tempo": fps_dst,
            "span_s_first_to_last_sample": (n_src - 1) / a.fps_src,
            "clip_s_src_frames_over_fps": n_src / a.fps_src,
            "clip_s_dst_frames_over_fps": n_dst / fps_dst,
        }
    else:
        n_dst = a.frames
        gate_time = resample.monotonic(n_src, n_dst)
        out_frames = resample.resample_frames(frames, n_dst)
        gate_ends = resample.endpoints_match(frames, out_frames)
        fps_dst = resample.fps_for(a.fps_src, n_src, n_dst)
        resample_block = {
            "mode": "densify",
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
        }

    gate_out = lift_solve.validate_motion_record(out_frames)
    present = [b for b in DIAGNOSTIC_BONES if b in frames[0]["local"]]

    payload = {
        "tool": "resample_motion",
        "tool_version": TOOL_VERSION,
        "module_version": resample.TOOL_VERSION,
        "mode": mode,
        "source": {"path": os.path.abspath(a.motion), "sha256": _sha256(a.motion),
                   "tool": src.get("tool"), "tool_version": src.get("tool_version"),
                   "clip_source": src.get("source"),
                   "ema_alpha": src.get("ema_alpha"),
                   "note": ("the smoothing configuration is CARRIED, not re-run: this tool "
                            "densifies or decimates the path the record already describes "
                            "and changes nothing about how that record was smoothed")},
        "resample": resample_block,
        "gates": {
            "SOLVE_input": gate_in, "RESAMPLE_monotonic": gate_time,
            "RESAMPLE_endpoints": gate_ends, "SOLVE_output": gate_out,
        },
        "diagnostics": {
            "step_angles_src_deg": resample.step_angles(frames, present),
            "step_angles_dst_deg": resample.step_angles(out_frames, present),
            "note": ("per-bone geodesic angle between consecutive frames. A DIAGNOSTIC; it "
                     "gates nothing."),
        },
        "frames": out_frames,
        "elapsed_s": time.time() - started,
    }

    name = a.name or (os.path.splitext(os.path.basename(a.motion))[0]
                      + (f".decimate{a.budget}" if mode == "decimate" else f".{n_dst}"))
    path = os.path.join(out_dir, name + ".motion.json")
    os.makedirs(out_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        payload.update(runtime_provenance())
        json.dump(payload, fh, indent=2)

    med = {b: {"src": payload["diagnostics"]["step_angles_src_deg"][b]["median_deg"],
               "dst": payload["diagnostics"]["step_angles_dst_deg"][b]["median_deg"]}
           for b in present[:4]}
    print("RESAMPLE_MOTION_OK " + json.dumps({
        "out": path, "sha256": _sha256(path)[:32],
        "mode": mode, "n_src": n_src, "n_dst": n_dst,
        "budget": a.budget, "kept_indices": kept_indices,
        "fps_src": a.fps_src, "fps_dst_true_tempo": fps_dst,
        "endpoints": gate_ends.get("verdict"), "timeline": gate_time.get("verdict"),
        "median_step_deg_sample": med}))
    return 0


if __name__ == "__main__":
    # WAVE 22, SEAM 1: the ONE `__main__` halt handler, adopted BY IMPORT from
    # `armature_core.parts` (core-solvers' file, posted to the wave-22 seams inbox). Never
    # copied — the whole point of the seam is that this block is one function with one home.
    from armature_core.parts import run_tool_main  # noqa: E402

    run_tool_main(main, "RESAMPLE_MOTION")
