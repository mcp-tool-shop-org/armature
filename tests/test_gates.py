"""Gate unit tests.

Every one of these asks the question CLAUDE.md asks of a fixture: *what would this
look like if the code were wrong in the specific way this check exists to catch?*
"""

import os

import pytest

from armature_core import gates
from armature_core.errors import (
    G1GeneratorLegality,
    G2Completeness,
    G4BboxSanity,
    G5ConventionConformance,
)


# ------------------------------------------------------------------ G1 goes red

def test_g1_passes_a_legal_frame():
    profile = gates.g1_generator_legality(512, 768, 33, "wan-vace")
    assert profile.dim_divisor == 16
    assert profile.frame_modulus == 4 and profile.frame_residue == 1


def test_g1_red_on_width_not_divisible_by_16():
    # 1020 is the spec's named case: 1020 = 63.75 * 16.
    with pytest.raises(G1GeneratorLegality) as exc:
        gates.g1_generator_legality(1020, 768, 33, "wan-vace")
    assert "width=1020" in str(exc.value)
    assert exc.value.gate == "G1"


def test_g1_red_on_height_not_divisible_by_16():
    with pytest.raises(G1GeneratorLegality):
        gates.g1_generator_legality(512, 770, 33, "wan-vace")


def test_g1_red_on_frame_count_not_4n_plus_1():
    # 80 is the spec's named case: 80 % 4 == 0, not 1.
    with pytest.raises(G1GeneratorLegality) as exc:
        gates.g1_generator_legality(512, 768, 80, "wan-vace")
    assert "4n+1" in str(exc.value)


@pytest.mark.parametrize("count", [80, 81 + 1, 34, 35, 36])
def test_g1_only_accepts_the_right_residue(count):
    if count % 4 == 1:
        gates.g1_generator_legality(512, 768, count, "wan-vace")
    else:
        with pytest.raises(G1GeneratorLegality):
            gates.g1_generator_legality(512, 768, count, "wan-vace")


def test_g1_red_on_unknown_generator():
    """The andon is on the direction the invariant does not bound: an unknown
    generator is the case where *nothing* would be checked."""
    with pytest.raises(G1GeneratorLegality) as exc:
        gates.g1_generator_legality(512, 768, 33, "some-model-nobody-filed")
    assert "unknown generator profile" in str(exc.value)


def test_g1_red_on_bool_masquerading_as_int():
    with pytest.raises(G1GeneratorLegality):
        gates.g1_generator_legality(True, 768, 33, "wan-vace")


def test_g1_is_not_an_assertionerror():
    """`assert` is deleted by -O; a gate that raised AssertionError would vanish."""
    with pytest.raises(G1GeneratorLegality) as exc:
        gates.g1_generator_legality(1020, 768, 33, "wan-vace")
    assert not isinstance(exc.value, AssertionError)


# ------------------------------------------------------------------ G2 goes red

def _make_channel(tmp_path, name, filenames, blank=(), missing=()):
    d = tmp_path / name
    d.mkdir(parents=True, exist_ok=True)
    for f in filenames:
        if f in missing:
            continue
        (d / f).write_bytes(b"" if f in blank else b"x" * 32)
    return d


def test_g2_passes_a_complete_export(tmp_path):
    names = [f"{i:05d}.png" for i in range(5)]
    _make_channel(tmp_path, "mask", names)
    detail = gates.g2_completeness(str(tmp_path), {"mask": names}, 5)
    assert detail["mask"]["present"] == 5


def test_g2_red_on_a_truncated_directory(tmp_path):
    names = [f"{i:05d}.png" for i in range(5)]
    _make_channel(tmp_path, "mask", names, missing={names[3]})
    with pytest.raises(G2Completeness) as exc:
        gates.g2_completeness(str(tmp_path), {"mask": names}, 5)
    assert "4 frames present, expected 5" in str(exc.value)


def test_g2_red_on_a_zero_length_frame(tmp_path):
    """A frame file that exists but is empty is the failure that looks finished."""
    names = [f"{i:05d}.png" for i in range(5)]
    _make_channel(tmp_path, "mask", names, blank={names[2]})
    with pytest.raises(G2Completeness) as exc:
        gates.g2_completeness(str(tmp_path), {"mask": names}, 5)
    assert "zero-length" in str(exc.value)


def test_g2_red_on_a_missing_directory(tmp_path):
    names = [f"{i:05d}.png" for i in range(3)]
    with pytest.raises(G2Completeness):
        gates.g2_completeness(str(tmp_path), {"edge": names}, 3)


# ------------------------------------------------------------------ G4 goes red

def test_g4_passes_when_the_boxes_agree():
    deltas = gates.g4_bbox_sanity(0, (10, 20, 60, 90), (10, 20, 61, 90), 2, 128, 128)
    assert max(deltas) == 1


def test_g4_red_on_facets_actual_failure():
    """facet's version caught a mask 751 px wide in a 752 px frame when the mesh was
    388. That is this case."""
    with pytest.raises(G4BboxSanity) as exc:
        gates.g4_bbox_sanity(7, (0, 0, 750, 700), (180, 60, 568, 700), 2, 752, 752)
    assert exc.value.gate == "G4"
    assert "disagrees" in str(exc.value)


def test_g4_red_on_an_empty_mask():
    """The direction the superset check does not bound: a collapsed mask."""
    with pytest.raises(G4BboxSanity) as exc:
        gates.g4_bbox_sanity(3, None, (10, 10, 100, 100), 2, 128, 128)
    assert "mask is empty" in str(exc.value)


def test_g4_red_when_nothing_projects():
    with pytest.raises(G4BboxSanity):
        gates.g4_bbox_sanity(0, (10, 10, 20, 20), None, 2, 128, 128)


# ------------------------------------------------------------------ G5 goes red

def test_g5_passes_against_f20():
    from armature_core import openpose

    assert gates.g5_openpose_conformance(
        openpose.KEYPOINT_COUNT, openpose.LIMB_SEQ,
        openpose.KEYPOINT_COUNT, openpose.LIMB_SEQ,
    )


def test_g5_red_on_coco17():
    from armature_core import openpose

    with pytest.raises(G5ConventionConformance) as exc:
        gates.g5_openpose_conformance(17, openpose.LIMB_SEQ, 18, openpose.LIMB_SEQ)
    assert "keypoint count 17 != 18" in str(exc.value)


def test_g5_red_on_zero_indexing():
    """F20's limbSeq is 1-indexed. A from-scratch renderer that helpfully 'fixed' the
    off-by-one would produce exactly this, and it must not pass."""
    from armature_core import openpose

    zero_indexed = [[a - 1, b - 1] for a, b in openpose.LIMB_SEQ]
    with pytest.raises(G5ConventionConformance) as exc:
        gates.g5_openpose_conformance(18, zero_indexed, 18, openpose.LIMB_SEQ)
    assert "1-indexed" in str(exc.value) or "limb pair" in str(exc.value)


def test_g5_red_on_a_dropped_pair():
    from armature_core import openpose

    with pytest.raises(G5ConventionConformance):
        gates.g5_openpose_conformance(18, openpose.LIMB_SEQ[:-1], 18, openpose.LIMB_SEQ)
