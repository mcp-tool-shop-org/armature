"""Tests for the payload builder, and the pin that stops E03 from moving E02.

**The load-bearing test here is `test_E02_payload_bytes_have_not_moved`.** E02 has been run
and reported; its payloads were submitted and their sha256 recorded in the meta files beside
them. Adding E03's arms meant refactoring the shared builder, and a refactor that changed
what E02 emits would silently re-topologise an experiment whose conclusions are already in
the repo. The recorded hashes are the pin.

The rest cover the thing E03 changes that E02 could not exercise: an arm with no reference
image, and an arm whose control is one held pose repeated 33 times.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import build_payload as bp  # noqa: E402
from armature_core import assembly as AS  # noqa: E402
from armature_core import route_gates as RG  # noqa: E402

# Recorded in outputs/E02/payloads/*.meta.json from the runs that were actually submitted.
E02_PINNED_SHA256 = {
    "A1a": "89777df0cc30f0eb9df8b179818a9e06b2551f9dd1b2b05e0b1b377d9f84d6a6",
    "A2": "ab7b683ec04b025bbcc969c0240d36537fe85d7f73d10596c32b1e251c7a0fb8",
}

# The four `os.path.isfile("outputs/...")` guards that used to stand here resolved against
# `os.getcwd()`, not against the repo, and `outputs/` is gitignored — so the pin below and
# every E03/E06 comparison skipped on CI and on every clone with the reason "E02 upload
# records are gitignored output". The name maps are now committed under
# `tests/fixtures/uploads/` and conftest's session fixture points the builder at whichever
# copy exists, so these ride every run. See `conftest.upload_record`.


@pytest.mark.parametrize("arm,pinned", sorted(E02_PINNED_SHA256.items()))
def test_E02_payload_bytes_have_not_moved(arm, pinned):
    """E02 was submitted and reported on these exact bytes. They may not drift."""
    _wf, meta = bp.build(arm, "E02")
    assert meta["payload_sha256"] == pinned, (
        f"E02 {arm}'s payload changed. An experiment that has already been run and "
        f"reported must not be silently re-topologised by a later experiment's refactor."
    )


class TestE03Arms:
    def test_B1_and_B3_differ_only_in_which_control_they_carry(self):
        b1, m1 = bp.build("B1", "E03")
        b3, m3 = bp.build("B3", "E03")

        assert m1["positive"] == m3["positive"]
        assert m1["negative"] == m3["negative"]
        assert m1["seed"] == m3["seed"]
        assert m1["reference_image"] is None and m3["reference_image"] is None
        assert set(b1) == set(b3), "the two arms must have the same graph shape"

        differing = {k for k in b1 if b1[k] != b3[k]}
        # Only the 33 LoadImage nodes, the batch node's links, and the two prefixes.
        assert differing <= ({str(200 + i) for i in range(33)} | {"300", "301", "302", "114"})
        assert m1["payload_sha256"] != m3["payload_sha256"]

    def test_B3_carries_ONE_distinct_image_repeated_33_times(self):
        """The arm's definition. E02's builder demanded 33 distinct names and would have
        refused this outright."""
        wf, meta = bp.build("B3", "E03")
        assert meta["control"]["distinct_images"] == 1
        assert len(meta["control"]["server_names"]) == 33
        assert len(wf["300"]["inputs"]) == 33, "still 33 batch slots, all bound"
        assert len({v[0] for v in wf["300"]["inputs"].values()}) == 33, "33 distinct nodes"

    def test_B1_carries_33_distinct_images(self):
        assert bp.build("B1", "E03")[1]["control"]["distinct_images"] == 33

    def test_B2_is_the_null_and_carries_no_control_at_all(self):
        wf, meta = bp.build("B2", "E03")
        assert meta["control"] == "none (the null — no control_video)"
        assert "control_video" not in wf["49"]["inputs"]
        assert not any(n["class_type"] == "BatchImagesNode" for n in wf.values())

    def test_no_E03_arm_carries_a_reference_image(self):
        """Held constant (absent) across all three. Measured legal: WanVaceToVideo reports
        reference_image as required: false."""
        for arm in ("B1", "B2", "B3"):
            wf, meta = bp.build(arm, "E03")
            assert meta["reference_image"] is None
            assert "reference_image" not in wf["49"]["inputs"]
            assert "134" not in wf

    def test_every_E03_arm_keeps_the_lossless_tap_on_VAEDecode(self):
        for arm in ("B1", "B2", "B3"):
            assert bp.build(arm, "E03")[0]["302"]["inputs"]["images"] == ["8", 0]


# ------------------------------------------------------- the checks, driven to failure

def test_a_reference_that_appeared_in_one_arm_is_caught():
    """A reference present in one arm and absent in its sibling is a second variable, and
    nothing downstream would ever report it."""
    wf = {
        "49": {"class_type": "WanVaceToVideo", "inputs": {"reference_image": ["134", 0]}},
        "134": {"class_type": "LoadImage", "inputs": {"image": "x.png"}},
        "302": {"class_type": "SaveImage", "inputs": {"images": ["8", 0]}},
        "8": {"class_type": "VAEDecode", "inputs": {}},
    }
    with pytest.raises(bp.PayloadError, match="expects it absent"):
        bp.verify_topology(wf, "B1", use_control=False, expects_reference=False)


def test_a_missing_reference_is_caught_when_one_is_expected():
    wf = {
        "49": {"class_type": "WanVaceToVideo", "inputs": {}},
        "302": {"class_type": "SaveImage", "inputs": {"images": ["8", 0]}},
        "8": {"class_type": "VAEDecode", "inputs": {}},
    }
    with pytest.raises(bp.PayloadError, match="expects it present"):
        bp.verify_topology(wf, "A2", use_control=False, expects_reference=True)


def test_an_orphan_reference_node_is_caught():
    wf = {
        "49": {"class_type": "WanVaceToVideo", "inputs": {}},
        "134": {"class_type": "LoadImage", "inputs": {"image": "x.png"}},
        "302": {"class_type": "SaveImage", "inputs": {"images": ["8", 0]}},
        "8": {"class_type": "VAEDecode", "inputs": {}},
    }
    with pytest.raises(bp.PayloadError, match="nothing consumes it"):
        bp.verify_topology(wf, "B2", use_control=False, expects_reference=False)


def test_unknown_experiment_and_arm_raise():
    with pytest.raises(bp.PayloadError, match="unknown experiment"):
        bp.build("B1", "E99")
    with pytest.raises(bp.PayloadError, match="unknown arm"):
        bp.build("B1", "E02")


class TestE06Arms:
    """E06 = B1's control byte-identical + E02's reference. Two arms, one prompt apart.

    What would this look like if the code were wrong in the way these exist to catch?
    The failure E06 cannot survive is **a second variable** — a control that is not
    actually B1's, a reference that reached one arm and not the other, or a prompt that
    drifted while being copied. Each test below is one of those.
    """

    def test_D1_carries_B1s_control_BYTE_IDENTICALLY(self):
        """The whole experiment is 'B1 plus a reference'. If the control differs at all,
        two things changed and the run answers nothing."""
        b1, m1 = bp.build("B1", "E03")
        d1, m_d1 = bp.build("D1", "E06")

        assert m_d1["control"]["server_names"] == m1["control"]["server_names"]
        assert m_d1["control"]["frame_keys"] == m1["control"]["frame_keys"]
        assert m_d1["control"]["source_dir"] == m1["control"]["source_dir"]
        assert m_d1["control"]["normalization"] == m1["control"]["normalization"]
        assert m_d1["control"]["polarity"] == m1["control"]["polarity"]
        # the 33 LoadImage nodes and the batch node are the control, as emitted
        for nid in [str(200 + i) for i in range(33)] + ["300"]:
            assert d1[nid] == b1[nid], f"node {nid} differs from B1's"

    def test_D1_differs_from_B1_in_the_REFERENCE_AND_NOTHING_ELSE(self):
        """The one-variable claim, enforced on the emitted graph rather than asserted in
        a doc. Anything outside the reference node and the two output prefixes is a
        second variable."""
        b1, m1 = bp.build("B1", "E03")
        d1, m_d1 = bp.build("D1", "E06")

        assert m_d1["positive"] == m1["positive"], "D1's prompt must be B1's, unchanged"
        assert m_d1["negative"] == m1["negative"]
        assert m_d1["seed"] == m1["seed"]
        assert m_d1["resolution"] == m1["resolution"] and m_d1["length"] == m1["length"]
        assert m_d1["models"] == m1["models"]
        assert d1["3"]["inputs"] == b1["3"]["inputs"], "sampler settings must not move"
        assert d1["48"]["inputs"]["shift"] == b1["48"]["inputs"]["shift"]

        added = set(d1) - set(b1)
        assert added == {"134"}, f"D1 adds only the reference LoadImage; it added {added}"
        assert not (set(b1) - set(d1)), "D1 may not drop a node B1 had"

        differing = {k for k in b1 if b1[k] != d1[k]}
        # WanVaceToVideo gains reference_image; 301/302/114 carry the E06 filename prefix.
        assert differing == {"49", "301", "302", "114"}, differing
        vace_b1 = dict(b1["49"]["inputs"])
        vace_d1 = dict(d1["49"]["inputs"])
        assert vace_d1.pop("reference_image") == ["134", 0]
        assert vace_d1 == vace_b1, "strength/width/height/length must be untouched"

    def test_D2_differs_from_D1_in_the_PROMPT_AND_NOTHING_ELSE(self):
        d1, m_d1 = bp.build("D1", "E06")
        d2, m_d2 = bp.build("D2", "E06")

        assert m_d2["positive"] != m_d1["positive"], "D2 is defined by naming the character"
        assert m_d2["negative"] == m_d1["negative"]
        assert m_d2["reference_image"] == m_d1["reference_image"]
        assert m_d2["control"]["server_names"] == m_d1["control"]["server_names"]
        assert m_d2["seed"] == m_d1["seed"]
        assert set(d2) == set(d1)
        differing = {k for k in d1 if d1[k] != d2[k]}
        # node 6 is the positive CLIPTextEncode; the rest is the per-arm output prefix.
        assert differing == {"6", "301", "302", "114"}, differing
        assert d2["7"] == d1["7"], "the negative encode may not move"

    def test_BOTH_E06_arms_carry_the_SAME_reference_as_E02_used(self):
        """A reference that differs between arms is a second variable; a reference that is
        not E02's is a different experiment."""
        _wf_a1a, m_a1a = bp.build("A1a", "E02")
        names = set()
        for arm in ("D1", "D2"):
            wf, meta = bp.build(arm, "E06")
            assert wf["49"]["inputs"]["reference_image"] == ["134", 0]
            assert wf["134"]["class_type"] == "LoadImage"
            names.add(meta["reference_image"])
        assert len(names) == 1, "the two arms must share one reference"
        assert names == {m_a1a["reference_image"]}, "and it must be the plate A1a ran on"

    def test_D2s_prompt_names_the_character_and_still_names_no_motion(self):
        """D2's variable is identity, not performance. A prompt that also asked for the
        arm to rise would make P2 unreadable on this arm."""
        m = bp.build("D2", "E06")[1]
        assert "blackguard" in m["positive"].lower()
        for motion_word in ("raise", "raises", "lift", "turn", "turns", "moves", "waves"):
            assert motion_word not in m["positive"].lower().split(), m["positive"]
        # the scene half is byte-identical to D1's, so the diff is one clause
        tail = "Plain grey seamless background, even neutral lighting, full body in frame."
        assert m["positive"].endswith(tail)
        assert bp.build("D1", "E06")[1]["positive"].endswith(tail)

    def test_both_E06_arms_carry_33_distinct_control_images(self):
        for arm in ("D1", "D2"):
            assert bp.build(arm, "E06")[1]["control"]["distinct_images"] == 33

    def test_both_E06_arms_keep_the_lossless_tap_on_VAEDecode(self):
        for arm in ("D1", "D2"):
            assert bp.build(arm, "E06")[0]["302"]["inputs"]["images"] == ["8", 0]


def test_a_per_arm_prompt_override_does_not_leak_into_arms_without_one():
    """The override is the one structural change E06 made to a shared builder. If it
    leaked, E02's and E03's prompts would move and the byte pin above would be the only
    thing standing between a silent re-topologising and the wire."""
    assert "positive" not in bp.EXPERIMENTS["E02"]["arms"]["A1a"]
    assert "positive" not in bp.EXPERIMENTS["E03"]["arms"]["B1"]
    assert "positive" not in bp.EXPERIMENTS["E06"]["arms"]["D1"]
    assert bp.EXPERIMENTS["E06"]["positive"] == bp.EXPERIMENTS["E03"]["positive"]


def test_an_E06_arm_that_lost_its_reference_is_caught_by_the_existing_gate():
    """E06 commissions no gate because this one already exists. Driven to failure so the
    claim is demonstrated rather than asserted: strip the reference off an E06-shaped
    graph and `verify_topology` must refuse it."""
    wf = {
        "49": {"class_type": "WanVaceToVideo", "inputs": {"control_video": ["300", 0]}},
        "302": {"class_type": "SaveImage", "inputs": {"images": ["8", 0]}},
        "8": {"class_type": "VAEDecode", "inputs": {}},
        "300": {"class_type": "BatchImagesNode",
                "inputs": {f"images.image{i}": [str(200 + i), 0] for i in range(33)}},
        "301": {"class_type": "SaveImage", "inputs": {"images": ["300", 0]}},
    }
    for i in range(33):
        wf[str(200 + i)] = {"class_type": "LoadImage", "inputs": {"image": f"{i}.png"}}
    with pytest.raises(bp.PayloadError, match="expects it present"):
        # `control_names` is required on a control arm since wave 10 (F-6cbb7b35): the
        # slot->frame andon's population is the clip's frame order, which lives in the
        # upload map and not in the graph.
        bp.verify_topology(wf, "D1", use_control=True, expects_reference=True,
                           control_names=[f"{i}.png" for i in range(33)])


def _control_dir(tmp_path, name, distinct):
    """A local control directory holding `distinct` distinct PNGs across 33 frames.

    `_distinct_source_frames` hashes the bytes of every `.png` in the directory, so the
    content only has to differ — this is the expectation side of the check, and it is
    supplied here rather than depending on a gitignored render that only one rig has.
    """
    d = tmp_path / name
    d.mkdir()
    for i in range(33):
        (d / f"{i:05d}.png").write_bytes(b"png-" + str(i % distinct).encode())
    return str(d)


def _arm_pointed_at(monkeypatch, experiment, arm, *, uploads, source_dir):
    cfg = dict(bp.EXPERIMENTS[experiment])
    arms = dict(cfg["arms"])
    arms[arm] = dict(arms[arm], uploads=uploads, source_dir=source_dir)
    monkeypatch.setitem(bp.EXPERIMENTS, experiment, dict(cfg, arms=arms))



def _collapse_message(*, server_names, local_images):
    """The collapse clause's message with both counts pinned in their own ROLE.

    `\b` on the leading digit so `1 distinct server name` cannot match `31`, and the two
    numbers are on opposite sides of the clause so neither direction's pin can be satisfied
    by the other direction's message.
    """
    return (rf"map to \b{server_names} distinct server name\(s\), but .* holds "
            rf"\b{local_images} distinct image\(s\)")


def test_the_distinct_name_check_binds_in_BOTH_directions(tmp_path, monkeypatch):
    """A moving control that collapsed on upload must raise, and so must a static arm that
    did not collapse. E02's version only caught the first.

    Both directions are exercised here now. The expectation side used to come from a
    gitignored render directory, so on any tree without `outputs/` the whole check
    degraded to "at least one distinct image" — the branch it exists to make impossible —
    and the test skipped rather than saying so. Both sides are supplied by the fixture.
    """
    # Direction 1 — a MOVING control (33 distinct local images) whose upload collapsed to
    # one server name. This is the batch that arrives as one frame repeated 33 times.
    collapsed = tmp_path / "uploads_moving_collapsed.json"
    collapsed.write_text(json.dumps({f"{i:05d}": "same.png" for i in range(33)}))
    _arm_pointed_at(monkeypatch, "E03", "B1", uploads=str(collapsed),
                    source_dir=_control_dir(tmp_path, "moving", 33))
    # Both directions raise from ONE clause (build_payload.py:361-365), so the only thing
    # distinguishing them is the pair of numbers — and `pytest.raises(match=)` is
    # `re.search`, so a bare `"1 distinct server name"` also matches a message reading
    # "31 distinct server name" and would silently accept direction 2's message
    # (F-02683edb). The regex below pins each number IN ITS ROLE, and both roles are
    # derived from the fixture above rather than typed, so a fixture change moves the pin
    # with it instead of leaving one direction unpinned.
    with pytest.raises(bp.PayloadError,
                       match=_collapse_message(server_names=1, local_images=33)):
        bp.build("B1", "E03")

    # Direction 2 — a STATIC arm (1 distinct local image) whose uploads did NOT collapse.
    # It would not be the arm it claims to be, and E02's version let this through.
    fake = tmp_path / "uploads_static_broken.json"
    fake.write_text(json.dumps({f"{i:05d}": f"name{i}.png" for i in range(33)}))
    _arm_pointed_at(monkeypatch, "E03", "B3", uploads=str(fake),
                    source_dir=_control_dir(tmp_path, "static", 1))
    with pytest.raises(bp.PayloadError,
                       match=_collapse_message(server_names=33, local_images=1)):
        bp.build("B3", "E03")


# ------ the control directory has three states, not two (wave 8, F-42aed00f)


def test_the_local_control_count_distinguishes_absent_from_empty(tmp_path):
    """`return len(digests) or None` collapsed three different states of the local control
    directory into ONE sentinel. Measured directly before the fix: a directory that exists
    and is empty returned None, a directory that does not exist returned None,
    `source_dir=None` returned None, and a directory holding only non-PNG files returned
    None. The caller branches on `expected is None` and degrades to "at least one distinct
    server name" there, so every one of those states silently lost the distinct-frame
    binding the surrounding comment says exists precisely so a collapsed batch cannot pass.
    """
    assert bp._distinct_source_frames(None) is None
    assert bp._distinct_source_frames(str(tmp_path / "never-rendered")) is None

    empty = tmp_path / "empty"
    empty.mkdir()
    assert bp._distinct_source_frames(str(empty)) == 0

    no_pngs = tmp_path / "no_pngs"
    no_pngs.mkdir()
    (no_pngs / "notes.txt").write_text("not a frame", encoding="utf-8")
    assert bp._distinct_source_frames(str(no_pngs)) == 0

    assert bp._distinct_source_frames(_control_dir(tmp_path, "moving33", 33)) == 33
    assert bp._distinct_source_frames(_control_dir(tmp_path, "held", 1)) == 1


def test_a_named_but_empty_control_directory_refuses_rather_than_degrading(
        tmp_path, monkeypatch):
    """The failure the collapse admitted: an arm whose `source_dir` is present but holds no
    frames (cleaned up, moved, renamed, or converted out of `.png`) took the `expected is
    None` branch, where the check is only `got < 1`. All 33 uploads mapping to ONE server
    name would have been admitted — the exact collapsed batch the check exists to catch —
    and the payload record read the same either way."""
    empty = tmp_path / "cleaned_up"
    empty.mkdir()
    collapsed = tmp_path / "uploads_collapsed.json"
    collapsed.write_text(json.dumps({f"{i:05d}": "same.png" for i in range(33)}))
    _arm_pointed_at(monkeypatch, "E03", "B1", uploads=str(collapsed),
                    source_dir=str(empty))
    with pytest.raises(bp.PayloadError, match="holds no `.png` frames at all"):
        bp.build("B1", "E03")


def test_the_empty_directory_clause_does_not_fire_on_a_directory_that_has_frames(
        tmp_path, monkeypatch):
    """The mutation that must NOT fire it. Same arm, same uploads, one real frame in the
    directory — the held-pose arm this check was written not to refuse."""
    held = tmp_path / "uploads_held.json"
    held.write_text(json.dumps({f"{i:05d}": "same.png" for i in range(33)}))
    _arm_pointed_at(monkeypatch, "E03", "B1", uploads=str(held),
                    source_dir=_control_dir(tmp_path, "held_one", 1))
    _wf, meta = bp.build("B1", "E03")
    assert meta["control"]["distinct_images"] == 1


def test_the_record_says_which_branch_the_control_check_took(tmp_path, monkeypatch):
    """The record could not say whether the check bound at 33 or degraded to 1.
    `meta['control']` carried `distinct_images = len(set(control_names))` — the SERVER-name
    count, i.e. the unchecked side — and never the locally measured expectation nor whether
    the directory was readable at all. On this rig E02's A1b row already runs on the
    degraded branch (`control_480x832_inverted/depth_pershot` is absent), and nothing in its
    payload record says so."""
    ok = tmp_path / "uploads_moving.json"
    ok.write_text(json.dumps({f"{i:05d}": f"name{i}.png" for i in range(33)}))
    _arm_pointed_at(monkeypatch, "E03", "B1", uploads=str(ok),
                    source_dir=_control_dir(tmp_path, "moving_rec", 33))
    _wf, meta = bp.build("B1", "E03")
    control = meta["control"]
    assert control["source_dir_present"] is True
    assert control["source_dir_distinct_images"] == 33
    assert control["comparison"] == "33 distinct server name(s) == 33 distinct local image(s)"

    # And the degraded branch says it is degraded, in the record, with its own words.
    _arm_pointed_at(monkeypatch, "E03", "B1", uploads=str(ok),
                    source_dir=str(tmp_path / "never-rendered"))
    _wf, meta = bp.build("B1", "E03")
    control = meta["control"]
    assert control["source_dir_present"] is False
    assert control["source_dir_distinct_images"] is None
    assert "at least one distinct server name" in control["comparison"]


# =======================================================================================
# wave 10 — the control ORDER, and the licence clause that never reached this builder
# =======================================================================================
#
# F-6cbb7b35 (panel: CRITICAL) and F-9ee7536d (panel: HIGH). Both are about a population
# this tool read and never checked: the temporal order of the control batch, and the graph
# it emits.


def _pointed_at_map(tmp_path, monkeypatch, mapping, *, distinct=33, name="m.json"):
    """Point E03/B1 at a synthetic upload map with a local control dir that matches it."""
    up = tmp_path / name
    up.write_text(json.dumps(mapping), encoding="utf-8")
    _arm_pointed_at(monkeypatch, "E03", "B1", uploads=str(up),
                    source_dir=_control_dir(tmp_path, name.replace(".json", "_dir"),
                                            distinct))
    return up


def test_an_UNPADDED_upload_map_is_refused_rather_than_sorted(tmp_path, monkeypatch):
    """The measured defect. A 33-entry map keyed `0.png`..`32.png` was ACCEPTED and the
    frame order came back `['0.png', '1.png', '10.png', '11.png', ...]` — `10.png` in slot
    2 — because `keys = sorted(control)` sorts unpadded names lexicographically. Every
    count in every gate still read right: 33 keys, 33 slots, 33 distinct sources.

    The clause is `build_assembly_payload.frame_order`, imported rather than re-written.
    """
    _pointed_at_map(tmp_path, monkeypatch,
                    {f"{i}.png": f"name{i}.png" for i in range(33)}, name="unpadded.json")
    with pytest.raises(bp.PayloadError, match="not a zero-padded frame name"):
        bp.build("B1", "E03")


def test_a_NON_FRAME_key_is_refused_rather_than_absorbed_as_a_frame(tmp_path, monkeypatch):
    """32 real frames plus one `reference.png` used to be accepted as 33 frames, the
    non-frame key sorting last and becoming frame 32. The count clause (33 == 33) cannot
    see it and neither can `verify_topology`."""
    mapping = {f"{i:05d}": f"name{i}.png" for i in range(32)}
    mapping["reference.png"] = "ref.png"
    _pointed_at_map(tmp_path, monkeypatch, mapping, name="stray.json")
    with pytest.raises(bp.PayloadError, match="not a zero-padded frame name"):
        bp.build("B1", "E03")


def test_a_GAP_in_the_frame_indices_is_refused(tmp_path, monkeypatch):
    """Every key well formed, the count reading right, and every frame after the hole off
    by one. The second half of the clause, and it fails for a different reason than the
    first — so both halves are exercised."""
    mapping = {f"{i:05d}": f"name{i}.png" for i in range(34) if i != 7}
    _pointed_at_map(tmp_path, monkeypatch, mapping, name="gap.json")
    with pytest.raises(bp.PayloadError, match="are not 0"):
        bp.build("B1", "E03")


def test_the_carried_refusal_keeps_the_siblings_evidence_and_names_where_it_came_from(
        tmp_path, monkeypatch):
    """The clause is imported, not copied. The receipt has to say so, and it has to keep
    the gate's own evidence dict rather than degrading to a message."""
    _pointed_at_map(tmp_path, monkeypatch,
                    {f"{i}.png": f"n{i}.png" for i in range(33)}, name="carry.json")
    with pytest.raises(bp.PayloadError) as exc:
        bp.build("B1", "E03")
    ev = exc.value.evidence
    assert ev["carried_from"] == "build_assembly_payload.frame_order"
    assert ev["gate"] == "ASSEMBLY"
    assert ev["malformed"], "the sibling's measurement must survive the carry"
    assert isinstance(exc.value.__cause__, AS.AssemblyGate)


def test_a_WELL_FORMED_map_still_builds(tmp_path, monkeypatch):
    """The mutation that must NOT fire the clause: the shape every map on this rig uses."""
    _pointed_at_map(tmp_path, monkeypatch,
                    {f"{i:05d}": f"name{i}.png" for i in range(33)}, name="good.json")
    _wf, meta = bp.build("B1", "E03")
    assert meta["control"]["frame_keys"] == [f"{i:05d}" for i in range(33)]


# ---- the slot -> frame andon (the direction verify_topology's other clauses do not bound)


def _control_graph(names):
    """An E02/E03-shaped control graph: N LoadImage + batch + probe + lossless tap."""
    wf = {
        "49": {"class_type": "WanVaceToVideo", "inputs": {"control_video": ["300", 0]}},
        "302": {"class_type": "SaveImage", "inputs": {"images": ["8", 0]}},
        "8": {"class_type": "VAEDecode", "inputs": {}},
        "300": {"class_type": "BatchImagesNode",
                "inputs": {f"images.image{i}": [str(200 + i), 0]
                           for i in range(len(names))}},
        "301": {"class_type": "SaveImage", "inputs": {"images": ["300", 0]}},
    }
    for i, n in enumerate(names):
        wf[str(200 + i)] = {"class_type": "LoadImage", "inputs": {"image": n}}
    return wf


def test_a_PERMUTED_batch_link_is_refused_by_the_slot_to_frame_andon():
    """Two links swapped inside the batch leaves every clause above it correct: 33 dotted
    keys named `images.image0..32`, 33 distinct source nodes, `control_video` fed by the
    batch, the probe wired. The clip ships out of sequence and no count changes."""
    names = [f"{i:05d}.png" for i in range(33)]
    wf = _control_graph(names)
    wf["300"]["inputs"]["images.image3"], wf["300"]["inputs"]["images.image9"] = (
        wf["300"]["inputs"]["images.image9"], wf["300"]["inputs"]["images.image3"])
    with pytest.raises(bp.PayloadError, match="does not hold the frame"):
        bp.verify_topology(wf, "B1", use_control=True, expects_reference=False,
                           control_names=names)


def test_the_slot_to_frame_andon_passes_the_graph_the_builder_actually_emits():
    """The mutation that must not fire it — the real thing, unpermuted."""
    names = [f"{i:05d}.png" for i in range(33)]
    assert bp.verify_topology(_control_graph(names), "B1", use_control=True,
                              expects_reference=False, control_names=names) is True


def test_a_control_arm_verified_without_its_frame_order_is_REFUSED_not_skipped():
    """A caller allowed to omit `control_names` holds a skip flag for the andon: the gate
    would inspect nothing and return green. This is the population clause."""
    names = [f"{i:05d}.png" for i in range(33)]
    with pytest.raises(bp.PayloadError, match="without .control_names"):
        bp.verify_topology(_control_graph(names), "B1", use_control=True,
                           expects_reference=False)


# ---- Gate ROUTE reaches this builder now (F-9ee7536d)


def test_the_builder_records_gate_ROUTEs_evidence_on_every_arm():
    """This was the only one of the nine builders that never called `route_gates.verify`,
    so E02/E03/E04/E06's payload records carried no licence evidence at all."""
    for exp, arm in (("E02", "A1a"), ("E02", "A2"), ("E03", "B1"), ("E06", "D2"),
                     ("E04", "C-bright")):
        _wf, meta = bp.build(arm, exp)
        route = meta["gate_ROUTE_built"]
        assert route["gate"] == "ROUTE"
        assert [c["file"] for c in route["components"]] == [
            "wan2.1_vace_14B_fp16.safetensors", "wan_2.1_vae.safetensors",
            "umt5_xxl_fp16.safetensors"], route["components"]
        assert route["seed_clause_verdict"].startswith("CHECKED")
        assert "wan-vace" in route["generator_family_note"]


def test_a_licence_BANNED_node_CLASS_in_the_emitted_graph_is_refused(monkeypatch):
    """The class-level licence clause wave 8 gave `route_gates`, reaching this builder for
    the first time. Measured before the fix: splicing a `DWPreprocessor` node into the
    emitted graph was accepted by `verify_topology` without comment, while
    `route_gates.ruled_node_classes` reads that same class as BANNED.

    The graph is built entirely from module constants, so the node is spliced in at the
    only seam a future edit would come through — between `verify_topology` and Gate ROUTE.
    """
    real = bp.verify_topology

    def splice(wf, *a, **k):
        out = real(wf, *a, **k)
        wf["999"] = {"class_type": "DWPreprocessor", "inputs": {"image": ["200", 0]}}
        return out

    monkeypatch.setattr(bp, "verify_topology", splice)
    with pytest.raises(RG.RouteGate, match="BANNED"):
        bp.build("B1", "E03")


def test_gate_ROUTE_adds_evidence_and_not_nodes():
    """`verify` may not move the bytes an already-reported experiment was submitted on.
    The pin at the top of this file says so for E02; this says why it still holds."""
    wf, _meta = bp.build("A1a", "E02")
    before = json.dumps(wf, sort_keys=True)
    RG.verify(wf, family="wan", frame=(bp.WIDTH, bp.HEIGHT, bp.LENGTH))
    assert json.dumps(wf, sort_keys=True) == before


def test_the_success_line_is_the_halt_sentinels_prefix_with_OK(tmp_path, capsys):
    """One success convention across the 13 CPU tools: `<PREFIX>_OK `, the same PREFIX the
    `__main__` block prints on a halt. This tool printed a bare `BUILD_PAYLOAD ` line."""
    rc = bp.main(["--experiment=E03", "--arm=B1", f"--out={tmp_path / 'p' / 'B1.json'}",
                  "--subject=BLACKGUARD", "--no-canon"])
    assert rc == 0
    out = capsys.readouterr().out
    assert len([ln for ln in out.splitlines()
                if ln.startswith("BUILD_PAYLOAD_OK ")]) == 1


# ---------------------------------------------------------------- wave 12, F-4f72af05
# The meta path was `a.out.replace(".json", ".meta.json")` — a substring rewrite of the
# WHOLE path, on a `--out` whose spelling argparse constrains in no way. Two measured
# consequences, both under exit 0 or a partial write:
#
#   (a) `--out=<dir>/payload` (no extension): `replace` is a no-op, so the graph is written
#       and then OVERWRITTEN by the meta at the same path. One file existed afterwards; its
#       top-level keys were the RECORD's, and stdout still ended
#       `BUILD_PAYLOAD_OK {... "out": ".../payload"}` with exit 0. The file an operator
#       points a submission step at holds the record, and the graph whose sha256 that record
#       names reached no disk anywhere.
#   (b) `--out=<dir>/run.json.d/A.json`: `str.replace` rewrites EVERY occurrence, so the meta
#       was aimed at `<dir>/run.meta.json.d/A.meta.json` — a directory that does not exist.
#       The graph was already on disk, the tool died `FileNotFoundError`, printed
#       BUILD_PAYLOAD_HALT with `evidence: null` and exited 1: a partial write reported as a
#       crash.
#
# family: keyed on the SECOND-ARTIFACT path derivation (a sidecar path computed from an
# `--out`), via grep over `tools/*.py` for `splitext(<out>)[0] + <suffix>` and
# `<out>.replace(` → 7 sites: author_walk.py:655, lift_solve.py:345, make_ab_clip.py:181,
# make_crop_strip.py:244, make_lift_sheet.py:283, make_pick_sheet.py:311 all derive from the
# STEM; build_payload.py:739 was the only `str.replace`. The sibling's implementation is
# carried, not a seventh spelling.


def _e03_argv(out):
    return ["--experiment=E03", "--arm=B1", f"--out={out}", "--subject=BLACKGUARD",
            "--no-canon"]


def test_an_out_with_no_json_suffix_writes_TWO_files_and_the_graph_is_the_graph(tmp_path):
    """(a). The graph and its record are two artifacts and must land at two paths."""
    out = tmp_path / "p" / "payload"
    assert bp.main(_e03_argv(out)) == 0

    with open(out, encoding="utf-8") as fh:
        graph = json.load(fh)
    assert all("class_type" in n for n in graph.values()), (
        f"the file --out names holds {sorted(graph)[:6]}, not an API graph")
    assert "payload_sha256" not in graph, "the RECORD was written over the graph"

    meta = tmp_path / "p" / "payload.meta.json"
    assert meta.is_file(), sorted(os.listdir(tmp_path / "p"))
    with open(meta, encoding="utf-8") as fh:
        rec = json.load(fh)
    assert rec["payload_sha256"] and rec["arm"] == "B1"


def test_a_directory_named_like_the_suffix_does_not_move_the_meta_out_of_the_run(tmp_path):
    """(b). `str.replace` rewrote the DIRECTORY component too. The stem operation cannot:
    only the extension of the last component is replaced."""
    out = tmp_path / "run.json.d" / "A.json"
    assert bp.main(_e03_argv(out)) == 0
    assert (tmp_path / "run.json.d" / "A.meta.json").is_file(), sorted(
        p.name for p in (tmp_path / "run.json.d").iterdir())
    assert not (tmp_path / "run.meta.json.d").exists()


def test_the_two_artifacts_never_share_a_path_and_the_gate_says_so(tmp_path):
    """The andon on the direction the derivation does not bound: if the two names ever
    collide, one artifact silently replaces the other under a green OK line. The gate fires
    BEFORE either write and before `os.makedirs`, so a refusal leaves no run directory —
    the invariant `build_payload` already states for Gate CANON."""
    out = tmp_path / "fresh" / "payload.json"
    with pytest.raises(bp.PayloadOutHalt,
                       match=r"the graph and its record would both be written to") as exc:
        bp.gate_out_paths(str(out), meta_suffix=".json")
    assert exc.value.evidence["out"] == exc.value.evidence["meta"]
    assert exc.value.evidence["clause"] == "meta_path_equals_graph_path"
    assert not out.parent.exists()


def test_the_gate_is_reachable_from_main_and_leaves_no_directory(tmp_path, monkeypatch):
    """The gate lives inside the tool that performs the write, not beside it."""
    monkeypatch.setattr(bp, "META_SUFFIX", ".json")
    out = tmp_path / "fresh" / "payload.json"
    with pytest.raises(bp.PayloadOutHalt,
                       match=r"the graph and its record would both be written to"):
        bp.main(_e03_argv(out))
    assert not out.parent.exists()


def test_no_builder_derives_a_sidecar_path_by_whole_path_substring():
    """The family census. Keyed on BEHAVIOUR — can this expression rewrite a DIRECTORY
    component? — rather than on a spelling or a file list: every `str.replace(<".ext">,
    <"...json">)` in `tools/**` is collected by AST, and the ones nested inside an
    `os.path.join(...)` call are exempt because they operate on a path COMPONENT that has
    no directory to rewrite. The exemption is re-derived from the tree on every run and
    reported, never typed.

    Red on today's `build_payload.py:739`, and NOT red on `make_shotset_sheet.py:232`
    (`os.path.join(out_dir, filename.replace(".png", "-panels.json"))`, a basename) — which
    is the discrimination this census exists to make.
    """
    import ast

    TOOLS_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
    offenders, exempt = [], []
    for name in sorted(os.listdir(TOOLS_DIR)):
        if not name.endswith(".py"):
            continue
        tree = ast.parse(open(os.path.join(TOOLS_DIR, name), encoding="utf-8").read())
        # The components: every `replace` call that is an ARGUMENT to os.path.join.
        joined = set()
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "join"):
                for arg in node.args:
                    for sub in ast.walk(arg):
                        joined.add(id(sub))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "replace" and len(node.args) == 2
                    and all(isinstance(x, ast.Constant) and isinstance(x.value, str)
                            for x in node.args)
                    and node.args[0].value.startswith(".")
                    and node.args[1].value.endswith(".json")):
                (exempt if id(node) in joined else offenders).append(
                    f"{name}:{node.lineno}")
    assert offenders == [], (
        f"{offenders} derive a sidecar path by rewriting every occurrence of an extension "
        f"in a whole PATH; the six siblings use os.path.splitext(out)[0] + <suffix>. "
        f"Path COMPONENTS exempted this run: {exempt}")
    # WAVE 16 (instruments-measure): 232 -> 228. `make_shotset_sheet.ShotsetSheetError`
    # lost its normalising `__init__` (four lines, rule 5 / F-13333ef4) and every line
    # below it moved. Re-measured in the commit that moved it.
    assert exempt == ["make_shotset_sheet.py:228"], (
        f"the exemption set moved: {exempt}. Each member must be a `replace` whose result "
        f"is joined into a directory, so it cannot rewrite a directory component.")
