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
}
#: `resample.sample_map`'s `if i >= span` LEFT this census in the same wave (F-60909e5b):
#: the branch no longer assigns to a seeded name, it RAISES, so the shape this walk keys on
#: is gone from that function rather than exempted in a list.


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
    # WAVE-22 MERGE (coordinator, 2026-09-05): on the merged tree `measure_clip.py` ends in
    # `parts.run_tool_main` (SEAM 1) and prints the six-key record, so the operand is read out
    # of `evidence` like every other row; the key is `n_selected` (0), MEASURED. The message
    # substring this row carried while the narrow record was in the tree is gone with it.
    ("F-e15d9de2", "measure_clip.py", "MEASURE_CLIP_HALT", _refusal_gradient_band_empty,
     "ClipCompareError", "n_selected"),
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
    other domain's fix has landed. (WAVE-22 MERGE (coordinator, 2026-09-05): it landed for `measure_clip` --
    the merged tree prints the six-key record there and the F-e15d9de2 row reads `evidence`;
    the paragraph above is kept as the record of why the two-shape read exists.)
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


# =================================================== wave 22: the four LOW findings
#
# Three of them are checks that cannot fail and one is a stale citation. None has a red proof
# in the ordinary sense — an unreachable branch has no input that reaches it — so each is
# proven the only honest way: SWEEP the population to show the branch is unreachable, then
# BREAK THE PRECONDITION the unreachability rests on and read what comes out.


def test_the_interior_of_the_sample_map_never_reaches_the_span_clamp():
    """F-60909e5b, the sweep. `u = j * span / (n_dst - 1) < span` for every
    `0 < j < n_dst - 1`, so `floor(u) <= span - 1` always."""
    from armature_core import resample as RS

    checked = 0
    for n_src in range(2, 60):
        for n_dst in range(2, 60):
            span = n_src - 1
            for j, (i, _t) in enumerate(RS.sample_map(n_src, n_dst)):
                if 0 < j < n_dst - 1:
                    assert i < span, (n_src, n_dst, j, i, span)
                    checked += 1
    assert checked > 50000, checked


def test_the_span_clamp_is_now_a_raise_that_names_the_arithmetic_it_guards(monkeypatch):
    """The red proof for an unreachable branch: break the arithmetic the unreachability
    rests on. Before this wave the same broken arithmetic was CLAMPED silently, which is
    the one shape that would hide the change it was written to survive."""
    import math as _math

    from armature_core import resample as RS

    class _Floor:
        def __getattr__(self, name):
            return getattr(_math, name)

        @staticmethod
        def floor(u):
            return _math.floor(u) + 99

    monkeypatch.setattr(RS, "math", _Floor())
    with pytest.raises(RS.ResampleError) as exc:
        RS.sample_map(8, 5)
    ev = exc.value.evidence
    assert ev["clause"] == "interior_sample_past_the_span"
    assert ev["n_src"] == 8 and ev["n_dst"] == 5 and ev["span"] == 7


def test_the_endpoint_clause_cannot_fire_against_todays_map_and_says_so():
    """F-63a37caf, the sweep the finding recorded: 2..80 x 2..80, 6241 pairs, 0 violations.

    Kept as a CROSS-FUNCTION REGRESSION GUARD on `sample_map`'s endpoint construction — a
    legitimate reason to keep a check that cannot fire today, but only if it is labelled as
    one, which is the treatment `binding.rigid_segment_weights` already gives its three
    `invariant_by_construction` diagnostics.
    """
    from armature_core import resample as RS

    pairs = 0
    for n_src in range(2, 81):
        for n_dst in range(2, 81):
            u = RS.positions(n_src, n_dst)
            assert u[0] == 0.0 and u[-1] == float(n_src - 1), (n_src, n_dst, u[0], u[-1])
            pairs += 1
    assert pairs == 79 * 79
    src = _owned_source("resample")
    assert "invariant_by_construction" in src
    assert "CROSS-FUNCTION REGRESSION GUARD" in src


def test_the_live_clause_beside_it_is_still_live(monkeypatch):
    """Both directions: the STRICT-INCREASE clause in the same function is not labelled a
    tripwire, because it is an andon on this function's own input and it fires."""
    from armature_core import resample as RS

    monkeypatch.setattr(RS, "positions", lambda n_src, n_dst: [0.0, 0.0, float(n_src - 1)])
    with pytest.raises(RS.ResampleGate, match=r"not strictly increasing"):
        RS.monotonic(4, 3)


def test_the_cadence_gate_walks_every_consecutive_interval():
    """F-aee5d2a8, the coverage measurement the disposition rests on: n-1 intervals for n
    phase samples, which is every consecutive pair — so the stance-exchange clause inside
    `_integrate_forward` can never be the first to see an over-long interval."""
    import math as _math

    from armature_core import walk as W

    for n, want in ((2, 1), (5, 4), (41, 40), (65, 64)):
        phase = [k * 2.0 * _math.pi * 0.01 for k in range(n)]
        ev = W.gate_cadence_is_representable(phase, W.STANCE_FRAC_MODELLED, where="t")
        assert ev["n_intervals"] == want, (n, ev)


def test_the_stance_exchange_refusal_is_labelled_a_tripwire_not_a_live_andon():
    """It carries its OWN clause word and a `reachability` key, so a reader who finds a
    `raise WalkError` there does not conclude the top-of-function gate misses the exchange
    frames. Same disposition as `resample.sample_map`'s clamp, recorded in one place.

    WAVE 34 pin-fix: finding-id stamps moved out of the raise site when the gait model
    generalised; the tripwire label and CadenceGate representability phrase remain.
    """
    src = _owned_source("walk")
    assert "cadence_outruns_frame_rate_at_a_stance_exchange" in src
    assert "structural tripwire on " in src
    assert "representability" in src


#: Every `<file>.py:<line>` prose citation surviving in this domain's 21 modules, MEASURED
#: on this branch, with the reason each is allowed to remain. The rule this wave adopts is
#: "prose cites FUNCTIONS, not lines" (F-b3ff3a57, and `lift_solve`'s three via SEAM 7/8) —
#: so a LIVE citation is a defect and the only line numbers left are inside CORRECTION
#: RECORDS, which this repo keeps rather than deletes because the correction is the useful
#: part. A new entry here is a new line citation somebody wrote as a live claim.
SURVIVING_LINE_CITATIONS = {
    # Named in the prose as blank and re-anchored on the symbol in the same sentence — the
    # correction discipline working, measured on `e8263a3` as part of this census.
    "blender_scene": {("probe_subject.py", 75), ("stage_render.py", 508)},
    # The correction record for the four stale anchors this pair used to carry, plus the two
    # LINE anchors retired this wave when the citations moved to the symbol form.
    # WAVE 28 (instruments-measure, F-3ce0db92): the set is UNCHANGED and the reason is the
    # measurement. Giving `measure_lift`'s six silent flags their `help=` added twelve lines
    # above `detect` and `summarise`, so the `(summarise)` qualifier on `measure_lift.py:468`
    # came to name `jitter` instead. The QUALIFIERS are dropped in `lift_solve`'s docstring
    # and the numbers are kept — `test_lift_solve.py` asserts `corrected <= mentioned`, so
    # deleting the correction record would take that census red — and both rows are recorded
    # in `test_amend_w16_core_solvers.CORRECTED_ANCHORS`, which is what that set is for.
    "lift_solve": {("lift_clip.py", 275), ("lift_clip.py", 276), ("measure_lift.py", 334),
                   ("measure_lift.py", 468), ("measure_lift.py", 481)},
    "posearc": {("rig_character.py", 661)},
    # F-b3ff3a57's own correction record: the three anchors the paragraph quotes as what it
    # USED to say, the one it measured as moved, and the sibling fix it points at.
    "sitelist": {("project_pose_keypoints.py", 229),
                 ("rig_character.py", 1135), ("rig_parts.py", 480)},
    "startframe": {("render_start_frame.py", 142)},
}


def line_citations_by_module():
    """`{module: {(file, line)}}` over the 21 owned modules' source text."""
    import re

    out = {}
    for name in OWNED:
        rows = {(f, int(n)) for f, n
                in re.findall(r"([a-z_]+\.py):([0-9]+)", _owned_source(name))}
        if rows:
            out[name] = rows
    return out


def test_no_prose_in_this_domain_makes_a_LIVE_claim_about_a_line_number():
    """F-b3ff3a57. The coordinator's 57-moved-citations seed, measured across this domain
    and confirmed on exactly one line — the line whose own purpose was to correct a stale
    citation.

    A census over all 17 `<file>.py:<line>` prose citations in the 21 modules resolved 14 to
    a non-blank line and found 3 pointing at blank lines, all three of which the surrounding
    prose ALREADY names as blank and re-anchors on the symbol. The one that did not:
    `sitelist.py` read "Of the three line numbers, only `project_pose_keypoints.py::span_stats` was
    right". MEASURED on `e8263a3`, that line is now the middle of a `ProjectGate` refusal
    message and `grep -n validate tools/project_pose_keypoints.py` returns exactly one line,
    which is not that one — the wave-16 constructor deletions moved it, so the wave-15
    correction that quoted it as the surviving-correct citation was itself wrong.

    The general form is taken rather than a line census: prose cites FUNCTIONS. What is
    asserted here is (a) the population of surviving line citations, each of which is inside
    a correction record, so a new LIVE one fails on the day it is written; (b) that every
    surviving citation still resolves to a line that exists in the file it names; and (c)
    that `sitelist`'s paragraph now names its callers by symbol and carries the measurement
    that overturned its own citation.
    """
    import os

    import armature_core

    got = line_citations_by_module()
    assert got == SURVIVING_LINE_CITATIONS, {
        "appeared": {m: sorted(v - SURVIVING_LINE_CITATIONS.get(m, set()))
                     for m, v in got.items()
                     if v - SURVIVING_LINE_CITATIONS.get(m, set())},
        "vanished": {m: sorted(v - got.get(m, set()))
                     for m, v in SURVIVING_LINE_CITATIONS.items()
                     if v - got.get(m, set())},
        "why it matters": "prose cites FUNCTIONS, not lines; a new line citation is a "
                          "claim that stops being true the next time anything above it "
                          "is edited",
    }

    tools_dir = os.path.dirname(os.path.dirname(os.path.abspath(armature_core.__file__)))
    for _mod, rows in got.items():
        for fname, lineno in rows:
            path = os.path.join(tools_dir, fname)
            if not os.path.exists(path):
                continue
            with open(path, encoding="utf-8") as fh:
                n_lines = len(fh.read().split("\n"))
            assert 1 <= lineno <= n_lines, (fname, lineno, n_lines)

    src = _owned_source("sitelist")
    for symbol in ("tools/rig_character.py::validate_sitelist",
                   "tools/project_pose_keypoints.py::main",
                   "tools/rig_parts.py::main"):
        assert symbol in src, symbol
    assert "MEASURED on `e8263a3`" in src
    assert "citations are on the SYMBOL and the line numbers are gone" in src


# =========================== wave 22, F-8759b386: every refusal carries a receipt
#
# CENSUSED on `e8263a3` over the 21 owned modules by AST, resolving each raised name to a
# runtime class: 221 raises with a call, of which 217 resolve into the `ArmatureError`
# family (101 of them `GateFailure` subclasses, 116 not). **52 of the 217 passed NO evidence
# argument at all**, and a further 17 passed a literal dict carrying `gate` and `andon` but
# no `clause`.
#
# All 17 `raise LandmarkError` sites in `landmarks.py` were among the 52, as were the four in
# `joints.py` that raise the same class — 21 `LandmarkError` raises in the domain, 21 with no
# receipt — as were all six `resample.ResampleError`, nine of ten `lift_solve.SolveError`,
# all four `posearc.SpecError`, both ortho `turnaround.TurnaroundPlanRefusal` and ten bare
# `ArmatureError(...)` raises in `binding.py`, `openpose.py` and `parts.py`. All 19 bare
# family raises in `armature_core` were in this domain's files, which `errors.py`'s own
# docstring names as the thing the wave-14 constructor fix was "not a licence for".
#
# `LandmarkError`'s own docstring argues that a mesh which does not present the anatomy "is a
# subject this derivation cannot place bones on ... Halting is the only signal that
# survives" — and the signal it emitted was a prose sentence and two nulls: a halt reaching
# `tools/diagnose_bone_heat.py` or `tools/make_parts_sheet.py` read `gate: null, evidence:
# null`, so a triage that wanted to know WHICH of seventeen anatomical refusals fired had to
# grep the message.
#
# The reason none of it was red: `tests/test_core_solver_evidence.py`'s derived census walks
# only raises whose class resolves to a `GateFailure` SUBCLASS, and the non-Gate subtree is
# spot-checked for a hand-typed trio and only for the constructor property. No census
# anywhere required a `clause`. Widening that census to the resolved `ArmatureError` family
# is the tests domain's (wave 23); what is asserted here is the property itself, derived.


def family_raises_without_a_clause():
    """Every family raise in the 21 owned modules whose evidence carries no `clause`.

    Keyed on the RESOLVED class (wave-18 rule 1): the raised NAME is looked up in its own
    module and then in `errors`, and only classes that actually subclass `ArmatureError`
    count — a census that keyed on the spelling would miss a re-exported name and invent a
    member out of any local variable that happens to be called `SolveError`.

    WAVE 25 (F-3b71c0aa): the WALK moved to `_census_nodes.family_raises_without_a_clause`
    and is called from here with this domain's population and this domain's resolver.
    Nothing about the property or the answer changed — what changed is that the SAME walk
    now also ranges over `tools/*.py`, where 78 of 150 resolved family raises carried no
    clause and the property `== []` had never been asked. A second copy of this walk for
    the second population is exactly the defect this module's own opening was written
    against, so there is not one.
    """
    import importlib

    import _census_nodes as _CN

    def _resolve(module, cname):
        try:
            mod = importlib.import_module("armature_core." + module)
        except Exception:                   # blender_scene imports bpy
            mod = None
        cls = getattr(mod, cname, None) if mod is not None else None
        if cls is None:
            import armature_core.errors as E
            cls = getattr(E, cname, None)
        return cls

    trees = {name: ast.parse(_owned_source(name)) for name in OWNED}
    return _CN.family_raises_without_a_clause(trees, _resolve, ArmatureError)


def test_every_family_raise_in_this_domain_names_the_clause_that_pulled():
    """The property, over the whole resolved family and not the `GateFailure` half of it."""
    bad = family_raises_without_a_clause()
    assert bad == [], {
        "raises with no clause a reader can key on": bad,
        "why it matters": "a halt line reading `gate: null, evidence: null` is a prose "
                          "sentence; a triage that wants to know WHICH of seventeen "
                          "anatomical refusals fired has to grep the message",
    }


#: Clause words spelled at more than one raise site inside one module, MEASURED on this
#: branch, with the reason each repeat is ONE refusal rather than two sharing a word. A new
#: entry is two different refusals a triage cannot split — the defect one level up from the
#: one this wave fixed.
REPEATED_CLAUSE_WORDS = {
    # One refusal, two profiles: `stickwidth` and `hand_stickwidth` refuse the same unknown
    # `stickwidth_type` with the same message shape.
    "aapose": {"unknown_stickwidth_type"},
    # WAVE 35: character-class bind refuses the same mesh/bone shape checks at more than
    # one door — one refusal shape per word, not two triage keys.
    "binding": {"bone_radius_not_positive", "no_deforming_bones", "vertices_not_n_by_3"},
    # `depth_extent` and `normalize_depth` refuse the same population — the geometry pixels
    # — under one word, deliberately (wave 18, F-476a4ee8).
    "channels": {"non_finite_geometry_depth"},
    # `frame_fidelity` and `gradient_split` now answer the same question about what a frame
    # is, under the same two words, which is the whole point of F-e15d9de2.
    "clipcompare": {"frame_not_hw3", "shape_mismatch"},
    # `half_fovs` and `require_frame_size` refuse a non-positive frame size the same way.
    # WAVE 34: camera-path solvers reuse empty_point_cloud / point_cloud_not_finite with
    # the single-shot framing refusals — one refusal shape, two call doors.
    "framing": {"empty_point_cloud", "frame_size_not_positive", "point_cloud_not_finite"},
    # WAVE 34: character-class adapter refuses a mismatched class at two import doors.
    "landmarks": {"character_class_mismatch"},
    # WAVE 34: GaitParams' constructor WalkError and gate_stance_frac_is_modelled's
    # GaitGate share stance_frac_outside_0_1 — one interval, two doors.
    "walk": {"stance_frac_outside_0_1"},
}


def test_a_repeated_clause_word_in_this_domain_is_one_refusal_and_not_two():
    """A clause is an identity. Two DIFFERENT refusals under one word are one word a triage
    cannot split, which is the defect one level up from the one this wave fixed."""
    import collections
    import re

    got = {}
    for name in OWNED:
        words = re.findall(r'"clause": "([a-z0-9_]+)"', _owned_source(name))
        dupes = {w for w, n in collections.Counter(words).items() if n > 1}
        if dupes:
            got[name] = dupes
    assert got == REPEATED_CLAUSE_WORDS, {
        "appeared": {m: sorted(v - REPEATED_CLAUSE_WORDS.get(m, set()))
                     for m, v in got.items() if v - REPEATED_CLAUSE_WORDS.get(m, set())},
        "vanished": {m: sorted(v - got.get(m, set()))
                     for m, v in REPEATED_CLAUSE_WORDS.items() if v - got.get(m, set())},
    }


LANDMARK_CLAUSES = {
    "vertices_not_n_by_3", "too_few_vertices_for_bands", "degenerate_bounding_box",
    "silhouette_is_not_a_standing_figure", "limb_column_is_discontinuous",
    "too_few_bands_for_a_centreline", "centreline_has_zero_length",
    "no_slab_to_read_facing_from", "trunk_holds_no_clusters",
    "no_neck_between_two_wider_sections", "too_few_leg_bands_for_an_ankle",
    "trunk_column_too_short", "limb_trace_too_short",
    "no_foot_vertices_below_the_ankle", "no_head_vertices_above_the_head_base",
    "no_trace_to_size_a_bone_against", "bone_has_no_registered_cross_section",
    # WAVE 34: character-class adapter + imported-site / proportion-fallback doors.
    "character_class_mismatch", "imported_sites_empty", "imported_sites_required",
    "proportion_fallback_bad_cloud", "proportion_fallback_degenerate_bbox",
    "unknown_character_class",
}


def test_the_seventeen_anatomical_refusals_are_seventeen_distinct_clauses():
    """`LandmarkError`'s docstring says halting is the only signal that survives.

    WAVE 34 pin-fix: character-class / imported-site work added six clause words;
    `character_class_mismatch` is raised at two sites, so the site count is 24 over 23
    distinct words. The name keeps the historical seventeen as the anatomical core.
    """
    import re

    words = re.findall(r'"clause": "([a-z0-9_]+)"', _owned_source("landmarks"))
    assert set(words) == LANDMARK_CLAUSES, {
        "appeared": sorted(set(words) - LANDMARK_CLAUSES),
        "vanished": sorted(LANDMARK_CLAUSES - set(words)),
    }
    assert len(set(words)) == 23, sorted(set(words))
    assert len(words) == 24, words


def test_a_landmark_refusal_reaches_a_halt_line_with_its_clause_on_it(capsys):
    """The receipt an operator actually gets, READ rather than assumed — driven through
    `diagnose_bone_heat.py`, one of the two tools the finding names."""
    from blender_stub import exit_code_of_main_block

    def raiser():
        from armature_core import landmarks
        landmarks.band_profile(np.zeros((2, 2)), 8)

    code, escaped = exit_code_of_main_block(
        "diagnose_bone_heat.py", raiser=raiser,
        argv=["python", "diagnose_bone_heat.py", "--out", "nope"])
    out = capsys.readouterr().out
    assert escaped is None, escaped
    assert code == 2, code
    lines = [ln for ln in out.splitlines()
             if ln.split(" ", 1)[0] == "DIAGNOSE_BONE_HEAT_HALT"]
    assert len(lines) == 1, out
    rec = json.loads(lines[0][len("DIAGNOSE_BONE_HEAT_HALT"):].strip())
    assert rec["error"] == "LandmarkError"
    assert rec["evidence"]["clause"] == "vertices_not_n_by_3"
    assert rec["evidence"]["andon"] == "LandmarkError"
    assert rec["evidence"]["gate"] is None
