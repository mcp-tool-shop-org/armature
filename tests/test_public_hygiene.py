"""Whole-repo public-repository hygiene guard.

Prevents internal workflow role labels, local filesystem paths, and personal
identifiers from re-entering public-facing files (code, tests, specs, docs,
workflows, site, and packaging). All checked needles and sensitive fixture tokens
are constructed from parts so this module introduces no checked token.
"""

import os
import re
import subprocess

from conftest import REPO

# Token needles constructed from fragments.
_LBL_1 = "dir" + "ector"
_LBL_2 = "se" + "at"
_LBL_3 = "pub" + "lisher"
_LBL_4 = "r" + "&d"
_LBL_5 = "anti" + "gravity"
_PNAME = "mi" + "ke"

# Published paper title kept in docs/research-grounding.md.
_PAPER_TITLE = "Video" + _LBL_1.title() + "GPT"

_TRUSTED = "trusted"
_DRV_C = "C" + ":"
_DRV_E = "E" + ":"
_C_SYSTEM = rf"{_DRV_C}(?:/|\\\\|\\)(?:Windows|Program Files)(?:[/\\\"'`\s]|$)"
_C_SYNTH = rf"{_DRV_C}(?:/|\\\\|\\)(?:tmp|elsewhere|clips|abs)(?:[/\\\"'`\s]|$)"
_HOME_PFX = "/" + "home/"
_MAC_PFX = "/" + "Users/"
_MNT_PFX = "/m" + "nt/"
_MODELS_TAG = "AI" + "-Models"
_NL_ESCAPE_ONLY = r"n(?![A-Za-z0-9_.-])"

RX_1 = re.compile(_LBL_1 + r"(?!y|ies|io|ios)", re.I)
# Identifier-aware match: catches standalone, hyphenated, snake_case, and camelCase/PascalCase
# forms of the role label, while letting English words like `seated` and `seating` pass.
RX_2 = re.compile(
    rf"(?:(?:^|[^A-Za-z0-9]|_)(?i:{_LBL_2}s?)(?=$|[^A-Za-z0-9]|_)"
    rf"|(?<=[a-z0-9]){_LBL_2.title()}s?(?=$|[^A-Za-z0-9]|_|[A-Z])"
    rf"|(?:^|[^A-Za-z0-9]|_)(?i:{_LBL_2}s?)(?=[A-Z]))"
)
RX_3 = re.compile(rf"(?<!{_TRUSTED} )(?<!{_TRUSTED}-)" + _LBL_3, re.I)
RX_4 = re.compile(re.escape(_LBL_4), re.I)
RX_5 = re.compile(_LBL_5, re.I)
RX_PNAME = re.compile(rf"\b{_PNAME}\b", re.I)
RX_E_BS_LETTER = re.compile(rf"(?<![A-Za-z0-9_]){_DRV_E}(?:\\\\|\\)[A-Za-z]")
RX_DRIVE_ANY = re.compile(
    rf"(?<![A-Za-z0-9_])(?!{_C_SYSTEM})(?!{_C_SYNTH})"
    rf"[A-Za-z]:(?:/|\\\\|\\(?!{_NL_ESCAPE_ONLY}|[\"'`]))(?=[A-Za-z0-9_.-])",
    re.I,
)
RX_LPATH_OTHER = re.compile(
    rf"(?:{_HOME_PFX}|{_MAC_PFX}|{_MNT_PFX}[A-Za-z]/|{re.escape(_MODELS_TAG)})",
    re.I,
)


def _match_local_path(line: str) -> bool:
    """Return True when a line contains a local machine drive or home/mount path."""
    return bool(
        RX_E_BS_LETTER.search(line)
        or RX_DRIVE_ANY.search(line)
        or RX_LPATH_OTHER.search(line)
    )


def tracked_repo_files(repo: str = REPO) -> list[str]:
    """Return all tracked file paths (POSIX) in the repository."""
    out = subprocess.check_output(
        ["git", "-C", repo, "ls-files"],
        stdin=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    return sorted(line.strip() for line in out.splitlines() if line.strip())


def scan_lines(rel: str, text: str) -> list[str]:
    """Return formatted hygiene violations for one file's decoded text."""
    hits: list[str] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        line_for_rx1 = line.replace(_PAPER_TITLE, " ")
        if RX_1.search(line_for_rx1):
            hits.append(f"{rel}:{lineno} [role-label] {line.strip()[:120]}")
        for kind, rx in (
            ("role-label", RX_2),
            ("role-label", RX_3),
            ("team-label", RX_4),
            ("tool-label", RX_5),
        ):
            if rx.search(line):
                hits.append(f"{rel}:{lineno} [role-label] {line.strip()[:120]}" if kind == "role-label" else f"{rel}:{lineno} [{kind}] {line.strip()[:120]}")
        if _match_local_path(line):
            hits.append(f"{rel}:{lineno} [local-path] {line.strip()[:120]}")
        if RX_PNAME.search(line):
            hits.append(f"{rel}:{lineno} [personal-name] {line.strip()[:120]}")
    return hits


def scan_tree(repo: str = REPO) -> list[str]:
    """Scan every tracked non-binary file in the repository for labels, paths, and names."""
    findings: list[str] = []
    for rel in tracked_repo_files(repo):
        full = os.path.join(repo, rel.replace("/", os.sep))
        if not os.path.isfile(full):
            continue
        with open(full, "rb") as fh:
            raw = fh.read()
        if b"\x00" in raw:
            continue
        text = raw.decode("utf-8", errors="replace")
        findings.extend(scan_lines(rel, text))
    return findings


def test_whole_repo_has_no_internal_labels_local_paths_or_personal_names():
    """Fail if any tracked file holds an internal label, local path, or personal name."""
    findings = scan_tree(REPO)
    assert findings == [], (
        f"{len(findings)} hygiene violation(s) found:\n  " + "\n  ".join(findings[:20])
    )


def test_ci_path_filters_cover_every_guarded_hygiene_file():
    """Every tracked file must trigger CI on push and pull_request."""
    import test_ci_workflows as ci_mod

    tracked = tracked_repo_files(REPO)
    for trigger in ("push", "pull_request"):
        patterns = ci_mod._paths_under(trigger)
        uncovered = [rel for rel in tracked if not ci_mod._pattern_hits(patterns, rel)]
        assert uncovered == [], (
            f"{trigger} path filters do not cover guarded files: {uncovered}"
        )


def test_hygiene_scanner_catches_labels_paths_and_name_while_honouring_exclusions():
    """Unit check: positives fire cleanly and narrow documented exemptions stay clean."""
    # Role, team, and tool labels
    assert scan_lines("README.md", f"Approved by the {_LBL_1.title()} yesterday.")
    assert scan_lines("tests/x.py", f"def test_{_LBL_1}_mode(): pass")
    assert scan_lines("notes/x.md", f"Next {_LBL_2} picks it up.")
    assert scan_lines("notes/x.md", f"Three {_LBL_2}s agreed.")
    assert scan_lines("notes/x.md", f"A five-{_LBL_2} panel.")
    # Identifier-aware forms of the second role label
    assert scan_lines("tools/x.py", f"{_LBL_2}_id = 'a'")
    assert scan_lines("tools/x.py", f"{_LBL_2.upper()}_LABEL = 'x'")
    assert scan_lines("tools/x.py", f"review{_LBL_2.title()} = 1")
    assert scan_lines("tools/x.py", f"review_{_LBL_2} = 1")
    assert scan_lines("CHANGELOG.md", f"The registered {_LBL_3} failed.")
    assert scan_lines("notes/x.md", f"Via {_LBL_4} and {_LBL_5.title()}.")

    # Drive letters (both cases, \ and /, including n/t/r initials) and /mnt/<letter>/
    _drv_f = "F" + ":"
    _drv_d_hi = "D" + ":"
    _drv_d_lo = "d" + ":"
    _drv_e_lo = "e" + ":"
    _bs = chr(92)
    assert scan_lines("tools/x.py", f"P = r'{_DRV_E}{_bs}AI{_bs}repo'")
    assert scan_lines("tools/x.py", f"P = r'{_DRV_E}{_bs}training{_bs}asset.glb'")
    assert scan_lines("tools/x.py", f"P = r'{_DRV_E}{_bs}t'")
    assert scan_lines("notes/x.md", f"{_drv_f}{_bs}training{_bs}model")
    assert scan_lines("notes/x.md", f"{_drv_d_hi}{_bs}new{_bs}run")
    assert scan_lines("notes/x.md", f"{_drv_e_lo}{_bs}new{_bs}run")
    assert scan_lines("tools/x.py", f"{_drv_d_lo}/x")
    assert scan_lines("tools/x.py", f"P = '{_drv_d_hi}/work/repo'")
    assert scan_lines("tools/x.py", "P = r'Z" + f":{_bs}models{_bs}clip.mp4'")
    assert scan_lines("tools/x.py", f"P = '{_DRV_C}/dev/checkout'")
    assert scan_lines("notes/x.md", f"cd {_MNT_PFX}e/work")
    assert scan_lines("notes/x.md", f"cd {_MNT_PFX}c/{'Us' + 'ers'}/dev")
    assert scan_lines("README.md", f"cd {_HOME_PFX}dev/armature")
    assert scan_lines("README.md", f"{_DRV_C}{_bs}{'Us' + 'ers'}{_bs}dev{_bs}armature")
    assert scan_lines("notes/x.md", f"| **Role** ({_PNAME.title()}) |")
    assert scan_lines("notes/x.md", f"{_PAPER_TITLE} by {_LBL_1.title()}")

    clean_lines = [
        "output directory and subdirectories",
        "el directorio de salida",
        f"PyPI {_TRUSTED.title()} {_LBL_3.title()} OIDC",
        _PAPER_TITLE,
        "smikeline non_matching_token",
        "a seated posture and seating arrangement",
        "except Exception as e:" + chr(92) + "n pass",
        'if "else:' + chr(92) + 'n" in src:',
        rf"{_DRV_C}\Program Files\Blender Foundation\Blender 5.2\blender.exe",
        rf"{_DRV_C}\Windows\Fonts\arial.ttf",
        f"{_DRV_C}/tmp/outdir",
        f"{_DRV_C}/elsewhere/x",
        f"{_DRV_C}/clips/sample.mp4",
        f"{_DRV_C}/abs/path",
    ]
    assert scan_lines("README.es.md", "\n".join(clean_lines)) == []
