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

**k and j are LISTING POSITIONS, and Gate TIMELINE is what makes that legitimate.** The
claim above — every frame of both arms shown once for exactly its own duration — held only
while each arm's file NUMBERS were the contiguous run those positions assume. Measured
2026-09-04 on an arm numbered `00000, 00001, 00003, 00004`: `f00003` was placed at
t = 0.1250 s and `f00004` at t = 0.1875 s, the instants of frames 2 and 3, so both claims
above and the manifest's own `composite.rule` were false on that input while the banner —
corrected in wave 14 to read the file's own number — said so on every frame. An OFFSET is
harmless and is not refused (wave 14 measured real arms numbered `00005..00007`); a GAP is
refused by name before the axis is built. See `gate_contiguous_numbering`.

**Integer milliseconds, with the drift corrected rather than accumulated.** WebP and APNG
carry per-frame delays in whole milliseconds, and 1/16 s is 62.5 of them. Rounding each
delay independently would drift by half a millisecond per frame — 32 ms over four seconds,
half a frame — so each delay is computed as the difference between the ROUNDED cumulative
times of consecutive events. The error is then bounded by one millisecond for the whole
clip instead of growing with it.

Compensator (NAMED_COMPENSATORS): writes one clip and one sidecar under `outputs/`.
Compensator: delete them; owner: the executor session. The frames are read-only.

Prints `MAKE_AB_CLIP_OK`.
Halt contract: exit 0 on success, 2 on a deliberate refusal (one <TOOL>_HALT JSON line; evidence.clause is the branch word), 1 on a crash. See README §"Reading a halt" and armature_core.parts.run_tool_main.
"""

import argparse
import json
import math
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core.errors import ArmatureError  # noqa: E402
from armature_core.parts import require_finite  # noqa: E402

TOOL_VERSION = "E10.1"



HALT_EPILOG = 'Halt contract: exit 0 on success, 2 on a deliberate refusal (one <TOOL>_HALT JSON line; evidence.clause is the branch word), 1 on a crash. See README §"Reading a halt".'

class ABClipError(ArmatureError):
    """The A/B composite cannot be built as asked.

    One typed refusal for this tool, carrying an evidence dict, rather than the bare
    `SystemExit(<str>)` these checks used to raise. A bare `SystemExit` carries no
    measurement, cannot be caught by class, and is indistinguishable at the process
    boundary from argparse's own usage exit — which is the whole reason the repo's
    refusals are typed.
    """


def require_rate(flag, value):
    """ANDON — a playback rate this tool can build a time axis from.

    F-afa9c41e, wave 22. `--a-fps` / `--b-fps` are `type=float, required=True` and were
    bounded NOWHERE, while every quantity in this tool divides by them: `event_timeline`'s
    axis, `tail`, and four manifest fields. Measured on `e8263a3` on two 4-frame arms,
    `--a-fps=-16 --b-fps=16` ran to COMPLETION — it printed `MAKE_AB_CLIP_OK` with
    `"clip_s": -0.25`, exited 0, and wrote both the WebP and the manifest. The axis it
    built was

        [(-0.1875, 3, -3), (-0.125, 2, -2), (-0.0625, 1, -1), (-0.0, 0, 0),
         (0.0625, -1, 1), (0.125, -2, 2), (0.1875, -3, 3)]

    — seven composite frames for two four-frame arms, with NEGATIVE indices that
    `ia_frames[x]` resolves by Python's wrap-around to frames counted from the END. The
    banner prints the wrapped frame's OWN file number, so the caption agreed with the
    pixels and nothing on the sheet looked wrong: the two arms were silently paired
    frame-3-against-frame-1 for the whole clip, under a manifest asserting that NEITHER arm
    is resampled or retimed. Gate TIMELINE, landed in wave 16 in this same file to stop
    exactly this desynchronisation, keys on the file NUMBERS and never on the rate that
    builds the axis, so it passed. `--a-fps=0` raised a bare `ZeroDivisionError` and
    `--a-fps=nan` a bare `ValueError: cannot convert float NaN to integer`.

    **Finite FIRST, then positive** — the ordering `resample_motion` records: `nan > 0` is
    False and `inf > 0` is True, so a positivity bound alone admits both ends of the
    non-finite population. The finiteness half goes through the repo's ONE helper,
    `armature_core.parts.require_finite`, so this is not a second copy of `math.isfinite`
    with a different message; the positivity half raises here because the two clauses have
    to be distinguishable in the record.
    """
    ev = {"gate": "ARGS", "andon": "ABClipError",
          "clause": "playback_rate_not_finite", "flag": flag, "value": value}
    v = require_finite(flag, value, ABClipError, ev, positive=False)
    if v <= 0.0:
        raise ABClipError(
            f"{flag}={value!r} is not a playback rate; this tool builds its time axis as "
            f"k/{flag} for every frame k, so a rate that is zero or negative gives an axis "
            f"that runs backwards and frame indices that Python resolves by wrap-around to "
            f"frames counted from the END of the other arm",
            {"gate": "ARGS", "andon": "ABClipError",
             "clause": "playback_rate_not_positive", "flag": flag, "value": v,
             "minimum_exclusive": 0.0})
    return v


def frame_paths(directory):
    """The numbered frames, in index order — never a contact strip that shares the dir."""
    names = [n for n in os.listdir(directory)
             if n.lower().endswith(".png") and os.path.splitext(n)[0].isdigit()]
    if not names:
        raise ABClipError(
            f"{directory} carries no NNNNN.png frames; there is nothing to lay beside "
            f"the other arm",
            {"gate": "FRAMES", "frames_dir": directory,
             "png_files": sorted(n for n in os.listdir(directory)
                                 if n.lower().endswith(".png"))[:16]})
    return [os.path.join(directory, n)
            for n in sorted(names, key=lambda n: int(os.path.splitext(n)[0]))]


def frame_numbers(paths):
    """The number in each file's own NAME, in the order `frame_paths` returned them.

    The banner burned into every composite frame read `f{x}` / `f{y}`, where x and y are
    POSITIONS produced by `event_timeline` — indices into `range(n)` — not the numbers in
    the file names. Measured 2026-09-04: two arms whose files are `00005.png, 00006.png,
    00007.png` give timeline indices (0,0), (1,1), (2,2), so the clip the Director watches
    was captioned `f0 f1 f2` over frames 5, 6 and 7, and the manifest recorded only
    `frames: 3` and `fps` — nothing in the record recovered the mapping. A note taken off
    the clip ("the hand melts around f12") then names a frame that is not the file, and the
    still pulled for the sheet is the wrong one.

    This is the LABELLING half only. `make_ab_clip` pairs by TIME by design (its module
    docstring argues that at length) and is correctly outside the pairing gate.
    """
    return [int(os.path.splitext(os.path.basename(p))[0]) for p in paths]


def gate_contiguous_numbering(numbers, arm, fps):
    """ANDON — this arm's file NUMBERS are the contiguous run its POSITIONS assume.

    F-b1949407, wave 16. `event_timeline` below builds the time axis from
    `{k / fps for k in range(n)}` — LISTING POSITIONS — while the banner burned into every
    composite frame was corrected in wave 14 to read the file's own NUMBER. Nothing compared
    the two, and `frame_numbers` was recorded in the sidecar beside a `rule` string
    asserting that neither arm is retimed.

    Measured in this worktree on an arm whose files are `00000, 00001, 00003, 00004` (one
    number missing) against a contiguous 4-frame arm at the same 16 fps: the composite
    placed `f00003` at t = 0.1250 s and `f00004` at t = 0.1875 s — the instants of frames 2
    and 3 — so every frame after the gap ran one frame-time (62.5 ms) early for the rest of
    the clip while the banner correctly read `f00003`. This module's docstring ("Every frame
    of both arms is shown, once, for exactly its own duration") and the manifest's own
    `composite.rule` ("NEITHER arm is resampled or retimed") were both false on that input,
    and the Director reads the resulting desynchronisation as a difference between the arms:
    the exact corruption the tool was written to prevent.

    **An OFFSET is not the defect and is not refused.** Wave 14 measured real arms numbered
    `00005, 00006, 00007`; an arm whose numbers start anywhere and run contiguously has
    positions and numbers in exact correspondence, so its time axis is right. A GAP is what
    breaks the correspondence, and it is what this refuses.

    The pairing question is separate and stays out: this tool pairs by TIME by design (its
    module docstring argues that at length) and is correctly outside `measure_lift`'s
    positional-pairing gate.

    **The shift this refusal quotes is a FRAME TIME, and a frame time needs the rate.**
    F-070bfff3, wave 22. Until this wave the message said every frame after the gap would
    be shown `1000.0 / max(len(numbers), 1)` "ms-scale early" — 1000 divided by the FRAME
    COUNT, which is not a time. Measured on `e8263a3` by calling this gate directly: a
    4-frame arm reported "250 ms-scale early" for both a 16 fps arm (true frame time
    62.5 ms) and an 8 fps arm (true 125 ms) — the quoted number was INVARIANT to the rate —
    and a 41-frame arm at 16 fps reported "24 ms-scale early" where the truth was still
    62.5 ms. The docstring one screen above states the correct quantity, so the file
    disagreed with itself, and the evidence dict carried no `fps` and no computed shift, so
    a reader could not correct the halt record either. Both rates were in hand at both call
    sites; the gate simply did not take one. It takes one now, and the receipt states the
    shift rather than the reader inferring it.
    """
    numbers = list(numbers)
    fps = require_rate(f"{arm}-fps", fps)
    frame_time_ms = 1000.0 / fps
    ev = {"gate": "TIMELINE", "arm": arm, "numbers": numbers, "first_gap": None,
          "fps": fps, "frame_time_ms": frame_time_ms, "frames_after_the_gap": None,
          "rule": ("the time axis is built from listing POSITIONS, so the file numbers "
                   "must be the contiguous run those positions assume; an offset is fine, "
                   "a gap is not")}
    for i in range(1, len(numbers)):
        if numbers[i] != numbers[i - 1] + 1:
            ev["first_gap"] = [numbers[i - 1], numbers[i]]
            ev["frames_after_the_gap"] = len(numbers) - i
            raise ABClipError(
                f"{arm}'s frames are not contiguous: {numbers[i - 1]:05d} is followed by "
                f"{numbers[i]:05d}. The composite's time axis is built from listing "
                f"positions, so each of the {len(numbers) - i} frames after that gap would "
                f"be shown one frame-time ({frame_time_ms:.1f} ms at {fps:g} fps) early "
                f"against its own banner, and the two arms would run out of step for the "
                f"rest of the clip — which is read as a difference between the arms",
                ev)
    ev["verdict"] = (f"contiguous from {numbers[0]}" if numbers
                     else "no frames")
    return ev


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

    **It bounds its own rates.** F-afa9c41e's fix bounds both flags in `main`, and this
    function refuses independently so the invariant — no index this returns is negative —
    does not depend on one caller having checked first.
    """
    fps_a = require_rate("--a-fps", fps_a)
    fps_b = require_rate("--b-fps", fps_b)
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


def _ellipsize(draw, text, max_w, font=None):
    """Shorten `text` with an ellipsis so its rendered width fits `max_w` (F-7cf7e22f)."""
    kwargs = {"font": font} if font is not None else {}
    if draw.textlength(text, **kwargs) <= max_w:
        return text
    if max_w <= 0:
        return ""
    ell = "..."
    if draw.textlength(ell, **kwargs) > max_w:
        return ""
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        candidate = text[:mid].rstrip() + ell
        if draw.textlength(candidate, **kwargs) <= max_w:
            lo = mid
        else:
            hi = mid - 1
    return (text[:lo].rstrip() + ell) if lo else ell


def banner(im, text, height=22):
    """A caption strip above a panel, so a still cut from the clip still says what it is.

    F-7cf7e22f: measure and ellipsize so a narrow panel does not crop the trailing `t=`.
    F-7f9eb100: resolved TrueType face, matching dailies sheets.
    """
    from sheet_compose import font as sheet_font

    face = sheet_font("arial.ttf", 13)
    out = Image.new("RGB", (im.width, im.height + height), (0, 0, 0))
    out.paste(im, (0, height))
    d = ImageDraw.Draw(out)
    display = _ellipsize(d, text, max(0, im.width - 12), font=face)
    d.text((6, 6), display, fill=(235, 235, 235), font=face)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="two clips side by side in one file, each played at its OWN true "
                    "tempo, for the Director to judge in motion",
        epilog=HALT_EPILOG)
    ap.add_argument("--a", required=True, help="the left clip's frame directory")
    ap.add_argument("--b", required=True, help="the right clip's frame directory")
    ap.add_argument("--a-fps", type=float, required=True,
                    help="the LEFT clip's own true rate; it is played at this rate, never "
                         "resampled to match the other side")
    ap.add_argument("--b-fps", type=float, required=True,
                    help="the RIGHT clip's own true rate")
    ap.add_argument("--a-label", default="A", help="caption drawn over the left panel")
    ap.add_argument("--b-label", default="B", help="caption drawn over the right panel")
    ap.add_argument("--out", required=True, help="the A/B file to write")
    ap.add_argument("--lossless", type=int, default=1,
                    help="1 writes a lossless WebP; 0 writes quality 95. Recorded either "
                         "way — the measurement source is the PNGs, never this file")
    a = ap.parse_args(argv)

    # ---- ANDON, before a single frame is opened and far above `os.makedirs`: both rates
    #      are playback rates. See `require_rate` for the measurement this earned.
    a_fps = require_rate("--a-fps", a.a_fps)
    b_fps = require_rate("--b-fps", a.b_fps)

    pa, pb = frame_paths(a.a), frame_paths(a.b)
    ia_frames = [Image.open(p).convert("RGB") for p in pa]
    ib_frames = [Image.open(p).convert("RGB") for p in pb]

    na, nb = frame_numbers(pa), frame_numbers(pb)
    # ---- ANDON, before the time axis exists: the numbers the banner prints are the
    #      contiguous run the axis's positions assume. Both arms, not the first one read.
    gate_a = gate_contiguous_numbering(na, "--a", a_fps)
    gate_b = gate_contiguous_numbering(nb, "--b", b_fps)
    times = event_timeline(len(pa), a_fps, len(pb), b_fps)
    tail = max(1.0 / a_fps, 1.0 / b_fps)
    delays = durations_ms([t for t, _x, _y in times], tail)

    label_a = f"{a.a_label}"
    label_b = f"{a.b_label}"
    comps = []
    for (t, x, y), _d in zip(times, delays):
        # The FILE's own number, five digits like the file itself — never the position.
        left = banner(ia_frames[x], f"{label_a}   f{na[x]:05d}   t={t:.3f}s")
        right = banner(ib_frames[y], f"{label_b}   f{nb[y]:05d}   t={t:.3f}s")
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
                  "frame_numbers": na,
                  "label": label_a,
                  "clip_s_frames_over_fps": len(pa) / a.a_fps,
                  "span_s_first_to_last_frame": (len(pa) - 1) / a.a_fps},
            "b": {"dir": os.path.abspath(a.b), "frames": len(pb), "fps": a.b_fps,
                  "frame_numbers": nb,
                  "label": label_b,
                  "clip_s_frames_over_fps": len(pb) / a.b_fps,
                  "span_s_first_to_last_frame": (len(pb) - 1) / a.b_fps},
            "composite": {"frames": len(comps), "total_ms": sum(delays),
                          "lossless": bool(a.lossless),
                          "rule": ("union of both arms' frame times; each side holds its "
                                   "own frame between its own events. NEITHER arm is "
                                   "resampled or retimed"),
                          # The receipt for that claim: the axis is built from listing
                          # positions, and Gate TIMELINE checked that each arm's own file
                          # numbers are the contiguous run those positions assume.
                          "numbering": {"a": gate_a["verdict"], "b": gate_b["verdict"]},
                          "gate_TIMELINE": {"a": gate_a, "b": gate_b}},
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
    # WAVE 25 (F-68f3fb4b): the ONE `__main__` halt handler, adopted BY IMPORT from
    # `armature_core.parts` (wave 22, SEAM 1 — core-solvers' file). This tool was one of
    # the 29 in `tests/test_instrument_exits.py::CPYTHON_HALT_CONTRACT_PENDING`: its
    # typed refusals reached the operator as a stdlib traceback at exit 1 — the code this
    # repo reserves for a crash — and the evidence dict naming the clause reached nothing.
    # Never copied; the point of the seam is that this block is one function with one home.
    from armature_core.parts import run_tool_main  # noqa: E402

    run_tool_main(main, "MAKE_AB_CLIP")
