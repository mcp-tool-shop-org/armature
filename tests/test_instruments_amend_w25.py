"""Wave 25, the instruments domain: seven approved findings, each with its own census.

Every check here is a PROPERTY over a DERIVED population, never a list of the sites someone
remembered. That rule is why five of the seven findings exist at all: each is a family whose
first sweep enumerated the members by hand and stopped one module short — the render-target
snapshot adopted at five renderers and not at the three sheets, the operator-status clause
asked of two Blender operators and not the third, the compensator paragraph written for
seven modules and not the other fourteen, the `clause` key required of `armature_core/**`
and not of `tools/*.py`, the success sentinel's payload agreed on by twenty modules and not
the twenty-first.

Helpers under `tests/` **raise**; they never `assert` outside a test function — `-O` deletes
an `assert` in a non-plugin helper.
"""

import ast
import gc
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import _census_nodes as CN                                          # noqa: E402
import blender_stub                                                 # noqa: E402
from test_instruments_amend_w14 import (                            # noqa: E402
    RENDER_SITE_MODULES_TODAY, RENDER_SITES_TODAY, _operator_call_sites, census_sources)

from armature_core.errors import ArmatureError                      # noqa: E402

TESTS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TESTS)
TOOLS = os.path.join(REPO, "tools")

#: The 21 Blender-side instruments this domain owns. Spelled once here and derived
#: nowhere, because it IS the domain boundary — a glob over `tools/*.py` would silently
#: absorb instruments-measure's 42 and answer a different question.
OWNED = (
    "author_walk", "check_relift", "diagnose_bone_heat", "lift_solve",
    "make_binding_sheet", "make_parts_sheet", "make_rig_sheet", "make_skeleton_sheet",
    "make_test_armature", "preview_glb", "preview_walk", "probe_glb", "probe_subject",
    "render_performer", "render_start_frame", "render_turnaround", "rig_bake",
    "rig_character", "rig_parts", "rig_repair", "rig_retopo",
)


def owned_trees():
    """`{module: ast.Module}` for the 21, read from disk each call."""
    return {name: ast.parse(CN.read_source(name)) for name in OWNED}


# =======================================================================================
# F-3b71c0aa (panel HIGH) — every family raise in the 21 tools names the clause that pulled
# =======================================================================================
#
# MEASURED on `580af47` by pointing wave 22's own resolved-class walk at the 21 owned tools
# instead of the 21 `armature_core` modules: 150 resolved family raises, **78 with no
# `clause` a halt reader can key on** — 43 carrying an evidence dict without the key and 35
# carrying no evidence at all, which the shared handler serialises as `"evidence": null`.
# The 78 were spread over 19 of the 21 modules. The sharpest member was the LICENCE andon in
# `render_start_frame.build_wood_material`: it exists because CLAUDE.md bans a
# non-commercially-licensed asset outright, it conditions the image a paid generation is
# submitted with, and its only identifier on the halt line was the class attribute
# `gate = "STARTFRAME"` — shared with six other STARTFRAME refusals.
#
# Why nothing was red: `tests/_census_nodes.clause_literals()` enumerates the clause words
# that EXIST and has no complement, and the complement property (`== []`) was asserted for
# `armature_core/**` only. The WALK now has one home (`_census_nodes`) and two populations.


@pytest.fixture(autouse=True)
def _drop_tool_modules_this_test_loaded():
    """Collect after every test here, because loading a tool is not free of effects.

    WAVE 25, measured while landing this module. `blender_stub.load_tool` pops the
    module out of `sys.modules` on teardown, but the CLASSES it defined stay reachable
    from any reference the test kept — and `GateFailure.__subclasses__()` sees them.
    `tests/test_gates.py::test_no_new_andon_takes_an_id_another_andon_already_uses`
    reads exactly that registry: with `check_relift` still referenced it measured a
    THIRD shared gate id (`RELIFT`: `ReliftMismatch`, `ReliftWindow`) and went red —
    a defect in THIS module, not in the tree, and one that only appears when the two
    files run in the same process. Dropping the references and collecting makes this
    module's answers its own.
    """
    yield
    _LOADED.clear()
    gc.collect()


def _tool_resolver(name, cname):
    """The runtime class for a name raised in `tools/<name>.py`, or None.

    The tools `import bpy` at module scope, so they resolve through
    `blender_stub.load_tool` rather than through `importlib` — the one difference between
    this caller of the walk and `armature_core`'s. The cache is per-test and is dropped
    by the fixture above.
    """
    mod = _LOADED.get(name, "unloaded")
    if mod == "unloaded":
        try:
            mod = blender_stub.load_tool(name + ".py")
        except Exception:
            mod = None
        _LOADED[name] = mod
    cls = getattr(mod, cname, None) if mod is not None else None
    if cls is None:
        import armature_core.errors as E
        cls = getattr(E, cname, None)
    return cls


_LOADED = {}


def test_every_family_raise_in_the_21_instruments_names_the_clause_that_pulled():
    """The property `armature_core` asserts, now true here too — same walk, same shape."""
    bad = CN.family_raises_without_a_clause(owned_trees(), _tool_resolver, ArmatureError)
    assert bad == [], {
        "raises with no clause a reader can key on": bad,
        "why it matters": "an operator triaging a refused start frame cannot tell the "
                          "licence andon from six other STARTFRAME refusals without "
                          "grepping the prose message",
    }


def test_the_walk_finds_a_clauseless_raise_when_there_is_one(tmp_path):
    """The census's own red proof, both directions and on the RESOLVED class.

    A module raising a real family class with no clause is FOUND; the same module raising a
    look-alike that is not in the family is not — which is the wave-18 rule the walk exists
    to keep.
    """
    src = ("class LocalGate(Exception):\n"
           "    pass\n"
           "def a():\n"
           "    raise DecoyError('x')\n"
           "def b():\n"
           "    raise RealGate('x', {'gate': 'G'})\n"
           "def c():\n"
           "    raise RealGate('x', {'clause': 'named'})\n")
    trees = {"scratch": ast.parse(src)}

    class RealGate(ArmatureError):
        pass

    class DecoyError(Exception):
        pass

    resolve = {"RealGate": RealGate, "DecoyError": DecoyError}.get
    got = CN.family_raises_without_a_clause(trees, lambda _m, c: resolve(c), ArmatureError)
    assert got == [("scratch", 6, "RealGate", "evidence without a clause")], got


#: The clause words this wave gave the 78, module by module — the FIXTURE that names them.
#:
#: A clause is an identity a halt reader keys on, so each word is spelled here as well as in
#: the tool: `test_refusal_clauses.test_every_clause_word_is_named_by_a_fixture_or_listed_
#: with_a_reason` treats a word no test spells as a receipt word nobody would notice
#: changing, and its table of such words may not grow.
WAVE_25_CLAUSE_WORDS = {
    "author_walk": ["gait_too_short_for_a_skin_comparison", "keying_produced_no_action",
                    "subject_is_not_one_mesh_and_one_armature"],
    "check_relift": ["frames_is_not_a_comparable_count", "glb_is_not_a_file",
                     "import_has_no_render_visible_mesh",
                     "pinned_and_fresh_are_the_same_file"],
    "diagnose_bone_heat": ["bands_not_a_usable_band_count",
                           "subject_is_not_one_render_visible_mesh"],
    "lift_solve": ["keying_produced_no_action",
                   "subject_is_not_one_mesh_and_one_armature"],
    "make_binding_sheet": ["no_valid_render_engine", "render_wrote_nothing",
                           "subject_is_not_one_armature",
                           "subject_is_not_one_render_visible_mesh"],
    "make_parts_sheet": ["armature_does_not_name_both_sides",
                         "both_arms_move_across_the_arc",
                         "glb_has_no_render_visible_mesh", "neither_arm_moved",
                         "no_valid_render_engine", "render_wrote_nothing",
                         "subject_is_not_one_armature"],
    "make_rig_sheet": ["reference_import_is_not_one_render_visible_mesh",
                       "subject_is_not_one_armature", "subject_is_not_one_skinned_mesh"],
    "make_skeleton_sheet": ["no_valid_render_engine", "render_wrote_nothing",
                            "subject_is_not_one_render_visible_mesh"],
    "make_test_armature": ["arc_names_parts_the_figure_has_none_of"],
    "preview_walk": ["asset_has_no_evaluated_geometry",
                     "asset_has_no_render_visible_mesh", "preview_is_incomplete"],
    "probe_glb": ["argument_carries_no_value", "argument_is_not_attached_with_equals",
                  "no_out_or_no_glb", "out_given_twice", "unknown_argument"],
    "probe_subject": ["argument_carries_no_value",
                      "argument_is_not_attached_with_equals", "named_glb_is_not_a_file",
                      "no_out_or_no_glb", "nothing_was_measured", "out_given_twice",
                      "unknown_argument"],
    "render_performer": ["coverage_has_no_frames_to_rule_on",
                         "glb_has_no_render_visible_mesh",
                         "motion_record_has_no_frames", "no_motion_source_given",
                         "performance_is_incomplete", "performance_outside_the_frame"],
    "render_start_frame": ["floor_material_reads_an_image",
                           "frame_outside_the_keyed_range",
                           "glb_has_no_render_visible_mesh", "plate_is_not_a_file",
                           "plate_size_does_not_match_the_frame",
                           "shadow_layer_needs_floor_and_plate",
                           "subject_has_no_vertices_at_this_frame"],
    "rig_bake": ["bake_operator_declined", "baked_atlas_is_mostly_empty",
                 "import_is_not_one_render_visible_mesh",
                 "no_image_texture_node_to_bake_into"],
    "rig_character": ["glb_and_out_are_required", "no_vertex_group_for_bone",
                      "reimport_is_not_one_render_visible_mesh",
                      "subject_is_not_one_mesh_object",
                      "unbound_declared_over_weighted_fingerprints", "unknown_argument",
                      "unknown_binding_mode", "unknown_envelope_radii", "unknown_mode"],
    "rig_parts": ["glb_and_out_are_required", "subject_is_not_one_mesh_object",
                  "unknown_argument"],
    "rig_repair": ["repair_removed_too_much", "still_not_manifold_after_repair",
                   "subject_is_not_one_render_visible_mesh"],
    "rig_retopo": ["comparison_is_not_isolated", "no_retopo_route_produced_a_mesh",
                   "panel_subject_is_hidden_from_render", "quadriflow_declined",
                   "subject_is_not_one_render_visible_mesh"],
}


def test_the_licence_andon_on_the_paid_path_names_its_own_clause():
    """The finding's sharpest member, by itself, because it is the one that conditions a
    paid submission: the floor material's image refusal is keyed on a WORD, not on a gate
    id shared with six other STARTFRAME refusals."""
    tree = ast.parse(CN.read_source("render_start_frame"))
    words = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call)):
            continue
        msg = ast.unparse(node.exc.args[0]) if node.exc.args else ""
        if "licence" not in msg and "license" not in msg:
            continue
        for arg in node.exc.args[1:]:
            if isinstance(arg, ast.Dict):
                for k, v in zip(arg.keys, arg.values):
                    if (isinstance(k, ast.Constant) and k.value == "clause"
                            and isinstance(v, ast.Constant)):
                        words.add(v.value)
    assert "floor_material_reads_an_image" in words, sorted(words)


def test_every_clause_word_this_wave_named_is_in_the_module_it_was_named_for():
    """The table above is the fixture; this is the tie to the tree.

    Membership per module, not a total: a word that moves to another module is a different
    refusal under the same name, which is the defect one level up from the one this wave
    fixed.
    """
    sites = CN.clause_literals()
    missing = []
    for module, words in sorted(WAVE_25_CLAUSE_WORDS.items()):
        for word in sorted(set(words)):
            where = sites.get(word, [])
            if not any(w.split(":")[0] == module + ".py" for w in where):
                missing.append((module, word, where))
    assert missing == [], missing


# =======================================================================================
# F-c05e8b32 (ground F-4925f60f, moved) — a render site takes a PRE-RENDER SNAPSHOT
# =======================================================================================
#
# The status clause and the pre-render snapshot are two halves of one premise, and only the
# first half had a census. MEASURED on `580af47` by counting `scene.render.filepath`
# assignments against `render_target_snapshot` / `require_render_target_moved` per owned
# module: preview_glb 2/3/1, preview_walk 1/2/2, render_performer 2/3/3,
# render_start_frame 6/7/7, render_turnaround 2/2/2 — and make_binding_sheet 1/0/0,
# make_parts_sheet 1/0/0, make_skeleton_sheet 1/0/0. The three sheets are where the
# Director approves the skeleton.
#
# `armature_core/blender_scene.py` is in the population and satisfies the property under its
# OWN spelling (`_channel_snapshot` per channel, refusing `stale_channel`), which is why the
# predicate is a set of spellings rather than one name: the property is "this module
# measures the target before the write", not "this module calls that function".

#: The calls that take a pre-render snapshot, by unparsed spelling. Two exist, deliberately:
#: the tool-side twin of `export_target_snapshot` and `blender_scene`'s per-channel one.
SNAPSHOT_CALLS = ("rig_character.render_target_snapshot", "rc.render_target_snapshot",
                  "_channel_snapshot")

#: The refusals that rule on the snapshot, by clause word.
STALE_CLAUSES = ("stale_render_target", "stale_channel")


def _calls_named(tree, names):
    return [n for n in ast.walk(tree)
            if isinstance(n, ast.Call) and ast.unparse(n.func) in names]


def _snapshot_census():
    """`{module: (n_render_sites, n_snapshots, refuses_on_stale)}` over the 15-site
    population `test_instruments_amend_w14` already pins."""
    sites = _operator_call_sites(TOOLS, "bpy.ops.render.render")
    out = {}
    for fn, path in census_sources(TOOLS):
        n_sites = sum(1 for f, _, _ in sites if f == fn)
        if not n_sites:
            continue
        src = open(path, encoding="utf-8").read()
        tree = ast.parse(src)
        n_snap = len(_calls_named(tree, SNAPSHOT_CALLS))
        # "rules on a stale target" is a BEHAVIOUR, not a spelling: a module either calls
        # the home that raises the clause, or (as `blender_scene` does) spells its own.
        stale = (any(w in src for w in STALE_CLAUSES)
                 or "require_render_target_moved" in src)
        out[fn] = (n_sites, n_snap, stale)
    return out


def test_every_render_site_takes_a_pre_render_snapshot():
    """The companion property to `RENDER_SITE_MODULES_TODAY`'s status clause, over the same
    population. Before this wave the three sheets read 1 render site / 0 snapshots each."""
    census = _snapshot_census()
    assert sorted(census) == RENDER_SITE_MODULES_TODAY, sorted(census)
    assert sum(n for n, _, _ in census.values()) == RENDER_SITES_TODAY, census
    short = {fn: row for fn, row in census.items() if row[1] < row[0] or not row[2]}
    assert short == {}, {
        "modules whose render sites are not all preceded by a snapshot, or which never "
        "rule on a stale target": short,
        "why it matters": "the FINISHED clause, `os.path.isfile` and `getsize` are all "
                          "properties a PREVIOUS run's file at the same path satisfies",
    }


@pytest.mark.parametrize("module", ["make_binding_sheet", "make_parts_sheet",
                                    "make_skeleton_sheet"])
def test_the_three_sheets_rule_on_the_snapshot_after_their_own_two_clauses(module):
    """Order, not just presence: the snapshot is taken ABOVE the render and ruled on BELOW
    the FINISHED and size clauses, which is where the one direction they cannot see is."""
    tree = ast.parse(CN.read_source(module))
    shoot = next(n for n in ast.walk(tree)
                 if isinstance(n, ast.FunctionDef) and n.name == "shoot")
    snap = _calls_named(shoot, SNAPSHOT_CALLS)
    moved = _calls_named(shoot, ("rig_character.require_render_target_moved",))
    assign = [n for n in ast.walk(shoot)
              if isinstance(n, ast.Assign) and len(n.targets) == 1
              and ast.unparse(n.targets[0]) == "scene.render.filepath"]
    render = [n for n in ast.walk(shoot)
              if isinstance(n, ast.Call) and ast.unparse(n.func) == "bpy.ops.render.render"]
    assert len(snap) == 1 and len(moved) == 1 and len(assign) == 1 and len(render) == 1
    assert snap[0].lineno < assign[0].lineno < render[0].lineno < moved[0].lineno, (
        module, snap[0].lineno, assign[0].lineno, render[0].lineno, moved[0].lineno)

    size_clause = [n for n in ast.walk(shoot)
                   if isinstance(n, ast.If) and "getsize" in ast.unparse(n.test)]
    assert size_clause and size_clause[0].lineno < moved[0].lineno, module


def test_the_snapshot_census_sees_a_render_site_that_takes_none(tmp_path):
    """Red proof for the walk: a module with a render site and no snapshot is caught."""
    fake = tmp_path / "make_decoy_sheet.py"
    fake.write_text("import bpy\n"
                    "def shoot(scene, path):\n"
                    "    scene.render.filepath = path\n"
                    "    r = bpy.ops.render.render(write_still=True)\n"
                    "    return r\n", encoding="utf-8")
    tree = ast.parse(fake.read_text(encoding="utf-8"))
    assert _calls_named(tree, SNAPSHOT_CALLS) == []
    assert len([n for n in ast.walk(tree) if isinstance(n, ast.Call)
                and ast.unparse(n.func) == "bpy.ops.render.render"]) == 1


# =======================================================================================
# F-8c2ad415 — an empty motion record is REFUSED, and Gate COVERAGE cannot pass on zero
# =======================================================================================


def _render_performer():
    return blender_stub.load_tool("render_performer.py")


def test_gate_coverage_refuses_a_plan_with_no_frames(tmp_path):
    """MEASURED on `580af47`: `gate_coverage([], plate)` RETURNED
    `{'min_fraction': 0.01, 'worst': {'frame': None, 'frac': 1.0},
      'verdict': 'min 1.0000 at frame None over 0 frames'}` — the gate's strongest verdict
    over zero frames, from the gate whose stated job is that the performer is in every
    frame. `worst` is seeded 1.0 and updated only inside the loop, so `1.0 < 0.01` is False.
    """
    from PIL import Image
    plate = tmp_path / "empty.png"
    Image.new("RGB", (16, 16), (30, 30, 30)).save(plate)

    RP = _render_performer()
    with pytest.raises(RP.RenderGate) as exc:
        RP.gate_coverage([], str(plate))
    assert exc.value.evidence["clause"] == "coverage_has_no_frames_to_rule_on"
    assert exc.value.evidence["n_frames"] == 0


def test_the_empty_record_is_refused_above_the_index_and_above_the_first_write():
    """Both orderings, from the tree: the refusal is above `clouds[-1]` (which is where the
    `IndexError` was) and above `os.makedirs` (so a truncated record leaves nothing).

    MEASURED end to end on `580af47` through `blender_stub.exit_code_of_main_block`: the
    `IndexError` printed `RENDER_PERFORMER_HALT {"outcome": "FAILED — an unhandled error",
    "gate": null, "error": "IndexError", "message": "list index out of range",
    "evidence": null}` at exit 1 — a crash where the halt contract's own three-outcome rule
    wants a deliberate refusal at exit 2.
    """
    tree = ast.parse(CN.read_source("render_performer"))
    main = next(n for n in tree.body
                if isinstance(n, ast.FunctionDef) and n.name == "main")
    refusal = [n for n in ast.walk(main) if isinstance(n, ast.Raise)
               and "motion_record_has_no_frames" in ast.unparse(n)]
    index = [n for n in ast.walk(main)
             if isinstance(n, ast.Subscript) and ast.unparse(n) == "clouds[-1]"]
    makedirs = [n for n in ast.walk(main)
                if isinstance(n, ast.Call) and ast.unparse(n.func) == "os.makedirs"]
    assert len(refusal) == 1 and index and makedirs
    assert refusal[0].lineno < index[0].lineno, (refusal[0].lineno, index[0].lineno)
    assert refusal[0].lineno < min(m.lineno for m in makedirs)


def test_the_vacuity_clause_does_not_depend_on_the_ordering_fix():
    """The two halves are independent statements, which is the whole point: a gate whose
    andon is load-bearing only in another statement's presence is the direction CLAUDE.md
    rules against. `gate_coverage`'s clause is inside `gate_coverage`."""
    tree = ast.parse(CN.read_source("render_performer"))
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "gate_coverage")
    assert any("coverage_has_no_frames_to_rule_on" in ast.unparse(n)
               for n in ast.walk(fn) if isinstance(n, ast.Raise))


# =======================================================================================
# F-19d4e0f7 — the THIRD Blender operator's status set, captured and ruled on
# =======================================================================================
#
# MEASURED on `580af47` with `test_instruments_amend_w14._operator_call_sites`, the ONE home
# for this walk: `bpy.ops.export_scene.gltf` 9 sites / 8 modules / 0 uncaptured (pinned),
# `bpy.ops.render.render` 15 sites / 9 modules / 0 uncaptured (pinned), and
# `bpy.ops.import_scene.gltf` 16 sites / 13 modules / **16 uncaptured**. Fifteen of the
# sixteen were in this domain; the sixteenth is inside `armature_core.blender_scene.
# import_glb` and is core-solvers' file — a RECORDED EXCEPTION here, posted to the wave-25
# inbox rather than reached across a domain boundary.
#
# The operator CALL stays at each site and the RESULT is handed to one clause, the shape
# `gate_glb_written(path, result=..., before=...)` already uses for the export half. The
# first attempt performed the import inside `rig_character` instead; `bpy` is a
# module-global in each tool, so that made every caller import against
# `rig_character.bpy` rather than its own, and four fixtures in `test_make_rig_sheet`
# and `test_retopo_and_bake` that monkeypatch their own module went red. Under real
# Blender the two are the same object; the fixtures were right and the shape was wrong.
#
# `tests/blender_stub._FakeOps.gltf` returned `None` where every real
# `bpy.ops.import_scene.gltf` returns a status set, so it modelled a Blender that
# answers nothing. Nothing read the return, so nothing noticed. It returns
# `{'FINISHED'}` now, and `FakeBpy.gltf_status` makes the declining direction testable.

#: The one site under `tools/**` this domain cannot reach, with the reason. Named rather
#: than counted, so that closing it deletes the row instead of moving a number.
IMPORT_SITE_NOT_OURS = {
    "armature_core/blender_scene.py":
        "inside `import_glb`; `armature_core` is core-solvers' tree (wave-25 seam)",
}


def test_every_glb_import_site_in_this_domain_captures_the_operator_status_set():
    """The third operator joins the census its two siblings were already held to."""
    sites = _operator_call_sites(TOOLS, "bpy.ops.import_scene.gltf")
    assert len(sites) == 16, sites
    uncaptured = sorted({fn for fn, _, cap in sites if not cap})
    assert uncaptured == sorted(IMPORT_SITE_NOT_OURS), {
        "uncaptured import sites": uncaptured,
        "recorded as not this domain's": IMPORT_SITE_NOT_OURS,
    }


def test_the_import_status_clause_has_exactly_one_home_in_this_domain():
    """One implementation of the CLAUSE, fourteen callers — the idiom
    `gate_glb_written(path, result=..., before=...)` already uses for the export half.

    The operator CALL stays at the call site on purpose, and the reason is measured
    rather than stylistic: `bpy` is a module-global in each tool, so performing the
    import inside `rig_character` would make every caller import against
    `rig_character.bpy` instead of its own. Under real Blender that is the same object;
    under `tests/blender_stub` it is not, and four fixtures that monkeypatch their own
    `bpy` went red on exactly that difference before the shape was corrected.
    """
    tree = ast.parse(CN.read_source("rig_character"))
    home = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
            and n.name == "require_import_status"]
    assert len(home) == 1
    inside = [n for n in ast.walk(home[0]) if isinstance(n, ast.Call)
              and ast.unparse(n.func) == "bpy.ops.import_scene.gltf"]
    assert inside == [], "the operator call belongs at the call site, not here"

    callers = {}
    for name in OWNED:
        src = CN.read_source(name)
        n = len([c for c in ast.walk(ast.parse(src)) if isinstance(c, ast.Call)
                 and ast.unparse(c.func).endswith("require_import_status")])
        if n:
            callers[name] = n
    # FOURTEEN of the fifteen captured sites hand their status to the home; the
    # fifteenth is `probe_glb`, whose outcome for a declined import is a MEASUREMENT
    # rather than a halt (below).
    assert sum(callers.values()) == 14, callers
    assert len(callers) == 11, callers
    assert "probe_glb" not in callers


def test_require_import_status_raises_on_a_declined_import(tmp_path):
    """The andon, driven: a CANCELLED status raises the caller's own class with the
    `operator_status` clause and the operand, rather than letting the previous import's
    objects satisfy every clause below it."""
    rc = blender_stub.load_tool("rig_character.py")
    with pytest.raises(rc.GateSubject) as exc:
        rc.require_import_status({"CANCELLED"}, str(tmp_path / "hero.glb"),
                                 rc.GateSubject, {"who": "a test"})
    ev = exc.value.evidence
    assert ev["clause"] == "operator_status"
    assert ev["operator"] == "bpy.ops.import_scene.gltf"
    assert ev["status"] == ["CANCELLED"]
    assert ev["who"] == "a test"


def test_require_import_status_returns_the_status_on_a_finished_import(tmp_path):
    """The other direction, so the clause is not vacuously green. An UNREADABLE
    return normalises to `[]`, which FAILS the clause rather than passing it."""
    rc = blender_stub.load_tool("rig_character.py")
    assert rc.require_import_status({"FINISHED"}, str(tmp_path / "hero.glb"),
                                    rc.GateSubject) == ["FINISHED"]
    with pytest.raises(rc.GateSubject) as exc:
        rc.require_import_status(None, str(tmp_path / "hero.glb"), rc.GateSubject)
    assert exc.value.evidence["clause"] == "operator_status"
    assert exc.value.evidence["status"] == []


def test_the_probe_records_the_import_status_instead_of_refusing_on_it():
    """`probe_glb` is the one member where a refusal is the WRONG shape: a file that will
    not open is this tool's measurement, not its halt. The status is still CAPTURED — the
    census's property — and a non-FINISHED import fails clause A."""
    tree = ast.parse(CN.read_source("probe_glb"))
    src = CN.read_source("probe_glb")
    assert "rec[\"import_status\"]" in src
    assert "\"FINISHED\" in rec[\"import_status\"]" in src
    sites = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and ast.unparse(n.func) == "bpy.ops.import_scene.gltf"]
    assert len(sites) == 1


# =======================================================================================
# F-6e1a9d54 — every instrument declares a NAMED compensator with an owner
# =======================================================================================
#
# MEASURED on `580af47` by grepping the 21 owned modules: SEVEN declared a named
# compensator with an owner (render_turnaround, preview_glb, render_start_frame,
# render_performer, author_walk, lift_solve, check_relift) and FOURTEEN declared none — and
# the fourteen included six of the eight GLB exporters in the tree. CLAUDE.md's workflow
# standard 3 (NAMED_COMPENSATORS — Sagas, Garcia-Molina & Salem, SIGMOD 1987) takes NO skip.
#
# The exposure is not hypothetical ordering: `_census_nodes.refusal_and_write_lines`, run
# over the 21, finds 15 modules with at least one refusal BELOW the first write, so a halt
# after the first write is the ordinary case.

COMPENSATOR_HEADING = "Compensator (NAMED_COMPENSATORS)"
COMPENSATOR_OWNER = "owner: the executor session"


def _module_docstring(name):
    """The module docstring with whitespace collapsed.

    Collapsed because these paragraphs are hard-wrapped at 88 columns and the owner phrase
    lands across a line break in five of the twenty-one -- a census that keyed on the raw
    text would report a module whose only defect is where its line ends.
    """
    tree = ast.parse(CN.read_source(name))
    return " ".join((ast.get_docstring(tree) or "").split())


def test_every_instrument_declares_a_named_compensator_with_an_owner():
    """Heading AND owner. A heading with no owner is a paragraph, not a compensator."""
    missing = {}
    for name in OWNED:
        doc = _module_docstring(name)
        if COMPENSATOR_HEADING not in doc:
            missing[name] = "no heading"
        elif COMPENSATOR_OWNER not in doc:
            missing[name] = "heading, no owner"
    assert missing == {}, missing


def test_the_compensator_census_refuses_a_heading_with_no_owner():
    """Red proof: the check is not satisfied by the heading alone."""
    doc = ("Something.\n\n" + COMPENSATOR_HEADING + "\n\n"
           "Compensator: delete the output directory.\n")
    assert COMPENSATOR_HEADING in doc and COMPENSATOR_OWNER not in doc


def test_a_halt_after_the_first_write_is_the_ordinary_case_in_this_domain():
    """The measurement the fourteen entries cite, re-derived rather than quoted."""
    below = []
    for name in OWNED:
        refusals, writes = CN.refusal_and_write_lines(CN.read_source(name))
        if not writes:
            continue
        first = min(writes)
        if any(line > first for line in refusals):
            below.append(name)
    assert len(below) == 15, below


def test_the_two_hand_rolled_name_flags_are_bounded_like_preview_glbs():
    """The condition the two exporters' compensator statements rest on.

    `rig_character` and `rig_parts` paste `--name` into the exported GLB's filename and
    parse their arguments by hand, so `_census_nodes.pasted_name_flags()` — which derives
    its population from argparse `add_argument` calls — cannot see either. MEASURED on this
    branch: that census returns the same 12 members before and after this fix, which is the
    census gap (posted to the wave-25 inbox for the tests domain), not a reason to leave the
    flag open. `single_path_segment` is adopted by import from wave 22's ONE home.
    """
    assert len(CN.pasted_name_flags()) == 12
    for name in ("rig_character", "rig_parts"):
        tree = ast.parse(CN.read_source(name))
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and ast.unparse(n.func) == "parts.single_path_segment"
                 and "--name" in ast.unparse(n)]
        assert len(calls) == 1, name


@pytest.mark.parametrize("name", ["rig_character", "rig_parts"])
def test_a_name_that_escapes_the_output_directory_is_refused(name):
    """Driven, not asserted from the tree: `--name=../escaped` refuses by NAME."""
    mod = blender_stub.load_tool(name + ".py")
    argv = ["blender", "-b", "-P", name + ".py", "--",
            "--glb=in.glb", "--out=out", "--name=../escaped"]
    old = sys.argv
    try:
        sys.argv = argv
        with pytest.raises(ArmatureError) as exc:
            mod.parse_args()
    finally:
        sys.argv = old
    assert exc.value.evidence["clause"] == "output_name_is_not_a_name"
    assert exc.value.evidence["flag"] == "--name"


# =======================================================================================
# F-f204a6d1 — the success sentinel's payload is JSON, and it says what the run measured
# =======================================================================================
#
# MEASURED on `580af47` by an AST walk over the 21 owned tools for `print` calls whose first
# argument mentions `_OK`: 22 such lines in 20 modules built their payload with
# `json.dumps`, and exactly one did not — `make_skeleton_sheet`'s, whose payload was a bare
# Windows path. So a wrapper reading BOTH lines of the halt contract needed two parsers: the
# HALT line is strict JSON everywhere (wave 22 added `allow_nan=False`).
#
# The token was also earned by reaching the end of `main` rather than by a measurable effect
# — the wave-12 rule, and the shape F-7e7703cb already closed for `diagnose_bone_heat`:
# `gate_snap` and the whole joint-snap table are computed twenty lines above and none of it
# reached the line, so a run in which every joint snapped and a run assembled from a
# degenerate table read identically.
#
# The wider tree is NOT this domain's: the same walk over all of `tools/*.py` finds 13 more
# `_OK` lines whose payload is not `json.dumps` (build_assembly_payload, build_cascade_
# payload, build_lora_arm_payload, build_r2v_payload, composite_reference,
# extract_clip_frames, make_cast_sheet, make_e13_sheet, make_hole_survey,
# make_shotset_sheet, measure_cascade_clip, rig_sheet_compose, sheet_compose). Counted and
# posted; not fixed here.


def _ok_prints(name):
    """`[(lineno, unparsed call)]` for every `print` mentioning `<PREFIX>_OK`."""
    out = []
    for node in ast.walk(ast.parse(CN.read_source(name))):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "print" and node.args):
            continue
        text = ast.unparse(node)
        if any(isinstance(n, ast.Constant) and isinstance(n.value, str)
               and "_OK" in n.value for n in ast.walk(node.args[0])):
            out.append((node.lineno, text))
    return out


def test_every_success_sentinel_in_this_domain_carries_a_json_object():
    """One convention across the 21, so one parser reads both halves of the contract."""
    offenders = []
    for name in OWNED:
        for lineno, text in _ok_prints(name):
            if "json.dumps" not in text:
                offenders.append((name, lineno))
    assert offenders == [], offenders


def test_the_skeleton_sheets_sentinel_reports_what_the_run_measured():
    """The token is earned by an EFFECT: the gate's own counts and the panel count reach
    the line, so a degenerate run and a clean one no longer read identically."""
    calls = _ok_prints("make_skeleton_sheet")
    assert len(calls) == 1, calls
    text = calls[0][1]
    # `ast.unparse` normalises string quoting to single quotes; the keys are compared in
    # that spelling rather than in the source's.
    for key in ("'tool'", "'json'", "'gate_SKELETON_SHEET'", "'n_inset_joints'",
                "'n_snap_sites'", "'panels'", "'side'"):
        assert key in text, (key, text)
    assert "gate_snap" in text and "spec['rows']" in text


def test_the_payload_of_the_rewritten_sentinel_is_a_dict_literal():
    """Shape, from the tree: `json.dumps` of a DICT, not of whatever `main` had to hand."""
    tree = ast.parse(CN.read_source("make_skeleton_sheet"))
    dumps = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and ast.unparse(n.func) == "json.dumps"
             and isinstance(n.args[0], ast.Dict)]
    keys = [sorted(k.value for k in d.args[0].keys if isinstance(k, ast.Constant))
            for d in dumps]
    assert ["gate_SKELETON_SHEET", "json", "n_inset_joints", "n_snap_sites", "panels",
            "side", "tool"] in keys, keys


#: The `_OK` lines OUTSIDE this domain whose payload is not `json.dumps`, measured
#: 2026-09-05. Posted, not fixed: eleven are instruments-measure's or builders'.
OK_LINES_NOT_JSON_ELSEWHERE = [
    "build_assembly_payload.py", "build_cascade_payload.py", "build_lora_arm_payload.py",
    "build_r2v_payload.py", "composite_reference.py", "extract_clip_frames.py",
    "make_cast_sheet.py", "make_e13_sheet.py", "make_hole_survey.py",
    "make_shotset_sheet.py", "measure_cascade_clip.py", "rig_sheet_compose.py",
    "sheet_compose.py",
]


def test_the_rest_of_the_tree_is_counted_rather_than_absorbed():
    """A number in a report is a claim; this is the claim, derived. The table may not grow
    without a reader deciding it should."""
    got = []
    for fn, path in census_sources(TOOLS, recursive=False):
        stem = fn[:-3]
        if stem in OWNED:
            continue
        for _lineno, text in _ok_prints(stem):
            if "json.dumps" not in text:
                got.append(fn)
    assert sorted(set(got)) == OK_LINES_NOT_JSON_ELSEWHERE, sorted(set(got))


# =======================================================================================
# F-a4f7b3c9 — `--bands` refuses on the FLAG, never as `silhouette_is_not_a_standing_figure`
# =======================================================================================
#
# MEASURED on `580af47` on the repo venv: `landmarks.band_profile(v, n_bands=0)` and
# `n_bands=-5` each RETURN with zero bands and no refusal of any kind, and
# `landmarks.derive` then raises `LandmarkError` under the clause
# `silhouette_is_not_a_standing_figure` — a clause about the ASSET, on a run whose only
# defect is the flag. This tool's whole purpose is investigating why a mesh binds badly, so
# a message blaming the silhouette is the message the operator is primed to believe.


def _dbh():
    return blender_stub.load_tool("diagnose_bone_heat.py")


class _Args:
    def __init__(self, bands):
        self.bands = bands


@pytest.mark.parametrize("bands", [0, -5, 1, 2, 11])
def test_a_band_count_that_cannot_resolve_a_figure_refuses_on_the_flag(bands):
    D = _dbh()
    with pytest.raises(D.BandCountError) as exc:
        D.require_band_count(_Args(bands))
    ev = exc.value.evidence
    assert ev["clause"] == "bands_not_a_usable_band_count"
    assert ev["flag"] == "--bands"
    assert ev["bands"] == bands
    assert "silhouette" not in ev["clause"]


@pytest.mark.parametrize("bands", [12, 33, 200])
def test_a_usable_band_count_passes(bands):
    """The other direction: a check that cannot pass is not a check."""
    D = _dbh()
    assert D.require_band_count(_Args(bands)).bands == bands


def test_the_floor_is_derived_from_the_derivation_it_protects():
    """`4 * MIN_RUN_BANDS`, spelled as the expression: `landmarks._region_runs` needs four
    cluster-count runs (legs, legs+arms, trunk+arms, trunk) each surviving the
    `>= MIN_RUN_BANDS` filter, and `_median3` holds its edges and preserves length. A
    global constant must not govern a local feature; this one is the feature's own."""
    from armature_core import landmarks
    D = _dbh()
    assert D.MIN_BANDS == 4 * landmarks.MIN_RUN_BANDS
    src = CN.read_source("diagnose_bone_heat")
    assert "MIN_BANDS = 4 * landmarks.MIN_RUN_BANDS" in src


def test_the_clause_fires_above_the_first_write():
    """Placement, from the tree — the `require_subject_args` shape carried: FIRST, above
    `load` and above `os.makedirs`, so a refusal leaves nothing behind."""
    tree = ast.parse(CN.read_source("diagnose_bone_heat"))
    main = next(n for n in tree.body
                if isinstance(n, ast.FunctionDef) and n.name == "main")
    guard = [n for n in ast.walk(main) if isinstance(n, ast.Call)
             and ast.unparse(n.func) == "require_band_count"]
    writes = [n for n in ast.walk(main) if isinstance(n, ast.Call)
              and ast.unparse(n.func) in ("os.makedirs", "load")]
    assert len(guard) == 1 and writes
    assert guard[0].lineno < min(w.lineno for w in writes)


def test_the_unbounded_flag_still_reaches_the_silhouette_clause_without_the_guard():
    """The finding's operand, held: `landmarks.band_profile` still RETURNS on a band count
    of zero (that half is `armature_core`'s and is posted to the inbox), which is exactly
    why the refusal has to be at the flag."""
    import numpy as np
    from armature_core import landmarks
    verts = np.random.default_rng(0).normal(size=(400, 3))
    bands, _extent = landmarks.band_profile(verts, n_bands=0)
    assert bands == []


def test_the_success_sentinel_of_this_tool_still_says_what_it_measured():
    """`diagnose_bone_heat`'s own `_OK` line was fixed by F-7e7703cb and is the shape
    `make_skeleton_sheet`'s now carries; asserted so the pair cannot drift apart."""
    calls = _ok_prints("diagnose_bone_heat")
    assert len(calls) == 1 and "json.dumps" in calls[0][1]


def test_the_halt_line_of_a_band_refusal_is_strict_json():
    """The halt line a triage actually reads, driven through the module's own handler."""
    D = _dbh()
    try:
        D.require_band_count(_Args(0))
    except D.BandCountError as exc:
        record = {"tool": "diagnose_bone_heat", "outcome": "REFUSED", "gate": None,
                  "error": type(exc).__name__, "message": str(exc),
                  "evidence": exc.evidence}
    payload = json.dumps(record, default=str, allow_nan=False)
    back = json.loads(payload)
    assert back["evidence"]["clause"] == "bands_not_a_usable_band_count"
    assert back["evidence"]["minimum"] == D.MIN_BANDS
