"""The shot spec — E01's other deliverable, and a contract.

A run that cannot be reproduced from its spec is a failed run, so the spec carries
everything needed to reproduce a shot: asset path + sha256, camera path, frame count
and rate, resolution, channels requested, render settings, and the generator profile
whose legality rules apply. The manifest written beside a run records the *resolved*
values (e.g. an `auto` orbit radius resolved to a number) plus the Blender version, so
a replay is exact rather than merely similar.

What the spec may NOT carry: the numeric legality constraints themselves, nor any
other number a gate compares against. Those live in `gates` — `GENERATOR_PROFILES`
and `G4_TOLERANCE_PX`. See the note at the top of gates.py.

`gates.g4_tolerance_px` was the exception that proved the rule and it is gone. It
shipped as a plain spec field that `normalise_spec` validated in no way: measured
2026-09-03, the values 1000000000, -5, 'off' and None were every one accepted, and
`stage_render` handed whatever arrived straight to G4 — so a spec with one extra zero
rendered and submitted a control sequence whose mask was not the subject, with the
gate green. A spec that still names the key is now REFUSED - the KEY itself, not
a row under it, so an EMPTY `gates` block is refused too - with the constant's new
home in the message when a row is present. No committed spec under `specs/` carries
the key any more.
"""

import copy
import hashlib
import json
import os

from .errors import SpecError
from .parts import require_finite

SPEC_VERSION = 1

KNOWN_CHANNELS = ("depth", "normal", "mask", "edge", "pose")

#: How the subject behaves across the shot. `static` is E01/E02: the scene frame is pinned
#: so only the camera moves. `per_frame` is E03: the scene frame advances with the control
#: frame, so an action carried by the asset performs — and G6 checks that it actually did.
ANIMATION_MODES = ("static", "per_frame")

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
    # E01/E02 render an existing pose while the camera moves; E03 renders a performance.
    # The default `static` reproduces E01's behaviour exactly — the scene frame stays
    # pinned at 1, so an asset carrying an action cannot move the subject. Opting in is
    # explicit because the opt-in ALSO arms G6: a spec saying `per_frame` is asserting the
    # subject performs, and G6 halts the run if it turns out it did not.
    "subject": {"animation": "static"},
    # The depth normalisation window. `per_shot` is E01/E02's behaviour: the shot's own
    # measured z extent maps to 0..255. A two-number window pins it instead, which is what
    # lets two arms share one tonal scale — see the note in `normalise_spec`.
    "depth": {"window": "per_shot"},
    "edge": {"depth_rel_threshold": 0.02, "normal_angle_deg": 30.0},
    "render": {
        "engine": "BLENDER_EEVEE",
        "samples": 1,
        "filter_size": 0.01,
        "film_transparent": True,
    },
}

#: Keys that used to live under `spec.gates` and now do not. A spec naming one is
#: refused rather than obeyed — see `normalise_spec`. Kept as data so the refusal can
#: name where the number went.
RETIRED_GATE_KEYS = {
    "g4_tolerance_px": "gates.G4_TOLERANCE_PX",
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
        named = (kind.__name__ if isinstance(kind, type)
                 else " or ".join(k.__name__ for k in kind))
        raise SpecError(
            f"{where}.{key}: expected {named}, got {type(value).__name__}"
        )
    return value


def _require_positive(mapping, key, where, note=None):
    """A count, a rate or a pixel dimension is a POSITIVE number, and the type test
    alone did not say so.

    Measured 2026-09-04: `normalise_spec` accepted `frames={"count": 0, "fps": 0}` and
    `frames={"count": -33, "fps": -24}` and returned them unchanged. This function
    already checks sign and ordering elsewhere — `depth.window` requires z_min < z_max,
    `camera.radius` refuses a bool — so the omission was inconsistent rather than a
    stated position. A zero frame count is caught later by G1 ("frame count must be
    positive") and a zero fps by `blender_scene.import_glb`'s frame-rate andon, so a run
    fails closed either way; what was missing is that the refusal came from the render
    layer instead of from the contract whose whole job is to say a spec is well formed,
    and `frame_names(-33, "png")` returns `[]` in between — an empty plan that reads as
    "nothing to render" rather than as a malformed spec.

    ⚠ **The camera block was outside it until 2026-09-04**, though this docstring's own
    argument covers it word for word. Measured: `normalise_spec` accepted and
    round-tripped `lens_mm: '50'`, `elevation_deg: 'up'`, `sensor_mm: 0`,
    `fit_margin: -1`, `clip_start: -5` with `clip_end: -1`, and `radius: -3.0`. `note`
    exists for the radius, whose refusal is worded the way `framing.load_pinned_camera`
    words the same refusal on the same quantity read back out of a record.
    """
    value = mapping[key]
    # · The positivity clause was `value <= 0`, and that comparison is **False for NaN** —
    # so every non-finite camera number was accepted and round-tripped. Measured
    # 2026-09-04: `normalise_spec` accepted and returned unchanged `camera.lens_mm = nan`,
    # `lens_mm = inf`, `sensor_mm = nan`, `fit_margin = nan` and `radius = nan` (only
    # `clip_start = nan` was caught, and by the separate `clip_start < clip_end` ordering
    # clause, not by this one). `require_finite` runs the finiteness test FIRST and the
    # sign test after, exactly as `parts.tightened` does — it is the repo's one non-finite
    # helper (wave 10's rule 4) and this module had no caller of it, which is why a class
    # of malformed value the helper exists to refuse reached a file this module's opening
    # line calls a contract.
    # `positive=False` here on purpose: the finiteness half is what was missing, and the
    # sign half keeps the words it already had, so a plain 0 or -33 is refused with the
    # message this function has always given it.
    _require_finite_number(mapping, key, where, note=note, positive=False)
    if value <= 0:
        raise SpecError(
            f"{where}.{key} is {value}" + (f", {note}" if note else "")
            + f"; it must be positive. A spec that parses is not "
            f"a spec that may run, but a non-positive count, rate or dimension is not a "
            f"spec that parses either"
        )
    return value


def _require_finite_number(mapping, key, where, note=None, positive=False):
    """`mapping[key]` is a number a gate can compare against, or `SpecError`.

    Routed through `parts.require_finite` — the repo's ONE implementation of "a verdict on
    a non-finite number is a refusal, never a PASS" — so this module does not grow a second
    `math.isfinite` with a different message. `positive=False` bounds finiteness only, for
    the angles: an elevation of -8 is a camera below the subject and a sweep of -360 is an
    orbit the other way, so sign is not the question there; **finiteness still is**, because
    `dump_spec` would otherwise write `NaN` for an angle exactly as it did for a lens.
    """
    # `gate: None` + `andon` is the receipt shape a PLAIN refusal carries in this tree (the
    # convention core-solvers is extending across walk/framing/glb this wave): SpecError is
    # not a gate, so it names no gate id, and it says so rather than omitting the key.
    ev = {"gate": None, "andon": "SpecError", "spec_field": f"{where}.{key}"}
    try:
        return require_finite(f"{where}.{key}", mapping[key], SpecError, ev,
                              positive=positive)
    except SpecError as err:
        # WAVE-12 MERGE (coordinator, 2026-09-04): the re-raise dropped `ev` (tests' no-evidence census found
        # the one site in the package raising with no receipt); the helper's evidence rides the raise.
        raise SpecError(
            f"{where}.{key} is {mapping[key]!r}" + (f", {note}" if note else "")
            + f"; it must be a finite number. {err.args[0] if err.args else ''}",
            ev,
        ) from None


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

    # A number a gate compares against may not arrive through the spec. gates.py makes
    # this argument for `dim_divisor` in its own opening lines; `g4_tolerance_px` was
    # the same flag wearing a schema's clothes, and unlike `dim_divisor` it was actually
    # wired — `stage_render` read it and handed it to G4 unvalidated.
    #
    # The refusal is on the KEY's PRESENCE, not on its rows. It used to be
    # `for key in sorted(gate_fields): ... raise`, which can only fire on a NON-EMPTY
    # block: measured 2026-09-03, a spec carrying `"gates": {}` was ACCEPTED and
    # `spec["gates"]` came back {}, while the same spec with one row raised. The module
    # docstring states the rule without that qualifier — "A spec that still names the key
    # is now REFUSED" — and the refusal message tells the author to "delete the row from
    # the spec", so an author who emptied the block instead of deleting it got a green
    # spec and `dump_spec` round-tripped the empty block back out. `spec.gates` stayed
    # alive as an accepted schema surface, and the next key added under it would only be
    # refused if a value happened to be present.
    if "gates" in raw:
        gate_fields = raw.get("gates")
        if not isinstance(gate_fields, dict):
            raise SpecError("spec.gates must be an object — and it is refused whatever "
                            "it contains; delete the key")
        if not gate_fields:
            raise SpecError(
                "spec.gates is refused even when it is EMPTY: the key itself is the "
                "retired schema surface, and an empty block that round-trips back out "
                "is the next number's home. Delete the key. "
                f"(Known retired keys and their new homes: {sorted(RETIRED_GATE_KEYS)}; "
                "g4_tolerance_px now lives in gates.G4_TOLERANCE_PX)"
            )
        for key in sorted(gate_fields):
            home = RETIRED_GATE_KEYS.get(key)
            raise SpecError(
                f"spec.gates.{key} is refused: a number a gate compares against is a "
                f"skip flag wearing a schema's clothes"
                + (f". It now lives in {home}" if home
                   else f". Known retired keys: {sorted(RETIRED_GATE_KEYS)}")
                + " — delete the row from the spec. (spec.gates.g4_tolerance_px used to "
                  "be read by stage_render and handed to G4 unvalidated; the constant is "
                  "gates.G4_TOLERANCE_PX)"
            )

    asset = _require(spec, "asset", dict, "spec")
    _require(asset, "path", str, "spec.asset")

    res = _require(spec, "resolution", dict, "spec")
    _require(res, "width", int, "spec.resolution")
    _require(res, "height", int, "spec.resolution")
    _require_positive(res, "width", "spec.resolution")
    _require_positive(res, "height", "spec.resolution")

    frames = _require(spec, "frames", dict, "spec")
    _require(frames, "count", int, "spec.frames")
    _require(frames, "fps", int, "spec.frames")
    _require_positive(frames, "count", "spec.frames")
    _require_positive(frames, "fps", "spec.frames")

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

    # A pinned depth window exists so two arms can share one tonal scale.
    #
    # E03's B1 and B3 render the SAME asset and differ only in whether the timeline
    # advances — but per-shot normalisation is computed from each shot's own z extent, and
    # the raised arm widens B1's extent by 11%. Measured: B1's frame 0 and B3's frames hold
    # identical geometry and still differed by up to 26 of 255 levels. That is a second
    # difference between the arms, and B3 is the discriminator, so it must differ from B1 in
    # exactly one thing. Pinning the window to B1's measured extent removes it.
    depth = _require(spec, "depth", dict, "spec")
    window = depth.get("window")
    if window != "per_shot":
        if (not isinstance(window, (list, tuple)) or len(window) != 2
                or not all(isinstance(v, (int, float)) and not isinstance(v, bool)
                           for v in window)):
            raise SpecError(
                "spec.depth.window must be 'per_shot' or a 2-number [z_min, z_max]"
            )
        if not window[0] < window[1]:
            raise SpecError(
                f"spec.depth.window is [{window[0]}, {window[1]}]; z_min must be below "
                f"z_max or the normalisation collapses"
            )

    subject = _require(spec, "subject", dict, "spec")
    animation = subject.get("animation")
    if animation not in ANIMATION_MODES:
        # Not a soft default: silently falling back to `static` would render 33 identical
        # frames for a spec that asked for a performance, and G6 would never be armed
        # because the mode it keys on never arrived.
        raise SpecError(
            f"spec.subject.animation {animation!r} is not one of {list(ANIMATION_MODES)}"
        )

    cam = spec["camera"]
    if cam.get("type") != "orbit":
        raise SpecError(f"spec.camera.type {cam.get('type')!r} is not implemented (only 'orbit')")
    radius = cam.get("radius")
    # `bool` is a subclass of `int`, so `radius: true` was accepted as a number and
    # resolved to an orbit radius of 1.0. The `target` clause immediately below already
    # carries `not isinstance(v, bool)`; the same clause, not a second mechanism.
    if radius != "auto" and (not isinstance(radius, (int, float))
                             or isinstance(radius, bool)):
        raise SpecError("spec.camera.radius must be a number or the string 'auto'")

    # `target` may be pinned numerically as well as derived. E03 needs this: its animated
    # arm fits the camera to the union of every frame while its static arm fits the bind
    # pose, so leaving both on `bbox_center` would frame the two arms DIFFERENTLY — and the
    # static arm is the discriminator, which must differ from the animated one in exactly
    # one thing. Pinning both target and radius makes the framing identical by construction
    # rather than identical by coincidence.
    target = cam.get("target")
    if target != "bbox_center":
        if (not isinstance(target, (list, tuple)) or len(target) != 3
                or not all(isinstance(v, (int, float)) and not isinstance(v, bool)
                           for v in target)):
            raise SpecError(
                "spec.camera.target must be 'bbox_center' or a 3-number [x, y, z]"
            )

    # An orbit RADIUS is a distance, and a non-positive one is not a spec that parses.
    #
    # ⚠ Measured 2026-09-04: `camera={'type':'orbit','radius':-3.0}` was accepted and
    # returned unchanged, and it renders the whole shot from the opposite side of the
    # subject — `framing.camera_position((0,0,0), -3.0, 8.0, 0.0)` is exactly
    # `camera_position((0,0,0), 3.0, -8.0, 180.0)`, azimuth+180 and elevation negated.
    # Nothing downstream sees it: `stage_render.py:170-174` only does `float(radius)` and
    # a `radius + sphere_r >= clip_end` test, which -3.0 passes; G4 compares the mask
    # against the projection computed from the SAME wrong camera so the deltas agree;
    # G1/G2/G6 are blind to camera placement; and the manifest then records
    # `camera_radius_resolved: -3.0` beside per-frame azimuths that are not the angles the
    # frames were rendered at — a recipe that does not reproduce its output, every gate
    # green. The asymmetry was inside this package: `framing.load_pinned_camera`
    # (framing.py:203-204) reads the SAME quantity back out of a camera record and refuses
    # it, in the words reused here.
    if radius != "auto":
        _require_positive(cam, "radius", "spec.camera", note="which is not a distance")

    # The rest of the camera block's numbers. `_require` was called on name, generator,
    # asset.path, resolution.width/height and frames.count/fps — and on nothing under
    # `camera` except `type` (a string equality), `target` (shape) and `radius`
    # (bool-ness). Measured 2026-09-04, every one of these was accepted and round-tripped:
    # `lens_mm: '50'`, `elevation_deg: 'up'`, `sensor_mm: 0`, `fit_margin: -1`,
    # `clip_start: -5` with `clip_end: -1`. The consequences are loud rather than silent
    # and that is the objection: `framing.project(p, target, 3.0, 0.0, 8.0, 50.0, 0.0,
    # 832, 480)` with `sensor_mm=0` raises `ZeroDivisionError: division by zero` at
    # framing.py:155 and a string `lens_mm` a bare `TypeError` out of the same arithmetic,
    # so the refusal arrives from the render layer rather than from the contract whose
    # stated job is to say a spec is well formed.
    #
    # The split is the one `_require_positive`'s docstring draws: a lens, a sensor, a fit
    # margin and a clip plane are POSITIVE quantities; an angle is not — an elevation of
    # -8 is a camera below the subject and a sweep of -360 is an orbit the other way.
    for key in ("lens_mm", "sensor_mm", "fit_margin", "clip_start", "clip_end"):
        _require(cam, key, (int, float), "spec.camera")
        _require_positive(cam, key, "spec.camera")
    for key in ("elevation_deg", "azimuth_start_deg", "azimuth_sweep_deg"):
        _require(cam, key, (int, float), "spec.camera")
        # The angles are the rest of the family. Sign is not the question here — an
        # elevation of -8 is a camera below the subject — but FINITENESS is, and it was
        # unchecked on these three for exactly the reason it was unchecked on the five
        # above: the type test says `float` and `float('nan')` is a float.
        _require_finite_number(cam, key, "spec.camera", positive=False)

    # The same clause `depth.window` already writes for z_min/z_max. `clip_end` is read by
    # `stage_render.py:171` as a bound (`radius + sphere_r >= float(c['clip_end'])`), so a
    # range that does not open turns that andon into a check that always fires, and
    # nothing anywhere catches it as a malformed value.
    if not cam["clip_start"] < cam["clip_end"]:
        raise SpecError(
            f"spec.camera.clip_start is {cam['clip_start']} and clip_end is "
            f"{cam['clip_end']}; the near plane must be in front of the far one or the "
            f"camera has no depth range at all"
        )

    if spec_path:
        spec.setdefault("_spec_path", os.path.abspath(spec_path))
    return spec


def resolve_asset(spec):
    """Resolve the asset path and its sha256, raising if the file is absent.

    The spec MUST pin a sha256, and a mismatch raises. A spec that pins a hash is
    asserting which bytes it was written against; a spec that pins none asserts
    nothing, and the GLB behind the path may change between the spec being written
    and the shot being rendered with nothing in the spec to contradict the run. The
    manifest would still record the digest actually used — what an unpinned spec
    loses is not the run record's honesty but the spec's ability to say which bytes
    it meant. That is the one field this module exists to fix.

    The refusal carries the measured digest so an author pastes it instead of
    computing it.
    """
    path = os.path.abspath(spec["asset"]["path"])
    if not os.path.isfile(path):
        raise SpecError(f"spec.asset.path does not exist: {path}")
    digest = sha256_file(path)
    pinned = spec["asset"].get("sha256")
    if not pinned:
        raise SpecError(
            f"spec.asset.sha256 is absent, so this spec asserts nothing about the "
            f"bytes it was written against. {path} hashes to {digest} — paste that "
            f"into spec.asset.sha256"
        )
    if pinned != digest:
        raise SpecError(
            f"spec.asset.sha256 pins {pinned} but {path} hashes to {digest}"
        )
    return path, digest


def frame_names(count, ext):
    """Frame file names. Zero-padded so lexical order is temporal order."""
    return [f"{i:05d}.{ext}" for i in range(count)]


def dump_spec(spec, path):
    """Write a spec file. `allow_nan=False`, which is not the stdlib default.

    ⚠ **`json.dump` writes the bare token `NaN` by default, and `json.load` reads it back.**
    Measured 2026-09-04, before `_require_positive` grew its finiteness clause: a spec whose
    `camera.lens_mm` was NaN was accepted by `normalise_spec`, written here as the literal
    line `"lens_mm": NaN,` and read back as nan by `normalise_spec(json.load(...))` — a full
    write/read round trip of the file this module's opening line calls a contract, leaving a
    file in `specs/**` that is **not RFC-8259 JSON**: any non-Python reader (a CI step, jq,
    the site) fails on it. The loader clause is the first defence and this is the second, on
    the direction the loader does not bound: a spec dict a caller mutated in memory after
    `normalise_spec` returned never passes the loader again on its way to disk. `ValueError`
    from here is the honest refusal — a non-finite value cannot reach a spec file at all.
    """
    clean = {k: v for k, v in spec.items() if not k.startswith("_")}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(clean, fh, indent=2, sort_keys=True, allow_nan=False)
        fh.write("\n")
    return path
