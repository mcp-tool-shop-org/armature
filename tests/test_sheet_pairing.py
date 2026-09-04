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

import ast
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


# WAVE 8, F-3bfcabfc — both censuses used to enumerate hard-coded tuples: a six-name
# `expected` and a five-name loop, under a docstring reading "The population may not grow
# silently". Neither could fail on a sheet not already typed into it. Derived from the tree
# on 2026-09-04, the tools that take `--frames` AND enumerate a directory with `os.listdir`
# number FIFTEEN — nine of them outside the census, and one of those nine is the live case:
# `make_crop_strip.frame_paths` sorts a listing and `build` indexes it with `paths[idx]`
# where `idx` came from `--boxes=<frame>:x0,y0,x1,y1`, so a frame NUMBER is used as a
# listing POSITION. A crop strip labelled "frame 32" then shows a different frame whenever
# the listing is not 0..N-1 — the defect the pairing law closed for six sheets, on a tool
# the law never reached.

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")


def _calls(tree, name):
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            called = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if called == name:
                out.append(node)
    return out


def _listing_builders(tree):
    """`{function: 'keyed' | 'positional'}` for every function that lists a directory.

    'keyed' means the function hands back a MAPPING built from the frame number
    (`{int(stem): path for ...}`), where a lookup by frame number is a lookup by NAME and
    cannot be a position. 'positional' means it hands back a sequence, where indexing it
    with a frame number is the defect this file exists for.
    """
    out = {}
    for fn in ast.walk(tree):
        if isinstance(fn, ast.FunctionDef) and _calls(fn, "listdir"):
            keyed = any(isinstance(n, ast.DictComp) and "int" in ast.dump(n.key)
                        for n in ast.walk(fn))
            out[fn.name] = "keyed" if keyed else "positional"
    return out


def _positional_indexing(tree):
    """Every `name[...]` where `name` holds a POSITIONAL listing.

    A small dataflow rather than a list of variable names: a name holds a listing when it
    is assigned from an `os.listdir` expression or from a call to one of the builders
    above, and a function PARAMETER holds one when a builder's result is passed into that
    position — which is how `make_crop_strip.build(frame_paths(...), ...)` reaches its
    `paths` argument.
    """
    builders = _listing_builders(tree)
    if not builders:
        return []
    funcs = {f.name: f for f in ast.walk(tree) if isinstance(f, ast.FunctionDef)}
    holds = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if isinstance(node.value, ast.Call):
                called = getattr(node.value.func, "id",
                                 getattr(node.value.func, "attr", ""))
                if called in builders:
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            holds[target.id] = builders[called]
            if _calls(ast.Module(body=[node], type_ignores=[]), "listdir"):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        holds.setdefault(target.id, "positional")
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in funcs):
            for i, arg in enumerate(node.args):
                called = getattr(getattr(arg, "func", None), "id", None)
                if called in builders:
                    params = funcs[node.func.id].args.args
                    if i < len(params):
                        holds[params[i].arg] = builders[called]
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name)
                and holds.get(node.value.id) == "positional"):
            out.append((node.lineno, node.value.id))
    return sorted(out)


def frame_indexing_tools():
    """THE DERIVATION: every tool that takes `--frames` and enumerates a directory."""
    out = []
    for name in sorted(os.listdir(TOOLS)):
        if not name.endswith(".py"):
            continue
        with open(os.path.join(TOOLS, name), encoding="utf-8") as fh:
            src = fh.read()
        if "--frames" not in src:
            continue
        tree = ast.parse(src)
        if _listing_builders(tree):
            out.append(name[:-3])
    return out


#: Derived 2026-09-04. Equality, so a sixteenth tool joins the census the day it lands.
RECORDED_FRAME_TOOLS = [
    "encode_control", "invert_frames", "lift_clip", "make_crop_strip", "make_gate0_sheet",
    "make_identity_sheet", "make_lift_sheet", "make_pick_sheet", "make_plate",
    "make_review_clip", "make_startframe_sheet", "make_thesis_sheet", "measure_arm",
    "measure_clip", "pack_pose_pack",
]

#: Named, dated, and checked against the clause it rests on. `make_crop_strip` indexes a
#: sorted listing with a number that came from `--boxes`, and its only guard is a LENGTH
#: check (`if idx >= len(paths): raise ...`) — which cannot tell frame 32 from position 32.
#: Routed to the instruments-measure domain in this wave ("`--boxes` keys by frame NUMBER
#: and records it"); when that lands, the tool either routes through the shared refusal or
#: its builder returns a mapping, and it drops out of `offenders` on its own. SUBSET
#: assertion, so this can only shrink, and a SEVENTEENTH offender fails here immediately.
POSITIONAL_INDEXING_ROUTED = {"make_crop_strip"}


def test_the_frame_indexing_population_is_derived_and_has_not_grown_silently():
    """Size and membership before the property. The old census typed six names into a
    tuple; the tree carries fifteen tools that take `--frames` and list a directory."""
    pop = frame_indexing_tools()
    assert pop == RECORDED_FRAME_TOOLS, {
        "appeared": sorted(set(pop) - set(RECORDED_FRAME_TOOLS)),
        "vanished": sorted(set(RECORDED_FRAME_TOOLS) - set(pop)),
    }
    assert POSITIONAL_INDEXING_ROUTED <= set(pop)


def test_every_tool_that_indexes_a_listing_by_frame_number_asks_for_the_check():
    """The property. A tool in the population is compliant when it routes through the
    shared refusal, or when it never uses a frame number as a POSITION at all — because
    it consumes the listing in order, or because its builder hands back a mapping keyed by
    the frame number, which is what `make_pick_sheet` and `make_plate` do."""
    offenders = {}
    for mod in frame_indexing_tools():
        with open(os.path.join(TOOLS, f"{mod}.py"), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        routed = bool(_calls(tree, "require_frames")
                      or _calls(tree, "gate_listing_pairing"))
        indexing = _positional_indexing(tree)
        if not routed and indexing:
            offenders[mod] = indexing
    new = sorted(set(offenders) - POSITIONAL_INDEXING_ROUTED)
    assert not new, (
        f"these tools index a positional listing with a frame number and route through "
        f"neither require_frames nor gate_listing_pairing: "
        f"{ {m: offenders[m] for m in new} }")
    assert set(offenders) <= POSITIONAL_INDEXING_ROUTED, sorted(offenders)


def test_the_exemptions_clause_is_the_state_it_was_recorded_for():
    """Rule 4: an exemption is checked against its REASON, not merely listed. If
    `make_crop_strip` stops indexing positionally, or starts routing, it leaves
    `offenders` on its own and this test says the record is stale."""
    with open(os.path.join(TOOLS, "make_crop_strip.py"), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    still_broken = (not _calls(tree, "require_frames")
                    and not _calls(tree, "gate_listing_pairing")
                    and bool(_positional_indexing(tree)))
    assert still_broken or "make_crop_strip" not in POSITIONAL_INDEXING_ROUTED, (
        "make_crop_strip no longer indexes a positional listing by frame number; remove "
        "it from POSITIONAL_INDEXING_ROUTED in the same commit, or the next tool to "
        "regress inherits an exemption written for a defect that is gone")


def test_the_positional_indexing_detector_can_see_the_defect_and_not_the_fix(tmp_path):
    """Rule 3: the derivation is driven against a tree whose answers are known. Three
    synthetic tools — a sorted list indexed by a frame number (the defect), the same tool
    with a mapping keyed by that number (the fix `make_pick_sheet` already carries), and
    one that only iterates."""
    broken = ast.parse(
        "import os\n"
        "def frame_paths(d):\n"
        "    return sorted(os.listdir(d))\n"
        "def build(paths, idx):\n"
        "    return paths[idx]\n"
        "def main():\n"
        "    build(frame_paths('x'), 32)\n")
    keyed = ast.parse(
        "import os\n"
        "def frame_paths(d):\n"
        "    return {int(n.split('.')[0]): n for n in os.listdir(d)}\n"
        "def build(paths, idx):\n"
        "    return paths[idx]\n"
        "def main():\n"
        "    build(frame_paths('x'), 32)\n")
    iterating = ast.parse(
        "import os\n"
        "def frame_paths(d):\n"
        "    return sorted(os.listdir(d))\n"
        "def main():\n"
        "    return [n for n in frame_paths('x')]\n")
    assert _positional_indexing(broken) == [(5, "paths")]
    assert _listing_builders(keyed) == {"frame_paths": "keyed"}
    assert _positional_indexing(keyed) == []
    assert _positional_indexing(iterating) == []


def test_no_sheet_still_carries_the_silent_continue():
    """The literal mechanism: `if fi >= len(...): continue` in a tile loop.

    Over the DERIVED population, not the five names this loop used to hold — a sheet that
    grew the skip after the wave-6 fix would have joined nothing."""
    offenders = []
    for mod in frame_indexing_tools():
        with open(os.path.join(TOOLS, f"{mod}.py"), encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        for i, line in enumerate(lines):
            stripped = line.strip()
            # an `if` STATEMENT, not the prose that records the defect above it
            if (stripped.startswith("if ") and ">= len(" in stripped
                    and "continue" in "".join(lines[i:i + 2])):
                offenders.append(f"{mod}:{i + 1} {stripped}")
    assert offenders == [], offenders
