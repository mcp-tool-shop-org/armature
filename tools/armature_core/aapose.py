"""The Wan-Animate **AAPose-20** driving convention, transcribed from the retrieved source.

No bpy. Everything here is arithmetic on numbers plus cv2 drawing calls, so it is testable
without Blender and without a GPU.

--------------------------------------------------------------------------------
The pin

Source file, fetched and banked by this experiment:

    repo    Wan-Video/Wan2.2                       (Apache-2.0 — docs/license-map.md)
    path    wan/modules/animate/preprocess/human_visualization.py
    commit  29d4a35d32273d5309a3a95250bd4e118d8789b2   ("Add Wan-Animate Codes and
            examples (#146)", 2025-09-19) — the last commit to touch this path
    sha256  962813c71b2f2e09f7cd745b35b31a0d278b122b5f2f429018d0576c795eda33
    bytes   44228
    fetched 2026-08-12, banked at outputs/E08/convention/human_visualization.py

**Why the file is banked and not merely cited.** E08's spec marked this premise MEASURED on
the strength of "Apache source fetched + banked with hash (E09 route2)". It was not banked:
`outputs/E09/route2/` holds the Wan **T2V** configs and README, and no copy of this file
existed anywhere in the repo or its worktrees. The convention detail in G6 was therefore the
only record, and G6 is a *summary* — it compresses exactly the places where this module has
to be exact. Re-fetched here, banked, hashed, and transcribed from the file itself.

**What the summary got wrong, measured against the source.** G6 calls this "the classic
18-point `limbSeq`". The function this pipeline matches, `draw_aapose_new` (reached via
`draw_aapose_by_meta_new`), carries **20 keypoints and 19 limb pairs**: the OpenPose-18 body
plus `LToe` and `RToe`, with two extra pairs `[14, 19]` and `[11, 20]` joining each ankle to
its toe. Rendering 18 points against this convention would silently omit both feet.

--------------------------------------------------------------------------------
The trap this module exists to keep visible

`armature_core.openpose` holds a DIFFERENT convention — F20, from lllyasviel/ControlNet.
Its first 17 pairs are identical to this one and its last two are **not**: ControlNet closes
the head with `[3, 17], [6, 18]` (shoulder-to-ear), Wan closes the feet with
`[14, 19], [11, 20]`. Two conventions that agree on 17 of 19 pairs are exactly the pair a
from-scratch renderer conflates, and the license map already records the general warning
("the DWPose drawing codepath ... is a **different implementation** — do not conflate them").
`tests/test_aapose_convention.py` pins the difference so a future edit that merges them fails
loudly. Neither module is deleted; they are different objects.

--------------------------------------------------------------------------------
Channel order — a determination from the source, with its evidence

The palette values are used as-is in `cv2` calls, and cv2 itself is channel-agnostic: the
order is whatever the *caller's* canvas holds. The file settles it in its own `__main__`,
which builds frames through this same palette and writes them with

    cv2.imwrite("traj.png", res[0][..., ::-1])

`cv2.imwrite` expects BGR, and the array is reversed on the way in — so the array these
functions draw into is **RGB**. Under that reading `[255, 0, 0]` (limb 0) is red and the hand
joint colour `(0, 0, 255)` is blue.

This is the highest-risk residual in the module and it is named rather than buried: a
red/blue swap fails silently (G10 — a weak or off-convention render makes the model obey
weakly, and no gate fires). The frames are written RGB and the provenance records it, so a
later run can flip one flag rather than re-derive this.

--------------------------------------------------------------------------------
The rig map

The 20 AAPose keypoints are read off the registered rig (`armature_core.sitelist`), not
detected. `L`/`R` in the AAPose names are the SUBJECT's own left and right — traced through
`split_pose2d_kps_to_aa`, whose index tables resolve to COCO-wholebody's subject-frame
left/right (e.g. AAPose 2 `RShoulder` <- COCO 6 `right_shoulder`). The rig's `.L`/`.R`
suffixes carry the same meaning by construction: `landmarks.facing` measures which way the
figure faces from its own feet and derives `left_x_sign` from that. So the mapping is
name-to-name and both sides were measured, not assumed.

Toes come from the ankle bones' TAILS (`sitelist` places `ankle.L` head->`ankle_L`,
tail->`toe_L`), which is the only place toe positions exist on this 22-bone rig.
"""

import math

import numpy as np

from .errors import ArmatureError

# --------------------------------------------------------------------------- the pin

SOURCE = {
    "repo": "Wan-Video/Wan2.2",
    "path": "wan/modules/animate/preprocess/human_visualization.py",
    "url": (
        "https://raw.githubusercontent.com/Wan-Video/Wan2.2/main/"
        "wan/modules/animate/preprocess/human_visualization.py"
    ),
    "commit": "29d4a35d32273d5309a3a95250bd4e118d8789b2",
    "commit_date": "2025-09-19T03:07:53Z",
    "sha256": "962813c71b2f2e09f7cd745b35b31a0d278b122b5f2f429018d0576c795eda33",
    "bytes": 44228,
    "fetched": "2026-08-12",
    "license": "Apache-2.0 (docs/license-map.md, Services and tools)",
    "function_matched": "draw_aapose_new via draw_aapose_by_meta_new",
}

# ------------------------------------------------------------------- the convention

#: `new_kep_list` verbatim, in index order. TWENTY names, not eighteen.
KEYPOINT_NAMES = (
    "Nose", "Neck",
    "RShoulder", "RElbow", "RWrist",
    "LShoulder", "LElbow", "LWrist",
    "RHip", "RKnee", "RAnkle",
    "LHip", "LKnee", "LAnkle",
    "REye", "LEye", "REar", "LEar",
    "LToe", "RToe",
)

KEYPOINT_COUNT = len(KEYPOINT_NAMES)

#: `draw_aapose_new`'s `limbSeq` verbatim — 19 pairs, **1-indexed**, the last two being the
#: feet. The 1-indexing is the live trap: `draw_aapose_new` reads `kp2ds_body[k - 1]`.
#: The inline comments are the SOURCE's own; note they label [3,4],[4,5] "left arm" while
#: those indices are RShoulder->RElbow->RWrist. The source's comments disagree with its own
#: `new_kep_list`; the NAMES govern and the comments are reproduced only for traceability.
LIMB_SEQ = (
    (2, 3), (2, 6),               # shoulders
    (3, 4), (4, 5),               # source comment: "left arm"  (indices are the R side)
    (6, 7), (7, 8),               # source comment: "right arm" (indices are the L side)
    (2, 9), (9, 10), (10, 11),    # right leg
    (2, 12), (12, 13), (13, 14),  # left leg
    (2, 1),                       # neck -> nose
    (1, 15), (15, 17), (1, 16), (16, 18),   # face (nose, eyes, ears)
    (14, 19), (11, 20),           # foot
)

#: `colors` verbatim — 20 entries, zipped against both the 19 limb pairs and the 20
#: keypoints. The 20th is never reached by the limb loop; it colours the 20th joint circle.
PALETTE = (
    (255, 0, 0), (255, 85, 0), (255, 170, 0), (255, 255, 0),
    (170, 255, 0), (85, 255, 0), (0, 255, 0), (0, 255, 85),
    (0, 255, 170), (0, 255, 255), (0, 170, 255), (0, 85, 255),
    (0, 0, 255), (85, 0, 255), (170, 0, 255), (255, 0, 255),
    (255, 0, 170), (255, 0, 85),
    (200, 200, 0), (100, 100, 0),          # foot
)

#: `draw_handpose_new`'s `edges` verbatim — 20 pairs over 21 keypoints, **0-indexed**.
HAND_EDGES = (
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (0, 9), (9, 10), (10, 11), (11, 12),
    (0, 13), (13, 14), (14, 15), (15, 16),
    (0, 17), (17, 18), (18, 19), (19, 20),
)

HAND_KEYPOINT_COUNT = 21

#: The hand joint dot colour, verbatim from `draw_handpose_new`. See the channel-order note.
HAND_JOINT_COLOR = (0, 0, 255)

#: Limbs are filled at 60% of their palette colour; joint circles at full. Verbatim:
#: `cv2.fillConvexPoly(img, polygon, [int(float(c) * 0.6) for c in color])`.
LIMB_BRIGHTNESS = 0.6

#: `draw_aapose_by_meta_new`'s default. Points below it are skipped entirely.
DEFAULT_THRESHOLD = 0.5

#: `draw_handpose_new`'s eps guard on hand coordinates.
HAND_EPS = 0.01


def stickwidth(height, width, stickwidth_type="v2"):
    """`draw_aapose_new`'s width, verbatim. v2 is `draw_aapose_by_meta_new`'s default.

    The source takes an unknown type to a bare `raise`; this raises something legible for
    the same reason `gates.resolve_generator` does — an unrecognised profile is the case
    where nothing is checked at all.
    """
    m = min(int(height), int(width))
    if stickwidth_type == "v1":
        return max(int(m / 200), 1)
    if stickwidth_type == "v2":
        return max(int(m / 200) - 1, 1)
    raise ArmatureError(
        f"unknown stickwidth_type {stickwidth_type!r}; the source defines only 'v1' and "
        f"'v2' and takes the else branch to a bare raise"
    )


def hand_stickwidth(height, width, stickwidth_type="v2"):
    """`draw_handpose_new`'s width, verbatim — HALF the body width in v2, floored at 1."""
    m = min(int(height), int(width))
    if stickwidth_type == "v1":
        return max(int(m / 200), 1)
    if stickwidth_type == "v2":
        return max(max(int(m / 200) - 1, 1) // 2, 1)
    raise ArmatureError(f"unknown stickwidth_type {stickwidth_type!r}")


# --------------------------------------------------------------------- the rig map

#: AAPose index (0-based, matching KEYPOINT_NAMES) -> (bone name, which end).
#: `head` is the bone's pivot; `tail` is its far end. Every one of the 20 resolves; nothing
#: here is invented or interpolated.
RIG_SITES = (
    ("nose", "head"),          # 0  Nose
    ("neck", "head"),          # 1  Neck      — bone `neck` head sits on landmark neck_base
    ("shoulder.R", "head"),    # 2  RShoulder
    ("elbow.R", "head"),       # 3  RElbow
    ("wrist.R", "head"),       # 4  RWrist
    ("shoulder.L", "head"),    # 5  LShoulder
    ("elbow.L", "head"),       # 6  LElbow
    ("wrist.L", "head"),       # 7  LWrist
    ("hip.R", "head"),         # 8  RHip
    ("knee.R", "head"),        # 9  RKnee
    ("ankle.R", "head"),       # 10 RAnkle
    ("hip.L", "head"),         # 11 LHip
    ("knee.L", "head"),        # 12 LKnee
    ("ankle.L", "head"),       # 13 LAnkle
    ("eye.R", "head"),         # 14 REye
    ("eye.L", "head"),         # 15 LEye
    ("ear.R", "head"),         # 16 REar
    ("ear.L", "head"),         # 17 LEar
    ("ankle.L", "tail"),       # 18 LToe     — sitelist: ankle.L tail is landmark toe_L
    ("ankle.R", "tail"),       # 19 RToe     — sitelist: ankle.R tail is landmark toe_R
)

#: Which bone supplies each hand's frame. The mannequin has mitten hands with no fingers, so
#: the 21 hand keypoints are SYNTHESISED in this bone's own space — see `mitten_hand`.
HAND_BONES = {"left": "wrist.L", "right": "wrist.R"}


def require_rig_map(all_names):
    """Raise unless every site this convention needs is a registered bone. ANDON.

    Called before any keypoint is sampled. **The andon is on the direction the invariant
    does not bound:** a missing bone would otherwise surface as a keypoint silently left at
    the origin, which draws a limb running to the corner of the frame and errors nowhere.
    """
    have = set(all_names)
    missing = sorted({b for b, _ in RIG_SITES if b not in have}
                     | {b for b in HAND_BONES.values() if b not in have})
    if missing:
        raise ArmatureError(
            f"the AAPose-20 rig map names bone(s) the rig does not carry: {missing}. "
            f"A keypoint with no bone behind it would be written as a zero and drawn as a "
            f"limb running off the frame, with nothing erroring. Rig bones present: "
            f"{sorted(have)}"
        )
    return True


def check_convention(keypoint_count, limb_seq, palette):
    """Conformance against the transcribed source. Raises `ArmatureError`.

    Compared element for element, including the 1-indexing and including the last two pairs,
    which is where a ControlNet/DWPose convention would differ (see the module docstring).
    """
    problems = []
    if keypoint_count != KEYPOINT_COUNT:
        problems.append(f"keypoint count {keypoint_count} != {KEYPOINT_COUNT}")

    ours = [tuple(p) for p in limb_seq]
    if len(ours) != len(LIMB_SEQ):
        problems.append(f"limb pair count {len(ours)} != {len(LIMB_SEQ)}")
    else:
        for i, (a, b) in enumerate(zip(ours, LIMB_SEQ)):
            if a != b:
                problems.append(f"limb pair {i}: {a} != source {b}")

    flat = [v for pair in ours for v in pair]
    if flat and min(flat) == 0:
        problems.append("limb pairs are 0-indexed; the source's limbSeq is 1-indexed")

    pal = [tuple(c) for c in palette]
    if len(pal) != len(PALETTE):
        problems.append(f"palette length {len(pal)} != {len(PALETTE)}")
    else:
        for i, (a, b) in enumerate(zip(pal, PALETTE)):
            if a != b:
                problems.append(f"palette entry {i}: {a} != source {b}")

    if problems:
        raise ArmatureError(
            "the emitted skeleton does not match the transcribed Wan AAPose-20 convention "
            f"({SOURCE['path']} @ {SOURCE['commit'][:12]}): " + "; ".join(problems)
        )
    return True


# ------------------------------------------------------------------------- the hand

def mitten_hand(wrist, palm_dir, palm_side, hand_length):
    """21 AAPose hand keypoints for a hand that has no fingers. A CONSTRUCTION, not a
    measurement — and the report says so.

    The subject is a clay artist's mannequin: each hand is one smooth mitten, so there is no
    knuckle, no fingertip and nothing to measure. The convention nevertheless wants 21
    points, and G6 records that Wan draws hands as their own pass. What is built here is a
    rigid five-finger fan laid out in the wrist bone's own frame: it rotates with the wrist
    (so it is not static in image space) and never articulates (so it is static in the
    hand's own space).

    Every offset is a fraction of THIS hand's own measured length — `hand_length` is the
    wrist->hand_end distance off the rig — so no length in metres governs it, per the
    global-constant law.

    Layout, matching the 21-point topology `HAND_EDGES` indexes:
      0            wrist root
      1-4    thumb, splayed to the side at a shallower angle
      5-8    index      9-12  middle     13-16  ring      17-20  pinky
    """
    w = np.asarray(wrist, dtype=np.float64)
    d = np.asarray(palm_dir, dtype=np.float64)
    s = np.asarray(palm_side, dtype=np.float64)
    L = float(hand_length)
    if L <= 0:
        raise ArmatureError("a hand needs a positive length to lay finger points along")

    pts = [w]
    # Thumb: off to the side of the palm, shorter, at a shallow angle.
    for k, f in enumerate((0.16, 0.34, 0.50, 0.62)):
        pts.append(w + d * (L * f * 0.85) + s * (L * (0.22 + 0.10 * k)))
    # Four fingers, evenly spread across the palm width, knuckle at 0.45 and tip near 0.98.
    for lane, spread in enumerate((0.10, -0.02, -0.14, -0.26)):
        base = 0.45
        tip = 0.98 - 0.06 * lane            # a little shorter toward the pinky
        for f in (base, base + (tip - base) * 0.45, base + (tip - base) * 0.78, tip):
            pts.append(w + d * (L * f) + s * (L * spread))
    out = np.asarray(pts, dtype=np.float64)
    if len(out) != HAND_KEYPOINT_COUNT:
        raise ArmatureError(
            f"mitten hand built {len(out)} points, the convention wants "
            f"{HAND_KEYPOINT_COUNT}"
        )
    return out


# ---------------------------------------------------------------------- the drawing

def blank_canvas(height, width):
    """The zeroed-black canvas the convention draws onto. uint8, 3 channels."""
    return np.zeros((int(height), int(width), 3), dtype=np.uint8)


def draw_body(canvas, kp2ds, threshold=DEFAULT_THRESHOLD, stickwidth_type="v2",
              draw_head=True):
    """`draw_aapose_new`'s body pass, transcribed.

    `kp2ds` is (20, 3): x pixels, y pixels, confidence. Drawn in place; the canvas is
    returned for chaining. Deliberately NOT normalising `kp2ds` at the end the way the
    source does — the source mutates its input to build a JSON sidecar and we do not.
    """
    import cv2

    kp = np.array(kp2ds, dtype=np.float64, copy=True)
    if kp.shape != (KEYPOINT_COUNT, 3):
        raise ArmatureError(
            f"body keypoints must be ({KEYPOINT_COUNT}, 3) — x, y, confidence — got "
            f"{kp.shape}"
        )
    if not draw_head:
        kp[[0, 14, 15, 16, 17], 2] = 0

    H, W = canvas.shape[:2]
    sw = stickwidth(H, W, stickwidth_type)

    for (k1, k2), color in zip(LIMB_SEQ, PALETTE):
        a, b = kp[k1 - 1], kp[k2 - 1]          # 1-indexed, as the source reads them
        if a[-1] < threshold or b[-1] < threshold:
            continue
        Y = np.array([a[0], b[0]])
        X = np.array([a[1], b[1]])
        mX, mY = float(np.mean(X)), float(np.mean(Y))
        length = float(((X[0] - X[1]) ** 2 + (Y[0] - Y[1]) ** 2) ** 0.5)
        angle = math.degrees(math.atan2(X[0] - X[1], Y[0] - Y[1]))
        polygon = cv2.ellipse2Poly((int(mY), int(mX)), (int(length / 2), sw),
                                   int(angle), 0, 360, 1)
        cv2.fillConvexPoly(canvas, polygon,
                           [int(float(c) * LIMB_BRIGHTNESS) for c in color])

    for point, color in zip(kp, PALETTE):
        if point[-1] < threshold:
            continue
        cv2.circle(canvas, (int(point[0]), int(point[1])), sw,
                   [int(c) for c in color], thickness=-1)
    return canvas


def draw_hand(canvas, keypoints, threshold=DEFAULT_THRESHOLD, stickwidth_type="v2"):
    """`draw_handpose_new`, transcribed. `keypoints` is (21, 3): x, y, confidence."""
    import cv2
    import matplotlib.colors as mcolors

    kp = np.asarray(keypoints, dtype=np.float64)
    if kp.shape != (HAND_KEYPOINT_COUNT, 3):
        raise ArmatureError(
            f"hand keypoints must be ({HAND_KEYPOINT_COUNT}, 3), got {kp.shape}"
        )
    H, W = canvas.shape[:2]
    sw = hand_stickwidth(H, W, stickwidth_type)

    for ie, (e1, e2) in enumerate(HAND_EDGES):
        k1, k2 = kp[e1], kp[e2]
        if k1[2] < threshold or k2[2] < threshold:
            continue
        x1, y1, x2, y2 = int(k1[0]), int(k1[1]), int(k2[0]), int(k2[1])
        if x1 > HAND_EPS and y1 > HAND_EPS and x2 > HAND_EPS and y2 > HAND_EPS:
            rgb = mcolors.hsv_to_rgb([ie / float(len(HAND_EDGES)), 1.0, 1.0]) * 255
            cv2.line(canvas, (x1, y1), (x2, y2), rgb, thickness=sw)

    for point in kp:
        if point[2] < threshold:
            continue
        x, y = int(point[0]), int(point[1])
        if x > HAND_EPS and y > HAND_EPS:
            cv2.circle(canvas, (x, y), sw, HAND_JOINT_COLOR, thickness=-1)
    return canvas


def draw_frame(height, width, body, left_hand=None, right_hand=None,
               threshold=DEFAULT_THRESHOLD, stickwidth_type="v2",
               draw_head=True, draw_hands=True):
    """One complete pose-stick frame: black canvas, body pass, then each hand pass.

    Order matches `draw_aapose_new`: the body is drawn first and the hands over it.
    """
    canvas = blank_canvas(height, width)
    draw_body(canvas, body, threshold=threshold, stickwidth_type=stickwidth_type,
              draw_head=draw_head)
    if draw_hands:
        for hand in (left_hand, right_hand):
            if hand is not None:
                draw_hand(canvas, hand, threshold=threshold,
                          stickwidth_type=stickwidth_type)
    return canvas
