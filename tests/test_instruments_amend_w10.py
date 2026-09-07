"""Wave-10 instruments amend: the andons a Blender tool must survive its own failure with.

Every census in this file DERIVES its population from the tree — `blender_stub.blender_tools()`
walks `tools/` for `import bpy`, so a new Blender tool joins the day it lands — and every one of
them is shown RED by a mutation that adds a member without the property. The checkers are written
as pure functions over source or over a mapping wherever that is possible, because a checker
exercised only against the tools it polices reports a clean tree the moment it quietly stops
looking (`test_instrument_exits.sentinel_violations` is the shape being carried).

Helpers here **raise**; they never `assert` (`-O` deletes an `assert` in a non-plugin helper and
`ci.yml`'s `-O` leg would report green over it).
"""

import ast
import builtins
import json
import os
import re

import pytest

# ONE definition of "this member cannot yet be held to the sentinel half of the halt
# contract", imported rather than restated: `stage_render.py` joined the Blender population
# in wave 12 (F-6b3040d1) when it stopped keying on the literal token `import bpy`, and the
# handler it needs is instruments-measure's to write (F-f9251c74).
from test_instrument_exits import halt_contract_pending
from blender_stub import (blender_tools, exit_code_of_main_block, halt_handler,
                          load_tool, main_block, read_source)

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")


# --------------------------------------------------------------------------------------
# F-3bf15648 — a `raise <Name>(...)` whose name the module never binds
# --------------------------------------------------------------------------------------
#
# `rig_repair.py:159` raised `ArmatureError` while line 38 imported `GateFailure` only. The
# branch is the ambiguous-subject refusal, reachable whenever the glTF importer's hidden
# Icosphere makes `len(visible) != 1`: instead of the refusal the comment describes, the
# operator gets `NameError: name 'ArmatureError' is not defined` and a halt record naming
# Python. Nothing in the suite could see it — `test_instrument_exits` replaces `main` with a
# raiser, so no test has ever executed a raise site inside a tool.


def _names_bound_in(scope):
    """Every name the given function/lambda body binds locally: arguments, assignments,
    `import` aliases, `except ... as`, `with ... as`, comprehension targets, nested defs."""
    bound = set()
    args = getattr(scope, "args", None)
    if args is not None:
        for a in (list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs)
                  + [args.vararg, args.kwarg]):
            if a is not None:
                bound.add(a.arg)
    for node in ast.walk(scope):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            bound.add(node.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                bound.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(node, ast.ExceptHandler) and node.name:
            bound.add(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(node.name)
    return bound


def unbound_raise_targets(filename):
    """Every `raise <Name>(...)` in the file whose `<Name>` is bound nowhere it can see.

    The node this keys on is the RAISE SITE (`ast.Raise` -> `Call` -> `Name`), because that
    is where the property lives: a name is bound or it is not at the moment the raise
    executes. Keying on the import lines instead would report a file green for importing a
    name it raises somewhere else, and keying on the module namespace alone cannot see a
    raise at all.

    A name counts as bound if it is a builtin, an attribute of the module as imported (which
    is the module-level namespace the loaded tool actually has), or bound locally inside the
    enclosing function -- the shape ten of these files use, `from armature_core.errors import
    ArmatureError, GateFailure` inside an `except` block. Returns `[(lineno, name)]`.
    """
    tree = ast.parse(read_source(filename))
    mod = load_tool(filename)
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    bad = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Raise) or node.exc is None:
            continue
        exc = node.exc
        target = exc.func if isinstance(exc, ast.Call) else exc
        if not isinstance(target, ast.Name):
            continue
        name = target.id
        if name in dir(builtins) or hasattr(mod, name):
            continue
        local = False
        cur = parents.get(node)
        while cur is not None and not local:
            if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
                local = name in _names_bound_in(cur)
            cur = parents.get(cur)
        if not local:
            bad.append((node.lineno, name))
    return bad


@pytest.mark.parametrize("filename", blender_tools())
def test_every_raise_names_something_the_module_actually_binds(filename):
    """`raise ArmatureError(...)` in a module that imported only `GateFailure` is a
    `NameError` wearing a refusal's clothes: the tool crashes (exit 1) where it meant to
    decline (exit 2), and the receipt names Python instead of naming the ambiguous subject."""
    bad = unbound_raise_targets(filename)
    assert bad == [], (
        f"{filename} raises name(s) it does not bind: {bad}. The raise site is reachable in "
        f"ordinary use and produces a NameError, not the refusal it was written to be")


def test_the_unbound_raise_census_goes_red_on_a_member_that_has_the_defect(tmp_path,
                                                                          monkeypatch):
    """Rule 3: prove it can fail. A synthetic tool with `rig_repair`'s exact shape — one
    error name imported, a different one raised — must be reported."""
    probe = tmp_path / "probe_tool.py"
    probe.write_text(
        "from armature_core.errors import GateFailure\n"
        "def main():\n"
        "    raise ArmatureError('the subject is ambiguous')\n", encoding="utf-8")
    import blender_stub
    monkeypatch.setattr(blender_stub, "TOOLS", str(tmp_path))
    monkeypatch.setattr("test_instruments_amend_w10.load_tool", blender_stub.load_tool)
    bad = unbound_raise_targets("probe_tool.py")
    assert bad == [(3, "ArmatureError")], bad


def test_the_ambiguous_subject_refusal_is_a_refusal_and_not_a_name_error(tmp_path):
    """The behavioural half of F-3bf15648, on the real branch rather than on the AST.

    Under the Blender stub `bpy.data.objects` iterates empty, so `render_visible_meshes`
    returns nothing and `len(visible) != 1` — the F-cb986eb3 / F-e911313d family guard the
    comment inside `rig_repair.py::main` describes (RE-ANCHORED ON THE SYMBOL, wave 28:
    the citation read `rig_repair.py:157-161` and that line went blank when this domain's
    `--help` work landed above it; a line number is prose, the function and the clause are
    what this test is about), and the branch an ordinary GLB reaches
    whenever the glTF importer's hidden Icosphere is present. It must raise the module's
    own refusal.
    """
    from armature_core.errors import ArmatureError

    argv = ["blender", "-b", "-P", "rig_repair.py", "--", "--glb=nope.glb",
            "--out=" + str(tmp_path / "out")]
    mod = load_tool("rig_repair.py", argv=argv)
    import sys as _sys
    saved = list(_sys.argv)
    try:
        _sys.argv = list(argv)
        with pytest.raises(ArmatureError) as caught:
            mod.main()
    finally:
        _sys.argv = saved
    assert not isinstance(caught.value, NameError)
    assert "render-visible mesh object(s)" in str(caught.value)


def test_the_ambiguous_subject_refusal_earns_the_refusal_exit_code(tmp_path, capsys):
    """...and the halt contract on that exact raiser: exit 2, one six-key sentinel line.

    Driven with the tool's OWN `main`, not with a synthetic raiser, so what is measured is
    the refusal the tool actually produces travelling through the handler it actually has.
    """
    argv = ["blender", "-b", "-P", "rig_repair.py", "--", "--glb=nope.glb",
            "--out=" + str(tmp_path / "out")]
    real = load_tool("rig_repair.py", argv=argv).main
    code, escaped = exit_code_of_main_block("rig_repair.py", raiser=real, argv=argv)
    out = capsys.readouterr().out
    assert escaped is None, f"{escaped!r} escaped the handler; blender -b -P exits 0"
    assert code == 2, f"exit code {code!r}; a deliberate refusal is 2, a crash is 1"
    lines = [l for l in out.splitlines() if l.split(" ", 1)[0] == "RIG_REPAIR_HALT"]
    assert len(lines) == 1, out
    rec = json.loads(lines[0][len("RIG_REPAIR_HALT"):])
    assert set(rec) == {"tool", "outcome", "gate", "error", "message", "evidence"}
    assert rec["outcome"] == "REFUSED \u2014 the tool declined to proceed", rec
    # WAVE 25 (instruments, F-3b71c0aa): `ArmatureError` -> `RigRepairSubjectError`,
    # CORRECTED IN PLACE rather than loosened. This site raised the family BASE, which
    # `errors.ArmatureError`'s own docstring calls the thing the wave-14 constructor is
    # "not a licence for": the family names nothing about which andon pulled, and the
    # tree-wide census in `test_instruments_measure_amend_w14.py` holds a bare base raise
    # WITH evidence at zero. The halt line now names the class AND carries the clause,
    # which is the property this assertion exists to read.
    assert rec["error"] == "RigRepairSubjectError", rec
    assert rec["evidence"]["clause"] == "subject_is_not_one_render_visible_mesh", rec


# --------------------------------------------------------------------------------------
# F-161b09fc -- the success sentinel every Blender invocation is bound to check
# --------------------------------------------------------------------------------------
#
# `docs/experiments/E07-the-skeleton.md:202-205` records the rule this repo binds every
# `blender -b -P` call to: verify a success sentinel in the output, never the exit code
# alone. Wave 8 made the HALT half uniform -- 21 of 21 print `<STEM>_HALT`. The OK half was
# not. MEASURED 2026-09-04: `make_test_armature` printed no uppercase token AT ALL, so a
# caller following the rule had nothing to match on the tool that builds the synthetic
# subject GLB and the authored `.joints.json` every arc comparison is measured against;
# `PANELS_OK` was printed by FOUR different tools, so a grep after running one is satisfied
# by another's line in the same log; and `PROBE_GLB` / `PROBE_SUBJECT` were PREFIXES of
# their own tools' `PROBE_GLB_HALT` / `PROBE_SUBJECT_HALT` lines, so the success grep
# matched the halt.


def _print_prefix(call):
    """The literal string a `print(...)` call starts with, or None.

    Handles the three shapes in this tree: a bare constant, `"TOKEN " + json.dumps(...)`,
    and an f-string whose first piece is a constant.
    """
    if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
            and call.func.id == "print" and call.args):
        return None
    node = call.args[0]
    while isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        node = node.left
    if isinstance(node, ast.JoinedStr):
        node = node.values[0] if node.values else None
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _handler_node_ids(tree):
    ids = set()
    for top in tree.body:
        if (isinstance(top, ast.If) and isinstance(top.test, ast.Compare)
                and isinstance(top.test.left, ast.Name)
                and top.test.left.id == "__name__"):
            ids.update(id(n) for n in ast.walk(top))
    return ids


def halt_prefix(filename):
    """The `<PREFIX>` of the tool's halt sentinel, from its `__main__` handler.

    Keyed on the HANDLER's own sentinel -- the node the halt contract's identity actually
    lives on -- rather than on the file's stem, so a tool whose token and stem disagree is
    REPORTED by the pairing assertion below instead of being defined into agreement by the
    census's own derivation.

    **WAVE 25 (F-40316edd): there are TWO spellings of the handler, and this reads both.**
    A tool that adopts `armature_core.parts.run_tool_main` passes its prefix as an argument
    (`run_tool_main(main, "STAGE_RENDER")`) and carries no `"<PREFIX>_HALT "` literal at
    all, so a walk for the literal reported `[]` and this raised on the FIRST Blender-side
    tool to adopt the home -- on the commit that adopted it. `blender_stub.halt_handler` is
    the ONE derivation that already reads both spellings (wave 23, F-2f1b18c2); it is used
    here rather than a second copy of the walk, and the literal walk stays as the
    cross-check that the two agree wherever a literal exists.
    """
    handler = halt_handler(filename)
    tree = ast.parse(read_source(filename))
    found = set()
    for top in tree.body:
        if not (isinstance(top, ast.If) and isinstance(top.test, ast.Compare)
                and isinstance(top.test.left, ast.Name)
                and top.test.left.id == "__name__"):
            continue
        for node in ast.walk(top):
            prefix = _print_prefix(node)
            if prefix and prefix.split(" ", 1)[0].endswith("_HALT"):
                found.add(prefix.split(" ", 1)[0][: -len("_HALT")])
    if found:
        if len(found) != 1:
            raise ValueError(
                f"{filename}: {sorted(found)} HALT token(s) in the handler, want 1")
        literal = found.pop()
        if handler is not None and handler["prefix"] != literal:
            raise ValueError(
                f"{filename}: the printed token is {literal!r} and the handler declares "
                f"{handler['prefix']!r}")
        return literal
    if handler is None:
        raise ValueError(f"{filename}: no HALT token and no handler in the `__main__` block")
    return handler["prefix"]


def success_tokens(filename):
    """Every uppercase token a `print` OUTSIDE the `__main__` handler leads with.

    Keyed on the PRINT CALLS -- the node an operator's grep actually reads -- not on the
    module docstring and not on a typed list. The HALT token is excluded: it is the failure
    half of the contract and `test_instrument_exits.py` pins it. Returns
    `{token: [(lineno, literal)]}`.
    """
    tree = ast.parse(read_source(filename))
    in_handler = _handler_node_ids(tree)
    out = {}
    for node in ast.walk(tree):
        if id(node) in in_handler:
            continue
        prefix = _print_prefix(node)
        if not prefix:
            continue
        head = prefix.split(" ", 1)[0]
        if head.endswith("_HALT") or not re.fullmatch(r"[A-Z][A-Z0-9_]*", head):
            continue
        out.setdefault(head, []).append((node.lineno, prefix))
    return out


BLENDER_TOOLS = blender_tools()

#: The members that print no `<STEM>_HALT` line at all, so no clause of the halt contract
#: has anything to read. Derived from the objective property, never typed — the category
#: empties itself the moment the handler lands.
HALT_PENDING = [f for f in BLENDER_TOOLS if halt_contract_pending(f)]
HALT_HELD = [f for f in BLENDER_TOOLS if not halt_contract_pending(f)]


def test_the_halt_pending_category_is_the_one_the_exit_census_names():
    """Rule 3: what cannot be judged is counted, and counted in ONE place.

    This file and `tests/test_instrument_exits.py` read the same category from the same
    function, so the two cannot disagree about which members are pending.
    """
    import test_instrument_exits as EX

    assert set(HALT_PENDING) <= EX.HALT_CONTRACT_PENDING, sorted(
        set(HALT_PENDING) - EX.HALT_CONTRACT_PENDING)
    assert set(HALT_PENDING) | set(HALT_HELD) == set(BLENDER_TOOLS)


@pytest.mark.parametrize("filename", HALT_HELD)
def test_every_blender_tool_prints_the_success_token_its_halt_token_pairs_with(filename):
    """`<PREFIX>_OK <payload>` for the same `<PREFIX>` the handler halts under.

    Pairing the two halves is the property: a caller told to key on a success sentinel has
    to derive it from something, and the only thing it already holds is the halt token. A
    payload is required (hence the trailing space) because a bare token says nothing about
    WHAT succeeded -- `render_turnaround.py:785` printed exactly that.
    """
    prefix = halt_prefix(filename)
    tokens = success_tokens(filename)
    want = prefix + "_OK"
    assert sorted(tokens) == [want], (
        f"{filename} halts under {prefix}_HALT but its success token(s) are "
        f"{sorted(tokens)}; a caller keying on {want} has nothing to match")
    for _lineno, literal in tokens[want]:
        assert literal.startswith(want + " "), (
            f"{filename}: {literal!r} carries no payload after the token")


def shared_success_tokens(token_map):
    """`{token: [tools]}` for every token more than one tool prints -- the `PANELS_OK` shape.

    A pure function of the mapping, so it can be shown red against a synthetic tree while
    the census below feeds it the derived one.
    """
    owners = {}
    for filename, tokens in token_map.items():
        for token in tokens:
            owners.setdefault(token, []).append(filename)
    return {t: sorted(v) for t, v in owners.items() if len(v) > 1}


def test_no_success_token_is_printed_by_two_different_tools():
    """MEASURED 2026-09-04: `PANELS_OK` came from `make_binding_sheet:267`,
    `make_parts_sheet:313`, `make_rig_sheet:237` and `make_skeleton_sheet:351`, so a caller
    that ran one of them and grepped for it was satisfied by any of the other three."""
    derived = {fn: set(success_tokens(fn)) for fn in HALT_HELD}
    shared = shared_success_tokens(derived)
    assert shared == {}, f"success tokens claimed by more than one tool: {shared}"


def test_no_success_token_is_a_prefix_of_any_tools_halt_token():
    """`PROBE_GLB` matched `PROBE_GLB_HALT`: the success grep was satisfied by the halt."""
    halts = {halt_prefix(fn) + "_HALT" for fn in HALT_HELD}
    bad = []
    for fn in HALT_HELD:
        for token in success_tokens(fn):
            hits = sorted(h for h in halts if h.startswith(token))
            if hits:
                bad.append((fn, token, hits))
    assert bad == [], bad


def test_the_sharing_checker_goes_red_on_the_shape_that_was_measured_here():
    """Rule 3, on the checker rather than on the tree: the four-way `PANELS_OK` collision."""
    synthetic = {
        "make_binding_sheet.py": {"PANELS_OK"}, "make_parts_sheet.py": {"PANELS_OK"},
        "make_rig_sheet.py": {"PANELS_OK"}, "make_skeleton_sheet.py": {"PANELS_OK"},
        "preview_glb.py": {"PREVIEW_GLB_OK"},
    }
    assert shared_success_tokens(synthetic) == {
        "PANELS_OK": ["make_binding_sheet.py", "make_parts_sheet.py", "make_rig_sheet.py",
                      "make_skeleton_sheet.py"]}


def test_the_pairing_checker_goes_red_on_a_tool_with_no_success_token_at_all(tmp_path,
                                                                            monkeypatch):
    """`make_test_armature`'s exact state: human prose only, no uppercase token to match."""
    probe = tmp_path / "probe_ok.py"
    probe.write_text(
        'import bpy\n'
        'def main():\n'
        '    print("[probe_ok] done")\n'
        'if __name__ == "__main__":\n'
        '    try:\n'
        '        raise SystemExit(main())\n'
        '    except SystemExit:\n'
        '        raise\n'
        '    except BaseException:\n'
        '        print("PROBE_OK_HALT {}")\n', encoding="utf-8")
    import blender_stub
    monkeypatch.setattr(blender_stub, "TOOLS", str(tmp_path))
    assert halt_prefix("probe_ok.py") == "PROBE_OK"
    assert success_tokens("probe_ok.py") == {}


# --------------------------------------------------------------------------------------
# The halt-handler escape routed from the tests domain (panel CRITICAL there)
# --------------------------------------------------------------------------------------
#
# `json.dumps(..., default=str)` applies `default` to VALUES only. A key that is not a
# string, int, float, bool or None -- a tuple, a `numpy.int64` -- raises `TypeError` from
# inside the `except` block, which leaves the whole `try` statement with `sys.exit` never
# reached. Under `blender -b -P` that is exit **0**: a fired andon reported as a success,
# and no sentinel line at all. MEASURED 2026-09-04 against all 21 handlers: 21 of 21
# escaped with `code=None`.
#
# Two evidence dicts in this tree already key on things that are not strings by nature --
# per-frame maps keyed by frame index and per-joint maps keyed by a `(bone, axis)` pair --
# so this is a shape the andons are one refactor away from producing, not a hypothetical.


def _nonstring_key_raiser():
    """A fired gate whose evidence keys are a tuple and a `numpy.int64`."""
    import numpy as np

    from armature_core.errors import GateFailure

    class _Gate(GateFailure):
        gate = "PROBE"

    def raiser():
        raise _Gate("a gate fired", {("hip", "z"): 1.5, np.int64(7): "frame 7",
                                     "measured": 1})

    return raiser


@pytest.mark.parametrize("filename", [f for f in HALT_HELD if main_block(f) is not None])
def test_a_non_string_keyed_evidence_dict_does_not_delete_the_exit_code(filename, tmp_path,
                                                                       capsys):
    """The handler serialises its own keys, and `sys.exit` runs whatever happens.

    The contract is unchanged by the fix: still exactly one `<STEM>_HALT <json>` line, still
    exactly six keys, still exit 2 for a fired gate. What changes is that a `TypeError` in
    the sentinel's own serialisation can no longer swallow the halt.
    """
    argv = ["blender", "-b", "-P", filename, "--", "--glb=nope.glb",
            "--out=" + str(tmp_path / "out")]
    code, escaped = exit_code_of_main_block(filename, raiser=_nonstring_key_raiser(),
                                            argv=argv)
    out = capsys.readouterr().out
    assert escaped is None, (
        f"{filename}: {escaped!r} escaped the handler because the sentinel could not be "
        f"serialised; `sys.exit` never ran and `blender -b -P` reports success")
    assert code == 2, f"{filename}: exit code {code!r}, contract says 2 for a fired gate"

    stem = filename[:-3].upper()
    lines = [l for l in out.splitlines() if l.split(" ", 1)[0] == stem + "_HALT"]
    assert len(lines) == 1, f"{filename}: {len(lines)} sentinel line(s)\n{out}"
    rec = json.loads(lines[0][len(stem) + len("_HALT"):])
    assert set(rec) == {"tool", "outcome", "gate", "error", "message", "evidence"}, rec
    assert rec["outcome"] == "HALTED — a gate fired", rec
    assert rec["gate"] == "PROBE", rec
    assert isinstance(rec["evidence"], dict), rec
    assert all(isinstance(k, str) for k in rec["evidence"]), rec["evidence"]
    assert rec["evidence"]["measured"] == 1, rec["evidence"]
    assert len(rec["evidence"]) == 3, (
        f"{filename}: the two non-string-keyed entries must survive as stringified keys, "
        f"not be dropped: {rec['evidence']}")


def test_the_keysafe_helper_stringifies_keys_at_every_depth():
    """The helper itself, on the shape `default=str` cannot reach: keys, not values, and
    keys nested inside lists and inner dicts."""
    import numpy as np

    mod = load_tool("preview_glb.py")
    got = mod._halt_keysafe({("hip", "z"): {np.int64(3): "x"}, "rows": [{(1, 2): "y"}]})
    assert json.loads(json.dumps(got, default=str)) == {
        "('hip', 'z')": {"3": "x"}, "rows": [{"(1, 2)": "y"}]}


@pytest.mark.parametrize("filename", [f for f in HALT_HELD if main_block(f) is not None])
def test_every_handler_carries_the_keysafe_helper(filename):
    """The family census. One implementation per tool today (21 copies, recorded as a
    Stage B lift into `armature_core.errors` under `skipped[]`), so the property has to be
    asserted of every member rather than of one shared function.

    **WAVE 25 (F-40316edd): the lift LANDED, and this reads the resolved shape.** The
    helper's one home is `armature_core.parts.halt_keysafe` (wave 22), and a tool that
    hands its `__main__` to `parts.run_tool_main` gets the walk by delegation -- it defines
    no `_halt_keysafe` of its own and must not, because a second copy is the thing the lift
    removed. `stage_render` is the first Blender-side adopter; read as a missing helper, it
    would fail here on the commit that deleted its copy, which is the census keying on the
    spelling rather than on the property (wave 18, rule 1). The property is "the handler
    this tool runs stringifies keys at every depth", and it is satisfied either way.

    WAVE 28 (instruments): "does this handler adopt `run_tool_main`?" is answered by an AST
    walk for a CALL, not by a substring in the block's text. MEASURED on this branch: the
    five handlers that gained `except SystemExit: raise` (F-814335e4) carry a comment
    naming `armature_core.parts.run_tool_main` as the CPython home the two lines are
    adopted from -- and the substring test then read all five as delegating to it, so it
    demanded they have no `_halt_keysafe` and failed on the five local walks the recorded
    exception says they keep. A sentence ABOUT a call is not a call; this is the same trap
    the wave-26 merge recorded for the clause census ("a prose sentence quoting the literal
    reads as a raise site") and wave 18's rule 1 in one line.
    """
    block = read_source(filename).split('if __name__ == "__main__":')[-1]
    delegates = any(
        isinstance(n, ast.Call)
        and (getattr(n.func, "attr", None) == "run_tool_main"
             or getattr(n.func, "id", None) == "run_tool_main")
        for n in ast.walk(ast.parse(read_source(filename))))
    if delegates:
        from armature_core.parts import halt_keysafe, run_tool_main  # noqa: F401

        assert callable(halt_keysafe)
        assert not hasattr(load_tool(filename), "_halt_keysafe"), (
            f"{filename} adopts `parts.run_tool_main` AND keeps a local `_halt_keysafe`; "
            f"the lift exists so there is one walk, not two")
        return
    mod = load_tool(filename)
    assert callable(getattr(mod, "_halt_keysafe", None)), (
        f"{filename} has no `_halt_keysafe`; its sentinel cannot serialise a "
        f"non-string-keyed evidence dict and the halt escapes")
    assert "_halt_keysafe(" in block, (
        f"{filename} defines the helper but its handler does not use it")


# --------------------------------------------------------------------------------------
# F-13bd448d + F-51c5e0ef -- a writer verifies its own output before it claims success
# --------------------------------------------------------------------------------------
#
# `bpy.ops.render.render(write_still=True)` returns an operator status set and can return
# `{'CANCELLED'}` without raising. Four tools discarded it and then printed a success
# sentinel over a directory that may hold nothing: `preview_glb` (four views, and its only
# downstream consumer `make_cast_sheet` reads the stats JSON rather than the PNGs, so a run
# that wrote zero images leaves no failing consumer anywhere) and the three sheet tools --
# `make_skeleton_sheet`, whose 14 `shoot()` calls name 28 PNG paths that go straight into
# `panels.json`, being the sheet the Director approves the skeleton on. `make_rig_sheet`
# imports `make_parts_sheet.shoot`, so it is a fifth caller of the same fix.


#: WAVE 12, F-b777d4a3 — the population of "a tool that writes an artefact", by BEHAVIOUR.
#:
#: `_render_call_sites` kept a node only when `ast.unparse(node.func)` was exactly
#: `bpy.ops.render.render`, so the tools whose output is a GLB rather than a PNG were
#: outside this census entirely. Measured over `tools/*.py` on 2026-09-04: **9 export calls
#: across 8 modules** — author_walk :604, lift_solve :332, make_test_armature :301,
#: rig_bake :279, rig_character :944, rig_parts :519, rig_repair :202, rig_retopo :405 and
#: :412 — and none of them was reachable by this walk. (The routed finding quoted 13 across
#: the same 8 modules; re-measured here, 4 of those 13 are
#: `bpy.ops.export_scene.gltf.get_rna_type(...)` introspection calls in author_walk,
#: lift_solve, rig_character and rig_parts, which discover the exporter's own keyword names
#: and write nothing. The population is the same 8; the site count is 9.) The exported GLB is
#: this repo's canonical
#: deliverable (the rig_* family's entire product), and the comment around this census
#: reasons about "a sentinel over a directory that may hold nothing", which is precisely what
#: an unverified export leaves.
WRITER_OPS = ("bpy.ops.render.render", "bpy.ops.export_scene.gltf")


def _writer_call_sites(filename, ops=WRITER_OPS):
    """`{op: [lines]}` for every `bpy.ops.*` call in `ops` — the artefact writers.

    Exact match on the unparsed callee, so `bpy.ops.export_scene.gltf.get_rna_type()` — an
    INTROSPECTION call the exporters make to discover their own keyword names — is not
    counted as a write.
    """
    tree = ast.parse(read_source(filename))
    out = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        try:
            called = ast.unparse(node.func)
        except Exception:                                               # noqa: BLE001
            continue
        if called in ops:
            out.setdefault(called, []).append(node.lineno)
    return {k: sorted(v) for k, v in out.items()}


def _render_call_sites(filename):
    """Line numbers of every `bpy.ops.render.render(...)` call in the file."""
    return _writer_call_sites(filename, ("bpy.ops.render.render",)).get(
        "bpy.ops.render.render", [])


def _export_call_sites(filename):
    """Line numbers of every `bpy.ops.export_scene.gltf(...)` call in the file."""
    return _writer_call_sites(filename, ("bpy.ops.export_scene.gltf",)).get(
        "bpy.ops.export_scene.gltf", [])


def _calls_named(filename, names):
    """`{callee: [names passed as its first positional argument]}` for `names`.

    Resolves both `f(x)` and `mod.f(x)` — WAVE 34's `rc.require_render_target_moved(path)`
    is the Attribute form the Name-only walk could not see.
    """
    tree = ast.parse(read_source(filename))
    out = {n: [] for n in names}
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and node.args
                and isinstance(node.args[0], ast.Name)):
            continue
        func = node.func
        callee = (func.id if isinstance(func, ast.Name)
                  else func.attr if isinstance(func, ast.Attribute) else None)
        if callee in out:
            out[callee].append(node.args[0].id)
    return out


def _render_output_names(filename):
    """Every variable name assigned to `scene.render.filepath` -- the file a render writes."""
    tree = ast.parse(read_source(filename))
    names = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if (isinstance(target, ast.Attribute) and target.attr == "filepath"
                    and isinstance(node.value, ast.Name)):
                names.add(node.value.id)
    return names


#: Derived 2026-09-04 by AST over `blender_tools()` for `bpy.ops.render.render` call sites.
#: Equality, so a tool that starts rendering cannot skip this census in the same commit.
RECORDED_RENDERERS = [
    "make_binding_sheet.py", "make_parts_sheet.py", "make_skeleton_sheet.py",
    "preview_glb.py", "preview_walk.py", "render_performer.py",
    "render_start_frame.py", "render_turnaround.py",
]

#: The ONE exemption, keyed on its REASON rather than on a proxy, and re-derived below
#: rather than trusted: this tool never asks whether the file exists because it OPENS every
#: render it takes, and an absent file raises there instead.
READ_BACK_EXEMPT = {
    # WAVE 34: nested `_render_still(path)` assigns `scene.render.filepath = path` and
    # read-backs via `require_render_target_moved(path, ...)` (Attribute callee). The
    # `_calls_named` walk below resolves both Name and Attribute.attr forms.
    "render_start_frame.py": ("_pixels", "_alpha_channel", "require_render_target_moved"),
}


#: Derived 2026-09-04 by AST over `blender_tools()` for `bpy.ops.export_scene.gltf` call
#: sites — the half of the writer population `_render_call_sites` could not reach. Equality,
#: so a tool that starts exporting cannot skip this census in the same commit.
RECORDED_EXPORTERS = [
    "author_walk.py", "lift_solve.py", "make_test_armature.py", "rig_bake.py",
    "rig_character.py", "rig_parts.py", "rig_repair.py", "rig_retopo.py",
]

#: WAVE 12, F-b777d4a3. The eight exporters do not ask whether the GLB they claim to have
#: written is there — none of them contains an `os.path.isfile(` at all. Named, dated
#: 2026-09-04, routed to INSTRUMENTS (the rig_* family and author_walk) and core-solvers
#: (`lift_solve`). A CEILING: a tool that grows the read-back leaves this set without failing
#: the file that named it, and a NEW exporter with no read-back fails loudly.
#:
#: The stake: a `rig_*` tool whose glTF export silently writes nothing — a wrong filepath, an
#: empty selection, an exporter refusal swallowed upstream — prints its `_OK` line and exits
#: 0 over an empty output directory, and the census written to make a writer verify its own
#: output has never looked at the export half of the tree.
#:
#: WAVE 16 — CLOSED and re-derived to EMPTY, not carried. Wave 14 landed
#: `rig_character.gate_glb_written` at every one of the nine export sites across the eight
#: tools, and that gate IS the read-back (`os.path.isfile` + `os.path.getsize` + the
#: exporter's own `FINISHED` status, each raising `GateGlbWritten`). The seven skips this
#: set gated described a hole that had already been closed; only `rig_character` — the
#: module that holds the implementation — satisfied the two-token check that produced them.
#: The set is derived from the property now, so a tool that loses its read-back fails
#: rather than joining a list.
EXPORT_READ_BACK_ROUTED = set()


def test_the_writer_population_is_derived_and_is_the_one_recorded():
    """Size and membership before the property, for BOTH halves of "writes an artefact"."""
    renderers = sorted(f for f in BLENDER_TOOLS if _render_call_sites(f))
    assert renderers == RECORDED_RENDERERS, {
        "appeared": sorted(set(renderers) - set(RECORDED_RENDERERS)),
        "vanished": sorted(set(RECORDED_RENDERERS) - set(renderers))}
    assert set(READ_BACK_EXEMPT) <= set(renderers), sorted(READ_BACK_EXEMPT)

    exporters = sorted(f for f in BLENDER_TOOLS if _export_call_sites(f))
    assert exporters == RECORDED_EXPORTERS, {
        "appeared": sorted(set(exporters) - set(RECORDED_EXPORTERS)),
        "vanished": sorted(set(RECORDED_EXPORTERS) - set(exporters))}
    assert set(EXPORT_READ_BACK_ROUTED) <= set(exporters), sorted(
        set(EXPORT_READ_BACK_ROUTED) - set(exporters))

    # 9 export calls across the 8, measured — beside the membership, so a call vanishing
    # inside a module that keeps one is visible.
    total = sum(len(_export_call_sites(f)) for f in exporters)
    assert total == 9, {f: _export_call_sites(f) for f in exporters}


def test_the_writer_walk_does_not_count_the_exporters_introspection_call():
    """`bpy.ops.export_scene.gltf.get_rna_type()` is how four of these tools discover their
    own keyword names. Counting it as a write would inflate the population and make the
    site count above meaningless."""
    src = read_source("rig_character.py")
    assert "bpy.ops.export_scene.gltf.get_rna_type" in src, (
        "the introspection call is gone; re-derive this test's premise")
    sites = _writer_call_sites("rig_character.py")
    assert sites["bpy.ops.export_scene.gltf"] == _export_call_sites("rig_character.py")
    assert len(sites["bpy.ops.export_scene.gltf"]) == 1, sites
    # …and a walk that matched on a PREFIX would count three here instead of one.
    prefix_matched = [n for n in ast.walk(ast.parse(src))
                      if isinstance(n, ast.Call)
                      and ast.unparse(n.func).startswith("bpy.ops.export_scene.gltf")]
    assert len(prefix_matched) == 3, len(prefix_matched)


#: The ONE implementation of the export read-back, and the module that owns it. Every
#: exporter either performs the read-back inline or calls this; keying on the two tokens
#: alone was keying on the shape ONE tool happens to use (wave 16).
CANONICAL_EXPORT_GATE = ("rig_character.py", "gate_glb_written")


def _reads_its_own_export_back(filename):
    """`(True, how)` if this exporter asks whether the GLB reached disk — either spelling.

    WAVE 16. The predicate was `"os.path.isfile(" in src and "os.path.getsize(" in src`, and
    seven of the eight exporters skipped on it under a routed-to-a-domain reason.
    Re-measured on `041027c` in this worktree: **all eight call
    `rig_character.gate_glb_written`**, which IS the read-back — `rig_character.py::render_target_snapshot`
    `os.path.isfile(p)` and `:296` `os.path.getsize(p)`, plus the operator's own `FINISHED`
    status, each raising `GateGlbWritten`. Wave 14 landed that gate at every export site
    (instruments confirmed it in the wave-16 seams inbox), so the skip reasons described a
    hole that had been closed, and only `rig_character` itself — the module that HOLDS the
    implementation — satisfied the token check. `make_test_armature.py` and `rig_retopo.py`
    do not contain the string `os.path.getsize(` at all and were exporting through a gate
    that does.
    """
    src = read_source(filename)
    _owner, gate = CANONICAL_EXPORT_GATE
    if gate + "(" in src:
        return True, f"calls {gate}()"
    if "os.path.isfile(" in src and "os.path.getsize(" in src:
        return True, "reads the file back inline"
    return False, "neither"


def test_the_canonical_export_gate_is_the_read_back_and_not_merely_a_name():
    """The premise `_reads_its_own_export_back` rests on, measured rather than assumed.

    If `gate_glb_written` stopped opening the file, every caller would keep satisfying the
    property below by calling a gate that no longer checks anything — the disarming shape
    this wave is about. So the implementation is read here, once, and the tokens are
    asserted against the module that owns them.
    """
    owner, gate = CANONICAL_EXPORT_GATE
    src = read_source(owner)
    assert f"def {gate}(" in src, f"{owner} no longer defines {gate}; re-derive this premise"
    body = src.split(f"def {gate}(", 1)[1].split("\ndef ", 1)[0]
    assert "os.path.isfile(" in body, f"{gate} no longer asks whether the file is there"
    assert "os.path.getsize(" in body, f"{gate} no longer asks how big it is"
    assert "FINISHED" in body, f"{gate} no longer reads the exporter's own status"
    assert "raise GateGlbWritten" in body, f"{gate} diagnoses without refusing"


@pytest.mark.parametrize("filename", RECORDED_EXPORTERS)
def test_every_exporter_asks_whether_the_glb_it_claims_to_have_written_is_there(filename):
    """The verify-your-own-output property, extended to the export half of the tree.

    The exported GLB is this repo's canonical deliverable; a `bpy.ops.export_scene.gltf`
    that writes nothing raises no exception the caller sees.

    WAVE 16: the seven skips this test carried are DELETED, not re-routed. Each skip reason
    asserted that its tool never asks whether the GLB reached disk; measured here, all eight
    call the canonical gate that asks, and `EXPORT_READ_BACK_ROUTED` is empty as a result.
    """
    reads_back, how = _reads_its_own_export_back(filename)
    assert reads_back, (
        f"{filename} exports at {_export_call_sites(filename)} and never asks whether the "
        f"GLB reached disk — neither inline nor through "
        f"{CANONICAL_EXPORT_GATE[0]}:{CANONICAL_EXPORT_GATE[1]}; a wrong filepath, an empty "
        f"selection or a swallowed exporter refusal produces a success sentinel over an "
        f"empty directory ({how})")


def test_the_export_read_back_backlog_is_empty_and_says_so():
    """F-b777d4a3's routing table, re-derived rather than trusted (wave 16).

    `EXPORT_READ_BACK_ROUTED` was `set(RECORDED_EXPORTERS)` — every exporter — and seven of
    the eight skipped against it. Wave 14 landed `gate_glb_written` at every export site, so
    the backlog is empty; a tool that loses its read-back re-enters it by failing the
    property above, not by being added to a list.
    """
    outstanding = sorted(f for f in RECORDED_EXPORTERS
                         if not _reads_its_own_export_back(f)[0])
    assert outstanding == [], outstanding
    assert EXPORT_READ_BACK_ROUTED == set(), sorted(EXPORT_READ_BACK_ROUTED)
    # …and the spelling that made seven of them look uncovered: only the module that HOLDS
    # the implementation satisfies the old two-token check.
    inline = sorted(f for f in RECORDED_EXPORTERS
                    if "os.path.isfile(" in read_source(f)
                    and "os.path.getsize(" in read_source(f))
    assert inline == ["rig_character.py"], inline


@pytest.mark.parametrize("filename", [f for f in RECORDED_RENDERERS
                                      if f not in READ_BACK_EXEMPT])
def test_every_renderer_asks_whether_the_file_it_claims_to_have_written_is_there(filename):
    """MEASURED 2026-09-04, render-call sites against existence checks per file:
    preview_glb 1/0, make_skeleton_sheet 1/0, make_binding_sheet 1/0, make_parts_sheet 1/0,
    against preview_walk (isfile+getsize over the plan), render_performer (the same shape
    over `paths`) and render_turnaround (a view that wrote no file raises)."""
    src = read_source(filename)
    assert "os.path.isfile(" in src and "os.path.getsize(" in src, (
        f"{filename} renders at {_render_call_sites(filename)} and never asks whether a "
        f"single pixel reached disk; a cancelled render, a full disk or a permission "
        f"error produces a success sentinel over an empty directory")


def test_the_read_back_exemption_holds_for_the_reason_it_states():
    """Rule 4 of wave 8: an exemption is re-derived, not trusted. `render_start_frame` is
    exempt only if EVERY path it renders to is later opened by one of the named readers."""
    for filename, readers in READ_BACK_EXEMPT.items():
        written = _render_output_names(filename)
        assert written, filename
        read_back = set()
        for names in _calls_named(filename, readers).values():
            read_back.update(names)
        assert written <= read_back, {
            "file": filename, "rendered_but_never_opened": sorted(written - read_back)}


# ---------------------- a success line is EARNED by a measurable effect (wave 12, rule 4)
#
# F-b777d4a3's second half. `test_every_blender_tool_prints_the_success_token_its_halt_token_
# pairs_with` asserts that the token's SPELLING pairs with the halt prefix and that it
# carries a payload — never that the run it announces did anything. That is how
# `probe_subject` can print `PROBE_SUBJECT_OK {"json": ..., "n": len(records)}` and exit 0
# with `n` at whatever the loop produced, including zero.
#
# THE NODE: a success line whose payload carries a `len(X)` term. `X` is the thing the run
# produced, so the tool must REFUSE an empty `X` before it announces success — the same
# structural claim as "a writer verifies its own output", one level up.


def _counted_payload_terms(filename):
    """`{line: [names counted with len() in the `_OK` payload]}` for one tool."""
    tree = ast.parse(read_source(filename))
    out = {}
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") == "print"
                and node.args):
            continue
        try:
            rendered = ast.unparse(node)
        except Exception:                                               # noqa: BLE001
            continue
        if "_OK" not in rendered:
            continue
        counted = []
        for inner in ast.walk(node):
            if (isinstance(inner, ast.Call) and getattr(inner.func, "id", "") == "len"
                    and inner.args):
                try:
                    counted.append(ast.unparse(inner.args[0]))
                except Exception:                                       # noqa: BLE001
                    continue
        if counted:
            out[node.lineno] = sorted(set(counted))
    return out


#: Derived 2026-09-04: the Blender-side tools whose success payload reports a count.
RECORDED_COUNTING_SUCCESS_LINES = [
    # WAVE 14 (instruments, F-7e7703cb): `diagnose_bone_heat` JOINED. Its success line was
    # `print("DIAGNOSE_BONE_HEAT_OK " + path)` -- a bare path, so it counted nothing and was
    # outside this population; it now reports n_arms / n_arms_with_weight / best_arm from the
    # sweep's own records. Deliberately NO refusal on an all-zero sweep (an all-zero result is
    # a legitimate finding for a diagnostic), so it is exempt from the guard clause below for
    # that stated reason.
    "diagnose_bone_heat.py",
    # WAVE 34: `lift_solve` LEFT — retarget's success path no longer prints a `len(...)`
    # term in the `_OK` payload, so `_counted_payload_terms` does not reach it. Measured;
    # entry deleted, not commented.
    # WAVE 25 (instruments, F-f204a6d1): `make_skeleton_sheet` JOINED, for the reason
    # `diagnose_bone_heat` did in wave 14. Its success line was
    # `print("MAKE_SKELETON_SHEET_OK " + path)` -- a bare Windows path, the only `_OK`
    # payload in the 21 owned tools a JSON reader could not parse, and a token earned by
    # reaching the end of `main` rather than by a measurable effect. It now reports the
    # gate's own snap counts, the inset-joint count, the panel count and `len(table)` --
    # and `table` is the operand `gate_any_pivot_matched(table)` refuses over, above the
    # success line, which is what this census asks of a counting payload.
    "make_parts_sheet.py",
    "make_rig_sheet.py", "make_skeleton_sheet.py", "preview_walk.py",
    # WAVE-12 MERGE (coordinator, 2026-09-04): `probe_subject` LEFT — its payload is now
    # `{"n_probed","n_measured","n_errors","json"}` computed from a population guarded by
    # `require_openable` / `require_something_measured` (instruments F-5b3ead49), no longer a bare
    # `len()`; the census derives the counting population and no longer sees it.
    "rig_parts.py", "rig_repair.py",
]

#: Named, dated 2026-09-04, routed to INSTRUMENTS: `probe_subject` prints
#: `PROBE_SUBJECT_OK {"json": ..., "n": len(records)}` with nothing between the loop and the
#: print, so a run that opened nothing announces success. A CEILING — a tool that grows the
#: refusal leaves this set, and a NEW counting success line with no guard fails loudly.
# WAVE-12 MERGE (coordinator, 2026-09-04): EMPTY — the routed guard landed (F-5b3ead49).
COUNTED_SUCCESS_WITHOUT_A_GUARD_ROUTED = set()

#: Tools whose zero IS THE FINDING, so a refusal on it would delete the result the tool
#: exists to produce. Named and dated 2026-09-04 (wave 14, instruments, F-7e7703cb):
#: `diagnose_bone_heat` sweeps twelve binding arms to answer whether bone-heat binds this
#: subject at all, and a sweep in which every arm weighted zero vertices is the exact
#: condition it was written to investigate -- the tool is working correctly there.
#:
#: The exemption is checked against its REASON, not granted by name: the member's success
#: payload must carry an explicit boolean naming the zero case, so a reader (or a scripted
#: caller) can tell "the sweep found nothing" from "the harness failed" without opening the
#: JSON. A counting success line that does neither -- no guard AND no flag -- still fails.
COUNTED_SUCCESS_WHERE_ZERO_IS_THE_FINDING = {
    "diagnose_bone_heat.py": "all_arms_weighted_nothing",
}


def _guards_the_count(filename, counted):
    """True when some refusal ABOVE the success line mentions one of the counted names.

    Structural and deliberately loose: the claim is "something refuses on the emptiness of
    the thing being counted", not "it refuses in one particular spelling". A refusal is a
    `raise` of an `ArmatureError` subclass or a `gate_`/`require_` call, which is the
    behavioural predicate `tests/_census_nodes.py` derives.
    """
    import _census_nodes as CN

    tree = ast.parse(read_source(filename))
    names = {term.split("[", 1)[0].split(".", 1)[0] for term in counted}
    error_names = CN.armature_error_names()
    for fn in tree.body:
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for node in ast.walk(fn):
            refuses = (isinstance(node, ast.Raise) and node.exc is not None
                       and (getattr(getattr(node.exc, "func", node.exc), "id", "")
                            in error_names
                            or getattr(getattr(node.exc, "func", node.exc), "attr", "")
                            in error_names))
            calls_gate = (isinstance(node, ast.Call)
                          and CN.is_refusal_call(CN.called_name(node)))
            if not (refuses or calls_gate):
                continue
            try:
                rendered = ast.unparse(node)
            except Exception:                                           # noqa: BLE001
                continue
            if any(name and name in rendered for name in names):
                return True
    return False


def _count_is_structurally_nonzero(filename, counted):
    """True when a counted name is appended to UNCONDITIONALLY somewhere in a function.

    The second honest category, and it is not an exemption granted by hand: measured on
    `make_rig_sheet`, `rows` is `[]` followed by three `rows.append({...})` statements at the
    top level of `main`, none of them inside an `if`, a `for`, a `while` or a `try` — so
    `len(rows)` cannot be 0 and a guard against an empty one would be a check that cannot
    fire. `probe_subject`'s `records` is appended to INSIDE a loop, which is exactly why its
    count can be zero.
    """
    tree = ast.parse(read_source(filename))
    names = {term.split("[", 1)[0].split(".", 1)[0] for term in counted}

    def unconditional(body):
        for stmt in body:
            if isinstance(stmt, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try,
                                 ast.With, ast.AsyncWith)):
                continue
            for node in ast.walk(stmt):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr in ("append", "extend")
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id in names):
                    return True
        return False

    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) and unconditional(fn.body):
            return True
    return False


#: The loop-appended counter `probe_subject` used to be, kept runnable. WAVE 14, F-501e37b3:
#: instruments' F-5b3ead49 replaced that tool's bare `len(records)` payload with
#: `{"n_probed","n_measured","n_errors","json"}`, so `_counted_payload_terms('probe_subject')`
#: is now `[]` — and `_count_is_structurally_nonzero` with an EMPTY term list builds
#: `names = set()`, whose `node.func.value.id in names` test can never match, so it returned
#: False for every file in the tree. Measured: False for `make_rig_sheet.py` and
#: `rig_parts.py` too, and `make_rig_sheet.py` is the subject of the POSITIVE half two lines
#: above. The negative assertion passed for a reason that had nothing to do with `records`
#: being appended inside a loop.
LOOP_APPENDED_COUNTER = (
    "import json\n"
    "def main(argv=None):\n"
    "    records = []\n"
    "    for path in argv or []:\n"
    "        records.append(path)\n"
    "    print('FAKE_OK ' + json.dumps({'n': len(records)}))\n"
    "    return 0\n")


def test_the_structurally_nonzero_category_is_measured_and_not_asserted(monkeypatch):
    """Rule 3: the walk must tell the two shapes apart, on a NON-EMPTY term list.

    WAVE 14, F-501e37b3. Both halves are driven with terms the walk can actually look for,
    and the term list is asserted non-empty first — because an empty one makes the walk
    answer False about everything, which is how this test came to pass while demonstrating
    nothing. The negative half is the synthetic loop-appended module the sibling test at
    `test_the_counted_success_walk_can_tell_a_guarded_tool_from_an_unguarded_one` already
    builds (the population no longer contains a real one), fed through `read_source` the same
    way.
    """
    import test_instruments_amend_w10 as me

    def terms(f):
        return sorted({t for v in _counted_payload_terms(f).values() for t in v})

    positive = terms("make_rig_sheet.py")
    assert positive, (
        "`make_rig_sheet` reports no counted payload term; with an empty term list "
        "`_count_is_structurally_nonzero` answers False about every file and neither half "
        "below measures the walk")
    assert _count_is_structurally_nonzero("make_rig_sheet.py", positive), (
        "`rows` is appended to unconditionally three times; if this reads as conditional the "
        "category is measuring nothing")

    real = me.read_source
    monkeypatch.setattr(
        me, "read_source",
        lambda f: LOOP_APPENDED_COUNTER if f == "fake_counter.py" else real(f))
    negative = terms("fake_counter.py")
    assert negative == ["records"], negative
    assert not _count_is_structurally_nonzero("fake_counter.py", negative), (
        "`records` is appended to inside a loop and CAN be empty; the category must not "
        "absorb the site it exists to leave uncovered")

    # The two answers differ on the SAME non-empty shape of input, which is the whole claim.
    assert _count_is_structurally_nonzero("make_rig_sheet.py", positive) is not \
        _count_is_structurally_nonzero("fake_counter.py", negative)


def test_an_empty_term_list_makes_the_walk_answer_false_about_everything():
    """The defect F-501e37b3 named, kept runnable so it cannot come back unnoticed.

    `_count_is_structurally_nonzero(f, [])` builds `names = set()` and its
    `node.func.value.id in names` test can never match. Any future caller that passes the
    empty list is asserting nothing, and the assertion above is the guard against it.
    """
    for filename in ("make_rig_sheet.py", "rig_parts.py"):
        assert _count_is_structurally_nonzero(filename, []) is False, filename


def test_the_counting_success_population_is_the_one_measured_today():
    derived = sorted(f for f in BLENDER_TOOLS if _counted_payload_terms(f))
    assert derived == RECORDED_COUNTING_SUCCESS_LINES, {
        "appeared": sorted(set(derived) - set(RECORDED_COUNTING_SUCCESS_LINES)),
        "vanished": sorted(set(RECORDED_COUNTING_SUCCESS_LINES) - set(derived))}
    assert COUNTED_SUCCESS_WITHOUT_A_GUARD_ROUTED <= set(derived), sorted(
        COUNTED_SUCCESS_WITHOUT_A_GUARD_ROUTED - set(derived))


@pytest.mark.parametrize("filename", RECORDED_COUNTING_SUCCESS_LINES)
def test_a_success_line_that_reports_a_count_is_guarded_against_an_empty_one(filename):
    """Rule 4: `<PREFIX>_OK` prints only after the tool's own record shows it did the thing.

    A payload that says `"n": len(records)` is the tool telling its caller how much work it
    did; `0` is a run that did none, announced as a success.
    """
    counted = _counted_payload_terms(filename)
    assert counted, filename
    terms = sorted({t for v in counted.values() for t in v})
    if _count_is_structurally_nonzero(filename, terms):
        pytest.skip(
            f"{filename}'s counted {terms} is appended to unconditionally, so `len()` "
            f"cannot be 0 and a guard against an empty one would be a check that cannot "
            f"fire. Measured by `_count_is_structurally_nonzero`, not granted by hand.")
    guarded = _guards_the_count(filename, terms)
    flag = COUNTED_SUCCESS_WHERE_ZERO_IS_THE_FINDING.get(filename)
    if flag is not None:
        # THE REASON, checked. The exemption holds only while the payload actually carries
        # the boolean that separates "found nothing" from "did nothing".
        import ast as _ast

        from blender_stub import read_source as _read

        tree = _ast.parse(_read(filename))
        printed = [_ast.unparse(n) for n in _ast.walk(tree)
                   if isinstance(n, _ast.Call) and getattr(n.func, "id", "") == "print"
                   and "_OK" in _ast.unparse(n)]
        assert any(flag in t for t in printed), (
            f"{filename} is exempt because its zero is a finding, and the exemption "
            f"requires the success line to carry {flag!r} so the two cases read "
            f"differently. It does not.")
        return
    if not guarded and filename in COUNTED_SUCCESS_WITHOUT_A_GUARD_ROUTED:
        pytest.skip(
            f"{filename} prints a success line reporting {terms} and no refusal in the "
            f"module mentions any of them, so a run that produced nothing announces "
            f"success. Routed 2026-09-04 (F-b777d4a3) to instruments — `probe_subject` "
            f"refuses an empty population before `PROBE_SUBJECT_OK`; this direction runs "
            f"against this tool the moment that lands.")
    assert guarded, (
        f"{filename}'s success payload reports {terms} and nothing refuses an empty one; "
        f"the token says the run succeeded and the count says it did nothing")


def test_the_counted_success_walk_can_tell_a_guarded_tool_from_an_unguarded_one(monkeypatch):
    """Rule 3 on the walk itself: the two answers must differ.

    WAVE-12 MERGE (coordinator, 2026-09-04): `probe_subject` was the real unguarded example until
    instruments landed its guard (F-5b3ead49), so the unguarded half is now a SYNTHETIC
    module — a count appended inside a loop and printed with no refusal above it — fed to
    the walk through `read_source`, exactly the shape the routed finding described.
    """
    import test_instruments_amend_w10 as me

    # WAVE 14, F-501e37b3: ONE copy of the synthetic module, shared with
    # `test_the_structurally_nonzero_category_is_measured_and_not_asserted`, which needs the
    # same shape now that the real tree carries no loop-appended counter. Two copies of one
    # fixture fork the same way two copies of one walk do.
    fake = LOOP_APPENDED_COUNTER
    real = me.read_source
    monkeypatch.setattr(me, "read_source", lambda f: fake if f == "fake_counter.py" else real(f))
    assert me._guards_the_count("fake_counter.py", ["records"]) is False
    guarded = {f: me._guards_the_count(f, sorted(
        {t for v in me._counted_payload_terms(f).values() for t in v}))
        for f in me.RECORDED_COUNTING_SUCCESS_LINES}
    assert any(guarded.values()), guarded


def _writes_nothing():
    """A `bpy.ops.render.render` that returns `{'CANCELLED'}` and writes no file — the
    operator behaviour the four tools discarded."""
    return {"CANCELLED"}


@pytest.mark.parametrize("filename,gate_name", [
    ("make_skeleton_sheet.py", "SkeletonSheetGate"),
    ("make_binding_sheet.py", "BindingSheetGate"),
    ("make_parts_sheet.py", "PartsSheetGate"),
])
def test_a_sheet_shoot_that_wrote_no_file_raises_its_own_gate(filename, gate_name, tmp_path):
    """WAVE 14, F-6a9a0f72: a `{'CANCELLED'}` return is now refused by the STATUS clause,
    which runs before the file clauses -- it is the only one of the three that can tell a
    declined render from a stale file at the same path. The file clause is exercised
    separately below, on a FINISHED render that wrote nothing."""
    mod = load_tool(filename)
    gate = getattr(mod, gate_name)
    mod.bpy.ops.render.render.side_effect = lambda **kw: _writes_nothing()
    path = str(tmp_path / "panel.png")
    args = (mod.bpy.context.scene, path)
    if filename == "make_skeleton_sheet.py":
        args = args + (False,)
    with pytest.raises(gate) as caught:
        mod.shoot(*args)
    assert caught.value.evidence["path"] == os.path.abspath(path)
    assert caught.value.evidence["clause"] == "operator_status"
    assert caught.value.evidence["status"] == ["CANCELLED"]


@pytest.mark.parametrize("filename,gate_name", [
    ("make_skeleton_sheet.py", "SkeletonSheetGate"),
    ("make_binding_sheet.py", "BindingSheetGate"),
    ("make_parts_sheet.py", "PartsSheetGate"),
])
def test_a_sheet_shoot_that_reported_finished_and_wrote_nothing_still_raises(
        filename, gate_name, tmp_path):
    """The F-51c5e0ef clause, kept reachable behind the new status clause."""
    mod = load_tool(filename)
    gate = getattr(mod, gate_name)
    mod.bpy.ops.render.render.side_effect = lambda **kw: {"FINISHED"}
    path = str(tmp_path / "panel.png")
    args = (mod.bpy.context.scene, path)
    if filename == "make_skeleton_sheet.py":
        args = args + (False,)
    with pytest.raises(gate) as caught:
        mod.shoot(*args)
    assert caught.value.evidence["path"] == os.path.abspath(path)
    assert caught.value.evidence["exists"] is False


@pytest.mark.parametrize("filename,gate_name", [
    ("make_skeleton_sheet.py", "SkeletonSheetGate"),
    ("make_binding_sheet.py", "BindingSheetGate"),
    ("make_parts_sheet.py", "PartsSheetGate"),
])
def test_a_sheet_shoot_that_wrote_a_zero_byte_file_raises_too(filename, gate_name,
                                                              tmp_path):
    """A cancelled render can also leave the empty file Blender opened."""
    mod = load_tool(filename)
    gate = getattr(mod, gate_name)
    path = str(tmp_path / "panel.png")
    def _empty_file(**kw):
        open(path, "wb").close()
        return {"FINISHED"}                 # WAVE 14: past the status clause, into the size one

    mod.bpy.ops.render.render.side_effect = _empty_file
    args = (mod.bpy.context.scene, path)
    if filename == "make_skeleton_sheet.py":
        args = args + (False,)
    with pytest.raises(gate, match="zero bytes"):
        mod.shoot(*args)


@pytest.mark.parametrize("filename", ["make_skeleton_sheet.py", "make_binding_sheet.py",
                                      "make_parts_sheet.py"])
def test_a_sheet_shoot_that_wrote_a_real_file_returns_its_path(filename, tmp_path):
    """The other direction: the gate may not fire on the happy path."""
    mod = load_tool(filename)
    path = str(tmp_path / "panel.png")
    def _real_file(**kw):
        open(path, "wb").write(b"PNG")
        return {"FINISHED"}

    mod.bpy.ops.render.render.side_effect = _real_file
    args = (mod.bpy.context.scene, path)
    if filename == "make_skeleton_sheet.py":
        args = args + (False,)
    assert mod.shoot(*args) == path


def test_make_rig_sheet_renders_through_the_sibling_it_imports():
    """The family carry, pinned: `make_rig_sheet` has no render call of its own and must not
    grow one — it renders through `make_parts_sheet.shoot`, so one fix covers both."""
    assert _render_call_sites("make_rig_sheet.py") == []
    rig, parts = load_tool("make_rig_sheet.py"), load_tool("make_parts_sheet.py")
    assert rig.shoot.__name__ == parts.shoot.__name__ == "shoot"
    assert rig.shoot.__module__.endswith("make_parts_sheet"), rig.shoot.__module__


def test_preview_glb_refuses_when_a_planned_view_never_reached_disk(tmp_path):
    """F-13bd448d. `add_camera_render` discarded the operator's status and nothing
    afterwards read the four paths back: `<name>_stats.json` is written from measurements
    taken off the scene, and `PREVIEW_GLB_OK` printed, over a directory that may be empty.
    """
    mod = load_tool("preview_glb.py")
    good = tmp_path / "a.png"
    good.write_bytes(b"PNG")
    empty = tmp_path / "b.png"
    empty.write_bytes(b"")
    missing = tmp_path / "c.png"
    with pytest.raises(mod.PreviewGlbGate) as caught:
        # WAVE 14, F-6a9a0f72: the gate takes `(path, status)` pairs, because the
        # operator's status set is the only clause that tells an empty directory from a
        # stale one. A FINISHED status is passed here so the file clauses are what fires.
        # RE-DERIVED wave 22 (instruments, F-a2630f86): a TRIPLE. The third element is
        # `rig_character.render_target_snapshot(path)` taken ABOVE the render, and the
        # gate's fourth clause -- "the operator said FINISHED and the bytes did not
        # move" -- cannot exist without it. `{"existed": False}` here is the honest
        # snapshot for a path nothing had written before the render.
        mod.gate_previews_written(
            [(str(good), ["FINISHED"], {"existed": False}),
             (str(empty), ["FINISHED"], {"existed": False}),
             (str(missing), ["FINISHED"], {"existed": False})])
    ev = caught.value.evidence
    assert [os.path.basename(p) for p in ev["missing"]] == ["c.png"], ev
    assert [os.path.basename(p) for p in ev["empty"]] == ["b.png"], ev
    assert ev["planned"] == 3, ev


def test_preview_glb_is_satisfied_by_four_real_files(tmp_path):
    mod = load_tool("preview_glb.py")
    paths = []
    for name in ("full_a", "full_b", "head_a", "head_b"):
        p = tmp_path / (name + ".png")
        p.write_bytes(b"PNG")
        # RE-DERIVED wave 22 (instruments, F-a2630f86): a TRIPLE, and the snapshot is
        # the honest one -- these four files are written by the test a moment before,
        # so nothing was at the path when the "render" began.
        paths.append((str(p), ["FINISHED"], {"existed": False}))
    assert mod.gate_previews_written(paths)["planned"] == 4


def test_preview_glb_main_gates_the_paths_its_renders_returned():
    """The wiring, not just the helper: `add_camera_render` must RETURN the path it wrote,
    and `main` must hand the collected list to the gate — a gate nothing calls is not a
    gate, which is the class this repo has shipped four times."""
    src = read_source("preview_glb.py")
    tree = ast.parse(src)
    fns = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    returns = [ast.unparse(n.value) for n in ast.walk(fns["add_camera_render"])
               if isinstance(n, ast.Return) and n.value is not None]
    assert returns, "add_camera_render returns nothing, so the plan cannot be the list " \
                    "the render wrote against"
    called = [ast.unparse(n.func) for n in ast.walk(fns["main"]) if isinstance(n, ast.Call)]
    assert "gate_previews_written" in called


# --------------------------------------------------------------------------------------
# F-d47095fa -- a refused run leaves no empty output directory behind (the bpy half)
# --------------------------------------------------------------------------------------
#
# `tests/test_instrument_write_ordering.py` states its bpy exemption as "the tool writes the
# artefact that its later gates then measure, so the directory must exist before the gate
# can run" and implements it as `imports_bpy(name)` -- a PROXY, and broader than the reason.
# Measured 2026-09-04 by pairing each tool's first `os.makedirs` in `main()` against the
# first call that actually produces BYTES: thirteen named refusals sit between the two
# across four of the exempted tools, and not one of them needs the directory.
#
# The census below keys on the REASON instead: the node is the first byte-producing call,
# and a refusal is stranded only if it sits strictly between the directory's creation and
# that call. A tool whose gates genuinely measure what it wrote has no refusal in that
# window and passes without being exempted at all.

#: Calls that put bytes on disk. Named rather than inferred (this walk is blind to any
#: writer it cannot name), and extended one level: a call to a function DEFINED in the same
#: module whose own body writes counts as a write at the call site -- which is how the sheet
#: tools write, through `shoot()`, and `preview_glb` through `add_camera_render()`.
BYTE_PRODUCING_CALLS = (
    "bpy.ops.export_scene.gltf", "bpy.ops.render.render", "bpy.ops.wm.save_as_mainfile",
    "json.dump", "pngio.write_png", "np.save", "shutil.copy", "shutil.copyfile",
)


def _is_byte_producer(node):
    if not isinstance(node, ast.Call):
        return False
    called = ast.unparse(node.func)
    if called in BYTE_PRODUCING_CALLS:
        return True
    if (called == "open" and len(node.args) > 1
            and isinstance(node.args[1], ast.Constant)
            and "w" in str(node.args[1].value)):
        return True
    return (isinstance(node.func, ast.Attribute)
            and node.func.attr in ("write", "writelines", "savefig", "save"))


def write_window(filename):
    """`(first_makedirs_line, first_byte_line)` in the tool's module-level `main()`."""
    src = read_source(filename)
    tree = ast.parse(src)
    module_fns = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    writers = {name for name, node in module_fns.items()
               if any(_is_byte_producer(x) for x in ast.walk(node))}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "") == "make_parts_sheet":
            writers.update(a.asname or a.name for a in node.names)
    main = module_fns.get("main")
    if main is None:
        return None, None
    byte_lines, dir_lines = [], []
    for node in ast.walk(main):
        if _is_byte_producer(node):
            byte_lines.append(node.lineno)
        elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
              and node.func.id in writers and node.func.id != "main"):
            byte_lines.append(node.lineno)
        if isinstance(node, ast.Call) and ast.unparse(node.func) == "os.makedirs":
            dir_lines.append(node.lineno)
    return (min(dir_lines) if dir_lines else None,
            min(byte_lines) if byte_lines else None)


def stranded_refusals(filename):
    """Refusal lines that sit between the output directory's creation and the first byte.

    The refusal population is the sibling census's own `gate_and_write_lines` -- carried,
    not reimplemented, so the two files cannot disagree about what a refusal is.

    WAVE 12, F-183635ad: carrying the sibling's walk was right and the walk was blind.
    It recognised a refusal only by CALLEE NAME, and this file's own docstring said the
    import existed "so the two files cannot disagree about what a refusal is" -- which made
    both files agree on a predicate that cannot see an INLINE `raise`. Measured: this
    function returned `[]` for every tool, while eleven of the 21 strand a refusal between
    their `makedirs` and their first byte. `make_rig_sheet` is the instruments auditor's
    example and it holds exactly: `<out>/` at :95, `<out>/panels/` at :97, then
    `raise ArmatureError` inline at :112, :119 and :139.
    """
    import test_instrument_write_ordering as WO

    makedirs, first_byte = write_window(filename)
    if makedirs is None or first_byte is None:
        return []
    gates, _writes = WO.gate_and_write_lines(read_source(filename), filename[:-3])
    return sorted(line for line in gates if makedirs < line < first_byte)


def stranded_refusal_names(filename):
    """The same sites, as NAMES.

    Keyed on names, not line numbers, for the ratchet below: a line number moves under any
    edit above it, which is how 23 of 31 entries in `test_gates`'s evidence ratchet came to
    name nothing (F-a30afea5).
    """
    import test_instrument_write_ordering as WO

    makedirs, first_byte = write_window(filename)
    if makedirs is None or first_byte is None:
        return []
    gates, _writes = WO.gate_and_write_lines(read_source(filename), filename[:-3])
    return sorted({gates[line] for line in gates if makedirs < line < first_byte})


#: Derived 2026-09-04: every Blender tool whose `main()` both creates its output directory
#: and writes bytes. Equality, so a tool that starts doing both joins this census loudly.
RECORDED_DIR_AND_WRITE = [
    "author_walk.py", "check_relift.py", "diagnose_bone_heat.py", "lift_solve.py",
    "make_binding_sheet.py", "make_parts_sheet.py", "make_rig_sheet.py",
    "make_skeleton_sheet.py", "make_test_armature.py", "preview_glb.py", "preview_walk.py",
    "probe_glb.py", "probe_subject.py", "render_performer.py", "render_start_frame.py",
    "render_turnaround.py", "rig_bake.py", "rig_character.py", "rig_parts.py",
    "rig_repair.py", "rig_retopo.py",
]


def test_the_write_ordering_population_is_derived_and_is_the_one_recorded():
    derived = sorted(f for f in BLENDER_TOOLS if all(write_window(f)))
    assert derived == RECORDED_DIR_AND_WRITE, {
        "appeared": sorted(set(derived) - set(RECORDED_DIR_AND_WRITE)),
        "vanished": sorted(set(RECORDED_DIR_AND_WRITE) - set(derived))}


#: MEASURED 2026-09-04 under the BEHAVIOURAL refusal predicate (wave 12, F-183635ad):
#: eleven of the 21 strand a refusal between `makedirs` and the first byte, 22 distinct
#: refusal names in all. Not one of them was visible while the predicate keyed on the callee
#: name, so this whole table is a measurement of the old blindness rather than of new code.
#:
#: The moves are INSTRUMENTS' (the wave-12 brief routes "the 18 stranded refusals moved
#: above the first write" there); this file's half is the census that makes them visible and
#: the ratchet that stops a new one arriving. The set may not GROW; it is expected to shrink
#: as the moves land, and an entry closed by a move is deleted by the commit that moves it.
STRANDED_BETWEEN_DIR_AND_BYTE = {
    "diagnose_bone_heat.py": ["load"],
    "make_binding_sheet.py": ["render_arm"],
    "make_parts_sheet.py": ["articulated_side", "light_the_scene", "raise ArmatureError"],
    "make_rig_sheet.py": ["raise ArmatureError"],
    "make_skeleton_sheet.py": ["light_the_scene", "raise SkeletonSheetGate"],
    "make_test_armature.py": ["build"],
    "render_turnaround.py": ["solve_ortho_scale_for_height", "solve_radius_for_height"],
    "rig_bake.py": ["_import", "bake", "raise BakeEmpty", "unwrap"],
    "rig_character.py": ["build_pass"],
    "rig_repair.py": ["raise ArmatureError", "raise NotManifoldAfterRepair",
                      "raise TooMuchRemoved"],
    "rig_retopo.py": ["import_subject", "quadriflow", "raise NoRetopoProduced"],
}


def test_the_stranded_ratchet_names_real_members_and_may_not_grow():
    """Size and membership before the property, in the direction that protects it."""
    assert set(STRANDED_BETWEEN_DIR_AND_BYTE) <= set(RECORDED_DIR_AND_WRITE), sorted(
        set(STRANDED_BETWEEN_DIR_AND_BYTE) - set(RECORDED_DIR_AND_WRITE))
    derived = {f: stranded_refusal_names(f) for f in RECORDED_DIR_AND_WRITE}
    derived = {f: v for f, v in derived.items() if v}
    grew = {f: sorted(set(v) - set(STRANDED_BETWEEN_DIR_AND_BYTE.get(f, [])))
            for f, v in derived.items()
            if set(v) - set(STRANDED_BETWEEN_DIR_AND_BYTE.get(f, []))}
    assert grew == {}, {"new refusals between the directory and the first byte": grew}
    assert sum(len(v) for v in derived.values()) <= 22, sorted(derived.items())


@pytest.mark.parametrize("filename", RECORDED_DIR_AND_WRITE)
def test_no_refusal_sits_between_the_output_directory_and_the_first_byte(filename):
    """MEASURED 2026-09-04, thirteen stranded refusals across four tools:
    lift_solve (makedirs 295, first byte 325; 307, 310, 315),
    author_walk (542 / 597; 552, 555, 576, 580, 586),
    rig_parts (480 / 512; 490, 492, 499, 503),
    render_start_frame (459 / 532; 472).

    A run refused by one of those leaves an empty output directory behind, which a reader
    scanning `outputs/` -- or a re-run into the same `--out` -- reads as an attempt that
    produced nothing rather than one that was refused."""
    if filename in STRANDED_BETWEEN_DIR_AND_BYTE:
        pytest.skip(
            f"its stranded refusals are named individually in "
            f"STRANDED_BETWEEN_DIR_AND_BYTE and ratcheted there "
            f"({STRANDED_BETWEEN_DIR_AND_BYTE[filename]}); the moves are instruments' "
            f"(wave 12, F-183635ad) and this module-level assertion would say nothing the "
            f"ratchet does not")
    stranded = stranded_refusals(filename)
    makedirs, first_byte = write_window(filename)
    assert stranded == [], (
        f"{filename}: makedirs at {makedirs}, first byte at {first_byte}, and refusals at "
        f"{stranded} in between — none of them needs the directory")


def test_the_stranding_census_goes_red_on_a_member_with_the_defect(tmp_path, monkeypatch):
    """Rule 3: prove it can fail, on a member added to the walked tree."""
    probe = tmp_path / "probe_order.py"
    probe.write_text(
        "import bpy\n"
        "import json\n"
        "import os\n"
        "def main():\n"
        "    os.makedirs(out, exist_ok=True)\n"
        "    gate_something(x)\n"
        "    with open(path, 'w') as fh:\n"
        "        json.dump({}, fh)\n", encoding="utf-8")
    import blender_stub
    monkeypatch.setattr(blender_stub, "TOOLS", str(tmp_path))
    assert write_window("probe_order.py") == (5, 7)
    assert stranded_refusals("probe_order.py") == [6]


# --------------------------------------------------------------------------------------
# F-6ee68fc0 -- the stale-pin instrument samples a window derived from the assets
# --------------------------------------------------------------------------------------
#
# `--frames` defaulted to the literal 65 and `main` passed that same number to BOTH
# `signatures` calls, which built their lists with `for i in range(frames)`. So
# `len(pinned_sigs) == len(fresh_sigs) == a.frames` for every input pair that exists, and
# `armature_core.glb.compare_signatures`' opening clause -- "frame counts differ ... A lift
# that dropped or gained a frame is not the same performance however well the frames it
# kept agree" -- was structurally unreachable from its ONLY production caller.
# `tests/test_check_relift.py:44-51` exercised it synthetically, so the suite was green over
# a clause no run could reach.


def _relift():
    return load_tool("check_relift.py")


def test_the_window_is_measured_off_the_asset_not_off_the_flag():
    mod = _relift()
    w = mod.keyed_window("a.glb", (1.0, 65.0), 65)
    assert w["keyed_frames"] == 65 and w["sampled"] == 65
    short = mod.keyed_window("b.glb", (1.0, 40.0), 65)
    assert short["keyed_frames"] == 40, short
    assert short["sampled"] == 40, "a request may not sample past the last key"
    assert mod.keyed_window("c.glb", None, 65)["keyed_frames"] == 0


def test_two_glbs_that_key_different_windows_refuse():
    """The dropped-frame case, in the tool that exists to notice it. A re-solve producing
    40 frames against a 65-frame pin used to be compared as 65-vs-65 with frames 40..64
    held at the last key on BOTH sides — and if the shared 40 agreed the record said
    `n_frames_compared: 65`, `n_frames_differing: 0`, "all 65 frames identical"."""
    mod = _relift()
    pinned = mod.keyed_window("pinned.glb", (1.0, 65.0), 40)
    fresh = mod.keyed_window("fresh.glb", (1.0, 40.0), 40)
    with pytest.raises(mod.ReliftWindow) as caught:
        mod.gate_relift_window(pinned, fresh, 40)
    assert caught.value.evidence["clause"] == "ranges_differ"
    assert caught.value.gate == "RELIFT"


def test_a_request_that_overruns_the_performance_refuses():
    """The second half, recorded in this repo by a sibling instrument:
    `render_start_frame.action_frame_range`'s docstring states that `frame_set` past the end
    of an action "holds the last pose and renders it without complaint", and
    render_start_frame refuses on exactly that. check_relift performed no such check."""
    mod = _relift()
    w = mod.keyed_window("x.glb", (1.0, 40.0), 65)
    with pytest.raises(mod.ReliftWindow) as caught:
        mod.gate_relift_window(w, dict(w, glb="y.glb"), 65)
    ev = caught.value.evidence
    assert ev["clause"] == "request_overruns_the_performance"
    assert ev["shared_keyed_frames"] == 40 and ev["requested_frames"] == 65


def test_a_pair_with_no_keyed_action_refuses_rather_than_agreeing_about_a_still():
    mod = _relift()
    w = mod.keyed_window("x.glb", None, 8)
    with pytest.raises(mod.ReliftWindow) as caught:
        mod.gate_relift_window(w, dict(w, glb="y.glb"), 8)
    assert caught.value.evidence["clause"] == "no_keyed_action"


def test_the_window_gate_passes_a_legal_request_and_records_both_ranges():
    """The other direction — a gate that cannot pass is not a gate either."""
    mod = _relift()
    a = mod.keyed_window("pinned.glb", (1.0, 65.0), 65)
    b = mod.keyed_window("fresh.glb", (1.0, 65.0), 65)
    ev = mod.gate_relift_window(a, b, 65)
    assert ev["clause"] is None and ev["shared_keyed_frames"] == 65
    assert ev["pinned"]["action_frame_range"] == [1.0, 65.0]
    assert ev["fresh"]["action_frame_range"] == [1.0, 65.0]


def test_the_window_gate_is_reached_from_mains_own_path(tmp_path, monkeypatch, capsys):
    """Not only from a hand-built pair: `main` must call it, on the real argv path, before
    any verdict is computed. A gate nothing calls is not a gate."""
    import sys as _sys

    pinned = tmp_path / "pinned.glb"
    pinned.write_bytes(b"glTF-pinned")
    fresh = tmp_path / "fresh.glb"
    fresh.write_bytes(b"glTF-fresh")
    out = tmp_path / "rec.json"
    argv = ["blender", "-b", "-P", "check_relift.py", "--",
            f"--pinned={pinned}", f"--fresh={fresh}", f"--out={out}", "--frames=40"]
    mod = load_tool("check_relift.py", argv=argv)

    def fake_signatures(glb, frames, fps):
        span = (1.0, 65.0) if glb == str(pinned) else (1.0, 40.0)
        window = mod.keyed_window(glb, span, frames)
        return [("sig", i) for i in range(window["sampled"])], window

    monkeypatch.setattr(mod, "signatures", fake_signatures)
    saved = list(_sys.argv)
    try:
        _sys.argv = list(argv)
        with pytest.raises(mod.ReliftWindow) as caught:
            mod.main()
    finally:
        _sys.argv = saved
    assert caught.value.evidence["clause"] == "ranges_differ"
    assert not out.exists(), "a refused comparison may not leave a record behind"


def test_a_legal_run_records_the_window_beside_the_verdict(tmp_path, monkeypatch):
    """The record says what was compared and over what — `gate_RELIFT.window`."""
    import sys as _sys

    pinned = tmp_path / "pinned.glb"
    pinned.write_bytes(b"glTF-pinned")
    fresh = tmp_path / "fresh.glb"
    fresh.write_bytes(b"glTF-pinned")
    out = tmp_path / "rec.json"
    argv = ["blender", "-b", "-P", "check_relift.py", "--",
            f"--pinned={pinned}", f"--fresh={fresh}", f"--out={out}", "--frames=40"]
    mod = load_tool("check_relift.py", argv=argv)

    def fake_signatures(glb, frames, fps):
        window = mod.keyed_window(glb, (1.0, 40.0), frames)
        return [("sig", i) for i in range(window["sampled"])], window

    monkeypatch.setattr(mod, "signatures", fake_signatures)
    monkeypatch.setattr(mod.blender_scene, "blender_provenance",
                        lambda: {"version": "stub"})
    saved = list(_sys.argv)
    try:
        _sys.argv = list(argv)
        assert mod.main() == 0
    finally:
        _sys.argv = saved
    rec = json.loads(out.read_text(encoding="utf-8"))
    assert rec["gate_RELIFT"]["window"]["shared_keyed_frames"] == 40
    assert rec["gate_RELIFT"]["window"]["pinned"]["action_frame_range"] == [1.0, 40.0]
    assert rec["gate_RELIFT"]["n_frames_compared"] == 40


def test_check_relift_carries_the_siblings_frame_range_reader_rather_than_a_second_copy():
    """family: the keyed-span reader exists once, in `render_start_frame`, and is imported
    — the same idiom as `make_rig_sheet` importing `make_parts_sheet.shoot`."""
    src = read_source("check_relift.py")
    assert "from render_start_frame import action_frame_range" in src
    assert "def action_frame_range" not in src, "a second implementation, not a carry"


# --------------------------------------------------------------------------------------
# F-328aaea2 -- the naive measurement is called by its own name
# --------------------------------------------------------------------------------------
#
# `probe_subject` reported its deliberately-naive row with the SAME call as its filtered
# row -- `blender_scene.world_bounds(visible)` at one line and
# `blender_scene.world_bounds(meshes)` at another -- so the two were distinguishable only
# by which list was passed. `blender_scene.unfiltered_world_bounds` exists for this row and
# names `probe_subject` in its own docstring, but its only caller was
# `tests/blender/check_visibility.py`, a rig-only script. A later sweep giving
# `world_bounds` its scene at every call site would have turned the naive line into a second
# copy of the filtered one, and the record would have kept publishing a field labelled
# `naive_type_mesh_selection` whose numbers are the filtered ones.


def unfiltered_world_bounds_calls(filename):
    """`world_bounds(...)` calls with no `scene=` keyword — the naive measurement's shape.

    Keyed on the CALL and its keywords, not on a spelling: `world_bounds` filters by render
    visibility when it is given the scene and does not when it is not, so `scene=` is the
    node the property lives on. `unfiltered_world_bounds` is the sanctioned public name for
    a row that must NOT be filtered and is therefore not counted here.
    """
    tree = ast.parse(read_source(filename))
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        called = ast.unparse(node.func)
        if called.rsplit(".", 1)[-1] != "world_bounds":
            continue
        if any(k.arg == "scene" for k in node.keywords):
            continue
        if len(node.args) >= 2:            # positional scene
            continue
        out.append((node.lineno, ast.unparse(node)))
    return out


#: The two case/visibility sites that are NOT in this domain's globs, measured 2026-09-04
#: and named rather than silently excluded: `tools/stage_render.py:155`
#: (`bs.world_bounds(meshes)`, scene omitted) is filed in this wave's `skipped[]`.
OUT_OF_DOMAIN_WORLD_BOUNDS = ("stage_render.py",)


@pytest.mark.parametrize("filename", BLENDER_TOOLS)
def test_no_blender_tool_measures_through_the_unfiltered_shape_of_world_bounds(filename):
    naive = unfiltered_world_bounds_calls(filename)
    assert naive == [], (
        f"{filename}: {naive} calls `world_bounds` with `scene` omitted, which is the "
        f"NAIVE measurement. Pass `scene=` where the row should be filtered, or call "
        f"`blender_scene.unfiltered_world_bounds` where it deliberately should not")


def test_probe_subject_reports_the_naive_row_by_its_public_name():
    src = read_source("probe_subject.py")
    assert "blender_scene.unfiltered_world_bounds(meshes)" in src
    assert "blender_scene.world_bounds(visible, scene=scene)" in src


@pytest.mark.parametrize("filename", BLENDER_TOOLS)
def test_no_blender_tool_defines_its_own_world_bounds(filename):
    """`make_parts_sheet` defined `world_bounds(objs)` returning (lo, hi) corners over
    UNEVALUATED vertices, shadowing the module function that returns a
    (center, half_extent, radius) triple over evaluated geometry and filters when given the
    scene. Two different measurements under one name is how a visibility obligation gets
    lost; it is `corner_bounds` now."""
    tree = ast.parse(read_source(filename))
    shadows = [n.lineno for n in tree.body
               if isinstance(n, ast.FunctionDef) and n.name == "world_bounds"]
    assert shadows == [], f"{filename}:{shadows} shadows blender_scene.world_bounds"


def test_the_world_bounds_census_goes_red_on_a_member_with_the_naive_shape(tmp_path,
                                                                          monkeypatch):
    probe = tmp_path / "probe_bounds.py"
    probe.write_text(
        "from armature_core import blender_scene\n"
        "def run(scene, meshes):\n"
        "    return blender_scene.world_bounds(meshes)\n", encoding="utf-8")
    import blender_stub
    monkeypatch.setattr(blender_stub, "TOOLS", str(tmp_path))
    assert unfiltered_world_bounds_calls("probe_bounds.py") == [
        (3, "blender_scene.world_bounds(meshes)")]


# --------------------------------------------------------------------------------------
# F-ffdb6d4d -- the two renderers report the same population for the same directory
# --------------------------------------------------------------------------------------
#
# `render_performer.py:359` built its stray list with a case-SENSITIVE `.endswith(".png")`
# while `preview_walk.py:201` took the whole listing with no suffix filter at all, and the
# consumers that list frames downstream (`encode_control.py::frame_population`, `invert_frames.py:70`)
# match case-INSENSITIVELY. A frame arriving as `.PNG` was therefore absent from
# `render_performer`'s `unexpected_files_in_out_dir` -- the record said nothing unexpected
# was in the directory -- while a consumer picked it up and encoded it into the clip.


def case_sensitive_png_tests(filename):
    """`x.endswith(".png")` sites whose receiver is not lower-cased first."""
    tree = ast.parse(read_source(filename))
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "endswith" and node.args):
            continue
        arg = node.args[0]
        if not (isinstance(arg, ast.Constant) and isinstance(arg.value, str)
                and arg.value.lower().endswith(".png")):
            continue
        receiver = ast.unparse(node.func.value)
        if not receiver.endswith(".lower()"):
            out.append((node.lineno, ast.unparse(node)))
    return out


#: The two `.png` sites outside this domain's globs, measured 2026-09-04 and named rather
#: than silently excluded: `tools/render_pose_sticks.py::_written_frames` (instruments-measure, Gate
#: COUNT) and `tools/armature_core/donor_gate.py::frame_paths` (core-gates, `frame_paths`). Both are
#: being aligned in the same wave; this domain's half is the two renderers below.
OUT_OF_DOMAIN_PNG_SITES = ("render_pose_sticks.py", "armature_core/donor_gate.py")


@pytest.mark.parametrize("filename", BLENDER_TOOLS)
def test_every_png_population_in_this_domain_is_taken_case_insensitively(filename):
    bad = case_sensitive_png_tests(filename)
    assert bad == [], (
        f"{filename}: {bad} match `.png` case-sensitively while the consumers that list "
        f"frames downstream do not, so the two sides can disagree about one directory")


def test_the_two_renderers_derive_the_same_stray_population():
    """The pair, stated as the property rather than as two separate spellings."""
    for filename in ("render_performer.py", "preview_walk.py"):
        src = read_source(filename)
        assert 'f.lower().endswith(".png")' in src, filename
        assert "unexpected_files_rule" in src, (
            f"{filename} records a stray list without saying how its population is derived")


def test_a_stray_png_with_an_upper_case_extension_is_named_by_render_performer(tmp_path):
    """Behavioural, on the expression the tool actually evaluates: a directory holding
    `STRAY.PNG` beside the planned frames must have it named."""
    out = tmp_path
    for name in ("00000.png", "00001.png", "empty_plate.png", "STRAY.PNG", "notes.txt"):
        (out / name).write_bytes(b"PNG")
    planned_names = {"00000.png", "00001.png"}
    strays = sorted(f for f in os.listdir(out)
                    if f.lower().endswith(".png") and f not in planned_names
                    and f != "empty_plate.png")
    assert strays == ["STRAY.PNG"], strays
    old = sorted(f for f in os.listdir(out)
                 if f.endswith(".png") and f not in planned_names
                 and f != "empty_plate.png")
    assert old == [], "the superseded case-sensitive test could not see it"


# --------------------------------------------------------------------------------------
# F-ce3a471d -- the three-outcome vocabulary is spelled the same way in all 21 copies
# --------------------------------------------------------------------------------------
#
# Normalising every `if __name__ == "__main__":` body by AST and hashing gave FIVE distinct
# shapes on 2026-09-04, with no behavioural drift: 63 runs through
# `blender_stub.exit_code_of_main_block` (21 handlers x the gate / refusal / crash raisers,
# and again with an `--out` whose parent is a regular file so the halt.json write itself
# fails) gave 0 violations of the 2/2/1 codes and 0 violations of the six-key sentinel.
#
# What remains duplicated is the VOCABULARY. `halt_outcome(exc)` is the only named
# implementation, it lives in a tool module (`rig_character.py`) rather than in
# `armature_core`, and `rig_character` is its only caller -- the other twenty inline the
# same three-branch ternary. The Stage B lift into `armature_core.errors` is outside this
# domain's globs and is filed in this wave's `skipped[]` (together with `_halt_keysafe`,
# which this wave added as a 21st copy for the same reason).
#
# The in-domain half is this census: the exit-code contract is driven for three raiser
# kinds, so a WORDING change in one copy of twenty is invisible to it unless one of those
# three raisers happens to hit the changed branch. This reads the literals themselves.

#: The vocabulary, as measured 2026-09-04 and as `test_instrument_exits.CONTRACT` asserts
#: behaviourally. Em dashes are part of it.
OUTCOME_VOCABULARY = (
    "FAILED — an unhandled error",
    "HALTED — a gate fired",
    "REFUSED — the tool declined to proceed",
)


def _outcome_strings(node):
    """Single-line em-dashed string constants inside `node`, docstrings excluded.

    The docstring exclusion is not cosmetic: `rig_character._write_halt`'s own docstring
    contains an em dash, and a census that counted it would report that tool as having a
    vocabulary of one prose paragraph instead of following the delegation to
    `halt_outcome`.
    """
    docstrings = set()
    for sub in ast.walk(node):
        if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                            ast.Module)):
            text = ast.get_docstring(sub, clean=False)
            if text is not None:
                docstrings.add(text)
    return {n.value for n in ast.walk(node)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and "—" in n.value and "\n" not in n.value
            and len(n.value) < 80 and n.value not in docstrings}


def outcome_literals(filename):
    """`(literals, routed_through)` — the outcome strings this tool's handler can print.

    Keyed on the handler and, where the handler delegates, on the module-level function it
    delegates to: `rig_character`'s handler carries no literal at all because it calls
    `halt_outcome(exc)`, and a census that read only the handler would report it as having
    no vocabulary rather than as having the same one by reference.
    """
    tree = ast.parse(read_source(filename))
    handler = None
    for top in tree.body:
        if (isinstance(top, ast.If) and isinstance(top.test, ast.Compare)
                and isinstance(top.test.left, ast.Name)
                and top.test.left.id == "__name__"):
            handler = top
    if handler is None:
        return [], None
    lits = _outcome_strings(handler)
    if lits:
        return sorted(lits), None
    called = {n.func.id for n in ast.walk(handler)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    module_fns = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    for name in sorted(called & set(module_fns)):
        found = _outcome_strings(module_fns[name])
        if found:
            return sorted(found), name
    # WAVE 25 (F-40316edd): the delegation can leave the module. A handler that is
    # `run_tool_main(main, "<PREFIX>")` prints the vocabulary through
    # `armature_core.parts.halt_outcome`, so the literals are read off THAT function --
    # the same one-hop rule, following the import instead of stopping at the module edge.
    # Read as an empty vocabulary, the tool that adopted the ONE home would be reported as
    # having no vocabulary at all on the commit that adopted it.
    if "run_tool_main" in called:
        import armature_core.parts as _parts

        home = ast.parse(open(_parts.__file__, encoding="utf-8").read())
        for node in ast.walk(home):
            if isinstance(node, ast.FunctionDef) and node.name == "halt_outcome":
                found = _outcome_strings(node)
                if found:
                    return sorted(found), "armature_core.parts.halt_outcome"
    return [], None


@pytest.mark.parametrize("filename", HALT_HELD)
def test_every_handler_spells_the_three_outcomes_the_same_way(filename):
    lits, _routed = outcome_literals(filename)
    assert tuple(lits) == OUTCOME_VOCABULARY, (
        f"{filename}: {lits}. The vocabulary is duplicated across 21 handlers, so a "
        f"wording change in one copy is a false record the exit-code contract cannot see")


def test_exactly_one_tool_routes_the_vocabulary_through_a_named_function():
    """The duplication itself, measured rather than described: 20 inline copies and one
    named `halt_outcome`, which is why the lift into `armature_core.errors` is filed."""
    routed = {f: r for f in HALT_HELD for _l, r in [outcome_literals(f)] if r}
    # WAVE 25 (F-40316edd): 20 inline copies, one module-local `halt_outcome`, and the
    # FIRST Blender-side tool to route through the lifted home. The lift the wave-10
    # comment above filed as pending landed in wave 22 as `armature_core.parts`; this row
    # is the measurement of it reaching this population, not a second exemption.
    assert routed == {"rig_character.py": "halt_outcome",
                      "stage_render.py": "armature_core.parts.halt_outcome"}, routed


def test_the_vocabulary_census_goes_red_on_one_reworded_copy(tmp_path, monkeypatch):
    """Rule 3: a member added with a drifted literal must be reported."""
    probe = tmp_path / "probe_words.py"
    probe.write_text(
        'import bpy\n'
        'if __name__ == "__main__":\n'
        '    try:\n'
        '        raise SystemExit(main())\n'
        '    except SystemExit:\n'
        '        raise\n'
        '    except BaseException as exc:\n'
        '        print("PROBE_WORDS_HALT", "HALTED \\u2014 a gate fired",\n'
        '              "REFUSED \\u2014 the tool declined to proceed",\n'
        '              "FAILED \\u2014 an unexpected error")\n', encoding="utf-8")
    import blender_stub
    monkeypatch.setattr(blender_stub, "TOOLS", str(tmp_path))
    lits, routed = outcome_literals("probe_words.py")
    assert routed is None
    assert tuple(lits) != OUTCOME_VOCABULARY
    assert "FAILED — an unexpected error" in lits
