"""The procedural floor's two claims, checked against a render rather than a comment.

E12's A1w arm gives the previz floor a real material so the frame reads as one room instead
of a figure standing in front of a photograph. Two things about that material go on the
record, and both are the kind that read as true in a provenance file while being false in
the file that gets uploaded:

* it reads **no image**, which is the licence claim — a downloaded wood texture is the most
  ordinary way for a CC-BY-NC or research-only asset to enter a pipeline that bans both;
* it is **wood**, not a flat fill — a mis-wired node graph resolves to a single colour,
  renders cleanly, passes every gate, and is the studio slab in a different shade.

Compensator: the Blender script writes two PNGs under `outputs/_test_floor_material/`.
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

SCRIPT = os.path.join(REPO, "tests", "blender", "check_floor_material.py")


@pytest.fixture(scope="module")
def measured():
    proc = subprocess.run(
        [BLENDER, "-b", "-P", SCRIPT], capture_output=True, text=True, timeout=600
    )
    lines = [l for l in proc.stdout.splitlines() if l.startswith("FLOOR_MATERIAL ")]
    assert lines, f"no result\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
    return json.loads(lines[-1][len("FLOOR_MATERIAL "):])


def test_the_material_reads_no_image_and_the_file_holds_none(measured):
    """THE licence clause, checked twice over. The node inventory says the graph has no
    image node; the datablock list says the FILE has no image at all, which catches an
    image pulled in by any route the node check would miss."""
    assert measured["reads_image_file"] is False
    assert measured["image_datablocks_in_file"] == []
    assert not [n for n in measured["node_types"] if "TexImage" in n or "TexEnvironment" in n]


def test_every_node_in_it_is_procedural(measured):
    """Named rather than counted, so a later edit that swaps a noise node for a texture
    lookup fails here instead of at the licence map."""
    assert set(measured["node_types"]) == {
        "ShaderNodeBsdfPrincipled", "ShaderNodeMapping", "ShaderNodeOutputMaterial",
        "ShaderNodeTexCoord", "ShaderNodeTexNoise", "ShaderNodeTexWave",
        "ShaderNodeValToRGB"}


def test_the_floor_actually_has_grain_rather_than_being_a_flat_fill(measured):
    """The second claim, measured against the mis-wire it exists to catch.

    The control is the SAME material with the ramp unlinked from the shader — a graph that
    resolves to one colour, which is what a broken wiring actually produces. Comparing
    against the pale default instead would compare brightness, not texture.

    And the quantity is high-frequency content, not plain variance. At 6 degrees of
    elevation the floor carries a strong near-to-horizon brightness gradient that dominates
    `std` outright: measured, the mis-wired control returns std 0.0291 against the real
    material's 0.0324 — a ratio of 1.11, on which no honest threshold can be set. A discrete
    Laplacian is zero on a gradient and non-zero on texture, and separates them 5.7 to 1.
    """
    assert measured["wood_floor_hf"] > measured["flat_floor_hf"] * 3


def test_the_grain_comparison_is_made_at_equal_brightness(measured):
    """Guard on the fixture above: the flat control only isolates texture if it sits at the
    same darkness as the real material. If it drifted, the ratio would be measuring
    brightness again through a different instrument."""
    assert abs(measured["wood_floor_mean"] - measured["flat_floor_mean"]) < 0.02


def test_the_floor_is_dark_the_way_a_bar_floor_is(measured):
    """Not a preference — the reason A1w exists. The Director's eye rejected a composite
    whose lower two-thirds read as a lit white slab under a dim bar; a wood material at
    studio brightness would reproduce that exactly, and the first parameter set did: it
    measured 0.3515 here, pale with a grazing-angle sheen, until roughness went up and
    specular came down."""
    assert measured["wood_floor_mean"] < measured["plain_floor_mean"] / 3


def test_the_control_is_still_the_pale_slab_this_replaces(measured):
    """Guard on the comparison itself: if the default floor ever stopped being pale, every
    assertion above would be measuring something other than the change it claims to."""
    assert measured["plain_floor_mean"] > 0.5


def test_the_measurement_is_taken_at_the_shot_camera(measured):
    """The fixture's own history, pinned. This check first measured the wood at an 80-degree
    down-angle, called it 0.0999 and passed, while the production render came back at 0.3729
    — because the pipeline shoots the floor at 6 degrees, where Fresnel washes a dark
    surface pale. A fixture at a geometry the pipeline never uses tests a different
    material."""
    assert measured["camera"]["elevation_deg"] == 6.0
    assert measured["camera"]["azimuth_deg"] == 225.0
