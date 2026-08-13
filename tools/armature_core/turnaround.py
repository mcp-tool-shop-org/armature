"""The turnaround set: which azimuths, and whether each view really carries alpha.

No bpy. A turnaround is a reference kit — the thing a route is *handed* when it must
bind identity — so the two questions this module answers are the two that decide whether
the kit is usable at all:

    which azimuths does the set stand on, and does each view carry a real alpha channel?

**Why the alpha question needs its own andon, per view.** `startframe.gate_alpha` already
makes this argument for a single frame and it is the same argument here, with one addition
a per-frame gate cannot make: a turnaround fails *per view*. Nothing else in the render
path can tell a genuine RGBA render from a baked void with a fourth channel full of 255s —
the files open, the dimensions are right, the figure is in every one of them, and a contact
sheet of eight baked views looks exactly like a contact sheet of eight authored ones. That
is not hypothetical: the set this module exists to replace
(`E:\\AI\\training\\facet_E33\\turn_final\\`) is eight RGBA PNGs whose alpha extrema are
(255, 255) on all eight, with a flat grey void baked into the RGB. It was consumed as a
reference set and nothing anywhere reported a defect.

**The andon goes on the direction the invariant does not bound.** Both directions, because
each is silent in the other's presence:

* `alpha_min == 255` — no pixel is transparent. This is the baked-void defect exactly, and
  it is what the Director's ruling of 2026-08-12 forbids.
* `alpha_max < 255` — no pixel is opaque. A render nobody is in, or one whose subject
  material went transparent, is well-formed, correctly sized, non-empty as a file, and
  carries a beautifully varied alpha channel. A gate written only against the first clause
  passes it.

Both are structural facts about the extrema, not thresholds: neither can be tuned toward a
number by anyone who does not like the result. The opaque fraction *is* a magnitude and is
therefore **reported and never gated** — no calibrated threshold for how much of a portrait
frame a mannequin should fill exists on this rig, and inventing one here would be a pass
condition the experiment could move.
"""

from .errors import GateFailure


class TurnaroundGate(GateFailure):
    """A turnaround set is not the whole set of distinct views it claims to be."""

    gate = "TURN"


class TurnaroundAlphaGate(TurnaroundGate):
    """A turnaround view does not carry the alpha the authored-RGBA law requires."""

    gate = "ALPHA"


#: Alpha is measured in 8-bit counts, so the two saturated values are the two that matter.
OPAQUE = 255

#: Below this (on a 0..1 alpha plane) a pixel counts as transparent for the reported
#: fraction. The same threshold `render_start_frame` uses, so the two numbers compare.
TRANSPARENT_BELOW = 0.5


def orbit_azimuths(n_views, start_deg, sweep_deg):
    """The azimuth of each view, in order.

    `sweep_deg` is the angle of the **closed path**: view `n_views` would coincide with
    view 0, so a 360-degree sweep does not render the first view twice. This is the
    convention `blender_scene.orbit_azimuth` states, restated here because that module
    imports bpy and this one must not — `test_turnaround.py` pins the two formulas
    together so the duplication cannot drift silently.
    """
    n = int(n_views)
    if n < 1:
        raise TurnaroundGate(
            f"a turnaround of {n} view(s) is not a turnaround", {"n_views": n})
    return [float(start_deg) + float(sweep_deg) * (i / float(n)) for i in range(n)]


def gate_view_alpha(view_index, alpha_min, alpha_max, transparent_fraction, path=None):
    """Gate ALPHA · ANDON, per view — this view is authored RGBA, not a baked void.

    Raises on either saturated extreme; reports the measured numbers either way, because
    "it carries alpha" and "it carries alpha on four pixels" are different facts about a
    reference view, and the second one is a warning for the Director's eye rather than a
    verdict this gate should invent.
    """
    lo, hi = int(alpha_min), int(alpha_max)
    ev = {
        "gate": "ALPHA", "view": int(view_index), "path": path,
        "alpha_extrema": [lo, hi],
        "transparent_fraction": float(transparent_fraction),
        "opaque_fraction": 1.0 - float(transparent_fraction),
        "note": ("film_transparent makes the world background alpha=0 while the subject's "
                 "own geometry stays opaque, so a solid figure standing in a transparent "
                 "field is the expected shape"),
    }
    if lo >= OPAQUE:
        raise TurnaroundAlphaGate(
            f"view {view_index} has alpha extrema ({lo}, {hi}): NO pixel is transparent, "
            "so this is not an RGBA render — it is a baked void with a fourth channel. "
            "`film_transparent` did not take effect, and every check after this one "
            "passes on the file anyway: it opens, it is the right size, the figure is in "
            "it, and a contact sheet cannot tell it from an authored view", ev)
    if hi < OPAQUE:
        raise TurnaroundAlphaGate(
            f"view {view_index} has alpha extrema ({lo}, {hi}): NO pixel is opaque, so "
            "nothing solid was rendered into this view. The file is well-formed, "
            "correctly sized, non-empty, and its alpha channel is richly varied — a gate "
            "written only against the flat-255 defect passes it", ev)
    ev["verdict"] = (f"view {view_index} authored RGBA; extrema ({lo}, {hi}), "
                     f"{float(transparent_fraction):.4f} of the frame transparent")
    return ev


def gate_set_distinct(view_records, expected):
    """Gate TURN · ANDON — the set is the whole turnaround, and every view is distinct.

    Runs after the views and **before the manifest**, because the manifest is what makes a
    run look finished (`stage_render`'s own doctrine, and the reason its G2 sits there).

    Two clauses, both silent elsewhere. A short set is the obvious one. The second is
    **duplicate content**: if the camera failed to move — an orbit helper handed the same
    azimuth every time, a scene frame that never advanced, a camera matrix assigned once
    outside the loop — the run writes `expected` well-formed RGBA files, every per-view
    alpha gate passes on every one of them, the count is right, and the set is eight copies
    of the front view. Nothing else here looks at whether the views differ from each other.
    """
    ev = {"gate": "TURN", "expected": int(expected), "observed": len(view_records)}
    if len(view_records) != int(expected):
        raise TurnaroundGate(
            f"the set carries {len(view_records)} view(s), not {expected}", ev)
    digests = [r.get("sha256") for r in view_records]
    if any(d is None for d in digests):
        raise TurnaroundGate(
            "a view record carries no sha256, so the set can be checked neither for "
            "duplicates nor for pinning", ev)
    ev["distinct_sha256"] = len(set(digests))
    if len(set(digests)) != len(digests):
        dupes = sorted({d for d in digests if digests.count(d) > 1})
        raise TurnaroundGate(
            f"{len(digests) - len(set(digests))} of {len(digests)} views are "
            f"byte-identical to another view ({', '.join(d[:12] for d in dupes)}): the "
            "camera did not move between them. Every per-view check passes on this set — "
            "the files are RGBA, the count is right, the figure is in all of them", ev)
    ev["verdict"] = f"{len(digests)} distinct views, as many as were asked for"
    return ev
