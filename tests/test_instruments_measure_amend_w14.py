"""Wave 14, instruments-measure — the twelve approved findings, each as a property.

Appended by the instruments-measure amend seat in ONE new module, following the wave-12
precedent (`tests/test_instruments_measure_amend_w12.py`), so the tests domain's own files
are not rewritten under it while both branches are in flight.

**THE OPERAND each fixture exercises** — wave 14's rule: a fix is only landed when the test
goes red on the object the finding named, not on its neighbour.

* **F-a254bbd3** — the operand is an UNKNOWN `--key=value` token reaching
  `stage_render._parse_argv`, and the known set is derived from what `main` itself reads,
  not typed beside it.
* **F-cd036a86** — the operand is `tools/measure_clip.py:131`, the consumer the wave-12
  `clipstats` fix NAMED, driven on a ONE-FRAME clip directory. Not `_stats` (already
  fixed), not a synthetic `None`: `measure_clip.main` on one PNG.
* **F-8da56714** — the operand is a view whose NEW master's maximum alpha is 254, so
  `figure_mask_new` (`>= 255`) matches nothing and the eroded interior is empty. The
  assertion is on the PRINTED summary and the token's position, both.
* **F-1fb7ba1c** — the operand is two 2-frame records that pass every OTHER refusal
  (matching resolution, camera, keypoint names and counts), driven through `main`.
* **F-5f2a7452** — the operand is `--out` AFTER Gate INK fires: the directory must hold no
  `NNNNN.png`.
* **F-6a18f6d5** — the operand is `--out` after `validate_motion_record` refuses: it must
  not exist at all.
* **F-0d033bd6** — the same, for `--mode=scale` with no `--second`.
* **F-734951dc** — the operand is `.evidence` on an instance built exactly as the raise
  sites build one, and `str(exc)` NOT being a 2-tuple repr.
* **F-8393e66c** — the operand is the PRINTED `STAGE_RENDER_HALT` line, read back and
  parsed, with its `evidence` keys asserted. A raise-site assertion would not have caught
  the defect, because the class dropped the dict on the way to the handler.
* **F-33ec9dd3** — the operand is `main`'s first docstring line beside `main`'s actual
  return statements, derived from the AST.
* **F-0c850c1a** — the operand is the printed `order` line on a hold-shaped clip, not the
  JSON record (which has carried the tie fields since wave 12).
* **F-90c26d7b** — the operand is the SIDECAR of a crop strip cut from a frames directory
  that holds a contact strip, plus the two predicates' partition of the PNG listing.

Helpers here raise; they never `assert` (`-O` deletes an `assert` in a non-plugin helper).
Every refusal proven here is a `raise`, and the module is run under `PYTHONOPTIMIZE=1` in
this amend's own verification.
"""

import ast
import json
import os
import subprocess
import sys

import numpy as np
import pytest
from PIL import Image

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(REPO, "tools")
sys.path.insert(0, TOOLS)

from armature_core.errors import ArmatureError, SpecError  # noqa: E402


def _src(name):
    with open(os.path.join(TOOLS, f"{name}.py"), encoding="utf-8") as fh:
        return fh.read()


def _func(name, fn):
    for node in ast.walk(ast.parse(_src(name))):
        if isinstance(node, ast.FunctionDef) and node.name == fn:
            return node
    raise LookupError(f"{name}.{fn} not found")


# ===========================================================================
# F-a254bbd3 — the control-sequence exporter refuses an unknown flag BY NAME
# ===========================================================================


def test_stage_render_refuses_a_mistyped_optional_flag_by_name():
    """THE OPERAND: `--assset=WRONG.glb`, three s's.

    Measured on the base tree: `_parse_argv(['--spec=s.json', '--out=d',
    '--assset=WRONG.glb', '--views=-30,0,30', '--typo=1'])` returned all five keys with no
    refusal, `main`'s `if "asset" in args` never fired, and the export ran on the SPEC's
    asset — exit 0, `STAGE_RENDER_OK`, and a manifest that looks finished. The substitution
    was recoverable only by reading `manifest['asset']['path']`.
    """
    import stage_render

    with pytest.raises(SpecError) as exc:
        stage_render._parse_argv(["--spec=s.json", "--out=d", "--assset=WRONG.glb"])
    assert "--assset" in str(exc.value), str(exc.value)
    assert "--asset" in str(exc.value), str(exc.value)

    # ...and the flag this tool does NOT have, advertised on line 11 of its own docstring
    # for years, is refused as well.
    with pytest.raises(SpecError) as exc:
        stage_render._parse_argv(["--spec=s.json", "--out=d", "--views=-30,0,30"])
    assert "--views" in str(exc.value), str(exc.value)

    # the happy path is unchanged, including the documented override
    assert stage_render._parse_argv(
        ["--spec=s.json", "--out=d", "--asset=x.glb"]) == {
            "spec": "s.json", "out": "d", "asset": "x.glb"}


def test_the_known_flag_set_is_the_one_main_actually_reads():
    """THE NODE: `main`'s own AST, not a list beside the parser.

    A flag accepted by the parser and read by nobody is the same defect one level along, so
    the set is derived from every string `main` uses against the `args` dict — subscripts,
    `.get(...)` calls and `in` tests alike — and compared with `KNOWN_FLAGS`.
    """
    import stage_render

    fn = _func("stage_render", "main")
    read = set()
    for node in ast.walk(fn):
        if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name)
                and node.value.id == "args"
                and isinstance(node.slice, ast.Constant)):
            read.add(node.slice.value)
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "args"
                and node.args and isinstance(node.args[0], ast.Constant)):
            read.add(node.args[0].value)
        if isinstance(node, ast.Compare) and isinstance(node.left, ast.Constant):
            for op, cmp in zip(node.ops, node.comparators):
                if (isinstance(op, ast.In) and isinstance(cmp, ast.Name)
                        and cmp.id == "args"):
                    read.add(node.left.value)

    assert read, "the derivation found no flag reads in stage_render.main"
    assert read == set(stage_render.KNOWN_FLAGS), {
        "read by main, not known to the parser": sorted(read - set(stage_render.KNOWN_FLAGS)),
        "known to the parser, read by nobody": sorted(set(stage_render.KNOWN_FLAGS) - read),
    }
    assert set(stage_render.REQUIRED_FLAGS) | set(stage_render.OPTIONAL_FLAGS) == set(
        stage_render.KNOWN_FLAGS)


def test_the_module_docstring_documents_the_flag_it_takes_and_not_one_it_does_not():
    """The docstring compounded the defect twice: `--asset` was absent from the usage line
    and `--views=-30,0,30` was advertised as this tool's example."""
    head = _src("stage_render").split('"""')[1]
    # the USAGE block: the indented invocation lines under "Run it headless"
    usage = [l for l in head.splitlines() if l.startswith("    blender")
             or l.startswith("        ")]
    joined = "\n".join(usage)
    assert "--asset" in joined, joined
    assert "--views" not in joined, joined
    # and the flag this tool does not have is named as a correction, never as an example
    assert "this tool has no `--views`" in head, head[:900]


# ===========================================================================
# F-8393e66c — the halt line's evidence, READ BACK off stdout
# ===========================================================================


def test_the_stage_render_halt_line_carries_the_clause_of_an_unreadable_path(capsys,
                                                                             tmp_path):
    """THE OPERAND: the PRINTED `STAGE_RENDER_HALT` line, parsed back.

    Measured on the base tree: `tools/stage_render.py --spec=nope.json --out=<tmp>` exited
    2 and printed a line whose `evidence` was `null` and whose `message` was the Python
    2-tuple repr of (the FileNotFoundError text, the evidence dict) — the base
    `ArmatureError` has no `__init__`, so the dict landed in `args[1]`. The comment beside
    the raise said "it carries no gate id (`gate: None` is the receipt)", which is a
    property no code delivered. An AST census keyed on "the raise passes a literal dict"
    scores that site compliant, which is why this assertion reads the LINE.
    """
    from blender_stub import exit_code_of_main_block

    missing = str(tmp_path / "nope.json")
    out = str(tmp_path / "run")

    def raiser():
        import stage_render
        return stage_render.main([f"--spec={missing}", f"--out={out}"])

    code, escaped = exit_code_of_main_block(
        "stage_render.py", raiser=raiser,
        argv=["blender", "-b", "-P", "stage_render.py", "--",
              f"--spec={missing}", f"--out={out}"])
    assert escaped is None, escaped
    assert code == 2, code

    printed = capsys.readouterr().out
    lines = [l for l in printed.splitlines()
             if l.split(" ", 1)[0] == "STAGE_RENDER_HALT"]
    assert len(lines) == 1, printed
    rec = json.loads(lines[0][len("STAGE_RENDER_HALT"):].strip())

    assert rec["evidence"] is not None, rec
    assert rec["evidence"]["clause"] == "spec_or_asset_path_unreadable", rec
    assert rec["evidence"]["gate"] is None, rec
    assert rec["evidence"]["spec"] == missing, rec
    assert rec["gate"] is None, rec
    # the message is the exception's text, not a 2-tuple repr of (text, evidence)
    assert not rec["message"].startswith("("), rec["message"]
    assert "FileNotFoundError" in rec["message"], rec["message"]
    assert "clause" not in rec["message"], rec["message"]


def test_no_tool_in_this_domain_raises_the_bare_base_with_an_evidence_argument():
    """The census half, keyed on the SHAPE rather than on this one site.

    `raise ArmatureError(msg, {...})` is the shape that silently discards its evidence
    until `ArmatureError` gains a constructor; an AST census over `tools/**` measured
    `stage_render.py:582` as the only one in the tree, and this holds that at zero for the
    42 modules of this domain.
    """
    offenders = []
    for name in sorted(os.listdir(TOOLS)):
        if not name.endswith(".py"):
            continue
        for node in ast.walk(ast.parse(_src(name[:-3]))):
            if not (isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call)):
                continue
            func = node.exc.func
            cls = getattr(func, "id", getattr(func, "attr", None))
            if cls == "ArmatureError" and len(node.exc.args) >= 2:
                offenders.append((name, node.lineno))
    assert offenders == [], offenders


# ===========================================================================
# F-33ec9dd3 — the docstring's first line says what `main` does
# ===========================================================================


def test_stage_render_main_promises_no_return_code_it_does_not_produce():
    """THE NODE: `main`'s `Return` statements, beside its first docstring line.

    After the wave-12 merge no path returns 2 — the `except ArmatureError` branch re-raises
    so the `__main__` handler can deliver the single halt line, and the `except OSError`
    branch raises too. The sentence promising a 2 sent an in-process caller (which is how
    this suite drives the tool) to `if stage_render.main(argv) == 2:`.
    """
    fn = _func("stage_render", "main")
    returned = {node.value.value for node in ast.walk(fn)
                if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant)}
    assert returned == {0}, returned

    first = ast.get_docstring(fn).splitlines()[0]
    assert "2" not in first, first
    assert "raises" in first.lower() or "raise" in first.lower(), first


# ===========================================================================
# F-cd036a86 — the one-frame clip, through the consumer the fix named
# ===========================================================================


def _one_frame_dir(tmp_path, n=1, size=16):
    d = tmp_path / f"frames{n}"
    d.mkdir()
    rng = np.random.default_rng(7)
    for i in range(n):
        a = rng.integers(0, 255, (size, size, 3), dtype=np.uint8)
        Image.fromarray(a).save(d / f"{i:05d}.png")
    return d


def test_a_one_frame_clip_is_summarised_with_a_null_and_not_a_typeerror(tmp_path, capsys):
    """THE OPERAND: `measure_clip.main` on a directory holding ONE PNG.

    The wave-12 `clipstats` fix named `tools/measure_clip.py:131` as the consumer it was
    protecting and left it broken with a different exception: the key resolves now, to
    `None`, and `round(None, 3)` is
    `TypeError: type NoneType doesn't define __round__ method`. The crash landed AFTER
    `json.dump`, so the `--out` JSON sat on disk complete while `MEASURE_CLIP_OK` was never
    printed.
    """
    import measure_clip

    out = tmp_path / "m.json"
    assert measure_clip.main([f"--frames={_one_frame_dir(tmp_path)}", f"--out={out}"]) == 0

    line = [l for l in capsys.readouterr().out.splitlines()
            if l.startswith("MEASURE_CLIP_OK")]
    assert len(line) == 1
    summary = json.loads(line[0][len("MEASURE_CLIP_OK"):])["summary"]["clip"]
    assert summary["frames"] == 1
    assert summary["frame_delta_median"] is None, summary
    assert summary["abs_delta_luma_median"] is None, summary

    rec = json.loads(out.read_text(encoding="utf-8"))
    assert rec["arms"][0]["frame_deltas"]["stats"]["median"] is None


def test_the_measurements_record_is_written_after_the_numbers_that_summarise_it(tmp_path):
    """THE NODE: the line numbers of the summary loop and of `json.dump`, in `main`.

    "A complete measurement file for a run the instrument refused to summarise" is the
    worst consequence the finding names, and it is a consequence of ORDER: the summary is
    now built first, so a failure to summarise leaves no record to be mistaken for one.
    """
    fn = _func("measure_clip", "main")
    dumps = [n.lineno for n in ast.walk(fn)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr == "dump"]
    summary_assign = [n.lineno for n in ast.walk(fn)
                      if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == "summary"
                              for t in n.targets)]
    fors = [n.lineno for n in ast.walk(fn) if isinstance(n, ast.For)]
    assert dumps and summary_assign and fors
    assert max(fors) < min(dumps), (fors, dumps)


def test_the_start_frame_sheet_survives_a_one_frame_measurements_record(tmp_path):
    """The second, unnamed consumer of the same two fields: `--measurements` pointing at
    any such record killed the START-FRAME SHEET build with a bare TypeError naming no
    flag."""
    import make_startframe_sheet

    assert make_startframe_sheet.round_or_none is not None
    arm = {"n_frames": 1, "distinct": {"n_distinct": 1},
           "frame_deltas": {"stats": {"median": None}},
           "luma": {"stats": {"median": None}},
           "similarity_to_first": {"per_frame_correlation": [1.0]},
           "horizon": {"n_found": 1}}
    panel = {
        "frames": f"{arm['n_frames']}, {arm['distinct']['n_distinct']} distinct",
        "d(frame) med": make_startframe_sheet.round_or_none(
            arm["frame_deltas"]["stats"]["median"], 3),
        "d(luma) med": make_startframe_sheet.round_or_none(
            arm["luma"]["stats"]["median"], 3),
    }
    assert panel["d(frame) med"] is None and panel["d(luma) med"] is None
    # ...and it is ONE implementation, imported rather than copied
    assert make_startframe_sheet.round_or_none.__module__ == "measure_clip"


# ===========================================================================
# F-8da56714 — one key set out of survey_view, and the token below the summary
# ===========================================================================


def _survey_masters(tmp_path, new_alpha, views=1):
    new_dir, old_dir = tmp_path / "new", tmp_path / "old"
    new_dir.mkdir()
    old_dir.mkdir()
    for i in range(views):
        a = np.zeros((24, 24, 4), np.uint8)
        a[..., :3] = 180
        a[6:18, 6:18, 3] = new_alpha          # the figure, at the alpha under test
        Image.fromarray(a, mode="RGBA").save(new_dir / f"turn_{i}.png")
        b = np.zeros((24, 24, 4), np.uint8)
        b[..., :3] = 40
        b[4:20, 4:20, :3] = 200
        b[..., 3] = 255
        Image.fromarray(b, mode="RGBA").save(old_dir / f"armfinal_{i}.png")
    return new_dir, old_dir


def test_survey_view_returns_one_key_set_on_an_empty_eroded_interior():
    """THE OPERAND: a mask that survives no erosion. `survey_view` used to return
    `{interior_px, note}` there and the full record otherwise — the different-key-set-on-
    the-empty-case defect core-solvers had just removed from `clipstats._stats`."""
    import make_hole_survey as HS

    rgb = np.full((20, 20, 3), 128, np.uint8)
    full = HS.survey_view(rgb, np.ones((20, 20), bool))
    empty = HS.survey_view(rgb, np.zeros((20, 20), bool))
    assert set(full) == set(empty), (sorted(full), sorted(empty))
    assert empty["interior_px"] == 0
    for key in HS.STAT_KEYS:
        assert empty[key] is None, (key, empty[key])
        assert full[key] is not None, key


def test_a_near_opaque_master_completes_with_n_a_and_the_token_last(tmp_path, capsys,
                                                                   monkeypatch):
    """THE OPERAND: a NEW master whose maximum alpha is 254.

    `figure_mask_new` is `rgba[..., 3] >= 255`, so the 3px erosion leaves nothing; measured
    on the base tree the run printed `SURVEY_OK <out>` and THEN raised
    `KeyError: 'low_saturation_fraction'`, with `survey.json` already on disk. `SURVEY_OK`
    is a token `docs/experiments/E07-the-skeleton.md:203` lists among the lines the
    pipeline keys on.
    """
    import make_hole_survey as HS

    new_dir, old_dir = _survey_masters(tmp_path, new_alpha=254)
    out = tmp_path / "survey"
    monkeypatch.setattr(sys, "argv", [
        "make_hole_survey", "--new", str(new_dir), "--old", str(old_dir),
        "--out", str(out), "--views", "1"])
    HS.main()

    printed = capsys.readouterr().out.splitlines()
    body = [l for l in printed if l.strip().startswith("view 0:")]
    assert len(body) == 1, printed
    assert "n/a" in body[0] and "interior_px 0" in body[0], body[0]

    tokens = [i for i, l in enumerate(printed) if l.startswith("SURVEY_OK")]
    view_at = printed.index(body[0])
    assert tokens and tokens[0] > view_at, printed

    rec = json.loads((out / "survey.json").read_text(encoding="utf-8"))
    assert rec["views"][0]["new"]["interior_px"] == 0
    assert rec["views"][0]["new"]["low_saturation_fraction"] is None


# ===========================================================================
# F-1fb7ba1c — a record with too few frames is refused by name, not by AttributeError
# ===========================================================================


def _kp_record(n_frames, n_kp=2):
    return {
        "resolution": [64, 64], "camera": {"radius": 2.0, "target": [0, 0, 0]},
        "fps": 16.0, "frames": n_frames,
        "keypoint_names": [f"kp{k}" for k in range(n_kp)],
        "body": [[[float(i + k), float(i), 1.0] for k in range(n_kp)]
                 for i in range(n_frames)],
        "left_hand": [[] for _ in range(n_frames)],
        "right_hand": [[] for _ in range(n_frames)],
    }


def test_two_two_frame_records_are_refused_with_the_frame_count_in_the_evidence(tmp_path):
    """THE OPERAND: two 2-frame records that pass EVERY other refusal.

    `second_differences` needs three frames, so `stats([])` is `None` and the success line
    did `pa['second_px_per_frame2'].items()`. Measured on the base tree:
    `AttributeError: 'NoneType' object has no attribute 'items'`, with the payload ALREADY
    written to `--out` — a complete diagnostic record on disk, no `MEASURE_SMOOTHNESS_OK`
    line, and an error naming neither the input nor the frame count.
    """
    import measure_smoothness as MS

    pa, pb = tmp_path / "a.json", tmp_path / "b.json"
    pa.write_text(json.dumps(_kp_record(2)), encoding="utf-8")
    pb.write_text(json.dumps(_kp_record(2)), encoding="utf-8")
    out = tmp_path / "deep" / "smooth.json"

    with pytest.raises(MS.SmoothnessInputError) as exc:
        MS.main([f"--a={pa}", f"--b={pb}", f"--out={out}"])
    ev = exc.value.evidence
    assert ev["clause"] == "too_few_frames_for_a_second_difference", ev
    assert ev["frames"] == 2, ev
    assert ev["minimum"] == MS.MIN_FRAMES_FOR_SECOND_DIFFERENCE
    assert not out.exists(), "a refused run left its payload behind"
    assert not out.parent.exists(), "a refused run left its output directory behind"


def test_the_success_line_refuses_a_block_that_was_never_computed(tmp_path):
    """The andon on the direction the frame refusal does not bound: any other route to an
    empty distribution. `_summarisable` names the block and the record; `.items()` on a
    `None` names neither."""
    import measure_smoothness as MS

    with pytest.raises(MS.SmoothnessInputError) as exc:
        MS._summarisable(None, "pooled second_px_per_frame2", "A", _kp_record(3),
                         str(tmp_path / "a.json"))
    assert exc.value.evidence["clause"] == "no_distribution_to_summarise"
    assert exc.value.evidence["frames"] == 3
    # the pass-through direction, so the guard is not a blanket refusal
    assert MS._summarisable({"n": 1}, "x", "A", _kp_record(3), "p") == {"n": 1}


def test_three_frames_still_measure(tmp_path, capsys):
    """The floor is a floor and not a ban: three frames is exactly one second difference."""
    import measure_smoothness as MS

    pa, pb = tmp_path / "a.json", tmp_path / "b.json"
    pa.write_text(json.dumps(_kp_record(3)), encoding="utf-8")
    pb.write_text(json.dumps(_kp_record(3)), encoding="utf-8")
    out = tmp_path / "smooth.json"
    assert MS.main([f"--a={pa}", f"--b={pb}", f"--out={out}"]) == 0
    assert "MEASURE_SMOOTHNESS_OK" in capsys.readouterr().out
    assert out.exists()


# ===========================================================================
# F-5f2a7452 — Gate INK fires before the first frame is on disk
# ===========================================================================


def _sticks_record(tmp_path, n=3, width=256, height=256, spread=1.0, name="kp.json"):
    """A keypoint record `render_pose_sticks` accepts, with the pose's SPREAD as the lever.

    `spread=0.0` collapses all twenty keypoints onto the frame centre: every limb ellipse
    degenerates to one blob, the drawn ink fraction falls under the floor `main` derives
    from `sw`, `width` and `height`, and Gate INK is the refusal under test. Larger spreads
    draw an ordinary figure.
    """
    from armature_core import aapose

    body = []
    for _ in range(n):
        frame = []
        for k in range(len(aapose.KEYPOINT_NAMES)):
            x = width / 2 + ((k % 5) - 2) * spread
            y = height / 2 + ((k // 5) - 2) * spread
            frame.append([float(x), float(y), 1.0])
        body.append(frame)
    rec = {"resolution": [width, height], "frames": n, "fps": 16, "body": body,
           "left_hand": [[] for _ in range(n)], "right_hand": [[] for _ in range(n)],
           "convention": dict(aapose.SOURCE), "diagnostics": {}}
    p = tmp_path / name
    p.write_text(json.dumps(rec), encoding="utf-8")
    return p


def test_gate_ink_leaves_no_frame_on_disk_when_it_fires(tmp_path):
    """THE OPERAND: `--out` AFTER Gate INK fires.

    `fracs` was appended inside the WRITE loop over the in-memory canvas, and `gate_ink`
    ran after the loop, so when the gate fired all n frames were already in `--out` — in
    exactly the shape the consumers of this directory pick up from a bare listing — while
    `READBACK_REASONS` excused the gate with "ink fraction measured over the frames just
    written". It opened no file.
    """
    import render_pose_sticks as RPS

    out = tmp_path / "sticks"
    kp = _sticks_record(tmp_path, n=3, spread=0.0)
    with pytest.raises(RPS.SticksGate) as exc:
        RPS.main([f"--keypoints={kp}", f"--out={out}", "--strip=0", "--hands=0"])
    assert exc.value.evidence.get("gate") == "INK", exc.value.evidence
    written = [] if not out.exists() else sorted(
        n for n in os.listdir(out)
        if n.lower().endswith(".png") and os.path.splitext(n)[0].isdigit())
    assert written == [], written


def test_gate_ink_is_above_the_first_write_in_the_source():
    """The ordering, keyed on the AST rather than on the fixture — the fixture proves the
    gate fires with nothing on disk; this proves nothing can be written before it runs on
    ANY input."""
    fn = _func("render_pose_sticks", "main")
    ink = [n.lineno for n in ast.walk(fn)
           if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "gate_ink"]
    makedirs = [n.lineno for n in ast.walk(fn)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "makedirs"]
    imwrite = [n.lineno for n in ast.walk(fn)
               if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
               and n.func.attr == "imwrite"]
    assert ink and makedirs and imwrite
    assert max(ink) < min(makedirs + imwrite), (ink, makedirs, imwrite)


def test_a_drawn_run_still_writes_its_frames(tmp_path):
    """The measurement is unchanged; only its position moved. A record whose frames carry
    real ink must still produce them."""
    import render_pose_sticks as RPS

    out = tmp_path / "sticks_ok"
    kp = _sticks_record(tmp_path, n=3, spread=22.0, name="kp_ok.json")
    RPS.main([f"--keypoints={kp}", f"--out={out}", "--strip=0", "--hands=0"])
    written = sorted(n for n in os.listdir(out)
                     if n.lower().endswith(".png") and os.path.splitext(n)[0].isdigit())
    assert written == ["00000.png", "00001.png", "00002.png"], written


# ===========================================================================
# F-6a18f6d5 — resample_motion writes nothing when an andon fires
# ===========================================================================


def _motion(n=4, with_local=True):
    """A motion record `lift_solve.validate_motion_record` accepts — every bone in
    `sitelist.ALL_NAMES` present at identity — with the `local` block as the lever."""
    from armature_core import sitelist

    frames = []
    for i in range(n):
        f = {"frame": i, "root": [0.0, 0.0, float(i)]}
        if with_local:
            f["local"] = {b: [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
                          for b in sitelist.ALL_NAMES}
        frames.append(f)
    return {"tool": "test", "frames": frames}


def test_a_refused_motion_record_leaves_no_output_directory(tmp_path):
    """THE OPERAND: `--out` after `lift_solve.validate_motion_record` refuses.

    `os.makedirs` sat above all four of this tool's andons, so a record whose frames carry
    no `local` rotations raised SolveGate [SOLVE] and left `--out` on disk, existing and
    empty. The wider point the finding makes is that the census which polices this rule
    could not see the tool at all — that half is closed in
    `tests/test_instrument_write_ordering.py` in the same commit.
    """
    import resample_motion as RM

    src = tmp_path / "m.json"
    src.write_text(json.dumps(_motion(4, with_local=False)), encoding="utf-8")
    out = tmp_path / "resampled"
    with pytest.raises(ArmatureError, match="carries no rotation for") as exc:
        RM.main([f"--motion={src}", "--frames=8", f"--out={out}"])
    assert exc.value.evidence["gate"] == "SOLVE", exc.value.evidence
    assert "hips" in exc.value.evidence["missing"], exc.value.evidence
    assert not out.exists(), "a refused run left its output directory behind"


def test_a_destination_of_one_frame_is_refused_by_name(tmp_path):
    """`sample_interval_ratio = (n_src - 1) / (n_dst - 1)` and `positions` both divide by
    `n_dst - 1`; `--frames=1` died with a bare ZeroDivisionError naming neither."""
    import resample_motion as RM

    src = tmp_path / "m.json"
    src.write_text(json.dumps(_motion(4)), encoding="utf-8")
    out = tmp_path / "resampled1"
    with pytest.raises(RM.ResampleArgError) as exc:
        RM.main([f"--motion={src}", "--frames=1", f"--out={out}"])
    assert exc.value.evidence["clause"] == "destination_frame_count_below_two"
    assert exc.value.evidence["frames"] == 1
    assert not out.exists()


def test_a_clean_resample_still_writes(tmp_path, capsys):
    import resample_motion as RM

    src = tmp_path / "m.json"
    src.write_text(json.dumps(_motion(4)), encoding="utf-8")
    out = tmp_path / "resampled_ok"
    assert RM.main([f"--motion={src}", "--frames=8", f"--out={out}"]) == 0
    assert "RESAMPLE_MOTION_OK" in capsys.readouterr().out
    assert sorted(os.listdir(out)) == ["m.8.motion.json"]


# ===========================================================================
# F-0d033bd6 — make_shotset_sheet writes nothing when an argument refusal fires
# ===========================================================================


def test_mode_scale_without_a_second_set_leaves_no_output_directory(tmp_path):
    """THE OPERAND: `--out` after the `--mode=scale`/`--second` refusal.

    A DISTINCT site from the four closed in F-1d5b6931 (`composite_reference`,
    `make_lift_sheet`, `make_review_clip`, `measure_lift`), none of which named this tool.
    Nine refusals sat below the first write here and `READBACK_REASONS` marked every one of
    them "REVIEW: not a read-back".
    """
    import make_shotset_sheet as MSS

    ortho = tmp_path / "ortho"
    ortho.mkdir()
    (ortho / "turnaround_manifest.json").write_text(json.dumps({
        "camera": {"projection": "ORTHO", "ortho_scale": 1.0,
                   "ortho_scale_source": "solved", "radius": 3.0, "elevation_deg": 15.0},
        "resolution": [64, 64], "views": [],
        "source": {"glb": "x.glb", "sha256": "0" * 64},
        "blender": {"version": "5.2"}, "tool_version": "t"}), encoding="utf-8")
    out = tmp_path / "sheet"
    with pytest.raises(MSS.ShotsetSheetError, match="only one was given") as exc:
        MSS.main([f"--ortho={ortho}", f"--out={out}", "--mode=scale"])
    assert exc.value.evidence["missing"] == "--second", exc.value.evidence
    assert not out.exists(), "a refused run left its output directory behind"


def test_no_refusal_in_make_shotset_sheet_sits_below_its_first_write():
    """The family, keyed on the AST: all nine refusals, not the one the fixture drives."""
    import test_instrument_write_ordering as WO

    assert WO.refusals_below_the_first_write("make_shotset_sheet") == []


# ===========================================================================
# F-734951dc — three classes that declared a gate id and dropped their evidence
# ===========================================================================


@pytest.mark.parametrize("module,cls", [
    ("extract_clip_frames", "ClipReadError"),
    ("measure_tracking", "TrackingError"),
    ("measure_tracking", "AnchorMismatch"),
])
def test_the_three_evidence_dropping_classes_store_what_they_are_passed(module, cls):
    """THE OPERAND: `.evidence` on an instance built the way the raise sites build one.

    Measured on the base tree: `ClipReadError('no WxH in the stream line', {'line': 'abc'})`
    gave `hasattr(e, 'evidence') == False` and `str(e)` equal to the 2-tuple repr, so the
    `stderr_tail` saying WHY ffmpeg refused was collected, passed and thrown away. A
    constructor probe over every `ArmatureError` subclass defined in this domain's 42 files
    found exactly these three.
    """
    mod = __import__(module)
    exc = getattr(mod, cls)("a message", {"line": "abc"})
    assert isinstance(exc, ArmatureError)
    assert exc.evidence == {"line": "abc"}
    assert str(exc) == "a message" or str(exc).endswith("a message"), str(exc)
    assert not str(exc).startswith("("), str(exc)
    # the one-argument form the two measure_tracking sites use today still works
    assert getattr(mod, cls)("just a message").evidence == {}


def test_the_clip_read_refusal_carries_the_stream_line_it_could_not_parse(monkeypatch,
                                                                          tmp_path):
    """The `:62` site, driven: `probe` on an ffmpeg report whose stream line holds no WxH.
    `tests/test_extract_clip_frames.py:57` constructs the class and never reads its
    evidence, which is how this survived."""
    import extract_clip_frames as ECF

    class _Proc:
        stderr = "  Stream #0:0: Video: h264, yuv420p, 25 fps\n"

    monkeypatch.setattr(ECF.subprocess, "run", lambda *a, **k: _Proc())
    with pytest.raises(ECF.ClipReadError) as exc:
        ECF.probe(str(tmp_path / "clip.mp4"))
    assert exc.value.evidence["line"].startswith("Stream #0:0"), exc.value.evidence


# ===========================================================================
# F-0c850c1a — the printed order line names the ties the record has carried since wave 12
# ===========================================================================


def test_the_printed_order_line_names_the_tie_count(tmp_path, capsys, monkeypatch):
    """THE OPERAND: the PRINTED `order` line, on the walk shape `order_check`'s own
    docstring names — distinct moving frames then a hold, compared against an exact copy.

    Measured on the base tree, 8 moving frames + a 4-frame hold: `order_check` returned
    `n_tied 5`, `tie_groups [[7,8,9,10,11]]`, `min_margin 0.0` — and the console read
    `order  12/12 on the diagonal, 0 displaced, min margin 0.000`, which is what a session
    quotes into a report. A real group displacement inside a tie set reads the same way.
    """
    import measure_cascade_clip as MCC

    d = tmp_path / "frames"
    d.mkdir()
    frames = []
    for i in range(12):
        a = np.zeros((32, 32, 3), np.uint8)
        band = min(i, 7)                      # 8 distinct frames, then a 4-frame hold
        a[:, :, 0] = (band * 13) % 256
        a[band % 32, :, 1] = 255
        Image.fromarray(a).save(d / f"{i:05d}.png")
        frames.append(a)

    monkeypatch.setattr(MCC, "ffprobe_stream", lambda path: {
        "raw": [], "stream": "Video: h264, 32x32", "fps": 16.0,
        "width": 32, "height": 32})
    monkeypatch.setattr(MCC, "decode",
                        lambda path, w, h: [f.copy() for f in frames])
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"not really a clip")
    out = tmp_path / "cmp"

    MCC.main([f"--clip={clip}", f"--frames={d}", f"--out={out}",
              "--expect-frames=12", "--expect-fps=16"])

    printed = capsys.readouterr().out
    order = [l for l in printed.splitlines() if l.startswith("order")]
    assert len(order) == 1, printed
    rec = json.loads((out / "cascade_decode_compare.json").read_text(encoding="utf-8"))
    o = rec["order"]
    assert o["n_tied"] > 0, o          # the fixture is the ambiguous shape, or it proves nothing
    assert f"{o['n_tied']} tied" in order[0], order[0]
    assert "group" in order[0], order[0]
    if o["min_margin"] == 0.0:
        assert "NONE" in order[0], order[0]


def test_the_margin_word_only_replaces_a_zero():
    import measure_cascade_clip as MCC

    assert MCC._margin(0.0).startswith("0.000 (NONE")
    assert MCC._margin(1.25) == "1.250"


# ===========================================================================
# F-90c26d7b — the crop strip records what it left out
# ===========================================================================


def test_a_contact_strip_beside_the_frames_is_recorded_not_silently_dropped(tmp_path):
    """THE OPERAND: the SIDECAR of a strip cut from a directory holding
    `strip_every8.png` beside `00000.png`.

    `sheet_compose.frames_by_number` RAISES on a stray and named the only difference
    between the two implementations as directory-versus-listing. `make_crop_strip` FILTERS
    — correctly, because this repo's own tools write contact strips into a frames directory
    — but it did so in silence, narrowing the population of a tool whose whole product is
    provenance a later reader can re-cut from.
    """
    import make_crop_strip as MCS

    frames = tmp_path / "frames"
    frames.mkdir()
    a = np.full((32, 32, 3), 120, np.uint8)
    Image.fromarray(a).save(frames / "00000.png")
    Image.fromarray(a).save(frames / "strip_every8.png")

    out = tmp_path / "strip.png"
    MCS.main([f"--frames={frames}", "--boxes=0:0,0,16,16", f"--out={out}",
              "--scale=1", "--title=t"])
    side = json.loads((tmp_path / "strip.json").read_text(encoding="utf-8"))
    assert side["excluded_png"] == ["strip_every8.png"], side["excluded_png"]


def test_the_two_predicates_partition_the_png_listing(tmp_path):
    """`strays_beside` is asserted to be the exact complement of `frames_by_number`, so it
    cannot drift into being something else."""
    import make_crop_strip as MCS

    frames = tmp_path / "frames2"
    frames.mkdir()
    a = np.full((8, 8, 3), 60, np.uint8)
    for name in ("00000.png", "00007.png", "strip_every8.png", "contact.PNG"):
        Image.fromarray(a).save(frames / name)
    (frames / "notes.txt").write_text("x", encoding="utf-8")

    by_number, strays = MCS.numbered_and_strays(str(frames))
    pngs = {n for n in os.listdir(frames) if n.lower().endswith(".png")}
    kept = {os.path.basename(p) for p in by_number.values()}
    assert kept | set(strays) == pngs, (sorted(kept), sorted(strays), sorted(pngs))
    assert kept & set(strays) == set()
    assert sorted(strays) == ["contact.PNG", "strip_every8.png"], strays


def test_the_sheet_compose_docstring_names_the_difference_that_is_real():
    """The sentence that was wrong is corrected in place, not deleted: both behaviours are
    named, with the caller each is right for."""
    import sheet_compose

    doc = sheet_compose.frames_by_number.__doc__
    assert "make_crop_strip" in doc
    assert "FILTERS" in doc and "RAISES" in doc, doc


# ===========================================================================
# The gate legs under -O, in-process: an `assert` would be gone, a `raise` is not
# ===========================================================================


def test_every_refusal_this_amend_added_survives_python_optimize():
    """`-O` deletes an `assert`; the six refusals added or repaired here are `raise`s.

    Driven in a child interpreter with `PYTHONOPTIMIZE=1` set in the ENVIRONMENT (not `-O`
    alone), because a subprocess inherits the environment and not the parent's flag.
    """
    script = r"""
import json, os, sys, tempfile
sys.path.insert(0, os.path.join(os.environ["ARMATURE_REPO"], "tools"))
assert __debug__ is False or True
if __debug__:
    raise SystemExit("PYTHONOPTIMIZE did not reach this interpreter")
import stage_render, resample_motion, measure_smoothness, make_shotset_sheet
from armature_core.errors import ArmatureError, SpecError
fired = []
try:
    stage_render._parse_argv(["--spec=s", "--out=o", "--nope=1"])
except SpecError:
    fired.append("stage_render_unknown_flag")
d = tempfile.mkdtemp()
m = os.path.join(d, "m.json")
open(m, "w").write(json.dumps({"frames": [
    {"frame": i, "root": [0.0, 0.0, 0.0],
     "local": {"hips": [[1.0,0.0,0.0],[0.0,1.0,0.0],[0.0,0.0,1.0]]}} for i in range(4)]}))
try:
    resample_motion.main(["--motion=" + m, "--frames=1", "--out=" + os.path.join(d, "r")])
except resample_motion.ResampleArgError:
    fired.append("resample_frames_bound")
try:
    measure_smoothness._summarisable(None, "b", "A", {"body": [[]]}, m)
except measure_smoothness.SmoothnessInputError:
    fired.append("smoothness_summary")
print(json.dumps(sorted(fired)))
"""
    env = dict(os.environ, PYTHONOPTIMIZE="1", ARMATURE_REPO=REPO)
    proc = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True,
                          env=env)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout.strip().splitlines()[-1]) == [
        "resample_frames_bound", "smoothness_summary", "stage_render_unknown_flag"]
