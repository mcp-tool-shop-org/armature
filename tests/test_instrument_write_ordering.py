"""A refused run leaves nothing behind: every in-tool andon fires above the first write.

`tests/test_canon_spend.py` pins this for the seven spend builders — "every refusal below
the first write leaves an output directory behind when it fires" — and the wave-6 sweep
that earned it was applied to those seven only. The measurement instruments were never
swept. Measured on this branch 2026-09-04, by the walk below (first `os.makedirs` line in
`main()` against the LAST in-tool refusal line in the same function):

    composite_reference   makedirs 203   last gate 231 (gate_flat)
    fit_reference         makedirs 171   last gate 181 (parse_plate)
    lift_clip             makedirs 247   last gate 263 (frame_paths)
    make_lift_sheet       makedirs 186   last gate 198 (require_frames)
    make_plate            makedirs 199   last gate 208 (parse_plate)
    make_review_clip      makedirs  70   last gate  97 (require_frames)
    measure_lift          makedirs 496   last gate 513 (gate_pairing)
    project_pose_keypoints makedirs 228  last gate 274 (gate_motion)

Nothing irreversible is at stake and nothing is paid — what is left behind is an EMPTY
output directory after a halt, which a reader scanning `outputs/`, or a re-run into the
same `--out`, reads as an attempt that produced nothing rather than one that was refused.
`composite_reference` was the most pointed of the eight: it is the alpha law's own tool,
its docstring says its three andons all raise "before a byte is written", and that was
true of the first view only — the gates ran inside the write loop.

**The population is DERIVED, not typed.** It is every module in `tools/` whose
module-level `main()` both runs an in-tool refusal and writes, read off the AST — so a
tool added later joins this file by existing rather than by being remembered. The
membership is asserted against what was measured today, so a new member fails loudly.

**The exemptions are named, dated, and checked against their reason**, not merely listed:

* **Renders into its own output directory** — the tool writes the artefact that its later
  gates then measure, so the directory must exist before the gate can run. Checked
  mechanically: the module imports `bpy`.
* **Reads back what it wrote** — `pack_pose_pack` encodes the pack, re-decodes the FILE
  (`read_pack(dst)`) and runs Gate R over the decode, which is the whole point of Gate R;
  `render_pose_sticks` measures the PNGs it drew; `fetch_t2v_run` gates the order of files
  it downloaded. Read, not measured: the reason is stated per member below and each is
  checked to be a real member of the derived population that is NOT a `bpy` tool, so the
  two classes cannot silently absorb each other.
* **Out of this domain** — `lift_solve` (core-solvers) is a `bpy` tool and lands in the
  first class anyway; `fetch_t2v_run` (builders) is named in this wave's `skipped[]`.
"""

import ast
import glob
import os

import pytest

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")

#: The canon gate's three call names, as `tests/test_canon_spend.py` names them.
CANON_CALLS = ("gate_write", "canon_spend", "require_canon")

#: In-tool refusals that carry no `gate_`/`require_` prefix. Named rather than inferred,
#: exactly as `test_canon_spend.OTHER_GATE_CALLS` is: this walk is blind to any refusal it
#: cannot name, and each of these raises a typed error with an evidence dict.
OTHER_GATE_CALLS = (
    "verify", "frame_legality", "parse_plate", "parse_boxes", "frame_paths",
    "frame_population", "frames_by_number", "check_runs", "common_frame_count",
    "bound_windows",
)


def _called_name(node):
    f = node.func
    return (f.id if isinstance(f, ast.Name)
            else f.attr if isinstance(f, ast.Attribute) else "")


def _is_gate_call(name):
    return (name.startswith("gate_") or name.startswith("require_")
            or name in CANON_CALLS or name in OTHER_GATE_CALLS)


def _returning_branch_spans(fn):
    """Line spans of `if` bodies that end in a `return` or a `raise`.

    A write inside one of those is on a path that never reaches the code below it, so
    comparing its line number against a later refusal compares two mutually exclusive
    branches and reports a defect that cannot happen. Measured 2026-09-04 on
    `encode_control.main`: its `--survey` mode writes a codec report and returns, and the
    plate parse sixteen lines below is on the other branch. Corrected here rather than
    exempted, because the same shape will arrive again.
    """
    spans = []
    for node in ast.walk(fn):
        if (isinstance(node, ast.If) and node.body
                and isinstance(node.body[-1], (ast.Return, ast.Raise))):
            spans.append((node.body[0].lineno, node.body[-1].end_lineno))
    return spans


def _cli_body(tree):
    """The module-level function that IS the tool's command line — derived, not named.

    The census used to key on the function literally called `main`. That was the right node
    only while every tool's `main` held its own body: wave 10 split three builders'
    (`build_assembly_payload`, `build_cascade_payload`, `build_r2v_payload`) into
    `build_and_write(argv)` — which builds, gates and writes — plus a `main(argv)` that
    returns the process exit code and nothing else, because `main` used to `return wf`
    under `raise SystemExit(main())` and exited 1 on a fully gated success. Keyed on the
    NAME, this census reported "runs no in-tool refusal at all" for three tools whose
    refusals had not moved an inch.

    The derivation follows ONE delegation, and only out of a `main` that is a wrapper and
    nothing else: at most three statements (its docstring aside) and exactly one call to a
    module-level function of its own module. That function is then the body. Every other
    `main` — including the eight builders that never split — is read exactly as before.
    (An earlier draft keyed on "which function calls `parse_args`". Three builders define a
    module-level helper literally named `parse_args`, so it picked the helper and reported
    the same false emptiness one level down. Measured 2026-09-04.)
    """
    named = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    fn = named.get("main")
    if fn is None:
        return None
    body = [st for st in fn.body
            if not (isinstance(st, ast.Expr) and isinstance(st.value, ast.Constant))]
    if len(body) > 3:
        return fn
    called = {c.func.id for c in ast.walk(fn)
              if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
              and c.func.id in named}
    if len(called) == 1:
        return named[next(iter(called))]
    return fn


def gate_and_write_lines(src, what):
    """`({line: gate name}, {line: write kind})` for `main()`, or `(None, None)`.

    The same shape `test_canon_spend._gate_and_write_lines` computes for the builders,
    lifted here so the instruments are read by the same rule rather than a second one —
    plus the mutually-exclusive-branch correction above.
    """
    fn = _cli_body(ast.parse(src))
    if fn is None:
        return None, None
    gates_at, writes_at = {}, {}
    for node in ast.walk(fn):
        if not isinstance(node, ast.Call):
            continue
        called = _called_name(node)
        if _is_gate_call(called):
            gates_at.setdefault(node.lineno, called)
        elif called == "makedirs":
            writes_at.setdefault(node.lineno, "os.makedirs")
        elif (called == "open" and len(node.args) >= 2
              and isinstance(node.args[1], ast.Constant)
              and "w" in str(node.args[1].value)):
            writes_at.setdefault(node.lineno, 'open(..., "w")')
    spans = _returning_branch_spans(fn)
    for line in list(writes_at):
        for lo, hi in spans:
            if lo <= line <= hi and not any(lo <= g <= hi for g in gates_at):
                del writes_at[line]
                break
    return gates_at, writes_at


def _source(name):
    with open(os.path.join(TOOLS, f"{name}.py"), encoding="utf-8") as fh:
        return fh.read()


def derive_population():
    """Every `tools/*.py` whose `main()` both refuses and writes — walked, never typed."""
    out = {}
    for path in sorted(glob.glob(os.path.join(TOOLS, "*.py"))):
        name = os.path.basename(path)[:-3]
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
        gates_at, writes_at = gate_and_write_lines(src, name)
        if gates_at and writes_at:
            out[name] = (gates_at, writes_at)
    return out


def imports_bpy(name):
    """`import bpy` anywhere in the module — a Blender tool renders into its own out dir."""
    for node in ast.walk(ast.parse(_source(name))):
        if isinstance(node, ast.Import):
            if any(a.name == "bpy" or a.name.startswith("bpy.") for a in node.names):
                return True
        if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "bpy":
            return True
    return False


#: Measured 2026-09-04 by `derive_population()` on this tree. Asserted, so a tool that
#: starts gating-and-writing joins this file loudly rather than slipping past it.
POPULATION_MEASURED_2026_09_04 = {
    "author_walk", "build_animate_payload", "build_assembly_payload",
    "build_camera_i2v_payload", "build_cascade_payload", "build_i2v_payload",
    "build_lora_arm_payload", "build_payload", "build_r2v_payload", "build_t2v_payload",
    # JOINED 2026-09-04 by the instruments wave-10 amend (F-6ee68fc0): `check_relift.main`
    # now calls `gate_relift_window` over each GLB's own keyed action range, so it
    # gates-and-writes where before it only wrote. Its makedirs already sits one line above
    # the record it writes, so nothing is stranded.
    "check_relift",
    "composite_reference", "fetch_t2v_run", "fit_reference", "gate_b_frames",
    "gate_saved_graph", "lift_clip", "lift_solve", "make_ab_clip", "make_crop_strip",
    "make_gate0_sheet", "make_identity_sheet", "make_lift_sheet", "make_pick_sheet",
    "make_plate", "make_review_clip", "make_skeleton_sheet", "make_startframe_sheet",
    # JOINED 2026-09-04 by the instruments wave-10 amend (F-13bd448d): `preview_glb.main`
    # now calls `gate_previews_written` over the four paths its renders returned, so it
    # gates-and-writes where before it only wrote. It is a `bpy` tool and lands in the
    # first exempt class; the ordering itself is pinned by
    # `tests/test_instruments_amend_w10.py::
    # test_no_refusal_sits_between_the_output_directory_and_the_first_byte`, which measures
    # the reason rather than the `imports_bpy` proxy.
    "preview_glb",
    # JOINED 2026-09-04 by the instruments wave-12 amend (F-5b3ead49): `probe_subject.main`
    # now calls `require_openable` before the population is built and
    # `require_something_measured` before its OK line, so it gates-and-writes where before
    # it only wrote. It is a `bpy` tool; its ordering is pinned by
    # `tests/test_instruments_amend_w12.py::
    # test_no_refusal_is_stranded_below_the_output_directory_in_any_of_the_eleven`'s
    # population test, which measures the reason rather than the `imports_bpy` proxy, and
    # `os.makedirs` sits below both refusals.
    "probe_subject",
    # JOINED 2026-09-04 by the instruments wave-12 amend (F-9b2d4106): all four now call
    # `rig_character.gate_glb_written` after `bpy.ops.export_scene.gltf`, which returns an
    # operator status set and can return CANCELLED without raising. They gate-and-write
    # where before they only wrote. All four are `bpy` tools; the ordering itself is pinned
    # by `tests/test_instruments_amend_w12.py`'s window census, which measures the reason
    # rather than the `imports_bpy` proxy.
    "make_test_armature", "rig_bake", "rig_repair", "rig_retopo",
    "make_thesis_sheet", "measure_floor", "measure_lift",
    "pack_pose_pack", "project_pose_keypoints", "render_performer", "render_pose_sticks",
    "render_start_frame", "render_turnaround", "rig_character", "rig_parts",
}

#: The write IS the thing the later gate measures. Named, dated 2026-09-04, and each
#: member re-checked below against the reason rather than trusted for being on a list.
GATES_READ_BACK_WHAT_THEY_WROTE = {
    "pack_pose_pack": "write_pack(dst) then read_pack(dst); Gate R compares the decode",
    "render_pose_sticks": "gate_ink measures the PNGs this tool just drew",
    "fetch_t2v_run": "the order gate reads the files this tool just downloaded",
}


def test_the_branch_correction_is_exercised_and_can_still_see_a_real_write():
    """Both directions of `_returning_branch_spans`, so the correction is not a blanket
    excuse: `encode_control.main` writes only inside its returning `--survey` branch and
    so has no comparable write, while a write in a branch that FALLS THROUGH is still
    counted."""
    gates_at, writes_at = gate_and_write_lines(_source("encode_control"), "encode_control")
    assert gates_at, "encode_control.main runs no in-tool refusal"
    assert writes_at == {}, writes_at

    falls_through = (
        "import os\n"
        "def main():\n"
        "    if flag:\n"
        "        os.makedirs(out)\n"
        "    gate_something()\n")
    g, w = gate_and_write_lines(falls_through, "probe")
    assert w, "a write in a branch that falls through must still be counted"


def test_the_population_is_the_one_measured_today():
    derived = set(derive_population())
    assert derived == POPULATION_MEASURED_2026_09_04, {
        "new": sorted(derived - POPULATION_MEASURED_2026_09_04),
        "gone": sorted(POPULATION_MEASURED_2026_09_04 - derived),
    }


def test_every_exemption_is_a_real_member_of_the_derived_population():
    derived = set(derive_population())
    assert set(GATES_READ_BACK_WHAT_THEY_WROTE) <= derived, sorted(
        set(GATES_READ_BACK_WHAT_THEY_WROTE) - derived)


def test_the_two_exemption_classes_do_not_absorb_each_other():
    """A `bpy` tool must not also be claimed under the read-back reason, or the second
    list would grow to cover the first and stop naming anything."""
    both = sorted(n for n in GATES_READ_BACK_WHAT_THEY_WROTE if imports_bpy(n))
    assert both == [], both


# --------------------------- the bpy exemption, keyed on the REFUSAL rather than the module
#
# WAVE 10, F-82e87ccc. The stated reason for the bpy exemption is narrow — "the tool writes
# the artefact that its later gates then measure, so the directory must exist before the
# gate can run" — and the check was `if imports_bpy(name): pytest.skip(...)`, which excuses
# EVERY refusal in the module rather than the ones that measure a rendered artefact. That is
# the proxy-instead-of-reason shape this wave exists to close: `imports bpy` is a property of
# the MODULE; "measures what it wrote" is a property of the REFUSAL.
#
# Measured 2026-09-04 over the derived population (8 bpy members, 3 read-back members, 27
# policed): 29 refusals sit below their tool's first write, and several are plainly
# independent of the output directory — `gate_n_names`, `gate_space_is_identity` and
# `gate_objects_registered` read the ARMATURE, not a render.
#
# So the module-wide skip is replaced by a per-refusal RATCHET, asserted by equality in both
# directions: the set below may not GROW (a new refusal under a write fails here, naming the
# tool and the refusal) and a refusal that moves above the write must be deleted from it in
# the same commit. Each entry is routed to the domain that owns the tool: author_walk,
# lift_solve, render_performer, render_start_frame, render_turnaround, rig_character and
# rig_parts are instruments (lift_solve is core-solvers' module and a bpy tool);
# make_skeleton_sheet is instruments.
REFUSALS_BELOW_THE_FIRST_WRITE_IN_A_BPY_TOOL = {
    # WAVE-10 MERGE (coordinator, 2026-09-04): instruments moved thirteen refusals above the first write across four
    # tools (F-d47095fa): `author_walk` and `lift_solve` each CLOSED four here (measured; deleted).
    # WAVE 12 (instruments, F-9b2d4106): `gate_glb_written` joins eight entries across six
    # tools, and it is the EXEMPTION'S OWN REASON rather than an excuse — it reads back the
    # GLB the export just wrote, so it cannot run before that write any more than
    # `preview_glb.gate_previews_written` can run before its four renders.
    # `bpy.ops.export_scene.gltf` returns an operator status set and can return CANCELLED
    # without raising; nothing in the tree refused a zero-byte export before this wave.
    "author_walk": ["gate_a_arrival", "gate_glb_written", "gate_n_names"],
    "lift_solve": ["gate_arrived", "gate_glb_written", "gate_n_names"],
    "make_skeleton_sheet": ["gate_any_pivot_matched"],
    "make_test_armature": ["gate_glb_written"],
    "render_performer": ["gate_coverage"],
    # WAVE-10 MERGE (coordinator, 2026-09-04): `preview_glb` JOINED — `gate_previews_written` checks that the four views
    # reached disk (F-13bd448d) and can only run AFTER the writes; a refusal that verifies its own
    # output is below the first write by construction. `render_start_frame.gate_whole` and three
    # `rig_parts` refusals CLOSED (measured on the merged tree; deleted, not relaxed).
    "preview_glb": ["gate_previews_written"],
    "render_start_frame": ["gate_alpha", "gate_backdrop"],
    "render_turnaround": ["gate_set_distinct", "gate_view_alpha", "gate_view_crop",
                          "gate_whole"],
    # WAVE-12 (instruments, F-244b2ad5): `rig_character` CLOSED both of its entries in the
    # commit that moved them. `os.makedirs` left the top of `main` and is now created per
    # branch below the last refusal, so Gate D and Gate N both sit ABOVE the first write on
    # every route. Deleted here, as this ratchet's own rule requires, rather than relaxed.
    "rig_bake": ["gate_glb_written"],
    "rig_parts": ["gate_atlas_untouched", "gate_glb_written", "gate_part_names"],
    "rig_repair": ["gate_glb_written"],
    "rig_retopo": ["gate_glb_written"],
}


def refusals_below_the_first_write(name):
    """The refusal NAMES in `name.main` that sit below its first write.

    Keyed on names, not line numbers: a line number moves under any edit above it, which is
    how 23 of 31 entries in `test_gates`'s evidence ratchet came to name nothing
    (F-a30afea5). A duplicate name at two lines collapses to one entry, deliberately — the
    question this ratchet asks is "which refusals are excused", not "how many times".
    """
    gates_at, writes_at = gate_and_write_lines(_source(name), name)
    if not gates_at or not writes_at:
        return []
    first_write = min(writes_at)
    return sorted({gates_at[ln] for ln in gates_at if ln > first_write})


def test_the_bpy_exemption_is_a_per_refusal_ratchet_and_not_a_module_wide_skip():
    """Size and membership before the property, and equality in BOTH directions.

    A subset assertion here would let a closed refusal sit in the list forever and a new
    one arrive under an already-listed tool in silence.
    """
    bpy_members = sorted(n for n in derive_population() if imports_bpy(n))
    listed = sorted(REFUSALS_BELOW_THE_FIRST_WRITE_IN_A_BPY_TOOL)
    assert set(listed) <= set(bpy_members), sorted(set(listed) - set(bpy_members))
    derived = {n: refusals_below_the_first_write(n) for n in bpy_members}
    derived = {n: v for n, v in derived.items() if v}
    assert derived == REFUSALS_BELOW_THE_FIRST_WRITE_IN_A_BPY_TOOL, {
        "new refusals under a write (fix, or add with the reason)":
            {n: sorted(set(v) - set(REFUSALS_BELOW_THE_FIRST_WRITE_IN_A_BPY_TOOL.get(n, [])))
             for n, v in derived.items()
             if set(v) - set(REFUSALS_BELOW_THE_FIRST_WRITE_IN_A_BPY_TOOL.get(n, []))},
        "closed — delete these in the commit that moved them":
            {n: sorted(set(v) - set(derived.get(n, [])))
             for n, v in REFUSALS_BELOW_THE_FIRST_WRITE_IN_A_BPY_TOOL.items()
             if set(v) - set(derived.get(n, []))},
    }
    # Two numbers, because they count two different things and the finding quoted the
    # second: 26 distinct refusal NAMES over 29 SITES, the gap being names that appear
    # twice under one tool (`author_walk.gate_n_names` at :552 and :604, and two more).
    # The ratchet keys on names; the site count is asserted beside it so a duplicate
    # appearing or vanishing is visible rather than silently collapsed.
    # WAVE-10 MERGE (coordinator, 2026-09-04): 26 names / 29 sites -> re-measured on the merged tree after instruments moved
    # thirteen refusals above the first write (F-d47095fa); both numbers below are the measurement.
    # WAVE 12 (instruments): 17 names / 17 sites -> 22 / 23. `rig_character`'s
    # `gate_d_determinism` and `gate_n_names` both moved ABOVE the first write when
    # `os.makedirs` left the top of `main` (F-244b2ad5, -2); `gate_glb_written` joined
    # eight entries across six tools (F-9b2d4106, +7 names because `rig_parts` already
    # listed two). Both numbers are re-measured, not relaxed; the site count exceeds the
    # name count because `author_walk.gate_n_names` appears at two lines under one tool.
    assert sum(len(v) for v in derived.values()) == 22, sorted(derived.items())
    sites = 0
    for name in bpy_members:
        gates_at, writes_at = gate_and_write_lines(_source(name), name)
        if not gates_at or not writes_at:
            continue
        sites += sum(1 for ln in gates_at if ln > min(writes_at))
    assert sites == 23, (
        f"{sites} refusal SITES below a first write; 23 were measured on 2026-09-04 "
        f"(wave 12, after rig_character's two moved above its first write and "
        f"`gate_glb_written` landed on the eight glTF exporters)")


def test_a_bpy_tool_with_no_excused_refusal_is_held_to_the_ordering_rule():
    """The exemption excuses REFUSALS, not modules: a bpy tool whose refusals all sit above
    its first write must still be asserted, not skipped for importing bpy."""
    bpy_members = sorted(n for n in derive_population() if imports_bpy(n))
    clean = [n for n in bpy_members if not refusals_below_the_first_write(n)]
    for name in clean:
        gates_at, writes_at = gate_and_write_lines(_source(name), name)
        if not gates_at or not writes_at:
            continue
        assert max(gates_at) < min(writes_at), (name, gates_at, writes_at)


def test_the_per_refusal_exemption_goes_red_on_a_new_refusal_under_a_write():
    """Rule 3, on a real member's real source: insert a refusal BELOW the first write in a
    bpy tool and the derived set must grow, so the ratchet above would fail."""
    name = "rig_character"
    src = _source(name)
    _, writes_at = gate_and_write_lines(src, name)
    at = min(writes_at)
    lines = src.splitlines(keepends=True)
    target = lines[at - 1]
    indent = target[:len(target) - len(target.lstrip())]
    lines.insert(at, f"{indent}gate_a_brand_new_refusal(x)\n")
    gates_at, mutated_writes = gate_and_write_lines("".join(lines), name)
    below = sorted({gates_at[ln] for ln in gates_at if ln > min(mutated_writes)})
    assert "gate_a_brand_new_refusal" in below, below
    assert set(below) - set(
        REFUSALS_BELOW_THE_FIRST_WRITE_IN_A_BPY_TOOL.get(name, [])) == {
        "gate_a_brand_new_refusal"}


@pytest.mark.parametrize("name", sorted(POPULATION_MEASURED_2026_09_04))
def test_no_refusal_sits_below_the_first_write(name):
    if name in GATES_READ_BACK_WHAT_THEY_WROTE:
        pytest.skip(f"exempt: {GATES_READ_BACK_WHAT_THEY_WROTE[name]}")
    if name in REFUSALS_BELOW_THE_FIRST_WRITE_IN_A_BPY_TOOL:
        pytest.skip(
            "its refusals under the first write are named individually in "
            "REFUSALS_BELOW_THE_FIRST_WRITE_IN_A_BPY_TOOL and ratcheted there; this "
            "module-level assertion would say nothing the ratchet does not")
    gates_at, writes_at = gate_and_write_lines(_source(name), name)
    last_gate, first_write = max(gates_at), min(writes_at)
    assert last_gate < first_write, (
        f"{name}.main writes at line {first_write} ({writes_at[first_write]}) but is "
        f"still refusing at line {last_gate} ({gates_at[last_gate]}); a run refused there "
        f"leaves an output directory behind that reads as an attempt that produced "
        f"nothing. Refusals in main: {sorted((ln, n) for ln, n in gates_at.items())}")


@pytest.mark.parametrize("name", sorted(
    n for n in ("composite_reference", "fit_reference", "lift_clip", "make_lift_sheet",
                "make_plate", "make_review_clip", "measure_lift",
                "project_pose_keypoints")))
def test_the_ordering_check_goes_red_when_a_write_moves_above_the_gate(name):
    """The falsifiability fixture, on each instrument's real source: a check that cannot
    fail is not a check. Move a write above `main()`'s FIRST refusal and the comparison
    must flip."""
    src = _source(name)
    gates_at, _ = gate_and_write_lines(src, name)
    at = min(gates_at)
    lines = src.splitlines(keepends=True)
    target = lines[at - 1]
    indent = target[:len(target) - len(target.lstrip())]
    lines.insert(at - 1, f"{indent}os.makedirs(_probe_out, exist_ok=True)\n")
    mutated_gates, mutated_writes = gate_and_write_lines("".join(lines), name)
    assert mutated_gates and mutated_writes
    assert not max(mutated_gates) < min(mutated_writes), (
        f"a write inserted above {name}.main's first refusal did not move the "
        f"comparison; the ordering check cannot fail")
