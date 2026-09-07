"""Suite entry point — how to run these tests, and what the skips mean.

From the repo root, with this worktree first on the path and the sibling record-index
binding available:

    PYTHONPATH=<repo>;<repo>/tools .venv/Scripts/python.exe -m pytest -q

(`ARMATURE_RECORD_INDEX` or the default sibling `E:/AI/record-index` is prepended by this
conftest when present — hand-extending PYTHONPATH is no longer required for the binding.)

Use the repo venv interpreter by path (never a bare `python` on PATH — that is the system
install this suite forbids). Re-derivation recipes in test comments cite this same
interpreter; they do not retype a different one. CI runs the suite a second time under
`-O` (verify.ps1), so helpers under tests/ `raise` rather than `assert` — `assert` is
deleted by optimize and would leave the -O leg unpoliced.

Expected wall-clock on this rig for a full plain-interpreter pass is about 10–15 minutes
(~11 minutes measured on an isolated checkout of this tree). A progress line that stops
advancing past that bound is a stall, not a slow suite; external-binary subprocesses in
the suite carry a short timeout so a hung `git`/`node`/`bash` raises TimeoutExpired.

Suite selection (wave 34, F-19d81931; wave 37, F-4b60724b) — registered in
`pytest_configure` below; applied mechanically by module path/name in
`pytest_collection_modifyitems`:

- `-m paid` / `-m "not blender"` / `-m sheet` / `-m measure` / `-m amend` /
  `-m control_sequence` / `-m fast` / `-m full`
- `--suite-family=<name>` — second axis that keeps only items carrying that marker
- `--suite-speed=fast` — census/pure unit tests (excludes blender + paid); short local loop
- `--suite-speed=full` — entire suite (default when the option is omitted)

pytest-xdist (parallel workers) is OUT-OF-DOMAIN for this seat — ci-packaging owns the
dependency install; this harness only owns the mark/partition scheme.

Operator levers (defaults are this rig's paths; set them on any other machine):

- `ARMATURE_BLENDER` — Blender executable; default
  `C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe`
- `ARMATURE_GIT` — git executable; default `git` (resolved on PATH)
- `ARMATURE_FONT_DIR` — optional extra font directory for sheet/label tests
- `ARMATURE_RECORD_INDEX` — sibling `record-index` checkout; default `E:/AI/record-index`
  when that directory exists (prepended to `sys.path` before collection)

Skip families, one sentence each:

- Blender missing — modules that drive headless Blender skip when `ARMATURE_BLENDER` is
  absent; the skip reason names the lever.
- git missing — packaging ignore-list tests skip when `ARMATURE_GIT`/`git` is absent.
- bash / node missing — workflow and launcher tests that shell out skip when the binary
  is not on PATH.
- record_index absent — `test_record_index_binding.py` skips unless `ARMATURE_RECORD_INDEX`
  (or the default sibling) resolves and imports.
- banked / sibling trees — tests that read gitignored `outputs/` banks or a sibling
  facet tree skip when those paths are not present.
- fonts — label/sheet tests skip when no permitted face is in `ARMATURE_FONT_DIR` or a
  platform font directory.
- platform — a few signal/posix-only cases skip on Windows.
"""

import copy
import importlib.util
import json
import os
import sys
import types
from unittest import mock

import pytest

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLENDER = os.environ.get(
    "ARMATURE_BLENDER", r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
)
GIT = os.environ.get("ARMATURE_GIT", "git")
#: Wave 37, F-1f71ab4b — single documented lever for the sibling record-index binding.
RECORD_INDEX_DEFAULT = os.path.join(os.path.dirname(REPO), "record-index")
RECORD_INDEX = os.environ.get("ARMATURE_RECORD_INDEX", RECORD_INDEX_DEFAULT)


def _ensure_record_index_on_path():
    """Prepend ARMATURE_RECORD_INDEX (or the default sibling) before collection."""
    configured = os.environ.get("ARMATURE_RECORD_INDEX")
    path = configured if configured else (
        RECORD_INDEX_DEFAULT if os.path.isdir(RECORD_INDEX_DEFAULT) else None)
    if not path:
        return None
    path = os.path.abspath(path)
    if os.path.isdir(path) and path not in sys.path:
        sys.path.insert(0, path)
    return path if os.path.isdir(path) else None


_ensure_record_index_on_path()

#: Wave 35, F-4515289b — skip-family levers named in this module's docstring. Every
#: `pytest.mark.skipif` reason in tests/** must name one of these (or sit on the
#: shrinking exemption list in `tests/test_skip_lever_census.py`).
SKIP_LEVER_VOCABULARY = (
    "ARMATURE_BLENDER",
    "ARMATURE_GIT",
    "ARMATURE_FONT_DIR",
    "ARMATURE_RECORD_INDEX",
    "bash",
    "node",
    "record-index",
    "record_index",
    "PYTHONPATH",
    "outputs/",
    "gitignored",
    "facet",
    "platform",
    "Windows",
    "POSIX",
    "PowerShell",
    "Pillow",
    "trove",
    "npm",
)


def _git_on_path():
    import shutil
    import subprocess

    exe = GIT if os.path.isabs(GIT) or os.path.sep in GIT else shutil.which(GIT)
    if not exe:
        return False
    try:
        return subprocess.run(
            [exe, "--version"], capture_output=True, timeout=30
        ).returncode == 0
    except OSError:
        return False


def requires_blender():
    """Skip when `ARMATURE_BLENDER` does not resolve to an executable file."""
    return pytest.mark.skipif(
        not os.path.isfile(BLENDER),
        reason=(f"Blender not found at {BLENDER}; set ARMATURE_BLENDER to your blender "
                "executable to run these"),
    )


def requires_git():
    """Skip when `ARMATURE_GIT`/`git` is not runnable."""
    return pytest.mark.skipif(
        not _git_on_path(),
        reason=(f"git not found via ARMATURE_GIT={GIT!r}; set ARMATURE_GIT to your git "
                "executable (default 'git' on PATH) — the ignore list can only be read "
                "through it"),
    )


def _permitted_face_present():
    """True when sheet_compose can resolve arial on this machine (unpatched)."""
    try:
        import sheet_compose as SC
    except Exception:
        return False
    env = getattr(SC, "FONT_ENV", "ARMATURE_FONT_DIR")
    saved = os.environ.pop(env, None)
    try:
        if hasattr(SC, "clear_font_index"):
            SC.clear_font_index()
        SC.resolve_font_path("arial.ttf")
        return True
    except Exception:
        return False
    finally:
        if saved is not None:
            os.environ[env] = saved
        if hasattr(SC, "clear_font_index"):
            SC.clear_font_index()


def requires_fonts():
    """Skip when no permitted face is under `ARMATURE_FONT_DIR` or a platform font dir."""
    return pytest.mark.skipif(
        not _permitted_face_present(),
        reason=("this machine has none of the permitted faces (arial / LiberationSans / "
                "NotoSans) in ARMATURE_FONT_DIR or any platform font directory"),
    )


def requires_bank(path, *, lever="outputs/"):
    """Skip when a gitignored bank / sibling path is absent — reason names the lever."""
    return pytest.mark.skipif(
        not os.path.exists(path),
        reason=(f"banked path {path!r} is not present ({lever} is gitignored / rig-local); "
                f"re-fetch or mount it before quoting this experiment's values"),
    )


def load_ok_payload(text, prefix="SAVED_ADMISSION_OK"):
    """Parse a builders OK receipt: one-line JSON or sentinel + pretty body (wave 32).

    Wave 35, F-a048ef6f — the ONE receipt reader for `*_OK` sentinels. Call sites that
    hand-roll `startswith`/`split` against an OK token belong on the shrinking exemption
    list in `tests/test_ok_payload_adoption.py` or must migrate here.
    """
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith(prefix + " "):
            rest = ln[len(prefix) + 1:].lstrip()
            if rest.startswith("{"):
                acc = [rest]
                if rest.count("{") == rest.count("}") and rest.rstrip().endswith("}"):
                    return json.loads(rest)
                for cont in lines[i + 1:]:
                    acc.append(cont)
                    try:
                        return json.loads("\n".join(acc))
                    except json.JSONDecodeError:
                        continue
                raise AssertionError(f"{prefix}: truncated JSON on sentinel line")
            # Non-JSON remainder (path-only receipts): return the rest as a string payload.
            return rest
        if ln == prefix:
            acc = []
            for cont in lines[i + 1:]:
                if not acc and cont and not cont.lstrip().startswith(("{", "[", '"')):
                    break
                acc.append(cont)
                try:
                    return json.loads("\n".join(acc))
                except json.JSONDecodeError:
                    continue
            raise AssertionError(f"{prefix}: no JSON body after sentinel")
        # `CAST_SHEET_OK path (w, h) font=...` — sentinel as first whitespace token.
        if ln.split(" ", 1)[0] == prefix and " " in ln:
            return ln[len(prefix) + 1:]
    raise AssertionError(f"missing {prefix}")


@pytest.fixture(scope="module")
def rt():
    """`render_turnaround`, imported with Blender stubbed out.

    Written for S04's ortho tests and moved here when S05's pin tests needed the same
    stub — one copy, not two that can drift apart. The module does `import bpy` at the
    top, so the suite cannot import it the ordinary way. The repo's older idiom
    (`test_turnaround.py`, `test_framing.py`) regexes one function out of the source text
    and execs it, which works and silently stops covering anything the regex does not
    reach. Stubbing the two modules Blender owns and importing the real file covers
    `parse_args`, both solves, the manifest's scale record and the module constants at
    once, and it fails loudly if the import surface changes.

    Wave 6, routed from core-solvers and measured here. Restoring `bpy` and `mathutils`
    is not the whole teardown. `render_turnaround` imports `armature_core.blender_scene`,
    which imports `bpy`, so under the stub that module lands in `sys.modules` and STAYS
    there — importable, for the rest of the session, on a machine with no Blender.
    `tests/test_cli.py` then reads `_probe("blender_scene")` as `ok` where the honest
    answer is `needs-blender`. Measured on this branch:
    `pytest tests/test_turnaround_ortho.py tests/test_cli.py` -> 3 failed;
    `pytest tests/test_cli.py` alone -> 0. Alphabetical collection puts `test_cli.py`
    first in a full run, so the suite hid an order-dependent pass rather than a broken
    one. `tests/test_cli.py:139-153` already carries this idea for its own stubbing; the
    fix here is the same one, in the fixture that installs the stubs.
    """
    # WAVE 22 (instruments, F-a2630f86): `bmesh` joins the stubbed set, and the reason is a
    # fixture of the tools' contract rather than a preference. `render_turnaround` now
    # imports `rig_character` for `render_target_snapshot` / `require_render_target_moved`
    # (`export_target_snapshot`'s twins, housed beside it), and `rig_character.py:42` does
    # `import bmesh` at module scope. `blender_stub.blender_stubbed()` has stubbed all four
    # of `bpy`, `bmesh`, `mathutils` and `mathutils.kdtree` since wave 6; this fixture
    # stubbed two, so the two copies of one idea had drifted and the narrower one broke on
    # a new edge in the module it exists to import. Same set here now, and the teardown
    # below already pops by name.
    saved = {k: sys.modules.get(k) for k in ("bpy", "bmesh", "mathutils")}
    before = set(sys.modules)
    sys.modules["bpy"] = mock.MagicMock(name="bpy")
    sys.modules["bmesh"] = mock.MagicMock(name="bmesh")
    mathutils = types.ModuleType("mathutils")
    mathutils.Vector = lambda v: v
    mathutils.Matrix = mock.MagicMock(name="Matrix")
    sys.modules["mathutils"] = mathutils
    try:
        path = os.path.join(TOOLS, "render_turnaround.py")
        spec = importlib.util.spec_from_file_location("_rt_under_test", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        yield mod
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
        # Everything that was first imported UNDER the stub goes with it. Anything else
        # would leave a module the next test can import only because Blender was faked
        # for it — the reading `armature check` exists to make honestly.
        # WAVE 14 (instruments, F-267361f5): a `tools/` module by NAME goes too, not only
        # `armature_core`. `render_turnaround` now imports `render_start_frame` for the one
        # `require_frame_size`, and that module lands in `sys.modules` under the stub and
        # stayed there — the exact leak this teardown exists to stop, one level out.
        # `blender_stub.blender_stubbed`'s teardown already keyed on both; this is the one
        # rule, carried rather than re-derived.
        _tool_names = {fn[:-3] for fn in os.listdir(TOOLS) if fn.endswith(".py")}
        for name in sorted(set(sys.modules) - before):
            root = name.split(".", 1)[0]
            if root == "armature_core" or root in _tool_names:
                gone = sys.modules.pop(name, None)
                # The registry entry is not the only binding: importing `armature_core.x`
                # also sets `x` as an attribute of the package, and `from armature_core
                # import x` reads that attribute first. Found by the wave-6 serial verify
                # through blender_stub's twin of this teardown; carried here (one rule).
                parent_name, _, child = name.rpartition(".")
                parent = sys.modules.get(parent_name) if parent_name else None
                if parent is not None and getattr(parent, child, None) is gone:
                    delattr(parent, child)


# --------------------------------------------------------------- repo-anchored resources

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
UPLOAD_FIXTURES = os.path.join(FIXTURES, "uploads")
#: The committed byte copies of gitignored `outputs/` RECORDS, laid out exactly as the live
#: tree lays them out, minus the leading `outputs/` — so `outputs/E02/payloads/A0.json`
#: is `tests/fixtures/records/E02/payloads/A0.json`. The root is NOT called `outputs`:
#: measured 2026-09-05, `git check-ignore -v tests/fixtures/outputs/E02/payloads/A0.json`
#: answers `.gitignore:3:outputs/` — the pattern has no leading slash, so it matches at any
#: depth and the fixtures would have been ignored wherever they were put under that name.
PAYLOAD_FIXTURES = os.path.join(FIXTURES, "records")

#: The upload name maps `build_payload.EXPERIMENTS` names as `outputs/E0x/uploads_*.json`.
#: They are content-addressed server filenames and nothing else — no pixels, ~2.7 KB each —
#: so committing them lets the E02 byte pin and E03's arm comparisons ride every run.
#: Measured 2026-09-03: `bp.build` reads ONLY these maps (the 480x832 control PNGs are read
#: by `_distinct_source_frames`, which returns None when the directory is absent), and both
#: pinned E02 payload hashes reproduce from the maps alone.
UPLOAD_RECORDS = (
    "outputs/E02/uploads_depth_pershot.json",
    "outputs/E02/uploads_depth_pershot_inverted.json",
    "outputs/E02/uploads_reference.json",
    "outputs/E03/uploads_posearc.json",
    "outputs/E03/uploads_static.json",
)

#: The two E02 payloads `test_gate_s.py` compares every E04 submission against, committed as
#: byte copies (wave 26, F-4c22f096). They are 9,566 bytes each and they are a RECORD of what
#: was submitted, not a product of the code under test — the E04 side of every comparison is
#: built in process. `A0` is C-bright's base and `A1b` is C-dark's; `A1a` is deliberately not
#: here, because it ran before the lossless tap existed and carries no node 302.
PAYLOAD_RECORDS = (
    "outputs/E02/payloads/A0.json",
    "outputs/E02/payloads/A1b.json",
)

#: `family -> (population, fixture root)`. ONE table, so the byte-copy census and the
#: branch-agreement census in `tests/test_measure_tracking.py` walk every committed record
#: family rather than only the one that happened to be written first (wave 26, F-4c22f096).
RECORD_FAMILIES = {
    "uploads": (UPLOAD_RECORDS, UPLOAD_FIXTURES),
    "payloads": (PAYLOAD_RECORDS, PAYLOAD_FIXTURES),
}

#: Wave 34, F-025b750b — one minimal API-format graph per spend builder, committed under
#: `tests/fixtures/records/<route>/` and resolved live-or-fixture the same way uploads are.
#: Paths are `outputs/<route>/<file>` so `_record_paths` strips the leading `outputs/` and
#: lands on `tests/fixtures/records/<route>/<file>`. The three pre-existing camera/i2v
#: fixtures under `tests/fixtures/*.api.json` stay; these are the bank that covers the
#: builders those three never reached.
API_GRAPH_RECORDS = (
    "outputs/animate/E08-probe-animate.api.json",
    "outputs/assembly/S03-assembly.api.json",
    "outputs/camera_i2v/E12-w3-camera-i2v.api.json",
    "outputs/cascade/E13-cascade.api.json",
    "outputs/i2v/E11-w1-probe-i2v.api.json",
    "outputs/lora_arm/E14-T-camera-i2v.api.json",
    "outputs/payload/E02-A0.api.json",
    "outputs/r2v/E13-A1-seed2026081351.api.json",
    "outputs/t2v/E09-B2-probe-t2v.api.json",
)
#: Kept OUT of `RECORD_FAMILIES`: that table's byte-copy / branch-agreement census in
#: `test_measure_tracking.py` keys a public resolver map of `uploads`/`payloads` only.
#: These graphs still resolve through the same `_record*` helpers via `api_graph_record`.


def repo_file(relpath):
    """An absolute path under the repo root for a `outputs/...`-style relative path.

    Skip guards and fixture reads anchor here, never on `os.getcwd()`. A bare relative
    path resolves against whatever directory pytest was invoked from: measured both
    directions on 2026-09-03 — from the repo root a guard read False, and from an
    unrelated scratch directory seeded with the same file name it read True. Thirty-two
    tests, including the whole through-the-builder half of Gate S, were decided by four
    such guards, and the skip reason read as though the repo simply had no run in it.
    """
    return os.path.join(REPO, *str(relpath).split("/"))


def _record_paths(relpath, fixture_root):
    """`(live, fixture)` — both candidate paths for one committed record, resolved.

    Split out of `upload_record` (wave 23, F-ef2a00e9) so the two copies can be COMPARED,
    not only chosen between. Nothing about the choice changes. Wave 26 (F-4c22f096) gave it
    a `fixture_root` so the E02 payload records resolve through the SAME three functions the
    upload name maps do, rather than through a second spelling of them.
    """
    return (repo_file(relpath),
            os.path.join(fixture_root, *str(relpath).split("/")[1:]))


def _record_branch(relpath, fixture_root):
    """Which copy `_record` would return, and what exists — for a test to RECORD.

    `"live"`, `"fixture"` or `"neither"`. A run that grades the live record and a run that
    grades the fixture are grading different inputs under one function name; a test that
    quotes a pinned hash needs to be able to say which one it read.
    """
    live, fixture = _record_paths(relpath, fixture_root)
    if os.path.isfile(live):
        return "live"
    return "fixture" if os.path.isfile(fixture) else "neither"


def _record(relpath, fixture_root):
    """The real run if this rig has one, else the committed byte copy — see `upload_record`."""
    live, fixture = _record_paths(relpath, fixture_root)
    if os.path.isfile(live):
        return live
    if os.path.isfile(fixture):
        return fixture
    # Neither: hand back the path the caller asked for so its own error names it.
    return live


def upload_record_paths(relpath):
    """`(live, fixture)` for one upload name map."""
    return _record_paths(relpath, UPLOAD_FIXTURES)


def upload_record_branch(relpath):
    """`"live"` / `"fixture"` / `"neither"` for one upload name map."""
    return _record_branch(relpath, UPLOAD_FIXTURES)


def payload_record_paths(relpath):
    """`(live, fixture)` for one committed E02 payload."""
    return _record_paths(relpath, PAYLOAD_FIXTURES)


def payload_record_branch(relpath):
    """`"live"` / `"fixture"` / `"neither"` for one committed E02 payload."""
    return _record_branch(relpath, PAYLOAD_FIXTURES)


def payload_record(relpath):
    """Resolve one E02 payload: the real run if this rig has one, else the committed copy.

    WAVE 26, F-4c22f096 — the twelve collected items of
    `tests/test_gate_s.py::test_an_E04_payload_differs_from_its_E02_base_ONLY_in_the_seed`
    (4 arms x 3 seeds) skipped on every clone, in every isolated worktree and on every
    ubuntu-latest job, because `outputs/` is gitignored (`git check-ignore -v` names
    `.gitignore:3 outputs/`). That is the test the file's own comment calls "the load-bearing
    test of the whole experiment" — the one that stops a refactor silently re-topologising an
    experiment that has already been run and reported — and it ran on exactly one machine.

    The stated reason it could not be committed was that the payloads are "the thing under
    test's own product". The test body contradicts that four lines below: it BUILDS the E04
    side in process (`bp.build(arm, "E04", seed=seed)`) and READS the E02 side as an archive
    of what was submitted. So the E02 payloads are a record, exactly like the upload name maps
    committed under `tests/fixtures/uploads/` — 9,566 bytes each — and they are resolved here
    the same way, through the same three functions, with the same byte-equality check in
    `tests/test_measure_tracking.py`.
    """
    return _record(relpath, PAYLOAD_FIXTURES)


def upload_record(relpath):
    """Resolve one upload name map: the real run if this rig has one, else the fixture.

    `outputs/` is gitignored, so on CI and on any clone the fallback is what exists. The
    fixture is a byte copy of the record the run actually submitted, which is why the
    pinned payload hashes still bind against it.

    **That last sentence is a load-bearing claim and it is now CHECKED** (wave 23,
    F-ef2a00e9): `tests/test_measure_tracking.py::
    test_every_upload_record_fixture_is_a_byte_copy_of_the_live_record` compares the two
    copies wherever both exist. It was prose with nothing behind it, and both branches are
    live at once across the machines that run this suite — an isolated worktree carries no
    upload maps under `outputs/` and takes the fixture, while the main checkout has the real
    files and takes those, so the rig and CI graded different inputs under one function name.
    Measured 2026-09-05: all five maps match their fixtures byte for byte, so this was an
    absent guard rather than a live divergence.
    """
    return _record(relpath, UPLOAD_FIXTURES)


def api_graph_record_paths(relpath):
    """`(live, fixture)` for one banked spend-builder API graph."""
    return _record_paths(relpath, PAYLOAD_FIXTURES)


def api_graph_record_branch(relpath):
    """`"live"` / `"fixture"` / `"neither"` for one banked spend-builder API graph."""
    return _record_branch(relpath, PAYLOAD_FIXTURES)


def api_graph_record(relpath):
    """Resolve one spend-builder API graph: live `outputs/` copy if present, else fixture.

    WAVE 34, F-025b750b — gate_saved_graph / link-round-trip for t2v, r2v, animate,
    assembly, cascade (and the rest of the nine builders) could not be rehearsed from a
    clean clone because only three camera/i2v `*.api.json` files lived under
    `tests/fixtures/`. Same live-or-fixture helper the upload maps and E02 payloads use.
    """
    return _record(relpath, PAYLOAD_FIXTURES)


@pytest.fixture(scope="session", autouse=True)
def _upload_records_are_resolved():
    """Point `build_payload`'s upload paths at a file that exists, wherever pytest ran.

    The builder names them `outputs/E0x/uploads_*.json`, relative to the caller's working
    directory, and `outputs/` is gitignored — so the E02 byte pin, E03's arm comparisons
    and the through-the-builder half of Gate S all skipped on every clone and every CI
    run. They are the tests that stop a refactor silently re-topologising an experiment
    that has already been run and reported, which is precisely the thing that must not
    depend on who happens to have `outputs/` on their rig.

    This rewrites the paths and nothing else: same bytes, same maps, same hashes.
    """
    try:
        import build_payload as bp
    except Exception:  # pragma: no cover - the builder is always importable in this repo
        yield
        return

    saved_map = dict(bp.UPLOAD_MAP)
    saved_experiments = copy.deepcopy(bp.EXPERIMENTS)

    for arm, path in list(bp.UPLOAD_MAP.items()):
        bp.UPLOAD_MAP[arm] = upload_record(path)
    for cfg in bp.EXPERIMENTS.values():
        ref = cfg.get("reference")
        if ref:
            cfg["reference"] = (upload_record(ref[0]), ref[1])
        for arm_cfg in cfg["arms"].values():
            if isinstance(arm_cfg, dict) and arm_cfg.get("uploads"):
                arm_cfg["uploads"] = upload_record(arm_cfg["uploads"])
    try:
        yield
    finally:
        bp.UPLOAD_MAP.clear()
        bp.UPLOAD_MAP.update(saved_map)
        bp.EXPERIMENTS.clear()
        bp.EXPERIMENTS.update(saved_experiments)


# ------------------------------------------------------------------- gate assertions

#: Modules first imported under `blender_stub.blender_stubbed()`, held by STRONG reference
#: so the classes they define stay registered in `GateFailure.__subclasses__()` after the
#: stub's teardown pops them out of `sys.modules`. Keyed by name and imported exactly once:
#: a second stubbed import would build a SECOND class object of the same name and the
#: derived population would grow by one on every call.
_STUB_IMPORTED = {}


def _import_every_core_module():
    """Import every `armature_core` module so a subclass walk sees all of them.

    `__subclasses__()` only knows about classes whose module has been imported, so the
    population depends on which tests ran first — measured: `test_gates.py` alone sees 12
    andons, the full suite sees 29. A class-wide invariant checked against a population
    that changes with collection order is not class-wide.

    WAVE 10, F-27a92797 — why `blender_scene` is no longer excluded. The exclusion's stated
    reason was "it imports bpy and cannot resolve under a plain CPython", and this suite
    falsifies that in its own fixtures: `tests/blender_stub.blender_stubbed()` resolves it,
    and `tests/test_core_solver_evidence._gate_raises` already walks that exact module
    through the stub. Measured 2026-09-04: `gate_failure_subclasses()` returned 31 classes
    and `CompositorWiring` (gate `COMPOSITOR`, 3 raise sites in `blender_scene.py` by AST)
    was not among them, so `test_gates.py:387` (no subclass may inherit `GateFailure.gate`)
    and `:393` (`str(cls(...))` starts with `[<gate>] `) had never once been asked of it,
    and `test_amend_w8_core_gates`'s `known` set would have called a correct
    `andon: "CompositorWiring"` a name for no real andon. The class passes both invariants
    today — the defect was that the question could not be asked, which is the one guarantee
    a class-wide census exists to give.
    """
    import glob
    import importlib
    import warnings

    from blender_stub import blender_stubbed

    for path in sorted(glob.glob(os.path.join(TOOLS, "armature_core", "*.py"))):
        name = os.path.basename(path)[:-3]
        if name.startswith("__"):
            continue
        needs_stub = name == "blender_scene"
        if needs_stub and (name in _STUB_IMPORTED
                           or "armature_core." + name in sys.modules):
            continue
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                if needs_stub:
                    with blender_stubbed():
                        _STUB_IMPORTED[name] = importlib.import_module(
                            "armature_core." + name)
                else:
                    importlib.import_module("armature_core." + name)
        except Exception:  # pragma: no cover - a module needing an absent dependency
            pass


def gate_failure_subclasses():
    """Every concrete `GateFailure` subclass, however deeply nested.

    Enumerated rather than listed, so a gate added later joins the checks automatically —
    the whole point of the class-wide invariant is that no new andon can opt out of it.
    """
    _import_every_core_module()
    from armature_core.errors import GateFailure

    seen, out = set(), []
    stack = [GateFailure]
    while stack:
        for sub in stack.pop().__subclasses__():
            if sub in seen:
                continue
            seen.add(sub)
            out.append(sub)
            stack.append(sub)
    return sorted(out, key=lambda c: c.__name__)


def assert_gate(exc, gate_id, **expected_evidence):
    """A raised gate names its andon AND carries the measurement that fired it.

    `armature_core.errors.GateFailure.__init__` is `self.evidence = evidence or {}`, so a
    gate raised with no evidence at all is a well-formed, silent object: the report the
    Director reads names an andon with nothing behind it, and a test asserting on the
    message string stays green through it. Across `tests/` there are hundreds of
    `pytest.raises` sites on gate types and only a handful assert on `.evidence`; this is
    the shared shape that makes emptiness fail loudly.

    Accepts pytest's `ExceptionInfo` or the exception itself. `expected_evidence` is
    checked by containment, never by equality — a gate is free to report MORE than a
    caller asked about (P1 adds `unexpected` beside G2's `missing`), and a test that
    demanded an exact key set would fail on a gate that got better.
    """
    err = getattr(exc, "value", exc)
    assert isinstance(err, Exception), err
    assert err.gate == gate_id, f"raised {type(err).__name__} with gate {err.gate!r}"
    assert isinstance(err.evidence, dict), type(err.evidence)
    assert err.evidence, (
        f"[{gate_id}] {err} carries an EMPTY evidence dict. A gate that reaches a report "
        f"with nothing behind it names an andon and proves nothing; the measurement that "
        f"fired it is the payload."
    )
    for key, want in expected_evidence.items():
        assert key in err.evidence, (
            f"[{gate_id}] evidence has {sorted(err.evidence)}, no {key!r}")
        if want is not ...:
            assert err.evidence[key] == want, (
                f"[{gate_id}] evidence[{key!r}] is {err.evidence[key]!r}, expected {want!r}")
    return err.evidence


# --------------------------------------------------------------------- sheet fonts

#: The two faces `sheet_compose` asks for by name.
SHEET_REGULAR, SHEET_BOLD = "arial.ttf", "arialbd.ttf"


def pil_scalable_fallback(size):
    """A scalable font PIL itself ships — no platform font, no committed binary.

    `ImageFont.load_default(size)` returns a real FreeTypeFont (Aileron) from Pillow
    10.1 onward; before that it returned a fixed-size bitmap font that `textlength`
    cannot scale, which is why the guard below tests the returned object rather than a
    version number.
    """
    from PIL import ImageFont

    return ImageFont.load_default(size)


def pil_has_a_scalable_font():
    try:
        from PIL import ImageDraw, Image

        a = pil_scalable_fallback(20)
        b = pil_scalable_fallback(40)
        ruler = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        return ruler.textlength("MMMM", font=b) > ruler.textlength("MMMM", font=a)
    except Exception:  # pragma: no cover - ancient Pillow
        return False


#: Every module that draws a sheet through `sheet_compose`'s resolver, in the order the
#: fallback is installed. `rig_sheet_compose` and `make_cast_sheet` do
#: `from sheet_compose import font as _font`, so each holds its OWN reference bound at
#: import — patching `sheet_compose._font` does not reach either of them.
#: `tests/test_font_resolution.py` asserts this list against the modules in `tools/` that
#: actually bind it, so a fourth composer joins the fixture rather than escaping it.
SHEET_COMPOSERS = ("sheet_compose", "rig_sheet_compose", "make_cast_sheet")


def install_sheet_font_fallback(monkeypatch):
    """Point every composer's `_font` at PIL's bundled scalable face.

    Wave 6, F-c707995d. The fixture below said it let "the sheet composers" run on a
    machine with no platform fonts and patched `sheet_compose._font` alone. Measured by
    simulating a fontless runner (`platform_font_dirs() -> []`, `ARMATURE_FONT_DIR` unset)
    and running the whole suite: exactly two tests failed —
    `test_the_rig_sheet_is_as_wide_as_its_own_parameter_line` and
    `test_the_cast_sheet_is_as_wide_as_its_own_stats_label` — both raising
    `sheet_compose.FontError` at `sheet_compose.py:157` through `rig_sheet_compose.py:53`
    and `make_cast_sheet.py:44`. Both carry the module-wide
    `pytest.mark.usefixtures("sheet_fonts")`, so the fixture was active and simply missed
    them. It is a separate function from the fixture so a test can install it on a machine
    that DOES have fonts and check that it reaches all three.
    """
    import importlib

    def fallback(name, size):
        return pil_scalable_fallback(size)

    for name in SHEET_COMPOSERS:
        monkeypatch.setattr(importlib.import_module(name), "_font", fallback)
    return fallback


@pytest.fixture
def sheet_fonts(monkeypatch):
    """Let the sheet composers run on a machine with no platform fonts.

    `sheet_compose.FONT_DIR` is a hard-coded Windows font directory and the two sheet test
    modules used to skip on `not os.path.isdir(FONT_DIR)` — 23 tests that skipped on
    EVERY CI run, because CI is `ubuntu-latest` and that directory can never exist there.
    Nothing about them needs Windows: they compose PIL images and measure text widths,
    and both files exist for defects found the expensive way (1153 px of label in a
    1024 px cell that saved, opened and looked finished; a sheet cropping its own
    measurements off the right edge).

    The substitution is deliberate and narrow. If the module's own resolver produces a
    font, it is left alone and the tests measure exactly what the module draws with. If
    it cannot, `_font` is pointed at PIL's bundled scalable face for the duration of the
    test — so what is exercised is the LAYOUT ARITHMETIC, which is what these files
    measure, on every platform. Whether `sheet_compose` finds a real font, and whether it
    refuses by name rather than substituting silently when it cannot, is that module's
    own contract and belongs in a test of `_font`.
    """
    import sheet_compose

    try:
        sheet_compose._font(SHEET_REGULAR, 26)
        sheet_compose._font(SHEET_BOLD, 26)
    except Exception:
        install_sheet_font_fallback(monkeypatch)
    yield sheet_compose._font


def sheet_font(name, size):
    """The font `sheet_compose` will actually draw with, for a test that must measure it.

    Resolved through the module's own `_font` rather than by rebuilding
    `os.path.join(FONT_DIR, name)` in the test: the two must agree or a width assertion is
    comparing one font's metrics against another's, and FONT_DIR is exactly the thing P7
    replaces.
    """
    import sheet_compose

    return sheet_compose._font(name, size)


# --------------------------------------------------------------- suite selection markers
#
# WAVE 34, F-19d81931. The suite had no `-m paid` / `-m "not blender"` / `-m sheet`
# capability: marks were only parametrize/skipif/usefixtures/xfail, and conftest carried
# no pytest_configure / addoption / collection_modifyitems. Marker registration strings in
# pyproject.toml are OUT-OF-DOMAIN for this seat (ci-packaging); registration here is what
# makes the vocabulary usable without that half.


SUITE_MARKERS = (
    ("paid", "spend builders, fetchers, pre-submit gates, and their argv SUCCESS fixtures"),
    ("control_sequence", "control-sequence encode / invert / pack instruments"),
    ("blender", "needs Blender (ARMATURE_BLENDER) or the blender_stub"),
    ("sheet", "sheet composers and sheet argv SUCCESS fixtures"),
    ("measure", "measure_* clip/floor/lift/tracking diagnostics"),
    ("amend", "wave amend pins (test_amend_* / test_instruments_*amend_*)"),
    ("fast", "census/pure unit tests — excludes blender and paid (wave 37 F-4b60724b)"),
    ("full", "full suite including blender, paid, and subprocess instruments"),
)


def pytest_configure(config):
    for name, doc in SUITE_MARKERS:
        config.addinivalue_line("markers", f"{name}: {doc}")


def pytest_addoption(parser):
    parser.addoption(
        "--suite-family", action="store", default=None,
        help="keep only tests carrying this suite marker "
             f"(one of: {', '.join(n for n, _ in SUITE_MARKERS)})")
    parser.addoption(
        "--suite-speed", action="store", default=None, choices=("fast", "full"),
        help="fast = census/pure (no blender/paid); full = entire suite "
             "(wave 37 F-4b60724b; xdist install is ci-packaging's)")


def _module_marker_names(path):
    """Suite markers derived from a collected module's path/name — never typed per test."""
    base = os.path.basename(path)
    stem = base[:-3] if base.endswith(".py") else base
    marks = set()
    norm = path.replace("\\", "/")
    if "/tests/blender/" in norm or norm.rstrip("/").endswith("/tests/blender"):
        marks.add("blender")
    if stem.startswith("test_amend_") or "amend_w" in stem:
        marks.add("amend")
    if (stem.startswith("test_build_") or stem.startswith("test_fetch_")
            or stem.startswith("test_gate_saved") or stem.startswith("test_gate_b")
            or stem in ("test_assembly", "test_cascade", "test_r2v_payload",
                        "test_canon_spend", "test_route_gates", "test_paid_argv_smoke",
                        "test_api_fixture_bank", "test_encode_control",
                        "test_fake_comfy")):
        marks.add("paid")
    if (stem.startswith("test_measure_") or stem.startswith("test_instruments_measure")
            or stem == "test_measure_argv_smoke"):
        marks.add("measure")
    if ("sheet" in stem or stem in ("test_sheet_compose", "test_sheet_pairing",
                                    "test_sheet_sides", "test_sheet_argv_smoke",
                                    "test_extended_sheet_argv_smoke",
                                    "test_e13_sheet")):
        marks.add("sheet")
    if (stem.startswith("test_blender") or stem.startswith("test_render_")
            or stem in ("test_floor_material", "test_ortho_convention",
                        "test_plate_composite", "test_pose_arc_roundtrip",
                        "test_visibility", "test_walk", "test_rig_gates",
                        "test_rig_character_dispatch", "test_lift_solve",
                        "test_instrument_exits", "test_turnaround",
                        "test_turnaround_ortho", "test_turnaround_pin",
                        "test_framing", "test_pinned_camera", "test_pinned_framing",
                        "test_startframe", "test_aapose_convention",
                        "test_openpose_convention", "test_check_pack")):
        marks.add("blender")
    if stem in ("test_encode_control", "test_invert_frames", "test_pack_pose_pack",
                "test_extract_clip_frames", "test_instrument_argv_smoke"):
        marks.add("control_sequence")
    # Source scan: a module that skipifs on ARMATURE_BLENDER / BLENDER is blender-family
    # even when its name does not say so.
    if os.path.isfile(path):
        try:
            text = open(path, encoding="utf-8").read(8000)
        except OSError:
            text = ""
        if "ARMATURE_BLENDER" in text or "blender_stub" in text:
            marks.add("blender")
    # Wave 37 F-4b60724b: every item is `full`; `fast` is the non-blender/non-paid partition.
    marks.add("full")
    if "blender" not in marks and "paid" not in marks:
        marks.add("fast")
    return marks


def pytest_collection_modifyitems(config, items):
    family = config.getoption("--suite-family")
    speed = config.getoption("--suite-speed")
    kept = []
    for item in items:
        path = str(getattr(item, "fspath", "") or getattr(item, "path", ""))
        for name in _module_marker_names(path):
            item.add_marker(getattr(pytest.mark, name))
        names = {m.name for m in item.iter_markers()}
        if family and family not in names:
            continue
        if speed == "fast" and "fast" not in names:
            continue
        kept.append(item)
    if family or speed == "fast":
        items[:] = kept
