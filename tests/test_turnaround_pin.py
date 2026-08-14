"""S05 — the roster scale pin: used verbatim, recorded as pinned, refused where it lies.

Four properties, each silent everywhere else.

**Verbatim means the same double, not a close one.** The pin's whole value is that one
recorded number governs every run of a cast, so the halfling and the nine-foot brute are
drawn against the same world span. A tool that rounded it, or that re-solved from it as a
starting point, would put each character back on his own private scale — and every cell
would still be beautifully framed, every gate green, the sheet perfectly plausible. So the
float is compared for exact equality, and the recorded value is checked to retype into
itself, because retyping is how the next character in the roster is actually rendered.

**The solved path is untouched when no pin is given.** Same doctrine as S04's flag and for
the same reason: the claim is made a property of `projection_plan`, one importable object,
rather than of a careful reading of the render loop. The default-path test goes through the
REAL parser, so flipping a default cannot leave it green.

**A `height_frac` beside a pinned scale would describe a fit that never happened.** The
pre-S05 manifest keyed its solve record off `ortho_scale is None`, which a pinned run does
not satisfy — so the natural non-edit writes a full solve record naming a target height the
run never targeted, in exactly the shape a real fit is described in. That is why
`ortho_scale_record` exists outside `main`: the property that matters is which block is
ABSENT, and absence inside a Blender-only function is untestable.

**A pin that cannot mean anything is refused twice.** At the parser, where a person typed
it; and in the plan, for every caller who never reaches the parser — which is the caller
this repo keeps commissioning, since `projection_plan` is the documented branch object. A
pin silently dropped on the perspective path is a roster rendered per-character with
nothing anywhere reporting it.
"""

import json
import math
import sys

import pytest

from armature_core import turnaround as TA


#: S04's measured solved scale for the proof GLB at the Task-C preset, and the two S05
#: arms derived from it. Written out at full precision on purpose: a pin truncated to six
#: places is a different world span, and this file is where that has to be visible.
S04_SOLVED = 1.1235359256161628
ROOMY = 1.25 * S04_SOLVED
TIGHT = 0.80 * S04_SOLVED


def _parse(rt, *args):
    """`parse_args` through the real parser, with the `blender -b -P ... --` preamble."""
    argv = sys.argv
    sys.argv = ["blender", "--"] + list(args)
    try:
        return rt.parse_args()
    finally:
        sys.argv = argv


# ------------------------------------------------------------------ the parser refuses


def test_a_pin_without_the_ortho_flag_is_refused(rt):
    """There is no shared world span on the perspective path — what is shared there is the
    radius. Accepting the pin would render a well-formed perspective turnaround that
    silently ignored the one number the run was pinned on, and record no scale at all."""
    with pytest.raises(SystemExit) as exc:
        _parse(rt, "--glb=x.glb", "--out=y", "--ortho-scale=1.2")
    assert exc.value.code == 2


@pytest.mark.parametrize("bad", ["0", "0.0", "-1.5", "nan", "inf", "-inf"])
def test_a_pin_that_is_not_a_finite_positive_span_is_refused(rt, bad):
    """Zero and negative collapse every point onto the frame centre; nan and inf send them
    nowhere at all. Every one of those still writes a well-formed, correctly-sized RGBA PNG
    that Gate ALPHA's transparent clause would not even see as empty in every case.

    `ortho_half_spans` refuses `<= 0` downstream, so the two that only this check catches
    are `nan` (which compares False against every bound) and `inf`."""
    with pytest.raises(SystemExit) as exc:
        _parse(rt, "--glb=x.glb", "--out=y", "--ortho", f"--ortho-scale={bad}")
    assert exc.value.code == 2


def test_a_good_pin_parses_and_keeps_the_text_it_was_typed_as(rt):
    a = _parse(rt, "--glb=x.glb", "--out=y", "--ortho", f"--ortho-scale={S04_SOLVED!r}")
    assert a.ortho is True
    assert a.ortho_scale == S04_SOLVED
    assert a.ortho_scale_text == repr(S04_SOLVED)


def test_the_default_run_carries_no_pin_at_all(rt):
    a = _parse(rt, "--glb=x.glb", "--out=y")
    assert a.ortho_scale is None
    assert a.ortho_scale_text is None


@pytest.mark.parametrize("argv,want", [
    (["--ortho", "--ortho-scale=1.25"], "1.25"),
    (["--ortho", "--ortho-scale", "1.25"], "1.25"),
    (["--ortho"], None),
    (["--ortho-scaled=9"], None),                 # a longer flag must not be mistaken
])
def test_the_typed_text_is_recovered_from_either_argument_form(rt, argv, want):
    """`--key=value` is this repo's form (argparse eats leading minus signs), but argparse
    accepts the separated form too and a manifest that recorded `None` for a run that was
    pinned would be silent about the only thing a reader retypes."""
    assert rt._pinned_text(argv) == want


# ------------------------------------------------------- the plan refuses the same two


def test_the_plan_refuses_a_pin_on_the_perspective_path(rt):
    """The parser bounds callers who come through the command line. This bounds the caller
    who imports `projection_plan` — the branch object this repo keeps building tools on."""
    with pytest.raises(TA.TurnaroundPlanRefusal) as exc:
        TA.projection_plan(False, 50.0, 36.0, ortho_scale_pin=1.2)
    assert "PERSPECTIVE" in str(exc.value)


@pytest.mark.parametrize("bad", [0.0, -1.0, float("nan"), float("inf")])
def test_the_plan_refuses_a_pin_that_is_not_a_finite_positive_span(bad):
    with pytest.raises(TA.TurnaroundPlanRefusal):
        TA.projection_plan(True, 50.0, 36.0, ortho_scale_pin=bad)


def test_the_plan_refusal_is_not_a_gate_failure():
    """It refuses to compose a plan before a camera exists; the four gates judge a rendered
    artifact. Making it a `GateFailure` would put a fifth andon into the vocabulary the
    manifests and reports use for measured views, and a report would then name a gate that
    never looked at a picture."""
    assert not issubclass(TA.TurnaroundPlanRefusal, TA.GateFailure)
    assert issubclass(TA.TurnaroundPlanRefusal, TA.ArmatureError)


# ------------------------------------------------------------------ verbatim, and shared


@pytest.mark.parametrize("pin", [
    S04_SOLVED, ROOMY, TIGHT,
    1e-6, 1234.5678901234567, 0.1 + 0.2,          # the classic non-representable sum
])
def test_the_pin_reaches_the_plan_as_the_identical_double(pin):
    """Exact equality, not `approx`. A pin that arrived a few ULPs away would draw a
    roster's characters at scales that differ by less than a pixel — invisible on any one
    sheet and wrong in exactly the way the pin exists to prevent."""
    plan = TA.projection_plan(True, 50.0, 36.0, ortho_scale_pin=pin)
    assert plan["ortho_scale_pin"] == pin
    assert plan["ortho_scale_source"] == TA.PINNED


@pytest.mark.parametrize("pin", [S04_SOLVED, ROOMY, TIGHT, 0.1 + 0.2])
def test_a_recorded_pin_retypes_into_the_same_double(pin):
    """The recipe law, as the mechanical property behind it. `json.dump` writes a float via
    `repr`, and `float(repr(x)) == x` for every finite double — so the number in a pinned
    manifest is the number the next character in the roster is rendered against, not one
    that reads the same to six places."""
    plan = TA.projection_plan(True, 50.0, 36.0, ortho_scale_pin=pin)
    round_tripped = json.loads(json.dumps(plan))["ortho_scale_pin"]
    assert round_tripped == pin
    assert float(repr(pin)) == pin


def test_a_pinned_plan_solves_nothing_and_shares_across_runs():
    plan = TA.projection_plan(True, 50.0, 36.0, ortho_scale_pin=S04_SOLVED)
    assert plan["solved"] is None
    assert plan["shared_across_views"] == "ortho_scale"
    assert plan["shared_across_runs"] is True
    assert plan["height_frac_participates"] is False


def test_an_unpinned_ortho_plan_still_solves_and_says_so():
    """The S04 behaviour, unchanged, stated as a property rather than assumed."""
    plan = TA.projection_plan(True, 50.0, 36.0)
    assert plan["ortho_scale_source"] == TA.SOLVED
    assert plan["ortho_scale_pin"] is None
    assert plan["solved"] == "ortho_scale"
    assert plan["shared_across_runs"] is False
    assert plan["height_frac_participates"] is True


def test_a_perspective_plan_has_no_scale_source_rather_than_a_solved_one():
    """`None` and `"solved"` are different answers. A perspective run does not solve an
    ortho scale — it has none — and a manifest saying `solved` would invite a reader to
    look for the number."""
    plan = TA.projection_plan(False, 50.0, 36.0)
    assert plan["ortho_scale_source"] is None
    assert plan["ortho_scale_pin"] is None
    assert plan["solved"] == "radius"


def test_the_default_parser_arguments_still_select_the_solved_ortho_path(rt):
    """Task A clause 4, through the REAL parser and the real plan — the same shape as
    S04's default-branch test, for the same reason: a test that passed `pin=None` by hand
    would keep passing after somebody gave `--ortho-scale` a default."""
    a = _parse(rt, "--glb=x.glb", "--out=y", "--ortho")
    plan = TA.projection_plan(a.ortho, a.lens, a.sensor, ortho_scale_pin=a.ortho_scale)
    assert a.ortho_scale is None
    assert plan["ortho_scale_source"] == TA.SOLVED
    assert plan["height_frac_participates"] is True


# ------------------------------------------------- the manifest's account of the source


HEIGHT_FRAC = 0.831


def test_a_pinned_run_records_no_solve_record_at_all(rt):
    """THE red test for the one-condition defect. Keyed off `ortho_scale is None` — the
    pre-S05 condition, which a pinned run does not satisfy — this returns a full solve
    record naming a `height_frac` the run never targeted."""
    plan = TA.projection_plan(True, 50.0, 36.0, ortho_scale_pin=S04_SOLVED)
    solved_for, pinned_as = rt.ortho_scale_record(
        plan, S04_SOLVED, HEIGHT_FRAC, repr(S04_SOLVED), 0.9124)
    assert solved_for is None
    assert pinned_as is not None
    assert pinned_as["value"] == S04_SOLVED
    assert pinned_as["given_text"] == repr(S04_SOLVED)
    assert pinned_as["height_frac_participates"] is False


def test_the_pinned_record_carries_no_height_frac_value_anywhere(rt):
    """Not merely "no `height_frac` key": the number itself must not appear. A block that
    said `height_frac_participates: False` beside `target_height_frac: 0.831` would be a
    manifest disagreeing with itself, and a reader retyping the run would believe the pin
    had been fitted to something."""
    plan = TA.projection_plan(True, 50.0, 36.0, ortho_scale_pin=S04_SOLVED)
    _, pinned_as = rt.ortho_scale_record(plan, S04_SOLVED, HEIGHT_FRAC, "1.1", 0.9124)
    assert str(HEIGHT_FRAC) not in json.dumps(pinned_as)


def test_a_solved_run_records_its_target_and_no_pin_record(rt):
    plan = TA.projection_plan(True, 50.0, 36.0)
    solved_for, pinned_as = rt.ortho_scale_record(
        plan, S04_SOLVED, HEIGHT_FRAC, None, 0.9124)
    assert pinned_as is None
    assert solved_for["height_frac"] == HEIGHT_FRAC
    assert solved_for["subject_sphere_radius"] == 0.9124


def test_a_perspective_run_records_neither(rt):
    """The radius solve has its own record; neither ortho block belongs on that path, and
    an empty-dict placeholder would read as a fit that produced nothing."""
    plan = TA.projection_plan(False, 50.0, 36.0)
    assert rt.ortho_scale_record(plan, None, HEIGHT_FRAC, None, None) == (None, None)


def test_exactly_one_scale_record_is_ever_written(rt):
    """The two blocks are mutually exclusive by construction. A manifest carrying both
    would describe a scale that was pinned and fitted at once."""
    for plan in (TA.projection_plan(True, 50.0, 36.0),
                 TA.projection_plan(True, 50.0, 36.0, ortho_scale_pin=ROOMY),
                 TA.projection_plan(False, 50.0, 36.0)):
        blocks = rt.ortho_scale_record(plan, ROOMY, HEIGHT_FRAC, "x", 0.9)
        assert sum(b is not None for b in blocks) <= 1


# ------------------------------------------------------- the arithmetic the arms rest on


@pytest.mark.parametrize("factor", [0.80, 1.0, 1.25])
def test_screen_size_scales_as_one_over_the_pin(factor):
    """Why a roster CAN stand on one number, and why a pin too tight crops rather than
    shrinking: pixel offset from frame centre goes as 1/ortho_scale exactly, with no
    distance term. This is the identity every S05 prediction is arithmetic on."""
    from armature_core import framing

    target, point = (0.0, 0.0, 0.0), (0.0, 0.0, 0.4)
    base = framing.project(point, target, 5.0, 270.0, 30.0, 50.0, 36.0, 1024, 1024,
                           ortho_scale=S04_SOLVED)
    scaled = framing.project(point, target, 5.0, 270.0, 30.0, 50.0, 36.0, 1024, 1024,
                             ortho_scale=S04_SOLVED * factor)
    assert (scaled[1] - 0.5) == pytest.approx((base[1] - 0.5) / factor, rel=1e-12)


def test_a_pin_reopens_the_direction_the_solve_closed():
    """A measured structural fact about a pinned run, recorded as a test because it is the
    thing a reader is most likely to get wrong about which andon fires.

    Gate WHOLE reads the PROJECTED cloud. On a solved run it cannot fail on the height
    axis — the solve fits that projection to `height_frac <= 1` by construction, which is
    S04's "Gate WHOLE passes by construction". A pin is not fitted to anything, so a pin
    tight enough pushes the projected silhouette past the frame border, and Gate WHOLE is
    live in a direction it is never live in on a solved run. Gate CROP sits downstream of
    it, on the RENDERED alpha, and binds the decimation gap — a band of a few pixels.
    """
    solved_height_frac = 0.8094                    # S04 view 0, measured
    assert solved_height_frac <= 1.0
    assert solved_height_frac / 0.80 > 1.0         # the tight pin overflows the frame
    assert solved_height_frac / 1.25 < 1.0         # the roomy pin cannot


def test_the_solve_and_the_pin_are_different_kinds_of_number(rt):
    """A solved scale is fitted to ONE subject; a pinned one is not fitted to anything.
    Handing the solve a subject twice as tall returns a different number — which is
    correct, and is exactly why a cast cannot be rendered on solved scales."""
    short = [(0.0, 0.0, z) for z in (0.0, 0.4, 0.8)] + [(0.1, 0.05, 0.8)]
    tall = [(0.0, 0.0, z) for z in (0.0, 0.8, 1.6)] + [(0.1, 0.05, 1.6)]
    az, target = [270.0, 0.0], (0.0, 0.0, 0.4)

    a = rt.solve_ortho_scale_for_height(short, target, 6.0, az, 0.0, 512, 1024, 0.8)
    b = rt.solve_ortho_scale_for_height(tall, (0.0, 0.0, 0.8), 6.0, az, 0.0, 512, 1024, 0.8)
    assert a != pytest.approx(b, rel=1e-3)

    pinned = TA.projection_plan(True, 50.0, 36.0, ortho_scale_pin=a)["ortho_scale_pin"]
    assert pinned == a                             # the same number, whoever is in front


def test_math_isfinite_is_what_rejects_inf_since_the_downstream_check_does_not():
    """`ortho_half_spans` guards `<= 0`, and `inf > 0` is True while `nan <= 0` is False.
    Both walk straight through it, so the pin's own check is the one that binds them."""
    from armature_core import framing

    assert framing.ortho_half_spans(float("inf"), 1024, 1024)      # does not raise
    assert not math.isfinite(float("inf"))
    with pytest.raises(framing.FramingError):
        framing.ortho_half_spans(0.0, 1024, 1024)
