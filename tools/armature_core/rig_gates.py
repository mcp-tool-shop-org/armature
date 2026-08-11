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

#: Gate P's epsilon, as a fraction of the mesh's own bbox diagonal. Not a length in
#: metres: a global constant must not govern a local feature.
REST_POSE_EPSILON_FRAC = 1e-4
#: Gate D's tolerances. Lengths scale with the subject; weights are a unit interval.
DETERMINISM_LENGTH_FRAC = 1e-6
DETERMINISM_WEIGHT_TOL = 1e-6
DETERMINISM_ANGLE_TOL = 1e-6


def gate_n_names(observed, registered, where):
    """Gate N · ANDON — every registered site is a bone with exactly that name, and the
    rig carries nothing that was not registered.

    `observed` is the sequence of bone names actually present; `registered` the committed
    list; `where` names what was inspected, so a failure says whether the defect is in the
    build or in the export.
    """
    observed = list(observed)
    registered = list(registered)
    ev = {"where": where, "n_observed": len(observed), "n_registered": len(registered)}

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


def gate_p_rest_pose(source_world, bound_world, bbox_diagonal,
                     epsilon_frac=REST_POSE_EPSILON_FRAC):
    """Gate P · ANDON — binding the mesh did not move it.

    `source_world` and `bound_world` are (N, 3) world-space vertex arrays: the mesh as
    imported, and the same mesh evaluated with the armature modifier live at the rest
    pose. Max displacement must be within `epsilon_frac` of the mesh's own bbox diagonal.
    """
    a = np.asarray(source_world, dtype=np.float64)
    b = np.asarray(bound_world, dtype=np.float64)
    ev = {"epsilon_frac": epsilon_frac, "bbox_diagonal": float(bbox_diagonal),
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
    if not (bbox_diagonal > 0):
        raise GatePRestPose(
            f"bbox diagonal is {bbox_diagonal}; the threshold is a fraction of the mesh's "
            f"own size and cannot be computed from a degenerate one",
            ev,
        )

    d = np.linalg.norm(b - a, axis=1)
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


def gate_p_evaluation_is_live(rest_world, probe_world, bbox_diagonal, min_frac=1e-4):
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
    """
    a = np.asarray(rest_world, dtype=np.float64)
    b = np.asarray(probe_world, dtype=np.float64)
    ev = {"min_frac": min_frac, "bbox_diagonal": float(bbox_diagonal)}
    if a.shape != b.shape:
        raise GatePRestPose(
            f"liveness probe returned a different vertex array ({a.shape} vs {b.shape}); "
            f"the probe cannot say whether the deform is live",
            ev,
        )
    d = np.linalg.norm(b - a, axis=1)
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


def gate_d_determinism(a, b, bbox_diagonal,
                       length_frac=DETERMINISM_LENGTH_FRAC,
                       weight_tol=DETERMINISM_WEIGHT_TOL,
                       angle_tol=DETERMINISM_ANGLE_TOL):
    """Gate D · ANDON — a second build from identical inputs produced the same rig.

    Compared as parsed objects. Lengths are toleranced as a fraction of the subject's own
    bbox diagonal; weights and rolls on their own natural units.
    """
    tol = length_frac * float(bbox_diagonal)
    ev = {"length_tolerance": tol, "weight_tolerance": weight_tol,
          "angle_tolerance": angle_tol, "bbox_diagonal": float(bbox_diagonal),
          "n_bones_a": len(a["bones"]), "n_bones_b": len(b["bones"])}
    problems = []

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
            if d > worst["delta"]:
                worst = {"bone": name, "quantity": q, "delta": d}
            if d > tol:
                problems.append(f"{name}.{q} moved {d:.3e} (> {tol:.3e})")
        if abs(ba["roll"] - bb["roll"]) > angle_tol:
            problems.append(f"{name}.roll differs by {abs(ba['roll'] - bb['roll']):.3e}")
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
    ev["verdict"] = "two builds agree on bones, hierarchy and weights"
    return ev
