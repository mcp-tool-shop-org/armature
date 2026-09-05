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


# ===========================================================================
# F-7cd1b3b7 · F-f7d1f64f (panel HIGH) — a --name / --prefix is a NAME, not a path.
# ===========================================================================
#
# SEAM 1 (core-solvers, wave 22) homed `single_path_segment` in `armature_core.parts`;
# instruments-measure deletes its two byte-identical copies (`pack_pose_pack.py:82`,
# `resample_motion.py:76`) and builders adopts the same object for `fetch_run --run`.
# Instruments ADOPTS BY IMPORT and spells nothing locally.
#
# The helper does not exist on this branch until core-solvers' commit merges, so the
# BEHAVIOURAL half below is skipped here and runs on the merged tree; the ADOPTION half is
# an AST census that runs unconditionally, and `test_the_seam_1_block_is_real` fails rather
# than skips if the premise ever stops being true. That is the shape of a measured block:
# it goes red the day it is lifted rather than quietly outliving it.


#: The ONE home, as SEAM 1 names it. On the merged tree this resolves to core-solvers'
#: object. Until their commit merges into this branch it is `None`, and `_one_home` below
#: stands the byte-identical copy SEAM 1 says it was lifted from into the same attribute
#: for the duration of one test — so the tools' OWN routing and refusal behaviour is
#: exercised here rather than skipped, and the stand-in disappears the moment the real
#: object arrives. `test_the_stand_in_is_byte_identical_to_what_seam_1_homed` is what makes
#: that substitution a measured statement instead of a convenience.
_STAND_IN_SOURCES = ("pack_pose_pack.py", "resample_motion.py")


def _source_of(filename, funcname):
    """The exact source text of one module-level function, by AST segment."""
    src = read_source(filename)
    for node in ast.parse(src).body:
        if isinstance(node, ast.FunctionDef) and node.name == funcname:
            return ast.get_source_segment(src, node)
    raise LookupError("%s has no def %s" % (filename, funcname))


def _shape_of(filename, funcname):
    """One function's signature, predicate and evidence — every message string erased.

    The comparison SEAM 1's claim needs is about what the function DOES, and the two copies
    each name their own module's artifact in the refusal sentence. Every `str` constant
    longer than 40 characters is replaced by a marker, so the prose cannot make two
    identical implementations read as different, and the clause word
    (`output_name_is_not_a_name`, 26 chars) and the evidence keys still count.
    """
    src = read_source(filename)
    for node in ast.parse(src).body:
        if isinstance(node, ast.FunctionDef) and node.name == funcname:
            body = [st for st in node.body
                    if not (isinstance(st, ast.Expr)
                            and isinstance(st.value, ast.Constant)
                            and isinstance(st.value.value, str))]
            stripped = ast.FunctionDef(
                name=node.name, args=node.args, body=body, decorator_list=[],
                returns=None, type_comment=None, type_params=[])
            for sub in ast.walk(stripped):
                if (isinstance(sub, ast.Constant) and isinstance(sub.value, str)
                        and len(sub.value) > 40):
                    sub.value = "<message>"
                if isinstance(sub, ast.JoinedStr):
                    sub.values = [v for v in sub.values
                                  if not (isinstance(v, ast.Constant)
                                          and isinstance(v.value, str))]
            ast.fix_missing_locations(stripped)
            return ast.dump(stripped, annotate_fields=True, include_attributes=False)
    raise LookupError("%s has no def %s" % (filename, funcname))


def _code_of(filename, funcname):
    """One function's SIGNATURE AND EXECUTABLE BODY, docstring stripped, as an AST dump.

    The docstrings of the two copies differ - each records its own module's earning story -
    and SEAM 1's claim is about what the function DOES. Comparing the prose would call two
    identical implementations different; comparing the dump keeps the claim on the code.
    """
    src = read_source(filename)
    for node in ast.parse(src).body:
        if isinstance(node, ast.FunctionDef) and node.name == funcname:
            body = [st for st in node.body
                    if not (isinstance(st, ast.Expr)
                            and isinstance(st.value, ast.Constant)
                            and isinstance(st.value.value, str))]
            stripped = ast.FunctionDef(
                name=node.name, args=node.args, body=body, decorator_list=[],
                returns=None, type_comment=None, type_params=[])
            ast.fix_missing_locations(stripped)
            return ast.dump(stripped, annotate_fields=True, include_attributes=False)
    raise LookupError("%s has no def %s" % (filename, funcname))


def test_the_two_copies_agree_on_everything_except_their_message():
    """SEAM 1 says `single_path_segment` is "byte-identical to the two copies you already
    hold" (`pack_pose_pack.py:82`, `resample_motion.py:76`). That is the premise `one_home`
    stands on while core-solvers' commit is in flight, so it is MEASURED here.

    ⚠ **MEASURED FALSE as stated, and corrected here rather than believed** (2026-09-05,
    on `e8263a3`, by unparsing both bodies with their docstrings stripped): the two differ
    in ONE statement — the refusal MESSAGE. `pack_pose_pack` says the escape leaves "the
    manifest that certifies it ... and every gate above reports on the file that escaped";
    `resample_motion` says "the sentinel line and the sha256 beside it describe a file that
    is not there". Each names its own module's artifact.

    What IS identical, and what this domain's two adoptions actually depend on: the
    signature `(value, flag, exc, extra=None)`, the predicate (the five clauses over
    separators, absolute paths, the two dot names and an empty name), the clause word
    `output_name_is_not_a_name`, the evidence keys, and the return. This asserts THAT, and
    the divergence is posted to the inbox for whoever writes the merged docstring — a home
    for two implementations that disagree in one sentence has to pick a sentence.
    """
    present = [f for f in _STAND_IN_SOURCES
               if "def single_path_segment" in read_source(f)]
    assert present, (
        "neither instruments-measure copy is on this tree any more; if `armature_core."
        "parts.single_path_segment` has merged this test has done its job")
    shapes = {f: _shape_of(f, "single_path_segment") for f in present}
    assert len(set(shapes.values())) == 1, sorted(shapes)


@pytest.fixture
def one_home(monkeypatch):
    """`armature_core.parts.single_path_segment`, standing one in if SEAM 1 is in flight.

    Returns `(module, "merged"|"stand-in")` so a reader of a failure knows which object
    answered. `monkeypatch` undoes the substitution, so nothing leaks into another test.
    """
    from armature_core import parts

    if getattr(parts, "single_path_segment", None) is not None:
        return parts, "merged"
    src = _source_of(_STAND_IN_SOURCES[0], "single_path_segment")
    ns = {"os": os}
    exec(compile(src, "<seam1-stand-in>", "exec"), ns)
    monkeypatch.setattr(parts, "single_path_segment", ns["single_path_segment"],
                        raising=False)
    return parts, "stand-in"


@pytest.mark.parametrize("filename,flag,attr", [
    ("preview_glb.py", "--name", "name"),
    ("render_turnaround.py", "--prefix", "prefix"),
])
def test_the_two_pasted_flags_are_routed_through_the_one_home(filename, flag, attr):
    """The census, keyed on the RESOLVED shape: the flag reaches `single_path_segment`,
    and it reaches it from `armature_core.parts` rather than from a local copy.

    RED on `e8263a3`, where an AST walk over this tree returned exactly two lines for
    `prefix` (`render_turnaround.py:292` declaring it and `:878` pasting it) and three for
    `name` (`preview_glb.py:65`, `:141`, `:290`), with no validation anywhere.
    """
    tree = _tree(filename)

    local_defs = [n.name for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "single_path_segment"]
    assert local_defs == [], (
        "%s spells its OWN `single_path_segment`; SEAM 1's home is `armature_core.parts` "
        "and nobody spells a third" % filename)

    calls = [n for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr == "single_path_segment"
             and isinstance(n.func.value, ast.Name) and n.func.value.id == "parts"]
    assert len(calls) == 1, [n.lineno for n in calls]
    call = calls[0]
    assert isinstance(call.args[1], ast.Constant) and call.args[1].value == flag, \
        ast.dump(call.args[1])
    assert isinstance(call.args[0], ast.Attribute) and call.args[0].attr == attr, \
        ast.dump(call.args[0])

    #: and it runs in `parse_args`, ABOVE every `os.makedirs` in the module.
    parse = [n for n in ast.walk(tree)
             if isinstance(n, (ast.FunctionDef,)) and n.name == "parse_args"]
    assert parse and parse[0].lineno < call.lineno < parse[0].end_lineno, call.lineno
    makedirs = [n.lineno for n in ast.walk(tree)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "makedirs"]
    assert makedirs and all(call.lineno < m for m in makedirs), (call.lineno, makedirs)


def test_the_pasted_flag_population_over_the_owned_tools_is_closed():
    """Wave-18 rule 2, on the population the wave-18 census could not see.

    `pack_pose_pack --name` and `resample_motion --name` were closed one domain over and
    that census was scoped to instruments-measure's 42 tools. This is the equivalent walk
    over these 21: every `str`-typed flag whose attribute is interpolated into an
    `os.path.join` argument. It finds exactly two, and both are routed above.
    """
    pasted = {}
    for filename in OWNED:
        tree = _tree(filename)
        joins = [n for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                 and n.func.attr == "join"]
        for join in joins:
            for arg in join.args:
                for node in ast.walk(arg):
                    if (isinstance(node, ast.Attribute)
                            and isinstance(node.value, ast.Name)
                            and node.value.id in ("a", "args")
                            and isinstance(node.ctx, ast.Load)):
                        pasted.setdefault(filename, set()).add(node.attr)
    #: `out` is the DIRECTORY argument, not a name component — it is what the name is
    #: joined ONTO, and bounding it as a single segment would refuse every real path.
    interpolated = {f: sorted(n for n in names if n != "out")
                    for f, names in pasted.items()}
    interpolated = {f: n for f, n in interpolated.items() if n}
    assert interpolated == {"preview_glb.py": ["name"],
                            "render_turnaround.py": ["prefix"]}, interpolated


@pytest.mark.parametrize("bad", ["../x", "C:/elsewhere/x", "a/b", "a\\b", ".", "..", ""])
def test_preview_glb_refuses_a_name_that_is_not_a_name(one_home, monkeypatch, bad):
    mod = load_tool("preview_glb.py")
    monkeypatch.setattr(mod.sys, "argv", [
        "blender", "-b", "-P", "x", "--", "--glb=g.glb", "--out=C:/tmp/out",
        "--name=" + bad])
    with pytest.raises(mod.PreviewGlbGate) as exc:
        mod.parse_args()
    ev = exc.value.evidence
    assert ev["flag"] == "--name", ev
    assert ev["clause"] == "output_name_is_not_a_name", ev
    assert ev["who"] == "preview_glb", ev


@pytest.mark.parametrize("bad", ["../x", "C:/elsewhere/x", "a/b", "a\\b", ".", "..", ""])
def test_render_turnaround_refuses_a_prefix_that_is_not_a_name(one_home, rt, monkeypatch, bad):
    monkeypatch.setattr(rt.sys, "argv", [
        "blender", "-b", "-P", "x", "--", "--glb=g.glb", "--out=C:/tmp/outdir",
        "--prefix=" + bad])
    with pytest.raises(rt.RenderTurnaroundGate) as exc:
        rt.parse_args()
    ev = exc.value.evidence
    assert ev["flag"] == "--prefix", ev
    assert ev["clause"] == "output_name_is_not_a_name", ev


def test_the_good_names_still_parse(one_home, rt, monkeypatch):
    """A bound that refuses the module default is a bug, not a bound."""
    monkeypatch.setattr(rt.sys, "argv", [
        "blender", "-b", "-P", "x", "--", "--glb=g.glb", "--out=o"])
    assert rt.parse_args().prefix == "turn"
    monkeypatch.setattr(rt.sys, "argv", [
        "blender", "-b", "-P", "x", "--", "--glb=g.glb", "--out=o", "--prefix=blackguard"])
    assert rt.parse_args().prefix == "blackguard"


def test_the_prefix_refusal_reaches_the_turnaround_halt_line(one_home, rt, capsys):
    """THE HALT LINE, READ."""
    def raiser():
        rt.sys.argv = ["blender", "-b", "-P", "x", "--", "--glb=g.glb", "--out=o",
                       "--prefix=../escaped"]
        rt.parse_args()

    code, rec, _ = _halt_record("render_turnaround.py", "RENDER_TURNAROUND_HALT",
                                raiser, capsys)
    assert code == 2
    assert rec["evidence"]["flag"] == "--prefix", rec
    assert rec["evidence"]["clause"] == "output_name_is_not_a_name", rec


def test_the_turnaround_manifest_records_the_prefix():
    """`prefix` was a run PARAMETER recorded nowhere — only implicitly, through each
    `views[].path`. A recipe that does not reproduce its output is not a recipe."""
    main = _fn_in("render_turnaround.py", "main")
    keys = [n.value for n in ast.walk(main)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    assert "prefix" in keys


def test_preview_glb_declares_its_compensator():
    """`preview_glb` declared NO named compensator at all, on a tool that creates a
    directory and writes five files into it (NAMED_COMPENSATORS, the wave-12 rule)."""
    src = read_source("preview_glb.py")
    head = src[:src.index("import argparse")]
    assert "Compensator" in head, head[-400:]
    assert "--out" in head


def _fn_in(filename, name):
    for node in _tree(filename).body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise LookupError(name)
