"""Gate BACKDROP's thresholds, checked against a measured round trip rather than a guess.

`render_start_frame` composites the authored master over a plate through Blender's own
compositor, so the plate is linearised on load and re-encoded by the Standard view transform
on the way out. Gate BACKDROP then asks whether what ended up behind the performer IS the
plate — and the tolerance it asks that question with is a fact about Blender's colour
pipeline, not a preference. Guessed too tight it halts good runs; guessed too loose it sleeps
through the failure it exists for.

So the numbers come from a render. `tests/blender/check_plate_composite.py` drives the real
`wire_plate_composite` on a synthetic scene and reports both the working case and its
falsifier — the same measurement taken on the flat composite, which is exactly what an
un-wired compositor writes to disk.

Compensator: the Blender script writes four files under `outputs/_test_plate_composite/`.
Compensator: delete that directory; owner: the executor session.
"""

import json
import os
import subprocess

import pytest

from conftest import BLENDER, REPO

pytestmark = pytest.mark.skipif(
    not os.path.isfile(BLENDER), reason=f"Blender not found at {BLENDER}"
)

SCRIPT = os.path.join(REPO, "tests", "blender", "check_plate_composite.py")


@pytest.fixture(scope="module")
def measured():
    proc = subprocess.run(
        [BLENDER, "-b", "-P", SCRIPT], capture_output=True, text=True, timeout=600
    )
    lines = [l for l in proc.stdout.splitlines() if l.startswith("PLATE_COMPOSITE ")]
    assert lines, f"no result\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
    return json.loads(lines[-1][len("PLATE_COMPOSITE "):])


def test_the_plate_arrives_behind_the_performer(measured):
    """The working case. Anything at or under the tolerance means the pixels behind the
    figure are the plate's own, through the whole linearise-composite-re-encode trip."""
    assert measured["void_vs_plate_255"] <= measured["gate_constants"]["tol_255"]


def test_an_unwired_compositor_would_be_nowhere_near_passing(measured):
    """THE falsifier. Without it, a green result above proves only that two numbers were
    both small — which they would also be if the plate happened to resemble the void. This
    is the same measurement taken on the flat composite: the file an un-wired compositor
    writes. The gate is only worth having if these two land on opposite sides of it."""
    tol = measured["gate_constants"]["tol_255"]
    assert measured["unwired_void_vs_plate_255"] > tol * 10, (
        "the fixture can no longer tell a working compositor from a broken one")


def test_the_separation_guard_has_room_on_a_real_plate(measured):
    """Gate BACKDROP refuses to pass when the plate and the flat fallback are the same
    picture over the measured region. A plate with any content at all clears this by a wide
    margin; if it stopped doing so, the guard would be firing on good runs."""
    assert (measured["plate_vs_flat_255"]
            > measured["gate_constants"]["min_separation_255"] * 5)


def test_the_plate_changes_only_the_void(measured):
    """One variable per rung, checked in pixels. Alpha-over must not touch the performer:
    the only difference across the solid region is the antialiased silhouette blending
    against a different background, which is a fraction of one 8-bit level."""
    assert measured["subject_comp_vs_flat_255"] < 2.0


def test_there_is_a_void_and_a_subject_to_measure_over(measured):
    """Both fractions non-trivial, or every number above is a mean over almost nothing."""
    assert 0.05 < measured["transparent_fraction"] < 0.95
    assert measured["subject_fraction"] > 0.05


def test_the_gate_itself_passes_on_the_measured_numbers(measured):
    """The thresholds are checked against the render, but the CHECKING is what ships — so
    the measured values are driven through the real gate rather than compared by hand."""
    from armature_core import startframe as SF

    ev = SF.gate_backdrop(
        void_vs_plate_255=measured["void_vs_plate_255"],
        plate_vs_flat_255=measured["plate_vs_flat_255"],
        transparent_fraction=measured["transparent_fraction"],
        why="the calibration plate",
        tol_255=measured["gate_constants"]["tol_255"],
        min_separation_255=measured["gate_constants"]["min_separation_255"])
    assert "the plate is behind the performer" in ev["verdict"]

    with pytest.raises(SF.BackdropGate):
        SF.gate_backdrop(
            void_vs_plate_255=measured["unwired_void_vs_plate_255"],
            plate_vs_flat_255=measured["plate_vs_flat_255"],
            transparent_fraction=measured["transparent_fraction"],
            why="the calibration plate",
            tol_255=measured["gate_constants"]["tol_255"],
            min_separation_255=measured["gate_constants"]["min_separation_255"])
