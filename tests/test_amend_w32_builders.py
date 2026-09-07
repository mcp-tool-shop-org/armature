"""Wave 32 Stage D amend — builders LOOK pins."""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(REPO, "tools")
sys.path.insert(0, TOOLS)

import build_assembly_payload as BAP  # noqa: E402
import build_payload as BP  # noqa: E402
import fetch_run as F  # noqa: E402
import gate_saved_graph as GSG  # noqa: E402

EPILOG_TOOLS = [
    "gate_saved_graph.py",
    "build_animate_payload.py",
    "build_camera_i2v_payload.py",
    "build_assembly_payload.py",
    "build_cascade_payload.py",
    "build_payload.py",
    "build_i2v_payload.py",
    "build_lora_arm_payload.py",
    "build_r2v_payload.py",
    "build_t2v_payload.py",
    "canon_gate.py",
    "fetch_run.py",
    "fetch_t2v_run.py",
]

SPEND_GROUP_TOOLS = [
    "build_payload.py",
    "build_r2v_payload.py",
    "build_i2v_payload.py",
    "build_t2v_payload.py",
    "build_camera_i2v_payload.py",
    "build_animate_payload.py",
    "build_lora_arm_payload.py",
]

PATH_OK_PREFIXES = [
    "BUILD_ASSEMBLY_OK",
    "BUILD_CASCADE_OK",
    "BUILD_R2V_OK",
    "BUILD_LORA_ARM_OK",
]


def _help_text(module_path):
    proc = subprocess.run(
        [sys.executable, module_path, "--help"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=REPO, env={**os.environ, "PYTHONPATH": f"{REPO};{TOOLS}"})
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


# ---------------------------------------------------------------------------
# F-13a5d3b0 — RawDescription + unsplittable COST label + blank line
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", EPILOG_TOOLS)
def test_epilog_keeps_cost_label_intact_and_blank_before_cost(name):
    """reverted-red: yes — without RawDescription / unsplittable label, COST splits."""
    src = open(os.path.join(TOOLS, name), encoding="utf-8").read()
    assert "RawDescriptionHelpFormatter" in src, name
    assert "WHAT A REFUSAL \"\n" not in src and 'WHAT A REFUSAL "\n' not in src, name
    # label never split across adjacent string literals
    assert not re.search(r'WHAT A REFUSAL\s*"\s*\n\s*"COSTS:', src), name
    help_out = _help_text(os.path.join(TOOLS, name))
    assert "WHAT A REFUSAL COSTS:" in help_out, help_out[-400:]
    assert re.search(r"WHAT A REFUSAL\s*\n\s*COSTS:", help_out) is None, help_out[-400:]
    # blank line between ROUTE block and COST block
    assert re.search(r"ROUTE:.*\n\nWHAT A REFUSAL COSTS:", help_out, re.S), help_out[-500:]


# ---------------------------------------------------------------------------
# F-277e6a39 — fetch_run progress field layout
# ---------------------------------------------------------------------------

def test_fetch_progress_lines_share_fields(tmp_path, monkeypatch, capfd):
    """reverted-red: yes — end line lacked -> dest and used double spaces."""

    def fake_run(cmd, **kw):
        env = kw.get("env") or {}
        with open(env["ARMATURE_FETCH_MANIFEST"], encoding="utf-8") as fh:
            jobs = json.load(fh)
        rows = []
        for job in jobs:
            os.makedirs(os.path.dirname(job["out"]), exist_ok=True)
            with open(job["out"], "wb") as out:
                out.write(F.PNG_SIGNATURE)
            rows.append({"out": job["out"], "url": job["url"], "code": 0, "message": ""})
        with open(env["ARMATURE_FETCH_EXITS"], "w", encoding="utf-8") as fh:
            json.dump(rows, fh)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(F.subprocess, "run", fake_run)
    from test_fetch_run import _dump, _result
    dump = _dump(tmp_path, [_result("302", i) for i in range(2)])
    assert F.main(["--dump", dump, "--run", "r", "--root", str(tmp_path / "runs")]) == 0
    err = [ln for ln in capfd.readouterr().err.splitlines() if ln.startswith("fetch_run download")]
    assert len(err) == 2, err
    assert "  " not in err[0].replace(" -> ", "→"), err[0]
    assert "  " not in err[1].replace(" -> ", "→"), err[1]
    assert "-> " in err[0] and "-> " in err[1]
    # same field order
    for ln in err:
        assert re.search(
            r"^fetch_run download \d+/\d+ elapsed \S+s bound \S+s -> ", ln), ln


# ---------------------------------------------------------------------------
# F-3fb6b39b — --node-map unbroken in --root help
# ---------------------------------------------------------------------------

def test_fetch_run_help_keeps_node_map_flag_intact():
    """reverted-red: yes — help wrapped as --node- / map."""
    help_out = _help_text(os.path.join(TOOLS, "fetch_run.py"))
    assert "--node-map" in help_out
    assert re.search(r"--node-\s*\n\s*map", help_out) is None, help_out


# ---------------------------------------------------------------------------
# F-32072072 / F-402fd2b8 — SAVED_ADMISSION_OK LOOK
# ---------------------------------------------------------------------------

def test_saved_admission_ok_is_pretty_ascii_safe(tmp_path, capsys):
    """reverted-red: yes — one-line dumps used \\u2014 and wrapped mid-key."""
    from conftest import load_ok_payload
    from test_amend_w22_builders import _latent_cli
    assert GSG.main(_latent_cli(tmp_path, frame="832,480,81")) == 0
    out = capsys.readouterr().out
    assert "SAVED_ADMISSION_OK\n" in out or out.startswith("SAVED_ADMISSION_OK\n")
    assert "\\u2014" not in out
    assert "—" not in out
    payload = load_ok_payload(out)
    assert "path" in payload and payload["path"]
    assert " - " in payload["gate_L"]
    # pretty body: indented keys on their own lines
    assert re.search(r'\n  "gate_L":', out), out
    for ln in out.splitlines():
        if ln.strip().startswith('"optional_sockets') or "optional_sockets" in ln:
            assert len(ln) <= 78 or ln.lstrip().startswith('"'), ln


# ---------------------------------------------------------------------------
# F-3e310dc1 — unified path key on OK receipts
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name,prefix", [
    ("build_assembly_payload.py", "BUILD_ASSEMBLY_OK"),
    ("build_cascade_payload.py", "BUILD_CASCADE_OK"),
    ("build_r2v_payload.py", "BUILD_R2V_OK"),
    ("build_lora_arm_payload.py", "BUILD_LORA_ARM_OK"),
])
def test_path_only_ok_receipts_carry_path_json_key(name, prefix):
    """reverted-red: yes — path-only OK lines had no JSON path key."""
    src = open(os.path.join(TOOLS, name), encoding="utf-8").read()
    assert f'print("{prefix} " + json.dumps({{"path":' in src.replace(" ", "") or \
           f'print("{prefix} " + json.dumps({{"path":' in src
    assert re.search(rf'print\(f"{prefix}\s+', src) is None, name


def test_json_ok_receipts_include_path_key():
    for name, prefix in [
        ("build_payload.py", "BUILD_PAYLOAD_OK"),
        ("build_animate_payload.py", "BUILD_ANIMATE_OK"),
        ("build_i2v_payload.py", "BUILD_I2V_OK"),
        ("fetch_run.py", "FETCH_RUN_OK"),
        ("fetch_t2v_run.py", "FETCH_T2V_OK"),
    ]:
        src = open(os.path.join(TOOLS, name), encoding="utf-8").read()
        idx = src.find(f'print("{prefix} ')
        assert idx >= 0, name
        window = src[idx: idx + 500]
        assert '"path"' in window, (name, window)


# ---------------------------------------------------------------------------
# F-8d31935f — 17-col route gutter
# ---------------------------------------------------------------------------

def test_route_report_uses_r2v_gutter():
    """reverted-red: yes — `route components` broke the 17-col gutter."""
    lines = BAP.route_report_lines({
        "components": [], "seeds": [], "latents": [], "frame_legality": []})
    assert lines[0].startswith("route            components"), lines[0]
    assert lines[0][0:17] == "route            "


# ---------------------------------------------------------------------------
# F-b56f4f49 — indent=2 ensure_ascii=False on graph/record writes
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", [
    "build_assembly_payload.py",
    "build_cascade_payload.py",
    "build_r2v_payload.py",
    "build_payload.py",
])
def test_operator_facing_dumps_use_indent2_ensure_ascii_false(name):
    """reverted-red: yes — assembly family wrote indent=1."""
    src = open(os.path.join(TOOLS, name), encoding="utf-8").read()
    assert "indent=1" not in src, name
    assert "indent=2, ensure_ascii=False" in src or "indent=2,\n" in src, name


# ---------------------------------------------------------------------------
# F-cd3e699a — argparse groups; inherit Gate CANON title from helper
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", SPEND_GROUP_TOOLS)
def test_spend_builders_group_build_flags_without_second_canon_group(name):
    """reverted-red: yes — flat options: with no build/output groups."""
    src = open(os.path.join(TOOLS, name), encoding="utf-8").read()
    assert 'add_argument_group("build")' in src, name
    assert 'add_argument_group("output")' in src, name
    # do not open a second CANON group in builders — helper owns "Gate CANON"
    assert 'add_argument_group("Gate CANON")' not in src, name
    assert "add_spend_flags(" in src, name


def test_build_payload_help_shows_build_and_output_groups():
    help_out = _help_text(os.path.join(TOOLS, "build_payload.py"))
    assert re.search(r"^build:", help_out, re.M), help_out
    assert re.search(r"^output:", help_out, re.M), help_out


# ---------------------------------------------------------------------------
# F-fd2be19e — disclosure wrap at boundaries
# ---------------------------------------------------------------------------

def test_disclosure_lines_wrap_at_boundaries_not_mid_word():
    """reverted-red: yes — 218-char credit line wrapped mid-word at col 80."""
    block = {
        "route_verdict": "V",
        "obligations": [{
            "kind": "credit",
            "creditor": "renderartist",
            "text": "credit the creator on published footage",
            "component": "style-lora-t",
            "applies_to": "published footage",
            "source": "docs/license-map.md",
        }],
    }
    lines = BAP.disclosure_lines(block)
    assert all(len(ln) <= 78 for ln in lines), lines
    joined = " ".join(ln.strip() for ln in lines)
    assert "CREDIT OBLIGATION:" in joined
    assert "style-lora-t" in joined
