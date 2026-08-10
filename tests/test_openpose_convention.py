"""The limbSeq fixture, pinned against F20's retrieved values.

Pinned so a future edit to the skeleton renderer fails loudly rather than drifting.
The values below are transcribed from `docs/research-grounding.md` F20, which records
them as **verified by direct source retrieval** — lllyasviel/ControlNet
`annotator/openpose/util.py`, fetched and read at ruling time. This test also reads
that document, so the fixture and the record cannot drift apart silently.
"""

import os
import re

from armature_core import openpose

# Transcribed from docs/research-grounding.md F20. Not from memory.
F20_LIMB_SEQ = [
    [2, 3], [2, 6], [3, 4], [4, 5], [6, 7], [7, 8], [2, 9], [9, 10],
    [10, 11], [2, 12], [12, 13], [13, 14], [2, 1], [1, 15], [15, 17],
    [1, 16], [16, 18], [3, 17], [6, 18],
]


def test_limbseq_matches_f20_element_for_element():
    assert openpose.LIMB_SEQ == F20_LIMB_SEQ


def test_limbseq_is_nineteen_pairs():
    assert len(openpose.LIMB_SEQ) == 19
    assert all(len(p) == 2 for p in openpose.LIMB_SEQ)


def test_limbseq_is_one_indexed_not_zero_indexed():
    """F20 calls the 1-indexing a live trap for a from-scratch renderer."""
    flat = [v for pair in openpose.LIMB_SEQ for v in pair]
    assert min(flat) == 1
    assert max(flat) == 18


def test_keypoint_count_is_eighteen_not_seventeen_or_twentyfive():
    assert openpose.KEYPOINT_COUNT == 18


def test_the_fixture_still_matches_the_document_it_was_transcribed_from():
    """If someone edits research-grounding.md's F20, this fails — which is the point.
    The code and the retrieved record are pinned to each other."""
    doc = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "docs", "research-grounding.md",
    )
    with open(doc, "r", encoding="utf-8") as fh:
        text = fh.read()
    pairs = re.findall(r"\[(\d+),\s*(\d+)\]", text)
    found = [[int(a), int(b)] for a, b in pairs]
    # F20's limbSeq is the only bracketed integer-pair list in the document.
    assert found == F20_LIMB_SEQ, f"docs/research-grounding.md no longer carries F20's limbSeq verbatim: {found}"


def test_drawing_is_refused_while_the_palette_is_unretrieved():
    """F20 records that a palette exists; it does not record its values. Writing one
    from memory would put an unretrieved assertion inside a gate."""
    import pytest

    from armature_core.errors import ArmatureError

    assert openpose.PALETTE is None
    assert openpose.KEYPOINT_NAMES is None
    with pytest.raises(ArmatureError) as exc:
        openpose.require_drawing_convention()
    assert "PALETTE" in str(exc.value)
