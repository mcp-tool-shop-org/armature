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
    assert spec["gates"]["g4_tolerance_px"] == 2


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
    with pytest.raises(SpecError):
        shotspec.normalise_spec(raw)


def test_empty_channels_is_refused(tmp_path):
    raw = _minimal(tmp_path)
    raw["channels"] = []
    with pytest.raises(SpecError):
        shotspec.normalise_spec(raw)


def test_bool_is_not_an_int(tmp_path):
    raw = _minimal(tmp_path)
    raw["resolution"]["width"] = True
    with pytest.raises(SpecError):
        shotspec.normalise_spec(raw)


def test_wrong_spec_version_is_refused(tmp_path):
    raw = _minimal(tmp_path)
    raw["spec_version"] = 2
    with pytest.raises(SpecError):
        shotspec.normalise_spec(raw)


def test_unimplemented_camera_type_is_refused(tmp_path):
    raw = _minimal(tmp_path)
    raw["camera"] = {"type": "dolly"}
    with pytest.raises(SpecError):
        shotspec.normalise_spec(raw)


def test_asset_hash_is_resolved(tmp_path):
    spec = shotspec.normalise_spec(_minimal(tmp_path))
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
    with pytest.raises(SpecError):
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
    with pytest.raises(G1GeneratorLegality):
        gates.g1_generator_legality(1020, 768, 80, spec["generator"])


def test_frame_names_sort_temporally():
    names = shotspec.frame_names(12, "png")
    assert names == sorted(names)
    assert names[0] == "00000.png" and names[-1] == "00011.png"
