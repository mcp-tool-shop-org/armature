#!/usr/bin/env python
"""make_review_clip — the motion review, and the stills where structure is hardest.

    python tools/make_review_clip.py --frames=<lossless dir> --out=<dir>
                                     [--detection=<detection_raw.json>] [--fps=8]

*Video is judged in motion AND as frames.* A clip that reads well at speed can carry a
melted hand in every frame, so this emits both from the SAME lossless source:

* **the review clip** — an animated WEBP written LOSSLESS, at 8 fps against a 16 fps
  source, which is the 0.5x the spec asks for. Lossless because the whole point of tapping
  PNGs off the decode is that nothing downstream re-compresses what the Director judges.
* **the stills** — native-resolution crops where structure is hardest. Hands are located
  from the detector's own wrist landmarks when a detection record is given, and from the
  frame centre when it is not; the crop box is written into the sidecar either way, because
  a still whose provenance is unrecorded is a picture, not evidence.

**Two silences, both measured 2026-09-03.** `if i >= len(ims): continue` dropped a
requested still index with nothing saying so — the default `--stills=0,16,32,48,64` against
a 33-frame clip cut stills for 0/16/32 and printed `"stills": 12`, a count with no
denominator — while nine lines above, this file states the opposite principle about a
landmark outside the image. And `det[i]` indexed the detection rows by the still index with
no check of `len(det)` against `len(ims)` and none that the row describes frame `i`, which
is the positional pairing `measure_lift.gate_pairing` exists to refuse over rows whose
`frame` is an enumeration index. A detection record made over a differently-numbered render
paired each crop's landmark centre with another frame's detection, and `centre_px` then
recorded a centre never measured on that frame — on the hands-and-feet crops, which exist
precisely because that is where a video model's structure fails first.

Nothing here resamples the source: the clip is written at the frames' own resolution and
the stills are cut at 1:1. Sheets locate; full size decides.
"""

import argparse
import json
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from measure_lift import gate_listing_pairing  # noqa: E402
from sheet_compose import require_frames  # noqa: E402


def clip_name(fps, source_fps):
    """`review_<rate>x_<fps>fps.webp`, from the actual numbers.

    The name was the literal `review_0.5x_8fps.webp` whatever the flags said, which was
    true only while every source ran at 16 fps. On a 20 fps source the same file is 0.40x
    at 8 fps and the filename asserted otherwise — a label on an artifact the Director
    opens is evidence, and it may not be a placeholder. Corrected E10, 2026-08-12.
    """
    return f"review_{fps / float(source_fps):.2f}x_{fps}fps.webp"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--detection", default=None)
    ap.add_argument("--fps", type=int, default=8,
                    help="playback rate; 8 against a 16 fps source is 0.5x")
    ap.add_argument("--source-fps", type=int, default=16)
    ap.add_argument("--stills", default="0,16,32,48,64")
    ap.add_argument("--crop", type=int, default=224, help="still crop size, native pixels")
    a = ap.parse_args(argv)

    names = sorted(f for f in os.listdir(a.frames)
                   if f.lower().endswith(".png") and f[0].isdigit())
    if not names:
        raise SystemExit(f"no frames in {a.frames}")
    ims = [Image.open(os.path.join(a.frames, n)).convert("RGB") for n in names]

    det = None
    if a.detection:
        with open(a.detection, encoding="utf-8") as fh:
            det = json.load(fh)["rows"]
        # ---- ANDON. The rows describe THESE frames, by frame number — not by position.
        gate_listing_pairing({"frames": names, "detection": det})

    idx = [int(v) for v in a.stills.split(",") if v.strip() != ""]
    # ---- every requested still index exists. The count had no denominator.
    require_frames(idx, ims, what="clip frame(s)", where=a.frames)

    # ---- the output directory is created only once every in-tool andon above has
    #      fired. A refused run that has already made its directory leaves an empty
    #      one behind, which a later reader -- or a re-run into the same --out --
    #      reads as an attempt that produced nothing rather than one that was refused.
    #      The clip used to be written between the two andons above, so a run refused
    #      by either left a directory holding a review clip and no stills.
    os.makedirs(a.out, exist_ok=True)
    clip = os.path.join(a.out, clip_name(a.fps, a.source_fps))
    ims[0].save(clip, save_all=True, append_images=ims[1:],
                duration=int(round(1000.0 / a.fps)), loop=0, lossless=True, quality=100)

    W, H = ims[0].size
    half = a.crop // 2
    # 15/16 = left/right wrist, 27/28 = ankles. Hands and feet are where a video model's
    # structure fails first (G17 for contact; hands are the classic melt), so those are the
    # stills. A landmark the detector placed OUTSIDE the image is still cut — and the
    # sidecar records that it was outside, which is the finding rather than a missing file.
    targets = {"hand_L": 15, "hand_R": 16, "foot_L": 27, "foot_R": 28}
    cuts = []
    for i in idx:
        for label, li in targets.items():
            if det and det[i].get("fired"):
                x, y = det[i]["image"][li]
                outside = not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0)
                cx, cy = int(x * W), int(y * H)
            else:
                outside, cx, cy = None, W // 2, H // 2
            x0 = max(0, min(W - a.crop, cx - half))
            y0 = max(0, min(H - a.crop, cy - half))
            name = f"still_f{i:03d}_{label}.png"
            ims[i].crop((x0, y0, x0 + a.crop, y0 + a.crop)).save(os.path.join(a.out, name))
            cuts.append({"file": name, "frame": i, "target": label,
                         "landmark_index": li, "centre_px": [cx, cy],
                         "crop_box": [x0, y0, x0 + a.crop, y0 + a.crop],
                         "landmark_outside_the_image": outside})

    side = os.path.join(a.out, "review_manifest.json")
    with open(side, "w", encoding="utf-8") as fh:
        json.dump({"tool": "make_review_clip", "source": os.path.abspath(a.frames),
                   "n_frames": len(ims), "resolution": [W, H],
                   "clip": os.path.abspath(clip), "clip_fps": a.fps,
                   "source_fps": a.source_fps,
                   "playback_rate": f"{a.fps / float(a.source_fps):.2f}x",
                   "clip_lossless": True,
                   "stills_requested": idx, "n_stills_requested": len(idx),
                   "stills": cuts}, fh, indent=2)
    print("MAKE_REVIEW_CLIP_OK " + json.dumps({
        "clip": clip, "frames": len(ims), "fps": a.fps,
        "rate": f"{a.fps / float(a.source_fps):.2f}x",
        "stills": len(cuts), "stills_requested": idx,
        "manifest": side}))


if __name__ == "__main__":
    main()
