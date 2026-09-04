"""The panels the Director judges on: the frames they SHOW are the frames they NAME.

Two defects, one family, over five tools.

**Positional pairing.** `make_lift_sheet` indexed three independent populations — the source
listing, the lifted listing and the detection rows — with the same `i` from `--frames`, with
no check that any two of them name the same frames. Measured 2026-09-03: a source numbered
00000..00004 beside a lifted directory holding the SAME five renders numbered 00001..00005
composed a sheet whose row `f000` showed source `00000.png` next to lifted `00001.png`,
printed `MAKE_LIFT_SHEET_OK {"frames": [0,1,2]}` and wrote a sidecar naming the requested
indices and no file at all. Exit 0. This is the off-by-one `measure_lift.gate_pairing` was
built for in wave 3 — and the gate landed in the measurement tool while the sheet the lift is
actually judged on kept the `zip`. `make_gate0_sheet` and `make_thesis_sheet` pair their
control and output listings the same way.

**Silent index dropping.** `if fi >= len(names): continue` drops a requested frame with
nothing on the panel or in the record saying so. Measured: a 3-frame control and 3-frame
output asked for `--frames=0,8,16,24` saved a ONE-column sheet, exit 0; when every requested
index is dropped the sheet dies instead at `cols[0][1].width` with a bare `IndexError`.
`make_identity_sheet` was given exactly this refusal in wave 3, because "dropping one
silently shows the Director fewer angles than were asked for"; four siblings kept the
`continue`.

Both checks are ONE implementation each — `measure_lift.gate_listing_pairing` (which
delegates to `gate_pairing`) and `sheet_compose.require_frames` (carried out of
`make_identity_sheet`) — and this file is parametrized over the tools so a new sheet joins
the family by being listed.
"""

import json
import os
import sys

import pytest
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "tools"))

import make_gate0_sheet as G0  # noqa: E402
import make_lift_sheet as LS  # noqa: E402
import make_review_clip as MRC  # noqa: E402
import make_startframe_sheet as SFS  # noqa: E402
import make_thesis_sheet as TS  # noqa: E402
import measure_lift as ML  # noqa: E402
import sheet_compose as SC  # noqa: E402

SIZE = (32, 24)


def _clip(d, numbers, base=(20, 20, 24), digits=3):
    """A render directory numbered as asked, each frame its own flat colour.

    Distinct per frame on purpose: a wrong pairing has to be visible in pixels, not only in
    a name — that is what makes the fixture able to catch the defect it exists for.
    """
    os.makedirs(d, exist_ok=True)
    for k, n in enumerate(numbers):
        colour = (base[0] + 20 * k, base[1] + 7 * k, base[2])
        Image.new("RGB", SIZE, colour).save(os.path.join(d, f"{n:0{digits}d}.png"))
    return d


def _plate(d):
    Image.new("RGB", SIZE, (0, 0, 0)).save(os.path.join(d, "empty_plate.png"))
    return d


def _detection(path, frames):
    rows = [{"frame": n, "file": f"{n:03d}.png", "fired": False,
             "image": [], "visibility": []} for n in frames]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"rows": rows}, fh)
    return path


# ----------------------------------------------------------- the pairing, made visible


def _lift_argv(tmp, src_numbers, lif_numbers, det_frames, frames="0,1", out=None):
    src = _plate(_clip(str(tmp / "src"), src_numbers))
    lif = _plate(_clip(str(tmp / "lif"), lif_numbers))
    det = _detection(str(tmp / "det.json"), det_frames)
    out = out or str(tmp / "sheet.png")
    return ["make_lift_sheet.py", f"--source={src}", f"--detection={det}",
            f"--lifted={lif}", f"--out={out}", f"--frames={frames}", "--tile-h=24",
            "--source-uncropped"], out


def test_a_lifted_directory_numbered_from_one_is_refused(tmp_path, monkeypatch):
    """THE fixture: the same five renders, numbered from 1 on one side. Counts match,
    every requested index resolves, and every row compares two different moments."""
    argv, out = _lift_argv(tmp_path, [0, 1], [1, 2], [0, 1])
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(ML.PairingGate) as e:
        LS.main()
    assert e.value.evidence["gate"] == "PAIRING"
    assert not os.path.exists(out)


def test_detection_rows_that_describe_other_frames_are_refused(tmp_path, monkeypatch):
    """`detect()` sets each row's `frame` to the ENUMERATION index, so the number that
    carries the information is the file's. A record over a differently-numbered render
    pairs each crop's landmarks with another frame's detection."""
    argv, out = _lift_argv(tmp_path, [0, 1], [0, 1], [1, 2])
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(ML.PairingGate) as e:
        LS.main()
    assert e.value.evidence["gate"] == "PAIRING"
    assert not os.path.exists(out)


def test_the_sidecar_records_the_file_each_column_actually_loaded(tmp_path, monkeypatch):
    """The sidecar recorded `"frames": [0,1,2]` and no file name anywhere in it."""
    argv, out = _lift_argv(tmp_path, [0, 1], [0, 1], [0, 1])
    monkeypatch.setattr(sys, "argv", argv)
    LS.main()
    side = json.loads((tmp_path / "sheet.json").read_text(encoding="utf-8"))
    assert len(side["rows"]) == 2
    for n, row in zip([0, 1], side["rows"]):
        assert row["frame"] == n
        assert os.path.splitext(os.path.basename(row["source"]))[0] == f"{n:03d}"
        assert os.path.splitext(os.path.basename(row["lifted"]))[0] == f"{n:03d}"
        assert row["detection_row"] == n


def test_a_requested_index_past_the_lift_populations_is_refused(tmp_path, monkeypatch):
    """`src[i]` had no bounds check at all: it raised a bare IndexError naming nothing."""
    argv, out = _lift_argv(tmp_path, [0, 1], [0, 1], [0, 1], frames="0,1,7")
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SC.SheetPopulationError) as e:
        LS.main()
    assert e.value.evidence["missing_indices"] == [7]
    assert not os.path.exists(out)


def test_the_pairing_gate_on_a_sheet_survives_python_optimize(tmp_path):
    """It raises; it is not an `assert`."""
    import subprocess

    argv, out = _lift_argv(tmp_path, [0, 1], [1, 2], [0, 1])
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    code = (
        "import sys; sys.path.insert(0, r'%s')\n"
        "sys.argv = %r\n"
        "import make_lift_sheet as LS, measure_lift as ML\n"
        "try:\n"
        "    LS.main()\n"
        "except ML.PairingGate:\n"
        "    print('RAISED')\n"
    ) % (os.path.join(root, "tools"), argv)
    res = subprocess.run([sys.executable, "-O", "-c", code], capture_output=True, text=True)
    assert "RAISED" in res.stdout, res.stderr


# ------------------------------------------------- the family: no index dropped in silence


def _gate0(tmp, requested):
    ctl = _clip(str(tmp / "ctl"), [0, 1, 2], digits=5)
    out = _clip(str(tmp / "out"), [0, 1, 2], digits=5)
    return G0.build(ctl, out, None, {"arm": "A1"}, requested, tile_h=24)


def _thesis(tmp, requested):
    ctl = _clip(str(tmp / "ctl"), [0, 1, 2], digits=5)
    arm = _clip(str(tmp / "arm"), [0, 1, 2], digits=5)
    sheet = str(tmp / "sheets" / "thesis.png")
    return TS.main([f"--control={ctl}", f"--arms=A:{arm}", "--reference=none",
                    f"--out={sheet}", f"--frames={requested}", "--tile-height=24"])


def _startframe(tmp, requested):
    d = _clip(str(tmp / "f"), [0, 1, 2], digits=5)
    paths = [os.path.join(d, n) for n in sorted(os.listdir(d))]
    start = os.path.join(str(tmp), "start.png")
    Image.new("RGB", SIZE, (9, 9, 9)).save(start)
    return SFS.build(start, paths, requested, {}, scale=0.5)


def _review(tmp, requested):
    d = _clip(str(tmp / "frames"), [0, 1, 2], digits=5)
    return MRC.main([f"--frames={d}", f"--out={tmp / 'rev'}",
                     f"--stills={requested}", "--crop=8"])


FAMILY = {
    "make_gate0_sheet": (_gate0, [0, 8, 16, 24], [8, 16, 24]),
    "make_startframe_sheet": (_startframe, [0, 8], [8]),
    "make_thesis_sheet": (_thesis, "0,8,16,24", [8, 16, 24]),
    "make_review_clip": (_review, "0,64", [64]),
}


@pytest.mark.parametrize("name", sorted(FAMILY))
def test_no_sheet_drops_a_requested_frame_in_silence(name, tmp_path):
    run, requested, missing = FAMILY[name]
    with pytest.raises(SC.SheetPopulationError) as e:
        run(tmp_path, requested)
    ev = e.value.evidence
    assert ev["missing_indices"] == missing, ev
    assert ev["n_frames"] == 3, ev


@pytest.mark.parametrize("name", sorted(FAMILY))
def test_a_fully_present_request_still_builds(name, tmp_path):
    """The guard the other way: a refusal that fires on a good request is not a check."""
    run, requested, _ = FAMILY[name]
    ok = "0,1,2" if isinstance(requested, str) else [0, 1, 2]
    run(tmp_path, ok)


def test_the_review_clip_manifest_names_what_was_asked_for(tmp_path):
    """The printed count had no denominator: `"stills": len(cuts)` and nothing else."""
    _review(tmp_path, "0,2")
    man = json.loads((tmp_path / "rev" / "review_manifest.json").read_text(encoding="utf-8"))
    assert man["stills_requested"] == [0, 2]
    assert man["n_frames"] == 3


def test_a_detection_record_of_another_length_is_not_indexed_positionally(tmp_path):
    """`det[i]` had no check of `len(det)` against `len(ims)` and none that
    `det[i]['frame'] == i`."""
    d = _clip(str(tmp_path / "frames"), [0, 1, 2], digits=5)
    det = _detection(str(tmp_path / "det.json"), [0, 1])
    with pytest.raises(ML.PairingGate) as e:
        MRC.main([f"--frames={d}", f"--out={tmp_path / 'rev'}", f"--detection={det}",
                  "--stills=0", "--crop=8"])
    assert e.value.evidence["gate"] == "PAIRING"


# --------------------------------------------------------------------- the census


def test_every_sheet_that_indexes_a_listing_asks_for_the_check(tmp_path):
    """The population may not grow silently: a sheet that takes `--frames` and indexes a
    directory listing routes through the shared refusal, or this fails naming it."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    expected = ("make_gate0_sheet", "make_identity_sheet", "make_lift_sheet",
                "make_review_clip", "make_startframe_sheet", "make_thesis_sheet")
    without = []
    for mod in expected:
        src = open(os.path.join(root, "tools", f"{mod}.py"), encoding="utf-8").read()
        if "require_frames" not in src:
            without.append(mod)
    assert without == [], without


def test_no_sheet_still_carries_the_silent_continue(tmp_path):
    """The literal mechanism: `if fi >= len(...): continue` in a tile loop."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    offenders = []
    for mod in ("make_gate0_sheet", "make_lift_sheet", "make_review_clip",
                "make_startframe_sheet", "make_thesis_sheet"):
        lines = open(os.path.join(root, "tools", f"{mod}.py"),
                     encoding="utf-8").read().splitlines()
        for i, line in enumerate(lines):
            stripped = line.strip()
            # an `if` STATEMENT, not the prose that records the defect above it
            if (stripped.startswith("if ") and ">= len(" in stripped
                    and "continue" in "".join(lines[i:i + 2])):
                offenders.append(f"{mod}:{i + 1} {stripped}")
    assert offenders == [], offenders
