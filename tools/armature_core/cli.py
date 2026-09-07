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

Beyond the signpost commands (`modules`, `check`, `where`), this CLI also runs the
paid-path gates that ship inside the wheel: `armature canon …` (Gate CANON) and
`armature verify` (Gate ROUTE / PAIR). Those wrap library entry points already in
`armature_core`; they do not pull Blender render scripts into the console script.
"""
import argparse
import ast
import importlib
import importlib.util
import json
import os
import re
import sys
import textwrap

REPO = "https://github.com/mcp-tool-shop-org/armature"
DOCS = "https://mcp-tool-shop-org.github.io/armature/"


def _halt(prefix, exc):
    """Print `<PREFIX>_HALT` with the six-key receipt and return the exit code."""
    from .errors import ArmatureError
    from .parts import halt_keysafe, halt_outcome, printable_halt_line

    code, outcome = halt_outcome(exc)
    evidence = getattr(exc, "evidence", None)
    record = {
        "tool": prefix.lower(),
        "outcome": outcome,
        "gate": getattr(exc, "gate", None),
        "error": type(exc).__name__,
        "message": str(exc),
        "evidence": halt_keysafe(evidence) if evidence is not None else None,
    }
    line = json.dumps(record, default=str, allow_nan=False, sort_keys=True)
    print(printable_halt_line(f"{prefix}_HALT {line}"))
    return code if isinstance(exc, ArmatureError) else 1


def _ok(prefix, payload):
    print(f"{prefix}_OK " + json.dumps(payload, default=str, allow_nan=False,
                                       sort_keys=True))
    return 0


def _load_census(path):
    if not path:
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _cmd_canon_resolve(args):
    from . import canon as C
    from . import canon_census
    from .errors import GateCanon

    census = _load_census(args.census)
    rec = canon_census.row(args.subject, census=census)
    if rec is None:
        raise GateCanon(
            f"unknown subject {args.subject!r}: it is in no canon census this "
            f"invocation can see, so nothing can be resolved for it",
            {"gate": "CANON", "andon": "GateCanon", "clause": "unknown_subject",
             "subject": args.subject, "census": args.census, "roots": args.roots})
    if rec.get("surfaces") is None:
        print(f"IDENTITY_ONLY {args.subject}")
        if rec.get("reason"):
            print(rec["reason"])
        return _ok("CANON", {"cmd": "resolve", "subject": args.subject,
                             "verdict": "IDENTITY_ONLY"})
    doc = C.resolve(args.subject, census=census, search_roots=args.roots)
    print(f"RESOLVED {args.subject} {doc['_path']}")
    print(json.dumps(C.coverage(doc), indent=2))
    return _ok("CANON", {"cmd": "resolve", "subject": args.subject,
                         "path": doc["_path"], "verdict": "RESOLVED"})


def _cmd_canon_coverage(args):
    from . import canon as C

    doc = C.load(args.canon)
    cov = C.coverage(doc)
    print(json.dumps(cov, indent=2))
    return _ok("CANON", {"cmd": "coverage", "path": args.canon, **{
        k: cov[k] for k in ("ratified", "holes") if k in cov}})


def _cmd_canon_check(args):
    from . import canon as C

    if args.canon:
        doc = C.load(args.canon)
    else:
        doc = C.resolve(args.subject, census=_load_census(args.census),
                        search_roots=args.roots)
    ev = C.cover(doc, args.prompt)
    print(json.dumps({k: ev[k] for k in ev if k != "prompt"}, indent=2))
    return _ok("CANON", {"cmd": "check", "verdict": ev.get("verdict")})


def _cmd_canon_spend(args):
    from . import canon as C
    from .errors import GateCanon

    # Same andon tools/canon_gate.gate_canon_ships_what_it_gated carries: the text
    # handed to the router IS the text being sent.
    if args.canon_prompt is not None and args.canon_prompt != args.prompt:
        raise GateCanon(
            "--canon-prompt is not the text this payload ships. The router would have "
            "checked one string while the graph carried another, and every other gate "
            "would still be green. Either fix the shipped prompt or drop the flag",
            {"gate": "CANON", "andon": "GateCanon",
             "clause": "gated_text_is_not_shipped_text",
             "canon_prompt": args.canon_prompt, "shipped": args.prompt})
    ev = C.gate_write(
        args.subject, args.prompt,
        no_canon=args.no_canon, out_dir=args.out,
        census=_load_census(args.census), search_roots=args.roots,
    )
    line = ev.get("announcement") or f"[canon] {ev.get('verdict')}: {ev.get('subject')}"
    print(line)
    print(json.dumps(ev, indent=2, default=str))
    return _ok("CANON", {"cmd": "spend", "verdict": ev.get("verdict"),
                         "subject": ev.get("subject")})


def _parse_frame(text):
    """`W,H,L` → (width, height, length). argparse eats leading minus signs — pass
    `--frame=-16,480,81` if a signed probe is ever needed."""
    parts = [p.strip() for p in text.split(",")]
    if len(parts) != 3:
        raise SystemExit(f"--frame needs width,height,length; got {text!r}")
    try:
        return tuple(int(p) for p in parts)
    except ValueError as exc:
        raise SystemExit(f"--frame values must be ints: {text!r}") from exc


def _cmd_verify(args):
    from . import route_gates as RG

    graph = RG.load_graph(args.graph)
    frame = _parse_frame(args.frame) if args.frame else None
    attribution = ()
    if args.attribution:
        raw = json.loads(args.attribution)
        attribution = tuple(raw) if isinstance(raw, list) else (raw,)
    ev = RG.verify(
        graph,
        family=args.family,
        frame=frame,
        hosted_tier=args.hosted_tier,
        allow=tuple(args.allow or ()),
        carries_no_sampler=args.carries_no_sampler,
        attribution=attribution,
    )
    print(json.dumps(ev, indent=2, default=str))
    return _ok("VERIFY", {"cmd": "verify", "graph": args.graph,
                          "family": args.family,
                          "frame_legality_verdict": ev.get("frame_legality_verdict")})


class _EpilogUnwrapped(argparse.HelpFormatter):
    """Keep newlines in the epilog (the repo URL); description still fills."""

    def _fill_text(self, text, width, indent):
        # ArgumentParser.format_help routes epilog through add_text → _fill_text,
        # which collapses newlines. Preserve them when the epilog carries the URL.
        if REPO in text or text.lstrip().startswith("Rendering scripts"):
            return "".join(indent + line + "\n" for line in text.splitlines())
        return super()._fill_text(text, width, indent)

#: The modules that make up the installed surface, with what each one is for. Kept as
#: data rather than prose so `armature modules --json` can hand it to a machine.
#:
#: ⚠ **A row may only name a gate the module beside it carries**, and **every gate a
#: SURFACE module carries must be named in a SURFACE row.** The `route_gates` row once
#: read "graph-level gates: ROUTE, PAIR, PAIR_TIER, LEDGER" and that module defines
#: exactly two gate classes; PAIR_TIER and LEDGER live in `tools/build_lora_arm_payload.py`
#: and LEDGER_W3 in `tools/build_camera_i2v_payload.py`, none of which is in the installed
#: package at all. The reverse drift was measured 2026-09-06: 19 of 32 package gate ids
#: (CANON, N, P, D, TURN, …) appeared in no row, so a halt's `"gate"` field could not be
#: turned back into a module from the installed package. Both directions are pinned:
#: `test_every_gate_named_in_the_surface_exists_in_the_module_beside_it` and
#: `test_every_gate_a_surface_module_carries_is_named_in_a_surface_row`. `--json` also
#: carries a mechanical `gates` list per row.
SURFACE = [
    ("gates", "pure predicates that RAISE; no bpy, no I/O — gates: G1, G2, G4, G5, G6, "
              "R, B, S"),
    ("route_gates", "graph-level gates: ROUTE, PAIR"),
    ("canon", "surface-keyed character statement, both-direction router, fail-closed "
              "spend — Gate CANON"),
    ("canon_census", "which subjects have a surfaces file, as data — Gate CANON"),
    ("rig_gates", "rig and skeleton gates: N, P, D"),
    ("donor_gate", "Gate DONOR — is this clip fit to be a baseline before anything is lifted"),
    ("shotspec", "the shot-spec contract: schema, load, resolve, hash"),
    ("subject", "what a subject asset is, as a number rather than as a filename"),
    ("framing", "camera framing and projection, perspective and orthographic — Gate PIN"),
    ("turnaround", "turnaround planning, the projection plan — gates: TURN, ALPHA, CROP"),
    ("startframe", "start-frame measurement: silhouette extent, mask bbox — "
                   "gates: WHOLE, ALPHA, BACKDROP"),
    ("channels", "channel maths: normalization, edge derivation, encoding"),
    ("openpose", "the OpenPose-18 convention"),
    ("aapose", "AAPose stick construction"),
    ("landmarks", "landmark extraction — Gate FACING"),
    ("lift_solve", "land 33 MediaPipe-topology landmarks on the 22-bone rig, as rotations "
                   "— Gate SOLVE"),
    ("joints", "joint and skeleton maths"),
    ("binding", "procedural rigid-per-segment skinning, testable without bpy"),
    ("parts", "split a shell mesh into rigid per-segment parts — gates: PARTS, RIGID, D"),
    ("posearc", "authored performances for the procedural wire subject"),
    ("walk", "the gait model — a walk, a stop and an emote, as numbers — "
             "gates: GAIT, CADENCE"),
    ("resample", "control-sequence resampling — Gate RESAMPLE"),
    ("assembly", "the assembly graph: frames in, one VIDEO out, no partner credit — "
                 "gates: ASSEMBLY, CASCADE"),
    ("sitelist", "the registered site list, as data"),
    ("clipstats", "clip statistics"),
    ("clipcompare", "clip comparison"),
    ("glb", "GLB reading helpers — gates: ATLAS, RELIFT"),
    ("pngio", "a dependency-free PNG writer"),
    ("errors", "the exception types the gates raise — gates: G1, G2, G4, G5, G6, R, B, S, "
               "N, P, D, CANON"),
    ("blender_scene", "the only module that imports bpy — needs Blender's interpreter — "
                      "gates: COMPOSITOR, FRAME"),
]


def _version():
    """The installed version, or a marker when running from a source checkout."""
    try:
        from importlib.metadata import version

        return version("armature-studio")
    except Exception:
        return "0.0.0+source"


def _gates_carried(name):
    """Gate ids this SURFACE module exposes as `GateFailure` subclasses.

    The mechanical half of `armature modules --json`: a consumer holding only a halt
    record's `"gate"` field can find the module without parsing purpose prose. For
    `blender_scene` — which cannot import under plain CPython — the ids are read from
    the source's `gate = "..."` class attributes, the same population an import would
    expose.
    """
    from .errors import GateFailure

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{name}.py")
    if name == "blender_scene":
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            return []
        return sorted(set(
            m.group(1) for m in re.finditer(
                r'^\s*gate\s*=\s*"([A-Z][A-Z0-9_]*)"', text, re.M)
            if m.group(1) != "G?"
        ))
    try:
        mod = importlib.import_module(f"armature_core.{name}")
    except Exception:  # noqa: BLE001 — a broken module still lists as a row with no gates
        return []
    return sorted({
        getattr(obj, "gate")
        for obj in vars(mod).values()
        if isinstance(obj, type)
        and issubclass(obj, GateFailure)
        and obj is not GateFailure
        and getattr(obj, "gate", None)
        and getattr(obj, "gate") != "G?"
    })


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


def _print_module_row(name, purpose, width=80):
    """Name column 16 wide; purpose wraps under its own column, never past width."""
    prefix = f"  {name:<16} "
    body_width = max(16, width - len(prefix))
    lines = textwrap.wrap(
        purpose, width=body_width,
        break_long_words=False, break_on_hyphens=False,
    ) or [""]
    print(prefix + lines[0])
    hang = " " * len(prefix)
    for line in lines[1:]:
        print(hang + line)


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="armature",
        description="armature — you block the shot; the model shoots it. "
        "GLB-authored previz for video-diffusion generation.",
        epilog=("Rendering scripts run inside Blender, from the repo:\n"
                f"{REPO}"),
        formatter_class=_EpilogUnwrapped,
    )
    ap.add_argument("--version", action="version", version=f"armature-studio {_version()}")
    sub = ap.add_subparsers(dest="cmd", title="commands", metavar="COMMAND")

    p_mod = sub.add_parser("modules", help="list the installed modules and what each is for")
    p_mod.add_argument("--json", action="store_true", help="machine-readable output")

    p_chk = sub.add_parser("check", help="import every module and report what resolved")
    p_chk.add_argument("--json", action="store_true", help="machine-readable output")

    sub.add_parser("where", help="print where the docs and the render scripts live")

    # Gate CANON — the four subcommands tools/canon_gate.py exposes, on the installed
    # console script (F-4b9ee614). Nested under `canon` so the top-level `check`
    # (import probe) keeps its name.
    p_canon = sub.add_parser(
        "canon",
        help="Gate CANON: resolve, coverage, check, or spend",
        description=(
            "Gate CANON at the command line: resolve a subject to its canon, measure "
            "coverage, check a prompt, or run the spend gate every payload builder "
            "calls before authoring a submission."),
    )
    p_canon.add_argument("--roots", action="append", default=None,
                         help="a canon root directory to search; repeatable")
    p_canon.add_argument("--census", default=None, help="override census JSON")
    canon_sub = p_canon.add_subparsers(dest="canon_cmd", required=True,
                                       metavar="{resolve,coverage,check,spend}")

    p_res = canon_sub.add_parser(
        "resolve", help="name the canon file a subject resolves to")
    p_res.add_argument("--subject", required=True)
    p_res.set_defaults(_canon_func=_cmd_canon_resolve)

    p_cov = canon_sub.add_parser(
        "coverage", help="report what a canon file covers")
    p_cov.add_argument("--canon", required=True, help="the canon file to measure")
    p_cov.set_defaults(_canon_func=_cmd_canon_coverage)

    p_cchk = canon_sub.add_parser(
        "check", help="check a prompt against a canon; spends nothing")
    p_cchk.add_argument("--subject", default=None)
    p_cchk.add_argument("--canon", default=None,
                        help="canon file instead of resolving --subject")
    p_cchk.add_argument("--prompt", required=True)
    p_cchk.set_defaults(_canon_func=_cmd_canon_check)

    p_spend = canon_sub.add_parser(
        "spend", help="the spend gate every payload builder calls")
    from . import canon as _canon_mod
    _canon_mod.add_spend_flags(p_spend)
    p_spend.add_argument("--prompt", dest="prompt", required=True,
                         help="the prompt that will actually be sent; this is gated")
    p_spend.add_argument("--out", default=None,
                         help="directory to write the canon evidence JSON into")
    p_spend.set_defaults(_canon_func=_cmd_canon_spend)

    # Gate ROUTE / PAIR — load a saved/API graph and run verify (F-656ac783).
    p_ver = sub.add_parser(
        "verify",
        help="Gate ROUTE/PAIR: load a graph and admit it before credits are spent",
        description=(
            "Run Gate ROUTE / PAIR on a saved or API-format graph. Pure CPython — "
            "no Blender. Reuses the frame/hosted-tier/attribution kwargs builders pass."),
    )
    p_ver.add_argument("graph", help="path to a saved or API-format graph JSON")
    p_ver.add_argument("--family", default="wan",
                       help="generator family or G1 profile name (default: wan)")
    p_ver.add_argument("--frame", default=None,
                       help="width,height,length to supply to Gate L "
                            "(argparse eats leading minus signs: pass --frame=W,H,L)")
    p_ver.add_argument("--hosted-tier", default=None, dest="hosted_tier",
                       help="hosted tier name when the graph carries no pixel latent")
    p_ver.add_argument("--allow", action="append", default=None,
                       help="component key with an explicit ruling; repeatable")
    p_ver.add_argument("--attribution", default=None,
                       help="JSON list/object of attribution entries for CONDITIONAL rows")
    p_ver.add_argument("--carries-no-sampler", action="store_true",
                       dest="carries_no_sampler",
                       help="assert the graph is not expected to carry a sampler")

    a = ap.parse_args(argv)

    if a.cmd == "modules":
        if a.json:
            print(json.dumps([{"module": m, "purpose": d, "gates": _gates_carried(m)}
                              for m, d in SURFACE], indent=2))
        else:
            print(f"armature_core — {len(SURFACE)} modules\n")
            for m, d in SURFACE:
                _print_module_row(m, d)
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
                # `needs-blender` is EXPECTED outside Blender — say so in the same words
                # `armature where` already prints, not as an exception line that sits next
                # to "all modules resolved" and reads as a broken install.
                if r["status"] == "needs-blender":
                    print(f"  {'':<16} render scripts run inside Blender, "
                          f"from a repo checkout")
                elif r["error"]:
                    # The CAUSE, beside the module. Suppress the parenthetical when
                    # `missing_root` is already inside `message` — for ModuleNotFoundError
                    # `str(exc)` IS "No module named '<root>'", so appending the same
                    # fact duplicated the line the operator reads first.
                    cause = f"{r['error']}: {r['message']}"
                    root = r["missing_root"]
                    if root and root not in (r["message"] or ""):
                        cause += f" (no module named {root!r})"
                    print(f"  {'':<16} {cause}")
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

    if a.cmd == "canon":
        from .errors import ArmatureError
        try:
            return a._canon_func(a)
        except ArmatureError as exc:
            return _halt("CANON", exc)

    if a.cmd == "verify":
        from .errors import ArmatureError
        try:
            return _cmd_verify(a)
        except ArmatureError as exc:
            return _halt("VERIFY", exc)

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
