"""Arm (c)'s partition rules and its four gates, driven with the inputs they exist to catch."""

import numpy as np
import pytest

from armature_core import parts
from armature_core.errors import ArmatureError, GateFailure

# A short thin bone between two fat ones — the neck, reduced to its essentials.
BONES = [
    {"name": "chest", "head": (0.0, 0.0, 0.00), "tail": (0.0, 0.0, 0.30), "parent": None},
    {"name": "neck", "head": (0.0, 0.0, 0.30), "tail": (0.0, 0.0, 0.35), "parent": "chest"},
    {"name": "head", "head": (0.0, 0.0, 0.35), "tail": (0.0, 0.0, 0.50), "parent": "neck"},
]
RADII = {"chest": 0.056, "neck": 0.020, "head": 0.050}
NAMES = [b["name"] for b in BONES]


# ------------------------------------------------------------------- face assignment


def test_plain_nearest_gives_the_neck_its_own_faces():
    """The consult's prescription, and the one that works here."""
    centroids = np.array([(0.02, 0.0, 0.32), (0.02, 0.0, 0.15), (0.02, 0.0, 0.45)])
    labels = parts.assign_faces(centroids, BONES, RADII, normalise=False)
    assert NAMES[labels[0]] == "neck"
    assert NAMES[labels[1]] == "chest"
    assert NAMES[labels[2]] == "head"


def test_normalising_squeezes_the_short_thin_bone_out_entirely():
    """The measured defect, reproduced. Dividing by each bone's own radius protects a thin
    bone from a fat NEIGHBOUR, and destroys a short thin bone BETWEEN two fat ones: on the
    performer the neck won zero of 306,110 faces this way and Gate PARTS fired."""
    # A hollow tube, not a filled cloud: this subject is a SHELL and carries no faces on
    # the limb axis. A volume-filled fixture hands the neck the on-axis points for free and
    # the squeeze never reproduces — which is what the first version of this fixture did.
    n = 4000
    z = np.linspace(0.30, 0.35, n)
    theta = np.linspace(0.0, 40.0 * np.pi, n)
    surface = 0.019                                    # the neck's own surface radius
    ring = np.stack([surface * np.cos(theta), surface * np.sin(theta), z], axis=1)
    plain = parts.assign_faces(ring, BONES, RADII, normalise=False)
    norm = parts.assign_faces(ring, BONES, RADII, normalise=True)
    assert (plain == NAMES.index("neck")).sum() > 0, "plain nearest must give the neck faces"
    assert (norm == NAMES.index("neck")).sum() == 0, (
        "fixture stale: normalisation no longer squeezes the neck out, so the regression it "
        "reproduces is gone")


def test_normalised_assignment_still_needs_a_radius_and_refuses_a_default():
    with pytest.raises(ArmatureError, match=r"no positive measured radius for "):
        parts.assign_faces(np.zeros((4, 3)), BONES, {"chest": 0.05}, normalise=True)


def test_plain_assignment_does_not_require_radii_at_all():
    labels = parts.assign_faces(np.array([(0.0, 0.0, 0.32)]), BONES, {}, normalise=False)
    assert NAMES[labels[0]] == "neck"


def test_a_malformed_centroid_array_raises():
    with pytest.raises(ArmatureError,
                       match=r"non-empty \(N, 3\) centroid array, got \(0, 3\)"):
        parts.assign_faces(np.zeros((0, 3)), BONES, RADII)
    with pytest.raises(ArmatureError,
                       match=r"non-empty \(N, 3\) centroid array, got \(5, 2\)"):
        parts.assign_faces(np.zeros((5, 2)), BONES, RADII)


# ------------------------------------------------------------------- Gate PARTS


def test_accounting_passes_on_a_clean_partition():
    labels = np.array([0, 0, 1, 2, 2])
    ev = parts.gate_parts_accounting(labels, 5, NAMES)
    assert ev["faces_per_part"] == {"chest": 2, "neck": 1, "head": 2}


def test_accounting_fires_on_a_face_assigned_to_nothing():
    """A dropped face is a hole in the character that every other gate reports green on."""
    with pytest.raises(parts.GatePartsAccounting) as exc:
        parts.gate_parts_accounting(np.array([0, -1, 1, 2, 2]), 5, NAMES)
    assert "assigned to nothing" in str(exc.value)


def test_accounting_fires_when_a_registered_part_would_be_empty():
    """The measured case: the neck with zero faces would separate into an empty object."""
    with pytest.raises(parts.GatePartsAccounting) as exc:
        parts.gate_parts_accounting(np.array([0, 0, 2, 2]), 4, NAMES)
    assert "neck" in str(exc.value)


def test_accounting_fires_when_the_label_count_does_not_match_the_face_count():
    with pytest.raises(parts.GatePartsAccounting,
                       match=r"\[PARTS\] the mesh was not partitioned cleanly into the"):
        parts.gate_parts_accounting(np.array([0, 1, 2]), 99, NAMES)


def test_accounting_fires_on_a_label_outside_the_registered_list():
    with pytest.raises(parts.GatePartsAccounting,
                       match=r"\[PARTS\] the mesh was not partitioned cleanly into the"):
        parts.gate_parts_accounting(np.array([0, 1, 2, 7]), 4, NAMES)


# ------------------------------------------------------------------- joint planes


def test_a_plane_sits_on_the_measured_ball_with_the_limb_axis_as_its_normal():
    planes = parts.joint_planes(BONES, {}, {"neck": 0.02, "head": 0.05}, RADII)
    by = {p["child"]: p for p in planes}
    assert np.allclose(by["neck"]["point"], (0.0, 0.0, 0.30))
    assert np.allclose(by["neck"]["normal"], (0.0, 0.0, 1.0))
    assert by["neck"]["radius_source"].startswith("measured")
    assert abs(by["neck"]["collar"] - 0.02 * parts.COLLAR_BALL_FRACTION) < 1e-12


def test_a_joint_with_no_ball_falls_back_and_says_so_in_the_record():
    """A fallback that looks like a measurement is the thing this repo keeps catching."""
    planes = parts.joint_planes(BONES, {}, {}, RADII)
    by = {p["child"]: p for p in planes}
    assert by["neck"]["radius_source"].startswith("FALLBACK")
    assert abs(by["neck"]["radius"] - RADII["neck"]) < 1e-12


def test_a_joint_with_neither_a_ball_nor_a_cross_section_raises():
    with pytest.raises(ArmatureError,
                       match=r"no positive radius from a ball or a cross-section"):
        parts.joint_planes(BONES, {}, {}, {"chest": 0.05})


def test_a_zero_length_child_bone_raises_because_its_plane_has_no_normal():
    bad = [dict(BONES[0]), {"name": "neck", "head": (0, 0, 0.3), "tail": (0, 0, 0.3),
                            "parent": "chest"}]
    with pytest.raises(ArmatureError, match=r"the child bone has no length"):
        parts.joint_planes(bad, {}, {}, {"chest": 0.05, "neck": 0.02})


# ------------------------------------------------------------------- collar overlap


def test_each_part_borrows_from_its_neighbour_across_the_joint():
    planes = parts.joint_planes(BONES, {}, {"neck": 0.05, "head": 0.05}, RADII)
    centroids = np.array([(0.0, 0.0, 0.32), (0.0, 0.0, 0.27), (0.0, 0.0, 0.05)])
    labels = np.array([NAMES.index("neck"), NAMES.index("chest"), NAMES.index("chest")])
    borrowed, detail = parts.collar_faces(centroids, labels, NAMES, planes)
    assert 0 in borrowed["chest"], "the chest did not reach past the joint into the neck"
    assert 1 in borrowed["neck"], "the neck did not reach back past the joint into the chest"
    assert 2 not in borrowed["neck"], "a face far from the joint was borrowed"
    assert any(d["joint"] == "chest->neck" for d in detail)


def test_a_zero_collar_borrows_nothing():
    """Without overlap, adjacent parts meet exactly at the plane and a gap opens the moment
    the joint rotates. Asserted so the collar cannot silently become decorative."""
    planes = parts.joint_planes(BONES, {}, {"neck": 0.05, "head": 0.05}, RADII,
                                collar_fraction=0.0)
    centroids = np.array([(0.0, 0.0, 0.32), (0.0, 0.0, 0.27)])
    labels = np.array([NAMES.index("neck"), NAMES.index("chest")])
    borrowed, _ = parts.collar_faces(centroids, labels, NAMES, planes)
    assert all(len(v) == 0 for v in borrowed.values())


def test_the_collar_is_bounded_by_its_own_joints_radius_not_a_shared_length():
    planes = parts.joint_planes(BONES, {}, {"neck": 0.02, "head": 0.08}, RADII)
    by = {p["child"]: p for p in planes}
    assert by["head"]["collar"] > by["neck"]["collar"] * 3.0


# ------------------------------------------------------------------- Gate RIGID


def _obs(name="a", disp=0.5, xform=0.0, pair=0.0):
    return {"name": name, "max_displacement": disp, "max_transform_error": xform,
            "max_pair_distance_change": pair, "vertices": 100}


def test_rigid_passes_when_each_part_lands_on_its_bone_transform():
    ev = parts.gate_rigid_arrival([_obs("a"), _obs("b", disp=0.0)], 1.069)
    assert ev["verdict"].startswith("2 parts")


def test_rigid_fires_when_a_part_is_not_where_its_bone_puts_it():
    with pytest.raises(parts.GateRigidArrival) as exc:
        parts.gate_rigid_arrival([_obs("elbow.L", xform=0.01)], 1.069)
    assert "elbow.L" in str(exc.value)


def test_rigid_fires_when_a_part_deforms():
    """The whole promise of this route is that nothing deforms. A part that is accidentally
    bound as well as parented still looks broadly right in a thumbnail."""
    with pytest.raises(parts.GateRigidArrival) as exc:
        parts.gate_rigid_arrival([_obs("chest", pair=0.001)], 1.069)
    assert "deforming" in str(exc.value)


def test_rigid_fires_when_nothing_arrived_at_all():
    """E03 Ruling 9's family: every other gate passes on a performance that did not happen."""
    with pytest.raises(parts.GateRigidArrival) as exc:
        parts.gate_rigid_arrival([_obs("a", disp=0.0), _obs("b", disp=0.0)], 1.069)
    assert "nothing arrived" in str(exc.value)


def test_rigid_fires_on_no_observations_rather_than_passing_vacuously():
    with pytest.raises(parts.GateRigidArrival,
                       match=r"\[RIGID\] no parts were observed under the pose; the gate"):
        parts.gate_rigid_arrival([], 1.069)


# ------------------------------------------------------------------- Gate D


def _fp(seed=0, n=50):
    rng = np.random.default_rng(seed)
    return {name: {"n_verts": n, "n_faces": n // 2,
                   "positions": np.sort(rng.uniform(-1, 1, size=(n, 3)), axis=0)}
            for name in NAMES}


def test_determinism_passes_on_two_identical_builds():
    assert parts.gate_parts_determinism(_fp(), _fp(), 1.069)["verdict"].startswith("3 parts")


def test_determinism_fires_on_a_moved_vertex_and_on_a_changed_count():
    a, b = _fp(), _fp()
    b["neck"]["positions"][3, 1] += 1e-3
    with pytest.raises(parts.GatePartsDeterminism,
                       match=r"\[D\] two builds produced different parts: neck: vertices"):
        parts.gate_parts_determinism(a, b, 1.069)

    a, c = _fp(), _fp()
    c["head"]["n_faces"] += 1
    with pytest.raises(parts.GatePartsDeterminism, match=r"\[D\] two builds produced different parts: head: 50v/25f vs"):
        parts.gate_parts_determinism(a, c, 1.069)


def test_determinism_fires_when_a_part_is_missing_from_the_second_build():
    a, b = _fp(), _fp()
    del b["neck"]
    with pytest.raises(parts.GatePartsDeterminism) as exc:
        parts.gate_parts_determinism(a, b, 1.069)
    assert "neck" in str(exc.value)


def test_the_collar_is_a_disc_around_the_joint_not_a_slab_across_the_figure():
    """The armpit blade, reproduced. A face on the far side of the body sits inside the
    plane band and must still be refused: without the radial bound the shoulder collar
    reached across the performer's torso and swept out as a flat shard when the arm moved."""
    planes = parts.joint_planes(BONES, {}, {"neck": 0.05, "head": 0.05}, RADII)
    centroids = np.array([(0.0, 0.0, 0.27),      # at the joint, just behind the plane
                          (0.6, 0.0, 0.27)])     # same band, far across the figure
    labels = np.array([NAMES.index("chest"), NAMES.index("chest")])
    borrowed, detail = parts.collar_faces(centroids, labels, NAMES, planes)
    assert 0 in borrowed["neck"], "the face at the joint should be borrowed"
    assert 1 not in borrowed["neck"], (
        "a face 0.6 from the joint axis was borrowed: the collar is still a slab")
    assert detail[0]["collar_radius"] > 0


# ------------------------------------- the vacuity family, and the receipt's own id


def test_determinism_refuses_two_empty_fingerprints_rather_than_agreeing_about_nothing():
    """F-1dd37d93. Measured: `gate_parts_determinism({}, {}, 1.0)` returned with the
    verdict "0 parts identical across two builds" and worst {"part": None, "delta": 0.0}
    — `set(a) != set(b)` is False over two empty dicts and the intersection loop never
    runs. Two functions above, `gate_rigid_arrival` refuses the identical shape and says
    why; Gate D was saved only by Gate PARTS firing earlier in a different function on a
    different pass, and `turnaround.gate_view_crop`'s docstring rules that out: a gate
    whose andon is load-bearing only in another gate's presence is not an andon."""
    with pytest.raises(parts.GatePartsDeterminism) as exc:
        parts.gate_parts_determinism({}, {}, 1.069)
    assert "check that cannot fail" in str(exc.value)
    assert exc.value.evidence["n_parts_a"] == 0
    assert exc.value.evidence["n_parts_b"] == 0


def test_determinism_refuses_one_empty_side_too():
    with pytest.raises(parts.GatePartsDeterminism) as exc:
        parts.gate_parts_determinism(_fp(), {}, 1.069)
    assert exc.value.evidence["n_parts_a"] == 3
    assert exc.value.evidence["n_parts_b"] == 0


def test_determinism_refuses_two_non_empty_builds_that_share_no_part():
    """Both sides carry parts, the set clause reports the difference — and then the
    intersection loop compares nothing, so the geometry half of this gate ran over an
    empty population. It is a raise either way today, but the evidence must say the
    comparison covered zero parts rather than leaving the reader to infer it."""
    a = _fp()
    b = {f"other_{k}": v for k, v in _fp().items()}
    with pytest.raises(parts.GatePartsDeterminism) as exc:
        parts.gate_parts_determinism(a, b, 1.069)
    assert exc.value.evidence["n_parts_compared"] == 0


def test_accounting_refuses_a_mesh_with_no_faces_and_no_registered_parts():
    """The same family as Gate D's blind spot, one function up: measured,
    `gate_parts_accounting([], 0, [])` returned green with the verdict "0 faces
    partitioned across 0 parts, each face exactly once"."""
    with pytest.raises(parts.GatePartsAccounting) as exc:
        parts.gate_parts_accounting(np.array([], dtype=int), 0, [])
    assert "check that cannot fail" in str(exc.value)


def test_every_parts_gate_carries_its_own_id_in_the_evidence_it_raises_with():
    """F-f2f42e4a. `stage_render` records the halt as one `STAGE_RENDER_HALT <json>` line
    carrying `gate` and `evidence` as separate keys (CORRECTED wave 14: the two-line
    `GATE_FAILURE` / `GATE_EVIDENCE` receipt this named was deleted with the old
    handler); measured, none of parts.py's three gates put a "gate" key in
    the evidence, while every gate in assembly.py, turnaround.py, startframe.py,
    resample.py, glb.py and lift_solve.py does. Gate id "D" is carried by two andons
    (`errors.GateDDeterminism`, `parts.GatePartsDeterminism`), so the JSON beside the
    receipt line is the only thing that can tell them apart."""
    calls = [
        ("PARTS", "GatePartsAccounting",
         lambda: parts.gate_parts_accounting(np.array([0, -1]), 2, NAMES)),
        ("RIGID", "GateRigidArrival", lambda: parts.gate_rigid_arrival([], 1.069)),
        ("D", "GatePartsDeterminism",
         lambda: parts.gate_parts_determinism({}, {}, 1.069)),
    ]
    for gate_id, cls_name, call in calls:
        with pytest.raises(GateFailure) as exc:
            call()
        ev = exc.value.evidence
        assert ev["gate"] == gate_id == exc.value.gate, f"{cls_name}: {ev.get('gate')!r}"
        assert ev["andon"] == cls_name, (
            f"{cls_name}: the id {gate_id!r} is not unique across andons, so the evidence "
            f"must name the class; got {ev.get('andon')!r}")


def test_the_parts_gates_name_their_andon_on_the_passing_path_too():
    """A receipt is written on a PASS as well, and Gate D's id is shared there too."""
    ev = parts.gate_parts_determinism(_fp(), _fp(), 1.069)
    assert ev["gate"] == "D" and ev["andon"] == "GatePartsDeterminism"
    ok = parts.gate_parts_accounting(np.array([0, 0, 1, 2, 2]), 5, NAMES)
    assert ok["gate"] == "PARTS" and ok["andon"] == "GatePartsAccounting"


# ---------------------------------------------------- Gate P raises Gate P's andon (w6)
#
# F-e0251035. The bind-pose clause raised `GateNNames` — `gate = "N"` — for a failure whose
# message says bone parenting moved the parts, whose evidence dict is `gate_p`, whose
# threshold is `rig_gates.REST_POSE_EPSILON_FRAC`, and whose result the manifest records
# under `gates.P_bind_pose`. `rig_parts.py`'s `__main__` handler reads
# `getattr(exc, "gate", None)` into `halt.json` and the printed HALT line, so the only
# machine-readable record of a wrong bone-parent inverse named the NAMES gate — sending the
# next session to `sitelist` instead of to the parent-inverse arithmetic.
#
# Family: enumerated every `raise Gate<Something>(` across `tools/*.py`. Inside this domain
# this was the only class/id mismatch; the two bare `GateFailure` raises in
# `build_lora_arm_payload.py` are builders' domain and are filed there.

from armature_core.errors import GateNNames, GatePRestPose
from blender_stub import load_tool


class _Vert:
    def __init__(self, co):
        self.co = co


class _Part:
    def __init__(self, verts):
        self.data = self
        self.vertices = [_Vert(v) for v in verts]


CUBE = [(0.0, 0.0, 0.0), (0.1, 0.0, 0.0), (0.0, 0.1, 0.0), (0.0, 0.0, 0.1)]


def _rig_parts():
    return load_tool("rig_parts.py")


def test_a_displaced_part_raises_gate_P_with_its_measurement():
    rp = _rig_parts()
    part = _Part(CUBE)
    moved = np.array(CUBE, dtype=np.float64) + np.array([0.0, 0.0, 0.5])
    with pytest.raises(GatePRestPose) as exc:
        rp.gate_p_bind_pose({"chest": part}, {"chest": moved}, 1.0)
    assert exc.value.gate == "P"
    ev = exc.value.evidence
    assert ev["gate"] == "P"
    assert ev["max_displacement"] == pytest.approx(0.5)
    assert ev["threshold"] > 0.0
    assert ev["per_part"]["chest"] == pytest.approx(0.5)
    assert ev["bbox_diagonal"] == 1.0


def test_the_bind_pose_clause_no_longer_raises_the_names_gate():
    """The red direction of the mis-typing itself: a run that used to record gate "N" for
    a parent-inverse defect must not do so any more."""
    rp = _rig_parts()
    part = _Part(CUBE)
    moved = np.array(CUBE, dtype=np.float64) + np.array([0.0, 0.0, 0.5])
    with pytest.raises(GatePRestPose) as exc:
        rp.gate_p_bind_pose({"chest": part}, {"chest": moved}, 1.0)
    assert not isinstance(exc.value, GateNNames)
    assert exc.value.gate != "N"


def test_a_part_that_did_not_move_passes_and_says_so():
    """A gate that refuses everything is not a gate."""
    rp = _rig_parts()
    part = _Part(CUBE)
    ev = rp.gate_p_bind_pose({"chest": part},
                             {"chest": np.array(CUBE, dtype=np.float64)}, 1.0)
    assert ev["gate"] == "P"
    assert ev["max_displacement"] == pytest.approx(0.0)
    assert "left every part where it was built" in ev["verdict"]


def test_the_threshold_is_a_fraction_of_the_subjects_own_diagonal():
    """A global constant must not govern a local feature: the same displacement passes on a
    large subject and fires on a small one."""
    rp = _rig_parts()
    part = _Part(CUBE)
    from armature_core import rig_gates

    d = 4.0 * rig_gates.REST_POSE_EPSILON_FRAC
    nudged = np.array(CUBE, dtype=np.float64) + np.array([0.0, 0.0, d])
    with pytest.raises(GatePRestPose,
                       match=r"\[P\] bone parenting moved the parts at the bind pose: max"):
        rp.gate_p_bind_pose({"chest": part}, {"chest": nudged}, 1.0)
    ev = rp.gate_p_bind_pose({"chest": part}, {"chest": nudged}, 100.0)
    assert ev["verdict"]


def test_no_gate_in_this_tool_raises_an_andon_whose_id_is_not_its_own():
    """The family census. Every `raise Gate<X>(` in rig_parts must name the gate the
    surrounding code is about; the evidence dict carries the id so a halt record cannot be
    ambiguous about which andon pulled."""
    import ast

    from blender_stub import read_source

    tree = ast.parse(read_source("rig_parts.py"))
    raised = {n.exc.func.id for n in ast.walk(tree)
              if isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call)
              and isinstance(n.exc.func, ast.Name)
              and n.exc.func.id.startswith("Gate")}
    assert "GatePRestPose" in raised
    assert raised <= {"GateNNames", "GatePRestPose", "GateFailure"}, raised


# --- routed family (core-gates, wave 8): a threshold the CALLER can loosen -------------


def _threshold_keyword_defaults():
    """Every gate function in `parts.py` whose signature declares a numeric tolerance
    default a caller could raise.

    Derived by AST over the module: any parameter whose name ends in `_frac`, `_tol`,
    `tol`, `eps` or `threshold` and whose default is a numeric literal. That is the shape
    core-gates removed from four rig gates in the same wave; the population here is
    whatever the source declares, not a list typed into this test.
    """
    import ast
    import inspect

    hits = []
    for node in ast.walk(ast.parse(inspect.getsource(parts))):
        if not isinstance(node, ast.FunctionDef):
            continue
        args = node.args.args + node.args.kwonlyargs
        defaults = ([None] * (len(node.args.args) - len(node.args.defaults))
                    + list(node.args.defaults) + list(node.args.kw_defaults))
        for arg, default in zip(args, defaults):
            name = arg.arg
            looks_like_tolerance = (name.endswith(("_frac", "_tol", "tol", "eps"))
                                    or "threshold" in name)
            if (looks_like_tolerance and isinstance(default, ast.Constant)
                    and isinstance(default.value, (int, float))
                    and not isinstance(default.value, bool)):
                hits.append((node.name, name, default.value))
    return hits


def test_no_gate_here_takes_a_loosenable_tolerance_default():
    """Census. `gate_rigid_arrival(epsilon_frac=1e-4, rigidity_frac=1e-5)` and
    `gate_parts_determinism(length_frac=1e-6)` declared the tolerance as a caller argument
    — the shape `assembly.gate_slot_ceiling` already refuses for `cap`: a bound the caller
    supplies is a bound the caller can raise. Neither production site passed one
    (`rig_parts.py:490` and `:503` both take the defaults), so the freedom bought nothing
    and only the loosening direction was unbounded.
    """
    assert _threshold_keyword_defaults() == [], _threshold_keyword_defaults()


def test_the_threshold_census_goes_red_on_a_reintroduced_default():
    """Prove it can fail: the same walk over a source that declares one."""
    import ast

    mutated = "def gate_x(a, b, length_frac=1e-6):\n    return a\n"
    hits = []
    for node in ast.walk(ast.parse(mutated)):
        if isinstance(node, ast.FunctionDef):
            for arg, default in zip(node.args.args[-len(node.args.defaults):],
                                    node.args.defaults):
                if arg.arg.endswith("_frac") and isinstance(default, ast.Constant):
                    hits.append((node.name, arg.arg, default.value))
    assert hits == [("gate_x", "length_frac", 1e-6)]


def test_the_module_owns_the_tolerances_and_a_caller_may_only_tighten():
    ev = parts.gate_rigid_arrival([_obs("a"), _obs("b", disp=0.0)], 1.069)
    assert ev["transform_frac"] == parts.RIGID_TRANSFORM_FRAC
    assert ev["rigidity_frac"] == parts.RIGID_RIGIDITY_FRAC
    tighter = parts.gate_rigid_arrival([_obs("a")], 1.069,
                                       epsilon_frac=parts.RIGID_TRANSFORM_FRAC / 10.0)
    assert tighter["transform_frac"] < parts.RIGID_TRANSFORM_FRAC

    ev = parts.gate_parts_determinism(_fp(), _fp(), 1.069)
    assert ev["length_frac"] == parts.DETERMINISM_LENGTH_FRAC
    assert parts.gate_parts_determinism(
        _fp(), _fp(), 1.069,
        length_frac=parts.DETERMINISM_LENGTH_FRAC / 10.0)["length_frac"] < \
        parts.DETERMINISM_LENGTH_FRAC


def test_a_caller_that_loosens_a_tolerance_is_refused_by_each_gate():
    """Both directions, on both gates. A gate whose tolerance grows with the deviation it
    is measuring cannot see the deviation."""
    with pytest.raises(parts.GateRigidArrival, match=r"may only TIGHTEN") as exc:
        parts.gate_rigid_arrival([_obs("a")], 1.069,
                                 epsilon_frac=parts.RIGID_TRANSFORM_FRAC * 10.0)
    assert exc.value.evidence["module_transform_frac"] == parts.RIGID_TRANSFORM_FRAC

    with pytest.raises(parts.GateRigidArrival, match=r"may only TIGHTEN"):
        parts.gate_rigid_arrival([_obs("a")], 1.069,
                                 rigidity_frac=parts.RIGID_RIGIDITY_FRAC * 10.0)

    with pytest.raises(parts.GatePartsDeterminism, match=r"may only TIGHTEN") as exc:
        parts.gate_parts_determinism(_fp(), _fp(), 1.069,
                                     length_frac=parts.DETERMINISM_LENGTH_FRAC * 10.0)
    assert exc.value.evidence["module_length_frac"] == parts.DETERMINISM_LENGTH_FRAC


def test_the_loosened_tolerance_would_have_hidden_a_real_difference():
    """What the freedom actually bought: the deviation the default catches, waved through
    by a fraction ten times larger — which is why the gate has to own it."""
    a = _fp()
    b = _fp()
    b["chest"]["positions"] = [[v + 1e-5 for v in p] for p in b["chest"]["positions"]]
    with pytest.raises(parts.GatePartsDeterminism, match=r"vertices differ"):
        parts.gate_parts_determinism(a, b, 1.069)


# ------------------------------------------------------- wave 10: the two ways past the
# ------------------------------------------------------- "may only TIGHTEN" guard




# ------------------------------------------------------- wave 12 (F-2a564189): the two
# ------------------------------------------------------- obligations `tightened` conflated
#
# `tightened` called `require_finite` with the `positive=True` default, so `requested=0.0`
# — exact match, the one value that is unambiguously NOT a loosening — was refused, and
# refused quoting `require_finite`'s NaN paragraph, none of which is true of a number that
# compares correctly in both directions. Measured on the wave-12 base against
# `owned = 1e-4`: 1e-30 accepted, 1e-4 accepted, 1e-3 refused as a loosening (correct), 0.0
# refused as "not a finite positive number". The same refusal reached every public gate
# importing the helper. So the sweeps below are split: NON-FINITE keeps
# "not a finite number", NEGATIVE gets its own "admits nothing" clause, and ZERO is
# accepted as the tightest legal request. A quantity that is a LENGTH SCALE
# (`bbox_diagonal`, `diagonal`) keeps `positive=True` and still refuses zero.


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf"), -1.0])
@pytest.mark.parametrize("keyword", ["epsilon_frac", "rigidity_frac"])
def test_rigid_refuses_a_tolerance_that_is_not_a_finite_number_or_is_negative(keyword,
                                                                             bad):
    """F-e982d505, half (1). `_tightened` refused on `value > owned`, and `nan > 1e-4` is
    False — so a NaN was accepted AS A TIGHTENING and every comparison below it then read
    False in both directions. Measured before the fix: `gate_rigid_arrival([_obs('a',
    xform=1e-3, pair=0.0, disp=0.5)], 1.0, epsilon_frac=float('nan'))` RETURNED, with
    `transform_tolerance` nan and the verdict '1 parts each landed on their own bone
    transform', where the same call at the module default raises. Zero and negative are the
    same door one step further: they are not above the owned value either.
    """
    want = r"admits nothing" if bad == bad and bad < 0 and bad != float("-inf")         else r"not a finite number|admits nothing"
    with pytest.raises(parts.GateRigidArrival, match=want) as exc:
        parts.gate_rigid_arrival([_obs("a", xform=1e-3)], 1.0, **{keyword: bad})
    ev = exc.value.evidence
    assert "verdict" not in ev
    assert ev["gate"] == "RIGID" and ev["andon"] == "GateRigidArrival"
    assert repr(ev[keyword]) == repr(float(bad))


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1.0])
def test_determinism_refuses_a_length_fraction_that_is_not_a_number_or_is_negative(bad):
    """The same door on Gate D. Measured before the fix: `gate_parts_determinism(a, b, 1.0,
    length_frac=float('nan'))` returned the verdict '3 parts identical across two builds'
    while its own evidence recorded a `worst` delta far above the module's tolerance."""
    a, b = _fp(), _fp()
    b["chest"]["positions"] = [[v + 99.0 for v in p] for p in b["chest"]["positions"]]
    with pytest.raises(parts.GatePartsDeterminism,
                       match=r"not a finite number|admits nothing") as exc:
        parts.gate_parts_determinism(a, b, 1.0, length_frac=bad)
    assert "verdict" not in exc.value.evidence
    assert exc.value.evidence["gate"] == "D"


def test_zero_is_the_tightest_legal_request_and_is_accepted_by_gate_d():
    """Wave 12, F-2a564189. `length_frac=0.0` on Gate D means "two builds must be
    byte-identical", the strictest reading of the gate — and it was refused with a message
    saying the number could not be compared, whose only remedy is to loosen. The guard was
    producing the loosening it exists to prevent."""
    ev = parts.gate_parts_determinism(_fp(), _fp(), 1.0, length_frac=0.0)
    assert ev["gate"] == "D" and ev["length_frac"] == 0.0


def test_zero_is_accepted_as_a_bound_by_gate_rigid_and_still_binds():
    """Accepted, not certified: at zero tolerance an arrival 1e-3 off its bone transform
    fires the gate on the RESIDUAL, and the message is the arrival defect rather than
    `require_finite`'s NaN paragraph quoted at a number that compares correctly."""
    with pytest.raises(parts.GateRigidArrival) as exc:
        parts.gate_rigid_arrival([_obs("a", xform=1e-3)], 1.0, epsilon_frac=0.0)
    assert "did not arrive whole" in str(exc.value)
    assert "not a finite" not in str(exc.value)
    assert exc.value.evidence["transform_frac"] == 0.0
    # And a clean arrival clears it at the same zero bound.
    ev = parts.gate_rigid_arrival([_obs("a", xform=0.0, pair=0.0, disp=0.5)], 1.0,
                                  epsilon_frac=0.0)
    assert ev["gate"] == "RIGID"


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf"), 0.0, -1.0])
def test_both_gates_refuse_a_bbox_diagonal_that_cannot_scale_a_tolerance(bad):
    """F-e982d505, half (2). `bbox_diagonal` multiplies every tolerance in this module and
    was not checked at all. Measured before the fix on an observation set that raises at
    bbox_diagonal 1.0: at 1e6 the gate PASSED with transform_tolerance 100.0, and at nan it
    PASSED with transform_tolerance nan — so the loosening direction wave 8 closed on
    `epsilon_frac` stayed fully open one argument over, and `rig_parts.py` passes this one
    from a measurement (`ctx['diagonal']`) rather than from a constant.

    A merely LARGE diagonal (1e6, the wrong-units case) is deliberately NOT in this sweep
    and is pinned as passing two tests below: a subject really can be metres across, this
    module cannot know the caller's units, and a guard that refused "big" would be a
    different defect wearing this one's name.
    """
    obs = [_obs("a", xform=1e-3)]
    with pytest.raises(parts.GateRigidArrival, match=r"not a finite positive") as exc:
        parts.gate_rigid_arrival(obs, bad)
    assert "verdict" not in exc.value.evidence
    assert repr(exc.value.evidence["bbox_diagonal"]) == repr(float(bad))

    a, b = _fp(), _fp()
    b["chest"]["positions"] = [[v + 99.0 for v in p] for p in b["chest"]["positions"]]
    with pytest.raises(parts.GatePartsDeterminism, match=r"not a finite positive"):
        parts.gate_parts_determinism(a, b, bad)


def test_the_same_inputs_still_raise_at_the_module_default():
    """The companion the sweep above needs, or it could pass on a gate that never fires."""
    with pytest.raises(parts.GateRigidArrival, match=r"did not arrive whole"):
        parts.gate_rigid_arrival([_obs("a", xform=1e-3)], 1.0)
    a, b = _fp(), _fp()
    b["chest"]["positions"] = [[v + 99.0 for v in p] for p in b["chest"]["positions"]]
    with pytest.raises(parts.GatePartsDeterminism, match=r"vertices differ"):
        parts.gate_parts_determinism(a, b, 1.0)


def test_a_bbox_diagonal_that_is_merely_large_is_not_refused_for_being_unusual():
    """The guard bounds non-finite and non-positive, not "big" — a subject really can be
    metres across, and a gate that refused that would be a different defect."""
    assert parts.gate_rigid_arrival([_obs("a")], 12.5)["verdict"].startswith("1 parts")


# ------------------------------------------------- wave 10: Gate D on a zero-vertex part


def test_determinism_refuses_a_zero_vertex_part_in_its_own_words():
    """F-03955683. `np.abs(...).max()` over an empty array raises `ValueError: zero-size
    array to reduction operation maximum which has no identity` — untyped, so it carries no
    gate id, no evidence and no andon name, and the halt contract records it as 'FAILED — an
    unhandled error' rather than as Gate D firing. A delta of 0.0 over a part with no
    geometry would be the other wrong answer: it would read as agreement.
    """
    empty = {"n_verts": 0, "n_faces": 0, "positions": np.zeros((0, 3))}
    with pytest.raises(parts.GatePartsDeterminism) as exc:
        parts.gate_parts_determinism({"p": empty}, {"p": dict(empty)}, 1.0)
    ev = exc.value.evidence
    assert ev["gate"] == "D" and ev["andon"] == "GatePartsDeterminism"
    assert ev["empty_parts"] == ["p"]
    assert "verdict" not in ev


def test_the_zero_vertex_refusal_is_not_the_numpy_error_wearing_a_gate_name():
    """The fixture that would pass if the code merely propagated numpy's error: assert the
    class AND that the message is this module's, not the reduction's."""
    empty = {"n_verts": 0, "n_faces": 0, "positions": np.zeros((0, 3))}
    with pytest.raises(parts.GatePartsDeterminism) as exc:
        parts.gate_parts_determinism({"p": empty}, {"p": dict(empty)}, 1.0)
    assert "zero-size array" not in str(exc.value)
    assert isinstance(exc.value, GateFailure)


def test_a_part_with_geometry_beside_an_empty_one_still_names_the_empty_one():
    a = _fp()
    b = _fp()
    a["void"] = {"n_verts": 0, "n_faces": 0, "positions": np.zeros((0, 3))}
    b["void"] = {"n_verts": 0, "n_faces": 0, "positions": np.zeros((0, 3))}
    with pytest.raises(parts.GatePartsDeterminism) as exc:
        parts.gate_parts_determinism(a, b, 1.069)
    assert exc.value.evidence["empty_parts"] == ["void"]


# ------------------------------------------------- wave 10: the one finite-number helper


def test_require_finite_writes_the_offending_value_into_the_caller_s_own_evidence():
    """The helper the four gate modules share (`startframe`, `resample`, `lift_solve` and
    this one), rather than four copies of `math.isfinite`. It raises the CALLER's andon
    class, so each module keeps its own gate id."""
    ev = {"gate": "RIGID"}
    with pytest.raises(parts.GateRigidArrival) as exc:
        parts.require_finite("x", float("nan"), parts.GateRigidArrival, ev)
    assert exc.value.evidence["x"] != exc.value.evidence["x"]      # NaN is not itself
    assert parts.require_finite("x", 0.0, parts.GateRigidArrival, ev,
                                positive=False) == 0.0
    with pytest.raises(parts.GateRigidArrival, match=r"not a finite positive number"):
        parts.require_finite("x", 0.0, parts.GateRigidArrival, ev)
    with pytest.raises(parts.GateRigidArrival, match=r"not a finite number"):
        parts.require_finite("x", float("inf"), parts.GateRigidArrival, ev, positive=False)


# ------------------------------------------------- wave 22: the coercion above the guard
#
# F-fda74b87. `v = float(value)` ran ABOVE `if not math.isfinite(v)`, so the ONE
# implementation of wave 10's rule 4 was broken in one class of the case it exists for: a
# value that is not a real number left the helper as an untyped `TypeError`, which the
# 21-tool halt contract records as exit 1 "FAILED - an unhandled error" where a typed
# refusal at exit 2 belongs. The file records the identical defect being caught by its own
# test 300 lines below, at `joint_planes`.


@pytest.mark.parametrize("raw", [None, [], {}, object(), "wide", (1.0,)])
def test_require_finite_refuses_an_unreadable_operand_in_the_caller_s_family(raw):
    """The direction the guard did not bound: not a BAD number, but not a number at all."""
    ev = {"gate": "RIGID"}
    with pytest.raises(parts.GateRigidArrival) as exc:
        parts.require_finite("x", raw, parts.GateRigidArrival, ev)
    assert isinstance(exc.value, ArmatureError)
    assert repr(raw) in str(exc.value), "the halt line must name the raw value"
    assert exc.value.evidence["x_raw"] == repr(raw)
    assert exc.value.evidence["x"] != exc.value.evidence["x"]        # coerced to NaN


def test_no_importer_of_the_helper_can_exit_the_family_on_an_unreadable_operand():
    """The siblings the finding enumerated, driven through their own front doors: three
    andons on the start-frame and turnaround routes whose input is a MEASUREMENT read back
    from a record, where `null` is the ordinary JSON shape of a measurement nobody took."""
    from armature_core import startframe, turnaround

    with pytest.raises(ArmatureError, match=r"transparent_fraction=None is not a number"):
        turnaround.gate_view_alpha(0, 0, 255, None)
    with pytest.raises(ArmatureError, match=r"void_vs_plate_255=None is not a number"):
        startframe.gate_backdrop(None, 10.0, 0.5, "why", 1.0, 5.0)
    with pytest.raises(ArmatureError, match=r"height=None is not a number"):
        startframe.gate_whole({"x0": 1.0, "x1": 2.0, "y0": 1.0, "y1": 2.0},
                              64, None, 4)


# ------------------------------------ wave 22: Gate D's seeded extremum behind a strict >
#
# F-cfb560aa. `worst = {"part": None, "delta": 0.0}` and BOTH readings of the per-part
# distance are strict `>`, which a NaN fails in both directions - so Gate D returned its
# strongest verdict, "N parts identical across two builds", over a build carrying a
# non-finite vertex position. `+inf` refused already; the sign-free direction did not.


def test_determinism_refuses_a_non_finite_vertex_rather_than_certifying_agreement():
    a, b = _fp(), _fp()
    b["neck"]["positions"][3, 1] = float("nan")
    with pytest.raises(parts.GatePartsDeterminism) as exc:
        parts.gate_parts_determinism(a, b, 1.069)
    assert exc.value.evidence["delta.neck"] != exc.value.evidence["delta.neck"]
    assert exc.value.gate == "D"


@pytest.mark.parametrize("bad", [float("inf"), float("-inf")])
def test_determinism_refuses_both_infinities_by_the_same_clause(bad):
    """The sibling that refused by ACCIDENT (`inf > tol`) now refuses by name, and the
    negative one - which `d > tol` reads as agreement after `np.abs` only because the
    absolute value happens to be `+inf` - takes the same door."""
    a, b = _fp(), _fp()
    b["head"]["positions"][2, 0] = bad
    with pytest.raises(parts.GatePartsDeterminism) as exc:
        parts.gate_parts_determinism(a, b, 1.069)
    assert "delta.head" in exc.value.evidence


def test_determinism_still_passes_and_still_fires_on_a_real_displacement():
    """The arm can still move in both directions: the sweep is not a check that always
    fires."""
    assert parts.gate_parts_determinism(_fp(), _fp(), 1.069)["verdict"].startswith("3 parts")
    a, b = _fp(), _fp()
    b["neck"]["positions"][3, 1] += 1e-3
    with pytest.raises(parts.GatePartsDeterminism, match=r"vertices differ by up to"):
        parts.gate_parts_determinism(a, b, 1.069)
