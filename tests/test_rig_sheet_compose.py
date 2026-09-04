"""The E07 rig sheet's subtitle: read from the run, or written `NOT RECORDED`.

The line drawn under the title read

    "22 named bones placed from landmarks measured on the mesh  ·  the arc is E03's:
     the +X-side arm ({p['which_arm_is_on_plus_x']}), 0°→90° about +Y,
     {p['frames']} keys at {p['fps']} fps"

— three values read from `spec['probe']` and two typed as literals on the same line, with
no way for a reader to tell which half is which. Both literals are values the record
already carries: `len(armature_core.sitelist.BONES)` is 22, and `rig_character`'s probe
dict writes `start_deg`, `end_deg`, `axis` and `sign`. Wave 3 rewrote this exact line
(moving it into a `subtitle` variable for the new width computation) and left them.

This is the "placeholder shaped like evidence" class the repo has now corrected in three
sibling sheets — `make_e08_sheet`, `make_gate0_sheet` and `make_startframe_sheet` — each of
which records the defect as corrected in its own file.

The second half of this file is the wave-5 carry: `rig_sheet_compose` and `make_cast_sheet`
bound `sheet_compose.font` at IMPORT time, so the two composers held a different function
object from the one `sheet_compose` itself calls.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "tools"))

import rig_sheet_compose as RSC  # noqa: E402
import sheet_compose as SC  # noqa: E402
from armature_core import sitelist  # noqa: E402


def _spec(probe=None, **extra):
    spec = {
        "geometry": {"pad": 26, "label_h": 54, "title_h": 150, "probe_frames": 33},
        "joint_order": ["elbow.L", "knee.L"],
        "side": "left",
        "probe": probe if probe is not None else {
            "which_arm_is_on_plus_x": "the character's LEFT",
            "frames": 33, "fps": 16,
            "start_deg": 0.0, "end_deg": 90.0, "axis": "Y", "sign": 1,
        },
    }
    spec.update(extra)
    return spec


def test_the_arc_range_comes_from_the_probe_not_from_a_literal():
    """A rig authored over another range is presented on a sheet stating the old one."""
    sub = RSC.subtitle_text(_spec(probe={
        "which_arm_is_on_plus_x": "the character's RIGHT", "frames": 17, "fps": 24,
        "start_deg": -45.0, "end_deg": 15.0, "axis": "X", "sign": -1}))
    assert "-45" in sub and "15" in sub and "X" in sub
    assert "0°→90°" not in sub
    assert "+Y" not in sub
    assert "17 keys at 24 fps" in sub


def test_the_bone_count_comes_from_the_spec_when_the_spec_carries_one():
    sub = RSC.subtitle_text(_spec(bone_count=7))
    assert "7 named bones" in sub
    assert "22 named bones" not in sub


def test_the_bone_count_falls_back_to_the_repo_constant_and_says_so():
    """`len(sitelist.BONES)` is a real repo constant the tool could read and did not."""
    sub = RSC.subtitle_text(_spec())
    assert f"{len(sitelist.BONES)} named bones" in sub
    assert "sitelist" in sub


def test_an_arc_the_record_does_not_carry_prints_not_recorded():
    """A value the record does not carry is written NOT RECORDED, never a plausible
    number beside a verdict — the repo's rule, and the reason the literals were a defect
    rather than an inaccuracy."""
    sub = RSC.subtitle_text(_spec(probe={
        "which_arm_is_on_plus_x": "the character's LEFT", "frames": 33, "fps": 16}))
    assert RSC.MISSING in sub
    assert "0°→90°" not in sub


def test_no_arc_or_bone_literal_survives_in_the_source():
    """The census over this file: the two literals may not come back."""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "tools", "rig_sheet_compose.py")
    code, inside = [], False
    for line in open(path, encoding="utf-8").read().splitlines():
        # docstrings and comments RECORD the defect, which is the repo's rule; what may
        # not carry the literal is a line that runs
        if line.count('"""') % 2:
            inside = not inside
            continue
        if inside or line.strip().startswith("#"):
            continue
        code.append(line)
    body = chr(10).join(code)
    assert "0°→90°" not in body
    assert "22 named bones" not in body


# ------------------------------------------- the typeface, resolved at CALL time (wave 5)


def test_the_composers_resolve_the_face_through_the_one_implementation(monkeypatch):
    """`from sheet_compose import font as _font` bound the function OBJECT at import, so
    the two composers held a different callable from the one `sheet_compose` calls — a
    substitution installed on the module reached `sheet_compose` and neither composer."""
    import make_cast_sheet as MCS

    calls = []

    def fake(name, size):
        calls.append((name, size))
        from PIL import ImageFont
        return ImageFont.load_default(size)

    monkeypatch.setattr(SC, "_font", fake)
    RSC._font("arial.ttf", 26)
    MCS._font("arialbd.ttf", 30)
    SC._font("arial.ttf", 12)
    assert calls == [("arial.ttf", 26), ("arialbd.ttf", 30), ("arial.ttf", 12)], calls
