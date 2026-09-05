"""Wave-18 core-solvers amend — the red proofs for six routed findings.

Every test here was written before the fix it names, run against the wave-18 base
(`6b984dd`) to see it fail, and run once more with the fix reverted to prove the guard —
and not its neighbour — is what turns it green.

**The rule this wave adds** (wave-18 coordinator brief): a census keys on the RESOLVED
shape, never the spelled one; a fix's red proof runs against its SIBLINGS; a refusal names
the andon that pulled (the NAMED subclass, the clause that matches the message, the
evidence that carries the operand); and the halt line a tool actually prints is READ.

So every fixture below names the population its property must hold over —

* Gate FRAME: not "the render call has a status" but EVERY path `render_frame` returns,
  proven on a CANCELLED render standing over the PREVIOUS run's EXRs at the same stem,
  which is the one shape `os.path.isfile` / `getsize` / a re-read of the pixels all pass;
* `half_fovs`: not one bad lens but the whole camera-number population of both copies,
  and the SIBLING divisions in the same file enumerated (`ortho_half_spans`' own
  non-finite door, and `blender_scene.auto_radius`' `1/sin`);
* `depth_extent`: not "a NaN somewhere" but the SELECTED population — the pixels the
  mask and the sky test admit — proven on the two non-finite doors that reopen the exact
  byte collision `GEOMETRY_DEPTH_FLOOR` exists to close;
* `endpoints_match`: not "an empty list" but four distinct failures over the BONE
  POPULATION, one of which (a gained bone) is outside the iterated set entirely;
* the ageing clock: not "a stale receipt" but a receipt aged from the WRONG SIDE of
  today, which no `a > WINDOW` test can ever satisfy;
* `ev["clause"]`: not one raise but every raise in the three gates, derived by AST from
  the module rather than typed as a list of line numbers.
"""

import ast
import datetime
import importlib
import io
import os
import sys

import numpy as np
import pytest

TESTS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TESTS)
TOOLS = os.path.join(REPO, "tools")
CORE = os.path.join(TOOLS, "armature_core")
if TESTS not in sys.path:
    sys.path.insert(0, TESTS)

import blender_stub  # noqa: E402

from armature_core import assembly, channels, framing, resample  # noqa: E402
from armature_core.errors import ArmatureError, GateFailure  # noqa: E402

#: The twenty-one modules the core-solvers domain owns, from the frozen wave-18 domain map.
OWNED_MODULES = (
    "aapose", "assembly", "binding", "blender_scene", "channels", "clipcompare",
    "clipstats", "framing", "glb", "joints", "landmarks", "lift_solve", "openpose",
    "parts", "pngio", "posearc", "resample", "sitelist", "startframe", "turnaround",
    "walk",
)


@pytest.fixture
def BS():
    """`blender_scene` imported under the suite's ONE stub installer, then unimported.

    It reuses `blender_stub.blender_stubbed()` rather than writing `sys.modules["bpy"]`
    here, deliberately. `tests/test_packaging.sys_modules_writers` derives the population
    of stub installers from the tree and requires each one to be named in
    `RECORDED_STUB_INSTALLERS`, to have a line in `INSTALLER_MODULE` saying how to drive
    it, and to be exercised by an `ORDER_DEPENDENT_PAIRS` entry that runs it before a
    reader — because the teardown is the invariant: a stub left in `sys.modules`, or
    bound as an ATTRIBUTE of the `armature_core` package, makes
    `tests/test_cli.py::_probe("blender_scene")` read `ok` where the honest answer is
    `needs-blender`, which is this suite's own defect class manufactured by its own
    fixture. A fifth installer would be a fifth thing to prove; the existing one already
    carries the full teardown and is already driven by a pair, so this file adds none.

    Function-scoped, because `blender_stubbed()`'s teardown pops what it made importable
    and the module is cheap to re-import; a module-scoped stub would outlive the tests
    that need it.
    """
    with blender_stub.blender_stubbed():
        yield importlib.import_module("armature_core.blender_scene")


# ======================================================================= F-25a5ecbf
#
# `bpy.ops.render.render(write_still=False)` in `armature_core.blender_scene.render_frame`
# was the ONE render invocation in the live tree whose operator status set was neither
# captured nor read — the single member of the population `_render_status` was written for
# that wave 14's sweep could not reach, because that sweep enumerated `tools/*.py` and this
# call lives in `armature_core`.
#
# The operand is a CANCELLED render standing over the PREVIOUS run's EXRs at the same
# stem. `exr_dir` is `os.path.join(work_dir, "master")`, stable across runs, and the stem
# is the frame index — so nothing distinguishes this run's frame 7 from the last run's,
# and `stage_render`'s only downstream check is `z.shape != (height, width)`, which a
# same-resolution stale frame satisfies.


class _FakeOutputNode:
    """The one attribute `render_frame` writes on a File Output node."""

    def __init__(self):
        self.file_name = None


def _exr_tree(root, tags, stem, payload=b"stale-exr-bytes"):
    """Write `<root>/<tag>/<stem><tag>.exr` for each tag and return the paths."""
    paths = {}
    for tag in tags:
        d = os.path.join(root, tag)
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, f"{stem}{tag}.exr")
        with open(p, "wb") as fh:
            fh.write(payload)
        paths[tag] = p
    return paths


def test_a_cancelled_render_over_the_previous_runs_exrs_is_refused_by_name(BS, tmp_path):
    """THE OPERAND. Frame 7's three EXRs are already on disk from a previous run; this
    run's `bpy.ops.render.render` returns `{'CANCELLED'}` without raising.

    On the base this returned the three stale paths and `stage_render` read them straight
    back through `bs.read_exr` — the geometry signature and camera matrix of THIS run
    recorded beside pixels from another, hashed into the manifest, and shipped as the
    per-frame control images driving a paid generation.
    """
    exr_dir = str(tmp_path / "master")
    tags = ("depth", "alpha", "normal")
    _exr_tree(exr_dir, tags, "00007_")
    outputs = {t: _FakeOutputNode() for t in tags}

    class _Ops:
        class render:
            @staticmethod
            def render(write_still=False):
                return {"CANCELLED"}

    BS.bpy.ops = _Ops()
    with pytest.raises(GateFailure) as exc:
        BS.render_frame(object(), outputs, 7, exr_dir)

    ev = exc.value.evidence
    assert ev["gate"] == "FRAME"
    assert ev["clause"] == "operator_status"
    assert ev["frame_index"] == 7
    assert ev["status"] == ["CANCELLED"]
    assert "FINISHED" in str(exc.value)


def test_an_unreadable_operator_return_fails_the_finished_clause_rather_than_passing_it(
        BS, tmp_path):
    """`_render_status`' own contract: an unreadable return is `[]`, which FAILS
    `'FINISHED' in ...` rather than walking past it. A `None` return is the shape a
    mocked or stubbed operator produces, and it must not read as a success."""
    exr_dir = str(tmp_path / "master")
    tags = ("depth", "alpha")
    _exr_tree(exr_dir, tags, "00000_")
    outputs = {t: _FakeOutputNode() for t in tags}

    class _Ops:
        class render:
            @staticmethod
            def render(write_still=False):
                return None

    BS.bpy.ops = _Ops()
    with pytest.raises(GateFailure) as exc:
        BS.render_frame(object(), outputs, 0, exr_dir)
    assert exc.value.evidence["status"] == []
    assert exc.value.evidence["clause"] == "operator_status"


def test_a_finished_render_that_wrote_nothing_is_refused_on_the_absent_path(BS, tmp_path):
    """SIBLING CLAUSE. FINISHED and no file: on the base this returned a path
    `bpy.data.images.load` would then raise an untyped RuntimeError on — exit 1, "an
    unhandled error", where a refusal at exit 2 belongs. The writer verifies its own
    output."""
    exr_dir = str(tmp_path / "master")
    outputs = {t: _FakeOutputNode() for t in ("depth", "alpha")}

    class _Ops:
        class render:
            @staticmethod
            def render(write_still=False):
                return {"FINISHED"}

    BS.bpy.ops = _Ops()
    with pytest.raises(GateFailure) as exc:
        BS.render_frame(object(), outputs, 3, exr_dir)
    assert exc.value.evidence["clause"] == "channel_never_reached_disk"
    assert exc.value.evidence["frame_index"] == 3


def test_a_finished_render_leaving_a_zero_byte_channel_is_refused(BS, tmp_path):
    """SIBLING CLAUSE. A file that exists and holds nothing is what a cancelled write
    leaves behind, and every consumer downstream reads the path rather than the size."""
    exr_dir = str(tmp_path / "master")
    tags = ("depth", "alpha")
    _exr_tree(exr_dir, tags, "00001_", payload=b"")
    outputs = {t: _FakeOutputNode() for t in tags}

    class _Ops:
        class render:
            @staticmethod
            def render(write_still=False):
                return {"FINISHED"}

    BS.bpy.ops = _Ops()
    with pytest.raises(GateFailure) as exc:
        BS.render_frame(object(), outputs, 1, exr_dir)
    assert exc.value.evidence["clause"] == "channel_is_zero_bytes"


def test_a_finished_render_that_left_the_previous_files_untouched_is_refused_as_stale(
        BS, tmp_path):
    """THE CLAUSE THE SNAPSHOT EXISTS FOR — Gate GLB's shape, one channel at a time.

    A render that reports FINISHED and writes nothing at all leaves three files whose
    size AND nanosecond mtime are exactly what they were before it ran. `isfile`,
    `getsize` and a re-read of the pixels all pass on those; the pre-render snapshot is
    the only thing that can tell them from this run's output.
    """
    exr_dir = str(tmp_path / "master")
    tags = ("depth", "alpha", "normal")
    _exr_tree(exr_dir, tags, "00007_")
    outputs = {t: _FakeOutputNode() for t in tags}

    class _Ops:
        class render:
            @staticmethod
            def render(write_still=False):
                return {"FINISHED"}

    BS.bpy.ops = _Ops()
    with pytest.raises(GateFailure) as exc:
        BS.render_frame(object(), outputs, 7, exr_dir)
    ev = exc.value.evidence
    assert ev["clause"] == "stale_channel"
    assert ev["frame_index"] == 7
    assert ev["tag"] in tags


def test_a_render_that_actually_writes_this_frame_returns_the_three_paths(BS, tmp_path):
    """The gate must not be a check that cannot pass. A FINISHED render that replaces
    every channel returns exactly the dict it always returned, one path per tag."""
    exr_dir = str(tmp_path / "master")
    tags = ("depth", "alpha", "normal")
    _exr_tree(exr_dir, tags, "00007_", payload=b"old")
    outputs = {t: _FakeOutputNode() for t in tags}

    class _Ops:
        class render:
            @staticmethod
            def render(write_still=False):
                _exr_tree(exr_dir, tags, "00007_", payload=b"fresh-bytes-for-this-run")
                return {"FINISHED"}

    BS.bpy.ops = _Ops()
    paths = BS.render_frame(object(), outputs, 7, exr_dir)
    assert sorted(paths) == sorted(tags)
    for tag in tags:
        assert paths[tag] == os.path.join(exr_dir, tag, f"00007_{tag}.exr")
        assert os.path.getsize(paths[tag]) > 0
    assert all(n.file_name == "00007_" for n in outputs.values())


def test_the_render_status_helper_here_matches_the_body_the_instruments_spelled():
    """The copy, held from drifting. The wave-14 census walks `tools/*.py` and
    `tools/superseded/*.py` and cannot see this module, so the equality is asserted here.

    Copied from `tools/render_start_frame.py::_render_status` (all nine tool-side copies
    are one AST body; `distinct bodies: 1`). The EXECUTABLE body is compared, not the
    docstring: this module's docstring has to say something different, because the
    tool-side one says the helper is spelled per tool "because these modules share no
    parent inside `tools/`", which is not the reason it is spelled here.
    """
    def _executable_body(path, name):
        tree = ast.parse(io.open(path, encoding="utf-8").read())
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == name)
        body = [s for s in fn.body
                if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant)
                        and isinstance(s.value.value, str))]
        return "\n".join(ast.unparse(s) for s in body)

    theirs = _executable_body(os.path.join(TOOLS, "render_start_frame.py"),
                             "_render_status")
    ours = _executable_body(os.path.join(CORE, "blender_scene.py"), "_render_status")
    assert ours == theirs, (ours, theirs)


# ======================================================================= F-329a9555
#
# `ortho_half_spans` opens with `if ortho_scale <= 0.0: raise` — and `nan <= 0.0` is False,
# so a NaN walks past the function's own and only clause. `half_fovs` has no clause at all,
# and its byte-twin in `blender_scene` has none either.
#
# SIBLING ENUMERATION — every division by a camera number in `framing.py` and in
# `turnaround.py`'s perspective branch (brief rule 2). There are seven, and each is named
# by a test below or by a measurement saying why it is out of scope:
#
#   1. framing.half_fovs:125       `sx * 0.5 / lens_mm`, `sy * 0.5 / lens_mm`   [the operand]
#   2. framing.half_fovs:121/124   `sensor_mm * height / width` (and the mirror) [width/height]
#   3. framing.ortho_half_spans    `ortho_scale * height / width` (and the mirror)
#   4. framing.project:214/215     `/ -z` — bounded already by the `z >= -1e-9` behind-test
#   5. framing.project:214/215     `/ math.tan(hx)` — tan(0) == 0; CLOSED by clause 1
#   6. framing.project:211/212     `/ hx`, `/ hy` from ortho_half_spans — CLOSED by clause 3
#   7. blender_scene.auto_radius   `/ math.sin(min(hx, hy))` — CLOSED by the mirrored clause
#
# and `turnaround.projection_plan`'s perspective branch, which divides by nothing but
# RECORDS `float(lens_mm)` / `float(sensor_mm)` into the plan a run is composed from.


@pytest.mark.parametrize("lens,sensor,clause", [
    (50.0, 0.0, "sensor_mm"),
    (50.0, -36.0, "sensor_mm"),
    (50.0, float("nan"), "sensor_mm"),
    (50.0, float("inf"), "sensor_mm"),
    (0.0, 36.0, "lens_mm"),
    (-50.0, 36.0, "lens_mm"),
    (float("nan"), 36.0, "lens_mm"),
    (float("inf"), 36.0, "lens_mm"),
])
def test_half_fovs_refuses_every_degenerate_camera_number_by_name(lens, sensor, clause):
    """THE OPERAND, and its whole population. On the base:
    `half_fovs(50, 0, 832, 480)` returned `(0.0, 0.0)` and `project` then raised a bare
    `ZeroDivisionError` from `math.tan(0.0)` — untyped, so the 21-tool halt contract
    records exit 1 "an unhandled error" where a refusal at exit 2 belongs;
    `half_fovs(-50, 36, ...)` returned a NEGATIVE field of view, from which `project`
    point-mirrors the frame about its centre and `silhouette_extent` reports a perfectly
    plausible finite box.
    """
    with pytest.raises(framing.FramingError) as exc:
        framing.half_fovs(lens, sensor, 832, 480)
    ev = exc.value.evidence
    assert ev["clause"] == f"{clause}_not_finite_and_positive"
    assert ev["andon"] == "FramingError"
    assert ev["gate"] is None
    assert clause in ev


def test_a_negative_lens_no_longer_point_mirrors_the_frame():
    """The escape that was open END TO END: `render_turnaround.py` declares `--lens` as a
    bare `type=float`, and a mirrored silhouette that stays inside the frame clears Gate
    WHOLE, Gate CROP and Gate ALPHA. The refusal is inside the function performing the
    step, so every caller inherits it."""
    ok = framing.project((0.3, 0.0, 1.6), (0.0, 0.0, 0.0), 4.0, 0.0, 0.0, 50.0, 36.0,
                         832, 480)
    assert ok[2] is True
    with pytest.raises(framing.FramingError,
                       match="lens_mm=-50.0 is not a finite positive camera number"):
        framing.project((0.3, 0.0, 1.6), (0.0, 0.0, 0.0), 4.0, 0.0, 0.0, -50.0, 36.0,
                        832, 480)


@pytest.mark.parametrize("scale", [float("nan"), float("inf"), float("-inf")])
def test_ortho_half_spans_bounds_the_direction_its_own_clause_did_not(scale):
    """SIBLING 3. `nan <= 0.0` is False, so `ortho_half_spans(nan, 832, 480)` RETURNED
    `(nan, nan)` past its own and only clause — measured on the base. The guard is
    reordered to `not (isfinite and > 0)` so the direction it does not bound is bounded.
    `turnaround.projection_plan`'s own docstring already recorded that this function
    "takes nan and inf"; that sentence is now false in the safe direction."""
    with pytest.raises(framing.FramingError) as exc:
        framing.ortho_half_spans(scale, 832, 480)
    assert exc.value.evidence["clause"] == "ortho_scale_not_positive"
    assert exc.value.evidence["ortho_scale"] == pytest.approx(scale, nan_ok=True)


@pytest.mark.parametrize("w,h", [(0, 480), (832, 0), (-832, 480), (832, -480)])
def test_both_span_functions_refuse_a_degenerate_frame_size(w, h):
    """SIBLING 2 and SIBLING 3's other divisor. `sensor_mm * height / width` divides by
    the frame's own dimensions, and `width >= height` picks WHICH one — so a zero width
    is a ZeroDivisionError in the portrait branch and a silent zero span in the other.
    Both functions take the same clause because both divide by the same numbers."""
    with pytest.raises(framing.FramingError) as exc:
        framing.half_fovs(50.0, 36.0, w, h)
    assert exc.value.evidence["clause"] == "frame_size_not_positive"
    with pytest.raises(framing.FramingError) as exc:
        framing.ortho_half_spans(1.0, w, h)
    assert exc.value.evidence["clause"] == "frame_size_not_positive"


def test_the_blender_scene_copy_carries_the_same_clauses(BS):
    """SIBLING 7's root. `blender_scene.half_fovs` is the byte-twin `tests/test_framing.py`
    pins framing's copy against, and `auto_radius` divides by `math.sin(min(hx, hy))` —
    so a zero sensor was a ZeroDivisionError there and a NaN lens placed the orbit camera
    at a NaN radius. The clause lives in the twin as well, which closes `auto_radius`
    without a second guard."""
    for lens, sensor, clause in ((50.0, 0.0, "sensor_mm"),
                                 (-50.0, 36.0, "lens_mm"),
                                 (float("nan"), 36.0, "lens_mm")):
        phrase = f"{clause}=.* is not a finite positive camera number"
        with pytest.raises(BS.CameraGeometry, match=phrase) as exc:
            BS.half_fovs(lens, sensor, 832, 480)
        assert exc.value.evidence["clause"] == f"{clause}_not_finite_and_positive"
        with pytest.raises(BS.CameraGeometry, match=phrase) as exc:
            BS.auto_radius(1.0, lens, sensor, 832, 480, 1.2)
        assert exc.value.evidence["clause"] == f"{clause}_not_finite_and_positive"
    assert issubclass(BS.CameraGeometry, ArmatureError)
    assert BS.auto_radius(1.0, 50.0, 36.0, 832, 480, 1.2) > 0.0


def test_the_two_half_fovs_copies_still_agree_on_every_legal_camera():
    """The pin `tests/test_framing.py::test_half_fovs_matches_blenders` makes, re-asserted
    here against the LIVE module rather than an exec'd source slice — so the guard being
    added to both copies is proven not to have moved either one's arithmetic."""
    import inspect
    import math as _math

    path = os.path.join(os.path.dirname(inspect.getfile(framing)), "blender_scene.py")
    with io.open(path, encoding="utf-8") as fh:
        src = fh.read()
    start = src.index("def half_fovs(")
    end = src.index("\ndef ", start + 1)
    ns = {"math": _math, "CameraGeometry": framing.FramingError}
    exec(compile(src[start:end], "blender_scene.half_fovs", "exec"), ns)  # noqa: S102
    for w, h in ((832, 480), (480, 832), (512, 512), (1280, 720)):
        assert framing.half_fovs(50.0, 36.0, w, h) == ns["half_fovs"](50.0, 36.0, w, h)


def test_the_perspective_plan_refuses_the_camera_numbers_it_records():
    """SIBLING — `turnaround.projection_plan`'s perspective branch. It divides by nothing,
    which is exactly why it was open: it RECORDS `float(lens_mm)` and `float(sensor_mm)`
    into the plan, and the ortho branch's pin already refuses a non-finite span by name
    while the perspective branch took any float at all."""
    from armature_core import turnaround

    plan = turnaround.projection_plan(False, 50.0, 36.0)
    assert plan["lens_mm"] == 50.0 and plan["sensor_mm"] == 36.0
    for lens, sensor, clause in ((float("nan"), 36.0, "lens_mm"),
                                 (-50.0, 36.0, "lens_mm"),
                                 (50.0, 0.0, "sensor_mm")):
        with pytest.raises(turnaround.TurnaroundPlanRefusal,
                           match="a PERSPECTIVE plan was asked for with "
                                 f"{clause}=") as exc:
            turnaround.projection_plan(False, lens, sensor)
        assert exc.value.evidence["clause"] == f"{clause}_not_finite_and_positive"


# ======================================================================= F-476a4ee8
#
# `require_finite` appears in `parts`, `gates`, `donor_gate`, `lift_solve`, `resample`,
# `rig_gates` and `turnaround` — and ZERO times in `channels.py`, the module that authors
# every depth control-sequence pixel.
#
# The SELECTED POPULATION is `np.logical_and(mask > 0, z < SKY_Z)`. `nan < 1e9` is False so
# a NaN geometry pixel is dropped from the extent and stays in the array; `-inf < 1e9` is
# True so a -inf pixel becomes `z_min`. Both reopen the farthest-geometry-vs-void byte
# collision `GEOMETRY_DEPTH_FLOOR` was introduced to close.


def _all_geometry(vals):
    z = np.array(vals, dtype=np.float64)
    return z, np.ones(z.shape, dtype=np.uint8)


def test_a_nan_geometry_pixel_is_refused_rather_than_encoded_as_the_void_byte():
    """THE OPERAND, door (a). On the base: `depth_extent` returned `(1.0, 3.0)` — the NaN
    silently dropped — `normalize_depth` returned `nan` at that pixel, and `encode_u8`
    cast the NaN to byte **0**, byte-identical to `BACKGROUND_DEPTH`. The collision the
    reserved floor exists to prevent, reachable per pixel."""
    z, mask = _all_geometry([[1.0, 2.0], [float("nan"), 3.0]])
    with pytest.raises(channels.DepthError) as exc:
        channels.depth_extent(z, mask)
    ev = exc.value.evidence
    assert ev["clause"] == "non_finite_geometry_depth"
    assert ev["n_non_finite"] == 1
    assert ev["n_finite"] == 3
    assert ev["n"] == 4
    assert ev["n_nan"] == 1


def test_a_negative_infinity_geometry_pixel_is_refused_rather_than_becoming_z_min():
    """THE OPERAND, door (b). On the base: `-inf < SKY_Z` is True, so `depth_extent`
    returned `(-inf, 3.0)`, `span` was `+inf`, the `span <= 0` guard was False, and EVERY
    finite geometry pixel encoded to byte **1** — the whole depth frame a flat plate with
    no gradient at all.

    The realistic consequence rides `stage_render.py:384-386`: the per-shot window is
    `min(mins)` over every frame, so ONE -inf pixel on ONE frame flattens EVERY frame's
    `depth_pershot` control image."""
    z, mask = _all_geometry([[1.0, 2.0], [3.0, float("-inf")]])
    with pytest.raises(channels.DepthError) as exc:
        channels.depth_extent(z, mask)
    ev = exc.value.evidence
    assert ev["clause"] == "non_finite_geometry_depth"
    assert ev["n_non_finite"] == 1
    assert ev["n_neg_inf"] == 1


def test_a_non_finite_pixel_outside_the_mask_is_not_the_gates_business():
    """The gate must not be a check that cannot pass, and the population is the SELECTED
    one. A NaN where there is no geometry is background, not a depth this module authored,
    and refusing it would refuse every ordinary frame."""
    z = np.array([[1.0, 2.0], [float("nan"), 3.0]], dtype=np.float64)
    mask = np.array([[1, 1], [0, 1]], dtype=np.uint8)
    assert channels.depth_extent(z, mask) == (1.0, 3.0)


def test_a_sky_pixel_inside_the_mask_still_does_not_participate():
    """The sky test is part of the selector and stays there: `SKY_Z` is Blender's
    unhit-pixel value, a finite 1e10, and it is excluded by value rather than refused."""
    z = np.array([[1.0, 2.0], [1e10, 3.0]], dtype=np.float64)
    mask = np.ones((2, 2), dtype=np.uint8)
    assert channels.depth_extent(z, mask) == (1.0, 3.0)


@pytest.mark.parametrize("near,far,name", [
    (float("nan"), 3.0, "z_near"),
    (1.0, float("nan"), "z_far"),
    (float("-inf"), 3.0, "z_near"),
    (1.0, float("inf"), "z_far"),
])
def test_normalize_depth_refuses_a_non_finite_window(near, far, name):
    """SIBLING CLAUSE, the second door into the same encoder. `span <= 0` is False for a
    NaN window, which sent the WHOLE frame to byte 0. That door is closed upstream today
    by `shotspec`'s `_require_finite_number` — but only for callers who arrive through a
    normalised spec, and this module is imported directly by four tools."""
    z, mask = _all_geometry([[1.0, 2.0], [3.0, 4.0]])
    with pytest.raises(channels.DepthError) as exc:
        channels.normalize_depth(z, mask, near, far)
    assert exc.value.evidence["clause"] == "non_finite_depth_window"
    assert name in exc.value.evidence


def test_normalize_depth_refuses_a_non_finite_pixel_inside_the_mask():
    """"No geometry" and "a pixel we could not read" stop being the same byte. The window
    can be perfectly finite and a single unreadable pixel still reaches `encode_u8`."""
    z, mask = _all_geometry([[1.0, 2.0], [float("nan"), 3.0]])
    with pytest.raises(channels.DepthError) as exc:
        channels.normalize_depth(z, mask, 1.0, 3.0)
    ev = exc.value.evidence
    assert ev["clause"] == "non_finite_geometry_depth"
    assert ev["n_non_finite"] == 1


def test_an_ordinary_depth_frame_still_encodes_exactly_as_it_did():
    """The arm has to be able to do nothing AND to work. This is the docstring's own
    worked example, byte for byte: geometry lands on [GEOMETRY_DEPTH_FLOOR, 1] and the
    void alone is byte 0."""
    z = np.array([[1.0, 2.0], [3.0, 1e10]], dtype=np.float64)
    mask = np.array([[1, 1], [1, 0]], dtype=np.uint8)
    assert channels.depth_extent(z, mask) == (1.0, 3.0)
    d = channels.normalize_depth(z, mask, 1.0, 3.0)
    assert channels.encode_u8(d).tolist() == [[255, 128], [1, 0]]


def test_the_encoder_can_never_be_handed_a_non_finite_input_from_this_module():
    """The property the two clauses exist for, stated over the whole module: no path
    through `depth_extent` -> `normalize_depth` -> `encode_u8` can produce a NaN input to
    the cast that silently becomes the void byte."""
    z = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float64)
    mask = np.ones((2, 2), dtype=np.uint8)
    near, far = channels.depth_extent(z, mask)
    d = channels.normalize_depth(z, mask, near, far)
    assert np.isfinite(d).all()


def test_stage_render_s_message_is_true_of_what_depth_extent_now_measures():
    """`stage_render.py` raises "mask is non-empty but carries no finite depth" when
    `depth_extent` returns None — a message asserting a finiteness property the function
    never measured. It measures it now, so the message is true. The tool file is another
    domain's; the property is asserted here, where the function lives."""
    z = np.array([[1e10, 1e10]], dtype=np.float64)
    mask = np.ones((1, 2), dtype=np.uint8)
    assert channels.depth_extent(z, mask) is None


# ======================================================================= F-62774c72
#
# `endpoints_match`'s population is `s["local"]` — the SOURCE's bone set — and it indexes
# `d["local"][b]` unguarded. Four measured failures on the base, all four below.


_I = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]


def _frames(n, bones=("b",), root=(0.0, 0.0, 0.0)):
    return [{"frame": k, "local": {b: [list(r) for r in _I] for b in bones},
             "root": list(root)} for k in range(n)]


def test_an_empty_pair_is_refused_by_name_rather_than_indexing_off_the_end():
    """(a) On the base: a bare `IndexError: list index out of range` from
    `src_frames[0]` — exit 1 with no gate id and no evidence — where `monotonic` and
    `resample_frames` both refuse `n < 2` by name."""
    with pytest.raises(resample.ResampleGate) as exc:
        resample.endpoints_match([], [])
    ev = exc.value.evidence
    assert ev["clause"] == "no_frames_to_compare"
    assert ev["n_src"] == 0 and ev["n_dst"] == 0


def test_a_one_frame_pair_no_longer_reports_agreement_over_nothing():
    """(b) THE VACUITY SHAPE. On the base a ONE-frame source and destination RETURNED the
    full PASS verdict "first and last frames are the source's own, value for value" with
    `checked: ['first','last']`, having compared frame 0 to itself twice — the shape
    `gate_parts_determinism`, `gate_cascade_topology` and `gate_no_paid_nodes` all got
    vacuity guards for."""
    one = _frames(1)
    with pytest.raises(resample.ResampleGate) as exc:
        resample.endpoints_match(one, one)
    ev = exc.value.evidence
    assert ev["clause"] == "a_single_frame_is_both_endpoints"
    assert ev["n_src"] == 1 and ev["n_dst"] == 1


def test_a_bone_dropped_from_the_destination_refuses_naming_the_bone():
    """(c) THE DEFECT THE GATE EXISTS TO DETECT, which arrived as a bare `KeyError('b')`
    — exit 1, "FAILED - an unhandled error", gate null, evidence null — from the one
    production caller, `tools/resample_motion.py:169`, on a record read from a JSON file."""
    src = _frames(3, bones=("hip", "knee"))
    dst = _frames(3, bones=("hip",))
    with pytest.raises(resample.ResampleGate) as exc:
        resample.endpoints_match(src, dst)
    ev = exc.value.evidence
    assert ev["clause"] == "bones_missing_from_destination"
    assert ev["bones_missing_from_destination"] == ["knee"]
    assert ev["label"] == "first"


def test_a_bone_the_source_never_had_refuses_rather_than_passing_unseen():
    """(d) THE MEMBER OUTSIDE THE OLD WALK. A destination that GAINED a bone RETURNED the
    full PASS verdict, because the extra bone is outside the iterated population — the
    population, not the operand, is what this rule is about."""
    src = _frames(3, bones=("hip",))
    dst = _frames(3, bones=("hip", "tail"))
    with pytest.raises(resample.ResampleGate) as exc:
        resample.endpoints_match(src, dst)
    ev = exc.value.evidence
    assert ev["clause"] == "bones_absent_from_source"
    assert ev["bones_absent_from_source"] == ["tail"]


def test_an_endpoint_that_actually_differs_still_refuses_with_its_own_clause():
    """The original clause, kept and now distinguishable from the three new ones — a halt
    record can say WHICH of the four failures fired."""
    src = _frames(3)
    dst = _frames(3)
    dst[-1]["root"] = [0.0, 0.0, 1.0]
    with pytest.raises(resample.ResampleGate) as exc:
        resample.endpoints_match(src, dst)
    ev = exc.value.evidence
    assert ev["clause"] == "endpoint_pose_differs"
    assert ev["label"] == "last"
    assert ev["root_differs"] is True


def test_a_correct_resample_still_returns_the_verdict_it_always_did():
    """The arm can still do nothing AND work: two frames in, two frames out, endpoints
    verbatim."""
    src = _frames(4, bones=("hip", "knee"))
    dst = _frames(4, bones=("hip", "knee"))
    ev = resample.endpoints_match(src, dst)
    assert ev["checked"] == ["first", "last"]
    assert "value for value" in ev["verdict"]


def test_no_verdict_returning_gate_in_the_owned_modules_affirms_over_an_empty_population():
    """THE SIBLING CENSUS for this finding, derived rather than typed.

    Every function in the twenty-one owned modules that can set `ev["verdict"]` was
    probed with an empty population. On the wave-18 base exactly ONE of them returned an
    affirmative — `resample.endpoints_match` — and it is the operand above. The others
    already refuse by name: `gate_no_paid_nodes` (`empty_graph`), `gate_batch_topology`
    and `gate_cascade_topology` (`0 frame(s)`), `gate_slot_ceiling` (no BatchImagesNode),
    `gate_parts_determinism` (`0 and 0 part(s)`), `gate_parts_accounting`,
    `gate_rigid_arrival`, `gate_set_distinct`, `gate_view_crop`, `gate_view_alpha`,
    `gate_alpha`, `gate_cadence_is_representable`, `gate_stance_frac_is_modelled`,
    `compare_signatures`, `validate_motion_record`, `monotonic`,
    `gate_compositor_wiring`; `clipstats.horizon_row` answers NOT FOUND, which is an
    explicit non-affirmative and not a verdict.

    This test keys on the RESOLVED shape — it calls the functions — rather than on the
    presence of a guard's spelling.
    """
    probes = []

    def affirms(fn, *a, **k):
        try:
            r = fn(*a, **k)
        except Exception:                                             # noqa: BLE001
            return False
        return isinstance(r, dict) and "verdict" in r

    from armature_core import parts, turnaround, walk

    probes.append(("assembly.gate_no_paid_nodes", affirms(assembly.gate_no_paid_nodes, {})))
    probes.append(("assembly.gate_slot_ceiling", affirms(assembly.gate_slot_ceiling, {})))
    probes.append(("assembly.gate_batch_topology",
                   affirms(assembly.gate_batch_topology, {}, 0, "1", "2", "3",
                           expected_sources=[])))
    probes.append(("assembly.gate_cascade_topology",
                   affirms(assembly.gate_cascade_topology, {}, 0, [], "f", "v", "c",
                           expected_sources=[])))
    probes.append(("resample.monotonic", affirms(resample.monotonic, 0, 0)))
    # The vacuous population here is ONE frame, not zero: a one-frame pair is the input
    # on which the gate compared frame 0 to itself twice and reported agreement. The
    # empty pair raised an untyped IndexError on the base, which is a crash rather than
    # an affirmative — so probing `[]` alone would have read this gate as already sound.
    probes.append(("resample.endpoints_match(empty)",
                   affirms(resample.endpoints_match, [], [])))
    probes.append(("resample.endpoints_match(one frame)",
                   affirms(resample.endpoints_match, _frames(1), _frames(1))))
    probes.append(("parts.gate_parts_determinism",
                   affirms(parts.gate_parts_determinism, {}, {}, 1.0)))
    probes.append(("parts.gate_parts_accounting",
                   affirms(parts.gate_parts_accounting, [], 0, [])))
    probes.append(("parts.gate_rigid_arrival", affirms(parts.gate_rigid_arrival, [], 1.0)))
    probes.append(("turnaround.gate_set_distinct",
                   affirms(turnaround.gate_set_distinct, [], 0)))
    probes.append(("turnaround.gate_view_crop",
                   affirms(turnaround.gate_view_crop, 0, None, 64, 64)))
    probes.append(("walk.gate_cadence_is_representable",
                   affirms(walk.gate_cadence_is_representable, [])))

    assert [name for name, yes in probes if yes] == [], probes


# ======================================================================= F-47db9eff


def test_a_receipt_dated_in_the_future_is_refused_by_name(monkeypatch):
    """THE OPERAND. A single transposed leading digit on the year the four live entries
    already carry. On the base: `measurement_age_days` returned `(-36502, '2126-08-13')`,
    `classes_whose_measurement_is_advisory` came back `[]`, and `gate_no_paid_nodes`
    RETURNED the verdict "... (oldest reading **-36502 day(s) old, all within the 90-day
    window**)" — a receipt dated in the future is permanently current, and the gate says
    so, in the ageing clause added one wave ago precisely because "a receipt table with no
    ageing clause is a licence map with no fetch date"."""
    monkeypatch.setitem(
        assembly.MEASURED_FREE_CLASSES, "LoadImage",
        {"api_node": False, "measured_with": "get_node", "measured_on": "2126-08-13"})
    with pytest.raises(assembly.AssemblyGate) as exc:
        assembly.gate_no_paid_nodes({"1": {"class_type": "LoadImage"}},
                                    allowed=("LoadImage",))
    ev = exc.value.evidence
    assert ev["clause"] == "measurement_dated_in_the_future"
    assert ev["classes_measured_in_the_future"] == {"LoadImage": -36502} or (
        ev["classes_measured_in_the_future"]["LoadImage"] < 0)


def test_the_clock_itself_has_a_floor_not_only_the_gate():
    """The direction the clause did not bound, measured on the function rather than
    through the gate. `(on - when).days` is signed and the staleness test is
    `a > WINDOW` — which a negative age can never satisfy."""
    future = {"api_node": False, "measured_with": "get_node", "measured_on": "2126-08-13"}
    age, raw = assembly.measurement_age_days(future, today=datetime.date(2026, 9, 4))
    assert age < 0 and raw == "2126-08-13"
    assert assembly.measurement_is_dated_in_the_future(future,
                                                       today=datetime.date(2026, 9, 4))
    ok = {"api_node": False, "measured_with": "get_node", "measured_on": "2026-08-13"}
    assert not assembly.measurement_is_dated_in_the_future(
        ok, today=datetime.date(2026, 9, 4))


def test_a_receipt_dated_today_is_current_and_not_refused(monkeypatch):
    """The boundary the floor sits on: zero is a legal age. A gate that refused today's
    own measurement would refuse the diff that takes it."""
    today = datetime.date.today().isoformat()
    monkeypatch.setitem(
        assembly.MEASURED_FREE_CLASSES, "LoadImage",
        {"api_node": False, "measured_with": "get_node", "measured_on": today})
    ev = assembly.gate_no_paid_nodes({"1": {"class_type": "LoadImage"}},
                                     allowed=("LoadImage",))
    assert ev["measurement_age_days"]["LoadImage"] == 0
    assert ev["classes_measured_in_the_future"] == {}


def test_the_advisory_state_reaches_a_reader_rather_than_only_a_sentence(monkeypatch):
    """The second half, decided contrastively (see the docstring): ADVISORY stays
    REPORTING-ONLY — a stale receipt does not refuse — but
    `classes_whose_measurement_is_advisory` had NO consumer anywhere in `tools/` (grep,
    zero hits outside this module and its unit test), so the state that begins on
    2026-11-12 for all four live entries existed only in a sentence nobody reads. It is a
    named field of the returned record now, so a payload writer can key on it."""
    monkeypatch.setitem(
        assembly.MEASURED_FREE_CLASSES, "LoadImage",
        {"api_node": False, "measured_with": "get_node", "measured_on": "2020-01-01"})
    ev = assembly.gate_no_paid_nodes({"1": {"class_type": "LoadImage"}},
                                     allowed=("LoadImage",))
    assert ev["classes_whose_measurement_is_advisory"] == ["LoadImage"]
    assert ev["measurement_is_advisory"] is True
    assert "ADVISORY" in ev["verdict"]


def test_the_live_receipt_table_is_neither_future_dated_nor_unreadable():
    """The four shipped rows, read rather than assumed. This is the population the clause
    actually protects, and it is the one a diff widens."""
    today = datetime.date.today()
    for name, rec in assembly.MEASURED_FREE_CLASSES.items():
        age, raw = assembly.measurement_age_days(rec, today=today)
        assert age is not None, (name, raw)
        assert age >= 0, (name, raw, age)


# ======================================================================= F-8d0e4cf1
#
# The census keys on the RESOLVED shape: every `Raise` node inside the three gates, found
# by AST walk of the module, never a typed list of line numbers.


THREE_GATES = ("gate_batch_topology", "gate_slot_ceiling", "gate_cascade_topology")


def _raises_without_a_clause(func_name):
    """Raise nodes in `assembly.<func_name>` with no `ev["clause"] = ...` assignment
    reachable before them in the same function, and no inline `"clause"` key."""
    tree = ast.parse(io.open(os.path.join(CORE, "assembly.py"), encoding="utf-8").read())
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == func_name)
    assigns = [n.lineno for n in ast.walk(fn)
               if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Subscript)
                       and isinstance(t.slice, ast.Constant) and t.slice.value == "clause"
                       for t in n.targets)]
    out = []
    for node in ast.walk(fn):
        if not isinstance(node, ast.Raise):
            continue
        src = ast.unparse(node)
        if "'clause'" in src or '"clause"' in src:
            continue
        if any(a < node.lineno for a in assigns):
            # An assignment exists earlier in the function; the raise still needs its OWN
            # clause set immediately before it, which the source check below enforces.
            pass
        out.append(node.lineno)
    return out, assigns


@pytest.mark.parametrize("func_name", THREE_GATES)
def test_every_raise_in_the_three_assembly_gates_can_name_its_clause(func_name):
    """THE OPERAND, over the whole population. On the base `gate_no_paid_nodes` set
    `ev["clause"]` at all SIX of its raises and the other fifteen raises in the file set
    none — so an ASSEMBLY or CASCADE halt on a payload run named the gate and the andon
    but not the clause, and a recurrence could not be fingerprinted.

    Keyed on the AST: a raise is covered when an `ev["clause"] = ...` assignment sits
    IMMEDIATELY above it in the same block, or when the raise's own evidence expression
    carries a `"clause"` key.
    """
    tree = ast.parse(io.open(os.path.join(CORE, "assembly.py"), encoding="utf-8").read())
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == func_name)

    uncovered = []

    def walk_block(body):
        for i, stmt in enumerate(body):
            if isinstance(stmt, ast.Raise):
                src = ast.unparse(stmt)
                inline = "'clause'" in src or '"clause"' in src
                prev = body[i - 1] if i else None
                preceded = (isinstance(prev, ast.Assign)
                            and any(isinstance(t, ast.Subscript)
                                    and isinstance(t.slice, ast.Constant)
                                    and t.slice.value == "clause"
                                    for t in prev.targets))
                if not (inline or preceded):
                    uncovered.append(stmt.lineno)
            for field in ("body", "orelse", "finalbody"):
                inner = getattr(stmt, field, None)
                if isinstance(inner, list):
                    walk_block(inner)
            for handler in getattr(stmt, "handlers", []) or []:
                walk_block(handler.body)

    walk_block(fn.body)
    assert uncovered == [], (func_name, uncovered)


def test_the_batch_gates_terminal_raise_carries_its_problems_as_clause_records():
    """The compounding half. `gate_batch_topology`'s terminal raise joined up to EIGHT
    structurally different failures into one prose string with no per-clause key — so the
    eight defects its message distinguishes were indistinguishable in its receipt.

    The message is unchanged (the same sentence, `'; '.join`); the evidence gains
    `problems` as `{clause, detail}` records and `ev["clause"]` is the first one.
    """
    graph = {
        "10": {"class_type": "BatchImagesNode", "inputs": {"images": [["1", 0]]}},
        "20": {"class_type": "CreateVideo", "inputs": {"images": ["999", 0]}},
        "30": {"class_type": "SaveVideo", "inputs": {"video": ["999", 0]}},
    }
    with pytest.raises(assembly.AssemblyGate) as exc:
        assembly.gate_batch_topology(graph, 1, "10", "20", "30", expected_sources=["1"])
    ev = exc.value.evidence
    assert isinstance(ev["problems"], list) and ev["problems"]
    assert all(set(p) == {"clause", "detail"} for p in ev["problems"]), ev["problems"]
    assert ev["clause"] == ev["problems"][0]["clause"]
    clauses = [p["clause"] for p in ev["problems"]]
    assert "bare_images_list" in clauses
    assert len(set(clauses)) > 1, clauses
    assert str(exc.value).endswith(ev["problems"][-1]["detail"])


def test_the_cascade_gates_terminal_raise_carries_its_problems_as_clause_records():
    """The sibling with the same shape, in the same file. Its terminal raise accumulated
    the same way and set no clause either."""
    graph = {
        "10": {"class_type": "BatchImagesNode", "inputs": {"images": [["1", 0]]}},
        "40": {"class_type": "BatchImagesNode", "inputs": {"images.image0": ["10", 0]}},
        "50": {"class_type": "CreateVideo", "inputs": {"images": ["999", 0]}},
        "60": {"class_type": "SaveVideo", "inputs": {"video": ["999", 0]}},
    }
    with pytest.raises(assembly.CascadeGate) as exc:
        assembly.gate_cascade_topology(graph, 1, ["10"], "40", "50", "60",
                                       group_size=1, expected_sources=["1"])
    ev = exc.value.evidence
    assert all(set(p) == {"clause", "detail"} for p in ev["problems"]), ev["problems"]
    assert ev["clause"] == ev["problems"][0]["clause"]


def test_the_family_census_over_the_three_gates_holds_the_shape_open_ended():
    """A census over the FAMILY, so a raise added tomorrow inherits the requirement: any
    gate in `assembly.py` that raises from more than one site must set a clause at every
    one of them. Derived from the module, never typed."""
    tree = ast.parse(io.open(os.path.join(CORE, "assembly.py"), encoding="utf-8").read())
    offenders = {}
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef) or not fn.name.startswith("gate_"):
            continue
        raises = [n for n in ast.walk(fn) if isinstance(n, ast.Raise)]
        if len(raises) < 2:
            continue
        assigns = {n.lineno for n in ast.walk(fn)
                   if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Subscript)
                           and isinstance(t.slice, ast.Constant)
                           and t.slice.value == "clause" for t in n.targets)}
        bad = []
        for r in raises:
            src = ast.unparse(r)
            if "'clause'" in src or '"clause"' in src:
                continue
            if any(a < r.lineno for a in assigns):
                continue
            bad.append(r.lineno)
        if bad:
            offenders[fn.name] = bad
    assert offenders == {}, offenders
