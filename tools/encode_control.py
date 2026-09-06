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
import time

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
          alpha_over=None, progress=None):
    """Encode a control sequence and run Gate R on it. **Raises** on any difference.

    The gate is called here, inside the function that produces the artifact a later
    step will upload — not chained behind a shell `&&`, which can walk past a failing
    exit code, and not as an `assert`, which `-O` deletes.
    """
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
    ap = argparse.ArgumentParser(
        description="build the control video a paid run uploads, and prove the encoder "
                    "round trip is lossless (Gate R)")
    ap.add_argument("--frames", help="the channel directory of NNNNN.png control frames "
                                     "to encode, in index order")
    ap.add_argument("--out", help="the video file to write; its receipt is written beside "
                                  "it as <out>.receipt.json")
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
    ap.add_argument("--codec", default="ffv1-gbrp", choices=sorted(CODECS),
                    help="the bridge to encode with (default ffv1-gbrp, the spec's stated "
                         "preference). x264-qp0-yuv420 is THE TRAP: its 4:2:0 chroma "
                         "subsampling is a no-op on grayscale depth/mask/edge channels and "
                         "quietly corrupts the true-RGB normal channel. Run --survey to "
                         "see every candidate measured")
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
    ap.add_argument("--survey", action="store_true",
                    help="DIAGNOSTIC: measure every candidate bridge against a grayscale "
                         "probe and a true-RGB probe, print the table and exit 0. Decides "
                         "nothing and encodes none of --frames")
    ap.add_argument("--survey-out",
                    help="with --survey: also write the table as JSON to this path, with "
                         "the ffmpeg binary that produced it")
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
        raise EncodeFailure(
            "--frames and --out are required unless --survey",
            {"gate": "ARGS", "andon": "EncodeFailure",
             "clause": "frames_and_out_are_required",
             "frames": args.frames, "out": args.out,
             "survey": bool(args.survey)})
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
        print(f"encode_control {stage} {done}/{total}  "
              f"elapsed {time.monotonic() - _started:.1f}s  bound none",
              file=sys.stderr, flush=True)

    receipt = build(args.frames, args.out, args.codec, invert=args.invert, fps=args.fps,
                    expect=args.expect, alpha_over=plate, progress=_progress)
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
