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

# Recorded in outputs/E02/payloads/*.meta.json from the runs that were actually submitted.
E02_PINNED_SHA256 = {
    "A1a": "89777df0cc30f0eb9df8b179818a9e06b2551f9dd1b2b05e0b1b377d9f84d6a6",
    "A2": "ab7b683ec04b025bbcc969c0240d36537fe85d7f73d10596c32b1e251c7a0fb8",
}

HAVE_E02_UPLOADS = os.path.isfile("outputs/E02/uploads_depth_pershot.json")
HAVE_E03_UPLOADS = os.path.isfile("outputs/E03/uploads_posearc.json")


@pytest.mark.skipif(not HAVE_E02_UPLOADS, reason="E02 upload records are gitignored output")
@pytest.mark.parametrize("arm,pinned", sorted(E02_PINNED_SHA256.items()))
def test_E02_payload_bytes_have_not_moved(arm, pinned):
    """E02 was submitted and reported on these exact bytes. They may not drift."""
    _wf, meta = bp.build(arm, "E02")
    assert meta["payload_sha256"] == pinned, (
        f"E02 {arm}'s payload changed. An experiment that has already been run and "
        f"reported must not be silently re-topologised by a later experiment's refactor."
    )


@pytest.mark.skipif(not HAVE_E03_UPLOADS, reason="E03 upload records are gitignored output")
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


@pytest.mark.skipif(not HAVE_E03_UPLOADS, reason="E03 upload records are gitignored output")
@pytest.mark.skipif(not HAVE_E02_UPLOADS, reason="E02 upload records are gitignored output")
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
        bp.verify_topology(wf, "D1", use_control=True, expects_reference=True)


@pytest.mark.skipif(not HAVE_E03_UPLOADS, reason="E03 upload records are gitignored output")
def test_the_distinct_name_check_binds_in_BOTH_directions(tmp_path, monkeypatch):
    """A moving control that collapsed on upload must raise, and so must a static arm that
    did not collapse. E02's version only caught the first."""
    # A "static" arm whose uploads did NOT collapse: 33 distinct names, 1 local image.
    fake = tmp_path / "uploads_static_broken.json"
    fake.write_text(json.dumps({f"{i:05d}": f"name{i}.png" for i in range(33)}))
    cfg = dict(bp.EXPERIMENTS["E03"])
    arms = dict(cfg["arms"])
    arms["B3"] = dict(arms["B3"], uploads=str(fake))
    monkeypatch.setitem(bp.EXPERIMENTS, "E03", dict(cfg, arms=arms))
    with pytest.raises(bp.PayloadError, match="33 distinct server name"):
        bp.build("B3", "E03")
