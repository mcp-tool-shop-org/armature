"""`rig_retopo` and `rig_bake` — the two stages nothing covered before wave 6.

Four findings land here:

* **F-4f5b33f1** — the two retopo variants were handled asymmetrically when one arm
  failed. A dead `variant_a` was removed; a dead `variant_b` was neither removed nor
  hidden, and `render_comparison` hides objects by iterating the `variants` list it was
  handed, so an object absent from that list is never touched. A failed B — a duplicate of
  the outer shell at the identical transform — stayed render-visible and was drawn into
  every panel of every region, on top of the variant each panel claims to show. Both arms
  are wrapped in `except Exception`, so the failure is reachable in ordinary use, and the
  tool then wrote `panels.json`, printed `RIG_RETOPO_OK` and exited 0.
* **F-b73739c1** — neither tool recorded the Blender it ran on, and `rig_retopo`'s manifest
  asserted one instead (`"Blender 5.2 built-ins only"` as a literal). The version is
  load-bearing for exactly these two: `QUADRIFLOW_SCALE`, `extract_outer_shell`'s pinned
  API return and `ISLAND_MARGIN` are each a measurement of one build's behaviour.
* **F-e7745240** — the manifest wrote the Director's conversational sentence verbatim into
  a public artifact, against the standing ruling that public surfaces carry decisions and
  facts in neutral prose and never quotations from chat.
* **F-cb986eb3** — `rig_bake._import` raised the BASE `GateFailure` with no evidence (so
  `halt.json` recorded `"gate": "G?"` and `"evidence": {}`) and picked its mesh with
  `new[0]` out of a SET, whose iteration order follows identity hashes and is not stable
  across processes — in a tool whose premise is a recipe that reproduces its output.
"""

import ast

import pytest

from blender_stub import (FakeBpy, FakeObject, blender_stubbed, load_tool,
                          read_source)


# --------------------------------------------------------------- fakes for the isolation


#: The fakes live in `blender_stub` so `test_make_rig_sheet.py` uses the same ones.
_Ob = FakeObject


@pytest.fixture(scope="module")
def retopo():
    return load_tool("rig_retopo.py")


@pytest.fixture(scope="module")
def bake():
    return load_tool("rig_bake.py")


# ------------------------------------------------------------ F-4f5b33f1: the isolation


def test_isolating_a_panel_hides_every_other_mesh_not_just_the_listed_ones(retopo):
    """The direction the invariant did not bound. `render_comparison` only ever touched the
    objects in its own `variants` list; a failed variant that never made the list was drawn
    into every panel."""
    shell = _Ob("outer_shell")
    a = _Ob("A_quadriflow_direct")
    orphan = _Ob("B_voxel_then_quadriflow")          # failed, never in `variants`
    others = retopo.isolate_subject([shell, a, orphan], a)
    assert a.hide_render is False
    assert shell.hide_render is True
    assert orphan.hide_render is True, (
        "a variant absent from the panel list is still in the render")
    assert sorted(others) == ["B_voxel_then_quadriflow", "outer_shell"]


def test_isolation_refuses_a_scene_it_could_not_isolate(retopo):
    """A mesh that will not hide has to stop the sheet, not quietly appear in it."""

    class _Stubborn(_Ob):
        @property
        def hide_render(self):
            return False

        @hide_render.setter
        def hide_render(self, value):
            pass

    a = _Ob("A_quadriflow_direct")
    with pytest.raises(retopo.ComparisonNotIsolated) as exc:
        retopo.isolate_subject([a, _Stubborn("ghost")], a)
    assert exc.value.gate == "ISOLATE"
    assert exc.value.evidence["still_visible"] == ["ghost"]


def test_isolation_refuses_to_hide_the_subject_itself(retopo):
    a = _Ob("A_quadriflow_direct")
    with pytest.raises(retopo.ComparisonNotIsolated) as exc:
        retopo.isolate_subject([a], None)
    assert exc.value.gate == "ISOLATE"


def test_the_two_variants_are_disposed_of_symmetrically(retopo):
    """The source-level half: the `if A live ... else remove(A)` / `if B live ...` pair is
    replaced by one loop over both names, so neither arm can be the one nobody removes."""
    src = read_source("rig_retopo.py")
    assert "bpy.data.objects.remove(variant_a, do_unlink=True)" not in src, (
        "variant_a still has its own removal branch while variant_b has none")
    tree = ast.parse(src)
    removes = [n for n in ast.walk(tree)
               if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
               and n.func.attr == "remove"
               and any(isinstance(a, ast.Name) and a.id.startswith("variant")
                       for a in n.args)]
    assert not removes, "a variant is still removed by name rather than in the shared loop"


def test_render_comparison_isolates_through_the_one_function(retopo):
    src = read_source("rig_retopo.py")
    body = src.split("def render_comparison")[1].split("\ndef ")[0]
    assert "isolate_subject" in body, (
        "render_comparison still hides only the objects in its own list")
    assert "other.hide_render = other is not ob" not in body


# ------------------------------------------------------- F-b73739c1: recorded provenance

# WAVE 8, F-9af57508 — the population was the literal predicate `'"tool":' in src` over
# the 21 Blender tools, giving 13, and the assertion below was a `>= 13` FLOOR. Both are
# now derived. The invariant is about the WRITING, not about a key a writer may simply not
# use: a tool that serialises a JSON record and does not say which Blender produced it
# leaves a measurement that moved because the interpreter moved reading as a measurement
# that moved because the subject did. Derived on 2026-09-04: 21 of 21 Blender tools write
# JSON, and 8 of them were outside the old predicate.


def _record_writing_blender_tools():
    """THE DERIVATION: every Blender-side tool that SERIALISES a record.

    `json.dump` or `json.dumps` as an `ast.Call`, over the tools that `import bpy` —
    read off the tree, so a writer that keys its record differently is still a writer.
    """
    from blender_stub import blender_tools

    out = []
    for filename in blender_tools():
        tree = ast.parse(read_source(filename))
        serialises = any(
            isinstance(node, ast.Call)
            and (getattr(node.func, "attr", "") in ("dump", "dumps")
                 or getattr(node.func, "id", "") in ("dump", "dumps"))
            for node in ast.walk(tree))
        if serialises:
            out.append(filename)
    return out


RECORD_WRITERS = _record_writing_blender_tools()

#: Derived 2026-09-04. Equality, not a floor: a floor cannot tell you a writer has stopped
#: being counted, and `>= 13` was green over a population of 13 that should have been 21.
RECORDED_RECORD_WRITERS = [
    "author_walk.py", "check_relift.py", "diagnose_bone_heat.py", "lift_solve.py",
    "make_binding_sheet.py", "make_parts_sheet.py", "make_rig_sheet.py",
    "make_skeleton_sheet.py", "make_test_armature.py", "preview_glb.py",
    "preview_walk.py", "probe_glb.py", "probe_subject.py", "render_performer.py",
    "render_start_frame.py", "render_turnaround.py", "rig_bake.py", "rig_character.py",
    "rig_parts.py", "rig_repair.py", "rig_retopo.py",
]

#: The writers that state no Blender version, measured 2026-09-04 with the derived walk
#: above — every one of them a `tools/` file in the instruments domain, none of them
#: reachable by the old `'"tool":' in src` predicate, which is why they were never filed.
#: SIX of them, from the eight the old predicate could not see (`make_test_armature` and
#: `probe_glb` were outside it too and do state a version). A RATCHET, the same shape
#: `EVIDENCE_FREE_GATE_RAISES` uses: the six are written down so the domain that owns them
#: can close them, and a SEVENTH fails here immediately.
#: SUBSET assertion, so this set can only shrink.
NO_BLENDER_VERSION_ROUTED = {
    "make_binding_sheet.py", "make_parts_sheet.py", "make_rig_sheet.py",
    "make_skeleton_sheet.py", "preview_glb.py", "preview_walk.py",
}


def test_the_record_writing_population_is_derived_and_has_not_grown_silently():
    assert RECORD_WRITERS == RECORDED_RECORD_WRITERS, {
        "appeared": sorted(set(RECORD_WRITERS) - set(RECORDED_RECORD_WRITERS)),
        "vanished": sorted(set(RECORDED_RECORD_WRITERS) - set(RECORD_WRITERS)),
    }
    assert len(RECORD_WRITERS) == 21, RECORD_WRITERS
    assert NO_BLENDER_VERSION_ROUTED <= set(RECORD_WRITERS)
    #: the eight the old `'"tool":' in src` predicate could not see
    assert {"make_binding_sheet.py", "preview_glb.py", "probe_glb.py"} <= set(RECORD_WRITERS)


def test_no_new_record_writer_omits_the_blender_it_ran_on():
    """QUADRIFLOW_SCALE, `extract_outer_shell`'s pinned API return and ISLAND_MARGIN are
    each a measurement of ONE build's behaviour; a recipe that does not reproduce its
    output is not a recipe. A sheet or probe record quoted later with no Blender beside it
    is a measurement whose interpreter is unknown."""
    silent = set()
    for filename in RECORD_WRITERS:
        src = read_source(filename)
        if not ("blender_provenance()" in src or "bpy.app.version_string" in src):
            silent.add(filename)
    new = sorted(silent - NO_BLENDER_VERSION_ROUTED)
    assert not new, (
        f"these tools write a record and never state which Blender produced it: {new}")
    assert silent <= NO_BLENDER_VERSION_ROUTED, sorted(silent)


@pytest.mark.parametrize("filename", sorted(set(RECORD_WRITERS) - NO_BLENDER_VERSION_ROUTED),
                         ids=lambda v: v.replace(".py", ""))
def test_every_tool_that_writes_a_record_records_the_blender_it_ran_on(filename):
    src = read_source(filename)
    assert ("blender_provenance()" in src or "bpy.app.version_string" in src), (
        f"{filename} writes a record and never states which Blender produced it. "
        f"QUADRIFLOW_SCALE, extract_outer_shell's pinned API return and ISLAND_MARGIN are "
        f"each a measurement of ONE build's behaviour; a recipe that does not reproduce "
        f"its output is not a recipe.")


@pytest.mark.parametrize("filename", ["rig_retopo.py", "rig_bake.py"])
def test_neither_tool_asserts_a_blender_version_as_a_literal(filename):
    """`"Blender 5.2 built-ins only"` was written into every manifest regardless of what
    was actually running."""
    for text in _emitted_strings(filename):
        assert "Blender 5.2" not in text, (
            f"{filename} still asserts a Blender version in an emitted string: {text!r}")


def _emitted_strings(filename):
    """String literals a tool can emit, EXCLUDING docstrings — a docstring recording the
    superseded claim is the method, not the defect."""
    tree = ast.parse(read_source(filename))
    docs = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            body = getattr(node, "body", [])
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                docs.add(id(body[0].value))
    return [n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and id(n) not in docs]


# ------------------------------------------------- F-e7745240: no chat quotation anywhere

#: The shape of a quoted ruling: a Director attribution followed by quotation marks.
QUOTED_RULING = ("Director 2026-08-11: 'it's not fit for the pipeline")


def test_no_tool_writes_a_quoted_director_sentence_into_an_artifact():
    """CLAUDE.md's portable core: public surfaces carry decisions and facts in neutral
    prose, never quotations from chat. The string was copied into every
    `retopo_manifest.json` the tool wrote and into anything quoting one."""
    import os

    from blender_stub import TOOLS

    offenders = []
    for fn in sorted(os.listdir(TOOLS)):
        if not fn.endswith(".py"):
            continue
        for text in _emitted_strings(fn):
            if QUOTED_RULING in text or ("Director 20" in text and "'" in text
                                         and "not fit for the pipeline" in text):
                offenders.append((fn, text[:80]))
    assert not offenders, offenders


def test_the_ruling_is_still_recorded_as_a_ruling():
    """The correction is a restatement, not a deletion: the date, the subject and the
    verdict all survive."""
    src = read_source("rig_retopo.py")
    assert "QuadRemesher" in src
    assert "2026-08-11" in src


# ------------------------------------------------------ F-cb986eb3: the import in rig_bake


def test_the_import_gate_is_typed_and_carries_evidence(bake):
    """`raise GateFailure(...)` with no evidence records `"gate": "G?"` and
    `"evidence": {}` in halt.json — a gate that cannot say which andon pulled. This file
    already defined two properly-tagged subclasses and did not use the pattern here."""
    assert issubclass(bake.ImportEmpty, bake.GateFailure)
    assert bake.ImportEmpty.gate == "IMPORT"


def test_an_import_that_brings_in_no_mesh_raises_the_typed_gate(bake, monkeypatch):
    with blender_stubbed():
        monkeypatch.setattr(bake, "bpy", FakeBpy(present=[FakeObject("Camera", kind="CAMERA")], adds=[]))
        with pytest.raises(bake.ImportEmpty) as exc:
            bake._import("nothing.glb", "target")
    assert exc.value.gate == "IMPORT"
    assert exc.value.evidence["path"] == "nothing.glb"
    assert exc.value.evidence["objects_added"] == []


def test_an_ambiguous_import_refuses_rather_than_taking_index_zero(bake, monkeypatch):
    """`new[0]` out of a SET: iteration order follows identity hashes and is not stable
    across processes, and the glTF importer routinely adds a second mesh (the
    `glTF_not_exported` Icosphere). Which mesh got baked was not reproducible from the
    recorded inputs, and neither the manifest nor the BAKE andon named it."""
    subject, decoy = _Ob("geometry_0"), _Ob("Icosphere")
    with blender_stubbed():
        monkeypatch.setattr(bake, "bpy", FakeBpy(adds=[subject, decoy]))
        with pytest.raises(bake.ImportEmpty) as exc:
            bake._import("two.glb", "target")
    assert exc.value.gate == "IMPORT"
    assert sorted(exc.value.evidence["render_visible"]) == ["Icosphere", "geometry_0"]


def test_a_hidden_decoy_does_not_change_which_mesh_is_baked(bake, monkeypatch):
    """The reproducibility clause: the same command must select the same object twice, and
    the decoy the importer drops into its hidden collection must not be a candidate."""
    chosen = []
    for order in ([_Ob("geometry_0"), _Ob("Icosphere", hide_render=True)],
                  [_Ob("Icosphere", hide_render=True), _Ob("geometry_0")]):
        with blender_stubbed():
            monkeypatch.setattr(bake, "bpy", FakeBpy(adds=order))
            ob = bake._import("one.glb", "target")
        chosen.append(ob is [o for o in order if not o.hide_render][0])
        assert ob.name == "target"
    assert chosen == [True, True], (
        "the decoy the importer hides was selected in one of the two orders")


def test_the_chosen_mesh_is_recorded_in_the_manifest():
    src = read_source("rig_bake.py")
    assert "subject_selection" in src, (
        "the manifest still does not name which object was baked")
