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
import ast
import importlib
import importlib.util
import json
import os
import sys

REPO = "https://github.com/mcp-tool-shop-org/armature"
DOCS = "https://mcp-tool-shop-org.github.io/armature/"

#: The modules that make up the installed surface, with what each one is for. Kept as
#: data rather than prose so `armature modules --json` can hand it to a machine.
#:
#: ⚠ **A row may only name a gate the module beside it carries.** The `route_gates` row
#: read "graph-level gates: ROUTE, PAIR, PAIR_TIER, LEDGER" and that module defines
#: exactly two gate classes; PAIR_TIER and LEDGER live in `tools/build_lora_arm_payload.py`
#: and LEDGER_W3 in `tools/build_camera_i2v_payload.py`, none of which is in the installed
#: package at all. This is the machine-readable surface — `armature modules --json` — so a
#: consumer was told a gate exists in a module that does not carry it.
#: `test_every_gate_named_in_the_surface_exists_in_the_module_beside_it` is the pin.
SURFACE = [
    ("gates", "pure predicates that RAISE; no bpy, no I/O — gates: G1, G2, G4, G5, G6, "
              "R, B, S"),
    ("route_gates", "graph-level gates: ROUTE, PAIR"),
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


#: Module names that are neither stdlib nor part of this package. Computed rather than
#: listed so a new dependency cannot be missed by an out-of-date literal.
_LOCAL_MODULES = frozenset(
    f[:-3] for f in os.listdir(os.path.dirname(os.path.abspath(__file__)))
    if f.endswith(".py")
)

_FUNC_LOCAL_CACHE = {}


def import_roots_by_scope(source, filename="<source>"):
    """Every root module a source imports, split by whether the import is at MODULE SCOPE.

    THE one import scan. Returns
    `{"module_scope": frozenset(...), "not_module_scope": frozenset(...)}` — the first is
    what a plain `import <module>` executes, the second is what it does not.

    ⚠ **This walk existed TWICE and the two copies did not agree on what "not at module
    scope" means.** `_function_local_dependencies` incremented its depth counter only on
    `FunctionDef`/`AsyncFunctionDef`, so an import in a CLASS BODY sat at depth 0 and was
    never collected; `tests/test_packaging.lazy_third_party_roots` classified laziness by
    whether the root appeared in `tree.body`, so a class-body import — and equally an
    import inside a module-level `try:` or `if:` — was classified LAZY, and
    `lazy_import_call_sites` (which walked `FunctionDef` nodes) then found no call site
    for it. Measured 2026-09-03 by dropping a module containing `class Thing: import
    cv2_probe_pkg` into `armature_core/` and removing it again: both readings returned
    nothing, i.e. `armature check` would print `ok` for that module on an install where
    the class body raises, and the packaging test's clean-room requirement would have no
    call site to demand. On today's tree the two agree exactly, so this is a divergence
    with no live instance — closed as ONE scanner both callers read, rather than as two
    walks patched to match.

    A `ClassDef` counts as a nested scope here for the same reason a `FunctionDef` does:
    the question this function answers for its callers is "which imports would a probe
    that only walks module-level statements fail to see", and a class body is one of
    them. `Lambda` is included for completeness.
    """
    tree = source if isinstance(source, ast.AST) else ast.parse(source, filename)
    at_module_scope, nested = set(), set()
    stack = [(tree, 0)]
    while stack:
        node, depth = stack.pop()
        for child in ast.iter_child_nodes(node):
            d = depth
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                                  ast.Lambda)):
                d += 1
            elif isinstance(child, ast.Import):
                (nested if depth else at_module_scope).update(
                    a.name.split(".")[0] for a in child.names)
            elif isinstance(child, ast.ImportFrom):
                if child.level == 0 and child.module:
                    (nested if depth else at_module_scope).add(
                        child.module.split(".")[0])
            stack.append((child, d))
    return {"module_scope": frozenset(at_module_scope),
            "not_module_scope": frozenset(nested)}


def _function_local_dependencies(name):
    """Third-party roots this module imports INSIDE a function body.

    ⚠ **`import` inside a function is invisible to an import probe.** `_probe` executed
    the module-level import and nothing else, so a dependency imported in a function body
    was never reached. Measured 2026-09-03 with cv2, PIL and matplotlib all blocked:
    every SURFACE row read `ok`, `armature check` printed "all modules resolved" and
    exited 0 — and `donor_gate.mean_consecutive_frame_difference` then raised
    `ModuleNotFoundError: PIL`. The command said "importable" in language an operator
    reads as "runnable", on an install where two modules' functions cannot run.

    They CAN be resolved without executing the functions: read the source and take the
    imports that are NOT at module scope, then `find_spec` on each root name. That reading
    finds gates -> numpy; donor_gate -> PIL, numpy; aapose -> cv2, matplotlib. Reading the
    source rather than importing keeps this probe as cheap and as side-effect-free as it
    was.

    The scan itself is `import_roots_by_scope`, which `tests/test_packaging.py` also
    reads — one walk, not two that disagree. See that function for the divergence.
    """
    if name in _FUNC_LOCAL_CACHE:
        return _FUNC_LOCAL_CACHE[name]
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{name}.py")
    try:
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
    except (OSError, SyntaxError):
        # A source we cannot parse is reported by the import probe instead; this
        # function's silence here is not a verdict.
        _FUNC_LOCAL_CACHE[name] = []
        return []
    roots = import_roots_by_scope(tree, filename=path)["not_module_scope"]
    out = sorted(r for r in roots
                 if r not in sys.stdlib_module_names
                 and r not in _LOCAL_MODULES
                 and r != "armature_core")
    _FUNC_LOCAL_CACHE[name] = out
    return out


def _resolvable(root):
    """Is this root importable from here? A finder that raises is a `no`."""
    try:
        return importlib.util.find_spec(root) is not None
    except (ImportError, ValueError):
        return False


def _missing_root(exc):
    """The root module an ImportError says was missing, or None."""
    name = getattr(exc, "name", None)
    return name.split(".")[0] if isinstance(name, str) and name else None


def _probe(name):
    """Import one surface module, resolve its function-local deps, report the outcome.

    Returns a ROW — `{"module", "status", "error", "message", "missing_root"}` — not a bare
    status string.

    ⚠ **The failure row carried no CAUSE.** This caught `Exception` and returned the bare
    string `"MISSING"`; the exception's type and message were discarded and appeared in no
    output path. Measured 2026-09-05 by making
    `importlib.import_module("armature_core.shotspec")` raise `ValueError("boom: a table in
    this module is malformed")`: `main(["check", "--json"])` printed `{"version": ...,
    "modules": {..., "shotspec": "MISSING", ...}, "missing": ["shotspec"]}` and exited 1,
    with no key anywhere in the document naming the error type, the message, or the module
    that could not be found. The exit code and the row were correct; what was absent is
    anything an operator or a support reader can key on — and this command is the installed
    package's ONLY self-diagnosis. A user on a broken wheel install got one word and had to
    reproduce the import by hand to learn whether the cause was a missing dependency, a
    syntax error or a packaging omission.

    `status` keeps the four words the command already distinguishes (`ok`, `needs-blender`,
    `needs-<dep>/<dep>`, `MISSING`), so `--json`'s `modules` map and every pin on it are
    unchanged; the cause rides `error` / `message` / `missing_root` beside it, and the whole
    row is carried in `--json` under `module_rows`.

    `blender_scene` is EXPECTED to fail outside Blender — but that reading belongs to
    **bpy**, not to the module's name. `_probe` used to return `needs-blender` for any
    `ImportError` raised by `blender_scene` without inspecting which module was missing:
    measured 2026-09-03, making the import raise `ImportError(name=
    'armature_core.typo_helper')` returned `needs-blender`, identical to the genuine
    bpy-absent reading, and `armature check` printed "all modules resolved" and exited 0
    on a genuinely broken module. It also caught only `ImportError`, so a `SyntaxError`
    at import time escaped as a traceback rather than as a row.
    """
    try:
        importlib.import_module(f"armature_core.{name}")
    except Exception as exc:  # noqa: BLE001 — a broken module is a row, not a traceback
        return {"module": name,
                "status": "needs-blender" if _missing_root(exc) == "bpy" else "MISSING",
                "error": type(exc).__name__, "message": str(exc),
                "missing_root": _missing_root(exc)}
    unresolved = [r for r in _function_local_dependencies(name) if not _resolvable(r)]
    status = "needs-" + "/".join(unresolved) if unresolved else "ok"
    return {"module": name, "status": status, "error": None, "message": None,
            "missing_root": None}


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
        rows = [_probe(m) for m, _ in SURFACE]
        # `needs-blender` is the one expected condition outside Blender. Every other
        # non-`ok` row is a broken install — including `needs-cv2` / `needs-PIL`, which
        # say the module imports and its functions cannot run. Reporting those as
        # resolved is what made this command worthless on a clean-venv wheel install.
        missing = [r["module"] for r in rows
                   if r["status"] not in ("ok", "needs-blender")]
        if a.json:
            # `modules` stays the module -> status map it has always been, so a consumer
            # keyed on it is unchanged; `module_rows` carries the whole row, including the
            # exception type and message this command used to discard. `missing` stays the
            # id list.
            print(json.dumps({"version": _version(),
                              "modules": {r["module"]: r["status"] for r in rows},
                              "module_rows": rows,
                              "missing": missing}, indent=2))
        else:
            print(f"armature-studio {_version()}\n")
            for r in rows:
                print(f"  {r['module']:<16} {r['status']}")
                # The CAUSE, beside the module, in the output an operator actually reads.
                if r["error"]:
                    print(f"  {'':<16} {r['error']}: {r['message']}"
                          + (f" (no module named {r['missing_root']!r})"
                             if r["missing_root"] else ""))
            print()
            print("all modules resolved" if not missing
                  else f"UNRESOLVED: {', '.join(missing)}")
        # A broken install is a broken install and the exit code says so.
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
