"""The installed command's tests.

What would this look like if the code were wrong in the specific way each check exists
to catch? The failure this file is really written against is a PACKAGING failure: the
surface table lists a module that the wheel does not ship, or ships a module the table
never names. Both make `armature check` lie — it would report a clean install while an
importer gets ImportError, or hide a module from the only list a user reads. So the
table is checked against the directory on disk in both directions, not merely for
self-consistency.

`blender_scene` is the deliberate exception everywhere below: it imports bpy, so it
cannot resolve under a plain CPython and MUST NOT be counted a defect.
"""
import json
import os

import pytest

from armature_core import cli

CORE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "armature_core"
)


def _shipped_modules():
    """Every module actually on disk, minus the package machinery and the CLI itself."""
    out = set()
    for fn in os.listdir(CORE_DIR):
        if fn.endswith(".py") and not fn.startswith("__") and fn != "cli.py":
            out.add(fn[:-3])
    return out


def test_surface_names_only_modules_that_exist():
    """A name in the table with no file behind it is a promise the wheel cannot keep."""
    listed = {m for m, _ in cli.SURFACE}
    missing = listed - _shipped_modules()
    assert not missing, f"SURFACE lists modules with no file: {sorted(missing)}"


def test_surface_covers_every_shipped_module():
    """The other direction: a module the table forgets is invisible to every reader."""
    listed = {m for m, _ in cli.SURFACE}
    unlisted = _shipped_modules() - listed
    assert not unlisted, f"modules on disk missing from SURFACE: {sorted(unlisted)}"


def test_surface_entries_are_described():
    """An empty purpose column is a row that teaches nothing."""
    for name, purpose in cli.SURFACE:
        assert purpose.strip(), f"{name} carries no description"


def test_check_reports_ok_for_pure_python_modules(capsys):
    """The real import path, not a mock: every non-Blender module must resolve here."""
    rc = cli.main(["check", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["missing"] == []
    assert rc == 0
    for name, state in payload["modules"].items():
        if name == "blender_scene":
            assert state == "needs-blender"
        else:
            assert state == "ok", f"{name} did not import: {state}"


def test_check_exits_nonzero_when_a_module_is_missing(monkeypatch, capsys):
    """The red case. A broken install must not exit 0 — a green exit code on a broken
    install is the failure mode that makes the whole command worthless."""
    monkeypatch.setattr(cli, "SURFACE", [("no_such_module_xyz", "invented for this test")])
    rc = cli.main(["check"])
    assert rc == 1
    assert "MISSING" in capsys.readouterr().out


def test_blender_probe_is_not_counted_a_defect(monkeypatch):
    """bpy is absent in this suite by construction, so this asserts the real outcome."""
    assert cli._probe("blender_scene") == "needs-blender"


def test_modules_json_is_machine_readable(capsys):
    rows = json.loads(_run(["modules", "--json"], capsys))
    assert len(rows) == len(cli.SURFACE)
    assert {"module", "purpose"} == set(rows[0])


def test_where_names_the_blender_invocation(capsys):
    """`where` exists to stop a user reaching for a console script that cannot exist;
    if it stops naming the Blender call, it has stopped doing its one job."""
    cli.main(["where"])
    out = capsys.readouterr().out
    assert "blender -b -P" in out
    assert "armature" in out


def test_version_flag_exits_clean(capsys):
    with pytest.raises(SystemExit) as e:
        cli.main(["--version"])
    assert e.value.code == 0
    assert "armature-studio" in capsys.readouterr().out


def test_bare_invocation_prints_help_and_exits_zero(capsys):
    rc = cli.main([])
    assert rc == 0
    assert "usage" in capsys.readouterr().out.lower()


def _run(argv, capsys):
    cli.main(argv)
    return capsys.readouterr().out


# =====================================================================================
# W3 amend — `armature check` must state what is true of the install.
# =====================================================================================

import re
import sys


class _Blocker:
    """A meta_path finder that makes named roots unfindable, as a clean-venv would."""

    def __init__(self, *roots):
        self.roots = set(roots)

    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in self.roots:
            raise ModuleNotFoundError(f"blocked for this test: {name}", name=name)
        return None


@pytest.fixture
def block(monkeypatch):
    """Make named roots unfindable, as they would be on a clean-venv wheel install.

    Every `armature_core.*` entry is dropped from `sys.modules` too, or the probe would
    hand back the copy this test session already imported and the blocker would never be
    consulted. monkeypatch restores both maps at teardown.
    """
    def _block(*roots):
        # `armature_core` itself goes too. Deleting only the submodules leaves the
        # ORIGINAL package object in sys.modules while the re-import rebinds its
        # attributes to fresh copies, so a later `from armature_core import gates`
        # elsewhere in the session gets a class that is not the one its module-level
        # import bound — and `pytest.raises(SomeGate)` stops matching.
        stale = [k for k in sys.modules
                 if k.split(".")[0] in roots or k == "armature_core"
                 or k.startswith("armature_core.")]
        for key in stale:
            monkeypatch.delitem(sys.modules, key, raising=False)
        monkeypatch.setattr(sys, "meta_path", [_Blocker(*roots)] + list(sys.meta_path))
    return _block


# --- a dependency imported inside a function body (F-4466d82c, pair P6) -----------

def test_a_function_local_dependency_that_is_absent_is_reported(block):
    """`_probe` executed the module-level import and nothing else, so a dependency
    imported inside a function body was never reached. Measured with cv2, PIL and
    matplotlib all blocked: every SURFACE row read 'ok', `main(['check'])` printed "all
    modules resolved" and returned 0 — and `donor_gate.mean_consecutive_frame_difference`
    then raised ModuleNotFoundError: PIL. The command said 'importable' in language an
    operator reads as 'runnable', on an install where two modules' functions cannot run."""
    block("PIL")
    assert cli._probe("donor_gate") == "needs-PIL"
    assert cli.main(["check"]) == 1


def test_the_json_names_the_row_it_counted(block, capsys):
    block("cv2", "matplotlib")
    rc = cli.main(["check", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert payload["modules"]["aapose"] == "needs-cv2/matplotlib"
    assert "aapose" in payload["missing"]


def test_the_function_local_scan_finds_what_the_ast_walk_found():
    """The measurement this fix is built on, pinned: an ast.walk over each SURFACE
    module's source for Import/ImportFrom nested in a FunctionDef finds
    gates -> numpy; donor_gate -> PIL, numpy; aapose -> cv2, matplotlib."""
    assert cli._function_local_dependencies("gates") == ["numpy"]
    assert cli._function_local_dependencies("donor_gate") == ["PIL", "numpy"]
    assert cli._function_local_dependencies("aapose") == ["cv2", "matplotlib"]
    assert cli._function_local_dependencies("errors") == []


def test_a_module_level_dependency_is_still_reported_as_missing(block):
    """The other half: a root the module imports at the top is caught by the import
    itself, and must not be mistaken for the expected Blender condition."""
    block("numpy")
    assert cli._probe("channels") in ("MISSING", "needs-numpy")
    assert cli.main(["check"]) == 1


# --- needs-blender is a reading about bpy, not about blender_scene (F-96137082) ---

def test_a_genuinely_broken_blender_scene_is_not_read_as_the_expected_condition(monkeypatch):
    """`_probe` caught ImportError and returned 'needs-blender' for `blender_scene`
    without inspecting which module was missing. Measured: making the import raise
    ImportError(name='armature_core.typo_helper') returned 'needs-blender', identical to
    the genuine bpy-absent reading, and `main(['check'])` printed "all modules resolved"
    and returned 0 — the repo's own install verifier reporting a healthy install on a
    genuinely broken module."""
    real = cli.importlib.import_module

    def fake(name, *a, **kw):
        if name.endswith("blender_scene"):
            raise ImportError("no module named armature_core.nope",
                              name="armature_core.nope")
        return real(name, *a, **kw)

    monkeypatch.setattr(cli.importlib, "import_module", fake)
    assert cli._probe("blender_scene") == "MISSING"
    assert cli.main(["check"]) == 1


def test_a_non_import_error_at_import_time_is_missing_not_a_traceback(monkeypatch):
    """A SyntaxError or an AttributeError raised at import time escaped `except
    ImportError` and reached the operator as a traceback rather than as a MISSING row."""
    real = cli.importlib.import_module

    def fake(name, *a, **kw):
        if name.endswith("channels"):
            raise SyntaxError("invalid syntax")
        return real(name, *a, **kw)

    monkeypatch.setattr(cli.importlib, "import_module", fake)
    assert cli._probe("channels") == "MISSING"
    assert cli.main(["check"]) == 1


def test_bpy_is_still_the_expected_condition():
    """The direction that must not break: bpy really is absent here, and that row is
    not a defect."""
    assert cli._probe("blender_scene") == "needs-blender"
    assert cli.main(["check"]) == 0


# --- the surface may not name a gate the module does not carry (F-7f9ab627) -------

def _gate_ids(description):
    """Gate ids a SURFACE description names, in the two forms the table uses:
    a `gates: A, B` list and an inline `Gate NAME` (or `Gate A/B`)."""
    ids = []
    listed = re.search(r"gates?:\s*([A-Z0-9_,/ ]+)", description)
    if listed:
        ids += re.findall(r"[A-Z][A-Z0-9_]*|G\d", listed.group(1))
    for named in re.findall(r"\bGate ([A-Z][A-Z0-9_]*(?:/[A-Z][A-Z0-9_]*)*)", description):
        ids += named.split("/")
    return sorted(set(ids))


def test_the_id_parser_finds_the_ids_that_are_there():
    """A parser that extracted nothing would make the test below vacuous."""
    found = {m: _gate_ids(d) for m, d in cli.SURFACE}
    assert found["route_gates"]
    assert found["donor_gate"] == ["DONOR"]
    assert "ALPHA" in found["turnaround"] and "CROP" in found["turnaround"]
    assert "G1" in found["gates"]


def test_every_gate_named_in_the_surface_exists_in_the_module_beside_it():
    """Measured 2026-09-03: the `route_gates` row read "graph-level gates: ROUTE, PAIR,
    PAIR_TIER, LEDGER" and the module defines exactly two gate classes. PAIR_TIER and
    LEDGER live in `tools/build_lora_arm_payload.py`, which is not in the installed
    package at all — so `armature modules --json`, the machine-readable surface, told a
    consumer a gate exists in a module that does not carry it."""
    import importlib as _il

    for name, description in cli.SURFACE:
        wanted = _gate_ids(description)
        if not wanted or name == "blender_scene":
            continue
        mod = _il.import_module(f"armature_core.{name}")
        carried = {getattr(obj, "gate", None) for obj in vars(mod).values()
                   if isinstance(obj, type)}
        for gid in wanted:
            assert gid in carried, (
                f"SURFACE says {name} carries gate {gid!r}; that module exposes "
                f"{sorted(g for g in carried if g)}")


def test_route_gates_is_described_by_what_it_defines():
    row = dict(cli.SURFACE)["route_gates"]
    assert "PAIR_TIER" not in row and "LEDGER" not in row
