"""The shot spec — E01's other deliverable, and a contract.

A run that cannot be reproduced from its spec is a failed run, so the spec carries
everything needed to reproduce a shot: asset path + sha256, camera path, frame count
and rate, resolution, channels requested, render settings, and the generator profile
whose legality rules apply. The manifest written beside a run records the *resolved*
values (e.g. an `auto` orbit radius resolved to a number) plus the Blender version, so
a replay is exact rather than merely similar.

What the spec may NOT carry: the numeric legality constraints themselves. Those live
in `gates.GENERATOR_PROFILES`. See the note at the top of gates.py.
"""

import copy
import hashlib
import json
import os

from .errors import SpecError

SPEC_VERSION = 1

KNOWN_CHANNELS = ("depth", "normal", "mask", "edge", "pose")

DEFAULTS = {
    "spec_version": SPEC_VERSION,
    "camera": {
        "type": "orbit",
        "target": "bbox_center",
        "radius": "auto",
        "fit_margin": 1.15,
        "elevation_deg": 8.0,
        "azimuth_start_deg": 0.0,
        "azimuth_sweep_deg": 360.0,
        "lens_mm": 50.0,
        "sensor_mm": 36.0,
        "clip_start": 0.05,
        "clip_end": 1000.0,
    },
    "edge": {"depth_rel_threshold": 0.02, "normal_angle_deg": 30.0},
    "render": {
        "engine": "BLENDER_EEVEE",
        "samples": 1,
        "filter_size": 0.01,
        "film_transparent": True,
    },
    "gates": {"g4_tolerance_px": 2},
}


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def _merge(base, override):
    out = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def _require(mapping, key, kind, where):
    if key not in mapping:
        raise SpecError(f"{where}: missing required key {key!r}")
    value = mapping[key]
    if not isinstance(value, kind) or isinstance(value, bool) and kind is not bool:
        raise SpecError(
            f"{where}.{key}: expected {getattr(kind, '__name__', kind)}, "
            f"got {type(value).__name__}"
        )
    return value


def load_spec(path):
    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    return normalise_spec(raw, spec_path=path)


def normalise_spec(raw, spec_path=None):
    """Fill defaults, validate shape, and return a spec dict.

    This does **not** check generator legality — that is G1's job, and G1 runs inside
    the tool that writes, not here. A spec that parses is not a spec that may run.
    """
    if not isinstance(raw, dict):
        raise SpecError("spec must be a JSON object")

    spec = _merge(DEFAULTS, raw)

    version = spec.get("spec_version")
    if version != SPEC_VERSION:
        raise SpecError(f"spec_version {version!r} is not supported (want {SPEC_VERSION})")

    _require(spec, "name", str, "spec")
    _require(spec, "generator", str, "spec")

    asset = _require(spec, "asset", dict, "spec")
    _require(asset, "path", str, "spec.asset")

    res = _require(spec, "resolution", dict, "spec")
    _require(res, "width", int, "spec.resolution")
    _require(res, "height", int, "spec.resolution")

    frames = _require(spec, "frames", dict, "spec")
    _require(frames, "count", int, "spec.frames")
    _require(frames, "fps", int, "spec.frames")

    channels = _require(spec, "channels", list, "spec")
    if not channels:
        raise SpecError("spec.channels is empty; there is nothing to export")
    unknown = [c for c in channels if c not in KNOWN_CHANNELS]
    if unknown:
        raise SpecError(
            f"spec.channels names unknown channel(s) {unknown}; known: {list(KNOWN_CHANNELS)}"
        )
    if len(set(channels)) != len(channels):
        raise SpecError(f"spec.channels contains duplicates: {channels}")

    cam = spec["camera"]
    if cam.get("type") != "orbit":
        raise SpecError(f"spec.camera.type {cam.get('type')!r} is not implemented (only 'orbit')")
    radius = cam.get("radius")
    if radius != "auto" and not isinstance(radius, (int, float)):
        raise SpecError("spec.camera.radius must be a number or the string 'auto'")

    if spec_path:
        spec.setdefault("_spec_path", os.path.abspath(spec_path))
    return spec


def resolve_asset(spec):
    """Resolve the asset path and its sha256, raising if the file is absent.

    If the spec pins a sha256, a mismatch raises: a spec that pins a hash is asserting
    which bytes it was written against, and silently rendering different bytes would
    make the run unreproducible in the one field the spec exists to fix.
    """
    path = os.path.abspath(spec["asset"]["path"])
    if not os.path.isfile(path):
        raise SpecError(f"spec.asset.path does not exist: {path}")
    digest = sha256_file(path)
    pinned = spec["asset"].get("sha256")
    if pinned and pinned != digest:
        raise SpecError(
            f"spec.asset.sha256 pins {pinned} but {path} hashes to {digest}"
        )
    return path, digest


def frame_names(count, ext):
    """Frame file names. Zero-padded so lexical order is temporal order."""
    return [f"{i:05d}.{ext}" for i in range(count)]


def dump_spec(spec, path):
    clean = {k: v for k, v in spec.items() if not k.startswith("_")}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(clean, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return path
