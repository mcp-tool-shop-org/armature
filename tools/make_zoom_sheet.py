#!/usr/bin/env python
"""make_zoom_sheet — native-resolution crops where structure is hardest, with their boxes.

    python tools\\make_zoom_sheet.py --frames=<painted dir> --keypoints=<keypoints.json>
           --site=LWrist --at=15,16,31,32,49,64 --out=<sheet.png> [--crop=140 --scale=4]

*Sheets locate; full size decides.* The Gate 0 sheet fits five 832x480 frames across a
page, which is where a melted hand hides. This cuts the same frames at 1:1 around a named
keypoint and magnifies with NEAREST, so what is on screen is the pixels that came back and
not an interpolation of them.

**The crop centre comes from the DRIVING signal, not from a detector.** The keypoints this
pipeline rendered as sticks are exactly where the figure was told to put its wrists, so
they locate the painted wrist without running an estimator over the output — and where the
painted figure did NOT follow, the crop shows that too, which is the more useful failure.

Every crop box is written to a sidecar. A still whose provenance is unrecorded is a
picture, not evidence.

Compensator (NAMED_COMPENSATORS): writes one PNG and one JSON under `outputs/`.
Compensator: delete them; owner: the executor session. Inputs are read-only.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def crop_box(cx, cy, size, width, height):
    """A `size x size` box centred on (cx, cy), shifted to stay inside the frame.

    Clamped rather than padded: a padded crop invents pixels at the edge, and a keypoint
    near the border is exactly where the interesting failures live. Returns the box and
    whether the requested centre had to move — because a crop that silently slid is a crop
    whose caption is wrong.
    """
    half = size // 2
    x0 = int(round(cx)) - half
    y0 = int(round(cy)) - half
    x0c = max(0, min(width - size, x0))
    y0c = max(0, min(height - size, y0))
    return (x0c, y0c, x0c + size, y0c + size), (x0c != x0 or y0c != y0)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True, help="directory of NNNNN.png frames")
    ap.add_argument("--keypoints", required=True)
    ap.add_argument("--site", required=True,
                    help="a name from the record's keypoint_names, e.g. LWrist / Nose")
    ap.add_argument("--at", required=True,
                    help="comma-separated frame indices (argparse eats leading minus "
                         "signs, so pass flags as --flag=value)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--crop", type=int, default=140)
    ap.add_argument("--scale", type=int, default=4)
    a = ap.parse_args(argv)

    import cv2
    import numpy as np

    with open(a.keypoints, encoding="utf-8") as fh:
        rec = json.load(fh)
    names = rec["keypoint_names"]
    if a.site not in names:
        raise SystemExit(f"{a.site!r} is not one of {names}")
    k = names.index(a.site)
    idx = [int(v) for v in a.at.split(",") if v.strip() != ""]

    tiles, cuts = [], []
    for i in idx:
        path = os.path.join(a.frames, f"{i:05d}.png")
        img = cv2.imread(path)
        if img is None:
            raise SystemExit(f"cv2 could not read {path}")
        h, w = img.shape[:2]
        if [w, h] != rec["resolution"]:
            raise SystemExit(
                f"{path} is {w}x{h} and the keypoints were projected at "
                f"{rec['resolution']}; a crop located across resolutions points nowhere")
        cx, cy, _c = rec["body"][i][k]
        box, moved = crop_box(cx, cy, a.crop, w, h)
        cut = img[box[1]:box[3], box[0]:box[2]]
        big = cv2.resize(cut, (a.crop * a.scale, a.crop * a.scale),
                         interpolation=cv2.INTER_NEAREST)
        cv2.rectangle(big, (0, 0), (big.shape[1] - 1, 26), (0, 0, 0), -1)
        cv2.putText(big, f"f{i} {a.site}{' [clamped]' if moved else ''}", (6, 19),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
        tiles.append(big)
        cuts.append({"frame": i, "site": a.site, "keypoint_index": k,
                     "centre_px": [cx, cy], "crop_box": list(box),
                     "clamped_to_frame": moved, "scale": a.scale,
                     "interpolation": "NEAREST"})

    sheet = np.concatenate(tiles, axis=1)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    cv2.imwrite(a.out, sheet)
    side = os.path.splitext(a.out)[0] + "_crops.json"
    with open(side, "w", encoding="utf-8") as fh:
        json.dump({"tool": "make_zoom_sheet", "frames_dir": os.path.abspath(a.frames),
                   "keypoints": os.path.abspath(a.keypoints),
                   "crop_px": a.crop, "cuts": cuts,
                   "note": ("crop centres are the DRIVING keypoints this pipeline rendered "
                            "as sticks, not detector output; where the painted figure did "
                            "not follow, the crop shows that")}, fh, indent=2)
    print("ZOOM_SHEET_OK " + json.dumps({"out": os.path.abspath(a.out), "site": a.site,
                                         "frames": idx, "sidecar": side}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
