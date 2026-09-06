#!/usr/bin/env python
"""render_pose_sticks — the AAPose-20 driving frames, drawn to the pinned Wan convention.

    python tools\\render_pose_sticks.py --keypoints=<keypoints.json> --out=<dir>

Stage 2 of the pose-stick commission (E08), and the half with no Blender in it.
`tools/project_pose_keypoints.py` decides WHERE the joints are; this decides HOW they are
drawn, and it does nothing else. The convention itself lives in `armature_core.aapose`,
transcribed from `Wan-Video/Wan2.2` `human_visualization.py` at a pinned commit — see that
module for the pin, the 20-vs-18 correction, and the channel-order determination.

**What this is FOR.** Wan-Animate drives the body from a spatially-aligned skeleton signal
(G7). Armature renders that skeleton from a rig it owns instead of detecting it from video,
which is why no pose estimator appears anywhere in this pipeline — the whole banned
preprocessor tier is sidestepped by construction rather than by substitution
(docs/license-map.md). Whether the model accepts a CG-rendered signal at product quality is
E08's premise 6, marked ASSUMED: it is the experiment.

--------------------------------------------------------------------------------
The gates — all raise, in-process, before the manifest exists

* **Gate CONV** — the emitted topology, palette and keypoint count match the transcribed
  source element for element. An off-convention render fails SILENTLY: the model obeys
  weakly and no other check notices (G10).
* **Gate CANVAS** — every body keypoint lands inside the frame. Stage 1's framing solve
  bounds the body cloud, of which these 20 are a subset, so this cannot fire on correct work
  — and cv2 clips a stray point without a word, so nothing else would catch it.
* **Gate INK** — no frame is blank. A pose frame with nothing drawn on it is a well-formed
  PNG of the right size and the right count; the only thing wrong with it is that it drives
  nothing. Every threshold and every projection failure lands here.
* **Gate COUNT** — as many PNGs on disk as there are frames in the record.

Compensator (NAMED_COMPENSATORS): writes PNGs and a manifest under `outputs/`. Compensator:
delete the directory; owner: the executor session. The keypoint record is read-only.
"""

import argparse
import hashlib
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402

from armature_core import aapose  # noqa: E402
from armature_core.errors import ArmatureError, GateFailure  # noqa: E402

TOOL_VERSION = "E08.1"

#: The array these functions draw into is RGB — determined from the source's own `__main__`,
#: which reverses the channels on the way into `cv2.imwrite`. Recorded in the manifest so a
#: later run can flip one flag rather than re-derive the argument.
CHANNEL_ORDER = "RGB"


class SticksGate(GateFailure):
    gate = "STICKS"


def parse_args(argv=None):
    ap = argparse.ArgumentParser(
        description="draw the AAPose-20 driving frames to the pinned Wan convention — the "
                    "control sequence a pose route is driven by")
    ap.add_argument("--keypoints", required=True,
                    help="the projected keypoints record to draw")
    ap.add_argument("--out", required=True,
                    help="directory for the NNNNN.png stick frames and their record")
    ap.add_argument("--stickwidth-type", default="v2", choices=("v1", "v2"),
                    help="which pinned limb-width convention to draw with (default v2); "
                         "recorded, because a route trained on one reads the other as a "
                         "different signal")
    ap.add_argument("--hands", type=int, default=1,
                    help="1 draws the synthesised mitten hands; recorded either way")
    ap.add_argument("--strip", type=int, default=8,
                    help="build a contact strip of every Nth frame; 0 disables")
    return ap.parse_args(argv)


def _sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def gate_canvas(body, width, height):
    """Gate CANVAS · ANDON — every body keypoint is inside the frame, and is a NUMBER.

    **The confidence is read, not discarded.** Wave 22, SEAM 9 item 2: this loop unpacked
    `for j, (x, y, _c) in enumerate(frame)` and threw `_c` away, so it bounded coordinates
    only. `aapose.draw_body` compares that confidence against a threshold to decide whether
    a limb is drawn, and `nan < threshold` is False in both directions — so a NaN
    confidence produced ink byte-identical to a confidence of 1.0, with nothing having read
    it. core-solvers closed the andon INSIDE `draw_body`/`draw_hand`
    (`confidence_not_a_number`); this is the complementary bound at the reader, which is
    the wave-18 SEAM-5 shape: the andon inside the function performing the step, and the
    reader's bound at the flag. It fires earlier and names the frame and the keypoint.

    A non-finite COORDINATE is caught by the range test below (`nan <= width - 1` is False,
    so it lands in `bad`), and is named explicitly rather than left to that accident.
    """
    bad, not_a_number = [], []
    for i, frame in enumerate(body):
        for j, (x, y, c) in enumerate(frame):
            if not all(math.isfinite(float(v)) for v in (x, y, c)):
                not_a_number.append({"frame": i, "index": j,
                                     "name": aapose.KEYPOINT_NAMES[j],
                                     "xyc": [x, y, c]})
                continue
            if not (0 <= x <= width - 1 and 0 <= y <= height - 1):
                bad.append({"frame": i, "index": j,
                            "name": aapose.KEYPOINT_NAMES[j], "xy": [x, y]})
    if not_a_number:
        raise SticksGate(
            f"{len(not_a_number)} body keypoint(s) carry a value that is not a number, "
            f"e.g. {not_a_number[0]}. A NaN confidence walks `draw_body`'s threshold "
            f"comparison in both directions — `nan < threshold` and `nan > threshold` are "
            f"both False — so the limb is drawn or dropped on a number no code read, and "
            f"the ink is byte-identical to a confidence of 1.0",
            {"gate": "CANVAS", "andon": "SticksGate",
             "clause": "keypoint_value_is_not_a_number",
             "resolution": [width, height], "n_not_a_number": len(not_a_number),
             "examples": not_a_number[:8]})
    ev = {"gate": "CANVAS", "andon": "SticksGate",
          "clause": "keypoint_outside_the_frame",
          "resolution": [width, height], "n_outside": len(bad),
          "examples": bad[:8]}
    if bad:
        raise SticksGate(
            f"{len(bad)} body keypoint(s) fall outside the {width}x{height} frame, e.g. "
            f"{bad[0]}. Stage 1's framing solve bounds the body cloud these are a subset "
            f"of, so this disagreement means the two stages are not describing the same "
            f"shot. cv2 clips a stray point without a word", ev)
    ev["verdict"] = "all inside"
    return ev


def gate_ink(fracs, min_frac):
    """Gate INK · ANDON — no frame is blank.

    The floor is derived from the drawing itself, not typed in: the thinnest thing the
    convention can legitimately produce is the 19 limb ellipses at the solved stick width,
    and a frame carrying less ink than a small fraction of that is a frame with nothing on
    it. Passing `min_frac` in from the caller's own measurement keeps a global constant from
    governing a local feature.
    """
    worst = min(range(len(fracs)), key=lambda i: fracs[i])
    ev = {"gate": "INK", "min_fraction": min_frac,
          "worst": {"frame": worst, "frac": fracs[worst]},
          "mean_frac": float(np.mean(fracs)),
          "note": ("fraction of non-black pixels; a blank pose frame is a valid PNG of the "
                   "right size and count that drives nothing")}
    if fracs[worst] < min_frac:
        raise SticksGate(
            f"frame {worst} carries ink on only {fracs[worst]:.6f} of the image (floor "
            f"{min_frac:.6f}); nothing was drawn on it and the model would be driven by a "
            f"black frame", ev)
    ev["verdict"] = f"min {fracs[worst]:.5f} at frame {worst} over {len(fracs)} frames"
    return ev


def _written_frames(out):
    """The numbered PNGs on disk, by the predicate this directory's CONSUMERS use.

    Gate COUNT matched `f.endswith(".png") and f[0].isdigit()` — case-SENSITIVE on the
    extension and a first-character test on the stem — while the five tools that read this
    directory (`measure_floor.frame_population`, `encode_control.frame_population`,
    `measure_arm._load_frames`, `gate_b_frames.frame_paths`, `measure_clip.frame_paths`)
    were all settled in wave 8 on `n.lower().endswith(".png")` plus
    `os.path.splitext(n)[0].isdigit()`.

    Measured 2026-09-04: with `00003.PNG` planted beside three written frames, the gate
    recorded `COUNT PASS, frames: 3` and exited 0 while all five consumers derived FOUR.
    The upper-case arrival is real here — `fetch_run.verify_downloads` sweeps `.PNG` as a
    downloaded frame, and Windows preserves case. The stem test also drops the
    `0_debug.png` over-count the old predicate produced; that direction is pinned in
    `tests/test_render_pose_sticks.py`.
    """
    return sorted((f for f in os.listdir(out)
                   if f.lower().endswith(".png")
                   and os.path.splitext(f)[0].isdigit()),
                  key=lambda f: int(os.path.splitext(f)[0]))


def gate_strip_stride(stride):
    """ANDON — the contact strip's stride is a stride, checked where it is READ.

    F-a5b1e0af, wave 22. `--strip` is `type=int, default=8` with no bound, and it is read
    as `list(range(0, n, a.strip))` AFTER the whole control sequence and Gate COUNT have
    run. Re-measured on `e8263a3`: `list(range(0, 5, -8))` is `[]`, so
    `np.concatenate([], axis=1)` raised an untyped
    `ValueError: need at least one array to concatenate`. `--strip=0` was already guarded —
    `if a.strip:` disables the strip, which is the parser's documented off switch — so the
    NEGATIVE direction is the one nothing bounded, which is the shape wave 18's rule names:
    put the andon on the direction the invariant does not bound.

    The consequence is a write-ordering one. The run exited 1 as a crash AFTER every
    `NNNNN.png` was written and Gate COUNT had passed, but BEFORE `sticks_manifest.json` —
    so `--out` held a complete-looking driving sequence with no manifest, no convention pin,
    no per-frame sha256 and no Gate INK/CANVAS verdicts, and every consumer that derives its
    population from a bare listing (`encode_control.frame_population`,
    `gate_b_frames.frame_paths`, `measure_floor.frame_population`, `measure_arm._load_frames`,
    `measure_clip.frame_paths`) reads that as a finished sequence. So the bound is raised in
    the argument block, above `os.makedirs`, and a refused run leaves `--out` absent.

    A stride LARGER than the population is legal and is not refused: `range(0, 3, 99)` is
    `[0]`, one tile, which is a contact strip.
    """
    if stride < 0:
        raise SticksGate(
            f"--strip={stride} is not a stride; the contact strip is built from "
            f"range(0, n, --strip), and a negative stride makes that range EMPTY, which "
            f"reaches np.concatenate with no arrays after the whole control sequence has "
            f"already been written and Gate COUNT has already passed",
            {"gate": "ARGS", "andon": "SticksGate",
             "clause": "strip_stride_not_positive", "flag": "--strip", "value": stride,
             "minimum": 0,
             "note": "0 is the parser's documented off switch and stays legal"})
    return stride


def main(argv=None):
    started = time.time()
    a = parse_args(argv)
    out = os.path.abspath(a.out)

    # ---- ANDON, in the argument block and far above `os.makedirs`: see the docstring
    #      above for why this cannot wait until the stride is read.
    gate_strip_stride(a.strip)

    import cv2

    with open(a.keypoints, encoding="utf-8") as fh:
        rec = json.load(fh)
    width, height = rec["resolution"]
    body, lh, rh = rec["body"], rec["left_hand"], rec["right_hand"]
    n = rec["frames"]
    if not (len(body) == len(lh) == len(rh) == n):
        raise SticksGate(
            f"the keypoint record disagrees with itself: {n} frames declared, "
            f"{len(body)}/{len(lh)}/{len(rh)} present",
            # F-eab60ac3, wave 22: this raise passed a LITERAL `{}`, so the
            # `RENDER_STICKS_HALT` line printed `"evidence": {}` — no gate, no clause, and
            # none of the four counts the message states in prose. An empty dict at the
            # raise site is the exact shape wave 16 deleted family-wide (`evidence or {}`),
            # spelled where that sweep does not reach.
            {"gate": "RECORD", "andon": "SticksGate",
             "clause": "record_frame_counts_disagree",
             "keypoints": os.path.abspath(a.keypoints), "n_declared": n,
             "n_body": len(body), "n_left_hand": len(lh), "n_right_hand": len(rh)})

    # Gate CONV — before a single pixel. What is about to be drawn IS the convention.
    aapose.check_convention(len(aapose.KEYPOINT_NAMES), aapose.LIMB_SEQ, aapose.PALETTE)
    if rec.get("convention", {}).get("sha256") != aapose.SOURCE["sha256"]:
        raise SticksGate(
            "the keypoint record was projected against a different convention pin than this "
            "module carries; the two halves would disagree about what a keypoint index "
            "means",
            {"gate": "CONV", "andon": "SticksGate",
             "clause": "convention_pin_disagrees",
             "record": rec.get("convention", {}).get("sha256"),
             "module": aapose.SOURCE["sha256"]})

    gate_can = gate_canvas(body, width, height)

    sw = aapose.stickwidth(height, width, a.stickwidth_type)
    hsw = aapose.hand_stickwidth(height, width, a.stickwidth_type)

    def _draw(i):
        return aapose.draw_frame(
            height, width, body[i],
            left_hand=lh[i] if a.hands else None,
            right_hand=rh[i] if a.hands else None,
            stickwidth_type=a.stickwidth_type, draw_hands=bool(a.hands))

    # The ink floor, derived from this drawing rather than typed: one limb ellipse of the
    # solved stick width spanning a tenth of the frame, as a fraction of the frame.
    min_frac = (sw * 2.0 * (0.1 * min(width, height))) / float(width * height)

    # ---- Gate INK, BEFORE the first byte (F-5f2a7452, wave 14).
    #      `fracs` was appended inside the WRITE loop, as
    #      `float((canvas.any(axis=2)).mean())` over the in-memory canvas, and `gate_ink`
    #      ran after the loop had written all n frames — so when Gate INK fired, the whole
    #      refused control sequence was already on disk in `--out`, in exactly the shape
    #      the consumers of this directory pick up from a bare listing. It was also the
    #      only refusal in the loop that could have run before any byte was written, and
    #      `tests/test_instrument_write_ordering.py::READBACK_REASONS` excused it with
    #      "ink fraction measured over the frames just written", which it never was: it
    #      opened no file. The measurement is unchanged (the same canvas, the same
    #      predicate); only its POSITION moves. The draw is repeated rather than kept,
    #      because holding n canvases costs `n * height * width * 3` bytes and a long
    #      sequence is exactly when this tool is used; `draw_frame` is pure, so the second
    #      pass draws the same pixels.
    #      SEAM: `gate_ink` is no longer a read-back and leaves READBACK_REASONS (tests).
    fracs = [float((_draw(i).any(axis=2)).mean()) for i in range(n)]
    gate_i = gate_ink(fracs, min_frac)

    # WAVE-12 MERGE (coordinator, 2026-09-04): the output directory is created below the last refusal that needs
    # no file (the record's self-consistency, Gate CONV, the convention pin, Gate CANVAS), so a run
    # refused there leaves nothing on disk; the refusals below this line read back what was written.
    os.makedirs(out, exist_ok=True)          # scripts create their own output directories
    paths, digests = [], {}
    for i in range(n):
        canvas = _draw(i)
        p = os.path.join(out, f"{i:05d}.png")
        # The source's own __main__ reverses channels into cv2.imwrite; the canvas is RGB.
        ok = cv2.imwrite(p, canvas[..., ::-1])
        if not ok:
            # F-eab60ac3, wave 22: this raise passed a LITERAL `{}` while its own sibling
            # twenty-four lines below (the strip write) carried
            # `{"gate": "WRITE", "strip": ..., "every": ..., "n_tiles": ...}`. This one
            # fires INSIDE the write loop, eight lines below `os.makedirs`, so a partial
            # control sequence is on disk and the halt record carried nothing to say which
            # frame stopped it or where the directory is — the operator had to parse prose.
            raise SticksGate(
                f"cv2 refused to write {p}; frame {i} of {n} did not reach disk, so "
                f"{out} now holds a PARTIAL control sequence",
                {"gate": "WRITE", "andon": "SticksGate",
                 "clause": "cv2_refused_the_frame_write",
                 "frame": i, "path": os.path.abspath(p), "out": out, "n": n,
                 "written_before_this_frame": len(paths)})
        paths.append(p)
        with open(p, "rb") as fh:
            digests[os.path.basename(p)] = _sha256_bytes(fh.read())

    # Gate COUNT — over the population every CONSUMER of this directory derives.
    written = _written_frames(out)
    if len(written) != n:
        raise SticksGate(
            f"wrote {len(written)} frames and the record carries {n}; the control "
            f"sequence a paid generation is driven by is not the sequence this manifest "
            f"describes",
            {"gate": "COUNT", "out": out, "written": written, "n_written": len(written),
             "n_record": n})

    strip_path = None
    if a.strip:
        idx = list(range(0, n, a.strip))
        tiles = [cv2.imread(paths[i]) for i in idx]
        strip = np.concatenate(tiles, axis=1)
        strip_path = os.path.join(out, f"strip_every{a.strip}.png")
        # The per-frame write above already checks its return (SticksGate on a False);
        # this one did not. `cv2.imwrite` returns a BOOL on failure and raises nothing, so
        # the manifest recorded a contact strip that is not on disk.
        if not cv2.imwrite(strip_path, strip):
            raise SticksGate(
                f"cv2 refused to write {strip_path}; the manifest would record a contact "
                f"strip that is not there",
                {"gate": "WRITE", "andon": "SticksGate",
                 "clause": "cv2_refused_the_strip_write",
                 "strip": os.path.abspath(strip_path),
                 "every": a.strip, "n_tiles": len(idx)})

    manifest = {
        "tool": "render_pose_sticks",
        "tool_version": TOOL_VERSION,
        "convention": dict(aapose.SOURCE),
        "channel_order_in_memory": CHANNEL_ORDER,
        "channel_order_note": ("frames are written through cv2.imwrite(canvas[..., ::-1]) — "
                               "the same reversal the source's own __main__ performs, which "
                               "is the evidence the in-memory canvas is RGB"),
        "source_keypoints": {"path": os.path.abspath(a.keypoints),
                             "sha256": _sha256_bytes(
                                 open(a.keypoints, "rb").read())},
        "resolution": [width, height],
        "frames": n,
        "fps": rec.get("fps"),
        "stickwidth_type": a.stickwidth_type,
        "stickwidth_px": sw,
        "hand_stickwidth_px": hsw,
        "hands_drawn": bool(a.hands),
        "threshold": aapose.DEFAULT_THRESHOLD,
        "limb_brightness": aapose.LIMB_BRIGHTNESS,
        "diagnostics": dict(rec.get("diagnostics", {}),
                            ink_fraction_per_frame=fracs),
        "gates": {
            "CONV": {"verdict": "PASS",
                     "detail": f"20 keypoints / 19 pairs / 20 palette entries vs "
                               f"{aapose.SOURCE['path']} @ "
                               f"{aapose.SOURCE['commit'][:12]}"},
            "CANVAS": gate_can,
            "INK": gate_i,
            "COUNT": {"verdict": "PASS", "frames": n},
        },
        "frame_sha256": digests,
        "strip": strip_path,
        "elapsed_s": time.time() - started,
    }
    mpath = os.path.join(out, "sticks_manifest.json")
    with open(mpath, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)

    print("RENDER_STICKS_OK " + json.dumps({
        "out": out, "frames": n, "resolution": [width, height],
        "stickwidth_px": sw, "hand_stickwidth_px": hsw,
        "ink": gate_i["verdict"], "manifest": mpath, "strip": strip_path}))
    return 0


if __name__ == "__main__":
    # WAVE 22, SEAM 1: the ONE `__main__` halt handler, adopted BY IMPORT from
    # `armature_core.parts` (core-solvers' file, posted to the wave-22 seams inbox). Never
    # copied — the whole point of the seam is that this block is one function with one home.
    from armature_core.parts import run_tool_main  # noqa: E402

    run_tool_main(main, "RENDER_STICKS")
