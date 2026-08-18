"""Canon statement, both-direction router, fail-closed spend.

Each check is written against the specific way the code would be wrong
if that check were missing.
"""

import json
import os

import pytest

from armature_core import canon as C
from armature_core import canon_census
from armature_core.errors import GateCanon
from armature_core.sitelist import ALL_NAMES

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "canon")
PROBE_PATH = os.path.join(FIXTURES, "probe.surfaces.json")
TEST_CENSUS = {
    "PROBE": {"surfaces": "probe.surfaces.json"},
    "PERFORMER": {
        "surfaces": None,
        "reason": "identity exists; no surfaces file",
    },
}
COVERED = (
    "a wire figure with a featureless head in an empty studio, even lighting"
)


def load_probe():
    return C.load(PROBE_PATH)


def resolve_probe():
    return C.resolve("PROBE", census=TEST_CENSUS, search_roots=[FIXTURES])


def test_probe_fixture_loads_and_the_hole_is_a_row():
    """An element list cannot show what it omitted. The hole has an id."""
    doc = load_probe()
    ids = [s["id"] for s in doc["surfaces"]]
    assert ids == ["torso", "head", "hand_L"]
    hole = next(s for s in doc["surfaces"] if s["id"] == "hand_L")
    assert hole["occupant"] is None


def test_coverage_counts_the_hole_in_the_denominator():
    ev = C.coverage(load_probe())
    assert ev["prompt_surfaces"] == 3
    assert ev["named"] == 2
    assert ev["ratified"] == 2
    assert ev["holes"] == ["hand_L"]
    assert ev["named_coverage"] == pytest.approx(2 / 3)
    assert ev["ratified_coverage"] == pytest.approx(2 / 3)


def test_a_duplicate_surface_id_raises_on_load(tmp_path):
    """The row key must be unique or a hole can hide under a twin."""
    src = load_probe()
    src["surfaces"].append(dict(src["surfaces"][0]))
    path = tmp_path / "dup.json"
    path.write_text(json.dumps(src), encoding="utf-8")
    with pytest.raises(GateCanon) as exc:
        C.load(str(path))
    assert "duplicate" in str(exc.value)


def test_a_bone_not_on_the_sitelist_raises_on_load(tmp_path):
    """The spatial half that this tree has and facet did not: sitelist is a census."""
    src = load_probe()
    src["surfaces"][0]["spatial"] = {"kind": "bone", "ref": "torso_bone"}
    path = tmp_path / "badbone.json"
    path.write_text(json.dumps(src), encoding="utf-8")
    with pytest.raises(GateCanon) as exc:
        C.load(str(path))
    assert "torso_bone" in str(exc.value)
    assert "torso_bone" not in ALL_NAMES
    assert exc.value.evidence["clause"] == "unknown_bone"


def test_every_probe_bone_is_on_the_sitelist():
    """The fixture itself would be a lie if it named a bone the rig does not carry."""
    for s in load_probe()["surfaces"]:
        spatial = s.get("spatial") or {}
        if spatial.get("kind") == "bone":
            assert spatial["ref"] in ALL_NAMES


def test_schema_above_max_is_a_stale_consumer(tmp_path):
    src = load_probe()
    src["schema"] = C.SCHEMA_MAX + 1
    path = tmp_path / "future.json"
    path.write_text(json.dumps(src), encoding="utf-8")
    with pytest.raises(GateCanon) as exc:
        C.load(str(path))
    assert "stale consumer" in str(exc.value)


def test_missing_legal_clauses_refuses_on_load(tmp_path):
    """Reverse unarmed is no answer. Schema 1 requires the key."""
    src = load_probe()
    del src["legal_clauses"]
    path = tmp_path / "nolegal.json"
    path.write_text(json.dumps(src), encoding="utf-8")
    with pytest.raises(GateCanon) as exc:
        C.load(str(path))
    assert exc.value.evidence["clause"] == "no_legal_clauses"


def test_cover_passes_on_the_licensed_prompt():
    ev = C.cover(load_probe(), COVERED)
    assert ev["verdict"] == "COVERED"
    assert ev["residue"] == []


def test_cover_refuses_a_missing_ratified_phrase():
    """Forward: thin prompt. The direction that finds a hole in the text."""
    thin = "a wire figure in an empty studio, even lighting"
    with pytest.raises(GateCanon) as exc:
        C.cover(load_probe(), thin)
    assert "featureless head" in str(exc.value)
    assert exc.value.evidence["missing"][0]["surface"] == "head"


def test_cover_refuses_a_negated_phrase():
    """'without a wire figure' is not coverage."""
    text = "without a wire figure, a featureless head, empty studio, even lighting"
    with pytest.raises(GateCanon) as exc:
        C.cover(load_probe(), text)
    assert exc.value.evidence["negated"]


def test_cover_refuses_unlicensed_residue():
    """Reverse: the direction that discriminated in facet. A gold necklace is not licensed."""
    text = COVERED + ", gold necklace"
    with pytest.raises(GateCanon) as exc:
        C.cover(load_probe(), text)
    assert "gold" in exc.value.evidence["residue"]
    assert "necklace" in exc.value.evidence["residue"]


def test_cover_does_not_require_a_phrase_for_a_hole():
    """hand_L is a row with no occupant. Forward does not invent a phrase for it."""
    ev = C.cover(load_probe(), COVERED)
    assert "hand_L" in ev["holes"]
    assert ev["verdict"] == "COVERED"


def test_resolve_silence_is_a_refuse():
    with pytest.raises(GateCanon) as exc:
        C.resolve("", census=TEST_CENSUS, search_roots=[FIXTURES])
    assert exc.value.evidence["clause"] == "missing_subject"


def test_resolve_unknown_subject_names_the_census():
    with pytest.raises(GateCanon) as exc:
        C.resolve("GALLEON", census=TEST_CENSUS, search_roots=[FIXTURES])
    assert exc.value.evidence["clause"] == "unknown_subject"
    assert "PROBE" in exc.value.evidence["known"]


def test_resolve_identity_only_refuses_without_the_escape():
    with pytest.raises(GateCanon) as exc:
        C.resolve("PERFORMER", census=TEST_CENSUS, search_roots=[FIXTURES])
    assert exc.value.evidence["clause"] == "identity_only"


def test_no_canon_on_a_subject_with_surfaces_is_the_checkbox():
    with pytest.raises(GateCanon) as exc:
        C.require_canon("PROBE", COVERED, no_canon=True,
                        census=TEST_CENSUS, search_roots=[FIXTURES])
    assert exc.value.evidence["clause"] == "checkbox"


def test_no_canon_on_identity_only_announces_ungated():
    ev = C.require_canon("PERFORMER", "anything at all", no_canon=True,
                         census=TEST_CENSUS, search_roots=[FIXTURES])
    assert ev["verdict"] == "UNGATED"
    assert "UNGATED" in ev["announcement"]


def test_no_canon_without_a_subject_is_a_skip_flag():
    with pytest.raises(GateCanon) as exc:
        C.require_canon(None, COVERED, no_canon=True,
                        census=TEST_CENSUS, search_roots=[FIXTURES])
    assert exc.value.evidence["clause"] == "escape_no_subject"


def test_zero_ratified_occupants_refuse(tmp_path):
    """A file that cannot fail is not a check."""
    src = load_probe()
    for s in src["surfaces"]:
        if s.get("occupant"):
            s["occupant"]["ratified"] = False
    path = tmp_path / "draft.json"
    path.write_text(json.dumps(src), encoding="utf-8")
    census = {"DRAFT": {"surfaces": "draft.json"}}
    with pytest.raises(GateCanon) as exc:
        C.require_canon("DRAFT", COVERED, census=census, search_roots=[str(tmp_path)])
    assert exc.value.evidence["clause"] == "unratified_only"


def test_require_canon_on_probe_with_covered_prompt_arms():
    ev = C.require_canon("PROBE", COVERED,
                         census=TEST_CENSUS, search_roots=[FIXTURES])
    assert ev["verdict"] == "ARMED"


def test_production_performer_is_identity_only():
    """The live staged figure has no ratified surfaces file. That is a row."""
    rec = canon_census.row("PERFORMER")
    assert rec is not None
    assert rec["surfaces"] is None
    with pytest.raises(GateCanon) as exc:
        C.resolve("PERFORMER")
    assert exc.value.evidence["clause"] == "identity_only"


def test_production_escape_on_performer_ungates():
    ev = C.require_canon("PERFORMER", "anything", no_canon=True)
    assert ev["verdict"] == "UNGATED"


def test_gate_canon_is_not_an_assertionerror():
    """-O deletes assert. A gate that became an AssertionError would vanish."""
    with pytest.raises(GateCanon):
        C.resolve(None)
    try:
        C.resolve(None)
    except Exception as err:
        assert not isinstance(err, AssertionError)
