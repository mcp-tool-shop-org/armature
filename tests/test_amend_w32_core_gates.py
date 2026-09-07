"""Wave 32 Stage D — core-gates LOOK pins for F-5a247f9b, F-a61ed92a,
F-b55313e0, F-d462af0d."""
import argparse
import re

from armature_core import canon, cli


# --- F-5a247f9b: root --help epilog URL must not soft-wrap mid-hostname ---------

def test_root_help_epilog_keeps_the_repo_url_on_one_line(capsys):
    """Measured: default HelpFormatter wrapped
    `https://github.com/mcp-` / `tool-shop-org/armature` across two physical lines."""
    rc = cli.main([])
    out = capsys.readouterr().out
    assert rc == 0
    assert cli.REPO in out
    assert "https://github.com/mcp-\n" not in out
    assert "mcp-\ntool-shop" not in out
    # The URL sits on its own epilog line, not glued to the prose.
    assert re.search(
        r"from the repo:\n\s*https://github.com/mcp-tool-shop-org/armature", out)


# --- F-a61ed92a: subcommands under commands: / COMMAND, not brace-set -----------

def test_root_help_lists_commands_under_commands_heading(capsys):
    """Measured: `positional arguments:` / `{modules,check,where}` brace-set."""
    cli.main([])
    out = capsys.readouterr().out
    assert "commands:" in out
    assert "COMMAND" in out
    assert "modules" in out and "check" in out and "where" in out
    assert "positional arguments:" not in out
    # Brace-set alone under positional arguments is the defect; choices may still
    # appear beside the COMMAND metavar, but not as the only heading content.
    before_commands = out.split("commands:")[0]
    assert "{modules,check,where}" not in before_commands


# --- F-b55313e0: modules text path hangs purpose under its column --------------

def test_modules_text_rows_hang_wrap_under_the_purpose_column(capsys, monkeypatch):
    """On an 80-col terminal, wrapped purpose lines indent to the purpose column
    (len('  ' + 16-wide name + ' ') == 19), so gate ids do not orphan at column 0."""
    monkeypatch.setattr(cli, "SURFACE", [
        ("assembly",
         "the assembly graph: frames in, one VIDEO out, no partner credit — "
         "gates: ASSEMBLY, CASCADE"),
        ("gates", "short"),
    ])
    rc = cli.main(["modules"])
    out = capsys.readouterr().out
    assert rc == 0
    lines = [ln for ln in out.splitlines() if ln.strip()]
    assert any(ln.startswith("  assembly") for ln in lines)
    assert any(ln.startswith(" " * 19) for ln in lines), lines
    assert any("ASSEMBLY" in ln or "CASCADE" in ln or "gates:" in ln for ln in lines)
    for ln in lines:
        if ln.lstrip().startswith(("gates:", "ASSEMBLY", "CASCADE", "PARTS")):
            assert ln.startswith(" " * 19), ln
    assert all(len(ln) <= 80 for ln in lines if not ln.startswith("armature_core")), lines


def test_modules_json_is_unchanged_by_the_text_wrap(capsys):
    """`--json` still ships purpose as one string; wrap is text-path only."""
    import json
    rows = json.loads(_run(["modules", "--json"], capsys))
    by_name = {r["module"]: r for r in rows}
    assert "ASSEMBLY" in by_name["assembly"]["purpose"]
    assert "\n" not in by_name["assembly"]["purpose"]


# --- F-d462af0d: add_spend_flags clusters under Gate CANON ---------------------

def test_add_spend_flags_opens_a_gate_canon_argument_group():
    """Measured: the three flags sat flat under options: with no section heading."""
    ap = argparse.ArgumentParser(prog="build_x_payload.py")
    canon.add_spend_flags(ap)
    titles = [g.title for g in ap._action_groups]
    assert "Gate CANON" in titles
    group = next(g for g in ap._action_groups if g.title == "Gate CANON")
    flags = {a.option_strings[0] for a in group._group_actions if a.option_strings}
    assert flags == {"--subject", "--no-canon", "--canon-prompt"}
    rendered = ap.format_help()
    assert "Gate CANON:" in rendered
    # Still one cluster — builders must not open a second.
    assert rendered.count("Gate CANON:") == 1


def _run(argv, capsys):
    cli.main(argv)
    return capsys.readouterr().out
