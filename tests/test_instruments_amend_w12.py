"""Wave-12 instruments amend — the properties the wave-12 findings name, pinned.

Every test here goes RED on the tree as it stood at `89269f1` and green after the fix in
the same commit. Helpers in this file **raise**; they never `assert` outside a test body
(`test_gate_survives_optimize.py` polices that, and `ci.yml` runs an `-O` leg).

The censuses in this file key on BEHAVIOUR, never on a callee's spelling — that is the
wave-12 rule, earned because wave 10's censuses recognised a refusal by the name
`gate_`/`require_` and could not see an inline `raise`.
"""

import ast
import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import blender_stub                                                    # noqa: E402
from blender_stub import blender_stubbed, load_tool, read_source       # noqa: E402

from armature_core import sitelist, walk                               # noqa: E402

TOOLS = blender_stub.TOOLS
REPO = os.path.dirname(TOOLS)


# --------------------------------------------------------------------------- helpers


class _Ident:
    """`mathutils.Matrix` reduced to the one thing the SPACE gates read off it."""

    @staticmethod
    def Identity(n):
        return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def _matrix(delta=0.0, nan_at=None):
    M = [[1.0 if i == j else 0.0 for j in range(4)] for i in range(4)]
    if nan_at is not None:
        M[nan_at[0]][nan_at[1]] = float("nan")
    else:
        M[0][3] = delta
    return M


class _Arm:
    def __init__(self, M):
        self.matrix_world = M


def _heads(value, n_frames=1, names=None):
    names = names if names is not None else sitelist.ALL_NAMES
    return [{n: list(value) for n in names} for _ in range(n_frames)]


NAN3 = (float("nan"),) * 3
ORIGIN = (0.0, 0.0, 0.0)


class _Bone:
    def __init__(self, p):
        self._p = p

    @property
    def matrix_local(self):
        return self

    def to_translation(self):
        return list(self._p)


class _Data:
    def __init__(self, bones):
        self.bones = bones


class _WalkArm:
    def __init__(self, heads):
        self.data = _Data({b: _Bone(heads[b]) for b in walk.GAIT_BONES})


class _Performer:
    def __init__(self, value):
        self.landmarks = {walk.HEAD_LANDMARK[b]: list(value) for b in walk.GAIT_BONES}


# =============================================================== F-524f0a25 (CRITICAL)
#
# "The arrival andon returns a full PASS on a performance made entirely of NaN."
# `nan > worst['d']` is False, so every frame is skipped and the sentinel 0.0 reaches the
# verdict line. Six sites carry the shape; each is driven below.


def test_gate_arrived_refuses_an_all_nan_performance_instead_of_passing_it():
    ls = load_tool("lift_solve.py")
    with pytest.raises(ls.LiftGate) as exc:
        ls.gate_arrived(_heads(NAN3), _heads(ORIGIN), 1.0)
    ev = exc.value.evidence
    assert ev["gate"] == "ARRIVED"
    assert "not a finite" in str(exc.value)
    assert any(isinstance(v, float) and math.isnan(v) for v in ev.values()), ev


def test_gate_arrived_still_passes_a_performance_that_actually_arrived():
    """A gate that refuses everything is not a gate."""
    ls = load_tool("lift_solve.py")
    ev = ls.gate_arrived(_heads(ORIGIN, 3), _heads(ORIGIN, 3), 1.0)
    assert ev["verdict"].startswith("max 0.000e+00 over 3 frames")
    assert ev["n_compared"] == 3 * len(sitelist.ALL_NAMES)


def test_gate_arrived_refuses_a_run_in_which_no_distance_was_compared():
    """The sentinel `worst['d'] = 0.0` is indistinguishable from a perfect arrival, so the
    gate counts the comparisons it made and refuses a non-empty population that produced
    none — the harm the NaN measurement exposed, without the NaN."""
    ls = load_tool("lift_solve.py")
    with pytest.raises(ls.LiftGate) as exc:
        ls.gate_arrived([{}], [{}], 1.0)
    assert exc.value.evidence["n_compared"] == 0


def test_gate_space_is_identity_refuses_a_nan_matrix_element(monkeypatch):
    ls = load_tool("lift_solve.py")
    monkeypatch.setattr(ls, "Matrix", _Ident)
    with pytest.raises(ls.LiftGate, match="not a finite"):
        ls.gate_space_is_identity(_Arm(_matrix(nan_at=(1, 2))))


def test_author_walk_gate_space_is_identity_refuses_a_nan_matrix_element(monkeypatch):
    aw = load_tool("author_walk.py")
    monkeypatch.setattr(aw, "Matrix", _Ident)
    with pytest.raises(aw.WalkGate, match="not a finite"):
        aw.gate_space_is_identity(_Arm(_matrix(nan_at=(0, 0))))


def test_both_space_gates_still_pass_an_identity_matrix(monkeypatch):
    ls, aw = load_tool("lift_solve.py"), load_tool("author_walk.py")
    monkeypatch.setattr(ls, "Matrix", _Ident)
    monkeypatch.setattr(aw, "Matrix", _Ident)
    assert ls.gate_space_is_identity(_Arm(_matrix()))["verdict"]
    assert aw.gate_space_is_identity(_Arm(_matrix()))["verdict"]


def test_gate_f_refuses_a_nan_disagreement_instead_of_reporting_max_zero():
    aw = load_tool("author_walk.py")
    arm = _WalkArm({b: ORIGIN for b in walk.GAIT_BONES})
    fk = [{"_heads": {b: list(NAN3) for b in walk.GAIT_BONES}}]
    heads = [{b: list(ORIGIN) for b in walk.GAIT_BONES}]
    with pytest.raises(aw.WalkGate, match="not a finite"):
        aw.gate_f_fk_agreement(fk, heads, _Performer(ORIGIN), arm, 1.0)


def test_gate_f_refuses_a_nan_input_precision_floor():
    """The floor is published beside the reading; a NaN floor is a number nothing could be
    compared against either."""
    aw = load_tool("author_walk.py")
    arm = _WalkArm({b: NAN3 for b in walk.GAIT_BONES})
    fk = [{"_heads": {b: list(ORIGIN) for b in walk.GAIT_BONES}}]
    heads = [{b: list(ORIGIN) for b in walk.GAIT_BONES}]
    with pytest.raises(aw.WalkGate, match="not a finite"):
        aw.gate_f_fk_agreement(fk, heads, _Performer(ORIGIN), arm, 1.0)


def test_gate_f_still_passes_agreeing_inputs():
    aw = load_tool("author_walk.py")
    arm = _WalkArm({b: ORIGIN for b in walk.GAIT_BONES})
    fk = [{"_heads": {b: list(ORIGIN) for b in walk.GAIT_BONES}}]
    heads = [{b: list(ORIGIN) for b in walk.GAIT_BONES}]
    ev = aw.gate_f_fk_agreement(fk, heads, _Performer(ORIGIN), arm, 1.0)
    assert ev["verdict"].startswith("max 0.000e+00")


def test_gate_a_refuses_an_all_nan_arrival():
    aw = load_tool("author_walk.py")
    authored = [{b: list(NAN3) for b in walk.GAIT_BONES} for _ in range(4)]
    reimported = [{b: list(ORIGIN) for b in walk.GAIT_BONES} for _ in range(4)]
    verts = {i: [(0.0, 0.0, 0.0)] for i in aw.mesh_sample_frames(4)}
    with blender_stubbed():
        with pytest.raises(aw.WalkGate, match="not a finite"):
            aw.gate_a_arrival(authored, reimported, verts, verts, 1.0)


def test_gate_a_refuses_a_nan_in_the_skin_clause():
    aw = load_tool("author_walk.py")
    heads = [{b: list(ORIGIN) for b in walk.GAIT_BONES} for _ in range(4)]
    frames = aw.mesh_sample_frames(4)
    good = {i: [(0.0, 0.0, 0.0)] for i in frames}
    bad = {i: [(float("nan"), 0.0, 0.0)] for i in frames}
    with blender_stubbed():
        with pytest.raises(aw.WalkGate, match="not a finite"):
            aw.gate_a_arrival(heads, heads, good, bad, 1.0)


def test_gate_p_refuses_a_nan_part_displacement():
    rp = load_tool("rig_parts.py")

    class _Vert:
        def __init__(self, co):
            self.co = co

    class _Part:
        def __init__(self, verts):
            self.data = self
            self.vertices = [_Vert(v) for v in verts]

    cube = [(0.0, 0.0, 0.0), (0.1, 0.0, 0.0)]
    at_bind = np.array([[float("nan"), 0.0, 0.0], [0.1, 0.0, 0.0]], dtype=np.float64)
    with pytest.raises(rp.GatePRestPose, match="not a finite"):
        rp.gate_p_bind_pose({"chest": _Part(cube)}, {"chest": at_bind}, 1.0)


# ================================================================ F-196c4257 (MEDIUM)
#
# Five gates took a tolerance the caller could LOOSEN, with no tightening guard. The
# repo's one implementation is `armature_core.parts.tightened`, which `armature_core.
# lift_solve.gate_round_trip` already calls.

LOOSENABLE = [
    ("lift_solve.py", "gate_arrived", "tol_frac"),
    ("lift_solve.py", "gate_space_is_identity", "tol"),
    ("author_walk.py", "gate_f_fk_agreement", "tol_frac"),
    ("author_walk.py", "gate_a_arrival", "tol_frac"),
    ("author_walk.py", "gate_space_is_identity", "tol"),
]


@pytest.mark.parametrize("filename,func,kw", LOOSENABLE)
def test_every_tolerance_keyword_in_this_domain_goes_through_the_tightening_guard(
        filename, func, kw):
    """The census keys on BEHAVIOUR — the function's own body must reach
    `parts.tightened` with this keyword — not on the keyword's spelling or its default."""
    tree = ast.parse(read_source(filename))
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == func)
    defaults = (dict(zip([a.arg for a in fn.args.args][-len(fn.args.defaults):],
                         fn.args.defaults)) if fn.args.defaults else {})
    node = defaults.get(kw)
    assert isinstance(node, ast.Constant) and node.value is None, (
        f"{filename}:{func} still defaults {kw} to a module constant rather than None; "
        f"`parts.tightened` reads None as 'use the module's own'")
    reached = [c for c in ast.walk(fn)
               if isinstance(c, ast.Call)
               and isinstance(c.func, ast.Attribute) and c.func.attr == "tightened"
               and c.args and isinstance(c.args[0], ast.Constant)
               and c.args[0].value == kw]
    assert reached, f"{filename}:{func} never routes {kw} through parts.tightened"


def test_a_looser_arrival_tolerance_is_refused_and_a_stricter_one_is_recorded():
    ls = load_tool("lift_solve.py")
    with pytest.raises(ls.LiftGate, match="may only TIGHTEN"):
        ls.gate_arrived(_heads(ORIGIN), _heads(ORIGIN), 1.0, tol_frac=1e30)
    ev = ls.gate_arrived(_heads(ORIGIN), _heads(ORIGIN), 1.0,
                         tol_frac=ls.GATE_ARRIVED_TOL_FRAC / 10.0)
    assert ev["tolerance_frac_of_diagonal"] == ls.GATE_ARRIVED_TOL_FRAC / 10.0


def test_the_nine_e_nine_displacement_that_measured_the_defect_can_no_longer_pass():
    """The finding's own measurement: `tol_frac=1e30` on a 9e9-unit displacement returned
    a PASS verdict and the manifest recorded that Gate ARRIVED ran."""
    ls = load_tool("lift_solve.py")
    with pytest.raises(ls.LiftGate):
        ls.gate_arrived(_heads((9e9, 0.0, 0.0)), _heads(ORIGIN), 1.0, tol_frac=1e30)


@pytest.mark.parametrize("filename,func,kw", LOOSENABLE)
def test_a_loosening_request_is_refused_at_every_one_of_the_five_gates(
        filename, func, kw, monkeypatch):
    mod = load_tool(filename)
    monkeypatch.setattr(mod, "Matrix", _Ident, raising=False)
    andon = mod.LiftGate if filename == "lift_solve.py" else mod.WalkGate
    fn = getattr(mod, func)
    with pytest.raises(andon, match="may only TIGHTEN"):
        if func == "gate_arrived":
            fn(_heads(ORIGIN), _heads(ORIGIN), 1.0, **{kw: 1e30})
        elif func == "gate_space_is_identity":
            fn(_Arm(_matrix()), **{kw: 1e30})
        elif func == "gate_f_fk_agreement":
            arm = _WalkArm({b: ORIGIN for b in walk.GAIT_BONES})
            fn([{"_heads": {b: list(ORIGIN) for b in walk.GAIT_BONES}}],
               [{b: list(ORIGIN) for b in walk.GAIT_BONES}],
               _Performer(ORIGIN), arm, 1.0, **{kw: 1e30})
        else:
            heads = [{b: list(ORIGIN) for b in walk.GAIT_BONES} for _ in range(4)]
            verts = {i: [(0.0, 0.0, 0.0)] for i in mod.mesh_sample_frames(4)}
            with blender_stubbed():
                fn(heads, heads, verts, verts, 1.0, **{kw: 1e30})


# =============================================================== F-940b0800 (CRITICAL)
#
# `build_pass` derived the tolerance SCALE as `float(np.linalg.norm(hi - lo))` over the raw
# imported mesh with no finiteness clause anywhere on the path, and on the skeleton route
# (`bind=False`) Gate D is the FIRST gate that sees geometry. One NaN vertex gives a NaN
# diagonal, a NaN tolerance, and a Gate D PASS whose evidence carries a 4.0-unit
# disagreement in the same dict.


def _rig_character():
    return load_tool("rig_character.py")


def test_a_subject_carrying_a_nan_vertex_is_refused_and_the_vertex_is_named():
    rc = _rig_character()
    source = np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0],
                       [float("nan"), 0.0, 0.0]], dtype=np.float64)
    with pytest.raises(rc.GateSubjectDegenerate) as exc:
        rc.subject_scale(source, "skeleton")
    ev = exc.value.evidence
    assert ev["gate"] == "SCALE"
    assert ev["n_vertices"] == 3
    assert ev["first_non_finite_vertex"]["index"] == 2
    assert ev["first_non_finite_vertex"]["axis"] == 0
    assert ev["where"] == "skeleton"


def test_a_subject_carrying_an_infinite_vertex_is_refused_too():
    rc = _rig_character()
    source = np.array([[0.0, 0.0, 0.0], [float("inf"), 1.0, 1.0]], dtype=np.float64)
    with pytest.raises(rc.GateSubjectDegenerate):
        rc.subject_scale(source, "full")


def test_an_all_coincident_subject_is_refused_because_its_diagonal_is_zero():
    """A zero diagonal is the divisor `measure_joint_balls` uses; `require_finite`'s
    default refuses zero and negatives in the same clause."""
    rc = _rig_character()
    source = np.array([[1.0, 2.0, 3.0], [1.0, 2.0, 3.0]], dtype=np.float64)
    with pytest.raises(rc.GateSubjectDegenerate, match="not a finite positive number"):
        rc.subject_scale(source, "skeleton")


def test_a_healthy_subject_still_yields_its_own_diagonal():
    """A gate that refuses everything is not a gate."""
    rc = _rig_character()
    source = np.array([[0.0, 0.0, 0.0], [1.0, 2.0, 2.0]], dtype=np.float64)
    diagonal, lo, hi = rc.subject_scale(source, "skeleton")
    assert diagonal == pytest.approx(3.0)
    assert list(lo) == [0.0, 0.0, 0.0]
    assert list(hi) == [1.0, 2.0, 2.0]


def test_no_path_in_rig_character_still_derives_a_bbox_diagonal_without_the_refusal():
    """The census keys on BEHAVIOUR — any expression in this module that takes the norm of
    a bbox span — not on the name `subject_scale`. A second, unguarded derivation is the
    defect coming back under a different spelling."""
    tree = ast.parse(read_source("rig_character.py"))
    unguarded = []
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        for node in ast.walk(fn):
            if not (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "norm"):
                continue
            seg = ast.get_source_segment(read_source("rig_character.py"), node) or ""
            if "hi - lo" in seg.replace("  ", " ") and fn.name != "subject_scale":
                unguarded.append((fn.name, node.lineno, seg))
    assert not unguarded, (
        f"a bbox diagonal is derived outside `subject_scale`, which is the only place the "
        f"finiteness refusal lives: {unguarded}")


def test_the_skeleton_route_reaches_the_refusal_before_gate_d():
    """Gate D is the first gate that sees geometry on `bind=False`, so the refusal has to
    sit in `build_pass` itself, above the landmark derivation that consumes the same
    array."""
    src = read_source("rig_character.py")
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "build_pass")
    scale_at = [n.lineno for n in ast.walk(fn)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "subject_scale"]
    consumers = [n.lineno for n in ast.walk(fn)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                 and n.func.attr in ("derive", "snap_sites_to_balls")]
    assert scale_at, "build_pass no longer routes its diagonal through subject_scale"
    assert min(scale_at) < min(consumers), (scale_at, consumers)
