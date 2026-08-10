"""Gate B — did the control batch actually carry every frame.

The fixture question for this gate is unusually pointed, because the check that was
*first specified* for it could not fail. The halt ruling asked for "the output frame
count equals the submitted control frame count". `WanVaceToVideo` pads a short
`control_video` up to `length`, so the output is 33 frames whether the batch held 33
images or 1 — the quantity does not move when the defect is present.

So the tests below are written against the quantity that **does** move: the batch as
saved off the batch node. `test_the_rejected_check_could_not_fire` pins that reasoning
in executable form, so nobody re-derives the weaker check later.
"""

import pytest

from armature_core.errors import GateBBatching, GateFailure
from armature_core.gates import gate_b_batching


def test_intact_batch_passes():
    ev = gate_b_batching(33, 33)
    assert ev["verdict"] == "batch intact"
    assert ev["expected_frames"] == 33


def test_the_defect_this_gate_exists_for():
    """BatchImagesNode binds only the first auto-grow slot: 33 submitted, 1 arrives."""
    with pytest.raises(GateBBatching) as exc:
        gate_b_batching(33, 1)
    msg = str(exc.value)
    assert "carried 1 image(s), not 33" in msg
    assert "no error anywhere" in msg
    assert exc.value.evidence["observed_batch_images"] == 1


def test_a_larger_batch_also_raises():
    """The andon binds in the direction the invariant does not bound.

    A duplicated link gives more images than submitted. `<` would pass it; `!=` does
    not. Left as its own test because 'too many' is the case a hand-written check
    forgets.
    """
    with pytest.raises(GateBBatching) as exc:
        gate_b_batching(33, 66)
    assert "a link is bound twice" in str(exc.value)


def test_an_unobserved_batch_is_a_failure_not_a_pass():
    """`None` means the save node returned nothing to count. That is unverified, and
    unverified must not read as verified."""
    for bad in (None, "33", -1):
        with pytest.raises(GateBBatching) as exc:
            gate_b_batching(33, bad)
        assert "unverified rather than verified" in str(exc.value)


def test_the_rejected_check_could_not_fire():
    """Why Gate B does not count output video frames.

    Models the documented `WanVaceToVideo` behaviour: the control is truncated or
    padded to `length`, so output frames are `length` regardless of batch size. A gate
    written on that quantity returns the same number for the healthy and the broken
    case — 'a check that cannot fail is not a check'.
    """
    def output_frames(control_batch_size, length=33):
        return length  # padding/truncation makes this independent of the batch

    assert output_frames(33) == output_frames(1) == 33

    # the specified check passes in both worlds...
    for batch in (33, 1):
        assert output_frames(batch) == 33
    # ...while the implemented check separates them.
    gate_b_batching(33, 33)
    with pytest.raises(GateBBatching):
        gate_b_batching(33, 1)


def test_evidence_carries_through():
    with pytest.raises(GateBBatching) as exc:
        gate_b_batching(33, 1, evidence={"prompt_id": "abc", "arm": "A1a"})
    assert exc.value.evidence["prompt_id"] == "abc"
    assert exc.value.evidence["arm"] == "A1a"


def test_it_is_a_gate_failure_and_not_an_assertion():
    assert issubclass(GateBBatching, GateFailure)
    assert not issubclass(GateBBatching, AssertionError)
    assert GateBBatching.gate == "B"
