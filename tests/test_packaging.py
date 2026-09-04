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
