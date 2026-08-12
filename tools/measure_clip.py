#!/usr/bin/env python
r"""measure_clip — the numbers a generated clip can be quoted by.

    python tools\measure_clip.py --frames=<lossless dir> --out=<measurements.json>
           [--label=E11] [--compare=<another lossless dir> --compare-label=E08]
           [--horizon-band=0,240]

Runs `armature_core.clipstats` over a directory of `NNNNN.png` frames — the lossless tap
off `VAEDecode`, never a re-encoded video — and writes one JSON. It measures; it judges
nothing, and no number here gates anything.

`--compare` runs the identical measurements over a second clip and puts the two side by
side in the record, so a cross-experiment number is computed by one instrument on both
arms rather than quoted from two reports. E10's report had to carry E08's figures by hand
for exactly this comparison.

**What separates what, restated where a caller will see it.** `frame_deltas`,
`luma_series` and `similarity_to_first` are whole-image statistics: they move with the
subject, the camera, the exposure and the scene alike, and none of them can attribute a
change to any one of those. `horizon_row` is the exception and the reason it is here — a
static camera over a moving figure leaves the room's horizon on one row. When the room is
repainted into somewhere without a single horizontal edge, it reports NOT FOUND rather
than a number, and that report is itself the finding.

Compensator (NAMED_COMPENSATORS): writes one JSON under `outputs/`. Compensator: delete
the file; owner: the executor session. Frame directories are opened read-only.

Prints `MEASURE_CLIP_OK`.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

from armature_core import clipstats as CS  # noqa: E402
from armature_core.errors import ArmatureError  # noqa: E402

TOOL_VERSION = "E11.1"


def frame_paths(directory):
    """The numbered frames of a directory, in index order.

    Numbered rather than `*.png`, for the reason `gate_b_frames` records: tools in this
    repo write contact strips beside their frames, and a naive glob counts one of those as
    a frame.
    """
    if not os.path.isdir(directory):
        raise ArmatureError(f"{directory} is not a directory of frames")
    names = [n for n in os.listdir(directory)
             if n.lower().endswith(".png") and os.path.splitext(n)[0].isdigit()]
    if not names:
        raise ArmatureError(
            f"{directory} carries no NNNNN.png frames; measurements over zero frames would "
            f"print a table of nulls that reads like a result")
    return [os.path.join(directory, n)
            for n in sorted(names, key=lambda n: int(os.path.splitext(n)[0]))]


def load(directory):
    return [np.asarray(Image.open(p).convert("RGB"), dtype=np.uint8)
            for p in frame_paths(directory)]


def measure(frames, label, band=None):
    horizon = [CS.horizon_row(f, band=band) for f in frames]
    found = [h for h in horizon if h["row"] is not None]
    rows = [h["row"] for h in found]
    return {
        "label": label,
        "n_frames": len(frames),
        "resolution": [int(frames[0].shape[1]), int(frames[0].shape[0])] if frames else None,
        "distinct": CS.distinct_frames(frames),
        "frame_deltas": CS.frame_deltas(frames),
        "luma": CS.luma_series(frames),
        "similarity_to_first": CS.similarity_to_first(frames),
        "horizon": {
            "per_frame": horizon,
            "n_found": len(found),
            "first_frame_row": horizon[0]["row"] if horizon else None,
            "row_range_where_found": ([min(rows), max(rows)] if rows else None),
            "reading": ("the one measurement here a moving subject cannot move. Frames "
                        "reporting NOT FOUND are frames whose room no longer has a single "
                        "horizontal edge — that is a finding about the scene, not a gap "
                        "in the data"),
        },
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", default="clip")
    ap.add_argument("--compare", default=None)
    ap.add_argument("--compare-label", default="compare")
    ap.add_argument("--horizon-band", default=None,
                    help="lo,hi rows to search for the horizon (argparse eats leading "
                         "minus signs: pass as --horizon-band=0,240)")
    a = ap.parse_args(argv)

    band = None
    if a.horizon_band:
        parts = [int(v) for v in a.horizon_band.split(",")]
        if len(parts) != 2:
            raise ArmatureError(f"--horizon-band={a.horizon_band!r} is not lo,hi")
        band = tuple(parts)

    record = {"tool": "measure_clip", "tool_version": TOOL_VERSION,
              "source": {"frames": os.path.abspath(a.frames)},
              "arms": [measure(load(a.frames), a.label, band)],
              "status": "DIAGNOSTIC — every number here gates nothing"}
    if a.compare:
        record["source"]["compare"] = os.path.abspath(a.compare)
        record["arms"].append(measure(load(a.compare), a.compare_label, band))

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2)

    summary = {}
    for arm in record["arms"]:
        summary[arm["label"]] = {
            "frames": arm["n_frames"], "distinct": arm["distinct"]["n_distinct"],
            "frame_delta_median": round(arm["frame_deltas"]["stats"]["median"], 3),
            "abs_delta_luma_median": round(arm["luma"]["stats"]["median"], 3),
            "similarity_mean_abs_last": round(
                arm["similarity_to_first"]["per_frame_mean_abs"][-1], 3),
            "correlation_last": round(
                arm["similarity_to_first"]["per_frame_correlation"][-1], 4),
            "horizon_found_on": f"{arm['horizon']['n_found']}/{arm['n_frames']}",
        }
    print("MEASURE_CLIP_OK " + json.dumps({"out": os.path.abspath(a.out),
                                           "summary": summary}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        print("MEASURE_CLIP_HALT " + json.dumps({
            "error": type(exc).__name__, "message": str(exc)}, default=str))
        sys.exit(2)
