"""armature — the command line surface of the installed toolkit.

WHAT THIS IS AND IS NOT. The installable package is `armature_core`: the gates, the
framing and turnaround solvers, the shot-spec contract, the channel maths and the
payload builders. Every one of those imports under a plain CPython, which is what
lets them be tested — and packaged — without Blender present.

The repo's rendering scripts are NOT entry points here and that is deliberate rather
than an omission. `render_turnaround.py`, `stage_render.py` and their siblings run
INSIDE Blender's own interpreter (`blender -b -P script.py -- args`); a console script
on the user's Python could not import `bpy` and would fail at the first line. Shipping
one would be a promise the package cannot keep. They stay in the repository, where the
invocation that works is the one written down.

So this command reports what is installed and where the rest lives. It is a signpost,
not a pipeline stage.
"""
import argparse
import importlib
import json
import sys

REPO = "https://github.com/mcp-tool-shop-org/armature"
DOCS = "https://mcp-tool-shop-org.github.io/armature/"

#: The modules that make up the installed surface, with what each one is for. Kept as
#: data rather than prose so `armature modules --json` can hand it to a machine.
SURFACE = [
    ("gates", "G1..G5 — pure predicates that RAISE; no bpy, no I/O"),
    ("route_gates", "graph-level gates: ROUTE, PAIR, PAIR_TIER, LEDGER"),
    ("canon", "surface-keyed character statement, both-direction router, fail-closed spend"),
    ("canon_census", "which subjects have a surfaces file, as data"),
    ("rig_gates", "rig and skeleton gates"),
    ("donor_gate", "Gate DONOR — is this clip fit to be a baseline before anything is lifted"),
    ("shotspec", "the shot-spec contract: schema, load, resolve, hash"),
    ("subject", "what a subject asset is, as a number rather than as a filename"),
    ("framing", "camera framing and projection, perspective and orthographic"),
    ("turnaround", "turnaround planning, the projection plan, Gate ALPHA/CROP"),
    ("startframe", "start-frame measurement: silhouette extent, Gate WHOLE, mask bbox"),
    ("channels", "channel maths: normalization, edge derivation, encoding"),
    ("openpose", "the OpenPose-18 convention"),
    ("aapose", "AAPose stick construction"),
    ("landmarks", "landmark extraction"),
    ("lift_solve", "land 33 MediaPipe-topology landmarks on the 22-bone rig, as rotations"),
    ("joints", "joint and skeleton maths"),
    ("binding", "procedural rigid-per-segment skinning, testable without bpy"),
    ("parts", "split a shell mesh into rigid per-segment parts"),
    ("posearc", "authored performances for the procedural wire subject"),
    ("walk", "the gait model — a walk, a stop and an emote, as numbers"),
    ("resample", "control-sequence resampling"),
    ("assembly", "the assembly graph: frames in, one VIDEO out, no partner credit"),
    ("sitelist", "the registered site list, as data"),
    ("clipstats", "clip statistics"),
    ("clipcompare", "clip comparison"),
    ("glb", "GLB reading helpers"),
    ("pngio", "a dependency-free PNG writer"),
    ("errors", "the exception types the gates raise"),
    ("blender_scene", "the only module that imports bpy — needs Blender's interpreter"),
]


def _version():
    """The installed version, or a marker when running from a source checkout."""
    try:
        from importlib.metadata import version

        return version("armature-studio")
    except Exception:
        return "0.0.0+source"


def _probe(name):
    """Import one surface module and report the outcome.

    `blender_scene` is EXPECTED to fail outside Blender, so a failure there is reported
    as `needs-blender` rather than as a defect. Everything else failing to import is a
    real problem and says so.
    """
    try:
        importlib.import_module(f"armature_core.{name}")
        return "ok"
    except ImportError:
        return "needs-blender" if name == "blender_scene" else "MISSING"


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="armature",
        description="armature — you block the shot; the model shoots it. "
        "GLB-authored previz for video-diffusion generation.",
        epilog=f"Rendering scripts run inside Blender, from the repo: {REPO}",
    )
    ap.add_argument("--version", action="version", version=f"armature-studio {_version()}")
    sub = ap.add_subparsers(dest="cmd")

    p_mod = sub.add_parser("modules", help="list the installed modules and what each is for")
    p_mod.add_argument("--json", action="store_true", help="machine-readable output")

    p_chk = sub.add_parser("check", help="import every module and report what resolved")
    p_chk.add_argument("--json", action="store_true", help="machine-readable output")

    sub.add_parser("where", help="print where the docs and the render scripts live")

    a = ap.parse_args(argv)

    if a.cmd == "modules":
        if a.json:
            print(json.dumps([{"module": m, "purpose": d} for m, d in SURFACE], indent=2))
        else:
            print(f"armature_core — {len(SURFACE)} modules\n")
            for m, d in SURFACE:
                print(f"  {m:<16} {d}")
        return 0

    if a.cmd == "check":
        rows = [(m, _probe(m)) for m, _ in SURFACE]
        missing = [m for m, s in rows if s == "MISSING"]
        if a.json:
            print(json.dumps({"version": _version(),
                              "modules": {m: s for m, s in rows},
                              "missing": missing}, indent=2))
        else:
            print(f"armature-studio {_version()}\n")
            for m, s in rows:
                print(f"  {m:<16} {s}")
            print()
            print("all modules resolved" if not missing else f"MISSING: {', '.join(missing)}")
        # A missing module is a broken install and the exit code says so.
        return 1 if missing else 0

    if a.cmd == "where":
        print(f"docs     {DOCS}")
        print(f"repo     {REPO}")
        print("render   scripts run inside Blender, from a repo checkout:")
        print("         blender -b -P tools/render_turnaround.py -- --glb X.glb --out D")
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
