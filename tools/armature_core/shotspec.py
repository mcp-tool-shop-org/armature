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

#: Channels a shot may export. Legacy five plus the authored geometric layouts that
#: `channels.CHANNEL_CONVENTIONS` names (`softedge` / `canny` / `flow` — NOT partner
#: HED / OpenCV Canny / flow weights). The convention digests live in `channels`; this
#: tuple is the shotspec vocabulary. Import-time pin below keeps the three names from
#: drifting off the convention table (F-98515e19).
KNOWN_CHANNELS = (
    "depth", "normal", "mask", "edge", "pose",
    "softedge", "canny", "flow",
)

#: Camera models this contract accepts. `orbit` is the E01 turntable. `static` is a
#: locked-off camera — `azimuth_sweep_deg` defaults to 0 and a non-zero sweep is refused
#: (F-2f2da5bb); consumers must honour `type` or the zeroed sweep (stage_render is
#: OUT-OF-DOMAIN). `path` / `track` are keyframed cameras whose `keys` match
#: `framing.normalize_camera_keys` (F-c3778bcf); framing already solves them. Unknown
#: names stay refused so a typo cannot silently fall through to orbit defaults.
KNOWN_CAMERA_TYPES = ("orbit", "static", "path", "track")

#: Keyframe fields `path` / `track` require on every `camera.keys` entry — the same
#: shape `framing.normalize_camera_keys` reads. Validated here so a typo refuses at
#: schema load rather than inside the framing solver mid-render.
CAMERA_PATH_KEY_FIELDS = (
    "frame", "azimuth_deg", "elevation_deg", "radius", "target",
)
#: The render engines a spec may name. `blender_scene.configure_render` assigns
#: `scene.render.engine = r["engine"]` verbatim, so an unknown identifier is refused by
#: Blender's own RNA with a `TypeError` from inside the render layer — the loud-not-silent
#: shape this contract exists to answer BEFORE the tool that writes is entered. Both EEVEE
#: spellings are here because Blender renamed it between versions and five tools in this
#: tree carry an `ENGINE_CANDIDATES = ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE")` loop for
#: exactly that reason; refusing the newer name would refuse a spec those tools can run.
KNOWN_ENGINES = ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT", "CYCLES", "BLENDER_WORKBENCH")

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

#: The keys each block of a spec may carry — the schema, as DATA, so a refusal can name
#: what the block does hold. One row per mapping block `normalise_spec` reads; a block with
#: no row would be a level checked at its parent and nowhere else.
#:
#: ⚠ **`normalise_spec` validated the keys it knew and ACCEPTED every key it did not, at
#: every level, and `dump_spec` then wrote them back into the provenance spec.** Measured
#: 2026-09-05 against a minimal valid spec: an unknown TOP-LEVEL key (`cammera`), and
#: unknown keys inside `spec.camera` (`fov_degrees`), `spec.resolution` (`depth`),
#: `spec.frames` (`framerate`) and `spec.render` (`engien`) were each ACCEPTED and each
#: survived into the returned spec. Round-tripped: with `camera.fov_degrees = 90.0`
#: alongside `camera.fov_deg = 35.0`, `dump_spec` wrote a camera block carrying BOTH, and
#: the value the solvers read is `spec["camera"]["fov_deg"]`.
#:
#: This module answered that question in exactly two places and nowhere else —
#: `spec.channels` refuses an unknown VALUE ("names unknown channel(s)") and `spec.gates`
#: refuses the retired KEY even when the block is empty, on the stated ground that "the key
#: itself is the retired schema surface, and an empty block that round-trips back out is
#: the next number's home". That argument is the general case and it was applied to one
#: key. An operator's typo — `fov_degrees`, `framerate`, `frame_count` — was accepted, the
#: render was taken at the module default instead, and the provenance spec recorded the
#: ignored field beside the used one with nothing saying which was read: a recipe that does
#: not reproduce its output.
SPEC_KEYS = {
    "spec": ("asset", "camera", "channels", "depth", "edge", "frames", "generator",
             "name", "render", "resolution", "spec_version", "subject"),
    # `note` is the schema's, not an author's stray: all five committed specs under
    # `specs/**` carry `asset.note`, and it is the one annotation field that is not
    # `_`-prefixed. Recorded here rather than tolerated by silence.
    "spec.asset": ("note", "path", "sha256"),
    "spec.resolution": ("height", "width"),
    "spec.frames": ("count", "fps"),
    "spec.camera": ("azimuth_start_deg", "azimuth_sweep_deg", "clip_end", "clip_start",
                    "elevation_deg", "fit_margin", "keys", "lens_mm", "radius", "sensor_mm",
                    "target", "type"),
    "spec.subject": ("animation",),
    "spec.depth": ("window",),
    "spec.edge": ("depth_rel_threshold", "normal_angle_deg"),
    "spec.render": ("engine", "film_transparent", "filter_size", "samples"),
}

#: The ONE named passthrough. Forward compatibility has a shape here rather than being
#: "anything the schema did not recognise": a key beginning with `_` is an annotation, it
#: is what the five committed specs already use (`_notes`), and `dump_spec` already strips
#: it on write (`if not k.startswith("_")`). Which ones a spec carried is RECORDED on the
#: returned spec under `_passthrough_keys`, so a reader can tell the fields the schema did
#: not read from the fields it did.
PASSTHROUGH_PREFIX = "_"

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


def _refuse(message, evidence):
    """This module's ONE andon, in the shape `canon._raise` and `canon_census._refuse` use.

    ⚠ **23 of this module's 25 refusals raised with NO evidence dict at all**, so the halt
    line an operator keys on printed `"evidence": null` for every refusal about the asset
    each control render is built from. Measured 2026-09-05 in this worktree on `580af47`:
    of 25 `raise SpecError(...)` sites exactly TWO passed a second argument, and
    `resolve_asset({'asset': {'path': <a real file>, 'sha256': 'deadbeef'}})` raised with
    `evidence is None` — the halt record reading `{"error": "SpecError", "message":
    "spec.asset.sha256 pins deadbeef but … hashes to …", "evidence": null}` for the ONE
    field this module's docstring says it exists to fix.

    `errors.ArmatureError`'s own docstring rules that a null is "the honest record for
    `raise ArmatureError("unknown --mode=wobble")`" — a plain refusal that HAS no receipt —
    and that "a refusal still names a class with a `clause` or a `gate`". These refusals
    HAVE a receipt to give (the pinned digest and the measured one, the path, the key, the
    accepted vocabulary) and gave none.

    The module was consequently absent from the census that would have noticed:
    `tests/test_core_solver_evidence.py`'s per-module table is keyed on
    `GateFailure`-subclass raises, and `SpecError` is a plain `ArmatureError`; the
    family-wide judge (`tests/test_gates.evidence_dicts_missing`) counted this module's
    four functions in `no_evidence` and `EVIDENCE_NO_EVIDENCE_ROUTED` carried them as a
    routed exemption. All four leave in the commit that adds this helper.

    `gate: None` + `andon` is the receipt shape a PLAIN refusal carries in this tree:
    `SpecError` is not a gate, so it names no gate id and SAYS so rather than omitting the
    key.
    """
    raise SpecError(message, dict(evidence, gate=None, andon="SpecError"))


def _require(mapping, key, kind, where):
    if key not in mapping:
        _refuse(f"{where}: missing required key {key!r}", {'clause': 'missing_spec_key',
                                                           'where': where, 'key': key,
                                                           'present_keys': sorted(map(str, mapping))})
    value = mapping[key]
    if not isinstance(value, kind) or isinstance(value, bool) and kind is not bool:
        named = (kind.__name__ if isinstance(kind, type)
                 else " or ".join(k.__name__ for k in kind))
        _refuse(
            f"{where}.{key}: expected {named}, got {type(value).__name__}",
            {'clause': 'spec_value_wrong_type', 'where': where, 'key': key,
             'expected': named, 'got': type(value).__name__, 'value': repr(value)}
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
        _refuse(
            f"{where}.{key} is {value}" + (f", {note}" if note else "")
            + f"; it must be positive. A spec that parses is not "
            f"a spec that may run, but a non-positive count, rate or dimension is not a "
            f"spec that parses either",
            {'clause': 'spec_value_not_positive', 'where': where, 'key': key,
             'value': value, 'note': note}
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
    # WAVE 25 (F-b333ba7c): `clause` joined this literal. It was the ONE site in the module
    # already carrying a receipt AND the one `evidence_dicts_missing('clause')` named as
    # this file's offender — a receipt with a gate id slot and no clause word, which is the
    # key a halt reader branches on.
    ev = {"gate": None, "andon": "SpecError", "clause": "spec_value_not_finite",
          "spec_field": f"{where}.{key}", "where": where, "key": key,
          "value": repr(mapping[key]), "note": note}
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


def _refuse_unknown_keys(spec):
    """ANDON — every key in every block is one `SPEC_KEYS` names, or `SpecError`.

    Returns `{block: [passthrough keys]}` for the `_`-prefixed annotations it admitted, so
    the caller can record them. Blocks that are not mappings are left alone: `_require`
    states the ONE refusal for a wrong-typed block, and two clauses answering the same
    question in different words is what this module already refuses to grow (see
    `_require_finite_number`).

    `spec.gates` is deliberately NOT in `SPEC_KEYS`: it has its own clause above, which
    runs first and names where each retired number went. A generic "unknown key" message
    there would lose that.
    """
    passthrough = {}
    for where, known in SPEC_KEYS.items():
        block = spec
        if where != "spec":
            block = spec.get(where.split(".", 1)[1])
        if not isinstance(block, dict):
            continue
        through = sorted(k for k in block
                         if isinstance(k, str) and k.startswith(PASSTHROUGH_PREFIX))
        if through:
            passthrough[where] = through
        unknown = sorted(str(k) for k in block
                         if str(k) not in known
                         and not str(k).startswith(PASSTHROUGH_PREFIX)
                         and not (where == "spec" and str(k) == "gates"))
        if unknown:
            _refuse(
                f"{where} carries {unknown!r}, which this schema has no reader for; the "
                f"keys of {where} are {list(known)}. An unknown key is not a spec with an "
                f"extra field — the value is IGNORED, the shot is taken at the module "
                f"default, and `dump_spec` writes the ignored field back into the "
                f"provenance spec beside the used one with nothing saying which was read. "
                f"A recipe that does not reproduce its output is not a recipe. For a note "
                f"the schema should not read, prefix the key with "
                f"{PASSTHROUGH_PREFIX!r} — that is what `specs/**` already does and what "
                f"`dump_spec` already strips",
                {'clause': 'unknown_spec_key', 'where': where, 'unknown': unknown,
                 'known_keys': list(known), 'passthrough_prefix': PASSTHROUGH_PREFIX}
            )
    return passthrough


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
        _refuse("spec must be a JSON object", {'clause': 'spec_is_not_an_object',
                                               'type': type(raw).__name__,
                                               'value': repr(raw)[:200]})

    spec = _merge(DEFAULTS, raw)

    version = spec.get("spec_version")
    if version != SPEC_VERSION:
        _refuse(f"spec_version {version!r} is not supported (want {SPEC_VERSION})",
                {'clause': 'spec_version_unsupported', 'version': repr(version),
                 'supported': SPEC_VERSION})

    _require(spec, "name", str, "spec")
    generator = _require(spec, "generator", str, "spec")
    # Name check only — dimensions still belong to G1 at write time. The vocabulary is
    # the union of G1 profiles and Gate L family rows so a shotspec cannot parse green
    # on a generator neither gate knows (F-a9e809dd). Lazy imports: `gates` imports
    # `ANIMATION_MODES` from this module at load time.
    from .gates import GENERATOR_PROFILES
    from .route_gates import GENERATOR_RULES
    known_generators = sorted(set(GENERATOR_PROFILES) | set(GENERATOR_RULES))
    if generator not in GENERATOR_PROFILES and generator not in GENERATOR_RULES:
        _refuse(
            f"spec.generator {generator!r} is not in the unified generator table "
            f"(G1 profiles + Gate L families); known: {known_generators}",
            {'clause': 'generator_unknown', 'where': 'spec', 'key': 'generator',
             'value': repr(generator), 'known_generators': known_generators}
        )

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
            _refuse("spec.gates must be an object — and it is refused whatever "
                    "it contains; delete the key", {'clause': 'retired_gates_block',
                                                    'where': 'spec.gates',
                                                    'got': type(gate_fields).__name__,
                                                    'value': repr(gate_fields)[:200],
                                                    'retired_keys': sorted(RETIRED_GATE_KEYS)})
        if not gate_fields:
            _refuse(
                "spec.gates is refused even when it is EMPTY: the key itself is the "
                "retired schema surface, and an empty block that round-trips back out "
                "is the next number's home. Delete the key. "
                f"(Known retired keys and their new homes: {sorted(RETIRED_GATE_KEYS)}; "
                "g4_tolerance_px now lives in gates.G4_TOLERANCE_PX)",
                {'clause': 'retired_gates_block', 'where': 'spec.gates', 'got': 'dict',
                 'value': '{}', 'retired_keys': sorted(RETIRED_GATE_KEYS)}
            )
        for key in sorted(gate_fields):
            home = RETIRED_GATE_KEYS.get(key)
            _refuse(
                f"spec.gates.{key} is refused: a number a gate compares against is a "
                f"skip flag wearing a schema's clothes"
                + (f". It now lives in {home}" if home
                   else f". Known retired keys: {sorted(RETIRED_GATE_KEYS)}")
                + " — delete the row from the spec. (spec.gates.g4_tolerance_px used to "
                  "be read by stage_render and handed to G4 unvalidated; the constant is "
                  "gates.G4_TOLERANCE_PX)",
                {'clause': 'retired_gates_key', 'where': 'spec.gates', 'key': key,
                 'value': repr(gate_fields[key]), 'new_home': home,
                 'retired_keys': sorted(RETIRED_GATE_KEYS)}
            )

    # · ANDON — the KEYS, before any value is read. Placed after `spec.gates`' own clause
    # (which names where each retired number went, and would be lost inside a generic
    # message) and before every value clause, because a key nothing reads is a value
    # nothing checks. See `SPEC_KEYS`.
    passthrough = _refuse_unknown_keys(spec)

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
        _refuse("spec.channels is empty; there is nothing to export", {'clause': 'channels_empty',
                                                                       'where': 'spec.channels',
                                                                       'known_channels': list(KNOWN_CHANNELS)})
    unknown = [c for c in channels if c not in KNOWN_CHANNELS]
    if unknown:
        _refuse(
            f"spec.channels names unknown channel(s) {unknown}; known: "
            f"{list(KNOWN_CHANNELS)}",
            {'clause': 'channel_unknown', 'where': 'spec.channels',
             'unknown': [repr(c) for c in unknown],
             'known_channels': list(KNOWN_CHANNELS),
             'channels': [repr(c) for c in channels]}
        )
    if len(set(channels)) != len(channels):
        _refuse(f"spec.channels contains duplicates: {channels}", {'clause': 'channels_duplicated',
                                                                   'where': 'spec.channels',
                                                                   'channels': [repr(c) for c in channels],
                                                                   'duplicated': sorted({repr(c) for c in channels if channels.count(c) > 1})})

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
            _refuse(
                "spec.depth.window must be 'per_shot' or a 2-number [z_min, z_max]",
                {'clause': 'depth_window_shape', 'where': 'spec.depth.window',
                 'value': repr(window), 'got': type(window).__name__}
            )
        # · ANDON — `spec.depth.window` was covered against NaN only BY ACCIDENT: the
        # ordering test below is `window[0] < window[1]`, which is False for a NaN, so a
        # NaN was refused with the words of an ordering complaint. An INFINITY was not
        # covered at all — measured 2026-09-04, `window=[-inf, inf]` was ACCEPTED and
        # returned unchanged, and the depth normalisation window is then degenerate.
        # `load_spec` uses `json.load` with the stdlib default, which reads the bare
        # tokens `NaN` and `Infinity`, so a spec file carrying one parses.
        for i in (0, 1):
            _require_finite_number(dict(enumerate(window)), i, "spec.depth.window",
                                   positive=False)
        if not window[0] < window[1]:
            _refuse(
                f"spec.depth.window is [{window[0]}, {window[1]}]; z_min must be below "
                f"z_max or the normalisation collapses",
                {'clause': 'depth_window_not_ordered', 'where': 'spec.depth.window',
                 'z_min': window[0], 'z_max': window[1]}
            )

    subject = _require(spec, "subject", dict, "spec")
    animation = subject.get("animation")
    if animation not in ANIMATION_MODES:
        # Not a soft default: silently falling back to `static` would render 33 identical
        # frames for a spec that asked for a performance, and G6 would never be armed
        # because the mode it keys on never arrived.
        _refuse(
            f"spec.subject.animation {animation!r} is not one of "
            f"{list(ANIMATION_MODES)}",
            {'clause': 'animation_mode_unknown', 'where': 'spec.subject',
             'key': 'animation', 'value': repr(animation),
             'animation_modes': list(ANIMATION_MODES)}
        )

    cam = spec["camera"]
    cam_type = cam.get("type")
    if cam_type not in KNOWN_CAMERA_TYPES:
        _refuse(f"spec.camera.type {cam_type!r} is not implemented "
                f"(known: {list(KNOWN_CAMERA_TYPES)})",
                {'clause': 'camera_type_not_implemented',
                 'where': 'spec.camera', 'key': 'type',
                 'value': repr(cam_type),
                 'implemented': list(KNOWN_CAMERA_TYPES)})
    # Author-supplied camera block (pre-defaults) — static sweep defaulting and
    # path/track `keys` presence key off what the author wrote, not the merge.
    raw_cam = raw.get("camera") if isinstance(raw.get("camera"), dict) else {}

    # `static` is locked-off: the orbit DEFAULTS merge would leave azimuth_sweep_deg
    # at 360 unless the author overrode it, which made `type=static` a label that did
    # not change the numeric camera model (F-2f2da5bb). Force the default to 0 when
    # the author omitted the key; refuse a non-zero sweep after the finite check below.
    if cam_type == "static" and "azimuth_sweep_deg" not in raw_cam:
        cam["azimuth_sweep_deg"] = 0.0

    # `path` / `track` need keyframes; orbit / static must not carry a silent unused
    # `keys` block (F-c3778bcf). Framing's `normalize_camera_keys` / `solve_path` are
    # the consumer — this contract only names the type and requires the keys shape.
    if cam_type in ("orbit", "static") and "keys" in cam:
        _refuse(
            f"spec.camera.type {cam_type!r} does not take camera.keys; keys belong to "
            f"path/track. Delete keys, or set type to 'path'/'track'",
            {'clause': 'camera_keys_not_for_type', 'where': 'spec.camera',
             'key': 'keys', 'type': cam_type,
             'path_types': ['path', 'track']}
        )
    if cam_type in ("path", "track"):
        keys = cam.get("keys")
        if not isinstance(keys, list) or not keys:
            _refuse(
                f"spec.camera.type {cam_type!r} requires a non-empty camera.keys list "
                f"(keyframe dicts with {list(CAMERA_PATH_KEY_FIELDS)}); framing."
                f"normalize_camera_keys is the consumer",
                {'clause': 'camera_path_keys_required', 'where': 'spec.camera',
                 'key': 'keys', 'type': cam_type,
                 'required_fields': list(CAMERA_PATH_KEY_FIELDS),
                 'got': type(keys).__name__, 'value': repr(keys)[:200]}
            )
        for i, key in enumerate(keys):
            if not isinstance(key, dict):
                _refuse(
                    f"spec.camera.keys[{i}] is a {type(key).__name__}, not a keyframe "
                    f"dict; required fields: {list(CAMERA_PATH_KEY_FIELDS)}",
                    {'clause': 'camera_path_key_not_a_dict', 'where': 'spec.camera.keys',
                     'index': i, 'got': type(key).__name__,
                     'required_fields': list(CAMERA_PATH_KEY_FIELDS)}
                )
            missing = [f for f in CAMERA_PATH_KEY_FIELDS if f not in key]
            if missing:
                _refuse(
                    f"spec.camera.keys[{i}] is missing {missing}; required fields: "
                    f"{list(CAMERA_PATH_KEY_FIELDS)}",
                    {'clause': 'camera_path_key_missing_field',
                     'where': 'spec.camera.keys', 'index': i, 'missing': missing,
                     'required_fields': list(CAMERA_PATH_KEY_FIELDS),
                     'present_keys': sorted(map(str, key))}
                )

    radius = cam.get("radius")
    # `bool` is a subclass of `int`, so `radius: true` was accepted as a number and
    # resolved to an orbit radius of 1.0. The `target` clause immediately below already
    # carries `not isinstance(v, bool)`; the same clause, not a second mechanism.
    if radius != "auto" and (not isinstance(radius, (int, float))
                             or isinstance(radius, bool)):
        _refuse("spec.camera.radius must be a number or the string 'auto'",
                {'clause': 'camera_radius_not_a_number', 'where': 'spec.camera',
                 'key': 'radius', 'value': repr(radius), 'got': type(radius).__name__})

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
            _refuse(
                "spec.camera.target must be 'bbox_center' or a 3-number [x, y, z]",
                {'clause': 'camera_target_shape', 'where': 'spec.camera',
                 'key': 'target', 'value': repr(target), 'got': type(target).__name__}
            )
        # · ANDON — `target` is the ONE numeric camera field the wave-12 non-finite sweep
        # did not reach: the comment below says "the rest of the camera block's numbers"
        # and the loop it introduces covers `lens_mm`, `sensor_mm`, `fit_margin`,
        # `clip_start`, `clip_end` and the three angles, with `radius` covered above.
        # `target` was checked for list shape, length and bool-ness and for nothing else.
        # Measured 2026-09-04: `camera={'type':'orbit','target':[nan,0,0]}` and
        # `target=[inf,0,0]` were both ACCEPTED and returned unchanged. The camera is then
        # placed at a non-finite target, `projected_bbox_px` finds nothing inside the
        # frame and returns None, and the operator gets G4's "no mesh vertex projects into
        # the frame" from the render layer instead of a SpecError naming the malformed
        # field. `positive=False`: a target coordinate is a position, not a distance.
        for i in (0, 1, 2):
            _require_finite_number(dict(enumerate(target)), i, "spec.camera.target",
                                   positive=False)

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

    # Locked-off means locked: an authored non-zero sweep under type=static is refused
    # by name so the label cannot disagree with the numeric model (F-2f2da5bb).
    if cam_type == "static" and float(cam["azimuth_sweep_deg"]) != 0.0:
        _refuse(
            f"spec.camera.type is 'static' but azimuth_sweep_deg is "
            f"{cam['azimuth_sweep_deg']}; a locked-off camera has sweep 0. Use "
            f"type 'orbit' (or 'path'/'track') for a moving camera, or set "
            f"azimuth_sweep_deg to 0",
            {'clause': 'static_camera_nonzero_sweep', 'where': 'spec.camera',
             'key': 'azimuth_sweep_deg', 'value': cam['azimuth_sweep_deg'],
             'type': 'static'}
        )

    # The same clause `depth.window` already writes for z_min/z_max. `clip_end` is read by
    # `stage_render.py:171` as a bound (`radius + sphere_r >= float(c['clip_end'])`), so a
    # range that does not open turns that andon into a check that always fires, and
    # nothing anywhere catches it as a malformed value.
    if not cam["clip_start"] < cam["clip_end"]:
        _refuse(
            f"spec.camera.clip_start is {cam['clip_start']} and clip_end is "
            f"{cam['clip_end']}; the near plane must be in front of the far one or the "
            f"camera has no depth range at all",
            {'clause': 'camera_clip_range_not_ordered', 'where': 'spec.camera',
             'clip_start': cam['clip_start'], 'clip_end': cam['clip_end']}
        )

    # · ANDON — `spec.edge` and `spec.render` were validated in NO WAY AT ALL: no
    # `_require`, no `_require_positive`, no `_require_finite_number`. `normalise_spec`
    # returned having never touched either block, while the comment above makes the
    # argument for exactly this shape about `camera`. Measured 2026-09-04, every one
    # ACCEPTED and round-tripped: `edge={'depth_rel_threshold': 'off',
    # 'normal_angle_deg': None}`, `edge={'depth_rel_threshold': nan,
    # 'normal_angle_deg': nan}`, `render={'engine': 'BLENDER_EEVEE', 'samples': -1,
    # 'filter_size': nan, 'film_transparent': True}`.
    #
    # The NaN case is the silent one and it is this repo's highest-priority defect class.
    # `stage_render.py:370` hands both edge numbers straight to `channels.derive_edge`,
    # where `rel > float(nan)` and `min_dot < cos(nan)` are both all-False. Measured on an
    # 8x8 synthetic depth step: `derive_edge(..., 0.02, 30.0)` reports `depth_break_px 16,
    # edge_px 16`; the same call with both thresholds NaN reports `depth_break_px 0,
    # normal_break_px 0, edge_px 0`. A completely blank edge control channel is then
    # written as a well-formed PNG at every frame, G2 counts the files present and
    # non-empty, G4 compares mask against projection and is blind to channel CONTENT, the
    # manifest records the run as finished, and the credits are spent on a generation
    # whose edge control carried no information.
    edge = _require(spec, "edge", dict, "spec")
    _require(edge, "depth_rel_threshold", (int, float), "spec.edge")
    _require_positive(edge, "depth_rel_threshold", "spec.edge",
                      note="which is a relative depth gradient")
    _require(edge, "normal_angle_deg", (int, float), "spec.edge")
    _require_finite_number(edge, "normal_angle_deg", "spec.edge", positive=False)
    # An angle, so sign is not the question the way it is for the threshold — but the
    # DOMAIN is: `derive_edge` reads this as `cos(radians(x))`, and cosine is periodic, so
    # 390 and 30 are the same break angle while 210 is 150's. A spec naming an angle
    # outside the half-turn is not a tighter or looser threshold, it is a number whose
    # meaning is not the one the field's name states.
    if not 0.0 <= float(edge["normal_angle_deg"]) <= 180.0:
        _refuse(
            f"spec.edge.normal_angle_deg is {edge['normal_angle_deg']}; a normal break "
            f"angle lives in [0, 180]. `channels.derive_edge` reads it as "
            f"cos(radians(x)), which is periodic, so a value outside the half-turn "
            f"silently means a different angle than the one written down",
            {'clause': 'edge_normal_angle_out_of_domain', 'where': 'spec.edge',
             'key': 'normal_angle_deg', 'value': edge['normal_angle_deg'],
             'domain': [0.0, 180.0]}
        )

    render = _require(spec, "render", dict, "spec")
    engine = _require(render, "engine", str, "spec.render")
    if engine not in KNOWN_ENGINES:
        _refuse(
            f"spec.render.engine {engine!r} is not one of {list(KNOWN_ENGINES)}. "
            f"`blender_scene.configure_render` assigns it to `scene.render.engine` "
            f"verbatim, so an unknown identifier is refused by Blender's RNA from inside "
            f"the render layer — after the scene is built and the tool that writes has "
            f"been entered",
            {'clause': 'render_engine_unknown', 'where': 'spec.render', 'key': 'engine',
             'value': repr(engine), 'known_engines': list(KNOWN_ENGINES)}
        )
    _require(render, "samples", int, "spec.render")
    _require_positive(render, "samples", "spec.render", note="which is a sample COUNT")
    _require(render, "filter_size", (int, float), "spec.render")
    _require_positive(render, "filter_size", "spec.render",
                      note="which is a pixel filter WIDTH")
    _require(render, "film_transparent", bool, "spec.render")

    # The receipt half of the passthrough: which fields the schema did NOT read, recorded
    # so a reader of the spec can tell them from the fields it did. `_`-prefixed, so
    # `dump_spec` strips it and the file on disk stays the schema.
    if passthrough:
        spec["_passthrough_keys"] = passthrough
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
        _refuse(f"spec.asset.path does not exist: {path}", {'clause': 'asset_missing',
                                                            'where': 'spec.asset',
                                                            'key': 'path',
                                                            'path': str(path),
                                                            'declared': repr(spec['asset']['path'])})
    digest = sha256_file(path)
    pinned = spec["asset"].get("sha256")
    if not pinned:
        _refuse(
            f"spec.asset.sha256 is absent, so this spec asserts nothing about the "
            f"bytes it was written against. {path} hashes to {digest} — paste that "
            f"into spec.asset.sha256",
            {'clause': 'asset_sha256_absent', 'where': 'spec.asset', 'key': 'sha256',
             'path': str(path), 'measured': digest, 'pinned': repr(pinned)}
        )
    if pinned != digest:
        _refuse(
            f"spec.asset.sha256 pins {pinned} but {path} hashes to {digest}",
            {'clause': 'asset_sha256_mismatch', 'where': 'spec.asset', 'key': 'sha256',
             'path': str(path), 'pinned': pinned, 'measured': digest}
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


def _pin_known_channels_to_conventions():
    """KNOWN_CHANNELS must name every CHANNEL_CONVENTIONS key (F-98515e19).

    channels.py owns the convention digests (core-solvers); this module owns the
    shotspec vocabulary. A new convention without a KNOWN_CHANNELS row would refuse
    at schema load while encode_* still shipped — the defect this pin closes.
    """
    from .channels import CHANNEL_CONVENTIONS

    missing = sorted(set(CHANNEL_CONVENTIONS) - set(KNOWN_CHANNELS))
    if missing:
        raise RuntimeError(
            f"shotspec.KNOWN_CHANNELS is missing CHANNEL_CONVENTIONS name(s) "
            f"{missing}; extend KNOWN_CHANNELS in the same change that adds a "
            f"convention. KNOWN_CHANNELS={list(KNOWN_CHANNELS)}; "
            f"CHANNEL_CONVENTIONS={sorted(CHANNEL_CONVENTIONS)}"
        )


_pin_known_channels_to_conventions()
