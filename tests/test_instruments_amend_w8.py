"""Wave 8, instruments: the ONE halt contract every Blender-side tool answers to.

`tests/test_instrument_exits.py` (wave 6) asserts only `code not in (0, None)`. That
accepts a tool that returns 1 where the contract says 2, and it says nothing at all about
what the tool PRINTS — so a halt could name no gate, carry no evidence, and read to a
later session exactly like a crash. Three wave-7 findings are that gap:

* **F-7e64c103** — `preview_glb.py` had a bare module-level `main()`: no guard, no
  handler, no sentinel. `blender -b -P` exits **0** when the script's exception
  propagates, so every failure of that tool returned success. It was exempted from the
  wave-6 census by name, on a premise (`a library of preview helpers ... not invoked as a
  script`) that its own docstring line 3 contradicts.
* **F-1aee25e2** — `preview_walk.py`'s handler called `sys.exit(1)` unconditionally and
  printed neither `gate` nor `evidence`, in the one tool whose whole purpose is to be
  looked at before a credit is spent.
* **F-c3f86abc** — `rig_character.py`'s halt record hard-coded
  `"outcome": "HALTED — a gate fired"` with no branch, so a crash in the rigging code
  wrote a record asserting an andon fired.

THE CONTRACT, decided this wave and pinned here so the whole family answers to one shape:

    exit 2   the tool refused deliberately — `isinstance(exc, (GateFailure, ArmatureError))`
    exit 1   anything else: a crash

    stdout   exactly one line `<STEM>_HALT <json object>` where `<STEM>` is the module's
             basename upper-cased, carrying

                 tool      the module basename
                 outcome   HALTED — a gate fired          (a typed GateFailure)
                           REFUSED — the tool declined to proceed   (a bare ArmatureError)
                           FAILED — an unhandled error     (anything else)
                 gate      the andon id, or null
                 error     the exception class name
                 message   str(exc)
                 evidence  the gate's evidence dict, or null

The three outcomes are three states, not two: a bad `--mode=` value is a deliberate
refusal AND not a gate, and writing it either as "a gate fired" or as "an unhandled
error" is a false record. The five tools that also write `halt.json` (`rig_bake`,
`rig_character`, `rig_parts`, `rig_repair`, `rig_retopo`) carry the same fields there.

The population is DERIVED by walking `tools/` for `import bpy` (wave 8's census rule), and
the derivation takes the directory as an argument precisely so the red direction below can
point it at a tree that contains a defective member.
"""

import ast
import json
import os

import pytest

from blender_stub import (TOOLS, blender_tools, blender_tools_in,
                          exit_code_of_main_block, main_block)
# ONE definition of "this member cannot yet be held to the sentinel half of the contract",
# imported rather than restated (F-e63ce880's rule applied to a category as well as a walk).
from test_instrument_exits import halt_contract_pending

HALTED = "HALTED — a gate fired"
REFUSED = "REFUSED — the tool declined to proceed"
FAILED = "FAILED — an unhandled error"

#: The exact key set the sentinel carries. Asserted as a set so a tool cannot answer the
#: contract by printing a superset that a reader has to guess at.
SENTINEL_KEYS = {"tool", "outcome", "gate", "error", "message", "evidence"}


# WAVE 12, F-6b3040d1 + F-e63ce880. `blender_tools_in` used to be defined HERE — a third
# copy of the Blender-tool derivation, and the copy that kept the token-keyed predicate
# (`ast.Import` naming `bpy`), so this file and `blender_stub` could disagree about the
# population while `test_the_population_is_the_size_and_the_membership_it_was_measured_to_be`
# asserted they agreed. It is now imported from `blender_stub`, which keys on the BEHAVIOUR
# "runs under Blender" — a lazy import inside a function, a documented `blender -b -P`
# invocation, or the `armature_core.blender_scene` backend — and still takes a directory, so
# `test_the_derivation_catches_a_tool_that_does_not_answer` can point it at a scratch tree.


#: Measured 2026-09-04 by the walk above over `tools/`. Written out so a new Blender tool
#: fails this file loudly rather than joining a census nobody re-read.
#: WAVE 12 (F-6b3040d1): `stage_render.py` JOINED when the derivation stopped keying on the
#: token. It is not new code; it was invisible to every exit census in the suite.
POPULATION = [
    "author_walk.py", "check_relift.py", "diagnose_bone_heat.py", "lift_solve.py",
    "make_binding_sheet.py", "make_parts_sheet.py", "make_rig_sheet.py",
    "make_skeleton_sheet.py", "make_test_armature.py", "preview_glb.py",
    "preview_walk.py", "probe_glb.py", "probe_subject.py", "render_performer.py",
    "render_start_frame.py", "render_turnaround.py", "rig_bake.py", "rig_character.py",
    "rig_parts.py", "rig_repair.py", "rig_retopo.py", "stage_render.py",
]


def test_the_population_is_the_size_and_the_membership_it_was_measured_to_be():
    """SIZE and MEMBERSHIP, then the property — a census that quietly stopped
    enumerating would report green over everything it no longer reaches."""
    derived = blender_tools_in(TOOLS)
    assert len(derived) == 22, derived
    assert sorted(derived) == sorted(POPULATION), (
        sorted(set(derived) ^ set(POPULATION)))
    assert sorted(derived) == sorted(blender_tools()), "blender_stub disagrees with the walk"


def test_every_tool_in_the_population_has_a_main_guard():
    """There is no exemption. `preview_glb.py` was exempted by name for having no
    `__main__` block; it had none because it called `main()` unconditionally instead."""
    missing = [fn for fn in blender_tools_in(TOOLS) if main_block(fn) is None]
    assert missing == [], (
        f"{missing}: a Blender-side tool with no `__main__` handler. `blender -b -P` exits "
        f"0 when the script's exception propagates, so every failure returns success.")


def test_no_tool_calls_main_at_module_scope():
    """The other half of the same defect: a guard is not enough if `main()` is ALSO
    called bare, and a bare call is what made `preview_glb` unreachable to the census."""
    offenders = []
    for fn in blender_tools_in(TOOLS):
        with open(os.path.join(TOOLS, fn), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        for node in tree.body:
            if (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Name)
                    and node.value.func.id == "main"):
                offenders.append((fn, node.lineno))
    assert offenders == [], offenders


def _halt(filename, raiser, tmp_path, capsys):
    """Run the tool's handler with `main` replaced, and read back (code, sentinel)."""
    code, escaped = exit_code_of_main_block(
        filename, raiser=raiser,
        argv=["blender", "-b", "-P", filename, "--", "--glb=nope.glb",
              "--out=" + str(tmp_path / "out")])
    out = capsys.readouterr().out
    stem = filename[:-3].upper()
    lines = [ln for ln in out.splitlines() if ln.startswith(stem + "_HALT ")]
    return code, escaped, lines


def _assert_sentinel(filename, lines, *, outcome, gate, error, evidence):
    """The shape assertion, factored out so the red direction below can feed it a
    defective handler's output and watch it refuse."""
    if len(lines) != 1:
        raise AssertionError(
            f"{filename}: expected exactly one `{filename[:-3].upper()}_HALT ` line, got "
            f"{len(lines)}: {lines}")
    payload = json.loads(lines[0].split(" ", 1)[1])
    if set(payload) != SENTINEL_KEYS:
        raise AssertionError(f"{filename}: sentinel keys {sorted(payload)}")
    if payload["tool"] != filename[:-3]:
        raise AssertionError(f"{filename}: tool {payload['tool']!r}")
    if payload["outcome"] != outcome:
        raise AssertionError(f"{filename}: outcome {payload['outcome']!r}, want {outcome!r}")
    if payload["gate"] != gate:
        raise AssertionError(f"{filename}: gate {payload['gate']!r}, want {gate!r}")
    if payload["error"] != error:
        raise AssertionError(f"{filename}: error {payload['error']!r}, want {error!r}")
    if payload["evidence"] != evidence:
        raise AssertionError(f"{filename}: evidence {payload['evidence']!r}")
    return payload


@pytest.mark.parametrize("filename", POPULATION)
def test_a_typed_gate_exits_two_and_names_itself(filename, tmp_path, capsys):
    from armature_core.errors import GateFailure

    class _Gate(GateFailure):
        gate = "PROBE"

    pending = halt_contract_pending(filename)
    if pending:
        pytest.skip(pending)
    def raiser():
        raise _Gate("a gate fired", {"measured": 1})

    code, escaped, lines = _halt(filename, raiser, tmp_path, capsys)
    assert escaped is None, f"{filename}: {escaped!r} escaped the handler; blender exits 0"
    assert code == 2, f"{filename}: exit {code!r}; a fired andon is 2"
    _assert_sentinel(filename, lines, outcome=HALTED, gate="PROBE", error="_Gate",
                     evidence={"measured": 1})


@pytest.mark.parametrize("filename", POPULATION)
def test_a_bare_refusal_exits_two_and_names_no_gate(filename, tmp_path, capsys):
    """An `ArmatureError` that is not a `GateFailure` is a deliberate refusal with no
    andon behind it — a bad `--mode=` value, a usage error. It is not a crash (exit 2),
    and it is not a gate (`gate` is null, and the outcome does not say one fired)."""
    from armature_core.errors import ArmatureError

    pending = halt_contract_pending(filename)
    if pending:
        pytest.skip(pending)
    def raiser():
        raise ArmatureError("unknown --mode='wobble'; known: skeleton, full")

    code, escaped, lines = _halt(filename, raiser, tmp_path, capsys)
    assert escaped is None, f"{filename}: {escaped!r} escaped the handler"
    assert code == 2, f"{filename}: exit {code!r}; a deliberate refusal is 2"
    _assert_sentinel(filename, lines, outcome=REFUSED, gate=None, error="ArmatureError",
                     evidence=None)


@pytest.mark.parametrize("filename", POPULATION)
def test_a_crash_exits_one_and_is_not_recorded_as_a_gate(filename, tmp_path, capsys):
    """F-c3f86abc's direction: the two records must DIFFER. A `ValueError` may not
    produce an outcome containing 'a gate fired'."""
    pending = halt_contract_pending(filename)
    if pending:
        pytest.skip(pending)
    def raiser():
        raise ValueError("a bug, not a gate")

    code, escaped, lines = _halt(filename, raiser, tmp_path, capsys)
    assert escaped is None, f"{filename}: {escaped!r} escaped the handler"
    assert code == 1, f"{filename}: exit {code!r}; a crash is 1"
    payload = _assert_sentinel(filename, lines, outcome=FAILED, gate=None,
                               error="ValueError", evidence=None)
    assert "gate fired" not in payload["outcome"]


#: The five tools that ALSO leave `halt.json` on disk, with an argv their own `parse_args`
#: accepts — the handler re-parses it to find out where to write. Derived below and pinned
#: against the derivation, so a sixth halt-file writer cannot join unnoticed.
HALT_FILE_ARGV = {
    "rig_bake.py": ["--retopo=nope.glb", "--source=nope.glb", "--max-deviation=0.1"],
    "rig_character.py": ["--glb=nope.glb"],
    "rig_parts.py": ["--glb=nope.glb"],
    "rig_repair.py": ["--glb=nope.glb"],
    "rig_retopo.py": ["--glb=nope.glb"],
}


def test_the_halt_file_writers_are_the_five_they_were_measured_to_be():
    """Derived from the tree: a tool whose `__main__` block writes `halt.json`."""
    derived = sorted(fn for fn in blender_tools_in(TOOLS)
                     if '"halt.json"' in open(os.path.join(TOOLS, fn),
                                              encoding="utf-8").read())
    assert derived == sorted(HALT_FILE_ARGV), derived


@pytest.mark.parametrize("filename", sorted(HALT_FILE_ARGV))
def test_the_halt_file_says_which_of_the_three_happened(filename, tmp_path, capsys):
    """The five tools that also leave a record on disk write the SAME outcome vocabulary.

    `rig_character._write_halt` hard-coded 'HALTED — a gate fired' for every exception it
    was handed; a crash in the rigging code wrote a record asserting an andon fired, next
    to a note explaining that gates after the one that fired are NOT YET RUN."""
    from armature_core.errors import ArmatureError, GateFailure

    class _Gate(GateFailure):
        gate = "PROBE"

    seen = {}
    for label, exc in (("gate", _Gate("a gate fired", {"measured": 1})),
                       ("refusal", ArmatureError("unknown --mode='wobble'")),
                       ("crash", ValueError("a bug, not a gate"))):
        out = tmp_path / label
        code, escaped = exit_code_of_main_block(
            filename, raiser=(lambda e=exc: (_ for _ in ()).throw(e)),
            argv=(["blender", "-b", "-P", filename, "--", "--out=" + str(out)]
                  + HALT_FILE_ARGV[filename]))
        capsys.readouterr()
        assert escaped is None, (filename, label, escaped)
        with open(out / "halt.json", encoding="utf-8") as fh:
            seen[label] = json.load(fh)

    assert seen["gate"]["outcome"] == HALTED, seen["gate"]
    assert seen["gate"]["gate"] == "PROBE", seen["gate"]
    assert seen["refusal"]["outcome"] == REFUSED, seen["refusal"]
    assert seen["crash"]["outcome"] == FAILED, seen["crash"]
    assert "gate fired" not in seen["crash"]["outcome"]
    assert seen["crash"]["gate"] is None, seen["crash"]


def test_the_derivation_catches_a_tool_that_does_not_answer(tmp_path):
    """The RED direction for the population walk: a census that cannot fail is not a
    census. A tree carrying a tool with a bare `main()` and no guard must be enumerated
    by the derivation and must fail the property."""
    (tmp_path / "sneaky_tool.py").write_text(
        "import bpy\n\n\ndef main():\n    return 0\n\n\nmain()\n", encoding="utf-8")
    (tmp_path / "not_a_blender_tool.py").write_text("import os\n", encoding="utf-8")

    derived = blender_tools_in(str(tmp_path))
    assert derived == ["sneaky_tool.py"], derived

    tree = ast.parse((tmp_path / "sneaky_tool.py").read_text(encoding="utf-8"))
    guards = [n for n in tree.body
              if isinstance(n, ast.If) and isinstance(n.test, ast.Compare)
              and isinstance(n.test.left, ast.Name) and n.test.left.id == "__name__"]
    bare = [n.lineno for n in tree.body
            if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
            and isinstance(n.value.func, ast.Name) and n.value.func.id == "main"]
    assert guards == [] and bare == [8], (guards, bare)


def test_the_shape_assertion_refuses_a_defective_handlers_output():
    """The RED direction for the property: the exact line `preview_walk` used to print —
    no gate, no evidence, no outcome — must not pass."""
    old = ('PREVIEW_WALK_HALT {"error": "RuntimeError", "message": '
           '"the preview is not complete: 1 of 16 frames were never written"}')
    with pytest.raises(AssertionError):
        _assert_sentinel("preview_walk.py", [old], outcome=HALTED, gate="PREVIEW",
                         error="RuntimeError", evidence={"missing": ["00007.png"]})


# ===========================================================================================
# The three other family censuses this wave's instruments findings name. Each derives its
# population from the TREE (wave 8's rule), asserts SIZE and MEMBERSHIP, then the property,
# and has a red direction that adds a member without the property.
#
# They live here rather than in the wave-6 files they correct, because those files
# (`test_render_visibility.py`, `test_retopo_and_bake.py`, `test_canon_spend.py`) are the
# tests domain's this wave and a second implementation in them would be a merge conflict
# wearing a census. The wave-6 checks still pass; these are strictly wider.
# ===========================================================================================


def _dotted(node):
    parts, cur = [], node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
    return ".".join(reversed(parts))


def _calls(tree):
    """Every call in `tree`, as dotted names -- `bpy.ops.import_scene.gltf`, `import_glb`."""
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            out.append((node.func.id, node.lineno))
        elif isinstance(node.func, ast.Attribute):
            out.append((_dotted(node.func), node.lineno))
    return out


def _tree(directory, filename):
    with open(os.path.join(directory, filename), encoding="utf-8") as fh:
        return ast.parse(fh.read())


# ------------------------------------------------- F-0e7d8b05: who imports a GLB, really


def tools_that_import_a_glb(directory=TOOLS):
    """Every tool that brings a GLB into the scene, by EITHER route.

    `tests/test_render_visibility.py:89` builds this population as `"import_glb(" in src`,
    which is 9 files. Twelve more import through `bpy.ops.import_scene.gltf` directly and
    are invisible to it -- including `preview_glb.py`, which was measuring the unfiltered
    mesh list. Derived here by AST over the call sites, which is 21.
    """
    found = []
    for fn in sorted(os.listdir(directory)):
        if not fn.endswith(".py"):
            continue
        names = {n for n, _ in _calls(_tree(directory, fn))}
        if any(n == "import_glb" or n.endswith(".import_glb")
               or n.endswith("import_scene.gltf") for n in names):
            found.append(fn)
    return found


#: Measured 2026-09-04. 21 files: the 20 Blender-side tools that import a subject, plus
#: `stage_render.py`, which imports `bpy` lazily and so is not in `blender_tools()`.
GLB_IMPORTERS = [
    "author_walk.py", "check_relift.py", "diagnose_bone_heat.py", "lift_solve.py",
    "make_binding_sheet.py", "make_parts_sheet.py", "make_rig_sheet.py",
    "make_skeleton_sheet.py", "make_test_armature.py", "preview_glb.py", "preview_walk.py", "probe_glb.py",
    "probe_subject.py", "render_performer.py", "render_start_frame.py",
    "render_turnaround.py", "rig_bake.py", "rig_character.py", "rig_parts.py",
    "rig_repair.py", "rig_retopo.py", "stage_render.py",
]

#: NAMED, DATED and CHECKED (wave 8's rule 4), not asserted by name alone. Both of these
#: import a GLB and neither FRAMES, BOUNDS nor POSITIONS anything from the mesh list, which
#: is what `render_visible_meshes` exists to protect:
#:
#:   probe_glb.py   reports what a file CONTAINS -- an object-type histogram, counts, bone
#:                  names. Its `mesh_objects` count includes the importer's decoy on
#:                  purpose, the way `object_types` does.
#:   rig_parts.py   refuses outright when the mesh count is not 1, loudly, rather than
#:                  measuring the list.
#:
#: `test_the_exemptions_are_a_subset_and_still_earn_it` checks that reason mechanically.
VISIBILITY_EXEMPT = {"probe_glb.py", "rig_parts.py"}

#: The helpers whose presence means a tool FRAMES or BOUNDS from the imported list. An
#: exempt tool that starts calling one of these stops being exempt.
FRAMING_HELPERS = ("world_bounds", "world_bounds_over_frames", "evaluated_world_vertices",
                   "auto_radius", "orbit_matrix", "solve_camera", "scene_bbox",
                   "framing_cloud", "union_sphere")


def test_the_glb_importing_population_is_the_size_and_membership_it_was_measured_to_be():
    derived = tools_that_import_a_glb()
    assert len(derived) == 22, derived
    assert sorted(derived) == sorted(GLB_IMPORTERS), sorted(set(derived) ^ set(GLB_IMPORTERS))


@pytest.mark.parametrize("filename", [f for f in GLB_IMPORTERS
                                      if f not in VISIBILITY_EXEMPT])
def test_every_tool_that_measures_imported_meshes_filters_by_render_visibility(filename):
    with open(os.path.join(TOOLS, filename), encoding="utf-8") as fh:
        src = fh.read()
    assert "render_visible_meshes" in src, (
        f"{filename} imports a GLB and never filters by render visibility. Blender's glTF "
        f"importer drops a hidden radius-1.0 Icosphere into `glTF_not_exported`; measuring "
        f"it reframes the shot (E02-report.md:34: a 3.23:1 figure read as a 1.05:1 "
        f"near-cube) and no gate downstream can see it.")


def test_the_exemptions_are_a_subset_and_still_earn_it():
    """An exemption set that is not re-derived is how `preview_glb` stayed exempt on a
    premise its own docstring contradicted."""
    derived = set(tools_that_import_a_glb())
    assert VISIBILITY_EXEMPT <= derived, VISIBILITY_EXEMPT - derived
    for filename in sorted(VISIBILITY_EXEMPT):
        names = {n for n, _ in _calls(_tree(TOOLS, filename))}
        framing = sorted(n for n in names
                         if any(n == h or n.endswith("." + h) for h in FRAMING_HELPERS))
        assert framing == [], (
            f"{filename} now calls {framing}: it frames or bounds from the imported list, "
            f"so the reason it is exempt from the render-visibility filter no longer holds")


def test_preview_glb_is_the_file_the_wave_six_census_could_not_see():
    """The specific site. `preview_glb.py:70` selected `type == "MESH"` and then measured
    that list -- the triangle total, and `scene_bbox`, whose radius sets every camera
    distance and whose dims/hi.z set the head-crop centre and radius."""
    with open(os.path.join(TOOLS, "preview_glb.py"), encoding="utf-8") as fh:
        src = fh.read()
    assert "render_visible_meshes" in src
    assert "mesh_objects_excluded" in src, (
        "preview_glb filters but does not record what it excluded (the shape "
        "probe_subject.py:57-59 uses)")
    # and the substring census that missed it would still miss it, which is why the
    # derivation above is by AST rather than by `"import_glb(" in src`
    assert "import_glb(" not in src


def test_the_glb_import_derivation_catches_a_tool_the_substring_scan_misses(tmp_path):
    """RED direction: a tool that imports through `bpy.ops` and never filters."""
    (tmp_path / "sneaky.py").write_text(
        "import bpy\n"
        "def main(path):\n"
        "    bpy.ops.import_scene.gltf(filepath=path)\n"
        "    return [o for o in bpy.data.objects if o.type == 'MESH']\n", encoding="utf-8")
    derived = tools_that_import_a_glb(str(tmp_path))
    assert derived == ["sneaky.py"], derived
    src = (tmp_path / "sneaky.py").read_text(encoding="utf-8")
    assert "import_glb(" not in src, "the wave-6 substring census would have returned []"
    assert "render_visible_meshes" not in src, "and this member fails the property"


# ------------------------------------------ F-fa4e6bb0: who states which Blender ran it


def test_every_blender_side_tool_records_the_blender_it_ran_on():
    """`tests/test_retopo_and_bake.py:122` builds its population as `'"tool":' in src`, a
    literal key match that returned 13 of 21. Six tools wrote JSON records -- four
    `panels.json` writers, `preview_glb`'s `_stats.json` and `preview_walk`'s OK payload --
    with neither `blender_provenance()` nor `bpy.app.version_string` anywhere, and the
    census could not see any of them. Those panels are not layout-only: `make_rig_sheet`
    prints `max_vertex_motion` onto the sheet, `make_parts_sheet` prints
    `max_displacement`, and `make_skeleton_sheet` is the artifact the Director gates the
    experiment at.

    The population here is every Blender-side tool, derived by the `import bpy` walk: all
    21 emit a JSON record, if only the halt sentinel, and a recipe that does not reproduce
    its output is not a recipe.

    WAVE 14, F-252f399d -- THE NODE. This test used to be the source-text predicate
    `'blender_provenance()' not in src and 'bpy.app.version_string' not in src`, an OR that
    a PARTIAL record satisfies: measured on the wave-13 tree, fourteen record sites carried
    `blender_provenance()` (version, version_tuple, build_hash, build_date and the numpy
    version) while TEN carried the bare `bpy.app.version_string` -- four of them
    `rig_character`'s own manifests, the records that describe the rigged GLB and whose
    Gate D verdict is a numerical comparison between two builds. The stricter half was a
    parametrisation over six named files. Both are replaced by ONE walk keyed on the record
    dicts themselves: every `"blender"` VALUE in every dict literal in the module must be
    the `blender_provenance()` call, except inside a `raise`, where a version string is
    refusal CONTEXT rather than a record.
    """
    derived = blender_tools_in(TOOLS)
    assert len(derived) == 22, derived
    partial, missing = [], []
    for fn in derived:
        with open(os.path.join(TOOLS, fn), encoding="utf-8") as fh:
            src = fh.read()
        values = _blender_field_values(src)
        record_values = [text for text, in_raise in values if not in_raise]
        # `stage_render` states its provenance through a backend method
        # (`self._bs.blender_provenance()`) rather than as a `"blender"` key in a dict
        # literal, so "records nothing" is the absence of BOTH -- the exemption is the
        # REASON (the call is made), not a name on a list.
        if not values and "blender_provenance()" not in src:
            missing.append(fn)
        for text in record_values:
            if "blender_provenance()" not in text:
                partial.append((fn, text))
    assert missing == [], missing
    assert partial == [], partial


def _blender_field_values(src):
    """`[(unparsed value, is inside a raise)]` for every `"blender": ...` in a dict literal.

    Keyed on the RECORD's key, not on a substring anywhere in the module -- so a tool that
    writes a full provenance in one manifest and a bare version string in a second is
    visible, which is exactly the shape the OR could not see (`rig_character` carried four
    of them).
    """
    tree = ast.parse(src)
    in_raise = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Raise):
            for child in ast.walk(node):
                in_raise.add(id(child))
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for k, v in zip(node.keys, node.values):
            if isinstance(k, ast.Constant) and k.value == "blender":
                out.append((ast.unparse(v), id(node) in in_raise))
    return out


def test_the_record_census_goes_red_on_a_partial_provenance():
    """PROVE THE CENSUS RED on the shape it exists to catch (wave-8 rule 3, wave-12 rule 2):
    a module whose record carries the bare version string rather than the full provenance.
    The old OR returned green on exactly this input."""
    partial = (
        'import bpy\n'
        'def main():\n'
        '    return {"tool": "x", "blender": bpy.app.version_string}\n')
    values = _blender_field_values(partial)
    assert values == [("bpy.app.version_string", False)], values
    assert all("blender_provenance()" not in t for t, _ in values)
    full = (
        'import bpy\n'
        'from armature_core import blender_scene\n'
        'def main():\n'
        '    return {"tool": "x", "blender": blender_scene.blender_provenance()}\n')
    assert _blender_field_values(full) == [
        ("blender_scene.blender_provenance()", False)]


def test_a_version_string_inside_a_refusal_is_not_a_record():
    """The exemption, named and derived rather than listed: the four sheet tools'
    exhausted-engine refusals put `bpy.app.version_string` in an EVIDENCE dict, which is
    context for a halt and not a record of a run."""
    refusing = (
        'import bpy\n'
        'def light(scene):\n'
        '    raise RuntimeError("no engine", {"blender": bpy.app.version_string})\n')
    assert _blender_field_values(refusing) == [("bpy.app.version_string", True)]


# ------------------------------------------ F-bba38f1c: the engine that silently was not


def tools_with_an_engine_candidate_loop(directory=TOOLS):
    """Every tool that tries more than one render-engine identifier."""
    found = []
    for fn in sorted(os.listdir(directory)):
        if not fn.endswith(".py"):
            continue
        with open(os.path.join(directory, fn), encoding="utf-8") as fh:
            src = fh.read()
        if "ENGINE_CANDIDATES" in src or 'for eng in ("BLENDER_EEVEE' in src:
            found.append(fn)
    return found


#: RE-DERIVED 2026-09-04 (wave 14, instruments, F-0bf74152): four -> nine. The guarded loop
#: existed on the four sheet tools and on NONE of the four renderers, which each pinned the
#: single literal `scene.render.engine = "BLENDER_EEVEE"`; `rig_bake` pinned `"CYCLES"`.
#: All five now carry the same guarded selection. The number is re-measured, not re-typed.
#: The stronger census -- over every ASSIGNMENT to `<scene>.render.engine` rather than over
#: the tools that happen to have a candidate list -- lives in
#: `tests/test_instruments_amend_w14.py::test_every_render_engine_assignment_is_guarded`,
#: because a census of "tools that have the loop" cannot see a tool that does not.
ENGINE_LOOPS = ["make_binding_sheet.py", "make_parts_sheet.py", "make_skeleton_sheet.py",
                "preview_glb.py", "preview_walk.py", "render_performer.py",
                "render_start_frame.py", "render_turnaround.py", "rig_bake.py"]


def test_the_engine_loop_population_is_the_nine_it_was_measured_to_be():
    assert sorted(tools_with_an_engine_candidate_loop()) == sorted(ENGINE_LOOPS)


class _RefusingRender:
    """A `scene.render` whose `engine` setter raises `TypeError` for every name."""

    def __setattr__(self, name, value):
        if name == "engine":
            raise TypeError("no such engine")
        object.__setattr__(self, name, value)


class _RefusingScene:
    def __init__(self):
        self.render = _RefusingRender()


#: `rig_bake` bakes, so its one candidate is a ray-tracer and not EEVEE. The EEVEE ORDER
#: clause applies to the eight tools that draw a picture; the FALL-THROUGH clause applies to
#: all nine, because that is the property (F-0bf74152, wave 14).
EEVEE_LOOPS = [f for f in ENGINE_LOOPS if f != "rig_bake.py"]


@pytest.mark.parametrize("filename", EEVEE_LOOPS)
def test_the_engine_loops_agree_on_the_order(filename):
    """MEASURED 2026-09-04: `preview_glb` tried the two names in the OPPOSITE order to the
    three sheets, so on a Blender where both are valid they did not agree on which engine
    drew them. Wave 14 brought the four renderers in on the same order."""
    from blender_stub import load_tool

    mod = load_tool(filename)
    assert mod.ENGINE_CANDIDATES == ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"), filename


@pytest.mark.parametrize("filename", ENGINE_LOOPS)
def test_the_engine_loops_refuse_a_fall_through(filename):
    """MEASURED 2026-09-04: the loop had no `else`, so if a future Blender renamed both
    identifiers the `for` would complete normally, nothing would be set, and the sheet
    would render on the factory default with no field in the record able to say so."""
    from armature_core.errors import GateFailure
    from blender_stub import load_tool

    mod = load_tool(filename)
    setter = getattr(mod, "select_engine", None) or mod.light_the_scene
    with pytest.raises(GateFailure,
                       match=r"none of the candidate render engines is valid"):
        setter(_RefusingScene())


@pytest.mark.parametrize("filename", ENGINE_LOOPS)
def test_the_engine_actually_set_reaches_the_record(filename):
    """WAVE 14: `rig_bake`'s manifest reads the engine off the scene
    (`bpy.context.scene.render.engine`) because `select_engine`'s return is local to
    `bake()`; what the census is about is that no record states the engine as a LITERAL,
    which is asserted for every tool by
    `tests/test_instruments_amend_w14.py::test_the_four_renderers_record_the_engine_they_actually_set`."""
    with open(os.path.join(TOOLS, filename), encoding="utf-8") as fh:
        src = fh.read()
    assert ('"engine": engine' in src
            or 'stats["engine"] = select_engine' in src
            or '"engine": bpy.context.scene.render.engine' in src), filename


# --------------------- F-8d2b9d7d: a refusal that fires before a pixel exists leaves no dir


def renderers(directory=TOOLS):
    """Every tool whose `main` both creates the output directory AND renders into it."""
    found = []
    for fn in sorted(os.listdir(directory)):
        if not fn.endswith(".py"):
            continue
        tree = _tree(directory, fn)
        fn_main = next((n for n in tree.body
                        if isinstance(n, ast.FunctionDef) and n.name == "main"), None)
        if fn_main is None:
            continue
        calls = _calls(fn_main)
        if (any(n == "os.makedirs" for n, _ in calls)
                and any(n == "bpy.ops.render.render" for n, _ in calls)):
            found.append(fn)
    return found


RENDERERS = ["preview_walk.py", "render_performer.py", "render_start_frame.py",
             "render_turnaround.py"]


def test_the_renderer_population_is_the_four_it_was_measured_to_be():
    assert sorted(renderers()) == sorted(RENDERERS)


@pytest.mark.parametrize("filename", RENDERERS)
def test_no_refusal_reachable_before_the_first_render_sits_below_the_makedirs(filename):
    """Thirteen refusals across these four files sat BELOW `os.makedirs` and ABOVE the
    first render, so each left an empty output directory behind -- which is the input
    condition a later run reads as a used one.

    This is the part of the builders' ordering rule that TRANSFERS. The whole rule (the
    last in-tool gate above the first write) cannot: `render_start_frame`'s alpha gate and
    coverage gate READ the render, and a check that reads a render cannot precede it."""
    tree = _tree(TOOLS, filename)
    fn_main = next(n for n in tree.body
                   if isinstance(n, ast.FunctionDef) and n.name == "main")
    calls = _calls(fn_main)
    makedirs = min(l for n, l in calls if n == "os.makedirs")
    first_render = min(l for n, l in calls if n == "bpy.ops.render.render")
    between = sorted(n.lineno for n in ast.walk(fn_main)
                     if isinstance(n, ast.Raise) and makedirs < n.lineno < first_render)
    assert between == [], (
        f"{filename}: refusals at {between} sit below os.makedirs (line {makedirs}) and "
        f"above the first render (line {first_render}); each leaves an empty --out behind")


def test_the_ordering_scan_catches_the_shape_it_was_written_for(tmp_path):
    """RED direction."""
    (tmp_path / "leaky.py").write_text(
        "import bpy\n"
        "import os\n"
        "def main():\n"
        "    os.makedirs(out, exist_ok=True)\n"
        "    if not subject:\n"
        "        raise RenderGate('nothing to render')\n"
        "    bpy.ops.render.render(write_still=True)\n", encoding="utf-8")
    assert renderers(str(tmp_path)) == ["leaky.py"]
    tree = _tree(str(tmp_path), "leaky.py")
    fn_main = next(n for n in tree.body
                   if isinstance(n, ast.FunctionDef) and n.name == "main")
    calls = _calls(fn_main)
    makedirs = min(l for n, l in calls if n == "os.makedirs")
    first_render = min(l for n, l in calls if n == "bpy.ops.render.render")
    between = [n.lineno for n in ast.walk(fn_main)
               if isinstance(n, ast.Raise) and makedirs < n.lineno < first_render]
    assert between == [6], between
