"""Tests for the crop-strip cutter.

The box parser is what is defended. A still published at 3x is the artifact identity gets
judged on, so where it was cut from has to be recoverable exactly — and a parser that
silently dropped a malformed entry would publish a strip missing the frame it was made to
show, with nothing saying so.
"""

import pytest

from conftest import TOOLS  # noqa: F401
import make_crop_strip as C


def test_a_well_formed_box_list_parses_in_order():
    assert C.parse_boxes("0:1,2,3,4;32:10,20,30,40") == [
        (0, (1, 2, 3, 4)), (32, (10, 20, 30, 40))]


def test_trailing_and_empty_entries_are_tolerated():
    assert C.parse_boxes(" 0:1,2,3,4 ; ; ") == [(0, (1, 2, 3, 4))]


@pytest.mark.parametrize("bad", [
    "0-1,2,3,4",        # no colon
    "0:1,2,3",          # three coordinates
    "0:1,2,3,4,5",      # five
    "0:5,2,3,4",        # x1 <= x0
    "0:1,9,3,4",        # y1 <= y0
    "",                 # nothing at all
])
def test_a_malformed_entry_halts_rather_than_being_skipped(bad):
    """`CropStripError`, not `SystemExit`: this tool's refusals are typed and carry the
    measurement that fired them, so a caller catching the tool's own error catches all of
    them and a report can print the evidence. Changed 2026-09-04 with the frame-number
    keying below."""
    with pytest.raises(C.CropStripError, match=r"box entry|parsed to nothing") as e:
        C.parse_boxes(bad)
    assert e.value.evidence


def test_a_zero_extent_box_is_refused_not_clamped():
    """A 0-pixel crop enlarges to nothing and pastes as a seam. Refusing is the only
    outcome that cannot be mistaken for a tile."""
    with pytest.raises(C.CropStripError, match=r"non-positive extent"):
        C.parse_boxes("4:100,100,100,140")


# --------------------------------------------- `--boxes` names a frame NUMBER, not a slot
#
# `<frame>` was a POSITION into the sorted listing (`paths[idx]`) while being called a frame
# everywhere a reader sees it: the refusal said "frame {idx} requested", the tile label was
# `f{idx:03d}` and the sidecar recorded `{"frame": i}`. The module's stated purpose is
# provenance — "stated in the filename-visible provenance, so a later reader can re-cut the
# identical crop rather than guess where a published still came from".
#
# Measured 2026-09-04 on a directory numbered 00001..00003: `--boxes=0:0,0,20,20` cut
# `00001.png` (checked by pixel — the strip carries that frame's colour, and `00000.png`
# does not exist) and wrote a sidecar naming `"frame": 0`. Also measured:
# `--boxes=-1:0,0,20,20` was ACCEPTED — the `idx >= len(paths)` guard bounded only the high
# side — cutting the LAST frame and recording `"frame": -1`. The tool was in neither of the
# two family censuses in `tests/test_sheet_pairing.py`, so nothing caught it.

import json  # noqa: E402
import os  # noqa: E402

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402


def _frames(tmp, numbers, size=(40, 30)):
    d = tmp / "frames"
    d.mkdir(parents=True, exist_ok=True)
    for n in numbers:
        arr = np.zeros((size[1], size[0], 3), dtype=np.uint8)
        arr[..., 0] = 40 * n                       # each frame its own, checkable colour
        Image.fromarray(arr).save(d / f"{n:05d}.png")
    return str(d)


def test_a_number_the_directory_does_not_hold_is_refused_naming_the_range(tmp_path):
    frames = _frames(tmp_path, [1, 2, 3])
    out = tmp_path / "strip.png"
    with pytest.raises(C.CropStripError, match=r"holds frames 1\.\.3") as e:
        C.main([f"--frames={frames}", f"--out={out}", "--boxes=0:0,0,20,20"])
    ev = e.value.evidence
    assert (ev["asked"], ev["lo"], ev["hi"]) == (0, 1, 3)
    assert not out.exists()


def test_a_negative_frame_no_longer_cuts_the_last_one(tmp_path):
    """The guard bounded only the high side: `-1` cut the LAST frame and recorded -1."""
    frames = _frames(tmp_path, [1, 2, 3])
    with pytest.raises(C.CropStripError, match=r"holds frames 1\.\.3"):
        C.main([f"--frames={frames}", f"--out={tmp_path / 'strip.png'}",
                "--boxes=-1:0,0,20,20"])


def test_the_cut_frame_is_the_one_the_caller_named(tmp_path):
    """By PIXEL, not by name. On a directory numbered from 1, `--boxes=2:` used to cut
    `00003.png` — the third position — and the strip is the only place that shows it.

    The tile is pasted at `(gap, LABEL_H + gap)` = (8, 24) and every label is drawn BELOW
    it, so that pixel is the crop's own top-left and nothing else.
    """
    frames = _frames(tmp_path, [1, 2, 3])
    out = tmp_path / "strip.png"
    C.main([f"--frames={frames}", f"--out={out}", "--boxes=2:0,0,20,20", "--scale=1"])
    strip = np.asarray(Image.open(out).convert("RGB"))
    assert tuple(int(v) for v in strip[24, 8]) == (80, 0, 0), strip[24, 8]   # 40 * 2


def test_the_sidecar_records_the_number_and_the_file(tmp_path):
    """Re-cutting from the sidecar has to land on the same pixels."""
    frames = _frames(tmp_path, [1, 2, 3])
    out = tmp_path / "strip.png"
    C.main([f"--frames={frames}", f"--out={out}", "--boxes=2:0,0,20,20;3:1,1,21,21"])
    side = json.loads((tmp_path / "strip.json").read_text(encoding="utf-8"))
    assert [c["frame"] for c in side["crops"]] == [2, 3]
    assert [c["file"] for c in side["crops"]] == ["00002.png", "00003.png"]
    for crop in side["crops"]:
        assert os.path.isfile(os.path.join(side["frames"], crop["file"]))


def test_a_directory_with_no_numbered_frames_is_refused(tmp_path):
    d = tmp_path / "frames"
    d.mkdir()
    Image.new("RGB", (8, 8)).save(d / "strip_every8.png")
    with pytest.raises(C.CropStripError, match=r"no NNNNN\.png frames") as e:
        C.main([f"--frames={d}", f"--out={tmp_path / 'strip.png'}", "--boxes=0:0,0,4,4"])
    assert e.value.evidence["png_files"] == ["strip_every8.png"]


def test_the_crop_strip_refusal_survives_python_optimize(tmp_path):
    import subprocess
    import sys

    frames = _frames(tmp_path, [1, 2, 3])
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    code = (
        "import sys; sys.path.insert(0, r'%s')\n"
        "import make_crop_strip as C\n"
        "try:\n"
        "    C.main([r'--frames=%s', r'--out=%s', '--boxes=0:0,0,20,20'])\n"
        "except C.CropStripError:\n"
        "    print('RAISED')\n"
    ) % (os.path.join(root, "tools"), frames, tmp_path / "strip.png")
    res = subprocess.run([sys.executable, "-O", "-c", code], capture_output=True, text=True)
    assert "RAISED" in res.stdout, res.stderr


# ------------------------------------------------------------------------- the census
#
# The tool was in neither of the two family censuses in `tests/test_sheet_pairing.py`
# (`require_frames` and the silent-`continue` walks), so nothing in the suite noticed that
# it indexed a listing by position. This census derives its population from the tree.


def test_every_tool_that_indexes_frames_by_a_caller_supplied_number_keys_by_the_name():
    """Derived by AST over `tools/*.py`: every module defining a function whose name
    contains `by_number` builds its map from the file's own numeric stem, never from
    `enumerate` or a list index. Written as a walk rather than a list so a fourth such
    tool joins by existing."""
    import ast
    import glob

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    derived = {}
    for path in sorted(glob.glob(os.path.join(root, "tools", "*.py"))):
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and "by_number" in node.name:
                body = ast.dump(node)
                derived[os.path.basename(path)[:-3]] = body
    assert "make_crop_strip" in derived, sorted(derived)
    for mod, body in derived.items():
        assert "splitext" in body, mod
        assert "enumerate" not in body, mod


# --------------------------- the box is inside the frame it is cut from, and the flags parse
#
# **A box outside the frame was padded with black and recorded as though it were cut.**
# `build` refuses a frame NUMBER the run does not hold, and nothing bounded the BOX against
# the frame it is cut from: `Image.open(path).convert('RGB').crop(box)` pads a box outside
# the image with zeros rather than raising. Measured 2026-09-04 on three 64x64 frames,
# `--boxes="0:900,900,960,960" --scale=2`: exit 0, `CROP_STRIP ... 136x168`, a tile of 14400
# pure-black pixels, and a sidecar recording `{"frame": 0, "file": "00000.png",
# "box": [900,900,960,960]}`. The realistic arrival is a box cut for one route's resolution
# applied to another's (832x480 vs 1280x720): part image, part black padding, no refusal and
# no note — under a docstring whose stated reason for existing is that "a later reader can
# re-cut the identical crop rather than guess where a published still came from".
#
# **And two flag typos escaped the tool's one refusal shape.** `CropStripError`'s class
# docstring states there is "One refusal shape for this tool, carrying an evidence dict,
# rather than the bare `SystemExit` strings these checks used to raise". Measured:
# `--boxes="0:a,b,c,d"` died with `ValueError: invalid literal for int() with base 10: 'a'`,
# exit 1, no evidence dict, no flag named; `--scale=0` died inside PIL at
# `ValueError: height and width must be > 0` raised from `PIL/Image.py:2438`, after every
# requested frame had been opened. This is the escape `measure_floor._span` was given a
# refusal for, one tool over.


def _square(tmp, numbers, size=64):
    d = tmp / "sq"
    d.mkdir(parents=True, exist_ok=True)
    for n in numbers:
        arr = np.zeros((size, size, 3), dtype=np.uint8)
        arr[..., 0] = 40 + n
        Image.fromarray(arr).save(d / f"{n:05d}.png")
    return str(d)


def test_a_box_wholly_outside_the_frame_is_refused_not_padded(tmp_path):
    """THE fixture: the measured case. 14400 black pixels published as a native crop."""
    frames = _square(tmp_path, [0, 1, 2])
    out = tmp_path / "strip.png"
    with pytest.raises(C.CropStripError, match=r"box .* is not inside") as e:
        C.main([f"--frames={frames}", f"--out={out}", "--boxes=0:900,900,960,960",
                "--scale=2"])
    ev = e.value.evidence
    assert ev["box"] == [900, 900, 960, 960]
    assert ev["frame_size"] == [64, 64]
    assert ev["overhang"] == {"x0": 0, "y0": 0, "x1": 896, "y1": 896}
    assert not out.exists()


def test_a_box_half_outside_the_frame_is_refused_too(tmp_path):
    """The realistic arrival: a box cut for another route's resolution. Part image, part
    black padding — the half that IS image is what makes it survive a glance."""
    frames = _square(tmp_path, [0, 1, 2])
    with pytest.raises(C.CropStripError, match=r"box .* is not inside") as e:
        C.main([f"--frames={frames}", f"--out={tmp_path / 'strip.png'}",
                "--boxes=1:40,40,100,100"])
    assert e.value.evidence["overhang"]["x1"] == 36


def test_a_negative_origin_is_refused(tmp_path):
    """The other side of the same bound: PIL pads a negative origin just as silently."""
    frames = _square(tmp_path, [0, 1, 2])
    with pytest.raises(C.CropStripError, match=r"box .* is not inside"):
        C.main([f"--frames={frames}", f"--out={tmp_path / 'strip.png'}",
                "--boxes=--0:-4,0,20,20".replace("--0", "0")])


def test_a_box_exactly_at_the_edge_is_accepted(tmp_path):
    """The guard the other way: the refusal must not make a legitimate full-frame crop
    unreachable. `crop((0,0,W,H))` is the whole frame and nothing is padded."""
    frames = _square(tmp_path, [0, 1, 2], size=64)
    out = tmp_path / "strip.png"
    assert C.main([f"--frames={frames}", f"--out={out}", "--boxes=0:0,0,64,64",
                   "--scale=1"]) == 0
    assert out.exists()


def test_the_sidecar_records_the_frame_size_the_box_was_checked_against(tmp_path):
    """So a later reader can see the crop was inside the frame, not merely that a box was
    asked for."""
    frames = _square(tmp_path, [0, 1, 2])
    out = tmp_path / "strip.png"
    C.main([f"--frames={frames}", f"--out={out}", "--boxes=0:0,0,20,20"])
    side = json.loads((tmp_path / "strip.json").read_text(encoding="utf-8"))
    assert side["crops"][0]["frame_size"] == [64, 64]
    assert side["crops"][0]["box"] == [0, 0, 20, 20]


@pytest.mark.parametrize("bad,where", [
    ("0:a,b,c,d", "coordinate"),
    ("0:1,2,3,x", "coordinate"),
    ("f:1,2,3,4", "frame"),
])
def test_a_non_numeric_token_raises_the_tools_own_error(bad, where):
    """`int(...)` was unguarded on both the coordinates and the frame token: a plausible
    operator typo in the flag this tool exists to RECORD surfaced as a bare Python error
    naming neither the flag nor the shape it wanted."""
    with pytest.raises(C.CropStripError, match=r"--boxes") as e:
        C.parse_boxes(bad)
    assert e.value.evidence["entry"] == bad
    assert where in str(e.value)


@pytest.mark.parametrize("scale", [0, -1])
def test_a_scale_below_one_is_refused_before_a_frame_is_opened(tmp_path, scale):
    """The contract is an enlargement "by an integer factor with NEAREST"; a factor below
    1 is not one, and PIL's own error named neither the flag nor the value — after every
    requested frame had been opened."""
    frames = _square(tmp_path, [0, 1, 2])
    out = tmp_path / "strip.png"
    with pytest.raises(C.CropStripError, match=r"--scale") as e:
        C.main([f"--frames={frames}", f"--out={out}", "--boxes=0:0,0,20,20",
                f"--scale={scale}"])
    assert e.value.evidence["scale"] == scale
    assert not out.exists()


def test_the_crop_strip_refusals_survive_python_optimize(tmp_path):
    """They raise; they are not asserts."""
    import subprocess
    import sys

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    frames = _square(tmp_path, [0, 1, 2])
    code = (
        "import sys; sys.path.insert(0, r'%s')\n"
        "import make_crop_strip as C\n"
        "for argv, tag in ((['--frames=%s', '--out=%s', '--boxes=0:900,900,960,960'], 'BOX'),\n"
        "                  (['--frames=%s', '--out=%s', '--boxes=0:0,0,20,20',\n"
        "                    '--scale=0'], 'SCALE')):\n"
        "    try:\n"
        "        C.main(argv)\n"
        "    except C.CropStripError:\n"
        "        print(tag + '_RAISED')\n"
        "try:\n"
        "    C.parse_boxes('0:a,b,c,d')\n"
        "except C.CropStripError:\n"
        "    print('PARSE_RAISED')\n"
    ) % (os.path.join(root, "tools"),
         frames.replace("\\", "/"), str(tmp_path / "s1.png").replace("\\", "/"),
         frames.replace("\\", "/"), str(tmp_path / "s2.png").replace("\\", "/"))
    res = subprocess.run([sys.executable, "-O", "-c", code], capture_output=True, text=True)
    for tag in ("BOX_RAISED", "SCALE_RAISED", "PARSE_RAISED"):
        assert tag in res.stdout, res.stdout + res.stderr
