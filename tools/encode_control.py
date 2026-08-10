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

from armature_core import gates  # noqa: E402
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
    """ffmpeg could not encode or decode with the requested settings."""


def _run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, **kw)


def load_frames(frames_dir, invert=False):
    """Read a channel directory as a list of (H, W, 3) uint8 RGB frames.

    Grayscale channels are replicated to R=G=B because that is what actually reaches
    the model: `GetVideoComponents` yields an IMAGE, which is RGB regardless of what
    we started with. Comparing anything else would be comparing the wrong object.
    """
    names = sorted(n for n in os.listdir(frames_dir) if n.lower().endswith(".png"))
    if not names:
        raise EncodeFailure(f"no PNG frames in {frames_dir}")
    out = []
    for n in names:
        a = np.array(Image.open(os.path.join(frames_dir, n)))
        if a.ndim == 2:
            a = np.repeat(a[..., None], 3, axis=2)
        elif a.shape[2] == 4:
            a = a[..., :3]
        if invert:
            a = (255 - a).astype(np.uint8)
        out.append(np.ascontiguousarray(a, dtype=np.uint8))
    return names, out


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
    stride = width * height * 3
    raw = proc.stdout
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


def build(frames_dir, out_path, codec, invert=False, fps=16):
    """Encode a control sequence and run Gate R on it. **Raises** on any difference.

    The gate is called here, inside the function that produces the artifact a later
    step will upload — not chained behind a shell `&&`, which can walk past a failing
    exit code, and not as an `assert`, which `-O` deletes.
    """
    names, frames = load_frames(frames_dir, invert=invert)
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
    receipt = build(args.frames, args.out, args.codec, invert=args.invert, fps=args.fps)
    print("ENCODE_CONTROL " + json.dumps({
        "video": receipt["video"],
        "sha256": receipt["video_sha256"][:16],
        "n_frames": receipt["n_frames"],
        "gate_R": "PASS",
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
