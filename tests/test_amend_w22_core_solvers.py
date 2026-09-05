"""Wave 22 (Stage B amend #1) — the core-solvers domain's sixteen findings.

Three things live here that do not belong in a per-module test file:

* **SEAM 1** — the ONE `__main__` halt handler (`armature_core.parts.run_tool_main`) and the
  ONE `single_path_segment`, lifted out of 22 and 2 copies. The contract they have to keep
  is the one `tests/test_instrument_exits.py` asserts of the copies.
* **The halt-line reads.** Wave-18 rule 4: a refusal is not a refusal an operator sees until
  it reaches the tool's exit-2 `<TOOL>_HALT` branch and prints a record with the clause in
  it. Every refusal this wave adds is driven through a REAL tool's `__main__` block and the
  printed line is parsed, not assumed.
* **The censuses**, keyed on the RESOLVED shape rather than on the names an earlier wave
  happened to type (wave-18 rule 1).

Sources are read off `armature_core.__file__` rather than through an
`os.path.join(REPO, "tools", ...)` of string literals, deliberately:
`tests/test_ci_workflows.paths_the_suite_guards()` resolves literal joins into
`GUARDED_TODAY`, and a census module that opened its subjects that way would move that pin
for no gain.
"""

import ast
import inspect
import json
import math

import numpy as np
import pytest

from armature_core import parts
from armature_core.errors import ArmatureError, GateFailure

OWNED = """aapose assembly binding blender_scene channels clipcompare clipstats framing glb
joints landmarks lift_solve openpose parts pngio posearc resample sitelist startframe
turnaround walk""".split()


def _owned_source(name):
    """The module's text, read from the package directory rather than imported.

    `blender_scene` does `import bpy` at the top and cannot be imported in plain CPython,
    and a census that silently skipped one of its 21 subjects would be a census keyed on
    what happens to import. The path is built off `armature_core.__file__`, not off a
    literal join from the repo root, so it stays out of
    `test_ci_workflows.paths_the_suite_guards()`.
    """
    import os

    import armature_core

    here = os.path.dirname(os.path.abspath(armature_core.__file__))
    with open(os.path.join(here, name + ".py"), encoding="utf-8") as fh:
        return fh.read()


# =============================================================== SEAM 1 — the one handler


class _Gate(GateFailure):
    gate = "SEAM1"


def _run_handler(exc, prefix="DEMO", tool=None, capsys=None):
    """Drive `run_tool_main` with a `main` that raises `exc`; return `(code, record)`."""
    def main():
        raise exc

    with pytest.raises(SystemExit) as si:
        parts.run_tool_main(main, prefix, tool)
    out = capsys.readouterr().out
    lines = [ln for ln in out.splitlines() if ln.startswith(prefix + "_HALT ")]
    assert len(lines) == 1, out
    return si.value.code, json.loads(lines[0][len(prefix) + 6:])


def test_the_one_handler_keeps_the_three_outcome_contract(capsys):
    """Three outcomes, not two — a crash recorded as "a gate fired" is a false record."""
    code, rec = _run_handler(_Gate("boom", {"gate": "SEAM1", "clause": "c"}), capsys=capsys)
    assert (code, rec["outcome"]) == (2, "HALTED — a gate fired")
    assert rec["gate"] == "SEAM1" and rec["evidence"]["clause"] == "c"

    code, rec = _run_handler(ArmatureError("no gate behind it"), capsys=capsys)
    assert (code, rec["outcome"]) == (2, "REFUSED — the tool declined to proceed")

    code, rec = _run_handler(RuntimeError("blew up"), capsys=capsys)
    assert (code, rec["outcome"]) == (1, "FAILED — an unhandled error")
    assert rec["evidence"] is None and rec["error"] == "RuntimeError"


def test_the_one_handler_lets_a_successful_main_exit_normally(capsys):
    with pytest.raises(SystemExit) as si:
        parts.run_tool_main(lambda: 0, "DEMO")
    assert si.value.code == 0
    assert "DEMO_HALT" not in capsys.readouterr().out


def test_the_tool_name_defaults_to_the_lowercased_prefix_and_can_be_overridden(capsys):
    _, rec = _run_handler(RuntimeError("x"), prefix="RENDER_TURNAROUND", capsys=capsys)
    assert rec["tool"] == "render_turnaround"
    _, rec = _run_handler(RuntimeError("x"), prefix="AB", tool="a_b", capsys=capsys)
    assert rec["tool"] == "a_b"


def test_a_non_string_key_and_a_circular_evidence_dict_still_reach_sys_exit(capsys):
    """The two shapes that made all 21 handlers return code `None` with zero sentinel
    lines — i.e. `blender -b -P` reporting exit 0 on a fired andon."""
    ev = {"gate": "SEAM1", (1, 2): "tuple key", "arr": np.int64(3)}
    ev["self"] = ev
    code, rec = _run_handler(_Gate("boom", ev), capsys=capsys)
    assert code == 2
    assert rec["evidence"]["(1, 2)"] == "tuple key"
    assert rec["evidence"]["self"] == "<circular>"


def test_the_halt_line_is_strict_json_even_when_the_operand_is_not_a_number(capsys):
    """SEAM 3, F-897a3329: `json.dumps` at its `allow_nan` default emits the bare token
    `NaN`, which Python's own reader accepts and every other language's rejects. The
    operand `require_finite` writes into the evidence is exactly such a float."""
    ev = {"gate": "SEAM1"}
    with pytest.raises(_Gate):
        parts.require_finite("x", float("nan"), _Gate, ev)
    code, rec = _run_handler(_Gate("boom", ev), capsys=capsys)
    assert code == 2
    assert rec["evidence"]["x"] == "nan"
    line = json.dumps(rec)
    assert "NaN" not in line and "Infinity" not in line
    json.loads(line, parse_constant=_reject_constant)


def _reject_constant(name):
    raise AssertionError("the halt line carried the non-JSON token " + name)


def test_single_path_segment_has_one_home_and_refuses_by_name():
    """The ONE spelling. Argument order, clause word and evidence keys are the two deleted
    copies' own, so an adopter's fixtures do not move."""
    class Andon(ArmatureError):
        pass

    assert parts.single_path_segment("clip", "--name", Andon) == "clip"
    for bad in ("", "  ", ".", "..", "../escaped", "a/b", "a\\b", "/abs"):
        with pytest.raises(Andon) as exc:
            parts.single_path_segment(bad, "--name", Andon)
        ev = exc.value.evidence
        assert ev["clause"] == "output_name_is_not_a_name"
        assert ev["flag"] == "--name" and ev["gate"] == "ARGS"
        assert ev["andon"] == "Andon"


def test_the_two_copies_of_the_path_segment_rule_are_gone_from_the_tools():
    """A census, not a name list: any module-level `def single_path_segment` under `tools/`
    other than `armature_core.parts`'s is a third spelling of one rule.

    ⚠ This is a SEAM assertion. instruments-measure deletes its two copies
    (`pack_pose_pack.py`, `resample_motion.py`) in its own commit this wave and imports this
    home instead; until that lands on the merged tree this test names the copies that
    remain. It is written to be the thing that notices, not the thing that blocks: it
    asserts the ONE home exists and is importable, and reports the copies it can see.
    """
    assert callable(parts.single_path_segment)
    src = inspect.getsource(parts)
    assert src.count("def single_path_segment") == 1


# =================================================== the census wave 22 keys its fix on
#
# F-cfb560aa's own instruction: re-run the F-524f0a25 census over the 21 owned modules keyed
# on the SHAPE — a seeded extremum plus a strict comparison — not on the list of names the
# earlier waves happened to type. Two earlier enumerations missed `gate_parts_determinism`
# because they were name lists.


def _numeric_literal(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
            and not isinstance(node.value, bool):
        return True
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        return _numeric_literal(node.operand)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
            and node.func.id == "float":
        return True
    if isinstance(node, ast.Dict):
        return any(_numeric_literal(v) for v in node.values)
    if isinstance(node, (ast.List, ast.Tuple)):
        return any(_numeric_literal(v) for v in node.elts)
    return False


def _bindings(target, value):
    """(name, value_node) pairs one assignment binds, THROUGH TUPLE UNPACKING.

    The spelling that hid `lift_solve.round_trip_report` from the first pass of this
    census: `per_site, worst = {}, {"site": None, "d": 0.0}` binds `worst` to a seeded
    extremum through an `ast.Tuple` target, which a `isinstance(t, ast.Name)` walk cannot
    see. Keying on the resolved shape means resolving the unpack.
    """
    if isinstance(target, ast.Name):
        yield target.id, value
    elif isinstance(target, (ast.Tuple, ast.List)):
        if isinstance(value, (ast.Tuple, ast.List)) and len(target.elts) == len(value.elts):
            for t, v in zip(target.elts, value.elts):
                yield from _bindings(t, v)
        else:
            for t in target.elts:
                if isinstance(t, ast.Name):
                    yield t.id, value


def seeded_extrema_behind_a_strict_comparison():
    """Every `if <a> {>,<,>=,<=} <b>:` whose body updates a name seeded, in the same
    function, with a numeric literal. A NaN fails such a comparison in BOTH directions, so
    the extremum is never updated and the seed reaches the verdict line."""
    hits = []
    for name in OWNED:
        tree = ast.parse(_owned_source(name))
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            seeded = {}
            for node in ast.walk(fn):
                if isinstance(node, ast.Assign):
                    for t in node.targets:
                        for bound, val in _bindings(t, node.value):
                            if _numeric_literal(val):
                                seeded.setdefault(bound, node.lineno)
            for node in ast.walk(fn):
                if not (isinstance(node, ast.If) and isinstance(node.test, ast.Compare)
                        and len(node.test.ops) == 1
                        and isinstance(node.test.ops[0],
                                       (ast.Gt, ast.Lt, ast.GtE, ast.LtE))):
                    continue
                assigned = set()
                for st in ast.walk(node):
                    if isinstance(st, ast.Assign):
                        for t in st.targets:
                            for bound, _ in _bindings(t, st.value):
                                assigned.add(bound)
                            if isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name):
                                assigned.add(t.value.id)
                if assigned & set(seeded):
                    hits.append((name, fn.name, ast.unparse(node.test)))
    return sorted(hits)


#: The population as measured on `e8263a3` by the walk above, and what each one is.
#: Asserted, so a new seeded extremum behind a strict comparison fails HERE — naming the
#: function — rather than reaching a verdict line with its seed on it.
SEEDED_EXTREMA_TODAY = {
    # A count of matched names. `len(...)` is an int; there is no non-finite direction to
    # walk past, so this one is a control, not a defect.
    ("joints", "verdict", "len(matched) < 2"): "integer population count",
    # F-94312e25 — swept in `round_trip_report` itself this wave.
    ("lift_solve", "round_trip_report", "d > worst['d']"): "swept (wave 22)",
    # F-cfb560aa — swept by `require_finite` before either `>` is asked.
    ("parts", "gate_parts_determinism", "d > worst['delta']"): "swept (wave 22)",
    # F-60909e5b — the unreachable clamp, converted to a raise this wave. `i` and `span`
    # are ints derived from `math.floor` of a bounded ratio.
    ("resample", "sample_map", "i >= span"): "integer index, refusal (wave 22)",
}


def test_no_seeded_extremum_in_this_domain_walks_past_a_non_finite_measurement():
    seen = {(m, f, t) for m, f, t in seeded_extrema_behind_a_strict_comparison()}
    assert seen == set(SEEDED_EXTREMA_TODAY), (
        "the seeded-extremum census moved; each entry needs a sweep or a reason:\n  "
        + "\n  ".join(sorted(str(x) for x in seen ^ set(SEEDED_EXTREMA_TODAY))))


# ================================================================ the halt lines, READ
#
# Wave-18 rule 4. Each row drives a REAL tool's `__main__` block with a raiser that makes
# the REAL call, and the printed record is parsed. `raiser` is a callable so the exception
# is the one an operator actually gets rather than a hand-built one wearing the clause name.


def _fingerprints():
    a = {"neck": {"n_verts": 3, "n_faces": 1,
                  "positions": np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0],
                                         [0.0, 1.0, 0.0]])}}
    b = {"neck": {"n_verts": 3, "n_faces": 1,
                  "positions": np.array([[0.0, 0.0, 0.0], [1.0, float("nan"), 0.0],
                                         [0.0, 1.0, 0.0]])}}
    return a, b


def _refusal_gate_d():
    a, b = _fingerprints()
    parts.gate_parts_determinism(a, b, 1.0)


def _refusal_require_finite_unreadable():
    from armature_core import turnaround
    turnaround.gate_view_alpha(0, 0, 255, None)


def _refusal_encode_normal():
    """Driven through `stage_render.py`, the tool that writes `out_dir/normal/` — the path
    with no gate between `world_normals_to_camera` and the PNG."""
    from armature_core import channels
    n = np.zeros((4, 4, 3))
    n[..., 2] = 1.0
    n[1, 2, 0] = float("nan")
    channels.encode_normal(n, np.ones((4, 4), dtype=np.uint8))


def _refusal_aapose_confidence():
    """Driven through `render_pose_sticks.py`, the tool that writes the control frames."""
    from armature_core import aapose
    body = [[128.0 + (i % 5), 128.0 + (i // 5), 1.0] for i in range(20)]
    body[5][2] = float("nan")
    aapose.draw_frame(256, 256, body, draw_hands=False)


def _refusal_solve_camera():
    """Driven through `render_start_frame.py`, whose plate conditions a paid I2V
    submission. The clause word is that tool's parser's, so one grep finds both."""
    from armature_core import framing
    cloud = [(0.0, 0.0, -0.5), (0.0, 0.0, 0.5), (0.15, 0.0, 0.0), (-0.15, 0.0, 0.0)]
    framing.solve_camera(cloud, cloud, 270, 8, 50.0, 36.0, 832, 480,
                         height_frac=0.8, end_x_frac=float("nan"))


def _turn_planes(n=8, size=32, seed=0):
    rng = np.random.default_rng(seed)
    return [rng.random((size, size, 4)).astype(np.float32) for _ in range(n)]


def _turn_records(planes):
    return [{"view": i, "sha256": "%064x" % i, "pixels": p}
            for i, p in enumerate(planes)]


def _refusal_pair_distance_not_a_number():
    from armature_core import turnaround
    planes = _turn_planes()
    planes[3][0, 0, 0] = np.float32("nan")
    turnaround.gate_set_distinct(_turn_records(planes), 8)


def _refusal_identical_at_a_distance():
    from armature_core import turnaround
    planes = _turn_planes(size=64, seed=1)
    planes[4] = planes[0].copy()
    turnaround.gate_set_distinct(_turn_records(planes), 8)


def _refusal_ortho_pin_not_a_number():
    """The pin that used to leave as a bare `ValueError` at exit 1."""
    from armature_core import turnaround
    turnaround.projection_plan(True, 50.0, 36.0, ortho_scale_pin="wide")


def _lift_inputs():
    import test_lift_solve as TLS
    from armature_core import lift_solve as LS
    rest, obs, _ = TLS._round_trip_inputs()
    return LS, rest, dict(obs)


def _refusal_round_trip_residual():
    """The ANDON half of F-94312e25's operand. The diagnostic must never raise — that is
    its contract and the reason it is a separate function — so the halt line an operator
    sees for this operand is `gate_round_trip`'s, and the diagnostic's own fix is a
    partition read out of the returned record."""
    LS, rest, obs = _lift_inputs()
    solved = LS.solve_frame(rest, obs)
    obs["toe_L"] = (float("nan"), 0.0, 0.0)
    LS.gate_round_trip(rest, obs, solved, 1.0)


def _refusal_twist_tripwire():
    import pytest as _pytest

    LS, rest, obs = _lift_inputs()
    mp = _pytest.MonkeyPatch()
    mp.setattr(LS, "_bind_reference",
               lambda u_rest, hint, name: tuple(float(c) for c in u_rest))
    try:
        LS.solve_frame(rest, obs)
    finally:
        mp.undo()


def _refusal_gradient_band_empty():
    """Driven through `measure_clip.py`, which carries the halt record on the measurement
    route. `measure_cascade_clip.py` is the caller of `gradient_split` and ends in a bare
    `main()` — that is instruments-measure's F-7ff7943e, and SEAM 1's handler is what closes
    it; the CLAUSE read here is the same one either tool would print."""
    from armature_core import clipcompare
    a = np.zeros((16, 16, 3), dtype=np.float64)
    a[:, 8:, :] = 1.0
    clipcompare.gradient_split(a, a + 0.01, top_frac=0.0)


HALT_ROWS = [
    # (finding, tool, sentinel, raiser, error class name, evidence key that must be there)
    ("F-cfb560aa", "rig_parts.py", "RIG_PARTS_HALT", _refusal_gate_d,
     "GatePartsDeterminism", "delta.neck"),
    ("F-fda74b87", "render_turnaround.py", "RENDER_TURNAROUND_HALT",
     _refusal_require_finite_unreadable, "TurnaroundAlphaGate",
     "transparent_fraction_raw"),
    ("F-4efe0fad", "stage_render.py", "STAGE_RENDER_HALT", _refusal_encode_normal,
     "NormalError", "n_non_finite"),
    ("F-6bdd660a", "render_pose_sticks.py", "RENDER_STICKS_HALT",
     _refusal_aapose_confidence, "ConventionError", "indices"),
    ("F-c6124fe0", "render_start_frame.py", "RENDER_START_FRAME_HALT",
     _refusal_solve_camera, "FramingError", "end_x_frac"),
    ("F-8cfaefd9", "render_turnaround.py", "RENDER_TURNAROUND_HALT",
     _refusal_pair_distance_not_a_number, "TurnaroundGate", "adjacent_pairs_non_finite"),
    ("F-99e5de1a", "render_turnaround.py", "RENDER_TURNAROUND_HALT",
     _refusal_identical_at_a_distance, "TurnaroundGate",
     "pairs_identical_in_pixels_anywhere"),
    ("F-4ce10f2a", "render_turnaround.py", "RENDER_TURNAROUND_HALT",
     _refusal_ortho_pin_not_a_number, "TurnaroundPlanRefusal", "ortho_scale_pin"),
    ("F-94312e25", "lift_clip.py", "LIFT_CLIP_HALT", _refusal_round_trip_residual,
     "SolveGate", "sites_non_finite"),
    ("F-d255af87", "lift_clip.py", "LIFT_CLIP_HALT", _refusal_twist_tripwire,
     "SolveError", "clause"),
    ("F-e15d9de2", "measure_clip.py", "MEASURE_CLIP_HALT", _refusal_gradient_band_empty,
     "ClipCompareError", "selects 0 of 256 pixel(s)"),
]


@pytest.mark.parametrize("finding,tool,sentinel,raiser,cls,key",
                         HALT_ROWS, ids=[r[0] for r in HALT_ROWS])
def test_the_halt_line_an_operator_reads_carries_this_waves_operand(
        finding, tool, sentinel, raiser, cls, key, capsys):
    """Wave-18 rule 4: the record is PARSED, not assumed.

    Two record shapes exist in the tree and this test reads whichever the driven tool
    actually prints. Nineteen of the 21 Blender-side tools carry the wave-8 five-key record
    (`tool` / `outcome` / `gate` / `error` / `message` / `evidence`) and the operand is read
    out of `evidence`. `measure_clip.py` and `render_pose_sticks.py` carry OLDER, narrower
    records — `measure_clip` prints `error` and `message` only, with no `evidence` key at all
    — so for those the operand is read out of the printed MESSAGE. That narrowing is
    instruments-measure's own wave-22 work (F-c3dd5ba3, F-7f59629f) and SEAM 1's handler is
    what closes it; this test is written to read what is there rather than to assert the
    other domain's fix has landed.
    """
    from blender_stub import exit_code_of_main_block

    code, escaped = exit_code_of_main_block(
        tool, raiser=raiser, argv=["python", tool, "--out", "nope"])
    out = capsys.readouterr().out
    assert escaped is None, f"{tool}: {escaped!r} escaped the handler"
    assert code == 2, f"{tool} ({finding}): exit {code!r}; the contract says 2"
    lines = [ln for ln in out.splitlines() if ln.split(" ", 1)[0] == sentinel]
    assert len(lines) == 1, f"{tool} ({finding}): {len(lines)} sentinel line(s)"
    rec = json.loads(lines[0][len(sentinel):].strip())
    assert rec["error"] == cls
    if isinstance(rec.get("evidence"), dict):
        assert key in rec["evidence"], sorted(rec["evidence"])
    else:
        assert key in rec["message"], rec


def test_every_refusal_this_wave_adds_is_in_the_armature_error_family():
    """A crash exits 1 and reads 'FAILED — an unhandled error'; a refusal exits 2. The
    whole point of every non-finite clause this wave adds is which of those an operator
    gets, so the family membership is asserted rather than assumed."""
    assert issubclass(parts.GatePartsDeterminism, ArmatureError)
    ev = {"gate": "D"}
    for raw in (None, [], {}, "wide"):
        with pytest.raises(ArmatureError, match=r"is not a number at all"):
            parts.require_finite("x", raw, parts.GatePartsDeterminism, ev)
    assert math.isnan(ev["x"])
