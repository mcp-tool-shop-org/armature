"""The OpenPose-18 convention — topology and drawing, retrieved from ControlNet.

F20 (docs/research-grounding.md) is marked **verified by direct source retrieval**:
`limbSeq` was fetched from lllyasviel/ControlNet `annotator/openpose/util.py` and read
at ruling time. It is 19 pairs and it is **1-indexed**, which is a live trap for a
from-scratch renderer. Those values are pinned below and G5 compares against them
element for element.

F-b08c0918 (wave 34): the 18-colour palette and the 0-based keypoint order were also
retrieved from the same `draw_bodypose()` in that file (fetched 2026-09-06 from
lllyasviel/ControlNet `main`). Drawing is therefore bounded the same way AAPose Gate
CONV pins its banked record — topology alone is not enough for a ControlNet-18 route.

Nothing in this module is an ML estimator: a skeleton drawn from known bone transforms
is arithmetic. The banned tier (OpenPose is CMU non-commercial — see
docs/license-map.md) is sidestepped by construction, not by substitution. AAPose-20 is
a different convention (`aapose`) and is not a substitute.
"""

import math

import numpy as np

from .errors import ArmatureError

#: F20, retrieved 2026-08-10. 19 pairs, 1-indexed.
LIMB_SEQ = [
    [2, 3], [2, 6], [3, 4], [4, 5], [6, 7], [7, 8], [2, 9], [9, 10],
    [10, 11], [2, 12], [12, 13], [13, 14], [2, 1], [1, 15], [15, 17],
    [1, 16], [16, 18], [3, 17], [6, 18],
]

#: F20: "18 keypoints".
KEYPOINT_COUNT = 18

#: ControlNet `draw_bodypose` `colors`, retrieved 2026-09-06 from
#: lllyasviel/ControlNet `annotator/openpose/util.py` on `main`. 18 BGR-order triples
#: used for both joint dots and limb polygons (limb i uses `colors[i % 18]` so all 19
#: pairs — including the two ear–shoulder links ControlNet's `range(17)` loop skipped —
#: receive a retrieved colour rather than an invented one).
PALETTE = [
    [255, 0, 0], [255, 85, 0], [255, 170, 0], [255, 255, 0], [170, 255, 0],
    [85, 255, 0], [0, 255, 0], [0, 255, 85], [0, 255, 170], [0, 255, 255],
    [0, 170, 255], [0, 85, 255], [0, 0, 255], [85, 0, 255], [170, 0, 255],
    [255, 0, 255], [255, 0, 170], [255, 0, 85],
]

#: 0-based COCO-18 order matching ControlNet's candidate index / OpenPose BODY_25
#: subset[0:18] layout. Names are the conventional short labels; order is the contract.
KEYPOINT_NAMES = (
    "nose", "neck",
    "right_shoulder", "right_elbow", "right_wrist",
    "left_shoulder", "left_elbow", "left_wrist",
    "right_hip", "right_knee", "right_ankle",
    "left_hip", "left_knee", "left_ankle",
    "right_eye", "left_eye", "right_ear", "left_ear",
)

SOURCE = {
    "path": "lllyasviel/ControlNet annotator/openpose/util.py",
    "function": "draw_bodypose",
    "retrieved": "2026-09-06",
    "limb_seq_ruling": "F20 — fetched and read at ruling time 2026-08-10",
    "note": ("palette + keypoint order banked for F-b08c0918; limbSeq already pinned "
             "by F20"),
}

#: ControlNet `draw_handpose` `edges`, retrieved 2026-09-07 from the same util.py on
#: `main` (F-3cc4b5d6). 20 pairs over 21 keypoints, **0-indexed**. Edge colours are HSV
#: (`ie / len(edges)`); joint dots use HAND_JOINT_COLOR.
HAND_EDGES = (
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (0, 9), (9, 10), (10, 11), (11, 12),
    (0, 13), (13, 14), (14, 15), (15, 16),
    (0, 17), (17, 18), (18, 19), (19, 20),
)
HAND_KEYPOINT_COUNT = 21
HAND_JOINT_COLOR = (0, 0, 255)  # ControlNet draw_handpose circle colour (BGR-ish RGB)
HAND_SOURCE = {
    "path": "lllyasviel/ControlNet annotator/openpose/util.py",
    "function": "draw_handpose",
    "retrieved": "2026-09-07",
    "note": "edges + joint colour banked for F-3cc4b5d6; HSV limb colours are procedural",
}

#: Rig site name aliases for packing into COCO-18 / OpenPose KEYPOINT_NAMES order
#: (F-588e3daf). AAPose uses `neck_base` and foot toes; OpenPose-18 wants `neck` and
#: drops toes. Each entry is tried in order until a site is present.
BODY_SITE_ALIASES = (
    ("nose", ("nose",)),
    ("neck", ("neck", "neck_base")),
    ("right_shoulder", ("shoulder_R", "right_shoulder")),
    ("right_elbow", ("elbow_R", "right_elbow")),
    ("right_wrist", ("wrist_R", "right_wrist")),
    ("left_shoulder", ("shoulder_L", "left_shoulder")),
    ("left_elbow", ("elbow_L", "left_elbow")),
    ("left_wrist", ("wrist_L", "left_wrist")),
    ("right_hip", ("hip_R", "right_hip")),
    ("right_knee", ("knee_R", "right_knee")),
    ("right_ankle", ("ankle_R", "right_ankle")),
    ("left_hip", ("hip_L", "left_hip")),
    ("left_knee", ("knee_L", "left_knee")),
    ("left_ankle", ("ankle_L", "left_ankle")),
    ("right_eye", ("eye_R", "right_eye")),
    ("left_eye", ("eye_L", "left_eye")),
    ("right_ear", ("ear_R", "right_ear")),
    ("left_ear", ("ear_L", "left_ear")),
)

DEFAULT_THRESHOLD = 0.1
DEFAULT_STICKWIDTH = 4
DEFAULT_HAND_STICKWIDTH = 2  # ControlNet draw_handpose line thickness
LIMB_BLEND = (0.4, 0.6)  # ControlNet: canvas*0.4 + limb*0.6


class ConventionError(ArmatureError):
    """Gate CONV · OpenPose-18 drawing convention does not match the banked record."""


def require_drawing_convention():
    """Raise unless the parts needed to *draw* a skeleton have been retrieved."""
    missing = [n for n, v in (("PALETTE", PALETTE), ("KEYPOINT_NAMES", KEYPOINT_NAMES))
               if v is None]
    if missing:
        raise ArmatureError(
            "the OpenPose-18 drawing convention is not fully retrieved: "
            f"{', '.join(missing)} unresolved. F20 pins limbSeq and the keypoint "
            "count but does not record the palette or the keypoint order, and this "
            "tool does not write conventions from memory. Retrieve them into "
            "docs/research-grounding.md before emitting a pose channel.",
            {"gate": None, "andon": "ArmatureError",
             "clause": "drawing_convention_not_retrieved"})
    if len(PALETTE) != KEYPOINT_COUNT:
        raise ConventionError(
            f"PALETTE holds {len(PALETTE)} entries, KEYPOINT_COUNT is {KEYPOINT_COUNT}",
            {"gate": "CONV", "andon": "ConventionError",
             "clause": "palette_length_mismatch",
             "palette_len": len(PALETTE), "keypoint_count": KEYPOINT_COUNT})
    if len(KEYPOINT_NAMES) != KEYPOINT_COUNT:
        raise ConventionError(
            f"KEYPOINT_NAMES holds {len(KEYPOINT_NAMES)} entries, KEYPOINT_COUNT is "
            f"{KEYPOINT_COUNT}",
            {"gate": "CONV", "andon": "ConventionError",
             "clause": "keypoint_names_length_mismatch",
             "names_len": len(KEYPOINT_NAMES), "keypoint_count": KEYPOINT_COUNT})
    return True


def check_convention(keypoint_count=None, limb_seq=None, palette=None):
    """Gate CONV — banked OpenPose-18 tables agree with the caller (and themselves)."""
    require_drawing_convention()
    problems = []
    if keypoint_count is not None and int(keypoint_count) != KEYPOINT_COUNT:
        problems.append(
            f"caller keypoint_count {keypoint_count} != banked {KEYPOINT_COUNT}")
    if limb_seq is not None and list(limb_seq) != list(LIMB_SEQ):
        problems.append("caller limb_seq differs from banked LIMB_SEQ")
    if palette is not None and [list(c) for c in palette] != [list(c) for c in PALETTE]:
        problems.append("caller palette differs from banked PALETTE")
    if problems:
        raise ConventionError(
            "the emitted OpenPose-18 skeleton does not match the banked ControlNet "
            f"record ({SOURCE['path']}::{SOURCE['function']}, retrieved "
            f"{SOURCE['retrieved']}): " + "; ".join(problems),
            {"gate": "CONV", "andon": "ConventionError",
             "clause": "convention_nonconformance", "problems": problems,
             "source": dict(SOURCE)})
    return {
        "verdict": "PASS",
        "compared_against": "armature_core.openpose banked ControlNet draw_bodypose",
        "keypoint_count": KEYPOINT_COUNT,
        "limb_pairs": len(LIMB_SEQ),
        "palette_entries": len(PALETTE),
        "source": dict(SOURCE),
        "detail": (f"{KEYPOINT_COUNT} keypoints / {len(LIMB_SEQ)} pairs / "
                   f"{len(PALETTE)} palette entries equal to banked ControlNet record"),
    }


def blank_canvas(height, width):
    return np.zeros((int(height), int(width), 3), dtype=np.uint8)


def body_from_sites(sites, conf=1.0):
    """Pack projected/world sites into an OpenPose-18 `(18, 3)` body array (F-588e3daf).

    Mirrors `aapose.body_from_sites` shape guard with an explicit site-name adapter:
    `neck_base` → neck slot, L/R rig names → right_* / left_* COCO-18 order, toes dropped.
    AAPose-20 stays in `aapose`; this packer is the OpenPose-18 half.
    """
    require_drawing_convention()
    if not isinstance(sites, dict):
        raise ArmatureError(
            f"body_from_sites sites must be a dict of name -> xy, got "
            f"{type(sites).__name__}",
            {"gate": None, "andon": "ArmatureError",
             "clause": "body_sites_not_a_mapping"})
    c = float(conf)
    if not (c == c) or c < 0.0:
        raise ArmatureError(
            f"body_from_sites conf={conf!r} is not a non-negative finite confidence",
            {"gate": None, "andon": "ArmatureError",
             "clause": "body_confidence_unreadable", "conf": repr(conf)})
    have = set(sites)
    missing = []
    rows = []
    for name, aliases in BODY_SITE_ALIASES:
        key = next((a for a in aliases if a in sites), None)
        if key is None:
            missing.append(name)
            continue
        p = np.asarray(sites[key], dtype=np.float64).reshape(-1)
        if p.size < 2:
            raise ArmatureError(
                f"site {key!r} (OpenPose {name!r}) needs at least 2 coordinates, "
                f"got shape {p.shape}",
                {"gate": None, "andon": "ArmatureError",
                 "clause": "body_site_too_short", "site": key, "openpose": name,
                 "shape": list(p.shape)})
        rows.append((float(p[0]), float(p[1]), c))
    if missing:
        raise ArmatureError(
            f"OpenPose-18 body_from_sites missing site(s) for {missing}; available: "
            f"{sorted(have)}",
            {"gate": None, "andon": "ArmatureError",
             "clause": "required_landmark_missing",
             "missing": missing, "available": sorted(have)})
    out = np.asarray(rows, dtype=np.float64)
    if out.shape != (KEYPOINT_COUNT, 3):
        raise ArmatureError(
            f"body_from_sites built shape {out.shape}, convention wants "
            f"({KEYPOINT_COUNT}, 3)",
            {"gate": None, "andon": "ArmatureError",
             "clause": "body_from_sites_wrong_shape",
             "shape": list(out.shape), "recorded": KEYPOINT_COUNT})
    return out


def draw_body(canvas, kp2ds, threshold=DEFAULT_THRESHOLD, stickwidth=DEFAULT_STICKWIDTH):
    """ControlNet `draw_bodypose` body pass over an (18, 3) keypoint array.

    `kp2ds` is (18, 3): x pixels, y pixels, confidence. Limb indices in `LIMB_SEQ` are
    1-indexed into that array. Drawn in place; canvas returned for chaining.
    """
    import cv2

    require_drawing_convention()
    kp = np.array(kp2ds, dtype=np.float64, copy=True)
    if kp.shape != (KEYPOINT_COUNT, 3):
        raise ArmatureError(
            f"body keypoints must be ({KEYPOINT_COUNT}, 3) — x, y, confidence — got "
            f"{kp.shape}",
            {"gate": None, "andon": "ArmatureError", "clause": "body_keypoints_wrong_shape",
             "shape": list(kp.shape), "expected": [KEYPOINT_COUNT, 3]})

    sw = int(stickwidth)
    for i, (k1, k2) in enumerate(LIMB_SEQ):
        a, b = kp[k1 - 1], kp[k2 - 1]
        if a[-1] < threshold or b[-1] < threshold:
            continue
        Y = np.array([a[0], b[0]])
        X = np.array([a[1], b[1]])
        mX, mY = float(np.mean(X)), float(np.mean(Y))
        length = float(((X[0] - X[1]) ** 2 + (Y[0] - Y[1]) ** 2) ** 0.5)
        angle = math.degrees(math.atan2(X[0] - X[1], Y[0] - Y[1]))
        polygon = cv2.ellipse2Poly((int(mY), int(mX)), (max(int(length / 2), 1), sw),
                                   int(angle), 0, 360, 1)
        color = [int(c) for c in PALETTE[i % len(PALETTE)]]
        cur = canvas.copy()
        cv2.fillConvexPoly(cur, polygon, color)
        canvas[:] = cv2.addWeighted(canvas, LIMB_BLEND[0], cur, LIMB_BLEND[1], 0)

    for i, point in enumerate(kp):
        if point[-1] < threshold:
            continue
        cv2.circle(canvas, (int(point[0]), int(point[1])), sw,
                   [int(c) for c in PALETTE[i]], thickness=-1)
    return canvas


def draw_hand(canvas, keypoints, threshold=DEFAULT_THRESHOLD,
              stickwidth=DEFAULT_HAND_STICKWIDTH, receipt=None):
    """ControlNet `draw_handpose` over a (21, 3) hand array (F-3cc4b5d6).

    Edges and joint colour are the banked HAND_EDGES / HAND_JOINT_COLOR record; limb
    colours follow ControlNet's HSV `ie / len(edges)` recipe. Drawn in place.
    """
    import cv2
    import matplotlib.colors as mcolors

    require_drawing_convention()
    kp = np.asarray(keypoints, dtype=np.float64)
    if kp.shape != (HAND_KEYPOINT_COUNT, 3):
        raise ArmatureError(
            f"hand keypoints must be ({HAND_KEYPOINT_COUNT}, 3) — x, y, confidence — got "
            f"{kp.shape}",
            {"gate": None, "andon": "ArmatureError", "clause": "hand_keypoints_wrong_shape",
             "shape": list(kp.shape), "expected": [HAND_KEYPOINT_COUNT, 3]})
    sw = int(stickwidth)
    drawn_limbs = 0
    drawn_joints = 0
    for ie, (e1, e2) in enumerate(HAND_EDGES):
        a, b = kp[e1], kp[e2]
        if a[2] < threshold or b[2] < threshold:
            continue
        rgb = mcolors.hsv_to_rgb([ie / float(len(HAND_EDGES)), 1.0, 1.0]) * 255
        cv2.line(canvas, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])),
                 rgb, thickness=sw)
        drawn_limbs += 1
    for point in kp:
        if point[2] < threshold:
            continue
        cv2.circle(canvas, (int(point[0]), int(point[1])), 4,
                   list(HAND_JOINT_COLOR), thickness=-1)
        drawn_joints += 1
    if receipt is not None:
        receipt.update({
            "hand_limbs_drawn": drawn_limbs,
            "hand_joints_drawn": drawn_joints,
            "hand_stickwidth_px": sw,
            "hand_source": dict(HAND_SOURCE),
        })
    return canvas


def draw_frame(height, width, body, left_hand=None, right_hand=None,
               threshold=DEFAULT_THRESHOLD, stickwidth=DEFAULT_STICKWIDTH,
               hands=False, receipt=None):
    """One OpenPose-18 pose-stick frame: black canvas then body pass.

    Body-only is the default (`hands=False`). Pass `hands=True` (and optional left/right
    hand arrays) to also run ControlNet `draw_handpose` (F-3cc4b5d6). Refuses with clause
    `drawn_ink_empty` when the finished plate has zero non-black pixels — same andon
    posture as `aapose.draw_frame`.
    """
    require_drawing_convention()
    canvas = blank_canvas(height, width)
    draw_body(canvas, body, threshold=threshold, stickwidth=stickwidth)
    hand_receipts = []
    if hands:
        for hand in (left_hand, right_hand):
            if hand is not None:
                hr = {}
                draw_hand(canvas, hand, threshold=threshold, receipt=hr)
                hand_receipts.append(hr)
    n_ink = int(np.count_nonzero(np.any(canvas != 0, axis=2)))
    arr = np.asarray(body, dtype=np.float64)
    n_confident = int(np.sum(arr[:, 2] >= float(threshold))) if arr.ndim == 2 else 0
    if receipt is not None:
        receipt.update({
            "n_ink": n_ink,
            "n_confident": n_confident,
            "stickwidth_px": int(stickwidth),
            "convention": "openpose-18",
            "hands": bool(hands),
            "hand_receipts": hand_receipts,
            "source": dict(SOURCE),
        })
    if n_ink == 0:
        raise ConventionError(
            f"draw_frame painted 0 non-black pixels on a {int(height)}x{int(width)} "
            f"canvas; {n_confident} keypoint(s) carried confidence >= {float(threshold)} "
            f"but none landed as ink",
            {"gate": "CONV", "andon": "ConventionError", "clause": "drawn_ink_empty",
             "n_ink": 0, "n_confident": n_confident, "threshold": float(threshold),
             "height": int(height), "width": int(width),
             "stickwidth_px": int(stickwidth)})
    return canvas
