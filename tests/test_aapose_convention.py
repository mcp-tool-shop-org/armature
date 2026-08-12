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


def test_limbseq_matches_the_source_element_for_element():
    assert [list(p) for p in aapose.LIMB_SEQ] == SOURCE_LIMB_SEQ


def test_limbseq_is_nineteen_pairs_over_twenty_keypoints():
    assert len(aapose.LIMB_SEQ) == 19
    flat = [v for pair in aapose.LIMB_SEQ for v in pair]
    assert min(flat) == 1, "the source's limbSeq is 1-indexed; it reads kp2ds_body[k - 1]"
    assert max(flat) == 20


def test_palette_matches_the_source_element_for_element():
    assert [list(c) for c in aapose.PALETTE] == SOURCE_COLORS
    assert len(aapose.PALETTE) == 20


def test_keypoint_names_and_count_are_twenty_not_eighteen():
    """G6 called this "the classic 18-point limbSeq". The source carries 20 with two toes,
    and rendering 18 against it omits both feet with nothing erroring."""
    assert list(aapose.KEYPOINT_NAMES) == SOURCE_KEYPOINT_NAMES
    assert aapose.KEYPOINT_COUNT == 20
    assert aapose.KEYPOINT_NAMES[18] == "LToe"
    assert aapose.KEYPOINT_NAMES[19] == "RToe"


def test_hand_edges_match_the_source():
    assert [list(e) for e in aapose.HAND_EDGES] == SOURCE_HAND_EDGES
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
    with pytest.raises(ArmatureError):
        aapose.stickwidth(480, 832, "v3")
    with pytest.raises(ArmatureError):
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

    # The v2 width expression, verbatim, inside draw_aapose_new.
    body = text[at:text.index("def draw_bbox(", at)]
    assert "stickwidth = max(int(min(H, W) / 200) - 1, 1)" in body
    # …and the hand pass's halving, inside draw_handpose_new.
    hand = text[text.index("def draw_handpose_new("):text.index("def draw_ellipse_by_2kp(")]
    assert "stickwidth = max(max(int(min(H, W) / 200) - 1, 1) // 2, 1)" in hand
    # …and that limbs are filled at 60% while joints are not.
    assert "[int(float(c) * 0.6) for c in color]" in body


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
    with pytest.raises(ArmatureError):
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
    with pytest.raises(ArmatureError):
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


#: Measured 2026-08-12 on this rig (numpy 2.4.6 / cv2 4.13.0, trellis2-env py3.13.13).
#: A cv2 or numpy change that alters the rasterisation moves these, and a human rules on
#: whether the move was intended. They are a regression pin, not a claim about correctness.
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
    assert hashlib.sha256(canvas.tobytes()).hexdigest() == GOLDEN[(width, height, hands)]


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
