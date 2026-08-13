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
from conftest import TOOLS


def _names(n):
    return [f"{i:064x}.png" for i in range(n)]


def _graph(n=81, **kw):
    return B.build(_names(n), **kw)


# ------------------------------------------------------------------ the free-chain andon


def test_the_built_chain_passes_both_clauses():
    wf = _graph()
    ev = AS.gate_no_paid_nodes(wf)
    assert set(ev["classes"]) == set(AS.ALLOWED_CLASSES)
    assert ev["name_pattern_flagged"] == []
    assert AS.gate_batch_topology(wf, 81, B.BATCH_ID, B.VIDEO_ID, B.SAVE_ID)["verdict"]


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
        AS.gate_batch_topology(wf, 4, B.BATCH_ID, B.VIDEO_ID, B.SAVE_ID)
    assert "bare `images` list" in str(exc.value)
    assert "dry_run does NOT catch this" in str(exc.value)


def test_a_short_batch_raises():
    """40 frames where 81 were uploaded: a shorter video, and nothing else notices."""
    wf = _graph(81)
    bi = wf[str(B.BATCH_ID)]["inputs"]
    for i in range(40, 81):
        del bi[f"images.image{i}"]
    with pytest.raises(AS.AssemblyGate) as exc:
        AS.gate_batch_topology(wf, 81, B.BATCH_ID, B.VIDEO_ID, B.SAVE_ID)
    assert "40 key(s), expected 81" in str(exc.value)


def test_a_link_bound_twice_raises_even_though_the_count_is_right():
    """The clause a count alone cannot make. 81 slots, 80 distinct sources: the video is
    81 frames long, the batch gate that counts images is satisfied, and one frame of the
    performance is silently doubled while another is gone."""
    wf = _graph(81)
    wf[str(B.BATCH_ID)]["inputs"]["images.image80"] = [str(B.FIRST_IMAGE_ID), 0]
    with pytest.raises(AS.AssemblyGate) as exc:
        AS.gate_batch_topology(wf, 81, B.BATCH_ID, B.VIDEO_ID, B.SAVE_ID)
    assert "distinct LoadImage node(s)" in str(exc.value)
    assert exc.value.evidence["distinct_sources"] == 80


def test_create_video_fed_from_somewhere_other_than_the_batch_raises():
    wf = _graph(4)
    wf[str(B.VIDEO_ID)]["inputs"]["images"] = [str(B.FIRST_IMAGE_ID), 0]
    with pytest.raises(AS.AssemblyGate) as exc:
        AS.gate_batch_topology(wf, 4, B.BATCH_ID, B.VIDEO_ID, B.SAVE_ID)
    assert "not the batch node's output" in str(exc.value)


def test_an_unwired_save_raises_because_create_video_saves_nothing_itself():
    """`CreateVideo` is `output_node: false` — measured. A graph whose SaveVideo is not
    fed by it runs to completion and writes no video at all."""
    wf = _graph(4)
    wf[str(B.SAVE_ID)]["inputs"]["video"] = [str(B.BATCH_ID), 0]
    with pytest.raises(AS.AssemblyGate) as exc:
        AS.gate_batch_topology(wf, 4, B.BATCH_ID, B.VIDEO_ID, B.SAVE_ID)
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
    uploads = {f"{i:05d}.png": f"{(80 - i):064x}.png" for i in range(81)}
    up = tmp_path / "uploads.json"
    up.write_text(json.dumps(uploads), encoding="utf-8")
    out = tmp_path / "out"
    B.main(["--uploads", str(up), "--out", str(out)])
    rec = json.loads((out / "S03-assembly-payload-record.json").read_text(encoding="utf-8"))
    assert rec["frame_order"] == [f"{i:05d}.png" for i in range(81)]
    wf = json.loads((out / "S03-assembly.api.json").read_text(encoding="utf-8"))
    assert wf[str(B.FIRST_IMAGE_ID)]["inputs"]["image"] == uploads["00000.png"]
    assert wf[str(B.FIRST_IMAGE_ID + 80)]["inputs"]["image"] == uploads["00080.png"]


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

PROBE = textwrap.dedent(
    """
    import json, sys
    sys.path.insert(0, sys.argv[1])
    import build_assembly_payload as B
    from armature_core import assembly as AS

    def _g(n=4):
        return B.build(["%064x.png" % i for i in range(n)])

    def paid():
        wf = _g(); wf["500"] = {"class_type": "Wan2ReferenceVideoApi", "inputs": {}}
        AS.gate_no_paid_nodes(wf)

    def bare():
        wf = _g()
        wf[str(B.BATCH_ID)]["inputs"] = {"images": [[str(B.FIRST_IMAGE_ID), 0]]}
        AS.gate_batch_topology(wf, 4, B.BATCH_ID, B.VIDEO_ID, B.SAVE_ID)

    def short():
        wf = _g()
        del wf[str(B.BATCH_ID)]["inputs"]["images.image3"]
        AS.gate_batch_topology(wf, 4, B.BATCH_ID, B.VIDEO_ID, B.SAVE_ID)

    def twice():
        wf = _g()
        wf[str(B.BATCH_ID)]["inputs"]["images.image3"] = [str(B.FIRST_IMAGE_ID), 0]
        AS.gate_batch_topology(wf, 4, B.BATCH_ID, B.VIDEO_ID, B.SAVE_ID)

    def unwired():
        wf = _g()
        wf[str(B.SAVE_ID)]["inputs"]["video"] = [str(B.BATCH_ID), 0]
        AS.gate_batch_topology(wf, 4, B.BATCH_ID, B.VIDEO_ID, B.SAVE_ID)

    out = {"optimize_flag": sys.flags.optimize, "asserts_active": __debug__, "raised": {}}
    for name, fn in {"paid": paid, "bare": bare, "short": short, "twice": twice,
                     "unwired": unwired}.items():
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
