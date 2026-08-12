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
    ap = argparse.ArgumentParser()
    ap.add_argument("--keypoints", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--stickwidth-type", default="v2", choices=("v1", "v2"))
    ap.add_argument("--hands", type=int, default=1,
                    help="1 draws the synthesised mitten hands; recorded either way")
    ap.add_argument("--strip", type=int, default=8,
                    help="build a contact strip of every Nth frame; 0 disables")
    return ap.parse_args(argv)


def _sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def gate_canvas(body, width, height):
    """Gate CANVAS · ANDON — every body keypoint is inside the frame."""
    bad = []
    for i, frame in enumerate(body):
        for j, (x, y, _c) in enumerate(frame):
            if not (0 <= x <= width - 1 and 0 <= y <= height - 1):
                bad.append({"frame": i, "index": j,
                            "name": aapose.KEYPOINT_NAMES[j], "xy": [x, y]})
    ev = {"gate": "CANVAS", "resolution": [width, height], "n_outside": len(bad),
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


def main(argv=None):
    started = time.time()
    a = parse_args(argv)
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)          # scripts create their own output directories

    import cv2

    with open(a.keypoints, encoding="utf-8") as fh:
        rec = json.load(fh)
    width, height = rec["resolution"]
    body, lh, rh = rec["body"], rec["left_hand"], rec["right_hand"]
    n = rec["frames"]
    if not (len(body) == len(lh) == len(rh) == n):
        raise SticksGate(
            f"the keypoint record disagrees with itself: {n} frames declared, "
            f"{len(body)}/{len(lh)}/{len(rh)} present", {})

    # Gate CONV — before a single pixel. What is about to be drawn IS the convention.
    aapose.check_convention(len(aapose.KEYPOINT_NAMES), aapose.LIMB_SEQ, aapose.PALETTE)
    if rec.get("convention", {}).get("sha256") != aapose.SOURCE["sha256"]:
        raise SticksGate(
            "the keypoint record was projected against a different convention pin than this "
            "module carries; the two halves would disagree about what a keypoint index "
            "means",
            {"record": rec.get("convention", {}).get("sha256"),
             "module": aapose.SOURCE["sha256"]})

    gate_can = gate_canvas(body, width, height)

    sw = aapose.stickwidth(height, width, a.stickwidth_type)
    hsw = aapose.hand_stickwidth(height, width, a.stickwidth_type)

    paths, fracs, digests = [], [], {}
    for i in range(n):
        canvas = aapose.draw_frame(
            height, width, body[i],
            left_hand=lh[i] if a.hands else None,
            right_hand=rh[i] if a.hands else None,
            stickwidth_type=a.stickwidth_type, draw_hands=bool(a.hands))
        fracs.append(float((canvas.any(axis=2)).mean()))
        p = os.path.join(out, f"{i:05d}.png")
        # The source's own __main__ reverses channels into cv2.imwrite; the canvas is RGB.
        ok = cv2.imwrite(p, canvas[..., ::-1])
        if not ok:
            raise SticksGate(f"cv2 refused to write {p}", {})
        paths.append(p)
        with open(p, "rb") as fh:
            digests[os.path.basename(p)] = _sha256_bytes(fh.read())

    # The ink floor, derived from this drawing rather than typed: one limb ellipse of the
    # solved stick width spanning a tenth of the frame, as a fraction of the frame.
    min_frac = (sw * 2.0 * (0.1 * min(width, height))) / float(width * height)
    gate_i = gate_ink(fracs, min_frac)

    written = sorted(f for f in os.listdir(out) if f.endswith(".png") and f[0].isdigit())
    if len(written) != n:
        raise SticksGate(f"wrote {len(written)} frames and the record carries {n}",
                         {"out": out})

    strip_path = None
    if a.strip:
        idx = list(range(0, n, a.strip))
        tiles = [cv2.imread(paths[i]) for i in idx]
        strip = np.concatenate(tiles, axis=1)
        strip_path = os.path.join(out, f"strip_every{a.strip}.png")
        cv2.imwrite(strip_path, strip)

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
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 - the halt must be legible and loud
        import traceback
        traceback.print_exc()
        detail = getattr(exc, "evidence", None)
        print("RENDER_STICKS_HALT " + json.dumps({
            "error": type(exc).__name__, "message": str(exc),
            "evidence": detail if isinstance(detail, dict) else None}, default=str))
        sys.exit(2 if isinstance(exc, (GateFailure, ArmatureError)) else 1)
