"""One implementation of the nodes this suite's censuses key on.

**Why this module exists.** Wave 12's rule is that a census keys on BEHAVIOUR, not on a
spelling — and the cheapest way to break that rule is to write the walk twice. Three
wave-11 findings are exactly that shape:

* `F-0e0709b2` — `tests/test_sheet_pairing.py`'s flag census started from the module-level
  function literally called `main`, while `tests/test_canon_spend.py` and
  `tests/test_instrument_write_ordering.py` each carried their own copy of `_cli_body`,
  which follows one delegation out of a wrapper `main`. Three builders moved their argv
  parsing into `build_and_write(argv)` in wave 10 and left the flag census; an undeclared
  read on any of the three was invisible.
* `F-1c9d39e2` — `tests/test_sheet_argv_smoke.py` carried a SECOND "a flag that is read and
  never declared" walk that resolves no cross-module helper and no `set_defaults`, so it
  reports six correct modules as offenders. Two walks, one law.
* `F-e63ce880` — `_called_name`, `_is_gate_call` and `_cli_body` were byte-identical between
  `test_canon_spend.py` and `test_instrument_write_ordering.py` (identical 1901-character
  AST dumps) and only the second applied the mutually-exclusive-branch correction, so the
  two files answered differently about `encode_control`, `measure_cascade_clip` and
  `rig_character`. `_spend_and_fetch_tools` was duplicated the same way between
  `test_amend_w10_builders.py` and `test_packaging.py` — a census POPULATION derived twice.

So every walk below has exactly one home. The importing test modules pass their own
constants in (`canon_calls`, `other_gate_calls`), which is what made two copies look
necessary; a parameter is not a second implementation.

Helpers under `tests/` **raise**; they never `assert` — `-O` deletes an `assert` in a
non-plugin helper and `ci.yml`'s `-O` leg would report green over it
(`test_gate_survives_optimize.py::test_no_helper_under_tests_checks_anything_with_assert`).
"""

import ast
import glob
import os
import re
import sys

TESTS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TESTS)
TOOLS = os.path.join(REPO, "tools")


# ------------------------------------------------------------------ reading the tree


def tool_paths(include_core=False):
    """Every `tools/*.py`, optionally with `tools/armature_core/*.py` beside it."""
    paths = sorted(glob.glob(os.path.join(TOOLS, "*.py")))
    if include_core:
        paths += sorted(glob.glob(os.path.join(TOOLS, "armature_core", "*.py")))
    return paths


def read_source(name):
    """The source of `tools/<name>.py` (a bare stem or a filename, either way)."""
    fn = name if name.endswith(".py") else name + ".py"
    with open(os.path.join(TOOLS, fn), encoding="utf-8") as fh:
        return fh.read()


def module_trees(include_core=True):
    """`{module name: ast.Module}` for `tools/*.py` (and `tools/armature_core/*.py`).

    Keyed by BASENAME, and one basename is claimed twice: `lift_solve` exists as both
    `tools/lift_solve.py` (the Blender-side CLI) and `tools/armature_core/lift_solve.py`
    (the pure solver). Measured 2026-09-04 in this worktree: the core module was parsed
    LAST and won the key, so every tool-keyed census that looked up `TREES["lift_solve"]`
    — `parser_population`, `declared_flags`, `namespace_reads` — walked the solver, which
    has no `main` at all. `tools/lift_solve.py` therefore reported "no command line" while
    declaring 5 flags and reading all 5 off its namespace, and sat outside the
    undeclared-flag property and the `--help` smoke alike. The tool wins its own basename
    now; `tool_trees()` below is the collision-free population for anything tool-keyed, and
    `test_sheet_pairing.py` pins the collision by name so a second one cannot land quietly.
    """
    out = {}
    paths = sorted(glob.glob(os.path.join(TOOLS, "armature_core", "*.py"))) if include_core else []
    paths += sorted(glob.glob(os.path.join(TOOLS, "*.py")))
    for path in paths:
        with open(path, encoding="utf-8") as fh:
            out[os.path.basename(path)[:-3]] = ast.parse(fh.read())
    return out


def tool_trees():
    """`{module name: ast.Module}` for `tools/*.py` ONLY — no `armature_core` shadowing."""
    out = {}
    for path in sorted(glob.glob(os.path.join(TOOLS, "*.py"))):
        with open(path, encoding="utf-8") as fh:
            out[os.path.basename(path)[:-3]] = ast.parse(fh.read())
    return out


def colliding_basenames():
    """Module basenames claimed by BOTH `tools/` and `tools/armature_core/`."""
    tools = {os.path.basename(p)[:-3] for p in glob.glob(os.path.join(TOOLS, "*.py"))}
    core = {os.path.basename(p)[:-3]
            for p in glob.glob(os.path.join(TOOLS, "armature_core", "*.py"))}
    return sorted(tools & core)


def tools_calling_add_argument():
    """Every `tools/*.py` that declares a command-line argument — the parser POPULATION.

    The census's own population must be derived from the thing it is about (a parser),
    never from the idiom a tool happens to use to reach one. `parser_population()` is
    asserted against this set, so a tool cannot leave the census by moving its parser into
    a helper (which is exactly what 31 of them had done — F-beeab1d0).
    """
    out = []
    for path in sorted(glob.glob(os.path.join(TOOLS, "*.py"))):
        with open(path, encoding="utf-8") as fh:
            if "add_argument(" in fh.read():
                out.append(os.path.basename(path)[:-3])
    return out


# ------------------------------------------------------------------- the CLI body node


def called_name(node):
    """The bare callee name of a `Call` node — `f(...)` and `x.f(...)` both give `f`."""
    func = node.func
    return (func.id if isinstance(func, ast.Name)
            else func.attr if isinstance(func, ast.Attribute) else "")


def cli_body(tree):
    """The module-level function that IS the tool's command line — derived, not named.

    The census used to key on the function literally called `main`. That was the right node
    only while every tool's `main` held its own body: wave 10 split three builders'
    (`build_assembly_payload`, `build_cascade_payload`, `build_r2v_payload`) into
    `build_and_write(argv)` — which builds, gates and writes — plus a `main(argv)` that
    returns the process exit code and nothing else, because `main` used to `return wf`
    under `raise SystemExit(main())` and exited 1 on a fully gated success. Keyed on the
    NAME, a census reports "runs no in-tool refusal at all", or "declares no flags", for
    three tools whose refusals and parsers had not moved an inch.

    The derivation follows ONE delegation, and only out of a `main` that is a wrapper and
    nothing else: at most three statements (its docstring aside) and exactly one call to a
    module-level function of its own module. That function is then the body. Every other
    `main` — including the eight builders that never split — is read exactly as before.
    (An earlier draft keyed on "which function calls `parse_args`". Three builders define a
    module-level helper literally named `parse_args`, so it picked the helper and reported
    the same false emptiness one level down. Measured 2026-09-04.)
    """
    named = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    fn = named.get("main")
    if fn is None:
        return None
    body = [st for st in fn.body
            if not (isinstance(st, ast.Expr) and isinstance(st.value, ast.Constant))]
    if len(body) > 3:
        return fn
    # WAVE 16 (F-beeab1d0): a parser HELPER is never the delegate. A short `main` that reads
    # `a = parse_args(argv)` and hands the result on has one module-local call, and the hop
    # used to land inside `parse_args` — which holds the parser and none of the reads, so the
    # census reported the tool as reading nothing. That is the exact false emptiness this
    # docstring's last paragraph records, arriving through the wrapper rule instead of
    # through the node choice. The delegate is the function that holds the BODY.
    helpers = parser_helpers(tree)
    called = {c.func.id for c in ast.walk(fn)
              if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
              and c.func.id in named and c.func.id not in helpers}
    if len(called) == 1:
        return named[next(iter(called))]
    return fn


def parser_helpers(tree):
    """`{name: "attr" | "dict"}` — module-level functions that RETURN a parsed namespace.

    The repo's DOMINANT argparse idiom, and the one `cli_body`'s one-hop rule does not
    reach: 31 of the 67 tools that call `add_argument(` factor their parser into a
    module-level helper and write `a = parse_args(argv)` in the body — a bare `ast.Name`
    call, where the walk below used to look only for an `ast.Attribute` call spelled
    `ap.parse_args(argv)`. Keyed on what the helper DOES (it parses), never on the name
    `parse_args`, so a helper called `_cli` or `read_argv` joins on the day it lands.

    The value says how the caller reads the result. `"attr"` is a `Namespace` and its
    flags are attribute reads; `"dict"` is `vars(p.parse_args(argv))` — four Blender-side
    tools (`make_rig_sheet`, `rig_bake`, `rig_repair`, `rig_retopo`) return that, and their
    flags are constant-string subscripts. Same defect, same census, two spellings.

    Keyed on the RETURN, not on "contains a `parse_args` call anywhere". `build_and_write`
    in the three wave-10 builders parses argv too, but it goes on to gate and write and
    returns none of it — it is the CLI body, and treating it as a parser helper dropped all
    three out of the population (measured 2026-09-04 while writing this).
    """
    def _is_parse(node):
        return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in ("parse_args", "parse_known_args"))

    out = {}
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        # names this function binds from a parse — `render_turnaround.parse_args` binds `a`,
        # decorates it with `a.ortho_scale_text = ...`, and returns the NAME, not the call
        local = _namespace_bindings(node, {})
        for n in ast.walk(node):
            if not isinstance(n, ast.Return) or n.value is None:
                continue
            value, kind = n.value, "attr"
            if (isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
                    and value.func.id == "vars" and value.args):
                value, kind = value.args[0], "dict"
            # RE-DERIVED wave 22 (instruments, F-798281dc): `local.get(...)` is read for
            # BOTH kinds. `return a` after `a = vars(p.parse_args(argv))` is a "dict"
            # helper, and reading only "attr" here dropped `rig_bake` out of the
            # population the moment its parser gained a refusal.
            if _is_parse(value):
                out[node.name] = kind
                break
            if isinstance(value, ast.Name) and local.get(value.id) in ("attr", "dict"):
                out[node.name] = local[value.id]
                break
    return out


def _namespace_bindings(fn, helpers):
    """`{local name: "attr"|"dict"}` for every name in `fn` bound to a parsed namespace."""
    ns = {}
    for node in walk_scope(fn):
        if not (isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)):
            continue
        func = node.value.func
        # RE-DERIVED wave 22 (instruments, F-798281dc): the `vars(...)` spelling, BOUND.
        # `parser_helpers` already reads `return vars(p.parse_args(argv))` as kind
        # "dict"; this walk read only the ATTRIBUTE call, so a helper that binds
        # `a = vars(p.parse_args(argv))`, refuses on the parsed values and then
        # `return a` bound nothing -- and its tool left `parser_population` entirely.
        # MEASURED on this branch when `rig_bake.parse_args` gained its two bounds:
        # `namespace_reads(rig_bake)` returned `{}` and `CLI_TOOLS` fell from 67 to 66
        # on a tool that declares five flags and reads four. A census that keys on the
        # spelling cannot see a tool leaving it (wave-18 rule 1).
        if (isinstance(func, ast.Name) and func.id == "vars" and node.value.args
                and isinstance(node.value.args[0], ast.Call)
                and isinstance(node.value.args[0].func, ast.Attribute)
                and node.value.args[0].func.attr in ("parse_args",
                                                     "parse_known_args")):
            kind = "dict"
        elif isinstance(func, ast.Attribute) and func.attr in ("parse_args",
                                                               "parse_known_args"):
            kind = "attr"
        elif isinstance(func, ast.Name) and func.id in helpers and func.id != fn.name:
            kind = helpers[func.id]
        else:
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                ns[target.id] = kind
            elif isinstance(target, ast.Tuple):
                for elt in target.elts:
                    if isinstance(elt, ast.Name):
                        ns[elt.id] = kind
                        break
    return ns


def cli_bodies(tree):
    """Every scope that holds this tool's command line — usually one, sometimes two.

    `cli_body` is the anchor and stays the anchor. The second edge is the DISPATCH idiom:
    a `main` that parses nothing itself and hands a module-local function to a shared
    runner — `tools/armature_index.py`'s `return _cli.run_contract(_dispatch, argv, ...)`,
    where `_dispatch` builds the parser, parses argv and reads six flags off it. A census
    anchored on `main` alone sees no parser there at all. The edge is deliberately narrow
    — it opens ONLY when the CLI body binds no namespace of its own, and only to a
    module-local function passed BY NAME as an argument that does bind one — because the
    wide version (any module-local function passed as any argument) pulls in sibling
    scopes and re-invents the six false positives `test_sheet_argv_smoke.py` records.
    """
    body = cli_body(tree)
    if body is None:
        return []
    helpers = parser_helpers(tree)
    if _namespace_bindings(body, helpers):
        return [body]
    named = {n.name: n for n in tree.body
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    out = []
    for node in walk_scope(body):
        if not isinstance(node, ast.Call):
            continue
        for arg in list(node.args) + [kw.value for kw in node.keywords]:
            if not (isinstance(arg, ast.Name) and arg.id in named):
                continue
            fn = named[arg.id]
            if fn is not body and fn not in out and _namespace_bindings(fn, helpers):
                out.append(fn)
    return out or [body]


def walk_scope(fn):
    """Every node belonging to `fn` ITSELF — stops at nested defs, lambdas and classes.

    NON-DESCENDING on purpose (SEAM 9, instruments-measure, 2026-09-04): a sibling scope's
    local named `a` — a numpy array, say — makes `a.shape` and `a.ndim` read as argparse
    namespace attributes, which is how a descending walk invents five offenders out of
    `composite_reference`, `encode_control`, `fit_reference`, `make_plate` and
    `pack_pose_pack`.
    """
    stack = list(fn.body)
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda,
                             ast.ClassDef)):
            continue
        yield node
        stack.extend(ast.iter_child_nodes(node))


# ------------------------------------------------------------------ the flag-parser node


def argparse_dests(node):
    """Every namespace attribute an `add_argument`/`set_defaults`/`add_subparsers` creates."""
    out = set()
    for n in ast.walk(node):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)):
            continue
        if n.func.attr == "set_defaults":
            out.update(kw.arg for kw in n.keywords if kw.arg)
            continue
        if n.func.attr == "add_subparsers":
            out.update(kw.value.value for kw in n.keywords
                       if kw.arg == "dest" and isinstance(kw.value, ast.Constant))
            continue
        if n.func.attr != "add_argument":
            continue
        explicit = [kw.value.value for kw in n.keywords
                    if kw.arg == "dest" and isinstance(kw.value, ast.Constant)]
        if explicit:
            out.add(explicit[0])
            continue
        longs = [a.value for a in n.args if isinstance(a, ast.Constant)
                 and isinstance(a.value, str) and a.value.startswith("--")]
        if longs:
            out.add(longs[0][2:].replace("-", "_"))
            continue
        positional = [a.value for a in n.args if isinstance(a, ast.Constant)
                      and isinstance(a.value, str) and not a.value.startswith("-")]
        if positional:
            out.add(positional[0].replace("-", "_"))
    return out


def flag_helpers(trees):
    """`{(module, function): dests}` for every function that adds flags to a parser.

    Keyed by MODULE and function, never by bare name: a name-keyed table unions every
    module's `main` into one entry and reported the whole census green (measured while
    writing it — `sheet_plate` arrived from `make_identity_sheet.main`).
    """
    out = {}
    for mod, tree in trees.items():
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                dests = argparse_dests(node)
                if dests:
                    out[(mod, node.name)] = dests
    return out


def visible_functions(tree, mod):
    """`{local name: (module, function)}` — module-local defs plus `from X import f`."""
    vis = {n.name: (mod, n.name) for n in tree.body
           if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            src = node.module.split(".")[-1]
            for alias in node.names:
                vis[alias.asname or alias.name] = (src, alias.name)
    return vis


def _namespace_writes(fn, ns):
    """Attributes the code ITSELF puts on a bound namespace — `a.x = ...`.

    `set_defaults(x=...)`'s hand-rolled twin, and a real declaration: after
    `tools/render_turnaround.py:325` runs `a.ortho_scale_text = _pinned_text(argv)` inside
    its own parser helper, the attribute is on the namespace as surely as any
    `add_argument` put it there. Reading it downstream is not the gate-0 defect, and a
    census that called it one would be reporting a correct module.
    """
    out = set()
    for node in walk_scope(fn):
        targets = (node.targets if isinstance(node, ast.Assign)
                   else [node.target] if isinstance(node, (ast.AnnAssign, ast.AugAssign))
                   else [])
        for target in targets:
            if (isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name)
                    and ns.get(target.value.id) == "attr"):
                out.add(target.attr)
            if (isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name)
                    and ns.get(target.value.id) == "dict"
                    and isinstance(target.slice, ast.Constant)
                    and isinstance(target.slice.value, str)):
                out.add(target.slice.value)
    return out


def declared_flags(tree, mod, helpers):
    """Everything the tool's parser can put on the namespace, helper calls resolved.

    Keyed on `cli_bodies`, not on the name `main` (F-0e0709b2): the three wave-10 builders
    declare their flags inside `build_and_write(argv)`, and `armature_index` declares its
    six inside the `_dispatch` it hands to a shared runner.

    The helper resolution is TRANSITIVE over module-local functions that contribute flags
    (F-beeab1d0): `build_animate_payload.main` calls `parse_args(argv)`, and `parse_args`
    calls `add_spend_flags(ap)` from `armature_core.canon` — one hop reaches the local
    helper and stops, so the three canon flags read in `main` looked undeclared. Only
    functions that themselves declare a flag or return a parsed namespace are followed, so
    an unrelated local call cannot widen the declared set and mask a real undeclared read.
    """
    bodies = cli_bodies(tree)
    if not bodies:
        return set()
    parsers = parser_helpers(tree)
    named = {n.name: n for n in tree.body
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    vis = visible_functions(tree, mod)
    out = set()
    for node in tree.body:  # a parser built at module level
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out |= argparse_dests(node)
    seen, stack = set(), list(bodies)
    while stack:
        fn = stack.pop()
        if fn.name in seen:
            continue
        seen.add(fn.name)
        out |= argparse_dests(fn)
        out |= _namespace_writes(fn, _namespace_bindings(fn, parsers))
        for node in ast.walk(fn):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
                continue
            name = node.func.id
            if vis.get(name) in helpers:
                out |= helpers[vis[name]]
            local = named.get(name)
            if (local is not None and name not in seen
                    and (name in parsers or argparse_dests(local))):
                stack.append(local)
    return out


def namespace_reads(tree):
    """`{flag: first line}` read off whatever `parse_args` returned, in the CLI bodies.

    Two spellings of the read, because the tools use two: `a.frames_dir` off a
    `Namespace`, and `args["frames_dir"]` off the `vars(...)` dict four Blender-side tools
    return. Both are "a flag this tool reads"; a walk that saw only the first left those
    four outside the property that exists to catch a flag read and never declared.
    """
    out = {}
    parsers = parser_helpers(tree)
    for body in cli_bodies(tree):
        ns = _namespace_bindings(body, parsers)
        for node in walk_scope(body):
            if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                    and ns.get(node.value.id) == "attr"):
                out.setdefault(node.attr, node.lineno)
            elif (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name)
                    and ns.get(node.value.id) == "dict"
                    and isinstance(node.slice, ast.Constant)
                    and isinstance(node.slice.value, str)):
                out.setdefault(node.slice.value, node.lineno)
    return out


def undeclared_flags(tree, mod, helpers):
    """`{attribute: line}` the CLI body reads and its own parser never declares."""
    declared = declared_flags(tree, mod, helpers)
    return {k: v for k, v in sorted(namespace_reads(tree).items()) if k not in declared}


def parser_population(trees=None):
    """Every `tools/*.py` whose CLI body reads a `parse_args` namespace.

    Defaults to `tool_trees()`, never to `module_trees()`: the latter is keyed by basename
    and `armature_core/lift_solve.py` shadowed `tools/lift_solve.py` there. Callers that
    pass their own dict get what they passed.
    """
    trees = tool_trees() if trees is None else trees
    return sorted(mod for mod in trees
                  if os.path.exists(os.path.join(TOOLS, mod + ".py"))
                  and namespace_reads(trees[mod]))


# ---------------------------------------------------- the refusal node, keyed on BEHAVIOUR


#: The canon gate's three call names.
CANON_CALLS = ("gate_write", "canon_spend", "require_canon")


def armature_error_names():
    """Every `ArmatureError` subclass name, from the class hierarchy and from the tree.

    Two sources, unioned: the live hierarchy under `armature_core.errors.ArmatureError`
    (so a class added there joins without being remembered), plus every `class X(Y)` in
    `tools/**` whose base resolves — transitively — to one of those names. `walk.WalkError`
    was outside the family once and its twelve raises were examined by nothing (wave 10),
    which is why the AST half exists too.
    """
    names = set()
    try:
        if TOOLS not in sys.path:
            sys.path.insert(0, TOOLS)
        from armature_core import errors as _errors  # noqa: PLC0415

        stack = [_errors.ArmatureError]
        while stack:
            cls = stack.pop()
            if cls.__name__ in names:
                continue
            names.add(cls.__name__)
            stack.extend(cls.__subclasses__())
    except Exception:                                                   # noqa: BLE001
        names.add("ArmatureError")
    # the AST half: a subclass declared anywhere in the tree, resolved to a fixed point
    declared = {}
    for path in tool_paths(include_core=True):
        try:
            with open(path, encoding="utf-8") as fh:
                tree = ast.parse(fh.read())
        except SyntaxError:                                             # pragma: no cover
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                declared[node.name] = [
                    b.id if isinstance(b, ast.Name)
                    else b.attr if isinstance(b, ast.Attribute) else ""
                    for b in node.bases]
    grew = True
    while grew:
        grew = False
        for name, bases in declared.items():
            if name not in names and any(b in names for b in bases):
                names.add(name)
                grew = True
    return names


def is_refusal_call(name, canon_calls=CANON_CALLS, other_gate_calls=()):
    """The NAME half of the predicate — kept, because it is cheap and it is not wrong.

    It is not SUFFICIENT, which is F-183635ad: an inline `raise` is not a call at all, and
    a helper whose name matches none of these spellings is invisible to it. Behaviour is
    the union of this and the raise walk below.
    """
    return (name.startswith("gate_") or name.startswith("require_")
            or name in canon_calls or name in other_gate_calls)


def raise_sites(fn, error_names):
    """`{line: "raise <Class>"}` for every `raise <ArmatureError subclass>` in `fn` itself."""
    out = {}
    for node in walk_scope(fn):
        if not isinstance(node, ast.Raise) or node.exc is None:
            continue
        exc = node.exc
        if isinstance(exc, ast.Call):
            exc = exc.func
        name = (exc.id if isinstance(exc, ast.Name)
                else exc.attr if isinstance(exc, ast.Attribute) else "")
        if name in error_names:
            out[node.lineno] = f"raise {name}"
    return out


def functions_that_refuse(tree, error_names):
    """Module-level function names whose own body raises an `ArmatureError` subclass.

    ONE hop: a call to one of these, from the CLI body, is a refusal even though its name
    carries no `gate_`/`require_` prefix. `make_rig_sheet`'s andons are inline; several
    instruments route theirs through a helper called `plan`, `parse_boxes` or `frame_paths`.
    """
    out = set()
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if raise_sites(node, error_names):
            out.add(node.name)
    return out


def returning_branch_spans(fn):
    """Line spans of `if` bodies that end in a `return` or a `raise`.

    A write inside one of those is on a path that never reaches the code below it, so
    comparing its line number against a later refusal compares two mutually exclusive
    branches and reports a defect that cannot happen. Measured 2026-09-04 on
    `encode_control.main`: its `--survey` mode writes a codec report and returns, and the
    plate parse sixteen lines below is on the other branch.
    """
    spans = []
    for node in ast.walk(fn):
        if (isinstance(node, ast.If) and node.body
                and isinstance(node.body[-1], (ast.Return, ast.Raise))):
            spans.append((node.body[0].lineno, node.body[-1].end_lineno))
    return spans


def refusal_and_write_lines(src, *, error_names=None, canon_calls=CANON_CALLS,
                            other_gate_calls=(), by_name_only=False):
    """`({line: refusal}, {line: write kind})` for the tool's CLI body, or `(None, None)`.

    THE NODE (wave 12, F-183635ad): a refusal is any `raise` of an `ArmatureError`
    subclass — inline, or one hop through a module-local helper that raises one — plus the
    named gate calls. Keyed on the callee NAME alone, this walk could not see an inline
    `raise` at all, so a tool whose refusals are ALL inline never entered the population:
    `make_rig_sheet.main` creates `<out>/` and `<out>/panels/` and then raises
    `ArmatureError` three times below them, and the census reported nothing.

    `by_name_only=True` restores the pre-wave-12 predicate. It exists so the red proof can
    show, in one test, that the old walk is blind to the shape the new one sees.
    """
    error_names = armature_error_names() if error_names is None else error_names
    tree = ast.parse(src)
    fn = cli_body(tree)
    if fn is None:
        return None, None
    refusing = () if by_name_only else functions_that_refuse(tree, error_names)
    gates_at = {} if by_name_only else dict(raise_sites(fn, error_names))
    writes_at = {}
    for node in walk_scope(fn):
        if not isinstance(node, ast.Call):
            continue
        called = called_name(node)
        if is_refusal_call(called, canon_calls, other_gate_calls):
            gates_at.setdefault(node.lineno, called)
        elif isinstance(node.func, ast.Name) and called in refusing and called != fn.name:
            gates_at.setdefault(node.lineno, called)
        elif called == "makedirs":
            writes_at.setdefault(node.lineno, "os.makedirs")
        elif (called == "open" and len(node.args) >= 2
              and isinstance(node.args[1], ast.Constant)
              and "w" in str(node.args[1].value)):
            writes_at.setdefault(node.lineno, 'open(..., "w")')
    spans = returning_branch_spans(fn)
    for line in list(writes_at):
        for lo, hi in spans:
            if lo <= line <= hi and not any(lo <= g <= hi for g in gates_at):
                del writes_at[line]
                break
    return gates_at, writes_at


# ------------------------------------------------------------- the Blender-reach node


def imports_bpy(src):
    """`import bpy` / `from bpy... import` anywhere in the source — nesting included."""
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            if any(a.name == "bpy" or a.name.startswith("bpy.") for a in node.names):
                return True
        if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "bpy":
            return True
    return False


def documents_blender_invocation(src):
    """The tool's own text documents `blender -b -P <this file>`.

    `tools/stage_render.py` reaches Blender through a lazily-instantiated backend and
    contains no `import bpy` statement at all (F-6b3040d1); its documented invocation is
    `blender -b -P tools/stage_render.py -- <args>`. A population keyed on the literal
    token `import bpy` cannot see it, which is how the one tool that writes the run
    directory every downstream payload consumes sat outside every exit census.
    """
    return "blender -b -P" in src


def uses_blender_scene_backend(src):
    """The module reaches Blender through `armature_core.blender_scene`.

    The third spelling of the same behaviour, kept beside the other two so the population
    is "reaches Blender", not "spells it one of two ways".
    """
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.endswith("blender_scene"):
                return True
            if any(a.name == "blender_scene" for a in node.names):
                return True
        if isinstance(node, ast.Import):
            if any(a.name.endswith("blender_scene") for a in node.names):
                return True
    return False


def blender_reach(src):
    """The set of reasons this source runs under Blender — empty if it does not.

    Behaviour, three spellings: the import token, the documented invocation, the backend
    module. A tool is a Blender tool if ANY of them holds.
    """
    why = set()
    if imports_bpy(src):
        why.add("import bpy")
    if documents_blender_invocation(src):
        why.add("documented `blender -b -P`")
    if uses_blender_scene_backend(src):
        why.add("armature_core.blender_scene backend")
    return why


# ------------------------------------------------------------- shared tool populations


def spend_and_fetch_tools():
    """The CPU-side tools that author a submission, gate one, or retrieve its output.

    Every `tools/build_*payload*.py`, `tools/canon_gate.py`, `tools/fetch_*.py` and
    `tools/gate_saved_graph.py` — WALKED rather than typed. Lifted here from
    `test_packaging.py` and `test_amend_w10_builders.py`, which carried byte-identical
    copies: a census POPULATION derived twice means a correction to one is a silent drift
    in the other's membership (F-e63ce880).
    """
    return sorted(
        n for n in os.listdir(TOOLS)
        if n.endswith(".py")
        and ((n.startswith("build_") and "payload" in n)
             or n.startswith("fetch_")
             or n in ("canon_gate.py", "gate_saved_graph.py")))


# --------------------------------------------------- the output-gated guard node (wave 16)
#
# `outputs/` is gitignored, so a handful of tests can only run on a rig that has the run on
# disk. Each is guarded by a module-level constant that resolves a path under `outputs/` and
# a boolean derived from it. NOTHING enumerated that population, which is how the fifth such
# guard was written as a bare relative path four waves after the first four were anchored
# (F-269878af), and how the worktree/main skip delta had to be re-measured by three
# consecutive waves instead of read off the suite (F-665cd590).

TESTS_DIR = TESTS


def test_module_trees():
    """`{test module name: ast.Module}` for every `tests/test_*.py`."""
    out = {}
    for path in sorted(glob.glob(os.path.join(TESTS_DIR, "test_*.py"))):
        with open(path, encoding="utf-8") as fh:
            out[os.path.basename(path)[:-3]] = ast.parse(fh.read())
    return out


def _names_an_output_path(node):
    """The `outputs/...` string constants anywhere inside an expression."""
    found = []
    for n in ast.walk(node):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            text = n.value.replace("\\", "/")
            if text == "outputs" or text.startswith("outputs/"):
                found.append(n.value)
    return found


def _is_repo_anchored(node):
    """The expression resolves against the REPO root, not against `os.getcwd()`.

    Two spellings, both live in this suite: `conftest.repo_file("outputs/E02")` and
    `os.path.join(REPO, "outputs", ...)`. A bare `"outputs/E02"` is neither.
    """
    for n in ast.walk(node):
        if isinstance(n, ast.Call) and called_name(n) == "repo_file":
            return True
        if isinstance(n, ast.Name) and n.id in ("REPO", "TESTS", "FIXTURES"):
            return True
        if isinstance(n, ast.Attribute) and n.attr in ("REPO", "TESTS", "FIXTURES"):
            return True
    return False


def output_path_constants(trees=None):
    """`{(module, constant): (paths named, repo-anchored?)}` over every `tests/test_*.py`.

    The POPULATION of guards that decide whether a test can see a gitignored run. Derived
    from the tree, so a sixth cannot land unenumerated the way the fifth did.
    """
    trees = test_module_trees() if trees is None else trees
    out = {}
    for mod, tree in trees.items():
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            paths = _names_an_output_path(node.value)
            if not paths:
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    out[(mod, target.id)] = (tuple(paths), _is_repo_anchored(node.value))
    return out


def output_gated_names(trees=None):
    """`{(module, name)}` — the path constants AND every module-level name derived from one.

    `HAVE_E02 = os.path.isdir(os.path.join(E02_ROOT, "runs"))` is a guard even though it
    names no string: it is the boolean the `skipif` reads. Resolved to a fixed point so a
    guard two assignments away from the path still counts.
    """
    trees = test_module_trees() if trees is None else trees
    names = {key for key in output_path_constants(trees)}
    grew = True
    while grew:
        grew = False
        for mod, tree in trees.items():
            local = {n for (m, n) in names if m == mod}
            for node in tree.body:
                if not isinstance(node, ast.Assign):
                    continue
                reads = {n.id for n in ast.walk(node.value) if isinstance(n, ast.Name)}
                if not (reads & local):
                    continue
                for target in node.targets:
                    if isinstance(target, ast.Name) and (mod, target.id) not in names:
                        names.add((mod, target.id))
                        grew = True
    return names


def output_gated_tests(trees=None):
    """`{(module, test name, line)}` — every test a gitignored `outputs/` run can skip.

    Both spellings of the guard: a `@pytest.mark.skipif` whose condition reads an output
    guard name, and a `pytest.skip(...)` reached from a helper the test calls. The second
    is why `test_aapose_convention.py`'s three are here at all — they carry no decorator.
    """
    trees = test_module_trees() if trees is None else trees
    guards = output_gated_names(trees)
    out = set()
    for mod, tree in trees.items():
        local = {n for (m, n) in guards if m == mod}
        skipping = set()
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            reads = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
            skips = any(isinstance(c, ast.Call) and called_name(c) == "skip"
                        for c in ast.walk(node))
            if skips and (reads & local):
                skipping.add(node.name)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not node.name.startswith("test_"):
                continue
            gated = False
            for dec in node.decorator_list:
                # THREE spellings of the same decorator, all live in this suite:
                # `@pytest.mark.skipif(not GUARD, ...)`, a module-level
                # `needs_bank = pytest.mark.skipif(...)` applied as a bare `@needs_bank`
                # (`test_build_t2v_payload_a3`, `test_donor_gate`), and no decorator at all
                # — a helper that calls `pytest.skip` (`test_aapose_convention`).
                if isinstance(dec, ast.Name) and (mod, dec.id) in guards:
                    gated = True
                    continue
                if not isinstance(dec, ast.Call) or called_name(dec) != "skipif":
                    continue
                if {n.id for n in ast.walk(dec) if isinstance(n, ast.Name)} & local:
                    gated = True
            reachable = skipping | {"skip"}
            if any(isinstance(c, ast.Call) and called_name(c) in reachable
                   for c in ast.walk(node)):
                if ({n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
                        & (skipping | local)):
                    gated = True
            if gated:
                out.add((mod, node.name, node.lineno))
    return out


# ------------------------------------------- the historical-number-in-a-message node (w16)


#: The phrases this suite uses when an assertion message quotes an EARLIER measurement.
HISTORICAL_PHRASES = ("were measured", "was measured", "was the count", "were the count",
                      "was the number", "were counted")


def messages_quoting_a_number_they_do_not_assert(trees=None):
    """`[(module, line, asserted, quoted)]` — a message naming a ceiling it does not assert.

    WAVE 16, F-9b4d01ef. Two assertions in `test_instrument_write_ordering.py` failed with
    "N sites; 72 were measured" beside `assert sites == 69` — the tests branch's own
    pre-merge numbers, left in the f-strings when the merge re-derived the constants, the
    `==` targets and the comments. A seat landing a move reads the message as the current
    pin, because that is what a failure message is for, and retypes the wrong number into
    the constant.

    Keyed narrowly on purpose: only messages that CLAIM a measurement (the phrases above)
    are read, so a slice bound, an exit code or a date in a message is not an offender.
    """
    trees = test_module_trees() if trees is None else trees
    out = []
    for mod, tree in sorted(trees.items()):
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assert) or node.msg is None:
                continue
            test = node.test
            if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                    and isinstance(test.ops[0], (ast.Eq, ast.LtE, ast.GtE))):
                continue
            wanted = test.comparators[0]
            if not (isinstance(wanted, ast.Constant) and isinstance(wanted.value, int)
                    and not isinstance(wanted.value, bool)):
                continue
            msg = ast.unparse(node.msg)
            if not any(phrase in msg for phrase in HISTORICAL_PHRASES):
                continue
            # A wave number, a finding id and a date are not ceilings. Struck out BEFORE the
            # numbers are read, so the census reports a stale pin and never a citation.
            text = re.sub(r"(?i)wave[-\s]*\d+", " ", msg)
            text = re.sub(r"(?i)F-[0-9a-f]{6,}", " ", text)
            text = re.sub(r"\d{4}-\d{2}-\d{2}", " ", text)
            quoted = {int(tok) for tok in re.findall(r"(?<![\w.])(\d{1,6})(?![\w.])", text)}
            quoted -= {wanted.value}
            quoted = {n for n in quoted if not (1 <= n <= 12 or 2020 <= n <= 2100)}
            if quoted:
                out.append((mod, node.lineno, wanted.value, sorted(quoted)))
    return out
