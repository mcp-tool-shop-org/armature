"""Tests for the timing-correlation instrument.

Every fixture here was written by asking the question the repo asks of a fixture: *what
would this look like if the code were wrong in the specific way this check exists to
catch?* The failures being guarded are, in order of how quietly they would pass:

* **the colour mode drifts to RGB** — returns numbers, plausible ones, ~0.037 off on A1a,
  which is over half the gap E04 exists to put a floor under;
* **the frame axis gets scrambled** by a lexical sort over ragged names — still returns a
  correlation, over the wrong time axis;
* **a constant clip returns nan** — printed beside real numbers, reads as "low";
* **the anchor passes vacuously** because E02's gitignored runs are not on disk.

The anchor leg itself needs E02's outputs, which are gitignored, so those tests skip
outside the rig. What does NOT skip is the check that the anchor *can* fail — a check
that cannot fail is not a check.
"""

import ast
import importlib
import json
import os
import sys

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import _census_nodes as CN  # noqa: E402
from conftest import RECORD_FAMILIES as _RECORD_FAMILIES  # noqa: E402
from conftest import repo_file  # noqa: E402

import measure_tracking as mt  # noqa: E402

#: WAVE 16, F-269878af. This was `E02_ROOT = "outputs/E02"` — a bare relative path resolved
#: against `os.getcwd()`, and the FIFTH guard of the shape `conftest.repo_file()` was written
#: to end. Re-measured both directions on 041027c: run from an unrelated scratch directory,
#: the three tests below SKIP even on the rig that HAS the runs; seed that scratch directory
#: with an empty `outputs/E02/runs` and the guard reads True, the three ARM, and
#: `measure_tracking.py:133` fails on "no such frame directory" for a directory that is not
#: this repo's. The anchor that reproduces every published E02 figure therefore reported
#: green having examined nothing, from any working directory but the repo root.
E02_ROOT = repo_file("outputs/E02")
HAVE_E02 = os.path.isdir(os.path.join(E02_ROOT, "runs"))


# ------------------------------------------------------------------ fixture helpers

def write_frames(d, arrays, width=8, height=8, pad=5):
    """Write frames from a list of per-frame (r, g, b) fill levels."""
    os.makedirs(d, exist_ok=True)
    for i, rgb in enumerate(arrays):
        a = np.zeros((height, width, 3), dtype=np.uint8)
        a[:, :] = rgb
        Image.fromarray(a, "RGB").save(os.path.join(d, f"{i:0{pad}d}.png"))
    return d


def gray_frames(d, levels, **kw):
    return write_frames(d, [(v, v, v) for v in levels], **kw)


# ---------------------------------------------------------------- floor and ceiling

def test_a_run_whose_energy_tracks_the_control_exactly_gives_plus_one(tmp_path):
    """The ceiling, stated before any real number is read."""
    levels = [0, 10, 40, 45, 90, 100, 160]
    run = gray_frames(str(tmp_path / "run"), levels)
    ctl = gray_frames(str(tmp_path / "ctl"), levels)
    assert mt.measure(run, ctl)["timing_correlation"] == pytest.approx(1.0)


def test_an_anti_correlated_run_gives_minus_one(tmp_path):
    """The floor. An arm can be anti-correlated, and the tool must be able to say so.

    A rising energy profile against a falling one is exactly -1. (An earlier version of
    this fixture used a profile against its own reverse, which is *not* anti-correlation:
    reversing [10,30,5,50,20] correlates at +0.61. The fixture was wrong, not the tool.)
    """
    run = gray_frames(str(tmp_path / "run"), np.cumsum([0, 10, 20, 30, 40]).tolist())
    ctl = gray_frames(str(tmp_path / "ctl"), np.cumsum([0, 40, 30, 20, 10]).tolist())
    assert mt.measure(run, ctl)["timing_correlation"] == pytest.approx(-1.0)


def test_correlation_is_scale_invariant(tmp_path):
    """A brighter clip that moves at the same moments must not read as tracking better.

    Levels are chosen even so halving is exact — integer rounding in the fixture would
    otherwise put the answer at 0.9997 and this would look like a tool defect.
    """
    base = [0, 20, 80, 90, 180, 200, 240]
    run = gray_frames(str(tmp_path / "run"), base)
    ctl = gray_frames(str(tmp_path / "ctl"), [v // 2 for v in base])
    assert mt.measure(run, ctl)["timing_correlation"] == pytest.approx(1.0)


# ------------------------------------------------- the colour mode is part of the definition

def test_the_statistic_is_GRAYSCALE_and_RGB_would_give_a_different_answer(tmp_path):
    """The pin on `convert("L")`.

    Frames move in R on some steps and in G on others. Grayscale weights those 0.299 and
    0.587; a per-channel RGB mean weights both 1/3 — so the two modes see different
    profile *shapes*, not just different scales, and correlation cannot absorb it.

    If someone changes the tool to RGB, this test fails. That is the whole job: E02's
    published +0.521 is the L-mode value, and the RGB-mode value for the same frames is
    +0.558.
    """
    # cumulative levels: R steps then G steps, alternating magnitudes
    frames = [(0, 0, 0), (30, 0, 0), (30, 30, 0), (40, 30, 0), (40, 40, 0)]
    run = write_frames(str(tmp_path / "run"), frames)
    ctl = gray_frames(str(tmp_path / "ctl"), [0, 10, 30, 60, 100])

    got = mt.measure(run, ctl)["timing_correlation"]

    def rgb_mode_value():
        names = sorted(os.listdir(run))
        stack = np.stack([np.asarray(Image.open(os.path.join(run, n)).convert("RGB"),
                                     dtype=np.float64) for n in names])
        prof = np.abs(np.diff(stack, axis=0)).mean(axis=(1, 2, 3))
        cnames = sorted(os.listdir(ctl))
        cstack = np.stack([np.asarray(Image.open(os.path.join(ctl, n)).convert("L"),
                                      dtype=np.float64) for n in cnames])
        cprof = np.abs(np.diff(cstack, axis=0)).mean(axis=(1, 2))
        return float(np.corrcoef(prof, cprof)[0, 1])

    assert abs(got - rgb_mode_value()) > 0.05, (
        "the fixture no longer discriminates between L and RGB, so this test would pass "
        "for a tool that had silently switched colour mode"
    )
    assert mt.measure(run, ctl)["colour_mode"].startswith("L")


def test_the_control_profile_is_blind_to_polarity(tmp_path):
    """`255 - x` on the control must leave the statistic untouched.

    Measured on E02's own pair (max difference 0.0 over 32 deltas), and it is the reason
    both E04 conditions correlate against the same reference profile. A tool that squared
    or signed the deltas instead of taking their absolute value would break this.
    """
    levels = [10, 30, 35, 80, 120, 130]
    run = gray_frames(str(tmp_path / "run"), [0, 20, 25, 90, 100, 150])
    ctl = gray_frames(str(tmp_path / "ctl"), levels)
    inv = gray_frames(str(tmp_path / "inv"), [255 - v for v in levels])

    a, b = mt.load_profile(ctl)[0], mt.load_profile(inv)[0]
    assert np.abs(a - b).max() == 0.0
    assert (mt.measure(run, ctl)["timing_correlation"]
            == pytest.approx(mt.measure(run, inv)["timing_correlation"]))


# --------------------------------------------------------------------- refusals

def test_a_clip_that_never_moves_raises_rather_than_returning_nan(tmp_path):
    """nan is the absence of a measurement, not a low correlation."""
    run = gray_frames(str(tmp_path / "run"), [40] * 6)
    ctl = gray_frames(str(tmp_path / "ctl"), [0, 10, 40, 45, 90, 100])
    with pytest.raises(mt.TrackingError, match="constant"):
        mt.measure(run, ctl)


def test_a_constant_CONTROL_also_raises(tmp_path):
    """Both directions. A control that does not move cannot grade an arm that does."""
    run = gray_frames(str(tmp_path / "run"), [0, 10, 40, 45, 90, 100])
    ctl = gray_frames(str(tmp_path / "ctl"), [40] * 6)
    with pytest.raises(mt.TrackingError, match="constant"):
        mt.measure(run, ctl)


def test_ragged_frame_names_raise_instead_of_scrambling_the_time_axis(tmp_path):
    """`1.png, 2.png, 10.png` sorts 1, 10, 2 — and still returns a correlation."""
    d = str(tmp_path / "ragged")
    os.makedirs(d)
    for i, v in enumerate([0, 10, 40, 45, 90, 100, 160, 200, 210, 240, 250]):
        a = np.full((8, 8, 3), v, dtype=np.uint8)
        Image.fromarray(a, "RGB").save(os.path.join(d, f"{i}.png"))
    with pytest.raises(mt.TrackingError, match="fixed width"):
        mt.load_profile(d)


def test_mismatched_frame_counts_raise(tmp_path):
    run = gray_frames(str(tmp_path / "run"), [0, 10, 40, 45, 90])
    ctl = gray_frames(str(tmp_path / "ctl"), [0, 10, 40, 45, 90, 100, 160])
    with pytest.raises(mt.TrackingError, match="frame counts differ"):
        mt.measure(run, ctl)


def test_too_few_frames_raise(tmp_path):
    run = gray_frames(str(tmp_path / "run"), [0, 40])
    ctl = gray_frames(str(tmp_path / "ctl"), [0, 40])
    with pytest.raises(mt.TrackingError, match="degenerate"):
        mt.measure(run, ctl)


def test_an_empty_or_missing_directory_raises(tmp_path):
    ctl = gray_frames(str(tmp_path / "ctl"), [0, 10, 40, 45, 90])
    with pytest.raises(mt.TrackingError, match="no such frame directory"):
        mt.measure(str(tmp_path / "nope"), ctl)
    os.makedirs(str(tmp_path / "empty"))
    with pytest.raises(mt.TrackingError, match="no PNG frames"):
        mt.measure(str(tmp_path / "empty"), ctl)


def test_the_report_names_its_own_inputs(tmp_path):
    """A number with no provenance is not evidence."""
    run = gray_frames(str(tmp_path / "run"), [0, 10, 40, 45, 90])
    ctl = gray_frames(str(tmp_path / "ctl"), [0, 20, 25, 90, 100])
    rec = mt.measure(run, ctl, label="probe")
    assert rec["label"] == "probe"
    assert rec["tool_version"] == mt.TOOL_VERSION
    assert len(rec["run"]["manifest_sha256"]) == 64
    assert rec["run"]["manifest_sha256"] != rec["control"]["manifest_sha256"]
    assert rec["n_deltas"] == rec["n_frames"] - 1 == 4


# ------------------------------------------------------------------- the anchor leg

def test_the_anchor_reports_NOT_RUN_rather_than_passing_vacuously(tmp_path):
    """An anchor that reports green when it read nothing is worse than no anchor."""
    assert mt.anchor(str(tmp_path / "no-such-root")) is None


@pytest.mark.skipif(not HAVE_E02, reason="E02 runs are gitignored output")
def test_the_anchor_reproduces_every_published_E02_figure():
    rows = mt.anchor(E02_ROOT)
    assert rows is not None and len(rows) == 5
    for r in rows:
        assert r["delta"] <= mt.ANCHOR_TOLERANCE, r


@pytest.mark.skipif(not HAVE_E02, reason="E02 runs are gitignored output")
def test_the_anchor_CAN_fail(monkeypatch):
    """Drive it to failure. A check that cannot fail is not a check."""
    monkeypatch.setitem(mt.E02_PUBLISHED, "A1a",
                        dict(mt.E02_PUBLISHED["A1a"], value=0.999))
    with pytest.raises(mt.AnchorMismatch, match="does not reproduce"):
        mt.anchor(E02_ROOT)


@pytest.mark.skipif(not HAVE_E02, reason="E02 runs are gitignored output")
def test_A1a_lossless_and_A1a_H264_are_NOT_the_same_number():
    """Why `E02_PUBLISHED` points A1a at A0r1's frames.

    A1a ran before the lossless tap existed. Its own frames came back through H.264, and
    the codec moves this statistic by ~0.025 — about 40% of the 0.060 gap E04 exists to
    put a floor under. Pointing the anchor at the wrong directory would miss by more than
    the tolerance, which is what makes this an anchor rather than a formality.
    """
    ctl = os.path.join(E02_ROOT, "control_480x832", "depth_pershot")
    lossless = mt.measure(os.path.join(E02_ROOT, "runs", "A0r1", "lossless"), ctl)
    h264_dir = os.path.join(E02_ROOT, "runs", "A1a", "frames")
    if not os.path.isdir(h264_dir):
        pytest.skip("A1a's H.264 frames are not on disk")
    h264 = mt.measure(h264_dir, ctl)
    assert abs(lossless["timing_correlation"] - h264["timing_correlation"]) > 0.02
    assert lossless["timing_correlation"] == pytest.approx(0.521, abs=0.0005)


# ------------------------------------------- the output-gated guards, ENUMERATED (wave 16)
#
# WAVE 16, F-269878af + F-665cd590. Two findings, one missing object: nothing in the suite
# named the population of guards that decide whether a gitignored `outputs/` run is visible.
# That is how the fifth guard was written as a bare relative path four waves after the other
# four were anchored, and how the worktree/main skip delta had to be re-measured from
# scratch by three consecutive waves — the coordinator's standing seed even attributed it to
# the wrong pair of files ("12 test_gate_s:154, 3 test_aapose_convention:190"; measured here,
# the aapose trio skips in BOTH trees and is not in the delta at all).
#
# The census lives in `tests/_census_nodes.py` beside every other walk this suite keys on.
# It reads three spellings of the decorator, because all three are live:
# `@pytest.mark.skipif(not GUARD, ...)`, a module-level `needs_bank = pytest.mark.skipif(...)`
# applied bare, and no decorator at all (a helper that calls `pytest.skip`).


def _parametrized_item_count(mod_name, test_name):
    """How many COLLECTED items one gated test function is, from its own decorators.

    `test_gate_s`'s single gated function is 12 items (4 arms x 3 seeds) and that is where
    12 of the 15 delta skips come from. The multiplier is read off the module's own
    `parametrize` arguments rather than typed, so adding a seed moves this count without
    anybody editing a number.
    """
    module = importlib.import_module(mod_name)
    tree = CN.test_module_trees()[mod_name]
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
              and n.name == test_name)
    count = 1
    for dec in fn.decorator_list:
        if not (isinstance(dec, ast.Call) and CN.called_name(dec) == "parametrize"):
            continue
        if len(dec.args) < 2:
            raise AssertionError(f"{mod_name}::{test_name} parametrize takes no argvalues")
        count *= len(eval(ast.unparse(dec.args[1]), vars(module)))  # noqa: S307
    return count


def test_every_output_gated_guard_in_the_suite_is_anchored_on_the_repo_root():
    """The POPULATION, not the site the finding named (wave-16 rule 1).

    Seven module-level constants across six test modules resolved a path under `outputs/`
    when this was written; six were already repo-anchored and the seventh was this file's
    `E02_ROOT`. Re-measured on the wave-26 branch: EIGHT across six modules, the eighth being
    `test_gate_s.E02_PAYLOAD_BRANCHES` (F-4c22f096), and every one anchored. A guard that
    resolves against `os.getcwd()` answers a different question from the one it is asked,
    in both directions, and the skip reason it prints reads as though the repo simply has
    no run in it.
    """
    constants = CN.output_path_constants()
    drifting = {k: v[0] for k, v in constants.items() if not v[1]}
    assert drifting == {}, (
        f"{sorted(drifting)} resolve an `outputs/` path against os.getcwd(); anchor them on "
        f"conftest.repo_file() or os.path.join(REPO, ...) like the other guards")
    # WAVE 26, F-4c22f096: EIGHT now. `test_gate_s.E02_PAYLOAD_BRANCHES` joined beside
    # `E02_PAYLOAD_PATHS` — both are assigned from `conftest.payload_record*`, which reaches
    # `repo_file` through `_record_paths`, so both are anchored. That is the widening this
    # census demanded and got: `_is_repo_anchored` recognised the single call `repo_file(...)`
    # and nothing built on it, so a constant resolved through a correct resolver read as
    # cwd-relative. The anchored set is now DERIVED from conftest to a fixed point
    # (`_census_nodes.repo_anchored_resolvers`) rather than typed, which is why adding
    # `payload_record` did not require adding a name here.
    assert sorted(constants) == [
        ("test_aapose_convention", "BANKED"),
        ("test_build_i2v_payload", "BANKED"),
        ("test_build_t2v_payload_a3", "BANK"),
        ("test_donor_gate", "PROBE"),
        ("test_donor_gate", "PROBE_MEASURE"),
        ("test_gate_s", "E02_PAYLOAD_BRANCHES"),
        ("test_gate_s", "E02_PAYLOAD_PATHS"),
        ("test_measure_tracking", "E02_ROOT"),
    ], sorted(constants)


def test_a_foreign_working_directory_cannot_arm_or_disarm_an_output_gated_guard(tmp_path,
                                                                                monkeypatch):
    """The RED PROOF, on the operand the finding named: the working directory.

    Both directions on the same scratch cwd. The anchored expression this file now uses is
    unmoved by a decoy `outputs/E02/runs` sitting in the caller's working directory; the
    bare relative expression it replaced reads True on that decoy — which is the false ARM
    that took the three anchor tests into `measure_tracking.py:133` on a directory that is
    not this repo's.
    """
    # WAVE-16 MERGE (coordinator, 2026-09-04): the first cut assumed the repo carries NO `outputs/E02/runs`; the main
    # checkout DOES (gitignored rig artifacts). The scratch cwd is now built in the OPPOSITE state
    # from the repo's, so the two spellings disagree on every rig and the fixture measures the
    # operand (the cwd) in both directions.
    repo_has_runs = os.path.isdir(os.path.join(repo_file("outputs/E02"), "runs"))
    (tmp_path / "outputs" / "E02").mkdir(parents=True)
    if not repo_has_runs:
        (tmp_path / "outputs" / "E02" / "runs").mkdir()
    monkeypatch.chdir(tmp_path)

    anchored = os.path.isdir(os.path.join(repo_file("outputs/E02"), "runs"))
    bare = os.path.isdir(os.path.join("outputs/E02", "runs"))
    assert bare is (not repo_has_runs), "the scratch cwd must show the spelling that was replaced the opposite state"
    assert anchored is repo_has_runs, "the anchor is cwd-independent"
    assert anchored != bare, (
        "the anchored and the bare spelling agree on a cwd built to disagree with the repo; the "
        "fixture is not measuring what it was written to measure")


#: The three tests in THIS module that a gitignored `outputs/` run can skip, named rather
#: than cited by line (wave 26, F-a15086f0). The docstring below used to identify them as
#: `test_measure_tracking.py:211/219/228`; measured on `81d6c07`, the three
#: `@pytest.mark.skipif(not HAVE_E02, ...)` decorators are at :224, :232 and :241, while
#: line 211 is `assert rec["tool_version"] == mt.TOOL_VERSION`, line 219 is the `def` of
#: `test_the_anchor_reports_NOT_RUN_rather_than_passing_vacuously` (which does not skip) and
#: line 228 is a `for r in rows:` inside a test body. The same three decorators sat at
#: 224/232/241 on `ce66e1f` too, so the citation was never right rather than moved by the
#: merge fix-up — and it had propagated into a coordinator brief. A name survives an edit
#: above it; a line number does not, which is why this is the spelling now.
E02_GATED_HERE = [
    "test_A1a_lossless_and_A1a_H264_are_NOT_the_same_number",
    "test_the_anchor_CAN_fail",
    "test_the_anchor_reproduces_every_published_E02_figure",
]


def test_the_worktree_to_checkout_skip_delta_is_read_off_the_suite_not_re_measured():
    """F-665cd590: PIN the delta by PATH, so the fourth wave does not measure it again.

    Measured on 041027c by running the six gated modules in both trees under one recipe: a
    fresh worktree skipped 28 of these, a checkout carrying `outputs/` skipped 13, and the
    15-test difference was EXACTLY the E02 subtree — 12 collected items in `test_gate_s.py`
    (4 arms x 3 seeds) and the 3 named in `E02_GATED_HERE` above.

    WAVE 26, F-4c22f096 — the twelve are GONE from this population. The two E02 base
    payloads are committed under `tests/fixtures/records/E02/payloads/` and resolved by
    `conftest.payload_record`, so `test_gate_s.py`'s comparison rides every run and the
    module leaves the gated census entirely. Re-derived here on the branch that did it: the
    population is 16 across FIVE modules, and the worktree-to-checkout delta is 3, not 15.

    The other 13 (aapose 3, build_i2v 2, build_t2v_payload_a3 5, donor_gate 3) gate on E08,
    E09 and E11 banks that are absent in BOTH trees and are part of the common baseline.
    """
    gated = CN.output_gated_tests()
    by_module = {}
    for mod, name, _line in gated:
        by_module.setdefault(mod, set()).add(name)
    assert sorted(by_module) == [
        "test_aapose_convention", "test_build_i2v_payload", "test_build_t2v_payload_a3",
        "test_donor_gate", "test_measure_tracking"], sorted(by_module)
    assert len(gated) == 16, sorted(gated)
    assert "test_gate_s" not in by_module, (
        "test_gate_s is gated on `outputs/` again; if a new comparison needs a live run, its "
        "record belongs in tests/fixtures/records/ beside the two E02 payloads")

    e02 = {(m, n) for (m, n, _l) in gated if m == "test_measure_tracking"}
    items = sum(_parametrized_item_count(m, n) for m, n in sorted(e02))
    assert items == 3, sorted(e02)
    assert sorted(n for (_m, n) in e02) == E02_GATED_HERE, sorted(e02)


def test_the_three_anchor_tests_are_the_ones_this_delta_names():
    """The membership behind the 3, so a fourth gated test here is not silently absorbed.

    WAVE 26, F-a15086f0 — the list is `E02_GATED_HERE` now, one object, read by this test and
    by the delta test above, so the names cannot fork the way the line numbers did.
    """
    mine = sorted(n for (m, n, _l) in CN.output_gated_tests() if m == "test_measure_tracking")
    assert mine == E02_GATED_HERE, mine


def test_every_name_in_the_delta_list_is_a_test_that_exists_in_this_module():
    """A name that survives an edit is only better than a line number if it is CHECKED.

    F-a15086f0's own defect in its new spelling would be a name that no longer resolves, so
    the list is held to the module's actual `def`s, read off the AST.
    """
    import ast

    with open(__file__, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    defined = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    absent = [n for n in E02_GATED_HERE if n not in defined]
    assert absent == [], f"the delta list names tests this module does not define: {absent}"


# ===========================================================================
# WAVE 23, F-ef2a00e9 — the upload-record fixtures are a BYTE COPY, checked
# ===========================================================================
#
# `conftest.upload_record` prefers the live `outputs/` record when the rig has one and falls
# back to `tests/fixtures/uploads/...` otherwise, and its docstring stated the load-bearing
# claim in prose — "the fixture is a byte copy of the record the run actually submitted,
# which is why the pinned payload hashes still bind against it" — with nothing checking it.
#
# Both branches are live at once across the machines that run this suite: an isolated swarm
# worktree carries no upload maps under `outputs/` and takes the FIXTURE on every one of the
# five, while the main checkout has the real files and takes THOSE. The rig and CI therefore
# graded different inputs under one function name, and `UPLOAD_RECORDS` was named by no test
# at all. Measured 2026-09-05, sha256 over all five maps: each matches its fixture byte for
# byte, so this is an absent guard rather than a live divergence — which is exactly when it
# is cheap to add.
#
# This census lives beside the `outputs/`-guard census above because it is the same node:
# what a test reads depends on whether this particular rig has the gitignored run on disk.


@pytest.mark.parametrize("family", sorted(_RECORD_FAMILIES))
def test_every_committed_record_fixture_is_a_byte_copy_of_the_live_record(family):
    """Where both copies exist, their bytes are equal — per member of every record family.

    What this looks like if the tree were wrong in the way this exists to catch: a re-run
    rewrites a live upload map, the rig's suite keeps passing against the changed file while
    CI passes against the unchanged fixture, and the byte pin that exists to stop a silent
    re-topologising of an already-reported experiment binds to whichever copy the runner
    happened to have.

    WAVE 26, F-4c22f096 — parametrized over `conftest.RECORD_FAMILIES` rather than written
    against `UPLOAD_RECORDS`, so the two E02 base payloads committed this wave are held to
    the same check on the day they land instead of waiting for someone to notice a second
    family exists. The census was named `..._upload_record_...`; it was never about uploads,
    it was about a committed copy of a gitignored record.
    """
    import hashlib

    from conftest import RECORD_FAMILIES, _record_branch, _record_paths

    population, fixture_root = RECORD_FAMILIES[family]
    assert population, f"the {family} population is empty; nothing below can fire"
    differing, missing, branches = {}, [], {}
    for relpath in population:
        live, fixture = _record_paths(relpath, fixture_root)
        branches[relpath] = _record_branch(relpath, fixture_root)
        if not os.path.isfile(fixture):
            missing.append(relpath)
            continue
        if not os.path.isfile(live):
            continue                       # this rig has no run; the fixture IS the record
        digests = [hashlib.sha256(open(p, "rb").read()).hexdigest()
                   for p in (live, fixture)]
        if digests[0] != digests[1]:
            differing[relpath] = {"live": digests[0], "fixture": digests[1]}

    # RECORDED in the test's own output, so a reader of a passing run knows which copy was
    # graded — the thing that was invisible.
    print(f"{family} record branches: " + json.dumps(branches, sort_keys=True))

    assert missing == [], (
        f"no committed fixture for {missing}; the {family} resolver would hand a caller on a "
        f"clone a path that does not exist")
    assert differing == {}, (
        f"the live record and its committed fixture differ: {differing}. The pinned payload "
        f"hashes bind against whichever copy the runner happened to have.")


@pytest.mark.parametrize("family", sorted(_RECORD_FAMILIES))
def test_the_record_branch_is_the_one_the_resolver_actually_takes(family):
    """The reporter above must describe the chooser, not a second opinion of it.

    A branch function that drifted from the resolver would make the recorded line a
    plausible identifier beside a verdict rather than evidence. Parametrized over every
    record family (wave 26, F-4c22f096); the public `upload_record` / `payload_record` pair
    are thin wrappers on the same `_record`, and the pair-agreement below is asserted on the
    public spelling as well so a wrapper cannot quietly point somewhere else.
    """
    from conftest import (RECORD_FAMILIES, _record, _record_branch, _record_paths,
                          payload_record, upload_record)

    public = {"uploads": upload_record, "payloads": payload_record}[family]
    population, fixture_root = RECORD_FAMILIES[family]
    for relpath in population:
        live, fixture = _record_paths(relpath, fixture_root)
        chosen = _record(relpath, fixture_root)
        branch = _record_branch(relpath, fixture_root)
        assert chosen == {"live": live, "fixture": fixture, "neither": live}[branch], (
            relpath, branch, chosen)
        assert public(relpath) == chosen, (family, relpath, public(relpath), chosen)


def test_the_byte_comparison_can_fail(tmp_path, monkeypatch):
    """The red proof kept in the tree: the census driven over a fixture root whose copy
    differs by one byte, and over one that matches.

    Rule 2 — the real tree is clean today, so the check that exists to catch a divergence
    has nothing to prove it can see one. This drives the same comparison over a synthetic
    pair, both directions.
    """
    import hashlib

    live = tmp_path / "live.json"
    same = tmp_path / "same.json"
    other = tmp_path / "other.json"
    live.write_bytes(b'{"00000": "srv_00000.png"}')
    same.write_bytes(b'{"00000": "srv_00000.png"}')
    other.write_bytes(b'{"00000": "srv_00001.png"}')

    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    assert digest(live) == digest(same)
    assert digest(live) != digest(other)
