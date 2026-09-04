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


# ---------------------------------------------------------------- the family census (w6)
#
# F-fc5ea793: `render_turnaround.py:552` was `subject = [o for o in meshes]` — every mesh
# `import_glb` returned, filtered only on `o.type == "MESH"`. The bbox, the orbit target,
# the framing cloud and the solved radius / shared `ortho_scale` were therefore computed
# over the decoy as well as the character, and NO gate here can see it: Gate WHOLE reads
# the same inflated cloud, and Gate CROP reads the rendered alpha, which a `hide_render`
# decoy never touches — a figure drawn too SMALL moves away from every border, so CROP
# passes more easily. `render_performer.py:288` and `preview_walk.py:89` set the ground
# plane's height from the same unfiltered list.
#
# `render_start_frame.py:435` already carried the fix under a five-line comment. This is
# the census that would have found the three that did not, and it is read off the files so
# a new tool joins the population the day it lands.

import ast

from blender_stub import TOOLS as TOOLS_DIR
from blender_stub import read_source

#: The mesh objects `import_glb` hands back are filtered on `o.type == "MESH"` alone. Any
#: tool that MEASURES them — framing, bbox, ground height, vertex cloud — must select
#: through `render_visible_meshes` first.
def _tools_that_import_glb():
    found = []
    for fn in sorted(os.listdir(TOOLS_DIR)):
        if not fn.endswith(".py"):
            continue
        src = read_source(fn)
        if "import_glb(" in src:
            found.append(fn)
    return found


def test_the_import_glb_population_is_what_it_was_measured_to_be():
    """A census that stopped enumerating would report green over everything."""
    pop = _tools_that_import_glb()
    assert len(pop) >= 9, pop
    for expected in ("render_turnaround.py", "render_performer.py", "preview_walk.py",
                     "render_start_frame.py", "stage_render.py"):
        assert expected in pop, (expected, pop)


@pytest.mark.parametrize("filename", _tools_that_import_glb())
def test_every_tool_that_measures_imported_meshes_filters_by_render_visibility(filename):
    src = read_source(filename)
    assert "render_visible_meshes" in src, (
        f"{filename} calls import_glb and never filters by render visibility. The glTF "
        f"importer drops a hidden radius-1.0 Icosphere into `glTF_not_exported`; measuring "
        f"it reframes the shot (E02-report.md:34: a 3.23:1 figure read as a 1.05:1 "
        f"near-cube) and no gate downstream can see it.")


def _measurement_loops_over_unfiltered_meshes(filename):
    """`for o in meshes` inside an arithmetic expression, i.e. a MEASUREMENT.

    Naming the objects for a record (`[o.name for o in meshes]`) is not the defect and is
    how `probe_subject.py:46` reports what it excluded; measuring their geometry is.
    """
    tree = ast.parse(read_source(filename))
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.ListComp, ast.GeneratorExp, ast.SetComp)):
            continue
        over_meshes = any(
            isinstance(g.iter, ast.Name) and g.iter.id in ("meshes", "imported_meshes")
            for g in node.generators)
        if not over_meshes:
            continue
        elt = ast.dump(node.elt)
        if "matrix_world" in elt or "bound_box" in elt or "vertices" in elt:
            hits.append(node.lineno)
        elif isinstance(node.elt, ast.Name):          # `[o for o in meshes]` — a copy
            hits.append(node.lineno)
    return hits


@pytest.mark.parametrize("filename", _tools_that_import_glb())
def test_no_tool_measures_the_unfiltered_mesh_list(filename):
    hits = _measurement_loops_over_unfiltered_meshes(filename)
    assert not hits, (
        f"{filename} lines {hits}: geometry measured over the unfiltered mesh list. "
        f"Select through blender_scene.render_visible_meshes first.")


def test_the_scan_would_catch_the_defect_it_was_written_for(tmp_path):
    """The red direction — a check that cannot fail is not a check."""
    probe = tmp_path / "probe_tool.py"
    probe.write_text(
        "def f(meshes):\n"
        "    subject = [o for o in meshes]\n"
        "    zs = [(o.matrix_world @ Vector(c)).z for o in meshes for c in o.bound_box]\n"
        "    return subject, zs\n", encoding="utf-8")
    tree = ast.parse(probe.read_text(encoding="utf-8"))
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.ListComp, ast.GeneratorExp)):
            over = any(isinstance(g.iter, ast.Name) and g.iter.id == "meshes"
                       for g in node.generators)
            elt = ast.dump(node.elt)
            if over and ("matrix_world" in elt or isinstance(node.elt, ast.Name)):
                hits.append(node.lineno)
    assert hits == [2, 3], hits
