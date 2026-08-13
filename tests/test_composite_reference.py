"""The reference plates' andons — E13's re-arm, A1.

What goes in front of a hosted identity-lock tier is the whole experiment's input, and
three ways of getting it wrong leave no trace anywhere downstream:

* a view that is not the pinned file — every hash in the report is somebody else's;
* a master with no real alpha — the baked grey void the Director ruled against, which
  produces a perfectly ordinary-looking plate;
* a fully transparent master — a legal PNG of nothing, with a plausible hash.

Each fixture below is a good input mutated in exactly one place.
"""

import json

import numpy as np
import pytest
from PIL import Image

import composite_reference as CR


PLATE = CR.SURVEY_PLATE


def _rgba(h=12, w=8, alpha_lo=0, alpha_hi=255):
    """A master with a solid figure, a transparent surround and a soft edge."""
    a = np.full((h, w), alpha_lo, dtype=np.uint8)
    a[3:9, 2:6] = alpha_hi
    a[2, 2:6] = 120                                    # a real soft edge
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    rgb[3:9, 2:6] = (136, 98, 79)                      # the kit's wood tone
    rgb[2, 2:6] = (110, 86, 76)                        # S03's measured edge tone
    return np.dstack([rgb, a])


def _kit(tmp_path, views=("turn_0", "turn_1", "turn_2", "turn_4"), maker=_rgba):
    kit = tmp_path / "turn_rgba"
    kit.mkdir()
    entries = []
    for i, stem in enumerate(views):
        arr = maker()
        p = kit / f"{stem}.png"
        Image.fromarray(arr, mode="RGBA").save(p)
        entries.append({"file": f"{stem}.png", "azimuth_deg": 270.0 + 45 * i,
                        "sha256": CR.sha256_file(str(p))})
    (kit / "turnaround_manifest.json").write_text(
        json.dumps({"source": {"glb": "x.glb", "sha256": "deadbeef"}, "views": entries}),
        encoding="utf-8")
    return kit


# ------------------------------------------------------------------ the composite itself


def test_alpha_zero_gives_exactly_the_plate():
    rgba = np.zeros((4, 4, 4), dtype=np.uint8)
    rgba[..., :3] = 255
    out = CR.composite_over(rgba, PLATE)
    assert (out == np.asarray(PLATE, dtype=np.uint8)).all()


def test_alpha_255_gives_exactly_the_source_colour():
    rgba = np.zeros((4, 4, 4), dtype=np.uint8)
    rgba[..., :3] = (136, 98, 79)
    rgba[..., 3] = 255
    out = CR.composite_over(rgba, PLATE)
    assert (out == np.asarray((136, 98, 79), dtype=np.uint8)).all()


def test_a_half_alpha_edge_lands_between_the_two():
    rgba = np.zeros((1, 1, 4), dtype=np.uint8)
    rgba[..., :3] = (100, 100, 100)
    rgba[..., 3] = 128
    out = CR.composite_over(rgba, (200, 200, 200))[0, 0]
    assert all(148 <= c <= 152 for c in out), out


def test_the_composite_is_straight_not_premultiplied():
    """S03 measured the kit's alpha straight. If this formula were applied to
    premultiplied data every edge would darken, and no gate would fire — so the arithmetic
    is pinned here where it can be read."""
    rgba = np.zeros((1, 1, 4), dtype=np.uint8)
    rgba[..., :3] = (200, 200, 200)
    rgba[..., 3] = 64
    straight = 200 * (64 / 255) + 154 * (1 - 64 / 255)
    assert abs(int(CR.composite_over(rgba, PLATE)[0, 0, 0]) - straight) <= 1


# ------------------------------------------------------------------ Gate PIN


def test_a_view_that_does_not_match_the_manifest_raises(tmp_path):
    kit = _kit(tmp_path)
    m = json.loads((kit / "turnaround_manifest.json").read_text(encoding="utf-8"))
    m["views"][1]["sha256"] = "0" * 64
    (kit / "turnaround_manifest.json").write_text(json.dumps(m), encoding="utf-8")
    with pytest.raises(CR.ReferenceGate) as exc:
        CR.main([f"--kit={kit}", "--views=turn_0,turn_1", f"--out={tmp_path / 'o'}"])
    assert "turnaround manifest records" in str(exc.value)


def test_a_repainted_view_raises_even_though_the_file_is_a_valid_png(tmp_path):
    """The defect Gate PIN exists for: the file still opens, still has alpha, still
    composites — and it is not the picture the manifest pinned."""
    kit = _kit(tmp_path)
    arr = np.asarray(Image.open(kit / "turn_2.png")).copy()
    arr[4, 3, :3] = (255, 0, 0)
    Image.fromarray(arr, mode="RGBA").save(kit / "turn_2.png")
    with pytest.raises(CR.ReferenceGate):
        CR.main([f"--kit={kit}", "--views=turn_2", f"--out={tmp_path / 'o'}"])


def test_a_view_the_manifest_does_not_name_raises(tmp_path):
    kit = _kit(tmp_path)
    with pytest.raises(CR.ReferenceGate) as exc:
        CR.main([f"--kit={kit}", "--views=turn_9", f"--out={tmp_path / 'o'}"])
    assert "no view named" in str(exc.value)


# ------------------------------------------------------------------ Gate ALPHA


def test_a_flat_255_master_raises_with_the_baked_void_reason(tmp_path):
    """`turn_final`'s exact defect: RGBA in mode, alpha 255 everywhere, a grey void baked
    into the RGB. It composites to something that looks entirely normal."""
    def maker():
        arr = _rgba()
        arr[..., 3] = 255                              # flat 255 EVERYWHERE, edge included
        return arr

    kit = _kit(tmp_path, views=("turn_0",), maker=maker)
    with pytest.raises(CR.ReferenceGate) as exc:
        CR.main([f"--kit={kit}", "--views=turn_0", f"--out={tmp_path / 'o'}"])
    assert "baked void" in str(exc.value)


def test_a_master_with_nothing_fully_opaque_raises(tmp_path):
    kit = _kit(tmp_path, views=("turn_0",), maker=lambda: _rgba(alpha_hi=200))
    with pytest.raises(CR.ReferenceGate) as exc:
        CR.main([f"--kit={kit}", "--views=turn_0", f"--out={tmp_path / 'o'}"])
    assert "nothing is fully opaque" in str(exc.value)


# ------------------------------------------------------------------ Gate FLAT


def test_a_fully_transparent_master_raises(tmp_path):
    """A legal PNG of nothing. Alpha extrema (0, 255) is satisfied by one opaque pixel;
    this fixture keeps that pixel EQUAL to the plate so only Gate FLAT can see it."""
    def maker():
        arr = np.zeros((12, 8, 4), dtype=np.uint8)
        arr[0, 0, :3] = PLATE
        arr[0, 0, 3] = 255
        return arr

    kit = _kit(tmp_path, views=("turn_0",), maker=maker)
    with pytest.raises(CR.ReferenceGate) as exc:
        CR.main([f"--kit={kit}", "--views=turn_0", f"--out={tmp_path / 'o'}"])
    assert "no character in it" in str(exc.value)


# ------------------------------------------------------------------ the record


def test_slot_order_follows_the_views_argument_exactly(tmp_path):
    """The slot binding is NOT VISIBLE on this tier — what is sent per slot is all the
    record can carry, so the record must carry it in the order it was sent."""
    kit = _kit(tmp_path)
    out = tmp_path / "o"
    rec = CR.main([f"--kit={kit}", "--views=turn_0,turn_1,turn_2,turn_4", f"--out={out}"])
    assert rec["slot_order"] == ["image1", "image2", "image3", "image4"]
    assert [v["view"] for v in rec["views"]] == ["turn_0", "turn_1", "turn_2", "turn_4"]
    written = json.loads((out / "A1-reference-record.json").read_text(encoding="utf-8"))
    assert written["plate_rgb_srgb"] == list(PLATE)
    for v in written["views"]:
        assert v["source_sha256"] and v["composited_sha256"]


def test_a_reordered_views_argument_produces_a_different_slot_binding(tmp_path):
    """The negative control for the test above: if slot order were an artefact of sorting
    rather than of the argument, this would come back identical."""
    kit = _kit(tmp_path)
    rec = CR.main([f"--kit={kit}", "--views=turn_4,turn_0", f"--out={tmp_path / 'o2'}"])
    assert [v["view"] for v in rec["views"]] == ["turn_4", "turn_0"]


def test_the_plate_is_a_parameter_and_lands_in_the_record(tmp_path):
    kit = _kit(tmp_path, views=("turn_0",))
    rec = CR.main([f"--kit={kit}", "--views=turn_0", f"--out={tmp_path / 'o3'}",
                   "--plate=0,0,0"])
    assert rec["plate_rgb_srgb"] == [0, 0, 0]
    arr = np.asarray(Image.open(rec["views"][0]["composited"]))
    assert arr.shape[2] == 3, "the submitted plate carries no alpha channel"
    assert (arr[0, 0] == 0).all()
