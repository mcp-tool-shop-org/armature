"""E07's gates: N (names), P (rest-pose fidelity), D (determinism). Every one raises.

None uses `assert`, none reads an environment variable, none takes a `skip` argument, and
none is chained behind a shell `&&` — they are called from inside `rig_character.py`'s
export path, in the same process, before the manifest that would make the run look
finished. The reasoning for each andon's *direction* lives on its exception class in
`errors.py`; what lives here is the arithmetic.

They are importable without bpy on purpose. A gate that can only be exercised by running
the whole Blender pipeline is a gate whose failure path is never tested, and this repo has
a standing rule that a fixture must answer *what would this look like if the code were
wrong in the specific way this check exists to catch* — which requires being able to hand
the gate a wrong input.
"""

import numpy as np

from .errors import GateDDeterminism, GateNNames, GatePRestPose
from .parts import require_finite

#: Gate P's epsilon, as a fraction of the mesh's own bbox diagonal. Not a length in
#: metres: a global constant must not govern a local feature.
REST_POSE_EPSILON_FRAC = 1e-4
#: Gate D's tolerances. Lengths scale with the subject; weights are a unit interval.
DETERMINISM_LENGTH_FRAC = 1e-6
DETERMINISM_WEIGHT_TOL = 1e-6
DETERMINISM_ANGLE_TOL = 1e-6


def _require_numeric(name, value, gate_cls, ev):
    """The clause `require_finite` cannot carry: the value is a NUMBER at all.

    `parts.require_finite` opens with `float(value)`, so a diagonal that is not numeric is
    destroyed by that coercion before the helper can refuse it — the receipt-shaped defect
    F-8a5683e0 names one line further out. Measured 2026-09-04 on the base tree:
    `gate_p_rest_pose(a, a, None)` raised `TypeError: float() argument must be a string or
    a real number, not 'NoneType'` and `gate_p_rest_pose(a, a, 'x')` raised `ValueError:
    could not convert string to float`. Neither is an `ArmatureError`, so
    `rig_character`'s halt handler classified a malformed argument as an unhandled crash
    and wrote no receipt at all on its halt line — the exact exit this page closed for the
    empty-array case in the same function. (The receipt is the six-key `<TOOL>_HALT` line
    every tool emits; the `GATE_FAILURE` / `GATE_EVIDENCE` pair this page's older comments
    name was deleted at the wave-12 merge.)

    `world_bounds` returning None is the plausible producer; today's two call sites
    (`rig_character.py:1050/:1194`) pass a computed float, so what this costs today is the
    receipt rather than the verdict. It refuses `bool` for the reason `shotspec` refuses a
    boolean radius: `True` is an `int`, and a flag is not a length. It ACCEPTS numpy's
    scalar types, which are what `np.linalg.norm` hands a caller that forgets the `float()`.

    Separate from `require_finite` rather than inside it: that helper is core-solvers' and
    is shared by four modules, and this clause is about a TYPE, not about a comparison.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float, np.floating,
                                                         np.integer)):
        ev[name] = repr(value)
        raise gate_cls(
            f"{name}={value!r} is a {type(value).__name__}, not a number this gate can "
            f"scale a tolerance by. A gate cannot compare against it and it cannot even "
            f"be coerced, so without this clause the refusal arrives as a stdlib "
            f"TypeError from inside the evidence dict — an unhandled crash naming no "
            f"gate, in place of a receipt naming this one",
            ev)
    return value


def _require_finite_measurement(name, values, gate_cls, ev):
    """Refuse a non-finite MEASURED quantity by index, through the one non-finite helper.

    ⚠ **Wave 12 guarded every THRESHOLD on this page and none of the MEASUREMENTS.**
    The shared helper runs on `bbox_diagonal` four times here, so the number a gate
    compares *against* is always finite — and every number a gate compares was left
    unchecked. That is the wrong operand: a NaN threshold makes a comparison unanswerable,
    but a NaN *observation* makes every comparison False in both directions and lands on
    the verdict line as agreement. Measured 2026-09-04 on the base tree, one NaN in the
    bound array: `gate_p_rest_pose` returned `verdict: 'rest pose preserved'` with
    `max_displacement: nan` (`d[i] > threshold` is False); `gate_p_evaluation_is_live`
    returned "the deform is live" on the same input (`d.max() <= threshold` is False);
    `gate_d_determinism` returned "two builds agree on bones and hierarchy" for a bone
    whose tail is `[nan, nan, nan]` in the second build, with `worst_bone_delta` recording
    a delta of **0.0** — the receipt actively stating there was no difference; the same for
    a NaN roll and for a weight vector `[nan, 1.0]` against `[0.0, 1.0]`.

    The producing input is the one Gate D's own page already names as reachable: a GLB
    carrying a non-finite vertex position, representable in glTF's float32 and passed
    through by the importer. The three andons that exist to catch a silent collapse then
    report green over it.

    This is not a second implementation of the family — it locates the first offending
    entry and hands THAT value to `parts.require_finite`, so the refusal carries the one
    message, the one paragraph and the caller's own andon class, with the index and the
    population beside it. `positive=False`: a displacement, a roll delta and a weight
    delta may legitimately be zero.
    """
    arr = np.asarray(values, dtype=np.float64).ravel()
    bad = np.flatnonzero(~np.isfinite(arr))
    if bad.size:
        i = int(bad[0])
        ev[f"{name}_non_finite"] = {"first_index": i, "n_non_finite": int(bad.size),
                                    "population": int(arr.size)}
        require_finite(f"{name}[{i}]", arr[i], gate_cls, ev, positive=False)
    return arr


def gate_n_names(observed, registered, where):
    """Gate N · ANDON — every registered site is a bone with exactly that name, and the
    rig carries nothing that was not registered.

    `observed` is the sequence of bone names actually present; `registered` the committed
    list; `where` names what was inspected, so a failure says whether the defect is in the
    build or in the export.
    """
    observed = list(observed)
    registered = list(registered)
    ev = {"gate": "N", "andon": "GateNNames",
          "where": where, "n_observed": len(observed),
          "n_registered": len(registered)}

    # · ANDON — a coverage verdict over an empty registry is not a verdict. Measured
    # 2026-09-04: `gate_n_names([], [], "the re-imported export")` returned
    # `verdict: "0 / 0 registered sites map to one bone each"` — a PASS having compared
    # nothing, phrased as a coverage claim. Its two neighbours were given exactly this
    # refusal in wave 10 on exactly this reasoning (`gate_d_determinism` below, on both
    # fingerprints carrying zero bones; `gates.g2_completeness`, on an empty channel
    # mapping) and both acknowledge the same reachability: the input needs a caller bug to
    # arrive. Every live call site passes `sitelist.ALL_NAMES` (`author_walk.py:552/612`,
    # `lift_solve.py:307`, `rig_character.py:1196`), a module constant that is non-empty
    # today, so an empty registry means that constant was emptied or mis-imported — and
    # THAT is the edit this andon exists to catch: E01's whole result (four rigged GLBs
    # naming bone_0..bone_N, zero of 18 sites findable, every other check passing) is
    # reproducible with this gate reporting 0 / 0. The other direction is already safe —
    # an empty `observed` against a non-empty registry raises, measured.
    if not registered:
        raise GateNNames(
            f"Gate N was asked to check {len(observed)} bone name(s) against a registry "
            f"of ZERO registered sites, which is not a coverage verdict: nothing would be "
            f"compared and '0 / 0 registered sites map to one bone each' would be a "
            f"statement about an empty population. Every call site passes "
            f"sitelist.ALL_NAMES; an empty one means the committed list was emptied or "
            f"mis-imported, which is exactly the defect this gate exists to see",
            ev)

    counts = {}
    for n in observed:
        counts[n] = counts.get(n, 0) + 1
    missing = [n for n in registered if counts.get(n, 0) == 0]
    duplicated = sorted(n for n in registered if counts.get(n, 0) > 1)
    unregistered = sorted(n for n in counts if n not in set(registered))

    ev.update({"missing": missing, "duplicated": duplicated,
               "unregistered": unregistered,
               "mapped": len(registered) - len(missing)})

    problems = []
    if missing:
        problems.append(f"{len(missing)} registered site(s) name no bone: {missing}")
    if duplicated:
        problems.append(f"{len(duplicated)} site(s) name more than one bone: {duplicated}")
    if unregistered:
        problems.append(
            f"{len(unregistered)} bone(s) that no committed list registered: "
            f"{unregistered[:12]}"
        )

    if problems:
        raise GateNNames(
            f"the rig at {where} does not match the registered site list "
            f"({ev['mapped']} / {len(registered)} mapped): " + "; ".join(problems),
            ev,
        )
    ev["verdict"] = f"{len(registered)} / {len(registered)} registered sites map to one bone each"
    return ev


def gate_p_rest_pose(source_world, bound_world, bbox_diagonal):
    """Gate P · ANDON — binding the mesh did not move it.

    `source_world` and `bound_world` are (N, 3) world-space vertex arrays: the mesh as
    imported, and the same mesh evaluated with the armature modifier live at the rest
    pose. Max displacement must be within `REST_POSE_EPSILON_FRAC` of the mesh's own
    bbox diagonal.

    ⚠ **The epsilon used to arrive from the caller.** Measured 2026-09-04:
    `gate_p_rest_pose(a, collapsed, 1.0)` raised, and the same call with
    `epsilon_frac=1e9` returned verdict 'rest pose preserved' on that same collapsed
    mesh. `gates.g4_bbox_sanity` and `donor_gate.gate_donor` both had this argument
    removed already, for the reason this module's own page states: a number a gate
    compares against is a skip flag wearing an argument's clothes. No caller in `tools/`
    passed it (measured by grep, 2026-09-04), so it was a latent skip flag rather than a
    live one. The constant is read here.
    """
    epsilon_frac = REST_POSE_EPSILON_FRAC
    a = np.asarray(source_world, dtype=np.float64)
    b = np.asarray(bound_world, dtype=np.float64)
    ev = {"gate": "P", "andon": "GatePRestPose",
          "epsilon_frac": epsilon_frac,
          "epsilon_source": "rig_gates.REST_POSE_EPSILON_FRAC",
          "n_source": int(a.shape[0]) if a.ndim == 2 else None,
          "n_bound": int(b.shape[0]) if b.ndim == 2 else None}

    if a.shape != b.shape:
        raise GatePRestPose(
            f"the bound mesh has a different vertex array than the source: {a.shape} vs "
            f"{b.shape}. Rest-pose fidelity is undefined when the vertices do not "
            f"correspond, and a per-vertex comparison would be reading two different "
            f"meshes against each other",
            ev,
        )
    if a.ndim != 2 or a.shape[1] != 3 or a.shape[0] == 0:
        raise GatePRestPose(f"expected a non-empty (N, 3) vertex array, got {a.shape}", ev)
    # · ANDON — `> 0` covered HALF this quantity: `nan > 0` is False and refused, but
    # `inf > 0` is True and walked straight through into `epsilon_frac * inf`, giving an
    # infinite threshold that no displacement can exceed. `require_finite` is the repo's
    # ONE non-finite helper (`parts.py`, wave 10's rule 4) and it refuses nan, inf,
    # zero and negatives by name with the value in the evidence — one implementation
    # across the four clauses on this page and the four `parts`/`startframe`/`lift_solve`
    # callers, never a second `math.isfinite`.
    _require_numeric("bbox_diagonal", bbox_diagonal, GatePRestPose, ev)
    bbox_diagonal = require_finite("bbox_diagonal", bbox_diagonal, GatePRestPose, ev,
                                  positive=False)
    # · The evidence dict is built AFTER this refusal, never before it. `ev` used to open
    # with `"bbox_diagonal": float(bbox_diagonal)`, so a NON-NUMERIC diagonal was destroyed
    # by that `float()` on the way into the receipt rather than refused by the gate.
    # Measured 2026-09-04: `gate_p_rest_pose(a, a, None)` raised `TypeError: float()
    # argument must be a string or a real number, not 'NoneType'` and `'x'` raised
    # `ValueError`. Neither is an `ArmatureError`, so `rig_character`'s halt handler
    # classified it an unhandled crash with no receipt at all — the exact exit this page
    # closed for the empty-array case. `gate_d_determinism` already had the order right.
    ev["bbox_diagonal"] = bbox_diagonal
    if not (bbox_diagonal > 0):
        raise GatePRestPose(
            f"bbox diagonal is {bbox_diagonal}; the threshold is a fraction of the mesh's "
            f"own size and cannot be computed from a degenerate one",
            ev,
        )

    d = np.linalg.norm(b - a, axis=1)
    # · ANDON — on the MEASUREMENT, which is the operand the threshold guard above does
    # not cover. `d[i] > threshold` is False for a NaN displacement, so a vertex whose
    # position is not a number reported "rest pose preserved" with `max_displacement: nan`
    # in the receipt beside it. See `_require_finite_measurement`.
    _require_finite_measurement("displacement", d, GatePRestPose, ev)
    threshold = epsilon_frac * float(bbox_diagonal)
    i = int(np.argmax(d))
    ev.update({
        "threshold": threshold,
        "max_displacement": float(d[i]),
        "max_displacement_vertex": i,
        "max_displacement_as_frac_of_diagonal": float(d[i] / bbox_diagonal),
        "mean_displacement": float(d.mean()),
        "median_displacement": float(np.median(d)),
        "n_over_threshold": int((d > threshold).sum()),
        "source_at_max": a[i].tolist(),
        "bound_at_max": b[i].tolist(),
    })

    if d[i] > threshold:
        raise GatePRestPose(
            f"binding moved the mesh: max vertex displacement {d[i]:.9f} exceeds "
            f"{epsilon_frac:g} × bbox diagonal ({threshold:.9f}) at vertex {i}, and "
            f"{ev['n_over_threshold']} vertices are over it. Linear-blend skinning at the "
            f"bind pose is the identity when each vertex's weights sum to 1, so a breach "
            f"here means weights that do not sum to 1 — vertices contracting toward the "
            f"origin, which is what a partially failed bone-heat solve produces and what "
            f"nothing else in this tool can see",
            ev,
        )
    ev["verdict"] = "rest pose preserved"
    return ev


def gate_p_round_trip_positions(source, roundtrip, bbox_diagonal, *, max_probe=20000):
    """Gate P, round-trip clause — the exported surface is the surface that went in.

    **Why this is a point-set comparison where the bind clause is index-wise.** The armature
    modifier is a deform: it preserves vertex order, so `gate_p_rest_pose` can compare index
    for index. A glTF *export* does not — it re-splits vertices at attribute discontinuities,
    and on this subject 399,140 vertices came back as 399,903. Comparing those index-wise
    reads two different arrays against each other, which is what the first version of this
    code did until it raised and said so.

    What has to hold is that the **set of positions** is unchanged; multiplicity is the
    exporter's business. Measured on this subject: 149,643 unique positions in, 149,643 out,
    identical to the last float32 bit.

    Compared at float32 because that is glTF's storage precision. Demanding float64 would be
    asking for a precision the format does not carry, and would fire on a correct export.

    ⚠ **A probe that could not finish now REFUSES; it used to report a pass.** Until
    2026-09-04, when the odd-position population exceeded `max_probe` the probe was
    truncated to the first `max_probe` entries and the gate reported "positions agree
    within <threshold>" computed over that prefix. Nothing in the return value
    distinguished "every differing position was measured" from "the first N were".
    Measured: ten source positions, all ten differing, the last in the gate's own sort
    order moved 50.0 units — with `max_probe=3` the gate returned `verdict='positions
    agree within 0.000100000'`, `max_deviation=9.99e-07`, `probe_truncated_at=3`. A glTF
    export that moved the surface would ship with Gate P green, which is the silent
    collapse `GatePRestPose` exists to catch, and `tools/rig_character.py:881` runs this
    clause on a subject whose own record is 149,643 unique positions.

    `epsilon_frac` went with it, for the reason `gate_p_rest_pose` records. `max_probe`
    stays because it no longer decides a verdict — exceeding it raises — and it is
    keyword-only so a caller that sets it is stating a choice rather than dropping a
    number into a threshold slot.
    """
    epsilon_frac = REST_POSE_EPSILON_FRAC
    raw_a = np.asarray(source, dtype=np.float32)
    raw_b = np.asarray(roundtrip, dtype=np.float32)
    ev = {"gate": "P", "andon": "GatePRestPose",
          "shape_source": list(raw_a.shape), "shape_roundtrip": list(raw_b.shape),
          "epsilon_frac": epsilon_frac,
          "epsilon_source": "rig_gates.REST_POSE_EPSILON_FRAC",
          "max_probe": int(max_probe),
          "compared_at": "float32 — glTF's storage precision"}
    # · ANDON — the two input guards `gate_p_rest_pose` writes, in its order. An empty
    # array reaches `np.unique` intact and comes back empty, both `setdiff1d` calls are
    # then empty, and the clause returned "the exported surface is the source surface"
    # about two meshes nobody read.
    for label, arr in (("source", raw_a), ("roundtrip", raw_b)):
        if arr.ndim != 2 or arr.shape[1] != 3 or arr.shape[0] == 0:
            raise GatePRestPose(
                f"expected a non-empty (N, 3) vertex array for the {label}, got "
                f"{arr.shape}", ev)
    # · ANDON — the same half-covered quantity as `gate_p_rest_pose`'s: `inf > 0` passes.
    _require_numeric("bbox_diagonal", bbox_diagonal, GatePRestPose, ev)
    bbox_diagonal = require_finite("bbox_diagonal", bbox_diagonal, GatePRestPose, ev,
                                  positive=False)
    # · As `gate_p_rest_pose`: the coerced value enters the receipt after the refusal.
    ev["bbox_diagonal"] = bbox_diagonal
    if not (bbox_diagonal > 0):
        raise GatePRestPose(f"bbox diagonal is {bbox_diagonal}; no threshold can be derived",
                            ev)

    a = np.unique(np.ascontiguousarray(raw_a), axis=0)
    b = np.unique(np.ascontiguousarray(raw_b), axis=0)
    ev.update({"unique_positions_source": int(len(a)),
               "unique_positions_roundtrip": int(len(b)),
               "n_source_vertices": int(len(raw_a)),
               "n_roundtrip_vertices": int(len(raw_b))})

    dtype = [("x", np.float32), ("y", np.float32), ("z", np.float32)]
    va, vb = a.view(dtype).ravel(), b.view(dtype).ravel()
    only_source = np.setdiff1d(va, vb)
    only_roundtrip = np.setdiff1d(vb, va)
    ev["positions_only_in_source"] = int(len(only_source))
    ev["positions_only_in_roundtrip"] = int(len(only_roundtrip))

    if not len(only_source) and not len(only_roundtrip):
        ev["verdict"] = "the exported surface is the source surface, position for position"
        ev["max_deviation"] = 0.0
        return ev

    # Positions differ. They may still be inside tolerance — measure, rather than firing on
    # a last-bit rounding difference the format is entitled to.
    threshold = epsilon_frac * float(bbox_diagonal)
    worst = 0.0
    for odd, against in ((only_source, b), (only_roundtrip, a)):
        if not len(odd):
            continue
        pts = np.stack([odd["x"], odd["y"], odd["z"]], axis=1).astype(np.float64)
        if len(pts) > max_probe:
            # · ANDON — on the direction the rest of this clause does not bound. A
            # prefix measured is not a population measured, and the verdict below would
            # say "positions agree" about the entries nobody read.
            ev["probe_truncated_at"] = int(max_probe)
            ev["probe_population"] = int(len(pts))
            ev["probe_unexamined"] = int(len(pts) - max_probe)
            raise GatePRestPose(
                f"the round-trip probe cannot examine this population: {len(pts)} "
                f"position(s) are present on only one side and the probe window is "
                f"{max_probe}, so {len(pts) - max_probe} of them would never be "
                f"measured. A deviation computed over the first {max_probe} would "
                f"state that the surface is unchanged on the strength of a prefix, and "
                f"a check that cannot fail is not a check. Raise max_probe as a stated "
                f"choice, or fix the export that produced {len(only_source)} "
                f"source-only and {len(only_roundtrip)} export-only positions",
                ev,
            )
        ref = against.astype(np.float64)
        for chunk in np.array_split(pts, max(1, len(pts) // 256 + 1)):
            d = np.linalg.norm(chunk[:, None, :] - ref[None, :, :], axis=2).min(axis=1)
            # · ANDON — the same MEASUREMENT guard, and this accumulator swallows a NaN
            # twice over: `max(worst, nan)` returns `worst` (because `nan > worst` is
            # False), so the deviation never even reaches the `worst > threshold` test.
            _require_finite_measurement("deviation", d, GatePRestPose, ev)
            worst = max(worst, float(d.max()))
    ev.update({"threshold": threshold, "max_deviation": worst})

    if worst > threshold:
        raise GatePRestPose(
            f"the export round trip moved the surface: {len(only_source)} position(s) only "
            f"in the source and {len(only_roundtrip)} only in the export, the worst of them "
            f"{worst:.9f} from any position in the other (> {threshold:.9f}). Vertex "
            f"multiplicity may change through glTF; the set of positions may not",
            ev,
        )
    ev["verdict"] = f"positions agree within {threshold:.9f}"
    return ev


#: Gate P's liveness floor, as a fraction of the mesh's own bbox diagonal. A module
#: constant, not an argument — see `gate_p_rest_pose`.
LIVENESS_MIN_FRAC = 1e-4


def gate_p_evaluation_is_live(rest_world, probe_world, bbox_diagonal):
    """Gate P, second clause · ANDON — the identity reading was not vacuous.

    **A check that cannot fail is not a check, and Gate P's first clause is one step from
    being exactly that.** It passed on this subject with a max displacement of *exactly*
    0.0, which has two possible causes and only one of them is the good one: either
    skinning is genuinely the identity at bind, or the evaluated mesh handed to the gate
    never carried the armature modifier at all. Both read 0.0. In the second case Gate P
    would report green on a mesh that was never bound to anything, and every run after it
    would inherit that green.

    So the tool poses a bone, re-evaluates, and hands the result here. If the mesh does not
    move when a bone moves, the evaluation path is dead and the 0.0 measured nothing.

    The floor is `LIVENESS_MIN_FRAC`, read here rather than taken from the caller: a
    caller-supplied floor of 0 would make this andon pass on a dead evaluation, which is
    the andon inverted. See `gate_p_rest_pose`.
    """
    min_frac = LIVENESS_MIN_FRAC
    a = np.asarray(rest_world, dtype=np.float64)
    b = np.asarray(probe_world, dtype=np.float64)
    ev = {"gate": "P", "andon": "GatePRestPose",
          "min_frac": min_frac, "min_frac_source": "rig_gates.LIVENESS_MIN_FRAC",
          "n_rest": int(a.shape[0]) if a.ndim == 2 else None,
          "n_probe": int(b.shape[0]) if b.ndim == 2 else None}
    if a.shape != b.shape:
        raise GatePRestPose(
            f"liveness probe returned a different vertex array ({a.shape} vs {b.shape}); "
            f"the probe cannot say whether the deform is live",
            ev,
        )
    # · ANDON — the two input guards `gate_p_rest_pose` carries at lines 110-117, in its
    # order, and this is the clause `rig_character.py:664` calls FIRST — two lines before
    # the rest-pose clause whose refusal would otherwise fire on the same input.
    #
    # (a) An empty array reached `float(d.max())` and raised a bare `ValueError: zero-size
    # array to reduction operation maximum which has no identity`. A ValueError is not an
    # `ArmatureError`, so the halt contract's exit-2 branch and the receipt every census
    # reads were bypassed and the run exited 1 with a stdlib traceback naming no gate.
    # (Citation corrected 2026-09-04: the receipt is the six-key `<TOOL>_HALT` line, not
    # the `GATE_FAILURE` / `GATE_EVIDENCE` pair this comment used to name — those two
    # lines were deleted at the wave-12 merge.)
    #
    # (b) With `bbox_diagonal == 0` the floor is `min_frac * 0.0 == 0.0`, so
    # `d.max() <= threshold` is False for any non-zero float noise and this andon reported
    # "the deform is live" on a probe that measured nothing — the andon inverted, which is
    # exactly what this function's docstring says a caller-supplied floor of 0 would do.
    if a.ndim != 2 or a.shape[1] != 3 or a.shape[0] == 0:
        raise GatePRestPose(f"expected a non-empty (N, 3) vertex array, got {a.shape}", ev)
    # · ANDON — as above, and this clause is the one an INFINITY inverts hardest: an
    # infinite floor makes `d.max() <= threshold` True for every real displacement, so the
    # liveness andon would fire on a mesh that DID move — an andon that fails on correct
    # work, which is the andon nobody keeps.
    _require_numeric("bbox_diagonal", bbox_diagonal, GatePRestPose, ev)
    bbox_diagonal = require_finite("bbox_diagonal", bbox_diagonal, GatePRestPose, ev,
                                  positive=False)
    # · As `gate_p_rest_pose`: the coerced value enters the receipt after the refusal.
    ev["bbox_diagonal"] = bbox_diagonal
    if not (bbox_diagonal > 0):
        raise GatePRestPose(
            f"bbox diagonal is {bbox_diagonal}; the liveness floor is a fraction of the "
            f"mesh's own size and a floor of 0 makes this andon pass on a dead evaluation",
            ev,
        )

    d = np.linalg.norm(b - a, axis=1)
    # · ANDON — the same MEASUREMENT guard, and here the inversion is the loud one:
    # `d.max() <= threshold` is False for a NaN, so a probe that measured nothing at all
    # reported "the deform is live". See `_require_finite_measurement`.
    _require_finite_measurement("displacement", d, GatePRestPose, ev)
    threshold = min_frac * float(bbox_diagonal)
    ev.update({"threshold": threshold, "max_displacement": float(d.max()),
               "mean_displacement": float(d.mean()),
               "n_vertices_moved": int((d > threshold).sum())})
    if d.max() <= threshold:
        raise GatePRestPose(
            f"the evaluated mesh did not move when a bone was posed (max displacement "
            f"{d.max():.3e} ≤ {threshold:.3e}), so the armature modifier is not live on "
            f"the evaluation Gate P read. Gate P's rest-pose measurement was therefore "
            f"vacuous: it would report a perfect identity on a mesh bound to nothing",
            ev,
        )
    ev["verdict"] = "the deform is live; Gate P's rest-pose reading is about a bound mesh"
    return ev


def rig_fingerprint(bones, weights, n_verts):
    """The comparable content of a rig: geometry, hierarchy, and per-vertex weights.

    `bones` maps name → dict with head, tail, roll, parent, use_deform. `weights` maps
    vertex-group name → an (n_verts,) array. Deliberately **not** a file hash: a GLB
    carries exporter strings and float noise that differ between runs producing the same
    rig, so a byte comparison both fires on runs that agree and, worse, would be quoted as
    proof of a property it never tested.
    """
    return {
        "n_verts": int(n_verts),
        "bones": {str(k): {
            "head": [float(v) for v in b["head"]],
            "tail": [float(v) for v in b["tail"]],
            "roll": float(b.get("roll", 0.0)),
            "parent": b.get("parent"),
            "use_deform": bool(b.get("use_deform", True)),
        } for k, b in bones.items()},
        "weights": {str(k): np.asarray(v, dtype=np.float64) for k, v in weights.items()},
    }


def gate_d_determinism(a, b, bbox_diagonal):
    """Gate D · ANDON — a second build from identical inputs produced the same rig.

    Compared as parsed objects. Lengths are toleranced as a fraction of the subject's own
    bbox diagonal; weights and rolls on their own natural units.

    **The verdict says only what was CHECKED.** Two clauses of this gate can be handed an
    empty population, and neither used to say so.

    * `a["bones"]` empty: nothing about the skeleton is compared and the gate returned
      "two builds agree on bones, hierarchy and weights". Measured 2026-09-03,
      `gate_d_determinism(rig_fingerprint({}, {}, 0), rig_fingerprint({}, {}, 0), 1.0)`
      returned exactly that with `n_bones_a == n_bones_b == 0`. `gate_p_rest_pose` on
      this page already raises on `a.shape[0] == 0`; this is the same refusal.
    * Both `weights` dicts empty: the weight clause iterates `sorted(set(wa) & set(wb))`,
      so ZERO per-vertex vectors are compared while the verdict names weights. This is
      not hypothetical — `rig_character.build_pass` initialises `weights = {}` and only
      fills it inside `if bind:`, and the skeleton-only route calls `build_pass(...,
      bind=False)` twice and hands both fingerprints straight here. On that route the
      per-vertex comparison this gate's own docstring names as part of the contract
      examines nothing, while the receipt asserts weights agree. The bone half DOES bind
      there, so the gate is not wholly vacuous — the false half is the one the receipt
      asserted, and the verdict now names it as NOT COMPARED.

    ⚠ **The three tolerances used to arrive from the caller.** Measured 2026-09-04:
    this gate raised on a rig whose bone tail had moved 4.0 and whose weights went
    0 -> 1, and the same call with `length_frac=1e9, weight_tol=1e9, angle_tol=1e9`
    returned "two builds agree on bones, hierarchy and weights". The constants are read
    here now, for the reason `gate_p_rest_pose` records.
    """
    length_frac = DETERMINISM_LENGTH_FRAC
    weight_tol = DETERMINISM_WEIGHT_TOL
    angle_tol = DETERMINISM_ANGLE_TOL
    ev = {"gate": "D", "andon": "GateDDeterminism",
          "weight_tolerance": weight_tol,
          "angle_tolerance": angle_tol,
          "tolerance_source": ("rig_gates.DETERMINISM_LENGTH_FRAC / "
                               "DETERMINISM_WEIGHT_TOL / DETERMINISM_ANGLE_TOL"),
          "n_bones_a": len(a["bones"]), "n_bones_b": len(b["bones"]),
          "n_weight_groups_a": len(a["weights"]), "n_weight_groups_b": len(b["weights"])}

    # · ANDON — Gate D was the ONE clause on this page that derived a tolerance from
    # `bbox_diagonal` without first refusing a degenerate one, and the route that reaches
    # it is the one route where the clauses that DO refuse never run. Measured 2026-09-04
    # on two fingerprints whose one bone's tail differs by 4.0 with both weight dicts
    # empty: `bbox_diagonal=inf` returned "two builds agree on bones and hierarchy over 1
    # bone(s)" with `length_tolerance` inf, and `nan` returned the same verdict with a nan
    # tolerance. The caller: `rig_character.py:1050/:1194` pass `ctx['diagonal']`, which is
    # `float(np.linalg.norm(hi - lo))` over the raw imported vertices, with both Gate P
    # clauses inside `if bind:` — so on `--mode=skeleton` (bind=False, deliberate) NOTHING
    # has looked at that number before this line scales a tolerance by it. A GLB carrying
    # a non-finite vertex position (representable in glTF's float32 and passed through by
    # the importer) yields a non-finite diagonal, and the skeleton build's determinism
    # receipt then says "two builds agree" over bones that moved — a recipe that does not
    # reproduce its output, with the andon that exists to catch exactly that reporting
    # green. The weight clause still binds either way (its tolerance is a constant); what
    # went vacuous is the bone geometry, which on the skeleton route is the whole quantity.
    _require_numeric("bbox_diagonal", bbox_diagonal, GateDDeterminism, ev)
    bbox_diagonal = require_finite("bbox_diagonal", bbox_diagonal, GateDDeterminism, ev,
                                  positive=False)
    ev["bbox_diagonal"] = bbox_diagonal
    if not (bbox_diagonal > 0):
        raise GateDDeterminism(
            f"bbox diagonal is {bbox_diagonal}; the length tolerance is a fraction of the "
            f"subject's own size and cannot be computed from a degenerate one. This is the "
            f"clause the three Gate P clauses on this page already carry, and Gate D was "
            f"the one that did not",
            ev,
        )
    tol = length_frac * bbox_diagonal
    ev["length_tolerance"] = tol
    problems = []

    # · ANDON — a comparison over zero bones is not a determinism verdict.
    if not a["bones"] and not b["bones"]:
        raise GateDDeterminism(
            "both fingerprints carry ZERO bones, so nothing about the skeleton was "
            "compared and 'the two builds agree' would be a statement about an empty "
            "population. gate_p_rest_pose refuses an empty vertex array on the same "
            "grounds", ev)

    if a["n_verts"] != b["n_verts"]:
        problems.append(f"vertex count {a['n_verts']} vs {b['n_verts']}")

    names_a, names_b = set(a["bones"]), set(b["bones"])
    if names_a != names_b:
        problems.append(
            f"bone sets differ: only in first {sorted(names_a - names_b)[:8]}, "
            f"only in second {sorted(names_b - names_a)[:8]}"
        )

    worst = {"bone": None, "quantity": None, "delta": 0.0}
    for name in sorted(names_a & names_b):
        ba, bb = a["bones"][name], b["bones"][name]
        for q in ("head", "tail"):
            d = float(np.linalg.norm(np.array(ba[q]) - np.array(bb[q])))
            # · ANDON — on the MEASUREMENT. `d > worst["delta"]` and `d > tol` are BOTH
            # False for a NaN, so a bone whose tail is `[nan, nan, nan]` in the second
            # build produced no problem AND left `worst_bone_delta` reading
            # `{'bone': None, 'quantity': None, 'delta': 0.0}` — a determinism receipt
            # affirmatively recording a zero difference between two rigs that differ.
            require_finite(f"{name}.{q}_delta", d, GateDDeterminism, ev, positive=False)
            if d > worst["delta"]:
                worst = {"bone": name, "quantity": q, "delta": d}
            if d > tol:
                problems.append(f"{name}.{q} moved {d:.3e} (> {tol:.3e})")
        # · ANDON — the roll is the same operand one field over: `abs(nan - x)` is nan and
        # `nan > angle_tol` is False, so a non-finite roll agreed with every other roll.
        d_roll = abs(float(ba["roll"]) - float(bb["roll"]))
        require_finite(f"{name}.roll_delta", d_roll, GateDDeterminism, ev, positive=False)
        if d_roll > angle_tol:
            problems.append(f"{name}.roll differs by {d_roll:.3e}")
        if ba["parent"] != bb["parent"]:
            problems.append(f"{name}.parent {ba['parent']!r} vs {bb['parent']!r}")
        if ba["use_deform"] != bb["use_deform"]:
            problems.append(f"{name}.use_deform {ba['use_deform']} vs {bb['use_deform']}")
    ev["worst_bone_delta"] = worst

    wa, wb = a["weights"], b["weights"]
    if set(wa) != set(wb):
        problems.append(
            f"vertex-group sets differ: only in first {sorted(set(wa) - set(wb))[:8]}, "
            f"only in second {sorted(set(wb) - set(wa))[:8]}"
        )
    worst_w = {"group": None, "max_abs": 0.0, "n_differing": 0}
    for g in sorted(set(wa) & set(wb)):
        x, y = np.asarray(wa[g]), np.asarray(wb[g])
        if x.shape != y.shape:
            problems.append(f"weight array for {g!r}: shape {x.shape} vs {y.shape}")
            continue
        d = np.abs(x - y)
        # · ANDON — the weight half of the same operand. Measured on `[0.0, 1.0]` against
        # `[nan, 1.0]`: `m > weight_tol` False, `m > worst_w["max_abs"]` False, verdict
        # "two builds agree on bones, hierarchy and weights" with `worst_weight_delta`
        # reading `{'group': None, 'max_abs': 0.0}`.
        _require_finite_measurement(f"weight_delta[{g}]", d, GateDDeterminism, ev)
        m = float(d.max()) if d.size else 0.0
        if m > worst_w["max_abs"]:
            worst_w = {"group": g, "max_abs": m, "n_differing": int((d > weight_tol).sum())}
        if m > weight_tol:
            problems.append(
                f"weights on {g!r} differ by up to {m:.3e} over "
                f"{int((d > weight_tol).sum())} vertices"
            )
    ev["worst_weight_delta"] = worst_w

    if problems:
        ev["problems"] = problems[:16]
        ev["n_problems"] = len(problems)
        raise GateDDeterminism(
            f"two builds from identical inputs produced different rigs "
            f"({len(problems)} difference(s)): " + "; ".join(problems[:6])
            + (f" (+{len(problems) - 6} more)" if len(problems) > 6 else ""),
            ev,
        )
    # The verdict says what was checked and no more. Both weight dicts empty means ZERO
    # per-vertex vectors were compared — the state the skeleton-only route is always in.
    compared_groups = sorted(set(a["weights"]) & set(b["weights"]))
    ev["n_weight_groups_compared"] = len(compared_groups)
    if compared_groups:
        ev["verdict"] = "two builds agree on bones, hierarchy and weights"
    else:
        ev["verdict"] = (
            f"two builds agree on bones and hierarchy over {len(a['bones'])} bone(s); "
            f"weights NOT COMPARED — neither fingerprint carries any vertex group")
    return ev
