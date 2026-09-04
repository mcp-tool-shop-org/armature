#!/usr/bin/env python
"""compare_runs — G3's instrument. Compares two run directories **pixel by pixel**.

    python tools/compare_runs.py --a=<run_a> --b=<run_b> --out=<report.json>

A PNG byte-hash mismatch is **not** evidence a render changed — facet false-halted on
that twice. So this compares decoded pixels and reports per-channel max and mean
absolute difference, plus where any difference lives. It **reports; it does not halt**:
G3 is a measurement, not an andon, and the spec says do not halt on nonzero without
inspecting where it lives.

Byte hashes are still reported alongside, because the difference between "the bytes
differ" and "the pixels differ" is itself the finding facet paid for.

Runs outside Blender (Pillow is not in Blender's python), which also makes the decoder
a different implementation from the writer.

**What DOES raise, and why it is not a halt on a difference.** Reporting a nonzero
difference is the design. Reporting a *clean* verdict over a comparison that opened no
pixels is not a measurement at all: two runs whose channel directories exist and hold no
PNGs used to print `{"max_abs_diff_any_channel": 0, ...}` and exit 0, byte for byte what a
run that genuinely reproduced prints, and so did two runs with no channel in common. So a
channel that compared zero frames raises, a pair of runs sharing no channel raises, and
`frames_compared` rides the printed line — a clean verdict now cannot be read without the
population behind it. Measured 2026-09-03.

**A PARTIAL non-comparison is the same defect, and it took a second measurement to see.**
Those two andons refuse only a TOTAL absence of comparison. `name_mismatch` and
`shape_mismatch` were recorded per channel and reached neither `verdict_inputs` nor the
printed line, so a reduced comparison still read as a clean reproduction. Measured
2026-09-03, two cases: run A of 6 frames against run B holding only the first 3,
byte-identical, printed `frames_compared: 3, max_abs_diff_any_channel: 0` and exited 0 —
an aborted render reported as a reproduction, with `only_in_a: [00003,00004,00005]` sitting
unread in the record; and four matching names of which three were rendered at another size
with wholly different content printed `max_abs_diff_any_channel: 0` with an empty
difference list, the render "reproducing" over one of four frames.

So the two sides must name the SAME frames for a shared channel, and every shared name must
be comparable. This is the refusal `measure_floor.common_frame_count` already implements for
the same reason — pairing populations that disagree reports over a population nobody
described. `frames_a`, `frames_b`, `n_name_mismatch` and `n_shape_mismatch` ride
`verdict_inputs` and the printed line as well, so the happy path also states what it
compared rather than only how much.

**A pixel is counted once.** `n_differing_px` used to sum `(d > 0)` over the whole
(H, W, C) array, so a single differing RGB pixel read 3. The pixel count and the sample
count are now reported as separate, separately named quantities with the channel count
beside them.
"""

import hashlib
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core.errors import ArmatureError  # noqa: E402


class CompareError(ArmatureError):
    """The comparison could not be made — not "the runs differ", but "nothing was opened"."""

    def __init__(self, message, evidence=None):
        super().__init__(message)
        self.evidence = evidence or {}


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _load(path):
    img = Image.open(path)
    arr = np.array(img)
    if arr.dtype == bool:
        arr = arr.astype(np.uint8) * 255
    return arr.astype(np.int32)


def compare_channel(dir_a, dir_b):
    names_a = sorted(f for f in os.listdir(dir_a) if f.endswith(".png"))
    names_b = sorted(f for f in os.listdir(dir_b) if f.endswith(".png"))
    rec = {
        "frames_a": len(names_a),
        "frames_b": len(names_b),
        "frames_compared": 0,
        "max_abs_diff": 0,
        "mean_abs_diff_per_sample": 0.0,
        "samples_per_pixel": None,
        "n_frames_with_any_pixel_difference": 0,
        "n_frames_with_byte_difference": 0,
        "worst_frame": None,
        "shape_mismatch": [],
    }
    only_a = sorted(set(names_a) - set(names_b))
    only_b = sorted(set(names_b) - set(names_a))
    if names_a != names_b:
        rec["name_mismatch"] = {"only_in_a": only_a[:8], "only_in_b": only_b[:8]}
        # ---- ANDON. Not on a difference — on the two sides not being the same frames.
        #      A truncated or renamed run compared over its intersection reports a clean
        #      verdict for the frames that survived and says nothing about the rest.
        raise CompareError(
            f"{dir_a} holds {len(names_a)} PNG(s) and {dir_b} holds {len(names_b)}, and "
            f"they do not name the same frames ({len(only_a)} only on the a side, "
            f"{len(only_b)} only on the b side). Comparing the "
            f"{len(set(names_a) & set(names_b))} shared name(s) would report a "
            f"reproduction over a population nobody described",
            {"dir_a": dir_a, "dir_b": dir_b,
             "frames_a": len(names_a), "frames_b": len(names_b),
             "names_a": names_a[:32], "names_b": names_b[:32],
             "only_in_a": only_a[:32], "only_in_b": only_b[:32],
             "n_name_mismatch": len(only_a) + len(only_b)},
        )

    shared = [n for n in names_a if n in set(names_b)]
    total, npx = 0.0, 0
    for name in shared:
        pa, pb = os.path.join(dir_a, name), os.path.join(dir_b, name)
        if _sha256(pa) != _sha256(pb):
            rec["n_frames_with_byte_difference"] += 1
        a, b = _load(pa), _load(pb)
        if a.shape != b.shape:
            rec["shape_mismatch"].append({"frame": name, "a": list(a.shape), "b": list(b.shape)})
            continue
        d = np.abs(a - b)
        rec["frames_compared"] += 1
        # A PIXEL is a position, not a sample. `(d > 0).sum()` over an (H, W, C) array
        # counts one differing RGB pixel three times, and there was nothing beside the
        # number saying which of the two it was.
        spp = int(d.shape[2]) if d.ndim == 3 else 1
        rec["samples_per_pixel"] = spp
        mx = int(d.max())
        if mx > 0:
            rec["n_frames_with_any_pixel_difference"] += 1
            if rec["worst_frame"] is None or mx > rec["max_abs_diff"]:
                ys, xs = np.nonzero(d.reshape(d.shape[0], -1))
                differing = (d > 0).any(axis=-1) if d.ndim == 3 else (d > 0)
                rec["worst_frame"] = {
                    "frame": name,
                    "max_abs_diff": mx,
                    "n_differing_px": int(differing.sum()),
                    "n_differing_samples": int((d > 0).sum()),
                    "samples_per_pixel": spp,
                    "first_differing_row": int(ys.min()) if ys.size else None,
                }
        rec["max_abs_diff"] = max(rec["max_abs_diff"], mx)
        total += float(d.sum())
        npx += int(d.size)
    # ---- ANDON. Not on a difference — on having compared nothing, which reports as a
    #      perfect zero and is indistinguishable from a run that reproduced.
    if rec["shape_mismatch"]:
        # ---- ANDON. The other half of the same refusal: every shared name exists on
        #      both sides, and some of them were never comparable. The pixel verdict was
        #      computed over the rest and read exactly like a run that reproduced.
        raise CompareError(
            f"{len(rec['shape_mismatch'])} of the {len(shared)} shared frame(s) between "
            f"{dir_a} and {dir_b} differ in SHAPE and were never compared "
            f"({', '.join(m['frame'] for m in rec['shape_mismatch'][:6])}); the pixel "
            f"verdict would be read over the {rec['frames_compared']} that remained",
            {"dir_a": dir_a, "dir_b": dir_b,
             "frames_a": len(names_a), "frames_b": len(names_b),
             "frames_compared": rec["frames_compared"],
             "shape_mismatch": rec["shape_mismatch"][:8],
             "n_shape_mismatch": len(rec["shape_mismatch"])},
        )
    if rec["frames_compared"] == 0:
        raise CompareError(
            f"nothing was compared between {dir_a} and {dir_b}: "
            f"{len(names_a)} PNG(s) on the a side, {len(names_b)} on the b side, "
            f"{len(shared)} shared name(s), {len(rec['shape_mismatch'])} of those "
            f"shape-mismatched. A zero difference over zero pixels is not a measurement",
            {"dir_a": dir_a, "dir_b": dir_b,
             "names_a": names_a[:32], "names_b": names_b[:32],
             "shared": shared[:32], "frames_compared": 0,
             "shape_mismatch": rec["shape_mismatch"][:8]},
        )
    rec["mean_abs_diff_per_sample"] = (total / npx) if npx else None
    return rec


def compare_runs(run_a, run_b):
    chans_a = {d for d in os.listdir(run_a) if os.path.isdir(os.path.join(run_a, d))}
    chans_b = {d for d in os.listdir(run_b) if os.path.isdir(os.path.join(run_b, d))}
    shared = sorted(c for c in chans_a & chans_b if c != "master")
    # ---- ANDON. A mistyped --a/--b, a run whose channels were written under different
    #      names, or an aborted render all reach here, and all used to print a null max
    #      with an empty channel list and exit 0.
    if not shared:
        raise CompareError(
            f"{run_a} and {run_b} share no comparable channel directory "
            f"(master is excluded by design); a report over no channels reads exactly "
            f"like a run that reproduced",
            {"run_a": os.path.abspath(run_a), "run_b": os.path.abspath(run_b),
             "channels_a": sorted(chans_a), "channels_b": sorted(chans_b),
             "shared": []},
        )

    report = {
        "run_a": os.path.abspath(run_a),
        "run_b": os.path.abspath(run_b),
        "channels_only_in_a": sorted(chans_a - chans_b),
        "channels_only_in_b": sorted(chans_b - chans_a),
        "channels": {},
    }
    for c in shared:
        report["channels"][c] = compare_channel(
            os.path.join(run_a, c), os.path.join(run_b, c)
        )

    report["verdict_inputs"] = {
        # The size of the population every number below is read over. A verdict without
        # it can be clean because nothing was opened — or because only part of it was.
        "frames_compared": sum(v["frames_compared"] for v in report["channels"].values()),
        "frames_a": sum(v["frames_a"] for v in report["channels"].values()),
        "frames_b": sum(v["frames_b"] for v in report["channels"].values()),
        "n_name_mismatch": sum(
            len(v.get("name_mismatch", {}).get("only_in_a", []))
            + len(v.get("name_mismatch", {}).get("only_in_b", []))
            for v in report["channels"].values()),
        "n_shape_mismatch": sum(
            len(v["shape_mismatch"]) for v in report["channels"].values()),
        "channels_compared": sorted(report["channels"]),
        "max_abs_diff_any_channel": max(
            (v["max_abs_diff"] for v in report["channels"].values()), default=None
        ),
        "channels_with_any_pixel_difference": sorted(
            c for c, v in report["channels"].items()
            if v["n_frames_with_any_pixel_difference"] > 0
        ),
        "channels_with_byte_difference": sorted(
            c for c, v in report["channels"].items()
            if v["n_frames_with_byte_difference"] > 0
        ),
    }
    return report


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    args = {}
    for token in argv:
        key, _, value = token[2:].partition("=")
        args[key] = value
    report = compare_runs(args["a"], args["b"])
    if "out" in args:
        os.makedirs(os.path.dirname(os.path.abspath(args["out"])), exist_ok=True)
        with open(args["out"], "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
    print("COMPARE " + json.dumps(report["verdict_inputs"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
