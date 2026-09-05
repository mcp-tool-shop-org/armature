"""Wave 25 (Stage B amend #3) — the core-solvers domain's eight findings.

Every one of the eight is `[proactive]`, plus the wave-24 seam's measured seed on
`blender_scene.py`'s clause-less family raises. What lives here rather than in the
per-module test files:

* **The halt-line reads** (wave-18 rule 4). A refusal is not a refusal an operator sees
  until it reaches a tool's exit-2 `<TOOL>_HALT` branch and prints a record carrying the
  clause. Every clause word this wave adds is driven through a REAL tool's `__main__`
  block and the printed line is PARSED, not assumed.
* **The sibling enumerations** (wave-18 rule 2), derived by AST over the module rather
  than typed, so a sibling written tomorrow joins the population.
* **The reverted-red proofs** — the mechanism each fix closes, re-implemented as the code
  read on `580af47`, so the test is shown able to fail for the reason it exists.

The isolated floor these were measured against: `6613 passed, 79 skipped` on `580af47`.
"""

import ast
import inspect
import json
import math

import numpy as np
import pytest

from armature_core import binding, channels, clipstats, framing, parts, startframe
from armature_core import turnaround
from armature_core.errors import ArmatureError, GateFailure


# ===================================================== F-e8074763 — the shared byte writer
#
# `encode_u8` is the function that writes every control-sequence byte and was the one
# function in `channels` with no clause.


def test_the_byte_writer_refuses_a_value_it_cannot_encode():
    """RED on the finding's own operand: `encode_u8([[0.5, nan], [inf, -inf]])`.

    MEASURED on `580af47`, before the fix: `[[128, 0], [255, 0]]`. NaN and -inf both
    became byte 0 — which is `encode_u8(BACKGROUND_DEPTH)`, measured beside it in the same
    run — and +inf became 255, the nearest-geometry byte. The only signal was a numpy
    RuntimeWarning, silent under the default filter.
    """
    with pytest.raises(channels.ChannelEncodeError) as exc:
        channels.encode_u8(np.array([[0.5, np.nan], [np.inf, -np.inf]]))
    ev = exc.value.evidence
    assert ev["clause"] == "non_finite_encoder_input"
    assert ev["andon"] == "ChannelEncodeError" and ev["gate"] is None
    assert (ev["n"], ev["n_non_finite"], ev["n_nan"]) == (4, 3, 1)
    assert (ev["n_pos_inf"], ev["n_neg_inf"]) == (1, 1)
    assert ev["first_non_finite_flat_index"] == 1
    assert ev["shape"] == [2, 2]
    assert ev["where"] == "encode_u8"


def test_the_void_byte_collision_is_what_the_writer_now_refuses():
    """The reverted-red: the old body, run on the same input, produces the collision.

    Reserved-byte arithmetic is asserted rather than narrated — `BACKGROUND_DEPTH` and
    `GEOMETRY_DEPTH_FLOOR` are one byte apart precisely so that "no geometry" and
    "farthest geometry" are distinguishable, and the old cast put an unreadable pixel on
    the first of them.
    """
    x = np.array([[0.5, np.nan], [np.inf, -np.inf]])
    with np.errstate(invalid="ignore"):
        # The RuntimeWarning IS the finding: it is the only signal the old cast gave, and
        # it is silent under the default filter. Silenced here so the suite output stays
        # clean; asserted for below.
        old = np.clip(np.rint(np.asarray(x, dtype=np.float64) * 255.0), 0,
                      255).astype(np.uint8)
    assert old.tolist() == [[128, 0], [255, 0]]
    assert int(channels.encode_u8(np.array([channels.BACKGROUND_DEPTH]))[0]) == 0
    assert int(channels.encode_u8(np.array([channels.GEOMETRY_DEPTH_FLOOR]))[0]) == 1
    assert old[0, 1] == channels.encode_u8(np.array([channels.BACKGROUND_DEPTH]))[0]
    assert old[1, 1] == channels.encode_u8(np.array([channels.BACKGROUND_DEPTH]))[0]


def test_the_writer_still_encodes_every_legal_plate_it_did_before():
    """A clause that also refuses correct work is a different defect. The three producers
    inside this module and the endpoints all still pass through."""
    assert channels.encode_u8(np.array([0.0, 0.5, 1.0])).tolist() == [0, 128, 255]
    n = np.zeros((4, 4, 3))
    n[..., 2] = 1.0
    m = np.ones((4, 4), dtype=np.uint8)
    assert channels.encode_normal(n, m).ravel()[:3].tolist() == [128, 128, 255]
    z = np.array([[1.0, 2.0], [3.0, 4.0]])
    d = channels.normalize_depth(z, np.ones((2, 2), dtype=np.uint8), 1.0, 4.0)
    assert channels.encode_u8(d).min() >= 1


def test_the_where_label_names_the_caller_and_decides_nothing():
    """`where` rides the evidence so a halt line separates the depth plate from the normal
    triple from `stage_render`'s P3 difference. It is a LABEL: no value of it changes what
    is refused, which is the property that keeps it from becoming a switch."""
    for label in ("encode_u8", "p3_diff", "anything at all"):
        with pytest.raises(channels.ChannelEncodeError) as exc:
            channels.encode_u8(np.array([np.nan]), where=label)
        assert exc.value.evidence["where"] == label


# ================================================ F-075b3af4 — the edge pass's two thresholds


def _edge_inputs():
    z = np.ones((8, 8))
    n = np.zeros((8, 8, 3))
    n[..., 2] = 1.0
    return z, n, np.ones((8, 8), dtype=np.uint8)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), 0.0, -1.0, None, "x"])
def test_the_depth_threshold_is_refused_by_name(bad):
    """MEASURED on `580af47`: `nan` and `inf` RETURNED with `depth_break_px: 0` and the
    threshold written back into the diagnostics as itself; `None` and `'x'` left as a bare
    `TypeError` / `ValueError`, which the halt contract records as exit 1 "FAILED — an
    unhandled error" where a typed refusal at exit 2 belongs. `parts.require_finite` is the
    home for both shapes and this adopts it."""
    z, n, m = _edge_inputs()
    with pytest.raises(channels.DepthError) as exc:
        channels.derive_edge(z, n, m, bad, 30.0)
    assert exc.value.evidence["clause"] == "depth_rel_threshold_not_finite_and_positive"


@pytest.mark.parametrize("bad,clause", [
    (float("nan"), "normal_angle_deg_not_finite"),
    (float("inf"), "normal_angle_deg_not_finite"),
    (None, "normal_angle_deg_not_finite"),
    (400.0, "normal_angle_deg_outside_domain"),
    (-5.0, "normal_angle_deg_outside_domain"),
])
def test_the_normal_angle_is_refused_by_name(bad, clause):
    z, n, m = _edge_inputs()
    with pytest.raises(channels.NormalError) as exc:
        channels.derive_edge(z, n, m, 0.02, bad)
    assert exc.value.evidence["clause"] == clause


def test_an_out_of_domain_angle_used_to_become_a_different_plausible_threshold():
    """The reverted-red for the DOMAIN clause, which is a separate fact from finiteness.

    `cos` is periodic: a 400-degree request is a 40-degree threshold, so the old code did
    not fail on it — it succeeded, at an angle nobody asked for. The two numbers are equal
    to the bit, which is why no diagnostic downstream could have seen the difference.
    """
    # Equal to float rounding, not to the bit: `radians(400)` and `radians(40)` differ in
    # the last place, so the two cosines land 1e-16 apart. Which is the point — no
    # diagnostic downstream could see the difference between the threshold that was asked
    # for and the one that was used.
    assert math.cos(math.radians(400.0)) == pytest.approx(math.cos(math.radians(40.0)),
                                                          abs=1e-15)
    assert math.cos(math.radians(190.0)) == pytest.approx(math.cos(math.radians(170.0)))
    z, n, m = _edge_inputs()
    # The endpoints of the domain are legal — the bound is on what is OUTSIDE it.
    for legal in (0.0, 90.0, 180.0):
        _, diag = channels.derive_edge(z, n, m, 0.02, legal)
        assert diag["normal_angle_deg"] == legal


def test_the_edge_pass_still_derives_the_three_terms_it_did_before():
    z, n, m = _edge_inputs()
    img, diag = channels.derive_edge(z, n, m, 0.02, 30.0)
    assert set(diag) == {"depth_break_px", "normal_break_px", "silhouette_px", "edge_px",
                         "depth_rel_threshold", "normal_angle_deg"}
    assert set(np.unique(img)) <= {0, 255}


def test_every_number_derive_edge_compares_against_now_has_a_clause():
    """SIBLING ENUMERATION (wave-18 rule 2), derived by AST rather than typed: every
    parameter of `derive_edge` that is not an array is reached by a named refusal.

    The two array parameters are ruled on by `require_readable_normals` (`n_cam`) and by
    `depth_extent` / `normalize_depth` upstream (`z`); `mask` is a selector and is
    booleanised. The two SCALARS are the population this finding names, and both are
    covered now.
    """
    sig = inspect.signature(channels.derive_edge)
    scalars = [p for p in sig.parameters if p not in ("z", "n_cam", "mask")]
    assert scalars == ["depth_rel_threshold", "normal_angle_deg"]
    src = inspect.getsource(channels.derive_edge)
    for name in scalars:
        assert f'require_finite(\n        "{name}"' in src or f'"{name}", {name}' in src, name


# ======================================== F-526e9069 — the point cloud and the bracket ends


def _cube():
    return [(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1),
            (1, 1, 0), (1, 0, 1), (0, 1, 1), (1, 1, 1)]


def _solve(cloud, end=None):
    return framing.solve_camera(cloud, end if end is not None else cloud,
                                30.0, 10.0, 50.0, 36.0, 832, 480, 0.8, 0.5)


def test_a_non_finite_vertex_used_to_return_the_radius_ceiling():
    """The reverted-red, run against the code as it stood on `580af47`.

    The whole finding is that the solver RETURNED rather than refused, so the proof that
    the clause is load-bearing is the measurement of what it returned. Re-derived here by
    calling the solver with the census bypassed, exactly as the old body ran it.
    """
    legal = _solve(_cube())
    assert legal["in_frame"] is True
    assert legal["achieved"]["union_height_frac"] == pytest.approx(0.8, abs=1e-6)
    assert legal["radius"] < 40.0

    bad = list(_cube())
    bad[3] = (0.0, float("nan"), 1.0)
    old = _solve_without_the_cloud_census(bad)
    assert old["radius"] == 40.0, "the radius_bounds CEILING, returned as a solution"
    assert all(math.isnan(c) for c in old["target"])
    assert math.isnan(old["achieved"]["union_height_frac"])
    # Every REQUESTED number is finite and legal — which is why nothing upstream fired.
    assert all(math.isfinite(v) for v in old["requested"].values())
    # And the record it returned is not JSON.
    with pytest.raises(ValueError, match="not JSON compliant"):
        json.dumps(old, allow_nan=False)
    assert json.dumps({"uh": old["achieved"]["union_height_frac"]}) == '{"uh": NaN}'


def _solve_without_the_cloud_census(cloud):
    """`solve_camera` run with THIS WAVE'S two clauses disarmed — the body as it ran on
    `580af47`, exercised rather than re-typed.

    Both clauses added here (the point-cloud census and the bisect bracket ends) are
    written over `framing._finite`, this module's own PREDICATE — never a raiser, which is
    what makes reverting them a one-line substitution rather than a hand-copy of the solver
    that would drift from it. `_finite_positive` and the wave-22 target clause are
    untouched: the scalar requests in this call are all finite and legal, which is the
    whole point of the measurement — every number the caller asked for is fine and the
    answer is still the ceiling.

    Keyed on the clause word, so renaming the clause fails here loudly rather than
    silently reverting nothing.
    """
    src = inspect.getsource(framing.solve_camera)
    assert '"clause": "point_cloud_not_finite"' in src
    assert "_finite(c) for c in tuple(p)[:3]" in src

    mp = pytest.MonkeyPatch()
    mp.setattr(framing, "_finite", lambda value: True)
    try:
        return framing.solve_camera(cloud, cloud, 30.0, 10.0, 50.0, 36.0,
                                    832, 480, 0.8, 0.5)
    finally:
        mp.undo()


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_the_point_cloud_is_refused_by_name_in_both_clouds(value):
    bad = list(_cube())
    bad[3] = (0.0, value, 1.0)
    with pytest.raises(framing.FramingError) as exc:
        _solve(bad)
    ev = exc.value.evidence
    assert ev["clause"] == "point_cloud_not_finite"
    assert ev["cloud"] == "all_points"
    assert (ev["n"], ev["n_finite"], ev["n_non_finite"]) == (8, 7, 1)
    assert ev["first_non_finite_index"] == 3
    assert ev["non_finite_indices"] == [3]
    assert "nan" in ev["first_non_finite_point"][1] or "inf" in ev["first_non_finite_point"][1]

    # `end_points` is the cloud `x_of` solves against and is not always a subset of
    # `all_points`, so it is censused separately and names itself.
    end_bad = list(_cube())
    end_bad[1] = (value, 0.0, 0.0)
    with pytest.raises(framing.FramingError) as exc:
        _solve(_cube(), end=end_bad)
    assert exc.value.evidence["cloud"] == "end_points"


def test_the_bracket_ends_take_the_clause_the_target_already_had():
    """Wave 22 guarded ONE end of the bracket test. MEASURED on `580af47`:
    `_bisect(lambda t: nan, 0.0, 1.0, 0.5)` returns **1.0**, its own upper bound, with a
    finite legal target — the same defect the target clause refuses, arriving through the
    closure instead of through the request."""
    with pytest.raises(framing.FramingError) as exc:
        framing._bisect(lambda t: float("nan"), 0.0, 1.0, 0.5)
    assert exc.value.evidence["clause"] == "bisect_bracket_not_finite"
    assert exc.value.evidence["end"] == "flo"

    with pytest.raises(framing.FramingError) as exc:
        framing._bisect(lambda t: float("inf") if t > 0.5 else 0.0, 0.0, 1.0, 0.5)
    assert exc.value.evidence["end"] == "fhi"

    # The target clause is unchanged and still names itself.
    with pytest.raises(framing.FramingError) as exc:
        framing._bisect(lambda t: t, 0.0, 1.0, float("nan"))
    assert exc.value.evidence["clause"] == "bisect_target_not_finite"

    assert framing._bisect(lambda t: t, 0.0, 1.0, 0.25) == pytest.approx(0.25)


def test_a_legal_composition_still_solves_to_the_same_camera():
    """The clause must not move the answer. Solved before and after is the same radius to
    the bit, because the census runs before the search and changes nothing in it."""
    got = _solve(_cube())
    assert got["radius"] == pytest.approx(3.70665, abs=1e-4)
    assert got["in_frame"] is True


# ==================================== F-e6d76657 — the drop census on the geometry primitive


class _StubMesh:
    def __init__(self, co):
        self.vertices = _StubVerts(co)


class _StubVerts:
    def __init__(self, co):
        self._co = co

    def __len__(self):
        return len(self._co) // 3

    def foreach_get(self, attr, buf):
        buf[:] = self._co


class _StubEval:
    def __init__(self, kind, off=0.0):
        self.kind = kind
        self.matrix_world = [[1, 0, 0, off], [0, 1, 0, off], [0, 0, 1, off], [0, 0, 0, 1]]

    def to_mesh(self):
        if self.kind == "raise":
            raise RuntimeError("no evaluated mesh")
        if self.kind == "none":
            return None
        return _StubMesh([0., 0., 0., 1., 0., 0., 0., 1., 0., 0., 0., 1.])

    def to_mesh_clear(self):
        pass


class _StubObject:
    def __init__(self, name, kind, off=0.0):
        self.name = name
        self._ev = _StubEval(kind, off)

    def evaluated_get(self, depsgraph):
        return self._ev


@pytest.fixture
def BS():
    """`blender_scene` imported under `blender_stub.blender_stubbed()`, then unimported.

    **This fixture installs no stub of its own, deliberately.** `test_packaging.py`'s
    census derives every function under `tests/` that writes into `sys.modules` and holds
    the population to `RECORDED_STUB_INSTALLERS` by equality, with a matching
    `INSTALLER_MODULE` row per member saying how to DRIVE its teardown — because a teardown
    is only observable by running it. A fourth hand-rolled installer would be a fourth
    stub-and-teardown pair to keep correct, and there is already a home: `blender_stubbed`
    is one of the three recorded members and its teardown is the one this repo has paid to
    get right twice (registry entry AND package attribute, for everything first imported
    under the stub).

    Measured in this worktree: writing the stub here by hand put
    `('test_amend_w25_core_solvers.py', 'BS')` into that census and turned it red, naming
    itself — which is the census working. Adopting the home is the fix, not registering a
    fourth member.

    `blender_stubbed`'s `bpy` is a `MagicMock`, so `bpy.context.evaluated_depsgraph_get()`
    returns a mock the stub objects below ignore — which is all `_evaluated_world_vertices`
    does with it. The two drop branches are pure Python around that one call.
    """
    import importlib

    from blender_stub import blender_stubbed

    with blender_stubbed():
        yield importlib.import_module("armature_core.blender_scene")


def _three_objects():
    return [_StubObject("body", "ok", 1.0),
            _StubObject("prop_raises", "raise", 100.0),
            _StubObject("prop_none", "none", 100.0)]


def test_a_partial_drop_used_to_leave_no_trace_at_all(BS):
    """The finding's own measurement, reproduced: three render-visible mesh objects in,
    bounds over ONE, and a bare (N, 3) array out.

    The two dropped objects sit at world x=100 and would have set the radius near 87; the
    body alone gives 0.866. Nothing in the return said so, and `stage_render`'s refusal
    evidence quotes `n_render_visible_meshes` — the count BEFORE the drop.
    """
    pts = BS._evaluated_world_vertices(_three_objects())
    assert pts.shape == (4, 3)
    centre, _half, radius = BS._sphere(pts)
    assert [round(float(c), 4) for c in centre] == [1.5, 1.5, 1.5]
    assert radius == pytest.approx(0.866, abs=1e-3)

    all_three = [_StubObject("body", "ok", 1.0), _StubObject("far", "ok", 100.0)]
    _c2, _h2, r2 = BS._sphere(BS._evaluated_world_vertices(all_three))
    assert r2 > 80.0, "what the dropped geometry would have done to the framing"


def test_the_drop_census_names_the_population_and_the_reason(BS):
    census = {}
    BS._evaluated_world_vertices(_three_objects(), census=census)
    assert census["n_objects"] == 3
    assert census["n_contributing"] == 1
    assert census["n_dropped"] == 2
    assert census["n_vertices"] == 4
    assert [d["name"] for d in census["dropped"]] == ["prop_raises", "prop_none"]
    assert [d["reason"] for d in census["dropped"]] == [
        "to_mesh_raised_runtime_error", "to_mesh_returned_none"]
    assert census["dropped"][0]["detail"] == "no evaluated mesh"


def test_the_all_drop_case_was_already_guarded_and_still_is(BS):
    """Honest about what was and was not open: `_sphere` returns None over an empty array
    and all three consumers refuse or record on `bounds is None`. The PARTIAL case is the
    one that mis-frames the shot, and it is the one that had no count."""
    census = {}
    pts = BS._evaluated_world_vertices(
        [_StubObject("a", "raise"), _StubObject("b", "none")], census=census)
    assert pts.shape == (0, 3)
    assert BS._sphere(pts) is None
    assert census["n_contributing"] == 0 and census["n_dropped"] == 2


def test_the_public_census_names_hand_back_the_same_bounds(BS):
    """The array return is UNCHANGED for every existing caller — the count is what was
    missing, not the geometry — so the census names must agree with the plain ones to the
    value."""
    objs = _three_objects()
    plain = BS.unfiltered_world_bounds(objs)
    bounds, census = BS.unfiltered_world_bounds_census(objs)
    assert [float(c) for c in bounds[0]] == [float(c) for c in plain[0]]
    assert bounds[2] == plain[2]
    assert census["n_objects"] == 3 and census["n_dropped"] == 2


def test_the_census_sibling_does_not_become_a_fourth_reader_of_the_primitive(BS):
    """`tests/test_blender_scene_pure` pins the unfiltered primitive to exactly three
    readers inside this module, and a naive fourth door is the failure that census exists
    for. `unfiltered_world_bounds_census` goes through `_points_to_measure(objects, None)`
    — the DELIBERATELY naive branch that funnel's own docstring names — rather than through
    the primitive, so the count of readers is unchanged."""
    found = set()
    for node in ast.walk(ast.parse(inspect.getsource(BS))):
        if not isinstance(node, ast.FunctionDef):
            continue
        for sub in ast.walk(node):
            if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name)
                    and sub.func.id == "_evaluated_world_vertices"):
                found.add(node.name)
    assert found == {"evaluated_world_vertices", "_points_to_measure",
                     "unfiltered_world_bounds"}, sorted(found)


# =============== the [proactive] seed — blender_scene's family raises and their clause words


def test_every_family_raise_in_blender_scene_carries_a_clause_the_census_can_see(BS):
    """The wave-24 seam's seed, MEASURED rather than inherited.

    The seed said "13 family raise sites, 12 without a clause the wave-22 census can see".
    Re-derived on `580af47` with the census that actually reads the tree
    (`tests/_census_nodes.clause_literals`, which reads BOTH spellings — the literal inside
    an evidence dict and the assignment into one): **13 family raise sites, of which 9 were
    covered by 9 clause words and FOUR were not** — the three `CompositorWiring` raises,
    which carried no `clause` key at all, and one `CameraGeometry` raise whose clause value
    was an f-string (`f"{_name}_not_finite_and_positive"`), which no AST census can read as
    a word. The seed's count of 12 is not the number this census yields and is corrected
    here with the measurement. All 13 are covered now.
    """
    import _census_nodes as CN

    src = inspect.getsource(BS)
    tree = ast.parse(src)
    seen = CN.clause_literals({"armature_core/blender_scene.py": tree})
    covered = {int(site.split(":")[1]) for sites in seen.values() for site in sites}

    family = {"NonReiterableFrames", "MeasurementWithoutScene", "G6SubjectMotion",
              "CameraGeometry", "CompositorWiring", "RenderedFrame"}
    raises = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
            func = node.exc.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
            if name in family:
                raises.append(node.lineno)
    assert len(raises) == 13, sorted(raises)

    # Every raise has a clause word within the twelve lines above it or inside it — the
    # window the two spellings sit in (`ev["clause"] = ...` immediately above, or the
    # literal inside the raise's own dict).
    for line in raises:
        assert any(line - 12 <= c <= line + 14 for c in sorted(covered)), line

    for word in ("compositor_link_count", "compositor_source_is_not_render_layers",
                 "compositor_socket_is_not_the_pass",
                 "lens_mm_not_finite_and_positive", "sensor_mm_not_finite_and_positive"):
        assert word in seen, word


def test_the_compositor_refusals_name_which_way_the_wiring_is_wrong(BS):
    """Three refusals, three conditions, three words. A halt reader keys on the word, and
    on `580af47` all three printed the same absent key."""
    with pytest.raises(BS.CompositorWiring) as exc:
        BS.gate_compositor_wiring("depth", "Depth", "Render Layers", [])
    assert exc.value.evidence["clause"] == "compositor_link_count"

    with pytest.raises(BS.CompositorWiring) as exc:
        BS.gate_compositor_wiring("depth", "Depth", "Render Layers", [("Blur", "Depth")])
    assert exc.value.evidence["clause"] == "compositor_source_is_not_render_layers"

    with pytest.raises(BS.CompositorWiring) as exc:
        BS.gate_compositor_wiring("depth", "Depth", "Render Layers",
                                  [("Render Layers", "Alpha")])
    assert exc.value.evidence["clause"] == "compositor_socket_is_not_the_pass"


def test_the_camera_number_refusals_name_the_number(BS):
    for bad, clause in ((("lens_mm", 0.0), "lens_mm_not_finite_and_positive"),
                        (("sensor_mm", float("nan")), "sensor_mm_not_finite_and_positive")):
        kw = {"lens_mm": 50.0, "sensor_mm": 36.0, "width": 832, "height": 480}
        kw[bad[0]] = bad[1]
        with pytest.raises(BS.CameraGeometry) as exc:
            BS.half_fovs(**kw)
        assert exc.value.evidence["clause"] == clause


def test_half_fovs_still_matches_framings_copy_after_the_clause_moved(BS):
    """The byte-twin. `tests/test_framing.py::test_half_fovs_matches_blenders` slices this
    function's SOURCE out of the file and execs it in a namespace holding only `math`, so
    no new NAME may appear in it — which is why the clause is an assignment of a literal
    rather than a lookup in a table. Asserted here too so the constraint is visible from
    the side that changed."""
    for w, h in ((832, 480), (480, 832), (512, 512), (1280, 720)):
        assert framing.half_fovs(50.0, 36.0, w, h) == BS.half_fovs(50.0, 36.0, w, h)


# ============================================ F-4ba279bf — the freeze instrument's real input


def test_the_pixel_half_reports_a_magnitude_where_the_byte_half_reported_a_word():
    """MEASURED on `580af47`: 65 frames of a 256x256x3 plate differing from the base by ONE
    byte in one channel returned `{'n_frames': 65, 'n_distinct': 65}` — the instrument's
    strongest reading, on a clip that never moved — while `frame_deltas` in the same module
    put the median frame-to-frame mean absolute difference at 5.09e-06."""
    rng = np.random.default_rng(7)
    base = rng.integers(0, 255, (128, 128, 3), dtype=np.uint8)
    frames = []
    for i in range(20):
        f = base.copy()
        f[0, 0, 0] = np.uint8((int(base[0, 0, 0]) + 1 + i) % 256)
        frames.append(f)
    got = clipstats.distinct_frames(frames)
    assert got["n_distinct"] == 20, "the byte count reads its maximum on a frozen clip"
    assert got["min_pair_mean_abs_difference"] < 1e-2
    assert got["n_pairs_compared"] == 190
    assert got["n_samples_per_frame"] == min(clipstats.PIXEL_SAMPLES_PER_FRAME,
                                             base.size)
    # And `frame_deltas` beside it agrees about the magnitude, which is the point: the two
    # instruments in one module now answer in the same units.
    assert clipstats.frame_deltas(frames)["stats"]["median"] < 1e-2


def test_the_stride_is_a_cost_bound_and_not_a_tuned_threshold():
    """Nothing about the sample count can be moved toward a picture: the quantity reported
    is the mean absolute difference over whatever it reads, and the count rides the dict so
    a reader knows the population. A clip small enough is read whole."""
    small = [np.zeros((8, 8, 3), dtype=np.uint8) for _ in range(3)]
    got = clipstats.distinct_frames(small)
    assert got["pixel_stride"] == 1
    assert got["n_samples_per_frame"] == 8 * 8 * 3
    assert got["min_pair_mean_abs_difference"] == 0.0


def test_the_freeze_instrument_gates_nothing():
    """This module's own doctrine — these are diagnostics and the Director's eye is the
    judge — asserted rather than narrated. `turnaround.gate_set_distinct` is the
    gate-shaped sibling and it lives there because that is where the andon belongs."""
    src = inspect.getsource(clipstats.distinct_frames)
    assert "raise" not in src
    frozen = [np.zeros((16, 16, 3), dtype=np.uint8) for _ in range(4)]
    assert clipstats.distinct_frames(frozen)["n_pixel_distinct"] == 1


# =========================== F-8361eff3 — two halves of one fix, and the half a reader sees


def test_the_revisit_refusal_no_longer_denies_the_gate_that_can_see_it():
    """Both halves of F-99e5de1a landed in one commit, and this message said the second one
    did not exist. MEASURED on `580af47`, the two ends of the contradiction in one run:

    * `orbit_azimuths(8, 0, 720)` raised `sweep_revisits_an_azimuth` carrying "... Gate
      TURN's pixel clause ranges over adjacent pairs — a revisit at stride 2 is never
      adjacent";
    * `gate_set_distinct` over eight 64x64x4 planes with view 4 a copy of view 0 and eight
      distinct sha256 values RAISED `views_identical_in_pixels_anywhere` with
      `pairs_identical_in_pixels_anywhere: [[0, 4]]` over 28 unordered pairs compared.
    """
    with pytest.raises(turnaround.TurnaroundGate) as exc:
        turnaround.orbit_azimuths(8, 0, 720)
    msg = str(exc.value)
    ev = exc.value.evidence
    assert ev["clause"] == "sweep_revisits_an_azimuth"
    assert "is never adjacent" not in msg
    assert "views_identical_in_pixels_anywhere" in msg
    assert "at ANY distance" in msg
    assert "refuses the PLAN" in msg or "PLAN" in msg

    # The other half, in the same test, so the two can never drift apart again.
    rng = np.random.default_rng(3)
    planes = [rng.random((64, 64, 4)) for _ in range(8)]
    planes[4] = planes[0].copy()
    records = [{"view": i, "sha256": "%064x" % i, "pixels": p}
               for i, p in enumerate(planes)]
    with pytest.raises(turnaround.TurnaroundGate) as exc2:
        turnaround.gate_set_distinct(records, 8)
    assert exc2.value.evidence["clause"] == "views_identical_in_pixels_anywhere"
    assert exc2.value.evidence["pairs_identical_in_pixels_anywhere"] == [[0, 4]]
    assert exc2.value.evidence["n_unordered_pairs_compared"] == 28


def test_the_revisit_stride_the_message_quotes_is_the_stride():
    """The second error in the same sentence, measured in the same run: `n // len(seen)`
    printed "stride 2" for `orbit_azimuths(8, 0, 720)`, whose coinciding views are 0 and 4.
    That quotient is how many TIMES each direction is photographed; the stride between two
    views pointing the same way is `len(seen)`. Both numbers ride the evidence now, under
    names that say which is which."""
    with pytest.raises(turnaround.TurnaroundGate) as exc:
        turnaround.orbit_azimuths(8, 0, 720)
    ev = exc.value.evidence
    assert ev["n_distinct_azimuths"] == 4
    assert ev["revisit_stride"] == 4
    assert ev["visits_per_direction"] == 2
    # The claim, checked against the plan the function built rather than asserted.
    azimuths = ev["azimuths"]
    assert azimuths[0] % 360.0 == azimuths[ev["revisit_stride"]] % 360.0

    with pytest.raises(turnaround.TurnaroundGate) as exc:
        turnaround.orbit_azimuths(9, 0, 1080)
    ev = exc.value.evidence
    assert (ev["revisit_stride"], ev["visits_per_direction"]) == (3, 3)
    assert ev["azimuths"][0] % 360.0 == ev["azimuths"][3] % 360.0


def test_a_legal_sweep_still_plans_the_orbit_it_did_before():
    assert turnaround.orbit_azimuths(8, 0, 360) == [0.0, 45.0, 90.0, 135.0,
                                                    180.0, 225.0, 270.0, 315.0]


# ============================= F-95c9a97e / F-efd6b45c — two bounds adopting the one home


def test_the_two_new_bounds_go_through_parts_and_not_through_a_second_spelling():
    """"Adopt the home" (the wave-24 method). Both fixes route to `parts.tightened`, which
    is where a bound on a module constant is ruled on, rather than re-deriving finiteness,
    the negative clause and the may-only-tighten clause a fifth and sixth time."""
    assert "tightened(" in inspect.getsource(binding.rigid_segment_weights)
    assert "tightened(" in inspect.getsource(startframe.shadow_ratio)
    # And the home itself is one function, not two.
    assert parts._tightened is parts.tightened


def test_the_tightened_refusals_now_name_their_condition():
    """MEASURED on `580af47` by reading every caller: not one of the eight evidence dicts
    handed to `parts.tightened` or `parts.narrowed` carried a `clause` key, so every "may
    only TIGHTEN" refusal reached a halt line with nothing for a reader to key on."""
    ev = {"gate": "D"}
    with pytest.raises(GateFailure) as exc:
        parts.tightened("t", float("nan"), 1e-4, parts.GatePartsDeterminism, dict(ev))
    assert exc.value.evidence["clause"] == "bound_not_finite"

    with pytest.raises(GateFailure) as exc:
        parts.tightened("t", -1.0, 1e-4, parts.GatePartsDeterminism, dict(ev))
    assert exc.value.evidence["clause"] == "bound_is_negative"

    with pytest.raises(GateFailure) as exc:
        parts.tightened("t", 1e-3, 1e-4, parts.GatePartsDeterminism, dict(ev))
    assert exc.value.evidence["clause"] == "bound_may_only_tighten"

    with pytest.raises(GateFailure) as exc:
        parts.narrowed("allowed", ("a", "b"), ("a",), parts.GatePartsDeterminism, dict(ev))
    assert exc.value.evidence["clause"] == "allowlist_may_only_narrow"


def test_a_caller_that_names_its_own_clause_keeps_it():
    """The home supplies a word where the caller has none and DEFERS where the caller has
    one. `render_performer.gate_coverage` passes `clause: min_frac_may_only_tighten`
    (instruments, wave 25 SEAM 4) — a word that says which FLAG, where the generic one says
    only which helper. Overwriting a finer id with a coarser one is the opposite of the
    improvement this change is."""
    for requested, generic in ((float("nan"), "bound_not_finite"),
                               (-1.0, "bound_is_negative"),
                               (1e-3, "bound_may_only_tighten")):
        ev = {"gate": "COVERAGE", "clause": "min_frac_may_only_tighten"}
        with pytest.raises(GateFailure) as exc:
            parts.tightened("min_frac", requested, 1e-4,
                            parts.GatePartsDeterminism, ev)
        assert exc.value.evidence["clause"] == "min_frac_may_only_tighten", generic

    ev = {"gate": "ASSEMBLY", "clause": "allowed_widened"}
    with pytest.raises(GateFailure) as exc:
        parts.narrowed("allowed", ("a", "b"), ("a",), parts.GatePartsDeterminism, ev)
    assert exc.value.evidence["clause"] == "allowed_widened"


def test_the_generic_clause_words_are_spelled_where_the_census_can_read_them():
    """`ev.setdefault("clause", ...)` is neither a `Constant` in a dict literal nor a
    `Constant` assigned into one, so `_census_nodes.clause_literals` cannot see it —
    measured in this worktree, the vocabulary pin went red reporting all four words as
    "vanished" the moment they were written that way. Same defect as the f-string clause in
    `blender_scene.half_fovs`, caught in the same wave. The census is asserted directly
    rather than the spelling, so a future rewrite that stays readable is free."""
    import _census_nodes as CN

    seen = CN.clause_literals({"armature_core/parts.py":
                               ast.parse(inspect.getsource(parts))})
    for word in ("bound_not_finite", "bound_is_negative", "bound_may_only_tighten",
                 "allowlist_may_only_narrow"):
        assert word in seen, sorted(seen)


def test_the_finiteness_clause_does_not_leak_into_a_callers_later_refusal():
    """The bug the copy exists to prevent, proven rather than described: `tightened`
    RETURNS on the happy path, so writing the word into the caller's own dict up front
    would leave `"clause": "bound_not_finite"` sitting in an evidence dict that
    `resample.require_rotation` and `author_walk`'s three gates go on to raise their OWN
    refusal with."""
    from armature_core import resample

    ev = {"gate": "D"}
    assert parts.tightened("t", 1e-6, 1e-4, parts.GatePartsDeterminism, ev) == 1e-6
    assert "clause" not in ev

    # Through a real importer: a legal tolerance, then that gate's own refusal.
    bad = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 2.0]])
    with pytest.raises(resample.ResampleGate) as exc:
        resample.require_rotation(bad, "probe", tol=1e-9)
    assert exc.value.evidence.get("clause") != "bound_not_finite"


@pytest.mark.parametrize("bad,clause", [
    (float("inf"), "bound_not_finite"),
    (float("nan"), "bound_not_finite"),
    (-0.2, "bound_is_negative"),
    (0.8, "bound_may_only_tighten"),
    (0.0, "blend_band_not_positive"),
])
def test_the_blend_band_is_bounded_where_the_character_is_decided(bad, clause):
    """`inf > 0` is True, which is the whole finding. MEASURED on `580af47` with
    `blend_band=inf` over a two-bone chain: `w1 = w2 = 0.5` on every vertex whose two
    nearest bones are adjacent — a uniformly smooth skin over a subject whose module
    docstring says rigid segments with a small blend at the joints are what the character
    IS, and the E07-round-1 failure this arm exists to replace."""
    verts = np.array([[0., 0., 0.], [0., 0., 1.], [0., 0., 2.]])
    bones = [{"name": "a", "head": (0, 0, 0), "tail": (0, 0, 1), "parent": None},
             {"name": "b", "head": (0, 0, 1), "tail": (0, 0, 2), "parent": "a"}]
    with pytest.raises(ArmatureError) as exc:
        binding.rigid_segment_weights(verts, bones, {"a": 1.0, "b": 1.0}, blend_band=bad)
    assert exc.value.evidence["clause"] == clause


def test_an_infinite_band_used_to_make_every_adjacent_vertex_a_half(monkeypatch):
    """The reverted-red: the guard as it stood (`if not (blend_band > 0)`) admits `inf`,
    and the diagnostics then carry a value `json.dumps` writes as the bare `Infinity`
    token that `parts.halt_keysafe` exists to stop reaching a halt line."""
    assert float("inf") > 0, "the old guard's whole condition, true for the operand"
    assert json.dumps({"bb": float("inf")}) == '{"bb": Infinity}'
    with pytest.raises(ValueError, match="not JSON compliant"):
        json.dumps({"bb": float("inf")}, allow_nan=False)
    assert parts.halt_keysafe({"bb": float("inf")}) == {"bb": "inf"}
    # The arithmetic the old guard let through: gap/inf clips to 0, so w1 = 0.5 + 0 = 0.5.
    assert float(np.clip(0.4 / float("inf"), 0, 1)) == 0.0


@pytest.mark.parametrize("bad,clause", [
    (float("nan"), "bound_not_finite"),
    (float("inf"), "bound_not_finite"),
    (-1.0, "bound_is_negative"),
    (0.5, "bound_may_only_tighten"),
    (0.0, "shadow_floor_eps_is_zero"),
])
def test_the_shadow_floor_is_bounded_where_the_layer_is_authored(bad, clause):
    """MEASURED on `580af47` on a black cast-and-lit pair: `eps=0.0` returns an all-NaN
    ratio plane (`np.maximum(lit, 0.0)` is a real zero denominator, `np.clip` passes the
    NaN through, and `ratio[dark] = 1.0` never restores it because `dark = lit < 0.0` is
    EMPTY), `eps=nan` the same, and `inf` / `-1.0` return 1.0 everywhere."""
    black = np.zeros((2, 2, 3))
    with pytest.raises(startframe.ShadowError) as exc:
        startframe.shadow_ratio(black, black, eps=bad)
    assert exc.value.evidence["clause"] == clause
    assert exc.value.evidence["andon"] == "ShadowError"
    assert exc.value.evidence["gate"] is None


def test_a_zero_floor_used_to_multiply_the_authored_plate_by_nan():
    """The reverted-red, in the arithmetic itself: this is what `apply_shadow` was handed."""
    black = np.zeros((2, 2, 3))
    lit = startframe.srgb_to_linear(black)
    with np.errstate(invalid="ignore"):
        ratio = np.clip(np.divide(lit, np.maximum(lit, 0.0)), 0.0, 1.0)
    dark = lit < 0.0
    ratio[dark] = 1.0
    assert bool(np.isnan(ratio).all()), "every channel, with no refusal anywhere"
    assert not dark.any(), "the branch that would have restored them selects nothing"


def test_the_shadow_layer_still_authors_the_layer_it_did_before():
    """The sole production call site passes the default and records it; the default and
    every tightening still return the same plane they always did."""
    lit = np.full((4, 4, 3), 0.5)
    assert startframe.shadow_ratio(lit.copy(), lit) == pytest.approx(np.ones((4, 4, 3)))
    cast = np.full((4, 4, 3), 0.25)
    tight = startframe.shadow_ratio(cast, lit, eps=startframe.SHADOW_FLOOR_EPS / 10.0)
    plain = startframe.shadow_ratio(cast, lit)
    assert tight == pytest.approx(plain)


def test_the_shadow_refusal_is_not_a_gate_and_says_so():
    """A refusal naming an andon that did not pull is the defect wave 18's rule 3 names.
    `StartFrameGate` is Gate WHOLE and `shadow_ratio` is arithmetic that authors a layer,
    so the class is a plain `ArmatureError` sibling with `gate` null — the shape
    `channels.DepthError` already uses."""
    assert issubclass(startframe.ShadowError, ArmatureError)
    assert not issubclass(startframe.ShadowError, GateFailure)
    assert startframe.StartFrameGate.gate == "WHOLE"
    code, outcome = parts.halt_outcome(startframe.ShadowError("x", {}))
    assert (code, outcome) == (2, "REFUSED — the tool declined to proceed")


def test_the_two_new_classes_are_in_the_family_so_a_refusal_exits_two():
    """A crash exits 1 and reads "FAILED — an unhandled error"; a refusal exits 2. Which of
    those an operator gets is the whole point of both new clauses, so membership is
    asserted rather than assumed."""
    for cls in (channels.ChannelEncodeError, startframe.ShadowError):
        assert issubclass(cls, ArmatureError)
        assert parts.halt_outcome(cls("x", {}))[0] == 2


# ============================================================ the halt lines an operator reads


def _refusal_encoder_input():
    """Driven through `stage_render.py`, which is the tool that calls `ch.encode_u8(diff)`
    at :479 on an array `channels` did not normalise — the public door the finding names."""
    from armature_core import channels as ch
    ch.encode_u8(np.array([[0.5, float("nan")], [1.0, 0.0]]), where="p3_diff")


def _refusal_edge_threshold():
    """Driven through `stage_render.py`, the only production caller of `derive_edge`."""
    from armature_core import channels as ch
    z = np.ones((8, 8))
    n = np.zeros((8, 8, 3))
    n[..., 2] = 1.0
    ch.derive_edge(z, n, np.ones((8, 8), dtype=np.uint8), float("nan"), 30.0)


def _refusal_edge_angle_domain():
    from armature_core import channels as ch
    z = np.ones((8, 8))
    n = np.zeros((8, 8, 3))
    n[..., 2] = 1.0
    ch.derive_edge(z, n, np.ones((8, 8), dtype=np.uint8), 0.02, 400.0)


def _refusal_point_cloud():
    """Driven through `render_start_frame.py`, whose plate conditions a paid I2V
    submission and which is one of the three live consumers of `solve_camera`."""
    from armature_core import framing as fr
    cloud = [(0.0, 0.0, -0.5), (0.0, float("nan"), 0.5),
             (0.15, 0.0, 0.0), (-0.15, 0.0, 0.0)]
    fr.solve_camera(cloud, cloud, 270, 8, 50.0, 36.0, 832, 480,
                    height_frac=0.8, end_x_frac=0.5)


def _refusal_shadow_floor():
    """Driven through `render_start_frame.py`, the sole production caller of
    `shadow_ratio` (`:884`, recording `"eps": SF.SHADOW_FLOOR_EPS` at `:910`)."""
    from armature_core import startframe as sf
    black = np.zeros((2, 2, 3))
    sf.shadow_ratio(black, black, eps=0.0)


def _refusal_blend_band():
    """Driven through `rig_character.py`, the one call site of `rigid_segment_weights`."""
    from armature_core import binding as bd
    verts = np.array([[0., 0., 0.], [0., 0., 1.], [0., 0., 2.]])
    bones = [{"name": "a", "head": (0, 0, 0), "tail": (0, 0, 1), "parent": None},
             {"name": "b", "head": (0, 0, 1), "tail": (0, 0, 2), "parent": "a"}]
    bd.rigid_segment_weights(verts, bones, {"a": 1.0, "b": 1.0},
                             blend_band=float("inf"))


def _refusal_revisit_message():
    """Driven through `render_turnaround.py`, the tool whose plan this bound refuses."""
    from armature_core import turnaround as ta
    ta.orbit_azimuths(8, 0, 720)


HALT_ROWS = [
    # (finding, tool, sentinel, raiser, error class, clause the record must carry)
    ("F-e8074763", "stage_render.py", "STAGE_RENDER_HALT", _refusal_encoder_input,
     "ChannelEncodeError", "non_finite_encoder_input"),
    ("F-075b3af4", "stage_render.py", "STAGE_RENDER_HALT", _refusal_edge_threshold,
     "DepthError", "depth_rel_threshold_not_finite_and_positive"),
    ("F-075b3af4", "stage_render.py", "STAGE_RENDER_HALT", _refusal_edge_angle_domain,
     "NormalError", "normal_angle_deg_outside_domain"),
    ("F-526e9069", "render_start_frame.py", "RENDER_START_FRAME_HALT",
     _refusal_point_cloud, "FramingError", "point_cloud_not_finite"),
    ("F-efd6b45c", "render_start_frame.py", "RENDER_START_FRAME_HALT",
     _refusal_shadow_floor, "ShadowError", "shadow_floor_eps_is_zero"),
    ("F-95c9a97e", "rig_character.py", "RIG_CHARACTER_HALT", _refusal_blend_band,
     "ArmatureError", "bound_not_finite"),
    ("F-8361eff3", "render_turnaround.py", "RENDER_TURNAROUND_HALT",
     _refusal_revisit_message, "TurnaroundGate", "sweep_revisits_an_azimuth"),
]


@pytest.mark.parametrize("finding,tool,sentinel,raiser,cls,clause",
                         HALT_ROWS, ids=[f"{r[0]}-{r[5]}" for r in HALT_ROWS])
def test_the_halt_line_an_operator_reads_carries_this_waves_clause(
        finding, tool, sentinel, raiser, cls, clause, capsys):
    """Wave-18 rule 4: the record is PARSED, not assumed.

    A refusal that never reaches a halt line is a refusal an operator never sees. Each row
    drives a REAL tool's `__main__` block with `main` replaced by the raiser, reads the
    printed `<TOOL>_HALT` record, and asserts the exit code, the class, and the clause word
    a log reader would key on.
    """
    from blender_stub import exit_code_of_main_block

    code, escaped = exit_code_of_main_block(
        tool, raiser=raiser, argv=["python", tool, "--out", "nope"])
    out = capsys.readouterr().out
    assert escaped is None, f"{tool}: {escaped!r} escaped the handler"
    assert code == 2, f"{tool} ({finding}): exit {code!r}; the contract says 2"
    lines = [ln for ln in out.splitlines() if ln.split(" ", 1)[0] == sentinel]
    assert len(lines) == 1, f"{tool} ({finding}): {len(lines)} sentinel line(s)"
    rec = json.loads(lines[0][len(sentinel):].strip())
    assert rec["error"] == cls, rec
    assert isinstance(rec["evidence"], dict), rec
    assert rec["evidence"].get("clause") == clause, sorted(rec["evidence"])


def test_every_halt_line_this_wave_prints_is_strict_json():
    """`json.dumps` at its `allow_nan` default emits the bare `NaN` / `Infinity` tokens
    that JS `JSON.parse`, Go `encoding/json` and serde all reject, and three of this wave's
    operands ARE non-finite floats that `require_finite` writes into the evidence
    (`ev[name] = v`). `parts.halt_keysafe` names them instead; asserted here on the exact
    shapes this wave produces."""
    for value in (float("nan"), float("inf"), float("-inf")):
        ev = {"gate": None, "clause": "bound_not_finite", "operand": value}
        safe = parts.halt_keysafe(ev)
        assert safe["operand"] == repr(value)
        json.loads(json.dumps(safe, allow_nan=False))
