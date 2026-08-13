"""The re-lift comparison's andon, against the ways it could agree about nothing.

Every E11 and E12 generation was conditioned on a start frame rendered from an E09 GLB that
has sat on disk since it was lifted. This check asks whether that file is still what its
recorded inputs produce. The failure it exists to catch is silent by construction: a stale
or drifted pin loads, renders, gates and generates exactly like a fresh one.
"""

import pytest

from armature_core import glb as CR


def test_identical_clips_pass_and_report_their_length():
    sigs = [f"sig{i}" for i in range(65)]
    ev = CR.compare_signatures(list(sigs), list(sigs), label="b2")
    assert ev["n_frames_compared"] == 65
    assert ev["n_frames_differing"] == 0
    assert "all 65 frames" in ev["verdict"]


def test_a_divergence_after_the_first_frame_is_caught():
    """THE clause. A lift shares its rest pose with the file it was solved from, so frame 0
    agrees even when the performance does not. A check that compared only the first frame
    would pass on every stale pin there is."""
    a = [f"sig{i}" for i in range(65)]
    b = list(a)
    b[40] = "different"
    with pytest.raises(CR.ReliftMismatch) as exc:
        CR.compare_signatures(a, b)
    assert exc.value.evidence["first_divergent_frame"] == 40
    assert exc.value.evidence["n_frames_differing"] == 1
    assert "unrecorded ancestor" in str(exc.value)


def test_every_differing_frame_is_counted_not_just_the_first():
    a = [f"sig{i}" for i in range(10)]
    b = ["x"] * 10
    with pytest.raises(CR.ReliftMismatch) as exc:
        CR.compare_signatures(a, b)
    assert exc.value.evidence["n_frames_differing"] == 10
    assert exc.value.evidence["first_divergent_frame"] == 0


def test_a_frame_count_mismatch_halts_even_when_the_shared_frames_agree():
    """A lift that dropped a frame is not the same performance, however well the frames it
    kept agree — and `zip` would silently compare only the shorter run."""
    a = [f"sig{i}" for i in range(65)]
    with pytest.raises(CR.ReliftMismatch) as exc:
        CR.compare_signatures(a, a[:64])
    assert "frame counts differ" in str(exc.value)


@pytest.mark.parametrize("a,b", [([], []), (["s"], []), ([], ["s"])])
def test_an_empty_comparison_halts_rather_than_agreeing_about_nothing(a, b):
    """A check that cannot fail is not a check: two empty lists are equal, and reporting
    that as a match would certify a pin nobody compared."""
    with pytest.raises(CR.ReliftMismatch) as exc:
        CR.compare_signatures(a, b)
    assert "nothing to compare" in str(exc.value)


def test_the_evidence_carries_the_signatures_it_disagreed_on():
    """A gate that hides what it saw makes the next reader re-run the comparison."""
    with pytest.raises(CR.ReliftMismatch) as exc:
        CR.compare_signatures(["a", "b"], ["a", "c"], label="b2-a3")
    ev = exc.value.evidence
    assert ev["label"] == "b2-a3"
    assert (ev["pinned_signature"], ev["fresh_signature"]) == ("b", "c")
