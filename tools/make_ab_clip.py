#!/usr/bin/env python
"""make_ab_clip — two clips at their OWN true tempos, side by side in one file.

    python tools\\make_ab_clip.py --a=<frames dir> --a-fps=16 --a-label="E08 65f @ 16"
           --b=<frames dir> --b-fps=20 --b-label="E10 81f @ 20" --out=<clip.webp>

The Director judges motion at true tempo. Two arms that ran at different frame counts over
the same performance cannot be laid side by side by pairing frame k with frame k — that
plays one of them at the wrong speed — and pairing by nearest time **resamples** one arm,
which changes the very texture the comparison exists to read. Both moves quietly corrupt
the A/B.

**So neither arm is resampled and neither is retimed.** The composite runs on the UNION of
the two arms' frame times: a composite frame is emitted at every instant either side
changes, and each side simply HOLDS its current frame until its own next one arrives. That
is what a projector does. Every frame of both arms is shown, once, for exactly its own
duration.

  A at 16 fps: events at k/16 for k in 0..n_a-1
  B at 20 fps: events at j/20 for j in 0..n_b-1
  composite:   the sorted union of those instants

**Integer milliseconds, with the drift corrected rather than accumulated.** WebP and APNG
carry per-frame delays in whole milliseconds, and 1/16 s is 62.5 of them. Rounding each
delay independently would drift by half a millisecond per frame — 32 ms over four seconds,
half a frame — so each delay is computed as the difference between the ROUNDED cumulative
times of consecutive events. The error is then bounded by one millisecond for the whole
clip instead of growing with it.

Compensator (NAMED_COMPENSATORS): writes one clip and one sidecar under `outputs/`.
Compensator: delete them; owner: the executor session. The frames are read-only.

Prints `MAKE_AB_CLIP_OK`.
"""

import argparse
import json
import math
import os

from PIL import Image, ImageDraw

TOOL_VERSION = "E10.1"


def frame_paths(directory):
    """The numbered frames, in index order — never a contact strip that shares the dir."""
    names = [n for n in os.listdir(directory)
             if n.lower().endswith(".png") and os.path.splitext(n)[0].isdigit()]
    if not names:
        raise SystemExit(f"{directory} carries no NNNNN.png frames")
    return [os.path.join(directory, n)
            for n in sorted(names, key=lambda n: int(os.path.splitext(n)[0]))]


def event_timeline(n_a, fps_a, n_b, fps_b):
    """`[(t_seconds, index_into_a, index_into_b)]` — the union of both arms' frame times.

    Each entry says which frame of each arm is on screen from that instant until the next.
    A time that both arms share appears ONCE, which is why the composite of a 65-frame and
    an 81-frame arm over the same four seconds is 129 frames and not 146.

    **`floor`, not `round`** — the index is the frame that has already STARTED, which is
    what "hold" means. Rounding snaps to the nearest frame boundary instead: at t = 0.05 s
    a 16 fps arm would jump to its frame 1, which does not begin until 0.0625 s, so one
    side would run a fraction of a frame ahead of its own tempo for the whole clip. Caught
    by `test_each_side_holds_its_own_frame_between_its_own_events`, 2026-08-12.
    """
    times = sorted({k / float(fps_a) for k in range(n_a)}
                   | {j / float(fps_b) for j in range(n_b)})
    out = []
    for t in times:
        ia = min(n_a - 1, int(math.floor(t * fps_a + 1e-9)))
        ib = min(n_b - 1, int(math.floor(t * fps_b + 1e-9)))
        out.append((t, ia, ib))
    return out


def durations_ms(times, tail_s):
    """Per-event delays in whole ms, from the ROUNDED cumulative times.

    `tail_s` is how long the last composite frame stays up — the longer of the two arms'
    remaining frame times, so neither clip is cut short.
    """
    edges = [round(t * 1000.0) for t in times] + [round((times[-1] + tail_s) * 1000.0)]
    return [edges[i + 1] - edges[i] for i in range(len(edges) - 1)]


def banner(im, text, height=22):
    """A caption strip above a panel, so a still cut from the clip still says what it is."""
    out = Image.new("RGB", (im.width, im.height + height), (0, 0, 0))
    out.paste(im, (0, height))
    ImageDraw.Draw(out).text((6, 6), text, fill=(235, 235, 235))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--a-fps", type=float, required=True)
    ap.add_argument("--b-fps", type=float, required=True)
    ap.add_argument("--a-label", default="A")
    ap.add_argument("--b-label", default="B")
    ap.add_argument("--out", required=True)
    ap.add_argument("--lossless", type=int, default=1,
                    help="1 writes a lossless WebP; 0 writes quality 95. Recorded either "
                         "way — the measurement source is the PNGs, never this file")
    a = ap.parse_args(argv)

    pa, pb = frame_paths(a.a), frame_paths(a.b)
    ia_frames = [Image.open(p).convert("RGB") for p in pa]
    ib_frames = [Image.open(p).convert("RGB") for p in pb]

    times = event_timeline(len(pa), a.a_fps, len(pb), a.b_fps)
    tail = max(1.0 / a.a_fps, 1.0 / a.b_fps)
    delays = durations_ms([t for t, _x, _y in times], tail)

    label_a = f"{a.a_label}"
    label_b = f"{a.b_label}"
    comps = []
    for (t, x, y), _d in zip(times, delays):
        left = banner(ia_frames[x], f"{label_a}   f{x}   t={t:.3f}s")
        right = banner(ib_frames[y], f"{label_b}   f{y}   t={t:.3f}s")
        h = max(left.height, right.height)
        canvas = Image.new("RGB", (left.width + right.width + 8, h), (0, 0, 0))
        canvas.paste(left, (0, 0))
        canvas.paste(right, (left.width + 8, 0))
        comps.append(canvas)

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    comps[0].save(a.out, save_all=True, append_images=comps[1:], duration=delays, loop=0,
                  lossless=bool(a.lossless), quality=100 if a.lossless else 95)

    side = os.path.splitext(a.out)[0] + "_manifest.json"
    with open(side, "w", encoding="utf-8") as fh:
        json.dump({
            "tool": "make_ab_clip", "tool_version": TOOL_VERSION,
            "a": {"dir": os.path.abspath(a.a), "frames": len(pa), "fps": a.a_fps,
                  "label": label_a,
                  "clip_s_frames_over_fps": len(pa) / a.a_fps,
                  "span_s_first_to_last_frame": (len(pa) - 1) / a.a_fps},
            "b": {"dir": os.path.abspath(a.b), "frames": len(pb), "fps": a.b_fps,
                  "label": label_b,
                  "clip_s_frames_over_fps": len(pb) / a.b_fps,
                  "span_s_first_to_last_frame": (len(pb) - 1) / a.b_fps},
            "composite": {"frames": len(comps), "total_ms": sum(delays),
                          "lossless": bool(a.lossless),
                          "rule": ("union of both arms' frame times; each side holds its "
                                   "own frame between its own events. NEITHER arm is "
                                   "resampled or retimed")},
            "delays_ms_first16": delays[:16],
        }, fh, indent=2)

    print("MAKE_AB_CLIP_OK " + json.dumps({
        "out": os.path.abspath(a.out), "composite_frames": len(comps),
        "total_s": sum(delays) / 1000.0,
        "a": {"frames": len(pa), "fps": a.a_fps, "clip_s": len(pa) / a.a_fps},
        "b": {"frames": len(pb), "fps": a.b_fps, "clip_s": len(pb) / a.b_fps},
        "manifest": side}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
