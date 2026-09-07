#!/usr/bin/env python
"""make_sheet — the panel the Director reads the run off.

    <venv-python> tools/make_sheet.py --run=<run dir> --out=<sheet.png> [--frames=0,8,16,24]
    <venv-python> tools/make_sheet.py --dailies-manifest=<run.json>

facet ran four arms and two gates before building its comparison sheet, and when the
sheet finally existed the Director read the whole thesis off one panel. E01 generates
nothing, so there is no *output* or *reference* column yet — what exists is the
**control** stack and its **provenance**, and those are what this lays out.

**F-ca0f0408 — `--dailies-manifest=`.** Post-generation judging used to be a hand-wired
chain of separate CLIs. `make_dailies.py` is outside this domain's frozen owned glob, so
the orchestrator lives here: a small run.json/toml names control/frames/reference/meta
and optional detection; this invokes the existing tools in-process and refuses to print
MEASURE_*_OK without GATE0_SHEET present. Each tool stays callable alone.

Sheets locate; full size decides. Every tile here is written at native resolution with
no resampling, so what is on the sheet is what is in the file.

Runs outside Blender (Pillow).
Halt contract: exit 0 on success, 2 on a deliberate refusal (one <TOOL>_HALT JSON line; evidence.clause is the branch word), 1 on a crash. See README §"Reading a halt" and armature_core.parts.run_tool_main.
"""

import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core.errors import ArmatureError  # noqa: E402
from sheet_compose import SHEET_PLATE, load_rgb_over_plate  # noqa: E402


class MakeSheetError(ArmatureError):
    """This panel cannot be built as asked. One typed refusal for this tool.

    It used to answer a missing required flag with a bare `KeyError: 'run'` out of
    `args["run"]` — a traceback ending in one word, naming neither the flag it wanted nor
    the token it got, on the panel tool. Every argparse instrument in this domain answers
    `error: the following arguments are required: --run`, and `stage_render._parse_argv` is
    the counter-example in the same hand-rolled shape: `missing --{required}=<path>`.
    """


def parse_argv(argv, *, required, optional=(), tool="make_sheet", exc=None):
    """`--key=value` tokens into a dict, refusing by NAME rather than by KeyError.

    ONE implementation for the two hand-rolled parsers in this domain (`make_sheet` and
    `analyze_p3`), in the shape `stage_render._parse_argv` already carries: a token that
    is not `--key=value` names itself, and a missing required flag names the flag.
    """
    exc = exc or MakeSheetError
    known = set(required) | set(optional)
    args = {}
    for token in argv:
        if not token.startswith("--") or "=" not in token:
            raise exc(
                f"{tool}: expected --key=value, got {token!r}; a token that lost its "
                f"leading dashes registers a key nobody asked for and the refusal below "
                f"then names the wrong thing",
                {"gate": "ARGV", "tool": tool, "token": token, "argv": list(argv),
                 "known_flags": sorted(known)})
        key, _, value = token[2:].partition("=")
        if key not in known:
            raise exc(
                f"{tool}: unknown flag --{key}; this tool takes "
                f"{', '.join('--' + k for k in sorted(known))}",
                {"gate": "ARGV", "tool": tool, "flag": f"--{key}",
                 "known_flags": sorted(known)})
        args[key] = value
    for name in required:
        if name not in args:
            raise exc(
                f"{tool}: missing --{name}=<value>",
                {"gate": "ARGV", "tool": tool, "missing": f"--{name}",
                 "given": sorted(args), "known_flags": sorted(known)})
    return args

MARGIN = 8
LABEL_H = 18
HEADER_H = 74


def _load_rgb(path, plate=SHEET_PLATE):
    """One channel tile, composited over the NAMED plate.

    This was `img.convert("RGB")` — PIL's SILENT alpha drop, which is the worse half of
    the family the four sheets carried: they at least composited through the mask, while
    this one submitted whatever RGB the author had made invisible with nothing recording
    that a channel had been dropped. Found 2026-09-04 by the census in
    `tests/test_sheet_pairing.py`, which derives its population from the tree rather than
    from the three sheets the finding named.
    """
    return load_rgb_over_plate(path, plate)[0]


def build_sheet(run_dir, frames=None, channels=None):
    manifest = json.load(open(os.path.join(run_dir, "manifest.json"), encoding="utf-8"))
    count = manifest["frame_count"]
    if frames is None:
        n = min(5, count)
        frames = [round(i * (count - 1) / max(n - 1, 1)) for i in range(n)]
    if channels is None:
        channels = [c for c in manifest["channel_dirs"] if os.path.isdir(os.path.join(run_dir, c))]

    first = _load_rgb(os.path.join(run_dir, channels[0], f"{frames[0]:05d}.png"))
    tw, th = first.size

    cols, rows = len(channels), len(frames)
    W = MARGIN + cols * (tw + MARGIN)
    H = HEADER_H + MARGIN + rows * (th + LABEL_H + MARGIN)
    sheet = Image.new("RGB", (W, H), (18, 18, 20))
    draw = ImageDraw.Draw(sheet)

    p3 = manifest.get("p3") or {}
    prov = manifest.get("provenance", {})
    header = [
        f"{manifest['spec']['name']}  ·  {os.path.basename(manifest['asset']['path'])}"
        f"  ·  sha256 {manifest['asset']['sha256'][:16]}…",
        f"{manifest['resolution'][0]}x{manifest['resolution'][1]}  ·  {count} frames  ·  "
        f"generator {manifest['generator_profile']['name']} "
        f"(/{manifest['generator_profile']['dim_divisor']}, "
        f"{manifest['generator_profile']['frame_form']})  ·  "
        f"engine {manifest['spec']['render']['engine']} @ {manifest['spec']['render']['samples']} spp"
        f"  ·  Blender {prov.get('version', '?')}",
        f"G1 {manifest['gates']['G1']['verdict']} · G2 {manifest['gates']['G2']['verdict']} · "
        f"G4 {manifest['gates']['G4']['verdict']} (max delta "
        f"{manifest['gates']['G4']['max_delta_px']} px) · G5 {manifest['gates']['G5']['verdict']}",
        (
            "P3 mean |per-frame - per-shot| on geometry = "
            f"{p3.get('pixel_weighted_mean_abs'):.4f} "
            f"({p3.get('pixel_weighted_mean_abs') * 255:.1f}/255)  ·  worst frame "
            f"{p3.get('worst_frame_index')} = {p3.get('worst_frame_mean_abs'):.4f}  ·  "
            f"z-range swing {p3.get('z_range_swing'):.3f}x"
        ) if p3.get("pixel_weighted_mean_abs") is not None else "P3 NOT COMPUTED",
    ]
    for i, line in enumerate(header):
        draw.text((MARGIN, 6 + i * 16), line, fill=(215, 215, 220))

    for r, f in enumerate(frames):
        y = HEADER_H + MARGIN + r * (th + LABEL_H + MARGIN)
        for c, chan in enumerate(channels):
            x = MARGIN + c * (tw + MARGIN)
            path = os.path.join(run_dir, chan, f"{f:05d}.png")
            if not os.path.isfile(path):
                draw.rectangle([x, y, x + tw, y + th], outline=(90, 40, 40))
                draw.text((x + 4, y + 4), "MISSING", fill=(220, 90, 90))
            else:
                sheet.paste(_load_rgb(path), (x, y))
            label = f"{chan}  f{f:03d}"
            if chan == "p3_diff":
                stats = next((s for s in p3.get("per_frame", []) if s["frame"] == f), None)
                if stats:
                    label += f"  mean {stats['mean_abs']:.3f}  max {stats['max_abs']:.3f}"
            draw.text((x + 2, y + th + 3), label, fill=(170, 170, 178))
    return sheet


def _manifest_path(token):
    """Split `--dailies-manifest=<path>` (or bare path after the flag form)."""
    if token.startswith("--dailies-manifest="):
        return token.split("=", 1)[1]
    return None


def load_dailies_manifest(path):
    """Read the small run.json / run.toml naming the post-fetch judging inputs.

    F-ca0f0408: make_dailies.py is outside the frozen owned glob; this tool is the
    owned entry that turns a fetched run directory into Gate 0 + review pack +
    measurement JSON in one invocation. Each underlying tool stays callable alone.
    """
    if not os.path.isfile(path):
        raise MakeSheetError(
            f"--dailies-manifest={path} is not a file",
            {"gate": "ARGS", "andon": "MakeSheetError",
             "clause": "dailies_manifest_missing", "path": os.path.abspath(path)})
    text = open(path, encoding="utf-8").read()
    lower = path.lower()
    if lower.endswith(".toml"):
        try:
            import tomllib  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover — 3.11+ on this rig
            raise MakeSheetError(
                f"tomllib unavailable for {path}: {exc}",
                {"gate": "ARGS", "andon": "MakeSheetError",
                 "clause": "dailies_toml_unavailable", "path": os.path.abspath(path)}) from exc
        data = tomllib.loads(text)
    else:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise MakeSheetError(
                f"--dailies-manifest={path} is not readable JSON: {exc}",
                {"gate": "ARGS", "andon": "MakeSheetError",
                 "clause": "dailies_manifest_not_json", "path": os.path.abspath(path)}) from exc
    if not isinstance(data, dict):
        raise MakeSheetError(
            f"--dailies-manifest={path} must be a JSON/TOML object",
            {"gate": "ARGS", "andon": "MakeSheetError",
             "clause": "dailies_manifest_not_object", "path": os.path.abspath(path)})
    required = ("control_dir", "frames_dir", "reference", "meta", "out_dir")
    missing = [k for k in required if not data.get(k)]
    if missing:
        raise MakeSheetError(
            f"--dailies-manifest missing required keys: {missing}",
            {"gate": "ARGS", "andon": "MakeSheetError",
             "clause": "dailies_manifest_missing_keys", "missing": missing,
             "required": list(required), "path": os.path.abspath(path)})
    return data


def run_dailies(manifest_path):
    """Gate 0 first; measurements only after GATE0_SHEET exists on disk (F-ca0f0408)."""
    import make_ab_clip as AB  # noqa: PLC0415
    import make_gate0_sheet as G0  # noqa: PLC0415
    import make_review_clip as MRC  # noqa: PLC0415
    import measure_clip as MC  # noqa: PLC0415
    import measure_tracking as MT  # noqa: PLC0415

    man = load_dailies_manifest(manifest_path)
    out_dir = os.path.abspath(man["out_dir"])
    os.makedirs(out_dir, exist_ok=True)
    gate0_out = os.path.join(out_dir, man.get("gate0_name", "gate0_sheet.png"))
    frames_flag = man.get("frames", "0,8,16,24")
    # ---- Gate 0 BEFORE any MEASURE_*_OK. The judging discipline forbids quoting a
    #      number without this sheet; the orchestrator refuses to print measure OK
    #      unless the sheet file is present after this step.
    G0.main([
        f"--run={man['control_dir']}",
        f"--frames-dir={man['frames_dir']}",
        f"--reference={man['reference']}",
        f"--meta={man['meta']}",
        f"--out={gate0_out}",
        f"--frames={frames_flag}",
    ])
    if not os.path.isfile(gate0_out):
        raise MakeSheetError(
            f"GATE0_SHEET was not written at {gate0_out}; refusing MEASURE_*_OK",
            {"gate": "DAILIES", "andon": "MakeSheetError",
             "clause": "gate0_sheet_missing_before_measure", "gate0_out": gate0_out})

    products = {"gate0_sheet": gate0_out}
    measure_ok_allowed = True  # sheet is on disk

    if man.get("measure_clip", True):
        if not measure_ok_allowed:
            raise MakeSheetError(
                "refusing MEASURE_CLIP_OK without GATE0_SHEET present",
                {"gate": "DAILIES", "andon": "MakeSheetError",
                 "clause": "measure_without_gate0"})
        clip_out = os.path.join(out_dir, man.get("measure_clip_name", "measure_clip.json"))
        MC.main([f"--frames={man['frames_dir']}", f"--out={clip_out}",
                 f"--label={man.get('label', 'clip')}"])
        products["measure_clip"] = clip_out

    if man.get("measure_tracking", False):
        if not measure_ok_allowed:
            raise MakeSheetError(
                "refusing MEASURE_TRACKING without GATE0_SHEET present",
                {"gate": "DAILIES", "andon": "MakeSheetError",
                 "clause": "measure_without_gate0"})
        track_out = os.path.join(out_dir, man.get("measure_tracking_name",
                                                   "measure_tracking.json"))
        MT.main([f"--run={man['frames_dir']}", f"--control={man['control_dir']}",
                 f"--out={track_out}", f"--label={man.get('label', 'clip')}"])
        products["measure_tracking"] = track_out

    if man.get("review_clip", True):
        review_out = os.path.join(out_dir, man.get("review_dir_name", "review"))
        argv = [f"--frames={man['frames_dir']}", f"--out={review_out}"]
        if man.get("detection"):
            argv.append(f"--detection={man['detection']}")
        if man.get("stills"):
            argv.append(f"--stills={man['stills']}")
        MRC.main(argv)
        products["review_clip"] = review_out

    if man.get("ab_clip", False):
        ab_out = os.path.join(out_dir, man.get("ab_clip_name", "gate0_ab.webp"))
        fps = float(man.get("fps", 16))
        AB.main([
            "--mode=gate0",
            f"--a={man['control_dir']}", f"--b={man['frames_dir']}",
            f"--a-fps={fps}", f"--b-fps={fps}",
            f"--meta={man['meta']}", f"--out={ab_out}",
        ])
        products["ab_clip"] = ab_out

    # Optional: rebuild Gate 0 with measurements bound onto the provenance column.
    if products.get("measure_clip") and man.get("gate0_with_measurements", True):
        g0_measured = os.path.join(out_dir, man.get("gate0_measured_name",
                                                     "gate0_sheet_measured.png"))
        argv = [
            f"--run={man['control_dir']}",
            f"--frames-dir={man['frames_dir']}",
            f"--reference={man['reference']}",
            f"--meta={man['meta']}",
            f"--out={g0_measured}",
            f"--frames={frames_flag}",
            f"--measurements={products['measure_clip']}",
        ]
        if products.get("measure_tracking"):
            argv.append(f"--tracking={products['measure_tracking']}")
        G0.main(argv)
        products["gate0_sheet_measured"] = g0_measured

    print("DAILIES_OK " + json.dumps({
        "manifest": os.path.abspath(manifest_path),
        "out_dir": out_dir,
        "gate0_sheet": gate0_out,
        "products": products,
    }))
    return 0


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    # F-ca0f0408: dailies pack from a run manifest (owned stand-in for make_dailies.py).
    dailies = None
    rest = []
    for token in argv:
        path = _manifest_path(token)
        if path is not None:
            dailies = path
        else:
            rest.append(token)
    if dailies is not None:
        return run_dailies(dailies)
    args = parse_argv(rest, required=("run", "out"), optional=("frames", "channels"))
    frames = [int(v) for v in args["frames"].split(",")] if args.get("frames") else None
    channels = args["channels"].split(",") if args.get("channels") else None
    sheet = build_sheet(args["run"], frames=frames, channels=channels)
    out = args["out"]
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    sheet.save(out)
    print("SHEET " + json.dumps({"path": os.path.abspath(out), "size": list(sheet.size),
                                 "sheet_plate": [int(v) for v in SHEET_PLATE]}))
    return 0


if __name__ == "__main__":
    # WAVE 25 (F-68f3fb4b): the ONE `__main__` halt handler, adopted BY IMPORT from
    # `armature_core.parts` (wave 22, SEAM 1 — core-solvers' file). This tool was one of
    # the 29 in `tests/test_instrument_exits.py::CPYTHON_HALT_CONTRACT_PENDING`: its
    # typed refusals reached the operator as a stdlib traceback at exit 1 — the code this
    # repo reserves for a crash — and the evidence dict naming the clause reached nothing.
    # Never copied; the point of the seam is that this block is one function with one home.
    from armature_core.parts import run_tool_main  # noqa: E402

    run_tool_main(main, "MAKE_SHEET")
