"""Gate DONOR — is this clip fit to be a baseline, before anything is lifted off it?

Amendment A3, 2026-08-12, and it exists because the 2026-08-11 probe produced a donor that
passed every gate the pipeline had. Detection fired on 65 of 65 frames. Mean visibility was
0.86. Every admission gate was green, the graph was clean, the seed was registered. And the
clip was a near-still figure whose feet were outside the frame on every frame — so the lift
that followed measured a solver against a body that barely moved and ankles that were never
observed, and the numbers went into a report as a baseline.

**The andon is on the direction the invariant does not bound.** Nothing else in this chain
asks whether the SOURCE is worth measuring. The detection gate asks whether the detector
fired; the route gates ask whether the graph was legal; the solver's round trip asks whether
the solver is self-consistent. All of them pass at their best on a static, cropped clip —
a still figure is the easiest thing a pose detector ever sees. This gate asks the question
none of them do, and it asks it BEFORE the lift, because a donor that fails is a recorded
take and not a baseline.

**Both thresholds are the amendment's, fixed in the spec before this clip existed.** They
are not tuned here and they are not tunable here: `THRESHOLDS` is the amendment's text in
code, and a caller that wants different numbers is writing a different experiment.

    motion   mean consecutive-frame absolute pixel difference >= 2.0 / 255
    framing  ankle landmarks inside the image on >= 80 % of frames

**Two readings of the framing clause are computed, and the STRICTER one gates.** "Ankle
landmarks inside the image on >= 80 % of frames" can mean each ankle separately or both at
once; both are reported, and the gate is on both-at-once. Choosing the stricter reading is
only honest if it is chosen before the numbers exist, which is why it is written here rather
than argued in the report.

**What this gate deliberately does NOT do.** It does not fold landmark *visibility* into the
verdict. A landmark can be placed inside the image by extrapolation onto a body whose feet
are cropped — the probe's own heels sat at 0.22 visibility while 100 % out of frame — so
visibility is carried beside the verdict as a diagnostic. Inventing a visibility threshold
here would be inventing a pass condition the spec did not calibrate, which is the error the
repo has already paid for once.
"""

import os

from .errors import GateFailure
from . import lift_solve as LS

TOOL_VERSION = "E09.A3"

#: Amendment A3 §2, verbatim in code. Changing a number here changes the experiment.
THRESHOLDS = {
    "min_mean_consecutive_frame_difference_over_255": 2.0,
    "min_fraction_of_frames_with_ankles_in_image": 0.80,
    "source": ("docs/experiments/E09-clean-chain-calibration.md, amendment A3 item 2, "
               "written 2026-08-12 before the clip it judges existed"),
}

ANKLES = ("left_ankle", "right_ankle")


class DonorGate(GateFailure):
    """A clip was about to be lifted that the amendment says is not a baseline."""

    gate = "DONOR"


def frame_paths(frames_dir):
    """The lossless frames, in temporal order.

    Numeric filenames only, sorted numerically. The probe's own near-miss is the reason
    this is a named function rather than an inline `sorted()`: `get_output` returns
    content-addressed names, and sorting THOSE alphabetically produces a random frame
    order that every count and every gate would have passed. Frames written by
    `fetch_run` are renumbered on the way in, so a name that is not a number is a frame
    whose order nobody established.
    """
    names = [f for f in os.listdir(frames_dir) if f.endswith(".png")]
    bad = [n for n in names if not os.path.splitext(n)[0].isdigit()]
    if bad:
        raise DonorGate(
            f"{len(bad)} frame(s) in {frames_dir} are not numerically named "
            f"({sorted(bad)[:5]}), so their temporal order is not established by this "
            f"directory. Sorting content-addressed names alphabetically produces a "
            f"shuffled clip that every other check passes",
            {"unnumbered": sorted(bad)[:20], "n_total": len(names)})
    return [os.path.join(frames_dir, n)
            for n in sorted(names, key=lambda n: int(os.path.splitext(n)[0]))]


def mean_consecutive_frame_difference(paths):
    """The clip's motion, in 0-255 units: mean over consecutive pairs of the mean
    absolute per-pixel, per-channel difference.

    Defined here rather than recomputed per session because the number has to be
    comparable to the probe's (0.7035 mean / 1.0839 max, results-array order). The alpha
    channel is dropped if present: a constant-opaque alpha would dilute the mean toward
    zero and make every clip look stiller than it is.
    """
    import numpy as np
    from PIL import Image

    if len(paths) < 2:
        raise DonorGate(f"a clip of {len(paths)} frame(s) has no consecutive pair to "
                        f"difference", {"n_frames": len(paths)})
    per_pair = []
    prev = None
    for p in paths:
        arr = np.asarray(Image.open(p).convert("RGB"), dtype=np.float64)
        if prev is not None:
            if arr.shape != prev.shape:
                raise DonorGate(
                    f"frame {os.path.basename(p)} is {arr.shape} where the previous frame "
                    f"is {prev.shape}; a clip whose frames change size has no per-pixel "
                    f"difference", {"frame": os.path.basename(p)})
            per_pair.append(float(np.abs(arr - prev).mean()))
        prev = arr
    return {
        "unit": "mean absolute difference per pixel per channel, 0-255",
        "n_frames": len(paths), "n_pairs": len(per_pair),
        "mean": float(sum(per_pair) / len(per_pair)),
        "max": max(per_pair), "min": min(per_pair),
        "per_pair": per_pair,
    }


def _inside(xy):
    """The detection gate's own out-of-frame test, in the positive direction."""
    x, y = float(xy[0]), float(xy[1])
    return 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0


def ankle_framing(rows, detect_evidence=None):
    """How often the ankles were inside the image — computed PER FRAME, not from rates.

    The aggregate per-landmark fractions the detection gate publishes cannot answer this
    clause on their own: knowing the left ankle is in frame 90 % of the time and the right
    90 % of the time bounds their co-occurrence only to somewhere between 80 % and 90 %,
    and gating on either end of that band would be gating on an artefact of the arithmetic
    rather than on the clip. So the per-frame landmarks are read directly and the
    co-occurrence is exact. The bounds are still reported, as a cross-check on the exact
    number rather than as a substitute for it.
    """
    idx = {a: LS.POSE_LANDMARKS.index(a) for a in ANKLES}
    fired = [r for r in rows if r.get("fired") and r.get("image")]
    if not fired:
        raise DonorGate("no frame carries image landmarks, so the framing clause cannot "
                        "be evaluated. A gate that cannot compute its own quantity halts "
                        "rather than passing", {"n_rows": len(rows)})
    per_frame = []
    for r in fired:
        flags = {a: _inside(r["image"][idx[a]]) for a in ANKLES}
        per_frame.append({"frame": r["frame"], **flags,
                          "both": all(flags.values()), "either": any(flags.values())})
    n = len(per_frame)
    per_ankle = {a: sum(1 for f in per_frame if f[a]) / n for a in ANKLES}
    both = sum(1 for f in per_frame if f["both"]) / n
    either = sum(1 for f in per_frame if f["either"]) / n
    out = {
        "n_frames_considered": n,
        "per_ankle_fraction_of_frames_in_image": per_ankle,
        "both_ankles_in_image": both,
        "either_ankle_in_image": either,
        "reading_that_gates": "both ankles in image, counted per frame",
        "why_the_stricter_reading": (
            "'ankle landmarks inside the image on >= 80% of frames' can be read per ankle "
            "or per frame; the per-frame reading is stricter and was chosen here BEFORE "
            "the clip existed, which is the only thing that makes choosing it honest"),
        "arithmetic_bounds_as_a_cross_check": {
            "lower": max(0.0, sum(per_ankle.values()) - 1.0),
            "upper": min(per_ankle.values()),
            "exact_lies_between": (max(0.0, sum(per_ankle.values()) - 1.0)
                                   <= both <= min(per_ankle.values()) + 1e-9)},
        "visibility_diagnostic_not_gated": {
            a: ((detect_evidence or {}).get("per_landmark_mean_visibility") or {}).get(a)
            for a in ANKLES},
        "why_visibility_is_not_gated": (
            "a landmark can be placed inside the image by extrapolation onto a cropped "
            "body — the probe's heels read 0.22 visibility while 100% out of frame. A "
            "visibility threshold is one this spec never calibrated, so it is reported "
            "and not applied"),
        "frames": per_frame,
    }
    if not out["arithmetic_bounds_as_a_cross_check"]["exact_lies_between"]:
        raise DonorGate(
            "the exact both-ankles fraction falls outside the bounds its own per-ankle "
            "rates allow, which means the two were computed off different populations",
            {k: v for k, v in out.items() if k != "frames"})
    return out


def gate_donor(motion, framing, thresholds=None):
    """ANDON. Raises unless BOTH of A3's clauses hold. Returns the evidence when they do."""
    th = dict(THRESHOLDS if thresholds is None else thresholds)
    m_min = th["min_mean_consecutive_frame_difference_over_255"]
    f_min = th["min_fraction_of_frames_with_ankles_in_image"]
    m = motion["mean"]
    f = framing["both_ankles_in_image"]

    ev = {
        "gate": "DONOR", "tool_version": TOOL_VERSION, "thresholds": th,
        "motion": {"measured_mean_over_255": m, "threshold": m_min, "passes": m >= m_min},
        "framing": {"measured_fraction": f, "threshold": f_min, "passes": f >= f_min,
                    "detail": {k: v for k, v in framing.items() if k != "frames"}},
        "motion_detail": {k: v for k, v in motion.items() if k != "per_pair"},
    }
    failed = []
    if m < m_min:
        failed.append(f"motion: mean consecutive-frame difference {m:.4f}/255 is below "
                      f"the {m_min}/255 the amendment requires")
    if f < f_min:
        failed.append(f"framing: ankles inside the image on at most {f:.1%} of frames, "
                      f"below the {f_min:.0%} the amendment requires "
                      f"(left {framing['per_ankle_fraction_of_frames_in_image']['left_ankle']:.1%}, "
                      f"right {framing['per_ankle_fraction_of_frames_in_image']['right_ankle']:.1%})")
    if failed:
        ev["verdict"] = "FAILED"
        raise DonorGate(
            "; ".join(failed) + ". A donor failing this gate is a recorded take, not a "
            "baseline: nothing is lifted off it, and A3 item 4 governs what happens next",
            ev)
    ev["verdict"] = (f"mean consecutive-frame difference {m:.4f}/255 (>= {m_min}) and "
                     f"ankles in image on at least {f:.1%} of frames (>= {f_min:.0%})")
    return ev


def _landmark_names_are_the_ones_this_module_assumes():
    """Guard against the landmark table being renamed out from under the ankle clause."""
    return all(a in LS.POSE_LANDMARKS for a in ANKLES)
