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
    with pytest.raises(ls.LiftGate, match="may only TIGHTEN"):
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
    with pytest.raises(rc.GateSubjectDegenerate,
                       match=r"non-finite coordinate component"):
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


# =================================================================== F-244b2ad5 (HIGH)
#
# Wave 10 closed "no refusal sits between the output directory and the first byte" with a
# census whose refusal predicate keys on the callee's NAME (`gate_`/`require_` plus a typed
# list). An inline `raise` inside `main()` and a call to a module-level helper that raises
# are both invisible to it, so `stranded_refusals` returned `[]` for all 21 while ELEVEN
# tools carried refusals in exactly that window. The walk below keys on BEHAVIOUR instead.


def _module_refusals(filename):
    """Every refusal REACHED from the tool's `main()`, by behaviour, with its line.

    A refusal is an `ast.Raise` anywhere in `main`'s own body, OR a call to a module-level
    function of the same module whose body raises (resolved one hop — the shape
    `light_the_scene`, `import_subject`, `_import`, `build`, `load`, `render_arm`,
    `quadriflow`, `articulated_side` and `build_pass` all wear, and the shape the name-keyed
    predicate cannot see). The `gate_`/`require_` names the sibling census recognises are
    kept, so this walk is a SUPERSET of it and cannot report fewer refusals than it does.
    """
    src = read_source(filename)
    tree = ast.parse(src)
    module_fns = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    raisers = {name for name, node in module_fns.items()
               if any(isinstance(x, ast.Raise) for x in ast.walk(node))}
    main = module_fns.get("main")
    if main is None:
        return []
    found = set()
    for node in ast.walk(main):
        if isinstance(node, ast.Raise):
            found.add((node.lineno, "inline raise"))
        elif isinstance(node, ast.Call):
            if (isinstance(node.func, ast.Name) and node.func.id in raisers
                    and node.func.id != "main"):
                found.add((node.lineno, node.func.id))
            else:
                tail = ast.unparse(node.func).split(".")[-1]
                if tail.startswith("gate_") or tail.startswith("require_"):
                    found.add((node.lineno, tail))
    return sorted(found)


#: Measured on `89269f1` with the walk above: the eleven Blender tools whose `main()`
#: stranded a refusal between `os.makedirs` and the first byte, and what each stranded.
#: Recorded so a tool that starts stranding one fails here loudly rather than quietly.
STRANDED_ON_THE_WAVE_12_BASE = {
    "diagnose_bone_heat.py": 6, "make_binding_sheet.py": 2, "make_parts_sheet.py": 5,
    "make_rig_sheet.py": 3, "make_skeleton_sheet.py": 2, "make_test_armature.py": 1,
    "render_turnaround.py": 2, "rig_bake.py": 6, "rig_character.py": 1,
    "rig_repair.py": 3, "rig_retopo.py": 4,
}

WRITE_ORDERED_TOOLS = sorted(
    f for f in blender_stub.blender_tools()
    if os.path.isfile(os.path.join(TOOLS, f)))


#: Calls that put bytes on disk, carried verbatim from
#: `test_instruments_amend_w10.BYTE_PRODUCING_CALLS` so the two files cannot disagree.
def _is_byte_producer(node):
    import test_instruments_amend_w10 as W10
    return W10._is_byte_producer(node)


def _writes(filename, seen=None):
    """Module-level function names in `filename` whose bodies put bytes on disk.

    Resolved by BEHAVIOUR and across module boundaries: `from make_parts_sheet import
    (articulated_side, light_the_scene, ortho_camera, shoot)` brings four names in and only
    `shoot` writes. `test_instruments_amend_w10.write_window` treats every name imported
    from that module as a writer, which puts the "first byte" of `make_rig_sheet` on
    `articulated_side` — a function that reads an armature and returns a dict. That is the
    same defect one level up: a population keyed on where a name CAME FROM rather than on
    what it does.
    """
    seen = seen if seen is not None else set()
    if filename in seen:
        return set()
    seen.add(filename)
    tree = ast.parse(read_source(filename))
    module_fns = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    out = {name for name, node in module_fns.items()
           if any(_is_byte_producer(x) for x in ast.walk(node))}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        mod = (node.module or "") + ".py"
        if not os.path.isfile(os.path.join(TOOLS, mod)):
            continue
        theirs = _writes(mod, seen)
        for alias in node.names:
            if alias.name in theirs:
                out.add(alias.asname or alias.name)
    # A local function that CALLS a writer writes too (`shoot` reached through a wrapper).
    for _ in range(3):
        grew = False
        for name, node in module_fns.items():
            if name in out:
                continue
            for c in ast.walk(node):
                if (isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
                        and c.func.id in out):
                    out.add(name)
                    grew = True
                    break
        if not grew:
            break
    return out


def _window(filename):
    """`(first os.makedirs line, first byte-producing line)` in the tool's `main()`."""
    tree = ast.parse(read_source(filename))
    module_fns = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    main = module_fns.get("main")
    if main is None:
        return None, None
    writers = _writes(filename)
    byte_lines, dir_lines = [], []
    for node in ast.walk(main):
        if _is_byte_producer(node):
            byte_lines.append(node.lineno)
        elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
              and node.func.id in writers and node.func.id != "main"):
            byte_lines.append(node.lineno)
        if isinstance(node, ast.Call) and ast.unparse(node.func) == "os.makedirs":
            dir_lines.append(node.lineno)
    return (min(dir_lines) if dir_lines else None,
            min(byte_lines) if byte_lines else None)


@pytest.mark.parametrize("filename", sorted(STRANDED_ON_THE_WAVE_12_BASE))
def test_no_refusal_is_stranded_below_the_output_directory_in_any_of_the_eleven(filename):
    makedirs, first_byte = _window(filename)
    assert makedirs and first_byte, (filename, makedirs, first_byte)
    assert makedirs < first_byte, (
        f"{filename}: the output directory is created at line {makedirs}, BELOW the first "
        f"byte at {first_byte}. An inverted window makes the invariant vacuous — moving "
        f"`makedirs` past the first write is not the fix, it is the check's blind spot")
    stranded = [r for r in _module_refusals(filename) if makedirs < r[0] < first_byte]
    assert stranded == [], (
        f"{filename}: makedirs at {makedirs}, first byte at {first_byte}, refusals at "
        f"{stranded} in between — a run refused by one of those leaves an EMPTY output "
        f"directory behind, which a reader scanning `outputs/` reads as an attempt that "
        f"produced nothing rather than one that was refused")


def test_the_same_property_holds_for_every_blender_tool_not_only_the_eleven():
    """The property is the population's, not a recorded list's."""
    offenders = {}
    for filename in WRITE_ORDERED_TOOLS:
        makedirs, first_byte = _window(filename)
        if not makedirs or not first_byte:
            continue
        stranded = [r for r in _module_refusals(filename) if makedirs < r[0] < first_byte]
        if stranded:
            offenders[filename] = stranded
    assert offenders == {}, offenders


def test_the_behaviour_keyed_walk_sees_what_the_name_keyed_one_cannot(tmp_path,
                                                                     monkeypatch):
    """Rule 2 — the census is proven red on the spelling that hides from the NAME.

    `test_instrument_write_ordering._is_gate_call` recognises `gate_*`/`require_*` and a
    typed list; the probe below refuses in two ways it cannot see (an inline `raise` and a
    call to a module-level helper that raises), which is exactly the shape that left the
    eleven tools invisible to the wave-10 census.
    """
    probe = tmp_path / "probe_behaviour.py"
    probe.write_text(
        "import bpy\n"
        "import json\n"
        "import os\n"
        "def sanity(x):\n"
        "    raise ValueError('nope')\n"
        "def main():\n"
        "    os.makedirs(out, exist_ok=True)\n"
        "    if bad:\n"
        "        raise RuntimeError('inline')\n"
        "    sanity(x)\n"
        "    with open(path, 'w') as fh:\n"
        "        json.dump({}, fh)\n", encoding="utf-8")
    monkeypatch.setattr(blender_stub, "TOOLS", str(tmp_path))
    import test_instrument_write_ordering as WO
    import test_instruments_amend_w10 as W10
    monkeypatch.setattr(W10, "read_source", blender_stub.read_source, raising=False)

    src = probe.read_text(encoding="utf-8")
    named_gates, _ = WO.gate_and_write_lines(src, "probe_behaviour")
    assert named_gates == {}, (
        "the name-keyed predicate is supposed to be blind to these two spellings; if it "
        "now sees them, this fixture no longer proves what it exists to prove")
    assert [line for line, _ in _module_refusals("probe_behaviour.py")] == [9, 10]


# =================================================================== F-4d9161df (HIGH)
#
# The stale-pin gate's window is a COUNT and the sampler's origin is a CONSTANT, so the
# frames compared are not the frames the gate certified. `keyed_window` collapsed the span
# to `hi - lo + 1` and threw `lo` away; `signatures` sampled control frames 0..n-1, which
# `blender_scene.set_scene_frame` maps to SCENE frames 1..n whatever the action keys.


def _relift():
    return load_tool("check_relift.py")


def test_the_window_keeps_both_ends_of_the_keyed_span_not_only_its_length():
    mod = _relift()
    w = mod.keyed_window("a.glb", (10.0, 74.0), 65)
    assert w["keyed_frames"] == 65
    assert w["first_keyed_scene_frame"] == 10
    assert w["last_keyed_scene_frame"] == 74
    assert w["sampled_scene_frames"] == [10, 74]


def test_an_offset_action_is_sampled_over_its_own_keys_not_from_scene_frame_one():
    """The measurement that opened the finding: both GLBs key (10.0, 74.0) and `--frames=65`
    passed with the verdict "both GLBs key [10.0, 74.0] and the requested 65 frames sit
    inside it", while the sampler read scene frames 1..65 — of which 1..9 are BEFORE the
    first key and 66..74 were never read at all."""
    mod = _relift()
    w = mod.keyed_window("a.glb", (10.0, 74.0), 65)
    assert mod.scene_frames_to_sample(w) == list(range(10, 75))
    assert mod.scene_frames_to_sample(w)[0] != 1


@pytest.mark.parametrize("span", [(10.0, 74.0), (0.0, 64.0), (-5.0, 59.0), (1.0, 65.0)])
def test_the_sampled_frames_lie_inside_the_keyed_span_for_every_origin(span):
    mod = _relift()
    w = mod.keyed_window("a.glb", span, 65)
    sampled = mod.scene_frames_to_sample(w)
    assert len(sampled) == 65
    assert sampled[0] == int(span[0]) and sampled[-1] == int(span[1])


def test_the_gate_states_the_absolute_window_it_certified():
    mod = _relift()
    w = mod.keyed_window("a.glb", (10.0, 74.0), 65)
    ev = mod.gate_relift_window(w, dict(w, glb="b.glb"), 65)
    assert ev["clause"] is None
    assert ev["sampled_scene_frames"] == [10, 74]
    assert "10" in ev["verdict"] and "74" in ev["verdict"]


def test_a_request_that_would_run_off_the_end_of_an_offset_action_refuses():
    """Carried from `render_start_frame.py:441`, which checks BOTH ends of the span for
    exactly this reason: "Blender holds the nearest pose and renders it with no error"."""
    mod = _relift()
    w = mod.keyed_window("a.glb", (10.0, 40.0), 65)
    with pytest.raises(mod.ReliftWindow) as caught:
        mod.gate_relift_window(w, dict(w, glb="b.glb"), 65)
    assert caught.value.evidence["clause"] == "request_overruns_the_performance"


def test_the_gate_refuses_a_window_whose_ends_do_not_lie_inside_the_keyed_span():
    """The clause the count could not state: a window may be short enough and still sit
    outside the keys. Driven by handing the gate a window whose recorded sample range was
    not derived from its own span — the shape any future caller of `keyed_window`'s record
    could produce."""
    mod = _relift()
    w = mod.keyed_window("a.glb", (10.0, 74.0), 65)
    off = dict(w, sampled_scene_frames=[1, 65])
    with pytest.raises(mod.ReliftWindow) as caught:
        mod.gate_relift_window(off, dict(off, glb="b.glb"), 65)
    ev = caught.value.evidence
    assert ev["clause"] == "sampled_window_outside_the_keys"


def test_the_sampler_reads_the_frames_the_gate_certified(monkeypatch):
    """The two halves are the same object or the census proves nothing: `signatures` asks
    `scene_frames_to_sample` for its frames rather than `range(window['sampled'])`."""
    src = read_source("check_relift.py")
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "signatures")
    calls = [ast.unparse(n.func) for n in ast.walk(fn) if isinstance(n, ast.Call)]
    assert "scene_frames_to_sample" in calls, calls
    assert not [n for n in ast.walk(fn)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "range"], (
        "the sampler still derives its frames from a COUNT; the origin is what the finding "
        "is about, and `range(n)` cannot carry one")


# =================================================================== F-33fb7947 (MEDIUM)
#
# Both `evaluated_geometry_signature` sites measured the FILTERED shape already — the
# correctness lived in a variable binding several lines up rather than in the call — and
# neither published record said which population produced the digest.


@pytest.mark.parametrize("filename,func", [("check_relift.py", "signatures"),
                                           ("render_start_frame.py", "main")])
def test_every_signature_call_names_its_selection_at_the_call(filename, func):
    """The census keys on the CALL that reaches the measuring function, whatever it is
    named — the wave-12 rule — and asks that it state its population rather than leave that
    to a reader of the argument. `probe_subject.py:67` is the precedent, one function over
    (F-328aaea2)."""
    tree = ast.parse(read_source(filename))
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == func)
    calls = [n for n in ast.walk(fn)
             if isinstance(n, ast.Call)
             and ast.unparse(n.func).endswith("evaluated_geometry_signature")]
    assert calls, f"{filename}:{func} no longer takes a geometry signature"
    for call in calls:
        assert any(kw.arg == "scene" for kw in call.keywords), (
            f"{filename}:{func} line {call.lineno} takes a signature without saying which "
            f"population it is over; `scene=` is idempotent on an already-filtered list "
            f"and is what states the measurement")


def test_the_relift_record_names_the_population_its_digests_are_over():
    mod = _relift()
    w = mod.keyed_window("a.glb", (1.0, 8.0), 8)
    ev = mod.gate_relift_window(w, dict(w, glb="b.glb"), 8)
    assert ev["clause"] is None
    src = read_source("check_relift.py")
    assert '"signature_selection"' in src
    assert 'window["selection"] = "render_visible_meshes"' in src


def test_the_start_frame_provenance_names_the_population_of_its_pose_signature():
    src = read_source("render_start_frame.py")
    assert '"pose_signature_selection": "render_visible_meshes"' in src


# =================================================================== F-34a858f5 (MEDIUM)
#
# `--width` / `--height` are bare `type=int` with no bound and reach `SF.silhouette_extent`
# and `SF.gate_whole` unvalidated. Gate WHOLE is not walked past — the false-PASS half of
# the routed question is REFUTED, measured — but `--width=0` produces a bare untyped
# `ZeroDivisionError` from inside a shared solver module, AFTER `scene.render.resolution_x`
# has already been assigned 0.


@pytest.mark.parametrize("width,height", [(0, 480), (832, 0), (-832, 480), (0, 0)])
def test_a_non_positive_frame_size_is_refused_by_name_before_anything_is_staged(
        width, height):
    rsf = load_tool("render_start_frame.py")
    with pytest.raises(rsf.RenderGate) as exc:
        rsf.require_frame_size(width, height)
    ev = exc.value.evidence
    assert ev["gate"] == "STARTFRAME"
    assert ev["width"] == width and ev["height"] == height
    assert "positive" in str(exc.value)


def test_the_refusal_states_the_generator_legal_constraint_the_module_pins():
    """This tool's output is the conditioning image a paid generation consumes, so the
    refusal is the natural place to state the constraint rather than let an arbitrary size
    reach the render."""
    rsf = load_tool("render_start_frame.py")
    with pytest.raises(rsf.RenderGate) as exc:
        rsf.require_frame_size(831, 479)
    ev = exc.value.evidence
    assert ev["divisor"] == 16
    assert ev["module_frame"] == [rsf.WIDTH, rsf.HEIGHT]
    assert "divisible" in str(exc.value)


def test_the_module_frame_and_other_legal_sizes_are_accepted():
    """A gate that refuses everything is not a gate — 832x480 is the model family's
    documented bucket and 1280x720 is legal by the same rule."""
    rsf = load_tool("render_start_frame.py")
    assert rsf.require_frame_size(rsf.WIDTH, rsf.HEIGHT) == (rsf.WIDTH, rsf.HEIGHT)
    assert rsf.require_frame_size(1280, 720) == (1280, 720)


def test_the_refusal_fires_before_the_scene_resolution_is_assigned():
    """The residue the finding names: the ZeroDivisionError happened AFTER
    `scene.render.resolution_x = 0` was already set."""
    src = read_source("render_start_frame.py")
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "main")
    checks = [n.lineno for n in ast.walk(fn)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
              and n.func.id == "require_frame_size"]
    assigns = [n.lineno for n in ast.walk(fn)
               if isinstance(n, ast.Assign)
               and "resolution_x" in ast.unparse(n)]
    assert checks, "main no longer refuses its frame size"
    assert assigns, "main no longer assigns a render resolution"
    assert min(checks) < min(assigns), (checks, assigns)
