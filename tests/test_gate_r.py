"""Gate R — the round trip that stands between our frames and a spent credit.

Every fixture here is written by asking the question CLAUDE.md asks of a fixture:
**what would this look like if the code were wrong in the specific way this check
exists to catch?** For Gate R that way is precise and is named in the spec — an
encoder that is luma-lossless and chroma-lossy. So the central test is not "does it
notice a difference", it is "does it notice a difference *that only exists in
chroma*", because that is the one a grayscale-only check would sail past.
"""

import numpy as np
import pytest

from armature_core.errors import GateFailure, GateRRoundTrip
from armature_core.gates import gate_r_round_trip


def _frames(n=4, h=8, w=6, rgb=True, seed=0):
    rng = np.random.default_rng(seed)
    shape = (n, h, w, 3) if rgb else (n, h, w)
    return list(rng.integers(0, 256, size=shape, dtype=np.uint8))


def _yuv420_round_trip(f):
    """An actual 4:2:0 round trip: RGB -> YUV, average U/V over 2x2, -> RGB.

    Written out properly because the first version of this helper faked it by
    spatially averaging the R and B *channels*, which is not what subsampling does —
    on an R=G=B image that fake corrupts what the real thing leaves untouched, and
    the gate correctly rejected it. The distinction is the whole point of the test:
    in YUV, a grayscale image has U = V = 0 everywhere, so averaging them is a no-op.
    """
    a = f.astype(np.float64)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    y = 0.299 * r + 0.587 * g + 0.114 * b
    u = 0.564 * (b - y)
    v = 0.713 * (r - y)

    for ch in (u, v):
        h, w = ch.shape
        for yy in range(0, h - h % 2, 2):
            for xx in range(0, w - w % 2, 2):
                ch[yy:yy + 2, xx:xx + 2] = ch[yy:yy + 2, xx:xx + 2].mean()

    out = np.stack(
        [y + 1.403 * v, y - 0.344 * u - 0.714 * v, y + 1.773 * u], axis=-1
    )
    return np.clip(np.rint(out), 0, 255).astype(np.uint8)


def test_identical_frames_pass_and_return_evidence():
    src = _frames()
    ev = gate_r_round_trip(src, [f.copy() for f in src])
    assert ev["verdict"] == "identical"
    assert ev["n_source"] == ev["n_decoded"] == 4


def test_a_short_decode_raises_before_anything_else():
    """The likeliest bridge failure: fewer frames out than in."""
    src = _frames(n=33)
    with pytest.raises(GateRRoundTrip) as exc:
        gate_r_round_trip(src, src[:32])
    assert "frame count changed" in str(exc.value)
    assert exc.value.evidence["n_source"] == 33
    assert exc.value.evidence["n_decoded"] == 32


def test_one_pixel_off_by_one_raises():
    """Not a tolerance. Lossless means lossless."""
    src = _frames()
    bad = [f.copy() for f in src]
    bad[2][3, 4, 1] = (int(bad[2][3, 4, 1]) + 1) % 256
    with pytest.raises(GateRRoundTrip) as exc:
        gate_r_round_trip(src, bad)
    assert exc.value.evidence["frames_differing"] == 1
    assert exc.value.evidence["detail"][0]["frame"] == 2


def test_chroma_only_corruption_is_caught_and_named_per_channel():
    """THE test. A 4:2:0 encoder leaves luma alone and wrecks colour difference.

    Constructed so that a naive luma-only or scalar-mean check would report ~0: the
    green channel is untouched (it dominates luma), while red and blue are shifted in
    opposite directions so even the *mean over all channels* cancels to zero. Only a
    per-channel comparison sees it — which is why the gate reports per channel.
    """
    src = _frames(n=3, h=16, w=16, seed=7)
    bad = []
    for f in src:
        g = f.copy().astype(np.int16)
        g[..., 0] = np.clip(g[..., 0] + 4, 0, 255)   # red up
        g[..., 2] = np.clip(g[..., 2] - 4, 0, 255)   # blue down
        bad.append(g.astype(np.uint8))

    # the trap this test exists to expose: signed mean over all channels ~ 0
    signed = np.mean(bad[0].astype(np.int16) - src[0].astype(np.int16))
    assert abs(signed) < 0.2

    with pytest.raises(GateRRoundTrip) as exc:
        gate_r_round_trip(src, bad)
    detail = exc.value.evidence["detail"][0]
    assert detail["per_channel_max_abs"][1] == 0          # green untouched
    assert detail["per_channel_max_abs"][0] == 4          # red moved
    assert detail["per_channel_max_abs"][2] == 4          # blue moved


def test_a_grayscale_sequence_cannot_demonstrate_chroma_safety():
    """Documents the gate's own blind spot rather than hiding it.

    Replicating gray into R=G=B and subsampling chroma is a no-op, so a grayscale
    round trip passes under a 4:2:0 encoder. The gate is correct to pass here; the
    point is that passing on grayscale is not evidence the bridge is lossless for the
    normal channel. This test is the reason the report must say which channel Gate R
    actually ran on.
    """
    gray = _frames(n=2, rgb=False, seed=3)
    rgb = [np.repeat(g[..., None], 3, axis=2) for g in gray]
    subsampled = [_yuv420_round_trip(f) for f in rgb]

    ev = gate_r_round_trip(rgb, subsampled)
    assert ev["verdict"] == "identical"

    # ...and the same simulation on true-RGB content DOES corrupt it, which is what
    # makes the pass above evidence about grayscale rather than about the simulation
    # being a no-op.
    colour = _frames(n=2, h=16, w=16, seed=11)
    with pytest.raises(GateRRoundTrip):
        gate_r_round_trip(colour, [_yuv420_round_trip(f) for f in colour])


def test_shape_change_raises():
    src = _frames(n=2, h=8, w=6)
    bad = [f[:, :4].copy() for f in src]
    with pytest.raises(GateRRoundTrip):
        gate_r_round_trip(src, bad)


def test_empty_input_raises_rather_than_passing_vacuously():
    """A check that cannot fail is not a check."""
    with pytest.raises(GateRRoundTrip) as exc:
        gate_r_round_trip([], [])
    assert "proves nothing" in str(exc.value)


def test_it_is_a_gate_failure_and_not_an_assertion():
    """CLAUDE.md: gates raise; an `assert` is deleted by -O."""
    assert issubclass(GateRRoundTrip, GateFailure)
    assert not issubclass(GateRRoundTrip, AssertionError)
    assert GateRRoundTrip.gate == "R"
