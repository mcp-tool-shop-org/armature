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
# instruments-measure deleted its two copies (`pack_pose_pack.py`, `resample_motion.py`) and
# builders adopts the same object for `fetch_run --run`. Instruments ADOPTS BY IMPORT and
# spells nothing locally.
#
# WAVE-22 MERGE (coordinator, 2026-09-05): the seam has LANDED. On the branch this module was written on the
# helper did not exist yet, so `tests/conftest.py` carried a session-scoped bridge that stood
# the `pack_pose_pack` copy in under the same name, `_STAND_IN_SOURCES` / `_shape_of` measured
# that the two copies agreed on everything but their refusal sentence, and `one_home` below
# reported which object answered. All of that was scaffolding for a tree that no longer
# exists: `armature_core.parts.single_path_segment` is on the merged tree, both copies are
# deleted, and `test_the_two_copies_agree_on_everything_except_their_message` went red on
# the merged tree by its own design ("if `armature_core.parts.single_path_segment` has
# merged this test has done its job"). The bridge, the stand-in sources, the three AST
# shape helpers and that test are deleted here; what remains asserts the merged state.


def test_single_path_segment_has_exactly_one_home():
    """The merged-tree statement of SEAM 1: ONE implementation, in `armature_core.parts`,
    and no `tools/*.py` spells a copy. RED on `e8263a3`, where `pack_pose_pack.py:82` and
    `resample_motion.py:76` each held one and the package held none.
    """
    import inspect

    from armature_core import parts

    fn = getattr(parts, "single_path_segment", None)
    assert inspect.isfunction(fn), "SEAM 1's home is missing from `armature_core.parts`"
    assert fn.__module__ == "armature_core.parts", fn.__module__
    copies = []
    for name in sorted(os.listdir(TOOLS)):
        if not name.endswith(".py"):
            continue
        with open(os.path.join(TOOLS, name), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        if any(isinstance(n, ast.FunctionDef) and n.name == "single_path_segment"
               for n in tree.body):
            copies.append(name)
    assert copies == [], ("a tool spells its OWN `single_path_segment`; SEAM 1's home is "
                          "`armature_core.parts` and nobody spells a second", copies)


def test_seam_1_is_the_one_home_on_a_merged_tree():
    """SEAM 1's helper is on the tree — the object the two parsers call, not a stand-in.

    `preview_glb --name` and `render_turnaround --prefix` call
    `armature_core.parts.single_path_segment` with no local copy and no fallback, because
    "nobody spells a third". While core-solvers' commit was in flight this test skipped
    behind `tests/conftest.py`'s bridge; the bridge is gone, so a missing attribute here is
    the `AttributeError` production would raise, and it fails rather than skips.
    """
    from armature_core import parts

    fn = getattr(parts, "single_path_segment", None)
    assert fn is not None, "the merged home did not resolve `single_path_segment`"
    assert fn.__module__ == "armature_core.parts", fn.__module__


@pytest.fixture
def one_home():
    """`armature_core.parts.single_path_segment`, and the word "merged".

    WAVE-22 MERGE (coordinator, 2026-09-05): this fixture used to stand the `pack_pose_pack` copy in while
    SEAM 1 was in flight and returned `(module, "merged"|"stand-in")` so a failure named
    which object answered. The seam landed; only the merged object exists, and the four
    tests below keep reading the pair so their failure messages still say so.
    """
    from armature_core import parts

    assert getattr(parts, "single_path_segment", None) is not None
    return parts, "merged"


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


# ===========================================================================
# F-0b201a20 — PROBE_GLB_OK is earned by an effect, and a refused run leaves nothing.
# ===========================================================================


@pytest.fixture(scope="module")
def pglb():
    return load_tool("probe_glb.py")


def test_probe_glb_refuses_named_paths_that_are_not_files(pglb, tmp_path, monkeypatch):
    """MEASURED on `e8263a3` under `blender_stub.blender_stubbed()`: `probe_one('nope_a.glb')`
    and `probe_one('nope_b.glb')` returned `{'exists': False, 'clause_A_loads': False,
    'error': 'file not found'}` rows, `main` never inspected that field, and the summary it
    builds from them is `{'n_files': 2, 'clause_A_loads': 0, ...}` — `n_files` counting
    ARGUMENTS. `hasattr(module, 'require_openable')` was False.

    This is the rule E07 earned — "verify a success sentinel in the output, never the exit
    code alone" — answered with a sentinel counting subjects that were never probed.
    """
    a, b = tmp_path / "nope_a.glb", tmp_path / "nope_b.glb"
    monkeypatch.setattr(pglb.sys, "argv", [
        "blender", "-b", "-P", "x", "--", "--out=" + str(tmp_path / "out"),
        "--glb=" + str(a), "--glb=" + str(b)])
    from armature_core.errors import ArmatureError   # inside the test: Trap A
    with pytest.raises(ArmatureError) as exc:
        pglb.main()
    assert "nope_a.glb" in str(exc.value) and "nope_b.glb" in str(exc.value)
    assert not (tmp_path / "out").exists(), (
        "a refused run created its output directory; a later run reads an empty one as used")
    assert not list(tmp_path.glob("**/p2_armatures.json"))


def test_probe_glb_creates_its_directory_below_the_whole_measurement():
    """`os.makedirs` sat ABOVE the population (`records = [probe_one(p) for p in globs]`)
    where `probe_subject.py:227` sits below `require_openable` and below the measurement.

    Keyed on the RESOLVED ordering inside `main`, not on the line numbers.
    """
    main = _fn_in("probe_glb.py", "main")
    makedirs = [n.lineno for n in ast.walk(main)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "makedirs"]
    openable = [n.lineno for n in ast.walk(main)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "require_openable"]
    probes = [n.lineno for n in ast.walk(main)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
              and n.func.id == "probe_one"]
    assert len(makedirs) == 1 and openable and probes, (makedirs, openable, probes)
    assert openable[0] < makedirs[0], (openable, makedirs)
    assert probes[0] < makedirs[0], (probes, makedirs)


def test_there_is_one_require_openable_and_two_callers():
    """One implementation, imported — never a second copy. The wave-12 fix's own docstring
    enumerated the tools it had checked (`check_relift.py:185-187` "already refuses
    outright") and did not name `probe_glb.py`, which carries a character-identical
    `probe_one` opening and `parse_argv`."""
    defs = [f for f in OWNED
            if any(isinstance(n, ast.FunctionDef) and n.name == "require_openable"
                   for n in _tree(f).body)]
    assert defs == ["probe_subject.py"], defs
    callers = sorted(f for f in OWNED
                     if any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                            and n.func.id == "require_openable"
                            for n in ast.walk(_tree(f))))
    assert callers == ["probe_glb.py", "probe_subject.py"], callers


def test_the_probe_glb_refusal_reaches_the_halt_line(pglb, tmp_path, capsys):
    """THE HALT LINE, READ. A bare `ArmatureError` is a REFUSAL, exit 2, gate null."""
    def raiser():
        pglb.require_openable([str(tmp_path / "nope.glb")])

    code, rec, _ = _halt_record("probe_glb.py", "PROBE_GLB_HALT", raiser, capsys)
    assert code == 2
    assert rec["outcome"].startswith("REFUSED"), rec
    assert rec["gate"] is None, rec
    assert "nope.glb" in rec["message"], rec


# ===========================================================================
# F-833343df — two andons, two clause strings, on all three dailies sheets.
# ===========================================================================


class _Verts:
    """A rest-frame vertex array `subject_scale` can measure a diagonal from."""

    def __init__(self, span=1.0):
        import numpy as np
        self.arr = np.array([[0.0, 0.0, 0.0], [span, span, span]], dtype="float64")


@pytest.fixture(scope="module")
def sheet():
    return load_tool("make_parts_sheet.py")


def _at_rest(span=1.0):
    import numpy as np
    return np.array([[0.0, 0.0, 0.0], [span, span, span]], dtype="float64")


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_a_non_finite_displacement_gets_its_own_clause_and_its_own_andon(sheet, bad):
    """RE-MEASURED end-to-end on `e8263a3`: `arc_liveness(nan, 'max_displacement', at_rest,
    'make_parts_sheet')` halted at exit 2 with `"error": "ArmatureError"` and
    `"evidence": {"clause": "arc_did_not_survive", ...}` — the bare family, under the OTHER
    clause's name. Two distinct andons published one clause string and the second named no
    andon at all."""
    with blender_stubbed():
        with pytest.raises(sheet.ArcMeasurementNotFinite) as exc:
            sheet.arc_liveness(bad, "max_displacement", _at_rest(), "make_parts_sheet")
    ev = exc.value.evidence
    assert ev["clause"] == "measurement_not_finite", ev
    assert ev["andon"] == "ArcMeasurementNotFinite", ev
    assert ev["measurement"] == "max_displacement", ev
    assert ev["where"] == "make_parts_sheet", ev
    assert "bbox_diagonal" in ev and "floor" in ev, ev


def test_a_finite_but_too_small_displacement_keeps_the_survival_clause(sheet):
    """The two must not be confusable from the halt line alone: this one returns the
    evidence with `survived: False` under `arc_did_not_survive`, and each sheet raises its
    own `ArcDidNotSurvive` at the line where its own arc died."""
    with blender_stubbed():
        ev, diagonal, _lo, _hi = sheet.arc_liveness(
            0.0, "max_displacement", _at_rest(), "make_parts_sheet")
    assert ev["clause"] == "arc_did_not_survive", ev
    assert ev["andon"] == "ArcDidNotSurvive", ev
    assert ev["survived"] is False
    assert ev["max_displacement"] == 0.0
    assert diagonal > 0.0


def test_a_live_arc_still_reports_survived(sheet):
    with blender_stubbed():
        ev, _d, _lo, _hi = sheet.arc_liveness(
            0.5, "max_displacement", _at_rest(), "make_parts_sheet")
    assert ev["survived"] is True


def test_all_three_sheets_reach_the_one_arc_liveness():
    """One change covers all three: `make_binding_sheet` and `make_rig_sheet` import this
    function from `make_parts_sheet` rather than spelling their own."""
    defs = [f for f in OWNED
            if any(isinstance(n, ast.FunctionDef) and n.name == "arc_liveness"
                   for n in _tree(f).body)]
    assert defs == ["make_parts_sheet.py"], defs
    callers = sorted(f for f in OWNED
                     if any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                            and n.func.id == "arc_liveness"
                            for n in ast.walk(_tree(f))))
    assert callers == ["make_binding_sheet.py", "make_parts_sheet.py",
                       "make_rig_sheet.py"], callers


def test_the_non_finite_arc_refusal_reaches_the_halt_line(sheet, capsys):
    """THE HALT LINE, READ — and it now names which of the two andons pulled."""
    def raiser():
        sheet.arc_liveness(float("nan"), "max_displacement", _at_rest(),
                           "make_parts_sheet")

    code, rec, _ = _halt_record("make_parts_sheet.py", "MAKE_PARTS_SHEET_HALT",
                                raiser, capsys)
    assert code == 2
    assert rec["outcome"].startswith("REFUSED"), rec
    assert rec["error"] == "ArcMeasurementNotFinite", rec
    assert rec["evidence"]["clause"] == "measurement_not_finite", rec


# ===========================================================================
# F-897a3329 — the halt line is STRICT JSON, for the family that made it not be.
# ===========================================================================


def _strict(payload):
    """`json.loads` with `parse_constant` armed — what every parser but CPython's does."""
    def refuse(token):
        raise ValueError("not JSON: bare constant " + token)

    return json.loads(payload, parse_constant=refuse)


@pytest.mark.parametrize("filename", OWNED)
def test_a_non_finite_operand_leaves_the_halt_line_strict_json(filename, capsys):
    """The halt contract promises "stdout EXACTLY ONE line `<STEM>_HALT <json object>`",
    and for exactly the refusal family wave 16 added — the NaN andons — the object was not
    JSON. `parts.require_finite` writes the offending value into the evidence
    (`ev[name] = v`, `armature_core/parts.py::require_finite`), the handler serialised it with
    `json.dumps(_sentinel, default=str)`, and `default=` applies to values Python CANNOT
    encode, never to a float it can: `allow_nan` defaults True, so the line carried the
    bare token `NaN`. `json.loads(payload)` ACCEPTS it — which is why every reader in this
    suite was green — and `json.loads(payload, parse_constant=<raise>)` REJECTS it, as
    would JS `JSON.parse`, Go `encoding/json` and serde.

    Driven over ALL 21 owned tools, not the one the finding was filed against: the same
    `json.dumps(_sentinel, default=str)` line was in 22 files (the 22nd, `stage_render.py`,
    is instruments-measure's and is posted to the inbox).
    """
    from armature_core.errors import GateFailure

    class _NaNGate(GateFailure):
        gate = "NAN_PROBE"

    def raiser():
        raise _NaNGate("a measurement that is not a number", {
            "clause": "measurement_not_finite",
            "floor": 0.00017320508075688773,
            "max_displacement": float("nan"),
            "span": float("inf"),
            "low": float("-inf"),
            "nested": [{"deep": float("nan")}],
        })

    code, escaped = exit_code_of_main_block(filename, raiser=raiser)
    assert escaped is None, escaped
    assert code == 2, code
    prefix = filename[:-3].upper() + "_HALT "
    lines = [l for l in capsys.readouterr().out.splitlines() if l.startswith(prefix)]
    assert len(lines) == 1, lines
    payload = lines[0][len(prefix):]
    rec = _strict(payload)          # RED on e8263a3: ValueError, bare constant NaN
    ev = rec["evidence"]
    #: and the operand is still READABLE — not a null that erases which value it was.
    assert ev["max_displacement"] == "nan", ev
    assert ev["span"] == "inf" and ev["low"] == "-inf", ev
    assert ev["nested"][0]["deep"] == "nan", ev
    assert ev["floor"] == 0.00017320508075688773, ev


def test_the_value_clause_is_spelled_the_same_way_in_all_twenty_one():
    """The 21 copies cannot drift. `tests/test_instruments_amend_w14.py` already asserts
    every `_render_status` copy is byte-identical; this is the same rule for the clause
    this wave added, until SEAM 1's `run_tool_main` absorbs all 21 handlers into one."""
    bodies = {}
    for fn in OWNED:
        for node in _tree(fn).body:
            if isinstance(node, ast.FunctionDef) and node.name == "_halt_keysafe":
                body = [st for st in node.body
                        if not (isinstance(st, ast.Expr)
                                and isinstance(st.value, ast.Constant))]
                bodies.setdefault(
                    tuple(ast.unparse(st) for st in body), []).append(fn)
    assert len(bodies) == 1, {len(v): v for v in bodies.values()}
    assert len(next(iter(bodies.values()))) == 21


def test_every_owned_handler_serialises_with_allow_nan_false():
    """The census, on the RESOLVED shape: the keyword, wherever the call is spelled."""
    missing = []
    for fn in OWNED:
        for node in ast.walk(_tree(fn)):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "dumps"
                    and any(isinstance(a, ast.Name) and a.id == "_sentinel"
                            for a in node.args)
                    and any(k.arg == "default" for k in node.keywords)):
                if not any(k.arg == "allow_nan"
                           and isinstance(k.value, ast.Constant)
                           and k.value.value is False for k in node.keywords):
                    missing.append((fn, node.lineno))
    assert missing == [], missing


# ===========================================================================
# F-e472aa37 — the retopo manifest cannot state two accounts of one voxel size.
# ===========================================================================


@pytest.fixture(scope="module")
def retopo():
    return load_tool("rig_retopo.py")


@pytest.mark.parametrize("bad", [0.0, -0.0, -0.005, float("nan"), float("inf")])
def test_an_explicit_voxel_that_is_not_a_size_is_refused_by_name(retopo, bad):
    """RE-MEASURED on `e8263a3`: `:400` was `args["voxel"] if args["voxel"] else
    smallest_r * VOXEL_PER_SMALLEST_RADIUS` — a TRUTHINESS test on a float declared
    `type=float, default=None` — so an explicit `--voxel=0.0` (or `-0.0`) silently fell
    through to the derived value with nothing saying the given number was discarded. With
    `VOXEL_PER_SMALLEST_RADIUS = 1/6` and a smallest limb radius of 0.01301, both produced
    voxel 0.00217 under `voxel_derivation: "smallest measured limb radius"`, the override
    erased without a word. The wave-16 rule: a clause keys on the VALUE, never on presence
    or truthiness."""
    from armature_core import parts

    ev = {"gate": retopo.VoxelOverrideRefused.gate, "flag": "--voxel"}
    with pytest.raises(retopo.VoxelOverrideRefused) as exc:
        parts.require_finite("--voxel", bad, retopo.VoxelOverrideRefused, ev,
                             positive=True)
    assert "--voxel" in str(exc.value)


def test_the_voxel_branch_keys_on_is_not_none(retopo):
    """The census, on the RESOLVED shape: `main` binds the branch off `is not None`."""
    main = _fn_in("rig_retopo.py", "main")
    src = read_source("rig_retopo.py")
    given = [n for n in ast.walk(main)
             if isinstance(n, ast.Assign) and len(n.targets) == 1
             and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "voxel_given"]
    assert given, "main no longer names the branch"
    text = ast.get_source_segment(src, given[0].value)
    assert "is not None" in text, text
    #: and no truthiness test on the flag survives anywhere in `main`.
    for node in ast.walk(main):
        if isinstance(node, ast.IfExp):
            assert 'args["voxel"]' != ast.get_source_segment(src, node.test), (
                "the ternary still keys on truthiness at line %d" % node.lineno)


def test_the_route_and_the_derivation_are_built_in_one_branch(retopo):
    """MEASURED on `e8263a3`: `:425-426` wrote `"route": f"voxel remesh at {voxel:.5f} (=
    {smallest_name} radius {smallest_r:.5f} / 6)"` UNCONDITIONALLY while `:428-431` wrote
    `voxel_derivation` under the branch — so `--voxel=0.005` on a 0.01301 forearm produced
    `route: 'voxel remesh at 0.00500 (= forearm radius 0.01301 / 6)'` (0.01301/6 is
    0.00217, not 0.00500) directly above `voxel_derivation: 'explicit override ...'`. One
    record, two contradictory accounts of where its voxel size came from, and a reader
    deciding which arm won reads the false one first."""
    src = read_source("rig_retopo.py")
    main = _fn_in("rig_retopo.py", "main")
    binds = {}
    for node in ast.walk(main):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)):
            binds.setdefault(node.targets[0].id, []).append(node)
    assert len(binds.get("voxel_route", [])) == 2, binds.get("voxel_route")
    assert len(binds.get("voxel_derivation", [])) == 2, binds.get("voxel_derivation")
    #: the two are built in the SAME two branches — the arithmetic clause appears in the
    #: derived arm only, and nowhere in the override arm.
    derived_route = [ast.get_source_segment(src, n.value) for n in binds["voxel_route"]]
    assert sum("/ 6" in t for t in derived_route) == 1, derived_route
    assert sum("explicit --voxel override" in t for t in derived_route) == 1, derived_route
    #: and the manifest reads the names rather than rebuilding either string.
    manifest_route = [n for n in ast.walk(main)
                      if isinstance(n, ast.Name) and n.id == "voxel_route"]
    assert len(manifest_route) >= 3, len(manifest_route)


def test_the_voxel_refusal_reaches_the_retopo_halt_line(retopo, capsys):
    """THE HALT LINE, READ."""
    from armature_core import parts

    def raiser():
        parts.require_finite(
            "--voxel", 0.0, retopo.VoxelOverrideRefused,
            {"gate": retopo.VoxelOverrideRefused.gate, "sub_gate": "VOXEL",
             "andon": retopo.VoxelOverrideRefused.__name__, "who": "rig_retopo",
             "flag": "--voxel", "clause": "voxel_not_finite_and_positive"},
            positive=True)

    code, rec, _ = _halt_record("rig_retopo.py", "RIG_RETOPO_HALT", raiser, capsys)
    assert code == 2
    assert rec["gate"] == "RETOPO_ARGS", rec
    assert rec["evidence"]["clause"] == "voxel_not_finite_and_positive", rec
    assert rec["evidence"]["flag"] == "--voxel", rec


# ===========================================================================
# F-f25774c2 — gate_coverage's floor goes through the ONE `tightened`.
# ===========================================================================


@pytest.fixture(scope="module")
def performer():
    return load_tool("render_performer.py")


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1.0])
def test_gate_coverage_refuses_a_floor_the_inline_comparison_walked_past(performer, bad):
    """RE-MEASURED on `e8263a3` against `MIN_SUBJECT_FRAC`: the inline
    `if min_frac > MIN_SUBJECT_FRAC` does NOT fire for `nan` or `-1.0`, both of which
    `parts.tightened` refuses with a typed gate — and with a NaN floor this gate's own
    refusal clause (`if worst["frac"] < min_frac`) is False for every frame (`0.0 < nan` is
    False), so `gate_coverage` returned its PASS verdict over a set of frames with nobody in
    them: precisely the failure its docstring says it exists to catch."""
    with pytest.raises(performer.RenderGate) as exc:
        performer.gate_coverage([], "plate.png", min_frac=bad)
    ev = exc.value.evidence
    assert ev["gate"] == performer.RenderGate.gate, ev
    assert repr(bad) in repr(ev), ev


def test_a_nan_floor_never_reaches_the_per_frame_loop(performer, monkeypatch):
    """The andon is on the direction the invariant does not bound: not one pixel is read."""
    calls = []
    monkeypatch.setattr(performer, "_pixels", lambda p: calls.append(p))
    with pytest.raises(performer.RenderGate,
                       match=r"is not a finite number, so it cannot be compared") as exc:
        performer.gate_coverage(["a.png", "b.png"], "plate.png", min_frac=float("nan"))
    assert exc.value.evidence["gate"] == performer.RenderGate.gate
    assert calls == [], calls


def test_gate_coverage_still_accepts_a_tightening_and_the_module_floor(performer,
                                                                      monkeypatch):
    """Zero is the tightest legal request, and a bound that refuses correct work is the
    defect (`parts.tightened`'s own F-2a564189 correction, one band over)."""
    import numpy as np

    frames = {"plate.png": np.zeros((4, 3), dtype=np.float32),
              "a.png": np.ones((4, 3), dtype=np.float32)}
    monkeypatch.setattr(performer, "_pixels", lambda p: frames[p])
    for good in (performer.MIN_SUBJECT_FRAC, performer.MIN_SUBJECT_FRAC / 10.0, 0.0):
        ev = performer.gate_coverage(["a.png"], "plate.png", min_frac=good)
        assert ev["min_fraction"] == float(good), ev


def test_the_coverage_floor_is_the_one_implementation():
    """`armature_core.parts.tightened` is the repo's ONE spelling of this comparison, and
    this gate is the sixth member of the family F-196c4257 routed — `author_walk`'s Gates
    F/A/SPACE and `lift_solve`'s Gates SPACE/ARRIVED all go through it, and this one, whose
    docstring cites that same routed sweep, kept the inline comparison."""
    fn = None
    for node in _tree("render_performer.py").body:
        if isinstance(node, ast.FunctionDef) and node.name == "gate_coverage":
            fn = node
    assert fn is not None
    calls = [n for n in ast.walk(fn)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr == "tightened"]
    assert len(calls) == 1, [n.lineno for n in calls]
    #: and the inline comparison is gone — asked of the AST, never of the text, because
    #: the comment that records the defect quotes the very line it replaced.
    inline = [n for n in ast.walk(fn)
              if isinstance(n, ast.Compare)
              and isinstance(n.left, ast.Name) and n.left.id == "min_frac"
              and any(isinstance(o, ast.Gt) for o in n.ops)]
    assert inline == [], [n.lineno for n in inline]


# ===========================================================================
# F-feb363d9 — the two arc angles join require_subject_args' single clause.
# ===========================================================================


@pytest.fixture(scope="module")
def subject():
    return load_tool("make_test_armature.py")


def _args(subject_mod, **over):
    import argparse
    base = dict(pose_arc="arm_r_raise", frames=33, fps=16, segments=16,
                thickness=0.03, joint_scale=1.55, arc_start_deg=0.0, arc_end_deg=90.0,
                out="o")
    base.update(over)
    return argparse.Namespace(**base)


@pytest.mark.parametrize("flag,attr,bad", [
    ("--arc-start-deg", "arc_start_deg", float("nan")),
    ("--arc-start-deg", "arc_start_deg", float("inf")),
    ("--arc-start-deg", "arc_start_deg", 1e9),
    ("--arc-end-deg", "arc_end_deg", float("inf")),
    ("--arc-end-deg", "arc_end_deg", float("nan")),
    ("--arc-end-deg", "arc_end_deg", -1e9),
])
def test_the_two_arc_angles_are_named_in_the_single_clause(subject, flag, attr, bad):
    """RE-MEASURED on `e8263a3` by an AST walk over this parser: `--arc-start-deg` and
    `--arc-end-deg` were bare `type=float` and neither identifier appeared anywhere inside
    `require_subject_args`, whose own docstring calls itself "one clause listing every
    offending flag by name". They are the ones that BECOME the authored bone rotations in
    the `.joints.json` ground truth every arc comparison in this repo is measured against.
    `nan` and `inf` were refused only INCIDENTALLY — `arc_readout` raises `SpecError`
    because every comparison against a NaN is False, not because any clause examined the
    flag — and `arc_readout(arc, 33, 1e9, -1e9)` returned a NORMAL readout with no refusal
    at all, so 2.7 million turns per arm were authored into the ground truth and exported.
    """
    with pytest.raises(subject.SubjectArgError) as exc:
        subject.require_subject_args(_args(subject, **{attr: bad}))
    ev = exc.value.evidence
    assert any(flag in row for row in ev["offending"]), ev["offending"]
    assert ev["arc_deg_bound"] == subject.ARC_DEG_BOUND, ev
    assert ev[attr] == bad or (bad != bad and ev[attr] != ev[attr]), ev


def test_the_arc_angles_this_repo_actually_authors_are_accepted(subject):
    """The registered arcs are within one turn by construction, and the module defaults
    (0.0 .. 90.0) must not be refused by their own bound."""
    for start, end in ((0.0, 90.0), (-30.0, 30.0), (0.0, -360.0), (360.0, 0.0)):
        got = subject.require_subject_args(
            _args(subject, arc_start_deg=start, arc_end_deg=end))
        assert got.arc_start_deg == start and got.arc_end_deg == end


def test_the_arc_refusal_lands_above_resolve_arc_and_writes_nothing(subject):
    """The clause runs FIRST, above `posearc.resolve_arc`, so a refusal leaves no GLB and
    no `.joints.json` behind — the property the wave-16 fix earned for `--frames`."""
    main = _fn_in("make_test_armature.py", "main")
    calls = {}
    for node in ast.walk(main):
        if isinstance(node, ast.Call):
            name = (node.func.attr if isinstance(node.func, ast.Attribute)
                    else node.func.id if isinstance(node.func, ast.Name) else None)
            if name in ("require_subject_args", "resolve_arc", "makedirs"):
                calls.setdefault(name, []).append(node.lineno)
    assert calls["require_subject_args"][0] < calls["resolve_arc"][0], calls
    assert all(calls["require_subject_args"][0] < m for m in calls.get("makedirs", [])), calls


def test_the_arc_refusal_reaches_the_make_test_armature_halt_line(subject, capsys):
    """THE HALT LINE, READ — and it names the FLAG, not the arc registry's readout."""
    def raiser():
        subject.require_subject_args(_args(subject, arc_start_deg=1e9))

    code, rec, _ = _halt_record("make_test_armature.py", "MAKE_TEST_ARMATURE_HALT",
                                raiser, capsys)
    assert code == 2
    assert rec["outcome"].startswith("REFUSED"), rec
    assert rec["error"] == "SubjectArgError", rec
    assert any("--arc-start-deg" in row for row in rec["evidence"]["offending"]), rec


# ===========================================================================
# F-a2630f86 — the render half of Gate GLB's stale-target clause.
# ===========================================================================


@pytest.fixture(scope="module")
def rigc():
    return load_tool("rig_character.py")


def test_a_finished_render_over_an_untouched_file_is_refused(rigc, tmp_path):
    """The direction the three existing clauses cannot see. `FINISHED` in the status set,
    `os.path.isfile` and `getsize != 0` are exactly the three properties
    `gate_glb_written`'s own docstring names as insufficient: a PREVIOUS run's file at the
    same path satisfies all three."""
    target = tmp_path / "turn_0.png"
    target.write_bytes(b"PNG-from-the-previous-run")
    before = rigc.render_target_snapshot(str(target))
    assert before["existed"] is True

    with pytest.raises(rigc.GateGlbWritten) as exc:
        rigc.require_render_target_moved(str(target), before, rigc.GateGlbWritten,
                                         {"who": "test"}, what="the rendered frame")
    ev = exc.value.evidence
    assert ev["clause"] == "stale_render_target", ev
    assert ev["before"]["bytes"] == ev["after"]["bytes"], ev


def test_a_render_that_moved_the_bytes_passes(rigc, tmp_path):
    target = tmp_path / "turn_0.png"
    target.write_bytes(b"old")
    before = rigc.render_target_snapshot(str(target))
    target.write_bytes(b"a genuinely new frame")
    after = rigc.require_render_target_moved(str(target), before, rigc.GateGlbWritten)
    assert after["bytes"] == len(b"a genuinely new frame")


def test_a_first_render_into_an_empty_directory_passes(rigc, tmp_path):
    target = tmp_path / "turn_0.png"
    before = rigc.render_target_snapshot(str(target))
    assert before["existed"] is False
    target.write_bytes(b"drawn")
    assert rigc.require_render_target_moved(str(target), before, rigc.GateGlbWritten)


@pytest.mark.parametrize("bad", [None, {}, {"existed": None}, {"existed": "yes"}, 4])
def test_a_snapshot_that_was_never_taken_is_refused(rigc, tmp_path, bad):
    """Clause 0, keyed on the VALUE — `gate_glb_written`'s F-8548f859 shape carried. An
    optional-shaped argument IS a skip flag."""
    target = tmp_path / "turn_0.png"
    target.write_bytes(b"x")
    with pytest.raises(rigc.GateGlbWritten) as exc:
        rigc.require_render_target_moved(str(target), bad, rigc.GateGlbWritten)
    assert exc.value.evidence["clause"] == "no_pre_render_snapshot", exc.value.evidence


def test_every_render_write_site_in_the_five_renderers_takes_a_snapshot():
    """The census, keyed on the RESOLVED shape: every
    `bpy.ops.render.render(write_still=True)` in the five renderers is preceded, in its own
    scope, by a `render_target_snapshot` of the path it is about to write.

    RE-ENUMERATED on `e8263a3`: `export_target_snapshot` had NINE call sites and ZERO
    callers outside the export family, while the render write sites read only the three
    properties Gate GLB's docstring names as insufficient. ELEVEN write sites here, MEASURED
    rather than counted by hand — six in `render_start_frame`, two in `render_performer`,
    one each in `preview_walk`, `render_turnaround` and `preview_glb`.
    """
    renderers = ("preview_glb.py", "preview_walk.py", "render_performer.py",
                 "render_start_frame.py", "render_turnaround.py")
    total = 0
    for fn in renderers:
        tree = _tree(fn)
        for scope in ast.walk(tree):
            body = getattr(scope, "body", None)
            if not isinstance(body, list):
                continue
            for i, st in enumerate(body):
                if not (isinstance(st, ast.Assign)
                        and isinstance(st.value, ast.Call)
                        and ast.unparse(st.value).startswith("bpy.ops.render.render(")):
                    continue
                total += 1
                window = ast.unparse(ast.Module(body=body[max(0, i - 3):i],
                                                type_ignores=[]))
                assert "render_target_snapshot" in window, (
                    "%s:%d renders without a pre-render snapshot in its own scope"
                    % (fn, st.lineno))
    assert total == 11, total


def test_the_snapshot_helpers_have_exactly_one_home():
    """One implementation, imported by five renderers -- never a sixth copy."""
    defs = [f for f in OWNED
            if any(isinstance(n, ast.FunctionDef)
                   and n.name in ("render_target_snapshot",
                                  "require_render_target_moved")
                   for n in _tree(f).body)]
    assert defs == ["rig_character.py"], defs
    callers = sorted(
        f for f in OWNED
        if any(isinstance(n, ast.Attribute)
               and n.attr in ("render_target_snapshot", "require_render_target_moved")
               for n in ast.walk(_tree(f))))
    assert callers == ["preview_glb.py", "preview_walk.py", "render_performer.py",
                       "render_start_frame.py", "render_turnaround.py"], callers


def test_the_stale_render_refusal_reaches_a_halt_line(rigc, tmp_path, capsys):
    """THE HALT LINE, READ, on one of the five."""
    target = tmp_path / "turn_0.png"
    target.write_bytes(b"the previous run's frame")
    before = rigc.render_target_snapshot(str(target))

    turn = load_tool("render_turnaround.py")

    def raiser():
        turn.rc.require_render_target_moved(
            str(target), before, turn.RenderTurnaroundGate,
            {"gate": turn.RenderTurnaroundGate.gate, "sub_gate": "RENDER_TARGET",
             "who": "render_turnaround"})

    code, rec, _ = _halt_record("render_turnaround.py", "RENDER_TURNAROUND_HALT",
                                raiser, capsys)
    assert code == 2
    assert rec["gate"] == "TURNAROUND", rec
    assert rec["evidence"]["clause"] == "stale_render_target", rec
    assert rec["evidence"]["before"]["existed"] is True, rec
