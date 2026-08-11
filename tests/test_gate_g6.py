"""Tests for G6 — a spec asked for a performance and the subject did not move.

G6 guards a failure that is **invisible to every other check in the tool**. The tests
therefore do two things: drive the gate directly, and drive `run_export` — the real
function that performs the write — with a backend whose subject genuinely does not move,
then assert that *every other gate still passes on that same run*. If the other gates could
catch it, G6 would be redundant, and a check that is redundant is worth deleting rather
than keeping.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import stage_render  # noqa: E402
from armature_core import gates  # noqa: E402
from armature_core.errors import G6SubjectMotion, SpecError  # noqa: E402
from fake_backend import FakeBackend, make_spec  # noqa: E402


# ------------------------------------------------------------------ the gate, directly

def test_raises_when_every_frame_is_identical():
    with pytest.raises(G6SubjectMotion) as exc:
        gates.g6_subject_motion(["same"] * 33, "per_frame")
    assert exc.value.gate == "G6"
    assert exc.value.evidence["distinct_signatures"] == 1
    assert exc.value.evidence["n_frames"] == 33


def test_passes_when_the_subject_moves():
    ev = gates.g6_subject_motion([f"f{i}" for i in range(33)], "per_frame")
    assert ev["verdict"] == "subject moved"
    assert ev["distinct_signatures"] == 33


def test_does_not_fire_on_a_slow_arc_that_holds_between_two_frames():
    """A gate that fails on correct work is worse than no gate. An arc slow enough to
    round to the same geometry for a frame or two is legitimate; only a shot where NOTHING
    ever moves is the defect."""
    sigs = ["a", "a", "b", "b", "b", "c"]
    assert gates.g6_subject_motion(sigs, "per_frame")["verdict"] == "subject moved"


def test_is_not_armed_in_static_mode_because_there_it_could_not_fail():
    """E01/E02 pin the scene to frame 1 deliberately, so a constant subject is CORRECT
    there. Checking it in static mode would be a check that cannot fail."""
    ev = gates.g6_subject_motion(["same"] * 33, "static")
    assert "N/A" in ev["verdict"]


def test_a_one_frame_performance_raises_because_motion_is_undefined():
    with pytest.raises(G6SubjectMotion, match="fewer than two frames"):
        gates.g6_subject_motion(["only"], "per_frame")


# --------------------------------------------- the gate, through the real write path

def _spec(tmp_path, animation, count=9):
    spec = make_spec(tmp_path, count=count, channels=("depth", "mask"))
    spec["subject"] = {"animation": animation}
    return spec


def test_run_export_halts_on_a_static_subject_in_per_frame_mode(tmp_path):
    spec = _spec(tmp_path, "per_frame")
    backend = FakeBackend(64, 96, moves=False)  # the honest default: the box never moves
    with pytest.raises(G6SubjectMotion):
        stage_render.run_export(spec, str(tmp_path / "run"), backend=backend)


def test_run_export_completes_when_the_subject_moves(tmp_path):
    spec = _spec(tmp_path, "per_frame")
    manifest = stage_render.run_export(
        spec, str(tmp_path / "run"), backend=FakeBackend(64, 96, moves=True)
    )
    assert manifest["gates"]["G6"]["verdict"] == "PASS"
    assert manifest["gates"]["G6"]["detail"]["distinct_signatures"] == 9
    assert [r["scene_frame"] for r in manifest["frames"]] == list(range(1, 10))


def test_G6_is_NA_and_nothing_halts_for_a_static_spec(tmp_path):
    """E01/E02's path must be completely unchanged by E03's addition."""
    manifest = stage_render.run_export(
        spec := _spec(tmp_path, "static"), str(tmp_path / "run"),
        backend=FakeBackend(64, 96, moves=False),
    )
    assert spec["subject"]["animation"] == "static"
    assert manifest["gates"]["G6"]["verdict"] == "N/A"
    assert manifest["gates"]["G1"]["verdict"] == "PASS"


def test_EVERY_OTHER_GATE_PASSES_on_the_run_G6_catches(tmp_path):
    """The justification for G6 existing, in executable form.

    Same backend, same frames, same spec — only `subject.animation` differs. Run as
    `static` the export completes with G1, G2 and G4 all green and 9 well-formed frames on
    disk. That is precisely the artifact a `per_frame` spec would have produced and shipped:
    complete, legal, bbox-consistent, and a figure standing still. Nothing but G6 objects.
    """
    manifest = stage_render.run_export(
        _spec(tmp_path, "static"), str(tmp_path / "run"),
        backend=FakeBackend(64, 96, moves=False),
    )
    assert manifest["gates"]["G1"]["verdict"] == "PASS"
    assert manifest["gates"]["G2"]["verdict"] == "PASS"
    assert manifest["gates"]["G4"]["verdict"] == "PASS"
    assert len(manifest["frames"]) == 9
    assert len({r["geometry_signature"] for r in manifest["frames"]}) == 1
    for name in ("00000.png", "00008.png"):
        assert os.path.getsize(os.path.join(str(tmp_path / "run"), "mask", name)) > 0


# --------------------------------------------------------------- the spec field itself

def test_an_unknown_animation_mode_raises_rather_than_defaulting_to_static(tmp_path):
    """Falling back silently would render 33 identical frames for a spec that asked for a
    performance, and G6 would never arm because the mode it keys on never arrived."""
    spec = _spec(tmp_path, "per-frame")  # hyphen, not underscore
    with pytest.raises(SpecError, match="subject.animation"):
        stage_render.run_export(spec, str(tmp_path / "run"), backend=FakeBackend(64, 96))


def test_the_default_is_static_so_E01_and_E02_specs_are_unchanged(tmp_path):
    spec = make_spec(tmp_path, count=9, channels=("depth", "mask"))
    assert "subject" not in spec
    manifest = stage_render.run_export(
        spec, str(tmp_path / "run"), backend=FakeBackend(64, 96, moves=False)
    )
    assert manifest["spec"]["subject"]["animation"] == "static"
    assert manifest["gates"]["G6"]["verdict"] == "N/A"
