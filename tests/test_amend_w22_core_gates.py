"""Wave 22 (core-gates, Stage B amend #1): the tables nothing checked, the declarations
nothing counted, the containers nothing read, and the rows that could not name their node.

The wave-21 auditors measured, on `e8263a3`, that four gate surfaces state a contract in
prose and enforce none of it, and that three row families cannot say WHICH node they are
about:

  * **F-682ce228** `canon_census.CENSUS` is a hand-edited table whose docstring states the
    contract the spend helpers rest on, and no clause anywhere checks a row against it: a
    misspelled `surface:` key made `require_canon`'s `clause: checkbox` refusal
    inoperative and returned `UNGATED` for a subject that HAS a ratified surfaces file; an
    identity-only row with no `reason` returned `UNGATED` with `reason: None`; a row that
    is not a mapping raised a bare `AttributeError` from both `require_canon` and
    `resolve`, bypassing the halt contract's exit-2 branch.
  * **F-0d33958f** `normalise_graph` resolves a document declaring TWO graphs by
    wrapper-key order and records nowhere that a second declaration existed — the shape a
    ComfyUI queue/history record carries — so `verify` returned a green verdict on an API
    half while the save half loaded `causvid_x.safetensors` (BANNED, CC-BY-NC).
  * **F-ddfb61e6** an API-format entry that declares its OWN `widgets_values` has it
    DISCARDED: `_walk_nodes` synthesises widgets from `inputs.values()` alone and
    `NODE_CONTAINERS[True]` records only `('inputs', dict)`, so the BANNED file spelled
    there is neither read nor refused and `verify` RETURNED "0 of 1 component(s)
    classified, ... 1 frame(s) checked and generator-legal".
  * **F-715ecaab** `normalise_spec` validates the keys it knows and ACCEPTS every key it
    does not, at every level, and `dump_spec` writes them back into the provenance spec —
    so `camera.fov_degrees` rides beside the `fov_deg` the solvers read.
  * **F-2fa07723 / F-94cc5fe1** `hosted_enums`' 4-tuple and Gate PAIR's
    `conditioning_nodes` rows are the two row families that discard the level the walk
    yields, so a refusal on a tier that bills per node reads `node 6; node 6`.
  * **F-f2808386** five of the six functions that index a widget list positionally call a
    shift andon in their own body; `gate_s_registration` calls none, and its coverage is a
    comment plus a hand-kept dict two functions away.

Every test here is written against the operand the wave-21 auditor measured, and against
that operand's enumerated siblings. `family:` lines ride the output record.
"""

import json
import math
import os
import sys

import pytest

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

from armature_core import canon as C                       # noqa: E402
from armature_core import canon_census as CC               # noqa: E402
from armature_core import cli                              # noqa: E402
from armature_core import donor_gate as DG                 # noqa: E402
from armature_core import route_gates as RG                # noqa: E402
from armature_core import shotspec as SS                   # noqa: E402
from armature_core.errors import GateCanon, SpecError      # noqa: E402

BANNED = "causvid_x.safetensors"
BASE = "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"


# ---------------------------------------------------------------------------
# F-682ce228 — `canon_census.CENSUS` is checked against the contract its own
# docstring states, at import and again at run time.
# ---------------------------------------------------------------------------

#: The six malformed shapes, enumerated. The auditor measured the first three on
#: `e8263a3`; the other three are their siblings in the same table position — the row
#: whose `surfaces` is not a path at all, the empty path, and the subject key that is not
#: a name. Every one of them is what "adding a subject is a data change here" admits.
MALFORMED_ROWS = [
    ("not_a_mapping", {"NEWCHAR": "newchar.json"}, "row_is_not_a_mapping"),
    ("misspelled_key", {"NEWCHAR": {"surface": "newchar.json", "reason": "typo"}},
     "unknown_census_key"),
    ("identity_only_without_reason", {"NEWCHAR": {"surfaces": None}},
     "hole_without_a_reason"),
    ("identity_only_blank_reason", {"NEWCHAR": {"surfaces": None, "reason": "  "}},
     "hole_without_a_reason"),
    ("surfaces_not_a_path", {"NEWCHAR": {"surfaces": 7}}, "surfaces_is_not_a_path"),
    ("surfaces_empty_path", {"NEWCHAR": {"surfaces": ""}}, "surfaces_is_not_a_path"),
]


@pytest.mark.parametrize("label,table,clause",
                         MALFORMED_ROWS, ids=[m[0] for m in MALFORMED_ROWS])
def test_a_malformed_census_row_refuses_by_name(label, table, clause):
    """RED on base: `gate_census_table` did not exist. The misspelled-key row returned
    `{'verdict': 'UNGATED', 'clause': 'escape'}` from `require_canon(no_canon=True)` for a
    subject that HAS a surfaces file — the `clause: 'checkbox'` refusal inoperative
    because `rec.get('surfaces')` read None — and the non-mapping row raised a bare
    `AttributeError`, which is not an `ArmatureError`."""
    with pytest.raises(GateCanon) as exc:
        CC.gate_census_table(table)
    ev = exc.value.evidence
    assert ev["clause"] == clause
    assert ev["gate"] == "CANON" and ev["andon"] == "GateCanon"
    assert ev["subject"] == "NEWCHAR"


def test_the_table_itself_and_its_keys_are_bounded_too():
    """The two shapes above the row: a census that is not a mapping at all, and a subject
    key that is not a name. A table read with `.get` answers None to every question."""
    with pytest.raises(GateCanon) as exc:
        CC.gate_census_table([("NEWCHAR", {"surfaces": None, "reason": "x"})])
    assert exc.value.evidence["clause"] == "census_is_not_a_mapping"
    with pytest.raises(GateCanon) as exc2:
        CC.gate_census_table({7: {"surfaces": None, "reason": "x"}})
    assert exc2.value.evidence["clause"] == "subject_is_not_a_name"


def test_the_shipped_census_passes_its_own_gate_and_the_gate_runs_at_import():
    """The three rows in the tree today are well formed — this is the guard direction
    unbounded, not a live escape — and the andon runs at import time for the reason
    `route_gates.gate_alias_table()` does: a table mirroring a document loses rows when
    the document is re-fetched."""
    assert CC.gate_census_table() is CC.CENSUS
    src = open(os.path.join(TOOLS, "armature_core", "canon_census.py"),
               encoding="utf-8").read()
    assert "\ngate_census_table()\n" in src, (
        "the import-time call is the half a run-time-only check does not have")


@pytest.mark.parametrize("label,table,clause",
                         MALFORMED_ROWS, ids=[m[0] for m in MALFORMED_ROWS])
def test_the_spend_helpers_refuse_a_table_mutated_at_run_time(label, table, clause):
    """The auditor's own operand: the three readings were taken THROUGH `require_canon`'s
    `census=` parameter, so the import-time andon alone would not have caught them.
    `resolve` is the sibling — it raised the same bare `AttributeError` on the non-mapping
    row — and `gate_write` forwards into `require_canon`."""
    for call in (
        lambda: C.require_canon("NEWCHAR", "a prompt", no_canon=True, census=table),
        lambda: C.require_canon("NEWCHAR", "a prompt", census=table),
        lambda: C.gate_write("NEWCHAR", "a prompt", no_canon=True, census=table),
        lambda: C.resolve("NEWCHAR", census=table),
    ):
        with pytest.raises(GateCanon) as exc:
            call()
        assert exc.value.evidence["clause"] == clause


def test_the_misspelled_row_no_longer_reaches_ungated():
    """The measured consequence, stated as its own test: a subject that HAS a ratified
    surfaces file used to walk out of `--no-canon` with `verdict: UNGATED` because the
    key that carries the path was spelled `surface`."""
    table = {"NEWCHAR": {"surface": "newchar.json", "reason": "typo"}}
    with pytest.raises(GateCanon) as exc:
        C.require_canon("NEWCHAR", "a prompt", no_canon=True, census=table)
    assert exc.value.evidence["clause"] == "unknown_census_key"
    assert exc.value.evidence["key"] == "surface"
    assert "surfaces" in exc.value.evidence["known_keys"]


REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _halt_line(argv, prefix, tool, expect_code=2):
    """Drive a tool's REAL `__main__` block in a subprocess and READ the halt record.

    Wave-18 rule 4: the fix is not landed until the printed line has been read — the
    class, the clause, the evidence keys. Returns the parsed sentinel payload.
    """
    import subprocess

    env = dict(os.environ, PYTHONPATH=os.path.join(REPO, "tools"))
    proc = subprocess.run([sys.executable, os.path.join(REPO, "tools", tool)] + argv,
                          capture_output=True, text=True, env=env, cwd=REPO)
    assert proc.returncode == expect_code, proc.stdout + proc.stderr
    halts = [ln for ln in proc.stdout.splitlines() if ln.startswith(prefix + " ")]
    assert len(halts) == 1, proc.stdout + proc.stderr
    return json.loads(halts[0][len(prefix) + 1:])


def test_the_canon_census_refusal_reaches_the_printed_halt_record(tmp_path):
    """The halt line READ, not asserted about in-process (wave-18 rule 4). A malformed
    census handed to `canon_gate.py --census` must leave the process through the
    `CANON_GATE_HALT` sentinel with exit 2, carrying the clause — not as an
    `AttributeError` traceback at exit 1, which is what a non-mapping row produced."""
    census = tmp_path / "bad-census.json"
    census.write_text(json.dumps({"NEWCHAR": "newchar.json"}), encoding="utf-8")
    payload = _halt_line(["--census", str(census), "resolve", "--subject", "NEWCHAR"],
                         "CANON_GATE_HALT", "canon_gate.py")
    assert payload["error"] == "GateCanon"
    assert payload["evidence"]["clause"] == "row_is_not_a_mapping"
    assert payload["evidence"]["gate"] == "CANON"
    assert payload["evidence"]["subject"] == "NEWCHAR"


# ---------------------------------------------------------------------------
# F-c77f6cce — `out_dir` was a parameter of both spend helpers, forwarded between
# them, and read by neither. It is now a check.
# ---------------------------------------------------------------------------

def test_out_dir_is_read_by_the_gate_that_is_handed_it(tmp_path):
    """RED on base: `grep -n out_dir tools/armature_core/canon.py` returned exactly four
    lines — two signatures, one docstring negative and one forward — and no statement in
    either body read the value, while `tools/canon_gate.py:75` hands it a real directory.
    A parameter is a promise about what a function looks at.

    The check is the one the finding names: a re-run may not write into a HALF-FINISHED
    spend. The negative in the docstring stands — this still never creates the directory."""
    out = tmp_path / "half-finished"
    out.mkdir()
    (out / "payload.json").write_text("{}", encoding="utf-8")
    for call in (C.require_canon, C.gate_write):
        with pytest.raises(GateCanon) as exc:
            call("PERFORMER", "a prompt", no_canon=True, out_dir=str(out))
        ev = exc.value.evidence
        assert ev["clause"] == "out_dir_not_empty"
        assert ev["out_dir"] == str(out)
        assert ev["entries"] == ["payload.json"]


def test_out_dir_none_and_an_absent_or_empty_directory_are_unchanged(tmp_path):
    """The siblings of the operand, enumerated: `out_dir=None` (the shape every test in
    `test_canon.py` uses), a path that does not exist (the shape `canon_gate.py` uses
    before mkdir), and an existing but EMPTY directory — a re-run that got as far as the
    mkdir and no further is not a half-finished spend."""
    empty = tmp_path / "empty"
    empty.mkdir()
    for out in (None, str(tmp_path / "not-yet"), str(empty)):
        ev = C.require_canon("PERFORMER", "a prompt", no_canon=True, out_dir=out)
        assert ev["verdict"] == "UNGATED"
    assert not (tmp_path / "not-yet").exists(), "the gate still creates nothing"


def test_a_file_standing_where_out_dir_should_be_is_refused_by_name(tmp_path):
    """The third shape of the same operand: the path exists and is not a directory at all,
    so `os.listdir` would raise `NotADirectoryError` — not an `ArmatureError`."""
    f = tmp_path / "not-a-dir"
    f.write_text("x", encoding="utf-8")
    with pytest.raises(GateCanon) as exc:
        C.gate_write("PERFORMER", "a prompt", no_canon=True, out_dir=str(f))
    assert exc.value.evidence["clause"] == "out_dir_is_not_a_directory"


def test_the_out_dir_refusal_reaches_the_printed_halt_record(tmp_path):
    """The halt line READ. `canon_gate.py spend --no-canon --subject PERFORMER --out <a
    directory holding a file>` leaves through `CANON_GATE_HALT` at exit 2 with the clause,
    the path and the entries — where on base it printed `[canon] UNGATED: PERFORMER` and
    `CANON_GATE_OK` over a directory already holding another run's payload."""
    out = tmp_path / "half-finished"
    out.mkdir()
    (out / "payload.json").write_text("{}", encoding="utf-8")
    payload = _halt_line(["spend", "--no-canon", "--subject", "PERFORMER",
                          "--prompt", "a prompt", "--out", str(out)],
                         "CANON_GATE_HALT", "canon_gate.py")
    assert payload["error"] == "GateCanon"
    assert payload["evidence"]["clause"] == "out_dir_not_empty"
    assert payload["evidence"]["entries"] == ["payload.json"]
