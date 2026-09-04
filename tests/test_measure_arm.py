"""The projection maths under measure_arm's ground truth — one copy, not a third one.

`measure_arm.half_fovs` was a third implementation of Blender's AUTO sensor fit, beside
`armature_core.blender_scene.half_fovs` and `armature_core.framing.half_fovs`. Its docstring
justified the duplication by naming a test that pins the copies together — and there was no
`tests/test_measure_arm.py` in the tree; a repo-wide grep for `test_measure_arm` found only
that docstring. `tests/test_framing.py::test_half_fovs_matches_blenders` pins framing's copy
against blender_scene's, so two of the three were held and the third was held by nothing.

Measured on 2026-09-03, all three agreed at 832x480, 480x832, 1024x1024 and 1280x720 — so
what this file records is an absent guard, not a live divergence. The absent guard matters
because the direction it leaves open is silent: a change to Blender's AUTO convention lands
in the two pinned copies, misses this one, and `measure_arm`'s projected ground truth — what
the Gate 0 sheet marks up — is quietly off with every test green.

The identity assertion is the load-bearing one. Numerical agreement is what the old comment
claimed and would have been satisfied by a copy that had not drifted *yet*; there being one
function is what makes drift impossible.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import measure_arm as MA  # noqa: E402
from armature_core import framing  # noqa: E402

LENS, SENSOR = 50.0, 36.0
CASES = ((832, 480), (480, 832), (1024, 1024), (1280, 720))


def test_measure_arm_uses_framings_pinned_copy_rather_than_its_own():
    """There is no third implementation to drift: it is the same function object."""
    assert MA.half_fovs is framing.half_fovs


def test_the_projection_still_agrees_with_blenders_auto_fit_on_every_case():
    """The numeric pin the old docstring claimed, over the same landscape / portrait /
    square cases test_framing.py uses — through whichever copy measure_arm now calls."""
    for w, h in CASES:
        assert MA.half_fovs(LENS, SENSOR, w, h) == framing.half_fovs(LENS, SENSOR, w, h)


def test_the_sensor_sits_on_the_longer_axis_which_is_the_whole_auto_convention():
    """What would this look like if the code were wrong in the way this catches? A copy
    that put the sensor on the WIDTH always would give the same answer on a square frame
    and the wrong one in portrait — so the two orientations are asserted apart."""
    land_x, land_y = MA.half_fovs(LENS, SENSOR, 832, 480)
    port_x, port_y = MA.half_fovs(LENS, SENSOR, 480, 832)
    assert land_x > land_y
    assert port_y > port_x
    assert land_x == pytest.approx(port_y)


def test_project_puts_the_camera_target_at_the_centre_of_frame():
    """The consumer, exercised once: a wrong half-FOV would move this off centre, and this
    is the ground truth the Gate 0 sheet marks up."""
    import numpy as np

    target = (0.0, 0.0, 0.0)
    M = np.array([[1.0, 0.0, 0.0, 0.0],
                  [0.0, 0.0, -1.0, -4.0],
                  [0.0, 1.0, 0.0, 0.0],
                  [0.0, 0.0, 0.0, 1.0]])  # looks down -Z_local toward +Y_world
    px, depth = MA.project([target], M, LENS, SENSOR, 832, 480)
    assert depth[0] == pytest.approx(4.0)
    assert px[0][0] == pytest.approx(416.0)
    assert px[0][1] == pytest.approx(240.0)
