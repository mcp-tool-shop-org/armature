"""Wave 28 (Stage C amend #1) — the core-solvers domain's nine findings.

Every test here drives the real predicate and states the RED direction it was shown
against, per the wave-18 rule and `F-ab2c1d14`'s: a red proof that re-implements the thing
it is checking proves nothing about the thing.

The nine, by canonical id:

  F-0a27b25c  the halt line's escaping — un-crashable on any stdout encoding
  F-2df6fd1b  `traceback.print_exc()` only for a crash
  F-48f0c3d4  the halt contract's code half (`run_tool_main`'s docstring is the spec)
  F-98b9b966  `channels.*` refusals take an `extra` mapping naming the frame and the file
  F-af6b12ed  `clipstats`' public readers declare their scale and what they measure
  F-f7449bc9  the clause-less named-andon receipts
  F-5f8714c8  THE ALPHA LAW's two "not explained" refusals name their flag
  F-9dbfdf8f  the refusals whose evidence knew the number their sentence did not
  F-08eaf630  every `PngWriteError` names the file it refused
"""

import ast
import importlib
import io
import json
import os
import subprocess
import sys
import types

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "tools"))

from armature_core import (assembly, channels, clipstats, framing,  # noqa: E402
                           glb, lift_solve, parts, pngio, resample, sitelist,
                           startframe, turnaround, walk)
from armature_core.errors import ArmatureError, GateFailure  # noqa: E402


@pytest.fixture()
def BS():
    """`blender_scene` imported under `blender_stub.blender_stubbed`, then unimported.

    ADOPT THE HOME, and the census says so. A hand-rolled `sys.modules` stub here JOINS
    `tests/test_packaging.sys_modules_writers` — the derived installer population — which
    is the trap wave 26 recorded and which this fixture hit on its first draft: the census
    went red naming `(test_amend_w28_core_solvers.py, BS)` as an installer nobody had
    declared. `blender_stubbed` is the one implementation, and its teardown is the
    load-bearing half (`tests/test_cli.py` asserts `import bpy` FAILS, so a stub or a
    stub-bound module left behind turns a real row green for the wrong reason — it pops the
    registry entry AND the package attribute, both of which wave 6 paid for).
    """
    import blender_stub

    with blender_stub.blender_stubbed():
        # A `pop` and no restore, deliberately: `sys.modules[...] = cached` would make this
        # fixture a stub INSTALLER by `test_packaging._writes_into_sys_modules`'s own
        # predicate (four shapes; removals are explicitly not counted), and the census
        # `test_every_derived_installer_is_driven_by_a_pair_that_runs_it_before_a_reader`
        # then requires an `ORDER_DEPENDENT_PAIRS` entry for it. There is nothing to
        # restore: `blender_stubbed`'s own teardown pops every `armature_core.*` module
        # imported under it, registry entry and package attribute both, which is the whole
        # reason to use it rather than a local stub.
        sys.modules.pop("armature_core.blender_scene", None)
        yield importlib.import_module("armature_core.blender_scene")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE = os.path.join(REPO, "tools", "armature_core")
OWNED = ("aapose.py", "assembly.py", "binding.py", "blender_scene.py", "channels.py",
         "clipcompare.py", "clipstats.py", "framing.py", "glb.py", "joints.py",
         "landmarks.py", "lift_solve.py", "openpose.py", "parts.py", "pngio.py",
         "posearc.py", "resample.py", "sitelist.py", "startframe.py", "turnaround.py",
         "walk.py")


def _tree(name):
    with open(os.path.join(CORE, name), encoding="utf-8") as fh:
        return ast.parse(fh.read())


# ===================================================================== F-0a27b25c
#
# THE HALT LINE'S ESCAPING. `run_tool_main` dumped its record at `ensure_ascii`'s default
# True, so the one field on a halt that is prose rather than an identifier arrived with
# backslash-u escapes in the middle of it — measured on all three outcomes, on every one
# of the 50 CPython tools that adopted the handler.
#
# `ensure_ascii=False` ALONE is not the fix and would be the worse defect: the `print`
# sits in the handler's `finally`, so a `UnicodeEncodeError` raised there propagates out
# of the whole `try` statement and DELETES `sys.exit` — `blender -b -P` then reports exit
# 0 on a fired andon. Both halves are driven below, and the encoding half is driven in a
# CHILD PROCESS because a stdout encoding is a property of a real stream.

#: One message carrying the three characters this tree's refusals actually use: an em
#: dash (45 sites in this package), a degree sign (`posearc`'s arc readout) and `≤`.
#: F-0d3138c9 (wave 32): `halt_ascii_standins` rewrites `≤` to `<=` before the dump, so
#: the halt RECORD carries the stand-in; the raw raise message still has the glyph.
NON_ASCII_MESSAGE = "the void \u2014 45.0\u00b0, span 12 \u2264 16"
HALT_MESSAGE_AFTER_STANDINS = "the void \u2014 45.0\u00b0, span 12 <= 16"

#: `(kind, expected exit code)` for the three outcomes `halt_outcome` discriminates. The
#: outcome SENTENCES are read from `parts.halt_outcome` itself rather than pasted, so this
#: census cannot drift from the implementation it drives.
HALT_KINDS = (("gate", 2), ("refusal", 2), ("crash", 1))

_PROBE = '''\
import sys
sys.path.insert(0, {tools!r})
from armature_core.errors import ArmatureError, GateFailure
from armature_core.parts import run_tool_main

MESSAGE = {message!r}


class _Gate(GateFailure):
    gate = "PROBE"


def main():
    kind = sys.argv[-1]
    if kind == "gate":
        raise _Gate(MESSAGE, {{"clause": "probe_clause", "note": MESSAGE}})
    if kind == "refusal":
        raise ArmatureError(MESSAGE)
    raise KeyError(MESSAGE)


if __name__ == "__main__":
    run_tool_main(main, "PROBE_TOOL")
'''


def _run_probe(tmp_path, kind, io_encoding):
    """Run the probe tool in a child process with `PYTHONIOENCODING` set, and decode it.

    Returns `(exit code, stdout, stderr)`. `io_encoding` is passed to the child verbatim,
    so `"cp1252:strict"` gives a stdout that genuinely cannot encode an em dash — the
    condition under which `ensure_ascii=False` alone deletes `sys.exit`.
    """
    script = tmp_path / "probe_tool.py"
    script.write_text(
        _PROBE.format(tools=os.path.join(REPO, "tools"), message=NON_ASCII_MESSAGE),
        encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = io_encoding
    env.pop("PYTHONWARNINGS", None)
    proc = subprocess.run([sys.executable, str(script), kind],
                          capture_output=True, env=env, timeout=120)
    codec = io_encoding.split(":")[0]
    return (proc.returncode,
            proc.stdout.decode(codec, "replace"),
            proc.stderr.decode(codec, "replace"))


def _halt_record(stdout):
    line = [ln for ln in stdout.splitlines() if ln.startswith("PROBE_TOOL_HALT ")]
    assert len(line) == 1, stdout
    return json.loads(line[0][len("PROBE_TOOL_HALT "):])


@pytest.mark.parametrize("kind,code", HALT_KINDS)
def test_the_halt_line_carries_its_prose_as_prose_on_a_utf8_stdout(tmp_path, kind, code):
    """RED on the base: `message` read `... \\u2014 45.0\\u00b0, span 12 \\u2264 16`.

    Driven on all three outcomes, because the defect was in the one `json.dumps` every
    outcome goes through — this is "the census that drives `run_tool_main`'s three
    outcomes" the wave's rule 3 asks for.
    """
    rc, out, _err = _run_probe(tmp_path, kind, "utf-8")
    rec = _halt_record(out)
    assert rc == code, (rc, out)
    # `in`, not `==`: a typed gate prefixes its own id and a `KeyError`'s `str` quotes its
    # argument. What is asserted is that the PROSE arrives as prose. Wave 32 stand-ins
    # rewrite `≤` -> `<=` in the record (F-0d3138c9); em dash and degree stay.
    assert HALT_MESSAGE_AFTER_STANDINS in rec["message"], rec["message"]
    assert "\\u" not in rec["message"], rec["message"]
    assert set(rec) == {"tool", "outcome", "gate", "error", "message", "evidence"}
    assert list(rec.keys()) == [
        "tool", "outcome", "gate", "evidence", "error", "message"]


@pytest.mark.parametrize("kind,code", HALT_KINDS)
def test_the_halt_line_still_exits_on_a_cp1252_stdout_that_cannot_encode_the_prose(
        tmp_path, kind, code):
    """The half that makes `ensure_ascii=False` safe rather than fatal.

    RED DIRECTION, MEASURED — not asserted. A scratch handler of exactly this shape
    (`ensure_ascii=False`, a BARE `print` in the `finally`, `sys.exit(2)` under it) was run
    as a child with `PYTHONIOENCODING=cp1252:strict` on the repo venv:

      reverted (ensure_ascii=False, bare print) -> rc **1**, stdout **b''**, stderr
          `UnicodeEncodeError: 'charmap' codec can't encode character '\\u2264' in
          position 55: character maps to <undefined>`
      base     (ensure_ascii=True,  bare print) -> rc 2, the line present, escaped

    So the reverted shape costs a REFUSAL both its halt line and its exit code — the exact
    failure `run_tool_main` exists to prevent, and worse than the escaping it would fix.
    Note WHICH character did it: cp1252 carries the em dash (0x97) and the degree sign
    (0xB0) and cannot carry `≤`, which is why the escaping decision has to be per
    character and per stream rather than global.

    With `printable_halt_line` in front of the print the line arrives — escaped for exactly
    the characters cp1252 cannot carry — and the exit code is unchanged, which is what this
    test drives on all three outcomes.
    """
    rc, out, _err = _run_probe(tmp_path, kind, "cp1252:strict")
    rec = _halt_record(out)
    assert rc == code, (rc, out)
    # The line still parses and still says what happened; only the characters cp1252
    # cannot carry are escaped.
    assert "45.0" in rec["message"] and "span 12" in rec["message"], rec["message"]
    assert rec["error"] in ("_Gate", "ArmatureError", "KeyError")


def test_printable_halt_line_returns_a_carrying_stream_its_line_unchanged():
    """The two directions of the helper, and the streams with no encoding at all.

    A check that cannot fail is not a check: the same string is put to a stream that can
    carry it and one that cannot, and the answers must differ.
    """
    line = "PROBE_HALT " + json.dumps({"m": NON_ASCII_MESSAGE}, ensure_ascii=False)

    class _Stream:
        def __init__(self, encoding, errors="strict"):
            self.encoding, self.errors = encoding, errors

    assert parts.printable_halt_line(line, _Stream("utf-8")) == line
    narrowed = parts.printable_halt_line(line, _Stream("cp1252"))
    # cp1252 CARRIES the em dash (0x97) and the degree sign; it cannot carry `≤`. So only
    # that one character is escaped, which is the whole point of deciding per stream
    # instead of globally: `ensure_ascii=True` escaped all three.
    assert narrowed != line
    assert "\\u2264" in narrowed and "—" in narrowed, narrowed
    narrowed.encode("cp1252")                       # the whole point: it now prints
    # A stream with no `encoding` attribute (io.StringIO, pytest's capture) carries any
    # str, so nothing is escaped.
    assert parts.printable_halt_line(line, io.StringIO()) == line
    assert parts.printable_halt_line(line, _Stream(None)) == line
    # A stream whose encoding is not a real codec must not take the helper down with it.
    assert isinstance(parts.printable_halt_line(line, _Stream("not-a-codec")), str)


def test_the_halt_lines_json_dump_asks_for_the_prose_it_prints():
    """The structural half, so a future edit cannot quietly restore the escaping.

    Read off the AST of `run_tool_main` rather than asserted as a source substring: the
    `json.dumps` that builds the RICH record (the one with `default=str`) must pass
    `ensure_ascii=False`, and the line it produces must reach `print` through
    `printable_halt_line`.
    """
    fn = [n for n in ast.walk(_tree("parts.py"))
          if isinstance(n, ast.FunctionDef) and n.name == "run_tool_main"][0]
    dumps = [n for n in ast.walk(fn)
             if isinstance(n, ast.Call)
             and getattr(n.func, "attr", None) == "dumps"
             and any(k.arg == "default" for k in n.keywords)]
    assert len(dumps) == 1, "the rich record is built by exactly one `json.dumps`"
    assert any(k.arg == "ensure_ascii" and k.value.value is False
               for k in dumps[0].keywords), ast.dump(dumps[0])
    prints = [n for n in ast.walk(fn)
              if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "print"]
    assert prints and all(
        any(isinstance(sub, ast.Call)
            and getattr(sub.func, "id", None) == "printable_halt_line"
            for sub in ast.walk(p)) for p in prints), (
        "every print in the handler renders its line for the stream first")


# ===================================================================== F-2df6fd1b
#
# A DELIBERATE REFUSAL AND A CRASH WERE THE SAME THING ON SCREEN, in the handler whose
# entire design is to tell them apart. `traceback.print_exc()` ran unconditionally for all
# three outcomes.


@pytest.mark.parametrize("kind,code", HALT_KINDS)
def test_only_the_crash_prints_a_traceback(tmp_path, kind, code):
    """RED on the base: all three printed a five-line stack rooted at `parts.py`.

    Driven end to end in a child process, on stderr, for each of the three outcomes — the
    same population the escaping fix is driven over, because the two findings share the
    handler.
    """
    rc, out, err = _run_probe(tmp_path, kind, "utf-8")
    assert rc == code, (rc, out, err)
    _halt_record(out)                                    # the record is unaffected
    if code == 1:
        assert "Traceback (most recent call last)" in err, err
    else:
        assert "Traceback" not in err, (
            "a deliberate refusal must not arrive as a stack rooted in repo internals; "
            "the halt record already carries error, message, gate and evidence")


def test_the_traceback_call_still_sits_inside_the_guarded_region():
    """The structural pin `tests/test_instruments_amend_w12.py` holds, re-derived here.

    The `if` that narrows `print_exc` to the crash must not move it out of the `try` whose
    `except` swallows a secondary failure — that guard is why a broken traceback cannot
    delete `sys.exit`.
    """
    fn = [n for n in ast.walk(_tree("parts.py"))
          if isinstance(n, ast.FunctionDef) and n.name == "run_tool_main"][0]
    tries = [n for n in ast.walk(fn) if isinstance(n, ast.Try)]
    guarded = [t for t in tries if any(
        isinstance(sub, ast.Call) and getattr(sub.func, "attr", None) == "dumps"
        for sub in ast.walk(t))]
    assert guarded, "the guarded region is the `try` that builds the rich record"
    assert any(isinstance(sub, ast.Call)
               and getattr(sub.func, "attr", None) == "print_exc"
               for t in guarded for sub in ast.walk(t))


# ===================================================================== F-48f0c3d4
#
# THE HALT CONTRACT'S CODE HALF. README §"Reading a halt" (the coordinator's, on
# `3380ae2`) ends "the one implementation of the CPython contract is
# `armature_core.parts.run_tool_main`; its docstring is the specification" — so the
# docstring has to actually BE one. Every element below is derived from the running code
# and then required of the prose, so the two cannot drift.


def test_run_tool_mains_docstring_states_the_whole_contract():
    doc = parts.run_tool_main.__doc__
    assert doc

    for key in ("tool", "outcome", "gate", "error", "message", "evidence"):
        assert f"``{key}``" in doc, f"the six keys are named; {key!r} is not"

    class _Gate(GateFailure):
        gate = "PROBE"

    for exc in (_Gate("x", {}), ArmatureError("x"), KeyError("x")):
        code, outcome = parts.halt_outcome(exc)
        assert outcome in doc, f"{outcome!r} is an outcome this handler can print"
        assert f"exit {code}" in doc, f"exit {code} is a code this handler can produce"
    assert "exit 0" in doc, "the success side of the table is stated too"
    assert "evidence.clause" in doc or "`evidence.clause`" in doc


# ===================================================================== F-98b9b966
#
# THE MODULE THAT AUTHORS EVERY CONTROL-SEQUENCE PIXEL refused without naming the frame or
# the file, and its only caller raises it inside an unadorned per-frame loop.

WHERE = {"frame": 12, "path": "out/depth/0012.png", "channel": "depth_perframe"}


def _channels_refusals(extra):
    """Every raising path in `channels`, driven; `[(clause, exc)]`."""
    nan = np.array([[float("nan")]])
    mask = np.array([[1]])
    normals = np.array([[[float("nan"), 0.0, 0.0]]])
    zeros = np.array([[[0.0, 0.0, 0.0]]])
    out = []
    for call in (
            lambda: channels.depth_extent(nan, mask, extra=extra),
            lambda: channels.normalize_depth(np.array([[1.0]]), mask,
                                             float("nan"), 1.0, extra=extra),
            lambda: channels.normalize_depth(nan, mask, 0.0, 1.0, extra=extra),
            lambda: channels.encode_u8(nan, extra=extra),
            lambda: channels.require_readable_normals(normals, mask, "probe", extra=extra),
            lambda: channels.require_readable_normals(zeros, mask, "probe", extra=extra),
            lambda: channels.derive_edge(np.array([[1.0]]), zeros, mask, 0.1, 400.0,
                                         extra=extra)):
        with pytest.raises(ArmatureError) as exc:
            call()
        out.append((exc.value.evidence["clause"], exc.value))
    return out


def test_every_channels_refusal_carries_the_callers_frame_and_file():
    """All seven, with `extra` supplied: the keys are in the receipt AND in the sentence.

    RED on the base: `extra` did not exist, and the seven evidence dicts held pixel counts
    only — no frame index, no path, no channel tag, no view — while
    `stage_render.run_export` calls them from inside its per-frame loop, whose own gate
    evidence already spells `"frame": i`.
    """
    seen = _channels_refusals(WHERE)
    assert len(seen) == 7, [c for c, _ in seen]
    for clause, exc in seen:
        for key, value in WHERE.items():
            assert exc.evidence.get(key) == value, (clause, exc.evidence)
        assert f"frame={WHERE['frame']}" in str(exc), (clause, str(exc)[:120])
        assert WHERE["path"] in str(exc), (clause, str(exc)[:120])


def test_a_channels_refusal_without_the_mapping_still_refuses_and_invents_nothing():
    """The other direction: a caller that sends no `extra` is byte-identical to before.

    A check that cannot fail is not a check — if the parameter were required, or if it
    manufactured keys when absent, this is where that shows.
    """
    for clause, exc in _channels_refusals(None):
        assert clause
        for key in WHERE:
            assert key not in exc.evidence or key == "path", (clause, exc.evidence)
        assert not str(exc).startswith("["), (clause, str(exc)[:80])


def test_the_callers_key_overwrites_the_evidences_own():
    """The rule posted to the relay: the caller's location is the more specific fact."""
    with pytest.raises(ArmatureError) as exc:
        channels.encode_u8(np.array([[float("nan")]]), where="encode_u8",
                           extra={"where": "stage_render.run_export"})
    assert exc.value.evidence["where"] == "stage_render.run_export"


def test_every_raising_function_in_channels_takes_the_mapping():
    """Derived from the module, never a pasted list: a raising function added later
    without the parameter is a failure here rather than a silent gap."""
    tree = _tree("channels.py")
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        if fn.name.startswith("_"):
            continue
        raises = [n for n in ast.walk(fn) if isinstance(n, ast.Raise)]
        if not raises:
            continue
        args = [a.arg for a in fn.args.args] + [a.arg for a in fn.args.kwonlyargs]
        assert "extra" in args, f"{fn.name} raises and does not take `extra`"


# ===================================================================== F-af6b12ed
#
# THE NUMBERS THIS MODULE REPORTS CARRY NO SCALE, and the docstring that quotes banked
# numbers invites exactly the comparison the missing scale breaks.


def _six_frames(dtype):
    rng = np.arange(6 * 16 * 16 * 3, dtype=np.float64).reshape(6, 16, 16, 3) % 256
    if dtype == "uint8":
        return [f.astype(np.uint8) for f in rng]
    return [(f / 255.0).astype(np.float64) for f in rng]


@pytest.mark.parametrize("reader", ("frame_deltas", "luma_series", "distinct_frames"))
def test_the_same_clip_at_two_scales_declares_two_scales(reader):
    """RED on the base: the two records were key-for-key identical in shape and the
    numbers differed by 255x with nothing in either record naming the difference."""
    as_bytes = getattr(clipstats, reader)(_six_frames("uint8"))
    as_unit = getattr(clipstats, reader)(_six_frames("float"))
    assert as_bytes["scale"] != as_unit["scale"], as_bytes["scale"]
    assert as_bytes["scale"]["input_dtype"] == "uint8"
    assert as_unit["scale"]["input_dtype"] == "float64"
    assert as_bytes["scale"]["observed_max"] > as_unit["scale"]["observed_max"]
    assert as_bytes["measures"] and as_unit["measures"]


def test_every_public_reader_in_clipstats_declares_what_it_measured():
    """The population, derived: `similarity_to_first` already carried a `measures`
    sentence and the other four carried none."""
    frames = _six_frames("uint8")
    records = {"frame_deltas": clipstats.frame_deltas(frames),
               "luma_series": clipstats.luma_series(frames),
               "distinct_frames": clipstats.distinct_frames(frames),
               "similarity_to_first": clipstats.similarity_to_first(frames),
               "horizon_row": clipstats.horizon_row(frames[0])}
    for name, rec in records.items():
        assert rec.get("measures"), f"{name} does not say what it measured"
    for name in ("frame_deltas", "luma_series", "distinct_frames", "horizon_row"):
        assert records[name].get("scale"), f"{name} does not declare its scale"


def test_the_scale_is_facts_and_nothing_is_rescaled():
    """The numbers the reports already banked must not move, and a NaN must not reach a
    record as the bare non-JSON token `NaN`."""
    frames = _six_frames("uint8")
    before = clipstats.frame_deltas(frames)["stats"]["median"]
    assert clipstats.frame_deltas(frames)["stats"]["median"] == before
    assert clipstats.scale_of([]) == {"input_dtype": None, "observed_min": None,
                                      "observed_max": None, "n_frames": 0}
    scale = clipstats.scale_of([np.full((2, 2, 3), float("nan"))])
    assert scale["observed_min"] is None and scale["observed_max"] is None
    json.dumps(scale, allow_nan=False)


# ===================================================================== F-f7449bc9
#
# NAMED-ANDON REFUSALS THAT COULD NOT SAY WHICH CLAUSE FIRED. Measured on `3380ae2` by the
# walk below: 28 raises in 12 functions passed a shared `ev` built without a `clause` key,
# among them THE ALPHA LAW's two gates. (The finding's own count was 33; the extra five
# are `resample.endpoints_match`'s, which DO name a clause — through `dict(ev,
# clause=...)`, the spelling wave 26 recorded as invisible to `clause_literals`. Measured
# and corrected here rather than carried.)


def _clauseless_evidence_raises():
    """Every raise in the 21 owned modules passing an evidence mapping, in a function no
    raise of which names a clause. THE PREDICATE, not a re-implementation of the fix."""
    def names_a_clause(fn):
        for n in ast.walk(fn):
            if isinstance(n, ast.Dict) and any(
                    isinstance(k, ast.Constant) and k.value == "clause" for k in n.keys):
                return True
            if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant) \
                    and n.slice.value == "clause":
                return True
            if isinstance(n, ast.keyword) and n.arg == "clause":
                return True
        return False

    out = []
    for name in OWNED:
        tree = _tree(name)
        fns = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        for fn in fns:
            hits = []
            for node in ast.walk(fn):
                if not isinstance(node, ast.Raise) or not isinstance(node.exc, ast.Call):
                    continue
                owner = None
                for cand in fns:
                    if cand.lineno <= node.lineno <= (cand.end_lineno or cand.lineno):
                        if owner is None or cand.lineno > owner.lineno:
                            owner = cand
                if owner is not fn:
                    continue
                rest = list(node.exc.args[1:]) + [k.value for k in node.exc.keywords]
                if any(isinstance(a, (ast.Dict, ast.Name)) for a in rest):
                    hits.append(node.lineno)
            if hits and not names_a_clause(fn):
                out.append((name, fn.name, tuple(sorted(hits))))
    return sorted(out)


def test_no_named_andon_in_this_package_writes_a_receipt_without_a_clause():
    """The mechanical form that stops the population growing back.

    RED on the base, measured: 28 raises across `startframe.gate_alpha` (3),
    `startframe.gate_backdrop` (4), `turnaround.gate_view_crop` (2),
    `turnaround.gate_view_alpha` (2), `glb.gate_atlas_untouched` (1),
    `glb.compare_signatures` (3), `lift_solve.gate_round_trip` (2),
    `parts.gate_parts_accounting` (2), `parts.require_finite` (1),
    `parts.gate_rigid_arrival` (2), `parts.gate_parts_determinism` (4) and
    `resample.monotonic` (2).
    """
    assert _clauseless_evidence_raises() == []


def test_the_clause_walk_can_fail(tmp_path, monkeypatch):
    """A check that cannot fail is not a check: the walk is shown a function of exactly
    the shape it exists to find and must report it."""
    probe = tmp_path / "probe_mod.py"
    probe.write_text(
        "def gate_probe(x):\n"
        "    ev = {'gate': 'PROBE', 'andon': 'ProbeGate'}\n"
        "    if x:\n"
        "        raise ValueError('no', ev)\n"
        "    return ev\n", encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "CORE", str(tmp_path))
    monkeypatch.setattr(sys.modules[__name__], "OWNED", ("probe_mod.py",))
    assert _clauseless_evidence_raises() == [("probe_mod.py", "gate_probe", (4,))]


def test_gate_alphas_three_refusals_write_three_different_receipts():
    """The behaviour behind the walk, on THE ALPHA LAW's own gate.

    RED on the base, measured by calling it three ways: each raised `AlphaGate` with gate
    `ALPHA` and the IDENTICAL evidence key set and no `clause` — three different failures,
    one receipt shape, distinguishable only by regex over 200 characters of prose.
    """
    clauses = []
    for kwargs in ({"transparent_fraction": 0.5, "why": None},
                   {"transparent_fraction": 0.0, "why": "a reason"},
                   {"transparent_fraction": 1.0, "why": "a reason"}):
        with pytest.raises(startframe.AlphaGate) as exc:
            startframe.gate_alpha(kwargs["transparent_fraction"], (0.1, 0.1, 0.1),
                                  kwargs["why"])
        assert exc.value.gate == "ALPHA"
        clauses.append(exc.value.evidence["clause"])
    assert len(set(clauses)) == 3, clauses


def test_gate_backdrops_four_refusals_write_four_different_receipts():
    calls = (
        dict(void_vs_plate_255=0.0, plate_vs_flat_255=9.0, transparent_fraction=0.5,
             why=None),
        dict(void_vs_plate_255=0.0, plate_vs_flat_255=9.0, transparent_fraction=0.0,
             why="a reason"),
        dict(void_vs_plate_255=0.0, plate_vs_flat_255=0.1, transparent_fraction=0.5,
             why="a reason"),
        dict(void_vs_plate_255=99.0, plate_vs_flat_255=9.0, transparent_fraction=0.5,
             why="a reason"),
    )
    clauses = []
    for kwargs in calls:
        with pytest.raises(startframe.BackdropGate) as exc:
            startframe.gate_backdrop(tol_255=1.0, min_separation_255=5.0, **kwargs)
        clauses.append(exc.value.evidence["clause"])
    assert len(set(clauses)) == 4, clauses


def _rigid(name, transform=0.0, pair=0.0, disp=1.0):
    return {"name": name, "max_transform_error": transform,
            "max_pair_distance_change": pair, "max_displacement": disp}


def _part(n_verts=1, n_faces=1, positions=((0.0, 0.0, 0.0),)):
    return {"n_verts": n_verts, "n_faces": n_faces, "positions": [list(p) for p in positions]}


def _image(sha, storage="buffer", name="atlas.png"):
    return {"index": 0, "sha256": sha, "storage": storage, "name": name}


#: EVERY clause word this commit adds, with the call that fires it. Spelled out rather
#: than counted, for two reasons: `tests/test_refusal_clauses.py` holds every clause word
#: to a fixture that NAMES it (`CLAUSES_NAMED_BY_NO_FIXTURE` is the dated exception list
#: and may not grow), and a word asserted only through `len(set(...)) == n` is a word no
#: test would notice being respelled — which is the defect this whole finding is about.
NEW_CLAUSE_WORDS = [
    # startframe — THE ALPHA LAW's two gates
    ("composite_reason_not_given",
     lambda: startframe.gate_alpha(0.5, (0.1, 0.1, 0.1), None)),
    ("master_carries_no_transparent_pixel",
     lambda: startframe.gate_alpha(0.0, (0.1, 0.1, 0.1), "why")),
    ("master_entirely_transparent",
     lambda: startframe.gate_alpha(1.0, (0.1, 0.1, 0.1), "why")),
    ("plate_reason_not_given",
     lambda: startframe.gate_backdrop(0.0, 9.0, 0.5, None, 1.0, 5.0)),
    ("master_carries_no_transparent_region_for_a_plate",
     lambda: startframe.gate_backdrop(0.0, 9.0, 0.0, "why", 1.0, 5.0)),
    ("plate_indistinguishable_from_the_flat_fallback",
     lambda: startframe.gate_backdrop(0.0, 0.1, 0.5, "why", 1.0, 5.0)),
    ("submitted_composite_is_not_the_plate",
     lambda: startframe.gate_backdrop(99.0, 9.0, 0.5, "why", 1.0, 5.0)),
    # turnaround — the same two laws, per view
    ("view_has_no_subject_pixels",
     lambda: turnaround.gate_view_crop(0, None, 64, 64)),
    ("subject_reaches_the_frame_border",
     lambda: turnaround.gate_view_crop(0, (0, 0, 10, 10), 64, 64)),
    ("view_carries_no_transparent_pixel",
     lambda: turnaround.gate_view_alpha(0, 255, 255, 0.0)),
    ("view_carries_no_opaque_pixel",
     lambda: turnaround.gate_view_alpha(0, 0, 1, 1.0)),
    # parts — Gate PARTS, Gate RIGID, Gate D, and the shared finiteness home
    ("nothing_to_partition",
     lambda: parts.gate_parts_accounting(np.array([]), 0, [])),
    ("assignment_count_is_not_the_face_count",
     lambda: parts.gate_parts_accounting(np.array([0]), 2, ["a"])),
    ("face_assigned_to_nothing",
     lambda: parts.gate_parts_accounting(np.array([-1, 0]), 2, ["a"])),
    ("face_assigned_outside_the_registered_list",
     lambda: parts.gate_parts_accounting(np.array([0, 5]), 2, ["a"])),
    # Never the FIRST clause: a label outside the registered list is what makes the
    # assigned total disagree, so this one always rides `clauses` behind that one.
    ("assigned_total_is_not_the_face_count",
     lambda: parts.gate_parts_accounting(np.array([0, 5]), 2, ["a"])),
    ("registered_part_with_no_faces",
     lambda: parts.gate_parts_accounting(np.array([0, 0]), 2, ["a", "b"])),
    ("no_parts_observed", lambda: parts.gate_rigid_arrival([], 1.0)),
    ("part_did_not_land_on_its_bone_transform",
     lambda: parts.gate_rigid_arrival([_rigid("a", transform=1.0)], 1.0)),
    ("part_deformed_under_the_pose",
     lambda: parts.gate_rigid_arrival([_rigid("a", pair=1.0)], 1.0)),
    ("the_figure_did_not_move_at_all",
     lambda: parts.gate_rigid_arrival([_rigid("a", disp=0.0)], 1.0)),
    ("one_build_carries_no_parts", lambda: parts.gate_parts_determinism({}, {}, 1.0)),
    ("the_two_builds_share_no_part_name",
     lambda: parts.gate_parts_determinism({"a": _part()}, {"b": _part()}, 1.0)),
    ("part_with_no_geometry_to_compare",
     lambda: parts.gate_parts_determinism({"a": _part(positions=())},
                                          {"a": _part(positions=())}, 1.0)),
    ("part_sets_differ",
     lambda: parts.gate_parts_determinism({"a": _part(), "x": _part()},
                                          {"a": _part()}, 1.0)),
    ("part_topology_differs_between_builds",
     lambda: parts.gate_parts_determinism({"a": _part(n_verts=1)},
                                          {"a": _part(n_verts=2)}, 1.0)),
    ("part_vertices_differ_between_builds",
     lambda: parts.gate_parts_determinism(
         {"a": _part(positions=((0.0, 0.0, 0.0),))},
         {"a": _part(positions=((9.0, 0.0, 0.0),))}, 1.0)),
    ("value_not_finite",
     lambda: parts.require_finite("x", float("nan"), ArmatureError,
                                  {"gate": "P", "andon": "A"})),
    ("round_trip_residual_over_tolerance", None),
    # glb — Gate ATLAS and the relift comparison
    ("one_clip_carries_no_frames", lambda: glb.compare_signatures([], [])),
    ("frame_counts_differ", lambda: glb.compare_signatures([1], [1, 2])),
    ("resolved_lift_diverges_from_the_pinned_glb",
     lambda: glb.compare_signatures([1, 2], [1, 3])),
    # resample — the timeline
    ("timeline_not_strictly_increasing", None),
    ("timeline_does_not_span_the_source", None),
    ("round_trip_population_incomplete", None),
    ("embedded_image_count_differs", None),
    ("source_carries_no_embedded_image", None),
    ("source_image_cannot_be_hashed", None),
    ("source_image_not_byte_identical_in_the_export", None),
]


@pytest.mark.parametrize("clause,call",
                         [(c, f) for c, f in NEW_CLAUSE_WORDS if f is not None],
                         ids=[c for c, f in NEW_CLAUSE_WORDS if f is not None])
def test_each_new_clause_word_is_the_one_its_own_refusal_writes(clause, call):
    """One word, one condition, driven — never `len(set(...)) == n`.

    RED on the base: every one of these raises passed a shared `ev` with no `clause` key
    at all, so `exc.value.evidence["clause"]` was a `KeyError` at all 28 sites.

    On a gate that COLLECTS (the `assembly.gate_batch_topology` shape) `clause` is the
    FIRST problem and the rest ride `clauses`, so a word that cannot be reached first —
    `assigned_total_is_not_the_face_count` is always preceded by the count clause — is
    asserted against the list. That is the shape's own contract, not a weakening.
    """
    with pytest.raises(ArmatureError) as exc:
        call()
    ev = exc.value.evidence
    assert clause == ev["clause"] or clause in ev.get("clauses", []), (
        clause, ev.get("clause"), ev.get("clauses"))


@pytest.mark.parametrize("clause,complete,worst", [
    ("round_trip_population_incomplete", False, 0.0),
    ("round_trip_residual_over_tolerance", True, 99.0),
])
def test_gate_round_trip_names_both_of_its_clauses(monkeypatch, clause, complete, worst):
    """Gate SOLVE's two refusals shared one `ev` with no clause, so an incomplete
    population and an inexact inversion wrote the same receipt shape. Driven against a
    substituted report, so both branches are reachable without a rig."""
    monkeypatch.setattr(lift_solve, "round_trip_report",
                        lambda *a, **k: {"population_complete": complete, "n_sites": 1,
                                         "n_sites_expected": 2,
                                         "sites_not_placed_by_fk": ["x"],
                                         "sites_not_observed": [],
                                         "per_site": {"s": 0.0},
                                         "worst": {"d": worst, "site": "s"},
                                         "tolerance": 1.0})
    with pytest.raises(lift_solve.SolveGate) as exc:
        lift_solve.gate_round_trip({}, {}, {}, 1.0)
    assert exc.value.evidence["clause"] == clause


@pytest.mark.parametrize("clause,before,after", [
    ("embedded_image_count_differs", [_image("aa")], []),
    ("source_carries_no_embedded_image", [_image(None)], [_image(None)]),
    ("source_image_cannot_be_hashed", [_image("aa"), _image(None)],
     [_image("aa"), _image(None)]),
    ("source_image_not_byte_identical_in_the_export", [_image("aa")], [_image("bb")]),
])
def test_gate_atlas_names_each_of_its_four_clauses(monkeypatch, clause, before, after):
    """Gate ATLAS collects up to four problems and raised ONE prose string over them with
    no clause anywhere. Driven against a substituted `embedded_images`, so the four are
    shown to write four different first clauses."""
    calls = {"n": 0}

    def _images(path):
        calls["n"] += 1
        return before if calls["n"] == 1 else after

    monkeypatch.setattr(glb, "embedded_images", _images)
    with pytest.raises(glb.GateAtlasUntouched) as exc:
        glb.gate_atlas_untouched("src.glb", "out.glb")
    assert exc.value.evidence["clause"] == clause, exc.value.evidence["clauses"]
    assert all(set(p) == {"clause", "detail"} for p in exc.value.evidence["problems"])


def test_the_multi_problem_gates_carry_problems_as_clause_records():
    """`assembly.gate_batch_topology`'s shape, adopted at the three gates that collect."""
    with pytest.raises(parts.GatePartsAccounting) as exc:
        parts.gate_parts_accounting(np.array([0, 0, 0]), 4, ["a", "b"])
    ev = exc.value.evidence
    assert all(set(p) == {"clause", "detail"} for p in ev["problems"]), ev["problems"]
    assert ev["clause"] == ev["problems"][0]["clause"]
    assert ev["clauses"] == [p["clause"] for p in ev["problems"]]
    assert str(exc.value).endswith(ev["problems"][-1]["detail"])


def test_require_finite_writes_a_clause_only_where_the_caller_has_none():
    """`tightened`'s rule, adopted: the home supplies a word where the caller has none and
    DEFERS where the caller has one — a caller's word names the same condition with its
    own operand in it, which is the finer id."""
    ev = {"gate": "PROBE", "andon": "ProbeGate"}
    with pytest.raises(ArmatureError, match="x=nan is not a finite") as exc:
        parts.require_finite("x", float("nan"), ArmatureError, ev)
    assert exc.value.evidence is ev
    assert ev["clause"] == "value_not_finite"

    own = {"gate": "PROBE", "andon": "ProbeGate", "clause": "min_frac_may_only_tighten"}
    with pytest.raises(ArmatureError, match="x=nan is not a finite") as exc:
        parts.require_finite("x", float("nan"), ArmatureError, own)
    assert exc.value.evidence is own
    assert own["clause"] == "min_frac_may_only_tighten"


def test_endpoints_match_already_named_its_clauses():
    """The five raises the finding counted and this walk does not: they DO carry a clause,
    through `dict(ev, clause=...)`. Recorded so the discrepancy is measured, not carried."""
    with pytest.raises(resample.ResampleGate) as exc:
        resample.endpoints_match([], [])
    assert exc.value.evidence["clause"] == "no_frames_to_compare"


def test_the_other_gates_that_collect_problems_name_their_clauses(monkeypatch):
    with pytest.raises(glb.ReliftMismatch) as exc:
        glb.compare_signatures([], [])
    assert exc.value.evidence["clause"] == "one_clip_carries_no_frames"
    with pytest.raises(glb.ReliftMismatch) as exc:
        glb.compare_signatures([1], [1, 2])
    assert exc.value.evidence["clause"] == "frame_counts_differ"
    with pytest.raises(glb.ReliftMismatch) as exc:
        glb.compare_signatures([1, 2], [1, 3])
    assert exc.value.evidence["clause"] == "resolved_lift_diverges_from_the_pinned_glb"

    # `monotonic`'s two clauses are unreachable through `sample_map`, which hard-codes both
    # endpoints — the module says so itself and keeps the second as a labelled
    # cross-function tripwire. Both are driven against a substituted `positions`, so the
    # two receipts are shown to differ rather than assumed to.
    monkeypatch.setattr(resample, "positions", lambda a, b: [0.0, 0.0, 0.0])
    with pytest.raises(resample.ResampleGate) as exc:
        resample.monotonic(3, 3)
    assert exc.value.evidence["clause"] == "timeline_not_strictly_increasing"
    monkeypatch.setattr(resample, "positions", lambda a, b: [0.0, 1.0, 9.0])
    with pytest.raises(resample.ResampleGate) as exc:
        resample.monotonic(3, 3)
    assert exc.value.evidence["clause"] == "timeline_does_not_span_the_source"


# ===================================================================== F-5f8714c8
#
# THE ALPHA LAW refused a missing reason without ever naming the flag that supplies it.


@pytest.mark.parametrize("call,flag", [
    (lambda: startframe.gate_alpha(0.5, (0.1, 0.1, 0.1), None), "--composite-why"),
    (lambda: startframe.gate_backdrop(0.0, 9.0, 0.5, None, 1.0, 5.0), "--plate-why"),
])
def test_the_not_explained_refusals_name_the_flag_that_supplies_the_reason(call, flag):
    """RED on the base: measured over all 243 raise-with-a-message sites in the 21 owned
    modules, not one contained a literal `--flag` spelling — while
    `parts.single_path_segment` and `framing.py` both put the flag in the evidence."""
    with pytest.raises(GateFailure) as exc:
        call()
    assert flag in str(exc.value), str(exc.value)
    assert exc.value.evidence["flag"] == flag


def test_the_flag_spelling_is_the_callers_and_not_hard_coded():
    """A library must not import its caller: the spelling arrives as an argument, so a
    second caller can name its own flag."""
    with pytest.raises(startframe.AlphaGate) as exc:
        startframe.gate_alpha(0.5, (0.1, 0.1, 0.1), None, why_flag="--why-here")
    assert "--why-here" in str(exc.value)
    assert exc.value.evidence["flag"] == "--why-here"


# ===================================================================== F-9dbfdf8f
#
# THE RECORD KNEW THE NUMBER AND THE SENTENCE DID NOT — 19 refusals whose own evidence
# literal carried the value their message omitted.

#: `(callable, evidence keys whose VALUE must appear in the sentence)`. Derived by driving
#: each refusal, never by reading the source: what is asserted is that the reader of the
#: message is told the number the receipt records.
VALUE_IN_SENTENCE = [
    ("walk.GaitParams",
     lambda: walk.GaitParams(n_walk=0),
     ("n_walk", "n_decel", "n_gesture", "n_hold")),
    # `GaitParams` refuses a zero-length phase, so the only way to a zero-sum envelope is
    # a caller that builds its own params object — which `_phase_schedule` accepts, being
    # module-private and duck-typed. The refusal is real; the constructor is not the door.
    ("walk._phase_schedule",
     lambda: walk._phase_schedule(types.SimpleNamespace(n_walk=0, n_decel=1, steps=1)),
     ("effective", "moving_frames")),
    ("framing._norm", lambda: framing._norm((0.0, 0.0, 0.0)), ("length", "vector")),
    ("framing.camera_basis",
     lambda: framing.camera_basis((0.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
     ("position", "target")),
    ("framing.solve_camera",
     lambda: framing.solve_camera([], [], 0.0, 0.0, 50.0, 36.0, 64, 64, 0.5, 0.5),
     ("n_all_points", "n_end_points")),
    ("startframe.composite_colour",
     lambda: startframe.composite_colour(None), ("supplied",)),
    ("startframe.framing_cloud", lambda: startframe.framing_cloud([]), ("n_points",)),
    ("startframe.silhouette_extent",
     lambda: startframe.silhouette_extent([], (0.0, 0.0, 0.0), 2.0, 0.0, 0.0,
                                          50.0, 36.0, 64, 64),
     ("n_points", "n_behind")),
    ("pngio.bit1_not_grayscale",
     lambda: pngio.write_png("x.png", np.zeros((2, 2, 3), dtype=np.uint8), bit_depth=1),
     ("shape",)),
    ("pngio.bit1_values",
     lambda: pngio.write_png("x.png", np.array([[0, 7]], dtype=np.uint8), bit_depth=1),
     ("distinct_values",)),
    ("lift_solve.validate_motion_record",
     lambda: lift_solve.validate_motion_record([]), ("n",)),
    ("assembly.cascade_plan", lambda: assembly.cascade_plan(8, 0), ("group_size",)),
]


def _quoted(value, text):
    """Is `value` readable in `text`? A sequence counts either way it can be spelled.

    `shape` rides the evidence as `[2, 2, 3]` and reads in the sentence as `(2, 2, 3)` —
    the same measurement, and this comparison is about whether the READER is told the
    number, not about which bracket the writer used.
    """
    if str(value) in text or repr(value) in text:
        return True
    if isinstance(value, (list, tuple)):
        return str(tuple(value)) in text or str(list(value)) in text
    return False


@pytest.mark.parametrize("label,call,keys", VALUE_IN_SENTENCE,
                         ids=[row[0] for row in VALUE_IN_SENTENCE])
def test_the_sentence_carries_the_value_its_evidence_records(label, call, keys):
    with pytest.raises(ArmatureError) as exc:
        call()
    text = str(exc.value)
    for key in keys:
        value = exc.value.evidence[key]
        assert _quoted(value, text), (label, key, value, text[:200])


def test_the_walk_measurement_refusal_says_which_side_of_the_disjunction_failed():
    """The worst instance the finding named: `leg_length <= 0 or height <= 0` reported
    "the measured leg length or height is not positive" — the evidence held BOTH numbers,
    the sentence named NEITHER, and the operator was not told which one fired."""
    flat = {name: (0.0, 0.0, 0.0) for name in walk.REQUIRED_LANDMARKS}
    with pytest.raises(walk.WalkError) as exc:
        walk.Performer(flat, 1.0, 1.0)
    ev = exc.value.evidence
    assert ev["clause"] == "measurement_not_positive"
    assert ev["not_positive"], ev
    for name in ev["not_positive"]:
        assert name in str(exc.value)
    assert str(ev["leg_length"]) in str(exc.value)
    assert str(ev["height"]) in str(exc.value)


def test_the_blender_scene_refusals_quote_the_values_their_evidence_records(BS):
    """The two in the one module that imports `bpy`, driven under the stub fixture."""
    with pytest.raises(ArmatureError) as exc:
        BS.world_bounds([1, 2, 3], None)
    assert str(exc.value.evidence["n_objects"]) in str(exc.value), str(exc.value)[:200]

    with pytest.raises(ArmatureError) as exc:
        BS.union_sphere(iter([]))
    assert exc.value.evidence["given_type"] in str(exc.value), str(exc.value)[:200]


def test_the_registered_site_list_refusal_quotes_its_own_counts(monkeypatch):
    monkeypatch.setattr(sitelist, "BONES", list(sitelist.BONES) + [sitelist.BONES[0]])
    with pytest.raises(sitelist.SiteListError) as exc:
        sitelist.validate()
    ev = exc.value.evidence
    assert str(ev["n_bones"]) in str(exc.value)
    assert str(ev["n_e01_sites"]) in str(exc.value)


# ===================================================================== F-08eaf630
#
# FOUR OF THE FIVE REFUSALS IN THE PNG WRITER did not say which file they refused — and
# the fifth, in the same function, proved the convention.

PNG_REFUSALS = [
    ("unsupported_shape", np.zeros((2, 2, 4), dtype=np.uint8), 8),
    ("zero_dimension", np.zeros((0, 2), dtype=np.uint8), 8),
    ("bit1_not_grayscale", np.zeros((2, 2, 3), dtype=np.uint8), 1),
    ("bit1_values", np.array([[0, 7]], dtype=np.uint8), 1),
    ("bit8_dtype", np.zeros((2, 2), dtype=np.float64), 8),
    ("unsupported_bit_depth", np.zeros((2, 2), dtype=np.uint8), 4),
]


@pytest.mark.parametrize("clause,arr,depth", PNG_REFUSALS,
                         ids=[c for c, _, _ in PNG_REFUSALS])
def test_every_png_refusal_names_the_file_it_refused(tmp_path, clause, arr, depth):
    """RED on the base: only `zero_dimension` carried `path`, and NO message of the six
    named it — so a halt from `stage_render`'s 3xN writes identified neither the frame nor
    the channel nor the file.

    The sixth (`unsupported_bit_depth`) is the sibling the finding did not name; it is in
    the same function and is fixed with the five, per the wave-18 sibling rule.
    """
    path = tmp_path / "frame0012.png"
    with pytest.raises(pngio.PngWriteError) as exc:
        pngio.write_png(str(path), arr, bit_depth=depth)
    assert exc.value.evidence["clause"] == clause
    assert exc.value.evidence["path"] == str(path)
    assert str(path) in str(exc.value), str(exc.value)
    assert str(exc.value).startswith(str(path) + ":")
    assert not path.exists(), "a refusal leaves no file"


def test_the_png_refusal_population_is_derived_and_complete():
    """Every `PngWriteError` raise in the module, counted from the tree, so a seventh
    added later without a `path` is a failure here rather than a silent gap."""
    raises = [n for n in ast.walk(_tree("pngio.py"))
              if isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call)
              and getattr(n.exc.func, "id", None) == "PngWriteError"]
    assert len(raises) == len(PNG_REFUSALS)
    for node in raises:
        ev = [a for a in node.exc.args if isinstance(a, ast.Dict)][0]
        keys = [k.value for k in ev.keys if isinstance(k, ast.Constant)]
        assert "path" in keys, ast.dump(node)
