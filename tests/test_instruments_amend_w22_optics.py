"""Wave 22 · instruments — the RENDERERS whose pixels are the reference stack.

`render_turnaround` writes the eight RGBA views a paid generation is conditioned on and
`preview_walk` / `render_performer` / `render_start_frame` write the frames a session looks
at before it spends. The findings closed here are the ones whose operand is one of those
pictures; the rest of the domain's fifteen are in `tests/test_instruments_amend_w22.py`.

Helpers here **raise**; they never `assert` outside a test body — `-O` deletes an `assert`
in a non-plugin helper and `ci.yml`'s `-O` leg would report green over it.
"""

import ast
import json
import math
import os

import pytest

from blender_stub import blender_stubbed, exit_code_of_main_block, load_tool, read_source

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")


def _fn(src, name):
    """The `ast.FunctionDef` called `name` at module level."""
    for node in ast.parse(src).body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise LookupError("no module-level def " + repr(name))


def _calls(node, dotted):
    """Every `ast.Call` under `node` whose callee spells `dotted` (``a.b`` or ``b``)."""
    want = dotted.split(".")
    out = []
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Call):
            continue
        parts, f = [], sub.func
        while isinstance(f, ast.Attribute):
            parts.append(f.attr)
            f = f.value
        if isinstance(f, ast.Name):
            parts.append(f.id)
        if list(reversed(parts)) == want:
            out.append(sub)
    return out


def _halt_line(filename, prefix, raiser):
    """Drive the tool's real `__main__` handler and return `(code, record)`.

    The wave-18 rule: the halt line is READ, not assumed. `import armature_core` stays
    inside the stub (Trap A) because these modules import `bpy` at module scope.
    """
    code, escaped = exit_code_of_main_block(filename, raiser=raiser)
    if escaped is not None:
        raise escaped
    return code


# ===========================================================================
# F-553c8bc0 (panel CRITICAL) — Gate WHOLE rules on the FULL silhouette cloud.
# ===========================================================================
#
# THE OPERAND, rebuilt from the auditor's wave-21 measurement. His was a 20,000-point
# synthetic performer (body cylinder + one outstretched arm) on which the decimated cloud
# over-reported the clearance by up to 21.73 px and `gate_whole` PASSED over the decimated
# cloud while REFUSING the full one. This is the same shape with the divergence isolated
# into ONE point so the window is wide rather than a knife edge: a cylinder of radius R,
# plus a single "fingertip" at (0.9R, 0.9R) — 1.27 R from the axis, so it is the SCREEN
# extreme at azimuths 315 and 135, and neither an x- nor a y- nor a z-extreme in WORLD
# space, which is the only thing `framing_cloud` carries across its reduction.

CYL_R = 0.30
CYL_N = 20000
FINGERTIP = (0.9 * CYL_R, 0.9 * CYL_R, 0.85)
W, H = 352, 1024
MARGIN_PX = 2.0
LENS_MM, SENSOR_MM = 50.0, 36.0
#: A radius at which the divergence is ~38 px — measured, not chosen by eye.
DIVERGENT_RADIUS = 3.0


def _performer_cloud():
    pts = []
    for i in range(CYL_N):
        ang = (i * 0.61803398875) * 2 * math.pi
        pts.append((CYL_R * math.cos(ang), CYL_R * math.sin(ang), (i / CYL_N) * 1.7))
    pts.append(FINGERTIP)
    return pts


def _target(pts):
    lo = [min(p[i] for p in pts) for i in range(3)]
    hi = [max(p[i] for p in pts) for i in range(3)]
    return tuple((lo[i] + hi[i]) * 0.5 for i in range(3))


@pytest.fixture(scope="module")
def sf():
    from armature_core import startframe
    return startframe


def test_the_decimated_cloud_drops_the_screen_extreme_that_is_not_a_world_extreme(sf):
    """`framing_cloud` carries the six WORLD-axis extremes and nothing else.

    The premise of the whole finding, measured rather than read off a docstring.
    """
    pts = _performer_cloud()
    dec = sf.framing_cloud(pts, cap=1500)
    assert len(pts) == CYL_N + 1
    assert len(dec) == 1500
    assert FINGERTIP not in dec, (
        "the fingertip survived the reduction, so this cloud no longer exhibits the "
        "defect and the comparison below would prove nothing")


def test_gate_whole_passes_the_decimated_cloud_and_refuses_the_full_one(sf):
    """The finding's own sentence, as a measurement.

    This stays true of the LIBRARY after the fix — what the fix changes is which of the two
    clouds the TOOL hands it, pinned by
    `test_render_turnaround_hands_gate_whole_the_full_cloud` below.
    """
    from armature_core.errors import ArmatureError

    pts = _performer_cloud()
    dec = sf.framing_cloud(pts, cap=1500)
    target = _target(pts)
    diverged = []
    for i in range(8):
        az = (270.0 + 360.0 * i / 8.0) % 360.0
        ed = sf.silhouette_extent(dec, target, DIVERGENT_RADIUS, az, 0.0,
                                  LENS_MM, SENSOR_MM, W, H)
        ef = sf.silhouette_extent(pts, target, DIVERGENT_RADIUS, az, 0.0,
                                  LENS_MM, SENSOR_MM, W, H)
        try:
            sf.gate_whole(ef, W, H, MARGIN_PX)
        except ArmatureError as exc:
            assert exc.evidence["clause"] == "silhouette_does_not_clear_the_border"
            sf.gate_whole(ed, W, H, MARGIN_PX)      # PASS over the decimated cloud
            diverged.append((i, round(az, 1),
                             round(max(ed["x0"] - ef["x0"], ef["x1"] - ed["x1"]), 2)))
    assert len(diverged) == 2, (
        "expected two views where the decimated cloud passes and the full one refuses; "
        "got " + repr(diverged))
    assert min(d[2] for d in diverged) > 20.0, diverged


def test_render_turnaround_exposes_both_populations(rt):
    """`framing_clouds(verts)` — the full cloud for the gate, the reduction for the solve.

    The sibling `render_start_frame` spells the separation inline (`cloud` = every vertex,
    `solve_cloud = SF.framing_cloud(cloud, cap=FRAMING_CLOUD_CAP)`); this file gets a named
    object so the property is testable without a Blender scene.
    """
    pts = _performer_cloud()
    cloud, solve_cloud = rt.framing_clouds(pts)
    assert len(cloud) == len(pts)
    assert [tuple(p) for p in cloud] == [tuple(p) for p in pts]
    assert len(solve_cloud) == rt.FRAMING_CLOUD_CAP
    assert len(solve_cloud) < len(cloud)


def test_render_turnaround_hands_gate_whole_the_full_cloud():
    """The census, keyed on the RESOLVED shape: which NAME each call receives.

    Not "the file mentions `framing_cloud`" — `main` binds two clouds, and the defect was
    entirely in which of them each caller got. Red on `e8263a3`, where ONE name was bound
    from `SF.framing_cloud(verts)` and handed to the solve AND to the gate.
    """
    main = _fn(read_source("render_turnaround.py"), "main")

    binds = {}
    for node in ast.walk(main):
        if not isinstance(node, ast.Assign):
            continue
        for t in node.targets:
            for name in ([t] if isinstance(t, ast.Name) else
                         [e for e in getattr(t, "elts", []) if isinstance(e, ast.Name)]):
                binds[name.id] = node.value
    assert "cloud" in binds and "solve_cloud" in binds, sorted(binds)
    assert binds["cloud"] is binds["solve_cloud"], (
        "the two populations are bound separately; they come from `framing_clouds`, which "
        "is the object `test_render_turnaround_exposes_both_populations` measures")
    assert not _calls(binds["cloud"], "SF.framing_cloud"), (
        "`cloud` — the name Gate WHOLE's extent is measured over — is bound from a "
        "`framing_cloud` REDUCTION; the gate then rules on the same samples the solve was "
        "fitted to and cannot see a silhouette wider than they are")
    assert _calls(binds["cloud"], "framing_clouds"), ast.dump(binds["cloud"])

    extent_calls = _calls(main, "SF.silhouette_extent")
    assert extent_calls, "main no longer measures a silhouette extent"
    for call in extent_calls:
        assert isinstance(call.args[0], ast.Name) and call.args[0].id == "cloud", (
            "SF.silhouette_extent at line %d is measured over %s, not the full `cloud`"
            % (call.lineno, ast.dump(call.args[0])))

    for solver in ("solve_radius_for_height", "solve_ortho_scale_for_height"):
        calls = _calls(main, solver)
        assert calls, "main no longer calls " + solver
        for call in calls:
            assert isinstance(call.args[0], ast.Name) and call.args[0].id == "solve_cloud", (
                "%s at line %d is solved against %s, not the reduction"
                % (solver, call.lineno, ast.dump(call.args[0])))


def test_the_gate_whole_refusal_reaches_the_turnaround_halt_line(sf, capsys):
    """THE HALT LINE, READ (wave-18 rule 4) for the refusal this finding restores.

    Gate WHOLE's andon is `StartFrameGate`, raised from inside `main`'s try. The record an
    operator keys on is `RENDER_TURNAROUND_HALT` at exit 2 with the clause in the evidence
    — which is the line the decimated cloud was preventing from ever being printed.
    """
    pts = _performer_cloud()
    target = _target(pts)
    az = (270.0 + 360.0 * 1 / 8.0) % 360.0
    ef = sf.silhouette_extent(pts, target, DIVERGENT_RADIUS, az, 0.0,
                              LENS_MM, SENSOR_MM, W, H)

    def raiser():
        sf.gate_whole(ef, W, H, MARGIN_PX)

    code = _halt_line("render_turnaround.py", "RENDER_TURNAROUND", raiser)
    out = capsys.readouterr().out
    line = [l for l in out.splitlines() if l.startswith("RENDER_TURNAROUND_HALT ")]
    assert len(line) == 1, out
    rec = json.loads(line[0].split(" ", 1)[1])
    assert code == 2
    assert rec["outcome"].startswith("HALTED")
    assert rec["gate"] == "WHOLE"
    assert rec["error"] == "StartFrameGate"
    assert rec["evidence"]["clause"] == "silhouette_does_not_clear_the_border"


def test_the_turnaround_manifest_records_both_cloud_populations():
    """`render_start_frame.py:1012`'s field, carried here.

    `subject.n_vertices` recorded the FULL count while the gate read 1500 and no field said
    so. The camera block now carries `framing_cloud: {n_vertices, n_solved_against, cap}`
    exactly as the sibling's does.
    """
    main = _fn(read_source("render_turnaround.py"), "main")
    keys = [n.value for n in ast.walk(main)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    assert "framing_cloud" in keys, (
        "the manifest's camera block does not record which population the gate measured")
    for field in ("n_vertices", "n_solved_against", "cap"):
        assert field in keys, field


# ===========================================================================
# F-3990e197 (panel HIGH, ground F-fd559fc6) — `preview_walk --scale` bounded.
# ===========================================================================
#
# THE POPULATION, re-enumerated on `e8263a3` by grep over the 21 owned tools: SEVEN sites
# assign `scene.render.resolution_x`. Four take a module constant no flag can move
# (`make_binding_sheet:150`, `make_parts_sheet:302`, `make_skeleton_sheet:261`,
# `preview_glb:140` — a `res` constant; `render_performer:334` — `WIDTH, HEIGHT`). Two are
# bounded through `require_frame_size` (`render_start_frame:595`, `render_turnaround:801`).
# `preview_walk:171` was the one whose resolution is DERIVED FROM A FLAG and bounded
# nowhere.


@pytest.fixture(scope="module")
def pw():
    return load_tool("preview_walk.py")


@pytest.mark.parametrize("scale", [float("nan"), float("inf"), float("-inf"), 0.0, -0.5,
                                   1e6])
def test_preview_walk_refuses_a_scale_that_is_not_a_fraction_of_the_shot(pw, scale):
    """The auditor's five operands plus `-inf`, each refused BY NAME.

    On `e8263a3` `nan` raised a bare `ValueError: cannot convert float NaN to integer`,
    `inf` a bare `OverflowError`, and `0` / `-0.5` / `1e6` raised nothing at all and were
    assigned to `scene.render.resolution_x`.
    """
    with pytest.raises(pw.PreviewWalkGate) as exc:
        pw.preview_frame(832, 480, scale)
    ev = exc.value.evidence
    assert ev["flag"] == "--scale"
    assert ev["who"] == "preview_walk"
    assert ev["gate"] == pw.PreviewWalkGate.gate
    assert "--scale" in str(exc.value)


def test_preview_walk_refuses_a_legal_fraction_that_collapses_the_frame(pw):
    """The direction neither borrowed bound covers: the PRODUCT rounds to zero.

    `--scale=1e-9` is a perfectly good fraction and 832x480 is a perfectly good shot; the
    preview is 0x0. The clause is this module's own, named, above the assignment.
    """
    with pytest.raises(pw.PreviewWalkGate) as exc:
        pw.preview_frame(832, 480, 1e-9)
    ev = exc.value.evidence
    assert ev["clause"] == "preview_frame_collapsed"
    assert ev["preview"] == [0, 0]
    assert ev["collapsed"] == ["width", "height"]


def test_preview_walk_accepts_the_scales_the_repo_actually_runs(pw):
    """A bound that refuses correct work is the defect, not the fix.

    Measured over every `specs/*.json` resolution in this tree (480x832 and 512x768) at the
    module default: both preview frames are drawn.
    """
    assert pw.preview_frame(480, 832, 0.5) == (240, 416)
    assert pw.preview_frame(512, 768, 0.5) == (256, 384)
    assert pw.preview_frame(480, 832, 1.0) == (480, 832)
    assert pw.preview_frame(480, 832, 0.3) == (144, 250)


def test_preview_walk_derives_its_frame_through_the_bound():
    """Census on the RESOLVED shape: `main` no longer multiplies the flag itself.

    Red on `e8263a3`, where `main` held `int(round(spec["resolution"]["width"] * a.scale))`
    twice with no bound between it and `scene.render.resolution_x`.
    """
    src = read_source("preview_walk.py")
    main = _fn(src, "main")
    bound = _calls(main, "preview_frame")
    assert bound, "main no longer derives its frame through the bound"
    #: `a.scale` may appear ONCE and only as an argument to the bound.
    inside = {id(n) for call in bound for arg in call.args for n in ast.walk(arg)}
    reads = [n for n in ast.walk(main)
             if isinstance(n, ast.Attribute) and n.attr == "scale"
             and isinstance(n.value, ast.Name) and n.value.id == "a"]
    assert reads, "main no longer reads --scale at all"
    for node in reads:
        assert id(node) in inside, (
            "main reads `a.scale` at line %d outside `preview_frame`; the flag is bounded "
            "where it is READ" % node.lineno)


def test_the_preview_walk_scale_refusal_reaches_the_halt_line(pw, capsys):
    """THE HALT LINE, READ. `PREVIEW_WALK_HALT`, exit 2, the flag in the evidence."""
    def raiser():
        pw.preview_frame(832, 480, float("nan"))

    code = _halt_line("preview_walk.py", "PREVIEW_WALK", raiser)
    out = capsys.readouterr().out
    line = [l for l in out.splitlines() if l.startswith("PREVIEW_WALK_HALT ")]
    assert len(line) == 1, out
    rec = json.loads(line[0].split(" ", 1)[1])
    assert code == 2
    assert rec["outcome"].startswith("HALTED")
    assert rec["error"] == "PreviewWalkGate"
    assert rec["evidence"]["flag"] == "--scale"


# ===========================================================================
# F-0befca53 — the ortho pin's two refusals are the ANDON, not `ap.error`.
# ===========================================================================


@pytest.mark.parametrize("argv,clause", [
    (["--glb=x.glb", "--out=o", "--ortho-scale=1.0"],
     "ortho_scale_pinned_without_ortho"),
    (["--glb=x.glb", "--out=o", "--ortho", "--ortho-scale=0.0"],
     "ortho_scale_not_finite_positive"),
    (["--glb=x.glb", "--out=o", "--ortho", "--ortho-scale=nan"],
     "ortho_scale_not_finite_positive"),
    (["--glb=x.glb", "--out=o", "--ortho", "--ortho-scale=-2.0"],
     "ortho_scale_not_finite_positive"),
])
def test_the_ortho_scale_clauses_raise_the_andon(rt, monkeypatch, argv, clause):
    """On `e8263a3` both clauses called `ap.error`, whose `SystemExit(2)` the `__main__`
    block re-raises untouched: exit 2 with stdout EMPTY — no sentinel, no gate id, no
    clause, no evidence, on the two refusals guarding the number a whole roster's shared
    frame span stands on."""
    monkeypatch.setattr(rt.sys, "argv", ["blender", "-b", "-P", "x", "--"] + argv)
    with pytest.raises(rt.RenderTurnaroundGate) as exc:
        rt.parse_args()
    ev = exc.value.evidence
    assert ev["clause"] == clause, ev
    assert ev["flag"] == "--ortho-scale", ev
    assert ev["gate"] == rt.RenderTurnaroundGate.gate, ev
    assert "--ortho-scale" in str(exc.value)


def test_the_instruments_domain_holds_no_ap_error_call_site():
    """The population, closed. A `ap.error` refusal prints an argparse usage line no log
    reader can key on and exits 2 — the same code the halt contract gives a fired andon.

    Measured on `e8263a3`: two sites, both in `render_turnaround.parse_args`. The only
    remaining call site anywhere under `tools/` is `measure_tracking.py:323`, which is
    instruments-measure's file and is posted to the inbox rather than edited here.
    """
    owned = (
        "author_walk.py", "check_relift.py", "diagnose_bone_heat.py", "lift_solve.py",
        "make_binding_sheet.py", "make_parts_sheet.py", "make_rig_sheet.py",
        "make_skeleton_sheet.py", "make_test_armature.py", "preview_glb.py",
        "preview_walk.py", "probe_glb.py", "probe_subject.py", "render_performer.py",
        "render_start_frame.py", "render_turnaround.py", "rig_bake.py",
        "rig_character.py", "rig_parts.py", "rig_repair.py", "rig_retopo.py",
    )
    sites = []
    for fn in owned:
        for node in ast.walk(ast.parse(read_source(fn))):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "error"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id in ("ap", "p", "parser")):
                sites.append((fn, node.lineno))
    assert sites == [], sites


def test_the_ortho_scale_refusal_reaches_the_halt_line(rt, capsys):
    """THE HALT LINE, READ — the record `ap.error` printed nothing of."""
    def raiser():
        rt.sys.argv = ["blender", "-b", "-P", "x", "--", "--glb=x.glb", "--out=o",
                       "--ortho", "--ortho-scale=0.0"]
        rt.parse_args()

    code = _halt_line("render_turnaround.py", "RENDER_TURNAROUND", raiser)
    out = capsys.readouterr().out
    line = [l for l in out.splitlines() if l.startswith("RENDER_TURNAROUND_HALT ")]
    assert len(line) == 1, out
    rec = json.loads(line[0].split(" ", 1)[1])
    assert code == 2
    assert rec["gate"] == "TURNAROUND"
    assert rec["evidence"]["clause"] == "ortho_scale_not_finite_positive", rec
    assert rec["evidence"]["flag"] == "--ortho-scale", rec
