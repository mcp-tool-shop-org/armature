"""The OpenPose-18 convention — only the part that has actually been retrieved.

F20 (docs/research-grounding.md) is marked **verified by direct source retrieval**:
`limbSeq` was fetched from lllyasviel/ControlNet `annotator/openpose/util.py` and read
at ruling time. It is 19 pairs and it is **1-indexed**, which is a live trap for a
from-scratch renderer. Those values are pinned below and G5 compares against them
element for element.

What F20 does **not** record is the 18-colour per-limb palette (it says the palette
exists in `draw_bodypose()`; it does not quote the values) or the keypoint *names* and
their order. Writing either from memory would put an unretrieved assertion inside a
gate, and CLAUDE.md forbids a report carrying a placeholder shaped like evidence. So
they are `None` here, and `require_drawing_convention()` raises rather than inventing
them. The advisor resolves the citation; until then this module can verify a skeleton's
topology but not draw one.

Nothing in this module is an ML estimator: a skeleton drawn from known bone transforms
is arithmetic. The banned tier (OpenPose is CMU non-commercial — see
docs/license-map.md) is sidestepped by construction, not by substitution.
"""

from .errors import ArmatureError

#: F20, retrieved 2026-08-10. 19 pairs, 1-indexed.
LIMB_SEQ = [
    [2, 3], [2, 6], [3, 4], [4, 5], [6, 7], [7, 8], [2, 9], [9, 10],
    [10, 11], [2, 12], [12, 13], [13, 14], [2, 1], [1, 15], [15, 17],
    [1, 16], [16, 18], [3, 17], [6, 18],
]

#: F20: "18 keypoints".
KEYPOINT_COUNT = 18

#: Not retrieved. See the module docstring.
PALETTE = None
KEYPOINT_NAMES = None

SOURCE = (
    "F20 — lllyasviel/ControlNet annotator/openpose/util.py, as quoted in "
    "docs/research-grounding.md; limbSeq fetched and read at ruling time"
)


def require_drawing_convention():
    """Raise unless the parts needed to *draw* a skeleton have been retrieved.

    The andon is on the direction the invariant does not bound: `LIMB_SEQ` is pinned,
    so topology is checkable; the palette and keypoint order are not, so drawing is
    the unbounded direction and that is what halts.
    """
    missing = [n for n, v in (("PALETTE", PALETTE), ("KEYPOINT_NAMES", KEYPOINT_NAMES)) if v is None]
    if missing:
        raise ArmatureError(
            "the OpenPose-18 drawing convention is not fully retrieved: "
            f"{', '.join(missing)} unresolved. F20 pins limbSeq and the keypoint "
            "count but does not record the palette or the keypoint order, and this "
            "tool does not write conventions from memory. Retrieve them into "
            "docs/research-grounding.md before emitting a pose channel."
        )
    return True
