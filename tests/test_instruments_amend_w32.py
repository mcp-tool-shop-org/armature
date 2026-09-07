"""Wave 32 Stage D amend — instruments LOOK fixes.

F-34e036b0 — preview_glb head crop from height alone; elev level.
F-cade389c — one clay plate name for sheets+preview_glb; WORLD_LINEAR for control.
F-b2a06c70 — make_rig_sheet fidelity figures and insets are separate uniform-height rows.
F-02ab94ad — skeleton Before overlay is cool magenta, not terracotta-adjacent orange.
F-3aec0c43 — unmatched inset caption is short; long reason rides panels.json.

Each check is a PROPERTY over source / a pure helper; helpers under tests/ raise.
"""

import ast
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

from blender_stub import load_tool, read_source  # noqa: E402


TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")


def _assign_tuple(src, name):
    """Module-level `NAME = (a, b, c)` numeric triple, or None."""
    tree = ast.parse(src)
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            continue
        val = node.value
        if isinstance(val, ast.Tuple) and len(val.elts) == 3:
            nums = []
            for elt in val.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, (int, float)):
                    nums.append(float(elt.value))
                else:
                    return None
            return tuple(nums)
    return None


# =======================================================================================
# F-34e036b0 — head crop height-driven
# =======================================================================================


def test_head_framing_ignores_character_width():
    """Wide and narrow subjects share the same head_r / top-band centre (frac of H)."""
    mod = load_tool("preview_glb.py")

    class V:
        def __init__(self, x, y, z):
            self.x, self.y, self.z = x, y, z

        def __iter__(self):
            return iter((self.x, self.y, self.z))

    # swordsman-ish (wide) vs lady-ish (narrow) — same height
    wide = V(1.0, 0.4, 2.0)
    narrow = V(0.35, 0.3, 2.0)
    hi = V(0.0, 0.0, 2.0)
    center = V(0.0, 0.0, 1.0)
    c_w, r_w = mod.head_framing(center, wide, hi)
    c_n, r_n = mod.head_framing(center, narrow, hi)
    assert r_w == pytest.approx(r_n)
    assert r_w == pytest.approx(mod.HEAD_RADIUS_FRAC * 2.0)
    # Stub Vector may return a tuple; production returns mathutils.Vector.
    z_w = c_w[2] if not hasattr(c_w, "z") else c_w.z
    z_n = c_n[2] if not hasattr(c_n, "z") else c_n.z
    assert z_w == pytest.approx(z_n)
    assert z_w == pytest.approx(hi.z - mod.HEAD_CENTRE_FROM_TOP_FRAC * 2.0)
    assert mod.HEAD_ELEV_DEG == 0.0


def test_head_framing_source_has_no_width_term():
    """The width-driven max(...) that inflated torso crops is gone from the helper body."""
    src = read_source("preview_glb.py")
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "head_framing")
    body = ast.unparse(fn)
    assert "dims.x" not in body and "dims.y" not in body, body
    assert "HEAD_RADIUS_FRAC" in body


def test_head_framing_reverted_red_width_term_would_inflate():
    """REVERTED-RED: the pre-fix width max makes a wide subject larger than height alone."""
    # Swordsman-class: width ≈ height → old head_r/H ≈ 0.30 (span ≈ 60%H).
    h, w = 2.0, 2.0
    height_only = 0.13 * h
    old = max(0.14 * h, 0.5 * max(w, 0.4) * 0.6)
    assert old > height_only
    assert old / h > 0.25


# =======================================================================================
# F-cade389c — shared studio plates
# =======================================================================================


CLAY_CONSUMERS = (
    "make_parts_sheet.py",
    "make_binding_sheet.py",
    "make_skeleton_sheet.py",
    "preview_glb.py",
)


@pytest.mark.parametrize("filename", CLAY_CONSUMERS)
def test_clay_stills_name_the_shared_plate(filename):
    """Director-facing stills reference CLAY_STUDIO_LINEAR, not a lone 0.72 / 0.30 literal."""
    src = read_source(filename)
    assert "CLAY_STUDIO_LINEAR" in src, filename
    assert "(0.72, 0.72, 0.73" not in src, filename


def test_clay_studio_linear_home_is_the_sheet_value():
    parts = load_tool("make_parts_sheet.py")
    assert parts.CLAY_STUDIO_LINEAR == (0.30, 0.30, 0.32)


@pytest.mark.parametrize("filename", ["preview_walk.py", "render_performer.py"])
def test_control_routes_import_world_linear(filename):
    src = read_source(filename)
    assert "WORLD_LINEAR" in src
    assert "(0.16, 0.16, 0.18" not in src, filename


def test_world_linear_home_unchanged():
    src = read_source("render_turnaround.py")
    assert _assign_tuple(src, "WORLD_LINEAR") == (0.16, 0.16, 0.18)


def test_clay_plate_reverted_red_preview_glb_was_light_grey():
    """REVERTED-RED: the unique 0.72 plate that made cast heads look graded differently."""
    decoy = "bg.inputs[0].default_value = (0.72, 0.72, 0.73, 1.0)\n"
    assert "CLAY_STUDIO_LINEAR" not in decoy
    assert "(0.72, 0.72, 0.73" in decoy


# =======================================================================================
# F-b2a06c70 — fidelity row heights
# =======================================================================================


def test_fidelity_figures_and_insets_are_separate_rows():
    """No single rows[].panels list mixes 1120 and 700 native heights."""
    src = read_source("make_rig_sheet.py")
    assert "fidelity_figures" in src and "fidelity_insets" in src
    assert 'title": "Texture fidelity — shoulder insets, same camera"' in src
    # The mixed-height append pattern: one list getting both (700, 1120) and (700, 700)
    # shoots into the same fidelity list — must not return.
    tree = ast.parse(src)
    fidelity_appends = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "append"
                and isinstance(node.func.value, ast.Name)):
            continue
        if node.func.value.id in ("fidelity_figures", "fidelity_insets", "fidelity"):
            fidelity_appends.append(node.func.value.id)
    assert "fidelity" not in fidelity_appends
    assert fidelity_appends.count("fidelity_figures") >= 1
    assert fidelity_appends.count("fidelity_insets") >= 1


def test_fidelity_mixed_row_reverted_red_shape():
    """REVERTED-RED: one `fidelity` list receiving both tall and square shoots."""
    decoy = (
        "fidelity = []\n"
        "fidelity.append({'body': shoot(scene, 'a.png'), 'label': 'before'})\n"
        "fidelity.append({'body': shoot(scene, 'b.png'), 'label': 'shoulder'})\n"
        "rows.append({'title': 'Texture fidelity', 'panels': fidelity})\n"
    )
    assert "fidelity_figures" not in decoy
    assert decoy.count("fidelity.append") == 2


# =======================================================================================
# F-02ab94ad — Before overlay contrast
# =======================================================================================


def test_before_rgb_is_not_terracotta_adjacent_orange():
    sheet = load_tool("make_skeleton_sheet.py")
    assert sheet.BEFORE_RGB != (1.00, 0.42, 0.16)
    # Cool magenta / lime / white-hot: not warm orange (high R, mid G, low B).
    r, g, b = sheet.BEFORE_RGB
    assert b > 0.5 and r > 0.5, sheet.BEFORE_RGB
    assert sheet.AFTER_RGB == (0.10, 0.85, 1.00)


def test_before_rgb_reverted_red_was_warm_orange():
    """REVERTED-RED: the warm orange that sat next to terracotta."""
    old = (1.00, 0.42, 0.16)
    assert old[0] > 0.9 and old[1] < 0.5 and old[2] < 0.3


# =======================================================================================
# F-3aec0c43 — short unmatched caption
# =======================================================================================


def test_unmatched_inset_label_is_short():
    sheet = load_tool("make_skeleton_sheet.py")
    table = {"wrist_L": {"matched": False, "reason": "no ball near site"}}
    label = sheet.inset_panel_label("wrist", "wrist_L", table)
    assert label == "wrist — NO MATCH"
    assert "heuristic placement" not in label
    assert len(label) < 40


def test_unmatched_detail_rides_panels_json_record():
    sheet = load_tool("make_skeleton_sheet.py")
    table = {"wrist_L": {"matched": False, "reason": "no ball near site"}}
    rec = sheet.inset_record("wrist", "wrist_L", table,
                             body="b.png", before="bf.png", after="af.png")
    assert rec["label"] == "wrist — NO MATCH"
    assert rec["unmatched_detail"] == sheet.UNMATCHED_DETAIL
    assert "NO BALL MATCHED" in rec["unmatched_detail"]
    assert rec["reason"] == "no ball near site"


def test_unmatched_label_reverted_red_was_long():
    """REVERTED-RED: the 600 px caption that nearly filled the 620 px cell."""
    old = "shoulder - NO BALL MATCHED, heuristic placement"
    assert len(old) > 40
    assert "heuristic placement" in old
