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
from encode_control import FFMPEG, decode, gate_ffmpeg_binary  # noqa: E402

TOOL_VERSION = "E13.1"

#: `1280x720` in an ffmpeg stream line, guarded on both sides so a bitrate or a timebase
#: cannot match it.
DIM = re.compile(r"[,\s](\d{2,5})x(\d{2,5})[,\s]")
FPS = re.compile(r"([\d.]+)\s+fps")


class ClipReadError(ArmatureError):
    """The clip's stream could not be read, so nothing downstream may quote its numbers.

    **It defines no constructor, and that is the fix — not an omission.** F-734951dc, wave
    14, said "`ArmatureError` (its base) defines none either", and that premise is FALSE on
    this tree: measured 2026-09-04 in this worktree, `armature_core/errors.py::ArmatureError.__init__` gives
    the base `__init__(self, message, evidence=None)` and stores the dict AS PASSED. The
    local override written here to work around the missing base constructor added one thing
    of its own — `evidence or {}` — which put back the very defect `errors.py:27-33` rules
    against: `"evidence": null` beside `"gate": null` is the honest halt record for a bare
    refusal, and `{}` says a receipt was built and came back empty. The override is deleted
    (wave 16), and the three raises below reach the base unchanged, receipt included.

    It is deliberately NOT re-based on `GateFailure`: the `tools/`-wide evidence ratchet in
    `tests/test_gates.py` derives its population from the live `GateFailure` subclass tree,
    so re-basing a tools-local class changes which raise sites that census examines
    depending on what has been imported.
    """

    gate = "CLIP_READ"


def probe(path):
    """Width, height, fps and the raw stream line, from ffmpeg's own report.

    **The encoder is GATED before it is run** (F-a19ebe73, wave 25). `FFMPEG` is selected at
    import from `ARMATURE_FFMPEG` with a hard-coded `E:/AI-Models` fallback, and this module
    imported the constant and ran it without arming the gate that was written for exactly
    that. Measured on `580af47` with the repo venv and `ARMATURE_FFMPEG` pointed at a path
    that does not exist: `tools/encode_control.py` exited 2 with an `ENCODE_CONTROL_HALT`
    line carrying `{"clause": "ffmpeg_binary_not_found", "from_env": true, "env_var":
    "ARMATURE_FFMPEG"}`, while `tools/extract_clip_frames.py --clip=<file> --out=<tmp>`
    exited 1 with a bare `FileNotFoundError: [WinError 2] The system cannot find the file
    specified` — naming neither the encoder, nor the variable that chose it, nor the path,
    on the one input that arrives AFTER a credit has been spent.

    `encode_control.gate_ffmpeg_binary` is the ONE home for this refusal and is adopted by
    import, never re-spelled as a local `os.path.isfile(FFMPEG)` test. This record already
    states `"ffmpeg": FFMPEG` as part of its provenance (:115); now it checks it.

    The ORDERING `encode_control.main` records is preserved: the operator's own arguments
    are refused before the encoder is inspected, so a missing rig binary cannot mask an
    argument defect. `main` parses and resolves `--out` above this call.
    """
    gate_ffmpeg_binary()
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


def _cli(argv=None):
    """The process entry point: an exit code, beside the frames record `main` returns.

    WAVE 25, F-68f3fb4b — the shape `composite_reference._cli` took in wave 22, for the
    same reason.

    `main` returns the frames record — `frames.json`'s own content — and this module ended in
    a bare `main()` with no `sys.exit` at all, the WEAKEST form in the 42-tool population:
    the returned value could never become an exit code, so neither a refusal nor a success
    was expressible. Measured on `580af47` with the repo venv: `--clip=<missing>` exited 1
    with `ClipReadError: no video stream line in ffmpeg's report` on stderr and stdout
    empty — a typed refusal on the tool that turns a PAID run's returned clip into frames,
    delivered as the code this repo reserves for a crash.

    `main` keeps returning the frames record; this wrapper is what `run_tool_main` runs, so the
    process gets 0 on success, 2 on a typed refusal and 1 on a crash.
    """
    main(argv)
    return 0


if __name__ == "__main__":
    # WAVE 25 (F-68f3fb4b): the ONE `__main__` halt handler, adopted BY IMPORT from
    # `armature_core.parts` (wave 22, SEAM 1 — core-solvers' file). This tool was one of
    # the 29 in `tests/test_instrument_exits.py::CPYTHON_HALT_CONTRACT_PENDING`: its
    # typed refusals reached the operator as a stdlib traceback at exit 1 — the code this
    # repo reserves for a crash — and the evidence dict naming the clause reached nothing.
    # Never copied; the point of the seam is that this block is one function with one home.
    from armature_core.parts import run_tool_main  # noqa: E402

    run_tool_main(_cli, "EXTRACT_CLIP_FRAMES")
