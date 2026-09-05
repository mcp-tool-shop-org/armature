"""`make_rig_sheet`'s texture-fidelity row. Nothing covered any sheet builder's object
selection before wave 6.

F-e911313d, two defects in the same section.

(a) Lines 130-132 were a loop with no effect whatsoever::

        for ob in list(bpy.data.objects):
            if ob.type == "ARMATURE":
                continue

The body is a bare `continue` and nothing else, so it iterates every object and does
nothing. It sat immediately before the reference import, where an abandoned cleanup was
clearly intended. This is the repo's highest-priority defect class — a step that reports
success while doing nothing — in its purest form.

(b) `ref = [o for o in bpy.data.objects if o.type == "MESH" and o is not mesh][0]` took the
FIRST such object after importing the reference GLB. The file's own comment at lines 63-67
records catching exactly this selection once: "The exported GLB also contains a stray
`Icosphere` with no vertex groups and no modifier; taking index 0 picked that." The stray
removal at lines 78-80 ran BEFORE this second import, so it does not cover what the
reference import adds, and the discriminator used there (vertex groups plus an ARMATURE
modifier) does not apply to an unrigged reference mesh. `ref` then supplied
`ref.data.polygons` for the "before — original mesh, N tris, source atlas" label and was
rendered as that panel: the Director's texture-fidelity comparison could show an Icosphere
beside the retopologised character, labelled with a triangle count read off the Icosphere,
and the sheet would read as catastrophic texture loss where the route is fine.
"""

import ast

import pytest

from blender_stub import FakeBpy, FakeObject, blender_stubbed, load_tool, read_source


@pytest.fixture(scope="module")
def sheet():
    return load_tool("make_rig_sheet.py")


# ------------------------------------------------------------------- (a) the dead loop


def _statement_loops_that_do_nothing(filename, source=None):
    """`for ...: continue` with no other statement in the body.

    WAVE 26, F-a89efade — `source` is the seam that lets the red direction below drive
    THIS walk over a decoy instead of re-implementing it inline. A proof that parses
    its own scratch source and re-writes the predicate demonstrates that `ast` finds
    the node; it cannot fail when the production walk is loosened, which is the one
    thing a red proof exists to make impossible.
    """
    tree = ast.parse(read_source(filename) if source is None else source)
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
            continue
        body = node.body
        if len(body) == 1 and isinstance(body[0], (ast.Pass, ast.Continue)):
            out.append(node.lineno)
        elif (len(body) == 1 and isinstance(body[0], ast.If)
              and len(body[0].body) == 1
              and isinstance(body[0].body[0], (ast.Pass, ast.Continue))
              and not body[0].orelse):
            out.append(node.lineno)
    return out


@pytest.mark.parametrize("filename", ["make_rig_sheet.py", "make_parts_sheet.py",
                                      "make_binding_sheet.py", "make_skeleton_sheet.py"])
def test_no_sheet_builder_carries_a_loop_that_does_nothing(filename):
    lines = _statement_loops_that_do_nothing(filename)
    assert not lines, (
        f"{filename} lines {lines}: a loop whose only body is `continue`/`pass`. A step "
        f"that reports success while doing nothing is the defect class this repo ranks "
        f"first.")


def test_the_dead_loop_scan_would_catch_the_one_it_was_written_for():
    """The red direction, driving `_statement_loops_that_do_nothing` (wave 26, F-a89efade).

    It used to write a probe module to disk and then re-implement the scan inline, which
    asserted a property of `ast` rather than of the scan: the `elif` branch that catches a
    `for` whose only statement is an `if ...: continue` could have been deleted and this
    would still have passed. Both directions in the decoy now — a dead loop and a live one —
    so the scan must report exactly the first.
    """
    decoy = chr(10).join([
        "import bpy",
        "def f():",
        "    for ob in list(bpy.data.objects):",
        "        if ob.type == 'ARMATURE':",
        "            continue",
        "    for ob in list(bpy.data.objects):",
        "        ob.hide_render = False",
        ""])
    assert _statement_loops_that_do_nothing("make_rig_sheet.py", source=decoy) == [3]


# ------------------------------------------------------- (b) which mesh is the reference


def test_the_reference_is_the_mesh_the_reference_import_added(sheet, monkeypatch):
    """Not "the first mesh that is not the skinned one" — the object set is snapshotted
    before the import and the reference is picked from the difference."""
    skinned = FakeObject("geometry_0")
    leftover = FakeObject("SomethingElse")        # already in the scene, not the reference
    reference = FakeObject("terracotta_source")
    bpy = FakeBpy(present=[skinned, leftover], adds=[reference])
    with blender_stubbed():
        monkeypatch.setattr(sheet, "bpy", bpy)
        got = sheet.import_reference("ref.glb", bpy.scene, skinned)
    assert got is reference


def test_the_hidden_decoy_the_importer_adds_is_not_the_reference(sheet, monkeypatch):
    """The measured case the file's own comment records, on the SECOND import this time:
    the glTF importer drops an Icosphere into its hidden `glTF_not_exported` collection."""
    skinned = FakeObject("geometry_0")
    decoy = FakeObject("Icosphere", hide_render=True)
    reference = FakeObject("terracotta_source")
    for order in ([decoy, reference], [reference, decoy]):
        bpy = FakeBpy(present=[skinned], adds=list(order))
        with blender_stubbed():
            monkeypatch.setattr(sheet, "bpy", bpy)
            got = sheet.import_reference("ref.glb", bpy.scene, skinned)
        assert got is reference, order


def test_an_ambiguous_reference_import_raises_rather_than_indexing_zero(sheet, monkeypatch):
    skinned = FakeObject("geometry_0")
    bpy = FakeBpy(present=[skinned],
                  adds=[FakeObject("mesh_a"), FakeObject("mesh_b")])
    with blender_stubbed():
        monkeypatch.setattr(sheet, "bpy", bpy)
        with pytest.raises(sheet.ArmatureError) as exc:
            sheet.import_reference("ref.glb", bpy.scene, skinned)
    assert "mesh_a" in str(exc.value) and "mesh_b" in str(exc.value)


def test_a_reference_import_that_added_no_mesh_raises(sheet, monkeypatch):
    skinned = FakeObject("geometry_0")
    bpy = FakeBpy(present=[skinned], adds=[FakeObject("Empty", kind="EMPTY")])
    with blender_stubbed():
        monkeypatch.setattr(sheet, "bpy", bpy)
        with pytest.raises(sheet.ArmatureError, match="exactly one is needed"):
            sheet.import_reference("ref.glb", bpy.scene, skinned)


def test_the_before_label_is_read_off_the_object_the_gate_returned():
    """The triangle count in the 'before' label comes from `ref.data.polygons`; if `ref`
    could be a decoy, so could the number printed beside the Director's comparison."""
    src = read_source("make_rig_sheet.py")
    assert "import_reference(" in src
    tree = ast.parse(src)
    # A comprehension over the whole object table, indexed straight into: the shape that
    # made a decoy the "before" panel. Checked on the CODE, not the text, so the docstring
    # recording the superseded line does not fire it.
    indexed = [n.lineno for n in ast.walk(tree)
               if isinstance(n, ast.Subscript) and isinstance(n.value, ast.ListComp)
               and any("objects" in ast.dump(g.iter) for g in n.value.generators)]
    assert not indexed, (
        f"make_rig_sheet lines {indexed}: a comprehension over the object table indexed "
        f"at [0]. Which object that is depends on file order, and the file's own comment "
        f"records it picking an Icosphere once.")


# ------------------------------------------------ the family: no subject picked by index 0
#
# `rig_bake._import`'s `new[0]` (F-cb986eb3) and this file's `[...][0]` (F-e911313d) are one
# mechanism. Enumerated across every Blender-side tool: five more sites carried it --
# `diagnose_bone_heat.py:57`, `make_rig_sheet.py:117` (the armature),
# `make_skeleton_sheet.py:233`, `rig_repair.py:150` and `rig_retopo.py:99`. Each now
# selects through `blender_scene.render_visible_meshes` and RAISES when the count is not 1,
# which is the shape `rig_character.build_pass:585` and `lift_solve.pick_subject:136`
# already used.


def _subjects_taken_by_index_zero(filename, source=None):
    """A subject taken as `[...][0]` of a comprehension over the object table.

    WAVE 26, F-a89efade — `source` is the seam that lets the red direction below drive
    THIS walk over a decoy instead of re-implementing it inline. A proof that parses
    its own scratch source and re-writes the predicate demonstrates that `ast` finds
    the node; it cannot fail when the production walk is loosened, which is the one
    thing a red proof exists to make impossible.
    """
    tree = ast.parse(read_source(filename) if source is None else source)
    return [n.lineno for n in ast.walk(tree)
            if isinstance(n, ast.Subscript) and isinstance(n.value, ast.ListComp)
            and any("objects" in ast.dump(g.iter) for g in n.value.generators)]


def _blender_side():
    from blender_stub import blender_tools

    return blender_tools()


def test_the_blender_side_population_is_still_being_enumerated():
    assert len(_blender_side()) >= 21, _blender_side()


@pytest.mark.parametrize("filename", _blender_side())
def test_no_blender_tool_takes_its_subject_by_index_zero(filename):
    lines = _subjects_taken_by_index_zero(filename)
    assert not lines, (
        f"{filename} lines {lines}: a subject taken as [0] of a comprehension over the "
        f"object table. Which object that is depends on file order, and the glTF importer "
        f"routinely adds a second mesh.")


def test_the_index_zero_scan_would_catch_one():
    """The red direction, driving `_subjects_taken_by_index_zero` (wave 26, F-a89efade).

    The decoy carries the defect on line 3 and a correctly-selected subject on line 5, so
    the scan is required to answer differently about two comprehensions rather than merely
    to find a `Subscript`.
    """
    decoy = chr(10).join([
        "import bpy",
        "def f():",
        "    return [o for o in bpy.data.objects if o.type == 'MESH'][0]",
        "def g(named):",
        "    return [o for o in named if o.type == 'MESH']",
        ""])
    assert _subjects_taken_by_index_zero("make_rig_sheet.py", source=decoy) == [3]


# --------------------------- the arc's numbers come from the probe, not from the caption
#
# Routed from instruments-measure (F-f3fe8179), which made `rig_sheet_compose` read
# `spec["probe"]` instead of baking the frame count and the rate into its subtitle. This
# file's subtitle carried the same two literals ("33 keys at 16 fps") plus the frame numbers
# it renders at, so a change to `rig_character.PROBE_FRAMES` or `PROBE_FPS` would move the
# pictures and leave the caption describing the old arc. ONE implementation: the constants
# the probe is authored with.


def test_the_sheet_takes_the_arcs_numbers_from_the_probe_constants():
    src = read_source("make_rig_sheet.py")
    tree = ast.parse(src)
    literals = [n.value for n in ast.walk(tree)
                if isinstance(n, ast.Constant) and n.value in (33, 17)]
    assert not literals, (
        "the probe's frame count is still typed into make_rig_sheet; it belongs to "
        "rig_character.PROBE_FRAMES")
    for text in _emitted(src):
        assert "33 keys" not in text and "16 fps" not in text, text


def test_the_probe_record_reaches_panels_json():
    """`rig_sheet_compose` reads `spec["probe"]`; this sheet now writes one in the same
    shape, so the two agree by construction rather than by both being typed correctly."""
    src = read_source("make_rig_sheet.py")
    assert '"probe": probe' in src
    for key in ("which_arm_is_on_plus_x", "frames", "fps"):
        assert key in src, key


def _emitted(src):
    tree = ast.parse(src)
    docs = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                docs.add(id(body[0].value))
    return [n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and id(n) not in docs]
