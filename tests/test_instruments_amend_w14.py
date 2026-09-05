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
    """`scene.objects`, and nothing else — the population an isolation andon must read.
    WAVE 16, F-94a7d14d (instruments). The two visibility andons now resolve render
    visibility through `blender_scene.collection_render_flags`, the canonical walk, which
    reads `scene.view_layers[0].layer_collection` — so a fake scene that exposes only
    `objects` no longer models the object under test. The view layer below is the DEFAULT
    one (`Scene Collection`, nothing hidden, nothing excluded), which is what every fixture
    in this file already assumed implicitly; the collection-level fixtures pass their own.
    No assertion in this file changed.
    """

    def __init__(self, objects=(), root=None):
        self.objects = list(objects)
        self.view_layers = [self]
        self.layer_collection = root or FakeCollection()


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
    with pytest.raises(retopo.ComparisonNotIsolated,
                       match="still in the render beside the panel's subject"):
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
    """The source-level half: `still` is derived from `scene.objects`, never from `objects`.

    CORRECTED IN PLACE, wave 16 (instruments, F-94a7d14d), by the measurement that
    overturned the last clause. It read `assert "users_collection" in text` over the ONE
    expression that assigns `still`, and its message said "collection-level hide_render is
    still not consulted". That was a check on a SPELLING at one line, and the spelling was
    the defect: the one-level `any(c.hide_render for c in o.users_collection)` it was
    pinning is precisely what F-94a7d14d measured wrong -- a decoy in a collection nested
    under a `hide_render=True` parent, and one in an excluded collection, both read as
    render-visible to it and as invisible to `blender_scene.render_visible_meshes`. The
    property is "collection-level visibility IS consulted, through the canonical walk",
    and it is now asserted over the whole function rather than over one expression, so a
    fix that lifts the predicate into a named helper reads as health rather than as a
    regression.
    """
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
    body = ast.unparse(fn)
    assert "users_collection" in body, (
        "collection-level visibility is still not consulted at all")
    assert "collection_render_flags(" in body, (
        "collection-level visibility is consulted with a SECOND implementation; the "
        "canonical walk is `blender_scene.collection_render_flags`, which is the only one "
        "that carries `exclude` and an ancestor's `hide_render` (F-94a7d14d)")


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
        with pytest.raises(rigchar.GateGlbWritten, match="did not report FINISHED"):
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
# WAVE 23, F-bca562a1 — `armature_core/` IS IN THE CENSUS, and the exclusion that kept it
# out is replaced by the measurement that overturned it.
#
# The docstring here read "`armature_core/blender_scene.py:772` is excluded by PATH (another
# domain's file, and a `write_still=False` MEASUREMENT render rather than a write)". Both
# halves fail. The site is at `blender_scene.py::render_frame`, not `:772`. It sits inside
# `render_frame`, which writes one EXR per channel through compositor File Output nodes, and
# whose Gate FRAME andon (`RenderedFrame`, raised at `:958` with clause `operator_status`)
# exists precisely because those writes can silently be the PREVIOUS run's frames — the
# module's own text at `:938-941` says the check proves each path differs from whatever stood
# there before the call ran. `write_still=False` is still literally true and is no longer a
# reason: the frames reach disk through the compositor, not through `write_still`.
#
# So the walk is RECURSIVE over `tools/`, which brings `armature_core/` in and leaves
# `tools/superseded/` excluded from the SIZE pin by name (a retired route may come and go)
# while still being required to carry the property. What was outside: a second
# `bpy.ops.render.render` added anywhere in `armature_core` — the package every previz render
# the video model paints over goes through — was required by no census to capture its status
# set, and a CANCELLED render that returns without raising hands the run the previous frames.


SUPERSEDED = "superseded"


def census_sources(directory, *, recursive=True, skip=(SUPERSEDED, "__pycache__")):
    """`[(label, path)]` for the `.py` files this census reads under `directory`.

    ONE home for the population, because three checks below iterate it and two of them used
    `os.listdir` — non-recursive — which is how `tools/armature_core/` sat outside every one
    of them (F-bca562a1). `label` is the path relative to `directory`, POSIX-spelled, so a
    member in a subpackage is reported as `armature_core/blender_scene.py` rather than as a
    bare basename that could collide.
    """
    out = []
    if not recursive:
        for fn in sorted(os.listdir(directory)):
            if fn.endswith(".py"):
                out.append((fn, os.path.join(directory, fn)))
        return out
    for root, dirs, names in os.walk(directory):
        dirs[:] = sorted(d for d in dirs if d not in skip)
        for fn in sorted(names):
            if not fn.endswith(".py"):
                continue
            path = os.path.join(root, fn)
            label = os.path.relpath(path, directory).replace(os.sep, "/")
            out.append((label, path))
    return sorted(out)


def _operator_call_sites(directory, dotted, *, recursive=True):
    """Every `<dotted>(...)` call in the `.py` files under `directory`.

    Returns `[(label, lineno, captured)]` where `captured` is True when the call is the
    value of an assignment. Keyed on the CALL node, so a rename of the local variable, a
    different keyword set, or a call inside a comprehension is all still one member.

    RECURSIVE since wave 23 (F-bca562a1), skipping `superseded/` — which is walked by its
    own call below, because it is excluded from the size pin and not from the property.
    """
    out = []
    for fn, path in census_sources(directory, recursive=recursive):
        with open(path, encoding="utf-8") as fh:
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
    # RE-DERIVED wave 23 under the recursive walk: 9, unchanged — `armature_core/` exports
    # no GLB, so the widening moves this pin not at all, which is itself the measurement.
    assert len(sites) == 9, sites
    assert sorted({fn for fn, _, _ in sites}) == [
        "author_walk.py", "lift_solve.py", "make_test_armature.py", "rig_bake.py",
        "rig_character.py", "rig_parts.py", "rig_repair.py",
        "rig_retopo.py"], sorted({s[0] for s in sites})
    uncaptured = [(fn, ln) for fn, ln, cap in sites if not cap]
    assert uncaptured == [], uncaptured


#: RE-DERIVED wave 23 (F-bca562a1) under the recursive walk: 14 -> 15. The member that
#: joined is `armature_core/blender_scene.py`, whose render site the old docstring excluded
#: on a stated reason wave 18 measured to be false. It was ALREADY compliant — the status is
#: captured and Gate FRAME refuses on it — so the widening moves the size and finds no
#: offender, which is the honest result: what was outside the census was the requirement,
#: not a defect.
#:
#: Re-derive with:
#:     python -c "import sys;sys.path[:0]=['tests','tools'];
#:     import test_instruments_amend_w14 as M;
#:     print(len(M._operator_call_sites(M.TOOLS,'bpy.ops.render.render')))"
RENDER_SITES_TODAY = 15
RENDER_SITE_MODULES_TODAY = [
    "armature_core/blender_scene.py", "make_binding_sheet.py", "make_parts_sheet.py",
    "make_skeleton_sheet.py", "preview_glb.py", "preview_walk.py", "render_performer.py",
    "render_start_frame.py", "render_turnaround.py",
]


def test_every_render_site_captures_the_operator_status_set():
    """The other half of the family: every `bpy.ops.render.render` site under `tools/`,
    `armature_core/` INCLUDED.

    The exclusion that kept `armature_core/` out is replaced by the measurement that
    overturned it — see the block comment above `census_sources`. Membership is pinned as
    well as size, so the module that joined is named rather than absorbed into a count.
    """
    sites = _operator_call_sites(TOOLS, "bpy.ops.render.render")
    assert len(sites) == RENDER_SITES_TODAY, sites
    assert sorted({fn for fn, _, _ in sites}) == RENDER_SITE_MODULES_TODAY,         sorted({s[0] for s in sites})
    uncaptured = [(fn, ln) for fn, ln, cap in sites if not cap]
    assert uncaptured == [], uncaptured


def test_the_widened_census_reaches_the_site_the_exclusion_named():
    """The finding's operand, by name: the site is in `armature_core/blender_scene.py`, it
    is inside `render_frame`, and the census now holds it.

    The stale docstring cited `blender_scene.py:772`; measured 2026-09-05 the call is at
    `:949` and `RenderedFrame` is raised at `:958` with clause `operator_status`. A
    line-number citation is prose; the FUNCTION and the clause are what this asserts.
    """
    sites = [s for s in _operator_call_sites(TOOLS, "bpy.ops.render.render")
             if s[0] == "armature_core/blender_scene.py"]
    assert len(sites) == 1, sites
    _label, lineno, captured = sites[0]
    assert captured, "the status set is not captured at the one render site every previz "                      "render goes through"

    path = os.path.join(TOOLS, "armature_core", "blender_scene.py")
    tree = ast.parse(open(path, encoding="utf-8").read())
    holder = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))                 and node.lineno <= lineno <= (node.end_lineno or node.lineno):
            if holder is None or node.lineno > holder.lineno:
                holder = node
    assert holder is not None and holder.name == "render_frame", holder

    # The clause is ASSIGNED into the evidence dict here (`ev["clause"] = "operator_status"`
    # immediately above the raise) rather than written as a literal inside the raise's own
    # `{...}`. `_refusal_clause` reads the literal form only and returns None for all four
    # raises in this function — a limit of that predicate worth recording, not a defect in
    # the module: the halt line an operator reads carries the same string either way.
    assigned = [n for n in ast.walk(holder)
                if isinstance(n, ast.Assign) and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Subscript)
                and isinstance(n.targets[0].slice, ast.Constant)
                and n.targets[0].slice.value == "clause"
                and isinstance(n.value, ast.Constant)
                and n.value.value == OPERATOR_STATUS_CLAUSE]
    assert assigned, (
        f"{holder.name} does not declare the `{OPERATOR_STATUS_CLAUSE}` clause; a CANCELLED "
        f"render that returns without raising hands the run the previous frames")
    guards = [n for n in ast.walk(holder)
              if isinstance(n, ast.If) and "FINISHED" in ast.unparse(n.test)
              and any(isinstance(b, ast.Raise) for b in n.body)]
    assert guards, "the captured status set reaches no refusal"


def test_the_superseded_render_site_captures_its_status_set_too():
    """Excluded from the size pin, not from the property: a retired route stays runnable."""
    sites = _operator_call_sites(os.path.join(TOOLS, "superseded"), "bpy.ops.render.render")
    assert [(fn, ln) for fn, ln, cap in sites if not cap] == [], sites


#: The clause a plan-wide render refusal declares in its own receipt. The CLAUSE, not the
#: prose: `tools/preview_glb.py:166` writes `{"clause": "operator_status", "declined": [...]}`
#: and a halt reader keys on that string, never on the sentence around it.
OPERATOR_STATUS_CLAUSE = "operator_status"


def _refusal_clause(node):
    """The `clause` value in a `raise X(msg, {...})`'s evidence dict, or None.

    Reads the dict literal, so rewording the message cannot move it and a message that
    happens to contain a keyword cannot forge it.
    """
    exc = node.exc
    if not isinstance(exc, ast.Call):
        return None
    for arg in list(exc.args) + [kw.value for kw in exc.keywords]:
        if not isinstance(arg, ast.Dict):
            continue
        for key, value in zip(arg.keys, arg.values):
            if (isinstance(key, ast.Constant) and key.value == "clause"
                    and isinstance(value, ast.Constant)):
                return value.value
    return None


def test_the_plan_wide_render_gate_declares_its_clause_and_is_not_found_by_a_word():
    """The premise the census below now rests on, both directions (wave 16).

    `tools/preview_glb.py` must carry a raise whose evidence declares
    `clause == "operator_status"`, and a raise whose MESSAGE merely contains the word
    "declined" must not be mistaken for one — which is what the previous keying did, in a
    way that let any module with that word in any refusal message escape the per-site
    requirement entirely.
    """
    with open(os.path.join(TOOLS, "preview_glb.py"), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    clauses = [_refusal_clause(n) for n in ast.walk(tree) if isinstance(n, ast.Raise)]
    assert OPERATOR_STATUS_CLAUSE in clauses, sorted(c for c in clauses if c)

    decoy = ast.parse(
        'raise SomeGate("the render operator declined 2 of 4 views", {"clause": "elsewhere"})'
    ).body[0]
    assert "declined" in ast.unparse(decoy), "the decoy must carry the word"
    assert _refusal_clause(decoy) != OPERATOR_STATUS_CLAUSE, (
        "a message containing the word must not read as the operator-status clause")


def test_every_captured_render_status_reaches_a_refusal():
    """Capturing a value nobody reads is the shape this wave exists to close.

    For each module carrying a render site: one `_render_status(...)` call and one
    `FINISHED`-testing `if` with a `raise` in its body per site. Keyed on the AST.
    """
    offenders = []
    for root, recursive in ((TOOLS, True), (os.path.join(TOOLS, "superseded"), False)):
        for fn, path in census_sources(root, recursive=recursive):
            with open(path, encoding="utf-8") as fh:
                src = fh.read()
            n_sites = sum(1 for f, _, _ in _operator_call_sites(
                root, "bpy.ops.render.render", recursive=recursive) if f == fn)
            if not n_sites:
                continue
            tree = ast.parse(src)
            calls = [n for n in ast.walk(tree)
                     if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                     and n.func.id == "_render_status"]
            # A refusal keyed on FINISHED, wherever it is written: an `if` whose test names
            # it and whose body raises, OR a plan-wide gate that refuses with the
            # OPERATOR-STATUS CLAUSE. `preview_glb` is the second shape deliberately — its
            # shooter RETURNS the status and `gate_previews_written` refuses once over the
            # whole plan, because a raise inside the shooter would strand a refusal below
            # the first write (measured; see the wave-14 report).
            #
            # WAVE 16: `plan_gate` used to key on the WORD "declined" appearing anywhere in
            # the unparsed raise — a prose token in a message string. Two ways that
            # disarms: reword `preview_glb`'s message and the plan gate vanishes, and — the
            # dangerous direction — ANY module whose refusal message happens to contain the
            # word escapes the `len(raises) >= n_sites` requirement entirely and passes with
            # no status refusal at all. The clause key is the machine-readable thing the
            # halt record carries and the thing a reader keys on, so that is what this
            # keys on: `{"clause": "operator_status", ...}` beside a `FINISHED` test.
            raises = [n for n in ast.walk(tree) if isinstance(n, ast.If)
                      and "FINISHED" in ast.unparse(n.test)
                      and any(isinstance(b, ast.Raise) for b in n.body)]
            plan_gate = [n for n in ast.walk(tree)
                         if isinstance(n, ast.Raise)
                         and _refusal_clause(n) == OPERATOR_STATUS_CLAUSE
                         and "FINISHED" in ast.unparse(tree)]
            # every site's status must be CAPTURED, and the module must refuse on it
            if len(calls) < n_sites or not (len(raises) >= n_sites or plan_gate):
                offenders.append((fn, n_sites, len(calls), len(raises), len(plan_gate)))
    assert offenders == [], offenders


def test_the_render_status_helper_is_one_implementation_in_every_copy():
    """It is spelled once per tool because `armature_core` is out of this domain's globs.
    The duplication is held from drifting rather than excused.

    WAVE 23 (F-bca562a1): the copy in `armature_core/blender_scene.py` joins this census
    with the recursive walk — 9 copies became 10. Its DOCSTRING differs (it records that its
    executable body is copied verbatim from `render_turnaround`), so the comparison is on
    the EXECUTABLE BODY with the docstring stripped, which is the resolved shape of "one
    implementation" and a stronger property than byte-identity of the whole node: it admits
    a copy that documents where it came from and still refuses one whose code has drifted.
    Measured 2026-09-05: 10 copies, ONE distinct executable body,
    `try: return sorted(str(s) for s in result) / except TypeError: return []`.
    """
    bodies = {}
    for root, recursive in ((TOOLS, True), (os.path.join(TOOLS, "superseded"), False)):
        for fn, path in census_sources(root, recursive=recursive):
            with open(path, encoding="utf-8") as fh:
                src = fh.read()
            if "def _render_status" not in src:
                continue
            tree = ast.parse(src)
            node = next(n for n in tree.body
                        if isinstance(n, ast.FunctionDef) and n.name == "_render_status")
            body = list(node.body)
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                body = body[1:]
            label = fn if root == TOOLS else f"superseded/{fn}"
            bodies[label] = "; ".join(ast.unparse(b) for b in body)
    assert len(bodies) == 10, sorted(bodies)
    assert "armature_core/blender_scene.py" in bodies, sorted(bodies)
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


# ================================== F-0bf74152 — the guarded engine selection, everywhere
#
# THE OPERAND. The guarded loop F-bba38f1c earned existed on the four SHEET tools and on
# none of the four RENDERERS: `preview_walk`, `render_performer`, `render_start_frame` and
# `render_turnaround` each pinned the single literal `'BLENDER_EEVEE'`. The candidate list
# exists precisely because that identifier is not stable across Blender versions, and the
# sheets' `except TypeError: continue` is this repo's own evidence that an invalid enum
# name RAISES. The census below keys on the ASSIGNMENT to `<scene>.render.engine` — the
# node the property lives on — not on the presence of a candidate list, which is what the
# wave-8 census counted and is why it could not see the four bare assignments.


def _engine_assignments(directory):
    """Every `<expr>.render.engine = ...` assignment under `directory`, with its function.

    Returns `[(filename, funcname, lineno, guarded)]`. `guarded` is True when the enclosing
    function iterates candidates, wraps the assignment in `try/except TypeError` and
    carries a `raise` for the exhausted case — the `preview_glb.select_engine` shape.
    """
    out = []
    for root in (directory, os.path.join(directory, "superseded")):
        if not os.path.isdir(root):
            continue
        for fn in sorted(os.listdir(root)):
            if not fn.endswith(".py"):
                continue
            with open(os.path.join(root, fn), encoding="utf-8") as fh:
                src = fh.read()
            tree = ast.parse(src)
            parents = {}
            for func in [n for n in ast.walk(tree)
                         if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
                for node in ast.walk(func):
                    parents[id(node)] = func
            for node in ast.walk(tree):
                if not isinstance(node, ast.Assign):
                    continue
                for t in node.targets:
                    if not (isinstance(t, ast.Attribute) and t.attr == "engine"
                            and isinstance(t.value, ast.Attribute)
                            and t.value.attr == "render"):
                        continue
                    func = parents.get(id(node))
                    if func is None:
                        out.append((fn, "<module>", node.lineno, False))
                        continue
                    body = ast.unparse(func)
                    guarded = ("for " in body and "except TypeError" in body
                               and any(isinstance(n, ast.Raise) for n in ast.walk(func)))
                    out.append((fn, func.name, node.lineno, guarded))
    return out


def test_every_render_engine_assignment_is_guarded():
    """SIZE, MEMBERSHIP, then the property — measured on this tree 2026-09-04.

    Nine assignments to `<scene>.render.engine` across `tools/` (the four sheet tools'
    `light_the_scene`, `preview_glb.select_engine`, and — new this wave — the four
    renderers' and `rig_bake`'s own `select_engine`). Every one sits inside a candidate
    loop with a `TypeError` handler and a refusal for the exhausted case; before this wave
    five of them were bare literal assignments.
    """
    sites = _engine_assignments(TOOLS)
    bare = [(fn, func, ln) for fn, func, ln, guarded in sites if not guarded]
    assert bare == [], bare
    assert len(sites) == 10, sites


def test_no_renderer_pins_a_single_engine_identifier():
    """The shape the finding named: the literal, with nothing around it."""
    offenders = []
    for fn in ("preview_walk.py", "render_performer.py", "render_start_frame.py",
               "render_turnaround.py"):
        with open(os.path.join(TOOLS, fn), encoding="utf-8") as fh:
            src = fh.read()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            for t in node.targets:
                if (isinstance(t, ast.Attribute) and t.attr == "engine"
                        and isinstance(node.value, ast.Constant)):
                    offenders.append((fn, node.lineno, node.value.value))
    assert offenders == [], offenders


@pytest.mark.parametrize("filename,gate_name", [
    ("preview_walk.py", "PreviewWalkGate"),
    ("render_performer.py", "RenderGate"),
    ("render_start_frame.py", "RenderGate"),
    ("render_turnaround.py", "RenderTurnaroundGate"),
    ("rig_bake.py", "BakeEmpty"),
])
def test_select_engine_refuses_when_no_candidate_is_valid(filename, gate_name):
    """RED on the operand: a Blender that accepts NEITHER identifier.

    The scene's `render.engine` setter raises `TypeError` on an invalid enum name — the
    behaviour the sheets' `except TypeError` records — so a scene that refuses every
    candidate must halt with a named refusal rather than render on whatever the factory
    settings left in place. Reverted-red: yes; on the base tree these four modules have no
    `select_engine` at all and the bare assignment raises an untyped `TypeError`.
    """
    mod = load_tool(filename)
    gate = getattr(mod, gate_name)

    class _RefusesEveryEngine:
        class render:                              # noqa: N801 - mirrors bpy's shape
            @staticmethod
            def __setattr__(name, value):          # pragma: no cover - unreachable
                raise TypeError(name)

    class _Render:
        def __setattr__(self, name, value):
            raise TypeError(f"bpy_struct: item.attr = val: enum {value!r} not found")

    class _Scene:
        def __init__(self):
            object.__setattr__(self, "render", _Render())

    with pytest.raises(gate) as exc:
        mod.select_engine(_Scene())
    assert exc.value.evidence["clause"] == "engine"
    assert exc.value.evidence["candidates"] == list(mod.ENGINE_CANDIDATES)


@pytest.mark.parametrize("filename", [
    "preview_walk.py", "render_performer.py", "render_start_frame.py",
    "render_turnaround.py", "rig_bake.py",
])
def test_select_engine_returns_the_first_candidate_that_takes(filename):
    """The other direction, and the reason the return value exists: the record states the
    engine that was SET, not the one that was asked for."""
    mod = load_tool(filename)
    accepted = mod.ENGINE_CANDIDATES[-1]

    class _Render:
        def __init__(self):
            object.__setattr__(self, "engine", None)

        def __setattr__(self, name, value):
            if value != accepted:
                raise TypeError(f"enum {value!r} not found")
            object.__setattr__(self, name, value)

    class _Scene:
        def __init__(self):
            object.__setattr__(self, "render", _Render())

    scene = _Scene()
    assert mod.select_engine(scene) == accepted
    assert scene.render.engine == accepted


def test_the_four_renderers_record_the_engine_they_actually_set():
    """A literal in a provenance record is an assertion, not a measurement. Two of the four
    published `"engine": "BLENDER_EEVEE"` as a literal beside an unguarded assignment."""
    offenders = []
    for fn in ("preview_walk.py", "render_performer.py", "render_start_frame.py",
               "render_turnaround.py", "rig_bake.py"):
        with open(os.path.join(TOOLS, fn), encoding="utf-8") as fh:
            src = fh.read()
        tree = ast.parse(src)
        found = False
        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue
            for k, v in zip(node.keys, node.values):
                if not (isinstance(k, ast.Constant) and k.value == "engine"):
                    continue
                text = ast.unparse(v)
                if isinstance(v, ast.Constant):
                    offenders.append((fn, node.lineno, text))
                else:
                    found = True
        if not found:
            offenders.append((fn, None, "no engine field in any record"))
    assert offenders == [], offenders


# ============================ F-267361f5 — the turnaround's frame size is bounded, above
#                                            the line that assigns it to the scene
#
# THE OPERAND. `render_turnaround`'s `--width`/`--height` were bare `type=int` with no
# bound: read at :528, assigned to `scene.render.resolution_x/_y` at :544, and handed
# unvalidated to the framing solvers and to Gate WHOLE. Measured on the tool's own solvers
# with a three-point cloud: `(0, 1024)` and `(1024, 0)` each raise a bare
# `ZeroDivisionError` out of `armature_core.startframe.silhouette_extent` — AFTER the scene
# resolution has been set to zero — and `(-1024, 1024)` returns the SAME radius as
# `1024x1024`, surfacing one render later inside Gate WHOLE. `833x481` passed both.
# `render_start_frame.require_frame_size` is the sibling's closed form; it is imported here
# rather than copied.


@pytest.fixture(scope="module")
def turn():
    return load_tool("render_turnaround.py")


@pytest.mark.parametrize("w,h,clause", [
    (0, 1024, "non_positive"),
    (1024, 0, "non_positive"),
    (-1024, 1024, "non_positive"),
    (833, 481, "not_divisible"),
])
def test_the_turnaround_refuses_a_frame_size_its_solvers_cannot_take(turn, w, h, clause):
    """RED on the operand: the flag values the finding measured.

    Reverted-red: yes — on the base tree `main` does `width, height = int(a.width),
    int(a.height)` and nothing between there and `silhouette_extent` looks at either.
    """
    with pytest.raises(turn.RenderTurnaroundGate) as exc:
        turn.require_frame_size(w, h, who="render_turnaround",
                                module_frame=(turn.WIDTH, turn.HEIGHT),
                                gate=turn.RenderTurnaroundGate,
                                gate_id="TURNAROUND_FRAME")
    ev = exc.value.evidence
    assert clause in ev, ev
    assert ev["who"] == "render_turnaround"
    # RE-DERIVED wave 22, F-6381b9ff (branch-local): `evidence["gate"]` is the RAISING
    # CLASS's id, so this key, `exc.gate` and `str(exc)`'s `[<gate>]` prefix are ONE
    # id; the caller's declared `gate_id` is the SUB-id under "sub_gate". Until then a
    # single halt event printed two, and "TURNAROUND_FRAME" was declared by no class.
    assert ev["gate"] == turn.RenderTurnaroundGate.gate == "TURNAROUND"
    assert ev["sub_gate"] == "TURNAROUND_FRAME"
    assert "--width" in str(exc.value) and "--height" in str(exc.value)


def test_the_turnaround_default_frame_is_accepted(turn):
    """A bound that refuses the tool's own default is not a bound, it is a bug. 352x1024
    is a multiple of 16 on both axes."""
    assert turn.require_frame_size(
        turn.WIDTH, turn.HEIGHT, who="render_turnaround",
        module_frame=(turn.WIDTH, turn.HEIGHT), gate=turn.RenderTurnaroundGate,
    ) == (turn.WIDTH, turn.HEIGHT)


def test_the_frame_size_refusal_runs_above_the_resolution_assignment(turn):
    """THE ORDERING CLAUSE F-34a858f5 earned, and the half this finding is about: a check
    below the assignment refuses a scene that has already been set to the bad number."""
    src = read_source("render_turnaround.py")
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "main")
    check_lines = [n.lineno for n in ast.walk(fn)
                   if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                   and n.func.id == "require_frame_size"]
    assert len(check_lines) == 1, check_lines
    assign_lines = [n.lineno for n in ast.walk(fn)
                    if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Attribute) and t.attr == "resolution_x"
                            for tgt in n.targets
                            for t in (tgt.elts if isinstance(tgt, ast.Tuple) else [tgt]))]
    assert assign_lines, "render_turnaround no longer assigns scene.render.resolution_x"
    assert check_lines[0] < min(assign_lines), (check_lines, assign_lines)


def test_there_is_one_require_frame_size_and_two_callers():
    """One implementation, carried — never a second copy. `armature_core.startframe` is
    where it belongs and is outside this domain's globs, so the lift is FILED."""
    defs = []
    for fn in sorted(os.listdir(TOOLS)):
        if not fn.endswith(".py"):
            continue
        with open(os.path.join(TOOLS, fn), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        defs += [(fn, n.lineno) for n in tree.body
                 if isinstance(n, ast.FunctionDef) and n.name == "require_frame_size"]
    assert defs == [("render_start_frame.py", defs[0][1] if defs else 0)], defs


def test_the_start_frame_caller_still_gets_its_own_refusal_class(turn):
    """Parameterising the gate must not change what the ORIGINAL caller raises."""
    rsf = load_tool("render_start_frame.py")
    with pytest.raises(rsf.RenderGate) as exc:
        rsf.require_frame_size(0, 480)
    assert exc.value.evidence["gate"] == "STARTFRAME"
    assert exc.value.evidence["who"] == "render_start_frame"
    assert rsf.require_frame_size(832, 480) == (832, 480)


# ================================= F-a74b69c9 / F-4db23b72 — the two true stranded refusals
#
# THE OPERAND, both times: a refusal whose only input is available long before the first
# byte is written, sitting below it. `make_skeleton_sheet.gate_any_pivot_matched(table)` was
# called 36 lines after `table` was produced and 28 lines after `os.makedirs(frames)`, with
# four body/bones panels shot into `frames/` in between and nothing in the gate reading any
# of them. `make_rig_sheet.import_reference`'s argument is `args['reference']`, a path known
# at PARSE time, and seven panels sat between the directory and it. Both left a half-built
# approval artifact where a refusal belonged — which reads as an interrupted render, and is
# more misreadable than the empty directory the wave-12 comments were written against.


def _write_ordering():
    import test_instrument_write_ordering as W

    return W


def test_the_two_true_strands_are_no_longer_below_a_first_write():
    """RED on the operand: the repo's own behavioural walk, over the two tools the
    coordinator named. Reverted-red: yes — both names come back."""
    W = _write_ordering()
    assert W.refusals_below_the_first_write("make_skeleton_sheet") == []
    assert W.refusals_below_the_first_write("make_rig_sheet") == []


def test_the_skeleton_sheet_gate_sits_directly_under_the_table_it_reads():
    """Not merely above the directory — above it AND adjacent to its own input, so a later
    edit that moves the directory up cannot re-strand it."""
    src = read_source("make_skeleton_sheet.py")
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "main")
    gate_lines = [n.lineno for n in ast.walk(fn)
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                  and n.func.id == "gate_any_pivot_matched"]
    snap_lines = [n.lineno for n in ast.walk(fn)
                  if isinstance(n, ast.Call)
                  and ast.unparse(n.func).endswith("snap_sites_to_balls")]
    write_lines = [n.lineno for n in ast.walk(fn)
                   if isinstance(n, ast.Call)
                   and ast.unparse(n.func).endswith("makedirs")]
    assert len(gate_lines) == 1 and snap_lines and write_lines, (
        gate_lines, snap_lines, write_lines)
    assert snap_lines[0] < gate_lines[0] < min(write_lines), (
        snap_lines, gate_lines, write_lines)


def test_make_rig_sheet_refuses_a_missing_reference_before_it_makes_a_directory(tmp_path):
    """RED on the operand the finding named: `--reference` naming a path that is not there.

    The refusal fires and `--out` is never created — the half-built `panels/` the finding is
    about cannot exist. Reverted-red: yes; on the base tree the check is inside
    `import_reference`, 55 lines below `os.makedirs(out_dir)`.
    """
    mod = load_tool("make_rig_sheet.py")
    out = tmp_path / "sheet"
    with pytest.raises(mod.ArmatureError, match="--reference"):
        mod.require_reference_file(str(tmp_path / "no_such.glb"))
    assert not out.exists()
    real = tmp_path / "ref.glb"
    real.write_bytes(b"glTF")
    assert mod.require_reference_file(str(real)) == os.path.abspath(str(real))


def test_make_rig_sheet_imports_the_reference_above_the_first_write():
    """The whole refusal, not only its argv half: the ambiguous-import `raise` inside
    `import_reference` needs the scene and the skinned mesh, and both exist above the
    directory — so the import is performed there and the reference is hidden immediately."""
    src = read_source("make_rig_sheet.py")
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "main")
    import_lines = [n.lineno for n in ast.walk(fn)
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                    and n.func.id == "import_reference"]
    write_lines = [n.lineno for n in ast.walk(fn)
                   if isinstance(n, ast.Call)
                   and ast.unparse(n.func).endswith("makedirs")]
    assert len(import_lines) == 1, import_lines
    assert import_lines[0] < min(write_lines), (import_lines, write_lines)


# ===================================== F-7e7703cb — a success line earned by a measurement


def test_the_bone_heat_sentinel_carries_the_sweep_s_own_counts():
    """THE OPERAND: the token, and what follows it.

    `print('DIAGNOSE_BONE_HEAT_OK ' + path)` put nothing after the token but the JSON's
    location, so the sentinel was earned by reaching the end of `main`. The twelve arms'
    numbers existed one line below it. This drives `main`'s printing block by AST rather
    than by running Blender: the OK line's payload must be derived from `arms`.
    Reverted-red: yes — the base tree's line is a bare concatenation with `path`.
    """
    src = read_source("diagnose_bone_heat.py")
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "main")
    prints = [n for n in ast.walk(fn)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
              and n.func.id == "print"
              and "DIAGNOSE_BONE_HEAT_OK" in ast.unparse(n)]
    assert len(prints) == 1, [ast.unparse(n) for n in prints]
    payload = ast.unparse(prints[0])
    for key in ("n_arms", "n_arms_with_weight", "best_arm", "best_weighted_fraction"):
        assert key in payload, (key, payload)
    assert "arms" in payload, payload
    assert payload.strip() != "print('DIAGNOSE_BONE_HEAT_OK ' + path)"


def test_an_all_zero_sweep_reads_differently_from_a_working_one():
    """The two cases the old sentinel could not tell apart, computed with the tool's own
    expressions over synthetic arm records. An all-zero sweep is a LEGITIMATE result for a
    diagnostic, so it must still be an OK line — but a distinguishable one."""
    def summarise(arms):
        weighted = {k: v for k, v in arms.items() if v["weighted_fraction"] > 0}
        best = max(arms.items(), key=lambda kv: kv[1]["weighted_fraction"], default=None)
        return {"n_arms": len(arms), "n_arms_with_weight": len(weighted),
                "best_arm": best[0] if best else None,
                "all_arms_weighted_nothing": len(weighted) == 0}

    dead = {f"arm{i}": {"weighted_fraction": 0.0} for i in range(12)}
    live = dict(dead, arm3={"weighted_fraction": 0.81})
    assert summarise(dead)["n_arms_with_weight"] == 0
    assert summarise(dead)["all_arms_weighted_nothing"] is True
    assert summarise(live)["n_arms_with_weight"] == 1
    assert summarise(live)["best_arm"] == "arm3"
    assert summarise(dead) != summarise(live)


def test_the_bone_heat_sweep_still_has_no_gate_on_an_all_zero_result():
    """The direction that must NOT be added. An all-zero sweep is the exact condition this
    diagnostic exists to investigate; a refusal there would delete the finding."""
    src = read_source("diagnose_bone_heat.py")
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "main")
    for node in ast.walk(fn):
        if isinstance(node, ast.Raise):
            assert "weighted" not in ast.unparse(node), ast.unparse(node)
