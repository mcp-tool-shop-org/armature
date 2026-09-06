"""The Wan AAPose-20 convention, pinned against the source it was transcribed from.

Three layers, and the order matters:

1. **Independent transcription.** The palette, the limb topology and the width formula are
   written out again here, by hand, from `human_visualization.py`. If `aapose.py` is edited
   these fail — the module cannot quietly become its own authority.
2. **The banked source.** When the fetched file is present (`outputs/E08/convention/`, git
   -ignored by design), its sha256 is checked and its `limbSeq` / `colors` / stickwidth
   expression are parsed back out of the file and compared. This is the layer that would
   catch a transcription error in *both* the module and the fixture above, and it is the
   reason the file was banked rather than merely cited.
3. **Golden frames.** Byte-stable hashes of a drawn canvas. Any change to the drawing — a
   cv2 upgrade that rounds an ellipse differently, an edit to the limb loop, a channel flip
   — moves these, and a human decides whether the move was intended.

**The specific way this code could be wrong, and the fixture that catches it.**
`armature_core.openpose` holds ControlNet's OpenPose-18 convention. It agrees with Wan's on
seventeen of nineteen limb pairs. A from-scratch renderer that reached for the familiar table
would differ only in the last two pairs and in two keypoints — the feet — and the model would
simply drive the legs a little worse with nothing erroring anywhere. So there is a test that
the two conventions are DIFFERENT, in exactly those places, and a test that
`check_convention` refuses ControlNet's table outright.
"""

import hashlib
import json
import os
import re

import numpy as np
import pytest

from armature_core import aapose, openpose, sitelist
from armature_core.errors import ArmatureError

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANKED = os.path.join(REPO, "outputs", "E08", "convention", "human_visualization.py")


# --------------------------------------------------------------- 1. transcription

#: Transcribed by hand from `draw_aapose_new`. NOT imported from the module under test.
SOURCE_LIMB_SEQ = [
    [2, 3], [2, 6],
    [3, 4], [4, 5],
    [6, 7], [7, 8],
    [2, 9], [9, 10], [10, 11],
    [2, 12], [12, 13], [13, 14],
    [2, 1],
    [1, 15], [15, 17], [1, 16], [16, 18],
    [14, 19], [11, 20],
]

#: Transcribed by hand from `draw_aapose_new`'s `colors`.
SOURCE_COLORS = [
    [255, 0, 0], [255, 85, 0], [255, 170, 0], [255, 255, 0],
    [170, 255, 0], [85, 255, 0], [0, 255, 0], [0, 255, 85],
    [0, 255, 170], [0, 255, 255], [0, 170, 255], [0, 85, 255],
    [0, 0, 255], [85, 0, 255], [170, 0, 255], [255, 0, 255],
    [255, 0, 170], [255, 0, 85],
    [200, 200, 0], [100, 100, 0],
]

#: Transcribed by hand from `new_kep_list`.
SOURCE_KEYPOINT_NAMES = [
    "Nose", "Neck", "RShoulder", "RElbow", "RWrist", "LShoulder", "LElbow", "LWrist",
    "RHip", "RKnee", "RAnkle", "LHip", "LKnee", "LAnkle",
    "REye", "LEye", "REar", "LEar", "LToe", "RToe",
]

#: Transcribed by hand from `draw_handpose_new`'s `edges`.
SOURCE_HAND_EDGES = [
    [0, 1], [1, 2], [2, 3], [3, 4],
    [0, 5], [5, 6], [6, 7], [7, 8],
    [0, 9], [9, 10], [10, 11], [11, 12],
    [0, 13], [13, 14], [14, 15], [15, 16],
    [0, 17], [17, 18], [18, 19], [19, 20],
]


def _transcription_mismatch(what):
    """Message for a pin against the hand-transcribed upstream tables (F-0d3d5156)."""
    return (
        f"{what} disagrees with the hand transcription in this file: "
        f"`aapose` (this repo's module) moved, or SOURCE_* (the upstream transcription) "
        f"is wrong — edit only one side. Upstream identity is aapose.SOURCE['commit']="
        f"{aapose.SOURCE['commit'][:12]}… sha256={aapose.SOURCE['sha256'][:16]}…"
    )


def test_limbseq_matches_the_source_element_for_element():
    assert [list(p) for p in aapose.LIMB_SEQ] == SOURCE_LIMB_SEQ, _transcription_mismatch(
        "aapose.LIMB_SEQ")


def test_limbseq_is_nineteen_pairs_over_twenty_keypoints():
    assert len(aapose.LIMB_SEQ) == 19
    flat = [v for pair in aapose.LIMB_SEQ for v in pair]
    assert min(flat) == 1, "the source's limbSeq is 1-indexed; it reads kp2ds_body[k - 1]"
    assert max(flat) == 20


def test_palette_matches_the_source_element_for_element():
    assert [list(c) for c in aapose.PALETTE] == SOURCE_COLORS, _transcription_mismatch(
        "aapose.PALETTE")
    assert len(aapose.PALETTE) == 20


def test_keypoint_names_and_count_are_twenty_not_eighteen():
    """G6 called this "the classic 18-point limbSeq". The source carries 20 with two toes,
    and rendering 18 against it omits both feet with nothing erroring."""
    assert list(aapose.KEYPOINT_NAMES) == SOURCE_KEYPOINT_NAMES, _transcription_mismatch(
        "aapose.KEYPOINT_NAMES")
    assert aapose.KEYPOINT_COUNT == 20
    assert aapose.KEYPOINT_NAMES[18] == "LToe"
    assert aapose.KEYPOINT_NAMES[19] == "RToe"


def test_hand_edges_match_the_source():
    assert [list(e) for e in aapose.HAND_EDGES] == SOURCE_HAND_EDGES, _transcription_mismatch(
        "aapose.HAND_EDGES")
    assert aapose.HAND_KEYPOINT_COUNT == 21


# ------------------------------------------------- the conflation trap, both directions

def test_wan_and_controlnet_conventions_are_not_the_same_object():
    """The whole reason this module exists beside `openpose`. They agree on 17 pairs."""
    wan = [list(p) for p in aapose.LIMB_SEQ]
    ctrl = [list(p) for p in openpose.LIMB_SEQ]
    assert wan[:17] == ctrl[:17], "the shared prefix is what makes conflation so easy"
    assert wan[17:] == [[14, 19], [11, 20]], "Wan closes the FEET"
    assert ctrl[17:] == [[3, 17], [6, 18]], "ControlNet closes shoulder-to-ear"
    assert wan != ctrl
    assert aapose.KEYPOINT_COUNT != openpose.KEYPOINT_COUNT


def test_check_convention_refuses_the_controlnet_table():
    """If a future edit reached for the familiar table, this is what would stop it."""
    with pytest.raises(ArmatureError) as exc:
        aapose.check_convention(18, openpose.LIMB_SEQ, aapose.PALETTE)
    msg = str(exc.value)
    assert "keypoint count 18" in msg
    assert "limb pair 17" in msg


def test_check_convention_refuses_a_zero_indexed_topology():
    zeroed = [(a - 1, b - 1) for a, b in aapose.LIMB_SEQ]
    with pytest.raises(ArmatureError) as exc:
        aapose.check_convention(20, zeroed, aapose.PALETTE)
    assert "0-indexed" in str(exc.value)


def test_check_convention_refuses_a_single_swapped_palette_entry():
    """A red/blue swap is the failure that fails silently; one entry is enough to catch."""
    pal = [list(c) for c in aapose.PALETTE]
    pal[0] = [0, 0, 255]
    with pytest.raises(ArmatureError) as exc:
        aapose.check_convention(20, aapose.LIMB_SEQ, pal)
    assert "palette entry 0" in str(exc.value)


def test_check_convention_accepts_the_module_itself():
    assert aapose.check_convention(aapose.KEYPOINT_COUNT, aapose.LIMB_SEQ, aapose.PALETTE)


# ------------------------------------------------------------------ the width formula

@pytest.mark.parametrize("h,w,v1,v2", [
    (480, 832, 2, 1),      # THE shot: 832x480 -> min 480 -> 480/200 = 2 -> v2 = 1
    (1080, 1920, 5, 4),
    (144, 256, 1, 1),      # the floor binds: 144/200 = 0 -> max(0,1)=1, max(-1,1)=1
    (200, 200, 1, 1),
    (600, 600, 3, 2),
])
def test_stickwidth_formula(h, w, v1, v2):
    assert aapose.stickwidth(h, w, "v1") == v1
    assert aapose.stickwidth(h, w, "v2") == v2


@pytest.mark.parametrize("h,w,v2", [
    (480, 832, 1),         # max(max(2-1,1)//2, 1) = max(0,1) = 1
    (1080, 1920, 2),       # max(max(5-1,1)//2, 1) = 2
    (144, 256, 1),
])
def test_hand_stickwidth_is_half_the_body_width_floored_at_one(h, w, v2):
    assert aapose.hand_stickwidth(h, w, "v2") == v2


def test_unknown_stickwidth_type_raises_rather_than_falling_through():
    """The source takes this branch to a bare `raise`; an unrecognised profile is the case
    where nothing is checked at all."""
    with pytest.raises(ArmatureError, match=r"unknown stickwidth_type 'v3'"):
        aapose.stickwidth(480, 832, "v3")
    with pytest.raises(ArmatureError, match=r"unknown stickwidth_type 'v3'"):
        aapose.hand_stickwidth(480, 832, "v3")


# ------------------------------------------------------------------ 2. the banked source

def _banked_text():
    if not os.path.isfile(BANKED):
        pytest.skip(
            f"the fetched convention source is not banked at {BANKED} (outputs/ is "
            f"git-ignored by design). Re-fetch it to run the strongest layer of this test."
        )
    with open(BANKED, "rb") as fh:
        return fh.read()


def test_banked_source_hash_matches_the_pin():
    raw = _banked_text()
    assert hashlib.sha256(raw).hexdigest() == aapose.SOURCE["sha256"]
    assert len(raw) == aapose.SOURCE["bytes"]


def _last_block(text, name, start):
    """The last `name = [...]` block in `text` at or after `start`, as raw source."""
    i = text.index(name, start)
    j = text.index("[", i)
    depth, k = 0, j
    while True:
        if text[k] == "[":
            depth += 1
        elif text[k] == "]":
            depth -= 1
            if depth == 0:
                return text[j:k + 1]
        k += 1


def test_the_transcription_matches_the_banked_file_itself():
    """The layer that catches an error made identically in the module AND the fixture.

    `draw_aapose_new` is the function `draw_aapose_by_meta_new` calls, so its own limbSeq
    and colors are parsed out and compared — not another function's.
    """
    text = _banked_text().decode("utf-8")
    at = text.index("def draw_aapose_new(")

    limb_src = _last_block(text, "limbSeq", at)
    pairs = [[int(a), int(b)] for a, b in re.findall(r"\[\s*(\d+)\s*,\s*(\d+)\s*\]",
                                                     limb_src)]
    assert pairs == SOURCE_LIMB_SEQ
    assert [list(p) for p in aapose.LIMB_SEQ] == pairs

    color_src = _last_block(text, "colors", at)
    cols = [[int(r), int(g), int(b)] for r, g, b in
            re.findall(r"\[\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\]", color_src)]
    assert cols == SOURCE_COLORS
    assert [list(c) for c in aapose.PALETTE] == cols

    names_src = _last_block(text, "new_kep_list", at)
    names = re.findall(r'"([A-Za-z]+)"', names_src)
    assert names == SOURCE_KEYPOINT_NAMES

    # The v2 width expression and the hand pass's halving, as EXPRESSIONS rather than as
    # source text (wave 10, F-18061bcb). The pins here were the two lines verbatim:
    # inserting a space or wrapping either turns them red with the formula unchanged, and
    # a comment carrying the same text turns them green with the formula broken. Compared
    # through `ast.unparse`, which normalises whitespace and cannot be satisfied by a
    # comment or a string.
    assert _stickwidth_expr(text, "draw_aapose_new") == \
        "max(int(min(H, W) / 200) - 1, 1)"
    assert _stickwidth_expr(text, "draw_handpose_new") == \
        "max(max(int(min(H, W) / 200) - 1, 1) // 2, 1)"
    # …and that limbs are filled at 60% while joints are not.
    body = text[at:text.index("def draw_bbox(", at)]
    assert "[int(float(c) * 0.6) for c in color]" in body



def _stickwidth_expr(text, function_name):
    """`ast.unparse` of the `stickwidth = ...` assignment inside one banked function.

    The banked file is Python, so its formulas can be compared as expressions instead of
    as source text. Whitespace and line wrapping move freely; a comment or a docstring
    carrying the same characters satisfies nothing (F-18061bcb).
    """
    import ast as _ast

    tree = _ast.parse(text)
    fn = next(n for n in _ast.walk(tree)
              if isinstance(n, (_ast.FunctionDef, _ast.AsyncFunctionDef))
              and n.name == function_name)
    found = [n.value for n in _ast.walk(fn)
             if isinstance(n, _ast.Assign) and len(n.targets) == 1
             and isinstance(n.targets[0], _ast.Name)
             and n.targets[0].id == "stickwidth"]
    assert len(found) == 1, (function_name, [_ast.unparse(f) for f in found])
    return _ast.unparse(found[0])


def test_the_stickwidth_reader_can_tell_a_changed_formula_from_a_reformatted_one():
    """Rule 3 on the reader: reformatting must not move the answer, and a real change must.
    The retired pin got both of these backwards."""
    same = ("def draw(H, W):\n"
            "    stickwidth = max(\n"
            "        int(min(H, W) / 200) - 1,\n"
            "        1,\n"
            "    )\n")
    changed = ("def draw(H, W):\n"
               "    # stickwidth = max(int(min(H, W) / 200) - 1, 1)\n"
               "    stickwidth = max(int(min(H, W) / 100) - 1, 1)\n")
    assert _stickwidth_expr(same, "draw") == "max(int(min(H, W) / 200) - 1, 1)"
    assert _stickwidth_expr(changed, "draw") == "max(int(min(H, W) / 100) - 1, 1)"
    assert "stickwidth = max(int(min(H, W) / 200) - 1, 1)" in changed, (
        "the retired substring pin reads the COMMENT and passes on a changed formula")


def test_the_channel_order_evidence_is_still_in_the_banked_file():
    """The determination that the canvas is RGB rests on one line. If that line changes,
    the module's colour claim needs re-deriving rather than inheriting."""
    text = _banked_text().decode("utf-8")
    assert 'cv2.imwrite("traj.png", res[0][..., ::-1])' in text


# ------------------------------------------------------------------------- 3. the rig

def registered_landmarks():
    """Every landmark name the registered site list places a bone end on."""
    out = set()
    for b in sitelist.BONES:
        out.add(b.head)
        out.add(b.tail)
    return out


def test_the_map_resolves_against_the_registered_site_list():
    sitelist.validate()
    assert aapose.require_rig_map(registered_landmarks())
    assert len(aapose.LANDMARK_SITES) == 20
    for site in aapose.LANDMARK_SITES:
        assert site in registered_landmarks()


def test_the_map_names_landmarks_not_bone_ends():
    """The correction of 2026-08-12. Reading toes off the ankle bones' TAILS works in the
    authored rig and breaks through glTF, which has no tail and makes one up for every leaf
    bone. Landmarks survive because they are measured and carried in the rig manifest."""
    assert aapose.LANDMARK_SITES[18] == "toe_L"
    assert aapose.LANDMARK_SITES[19] == "toe_R"
    by = sitelist.by_name()
    assert by["ankle.L"].tail == "toe_L"
    assert by["ankle.R"].tail == "toe_R"
    assert all(isinstance(s, str) for s in aapose.LANDMARK_SITES)


def test_left_and_right_are_not_crossed():
    """AAPose L/R are the SUBJECT's own sides, and so are the rig's `_L`/`_R` suffixes."""
    for i, name in enumerate(aapose.KEYPOINT_NAMES):
        site = aapose.LANDMARK_SITES[i]
        if name in ("Nose", "Neck"):
            continue
        assert site.endswith("_L") if name.startswith("L") else site.endswith("_R"), \
            (name, site)


def test_every_keypoint_has_its_own_landmark():
    """Two keypoints sharing a landmark would collapse a limb to a point and draw nothing."""
    assert len(set(aapose.LANDMARK_SITES)) == 20


def test_require_rig_map_raises_on_a_missing_landmark():
    """A keypoint with nothing behind it would be written as a zero and drawn as a limb
    running to the corner of the frame, with nothing erroring."""
    crippled = registered_landmarks() - {"ear_R"}
    with pytest.raises(ArmatureError) as exc:
        aapose.require_rig_map(crippled)
    assert "ear_R" in str(exc.value)


def test_require_rig_map_also_covers_the_hand_sites():
    """The hands read three landmarks each; a missing hand end is as silent as a missing
    joint, and would splay a hand of zero length across the frame."""
    crippled = registered_landmarks() - {"hand_end_L"}
    with pytest.raises(ArmatureError) as exc:
        aapose.require_rig_map(crippled)
    assert "hand_end_L" in str(exc.value)


# ------------------------------------------------------------------- the hand frame

def test_hand_frame_returns_an_orthonormal_pair_and_the_hands_own_length():
    d, s, L = aapose.hand_frame((0, 0, 0), (0, 0.1, 0), (0, -0.3, 0.05))
    assert L == pytest.approx(0.1)
    assert np.linalg.norm(d) == pytest.approx(1.0)
    assert np.linalg.norm(s) == pytest.approx(1.0)
    assert float(np.dot(d, s)) == pytest.approx(0.0, abs=1e-12)


def test_hand_frame_survives_a_hand_collinear_with_its_forearm():
    """A straight arm makes the palm plane undefined. Left to itself the cross product is
    zero, the normalisation is a divide-by-zero, and NaNs reach pixel coordinates where cv2
    draws something arbitrary without complaint."""
    d, s, L = aapose.hand_frame((0, 0, 0), (0, 0, 0.1), (0, 0, -0.3))
    assert np.isfinite(d).all() and np.isfinite(s).all()
    assert float(np.dot(d, s)) == pytest.approx(0.0, abs=1e-12)


def test_hand_frame_refuses_a_zero_length_hand():
    with pytest.raises(ArmatureError, match=r"no length and no direction"):
        aapose.hand_frame((0, 0, 0), (0, 0, 0), (0, -1, 0))


def test_hand_frame_rolls_with_the_forearm():
    """Same hand direction, elbow swung out of the previous plane: the palm must roll with
    it. If it did not, the constructed hand would sit in a fixed world orientation and the
    thumb would point the same way whatever the arm did."""
    a = aapose.hand_frame((0, 0, 0), (0, 0.1, 0), (0.3, -0.2, 0.0))[1]
    b = aapose.hand_frame((0, 0, 0), (0, 0.1, 0), (0.0, -0.2, 0.3))[1]
    assert not np.allclose(a, b)


def test_hand_frame_is_rigid_under_a_rotation_of_the_whole_arm():
    """Rotating wrist, hand and elbow together by 90 degrees about Z must rotate the frame
    by the same 90 degrees — no more, no less."""
    def rot_z(p):
        x, y, z = p
        return (-y, x, z)

    w, h, e = (0.0, 0.0, 0.0), (0.0, 0.1, 0.0), (0.3, -0.2, 0.05)
    d1, s1, L1 = aapose.hand_frame(w, h, e)
    d2, s2, L2 = aapose.hand_frame(rot_z(w), rot_z(h), rot_z(e))
    assert L2 == pytest.approx(L1)
    assert np.allclose(d2, rot_z(d1))
    assert np.allclose(s2, rot_z(s1))


# -------------------------------------------------------------------------- the hand

def test_mitten_hand_is_twentyone_points_and_scales_with_its_own_length():
    a = aapose.mitten_hand((0, 0, 0), (0, 1, 0), (1, 0, 0), 1.0)
    b = aapose.mitten_hand((0, 0, 0), (0, 1, 0), (1, 0, 0), 2.0)
    assert a.shape == (21, 3)
    assert np.allclose(b, 2.0 * a)


def test_mitten_hand_is_rigid_in_its_own_frame_and_rotates_with_the_wrist():
    """Static in the hand's space, not in image space — which is the honest description of
    a mannequin's mitten and what the report has to say about it."""
    a = aapose.mitten_hand((0, 0, 0), (0, 1, 0), (1, 0, 0), 1.0)
    rotated = aapose.mitten_hand((0, 0, 0), (1, 0, 0), (0, -1, 0), 1.0)
    assert not np.allclose(a, rotated)
    # a 90-degree turn about Z maps (x, y) -> (y, -x) under the given basis swap
    assert np.allclose(np.linalg.norm(a, axis=1), np.linalg.norm(rotated, axis=1))
    moved = aapose.mitten_hand((5, 0, 0), (0, 1, 0), (1, 0, 0), 1.0)
    assert np.allclose(moved - a, np.array([5.0, 0.0, 0.0]))


def test_mitten_hand_refuses_a_zero_length_hand():
    with pytest.raises(ArmatureError, match=r"needs a positive length"):
        aapose.mitten_hand((0, 0, 0), (0, 1, 0), (1, 0, 0), 0.0)


# ---------------------------------------------------------------------- 4. the drawing

def golden_pose(width, height):
    """A deterministic standing figure in pixels. Not measured from anything — a fixture."""
    cx, cy = width * 0.5, height * 0.5
    s = min(width, height) / 6.0
    P = {
        0: (cx, cy - 2.30 * s), 1: (cx, cy - 1.80 * s),
        2: (cx - 0.70 * s, cy - 1.75 * s), 3: (cx - 1.05 * s, cy - 0.95 * s),
        4: (cx - 1.30 * s, cy - 0.15 * s),
        5: (cx + 0.70 * s, cy - 1.75 * s), 6: (cx + 1.05 * s, cy - 0.95 * s),
        7: (cx + 1.30 * s, cy - 0.15 * s),
        8: (cx - 0.45 * s, cy - 0.10 * s), 9: (cx - 0.50 * s, cy + 1.00 * s),
        10: (cx - 0.52 * s, cy + 2.05 * s),
        11: (cx + 0.45 * s, cy - 0.10 * s), 12: (cx + 0.50 * s, cy + 1.00 * s),
        13: (cx + 0.52 * s, cy + 2.05 * s),
        14: (cx - 0.18 * s, cy - 2.42 * s), 15: (cx + 0.18 * s, cy - 2.42 * s),
        16: (cx - 0.38 * s, cy - 2.36 * s), 17: (cx + 0.38 * s, cy - 2.36 * s),
        18: (cx + 0.62 * s, cy + 2.38 * s), 19: (cx - 0.62 * s, cy + 2.38 * s),
    }
    return [[P[i][0], P[i][1], 1.0] for i in range(20)]


def golden_frame(width, height, hands=True):
    body = golden_pose(width, height)
    L = 0.06 * min(width, height)
    lh = aapose.mitten_hand((body[7][0], body[7][1], 0.0), (0, 1, 0), (1, 0, 0), L)
    rh = aapose.mitten_hand((body[4][0], body[4][1], 0.0), (0, 1, 0), (-1, 0, 0), L)
    return aapose.draw_frame(
        height, width, body,
        left_hand=[[p[0], p[1], 1.0] for p in lh],
        right_hand=[[p[0], p[1], 1.0] for p in rh],
        draw_hands=hands)


#: The four golden frames, and the environment they were LAST VERIFIED in.
#:
#: WAVE 26, F-b460731c — the line here read "Measured 2026-08-12 on this rig (numpy 2.4.6 /
#: cv2 4.13.0, trellis2-env py3.13.13)". Re-measured 2026-09-05 in the repo venv that
#: verifies these hashes today: **numpy 2.5.2, cv2 5.0.0 (opencv-contrib-python 5.0.0.93),
#: Python 3.14.5** — and all four hashes still pass. So every version named in the old
#: comment was stale, and the pin is MORE version-stable than the comment claimed: the
#: rasterisation of these four frames did not move across the cv2 4.13 -> 5.0 boundary, nor
#: across numpy 2.4 -> 2.5, nor across CPython 3.13 -> 3.14.
#:
#: That matters because the comment's whole job is to let a human rule on whether a moved
#: hash was intended: with a stale baseline the operator diffs against the wrong environment.
#: `.github/workflows/ci.yml` compounded it — it installs `opencv-python-headless==5.0.0.93`
#: under a comment saying opencv "is pinned to the rig's verified version", contradicting the
#: 4.13.0 written here, and it is a DIFFERENT DISTRIBUTION of the library from the one
#: installed locally (`opencv-contrib-python`). The two are reconciled below by measurement
#: rather than by a second literal: `test_the_recorded_environment_is_the_one_verifying_these_hashes`
#: derives the CI pin from `ci.yml` and states plainly which distribution each side installs.
#:
#: A cv2 or numpy change that alters the rasterisation moves these, and a human rules on
#: whether the move was intended. They are a regression pin, not a claim about correctness.
ENVIRONMENT_VERIFIED_2026_09_05 = {
    "python": "3.14.5",
    "numpy": "2.5.2",
    "cv2": "5.0.0",
    "cv2 distribution": "opencv-contrib-python 5.0.0.93",
    "where": "this rig, the repo venv",
}

#: WAVE-26 CI FIX-UP (coordinator, 2026-09-05). The first CI run over the record above read it on ubuntu-latest —
#: Python 3.11.16 with numpy 2.4.6, and Python 3.13.15 with numpy 2.5.2, both with opencv-python-headless
#: 5.0.0.93 (the `ci.yml` pin) — and ALL FOUR HASHES PASSED on both; only the record test was red, because it
#: held the observed triple to this rig's exact versions. So the record is a TABLE of every environment the
#: hashes were verified in, and the test holds the observed environment to it at the MINOR boundary
#: (major.minor of python / numpy / cv2): the boundaries the prose above says the rasterisation crossed are
#: minor ones, and a runner's monthly patch release is not one. The full observed versions are printed on
#: every run, so a patch drift is on the record without a red. A minor boundary nobody has verified — numpy
#: 2.6, cv2 5.1, CPython 3.15 — goes red here, naming the row to add once the hashes pass there.
ENVIRONMENTS_VERIFIED_2026_09_05 = (
    ENVIRONMENT_VERIFIED_2026_09_05,
    {"python": "3.11.16", "numpy": "2.4.6", "cv2": "5.0.0",
     "cv2 distribution": "opencv-python-headless 5.0.0.93",
     "where": "ubuntu-latest, ci.yml python-tests (3.11), run 33998757157"},
    {"python": "3.13.15", "numpy": "2.5.2", "cv2": "5.0.0",
     "cv2 distribution": "opencv-python-headless 5.0.0.93",
     "where": "ubuntu-latest, ci.yml python-tests (3.13), run 33998757157"},
)

VERSION_AXES = ("python", "numpy", "cv2")


def _minor(version):
    """`major.minor` of a dotted version string — the boundary the record is kept at."""
    return ".".join(version.split(".")[:2])


def environment_is_recorded(observed, table=ENVIRONMENTS_VERIFIED_2026_09_05):
    """True when `observed` matches a row of `table` on every version axis at the minor boundary."""
    want = {k: _minor(observed[k]) for k in VERSION_AXES}
    return any({k: _minor(row[k]) for k in VERSION_AXES} == want for row in table)


def observed_environment():
    """The numpy / cv2 / Python triple this run is actually using, plus the distribution.

    Quoted in the golden assertion's failure message (F-b460731c), so a moved hash carries
    its own environment instead of sending the reader to a dated comment.
    """
    import sys

    import cv2
    import numpy

    try:
        import importlib.metadata as md
        dists = [f"{name} {md.version(name)}" for name in
                 ("opencv-python", "opencv-python-headless", "opencv-contrib-python")
                 if _installed(md, name)]
    except Exception:                                        # pragma: no cover
        dists = []
    return {
        "python": ".".join(str(v) for v in sys.version_info[:3]),
        "numpy": numpy.__version__,
        "cv2": cv2.__version__,
        "cv2 distribution": ", ".join(dists) or "unknown",
    }


def _installed(md, name):
    try:
        md.version(name)
        return True
    except Exception:
        return False


GOLDEN = {
    (832, 480, True): "5ebc3e11588ca39331738a3f3889e6be688c5865568dbaa75b8138d1f6f3bbad",
    (832, 480, False): "da7ed08df72ed8e09efd92e924d23d3fce4efd70f764484f3f440c2d0882d7f4",
    (256, 144, True): "cf746d493f48bba80f0d213a6a88a99d9be149a51efd965868069172ea369d40",
    (256, 144, False): "563fae32a0febbe76617f70240a6a8a703c6411d7205497d04fffb7b338f1d2b",
}


@pytest.mark.parametrize("width,height,hands", sorted(GOLDEN))
def test_golden_frames_are_byte_stable(width, height, hands):
    canvas = golden_frame(width, height, hands)
    assert canvas.shape == (height, width, 3)
    assert canvas.dtype == np.uint8
    got = hashlib.sha256(canvas.tobytes()).hexdigest()
    # WAVE 26, F-b460731c: the message carries the environment that produced the hash, so a
    # human ruling on a moved rasterisation has the axis in front of them rather than in a
    # comment that may be three cv2 majors old.
    assert got == GOLDEN[(width, height, hands)], {
        "frame": (width, height, hands),
        "expected": GOLDEN[(width, height, hands)],
        "got": got,
        "observed environment": observed_environment(),
        "last verified in": ENVIRONMENT_VERIFIED_2026_09_05,
    }


def test_the_recorded_environment_is_the_one_verifying_these_hashes():
    """The dated comment above may not go stale silently again (F-b460731c).

    RECORDS the observed triple in the run's own output, and holds the recorded table to it.
    A MINOR version boundary on any verifying host — this rig or a CI runner — now fails HERE,
    naming the observed triple and the rows, instead of leaving a reader of the golden pin
    diffing against an environment nobody has run since 2026-08-12. (WAVE-26 CI FIX-UP (coordinator, 2026-09-05):
    the boundary is major.minor; the first CI run over the exact-triple form went red on
    both runners while every hash passed.)
    """
    observed = observed_environment()
    print("aapose golden environment: " + json.dumps(observed, sort_keys=True))
    recorded = [{k: _minor(row[k]) for k in VERSION_AXES} for row in ENVIRONMENTS_VERIFIED_2026_09_05]
    assert environment_is_recorded(observed), (
        f"the golden frames are being verified in an environment the record does not name: "
        f"observed { {k: observed[k] for k in VERSION_AXES} } is on none of the recorded minor "
        f"boundaries {recorded}. If the four hashes still pass here, add a row to "
        f"ENVIRONMENTS_VERIFIED_2026_09_05 with these versions and where they were seen — that is "
        f"evidence the pin is stable across the boundary, and it is the whole reason the record exists.")


def test_the_environment_record_goes_red_on_an_unverified_minor_boundary():
    """WAVE-26 CI FIX-UP (coordinator, 2026-09-05): the direction the record must catch, driven. A numpy minor
    nobody has verified is not recorded; a patch release of a recorded minor is."""
    rig = ENVIRONMENT_VERIFIED_2026_09_05
    assert environment_is_recorded(dict(rig, numpy="2.5.99"))            # a patch release: recorded
    assert not environment_is_recorded(dict(rig, numpy="2.6.0"))         # a minor boundary: not
    assert not environment_is_recorded(dict(rig, python="3.15.0"))
    assert not environment_is_recorded(dict(rig, cv2="5.1.0"))
    assert not environment_is_recorded(rig, table=())                    # an empty record verifies nothing


def test_the_ci_opencv_pin_and_the_local_one_are_reconciled_by_measurement():
    """The other half of F-b460731c: `ci.yml` pins a DIFFERENT DISTRIBUTION.

    `.github/workflows/ci.yml` installs `opencv-python-headless==<v>` under a comment saying
    opencv "is pinned to the rig's verified version"; this rig has `opencv-contrib-python`.
    Both ship the same `cv2` rasteriser at the same version, which is the axis these hashes
    are pinned on — so the two are compatible, and that is stated by DERIVING the CI version
    from the workflow rather than typing a second literal here (a second literal is how the
    4.13.0 / 5.0.0.93 contradiction survived in the first place).

    The workflow is ci-packaging's file and is read here as TEXT only.
    """
    import re

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(repo, ".github", "workflows", "ci.yml"), encoding="utf-8") as fh:
        ci = fh.read()
    pinned = re.findall(r"opencv-python-headless==([0-9][0-9.]*)", ci)
    assert len(pinned) == 1, pinned
    ci_version = pinned[0]

    local = ENVIRONMENT_VERIFIED_2026_09_05["cv2 distribution"].rsplit(" ", 1)[-1]
    assert ci_version == local, (
        f"ci.yml pins opencv {ci_version} and this rig's record names {local}; the golden "
        f"hashes are verified against one rasteriser version, so the two must agree "
        f"(the distributions deliberately differ — headless on a runner, contrib here)")
    assert ci_version.startswith(observed_environment()["cv2"]), (
        ci_version, observed_environment()["cv2"])


def test_the_canvas_is_zeroed_black_outside_the_figure():
    canvas = golden_frame(832, 480)
    assert canvas[0, 0].tolist() == [0, 0, 0]
    assert canvas[-1, -1].tolist() == [0, 0, 0]
    assert float((canvas.any(axis=2)).mean()) < 0.05


def test_hands_add_ink_and_disabling_them_removes_it():
    """If `draw_hands=False` changed nothing, the hand pass would be silently dead."""
    with_hands = golden_frame(832, 480, hands=True)
    without = golden_frame(832, 480, hands=False)
    assert float(with_hands.any(axis=2).mean()) > float(without.any(axis=2).mean())


def test_a_below_threshold_keypoint_is_not_drawn():
    """The threshold is the mechanism by which a detector's uncertainty removes a limb.
    Ours are all 1.0, so this proves the mechanism is live rather than vestigial."""
    body = golden_pose(832, 480)
    full = aapose.draw_frame(480, 832, body, draw_hands=False)
    body[4][2] = 0.0                       # RWrist unseen
    dropped = aapose.draw_frame(480, 832, body, draw_hands=False)
    assert float(dropped.any(axis=2).mean()) < float(full.any(axis=2).mean())


def test_draw_head_false_removes_the_five_head_points():
    body = golden_pose(832, 480)
    with_head = aapose.draw_frame(480, 832, body, draw_hands=False, draw_head=True)
    without = aapose.draw_frame(480, 832, body, draw_hands=False, draw_head=False)
    assert float(without.any(axis=2).mean()) < float(with_head.any(axis=2).mean())


def test_limbs_are_dimmer_than_their_joints():
    """`fillConvexPoly` at 0.6 of the colour, `circle` at full. A drawing that lost the
    0.6 would be brighter everywhere and no count would change."""
    body = [[416.0, 100.0, 1.0]] * 20
    body[1] = [416.0, 100.0, 1.0]          # Neck
    body[2] = [300.0, 300.0, 1.0]          # RShoulder — a long limb 0 to sample along
    canvas = aapose.draw_frame(480, 832, body, draw_hands=False)
    lit = canvas[canvas.any(axis=2)]
    assert lit.max() == 255                 # a joint circle at full brightness
    assert (lit.max(axis=1) < 255).any()    # and limb pixels below it


# --------------------------------------------------------------------- the record

def test_the_source_pin_is_complete_enough_to_refetch():
    for key in ("repo", "path", "url", "commit", "sha256", "bytes", "fetched", "license"):
        assert aapose.SOURCE.get(key), f"the pin is missing {key}"
    assert len(aapose.SOURCE["commit"]) == 40
    assert len(aapose.SOURCE["sha256"]) == 64
    assert json.dumps(aapose.SOURCE)        # it has to survive into a provenance record


# ------------- wave 22, F-6bdd660a: confidence is a MEASUREMENT and is bounded like one
#
# The convention that draws the pose-stick control frame reads confidence at four sites —
# `draw_body` twice, `draw_hand` twice — and every one was a bare `< threshold` with no
# finiteness bound anywhere in the module (`aapose` was one of nine `armature_core` modules
# that did not import `parts.require_finite`). A NaN confidence fails `<` in BOTH
# directions, so the keypoint was treated as fully confident and DRAWN.
#
# MEASURED on `e8263a3` on a 20x3 body at 256x256: baseline 2075 non-black pixels; the same
# body with keypoint 5's confidence set to NaN drew 2075 non-black pixels — byte-identical
# ink to confidence 1.0 — with no refusal, where a real detector's low confidence would have
# dropped the joint. The coordinate direction escaped the family instead: keypoint 5's x set
# to NaN raised a bare `ValueError: cannot convert float NaN to integer` (from `int(mY)` /
# `int(point[0])`) and +inf raised a bare `OverflowError`, NEITHER in the `ArmatureError`
# family, so the 21-tool halt contract recorded exit 1 "FAILED — an unhandled error" where a
# typed refusal at exit 2 belongs.
#
# Reachability: the keypoint record is read from JSON (`render_pose_sticks.py`, and Python's
# `json.load` accepts the literal `NaN`), so the moment a producer other than
# `project_pose_keypoints` supplies confidences — which the record's own note anticipates,
# "a real detector would report low confidence on an occluded joint" — an occluded joint
# whose confidence is not a number is drawn as certain into the control frame that steers a
# paid generation, and `gate_INK` cannot see it because the ink is there.


def _plain_body(size=256):
    """A 20x3 body inside a square canvas, every joint fully confident."""
    c = size / 2.0
    s = size / 12.0
    return [[c + (i % 5 - 2) * s, c + (i // 5 - 2) * s, 1.0] for i in range(20)]


def _ink(canvas):
    return int((canvas.reshape(-1, 3).max(axis=1) > 0).sum())


def test_the_baseline_ink_is_what_a_fully_confident_body_draws():
    """The control. Without it, "the NaN drew the same ink" is a number with no reading."""
    body = _plain_body()
    canvas = aapose.draw_frame(256, 256, body, draw_hands=False)
    assert _ink(canvas) > 0


def test_a_non_finite_confidence_is_refused_rather_than_drawn_as_certain():
    body = _plain_body()
    body[5][2] = float("nan")
    with pytest.raises(aapose.ConventionError) as exc:
        aapose.draw_frame(256, 256, body, draw_hands=False)
    ev = exc.value.evidence
    assert ev["clause"] == "confidence_not_a_number"
    assert ev["where"] == "draw_body"
    assert ev["indices"] == [5]


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_every_non_finite_confidence_spelling_takes_the_same_door(bad):
    """`nan` walks past `<` in both directions; `+inf` reads as certain; `-inf` reads as
    absent. Three different readings of one unreadable measurement, one clause."""
    body = _plain_body()
    body[11][2] = bad
    with pytest.raises(aapose.ConventionError, match=r"confidence"):
        aapose.draw_frame(256, 256, body, draw_hands=False)


@pytest.mark.parametrize("bad", [float("nan"), float("inf")])
def test_a_non_finite_coordinate_on_a_DRAWN_keypoint_leaves_in_the_family(bad):
    """The direction that escaped the family instead of walking past it: `int(nan)` is a
    bare `ValueError` and `int(inf)` a bare `OverflowError`, and the halt contract records
    either as a crash at exit 1."""
    from armature_core.errors import ArmatureError

    body = _plain_body()
    body[5][0] = bad
    with pytest.raises(aapose.ConventionError) as exc:
        aapose.draw_frame(256, 256, body, draw_hands=False)
    assert isinstance(exc.value, ArmatureError)
    assert exc.value.evidence["clause"] == "drawn_keypoint_coordinate_not_a_number"
    assert exc.value.evidence["indices"] == [5]


def test_a_non_finite_coordinate_on_a_keypoint_BELOW_the_threshold_is_not_drawn_and_not_refused():
    """Grade the clause only on what it can move: a keypoint the convention skips is not a
    pixel this frame carries, and refusing it would be a bound on a population the drawing
    never reads."""
    body = _plain_body()
    body[5][0] = float("nan")
    body[5][2] = 0.0
    canvas = aapose.draw_frame(256, 256, body, draw_hands=False)
    assert _ink(canvas) > 0


def test_a_non_finite_threshold_is_refused_rather_than_silently_drawing_nothing():
    """`c < nan` is False at every keypoint, so a NaN threshold draws EVERYTHING; `c < inf`
    is True at every keypoint, so it draws NOTHING. Neither is a decision."""
    with pytest.raises(aapose.ConventionError) as exc:
        aapose.draw_frame(256, 256, _plain_body(), threshold=float("nan"),
                          draw_hands=False)
    assert exc.value.evidence["clause"] == "threshold_not_a_number"


def test_the_hand_pass_carries_the_same_two_clauses():
    """The four reading sites are two per function; the sibling half is `draw_hand`'s."""
    body = _plain_body()
    hand = [[100.0 + i, 100.0 + i, 1.0] for i in range(aapose.HAND_KEYPOINT_COUNT)]
    aapose.draw_frame(256, 256, body, left_hand=hand, draw_hands=True)   # control

    bad_conf = [list(p) for p in hand]
    bad_conf[3][2] = float("nan")
    with pytest.raises(aapose.ConventionError) as exc:
        aapose.draw_frame(256, 256, body, left_hand=bad_conf, draw_hands=True)
    assert exc.value.evidence["clause"] == "confidence_not_a_number"
    assert exc.value.evidence["where"] == "draw_hand"

    bad_xy = [list(p) for p in hand]
    bad_xy[3][1] = float("inf")
    with pytest.raises(aapose.ConventionError) as exc:
        aapose.draw_frame(256, 256, body, left_hand=bad_xy, draw_hands=True)
    assert exc.value.evidence["clause"] == "drawn_keypoint_coordinate_not_a_number"


def test_dropping_the_head_still_works_because_a_zeroed_confidence_is_a_number():
    """`draw_head=False` sets five confidences to 0. A bound that refused it would have
    deleted the flag."""
    body = _plain_body()
    with_head = aapose.draw_frame(256, 256, body, draw_hands=False, draw_head=True)
    without = aapose.draw_frame(256, 256, body, draw_hands=False, draw_head=False)
    assert _ink(without) < _ink(with_head)
