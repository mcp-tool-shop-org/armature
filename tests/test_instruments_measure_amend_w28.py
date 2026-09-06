"""Wave 28 — the instruments-measure amend, seven findings, red proofs first.

Every test here goes red on `3380ae2` and green on the commit beside it. Where a claim is
about a PROCESS — an exit code, a halt line an operator keys on, a `--help` route — it is
driven as a real subprocess with this interpreter, because the finding in each case is that
the in-process value and the process's answer had stopped agreeing.

Three of the seven are one mechanism seen from three sides, and the tests are grouped that
way rather than one-per-finding:

* **the wait** (`F-594d4efc`, `F-3dc24905`) — every ffmpeg subprocess carries a `timeout=`
  DERIVED from the work it is given, a bound that is reached is a NAMED refusal and never a
  retry, and the long local loops print elapsed progress on stderr. The progress line is
  deliberately lowercase: `tests/test_instruments_amend_w10.success_tokens` walks every
  `print` outside the `__main__` handler and asserts exactly ONE uppercase token per Blender
  tool, so a `<PREFIX>_PROGRESS` line would take that census red on the commit that adds
  progress. A progress line is not a sentinel and must not look like one.
* **the write refusal** (`F-18e31b77`) — `stage_render.main`'s single `except OSError` is
  split by cause, so an out-of-space write inside `run_export` is no longer delivered as a
  mistyped `--spec`.
* **the help route** (`F-3ce0db92`, `F-7c3f8a26`, `F-01f7eda9`) — every parser in the domain
  carries a `description=`, every flag a `help=`, and `--codec` a `choices=`.

`F-79f38dd5` rides the same file as the wait: the directory the tool created before it
refused is named in the refusal, and `clip_bytes` — the one number that separates a truncated
download from a real clip — is on the record.

Sources are read through `_census_nodes` rather than by literal repo path, so this file adds
nothing to `tests/test_ci_workflows.GUARDED_TODAY`.
"""

import ast
import json
import os
import subprocess
import sys

import pytest
from PIL import Image

TESTS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TESTS)
TOOLS = os.path.join(REPO, "tools")

sys.path.insert(0, TOOLS)
sys.path.insert(0, TESTS)

import _census_nodes as CN  # noqa: E402


#: The 42 modules this domain owns, spelled once. `F-3ce0db92`'s population is the subset of
#: these that builds an `argparse` parser; the other five parse `--key=value` by hand and are
#: named by the test that measures them, not silently dropped.
OWNED = tuple(sorted("""
analyze_p3 armature_index compare_runs composite_reference encode_control
extract_clip_frames fit_reference gate_b_frames invert_frames lift_clip make_ab_clip
make_cast_sheet make_crop_strip make_e08_sheet make_e13_sheet make_gate0_sheet
make_hole_survey make_identity_sheet make_lift_sheet make_overlay_sheet make_pick_sheet
make_plate make_review_clip make_sheet make_shotset_sheet make_startframe_sheet
make_thesis_sheet make_zoom_sheet measure_arm measure_cascade_clip measure_clip
measure_floor measure_lift measure_smoothness measure_tracking pack_pose_pack
project_pose_keypoints render_pose_sticks resample_motion rig_sheet_compose sheet_compose
stage_render
""".split()))


# ---------------------------------------------------------------------------- helpers


def _tree(name):
    return ast.parse(CN.read_source(name + ".py"))


#: The parser CLASSES this domain constructs. Keyed on the resolved shape rather than on one
#: base name: `armature_index` builds its parser through `record_index._cli.ContractParser`,
#: an `argparse.ArgumentParser` SUBCLASS, and a walk keyed on `ArgumentParser` alone measured
#: that module as having no parser at all while it declared three flags.
_PARSER_CALLS = ("ArgumentParser", "ContractParser")


def _parsers_and_flags(tree):
    """`(parser constructions, add_argument calls)` in one module — the census's own node."""
    parsers, adds = [], []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        tail = (node.func.attr if isinstance(node.func, ast.Attribute)
                else getattr(node.func, "id", None))
        if tail in _PARSER_CALLS:
            parsers.append(node)
        elif tail == "add_argument":
            adds.append(node)
    return parsers, adds


def _kw(call, name):
    for k in call.keywords:
        if k.arg == name:
            return k.value
    return None


def _run(tool, argv, cwd=None, env=None):
    """The tool's own `__main__`, as a real process on this interpreter."""
    inherited = os.environ.get("PYTHONPATH", "")
    path = os.pathsep.join([TOOLS] + ([inherited] if inherited else []))
    return subprocess.run(
        [sys.executable, os.path.join(TOOLS, tool + ".py")] + list(argv),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(cwd or TOOLS), env=dict(os.environ, PYTHONPATH=path, **(env or {})))


def _halt(proc, prefix):
    """The one `<PREFIX>_HALT <json>` line on stdout, parsed. Fails loudly if absent."""
    token = prefix + "_HALT"
    lines = [l for l in proc.stdout.splitlines() if l.split(" ", 1)[0] == token]
    assert len(lines) == 1, (
        f"{len(lines)} `{token} <json>` line(s); rc={proc.returncode}\n"
        f"stdout:\n{proc.stdout[-1200:]}\nstderr:\n{proc.stderr[-1200:]}")
    return json.loads(lines[0][len(token):].strip())


# ------------------------------------------------------- F-3ce0db92 / F-7c3f8a26 / F-01f7eda9
#
# README's one discovery route for every instrument is `python tools/<name>.py --help`.
# MEASURED on `3380ae2` by AST census over the 42 owned modules with the repo venv: 36 build
# an `ArgumentParser`, ONE gave it a `description` (`compare_runs`), and 153 of 253
# `add_argument` calls carried no `help=` — including `encode_control`'s `--fps` and
# `--invert`, which decide the rate and the polarity of the control video a paid run uploads.


#: The five owned modules that build NO `argparse` parser. Derived and asserted rather than
#: assumed: they parse `--key=value` by hand (`make_sheet.parse_argv`, which
#: `stage_render._parse_argv` is the model for, and `sys.argv[1]` in the two compose tools),
#: so `--help` is not a route argparse can serve for them. Their doc half — README's promise
#: of a route that is empty for these five — is the coordinator's.
HAND_PARSED = ("analyze_p3", "make_sheet", "rig_sheet_compose", "sheet_compose",
               "stage_render")


def test_the_argparse_population_of_this_domain_is_derived_and_the_rest_are_named():
    """The denominator, walked rather than typed — 36 parsers, 5 hand-parsed, 1 with none."""
    with_parser, without = [], []
    for name in OWNED:
        parsers, adds = _parsers_and_flags(_tree(name))
        (with_parser if (parsers or adds) else without).append(name)
    assert sorted(set(OWNED) - set(with_parser)) == sorted(
        n for n in HAND_PARSED if n not in with_parser), sorted(without)
    for name in HAND_PARSED:
        parsers, _adds = _parsers_and_flags(_tree(name))
        assert parsers == [], (
            f"{name} now builds an argparse parser; it has left HAND_PARSED and the "
            f"--help route it could not serve is servable")


@pytest.mark.parametrize("name", [n for n in OWNED if n not in HAND_PARSED])
def test_every_parser_in_this_domain_says_what_the_tool_does(name):
    """`description=` on the parser — the first line an operator's `--help` shows.

    Red on `3380ae2` for 35 of the 36: `compare_runs` was the tree's ONE precedent, and the
    brief names it as the shape to copy.
    """
    parsers, _adds = _parsers_and_flags(_tree(name))
    assert parsers, f"{name} builds no ArgumentParser; it belongs in HAND_PARSED"
    described = [p for p in parsers if isinstance(_kw(p, "description"), ast.Constant)]
    assert described, (
        f"tools/{name}.py builds a parser with no description=; `--help` opens on a bare "
        f"usage line and says nothing about what the tool does or who reads its output")


@pytest.mark.parametrize("name", [n for n in OWNED if n not in HAND_PARSED])
def test_every_flag_in_this_domain_carries_help_text(name):
    """`help=` on every `add_argument` — 153 of 253 carried none on `3380ae2`."""
    _parsers, adds = _parsers_and_flags(_tree(name))
    silent = [a.lineno for a in adds if _kw(a, "help") is None]
    assert silent == [], (
        f"tools/{name}.py declares {len(silent)} flag(s) with no help= (lines {silent}); "
        f"`--help` prints the flag name and nothing beside it")


def test_the_parser_walk_sees_a_subclassed_parser_and_not_only_the_base_name():
    """The red proof for `_PARSER_CALLS`, on the shape that was measured here.

    `armature_index` constructs `_cli.ContractParser(...)`. A walk keyed on the literal
    `ArgumentParser` returns nothing for it, which reads as "this module has no parser" for
    a module that declares three flags — the same class of blindness wave 18's rule 1 names.
    """
    subclassed = ast.parse(
        "def _dispatch(argv=None):\n"
        "    ap = _cli.ContractParser(prog='x', description='what it does')\n"
        "    ap.add_argument('verb', choices=('build',), help='what to do')\n"
        "    return ap.parse_args(argv)\n")
    parsers, adds = _parsers_and_flags(subclassed)
    assert len(parsers) == 1 and len(adds) == 1
    assert isinstance(_kw(parsers[0], "description"), ast.Constant)
    base_only = [n for n in ast.walk(subclassed)
                 if isinstance(n, ast.Call)
                 and (getattr(n.func, "attr", None) or getattr(n.func, "id", None))
                 == "ArgumentParser"]
    assert base_only == [], "the narrow predicate must be blind here, or this proves nothing"


def test_the_help_census_goes_red_on_a_parser_that_declares_a_silent_flag():
    """The falsifiability fixture: the predicate must catch the shape it exists to catch."""
    offender = ast.parse(
        "import argparse\n"
        "def parse_args(argv=None):\n"
        "    ap = argparse.ArgumentParser()\n"
        "    ap.add_argument('--out', required=True)\n"
        "    return ap.parse_args(argv)\n")
    parsers, adds = _parsers_and_flags(offender)
    assert [p for p in parsers if isinstance(_kw(p, "description"), ast.Constant)] == []
    assert [a.lineno for a in adds if _kw(a, "help") is None] == [4]


def test_the_codec_flag_offers_its_closed_set_and_flags_the_trap():
    """F-7c3f8a26 — `--codec`'s five legal values reach `--help`, not only the refusal.

    Red on `3380ae2`: `--codec` was declared with no `choices=` and no `help=`, so the ONLY
    place the set reached the operator was the `unknown_codec` raise inside `encode()` —
    which fires from `build()` AFTER the whole frame population has been listed, opened,
    coerced and hashed. `x264-qp0-yuv420` is annotated in the module as THE TRAP and was
    offered on the same footing as the four safe ones.
    """
    import encode_control as EC

    _parsers, adds = _parsers_and_flags(_tree("encode_control"))
    codec = [a for a in adds
             if a.args and isinstance(a.args[0], ast.Constant)
             and a.args[0].value == "--codec"]
    assert len(codec) == 1, codec
    choices = _kw(codec[0], "choices")
    assert choices is not None, "--codec has no choices=; a typo is still a late refusal"
    helptext = _kw(codec[0], "help")
    assert isinstance(helptext, ast.Constant) or isinstance(helptext, ast.JoinedStr) \
        or helptext is not None
    proc = _run("encode_control", ["--help"])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    for name in sorted(EC.CODECS):
        assert name in proc.stdout, (name, proc.stdout[:1500])
    assert "TRAP" in proc.stdout, proc.stdout[:1500]

    # The in-code refusal STAYS: the parser guards this one caller, the raise guards every
    # programmatic one. Driven in process rather than asserted from the source.
    with pytest.raises(EC.EncodeFailure) as caught:
        EC.encode([], "x.mkv", "ffv1")
    assert caught.value.evidence["clause"] == "unknown_codec", caught.value.evidence


def test_a_typo_on_codec_is_refused_before_a_frame_is_opened():
    """The consequence of `choices=`, driven as a process: argparse exits 2 on the flag."""
    proc = _run("encode_control", ["--frames=nowhere", "--out=x.mkv", "--codec=ffv1"])
    assert proc.returncode == 2, (proc.returncode, proc.stdout, proc.stderr)
    assert "--codec" in proc.stderr and "ffv1-gbrp" in proc.stderr, proc.stderr[-600:]


def test_the_two_frame_size_flags_name_the_route_their_defaults_came_from():
    """F-01f7eda9 — `--width` / `--height` on both sides of the same frame.

    Red on `3380ae2`: both were bare `type=int, default=...` in `fit_reference` (the tool
    that builds the reference image a paid run SUBMITS) and in `project_pose_keypoints` (the
    control side of the same frame), while `--pad` and `--alpha-over` in the same parser
    carried two of the best help strings in the domain. CLAUDE.md's generator-legality rule
    reached the operator nowhere in either tool.
    """
    for name in ("fit_reference", "project_pose_keypoints"):
        proc = _run(name, ["--help"])
        assert proc.returncode == 0, proc.stdout + proc.stderr
        out = proc.stdout
        assert "GENERATOR_PROFILES" in out, (name, out)
        assert "832" in out and "480" in out, (name, out)
        # The per-model table is enforced by a gate, and the help points at that gate by
        # name rather than at a number somebody remembered.
        assert "g1_generator_legality" in out, (name, out)


# --------------------------------------------------------------- F-594d4efc / F-3dc24905
#
# The wait shape, shared with builders' fetchers (wave-28 seams inbox, SEAM 2).


def test_every_ffmpeg_subprocess_in_this_domain_runs_under_a_bound():
    """The census, walked: no bare `subprocess.run` on the encoder in the three consumers.

    Red on `3380ae2` — `encode_control._run`, `extract_clip_frames.probe` and
    `measure_cascade_clip.ffprobe_stream` were three `subprocess.run` calls with no
    `timeout=` between them, two of them probing a clip that arrived after a credit had
    been spent.
    """
    bad = []
    for name in ("encode_control", "extract_clip_frames", "measure_cascade_clip"):
        for node in ast.walk(_tree(name)):
            if not (isinstance(node, ast.Call) and CN.called_name(node) == "run"
                    and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "subprocess"):
                continue
            if _kw(node, "timeout") is None:
                bad.append(f"{name}:{node.lineno}")
    assert bad == [], f"subprocess.run on ffmpeg with no timeout=: {bad}"


def test_the_bound_is_derived_from_the_work_and_not_one_global_constant():
    """A global constant must not govern a local feature (CLAUDE.md).

    A 39-byte truncated download and a 500-frame lossless encode cannot honestly share one
    ceiling, so the bound is start-up plus a charge against the structure the call is given.
    """
    import encode_control as EC

    assert EC.timeout_for_frames(0) == EC.FFMPEG_STARTUP_S
    assert EC.timeout_for_frames(81) > EC.timeout_for_frames(8) > EC.timeout_for_frames(0)
    assert EC.timeout_for_file("this-path-does-not-exist.mp4") == EC.FFMPEG_STARTUP_S


def test_a_wait_that_ends_is_a_named_refusal_carrying_the_bound_it_broke(tmp_path):
    """Driven against the real predicate: a command that outlives its bound.

    The refusal names the binary, the input, the bound and the elapsed time, and it is a
    REFUSAL rather than a retry — nothing is re-submitted and no credit is spent on a wait
    that ended. Stood up with this interpreter in place of the encoder, the wave-25 CI
    fix-up's idiom, because the driven refusal fires before any encode.
    """
    import encode_control as EC

    with pytest.raises(EC.EncodeFailure) as caught:
        EC.run_ffmpeg([sys.executable, "-c", "import time; time.sleep(30)"],
                      timeout_s=0.75, subject="stream probe",
                      input_path=str(tmp_path / "run.mp4"))
    ev = caught.value.evidence
    assert ev["clause"] == "ffmpeg_exceeded_the_time_bound", ev
    assert ev["gate"] == "ENCODE" and ev["andon"] == "EncodeFailure", ev
    assert ev["bound_s"] == 0.75 and ev["elapsed_s"] >= 0.7, ev
    assert ev["subject"] == "stream probe", ev
    assert ev["binary"] == sys.executable and ev["input"].endswith("run.mp4"), ev
    assert ev["partial"] is None, ev
    assert "not a retry" in str(caught.value), str(caught.value)


def test_a_timed_out_encode_says_what_is_on_disk_now(tmp_path):
    """`partial` is the half an operator cannot get from the message alone."""
    import encode_control as EC

    half = tmp_path / "half.mkv"
    half.write_bytes(b"\x00" * 1234)
    with pytest.raises(EC.EncodeFailure) as caught:
        EC.run_ffmpeg([sys.executable, "-c", "import time; time.sleep(30)"],
                      timeout_s=0.5, subject="encode", input_path="9 frame(s) on stdin",
                      output_path=str(half))
    assert caught.value.evidence["partial"] == {"path": str(half), "bytes": 1234}, \
        caught.value.evidence


def test_the_long_loops_report_progress_and_none_of_it_looks_like_a_sentinel():
    """F-3dc24905 — the two ends of the same property, on the source itself.

    `stage_render.run_export` and `encode_control.read_frames` take a `progress` callback and
    call it once per frame; `extract_clip_frames` prints per frame directly. And NONE of the
    progress lines leads with an uppercase token, because
    `test_instruments_amend_w10.success_tokens` asserts exactly one per Blender tool.
    """
    import test_instruments_amend_w10 as W10

    for name in ("stage_render", "encode_control"):
        tree = _tree(name)
        fns = {n.name: n for n in tree.body
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        target = fns["run_export" if name == "stage_render" else "read_frames"]
        assert any(a.arg == "progress" for a in target.args.args), (
            f"{name}.{target.name} takes no progress callback")
        calls = [n for n in ast.walk(target)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                 and n.func.id == "progress"]
        assert calls, f"{name}.{target.name} declares progress and never calls it"

    # The sentinel census, asked directly rather than described.
    assert sorted(W10.success_tokens("stage_render.py")) == ["STAGE_RENDER_OK"], \
        sorted(W10.success_tokens("stage_render.py"))


def test_the_extractor_prints_a_lowercase_progress_line_per_frame(tmp_path):
    """The runtime half, driven as a process on a real decode.

    The frames come from `encode_control`'s own probe pair through a stubbed decoder rather
    than from ffmpeg, so this runs on a host with no encoder installed.
    """
    src = tmp_path / "clip.mp4"
    src.write_bytes(b"\x00" * 64)
    stub = tmp_path / "stub_extract.py"
    stub.write_text(
        "import os, sys\n"
        "import numpy as np\n"
        f"sys.path.insert(0, {TOOLS!r})\n"
        "import extract_clip_frames as X\n"
        "X.probe = lambda p, out_dir=None: {'line': 'stub', 'width': 4, 'height': 4,\n"
        "                                   'fps': 16.0, 'duration_line': None}\n"
        "X.decode = lambda p, w, h: [np.zeros((h, w, 3), dtype=np.uint8) for _ in range(3)]\n"
        "sys.exit(X._cli(sys.argv[1:]))\n", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(stub), f"--clip={src}", f"--out={tmp_path / 'frames'}"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(tmp_path), env=dict(os.environ, PYTHONPATH=TOOLS))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rows = [l for l in proc.stderr.splitlines()
            if l.startswith("extract_clip_frames write ")]
    assert len(rows) == 3, proc.stderr
    assert "1/3" in rows[0] and "elapsed" in rows[0] and "bound" in rows[0], rows[0]
    # Not a sentinel: stdout carries EXTRACT_OK and the progress carries no uppercase token.
    assert "EXTRACT_OK" in proc.stdout, proc.stdout
    for row in rows:
        assert row.split(" ", 1)[0].islower(), row


# ------------------------------------------------------------------------- F-79f38dd5


def test_a_clip_that_is_not_a_clip_is_refused_with_its_byte_count_and_the_empty_dir(
        tmp_path):
    """The refusal an operator meets when a paid run's download is an HTML error body.

    Red on `3380ae2`: the refusal carried a `stderr_tail`, no clause, no gate, no andon, no
    byte count, and no mention of the `frames/` directory the run had already created —
    which then reads as a run that happened and produced nothing.
    """
    import extract_clip_frames as X

    src = tmp_path / "run.mp4"
    src.write_bytes(b"<html><body>403 Forbidden</body></html>")
    out = tmp_path / "frames"
    out.mkdir()

    class _Proc:
        stderr = "ffmpeg version stub\nInvalid data found when processing input\n"

    real = X.run_ffmpeg
    X.run_ffmpeg = lambda *a, **k: _Proc()
    try:
        with pytest.raises(X.ClipReadError) as caught:
            X.probe(str(src), out_dir=str(out))
    finally:
        X.run_ffmpeg = real
    ev = caught.value.evidence
    assert ev["clause"] == "no_video_stream_line", ev
    assert ev["clip_bytes"] == 39, ev
    assert ev["created_empty_dir"] == str(out), ev
    assert "holds NO frames" in str(caught.value), str(caught.value)
    assert "39 bytes" in str(caught.value), str(caught.value)


# ------------------------------------------------------------------------- F-18e31b77


def _stage_render_probe(tmp_path, filename, errno_=28, message="No space left on device",
                        raise_after=None):
    """Drive `stage_render.main` with `run_export` patched to raise an OSError.

    A script by path on this interpreter, never `python -` on stdin: the halt line is a
    property of the PROCESS, and `run_tool_main` only runs under `__main__`.
    """
    probe = tmp_path / "probe_stage_render.py"
    probe.write_text(
        "import sys\n"
        f"sys.path.insert(0, {TOOLS!r})\n"
        "import stage_render as S\n"
        "from armature_core.parts import run_tool_main\n"
        "def boom(spec, out_dir, backend=None, progress=None):\n"
        + ("    " + (raise_after or "pass") + "\n" if raise_after else "")
        + f"    raise OSError({errno_}, {message!r}, {filename!r})\n"
        "S.run_export = boom\n"
        "S.shotspec.load_spec = lambda p: {'stub': True}\n"
        "run_tool_main(S.main, 'STAGE_RENDER')\n", encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(probe), "--spec=whatever.json", f"--out={tmp_path / 'run'}"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(tmp_path), env=dict(os.environ, PYTHONPATH=TOOLS))


def test_an_out_of_space_write_is_a_write_refusal_and_not_a_mistyped_spec(tmp_path):
    """F-18e31b77, the finding's own operand, driven end to end.

    MEASURED on `3380ae2`: this produced `_UnreadablePath` with clause
    `spec_or_asset_path_unreadable` and an evidence dict naming `spec` / `asset` / `out` —
    so the operator re-checks two flags that are fine while a partial control sequence sits
    in `--out` with no manifest.
    """
    doomed = str(tmp_path / "run" / "depth" / "00040.png")
    proc = _stage_render_probe(tmp_path, doomed)
    assert proc.returncode == 2, (proc.returncode, proc.stdout, proc.stderr)
    rec = _halt(proc, "STAGE_RENDER")
    ev = rec["evidence"]
    assert ev["clause"] == "control_sequence_write_failed", ev
    assert ev["andon"] == "StageRenderError", ev
    assert ev["errno"] == 28 and ev["path"] == doomed, ev
    assert ev["partial_export"] is True, ev
    assert ev["out"] == os.path.abspath(str(tmp_path / "run")), ev
    assert "PARTIAL export" in rec["message"], rec["message"]
    assert "--spec and --asset are not implicated" in rec["message"], rec["message"]


def test_a_read_outside_out_under_the_export_is_not_called_a_write_failure(tmp_path):
    """The other half of the split: the asset, or something the backend opens.

    Calling that a write failure would be a second wrong label rather than a fix, so it
    keeps `_UnreadablePath` under its own clause word.
    """
    proc = _stage_render_probe(tmp_path, str(tmp_path / "assets" / "subject.glb"),
                               errno_=2, message="No such file or directory")
    assert proc.returncode == 2, (proc.returncode, proc.stdout, proc.stderr)
    ev = _halt(proc, "STAGE_RENDER")["evidence"]
    assert ev["clause"] == "export_input_path_unreadable", ev
    assert ev["andon"] == "_UnreadablePath", ev
    assert ev["partial_export"] is False, ev


def test_the_spec_read_keeps_its_own_clause_word_unchanged(tmp_path):
    """The word does not move under a fix to the sentence it names.

    `spec_or_asset_path_unreadable` stays exactly where it was, on the two path-READING
    statements, so no census renames and the vocabulary gains only the two new words.
    """
    proc = _run("stage_render", ["--spec=nope.json", f"--out={tmp_path / 'run'}"],
                cwd=tmp_path)
    assert proc.returncode == 2, (proc.returncode, proc.stdout, proc.stderr)
    ev = _halt(proc, "STAGE_RENDER")["evidence"]
    assert ev["clause"] == "spec_or_asset_path_unreadable", ev
    assert ev["andon"] == "_UnreadablePath", ev
    assert ev["spec"] == "nope.json", ev


def test_the_write_refusal_quotes_the_frame_count_the_operator_watched_go_by(tmp_path):
    """The progress callback and the refusal are ONE mechanism, not two.

    `frames_written` is the count the callback last reported, so the number in the halt line
    is the number that went past on stderr — rather than a count the refusal invented.
    """
    doomed = str(tmp_path / "run" / "depth" / "00007.png")
    proc = _stage_render_probe(tmp_path, doomed,
                               raise_after="progress('frames', 7, 81)")
    assert proc.returncode == 2, (proc.returncode, proc.stdout, proc.stderr)
    ev = _halt(proc, "STAGE_RENDER")["evidence"]
    assert (ev["frames_written"], ev["frame_count"], ev["stage"]) == (7, 81, "frames"), ev
    rows = [l for l in proc.stderr.splitlines() if l.startswith("stage_render frames ")]
    assert rows and "7/81" in rows[-1] and "elapsed" in rows[-1], proc.stderr[-600:]
    assert rows[-1].split(" ", 1)[0].islower(), rows[-1]


def test_the_helper_that_both_refuses_and_writes_is_unmoved_by_this_split():
    """The pin, MEASURED with its own derivation rather than assumed from the brief.

    The wave-28 brief expected `F-18e31b77` to move `HELPER_BOTH_REFUSES_AND_WRITES`. It does
    not, and the derivation says why: `_census_nodes.helpers_that_refuse_and_write`
    intersects `functions_that_refuse` with `functions_that_write` and keeps the helpers the
    CLI body calls. `run_export` both refuses and writes before this fix and after it, and
    every edit here is in `main`, which gains no write. The `except`-handler analogue of
    `returning_branch_spans` — the census half of wave-26 SEAM 5a S6.2 — is tests' and is not
    in this wave.
    """
    derived = {}
    for path in CN.tool_paths():
        name = os.path.basename(path)[:-3]
        hits = CN.helpers_that_refuse_and_write(ast.parse(CN.read_source(name)))
        if hits:
            derived[name] = sorted(hits)
    assert derived == {"rig_character": ["export_rigged"],
                       "stage_render": ["run_export"]}, derived


def test_the_export_still_writes_and_the_reason_stage_render_sits_outside_is_intact():
    """The premise the pin above rests on, asserted rather than inherited."""
    tree = _tree("stage_render")
    assert "run_export" in CN.functions_that_write(tree)
    gates_at, writes_at = CN.refusal_and_write_lines(CN.read_source("stage_render.py"))
    assert gates_at, "stage_render's CLI body refuses somewhere"
    assert writes_at == {}, (
        "stage_render's CLI body now writes directly; the ordering population has changed "
        "and tests/test_instrument_write_ordering.py must be re-derived")


# ------------------------------------------------------------- the six new clause words
#
# Spelled here in CODE so each is "named by a fixture" and
# `tests/test_refusal_clauses.CLAUSES_NAMED_BY_NO_FIXTURE` does not grow. Five of the six are
# already driven by a test above; `clip_decoded_to_zero_frames` is driven below.


def test_a_clip_that_decodes_to_nothing_names_the_directory_it_left_behind(tmp_path):
    """The third of `extract_clip_frames`' three refusals, which carried no clause either."""
    import extract_clip_frames as X

    src = tmp_path / "run.mp4"
    src.write_bytes(b"\x00" * 8)
    out = tmp_path / "frames"
    stub = tmp_path / "stub_zero.py"
    stub.write_text(
        "import json, sys\n"
        f"sys.path.insert(0, {TOOLS!r})\n"
        "import extract_clip_frames as X\n"
        "from armature_core.parts import run_tool_main\n"
        "X.probe = lambda p, out_dir=None: {'line': 'stub', 'width': 4, 'height': 4,\n"
        "                                   'fps': 16.0, 'duration_line': None}\n"
        "X.decode = lambda p, w, h: []\n"
        "run_tool_main(X._cli, 'EXTRACT_CLIP_FRAMES')\n", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(stub), f"--clip={src}", f"--out={out}"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(tmp_path), env=dict(os.environ, PYTHONPATH=TOOLS))
    assert proc.returncode == 2, (proc.returncode, proc.stdout, proc.stderr)
    ev = _halt(proc, "EXTRACT_CLIP_FRAMES")["evidence"]
    assert ev["clause"] == "clip_decoded_to_zero_frames", ev
    assert ev["created_empty_dir"] == str(out), ev
    assert ev["clip_bytes"] == 8, ev
    assert X.ClipReadError.gate == "CLIP_READ"


def test_every_clause_word_this_wave_adds_is_in_the_recorded_vocabulary():
    """The membership half of the pin, re-derived branch-local (638 -> 644).

    Six words join, all of them in this domain: two from the split handler, one for the
    ffmpeg bound, and three from `extract_clip_frames`' previously clause-less refusals.
    """
    import test_refusal_clauses as RC

    added = ["clip_decoded_to_zero_frames", "control_sequence_write_failed",
             "export_input_path_unreadable", "ffmpeg_exceeded_the_time_bound",
             "no_video_stream_line", "stream_line_carries_no_resolution"]
    vocabulary = CN.clause_literals()
    for word in added:
        assert word in vocabulary, word
        assert word in RC.RECORDED_CLAUSES, word
    assert "spec_or_asset_path_unreadable" in vocabulary
    assert sorted(vocabulary) == sorted(RC.RECORDED_CLAUSES), {
        "appeared": sorted(set(vocabulary) - set(RC.RECORDED_CLAUSES)),
        "vanished": sorted(set(RC.RECORDED_CLAUSES) - set(vocabulary)),
    }
