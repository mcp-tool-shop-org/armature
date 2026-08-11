"""Find the subject's own sculpted ball-joints and snap the skeleton's pivots onto them.

**The failure this module exists to correct, named plainly: placement by proportion when the
subject carries its own markers.** E07's first skeleton put the elbow at 0.44 along the arm's
measured centreline because a figure standing with straight limbs presents no *bend* to read a
joint from. That reasoning was right about silhouettes and wrong about this subject: he is a
clay artist's mannequin and he is **covered in sculpted ball-joints**. The balls are the ground
truth, and they were sitting in the mesh the whole time. The Director caught it by eye at 1:1 —
"This looks like it's not lined up properly" — and the measurement put the elbows **27–30 % of
the upper arm's own length** away from their balls.

**Standing method for this character class:** where the subject carries a sculpted marker, the
marker is the pivot. Proportion heuristics are the fallback for sites that genuinely have no
marker, and those sites are named in the report rather than left to look measured.

**How a ball is found.** The mannequin's joints are separate shells in the mesh. Welding the
glTF seam-splits collapses the file's 21,514 vertex-split shells to the asset's real 67 pieces,
and among those the joints stand out as near-spherical: bbox aspect near 1, and a small residual
around a least-squares sphere fit. The face carries small spherical pieces too, so a candidate
must also be the right *size* for the limb it is claimed for — a fraction of that limb's own
measured cross-section radius, never a length in metres.

Nothing here is a gate. It produces an offset table; the Director rules on the sheet.
"""

import numpy as np

from .errors import LandmarkError

#: A candidate must be this round to be a ball at all (min bbox dimension over max).
BALL_MIN_ASPECT = 0.58
#: …and sit this close to its own least-squares sphere (std of radii over mean radius).
BALL_MAX_RESIDUAL = 0.20
#: …and carry at least this many vertices, so a 6-vertex sliver cannot become a pivot.
BALL_MIN_VERTS = 100

#: A ball may be claimed for a site only if its radius lies in this window, expressed as a
#: multiple of THAT limb's own measured cross-section radius. Keeps the face's 0.006-radius
#: pieces from being claimed as elbows without naming a length in metres anywhere.
BALL_RADIUS_WINDOW = (0.5, 2.5)

#: …and only if it lies within this fraction of that segment's own length from the site's
#: current estimate. Per-structure, so a long thigh searches further than a short forearm.
SNAP_SEARCH_FRACTION = 0.35

#: The twelve limb pivots this subject carries balls for, each with the trace that sizes it
#: and the segment whose length bounds its search. Torso, neck, head, hands, feet and face
#: are absent on purpose: this mannequin sculpts no ball at any of them.
SNAPPABLE = {
    "shoulder_L": ("arm_L", ("shoulder_L", "elbow_L")),
    "elbow_L":    ("arm_L", ("shoulder_L", "elbow_L")),
    "wrist_L":    ("arm_L", ("elbow_L", "wrist_L")),
    "shoulder_R": ("arm_R", ("shoulder_R", "elbow_R")),
    "elbow_R":    ("arm_R", ("shoulder_R", "elbow_R")),
    "wrist_R":    ("arm_R", ("elbow_R", "wrist_R")),
    "hip_L":      ("leg_L", ("hip_L", "knee_L")),
    "knee_L":     ("leg_L", ("hip_L", "knee_L")),
    "ankle_L":    ("leg_L", ("knee_L", "ankle_L")),
    "hip_R":      ("leg_R", ("hip_R", "knee_R")),
    "knee_R":     ("leg_R", ("hip_R", "knee_R")),
    "ankle_R":    ("leg_R", ("knee_R", "ankle_R")),
}


def sphere_fit(points):
    """Least-squares sphere through a vertex cloud: centre, mean radius, relative residual."""
    p = np.asarray(points, dtype=np.float64)
    if p.ndim != 2 or p.shape[1] != 3 or len(p) < 4:
        raise LandmarkError(f"a sphere fit needs at least 4 points in 3D, got {p.shape}")
    a = np.hstack([2.0 * p, np.ones((len(p), 1))])
    sol, *_ = np.linalg.lstsq(a, (p ** 2).sum(axis=1), rcond=None)
    centre = sol[:3]
    d = np.linalg.norm(p - centre, axis=1)
    mean = float(d.mean())
    return centre, mean, float(d.std() / mean) if mean > 0 else float("inf")


def describe_shells(verts, labels):
    """One record per connected shell: sphere fit, bbox aspect, vertex count."""
    verts = np.asarray(verts, dtype=np.float64)
    labels = np.asarray(labels)
    out = []
    for shell in np.unique(labels):
        idx = np.flatnonzero(labels == shell)
        if len(idx) < 4:
            continue
        p = verts[idx]
        dims = p.max(axis=0) - p.min(axis=0)
        centre, radius, residual = sphere_fit(p)
        out.append({
            "shell": int(shell), "n": int(len(idx)),
            "centre": [float(v) for v in centre], "radius": radius,
            "relative_residual": residual,
            "aspect": float(dims.min() / dims.max()) if dims.max() > 0 else 0.0,
            "dims": [float(v) for v in dims],
        })
    out.sort(key=lambda r: -r["n"])
    return out


def candidate_balls(shells, min_aspect=BALL_MIN_ASPECT, max_residual=BALL_MAX_RESIDUAL,
                    min_verts=BALL_MIN_VERTS):
    """The shells round enough, tight enough and big enough to be a sculpted joint."""
    return [s for s in shells
            if s["aspect"] >= min_aspect
            and s["relative_residual"] <= max_residual
            and s["n"] >= min_verts]


def _limb_radius(derived, trace_key, z):
    """That limb's own measured cross-section radius nearest a height. Sizes the window."""
    trace = derived["traces"].get(trace_key) or []
    if not trace:
        raise LandmarkError(f"no trace {trace_key!r} to size a ball against")
    near = min(trace, key=lambda p: abs(p["z"] - z))
    return float(near["r_mean"])


def snap_sites_to_balls(derived, balls, snappable=SNAPPABLE,
                        radius_window=BALL_RADIUS_WINDOW,
                        search_fraction=SNAP_SEARCH_FRACTION):
    """Move each limb pivot onto its sculpted ball. Returns (new landmarks, offset table).

    Greedy by match distance so the most confident pairing claims its ball first, and every
    ball is claimed at most once — otherwise a single prominent shoulder ball could be handed
    to the shoulder *and* the elbow, and the table would report two confident matches to the
    same piece of geometry.

    A site with no qualifying ball keeps its heuristic position and is reported as
    `matched: false`, so the report can name which pivots are measured and which are not.
    """
    marks = dict(derived["landmarks"])
    pool = list(balls)

    proposals = []
    for site, (trace_key, (seg_a, seg_b)) in snappable.items():
        if site not in marks:
            raise LandmarkError(f"snappable site {site!r} is not a derived landmark")
        here = np.asarray(marks[site], dtype=np.float64)
        seg_len = float(np.linalg.norm(np.asarray(marks[seg_a]) - np.asarray(marks[seg_b])))
        if seg_len <= 0:
            raise LandmarkError(f"segment {seg_a}->{seg_b} has zero length; it cannot bound "
                                f"a search radius for {site!r}")
        limb_r = _limb_radius(derived, trace_key, here[2])
        lo, hi = radius_window[0] * limb_r, radius_window[1] * limb_r
        tol = search_fraction * seg_len
        for ball in pool:
            if not (lo <= ball["radius"] <= hi):
                continue
            d = float(np.linalg.norm(np.asarray(ball["centre"]) - here))
            if d <= tol:
                proposals.append((d, site, ball, seg_len, limb_r, tol))
    proposals.sort(key=lambda t: t[0])

    taken_sites, taken_balls, table = set(), set(), {}
    for d, site, ball, seg_len, limb_r, tol in proposals:
        if site in taken_sites or id(ball) in taken_balls:
            continue
        taken_sites.add(site)
        taken_balls.add(id(ball))
        before = np.asarray(marks[site], dtype=np.float64)
        after = np.asarray(ball["centre"], dtype=np.float64)
        offset = after - before
        table[site] = {
            "matched": True,
            "before": [float(v) for v in before],
            "after": [float(v) for v in after],
            "offset_vector": [float(v) for v in offset],
            "offset": float(np.linalg.norm(offset)),
            "offset_as_fraction_of_segment": float(np.linalg.norm(offset) / seg_len),
            "segment": f"{snappable[site][1][0]}->{snappable[site][1][1]}",
            "segment_length": seg_len,
            "ball_radius": ball["radius"],
            "ball_vertices": ball["n"],
            "ball_aspect": ball["aspect"],
            "ball_relative_residual": ball["relative_residual"],
            "limb_cross_section_radius": limb_r,
            "search_tolerance": tol,
        }
        marks[site] = tuple(float(v) for v in after)

    for site, (trace_key, (seg_a, seg_b)) in snappable.items():
        if site in table:
            continue
        table[site] = {
            "matched": False,
            "before": [float(v) for v in marks[site]],
            "after": [float(v) for v in marks[site]],
            "offset": 0.0,
            "offset_as_fraction_of_segment": 0.0,
            "segment": f"{seg_a}->{seg_b}",
            "reason": ("no shell qualified as this site's ball: none was round enough, the "
                       "right size for this limb, and inside the search radius. The pivot "
                       "keeps its heuristic position and is NOT a measured marker."),
        }
    return marks, table


def verdict(table):
    """Instrument-or-subject, decided from the spread of the offsets rather than asserted.

    **A projection or overlay error moves every marker by the same transform.** If the sheet's
    overlay were the defect, every offset would be near-equal — that is what a wrong transform
    does. Offsets that differ by an order of magnitude between joints cannot come from one bad
    transform, so they are the subject's: the pivots really are in the wrong places.
    """
    matched = {k: v for k, v in table.items() if v["matched"]}
    if not matched:
        return {"ruling": "NO BALLS MATCHED — neither hypothesis is testable from this table"}
    offs = np.array([v["offset"] for v in matched.values()])
    fracs = np.array([v["offset_as_fraction_of_segment"] for v in matched.values()])
    vectors = np.array([v["offset_vector"] for v in matched.values()])
    spread = float(offs.max() / offs.min()) if offs.min() > 0 else float("inf")
    common = vectors.mean(axis=0)
    residual_after_common = np.linalg.norm(vectors - common, axis=1)
    return {
        "n_matched": len(matched),
        "offset_min": float(offs.min()), "offset_max": float(offs.max()),
        "offset_spread_ratio": spread,
        "fraction_of_segment_min": float(fracs.min()),
        "fraction_of_segment_max": float(fracs.max()),
        "best_common_translation": [float(v) for v in common],
        "residual_after_removing_common_translation_max":
            float(residual_after_common.max()),
        "ruling": (
            "THE SUBJECT — the pivots are genuinely misplaced. A projection or overlay error "
            "applies one transform to every marker and would produce near-equal offsets; "
            "these differ by a factor of "
            f"{spread:.1f} between joints, and removing the best single translation still "
            f"leaves up to {residual_after_common.max():.4f} of error."
            if spread > 3.0 else
            "THE INSTRUMENT — the offsets are near-uniform, which is what one wrong transform "
            "looks like. Check the overlay projector before moving any bone."
        ),
    }
