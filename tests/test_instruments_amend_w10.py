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


@pytest.mark.parametrize("filename", BLENDER_TOOLS)
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
    derived = {fn: set(success_tokens(fn)) for fn in BLENDER_TOOLS}
    shared = shared_success_tokens(derived)
    assert shared == {}, f"success tokens claimed by more than one tool: {shared}"


def test_no_success_token_is_a_prefix_of_any_tools_halt_token():
    """`PROBE_GLB` matched `PROBE_GLB_HALT`: the success grep was satisfied by the halt."""
    halts = {halt_prefix(fn) + "_HALT" for fn in BLENDER_TOOLS}
    bad = []
    for fn in BLENDER_TOOLS:
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
