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
import os
import subprocess
import sys
import tomllib

import pytest

from conftest import REPO

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

    Depth counts FunctionDef nesting and nothing else, so an import inside a module-level
    `try:` / `if:` / `with:` is module scope — which is exactly what the old `tree.body`
    iteration could not see.
    """
    roots, stack = set(), [(tree, 0)]
    while stack:
        node, depth = stack.pop()
        for child in ast.iter_child_nodes(node):
            d = depth
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                d += 1
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

    The function-local half is the shipped scanner's answer, not a copy of it, so what the
    suite measures is what `armature check` reports.
    """
    from armature_core import cli

    module_scope, func_local = set(), {}
    for mod in _core_modules():
        with open(os.path.join(CORE, mod + ".py"), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        module_scope |= _third_party(_module_scope_roots_of_tree(tree))
        for root in cli._function_local_dependencies(mod):
            if root in NOT_ON_PYPI:
                continue
            func_local.setdefault(root, []).append(mod + ".py")
    return {root: files for root, files in func_local.items() if root not in module_scope}


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
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
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
        tree = ast.parse(open(os.path.join(CORE, module), encoding="utf-8").read())
        module_level = set()
        for node in tree.body:
            if isinstance(node, ast.Import):
                module_level |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                module_level.add(node.module.split(".")[0])
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


def test_every_stub_installing_fixture_restores_what_it_imported():
    """The family, asserted rather than left to the two pairs above.

    `conftest.rt` is the only fixture in this suite that writes into `sys.modules`
    (`tests/test_cli.py` does it too, through `monkeypatch.delitem`, which pytest undoes
    itself). Any second one must clear what was imported under its stub, so the census is
    the check: a new stub-installing fixture fails here until it is paired with a teardown
    and added to the pairs above.
    """
    conftest_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "conftest.py")
    with open(conftest_path, encoding="utf-8") as fh:
        src = fh.read()
    tree = ast.parse(src)

    installers = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        writes_stub = any(
            isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Subscript)
                    and isinstance(t.value, ast.Attribute) and t.value.attr == "modules"
                    for t in n.targets)
            for n in ast.walk(fn))
        if writes_stub:
            installers.append(fn)

    assert [fn.name for fn in installers] == ["rt"], (
        f"conftest installs stub modules in {[fn.name for fn in installers]}; each one "
        f"needs a teardown that clears what was imported under it, and a pair in "
        f"ORDER_DEPENDENT_PAIRS that runs it before a module reading those imports")

    for fn in installers:
        body = ast.get_source_segment(src, fn) or ""
        assert "set(sys.modules) - before" in body or "- before" in body, (
            f"conftest.{fn.name} installs a stub and never clears the modules imported "
            f"under it; restoring the stub entries alone leaves those importable")
        assert "armature_core" in body, (
            f"conftest.{fn.name}'s teardown does not name the package whose modules the "
            f"stub makes importable")
