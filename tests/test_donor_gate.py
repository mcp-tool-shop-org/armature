"""Gate DONOR, checked against the run that made it necessary.

The strongest fixture available is the 2026-08-11 probe itself: a clip that passed every
other gate in this pipeline and was a near-still figure with its feet outside the frame. If
this gate does not fire on that clip, it does not exist. Those frames are banked under
`outputs/E09/b2-probe/`, so the check is run against the real thing rather than a mock of
what the real thing was believed to be.

The synthetic fixtures cover the directions the probe does not: a clip that moves but is
cropped, a clip framed correctly but static, and a clip that is fine — because a gate that
has only ever seen one failure cannot be shown to discriminate.
"""

import json
import os

import numpy as np
import pytest

from conftest import TOOLS, REPO  # noqa: F401
from armature_core import donor_gate as DG
from armature_core import lift_solve as LS


PROBE = os.path.join(REPO, "outputs", "E09", "b2-probe")
PROBE_MEASURE = os.path.join(REPO, "outputs", "E09", "b2-measure", "measurement.json")

needs_probe = pytest.mark.skipif(
    not os.path.isdir(os.path.join(PROBE, "lossless")),
    reason="the 2026-08-11 probe frames are not present; outputs/ is out of git")


def _rows(ankle_xy, n=10, fired=True):
    """Detection rows with both ankles at a given image position on every frame."""
    rows = []
    for i in range(n):
        image = [(0.5, 0.5)] * 33
        for a in ("left_ankle", "right_ankle"):
            image[LS.POSE_LANDMARKS.index(a)] = ankle_xy
        rows.append({"frame": i, "fired": fired, "image": image})
    return rows


def _clip(tmp_path, n=6, step=0.0, size=(8, 8)):
    """A synthetic clip whose per-frame difference is exactly `step` in 0-255 units."""
    d = tmp_path / "lossless"
    d.mkdir(parents=True, exist_ok=True)
    from PIL import Image
    for i in range(n):
        arr = np.full((size[1], size[0], 3), i * step, dtype=np.uint8)
        Image.fromarray(arr).save(d / f"{i:05d}.png")
    return str(d)


# --------------------------------------------------------------------- the thresholds

def test_the_thresholds_are_the_amendments_and_name_where_they_came_from():
    assert DG.THRESHOLDS["min_mean_consecutive_frame_difference_over_255"] == 2.0
    assert DG.THRESHOLDS["min_fraction_of_frames_with_ankles_in_image"] == 0.80
    assert "A3" in DG.THRESHOLDS["source"]


def test_the_landmark_names_this_module_assumes_still_exist():
    assert DG._landmark_names_are_the_ones_this_module_assumes()


# ------------------------------------------------------------ the clip that made it necessary

@needs_probe
def test_it_fires_on_the_probe_that_made_it_necessary():
    """The whole point. The probe passed DETECT on 65/65 frames and was not a baseline."""
    motion = DG.mean_consecutive_frame_difference(
        DG.frame_paths(os.path.join(PROBE, "lossless")))
    with pytest.raises(DG.DonorGate) as e:
        DG.gate_donor(motion, DG.ankle_framing(_rows((0.5, 1.4))))
    assert "motion" in str(e.value) and "framing" in str(e.value)


@needs_probe
def test_the_motion_statistic_is_the_probes_statistic_to_the_bit():
    """The number this gate reads has to be the SAME number the probe was described by, or
    2.0176 and 0.7035 are not comparable and the A3 report is quoting two different things.

    The committed implementation accumulates in float64 and lands 1.3e-9 away from the
    0.7034705802798271 recorded last session. That residual was MEASURED, not assumed:
    re-running the identical arithmetic in float32 reproduces the recorded mean and max
    bit-for-bit, so last session's ad-hoc pass accumulated in float32 and the statistic
    itself is unchanged. Both are pinned here — the exact float32 identity is what proves
    it is the same statistic, and the float64 agreement is what shows the choice of
    precision cannot move a gate whose threshold is 2.0.
    """
    import numpy as np
    from PIL import Image

    recorded = json.load(open(os.path.join(PROBE, "frame_order_evidence.json"),
                              encoding="utf-8"))["results_array_order"]
    paths = DG.frame_paths(os.path.join(PROBE, "lossless"))

    got = DG.mean_consecutive_frame_difference(paths)
    assert got["mean"] == pytest.approx(recorded["mean"], rel=1e-6)
    assert got["max"] == pytest.approx(recorded["max"], rel=1e-6)
    assert abs(got["mean"] - recorded["mean"]) < 1e-8

    prev, per_pair = None, []
    for p in paths:
        arr = np.asarray(Image.open(p).convert("RGB"), dtype=np.float32)
        if prev is not None:
            per_pair.append(float(np.abs(arr - prev).mean()))
        prev = arr
    assert sum(per_pair) / len(per_pair) == recorded["mean"]      # bit-for-bit
    assert max(per_pair) == recorded["max"]


@needs_probe
def test_the_probes_measured_ankle_framing_is_what_the_gate_would_have_read():
    """0% in-image on both ankles, from the probe's own measurement record."""
    m = json.load(open(PROBE_MEASURE, encoding="utf-8"))
    outside = m["gates"]["DETECT"]["fraction_of_frames_landmark_lies_outside_the_image"]
    assert outside["left_ankle"] == 1.0 and outside["right_ankle"] == 1.0


# ----------------------------------------------------------------- discrimination

def test_it_passes_a_clip_that_moves_enough_and_is_framed(tmp_path):
    frames = _clip(tmp_path, n=6, step=10)
    ev = DG.gate_donor(DG.mean_consecutive_frame_difference(DG.frame_paths(frames)),
                       DG.ankle_framing(_rows((0.5, 0.9))))
    assert ev["motion"]["passes"] and ev["framing"]["passes"]
    assert "FAILED" not in ev["verdict"]


def test_it_fires_on_a_clip_that_moves_but_is_cropped(tmp_path):
    frames = _clip(tmp_path, n=6, step=10)
    with pytest.raises(DG.DonorGate) as e:
        DG.gate_donor(DG.mean_consecutive_frame_difference(DG.frame_paths(frames)),
                      DG.ankle_framing(_rows((0.5, 1.2))))
    assert "framing" in str(e.value) and "motion" not in str(e.value)


def test_it_fires_on_a_clip_that_is_framed_but_static(tmp_path):
    frames = _clip(tmp_path, n=6, step=0)
    with pytest.raises(DG.DonorGate) as e:
        DG.gate_donor(DG.mean_consecutive_frame_difference(DG.frame_paths(frames)),
                      DG.ankle_framing(_rows((0.5, 0.9))))
    assert "motion" in str(e.value) and "framing" not in str(e.value)


def test_the_motion_threshold_bites_at_the_stated_number(tmp_path):
    """Just under fails, just over passes. A gate whose boundary is somewhere else than
    its documented number is a gate nobody can predict."""
    below = _clip(tmp_path / "a", n=6, step=1)      # 1.0/255 per pair
    (tmp_path / "a").mkdir(exist_ok=True)
    with pytest.raises(DG.DonorGate):
        DG.gate_donor(DG.mean_consecutive_frame_difference(DG.frame_paths(below)),
                      DG.ankle_framing(_rows((0.5, 0.9))))
    above = _clip(tmp_path / "b", n=6, step=3)      # 3.0/255 per pair
    DG.gate_donor(DG.mean_consecutive_frame_difference(DG.frame_paths(above)),
                  DG.ankle_framing(_rows((0.5, 0.9))))


def test_the_framing_threshold_bites_at_the_stated_number():
    """8 of 10 frames in-image passes; 7 of 10 fails."""
    def rows_with(n_in, n=10):
        rows = _rows((0.5, 0.9), n=n)
        for i in range(n_in, n):
            for a in ("left_ankle", "right_ankle"):
                rows[i]["image"][LS.POSE_LANDMARKS.index(a)] = (0.5, 1.3)
        return rows
    good = _clip_free_motion()
    DG.gate_donor(good, DG.ankle_framing(rows_with(8)))
    with pytest.raises(DG.DonorGate):
        DG.gate_donor(good, DG.ankle_framing(rows_with(7)))


def _clip_free_motion():
    """A motion record that comfortably passes, so framing is the only variable."""
    return {"unit": "test", "n_frames": 6, "n_pairs": 5, "mean": 9.0, "max": 9.0,
            "min": 9.0, "per_pair": [9.0] * 5}


# ------------------------------------------------------------------ the two readings

def test_one_ankle_in_frame_is_not_enough():
    """The per-frame reading is the one that gates. A clip where the left ankle is always
    in and the right always out reads 50% per-landmark and 0% per-frame; the looser
    reading would let it through."""
    rows = _rows((0.5, 0.9), n=10)
    for r in rows:
        r["image"][LS.POSE_LANDMARKS.index("right_ankle")] = (0.5, 1.3)
    f = DG.ankle_framing(rows)
    assert f["per_ankle_fraction_of_frames_in_image"]["left_ankle"] == 1.0
    assert f["per_ankle_fraction_of_frames_in_image"]["right_ankle"] == 0.0
    assert f["both_ankles_in_image"] == 0.0
    assert f["either_ankle_in_image"] == 1.0
    with pytest.raises(DG.DonorGate):
        DG.gate_donor(_clip_free_motion(), f)


def test_the_exact_count_is_reported_not_an_arithmetic_bound():
    """Alternating ankles: each is in-image on half the frames, and they never coincide.
    The per-landmark rates alone would allow anything from 0% to 50%; only counting
    per frame gives the truth, which is 0%."""
    rows = _rows((0.5, 0.9), n=10)
    for i, r in enumerate(rows):
        out = "left_ankle" if i % 2 == 0 else "right_ankle"
        r["image"][LS.POSE_LANDMARKS.index(out)] = (0.5, 1.3)
    f = DG.ankle_framing(rows)
    assert f["per_ankle_fraction_of_frames_in_image"] == {"left_ankle": 0.5,
                                                          "right_ankle": 0.5}
    assert f["both_ankles_in_image"] == 0.0
    b = f["arithmetic_bounds_as_a_cross_check"]
    assert b["lower"] == 0.0 and b["upper"] == 0.5 and b["exact_lies_between"]


def test_a_landmark_off_the_left_or_right_edge_counts_as_outside_too():
    """Cropping is not only vertical. A dancer who steps out of a narrow frame sideways
    is as unobserved as one whose feet are below the bottom edge."""
    rows = _rows((1.4, 0.5), n=10)
    assert DG.ankle_framing(rows)["both_ankles_in_image"] == 0.0


# ---------------------------------------------------------------- refusals, not guesses

def test_frames_that_are_not_numerically_named_halt(tmp_path):
    """Content-addressed filenames sorted alphabetically are a shuffled clip, and E09's
    first download did exactly that."""
    d = tmp_path / "lossless"
    d.mkdir(parents=True, exist_ok=True)
    from PIL import Image
    for name in ("00f09b64", "0211117d", "9d7a4fcf"):
        Image.fromarray(np.zeros((4, 4, 3), dtype=np.uint8)).save(d / f"{name}.png")
    with pytest.raises(DG.DonorGate) as e:
        DG.frame_paths(str(d))
    assert "temporal order" in str(e.value)


def test_a_single_frame_has_no_pair_to_difference(tmp_path):
    frames = _clip(tmp_path, n=1, step=0)
    with pytest.raises(DG.DonorGate):
        DG.mean_consecutive_frame_difference(DG.frame_paths(frames))


def test_frames_of_different_sizes_halt(tmp_path):
    d = tmp_path / "lossless"
    d.mkdir(parents=True, exist_ok=True)
    from PIL import Image
    Image.fromarray(np.zeros((8, 8, 3), dtype=np.uint8)).save(d / "00000.png")
    Image.fromarray(np.zeros((9, 9, 3), dtype=np.uint8)).save(d / "00001.png")
    with pytest.raises(DG.DonorGate):
        DG.mean_consecutive_frame_difference(DG.frame_paths(str(d)))


def test_no_fired_frames_halts_rather_than_passing():
    with pytest.raises(DG.DonorGate):
        DG.ankle_framing(_rows((0.5, 0.9), fired=False))


def test_the_gate_is_a_raise_and_not_an_assert():
    """CLAUDE.md: an `assert` is deleted by -O. This gate must survive PYTHONOPTIMIZE."""
    src = open(os.path.join(TOOLS, "armature_core", "donor_gate.py"),
               encoding="utf-8").read()
    body = "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))
    assert "assert " not in body
    assert "raise DonorGate" in body


def test_the_lift_tool_calls_the_gate_before_it_solves_anything():
    """Wiring, checked as wiring. A gate that exists in a module nobody calls is not a
    gate, and the order matters: after DETECT, before the first solve_frame."""
    src = open(os.path.join(TOOLS, "lift_clip.py"), encoding="utf-8").read()
    assert "DG.gate_donor(" in src
    assert src.index("DG.gate_donor(") > src.index("gate = gate_detection(rows)")
    assert src.index("DG.gate_donor(") < src.index("LS.solve_frame(")
    assert "skip" not in src[src.index("DG.gate_donor("):src.index("DG.gate_donor(") + 400]


# =====================================================================================
# W3 amend — the door in the andon, and the denominator that was not the clip.
# =====================================================================================


def test_gate_donor_takes_no_thresholds_argument():
    """The module's own docstring rules that the thresholds "are not tuned here and they
    are not tunable here". The signature said otherwise: `gate_donor(motion, framing,
    thresholds=None)` used the caller's dict verbatim, so
    `thresholds={'min_mean_consecutive_frame_difference_over_255': 0,
    'min_fraction_of_frames_with_ankles_in_image': 0}` returned a green verdict on a
    dead-still, ankles-never-in-frame clip — a skip flag inside an andon, which
    CLAUDE.md forbids outright. A test that needs a different number monkeypatches
    `DG.THRESHOLDS`; a different experiment writes a different module constant with its
    own amendment reference."""
    import inspect

    params = list(inspect.signature(DG.gate_donor).parameters)
    assert params == ["motion", "framing"]


def test_the_2026_08_11_failure_cannot_be_argued_past_by_a_caller():
    """The exact call the old signature admitted, on the exact clip the gate exists for."""
    still = {"unit": "test", "n_frames": 6, "n_pairs": 5, "mean": 0.0, "max": 0.0,
             "min": 0.0, "per_pair": [0.0] * 5}
    cropped = DG.ankle_framing(_rows((0.5, 1.4)))
    with pytest.raises(DG.DonorGate):
        DG.gate_donor(still, cropped)
    with pytest.raises(TypeError):
        DG.gate_donor(still, cropped,
                      {"min_mean_consecutive_frame_difference_over_255": 0.0,
                       "min_fraction_of_frames_with_ankles_in_image": 0.0})


def test_a_monkeypatched_constant_is_how_a_fixture_moves_a_threshold(monkeypatch):
    """The replacement door, and it is the module's own constant rather than a
    parameter: it cannot be reached from a production call site."""
    monkeypatch.setattr(DG, "THRESHOLDS", dict(DG.THRESHOLDS,
                                               min_mean_consecutive_frame_difference_over_255=0.0))
    ev = DG.gate_donor({"unit": "test", "n_frames": 6, "n_pairs": 5, "mean": 0.0,
                        "max": 0.0, "min": 0.0, "per_pair": [0.0] * 5},
                       DG.ankle_framing(_rows((0.5, 0.9))))
    assert ev["thresholds"]["min_mean_consecutive_frame_difference_over_255"] == 0.0


# --- the framing denominator is the clip, not the frames the detector liked ---------


def _mostly_unfired(n=65, n_fired=3):
    """A 65-frame clip the detector fired on 3 times, perfectly framed on those 3."""
    rows = _rows((0.5, 0.5), n=n)
    for i, r in enumerate(rows):
        r["fired"] = i < n_fired
        if not r["fired"]:
            r["image"] = None
    return rows


def test_a_clip_observed_on_three_of_sixty_five_frames_fails_the_framing_clause():
    """The amendment's clause is "ankle landmarks inside the image on >= 80 % of
    frames" — a population of CLIP frames. Every fraction was computed over
    `[r for r in rows if r.get('fired') and r.get('image')]`, so 3 perfect frames out of
    65 read 1.0 and the clause passed; `n_frames_considered=3` was honest and gated
    nothing. A donor whose ankles were observed on a small minority of frames was
    admitted as a baseline and the lift numbers were quoted against it."""
    f = DG.ankle_framing(_mostly_unfired())
    assert f["n_frames_considered"] == 65
    assert f["n_frames_detector_fired"] == 3
    assert f["both_ankles_in_image"] == pytest.approx(3 / 65)
    with pytest.raises(DG.DonorGate) as exc:
        DG.gate_donor(_clip_free_motion(), f)
    assert "framing" in str(exc.value)


def test_the_fired_only_fraction_is_kept_beside_it_as_a_diagnostic():
    f = DG.ankle_framing(_mostly_unfired())
    assert f["both_ankles_in_image_over_fired_frames_only"] == 1.0
    assert "diagnostic" in f["why_the_fired_only_fraction_is_not_the_gate"].lower()


def test_the_cross_check_still_holds_on_the_new_population():
    """The per-ankle rates and the exact both-ankles fraction must be computed off the
    SAME population or the bounds check raises — which is what it is for."""
    f = DG.ankle_framing(_mostly_unfired())
    assert f["per_ankle_fraction_of_frames_in_image"] == {
        "left_ankle": pytest.approx(3 / 65), "right_ankle": pytest.approx(3 / 65)}
    assert f["arithmetic_bounds_as_a_cross_check"]["exact_lies_between"]


def test_a_fully_fired_clip_is_unchanged():
    """The other direction: on a clip the detector fired on everywhere, the two
    denominators are the same number and no reading moves."""
    f = DG.ankle_framing(_rows((0.5, 0.9), n=10))
    assert f["n_frames_considered"] == f["n_frames_detector_fired"] == 10
    assert f["both_ankles_in_image"] == 1.0
