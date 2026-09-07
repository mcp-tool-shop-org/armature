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

**The population is DERIVED, not typed.** It is every module in `tools/` whose CLI body
both runs an in-tool refusal and writes, read off the AST — so a tool added later joins
this file by existing rather than by being remembered. The membership is asserted against
what was measured today, so a new member fails loudly.

**WAVE 12 (F-183635ad) — the predicate is keyed on BEHAVIOUR, not on a spelling.** Until
this wave a refusal was recognised only by CALLEE NAME (`gate_`/`require_`/a named list).
An inline `raise` is not a call, and a helper whose name matches none of those spellings is
not one either, so both were invisible — and because `derive_population()` keeps a module
only when `gates_at and writes_at`, a tool whose refusals are ALL inline never entered the
population at all. Measured on this tree: 39 members under the old predicate, 62 under this
one; 25 tools strand a refusal below their first write, and nine of them
(`extract_clip_frames`, `make_parts_sheet`, `make_rig_sheet`, `make_shotset_sheet`,
`measure_cascade_clip`, `preview_walk`, `rig_bake`, `rig_repair`, `rig_retopo`) were
outside the census entirely. `make_rig_sheet.main` creates `<out>/` at :95 and
`<out>/panels/` at :97 and then raises `ArmatureError` inline at :112, :119 and :139, so a
refused run leaves two empty directories on disk and this file reported nothing about it.
The predicate now lives in `tests/_census_nodes.refusal_and_write_lines` — ONE
implementation, shared with `tests/test_canon_spend.py` (F-e63ce880) — and its blindness is
kept runnable as `by_name_only=True` so the red proof can show, in one test, that the old
walk cannot see the shape the new one reports.

**The exemptions are named, dated, and checked against their reason**, not merely listed:

* **Refuses below its first write** — a per-refusal ratchet, no longer a module-wide skip
  and no longer bpy-only. See the comment above `REFUSALS_BELOW_THE_FIRST_WRITE` for the
  direction of the assertion and why it is a ceiling while wave 12's moves land.
* **Reads back what it wrote** — a per-NAME excuse, administered in `READBACK_REASONS`.
  WAVE 14, F-3a0d4576: it used to be applied MODULE-wide, inside the ratchet's own `derived`
  expression and at the first branch of `test_no_refusal_sits_below_the_first_write`, which
  made the file's one asserted property blind to `pack_pose_pack`, `render_pose_sticks` and
  `fetch_t2v_run` — the three tools with the most refusals under a write. Each reason now
  NAMES the call that performs the read-back and a test finds that call in the tool's source
  (F-385f2b60); the names that are not read-backs are a dated backlog, `NOT_YET_MOVED`, with
  its size on the page.
* **Out of this domain** — `lift_solve` (core-solvers) is a `bpy` tool and lands in the
  first class anyway; `fetch_t2v_run` (builders) is named in this wave's `skipped[]`.
"""

import ast
import os

import pytest

import _census_nodes as CN

TOOLS = CN.TOOLS

#: The canon gate's three call names, as `tests/test_canon_spend.py` names them.
CANON_CALLS = CN.CANON_CALLS

#: In-tool refusals that carry no `gate_`/`require_` prefix and raise through a helper this
#: walk resolves anyway. Kept as a hint, not as the definition: since wave 12 the predicate
#: is BEHAVIOURAL (`_census_nodes.refusal_and_write_lines`) and a refusal is any `raise` of
#: an `ArmatureError` subclass, inline or one hop through a module-local helper.
OTHER_GATE_CALLS = (
    "verify", "frame_legality", "parse_plate", "parse_boxes", "frame_paths",
    "frame_population", "frames_by_number", "check_runs", "common_frame_count",
    "bound_windows",
)

#: Every `ArmatureError` subclass name, from the live class hierarchy AND from the tree.
#: Computed once: the walk below is run several hundred times across this module.
ERROR_NAMES = CN.armature_error_names()

# ONE implementation of each node, in `tests/_census_nodes.py` (F-e63ce880): `_called_name`,
# `_is_gate_call` and `_cli_body` used to be duplicated byte-for-byte between this file and
# `tests/test_canon_spend.py` (identical 1901-character AST dumps), and only this copy
# applied the mutually-exclusive-branch correction — so the two files reported different
# write lines on `encode_control`, `measure_cascade_clip` and `rig_character` while each
# docstring claimed to compute the other's answer.
_called_name = CN.called_name
_cli_body = CN.cli_body
_returning_branch_spans = CN.returning_branch_spans


def _is_gate_call(name):
    """The NAME half of the predicate. Kept, and no longer the whole of it."""
    return CN.is_refusal_call(name, CANON_CALLS, OTHER_GATE_CALLS)


def gate_and_write_lines(src, what, *, by_name_only=False):
    """`({line: refusal}, {line: write kind})` for the tool's CLI body, or `(None, None)`.

    THE NODE, since wave 12 (F-183635ad): a refusal is any `raise` of an `ArmatureError`
    subclass — inline in the CLI body, or one hop through a module-local helper that raises
    one — UNIONED with the named gate calls above. The predicate this file shipped
    recognised a refusal only by CALLEE NAME, and an inline `raise` is not a call: measured
    on this tree, 18 tools strand one below their first write and 9 of them never entered
    `derive_population()` at all, because that function keeps a module only when
    `gates_at and writes_at`. `make_rig_sheet.main` creates `<out>/` and `<out>/panels/`
    and then raises `ArmatureError` inline three times below them; the census reported
    nothing about it, and `tests/test_instruments_amend_w10.stranded_refusals` — which
    imports this function precisely "so the two files cannot disagree about what a refusal
    is" — inherited the blindness and returned `[]` for every tool.

    `by_name_only=True` restores the pre-wave-12 predicate, so the red proof below can show
    in one test that the old walk cannot see the shape the new one reports.
    """
    return CN.refusal_and_write_lines(
        src, error_names=ERROR_NAMES, canon_calls=CANON_CALLS,
        other_gate_calls=OTHER_GATE_CALLS, by_name_only=by_name_only)


def _source(name):
    return CN.read_source(name)


def derive_population():
    """Every `tools/*.py` whose CLI body both refuses and writes — walked, never typed."""
    out = {}
    for path in CN.tool_paths():
        name = os.path.basename(path)[:-3]
        gates_at, writes_at = gate_and_write_lines(CN.read_source(name), name)
        if gates_at and writes_at:
            out[name] = (gates_at, writes_at)
    return out


#: WAVE 26, F-12aacdc4 — the tools whose CLI body reaches disk through a module-local helper
#: that ALSO refuses, so the one-hop write is deliberately not recorded and no ordering
#: verdict is issued. MEASURED on `81d6c07`; an equality, so a third tool in this shape lands
#: here loudly instead of sitting outside every category the way `stage_render` did.
HELPER_BOTH_REFUSES_AND_WRITES = {
    # WAVE 34: `post_prompt` writes the curl body and raises; `build_control_pack` writes
    # the control receipt and raises. Both join the residue the one-hop write deliberately
    # does not record — measured after the submitter / encode_control --run landings.
    # WAVE 37: `merge_spend_into_record` joins on submit (reads/refuses then writes spend);
    # `write_diff_sheet` joins on compare_runs (--sheet); `from_motion_pipeline` joins on
    # pack_pose_pack (--from-motion). Measured; named exemptions, not product rollback.
    "build_submit_payload": ["merge_spend_into_record", "post_prompt"],
    "compare_runs": ["write_diff_sheet"],
    "encode_control": ["build_control_pack"],
    # WAVE 35: `run_dailies` / `sheet_main` both refuse and write; make_sheet and
    # measure_floor still gate-and-write directly elsewhere, so they stay in the
    # ordering population too (same shape as rig_character / export_rigged).
    "make_sheet": ["run_dailies"],
    "measure_floor": ["sheet_main"],
    "pack_pose_pack": ["from_motion_pipeline"],
    # `export_rigged` writes the GLB and raises the family; `rig_character` is in the ordering
    # population anyway, because its CLI body also writes directly (`os.makedirs` at :1691).
    "rig_character": ["export_rigged"],
    # `run_export` does `os.makedirs(out_dir)`, writes `.armature_run` and writes
    # `manifest.json`, and raises. `stage_render` has NO write its CLI body performs itself,
    # so before this wave it had `gates_at` and an EMPTY `writes_at` and `derive_population()`
    # — which keeps a module only when `gates_at and writes_at` — left it out of the census
    # entirely. It is the tool that creates the run directory every downstream payload
    # consumes, and the one `_census_nodes.documents_blender_invocation` was written to reach.
    "stage_render": ["run_export"],
}


def test_the_helper_that_both_refuses_and_writes_population_is_derived_and_named():
    """The residue of the one-hop widening, asserted rather than silent (F-12aacdc4).

    Before this wave the write half of the ratchet stopped at the CLI body while the refusal
    half followed one hop, so a tool whose first byte to disk went through a helper had zero
    visible writes and fell out of `derive_population()`. The hop is followed now; these two
    are what remains, because a helper that ALSO refuses is claimed by the refusal branch —
    see `_census_nodes.helpers_that_refuse_and_write` for the measurement that made that the
    right call rather than the convenient one.
    """
    import ast

    derived = {}
    for path in CN.tool_paths():
        name = os.path.basename(path)[:-3]
        hits = CN.helpers_that_refuse_and_write(ast.parse(CN.read_source(name)))
        if hits:
            derived[name] = sorted(hits)
    assert derived == HELPER_BOTH_REFUSES_AND_WRITES, {
        "appeared": sorted(set(derived) - set(HELPER_BOTH_REFUSES_AND_WRITES)),
        "vanished": sorted(set(HELPER_BOTH_REFUSES_AND_WRITES) - set(derived)),
        "derived": derived,
    }


def test_stage_render_reaches_disk_through_a_helper_and_this_file_says_where():
    """The pointed case, named on the real tree rather than described.

    `stage_render` is not in `POPULATION_MEASURED_2026_09_04` and the reason is now a fact
    this file asserts instead of an absence nobody could see: its CLI body performs no write
    of its own, and `run_export` — which it calls — creates the run directory, writes
    `.armature_run` and writes `manifest.json`.
    """
    import ast

    tree = ast.parse(CN.read_source("stage_render"))
    hits = CN.helpers_that_refuse_and_write(tree)
    assert sorted(hits) == ["run_export"], hits

    gates_at, writes_at = gate_and_write_lines(CN.read_source("stage_render"), "stage_render")
    assert gates_at, "stage_render's CLI body refuses somewhere; if not, this file is stale"
    assert writes_at == {}, (
        "stage_render's CLI body now writes directly; it should be in "
        "POPULATION_MEASURED_2026_09_04 and this test replaced by the ordering property")
    assert "stage_render" not in POPULATION_MEASURED_2026_09_04

    assert "run_export" in CN.functions_that_write(tree), (
        "run_export stopped writing; then the whole reason stage_render sits outside the "
        "ordering population has changed and this file must be re-derived")


def test_the_one_hop_write_predicate_is_strict_about_copy_and_replace():
    """The red proof for the hop, driving `_census_nodes.functions_that_write` itself.

    `WRITE_CALLS` is keyed on the callee TAIL, and `copy`, `copy2`, `rename`, `replace` and
    `save` are also ordinary method names. Measured on `81d6c07`: following the hop with the
    tail-keyed predicate admitted five helpers that never touch disk — `make_e08_sheet.label`
    (an image `.copy()`), `make_parts_sheet.corner_bounds`, `measure_cascade_clip.
    ffprobe_stream` (a `str.replace()`), `rig_parts.observe_under_pose` and
    `rig_retopo._duplicate` — and each moved its tool's first-write line hundreds of lines
    earlier, taking the ratchet's numbers with it for a reason that had nothing to do with
    bytes reaching disk.
    """
    import ast

    decoy = "\n".join([
        "def a(x):",
        "    return x.copy()",
        "def b(s):",
        "    return s.replace('a', 'b')",
        "def c(obj):",
        "    return obj.save()",
        "def d(src, dst):",
        "    return shutil.copy(src, dst)",
        "def e(path):",
        "    os.makedirs(path)",
        "def f(path):",
        "    with open(path, 'w') as fh:",
        "        fh.write('x')",
        "def g(path):",
        "    with open(path) as fh:",
        "        return fh.read()",
        "",
    ])
    assert CN.functions_that_write(ast.parse(decoy)) == {"d", "e", "f"}, \
        CN.functions_that_write(ast.parse(decoy))


def imports_bpy(name):
    """The module reaches Blender — a Blender tool renders into its own out dir.

    Keyed on BEHAVIOUR since wave 12 (F-6b3040d1), not on the literal token `import bpy`:
    `stage_render` reaches Blender through a lazily-instantiated backend and documents
    `blender -b -P tools/stage_render.py`, and a population keyed on the token could not
    see it. The name is kept because every caller reads it as the question "is this a
    Blender tool".
    """
    return bool(CN.blender_reach(CN.read_source(name)))


#: Measured 2026-09-04 by `derive_population()` on this tree, under the BEHAVIOURAL refusal
#: predicate (wave 12, F-183635ad). Asserted, so a tool that starts gating-and-writing joins
#: this file loudly rather than slipping past it.
#:
#: 39 members under the name-keyed predicate, 62 under this one. The 23 that JOINED are the
#: measurement of the finding: every one of them refuses — by an inline `raise` of an
#: `ArmatureError` subclass, or through a module-local helper whose name carries no
#: `gate_`/`require_` prefix — and writes, and none of them was examined by anything.
#: `make_rig_sheet` is the pointed one: it creates `<out>/` and `<out>/panels/` and then
#: raises `ArmatureError` inline at three lines below them.
POPULATION_MEASURED_2026_09_04 = {
    # WAVE 26 (tests, F-12aacdc4): 69 -> 70, RE-DERIVED with `==` on `81d6c07`. ONE joins,
    # `encode_control`, and it is the measurement of that finding: the write half of the
    # ratchet now follows the SAME one hop into a module-local helper that the refusal half
    # has followed since wave 12 (`_census_nodes.functions_that_write`). `encode_control`'s
    # CLI body performs no write of its own outside its returning `--survey` branch; it calls
    # `build(...)`, whose body writes the receipt, so it had `gates_at` and an EMPTY
    # `writes_at` and `derive_population()` — which keeps a module only when
    # `gates_at and writes_at` — left it out. It orders correctly today: its refusals are at
    # 537, 561 and 563 and the hop is at 564.
    #
    # `stage_render` does NOT join, and that is deliberate rather than an oversight: its
    # helper `run_export` BOTH refuses and writes, so the refusal branch claims the call line
    # first. `HELPER_BOTH_REFUSES_AND_WRITES` above names it, with the measurement, so it is
    # asserted by a test instead of sitting outside every category.
    #
    # The three ratchet pins are UNMOVED by the widening — re-derived with this file's own
    # command on the branch that widened it: 27 modules / 55 names / 78 sites, the same three
    # numbers. The population is a floor by construction, and the one tool that joined orders
    # correctly, so nothing is stranded that was not stranded before.
    # WAVE 25 (instruments-measure, F-c66ad0c4): FOUR JOIN, and they are the measurement of
    # that finding. `analyze_p3`, `make_cast_sheet`, `make_hole_survey` and
    # `rig_sheet_compose` were the modules in that domain with NO refusal of their own —
    # zero `raise` statements between them by AST walk on `580af47` — so they only WROTE and
    # `derive_population()` could not reach them. Each now refuses by name with evidence, so
    # each gates-and-writes and joins here loudly, which is this census doing its job.
    #
    # None of the four strands a refusal: `make_cast_sheet`'s three clauses and
    # `rig_sheet_compose`'s four sit in `main`/`gate_spec` above the single `os.makedirs`
    # beside `sheet.save`; `analyze_p3`'s two are inside `analyze()`, above the `--out`
    # write; `make_hole_survey`'s per-view existence clause was MOVED above its
    # `os.makedirs(panels_dir)` when this ratchet reported it stranded — the census caught
    # a real ordering defect in the fix that created it, which is the direction it exists
    # for, and the fix is better for it (a run refused at view 5 no longer leaves four
    # pairs of written panels behind).
    "analyze_p3", "make_cast_sheet", "make_hole_survey", "rig_sheet_compose",
    # WAVE 16 (instruments-measure, SEAM 14 §1): `make_e13_sheet` JOINS. It had NO typed
    # refusal at all — it only wrote — and now refuses (`E13SheetError`, their `F-9297b54f`,
    # the listing checked before it is indexed), so `derive_population()` reaches it. It
    # strands NOTHING: its `os.makedirs` moved from the top of `main` to immediately above
    # `sheet.save`, so the new refusal sits above the first write and the 27 / 51 / 69
    # ratchet is unchanged in all three numbers. RED ON THE tests BRANCH ALONE — the tool
    # is unchanged in this worktree, so `derive_population()` does not return it here.
    "make_e13_sheet",
    # WAVE-12 MERGE (coordinator, 2026-09-04): `make_overlay_sheet` JOINED — its `cv2.imwrite` return is a typed
    # refusal now (instruments-measure), so it gates-and-writes.
    "make_overlay_sheet",
    "author_walk", "build_animate_payload", "build_assembly_payload",
    "build_camera_i2v_payload", "build_cascade_payload", "build_i2v_payload",
    "build_lora_arm_payload", "build_payload", "build_r2v_payload",
    # WAVE 34: submitter + uploads-map author join — both gate-and-write.
    "build_submit_payload", "build_t2v_payload", "build_uploads_payload",
    # JOINED 2026-09-04 by the instruments wave-10 amend (F-6ee68fc0): `check_relift.main`
    # now calls `gate_relift_window` over each GLB's own keyed action range, so it
    # gates-and-writes where before it only wrote. Its makedirs already sits one line above
    # the record it writes, so nothing is stranded.
    "check_relift",
    "composite_reference", "fetch_t2v_run", "fit_reference", "gate_b_frames",
    "gate_saved_graph", "lift_clip", "lift_solve", "make_ab_clip", "make_crop_strip",
    "make_gate0_sheet", "make_identity_sheet", "make_lift_sheet", "make_pick_sheet",
    "make_plate", "make_review_clip",
    # WAVE 35: dailies sheet author joins — gates-and-writes (and also HELPER_BOTH via
    # `run_dailies`).
    "make_sheet",
    "make_skeleton_sheet", "make_startframe_sheet",
    # JOINED 2026-09-04 by the instruments wave-10 amend (F-13bd448d): `preview_glb.main`
    # now calls `gate_previews_written` over the four paths its renders returned, so it
    # gates-and-writes where before it only wrote. It is a `bpy` tool and lands in the
    # first exempt class; the ordering itself is pinned by
    # `tests/test_instruments_amend_w10.py::
    # test_no_refusal_sits_between_the_output_directory_and_the_first_byte`, which measures
    # the reason rather than the `imports_bpy` proxy.
    "preview_glb",
    # JOINED 2026-09-04 by the instruments-measure wave-14 amend (F-6a18f6d5):
    # `resample_motion.main` now raises `ResampleArgError` inline when `--frames` is below
    # 2 (`positions` and `sample_interval_ratio` both divide by `n_dst - 1`, so `--frames=1`
    # died with a bare ZeroDivisionError). It ALWAYS wrote; its four andons —
    # `lift_solve.validate_motion_record` twice, `resample.monotonic`,
    # `resample.endpoints_match` — are cross-module helpers this walk does not resolve, so
    # `gate_and_write_lines` reported `gates: {}` for it and the tool sat outside the census
    # entirely while its `makedirs` sat ABOVE all four. Both halves are fixed in the same
    # commit: the refusal is visible here, and the `makedirs` moved below every andon, so
    # the tool joins CLEAN (no refusal below its first write).
    "resample_motion",
    "make_thesis_sheet", "measure_floor", "measure_lift",
    "pack_pose_pack", "project_pose_keypoints", "render_performer", "render_pose_sticks",
    "render_start_frame", "render_turnaround", "rig_character", "rig_parts",
    # ---------------------------------------------------------------------------------
    # JOINED 2026-09-04 (wave 12, F-183635ad) when the predicate stopped keying on the
    # callee's SPELLING. Each of these refuses somewhere the name-keyed walk could not
    # look; none of them is new code.
    "compare_runs", "diagnose_bone_heat", "extract_clip_frames", "fetch_run",
    "make_binding_sheet", "make_e08_sheet", "make_parts_sheet", "make_rig_sheet",
    "make_shotset_sheet", "make_test_armature", "make_zoom_sheet", "measure_arm",
    "measure_cascade_clip", "measure_clip", "measure_smoothness", "measure_tracking",
    "preview_walk", "probe_glb", "probe_subject", "rig_bake", "rig_repair", "rig_retopo",
    # WAVE 26, F-12aacdc4 — the one-hop write half; see the note at the top of this table.
    "encode_control",
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
    excuse: `encode_control.main`'s DIRECT write is inside its returning `--survey` branch and
    is dropped, while a write in a branch that FALLS THROUGH is still counted.

    WAVE 26, F-12aacdc4 — this used to assert `writes_at == {}` for `encode_control`, which
    was true only because the write half of the ratchet stopped at the CLI body. It follows
    one hop now, the same hop the refusal half has always followed, so `build(...)` — whose
    body writes the receipt — is a write at its CALL line. The `--survey` correction is still
    the thing under test and is still exercised: the direct write inside the returning branch
    is absent from `writes_at`, and the only entry is the hop.
    """
    gates_at, writes_at = gate_and_write_lines(_source("encode_control"), "encode_control")
    assert gates_at, "encode_control.main runs no in-tool refusal"
    assert sorted(writes_at.values()) == ["build()"], writes_at
    survey_spans = CN.returning_branch_spans(CN.cli_body(ast.parse(_source("encode_control"))))
    assert survey_spans, "encode_control.main has no returning branch; the correction is unexercised"
    inside = [ln for ln in writes_at if any(lo <= ln <= hi for lo, hi in survey_spans)]
    assert inside == [], (
        f"a write inside a returning branch survived the correction: {inside}; it is on a "
        f"path that never reaches the code below it")

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


# ------------------------------- the exemption, keyed on the REFUSAL rather than the module
#
# WAVE 10, F-82e87ccc. The stated reason for the bpy exemption is narrow — "the tool writes
# the artefact that its later gates then measure, so the directory must exist before the
# gate can run" — and the check was `if imports_bpy(name): pytest.skip(...)`, which excuses
# EVERY refusal in the module rather than the ones that measure a rendered artefact. That is
# the proxy-instead-of-reason shape: `imports bpy` is a property of the MODULE; "measures
# what it wrote" is a property of the REFUSAL. So the module-wide skip became a per-refusal
# RATCHET.
#
# WAVE 12, F-183635ad. The ratchet was right and its INPUT was blind. Under the behavioural
# predicate the ratchet is no longer a bpy-only list — a CPython instrument strands a
# refusal exactly the same way, and five of them do — so it is renamed for what it holds and
# re-measured: 25 tools, 62 distinct refusal names, 87 sites, on 2026-09-04.
#
# **Direction of the assertion, and why it is not equality this wave.** The set may not
# GROW: a new stranded refusal — under a tool already listed or a tool not listed — fails
# loudly, naming the tool and the refusal. It is expected to SHRINK while wave 12 is in
# flight: `instruments` and `instruments-measure` own the moves (the coordinator brief
# routes "the 18 stranded refusals moved above the first write" to instruments), and each
# entry names the domain that owns it below. An entry closed by such a move is DELETED in
# the commit that moves it — that is the ratchet's other half, and it is administered at
# merge rather than here, because a sibling landing its half in a parallel worktree must not
# fail this file. Equality returns the moment the moves have landed; the growth direction —
# the one that protects the property — is asserted today.
REFUSALS_BELOW_THE_FIRST_WRITE = {
    # WAVE-14 MERGE (coordinator, 2026-09-04): `make_rig_sheet`, `make_skeleton_sheet` (instruments, the two true strands) and
    # `make_shotset_sheet` (instruments-measure) strand NOTHING on the merged tree — entries deleted, not
    # edited; `gate_ink` MOVED above the write in `render_pose_sticks` (instruments-measure) and is not a
    # read-back, so it leaves this table and enters nothing. SEAM 13 + SEAM 15.
    # WAVE-12 MERGE (coordinator, 2026-09-04): RE-DERIVED on the merged tree with this file's own
    # behavioural walk after the moves landed (instruments moved eleven tools' refusals above
    # `makedirs` — F-244b2ad5; the coordinator moved `render_pose_sticks` and `pack_pose_pack`).
    # CORRECTED 2026-09-04 (wave 14, F-385f2b60) by re-reading the table this line pointed
    # at. The claim was "every entry that remains is a refusal that READS BACK the write it
    # sits below"; measured, 34 of the 47 names carried the placeholder reason
    # "REVIEW: not a read-back". Twelve names are read-backs (`READBACK_REASONS`, each with
    # the call token a test finds in the source); thirty-five are a dated BACKLOG
    # (`NOT_YET_MOVED`) whose size is pinned, not a design decision.
    "author_walk": ["gate_a_arrival", "gate_arrived", "gate_glb_written", "gate_n_names",
                    "pick_subject"],
    # WAVE 37: submit merges spend onto --record after append_ledger; compare_runs'
    # --sheet helper both refuses and writes. Named exemptions (per-refusal ratchet).
    "build_submit_payload": ["merge_spend_into_record"],
    "compare_runs": ["write_diff_sheet"],
    "extract_clip_frames": ["probe", "raise ClipReadError"],
    "fetch_run": ["download", "verify_downloads"],
    # WAVE-14 MERGE (coordinator, 2026-09-04): `download` LEFT — `fetch_t2v_run.download` is now a call into
    # `fetch_run.download` (builders, F-a3ba416b: one downloader across both fetchers); measured.
    "fetch_t2v_run": ["gate_order_evidence", "order_evidence"],
    "fit_reference": ["raise FitReferenceError"],
    # WAVE 34 retarget: motion_out is written before the shared gate/author/export path, so
    # `author` / `gate_objects_registered` / `gate_space_is_identity` join the stranded set
    # (re-measured; not moved above the new first write in this pin-fix).
    "lift_solve": ["author", "gate_arrived", "gate_glb_written", "gate_n_names",
                   "gate_objects_registered", "gate_space_is_identity", "pick_subject"],
    "make_binding_sheet": ["render_arm"],
    "make_e08_sheet": ["raise SheetInputError"],
    "make_lift_sheet": ["subject_box"],
    "make_overlay_sheet": ["raise OverlaySheetError"],
    "make_parts_sheet": ["shoot"],
    # WAVE 22 (instruments-measure, F-e40749e9): the token changed, not the position.
    # `make_plate` raised the family BASE at eleven sites; all eleven now raise its own
    # `PlateError` with a clause, so the one refusal that still sits below a write is
    # spelled `raise PlateError`. The `--visible-rows` refusal that used to sit here too
    # MOVED above `os.makedirs` in the same commit and leaves this table entirely.
    "make_plate": ["raise PlateError"],
    "make_test_armature": ["gate_glb_written"],
    "make_zoom_sheet": ["raise ZoomSheetError"],
    "measure_cascade_clip": ["raise ClipCountError"],
    "pack_pose_pack": ["gate_r_round_trip"],
    "preview_glb": ["gate_previews_written"],
    # WAVE 22 (instruments, F-a2630f86): `require_render_target_moved` joins four
    # renderers. It is a genuine READ-BACK -- it `os.stat`s the frame the render just
    # wrote and compares it against the snapshot taken above the write -- so it belongs
    # below the write by construction and is entered in `READBACK_REASONS`, not in the
    # backlog. `preview_glb` reaches the same call inside `gate_previews_written`, which
    # is already listed.
    "preview_walk": ["raise PreviewWalkGate", "require_render_target_moved"],
    "render_performer": ["gate_coverage", "raise RenderGate",
                         "require_render_target_moved"],
    "render_pose_sticks": ["raise SticksGate"],
    # WAVE 34: `require_render_target_moved` LEFT — the nested `_render_still` helper
    # now takes the snapshot+require around the single write_still site, so the
    # call no longer sits below a first write the walk attributes to this module's
    # other paths. Measured; entry deleted, not commented.
    "render_start_frame": ["gate_alpha", "gate_backdrop", "raise RenderGate"],
    "render_turnaround": ["gate_set_distinct", "gate_view_alpha", "gate_view_crop", "gate_whole", "raise RenderTurnaroundGate",
                          "require_render_target_moved"],
    "rig_bake": ["gate_glb_written"],
    "rig_character": ["build_pass", "export_rigged", "gate_d_determinism", "gate_n_names", "raise GateMode", "unbound_determinism_record"],
    # WAVE 25 (instruments, F-19d4e0f7): `require_import_status` joins, and it is a
    # genuine READ-BACK -- `rig_parts.main` re-imports the parts GLB it just exported
    # so Gate PART NAMES can read the names a consumer would actually get, and the
    # refusal is on THAT import's operator status. It belongs below the write by
    # construction, so it is entered in `READBACK_REASONS` rather than in the backlog.
    # The tool's OTHER import (`build_pass`) sits above every write and does not
    # appear here, which is the measurement that says this entry is the readback one.
    "rig_parts": ["gate_atlas_untouched", "gate_glb_written", "gate_part_names",
                  "require_import_status"],
    "rig_repair": ["gate_glb_written"],
    "rig_retopo": ["gate_glb_written"],
}

# --------------------------------------------------------------- the read-back table, split
#
# WAVE 14, F-385f2b60. The constant below used to hold all 47 names under the comment above
# `REFUSALS_BELOW_THE_FIRST_WRITE` \u2014 "Every entry that remains is a refusal that READS BACK
# the write it sits below" \u2014 and 34 of its 47 values were the literal string
# `"REVIEW: not a read-back \u2014 a strand the coordinator did not move"`. So the file's central
# exemption documented itself as principled while, for 34 names, self-declaring as
# unfinished work; and nothing read the table at all (a grep for `READBACK_REASONS` returned
# the prose and the definition, and no assertion). A reader \u2014 or a later wave \u2014 took 30
# tools' stranded refusals as accepted by design rather than as a routed backlog, and the
# moves stopped being made.
#
# The two things are now two tables and BOTH are read by
# `test_the_read_back_table_is_read_and_says_what_it_means`:
#
# * `READBACK_REASONS` \u2014 the genuine read-backs. Each value names the CALL that performs the
#   read-back, and the test asserts that call token appears in the source of every tool that
#   lists the name. A reason a test can check, not prose.
# * `NOT_YET_MOVED` \u2014 the backlog, dated, with an owner DERIVED per name (never typed) from
#   the run's own domain split. Its size is pinned `==`, so the count of unmoved strands is
#   visible on the page and falls only when a commit moves one and deletes its entry.
#
# CORRECTED IN PLACE by the measurement that overturned it (wave 13): `gate_ink` was listed
# here as "ink fraction measured over the frames just written" and it is not \u2014 it measures
# the IN-MEMORY canvas, one operand short of the frames on disk. It has moved to the backlog
# with its route (`render_pose_sticks:202`, instruments-measure F-5f2a7452). The claim was
# checkable and unchecked for two waves, which is what an unread table is worth.

#: The genuine read-backs: `name -> (read-back call token, why)`. The token must appear in
#: the source of EVERY tool whose entry in `REFUSALS_BELOW_THE_FIRST_WRITE` names it \u2014 that
#: is the half a test can check, and it is checked below.
READBACK_REASONS = {
    "download": ("download",
                 "the fetcher's write IS the download; the refusal reads back what arrived"),
    "gate_glb_written": ("gate_glb_written",
                         "reads back the GLB the export just wrote (instruments F-9b2d4106)"),
    "gate_order_evidence": ("gate_order_evidence",
                            "reads back the downloaded manifest (fetch_t2v_run)"),
    "gate_previews_written": ("gate_previews_written",
                              "reads back the four renders (F-13bd448d)"),
    "gate_r_round_trip": ("read_pack",
                          "Gate R re-decodes, with `read_pack(dst)`, the pack this tool wrote"),
    "order_evidence": ("order_evidence",
                       "reads back the downloaded manifest (fetch_t2v_run)"),
    "raise OverlaySheetError": ("imwrite", "the refusal IS the `cv2.imwrite` return"),
    "raise SheetInputError": ("imwrite",
                              "the refusal IS the `cv2.imwrite` return \u2014 it verifies the "
                              "write it just made"),
    "raise SticksGate": ("imwrite",
                         "the refusal IS the `cv2.imwrite` return for the frame just drawn"),
    "require_import_status": (
        "require_import_status",
        "reads back the GLB the export just wrote -- `rig_parts.main` re-imports it so "
        "Gate PART NAMES can read the names a consumer would get, and this refusal is "
        "on that import's operator status set (instruments F-19d4e0f7); it is the "
        "import half of `gate_glb_written`'s family"),
    "require_render_target_moved": (
        "require_render_target_moved",
        "reads back the frame the render just wrote -- `os.stat` against the "
        "`render_target_snapshot` taken above the write (instruments F-a2630f86); it is "
        "the render half of `gate_glb_written`'s clause 4"),
    "raise ZoomSheetError": ("imwrite",
                             "the refusal IS the `cv2.imwrite` return / the sidecar of a "
                             "written sheet"),
    "verify_downloads": ("verify_downloads", "reads back what it downloaded (fetch_run)"),
}

#: THE BACKLOG, named and dated 2026-09-04 (wave 14, F-385f2b60). Refusals that sit below a
#: first write and are NOT read-backs: a run refused at one of these leaves an output
#: directory behind that reads as an attempt that produced nothing. Each is a move somebody
#: owns; the owner is derived by `owning_domain()` below from the file the name sits in, so
#: an entry cannot claim a domain that does not own its tool.
#:
#: **This set may only SHRINK.** Its size is pinned `==` beside the ratchet, so a move that
#: lands deletes its entry in the same commit and the number on the page falls with it.
#: Re-derive with the suite interpreter (tests/conftest.py module docstring):
#:     .venv/Scripts/python.exe -c "import sys;sys.path[:0]=['tests','tools'];\
#:     import test_instrument_write_ordering as M;\
#:     print(len(M.NOT_YET_MOVED))"
NOT_YET_MOVED = {
    # WAVE-14 MERGE (coordinator, 2026-09-04): six names left — the four `make_shotset_sheet` / `make_rig_sheet` / `make_skeleton_sheet`
    # strands moved above their writes (instruments, instruments-measure) and `gate_ink` moved (instruments-measure).
    "author": "lift_solve authors the action after retarget already wrote motion_out (wave 34)",
    "build_pass": "rig_character's build pass refuses below the measure branch's makedirs (wave 13 read this family as an artefact of the walk's mutually-exclusive-branch handling; the walk is the operand, not the reason)",
    "export_rigged": "rig_character, same family as `build_pass`",
    "gate_a_arrival": "author_walk stages the walk and refuses after the run directory exists",
    "gate_alpha": "render_start_frame refuses on alpha after the first frame's directory exists",
    "gate_arrived": "lift_solve / author_walk, the shape that refuses after the run directory exists",
    "gate_atlas_untouched": "rig_parts refuses on the atlas after the part GLBs are written",
    "gate_backdrop": "render_start_frame, same family as `gate_alpha`",
    "gate_coverage": "render_performer refuses on coverage after the render directory exists",
    "gate_d_determinism": "rig_character, same family as `build_pass`",
    "gate_n_names": "author_walk / lift_solve / rig_character",
    "gate_objects_registered": "lift_solve, below the retarget motion_out write (wave 34)",
    "gate_part_names": "rig_parts, same family as `gate_atlas_untouched`",
    "gate_set_distinct": "render_turnaround refuses on the view set after the out dir exists",
    "gate_space_is_identity": "lift_solve, below the retarget motion_out write (wave 34)",
    "gate_view_alpha": "render_turnaround, same family as `gate_set_distinct`",
    "gate_view_crop": "render_turnaround, same family as `gate_set_distinct`",
    "gate_whole": "render_turnaround, same family as `gate_set_distinct`",
    "pick_subject": "author_walk / lift_solve pick the subject after the run directory exists",
    "probe": "extract_clip_frames probes the clip after the frame directory exists",
    "raise PlateError": "make_plate's cv2 write-failure refusal reports the write it sits below (wave 22: the token was `raise ArmatureError` until the eleven base raises were named)",
    "raise ClipCountError": "measure_cascade_clip refuses on the clip count below its first write",
    "raise ClipReadError": "extract_clip_frames, same family as `probe`",
    "raise FitReferenceError": "fit_reference refuses inline below its first write",
    "raise GateMode": "rig_character, same family as `build_pass`",
    "merge_spend_into_record": (
        "build_submit_payload merges spend onto --record after append_ledger "
        "(wave 37); the read/refuse is of the builder record, not a read-back of the ledger"),
    "raise PreviewWalkGate": "preview_walk refuses inline below its first write",
    "raise RenderGate": "render_performer / render_start_frame",
    "raise RenderTurnaroundGate": "render_turnaround, same family as `gate_set_distinct`",
    "render_arm": "make_binding_sheet renders the arm after `<out>/` exists",
    "shoot": "make_parts_sheet shoots after `<out>/` exists",
    "subject_box": "make_lift_sheet takes the subject box after `<out>/` exists",
    "unbound_determinism_record": "rig_character, same family as `build_pass`",
    "write_diff_sheet": (
        "compare_runs --sheet helper refuses and writes below os.makedirs (wave 37)"),
}

#: The domains this run froze. An owner outside this set is a typo, and the test says so.
RUN_DOMAINS = {"builders", "ci-packaging", "core-gates", "core-solvers", "docs",
               "instruments", "instruments-measure", "tests"}


def owning_domain(tool):
    """Which domain owns `tools/<tool>.py`, by the run's OWN frozen split \u2014 derived.

    The run defines `instruments` as "every `tools/*.py` that imports bpy \u2026 re-globbed at
    the wave-4/5 boundary \u2026 the CPython half moved to instruments-measure", and the payload
    builders and fetchers are `builders`. So the owner of a stranded refusal is a fact about
    the file, not a field to be typed beside 35 entries and to rot beside them.
    """
    if imports_bpy(tool):
        return "instruments"
    if tool.startswith(("build_", "fetch_")) or tool == "gate_saved_graph":
        return "builders"
    return "instruments-measure"


def tools_naming(refusal):
    """Every tool whose entry in the ratchet names `refusal`."""
    return sorted(t for t, names in REFUSALS_BELOW_THE_FIRST_WRITE.items()
                  if refusal in names)


def owners_of(refusal):
    """The domains that must make the move for `refusal` \u2014 derived, never typed."""
    return sorted({owning_domain(t) for t in tools_naming(refusal)})


class ReadBackTableViolation(Exception):
    """One clause of the read-back table's contract, broken by the table it was handed."""


def read_back_table_violations(readback=None, not_yet_moved=None, *, ratchet=None,
                               source=None):
    """The two clauses of the exemption table's contract, over TABLES PASSED IN.

    WAVE 16, F-d18443ac. The red proof for F-385f2b60 re-implemented both clauses inline
    over literals it built itself, so it never touched the checker. Measured by driving
    both in process against the live table: with the exact placeholder the finding named
    (`"REVIEW: not a read-back \u2014 a strand the coordinator did not move"`) restored as
    `READBACK_REASONS['gate_r_round_trip']`'s reason, the real checker FAILED and the red
    proof still PASSED. A red proof that cannot go red is not a proof.

    So the clauses live here, taking their tables the way `stranded_by_tool` takes its
    `source` \u2014 the checker calls this on the module constants and the red proof calls the
    SAME function on a table carrying the placeholder. It RAISES rather than asserting,
    because `-O` deletes an `assert` in a helper under `tests/`
    (`test_gate_survives_optimize.py`), and this one decides whether a check ran at all.
    """
    readback = READBACK_REASONS if readback is None else readback
    not_yet_moved = NOT_YET_MOVED if not_yet_moved is None else not_yet_moved
    ratchet = REFUSALS_BELOW_THE_FIRST_WRITE if ratchet is None else ratchet
    read_source = _source if source is None else source.__getitem__

    def naming(refusal):
        return sorted(t for t, names in ratchet.items() if refusal in names)

    for refusal, (call, why) in sorted(readback.items()):
        if not call or not why or "REVIEW" in why:
            raise ReadBackTableViolation(
                f"{refusal!r} is excused as a read-back with reason {why!r} and call "
                f"{call!r}; an empty reason or a REVIEW placeholder is the self-declaring "
                f"exemption F-385f2b60 was paid to end")
        for tool in naming(refusal):
            if call not in read_source(tool):
                raise ReadBackTableViolation(
                    f"{refusal} is excused in {tool} as a read-back performed by {call!r}, "
                    f"and {call!r} does not appear in tools/{tool}.py; the reason names a "
                    f"call the tool does not make")

    for refusal, why in sorted(not_yet_moved.items()):
        if not why or "REVIEW" in why:
            raise ReadBackTableViolation(
                f"{refusal!r} sits in the backlog with reason {why!r}; a backlog entry that "
                f"declares nothing is the placeholder, not a reason")
    return True

#: The old name, kept as an alias for one wave so a sibling worktree importing it does not
#: break at merge. It is the same object; the list is no longer bpy-only.
REFUSALS_BELOW_THE_FIRST_WRITE_IN_A_BPY_TOOL = REFUSALS_BELOW_THE_FIRST_WRITE


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


def stranded_detail_by_tool(members=None, *, source=None):
    """Parallel map for the ratchet message (F-0d690499): first write named, not just 'it'.

    `{tool: {'first_write': (line, kind), 'refusals': [names],
             'refusal_sites': [(line, name), ...]}}`. `stranded_by_tool` keeps the
    `{tool: [names]}` shape the recorded table compares against; this carries the line and
    kind a seat needs to move a refusal above, or to tell a false alarm from a real strand.
    """
    source = source or {}
    members = sorted(derive_population()) if members is None else members
    out = {}
    for name in members:
        gates_at, writes_at = gate_and_write_lines(source.get(name, _source(name)), name)
        if not gates_at or not writes_at:
            continue
        first_ln = min(writes_at)
        sites = sorted((ln, gates_at[ln]) for ln in gates_at if ln > first_ln)
        if sites:
            out[name] = {
                "first_write": (first_ln, writes_at[first_ln]),
                "refusals": sorted({n for _, n in sites}),
                "refusal_sites": sites,
            }
    return out


def stranded_by_tool(members=None, *, source=None):
    """`{tool: [refusal names below its first write]}` over the WHOLE derived population.

    THE OPERAND (wave 14, rule 1; F-3a0d4576). This expression used to carry
    `and n not in GATES_READ_BACK_WHAT_THEY_WROTE` — a MODULE-wide filter administering a
    per-REFUSAL excuse — so the ratchet's one asserted property never looked at
    `pack_pose_pack`, `render_pose_sticks` or `fetch_t2v_run`: the three tools with the most
    refusals under a write, and the fetcher and the two writers whose run directories
    downstream payloads consume. Proven by mutation on this tree: a
    `gate_a_brand_new_refusal(x)` inserted one line below `pack_pose_pack`'s first write made
    `refusals_below_the_first_write('pack_pose_pack')` report it, and `grew` still evaluated
    to `{}`. The read-back excuse is a property of the REFUSAL and is administered per NAME
    in `READBACK_REASONS`, which is where a name-keyed excuse belongs; re-measured without
    the module filter, the derived table IS `REFUSALS_BELOW_THE_FIRST_WRITE` exactly, so the
    three tools' names were already individually listed and compare clean.

    `source` maps a tool name to replacement source text, so the red proof below drives THIS
    expression over a mutated tool rather than re-implementing it beside it.

    WAVE 29, F-0d690499: the first-write line and kind ride `stranded_detail_by_tool`; the
    failure message below names them so a seat is not told to move a refusal above an
    unnamed 'it'.
    """
    return {n: v["refusals"] for n, v in stranded_detail_by_tool(members, source=source).items()}


def _format_stranded_growth(detail, grew_names):
    """One sentence per tool: refusal line below the named first write (F-0d690499)."""
    out = {}
    for tool, names in grew_names.items():
        fw_ln, fw_kind = detail[tool]["first_write"]
        sites = [f"{n} at :{ln}" for ln, n in detail[tool]["refusal_sites"] if n in names]
        out[tool] = (
            f"{tool}: {', '.join(sites)} sit(s) below {fw_kind} at :{fw_ln} "
            f"(move them above that write, or add with the reason)"
        )
    return out


def _format_ordering_failure(name, gates_at, writes_at):
    """Line-sorted refusal/write table for the clean-tool ordering assert (F-ec3f261b)."""
    first_ln = min(writes_at)
    ordered = max(gates_at) < min(writes_at)
    rows = [
        f"{name}: first write {writes_at[first_ln]} at :{first_ln}",
        f"ordered max(gate)<min(write): {ordered}",
        "refusals:",
    ]
    for ln in sorted(gates_at):
        rows.append(f"  :{ln}  {gates_at[ln]}")
    rows.append("writes:")
    for ln in sorted(writes_at):
        rows.append(f"  :{ln}  {writes_at[ln]}")
    return "\n".join(rows)


def stranded_site_count(members=None, *, source=None):
    """SITES, not names: the same walk, counting every line rather than every spelling."""
    source = source or {}
    members = sorted(derive_population()) if members is None else members
    total = 0
    for name in members:
        gates_at, writes_at = gate_and_write_lines(source.get(name, _source(name)), name)
        if not gates_at or not writes_at:
            continue
        total += sum(1 for ln in gates_at if ln > min(writes_at))
    return total


def test_the_exemption_is_a_per_refusal_ratchet_and_not_a_module_wide_skip():
    """Size and membership before the property, over the FULL derived population.

    Every listed tool is checked to be a real member of the derived population, so an entry
    naming a tool that stopped gating-and-writing cannot sit here saying nothing.
    """
    members = sorted(derive_population())
    listed = sorted(REFUSALS_BELOW_THE_FIRST_WRITE)
    assert set(listed) <= set(members), sorted(set(listed) - set(members))
    detail = stranded_detail_by_tool(members)
    derived = {n: v["refusals"] for n, v in detail.items()}
    grew = {n: sorted(set(v) - set(REFUSALS_BELOW_THE_FIRST_WRITE.get(n, [])))
            for n, v in derived.items()
            if set(v) - set(REFUSALS_BELOW_THE_FIRST_WRITE.get(n, []))}
    assert grew == {}, {
        "new refusals under a write (move them above the named first write, or add with the reason)":
            _format_stranded_growth(detail, grew)}
    # EQUALITY, both directions (wave 14, rule 4). The growth half above names the tool and
    # the refusal, which is the failure an author wants; this half catches the other
    # direction — an entry that has stopped naming a live strand, which is how a ratchet
    # stops ratcheting. A move that lands DELETES its entry in the same commit; a move
    # landed in a sibling worktree is reconciled once, at merge, by re-running the
    # derivation command below.
    assert derived == REFUSALS_BELOW_THE_FIRST_WRITE, {
        "stranded and not listed": {n: v for n, v in derived.items()
                                    if set(v) - set(REFUSALS_BELOW_THE_FIRST_WRITE.get(n, []))},
        "listed and no longer stranded (delete these in the commit that moved them)": {
            n: v for n, v in REFUSALS_BELOW_THE_FIRST_WRITE.items()
            if set(v) - set(derived.get(n, []))},
    }
    # Two numbers, because they count two different things: distinct refusal NAMES and
    # SITES, the gap being names that appear twice under one tool. The ratchet keys on
    # names; the site count is asserted beside it so a duplicate appearing is visible rather
    # than silently collapsed.
    #
    # RE-DERIVED 2026-09-04 (wave 14, F-4f2c2aea) and pinned `==`. They were ceilings reading
    # `names <= 62` and `sites <= 87` under a comment claiming "MEASURED 2026-09-04 …: 25
    # tools, 62 names, 87 sites" — three numbers, none of which any expression in this file
    # produced. Measured under the module filter the ceilings actually used: 27 tools, 51
    # names, 63 sites; the constant beneath the comment held 30 tools and 58 names. So the
    # ceilings carried 11 names and 24 sites of headroom and could no longer report that the
    # population had moved. The measurement that overturned the comment, on the full
    # population this test now walks: 30 tools, 58 names, 72 sites.
    #
    #     .venv/Scripts/python.exe -c "import sys;sys.path[:0]=['tests','tools'];\
    #     import test_instrument_write_ordering as M;\
    #     d=M.stranded_by_tool();print(len(d),sum(len(v) for v in d.values()),\
    #     M.stranded_site_count())"   # suite interpreter: tests/conftest.py
    # WAVE-14 MERGE (coordinator, 2026-09-04): 30 / 58 / 72 → 27 / 51 / 69, MEASURED on the merged tree (never subtracted).
    # WAVE 22 (builders, 2026-09-05): 27 / 51 / 69 → 27 / 50 / 68, RE-DERIVED with `==` by
    # running the derivation above in `w22-builders` after reading 27/51/69 GREEN there
    # first. One name and one site leave: `fetch_t2v_run`'s `raise FetchHalt` for
    # `zero_length_frames` (F-c03a23c5) — a clause that COULD NOT FIRE.
    # `verify_downloads(jobs, directories=[...], root=a.out)` above it already raises when
    # any planned output is zero length, across the frame jobs AND the video job, and
    # `manifest` is a strict subset of the same planned frames read from the same paths.
    # RE-MEASURED by calling `fetch_run.verify_downloads` directly on a single planned
    # zero-byte `lossless/00000.png`: it raised `FetchHalt` with clause
    # `downloaded_population_is_not_the_planned_one` before any manifest existed. Its
    # entries in `STRANDED_TODAY` and in the read-back reason table go with it, per this
    # file's own instruction to delete a listing in the commit that moved it.
    #      ⚠ **BRANCH-LOCAL.** Other domains move this census in the same wave; the
    #      coordinator MEASURES it on the merged tree and never subtracts.
    # RE-DERIVED wave 22 (instruments, F-a2630f86), branch-local: 27 / 51 / 69 →
    # 27 / 55 / 79, MEASURED with the command above on this branch, never summed. The
    # four new names are `require_render_target_moved` on `preview_walk`,
    # `render_performer`, `render_start_frame` and `render_turnaround`; the ten new
    # SITES are its call sites (one per `bpy.ops.render.render(write_still=True)` — six
    # in `render_start_frame`, two in `render_performer`, one each in the other two).
    # It is a READ-BACK by construction: it `os.stat`s the frame the render just wrote
    # against the snapshot taken above the write, so it CANNOT be moved above the write
    # and it is entered in `READBACK_REASONS` rather than in the backlog. The number
    # rising here is the population growing, not a move being missed.
    # WAVE-22 MERGE (coordinator, 2026-09-05): 27 / 54 / 78 MEASURED on the merged tree with the derivation above —
    # builders (27 / 50 / 68) and instruments (27 / 55 / 79) each moved this census branch-local; the merged value
    # is neither and is not their sum.
    # WAVE 37: 27 -> 29. build_submit_payload (merge_spend_into_record) and compare_runs
    # (write_diff_sheet) join; measured after --write-record / --sheet landings.
    assert len(derived) == 29, (
        f"{len(derived)} tools strand a refusal below their first write; this pin asserts 29 "
        f"(one unit = one tool in derive_population() that still strands). Re-derive with the "
        f"suite interpreter named in tests/conftest.py via the command in the comment block "
        f"above (tools/names/sites). Record the wave that moved it BRANCH-LOCAL, never summed. "
        f"Members: {sorted(derived)}")
    names = sum(len(v) for v in derived.values())
    # WAVE 25 (instruments, F-19d4e0f7): 54 -> 55, BRANCH-LOCAL and MEASURED. ONE name,
    # `require_import_status` in `rig_parts` -- the re-import whose names Gate PART
    # NAMES reads, below the export it reads back. It is a READ-BACK, so it enters
    # `READBACK_REASONS` and NOT the `NOT_YET_MOVED` backlog, whose size is unchanged.
    # WAVE 34: 55 -> 58. author_walk gains `gate_arrived`; lift_solve gains `author` /
    # `gate_objects_registered` / `gate_space_is_identity` below the new retarget
    # motion_out write; render_start_frame loses `require_render_target_moved` (-1).
    # WAVE 37: 58 -> 60. merge_spend_into_record + write_diff_sheet join.
    assert names == 60, (
        f"{names} distinct stranded refusal NAMES; this pin asserts 60 (one unit = one "
        f"refusal spelling under a tool, collapsed per tool). Re-derive with the suite "
        f"interpreter named in tests/conftest.py via the command in the comment block above. "
        f"Record the wave that moved it BRANCH-LOCAL, never summed. Dump: {sorted(derived.items())}")
    sites = stranded_site_count(members)
    # WAVE 16, F-9b4d01ef: the message used to name 72 — the tests branch's own measurement,
    # which the wave-14 merge overturned when it re-derived 27/51/69 on the merged tree and
    # updated the constants, the `==` targets and the comment above but not this f-string.
    # A seat landing a move read "N sites; 72 were measured" beside an assertion demanding
    # 69 and had every reason to retype the wrong number. The message quotes the value it
    # ASSERTS; the overturned measurement stays in the comment above, where this file keeps
    # its corrections.

    # WAVE 22 (instruments-measure): 69 → 68, MEASURED in this worktree with the derivation
    # command above. `make_plate --visible-rows` MOVED above `os.makedirs`: the flag was
    # parsed and range-checked below both the directory and the `plate.png` write, so a
    # refused run left the plate on disk with no provenance JSON beside it. One site, one
    # direction, and the number falls — which is what this pin is for. `len(derived)` and
    # `names` are unchanged at 27 / 51 because `make_plate`'s OTHER stranded refusal (the
    # `cv2.imwrite` failure, which reports the write it sits below) keeps the module and its
    # one name in the table; only its TOKEN changed, from `raise ArmatureError` to
    # `raise PlateError`, re-derived in `NOT_YET_MOVED` and `READBACK_REASONS` above.
    # ⚠ BRANCH-LOCAL — four sibling domains move this pin in the same wave.
    # WAVE 25 (instruments, F-19d4e0f7): 77 -> 78, BRANCH-LOCAL and MEASURED. ONE site,
    # `rig_parts`' `require_import_status` on the re-import Gate PART NAMES reads --
    # a READ-BACK of the export above it, so it enters `READBACK_REASONS` and the
    # `NOT_YET_MOVED` backlog is unchanged. The three sheets' new
    # `require_render_target_moved` calls add NO site: each sits inside a `shoot`
    # already counted through that name.
    # WAVE 34: 78 -> 72. The six `require_render_target_moved` sites inside
    # `render_start_frame`'s former inlined write_still calls leave when the nested
    # `_render_still` helper owns the snapshot+require pair; measured, never summed.
    # WAVE 37: 72 -> 75. submit merge_spend + compare_runs write_diff_sheet sites join;
    # pack_pose_pack's from_motion stick-drift raise MOVED above makedirs (sites fall
    # relative to an unmoved strand). Measured 29/60/75.
    assert sites == 75, (
        f"{sites} refusal SITES below a first write; this pin asserts 75, re-derived on the "
        f"merged tree after wave 37 submit/compare/pack landings "
        f"(see the comments above for the measurements it overturned), and the number "
        f"falls as the moves land")


def test_no_assertion_message_in_the_suite_quotes_a_ceiling_it_does_not_assert():
    """F-9b4d01ef, as the POPULATION rather than as the two f-strings that carried it.

    The defect is not "these two messages are stale" — it is that a failure message is the
    thing a seat reads when a ratchet fires, and nothing in the suite compared what a
    message CLAIMS was measured against what its own assertion demands. Walked over every
    `tests/test_*.py`, keyed narrowly on messages that claim a measurement ("N were
    measured", "N was the count"), so a date, a slice bound or an exit code in a message is
    not an offender and a wave number is struck out before the numbers are read.

    Derivation (suite interpreter — tests/conftest.py):
        .venv/Scripts/python.exe -c "import sys;sys.path.insert(0,'tests');import _census_nodes as CN;\\
        print(CN.messages_quoting_a_number_they_do_not_assert())"
    """
    stale = CN.messages_quoting_a_number_they_do_not_assert()
    assert stale == [], (
        "an assertion message names a measurement that is not the value it asserts; a seat "
        "landing a change reads the message as the current pin and retypes the wrong "
        f"number into the constant: {stale}")


def test_a_tool_with_no_excused_refusal_is_held_to_the_ordering_rule():
    """The exemption excuses REFUSALS, not modules: a tool whose refusals all sit above its
    first write must still be asserted, not skipped for reaching Blender.

    WAVE 14, F-3a0d4576: `and n not in GATES_READ_BACK_WHAT_THEY_WROTE` is gone from here
    too. It could only ever remove a tool that the first clause had already kept, so it was
    a module-wide skip standing in front of a per-refusal derivation.
    """
    members = sorted(derive_population())
    clean = [n for n in members if not refusals_below_the_first_write(n)]
    assert clean, "no member is clean; the walk is not measuring anything"
    for name in clean:
        gates_at, writes_at = gate_and_write_lines(_source(name), name)
        if not gates_at or not writes_at:
            continue
        assert max(gates_at) < min(writes_at), _format_ordering_failure(
            name, gates_at, writes_at)


def _with_a_refusal_below_the_first_write(name):
    """`name`'s real source with `gate_a_brand_new_refusal(x)` inserted one line under its
    first write — the mutation the ratchet exists to catch."""
    src = _source(name)
    _, writes_at = gate_and_write_lines(src, name)
    at = min(writes_at)
    lines = src.splitlines(keepends=True)
    target = lines[at - 1]
    indent = target[:len(target) - len(target.lstrip())]
    lines.insert(at, f"{indent}gate_a_brand_new_refusal(x)\n")
    return "".join(lines)


#: The three tools the module filter used to hide from the ratchet (F-3a0d4576). The red
#: proof runs on THESE, on their real sources, because the hole was exactly here: the proof
#: this file shipped ran on `rig_character`, which was never module-exempt, so it could not
#: have caught the defect it was written to guard against. `rig_character` is also the wrong
#: subject for a second reason instruments measured in wave 13 — its first write sits in a
#: mutually-exclusive measure branch, so the ordering it probes is an artefact of the walk
#: rather than a real one.
FORMERLY_MODULE_EXEMPT = sorted(GATES_READ_BACK_WHAT_THEY_WROTE)


@pytest.mark.parametrize("name", FORMERLY_MODULE_EXEMPT)
def test_the_per_refusal_exemption_goes_red_on_a_new_refusal_under_a_write(name):
    """Rule 3, on the operand the finding named: insert a refusal BELOW the first write in
    one of the three read-back tools and the RATCHET'S OWN expression must fail.

    Not a re-implementation of the walk beside the ratchet — `stranded_by_tool` is the
    function the assertion calls, driven here over the mutated source. With the module
    filter restored inside it, `grew` evaluates to `{}` on every one of these three and this
    test goes green over a live hole; that is the reverted-red proof.
    """
    mutated = _with_a_refusal_below_the_first_write(name)
    members = sorted(derive_population())
    detail = stranded_detail_by_tool(members, source={name: mutated})
    derived = {n: v["refusals"] for n, v in detail.items()}
    assert "gate_a_brand_new_refusal" in derived.get(name, []), derived.get(name)
    grew = {n: sorted(set(v) - set(REFUSALS_BELOW_THE_FIRST_WRITE.get(n, [])))
            for n, v in derived.items()
            if set(v) - set(REFUSALS_BELOW_THE_FIRST_WRITE.get(n, []))}
    assert grew == {name: ["gate_a_brand_new_refusal"]}, grew
    # F-0d690499: the message names the first write (line + kind), not an unnamed "it".
    named = _format_stranded_growth(detail, grew)
    fw_ln, fw_kind = detail[name]["first_write"]
    assert name in named and f"below {fw_kind} at :{fw_ln}" in named[name], named


def test_the_read_back_table_is_read_and_says_what_it_means():
    """F-385f2b60: the exemption's stated justification, asserted rather than narrated.

    Four things, none of which anything checked before this wave:

    1. the two tables COVER the ratchet's names exactly, and do not overlap — so a name
       cannot be excused twice or excused by absence;
    2. every read-back reason NAMES A CALL, and that call is found in the source of every
       tool whose entry names the refusal — the checkable half of "it verifies that write";
    3. no reason is empty and none is the `REVIEW:` placeholder that 34 of the 47 entries
       carried;
    4. the backlog's size is on the page, and every entry has an owner drawn from the run's
       own domain set — derived from the file, never typed.
    """
    listed = {n for v in REFUSALS_BELOW_THE_FIRST_WRITE.values() for n in v}
    assert set(READBACK_REASONS) | set(NOT_YET_MOVED) == listed, {
        "in the ratchet with no reason at all":
            sorted(listed - set(READBACK_REASONS) - set(NOT_YET_MOVED)),
        "given a reason and no longer in the ratchet":
            sorted((set(READBACK_REASONS) | set(NOT_YET_MOVED)) - listed)}
    assert set(READBACK_REASONS) & set(NOT_YET_MOVED) == set(), sorted(
        set(READBACK_REASONS) & set(NOT_YET_MOVED))

    # Clauses 2 and 3 are `read_back_table_violations`, called on the module constants —
    # the SAME function the red proof below drives over a mutated table (F-d18443ac).
    assert read_back_table_violations() is True

    for refusal in sorted(NOT_YET_MOVED):
        owners = owners_of(refusal)
        assert owners and set(owners) <= RUN_DOMAINS, (refusal, owners)

    # The backlog, on the page. RE-DERIVED 2026-09-04 (wave 14):
    #     .venv/Scripts/python.exe -c "import sys;sys.path[:0]=['tests','tools'];\
    #     import test_instrument_write_ordering as M;\
    #     print(len(M.READBACK_REASONS), len(M.NOT_YET_MOVED))"  # suite interpreter: tests/conftest.py
    # WAVE-14 MERGE (coordinator, 2026-09-04): 12 / 35 → 12 / 29, measured after the six names left.
    # WAVE 22 (builders, 2026-09-05): 12 -> 11, RE-DERIVED with `==`. `raise FetchHalt`
    # leaves the table with the refusal it described: `fetch_t2v_run`'s
    # `zero_length_frames` clause was deleted (F-c03a23c5) because it COULD NOT FIRE —
    # `verify_downloads` above it already raises on any zero-length planned output, over a
    # WIDER population (the video job included), and the deleted branch read a manifest
    # built from a strict subset of the same paths. A reason for a refusal that no longer
    # exists is a reason nothing can be checked against.
    # RE-DERIVED wave 22 (instruments, F-a2630f86), branch-local: 12 -> 13.
    # WAVE-22 MERGE (coordinator, 2026-09-05): 12 MEASURED — builders deleted one reason (11) and instruments added one (13) on
    # different branches; the merged table holds what the merged tree holds.
    # WAVE 25 (instruments, F-19d4e0f7): 12 -> 13, `require_import_status`.
    assert len(READBACK_REASONS) == 13, sorted(READBACK_REASONS)
    # WAVE 16, F-9b4d01ef: the message named 35, which the wave-14 merge overturned when it
    # re-derived 12 / 29 on the merged tree. Same correction as the sites message above.
    # WAVE 34: 29 -> 32 (`author`, `gate_objects_registered`, `gate_space_is_identity`).
    # WAVE 37: 32 -> 34. merge_spend_into_record + write_diff_sheet join the backlog.
    assert len(NOT_YET_MOVED) == 34, (
        f"{len(NOT_YET_MOVED)} refusals still sit below a first write without reading it "
        f"back; this pin asserts 32, re-derived after wave 34 retarget strands, and the "
        f"number may only fall — a move deletes its entry in the commit that makes it")


def test_the_read_back_table_check_is_red_on_a_placeholder_and_on_a_reason_that_names_nothing():
    """Rule 3 on the checker above, on the two shapes the real table carried.

    Reverting F-385f2b60 means putting a `REVIEW:` placeholder back, or leaving a reason
    whose named call the tool never makes. Both are exercised here, so the check is shown to
    fail on the exact input it was written for rather than on a hypothetical.

    WAVE 16, F-d18443ac — this proof used to exercise a COPY of the checker. Both
    `pytest.raises` blocks re-implemented the clauses inline over literals the test built
    itself, so neither ever called the assertion under test. Measured by driving both in
    process against the live table: with the exact placeholder below restored as
    `READBACK_REASONS['gate_r_round_trip']`'s reason, the REAL checker failed and this
    proof still passed. It now drives `read_back_table_violations` — the function the
    checker calls — over a COPY of the live table carrying each defect in turn, the way its
    sibling two functions up drives `stranded_by_tool` over mutated source.
    """
    real_call, real_why = READBACK_REASONS["gate_r_round_trip"]

    # BASELINE: the live tables satisfy the contract, or nothing below means anything.
    assert read_back_table_violations() is True

    # 1. the `REVIEW:` placeholder, restored into a COPY of the LIVE table and driven
    #    through the real checker — the literal 34 of the 47 entries carried.
    placeholder = "REVIEW: not a read-back — a strand the coordinator did not move"
    assert "REVIEW" in placeholder
    with_placeholder = dict(READBACK_REASONS)
    with_placeholder["gate_r_round_trip"] = (real_call, placeholder)
    with pytest.raises(ReadBackTableViolation, match="REVIEW placeholder"):
        read_back_table_violations(readback=with_placeholder)

    # …and in the backlog table, whose entries carry a reason and no call.
    backlog_placeholder = dict(NOT_YET_MOVED)
    backlog_placeholder[sorted(NOT_YET_MOVED)[0]] = placeholder
    with pytest.raises(ReadBackTableViolation, match="placeholder, not a reason"):
        read_back_table_violations(not_yet_moved=backlog_placeholder)

    # 2. a reason that names a call the tool does not make — same table, one field moved.
    names_nothing = dict(READBACK_REASONS)
    names_nothing["gate_r_round_trip"] = (
        "read_back_a_call_pack_pose_pack_never_makes", real_why)
    with pytest.raises(ReadBackTableViolation, match="does not appear in"):
        read_back_table_violations(readback=names_nothing)

    # 3. an EMPTY reason, the third shape the clause bounds.
    empty = dict(READBACK_REASONS)
    empty["gate_r_round_trip"] = (real_call, "")
    with pytest.raises(ReadBackTableViolation, match="REVIEW placeholder"):
        read_back_table_violations(readback=empty)

    # the real one is found, or the comparisons above say nothing
    for tool in tools_naming("gate_r_round_trip"):
        assert real_call in _source(tool), tool


def test_the_read_back_checker_and_its_red_proof_are_the_same_function():
    """F-d18443ac's own fix, asserted rather than trusted.

    The shape `test_sheet_argv_smoke.py::test_the_two_walks_are_literally_the_same_function`
    already uses: not "these two agree today", but "there is one implementation". A red
    proof that re-implements the clause it is proving can go green over a live hole, which
    is exactly what this file's did for two waves.
    """
    import inspect

    checker = inspect.getsource(test_the_read_back_table_is_read_and_says_what_it_means)
    proof = inspect.getsource(
        test_the_read_back_table_check_is_red_on_a_placeholder_and_on_a_reason_that_names_nothing)
    assert "read_back_table_violations(" in checker
    assert "read_back_table_violations(" in proof
    for text, who in ((checker, "the checker"), (proof, "the red proof")):
        assert '"REVIEW" not in why' not in text, (
            f"{who} re-implements the placeholder clause inline; the clause has one home")


# ---------------------------------------- THE RED PROOF: the shape that hides from the name
#
# Wave 12, rule 2: every census fix ships a fixture carrying the property under a DIFFERENT
# spelling and is shown red on it. The spelling this walk was blind to is an INLINE `raise`
# — not a call at all, so no callee-name predicate can reach it — and a module-local helper
# whose name carries no `gate_`/`require_` prefix.


INLINE_RAISE_MODULE = (
    "import os\n"
    "from armature_core.errors import ArmatureError\n"
    "def main(argv=None):\n"
    "    os.makedirs(out, exist_ok=True)\n"
    "    if not frames:\n"
    "        raise ArmatureError('expected exactly one skinned mesh')\n"
    "    with open(path, 'w') as fh:\n"
    "        fh.write('x')\n"
)

# `main` here carries four statements on purpose: `cli_body` follows ONE delegation out of a
# `main` that is a three-statement wrapper calling exactly one module-level function, so a
# shorter probe would be read AS the helper rather than as a caller of it.
HELPER_HOP_MODULE = (
    "import os\n"
    "from armature_core.errors import ArmatureError\n"
    "def import_reference(path):\n"
    "    raise ArmatureError('nothing importable')\n"
    "def main(argv=None):\n"
    "    src = argv[0]\n"
    "    out = argv[1]\n"
    "    os.makedirs(out, exist_ok=True)\n"
    "    import_reference(src)\n"
    "    with open(out, 'w') as fh:\n"
    "        fh.write('x')\n"
)


def test_the_refusal_predicate_sees_an_inline_raise_that_the_name_keyed_one_cannot():
    """RED on the hidden spelling, and the old walk shown blind to it in the same test.

    `make_rig_sheet.main` is this shape on the real tree: `<out>/` at :95 and
    `<out>/panels/` at :97, then `raise ArmatureError` inline at :112, :119 and :139. Under
    the name-keyed predicate the module carried no refusals at all, so
    `derive_population()` — which keeps a module only when `gates_at and writes_at` —
    dropped it, and the census reported nothing about a refused run that leaves two empty
    directories on disk.
    """
    gates, writes = gate_and_write_lines(INLINE_RAISE_MODULE, "probe")
    assert writes, "the probe writes; the walk must see that"
    stranded = sorted(gates[ln] for ln in gates if ln > min(writes))
    assert stranded == ["raise ArmatureError"], (gates, writes)

    blind_gates, blind_writes = gate_and_write_lines(
        INLINE_RAISE_MODULE, "probe", by_name_only=True)
    assert blind_gates == {}, (
        "the pre-wave-12 predicate reported a refusal it cannot structurally see; the "
        "comparison this test makes is meaningless")
    assert blind_writes, blind_writes
    # …and the consequence: with no refusal, the module never enters `derive_population()`.
    assert not (blind_gates and blind_writes)


def test_the_refusal_predicate_follows_one_hop_into_a_helper_with_no_gate_prefix():
    """The second hidden spelling: `import_reference(src)` is a refusal because the callee
    raises, not because of how it is spelled."""
    gates, writes = gate_and_write_lines(HELPER_HOP_MODULE, "probe")
    stranded = sorted(gates[ln] for ln in gates if ln > min(writes))
    assert stranded == ["import_reference"], (gates, writes)
    blind_gates, _ = gate_and_write_lines(HELPER_HOP_MODULE, "probe", by_name_only=True)
    assert blind_gates == {}, blind_gates


def test_the_nine_tools_the_name_keyed_walk_could_not_see_are_in_the_population_now():
    """The measurement, asserted rather than narrated (F-183635ad).

    Nine tools strand a refusal below their first write AND were outside
    `derive_population()` entirely under the name-keyed predicate, because that function
    keeps a module only when it can see both a refusal and a write.
    """
    # WAVE-12 MERGE (coordinator, 2026-09-04): `measure_cascade_clip` LEFT this list — instruments-measure gave it
    # `gate_clip_rate` (a `gate_` name) in the same wave, so the name-keyed walk sees it too; eight remain.
    # `rig_bake`, `rig_repair`, `rig_retopo` LEFT too — instruments gave each `gate_glb_written`
    # (a `gate_` name, F-9b2d4106); five remain invisible to the name-keyed walk on the merged tree.
    # WAVE 14 (instruments-measure, F-0d033bd6): `make_shotset_sheet` no longer STRANDS a
    # refusal — its `os.makedirs` moved below all nine of its pre-write refusals — but it is
    # still a member of the population and still invisible to the name-keyed walk, which is
    # what this test is about. So the membership half keeps every one of the five names and
    # the stranded half names the four that still strand one. The entry is corrected in
    # place rather than deleted: "the walk could not see it" and "it strands a refusal" are
    # two different claims, and only the second one stopped being true.
    # WAVE-14 MERGE (coordinator, 2026-09-04): `make_rig_sheet` LEFT this list too — instruments split its argv clause into
    # `require_reference_file` (F-4db23b72), a `require_` name the name-keyed walk sees; four remain.
    # WAVE 22 (instruments, F-a2630f86): `preview_walk` LEAVES this list, corrected in
    # place for the reason `make_rig_sheet` left it in wave 14 — it now carries a
    # `require_`-named refusal (`require_render_target_moved`, the render half of Gate
    # GLB's stale-target clause), so the name-keyed predicate is no longer blind to it
    # and the claim this list makes about it stopped being true. It remains in the
    # derived population and still strands that refusal below the write, which is what
    # `REFUSALS_BELOW_THE_FIRST_WRITE` records; only "the walk could not see it" is gone.
    # WAVE 25 (instruments, F-19d4e0f7): `make_parts_sheet` LEAVES this list, corrected
    # in place for the reason `preview_walk` left it in wave 22 and `make_rig_sheet`
    # in wave 14 -- it now carries a `require_`-named refusal
    # (`require_import_status`, the glTF importer's status clause), so the name-keyed
    # predicate is no longer blind to it and the claim this list makes about it
    # stopped being true. It remains in the derived population and still strands
    # `shoot` below its first write, which is what `REFUSALS_BELOW_THE_FIRST_WRITE`
    # records; only "the walk could not see it" is gone.
    joined = ["extract_clip_frames", "make_shotset_sheet"]
    # WAVE-14 MERGE (coordinator, 2026-09-04): `make_rig_sheet` stopped stranding too (instruments, F-4db23b72).
    strands_one_today = [n for n in joined if n not in ("make_shotset_sheet", "make_rig_sheet")]
    pop = derive_population()
    for name in joined:
        assert name in pop, f"{name} is not in the derived population"
        assert bool(refusals_below_the_first_write(name)) == (
            name in strands_one_today), name
        blind_gates, blind_writes = gate_and_write_lines(
            _source(name), name, by_name_only=True)
        assert not (blind_gates and blind_writes), (
            f"{name} was already visible to the name-keyed predicate; it does not belong "
            f"in this list")


@pytest.mark.parametrize("name", sorted(POPULATION_MEASURED_2026_09_04))
def test_no_refusal_sits_below_the_first_write(name):
    # WAVE 14, F-3a0d4576: the module-wide `if name in GATES_READ_BACK_WHAT_THEY_WROTE:
    # pytest.skip(...)` that stood here — BEFORE the per-name branch below — is gone. It
    # excused three whole modules on a per-refusal reason, so a tool that lost every entry in
    # the ratchet would still have been skipped by the module it lives in. The per-name
    # branch below now governs: the three read-back tools are listed there today and skip for
    # the reason that is actually true of them, and the day a move empties one of their
    # entries this assertion starts running against it.
    if name in REFUSALS_BELOW_THE_FIRST_WRITE:
        pytest.skip(
            "its refusals under the first write are named individually in "
            "REFUSALS_BELOW_THE_FIRST_WRITE and ratcheted there; this module-level "
            "assertion would say nothing the ratchet does not")
    gates_at, writes_at = gate_and_write_lines(_source(name), name)
    # WAVE 16: a NAMED refusal rather than a `max() iterable argument is empty` ValueError.
    # Every member of `derive_population()` gates AND writes by construction, so a member of
    # the recorded population that does neither means the two have drifted apart — which is
    # a defect in the population, not a crash in this comparison. (Measured: with
    # `make_e13_sheet` recorded ahead of instruments-measure's refusal landing, this line
    # raised `ValueError` and named nothing.)
    assert gates_at and writes_at, (
        f"{name} is in POPULATION_MEASURED_2026_09_04 and `gate_and_write_lines` finds "
        f"{len(gates_at)} refusal(s) and {len(writes_at)} write(s) in its CLI body; a "
        f"member of the derived population has both. Either the tool changed or the "
        f"recorded population is ahead of the tree")
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


# ===========================================================================
# WAVE 23, F-d91c8d9b — the write predicate recognises the writes this tree makes
# ===========================================================================
#
# `refusal_and_write_lines` counted a write only as `os.makedirs` or `open(...)` whose
# SECOND POSITIONAL argument is a mode containing `w`. Measured 2026-09-05 by re-running the
# census's own walk with the wider spellings over every tool it admits: 24 tools carry a
# write it could not see — `cv2.imwrite`, `Image.save`, `np.save`, `shutil.copy*`,
# `Path.write_text` / `write_bytes` and `open(path, mode="w")` were all invisible.
#
# THE HALF WORTH RECORDING: the live-defect form is REFUTED and stays refuted. In ALL 24, a
# recognised `os.makedirs` already sits ABOVE the hidden write, so the first-write line the
# ordering property reads is unchanged and no refusal moves below it. RE-DERIVED after the
# widening with the file's own derivation command: 27 / 54 / 77, the same three numbers —
# the population is a floor by construction and the widening moves it not at all.
#
# What it buys is the next tool: a control-sequence tool whose first byte reaches disk
# through `cv2.imwrite` above its refusals used to pass the census whose whole purpose is
# that no refusal sits below the first write. That is what the red proof below drives.


def test_the_write_predicate_sees_a_cv2_imwrite_above_a_refusal():
    """The RED PROOF: a synthetic tool whose ONLY write is `cv2.imwrite`, above its refusal.

    Under the two-spelling predicate this module reports no write at all, so it never enters
    `derive_population()` (which keeps a module only when `gates_at and writes_at`) and the
    ordering property is not applied to it. Under the widened one the write is seen and the
    refusal below it is stranded — which is the whole point of the census.
    """
    src = "\n".join([
        "import argparse, cv2",
        "from armature_core.errors import ArmatureError",
        "",
        "def main(argv=None):",
        "    ap = argparse.ArgumentParser()",
        "    ap.add_argument('--out', required=True)",
        "    ap.add_argument('--rows', type=int, default=4)",
        "    a = ap.parse_args(argv)",
        "    cv2.imwrite(a.out, build())",
        "    if a.rows <= 0:",
        "        raise ArmatureError('--rows is a count', {'clause': 'rows_not_positive'})",
        "    return 0",
    ])
    gates, writes = gate_and_write_lines(src, "<synthetic probe>")
    assert writes == {9: "cv2.imwrite"}, writes
    assert gates and min(gates) > min(writes), (gates, writes)

    # …and the predicate this replaces is blind to it: no write, so no population, so no
    # ordering property. Reconstructed here rather than described.
    narrow = {ln for ln, kind in writes.items() if kind == "os.makedirs"}
    assert narrow == set(), (
        "the two-spelling predicate would have reported this module's write; the "
        "comparison below says nothing")


def test_the_widened_predicate_still_refuses_a_read(tmp_path):
    """The direction the predicate must not bound: `open(path)` and `open(path, "rb")` are
    not writes, and a census that calls every `open` a write would strand every refusal in
    the tree."""
    src = "\n".join([
        "import argparse, json",
        "from armature_core.errors import ArmatureError",
        "",
        "def main(argv=None):",
        "    ap = argparse.ArgumentParser()",
        "    ap.add_argument('--src', required=True)",
        "    a = ap.parse_args(argv)",
        "    with open(a.src, encoding='utf-8') as fh:",
        "        doc = json.load(fh)",
        "    with open(a.src, 'rb') as fh:",
        "        head = fh.read(4)",
        "    if not doc:",
        "        raise ArmatureError('empty', {'clause': 'empty'})",
        "    return 0 if head else 1",
    ])
    _gates, writes = gate_and_write_lines(src, "<synthetic probe>")
    assert writes == {}, writes


def test_the_keyword_mode_spelling_is_a_write():
    """`open(path, mode="w")` — the spelling the positional-only read could not see."""
    src = "\n".join([
        "import argparse",
        "from armature_core.errors import ArmatureError",
        "",
        "def main(argv=None):",
        "    ap = argparse.ArgumentParser()",
        "    ap.add_argument('--out', required=True)",
        "    a = ap.parse_args(argv)",
        "    with open(a.out, mode='w', encoding='utf-8') as fh:",
        "        fh.write('x')",
        "    raise ArmatureError('late', {'clause': 'late'})",
    ])
    _gates, writes = gate_and_write_lines(src, "<synthetic probe>")
    assert writes == {8: 'open(..., "w")'}, writes


def test_the_hidden_writes_all_sit_below_a_recognised_makedirs():
    """The measurement the refutation rests on, kept as an assertion rather than as prose.

    For every tool this census admits, the FIRST write the widened predicate reports is at
    or above every write the narrow predicate reported — i.e. widening can only move the
    first-write line EARLIER, and here it moves it nowhere that changes a verdict. If a
    later edit puts a `cv2.imwrite` above a tool's `os.makedirs` this fails, naming it, and
    the pins are re-derived in that commit.
    """
    moved = {}
    for name in sorted(derive_population()):
        src = _source(name)
        _gates, wide = gate_and_write_lines(src, name)
        narrow = {ln for ln, kind in wide.items()
                  if kind in ("os.makedirs", 'open(..., "w")')}
        if not narrow or not wide:
            continue
        if min(wide) < min(narrow):
            moved[name] = {"widened first write": min(wide),
                           "narrow first write": min(narrow),
                           "kind": wide[min(wide)]}
    assert moved == {}, (
        f"the widened write predicate moves the first-write line earlier in {sorted(moved)}: "
        f"{moved}. Re-derive the 27 / 54 / 77 pins in the same commit and record which "
        f"refusals the move strands.")
