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


def declared_clauses(mod):
    """Every `clause` value `require_reference_file` can raise, read off its own source.

    The POPULATION, so "which clauses have behavioural coverage" is a comparison rather
    than a memory. Two today: `reference_not_a_file` and `reference_unreadable`.
    """
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(mod.require_reference_file))
    out = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call)):
            continue
        for arg in node.exc.args:
            if not isinstance(arg, ast.Dict):
                continue
            for key, value in zip(arg.keys, arg.values):
                if (isinstance(key, ast.Constant) and key.value == "clause"
                        and isinstance(value, ast.Constant)):
                    out.add(value.value)
    return out


def test_a_directory_named_as_the_reference_takes_the_FIRST_clause(tmp_path):
    """What the wave-14 probe actually drove, named for the clause it actually reaches.

    WAVE 16, F-c060f729. This test was called
    `test_an_unreadable_reference_is_refused_with_its_own_clause`, its own comment said "a
    directory IS a path and is not a file: the first clause fires; make the second
    reachable by a file that exists but cannot be opened", and then it never built that
    path — it passed the directory and asserted `reference_not_a_file`, the same value as
    its sibling. Measured by grep over `tests/`: `reference_unreadable` occurred zero times
    in any test source. The `if os.name != "nt": skip` above it therefore gated a probe
    that exercised nothing the unguarded sibling did not, and since every job in
    `.github/workflows/` is `runs-on: ubuntu-latest`, in CI it ran zero probes.

    The directory case is a real distinction worth keeping — it is the shape a seat reaches
    for when trying to make a file unreadable — so it stays, under the clause it fires, and
    the second clause is driven for real below. No skip: a directory is a directory on
    every platform.
    """
    mod = load_tool("make_rig_sheet.py")
    d = tmp_path / "a_dir.glb"
    d.mkdir()
    err = _refusal(mod, str(d))
    assert err.evidence["clause"] == "reference_not_a_file", err.evidence


def test_an_unreadable_reference_is_refused_with_its_own_clause(tmp_path, monkeypatch):
    """The SECOND clause, driven — the half of this receipt nothing in the suite read.

    The file exists (so the first clause cannot fire) and `open()` raises. The failure is
    injected at `open` rather than through a permission bit because the permission bit is
    the part that is not portable: `os.chmod(path, 0)` is honoured on POSIX and ignored for
    read access on Windows, and an ACL fixture needs a system tool. What is being read back
    is the tool's OSError arm — that it names its own clause, carries the `error` key, and
    chains the cause — and that arm is identical on every platform. The OS-level version
    runs beside it below, where the platform provides one.
    """
    mod = load_tool("make_rig_sheet.py")
    real = tmp_path / "real.glb"
    real.write_bytes(b"glTF\x02\x00\x00\x00")
    assert os.path.isfile(real), "the first clause must not be the one that fires"

    def refuse_to_open(*args, **kwargs):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(mod, "open", refuse_to_open, raising=False)
    err = _refusal(mod, str(real))
    ev = err.evidence
    assert ev["clause"] == "reference_unreadable", ev
    assert ev["error"] == "PermissionError", ev
    assert ev["gate"] is None and ev["andon"] == "ReferenceFileError", ev
    assert ev["path"] == str(real)
    assert isinstance(err.__cause__, OSError), err.__cause__


@pytest.mark.skipif(os.name == "nt",
                    reason="`os.chmod(path, 0)` removes the read bit on POSIX; on Windows "
                           "it sets the read-only attribute and leaves READ permitted, so "
                           "the file still opens and the clause under test never fires. "
                           "The platform-independent injection above covers the same arm.")
def test_the_unreadable_clause_also_fires_on_a_real_permission_bit(tmp_path):
    """The OS-level shape, where the OS provides one. Every CI job is `ubuntu-latest`."""
    mod = load_tool("make_rig_sheet.py")
    real = tmp_path / "real.glb"
    real.write_bytes(b"glTF\x02\x00\x00\x00")
    os.chmod(real, 0)
    try:
        with open(real, "rb"):
            pytest.skip("this process can read a mode-0 file (running as root?); the "
                        "permission bit is not the operand here")
    except OSError:
        pass
    try:
        err = _refusal(mod, str(real))
        assert err.evidence["clause"] == "reference_unreadable", err.evidence
        assert err.evidence["error"] in ("PermissionError", "OSError"), err.evidence
    finally:
        os.chmod(real, 0o600)


def test_every_clause_require_reference_file_can_raise_is_driven_by_a_probe(tmp_path,
                                                                            monkeypatch):
    """The POPULATION (wave-16 rule 1): observed clauses == declared clauses.

    Not "the two tests above exist" but "every clause the function's own source can raise
    was produced by driving the function". A third clause added to that function joins this
    comparison on the day it lands, rather than being covered by an AST shape check that
    cannot tell one clause from another.
    """
    mod = load_tool("make_rig_sheet.py")
    declared = declared_clauses(mod)
    assert declared == {"reference_not_a_file", "reference_unreadable"}, declared

    observed = set()
    observed.add(_refusal(mod, str(tmp_path / "no_such.glb")).evidence["clause"])

    real = tmp_path / "real.glb"
    real.write_bytes(b"glTF\x02\x00\x00\x00")

    def refuse_to_open(*args, **kwargs):
        raise OSError(5, "Input/output error")

    monkeypatch.setattr(mod, "open", refuse_to_open, raising=False)
    observed.add(_refusal(mod, str(real)).evidence["clause"])

    assert observed == declared, {
        "declared and never driven": sorted(declared - observed),
        "driven and not declared": sorted(observed - declared)}


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
