"""Wave 35, F-4515289b — every skipif reason names a documented suite lever.

conftest's module docstring lists the operator levers (`ARMATURE_BLENDER` /
`ARMATURE_GIT` / `ARMATURE_FONT_DIR`) and the skip families. Before this wave the
predicates lived inline and many reasons keyed on path constants (`BLENDER`, a banked
`outputs/` path) without naming the lever an operator would set. The helpers
`requires_blender` / `requires_git` / `requires_fonts` / `requires_bank` embed the lever
in `reason=`; this census keeps every other skipif honest.
"""

from __future__ import annotations

import ast
import glob
import os

import pytest

from conftest import SKIP_LEVER_VOCABULARY

TESTS = os.path.dirname(os.path.abspath(__file__))

#: Modules whose skip reasons are platform / third-party / PATH binaries rather than the
#: three ARMATURE_* levers — may only shrink. Each entry's reason must still match
#: SKIP_LEVER_VOCABULARY (bash/node/platform/Pillow/…).
SKIPIF_REASON_EXEMPT_MODULES = set()


def _skipif_reasons(path):
    """`(lineno, reason_str_or_None)` for every `pytest.mark.skipif` in this module."""
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    tree = ast.parse(src)
    out = []

    def _const(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.JoinedStr):
            parts = []
            for v in node.values:
                if isinstance(v, ast.Constant) and isinstance(v.value, str):
                    parts.append(v.value)
                else:
                    parts.append("{}")
            return "".join(parts)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left, right = _const(node.left), _const(node.right)
            if left is not None and right is not None:
                return left + right
        return None

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # pytest.mark.skipif(...)
        if not (isinstance(func, ast.Attribute) and func.attr == "skipif"):
            continue
        reason = None
        for kw in node.keywords:
            if kw.arg == "reason":
                reason = _const(kw.value)
        if reason is None and len(node.args) >= 2:
            reason = _const(node.args[1])
        out.append((node.lineno, reason))
    return out


def _reason_names_a_lever(reason):
    if reason is None:
        return False
    lower = reason.lower()
    return any(token.lower() in lower for token in SKIP_LEVER_VOCABULARY)

def test_every_skipif_reason_names_a_documented_lever():
    """F-4515289b: the docstring contract is a harness capability, not prose."""
    offenders = []
    for path in sorted(glob.glob(os.path.join(TESTS, "test_*.py"))):
        base = os.path.basename(path)
        if base in SKIPIF_REASON_EXEMPT_MODULES:
            continue
        for lineno, reason in _skipif_reasons(path):
            if not _reason_names_a_lever(reason):
                offenders.append((base, lineno, reason))
    assert offenders == [], (
        "skipif reason must name a lever from conftest.SKIP_LEVER_VOCABULARY "
        f"({SKIP_LEVER_VOCABULARY}); offenders: {offenders}")


def test_the_skip_helpers_embed_the_armature_levers():
    """The centralized predicates name ARMATURE_* in reason=."""
    from conftest import requires_bank, requires_blender, requires_fonts, requires_git

    cases = (
        (requires_blender(), "ARMATURE_BLENDER"),
        (requires_git(), "ARMATURE_GIT"),
        (requires_fonts(), "ARMATURE_FONT_DIR"),
        (requires_bank("/no/such/bank/path"), "outputs/"),
    )
    for mark, token in cases:
        reason = mark.mark.kwargs.get("reason") or ""
        assert token in reason, (token, reason)


def test_the_skip_lever_census_goes_red_on_a_silent_reason(tmp_path):
    """reverted-red operand: a skipif whose reason names no lever."""
    src = (
        "import pytest\n"
        "@pytest.mark.skipif(True, reason='missing binary')\n"
        "def test_x():\n"
        "    pass\n"
    )
    p = tmp_path / "test_silent.py"
    p.write_text(src, encoding="utf-8")
    reasons = _skipif_reasons(str(p))
    assert len(reasons) == 1
    assert not _reason_names_a_lever(reasons[0][1])
