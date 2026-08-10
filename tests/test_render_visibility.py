"""The regression fixture for the defect G4 caught on 2026-08-10.

Selecting subject geometry by `type == "MESH"` swept up the decoy Blender's glTF
importer leaves in a `hide_render=True` collection. That inflated the auto camera
radius and made G4's expected bbox far larger than the rendered mask, so G4 fired on
frame 0 of the character arm. This pins the fix.
"""

import json
import os
import subprocess

import pytest

from conftest import BLENDER, REPO

pytestmark = pytest.mark.skipif(
    not os.path.isfile(BLENDER), reason=f"Blender not found at {BLENDER}"
)

SCRIPT = os.path.join(REPO, "tests", "blender", "check_visibility.py")


@pytest.fixture(scope="module")
def vis():
    proc = subprocess.run(
        [BLENDER, "-b", "-P", SCRIPT], capture_output=True, text=True, timeout=300
    )
    lines = [l for l in proc.stdout.splitlines() if l.startswith("VISIBILITY ")]
    assert lines, f"no result\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
    return json.loads(lines[-1][len("VISIBILITY "):])


def test_only_the_subject_survives_the_filter(vis):
    assert vis["render_visible_names"] == ["subject"]


def test_the_naive_filter_would_have_returned_all_four(vis):
    """If this ever stops being true the fixture has gone slack and is no longer
    testing anything."""
    assert len(vis["all_mesh_names"]) == 4


def test_the_gltf_importers_hidden_collection_is_excluded(vis):
    assert "gltf_decoy" not in vis["render_visible_names"]


def test_object_level_hide_render_is_excluded(vis):
    assert "obj_hidden" not in vis["render_visible_names"]


def test_render_hidden_but_viewport_visible_is_excluded(vis):
    """`visible_get()` is viewport visibility. A predicate built on it would keep this
    decoy, and the instrument would disagree with the renderer again."""
    assert vis["viewport_visible_get"]["viewport_visible_decoy"] is True
    assert "viewport_visible_decoy" not in vis["render_visible_names"]


def test_the_decoys_would_have_moved_the_framing(vis):
    """The bounding sphere is what auto_radius fits, so a decoy does not merely add a
    stray object — it reframes the shot."""
    assert vis["naive_sphere_radius"] > vis["filtered_sphere_radius"] * 3
    assert vis["filtered_sphere_radius"] == pytest.approx(0.8660254, rel=1e-4)
