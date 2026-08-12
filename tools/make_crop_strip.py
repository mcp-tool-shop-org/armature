#!/usr/bin/env python
r"""make_crop_strip — named native-resolution crops across frames, in one strip.

    python tools\make_crop_strip.py --frames=<dir> --out=<strip.png> --scale=3
           --boxes="0:380,4,470,96;32:352,12,442,112" [--title="face"]

`make_zoom_sheet` locates its crops from a keypoint projection, which exists only on the
routes that project one. A route with no driving signal has no keypoints, so the boxes are
stated by the caller — and stated **in the filename-visible provenance**, so a later reader
can re-cut the identical crop rather than guess where a published still came from.

Crops are cut at native resolution and enlarged by an integer factor with NEAREST, so no
resampling invents structure at the scale identity is judged at. The box and the scale are
printed on the strip and written to a sidecar.

Compensator (NAMED_COMPENSATORS): writes one PNG and one JSON under `outputs/`.
Compensator: delete them; owner: the executor session.
"""

import argparse
import json
import os

from PIL import Image, ImageDraw

BG = (18, 18, 20)
FG = (235, 235, 235)
DIM = (140, 140, 150)
LABEL_H = 16


def parse_boxes(text):
    """`"0:x0,y0,x1,y1;32:..."` -> `[(index, (x0, y0, x1, y1)), ...]`, or raise.

    Raises rather than skipping a malformed entry: a strip silently missing the frame it
    was cut to show is a strip that answers a question nobody asked.
    """
    out = []
    for part in (p.strip() for p in text.split(";")):
        if not part:
            continue
        if part.count(":") != 1:
            raise SystemExit(f"box entry {part!r} is not `<frame>:<x0,y0,x1,y1>`")
        idx, coords = part.split(":")
        nums = [int(v) for v in coords.split(",")]
        if len(nums) != 4:
            raise SystemExit(f"box entry {part!r} needs four coordinates, got {len(nums)}")
        x0, y0, x1, y1 = nums
        if x1 <= x0 or y1 <= y0:
            raise SystemExit(f"box entry {part!r} has non-positive extent")
        out.append((int(idx), (x0, y0, x1, y1)))
    if not out:
        raise SystemExit("--boxes parsed to nothing")
    return out


def frame_paths(directory):
    names = [n for n in os.listdir(directory)
             if n.lower().endswith(".png") and os.path.splitext(n)[0].isdigit()]
    return [os.path.join(directory, n)
            for n in sorted(names, key=lambda n: int(os.path.splitext(n)[0]))]


def build(paths, boxes, scale, title):
    tiles = []
    for idx, box in boxes:
        if idx >= len(paths):
            raise SystemExit(f"frame {idx} requested; only {len(paths)} frames present")
        im = Image.open(paths[idx]).convert("RGB").crop(box)
        im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
        tiles.append((idx, box, im))

    gap = 8
    width = sum(t[2].width for t in tiles) + gap * (len(tiles) + 1)
    height = max(t[2].height for t in tiles) + LABEL_H * 2 + gap * 2
    strip = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(strip)
    d.text((gap, 4), f"{title}   {scale}x NEAREST of native pixels   "
                     f"(crop boxes printed under each tile)", fill=FG)
    x = gap
    for idx, box, im in tiles:
        strip.paste(im, (x, LABEL_H + gap))
        d.text((x, LABEL_H + gap + im.height + 2), f"f{idx:03d}", fill=FG)
        d.text((x, LABEL_H + gap + im.height + 2 + 13),
               f"{box[0]},{box[1]},{box[2]},{box[3]}", fill=DIM)
        x += im.width + gap
    return strip, [{"frame": i, "box": list(b)} for i, b, _ in tiles]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--boxes", required=True,
                    help="`<frame>:<x0,y0,x1,y1>` entries, semicolon separated "
                         "(argparse eats leading minus signs: pass as --boxes=...)")
    ap.add_argument("--scale", type=int, default=3)
    ap.add_argument("--title", default="crop")
    a = ap.parse_args(argv)

    paths = frame_paths(a.frames)
    strip, record = build(paths, parse_boxes(a.boxes), a.scale, a.title)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    strip.save(a.out)
    side = os.path.splitext(a.out)[0] + ".json"
    with open(side, "w", encoding="utf-8") as fh:
        json.dump({"tool": "make_crop_strip", "frames": os.path.abspath(a.frames),
                   "title": a.title, "scale": a.scale, "crops": record}, fh, indent=2)
    print(f"CROP_STRIP {a.out} {strip.width}x{strip.height} sidecar={side}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
