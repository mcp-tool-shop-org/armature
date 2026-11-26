"""Public-repository hygiene guard across Part A files and CLAUDE.md.

Prevents internal workflow role labels, local filesystem paths, and personal
identifiers from re-entering public-facing files (code, tests, specs, docs,
workflows, site, and packaging). All checked needles and Part B exclusions are
constructed from parts so this module introduces no checked token and adds no
synthetic literal to the CI docs-path census.
"""

import os
import re
import subprocess

from conftest import REPO

_DOCS_DIR = "docs/"
_PART_B_DOCS_FILES = (
    "audit-first-arc.md",
    "random-routes.md",
    "video-provider-field-notes.md",
    "wan-video-prompt-guide-notes.md",
    "wan21-prompt-guide-notes.md",
    "wan26-image-guide-notes.md",
)
_PART_B_DOCS_PFX = (
    "experiments/",
    "dispatches/",
    "comfy-consult",
    "grok-consult",
    "research-grounding",
    "index/",
)

# Historical records and derived index artifacts outside Part A's scope.
# Any new file added anywhere else in the repo enters Part A by default.
PART_B_EXACT = frozenset({"CLAUDE.md", "HANDOFF.md"} | {_DOCS_DIR + x for x in _PART_B_DOCS_FILES})
PART_B_PREFIXES = tuple(_DOCS_DIR + p for p in _PART_B_DOCS_PFX)

# Token needles constructed from fragments.
_LBL_1 = "dir" + "ector"
_LBL_2 = "se" + "at"
_LBL_3 = "pub" + "lisher"
_LBL_4 = "r" + "&d"
_LBL_5 = "anti" + "gravity"
_PNAME = "mi" + "ke"

_TRUSTED = "trusted"
_DRV_C = "C" + ":"
_DRV_E = "E" + ":"
_C_SYSTEM = rf"{_DRV_C}(?:/|\\\\|\\)(?:Windows|Program Files)(?:[/\\\"'`\s]|$)"
_C_SYNTH = rf"{_DRV_C}(?:/|\\\\|\\)(?:tmp|elsewhere|clips|abs)(?:[/\\\"'`\s]|$)"
_HOME_PFX = "/" + "home/"
_MAC_PFX = "/" + "Users/"
_MODELS_TAG = "AI" + "-Models"

RX_1 = re.compile(_LBL_1 + r"(?!y|ies|io|ios)", re.I)
RX_2 = re.compile(rf"\b{_LBL_2}s?\b", re.I)
RX_3 = re.compile(rf"(?<!{_TRUSTED} )(?<!{_TRUSTED}-)" + _LBL_3, re.I)
RX_4 = re.compile(re.escape(_LBL_4), re.I)
RX_5 = re.compile(_LBL_5, re.I)
RX_PNAME = re.compile(rf"\b{_PNAME}\b", re.I)
RX_E_BS_LETTER = re.compile(rf"(?<![A-Za-z0-9_]){_DRV_E}(?:\\\\|\\)[A-Za-z]")
RX_DRIVE_ANY = re.compile(
    rf"(?<![A-Za-z0-9_])(?!{_C_SYSTEM})(?!{_C_SYNTH})"
    rf"[A-Za-z]:(?:/|\\\\|\\(?![nrt\"'`]))(?=[A-Za-z0-9_.-])",
    re.I,
)
RX_LPATH_OTHER = re.compile(
    rf"(?:{_HOME_PFX}|{_MAC_PFX}|{re.escape(_MODELS_TAG)})",
    re.I,
)


def _match_local_path(line: str) -> bool:
    """Return True when a line contains a local machine drive or home path."""
    return bool(
        RX_E_BS_LETTER.search(line)
        or RX_DRIVE_ANY.search(line)
        or RX_LPATH_OTHER.search(line)
    )


def is_part_b(rel: str) -> bool:
    """Return True when a repo-relative POSIX path belongs to Part B records."""
    return rel in PART_B_EXACT or rel.startswith(PART_B_PREFIXES)


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


def scan_lines(rel: str, text: str, include_labels_and_paths: bool = True) -> list[str]:
    """Return formatted hygiene violations for one file's decoded text."""
    hits: list[str] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if include_labels_and_paths:
            for kind, rx in (
                ("role-label", RX_1),
                ("role-label", RX_2),
                ("role-label", RX_3),
                ("team-label", RX_4),
                ("tool-label", RX_5),
            ):
                if rx.search(line):
                    hits.append(f"{rel}:{lineno} [{kind}] {line.strip()[:120]}")
            if _match_local_path(line):
                hits.append(f"{rel}:{lineno} [local-path] {line.strip()[:120]}")
        if RX_PNAME.search(line):
            hits.append(f"{rel}:{lineno} [personal-name] {line.strip()[:120]}")
    return hits


def scan_tree(repo: str = REPO) -> list[str]:
    """Scan every Part A tracked file for labels, paths, and personal name, plus CLAUDE.md for personal name."""
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
        if rel == "CLAUDE.md":
            findings.extend(scan_lines(rel, text, include_labels_and_paths=False))
        elif not is_part_b(rel):
            findings.extend(scan_lines(rel, text, include_labels_and_paths=True))
    return findings


def test_part_a_has_no_internal_labels_local_paths_or_personal_names():
    """Fail if any Part A file holds an internal label, local path, or personal name (plus CLAUDE.md)."""
    findings = scan_tree(REPO)
    assert findings == [], (
        f"{len(findings)} hygiene violation(s) found:\n  " + "\n  ".join(findings[:20])
    )


def test_ci_path_filters_cover_every_guarded_hygiene_file():
    """Every Part A file and CLAUDE.md must trigger CI on push and pull_request."""
    import test_ci_workflows as ci_mod

    tracked = tracked_repo_files(REPO)
    guarded = [
        rel for rel in tracked if rel == "CLAUDE.md" or not is_part_b(rel)
    ]
    for trigger in ("push", "pull_request"):
        patterns = ci_mod._paths_under(trigger)
        uncovered = [rel for rel in guarded if not ci_mod._pattern_hits(patterns, rel)]
        assert uncovered == [], (
            f"{trigger} path filters do not cover guarded files: {uncovered}"
        )


def test_hygiene_scanner_catches_labels_paths_and_name_while_honouring_exclusions():
    """Unit check: positives fire cleanly and documented exclusions do not false-positive."""
    assert scan_lines("README.md", f"Approved by the {_LBL_1.title()} yesterday.")
    assert scan_lines("tests/x.py", f"def test_{_LBL_1}_mode(): pass")
    assert scan_lines("notes/x.md", f"Next {_LBL_2} picks it up.")
    assert scan_lines("notes/x.md", f"Three {_LBL_2}s agreed.")
    assert scan_lines("notes/x.md", f"A five-{_LBL_2} panel.")
    assert scan_lines("CHANGELOG.md", f"The registered {_LBL_3} failed.")
    assert scan_lines("notes/x.md", f"Via {_LBL_4} and {_LBL_5.title()}.")
    assert scan_lines("tools/x.py", f"P = r'{_DRV_E}\\AI\\repo'")
    assert scan_lines("tools/x.py", f"P = r'{_DRV_E}\\training\\asset.glb'")
    assert scan_lines("tools/x.py", f"P = r'{_DRV_E}\\t'")
    assert scan_lines("tools/x.py", "P = 'D" + ":/work/repo'")
    assert scan_lines("tools/x.py", "P = r'Z" + ":\\models\\clip.mp4'")
    assert scan_lines("tools/x.py", f"P = '{_DRV_C}/dev/checkout'")
    assert scan_lines("README.md", f"cd {_HOME_PFX}dev/armature")
    assert scan_lines("README.md", f"{_DRV_C}\\{'Us' + 'ers'}\\dev\\armature")
    assert scan_lines(
        "CLAUDE.md",
        f"| **Role** ({_PNAME.title()}) |",
        include_labels_and_paths=False,
    )

    clean_lines = [
        "output directory and subdirectories",
        "el directorio de salida",
        f"PyPI {_TRUSTED.title()} {_LBL_3.title()} OIDC",
        "smikeline non_matching_token",
        "a seated posture and seating arrangement",
        'except Exception as e:' + chr(92) + 'n pass',
        'if "else:' + chr(92) + 'n" in src:',
        rf"{_DRV_C}\Program Files\Blender Foundation\Blender 5.2\blender.exe",
        rf"{_DRV_C}\Windows\Fonts\arial.ttf",
        f"{_DRV_C}/elsewhere/x",
    ]
    assert scan_lines("README.es.md", "\n".join(clean_lines)) == []
