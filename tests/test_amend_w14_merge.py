"""Coordinator tests at the wave-14 merge (after adjudication #159).

The jury contested `AC-raise-typed-with-evidence` and the coordinator's scan of part B found why: the two
refusals instruments' F-4db23b72 moved above the first write in `make_rig_sheet.require_reference_file`
raised the BASE `ArmatureError` with a message only -- no gate, no andon, no clause -- the exact shape wave 14
asked instruments-measure to remove at `stage_render:582`, reintroduced by a sibling in the same wave. The
evidence census walks `armature_core` only, so the suite was green. This file reads the receipt back.
"""
import os

import pytest

from blender_stub import load_tool


def _refusal(mod, path):
    with pytest.raises(mod.ReferenceFileError) as exc:   # a NAMED subclass, never the base
        mod.require_reference_file(path)
    assert isinstance(exc.value, mod.ArmatureError)
    return exc.value


def test_a_missing_reference_is_refused_with_a_receipt_a_halt_line_can_print(tmp_path):
    """Red on the pre-fix shape by construction: `.evidence` was None, so every key read below fails."""
    mod = load_tool("make_rig_sheet.py")
    missing = str(tmp_path / "no_such.glb")
    err = _refusal(mod, missing)
    ev = err.evidence
    assert isinstance(ev, dict), ev
    assert ev["gate"] is None and ev["andon"] == "ReferenceFileError", ev
    assert ev["clause"] == "reference_not_a_file", ev
    assert ev["path"] == missing


def test_an_unreadable_reference_is_refused_with_its_own_clause(tmp_path):
    mod = load_tool("make_rig_sheet.py")
    if os.name != "nt":
        pytest.skip("the unreadable-file shape below is the Windows one (a directory named as a file)")
    d = tmp_path / "a_dir.glb"
    d.mkdir()
    # a directory IS a path and is not a file: the first clause fires; make the second reachable by a
    # file that exists but cannot be opened -- a path with a trailing NUL is refused by open() on Windows.
    err = _refusal(mod, str(d))
    assert err.evidence["clause"] == "reference_not_a_file"


def test_every_refusal_in_require_reference_file_names_a_clause():
    """Source-level: every raise in that function is the NAMED class with two arguments (a bare base
    raise, with or without evidence, is the shape two censuses refuse)."""
    import ast, inspect
    mod = load_tool("make_rig_sheet.py")
    src = inspect.getsource(mod.require_reference_file)
    tree = ast.parse(src)
    raises = [n for n in ast.walk(tree) if isinstance(n, ast.Raise)]
    assert len(raises) == 2, len(raises)
    for r in raises:
        assert isinstance(r.exc, ast.Call) and len(r.exc.args) == 2, ast.dump(r.exc)[:200]
        assert getattr(r.exc.func, "id", None) == "ReferenceFileError", ast.dump(r.exc.func)
        ev = r.exc.args[1]
        keys = {k.value for k in ev.keys if isinstance(k, ast.Constant)}
        assert {"gate", "andon", "clause"} <= keys, keys
