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
