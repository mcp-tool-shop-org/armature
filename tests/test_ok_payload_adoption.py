"""Wave 35, F-a048ef6f — every `*_OK` parser imports `load_ok_payload` or is exempt.

`load_ok_payload` in conftest is the ONE receipt reader (one-line JSON or sentinel +
pretty body). Modules that still hand-roll `startswith`/`split` against an OK token must
migrate or sit on the shrinking exemption list below.
"""

from __future__ import annotations

import ast
import glob
import os
import re

import pytest

from conftest import load_ok_payload

TESTS = os.path.dirname(os.path.abspath(__file__))
OK_TOKEN_RE = re.compile(r"\b[A-Z][A-Z0-9_]*_OK\b")
HAND_PARSE_RE = re.compile(
    r"""(?:startswith\([^)]*_OK|split\([^)]*_OK|\[len\([^)]*_OK)"""
)

#: Modules that mention an `*_OK` token but do not parse a JSON receipt through
#: `load_ok_payload` — presence checks, source-scan pins, halt/OK pairing censuses.
#: May only shrink.
OK_PAYLOAD_EXEMPT = {
    "test_amend_w10_builders.py",
    "test_amend_w22_core_gates.py",
    "test_amend_w28_builders.py",
    "test_assembly.py",
    "test_cascade.py",
    "test_route_gates.py",
    "test_build_t2v_payload_a3.py",
    "test_ci_workflows.py",
    "test_instruments_amend_w10.py",
    "test_instruments_amend_w12.py",
    "test_instruments_amend_w14.py",
    "test_instruments_amend_w22.py",
    "test_instruments_amend_w25.py",
    "test_instruments_amend_w29.py",
    "test_instruments_measure_amend_w12.py",
    "test_instruments_measure_amend_w14.py",
    "test_instruments_measure_amend_w16.py",
    "test_instruments_measure_amend_w18.py",
    "test_instruments_measure_amend_w22.py",
    "test_instruments_measure_amend_w25.py",
    "test_instruments_measure_amend_w28.py",
    "test_instruments_measure_amend_w34.py",
    "test_packaging.py",
    "test_paid_argv_smoke.py",
    "test_measure_argv_smoke.py",
    "test_measure_clip.py",
    "test_extended_sheet_argv_smoke.py",
    "test_sheet_argv_smoke.py",
    "test_sheet_pairing.py",
    "test_sheet_compose.py",
    "test_make_review_clip.py",
    "test_make_e08_sheet.py",
    "test_make_lift_sheet.py",
    "test_render_pose_sticks.py",
    "test_gate_saved_graph.py",
    "test_build_camera_i2v_payload.py",
    "test_build_i2v_payload.py",
    "test_record_index_binding.py",
    "test_refusal_clauses.py",
    "test_retopo_and_bake.py",
    "test_ok_payload_adoption.py",
}


def _imports_load_ok_payload(tree):
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom):
            if any(a.name == "load_ok_payload" for a in n.names):
                return True
        if isinstance(n, ast.Name) and n.id == "load_ok_payload":
            return True
        if isinstance(n, ast.Attribute) and n.attr == "load_ok_payload":
            return True
    return False


def _mentions_ok_token(src):
    return bool(OK_TOKEN_RE.search(src))


def _hand_parses_ok(src):
    return bool(HAND_PARSE_RE.search(src))


def test_every_ok_mention_imports_load_ok_payload_or_is_exempt():
    offenders = []
    for path in sorted(glob.glob(os.path.join(TESTS, "test_*.py"))):
        base = os.path.basename(path)
        src = open(path, encoding="utf-8").read()
        if not _mentions_ok_token(src):
            continue
        tree = ast.parse(src)
        if _imports_load_ok_payload(tree):
            continue
        if base in OK_PAYLOAD_EXEMPT:
            continue
        offenders.append(base)
    assert offenders == [], (
        "modules mentioning *_OK must import load_ok_payload or join OK_PAYLOAD_EXEMPT "
        f"(may only shrink): {offenders}")


def test_the_exemption_list_may_only_shrink():
    """Ceiling pin — bump only with a reason naming the module that joined."""
    assert len(OK_PAYLOAD_EXEMPT) <= 42, len(OK_PAYLOAD_EXEMPT)


def test_load_ok_payload_reads_one_line_and_pretty_bodies():
    one = 'BUILD_PAYLOAD_OK {"out": "x"}\n'
    assert load_ok_payload(one, "BUILD_PAYLOAD_OK") == {"out": "x"}
    pretty = 'SAVED_ADMISSION_OK\n{\n  "path": "p"\n}\n'
    assert load_ok_payload(pretty) == {"path": "p"}


def test_a_hand_rolled_parser_without_import_is_visible_to_the_census(tmp_path):
    src = (
        "import json\n"
        "def test_x(capsys):\n"
        "    line = json.loads(capsys.readouterr().out.split('FETCH_RUN_OK ', 1)[1])\n"
    )
    p = tmp_path / "test_hand.py"
    p.write_text(src, encoding="utf-8")
    text = p.read_text(encoding="utf-8")
    assert _mentions_ok_token(text) and _hand_parses_ok(text)
    assert not _imports_load_ok_payload(ast.parse(text))
