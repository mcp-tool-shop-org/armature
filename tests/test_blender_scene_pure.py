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
    with pytest.raises(TypeError):
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
