"""Tests for the two things E03 pins so its arms differ in exactly one variable.

Both exist for the same reason and it is worth stating once: B1 and B3 render the SAME
asset and are supposed to differ only in whether the timeline advances. Two derived
quantities quietly broke that — the camera fit (union of all frames vs the bind pose) and
the depth normalisation window (each shot's own z extent). Neither is a bug; both are
correct behaviour that becomes a confound the moment two arms are compared.

⚠ **Coverage boundary, stated rather than implied.** The camera-target *resolution* lives
in `BlenderBackend.prepare`, which needs bpy, so these tests cover its spec validation
only. That the pinned target actually reaches the camera was verified by measurement
instead: both E03 control manifests report `camera_target_source: "spec.camera.target
(pinned)"` and the same `camera_radius_resolved` to ten decimals.
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import stage_render  # noqa: E402
from armature_core import shotspec  # noqa: E402
from armature_core.errors import SpecError  # noqa: E402
from fake_backend import FakeBackend, make_spec  # noqa: E402


# ------------------------------------------------------------------ the depth window

def _spec(tmp_path, **over):
    spec = make_spec(tmp_path, count=5, channels=("depth", "mask"))
    spec.update(over)
    return spec


def test_default_is_per_shot_so_E01_and_E02_are_unchanged(tmp_path):
    manifest = stage_render.run_export(
        _spec(tmp_path), str(tmp_path / "run"),
        backend=FakeBackend(64, 96, z_near=2.0, z_far=5.0),
    )
    p3 = manifest["p3"]
    assert p3["window_source"] == "measured per-shot"
    assert p3["shot_z_min"] == p3["measured_z_min"] == pytest.approx(2.0)
    assert p3["shot_z_max"] == p3["measured_z_max"] == pytest.approx(5.0)


def test_a_pinned_window_overrides_the_measured_extent(tmp_path):
    manifest = stage_render.run_export(
        _spec(tmp_path, depth={"window": [1.0, 9.0]}), str(tmp_path / "run"),
        backend=FakeBackend(64, 96, z_near=2.0, z_far=5.0),
    )
    p3 = manifest["p3"]
    assert p3["window_source"] == "spec.depth.window (pinned)"
    assert (p3["shot_z_min"], p3["shot_z_max"]) == (1.0, 9.0)
    # The measured extent is still recorded — a pinned window must never hide what the
    # shot actually held.
    assert p3["measured_z_min"] == pytest.approx(2.0)
    assert p3["measured_z_max"] == pytest.approx(5.0)
    assert p3["measured_within_window"] is True


def test_two_shots_with_different_extents_get_the_SAME_pixels_under_one_window(tmp_path):
    """The property the pin exists for, measured end to end.

    Two runs of identical geometry whose shots have different z extents — exactly B1 vs B3.
    Under per-shot normalisation their depth PNGs differ; under one pinned window they are
    byte-identical.
    """
    # `breathe` widens the depth window as the shot proceeds and leaves frame 0 untouched,
    # so two runs differing only in breathe hold IDENTICAL geometry on frame 0 and different
    # shot extents — which is the B1/B3 shape. (Varying z_far instead would change the
    # scene's depth content, not just its extent, and the pin could not fix that.)
    def render(name, breathe, depth):
        stage_render.run_export(
            _spec(tmp_path, depth=depth), str(tmp_path / name),
            backend=FakeBackend(64, 96, z_near=2.0, z_far=5.0, breathe=breathe),
        )
        return (tmp_path / name / "depth_pershot" / "00000.png").read_bytes()

    still_ps = render("still_ps", 0.0, {"window": "per_shot"})
    moving_ps = render("moving_ps", 1.0, {"window": "per_shot"})
    assert still_ps != moving_ps, (
        "fixture is wrong: with per-shot normalisation the same frame-0 geometry must "
        "render differently under different shot extents, or there is nothing to pin"
    )

    win = {"window": [2.0, 8.0]}
    assert render("still_pin", 0.0, win) == render("moving_pin", 1.0, win)


def test_a_window_that_does_not_contain_the_shot_is_REPORTED_not_hidden(tmp_path):
    """Clipping is not raised on — a deliberately tight window is a legitimate creative
    choice — but it must be visible in the manifest rather than inferred from the pixels."""
    manifest = stage_render.run_export(
        _spec(tmp_path, depth={"window": [2.5, 3.0]}), str(tmp_path / "run"),
        backend=FakeBackend(64, 96, z_near=2.0, z_far=5.0),
    )
    assert manifest["p3"]["measured_within_window"] is False


@pytest.mark.parametrize("bad", [
    [3.0], [1, 2, 3], "auto", [3.0, 1.0], ["1", "2"], [True, False], None,
])
def test_a_malformed_window_raises(bad):
    with pytest.raises(SpecError, match="depth.window"):
        shotspec.normalise_spec({
            "spec_version": 1, "name": "x", "generator": "wan-vace",
            "asset": {"path": "x.glb"},
            "resolution": {"width": 480, "height": 832},
            "frames": {"count": 33, "fps": 16},
            "channels": ["depth"], "depth": {"window": bad},
        })


def test_an_inverted_window_raises_before_it_collapses_the_normalisation():
    with pytest.raises(SpecError, match="z_min must be below"):
        shotspec.normalise_spec({
            "spec_version": 1, "name": "x", "generator": "wan-vace",
            "asset": {"path": "x.glb"},
            "resolution": {"width": 480, "height": 832},
            "frames": {"count": 33, "fps": 16},
            "channels": ["depth"], "depth": {"window": [5.0, 5.0]},
        })


# ------------------------------------------------------------------ the camera target

def _cam_spec(target):
    return shotspec.normalise_spec({
        "spec_version": 1, "name": "x", "generator": "wan-vace",
        "asset": {"path": "x.glb"},
        "resolution": {"width": 480, "height": 832},
        "frames": {"count": 33, "fps": 16},
        "channels": ["depth"], "camera": {"target": target},
    })


def test_bbox_center_remains_the_default():
    assert shotspec.DEFAULTS["camera"]["target"] == "bbox_center"
    assert _cam_spec("bbox_center")["camera"]["target"] == "bbox_center"


def test_a_numeric_target_is_accepted():
    assert _cam_spec([0.0, 0.0, 0.56])["camera"]["target"] == [0.0, 0.0, 0.56]


@pytest.mark.parametrize("bad", [
    [0.0, 0.0], [0.0, 0.0, 0.0, 0.0], "centre", [0.0, 0.0, "z"], [True, False, True], 0.56,
])
def test_a_malformed_target_raises(bad):
    with pytest.raises(SpecError, match="camera.target"):
        _cam_spec(bad)


# ------------------------------------------------------- preview_walk resolves the shot
#
# F-b97fba5b. `preview_walk.py:93-94` re-derived the two camera fields instead of reading
# them the way `stage_render` does:
#
#     target = Vector(c["target"]) if c["target"] != "bbox_center" else Vector((0, 0, 0))
#     radius = float(c["radius"])
#
# `bbox_center` is the DEFAULT (`shotspec.DEFAULTS["camera"]["target"]`) and it resolved to
# the WORLD ORIGIN, not the subject; `radius` is `"auto"` by default and `float("auto")`
# raises. So the one artifact whose stated purpose is "so the performance can be inspected
# before a credit is spent" either crashed on the default spec or previewed a shot aimed at
# the origin — while the module docstring claims "one implementation, so the preview cannot
# drift from the render."
#
# `stage_render.BlenderBackend.prepare` needs bpy, so the tie here is the one the file's own
# coverage-boundary note already uses: preview_walk must call the SAME helpers with the SAME
# arguments (`bs.auto_radius(sphere_r, lens, sensor, width, height, fit_margin)`, stage_render
# lines 168-170) and report the SAME source strings.

import ast

from blender_stub import load_tool, read_source

SPECS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "specs")
COMMITTED_SPECS = sorted(f for f in os.listdir(SPECS_DIR) if f.endswith(".json"))

#: A subject that is nowhere near the origin, so "resolved to (0,0,0)" is distinguishable
#: from "resolved to the measured centre".
BOUNDS = (np.array([1.5, -2.25, 0.875]), np.array([0.3, 0.3, 0.9]), 1.125)


def _shot_specs():
    """The committed specs that describe a render (a camera and a resolution)."""
    out = []
    for fn in COMMITTED_SPECS:
        try:
            spec = shotspec.load_spec(os.path.join(SPECS_DIR, fn))
        except SpecError:
            continue
        if "camera" in spec and "resolution" in spec:
            out.append((fn, spec))
    return out


def test_the_committed_shot_specs_still_exercise_both_defaults():
    """If every committed spec pinned both fields this check would prove nothing — E03 is
    the only one that does, and it is not the population."""
    specs = _shot_specs()
    assert specs, COMMITTED_SPECS
    assert any(s["camera"]["target"] == "bbox_center" for _, s in specs)
    assert any(s["camera"]["radius"] == "auto" for _, s in specs)


@pytest.mark.parametrize("filename", [fn for fn, _ in _shot_specs()])
def test_preview_walk_resolves_every_committed_spec_the_way_stage_render_does(filename):
    pw = load_tool("preview_walk.py")
    bs = pw.blender_scene          # imported under the bpy stub; auto_radius is pure math
    spec = shotspec.load_spec(os.path.join(SPECS_DIR, filename))
    c = spec["camera"]
    w, h = int(spec["resolution"]["width"]), int(spec["resolution"]["height"])

    got = pw.resolve_camera(spec, BOUNDS, w, h)

    if c["target"] == "bbox_center":
        assert tuple(got["target"]) == tuple(float(v) for v in BOUNDS[0])
        assert tuple(got["target"]) != (0.0, 0.0, 0.0)
        assert got["target_source"] == "measured bbox centre"
    else:
        assert tuple(got["target"]) == tuple(float(v) for v in c["target"])
        assert got["target_source"] == "spec.camera.target (pinned)"

    if c["radius"] == "auto":
        want = bs.auto_radius(BOUNDS[2], c["lens_mm"], c["sensor_mm"], w, h,
                              c["fit_margin"])
        assert got["radius"] == pytest.approx(want, rel=0, abs=0)
        assert got["radius_source"].startswith("auto")
    else:
        assert got["radius"] == float(c["radius"])
        assert got["radius_source"] == "spec.camera.radius (pinned)"


def test_preview_walk_reports_the_same_source_vocabulary_stage_render_writes():
    """The two strings are the record a reader compares a preview against; if they drift
    the two artifacts stop being comparable at all."""
    sr = read_source("stage_render.py")
    pw = read_source("preview_walk.py")
    for phrase in ('"measured bbox centre"', '"spec.camera.target (pinned)"'):
        assert phrase in sr, phrase
        assert phrase in pw, phrase


def test_the_old_two_lines_disagree_with_the_resolver_on_the_default_spec():
    """The red direction, pinned so this cannot become a check that passes on anything.

    The superseded expressions are reproduced here VERBATIM and must fail or disagree on a
    spec carrying the shotspec defaults."""
    pw = load_tool("preview_walk.py")
    spec = shotspec.load_spec(os.path.join(SPECS_DIR, "E01-anchor.json"))
    c = spec["camera"]
    assert c["target"] == "bbox_center" and c["radius"] == "auto"

    old_target = tuple(c["target"]) if c["target"] != "bbox_center" else (0.0, 0.0, 0.0)
    with pytest.raises(ValueError):
        float(c["radius"])                      # `float("auto")` — the crash

    got = pw.resolve_camera(spec, BOUNDS, int(spec["resolution"]["width"]),
                            int(spec["resolution"]["height"]))
    assert tuple(got["target"]) != old_target


def test_the_preview_counts_its_frames_by_name_not_by_extension():
    """`preview_walk.py:114` counted `*.png` in the output directory with a bare listdir.
    Its population must be the plan — `shotspec.frame_names` — so a stray file cannot make
    a short render look complete and a misnamed frame cannot hide."""
    src = read_source("preview_walk.py")
    assert 'os.listdir(a.out) if f.endswith(".png")' not in src, (
        "the completeness check still counts whatever *.png happens to be in the output "
        "directory: a stray makes a short render look complete, and the check cannot name "
        "which frame is missing")
    tree = ast.parse(src)
    calls = [n for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr == "frame_names"]
    assert calls, "preview_walk does not build its population from shotspec.frame_names"


# ===========================================================================================
# Wave 8 (appended block). F-ed1dfdb5: the frame-completeness andon counts the PLAN.
#
# `render_performer.py:321` counted `os.listdir(out)` and compared the count to `count`,
# while `paths` -- the list the render had just written against -- sat two lines above and
# was passed straight into `gate_coverage`. Measured on those two lines verbatim: a
# 16-frame run into an `--out` already holding a stale `00099.png`, with `00007.png` never
# written, gives `len(written) == 16 == count` and the gate does NOT fire; and a 16-frame
# run into a directory holding 33 stale frames prints "wrote 33 frames" about a run that
# wrote 16. A zero-byte frame passed either way. `preview_walk.py:167` already carried the
# corrected shape in the same repo, under a comment naming this exact failure.
# ===========================================================================================

import ast as _ast  # noqa: E402

from blender_stub import read_source as _read_source  # noqa: E402


def _completeness_population(filename):
    """Which name the completeness andon counts over, read off the AST."""
    tree = _ast.parse(_read_source(filename))
    fn = next(n for n in _ast.walk(tree)
              if isinstance(n, _ast.FunctionDef) and n.name == "main")
    listdirs = [n.lineno for n in _ast.walk(fn)
                if isinstance(n, _ast.Call) and isinstance(n.func, _ast.Attribute)
                and n.func.attr == "listdir"]
    isfiles = [n.lineno for n in _ast.walk(fn)
               if isinstance(n, _ast.Call) and isinstance(n.func, _ast.Attribute)
               and n.func.attr == "isfile"]
    getsizes = [n.lineno for n in _ast.walk(fn)
                if isinstance(n, _ast.Call) and isinstance(n.func, _ast.Attribute)
                and n.func.attr == "getsize"]
    return listdirs, isfiles, getsizes


def _completeness_bindings(filename):
    """`{name: the expression bound to it}` for the three completeness lists in `main`.

    AST, not a substring over source (wave 10, F-18061bcb). The pin here used to be the
    exact expression `missing = [p for p in paths if not os.path.isfile(p)]`, which is
    wrong in BOTH directions: inserting a space or wrapping the line turns it red with the
    behaviour unchanged, and a comment carrying the same text turns it green with the
    behaviour broken.
    """
    tree = _ast.parse(_read_source(filename))
    fn = next(n for n in _ast.walk(tree)
              if isinstance(n, _ast.FunctionDef) and n.name == "main")
    out = {}
    for node in _ast.walk(fn):
        if not isinstance(node, _ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, _ast.Name) and target.id in ("missing", "empty", "strays"):
            out[target.id] = node.value
    return out


def _iterated_name(comp):
    """The NAME a comprehension iterates, or None."""
    if not isinstance(comp, (_ast.ListComp, _ast.SetComp, _ast.GeneratorExp)):
        return None
    src = comp.generators[0].iter
    return src.id if isinstance(src, _ast.Name) else None


def test_render_performer_counts_the_plan_and_not_the_directory():
    listdirs, isfiles, getsizes = _completeness_population("render_performer.py")
    assert isfiles, "no per-planned-frame existence check"
    assert getsizes, "a zero-byte frame still passes: nothing reads getsize"

    bound = _completeness_bindings("render_performer.py")
    assert set(bound) == {"missing", "empty", "strays"}, sorted(bound)

    # `missing` is derived from the PLANNED paths, not from a directory listing...
    assert _iterated_name(bound["missing"]) == "paths", _ast.unparse(bound["missing"])
    # ...and its condition is the per-path existence check, read as STRUCTURE rather than
    # as text, so whitespace moves freely and a comment cannot satisfy it.
    condition = bound["missing"].generators[0].ifs
    assert len(condition) == 1
    assert isinstance(condition[0], _ast.UnaryOp) and isinstance(condition[0].op, _ast.Not)
    call = condition[0].operand
    assert isinstance(call, _ast.Call) and call.func.attr == "isfile", _ast.unparse(call)

    # the bare listdir census may not be the andon's population
    for name in ("missing", "empty"):
        assert "listdir" not in _ast.unparse(bound[name]), (name, _ast.unparse(bound[name]))


def test_the_stray_is_reported_as_a_stray_and_not_as_a_success():
    """`listdir` is still called -- to REPORT unexpected files -- and that is the shape
    `preview_walk` uses. The difference is which list the verdict is computed over."""
    listdirs, _, _ = _completeness_population("render_performer.py")
    assert listdirs, "strays are no longer reported at all"
    bound = _completeness_bindings("render_performer.py")
    assert "listdir" in _ast.unparse(bound["strays"]), _ast.unparse(bound["strays"])
    # the strays reach the RECORD under their own key -- read off the dict literals in
    # `main`, not off the file's text, so a comment naming the key cannot satisfy it
    tree = _ast.parse(_read_source("render_performer.py"))
    fn = next(n for n in _ast.walk(tree)
              if isinstance(n, _ast.FunctionDef) and n.name == "main")
    keys = {k.value for node in _ast.walk(fn) if isinstance(node, _ast.Dict)
            for k in node.keys
            if isinstance(k, _ast.Constant) and isinstance(k.value, str)}
    assert "unexpected_files_in_out_dir" in keys, sorted(keys)


def test_both_renderers_that_write_a_frame_sequence_agree_on_the_shape():
    """The family: `preview_walk.py` and `render_performer.py`. One shape, so a fix to one
    is a fix to both."""
    for filename in ("preview_walk.py", "render_performer.py"):
        # `assert "missing" in src and "empty" in src and "strays" in src` stood here:
        # three ordinary English words, each satisfied by a docstring or a comment, none
        # of which proves any of the three states is COMPUTED (F-18061bcb).
        # `render_performer` alone carries the word "empty" nine times in prose. The three
        # names must be BOUND in `main`, each to a comprehension, and the two derived from
        # the plan must not be computed off a directory listing.
        bound = _completeness_bindings(filename)
        assert set(bound) == {"missing", "empty", "strays"}, (filename, sorted(bound))
        for name in ("missing", "empty"):
            assert isinstance(bound[name], (_ast.ListComp, _ast.SetComp)), (
                filename, name, _ast.unparse(bound[name]))
            assert "listdir" not in _ast.unparse(bound[name]), (filename, name)
        assert "listdir" in _ast.unparse(bound["strays"]), filename
        _, isfiles, getsizes = _completeness_population(filename)
        assert isfiles and getsizes, filename


def test_the_completeness_binding_walk_cannot_be_satisfied_by_prose(tmp_path):
    """Rule 3 on the walk itself: the shape the old substring pin accepted must now fail.

    A module whose `main` MENTIONS all three words in prose and binds none of them reads
    as empty here, where the retired pin read green.
    """
    probe = tmp_path / "prose_only.py"
    probe.write_text(
        "def main():\n"
        "    # missing, empty and strays are all reported here, honest\n"
        "    note = 'the missing frames, the empty ones, and any strays'\n"
        "    return note\n", encoding="utf-8")
    tree = _ast.parse(probe.read_text(encoding="utf-8"))
    fn = next(n for n in _ast.walk(tree)
              if isinstance(n, _ast.FunctionDef) and n.name == "main")
    bound = {t.id for node in _ast.walk(fn) if isinstance(node, _ast.Assign)
             for t in node.targets if isinstance(t, _ast.Name)}
    assert bound & {"missing", "empty", "strays"} == set()
    src = probe.read_text(encoding="utf-8")
    assert "missing" in src and "empty" in src and "strays" in src, (
        "the retired pin would have passed this module")


def test_gate_coverage_may_be_tightened_and_may_not_be_loosened():
    """ROUTED from core-gates' threshold-argument family (the shape they applied to four
    rig gates): a tolerance the caller can LOOSEN is a gate the caller can switch off one
    keyword at a time, with the record still saying it ran and passed.

    RE-DERIVED wave 22 (instruments, F-f25774c2), branch-local: the inline comparison is
    now `armature_core.parts.tightened`, the repo's ONE implementation of it, so the
    sentence a refusal quotes is that helper's ("It may only TIGHTEN: a tolerance the
    caller supplies is a tolerance the caller can loosen...") rather than this module's
    own copy of the same paragraph. The property is unchanged and TWO more operands are
    asserted below, which the inline `min_frac > MIN_SUBJECT_FRAC` could not refuse at
    all: `nan` and `-1.0` both walk past a bare `>` comparison, and with a NaN floor this
    gate's own per-frame clause (`worst["frac"] < min_frac`) is False for every frame, so
    it returned its PASS verdict over a set of frames with nobody in them."""
    import pytest as _pytest
    from armature_core.errors import GateFailure
    from blender_stub import load_tool

    rp = load_tool("render_performer.py")
    with _pytest.raises(GateFailure, match=r"It may only TIGHTEN"):
        rp.gate_coverage([], "plate.png", min_frac=rp.MIN_SUBJECT_FRAC * 10)
    for bad in (float("nan"), float("inf"), -1.0):
        with _pytest.raises(rp.RenderGate) as exc:
            rp.gate_coverage([], "plate.png", min_frac=bad)
        assert exc.value.evidence["gate"] == rp.RenderGate.gate
