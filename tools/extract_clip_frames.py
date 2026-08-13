#!/usr/bin/env python
"""extract_clip_frames — a generated clip to lossless per-frame PNGs, with its stream facts.

    <venv-python> tools\\extract_clip_frames.py --clip=<mp4> --out=<dir> [--label=A1-seed1]

CLAUDE.md: **video is judged in motion AND as frames.** A clip that reads well at speed can
carry a melted hand in every frame, so the frames have to exist as files before anything is
judged or sheeted. This writes them losslessly and records what the container actually said
rather than what the request asked for — a 720P request and a 1280x720 stream are two
different facts, and only the second one is measured.

`encode_control.FFMPEG` is the repo's pinned binary; the dimensions are read off the stream
rather than supplied, because supplying them is how a decode silently reshapes.

Compensator (NAMED_COMPENSATORS): writes PNGs + JSON under `outputs/`. Compensator: delete
the directory; owner: the executor session. The clip is read-only.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core.errors import ArmatureError  # noqa: E402
from encode_control import FFMPEG, decode  # noqa: E402

TOOL_VERSION = "E13.1"

#: `1280x720` in an ffmpeg stream line, guarded on both sides so a bitrate or a timebase
#: cannot match it.
DIM = re.compile(r"[,\s](\d{2,5})x(\d{2,5})[,\s]")
FPS = re.compile(r"([\d.]+)\s+fps")


class ClipReadError(ArmatureError):
    """The clip's stream could not be read, so nothing downstream may quote its numbers."""

    gate = "CLIP_READ"


def probe(path):
    """Width, height, fps and the raw stream line, from ffmpeg's own report."""
    proc = subprocess.run([FFMPEG, "-hide_banner", "-i", path],
                          capture_output=True, text=True)
    line = next((l.strip() for l in proc.stderr.splitlines()
                 if "Stream #" in l and "Video:" in l), None)
    if line is None:
        raise ClipReadError(
            f"no video stream line in ffmpeg's report for {path}. Every number below this "
            f"point would describe a decode nobody could check",
            {"stderr_tail": proc.stderr[-800:]})
    dim = DIM.search(line)
    fps = FPS.search(line)
    if not dim:
        raise ClipReadError(f"no WxH in the stream line: {line!r}", {"line": line})
    duration = next((l.strip() for l in proc.stderr.splitlines() if "Duration:" in l), None)
    return {"line": line, "width": int(dim.group(1)), "height": int(dim.group(2)),
            "fps": float(fps.group(1)) if fps else None, "duration_line": duration}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--clip", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", default=None)
    a = ap.parse_args(argv)

    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)          # scripts create their own output directories

    stream = probe(a.clip)
    frames = decode(a.clip, stream["width"], stream["height"])
    if not frames:
        raise ClipReadError(f"{a.clip} decoded to zero frames", {"stream": stream})

    hashes = {}
    for i, f in enumerate(frames):
        name = f"{i:05d}.png"
        Image.fromarray(f).save(os.path.join(out, name))
        hashes[name] = hashlib.sha256(
            open(os.path.join(out, name), "rb").read()).hexdigest()

    with open(a.clip, "rb") as fh:
        clip_sha = hashlib.sha256(fh.read()).hexdigest()
    record = {
        "tool": "extract_clip_frames", "tool_version": TOOL_VERSION,
        "label": a.label or os.path.basename(a.clip),
        "clip": os.path.abspath(a.clip), "clip_sha256": clip_sha,
        "clip_bytes": os.path.getsize(a.clip),
        "stream": stream, "n_frames": len(frames),
        "distinct_frames": len(set(hashes.values())),
        "frame_sha256": hashes, "ffmpeg": FFMPEG,
    }
    with open(os.path.join(out, "frames.json"), "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=1)

    print(f"stream   {stream['line']}")
    print(f"frames   {len(frames)}  distinct {record['distinct_frames']}")
    print(f"size     {stream['width']}x{stream['height']}  fps {stream['fps']}")
    print(f"EXTRACT_OK {out}")
    return record


if __name__ == "__main__":
    main()
