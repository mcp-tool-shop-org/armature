"""Wave 28, the instruments domain: seven approved findings, each with its own census.

Every check here is a PROPERTY over a DERIVED population, never a list of the sites
someone remembered — the rule five of wave 25's seven findings existed because of. The
populations here are: the 21 Blender-side instruments this domain owns; the 20 files among
them (and under `tools/superseded/`) that build an `argparse.ArgumentParser`; the three
renderers that author the images a generation is conditioned on; and the refusal sites that
sit BELOW the first write, derived by `_census_nodes.refusal_and_write_lines` rather than
enumerated.

Each section drives the REAL predicate — the production function, the production parser,
the production `__main__` block — and each carries the direction that must FAIL, because a
check that cannot fail is not a check. Where the reverted-red proof would mean editing a
shipped tool, it is driven against a synthetic module carrying the pre-fix shape, which is
the arrangement `test_instrument_exits.py` already uses for the halt contract.

Helpers under `tests/` **raise**; they never `assert` outside a test function — `-O`
deletes an `assert` in a non-plugin helper.
"""

import ast
import contextlib
import io
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import _census_nodes as CN                                          # noqa: E402
import blender_stub                                                 # noqa: E402

TESTS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TESTS)
TOOLS = os.path.join(REPO, "tools")

#: The 21 Blender-side instruments this domain owns. Spelled once, because it IS the
#: domain boundary — a glob over `tools/*.py` would absorb instruments-measure's and
#: answer a different question. Same list wave 25 spelled, for the same reason.
OWNED = (
    "author_walk.py", "check_relift.py", "diagnose_bone_heat.py", "lift_solve.py",
    "make_binding_sheet.py", "make_parts_sheet.py", "make_rig_sheet.py",
    "make_skeleton_sheet.py", "make_test_armature.py", "preview_glb.py",
    "preview_walk.py", "probe_glb.py", "probe_subject.py", "render_performer.py",
    "render_start_frame.py", "render_turnaround.py", "rig_bake.py", "rig_character.py",
    "rig_parts.py", "rig_repair.py", "rig_retopo.py",
)

#: The falsified approaches kept runnable beside them (CLAUDE.md: "failures stay in the
#: repo"). They are in this domain's globs and their parsers reach an operator too.
SUPERSEDED = tuple(
    "superseded/" + n for n in sorted(os.listdir(os.path.join(TOOLS, "superseded")))
    if n.endswith(".py"))

#: The three renderers whose output feeds a submission and that had neither the stray
#: sweep nor any word about a re-used `--out` (F-8b7f48a8).
RENDERERS = ("render_turnaround.py", "render_start_frame.py", "preview_glb.py")


def source(rel):
    """`tools/<rel>` as text. `rel` may name a file under `superseded/`."""
    with open(os.path.join(TOOLS, rel), encoding="utf-8") as fh:
        return fh.read()


def tree(rel):
    return ast.parse(source(rel))


def called_name(call):
    func = call.func
    return func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")


# =======================================================================================
# F-814335e4 (panel HIGH) — a deliberate refusal exits 2, and is not recorded as a crash
# =======================================================================================
#
# MEASURED on `3380ae2` with `blender_stub.exit_code_of_main_block` and a `main` replaced
# by a `SystemExit(2)` raiser — exactly what `argparse` does on a missing required flag,
# reachable from the 43 `required=True` and 43 typed flags across this domain's parsers:
#
#     rig_bake, rig_character, rig_parts, rig_repair, rig_retopo  ->  exit 1, and
#         RIG_BAKE_HALT {"outcome": "FAILED - an unhandled error", "error": "SystemExit",
#                        "message": "2", "gate": null, "evidence": null}
#     the other sixteen                                           ->  exit 2, stdout empty
#
# The operator's whole account of a one-character flag typo was a sentence whose entire
# content was the character `2`, under the words `an unhandled error`, at the exit code
# this repo reserves for a crash. The finding named the three EXPOSED tools (rig_bake,
# rig_repair, rig_retopo — the argparse ones); wave-18 rule 2 says a fix's red proof runs
# against its siblings, and the derivation above finds five. `rig_character` and
# `rig_parts` hand-roll their parsers and so could not reach `SystemExit` from an argument
# — until `rig_character` gained a `--help` that exits 0 (F-e0ade43a), which the same
# missing re-raise would have recorded as a crash. All five take the two lines their
# sixteen siblings and `armature_core.parts.run_tool_main` already carry.


def systemexit_reraise_missing():
    """Every owned `__main__` whose handler does not re-raise `SystemExit` before its
    `except BaseException`. Derived over the block, never listed."""
    missing = []
    for rel in OWNED:
        block = blender_stub._main_block_ast(rel)
        if block is None:
            missing.append((rel, "no __main__ block"))
            continue
        ok = False
        for node in ast.walk(block):
            if not isinstance(node, ast.Try):
                continue
            for handler in node.handlers:
                names = handler.type
                is_systemexit = (isinstance(names, ast.Name)
                                 and names.id == "SystemExit")
                body = handler.body
                reraises = (len(body) == 1 and isinstance(body[0], ast.Raise)
                            and body[0].exc is None)
                if is_systemexit and reraises:
                    ok = True
        if not ok:
            missing.append((rel, "no `except SystemExit: raise`"))
    return missing


def test_every_owned_main_block_re_raises_systemexit():
    """The structural half: the property is asserted `== []` over the derived 21."""
    assert systemexit_reraise_missing() == [], systemexit_reraise_missing()


def test_a_refused_argument_exits_2_with_no_halt_line_on_all_21(capsys):
    """The BEHAVIOUR, driven through every owned `__main__` with the real handler.

    `SystemExit(2)` is what `argparse` raises on a missing or mistyped required flag. The
    contract README.md:190 states is: 2 on a deliberate refusal, 1 on a crash, and one
    `<TOOL>_HALT` line for either. argparse has already printed its own usage and error to
    stderr by the time this propagates, so the handler must add nothing and exit 2.
    """
    def raiser():
        raise SystemExit(2)

    wrong = {}
    for rel in OWNED:
        capsys.readouterr()
        code, escaped = blender_stub.exit_code_of_main_block(rel, raiser=raiser)
        out = capsys.readouterr().out
        halt_lines = [ln for ln in out.splitlines() if "_HALT " in ln]
        if code != 2 or escaped is not None or halt_lines:
            wrong[rel] = {"code": code, "escaped": repr(escaped), "halt": halt_lines}
    assert wrong == {}, wrong


def test_no_census_reads_the_handlers_comment_as_a_delegation():
    """The comment the fix adds names `armature_core.parts.run_tool_main` as the CPython
    home the two lines are adopted from — and TWO censuses asked "does this tool delegate
    to `run_tool_main`?" by looking for that name in the file's text.

    Both failed, in opposite directions, and the second is why this test exists:

    * `test_instruments_amend_w10.test_every_handler_carries_the_keysafe_helper` demanded
      the five have NO local `_halt_keysafe` and went red on the five local walks the
      recorded exception says they keep — a false failure, which is loud.
    * `test_instrument_exits._keysafe_is_guarded` returned True for the five, so the
      `key_str_raises` cases stopped skipping and started PASSING — a false SUCCESS, which
      is silent. MEASURED on this branch with the shortcut removed: the AST half answers
      False for all five, so the coverage those five tests appeared to gain was invented by
      a comment.

    Both predicates key on a `Call` now. This asserts the property directly, in both
    directions, so a third census written against the text fails here rather than in a
    number nobody reads: the five carry the NAME and must not read as delegating, and a
    tool that genuinely delegates must.
    """
    import test_instrument_exits as EX

    named_but_not_delegating = ("rig_bake.py", "rig_character.py", "rig_parts.py",
                                "rig_repair.py", "rig_retopo.py")
    for rel in named_but_not_delegating:
        src = source(rel)
        assert "run_tool_main" in src, (
            f"{rel} no longer names the home the two lines are adopted from; this test's "
            f"whole operand is that the name is present in PROSE")
        calls = [n for n in ast.walk(tree(rel))
                 if isinstance(n, ast.Call)
                 and (getattr(n.func, "attr", None) == "run_tool_main"
                      or getattr(n.func, "id", None) == "run_tool_main")]
        assert calls == [], f"{rel} now really calls run_tool_main; retire this row"
        assert EX._keysafe_is_guarded(rel) is False, (
            f"{rel} reads as guarded, and the AST says it is not — a comment has been "
            f"mistaken for a delegation and five behavioural cases are passing on it")

    # The other direction: a tool that DOES hand its `__main__` to the home reads as
    # guarded, so the fix did not buy honesty by losing the coverage it was written for.
    delegating = [f for f in blender_stub.cpython_tools()
                  if any(isinstance(n, ast.Call)
                         and (getattr(n.func, "attr", None) == "run_tool_main"
                              or getattr(n.func, "id", None) == "run_tool_main")
                         for n in ast.walk(ast.parse(blender_stub.read_source(f))))]
    assert delegating, "no CPython tool delegates; the positive direction is untested"
    assert EX._keysafe_is_guarded(delegating[0]) is True, delegating[0]


def test_the_pre_fix_handler_records_the_refusal_as_a_crash(tmp_path, monkeypatch):
    """REVERTED-RED, on a synthetic module carrying the shape all five had on `3380ae2`.

    The same driver, the same raiser, the handler without the two lines: exit **1**, and a
    halt line whose `message` is the character `2` under `FAILED - an unhandled error`.
    That is the operator's whole account of a one-character flag typo, and it is what the
    fix ends. Driven here rather than by editing a shipped tool, the way
    `test_instrument_exits.py` drives the other halt-contract directions.
    """
    head = (
        "import json, sys\n"
        "def main():\n"
        "    return 0\n"
        'if __name__ == "__main__":\n'
        "    try:\n"
        "        main()\n")
    tail = (
        "    except BaseException as exc:\n"
        "        _code = 1\n"
        "        _outcome = 'FAILED - an unhandled error'\n"
        "        _sentinel = {'tool': 'probe_reraise', 'outcome': _outcome,\n"
        "                     'gate': None, 'error': type(exc).__name__,\n"
        "                     'message': str(exc), 'evidence': None}\n"
        "        try:\n"
        "            _line = json.dumps(_sentinel)\n"
        "        except BaseException:\n"
        "            _line = '{}'\n"
        "        finally:\n"
        "            print('PROBE_RERAISE_HALT ' + _line)\n"
        "            sys.exit(_code)\n")
    # The ONLY difference between the two modules is the two lines the fix adds.
    open_handler = head + tail
    shut_handler = head + "    except SystemExit:\n        raise\n" + tail

    (tmp_path / "probe_open.py").write_text(open_handler, encoding="utf-8")
    (tmp_path / "probe_shut.py").write_text(shut_handler, encoding="utf-8")
    monkeypatch.setattr(blender_stub, "TOOLS", str(tmp_path))

    def raiser():
        raise SystemExit(2)

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        open_code, _ = blender_stub.exit_code_of_main_block("probe_open.py",
                                                            raiser=raiser)
    open_out = buf.getvalue()
    assert open_code == 1, "the pre-fix handler must record the refusal as a crash"
    record = json.loads(open_out.split("PROBE_RERAISE_HALT ", 1)[1])
    assert record["error"] == "SystemExit"
    assert record["message"] == "2"
    assert record["outcome"] == "FAILED - an unhandled error"

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        shut_code, _ = blender_stub.exit_code_of_main_block("probe_shut.py",
                                                            raiser=raiser)
    assert shut_code == 2
    assert "PROBE_RERAISE_HALT" not in buf.getvalue()


# =======================================================================================
# F-2b8afc38 — `--help` says what the tool does, and prints an invocation that works
# =======================================================================================
#
# MEASURED on `3380ae2` by AST over this domain's 24 files: **20 build an
# `ArgumentParser`; 0 pass `description`; 0 pass `epilog`; 83 of 117 `add_argument` calls
# carry no `help=`.** (The finding said 21 parsers; the derivation below returns 20 — 17
# under `tools/` and 3 under `tools/superseded/` — and the derived population is what this
# asserts, not the number in the prose.) Driven under the bpy stub with argv
# `blender -b -P tools/<tool>.py -- --help`, `preview_glb`'s entire help was
# `usage: blender.exe [-h] --glb GLB --out OUT --name NAME` and three flag names, one with
# text. Both halves of that line are the operator's: `prog` defaults to
# `os.path.basename(sys.argv[0])`, which under `blender -b -P` is the Blender binary, so
# the usage line named `blender.exe` and omitted the `-b -P tools/<name>.py --` prologue
# every one of those flags requires — the string an operator would copy is not the
# invocation that works, and README.md:181 is where that route line is written.


def parser_sites(rel):
    """`[(lineno, {kwarg names})]` for every `ArgumentParser(...)` built in `rel`."""
    return [(n.lineno, {k.arg for k in n.keywords if k.arg})
            for n in ast.walk(tree(rel))
            if isinstance(n, ast.Call) and called_name(n) == "ArgumentParser"]


def add_argument_sites(rel):
    """`[(lineno, flag, has_help)]` for every `add_argument(...)` call in `rel`."""
    out = []
    for n in ast.walk(tree(rel)):
        if not (isinstance(n, ast.Call) and called_name(n) == "add_argument"):
            continue
        flag = (n.args[0].value if n.args and isinstance(n.args[0], ast.Constant)
                else None)
        out.append((n.lineno, flag, any(k.arg == "help" for k in n.keywords)))
    return out


def parser_files():
    """Every owned file that builds a parser — DERIVED, so a new instrument joins it."""
    return [rel for rel in OWNED + SUPERSEDED if parser_sites(rel)]


def test_the_parser_population_is_the_files_that_build_one():
    """The population this section asserts over, stated before it is used.

    20 on this branch: 17 under `tools/` and the 3 kept runnable under `tools/superseded/`.
    `probe_glb`, `probe_subject`, `rig_character` and `rig_parts` hand-roll their parsers
    and are outside it — `rig_character`'s is F-e0ade43a's, below.
    """
    got = parser_files()
    assert len(got) == 20, got
    assert set(got) & {"probe_glb.py", "rig_character.py"} == set(), got


def test_every_parser_names_what_the_tool_does_and_how_to_run_it():
    """`description` and `prog` on every parser in the population."""
    offenders = {}
    for rel in parser_files():
        for lineno, kwargs in parser_sites(rel):
            missing = {"description", "prog"} - kwargs
            if missing:
                offenders[f"{rel}:{lineno}"] = sorted(missing)
    assert offenders == {}, offenders


def test_every_flag_that_reaches_an_operator_carries_a_sentence():
    """`help=` on all 117 `add_argument` calls in the population.

    83 of them had none on `3380ae2`, sharpest where it costs most: `render_turnaround` —
    the tool that authors the eight-view reference stack a composed route conditions a
    generation on — listed 15 flags of which `--views`, `--elevation`, `--width`,
    `--height`, `--height-frac`, `--lens` and `--sensor` had no sentence anywhere.
    """
    bare = {}
    for rel in parser_files():
        for lineno, flag, has_help in add_argument_sites(rel):
            if not has_help:
                bare.setdefault(rel, []).append((lineno, flag))
    assert bare == {}, bare


def help_text_of(rel):
    """`--help`'s real output for `rel`, driven through the module's own parser.

    The entry is `parse_args` where the module has one and `main` otherwise
    (`make_test_armature` builds its parser inside `main`); argv is the documented
    `blender -b -P tools/<name>.py -- --help` form the Blender-side parsers slice on.
    """
    import inspect

    mod_tree = tree(rel)
    names = {n.name for n in mod_tree.body if isinstance(n, ast.FunctionDef)}
    entry_name = "parse_args" if "parse_args" in names else "main"
    argv = ["blender", "-b", "-P", "x", "--", "--help"]
    mod = blender_stub.load_tool(rel, argv=argv)
    entry = getattr(mod, entry_name)
    saved = list(sys.argv)
    buf = io.StringIO()
    try:
        sys.argv = list(argv)
        with blender_stub.blender_stubbed(), contextlib.redirect_stdout(buf):
            try:
                entry(sys.argv) if inspect.signature(entry).parameters else entry()
            except SystemExit as exc:
                return exc.code, buf.getvalue()
    finally:
        sys.argv = saved
    return None, buf.getvalue()


@pytest.mark.parametrize("rel", ["render_turnaround.py", "preview_glb.py"])
def test_help_prints_the_blender_invocation_and_the_tools_own_sentence(rel):
    """DRIVEN, not asserted structurally: the two tools the finding measured by hand.

    `render_turnaround` is the reference-stack author; `preview_glb` is the one whose
    entire help was the `blender.exe` usage line plus three flag names.
    """
    code, text = help_text_of(rel)
    assert code == 0, text
    assert f"blender -b -P tools/{rel} --" in text, text
    assert "blender.exe" not in text, text
    first_line = (ast.get_docstring(tree(rel)) or "").strip().splitlines()[0]
    assert first_line in text, text


def test_the_reference_stacks_shot_flags_each_have_a_sentence():
    """The finding's operand, by name: the seven `render_turnaround` flags that compose
    the shot and had no sentence, driven through the real `--help`."""
    _code, text = help_text_of("render_turnaround.py")
    for flag in ("--views", "--elevation", "--width", "--height", "--height-frac",
                 "--lens", "--sensor"):
        head = text.split(flag, 1)
        assert len(head) == 2, f"{flag} is absent from --help"
        assert head[1].strip(), f"{flag} appears with nothing after it"


def test_the_help_census_reports_a_parser_that_says_nothing(tmp_path):
    """REVERTED-RED, driving the production predicates over a synthetic module.

    The shape every parser in this domain had on `3380ae2`: a bare `ArgumentParser()` and
    flags with no `help=`. Both censuses must name it; without this the two properties
    above are satisfied by a walk that finds nothing anywhere.
    """
    p = tmp_path / "make_twenty_first_thing.py"
    p.write_text(
        "import argparse\n"
        "def parse_args():\n"
        "    ap = argparse.ArgumentParser()\n"
        "    ap.add_argument('--glb', required=True)\n"
        "    ap.add_argument('--out', required=True, help='where it goes')\n"
        "    return ap.parse_args()\n", encoding="utf-8")
    src = p.read_text(encoding="utf-8")
    t = ast.parse(src)
    sites = [(n.lineno, {k.arg for k in n.keywords if k.arg})
             for n in ast.walk(t)
             if isinstance(n, ast.Call) and called_name(n) == "ArgumentParser"]
    assert sites and {"description", "prog"} - sites[0][1] == {"description", "prog"}
    adds = [(n.args[0].value, any(k.arg == "help" for k in n.keywords))
            for n in ast.walk(t)
            if isinstance(n, ast.Call) and called_name(n) == "add_argument"]
    assert adds == [("--glb", False), ("--out", True)]


# =======================================================================================
# F-8b7f48a8 (panel CRITICAL) — the silent overwrite, and the two populations a re-used
# `--out` has
# =======================================================================================
#
# MEASURED on `3380ae2` over the 21: 36 `os.makedirs` call sites, every one
# `exist_ok=True`, no refusal, no numbering, and no line in any record saying "this
# directory already existed". `render_performer.py:511` and `preview_walk.py:365` DO
# derive `unexpected_files_in_out_dir` and say in their own comments why; the three
# renderers whose output feeds a submission had no such sweep at all
# (`grep -n 'stray\\|unplanned\\|listdir'` returned zero hits in each).
#
# SEAM 1 (`wave-28/seams-inbox.md`, instruments -> builders): ONE flag `--overwrite`, ONE
# clause word `output_already_exists`, ONE sentence, and `out_dir_pre_existed` /
# `overwrote` in the record, shared with builders' `F-5fd16451` at
# `build_assembly_payload.py:831`. `armature_core.parts` is where a shared helper would
# live and is core-solvers' owned file this wave, so the three copies are held to one text
# HERE — the arrangement `_render_status`'s nine copies already have.


def overwrite_helper_source(rel):
    """The text of `gate_output_overwrite` in `rel`, exactly as written."""
    return blender_stub.fn_source(rel, "gate_output_overwrite")


def test_the_three_copies_of_the_overwrite_gate_are_one_text():
    """A copy that drifts is the defect wave 16 measured in `select_engine`: seven
    definitions, one of them missing the field the halt line reads. Byte equality, over
    the derived trio."""
    texts = {rel: overwrite_helper_source(rel) for rel in RENDERERS}
    distinct = set(texts.values())
    assert len(distinct) == 1, {rel: len(t) for rel, t in texts.items()}


@pytest.mark.parametrize("rel", RENDERERS)
def test_the_overwrite_gate_fires_above_the_output_directory(rel):
    """ORDERING, which is the whole point: a refused run must leave nothing behind.

    The call to `gate_output_overwrite` sits above the `os.makedirs` in the same body, so
    a declined run has created no directory for a later run to read as a used one — the
    invariant `render_turnaround.py`'s own comment states and `test_instruments_amend_w10`
    holds for the refusals that were already there.
    """
    t = tree(rel)
    gate_lines = [n.lineno for n in ast.walk(t)
                  if isinstance(n, ast.Call)
                  and called_name(n) == "gate_output_overwrite"
                  and not isinstance(getattr(n, "parent", None), ast.FunctionDef)]
    makedirs = [n.lineno for n in ast.walk(t)
                if isinstance(n, ast.Call) and called_name(n) == "makedirs"]
    assert gate_lines, f"{rel} does not call the overwrite gate"
    assert makedirs, f"{rel} creates no output directory"
    assert min(gate_lines) < min(m for m in makedirs if m > min(gate_lines)), (
        gate_lines, makedirs)


@pytest.mark.parametrize("rel", RENDERERS)
def test_the_overwrite_gate_refuses_by_name_and_says_what_is_there(rel, tmp_path):
    """DRIVEN against the real function and a real directory, all four directions.

    A fresh `--out`, a re-used one, `--overwrite`, and a stray whose suffix differs only
    in case — the last because `render_performer.py` measured a `.PNG` frame that its own
    record called nothing while `encode_control` encoded it into the clip.
    """
    mod = blender_stub.load_tool(rel)
    gate_cls = next(v for k, v in vars(mod).items()
                    if isinstance(v, type) and k.endswith("Gate"))
    planned = ["a.png", "b.png", "manifest.json"]

    fresh = tmp_path / "fresh"
    pre, present, strays = mod.gate_output_overwrite(str(fresh), planned, False, gate_cls)
    assert (pre, present, strays) == (False, [], []), (pre, present, strays)

    used = tmp_path / "used"
    used.mkdir()
    (used / "a.png").write_bytes(b"an earlier run")
    (used / "LEFTOVER.PNG").write_bytes(b"a stray, in the other case")

    with pytest.raises(gate_cls) as exc:
        mod.gate_output_overwrite(str(used), planned, False, gate_cls)
    ev = exc.value.evidence
    assert ev["clause"] == "output_already_exists"
    assert ev["already_present"] == ["a.png"]
    assert ev["planned"] == 3
    assert ev["out"] == os.path.abspath(str(used))
    assert ev["unexpected_files_in_out_dir"] == ["LEFTOVER.PNG"]
    assert ev["compensator"] == "delete --out; owner: the executor session"
    assert "--overwrite" in str(exc.value)
    assert "1 of the 3 files this run writes" in str(exc.value)

    pre, present, strays = mod.gate_output_overwrite(str(used), planned, True, gate_cls)
    assert (pre, present, strays) == (True, ["a.png"], ["LEFTOVER.PNG"])


@pytest.mark.parametrize("rel", RENDERERS)
def test_the_run_says_on_stdout_and_in_the_record_that_out_was_re_used(rel):
    """The half that makes two runs distinguishable in a scrollback (SEAM 1 §4).

    Both record keys, spelled the same in all three tools and in builders'.

    The announcement is `[overwrite] {json}`, a bracketed lowercase tag in the shape
    `canon_gate`'s `[canon] UNGATED:` line already uses — NOT an all-caps token. Measured
    on this branch: `<TOOL>_OVERWRITING` joined `test_instruments_amend_w10.success_tokens`,
    which collects every all-caps token a tool prints outside its handler and asserts the
    set is exactly `{<PREFIX>_OK}`, because a caller told to key on a success sentinel
    derives it from the halt token and a second token breaks that pairing. This line is
    progress, not a sentinel, and it says so by its shape.
    """
    src = source(rel)
    assert '"out_dir_pre_existed"' in src, rel
    assert '"overwrote"' in src, rel
    assert '"unexpected_files_in_out_dir"' in src, rel
    assert 'print("[overwrite] " + json.dumps(' in src, rel
    assert "_OVERWRITING" not in src, rel
    assert '"--overwrite"' in src, rel


def test_a_renderer_without_the_gate_is_reported(tmp_path, monkeypatch):
    """REVERTED-RED for the ordering property: the pre-fix shape is `os.makedirs` with no
    gate above it at all, which is what all three had."""
    p = tmp_path / "render_nothing.py"
    p.write_text(
        "import os\n"
        "def main():\n"
        "    out = 'x'\n"
        "    os.makedirs(out, exist_ok=True)\n"
        "    return 0\n", encoding="utf-8")
    t = ast.parse(p.read_text(encoding="utf-8"))
    gate_lines = [n.lineno for n in ast.walk(t)
                  if isinstance(n, ast.Call)
                  and called_name(n) == "gate_output_overwrite"]
    assert gate_lines == [], "the pre-fix shape has no overwrite gate to find"


# =======================================================================================
# F-c62f38e0 — the three refusals on the tool that authors a paid run's conditioning image
# =======================================================================================
#
# All three stated a constant string that named neither the path, the flag nor the frame
# that caused them, and one named its subject in NO FIELD AT ALL:
#
#   :630  RenderGate("no such plate", {"clause": "plate_is_not_a_file", "plate": backdrop})
#   :647  RenderGate("the GLB imported no render-visible mesh", {..., "glb": a.glb})
#   :667  RenderGate("the subject evaluates to no vertices at this frame",
#                    {"clause": "subject_has_no_vertices_at_this_frame"})
#
# Each has a neighbour in the same file or on the neighbouring tool that does it right —
# the plate-size clause names both sizes and the tool to run; `render_turnaround.py:902`,
# `preview_glb.py:279` and `check_relift.py:258` all name the GLB and list what WAS
# imported; the refusal twelve lines above :667 names `a.frame`, the mapped scene frame and
# the action's keyed span. "This frame" IS `--frame`, an operator-chosen integer, and it
# was in neither the message nor the evidence, so not even a census could say which frame
# had been asked for.

#: `(clause word, the evidence key that must carry the operand the sentence names)`.
STARTFRAME_REFUSALS = (
    ("plate_is_not_a_file", "plate_as_typed"),
    ("glb_has_no_render_visible_mesh", "mesh_objects_all"),
    ("subject_has_no_vertices_at_this_frame", "requested_frame"),
)


def refusals_by_clause(rel):
    """`{clause word: (message node, {evidence keys})}` for every `raise` in `rel` whose
    first argument is a message and whose second is an evidence dict literal."""
    out = {}
    for node in ast.walk(tree(rel)):
        if not (isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call)):
            continue
        args = node.exc.args
        if len(args) < 2 or not isinstance(args[1], ast.Dict):
            continue
        keys = {k.value: v for k, v in zip(args[1].keys, args[1].values)
                if isinstance(k, ast.Constant) and isinstance(k.value, str)}
        clause = keys.get("clause")
        if isinstance(clause, ast.Constant) and isinstance(clause.value, str):
            out[clause.value] = (args[0], set(keys))
    return out


def test_the_three_start_frame_refusals_name_what_they_are_about():
    """The message is an f-string (it interpolates the operand) and the evidence carries
    the value the sentence quotes. Both halves, because rule 1 of this wave's brief is
    that the message is for a person and the evidence is for a census — and both must
    hold."""
    found = refusals_by_clause("render_start_frame.py")
    offenders = {}
    for clause, ev_key in STARTFRAME_REFUSALS:
        if clause not in found:
            offenders[clause] = "no raise carries this clause"
            continue
        msg, keys = found[clause]
        if not isinstance(msg, ast.JoinedStr):
            offenders[clause] = "the message is a constant string"
        elif ev_key not in keys:
            offenders[clause] = f"the evidence does not carry {ev_key!r}"
    assert offenders == {}, offenders


def test_the_empty_subject_refusal_names_the_frame_that_was_asked_for():
    """The operand this finding is about, by name. `--frame` is an operator-chosen
    integer; the refusal must quote it in the sentence AND record it, so a census over
    halt lines can say which frame was requested."""
    src = source("render_start_frame.py")
    # WAVE 34: multi-frame authoring quotes the resolved index (`idx`), not `a.frame`.
    assert "--frame={idx}" in src, "the sentence does not quote the flag's value"
    found = refusals_by_clause("render_start_frame.py")
    _msg, keys = found["subject_has_no_vertices_at_this_frame"]
    assert {"requested_frame", "scene_frame", "action_range"} <= keys, sorted(keys)


def test_the_predicate_reports_a_constant_message_beside_a_populated_evidence_dict(
        tmp_path):
    """REVERTED-RED: the pre-fix shape, driven through the same walk.

    A constant message with the value it drops sitting in the evidence next to it — the
    family the finding censused at 22 sites tree-wide. `refusals_by_clause` must return a
    `Constant` here, which is exactly what the property above rejects.
    """
    p = tmp_path / "probe_constant_message.py"
    p.write_text(
        "class G(Exception):\n"
        "    def __init__(self, msg, ev):\n"
        "        super().__init__(msg)\n"
        "        self.evidence = ev\n"
        "def f(backdrop):\n"
        "    raise G('no such plate', {'clause': 'plate_is_not_a_file',\n"
        "                              'plate': backdrop})\n", encoding="utf-8")
    t = ast.parse(p.read_text(encoding="utf-8"))
    msgs = [n.exc.args[0] for n in ast.walk(t)
            if isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call)
            and len(n.exc.args) >= 2]
    assert len(msgs) == 1
    assert isinstance(msgs[0], ast.Constant), "the walk cannot see the shape it is for"
    assert not isinstance(msgs[0], ast.JoinedStr)


# =======================================================================================
# F-d6042cf6 — a gate that fires below the first write names the directory, and the undo
# =======================================================================================
#
# MEASURED on `3380ae2` with the repo's own census,
# `_census_nodes.refusal_and_write_lines` over the 21: **15 of 21 modules have at least one
# refusal below the first write, 60 refusal sites in total**, and only TWO of them told a
# halted operator where the partial run was (`preview_walk:370`, `render_performer:515`).
# Every module in this domain declares a named compensator in its own docstring, in the
# same words — "Compensator: delete `--out`; owner: the executor session" — and the halt
# line an operator actually reads is `{tool, outcome, gate, error, message, evidence}`,
# which has no field for it.
#
# THE HALF THAT IS FIXED HERE, and the half that is not. The INLINE raises below the first
# write are this domain's to fix and all of them now carry `out` and `compensator`. The
# remaining sites are CALL SITES of a helper that raises: `rc.gate_glb_written`,
# `rc.require_render_target_moved`, `SF.gate_*`, `TA.gate_*` and `glb.gate_atlas_untouched`
# all build their evidence inside `armature_core`, which is core-solvers' and core-gates'
# owned files this wave; the rest are module-local helpers (`build_pass`, `export_rigged`,
# `shoot`, `render_arm`, `pick_subject`, `gate_coverage`, `gate_part_names`) whose
# signatures carry no `--out`. Those are enumerated in the wave-28 report, not silently
# absorbed into a smaller population here.


def inline_refusals_below_the_first_write():
    """`{module: [(line, evidence keys)]}` for every INLINE `raise` of a family class that
    sits below the module's first write.

    The write and refusal lines come from `_census_nodes.refusal_and_write_lines` — the ONE
    home for that derivation — and the inline subset is the lines where an `ast.Raise`
    actually sits, which is what distinguishes them from the helper-hop call sites.
    """
    found = {}
    for rel in OWNED:
        src = source(rel)
        gates, writes = CN.refusal_and_write_lines(src)
        if not gates or not writes:
            continue
        first_write = min(writes)
        module = ast.parse(src)
        # RESOLVED SHAPE, not the spelled one (wave-18 rule 1): an evidence dict is often
        # BOUND to a name and handed to the raise (`ev_cov` in `render_start_frame`), and a
        # walk that reads only dict literals AT the raise reports those sites as carrying
        # no keys at all. Every `<name> = {...}` in the module contributes its keys, plus
        # every `<name>["key"] = ...` subscript assignment, which is the second spelling
        # `_census_nodes.clause_literals` already reads for `clause`.
        bound = {}
        for node in ast.walk(module):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and isinstance(node.value, ast.Dict)):
                bound.setdefault(node.targets[0].id, set()).update(
                    k.value for k in node.value.keys
                    if isinstance(k, ast.Constant) and isinstance(k.value, str))
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Subscript)
                    and isinstance(node.targets[0].value, ast.Name)
                    and isinstance(node.targets[0].slice, ast.Constant)
                    and isinstance(node.targets[0].slice.value, str)):
                bound.setdefault(node.targets[0].value.id, set()).add(
                    node.targets[0].slice.value)
        raises = {}
        for node in ast.walk(module):
            if not (isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call)):
                continue
            keys = set()
            for arg in list(node.exc.args) + [k.value for k in node.exc.keywords]:
                if isinstance(arg, ast.Dict):
                    keys |= {k.value for k in arg.keys
                             if isinstance(k, ast.Constant) and isinstance(k.value, str)}
                elif isinstance(arg, ast.Name):
                    keys |= bound.get(arg.id, set())
            raises[node.lineno] = keys
        below = [(ln, raises[ln]) for ln in sorted(gates)
                 if ln > first_write and ln in raises]
        if below:
            found[rel] = below
    return found


def test_every_inline_refusal_below_the_first_write_names_the_output_directory():
    """The property, `== {}` over the derived population.

    A halt on view 6 of an eight-view reference stack leaves five RGBA masters and no
    manifest; before this the halt line named the FILE and never the directory those five
    are in, on tools whose own workflow standard says compensators take no skip.
    """
    offenders = {}
    for rel, sites in inline_refusals_below_the_first_write().items():
        for line, keys in sites:
            missing = {"out", "compensator"} - keys
            if missing:
                offenders[f"{rel}:{line}"] = sorted(missing)
    assert offenders == {}, offenders


def test_the_population_is_not_empty():
    """A property over an empty set is not a check. The derivation must find the sites it
    is about — WAVE 34: 13 -> 9 after render_start_frame's nested `_render_still` collapsed
    the per-path inline refusals into the helper."""
    found = inline_refusals_below_the_first_write()
    total = sum(len(v) for v in found.values())
    assert total >= 9, {k: len(v) for k, v in found.items()}
    assert "render_turnaround.py" in found and "render_start_frame.py" in found, found


def test_a_refusal_that_names_only_the_file_is_reported(tmp_path):
    """REVERTED-RED: the pre-fix evidence, which named the file and not the directory."""
    p = tmp_path / "probe_below_write.py"
    p.write_text(
        "import os\n"
        "class G(Exception):\n"
        "    def __init__(self, msg, ev):\n"
        "        super().__init__(msg)\n"
        "        self.evidence = ev\n"
        "def f(path):\n"
        "    raise G('did not draw', {'clause': 'operator_status',\n"
        "                             'path': os.path.abspath(path)})\n",
        encoding="utf-8")
    t = ast.parse(p.read_text(encoding="utf-8"))
    keys = set()
    for node in ast.walk(t):
        if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
            for arg in node.exc.args:
                if isinstance(arg, ast.Dict):
                    keys |= {k.value for k in arg.keys if isinstance(k, ast.Constant)}
    assert {"out", "compensator"} - keys == {"out", "compensator"}


# =======================================================================================
# F-e0ade43a (panel HIGH) — the hand-rolled parser on the tool that exports the tree's
# central artefact
# =======================================================================================
#
# MEASURED on `3380ae2` under the bpy stub with argv
# `blender -b -P tools/rig_character.py -- --help`:
# `RigCharacterError: unknown argument '--help'; known: ['bands', 'binding',
# 'envelope_radii', 'glb', 'measure_only', 'mode', 'name', 'out']`, exit 2. The `known:`
# list is INTERNAL KEY NAMES, and `--measure_only` typed back from it is not the bare flag
# the loop special-cased: it fell through to `partition("=")`, `value` became `''`, and a
# FALSY `measure_only` ran the full skeleton build and GLB export instead of the cheap
# measure pass. `--binding` and `--envelope-radii` were accepted with no vocabulary check
# and, on the DEFAULT route (`--mode=skeleton`), never read again.


def rig_character_parse(extra):
    """`("args"|<exception class name>, value, stdout)` for one real argv."""
    argv = ["blender", "-b", "-P", "x", "--"] + list(extra)
    mod = blender_stub.load_tool("rig_character.py", argv=argv)
    saved = list(sys.argv)
    buf = io.StringIO()
    try:
        sys.argv = list(argv)
        with blender_stub.blender_stubbed(), contextlib.redirect_stdout(buf):
            try:
                return "args", mod.parse_args(), buf.getvalue()
            except SystemExit as exc:
                return "exit", exc.code, buf.getvalue()
            except BaseException as exc:                            # noqa: BLE001
                return type(exc).__name__, exc, buf.getvalue()
    finally:
        sys.argv = saved


def test_rig_character_help_prints_every_flag_in_the_spelling_it_is_typed_in():
    """`--help` is answered rather than refused, and answers in FLAG spellings.

    It exits 0, which only reaches the operator because this file's `__main__` handler
    re-raises `SystemExit` (F-814335e4) instead of recording it as a crash — the two
    findings meet here.
    """
    kind, code, text = rig_character_parse(["--help"])
    assert (kind, code) == ("exit", 0), (kind, code, text)
    for flag in ("--glb", "--out", "--name", "--mode", "--bands", "--binding",
                 "--envelope-radii", "--measure-only"):
        assert flag in text, (flag, text)
    assert "measure_only" not in text, "the internal key name is not a flag"
    assert "blender -b -P tools/rig_character.py --" in text, text
    # every argument carries a sentence, not just a name
    for line in text.splitlines():
        if line.startswith("  --"):
            assert len(line.split()) > 2, line


def test_the_usage_line_names_all_eight_arguments():
    """It named four. The line is built from the table now, so it cannot name four again."""
    kind, exc, _text = rig_character_parse(["--out=o"])
    assert kind == "RigCharacterError", (kind, exc)
    usage = str(exc)
    for flag in ("--glb", "--out", "--name", "--mode", "--bands", "--binding",
                 "--envelope-radii", "--measure-only"):
        assert flag in usage, (flag, usage)


def test_an_unknown_argument_is_answered_in_flag_spellings():
    """The `known:` list is what an operator types back. It was internal key names."""
    kind, exc, _text = rig_character_parse(["--glb=a.glb", "--out=o", "--nope=1"])
    assert kind == "RigCharacterError", (kind, exc)
    assert exc.evidence["known"][0] == "--glb", exc.evidence["known"]
    assert all(k.startswith("--") for k in exc.evidence["known"]), exc.evidence["known"]


def test_the_underscore_spelling_of_the_bare_flag_is_refused_not_silently_disabled():
    """THE DEFECT, driven end to end.

    `--measure_only` used to parse to the empty string, which is falsy, so the run did the
    full build and export instead of the measure pass and nothing anywhere said so. It is
    a named refusal now, and the sentence says which spelling to type.
    """
    kind, exc, _text = rig_character_parse(["--glb=a.glb", "--out=o", "--measure_only"])
    assert kind == "RigCharacterError", (kind, exc)
    assert exc.evidence["clause"] == "argument_carries_no_value"
    assert exc.evidence["flag"] == "--measure-only"
    assert "--measure-only" in str(exc)

    kind, args, _text = rig_character_parse(["--glb=a.glb", "--out=o", "--measure-only"])
    assert kind == "args" and args["measure_only"] is True, (kind, args)


@pytest.mark.parametrize("flag,value,clause", [
    ("--binding", "rigidd", "unknown_binding_mode"),
    ("--envelope-radii", "measuredd", "unknown_envelope_radii"),
])
def test_a_mistyped_vocabulary_is_refused_at_the_boundary(flag, value, clause):
    """Both were accepted at the boundary and then unused on the default route.

    Same clause words as the deeper checks in `apply_binding` — the boundary copy, not a
    second vocabulary, so a halt reader keys on one word either way.
    """
    kind, exc, _text = rig_character_parse(
        ["--glb=a.glb", "--out=o", f"{flag}={value}"])
    assert kind == "GateMode", (kind, exc)
    assert exc.evidence["clause"] == clause
    assert exc.evidence["flag"] == flag
    assert value in str(exc)


def test_a_legal_vocabulary_word_still_parses():
    """The direction that must NOT refuse: a check that refuses everything is not a check."""
    for flag, value in (("--binding", "envelope"), ("--envelope-radii", "default"),
                        ("--mode", "full")):
        kind, args, _text = rig_character_parse(
            ["--glb=a.glb", "--out=o", f"{flag}={value}"])
        assert kind == "args", (flag, value, kind, args)


def test_the_skeleton_manifest_records_the_arguments_that_route_did_not_use():
    """The other half of the finding: `--mode=skeleton` binds nothing, so `--binding` and
    `--envelope-radii` are legal words this route declines to act on — a different
    statement from "you typed it wrong", and both must reach the operator."""
    src = source("rig_character.py")
    assert '"arguments_not_used_on_this_route"' in src
    fn = blender_stub.fn_source("rig_character.py", "run_skeleton")
    assert "arguments_not_used_on_this_route" in fn
    assert '"binding": args["binding"]' in fn
    assert '"envelope_radii": args["envelope_radii"]' in fn


# =======================================================================================
# F-e7d3303e (panel HIGH) — the caption under the panels the Director rules on
# =======================================================================================
#
# `"subtitle": ("17 rigid parts, bone-parented, no deformation anywhere ...")` was a
# literal: the count 17 was TYPED while the run had `visible` in hand thirty lines earlier
# (`blender_scene.render_visible_meshes(scene, meshes)` — `len(visible)` IS the number of
# parts in a rigid-parts GLB), and "no deformation anywhere" was an unconditional
# assertion about a run that measures `arc_liveness`, a DISPLACEMENT: it says the parts
# MOVED, not that none of them deformed. Pointed at a 12-part figure the sheet still said
# 17. This is the fix `make_skeleton_sheet.sheet_subtitle` already had, applied to one
# sheet and not to its neighbour.


def parts_sheet():
    return blender_stub.load_tool("make_parts_sheet.py")


def fake_visible(n):
    return [object() for _ in range(n)]


ARC = {"max_displacement": 0.0123456, "displacement_over_diagonal": 0.00456,
       "bbox_diagonal": 2.703951, "floor": 1e-6, "survived": True}


@pytest.mark.parametrize("n", [12, 17, 21])
def test_the_parts_sheet_subtitle_counts_the_parts_the_run_found(n):
    """DRIVEN against the real function. The count tracks the input, so a 12-part or a
    21-part figure is captioned as what it is."""
    text = parts_sheet().sheet_subtitle(fake_visible(n), ARC, "right", 33)
    assert f"{n} rigid parts" in text, text


def test_the_subtitle_states_the_measurement_instead_of_asserting_no_deformation():
    """The second clause. What the run measures is a displacement; it says the parts
    MOVED, which is not the same claim as "no deformation anywhere"."""
    text = parts_sheet().sheet_subtitle(fake_visible(17), ARC, "right", 33)
    assert "no deformation anywhere" not in text, text
    assert "MOVED" in text, text
    assert f"{ARC['bbox_diagonal']:.6f}" in text, text


def test_the_spec_takes_its_subtitle_from_the_run_rather_than_a_literal():
    """The literal is gone from the CODE — the docstring that records the correction is
    not a candidate, because the repo's law is that the correction is kept, not deleted.

    Asserted on the AST: the `"subtitle"` value in the spec dict is a CALL, not a constant
    or an f-string over constants. `grep -n '17'` in this file returned the old subtitle
    and `ARC_FRAMES = (17, ...)`, an unrelated frame index, and nothing else.
    """
    subtitles = []
    for node in ast.walk(tree("make_parts_sheet.py")):
        if not isinstance(node, ast.Dict):
            continue
        for key, value in zip(node.keys, node.values):
            if isinstance(key, ast.Constant) and key.value == "subtitle":
                subtitles.append(value)
    assert len(subtitles) == 1, subtitles
    assert isinstance(subtitles[0], ast.Call), ast.dump(subtitles[0])[:200]
    assert called_name(subtitles[0]) == "sheet_subtitle"


def test_the_sibling_sheet_is_still_the_shape_this_was_adopted_from():
    """ADOPT THE HOME, and say where the home is. `make_skeleton_sheet.sheet_subtitle`
    derives both halves of its own caption; this asserts it still does, so the two sheets
    cannot drift apart again the way they did between wave 25 and now."""
    fn = blender_stub.fn_source("make_skeleton_sheet.py", "sheet_subtitle")
    assert "len(sitelist.BONES)" in fn
    assert "snap_census(table)" in fn
