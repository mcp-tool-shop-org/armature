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
from blender_stub import (blender_tools, exit_code_of_main_block, load_tool, main_block,
                          read_source)

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
    comment at rig_repair.py:157-161 describes, and the branch an ordinary GLB reaches
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
    assert rec["error"] == "ArmatureError", rec


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
    """The `<PREFIX>` of the one `<PREFIX>_HALT` literal in the tool's `__main__` handler.

    Keyed on the HANDLER's own sentinel -- the node the halt contract's identity actually
    lives on -- rather than on the file's stem, so a tool whose token and stem disagree is
    REPORTED by the pairing assertion below instead of being defined into agreement by the
    census's own derivation.
    """
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
    if len(found) != 1:
        raise ValueError(f"{filename}: {sorted(found)} HALT token(s) in the handler, want 1")
    return found.pop()


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
    """
    mod = load_tool(filename)
    assert callable(getattr(mod, "_halt_keysafe", None)), (
        f"{filename} has no `_halt_keysafe`; its sentinel cannot serialise a "
        f"non-string-keyed evidence dict and the halt escapes")
    assert "_halt_keysafe(" in read_source(filename).split(
        'if __name__ == "__main__":')[-1], (
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


def _render_call_sites(filename):
    """Line numbers of every `bpy.ops.render.render(...)` call in the file."""
    tree = ast.parse(read_source(filename))
    return sorted(node.lineno for node in ast.walk(tree)
                  if isinstance(node, ast.Call)
                  and ast.unparse(node.func) == "bpy.ops.render.render")


def _calls_named(filename, names):
    """`{callee: [names passed as its first positional argument]}` for `names`."""
    tree = ast.parse(read_source(filename))
    out = {n: [] for n in names}
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in out and node.args
                and isinstance(node.args[0], ast.Name)):
            out[node.func.id].append(node.args[0].id)
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
    "render_start_frame.py": ("_pixels", "_alpha_channel"),
}


def test_the_renderer_population_is_derived_and_is_the_one_recorded():
    derived = sorted(f for f in BLENDER_TOOLS if _render_call_sites(f))
    assert derived == RECORDED_RENDERERS, {
        "appeared": sorted(set(derived) - set(RECORDED_RENDERERS)),
        "vanished": sorted(set(RECORDED_RENDERERS) - set(derived))}
    assert set(READ_BACK_EXEMPT) <= set(derived), sorted(READ_BACK_EXEMPT)


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
    mod.bpy.ops.render.render.side_effect = lambda **kw: open(path, "wb").close()
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
    mod.bpy.ops.render.render.side_effect = lambda **kw: open(path, "wb").write(b"PNG")
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
        mod.gate_previews_written([str(good), str(empty), str(missing)])
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
        paths.append(str(p))
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
# consumers that list frames downstream (`encode_control.py:126`, `invert_frames.py:70`)
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
#: than silently excluded: `tools/render_pose_sticks.py:178` (instruments-measure, Gate
#: COUNT) and `tools/armature_core/donor_gate.py:79` (core-gates, `frame_paths`). Both are
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
    assert routed == {"rig_character.py": "halt_outcome"}, routed


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
