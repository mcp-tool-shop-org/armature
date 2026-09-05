#!/usr/bin/env python
"""pack_pose_webp — the pose-stick frames as ONE lossless animated WebP.

    python tools\\pack_pose_webp.py --frames=<sticks dir> --out=<dir> [--fps=16]

**Why this bridge instead of N x LoadImage.** E02's bridge was 33 `LoadImage` nodes into a
`BatchImagesNode`, and it works. At 65 frames on a hosted session it is 65 minted upload
URLs and 65 PUTs, and every one of them is a place for a frame to go missing quietly — which
is why Gate B exists at all.

`LoadImage` already does this job. Read from `ComfyUI/nodes.py` (fetched 2026-08-12,
sha256 fb38cf4f...): it first tries `InputImpl.VideoFromFile(path).get_components()` and
returns that image batch when it has frames; otherwise it falls through to a PIL
`ImageSequence.Iterator` loop that concatenates every frame into one batch, under a comment
naming its purpose outright — "This code is left here to handle animated webp which pyav does
not support loading". So a multi-frame WebP arrives as a 65-frame IMAGE batch from a single
upload, and `BatchImagesNode` is not needed at all.

**The whole bridge rests on the encoding being lossless, so that is gated, not assumed.**
These frames are one-pixel-wide coloured sticks on black: the thinnest possible subject for a
codec, and the palette IS the convention (G6, G10 — an off-convention driving signal fails
silently). The pack is therefore decoded straight back off disk and compared pixel for pixel
against the source PNGs by `gates.gate_r_round_trip` — the same andon E02 armed on its
encode/decode bridge — before the manifest is written. A lossy pack halts here rather than
reaching the model.

**APNG, not WebP, and that is a measurement.** Animated WebP was the first choice — it is
what `LoadImage`'s own fallback comment names — and Comfy Cloud's upload endpoint **refused
it**: `422 INVALID_IMAGE, "Uploaded input is not a valid image"` (measured 2026-08-12). The
same frames as a lossless APNG uploaded without complaint. Both encodings pass Gate R
locally, so the choice costs nothing; `--format=webp` is kept because the rejection is an
endpoint behaviour that can change, and the day it does the record should show what was tried.

**What this does NOT prove on its own**, and the report says so: that the SERVER decodes the
pack the same way. That is what the Gate B probe answers — a `SaveImage` hung off the
`LoadImage` output, counted and compared against these same source frames. Measured for this
pack 2026-08-12 on a model-free verification run (`LoadImage` -> `SaveImage`, prompt
`ef07f754-cf79-4998-8fdf-0f3d63051029`): **65 results, in order** (`batch_00001_` ...
`batch_00065_`), **pixel-identical** to the local frames at indices 0/16/32/48/64.

Compensator (NAMED_COMPENSATORS): writes a WebP and a manifest under `outputs/`.
Compensator: delete them; owner: the executor session. The frames are read-only.
"""

import argparse
import hashlib
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core import gates  # noqa: E402
from armature_core.errors import ArmatureError  # noqa: E402
from composite_reference import (  # noqa: E402
    compose_over_named_plate, parse_plate)


class PosePackError(ArmatureError):
    """The pack cannot be built honestly — the authored-RGBA law, chiefly.

    These frames ARE the submitted control batch, so `im.convert("RGB")` on an RGBA stick
    render silently submitted whatever RGB sat under alpha. Same law, same implementation
    as `fit_reference`, `make_plate` and `encode_control`.
    """

TOOL_VERSION = "E08.1"

#: The rate this pack is written at. `--fps` is `type=int`, so a non-finite spelling never
#: reaches `main`: measured in this worktree on the base tree, `--fps=nan` is refused by
#: argparse itself with `invalid int value: 'nan'` at exit 2, before `main` is entered. The
#: bound below is therefore POSITIVITY only — a `math.isfinite` clause here would be a
#: clause with no caller, which this repo arms or deletes rather than ships, and `math`
#: is not imported for a clause that does not exist. The day `--fps` becomes a float,
#: the finiteness half is `resample_motion`'s two lines, in that order (`isfinite` first,
#: because `nan > 0` is False and `inf > 0` is True).
MIN_FPS_EXCLUSIVE = 0


def single_path_segment(value, flag, exc, extra=None):
    """`value` if it names ONE path component, else raise `exc` naming the flag. · ANDON

    A `--name` is a NAME, not a path. `os.path.join(out_dir, f"{name}.{ext}")` with
    `name="../escaped"` writes OUTSIDE `--out` while every gate above it stays green and
    the manifest that certifies the artifact stays behind in `--out` — measured on the base
    tree (F-62dec63b): `PACK_POSE_PACK_OK` with `"gate_R": "identical"`, exit 0, the pack
    at `<base>/esc/escaped.apng.png` and the manifest at `<base>/esc/inner/`, so the
    directory the caller was told to read held a manifest and no pack. Gate R read the
    escaped file back and reported it identical, because Gate R compares pixels and is
    blind to where they live.

    `os.path.basename` alone is not the check: it is platform-dependent (on POSIX
    `basename("a\b")` is the whole string) and it accepts `.` and `..` unchanged. Both
    separators, the drive-relative spellings, the two dot names and an absent name are
    refused explicitly, so the same call answers the same way on either platform.

    ⚠ **This is the second spelling of one rule, not a second rule.** `resample_motion`
    carries a character-identical copy under the same clause word
    (`output_name_is_not_a_name`); the single home for it is `armature_core`, which is
    another domain's tree in the frozen map, so the helper lives beside its callers the way
    `parts.require_finite` does. The third instance in this domain — `make_review_clip`'s
    `--run`, which reaches `clip_name`'s `f"{run}_{stem}"` — is a DEFERRED Stage B item and
    is deliberately NOT fixed here.
    """
    text = "" if value is None else str(value)
    sep = {"/", "\\"} | {c for c in (os.sep, os.altsep) if c}
    if (not text.strip() or text in (".", "..") or os.path.isabs(text)
            or any(c in text for c in sep) or os.path.basename(text) != text):
        ev = {"gate": "ARGS", "andon": exc.__name__,
              "clause": "output_name_is_not_a_name", "flag": flag, "name": text}
        ev.update(extra or {})
        raise exc(
            f"{flag}={text!r} is not a name; it is pasted into the output path as one "
            f"component of a filename, so a separator, an absolute path or a dot name "
            f"writes the artifact somewhere other than the directory this tool was told to "
            f"write into, while the manifest that certifies it stays behind and every "
            f"gate above reports on the file that escaped",
            ev)
    return text


def parse_args(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True, help="directory of NNNNN.png stick frames")
    ap.add_argument("--out", required=True)
    ap.add_argument("--fps", type=int, default=16)
    ap.add_argument("--alpha-over", default=None,
                    help="R,G,B of the plate an RGBA stick frame is composited over. "
                         "Without it an alpha channel is a refusal, not a silent drop")
    ap.add_argument("--name", default="E08_pose_sticks")
    ap.add_argument("--format", default="apng", choices=("apng", "webp"),
                    help="apng is the default because Comfy Cloud's upload endpoint "
                         "refused animated WebP with 422 INVALID_IMAGE, measured 2026-08-12")
    return ap.parse_args(argv)


def frame_paths(directory):
    """The NNNNN.png frames in index order. Sorted numerically, never lexically.

    A lexical sort is right for zero-padded names and wrong the moment the padding changes,
    and a pose video in the wrong order is a performance that still looks like a
    performance — E09 measured the cost of frame order going unnoticed and built an order
    discriminator for it.
    """
    names = [f for f in os.listdir(directory)
             if f.lower().endswith(".png") and os.path.splitext(f)[0].isdigit()]
    if not names:
        raise PosePackError(
            f"no NNNNN.png frames in {directory}",
            {"gate": "FRAMES", "andon": "PosePackError",
             "clause": "no_numbered_frames_in_the_directory",
             "flag": "--frames", "frames": os.path.abspath(directory),
             "png_files": sorted(n for n in os.listdir(directory)
                                 if n.lower().endswith(".png"))[:16]})
    return [os.path.join(directory, n)
            for n in sorted(names, key=lambda s: int(os.path.splitext(s)[0]))]


def load_frames(paths, alpha_over=None):
    from PIL import Image
    out = []
    for p in paths:
        with Image.open(p) as im:
            has_alpha = im.mode in ("RGBA", "LA", "PA")
            arr = np.array(im.convert("RGBA") if has_alpha else im.convert("RGB"))
        # ---- ANDON. One implementation of the authored-RGBA law.
        rgb, _rec = compose_over_named_plate(
            arr, alpha_over, label=os.path.abspath(p), exc=PosePackError,
            extra_evidence={"frame": os.path.basename(p), "mode": im.mode,
                            "tool": "pack_pose_pack"},
            channel_order="RGB")
        out.append(np.ascontiguousarray(rgb, dtype=np.uint8))
    shapes = {a.shape for a in out}
    if len(shapes) != 1:
        raise PosePackError(
            f"the frames are not all the same size: {sorted(shapes)}. LoadImage's PIL path "
            f"SKIPS any frame whose size differs from the first, so a mixed-size pack "
            f"arrives as a short batch with nothing erroring",
            {"gate": "FRAMES", "andon": "PosePackError",
             "clause": "frames_are_not_all_one_size",
             "shapes": [list(sh) for sh in sorted(shapes)], "n_frames": len(out)})
    return out


def write_pack(frames, path, fps, fmt="apng"):
    """One lossless multi-frame image. Losslessness is the entire point of this function.

    APNG is lossless by construction. WebP is lossless only with `lossless=True`, and a
    default-quality animated WebP smears a one-pixel stick immediately — which is why
    `tests/test_pack_pose_pack.py` proves Gate R actually fires on that encoding.
    """
    from PIL import Image
    imgs = [Image.fromarray(a, mode="RGB") for a in frames]
    duration = int(round(1000.0 / fps))
    if fmt == "webp":
        imgs[0].save(path, format="WEBP", save_all=True, append_images=imgs[1:],
                     lossless=True, quality=100, method=6, duration=duration, loop=0)
    else:
        imgs[0].save(path, format="PNG", save_all=True, append_images=imgs[1:],
                     duration=duration, loop=0, default_image=False)
    return path


def read_pack(path):
    """Every frame back off disk, through the same PIL path `LoadImage` falls through to."""
    from PIL import Image, ImageSequence
    out = []
    with Image.open(path) as im:
        for frame in ImageSequence.Iterator(im):
            out.append(np.array(frame.convert("RGB"), dtype=np.uint8))
    return out


def main(argv=None):
    a = parse_args(argv)
    out_dir = os.path.abspath(a.out)

    # ---- ANDON, before anything is read or written, and far above `os.makedirs`: the
    #      pack's rate is a rate. F-6bb38028, wave 18, and the same divisor
    #      `make_review_clip` (F-e924157e) and `resample_motion` (F-981fe49d) were given a
    #      bound for in wave 16 while this tool -- the one whose output is UPLOADED as the
    #      driving signal -- was left open. Measured on the base tree in this worktree, on a
    #      4-frame stick directory: `--fps=0` raised a bare `ZeroDivisionError` at
    #      `duration = int(round(1000.0 / fps))` under BOTH `--format=apng` and
    #      `--format=webp`, naming neither the flag nor the value; `--fps=-16` raised a bare
    #      `struct.error: 'H' format requires 0 <= number <= 65535` (apng) and a bare
    #      `RuntimeError: ERROR adding frame: timestamps must be non-decreasing` (webp). In
    #      all four runs `--out` had already been created by `os.makedirs` below and was
    #      left behind EMPTY, which a later reader takes for an attempt that produced
    #      nothing rather than one that was refused.
    #
    #      The consequence the bound is really for is the one no gate downstream can see:
    #      the frame delay of the uploaded pack is `1000/--fps` ms and Gate R compares
    #      PIXELS, so on the day a Pillow version accepts a negative or absurd delay rather
    #      than refusing it, the driving signal's timing is written from a value nothing
    #      checked, under a green gate.
    if a.fps <= MIN_FPS_EXCLUSIVE:
        raise PosePackError(
            f"--fps={a.fps} is not a rate; this pack's frame delay is 1000/--fps ms, "
            f"written into the animated image the run UPLOADS and quoted in the manifest "
            f"as `encoding.duration_ms`, and Gate R compares pixels and is blind to it",
            {"gate": "ARGS", "andon": "PosePackError",
             "clause": "pack_rate_not_positive",
             "flag": "--fps", "value": a.fps,
             "minimum_exclusive": MIN_FPS_EXCLUSIVE})

    # ---- ANDON, the same block: `--name` is a NAME. F-62dec63b, wave 18.
    single_path_segment(a.name, "--name", PosePackError,
                        extra={"tool": "pack_pose_pack", "out": out_dir})

    paths = frame_paths(a.frames)
    frames = load_frames(paths, alpha_over=parse_plate(a.alpha_over, PosePackError))
    # WAVE-12 MERGE (coordinator, 2026-09-04): created below the frame refusals (a missing or unreadable frame leaves
    # nothing on disk); Gate R below reads back the pack this tool writes.
    os.makedirs(out_dir, exist_ok=True)
    ext = "apng.png" if a.format == "apng" else "webp"
    dst = os.path.join(out_dir, f"{a.name}.{ext}")
    write_pack(frames, dst, a.fps, a.format)

    decoded = read_pack(dst)
    # Gate R · ANDON — the same andon E02 armed on its bridge. Per-channel, and it raises.
    gate_r = gates.gate_r_round_trip(frames, decoded,
                                     source_label=f"{len(frames)} stick PNGs",
                                     decoded_label=f"{os.path.basename(dst)} re-decoded")

    with open(dst, "rb") as fh:
        raw = fh.read()
    manifest = {
        "tool": "pack_pose_pack", "tool_version": TOOL_VERSION,
        "pack": {"path": dst, "sha256": hashlib.sha256(raw).hexdigest(),
                 "bytes": len(raw)},
        "frames": len(frames),
        "resolution": [int(frames[0].shape[1]), int(frames[0].shape[0])],
        "fps": a.fps,
        "encoding": {"format": a.format, "lossless": True,
                     "duration_ms": int(round(1000.0 / a.fps)),
                     "webp_rejected_by_endpoint": ("422 INVALID_IMAGE from the Comfy Cloud "
                                                  "upload endpoint, measured 2026-08-12")},
        "source_frames": [{"path": p,
                           "sha256": hashlib.sha256(open(p, "rb").read()).hexdigest()}
                          for p in paths],
        "gates": {"R": gate_r},
        "what_this_does_not_prove": (
            "that the SERVER decodes this pack the same way. LoadImage's PIL fallback is "
            "the path read from ComfyUI/nodes.py, but the run has to demonstrate it: the "
            "Gate B probe saves the batch as the conditioning node received it, to be "
            "counted and compared against these source frames."),
    }
    mpath = os.path.join(out_dir, "pose_pack_manifest.json")
    with open(mpath, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)

    print("PACK_POSE_PACK_OK " + json.dumps({
        "pack": dst, "format": a.format, "frames": len(frames), "bytes": len(raw),
        "sha256": manifest["pack"]["sha256"][:32],
        "gate_R": gate_r["verdict"], "manifest": mpath}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
