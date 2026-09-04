"""The parts of `blender_scene` that are arithmetic and topology, not Blender.

`blender_scene` is the only module that imports `bpy`, so nothing in it was reachable
from the suite and its checks went untested by construction — including the three
compositor link-topology refusals, whose own comment names them as the andon ("a dry_run
PASS does not prove link sanity — check the topology in code").

`bpy` and `mathutils` are stubbed here so the module imports. Nothing below touches a
stub: every function exercised is pure. A test that needed a real Blender would belong in
`tests/test_blender_conventions.py`, which subprocesses one.
"""

import importlib
import sys
import types

import numpy as np
import pytest

from armature_core.errors import GateFailure


@pytest.fixture(scope="module")
def BS():
    """`blender_scene` imported against stub bpy/mathutils, then unimported.

    The cleanup is load-bearing, not tidiness: `tests/test_cli.py` asserts
    `cli._probe("blender_scene") == "needs-blender"`, which is a reading about `import bpy`
    FAILING. A stub left in `sys.modules` would make that import succeed and turn a real
    row green for the wrong reason - the exact class of defect this suite exists to catch,
    manufactured by its own fixture.
    """
    installed = []
    for name in ("bpy", "mathutils"):
        if name not in sys.modules:
            stub = types.ModuleType(name)
            stub.context = types.SimpleNamespace()
            stub.data = types.SimpleNamespace()
            stub.ops = types.SimpleNamespace()
            sys.modules[name] = stub
            installed.append(name)
    cached = sys.modules.pop("armature_core.blender_scene", None)
    before = set(sys.modules)
    try:
        yield importlib.import_module("armature_core.blender_scene")
    finally:
        # The registry entry is not the only binding. Importing `armature_core.blender_scene`
        # also sets `blender_scene` as an attribute of the package, and
        # `from armature_core import blender_scene` (stage_render's Blender backend) reads
        # that attribute BEFORE consulting sys.modules — so a registry-only teardown left
        # test_run_export reading Blender as importable through this fixture's stub.
        # Measured by the wave-6 serial verify: this file then test_run_export.py → 1 failed.
        # Same rule as conftest.rt and blender_stub.blender_stubbed: everything first
        # imported under the stub goes, registry and attribute both.
        for name in sorted(set(sys.modules) - before):
            if name == "armature_core" or name.startswith("armature_core."):
                gone = sys.modules.pop(name, None)
                parent_name, _, child = name.rpartition(".")
                parent = sys.modules.get(parent_name) if parent_name else None
                if parent is not None and getattr(parent, child, None) is gone:
                    delattr(parent, child)
        for name in installed:
            sys.modules.pop(name, None)
        if cached is not None:
            sys.modules["armature_core.blender_scene"] = cached
            setattr(sys.modules["armature_core"], "blender_scene", cached)


def test_this_module_does_not_stub_bpy_at_import_time():
    """The regression this guards: an earlier draft installed the stubs at module scope,
    which leaves them in `sys.modules` for the whole session. Collection alone must not
    make `import bpy` succeed. (The fixture's teardown is measured by running this file
    together with `tests/test_cli.py`, whose `needs-blender` rows are readings about that
    import failing.)"""
    assert "bpy" not in sys.modules or getattr(sys.modules["bpy"], "__file__", None)


# ------------------------------------------------- the compositor wiring is a typed gate


def test_a_compositor_output_with_no_incoming_link_raises_a_typed_gate(BS):
    """F-ac989919. The three checks raised a bare RuntimeError with no gate id and no
    evidence. `ArmatureError` subclasses `RuntimeError`, so this was not merely untyped:
    `stage_render.py:508` catches only `GateFailure` and prints GATE_FAILURE /
    GATE_EVIDENCE before returning 2, so a compositor mis-wiring escaped that handler
    entirely and surfaced as an unhandled traceback with no receipt lines at all."""
    with pytest.raises(BS.CompositorWiring) as exc:
        BS.gate_compositor_wiring("depth", "Depth", "Render Layers", [])
    assert isinstance(exc.value, GateFailure)
    ev = exc.value.evidence
    assert ev["gate"] == exc.value.gate == "COMPOSITOR"
    assert ev["tag"] == "depth" and ev["n_links"] == 0
    assert ev["expected_socket"] == "Depth"


def test_a_second_incoming_link_raises(BS):
    with pytest.raises(BS.CompositorWiring) as exc:
        BS.gate_compositor_wiring("depth", "Depth", "Render Layers",
                                  [("Render Layers", "Depth"), ("Blur", "Image")])
    assert exc.value.evidence["n_links"] == 2


def test_a_source_that_is_not_the_render_layers_node_raises(BS):
    with pytest.raises(BS.CompositorWiring) as exc:
        BS.gate_compositor_wiring("depth", "Depth", "Render Layers",
                                  [("Blur", "Depth")])
    assert exc.value.evidence["from_node"] == "Blur"
    assert "Render Layers" in str(exc.value)


def test_the_depth_pass_wired_to_the_alpha_socket_raises_naming_both_sockets(BS):
    """The measured worst case in the finding: Depth wired to Alpha. The check correctly
    stops the run; what it did not do was leave a gate id or a measurement behind."""
    with pytest.raises(BS.CompositorWiring) as exc:
        BS.gate_compositor_wiring("depth", "Depth", "Render Layers",
                                  [("Render Layers", "Alpha")])
    ev = exc.value.evidence
    assert ev["expected_socket"] == "Depth" and ev["got_socket"] == "Alpha"
    assert str(exc.value).startswith("[COMPOSITOR]")


def test_correct_wiring_returns_its_evidence_rather_than_nothing(BS):
    ev = BS.gate_compositor_wiring("depth", "Depth", "Render Layers",
                                   [("Render Layers", "Depth")])
    assert ev["gate"] == "COMPOSITOR" and ev["got_socket"] == "Depth"
    assert "verdict" in ev


# ------------------------------------ the union sphere holds one frame's vertices at once


def _frames(arrays):
    """A callable returning a FRESH iterator each time, which is what `union_sphere`
    requires — and what makes the two-pass form possible without retention."""
    return lambda: iter(arrays)


def test_the_union_sphere_bounds_every_frame_about_the_union_centre(BS):
    a = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    b = np.array([[0.0, 0.0, 2.0], [-1.0, 0.0, 2.0]])
    center, half, radius = BS.union_sphere(_frames([a, b]))
    assert center == pytest.approx([0.0, 0.0, 1.0])
    assert half == pytest.approx([1.0, 0.0, 1.0])
    # The far corner is (-1, 0, 2) and (1, 0, 0), both sqrt(2) from the union centre.
    assert radius == pytest.approx(np.sqrt(2.0))


def test_the_union_sphere_matches_the_one_pass_arithmetic_it_replaces(BS):
    """The retained-array version computed exactly this; the two-pass version must not
    change the number, only where the memory goes."""
    rng = np.random.default_rng(7)
    arrays = [rng.uniform(-1.0, 1.0, size=(50, 3)) + i * 0.1 for i in range(9)]
    center, half, radius = BS.union_sphere(_frames(arrays))

    allpts = np.concatenate(arrays, axis=0)
    lo, hi = allpts.min(axis=0), allpts.max(axis=0)
    want_center = (lo + hi) * 0.5
    want_radius = max(float(np.linalg.norm(a - want_center, axis=1).max()) for a in arrays)
    assert center == pytest.approx(want_center)
    assert half == pytest.approx((hi - lo) * 0.5)
    assert radius == pytest.approx(want_radius)


def test_the_union_sphere_is_none_when_no_frame_carried_geometry(BS):
    assert BS.union_sphere(_frames([])) is None
    assert BS.union_sphere(_frames([np.zeros((0, 3))])) is None


def test_the_union_sphere_iterates_twice_and_retains_no_frame(BS):
    """F-39c191a8. `centers.append(pts)` appended every frame's FULL evaluated vertex
    array and held the list until the radius loop consumed it, so peak resident memory was
    the whole shot's geometry at once — on the performer (306,110 faces, float64) roughly
    0.3 GB for 81 frames and 1.2 GB for 320, on a rig whose Blender process is also
    rendering. The union radius needs two passes over the frames, not one pass plus a
    list: this pins that the second pass re-reads rather than replays.
    """
    seen = []

    def frames():
        seen.append("pass")
        for arr in (np.array([[0.0, 0.0, 0.0]]), np.array([[2.0, 0.0, 0.0]])):
            yield arr

    BS.union_sphere(frames)
    assert len(seen) == 2, f"expected two passes over the frames, got {len(seen)}"


def test_a_single_use_iterator_is_refused_rather_than_silently_read_once(BS):
    """Handing this an exhausted iterator would make the radius pass read nothing and
    return 0.0 — a bounding sphere of radius zero around a real subject, with every other
    check green."""
    # WAVE 12 (F-9fab7829): `NonReiterableFrames`, not a bare `TypeError` — the halt
    # contract records a builtin as "FAILED - an unhandled error" at exit 1 where this is a
    # refusal at exit 2, and the class this function already raises for the same reason
    # exists two clauses down.
    with pytest.raises(BS.NonReiterableFrames, match=r"takes a CALLABLE"):
        BS.union_sphere(iter([np.array([[0.0, 0.0, 0.0]])]))


# ----------------------------------------- the public evaluated-vertices name (wave-5 note)


def test_the_evaluated_vertex_reader_has_a_public_name_that_filters_by_visibility(BS):
    """Two tools import `_evaluated_world_vertices` by its underscore name and apply no
    visibility filter, so geometry that will not render can define a measurement. The
    public entry point takes the scene and filters through `render_visible_meshes`; the
    private one stays the unfiltered primitive this module's own already-filtered callers
    use."""
    import inspect

    assert hasattr(BS, "evaluated_world_vertices")
    params = list(inspect.signature(BS.evaluated_world_vertices).parameters)
    assert params[:2] == ["scene", "objects"], params
    assert "render_visible_meshes" in inspect.getsource(BS.evaluated_world_vertices)


# --- F-ae34fe44: callability is not re-iterability -----------------------------------


def test_a_callable_returning_a_spent_iterator_is_refused_not_read_as_radius_zero(BS):
    """Measured against the stubbed module over two frames spanning a 1.118 bounding
    radius: `union_sphere(lambda: iter(frames))` returned radius 1.118033988749895, while
    `it = iter(frames); union_sphere(lambda: it)` PASSED the `callable()` guard and
    returned radius 0.0 — `centre` and `half` correct in both, so nothing anywhere
    disagreed with the zero. That radius is `auto_radius`'s only size input, so a 0.0
    sphere puts the orbit camera on the target with the subject wrapped around the lens.
    """
    frames = [np.array([[-1.0, 0.0, 0.0]]), np.array([[1.0, 0.0, 1.0]])]
    it = iter(frames)
    with pytest.raises(BS.NonReiterableFrames) as exc:
        BS.union_sphere(lambda: it)
    msg = str(exc.value)
    assert "2" in msg and "0" in msg, msg
    assert "second pass" in msg


def test_a_generator_function_over_a_spent_source_is_refused(BS):
    """The exact shape `world_bounds_over_frames.frames()` uses — a generator FUNCTION,
    perfectly callable, closing over a source that is already spent."""
    src = iter([np.array([[0.0, 0.0, 0.0]]), np.array([[1.0, 1.0, 1.0]])])

    def frames():
        for arr in src:
            yield arr

    with pytest.raises(BS.NonReiterableFrames, match=r"not re-iterable"):
        BS.union_sphere(frames)


def test_a_partly_spent_source_is_refused_too(BS):
    """A spent iterator yields zero; a partly-spent one yields fewer. Counting both
    passes catches every shape `callable()` cannot."""
    arrays = [np.array([[float(i), 0.0, 0.0]]) for i in range(4)]
    state = {"n": 0}

    def frames():
        state["n"] += 1
        take = arrays if state["n"] == 1 else arrays[:2]
        return iter(take)

    with pytest.raises(BS.NonReiterableFrames) as exc:
        BS.union_sphere(frames)
    assert "4" in str(exc.value) and "2" in str(exc.value)


def test_a_genuinely_re_iterable_source_still_returns_the_same_numbers(BS):
    """The check binds in both directions: handed a fresh iterator the two passes must
    still reproduce the one-pass arithmetic exactly."""
    rng = np.random.default_rng(11)
    arrays = [rng.uniform(-1.0, 1.0, size=(30, 3)) + i * 0.2 for i in range(5)]
    center, half, radius = BS.union_sphere(_frames(arrays))
    allpts = np.concatenate(arrays, axis=0)
    lo, hi = allpts.min(axis=0), allpts.max(axis=0)
    want_center = (lo + hi) * 0.5
    assert center == pytest.approx(want_center)
    assert half == pytest.approx((hi - lo) * 0.5)
    assert radius == pytest.approx(
        max(float(np.linalg.norm(a - want_center, axis=1).max()) for a in arrays))


def test_a_source_whose_empty_frames_differ_between_passes_is_refused(BS):
    """The count is of frames YIELDED, before the empty-array skip, so a source that
    changes what it yields between passes is caught even when the geometry agrees."""
    state = {"n": 0}

    def frames():
        state["n"] += 1
        if state["n"] == 1:
            return iter([np.zeros((0, 3)), np.array([[1.0, 0.0, 0.0]])])
        return iter([np.array([[1.0, 0.0, 0.0]])])

    with pytest.raises(BS.NonReiterableFrames, match=r"not re-iterable"):
        BS.union_sphere(frames)


# --- F-0e29613a: the measuring entry points go through the filtering reader -----------


def _routing_probe(BS, monkeypatch):
    """Record what `evaluated_world_vertices` was handed, without a real depsgraph."""
    seen = {}

    def fake_visible(scene, objects):
        seen["scene"] = scene
        return ["visible-only"]

    def fake_points(objects):
        seen["measured"] = objects
        return np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])

    monkeypatch.setattr(BS, "render_visible_meshes", fake_visible)
    monkeypatch.setattr(BS, "_evaluated_world_vertices", fake_points)
    return seen


def test_world_bounds_filters_by_render_visibility_when_it_is_given_the_scene(BS,
                                                                              monkeypatch):
    """`evaluated_world_vertices(scene, objects)` was introduced so that "there is no
    shape of it that skips the filter", and it guarded ONE entry point of five: this one,
    `world_bounds_over_frames`, `evaluated_geometry_signature` and `projected_bbox_px` all
    still called the unfiltered primitive on whatever list they were handed (F-0e29613a).
    """
    seen = _routing_probe(BS, monkeypatch)
    BS.world_bounds(["a", "b"], scene="SCENE")
    assert seen == {"scene": "SCENE", "measured": ["visible-only"]}


def test_world_bounds_without_a_scene_is_now_refused_by_name(BS, monkeypatch):
    """CORRECTED IN PLACE, wave 12 (F-e2be2262 / F-efe65849). This test used to assert the
    other direction — "the caller-filtered contract is unchanged" — and pinned that
    `world_bounds(["a","b"])` measured what it was handed. That contract is gone: the
    docstring justifying it said "three call sites in other domains still omit it and the
    signature cannot tighten until they move", and a grep across `tools/` and `tests/` on
    the wave-12 base found ZERO live call sites omitting `scene` (the only omission,
    `tools/superseded/render_reference.py:183`, is inside `UNFILTERED_BAN_EXEMPT_DIRS` by
    name and date). So `scene` is required, and an explicit `scene=None` is refused toward
    `unfiltered_world_bounds` — the name a deliberately naive reading has."""
    _routing_probe(BS, monkeypatch)
    with pytest.raises(TypeError):
        BS.world_bounds(["a", "b"])
    with pytest.raises(BS.MeasurementWithoutScene) as exc:
        BS.world_bounds(["a", "b"], scene=None)
    assert "unfiltered_world_bounds" in str(exc.value)
    assert exc.value.evidence["gate"] is None
    assert exc.value.evidence["clause"] == "world_bounds_without_scene"


def test_there_is_now_only_ONE_naive_spelling_and_it_is_the_naive_NAME(BS, monkeypatch):
    """CORRECTED IN PLACE, wave 12 (F-e2be2262 / F-efe65849). This test used to pin the two
    spellings as the SAME measurement — `world_bounds(objects)` with `scene` omitted was
    behaviourally identical to `unfiltered_world_bounds(objects)`, same triple and same
    object list handed to the primitive — with the reasoning that "a ban is only worth
    having while these two really are the same call".

    They are no longer the same call, and the correction is the stronger one the old
    docstring asked for: the ambiguous spelling has been removed rather than merely banned
    suite-side, so a deliberate naive row and a forgotten `scene=` can no longer be
    confused because the second one does not run. What is pinned now is that
    `unfiltered_world_bounds` is the ONE naive reader and that the filtered name has no
    naive shape at all.
    """
    seen = _routing_probe(BS, monkeypatch)
    naive_name = BS.unfiltered_world_bounds(["decoy", "real"])
    assert "scene" not in seen
    assert seen["measured"] == ["decoy", "real"]
    assert len(naive_name) == 3

    for call in (lambda: BS.world_bounds(["decoy", "real"], scene=None),
                 lambda: BS.world_bounds(["decoy", "real"])):
        with pytest.raises((BS.MeasurementWithoutScene, TypeError)):
            call()


def test_the_unfiltered_bounds_have_a_public_name(BS, monkeypatch):
    """`probe_subject` reports the naive bounds beside the filtered ones, and
    `tests/blender/check_visibility.py` pins that the two differ — so the naive
    measurement needs a public name rather than a reach into the private primitive."""
    seen = _routing_probe(BS, monkeypatch)
    assert BS.unfiltered_world_bounds(["a", "b"])[2] == pytest.approx(0.5)
    assert seen == {"measured": ["a", "b"]}


def test_the_geometry_signature_filters_when_it_is_given_the_scene(BS, monkeypatch):
    seen = _routing_probe(BS, monkeypatch)
    BS.evaluated_geometry_signature(["a", "b"], scene="SCENE")
    assert seen == {"scene": "SCENE", "measured": ["visible-only"]}


def test_world_bounds_over_frames_always_filters_because_it_holds_the_scene(BS,
                                                                            monkeypatch):
    """It already took `scene` and still read the unfiltered primitive."""
    seen = _routing_probe(BS, monkeypatch)
    monkeypatch.setattr(BS, "set_scene_frame", lambda scene, i: None)
    BS.world_bounds_over_frames("SCENE", ["a", "b"], 2)
    assert seen == {"scene": "SCENE", "measured": ["visible-only"]}


def _functions_calling(source, callee):
    """Every function in `source` whose body calls `callee` by name.

    Derived by AST over the module itself, so a fifth reader of the unfiltered primitive
    joins the population the moment it is written.
    """
    import ast

    found = set()
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for sub in ast.walk(node):
            if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name)
                    and sub.func.id == callee):
                found.add(node.name)
    return found


def test_the_unfiltered_primitive_has_exactly_three_readers_inside_the_module(BS):
    """Census, derived by AST over blender_scene.py.

    Measured on this tree: `_evaluated_world_vertices` is reached from the public filtering
    reader, from the funnel the four measuring entry points share, and from the one
    deliberately naive measurement. Nothing else may read it, and a new reader fails here.
    """
    import inspect

    derived = _functions_calling(inspect.getsource(BS), "_evaluated_world_vertices")
    assert derived == {"evaluated_world_vertices", "_points_to_measure",
                       "unfiltered_world_bounds"}, sorted(derived)


def test_that_census_goes_red_on_a_fourth_reader():
    """Prove it can fail — the mutation adds a member without the property."""
    mutated = (
        "def evaluated_world_vertices(scene, objects):\n"
        "    return _evaluated_world_vertices(render_visible_meshes(scene, objects))\n"
        "\n"
        "def _points_to_measure(objects, scene):\n"
        "    return _evaluated_world_vertices(objects)\n"
        "\n"
        "def unfiltered_world_bounds(objects):\n"
        "    return _evaluated_world_vertices(objects)\n"
        "\n"
        "def new_measurement(objects):\n"
        "    return _evaluated_world_vertices(objects)\n"
    )
    derived = _functions_calling(mutated, "_evaluated_world_vertices")
    assert "new_measurement" in derived
    assert derived != {"evaluated_world_vertices", "_points_to_measure",
                       "unfiltered_world_bounds"}
