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

**Nothing here judges quality.** Every number is a diagnostic and gates nothing. The one
thing that raises is a count mismatch against `--expect-frames`, because a clip with the
wrong number of frames makes every per-frame comparison below it a comparison of different
pictures, and reporting those numbers would be reporting noise with a unit on it.

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
    os.makedirs(out, exist_ok=True)          # scripts create their own output directories

    paths, sources = load_sources(a.frames)
    h, w, _ = sources[0].shape
    stream = ffprobe_stream(a.clip)
    decoded = decode(a.clip, w, h)

    with open(a.clip, "rb") as fh:
        clip_sha = hashlib.sha256(fh.read()).hexdigest()

    record = {
        "tool": "measure_cascade_clip", "tool_version": TOOL_VERSION,
        "clip": os.path.abspath(a.clip), "clip_sha256": clip_sha,
        "clip_bytes": os.path.getsize(a.clip),
        "frames_dir": os.path.abspath(a.frames),
        "n_source_frames": len(sources), "n_decoded_frames": len(decoded),
        "expect_frames": a.expect_frames, "expect_fps": a.expect_fps,
        "source_shape": [h, w], "stream": stream, "ffmpeg": FFMPEG,
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
    record["gradient_split_frame0"] = CC.gradient_split(sources[0], decoded[0])
    record["gradient_split_frame40"] = CC.gradient_split(sources[40], decoded[40])
    record["order"] = CC.order_check(sources, decoded, step=a.step)
    record["source_frame_files"] = [os.path.basename(p) for p in paths]

    with open(os.path.join(out, "cascade_decode_compare.json"), "w",
              encoding="utf-8") as fh:
        json.dump(record, fh, indent=1)

    o = record["order"]
    f = record["fidelity_summary"]
    print(f"decoded frames   {len(decoded)} (expected {a.expect_frames})")
    print(f"stream           {stream.get('stream', 'NOT PARSED')}")
    print(f"fps read         {stream.get('fps', 'NOT PARSED')} (expected {a.expect_fps})")
    print(f"identical frames {f['n_identical']} of {len(per_frame)}")
    print(f"mean abs         {f['mean_abs_min']:.4f} .. {f['mean_abs_max']:.4f}  "
          f"max {f['max_abs_max']:.0f}")
    print(f"gradient split   f0 top {record['gradient_split_frame0']['mean_err_top_gradient']:.2f} "
          f"vs flat {record['gradient_split_frame0']['mean_err_flat']:.2f}")
    print(f"order            {o['n_on_diagonal']}/{o['n']} on the diagonal, "
          f"{o['n_displaced']} displaced, min margin {o['min_margin']:.3f}")
    print(f"MEASURE_CASCADE_OK {out}")
    return record


if __name__ == "__main__":
    main()
