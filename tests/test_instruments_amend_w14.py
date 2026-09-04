"""Wave-14 instruments amend — the operand each wave-14 finding named, pinned.

The wave-14 rule, in one line: **a guard's red proof exercises the guard, not its
neighbour.** Every fixture here was run once with its fix reverted (`git stash` / run /
`git stash pop`) and is recorded RED in that state in `output.json`; where a fixture is
green with the fix reverted it says so in its own docstring rather than claiming a proof
it does not have.

Helpers in this file **raise**; they never `assert` outside a test body
(`test_gate_survives_optimize.py` polices that, and `ci.yml` runs an `-O` leg).
"""

import ast
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import blender_stub                                                    # noqa: E402
from blender_stub import (FakeCollection, FakeObject, blender_stubbed,  # noqa: E402
                          load_tool, read_source)

TOOLS = blender_stub.TOOLS


# --------------------------------------------------------------------------- fakes


class FakeScene:
    """`scene.objects`, and nothing else — the population an isolation andon must read."""

    def __init__(self, objects=()):
        self.objects = list(objects)


def _fn_source(filename, name):
    """The source of one top-level function, for a mutation fixture."""
    src = read_source(filename)
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(src, node)
    raise LookupError(f"{filename} has no top-level function {name!r}")


# ============================================================ F-4392a2c1 — the isolation
#
# THE OPERAND. `rig_retopo.isolate_subject`'s andon (wave 12, F-4f5b33f1) read
# `[o for o in OBJECTS if ... o.hide_render is not True]` — the same list the loop on the
# line above had just assigned `hide_render` on. Its population was therefore bounded by
# the very loop it was written to check, and the wave-13 auditor measured `still` empty in
# three of three trials including ones seeded to fire it. The operand the finding named is
# the SCENE's population and the collection level of visibility; the fixtures below put a
# render-visible object OUTSIDE the caller's list, which is the only shape that separates
# the two populations.


@pytest.fixture(scope="module")
def retopo():
    return load_tool("rig_retopo.py")


def test_isolation_refuses_a_render_visible_mesh_that_is_not_in_the_caller_s_list(retopo):
    """RED on the operand: the stray is in the SCENE and not in `objects`.

    Reverted-red: yes. With the wave-12 comprehension restored this call returns normally
    and the stray is drawn into every panel — which is exactly the dead-variant-B story the
    andon's own docstring tells.
    """
    a = FakeObject("A_quadriflow_direct")
    shell = FakeObject("outer_shell")
    stray = FakeObject("B_voxel_then_quadriflow")        # failed arm, never in `variants`
    with pytest.raises(retopo.ComparisonNotIsolated) as exc:
        retopo.isolate_subject(FakeScene([a, shell, stray]), [a, shell], a)
    assert exc.value.gate == "ISOLATE"
    assert exc.value.evidence["still_visible"] == ["B_voxel_then_quadriflow"]
    assert exc.value.evidence["n_examined"] == 3
    assert exc.value.evidence["n_hidden_by_the_loop"] == 1


def test_isolation_sees_a_render_visible_object_that_is_not_a_mesh(retopo):
    """The caller's list is `type == "MESH"`; a CURVE draws too and was outside the question."""
    a = FakeObject("A_quadriflow_direct")
    curve = FakeObject("sketch_guide", kind="CURVE")
    with pytest.raises(retopo.ComparisonNotIsolated) as exc:
        retopo.isolate_subject(FakeScene([a, curve]), [a], a)
    assert exc.value.evidence["still_visible"] == ["sketch_guide"]


def test_a_camera_or_a_light_is_not_a_stray(retopo):
    """The other direction, so the gate is not simply always-on: nothing that draws
    nothing may halt the sheet."""
    a = FakeObject("A_quadriflow_direct")
    cam = FakeObject("cam_A_figure", kind="CAMERA")
    key = FakeObject("key_light", kind="LIGHT")
    assert retopo.isolate_subject(FakeScene([a, cam, key]), [a], a) == []


def test_isolation_consults_collection_level_visibility(retopo):
    """`gate_objects_registered`'s level, which this andon never read.

    An object whose own `hide_render` is False but whose collection is hidden is NOT in the
    render, so it must not halt the sheet; the same object in a visible collection must.
    """
    a = FakeObject("A_quadriflow_direct")
    hidden_coll = FakeCollection(name="dead_arms", hide_render=True)
    parked = FakeObject("B_voxel_then_quadriflow", collection=hidden_coll)
    assert retopo.isolate_subject(FakeScene([a, parked]), [a], a) == []
    parked.users_collection = [FakeCollection(name="Scene Collection")]
    with pytest.raises(retopo.ComparisonNotIsolated):
        retopo.isolate_subject(FakeScene([a, parked]), [a], a)


def test_clause_one_goes_red_when_the_hiding_loop_is_mutated_to_a_no_op(retopo):
    """The falsifiability fixture the repo's law asks for.

    A gate whose protected thing can be deleted without the gate firing is not a gate. The
    loop `ob.hide_render = ob is not subject` is replaced by `pass` in a COPY of the
    function compiled in the module's own namespace, and clause 1 must fire on a scene the
    unmutated function accepts.
    """
    src = _fn_source("rig_retopo.py", "isolate_subject")
    mutated_src = src.replace("ob.hide_render = ob is not subject", "pass")
    assert mutated_src != src, "the loop this fixture mutates is no longer written that way"
    ns = dict(retopo.__dict__)
    exec(compile(mutated_src, "<mutated isolate_subject>", "exec"), ns)
    mutated = ns["isolate_subject"]

    a = FakeObject("A_quadriflow_direct")
    shell = FakeObject("outer_shell")
    scene = FakeScene([a, shell])
    assert retopo.isolate_subject(scene, [a, shell], a) == ["outer_shell"]
    shell.hide_render = False
    with pytest.raises(retopo.ComparisonNotIsolated) as exc:
        mutated(scene, [a, shell], a)
    assert exc.value.evidence["still_visible"] == ["outer_shell"]


def test_the_isolation_andon_no_longer_reads_the_list_the_loop_just_wrote(retopo):
    """The source-level half: `still` is derived from `scene.objects`, never from `objects`."""
    src = read_source("rig_retopo.py")
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "isolate_subject")
    assigns = [n for n in ast.walk(fn)
               if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == "still" for t in n.targets)]
    assert len(assigns) == 1, "the andon's population is assigned somewhere else now"
    text = ast.unparse(assigns[0])
    assert "scene.objects" in text, text
    assert "for o in objects" not in text, (
        "the andon still reads the list the loop on the line above assigned")
    assert "users_collection" in text, (
        "collection-level hide_render is still not consulted (gate_objects_registered's level)")


def test_render_comparison_hands_the_scene_to_the_isolation(retopo):
    """The caller half: a signature change that a caller did not follow is a fix one caller
    away from its defect."""
    src = read_source("rig_retopo.py")
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "render_comparison")
    calls = [n for n in ast.walk(fn)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
             and n.func.id == "isolate_subject"]
    assert len(calls) == 1, "the isolation is reached by more than one call site now"
    first = calls[0].args[0]
    assert isinstance(first, ast.Name) and first.id == "scene", ast.unparse(calls[0])


# ======================================================= F-94657d8e — the two sides of a
#                                                          determinism claim
#
# THE OPERAND. `check_relift.main` checked only `os.path.isfile` for each of `--pinned` and
# `--fresh`; nothing anywhere compared the two paths. The wave-13 auditor drove the tool's
# own pure functions with ONE window and ONE signature list on both sides and got
# `clause: None`, `n_frames_differing: 0`, "all 65 frames of evaluated geometry identical",
# and `bytes_identical: true` — the strongest PASS the instrument can print, from a
# comparison of one decode against itself. The operand is IDENTITY OF FILE; the fixtures
# below name one file through two spellings, which is the shape an operator produces (the
# two GLBs live one directory apart).


@pytest.fixture(scope="module")
def relift():
    return load_tool("check_relift.py")


def _relift_argv(pinned, fresh, out):
    return ["blender", "-b", "-P", "check_relift.py", "--",
            f"--pinned={pinned}", f"--fresh={fresh}", f"--out={out}"]


def _a_glb(path, payload=b"glTF\x02\x00\x00\x00"):
    path.write_bytes(payload)
    return str(path)


def test_the_same_path_twice_is_refused_before_either_glb_is_imported(relift, tmp_path):
    """RED on the operand the finding named: `--pinned` and `--fresh` naming one file.

    Reverted-red: yes — without the clause `main` walks past both `isfile` checks and
    reaches `signatures()`, which is where the stubbed `bpy` takes over.
    """
    glb = _a_glb(tmp_path / "b2.glb")
    out = tmp_path / "rec" / "relift.json"
    with blender_stubbed():
        with pytest.raises(relift.ReliftSelfComparison) as exc:
            _run_main(relift, glb, glb, out)
    assert exc.value.gate == "RELIFT_SIDES"
    assert exc.value.evidence["compared_on"].startswith("os.path.samefile")
    assert not out.parent.exists(), "the refusal fired after the record directory was made"


def _run_main(mod, pinned, fresh, out):
    saved = list(sys.argv)
    try:
        sys.argv = _relift_argv(pinned, fresh, out)
        return mod.main()
    finally:
        sys.argv = saved


def test_a_dot_slash_alias_of_the_same_file_is_the_same_file(relift, tmp_path, monkeypatch):
    """The hidden spelling (wave-12 rule 2). A string comparison of the two flags would
    pass this; `os.path.samefile` is the operand that does not."""
    _a_glb(tmp_path / "b2.glb")
    monkeypatch.chdir(tmp_path)
    with blender_stubbed():
        with pytest.raises(relift.ReliftSelfComparison) as exc:
            _run_main(relift, "b2.glb", os.path.join(".", "b2.glb"),
                      str(tmp_path / "rec" / "relift.json"))
    assert exc.value.evidence["pinned_realpath"] == exc.value.evidence["fresh_realpath"]


def test_two_byte_identical_glbs_from_two_files_are_not_refused(relift, tmp_path):
    """The direction that must NOT be refused, and the reason the clause is not a sha
    compare: two byte-identical GLBs produced by two independent solves are the strongest
    determinism result there is. The run proceeds past the gate and dies in the stubbed
    importer, which is proof enough that RELIFT_SIDES let it through."""
    p = _a_glb(tmp_path / "pinned.glb")
    f = _a_glb(tmp_path / "fresh.glb")
    assert open(p, "rb").read() == open(f, "rb").read()
    with blender_stubbed():
        with pytest.raises(Exception) as exc:
            _run_main(relift, p, f, str(tmp_path / "rec" / "relift.json"))
    assert not isinstance(exc.value, relift.ReliftSelfComparison), (
        "a byte-identical pair from two files was refused; that deletes the finding the "
        "tool exists to make")


def test_the_record_carries_a_realpath_for_each_side(relift):
    """A reader of the JSON must be able to see the two sides were two files."""
    src = read_source("check_relift.py")
    assert '"realpath": os.path.realpath(a.pinned)' in src
    assert '"realpath": os.path.realpath(a.fresh)' in src


def test_the_self_comparison_clause_is_not_keyed_on_the_digests(relift):
    """The clause that must NOT be written. `pinned_sha == fresh_sha` is a RECORD field
    (`bytes_identical`), never a refusal."""
    src = read_source("check_relift.py")
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "main")
    raises = [n for n in ast.walk(fn) if isinstance(n, ast.Raise)]
    for r in raises:
        text = ast.unparse(r)
        assert "pinned_sha" not in text and "fresh_sha" not in text, text


# ============================================ F-6a9a0f72 — Gate GLB reads what it named
#
# THE OPERAND. `GateGlbWritten`'s own class docstring and its own refusal message both say
# `bpy.ops.export_scene.gltf` returns an operator STATUS SET and can return CANCELLED
# without raising. The gate never read one: it was `os.path.isfile` then `getsize == 0`,
# two properties a PREVIOUS run's GLB at the same path satisfies. The wave-13 auditor wrote
# 4,004 bytes to a path with plain Python and got back a PASS record carrying a sha256 out
# of a process that had exported nothing. The red proof below is exactly that shape: a
# stubbed exporter returning `{'CANCELLED'}` over a pre-existing non-empty file.


@pytest.fixture(scope="module")
def rigchar():
    return load_tool("rig_character.py")


def test_gate_glb_refuses_a_cancelled_export_over_a_pre_existing_file(rigchar, tmp_path):
    """RED on the operand the finding named.

    Reverted-red: yes. On the wave-12 gate this call returned
    `{'bytes': 4004, 'sha256': ..., 'verdict': 'the rigged GLB is 4,004 bytes on disk'}`.
    """
    p = tmp_path / "hero_bone_heat.glb"
    p.write_bytes(b"g" * 4004)
    before = rigchar.export_target_snapshot(str(p))
    with pytest.raises(rigchar.GateGlbWritten) as exc:
        rigchar.gate_glb_written(str(p), result={"CANCELLED"}, before=before,
                                 what="the rigged GLB")
    assert exc.value.gate == "GLB"
    assert exc.value.evidence["status"] == ["CANCELLED"]
    assert "FINISHED" in str(exc.value)


def test_gate_glb_refuses_a_return_value_that_is_not_a_status_set(rigchar, tmp_path):
    """The hidden spelling: a None, an int, a bare object — anything that is not a readable
    set of statuses fails the clause rather than passing it."""
    p = tmp_path / "x.glb"
    p.write_bytes(b"glTF")
    before = rigchar.export_target_snapshot(str(p))
    for bogus in (None, 7, object()):
        with pytest.raises(rigchar.GateGlbWritten):
            rigchar.gate_glb_written(str(p), result=bogus, before=before)


def test_gate_glb_refuses_the_file_that_was_already_there(rigchar, tmp_path):
    """Clause 4, the second and weaker guard: a FINISHED status over a file whose size AND
    nanosecond mtime are unchanged is the previous run's GLB."""
    p = tmp_path / "hero.glb"
    p.write_bytes(b"glTF" * 100)
    before = rigchar.export_target_snapshot(str(p))
    with pytest.raises(rigchar.GateGlbWritten, match="already there"):
        rigchar.gate_glb_written(str(p), result={"FINISHED"}, before=before)


def test_gate_glb_passes_a_finished_export_and_returns_its_status(rigchar, tmp_path):
    """A gate that refuses everything is not a gate. The status set rides the record."""
    p = tmp_path / "fresh.glb"
    before = rigchar.export_target_snapshot(str(p))
    assert before["existed"] is False
    p.write_bytes(b"glTF" * 3)
    rec = rigchar.gate_glb_written(str(p), result={"FINISHED"}, before=before)
    assert rec["bytes"] == 12
    assert rec["status"] == ["FINISHED"]
    assert len(rec["sha256"]) == 64


def test_gate_glb_takes_no_default_for_result_or_before(rigchar):
    """A default IS the hole this finding is about: a caller that forgets the status set
    would silently get the wave-12 gate back."""
    import inspect

    sig = inspect.signature(rigchar.gate_glb_written)
    for name in ("result", "before"):
        param = sig.parameters[name]
        assert param.kind is inspect.Parameter.KEYWORD_ONLY, name
        assert param.default is inspect.Parameter.empty, (
            f"{name} has a default; a caller can forget it and get the old gate back")


# ------------------------------------------------------------------- the family census
#
# THE NODE (wave-8 rule): the population is derived by AST from `tools/*.py`, keyed on the
# CALL — `bpy.ops.export_scene.gltf` / `bpy.ops.render.render` — and the property is that
# the call is the value of an assignment, i.e. that the status set is captured at all.
# `armature_core/` is excluded by PATH (it is another domain's; its one render site,
# `blender_scene.py:772`, is `write_still=False` — a MEASUREMENT render, not a write), and
# `tools/superseded/` is excluded from the SIZE pin by path while still being required to
# carry the property, because a retired route may come and go.


def _operator_call_sites(directory, dotted):
    """Every `<dotted>(...)` call in the `.py` files directly under `directory`.

    Returns `[(filename, lineno, captured)]` where `captured` is True when the call is the
    value of an assignment. Keyed on the CALL node, so a rename of the local variable, a
    different keyword set, or a call inside a comprehension is all still one member.
    """
    out = []
    for fn in sorted(os.listdir(directory)):
        if not fn.endswith(".py"):
            continue
        with open(os.path.join(directory, fn), encoding="utf-8") as fh:
            src = fh.read()
        tree = ast.parse(src)
        captured_calls = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
                if isinstance(node.value, ast.Call):
                    captured_calls.add(id(node.value))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if ast.unparse(node.func) != dotted:
                continue
            out.append((fn, node.lineno, id(node) in captured_calls))
    return out


def test_every_glb_export_site_captures_the_operator_status_set():
    """SIZE, MEMBERSHIP, then the property — measured on this tree 2026-09-04.

    Nine `bpy.ops.export_scene.gltf` call sites in `tools/*.py`, in seven modules. Every
    one is now the value of an assignment; before this wave not one of them was
    (`grep -rn '= *bpy.ops.export_scene.gltf' tools/*.py` returned nothing).
    """
    sites = _operator_call_sites(TOOLS, "bpy.ops.export_scene.gltf")
    assert len(sites) == 9, sites
    assert sorted({fn for fn, _, _ in sites}) == [
        "author_walk.py", "lift_solve.py", "make_test_armature.py", "rig_bake.py",
        "rig_character.py", "rig_parts.py", "rig_repair.py",
        "rig_retopo.py"], sorted({s[0] for s in sites})
    uncaptured = [(fn, ln) for fn, ln, cap in sites if not cap]
    assert uncaptured == [], uncaptured


def test_every_render_site_captures_the_operator_status_set():
    """The other half of the family: fourteen `bpy.ops.render.render` sites in `tools/*.py`.

    `armature_core/blender_scene.py:772` is excluded by PATH (another domain's file, and a
    `write_still=False` MEASUREMENT render rather than a write).
    """
    sites = _operator_call_sites(TOOLS, "bpy.ops.render.render")
    assert len(sites) == 14, sites
    uncaptured = [(fn, ln) for fn, ln, cap in sites if not cap]
    assert uncaptured == [], uncaptured


def test_the_superseded_render_site_captures_its_status_set_too():
    """Excluded from the size pin, not from the property: a retired route stays runnable."""
    sites = _operator_call_sites(os.path.join(TOOLS, "superseded"), "bpy.ops.render.render")
    assert [(fn, ln) for fn, ln, cap in sites if not cap] == [], sites


def test_every_captured_render_status_reaches_a_refusal():
    """Capturing a value nobody reads is the shape this wave exists to close.

    For each module carrying a render site: one `_render_status(...)` call and one
    `FINISHED`-testing `if` with a `raise` in its body per site. Keyed on the AST.
    """
    offenders = []
    for root in (TOOLS, os.path.join(TOOLS, "superseded")):
        for fn in sorted(os.listdir(root)):
            if not fn.endswith(".py"):
                continue
            with open(os.path.join(root, fn), encoding="utf-8") as fh:
                src = fh.read()
            n_sites = len(_operator_call_sites(root, "bpy.ops.render.render"))
            n_sites = sum(1 for f, _, _ in _operator_call_sites(root, "bpy.ops.render.render")
                          if f == fn)
            if not n_sites:
                continue
            tree = ast.parse(src)
            calls = [n for n in ast.walk(tree)
                     if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                     and n.func.id == "_render_status"]
            raises = [n for n in ast.walk(tree) if isinstance(n, ast.If)
                      and "FINISHED" in ast.unparse(n.test)
                      and any(isinstance(b, ast.Raise) for b in n.body)]
            if len(calls) < n_sites or len(raises) < n_sites:
                offenders.append((fn, n_sites, len(calls), len(raises)))
    assert offenders == [], offenders


def test_the_render_status_helper_is_byte_identical_in_every_copy():
    """It is spelled once per tool because `armature_core` is out of this domain's globs.
    The duplication is held from drifting rather than excused."""
    bodies = {}
    for root in (TOOLS, os.path.join(TOOLS, "superseded")):
        for fn in sorted(os.listdir(root)):
            if not fn.endswith(".py"):
                continue
            with open(os.path.join(root, fn), encoding="utf-8") as fh:
                src = fh.read()
            if "def _render_status" not in src:
                continue
            tree = ast.parse(src)
            node = next(n for n in tree.body
                        if isinstance(n, ast.FunctionDef) and n.name == "_render_status")
            bodies[os.path.join(os.path.basename(root), fn)] = ast.unparse(node)
    assert len(bodies) == 9, sorted(bodies)
    assert len(set(bodies.values())) == 1, sorted(bodies)


# --------------------------------------- sibling carried: Gate SCALE at every derivation


def test_no_tool_derives_a_bbox_diagonal_without_gate_scale():
    """SIBLING CARRIED under F-6a9a0f72 (the coordinator's one unfiled wave-14 item).

    `GateSubjectDegenerate` / `rig_character.subject_scale` was wired at 2 of 6
    bbox-diagonal derivations. The other four — `rig_repair` (whose EXPECTED input is a
    broken mesh), `rig_character.atlas_safe_weld`, `rig_retopo` and `make_rig_sheet` — plus
    `make_skeleton_sheet`'s hand-rolled `((hi - lo) ** 2).sum() ** 0.5` derived the number
    raw. Keyed on the ASSIGNMENT whose target is the diagonal, so a hand-rolled euclidean
    length is caught as well as a `np.linalg.norm`.
    """
    offenders = []
    for fn in sorted(os.listdir(TOOLS)):
        if not fn.endswith(".py") or fn == "rig_character.py":
            continue
        with open(os.path.join(TOOLS, fn), encoding="utf-8") as fh:
            src = fh.read()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            targets = []
            for t in node.targets:
                if isinstance(t, ast.Name):
                    targets.append(t.id)
                elif isinstance(t, ast.Tuple):
                    targets += [e.id for e in t.elts if isinstance(e, ast.Name)]
            if "diagonal" not in targets:
                continue
            text = ast.unparse(node.value)
            # DERIVED, not merely NAMED. `float(man['bbox']['diagonal'])` reads a number a
            # gated run already wrote into a manifest; the population is the sites that
            # COMPUTE the length from a bbox span — a `linalg.norm`, a `sqrt`, or the
            # hand-rolled `(...) ** 0.5` `make_skeleton_sheet` used.
            derives = ("linalg.norm" in text or "sqrt(" in text or "** 0.5" in text)
            if derives and "subject_scale" not in text:
                offenders.append((fn, node.lineno, text))
    assert offenders == [], offenders


def test_gate_scale_still_refuses_a_non_finite_subject(rigchar):
    """The gate the five new call sites reach, exercised on the operand it guards."""
    import numpy as np

    good = np.array([[0.0, 0.0, 0.0], [1.0, 2.0, 3.0]])
    assert rigchar.subject_scale(good, "fixture")[0] > 0
    bad = np.array([[0.0, 0.0, 0.0], [1.0, float("nan"), 3.0]])
    with pytest.raises(rigchar.GateSubjectDegenerate) as exc:
        rigchar.subject_scale(bad, "fixture")
    assert exc.value.gate == "SCALE"
