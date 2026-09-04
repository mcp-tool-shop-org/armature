"""`probe_glb`'s anatomical-site matcher. Nothing covered this file before wave 6.

F-187f792c, measured: `_side_of` decided laterality with

    left  = any(t in low for t in LEFT_TOKENS)  or low.endswith("l")
    right = any(t in low for t in RIGHT_TOKENS) or low.endswith("r")

and the bare terminal-character clause misfires on ordinary bone names.
`_side_of("mixamorig:LeftShoulder")` returned **None** — the name contains "left" AND ends
in "r", so both flags set and the function reported sideless. `_side_of("Shoulder")`
returned "R"; `_side_of("ear")` returned "R"; `_side_of("heel")` returned "L".

The consequence is not academic. This is the instrument behind E01's headline count
("zero of 18 anatomical sites findable by name") and `P2b_all_18_sites_named` is read
straight off it: a donor GLB carrying a correct, industry-standard rig gets recorded in
the repo as missing anatomical sites it names perfectly, and a route is commissioned
around a gap that is in the matcher.

The fix is a boundary, not a last character: names are split into tokens on separators and
camelCase, and a side token has to BE one of those tokens.
"""

import pytest

from blender_stub import load_tool


@pytest.fixture(scope="module")
def pg():
    return load_tool("probe_glb.py")


#: A full Mixamo body skeleton, verbatim. The naming convention this matcher exists to
#: read, and the one it was measured failing on.
MIXAMO = [
    "mixamorig:Hips", "mixamorig:Spine", "mixamorig:Spine1", "mixamorig:Spine2",
    "mixamorig:Neck", "mixamorig:Head", "mixamorig:HeadTop_End",
    "mixamorig:LeftShoulder", "mixamorig:LeftArm", "mixamorig:LeftForeArm",
    "mixamorig:LeftHand",
    "mixamorig:RightShoulder", "mixamorig:RightArm", "mixamorig:RightForeArm",
    "mixamorig:RightHand",
    "mixamorig:LeftUpLeg", "mixamorig:LeftLeg", "mixamorig:LeftFoot",
    "mixamorig:LeftToeBase",
    "mixamorig:RightUpLeg", "mixamorig:RightLeg", "mixamorig:RightFoot",
    "mixamorig:RightToeBase",
]

#: The symmetric rig from the finding: six bones, named the industry-standard way.
SYMMETRIC = ["LeftShoulder", "RightShoulder", "LeftElbow", "RightElbow",
             "LeftWrist", "RightWrist"]


@pytest.mark.parametrize("name,want", [
    # the measured failures
    ("mixamorig:LeftShoulder", "L"),
    ("mixamorig:RightShoulder", "R"),
    ("Shoulder", None),
    ("ear", None),
    ("heel", None),
    ("leftShoulder", "L"),
    # the conventions the token list was always meant to read
    ("shoulder.L", "L"),
    ("shoulder.R", "R"),
    ("upper_arm.L", "L"),
    ("DEF-upper_arm.R", "R"),
    ("L_arm", "L"),
    ("arm_R", "R"),
    ("lft_hand", "L"),
    ("rgt_hand", "R"),
    ("LeftUpLeg", "L"),
    ("RightToeBase", "R"),
    # sideless things that must stay sideless
    ("Hips", None),
    ("Spine1", None),
    ("neck", None),
    ("nose", None),
    ("Root", None),
    ("HeadTop_End", None),
    ("Control", None),
    ("pelvis", None),
    # genuinely ambiguous stays ambiguous
    ("Left_to_Right_helper", None),
])
def test_side_of(pg, name, want):
    assert pg._side_of(name) == want


def test_the_terminal_character_clause_is_gone(pg):
    """The exact shape of the defect: a name that ENDS in l or r but names no side.

    These all read as sided under the superseded rule, which is what made `Shoulder` an
    "R" and `heel` an "L"."""
    for name in ("Shoulder", "heel", "ear", "Spiral", "Collar", "Femur", "Molar"):
        assert pg._side_of(name) is None, name


def test_a_symmetrically_named_rig_gets_a_symmetric_verdict(pg):
    """The measured consequence: `shoulder.L -> None` while `shoulder.R -> [RightShoulder]`
    — a half-named verdict on a rig that names both sides perfectly."""
    found = pg.match_sites(SYMMETRIC)
    assert found["shoulder.L"] == ["LeftShoulder"]
    assert found["shoulder.R"] == ["RightShoulder"]
    assert found["elbow.L"] == ["LeftElbow"]
    assert found["elbow.R"] == ["RightElbow"]
    assert found["wrist.L"] == ["LeftWrist"]
    assert found["wrist.R"] == ["RightWrist"]


def test_the_recorded_evidence_no_longer_omits_the_left_shoulder(pg):
    """On a full Mixamo skeleton the site COUNT survived (15 of 18) only because
    `shoulder.L` was rescued by the "arm" token matching `mixamorig:LeftArm` — while the
    recorded detail still listed `RightShoulder` and omitted `LeftShoulder`."""
    found = pg.match_sites(MIXAMO)
    assert "mixamorig:LeftShoulder" in found["shoulder.L"]
    assert "mixamorig:RightShoulder" in found["shoulder.R"]
    assert not (set(found["shoulder.L"]) & set(found["shoulder.R"])), (
        found["shoulder.L"], found["shoulder.R"])


def test_no_site_claims_a_bone_from_the_other_side(pg):
    """The direction the count does not bound: a matcher can find 18 of 18 sites and have
    every one of them pointing at the wrong arm."""
    found = pg.match_sites(MIXAMO)
    for site, hits in found.items():
        if not site.endswith((".L", ".R")):
            continue
        want = site[-1]
        for hit in hits:
            assert pg._side_of(hit) == want, (site, hit, pg._side_of(hit))


def test_the_mixamo_site_census_is_unchanged_by_the_side_fix(pg):
    """15 of 18, measured before AND after: the count is pinned so neither this fix nor a
    later change to SITES can move it silently.

    NOT FIXED HERE, recorded instead: `ear.L`/`ear.R` are "found" because the site token
    "ear" is a SUBSTRING of "ForeArm". That is a second, separate defect in the same file
    (a token matched without a boundary, the site half of what F-187f792c fixed on the
    side half), and it is what makes 15 rather than 13. It is left alone deliberately --
    changing site matching is a different finding and would move a recorded count."""
    found = pg.match_sites(MIXAMO)
    assert len(pg.SITES) == 18
    assert sorted(set(pg.SITES) - set(found)) == ["eye.L", "eye.R", "nose"]
    assert len(found) == 15
    assert found["ear.L"] == ["mixamorig:LeftForeArm"], (
        "the substring collision this test records has changed shape")


def test_the_matcher_finds_nothing_in_a_rig_that_names_nothing(pg):
    """A matcher that returns hits for anything is not a matcher."""
    assert pg.match_sites(["Bone", "Bone.001", "Bone.002", "Armature"]) == {}
