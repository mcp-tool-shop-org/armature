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


# ------------------------------------------------- --plate goes through the ONE parser
#
# `parse_plate` sits 70 lines above `main`, is called by `fit_reference`, `make_plate` and
# `pack_pose_pack`, and was bypassed by this module's own `main` — the module that HOLDS
# the alpha law's one implementation. Measured 2026-09-04: `--plate=999,-5,0` passed
# `main`'s only check (`len(plate) != 3`), `composite_over` clipped the channels to
# [255, 0, 0], and `A1-reference-record.json` recorded `"plate_rgb_srgb": [999, -5, 0]` —
# the artefact that says what the model was shown, naming a colour it was not shown, with
# the PNG and its sha256 internally consistent either way. `--plate=a,b,c` raised a bare
# `ValueError: invalid literal for int()`.


@pytest.mark.parametrize("bad", ["999,-5,0", "a,b,c", "1,2", "1,2,3,4", "1, 2"])
def test_a_plate_outside_the_parsers_range_or_shape_is_this_tools_refusal(tmp_path, bad):
    kit = _kit(tmp_path)
    out = tmp_path / "A1"
    with pytest.raises(CR.ReferenceGate) as e:
        CR.main([f"--kit={kit}", "--views=turn_0", f"--out={out}", f"--plate={bad}"])
    assert e.value.evidence["supplied"] == bad, e.value.evidence
    assert not out.exists(), "a refused plate left an output directory behind"


def test_an_empty_plate_is_refused_rather_than_composited_over_nothing(tmp_path):
    kit = _kit(tmp_path)
    out = tmp_path / "A1"
    with pytest.raises(CR.ReferenceGate) as e:
        CR.main([f"--kit={kit}", "--views=turn_0", f"--out={out}", "--plate="])
    assert e.value.evidence["supplied"] == ""


def test_a_valid_plate_still_round_trips_into_the_record(tmp_path):
    """The guard the other way: the refusal must not make a real plate unreachable."""
    kit = _kit(tmp_path)
    out = tmp_path / "A1"
    rec = CR.main([f"--kit={kit}", "--views=turn_0,turn_1", f"--out={out}",
                   "--plate=154,154,157"])
    assert rec["plate_rgb_srgb"] == [154, 154, 157]
    written = json.loads((out / "A1-reference-record.json").read_text(encoding="utf-8"))
    assert written["plate_rgb_srgb"] == [154, 154, 157]


def test_the_parser_is_the_module_s_own_and_not_a_second_copy():
    """`parse_plate` is what the three sibling producers call; `main` calls it too.

    Read off the AST rather than off the source text. Written first as a substring check
    (`"int(v) for v in a.plate.split" not in inspect.getsource(CR.main)`) it went RED on
    the fixed tool, because the comment recording the defect contains the defect's own
    text — the wave-8 class exactly: a census whose population is a substring in source
    describes something other than what it claims to.
    """
    import ast
    import inspect

    fn = ast.parse(inspect.getsource(CR.main).lstrip()).body[0]
    called = set()
    splits_the_flag = []
    for node in ast.walk(fn):
        if isinstance(node, ast.Call):
            f = node.func
            name = (f.id if isinstance(f, ast.Name)
                    else f.attr if isinstance(f, ast.Attribute) else "")
            called.add(name)
            if (name == "split" and isinstance(f, ast.Attribute)
                    and isinstance(f.value, ast.Attribute) and f.value.attr == "plate"):
                splits_the_flag.append(ast.dump(node))
    assert "parse_plate" in called, sorted(called)
    assert splits_the_flag == [], splits_the_flag


# --------------------------------------- every andon fires before the first byte is written
#
# The module docstring says the three andons all raise "before a byte is written". That was
# true of the FIRST view only: the gates ran inside the write loop, so a kit whose later
# view failed left composited plates behind — and `os.makedirs` sat above all three.


def test_a_kit_whose_later_view_has_no_real_alpha_writes_nothing_at_all(tmp_path):
    kit = _kit(tmp_path)
    # mutate the THIRD view into the baked-void defect, and re-pin it so Gate PIN passes
    arr = _rgba()
    arr[..., 3] = 255
    p = kit / "turn_2.png"
    Image.fromarray(arr, mode="RGBA").save(p)
    man = json.loads((kit / "turnaround_manifest.json").read_text(encoding="utf-8"))
    for v in man["views"]:
        if v["file"] == "turn_2.png":
            v["sha256"] = CR.sha256_file(str(p))
    (kit / "turnaround_manifest.json").write_text(json.dumps(man), encoding="utf-8")

    out = tmp_path / "A1"
    with pytest.raises(CR.ReferenceGate) as e:
        CR.main([f"--kit={kit}", "--views=turn_0,turn_1,turn_2", f"--out={out}"])
    assert e.value.evidence["gate"] == "ALPHA"
    assert not out.exists(), "views composited before the refusal were left on disk"


def test_a_whole_good_kit_still_writes_every_slot(tmp_path):
    """The guard the other way."""
    kit = _kit(tmp_path)
    out = tmp_path / "A1"
    rec = CR.main([f"--kit={kit}", "--views=turn_0,turn_1,turn_2,turn_4", f"--out={out}"])
    assert [e["slot"] for e in rec["views"]] == ["image1", "image2", "image3", "image4"]
    assert len(list(out.glob("A1_slot*.png"))) == 4
