"""The shot spec contract."""

import json

import pytest

from armature_core import shotspec
from armature_core.errors import SpecError


def _minimal(tmp_path):
    asset = tmp_path / "a.glb"
    asset.write_bytes(b"glb")
    return {
        "spec_version": 1,
        "name": "t",
        "generator": "wan-vace",
        "asset": {"path": str(asset)},
        "resolution": {"width": 512, "height": 768},
        "frames": {"count": 33, "fps": 16},
        "channels": ["depth", "mask"],
    }


def test_defaults_are_filled(tmp_path):
    spec = shotspec.normalise_spec(_minimal(tmp_path))
    assert spec["camera"]["type"] == "orbit"
    assert spec["render"]["engine"] == "BLENDER_EEVEE"
    # `gates.g4_tolerance_px` used to be defaulted here. It is not a default any more
    # and not a spec field at all — a number G4 compares against may not arrive
    # through the spec, so the assertion moved to `gates.G4_TOLERANCE_PX` and to
    # `test_a_spec_supplied_g4_tolerance_is_refused` below.
    assert "gates" not in spec


def test_overrides_survive_the_merge(tmp_path):
    raw = _minimal(tmp_path)
    raw["camera"] = {"elevation_deg": 22.0}
    spec = shotspec.normalise_spec(raw)
    assert spec["camera"]["elevation_deg"] == 22.0
    assert spec["camera"]["lens_mm"] == 50.0


def test_round_trip_through_disk_is_identical(tmp_path):
    """A run that cannot be reproduced from its spec is a failed run."""
    spec = shotspec.normalise_spec(_minimal(tmp_path))
    path = tmp_path / "spec.json"
    shotspec.dump_spec(spec, str(path))
    again = shotspec.load_spec(str(path))
    a = {k: v for k, v in spec.items() if not k.startswith("_")}
    b = {k: v for k, v in again.items() if not k.startswith("_")}
    assert a == b


def test_unknown_channel_is_refused(tmp_path):
    raw = _minimal(tmp_path)
    raw["channels"] = ["depth", "flow"]
    with pytest.raises(SpecError) as exc:
        shotspec.normalise_spec(raw)
    assert "flow" in str(exc.value)


def test_duplicate_channel_is_refused(tmp_path):
    raw = _minimal(tmp_path)
    raw["channels"] = ["depth", "depth"]
    with pytest.raises(SpecError,
                       match=r"spec\.channels contains duplicates: \['depth', 'depth'\]"):
        shotspec.normalise_spec(raw)


def test_empty_channels_is_refused(tmp_path):
    raw = _minimal(tmp_path)
    raw["channels"] = []
    with pytest.raises(SpecError,
                       match=r"spec\.channels is empty; there is nothing to export"):
        shotspec.normalise_spec(raw)


def test_bool_is_not_an_int(tmp_path):
    raw = _minimal(tmp_path)
    raw["resolution"]["width"] = True
    with pytest.raises(SpecError, match=r"spec\.resolution\.width: expected int, got bool"):
        shotspec.normalise_spec(raw)


def test_wrong_spec_version_is_refused(tmp_path):
    raw = _minimal(tmp_path)
    raw["spec_version"] = 2
    with pytest.raises(SpecError, match=r"spec_version 2 is not supported \(want 1\)"):
        shotspec.normalise_spec(raw)


def test_unimplemented_camera_type_is_refused(tmp_path):
    raw = _minimal(tmp_path)
    raw["camera"] = {"type": "dolly"}
    # `static` joined `orbit` as an implemented type; the refusal names the known set.
    with pytest.raises(
        SpecError,
        match=r"spec\.camera\.type 'dolly' is not implemented \(known: \['orbit', 'static'\]\)",
    ):
        shotspec.normalise_spec(raw)


def test_asset_hash_is_resolved(tmp_path):
    raw = _minimal(tmp_path)
    # The pin is now required, so this fixture states one. It is measured from the
    # file the fixture just wrote rather than hard-coded, so the test still fails if
    # `resolve_asset` starts returning a digest of something else.
    raw["asset"]["sha256"] = shotspec.sha256_file(raw["asset"]["path"])
    spec = shotspec.normalise_spec(raw)
    path, digest = shotspec.resolve_asset(spec)
    assert len(digest) == 64
    assert shotspec.sha256_file(path) == digest


def test_a_pinned_hash_that_does_not_match_is_refused(tmp_path):
    """A spec that pins a hash asserts which bytes it was written against."""
    spec = shotspec.normalise_spec(_minimal(tmp_path))
    spec["asset"]["sha256"] = "0" * 64
    with pytest.raises(SpecError) as exc:
        shotspec.resolve_asset(spec)
    assert "pins" in str(exc.value)


def test_missing_asset_is_refused(tmp_path):
    raw = _minimal(tmp_path)
    raw["asset"]["path"] = str(tmp_path / "nope.glb")
    spec = shotspec.normalise_spec(raw)
    with pytest.raises(SpecError, match=r"spec\.asset\.path does not exist"):
        shotspec.resolve_asset(spec)


def test_the_spec_cannot_weaken_a_gate(tmp_path):
    """A spec-supplied `dim_divisor` would be a skip flag wearing a schema's clothes.
    The spec may only *name* a generator; the numbers live in gates.py.

    WAVE 22 (core-gates, F-715ecaab): the two keys are now REFUSED rather than accepted
    and ignored. They used to reach `normalise_spec` and survive into the returned spec —
    the gate read gates.py's numbers anyway, so nothing was weakened, but the provenance
    spec then recorded a `dim_divisor` beside the one that was actually used with nothing
    saying which was read. `spec.gates`' own clause already made this argument for one
    key; the unknown-key clause is that argument as the general case. Both halves are
    asserted here: the refusal names them, and with them gone the gate still reads
    gates.py."""
    from armature_core import gates
    from armature_core.errors import G1GeneratorLegality, SpecError

    raw = _minimal(tmp_path)
    raw["generator"] = "wan-vace"
    raw["dim_divisor"] = 1
    raw["generator_profile"] = {"dim_divisor": 1, "frame_modulus": 1, "frame_residue": 0}
    with pytest.raises(SpecError) as exc:
        shotspec.normalise_spec(raw)
    assert exc.value.evidence["clause"] == "unknown_spec_key"
    assert exc.value.evidence["unknown"] == ["dim_divisor", "generator_profile"]

    raw.pop("dim_divisor"), raw.pop("generator_profile")
    spec = shotspec.normalise_spec(raw)
    with pytest.raises(G1GeneratorLegality,
                       match=r"\[G1\] frame is not legal for generator 'wan-vace'"):
        gates.g1_generator_legality(1020, 768, 80, spec["generator"])


def test_frame_names_sort_temporally():
    names = shotspec.frame_names(12, "png")
    assert names == sorted(names)
    assert names[0] == "00000.png" and names[-1] == "00011.png"


# --- W3 amend: the spec may not carry a gate's numbers ----------------------------


@pytest.mark.parametrize("value", [10**9, -5, "off", None, 2])
def test_a_spec_supplied_g4_tolerance_is_refused(tmp_path, value):
    """`gates.py` already rules that a spec-supplied `dim_divisor` is a skip flag
    wearing a schema's clothes. `gates.g4_tolerance_px` was exactly that and was
    validated in no way at all: measured 2026-09-03, 1000000000, -5, 'off' and None
    were every one accepted, and a tolerance of 10**9 passes a mask 5000 px away from
    the subject with G4 green. The number now lives in `gates.G4_TOLERANCE_PX`, so a
    spec that names it is refused rather than obeyed — including one that names the
    same value, because the next edit of that row is the one that matters.
    """
    raw = _minimal(tmp_path)
    raw["gates"] = {"g4_tolerance_px": value}
    with pytest.raises(SpecError) as exc:
        shotspec.normalise_spec(raw)
    assert "g4_tolerance_px" in str(exc.value)
    assert "G4_TOLERANCE_PX" in str(exc.value)


def test_an_unknown_key_under_gates_is_refused_too(tmp_path):
    """The family, not the instance: `spec.gates` is not a place to put numbers."""
    raw = _minimal(tmp_path)
    raw["gates"] = {"g1_dim_divisor": 1}
    with pytest.raises(SpecError, match=r"delete the row from the spec\. \(spec\.gates\.g4_tolerance_px"):
        shotspec.normalise_spec(raw)


def test_the_defaults_no_longer_offer_a_gate_number():
    assert "gates" not in shotspec.DEFAULTS


# --- W3 amend: a spec that pins no hash asserts nothing about its bytes ------------


def test_an_unpinned_asset_is_refused_and_the_error_carries_the_digest(tmp_path):
    """"A run that cannot be reproduced from its spec is a failed run" is this
    module's opening line. Without the pin, the GLB behind the path may change between
    the spec being written and the shot being rendered and nothing in the spec
    contradicts the run. The refusal carries the measured digest so an author pastes
    it rather than computing it."""
    raw = _minimal(tmp_path)
    raw["asset"].pop("sha256", None)
    spec = shotspec.normalise_spec(raw)
    with pytest.raises(SpecError) as exc:
        shotspec.resolve_asset(spec)
    assert "sha256" in str(exc.value)
    assert shotspec.sha256_file(spec["asset"]["path"]) in str(exc.value)


def test_an_empty_pin_is_not_a_pin(tmp_path):
    raw = _minimal(tmp_path)
    raw["asset"]["sha256"] = ""
    spec = shotspec.normalise_spec(raw)
    with pytest.raises(SpecError, match=r"spec\.asset\.sha256 is absent, so this spec asserts nothing"):
        shotspec.resolve_asset(spec)


# --- W6 amend: the refusal is on the KEY, not on its rows (F-5dd933c5) --------------


@pytest.mark.parametrize("block", [{}, {"g4_tolerance_px": 2}, {"g1_dim_divisor": 1}])
def test_the_gates_key_is_refused_whatever_it_contains(tmp_path, block):
    """The loop `for key in sorted(gate_fields): ... raise` can only fire on a NON-EMPTY
    block. Measured 2026-09-03: a spec carrying "gates": {} was ACCEPTED and
    spec["gates"] came back {}, while the same spec with one row raised — so an author
    who emptied the block instead of deleting it got a green spec, and dump_spec
    round-tripped the empty block back out."""
    raw = _minimal(tmp_path)
    raw["gates"] = block
    with pytest.raises(SpecError) as exc:
        shotspec.normalise_spec(raw)
    assert "gates" in str(exc.value)


def test_a_populated_block_still_names_the_retired_keys_new_home(tmp_path):
    raw = _minimal(tmp_path)
    raw["gates"] = {"g4_tolerance_px": 2}
    with pytest.raises(SpecError) as exc:
        shotspec.normalise_spec(raw)
    assert "G4_TOLERANCE_PX" in str(exc.value)


def test_a_gates_key_that_is_not_an_object_is_refused_too(tmp_path):
    raw = _minimal(tmp_path)
    raw["gates"] = []
    with pytest.raises(SpecError,
                       match=r"and it is refused whatever it contains; delete the key"):
        shotspec.normalise_spec(raw)


def test_a_boolean_camera_radius_is_not_a_number(tmp_path):
    """`bool` subclasses `int`, so `radius: true` was accepted as a number and resolved
    to an orbit radius of 1.0. The `target` clause four lines below already carries
    `not isinstance(v, bool)`; the same clause, carried, not re-invented."""
    raw = _minimal(tmp_path)
    raw.setdefault("camera", {})["radius"] = True
    with pytest.raises(SpecError) as exc:
        shotspec.normalise_spec(raw)
    assert "radius" in str(exc.value)


# --- W8 amend: the contract says a spec is well formed, so it checks SIGN (F-7834031b)
#
# `_require(res, "width", int, ...)`, height, `frames.count` and `frames.fps` validated
# TYPE only. Measured 2026-09-04: normalise_spec accepted frames={"count": 0, "fps": 0}
# and frames={"count": -33, "fps": -24} and returned them unchanged. The same function
# already checks sign and ordering elsewhere (depth.window z_min < z_max, camera.radius
# bool-vs-number), so the omission was inconsistent rather than a stated position. A
# zero frame count is caught later by G1 and a zero fps by blender_scene's frame-rate
# andon, so a run fails closed - what was lost is that the refusal came from the render
# layer instead of from the contract that exists to say a spec is well formed, and
# shotspec.frame_names(-33, "png") returns [] in between.


@pytest.mark.parametrize("field,value", [
    ("count", 0), ("count", -1), ("count", -33), ("fps", 0), ("fps", -24)])
def test_a_non_positive_frame_field_is_refused_by_the_contract(tmp_path, field, value):
    raw = _minimal(tmp_path)
    raw.setdefault("frames", {})[field] = value
    with pytest.raises(SpecError) as exc:
        shotspec.normalise_spec(raw)
    assert f"spec.frames.{field}" in str(exc.value)
    assert str(value) in str(exc.value)


@pytest.mark.parametrize("field,value", [
    ("width", 0), ("height", 0), ("width", -16), ("height", -832)])
def test_a_non_positive_resolution_field_is_refused_by_the_contract(tmp_path, field, value):
    raw = _minimal(tmp_path)
    raw.setdefault("resolution", {})[field] = value
    with pytest.raises(SpecError) as exc:
        shotspec.normalise_spec(raw)
    assert f"spec.resolution.{field}" in str(exc.value)


def test_the_positive_values_this_repo_actually_renders_still_pass(tmp_path):
    """The other direction: 1 is the smallest legal frame count and must not be caught
    by the clause that refuses 0."""
    raw = _minimal(tmp_path)
    raw.setdefault("frames", {}).update({"count": 1, "fps": 1})
    raw.setdefault("resolution", {}).update({"width": 1, "height": 1})
    spec = shotspec.normalise_spec(raw)
    assert spec["frames"]["count"] == 1 and spec["resolution"]["width"] == 1


def test_frame_names_is_never_asked_for_a_negative_count_through_the_contract(tmp_path):
    """The consequence the finding names: between the accepted spec and G1,
    `frame_names(-33, "png")` returns [] - an empty plan that reads as 'nothing to
    render' rather than as a malformed spec."""
    assert shotspec.frame_names(-33, "png") == []
    raw = _minimal(tmp_path)
    raw.setdefault("frames", {})["count"] = -33
    with pytest.raises(SpecError, match=r"frames\.count is -33; it must be positive"):
        shotspec.normalise_spec(raw)


# --- W10 amend: the camera block is validated like every other block ------------------


def _with_camera(tmp_path, **cam):
    raw = _minimal(tmp_path)
    raw["camera"] = dict(cam)
    return raw


# F-e920f5a2 — a non-positive orbit radius parses, and a negative one renders the whole
# shot from the opposite side of the subject.


@pytest.mark.parametrize("radius", [0, 0.0, -3.0, -1])
def test_a_non_positive_orbit_radius_is_not_a_spec_that_parses(tmp_path, radius):
    """Measured 2026-09-04: `normalise_spec` accepted `camera={'type':'orbit','radius':0}`
    and `radius: -3.0` and returned them unchanged. `framing.camera_position((0,0,0),
    -3.0, 8.0, 0.0)` is exactly `camera_position((0,0,0), 3.0, -8.0, 180.0)` — azimuth+180
    and elevation negated — a different, perfectly plausible view of the same body, and
    nothing downstream sees it: `stage_render.py:170-174` only does `float(radius)` and a
    `radius + sphere_r >= clip_end` test, which -3.0 passes; G4 compares the mask against
    the projection computed from the SAME wrong camera; G1/G2/G6 are blind to camera
    placement; and the manifest records `camera_radius_resolved: -3.0` beside per-frame
    azimuths that are not the angles the frames were rendered at."""
    raw = _with_camera(tmp_path, type="orbit", radius=radius)
    with pytest.raises(SpecError, match=r"camera\.radius is .*not a distance"):
        shotspec.normalise_spec(raw)


def test_the_two_camera_radius_refusals_in_this_package_accept_the_same_values(tmp_path):
    """The asymmetry was inside one package: `framing.load_pinned_camera` reads the SAME
    quantity back out of a camera record and refuses it — `if not (radius > 0.0): raise
    FramingError(f'{path}: camera.radius is {radius}, which is not a distance')` — while
    the contract that writes it accepted anything non-bool. Pinned as a pair so they
    cannot drift apart again."""
    from armature_core import framing

    # core-solvers is moving `FramingError` into the `ArmatureError` family this wave
    # (wave-10 seam); read through the module so this pin survives that move.
    FramingError = framing.FramingError

    def framing_accepts(radius):
        rec = {"camera": {"target": [0.0, 0.0, 0.0], "radius": radius,
                          "elevation_deg": 8.0}}
        path = tmp_path / f"cam_{radius}.json"
        path.write_text(json.dumps(rec), encoding="utf-8")
        try:
            framing.load_pinned_camera(str(path), {"elevation_deg": 8.0})
        except FramingError as exc:
            assert "not a distance" in str(exc), str(exc)
            return False
        return True

    def spec_accepts(radius):
        try:
            shotspec.normalise_spec(_with_camera(tmp_path, type="orbit", radius=radius))
        except SpecError:
            return False
        return True

    for radius in (3.0, 1, 1e-9, 0, 0.0, -0.0, -1, -3.0):
        assert framing_accepts(radius) == spec_accepts(radius), radius


def test_auto_is_still_the_documented_radius_and_still_parses(tmp_path):
    """`auto` is resolved by the framing solve, not by the spec, so it is the one value
    the positivity clause must not touch — it is also the DEFAULTS value."""
    spec = shotspec.normalise_spec(_with_camera(tmp_path, type="orbit", radius="auto"))
    assert spec["camera"]["radius"] == "auto"
    assert shotspec.DEFAULTS["camera"]["radius"] == "auto"
    assert shotspec.normalise_spec(_minimal(tmp_path))["camera"]["radius"] == "auto"


# F-8382e442 — the camera block's numeric fields got no type check at all.


CAMERA_POSITIVE_FIELDS = ("lens_mm", "sensor_mm", "fit_margin", "clip_start", "clip_end")
CAMERA_ANGLE_FIELDS = ("elevation_deg", "azimuth_start_deg", "azimuth_sweep_deg")


def test_the_camera_field_population_is_the_defaults_block_itself():
    """The node this census keys on is `shotspec.DEFAULTS['camera']` — the block the
    contract fills and round-trips — not a list typed into this file. Every numeric key
    in it is covered by one of the two tables above, so a numeric field added to DEFAULTS
    without a clause fails here."""
    numeric = {k for k, v in shotspec.DEFAULTS["camera"].items()
               if isinstance(v, (int, float)) and not isinstance(v, bool)}
    assert numeric == set(CAMERA_POSITIVE_FIELDS) | set(CAMERA_ANGLE_FIELDS)
    assert set(shotspec.DEFAULTS["camera"]) == (
        numeric | {"type", "target", "radius"})


@pytest.mark.parametrize("field", CAMERA_POSITIVE_FIELDS + CAMERA_ANGLE_FIELDS)
@pytest.mark.parametrize("wrong", ["50", "up", None, True])
def test_every_numeric_camera_field_refuses_a_wrong_type(tmp_path, field, wrong):
    """Measured 2026-09-04, `normalise_spec` ACCEPTED and round-tripped `lens_mm: '50'`
    and `elevation_deg: 'up'`. The consequence is loud and arrives from the wrong layer:
    `framing.project(...)` raises a bare TypeError out of the arithmetic at framing.py:155
    rather than the contract whose stated job is to say a spec is well formed."""
    raw = _with_camera(tmp_path, type="orbit", radius="auto", **{field: wrong})
    with pytest.raises(SpecError, match=rf"camera\.{field}"):
        shotspec.normalise_spec(raw)


@pytest.mark.parametrize("field", CAMERA_POSITIVE_FIELDS)
@pytest.mark.parametrize("wrong", [0, -1, -5.0])
def test_every_positive_camera_quantity_refuses_a_non_positive_value(tmp_path, field,
                                                                     wrong):
    """`sensor_mm: 0` measured: `framing.project(p, target, 3.0, 0.0, 8.0, 50.0, 0.0, 832,
    480)` raises `ZeroDivisionError: division by zero` at framing.py:155. `fit_margin: -1`
    and `clip_start: -5` were accepted too, and `clip_end` is read by `stage_render.py:171`
    as a bound (`radius + sphere_r >= float(c['clip_end'])`), so a negative one turns that
    andon into a check that always fires and is not caught anywhere as malformed."""
    raw = _with_camera(tmp_path, type="orbit", radius="auto", **{field: wrong})
    with pytest.raises(SpecError, match=rf"camera\.{field} is {wrong}"):
        shotspec.normalise_spec(raw)


def test_a_clip_range_that_does_not_open_is_refused_like_the_depth_window(tmp_path):
    """`depth.window` already refuses `z_min >= z_max` at line 248; the clip range is the
    same object and was refused nowhere."""
    raw = _with_camera(tmp_path, type="orbit", radius="auto",
                       clip_start=100.0, clip_end=1.0)
    with pytest.raises(SpecError, match=r"clip_start"):
        shotspec.normalise_spec(raw)
    raw = _with_camera(tmp_path, type="orbit", radius="auto",
                       clip_start=5.0, clip_end=5.0)
    with pytest.raises(SpecError, match=r"clip_start"):
        shotspec.normalise_spec(raw)


def test_the_defaults_camera_block_still_parses_unchanged(tmp_path):
    """The green direction: the block the repo ships is well formed, and an angle may
    still be negative or zero — an elevation of -8 is a camera below the subject, not a
    malformed spec."""
    spec = shotspec.normalise_spec(_minimal(tmp_path))
    assert spec["camera"] == shotspec.DEFAULTS["camera"]
    ok = shotspec.normalise_spec(_with_camera(
        tmp_path, type="orbit", radius=3.0, elevation_deg=-8.0,
        azimuth_start_deg=0, azimuth_sweep_deg=-360.0, lens_mm=35, sensor_mm=36.0,
        fit_margin=1.15, clip_start=0.05, clip_end=1000.0))
    assert ok["camera"]["elevation_deg"] == -8.0 and ok["camera"]["radius"] == 3.0
