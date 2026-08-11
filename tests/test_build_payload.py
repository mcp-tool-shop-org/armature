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
