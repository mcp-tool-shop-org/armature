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

**"of frames" means of the CLIP's frames.** Corrected 2026-09-03: every fraction was
computed over the frames the detector fired on, so 3 perfect frames out of 65 read 1.0 and
the clause passed on a clip whose ankles were observed on 5 % of it. A frame nothing
observed is not a frame the ankles were seen inside. The fired-only fraction rides the
evidence beside the gating one, as a diagnostic.

**What this gate deliberately does NOT do.** It does not fold landmark *visibility* into the
verdict. A landmark can be placed inside the image by extrapolation onto a body whose feet
are cropped — the probe's own heels sat at 0.22 visibility while 100 % out of frame — so
visibility is carried beside the verdict as a diagnostic. Inventing a visibility threshold
here would be inventing a pass condition the spec did not calibrate, which is the error the
repo has already paid for once.
"""

import os

from .errors import GateFailure
from .parts import require_finite
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

    ⚠ **The suffix test was case SENSITIVE, and it silently dropped this gate's own
    andon's population.** Measured 2026-09-04 on a directory holding 0.png, 1.PNG and
    2.png: this function returned ['0.png', '2.png'] with no complaint, so
    `mean_consecutive_frame_difference` differenced frame 0 against frame 2 as a
    CONSECUTIVE pair and the clip's motion mean — the number `gate_donor` compares
    against `THRESHOLDS` — was computed over the wrong pairs. On a directory holding only
    0.PNG and notanumber.PNG it returned [] and the unnumbered-name refusal below never
    fired, because the name it exists to catch was filtered out before it was examined.

    The producer states the contract explicitly: `fetch_run.verify_downloads` was made
    case-insensitive at the wave-8 merge and its comment (fetch_run.py:250) says its
    consumers `encode_control.py:126` and `invert_frames.py:70` use
    `n.lower().endswith('.png')` and that "the andon and its consumers share one"
    population rule. This is the gate that decides whether a clip may be a baseline at
    all, so it reads the population the same way — and the RAW directory count rides in
    the evidence beside `n_total`, so a dropped file is visible rather than inferred.
    """
    listing = os.listdir(frames_dir)
    names = [f for f in listing if f.lower().endswith(".png")]
    bad = [n for n in names if not os.path.splitext(n)[0].isdigit()]
    if bad:
        raise DonorGate(
            f"{len(bad)} frame(s) in {frames_dir} are not numerically named "
            f"({sorted(bad)[:5]}), so their temporal order is not established by this "
            f"directory. Sorting content-addressed names alphabetically produces a "
            f"shuffled clip that every other check passes",
            {"gate": "DONOR", "andon": "DonorGate", "clause": "frames_not_numerically_named",
             "unnumbered": sorted(bad)[:20], "n_total": len(names),
             "n_in_directory": len(listing),
             "n_not_png": len(listing) - len(names)})
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
                        f"difference",
                        {"gate": "DONOR", "andon": "DonorGate",
                         "clause": "clip_has_no_consecutive_pair",
                         "n_frames": len(paths)})
    per_pair = []
    prev = None
    for p in paths:
        arr = np.asarray(Image.open(p).convert("RGB"), dtype=np.float64)
        if prev is not None:
            if arr.shape != prev.shape:
                raise DonorGate(
                    f"frame {os.path.basename(p)} is {arr.shape} where the previous frame "
                    f"is {prev.shape}; a clip whose frames change size has no per-pixel "
                    f"difference",
                    {"gate": "DONOR", "andon": "DonorGate",
                     "clause": "frame_sizes_differ",
                     "frame": os.path.basename(p)})
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


def _readable_landmark_row(r, idx, required):
    """Gate DONOR's refusal for a detection row whose `image` list it cannot index.

    ⚠ **The gate guarded its EMPTY population and never the SHAPE of a row it does
    read.** `flags = {a: (observed and _inside(r["image"][idx[a]])) for a in ANKLES}` with
    `idx = {'left_ankle': 27, 'right_ankle': 28}` from `LS.POSE_LANDMARKS` (33 entries),
    and `_inside` then does `float(xy[0]), float(xy[1])`. Measured 2026-09-04 in this
    worktree: a row whose `image` list carries 17 landmarks (a COCO-topology record)
    raised `IndexError: list index out of range`; a 33-entry list with `image[27] = None`
    raised `TypeError: 'NoneType' object is not subscriptable`; a list of
    `{'x':..,'y':..}` dicts raised `KeyError: 0`.

    None of the three is an `ArmatureError`, so `lift_clip`'s halt handler
    (`detail = getattr(exc, "evidence", None)`) classified a deliberate-shaped refusal
    from this gate as an unhandled crash and wrote a halt line naming no gate and carrying
    no receipt — the exact exit `SubjectExtentError`, `rig_gates._require_numeric` and
    `_readable_node` were each written to close in their own modules this year. Gate DONOR
    is the andon that decides whether a clip may be a baseline at all, so a malformed
    detection record made its halt indistinguishable from a crash and an operator would
    debug the solver instead of the record.

    Bounded honestly: the one production caller is `lift_clip.py`, whose rows come from a
    live MediaPipe `detect()` that always emits 33 landmarks, so this was the guard
    direction unbounded rather than a live escape; the exposure is a detection record read
    back from JSON or produced by a second detector.

    Only a row the gate actually READS is checked. A frame the detector did not fire on
    carries no landmarks by definition, and A3's clip-denominator reading already counts
    it as not-in-frame — guarding its shape would refuse a legitimate clip.
    """
    image = r.get("image")
    frame = r.get("frame")
    ev = {"gate": "DONOR", "andon": "DonorGate", "clause": "unreadable_landmark_row",
          "frame": frame, "required_index": required,
          "landmarks_expected": len(LS.POSE_LANDMARKS),
          "ankle_indices": dict(idx), "image_type": type(image).__name__}
    if not isinstance(image, (list, tuple)):
        raise DonorGate(
            f"frame {frame}'s detection record carries `image` as a "
            f"{type(image).__name__}, which is not the ordered landmark sequence this "
            f"clause indexes by position. A gate that cannot read its own operand halts "
            f"by name rather than crashing under one", dict(ev, n_landmarks=None))
    if len(image) <= required:
        raise DonorGate(
            f"frame {frame}'s detection record carries {len(image)} landmark(s) and this "
            f"clause reads index {required} ({', '.join(f'{a}={idx[a]}' for a in ANKLES)}), "
            f"so the ankles are not in it at all. A record of a different topology is not "
            f"a clip with its ankles out of frame — it is a record this gate cannot grade, "
            f"and MediaPipe's own POSE_LANDMARKS has "
            f"{len(LS.POSE_LANDMARKS)} entries",
            dict(ev, n_landmarks=len(image)))
    for a in ANKLES:
        xy = image[idx[a]]
        if not isinstance(xy, (list, tuple)) or len(xy) < 2:
            raise DonorGate(
                f"frame {frame}'s {a} landmark is a {type(xy).__name__} ({xy!r}), which "
                f"is not the (x, y) pair this clause tests for being inside the image. "
                f"A landmark nothing can read is not a landmark outside the frame",
                dict(ev, n_landmarks=len(image), landmark=a,
                     landmark_index=idx[a], landmark_type=type(xy).__name__))
        for axis, v in zip(("x", "y"), xy[:2]):
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise DonorGate(
                    f"frame {frame}'s {a} landmark carries {v!r} "
                    f"({type(v).__name__}) where its {axis} coordinate is required",
                    dict(ev, n_landmarks=len(image), landmark=a,
                         landmark_index=idx[a], axis=axis, coordinate=repr(v)))
            # A NaN fails `0.0 <= x <= 1.0` in both directions at once, so `_inside`
            # answers False and the frame is silently counted as ankles-out-of-frame —
            # a measurement-shaped answer to a record that carries no measurement.
            require_finite(f"frame {frame} {a}.{axis}", v, DonorGate,
                           dict(ev, n_landmarks=len(image), landmark=a,
                                landmark_index=idx[a], axis=axis),
                           positive=False)


def ankle_framing(rows, detect_evidence=None):
    """How often the ankles were inside the image — computed PER FRAME, not from rates.

    The aggregate per-landmark fractions the detection gate publishes cannot answer this
    clause on their own: knowing the left ankle is in frame 90 % of the time and the right
    90 % of the time bounds their co-occurrence only to somewhere between 80 % and 90 %,
    and gating on either end of that band would be gating on an artefact of the arithmetic
    rather than on the clip. So the per-frame landmarks are read directly and the
    co-occurrence is exact. The bounds are still reported, as a cross-check on the exact
    number rather than as a substitute for it.

    **The denominator is the CLIP.** Amendment A3's clause is "ankle landmarks inside the
    image on >= 80 % of frames", and *frames* there means the clip's frames. Every
    fraction here used to be computed over `[r for r in rows if r['fired'] and
    r['image']]`, so on a 65-frame clip the detector fired on 3 times, with both ankles
    inside on all 3, `both_ankles_in_image` was 1.0 and the clause passed —
    `n_frames_considered = 3` was honest and gated nothing. That is the repo's
    unit/population class: a donor whose ankles were *observed* on a small minority of
    frames was admitted as a baseline and the lift numbers were quoted against it. A
    frame the detector did not fire on is a frame whose ankles were not inside the image,
    because nothing observed them there. The fired-only fraction is kept beside the
    gating one as a diagnostic, so the two readings are visible rather than swapped.
    """
    # · ANDON — the landmark TABLE, before the index comprehension reads it. See
    # `_require_landmark_table`: the named guard existed and only a test called it.
    idx = _require_landmark_table()
    fired = [r for r in rows if r.get("fired") and r.get("image")]
    if not fired:
        raise DonorGate("no frame carries image landmarks, so the framing clause cannot "
                        "be evaluated. A gate that cannot compute its own quantity halts "
                        "rather than passing",
                        {"gate": "DONOR", "andon": "DonorGate",
                         "clause": "no_frame_carries_landmarks",
                         "n_rows": len(rows)})
    required = max(idx.values())
    per_frame = []
    for r in rows:
        observed = bool(r.get("fired") and r.get("image"))
        if observed:
            # · ANDON — the gate guarded its EMPTY population (`if not fired: raise`) and
            # never the SHAPE of a row it does read. See `_readable_landmark_row`.
            _readable_landmark_row(r, idx, required)
        flags = {a: (observed and _inside(r["image"][idx[a]])) for a in ANKLES}
        per_frame.append({"frame": r.get("frame"), **flags, "observed": observed,
                          "both": all(flags.values()), "either": any(flags.values())})
    n = len(per_frame)
    n_fired = len(fired)
    per_ankle = {a: sum(1 for f in per_frame if f[a]) / n for a in ANKLES}
    both = sum(1 for f in per_frame if f["both"]) / n
    either = sum(1 for f in per_frame if f["either"]) / n
    observed_frames = [f for f in per_frame if f["observed"]]
    out = {
        "n_frames_considered": n,
        "n_frames_detector_fired": n_fired,
        "per_ankle_fraction_of_frames_in_image": per_ankle,
        "both_ankles_in_image": both,
        "either_ankle_in_image": either,
        "both_ankles_in_image_over_fired_frames_only": (
            sum(1 for f in observed_frames if f["both"]) / n_fired),
        "why_the_fired_only_fraction_is_not_the_gate": (
            "it is a diagnostic. A3's clause counts CLIP frames, and a frame the "
            "detector did not fire on is not a frame whose ankles were seen inside the "
            "image. Gating on the fired-only fraction let 3 perfect frames out of 65 "
            "read 1.0"),
        "reading_that_gates": ("both ankles in image, counted per frame over every frame "
                               "of the clip"),
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
            dict({k: v for k, v in out.items() if k != "frames"},
                 gate="DONOR", andon="DonorGate",
                 clause="ankle_fractions_off_different_populations"))
    return out


def _readable_gate_record(name, record, required, producer):
    """Gate DONOR's refusal for an argument record whose key moved.

    ⚠ **The gate read its two argument records with BARE SUBSCRIPTS, and the fragile path
    was the REFUSAL path.** `m = motion['mean']` and `f = framing['both_ankles_in_image']`
    were bare, and the failure branch composes its own message from
    `framing['per_ankle_fraction_of_frames_in_image']['left_ankle'|'right_ankle']`, which
    nothing reads when the clip passes. Measured 2026-09-05 in this worktree on `580af47`:
    `gate_donor({'mean_over_255': 3.0}, {'both_ankles_in_image': 0.9})` raised
    `KeyError: 'mean'`; `gate_donor({'mean': 3.0}, {'ankles_in_image': 0.9})` raised
    `KeyError: 'both_ankles_in_image'`; and — the sharp one —
    `gate_donor({'mean': 0.1}, {'both_ankles_in_image': 0.1})`, a clip that FAILS both of
    A3's clauses, raised `KeyError: 'per_ankle_fraction_of_frames_in_image'`.

    `isinstance(exc, ArmatureError)` is False for all three, so the halt contract's exit-2
    receipt branch is bypassed and a deliberate Gate DONOR refusal is classified exit 1 —
    an unhandled crash — with the evidence dict (thresholds, both measurements, `verdict:
    FAILED`) reaching no printed line. The operator sees a stdlib traceback where "this
    clip is not a baseline" belonged, on the gate whose pass is the input to every
    rotation solved afterwards.

    This is one step earlier than the direction this function already accepted: the two
    MEASURED quantities were given `parts.require_finite` on the stated ground that "the
    exposure is a caller, or a future producer (a record read back from a JSON motion
    summary), handing the gate a non-number". The same producer class hands it a record
    whose KEY moved, and the presence of the key got no clause while the finiteness of its
    value did. The sibling shape inside this module — `_readable_landmark_row`, refusing
    the SHAPE of a row `ankle_framing` reads — is the pattern copied here.

    `producer` names which function in this module writes the record, so the halt line
    tells the operator where to look rather than only that a key was absent.
    """
    if not isinstance(record, dict):
        raise DonorGate(
            f"Gate DONOR's `{name}` argument is a {type(record).__name__} "
            f"({record!r}), not the record `{producer}` writes. A gate that cannot read "
            f"its own operand halts by name rather than crashing under one",
            {"gate": "DONOR", "andon": "DonorGate", "clause": "unreadable_gate_input",
             "argument": name, "producer": producer, "required_keys": list(required),
             "record_type": type(record).__name__, "record_keys": None},
        )
    missing = [k for k in required if k not in record]
    if missing:
        raise DonorGate(
            f"Gate DONOR's `{name}` record is missing {missing!r}; it carries "
            f"{sorted(map(str, record))!r}. `{producer}` is what writes this record — a "
            f"renamed or dropped key reaches this gate as a `KeyError`, which is not an "
            f"`ArmatureError`, so a deliberate refusal would be classified as an "
            f"unhandled crash and the evidence would reach no printed line",
            {"gate": "DONOR", "andon": "DonorGate", "clause": "unreadable_gate_input",
             "argument": name, "producer": producer, "required_keys": list(required),
             "missing_keys": missing, "record_type": type(record).__name__,
             "record_keys": sorted(map(str, record))},
        )
    return record


def _readable_per_ankle(per_ankle):
    """The per-ankle sub-record the FAILURE message indexes, guarded on the same clause.

    `ANKLES` is the population: the refusal branch formats
    `per_ankle_fraction_of_frames_in_image[a]` for each, so a record carrying the outer key
    and not the inner ones crashes only on the path that was about to refuse.
    """
    if not isinstance(per_ankle, dict):
        raise DonorGate(
            f"Gate DONOR's `framing.per_ankle_fraction_of_frames_in_image` is a "
            f"{type(per_ankle).__name__} ({per_ankle!r}), not a per-ankle mapping. The "
            f"REFUSAL message indexes it, so this shape crashes exactly when the gate was "
            f"about to say the clip is not a baseline",
            {"gate": "DONOR", "andon": "DonorGate", "clause": "unreadable_gate_input",
             "argument": "framing.per_ankle_fraction_of_frames_in_image",
             "producer": "donor_gate.ankle_framing", "required_keys": list(ANKLES),
             "record_type": type(per_ankle).__name__, "record_keys": None},
        )
    missing = [a for a in ANKLES if a not in per_ankle]
    if missing:
        raise DonorGate(
            f"Gate DONOR's `framing.per_ankle_fraction_of_frames_in_image` is missing "
            f"{missing!r}; it carries {sorted(map(str, per_ankle))!r}. The REFUSAL message "
            f"indexes both ankles, so this record refuses cleanly on a passing clip and "
            f"crashes on a failing one",
            {"gate": "DONOR", "andon": "DonorGate", "clause": "unreadable_gate_input",
             "argument": "framing.per_ankle_fraction_of_frames_in_image",
             "producer": "donor_gate.ankle_framing", "required_keys": list(ANKLES),
             "missing_keys": missing, "record_type": type(per_ankle).__name__,
             "record_keys": sorted(map(str, per_ankle))},
        )
    return per_ankle


def gate_donor(motion, framing):
    """ANDON. Raises unless BOTH of A3's clauses hold. Returns the evidence when they do.

    **There is no `thresholds` argument and there will not be one.** The signature used to
    read `gate_donor(motion, framing, thresholds=None)` and line 189 used the caller's
    dict verbatim, so `thresholds={'min_mean_consecutive_frame_difference_over_255': 0.0,
    'min_fraction_of_frames_with_ankles_in_image': 0.0}` returned the verdict "mean
    consecutive-frame difference 0.0000/255 (>= 0.0) and ankles in image on at least 0.0%
    of frames (>= 0%)" on a dead-still, ankles-never-in-frame clip — measured 2026-09-03.
    That is a skip flag inside an andon, which CLAUDE.md forbids outright, and it
    contradicted this module's own docstring two screens above it: the thresholds "are
    not tuned here and they are not tunable here". A fixture that needs a different
    number monkeypatches `THRESHOLDS`; a different experiment writes a different module
    constant with its own amendment reference.
    """
    th = dict(THRESHOLDS)
    m_min = th["min_mean_consecutive_frame_difference_over_255"]
    f_min = th["min_fraction_of_frames_with_ankles_in_image"]
    # · ANDON — the two ARGUMENT RECORDS, before the first subscript. See
    # `_readable_gate_record`: `m = motion['mean']` and `f = framing[
    # 'both_ankles_in_image']` were bare, and so were the two per-ankle reads the FAILURE
    # message composes — so the fragile path was the refusal path, not the pass path.
    _readable_gate_record("motion", motion, ("mean",),
                          "donor_gate.mean_consecutive_frame_difference")
    _readable_gate_record("framing", framing,
                          ("both_ankles_in_image",
                           "per_ankle_fraction_of_frames_in_image"),
                          "donor_gate.ankle_framing")
    _readable_per_ankle(framing["per_ankle_fraction_of_frames_in_image"])
    m = motion["mean"]
    f = framing["both_ankles_in_image"]

    ev = {
        "gate": "DONOR", "andon": "DonorGate",
        "tool_version": TOOL_VERSION, "thresholds": th,
        "motion": {"measured_mean_over_255": m, "threshold": m_min, "passes": m >= m_min},
        "framing": {"measured_fraction": f, "threshold": f_min, "passes": f >= f_min,
                    "detail": {k: v for k, v in framing.items() if k != "frames"}},
        "motion_detail": {k: v for k, v in motion.items() if k != "per_pair"},
    }

    # · ANDON — the two MEASURED quantities, through the repo's one non-finite helper.
    # Gate DONOR was the last andon in `armature_core` whose measurements never passed a
    # finiteness test, while the same wave gave `parts.require_finite` to `shotspec`,
    # `subject`, `rig_gates` (six quantities), `assembly`, `startframe`, `turnaround` and
    # Gates RIGID/CADENCE for exactly this inversion. The two clauses below are `m < m_min`
    # and `f < f_min`, and BOTH are False for a NaN. Measured 2026-09-04 in this worktree:
    # `gate_donor({'mean': nan, ...}, {'both_ankles_in_image': nan, ...})` RETURNED with the
    # verdict "mean consecutive-frame difference nan/255 (>= 2.0) and ankles in image on at
    # least nan% of frames (>= 80%)" — an affirmative pass printing the NaN inside the
    # verdict it had just asserted. `rig_gates._require_finite_measurement`'s own comment
    # names this: the inversion is the loud one.
    #
    # The live producers cannot emit a NaN today — `mean_consecutive_frame_difference`
    # differences uint8 PNG arrays through a numpy mean, `frame_paths` admits only `.png`,
    # and `ankle_framing` guards its empty population — so this is the guard direction being
    # unbounded rather than a live escape. The exposure is a caller, or a future producer
    # (a record read back from a JSON motion summary), handing the gate a non-number. Gate
    # DONOR decides whether a clip may be a baseline at all, and a pass here is the input to
    # every rotation `lift_clip` then solves.
    #
    # `positive=False` on both: a mean absolute difference and a fraction of frames may
    # legitimately be zero, and zero is what the thresholds below are for.
    require_finite("motion.mean", m, DonorGate, ev, positive=False)
    require_finite("framing.both_ankles_in_image", f, DonorGate, ev, positive=False)

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
        ev["clause"] = "donor_below_threshold"
        raise DonorGate(
            "; ".join(failed) + ". A donor failing this gate is a recorded take, not a "
            "baseline: nothing is lifted off it, and A3 item 4 governs what happens next",
            ev)
    ev["verdict"] = (f"mean consecutive-frame difference {m:.4f}/255 (>= {m_min}) and "
                     f"ankles in image on at least {f:.1%} of frames (>= {f_min:.0%})")
    return ev


def _require_landmark_table():
    """Gate DONOR's `landmark_table_renamed`, and the ankle index map it hands back.

    ⚠ **This was a named guard that only a TEST called.** It read
    `def _landmark_names_are_the_ones_this_module_assumes(): return all(a in
    LS.POSE_LANDMARKS for a in ANKLES)` — a predicate returning a bool — and its docstring
    called it "a guard against the landmark table being renamed out from under the ankle
    clause". Measured 2026-09-05 by grep across the worktree on `e8263a3`: exactly one
    caller, `tests/test_donor_gate.py:64`, and no code path in `tools/` invoked it at all.
    So in production the protection was whatever `LS.POSE_LANDMARKS.index(a)` inside
    `ankle_framing` happened to do — a `ValueError`, which is not an `ArmatureError` and so
    bypasses the halt contract's exit-2 branch, and which is raised AFTER `ankle_framing`
    has been entered rather than before. A named guard that only a test calls reads as an
    armed check and is not one.

    Its own sibling two lines below the same `idx` construction — `_readable_landmark_row`,
    added in waves 12/14 — DOES raise `DonorGate`; this one did not get the same treatment.
    It is now that same shape: it raises, it names the missing names and the table it read
    them from, and it returns the `{name: index}` map so there is one construction of the
    ankle indices rather than a check beside a separate read.

    `lift_solve.POSE_LANDMARKS` is MediaPipe's 33-entry topology as this repo records it.
    A rename there is a data change of exactly the class `canon_census.CENSUS` and
    `route_gates.RULED_COMPONENTS` carry their own import-time andons for.
    """
    missing = [a for a in ANKLES if a not in LS.POSE_LANDMARKS]
    if missing:
        raise DonorGate(
            f"the landmark table this clause indexes no longer carries {missing!r}: "
            f"`lift_solve.POSE_LANDMARKS` has {len(LS.POSE_LANDMARKS)} entries and Gate "
            f"DONOR's framing clause is written against the names {list(ANKLES)}. A table "
            f"renamed out from under the clause is not a clip whose ankles are out of "
            f"frame — it is a gate that cannot compute its own quantity, and reading it "
            f"anyway raises a bare `ValueError` from inside the clause, which is not an "
            f"`ArmatureError` and so leaves the run classified as a crash",
            {"gate": "DONOR", "andon": "DonorGate", "clause": "landmark_table_renamed",
             "missing": missing, "expected": list(ANKLES),
             "landmarks_expected": len(LS.POSE_LANDMARKS),
             "table": "lift_solve.POSE_LANDMARKS",
             "table_names": list(LS.POSE_LANDMARKS)})
    return {a: LS.POSE_LANDMARKS.index(a) for a in ANKLES}
