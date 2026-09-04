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


def test_the_mixamo_site_census_is_what_a_token_match_measures(pg):
    """**13 of 18**, re-derived 2026-09-04 with F-d83052e8's fix. The pin MOVED, and this
    is the record of the move rather than a silent re-pin.

    It read 15 of 18 under the superseded rule, which matched a site's tokens as bare
    SUBSTRINGS of the whole lowercased name. Two of those fifteen were

        ear.L -> ['mixamorig:LeftForeArm']    ear.R -> ['mixamorig:RightForeArm']

    because "ear" occurs inside "f-o-r-e-a-r-m", and `_side_of('mixamorig:LeftForeArm')`
    is "L". The wave-6 version of this test pinned that collision deliberately, on the
    ground that fixing it was a different finding. It is now fixed: a site token must BE a
    name token (or a contiguous run of them, so `upleg` reads `Up`+`Leg`). The Mixamo
    skeleton below has no ear bone, no eye bone and no nose bone, so the true anatomical
    count on it is 13, and `ear.L`/`ear.R` join the missing set.
    """
    found = pg.match_sites(MIXAMO)
    assert len(pg.SITES) == 18
    assert sorted(set(pg.SITES) - set(found)) == [
        "ear.L", "ear.R", "eye.L", "eye.R", "nose"]
    assert len(found) == 13
    assert "ear.L" not in found and "ear.R" not in found


def test_a_forearm_is_not_an_ear(pg):
    """The red direction, and the exact defect: a bone list containing ONLY ForeArm bones
    must report no ear site at all. Under the substring rule it reported two."""
    found = pg.match_sites(["mixamorig:LeftForeArm", "mixamorig:RightForeArm"])
    assert "ear.L" not in found, found
    assert "ear.R" not in found, found
    assert found["elbow.L"] == ["mixamorig:LeftForeArm"]


def test_the_compound_conventions_still_read(pg):
    """A boundary rule that dropped `upleg`, `upperarm` and `upper_arm` would trade one
    silent miscount for another. These are the conventions SITES was written from."""
    assert pg.match_sites(["mixamorig:LeftUpLeg"])["hip.L"] == ["mixamorig:LeftUpLeg"]
    assert pg.match_sites(["DEF-upper_arm.R"])["shoulder.R"] == ["DEF-upper_arm.R"]
    assert pg.match_sites(["LeftUpperArm"])["shoulder.L"] == ["LeftUpperArm"]
    assert pg.match_sites(["lower_arm.L"])["elbow.L"] == ["lower_arm.L"]


def test_the_matcher_finds_nothing_in_a_rig_that_names_nothing(pg):
    """A matcher that returns hits for anything is not a matcher."""
    assert pg.match_sites(["Bone", "Bone.001", "Bone.002", "Armature"]) == {}


# --------------------------------------------------------- F-f3cd559e: the argv parser
#
# `key, _, value = token[2:].partition("=")` with `if key == "out" / elif key == "glb"`
# and no else. It silently ignored what it did not recognise and silently ADMITTED empty
# paths into the probed population, and every number these two tools exist to produce is a
# count over that population. `probe_subject.py` carried the identical eight lines.

import pytest as _pytest  # noqa: E402  (appended block)

from armature_core.errors import ArmatureError  # noqa: E402
from blender_stub import read_source  # noqa: E402


@_pytest.fixture(scope="module")
def ps():
    return load_tool("probe_subject.py")


@_pytest.mark.parametrize("tool", ["pg", "ps"])
@_pytest.mark.parametrize("argv,phrase", [
    # THE MEASURED CASE: the space form. `--glb` alone gives key "glb" value "", and
    # `"b.glb"[2:]` is ALSO "glb", so the bare path contributes a SECOND "". The old
    # parser returned ['a.glb', '', ''] and reported n_files == 3 for two files named.
    (["--out=d", "--glb=a.glb", "--glb", "b.glb"], r"carries no value"),
    # a typo, dropped without a word
    (["--out=d", "--glb=a.glb", "--gbl=b.glb"], r"unknown argument"),
    # a bare positional, which contributed another ""
    (["--out=d", "--glb=a.glb", "c.glb"], r"unexpected argument"),
    # swallowed, and the tool probed anyway
    (["--out=d", "--glb=a.glb", "--help"], r"unknown argument"),
    # an empty value written out
    (["--out=d", "--glb="], r"carries no value"),
    (["--out=", "--glb=a.glb"], r"carries no value"),
    # nothing to probe
    (["--out=d"], r"usage: -- --out="),
])
def test_the_parser_refuses_rather_than_inventing_a_population(request, tool, argv, phrase):
    mod = request.getfixturevalue(tool)
    with _pytest.raises(ArmatureError, match=phrase):
        mod.parse_argv(argv)


@_pytest.mark.parametrize("tool", ["pg", "ps"])
def test_the_parser_accepts_what_the_usage_line_documents(request, tool):
    mod = request.getfixturevalue(tool)
    assert mod.parse_argv(["--out=d", "--glb=a.glb", "--glb=b.glb"]) == ("d", ["a.glb", "b.glb"])


@_pytest.mark.parametrize("tool", ["pg", "ps"])
def test_two_out_directories_is_a_refusal_not_a_last_one_wins(request, tool):
    """One run writes one record; silently taking the last is how a run's outputs end up
    somewhere nobody looked."""
    mod = request.getfixturevalue(tool)
    with _pytest.raises(ArmatureError, match=r"--out given twice"):
        mod.parse_argv(["--out=d", "--out=e", "--glb=a.glb"])


def test_both_tools_read_argv_through_the_same_parser():
    """The family: `probe_subject.py:88` carried the identical eight lines. A second
    implementation is how one of them gets fixed and the other does not."""
    import ast

    for filename in ("probe_glb.py", "probe_subject.py"):
        tree = ast.parse(read_source(filename))
        fn = next(n for n in tree.body
                  if isinstance(n, ast.FunctionDef) and n.name == "main")
        calls = {n.func.id for n in ast.walk(fn)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        assert "parse_argv" in calls, (filename, sorted(calls))
        # The ignoring loop was `for token in argv:` inside `main`. Checked as a STATEMENT,
        # not as a substring: `parse_argv`'s docstring quotes the superseded lines verbatim,
        # and a source-text scan reads its own record as the defect.
        loops = [n.lineno for n in ast.walk(fn)
                 if isinstance(n, ast.For) and isinstance(n.iter, ast.Name)
                 and n.iter.id == "argv"]
        assert loops == [], (filename, loops)
