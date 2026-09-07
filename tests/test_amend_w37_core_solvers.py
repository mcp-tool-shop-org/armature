"""Wave-37 feature-execute: core-solvers findings (reverted-red proofs)."""

import json
import math
import struct

import numpy as np
import pytest

from armature_core import (
    clipcompare, clipstats, framing, glb, lift_solve, openpose, pngio, posearc,
    resample, sitelist, walk,
)
from armature_core.errors import ArmatureError, GateFailure, SpecError

W37_NEW_CLAUSES = (
    "body_sites_not_a_mapping",
    "camera_key_interp_unknown",
    "decimate_budget_not_positive",
    "face_targets_unavailable",
    "heading_key_unreadable",
    "heading_length_mismatch",
    "heading_not_finite",
    "heading_unreadable",
    "lag_max_negative",
    "lag_no_overlap",
    "lag_too_few_frames",
    "motion_diag_authored_length_mismatch",
    "motion_diag_authored_unreadable",
    "motion_diag_empty_motion",
    "motion_diag_no_frames",
    "motion_diag_record_unreadable",
    "motion_diag_rest_obs_incomplete",
    "png_bad_signature",
    "png_crc_mismatch",
    "png_ihdr_missing",
    "png_no_idat",
    "png_scanline_length",
    "png_truncated",
    "png_unreadable",
    "png_unsupported_color_type",
    "png_unsupported_encoding",
    "png_unsupported_filter",
    "png_zlib_error",
    "too_few_frames_to_decimate",
    "unknown_face_mode",
    "unknown_foot_mode",
)


def test_w37_new_clauses_are_spelled_for_the_vocabulary_census():
    assert len(W37_NEW_CLAUSES) == 31
    assert "unknown_face_mode" in W37_NEW_CLAUSES
    assert "camera_key_interp_unknown" in W37_NEW_CLAUSES


def _identity_local():
    I = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    return {name: [row[:] for row in I] for name in sitelist.ALL_NAMES}


def _gait_landmarks():
    return {
        "crotch": [0, 0, 0.9], "spine_base": [0, 0, 1.0], "chest_base": [0, 0, 1.2],
        "neck_base": [0, 0, 1.45], "head_base": [0, 0, 1.55], "head_top": [0, 0, 1.7],
        "shoulder_L": [-0.2, 0, 1.4], "shoulder_R": [0.2, 0, 1.4],
        "elbow_L": [-0.25, 0, 1.1], "elbow_R": [0.25, 0, 1.1],
        "wrist_L": [-0.28, 0, 0.85], "wrist_R": [0.28, 0, 0.85],
        "hand_end_L": [-0.30, 0, 0.75], "hand_end_R": [0.30, 0, 0.75],
        "hip_L": [-0.1, 0, 0.9], "hip_R": [0.1, 0, 0.9],
        "knee_L": [-0.1, 0, 0.5], "knee_R": [0.1, 0, 0.5],
        "ankle_L": [-0.1, 0, 0.1], "ankle_R": [0.1, 0, 0.1],
        "toe_L": [-0.1, 0.05, 0.05], "toe_R": [0.1, 0.05, 0.05],
    }


def _anim_glb(path, node_name="hips"):
    times = struct.pack("<ff", 0.0, 1.0)
    quats = struct.pack("<ffffffff", 0, 0, 0, 1, 0, 0, math.sin(0.1), math.cos(0.1))
    trans = struct.pack("<ffffff", 0, 0, 0, 0, 0.5, 0)
    binary = times + quats + trans
    views = [
        {"buffer": 0, "byteOffset": 0, "byteLength": 8},
        {"buffer": 0, "byteOffset": 8, "byteLength": 32},
        {"buffer": 0, "byteOffset": 40, "byteLength": 24},
    ]
    accessors = [
        {"bufferView": 0, "componentType": 5126, "count": 2, "type": "SCALAR",
         "max": [1.0], "min": [0.0]},
        {"bufferView": 1, "componentType": 5126, "count": 2, "type": "VEC4"},
        {"bufferView": 2, "componentType": 5126, "count": 2, "type": "VEC3"},
    ]
    js = {
        "asset": {"version": "2.0"},
        "buffers": [{"byteLength": len(binary)}],
        "bufferViews": views,
        "accessors": accessors,
        "nodes": [{"name": node_name}],
        "animations": [{
            "name": "clip",
            "samplers": [
                {"input": 0, "output": 1, "interpolation": "LINEAR"},
                {"input": 0, "output": 2, "interpolation": "LINEAR"},
            ],
            "channels": [
                {"sampler": 0, "target": {"node": 0, "path": "rotation"}},
                {"sampler": 1, "target": {"node": 0, "path": "translation"}},
            ],
        }],
    }
    payload = json.dumps(js).encode("utf-8")
    payload += b" " * (-len(payload) % 4)
    binary += b"\x00" * (-len(binary) % 4)
    total = 12 + 8 + len(payload) + 8 + len(binary)
    with open(path, "wb") as fh:
        fh.write(struct.pack("<III", glb.GLB_MAGIC, 2, total))
        fh.write(struct.pack("<II", len(payload), glb.CHUNK_JSON))
        fh.write(payload)
        fh.write(struct.pack("<II", len(binary), glb.CHUNK_BIN))
        fh.write(binary)


def _rest_sites():
    """Minimal rest table covering SITE_FROM_LANDMARK (+ optional face/heel)."""
    base = {
        "nose": (0.0, -0.05, 1.6),
        "ear_L": (-0.08, -0.02, 1.58), "ear_R": (0.08, -0.02, 1.58),
        "shoulder_L": (-0.2, 0.0, 1.4), "shoulder_R": (0.2, 0.0, 1.4),
        "elbow_L": (-0.25, 0.0, 1.1), "elbow_R": (0.25, 0.0, 1.1),
        "wrist_L": (-0.28, 0.0, 0.85), "wrist_R": (0.28, 0.0, 0.85),
        "hand_end_L": (-0.30, 0.0, 0.75), "hand_end_R": (0.30, 0.0, 0.75),
        "hip_L": (-0.1, 0.0, 0.9), "hip_R": (0.1, 0.0, 0.9),
        "knee_L": (-0.1, 0.0, 0.5), "knee_R": (0.1, 0.0, 0.5),
        "ankle_L": (-0.1, 0.0, 0.1), "ankle_R": (0.1, 0.0, 0.1),
        "toe_L": (-0.1, 0.05, 0.05), "toe_R": (0.1, 0.05, 0.05),
        "crotch": (0.0, 0.0, 0.9),
        "spine_base": (0.0, 0.0, 1.0), "chest_base": (0.0, 0.0, 1.2),
        "neck_base": (0.0, 0.0, 1.45), "head_base": (0.0, 0.0, 1.55),
        "head_top": (0.0, 0.0, 1.7),
        "eye_L": (-0.03, -0.05, 1.62), "eye_R": (0.03, -0.05, 1.62),
        "nose_tip": (0.0, -0.07, 1.6),
        "eye_L_tip": (-0.03, -0.06, 1.62), "eye_R_tip": (0.03, -0.06, 1.62),
        "ear_L_tip": (-0.09, -0.02, 1.58), "ear_R_tip": (0.09, -0.02, 1.58),
    }
    return base


# --------------------------------------------------------- F-1beb140b face_mode

def test_f1beb140b_face_mode_maps_eye_mouth_and_reports_dofs():
    assert 1 in lift_solve.unused_landmarks_for("mitten", face_mode="hold")
    assert 9 in lift_solve.unused_landmarks_for(face_mode="hold")
    unused = lift_solve.unused_landmarks_for(face_mode="landmarks")
    assert 1 not in unused and 9 not in unused
    sm = lift_solve.site_map_for(face_mode="landmarks")
    assert sm["eye_L"] == 2 and sm["mouth_L"] == 9
    rest = _rest_sites()
    rest.update({
        "eye_L_inner": (-0.025, -0.05, 1.62), "eye_L_outer": (-0.04, -0.05, 1.62),
        "eye_R_inner": (0.025, -0.05, 1.62), "eye_R_outer": (0.04, -0.05, 1.62),
        "mouth_L": (-0.03, -0.04, 1.55), "mouth_R": (0.03, -0.04, 1.55),
    })
    obs = dict(rest)
    # Nudge mouth corners so nose leaves hold.
    obs["mouth_L"] = (-0.035, -0.045, 1.55)
    obs["mouth_R"] = (0.035, -0.045, 1.55)
    obs["eye_L_outer"] = (-0.045, -0.052, 1.62)
    obs["eye_R_outer"] = (0.045, -0.052, 1.62)
    solved = lift_solve.solve_frame(rest, obs, face_mode="landmarks")
    assert solved["face_mode"] == "landmarks"
    assert "nose" in solved["face_solved"] or "eye.L" in solved["face_solved"]
    assert isinstance(solved["face_held"], list)
    assert len(sitelist.bones_for(face_mode="landmarks")) == len(sitelist.BONES) + 4


def test_f1beb140b_unknown_face_mode_refused():
    with pytest.raises(lift_solve.SolveError) as ei:
        lift_solve.site_map_for(face_mode="blendshapes")
    assert ei.value.evidence["clause"] == "unknown_face_mode"


# --------------------------------------------------------- F-3cc4b5d6 openpose hands

def test_f3cc4b5d6_draw_hand_and_frame_hands_flag():
    assert hasattr(openpose, "draw_hand")
    assert openpose.HAND_KEYPOINT_COUNT == 21
    assert len(openpose.HAND_EDGES) == 20
    body = np.zeros((18, 3), dtype=np.float64)
    for i in range(18):
        body[i] = (32 + (i % 6) * 4, 20 + (i // 6) * 10, 1.0)
    hand = np.zeros((21, 3), dtype=np.float64)
    for i in range(21):
        hand[i] = (10 + i, 40, 1.0)
    body_only = openpose.draw_frame(64, 64, body)
    with_hands = openpose.draw_frame(64, 64, body, left_hand=hand, right_hand=hand,
                                     hands=True)
    assert int(np.count_nonzero(with_hands)) > int(np.count_nonzero(body_only))
    receipt = {}
    openpose.draw_frame(64, 64, body, left_hand=hand, hands=True, receipt=receipt)
    assert receipt["hands"] is True
    assert receipt["hand_receipts"]


# --------------------------------------------------- F-47e3b3af glb motion record

def test_f47e3b3af_as_motion_record_stamps_schema(tmp_path):
    p = str(tmp_path / "perf.glb")
    _anim_glb(p, node_name="hips")
    rec = glb.as_motion_record(p, fps=2.0, sitelist_names=list(sitelist.ALL_NAMES))
    assert rec["motion_schema"] == lift_solve.MOTION_SCHEMA
    assert "source" in rec and "retarget" in rec
    assert len(rec["frames"]) == 3
    out = tmp_path / "clip.motion.json"
    saved = glb.save_motion_record(str(out), p, fps=2.0,
                                   sitelist_names=list(sitelist.ALL_NAMES))
    assert saved["motion_schema"] == 1
    loaded = lift_solve.load_motion_record(str(out))
    assert loaded["motion_schema"] == 1


# --------------------------------------------- F-48da73de clipstats motion diag

def test_f48da73de_motion_aware_diagnostics_uses_lift_units():
    frames_px = [np.zeros((8, 8, 3), dtype=np.uint8) for _ in range(3)]
    motion = [
        {"frame": 0, "local": _identity_local(), "root": [0, 0, 0]},
        {"frame": 1, "local": _identity_local(), "root": [0.1, 0, 0]},
        {"frame": 2, "local": _identity_local(), "root": [0.2, 0, 0]},
    ]
    # Bend one bone on frame 2 so step_angles is non-trivial.
    th = math.radians(10)
    c, s = math.cos(th), math.sin(th)
    motion[2]["local"]["hip.L"] = [[1, 0, 0], [0, c, -s], [0, s, c]]
    diag = clipstats.motion_aware_diagnostics(
        frames_px, {"frames": motion, "motion_schema": 1})
    assert diag["length_match"] is True
    assert "hip.L" in diag["step_angles"]
    assert diag["step_angles"]["hip.L"]["max_deg"] == pytest.approx(10.0, abs=0.1)
    rest = _rest_sites()
    residuals = clipstats.motion_aware_diagnostics(
        frames_px, motion, rest=rest, obs=rest)["bone_length_residuals"]
    assert residuals is not None and "hip.L" in residuals


# --------------------------------------------------------- F-4c9a4d9e foot_mode

def test_f4c9a4d9e_heel_mode_maps_and_sets_provenance():
    assert 29 in lift_solve.unused_landmarks_for(foot_mode="ankle_as_toe")
    assert 29 not in lift_solve.unused_landmarks_for(foot_mode="heel")
    sm = lift_solve.site_map_for(foot_mode="heel")
    assert sm["heel_L"] == 29 and sm["heel_R"] == 30
    rest = _rest_sites()
    rest["heel_L"] = (-0.1, -0.02, 0.08)
    rest["heel_R"] = (0.1, -0.02, 0.08)
    obs = dict(rest)
    obs["toe_L"] = (-0.1, 0.08, 0.05)
    obs["heel_L"] = (-0.12, -0.03, 0.08)
    solved = lift_solve.solve_frame(rest, obs, foot_mode="heel")
    assert solved["foot_mode"] == "heel"
    assert solved["foot_provenance"] == "heel_twist"
    assert "ankle.L" in solved["solved"]
    assert len(sitelist.bones_for(foot_mode="heel")) == len(sitelist.BONES) + 2


# --------------------------------------------------------- F-54ffc7d4 decimate

def test_f54ffc7d4_decimate_keeps_endpoints_under_budget():
    frames = []
    for i in range(10):
        local = _identity_local()
        th = math.radians(i * 5)
        c, s = math.cos(th), math.sin(th)
        local["hip.L"] = [[1, 0, 0], [0, c, -s], [0, s, c]]
        frames.append({"frame": i, "local": local, "root": [0.0, i * 0.01, 0.0]})
    out = resample.decimate_frames(frames, max_step_deg=12.0)
    assert out[0]["source_frame"] == 0
    assert out[-1]["source_frame"] == 9
    assert 2 <= len(out) < len(frames)
    with pytest.raises(resample.ResampleError) as ei:
        resample.decimate_frames(frames, max_step_deg=0.0)
    assert ei.value.evidence["clause"] == "decimate_budget_not_positive"


# --------------------------------------------- F-588e3daf openpose body_from_sites

def test_f588e3daf_body_from_sites_adapts_neck_base_and_drops_toes():
    assert hasattr(openpose, "body_from_sites")
    sites = {
        "nose": (1.0, 2.0), "neck_base": (3.0, 4.0),
        "shoulder_R": (5, 6), "elbow_R": (7, 8), "wrist_R": (9, 10),
        "shoulder_L": (11, 12), "elbow_L": (13, 14), "wrist_L": (15, 16),
        "hip_R": (17, 18), "knee_R": (19, 20), "ankle_R": (21, 22),
        "hip_L": (23, 24), "knee_L": (25, 26), "ankle_L": (27, 28),
        "eye_R": (29, 30), "eye_L": (31, 32), "ear_R": (33, 34), "ear_L": (35, 36),
        "toe_L": (99, 99), "toe_R": (98, 98),  # present but must be dropped
    }
    body = openpose.body_from_sites(sites, conf=0.9)
    assert body.shape == (18, 3)
    assert list(body[1, :2]) == pytest.approx([3.0, 4.0])
    assert body[0, 2] == pytest.approx(0.9)
    assert openpose.KEYPOINT_NAMES[1] == "neck"


# --------------------------------------------------------- F-68c9af38 camera cut

def test_f68c9af38_cut_interp_holds_then_snaps():
    keys = [
        {"frame": 0, "azimuth_deg": 0.0, "elevation_deg": 0.0, "radius": 2.0,
         "target": [0, 0, 0]},
        {"frame": 10, "azimuth_deg": 90.0, "elevation_deg": 5.0, "radius": 3.0,
         "target": [1, 0, 0], "interp": "cut"},
    ]
    mid = framing.sample_camera_at(keys, 5)
    assert mid["segment_kind"] == "cut"
    assert mid["azimuth_deg"] == pytest.approx(0.0)
    end = framing.sample_camera_at(keys, 10)
    assert end["azimuth_deg"] == pytest.approx(90.0)
    assert end["radius"] == pytest.approx(3.0)
    with pytest.raises(framing.FramingError) as ei:
        framing.normalize_camera_keys([
            {"frame": 0, "azimuth_deg": 0, "elevation_deg": 0, "radius": 1,
             "target": [0, 0, 0], "interp": "slerp"}])
    assert ei.value.evidence["clause"] == "camera_key_interp_unknown"


# --------------------------------------------------------- F-69a1f058 read_png

def test_f69a1f058_read_png_roundtrips_rgba(tmp_path):
    path = tmp_path / "a.png"
    arr = np.zeros((6, 7, 4), dtype=np.uint8)
    arr[..., 0] = 12
    arr[..., 1] = 34
    arr[..., 2] = 56
    arr[..., 3] = 200
    pngio.write_png(str(path), arr)
    got, color = pngio.read_png(str(path))
    assert color == pngio.COLOR_RGBA
    assert got.shape == (6, 7, 4)
    assert np.array_equal(got, arr)
    with pytest.raises(pngio.PngWriteError) as ei:
        pngio.read_png(str(tmp_path / "nope.png"))
    assert ei.value.evidence["clause"] == "png_unreadable"


# --------------------------------------------------------- F-71579a7f posearc legs

def test_f71579a7f_knee_and_hip_arcs_resolve():
    assert "knee_r_bend" in posearc.POSE_ARCS
    assert "hip_sit" in posearc.POSE_ARCS
    knee = posearc.resolve_arc("knee_r_bend")
    assert knee["pivot"] == "knee_r"
    assert knee["readout_deg"] == 45.0
    hip = posearc.resolve_arc("hip_sit")
    assert hip["pivot"] == "hip_r"
    joints = {
        "hip_r": (0.1, 0.0, 0.9), "knee_r": (0.1, 0.0, 0.5),
        "ankle_r": (0.1, 0.0, 0.1), "toe_r": (0.1, 0.05, 0.05),
        "shoulder_l": (0, 0, 1),
    }
    _theta, end = posearc.joints_at_frame(joints, knee, index=1, count=2,
                                          start_deg=0.0, end_deg=90.0)
    assert end["ankle_r"] != joints["ankle_r"]
    with pytest.raises(SpecError) as ei:
        posearc.resolve_arc("no_such_arc")
    assert ei.value.evidence["clause"] == "unknown_pose_arc"


# --------------------------------------------------------- F-7441d205 lag sweep

def test_f7441d205_lag_sweep_recovers_offset():
    sources = [np.full((12, 12, 3), i, dtype=np.uint8) for i in range(8)]
    decoded = sources[2:] + sources[:2]
    report = clipcompare.lag_sweep(sources, decoded, max_lag=3, step=4)
    assert report["best_offset"] == 2
    assert report["mean_err_at_best"] == pytest.approx(0.0)
    assert "order_check" in report and "order_at_best" in report


# --------------------------------------------------------- F-7f15fb7f heading

def test_f7f15fb7f_heading_rotates_path_and_foot_slip_lateral():
    perf = walk.Performer(_gait_landmarks(), facing_y_sign=-1.0, left_x_sign=-1.0)
    straight = walk.build_gait(
        perf, walk.GaitParams(n_walk=12, n_decel=2, n_gesture=2, n_hold=2, steps=2))
    turned = walk.build_gait(
        perf, walk.GaitParams(n_walk=12, n_decel=2, n_gesture=2, n_hold=2, steps=2,
                              heading_deg=90.0))
    assert straight["derived"]["forward_axis"] == "Y"
    assert turned["derived"]["heading_active"] is True
    assert turned["derived"]["forward_axis"] == "heading"
    last_s = straight["frames"][-1]["pose"]["hips"]["translation"]
    last_t = turned["frames"][-1]["pose"]["hips"]["translation"]
    # 90° yaw moves travel onto world X; straight stays on Y.
    assert abs(last_s[0]) < abs(last_s[1]) + 1e-6
    assert abs(last_t[0]) > abs(last_t[1]) - 1e-6
    fk = walk.forward_kinematics(perf, turned)
    slip = walk.foot_slip(fk)
    assert "lateral_slip_fraction_total" in slip["slide"]
    assert "hips_lateral_path" in slip["slide"]
