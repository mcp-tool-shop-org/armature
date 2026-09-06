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

import hashlib
import json
import math
import os

import numpy as np

from .errors import ArmatureError
from .parts import require_finite


class ConventionError(ArmatureError):
    """Gate CONV refused: the drawing convention is not the one that was recorded.

    A named andon, so the receipt can say which one pulled — the way `ClipStatsError`,
    `ClipCompareError` and `SiteListError` were re-classed in wave 12 (F-d0de0c2d, wave
    14). Both of Gate CONV's refusals were `raise ArmatureError(<message>)` with ONE
    argument, and `errors.py`'s base has no `__init__`, so the halt line recorded an
    empty evidence dict with no `gate`, no `andon` and no `clause`. `check_convention` is
    a named ANDON on the control image and its receipt is what a run's provenance quotes;
    the reason the record exists at all is that a previous provenance line named a
    comparison no code performed, and a refusal from it produced the inverse — a halt
    whose receipt named nothing.

    A plain refusal writes `gate: None` + `andon` + `clause`: Gate CONV's id lives in the
    provenance key the tool writes, and this class is the andon, so the honest answer is
    written down rather than left absent.
    """

    # WAVE-14 MERGE (coordinator, 2026-09-04): the explicit constructor this class carried on its branch is gone — the
    # base `ArmatureError(message, evidence=None)` (core-gates, F-8393e66c root) stores what it is passed,
    # and both raise sites pass a full dict, so nothing observable changes; a non-GateFailure that
    # normalised to `{}` would have been a third rule where the family now has two (SEAM 8 §3, SEAM 10).


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


# ------------------------------------------------- the RECORDED reference (Gate CONV)
#
# F-499b7cfa, wave 12. **Gate CONV compared the module's tables against the module's own
# tables, and the provenance recorded the comparison it did not make.**
# `check_convention(keypoint_count, limb_seq, palette)` compared its three arguments
# element-for-element against `KEYPOINT_COUNT` / `LIMB_SEQ` / `PALETTE` in this same
# module, and the ONE production call site is `tools/render_pose_sticks.py::main`, whose
# call is `aapose.check_convention(len(aapose.KEYPOINT_NAMES), aapose.LIMB_SEQ,
# aapose.PALETTE)` — three parameters with zero degrees of freedom.
#
# Measured 2026-09-04 on the wave-12 base: the tool's exact call returns True; then, with
# the module's own tables swapped to a ControlNet-18 shape (`KEYPOINT_NAMES[:18]`,
# `PALETTE[:18]`, `LIMB_SEQ` opened with ControlNet's closing pairs `(3,17),(6,18)`) —
# precisely the conflation this module's docstring says it exists to keep visible — the
# SAME call still returns True. The run then writes
# `"CONV": {"verdict": "PASS", "detail": "... vs wan/modules/animate/preprocess/
# human_visualization.py @ 29d4a35d3227"}`: a verdict naming a comparison against the
# fetched source that no code in the run performs. That is this repo's named
# most-expensive defect class, on the artifact that decides what the model draws.
#
# So the convention is RECORDED here, once, as data — a second transcription from the
# banked source, held apart from the live tables above so that the gate has something to
# compare them against — and the record is pinned by a digest over its own canonical JSON.
# An edit to the live tables now fires the gate; an edit to BOTH the live tables and this
# record has to recompute `RECORDED_CONVENTION_SHA256`, which is a deliberate, visible act
# rather than a silent one.
#
# **Why it is in this module and not a sidecar data file.** The wave-12 frozen domain map
# gives core-solvers twenty-one named `.py` files and no data directory; a new
# `armature_core/data/*.json` would be an ownership violation that blocks the wave. The
# digest gives the in-module record the property the sidecar was wanted for. The seam is
# posted for whoever holds the map next.
#
# The banked source (`outputs/E08/convention/human_visualization.py`) is checked when it is
# present and reported ABSENT when it is not — `outputs/` is git-ignored by design, so it
# is absent in every fresh checkout including CI. `check_convention` says which of those
# happened; it does not print a verdict naming a file it never opened.

RECORDED_CONVENTION = {
    "source_path": "wan/modules/animate/preprocess/human_visualization.py",
    "source_commit": "29d4a35d32273d5309a3a95250bd4e118d8789b2",
    "source_sha256": "962813c71b2f2e09f7cd745b35b31a0d278b122b5f2f429018d0576c795eda33",
    "function": "draw_aapose_new via draw_aapose_by_meta_new",
    "recorded": "2026-09-04",
    "keypoint_names": [
        "Nose", "Neck", "RShoulder", "RElbow", "RWrist", "LShoulder", "LElbow", "LWrist",
        "RHip", "RKnee", "RAnkle", "LHip", "LKnee", "LAnkle",
        "REye", "LEye", "REar", "LEar", "LToe", "RToe",
    ],
    "limb_seq": [
        [2, 3], [2, 6],
        [3, 4], [4, 5],
        [6, 7], [7, 8],
        [2, 9], [9, 10], [10, 11],
        [2, 12], [12, 13], [13, 14],
        [2, 1],
        [1, 15], [15, 17], [1, 16], [16, 18],
        [14, 19], [11, 20],
    ],
    "palette": [
        [255, 0, 0], [255, 85, 0], [255, 170, 0], [255, 255, 0],
        [170, 255, 0], [85, 255, 0], [0, 255, 0], [0, 255, 85],
        [0, 255, 170], [0, 255, 255], [0, 170, 255], [0, 85, 255],
        [0, 0, 255], [85, 0, 255], [170, 0, 255], [255, 0, 255],
        [255, 0, 170], [255, 0, 85],
        [200, 200, 0], [100, 100, 0],
    ],
    "hand_edges": [
        [0, 1], [1, 2], [2, 3], [3, 4],
        [0, 5], [5, 6], [6, 7], [7, 8],
        [0, 9], [9, 10], [10, 11], [11, 12],
        [0, 13], [13, 14], [14, 15], [15, 16],
        [0, 17], [17, 18], [18, 19], [19, 20],
    ],
    "keypoint_count": 20,
    "hand_keypoint_count": 21,
    "limb_brightness": 0.6,
    "hand_joint_color": [0, 0, 255],
    "default_threshold": 0.5,
    "hand_eps": 0.01,
}

#: sha256 over `json.dumps(RECORDED_CONVENTION, sort_keys=True, separators=(",", ":"))`.
#: Recomputed only in a commit that deliberately re-records the convention.
#:
#: Recomputed 2026-09-04 (F-33d53180, wave 16) in the commit that added `hand_eps` and
#: `keypoint_count` to the record — the deliberate, visible act the block above says a
#: re-record has to be. Previous value
#: 90489445a74fe61343136677d99515256e663290c5ae49a27d5c06748eff84f5, over the thirteen-
#: field record. `hand_eps` transcribes `draw_handpose_new`'s eps guard on hand
#: coordinates; `keypoint_count` is `len(KEYPOINT_NAMES)` written down because
#: `KEYPOINT_COUNT` is read by `draw_body` and the derivation below therefore requires it
#: to have a recorded value. Before this, the previous value
#: 0967b4a45e34abc99d85a36fb58f6ead399a37fbbfdc2424738c1b746339d79c stood over the
#: eleven-field record (F-d59fab92, wave 14).
RECORDED_CONVENTION_SHA256 = (
    "81bfaea17933bcf87daa22e425965a3892bdccbddf667ea648374f8e8d814266")

#: Where the fetched source is banked when a session has fetched it. Git-ignored by design.
BANKED_SOURCE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "outputs", "E08", "convention", "human_visualization.py")


def recorded_convention_digest(record=None):
    """sha256 over the canonical JSON of `RECORDED_CONVENTION`."""
    rec = RECORDED_CONVENTION if record is None else record
    blob = json.dumps(rec, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def banked_source_state():
    """`(state, sha256_or_None)` for the fetched source — `verified`, `MISMATCH`, `absent`.

    A diagnostic, not a gate on its own: the file is git-ignored, so "absent" is the
    ordinary state of a fresh checkout and refusing on it would take every render down.
    What the gate refuses is a MISMATCH, which is the only reading that means the pin and
    the file disagree.

    **Read against the RECORD's hash, not `SOURCE`'s** (F-d59fab92, wave 14). This
    compared the file against `SOURCE["sha256"]`, which sits OUTSIDE
    `RECORDED_CONVENTION_SHA256`, rather than against `RECORDED_CONVENTION
    ["source_sha256"]`, which sits inside it. The two are equal today and were never
    compared to each other, so the one hash the digest protects was not the one the file
    was checked against. `check_convention` now asserts the two agree as its own clause,
    which is the check that keeps them equal.
    """
    try:
        with open(BANKED_SOURCE, "rb") as fh:
            got = hashlib.sha256(fh.read()).hexdigest()
    except OSError:
        return "absent", None
    if got != RECORDED_CONVENTION["source_sha256"]:
        return "MISMATCH", got
    return "verified", got

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
        f"'v2' and takes the else branch to a bare raise",
        {"gate": None, "andon": "ArmatureError", "clause": "unknown_stickwidth_type",
         "stickwidth_type": stickwidth_type, "defined": ["v1", "v2"],
         "where": "stickwidth"})


def hand_stickwidth(height, width, stickwidth_type="v2"):
    """`draw_handpose_new`'s width, verbatim — HALF the body width in v2, floored at 1."""
    m = min(int(height), int(width))
    if stickwidth_type == "v1":
        return max(int(m / 200), 1)
    if stickwidth_type == "v2":
        return max(max(int(m / 200) - 1, 1) // 2, 1)
    raise ArmatureError(
        f"unknown stickwidth_type {stickwidth_type!r}",
        {"gate": None, "andon": "ArmatureError", "clause": "unknown_stickwidth_type",
         "stickwidth_type": stickwidth_type, "defined": ["v1", "v2"],
         "where": "hand_stickwidth"})


# --------------------------------------------------------------------- the rig map

#: AAPose index (0-based, matching KEYPOINT_NAMES) -> the rig LANDMARK that supplies it.
#: Landmarks, not bones-and-ends: `toe_L` / `toe_R` are measured landmarks in the rig
#: manifest, whereas the ankle bones' tails do not survive a glTF round trip — the importer
#: synthesises a tail for every leaf bone, and the ankles are leaves. Measured 2026-08-12;
#: the falsified route is kept runnable at
#: `tools/superseded/project_pose_keypoints_from_glb.py` with its numbers.
LANDMARK_SITES = (
    "nose",          # 0  Nose      — MEASURED (furthest head vertex along the facing)
    "neck_base",     # 1  Neck      — bone `neck` head sits here
    "shoulder_R",    # 2  RShoulder
    "elbow_R",       # 3  RElbow
    "wrist_R",       # 4  RWrist
    "shoulder_L",    # 5  LShoulder
    "elbow_L",       # 6  LElbow
    "wrist_L",       # 7  LWrist
    "hip_R",         # 8  RHip
    "knee_R",        # 9  RKnee
    "ankle_R",       # 10 RAnkle
    "hip_L",         # 11 LHip
    "knee_L",        # 12 LKnee
    "ankle_L",       # 13 LAnkle
    "eye_R",         # 14 REye      — DERIVED: this mesh carries no eye feature
    "eye_L",         # 15 LEye      — DERIVED
    "ear_R",         # 16 REar      — DERIVED: no ear feature either
    "ear_L",         # 17 LEar      — DERIVED
    "toe_L",         # 18 LToe      — MEASURED (furthest foot vertex, at ground)
    "toe_R",         # 19 RToe      — MEASURED
)

#: Each hand's frame, as (wrist, hand end, elbow) landmarks. The mannequin has mitten hands
#: with no fingers, so the 21 hand keypoints are SYNTHESISED in this frame — see
#: `mitten_hand`. The elbow is here only to orient the palm; see `hand_frame`.
HAND_SITES = {
    "left": ("wrist_L", "hand_end_L", "elbow_L"),
    "right": ("wrist_R", "hand_end_R", "elbow_R"),
}


def required_sites():
    """Every rig landmark this convention reads, body and hands."""
    out = list(LANDMARK_SITES)
    for triple in HAND_SITES.values():
        out.extend(triple)
    return tuple(dict.fromkeys(out))


def require_rig_map(available_sites):
    """Raise unless every landmark this convention needs exists. ANDON.

    Called before any keypoint is placed. **The andon is on the direction the invariant does
    not bound:** a missing landmark would otherwise surface as a keypoint silently left at
    the origin, which draws a limb running to the corner of the frame and errors nowhere.
    """
    have = set(available_sites)
    missing = sorted(s for s in required_sites() if s not in have)
    if missing:
        raise ArmatureError(
            f"the AAPose-20 map names rig landmark(s) that are not available: {missing}. "
            f"A keypoint with nothing behind it would be written as a zero and drawn as a "
            f"limb running off the frame, with nothing erroring. Available: "
            f"{sorted(have)}",
            {"gate": None, "andon": "ArmatureError",
             "clause": "required_landmark_missing",
             "missing": missing, "available": sorted(have)})
    return True


def hand_frame(wrist, hand_end, elbow):
    """(palm_dir, palm_side, length) for one hand, from three rig landmarks.

    `palm_dir` runs wrist -> hand end, so its length is this hand's own measured length.
    `palm_side` is the in-plane perpendicular — the direction a thumb splays — built from the
    forearm so that the constructed hand turns with the arm instead of sitting in a fixed
    world orientation.

    **The degenerate case is handled rather than left to produce a NaN.** When the hand is
    exactly collinear with the forearm the cross product vanishes and the plane is
    undefined; world up is the fallback reference, and if the hand points straight up too,
    world +X. A NaN here would propagate into pixel coordinates and cv2 would draw
    something at an arbitrary place without complaint.
    """
    w = np.asarray(wrist, dtype=np.float64)
    h = np.asarray(hand_end, dtype=np.float64)
    e = np.asarray(elbow, dtype=np.float64)

    v = h - w
    length = float(np.linalg.norm(v))
    if length <= 0.0:
        raise ArmatureError(
            f"wrist and hand end are the same point (length={length}); this hand has no "
            f"length and no direction",
            {"gate": None, "andon": "ArmatureError", "clause": "hand_has_no_length",
             "length": length})
    d = v / length

    for ref in (w - e, np.array([0.0, 0.0, 1.0]), np.array([1.0, 0.0, 0.0])):
        n = np.cross(ref, d)
        if np.linalg.norm(n) > 1e-9:
            n = n / np.linalg.norm(n)
            s = np.cross(n, d)
            return d, s / np.linalg.norm(s), length
    raise ArmatureError(
        f"could not build a palm plane over a hand of length {length}; all 3 references "
        f"were collinear with it",
        {"gate": None, "andon": "ArmatureError", "clause": "palm_plane_degenerate",
         "hand_length": length, "references_tried": 3})


def _compare_against_record(label, keypoint_count, limb_seq, palette, record):
    """Element-for-element differences between one triple and the RECORDED reference."""
    problems = []
    want_names = record["keypoint_names"]
    if int(keypoint_count) != len(want_names):
        problems.append(
            f"{label}: keypoint count {keypoint_count} != {len(want_names)}")

    ours = [tuple(p) for p in limb_seq]
    want_limbs = [tuple(p) for p in record["limb_seq"]]
    if len(ours) != len(want_limbs):
        problems.append(f"{label}: limb pair count {len(ours)} != {len(want_limbs)}")
    else:
        for i, (a, b) in enumerate(zip(ours, want_limbs)):
            if a != b:
                problems.append(f"{label}: limb pair {i}: {a} != recorded {b}")

    flat = [v for pair in ours for v in pair]
    if flat and min(flat) == 0:
        problems.append(
            f"{label}: limb pairs are 0-indexed; the source's limbSeq is 1-indexed")

    pal = [tuple(c) for c in palette]
    want_pal = [tuple(c) for c in record["palette"]]
    if len(pal) != len(want_pal):
        problems.append(f"{label}: palette length {len(pal)} != {len(want_pal)}")
    else:
        for i, (a, b) in enumerate(zip(pal, want_pal)):
            if a != b:
                problems.append(f"{label}: palette entry {i}: {a} != recorded {b}")
    return problems


#: The functions in this module that put pixels on a canvas. They are the DEFINITION of
#: "a drawing constant": a module-level constant one of them reads decides what is drawn,
#: whatever it is called and whenever it was added.
PIXEL_WRITERS = ("blank_canvas", "draw_body", "draw_hand", "draw_frame", "stickwidth",
                 "hand_stickwidth")


def drawing_constants():
    """Every module-level constant one of `PIXEL_WRITERS` reads, derived from this file.

    **The class, not the instance** (F-33d53180, wave 16). Wave 14 closed four named
    constants by typing four names into `_compare_drawing_constants` — whose docstring
    then called them "The four module constants that decide what pixels are drawn". A
    fifth already existed: `HAND_EPS`, read by `draw_hand` at every hand limb and every
    hand joint dot, in neither the record nor the comparison and therefore outside
    `RECORDED_CONVENTION_SHA256` and outside Gate CONV. Measured 2026-09-04 with
    `HAND_EPS` set to 0.9 — which skips every hand stroke and every hand dot on a
    normalised coordinate — `check_convention(len(KEYPOINT_NAMES), LIMB_SEQ, PALETTE)`
    returned `verdict: PASS` with the unchanged detail line.

    A hand-typed list cannot see the constant nobody thought to add to it, so the list is
    gone: the population is read off the module's own AST, and a sixth drawing constant
    joins Gate CONV on the day it is written. The record field for a constant is its name
    lower-cased; a constant with no such field is refused by `check_convention` rather
    than silently uncompared.

    The stickwidth divisor is the remaining drawing quantity outside this derivation: it
    is the literal `200` inside `stickwidth`/`hand_stickwidth` and not a named constant,
    so an AST walk over reads cannot see it. It is pinned numerically by
    `tests/test_aapose_convention.py`, which is stated here rather than left for a reader
    to assume.
    """
    import ast

    with open(os.path.abspath(__file__).replace(".pyc", ".py"), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    module_level = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    module_level.add(target.id)
    read = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in PIXEL_WRITERS:
            for sub in ast.walk(node):
                if (isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load)
                        and sub.id in module_level):
                    read.add(sub.id)
    return tuple(sorted(read))


#: The record fields that decide what is drawn but are not read by a pixel writer under
#: their own name: the keypoint NAMES (the convention's naming, compared by
#: `_compare_against_record`) and the banked source's hash (the provenance clause that
#: keeps `SOURCE` and the record equal). Everything else in the compared set is derived.
NON_DRAWING_FIELDS_COMPARED = ("keypoint_names", "source_sha256")

#: Which `RECORDED_CONVENTION` fields `check_convention` actually compares — DERIVED, so
#: the coverage is a measurement of this module rather than a list somebody remembered to
#: extend (F-33d53180). `source_path`, `source_commit` and `recorded` are provenance
#: strings the message quotes and are the record's remaining three fields.
RECORD_FIELDS_COMPARED = tuple(sorted(
    {c.lower() for c in drawing_constants()} | set(NON_DRAWING_FIELDS_COMPARED)))


#: Why a reader should care that a given constant moved, appended to the problem line.
#: A note is prose about a field; the COMPARISON is derived, so a field with no note is
#: compared exactly the same way.
WHY_IT_DECIDES_PIXELS = {
    "limb_brightness": " — this is the literal every limb polygon is filled with",
    "default_threshold": " — points below it are skipped entirely",
    "hand_eps": " — every hand limb and every hand joint dot is drawn only where both "
                "coordinates exceed it, so raising it on a normalised coordinate erases "
                "the hands",
    "keypoint_count": " — the body loop's length",
}


def _canonical(v):
    """A comparable, JSON-shaped reading of a constant or a recorded value.

    Tuples and lists compare as lists and numbers as floats, so `(0, 0, 255)` and
    `[0, 0, 255]` are the same colour and `21` and `21.0` are the same count — the
    difference between a Python literal and its JSON transcription is not a drift.
    """
    if isinstance(v, (list, tuple)):
        return [_canonical(x) for x in v]
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return float(v)
    return v


def _compare_drawing_constants(record):
    """Every constant `drawing_constants()` derives, against its recorded value.

    F-d59fab92, wave 14. `RECORDED_CONVENTION` carried nine fields and
    `check_convention` compared five of them; `hand_keypoint_count` and `limb_brightness`
    were pinned by the digest and compared against nothing, and `HAND_JOINT_COLOR` and
    `DEFAULT_THRESHOLD` were in neither the record nor the comparison. Measured
    2026-09-04 with `LIMB_BRIGHTNESS` set to 1.0, `HAND_KEYPOINT_COUNT` to 18,
    `HAND_JOINT_COLOR` to (255, 0, 0) and `DEFAULT_THRESHOLD` to 0.0:
    `check_convention(len(KEYPOINT_NAMES), LIMB_SEQ, PALETTE)` returned verdict PASS with
    the unchanged detail line "20 keypoints / 19 pairs / 20 palette entries, module
    tables and caller both equal to RECORDED_CONVENTION".

    None of the four is inert. `LIMB_BRIGHTNESS` is the literal that fills every limb
    polygon (`draw_body`) and `tools/render_pose_sticks.py` writes it into the run's
    provenance as a conformance fact; `HAND_KEYPOINT_COUNT` is the shape both
    `mitten_hand` and `draw_hand` enforce; `HAND_JOINT_COLOR` is every hand joint dot;
    `DEFAULT_THRESHOLD` is the point-skipping threshold, also written to provenance. A
    limb-brightness or threshold edit reached the frames the model obeys with Gate CONV
    green and the provenance quoting the edited value beside a PASS.
    """
    problems = []
    for name in drawing_constants():
        field = name.lower()
        if field not in record:
            # The clause that closes the class: a drawing constant with no recorded
            # value. `check_convention` refuses on this before it compares anything, so
            # reaching it here means the record was edited between the two.
            problems.append(
                f"module tables: {field} is read by {', '.join(PIXEL_WRITERS)} and has no "
                f"recorded value, so nothing compares it")
            continue
        got, want = _canonical(globals()[name]), _canonical(record[field])
        if got != want:
            problems.append(
                f"module tables: {field} {got} != recorded {want}"
                + WHY_IT_DECIDES_PIXELS.get(field, ""))
    if SOURCE["sha256"] != record["source_sha256"]:
        problems.append(
            f"the module's SOURCE hash {SOURCE['sha256'][:16]} is not the record's "
            f"source_sha256 {record['source_sha256'][:16]}; the digest pins the second, "
            f"so the banked file must be checked against it")
    return problems


def check_convention(keypoint_count, limb_seq, palette):
    """Gate CONV · ANDON — conformance against the RECORDED reference. Raises `ArmatureError`.

    Three comparisons, in the order a reader should trust them, and the returned dict says
    which ones ran:

    1. **The record against its own digest.** `RECORDED_CONVENTION` is pinned by
       `RECORDED_CONVENTION_SHA256`, so the reference cannot be edited into agreement with
       a wrong table without the pin firing.
    2. **This module's live tables against the record.** THE clause the gate was missing.
    3. **The caller's arguments against the record** — the original comparison, kept,
       because a caller may hand in tables it built itself.

    Plus the banked source's own sha256 when the file is present (`banked_source_state`).

    **What this replaces, and why** (F-499b7cfa, wave 12 — see the RECORDED reference
    block above). The three parameters were read off the same tables they were compared
    with, so the gate had zero degrees of freedom and could not fail; the run's provenance
    nonetheless wrote `"CONV": {"verdict": "PASS", "detail": "... vs
    human_visualization.py @ 29d4a35d3227"}` — a verdict naming a comparison against the
    fetched source that no code performed. Measured on the base: with the module's own
    tables swapped to a ControlNet-18 shape the tool's exact call still returned True.

    **Returns a dict, not `True`.** A provenance record must be able to quote what was
    actually compared instead of a literal typed at the call site: `compared_against`,
    `recorded_sha256`, `banked_source`, `source_commit` and a `detail` line that names the
    fetched file ONLY when the fetched file was hashed. The dict is truthy, so an existing
    `if check_convention(...)` still reads the same.

    **The comparison now covers the record, not five of its fields** (F-d59fab92, wave
    14). Wave 12 closed the "does the record match itself" half; what was left open was
    COVERAGE. `RECORDED_CONVENTION` carried nine fields and this function compared five
    — `keypoint_names`, `limb_seq`, `palette`, `hand_edges`, and the `source_commit` /
    `recorded` strings as prose in the message. `hand_keypoint_count` and
    `limb_brightness` were pinned by the digest and compared against nothing;
    `HAND_JOINT_COLOR` and `DEFAULT_THRESHOLD` were in neither. All four decide what
    pixels are drawn and two of them are written into the run's provenance as
    conformance facts. `_compare_drawing_constants` closes all four, the record grew the
    two missing fields (and its digest was recomputed in that same deliberate commit),
    and `fields_compared` rides the returned dict so the coverage is a quantity a
    provenance record carries rather than a claim in a docstring.

    Also closed there: the banked-source clause compared against `SOURCE['sha256']`,
    which is outside the digest, rather than against `record['source_sha256']`, which is
    inside it. `banked_source_state` reads the record's hash now, and their equality is
    itself one of the compared clauses — so the value the digest pins is the value the
    file is checked against.

    **It raises `ConventionError`, and both refusals carry a receipt** (F-d0de0c2d).
    """
    record = RECORDED_CONVENTION
    outside = [c for c in drawing_constants() if c.lower() not in record]
    if outside:
        raise ConventionError(
            f"{outside} are read by this module's pixel writers "
            f"({', '.join(PIXEL_WRITERS)}) and have no recorded value, so Gate CONV "
            f"cannot compare them and the digest does not pin them. A constant that "
            f"decides what is drawn and sits outside the record is the shape `HAND_EPS` "
            f"had: edited, the gate returns PASS and the run's provenance quotes that "
            f"PASS beside the edited value on the frames the video model obeys. Record "
            f"the value from the banked source and recompute "
            f"RECORDED_CONVENTION_SHA256 in the same commit",
            {"gate": None, "andon": "ConventionError",
             "clause": "drawing_constant_outside_the_record",
             "constants_outside_the_record": outside,
             "pixel_writers": list(PIXEL_WRITERS),
             "recorded_fields": sorted(record)})
    digest = recorded_convention_digest(record)
    if digest != RECORDED_CONVENTION_SHA256:
        raise ConventionError(
            "the recorded AAPose-20 reference does not match its own pinned digest "
            f"(computed {digest[:16]}, pinned {RECORDED_CONVENTION_SHA256[:16]}). The "
            "record is what Gate CONV compares the module's tables against, so a record "
            "that has drifted turns the gate back into the module checking itself. "
            "Re-record the convention from the banked source and update the pin in the "
            "same commit",
            {"gate": None, "andon": "ConventionError",
             "clause": "recorded_convention_digest_drift",
             "computed_sha256": digest, "pinned_sha256": RECORDED_CONVENTION_SHA256,
             "recorded_on": record.get("recorded"),
             "source_path": record.get("source_path"),
             "source_commit": record.get("source_commit")})

    problems = _compare_against_record(
        "module tables", KEYPOINT_COUNT, LIMB_SEQ, PALETTE, record)
    problems += _compare_against_record(
        "caller", keypoint_count, limb_seq, palette, record)
    if list(KEYPOINT_NAMES) != list(record["keypoint_names"]):
        problems.append(
            f"module tables: keypoint names {list(KEYPOINT_NAMES)} != recorded "
            f"{record['keypoint_names']}")
    if [tuple(e) for e in HAND_EDGES] != [tuple(e) for e in record["hand_edges"]]:
        problems.append("module tables: hand edges differ from the recorded reference")
    problems += _compare_drawing_constants(record)

    banked, banked_sha = banked_source_state()
    if banked == "MISMATCH":
        problems.append(
            f"the banked source at {BANKED_SOURCE} hashes {banked_sha[:16]} and the "
            f"record's source_sha256 — the hash the digest pins — is "
            f"{record['source_sha256'][:16]}")

    if problems:
        raise ConventionError(
            "the emitted skeleton does not match the recorded reference for the Wan "
            f"AAPose-20 convention ({record['source_path']} @ "
            f"{record['source_commit'][:12]}, recorded {record['recorded']}): "
            + "; ".join(problems),
            {"gate": None, "andon": "ConventionError",
             "clause": "convention_nonconformance",
             "problems": problems,
             "computed_sha256": digest, "pinned_sha256": RECORDED_CONVENTION_SHA256,
             "banked_source": banked, "banked_source_sha256": banked_sha,
             "source_path": record.get("source_path"),
             "source_commit": record.get("source_commit")})

    if banked == "verified":
        detail = (f"{len(record['keypoint_names'])} keypoints / "
                  f"{len(record['limb_seq'])} pairs / {len(record['palette'])} palette "
                  f"entries, module tables and caller both equal to "
                  f"RECORDED_CONVENTION (digest {digest[:12]}); banked "
                  f"{record['source_path']} @ {record['source_commit'][:12]} hashed and "
                  f"matching the pin")
    else:
        detail = (f"{len(record['keypoint_names'])} keypoints / "
                  f"{len(record['limb_seq'])} pairs / {len(record['palette'])} palette "
                  f"entries, module tables and caller both equal to "
                  f"RECORDED_CONVENTION (digest {digest[:12]}); the fetched source was "
                  f"NOT opened by this run (banked copy absent — outputs/ is git-ignored)")

    return {
        "verdict": "PASS",
        "compared_against": "armature_core.aapose.RECORDED_CONVENTION",
        "recorded_sha256": RECORDED_CONVENTION_SHA256,
        "recorded_on": record["recorded"],
        "source_path": record["source_path"],
        "source_commit": record["source_commit"],
        "banked_source": banked,
        "banked_source_sha256": banked_sha,
        "keypoint_count": len(record["keypoint_names"]),
        "limb_pairs": len(record["limb_seq"]),
        "palette_entries": len(record["palette"]),
        "fields_compared": sorted(RECORD_FIELDS_COMPARED),
        "n_fields_compared": len(RECORD_FIELDS_COMPARED),
        "n_fields_in_record": len(record),
        "detail": detail,
    }


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
        raise ArmatureError(
            f"a hand needs a positive length to lay finger points along, and this one is "
            f"{L}",
            {"gate": None, "andon": "ArmatureError", "clause": "hand_length_not_positive",
             "hand_length": L})

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
            f"{HAND_KEYPOINT_COUNT}",
            {"gate": None, "andon": "ArmatureError",
             "clause": "mitten_hand_wrong_point_count",
             "built": len(out), "recorded": HAND_KEYPOINT_COUNT})
    return out


# ---------------------------------------------------------------------- the drawing

def blank_canvas(height, width):
    """The zeroed-black canvas the convention draws onto. uint8, 3 channels."""
    return np.zeros((int(height), int(width), 3), dtype=np.uint8)


def require_readable_keypoints(kp, threshold, where):
    """Refuse a keypoint record this convention cannot draw from. · ANDON

    F-6bdd660a, wave 22. Confidence is read at four sites — twice in `draw_body`, twice in
    `draw_hand` — and every one was a bare `< threshold`, with no finiteness bound anywhere
    in this module: `aapose` was one of nine `armature_core` modules that did not import
    `parts.require_finite`. **A NaN fails `<` in both directions**, so the keypoint was
    treated as fully confident and DRAWN.

    MEASURED on `e8263a3` on a 20x3 body at 256x256: baseline 2075 non-black pixels; the
    same body with keypoint 5's confidence set to NaN drew **2075** non-black pixels —
    byte-identical ink to confidence 1.0 — with no refusal, where a real detector's low
    confidence would have dropped the joint. The three unreadable spellings each read
    differently and none of them is a decision: `nan` draws the joint as certain, `+inf`
    reads as certain, `-inf` reads as absent.

    The COORDINATE direction escaped the family instead of walking past it: keypoint 5's x
    set to NaN raised a bare `ValueError: cannot convert float NaN to integer` (from
    `int(mY)` / `int(point[0])`) and `+inf` a bare `OverflowError`, NEITHER in the
    `ArmatureError` family — so the 21-tool halt contract recorded exit 1 "FAILED — an
    unhandled error" where a typed refusal at exit 2 belongs.

    And the THRESHOLD itself: `c < nan` is False at every keypoint, so a NaN threshold draws
    everything; `c < inf` is True at every keypoint, so it draws nothing. Neither is a
    decision, and nothing downstream could tell which had happened.

    **The coordinate clause is graded only on what it can move**: a keypoint the convention
    skips is not a pixel this frame carries, so only the coordinates of keypoints that will
    actually be DRAWN are bounded. The confidence clause runs over the whole record, and
    over the record as GIVEN — before `draw_head=False` zeroes five of them — because a
    confidence that is not a number is a broken record whatever a flag then does with it.

    Reachability: the keypoint record is read from JSON (`render_pose_sticks`, and Python's
    `json.load` accepts the literal `NaN`), so the moment a producer other than
    `project_pose_keypoints` supplies confidences — which the record's own note anticipates,
    "a real detector would report low confidence on an occluded joint" — an occluded joint
    whose confidence is not a number is drawn as certain into the control frame that steers a
    paid generation, and `gate_INK` cannot see it because the ink is there.

    ⚠ **SEAM, routed to instruments-measure.** `render_pose_sticks.gate_canvas` unpacks
    `for j, (x, y, _c) in enumerate(frame)` and DISCARDS the confidence, so it bounds
    coordinates only; `make_overlay_sheet` calls `draw_frame` with no canvas gate at all.
    The bound here is inside the function performing the step, which is where this repo puts
    an andon; a complementary bound at the reader is theirs to add.
    """
    ev = {"gate": None, "andon": "ConventionError", "where": where}
    require_finite("threshold", threshold, ConventionError,
                   dict(ev, clause="threshold_not_a_number"), positive=False)
    t = float(threshold)
    conf = [float(c) for c in np.asarray(kp, dtype=np.float64)[:, 2]]
    bad = [i for i, c in enumerate(conf) if not math.isfinite(c)]
    if bad:
        detail = dict(ev, clause="confidence_not_a_number", indices=bad,
                      n_keypoints=len(conf))
        for i in bad:
            require_finite(f"confidence[{i}]", conf[i], ConventionError, detail,
                           positive=False)
    drawn = [i for i, c in enumerate(conf) if not (c < t)]
    arr = np.asarray(kp, dtype=np.float64)
    bad_xy = [i for i in drawn
              if not (math.isfinite(float(arr[i, 0])) and math.isfinite(float(arr[i, 1])))]
    if bad_xy:
        detail = dict(ev, clause="drawn_keypoint_coordinate_not_a_number",
                      indices=bad_xy, threshold=t, n_drawn=len(drawn))
        for i in bad_xy:
            for axis, name in ((0, "x"), (1, "y")):
                require_finite(f"{name}[{i}]", arr[i, axis], ConventionError, detail,
                               positive=False)


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
            f"{kp.shape}",
            {"gate": None, "andon": "ArmatureError", "clause": "body_keypoints_wrong_shape",
             "shape": list(kp.shape), "expected": [KEYPOINT_COUNT, 3]})
    require_readable_keypoints(kp, threshold, "draw_body")
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
            f"hand keypoints must be ({HAND_KEYPOINT_COUNT}, 3), got {kp.shape}",
            {"gate": None, "andon": "ArmatureError", "clause": "hand_keypoints_wrong_shape",
             "shape": list(kp.shape), "expected": [HAND_KEYPOINT_COUNT, 3]})
    require_readable_keypoints(kp, threshold, "draw_hand")
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
