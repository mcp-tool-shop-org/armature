#!/usr/bin/env python
"""measure_cascade_clip — decode a cascade-assembled clip and compare it to its sources.

    <venv-python> tools\\measure_cascade_clip.py --clip=<mp4> --frames=<dir> \\
        --out=<dir> [--expect-frames=81] [--expect-fps=16] [--step=8]

E13's re-arm, Stage 0. S03 measured the flat 81-frame chain failing at execution and the
8-frame chain producing a decodable 16 fps h264 whose only delta from source was yuv420p
chroma subsampling. This is the same decode comparison at 81, on the cascade's output.

The three questions are kept apart on purpose — count, ORDER, fidelity — because a cascade
can get the first and third right while getting the second wrong, and every gate in the
build path would still be green.

**Nothing here judges quality.** Every number is a diagnostic and gates nothing. What
raises is a comparison that could not be made at all — a count mismatch against
`--expect-frames`, and a clip whose own resolution is not the source frames' — because
either makes every per-frame number below it a comparison of different pictures, and
reporting those would be reporting noise with a unit on it.

**The dimensions come off the stream.** `decode` reshapes a raw byte stream at
`stride = width*height*3`; supplying the wrong pair does not fail, it reinterprets, and
`n_decoded_frames` can still land on `--expect-frames`. This tool read the stream's own
width and height and then decoded with the *sources'* — the exact thing
`extract_clip_frames`' docstring warns against. Corrected 2026-09-03.

Compensator (NAMED_COMPENSATORS): writes JSON and PNGs under `outputs/`. Compensator:
delete the directory; owner: the executor session.
"""

import argparse
import glob
import hashlib
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core import clipcompare as CC  # noqa: E402
from armature_core.errors import ArmatureError  # noqa: E402
from encode_control import FFMPEG, decode  # noqa: E402

TOOL_VERSION = "E13.1"


class ClipCountError(ArmatureError):
    """The decoded clip does not carry the number of frames that was submitted."""

    gate = "CLIP_COUNT"


class ClipShapeError(ArmatureError):
    """The clip's own resolution is not the one the decode was about to use.

    `encode_control.decode` reshapes a raw byte stream at `stride = width*height*3`, so
    supplying the wrong dimensions does not fail — it reinterprets. The frames become
    garbage, a trailing partial frame is dropped in silence, and `n_decoded_frames` can
    still land on `--expect-frames`, so the count andon passes and every fidelity and
    order number below it is computed over scrambled pixels. The sibling tool
    `extract_clip_frames` records the rule this class enforces: the dimensions are read
    off the stream, because supplying them is how a decode silently reshapes.
    """

    gate = "CLIP_SHAPE"


class ClipRateError(ArmatureError):
    """The clip's playback rate is not the one the spec declared.

    `--expect-fps` was PARSED (`:112`), written into the record (`:152`) and printed beside
    the value read off the stream (`:196`) -- and nothing compared them. Its sibling
    `--expect-frames` IS gated, with the stated reason that every per-frame comparison
    below a count mismatch compares different pictures; the frame rate is the third
    dimension of the same argument, because the clip's duration -- and therefore every
    timing number read against it (`measure_tracking`'s correlation, the review clip's
    0.5x rate) -- is computed from it. The two adjacent shape checks exist because
    "supplying the dimensions is how a decode silently reshapes"; supplying the rate is
    how a decode silently retimes.

    Also fires when ffprobe's fps token did not parse at all: the line rendered
    `NOT PARSED` beside the expectation and exited 0 with a full record on disk.
    """

    gate = "CLIP_RATE"


#: How far the stream's reported rate may sit from `--expect-fps` and still be the same
#: rate. A container reports a rate ffmpeg derived from a time base, so an exact float
#: equality would refuse a legal 16000/1001 clip; a twentieth of a frame per second is far
#: below any rate a route would legitimately choose instead.
FPS_TOLERANCE = 0.05


def gate_clip_rate(stream, expect_fps, clip, tolerance=FPS_TOLERANCE):
    """ANDON -- the decoded clip plays at the rate the spec declared, or raise.

    Returns the evidence dict when it holds: a gate whose passing verdict is never written
    down is a gate nobody can read.
    """
    read = stream.get("fps")
    ev = {"gate": "CLIP_RATE", "clip": os.path.abspath(clip), "read": read,
          "expected": float(expect_fps), "tolerance": float(tolerance),
          "stream": stream.get("stream", "NOT PARSED")}
    if read is None:
        raise ClipRateError(
            f"{clip}: ffmpeg reported no frame rate for this stream, so the rate every "
            f"timing number below is computed against was never read. `NOT PARSED` beside "
            f"an expectation is not a comparison",
            ev)
    read = float(read)
    ev["read"] = read
    ev["delta"] = abs(read - float(expect_fps))
    if ev["delta"] > tolerance:
        raise ClipRateError(
            f"{clip} decodes at {read} fps and --expect-fps declared "
            f"{float(expect_fps)} (|delta| {ev['delta']:.4f} > {tolerance}); the clip's "
            f"duration, and therefore every timing number read against it, is computed "
            f"on a rate nobody verified",
            ev)
    ev["verdict"] = f"{read} fps, within {tolerance} of the declared {float(expect_fps)}"
    return ev


def ffprobe_stream(path):
    """Container facts, read from ffmpeg's own report rather than assumed."""
    proc = subprocess.run([FFMPEG, "-hide_banner", "-i", path],
                          capture_output=True, text=True)
    text = proc.stderr
    info = {"raw": [l.strip() for l in text.splitlines() if "Stream #" in l
                    or "Duration:" in l]}
    for line in text.splitlines():
        if "Stream #" in line and "Video:" in line:
            info["stream"] = line.strip()
            for part in line.split(","):
                part = part.strip()
                if part.endswith("fps"):
                    info["fps"] = float(part[:-3].strip())
                if "x" in part and part.split()[0].replace("x", "").isdigit():
                    wh = part.split()[0].split("x")
                    if len(wh) == 2:
                        info["width"], info["height"] = int(wh[0]), int(wh[1])
    return info


def _margin(value):
    """`min_margin` for the console line, with a WORD where a bare `0.000` misleads.

    A minimum margin of exactly zero means at least one decoded frame was equidistant from
    two or more sources — the separation the diagonal count is read off does not exist
    there. Printed as `0.000` beside `12/12 on the diagonal` it reads as a clean decode
    with a small number attached (F-0c850c1a).
    """
    if value == 0.0:
        return "0.000 (NONE — at least one frame is equidistant from two sources)"
    return f"{value:.3f}"


def load_sources(frames_dir):
    paths = sorted(glob.glob(os.path.join(frames_dir, "*.png")))
    return paths, [np.asarray(Image.open(p).convert("RGB")) for p in paths]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--clip", required=True)
    ap.add_argument("--frames", required=True, help="the SOURCE frames, in order")
    ap.add_argument("--out", required=True)
    ap.add_argument("--expect-frames", type=int, default=81)
    ap.add_argument("--expect-fps", type=float, default=16.0)
    ap.add_argument("--step", type=int, default=8)
    a = ap.parse_args(argv)

    out = os.path.abspath(a.out)

    paths, sources = load_sources(a.frames)
    h, w, _ = sources[0].shape
    stream = ffprobe_stream(a.clip)

    # ---- ANDON · the decode's dimensions come off the STREAM, never off the sources.
    if stream.get("width") is None or stream.get("height") is None:
        raise ClipShapeError(
            f"{a.clip}: ffmpeg did not report a video stream resolution, so there is "
            f"nothing to decode against. Falling back to the source frames' shape is "
            f"how a decode silently reshapes at the wrong stride",
            {"clip": os.path.abspath(a.clip), "stream": stream,
             "source_shape": [h, w]},
        )
    sw, sh = int(stream["width"]), int(stream["height"])
    if (sh, sw) != (h, w):
        raise ClipShapeError(
            f"{a.clip} is {sw}x{sh} and the source frames are {w}x{h}; a per-frame "
            f"comparison across resolutions compares different pictures, and decoding "
            f"at the sources' stride would reinterpret the bytes rather than fail",
            {"clip": os.path.abspath(a.clip), "stream_shape": [sh, sw],
             "source_shape": [h, w], "frames_dir": os.path.abspath(a.frames)},
        )
    # ---- ANDON . the rate is COMPARED, not printed beside. Before the decode is spent
    #      and before any per-frame number is computed, exactly as the count clause below
    #      states its own reason.
    gate_rate = gate_clip_rate(stream, a.expect_fps, a.clip)
    decoded = decode(a.clip, sw, sh)

    with open(a.clip, "rb") as fh:
        clip_sha = hashlib.sha256(fh.read()).hexdigest()

    # ---- the output directory is created only once every in-tool andon above has fired
    #      (the shape clauses and the rate clause). A refused run that has already made its
    #      directory leaves an empty one behind, which a later reader -- or a re-run into
    #      the same --out -- reads as an attempt that produced nothing rather than one that
    #      was refused. The COUNT clause below deliberately writes its record before it
    #      raises, so the directory must exist by then and not before.
    os.makedirs(out, exist_ok=True)          # scripts create their own output directories

    record = {
        "tool": "measure_cascade_clip", "tool_version": TOOL_VERSION,
        "clip": os.path.abspath(a.clip), "clip_sha256": clip_sha,
        "clip_bytes": os.path.getsize(a.clip),
        "frames_dir": os.path.abspath(a.frames),
        "n_source_frames": len(sources), "n_decoded_frames": len(decoded),
        "expect_frames": a.expect_frames, "expect_fps": a.expect_fps,
        "source_shape": [h, w], "stream": stream, "ffmpeg": FFMPEG,
        "gate_FPS": gate_rate,
    }

    if len(decoded) != a.expect_frames or len(sources) != a.expect_frames:
        record["verdict"] = "COUNT MISMATCH — per-frame numbers not computed"
        with open(os.path.join(out, "cascade_decode_compare.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(record, fh, indent=1)
        raise ClipCountError(
            f"{len(decoded)} decoded frame(s) and {len(sources)} source frame(s) against "
            f"{a.expect_frames} expected. Every per-frame comparison below a count "
            f"mismatch compares different pictures, so none is reported",
            {"decoded": len(decoded), "sources": len(sources),
             "expected": a.expect_frames})

    per_frame = [CC.frame_fidelity(s, d) for s, d in zip(sources, decoded)]
    record["per_frame"] = per_frame
    record["fidelity_summary"] = {
        "n_identical": sum(1 for p in per_frame if p["identical"]),
        "mean_abs_min": min(p["mean_abs"] for p in per_frame),
        "mean_abs_max": max(p["mean_abs"] for p in per_frame),
        "max_abs_max": max(p["max_abs"] for p in per_frame),
    }
    # The middle of THIS clip, not of the default 81. `sources[40]` was a global constant
    # governing a local feature: a legal 17-frame bucket passed the count andon above and
    # then died here with a bare IndexError, after the decode had been spent. The index
    # used is recorded beside the numbers rather than named in the key.
    mid = len(sources) // 2
    record["gradient_split_first_frame"] = {
        "frame_index": 0, **CC.gradient_split(sources[0], decoded[0])}
    record["gradient_split_mid_frame"] = {
        "frame_index": mid, **CC.gradient_split(sources[mid], decoded[mid])}
    record["order"] = CC.order_check(sources, decoded, step=a.step)
    record["source_frame_files"] = [os.path.basename(p) for p in paths]

    with open(os.path.join(out, "cascade_decode_compare.json"), "w",
              encoding="utf-8") as fh:
        json.dump(record, fh, indent=1)

    o = record["order"]
    f = record["fidelity_summary"]
    print(f"decoded frames   {len(decoded)} (expected {a.expect_frames})")
    print(f"stream           {stream.get('stream', 'NOT PARSED')}")
    print(f"fps read         {stream.get('fps', 'NOT PARSED')} (expected {a.expect_fps}) "
          f"-- {gate_rate['verdict']}")
    print(f"identical frames {f['n_identical']} of {len(per_frame)}")
    print(f"mean abs         {f['mean_abs_min']:.4f} .. {f['mean_abs_max']:.4f}  "
          f"max {f['max_abs_max']:.0f}")
    print(f"gradient split   f0 top {record['gradient_split_first_frame']['mean_err_top_gradient']:.2f} "
          f"vs flat {record['gradient_split_first_frame']['mean_err_flat']:.2f}   "
          f"(mid frame {record['gradient_split_mid_frame']['frame_index']})")
    # The console line is what a session quotes into a report, so it carries the tie facts
    # the record has carried since wave 12 (F-0c850c1a). Measured on this branch on the
    # walk shape `clipcompare.order_check`'s own docstring names — 8 distinct frames then a
    # 4-frame hold, compared against an exact copy — the line read
    # `order  12/12 on the diagonal, 0 displaced, min margin 0.000` on a clip where 5 of 12
    # frames were AMBIGUOUS and the check could not distinguish them; a real group
    # displacement occurring inside a tie set would have printed the same sentence.
    # `min_margin 0.000` was the only hint and it was not labelled as one.
    print(f"order            {o['n_on_diagonal']}/{o['n']} on the diagonal, "
          f"{o['n_displaced']} displaced, {o['n_tied']} tied"
          + (f" in {len(o['tie_groups'])} group(s) {o['tie_groups'][:4]}"
             if o.get("tie_groups") else "")
          + f", min margin {_margin(o['min_margin'])}")
    print(f"MEASURE_CASCADE_OK {out}")
    return record


if __name__ == "__main__":
    main()
