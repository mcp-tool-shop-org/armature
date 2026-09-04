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
