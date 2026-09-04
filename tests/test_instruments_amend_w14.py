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
