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
    """`{module name: ast.Module}` for `tools/*.py` (and `tools/armature_core/*.py`)."""
    out = {}
    for path in tool_paths(include_core=include_core):
        with open(path, encoding="utf-8") as fh:
            out[os.path.basename(path)[:-3]] = ast.parse(fh.read())
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
    called = {c.func.id for c in ast.walk(fn)
              if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
              and c.func.id in named}
    if len(called) == 1:
        return named[next(iter(called))]
    return fn


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


def declared_flags(tree, mod, helpers):
    """Everything the CLI body's parser can put on the namespace, helper calls resolved.

    Keyed on `cli_body`, not on the name `main` (F-0e0709b2): the three wave-10 builders
    declare their flags inside `build_and_write(argv)`.
    """
    body = cli_body(tree)
    if body is None:
        return set()
    out = argparse_dests(body)
    for node in tree.body:  # a parser built at module level
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out |= argparse_dests(node)
    vis = visible_functions(tree, mod)
    for node in ast.walk(body):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            name = node.func.id
            if name != body.name and vis.get(name) in helpers:
                out |= helpers[vis[name]]
    return out


def namespace_reads(tree):
    """`{attribute: first line}` read off whatever `parse_args` returned, in the CLI body."""
    body = cli_body(tree)
    if body is None:
        return {}
    ns = set()
    for node in walk_scope(body):
        if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Attribute)
                and node.value.func.attr in ("parse_args", "parse_known_args")):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    ns.add(target.id)
                elif isinstance(target, ast.Tuple):
                    for elt in target.elts:
                        if isinstance(elt, ast.Name):
                            ns.add(elt.id)
                            break
    out = {}
    for node in walk_scope(body):
        if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                and node.value.id in ns):
            out.setdefault(node.attr, node.lineno)
    return out


def undeclared_flags(tree, mod, helpers):
    """`{attribute: line}` the CLI body reads and its own parser never declares."""
    declared = declared_flags(tree, mod, helpers)
    return {k: v for k, v in sorted(namespace_reads(tree).items()) if k not in declared}


def parser_population(trees=None):
    """Every `tools/*.py` whose CLI body reads a `parse_args` namespace."""
    trees = module_trees() if trees is None else trees
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
