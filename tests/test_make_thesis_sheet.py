"""make_thesis_sheet — the two defects E14 met, and the shapes behind them.

Both are the same failure class, which is why they get tests rather than a quiet edit: a
tool that bakes ONE experiment's meaning into a literal lies the first time it is reused,
and it lies in a place the reader has no reason to check (a caption, or a missing column).
"""

import os
import subprocess
import sys

import pytest

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tools", "make_thesis_sheet.py")


def _frames(d, n, size=(64, 36), colour=(80, 80, 80)):
    os.makedirs(d, exist_ok=True)
    for i in range(n):
        Image.new("RGB", size, colour).save(os.path.join(d, f"{i:05d}.png"))
    return d


@pytest.fixture
def scene(tmp_path):
    ctl = _frames(str(tmp_path / "ctl"), 8, colour=(30, 30, 30))
    arm = _frames(str(tmp_path / "arm"), 8, colour=(120, 60, 60))
    ref = str(tmp_path / "ref.png")
    Image.new("RGB", (64, 36), (200, 30, 200)).save(ref)
    return ctl, arm, ref, tmp_path


def _run(*args):
    out = subprocess.run([sys.executable, TOOL, *args], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return out.stdout


def test_reference_is_drawn_when_the_first_row_is_not_called_control(scene):
    """THE E14 defect. The reference used to be gated on the first row's label STARTING
    WITH 'CONTROL'. E14's first row is a BASELINE, so the plate was silently never drawn —
    the four-column panel the repo requires, quietly missing a column."""
    ctl, arm, ref, tmp = scene
    out = str(tmp / "sheet.png")
    _run(f"--control={ctl}", f"--arms=A:{arm}", f"--reference={ref}", f"--out={out}",
         "--frames=0,4", "--tile-height=36", "--control-label=BASELINE  not a control")
    sheet = Image.open(out).convert("RGB")
    # the reference is magenta and appears nowhere else in the sheet
    assert (200, 30, 200) in set(sheet.getdata()), (
        "the reference plate was not drawn on a first row whose label is not 'CONTROL'")


def test_reference_still_drawn_for_a_control_labelled_first_row(scene):
    ctl, arm, ref, tmp = scene
    out = str(tmp / "sheet2.png")
    _run(f"--control={ctl}", f"--arms=A:{arm}", f"--reference={ref}", f"--out={out}",
         "--frames=0,4", "--tile-height=36", "--control-label=CONTROL  depth")
    assert (200, 30, 200) in set(Image.open(out).convert("RGB").getdata())


def test_azimuth_captions_are_opt_in_now(scene):
    """A video route's frames are TIME. Labelling frame 4 of 8 as 'az 180d' states a camera
    orbit that never happened, in a caption nobody double-checks."""
    ctl, arm, ref, tmp = scene
    out = str(tmp / "sheet3.png")
    stdout = _run(f"--control={ctl}", f"--arms=A:{arm}", "--reference=none", f"--out={out}",
                  "--frames=0,4", "--tile-height=36")
    assert "THESIS_SHEET" in stdout
    # opt-in flag still available for the turnaround case it is actually true for
    out2 = str(tmp / "sheet4.png")
    _run(f"--control={ctl}", f"--arms=A:{arm}", "--reference=none", f"--out={out2}",
         "--frames=0,4", "--tile-height=36", "--azimuth-captions")


def test_no_reference_note_is_not_hardcoded_to_one_experiment(scene):
    """The --reference=none branch used to print E03's prose about WanVaceToVideo's
    reference_image socket — a measured claim about a node most routes never load."""
    ctl, arm, ref, tmp = scene
    out = str(tmp / "sheet5.png")
    _run(f"--control={ctl}", f"--arms=A:{arm}", "--reference=none", f"--out={out}",
         "--frames=0,4", "--tile-height=36",
         "--no-reference-note=REFERENCE: NONE.|this route uploads a start frame")
    src = open(TOOL, encoding="utf-8").read()
    assert "WanVaceToVideo" not in src, (
        "one experiment's measured claim is still baked into the shared composer")


def test_an_out_under_a_directory_that_does_not_exist_still_produces_the_sheet(scene):
    """`sheet.save(a.out)` with no `os.makedirs` anywhere in the file — the only writer
    among this domain's 42 tools with zero makedirs calls, while every sibling got one
    (`sheet_compose.py`, `rig_sheet_compose.py`, `make_cast_sheet.py`, and
    `make_lift_sheet.py` / `make_review_clip.py` already had theirs).

    Measured: `--out=outputs/E02/sheets/thesis.png` against a tree where that directory
    does not yet exist died with `FileNotFoundError` out of PIL's `Image.save` — on the
    panel assembled after the arms have been generated and paid for. This file's other
    tests all write into an existing `tmp_path`, so the direction was unexercised."""
    ctl, arm, ref, tmp = scene
    out = str(tmp / "E02" / "sheets" / "thesis.png")
    assert not os.path.isdir(os.path.dirname(out))
    _run(f"--control={ctl}", f"--arms=A:{arm}", f"--reference={ref}", f"--out={out}",
         "--frames=0,4", "--tile-height=36")
    assert os.path.isfile(out)


def test_every_writer_in_this_family_creates_its_own_output_directory():
    """The census: the repo's named rule ("Scripts create their own output directories.
    Two facet runs died on this."), asserted over the family rather than one file."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    without = []
    for mod in ("make_thesis_sheet", "make_lift_sheet", "make_gate0_sheet",
                "make_review_clip", "make_cast_sheet", "sheet_compose",
                "rig_sheet_compose", "make_identity_sheet", "make_plate",
                "fit_reference", "pack_pose_pack"):
        lines = open(os.path.join(root, "tools", f"{mod}.py"),
                     encoding="utf-8").read().splitlines()
        # a CALL, not the prose that records the defect: naming makedirs in a docstring
        # is exactly what this census must not accept as having made a directory
        if not any(ln.strip().startswith("os.makedirs(") for ln in lines):
            without.append(mod)
    assert without == [], without


# ------------------------------------------- two arms may not share one `--arms` label
#
# The pairing andon is armed with a dict comprehension keyed by the row TITLE —
# `gate_listing_pairing({title: names for title, _d, names in rows})` — while `rows` is a
# LIST built from `--arms=LABEL:dir,LABEL:dir`. Two arms sharing a label collapse to one
# key, and the earlier one's listing is discarded before the gate ever sees it.
#
# Measured 2026-09-04: a control numbered 00000..00002 with
# `--arms=A1:<dir numbered 00007..00009>,A1:<dir numbered 00000..00002>` built the sheet and
# printed `THESIS_SHEET ... 358x220`, exit 0, with the mis-numbered arm drawn as a row under
# captions f000/f001; the same two arms with distinct labels (`A1:` and `A2:`) raised
# `PairingGate`. The `require_frames` loop iterates the LIST and so does still check every
# row's index presence — it is only the frame-NUMBER agreement, the check that line exists
# for, that a duplicate label removes.
#
# The E02 thesis panel is the panel this repo says turns a demonstration into evidence, and
# a repeated `--arms` label was the one input shape that disarmed its andon.

sys.path.insert(0, os.path.join(ROOT, "tools"))

import make_thesis_sheet as MTS  # noqa: E402
from sheet_compose import SheetPopulationError  # noqa: E402


def _numbered(d, numbers, digits=5, base=(20, 20, 24)):
    os.makedirs(d, exist_ok=True)
    for k, n in enumerate(numbers):
        Image.new("RGB", (32, 24),
                  (base[0] + 20 * k, base[1] + 7 * k, base[2])).save(
            os.path.join(d, f"{n:0{digits}d}.png"))
    return d


def test_a_repeated_arms_label_is_refused_before_the_gate_is_armed(tmp_path):
    ctl = _numbered(str(tmp_path / "ctl"), [0, 1, 2])
    bad = _numbered(str(tmp_path / "bad"), [7, 8, 9])
    good = _numbered(str(tmp_path / "good"), [0, 1, 2])
    out = tmp_path / "thesis.png"
    with pytest.raises(SheetPopulationError, match=r"repeats the label") as e:
        MTS.main([f"--control={ctl}", f"--arms=A1:{bad},A1:{good}", "--reference=none",
                  f"--out={out}", "--frames=0,1", "--tile-height=24"])
    assert e.value.evidence["repeated"] == ["A1"], e.value.evidence
    assert e.value.evidence["arms"] == ["A1", "A1"]
    assert not out.exists()


def test_the_same_two_arms_under_distinct_labels_still_reach_the_pairing_gate(tmp_path):
    """The check the duplicate label was hiding: with distinct labels the mis-numbered arm
    is refused by the andon, which is what the panel exists to guarantee."""
    import measure_lift as ML

    ctl = _numbered(str(tmp_path / "ctl"), [0, 1, 2])
    bad = _numbered(str(tmp_path / "bad"), [7, 8, 9])
    good = _numbered(str(tmp_path / "good"), [0, 1, 2])
    with pytest.raises(ML.PairingGate):
        MTS.main([f"--control={ctl}", f"--arms=A1:{bad},A2:{good}", "--reference=none",
                  f"--out={tmp_path / 'thesis.png'}", "--frames=0,1", "--tile-height=24"])


def test_two_distinctly_labelled_good_arms_still_build(tmp_path):
    """The guard the other way: the refusal must not make a real two-arm panel
    unreachable."""
    ctl = _numbered(str(tmp_path / "ctl"), [0, 1, 2])
    a1 = _numbered(str(tmp_path / "a1"), [0, 1, 2])
    a2 = _numbered(str(tmp_path / "a2"), [0, 1, 2])
    out = tmp_path / "thesis.png"
    MTS.main([f"--control={ctl}", f"--arms=A1:{a1},A2:{a2}", "--reference=none",
              f"--out={out}", "--frames=0,1", "--tile-height=24"])
    assert out.exists()


def test_the_duplicate_label_refusal_survives_python_optimize(tmp_path):
    import subprocess
    import sys as _sys

    ctl = _numbered(str(tmp_path / "ctl"), [0, 1, 2])
    bad = _numbered(str(tmp_path / "bad"), [7, 8, 9])
    good = _numbered(str(tmp_path / "good"), [0, 1, 2])
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    code = (
        "import sys; sys.path.insert(0, r'%s')\n"
        "import make_thesis_sheet as TS\n"
        "from sheet_compose import SheetPopulationError\n"
        "try:\n"
        "    TS.main([r'--control=%s', r'--arms=A1:%s,A1:%s', '--reference=none',\n"
        "             r'--out=%s', '--frames=0,1', '--tile-height=24'])\n"
        "except SheetPopulationError:\n"
        "    print('RAISED')\n"
    ) % (os.path.join(root, "tools"), ctl, bad, good, tmp_path / "o.png")
    res = subprocess.run([_sys.executable, "-O", "-c", code], capture_output=True, text=True)
    assert "RAISED" in res.stdout, res.stderr


def test_every_panel_that_takes_labelled_arms_refuses_a_repeat():
    """Derived, not typed: every module in `tools/` whose parser defines an `--arms` flag
    must refuse a repeated label. One member today; a second joins by existing."""
    import argparse
    import ast
    import glob
    import importlib

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    derived = []
    for path in sorted(glob.glob(os.path.join(root, "tools", "*.py"))):
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call)
                    and getattr(node.func, "attr", "") == "add_argument"
                    and node.args and isinstance(node.args[0], ast.Constant)
                    and node.args[0].value == "--arms"):
                derived.append(os.path.basename(path)[:-3])
    assert sorted(set(derived)) == ["make_thesis_sheet"], sorted(set(derived))
    for mod_name in set(derived):
        tree = ast.parse(open(os.path.join(root, "tools", mod_name + ".py"),
                              encoding="utf-8").read())
        fn = next(n for n in tree.body
                  if isinstance(n, ast.FunctionDef) and n.name == "main")
        # An actual `raise` STATEMENT whose message names the repeat — read off the AST,
        # so a comment recording the defect cannot satisfy it (the shape that turned this
        # wave's `composite_reference` parser census green on the broken tool).
        raises = [node for node in ast.walk(fn) if isinstance(node, ast.Raise)]
        naming_a_repeat = [
            r for r in raises
            if any(isinstance(c, ast.Constant) and isinstance(c.value, str)
                   and "repeat" in c.value for c in ast.walk(r))]
        assert naming_a_repeat, (
            f"{mod_name}.main takes --arms and never raises on a repeated label; the "
            f"pairing gate is keyed by that label")
        assert argparse is not None and importlib is not None
