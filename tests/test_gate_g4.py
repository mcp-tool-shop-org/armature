"""G4's tolerance: who owns it, and which direction of it is bounded.

`run_export` did `g4_tol = spec['gates']['g4_tolerance_px']` and passed it straight into
`gates.g4_bbox_sanity` with nothing between — no range check, no type check, no record of
the value used. `shotspec.normalise_spec` `_require`s name, generator, asset.path,
resolution, frames, channels and depth.window, and nothing under `gates`: the key is a plain
`_merge` of DEFAULTS with the file.

Measured 2026-09-03: a spec identical to the committed ones except
`"gates": {"g4_tolerance_px": 100000}` was ACCEPTED by `load_spec`, and `g4_bbox_sanity` at
that value did not raise on facet's own recorded defect — a 751-px mask around a 388-px
projected mesh, deltas [300, 300, 363, 363]. `inf` behaves the same.

Note the asymmetry, which is the whole finding: too-SMALL values (`True`, `-5`) still fire,
so the only unbounded direction is the one that DISARMS the gate. "Put the andon on the
direction the invariant does not bound", unapplied to G4's own tolerance. All five committed
specs carry 2, so this was a latent hole rather than a live wrong number.
"""

import math
import os

import pytest

import stage_render
from armature_core import gates
from armature_core.errors import ArmatureError, G4BboxSanity
from fake_backend import FakeBackend, make_spec


def _spec(tmp_path, tol, **kw):
    spec = make_spec(tmp_path, **kw)
    spec["gates"] = {"g4_tolerance_px": tol}
    return spec


# --------------------------------------------------------------- the unbounded direction


def test_a_loosened_tolerance_is_refused_before_any_frame_renders(tmp_path):
    """THE fixture. 100000 px on a 64x96 frame disarms G4 entirely, and the run would
    complete with a full per-frame g4_deltas_px record and a manifest that looks finished."""
    backend = FakeBackend(64, 96, lie_about_bbox=True)
    with pytest.raises(ArmatureError) as e:
        stage_render.run_export(_spec(tmp_path, 100000), str(tmp_path / "run"),
                                backend=backend)
    assert backend.prepared is False
    assert not (tmp_path / "run").exists()
    assert e.value.evidence["value"] == 100000
    assert e.value.evidence["resolution"] == [64, 96]


def test_an_infinite_tolerance_is_refused(tmp_path):
    with pytest.raises(ArmatureError):
        stage_render.run_export(_spec(tmp_path, float("inf")), str(tmp_path / "run"),
                                backend=FakeBackend(64, 96))


def test_a_bool_is_not_an_integer_number_of_pixels(tmp_path):
    """`True == 1` in Python, so a bool would sail through an `isinstance(v, int)` check
    and print as `True` in the manifest."""
    with pytest.raises(ArmatureError):
        stage_render.run_export(_spec(tmp_path, True), str(tmp_path / "run"),
                                backend=FakeBackend(64, 96))


def test_a_negative_tolerance_is_refused(tmp_path):
    with pytest.raises(ArmatureError):
        stage_render.run_export(_spec(tmp_path, -5), str(tmp_path / "run"),
                                backend=FakeBackend(64, 96))


def test_a_non_numeric_tolerance_is_refused(tmp_path):
    with pytest.raises(ArmatureError):
        stage_render.run_export(_spec(tmp_path, "2"), str(tmp_path / "run"),
                                backend=FakeBackend(64, 96))


def test_the_bound_is_derived_from_the_frame_not_from_a_global_constant(tmp_path):
    """A global constant must not govern a local feature: what counts as a loose tolerance
    on a 64px frame is not what counts as one on 832x480."""
    small = stage_render.g4_tolerance_limit(64, 96)
    large = stage_render.g4_tolerance_limit(832, 480)
    assert large > small
    assert stage_render.resolve_g4_tolerance(_spec(tmp_path, large), 832, 480)[0] == large
    with pytest.raises(ArmatureError):
        stage_render.resolve_g4_tolerance(_spec(tmp_path, large + 1), 832, 480)


# ----------------------------------------------------------------------- who owns it


def test_the_gate_owns_the_tolerance_when_it_declares_one(tmp_path, monkeypatch):
    """P4's seam: `armature_core.gates.G4_TOLERANCE_PX` is the single source of truth, and
    the spec may not move it."""
    monkeypatch.setattr(gates, "G4_TOLERANCE_PX", 3, raising=False)
    tol, source = stage_render.resolve_g4_tolerance(_spec(tmp_path, 3), 832, 480)
    assert tol == 3
    assert source.endswith("G4_TOLERANCE_PX")


def test_the_bound_applies_to_the_gates_own_constant_too(tmp_path, monkeypatch):
    """Ownership is not exemption: a constant that disarms the gate on this frame is
    refused wherever it came from."""
    monkeypatch.setattr(gates, "G4_TOLERANCE_PX", 100000, raising=False)
    spec = make_spec(tmp_path)
    spec.pop("gates", None)
    with pytest.raises(ArmatureError):
        stage_render.resolve_g4_tolerance(spec, 832, 480)


def test_a_spec_that_disagrees_with_the_gates_constant_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(gates, "G4_TOLERANCE_PX", 2, raising=False)
    with pytest.raises(ArmatureError) as e:
        stage_render.resolve_g4_tolerance(_spec(tmp_path, 1), 64, 96)
    assert e.value.evidence["declared"] == 1
    assert e.value.evidence["owned"] == 2


def test_without_a_gate_constant_the_spec_value_is_used_and_still_bounded(tmp_path, monkeypatch):
    monkeypatch.delattr(gates, "G4_TOLERANCE_PX", raising=False)
    tol, source = stage_render.resolve_g4_tolerance(_spec(tmp_path, 2), 64, 96)
    assert tol == 2
    assert source.startswith("spec")


# ------------------------------------------------------------------- what gets recorded


def test_the_manifest_records_the_tolerance_and_where_it_came_from(tmp_path):
    """A loosened run must say so on its face, rather than looking like every other run."""
    manifest = stage_render.run_export(_spec(tmp_path, 2), str(tmp_path / "run"),
                                       backend=FakeBackend(64, 96))
    g4 = manifest["gates"]["G4"]
    assert g4["tolerance_px"] == 2
    assert g4["tolerance_source"]
    assert manifest["spec"]["gates"]["g4_tolerance_px"] == 2


# ------------------------------------------- the direction the gate's own test never took


def test_g4_does_not_fire_on_facets_defect_at_a_loosened_tolerance():
    """Why the bound has to exist at all. This is the failure G4 was written for — facet's
    751-px mask around a 388-px projected mesh — and at 100000 the gate is silent."""
    deltas = gates.g4_bbox_sanity(7, (0, 0, 750, 700), (180, 60, 568, 700), 100000, 752, 752)
    # Measured here rather than quoted: the audit finding described these deltas as
    # [300, 300, 363, 363]; against the fixture `tests/test_gates.py` actually carries they
    # are [180, 60, 182, 0]. The size of the miss is not the point — that a 182-px
    # disagreement passes is.
    assert deltas == [180, 60, 182, 0]


def test_g4_fires_on_facets_defect_at_a_tolerance_this_frame_permits():
    """And the same defect against the largest tolerance a 752x752 frame will now accept."""
    limit = stage_render.g4_tolerance_limit(752, 752)
    with pytest.raises(G4BboxSanity):
        gates.g4_bbox_sanity(7, (0, 0, 750, 700), (180, 60, 568, 700), limit, 752, 752)
