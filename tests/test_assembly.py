"""The assembly chain's andons — S03 Task C.

The chain is `LoadImage x N -> BatchImagesNode -> CreateVideo -> SaveVideo`, and it exists
to cost nothing. Two things can go wrong quietly:

* a class that bills gets into it, and the graph still runs and still produces a video;
* the batch mis-binds, and the graph still runs and still produces a video — a shorter one,
  or one with a duplicated frame, with every count in every other check reading correctly.

`dry_run` does not catch the second: E02 measured a bare `images` list VALIDATING with zero
warnings and being refused only by a real submission. That receipt is why the topology is
checked in code, and `test_the_bare_images_list_dry_run_validated` pins it in executable
form so nobody re-derives the weaker check.
"""

import json
import os
import subprocess
import sys
import textwrap

import pytest

import build_assembly_payload as B
from armature_core import assembly as AS
from armature_core import route_gates as RG
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


def _names(n):
    return [f"{i:064x}.png" for i in range(n)]


#: The default frame count for every fixture that goes through `B.build`.
#:
#: Wave 12, F-133f2bdc: it was 81 — the exact flat chain S03 watched pass pre-flight and die
#: at execution, and the shape `gate_flat_slot_ceiling` exists to refuse. The gate now lives
#: inside `build`, so the builder's own tests may not be built on a graph the builder
#: refuses. It is read from the tool's measured constant rather than typed, so the day
#: someone measures where the boundary between 8 and 81 actually is, these fixtures move
#: with it.
N = B.MEASURED_FLAT_SLOT_MAX


def _graph(n=N, **kw):
    return B.build(_names(n), **kw)


def _srcs(n=N):
    """The builder's own per-frame LoadImage node ids, in frame order.

    `gate_batch_topology` requires these: without them it could relate no slot to any
    frame, so its "every frame reaches the batch" verdict was a sentence rather than a
    check (F-6d125eb8).
    """
    return [str(B.FIRST_IMAGE_ID + i) for i in range(n)]


# ------------------------------------------------------------------ the free-chain andon


def test_the_built_chain_passes_both_clauses():
    wf = _graph()
    ev = AS.gate_no_paid_nodes(wf)
    assert set(ev["classes"]) == set(AS.ALLOWED_CLASSES)
    assert ev["name_pattern_flagged"] == []
    assert AS.gate_batch_topology(wf, N, B.BATCH_ID, B.VIDEO_ID, B.SAVE_ID,
                               expected_sources=_srcs(N))["verdict"]


def test_a_partner_node_in_the_graph_raises():
    """The defect the allowlist exists for: the r2v node E13 halted in front of, wired
    into a chain that is supposed to be free. It would run, it would produce a video,
    and it would bill 106-211 credits."""
    wf = _graph(4)
    wf["500"] = {"class_type": "Wan2ReferenceVideoApi",
                 "inputs": {"model.prompt": "a dancer", "seed": 1}}
    with pytest.raises(AS.AssemblyGate) as exc:
        AS.gate_no_paid_nodes(wf)
    assert "Wan2ReferenceVideoApi" in str(exc.value)
    assert "the allowlist does not name" in str(exc.value)


def test_an_innocuous_unlisted_class_also_raises():
    """The allowlist binds on membership, not on whether a class LOOKS paid.

    A free class nobody vetted is exactly the case a name-pattern check would wave
    through, and it is the reason the allowlist is the binding clause rather than the
    pattern.
    """
    wf = _graph(4)
    wf["500"] = {"class_type": "ImageScale", "inputs": {"width": 512}}
    with pytest.raises(AS.AssemblyGate) as exc:
        AS.gate_no_paid_nodes(wf)
    assert "ImageScale" in str(exc.value)


def test_widening_the_allowlist_to_a_partner_class_is_caught_by_the_second_clause():
    """The two clauses fail differently, and this is the case the allowlist alone cannot
    see: somebody adds a paid class to the allowlist, so membership passes. The name
    pattern is the second opinion on the allowlist itself."""
    wf = _graph(4)
    wf["500"] = {"class_type": "Wan2ReferenceVideoApi", "inputs": {}}
    widened = AS.ALLOWED_CLASSES + ("Wan2ReferenceVideoApi",)
    with pytest.raises(AS.AssemblyGate) as exc:
        AS.gate_no_paid_nodes(wf, allowed=widened)
    assert "the allowlist itself names" in str(exc.value)


def test_the_pattern_clause_has_unknown_recall_and_the_test_says_so():
    """Recorded rather than left implicit: a paid class whose name carries no marker
    passes the second clause. That is not a bug in the clause — it is why the clause is
    not the one doing the work, and it is stated in the module docstring."""
    assert not any(m in "KlingTextToVideoNode".lower() for m in AS.API_MARKERS)


# ------------------------------------------------------------------ the batch andon


def test_the_bare_images_list_dry_run_validated():
    """E02's measured receipt: a bare `images` list VALIDATES under dry_run with zero
    warnings and is refused only by a real submission. A dry_run PASS does not prove link
    sanity, so this is checked in code."""
    wf = _graph(4)
    wf[str(B.BATCH_ID)]["inputs"] = {"images": [[str(B.FIRST_IMAGE_ID + i), 0]
                                                for i in range(4)]}
    with pytest.raises(AS.AssemblyGate) as exc:
        AS.gate_batch_topology(wf, 4, B.BATCH_ID, B.VIDEO_ID, B.SAVE_ID,
                               expected_sources=_srcs(4))
    assert "bare `images` list" in str(exc.value)
    assert "dry_run does NOT catch this" in str(exc.value)


def test_a_short_batch_raises():
    """Half the frames where all of them were uploaded: a shorter video, and nothing else
    notices. Stated at 81 when this was written; the clause is about the DIFFERENCE, and the
    fixture is at `N` because the builder refuses to emit 81 slots (wave 12, F-133f2bdc)."""
    half = N // 2
    wf = _graph(N)
    bi = wf[str(B.BATCH_ID)]["inputs"]
    for i in range(half, N):
        del bi[f"images.image{i}"]
    with pytest.raises(AS.AssemblyGate) as exc:
        AS.gate_batch_topology(wf, N, B.BATCH_ID, B.VIDEO_ID, B.SAVE_ID,
                               expected_sources=_srcs(N))
    assert f"{half} key(s), expected {N}" in str(exc.value)


def test_a_link_bound_twice_raises_even_though_the_count_is_right():
    """The clause a count alone cannot make. 81 slots, 80 distinct sources: the video is
    81 frames long, the batch gate that counts images is satisfied, and one frame of the
    performance is silently doubled while another is gone."""
    wf = _graph(N)
    wf[str(B.BATCH_ID)]["inputs"][f"images.image{N - 1}"] = [str(B.FIRST_IMAGE_ID), 0]
    with pytest.raises(AS.AssemblyGate) as exc:
        AS.gate_batch_topology(wf, N, B.BATCH_ID, B.VIDEO_ID, B.SAVE_ID,
                               expected_sources=_srcs(N))
    assert "distinct LoadImage node(s)" in str(exc.value)
    assert exc.value.evidence["distinct_sources"] == N - 1


def test_create_video_fed_from_somewhere_other_than_the_batch_raises():
    wf = _graph(4)
    wf[str(B.VIDEO_ID)]["inputs"]["images"] = [str(B.FIRST_IMAGE_ID), 0]
    with pytest.raises(AS.AssemblyGate) as exc:
        AS.gate_batch_topology(wf, 4, B.BATCH_ID, B.VIDEO_ID, B.SAVE_ID,
                               expected_sources=_srcs(4))
    assert "not the batch node's output" in str(exc.value)


def test_an_unwired_save_raises_because_create_video_saves_nothing_itself():
    """`CreateVideo` is `output_node: false` — measured. A graph whose SaveVideo is not
    fed by it runs to completion and writes no video at all."""
    wf = _graph(4)
    wf[str(B.SAVE_ID)]["inputs"]["video"] = [str(B.BATCH_ID), 0]
    with pytest.raises(AS.AssemblyGate) as exc:
        AS.gate_batch_topology(wf, 4, B.BATCH_ID, B.VIDEO_ID, B.SAVE_ID,
                               expected_sources=_srcs(4))
    assert "CreateVideo is `output_node: false`" in str(exc.value)


# ------------------------------------------------------------------ frame ORDER


def test_frames_are_ordered_by_local_name_not_by_server_name(tmp_path):
    """The silent defect with no gate anywhere else in the chain.

    Upload names are content-addressed, so their sort order is arbitrary with respect to
    time. Order the batch by them and the clip's 81 frames are assembled in a shuffled
    sequence — 81 slots, 81 distinct sources, every gate above green, a video of the right
    length whose motion is noise. This test pins that the builder reads the LOCAL frame
    name as the ordering key.
    """
    # FIVE frames, not 81: wave 10 bounded this builder at MEASURED_FLAT_SLOT_MAX = 8 (the
    # largest flat batch S03 saw execute) and Gate L wants a 4n+1 count, so 5 is the largest
    # legal flat clip. The property under test is the ORDERING KEY and is independent of
    # width — the server names below still sort in reverse of the local ones, which is the
    # only thing that makes this test able to fail.
    n = 5
    uploads = {f"{i:05d}.png": f"{(n - 1 - i):064x}.png" for i in range(n)}
    up = tmp_path / "uploads.json"
    up.write_text(json.dumps(uploads), encoding="utf-8")
    out = tmp_path / "out"
    B.main(["--uploads", str(up), "--out", str(out)])
    rec = json.loads((out / "S03-assembly-payload-record.json").read_text(encoding="utf-8"))
    assert rec["frame_order"] == [f"{i:05d}.png" for i in range(n)]
    wf = json.loads((out / "S03-assembly.api.json").read_text(encoding="utf-8"))
    assert wf[str(B.FIRST_IMAGE_ID)]["inputs"]["image"] == uploads["00000.png"]
    assert wf[str(B.FIRST_IMAGE_ID + n - 1)]["inputs"]["image"] == uploads[f"{n - 1:05d}.png"]


def test_two_local_frames_uploading_to_one_object_raises(tmp_path):
    """Content addressing dedupes identical bytes. Two identical frames would come back
    as one name, the batch would bind the same object twice, and the topology gate's
    distinct-source clause fires downstream — but the upload map is where the fact is
    visible, so it is caught there with the clearer message."""
    uploads = {f"{i:05d}.png": "same.png" for i in range(3)}
    up = tmp_path / "uploads.json"
    up.write_text(json.dumps(uploads), encoding="utf-8")
    with pytest.raises(AS.AssemblyGate) as exc:
        B.main(["--uploads", str(up), "--out", str(tmp_path / "o")])
    assert "only 1 distinct server names" in str(exc.value)


# ------------------------------------------------- and none of them is an `assert`


# ------------------------------------------------- frame ORDER inside the batch (P3)


def test_a_transposed_slot_raises_even_though_every_count_is_right():
    """The defect this gate claimed to cover and did not.

    Its docstring's clause list named shuffling, but it collected sources in slot order and
    then only tested length and distinctness — so permuting two slots kept the count, kept
    every source distinct, and passed with a full verdict. The clip plays its frames in an
    order nobody chose and `clipcompare.order_check` (post-spend) is the next thing that
    could notice.
    """
    wf = _graph(8)
    bi = wf[str(B.BATCH_ID)]["inputs"]
    bi["images.image2"], bi["images.image6"] = bi["images.image6"], bi["images.image2"]
    with pytest.raises(AS.AssemblyGate) as exc:
        AS.gate_batch_topology(wf, 8, B.BATCH_ID, B.VIDEO_ID, B.SAVE_ID,
                               expected_sources=_srcs(8))
    assert "out of sequence" in str(exc.value)
    assert exc.value.evidence["n_expected_sources"] == 8


def test_an_expectation_that_is_not_the_frame_list_raises():
    """A short or duplicated expectation would let the ordering clause index off the end
    or compare a frame to itself, so the gate refuses the expectation first."""
    wf = _graph(4)
    with pytest.raises(AS.AssemblyGate) as exc:
        AS.gate_batch_topology(wf, 4, B.BATCH_ID, B.VIDEO_ID, B.SAVE_ID,
                               expected_sources=_srcs(3))
    assert "not the frame list" in str(exc.value)
    with pytest.raises(AS.AssemblyGate) as exc:
        AS.gate_batch_topology(wf, 4, B.BATCH_ID, B.VIDEO_ID, B.SAVE_ID,
                               expected_sources=["200", "200", "202", "203"])
    assert "not distinct" in str(exc.value)


def test_the_batch_gate_refuses_an_empty_frame_set():
    """`glb.compare_signatures` already refuses an empty pair because "a comparison over
    nothing must not report agreement". This gate did not: at n_frames=0 every count clause
    compared 0 to 0 and it returned a full success verdict over an empty clip."""
    wf = _graph(4)
    with pytest.raises(AS.AssemblyGate) as exc:
        AS.gate_batch_topology(wf, 0, B.BATCH_ID, B.VIDEO_ID, B.SAVE_ID,
                               expected_sources=[])
    assert "must not report agreement" in str(exc.value)
    assert exc.value.evidence["n_frames"] == 0


def test_a_node_without_a_class_type_raises_the_gate_not_a_typeerror():
    """`sorted()` over a set containing None raised `TypeError: '<' not supported between
    instances of 'str' and 'NoneType'`, so the failure path was broken in exactly one class
    of malformed graph — the caller got an untyped error with no gate id and no evidence
    where the andon belonged. `parts.py:155-159` records the identical defect."""
    wf = _graph(4)
    wf["500"] = {"inputs": {}}
    with pytest.raises(AS.AssemblyGate) as exc:
        AS.gate_no_paid_nodes(wf)
    assert "no `class_type`" in str(exc.value)
    assert exc.value.evidence["nodes_without_class_type"] == ["500"]

PROBE = textwrap.dedent(
    """
    import json, sys
    sys.path.insert(0, sys.argv[1])
    import build_assembly_payload as B
    from armature_core import assembly as AS

    def _g(n=4):
        return B.build(["%064x.png" % i for i in range(n)])

    def _s(n=4):
        return [str(B.FIRST_IMAGE_ID + i) for i in range(n)]

    def paid():
        wf = _g(); wf["500"] = {"class_type": "Wan2ReferenceVideoApi", "inputs": {}}
        AS.gate_no_paid_nodes(wf)

    def bare():
        wf = _g()
        wf[str(B.BATCH_ID)]["inputs"] = {"images": [[str(B.FIRST_IMAGE_ID), 0]]}
        AS.gate_batch_topology(wf, 4, B.BATCH_ID, B.VIDEO_ID, B.SAVE_ID,
                               expected_sources=_s(4))

    def short():
        wf = _g()
        del wf[str(B.BATCH_ID)]["inputs"]["images.image3"]
        AS.gate_batch_topology(wf, 4, B.BATCH_ID, B.VIDEO_ID, B.SAVE_ID,
                               expected_sources=_s(4))

    def twice():
        wf = _g()
        wf[str(B.BATCH_ID)]["inputs"]["images.image3"] = [str(B.FIRST_IMAGE_ID), 0]
        AS.gate_batch_topology(wf, 4, B.BATCH_ID, B.VIDEO_ID, B.SAVE_ID,
                               expected_sources=_s(4))

    def unwired():
        wf = _g()
        wf[str(B.SAVE_ID)]["inputs"]["video"] = [str(B.BATCH_ID), 0]
        AS.gate_batch_topology(wf, 4, B.BATCH_ID, B.VIDEO_ID, B.SAVE_ID,
                               expected_sources=_s(4))

    def transposed():
        wf = _g(8)
        bi = wf[str(B.BATCH_ID)]["inputs"]
        bi["images.image2"], bi["images.image6"] = bi["images.image6"], bi["images.image2"]
        AS.gate_batch_topology(wf, 8, B.BATCH_ID, B.VIDEO_ID, B.SAVE_ID,
                               expected_sources=_s(8))

    def empty():
        AS.gate_batch_topology(_g(), 0, B.BATCH_ID, B.VIDEO_ID, B.SAVE_ID,
                               expected_sources=[])

    def noclass():
        wf = _g(); wf["500"] = {"inputs": {}}
        AS.gate_no_paid_nodes(wf)

    out = {"optimize_flag": sys.flags.optimize, "asserts_active": __debug__, "raised": {}}
    for name, fn in {"paid": paid, "bare": bare, "short": short, "twice": twice,
                     "unwired": unwired, "transposed": transposed, "empty": empty,
                     "noclass": noclass}.items():
        try:
            fn()
            out["raised"][name] = "NO_RAISE"
        except AS.GateFailure:
            out["raised"][name] = "RAISED"
        except BaseException as exc:
            out["raised"][name] = "WRONG_ERROR:" + type(exc).__name__
    print("ASSEMBLY " + json.dumps(out))
    """
)


def _run(tmp_path, *, flag=False, env_var=False):
    script = tmp_path / f"as_probe_{int(flag)}_{int(env_var)}.py"
    script.write_text(PROBE, encoding="utf-8")
    env = dict(os.environ)
    env.pop("PYTHONOPTIMIZE", None)
    if env_var:
        env["PYTHONOPTIMIZE"] = "1"
    cmd = [sys.executable] + (["-O"] if flag else []) + [str(script), TOOLS]
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=180)
    assert proc.returncode == 0, proc.stderr
    line = [l for l in proc.stdout.splitlines() if l.startswith("ASSEMBLY ")]
    assert line, proc.stdout + proc.stderr
    return json.loads(line[-1][len("ASSEMBLY "):])


@pytest.mark.parametrize(
    "flag,env_var,label",
    [(False, False, "plain"), (True, False, "-O"), (False, True, "PYTHONOPTIMIZE=1")],
)
def test_every_assembly_andon_survives_optimization(tmp_path, flag, env_var, label):
    res = _run(tmp_path, flag=flag, env_var=env_var)
    for name, outcome in res["raised"].items():
        assert outcome == "RAISED", f"{label}/{name}: {outcome}"


def test_the_optimization_actually_took_effect(tmp_path):
    assert _run(tmp_path, flag=False)["asserts_active"] is True
    assert _run(tmp_path, flag=True)["asserts_active"] is False
    assert _run(tmp_path, env_var=True)["asserts_active"] is False


# ------------------------------------------------- the round-trip table row


def test_the_round_trip_table_now_carries_the_batch_class():
    """The table is looked up with `is None`, so an ABSENT class halts the check rather
    than skipping the node. `BatchImagesNode` had no row until this spec executed it."""
    import gate_saved_graph as GS

    assert GS.WIDGET_INDEX.get("BatchImagesNode") == {}
    for cls in AS.ALLOWED_CLASSES:
        assert GS.WIDGET_INDEX.get(cls) is not None, f"{cls} has no widget row"


# ------------------------------------------------- the frame order is not a filename sort
#
# Wave 3, F-4a64a24e. Both this file and the cascade took the clip's temporal order from
# `sorted(uploads)` over LOCAL filenames, and no gate downstream related a batch slot index
# to a frame index. Two ordinary inputs broke it silently, and both were measured on
# 2026-09-03:
#
# (a) unpadded names. An 81-entry map keyed 0.png..80.png built, printed a clean topology
#     verdict and BUILD_*_OK, while the recorded frame_order ran
#     ['0.png', '1.png', '10.png', '11.png', ...] and 10.png occupied slot 2.
# (b) a stray key. A 4-frame map plus one 'reference.png' was absorbed as a fifth frame,
#     n_frames read 5, and the same green verdict printed.


def test_an_unpadded_upload_map_is_refused_rather_than_lexicographically_sorted(tmp_path):
    uploads = {f"{i}.png": f"{i:064x}.png" for i in range(12)}
    up = tmp_path / "uploads.json"
    up.write_text(json.dumps(uploads), encoding="utf-8")
    with pytest.raises(AS.AssemblyGate) as exc:
        B.main(["--uploads", str(up), "--out", str(tmp_path / "o")])
    assert "00000.png" in str(exc.value)
    assert "0.png" in exc.value.evidence["malformed"]


def test_a_stray_non_frame_key_is_not_absorbed_as_an_extra_frame(tmp_path):
    uploads = {f"{i:05d}.png": f"{i:064x}.png" for i in range(4)}
    uploads["reference.png"] = "ffff.png"
    up = tmp_path / "uploads.json"
    up.write_text(json.dumps(uploads), encoding="utf-8")
    with pytest.raises(AS.AssemblyGate) as exc:
        B.main(["--uploads", str(up), "--out", str(tmp_path / "o")])
    assert exc.value.evidence["malformed"] == ["reference.png"]


def test_a_gap_in_the_frame_indices_is_refused(tmp_path):
    """Every key is well formed and the count reads right; frame 2 is simply absent, so
    every frame after it is off by one and nothing downstream can see it."""
    uploads = {"00000.png": "a.png", "00001.png": "b.png", "00003.png": "c.png"}
    up = tmp_path / "uploads.json"
    up.write_text(json.dumps(uploads), encoding="utf-8")
    with pytest.raises(AS.AssemblyGate) as exc:
        B.main(["--uploads", str(up), "--out", str(tmp_path / "o")])
    assert exc.value.evidence["missing"] == ["00002.png"]


def test_a_zero_padded_contiguous_map_still_builds(tmp_path):
    """The mutation that must NOT fire the refusal. A gate that refused every map would be
    a gate nobody could use, and its greenness would prove nothing."""
    uploads = {f"{i:05d}.png": f"{i:064x}.png" for i in range(5)}
    up = tmp_path / "uploads.json"
    up.write_text(json.dumps(uploads), encoding="utf-8")
    out = tmp_path / "o"
    B.main(["--uploads", str(up), "--out", str(out)])
    rec = json.loads((out / "S03-assembly-payload-record.json").read_text(encoding="utf-8"))
    assert rec["frame_order"] == [f"{i:05d}.png" for i in range(5)]


# ------------------------------------------------- slot k holds frame k


def test_the_slot_index_gate_catches_a_permuted_slot_that_topology_calls_clean():
    """`gate_batch_topology` checks that the slot keys are the right NAMES and that their
    sources are distinct LoadImages. It never relates slot k to frame k, so swapping two
    slots leaves every count right and the clip out of sequence."""
    names = [f"{i:064x}.png" for i in range(6)]
    wf = B.build(names)
    expected = [str(B.FIRST_IMAGE_ID + i) for i in range(6)]
    assert AS.gate_batch_topology(wf, 6, B.BATCH_ID, B.VIDEO_ID, B.SAVE_ID,
                                  expected_sources=expected)["verdict"]
    assert B.gate_slot_frame_index(wf, names, [(B.BATCH_ID, 0, 6)], B.FIRST_IMAGE_ID)["verdict"]

    bi = wf[str(B.BATCH_ID)]["inputs"]
    bi["images.image0"], bi["images.image1"] = bi["images.image1"], bi["images.image0"]
    # Wave-3 merge (coordinator): the topology gate gained the slot-k-is-frame-k clause on the
    # core-solvers branch (P3 side A) while this builder grew `gate_slot_frame_index` (side B),
    # so BOTH now refuse the permutation. One clause in two gates is a Stage B consolidation
    # item; until then the test states the merged truth rather than the pre-merge one.
    with pytest.raises(AS.AssemblyGate,
                       match=r"\[ASSEMBLY\] batch slot images\.image0 is bound to \['201'"):
        AS.gate_batch_topology(wf, 6, B.BATCH_ID, B.VIDEO_ID, B.SAVE_ID,
                               expected_sources=expected)
    with pytest.raises(AS.AssemblyGate) as exc:
        B.gate_slot_frame_index(wf, names, [(B.BATCH_ID, 0, 6)], B.FIRST_IMAGE_ID)
    assert "slot 0" in str(exc.value)


# ------------------------------------------------- a refuse leaves no output directory


def test_a_refused_build_leaves_no_output_directory(tmp_path):
    """Wave 3, F-451d9008. `os.makedirs` ran before --uploads was even read, so the
    duplicate-server-name gate fired with the directory already on disk — an empty run
    directory beside real ones, read later as a run that happened. Measured 2026-09-03."""
    uploads = {f"{i:05d}.png": "same.png" for i in range(4)}
    up = tmp_path / "uploads.json"
    up.write_text(json.dumps(uploads), encoding="utf-8")
    out = tmp_path / "fresh" / "run"
    with pytest.raises(AS.AssemblyGate,
                       match=r"\[ASSEMBLY\] the upload map carries 4 frames but only 1"):
        B.main(["--uploads", str(up), "--out", str(out)])
    assert not out.exists()
    assert not out.parent.exists()


# ------------------- the gate's population is the PLAN, not the graph (wave 6, F-de2bc940)


def _six():
    names = [f"{i:064x}.png" for i in range(6)]
    return names, B.build(names)


def test_the_span_is_the_population_so_a_vacuous_shape_cannot_pass():
    """`slots = [k for k in inputs if k.startswith("images.image")]` took the population
    from whatever dotted keys HAPPENED to exist while the verdict was built from
    `len(names)`. Measured on a 6-frame assembly graph: the batch replaced by a bare
    `images` LIST -> PASS, "6 frame(s) checked" (zero slots inspected); the tail dropped so
    only image0..2 remain -> PASS, "6 frame(s) checked" (three inspected); the batch node
    REMOVED from the graph outright -> PASS, "6 frame(s) checked" (nothing inspected,
    because `graph.get(str(nid)) or {}` turns an absent node into an empty loop). A
    contiguous truncation cannot fire the old gate at ANY length, because dropping N keys
    also shortens the loop by N.

    All three are caught upstream by `gate_batch_topology` at every production call site
    today — the severity is that the gate cannot stand on its own while its verdict says
    it can, and it is exported in `build_cascade_payload.__all__` for exactly that use.
    """
    names, wf = _six()
    plan = [(B.BATCH_ID, 0, 6)]
    assert B.gate_slot_frame_index(wf, names, plan, B.FIRST_IMAGE_ID)["verdict"]

    bare = json.loads(json.dumps(wf))
    bare[str(B.BATCH_ID)]["inputs"] = {"images": [[str(B.FIRST_IMAGE_ID + i), 0]
                                                  for i in range(6)]}
    with pytest.raises(AS.AssemblyGate) as exc:
        B.gate_slot_frame_index(bare, names, plan, B.FIRST_IMAGE_ID)
    assert "images" in str(exc.value)

    truncated = json.loads(json.dumps(wf))
    for k in range(3, 6):
        truncated[str(B.BATCH_ID)]["inputs"].pop(f"images.image{k}")
    with pytest.raises(AS.AssemblyGate) as exc:
        B.gate_slot_frame_index(truncated, names, plan, B.FIRST_IMAGE_ID)
    assert "images.image3" in str(exc.value) or "slot 3" in str(exc.value)

    gone = json.loads(json.dumps(wf))
    gone.pop(str(B.BATCH_ID))
    with pytest.raises(AS.AssemblyGate) as exc:
        B.gate_slot_frame_index(gone, names, plan, B.FIRST_IMAGE_ID)
    assert "BatchImagesNode" in str(exc.value) or str(B.BATCH_ID) in str(exc.value)


def test_a_node_of_the_wrong_class_in_the_slot_plan_is_refused():
    names, wf = _six()
    wf[str(B.BATCH_ID)]["class_type"] = "CreateVideo"
    with pytest.raises(AS.AssemblyGate) as exc:
        B.gate_slot_frame_index(wf, names, [(B.BATCH_ID, 0, 6)], B.FIRST_IMAGE_ID)
    assert "BatchImagesNode" in str(exc.value)


def test_the_verdict_reports_what_was_inspected_not_the_length_of_the_clip():
    names, wf = _six()
    ev = B.gate_slot_frame_index(wf, names, [(B.BATCH_ID, 0, 6)], B.FIRST_IMAGE_ID)
    assert ev["slots_inspected"] == 6
    assert "6 slot(s) inspected" in ev["verdict"]


# ------------- the plan must COVER the clip (wave 8, F-ad45bc42)


def _cascade81():
    """The real 81-frame cascade graph and its full, correct slot plan.

    `build_cascade_payload.build` is the production constructor; `AS.cascade_plan` is what
    both production call sites pair with the group ids. Deriving the fixture from them
    rather than typing spans keeps this test measuring the shipped shapes.
    """
    import build_cascade_payload as C

    names = [f"{i:064x}.png" for i in range(81)]
    wf, gids = C.build(names, fps=16.0, group_size=AS.GROUP_SIZE)
    plan = [(gid, start, stop) for (start, stop), gid
            in zip(AS.cascade_plan(len(names), AS.GROUP_SIZE), gids, strict=True)]
    return C, names, wf, plan


def test_the_full_plan_still_passes_and_says_what_it_inspected():
    """The mutation that must NOT fire the coverage clause: the plan the production call
    sites actually build."""
    C, names, wf, plan = _cascade81()
    ev = C.gate_slot_frame_index(wf, names, plan, C.FIRST_IMAGE_ID)
    assert ev["slots_inspected"] == 81
    assert ev["frames_in_clip"] == 81
    assert "81 slot(s) inspected against a clip of 81 frame(s)" in ev["verdict"]


@pytest.mark.parametrize("keep,inspected", [(0, 0), (1, 27), (2, 54)])
def test_a_plan_that_does_not_cover_the_clip_is_refused(keep, inspected):
    """The finding. The gate took its population from the caller's `slot_plan` and imposed
    no clause requiring that plan to cover the clip, so it returned a PASS verdict having
    inspected any number of slots INCLUDING ZERO — while the verdict string printed both
    numbers side by side ("{inspected} slot(s) inspected against a clip of {len(names)}
    frame(s)") with nothing comparing them.

    Measured 2026-09-04 on this exact 81-frame graph before the clause: `slot_plan=[]`
    returned "every slot across 0 batch node(s) holds the upload name of its own frame
    index, 0 slot(s) inspected against a clip of 81 frame(s)"; a one-group plan returned
    the same green sentence at 27 of 81; and a plan ONE GROUP SHORT — the shape an
    un-strict `zip` produces — returned it at 54 of 81.

    The two-group case is the reachable one: both production call sites build the plan
    through a `zip` of `cascade_plan(...)` against the group-id list, and `build_r2v_payload`
    is the arm that spends.
    """
    C, names, wf, plan = _cascade81()
    with pytest.raises(AS.AssemblyGate) as exc:
        C.gate_slot_frame_index(wf, names, plan[:keep], C.FIRST_IMAGE_ID)
    ev = exc.value.evidence
    assert ev["frames_planned"] == inspected
    assert ev["frames_in_clip"] == 81
    assert len(ev["frames_never_planned"]) > 0
    assert "does not cover the clip" in str(exc.value)


def test_a_plan_with_a_hole_in_the_middle_is_refused():
    """A gap between two spans: every slot the plan names holds its own frame, and 27
    frames of the clip were never looked at."""
    C, names, wf, plan = _cascade81()
    holed = [plan[0], plan[2]]
    with pytest.raises(AS.AssemblyGate) as exc:
        C.gate_slot_frame_index(wf, names, holed, C.FIRST_IMAGE_ID)
    assert exc.value.evidence["frames_never_planned"][0] == 27
    assert any("not contiguous" in p for p in exc.value.evidence["coverage_problems"])


def test_a_plan_that_covers_a_frame_twice_is_refused():
    """The other direction. Two spans over the same frames is not a clip this gate can
    vouch for either, and it used to inspect 108 slots against a clip of 81 and pass."""
    C, names, wf, plan = _cascade81()
    doubled = list(plan) + [plan[0]]
    with pytest.raises(AS.AssemblyGate) as exc:
        C.gate_slot_frame_index(wf, names, doubled, C.FIRST_IMAGE_ID)
    assert exc.value.evidence["frames_planned_twice"]


def test_a_plan_that_runs_past_the_end_of_the_clip_is_refused():
    C, names, wf, plan = _cascade81()
    over = list(plan[:-1]) + [(plan[-1][0], plan[-1][1], 200)]
    with pytest.raises(AS.AssemblyGate) as exc:
        C.gate_slot_frame_index(wf, names, over, C.FIRST_IMAGE_ID)
    assert exc.value.evidence["frames_planned_past_the_clip"]


def test_both_production_call_sites_pair_the_plan_STRICTLY():
    """The un-strict `zip` is what silently produced a short plan. Both call sites pass
    `strict=True` now, so the pairing raises rather than truncating.

    family: derived by AST over every `tools/*.py` call to `AS.cascade_plan` paired with a
    group-id list under `zip` -> 2 sites — tools/build_cascade_payload.py,
    tools/build_r2v_payload.py (the third reader, tools/build_assembly_payload.py, does not
    zip: it plans one batch node).
    """
    import ast

    sites = []
    for name in sorted(os.listdir(TOOLS)):
        if not name.endswith(".py"):
            continue
        src = open(os.path.join(TOOLS, name), encoding="utf-8").read()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name) and node.func.id == "zip"):
                continue
            if "cascade_plan" not in ast.get_source_segment(src, node):
                continue
            sites.append((name, [kw.arg for kw in node.keywords]))
    assert [s[0] for s in sites] == ["build_cascade_payload.py", "build_r2v_payload.py"], sites
    for name, kwargs in sites:
        assert "strict" in kwargs, f"{name} pairs cascade_plan with an un-strict zip"

    # And the pairing really does raise on a mismatched length, rather than truncating.
    with pytest.raises(ValueError, match=r"zip\(\) argument"):
        list(zip(AS.cascade_plan(81, AS.GROUP_SIZE), ["400", "401"], strict=True))


# ---- the .png case family's last builders site (wave 8, F-d85dafd9, routed by the
# ---- coordinator from instruments-measure)
#
# `frame_order` is the one site in this domain where the suffix belongs to an upload KEY
# rather than to a directory listing, and it was the last one still comparing case
# SENSITIVELY. Measured on this branch before the fix:
#
#   all `00000.png`  -> OK
#   all `00000.PNG`  -> AssemblyGate "4 key(s) that are not a zero-padded frame name"
#   mixed png/PNG    -> AssemblyGate, same clause, naming the two .PNG keys
#   bare `00000`     -> OK
#
# The `.PNG` map REFUSED, so nothing unsafe was admitted — but it refused through the wrong
# clause, telling an operator their keys are not zero-padded frame names when they are, and
# it made this gate's population rule disagree with every consumer of the same frames
# (`encode_control.py:126` and `invert_frames.py:70` both `n.lower().endswith('.png')`) and
# with both fetchers, whose EXTRA andon now lower-cases too.
#
# The shape classification takes each key's suffix VERBATIM rather than normalising it,
# because the invariant this gate exists for is SORT ORDER: '.PNG' sorts before '.png' in
# ASCII, so a map mixing the two cases genuinely has no single order and must still refuse —
# now through the mixed-shape clause, which is the sentence that describes it.


def _map(keys):
    return {k: f"server_{i}.png" for i, k in enumerate(keys)}


def test_an_upload_map_keyed_with_an_uppercase_suffix_is_a_frame_map():
    """The population rule, agreeing with the consumers and with both fetchers."""
    keys = [f"{i:05d}.PNG" for i in range(4)]
    assert B.frame_order(_map(keys)) == sorted(keys)


def test_the_lowercase_and_bare_shapes_are_unchanged():
    """The mutations that must NOT change: the eleven E02/E03 maps on this rig are keyed
    bare, and the cascade route keys its maps `00000.png`."""
    assert B.frame_order(_map([f"{i:05d}.png" for i in range(4)])) == \
        [f"{i:05d}.png" for i in range(4)]
    assert B.frame_order(_map([f"{i:05d}" for i in range(4)])) == \
        [f"{i:05d}" for i in range(4)]


def test_a_map_mixing_the_two_CASES_refuses_through_the_mixed_shape_clause():
    """It must still refuse — '.PNG' sorts before '.png', so a mixed-case map has no single
    order — but through the clause that names the real defect, not through 'these are not
    zero-padded frame names'."""
    keys = ["00000.PNG", "00001.png", "00002.PNG", "00003.png"]
    with pytest.raises(AS.AssemblyGate, match=r"mixes") as exc:
        B.frame_order(_map(keys))
    assert sorted(exc.value.evidence["suffixes"]) == [".PNG", ".png"]


def test_a_key_that_really_is_malformed_still_halts_on_the_malformed_clause():
    """The boundary on the fix: widening the SUFFIX's case must not widen anything else."""
    for bad in ("0.png", "00000.jpg", "frame_00000.png", "00000.png.bak"):
        with pytest.raises(AS.AssemblyGate, match=r"not a zero-padded frame name"):
            B.frame_order(_map([bad] + [f"{i:05d}.png" for i in range(1, 4)]))


def test_the_png_case_rule_is_the_same_one_its_consumers_use():
    """family: derived by grep over tools/ for a `.png` suffix test -> 5 sites —
    fetch_run.py (verify_downloads, the EXTRA andon), fetch_t2v_run.py (same function,
    imported not re-written), build_payload.py (`_distinct_source_frames`),
    encode_control.py:126 and invert_frames.py:70 (the consumers), plus this one,
    build_assembly_payload.py:96, which is the only member keyed on an upload KEY rather
    than a directory listing. SIBLING CARRIED: `fetch_run.verify_downloads`'s lower-cased
    comparison, settled with instruments-measure this wave. Every member treats a
    differently-cased suffix as the same population."""
    import fetch_run as F

    assert B.FRAME_KEY.match("00000.PNG"), "this gate's own population rule is narrower"
    assert F.verify_downloads is __import__("fetch_t2v_run").verify_downloads

    for name, line in (("encode_control.py", 126), ("invert_frames.py", 70)):
        src = open(os.path.join(TOOLS, name), encoding="utf-8").read().splitlines()
        assert ".lower()" in src[line - 1], f"{name}:{line} no longer lower-cases"


# ============================================================ wave 12, F-133f2bdc
# `gate_flat_slot_ceiling` was called in `build_and_write`, not in `build()` — the function
# that EMITS the BatchImagesNode — while the sibling gate in the same file,
# `gate_create_video_fps`, sits inside `build()` under the comment "The gate lives inside the
# function that emits the node, so an in-process caller cannot route around it the way a
# check in `main` would allow". The ceiling gate's own docstring claimed the stronger
# placement: "it is checked here, in the tool that authors the graph, before any submission".
#
# Measured in this worktree before the fix: `build(["%064x.png" % i for i in range(81)])`
# returned an 84-node graph whose node 400 carried 81 `images.image*` slots and raised
# nothing, while `gate_flat_slot_ceiling(wf, BATCH_ID)` on that same graph raised
# AssemblyGate. The suite's own default fixture was that shape — `_graph(n=81)` — so the
# builder's tests exercised a graph the builder refuses, which is why the four call sites
# below are re-based on the measured maximum.
#
# family: keyed on BEHAVIOUR — "a gate whose subject is a node this function emits" — by
# reading each gate call in this module against the function that writes the node it judges
# -> 2 sites: `gate_create_video_fps` (already inside `build`) and `gate_flat_slot_ceiling`
# (moved). The cascade builder's `AS.gate_slot_ceiling` judges the GROUP plan, which
# `build` takes as an argument rather than emitting, and stays where it is.


def test_build_itself_refuses_the_81_slot_flat_chain_S03_falsified():
    """The whole finding: an in-process caller received the exact shape S03 watched pass
    pre-flight and die at execution, from the builder that carries a gate against it."""
    with pytest.raises(AS.AssemblyGate, match=r"largest flat batch anyone has SEEN EXECUTE"):
        B.build(_names(81))


def test_the_ceiling_gate_is_the_LAST_thing_build_does_so_the_graph_is_complete():
    """Placed before the return rather than before the loop: the gate reads the emitted
    node, so it must run after the node exists — and it must still run before any caller
    can take the graph."""
    wf = B.build(_names(B.MEASURED_FLAT_SLOT_MAX))
    slots = [k for k in wf[str(B.BATCH_ID)]["inputs"] if k.startswith("images.image")]
    assert len(slots) == B.MEASURED_FLAT_SLOT_MAX


def test_the_record_still_carries_the_ceiling_evidence(tmp_path):
    """`build_and_write` re-runs the gate for the RECORD — the pattern
    `gate_create_video_fps` already uses — so the receipt states the contract that was
    checked rather than asserting a number nothing read."""
    # 5, not 8: Gate ROUTE's frame-legality clause requires a length of the form 4n+1, and
    # the write path runs it. The ceiling is still the number the RECORD is checked against.
    n = 5
    assert n <= B.MEASURED_FLAT_SLOT_MAX
    uploads = {f"{i:05d}.png": f"{i:064x}.png" for i in range(n)}
    up = tmp_path / "uploads.json"
    up.write_text(json.dumps(uploads), encoding="utf-8")
    out = tmp_path / "run"
    B.build_and_write(["--uploads", str(up), "--out", str(out)])
    rec = json.loads((out / "S03-assembly-payload-record.json").read_text(encoding="utf-8"))
    ev = rec["gates"]["FLAT_SLOT_CEILING"]
    assert ev["slots"] == n and ev["measured_max"] == B.MEASURED_FLAT_SLOT_MAX
    assert ev["boundary_located"] is False


def test_the_write_path_refuses_an_81_frame_upload_map_and_leaves_no_directory(tmp_path):
    """The gate moved INTO `build`, so the refusal now happens above `os.makedirs` on the
    write path too."""
    uploads = {f"{i:05d}.png": f"{i:064x}.png" for i in range(81)}
    up = tmp_path / "uploads.json"
    up.write_text(json.dumps(uploads), encoding="utf-8")
    out = tmp_path / "fresh" / "run"
    with pytest.raises(AS.AssemblyGate, match=r"largest flat batch anyone has SEEN EXECUTE"):
        B.build_and_write(["--uploads", str(up), "--out", str(out)])
    assert not out.exists() and not out.parent.exists()


def test_every_gate_this_module_calls_on_a_node_build_emits_is_called_INSIDE_build():
    """The census, keyed on the AST: for each gate call in this module, which function is
    it in, and does the graph it judges come from `build`? Red on today's tree, where
    `gate_flat_slot_ceiling` is called only from `build_and_write`."""
    import ast

    from conftest import TOOLS

    tree = ast.parse(open(os.path.join(TOOLS, "build_assembly_payload.py"),
                          encoding="utf-8").read())
    inside = {}
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        for node in ast.walk(fn):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                inside.setdefault(node.func.id, set()).add(fn.name)
    for gate in ("gate_create_video_fps", "gate_flat_slot_ceiling"):
        assert "build" in inside.get(gate, set()), (
            f"{gate} judges a node `build` emits and is called only from "
            f"{sorted(inside.get(gate, set()))}; an in-process caller routes around it")


# ============================================================ wave 12, F-60a1222b
# Both textless assemblers expressed "this graph has no sampler" with the UNCHECKED flag
# `require_pinned_seeds=False`, while `route_gates` grew `carries_no_sampler=True` as the
# CHECKED form of that exact sentence — which their own comments write in the checked form's
# words ("this graph has no noise-bearing node at all, so the seed clause has nothing to
# decide"). Measured in this worktree on the flat graph at a legal 5 frames with a
# KSamplerAdvanced spliced in as node 900: the builders' verbatim call returned GREEN with
# `seed_clause_verdict: "NOT CHECKED"`, while `RG.verify(same graph, carries_no_sampler=True,
# ...)` raises "the caller asserted this graph carries no sampler and it carries 1
# seed-bearing node(s) ... The assertion is checked, not obeyed". The flag also skipped
# `unrecorded_seed_sources` entirely: a node classed `SomeUnknownSamplerApi` rode the same
# call green with no `unrecorded_seed_sources` key in the evidence at all.
#
# REFUTED half, and recorded as refuted: no sampler can reach that call on either builder
# today, because `AS.gate_no_paid_nodes` runs first in both and its allowlist is closed. So
# the direction was bounded — but by a NEIGHBOURING module's allowlist rather than by the
# clause whose comment claims it, and a widening of ALLOWED_CLASSES silently un-blocked it.
#
# family: keyed on the CALL — every `RG.verify(...)` in this domain passing
# `require_pinned_seeds=False` — by grep over tools/build_*.py -> 2 sites
# (build_assembly_payload, build_cascade_payload). `verify` refuses the two keywords
# together, so it is a swap, not an addition.


def _with_a_sampler(wf):
    wf = dict(wf)
    wf["900"] = {"class_type": "KSamplerAdvanced",
                 "inputs": {"noise_seed": 7, "add_noise": "enable",
                            "control_after_generate": "fixed"}}
    return wf


def test_the_seed_clause_is_CHECKED_and_the_record_says_so(tmp_path):
    n = 5
    uploads = {f"{i:05d}.png": f"{i:064x}.png" for i in range(n)}
    up = tmp_path / "uploads.json"
    up.write_text(json.dumps(uploads), encoding="utf-8")
    out = tmp_path / "run"
    B.build_and_write(["--uploads", str(up), "--out", str(out)])
    rec = json.loads((out / "S03-assembly-payload-record.json").read_text(encoding="utf-8"))
    route = rec["gates"]["ROUTE"]
    assert route["seed_clause_verdict"].startswith("CHECKED"), route["seed_clause_verdict"]
    assert "NOT CHECKED" not in route["verdict"]
    assert "unrecorded_seed_sources" in route, (
        "the unrecorded-seed-source andon does not run under require_pinned_seeds=False")


def test_the_route_call_refuses_a_spliced_sampler_ON_ITS_OWN(tmp_path):
    """Independently of `gate_no_paid_nodes`, which is what bounded this direction before —
    a neighbouring module's allowlist, one widening away from un-blocking it."""
    wf = _with_a_sampler(B.build(_names(5)))
    with pytest.raises(RG.RouteGate, match=r"asserted this graph carries no sampler"):
        RG.verify(wf, family="wan", carries_no_sampler=True, frame=(B.WIDTH, B.HEIGHT, 5))


def test_no_builder_in_this_domain_still_says_NOT_CHECKED_where_it_means_no_sampler():
    """The family census, keyed on the CALL rather than on a comment: any `verify(...)`
    passing `require_pinned_seeds=False` in a builder is the unchecked spelling of a
    checkable claim."""
    import ast

    from conftest import TOOLS

    offenders = []
    for name in sorted(os.listdir(TOOLS)):
        if not (name.startswith("build_") and name.endswith(".py")):
            continue
        tree = ast.parse(open(os.path.join(TOOLS, name), encoding="utf-8").read())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            for kw in node.keywords:
                if (kw.arg == "require_pinned_seeds"
                        and isinstance(kw.value, ast.Constant)
                        and kw.value.value is False):
                    offenders.append(f"{name}:{node.lineno}")
    assert offenders == [], (
        f"{offenders} tell Gate ROUTE nobody looked, where what they mean is that the "
        f"graph carries no sampler — which `carries_no_sampler=True` states AND checks")
