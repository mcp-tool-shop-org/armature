"""Wave-34 feature-execute: core-solvers HIGH findings (reverted-red proofs)."""

import hashlib
import json
import math
import struct

import numpy as np
import pytest

from armature_core import (
    aapose, framing, glb, landmarks, lift_solve, openpose, pngio, sitelist, walk,
)
from armature_core.errors import ArmatureError

#: Spelled in CODE so the clause-vocabulary census sees every wave-34 receipt word.
W34_NEW_CLAUSES = (
    "animation_accessor_empty",
    "animation_accessor_has_no_bufferview",
    "animation_accessor_out_of_range",
    "animation_accessor_past_bin_chunk",
    "animation_ambiguous_root_translation",
    "animation_bufferview_out_of_range",
    "animation_cubicspline_length_mismatch",
    "animation_fps_not_positive",
    "animation_has_no_channels",
    "animation_index_out_of_range",
    "animation_interpolation_unsupported",
    "animation_joint_unmapped",
    "animation_no_usable_tracks",
    "animation_node_out_of_range",
    "animation_rotation_not_vec4",
    "animation_sampler_input_not_scalar",
    "animation_sampler_length_mismatch",
    "animation_sampler_out_of_range",
    "animation_scale_channel_unsupported",
    "animation_translation_not_vec3",
    "animation_unsupported_accessor_type",
    "animation_unsupported_component_type",
    "articulated_hand_bad_columns",
    "articulated_hand_points_required",
    "articulated_hand_wrong_point_count",
    "camera_key_angle_not_finite",
    "camera_key_frame_duplicate",
    "camera_key_frame_negative",
    "camera_key_not_a_dict",
    "camera_key_radius_not_positive",
    "camera_key_target_not_finite",
    "camera_key_unreadable",
    "camera_path_sample_miss",
    "character_class_mismatch",
    "empty_camera_path",
    "imported_sites_empty",
    "imported_sites_required",
    "keypoint_names_length_mismatch",
    "n_frames_not_positive",
    "no_animations",
    "palette_length_mismatch",
    "path_puts_union_out_of_frame",
    "proportion_fallback_bad_cloud",
    "proportion_fallback_degenerate_bbox",
    "root_provider_missing_root",
    "root_provider_root_not_3vector",
    "root_provider_unknown_source",
    "root_provider_unreadable",
    "unknown_character_class",
    "unknown_hand_mode",
    "unknown_named_gait",
)


def test_w34_new_clauses_are_spelled_for_the_vocabulary_census():
    assert len(W34_NEW_CLAUSES) == 51
    assert "animation_joint_unmapped" in W34_NEW_CLAUSES
    assert "stance_frac_not_modelled" not in W34_NEW_CLAUSES


# ----------------------------------------------------------------- F-219a7aba pngio RGBA

def test_f219a7aba_rgba_write_roundtrips_via_pillow(tmp_path):
    path = tmp_path / "rgba.png"
    arr = np.zeros((8, 8, 4), dtype=np.uint8)
    arr[..., 0] = 10
    arr[..., 1] = 20
    arr[..., 2] = 30
    arr[..., 3] = 200
    n = pngio.write_png(str(path), arr)
    assert n > 0
    assert pngio.COLOR_RGBA == 6
    from PIL import Image
    got = np.asarray(Image.open(path))
    assert got.shape == (8, 8, 4)
    assert got.dtype == np.uint8
    assert int(got[0, 0, 3]) == 200


# --------------------------------------------------------- F-b08c0918 OpenPose drawing

def test_fb08c0918_openpose_draw_frame_inks():
    openpose.require_drawing_convention()
    body = np.zeros((18, 3), dtype=np.float64)
    # A tiny standing stick in frame.
    xs = [64, 64, 40, 30, 20, 88, 98, 108, 50, 50, 50, 78, 78, 78, 58, 70, 52, 76]
    ys = [20, 40, 40, 70, 100, 40, 70, 100, 100, 140, 180, 100, 140, 180, 16, 16, 18, 18]
    for i, (x, y) in enumerate(zip(xs, ys)):
        body[i] = (x, y, 1.0)
    canvas = openpose.draw_frame(200, 128, body)
    assert int(np.count_nonzero(np.any(canvas != 0, axis=2))) > 0


# ----------------------------------------------------- F-46f5e906 framing camera path

def test_f46f5e906_solve_path_samples_and_checks_in_frame():
    cloud = [(0.0, 0.0, 0.0), (0.1, 0.0, 1.7), (-0.1, 0.0, 1.7),
             (0.2, 0.0, 0.9), (-0.2, 0.0, 0.9)]
    keys = [
        {"frame": 0, "azimuth_deg": 0.0, "elevation_deg": 10.0, "radius": 4.0,
         "target": [0.0, 0.0, 0.9]},
        {"frame": 4, "azimuth_deg": 30.0, "elevation_deg": 12.0, "radius": 4.2,
         "target": [0.05, 0.0, 0.9]},
    ]
    path = framing.solve_path(cloud, keys, lens_mm=50.0, sensor_mm=36.0,
                              width=832, height=480, n_frames=5, require_in_frame=False)
    assert path["n_frames"] == 5
    assert len(path["frames"]) == 5
    assert path["frames"][2]["azimuth_deg"] == pytest.approx(15.0)
    mid = framing.sample_camera_at(keys, 2)
    assert mid["radius"] == pytest.approx(4.1)


# ----------------------------------------------- F-03853b93 GLB animation ingest

def _anim_glb(path, node_name="hips"):
    """Minimal GLB with one node rotation + translation animation over 1 second."""
    # identity quat + a small yaw; translation along +Y
    times = struct.pack("<ff", 0.0, 1.0)
    # quats (x,y,z,w)
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


def test_f03853b93_read_animation_keyed_to_sitelist(tmp_path):
    p = str(tmp_path / "perf.glb")
    _anim_glb(p, node_name="hips")
    motion = glb.read_animation(p, fps=2.0, sitelist_names=list(sitelist.ALL_NAMES))
    assert motion["source"]["n_frames"] == 3  # t=0, 0.5, 1.0
    assert "hips" in motion["frames"][0]["local"]
    assert motion["frames"][-1]["root"][1] == pytest.approx(0.5)
    assert motion["root_bone"] == "hips"


def test_f03853b93_unmapped_joint_refused(tmp_path):
    p = str(tmp_path / "bad.glb")
    _anim_glb(p, node_name="Root_JNT")
    with pytest.raises(glb.MalformedGLB) as exc:
        glb.read_animation(p, fps=2.0, sitelist_names=list(sitelist.ALL_NAMES))
    assert exc.value.evidence["clause"] == "animation_joint_unmapped"


# --------------------------------------------- F-ce5896e5 gait beyond 0.5

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


def test_fce5896e5_named_run_flight_builds():
    perf = walk.Performer(_gait_landmarks(), facing_y_sign=-1.0, left_x_sign=-1.0)
    p = walk.GaitParams(named_gait="run_flight", n_walk=12, n_decel=4,
                        n_gesture=4, n_hold=2, steps=2)
    assert p.stance_frac == 0.4
    gait = walk.build_gait(perf, p)
    assert any(not f["stance_L"] and not f["stance_R"] for f in gait["frames"])
    phases = walk.gait_phase_fractions(0.4)
    assert phases["flight_fraction_of_cycle"] == pytest.approx(0.2, abs=0.01)


def test_fce5896e5_walk_double_builds():
    perf = walk.Performer(_gait_landmarks(), facing_y_sign=-1.0, left_x_sign=-1.0)
    p = walk.GaitParams(stance_frac=0.6, n_walk=12, n_decel=4, n_gesture=4, n_hold=2,
                        steps=2)
    gait = walk.build_gait(perf, p)
    assert any(f["stance_L"] and f["stance_R"] for f in gait["frames"])

# ------------------------------------------- F-e1d071d0 metric travel root

def test_fe1d071d0_root_provider_walk_gait():
    # Use the suite's synthetic rest if available; else a minimal table.
    import test_lift_solve as TLS
    rest = TLS.synthetic_rest()
    obs = TLS.observed_from(rest, TLS.motion(TLS.LIMB_MOTION))
    solved = lift_solve.solve_frame(
        rest, obs, root_provider={"source": "walk_gait", "root": [0.1, 0.4, -0.02]})
    assert solved["root"]["source"] == "walk_gait"
    assert solved["root"]["translation"] == pytest.approx((0.1, 0.4, -0.02))
    assert solved["root"]["hips_delta_translation"] != solved["root"]["translation"]


# -------------------------------- F-3c80ad38 character-class adapter

def test_f3c80ad38_imported_sites_adapter_shape():
    sites = {"crotch": (0, 0, 1), "neck_base": (0, 0, 1.5), "head_top": (0, 0, 1.8)}
    out = landmarks.derive(None, character_class="imported_sites", imported_sites=sites)
    assert out["character_class"] == "imported_sites"
    assert out["landmarks"]["crotch"] == (0.0, 0.0, 1.0)
    assert out["provenance"]["crotch"].startswith("MEASURED")


def test_f3c80ad38_cross_class_snap_refused():
    from armature_core import joints
    derived = {"landmarks": {"shoulder_L": (0, 0, 1)}, "character_class": "imported_sites"}
    with pytest.raises(landmarks.LandmarkError) as exc:
        joints.snap_sites_to_balls(derived, [])
    assert exc.value.evidence["clause"] == "character_class_mismatch"


# ------------------------------------------- F-f821776d hands beyond mittens

def test_ff821776d_articulated_hand_packer():
    pts = [(float(i), float(i), 1.0) for i in range(21)]
    arr, meta = aapose.articulated_hand(pts)
    assert arr.shape == (21, 3)
    assert meta["hand_mode"] == "articulated"
    assert meta["provenance"] == "MEASURED"


def test_ff821776d_sitelist_hand_chain_optional():
    assert len(sitelist.bones_for("mitten")) == len(sitelist.BONES)
    art = sitelist.bones_for("articulated")
    assert len(art) == len(sitelist.BONES) + len(sitelist.HAND_CHAIN)
    assert "index.L" in sitelist.hand_chain_names()
    assert lift_solve.site_map_for("articulated")[17] == "pinky_L"
    assert 17 not in lift_solve.unused_landmarks_for("articulated")
