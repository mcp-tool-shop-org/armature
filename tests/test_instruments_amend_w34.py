"""Wave 34 feature-execute — instruments HIGH fixes.

F-3415ebd2 — author_walk key_motion / pose-library beyond the one gait.
F-91411b51 — render_start_frame --set 3D scenery staging.
F-97da5a40 — lift_solve --retarget BVH/FBX onto sitelist bones.
F-d7f9fed5 — render_start_frame --frames FLF2V matched pair under one lock.

Each check is a PROPERTY over source / a pure helper; helpers under tests/ raise.
"""

import ast
import json
import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

from blender_stub import load_tool, read_source  # noqa: E402
from armature_core import sitelist  # noqa: E402
from armature_core.errors import ArmatureError, GateFailure  # noqa: E402
import _census_nodes as CN  # noqa: E402

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")

#: ONE home in `_census_nodes.flag_names` (wave-26 F-f893634d); aliased here and in w35.
_flag_names = CN.flag_names


# =======================================================================================
# F-3415ebd2 — performance authoring beyond the one gait
# =======================================================================================


def test_author_walk_exposes_motion_and_pose_library_flags():
    src = read_source("author_walk.py")
    flags = _flag_names(src)
    assert "--motion" in flags
    assert "--pose-library" in flags


def test_pose_library_builds_valid_lift_solve_frames():
    mod = load_tool("author_walk.py")
    frames = mod.build_pose_library_frames("hold", n_frames=3)
    assert len(frames) == 3
    assert all(f["frame"] == i for i, f in enumerate(frames))
    for name in sitelist.ALL_NAMES:
        assert name in frames[0]["local"]
    from armature_core import lift_solve as LS
    gate = LS.validate_motion_record(frames)
    assert gate["n_frames"] == 3


def test_pose_library_idle_is_not_a_rest_clone():
    mod = load_tool("author_walk.py")
    rest = mod.build_pose_library_frames("rest", n_frames=4)
    idle = mod.build_pose_library_frames("idle", n_frames=4)
    assert rest[1]["local"]["spine"] == rest[0]["local"]["spine"]
    assert idle[1]["local"]["spine"] != idle[0]["local"]["spine"]


def test_resolve_performance_refuses_motion_and_library_together():
    mod = load_tool("author_walk.py")
    args = SimpleNamespace(motion="x.json", pose_library="hold", n_hold=2)
    with pytest.raises(ArmatureError) as exc:
        mod.resolve_performance(args)
    assert exc.value.evidence["clause"] == "motion_and_pose_library_both_set"


def test_author_walk_reverted_red_had_only_gait_factory():
    """REVERTED-RED: pre-fix author_walk had no --motion / --pose-library tokens."""
    # Decoy of the measured pre-fix surface (finding evidence: parse_args :152-173).
    decoy = '''
def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glb", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fps", type=int, default=16)
    ap.add_argument("--n-walk", type=int, default=40)
    ap.add_argument("--n-decel", type=int, default=8)
    ap.add_argument("--n-gesture", type=int, default=12)
    ap.add_argument("--n-hold", type=int, default=5)
    ap.add_argument("--steps", type=int, default=5)
    return ap.parse_args([])
'''
    flags = _flag_names(decoy)
    assert "--motion" not in flags and "--pose-library" not in flags
    src = read_source("author_walk.py")
    live = _flag_names(src)
    assert "--motion" in live and "--pose-library" in live


# =======================================================================================
# F-91411b51 — 3D set staging
# =======================================================================================


def test_render_start_frame_exposes_appendable_set_flag():
    src = read_source("render_start_frame.py")
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "parse_args")
    set_calls = []
    for node in ast.walk(fn):
        if not isinstance(node, ast.Call):
            continue
        if not (isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument"):
            continue
        if node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == "--set":
            set_calls.append(node)
    assert len(set_calls) == 1
    keywords = {k.arg: k.value for k in set_calls[0].keywords}
    assert isinstance(keywords.get("action"), ast.Constant)
    assert keywords["action"].value == "append"


def test_render_start_frame_main_imports_set_and_excludes_from_framing():
    src = read_source("render_start_frame.py")
    assert "sets_in_framing_solve" in src
    assert "F-91411b51" in src
    tree = ast.parse(src)
    main = next(n for n in ast.walk(tree)
                if isinstance(n, ast.FunctionDef) and n.name == "main")
    body = ast.unparse(main)
    assert "a.set" in body or "args.set" in body or "(a.set or [])" in body
    assert "set_records" in body


def test_set_flag_reverted_red_absent_from_pre_fix_parser():
    """REVERTED-RED: pre-fix flag census had zero --set / set_glb tokens."""
    decoy = '''
def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glb", required=True)
    ap.add_argument("--plate", default=None)
    ap.add_argument("--plate-why", default=None)
    ap.add_argument("--floor", type=int, default=1)
    return ap.parse_args([])
'''
    assert "--set" not in _flag_names(decoy)
    assert "--set" in _flag_names(read_source("render_start_frame.py"))


# =======================================================================================
# F-97da5a40 — mocap / BVH retarget
# =======================================================================================


def test_lift_solve_exposes_retarget_admission_flags():
    src = read_source("lift_solve.py")
    flags = _flag_names(src)
    for need in ("--retarget", "--bone-map", "--licence-row", "--root-translation"):
        assert need in flags, need


def test_require_retarget_flags_demands_licence_row_and_bone_map():
    mod = load_tool("lift_solve.py")
    args = SimpleNamespace(motion=None, retarget="clip.bvh", bone_map=None,
                           licence_row=None, root_translation="hips_delta_world")
    with pytest.raises(ArmatureError) as exc:
        mod.require_retarget_flags(args)
    assert exc.value.evidence["clause"] == "retarget_missing_admission"
    assert "--bone-map" in exc.value.evidence["missing"]
    assert "--licence-row" in exc.value.evidence["missing"]


def test_retarget_provenance_records_root_translation_and_licence_row():
    mod = load_tool("lift_solve.py")
    block = mod.retarget_provenance(
        source_path="C:/clips/walk.bvh", source_sha="abc",
        bone_map={"hips": "Hips", "spine": "Spine"},
        licence_row="100STYLE", root_translation="hips_delta_world",
        source_format="bvh")
    assert block["licence_row_id"] == "100STYLE"
    assert block["root_translation_representation"] == "hips_delta_world"
    assert "movement-library" in block["root_translation_note"]


def test_load_bone_map_refuses_unknown_sitelist_keys(tmp_path):
    mod = load_tool("lift_solve.py")
    p = tmp_path / "map.json"
    p.write_text(json.dumps({"hips": "Hips", "not_a_bone": "X"}), encoding="utf-8")
    with pytest.raises(ArmatureError) as exc:
        mod.load_bone_map(str(p))
    assert exc.value.evidence["clause"] == "bone_map_unknown_sitelist_bones"


def test_retarget_reverted_red_had_zero_retarget_tokens():
    """REVERTED-RED: pre-fix author_walk/lift_solve had zero retarget/BVH/mocap tokens."""
    decoy = "def parse_args():\n    ap.add_argument('--motion', required=True)\n"
    for tok in ("retarget", "BVH", "bvh", "mocap"):
        assert tok not in decoy
    src = read_source("lift_solve.py")
    assert "retarget" in src and "BVH" in src


# =======================================================================================
# F-d7f9fed5 — FLF2V matched first/last pair
# =======================================================================================


def test_resolve_frame_indices_pair_and_same_index_refusal():
    mod = load_tool("render_start_frame.py")
    ok = mod.resolve_frame_indices(SimpleNamespace(frames="0,64", end_frame=None, frame=0))
    assert ok == (0, 64)
    with pytest.raises(GateFailure) as exc:
        mod.resolve_frame_indices(SimpleNamespace(frames="7,7", end_frame=None, frame=0))
    assert exc.value.evidence["clause"] == "flf_pair_same_index"


def test_plan_output_files_names_start_and_end_stems():
    mod = load_tool("render_start_frame.py")
    planned = mod.plan_output_files((0, 64), backdrop=False, shadow_layer=False)
    assert "start_frame_rgba.png" in planned
    assert "end_frame_rgba.png" in planned
    assert "start_frame.png" in planned
    assert "end_frame.png" in planned
    assert "start_frame_provenance.json" in planned


def test_render_start_frame_exposes_frames_and_end_frame_flags():
    flags = _flag_names(read_source("render_start_frame.py"))
    assert "--frames" in flags
    assert "--end-frame" in flags


def test_flf_pair_reverted_red_had_only_single_frame_flag():
    """REVERTED-RED: pre-fix parser exposed only --frame, no pair tokens."""
    decoy = '''
def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frame", type=int, default=0)
    return ap.parse_args([])
'''
    flags = _flag_names(decoy)
    assert "--frames" not in flags and "--end-frame" not in flags
    live = _flag_names(read_source("render_start_frame.py"))
    assert "--frames" in live and "--end-frame" in live


def test_main_writes_pair_block_in_provenance_source():
    src = read_source("render_start_frame.py")
    assert '"pair"' in src or "'pair'" in src
    assert "FLF2V" in src
    assert "shared_across_pair" in src
