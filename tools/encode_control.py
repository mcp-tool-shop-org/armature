#!/usr/bin/env python
"""encode_control — build the control video and prove the bridge is lossless.

    python tools/encode_control.py --frames=<dir> --out=<video> --codec=<name>
                                   [--invert] [--survey]

E02 Stage 0. There is no folder loader on Comfy Cloud, so a control *sequence* reaches
the graph as a video file that `LoadVideo` -> `GetVideoComponents` decodes back into an
IMAGE batch. That means our frames make a round trip through an encoder, and Gate R is
the andon standing on it.

**Why this is not paranoia.** `-qp 0` is *luma*-lossless while x264 still defaults to
`yuv420p`, which subsamples chroma 4:1. Our depth, mask and edge channels are grayscale
(R=G=B, so U=V=0 and subsampling is a no-op) — they survive that untouched. The **normal**
channel is true RGB and would be quietly corrupted, and the video would look correct. So
a bridge certified only on depth is not certified for normal, and this tool refuses to
let that confusion happen silently: `--survey` reports every candidate encoding against
*both* a grayscale and a true-RGB probe, and the gate fires on the one actually used.

**Diagnostic and gate are different objects** (CLAUDE.md). `survey_codecs` measures and
returns a table; `gates.gate_r_round_trip` raises. The survey never decides anything.

**What the input side refuses, and why Gate R cannot cover it.** Gate R compares the frames
this tool loaded against their decode, so anything that happened *while loading* is invisible
to it — the corruption is on both sides of the comparison. Three such things are refused here
instead, in `frame_population` and `read_frames`: a PNG the frame numbering does not name
(the stick renderer's `strip_every{N}.png` contact sheet sorts last and becomes the final
frame of the control), an alpha channel with no named plate (the Director's 2026-08-12 law —
the RGB composite a route submits is a deliberate, recorded choice), and a non-uint8 dtype
(the old cast wrapped 16-bit levels mod 256). The receipt records the modes, the dtype, and
the alpha disposition, because the frame hash it carries is of the already-coerced array.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core import gates, shotspec  # noqa: E402
from composite_reference import compose_over_named_plate, parse_plate  # noqa: E402
from armature_core.errors import ArmatureError  # noqa: E402

FFMPEG = os.environ.get(
    "ARMATURE_FFMPEG",
    r"E:\AI-Models\trellis2-env\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe",
)

# Candidate bridges, in the order the spec prefers them. `container` matters as much as
# the codec: FFV1 needs a container that will carry it, and mp4 will not.
CODECS = {
    "ffv1-gbrp": {
        "args": ["-c:v", "ffv1", "-pix_fmt", "gbrp"],
        "ext": ".mkv",
        "note": "the spec's stated preference",
    },
    "ffv1-bgr0": {
        "args": ["-c:v", "ffv1", "-pix_fmt", "bgr0"],
        "ext": ".mkv",
        "note": "8-bit packed RGB; this build's ffv1 lists bgr0 but not plain gbrp",
    },
    "x264rgb-qp0": {
        "args": ["-c:v", "libx264rgb", "-qp", "0", "-pix_fmt", "bgr0"],
        "ext": ".mkv",
        "note": "H.264 in an RGB colour space - no YUV conversion at all",
    },
    "x264-qp0-yuv444": {
        "args": ["-c:v", "libx264", "-qp", "0", "-pix_fmt", "yuv444p"],
        "ext": ".mp4",
        "note": "the spec's named fallback; YUV but not subsampled",
    },
    "x264-qp0-yuv420": {
        "args": ["-c:v", "libx264", "-qp", "0", "-pix_fmt", "yuv420p"],
        "ext": ".mp4",
        "note": "THE TRAP. Included so the failure is measured here, not inferred.",
    },
}


class EncodeFailure(ArmatureError):
    """The frames are not what this bridge encodes, or ffmpeg could not carry them.

    Carries an evidence dict for the same reason every gate in this repo does: the
    measurement that fired the refusal is the useful half of it.
    """

    def __init__(self, message, evidence=None):
        super().__init__(message)
        self.evidence = evidence or {}


def _run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, **kw)


def frame_population(frames_dir, expect=None):
    """The NUMBERED frames of a channel directory, in index order, and a refusal for
    every other PNG beside them.

    **Numbered, not merely `*.png`, and strays raise rather than being filtered.**
    `render_pose_sticks` writes a `strip_every{N}.png` contact sheet into the very
    directory it just filled with `NNNNN.png` frames. Under the old bare listdir that
    stray sorted last and became the final frame of the encoded control — while
    `gates.g2_completeness` iterated the EXPECTED names and reported `present: 5,
    expected: 5, missing: []`, and Gate R compared the same six-frame population
    against its own decode and passed as well. Measured 2026-09-03.

    Filtering silently (what `gate_b_frames.frame_paths` does, for a diagnostic that
    opens no credit) is not enough here: this population becomes an upload. A
    directory holding a file this tool cannot name is a directory whose contents
    nobody has stated, so it raises and carries the strays as evidence.

    `expect` pins the population to the spec's own names — `shotspec.frame_names` — so
    a short or renumbered directory is a refusal rather than a shorter video.
    """
    if not os.path.isdir(frames_dir):
        raise EncodeFailure(f"{frames_dir} is not a directory of frames",
                            {"frames_dir": frames_dir})
    pngs = sorted(n for n in os.listdir(frames_dir) if n.lower().endswith(".png"))
    numbered = [n for n in pngs if os.path.splitext(n)[0].isdigit()]
    unexpected = [n for n in pngs if n not in set(numbered)]
    names = sorted(numbered, key=lambda n: int(os.path.splitext(n)[0]))
    if unexpected:
        raise EncodeFailure(
            f"{frames_dir} holds {len(unexpected)} PNG(s) that are not numbered frames "
            f"({', '.join(unexpected[:8])}); a stray sorts into the population and "
            f"becomes a frame of the encoded control with every gate green",
            {"frames_dir": frames_dir, "unexpected": unexpected, "frames": names},
        )
    if not names:
        raise EncodeFailure(
            f"no NNNNN.png frames in {frames_dir}; there is nothing to encode",
            {"frames_dir": frames_dir, "png_files": pngs},
        )
    if expect is not None:
        want = shotspec.frame_names(expect, "png")
        if names != want:
            raise EncodeFailure(
                f"{frames_dir} holds {len(names)} frame(s) and the spec names "
                f"{len(want)}; the population an upload is built from must be the one "
                f"the spec declared",
                {"frames_dir": frames_dir, "found": names, "expected": want,
                 "missing": [n for n in want if n not in set(names)],
                 "unexpected": [n for n in names if n not in set(want)]},
            )
    return names


def read_frames(frames_dir, invert=False, expect=None, alpha_over=None):
    """Read a channel directory as `(names, frames, source)`.

    `frames` are (H, W, 3) uint8 RGB. Grayscale channels are replicated to R=G=B
    because that is what actually reaches the model: `GetVideoComponents` yields an
    IMAGE, which is RGB regardless of what we started with. Comparing anything else
    would be comparing the wrong object.

    **What raises, and why those directions.** The old body reshaped whatever arrived:
    `a[..., :3]` dropped a 4th channel outright and `np.ascontiguousarray(a, uint8)`
    wrapped a 16-bit level mod 256 (40000 -> 64). Both are silent all the way down —
    the receipt hashes the already-coerced array, and Gate R compares the coerced
    frames against the decode, so neither the alpha drop nor the truncation can fire a
    gate. The sibling `invert_frames._read_u8_gray` already refuses exactly these two
    inputs; this path did not, and now does.

    Alpha is the Director's law of 2026-08-12: the RGB composite a route submits is a
    **deliberate, recorded choice**. So an alpha channel raises unless `alpha_over`
    names the plate it is composited over, and `source` states what happened either
    way for the receipt to carry.
    """
    names = frame_population(frames_dir, expect=expect)
    out = []
    modes, dtypes, alpha_seen = [], [], False
    for n in names:
        path = os.path.join(frames_dir, n)
        with Image.open(path) as im:
            mode = im.mode
            if mode == "P":
                raise EncodeFailure(
                    f"{path}: mode 'P' is palette-indexed; encoding an index as a "
                    f"value is not encoding the frame",
                    {"frame": n, "mode": mode},
                )
            has_alpha = mode in ("RGBA", "LA", "PA")
            a = np.array(im.convert("RGBA") if has_alpha else im)
        if mode not in modes:
            modes.append(mode)
        if a.dtype.name not in dtypes:
            dtypes.append(a.dtype.name)
        if a.dtype != np.uint8:
            raise EncodeFailure(
                f"{path}: dtype {a.dtype}; the uint8 view of 16-bit data wraps mod 256 "
                f"(a level of 40000 becomes 64) rather than converting, and the receipt "
                f"would hash the wrapped array",
                {"frame": n, "mode": mode, "dtype": a.dtype.name,
                 "alpha_present": has_alpha},
            )
        if has_alpha:
            alpha_seen = True
            # ---- ANDON. The refusal and the composite that used to live here are now
            #      `composite_reference.compose_over_named_plate`: the same law was
            #      implemented twice and missing three times, so there is one of it.
            a, _rec = compose_over_named_plate(
                a, alpha_over,
                label=f"{path}: mode {mode!r}", exc=EncodeFailure,
                extra_evidence={"frame": n, "mode": mode, "dtype": a.dtype.name},
                channel_order="RGB")
        elif a.ndim == 2:
            a = np.repeat(a[..., None], 3, axis=2)
        elif a.ndim == 3 and a.shape[2] == 3:
            pass
        else:
            raise EncodeFailure(
                f"{path}: array shape {a.shape} is not a frame this bridge encodes",
                {"frame": n, "mode": mode, "shape": list(a.shape)},
            )
        if invert:
            a = (255 - a).astype(np.uint8)
        out.append(np.ascontiguousarray(a, dtype=np.uint8))

    source = {
        "source_modes": modes,
        "source_dtype": dtypes[0] if len(dtypes) == 1 else dtypes,
        "source_alpha_present": alpha_seen,
        "alpha_disposition": (
            f"composited over rgb{tuple(int(v) for v in alpha_over)}" if alpha_seen
            else "no alpha channel in any source frame"),
    }
    return names, out, source


def load_frames(frames_dir, invert=False, expect=None, alpha_over=None):
    """`read_frames` without the source record — the two-value form callers had."""
    names, frames, _ = read_frames(frames_dir, invert=invert, expect=expect,
                                   alpha_over=alpha_over)
    return names, frames


def encode(frames, path, codec, fps=16):
    """Write `frames` to `path` with the named codec. Raises on ffmpeg failure."""
    if codec not in CODECS:
        raise EncodeFailure(f"unknown codec {codec!r}; known: {sorted(CODECS)}")
    h, w = frames[0].shape[:2]
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    cmd = [
        FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps),
        "-i", "-",
        *CODECS[codec]["args"],
        path,
    ]
    proc = _run(cmd, input=b"".join(f.tobytes() for f in frames))
    if proc.returncode != 0 or not os.path.isfile(path):
        raise EncodeFailure(
            f"ffmpeg failed to encode {codec}: {proc.stderr.decode('utf-8', 'replace')[:500]}"
        )
    return path


def decode(path, width, height):
    """Decode a video back to a list of (H, W, 3) uint8 RGB frames.

    Decoded to rawvideo rather than to PNG files: a PNG intermediary would add a second
    codec to the thing being measured, and the question is what the *video* bridge did.
    """
    cmd = [
        FFMPEG, "-hide_banner", "-loglevel", "error",
        "-i", path, "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
    ]
    proc = _run(cmd)
    if proc.returncode != 0:
        raise EncodeFailure(
            f"ffmpeg failed to decode {path}: {proc.stderr.decode('utf-8', 'replace')[:500]}"
        )
    stride = int(width) * int(height) * 3
    raw = proc.stdout
    if stride <= 0:
        raise EncodeFailure(
            f"decode asked for a {width}x{height} frame, which has no bytes",
            {"width": width, "height": height, "stride": stride},
        )
    if len(raw) % stride:
        # `n = len(raw) // stride` drops a trailing partial frame in silence, and a byte
        # count that is not a whole number of frames is the signature of a decode at the
        # WRONG stride — a clip whose real resolution was supplied rather than read off
        # its own stream. Reinterpreted at the wrong stride the frames are garbage and
        # `n` can still land on the expected count, so nothing downstream would notice.
        raise EncodeFailure(
            f"{path} decoded to {len(raw)} bytes, which is not a whole number of "
            f"{width}x{height} RGB frames ({stride} bytes each; remainder "
            f"{len(raw) % stride}). The dimensions are wrong for this stream",
            {"path": path, "width": width, "height": height, "stride": stride,
             "n_bytes": len(raw), "remainder": len(raw) % stride},
        )
    n = len(raw) // stride
    return [
        np.frombuffer(raw[i * stride:(i + 1) * stride], dtype=np.uint8).reshape(height, width, 3)
        for i in range(n)
    ]


def _probe_pair(h=64, w=64, n=5, seed=17):
    """A grayscale probe and a true-RGB probe, for the survey.

    Two probes because one cannot answer the question. Grayscale passing proves nothing
    about the normal channel; RGB is where a chroma-lossy bridge shows itself.
    """
    rng = np.random.default_rng(seed)
    gray = rng.integers(0, 256, size=(n, h, w), dtype=np.uint8)
    return (
        [np.repeat(g[..., None], 3, axis=2).copy() for g in gray],
        list(rng.integers(0, 256, size=(n, h, w, 3), dtype=np.uint8)),
    )


def survey_codecs():
    """DIAGNOSTIC — measure every candidate bridge. Decides nothing, raises nothing."""
    gray, colour = _probe_pair()
    h, w = gray[0].shape[:2]
    rows = []
    with tempfile.TemporaryDirectory() as td:
        for name, spec in CODECS.items():
            row = {"codec": name, "note": spec["note"], "container": spec["ext"]}
            for label, probe in (("grayscale", gray), ("rgb", colour)):
                try:
                    p = os.path.join(td, f"{name}-{label}{spec['ext']}")
                    encode(probe, p, name)
                    back = decode(p, w, h)
                    if len(back) != len(probe):
                        row[label] = f"FRAME COUNT {len(probe)} -> {len(back)}"
                        continue
                    d = max(
                        int(np.abs(a.astype(np.int16) - b.astype(np.int16)).max())
                        for a, b in zip(probe, back)
                    )
                    row[label] = "lossless" if d == 0 else f"max|delta|={d}"
                except EncodeFailure as e:
                    row[label] = f"UNAVAILABLE: {str(e)[:90]}"
            rows.append(row)
    return rows


def build(frames_dir, out_path, codec, invert=False, fps=16, expect=None,
          alpha_over=None):
    """Encode a control sequence and run Gate R on it. **Raises** on any difference.

    The gate is called here, inside the function that produces the artifact a later
    step will upload — not chained behind a shell `&&`, which can walk past a failing
    exit code, and not as an `assert`, which `-O` deletes.
    """
    names, frames, source = read_frames(frames_dir, invert=invert, expect=expect,
                                        alpha_over=alpha_over)
    h, w = frames[0].shape[:2]
    encode(frames, out_path, codec, fps=fps)
    decoded = decode(out_path, w, h)

    # ---- Gate R · ANDON. Nothing downstream runs if this raises.
    ev = gates.gate_r_round_trip(
        frames, decoded,
        source_label=f"{frames_dir} ({'inverted' if invert else 'as rendered'})",
        decoded_label=f"{out_path} [{codec}]",
    )

    with open(out_path, "rb") as fh:
        video_sha = hashlib.sha256(fh.read()).hexdigest()
    receipt = {
        "tool": "encode_control",
        "frames_dir": frames_dir,
        "frame_names": names,
        "n_frames": len(frames),
        "resolution": [w, h],
        "fps": fps,
        "inverted": invert,
        # What was READ, before this tool touched it. The sha256 below is of the
        # already-coerced array, so without these three lines an alpha drop or a dtype
        # truncation would leave no trace anywhere in the record.
        **source,
        "codec": codec,
        "codec_args": CODECS[codec]["args"],
        "video": out_path,
        "video_sha256": video_sha,
        "source_frames_sha256": hashlib.sha256(
            b"".join(f.tobytes() for f in frames)
        ).hexdigest(),
        "gate_R": {"verdict": "PASS", "evidence": ev},
    }
    with open(out_path + ".receipt.json", "w", encoding="utf-8") as fh:
        json.dump(receipt, fh, indent=2)
    return receipt


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames")
    ap.add_argument("--out")
    ap.add_argument("--codec", default="ffv1-gbrp")
    ap.add_argument("--fps", type=int, default=16)
    ap.add_argument("--invert", action="store_true")
    ap.add_argument("--expect", type=int, default=None,
                    help="the frame count the spec declares; the directory's numbered "
                         "frames must be exactly shotspec.frame_names(expect, 'png')")
    ap.add_argument("--alpha-over", default=None,
                    help="R,G,B of the plate an RGBA source is composited over. Without "
                         "it an alpha channel is a refusal, not a silent drop")
    ap.add_argument("--survey", action="store_true")
    ap.add_argument("--survey-out")
    args = ap.parse_args(argv)

    if args.survey:
        rows = survey_codecs()
        print(json.dumps({"survey": rows}, indent=2))
        if args.survey_out:
            os.makedirs(os.path.dirname(os.path.abspath(args.survey_out)), exist_ok=True)
            with open(args.survey_out, "w", encoding="utf-8") as fh:
                json.dump({"ffmpeg": FFMPEG, "survey": rows}, fh, indent=2)
        return 0

    if not args.frames or not args.out:
        raise SystemExit("--frames and --out are required unless --survey")
    # ---- the ONE parser. `compose_over_named_plate`'s docstring states the contract the
    #      wave-6 sweep delivered -- "there is one refusal, one composite and one record
    #      shape" -- and the composite and the record WERE one implementation while the
    #      flag parser was three. `fit_reference`, `make_plate` and `pack_pose_pack` all
    #      call `composite_reference.parse_plate` and get a typed error with an evidence
    #      dict; this reimplemented the same three-integer check inline and raised a bare
    #      `SystemExit` string, in the one tool of the four whose output is UPLOADED -- so
    #      a caller catching `EncodeFailure` around `main` did not catch it, and the halt
    #      carried none of the measurement that fired it.
    plate = parse_plate(args.alpha_over, EncodeFailure)
    receipt = build(args.frames, args.out, args.codec, invert=args.invert, fps=args.fps,
                    expect=args.expect, alpha_over=plate)
    print("ENCODE_CONTROL " + json.dumps({
        "video": receipt["video"],
        "sha256": receipt["video_sha256"][:16],
        "n_frames": receipt["n_frames"],
        "alpha_disposition": receipt["alpha_disposition"],
        "gate_R": "PASS",
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
