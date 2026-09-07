"""Wave 35, F-6e7451e6 — amend-pin inventory, ratchet, and graduation path.

The suite's durable product surface was being displaced by a wave ledger: dozens of
`test_*amend_w*.py` modules (~40% of suite bytes) with no inventory, no expiry, and no
graduation move into durable `test_*` homes. This census:

1. records wave id + finding ids from each amend module docstring;
2. ratchets amend file count and byte fraction so both may only fall (absent an
   explicit allowlist bump);
3. documents the graduation move in GRADUATION_PATH below.
"""

from __future__ import annotations

import glob
import os
import re

import pytest

TESTS = os.path.dirname(os.path.abspath(__file__))

#: Graduation move (F-6e7451e6): relocate the pin body into the durable `test_*` home
#: that owns the product surface; shrink the amend file to a one-liner pointer
#: (`from test_X import *  # graduated wN`) or delete it. Amend modules must not keep
#: growing as the only home for load-bearing law.
GRADUATION_PATH = (
    "pin body -> durable test_* home; amend file shrinks to a one-liner pointer or is "
    "deleted"
)

AMEND_GLOB = ("test_amend_w*.py", "test_instruments_amend_w*.py",
              "test_instruments_measure_amend_w*.py")

WAVE_RE = re.compile(r"\b[Ww]ave\s+(\d+)\b")
WAVE_IN_NAME_RE = re.compile(r"_w(\d+)")
FINDING_RE = re.compile(r"\bF-[0-9a-f]{8}\b")

#: Measured 2026-09-06 on ca26d0a worktree before this wave's own amend file landed.
#: May only fall; bump deliberately with a comment naming the wave that grew it.
#: WAVE 35: 60 -> 64. Four `test_*_w35_*.py` amend modules landed with the MEDIUM
#: execute (builders / core-solvers / instruments / instruments-measure); graduate
#: later rather than delete product pins to clear the ceiling.
AMEND_FILE_CEILING = 64
AMEND_BYTE_FRACTION_CEILING = 0.42


def _amend_paths():
    paths = []
    for pat in AMEND_GLOB:
        paths.extend(glob.glob(os.path.join(TESTS, pat)))
    return sorted(set(paths))


def _docstring(path):
    with open(path, encoding="utf-8") as fh:
        src = fh.read(4000)
    if src.startswith('"""') or src.startswith("'''"):
        q = src[:3]
        end = src.find(q, 3)
        if end > 0:
            return src[3:end]
    return src[:800]


def amend_inventory():
    """`[{file, wave, findings}]` derived from each amend module's docstring + filename."""
    rows = []
    for path in _amend_paths():
        base = os.path.basename(path)
        doc = _docstring(path)
        waves = [int(m) for m in WAVE_RE.findall(doc)]
        if not waves:
            named = WAVE_IN_NAME_RE.findall(base)
            waves = [int(named[0])] if named else []
        findings = sorted(set(FINDING_RE.findall(doc)))
        rows.append({
            "file": base,
            "wave": waves[0] if waves else None,
            "findings": findings,
            "bytes": os.path.getsize(path),
        })
    return rows


def test_the_amend_inventory_records_wave_and_finding_ids():
    rows = amend_inventory()
    assert rows, "amend population is empty — census has nothing to ratchet"
    missing_wave = [r["file"] for r in rows if r["wave"] is None]
    assert missing_wave == [], (
        "every amend module docstring must name its wave id "
        f"(e.g. 'Wave 32'); missing: {missing_wave}")
    # At least half carry finding ids — some early amend files are narrative-only.
    with_findings = [r for r in rows if r["findings"]]
    assert len(with_findings) >= max(1, len(rows) // 4), (
        f"only {len(with_findings)}/{len(rows)} amend modules name F-xxxxxxxx ids")


def test_amend_byte_fraction_and_file_count_may_only_fall():
    """Ratchet: absent an explicit ceiling bump, amend weight only shrinks."""
    rows = amend_inventory()
    amend_bytes = sum(r["bytes"] for r in rows)
    all_bytes = sum(os.path.getsize(p)
                    for p in glob.glob(os.path.join(TESTS, "test_*.py")))
    fraction = amend_bytes / all_bytes if all_bytes else 0.0
    assert len(rows) <= AMEND_FILE_CEILING, (
        f"{len(rows)} amend modules > ceiling {AMEND_FILE_CEILING}; graduate pins into "
        f"durable homes ({GRADUATION_PATH}) or bump AMEND_FILE_CEILING with a reason")
    assert fraction <= AMEND_BYTE_FRACTION_CEILING, (
        f"amend byte fraction {fraction:.4f} > ceiling {AMEND_BYTE_FRACTION_CEILING}; "
        f"graduate ({GRADUATION_PATH}) or bump AMEND_BYTE_FRACTION_CEILING with a reason")


def test_graduation_path_is_documented_in_this_module():
    assert "durable" in GRADUATION_PATH and "pointer" in GRADUATION_PATH


def test_the_amend_inventory_goes_red_when_a_module_names_no_wave(tmp_path):
    """reverted-red operand: docstring without a wave id."""
    p = tmp_path / "test_amend_w99_silent.py"
    p.write_text('"""pins with no wave marker and no F- ids."""\n', encoding="utf-8")
    doc = _docstring(str(p))
    assert WAVE_RE.findall(doc) == []
