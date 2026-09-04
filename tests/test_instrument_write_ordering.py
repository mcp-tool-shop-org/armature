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
    # WAVE-12 MERGE (coordinator, 2026-09-04): `make_overlay_sheet` JOINED — its `cv2.imwrite` return is a typed
    # refusal now (instruments-measure), so it gates-and-writes.
    "make_overlay_sheet",
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
    "author_walk": ["gate_a_arrival", "gate_glb_written", "gate_n_names", "pick_subject"],
    "extract_clip_frames": ["probe", "raise ClipReadError"],
    "fetch_run": ["download", "verify_downloads"],
    # WAVE-14 MERGE (coordinator, 2026-09-04): `download` LEFT — `fetch_t2v_run.download` is now a call into
    # `fetch_run.download` (builders, F-a3ba416b: one downloader across both fetchers); measured.
    "fetch_t2v_run": ["gate_order_evidence", "order_evidence", "raise FetchHalt"],
    "fit_reference": ["raise FitReferenceError"],
    "lift_solve": ["gate_arrived", "gate_glb_written", "gate_n_names", "pick_subject"],
    "make_binding_sheet": ["render_arm"],
    "make_e08_sheet": ["raise SheetInputError"],
    "make_lift_sheet": ["subject_box"],
    "make_overlay_sheet": ["raise OverlaySheetError"],
    "make_parts_sheet": ["shoot"],
    "make_plate": ["raise ArmatureError"],
    "make_test_armature": ["gate_glb_written"],
    "make_zoom_sheet": ["raise ZoomSheetError"],
    "measure_cascade_clip": ["raise ClipCountError"],
    "pack_pose_pack": ["gate_r_round_trip"],
    "preview_glb": ["gate_previews_written"],
    "preview_walk": ["raise PreviewWalkGate"],
    "render_performer": ["gate_coverage", "raise RenderGate"],
    "render_pose_sticks": ["raise SticksGate"],
    "render_start_frame": ["gate_alpha", "gate_backdrop", "raise RenderGate"],
    "render_turnaround": ["gate_set_distinct", "gate_view_alpha", "gate_view_crop", "gate_whole", "raise RenderTurnaroundGate"],
    "rig_bake": ["gate_glb_written"],
    "rig_character": ["build_pass", "export_rigged", "gate_d_determinism", "gate_n_names", "raise GateMode", "unbound_determinism_record"],
    "rig_parts": ["gate_atlas_untouched", "gate_glb_written", "gate_part_names"],
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
    "raise FetchHalt": ("order_evidence",
                        "raised off the order evidence read back from what it downloaded"),
    "raise OverlaySheetError": ("imwrite", "the refusal IS the `cv2.imwrite` return"),
    "raise SheetInputError": ("imwrite",
                              "the refusal IS the `cv2.imwrite` return \u2014 it verifies the "
                              "write it just made"),
    "raise SticksGate": ("imwrite",
                         "the refusal IS the `cv2.imwrite` return for the frame just drawn"),
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
#: Re-derive with:
#:     python -c "import sys;sys.path[:0]=['tests','tools'];\
#:     import test_instrument_write_ordering as M;\
#:     print(len(M.NOT_YET_MOVED))"
NOT_YET_MOVED = {
    # WAVE-14 MERGE (coordinator, 2026-09-04): six names left — the four `make_shotset_sheet` / `make_rig_sheet` / `make_skeleton_sheet`
    # strands moved above their writes (instruments, instruments-measure) and `gate_ink` moved (instruments-measure).
    "build_pass": "rig_character's build pass refuses below the measure branch's makedirs (wave 13 read this family as an artefact of the walk's mutually-exclusive-branch handling; the walk is the operand, not the reason)",
    "export_rigged": "rig_character, same family as `build_pass`",
    "gate_a_arrival": "author_walk stages the walk and refuses after the run directory exists",
    "gate_alpha": "render_start_frame refuses on alpha after the first frame's directory exists",
    "gate_arrived": "lift_solve, the author_walk shape one domain over",
    "gate_atlas_untouched": "rig_parts refuses on the atlas after the part GLBs are written",
    "gate_backdrop": "render_start_frame, same family as `gate_alpha`",
    "gate_coverage": "render_performer refuses on coverage after the render directory exists",
    "gate_d_determinism": "rig_character, same family as `build_pass`",
    "gate_n_names": "author_walk / lift_solve / rig_character",
    "gate_part_names": "rig_parts, same family as `gate_atlas_untouched`",
    "gate_set_distinct": "render_turnaround refuses on the view set after the out dir exists",
    "gate_view_alpha": "render_turnaround, same family as `gate_set_distinct`",
    "gate_view_crop": "render_turnaround, same family as `gate_set_distinct`",
    "gate_whole": "render_turnaround, same family as `gate_set_distinct`",
    "pick_subject": "author_walk / lift_solve pick the subject after the run directory exists",
    "probe": "extract_clip_frames probes the clip after the frame directory exists",
    "raise ArmatureError": "make_plate refuses inline below its first write",
    "raise ClipCountError": "measure_cascade_clip refuses on the clip count below its first write",
    "raise ClipReadError": "extract_clip_frames, same family as `probe`",
    "raise FitReferenceError": "fit_reference refuses inline below its first write",
    "raise GateMode": "rig_character, same family as `build_pass`",
    "raise PreviewWalkGate": "preview_walk refuses inline below its first write",
    "raise RenderGate": "render_performer / render_start_frame",
    "raise RenderTurnaroundGate": "render_turnaround, same family as `gate_set_distinct`",
    "render_arm": "make_binding_sheet renders the arm after `<out>/` exists",
    "shoot": "make_parts_sheet shoots after `<out>/` exists",
    "subject_box": "make_lift_sheet takes the subject box after `<out>/` exists",
    "unbound_determinism_record": "rig_character, same family as `build_pass`",
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
    """
    source = source or {}
    members = sorted(derive_population()) if members is None else members
    out = {}
    for name in members:
        gates_at, writes_at = gate_and_write_lines(source.get(name, _source(name)), name)
        if not gates_at or not writes_at:
            continue
        first_write = min(writes_at)
        below = sorted({gates_at[ln] for ln in gates_at if ln > first_write})
        if below:
            out[name] = below
    return out


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
    derived = stranded_by_tool(members)
    grew = {n: sorted(set(v) - set(REFUSALS_BELOW_THE_FIRST_WRITE.get(n, [])))
            for n, v in derived.items()
            if set(v) - set(REFUSALS_BELOW_THE_FIRST_WRITE.get(n, []))}
    assert grew == {}, {
        "new refusals under a write (move them above it, or add with the reason)": grew}
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
    #     python -c "import sys;sys.path[:0]=['tests','tools'];\
    #     import test_instrument_write_ordering as M;\
    #     d=M.stranded_by_tool();print(len(d),sum(len(v) for v in d.values()),\
    #     M.stranded_site_count())"
    # WAVE-14 MERGE (coordinator, 2026-09-04): 30 / 58 / 72 → 27 / 51 / 69, MEASURED on the merged tree (never subtracted).
    assert len(derived) == 27, sorted(derived)
    names = sum(len(v) for v in derived.values())
    assert names == 51, sorted(derived.items())
    sites = stranded_site_count(members)
    assert sites == 69, (
        f"{sites} refusal SITES below a first write; 72 were measured on 2026-09-04 over "
        f"the full derived population, and the number falls as the moves land")


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
        assert max(gates_at) < min(writes_at), (name, gates_at, writes_at)


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
    derived = stranded_by_tool(members, source={name: mutated})
    assert "gate_a_brand_new_refusal" in derived.get(name, []), derived.get(name)
    grew = {n: sorted(set(v) - set(REFUSALS_BELOW_THE_FIRST_WRITE.get(n, [])))
            for n, v in derived.items()
            if set(v) - set(REFUSALS_BELOW_THE_FIRST_WRITE.get(n, []))}
    assert grew == {name: ["gate_a_brand_new_refusal"]}, grew


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

    for refusal, (call, why) in sorted(READBACK_REASONS.items()):
        assert call and why and "REVIEW" not in why, (refusal, call, why)
        for tool in tools_naming(refusal):
            assert call in _source(tool), (
                f"{refusal} is excused in {tool} as a read-back performed by {call!r}, and "
                f"{call!r} does not appear in tools/{tool}.py; the reason names a call the "
                f"tool does not make")

    for refusal, why in sorted(NOT_YET_MOVED.items()):
        assert why and "REVIEW" not in why, (refusal, why)
        owners = owners_of(refusal)
        assert owners and set(owners) <= RUN_DOMAINS, (refusal, owners)

    # The backlog, on the page. RE-DERIVED 2026-09-04 (wave 14):
    #     python -c "import sys;sys.path[:0]=['tests','tools'];\
    #     import test_instrument_write_ordering as M;\
    #     print(len(M.READBACK_REASONS), len(M.NOT_YET_MOVED))"
    # WAVE-14 MERGE (coordinator, 2026-09-04): 12 / 35 → 12 / 29, measured after the six names left.
    assert len(READBACK_REASONS) == 12, sorted(READBACK_REASONS)
    assert len(NOT_YET_MOVED) == 29, (
        f"{len(NOT_YET_MOVED)} refusals still sit below a first write without reading it "
        f"back; 35 were measured on 2026-09-04 and the number may only fall — a move "
        f"deletes its entry in the commit that makes it")


def test_the_read_back_table_check_is_red_on_a_placeholder_and_on_a_reason_that_names_nothing():
    """Rule 3 on the checker above, on the two shapes the real table carried.

    Reverting F-385f2b60 means putting a `REVIEW:` placeholder back, or leaving a reason
    whose named call the tool never makes. Both are exercised here, so the check is shown to
    fail on the exact input it was written for rather than on a hypothetical.
    """
    real_call, _real_why = READBACK_REASONS["gate_r_round_trip"]

    placeholder = "REVIEW: not a read-back — a strand the coordinator did not move"
    assert "REVIEW" in placeholder            # the literal 34 entries carried
    with pytest.raises(AssertionError):
        for refusal, why in {"gate_ink": placeholder}.items():
            assert why and "REVIEW" not in why, (refusal, why)

    # …and a reason that names a call the tool does not make.
    with pytest.raises(AssertionError):
        for tool in tools_naming("gate_r_round_trip"):
            assert "read_back_a_call_pack_pose_pack_never_makes" in _source(tool), tool
    # the real one is found, or the comparison above says nothing
    for tool in tools_naming("gate_r_round_trip"):
        assert real_call in _source(tool), tool


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
    joined = ["extract_clip_frames", "make_parts_sheet",
              "make_shotset_sheet", "preview_walk"]
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
