#!/usr/bin/env python
"""make_overlay_sheet — the pose sticks composited onto the render they claim to describe.

    python tools\\make_overlay_sheet.py --keypoints=<keypoints.json> --render=<frame dir>
           --out=<sheet.png> [--frames=0,16,32,48,64]

A DIAGNOSTIC. It gates nothing, decides nothing and is never quoted as a number. What it
does is put the driving signal and the previz of the same performance in the same pixels, so
a wrong keypoint is visible instead of arguable.

**Why it earns its place before any credit is spent.** Every check in the pose-stick chain
so far is internally consistent: the counts agree, the frames are legal, nothing lands off
canvas, no frame is blank, the convention matches its source byte for byte. All of that is
equally true of a skeleton with its left and right arms swapped, its eyes placed on the back
of the skull, or its toes taken from the wrong end of the ankle bone. Those are errors of
*correspondence*, and the only instrument that sees them is the body itself.

This requires the keypoints to have been projected through the SAME camera the render used
— `project_pose_keypoints --camera-json=<that render's provenance>`, whose loader refuses a
record that disagrees about any angle.

Compensator: writes one PNG under `outputs/`; delete the file. Inputs are read-only.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402

from armature_core import aapose  # noqa: E402


def parse_args(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--keypoints", required=True)
    ap.add_argument("--render", required=True, help="directory of NNNNN.png previz frames")
    ap.add_argument("--out", required=True)
    ap.add_argument("--frames", default="0,16,32,48,64",
                    help="comma-separated frame indices (argparse eats leading minus signs)")
    ap.add_argument("--scale", type=float, default=0.5)
    ap.add_argument("--dot", type=int, default=5, help="marker radius in source pixels")
    return ap.parse_args(argv)


def main(argv=None):
    a = parse_args(argv)
    import cv2

    with open(a.keypoints, encoding="utf-8") as fh:
        rec = json.load(fh)
    width, height = rec["resolution"]
    idx = [int(v) for v in a.frames.split(",") if v.strip() != ""]

    tiles = []
    for i in idx:
        src = os.path.join(a.render, f"{i:05d}.png")
        if not os.path.isfile(src):
            raise FileNotFoundError(f"no previz frame at {src}")
        img = cv2.imread(src)
        if img is None:
            raise RuntimeError(f"cv2 could not read {src}")
        if (img.shape[1], img.shape[0]) != (width, height):
            raise ValueError(
                f"{src} is {img.shape[1]}x{img.shape[0]} and the keypoints were projected "
                f"at {width}x{height}; an overlay across resolutions proves nothing")

        # The sticks, drawn full-strength, then screened over the render so the body stays
        # readable underneath. Additive rather than alpha: a stick over a light backdrop
        # must not disappear into it, and the render here is a pale studio plate.
        sticks = aapose.draw_frame(height, width, rec["body"][i],
                                   left_hand=rec["left_hand"][i],
                                   right_hand=rec["right_hand"][i])[..., ::-1]
        over = np.maximum(img.astype(np.int16), sticks.astype(np.int16))
        over = np.clip(over, 0, 255).astype(np.uint8)

        # Ringed markers on the 20 body keypoints, so a joint landing off the body is
        # visible as a ring in empty air rather than hidden inside a stick.
        for j, (x, y, _c) in enumerate(rec["body"][i]):
            cv2.circle(over, (int(round(x)), int(round(y))), a.dot, (255, 255, 255), 1)
            cv2.putText(over, str(j), (int(round(x)) + a.dot + 2, int(round(y)) - 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)

        cv2.putText(over, f"frame {i}", (24, 44), cv2.FONT_HERSHEY_SIMPLEX, 1.1,
                    (255, 255, 255), 2, cv2.LINE_AA)
        tiles.append(cv2.resize(over, (int(width * a.scale), int(height * a.scale)),
                                interpolation=cv2.INTER_AREA))

    sheet = np.concatenate(tiles, axis=1)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    cv2.imwrite(a.out, sheet)
    print("OVERLAY_SHEET_OK " + json.dumps({
        "out": os.path.abspath(a.out), "frames": idx,
        "tile": [int(width * a.scale), int(height * a.scale)],
        "keypoint_names": list(aapose.KEYPOINT_NAMES)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
