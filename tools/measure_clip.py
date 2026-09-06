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
Halt contract: exit 0 on success, 2 on a deliberate refusal (one <TOOL>_HALT JSON line; evidence.clause is the branch word), 1 on a crash. See README §"Reading a halt" and armature_core.parts.run_tool_main.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from encode_control import runtime_provenance  # noqa: E402

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

from armature_core import clipstats as CS  # noqa: E402
from armature_core.errors import ArmatureError  # noqa: E402

TOOL_VERSION = "E11.1"



HALT_EPILOG = 'Halt contract: exit 0 on success, 2 on a deliberate refusal (one <TOOL>_HALT JSON line; evidence.clause is the branch word), 1 on a crash. See README §"Reading a halt".'

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


def round_or_none(value, ndigits):
    """`round(value, ndigits)`, or `None` when there is no value to round.

    F-cd036a86, wave 14. `clipstats._stats` was fixed in wave 12 so that its EMPTY case
    returns the same key set as its full one (`{"n": 0, ..., "median": None, ...}`) rather
    than a short dict, and the finding that drove it named `tools/measure_clip.py:131` as
    the consumer it was protecting: `round(arm["frame_deltas"]["stats"]["median"], 3)` on a
    one-frame clip. The key resolves now, to `None`, and the same line died on
    `TypeError: type NoneType doesn't define __round__ method` instead of `KeyError`.

    A one-frame clip is the natural input for exactly the failure these instruments exist
    to detect (`clipstats` says so in its own docstring), so the summary records `null`
    deliberately rather than refusing: this record is a DIAGNOSTIC and gates nothing. ONE
    implementation for the two consumers of the same two fields — this module's own summary
    and `make_startframe_sheet`'s `--measurements` panel, which imports it from here.
    """
    return None if value is None else round(value, ndigits)


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
    ap = argparse.ArgumentParser(
        description="the numbers a generated clip can be quoted by — diagnostics, all of "
                    "them, and the Director's eye is the judge",
        epilog=HALT_EPILOG)
    ap.add_argument("--frames", required=True,
                    help="the lossless frame directory to measure")
    ap.add_argument("--out", required=True, help="the measurements JSON to write")
    ap.add_argument("--label", default="clip",
                    help="what this clip is called in the record and in the printed lines")
    ap.add_argument("--compare", default=None,
                    help="a second frame directory to measure alongside; without it the "
                         "record carries one clip and no comparison")
    ap.add_argument("--compare-label", default="compare",
                    help="what the --compare clip is called in the record")
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

    # ---- the summary is built BEFORE the record is written. It used to be built after,
    #      so a one-frame clip left a complete, well-formed measurements JSON on disk with
    #      no `MEASURE_CLIP_OK` line ever printed — a later session (or a re-run into the
    #      same `--out`) reading the record alone found a finished measurement file for a
    #      run the instrument had died summarising (F-cd036a86).
    summary = {}
    for arm in record["arms"]:
        summary[arm["label"]] = {
            "frames": arm["n_frames"], "distinct": arm["distinct"]["n_distinct"],
            "frame_delta_median": round_or_none(
                arm["frame_deltas"]["stats"]["median"], 3),
            "abs_delta_luma_median": round_or_none(arm["luma"]["stats"]["median"], 3),
            "similarity_mean_abs_last": round_or_none(
                arm["similarity_to_first"]["per_frame_mean_abs"][-1], 3),
            "correlation_last": round_or_none(
                arm["similarity_to_first"]["per_frame_correlation"][-1], 4),
            "horizon_found_on": f"{arm['horizon']['n_found']}/{arm['n_frames']}",
        }

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        record.update(runtime_provenance())
        json.dump(record, fh, indent=2)

    print("MEASURE_CLIP_OK " + json.dumps({"out": os.path.abspath(a.out),
                                           "summary": summary}))
    return 0


if __name__ == "__main__":
    # WAVE 22, SEAM 1: the ONE `__main__` halt handler, adopted BY IMPORT from
    # `armature_core.parts` (core-solvers' file, posted to the wave-22 seams inbox). Never
    # copied — the whole point of the seam is that this block is one function with one home.
    from armature_core.parts import run_tool_main  # noqa: E402

    run_tool_main(main, "MEASURE_CLIP")
