"""Core-solvers pins graduated from test_amend_w35_core_solvers (wave 37).

Wave-35 feature-execute: core-solvers MEDIUM findings (reverted-red proofs).
Left the amend glob via GRADUATION_PATH.
"""

import json
import math

import numpy as np
import pytest

from armature_core import (
    aapose, assembly, binding, channels, lift_solve, posearc, sitelist, turnaround,
)
from armature_core.errors import ArmatureError, GateFailure, SpecError

W35_NEW_CLAUSES = (
    "audio_class_without_allowlist",
    "binding_arm_unimplemented",
    "body_confidence_unreadable",
    "body_from_sites_wrong_shape",
    "body_site_too_short",
    "canny_bad_shape",
    "elevation_not_finite",
    "elevations_length_mismatch",
    "elevations_not_a_sequence",
    "flow_bad_shape",
    "flow_max_mag_not_finite_and_positive",
    "hands_from_sites_bad_columns",
    "heat_power_out_of_bounds",
    "imported_weights_length_mismatch",
    "imported_weights_missing_bone",
    "imported_weights_negative",
    "imported_weights_not_finite",
    "imported_weights_required",
    "imported_weights_sum_not_one",
    "motion_record_extra_key_collision",
    "motion_record_unreadable",
    "motion_schema_too_new",
    "motion_schema_unreadable",
    "optional_landmark_missing_from_rest",
    "softedge_bad_shape",
    "unknown_binding_character_class",
    "unknown_channel_convention",
    "unknown_pose_arc_axis",
    "view_list_revisits_a_direction",
)


def test_w35_new_clauses_are_spelled_for_the_vocabulary_census():
    assert len(W35_NEW_CLAUSES) == 29
    assert "motion_schema_too_new" in W35_NEW_CLAUSES
    assert "audio_class_without_allowlist" in W35_NEW_CLAUSES


def _identity_local():
    I = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    return {name: [row[:] for row in I] for name in sitelist.ALL_NAMES}


# --------------------------------------------------------- F-08663836 motion_record I/O

def test_f08663836_dump_save_load_roundtrip(tmp_path):
    frames = [
        {"frame": 0, "local": _identity_local(), "root": [0.0, 0.0, 0.0]},
        {"frame": 1, "local": _identity_local(), "root": [0.1, 0.0, 0.0]},
    ]
    path = tmp_path / "clip.motion.json"
    written = lift_solve.save_motion_record(str(path), frames, tool="test")
    assert written["motion_schema"] == lift_solve.MOTION_SCHEMA
    loaded = lift_solve.load_motion_record(str(path))
    assert loaded["motion_schema"] == lift_solve.MOTION_SCHEMA
    assert len(loaded["frames"]) == 2
    assert loaded["frames"][1]["root"] == [0.1, 0.0, 0.0]


def test_f08663836_load_refuses_schema_too_new(tmp_path):
    path = tmp_path / "future.motion.json"
    path.write_text(json.dumps({
        "motion_schema": lift_solve.MOTION_SCHEMA + 1,
        "frames": [{"frame": 0, "local": _identity_local(), "root": [0, 0, 0]}],
    }), encoding="utf-8")
    with pytest.raises(GateFailure, match="newer than this consumer") as ei:
        lift_solve.load_motion_record(str(path))
    assert ei.value.evidence["clause"] == "motion_schema_too_new"


def test_f08663836_load_refuses_missing_bone(tmp_path):
    local = _identity_local()
    del local["hips"]
    path = tmp_path / "gap.motion.json"
    path.write_text(json.dumps({
        "motion_schema": 1,
        "frames": [{"frame": 0, "local": local, "root": [0, 0, 0]}],
    }), encoding="utf-8")
    with pytest.raises(GateFailure) as ei:
        lift_solve.load_motion_record(str(path))
    assert ei.value.evidence["clause"] == "frame_is_missing_a_bone"


# ----------------------------------------------- F-2ad2d7cf assembly audio mux stance

def test_f2ad2d7cf_audio_mux_stance_is_out_of_band():
    assert assembly.OPTIONAL_AUDIO_CLASSES == ()
    assert assembly.AUDIO_MUX_STANCE["product"] == "out_of_band_mux"
    assert assembly.AUDIO_MUX_STANCE["in_graph_audio"] is False
    assert "silent" in assembly.AUDIO_MUX_STANCE["disclosure"].lower()


def test_f2ad2d7cf_topology_refuses_unallowlisted_audio_class():
    graph = {
        "0": {"class_type": "LoadImage", "inputs": {"image": "a.png"}},
        "1": {"class_type": "LoadImage", "inputs": {"image": "b.png"}},
        "2": {"class_type": "BatchImagesNode",
              "inputs": {"images.image0": ["0", 0], "images.image1": ["1", 0]}},
        "3": {"class_type": "CreateVideo", "inputs": {"images": ["2", 0], "fps": 16}},
        "4": {"class_type": "SaveVideo", "inputs": {"video": ["3", 0]}},
        "5": {"class_type": "LoadAudio", "inputs": {"audio": "x.wav"}},
    }
    with pytest.raises(GateFailure) as ei:
        assembly.gate_batch_topology(
            graph, 2, "2", "3", "4", expected_sources=["0", "1"])
    assert "audio_class_without_allowlist" in ei.value.evidence["clauses"]


def test_f2ad2d7cf_silent_chain_records_stance_on_pass():
    graph = {
        "0": {"class_type": "LoadImage", "inputs": {"image": "a.png"}},
        "1": {"class_type": "LoadImage", "inputs": {"image": "b.png"}},
        "2": {"class_type": "BatchImagesNode",
              "inputs": {"images.image0": ["0", 0], "images.image1": ["1", 0]}},
        "3": {"class_type": "CreateVideo", "inputs": {"images": ["2", 0], "fps": 16}},
        "4": {"class_type": "SaveVideo", "inputs": {"video": ["3", 0]}},
    }
    ev = assembly.gate_batch_topology(
        graph, 2, "2", "3", "4", expected_sources=["0", "1"])
    assert ev["audio_mux_stance"]["product"] == "out_of_band_mux"
    assert "silent VIDEO" in ev["verdict"]


# --------------------------------------------- F-2b26bedc aapose body/hands_from_sites

def _site_table():
    # Minimal world sites covering required_sites(); numbers are arbitrary.
    out = {}
    for i, name in enumerate(aapose.required_sites()):
        out[name] = (float(i) * 0.01, 0.5, 1.0 - i * 0.001)
    return out


def test_f2b26bedc_body_from_sites_shape_and_order():
    sites = _site_table()
    body = aapose.body_from_sites(sites, conf=0.9)
    assert body.shape == (20, 3)
    assert body[0, 2] == pytest.approx(0.9)
    assert list(body[0, :2]) == pytest.approx(list(sites["nose"][:2]))


def test_f2b26bedc_hands_from_sites_mitten():
    sites = _site_table()
    left, right, prov = aapose.hands_from_sites(sites, hand_mode="mitten")
    assert left.shape == (21, 3) and right.shape == (21, 3)
    assert prov["left"]["hand_mode"] == "mitten"
    assert prov["right"]["provenance"].startswith("CONSTRUCTED")


# ------------------------------------------------- F-31bce024 turnaround elevations

def test_f31bce024_projection_plan_records_elevations():
    plan = turnaround.projection_plan(
        False, 50.0, 36.0, elevations=[0.0, 30.0, -20.0, 10.0], n_views=4)
    assert plan["elevations_deg"] == [0.0, 30.0, -20.0, 10.0]


def test_f31bce024_compose_view_list_and_revisit_refusal():
    az = turnaround.orbit_azimuths(4, 0, 360)
    views = turnaround.compose_view_list(az, [0, 15, -15, 30])
    assert len(views) == 4
    assert views[1]["elevation_deg"] == 15.0
    # Same (az mod 360, el) twice — refuse on the plan.
    with pytest.raises(GateFailure) as ei:
        turnaround.compose_view_list([0.0, 360.0], [10.0, 10.0])
    assert ei.value.evidence["clause"] == "view_list_revisits_a_direction"


def test_f31bce024_default_plan_keeps_elevations_none():
    plan = turnaround.projection_plan(False, 50.0, 36.0)
    assert plan["elevations_deg"] is None


# --------------------------------------------------------- F-72d73808 posearc table

def test_f72d73808_arcs_are_data_and_resolve_closed():
    assert "elbow_r_bend" in posearc.POSE_ARCS
    assert "spine_lean" in posearc.POSE_ARCS
    assert "arm_l_raise" in posearc.POSE_ARCS
    for name in ("arm_r_raise", "arm_l_raise", "elbow_r_bend", "spine_lean"):
        arc = posearc.resolve_arc(name)
        assert "pivot" in arc and "axis" in arc and "sign" in arc
        assert "moving_parts" in arc
    with pytest.raises(SpecError) as ei:
        posearc.resolve_arc("not_an_arc")
    assert ei.value.evidence["clause"] == "unknown_pose_arc"


def test_f72d73808_elbow_bend_endpoint_pinned():
    joints = {
        "elbow_r": (0.25, 0.0, 0.82),
        "wrist_r": (0.40, 0.0, 0.82),
        "shoulder_r": (0.09, 0.0, 0.82),
    }
    arc = posearc.POSE_ARCS["elbow_r_bend"]
    _, end = posearc.joints_at_frame(joints, arc, 16, 17, 0.0, 90.0)
    # +90 about +X through elbow: wrist was +X of elbow in the XZ plane at same Y;
    # after R_x(90): (dx, dy, dz)=(0.15,0,0) -> (0.15, 0, 0) wait — dx stays, dy/dz rotate.
    # (0.15, 0, 0) about X is unchanged. Need a z offset for a visible bend.
    joints2 = {
        "elbow_r": (0.25, 0.0, 0.82),
        "wrist_r": (0.25, 0.0, 0.67),  # straight down the forearm in -Z
        "shoulder_r": (0.09, 0.0, 0.82),
    }
    _, end = posearc.joints_at_frame(joints2, arc, 16, 17, 0.0, 90.0)
    # R_x(+90): (0,0,-0.15) -> (0, 0.15, 0) relative to elbow.
    assert end["wrist_r"][0] == pytest.approx(0.25, abs=1e-9)
    assert end["wrist_r"][1] == pytest.approx(0.15, abs=1e-9)
    assert end["wrist_r"][2] == pytest.approx(0.82, abs=1e-9)
    assert end["elbow_r"] == pytest.approx(joints2["elbow_r"], abs=1e-12)


# --------------------------------------- F-96d82898 optional mid-torso / held vs solved

def _rest_obs_minimal():
    """Enough sites for a default (held spine/neck) solve_frame call."""
    sites = {
        "hip_L": (-0.1, 0.0, 0.9), "hip_R": (0.1, 0.0, 0.9),
        "crotch": (0.0, 0.0, 0.9),
        "spine_base": (0.0, 0.0, 1.0), "chest_base": (0.0, 0.0, 1.2),
        "neck_base": (0.0, 0.0, 1.35), "head_base": (0.0, 0.0, 1.45),
        "head_top": (0.0, 0.0, 1.6),
        "shoulder_L": (-0.2, 0.0, 1.35), "shoulder_R": (0.2, 0.0, 1.35),
        "elbow_L": (-0.4, 0.0, 1.35), "elbow_R": (0.4, 0.0, 1.35),
        "wrist_L": (-0.55, 0.0, 1.35), "wrist_R": (0.55, 0.0, 1.35),
        "hand_end_L": (-0.65, 0.0, 1.35), "hand_end_R": (0.65, 0.0, 1.35),
        "knee_L": (-0.1, 0.0, 0.5), "knee_R": (0.1, 0.0, 0.5),
        "ankle_L": (-0.1, 0.0, 0.1), "ankle_R": (0.1, 0.0, 0.1),
        "toe_L": (-0.1, 0.1, 0.05), "toe_R": (0.1, 0.1, 0.05),
        "nose": (0.0, 0.05, 1.5),
        "ear_L": (-0.08, 0.0, 1.5), "ear_R": (0.08, 0.0, 1.5),
        "eye_L": (-0.03, 0.04, 1.52), "eye_R": (0.03, 0.04, 1.52),
        "nose_tip": (0.0, 0.07, 1.5),
        "eye_L_tip": (-0.03, 0.05, 1.52), "eye_R_tip": (0.03, 0.05, 1.52),
        "ear_L_tip": (-0.1, 0.0, 1.5), "ear_R_tip": (0.1, 0.0, 1.5),
        "shoulder_line": (0.0, 0.0, 1.35),
    }
    return sites, dict(sites)


def test_f96d82898_default_holds_spine_and_neck():
    rest, obs = _rest_obs_minimal()
    solved = lift_solve.solve_frame(rest, obs)
    assert "spine" in solved["held"]
    assert "neck" in solved["held"]
    assert "spine" not in solved["solved"]
    assert "chest" in solved["solved_bones"]
    assert solved["optional_landmarks_used"] == []


def test_f96d82898_mid_torso_unlocks_spine():
    rest, obs = _rest_obs_minimal()
    rest["mid_torso"] = (0.0, 0.0, 1.1)
    obs["mid_torso"] = (0.05, 0.0, 1.1)  # slight lean
    solved = lift_solve.solve_frame(rest, obs)
    assert "spine" in solved["solved"]
    assert "spine" not in solved["held"]
    assert "mid_torso" in solved["optional_landmarks_used"]
    assert "spine" in solved["solved_bones"]


# --------------------------------------------- F-a4aeb565 binding alternate arms

def test_fa4aeb565_rigid_remains_default_for_mannequin():
    assert binding.resolve_binding("mannequin_balls") == "rigid_segment_weights"


def test_fa4aeb565_imported_weights_validator():
    bones = [
        {"name": "a", "head": (0, 0, 1), "tail": (0, 0, 0), "parent": None},
        {"name": "b", "head": (0, 0, 0), "tail": (0, 0, -1), "parent": "a"},
    ]
    verts = np.array([[0, 0, 0.5], [0, 0, -0.5]], dtype=float)
    imported = {"a": np.array([1.0, 0.0]), "b": np.array([0.0, 1.0])}
    w, diag = binding.validate_imported_weights(verts, bones, imported)
    assert diag["gate_p_readable"] is True
    assert diag["binding_arm"] == "imported_weights"
    assert w["a"][0] == 1.0


def test_fa4aeb565_bounded_heat_via_character_class():
    bones = [
        {"name": "a", "head": (0, 0, 1), "tail": (0, 0, 0), "parent": None},
        {"name": "b", "head": (0, 0, 0), "tail": (0, 0, -1), "parent": "a"},
    ]
    radii = {"a": 0.2, "b": 0.2}
    verts = np.array([[0, 0, 0.8], [0, 0, -0.8], [0, 0, 0.0]], dtype=float)
    w, diag = binding.bind_weights(
        verts, bones, radii, character_class="soft_skinned")
    assert diag["binding_arm"] == "bounded_heat_weights"
    assert diag["gate_p_readable"] is True
    totals = w["a"] + w["b"]
    assert np.allclose(totals, 1.0)


# ----------------------------------------- F-e37bc671 channel softedge/flow/canny

def test_fe37bc671_encode_softedge_and_canny():
    edge = np.zeros((8, 8), dtype=np.uint8)
    edge[3:5, 3:5] = 255
    soft, sdiag = channels.encode_softedge(edge, radius=1)
    assert soft.dtype == np.uint8 and soft.shape == (8, 8)
    assert sdiag["convention"] == "softedge"
    assert len(sdiag["digest"]) == 64
    assert int((soft > 0).sum()) >= int((edge > 0).sum())  # blur keeps/spreads ink
    canny, cdiag = channels.encode_canny(edge)
    assert set(np.unique(canny)).issubset({0, 255})
    assert cdiag["convention"] == "canny"
    assert "not OpenCV" in cdiag["note"]


def test_fe37bc671_encode_flow_zero_is_mid_grey():
    flow = np.zeros((4, 4, 2), dtype=np.float64)
    mask = np.ones((4, 4), dtype=np.uint8)
    rgb, diag = channels.encode_flow(flow, mask, max_mag=10.0)
    assert rgb.shape == (4, 4, 3)
    assert rgb[0, 0, 0] == 128 and rgb[0, 0, 1] == 128 and rgb[0, 0, 2] == 0
    assert diag["digest"] == channels.convention_digest("flow")
    # Background stays black.
    mask2 = np.zeros((4, 4), dtype=np.uint8)
    rgb2, _ = channels.encode_flow(flow, mask2, max_mag=10.0)
    assert rgb2.sum() == 0
