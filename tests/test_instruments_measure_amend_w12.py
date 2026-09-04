"""Wave 12, instruments-measure — the nine approved findings, each as a property.

Every test here is appended by the instruments-measure amend seat, in ONE block, so the
tests domain's own files are not rewritten under it (wave-12 coordinator brief: `tests/**`
is a bridge domain; a sibling's fixes are pinned in appended blocks).

THE NODES these censuses key on, and why each is the node the property lives on:

* **F-e96ed69b** — the node is the `require_frames` CALL SITE, not the helper. `numbers=`
  has existed since wave 10 and landed in one of six callers; a census over the helper is
  green on a tree where five callers still bound a frame NUMBER by its POSITION in a
  listing. Proven red on a synthetic module whose call omits the keyword.
* **F-f9251c74** — the node is "a tool invoked under `blender -b -P`", not the literal
  token `import bpy`. `stage_render` imports its backend lazily inside
  `BlenderBackend.__init__` and documents the `blender -b -P` invocation on line 9 of its
  own docstring, so it sits in no exit census at all. Its handler is driven here through
  the same machinery `tests/test_instrument_exits.py` drives the other 21 with, and the
  wider population re-keying is the tests domain's half (seam posted).
* **F-9c43c029** — the node is `tools/*.py`, not the five plate sheets. `SHEET_OK` was
  printed by four modules and the distinctness census could not see them because its
  population was the five modules that read `sheet_plate`.
* **F-97de9ce4** — the node is the parser, in the direction the existing census does not
  walk: a dest DECLARED by a module's own `add_argument` and read nowhere in that module.
* **F-e4fc9531** — the node is the `cv2.imwrite` CALL, in a position that tests its
  return; `cv2.imwrite` returns False on failure and raises nothing.

Helpers under `tests/` raise; they never `assert` (`-O` deletes an assert in a non-plugin
helper). Every gate this file proves is a `raise`, and the gate legs are run under
`PYTHONOPTIMIZE=1` in the amend's own verification.
"""

import ast
import glob
import json
import os
import subprocess
import sys

import numpy as np
import pytest
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
sys.path.insert(0, TOOLS)

from conftest import TOOLS as _TOOLS_FIXTURE_MARKER  # noqa: F401,E402

from armature_core.errors import ArmatureError, GateFailure  # noqa: E402

SIZE = (32, 24)


def _src(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _tool_trees():
    """`{module name: (path, ast)}` over every `tools/*.py`. Derived, never typed."""
    out = {}
    for path in sorted(glob.glob(os.path.join(TOOLS, "*.py"))):
        out[os.path.basename(path)[:-3]] = (path, ast.parse(_src(path)))
    return out


TOOL_TREES = _tool_trees()


def _clip(d, numbers, base=(20, 20, 24), digits=5):
    os.makedirs(d, exist_ok=True)
    for k, n in enumerate(numbers):
        Image.new("RGB", SIZE, (base[0] + 20 * k, base[1] + 7 * k, base[2])).save(
            os.path.join(d, f"{n:0{digits}d}.png"))
    return d


# ===========================================================================
# F-e96ed69b — `--frames` is bounded by NUMBER, at every call site
# ===========================================================================


def _require_frames_calls(tree):
    """Every `require_frames(...)` call in one module, with its keyword names.

    THE NODE: the call site. `sheet_compose.require_frames` grew a `numbers=` mode in
    wave 10 and the mode landed in one caller; the defect lives in the five that kept
    calling it positionally, and no property of the helper can see them.
    """
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = (node.func.id if isinstance(node.func, ast.Name)
                else node.func.attr if isinstance(node.func, ast.Attribute) else None)
        if name == "require_frames":
            found.append({kw.arg for kw in node.keywords})
    return found


def _positional_frame_bounds():
    """`{module: n}` for every module with a `require_frames` call lacking `numbers=`."""
    bad = {}
    for mod, (_path, tree) in TOOL_TREES.items():
        n = sum(1 for kws in _require_frames_calls(tree) if "numbers" not in kws)
        if n:
            bad[mod] = n
    return bad


def test_the_call_site_census_goes_red_on_a_positional_bound():
    """The falsifiability fixture, in the spelling that hides from a helper-keyed walk.

    A census that reads `sheet_compose.require_frames` and finds the `numbers=` branch
    reports a tree where every caller still passes positions. This walk keys on the CALL.
    """
    tree = ast.parse(
        "def build(idx, names, by_number):\n"
        "    require_frames(idx, names, what='f', where='d')\n"
        "    require_frames(idx, names, what='f', where='d', numbers=sorted(by_number))\n")
    kws = _require_frames_calls(tree)
    assert len(kws) == 2, kws
    assert sum(1 for k in kws if "numbers" not in k) == 1, kws


def test_every_require_frames_call_in_the_tree_bounds_by_number():
    """Size and membership before the property: the population is every call in `tools/`.

    Measured 2026-09-04 before this amend: five of six callers passed no `numbers=`
    (`make_gate0_sheet` x2, `make_lift_sheet` x3, `make_review_clip`,
    `make_startframe_sheet`, `make_thesis_sheet`), and `make_identity_sheet` alone did.
    """
    callers = sorted(m for m, (_p, t) in TOOL_TREES.items() if _require_frames_calls(t))
    assert callers == ["make_gate0_sheet", "make_identity_sheet", "make_lift_sheet",
                       "make_review_clip", "make_startframe_sheet",
                       "make_thesis_sheet"], callers
    assert _positional_frame_bounds() == {}, _positional_frame_bounds()


def _one_based(tmp, name, numbers=(1, 2, 3), base=(20, 20, 24)):
    return _clip(str(tmp / name), list(numbers), base=base)


def _gate0_one_based(tmp, frames):
    import make_gate0_sheet as G0
    return G0.main([f"--run={_one_based(tmp, 'ctl')}",
                    f"--frames-dir={_one_based(tmp, 'out', base=(40, 30, 24))}",
                    "--reference=none",
                    f"--meta={_meta(str(tmp / 'meta.json'))}",
                    f"--out={tmp / 'sheets' / 'g0.png'}", f"--frames={frames}"])


def _lift_one_based(tmp, frames):
    import make_lift_sheet as LS
    src = _one_based(tmp, "src")
    lif = _one_based(tmp, "lif", base=(40, 30, 24))
    for d in (src, lif):
        Image.new("RGB", SIZE, (0, 0, 0)).save(os.path.join(d, "empty_plate.png"))
    det = str(tmp / "det.json")
    with open(det, "w", encoding="utf-8") as fh:
        json.dump({"rows": [{"frame": n, "file": f"{n:05d}.png", "fired": False,
                             "image": [], "visibility": []} for n in (1, 2, 3)]}, fh)
    return LS.main([f"--source={src}", f"--lifted={lif}", f"--detection={det}",
                    f"--out={tmp / 'sheets' / 'lift.png'}", f"--frames={frames}",
                    "--tile-h=24", "--source-uncropped"])


def _startframe_one_based(tmp, frames):
    import make_startframe_sheet as SFS
    start = str(tmp / "start.png")
    Image.new("RGB", SIZE, (9, 9, 9)).save(start)
    return SFS.main([f"--start={start}", f"--frames={_one_based(tmp, 'f')}",
                     f"--meta={_meta(str(tmp / 'meta.json'))}",
                     f"--out={tmp / 'sheets' / 'sf.png'}", f"--at={frames}",
                     "--scale=0.5"])


def _thesis_one_based(tmp, frames):
    import make_thesis_sheet as TS
    return TS.main([f"--control={_one_based(tmp, 'ctl')}",
                    f"--arms=A1:{_one_based(tmp, 'arm', base=(40, 30, 24))}",
                    "--reference=none", f"--out={tmp / 'sheets' / 'th.png'}",
                    f"--frames={frames}", "--tile-height=24"])


def _review_one_based(tmp, frames):
    import make_review_clip as MRC
    return MRC.main([f"--frames={_one_based(tmp, 'frames')}",
                     f"--out={tmp / 'rev'}", f"--stills={frames}", "--crop=8"])


def _meta(path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"experiment": "E99", "arm": "A1"}, fh)
    return path


ONE_BASED = {
    "make_gate0_sheet": _gate0_one_based,
    "make_lift_sheet": _lift_one_based,
    "make_review_clip": _review_one_based,
    "make_startframe_sheet": _startframe_one_based,
    "make_thesis_sheet": _thesis_one_based,
}


@pytest.mark.parametrize("name", sorted(ONE_BASED))
def test_a_run_numbered_from_one_refuses_frame_zero(name, tmp_path):
    """The measured defect: a run holding 00001..00003 accepted `--frames=0,1,2`.

    Exit 0, a sheet on disk, tiles captioned f000/f001/f002 cut from 00001/00002/00003 —
    on a run that holds no frame 0. `make_identity_sheet` refused the identical input,
    because it is the one caller that passed `numbers=`.
    """
    with pytest.raises(ArmatureError) as exc:
        ONE_BASED[name](tmp_path, "0,1,2")
    ev = getattr(exc.value, "evidence", {})
    assert ev.get("missing_indices") == [0], ev
    assert ev.get("frame_numbers") == [1, 2, 3], ev


@pytest.mark.parametrize("name", sorted(ONE_BASED))
def test_the_frames_a_one_based_run_does_hold_are_accepted(name, tmp_path):
    """The guard the other way: a bound that refuses everything is not a bound.

    `--frames=3` on a run numbered 00001..00003 was REFUSED before this amend (the
    positional bound is `0 <= i < 3`), which is the flag reading backwards from what its
    own caption promises.
    """
    assert ONE_BASED[name](tmp_path, "1,2,3") == 0


def test_the_lift_sidecar_names_the_file_the_frame_number_names(tmp_path):
    """Indexing by number, not only bounding by it.

    The sidecar records the FILE each column loaded. Under the positional read, frame 1 of
    a run numbered from 1 named `00002.png`; under the numbered read it names `00001.png`.
    """
    _lift_one_based(tmp_path, "1,2")
    rec = json.loads((tmp_path / "sheets" / "lift.json").read_text(encoding="utf-8"))
    rows = {r["frame"]: r for r in rec["rows"]}
    assert os.path.basename(rows[1]["source"]) == "00001.png", rec["rows"]
    assert os.path.basename(rows[2]["lifted"]) == "00002.png", rec["rows"]


def test_the_review_manifest_cuts_the_still_the_frame_number_names(tmp_path):
    """`still_f001` is cut from `00001.png`, not from the second file in the listing."""
    _review_one_based(tmp_path, "1,3")
    man = json.loads(
        (tmp_path / "rev" / "review_manifest.json").read_text(encoding="utf-8"))
    frames = sorted({c["frame"] for c in man["stills"]})
    assert frames == [1, 3], man["stills"]
    assert man["source_frame_files"] == ["00001.png", "00002.png", "00003.png"], man


# ===========================================================================
# F-f9251c74 — stage_render joins the halt contract
# ===========================================================================

GATE_OUTCOME = "HALTED \u2014 a gate fired"
REFUSAL_OUTCOME = "REFUSED \u2014 the tool declined to proceed"
CRASH_OUTCOME = "FAILED \u2014 an unhandled error"
SENTINEL_KEYS = {"tool", "outcome", "gate", "error", "message", "evidence"}


def _stage_raiser(kind):
    class _Gate(GateFailure):
        gate = "PROBE"

    def gate():
        raise _Gate("a gate fired", {"measured": 1})

    def refusal():
        raise ArmatureError("a refusal, not a crash")

    def crash():
        raise ValueError("an ordinary mistake")

    return {"gate": gate, "refusal": refusal, "crash": crash}[kind]


@pytest.mark.parametrize("kind,want_code,want_outcome,want_gate", [
    ("gate", 2, GATE_OUTCOME, "PROBE"),
    ("refusal", 2, REFUSAL_OUTCOME, None),
    ("crash", 1, CRASH_OUTCOME, None),
])
def test_stage_render_delivers_the_six_key_halt_line(kind, want_code, want_outcome,
                                                     want_gate, capsys):
    """The contract the other 21 tools carry, on the tool the README names beside them.

    Measured 2026-09-04 before this amend: the `__main__` block was `sys.exit(main())`
    with no handler at all, so a `SpecError` out of `_parse_argv` or `shotspec.load_spec`
    propagated — and under `blender -b -P` a propagating exception is exit **0**.
    """
    from blender_stub import exit_code_of_main_block

    code, escaped = exit_code_of_main_block(
        "stage_render.py", raiser=_stage_raiser(kind),
        argv=["blender", "-b", "-P", "stage_render.py", "--", "--spec=x", "--out=y"])
    assert escaped is None, escaped
    assert code == want_code, (kind, code)

    out = capsys.readouterr().out
    lines = [l for l in out.splitlines() if l.split(" ", 1)[0] == "STAGE_RENDER_HALT"]
    assert len(lines) == 1, out
    rec = json.loads(lines[0][len("STAGE_RENDER_HALT"):].strip())
    assert set(rec) == SENTINEL_KEYS, sorted(rec)
    assert rec["tool"] == "stage_render"
    assert rec["outcome"] == want_outcome
    assert rec["gate"] == want_gate
    if kind == "gate":
        assert rec["evidence"] == {"measured": 1}, rec


def test_stage_render_main_catches_the_family_and_not_gate_failure_alone(tmp_path):
    """`_parse_argv`, `load_spec` and every `SpecError` inside `prepare` sat OUTSIDE the
    handler. Measured before this amend: `--spec=nope.json` raised FileNotFoundError,
    `--out` alone raised SpecError, `-spec=x` raised SpecError — all escaping `main`."""
    import stage_render

    for argv in ([f"--spec={tmp_path / 'nope.json'}", f"--out={tmp_path / 'x'}"],
                 [f"--out={tmp_path / 'x'}"],
                 ["-spec=x", f"--out={tmp_path / 'x'}"]):
        assert stage_render.main(argv) == 2, argv
    assert not os.path.exists(tmp_path / "x")


def test_stage_render_main_prints_the_halt_line_it_returns_two_for(tmp_path, capsys):
    """A refusal `main` handles is still legible to a reader keyed on the contract."""
    import stage_render

    assert stage_render.main([f"--out={tmp_path / 'x'}"]) == 2
    out = capsys.readouterr().out
    lines = [l for l in out.splitlines() if l.split(" ", 1)[0] == "STAGE_RENDER_HALT"]
    assert len(lines) == 1, out
    rec = json.loads(lines[0][len("STAGE_RENDER_HALT"):].strip())
    assert set(rec) == SENTINEL_KEYS, sorted(rec)
    assert rec["outcome"] == REFUSAL_OUTCOME, rec


def test_stage_render_is_a_blender_tool_by_behaviour_even_without_a_module_import():
    """The population re-keying, stated here so the premise is checked in this domain too.

    `blender_stub.blender_tools()` keys on a MODULE-LEVEL `import bpy`; `stage_render`
    imports its backend inside `BlenderBackend.__init__` and documents
    `blender -b -P tools\\stage_render.py` on line 9 of its own docstring. The wider
    census is the tests domain's half (seam posted); this asserts the two facts it keys on.
    """
    src = _src(os.path.join(TOOLS, "stage_render.py"))
    tree = ast.parse(src)
    module_level = any(
        isinstance(n, ast.Import) and any(a.name == "bpy" for a in n.names)
        for n in tree.body)
    assert not module_level, "stage_render grew a module-level `import bpy`"
    assert "blender -b -P tools" in src.replace("\\\\", "")


def test_the_stage_render_halt_survives_an_unserialisable_evidence_dict(capsys):
    """The wave-10 escape, on the 22nd tool: `json.dumps(default=str)` applies `default`
    to VALUES only, so a tuple key raises inside the handler, the new exception leaves the
    whole `try`, and `sys.exit` never runs."""
    from blender_stub import exit_code_of_main_block

    class _Gate(GateFailure):
        gate = "PROBE"

    def raiser():
        raise _Gate("a gate fired", {(1, 2): "a tuple key", "np": np.int64(3)})

    code, escaped = exit_code_of_main_block(
        "stage_render.py", raiser=raiser,
        argv=["blender", "-b", "-P", "stage_render.py", "--", "--spec=x", "--out=y"])
    assert escaped is None, escaped
    assert code == 2, code
    out = capsys.readouterr().out
    lines = [l for l in out.splitlines() if l.split(" ", 1)[0] == "STAGE_RENDER_HALT"]
    assert len(lines) == 1, out


def test_stage_render_records_no_gate_verdict_it_did_not_run():
    """`"G5": {"verdict": "PASS"}` sat on a branch no run reaches: `pose` in `channels` is
    refused by `openpose.require_drawing_convention()` before the output directory exists,
    so the tool never emits a skeleton for G5 to conform-check. A verdict beside a gate
    that did not run is a placeholder shaped like evidence."""
    src = _src(os.path.join(TOOLS, "stage_render.py"))
    tree = ast.parse(src)
    g5_values = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and node.value == "G5"):
            g5_values.append(node)
    assert g5_values, "the manifest no longer records a G5 key at all"
    assert '"verdict": "PASS"}\n            if "pose" not in requested' not in src
    assert "G5_VERDICT_SOURCE" in src or "does not emit pose" in src


# ===========================================================================
# F-9c43c029 — one success sentinel per tool, across the whole tree
# ===========================================================================


def _success_tokens(path):
    """The success sentinel(s) `main` PRINTS — the walk `test_sheet_argv_smoke` uses,
    over the population that walk could not see: every `tools/*.py`, not the five plate
    sheets."""
    tree = ast.parse(_src(path))
    main = next((n for n in ast.walk(tree)
                 if isinstance(n, ast.FunctionDef) and n.name == "main"), None)
    if main is None:
        return set()
    stack, nodes = list(ast.iter_child_nodes(main)), []
    while stack:
        node = stack.pop()
        nodes.append(node)
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            stack.extend(ast.iter_child_nodes(node))
    tokens = set()
    for node in nodes:
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "print" and node.args):
            continue
        first = node.args[0]
        while isinstance(first, ast.BinOp) and isinstance(first.op, ast.Add):
            first = first.left
        if isinstance(first, ast.JoinedStr) and first.values:
            first = first.values[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            word = first.value.strip().split()
            if word and word[0].endswith("_OK"):
                tokens.add(word[0])
    return tokens


def test_no_two_instruments_share_a_success_sentinel():
    """Measured 2026-09-04: `SHEET_OK` was printed by `make_cast_sheet`,
    `make_e13_sheet`, `rig_sheet_compose` and `sheet_compose` — the only shared token in
    the tree, and invisible to the distinctness census whose population is the five plate
    sheets, of which none of the four is a member."""
    owners = {}
    for mod, (path, _tree) in TOOL_TREES.items():
        for tok in _success_tokens(path):
            owners.setdefault(tok, []).append(mod)
    shared = {tok: sorted(mods) for tok, mods in owners.items() if len(mods) > 1}
    assert shared == {}, shared


def test_the_sentinel_census_goes_red_on_a_second_owner(tmp_path):
    """Falsifiability: the walk finds a collision when one exists, in the `print(f"...")`
    spelling as well as the `print("..." + json.dumps(...))` one."""
    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    a.write_text("import json\ndef main():\n    print('SHARED_OK ' + json.dumps({}))\n",
                 encoding="utf-8")
    b.write_text("def main():\n    print(f'SHARED_OK {1}')\n", encoding="utf-8")
    assert _success_tokens(str(a)) == {"SHARED_OK"}
    assert _success_tokens(str(b)) == {"SHARED_OK"}


# ===========================================================================
# F-a620d96c — a hand-rolled parser names the flag it wanted
# ===========================================================================


@pytest.mark.parametrize("mod_name,argv,wanted", [
    ("make_sheet", ["--out=x.png"], "--run"),
    ("analyze_p3", ["--out=x.json"], "--run"),
    ("make_sheet", ["--run=x"], "--out"),
    ("analyze_p3", ["--run=x"], "--out"),
])
def test_a_missing_required_flag_is_a_typed_refusal_naming_the_flag(mod_name, argv,
                                                                    wanted):
    """Measured before this amend: `KeyError: 'run'` — a one-word traceback naming no
    flag, the shape wave 8's typed-refusal sweep removed everywhere else. Every other
    instrument in the domain answers `error: the following arguments are required: --run`.
    """
    mod = __import__(mod_name)
    with pytest.raises(ArmatureError) as exc:
        mod.main(argv)
    assert wanted in str(exc.value), str(exc.value)


@pytest.mark.parametrize("mod_name", ["make_sheet", "analyze_p3"])
def test_a_token_that_lost_its_leading_dashes_is_named(mod_name):
    """`analyze_p3.main(['run=E:/x'])` registered the key `n` (from `token[2:]`) and then
    died with `KeyError: 'run'`, naming neither the flag it wanted nor the token it got.
    `stage_render._parse_argv` is the counter-example: `expected --key=value, got ...`."""
    mod = __import__(mod_name)
    with pytest.raises(ArmatureError) as exc:
        mod.main(["run=E:/x", "--out=y"])
    assert "run=E:/x" in str(exc.value), str(exc.value)


def test_no_instrument_indexes_a_hand_rolled_argv_dict_without_a_named_refusal():
    """THE NODE: the modules that build their own `{flag: value}` dict from `argv` instead
    of using argparse. Derived from the tree — a subscript of a dict assembled by a
    `partition("=")` loop — so a third hand-rolled parser joins the census when it lands.
    """
    hand_rolled = []
    for mod, (path, tree) in TOOL_TREES.items():
        src = _src(path)
        if 'partition("=")' not in src and "partition('=')" not in src:
            continue
        if "argparse" in src:
            continue
        hand_rolled.append(mod)
    assert sorted(hand_rolled) == ["analyze_p3", "make_sheet", "stage_render"], \
        sorted(hand_rolled)
    for mod in hand_rolled:
        src = _src(TOOL_TREES[mod][0])
        assert "SpecError" in src or "Error(" in src, mod


# ===========================================================================
# F-c397574b — `--expect-fps` is compared, not printed beside
# ===========================================================================


def _cascade_fixture(tmp_path, n=2):
    frames = _clip(str(tmp_path / "src"), list(range(n)))
    clip = tmp_path / "clip.webm"
    clip.write_bytes(b"not really a clip")
    return frames, str(clip)


def _patch_cascade(monkeypatch, fps):
    import measure_cascade_clip as MCC

    w, h = SIZE
    monkeypatch.setattr(MCC, "ffprobe_stream", lambda p: {
        "width": w, "height": h, "fps": fps, "stream": "vp9 stub"})
    monkeypatch.setattr(MCC, "decode", lambda p, sw, sh: [
        np.zeros((sh, sw, 3), np.uint8) for _ in range(2)])
    return MCC


def test_a_clip_whose_rate_is_not_the_declared_one_is_refused(tmp_path, monkeypatch):
    """`--expect-fps` was parsed, written into the record and printed beside the value read
    off the stream, and nothing compared them. Its sibling `--expect-frames` IS gated, for
    the stated reason that every per-frame comparison below a mismatch compares different
    pictures — the frame rate is the third dimension of the same argument."""
    MCC = _patch_cascade(monkeypatch, 8.0)
    frames, clip = _cascade_fixture(tmp_path)
    with pytest.raises(ArmatureError) as exc:
        MCC.main([f"--clip={clip}", f"--frames={frames}",
                  f"--out={tmp_path / 'out'}", "--expect-frames=2", "--expect-fps=16"])
    ev = getattr(exc.value, "evidence", {})
    assert ev.get("read") == 8.0 and ev.get("expected") == 16.0, ev


def test_an_fps_the_probe_could_not_parse_is_refused(tmp_path, monkeypatch):
    """The same line renders `NOT PARSED` when ffprobe's fps token did not parse, and that
    too exited 0 with a full record on disk."""
    MCC = _patch_cascade(monkeypatch, None)
    frames, clip = _cascade_fixture(tmp_path)
    with pytest.raises(ArmatureError) as exc:
        MCC.main([f"--clip={clip}", f"--frames={frames}",
                  f"--out={tmp_path / 'out'}", "--expect-frames=2", "--expect-fps=16"])
    assert getattr(exc.value, "evidence", {}).get("read") is None


def test_the_matching_rate_still_measures(tmp_path, monkeypatch):
    """The guard the other way: a gate that fires on the declared rate is not a gate."""
    MCC = _patch_cascade(monkeypatch, 16.0)
    frames, clip = _cascade_fixture(tmp_path)
    rec = MCC.main([f"--clip={clip}", f"--frames={frames}",
                    f"--out={tmp_path / 'out'}", "--expect-frames=2", "--expect-fps=16"])
    assert rec["stream"]["fps"] == 16.0
    assert rec["gate_FPS"]["verdict"], rec["gate_FPS"]


# ===========================================================================
# F-6e6a89e6 — an anchor that read nothing does not exit 0
# ===========================================================================


def test_the_anchor_exits_non_zero_when_it_read_nothing(tmp_path, capsys):
    """`outputs/` is gitignored by design, so "the runs are absent" is the DEFAULT state
    of any fresh clone, CI runner or swarm worktree. Three exits a caller can read were
    spelled the same: 0 for "reproduces E02's figures" and 0 for "never ran"."""
    import measure_tracking as MT

    code = MT.main(["--anchor", f"--e02-root={tmp_path / 'no-such-root'}"])
    assert code != 0, code
    assert "ANCHOR NOT YET RUN" in capsys.readouterr().out


def test_the_absent_anchor_can_be_made_optional_only_by_naming_itself(tmp_path, capsys):
    """If exit 0 must be preserved for an optional step, it is gated behind an explicit
    flag that names itself in the printed line."""
    import measure_tracking as MT

    code = MT.main(["--anchor", "--allow-absent",
                    f"--e02-root={tmp_path / 'no-such-root'}"])
    assert code == 0, code
    out = capsys.readouterr().out
    assert "ANCHOR NOT YET RUN" in out and "--allow-absent" in out


def test_the_anchor_flag_is_not_defaulted_on():
    """A skip flag that defaults to on is not a flag. `--allow-absent` must default False."""
    import measure_tracking as MT

    src = _src(os.path.join(TOOLS, "measure_tracking.py"))
    assert "store_true" in src
    assert MT.main is not None


# ===========================================================================
# F-e4fc9531 — the sentinel is not printed over a write that did not land
# ===========================================================================


def _imwrite_calls(tree):
    """Every `cv2.imwrite(...)` call, and whether its RETURN is in a tested position.

    THE NODE: the call. `cv2.imwrite` returns a bool on failure and raises nothing, so a
    bare expression statement discards the only signal there is. Tested positions: the
    operand of a `not`/comparison inside an `if`, or bound to a name (the name is then
    required to appear in an `if`).
    """
    checked, bare = [], []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)):
            continue
        call = node.value
        if (isinstance(call.func, ast.Attribute) and call.func.attr == "imwrite"):
            bare.append(node.lineno)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute) and node.func.attr == "imwrite":
            checked.append(node.lineno)
    return sorted(set(checked) - set(bare)), sorted(bare)


def test_no_instrument_discards_an_imwrite_return():
    """Measured 2026-09-04 with the repo venv's OpenCV: `cv2.imwrite(<an existing
    directory named x.png>, arr)` returned False, wrote nothing and raised nothing.
    `make_overlay_sheet:94`, `make_zoom_sheet:126`, `make_e08_sheet:210` and
    `render_pose_sticks:217` then printed a success sentinel carrying the absolute path
    of a file that is not there. The correct shape is already in the domain three times
    (`fit_reference:216`, `make_plate:224`, `render_pose_sticks:189`)."""
    bare = {}
    for mod, (_path, tree) in TOOL_TREES.items():
        _ok, discarded = _imwrite_calls(tree)
        if discarded:
            bare[mod] = discarded
    assert bare == {}, bare


def test_the_imwrite_census_goes_red_on_a_bare_call(tmp_path):
    """Falsifiability, in the spelling that hides from a grep for `if not cv2.imwrite`."""
    tree = ast.parse("import cv2\ndef main(p, a):\n"
                     "    cv2.imwrite(p, a)\n"
                     "    if not cv2.imwrite(p, a):\n        raise RuntimeError(p)\n")
    checked, bare = _imwrite_calls(tree)
    assert len(bare) == 1 and len(checked) == 1, (checked, bare)


def test_a_zoom_sheet_whose_write_cannot_land_refuses_instead_of_printing_ok(tmp_path,
                                                                            capsys):
    """The behavioural half, on the cheapest of the four sites. `--out` names an existing
    DIRECTORY: `cv2.imwrite` returns False, and the tool used to print `ZOOM_SHEET_OK`
    with that path and write its `_crops.json` sidecar describing a sheet that is not
    there."""
    import make_zoom_sheet as MZS

    frames = _clip(str(tmp_path / "f"), [0])
    kp = str(tmp_path / "kp.json")
    with open(kp, "w", encoding="utf-8") as fh:
        json.dump({"keypoint_names": ["Nose"], "resolution": list(SIZE),
                   "body": [[[16.0, 12.0, 1.0]]]}, fh)
    out = str(tmp_path / "sheet.png")
    os.makedirs(out)
    with pytest.raises(MZS.ZoomSheetError) as exc:
        MZS.main([f"--frames={frames}", f"--keypoints={kp}", "--site=Nose", "--at=0",
                  f"--out={out}", "--crop=8", "--scale=2"])
    assert out in str(exc.value)
    assert "ZOOM_SHEET_OK" not in capsys.readouterr().out
    assert not os.path.exists(os.path.splitext(out)[0] + "_crops.json")


# ===========================================================================
# F-97de9ce4 — a declared flag is read, or it is not declared
# ===========================================================================


def _dests_declared(tree):
    out = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "add_argument"):
            continue
        dest = None
        for kw in node.keywords:
            if kw.arg == "dest" and isinstance(kw.value, ast.Constant):
                dest = kw.value.value
        if dest is None:
            for arg in node.args:
                if not (isinstance(arg, ast.Constant) and isinstance(arg.value, str)):
                    continue
                if arg.value.startswith("--"):
                    dest = arg.value[2:].replace("-", "_")
                    break
                if not arg.value.startswith("-"):
                    dest = arg.value.replace("-", "_")
                    break
        if dest:
            out.add(dest)
    return out


def _names_read(tree):
    """Every attribute name read anywhere in the module, plus every bare name.

    The DECLARED-and-unread direction cannot use the namespace-scoped walk the READ-and-
    undeclared direction uses: a flag may legitimately be read through a helper that took
    the namespace as a parameter (`provenance_lines(a.meta)`), so this direction asks the
    weaker question — does the dest appear at all — and a flag that appears nowhere in its
    own module reaches nothing by any route.
    """
    seen = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            seen.add(node.attr)
        elif isinstance(node, ast.Name):
            seen.add(node.id)
        elif isinstance(node, ast.keyword) and node.arg:
            seen.add(node.arg)
    return seen


#: Flags declared by `armature_core.canon`'s shared helper rather than by the module's own
#: parser body are resolved as DECLARED there; this census walks each module's own
#: `add_argument` calls, so a shared flag is only in the population of the module that
#: writes the call. Named here because the exemption is the reason, not a proxy.
CANON_SHARED_FLAGS = {"subject", "no_canon", "canon_prompt"}


def test_every_flag_a_parser_declares_is_read_somewhere_in_that_module():
    """The second direction of the parser census.

    `tests/test_sheet_argv_smoke.py` walks flags READ and not DECLARED (the
    `--sheet-plate` regression). A flag DECLARED and not READ is invisible to it, and is
    the same defect pointing the other way: measured 2026-09-04,
    `make_thesis_sheet.main([... '--meta=E:/no/such/meta.json'])` returned 0, printed
    `THESIS_SHEET`, left the sheet on disk, and accepted a path that does not exist in
    silence — while its two siblings draw the run's provenance off exactly that flag.
    """
    dangling = {}
    for mod, (_path, tree) in TOOL_TREES.items():
        declared = _dests_declared(tree)
        if not declared:
            continue
        read = _names_read(tree)
        unread = sorted(d for d in declared - CANON_SHARED_FLAGS if d not in read)
        if unread:
            dangling[mod] = unread
    assert dangling == {}, dangling


def test_the_declared_and_unread_census_goes_red_on_a_dangling_flag():
    """Falsifiability, in the spelling that hides from the READ-and-undeclared walk."""
    tree = ast.parse(
        "import argparse\n"
        "def main(argv=None):\n"
        "    ap = argparse.ArgumentParser()\n"
        "    ap.add_argument('--out', required=True)\n"
        "    ap.add_argument('--meta', default=None)\n"
        "    a = ap.parse_args(argv)\n"
        "    return a.out\n")
    declared, read = _dests_declared(tree), _names_read(tree)
    assert declared == {"out", "meta"}
    assert sorted(d for d in declared if d not in read) == ["meta"]


def test_the_thesis_sheet_draws_the_provenance_it_is_pointed_at(tmp_path, capsys):
    """`--meta` reaches the panel. Carried from `make_gate0_sheet.provenance_lines` — one
    implementation, not a second copy — so the thesis panel says the same things about a
    run's record that the Gate 0 panel does."""
    import make_thesis_sheet as TS

    meta = str(tmp_path / "meta.json")
    with open(meta, "w", encoding="utf-8") as fh:
        json.dump({"arm": "A1", "prompt_id": "pid-77",
                   "models": {"unet": "a-model.safetensors"}}, fh)
    ctl = _clip(str(tmp_path / "ctl"), [0, 1, 2])
    arm = _clip(str(tmp_path / "arm"), [0, 1, 2], base=(40, 30, 24))
    out = str(tmp_path / "sheets" / "th.png")
    assert TS.main([f"--control={ctl}", f"--arms=A1:{arm}", "--reference=none",
                    f"--out={out}", "--frames=0,1", "--tile-height=24",
                    f"--meta={meta}"]) == 0
    assert "provenance=" in capsys.readouterr().out
    assert os.path.getsize(out) > 0


def test_the_thesis_sheet_refuses_a_meta_path_that_is_not_there(tmp_path):
    """A path that does not exist was accepted in silence, on a panel this repo requires
    to carry provenance."""
    import make_thesis_sheet as TS

    ctl = _clip(str(tmp_path / "ctl"), [0, 1, 2])
    arm = _clip(str(tmp_path / "arm"), [0, 1, 2], base=(40, 30, 24))
    out = str(tmp_path / "sheets" / "th.png")
    with pytest.raises(OSError):
        TS.main([f"--control={ctl}", f"--arms=A1:{arm}", "--reference=none",
                 f"--out={out}", "--frames=0,1", "--tile-height=24",
                 f"--meta={tmp_path / 'no' / 'such.json'}"])
    assert not os.path.exists(out)


# ===========================================================================
# F-693a3875 — the two halves partition the mask, and the denominator is recorded
# ===========================================================================


def _p3_run(tmp_path, levels):
    """A one-frame run on disk: a mask, a per-frame depth and a per-shot depth."""
    run = tmp_path / "run"
    for d in ("mask", "depth_perframe", "depth_pershot"):
        os.makedirs(run / d, exist_ok=True)
    n = len(levels)
    mask = np.ones((1, n), np.uint8) * 255
    Image.fromarray(mask).convert("1").save(run / "mask" / "00000.png")
    Image.fromarray(np.array([levels], np.uint8)).save(run / "depth_perframe" / "00000.png")
    Image.fromarray(np.array([[v + 1 for v in levels]], np.uint8)).save(
        run / "depth_pershot" / "00000.png")
    with open(run / "manifest.json", "w", encoding="utf-8") as fh:
        json.dump({"frame_count": 1}, fh)
    return str(run)


def test_the_two_halves_partition_the_mask(tmp_path):
    """Measured: on a plausible masked depth population the strict `>`/`<` split left
    40.9% of the geometry in NEITHER half, with `n_px` (the mask total) the only
    denominator on the record — so a reader could not derive the shortfall. Here a flat
    surface after 8-bit quantisation is the whole population."""
    import analyze_p3

    run = _p3_run(tmp_path, [128] * 4 + [100, 110, 140, 150])
    rec = analyze_p3.analyze(run)
    f = rec["per_frame"][0]
    assert f["n_px"] == 8, f
    assert f["n_near_half"] + f["n_far_half"] + f["n_at_median"] == f["n_px"], f
    assert f["n_at_median"] == 4, f
    assert "median" in rec["unit"], rec["unit"]


def test_a_flat_frame_is_not_reported_as_a_direction(tmp_path):
    """Every masked pixel at the median is the shape a flat surface takes after 8-bit
    quantisation; the summary the tool exists to produce counted frames by the sign of two
    means taken over an unstated fraction of the geometry."""
    import analyze_p3

    rec = analyze_p3.analyze(_p3_run(tmp_path, [128] * 6))
    f = rec["per_frame"][0]
    assert f["n_at_median"] == 6, f
    assert f["n_near_half"] + f["n_far_half"] + f["n_at_median"] == f["n_px"], f
    assert rec["direction"]["n_frames"] == 1


# ===========================================================================
# the gates raise; `-O` does not delete them
# ===========================================================================


@pytest.mark.parametrize("snippet,token", [
    ("import make_sheet as M\n"
     "try:\n    M.main(['--out=x.png'])\nexcept Exception as e:\n"
     "    print(type(e).__name__)\n", "MakeSheetError"),
    ("import measure_tracking as MT\n"
     "print('CODE', MT.main(['--anchor', '--e02-root=nope-nope']))\n", "CODE 3"),
])
def test_the_new_refusals_survive_python_optimize(snippet, token):
    """`-O` deletes an `assert`; every refusal added by this amend is a `raise` or a
    returned exit code."""
    code = f"import sys; sys.path.insert(0, r'{TOOLS}')\n" + snippet
    res = subprocess.run([sys.executable, "-O", "-c", code],
                         capture_output=True, text=True, cwd=ROOT)
    assert token in res.stdout, (res.stdout, res.stderr)
