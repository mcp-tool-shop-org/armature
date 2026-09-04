"""What a `pip install armature-studio` actually gets, and what a `git add -A` never sends.

Three packaging invariants that no other test covered, each filed after a measurement
rather than a reading:

1. **Every third-party module `armature_core` imports is declared.** `cv2`, `PIL` and
   `matplotlib` are imported inside function bodies, so `import armature_core.aapose`
   succeeds on an install that cannot run `draw_body`. The wheel was built, installed into
   a fresh venv, and `aapose.draw_body(...)` raised `ModuleNotFoundError: No module named
   'cv2'` while `armature check` on the same install printed `all modules resolved` and
   exited 0. A function-local import is still a dependency; only the moment of failure moved.

2. **The ignore list covers the artifact type this repo actually produces.** Every control
   sequence, start frame and comparison sheet here is a PNG (`armature_core.pngio` is the
   writer), and the extension backstop listed mp4/mov/webm/glb/gltf/blend/exr/npy and no
   raster image at all.

3. **The ignore list covers the files that carry a registry token.** This repo publishes to
   npm and to PyPI; the two files a maintainer creates while debugging a publish by hand
   are `.npmrc` and `.pypirc`, and neither was ignored. SECURITY.md asserts that no
   long-lived registry token exists in this repository — .gitignore is the mechanical
   backstop for that assertion, so it is tested rather than asserted.
"""

import ast
import json
import os
import subprocess
import sys
import tomllib

import pytest

from conftest import REPO  # noqa: F401  (puts tools/ on sys.path)

CORE = os.path.join(REPO, "tools", "armature_core")
GIT = os.environ.get("ARMATURE_GIT", "git")


# -- 1. declared dependencies ------------------------------------------------------------

# Which distribution on PyPI provides each third-party root module armature_core imports.
# The table is deliberately explicit and the test is fail-closed: a new third-party import
# with no row here fails with a message naming the module, rather than passing because a
# lookup silently returned nothing. `bpy` has no row because it has no distribution -- it
# is Blender's own interpreter and is never pip-installable; the exception is asserted in
# its own test below so nobody can widen it by editing one set.
PROVIDES = {
    "numpy": "numpy",
    "cv2": "opencv-python-headless",
    "PIL": "pillow",
    "matplotlib": "matplotlib",
}
NOT_ON_PYPI = {"bpy", "mathutils"}


def _root_imports(path):
    """Root module name of every import in a file, at any nesting depth."""
    tree = ast.parse(open(path, encoding="utf-8").read())
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # a relative import -- this package, not a dependency
                continue
            if node.module:
                roots.add(node.module.split(".")[0])
    return roots


def third_party_roots():
    """Every non-stdlib, non-local root module imported anywhere in armature_core."""
    local = {f[:-3] for f in os.listdir(CORE) if f.endswith(".py")} | {"armature_core"}
    found = {}
    for name in sorted(os.listdir(CORE)):
        if not name.endswith(".py"):
            continue
        for root in _root_imports(os.path.join(CORE, name)):
            if root in sys.stdlib_module_names or root in local:
                continue
            found.setdefault(root, []).append(name)
    return found


def declared_requirements():
    """Every distribution named in pyproject's runtime deps and every extra, normalised."""
    with open(os.path.join(REPO, "pyproject.toml"), "rb") as fh:
        cfg = tomllib.load(fh)["project"]
    names = set()
    groups = [cfg.get("dependencies", [])] + list(
        cfg.get("optional-dependencies", {}).values()
    )
    for group in groups:
        for spec in group:
            # strip the version clause / extras / environment marker
            for sep in (";", "[", "<", ">", "=", "!", "~", " "):
                spec = spec.split(sep)[0]
            names.add(spec.strip().lower().replace("_", "-"))
    return names


def test_every_third_party_import_in_armature_core_is_declared():
    declared = declared_requirements()
    undeclared = []
    for root, files in sorted(third_party_roots().items()):
        if root in NOT_ON_PYPI:
            continue
        dist = PROVIDES.get(root)
        if dist is None:
            undeclared.append(f"{root} (imported by {', '.join(files)}) has no PROVIDES row")
        elif dist.lower() not in declared:
            undeclared.append(
                f"{root} (imported by {', '.join(files)}) needs {dist!r} in pyproject"
            )
    assert undeclared == [], "undeclared runtime dependencies: " + "; ".join(undeclared)


def scope_scanner():
    """`armature_core.cli.import_roots_by_scope` — the ONE import scan, resolved here.

    Resolved through a function rather than imported at module scope so this file still
    collects against a tree that does not carry the scanner, and the tests that need it
    fail as tests rather than as a collection error.
    """
    from armature_core import cli

    return cli.import_roots_by_scope


# ------------------------------------------------- one scanner, and its exact complement
#
# Wave 6, F-71538ecf. The function-local import scan was implemented TWICE and the two
# disagreed by construction, with nothing pinning them against each other.
# `armature_core.cli._function_local_dependencies` walks with a FunctionDef DEPTH counter,
# so an import at module scope inside a `try:` or an `if:` stays depth 0 and is correctly
# not function-local. This module detected module scope by iterating `tree.body` alone, so
# the same guarded import was invisible to it and its root was classified lazy. Measured
# with a synthetic module whose only import is `try: import matplotlib / except
# ImportError:` at module scope: the shipped scanner returned [] (correct) and this
# module's detector never saw the import at all, leaving `at_module_scope` False.
#
# The consequence crossed a module boundary: `tests/test_ci_workflows.py` imports
# `lazy_third_party_roots` and requires CI's clean-room leg to CALL a function that imports
# each "lazy" root. For a guarded module-scope dependency there is no such function, so the
# suite would go red for a false reason while `armature check` reported the honest answer.
#
# The second implementation is deleted. `lazy_third_party_roots` now reads the SHIPPED
# scanner, and the only walk left here answers the complementary question — which roots are
# imported at module scope — with the same depth rule, asserted against the shipped scanner
# on every armature_core module and on the two fixture sources that separate them.


def _module_scope_roots_of_tree(tree):
    """Roots imported at module scope, by the same depth rule the shipped scanner uses.

    Depth counts FunctionDef and ClassDef nesting and nothing else, so an import inside a module-level
    `try:` / `if:` / `with:` is module scope — which is exactly what the old `tree.body`
    iteration could not see.
    """
    roots, stack = set(), [(tree, 0)]
    while stack:
        node, depth = stack.pop()
        for child in ast.iter_child_nodes(node):
            d = depth
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                d += 1  # merge fix-up: the shipped scanner counts a class body as nested scope too

            elif d == 0 and isinstance(child, ast.Import):
                roots.update(a.name.split(".")[0] for a in child.names)
            elif (d == 0 and isinstance(child, ast.ImportFrom)
                  and child.level == 0 and child.module):
                roots.add(child.module.split(".")[0])
            stack.append((child, d))
    return roots


def _third_party(roots):
    local = {f[:-3] for f in os.listdir(CORE) if f.endswith(".py")} | {"armature_core"}
    return {r for r in roots if r not in sys.stdlib_module_names and r not in local}


def _core_modules():
    return [n[:-3] for n in sorted(os.listdir(CORE)) if n.endswith(".py")]


def lazy_third_party_roots():
    """The third-party roots imported ONLY inside function bodies.

    These are the ones an import-only check cannot see: the module imports clean and the
    first call raises. `test_ci_workflows` reads this list to require that the clean-room
    leg actually reaches each of them, so a newly added lazy dependency drags its coverage
    along instead of arriving silently.

    ⚠ The scope reading is `armature_core.cli.import_roots_by_scope` — the SAME walk
    `armature check` uses — rather than a second one derived here. This function used to
    classify by whether the root appeared in `tree.body`, which called an import inside a
    class body, a module-level `try:` or a module-level `if:` LAZY while the cli scan
    called it neither lazy nor function-local. Two implementations of "not at module
    scope" that do not agree is the install-health blind spot one scope over.
    """
    lazy = {}
    for root, files in third_party_roots().items():
        if root in NOT_ON_PYPI:
            continue
        at_module_scope = any(
            root in scope_scanner()(
                open(os.path.join(CORE, name), encoding="utf-8").read(),
                filename=name)["module_scope"]
            for name in files)
        if not at_module_scope:
            lazy[root] = files
    return lazy


#: A module-scope import inside a `try:` — the case that separated the two scanners. Kept
#: as source rather than a file under `tools/`: the shipped scanner resolves its path from
#: `cli.__file__`, so pointing that at a temporary directory exercises the real walk.
GUARDED_MODULE_SCOPE_SOURCE = """\
try:
    import matplotlib
except ImportError:  # pragma: no cover
    matplotlib = None


def draw():
    return matplotlib
"""

FUNCTION_LOCAL_SOURCE = """\
def draw():
    import matplotlib
    return matplotlib
"""


def _shipped_scan(tmp_path, monkeypatch, source, name="probe_guarded"):
    """`cli._function_local_dependencies` run over a source of our choosing."""
    from armature_core import cli

    (tmp_path / (name + ".py")).write_text(source, encoding="utf-8")
    monkeypatch.setattr(cli, "__file__", str(tmp_path / "cli.py"))
    cli._FUNC_LOCAL_CACHE.clear()
    try:
        return cli._function_local_dependencies(name)
    finally:
        cli._FUNC_LOCAL_CACHE.clear()


def _body_only_module_scope_roots(tree):
    """The detector this module used to carry, kept only so the fixture below can show
    what it missed."""
    roots = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            roots.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            roots.add(node.module.split(".")[0])
    return roots


def test_a_guarded_module_scope_import_separates_the_two_scanners(tmp_path, monkeypatch):
    """The fixture the finding names, both sources run through both walks.

    A `try: import matplotlib` at module scope is NOT function-local — the shipped scanner
    says so and `armature check` reports it honestly — and the old `tree.body` detector
    could not see it at all, which is what made the same root read as lazy here.
    """
    assert _shipped_scan(tmp_path, monkeypatch, GUARDED_MODULE_SCOPE_SOURCE) == []
    assert _shipped_scan(tmp_path, monkeypatch, FUNCTION_LOCAL_SOURCE) == ["matplotlib"]

    guarded = ast.parse(GUARDED_MODULE_SCOPE_SOURCE)
    local = ast.parse(FUNCTION_LOCAL_SOURCE)
    assert _module_scope_roots_of_tree(guarded) == {"matplotlib"}
    assert _module_scope_roots_of_tree(local) == set()
    assert _body_only_module_scope_roots(guarded) == set(), (
        "the retired detector now sees the guarded import; this fixture no longer "
        "separates the two scanners")


def test_the_two_import_scans_agree_on_every_armature_core_module():
    """The pin the finding asked for: every module, both questions, complementary answers.

    `module scope | function local == every third-party root the file imports`, and the
    two sets are disjoint — no root in this package is imported both ways in one file, so
    the derivation `lazy_third_party_roots` performs is exact on this tree. The day one is,
    this fails rather than the classification quietly drifting.
    """
    from armature_core import cli

    for mod in _core_modules():
        path = os.path.join(CORE, mod + ".py")
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        module_scope = _third_party(_module_scope_roots_of_tree(tree))
        func_local = set(cli._function_local_dependencies(mod))
        every = _third_party(_root_imports(path))
        assert module_scope | func_local == every, (
            f"{mod}: module scope {sorted(module_scope)} plus function-local "
            f"{sorted(func_local)} does not account for {sorted(every)}")
        assert module_scope & func_local == set(), (
            f"{mod} imports {sorted(module_scope & func_local)} both at module scope and "
            f"inside a function; the lazy classification can no longer be derived from "
            f"the two answers alone")


def lazy_import_call_sites():
    """`{root: [function names that import it]}` for the function-local dependencies.

    The clean-room leg has to CALL one of these to reach the import; running `armature
    check` reaches none of them, which is how that leg stayed green on a wheel whose
    drawing path could not run. Derived from the source so a new lazy dependency drags the
    requirement along with it.
    """
    sites = {}
    for root in lazy_third_party_roots():
        for name in sorted(os.listdir(CORE)):
            if not name.endswith(".py"):
                continue
            tree = ast.parse(open(os.path.join(CORE, name), encoding="utf-8").read())
            # ClassDef as well as FunctionDef: `lazy_third_party_roots` reads scope
            # through the one scanner, which counts a class body as not-module-scope, so
            # a class-body import would otherwise be LAZY with no site to name and this
            # function's caller would fail on an absence it could not locate.
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                         ast.ClassDef)):
                    continue
                if root in _root_imports_of_body(node):
                    sites.setdefault(root, []).append(node.name)
    return sites


def _root_imports_of_body(func):
    roots = set()
    for node in ast.walk(func):
        if isinstance(node, ast.Import):
            roots |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            roots.add(node.module.split(".")[0])
    return roots


def test_bpy_is_the_documented_exception():
    """Blender's module is the one import with no distribution, and that is on purpose."""
    roots = third_party_roots()
    assert "bpy" in roots, "blender_scene.py no longer imports bpy -- re-read NOT_ON_PYPI"
    assert "bpy" not in PROVIDES
    assert "bpy" not in declared_requirements()


def test_the_lazily_imported_ones_are_still_lazy():
    """The three that broke are function-local, which is why an import check cannot see them.

    If any of these moves to module scope this test fails, and the reason the packaging
    test above exists changes with it -- so it should be read again, not re-pinned.
    """
    for module, name in (
        ("aapose.py", "cv2"),
        ("aapose.py", "matplotlib"),
        ("donor_gate.py", "PIL"),
    ):
        # The THIRD copy of this walk, routed through the one scanner: it read only
        # `tree.body` too, so it agreed with neither of the other two about a class
        # body or a module-level try block.
        src = open(os.path.join(CORE, module), encoding="utf-8").read()
        module_level = scope_scanner()(src, filename=module)["module_scope"]
        assert name not in module_level, f"{name} became a module-scope import in {module}"


# -- 2 and 3. what the ignore list covers -------------------------------------------------


def _check_ignore(paths):
    """`git check-ignore` verdict per path: the ignoring pattern, or None if not ignored.

    `--no-index` so tracked files answer too — by default the command stays silent about
    anything already in the index, which is exactly the set the committed-figure test asks
    about. `-v` prints the LAST matching line including negations, and a `!` line means the
    path is re-included, so a negation is read as "not ignored" rather than as a match.
    """
    proc = subprocess.run(
        [GIT, "check-ignore", "--no-index", "-v", "--", *paths],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    matched = {}
    for line in proc.stdout.splitlines():
        # <source>:<line>:<pattern>\t<pathname>
        rule, _, path = line.rpartition("\t")
        pattern = rule.split(":", 2)[-1]
        matched[path.replace("\\", "/")] = None if pattern.startswith("!") else rule
    return {p: matched.get(p) for p in paths}


def _git_present():
    try:
        return subprocess.run([GIT, "--version"], capture_output=True).returncode == 0
    except OSError:
        return False


requires_git = pytest.mark.skipif(
    not _git_present(),
    reason="git is not on PATH; the ignore list can only be read through it",
)

CREDENTIAL_SHAPED = [
    ".npmrc",
    "npm/.npmrc",
    ".pypirc",
    ".env",
    ".env.local",
    ".env.production",
    "secrets.pem",
    "client.p12",
    "cert.pfx",
    "deploy.key",
    "credentials.json",
]

RENDER_SHAPED = [
    "sheets/control_0001.png",
    "renders/frame.png",
    "tools/out/plate.jpg",
    "probe.jpeg",
    "strip.webp",
    "scan.tif",
    "armature-studio-0.3.0.tgz",
    "clip.mp4",
    "figure.glb",
]

# Raster images that ARE committed, deliberately. The extension rules must not swallow
# these, and a negation aimed at a directory the tree does not have is not a negation.
COMMITTED_IMAGES = [
    "docs/assets/logo-wide.png",
    "docs/assets/mark-figure.png",
    "docs/assets/E02-identity-sheet.png",
    "site/public/logo-wide.png",
    "site/public/favicon-32.png",
]


@requires_git
def test_every_credential_shaped_name_is_ignored():
    verdicts = _check_ignore(CREDENTIAL_SHAPED)
    missing = [p for p, pattern in verdicts.items() if not pattern]
    assert missing == [], f"a token could ride a `git add -A` in: {missing}"


@requires_git
def test_every_render_shaped_name_is_ignored():
    verdicts = _check_ignore(RENDER_SHAPED)
    missing = [p for p, pattern in verdicts.items() if not pattern]
    assert missing == [], f"generated artifacts outside the extension backstop: {missing}"


@requires_git
def test_the_committed_figures_are_not_ignored():
    verdicts = _check_ignore(COMMITTED_IMAGES)
    swallowed = {p: pat for p, pat in verdicts.items() if pat}
    assert swallowed == {}, f"the extension rules swallowed committed figures: {swallowed}"


@requires_git
def test_every_negation_points_at_a_path_that_exists():
    """A `!` line aimed at a directory the tree does not have re-includes nothing."""
    dead = []
    with open(os.path.join(REPO, ".gitignore"), encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line.startswith("!"):
                continue
            head = line[1:].split("/**")[0].split("/*")[0].rstrip("/")
            if not os.path.exists(os.path.join(REPO, head)):
                dead.append(line)
    assert dead == [], f"negations pointing at nothing: {dead}"


# -- 4. one import scan, not two that disagree (F-3a6dd108) -----------------------------

CLASS_BODY = "class Thing:\n    import cv2\n"
FUNC_BODY = "def f():\n    import cv2\n"
NESTED_FUNC = "def f():\n    def g():\n        from cv2 import imread\n"
MODULE_SCOPE = "import cv2\n"
MODULE_TRY = "try:\n    import cv2\nexcept ImportError:\n    cv2 = None\n"
METHOD_BODY = "class Thing:\n    def m(self):\n        import cv2\n"
BOTH = "import cv2\n\n\ndef f():\n    import cv2\n"


@pytest.mark.parametrize("src,at_module_scope,nested", [
    (MODULE_SCOPE, True, False),
    (MODULE_TRY, True, False),
    (FUNC_BODY, False, True),
    (NESTED_FUNC, False, True),
    (METHOD_BODY, False, True),
    (CLASS_BODY, False, True),
    (BOTH, True, True),
])
def test_one_scanner_answers_the_scope_question_for_both_callers(src, at_module_scope,
                                                                 nested):
    """The measured divergence: `cli._function_local_dependencies` incremented its depth
    counter only on FunctionDef, so a CLASS-BODY import sat at depth 0 and was never
    collected, while this file classified laziness by presence in `tree.body`, so the
    same import was classified LAZY and `lazy_import_call_sites` then found no site for
    it. Both callers now read one function."""
    got = scope_scanner()(src)
    assert ("cv2" in got["module_scope"]) is at_module_scope
    assert ("cv2" in got["not_module_scope"]) is nested


def test_the_packaging_scan_and_the_cli_scan_are_literally_the_same_function():
    """The de-duplication itself, asserted rather than described: this module reads scope
    through `armature_core.cli`'s scanner and derives no walk of its own."""
    from armature_core import cli

    import inspect

    assert scope_scanner() is cli.import_roots_by_scope
    # and this module derives no walk of its own: every scope decision here goes
    # through `scope_scanner()`, so there is no second implementation to drift.
    import textwrap

    for fn in (lazy_third_party_roots, lazy_import_call_sites,
               test_the_lazily_imported_ones_are_still_lazy):
        node = ast.parse(textwrap.dedent(inspect.getsource(fn))).body[0]
        if (node.body and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)):
            node.body = node.body[1:]          # the docstring may DESCRIBE the walk
        assert "tree.body" not in ast.unparse(node), fn.__name__


def test_the_two_readings_agree_on_every_module_in_the_package():
    """The census over the real tree, in both directions."""
    from armature_core import cli

    for name in sorted(os.listdir(CORE)):
        if not name.endswith(".py") or name.startswith("__"):
            continue
        src = open(os.path.join(CORE, name), encoding="utf-8").read()
        scope = scope_scanner()(src, filename=name)
        reported = set(cli._function_local_dependencies(name[:-3]))
        # everything the cli reports is a root the scanner calls not-module-scope
        assert reported <= scope["not_module_scope"], (name, reported)
        # and every third-party not-module-scope root is reported by the cli
        third_party = {r for r in scope["not_module_scope"]
                       if r not in sys.stdlib_module_names
                       and r not in {f[:-3] for f in os.listdir(CORE) if f.endswith(".py")}
                       and r != "armature_core"}
        assert third_party <= reported, (name, third_party - reported)


def test_todays_tree_still_reads_the_way_the_measurement_recorded_it():
    """gates -> numpy; donor_gate -> PIL, numpy; aapose -> cv2, matplotlib."""
    from armature_core import cli

    assert cli._function_local_dependencies("gates") == ["numpy"]
    assert cli._function_local_dependencies("donor_gate") == ["PIL", "numpy"]
    assert cli._function_local_dependencies("aapose") == ["cv2", "matplotlib"]
    assert set(lazy_third_party_roots()) == {"cv2", "matplotlib", "PIL"}

# ------------------------------------------- the stub that outlived the fixture that set it
#
# Wave 6, routed from core-solvers and measured here. `conftest.rt` stubs `bpy` and
# `mathutils`, imports `render_turnaround.py` — which imports `armature_core.blender_scene`,
# which imports `bpy` — and on teardown restored only the two stub entries. The
# blender_scene module stayed in `sys.modules`, importable for the rest of the session on a
# machine with no Blender, so `tests/test_cli.py`'s three `needs-blender` readings turned
# `ok` for a reason that has nothing to do with the install.
#
# Measured before the fix: `pytest tests/test_turnaround_ortho.py tests/test_cli.py` -> 3
# failed; `pytest tests/test_cli.py` alone -> 0. A full run collects alphabetically, so
# `test_cli.py` ran first and the suite reported green on an order-dependent pass — the
# same class as the two import scans above, one directory over.
#
# This is checked in a subprocess because the leak is a property of a session's teardown and
# cannot be observed from inside the module whose fixture is doing the leaking.

ORDER_DEPENDENT_PAIRS = [
    ("test_turnaround_ortho.py", "test_cli.py"),
    ("test_turnaround_pin.py", "test_cli.py"),
    # blender_stub.blender_stubbed() — the second installer, found by the wave-6 serial verify:
    # rig_retopo/rig_bake imported armature_core.blender_scene under the stub and left it cached,
    # so test_run_export's NotInsideBlender path read Blender as importable. Measured red before
    # the teardown fix: 1 failed, 45 passed on this pair alone.
    ("test_retopo_and_bake.py", "test_run_export.py"),
    # test_blender_scene_pure.BS — the third installer, same attribute gap; measured red on
    # this pair before its teardown carried the rule (1 failed, 29 passed).
    ("test_blender_scene_pure.py", "test_run_export.py"),
]


@pytest.mark.parametrize("first,second", ORDER_DEPENDENT_PAIRS,
                         ids=lambda v: v.replace(".py", ""))
def test_a_stub_using_module_does_not_change_what_the_next_one_can_import(first, second,
                                                                          tmp_path):
    """The order the suite does NOT run in, run on purpose.

    What this looks like if the teardown is wrong: `armature check` reports `ok` for a
    module whose import needs Blender, because a fixture two files ago faked it.
    """
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        p for p in (env.get("PYTHONPATH", ""), CORE, REPO) if p)
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
         "--basetemp", str(tmp_path / "bt"),
         os.path.join(tests_dir, first), os.path.join(tests_dir, second)],
        cwd=REPO, env=env, capture_output=True, text=True)
    assert proc.returncode == 0, (
        f"{first} before {second} is not the same suite as {second} alone; a fixture in "
        f"{first} left a module in sys.modules that {second} then read as importable:\n"
        + proc.stdout[-3000:] + proc.stderr[-2000:])


TESTS_DIR = os.path.dirname(os.path.abspath(__file__))


def _writes_into_sys_modules(fn):
    """Every line at which `fn` puts something INTO `sys.modules`.

    Four shapes, because a census that reads one of them polices one of them:
    `sys.modules[name] = stub`, `sys.modules.update(...)`, `sys.modules.setdefault(...)`
    and `monkeypatch.setitem(sys.modules, ...)`. Removals (`pop`, `del`,
    `monkeypatch.delitem`) are not installs and are deliberately not counted — pytest
    undoes its own `delitem`, and `tests/test_cli.py` relies on that.
    """
    hits = []
    for node in ast.walk(fn):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (isinstance(target, ast.Subscript)
                        and isinstance(target.value, ast.Attribute)
                        and target.value.attr == "modules"):
                    hits.append(node.lineno)
        elif isinstance(node, ast.Call):
            func = node.func
            if not isinstance(func, ast.Attribute):
                continue
            if (func.attr in ("update", "setdefault")
                    and isinstance(func.value, ast.Attribute)
                    and func.value.attr == "modules"):
                hits.append(node.lineno)
            if (func.attr == "setitem" and node.args
                    and isinstance(node.args[0], ast.Attribute)
                    and node.args[0].attr == "modules"):
                hits.append(node.lineno)
    return sorted(hits)


def sys_modules_writers(tests_dir=None):
    """THE DERIVATION: `(filename, function)` for every stub installer under `tests/`.

    Walked out of every `.py` in the suite, helpers and test modules alike — the wave-6
    version iterated a hard-coded `expected` dict of three filenames, so a fourth writer
    in a NEW file was never opened. Measured in a scratch copy of `tests/` on 2026-09-04:
    adding a fourth file containing a real installer that wrote `sys.modules['bpy']`,
    imported `armature_core.blender_scene` and never cleared it left the census GREEN.
    """
    tests_dir = TESTS_DIR if tests_dir is None else tests_dir
    out = []
    for name in sorted(os.listdir(tests_dir)):
        if not name.endswith(".py"):
            continue
        with open(os.path.join(tests_dir, name), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        for fn in ast.walk(tree):
            if (isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and _writes_into_sys_modules(fn)):
                out.append((name, fn.name))
    return sorted(set(out))


#: Derived 2026-09-04. Equality, so a fourth installer fails HERE, in the census, rather
#: than silently in whatever order the next session happens to run the suite in.
RECORDED_STUB_INSTALLERS = [
    ("blender_stub.py", "blender_stubbed"),
    ("conftest.py", "rt"),
    ("test_blender_scene_pure.py", "BS"),
]

#: A new installer needs a line here saying how to DRIVE it, because the teardown is only
#: observable by running it. Every one of the three is a generator — two pytest fixtures
#: and one `contextlib.contextmanager` — so `__wrapped__` reaches the raw function and
#: `next()` twice runs setup then teardown.
INSTALLER_MODULE = {
    ("blender_stub.py", "blender_stubbed"): "blender_stub",
    ("conftest.py", "rt"): "conftest",
    ("test_blender_scene_pure.py", "BS"): "test_blender_scene_pure",
}

_DRIVE_ONE = """
import importlib, json, os, sys
sys.path.insert(0, {tests!r})
sys.path.insert(0, os.path.join(os.path.dirname({tests!r}), "tools"))
mod = importlib.import_module({module!r})
fn = getattr(mod, {func!r})
raw = getattr(fn, "__wrapped__", fn)
before = set(sys.modules)
gen = raw()
next(gen)
try:
    next(gen)
except StopIteration:
    pass
after = set(sys.modules)
new = sorted(after - before)
tools = os.path.join(os.path.dirname({tests!r}), "tools")


def _from_this_repo(name):
    path = getattr(sys.modules.get(name), "__file__", None) or ""
    return path.startswith(tools)


# Stdlib a stub happened to pull in (`hashlib`, `_blake2`) is not the invariant: it does
# not depend on Blender and nothing reads it as evidence that Blender is present. What
# may not survive is anything from THIS repo's tree, or a Blender name itself.
relevant = [n for n in new
            if n.split(".")[0] in ("bpy", "mathutils", "bmesh") or _from_this_repo(n)]
print("ALL " + json.dumps(new))
print("LEAKED " + json.dumps(relevant))
"""


def test_the_stub_installer_population_is_derived_and_has_not_grown_silently():
    """Size and membership before the property (wave 8, F-391c9d0f). The old census could
    not open a file it had not been told about, and both of its per-installer checks were
    substring searches over the function's source: `'- before' in body` and
    `'armature_core' in body`, each satisfiable by a comment. Measured in a scratch copy:
    replacing `conftest.rt`'s entire teardown with a stub whose docstring contained the
    words `- before` and `armature_core` left the census GREEN."""
    writers = sys_modules_writers()
    assert writers == RECORDED_STUB_INSTALLERS, {
        "appeared": sorted(set(writers) - set(RECORDED_STUB_INSTALLERS)),
        "vanished": sorted(set(RECORDED_STUB_INSTALLERS) - set(writers)),
    }
    assert sorted(INSTALLER_MODULE) == sorted(writers), (
        "a stub installer has no line in INSTALLER_MODULE saying how to drive it, so its "
        "teardown is asserted by nothing that runs")


@pytest.mark.parametrize("filename,func", RECORDED_STUB_INSTALLERS,
                         ids=lambda v: v.replace(".py", ""))
def test_every_stub_installing_fixture_restores_what_it_imported(filename, func, tmp_path):
    """BEHAVIOURAL, not textual. The installer is driven in a subprocess — setup, then
    teardown — and `sys.modules` is compared across it. What this looks like if the
    teardown is wrong: a module imported under a fake `bpy` stays importable for the rest
    of the session, and `tests/test_cli.py` reads `needs-blender` as `ok`.

    A subprocess because the leak is a property of the teardown and cannot be observed
    from inside the session doing the leaking — and because observing it in THIS process
    would leave the very cache the test exists to forbid.
    """
    script = _DRIVE_ONE.format(tests=TESTS_DIR, module=INSTALLER_MODULE[(filename, func)],
                               func=func)
    path = tmp_path / "drive.py"
    path.write_text(script, encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        p for p in (env.get("PYTHONPATH", ""), CORE, REPO) if p)
    proc = subprocess.run([sys.executable, str(path)], cwd=REPO, env=env,
                          capture_output=True, text=True)
    assert proc.returncode == 0, (
        f"{filename}:{func} could not be driven:\n{proc.stdout}\n{proc.stderr}")
    line = [l for l in proc.stdout.splitlines() if l.startswith("LEAKED ")]
    assert line, f"the driver printed nothing:\n{proc.stdout}\n{proc.stderr}"
    leaked = json.loads(line[-1][len("LEAKED "):])
    assert leaked == [], (
        f"{filename}:{func} installs a stub and leaves {leaked} in sys.modules after its "
        f"teardown; restoring the stub entries alone leaves everything imported under "
        f"them importable, on a machine that has no Blender")


def test_the_behavioural_check_can_see_a_teardown_that_does_nothing(tmp_path):
    """Rule 3: prove the census fails on a member without the property. A synthetic tests
    directory with one installer whose teardown restores the stub entry and nothing else —
    which is exactly the shape all three of the real ones had before wave 6."""
    fake = tmp_path / "tests"
    fake.mkdir()
    (fake / "leaky_stub.py").write_text(
        "import sys, types\n"
        "def leaky():\n"
        "    saved = sys.modules.get('bpy')\n"
        "    sys.modules['bpy'] = types.ModuleType('bpy')\n"
        "    sys.modules['bmesh'] = types.ModuleType('bmesh')\n"
        "    try:\n"
        "        yield\n"
        "    finally:\n"
        "        if saved is None:\n"
        "            del sys.modules['bpy']\n"
        "        else:\n"
        "            sys.modules['bpy'] = saved\n", encoding="utf-8")

    #: the derivation sees it
    assert sys_modules_writers(str(fake)) == [("leaky_stub.py", "leaky")]

    #: and driving it names what it left behind
    script = _DRIVE_ONE.format(tests=str(fake), module="leaky_stub", func="leaky")
    path = tmp_path / "drive.py"
    path.write_text(script, encoding="utf-8")
    proc = subprocess.run([sys.executable, str(path)], cwd=str(tmp_path),
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    leaked = json.loads(
        [l for l in proc.stdout.splitlines() if l.startswith("LEAKED ")][-1][len("LEAKED "):])
    assert leaked == ["bmesh"], (leaked, proc.stdout)


def test_every_derived_installer_is_driven_by_a_pair_that_runs_it_before_a_reader():
    """The third half of F-391c9d0f: the derived population and `ORDER_DEPENDENT_PAIRS`
    must be the same family. An installer with a teardown and no pair is a teardown whose
    ORDERING nothing exercises — and the ordering is what the defect was made of."""
    firsts = {first for first, _second in ORDER_DEPENDENT_PAIRS}
    for filename, func in sys_modules_writers():
        if filename.startswith("test_"):
            consumers = {filename}
        else:
            consumers = set()
            for name in sorted(os.listdir(TESTS_DIR)):
                if not (name.startswith("test_") and name.endswith(".py")):
                    continue
                with open(os.path.join(TESTS_DIR, name), encoding="utf-8") as fh:
                    tree = ast.parse(fh.read())
                used = any(
                    (isinstance(n, ast.Name) and n.id == func)
                    or (isinstance(n, ast.Attribute) and n.attr == func)
                    or (isinstance(n, ast.arg) and n.arg == func)
                    for n in ast.walk(tree))
                if used:
                    consumers.add(name)
        assert consumers & firsts, (
            f"{filename}:{func} installs stub modules and no pair in "
            f"ORDER_DEPENDENT_PAIRS runs one of its users ({sorted(consumers)}) before a "
            f"module that reads what it made importable")




# -- 4. the exit convention on the CPU-side spend and fetch tools (wave 8, F-3f642bd9) ----
#
# The nine builders and the two fetchers disagreed THREE ways on how a refusal leaves the
# process. Measured 2026-09-04 by running each as a subprocess:
#
#   * `build_payload.py --experiment=E02 --arm=A1a --out=<fresh>` on a Gate CANON refusal
#     exited 1 with a raw traceback and no HALT sentinel;
#   * `build_t2v_payload.py --out=<fresh>` on the SAME GateCanon exited 2 with
#     BUILD_T2V_HALT;
#   * `gate_saved_graph.py` on a plain `FileNotFoundError` — not a gate at all — exited 2
#     with SAVED_ADMISSION_HALT;
#   * `fetch_run.py` on a missing dump exited 1 with a traceback.
#
# Eight of the eleven carried no handler at all. Argparse's own usage errors also exit 2
# (measured on `build_r2v_payload.py` and `build_animate_payload.py`), which is why the
# convention is "2 vs 1 AND the sentinel", and why a caller keys on the sentinel: `verify.ps1`
# tests `-ne 0` only, so nothing on the rig reads the distinction today and a wrapper that
# started to would read a build_payload refusal as a crash.


def _spend_and_fetch_tools():
    """The population, WALKED rather than typed.

    Every `tools/build_*payload*.py`, `tools/canon_gate.py`, `tools/fetch_*.py` and
    `tools/gate_saved_graph.py` — the CPU-side tools that either author a submission, gate
    one, or retrieve its output. A typed list is what let this family drift into three
    conventions; a member added tomorrow joins the census the day it lands.
    """
    tools = os.path.join(REPO, "tools")
    return sorted(
        n for n in os.listdir(tools)
        if n.endswith(".py")
        and ((n.startswith("build_") and "payload" in n)
             or n.startswith("fetch_")
             or n in ("canon_gate.py", "gate_saved_graph.py")))


def _exit_convention(path):
    """`(has_main_block, prints_halt_sentinel, discriminates_2_vs_1)` for one file."""
    src = open(path, encoding="utf-8").read()
    block = None
    for node in ast.parse(src).body:
        if (isinstance(node, ast.If) and isinstance(node.test, ast.Compare)
                and isinstance(node.test.left, ast.Name)
                and node.test.left.id == "__name__"):
            block = node
    if block is None:
        return (False, False, False)
    sentinel = discriminates = False
    for node in ast.walk(block):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "print"):
            for lit in ast.walk(node):
                if isinstance(lit, ast.Constant) and isinstance(lit.value, str) \
                        and lit.value.strip().endswith("_HALT"):
                    sentinel = True
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "exit" and node.args
                and isinstance(node.args[0], ast.IfExp)):
            discriminates = True
    return (True, sentinel, discriminates)


SPEND_AND_FETCH = _spend_and_fetch_tools()


def test_the_spend_and_fetch_population_is_the_one_this_census_claims():
    """Size AND membership, so a new member fails loudly rather than being skipped."""
    assert SPEND_AND_FETCH == [
        "build_animate_payload.py", "build_assembly_payload.py",
        "build_camera_i2v_payload.py", "build_cascade_payload.py",
        "build_i2v_payload.py", "build_lora_arm_payload.py", "build_payload.py",
        "build_r2v_payload.py", "build_t2v_payload.py", "canon_gate.py",
        "fetch_run.py", "fetch_t2v_run.py", "gate_saved_graph.py"], SPEND_AND_FETCH
    assert len(SPEND_AND_FETCH) == 13


@pytest.mark.parametrize("filename", SPEND_AND_FETCH)
def test_every_spend_and_fetch_tool_carries_the_exit_convention(filename):
    has_main, sentinel, discriminates = _exit_convention(
        os.path.join(REPO, "tools", filename))
    assert has_main, f"{filename} has no `__main__` block at all"
    assert sentinel, f"{filename} prints no <TOOL>_HALT line; its halt is a traceback"
    assert discriminates, (
        f"{filename} does not discriminate a gate refusal (2) from a crash (1); an "
        f"unconditional exit code makes a programming error indistinguishable from an andon")


def test_the_census_goes_RED_on_a_member_without_the_convention(tmp_path, monkeypatch):
    """A census that cannot fail is the defect class this wave exists to close. A module is
    added to the walked tree WITHOUT the handler and the property check must refuse it."""
    fake = tmp_path / "build_nothing_payload.py"
    fake.write_text('if __name__ == "__main__":\n    main()\n', encoding="utf-8")
    assert _exit_convention(str(fake)) == (True, False, False)

    # …and one that exits 2 unconditionally — the SECOND of the three conventions — is
    # refused for the reason it was filed: a crash reads as a gate refusal.
    blunt = tmp_path / "build_blunt_payload.py"
    blunt.write_text(
        'if __name__ == "__main__":\n'
        '    try:\n'
        '        raise SystemExit(main())\n'
        '    except BaseException as exc:\n'
        '        print("BUILD_BLUNT_HALT " + json.dumps({}))\n'
        '        sys.exit(2)\n', encoding="utf-8")
    has_main, sentinel, discriminates = _exit_convention(str(blunt))
    assert (has_main, sentinel) == (True, True)
    assert discriminates is False

    # And the walk itself sees a new member rather than a typed list of the old ones.
    real_listdir = os.listdir
    tools_dir = os.path.join(REPO, "tools")

    def listdir(path):
        names = real_listdir(path)
        return names + ["build_nothing_payload.py"] if path == tools_dir else names

    monkeypatch.setattr(os, "listdir", listdir)
    grown = _spend_and_fetch_tools()
    assert "build_nothing_payload.py" in grown
    assert len(grown) == len(SPEND_AND_FETCH) + 1


def test_a_gate_refusal_exits_2_with_its_sentinel_and_a_crash_exits_1(tmp_path):
    """The convention, behaviourally, on the two tools the finding measured: a Gate CANON
    refusal out of `build_payload` (which exited 1 with a raw traceback) and a missing dump
    out of `fetch_run` (which did the same). Both leave a machine-readable line now."""
    env = dict(os.environ, PYTHONPATH=os.path.join(REPO, "tools"))

    refusal = subprocess.run(
        [sys.executable, os.path.join(REPO, "tools", "build_payload.py"),
         "--experiment=E03", "--arm=B2", f"--out={tmp_path / 'fresh' / 'B2.json'}"],
        capture_output=True, text=True, env=env, cwd=REPO)
    assert refusal.returncode == 2, refusal.stdout + refusal.stderr
    assert "BUILD_PAYLOAD_HALT" in refusal.stdout
    assert "GateCanon" in refusal.stdout
    assert not (tmp_path / "fresh").exists()

    crash = subprocess.run(
        [sys.executable, os.path.join(REPO, "tools", "fetch_run.py"),
         f"--dump={tmp_path / 'nothing.json'}", "--run=r", f"--root={tmp_path / 'runs'}"],
        capture_output=True, text=True, env=env, cwd=REPO)
    assert crash.returncode == 1, crash.stdout + crash.stderr
    assert "FETCH_RUN_HALT" in crash.stdout
    assert "FileNotFoundError" in crash.stdout


# -- 3b. the two ignore populations, DERIVED from the tree (F-0162b2ce) -------------------
#
# Both lists above are typed. A typed list is a population that stops growing the day
# someone forgets it, and the measured defect here was exactly that shape: the ignore rule
# read `site/node_modules/`, written for the one npm tree that existed when it was written,
# while `npm/package.json` has carried its own `scripts.test` since v0.2.0 — run by ci.yml,
# by release.yml and by verify.ps1 — so an `npm install` there is an ordinary local act
# whose output was untracked AND unignored. Measured from this worktree before the fix:
# `site/node_modules/x.js` IGNORED (.gitignore:53), `npm/node_modules/x.js` NOT IGNORED,
# `node_modules/x.js` NOT IGNORED.
#
# So both populations below are read out of the tree instead: where npm can install, and
# which registries this repository actually publishes to.


def npm_install_roots():
    """Every directory an `npm install` can leave a `node_modules/` in, walked from the tree.

    The package manifests are enumerated (`package.json`, skipping vendored trees), plus the
    repository root — `npm install <pkg>` in a directory with no manifest at all still
    creates `node_modules/` there, and the root is where a maintainer types it by mistake.
    """
    skip = {".git", "node_modules", ".venv", ".swarm", "dist", "outputs", "__pycache__",
            ".astro", ".pytest_cache", ".ruff_cache"}
    roots = {""}
    for dirpath, dirnames, filenames in os.walk(REPO):
        dirnames[:] = [d for d in dirnames if d not in skip]
        if "package.json" in filenames:
            rel = os.path.relpath(dirpath, REPO).replace("\\", "/")
            roots.add("" if rel == "." else rel)
    return sorted(roots)


#: Measured 2026-09-04 by the walk above. A third npm tree fails this before it fails the
#: ignore check, so the reader learns the population changed rather than the rule.
NPM_ROOTS_TODAY = ["", "npm", "site"]


def test_the_npm_root_census_is_the_manifests_in_the_tree():
    assert npm_install_roots() == NPM_ROOTS_TODAY, (
        f"npm can install into {npm_install_roots()}; this file was written against "
        f"{NPM_ROOTS_TODAY}")


@requires_git
@pytest.mark.parametrize("root", NPM_ROOTS_TODAY, ids=lambda r: r or "<repo root>")
def test_a_dependency_tree_is_ignored_wherever_npm_can_create_one(root):
    """A `git add -A` after a local install must not commit a dependency tree."""
    path = (root + "/" if root else "") + "node_modules/left-pad/index.js"
    verdict = _check_ignore([path])[path]
    assert verdict, (
        f"{path} is not ignored; `npm install` in {root or 'the repository root'} leaves a "
        "dependency tree a `git add -A` would commit")


#: The credential file each registry's own client reads, with the document that says so.
#: The mapping is knowledge; WHICH rows apply is derived from release.yml below, and a
#: registry with no row here fails rather than passing on an empty lookup.
#:   npm  — https://docs.npmjs.com/cli/v11/configuring-npm/npmrc  (.npmrc)
#:   pip/twine — https://packaging.python.org/specifications/pypirc/  (.pypirc)
#:   both — .netrc, read by npm (`npm config` follows curl/netrc conventions for registry
#:   auth) and by pip/twine through requests' trust_env; it is the third file a maintainer
#:   debugging a publish by hand creates, and it was not on the list.
REGISTRY_CARRIERS = {
    "pypi": (".pypirc", ".netrc"),
    "npm": (".npmrc", ".netrc"),
}

#: How each registry is recognised in the workflow that publishes to it.
REGISTRY_MARKERS = {
    "pypi": "gh-action-pypi-publish",
    "npm": "npm publish",
}


def registries_published_to():
    """Which registries `.github/workflows/` actually reaches, read out of the files."""
    workflows = os.path.join(REPO, ".github", "workflows")
    text = ""
    for name in sorted(os.listdir(workflows)):
        if name.endswith((".yml", ".yaml")):
            with open(os.path.join(workflows, name), encoding="utf-8") as fh:
                text += fh.read()
    return sorted(r for r, marker in REGISTRY_MARKERS.items() if marker in text)


def test_every_registry_this_repo_publishes_to_has_a_credential_row():
    """Fail-closed: a third registry arrives with no carrier list rather than silently none."""
    found = registries_published_to()
    assert found, (
        "no publish step is recognised in .github/workflows/ any more; this check and the "
        "one below have no subject and must be retired deliberately, not left green")
    assert set(found) <= set(REGISTRY_CARRIERS), (
        f"{sorted(set(found) - set(REGISTRY_CARRIERS))} is published to and has no row in "
        "REGISTRY_CARRIERS, so its credential file is covered by nothing here")


@requires_git
def test_the_credential_file_of_every_registry_this_repo_publishes_to_is_ignored():
    """SECURITY.md asserts no long-lived registry token exists here; this is the backstop.

    Derived, not typed: the carriers checked are the ones belonging to the registries the
    workflows reach, so adding a third registry brings its credential file with it.
    """
    carriers = sorted({c for r in registries_published_to() for c in REGISTRY_CARRIERS[r]})
    verdicts = _check_ignore(carriers)
    missing = [p for p, pattern in verdicts.items() if not pattern]
    assert missing == [], (
        f"a registry credential could ride a `git add -A` in: {missing}; the registries "
        f"published to are {registries_published_to()}")


# ------------------------------------------------ what the sdist carries (wave 8, F-4c607d79)
#
# Coordinator fix-up at the wave-8 merge: no frozen domain owned MANIFEST.in, so ci-packaging
# recorded the measurement in pyproject.toml and the file landed here with this test. The
# decision the file makes: the sdist ships NO tests and no experiment records — the suite runs
# from the repo, where its fixtures and the rig's assets exist. What this looks like if the
# code were wrong in the specific way this check exists to catch: the default `tests/test*.py`
# glob puts 112 test files into the archive with none of what they import, and the unpacked
# archive reads as self-verifying and cannot collect.


def _build_sdist(tmp_path):
    """Build the sdist from the repo into tmp_path and return the unpacked root."""
    import tarfile

    out = tmp_path / "dist"
    proc = subprocess.run(
        [sys.executable, "-m", "build", "--sdist", "--outdir", str(out), REPO],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=REPO,
    )
    if proc.returncode != 0:
        pytest.skip(f"python -m build is not available or failed here:\n{proc.stderr[-1500:]}")
    archives = sorted(out.glob("*.tar.gz"))
    assert len(archives) == 1, [a.name for a in archives]
    with tarfile.open(archives[0]) as tf:
        names = tf.getnames()
        tf.extractall(tmp_path / "unpacked", filter="data")
    root = next((tmp_path / "unpacked").iterdir())
    return root, names


def test_the_sdist_ships_no_tests_and_says_so_in_manifest(tmp_path):
    """The choice MANIFEST.in makes is asserted on the artifact, not on the file's text."""
    manifest = os.path.join(REPO, "MANIFEST.in")
    assert os.path.exists(manifest), "MANIFEST.in is the only mechanism that overrides the default tests/test*.py glob"
    root, names = _build_sdist(tmp_path)
    shipped_tests = [n for n in names if "/tests/" in n or n.endswith("/tests")]
    assert shipped_tests == [], (
        "the sdist carries test files it cannot collect (they import tools/*.py and fixtures "
        f"the archive does not ship): {shipped_tests[:8]}")
    for sub in ("specs", "docs", "site", "npm", "outputs"):
        assert not (root / sub).exists(), f"{sub}/ is not part of the distribution"
    # Measured at the merge: with `package-dir = {"" = "tools"}` setuptools GENERATES the
    # sdist's own `tools/armature_studio.egg-info/SOURCES.txt` during the build, so an
    # egg-info under tools/ is the archive's metadata, not a stale copy. The
    # `recursive-exclude` line in MANIFEST.in guards a leftover LOCAL build tree only; the
    # generated one is re-added by setuptools itself and is not asserted against here.


def test_the_sdist_still_carries_the_package_the_wheel_installs(tmp_path):
    """The other direction: pruning must not cut into the package itself."""
    root, names = _build_sdist(tmp_path)
    core = root / "tools" / "armature_core"
    assert core.is_dir(), "tools/armature_core is the package"
    shipped = {p.name for p in core.glob("*.py")}
    on_disk = {p for p in os.listdir(CORE) if p.endswith(".py")}
    assert shipped == on_disk, (f"modules on disk but not in the sdist: {sorted(on_disk - shipped)}; "
                               f"in the sdist but not on disk: {sorted(shipped - on_disk)}")
    for doc in ("pyproject.toml", "README.pypi.md", "LICENSE"):
        assert (root / doc).exists(), f"{doc} is named by pyproject and must ship"
