"""G4's tolerance is not something this tool can reach — the call site's half of P4.

`run_export` did `g4_tol = spec['gates']['g4_tolerance_px']` and passed it into
`gates.g4_bbox_sanity` with nothing between: no range check, no type check, no record of the
value used. `shotspec.normalise_spec` `_require`d name, generator, asset.path, resolution,
frames, channels and depth.window, and nothing under `gates` — the key was a plain `_merge`
of DEFAULTS with the file.

Measured 2026-09-03: a spec identical to the committed ones except
`"gates": {"g4_tolerance_px": 100000}` was ACCEPTED by `load_spec`, and `g4_bbox_sanity` at
that value did not raise on facet's own recorded defect — a 751-px mask around a 388-px
projected mesh. `inf` behaved the same. Note the asymmetry that kept it invisible: too-SMALL
values (`True`, `-5`) still fired, so the only unbounded direction was the one that DISARMED
the gate — "put the andon on the direction the invariant does not bound", unapplied to G4's
own tolerance.

The number now lives in `gates.G4_TOLERANCE_PX` and `g4_bbox_sanity` takes no tolerance
argument, so this file tests what remains true of the CALLER: it passes no tolerance, it can
no longer be handed one through a spec, and the manifest reads the value and its provenance
back off the gate instead of restating them. The constant's own bounds and the spec refusal
are core-gates' tests.
"""

import inspect
import os

import pytest

import stage_render
from armature_core import gates, shotspec
from armature_core.errors import G4BboxSanity, SpecError
from fake_backend import FakeBackend, make_spec


def _spec(tmp_path, **kw):
    """`make_spec` with the asset digest pinned.

    Pinned here rather than in `fake_backend.make_spec`: that helper is shared with the
    tests domain, and a spec whose asset is unpinned is refused by `normalise_spec`.
    Adding the field is inert against a schema that does not require it.
    """
    spec = make_spec(tmp_path, **kw)
    spec["asset"]["sha256"] = shotspec.sha256_file(spec["asset"]["path"])
    return spec


# ------------------------------------------------------- the caller cannot widen it


def test_the_gate_takes_no_tolerance_argument_from_any_caller():
    """The structural half. A settable tolerance is a skip flag wearing a parameter's
    clothes, and this is the assertion that keeps one from growing back."""
    params = list(inspect.signature(gates.g4_bbox_sanity).parameters)
    assert params == ["frame_index", "mask_bbox", "projected_bbox", "width", "height"]


def test_stage_render_reads_no_gate_number_out_of_the_spec():
    """Read as text rather than behaviour, because the defect was one subscript: any
    reintroduction of `spec['gates'][...]` here puts the dial straight back."""
    src = open(stage_render.__file__, encoding="utf-8").read()
    body = src.split('"""', 2)[-1]           # skip the module docstring, which recounts it
    assert "g4_tolerance_px" not in body
    assert 'spec["gates"]' not in body and "spec['gates']" not in body


def test_a_spec_that_still_carries_the_retired_key_never_renders(tmp_path):
    """End to end through the real write path: the refusal arrives before the backend is
    prepared and before the output directory exists."""
    spec = _spec(tmp_path)
    spec["gates"] = {"g4_tolerance_px": 100000}
    backend = FakeBackend(64, 96, lie_about_bbox=True)

    with pytest.raises(SpecError) as e:
        stage_render.run_export(spec, str(tmp_path / "run"), backend=backend)
    assert "g4_tolerance_px" in str(e.value)
    assert backend.prepared is False
    assert not (tmp_path / "run").exists()


def test_the_retired_key_is_refused_at_every_value_including_the_committed_one(tmp_path):
    """Not "an out-of-range value is refused" — the KEY is refused. A spec carrying the
    old default would otherwise read as blessed while the number it names is inert."""
    for value in (2, 0, -5, True, "off", None, float("inf")):
        spec = _spec(tmp_path)
        spec["gates"] = {"g4_tolerance_px": value}
        with pytest.raises(SpecError):
            shotspec.normalise_spec(spec)


# ------------------------------------------------------------------- what is recorded


def test_the_manifest_quotes_the_tolerance_the_gate_actually_used(tmp_path):
    """Read back off the gate, not restated here: a manifest that names a number the run
    did not check against is a placeholder shaped like evidence."""
    manifest = stage_render.run_export(_spec(tmp_path), str(tmp_path / "run"),
                                       backend=FakeBackend(64, 96))
    g4 = manifest["gates"]["G4"]
    assert g4["verdict"] == "PASS"
    assert g4["tolerance_px"] == gates.G4_TOLERANCE_PX
    assert g4["tolerance_source"] == gates.G4_TOLERANCE_SOURCE
    assert "gates" not in manifest["spec"]


def test_the_per_frame_deltas_are_still_recorded(tmp_path):
    """The record the gate's evidence is read from must survive the signature change."""
    manifest = stage_render.run_export(_spec(tmp_path), str(tmp_path / "run"),
                                       backend=FakeBackend(64, 96))
    assert len(manifest["frames"]) == 9
    assert all(len(r["g4_deltas_px"]) == 4 for r in manifest["frames"])
    assert manifest["gates"]["G4"]["max_delta_px"] is not None


# ---------------------------------------------------- the gate still fires downstream


def test_g4_still_fires_through_the_real_write_path(tmp_path):
    """The guard the other way: none of this may have disarmed the gate it is protecting."""
    with pytest.raises(G4BboxSanity) as e:
        stage_render.run_export(_spec(tmp_path), str(tmp_path / "run"),
                                backend=FakeBackend(64, 96, lie_about_bbox=True))
    assert e.value.evidence["frame"] == 0
    assert e.value.evidence["tolerance_px"] == gates.G4_TOLERANCE_PX


def test_g4_fires_on_facets_own_defect_at_the_constants_value():
    """The failure G4 was written for — facet's 751-px mask around a 388-px projected mesh.
    Measured here rather than quoted: the audit finding described these deltas as
    [300, 300, 363, 363]; against the fixture tests/test_gates.py actually carries they are
    [180, 60, 182, 0]. The size of the miss is not the point — that a 182-px disagreement
    used to pass at a spec-supplied 100000 is."""
    with pytest.raises(G4BboxSanity):
        gates.g4_bbox_sanity(7, (0, 0, 750, 700), (180, 60, 568, 700), 752, 752)
