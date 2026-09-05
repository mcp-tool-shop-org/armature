"""Wave 22 · instruments — the domain's fifteen, less the renderer-optics half.

The renderer findings whose operand is a picture live in
`tests/test_instruments_amend_w22_optics.py`. Everything else in the domain's fifteen is
here: the gate-id census, the halt line's JSON, the probe's success sentinel, the sheets'
clause split, the bake's empty-atlas andon, the repair tool's denominators, the retopo
route string, the synthetic subject's arc flags, and the render-target snapshot.

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

#: The instruments domain's owned modules, from wave 22's frozen domain map
#: (snapshot `b3a82d889dc918f6`). Typed here rather than derived because the DOMAIN is a
#: coordinator fact, not a property of the tree — and the census below states which
#: population it ruled over so a reader can tell what it did NOT look at.
OWNED = (
    "author_walk.py", "check_relift.py", "diagnose_bone_heat.py", "lift_solve.py",
    "make_binding_sheet.py", "make_parts_sheet.py", "make_rig_sheet.py",
    "make_skeleton_sheet.py", "make_test_armature.py", "preview_glb.py",
    "preview_walk.py", "probe_glb.py", "probe_subject.py", "render_performer.py",
    "render_start_frame.py", "render_turnaround.py", "rig_bake.py", "rig_character.py",
    "rig_parts.py", "rig_repair.py", "rig_retopo.py",
)


def _tree(filename):
    return ast.parse(read_source(filename))


class _IdentityArm:
    """Enough of an armature object for `gate_space_is_identity` to build its evidence."""

    matrix_world = ((1.0, 0.0, 0.0, 0.0), (0.0, 1.0, 0.0, 0.0),
                    (0.0, 0.0, 1.0, 0.0), (0.0, 0.0, 0.0, 1.0))


def _halt_record(filename, prefix, raiser, capsys):
    """Drive the tool's REAL `__main__` handler; return `(code, parsed record, raw line)`."""
    code, escaped = exit_code_of_main_block(filename, raiser=raiser)
    if escaped is not None:
        raise escaped
    out = capsys.readouterr().out
    lines = [l for l in out.splitlines() if l.startswith(prefix + " ")]
    if len(lines) != 1:
        raise AssertionError("expected exactly one %s line; got %r" % (prefix, out))
    return code, json.loads(lines[0].split(" ", 1)[1]), lines[0]


# ===========================================================================
# F-6381b9ff — one halt event, ONE gate id.
# ===========================================================================
#
# The repo closed this family twice in the builders domain
# (`tests/test_amend_w16_builders.py:815-823`, the rule stated at :879-886 as
# `ev["gate"] == type(exc).gate` beside `str(exc).startswith(f"[{ev['gate']}]")`). It was
# not held in this domain, and wave 18 widened it: an AST walk over the 21 owned tools
# found SEVEN sites where a declared id under `evidence["gate"]` disagreed with the raising
# class's own `gate`, and `grep` for `TURNAROUND_OPTICS`, `TURNAROUND_ORBIT`,
# `TURNAROUND_FRAME`, `TURNAROUND_FRACTION`, `STARTFRAME_FRACTION` across `tools/` found no
# `gate = "..."` class literal for ANY of them — so a census enumerating gate ids from the
# family classes reported zero sites for four ids the amend had declared.
#
# The resolution: `evidence["gate"]` is the RAISING CLASS's id, and the refusal's own,
# finer id moves to `evidence["sub_gate"]`. A reader can still tell the two STARTFRAME
# refusals apart; a census can still enumerate every gate id from the class literals.


def _declared_gate_ids(filename):
    """`{class name: gate id}` for every andon class reachable from `filename`.

    "Reachable" is resolved, not spelled: classes defined in the module itself, plus every
    class the module imports by name from another `tools/` module or from `armature_core`,
    resolved by reading THAT file. A census that read only the local `class` statements
    would not know what `StartFrameGate.gate` is in any file that imports it.
    """
    ids, seen = {}, set()

    def declared_in(path):
        try:
            with open(path, encoding="utf-8") as fh:
                tree = ast.parse(fh.read())
        except (OSError, SyntaxError):
            return {}
        out = {}
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for st in node.body:
                if (isinstance(st, ast.Assign) and len(st.targets) == 1
                        and isinstance(st.targets[0], ast.Name)
                        and st.targets[0].id == "gate"
                        and isinstance(st.value, ast.Constant)):
                    out[node.name] = st.value.value
        return out

    def visit(path):
        if path in seen or not os.path.isfile(path):
            return
        seen.add(path)
        ids.update(declared_in(path))
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                head = node.module.split(".")
                if head[0] == "armature_core":
                    visit(os.path.join(TOOLS, *head) + ".py")
                elif len(head) == 1:
                    visit(os.path.join(TOOLS, head[0] + ".py"))

    visit(os.path.join(TOOLS, filename))
    return ids


#: Helpers that take `(..., gate_cls, ev, ...)` and RAISE `gate_cls` with `ev`. The
#: evidence dict handed to one of these is that class's evidence exactly as if the caller
#: had written the `raise` — which is the whole point of there being one implementation.
_EVIDENCE_HELPERS = {"require_finite": (2, 3), "tightened": (3, 4), "narrowed": (3, 4)}


def _evidence_dicts(filename):
    """`[(lineno, class_name, gate_value_or_None)]` for every EVIDENCE dict in the module.

    The population is keyed on the RESOLVED shape — "a dict that reaches an andon's
    constructor" — not on the spelling `raise Cls(msg, {...})`. Three spellings reach it in
    this tree and all three are walked:

    * `raise Cls(msg, {...})` — the literal at the raise;
    * `ev = {...}` … `raise Cls(msg, ev)` — the name bound in the same function, which is
      what four of the eight sites use;
    * `ev = {...}` … `parts.require_finite(name, v, Cls, ev)` — handed to the ONE
      implementation of a bound, which raises `Cls` with that dict.

    A manifest VERDICT record (`rec["gate_CROP"] = {"gate": "CROP", ...}`) is a different
    object — a record of a gate's outcome under the manifest's own schema, not a refusal's
    receipt — and is deliberately not in this population.
    """
    declared = _declared_gate_ids(filename)
    tree = _tree(filename)

    def local(scope):
        """Every node in `scope`'s own body — NOT inside a nested def.

        Measured while writing this: walking the module and every function separately
        paired `rig_character.py:302`'s `ev` with a class raised in a DIFFERENT function,
        because `ast.walk` on the module descends into every body. A name binding is a
        property of one scope; the walk has to be one too.
        """
        out, stack = [], list(ast.iter_child_nodes(scope))
        while stack:
            n = stack.pop()
            out.append(n)
            if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                stack.extend(ast.iter_child_nodes(n))
        return out

    found = []
    for scope in [n for n in ast.walk(tree)
                  if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        bound = {}
        for node in local(scope):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and isinstance(node.value, ast.Dict)):
                bound[node.targets[0].id] = node.value

        def operand(node):
            if isinstance(node, ast.Dict):
                return node
            if isinstance(node, ast.Name):
                return bound.get(node.id)
            return None

        def cls_of(node):
            name = (node.id if isinstance(node, ast.Name)
                    else node.attr if isinstance(node, ast.Attribute) else None)
            return name if name in declared else None

        pairs = []
        for node in local(scope):
            if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
                cls = cls_of(node.exc.func)
                if cls and len(node.exc.args) > 1:
                    pairs.append((cls, node.exc.args[1]))
            if isinstance(node, ast.Call):
                fname = (node.func.attr if isinstance(node.func, ast.Attribute)
                         else node.func.id if isinstance(node.func, ast.Name) else None)
                slots = _EVIDENCE_HELPERS.get(fname)
                if slots and len(node.args) > max(slots):
                    cls = cls_of(node.args[slots[0]])
                    if cls:
                        pairs.append((cls, node.args[slots[1]]))
        for cls, arg in pairs:
            d = operand(arg)
            if d is None:
                continue
            for k, v in zip(d.keys, d.values):
                if isinstance(k, ast.Constant) and k.value == "gate":
                    found.append((d.lineno, cls,
                                  v.value if isinstance(v, ast.Constant) else None))
    return sorted(set(found)), declared


@pytest.mark.parametrize("filename", OWNED)
def test_every_evidence_gate_id_is_the_raising_classs_own(filename):
    """The census, lifted out of the builders module and keyed on the RESOLVED shape.

    `tests/test_amend_w16_builders.py:879-886` states the rule for the builders' andons —
    `ev["gate"] == type(exc).gate` beside `str(exc).startswith(f"[{ev['gate']}]")`. It was
    not held in this domain and wave 18 widened it. RED on `e8263a3` at EIGHT sites, which
    is one more than the finding's seven because that walk keyed on `raise Cls(msg, {...})`
    literals and four of the eight bind `ev = {...}` a few lines above the call that raises:

        author_walk.py       WalkGate  WALK      vs  SPACE, F, A, A       (4 sites)
        lift_solve.py        LiftGate  LIFT      vs  SPACE, ARRIVED       (2 sites)
        render_performer.py  RenderGate RENDER   vs  COVERAGE, COVERAGE   (2 sites)
        render_turnaround.py RenderTurnaroundGate TURNAROUND vs
                                                    TURNAROUND_OPTICS, TURNAROUND_ORBIT

    A finer id is not deleted — it moves to `evidence["sub_gate"]`, so a reader can still
    tell which clause of the andon pulled and a census can still enumerate every gate id
    from the family's `gate = "..."` class literals.
    """
    found, declared = _evidence_dicts(filename)
    offenders = [(line, cls, val) for line, cls, val in found
                 if isinstance(val, str) and val != declared.get(cls)]
    assert not offenders, (
        "%s: evidence dicts whose `gate` is not the raising class's own id "
        "(line, class, evidence['gate']): %r. A finer id belongs under `sub_gate`."
        % (filename, offenders))


def test_the_frame_and_fraction_bounds_name_the_class_not_the_sub_id(rt):
    """The constructed half of the same rule, driven rather than read.

    `require_frame_size` and `require_shot_fraction` build `evidence["gate"]` from their
    `gate_id` argument. Both callers on the turnaround declared ids no class owns.
    """
    for call, kwargs in (
            (lambda: rt.require_frame_size(
                0, 1024, who="render_turnaround", module_frame=(rt.WIDTH, rt.HEIGHT),
                gate=rt.RenderTurnaroundGate, gate_id="TURNAROUND_FRAME"),
             "TURNAROUND_FRAME"),
            (lambda: rt.require_shot_fraction(
                "--height-frac", float("nan"), who="render_turnaround",
                gate=rt.RenderTurnaroundGate, gate_id="TURNAROUND_FRACTION"),
             "TURNAROUND_FRACTION")):
        with pytest.raises(rt.RenderTurnaroundGate) as exc:
            call()
        ev = exc.value.evidence
        assert ev["gate"] == type(exc.value).gate == "TURNAROUND", ev
        assert ev["sub_gate"] == kwargs, ev
        assert str(exc.value).startswith("[%s] " % ev["gate"]), str(exc.value)


def test_the_turnaround_optics_refusal_prints_one_gate_id(rt, capsys):
    """THE HALT LINE, READ — the finding's own operand, end to end.

    On `e8263a3` this record read `"gate": "TURNAROUND"` at the top level beside
    `"evidence": {"gate": "TURNAROUND_OPTICS", ...}`: one halt event, two gate ids.
    """
    def raiser():
        rt.parts.require_finite(
            "--lens", float("nan"), rt.RenderTurnaroundGate,
            {"gate": rt.RenderTurnaroundGate.gate, "sub_gate": "TURNAROUND_OPTICS",
             "andon": rt.RenderTurnaroundGate.__name__, "who": "render_turnaround",
             "flag": "--lens", "clause": "lens_mm_not_finite_and_positive"},
            positive=True)

    code, rec, _ = _halt_record("render_turnaround.py", "RENDER_TURNAROUND_HALT",
                                raiser, capsys)
    assert code == 2
    assert rec["gate"] == "TURNAROUND"
    assert rec["evidence"]["gate"] == rec["gate"], rec
    assert rec["evidence"]["sub_gate"] == "TURNAROUND_OPTICS", rec
    assert rec["message"].startswith("[TURNAROUND] "), rec


@pytest.mark.parametrize("filename,cls,call", [
    ("author_walk.py", "WalkGate",
     lambda m: m.mesh_sample_frames(1)),
    ("render_performer.py", "RenderGate",
     lambda m: m.gate_coverage([], "plate.png", min_frac=1.0)),
    ("author_walk.py", "WalkGate",
     lambda m: m.gate_space_is_identity(_IdentityArm(), tol=1.0)),
    ("lift_solve.py", "LiftGate",
     lambda m: m.gate_space_is_identity(_IdentityArm(), tol=1.0)),
])
def test_the_static_siblings_agree_with_their_own_class(filename, cls, call):
    """The rest of the eight, DRIVEN through the functions that raise them.

    A census reads source; this reads the object a caller actually gets — the shape
    `tests/test_amend_w16_builders.py:879-886` uses, and the reason a `sub_gate` key that
    the census would accept cannot quietly become the thing the halt line prints.
    """
    mod = load_tool(filename)
    gate_cls = getattr(mod, cls)
    with pytest.raises(gate_cls) as exc:
        call(mod)
    ev = exc.value.evidence
    assert ev["gate"] == gate_cls.gate, ev
    assert str(exc.value).startswith("[%s] " % gate_cls.gate)
    assert "sub_gate" in ev, ev


# ===========================================================================
# F-798281dc (panel HIGH, ground F-333cefd8) — rig_bake's empty-atlas andon can fire.
# ===========================================================================


class _ZeroPixelImage:
    """A Blender image with no pixels — what `--atlas=0` builds."""

    pixels = ()
    size = (0, 0)


class _LitImage:
    """A 2x2 RGBA image whose pixels are lit, so `atlas_health` has a fraction to report."""

    pixels = tuple([0.5, 0.5, 0.5, 1.0] * 4)
    size = (2, 2)


@pytest.fixture(scope="module")
def bake():
    return load_tool("rig_bake.py")


def test_atlas_health_refuses_a_zero_pixel_atlas_by_name(bake):
    """RE-MEASURED on `e8263a3` under the stub with a zero-pixel image: `atlas_health`
    returned `{'pixels': 0, 'non_black_fraction': nan, ...}` (numpy "Mean of empty slice"),
    `nan < 0.20` is False, so the "the baked atlas is mostly empty" andon did NOT fire on
    the TOTAL failure it exists for — `os.makedirs` ran below it, the GLB was exported,
    Gate GLB passed on a real non-empty file, and the manifest published
    `non_black_fraction: NaN`.
    """
    with blender_stubbed():
        with pytest.raises(bake.BakeEmpty) as exc:
            bake.atlas_health(_ZeroPixelImage())
    ev = exc.value.evidence
    assert ev["clause"] == "atlas_has_no_pixels", ev
    assert ev["pixels"] == 0, ev
    assert ev["gate"] == bake.BakeEmpty.gate, ev


def test_atlas_health_still_reports_a_fraction_when_there_are_pixels(bake):
    """A refusal that also refuses correct work is the defect, not the fix."""
    with blender_stubbed():
        health = bake.atlas_health(_LitImage())
    assert health["pixels"] == 4
    assert health["non_black_fraction"] == 1.0


@pytest.mark.parametrize("argv,flag", [
    (["--retopo=r.glb", "--source=s.glb", "--out=o", "--max-deviation=0.003",
      "--atlas=0"], "--atlas"),
    (["--retopo=r.glb", "--source=s.glb", "--out=o", "--max-deviation=0.003",
      "--atlas=-4096"], "--atlas"),
    (["--retopo=r.glb", "--source=s.glb", "--out=o", "--max-deviation=nan"],
     "--max-deviation"),
    (["--retopo=r.glb", "--source=s.glb", "--out=o", "--max-deviation=inf"],
     "--max-deviation"),
    (["--retopo=r.glb", "--source=s.glb", "--out=o", "--max-deviation=0"],
     "--max-deviation"),
    (["--retopo=r.glb", "--source=s.glb", "--out=o", "--max-deviation=-0.003"],
     "--max-deviation"),
])
def test_the_two_flags_that_size_the_bake_are_bounded(bake, monkeypatch, argv, flag):
    """`grep require_finite tools/rig_bake.py` returned NOTHING on `e8263a3`: this module
    had no finiteness bound anywhere. `--atlas` sizes the image `atlas_health` measures;
    `--max-deviation` reaches `cage_extrusion` and `max_ray_distance` unexamined.
    """
    monkeypatch.setattr(bake.sys, "argv", ["blender", "-b", "-P", "x", "--"] + argv)
    with pytest.raises(bake.BakeEmpty) as exc:
        bake.parse_args()
    ev = exc.value.evidence
    assert ev["flag"] == flag, ev
    assert ev["gate"] == bake.BakeEmpty.gate, ev
    assert flag in str(exc.value)


def test_the_good_bake_arguments_still_parse(bake, monkeypatch):
    monkeypatch.setattr(bake.sys, "argv", [
        "blender", "-b", "-P", "x", "--", "--retopo=r.glb", "--source=s.glb",
        "--out=o", "--max-deviation=0.00358"])
    a = bake.parse_args()
    assert a["atlas"] == bake.ATLAS and a["max_deviation"] == 0.00358


def test_the_empty_atlas_refusal_reaches_the_rig_bake_halt_line(bake, capsys):
    """THE HALT LINE, READ."""
    def raiser():
        bake.atlas_health(_ZeroPixelImage())

    code, rec, _ = _halt_record("rig_bake.py", "RIG_BAKE_HALT", raiser, capsys)
    assert code == 2
    assert rec["error"] == "BakeEmpty"
    assert rec["evidence"]["clause"] == "atlas_has_no_pixels", rec
    assert rec["evidence"]["pixels"] == 0, rec


# ===========================================================================
# F-4354f34d (panel HIGH, ground F-3551d50a) — rig_repair's two vacuity holes.
# ===========================================================================


class _FakeElem:
    is_manifold = True
    is_boundary = False
    link_faces = ()


class _FakeSeq(list):
    def __init__(self, n):
        super().__init__(_FakeElem() for _ in range(n))

    def ensure_lookup_table(self):
        pass


class _FakeBMesh:
    """Just enough bmesh for `manifold_stats` and `extract_and_weld`'s guard."""

    def __init__(self, faces=0, verts=0, edges=0):
        self.faces = _FakeSeq(faces)
        self.verts = _FakeSeq(verts)
        self.edges = _FakeSeq(edges)
        self.freed = False

    def from_mesh(self, data):
        pass

    def free(self):
        self.freed = True


class _FakeObject:
    name = "broken_source"
    data = object()


@pytest.fixture(scope="module")
def repair():
    return load_tool("rig_repair.py")


def _with_bmesh(monkeypatch, mod, bm):
    fake = type("bmesh_stub", (), {})()
    fake.new = lambda: bm
    fake.ops = mod.bmesh.ops
    monkeypatch.setattr(mod, "bmesh", fake)


def test_an_empty_mesh_is_not_a_closed_manifold(repair, monkeypatch):
    """MEASURED on `e8263a3` by evaluating `closed_manifold`'s expression on the zero-count
    dict: `True`. Gate REPAIR's `if not final["closed_manifold"]` therefore PASSED a mesh
    deleted entirely, and total deletion was caught one clause LOWER by the face budget —
    the second gate carrying the first gate's load, which CLAUDE.md rules against.
    """
    _with_bmesh(monkeypatch, repair, _FakeBMesh(faces=0, verts=0, edges=0))
    stats = repair.manifold_stats(_FakeObject())
    assert stats["faces"] == 0
    assert stats["closed_manifold"] is False


def test_a_real_closed_shell_is_still_a_closed_manifold(repair, monkeypatch):
    _with_bmesh(monkeypatch, repair, _FakeBMesh(faces=12, verts=8, edges=18))
    stats = repair.manifold_stats(_FakeObject())
    assert stats["closed_manifold"] is True


def test_a_source_with_no_faces_is_refused_by_name(repair, monkeypatch):
    """`"interior_fraction": interior_deleted / before["faces"]` divided by a measured face
    count with no guard, on the tool whose EXPECTED input is a broken mesh. A source with
    vertices and no polygons reached a bare `ZeroDivisionError` inside a helper, recorded by
    the halt contract as "FAILED — an unhandled error" at exit 1 rather than as a refusal
    naming the asset.
    """
    _with_bmesh(monkeypatch, repair, _FakeBMesh(faces=0, verts=140))
    with pytest.raises(repair.SourceHasNoFaces) as exc:
        repair.extract_and_weld(_FakeObject(), 1.0)
    ev = exc.value.evidence
    assert ev["clause"] == "source_has_no_faces", ev
    assert ev["object"] == "broken_source", ev
    assert ev["verts"] == 140, ev
    assert ev["gate"] == repair.SourceHasNoFaces.gate == "REPAIR_SOURCE"


def test_the_repair_source_refusal_reaches_the_halt_line(repair, capsys, monkeypatch):
    """THE HALT LINE, READ — and it names the asset, not `ZeroDivisionError`."""
    _with_bmesh(monkeypatch, repair, _FakeBMesh(faces=0, verts=140))

    def raiser():
        repair.extract_and_weld(_FakeObject(), 1.0)

    code, rec, _ = _halt_record("rig_repair.py", "RIG_REPAIR_HALT", raiser, capsys)
    assert code == 2
    assert rec["error"] == "SourceHasNoFaces", rec
    assert rec["evidence"]["clause"] == "source_has_no_faces", rec
    assert rec["evidence"]["object"] == "broken_source", rec


def test_both_denominators_are_guarded_above_their_division():
    """The census: every division by a measured face count in this module sits BELOW a
    clause that refuses zero. Keyed on the resolved shape — the two divisions are spelled
    differently (`interior_deleted / before["faces"]` and `removed / shell_faces`) and both
    are in the population.
    """
    tree = _tree("rig_repair.py")
    divisions = [n for n in ast.walk(tree)
                 if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div)]
    counted = [n for n in divisions
               if "faces" in ast.dump(n.right) or "shell_faces" in ast.dump(n.right)]
    assert len(counted) == 2, [ast.dump(n) for n in counted]
    guards = [n.lineno for n in ast.walk(tree)
              if isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call)
              and isinstance(n.exc.func, ast.Name)
              and n.exc.func.id == "SourceHasNoFaces"]
    assert len(guards) == 2, guards
    for div in counted:
        assert any(g < div.lineno for g in guards), (div.lineno, guards)
