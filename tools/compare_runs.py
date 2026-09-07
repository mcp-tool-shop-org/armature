#!/usr/bin/env python
"""compare_runs — G3's instrument. Compares two run directories **pixel by pixel**.

    <venv-python> tools/compare_runs.py --a=<run_a> --b=<run_b> --out=<report.json>
    <venv-python> tools/compare_runs.py --mode=frames --a=<lossless_a> --b=<lossless_b>

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
described. `frames_a` and `frames_b` ride `verdict_inputs` and the printed line as well,
so the happy path also states what it compared rather than only how much.

**CORRECTED 2026-09-04, and the correction is the interesting half.** That last sentence
also promised `n_name_mismatch` and `n_shape_mismatch` on `verdict_inputs`, and they were
put there — as sums over per-channel keys that a returned channel record can never carry,
because `compare_channel` RAISES on the first name disagreement and RAISES on any shape
disagreement, both before a `rec` exists to sum. Measured: a matched pair returned
`n_name_mismatch 0, n_shape_mismatch 0` and the channel record did not even hold a
`name_mismatch` key; a 3-vs-4-frame pair and an 8px-vs-16px pair each raised instead of
returning a report. The only two values those fields could ever take were 0 and 0, sitting
beside `frames_compared: N` and reading as a measurement that the two runs named the same
frames. That is a report carrying a placeholder shaped like evidence, and a check that
cannot fail is not a check. The counts are gone; in their place `verdict_inputs` states the
POLICY — these disagreements are refused, never reported — which is what is true.

**A pixel is counted once.** `n_differing_px` used to sum `(d > 0)` over the whole
(H, W, C) array, so a single differing RGB pixel read 3. The pixel count and the sample
count are now reported as separate, separately named quantities with the channel count
beside them.
Halt contract: exit 0 on success, 2 on a deliberate refusal (one <TOOL>_HALT JSON line; evidence.clause is the branch word), 1 on a crash. See README §"Reading a halt" and armature_core.parts.run_tool_main.
"""

import argparse
import hashlib
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from encode_control import runtime_provenance  # noqa: E402

from armature_core.errors import ArmatureError  # noqa: E402
from sheet_compose import frames_by_number  # noqa: E402



HALT_EPILOG = 'Halt contract: exit 0 on success, 2 on a deliberate refusal (one <TOOL>_HALT JSON line; evidence.clause is the branch word), 1 on a crash. See README §"Reading a halt".'

class CompareError(ArmatureError):
    """The comparison could not be made — not "the runs differ", but "nothing was opened"."""


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
    """Both sides, frame by frame — on a population that is FRAMES (F-2f2c19a9, wave 25).

    The two listings were bare `*.png` walks on both sides of the reproduction verdict. A
    stray — `render_pose_sticks` writes `strip_every{N}.png` beside its `NNNNN.png` frames,
    so this is the pipeline's own ordinary output — present in BOTH runs sorted into both
    populations and was compared as a frame; present in ONE it was refused, but as a name
    disagreement rather than as the stray it is, so the halt named the wrong condition.
    `sheet_compose.frames_by_number` is the ONE home for this refusal and is adopted by
    import, never spelled again here.
    """
    names_a = sorted(f for f in os.listdir(dir_a) if f.lower().endswith(".png"))
    names_b = sorted(f for f in os.listdir(dir_b) if f.lower().endswith(".png"))
    # ---- ANDON on each population, before either is compared or counted.
    for side, where, names in (("a", dir_a, names_a), ("b", dir_b, names_b)):
        frames_by_number(names, where=where, what="frames", exc=CompareError,
                         evidence={"andon": "CompareError",
                                   "clause": "stray_png_in_the_frame_population",
                                   "side": side})
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
    }
    # A LOCAL accumulator, not a record key. `rec["shape_mismatch"]` was initialised to
    # `[]`, appended to, and then RAISED on whenever it was non-empty, so every record a
    # caller can read carried the empty list and no other value was reachable — the
    # placeholder-shaped-like-evidence the wave-8 correction removed from `verdict_inputs`
    # and left one level down. The evidence dict on the refusal carries the measurement.
    shape_mismatch = []
    only_a = sorted(set(names_a) - set(names_b))
    only_b = sorted(set(names_b) - set(names_a))
    if names_a != names_b:
        # No `rec["name_mismatch"] = ...` here any more: it was assigned one line above a
        # raise, so no caller could ever read it, and the aggregate that summed it across
        # channels could only ever be 0. The evidence dict below carries the disagreement.
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
            shape_mismatch.append({"frame": name, "a": list(a.shape), "b": list(b.shape)})
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
    if shape_mismatch:
        # ---- ANDON. The other half of the same refusal: every shared name exists on
        #      both sides, and some of them were never comparable. The pixel verdict was
        #      computed over the rest and read exactly like a run that reproduced.
        raise CompareError(
            f"{len(shape_mismatch)} of the {len(shared)} shared frame(s) between "
            f"{dir_a} and {dir_b} differ in SHAPE and were never compared "
            f"({', '.join(m['frame'] for m in shape_mismatch[:6])}); the pixel "
            f"verdict would be read over the {rec['frames_compared']} that remained",
            {"dir_a": dir_a, "dir_b": dir_b,
             "frames_a": len(names_a), "frames_b": len(names_b),
             "frames_compared": rec["frames_compared"],
             "shape_mismatch": shape_mismatch[:8],
             "n_shape_mismatch": len(shape_mismatch)},
        )
    if rec["frames_compared"] == 0:
        raise CompareError(
            f"nothing was compared between {dir_a} and {dir_b}: "
            f"{len(names_a)} PNG(s) on the a side, {len(names_b)} on the b side, "
            f"{len(shared)} shared name(s), {len(shape_mismatch)} of those "
            f"shape-mismatched. A zero difference over zero pixels is not a measurement",
            {"dir_a": dir_a, "dir_b": dir_b,
             "names_a": names_a[:32], "names_b": names_b[:32],
             "shared": shared[:32], "frames_compared": 0,
             "shape_mismatch": shape_mismatch[:8]},
        )
    rec["mean_abs_diff_per_sample"] = (total / npx) if npx else None
    return rec


FRAMES_CHANNEL_NAME = "lossless"


def _verdict_inputs(channels):
    """Shared verdict block for channel-layout and flat-frames reports."""
    return {
        # The size of the population every number below is read over. A verdict without
        # it can be clean because nothing was opened — or because only part of it was.
        "frames_compared": sum(v["frames_compared"] for v in channels.values()),
        "frames_a": sum(v["frames_a"] for v in channels.values()),
        "frames_b": sum(v["frames_b"] for v in channels.values()),
        # Not counts. `compare_channel` raises on ANY name disagreement and on ANY shape
        # disagreement before it can return, so a report that exists at all is a report
        # over two populations that named the same frames at the same shapes. The counts
        # that used to sit here could only ever be 0 and 0.
        "name_mismatch_policy": ("refused, never reported: compare_channel raises "
                                 "CompareError on any name disagreement before a report "
                                 "exists"),
        "shape_mismatch_policy": ("refused, never reported: compare_channel raises "
                                  "CompareError on any shape disagreement before a report "
                                  "exists"),
        "channels_compared": sorted(channels),
        "max_abs_diff_any_channel": max(
            (v["max_abs_diff"] for v in channels.values()), default=None
        ),
        "channels_with_any_pixel_difference": sorted(
            c for c, v in channels.items()
            if v["n_frames_with_any_pixel_difference"] > 0
        ),
        "channels_with_byte_difference": sorted(
            c for c, v in channels.items()
            if v["n_frames_with_byte_difference"] > 0
        ),
    }


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
            f"like a run that reproduced. For two flat NNNNN.png generation directories "
            f"pass --mode=frames",
            {"run_a": os.path.abspath(run_a), "run_b": os.path.abspath(run_b),
             "channels_a": sorted(chans_a), "channels_b": sorted(chans_b),
             "shared": [], "hint": "--mode=frames"},
        )

    report = {
        "mode": "channels",
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

    report["verdict_inputs"] = _verdict_inputs(report["channels"])
    return report


def compare_frames(dir_a, dir_b, channel_name=FRAMES_CHANNEL_NAME):
    """Pixel-compare two flat NNNNN.png directories (F-fd89dddf).

    Paid runs' `extract_clip_frames` / VAEDecode taps write flat lossless dirs, not the
    channel-subdirectory layout `compare_runs` walks. Same receipt shape, one synthetic
    channel name (default `lossless`).
    """
    if not os.path.isdir(dir_a) or not os.path.isdir(dir_b):
        raise CompareError(
            f"--mode=frames needs two frame directories; "
            f"a={dir_a!r} is_dir={os.path.isdir(dir_a)} "
            f"b={dir_b!r} is_dir={os.path.isdir(dir_b)}",
            {"run_a": os.path.abspath(dir_a) if dir_a else dir_a,
             "run_b": os.path.abspath(dir_b) if dir_b else dir_b,
             "mode": "frames", "clause": "frames_dirs_required"},
        )
    rec = compare_channel(dir_a, dir_b)
    channels = {channel_name: rec}
    return {
        "mode": "frames",
        "run_a": os.path.abspath(dir_a),
        "run_b": os.path.abspath(dir_b),
        "channels_only_in_a": [],
        "channels_only_in_b": [],
        "channels": channels,
        "verdict_inputs": _verdict_inputs(channels),
    }


def _worst_frame_names(dir_a, dir_b, k=3):
    """Top-k frames by max_abs_diff (reuse compare_channel's per-frame math)."""
    names = sorted(f for f in os.listdir(dir_a)
                   if f.lower().endswith(".png") and f in set(os.listdir(dir_b)))
    scored = []
    for name in names:
        a = _load(os.path.join(dir_a, name))
        b = _load(os.path.join(dir_b, name))
        if a.shape != b.shape:
            continue
        d = np.abs(a - b)
        scored.append((int(d.max()), name))
    scored.sort(reverse=True)
    return [name for _mx, name in scored[:max(1, k)]]


def write_diff_sheet(path_a, path_b, report, out_path, mode="frames",
                     channel=None, k=3):
    """Paste A | B | abs-diff for the worst K frames; sidecar states scale (F-fbe241bc).

    make_diff_sheet.py is outside the frozen owned glob; --sheet on this tool is the
    owned entry. Diff is view-scaled so a 1-level delta is visible; the sidecar records
    the scale factor applied.
    """
    if mode == "frames":
        dir_a, dir_b = path_a, path_b
        ch_name = next(iter(report.get("channels") or {"lossless": None}))
    else:
        channels = report.get("channels") or {}
        if channel and channel in channels:
            ch_name = channel
        elif channels:
            ch_name = max(channels, key=lambda c: channels[c].get("max_abs_diff") or 0)
        else:
            raise CompareError(
                "--sheet under --mode=channels needs at least one compared channel",
                {"clause": "sheet_no_channel", "mode": mode})
        dir_a = os.path.join(path_a, ch_name)
        dir_b = os.path.join(path_b, ch_name)

    worst = _worst_frame_names(dir_a, dir_b, k=k)
    if not worst:
        raise CompareError(
            f"--sheet found no comparable frames under {dir_a} / {dir_b}",
            {"clause": "sheet_no_frames", "dir_a": dir_a, "dir_b": dir_b})

    # Scale so the max delta in the sheet maps near 255 for viewing.
    global_max = 1
    tiles = []
    for name in worst:
        a = np.array(Image.open(os.path.join(dir_a, name)).convert("RGB"), dtype=np.int16)
        b = np.array(Image.open(os.path.join(dir_b, name)).convert("RGB"), dtype=np.int16)
        d = np.abs(a.astype(np.int16) - b.astype(np.int16))
        global_max = max(global_max, int(d.max()) if d.size else 1)
        tiles.append((name, a.astype(np.uint8), b.astype(np.uint8), d))

    scale = 255.0 / float(global_max) if global_max > 0 else 1.0
    rows = []
    for name, a, b, d in tiles:
        view = np.clip(d.astype(np.float32) * scale, 0, 255).astype(np.uint8)
        gap = 8
        h = max(a.shape[0], b.shape[0], view.shape[0])
        w = a.shape[1] + gap + b.shape[1] + gap + view.shape[1]
        canvas = Image.new("RGB", (w, h + 18), (18, 18, 20))
        canvas.paste(Image.fromarray(a), (0, 0))
        canvas.paste(Image.fromarray(b), (a.shape[1] + gap, 0))
        canvas.paste(Image.fromarray(view), (a.shape[1] + gap + b.shape[1] + gap, 0))
        from PIL import ImageDraw
        ImageDraw.Draw(canvas).text(
            (4, h + 2), f"{name}  max|d|={int(d.max())}  scale={scale:.3f}",
            fill=(200, 200, 210))
        rows.append(canvas)

    margin = 8
    sheet_w = max(r.width for r in rows)
    sheet_h = margin + sum(r.height + margin for r in rows)
    sheet = Image.new("RGB", (sheet_w + 2 * margin, sheet_h), (12, 12, 14))
    y = margin
    for r in rows:
        sheet.paste(r, (margin, y))
        y += r.height + margin

    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    sheet.save(out_path)
    sidecar = {
        "tool": "compare_runs",
        "kind": "diff_sheet",
        "sheet": os.path.abspath(out_path),
        "mode": mode,
        "channel": ch_name,
        "worst_frames": worst,
        "view_scale": scale,
        "global_max_abs_diff": global_max,
        "note": ("abs-diff column is view-scaled: displayed = min(255, raw * scale). "
                 "Native pixels decide; this sheet locates."),
        **runtime_provenance(),
    }
    side_path = out_path + ".scale.json"
    with open(side_path, "w", encoding="utf-8") as fh:
        json.dump(sidecar, fh, indent=2)
    return os.path.abspath(out_path)


def main(argv=None):
    """G3's comparison, driven from the command line.

    **The parser was hand-rolled** as `for token in argv: key, _, value =
    token[2:].partition("=")` — the first two characters removed from every token whatever
    its shape, unknown keys accepted in silence, and the report written only `if "out" in
    args`. Measured 2026-09-04 against the rig's own E02 runs: `--outt=<path>` printed a
    clean `COMPARE {...}`, exited 0 and wrote no file; `--help` died with `KeyError: 'a'`,
    so the tool could not answer for its own usage; and `--a <path>` — the space form every
    sibling in this domain accepts — read `''` and died in `os.listdir` naming no flag.

    argparse gives `--help`, refuses an unknown flag with exit 2, and accepts both forms.
    `--out` stays optional, and the success line says which of the two happened rather than
    leaving a reader to infer a report exists.

    F-fd89dddf: `--mode=frames` exposes `compare_channel` on two flat generation dirs.
    """
    ap = argparse.ArgumentParser(
        description="compare two run directories pixel by pixel (G3's instrument). "
                    "--mode=channels (default) walks channel subdirectories; "
                    "--mode=frames compares two flat NNNNN.png dirs",
        epilog=HALT_EPILOG)
    ap.add_argument("--a", required=True,
                    help="first run directory (channels mode) or flat frames dir "
                         "(frames mode)")
    ap.add_argument("--b", required=True,
                    help="second run directory (channels mode) or flat frames dir "
                         "(frames mode)")
    ap.add_argument("--mode", default="channels", choices=("channels", "frames"),
                    help="channels (default): compare shared channel subdirectories. "
                         "frames: call compare_channel on --a/--b directly under the "
                         "synthetic channel name 'lossless' (paid-run VAEDecode layout)")
    ap.add_argument("--channel", default=None,
                    help="with --sheet under --mode=channels: which channel subdirectory "
                         "to tile (default: the channel with the worst max_abs_diff)")
    ap.add_argument("--sheet", default=None,
                    help="write A | B | abs-diff tiles for the worst frames to this PNG "
                         "(F-fbe241bc); sidecar <sheet>.scale.json states the view scale")
    ap.add_argument("--sheet-k", type=int, default=3,
                    help="with --sheet: how many worst frames to tile (default 3)")
    ap.add_argument("--out", default=None,
                    help="where to write the JSON report; omitted, none is written and "
                         "the OK line says so")
    args = ap.parse_args(argv)

    if args.mode == "frames":
        report = compare_frames(args.a, args.b)
    else:
        report = compare_runs(args.a, args.b)
    written = None
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            report.update(runtime_provenance())
            json.dump(report, fh, indent=2)
        written = os.path.abspath(args.out)
    sheet_path = None
    if args.sheet:
        sheet_path = write_diff_sheet(
            args.a, args.b, report, args.sheet,
            mode=args.mode, channel=args.channel, k=args.sheet_k)
    # The success sentinel rides AFTER the report is on disk, and names it: a verdict line
    # that printed whether or not anything was written is how a mistyped flag read as a
    # completed comparison.
    print("COMPARE_RUNS_OK " + json.dumps(
        dict(report["verdict_inputs"],
             mode=report.get("mode", args.mode),
             report=written or "no report written (--out not given)",
             sheet=sheet_path or "no sheet (--sheet not given)")))
    return 0


if __name__ == "__main__":
    # WAVE 25 (F-68f3fb4b): the ONE `__main__` halt handler, adopted BY IMPORT from
    # `armature_core.parts` (wave 22, SEAM 1 — core-solvers' file). This tool was one of
    # the 29 in `tests/test_instrument_exits.py::CPYTHON_HALT_CONTRACT_PENDING`: its
    # typed refusals reached the operator as a stdlib traceback at exit 1 — the code this
    # repo reserves for a crash — and the evidence dict naming the clause reached nothing.
    # Never copied; the point of the seam is that this block is one function with one home.
    from armature_core.parts import run_tool_main  # noqa: E402

    run_tool_main(main, "COMPARE_RUNS")
