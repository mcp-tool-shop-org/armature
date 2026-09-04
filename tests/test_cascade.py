"""The cascade's andons — E13's re-arm, Stage 0.

S03 measured the flat chain executing at 8 slots and failing at 81 on
`BatchImagesNode.execute() got an unexpected keyword argument 'images.image50'`. The
cascade batches the batches so no node is loaded above the observed cap. That re-shape
adds failure modes the flat gate cannot describe, and every one of them is silent:

* a group dropped from the final batch — a shorter clip, no error anywhere;
* the groups wired out of order — 81 frames, right count, shuffled clip;
* a frame in two groups and another in none — right count, wrong clip;
* the group size edited upward past the cap — pre-flight passes and execution dies, which
  is precisely what S03 measured (round-trip admitted, Gate-ROUTE walked, pre-flight green
  with zero warnings, refused at execution).

Every fixture below asks the question CLAUDE.md requires of a fixture: what would this look
like if the code were wrong in the specific way this check exists to catch? So the failure
graphs here are built by mutating a good graph in exactly one place, and each one keeps
every count that any other check reads.
"""

import json
import os
import subprocess
import sys
import textwrap

import pytest

import build_cascade_payload as B
from armature_core import assembly as AS
from conftest import TOOLS



# ---------------------------------------------------------------------------------------
# P2 / P3 seam adapter (swarm wave 3, health-amend-a) — TEST-LOCAL, never in the tools.
#
# The builders call the shared gates in the shape the core-solvers branch ships:
#
#     AS.gate_slot_ceiling(graph, group_size=..., cap=...)
#     AS.gate_batch_topology(graph, n, batch, video, save, *, expected_sources)
#     AS.gate_cascade_topology(graph, n, groups, final, video, save, consumer_input,
#                              group_size=..., *, expected_sources)
#
# THIS branch's `armature_core.assembly` does not declare those two keywords yet, so
# without the adapter below every end-to-end fixture here dies on a TypeError that says
# nothing about the code under test. The adapter reads the real signature and does exactly
# two things, both of which become no-ops the moment the sibling branch merges:
#
#   * drops `group_size` / `expected_sources` when the local gate does not declare them —
#     so the pre-merge run exercises THIS branch's half of the pair;
#   * supplies a derived `expected_sources` when the merged gate REQUIRES one and a test
#     calls the gate directly without it — so this module's older fixtures, which predate
#     the parameter, keep exercising the clauses they were written for.
#
# Owner of its deletion: the coordinator, in the commit that merges the two branches.


@pytest.fixture(autouse=True)
def _pair_seam_adapter(monkeypatch):
    import inspect

    from armature_core import assembly as _AS

    def adapt(fname, derive=None):
        fn = getattr(_AS, fname)
        params = inspect.signature(fn).parameters

        def shim(*a, _fn=fn, _params=params, _derive=derive, **kw):
            for key in ("group_size", "expected_sources"):
                if key in kw and key not in _params:
                    kw.pop(key)
            need = _params.get("expected_sources")
            if (need is not None and need.default is inspect.Parameter.empty
                    and "expected_sources" not in kw and _derive is not None):
                kw["expected_sources"] = _derive(*a)
            return _fn(*a, **kw)

        monkeypatch.setattr(_AS, fname, shim)

    def _ids(graph, n_frames, *rest):
        return [str(200 + i) for i in range(int(n_frames))]

    adapt("gate_slot_ceiling")
    adapt("gate_batch_topology", _ids)
    adapt("gate_cascade_topology", _ids)


def _names(n):
    return [f"{i:064x}.png" for i in range(n)]


def _graph(n=81, **kw):
    """A good cascade and its group ids."""
    return B.build(_names(n), **kw)


def _gates(wf, gids, n=81, group=AS.GROUP_SIZE):
    return AS.gate_cascade_topology(wf, n, gids, B.FINAL_BATCH_ID, B.VIDEO_ID, B.SAVE_ID,
                                    "video", group_size=group)


# ------------------------------------------------------------------ the plan itself


def test_the_plan_is_contiguous_ascending_and_exhaustive():
    plan = AS.cascade_plan(81, 27)
    assert plan == [(0, 27), (27, 54), (54, 81)]
    assert plan[0][0] == 0 and plan[-1][1] == 81
    assert all(a[1] == b[0] for a, b in zip(plan, plan[1:]))


def test_a_ragged_last_group_is_the_plan_not_an_error():
    """80 frames at 27 leaves 26 in the last group. The gate must accept the short tail and
    still refuse a short MIDDLE group, which is a different thing entirely."""
    assert AS.cascade_plan(80, 27) == [(0, 27), (27, 54), (54, 80)]
    wf, gids = _graph(80)
    assert _gates(wf, gids, n=80)["verdict"]


def test_a_group_size_of_zero_raises_rather_than_looping():
    with pytest.raises(AS.AssemblyGate):
        AS.cascade_plan(81, 0)


# ------------------------------------------------------------------ the slot ceiling


def test_the_built_cascade_is_under_the_ceiling_and_far_under_the_inferred_cap():
    wf, _ = _graph()
    ev = AS.gate_slot_ceiling(wf)
    assert max(ev["per_node"].values()) == 27
    assert AS.MAX_SLOTS_PER_NODE < AS.INFERRED_SLOT_CAP, (
        "the ceiling must sit BELOW the inferred cap: the cap is one error message's "
        "implication and was never measured at its boundary")


def test_the_flat_81_slot_graph_s03_measured_failing_is_refused_by_the_ceiling():
    """The exact graph S03 submitted: one BatchImagesNode carrying images.image0..80. It
    passed the round trip, Gate ROUTE and pre-flight, and died at execution. The ceiling is
    the check that would have caught it before the submission."""
    wf = {str(200 + i): {"class_type": "LoadImage", "inputs": {"image": f"{i}.png"}}
          for i in range(81)}
    wf["400"] = {"class_type": "BatchImagesNode",
                 "inputs": {f"images.image{i}": [str(200 + i), 0] for i in range(81)}}
    with pytest.raises(AS.AssemblyGate) as exc:
        AS.gate_slot_ceiling(wf)
    assert "more than 27" in str(exc.value)
    assert "INFERRED" in str(exc.value)


def test_a_group_size_edited_up_past_the_ceiling_raises():
    """The upward direction is the one the invariant does not bound, so it is the one gated:
    a group of 50 builds cleanly, wires cleanly, and is exactly the shape that dies."""
    wf, gids = _graph(81, group_size=50)
    assert _gates(wf, gids, group=50)["verdict"], "topology alone sees nothing wrong"
    with pytest.raises(AS.AssemblyGate):
        AS.gate_slot_ceiling(wf)


def test_the_ceiling_ignores_non_batch_nodes():
    wf, _ = _graph(4, group_size=2)
    ev = AS.gate_slot_ceiling(wf, cap=2)
    assert set(ev["per_node"]) == {"400", "401", "410"}


# ------------------------------------------------------------------ cascade topology


def test_the_built_cascade_passes_every_clause():
    wf, gids = _graph()
    ev = _gates(wf, gids)
    assert ev["n_groups"] == 3
    assert ev["n_sources"] == 81 and ev["n_distinct_sources"] == 81
    assert ev["final_links"] == [["400", 0], ["401", 0], ["402", 0]]
    assert AS.gate_no_paid_nodes(wf)["name_pattern_flagged"] == []


def test_groups_wired_to_the_final_batch_out_of_order_raises():
    """The defect this gate exists for. Every count is right — 81 frames, 3 groups, 3 slots
    — and the clip plays its middle third first. No other check in the repo sees it."""
    wf, gids = _graph()
    fi = wf[str(B.FINAL_BATCH_ID)]["inputs"]
    fi["images.image0"], fi["images.image1"] = fi["images.image1"], fi["images.image0"]
    with pytest.raises(AS.AssemblyGate) as exc:
        _gates(wf, gids)
    assert "out of sequence" in str(exc.value)


def test_a_dropped_group_raises():
    wf, gids = _graph()
    del wf[str(B.FINAL_BATCH_ID)]["inputs"]["images.image2"]
    with pytest.raises(AS.AssemblyGate) as exc:
        _gates(wf, gids)
    assert "final batch has 2 slot(s)" in str(exc.value)


def test_a_frame_in_two_groups_raises_even_though_the_count_is_right():
    """One frame duplicated, another orphaned. 81 slots, 81 frames loaded, 80 distinct."""
    wf, gids = _graph()
    wf["401"]["inputs"]["images.image0"] = wf["400"]["inputs"]["images.image0"]
    with pytest.raises(AS.AssemblyGate) as exc:
        _gates(wf, gids)
    assert "duplicated" in str(exc.value)


def test_a_short_middle_group_raises():
    wf, gids = _graph()
    del wf["400"]["inputs"]["images.image26"]
    with pytest.raises(AS.AssemblyGate) as exc:
        _gates(wf, gids)
    assert "expected 27" in str(exc.value)


def test_a_bare_images_list_in_a_group_raises():
    """E02 measured a bare `images` list VALIDATING under dry_run with zero warnings. The
    cascade inherits that hazard once per group, so the clause is checked per group."""
    wf, gids = _graph()
    wf["401"]["inputs"] = {"images": [["200", 0]]}
    with pytest.raises(AS.AssemblyGate) as exc:
        _gates(wf, gids)
    assert "bare `images` list" in str(exc.value)


def test_create_video_fed_from_a_group_instead_of_the_final_batch_raises():
    """The silent one: the clip is 27 frames, the graph runs, nothing errs."""
    wf, gids = _graph()
    wf[str(B.VIDEO_ID)]["inputs"]["images"] = ["400", 0]
    with pytest.raises(AS.AssemblyGate) as exc:
        _gates(wf, gids)
    assert "not the FINAL batch's output" in str(exc.value)


def test_an_unwired_save_raises_because_create_video_saves_nothing_itself():
    wf, gids = _graph()
    wf[str(B.SAVE_ID)]["inputs"]["video"] = ["999", 0]
    with pytest.raises(AS.AssemblyGate) as exc:
        _gates(wf, gids)
    assert "a VIDEO that never exists" in str(exc.value)


def test_a_group_pointing_at_a_batch_instead_of_a_loadimage_raises():
    wf, gids = _graph()
    wf["402"]["inputs"]["images.image0"] = ["400", 0]
    with pytest.raises(AS.AssemblyGate) as exc:
        _gates(wf, gids)
    assert "not a LoadImage" in str(exc.value)


def test_a_partner_node_in_the_cascade_is_caught_by_the_allowlist():
    """The cascade is supposed to cost nothing. The r2v node would run, produce a video,
    and bill 106-211 credits."""
    wf, _ = _graph(4, group_size=2)
    wf["500"] = {"class_type": "Wan2ReferenceVideoApi", "inputs": {"seed": 1}}
    with pytest.raises(AS.AssemblyGate):
        AS.gate_no_paid_nodes(wf)


# ------------------------------------------------------------------ frame order


def test_frames_are_ordered_by_local_name_not_by_server_name(tmp_path):
    """Content-addressed upload names sort into a meaningless order. Sorting by them would
    shuffle the clip while every count in every gate still read correctly — and in a
    cascade the shuffle would also cross group boundaries, so the check runs end to end
    rather than on `build` alone. The map is deliberately reverse-ordered by server name."""
    uploads = {f"{i:05d}.png": f"{(80 - i):064x}.png" for i in range(81)}
    p = tmp_path / "uploads.json"
    p.write_text(json.dumps(uploads), encoding="utf-8")
    out = tmp_path / "route"
    B.main([f"--uploads={p}", f"--out={out}"])
    rec = json.loads((out / "E13-cascade-payload-record.json").read_text(encoding="utf-8"))
    assert rec["frame_order"] == [f"{i:05d}.png" for i in range(81)]
    wf = json.loads((out / "E13-cascade.api.json").read_text(encoding="utf-8"))
    assert wf[str(B.FIRST_IMAGE_ID)]["inputs"]["image"] == uploads["00000.png"]
    assert wf[str(B.FIRST_IMAGE_ID + 80)]["inputs"]["image"] == uploads["00080.png"]
    # the group that owns frame 27 is the SECOND group, at its slot 0
    assert wf["401"]["inputs"]["images.image0"] == [str(B.FIRST_IMAGE_ID + 27), 0]


def test_two_local_frames_uploading_to_one_object_raises(tmp_path):
    """Content addressing dedupes identical bytes: two identical frames come back as one
    name, and the cascade would bind the same object twice while every count read right."""
    uploads = {f"{i:05d}.png": "same.png" for i in range(81)}
    p = tmp_path / "uploads.json"
    p.write_text(json.dumps(uploads), encoding="utf-8")
    with pytest.raises(AS.AssemblyGate) as exc:
        B.main([f"--uploads={p}", f"--out={tmp_path / 'route'}"])
    assert "only 1 distinct server names" in str(exc.value)


def test_the_record_names_the_cap_as_inferred_rather_than_measured(tmp_path):
    """A number carried forward as a measurement when it is one error message's implication
    is exactly the inherited-claim failure this repo keeps paying for."""
    uploads = {f"{i:05d}.png": f"{i:064x}.png" for i in range(81)}
    p = tmp_path / "uploads.json"
    p.write_text(json.dumps(uploads), encoding="utf-8")
    out = tmp_path / "route"
    B.main([f"--uploads={p}", f"--out={out}"])
    rec = json.loads((out / "E13-cascade-payload-record.json").read_text(encoding="utf-8"))
    assert rec["inferred_slot_cap"] == 50
    assert "INFERRED" in rec["inferred_slot_cap_note"]
    assert "not a measurement" in rec["inferred_slot_cap_note"]
    assert rec["plan"] == [[0, 27], [27, 54], [54, 81]]
    assert rec["group_size"] == 27


# ------------------------------------------------- the andons survive optimization


PROBE = textwrap.dedent(
    """
    import json, sys
    sys.path.insert(0, sys.argv[1])
    from armature_core import assembly as AS
    import build_cascade_payload as B

    asserts_active = False
    try:
        assert False
    except AssertionError:
        asserts_active = True

    names = ["%064x.png" % i for i in range(81)]

    def ceiling():
        wf, _ = B.build(names, group_size=50)
        AS.gate_slot_ceiling(wf)

    def order():
        wf, gids = B.build(names)
        fi = wf[str(B.FINAL_BATCH_ID)]["inputs"]
        fi["images.image0"], fi["images.image1"] = fi["images.image1"], fi["images.image0"]
        AS.gate_cascade_topology(wf, 81, gids, B.FINAL_BATCH_ID, B.VIDEO_ID, B.SAVE_ID,
                                 "video")

    def dropped():
        wf, gids = B.build(names)
        del wf[str(B.FINAL_BATCH_ID)]["inputs"]["images.image2"]
        AS.gate_cascade_topology(wf, 81, gids, B.FINAL_BATCH_ID, B.VIDEO_ID, B.SAVE_ID,
                                 "video")

    def duplicated():
        wf, gids = B.build(names)
        wf["401"]["inputs"]["images.image0"] = wf["400"]["inputs"]["images.image0"]
        AS.gate_cascade_topology(wf, 81, gids, B.FINAL_BATCH_ID, B.VIDEO_ID, B.SAVE_ID,
                                 "video")

    def paid():
        wf, _ = B.build(names)
        wf["500"] = {"class_type": "Wan2ReferenceVideoApi", "inputs": {}}
        AS.gate_no_paid_nodes(wf)

    out = {"asserts_active": asserts_active, "raised": {}}
    for name, fn in {"ceiling": ceiling, "order": order, "dropped": dropped,
                     "duplicated": duplicated, "paid": paid}.items():
        try:
            fn()
            out["raised"][name] = "NO_RAISE"
        except AS.GateFailure:
            out["raised"][name] = "RAISED"
        except BaseException as exc:
            out["raised"][name] = "WRONG_ERROR:" + type(exc).__name__
    print("CASCADE " + json.dumps(out))
    """
)


def _run(tmp_path, *, flag=False, env_var=False):
    script = tmp_path / f"cas_probe_{int(flag)}_{int(env_var)}.py"
    script.write_text(PROBE, encoding="utf-8")
    env = dict(os.environ)
    env.pop("PYTHONOPTIMIZE", None)
    if env_var:
        env["PYTHONOPTIMIZE"] = "1"
    cmd = [sys.executable] + (["-O"] if flag else []) + [str(script), TOOLS]
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=180)
    assert proc.returncode == 0, proc.stderr
    line = [l for l in proc.stdout.splitlines() if l.startswith("CASCADE ")]
    assert line, proc.stdout + proc.stderr
    return json.loads(line[-1][len("CASCADE "):])


@pytest.mark.parametrize(
    "flag,env_var,label",
    [(False, False, "plain"), (True, False, "-O"), (False, True, "PYTHONOPTIMIZE=1")],
)
def test_every_cascade_andon_survives_optimization(tmp_path, flag, env_var, label):
    res = _run(tmp_path, flag=flag, env_var=env_var)
    for name, outcome in res["raised"].items():
        assert outcome == "RAISED", f"{label}/{name}: {outcome}"


def test_the_optimization_actually_took_effect(tmp_path):
    assert _run(tmp_path, flag=False)["asserts_active"] is True
    assert _run(tmp_path, flag=True)["asserts_active"] is False
    assert _run(tmp_path, env_var=True)["asserts_active"] is False


# ------------------------------------------------- the round-trip table


def test_the_cascade_introduces_no_class_the_table_does_not_carry():
    """The dispatch requires teaching the round-trip table any NEW class. The cascade adds
    none — it re-uses the five S03 already taught — so the check here is that the claim is
    true rather than that a row was added for its own sake. The table is looked up with
    `is None`, so an absent class halts."""
    import gate_saved_graph as GS

    wf, _ = _graph(4, group_size=2)
    for cls in sorted({n["class_type"] for n in wf.values()}):
        assert GS.WIDGET_INDEX.get(cls) is not None, f"{cls} has no widget row"


# ------------------------------------------------- the frame order is not a filename sort
#
# Wave 3, F-4a64a24e / F-53ee3299 / F-451d9008. Measured 2026-09-03, all three on this
# tool: an 81-entry map keyed 0.png..80.png printed "81 distinct LoadImage nodes -> 3 group
# batch(es) ... groups in frame order, every link resolved", "slot ceiling ... ceiling 27",
# a clean paid-node verdict and BUILD_CASCADE_OK, while the recorded frame_order ran
# ['0.png', '1.png', '10.png', ...] and 10.png sat in slot 2; --group=81 built ONE
# BatchImagesNode carrying 81 auto-grow slots and the ceiling gate reported "ceiling 81",
# because the cap was the same --group value that produced the node; and a refused build
# left its output directory on disk.


def test_an_unpadded_upload_map_is_refused_rather_than_lexicographically_sorted(tmp_path):
    uploads = {f"{i}.png": f"{i:064x}.png" for i in range(81)}
    p = tmp_path / "uploads.json"
    p.write_text(json.dumps(uploads), encoding="utf-8")
    with pytest.raises(AS.AssemblyGate) as exc:
        B.main([f"--uploads={p}", f"--out={tmp_path / 'route'}"])
    assert "10.png" in exc.value.evidence["malformed"]


def test_a_stray_non_frame_key_is_not_absorbed_as_a_fifth_frame(tmp_path):
    uploads = {f"{i:05d}.png": f"{i:064x}.png" for i in range(4)}
    uploads["reference.png"] = "ffff.png"
    p = tmp_path / "uploads.json"
    p.write_text(json.dumps(uploads), encoding="utf-8")
    with pytest.raises(AS.AssemblyGate) as exc:
        B.main([f"--uploads={p}", f"--out={tmp_path / 'route'}"])
    assert exc.value.evidence["malformed"] == ["reference.png"]


def test_a_within_group_slot_swap_is_caught_by_the_index_gate():
    """The clause `gate_cascade_topology` does not carry: it checks that the GROUP nodes
    appear in order and that every link resolves, over whatever list `names` happens to be.
    Two slots swapped INSIDE a group keeps every count and every group order right."""
    names = _names(81)
    wf, gids = B.build(names)
    plan = [(gid, start) for (start, _), gid in zip(AS.cascade_plan(81, AS.GROUP_SIZE),
                                                    gids)]
    assert B.gate_slot_frame_index(wf, names, plan, B.FIRST_IMAGE_ID)["verdict"]

    gi = wf[gids[1]]["inputs"]
    gi["images.image0"], gi["images.image1"] = gi["images.image1"], gi["images.image0"]
    assert _gates(wf, gids)["verdict"], "the topology gate must still see nothing wrong"
    with pytest.raises(AS.AssemblyGate) as exc:
        B.gate_slot_frame_index(wf, names, plan, B.FIRST_IMAGE_ID)
    assert "slot 0" in str(exc.value)


# ------------------------------------------------- the ceiling is the module's, not the CLI's


def test_a_group_above_the_module_ceiling_is_refused_end_to_end(tmp_path):
    """`assembly.py` states the contract: MAX_SLOTS_PER_NODE is equal to GROUP_SIZE so any
    widening of the group is a deliberate diff in both places. The CLI defeated it at
    runtime by passing cap=max(--group, 1), so the gate checked a direction the
    construction already bounds and 81 flat slots printed "ceiling 81"."""
    uploads = {f"{i:05d}.png": f"{i:064x}.png" for i in range(81)}
    p = tmp_path / "uploads.json"
    p.write_text(json.dumps(uploads), encoding="utf-8")
    with pytest.raises(AS.AssemblyGate) as exc:
        B.main([f"--uploads={p}", f"--out={tmp_path / 'route'}", "--group=81"])
    assert f"more than {AS.MAX_SLOTS_PER_NODE}" in str(exc.value)


def test_a_group_at_the_module_ceiling_still_builds(tmp_path):
    """The mutation that must NOT fire it."""
    uploads = {f"{i:05d}.png": f"{i:064x}.png" for i in range(81)}
    p = tmp_path / "uploads.json"
    p.write_text(json.dumps(uploads), encoding="utf-8")
    out = tmp_path / "route"
    B.main([f"--uploads={p}", f"--out={out}", f"--group={AS.MAX_SLOTS_PER_NODE}"])
    rec = json.loads((out / "E13-cascade-payload-record.json").read_text(encoding="utf-8"))
    per_node = rec["gates"]["CASCADE_ceiling"]["per_node"]
    assert max(per_node.values()) <= AS.MAX_SLOTS_PER_NODE


# ------------------------------------------------- a refuse leaves no output directory


def test_a_refused_build_leaves_no_output_directory(tmp_path):
    uploads = {f"{i:05d}.png": "same.png" for i in range(81)}
    p = tmp_path / "uploads.json"
    p.write_text(json.dumps(uploads), encoding="utf-8")
    out = tmp_path / "fresh" / "route"
    with pytest.raises(AS.AssemblyGate):
        B.main([f"--uploads={p}", f"--out={out}"])
    assert not out.exists()
    assert not out.parent.exists()
