"""Wave 29 Stage D — core-gates pins for F-0f29b961 and F-9407b553."""
import json
import os
import re

import pytest

from armature_core import cli
from armature_core.errors import GateFailure


# --- F-0f29b961: needs-blender is not an exception line -------------------------

def test_needs_blender_row_uses_the_where_sentence_not_an_exception(capsys):
    """Measured: `armature check` printed
    `ModuleNotFoundError: No module named 'bpy' (no module named 'bpy')` on the
    expected needs-blender row, directly above `all modules resolved`."""
    rc = cli.main(["check"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "needs-blender" in out
    assert "all modules resolved" in out
    assert "ModuleNotFoundError" not in out
    assert "No module named 'bpy'" not in out
    assert "render scripts run inside Blender, from a repo checkout" in out


def test_json_module_rows_still_carry_the_raw_blender_cause(capsys):
    """`--json`'s `module_rows` keeps error / message / missing_root either way."""
    rc = cli.main(["check", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    row = next(r for r in payload["module_rows"] if r["module"] == "blender_scene")
    assert row["status"] == "needs-blender"
    assert row["error"] == "ModuleNotFoundError"
    assert "bpy" in (row["message"] or "")
    assert row["missing_root"] == "bpy"


def test_parenthetical_is_suppressed_when_message_already_names_the_root(
        monkeypatch, capsys):
    """A ModuleNotFoundError's message IS `No module named '<root>'`; appending the
    parenthetical restated it."""
    real = cli.importlib.import_module

    def boom(name, *a, **k):
        if name == "armature_core.shotspec":
            raise ModuleNotFoundError("No module named 'nope'", name="nope")
        return real(name, *a, **k)

    monkeypatch.setattr(cli.importlib, "import_module", boom)
    assert cli.main(["check"]) == 1
    text = capsys.readouterr().out
    assert "ModuleNotFoundError: No module named 'nope'" in text
    assert "(no module named 'nope')" not in text


def test_parenthetical_still_appears_when_message_omits_the_root(monkeypatch, capsys):
    """The other direction: an ImportError whose message does not carry the root still
    gets the parenthetical."""
    real = cli.importlib.import_module

    def boom(name, *a, **k):
        if name == "armature_core.shotspec":
            raise ImportError("DLL load failed while importing extension", name="nope")
        return real(name, *a, **k)

    monkeypatch.setattr(cli.importlib, "import_module", boom)
    assert cli.main(["check"]) == 1
    text = capsys.readouterr().out
    assert "ImportError: DLL load failed while importing extension" in text
    assert "(no module named 'nope')" in text


# --- F-9407b553: every carried gate id is named on the surface ------------------

def _gate_ids(description):
    """Same two forms `tests/test_cli.py` parses — kept local so this file stands alone."""
    ids = []
    listed = re.search(r"gates?:\s*([A-Z0-9_,/ ]+)", description)
    if listed:
        ids += re.findall(r"[A-Z][A-Z0-9_]*|G\d", listed.group(1))
    for named in re.findall(r"\bGate ([A-Z][A-Z0-9_]*(?:/[A-Z][A-Z0-9_]*)*)", description):
        ids += named.split("/")
    return sorted(set(ids))


def test_modules_json_carries_a_gates_list_per_row(capsys):
    rows = json.loads(_run(["modules", "--json"], capsys))
    assert {"module", "purpose", "gates"} == set(rows[0])
    by_name = {r["module"]: r for r in rows}
    assert by_name["route_gates"]["gates"] == ["PAIR", "ROUTE"]
    assert by_name["canon"]["gates"] == ["CANON"]
    assert by_name["rig_gates"]["gates"] == ["D", "N", "P"]
    assert by_name["blender_scene"]["gates"] == ["COMPOSITOR", "FRAME"]
    assert "ASSEMBLY" in by_name["assembly"]["gates"]
    assert "CASCADE" in by_name["assembly"]["gates"]


def test_every_gate_a_surface_module_carries_is_named_in_a_surface_row():
    """The closing direction of F-7f9ab627. Measured 2026-09-06: 19 of 32 package gate
    ids (CANON, N, P, D, TURN, …) appeared in no SURFACE row, so a halt's `"gate"`
    field could not be turned back into a module from the installed package."""
    named = set()
    for _, description in cli.SURFACE:
        named |= set(_gate_ids(description))
    carried = set()
    for name, _ in cli.SURFACE:
        carried |= set(cli._gates_carried(name))
    missing = sorted(carried - named)
    assert missing == [], (
        f"SURFACE names no row for gate id(s) {missing}; a halt carrying one of these "
        f"cannot be mapped back to a module from the installed package")


def test_gates_carried_matches_what_an_import_exposes():
    """`_gates_carried` is the mechanical census `--json` ships; it must agree with the
    GateFailure subclasses reachable from each importable SURFACE module."""
    for name, _ in cli.SURFACE:
        if name == "blender_scene":
            continue
        mod = __import__(f"armature_core.{name}", fromlist=["*"])
        expected = sorted({
            getattr(obj, "gate")
            for obj in vars(mod).values()
            if isinstance(obj, type)
            and issubclass(obj, GateFailure)
            and obj is not GateFailure
            and getattr(obj, "gate", None)
            and getattr(obj, "gate") != "G?"
        })
        assert cli._gates_carried(name) == expected, name


def _run(argv, capsys):
    cli.main(argv)
    return capsys.readouterr().out
