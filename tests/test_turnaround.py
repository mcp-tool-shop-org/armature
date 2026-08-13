"""The turnaround set's andons — S03 Task A.

The fixture question for Gate ALPHA is answerable from the rig rather than imagined: the
set this gate exists to have caught is on disk. `E:\\AI\\training\\facet_E33\\turn_final\\`
is eight RGBA PNGs, 352x1024, whose alpha extrema are **(255, 255) on all eight** with a
flat grey void baked into the RGB. Those literal numbers are the first fixture below.

`test_the_extrema_only_check_would_have_passed_this` is the load-bearing one. The dispatch
states the criterion as "alpha extrema != (255, 255)", which is the right description of
the defect that was found and an incomplete check: a view that is semi-transparent
*everywhere* — nothing solid rendered into it at all — has extrema (0, 200) and sails
through. That test pins why the gate binds both directions rather than the one.
"""

import os
import re
import subprocess
import sys
import textwrap

import pytest

from armature_core import turnaround as TA
from conftest import TOOLS

# The measured `turn_final` defect, in the units the gate takes.
FLAT_ALPHA_EXTREMA = (255, 255)
FLAT_TRANSPARENT_FRACTION = 0.0


# ------------------------------------------------------------------ the orbit plan


def _blender_scene_orbit_azimuth():
    """`blender_scene.orbit_azimuth`, executed out of its own source text.

    `turnaround.orbit_azimuths` restates that function's convention because
    `blender_scene` imports bpy and `turnaround` must not. Copying a convention is how
    two modules quietly disagree about which way a camera goes, so this lifts the real
    function out of the real file and runs it — the duplication is checked, not trusted.
    """
    src = open(os.path.join(TOOLS, "armature_core", "blender_scene.py"),
               encoding="utf-8").read()
    m = re.search(r"^def orbit_azimuth\(.*?(?=^def |\Z)", src, re.S | re.M)
    assert m, "orbit_azimuth is no longer defined in blender_scene.py"
    ns = {}
    exec(compile(m.group(0), "blender_scene.orbit_azimuth", "exec"), ns)
    return ns["orbit_azimuth"]


def test_orbit_plan_agrees_with_the_blender_side_convention():
    ref = _blender_scene_orbit_azimuth()
    got = TA.orbit_azimuths(8, 270.0, 360.0)
    want = [ref(i, 8, 270.0, 360.0) for i in range(8)]
    assert got == pytest.approx(want)


def test_a_closed_sweep_does_not_render_view_zero_twice():
    """`sweep` is the angle of the closed path: view `n` would coincide with view 0.

    Divide by `count - 1` instead of `count` — the ordinary off-by-one for a range of
    angles — and the eighth view is the front view again, 45 degrees of the turnaround
    are never rendered, and the set still has eight distinct-looking files in it.
    """
    az = TA.orbit_azimuths(8, 270.0, 360.0)
    assert az[0] == 270.0
    assert az[1] - az[0] == pytest.approx(45.0)
    assert (az[-1] - az[0]) % 360.0 == pytest.approx(315.0)
    assert len({a % 360.0 for a in az}) == 8


def test_a_turnaround_of_no_views_raises():
    with pytest.raises(TA.TurnaroundGate):
        TA.orbit_azimuths(0, 270.0, 360.0)


# ------------------------------------------------------------------ Gate ALPHA


def test_an_authored_view_passes_and_reports_its_numbers():
    ev = TA.gate_view_alpha(3, 0, 255, 0.7412, path="turn_3.png")
    assert ev["alpha_extrema"] == [0, 255]
    assert ev["transparent_fraction"] == pytest.approx(0.7412)
    assert ev["opaque_fraction"] == pytest.approx(0.2588)
    assert "authored RGBA" in ev["verdict"]


def test_the_defect_this_gate_exists_for():
    """`turn_final`'s measured numbers: a baked grey void wearing an alpha channel."""
    with pytest.raises(TA.TurnaroundAlphaGate) as exc:
        TA.gate_view_alpha(0, *FLAT_ALPHA_EXTREMA,
                           transparent_fraction=FLAT_TRANSPARENT_FRACTION)
    msg = str(exc.value)
    assert "NO pixel is transparent" in msg
    assert "baked void with a fourth channel" in msg
    assert exc.value.evidence["alpha_extrema"] == [255, 255]
    assert exc.value.gate == "ALPHA"


def test_the_extrema_only_check_would_have_passed_this():
    """A view nobody is in, with a richly varied alpha channel and no opaque pixel.

    Extrema (0, 200) is not (255, 255), so the criterion as stated in prose admits it.
    Every other check admits it too: the file opens, it is 352x1024, it is not empty, its
    transparent fraction is a perfectly healthy number. What is wrong is that the subject
    never rendered — a material that lost its opacity, a mesh hidden from the render, a
    camera pointed at nothing. This is why the gate binds `alpha_max` as well.
    """
    with pytest.raises(TA.TurnaroundAlphaGate) as exc:
        TA.gate_view_alpha(5, 0, 200, transparent_fraction=0.61)
    assert "NO pixel is opaque" in str(exc.value)
    assert exc.value.evidence["alpha_extrema"] == [0, 200]


def test_the_boundary_between_them_is_one_count():
    """(254, 255) passes, (255, 255) does not. The gate is on the extremum, not a
    threshold somebody could move by a count when they did not like the result."""
    assert TA.gate_view_alpha(1, 254, 255, 0.0001)["verdict"]
    with pytest.raises(TA.TurnaroundAlphaGate):
        TA.gate_view_alpha(1, 255, 255, 0.0)


def test_a_fully_transparent_view_raises_on_the_opaque_clause():
    with pytest.raises(TA.TurnaroundAlphaGate) as exc:
        TA.gate_view_alpha(2, 0, 0, transparent_fraction=1.0)
    assert "NO pixel is opaque" in str(exc.value)


def test_the_opaque_fraction_is_reported_and_never_gated():
    """A magnitude with no calibrated threshold on this rig is a diagnostic, not a gate.

    Four opaque pixels in a 352x1024 frame is a warning for the Director's eye; it is not
    a number this gate may invent a pass condition around.
    """
    ev = TA.gate_view_alpha(0, 0, 255, transparent_fraction=0.999989)
    assert ev["opaque_fraction"] == pytest.approx(1.1e-5, rel=0.05)
    assert "authored RGBA" in ev["verdict"]


# ------------------------------------------------------------------ Gate TURN


def _views(digests):
    return [{"view": i, "sha256": d} for i, d in enumerate(digests)]


def test_a_whole_distinct_set_passes():
    ev = TA.gate_set_distinct(_views([f"{i:064x}" for i in range(8)]), 8)
    assert ev["distinct_sha256"] == 8
    assert "8 distinct views" in ev["verdict"]


def test_a_short_set_raises():
    with pytest.raises(TA.TurnaroundGate) as exc:
        TA.gate_set_distinct(_views([f"{i:064x}" for i in range(7)]), 8)
    assert "carries 7 view(s), not 8" in str(exc.value)


def test_the_camera_that_never_moved():
    """The defect Gate TURN exists for, and it is silent everywhere else.

    Assign `cam.matrix_world` once outside the render loop — or hand every view the same
    azimuth — and the run writes eight well-formed RGBA files. Every per-view alpha gate
    passes on every one of them, Gate WHOLE passes on every one of them, the count is
    right, and the deliverable is eight copies of the front view. Nothing else in this
    tool compares the views to each other.
    """
    with pytest.raises(TA.TurnaroundGate) as exc:
        TA.gate_set_distinct(_views(["ab" * 32] * 8), 8)
    msg = str(exc.value)
    assert "byte-identical to another view" in msg
    assert "the camera did not move between them" in msg
    assert exc.value.evidence["distinct_sha256"] == 1


def test_one_duplicated_pair_among_distinct_views_still_raises():
    """The partial case: seven azimuths right and one repeated. A check that only fired
    when the WHOLE set collapsed would pass this."""
    digests = [f"{i:064x}" for i in range(7)] + [f"{3:064x}"]
    with pytest.raises(TA.TurnaroundGate) as exc:
        TA.gate_set_distinct(_views(digests), 8)
    assert exc.value.evidence["distinct_sha256"] == 7


def test_an_unhashed_view_raises_rather_than_being_skipped():
    """A record with no digest cannot be compared. Dropping it from the comparison would
    make the duplicate check quietly weaker exactly when hashing had failed."""
    views = _views([f"{i:064x}" for i in range(7)])
    views.append({"view": 7})
    with pytest.raises(TA.TurnaroundGate) as exc:
        TA.gate_set_distinct(views, 8)
    assert "no sha256" in str(exc.value)


# ------------------------------------------------- and none of them is an `assert`

PROBE = textwrap.dedent(
    """
    import json, sys
    sys.path.insert(0, sys.argv[1])
    from armature_core import turnaround as TA

    cases = {
        "alpha_flat_255":   lambda: TA.gate_view_alpha(0, 255, 255, 0.0),
        "alpha_none_opaque": lambda: TA.gate_view_alpha(0, 0, 200, 0.61),
        "alpha_all_clear":  lambda: TA.gate_view_alpha(0, 0, 0, 1.0),
        "turn_short":       lambda: TA.gate_set_distinct(
                                [{"view": i, "sha256": "%064x" % i} for i in range(7)], 8),
        "turn_duplicate":   lambda: TA.gate_set_distinct(
                                [{"view": i, "sha256": "ab" * 32} for i in range(8)], 8),
        "turn_unhashed":    lambda: TA.gate_set_distinct([{"view": 0}], 1),
        "orbit_no_views":   lambda: TA.orbit_azimuths(0, 270.0, 360.0),
        "crop_left":        lambda: TA.gate_view_crop(0, (0, 90, 980, 940), 1024, 1024),
        "crop_last_index":  lambda: TA.gate_view_crop(0, (40, 90, 1023, 940), 1024, 1024),
        "crop_empty_cell":  lambda: TA.gate_view_crop(0, None, 1024, 1024),
    }
    # S05's plan refusals are deliberately NOT GateFailures, so they get their own catch
    # rather than a widened one — widening this to ArmatureError would silently turn every
    # WRONG_ERROR above into a pass for any error in the same family.
    plan_cases = {
        "pin_on_perspective": lambda: TA.projection_plan(False, 50.0, 36.0,
                                                         ortho_scale_pin=1.2),
        "pin_zero":           lambda: TA.projection_plan(True, 50.0, 36.0,
                                                         ortho_scale_pin=0.0),
        "pin_negative":       lambda: TA.projection_plan(True, 50.0, 36.0,
                                                         ortho_scale_pin=-1.0),
        "pin_nan":            lambda: TA.projection_plan(True, 50.0, 36.0,
                                                         ortho_scale_pin=float("nan")),
        "pin_inf":            lambda: TA.projection_plan(True, 50.0, 36.0,
                                                         ortho_scale_pin=float("inf")),
    }

    out = {"optimize_flag": sys.flags.optimize, "asserts_active": __debug__,
           "raised": {}, "plan_raised": {}}
    for name, fn in cases.items():
        try:
            fn()
            out["raised"][name] = "NO_RAISE"
        except TA.GateFailure:
            out["raised"][name] = "RAISED"
        except BaseException as exc:
            out["raised"][name] = "WRONG_ERROR:" + type(exc).__name__
    for name, fn in plan_cases.items():
        try:
            fn()
            out["plan_raised"][name] = "NO_RAISE"
        except TA.TurnaroundPlanRefusal:
            out["plan_raised"][name] = "RAISED"
        except BaseException as exc:
            out["plan_raised"][name] = "WRONG_ERROR:" + type(exc).__name__
    print("TURNAROUND " + json.dumps(out))
    """
)


def _run(tmp_path, *, flag=False, env_var=False):
    script = tmp_path / f"ta_probe_{int(flag)}_{int(env_var)}.py"
    script.write_text(PROBE, encoding="utf-8")
    env = dict(os.environ)
    env.pop("PYTHONOPTIMIZE", None)
    if env_var:
        env["PYTHONOPTIMIZE"] = "1"
    cmd = [sys.executable] + (["-O"] if flag else []) + [str(script), TOOLS]
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=180)
    assert proc.returncode == 0, proc.stderr
    line = [l for l in proc.stdout.splitlines() if l.startswith("TURNAROUND ")]
    assert line, proc.stdout + proc.stderr
    import json

    return json.loads(line[-1][len("TURNAROUND "):])


@pytest.mark.parametrize(
    "flag,env_var,label",
    [(False, False, "plain"), (True, False, "-O"), (False, True, "PYTHONOPTIMIZE=1")],
)
def test_every_turnaround_andon_survives_optimization(tmp_path, flag, env_var, label):
    """87 of facet's ANDONs turned out to be removable by an environment variable."""
    res = _run(tmp_path, flag=flag, env_var=env_var)
    for name, outcome in res["raised"].items():
        assert outcome == "RAISED", f"{label}/{name}: {outcome}"


@pytest.mark.parametrize(
    "flag,env_var,label",
    [(False, False, "plain"), (True, False, "-O"), (False, True, "PYTHONOPTIMIZE=1")],
)
def test_the_plan_refusals_survive_optimization(tmp_path, flag, env_var, label):
    """S05. A refusal that an environment variable deletes is not a refusal, and a pin
    silently dropped under `-O` renders a roster on per-character scales with every gate
    green — the exact failure the pin exists to prevent, reintroduced by a flag."""
    res = _run(tmp_path, flag=flag, env_var=env_var)
    assert res["plan_raised"], "the probe reported no plan cases at all"
    for name, outcome in res["plan_raised"].items():
        assert outcome == "RAISED", f"{label}/{name}: {outcome}"


def test_the_optimization_actually_took_effect(tmp_path):
    """A green sweep under an -O that never applied is a check that cannot fail."""
    assert _run(tmp_path, flag=False)["asserts_active"] is True
    assert _run(tmp_path, flag=True)["asserts_active"] is False
    assert _run(tmp_path, env_var=True)["asserts_active"] is False
