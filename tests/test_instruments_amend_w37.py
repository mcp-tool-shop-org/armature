"""Wave 37 feature-execute — instruments HIGH+MEDIUM+LOW fixes.

Each check is a PROPERTY over source / a pure helper; helpers under tests/ raise.
One reverted-red decoy per finding family.
"""

import ast
import json
import os
import sys
import tempfile
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

from blender_stub import load_tool, read_source  # noqa: E402
from armature_core import framing, sitelist  # noqa: E402
from armature_core.errors import ArmatureError, GateFailure  # noqa: E402
import _census_nodes as CN  # noqa: E402

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
_flag_names = CN.flag_names


def _arg_action(src, flag, func="parse_args"):
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == func)
    for node in ast.walk(fn):
        if not isinstance(node, ast.Call):
            continue
        if not (isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument"):
            continue
        if not (node.args and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == flag):
            continue
        for kw in node.keywords:
            if kw.arg == "action" and isinstance(kw.value, ast.Constant):
                return kw.value.value
    return None


# =======================================================================================
# F-0f6135ad — --set on performer / preview_walk
# =======================================================================================


def test_set_flag_on_performer_and_preview_walk():
    for tool in ("render_performer.py", "preview_walk.py"):
        assert "--set" in _flag_names(read_source(tool))
        assert _arg_action(read_source(tool), "--set") == "append"
    mod = load_tool("render_performer.py")
    assert callable(mod.import_set_glbs)


def test_set_reverted_red_absent():
    decoy = '''
def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glb", action="append", required=True)
    ap.add_argument("--camera-path", default=None)
    return ap.parse_args([])
'''
    assert "--set" not in _flag_names(decoy)
    assert "--set" in _flag_names(read_source("render_performer.py"))


# =======================================================================================
# F-4d4508b0 — --width/--height on performer
# =======================================================================================


def test_performer_exposes_width_height():
    src = read_source("render_performer.py")
    flags = _flag_names(src)
    assert "--width" in flags and "--height" in flags


def test_width_height_reverted_red():
    decoy = '''
WIDTH, HEIGHT = 1920, 1080
def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glb", required=True)
    return ap.parse_args([])
'''
    assert "--width" not in _flag_names(decoy)
    assert "--width" in _flag_names(read_source("render_performer.py"))


# =======================================================================================
# F-86b53f15 — --review-clip on performer
# =======================================================================================


def test_performer_review_clip_and_next():
    src = read_source("render_performer.py")
    assert "--review-clip" in _flag_names(src)
    assert "review_clip_next" in src
    mod = load_tool("render_performer.py")
    nxt = mod.review_clip_next("/tmp/frames")
    assert nxt["tool"] == "make_review_clip"


def test_review_clip_performer_reverted_red():
    decoy = '''
def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    return ap.parse_args([])
'''
    assert "--review-clip" not in _flag_names(decoy)
    assert "--review-clip" in _flag_names(read_source("render_performer.py"))


# =======================================================================================
# F-787129aa — --engine=eevee|cycles
# =======================================================================================


def test_engine_flag_and_candidates():
    for tool in ("render_performer.py", "render_start_frame.py", "render_turnaround.py"):
        assert "--engine" in _flag_names(read_source(tool))
    mod = load_tool("render_performer.py")
    assert mod.engine_candidates_for("eevee") == mod.ENGINE_CANDIDATES
    assert mod.engine_candidates_for("cycles") == mod.CYCLES_CANDIDATES
    with pytest.raises(ArmatureError):
        mod.engine_candidates_for("metal")


def test_engine_reverted_red():
    decoy = '''
ENGINE_CANDIDATES = ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE")
def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glb", required=True)
    return ap.parse_args([])
'''
    assert "--engine" not in _flag_names(decoy)
    assert "--engine" in _flag_names(read_source("render_performer.py"))


# =======================================================================================
# F-63fdb149 — --foot-plant
# =======================================================================================


def test_foot_plant_flag_and_pure_helper():
    src = read_source("lift_solve.py")
    assert "--foot-plant" in _flag_names(src)
    mod = load_tool("lift_solve.py")
    frames = [
        {"frame": 0, "local": {"ankle.L": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
                               "ankle.R": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]},
         "root": [0.0, 0.0, 0.0]},
        {"frame": 1, "local": {"ankle.L": [[0.9, 0.1, 0], [0, 1, 0], [0, 0, 1]],
                               "ankle.R": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]},
         "root": [0.001, 0.0, 0.0]},
    ]
    out, meta = mod.apply_foot_plant(frames, mode="speed", speed_threshold=0.02)
    assert meta["policy"] == "speed"
    assert meta["planted_frames"] >= 1
    assert out[1]["local"]["ankle.L"] == frames[0]["local"]["ankle.L"]
    off, meta_off = mod.apply_foot_plant(frames, mode="off")
    assert meta_off["policy"] == "off"
    assert off[1]["local"]["ankle.L"] == frames[1]["local"]["ankle.L"]


def test_foot_plant_reverted_red():
    decoy = '''
def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--retarget", default=None)
    ap.add_argument("--bone-map", default=None)
    return ap.parse_args([])
'''
    assert "--foot-plant" not in _flag_names(decoy)
    assert "--foot-plant" in _flag_names(read_source("lift_solve.py"))


# =======================================================================================
# F-c743fc7d — bone-map presets
# =======================================================================================


def test_bone_map_presets_mixamo_and_gltf():
    mod = load_tool("lift_solve.py")
    assert "mixamo" in mod.BONE_MAP_PRESETS
    assert "gltf-humanoid" in mod.BONE_MAP_PRESETS
    m, meta = mod.resolve_bone_map("mixamo")
    assert m["hips"] == "mixamorig:Hips"
    assert meta["preset"] == "mixamo"
    assert len(meta["preset_sha256"]) == 64
    g = mod.load_bone_map("gltf-humanoid")
    assert g["shoulder.L"] == "leftUpperArm"


def test_bone_map_preset_reverted_red():
    decoy = '''
def load_bone_map(path):
    with open(path) as fh:
        return json.load(fh)
'''
    assert "BONE_MAP_PRESETS" not in decoy
    assert "mixamo" in load_tool("lift_solve.py").BONE_MAP_PRESETS


# =======================================================================================
# F-6966f488 — --hand-pose
# =======================================================================================


def test_hand_pose_builders():
    mod = load_tool("author_walk.py")
    assert "--hand-pose" in _flag_names(read_source("author_walk.py"))
    fist = mod.hand_pose_locals("fist")
    assert "index.L" in fist
    assert fist["index.L"] != [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    hold = mod.hand_pose_locals("hold")
    assert hold["index.L"][0][0] == pytest.approx(1.0)
    frames = [{"frame": 0, "local": {"hips": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]},
               "root": [0, 0, 0]}]
    out, meta = mod.apply_hand_pose_to_frames(frames, "spread", hand_mode="articulated")
    assert meta["applied"] is True
    assert "pinky.R" in out[0]["local"]


def test_hand_pose_reverted_red():
    decoy = '''
HAND_HOLD_REASON = "hold"
def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hand-mode", default="mitten")
    return ap.parse_args([])
'''
    assert "--hand-pose" not in _flag_names(decoy)
    assert "--hand-pose" in _flag_names(read_source("author_walk.py"))


# =======================================================================================
# F-b11474d7 — grow POSE_LIBRARIES
# =======================================================================================


def test_pose_libraries_include_sit_turn_run_gesture():
    mod = load_tool("author_walk.py")
    for name in ("sit", "turn", "run", "gesture"):
        assert name in mod.POSE_LIBRARIES
    sit = mod.build_pose_library_frames("sit", n_frames=2)
    assert len(sit) == 2
    assert sit[0]["local"]["hip.L"] != sit[0]["local"].get(
        "nose", sit[0]["local"]["hips"])
    turn = mod.build_pose_library_frames("turn", n_frames=3)
    assert turn[0]["local"]["hips"] != turn[-1]["local"]["hips"]
    run = mod.build_pose_library_frames("run", n_frames=4)
    assert run[-1]["root"][0] != 0.0
    gesture = mod.build_pose_library_frames("gesture", n_frames=2)
    assert gesture[-1]["local"]["shoulder.R"] != gesture[0]["local"]["shoulder.R"]


def test_pose_library_reverted_red():
    decoy = 'POSE_LIBRARIES = ("rest", "idle", "hold")\n'
    assert "sit" not in decoy
    assert "sit" in load_tool("author_walk.py").POSE_LIBRARIES


# =======================================================================================
# F-dec5af66 — write_camera_path
# =======================================================================================


def test_write_camera_path_helper_and_preview_flag():
    assert "--write-camera-path" in _flag_names(read_source("preview_walk.py"))
    mod = load_tool("render_performer.py")
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "cam.json")
        rec = mod.write_camera_path(
            out_path=path, n_frames=10,
            azimuth_start_deg=225.0, azimuth_end_deg=315.0,
            elevation_deg=8.0, radius=2.5, target=[0.0, 0.0, 1.0])
        assert rec["n_keys"] == 2
        assert os.path.isfile(path)
        loaded = framing.normalize_camera_keys(rec["keys"])
        assert loaded[0]["azimuth_deg"] == pytest.approx(225.0)


def test_write_camera_path_reverted_red():
    decoy = '''
def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--camera-path", default=None)
    return ap.parse_args([])
'''
    assert "--write-camera-path" not in _flag_names(decoy)
    assert "--write-camera-path" in _flag_names(read_source("preview_walk.py"))


# =======================================================================================
# F-e04bca15 — probe_glb clause_D
# =======================================================================================


def test_probe_glb_clause_d_tokens():
    src = read_source("probe_glb.py")
    assert "clause_D_has_keyed_action" in src
    assert "bone_fcurve_count" in src
    assert "n_frames" in src
    # P2 conjunction must remain A∧B∧C only.
    assert 'clause_D_has_keyed_action")' not in src.split("P2_joined")[1][:200]


def test_clause_d_reverted_red():
    decoy = '''
summary = {
    "clause_A_loads": 0,
    "clause_B_has_bones": 0,
    "clause_C_posable_and_named": 0,
    "P2_joined": 0,
}
'''
    assert "clause_D" not in decoy
    assert "clause_D_has_keyed_action" in read_source("probe_glb.py")


# =======================================================================================
# F-0f3723ca — retopo-bake-bind pipeline
# =======================================================================================


def test_retopo_bake_pipeline():
    mod = load_tool("rig_character.py")
    assert "retopo-bake-bind" in mod.PIPELINES
    assert mod.PIPELINES["retopo-bake-bind"] == (
        "rig_retopo", "rig_bake", "rig_character")
    man = mod.build_stage_manifest(
        glb="x.glb", out_dir="out", pipeline="retopo-bake-bind")
    assert man["pipeline"] == "retopo-bake-bind"
    assert man["stages"][0] == "rig_retopo"
    assert len(man["stage_receipts"]) == 3
    src = read_source("diagnose_bone_heat.py")
    assert "next_pipelines" in src
    assert "retopo-bake-bind" in src


def test_pipeline_retopo_reverted_red():
    decoy = 'LIVE_ARM_STAGES = ("rig_repair", "rig_character")\nPIPELINE_MODES = ("", "repair-bind")\n'
    assert "retopo-bake-bind" not in decoy
    assert "retopo-bake-bind" in load_tool("rig_character.py").PIPELINES


# =======================================================================================
# F-6a7e819f — motion compare on check_relift
# =======================================================================================


def test_check_relift_motion_mode():
    src = read_source("check_relift.py")
    flags = _flag_names(src)
    assert "--pinned-motion" in flags and "--fresh-motion" in flags
    mod = load_tool("check_relift.py")
    frames = [
        {"frame": 0, "local": {"hips": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]},
         "root": [0, 0, 0]},
        {"frame": 1, "local": {"hips": [[0.9, 0.1, 0], [0, 1, 0], [0, 0, 1]]},
         "root": [0.1, 0, 0]},
    ]
    with tempfile.TemporaryDirectory() as td:
        p1 = os.path.join(td, "a.json")
        p2 = os.path.join(td, "b.json")
        with open(p1, "w", encoding="utf-8") as fh:
            json.dump({"frames": frames}, fh)
        with open(p2, "w", encoding="utf-8") as fh:
            json.dump({"frames": frames}, fh)
        s1, w1 = mod.motion_channel_signatures(p1, 65)
        s2, w2 = mod.motion_channel_signatures(p2, 65)
        ev = mod.compare_motion_signatures(s1, s2)
        assert ev["n_frames_differing"] == 0
        frames2 = list(frames)
        frames2[1] = {"frame": 1, "local": {"hips": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]},
                      "root": [0.1, 0, 0]}
        with open(p2, "w", encoding="utf-8") as fh:
            json.dump({"frames": frames2}, fh)
        s2b, _ = mod.motion_channel_signatures(p2, 65)
        ev2 = mod.compare_motion_signatures(s1, s2b)
        assert ev2["n_frames_differing"] >= 1


def test_motion_relift_reverted_red():
    decoy = '''
def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pinned", required=True)
    ap.add_argument("--fresh", required=True)
    return ap.parse_args([])
'''
    assert "--pinned-motion" not in _flag_names(decoy)
    assert "--pinned-motion" in _flag_names(read_source("check_relift.py"))


# =======================================================================================
# F-7d067bf8 — --glb on make_test_armature
# =======================================================================================


def test_make_test_armature_glb_flag():
    # argparse lives inside main() (no parse_args); census by token.
    src = read_source("make_test_armature.py")
    assert 'add_argument("--glb"' in src or "add_argument('--glb'" in src
    assert "F-7d067bf8" in src


def test_make_test_armature_glb_reverted_red():
    decoy = '''
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--thickness", type=float, default=0.03)
    ap.add_argument("--out", required=True)
'''
    assert 'add_argument("--glb"' not in decoy
    assert 'add_argument("--glb"' in read_source("make_test_armature.py")


# =======================================================================================
# F-813d7a7f — --camera-path on preview_glb
# =======================================================================================


def test_preview_glb_camera_path():
    assert "--camera-path" in _flag_names(read_source("preview_glb.py"))
    assert "load_camera_path" in read_source("preview_glb.py")


def test_preview_glb_camera_path_reverted_red():
    decoy = '''
def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glb", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--name", required=True)
    return ap.parse_args([])
'''
    assert "--camera-path" not in _flag_names(decoy)
    assert "--camera-path" in _flag_names(read_source("preview_glb.py"))


# =======================================================================================
# F-bfac5ade — --set on turnaround
# =======================================================================================


def test_turnaround_set_flag():
    assert "--set" in _flag_names(read_source("render_turnaround.py"))
    assert _arg_action(read_source("render_turnaround.py"), "--set") == "append"


def test_turnaround_set_reverted_red():
    decoy = '''
def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--roster", default=None)
    ap.add_argument("--ortho-scale", type=float, default=None)
    return ap.parse_args([])
'''
    assert "--set" not in _flag_names(decoy)
    assert "--set" in _flag_names(read_source("render_turnaround.py"))


# =======================================================================================
# F-d9a334e8 — beauty mode on start_frame
# =======================================================================================


def test_start_frame_beauty_mode_and_hdri():
    src = read_source("render_start_frame.py")
    flags = _flag_names(src)
    assert "--mode" in flags
    assert "--hdri" in flags
    assert "beauty" in src
    mod = load_tool("render_start_frame.py")
    assert "beauty" in mod.START_MODES


def test_beauty_hdri_reverted_red():
    decoy = '''
def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", action="append")
    ap.add_argument("--plate", default=None)
    return ap.parse_args([])
'''
    assert "--mode" not in _flag_names(decoy)
    assert "--hdri" not in _flag_names(decoy)
    live = _flag_names(read_source("render_start_frame.py"))
    assert "--mode" in live and "--hdri" in live


# =======================================================================================
# F-ff605a1f covered with beauty/hdri above
# =======================================================================================
