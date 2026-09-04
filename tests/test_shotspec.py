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
    with pytest.raises(SpecError, match=r"spec\.camera\.type 'dolly' is not implemented \(only 'orbit'\)"):
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
    The spec may only *name* a generator; the numbers live in gates.py."""
    from armature_core import gates
    from armature_core.errors import G1GeneratorLegality

    raw = _minimal(tmp_path)
    raw["generator"] = "wan-vace"
    raw["dim_divisor"] = 1
    raw["generator_profile"] = {"dim_divisor": 1, "frame_modulus": 1, "frame_residue": 0}
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
