"""Derive anatomical landmarks from a character mesh's vertices. No bpy, so it is testable.

**Why this is measurement and not a proportion table.** A rig placed from "the elbow is at
0.62 of standing height" is a global constant governing a local feature, which this repo has
a law against. Every landmark below that a *feature of this mesh* can locate is located from
the mesh: the crotch from where the silhouette splits into two legs, the armpit from where
the arms merge into the trunk, the neck from the narrowest cross-section above the shoulders,
the ankle from where the foot flares out of the shin, the limb centrelines from the actual
vertex centroids band by band.

**Where no feature exists, the derivation says so instead of pretending.** A figure standing
with straight limbs presents no measurable elbow and no measurable knee — there is no bend to
find and, on a smooth clay mannequin, no reliable radius minimum either. Those two joints are
placed at a fraction of *that limb's own measured length*, which is the form the global-constant
law permits, and every landmark carries a `provenance` of `MEASURED` or `DERIVED(<rule>)` so a
report can say per structure which is which rather than presenting all of them as measurements.

**The topology check raises.** If the silhouette does not resolve into trunk / two arms / two
legs the derivation halts, because the alternative is a rig with invented joint positions that
every downstream gate reports green on: the names check out, the rest pose is preserved, the
build is deterministic, and the bones are simply in the wrong places.
"""

import numpy as np

from .errors import LandmarkError

#: Fraction of total X width below which two X-clusters in a band count as one structure.
GAP_FRAC = 0.02
#: A cluster holding less than this fraction of its band's vertices is noise, not anatomy.
MIN_CLUSTER_FRAC = 0.04
#: A run of bands shorter than this is a clustering artifact, not a body region.
MIN_RUN_BANDS = 3

#: Where along a limb's own measured length a joint with no measurable feature is placed.
#: Fractions of that limb's own chain length — never of standing height.
ELBOW_ALONG_ARM = 0.44
WRIST_ALONG_ARM = 0.75
KNEE_ALONG_LEG = 0.50


def _median3(seq):
    """Median filter, width 3, edges held. Kills isolated cluster-count spikes."""
    out = list(seq)
    for i in range(1, len(seq) - 1):
        out[i] = sorted(seq[i - 1:i + 2])[1]
    return out


def _runs(seq):
    """Run-length encode into (value, start_index, end_index_exclusive)."""
    out = []
    if not len(seq):
        return out
    start = 0
    for i in range(1, len(seq) + 1):
        if i == len(seq) or seq[i] != seq[start]:
            out.append((seq[start], start, i))
            start = i
    return out


def band_profile(verts, n_bands=200, gap_frac=GAP_FRAC, min_cluster_frac=MIN_CLUSTER_FRAC):
    """Slice the mesh into `n_bands` horizontal bands and cluster each band along X.

    Returns one record per band. A band's clusters are maximal groups of vertices whose
    sorted X coordinates have no gap wider than `gap_frac` of the mesh's total width — so
    "two clusters" means the silhouette genuinely separates at that height, at a threshold
    tied to the subject's own width rather than to a length in metres.
    """
    verts = np.asarray(verts, dtype=np.float64)
    if verts.ndim != 2 or verts.shape[1] != 3:
        raise LandmarkError(f"expected an (N, 3) vertex array, got shape {verts.shape}")
    if len(verts) < n_bands:
        raise LandmarkError(
            f"{len(verts)} vertices cannot be resolved into {n_bands} bands; "
            f"the profile would be mostly empty and every landmark read off noise"
        )

    lo, hi = verts.min(axis=0), verts.max(axis=0)
    height = hi[2] - lo[2]
    width = hi[0] - lo[0]
    if height <= 0 or width <= 0:
        raise LandmarkError(f"degenerate bounding box: dims {(hi - lo).tolist()}")
    gap_thr = width * gap_frac

    order = np.argsort(verts[:, 2], kind="stable")
    zs = verts[order, 2]
    bands = []
    for i in range(n_bands):
        z0 = lo[2] + height * i / n_bands
        z1 = lo[2] + height * (i + 1) / n_bands
        a = int(np.searchsorted(zs, z0, side="left"))
        b = int(np.searchsorted(zs, z1, side="right" if i == n_bands - 1 else "left"))
        idx = order[a:b]
        rec = {"i": i, "z_lo": float(z0), "z_hi": float(z1), "z": float((z0 + z1) / 2.0),
               "n": len(idx), "clusters": []}
        if len(idx) == 0:
            bands.append(rec)
            continue

        band = verts[idx]
        xorder = np.argsort(band[:, 0], kind="stable")
        bx = band[xorder]
        cuts = np.where(np.diff(bx[:, 0]) > gap_thr)[0]
        groups = np.split(np.arange(len(bx)), cuts + 1)
        floor = max(int(round(min_cluster_frac * len(band))), 8)
        clusters = []
        for g in groups:
            if len(g) < floor:
                continue
            c = bx[g]
            cx, cy = float(c[:, 0].mean()), float(c[:, 1].mean())
            # Mean radial distance from this cluster's own centroid — a real radius, not a
            # bbox width. This is the profile the sculpted ball-joints show up as peaks in,
            # and a bbox width would smear them: a ball and a flattened-but-wide section
            # give the same x extent.
            rad = np.hypot(c[:, 0] - cx, c[:, 1] - cy)
            clusters.append({
                "x_lo": float(c[:, 0].min()), "x_hi": float(c[:, 0].max()),
                "y_lo": float(c[:, 1].min()), "y_hi": float(c[:, 1].max()),
                "cx": cx, "cy": cy,
                "r_mean": float(rad.mean()), "r_p90": float(np.percentile(rad, 90)),
                "n": int(len(g)),
            })
        clusters.sort(key=lambda c: -c["n"])
        clusters = clusters[:4]
        clusters.sort(key=lambda c: c["cx"])
        rec["clusters"] = clusters
        bands.append(rec)
    return bands, {"lo": lo.tolist(), "hi": hi.tolist(), "height": float(height),
                   "width": float(width), "gap_threshold": float(gap_thr),
                   "diagonal": float(np.linalg.norm(hi - lo))}


def _region_runs(bands):
    """Find the trunk / arms+trunk / arms+legs / legs stack, or raise naming what was seen.

    Reading top-down, a standing figure's cluster count goes 1 (head, neck, shoulders) →
    3 (trunk plus two arms) → 4 (two legs plus two arms) → 2 (legs alone below the hands).
    Anything else is a subject this derivation cannot place bones on.
    """
    counts = _median3([len(b["clusters"]) for b in bands])
    # Absorb short runs into their neighbours rather than merely dropping them. Dropping
    # alone leaves the two halves of an interrupted region as two separate runs, and the
    # pattern check then rejects a perfectly ordinary figure: a limb brushing the body for
    # two bands splits the trunk+arms region into 3, 3 and reads as an unrecognisable
    # silhouette. Measured 2026-08-11 on the fixture that reproduces the subject's own
    # bands 109-110.
    smoothed = list(counts)
    for value, start, end in _runs(counts):
        if end - start >= MIN_RUN_BANDS:
            continue
        fill = smoothed[start - 1] if start > 0 else (
            counts[end] if end < len(counts) else value)
        for i in range(start, end):
            smoothed[i] = fill
    runs = [r for r in _runs(smoothed) if r[2] - r[1] >= MIN_RUN_BANDS and r[0] != 0]
    pattern = [r[0] for r in runs]
    want = [2, 4, 3, 1]  # bottom-up
    if pattern != want:
        raise LandmarkError(
            f"the silhouette does not resolve into the expected standing figure. "
            f"Reading bottom-up the cluster-count runs are {pattern}, expected {want} "
            f"(legs alone → legs+arms → trunk+arms → trunk). Every landmark below is "
            f"read off those transitions, so placing bones anyway would put joints in "
            f"invented positions that no downstream gate can see. Runs: "
            f"{[(v, s, e) for v, s, e in runs]}"
        )
    return {"legs_only": runs[0], "legs_and_arms": runs[1],
            "trunk_and_arms": runs[2], "trunk": runs[3], "counts": counts}


def _expected_counts(bands, reg):
    """The cluster count each band is expected to show, from the region map.

    ⚠ **The defect this exists to close, measured 2026-08-11 on the subject.** The region
    map is built from a median-filtered cluster count, so an isolated band whose raw
    clustering disagrees is smoothed out of the *map* while still being read by the trace.
    On this subject, bands 109 and 110 merge the right arm into the torso — the arm passes
    within the 2%-of-width gap threshold there — and the picker duly returned a merged
    trunk-plus-arm blob whose centroid sat at x = −0.004 instead of the arm's −0.150. That
    one point dragged the arc-length parameterisation sideways and put the right elbow
    almost on the body's centreline while every count and every gate stayed green. A band
    whose raw clustering disagrees with its region is not evidence about a limb, so it is
    dropped rather than trusted.
    """
    exp = [0] * len(bands)
    for key in ("legs_only", "legs_and_arms", "trunk_and_arms", "trunk"):
        value, start, end = reg[key]
        for i in range(start, end):
            exp[i] = value
    return exp


def _column_trace(bands, lo_band, hi_band, picker, expected):
    """Centroid trace of one limb column over a band range. `picker` selects its cluster."""
    trace = []
    for i in range(lo_band, hi_band):
        if len(bands[i]["clusters"]) != expected[i] or expected[i] == 0:
            continue
        c = picker(bands[i])
        if c is None:
            continue
        trace.append({"i": i, "z": bands[i]["z"], "cx": c["cx"], "cy": c["cy"],
                      "x_lo": c["x_lo"], "x_hi": c["x_hi"],
                      "y_lo": c["y_lo"], "y_hi": c["y_hi"], "n": c["n"],
                      "r_mean": c["r_mean"], "r_p90": c["r_p90"],
                      "x_width": c["x_hi"] - c["x_lo"], "y_width": c["y_hi"] - c["y_lo"]})
    return trace


def _prune_discontinuities(trace, label):
    """Drop points that are not the same limb as the point before them.

    A limb cannot move sideways by more than its own diameter between two adjacent bands
    half a percent of body height apart. The bound is that limb's own median width — a
    fraction of the structure's own size, never a length in metres — so it scales with the
    subject instead of encoding this one.
    """
    if len(trace) < 2:
        return trace, {"kept": len(trace), "dropped": 0, "max_jump": 0.0}
    widths = sorted(t["x_width"] for t in trace)
    max_jump = widths[len(widths) // 2]
    kept = [trace[0]]
    dropped = 0
    for t in trace[1:]:
        p = kept[-1]
        if np.hypot(t["cx"] - p["cx"], t["cy"] - p["cy"]) <= max_jump:
            kept.append(t)
        else:
            dropped += 1
    if len(kept) < 0.70 * len(trace):
        raise LandmarkError(
            f"{label}: only {len(kept)} of {len(trace)} bands form a continuous column "
            f"(jump bound {max_jump:.5f}, this limb's own median width). A centreline read "
            f"off a column that keeps jumping is not a centreline, and the joints placed "
            f"along it would land in invented positions with every gate still green"
        )
    return kept, {"kept": len(kept), "dropped": dropped, "max_jump": float(max_jump)}


def _point_along(trace, frac):
    """Point at `frac` of the arc length of a centroid trace, ordered high z to low z."""
    pts = [np.array([t["cx"], t["cy"], t["z"]]) for t in trace]
    if len(pts) < 2:
        raise LandmarkError("a limb centreline needs at least two bands to have a length")
    seg = [float(np.linalg.norm(pts[i + 1] - pts[i])) for i in range(len(pts) - 1)]
    total = sum(seg)
    if total <= 0:
        raise LandmarkError("limb centreline has zero length")
    target = total * frac
    acc = 0.0
    for i, s in enumerate(seg):
        if acc + s >= target:
            t = (target - acc) / s if s > 0 else 0.0
            return tuple(float(v) for v in (pts[i] + (pts[i + 1] - pts[i]) * t)), total
        acc += s
    return tuple(float(v) for v in pts[-1]), total


def facing(verts, z_ankle, height, z_ground):
    """Which way the figure faces, measured from the feet and cross-checked on the head.

    The feet are the primary instrument because a toe is unambiguous: a foot extends much
    further forward of the ankle than the heel extends behind it. The head is a cross-check
    and not a tiebreaker — a clay mannequin may have no nose at all, and a face-derived
    answer would then be reading noise.
    """
    verts = np.asarray(verts, dtype=np.float64)
    foot = verts[verts[:, 2] < z_ground + 0.03 * height]
    shin = verts[(verts[:, 2] >= z_ankle) & (verts[:, 2] < z_ankle + 0.05 * height)]
    if len(foot) == 0 or len(shin) == 0:
        raise LandmarkError("no foot or shin slab to read facing from")
    y_shin = float(shin[:, 1].mean())
    fwd = float(foot[:, 1].max()) - y_shin
    back = y_shin - float(foot[:, 1].min())
    sign = 1.0 if fwd > back else -1.0

    head = verts[verts[:, 2] > z_ground + 0.88 * height]
    head_sign, head_fwd, head_back = None, None, None
    if len(head):
        y_head = float(head[:, 1].mean())
        head_fwd = float(head[:, 1].max()) - y_head
        head_back = y_head - float(head[:, 1].min())
        head_sign = 1.0 if head_fwd > head_back else -1.0

    return {
        "facing_y_sign": sign,
        "left_x_sign": -sign,
        "foot_forward_extent": fwd,
        "foot_backward_extent": back,
        "foot_margin": abs(fwd - back),
        "head_cross_check_sign": head_sign,
        "head_forward_extent": head_fwd,
        "head_backward_extent": head_back,
        "cross_check_agrees": None if head_sign is None else bool(head_sign == sign),
        "instrument": "feet primary (toe protrusion past the shin centre); head advisory",
    }


def derive(verts, n_bands=200):
    """Every landmark this rig needs, each tagged MEASURED or DERIVED(<rule>)."""
    verts = np.asarray(verts, dtype=np.float64)
    bands, box = band_profile(verts, n_bands=n_bands)
    reg = _region_runs(bands)
    height = box["height"]

    z_ground, z_top = box["lo"][2], box["hi"][2]
    z_hand_bottom = bands[reg["legs_and_arms"][1]]["z_lo"]
    z_crotch = bands[reg["trunk_and_arms"][1]]["z_lo"]
    z_armpit = bands[reg["trunk"][1]]["z_lo"]

    # --- neck: the narrowest cross-section in the single-cluster region above the shoulders
    t0, t1 = reg["trunk"][1], reg["trunk"][2]
    trunk = [(i, bands[i]["clusters"][0]) for i in range(t0, t1) if bands[i]["clusters"]]
    if not trunk:
        raise LandmarkError("the trunk region holds no clusters to find a neck in")
    i_neck, c_neck = min(trunk, key=lambda p: p[1]["x_hi"] - p[1]["x_lo"])
    w_neck = c_neck["x_hi"] - c_neck["x_lo"]
    below = [i for i, c in trunk if i < i_neck and (c["x_hi"] - c["x_lo"]) >= 2.0 * w_neck]
    above = [i for i, c in trunk if i > i_neck and (c["x_hi"] - c["x_lo"]) >= 2.0 * w_neck]
    if not below or not above:
        raise LandmarkError(
            f"no neck found: the narrowest trunk band (width {w_neck:.5f} at z "
            f"{bands[i_neck]['z']:.5f}) is not flanked above and below by sections at "
            f"least twice as wide, so what was found is not a neck between a head and a "
            f"pair of shoulders"
        )
    i_neck_base, i_head_base = max(below), min(above)
    z_neck_base, z_head_base = bands[i_neck_base]["z"], bands[i_head_base]["z"]
    y_trunk = float(np.mean([c["cy"] for _, c in trunk]))

    # --- ankle: where the foot flares out of the shin. Measured, not a fraction.
    l0, l1 = reg["legs_only"][1], reg["legs_only"][2]
    leg_widths = [(i, max(c["x_hi"] - c["x_lo"] for c in bands[i]["clusters"]))
                  for i in range(l0, l1) if bands[i]["clusters"]]
    if len(leg_widths) < 4:
        raise LandmarkError("too few leg-only bands to locate an ankle")
    shin_ref = float(np.median([w for _, w in leg_widths[len(leg_widths) // 2:]]))
    flare = [i for i, w in leg_widths if w >= 1.6 * shin_ref]
    i_ankle = (max(flare) + 1) if flare else leg_widths[0][0]
    i_ankle = min(i_ankle, leg_widths[-1][0])
    z_ankle = bands[i_ankle]["z"]

    face = facing(verts, z_ankle, height, z_ground)
    left_sign = face["left_x_sign"]

    def side_picker(which, outer):
        """Pick the arm (outer) or leg (inner) cluster on the named body side."""
        def pick(band):
            cs = band["clusters"]
            if len(cs) < 2:
                return None
            want_positive_x = (which == "L") == (left_sign > 0)
            half = [c for c in cs if (c["cx"] > 0) == want_positive_x]
            if not half:
                return None
            key = (lambda c: abs(c["cx"]))
            return max(half, key=key) if outer else min(half, key=key)
        return pick

    a0, a1 = reg["legs_and_arms"][1], reg["trunk"][1]      # hand bottom → armpit
    g0, g1 = reg["legs_only"][1], reg["trunk_and_arms"][1]  # ground → crotch
    marks, prov = {}, {}

    def put(name, point, provenance):
        marks[name] = tuple(float(v) for v in point)
        prov[name] = provenance

    # --- trunk chain. Ends measured; the two interior spine joints split a measured span.
    z_shoulder = 0.5 * (z_armpit + z_neck_base)
    put("crotch", (0.0, y_trunk, z_crotch), "MEASURED — band where the two legs merge")
    put("neck_base", (0.0, y_trunk, z_neck_base),
        "MEASURED — lowest band above the neck minimum at ≥2× its width")
    put("head_base", (0.0, y_trunk, z_head_base),
        "MEASURED — lowest band above the neck minimum at ≥2× its width")
    put("head_top", (0.0, y_trunk, z_top), "MEASURED — mesh bbox maximum in Z")
    put("shoulder_line", (0.0, y_trunk, z_shoulder),
        "DERIVED(midpoint of the measured armpit→neck-base span)")
    span = z_neck_base - z_crotch
    put("spine_base", (0.0, y_trunk, z_crotch + span / 3.0),
        "DERIVED(1/3 of the measured crotch→neck-base span)")
    put("chest_base", (0.0, y_trunk, z_crotch + 2.0 * span / 3.0),
        "DERIVED(2/3 of the measured crotch→neck-base span)")

    expected = _expected_counts(bands, reg)
    traces, trace_health = {}, {}
    for side in ("L", "R"):
        arm = _column_trace(bands, a0, a1, side_picker(side, outer=True), expected)[::-1]
        leg = _column_trace(bands, g0, g1, side_picker(side, outer=False), expected)[::-1]
        if len(arm) < 4 or len(leg) < 4:
            raise LandmarkError(
                f"side {side}: arm trace has {len(arm)} bands and leg trace {len(leg)}; "
                f"a limb centreline read off fewer than four bands is noise"
            )
        arm, arm_health = _prune_discontinuities(arm, f"arm_{side}")
        leg, leg_health = _prune_discontinuities(leg, f"leg_{side}")
        traces[f"arm_{side}"], traces[f"leg_{side}"] = arm, leg
        trace_health[f"arm_{side}"], trace_health[f"leg_{side}"] = arm_health, leg_health

        top = arm[0]
        put(f"shoulder_{side}", (top["cx"], top["cy"], z_shoulder),
            "MEASURED(x, y from the arm's own centroid at the armpit band) + "
            "DERIVED(z from the armpit→neck-base midpoint)")
        elbow, arm_len = _point_along(arm, ELBOW_ALONG_ARM)
        wrist, _ = _point_along(arm, WRIST_ALONG_ARM)
        put(f"elbow_{side}", elbow,
            f"DERIVED({ELBOW_ALONG_ARM} of this arm's own measured centreline length "
            f"{arm_len:.5f}) — this pose presents no measurable elbow: the arm hangs "
            f"straight, so there is no bend and no reliable radius minimum to find")
        put(f"wrist_{side}", wrist,
            f"DERIVED({WRIST_ALONG_ARM} of this arm's own measured centreline length "
            f"{arm_len:.5f}) — same reason as the elbow")
        end = arm[-1]
        put(f"hand_end_{side}", (end["cx"], end["cy"], z_hand_bottom),
            "MEASURED — lowest band at which this arm's column still exists")

        hip = leg[0]
        put(f"hip_{side}", (hip["cx"], hip["cy"], z_crotch),
            "MEASURED(x, y from this leg's own centroid at the crotch band; z from the "
            "band where the legs merge)")
        ank = min(leg, key=lambda t: abs(t["z"] - z_ankle))
        put(f"ankle_{side}", (ank["cx"], ank["cy"], z_ankle),
            "MEASURED — band where the foot flares to ≥1.6× the shin's median width")
        knee, leg_len = _point_along(
            [t for t in leg if t["z"] >= z_ankle] or leg, KNEE_ALONG_LEG)
        put(f"knee_{side}", knee,
            f"DERIVED({KNEE_ALONG_LEG} of this leg's own measured hip→ankle centreline "
            f"length {leg_len:.5f}) — the leg is straight in this pose and presents no "
            f"measurable knee")

        foot = verts[(verts[:, 2] < z_ankle) &
                     ((verts[:, 0] > 0) == ((side == "L") == (left_sign > 0)))]
        if len(foot) == 0:
            raise LandmarkError(f"side {side}: no foot vertices below the ankle")
        toe_y = float(foot[:, 1].max() if face["facing_y_sign"] > 0 else foot[:, 1].min())
        put(f"toe_{side}", (ank["cx"], toe_y, z_ground),
            "MEASURED — furthest foot vertex in the measured facing direction, at ground")

    # --- head markers. Nose is measured; eyes and ears are not on a clay mannequin.
    head = verts[verts[:, 2] >= z_head_base]
    if len(head) == 0:
        raise LandmarkError("no head vertices above the measured head base")
    hz = float(head[:, 2].mean())
    face_slab = head[(head[:, 2] > hz - 0.06 * height) & (head[:, 2] < hz + 0.06 * height)]
    slab = face_slab if len(face_slab) else head
    nose_y = float(slab[:, 1].max() if face["facing_y_sign"] > 0 else slab[:, 1].min())
    put("nose", (0.0, nose_y, hz),
        "MEASURED — furthest head vertex in the measured facing direction, at mid-head height")
    head_half = float(max(abs(head[:, 0].max()), abs(head[:, 0].min())))
    head_top_z, head_base_z = float(head[:, 2].max()), z_head_base
    eye_z = head_base_z + 0.62 * (head_top_z - head_base_z)
    ear_z = head_base_z + 0.55 * (head_top_z - head_base_z)
    eye_y = nose_y - face["facing_y_sign"] * 0.25 * abs(nose_y - float(head[:, 1].mean()))
    # Marker tails. A bone needs a tail to exist at all; these five deform nothing, so
    # their tails carry no anatomy and are a short offset off their own head, sized as a
    # fraction of this head's own measured half-width.
    stub = 0.30 * head_half
    put("nose_tip", (0.0, nose_y + face["facing_y_sign"] * stub, hz),
        f"DERIVED(marker tail: {stub:.5f} = 0.30 of this head's own measured half-width, "
        f"along the measured facing direction) — a non-deforming bone still needs a tail")
    for side in ("L", "R"):
        sx = head_half * (0.35 if (side == "L") == (left_sign > 0) else -0.35)
        ex = head_half * (0.95 if (side == "L") == (left_sign > 0) else -0.95)
        put(f"eye_{side}", (sx, eye_y, eye_z),
            "DERIVED(0.35 of this head's own measured half-width, 0.62 of its own measured "
            "height) — NO EYE FEATURE IS PRESENT ON THIS MESH to measure against")
        put(f"ear_{side}", (ex, float(head[:, 1].mean()), ear_z),
            "DERIVED(0.95 of this head's own measured half-width, 0.55 of its own measured "
            "height) — NO EAR FEATURE IS PRESENT ON THIS MESH to measure against")
        put(f"eye_{side}_tip", (sx, eye_y + face["facing_y_sign"] * stub, eye_z),
            "DERIVED(marker tail, 0.30 of this head's own measured half-width)")
        put(f"ear_{side}_tip", (ex + (stub if ex > 0 else -stub),
                                float(head[:, 1].mean()), ear_z),
            "DERIVED(marker tail, 0.30 of this head's own measured half-width)")

    return {
        "landmarks": marks,
        "provenance": prov,
        "facing": face,
        "box": box,
        "regions": {
            "z_ground": float(z_ground), "z_hand_bottom": float(z_hand_bottom),
            "z_ankle": float(z_ankle), "z_crotch": float(z_crotch),
            "z_armpit": float(z_armpit), "z_shoulder": float(z_shoulder),
            "z_neck_base": float(z_neck_base), "z_neck_min": float(bands[i_neck]["z"]),
            "neck_min_width": float(w_neck),
            "z_head_base": float(z_head_base), "z_top": float(z_top),
            "cluster_runs": {k: [int(v[0]), int(v[1]), int(v[2])]
                             for k, v in reg.items() if k != "counts"},
        },
        "traces": traces,
        "trace_health": trace_health,
        "n_bands": n_bands,
    }
