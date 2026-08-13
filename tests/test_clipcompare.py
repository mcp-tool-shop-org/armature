"""The decode comparison's instruments — E13's re-arm, Stage 0.

Three separable questions about a round trip through an encoder, and each fixture asks what
the answer would look like if the code were wrong in the specific way the check exists to
catch:

* **count** — a clip carrying 27 frames where 81 were submitted must stop the comparison,
  not report 27 rows of per-frame numbers that compare different pictures;
* **order** — a decoded clip whose thirds are swapped must read as displaced even though
  its count, its fps and every build-path gate are correct. This is the fault a cascade
  adds and the reason `order_check` exists at all;
* **fidelity** — the gradient split must actually separate edges from flats, or the
  "structured at edges" reading is a number with no instrument behind it.
"""

import numpy as np
import pytest

from armature_core import clipcompare as CC


def _frames(n=9, h=24, w=32, seed=5):
    """Frames with real structure — an edge that moves — so a shuffle is detectable and
    the gradient split has something to separate."""
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        f = np.full((h, w, 3), 40, dtype=np.uint8)
        f[:, (i * 3) % w:((i * 3) % w) + 6, :] = 220        # a moving bright bar
        f = np.clip(f.astype(np.int16) + rng.integers(-2, 3, f.shape), 0, 255)
        out.append(f.astype(np.uint8))
    return out


# ------------------------------------------------------------------ fidelity


def test_an_identical_frame_reads_identical_and_zero():
    f = _frames(1)[0]
    ev = CC.frame_fidelity(f, f)
    assert ev["identical"] is True
    assert ev["mean_abs"] == 0.0 and ev["max_abs"] == 0.0
    assert ev["frac_differing"] == 0.0


def test_a_one_level_shift_is_not_identical_and_reports_its_size():
    f = _frames(1)[0]
    g = np.clip(f.astype(np.int16) + 1, 0, 255).astype(np.uint8)
    ev = CC.frame_fidelity(f, g)
    assert ev["identical"] is False
    assert 0.9 <= ev["mean_abs"] <= 1.1
    assert ev["frac_differing"] > 0.99


def test_a_shape_mismatch_raises_rather_than_broadcasting():
    a, b = _frames(1)[0], np.zeros((8, 8, 3), dtype=np.uint8)
    with pytest.raises(ValueError):
        CC.frame_fidelity(a, b)


def test_the_gradient_split_actually_separates_edges_from_flats():
    """Error placed ONLY at the bar's edges must read high in the top-gradient band and
    ~0 in the flat band. If the split reported the same number in both, the 'structured at
    edges' reading would be an artefact of the instrument rather than of the encoder."""
    src = _frames(1)[0]
    dec = src.astype(np.int16).copy()
    lum = src.astype(np.float64).mean(axis=-1)
    gy, gx = np.gradient(lum)
    edge = np.hypot(gy, gx) > 20
    dec[edge] += 30
    ev = CC.gradient_split(src, np.clip(dec, 0, 255).astype(np.uint8))
    assert ev["mean_err_top_gradient"] > 5 * max(ev["mean_err_flat"], 0.01)


def test_uniform_error_reads_the_same_in_both_bands():
    """The negative control for the test above: an encoder that spread its error evenly
    must NOT read as structured. Without this, the split would 'find' structure anywhere."""
    src = _frames(1)[0]
    dec = np.clip(src.astype(np.int16) + 4, 0, 255).astype(np.uint8)
    ev = CC.gradient_split(src, dec)
    assert abs(ev["mean_err_top_gradient"] - ev["mean_err_flat"]) < 0.5


# ------------------------------------------------------------------ order


def test_an_unshuffled_clip_reads_order_preserved():
    fr = _frames(9)
    ev = CC.order_check(fr, [f.copy() for f in fr], step=1)
    assert ev["order_preserved"] is True
    assert ev["n_on_diagonal"] == 9 and ev["n_displaced"] == 0


def test_encoder_noise_does_not_break_the_order_finding():
    """The real case: decoded frames are never bit-exact. Order must survive that."""
    fr = _frames(9)
    rng = np.random.default_rng(11)
    dec = [np.clip(f.astype(np.int16) + rng.integers(-3, 4, f.shape), 0, 255)
           .astype(np.uint8) for f in fr]
    ev = CC.order_check(fr, dec, step=1)
    assert ev["order_preserved"] is True
    assert ev["min_margin"] > 0


def test_two_groups_swapped_reads_as_displaced():
    """The cascade's own failure: three groups of three, the first two swapped. Nine
    frames, right count, right fps, every build gate green, the clip scrambled."""
    fr = _frames(9)
    dec = fr[3:6] + fr[0:3] + fr[6:9]
    ev = CC.order_check(fr, dec, step=1)
    assert ev["order_preserved"] is False
    assert ev["n_displaced"] == 6
    assert (0, 3) in ev["displaced"]


def test_a_single_transposed_pair_is_caught():
    fr = _frames(9)
    dec = list(fr)
    dec[4], dec[5] = dec[5], dec[4]
    ev = CC.order_check(fr, dec, step=1)
    assert ev["order_preserved"] is False
    assert ev["n_displaced"] == 2


def test_a_length_mismatch_raises_rather_than_comparing_a_prefix():
    fr = _frames(9)
    with pytest.raises(ValueError):
        CC.order_check(fr, fr[:8], step=1)


def test_the_margin_is_reported_so_a_weakly_separated_finding_says_so():
    """Nine near-identical frames: order may still land on the diagonal, but the margin
    must be small enough that the report cannot present it as a clean separation."""
    base = _frames(1)[0]
    rng = np.random.default_rng(3)
    fr = [np.clip(base.astype(np.int16) + rng.integers(-1, 2, base.shape), 0, 255)
          .astype(np.uint8) for _ in range(9)]
    ev = CC.order_check(fr, [f.copy() for f in fr], step=1)
    assert ev["min_margin"] < 1.0


def test_downsampling_preserves_gross_layout():
    f = _frames(1, h=64, w=64)[0]
    d = CC.downsample(f, step=8)
    assert d.shape == (8, 8, 3)
