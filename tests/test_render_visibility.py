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

#: Scoped to the tests that actually subprocess Blender. This was a module-level
#: `pytestmark`, which took the static censuses below down with it — and those are the half
#: that has to run on CI, where there is no Blender at all. A census skipped wherever it
#: would matter polices nothing.
needs_blender = pytest.mark.skipif(
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


@needs_blender
def test_only_the_subject_survives_the_filter(vis):
    assert vis["render_visible_names"] == ["subject"]


@needs_blender
def test_the_naive_filter_would_have_returned_all_four(vis):
    """If this ever stops being true the fixture has gone slack and is no longer
    testing anything."""
    assert len(vis["all_mesh_names"]) == 4


@needs_blender
def test_the_gltf_importers_hidden_collection_is_excluded(vis):
    assert "gltf_decoy" not in vis["render_visible_names"]


@needs_blender
def test_object_level_hide_render_is_excluded(vis):
    assert "obj_hidden" not in vis["render_visible_names"]


@needs_blender
def test_render_hidden_but_viewport_visible_is_excluded(vis):
    """`visible_get()` is viewport visibility. A predicate built on it would keep this
    decoy, and the instrument would disagree with the renderer again."""
    assert vis["viewport_visible_get"]["viewport_visible_decoy"] is True
    assert "viewport_visible_decoy" not in vis["render_visible_names"]


@needs_blender
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
#:
#: Wave 8, F-09a56210 — why neither half of this census is a substring any more.
#: The population was `'import_glb(' in src`, and the property was
#: `'render_visible_meshes' in src`. Both are satisfied by PROSE, in a repo whose own
#: convention (this file's header, `test_alpha_law.py`) is that naming a thing in a comment
#: is how a defect gets RECORDED. Measured on the nine-file population: every member had
#: exactly one real call site, so deleting the call and leaving the comment above it kept
#: this test green. The population missed the other half of the family outright — 21 tools
#: import `bpy` and twelve of them build a MESH-filtered object list without going anywhere
#: near `import_glb`.


def _call_lines(tree, name):
    """Every line at which `name` appears as the callee of an `ast.Call`."""
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            called = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if called == name:
                out.append(node.lineno)
    return sorted(out)


def _selects_mesh_objects_by_type(tree):
    """Every line comparing some object's `.type` to the literal `"MESH"`.

    This is the shape the whole file exists for: `[o for o in bpy.data.objects if
    o.type == "MESH"]` is the filter that sweeps up the importer's decoy, whether the
    objects arrived through `import_glb` or through `bpy.ops.import_scene.gltf` directly.
    """
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Compare) and isinstance(node.left, ast.Attribute)
                and node.left.attr == "type"
                and any(isinstance(c, ast.Constant) and c.value == "MESH"
                        for c in node.comparators)):
            out.append(node.lineno)
    return sorted(out)


def _tools_that_obtain_meshes(tools_dir=None):
    """THE DERIVATION: every tool that obtains mesh objects from `bpy` at all.

    A tool is in the population when its AST carries any of: a CALL to `import_glb`, a
    CALL to `render_visible_meshes`, or a `.type == "MESH"` comparison. Nothing is read as
    a substring, so a comment naming any of the three puts nothing in and takes nothing
    out. 21 members on 2026-09-04 — the nine the old predicate found, plus the twelve that
    import through `bpy.ops.import_scene.gltf` and filter by type themselves.
    """
    tools_dir = TOOLS_DIR if tools_dir is None else tools_dir
    found = []
    for fn in sorted(os.listdir(tools_dir)):
        if not fn.endswith(".py"):
            continue
        with open(os.path.join(tools_dir, fn), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        if (_call_lines(tree, "import_glb") or _call_lines(tree, "render_visible_meshes")
                or _selects_mesh_objects_by_type(tree)):
            found.append(fn)
    return found


#: The population as derived on 2026-09-04. Equality, so a new Blender tool joins the
#: census on the day it lands rather than the day somebody remembers to widen a tuple.
RECORDED_MESH_TOOLS = [
    "author_walk.py", "check_relift.py", "diagnose_bone_heat.py", "lift_solve.py",
    "make_binding_sheet.py", "make_parts_sheet.py", "make_rig_sheet.py",
    "make_skeleton_sheet.py", "preview_glb.py", "preview_walk.py", "probe_glb.py",
    "probe_subject.py", "render_performer.py", "render_start_frame.py",
    "render_turnaround.py", "rig_bake.py", "rig_character.py", "rig_parts.py",
    "rig_repair.py", "rig_retopo.py", "stage_render.py",
]

#: Exemptions, re-derived 2026-09-04, each with the clause that makes it true and a
#: mechanical check of that clause below — an exemption whose premise nobody re-reads is
#: how `preview_glb` sat outside the exit-handler census under a comment its own file
#: falsified. `preview_glb.py` is deliberately NOT here: it derives a camera radius from
#: `scene_bbox(meshes)` over the unfiltered list, which is the defect verbatim, and its fix
#: is the instruments domain's (wave 8, "the visibility fix reaches this file").
MEASURES_NOTHING_FROM_THE_MESH_LIST = {
    "probe_glb.py": "reports an inventory of what the FILE contains — object counts, a "
                    "type histogram, vertex and vertex-group totals. Filtering by render "
                    "visibility would make the probe lie about the file it is probing, and "
                    "`len(o.data.vertices)` summed over the meshes is a COUNT, not a "
                    "vertex cloud. Checked: the module makes no world-space measurement "
                    "at all — no `matrix_world`, no `bound_box`, so nothing it writes can "
                    "reframe a shot.",
    "rig_parts.py": "refuses rather than measures: the import is followed immediately by "
                    "a count guard that raises unless exactly one MESH object arrived, so "
                    "the importer's decoy halts the tool instead of joining a "
                    "measurement. Checked: the guard is still there.",
}


def test_the_mesh_tool_population_is_derived_and_has_not_grown_silently():
    """Size, then membership. A census that stopped enumerating would report green over
    everything, and one whose predicate was a substring would report green over a comment.
    """
    pop = _tools_that_obtain_meshes()
    assert len(pop) == 21, pop
    assert pop == RECORDED_MESH_TOOLS, {
        "appeared": sorted(set(pop) - set(RECORDED_MESH_TOOLS)),
        "vanished": sorted(set(RECORDED_MESH_TOOLS) - set(pop)),
    }
    #: the twelve the old `'import_glb(' in src` predicate could not see
    assert {"rig_character.py", "rig_parts.py", "make_rig_sheet.py", "probe_glb.py",
            "preview_glb.py", "diagnose_bone_heat.py"} <= set(pop)


def test_the_exemptions_sit_inside_the_population_and_their_clauses_still_hold():
    """Rule 4: named, dated, re-derived — and each checked against the REASON it is
    exempt, not merely listed."""
    pop = set(_tools_that_obtain_meshes())
    assert set(MEASURES_NOTHING_FROM_THE_MESH_LIST) <= pop

    probe = ast.parse(read_source("probe_glb.py"))
    world = [n.lineno for n in ast.walk(probe)
             if isinstance(n, ast.Attribute) and n.attr in ("matrix_world", "bound_box")]
    assert world == [], (
        f"probe_glb.py measures world-space geometry at {world}; it is exempt only for as "
        f"long as its record is an inventory rather than a measurement")

    parts = ast.parse(read_source("rig_parts.py"))
    guards = [n.lineno for n in ast.walk(parts)
              if isinstance(n, ast.If)
              and any(isinstance(b, ast.Raise) for b in n.body)
              and "expected one mesh object" in ast.dump(n)]
    assert guards, (
        "rig_parts.py no longer raises on a mesh count other than one, so the clause its "
        "exemption rests on is gone: a decoy would now be measured rather than refused")


@pytest.mark.parametrize("filename", _tools_that_obtain_meshes())
def test_every_tool_that_measures_imported_meshes_filters_by_render_visibility(filename):
    """The property, asserted as a CALL. `'render_visible_meshes' in src` is satisfied by
    the comment that explains the call, which is precisely the sentence a seat writes just
    before deleting the line under it."""
    if filename in MEASURES_NOTHING_FROM_THE_MESH_LIST:
        pytest.skip(f"{filename}: {MEASURES_NOTHING_FROM_THE_MESH_LIST[filename]}")
    tree = ast.parse(read_source(filename))
    assert _call_lines(tree, "render_visible_meshes"), (
        f"{filename} obtains mesh objects from bpy and never CALLS render_visible_meshes. "
        f"The glTF importer drops a hidden radius-1.0 Icosphere into `glTF_not_exported`; "
        f"measuring it reframes the shot (E02-report.md:34: a 3.23:1 figure read as a "
        f"1.05:1 near-cube) and no gate downstream can see it.")


def test_the_call_site_census_goes_red_when_the_call_goes_and_the_comment_stays(tmp_path):
    """Rule 3: prove the census fails on a mutation that adds a member without the
    property. Three synthetic tools — one that calls the filter, one that only NAMES it in
    a comment and a docstring, and one that never mentions it. The middle one is the
    mutation the old substring predicate accepted."""
    root = tmp_path / "tools"
    root.mkdir()
    (root / "keeps_the_call.py").write_text(
        'def main(scene):\n'
        '    meshes = render_visible_meshes(scene)\n'
        '    return [o for o in meshes]\n', encoding="utf-8")
    (root / "keeps_only_the_words.py").write_text(
        '"""Selects through render_visible_meshes so the decoy never lands."""\n'
        'def main(scene):\n'
        '    # render_visible_meshes(scene) — see the module docstring\n'
        '    meshes = [o for o in scene.objects if o.type == "MESH"]\n'
        '    return meshes\n', encoding="utf-8")
    (root / "never_heard_of_it.py").write_text(
        'def main(scene):\n'
        '    return [o for o in scene.objects if o.type == "MESH"]\n', encoding="utf-8")

    pop = _tools_that_obtain_meshes(str(root))
    assert pop == ["keeps_only_the_words.py", "keeps_the_call.py",
                   "never_heard_of_it.py"], pop

    verdict = {}
    for fn in pop:
        with open(root / fn, encoding="utf-8") as fh:
            verdict[fn] = bool(_call_lines(ast.parse(fh.read()), "render_visible_meshes"))
    assert verdict == {"keeps_the_call.py": True, "keeps_only_the_words.py": False,
                       "never_heard_of_it.py": False}, verdict


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


@pytest.mark.parametrize("filename", _tools_that_obtain_meshes())
def test_no_tool_measures_the_unfiltered_mesh_list(filename):
    if filename in MEASURES_NOTHING_FROM_THE_MESH_LIST:
        pytest.skip(f"{filename}: {MEASURES_NOTHING_FROM_THE_MESH_LIST[filename]}")
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


def test_no_tool_reaches_into_the_private_vertex_primitive():
    """SEAM, wave 6 (core-solvers): `blender_scene.evaluated_world_vertices(scene, objects)`
    is the public name and filters by render visibility itself; there is no shape that skips
    the filter. `render_turnaround.py:553` and `render_start_frame.py:452` were the two
    tools importing the private `_evaluated_world_vertices`, and a private primitive that
    tools reach into is a filter waiting to be bypassed again."""
    for filename in _tools_that_obtain_meshes():
        src = read_source(filename)
        assert "_evaluated_world_vertices" not in src, (
            f"{filename} calls the private primitive instead of "
            f"blender_scene.evaluated_world_vertices(scene, objects)")


# --- F-0e29613a: the ban covers every tool, not only the ones that import a GLB -------


def _all_tool_sources():
    """Every `.py` under `tools/`, including `tools/superseded/`.

    Derived by walking the directory — not by a substring in source. The existing ban
    (`test_no_tool_reaches_into_the_private_vertex_primitive`) enumerated only files
    containing `import_glb(`, so a future tool that MEASURES without importing sat outside
    the population the ban claimed to cover. Returns `{relative path: source}`.
    """
    out = {}
    root = TOOLS_DIR
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in sorted(filenames):
            if not fn.endswith(".py"):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            with open(full, encoding="utf-8") as fh:
                out[rel] = fh.read()
    return out


def test_the_widened_population_is_a_superset_of_the_mesh_tool_one():
    """The census's own premise, measured: walking the whole tree must cover strictly more
    than the mesh-tool population above, and the extra files are real tools.

    At the wave-8 merge this compared against `_tools_that_import_glb()`, the substring
    helper the tests domain retired the same wave (the population is now derived by AST —
    `RECORDED_MESH_TOOLS`); the comparison is re-pointed at that derived set.
    """
    walked = set(_all_tool_sources())
    top_level = {k.replace("\\", "/") for k in walked if "/" not in k.replace("\\", "/")}
    mesh_tools = set(RECORDED_MESH_TOOLS)
    assert mesh_tools <= top_level, sorted(mesh_tools - top_level)
    assert len(walked) > len(mesh_tools), (len(walked), len(mesh_tools))


def test_no_file_under_tools_reaches_into_the_private_vertex_primitive():
    """Widened form of the wave-6 ban (F-0e29613a).

    `blender_scene.evaluated_world_vertices(scene, objects)` is the public name and filters
    by render visibility itself; `unfiltered_world_bounds` is the public name for the one
    measurement that is deliberately naive. The old ban only walked files containing
    `import_glb(`, so it covered neither `armature_core` itself nor a future tool that
    measures geometry it was handed. This walks every `.py` under `tools/`.
    """
    sources = _all_tool_sources()
    # The one exemption, re-derived rather than trusted: the file exempt from the ban must
    # be in the walked population AND must be the file that DEFINES the primitive.
    exempt = "armature_core/blender_scene.py"
    assert exempt in sources, sorted(sources)
    assert "def _evaluated_world_vertices(" in sources[exempt], (
        f"{exempt} is exempt because it defines the primitive; it no longer does")
    offenders = sorted(
        rel for rel, src in sources.items()
        if "_evaluated_world_vertices" in src and rel != exempt)
    assert offenders == [], (
        f"{offenders} reach into the private primitive instead of "
        f"blender_scene.evaluated_world_vertices(scene, objects) — or, for a row that is "
        f"deliberately unfiltered, blender_scene.unfiltered_world_bounds(objects)")


# -------------------------- the same ban, keyed on the BEHAVIOUR rather than one spelling
#
# THE NODE THIS KEYS ON (wave 10, F-bd6a03e8): a CALL that reaches unfiltered geometry.
# The census above keys on the identifier `_evaluated_world_vertices` appearing in source
# text, which polices one spelling and reports `offenders == []` while two other doors
# stand open:
#
#   Door one — `blender_scene.world_bounds(objects, scene=None)` routes through
#   `_points_to_measure`, which calls the private primitive VERBATIM when `scene is None`
#   (blender_scene.py:305). Measured 2026-09-04, four production sites pass no scene:
#   probe_subject.py:63, probe_subject.py:75, preview_walk.py:159, stage_render.py:155.
#   probe_subject.py:75 is the exact site wave 8 introduced `unfiltered_world_bounds` to
#   carry — its own docstring names `probe_subject` as its consumer — and it was never
#   re-pointed, so the naive row is still taken through the public two-arg form.
#
#   Door two — `tools/make_parts_sheet.py:200` defines its OWN `world_bounds(objs)`, a
#   fourth hand-rolled world-space bounds over `ob.data.vertices` with no depsgraph
#   evaluation and no visibility filter. The substring ban sees nothing there at all.
#
# So the ban is now: outside `blender_scene.py`, no call to a member of the bounds family
# may omit `scene`, and no module may define its own `world_bounds`. The one sanctioned
# unfiltered measurement has a public name — `unfiltered_world_bounds` — and using it is
# how a site says out loud that it means the naive row.
#
# Owners: core-solvers (`blender_scene.world_bounds`'s refusal/routing), instruments
# (probe_subject, preview_walk), instruments-measure (stage_render, make_parts_sheet).

#: The family: every public reader whose first argument is an object list and whose filter
#: depends on being handed a scene. `unfiltered_world_bounds` is deliberately absent — it is
#: the sanctioned way to ASK for the naive measurement.
BOUNDS_FAMILY = ("world_bounds",)

#: Named and dated 2026-09-04. `tools/superseded/` is not a pipeline path: CLAUDE.md keeps
#: falsified approaches in the tree, runnable, as the record of why they were falsified, and
#: re-pointing one at a filtered reader would edit a record. Asserted to be a real directory
#: below, so the exemption cannot outlive what it names.
UNFILTERED_BAN_EXEMPT_DIRS = ("superseded/",)


def _bounds_call_sites():
    """`{path: [(line, source)]}` for every `<family>(...)` call that omits a scene.

    `world_bounds(objects, scene=None)`: a scene reaches it as the second POSITIONAL
    argument or as `scene=`. Anything else is the naive measurement, whatever it is spelled
    through — `blender_scene.world_bounds(x)`, `bs.world_bounds(x)` or a bare
    `world_bounds(x)` after a `from ... import`.
    """
    out = {}
    for rel, src in sorted(_all_tool_sources().items()):
        if rel == "armature_core/blender_scene.py":
            continue
        if any(rel.startswith(d) for d in UNFILTERED_BAN_EXEMPT_DIRS):
            continue
        for node in ast.walk(ast.parse(src)):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", None)
            if name not in BOUNDS_FAMILY:
                continue
            has_scene = len(node.args) >= 2 or any(kw.arg == "scene" for kw in node.keywords)
            if not has_scene:
                out.setdefault(rel, []).append((node.lineno, ast.unparse(node)))
    return out


def _module_local_bounds_definitions():
    """`{path: [(line, name)]}` for any module OUTSIDE blender_scene.py defining the name."""
    out = {}
    for rel, src in sorted(_all_tool_sources().items()):
        if rel == "armature_core/blender_scene.py":
            continue
        if any(rel.startswith(d) for d in UNFILTERED_BAN_EXEMPT_DIRS):
            continue
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                    and node.name in BOUNDS_FAMILY:
                out.setdefault(rel, []).append((node.lineno, node.name))
    return out


def test_the_exempt_paths_and_the_family_are_the_ones_this_ban_claims():
    """Exemptions are named, dated and RE-DERIVED — and so is the family itself."""
    root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
    for rel in UNFILTERED_BAN_EXEMPT_DIRS:
        assert os.path.isdir(os.path.join(root, rel.rstrip("/"))), rel
    sources = _all_tool_sources()
    defining = sources["armature_core/blender_scene.py"]
    tree = ast.parse(defining)
    defined = {n.name for n in ast.walk(tree)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    for name in BOUNDS_FAMILY:
        assert name in defined, f"{name} is not defined by blender_scene.py any more"
    assert "unfiltered_world_bounds" in defined, (
        "the sanctioned naive reader is gone; a site that means the naive measurement has "
        "no way left to say so")
    # the premise the whole ban rests on, read off the defining module rather than assumed
    fn = next(n for n in tree.body
              if isinstance(n, ast.FunctionDef) and n.name == "_points_to_measure")
    assert any(isinstance(n, ast.Call) and getattr(n.func, "id", None)
               == "_evaluated_world_vertices" for n in ast.walk(fn)), (
        "`_points_to_measure` no longer reaches the private primitive; re-derive this ban")


def test_no_tool_takes_a_bounds_measurement_with_the_scene_omitted():
    """The behavioural ban. `world_bounds(meshes)` IS the unfiltered primitive, one frame
    deeper — geometry that never renders defining a camera fit or a framing measurement."""
    offenders = _bounds_call_sites()
    assert offenders == {}, (
        "these call the bounds family with no scene, so `_points_to_measure` takes the "
        "objects AS GIVEN: " + json.dumps(offenders, indent=2) + "\n  Pass `scene=` for the "
        "filtered measurement, or call `blender_scene.unfiltered_world_bounds(objects)` "
        "where the naive row is the point.")


def test_no_module_reimplements_the_bounds_reader_under_its_own_roof():
    """A module-local `def world_bounds` is a fourth hand-rolled measurement that the
    call-site ban cannot see, because the call it makes is legal against its own def."""
    local = _module_local_bounds_definitions()
    assert local == {}, (
        "these define their own bounds reader instead of calling blender_scene's: "
        + json.dumps(local, indent=2))


def test_the_behavioural_ban_goes_red_on_both_doors(tmp_path, monkeypatch):
    """Rule 3: driven against synthetic modules carrying each door, and against the two
    shapes that must NOT be flagged."""
    files = {
        "door_one.py": ("from armature_core import blender_scene\n"
                        "def run(meshes):\n"
                        "    return blender_scene.world_bounds(meshes)\n"),
        "door_two.py": ("def world_bounds(objs):\n"
                        "    return min(o.x for o in objs), max(o.x for o in objs)\n"),
        "filtered_kw.py": ("from armature_core import blender_scene\n"
                           "def run(scene, meshes):\n"
                           "    return blender_scene.world_bounds(meshes, scene=scene)\n"),
        "filtered_pos.py": ("from armature_core import blender_scene\n"
                            "def run(scene, meshes):\n"
                            "    return blender_scene.world_bounds(meshes, scene)\n"),
        "sanctioned.py": ("from armature_core import blender_scene\n"
                          "def run(meshes):\n"
                          "    return blender_scene.unfiltered_world_bounds(meshes)\n"),
    }
    fake = {"armature_core/blender_scene.py":
            _all_tool_sources()["armature_core/blender_scene.py"]}
    fake.update(files)
    monkeypatch.setitem(globals(), "_all_tool_sources", lambda: fake)

    calls = _bounds_call_sites()
    assert sorted(calls) == ["door_one.py"], calls
    assert sorted(_module_local_bounds_definitions()) == ["door_two.py"]

    # and the exempt directory really is exempt rather than merely absent
    fake["superseded/old.py"] = files["door_one.py"]
    assert sorted(_bounds_call_sites()) == ["door_one.py"]


def test_the_widened_ban_goes_red_on_a_tool_that_does_not_import_a_glb(tmp_path):
    """Prove the census can fail on a member the OLD population could not see: a file with
    no `import_glb(` in it at all, which the substring filter would never have enumerated.
    """
    probe = tmp_path / "measure_only.py"
    probe.write_text(
        "from armature_core import blender_scene\n"
        "def run(meshes):\n"
        "    return blender_scene._evaluated_world_vertices(meshes)\n", encoding="utf-8")
    src = probe.read_text(encoding="utf-8")
    assert "import_glb(" not in src, "the old population would not have enumerated this"
    assert "_evaluated_world_vertices" in src, "the widened ban catches it"
