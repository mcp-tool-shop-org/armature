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
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core.errors import ArmatureError  # noqa: E402

BG = (18, 18, 20)
FG = (235, 235, 235)
DIM = (140, 140, 150)
LABEL_H = 16


class CropStripError(ArmatureError):
    """The strip cannot be cut as asked, or could not be re-cut from what it recorded.

    One refusal shape for this tool, carrying an evidence dict, rather than the bare
    `SystemExit` strings these checks used to raise: the measurement that fired a refusal
    is the useful half, and a caller catching this tool's own error catches all of them.
    """

    def __init__(self, message, evidence=None):
        super().__init__(message)
        self.evidence = evidence or {}


def _is_int(text):
    """An integer token, leading sign allowed. `str.isdigit()` refuses `-4`, which is a
    legal coordinate on a box that is later bounded against the frame."""
    t = str(text).strip()
    return bool(t) and (t[1:] if t[0] in "+-" else t).isdigit()


def parse_boxes(text):
    """`"0:x0,y0,x1,y1;32:..."` -> `[(frame NUMBER, (x0, y0, x1, y1)), ...]`, or raise.

    The first field is the frame's own NUMBER — the one in its file name — not a position
    in a sorted listing. See `build` for what that distinction cost.

    Raises rather than skipping a malformed entry: a strip silently missing the frame it
    was cut to show is a strip that answers a question nobody asked.
    """
    out = []
    for part in (p.strip() for p in text.split(";")):
        if not part:
            continue
        if part.count(":") != 1:
            raise CropStripError(f"box entry {part!r} is not `<frame>:<x0,y0,x1,y1>`",
                                 {"entry": part, "supplied": text})
        idx, coords = part.split(":")
        # `int(...)` was unguarded on BOTH tokens: the plausible operator typo in the flag
        # this tool exists to RECORD escaped the one refusal shape this module promises and
        # surfaced as `ValueError: invalid literal for int() with base 10: 'a'`, naming
        # neither the flag nor the shape it wanted. Measured 2026-09-04. This is the escape
        # `measure_floor._span` was given a refusal for, one tool over.
        raw = [v.strip() for v in coords.split(",")]
        bad = [v for v in raw if not _is_int(v)]
        if bad:
            raise CropStripError(
                f"--boxes entry {part!r} has a non-numeric coordinate "
                f"({', '.join(repr(v) for v in bad)}); it must be written "
                f"`<frame>:<x0,y0,x1,y1>` with five integers",
                {"entry": part, "supplied": text, "coordinates": raw,
                 "non_numeric": bad, "expected_shape": "<frame>:<x0,y0,x1,y1>"})
        if not _is_int(idx.strip()):
            raise CropStripError(
                f"--boxes entry {part!r} names a non-numeric frame ({idx.strip()!r}); the "
                f"first field is the frame's own NUMBER, as it appears in its file name",
                {"entry": part, "supplied": text, "frame_token": idx.strip(),
                 "expected_shape": "<frame>:<x0,y0,x1,y1>"})
        nums = [int(v) for v in raw]
        if len(nums) != 4:
            raise CropStripError(
                f"box entry {part!r} needs four coordinates, got {len(nums)}",
                {"entry": part, "coordinates": nums})
        x0, y0, x1, y1 = nums
        if x1 <= x0 or y1 <= y0:
            raise CropStripError(f"box entry {part!r} has non-positive extent",
                                 {"entry": part, "box": nums})
        out.append((int(idx), (x0, y0, x1, y1)))
    if not out:
        raise CropStripError("--boxes parsed to nothing", {"supplied": text})
    return out


def frames_by_number(directory):
    """`{frame NUMBER: path}` — keyed by the number in the file NAME.

    The shape `make_pick_sheet.frame_paths` and `make_plate` already build, for the reason
    this module exists: provenance a later reader can re-cut from. A listing indexed by
    POSITION cannot be re-cut, because the position depends on what else happens to be in
    the directory and on where the run's numbering starts.
    """
    if not os.path.isdir(directory):
        raise CropStripError(f"{directory} is not a directory of frames",
                             {"frames_dir": directory})
    names = [n for n in os.listdir(directory)
             if n.lower().endswith(".png") and os.path.splitext(n)[0].isdigit()]
    if not names:
        raise CropStripError(
            f"{directory} carries no NNNNN.png frames; there is nothing to cut a strip "
            f"from", {"frames_dir": directory,
                      "png_files": sorted(n for n in os.listdir(directory)
                                          if n.lower().endswith(".png"))[:16]})
    return {int(os.path.splitext(n)[0]): os.path.join(directory, n) for n in names}


def frame_paths(directory):
    """The numbered frames in index order. Kept for callers that want the sequence."""
    by_number = frames_by_number(directory)
    return [by_number[n] for n in sorted(by_number)]


def gate_box_inside(box, size, number, filename):
    """ANDON — the crop box lies inside the frame, or raise naming the overhang.

    PIL pads a box outside the image with zeros and says nothing, so the black is
    published as native pixels and the sidecar records the box as though it had been cut.
    """
    x0, y0, x1, y1 = box
    w, h = size
    over = {"x0": max(0, -x0), "y0": max(0, -y0),
            "x1": max(0, x1 - w), "y1": max(0, y1 - h)}
    ev = {"gate": "BOX", "frame": number, "file": filename, "box": list(box),
          "frame_size": [int(w), int(h)], "overhang": over}
    if any(over.values()):
        raise CropStripError(
            f"box {tuple(box)} is not inside frame {number} ({filename}, {w}x{h}); it "
            f"overhangs by {over}. PIL pads the outside with black and the sidecar would "
            f"record the box as though it had been cut from that frame, so re-cutting "
            f"from the record lands on the same black", ev)
    ev["verdict"] = f"inside {w}x{h}"
    return ev


def build(by_number, boxes, scale, title):
    """The strip and its crop record. `boxes` is keyed by frame NUMBER.

    **It used to be keyed by POSITION** (`paths[idx]`) while calling it a frame everywhere
    a reader sees it: the refusal said "frame {idx} requested", the tile label was
    `f{idx:03d}` and the sidecar recorded `{"frame": i}`. Measured 2026-09-04 on a
    directory numbered 00001..00003: `--boxes=0:0,0,20,20` cut `00001.png` (checked by
    pixel; `00000.png` does not exist) and wrote a sidecar naming `"frame": 0`. And
    `--boxes=-1:...` was accepted — the `idx >= len(paths)` guard bounded only the high
    side — cutting the LAST frame and recording `"frame": -1`. A published still's
    provenance then names a frame the run does not hold, and re-cutting from the sidecar
    lands somewhere else: a recipe that does not reproduce its output is not a recipe.
    """
    lo, hi = min(by_number), max(by_number)
    tiles = []
    for number, box in boxes:
        path = by_number.get(number)
        if path is None:
            raise CropStripError(
                f"--boxes names frame {number}; this directory holds frames {lo}..{hi} "
                f"({len(by_number)} of them). Cutting the nearest position instead would "
                f"publish a still whose provenance names a frame the run does not hold",
                {"asked": number, "lo": lo, "hi": hi, "n_frames": len(by_number),
                 "frames": sorted(by_number)[:32]})
        src = Image.open(path).convert("RGB")
        # ---- ANDON, before the crop: the box is INSIDE the frame it is cut from.
        #      `Image.crop` pads a box outside the image with zeros rather than raising,
        #      so a still that is wholly or partly black was published with a sidecar
        #      recording the box as though it had been cut from that frame. Measured
        #      2026-09-04 on 64x64 frames, `--boxes="0:900,900,960,960" --scale=2`:
        #      exit 0, a tile of 14400 pure-black pixels, `CROP_STRIP ... 136x168`. The
        #      realistic arrival is a box cut for one route's resolution applied to
        #      another's (832x480 vs 1280x720) — part image, part padding, no refusal.
        gate_box_inside(box, src.size, number, os.path.basename(path))
        im = src.crop(box)
        im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
        tiles.append((number, os.path.basename(path), box, src.size, im))

    gap = 8
    width = sum(t[4].width for t in tiles) + gap * (len(tiles) + 1)
    height = max(t[4].height for t in tiles) + LABEL_H * 2 + gap * 2
    strip = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(strip)
    d.text((gap, 4), f"{title}   {scale}x NEAREST of native pixels   "
                     f"(crop boxes printed under each tile)", fill=FG)
    x = gap
    for number, fname, box, _size, im in tiles:
        strip.paste(im, (x, LABEL_H + gap))
        # The FILE's own number, five digits like the file itself — never a position.
        d.text((x, LABEL_H + gap + im.height + 2), f"f{number:05d}", fill=FG)
        d.text((x, LABEL_H + gap + im.height + 2 + 13),
               f"{box[0]},{box[1]},{box[2]},{box[3]}", fill=DIM)
        x += im.width + gap
    # `frame_size` rides every crop: a later reader can then see the box was inside the
    # frame it names, rather than only that a box was asked for.
    return strip, [{"frame": n, "file": f, "box": list(b), "frame_size": list(sz)}
                   for n, f, b, sz, _im in tiles]


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

    # ---- ANDON, before a frame is opened: the enlargement factor is an enlargement.
    #      `--scale=0` reached `im.resize` and died inside PIL with
    #      `ValueError: height and width must be > 0`, naming neither the flag nor the
    #      value, after every requested frame had been read. The module's own contract is
    #      an enlargement "by an integer factor with NEAREST"; a factor below 1 is not one.
    if a.scale < 1:
        raise CropStripError(
            f"--scale={a.scale} is not an enlargement; this tool enlarges native pixels "
            f"by an integer factor with NEAREST, so the factor must be at least 1",
            {"gate": "SCALE", "scale": a.scale})

    by_number = frames_by_number(a.frames)
    strip, record = build(by_number, parse_boxes(a.boxes), a.scale, a.title)
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
