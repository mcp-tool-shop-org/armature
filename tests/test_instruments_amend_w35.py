"""Wave 35 feature-execute — instruments MEDIUM fixes.

F-30f9bf58 — finger/toe bones + hand binding + author_walk hold reason.
F-5b7048d5 — appendable --glb on staging tools.
F-7071dc05 — --roster batch with pinned ortho_scale gate.
F-82f88f23 — --camera-path on staging tools.
F-8673b6ad — roster/sheet batching in one session (with F-7071dc05).
F-938485d6 — --compose/--no-compose on make_*_sheet.
F-ce65f941 — repair-bind pipeline + diagnose next_tool.
F-cee7b569 — preview_walk --review-clip / next field.

Each check is a PROPERTY over source / a pure helper; helpers under tests/ raise.
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


TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")


def _flag_names(src, func="parse_args"):
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == func)
    names = []
    for node in ast.walk(fn):
        if isinstance(node, ast.Call):
            func_node = node.func
            if isinstance(func_node, ast.Attribute) and func_node.attr == "add_argument":
                if node.args and isinstance(node.args[0], ast.Constant):
                    names.append(node.args[0].value)
    return names


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
# F-30f9bf58 — finger/toe bones + hand binding
# =======================================================================================


def test_rig_character_exposes_hand_mode_and_hand_binding():
    src = read_source("rig_character.py")
    assert "hand" in src
    assert "--hand-mode" in src or '"--hand-mode"' in src
    mod = load_tool("rig_character.py")
    assert "hand" in mod.BINDINGS
    assert "articulated" in mod.HAND_MODES
    names = mod.registered_names_for("articulated")
    for n in sitelist.hand_chain_names():
        assert n in names
    assert "toe.L" in names and "toe.R" in names


def test_synthesize_finger_marks_fills_missing_tips():
    mod = load_tool("rig_character.py")
    marks = {
        "wrist_L": [0.0, 0.2, 1.0], "hand_end_L": [0.0, 0.35, 1.0],
        "wrist_R": [0.0, -0.2, 1.0], "hand_end_R": [0.0, -0.35, 1.0],
    }
    out = mod.synthesize_finger_marks(marks)
    assert "thumb_L" in out and "pinky_R" in out


def test_author_walk_holds_extremities_with_named_reason():
    mod = load_tool("author_walk.py")
    assert mod.HAND_HOLD_REASON
    assert "GAIT_BONES" in mod.HAND_HOLD_REASON
    holds = mod.extremity_hold_names("articulated")
    assert "thumb.L" in holds and "toe.L" in holds
    assert mod.extremity_hold_names("mitten") == ()


def test_hand_binding_reverted_red_had_no_hand_mode():
    """REVERTED-RED: pre-fix BINDINGS lacked hand; no --hand-mode token."""
    decoy = '''
BINDINGS = ("auto", "envelope", "rigid")
def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--binding", default="rigid")
    return ap.parse_args([])
'''
    assert "hand" not in decoy.split("BINDINGS")[1].split("\n")[0]
    assert "--hand-mode" not in _flag_names(decoy)
    live = load_tool("rig_character.py")
    assert "hand" in live.BINDINGS


# =======================================================================================
# F-5b7048d5 — multi-glb append
# =======================================================================================


@pytest.mark.parametrize("tool", [
    "render_performer.py", "render_start_frame.py", "preview_glb.py",
    "author_walk.py", "lift_solve.py",
])
def test_staging_tools_glb_is_appendable(tool):
    src = read_source(tool)
    assert _arg_action(src, "--glb") == "append"


def test_author_walk_resolve_subjects_companions():
    mod = load_tool("author_walk.py")
    args = SimpleNamespace(glb=["a.glb", "b.glb"], manifest=["a.json"])
    sub = mod.resolve_subjects(args)
    assert sub["performer_glb"] == "a.glb"
    assert len(sub["companions"]) == 1
    assert sub["companions"][0]["glb"] == "b.glb"


def test_multi_glb_reverted_red_singular():
    """REVERTED-RED: pre-fix --glb was required singular, not append."""
    decoy = '''
def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glb", required=True)
    return ap.parse_args([])
'''
    assert _arg_action(decoy, "--glb") is None
    assert _arg_action(read_source("render_performer.py"), "--glb") == "append"


# =======================================================================================
# F-7071dc05 / F-8673b6ad — roster batch + pin gate
# =======================================================================================


def test_render_turnaround_exposes_roster_and_helpers():
    src = read_source("render_turnaround.py")
    flags = _flag_names(src)
    assert "--roster" in flags
    mod = load_tool("render_turnaround.py")
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump([{"glb": "a.glb", "prefix": "brute"},
                   {"glb": "b.glb", "prefix": "halfling"}], fh)
        path = fh.name
    try:
        members = mod.load_roster(path)
        assert len(members) == 2
        assert members[0]["prefix"] == "brute"
    finally:
        os.unlink(path)
    args = SimpleNamespace(roster=path, ortho=False, ortho_scale=None, glb=None, prefix="turn")
    # recreate path for require
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump([{"glb": "a.glb", "prefix": "a"}], fh)
        args.roster = fh.name
    try:
        with pytest.raises(GateFailure) as exc:
            mod.require_roster_pin(args)
        assert exc.value.evidence["clause"] == "roster_requires_ortho_scale"
        args.ortho_scale = 1.5
        out = mod.require_roster_pin(args)
        assert out.ortho is True
        gate = mod.gate_roster_scales(
            [{"ortho_scale": 1.5, "ortho_scale_source": "pinned"},
             {"ortho_scale": 1.5, "ortho_scale_source": "pinned"}], 1.5)
        assert gate["verdict"] == "PASS"
        with pytest.raises(GateFailure):
            mod.gate_roster_scales(
                [{"ortho_scale": 1.5, "ortho_scale_source": "pinned"},
                 {"ortho_scale": 1.2, "ortho_scale_source": "pinned"}], 1.5)
    finally:
        os.unlink(args.roster)


def test_roster_reverted_red_absent():
    decoy = '''
def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glb", required=True)
    ap.add_argument("--ortho-scale", type=float, default=None)
    return ap.parse_args([])
'''
    assert "--roster" not in _flag_names(decoy)
    assert "--roster" in _flag_names(read_source("render_turnaround.py"))


# =======================================================================================
# F-82f88f23 — camera path
# =======================================================================================


def test_camera_path_flag_and_loader():
    for tool in ("render_performer.py", "render_start_frame.py", "preview_walk.py"):
        assert "--camera-path" in _flag_names(read_source(tool))
    mod = load_tool("render_performer.py")
    keys = [
        {"frame": 0, "azimuth_deg": 225.0, "elevation_deg": 8.0,
         "radius": 2.0, "target": [0.0, 0.0, 1.0]},
        {"frame": 10, "azimuth_deg": 270.0, "elevation_deg": 12.0,
         "radius": 2.2, "target": [0.0, 0.0, 1.0]},
    ]
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump({"keys": keys}, fh)
        path = fh.name
    try:
        loaded = mod.load_camera_path(path)
        assert len(loaded) == 2
        sample = framing.sample_camera_at(loaded, 5)
        assert sample["azimuth_deg"] == pytest.approx(247.5)
    finally:
        os.unlink(path)
    assert mod.load_camera_path(None) is None


def test_camera_path_reverted_red_absent():
    decoy = '''
def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glb", required=True)
    return ap.parse_args([])
'''
    assert "--camera-path" not in _flag_names(decoy)
    assert "--camera-path" in _flag_names(read_source("render_performer.py"))


# =======================================================================================
# F-938485d6 — sheet compose
# =======================================================================================


@pytest.mark.parametrize("tool", [
    "make_binding_sheet.py", "make_parts_sheet.py",
    "make_rig_sheet.py", "make_skeleton_sheet.py",
])
def test_sheet_tools_expose_compose_flags(tool):
    src = read_source(tool)
    flags = _flag_names(src)
    assert "--compose" in flags or "--no-compose" in flags
    assert "maybe_compose_panels" in src


def test_maybe_compose_panels_no_compose_skips():
    mod = load_tool("render_performer.py")
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump({"rows": []}, fh)
        path = fh.name
    try:
        rec = mod.maybe_compose_panels(path, compose=False)
        assert rec["composed"] is False
        assert rec["reason"] == "--no-compose"
        assert rec["panels"] == os.path.abspath(path)
    finally:
        os.unlink(path)


def test_compose_reverted_red_absent():
    decoy = '''
def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    return ap.parse_args([])
'''
    assert "--compose" not in _flag_names(decoy)
    assert "--no-compose" in _flag_names(read_source("make_binding_sheet.py"))


# =======================================================================================
# F-ce65f941 — pipeline driver + diagnose next_tool
# =======================================================================================


def test_rig_character_pipeline_stage_manifest():
    mod = load_tool("rig_character.py")
    assert mod.LIVE_ARM_STAGES == ("rig_repair", "rig_character")
    man = mod.build_stage_manifest(glb="x.glb", out_dir="out", repaired_from="raw.glb")
    assert man["pipeline"] == "repair-bind"
    assert man["stages"][0] == "rig_repair"
    assert "rig_character" in man["next_after_repair"]


def test_diagnose_bone_heat_source_names_next_tool():
    src = read_source("diagnose_bone_heat.py")
    assert "next_tool" in src
    assert "next_invocation" in src
    assert "rig_repair" in src


def test_pipeline_reverted_red_absent():
    decoy = '''
ARGUMENTS = (("--glb", "<path>", True, "x"),)
def parse_args():
    return {"glb": None}
'''
    assert "pipeline" not in decoy
    assert "--pipeline" in read_source("rig_character.py")


# =======================================================================================
# F-cee7b569 — preview_walk review clip
# =======================================================================================


def test_preview_walk_review_clip_flag_and_next():
    src = read_source("preview_walk.py")
    flags = _flag_names(src)
    assert "--review-clip" in flags
    mod = load_tool("render_performer.py")
    nxt = mod.review_clip_next("/tmp/frames")
    assert nxt["tool"] == "make_review_clip"
    assert "--frames=" in nxt["next"]
    skipped = mod.maybe_run_review_clip("/tmp/frames", enabled=False)
    assert skipped["ran"] is False
    assert "make_review_clip" in skipped["next"]


def test_preview_walk_ok_carries_next_token():
    src = read_source("preview_walk.py")
    assert '"next"' in src or "'next'" in src
    assert "review_clip" in src


def test_review_clip_reverted_red_absent():
    decoy = '''
def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", required=True)
    return ap.parse_args([])
'''
    assert "--review-clip" not in _flag_names(decoy)
    assert "--review-clip" in _flag_names(read_source("preview_walk.py"))
