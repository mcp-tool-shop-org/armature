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

from armature_core.errors import ArmatureError  # noqa: E402
from measure_lift import as_pairing_rows as ML_as_pairing_rows  # noqa: E402
from measure_lift import gate_listing_pairing  # noqa: E402
from sheet_compose import frames_by_number, require_frames  # noqa: E402


class ReviewClipError(ArmatureError):
    """This review pass cannot be written where it was pointed.

    One typed refusal for this tool, carrying an evidence dict, rather than the bare
    `SystemExit` string the frame check used to raise.
    """


#: The directory names a run's frame population canonically lives under, so that `<run>`
#: is the frames directory's PARENT. Recorded rather than guessed: the run token is derived
#: only when the layout it is derived from is the one that carries it.
FRAME_SUBDIR_NAMES = ("lossless", "frames")

#: What the record says when no run token could be derived. The repo's rule: a value the
#: inputs do not carry prints as missing, never as a plausible default -- and the review
#: clip's FILENAME is a label the Director opens.
NO_RUN_TOKEN = "NOT DERIVED"


def run_token(frames_dir, explicit=None):
    """`(token, source)` -- the run this review pass is OF, or `(None, 'NOT DERIVED')`.

    F-78f49c7c, wave 16. `clip_name` returned `review_{rate:.2f}x_{fps}fps.webp` with no run
    token, and `fetch_run.derived_root_artifacts(run)`'s second pattern --
    `^review_[0-9.]+x_[0-9]+fps[.][a-z0-9]+$` -- therefore could not be bound to the run.
    That module's own CORRECTION block measures it (`derived_root_artifacts('A2')`:
    `A0r1_review_8fps.mp4` matches neither pattern, `review_0.50x_8fps.mp4` matches pattern
    1 and so exempts ANY run's review clip) and names this tool as the owner of the fix.
    Today's live consequence is nil -- the canonical suffix is `.webp` and `VIDEO_SUFFIXES`
    is (.mp4, .webm, .mkv) -- but the pattern exists to survive a change of suffix, and on
    that day a PREVIOUS run's review clip in a re-used run root is exempted rather than
    raised: the exact stray class the sweep was added for.

    **It is derived from `--frames`, not from `--out`.** The wave-16 brief said "derive the
    token from `--out`'s run directory"; that cannot be done here, for a reason
    `gate_out_directory` below measures: `--out` is REFUSED when it is the frames directory
    or when it already holds a numbered frame population, so `--out` is by construction a
    review directory of its own and its parent is not run-shaped. `--frames` is the run's
    own `<run>/lossless/`, so the run is that directory's parent -- and the derivation fires
    only when the frames directory is actually named like a frame population, because a
    token pasted onto a filename from a directory that is not a run is a placeholder shaped
    like evidence. `--run=<token>` states it explicitly and wins.
    """
    if explicit is not None and str(explicit).strip():
        # ---- ANDON, where the token becomes a NAME rather than where it is read.
        #      F-03bf2b7e, wave 22. `--run` (added wave 16) was pasted into the output
        #      FILENAME unvalidated: `run_token` returned `str(explicit).strip()`,
        #      `clip_name` returned `f"{run}_{stem}"`, and `main` joined that onto `--out`.
        #      Measured on `e8263a3` on a 3-frame `<base>/A2/lossless`:
        #      `--out=<base>/review --run=../A2/lossless/A2` wrote
        #      `A2_review_0.50x_8fps.webp` INTO the run's own numbered-frame directory
        #      (`lossless/` then held `00000.png, 00001.png, 00002.png` and the clip),
        #      printed `MAKE_REVIEW_CLIP_OK` and returned 0 — so the andon landed in wave 16
        #      to prevent exactly that outcome (`gate_out_directory`, which refuses that
        #      destination when it is asked for directly) was walked past by a flag landed
        #      in the same wave: the gate inspects `--out` only, and the write is `--out`
        #      plus an operator string. A second measurement, `--run=outputs/E09/A2` — a
        #      directory-shaped run name, which is how a run is spelled everywhere else on
        #      this rig — died with a bare `FileNotFoundError` naming a path with mixed
        #      separators, AFTER `os.makedirs(a.out)` had created the review directory: the
        #      empty-directory residue the ordering comment in `main` exists to prevent.
        #      In both cases the sentinel and `review_manifest.json` recorded `clip` as an
        #      un-normalised `<out>/../...` string.
        #
        #      The DERIVED branch below already returns a basename and is unaffected.
        # WAVE 22, SEAM 1: the ONE home for this check, adopted BY IMPORT (the two
        # byte-identical copies this domain held are deleted). The import is at the
        # CALL SITE rather than at module scope for one reason, stated so it is not
        # read as a cycle break: the helper lands on core-solvers' branch in the same
        # parallel wave, and a module-scope import makes this file uncollectable on
        # any tree where that branch has not merged yet. Same object either way.
        from armature_core.parts import single_path_segment

        return single_path_segment(
            str(explicit).strip(), "--run", ReviewClipError,
            extra={"tool": "make_review_clip", "frames": os.path.abspath(frames_dir),
                   "pasted_into": "the review clip's FILENAME, as f'{run}_{stem}'"}), "--run"
    frames_abs = os.path.abspath(frames_dir)
    if os.path.basename(frames_abs).lower() in FRAME_SUBDIR_NAMES:
        parent = os.path.basename(os.path.dirname(frames_abs))
        if parent:
            return parent, "frames_parent"
    return None, NO_RUN_TOKEN


def gate_out_directory(out, frames_dir):
    """ANDON — `--out` is a review directory, not the run it is reading.

    Measured 2026-09-04: `--frames=<dir> --out=<same dir>` on a 5-frame `lossless/` with
    `--stills=0,4` exited 0 and left `review_0.50x_8fps.webp`, `review_manifest.json` and
    EIGHT `still_f00*.png` beside `00000..00004.png`. `measure_floor.frame_population` then
    refused that directory ("holds 8 PNG(s) that are not numbered frames") and
    `measure_clip.frame_paths` silently dropped all eight — so a review pass pointed at a
    run's own fetched frames leaves that population unusable for every stray-refusing
    instrument, and halts a later `verify_downloads` re-check on files the fetcher cannot
    attribute to anything.

    The refusal is here rather than a widening of the fetcher's sweep: the canonical name
    is `review_<rate>x_<fps>fps.webp` under a dedicated review directory, which is what
    every report on the rig records (E09, E10, E11), and teaching the run-root andon to
    tolerate a review artifact would teach it to accept a file that does not belong there.
    """
    out_abs = os.path.abspath(out)
    frames_abs = os.path.abspath(frames_dir)
    ev = {"gate": "OUT", "out": out_abs, "frames": frames_abs,
          "convention": "review_<rate>x_<fps>fps.webp under a directory of its own"}
    if out_abs == frames_abs:
        raise ReviewClipError(
            f"--out {out_abs} is the frames directory itself; the clip, the manifest and "
            f"one still per index per target would be written in among the run's numbered "
            f"frames, where every stray-refusing instrument then halts on them", ev)
    if os.path.isdir(out_abs):
        numbered = sorted(n for n in os.listdir(out_abs)
                          if n.lower().endswith(".png")
                          and os.path.splitext(n)[0].isdigit())
        has_urls = os.path.exists(os.path.join(out_abs, "urls.json"))
        if numbered or has_urls:
            raise ReviewClipError(
                f"--out {out_abs} already holds "
                f"{len(numbered)} numbered frame(s)"
                f"{' and a urls.json' if has_urls else ''}; it is a run directory, and the "
                f"stills would sort in beside its population",
                dict(ev, numbered_frames=numbered[:16], urls_json=has_urls))
    ev["verdict"] = "a review directory of its own"
    return ev


def clip_name(fps, source_fps, run=None):
    """`review_<rate>x_<fps>fps.webp`, from the actual numbers.

    The name was the literal `review_0.5x_8fps.webp` whatever the flags said, which was
    true only while every source ran at 16 fps. On a 20 fps source the same file is 0.40x
    at 8 fps and the filename asserted otherwise — a label on an artifact the Director
    opens is evidence, and it may not be a placeholder. Corrected E10, 2026-08-12.

    WAVE 16 (F-78f49c7c): the run token is prefixed when one is KNOWN, so a review clip
    carries the identity of the generation it reviews and a run-root sweep can bind its
    exemption to the run instead of exempting every run's clip. When no token could be
    derived the name is unchanged - an un-tokened name is the honest one, and pasting a
    directory name that is not a run onto the file would be the placeholder this tool's own
    history is about. See `run_token`.
    """
    stem = f"review_{fps / float(source_fps):.2f}x_{fps}fps.webp"
    return f"{run}_{stem}" if run else stem


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--detection", default=None)
    ap.add_argument("--fps", type=int, default=8,
                    help="playback rate; 8 against a 16 fps source is 0.5x")
    ap.add_argument("--source-fps", type=int, default=16)
    ap.add_argument("--run", default=None,
                    help="the run this review pass is OF; prefixed onto the clip's name so "
                         "a run-root sweep can bind its exemption to the run. Derived from "
                         "--frames' own run root when not given")
    ap.add_argument("--stills", default="0,16,32,48,64")
    ap.add_argument("--crop", type=int, default=224, help="still crop size, native pixels")
    a = ap.parse_args(argv)

    # ---- ANDON, before anything is read or made, and far above `os.makedirs`: both rates
    #      are rates. F-e924157e, wave 16. `--fps=0` reached
    #      `duration=int(round(1000.0 / a.fps))` inside `ims[0].save(...)` and died with a
    #      bare `ZeroDivisionError` -- untyped, and AFTER `os.makedirs(a.out)` had created
    #      the review directory, so a refused run left an empty directory a later reader
    #      takes for an attempt that produced nothing. `--source-fps=0` dies one line later,
    #      in `a.fps / float(a.source_fps)` and in `clip_name` -- which is the FILENAME the
    #      Director opens. A negative rate is worse than either: `int(round(1000.0 / -8))`
    #      is a negative frame delay written into a WebP.
    for _flag, _value in (("--fps", a.fps), ("--source-fps", a.source_fps)):
        if _value <= 0:
            raise ReviewClipError(
                f"{_flag}={_value} is not a rate; the clip's frame delay is "
                f"1000/--fps ms and both the clip's name and its manifest quote "
                f"--fps and --source-fps as a playback rate",
                {"gate": "ARGS", "andon": "ReviewClipError",
                 "clause": "playback_rate_not_positive",
                 "flag": _flag, "value": _value, "minimum_exclusive": 0})

    # ---- ANDON: this review pass is not being written into the run it is reading.
    gate_out = gate_out_directory(a.out, a.frames)
    token, token_source = run_token(a.frames, a.run)

    names = sorted(f for f in os.listdir(a.frames)
                   if f.lower().endswith(".png") and os.path.splitext(f)[0].isdigit())
    if not names:
        raise ReviewClipError(
            f"no numbered frames in {a.frames}; there is nothing to review",
            {"gate": "FRAMES", "frames": os.path.abspath(a.frames),
             "png_files": sorted(n for n in os.listdir(a.frames)
                                 if n.lower().endswith(".png"))[:16]})
    ims = [Image.open(os.path.join(a.frames, n)).convert("RGB") for n in names]
    # `{frame NUMBER: position in the listing}` — the stills are asked for by number and
    # were cut by position (wave 12): on a run numbered 00001..00003, `--stills=0` cut
    # `still_f000_*` out of `00001.png` and recorded `"frame": 0`, a frame the run does
    # not hold, while `--stills=3` was refused.
    by_number = frames_by_number(names, where=a.frames, what="clip frame(s)")
    at = {n: names.index(name) for n, name in by_number.items()}

    det = None
    if a.detection:
        with open(a.detection, encoding="utf-8") as fh:
            det = json.load(fh)["rows"]
        # ---- ANDON. The rows describe THESE frames, by frame number — not by position.
        gate_listing_pairing({"frames": names, "detection": det})
        det_by_number = {}
        for _row, _pr in zip(det, ML_as_pairing_rows(det)):
            _stem = os.path.splitext(str(_pr["file"]))[0]
            if _stem.isdigit():
                det_by_number[int(_stem)] = _row

    idx = [int(v) for v in a.stills.split(",") if v.strip() != ""]
    # ---- every requested still NUMBER exists. The count had no denominator, and the
    #      bound was positional.
    require_frames(idx, ims, what="clip frame(s)", where=a.frames,
                   numbers=sorted(by_number))

    # ---- the output directory is created only once every in-tool andon above has
    #      fired. A refused run that has already made its directory leaves an empty
    #      one behind, which a later reader -- or a re-run into the same --out --
    #      reads as an attempt that produced nothing rather than one that was refused.
    #      The clip used to be written between the two andons above, so a run refused
    #      by either left a directory holding a review clip and no stills.
    clip = os.path.join(a.out, clip_name(a.fps, a.source_fps, token))
    # ---- Belt and braces for the andon in `run_token` above: whatever the token
    #      was, the file this tool writes is INSIDE `--out`. A gate that cannot
    #      fail is not a gate, so this one is stated on the direction the name
    #      check does not bound — a future spelling that escapes it.
    if os.path.dirname(os.path.abspath(clip)) != os.path.abspath(a.out):
        raise ReviewClipError(
            f"the review clip would be written to {os.path.abspath(clip)}, "
            f"which is not inside --out={os.path.abspath(a.out)}",
            {"gate": "OUT", "andon": "ReviewClipError",
             "clause": "clip_would_be_written_outside_out",
             "clip": os.path.abspath(clip), "out": os.path.abspath(a.out),
             "run": token, "run_source": token_source})
    os.makedirs(a.out, exist_ok=True)
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
            if det and det_by_number[i].get("fired"):
                x, y = det_by_number[i]["image"][li]
                outside = not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0)
                cx, cy = int(x * W), int(y * H)
            else:
                outside, cx, cy = None, W // 2, H // 2
            x0 = max(0, min(W - a.crop, cx - half))
            y0 = max(0, min(H - a.crop, cy - half))
            name = f"still_f{i:03d}_{label}.png"
            ims[at[i]].crop(
                (x0, y0, x0 + a.crop, y0 + a.crop)).save(os.path.join(a.out, name))
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
                   "source_frame_files": list(names),
                   "stills_requested": idx, "n_stills_requested": len(idx),
                   "gate_OUT": gate_out,
                   "run_token": token if token else NO_RUN_TOKEN,
                   "run_token_source": token_source,
                   "stills": cuts}, fh, indent=2)
    print("MAKE_REVIEW_CLIP_OK " + json.dumps({
        "clip": clip, "run_token": token if token else NO_RUN_TOKEN,
        "frames": len(ims), "fps": a.fps,
        "rate": f"{a.fps / float(a.source_fps):.2f}x",
        "stills": len(cuts), "stills_requested": idx,
        "manifest": side}))
    return 0


if __name__ == "__main__":
    # WAVE 22, SEAM 1: the ONE `__main__` halt handler, adopted BY IMPORT from
    # `armature_core.parts` (core-solvers' file, posted to the wave-22 seams inbox). Never
    # copied — the whole point of the seam is that this block is one function with one home.
    from armature_core.parts import run_tool_main  # noqa: E402

    run_tool_main(main, "MAKE_REVIEW_CLIP")
