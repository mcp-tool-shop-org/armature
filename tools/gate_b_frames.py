#!/usr/bin/env python
"""gate_b_frames — did the driving signal reach the model exactly as it was drawn?

    python tools\\gate_b_frames.py --sticks=<local stick dir> --batchprobe=<server dir>
           --out=<evidence.json> [--painted=<lossless dir>]

Gate B, armed after the run instead of before it, because the thing it measures only
exists once the server has decoded the pack. E08 ran this inline and banked the verdict;
E10 commissions it so the check is reproducible and its tests ride the code.

**What it actually proves, and what it cannot.** The pack bridge sends 81 stick frames as
ONE multi-frame image through a single `LoadImage`, and `pack_pose_pack` gates the encode
locally with Gate R. That leaves the other half open: whether the SERVER decodes the pack
the same way. So the graph hangs a `SaveImage` directly off the `LoadImage` output, and
this compares those returned frames against the local ones **pixel for pixel, all of
them** — not a sample. A pack that lost, reordered, resampled or recoloured a frame
arrives as a perfectly well-formed run whose driving signal is not the one the report
quotes.

Two andons, in this order:

* **Gate B (count)** — `gates.gate_b_batching`. `WanAnimateToVideo` pads a short pose video
  by REPEATING its last frame and truncates a long one, both silently, so a miscount is a
  performance that freezes or ends early with every other check green.
* **Gate B (pixels)** — `gates.gate_r_round_trip`, per channel. A scalar mean over these
  frames would sit near zero whether or not a channel was destroyed; the sticks ARE the
  convention, and a red/blue swap is the named silent failure of this chain.

`--painted` is a diagnostic and gates nothing: it counts how many returned frames are
distinct, which is what a driving signal that arrived and did nothing would show.

Compensator (NAMED_COMPENSATORS): writes one JSON under `outputs/`. Compensator: delete the
file; owner: the executor session. Every frame directory is opened read-only.

Prints `GATE_B_OK`, or raises.
"""

import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

from armature_core import gates  # noqa: E402
from armature_core.errors import ArmatureError, GateFailure  # noqa: E402

TOOL_VERSION = "E10.1"


def frame_paths(directory):
    """The numbered frames of a directory, in index order. Order IS the signal here.

    **Numbered, not merely `*.png`** — and that is a correction, not a nicety. The stick
    renderer writes a `strip_every8.png` contact sheet beside its `NNNNN.png` frames, so a
    naive glob counts 82 frames where 81 were drawn, and the count andon fires with a
    message about batching that has nothing to do with what went wrong. Caught by this
    gate on its own first run, 2026-08-12, which is the cheap place to catch it.
    """
    if not os.path.isdir(directory):
        raise ArmatureError(f"{directory} is not a directory of frames")
    names = [n for n in os.listdir(directory)
             if n.lower().endswith(".png") and os.path.splitext(n)[0].isdigit()]
    if not names:
        raise ArmatureError(
            f"{directory} carries no NNNNN.png frames; a comparison over zero frames "
            f"proves nothing and would report a passing gate")
    return [os.path.join(directory, n)
            for n in sorted(names, key=lambda n: int(os.path.splitext(n)[0]))]


def load_rgb(path):
    with Image.open(path) as im:
        return np.asarray(im.convert("RGB"), dtype=np.uint8)


def distinct_count(paths):
    """How many frames are pixel-distinct. A DIAGNOSTIC; it gates nothing."""
    seen = set()
    for p in paths:
        seen.add(hashlib.sha256(load_rgb(p).tobytes()).hexdigest())
    return len(seen)


def mean_abs_frame_deltas(paths):
    """Mean |frame[i+1] - frame[i]| over the sequence, 0-255. A DIAGNOSTIC."""
    out = []
    prev = load_rgb(paths[0]).astype(np.int16)
    for p in paths[1:]:
        cur = load_rgb(p).astype(np.int16)
        out.append(float(np.abs(cur - prev).mean()))
        prev = cur
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sticks", required=True, help="the local stick frames as drawn")
    ap.add_argument("--batchprobe", required=True,
                    help="the frames the server returned off the pose LoadImage")
    ap.add_argument("--painted", default=None, help="the lossless output frames; diagnostic")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)

    src_paths = frame_paths(a.sticks)
    got_paths = frame_paths(a.batchprobe)

    gate_count = gates.gate_b_batching(len(src_paths), len(got_paths))
    src = [load_rgb(p) for p in src_paths]
    got = [load_rgb(p) for p in got_paths]
    gate_px = gates.gate_r_round_trip(
        src, got,
        source_label=f"{len(src)} local stick frames",
        decoded_label=f"{len(got)} server batchprobe frames")

    record = {
        "tool": "gate_b_frames", "tool_version": TOOL_VERSION,
        "sticks": {"dir": os.path.abspath(a.sticks), "n": len(src_paths)},
        "batchprobe": {"dir": os.path.abspath(a.batchprobe), "n": len(got_paths)},
        "gate_B_count": gate_count,
        "gate_B_pixels": gate_px,
        "note": ("every frame compared, not a sample: the pack bridge's local Gate R proves "
                 "the encode, and only this proves the server's decode"),
    }
    if a.painted:
        out_paths = frame_paths(a.painted)
        deltas = mean_abs_frame_deltas(out_paths) if len(out_paths) > 1 else []
        record["painted"] = {
            "dir": os.path.abspath(a.painted), "n": len(out_paths),
            "distinct_frames": distinct_count(out_paths),
            "mean_abs_frame_delta_0_255": (
                {"min": min(deltas), "median": sorted(deltas)[len(deltas) // 2],
                 "max": max(deltas)} if deltas else None),
            "status": "DIAGNOSTIC — gates nothing",
        }

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2)

    print("GATE_B_OK " + json.dumps({
        "out": os.path.abspath(a.out),
        "count": gate_count["verdict"], "pixels": gate_px["verdict"],
        "painted": record.get("painted", {}).get("distinct_frames")}))
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
        print("GATE_B_HALT " + json.dumps({
            "error": type(exc).__name__, "message": str(exc),
            "evidence": detail if isinstance(detail, dict) else None}, default=str))
        sys.exit(2 if isinstance(exc, (GateFailure, ArmatureError)) else 1)
