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
    "composite_reference", "fetch_t2v_run", "fit_reference", "gate_b_frames",
    "gate_saved_graph", "lift_clip", "lift_solve", "make_ab_clip", "make_crop_strip",
    "make_gate0_sheet", "make_identity_sheet", "make_lift_sheet", "make_pick_sheet",
    "make_plate", "make_review_clip", "make_skeleton_sheet", "make_startframe_sheet",
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


@pytest.mark.parametrize("name", sorted(POPULATION_MEASURED_2026_09_04))
def test_no_refusal_sits_below_the_first_write(name):
    if imports_bpy(name) or name in GATES_READ_BACK_WHAT_THEY_WROTE:
        pytest.skip(f"exempt: {'renders into its own out dir (imports bpy)' if imports_bpy(name) else GATES_READ_BACK_WHAT_THEY_WROTE[name]}")
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
