#!/usr/bin/env python
"""encode_control — build the control video and prove the bridge is lossless.

    <venv-python> tools/encode_control.py --frames=<dir> --out=<video> --codec=<name>
                                   [--invert] [--survey]
    <venv-python> tools/encode_control.py --run=<stage_render out> --codec=<name>

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
returns a table; `gates.gate_r_round_trip` raises. Recommendations
(`recommended_gray` / `recommended_rgb`) pin the next encode for `--codec=auto` /
`--codec-from=`; they do not replace Gate R.

**What the input side refuses, and why Gate R cannot cover it.** Gate R compares the frames
this tool loaded against their decode, so anything that happened *while loading* is invisible
to it — the corruption is on both sides of the comparison. Three such things are refused here
instead, in `frame_population` and `read_frames`: a PNG the frame numbering does not name
(the stick renderer's `strip_every{N}.png` contact sheet sorts last and becomes the final
frame of the control), an alpha channel with no named plate (the Director's 2026-08-12 law —
the RGB composite a route submits is a deliberate, recorded choice), and a non-uint8 dtype
(the old cast wrapped 16-bit levels mod 256). The receipt records the modes, the dtype, and
the alpha disposition, because the frame hash it carries is of the already-coerced array.
Halt contract: exit 0 on success, 2 on a deliberate refusal (one <TOOL>_HALT JSON line; evidence.clause is the branch word), 1 on a crash. See README §"Reading a halt" and armature_core.parts.run_tool_main.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HALT_EPILOG = (
    'Halt contract: exit 0 on success, 2 on a deliberate refusal '
    '(one <TOOL>_HALT JSON line; evidence.clause is the branch word), 1 on a crash. '
    'See README §"Reading a halt".'
)


def runtime_provenance(libraries=None):
    """Interpreter + imaging-library versions for a written record (F-2ad4f715).

    Defined ABOVE the `composite_reference` import so writers that import this helper
    from encode_control (and that encode_control itself imports) do not circular-import.
    Pass ``libraries`` as ``{short_name: module}`` for what THIS tool imported; when
    omitted, versions are taken only for numpy / Pillow / cv2 / matplotlib already
    present in ``sys.modules`` — never imported just to ask.
    """
    libs = {}
    if libraries is None:
        for label, modname in (
            ("numpy", "numpy"),
            ("Pillow", "PIL"),
            ("cv2", "cv2"),
            ("matplotlib", "matplotlib"),
        ):
            mod = sys.modules.get(modname)
            if mod is not None:
                libs[label] = getattr(mod, "__version__", "UNKNOWN")
    else:
        for label, mod in libraries.items():
            if mod is None:
                continue
            ver = getattr(mod, "__version__", None)
            if ver is None and label == "Pillow":
                pil = sys.modules.get("PIL")
                ver = getattr(pil, "__version__", "UNKNOWN") if pil else "UNKNOWN"
            libs[label] = "UNKNOWN" if ver is None else ver
    return {
        "python_executable": sys.executable,
        "python_version": sys.version,
        "libraries": libs,
    }


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

#: F-06be7ebb / F-1bfe3e49 — the chroma-subsampled trap. Surveyed so the failure is
#: measured; offered on argparse only when `--allow-trap` is set.
TRAP_CODEC = "x264-qp0-yuv420"
SAFE_CODECS = tuple(c for c in CODECS if c != TRAP_CODEC)
CODEC_AUTO = "auto"


class EncodeFailure(ArmatureError):
    """The frames are not what this bridge encodes, or ffmpeg could not carry them.

    Carries an evidence dict for the same reason every gate in this repo does: the
    measurement that fired the refusal is the useful half of it.

    **WAVE 25 (F-b2c7b15a): it declares its gate id.** `run_tool_main` reads
    `getattr(exc, "gate", None)`, so a class with no class-level `gate` prints
    `"gate": null` on its halt line wherever the raise site's own evidence dict does not
    carry one. Driven end to end on `580af47` with the repo venv:
    `python tools/encode_control.py --frames=<empty dir> --out=<tmp>` exited 2 and printed
    `ENCODE_CONTROL_HALT {"tool": "encode_control", "outcome": "REFUSED - the tool declined
    to proceed", "gate": null, ...}` — the tool that produces the control video a paid run
    UPLOADS, halting on the refusal that stops a wrong frame population from becoming that
    upload, with no andon named for a runner to branch on. `ProjectGate`, `SticksGate`,
    `ClipReadError` and `measure_cascade_clip`'s trio all declare one; this is the same
    declaration, and it is why the halt line now reads `"gate": "ENCODE"`.
    """

    gate = "ENCODE"


#: The wall-clock allowance for one ffmpeg call, in three DERIVED pieces rather than one
#: fixed number: a global constant must not govern a local feature (CLAUDE.md), and the
#: same ceiling cannot honestly bound a header probe of a 39-byte download and a
#: 500-frame lossless encode. `FFMPEG_STARTUP_S` covers process start, container open and
#: the stream probe itself; the other two are charged against the structure each call is
#: actually given — the frame list handed to the encoder, or the bytes of the file handed
#: to the decoder.
FFMPEG_STARTUP_S = 120.0
FFMPEG_PER_FRAME_S = 10.0
FFMPEG_PER_MB_S = 10.0


def timeout_for_frames(n_frames):
    """The bound for a call whose work is a FRAME LIST — the encode."""
    return FFMPEG_STARTUP_S + FFMPEG_PER_FRAME_S * max(0, int(n_frames))


def timeout_for_file(path):
    """The bound for a call whose work is a FILE — a decode, or a stream probe.

    A path that is not on disk scores zero megabytes and gets the start-up allowance: the
    binary will fail fast on it anyway, and `gate_ffmpeg_binary` has already run.
    """
    size = os.path.getsize(path) if os.path.isfile(path) else 0
    return FFMPEG_STARTUP_S + FFMPEG_PER_MB_S * (size / 1e6)


def run_ffmpeg(cmd, *, timeout_s, subject, input_path=None, output_path=None, **kw):
    """Run one ffmpeg call under a BOUND, and make a wait that ended a named refusal.

    F-594d4efc, wave 28. The three subprocess sites in this domain gave ffmpeg no
    `timeout=`: this wrapper (which both the Gate R encode and the Gate R decode go
    through), `extract_clip_frames.probe` and `measure_cascade_clip.ffprobe_stream` — the
    last two being stream probes of a clip that arrived AFTER a credit was spent. Read
    against F-3dc24905 (33 of this domain's 42 tools print exactly one line, and none of
    the three printed anything before its result), the operator's picture of a wedged
    ffmpeg was an empty terminal with no elapsed time, no way to tell a slow decode from a
    stuck one, and nothing to end it but their own interrupt — with the paid artefact
    already downloaded and unprocessed. The realistic trigger is a malformed or truncated
    download from the hosted run.

    This is the ONE home for the bound and for the refusal; the two probes adopt it by
    import, exactly as they already adopt `gate_ffmpeg_binary` (F-a19ebe73, wave 25).
    Adopting the home means adopting its exception too, so all three refusals arrive as
    `EncodeFailure` under gate `ENCODE`; the evidence's `subject`, `binary` and `input`
    say which of the three calls it was.

    **A timeout is a refusal, never a retry.** `subprocess.run` kills the child, and the
    evidence states what is on disk now (`partial`) so the operator is not left guessing
    whether a half-written video exists.
    """
    started = time.monotonic()
    try:
        return subprocess.run(cmd, capture_output=True, timeout=timeout_s, **kw)
    except subprocess.TimeoutExpired as exc:
        elapsed = time.monotonic() - started
        partial = None
        if output_path and os.path.isfile(output_path):
            partial = {"path": output_path, "bytes": os.path.getsize(output_path)}
        raise EncodeFailure(
            f"ffmpeg did not finish the {subject} within the {timeout_s:.0f}s bound "
            f"derived for it (elapsed {elapsed:.1f}s) and was killed. The binary is "
            f"{cmd[0]!r} and the input it was given is {input_path!r}. This is a refusal, "
            f"not a retry: nothing is re-submitted and no credit is spent on a wait that "
            f"ended",
            {"gate": "ENCODE", "andon": "EncodeFailure",
             "clause": "ffmpeg_exceeded_the_time_bound",
             "subject": subject, "bound_s": timeout_s,
             "elapsed_s": round(elapsed, 3), "binary": cmd[0],
             "input": input_path, "partial": partial},
        ) from exc


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
                            {"gate": "FRAMES", "andon": "EncodeFailure",
                             "clause": "frames_dir_is_not_a_directory",
                             "frames_dir": frames_dir})
    pngs = sorted(n for n in os.listdir(frames_dir) if n.lower().endswith(".png"))
    numbered = [n for n in pngs if os.path.splitext(n)[0].isdigit()]
    unexpected = [n for n in pngs if n not in set(numbered)]
    names = sorted(numbered, key=lambda n: int(os.path.splitext(n)[0]))
    if unexpected:
        raise EncodeFailure(
            f"{frames_dir} holds {len(unexpected)} PNG(s) that are not numbered frames "
            f"({', '.join(unexpected[:8])}); a stray sorts into the population and "
            f"becomes a frame of the encoded control with every gate green",
            {"gate": "FRAMES", "andon": "EncodeFailure",
             "clause": "stray_png_in_the_frame_population",
             "frames_dir": frames_dir, "unexpected": unexpected, "frames": names},
        )
    if not names:
        raise EncodeFailure(
            f"no NNNNN.png frames in {frames_dir}; there is nothing to encode",
            {"gate": "FRAMES", "andon": "EncodeFailure",
             "clause": "no_numbered_frames_to_encode",
             "frames_dir": frames_dir, "png_files": pngs},
        )
    if expect is not None:
        want = shotspec.frame_names(expect, "png")
        if names != want:
            raise EncodeFailure(
                f"{frames_dir} holds {len(names)} frame(s) and the spec names "
                f"{len(want)}; the population an upload is built from must be the one "
                f"the spec declared",
                {"gate": "FRAMES", "andon": "EncodeFailure",
                 "clause": "population_is_not_the_spec_names",
                 "frames_dir": frames_dir, "found": names, "expected": want,
                 "missing": [n for n in want if n not in set(names)],
                 "unexpected": [n for n in names if n not in set(want)]},
            )
    return names


def read_frames(frames_dir, invert=False, expect=None, alpha_over=None, progress=None):
    """Read a channel directory as `(names, frames, source)`.

    `progress(stage, done, total)`, when a caller supplies one, is called once per frame
    opened — this is the other long loop F-3dc24905 names, beside `stage_render.run_export`
    and `extract_clip_frames`' decode. `main` supplies one and prints it lowercase on
    stderr; stdout keeps its single sentinel.

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
                    {"gate": "FRAMES", "andon": "EncodeFailure",
                     "clause": "frame_is_palette_indexed",
                     "frame": n, "mode": mode},
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
                {"gate": "FRAMES", "andon": "EncodeFailure",
                 "clause": "frame_dtype_is_not_uint8",
                 "frame": n, "mode": mode, "dtype": a.dtype.name,
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
                {"gate": "FRAMES", "andon": "EncodeFailure",
                 "clause": "frame_array_shape_is_not_a_frame",
                 "frame": n, "mode": mode, "shape": list(a.shape)},
            )
        if invert:
            a = (255 - a).astype(np.uint8)
        out.append(np.ascontiguousarray(a, dtype=np.uint8))
        if progress is not None:
            progress("read", len(out), len(names))

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


def gate_encode_rate(fps):
    """ANDON — `--fps` is a rate, refused by name where it is READ.

    F-e0f1f520, wave 22. `--fps` is `type=int, default=16` with no bound and it reaches
    ffmpeg as `-r str(fps)`. Measured on `e8263a3` through the real CLI: `--fps=0` and
    `--fps=-16` both exited 1 with stdout EMPTY and the raw line
    `Error opening input files: Invalid argument` — naming neither the flag, nor the value,
    nor this tool. A refusal on the paid path that reads as an environment failure sends a
    chain routing on exit codes into the retry branch.
    """
    if fps <= 0:
        raise EncodeFailure(
            f"--fps={fps} is not a rate; it reaches ffmpeg as `-r {fps}` on the input "
            f"side of the control video this run uploads, and the receipt records it as "
            f"the rate that video plays at",
            {"gate": "ARGS", "andon": "EncodeFailure",
             "clause": "encode_rate_not_positive", "flag": "--fps", "value": fps,
             "minimum_exclusive": 0})
    return fps


def gate_ffmpeg_binary():
    """ANDON — the encoder this tool is about to run exists, named by path and by source.

    F-e0f1f520, wave 22. `FFMPEG` is selected at import from `ARMATURE_FFMPEG` with a
    hard-coded fallback under `E:/AI-Models`. Measured on `e8263a3` with that variable
    pointed at a path that does not exist: exit 1 and a bare
    `FileNotFoundError: [WinError 2] The system cannot find the file specified` — naming
    neither the variable, nor the path, nor ffmpeg.
    """
    if not os.path.isfile(FFMPEG):
        raise EncodeFailure(
            f"the ffmpeg binary this tool encodes and decodes with is not on disk: "
            f"{FFMPEG!r}. Gate R compares an encode against its own decode, so both halves "
            f"of the losslessness proof run through this one binary",
            {"gate": "ARGS", "andon": "EncodeFailure",
             "clause": "ffmpeg_binary_not_found", "ffmpeg": FFMPEG,
             "from_env": "ARMATURE_FFMPEG" in os.environ,
             "env_var": "ARMATURE_FFMPEG"})
    return FFMPEG


def ffmpeg_version():
    """The encoder's OWN first line of `ffmpeg -version`, for the receipt.

    F-7c1f4117, wave 22. The receipt beside the control video named the codec, the codec
    args, the resolution, the fps, the video sha256 and the source-frame sha256 — and NOT
    the binary that produced it, although that binary is chosen by an environment variable
    and this module's own `CODECS` table records that the build matters ("this build's ffv1
    lists bgr0 but not plain gbrp"). Losslessness, the single property this receipt
    certifies, is a property of an encoder the receipt did not identify. Its three siblings
    all record it: `extract_clip_frames`, `measure_cascade_clip`, and this module's own
    `--survey` branch.
    """
    try:
        proc = run_ffmpeg([FFMPEG, "-hide_banner", "-version"],
                          timeout_s=FFMPEG_STARTUP_S, subject="version probe")
        first = proc.stdout.decode("utf-8", "replace").splitlines()
        return first[0].strip() if first else "NOT REPORTED"
    except OSError as exc:                       # the binary vanished between the two calls
        return f"UNAVAILABLE: {exc}"
    except EncodeFailure as exc:
        # WAVE 28 (F-594d4efc): the bound now applies here too, and a `-version` call that
        # hangs must not take down a receipt that is otherwise complete. This function is a
        # PROVENANCE reader, not a gate — its two siblings already return a string for the
        # binary-vanished case, and a wait that ended is the same class of answer.
        return f"UNAVAILABLE: {exc}"


def encode(frames, path, codec, fps=16):
    """Write `frames` to `path` with the named codec. Raises on ffmpeg failure."""
    if codec not in CODECS:
        raise EncodeFailure(f"unknown codec {codec!r}; known: {sorted(CODECS)}",
                            {"gate": "ARGS", "andon": "EncodeFailure",
                             "clause": "unknown_codec", "flag": "--codec",
                             "value": codec, "known": sorted(CODECS)})
    # ---- ANDON, above the subprocess: the rate, then the binary.
    gate_encode_rate(fps)
    gate_ffmpeg_binary()
    h, w = frames[0].shape[:2]
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    cmd = [
        FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps),
        "-i", "-",
        *CODECS[codec]["args"],
        path,
    ]
    proc = run_ffmpeg(cmd, timeout_s=timeout_for_frames(len(frames)), subject="encode",
                      input_path=f"{len(frames)} frame(s) on stdin", output_path=path,
                      input=b"".join(f.tobytes() for f in frames))
    if proc.returncode != 0 or not os.path.isfile(path):
        raise EncodeFailure(
            f"ffmpeg failed to encode {codec}: {proc.stderr.decode('utf-8', 'replace')[:500]}",
            {"gate": "ENCODE", "andon": "EncodeFailure",
             "clause": "ffmpeg_refused_the_encode",
             "codec": codec, "out": path, "returncode": proc.returncode,
             "wrote_the_file": os.path.isfile(path), "ffmpeg": FFMPEG,
             "stderr_tail": proc.stderr.decode("utf-8", "replace")[-800:]},
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
    proc = run_ffmpeg(cmd, timeout_s=timeout_for_file(path), subject="decode",
                      input_path=path)
    if proc.returncode != 0:
        raise EncodeFailure(
            f"ffmpeg failed to decode {path}: {proc.stderr.decode('utf-8', 'replace')[:500]}",
            {"gate": "ENCODE", "andon": "EncodeFailure",
             "clause": "ffmpeg_refused_the_decode",
             "path": path, "returncode": proc.returncode, "ffmpeg": FFMPEG,
             "stderr_tail": proc.stderr.decode("utf-8", "replace")[-800:]},
        )
    stride = int(width) * int(height) * 3
    raw = proc.stdout
    if stride <= 0:
        raise EncodeFailure(
            f"decode asked for a {width}x{height} frame, which has no bytes",
            {"gate": "ENCODE", "andon": "EncodeFailure",
             "clause": "decode_stride_is_not_positive",
             "width": width, "height": height, "stride": stride},
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
            {"gate": "ENCODE", "andon": "EncodeFailure",
             "clause": "decoded_bytes_are_not_whole_frames",
             "path": path, "width": width, "height": height, "stride": stride,
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


def survey_recommendations(rows):
    """First lossless codec per probe column, in CODECS declaration order (F-06be7ebb).

    `recommended_gray` / `recommended_rgb` pin the next encode; the survey table alone
    used to leave the operator re-typing `--codec=` — including the trap — by hand.
    """
    rec = {"recommended_gray": None, "recommended_rgb": None}
    for row in rows:
        name = row.get("codec")
        if name == TRAP_CODEC:
            continue
        if rec["recommended_gray"] is None and row.get("grayscale") == "lossless":
            rec["recommended_gray"] = name
        if rec["recommended_rgb"] is None and row.get("rgb") == "lossless":
            rec["recommended_rgb"] = name
        if rec["recommended_gray"] and rec["recommended_rgb"]:
            break
    return rec


def survey_codecs():
    """DIAGNOSTIC — measure every candidate bridge; pin recommended_gray/rgb (F-06be7ebb).

    Still raises nothing. Recommendations are the first non-trap lossless row per probe,
    so `--codec=auto` / `--codec-from=` can select without re-typing a trap.
    """
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


def survey_table(rows=None):
    """Survey rows plus recommended_gray / recommended_rgb (F-1bfe3e49 / F-06be7ebb)."""
    rows = list(rows) if rows is not None else survey_codecs()
    return {**survey_recommendations(rows), "survey": rows}


def load_survey_table(path):
    """Load a --survey-out JSON and require recommended_* (or derive them)."""
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise EncodeFailure(
            f"--codec-from={path} is not readable survey JSON: {exc}",
            {"gate": "ARGS", "andon": "EncodeFailure",
             "clause": "codec_from_unreadable", "path": os.path.abspath(path),
             "error": str(exc)}) from exc
    if not isinstance(data, dict):
        raise EncodeFailure(
            f"--codec-from={path} must be a JSON object",
            {"gate": "ARGS", "andon": "EncodeFailure",
             "clause": "codec_from_not_object", "path": os.path.abspath(path)})
    rows = data.get("survey")
    if not isinstance(rows, list) or not rows:
        raise EncodeFailure(
            f"--codec-from={path} carries no survey rows",
            {"gate": "ARGS", "andon": "EncodeFailure",
             "clause": "codec_from_missing_survey", "path": os.path.abspath(path)})
    rec = survey_recommendations(rows)
    gray = data.get("recommended_gray") or rec["recommended_gray"]
    rgb = data.get("recommended_rgb") or rec["recommended_rgb"]
    if not gray or not rgb:
        raise EncodeFailure(
            f"--codec-from={path} has no lossless recommendation for "
            f"gray={gray!r} rgb={rgb!r}",
            {"gate": "ARGS", "andon": "EncodeFailure",
             "clause": "codec_from_missing_recommendation",
             "path": os.path.abspath(path),
             "recommended_gray": gray, "recommended_rgb": rgb})
    return {"recommended_gray": gray, "recommended_rgb": rgb, "survey": rows,
            "path": os.path.abspath(path)}


def codec_for_mode(mode, recommendations):
    """Pick recommended_gray / recommended_rgb for a measured channel mode."""
    if mode == "gray":
        return recommendations["recommended_gray"]
    if mode == "rgb":
        return recommendations["recommended_rgb"]
    raise EncodeFailure(
        f"channel mode {mode!r} is not gray or rgb",
        {"gate": "CODEC", "andon": "EncodeFailure",
         "clause": "unknown_channel_mode", "mode": mode})


def channel_pixel_mode(frames_dir, sample_n=1):
    """`gray` when every sampled frame is R=G=B; `rgb` otherwise (F-b8bf8e7d).

    The survey measures both probes; the channel's OWN pixels pick which column gates
    the codec. A true-RGB normal channel must not inherit a grayscale-safe trap.
    """
    names = frame_population(frames_dir)
    take = names[:max(1, min(len(names), sample_n))]
    for n in take:
        arr = np.array(Image.open(os.path.join(frames_dir, n)).convert("RGB"))
        if not (arr[..., 0] == arr[..., 1]).all() or not (arr[..., 1] == arr[..., 2]).all():
            return "rgb"
    return "gray"


def survey_row_for(codec, survey_rows=None):
    """The survey table row for `codec`, or raise naming the unknown bridge."""
    rows = survey_rows if survey_rows is not None else survey_codecs()
    for row in rows:
        if row.get("codec") == codec:
            return row
    raise EncodeFailure(
        f"codec {codec!r} is not in the survey table; known: "
        f"{sorted(r.get('codec') for r in rows)}",
        {"gate": "CODEC", "andon": "EncodeFailure",
         "clause": "codec_not_in_survey", "codec": codec,
         "survey_codecs": [r.get("codec") for r in rows]},
    )


def gate_codec_safe_for_mode(codec, mode, survey_rows=None):
    """ANDON — refuse a codec `--survey` does not mark lossless for this channel mode.

    F-b8bf8e7d: a multi-channel pack used to let each channel pick a codec in isolation;
    grayscale channels could quietly take `x264-qp0-yuv420` while the RGB normal needed
    an RGB-safe bridge. Survey column is `grayscale` for gray, `rgb` for rgb; only the
    literal `lossless` passes.
    """
    if mode not in ("gray", "rgb"):
        raise EncodeFailure(
            f"channel mode {mode!r} is not gray or rgb",
            {"gate": "CODEC", "andon": "EncodeFailure",
             "clause": "unknown_channel_mode", "mode": mode, "codec": codec})
    row = survey_row_for(codec, survey_rows=survey_rows)
    col = "grayscale" if mode == "gray" else "rgb"
    verdict = row.get(col)
    if verdict != "lossless":
        raise EncodeFailure(
            f"codec {codec!r} is not lossless for {mode} channels per --survey "
            f"({col}={verdict!r}); a mixed-fidelity control pack would upload quietly "
            f"damaged chroma on true-RGB channels",
            {"gate": "CODEC", "andon": "EncodeFailure",
             "clause": "codec_unsafe_for_channel_mode",
             "codec": codec, "mode": mode, "survey_column": col,
             "survey_verdict": verdict, "survey_row": row},
        )
    return {"codec": codec, "mode": mode, "survey_column": col,
            "survey_verdict": verdict, "verdict": "PASS"}


def read_stage_render_channel_dirs(run_dir):
    """`manifest.json` `channel_dirs` from a stage_render out, or raise by name."""
    manifest_path = os.path.join(run_dir, "manifest.json")
    if not os.path.isfile(manifest_path):
        raise EncodeFailure(
            f"{run_dir} has no manifest.json; --run expects a stage_render out that "
            f"already published channel_dirs",
            {"gate": "RUN", "andon": "EncodeFailure",
             "clause": "stage_render_manifest_missing",
             "run": os.path.abspath(run_dir), "manifest": manifest_path})
    try:
        with open(manifest_path, encoding="utf-8") as fh:
            manifest = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise EncodeFailure(
            f"{manifest_path} is not readable JSON: {exc}",
            {"gate": "RUN", "andon": "EncodeFailure",
             "clause": "stage_render_manifest_unreadable",
             "run": os.path.abspath(run_dir), "manifest": manifest_path,
             "error": str(exc)}) from exc
    channel_dirs = manifest.get("channel_dirs")
    if not isinstance(channel_dirs, dict) or not channel_dirs:
        raise EncodeFailure(
            f"{manifest_path} carries no channel_dirs map; nothing to encode into a "
            f"control pack",
            {"gate": "RUN", "andon": "EncodeFailure",
             "clause": "channel_dirs_missing",
             "run": os.path.abspath(run_dir), "manifest": manifest_path,
             "channel_dirs": channel_dirs})
    resolved = {}
    for channel, rel in channel_dirs.items():
        path = rel if os.path.isabs(str(rel)) else os.path.join(run_dir, str(rel))
        if not os.path.isdir(path):
            raise EncodeFailure(
                f"channel {channel!r} names {path} which is not a directory",
                {"gate": "RUN", "andon": "EncodeFailure",
                 "clause": "channel_dir_missing",
                 "run": os.path.abspath(run_dir), "channel": channel,
                 "channel_dir": path, "channel_dirs": channel_dirs})
        resolved[channel] = path
    return manifest, resolved


def build_control_pack(run_dir, codec, invert=False, fps=16, expect=None,
                       alpha_over=None, progress=None, survey_rows=None,
                       recommendations=None, stream=False):
    """Encode every stage_render channel into one pack receipt (F-b8bf8e7d / F-1bfe3e49).

    Videos land under `<run>/control_videos/<channel>.<ext>`. A codec that `--survey`
    marks unsafe for a channel's measured mode is refused before that channel encodes,
    so a grayscale-safe trap cannot ride beside an RGB normal under one green pack.

    `codec="auto"` (F-1bfe3e49) picks per channel from `recommended_gray` /
    `recommended_rgb`. An explicit codec remains an all-channels override that still
    runs `gate_codec_safe_for_mode`.
    """
    manifest, channel_dirs = read_stage_render_channel_dirs(run_dir)
    rows = survey_rows if survey_rows is not None else survey_codecs()
    auto = codec == CODEC_AUTO
    if auto:
        recs = recommendations or survey_recommendations(rows)
        if not recs.get("recommended_gray") or not recs.get("recommended_rgb"):
            raise EncodeFailure(
                "codec=auto needs recommended_gray and recommended_rgb from the survey",
                {"gate": "ARGS", "andon": "EncodeFailure",
                 "clause": "auto_missing_recommendations",
                 "recommendations": recs})
    elif codec not in CODECS:
        raise EncodeFailure(
            f"unknown codec {codec!r}; known: {sorted(CODECS)} or {CODEC_AUTO!r}",
            {"gate": "ARGS", "andon": "EncodeFailure",
             "clause": "unknown_codec", "flag": "--codec", "codec": codec,
             "known": sorted(CODECS)})
    videos_dir = os.path.join(run_dir, "control_videos")
    os.makedirs(videos_dir, exist_ok=True)
    channels = {}
    codecs_used = {}
    for channel, frames_dir in sorted(channel_dirs.items()):
        mode = channel_pixel_mode(frames_dir)
        ch_codec = codec_for_mode(mode, recs) if auto else codec
        safety = gate_codec_safe_for_mode(ch_codec, mode, survey_rows=rows)
        ext = CODECS[ch_codec]["ext"]
        out_path = os.path.join(videos_dir, f"{channel}{ext}")
        build_kw = dict(invert=invert, fps=fps, expect=expect,
                        alpha_over=alpha_over, progress=progress)
        if stream:
            build_kw["stream"] = True
        receipt = build(frames_dir, out_path, ch_codec, **build_kw)
        codecs_used[channel] = ch_codec
        channels[channel] = {
            "channel": channel,
            "frames_dir": os.path.abspath(frames_dir),
            "mode": mode,
            "codec": ch_codec,
            "codec_safety": safety,
            "video": os.path.abspath(out_path),
            "video_sha256": receipt["video_sha256"],
            "source_frames_sha256": receipt["source_frames_sha256"],
            "n_frames": receipt["n_frames"],
            "gate_R": receipt["gate_R"],
            "receipt": out_path + ".receipt.json",
            "stream": bool(stream),
        }
    pack = {
        "tool": "encode_control",
        "kind": "control_pack",
        "run": os.path.abspath(run_dir),
        "manifest": os.path.abspath(os.path.join(run_dir, "manifest.json")),
        "channel_dirs": {k: os.path.abspath(v) for k, v in channel_dirs.items()},
        "codec": codec,
        "codec_selection": "per_channel_auto" if auto else "explicit_override",
        "codecs_used": codecs_used,
        "recommendations": (recommendations or survey_recommendations(rows)) if auto else None,
        "fps": fps,
        "inverted": invert,
        "stream": bool(stream),
        "ffmpeg": FFMPEG,
        "ffmpeg_version": ffmpeg_version(),
        "ffmpeg_from_env": "ARMATURE_FFMPEG" in os.environ,
        **runtime_provenance({"numpy": np, "Pillow": Image}),
        "channels": channels,
        "gate_R_all": {
            "verdict": "PASS",
            "channels": sorted(channels),
        },
        "stage_render_tool_version": manifest.get("tool_version"),
    }
    if not auto:
        pack["codec_args"] = CODECS[codec]["args"]
    pack_path = os.path.join(run_dir, "control_pack.receipt.json")
    with open(pack_path, "w", encoding="utf-8") as fh:
        json.dump(pack, fh, indent=2)
    pack["pack_receipt"] = os.path.abspath(pack_path)
    return pack


def encode_stream_png_sequence(frames_dir, path, codec, fps=16, invert=False,
                               expect=None, alpha_over=None, progress=None,
                               batch_size=8):
    """Encode via a temporary %05d.png sequence ffmpeg reads (F-a0dda17d).

    Keeps Gate R by decoding back and comparing against on-disk sources in batches so
    the full RGB stack need not stay in Python memory. Default in-memory path stays for
    short packs.
    """
    if codec not in CODECS:
        raise EncodeFailure(f"unknown codec {codec!r}; known: {sorted(CODECS)}",
                            {"gate": "ARGS", "andon": "EncodeFailure",
                             "clause": "unknown_codec", "flag": "--codec",
                             "value": codec, "known": sorted(CODECS)})
    gate_encode_rate(fps)
    gate_ffmpeg_binary()
    names = frame_population(frames_dir, expect=expect)
    if not names:
        raise EncodeFailure(
            f"{frames_dir} holds no numbered frames to stream-encode",
            {"gate": "FRAMES", "andon": "EncodeFailure",
             "clause": "no_frames_to_stream", "frames_dir": frames_dir})

    with tempfile.TemporaryDirectory(prefix="encode_control_stream_") as td:
        modes, dtypes, alpha_seen = [], [], False
        for i, n in enumerate(names):
            src = os.path.join(frames_dir, n)
            with Image.open(src) as im:
                mode = im.mode
                if mode == "P":
                    raise EncodeFailure(
                        f"{src}: mode 'P' is palette-indexed; encoding an index as a "
                        f"value is not encoding the frame",
                        {"gate": "FRAMES", "andon": "EncodeFailure",
                         "clause": "frame_is_palette_indexed",
                         "frame": n, "mode": mode})
                has_alpha = mode in ("RGBA", "LA", "PA")
                a = np.array(im.convert("RGBA") if has_alpha else im)
            if mode not in modes:
                modes.append(mode)
            if a.dtype.name not in dtypes:
                dtypes.append(a.dtype.name)
            if a.dtype != np.uint8:
                raise EncodeFailure(
                    f"{src}: dtype {a.dtype}; the uint8 view of 16-bit data wraps mod 256",
                    {"gate": "FRAMES", "andon": "EncodeFailure",
                     "clause": "frame_dtype_is_not_uint8",
                     "frame": n, "mode": mode, "dtype": a.dtype.name})
            if has_alpha:
                alpha_seen = True
                a, _rec = compose_over_named_plate(
                    a, alpha_over, label=f"{src}: mode {mode!r}", exc=EncodeFailure,
                    extra_evidence={"frame": n, "mode": mode, "dtype": a.dtype.name},
                    channel_order="RGB")
            elif a.ndim == 2:
                a = np.repeat(a[..., None], 3, axis=2)
            elif a.ndim == 3 and a.shape[2] == 3:
                pass
            else:
                raise EncodeFailure(
                    f"{src}: array shape {a.shape} is not a frame this bridge encodes",
                    {"gate": "FRAMES", "andon": "EncodeFailure",
                     "clause": "frame_array_shape_is_not_a_frame",
                     "frame": n, "mode": mode, "shape": list(a.shape)})
            if invert:
                a = (255 - a).astype(np.uint8)
            a = np.ascontiguousarray(a, dtype=np.uint8)
            Image.fromarray(a, mode="RGB").save(os.path.join(td, f"{i:05d}.png"))
            if progress is not None:
                progress("stream-write", i + 1, len(names))
            if i == 0:
                h, w = a.shape[:2]

        pattern = os.path.join(td, "%05d.png")
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        cmd = [
            FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
            "-framerate", str(fps), "-i", pattern,
            *CODECS[codec]["args"],
            path,
        ]
        proc = run_ffmpeg(cmd, timeout_s=timeout_for_frames(len(names)), subject="encode",
                          input_path=pattern, output_path=path)
        if proc.returncode != 0 or not os.path.isfile(path):
            raise EncodeFailure(
                f"ffmpeg failed to stream-encode {codec}: "
                f"{proc.stderr.decode('utf-8', 'replace')[:500]}",
                {"gate": "ENCODE", "andon": "EncodeFailure",
                 "clause": "ffmpeg_refused_the_stream_encode",
                 "codec": codec, "out": path, "returncode": proc.returncode,
                 "wrote_the_file": os.path.isfile(path), "ffmpeg": FFMPEG,
                 "stderr_tail": proc.stderr.decode("utf-8", "replace")[-800:]})

        decoded = decode(path, w, h)
        if len(decoded) != len(names):
            raise EncodeFailure(
                f"stream Gate R: decode returned {len(decoded)} frames, source has "
                f"{len(names)}",
                {"gate": "R", "andon": "EncodeFailure",
                 "clause": "stream_decode_frame_count",
                 "n_source": len(names), "n_decoded": len(decoded)})

        # Batch Gate R against on-disk coerced sources (not a full in-memory stack).
        source_hasher = hashlib.sha256()
        for start in range(0, len(names), max(1, batch_size)):
            end = min(len(names), start + max(1, batch_size))
            batch_src = []
            for i in range(start, end):
                with Image.open(os.path.join(td, f"{i:05d}.png")) as im:
                    arr = np.ascontiguousarray(np.array(im.convert("RGB")), dtype=np.uint8)
                batch_src.append(arr)
                source_hasher.update(arr.tobytes())
            gates.gate_r_round_trip(
                batch_src, decoded[start:end],
                source_label=f"{frames_dir} stream batch {start}:{end}",
                decoded_label=f"{path} [{codec}] batch {start}:{end}")
            if progress is not None:
                progress("stream-gate-R", end, len(names))

        source = {
            "source_modes": modes,
            "source_dtype": dtypes[0] if len(dtypes) == 1 else dtypes,
            "source_alpha_present": alpha_seen,
            "alpha_disposition": (
                f"composited over rgb{tuple(int(v) for v in alpha_over)}" if alpha_seen
                else "no alpha channel in any source frame"),
            "encode_path": "stream_png_sequence",
        }
        with open(path, "rb") as fh:
            video_sha = hashlib.sha256(fh.read()).hexdigest()
        receipt = {
            "tool": "encode_control",
            "frames_dir": frames_dir,
            "frame_names": names,
            "n_frames": len(names),
            "resolution": [w, h],
            "fps": fps,
            "inverted": invert,
            **source,
            "codec": codec,
            "codec_args": CODECS[codec]["args"],
            "ffmpeg": FFMPEG,
            "ffmpeg_version": ffmpeg_version(),
            "ffmpeg_from_env": "ARMATURE_FFMPEG" in os.environ,
            **runtime_provenance({"numpy": np, "Pillow": Image}),
            "video": path,
            "video_sha256": video_sha,
            "source_frames_sha256": source_hasher.hexdigest(),
            "gate_R": {"verdict": "PASS", "path": "stream_batched"},
            "stream": True,
            "stream_batch_size": max(1, batch_size),
        }
        with open(path + ".receipt.json", "w", encoding="utf-8") as fh:
            json.dump(receipt, fh, indent=2)
        return receipt


def build(frames_dir, out_path, codec, invert=False, fps=16, expect=None,
          alpha_over=None, progress=None, stream=False):
    """Encode a control sequence and run Gate R on it. **Raises** on any difference.

    The gate is called here, inside the function that produces the artifact a later
    step will upload — not chained behind a shell `&&`, which can walk past a failing
    exit code, and not as an `assert`, which `-O` deletes.

    `stream=True` (F-a0dda17d) writes a temp PNG sequence ffmpeg reads and batches Gate R
    against on-disk sources. Default stays in-memory for short packs.
    """
    if stream:
        return encode_stream_png_sequence(
            frames_dir, out_path, codec, fps=fps, invert=invert, expect=expect,
            alpha_over=alpha_over, progress=progress)

    names, frames, source = read_frames(frames_dir, invert=invert, expect=expect,
                                        alpha_over=alpha_over, progress=progress)
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
        # F-7c1f4117, wave 22: the encoder is selected at import by `ARMATURE_FFMPEG`, and
        # losslessness — the one property this receipt certifies — is a property of the
        # build. The two siblings that merely MEASURE (`extract_clip_frames`,
        # `measure_cascade_clip`) already recorded it; the one that PRODUCES did not.
        "ffmpeg": FFMPEG,
        "ffmpeg_version": ffmpeg_version(),
        "ffmpeg_from_env": "ARMATURE_FFMPEG" in os.environ,
        # F-2ad4f715: the interpreter and imaging libs beside the ffmpeg key — a receipt
        # that names the encoder but not the Python cannot attribute a re-measured gap.
        **runtime_provenance({"numpy": np, "Pillow": Image}),
        "video": out_path,
        "video_sha256": video_sha,
        "source_frames_sha256": hashlib.sha256(
            b"".join(f.tobytes() for f in frames)
        ).hexdigest(),
        "gate_R": {"verdict": "PASS", "evidence": ev},
        "stream": False,
    }
    with open(out_path + ".receipt.json", "w", encoding="utf-8") as fh:
        json.dump(receipt, fh, indent=2)
    return receipt


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="build the control video a paid run uploads, and prove the encoder "
                    "round trip is lossless (Gate R). --run=<stage_render out> encodes "
                    "every manifest.channel_dirs entry into one control_pack.receipt.json "
                    "(F-b8bf8e7d)",
        epilog=HALT_EPILOG)
    ap.add_argument("--frames", help="the channel directory of NNNNN.png control frames "
                                     "to encode, in index order (single-channel mode)")
    ap.add_argument("--out", help="the video file to write; its receipt is written beside "
                                  "it as <out>.receipt.json (single-channel mode)")
    ap.add_argument("--run", default=None,
                    help="a stage_render out directory whose manifest.json publishes "
                         "channel_dirs; encodes each channel to "
                         "<run>/control_videos/<channel>.<ext>, refuses a codec "
                         "--survey marks unsafe for that channel's gray/rgb mode, and "
                         "writes <run>/control_pack.receipt.json")
    # WAVE 28 (F-7c3f8a26): `choices=` and a `help=`. The legal values are a closed set of
    # five literal keys in `CODECS` above, and the ONLY place that set reached the operator
    # was the refusal inside `encode()` — which fires from `build()` AFTER `read_frames` has
    # listed, opened, coerced and hashed the whole frame population. MEASURED on `3380ae2`
    # against the real 33-frame `outputs/E02/control_480x832/depth_pershot`: `--codec=ffv1`
    # exits 2 with `unknown codec 'ffv1'; known: [...]`. So the only way to learn which
    # names exist was to run the tool wrong and read the refusal, and `x264-qp0-yuv420` —
    # annotated in this module as THE TRAP, 4:2:0 chroma subsampling that is a no-op on the
    # grayscale channels and quiet corruption on the true-RGB normal channel — was offered
    # on the same footing as the four safe ones. `fit_reference:82` uses `choices=` for
    # exactly this job eleven files over. argparse now refuses the typo before a single
    # frame is opened; the `unknown_codec` raise in `encode()` STAYS, because it guards
    # every programmatic caller and the parser guards only this one.
    # F-06be7ebb: trap stays in CODECS for survey measurement, but argparse only offers
    # it when --allow-trap is set. auto is the per-channel pack selector (F-1bfe3e49).
    ap.add_argument("--allow-trap", action="store_true",
                    help="offer x264-qp0-yuv420 (THE TRAP) as a --codec choice; without "
                         "this flag the trap is surveyed but not selectable for a normal "
                         "encode (F-06be7ebb)")
    ap.add_argument("--codec", default="ffv1-gbrp",
                    help="the bridge to encode with (default ffv1-gbrp). With --run, "
                         "codec=auto picks recommended_gray/recommended_rgb per channel "
                         "(F-1bfe3e49). Explicit codec remains an all-channels override "
                         "that still runs gate_codec_safe_for_mode. x264-qp0-yuv420 needs "
                         "--allow-trap")
    ap.add_argument("--codec-from", default=None,
                    help="select codec from a --survey-out JSON by measured source mode "
                         "(recommended_gray / recommended_rgb); for --run this is "
                         "equivalent to --codec=auto using that table (F-06be7ebb)")
    ap.add_argument("--fps", type=int, default=16,
                    help="the rate written into the control video and into its receipt "
                         "(default 16); it reaches ffmpeg as `-r <fps>` on the INPUT side, "
                         "so it is the rate the uploaded video plays at. Must be positive")
    ap.add_argument("--invert", action="store_true",
                    help="flip the polarity of every frame (255 - value) before encoding, "
                         "to match a route whose depth convention is near-dark rather than "
                         "near-bright. Recorded in the receipt as `inverted`; the frames on "
                         "disk are not modified")
    ap.add_argument("--expect", type=int, default=None,
                    help="the frame count the spec declares; the directory's numbered "
                         "frames must be exactly shotspec.frame_names(expect, 'png')")
    ap.add_argument("--alpha-over", default=None,
                    help="R,G,B of the plate an RGBA source is composited over. Without "
                         "it an alpha channel is a refusal, not a silent drop")
    ap.add_argument("--stream", action="store_true",
                    help="encode via a temporary %%05d.png sequence ffmpeg reads; Gate R "
                         "compares decode against on-disk sources in batches "
                         "(F-a0dda17d). Default stays in-memory for short packs")
    ap.add_argument("--survey", action="store_true",
                    help="DIAGNOSTIC: measure every candidate bridge against a grayscale "
                         "probe and a true-RGB probe, print the table (with "
                         "recommended_gray/recommended_rgb) and exit 0")
    ap.add_argument("--survey-out",
                    help="with --survey: also write the table as JSON to this path, with "
                         "recommended_gray / recommended_rgb and the ffmpeg binary")
    args = ap.parse_args(argv)

    if args.survey:
        rows = survey_codecs()
        table = survey_table(rows)
        print(json.dumps(table, indent=2))
        if args.survey_out:
            os.makedirs(os.path.dirname(os.path.abspath(args.survey_out)), exist_ok=True)
            with open(args.survey_out, "w", encoding="utf-8") as fh:
                json.dump({"ffmpeg": FFMPEG,
                           "recommended_gray": table["recommended_gray"],
                           "recommended_rgb": table["recommended_rgb"],
                           "survey": rows,
                           **runtime_provenance({"numpy": np, "Pillow": Image})},
                          fh, indent=2)
        return 0

    if args.run and (args.frames or args.out):
        raise EncodeFailure(
            "--run is the multi-channel pack path; do not also pass --frames/--out",
            {"gate": "ARGS", "andon": "EncodeFailure",
             "clause": "run_excludes_frames_and_out",
             "run": args.run, "frames": args.frames, "out": args.out})
    if not args.run and (not args.frames or not args.out):
        raise EncodeFailure(
            "--frames and --out are required unless --survey or --run",
            {"gate": "ARGS", "andon": "EncodeFailure",
             "clause": "frames_and_out_are_required",
             "frames": args.frames, "out": args.out, "run": args.run,
             "survey": bool(args.survey)})

    codec_from = load_survey_table(args.codec_from) if args.codec_from else None
    codec = args.codec
    if codec_from is not None and args.run:
        # --codec-from on --run is auto selection from that survey table.
        codec = CODEC_AUTO
    elif codec_from is not None and not args.run:
        # Single-channel: pick by measured mode of --frames.
        mode = channel_pixel_mode(args.frames)
        codec = codec_for_mode(mode, codec_from)
    if codec == TRAP_CODEC and not args.allow_trap:
        raise EncodeFailure(
            f"codec {TRAP_CODEC!r} is THE TRAP (4:2:0 chroma); pass --allow-trap to "
            f"select it deliberately, or run --survey and use recommended_gray/"
            f"recommended_rgb / --codec-from= / --codec=auto",
            {"gate": "ARGS", "andon": "EncodeFailure",
             "clause": "trap_codec_requires_allow_trap",
             "codec": codec, "flag": "--allow-trap"})
    allowed = set(SAFE_CODECS) | {CODEC_AUTO}
    if args.allow_trap:
        allowed.add(TRAP_CODEC)
    if codec not in allowed and codec not in CODECS:
        raise EncodeFailure(
            f"unknown codec {codec!r}; known: {sorted(SAFE_CODECS)} or {CODEC_AUTO!r}"
            + (f" (or {TRAP_CODEC} with --allow-trap)" if not args.allow_trap else ""),
            {"gate": "ARGS", "andon": "EncodeFailure",
             "clause": "unknown_codec", "flag": "--codec", "value": codec,
             "known": sorted(allowed)})
    if codec not in allowed:
        # Explicit trap without --allow-trap already refused; other CODECS keys that are
        # somehow not in SAFE need the same footing as unknown when allow-trap is off.
        if codec == TRAP_CODEC:
            pass  # handled above
        elif codec not in CODECS and codec != CODEC_AUTO:
            raise EncodeFailure(
                f"unknown codec {codec!r}",
                {"gate": "ARGS", "andon": "EncodeFailure",
                 "clause": "unknown_codec", "flag": "--codec", "value": codec,
                 "known": sorted(allowed)})

    # ---- the ONE parser. `compose_over_named_plate`'s docstring states the contract the
    #      wave-6 sweep delivered -- "there is one refusal, one composite and one record
    #      shape" -- and the composite and the record WERE one implementation while the
    #      flag parser was three. `fit_reference`, `make_plate` and `pack_pose_pack` all
    #      call `composite_reference.parse_plate` and get a typed error with an evidence
    #      dict; this reimplemented the same three-integer check inline and raised a bare
    #      `SystemExit` string, in the one tool of the four whose output is UPLOADED -- so
    #      a caller catching `EncodeFailure` around `main` did not catch it, and the halt
    #      carried none of the measurement that fired it.
    # ---- ANDON, before a single frame is read: the operator's arguments first, then the
    #      encoder. Operator input is refused before the environment is inspected, so a
    #      malformed `--alpha-over` or `--fps` reads as ITS OWN refusal on any host --
    #      MEASURED on the first CI run of the swarm (2026-09-05, `6e83dbb`, ubuntu-latest, no
    #      ffmpeg on the runner): with the encoder gate ahead of the plate parser, the alpha-law
    #      family test's `[encode_control]` case met `ffmpeg_binary_not_found` instead of the
    #      parser's refusal and read `KeyError: 'supplied'` -- the one producer of four whose
    #      parser contract could not be exercised without an encoder installed. The same
    #      inversion reproduces on the rig with `ARMATURE_FFMPEG` pointed at a missing path.
    gate_encode_rate(args.fps)
    plate = parse_plate(args.alpha_over, EncodeFailure)
    gate_ffmpeg_binary()

    # The wait says it is alive (F-3dc24905, wave 28). Lowercase, on stderr: stdout carries
    # exactly one uppercase sentinel per tool and two censuses assert it
    # (`test_sheet_argv_smoke`, `test_instruments_amend_w10.success_tokens`).
    _started = time.monotonic()

    def _progress(stage, done, total):
        # F-e28656b8: plumb the real frame-list bound — never the dead token `bound none`.
        bound_s = timeout_for_frames(total)
        print(f"encode_control {stage} {done}/{total}  "
              f"elapsed {time.monotonic() - _started:.1f}s  bound {bound_s:.0f}s",
              file=sys.stderr, flush=True)

    if args.run:
        pack = build_control_pack(
            args.run, codec, invert=args.invert, fps=args.fps,
            expect=args.expect, alpha_over=plate, progress=_progress,
            survey_rows=(codec_from["survey"] if codec_from else None),
            recommendations=(codec_from if codec_from else None),
            stream=args.stream)
        print("ENCODE_CONTROL_PACK " + json.dumps({
            "run": pack["run"],
            "pack_receipt": pack["pack_receipt"],
            "channels": sorted(pack["channels"]),
            "codec": pack["codec"],
            "codecs_used": pack.get("codecs_used"),
            "gate_R_all": "PASS",
        }))
        return 0

    # Single-channel: still refuse an unsafe codec for the measured mode (pack path
    # already does this per channel).
    if codec != CODEC_AUTO:
        mode = channel_pixel_mode(args.frames)
        gate_codec_safe_for_mode(
            codec, mode,
            survey_rows=(codec_from["survey"] if codec_from else None))
    receipt = build(args.frames, args.out, codec, invert=args.invert, fps=args.fps,
                    expect=args.expect, alpha_over=plate, progress=_progress,
                    stream=args.stream)
    print("ENCODE_CONTROL " + json.dumps({
        "video": receipt["video"],
        "sha256": receipt["video_sha256"][:16],
        "n_frames": receipt["n_frames"],
        "alpha_disposition": receipt["alpha_disposition"],
        "gate_R": "PASS",
    }))
    return 0


if __name__ == "__main__":
    # WAVE 22, SEAM 1: the ONE `__main__` halt handler, adopted BY IMPORT from
    # `armature_core.parts` (core-solvers' file, posted to the wave-22 seams inbox). Never
    # copied — the whole point of the seam is that this block is one function with one home.
    from armature_core.parts import run_tool_main  # noqa: E402

    run_tool_main(main, "ENCODE_CONTROL")
