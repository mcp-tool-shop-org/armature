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
