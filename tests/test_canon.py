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
    with pytest.raises(GateCanon,
                       match=r"\[CANON\] no subject: a spend with no census id has no"):
        C.resolve(None)
    try:
        C.resolve(None)
    except Exception as err:
        assert not isinstance(err, AssertionError)


# =====================================================================================
# W3 amend — four clauses in canon.py that a plural, a wrapper, an empty string or a
# field name could walk past.
# =====================================================================================


# --- an empty prompt is no prompt (F-60553de0) ------------------------------------

def test_cover_refuses_an_empty_prompt():
    """`cover` rejected None and nothing else. Measured: on a doc whose only ratified
    occupant carries no phrase, `cover(doc, '')` returned COVERED with missing=[] and
    residue=[] — both directions green having examined zero characters of prompt.
    `residue('')` is [] for ANY doc, so the reverse direction alone is vacuous on empty
    text whatever the occupants look like. An empty prompt is no prompt, which is the
    argument the None clause already makes."""
    with pytest.raises(GateCanon) as exc:
        C.cover(load_probe(), "")
    assert exc.value.evidence["clause"] == "empty_prompt"
    with pytest.raises(GateCanon) as exc:
        C.cover(load_probe(), "   \n\t ")
    assert exc.value.evidence["clause"] == "empty_prompt"


def test_a_bare_only_ratified_doc_cannot_arm(tmp_path):
    """`require_canon`'s tripwire is "zero ratified prompt occupants: a check that
    cannot fail is not a check". `is_named` returns True for kind='bare', so a doc whose
    ratified occupants were all bare satisfied the tripwire while carrying nothing the
    router could check."""
    src = load_probe()
    for s in src["surfaces"]:
        if s.get("occupant"):
            s["occupant"].pop("phrase", None)
            s["occupant"]["kind"] = "bare"
    path = tmp_path / "bare.json"
    path.write_text(json.dumps(src), encoding="utf-8")
    census = {"BARE": {"surfaces": "bare.json"}}
    with pytest.raises(GateCanon) as exc:
        C.require_canon("BARE", COVERED, census=census, search_roots=[str(tmp_path)])
    assert exc.value.evidence["clause"] == "unratified_only"


def test_coverage_counts_bare_occupants_separately_rather_than_losing_them(tmp_path):
    src = load_probe()
    src["surfaces"][1]["occupant"] = {"id": "P2", "kind": "bare", "ratified": True}
    ev = C.coverage(src)
    assert ev["ratified"] == 1
    assert ev["ratified_bare"] == 1
    assert ev["named"] == 2


# --- the reverse direction reads the shape it was handed (F-85d2b7a3) -------------

_API_TEXT = "a black plate warrior"


def _text_graph():
    return {"6": {"class_type": "CLIPTextEncode",
                  "inputs": {"text": _API_TEXT, "clip": ["5", 0]}}}


def test_texts_are_found_through_the_standard_prompt_wrapper():
    """`nodes = graph.values() if all(isinstance(v, dict) ...) else []` — ONE non-dict
    top-level key empties the result. Measured: the bare graph returned the text; the
    same graph under {'prompt': ...} returned []; the same graph plus last_node_id=12
    returned []. A caller cannot tell "this graph carries no text" from "this shape was
    not recognised", and the prompt it hands Gate CANON is what the check is about."""
    assert C.texts_from_api_graph({"prompt": _text_graph()}) == [_API_TEXT]
    assert C.texts_from_api_graph({"workflow": _text_graph()}) == [_API_TEXT]


def test_a_scalar_sibling_key_does_not_abandon_the_walk():
    g = dict(_text_graph(), last_node_id=12)
    assert C.texts_from_api_graph(g) == [_API_TEXT]


def test_a_shape_with_no_nodes_at_all_raises_rather_than_returning_empty():
    with pytest.raises(GateCanon) as exc:
        C.texts_from_api_graph({"last_node_id": 12, "version": 0.4})
    assert exc.value.evidence["clause"] == "unrecognised_graph"
    with pytest.raises(GateCanon,
                       match=r"\[CANON\] a graph must be an object, got list; an"):
        C.texts_from_api_graph(["not", "a", "graph"])


def test_a_recognised_graph_carrying_no_text_still_returns_empty():
    """The other direction: "no text here" is a real answer and must not raise."""
    g = {"1": {"class_type": "UNETLoader", "inputs": {"unet_name": "x.safetensors"}}}
    assert C.texts_from_api_graph(g) == []


# --- blocked_additions means blocked (F-98d851e3) ---------------------------------

def _blocked_doc():
    doc = load_probe()
    doc["blocked_additions"] = [{"id": "B1", "phrase": "glowing red halo"}]
    return doc


def test_a_blocked_addition_is_refused_not_licensed():
    """The field's only behaviour was to PERMIT exactly the text its name says is
    blocked: `licensed_phrases` collected every blocked phrase and `residue` stripped it
    before the reverse direction looked for leftovers. Measured: cover(doc, 'black plate
    glowing red halo') returned COVERED with residue []."""
    doc = _blocked_doc()
    assert "glowing red halo" not in C.licensed_phrases(doc)
    with pytest.raises(GateCanon) as exc:
        C.cover(doc, COVERED + ", glowing red halo")
    assert exc.value.evidence["clause"] == "blocked_addition"
    assert exc.value.evidence["blocked"][0]["phrase"] == "glowing red halo"


def test_a_blocked_phrase_absent_from_the_prompt_changes_nothing():
    assert C.cover(_blocked_doc(), COVERED)["verdict"] == "COVERED"


def test_a_blocked_phrase_is_not_quietly_turned_into_residue():
    """If the field had merely been dropped from `licensed_phrases`, the phrase would
    surface as unlicensed residue and the message would say "unlicensed" about text the
    doc names explicitly. The clause names it."""
    with pytest.raises(GateCanon) as exc:
        C.cover(_blocked_doc(), COVERED + ", glowing red halo")
    assert "blocked" in str(exc.value).lower()


# --- forbidden words are forbidden in the plural too (F-eb8508e1) -----------------
#
# The forbidden clause raises BEFORE the residue clause, so these fixtures license the
# word under a legal clause too. That keeps each case testing the one thing it names:
# without the licence, "sleeveless" would raise as unlicensed residue and the negative
# case would prove nothing about the forbidden matcher.


def _forbidden_doc(*words, licensed=()):
    doc = load_probe()
    doc["surfaces"][0]["occupant"]["forbidden"] = list(words)
    for i, phrase in enumerate(licensed):
        doc["legal_clauses"].append({"id": f"LX{i}", "phrase": phrase, "class": "style"})
    return doc


def test_a_forbidden_word_fires_in_the_plural():
    """`\b + word + \b` fires on 'gauntlet' and not on 'gauntlets', so a canon that
    forbids a garment feature passed any prompt naming it in the plural and Gate CANON
    reported COVERED."""
    doc = _forbidden_doc("gauntlet", licensed=("gauntlets",))
    with pytest.raises(GateCanon) as exc:
        C.cover(doc, COVERED + ", gauntlets")
    assert exc.value.evidence["forbidden"][0]["word"] == "gauntlet"


def test_sleeve_fires_on_sleeves_and_not_on_sleeveless():
    """The hand-written SLEEVE special case was inert — the trailing \b already
    prevented a match inside 'sleeveless', so (?!less) changed nothing — and it kept a
    hard-coded single word inside a general mechanism. Both readings are now one rule."""
    with pytest.raises(GateCanon,
                       match=r"\[CANON\] forward cover failed: forbidden words present"):
        C.cover(_forbidden_doc("sleeve", licensed=("long sleeves",)),
                COVERED + ", long sleeves")
    ok = C.cover(_forbidden_doc("sleeve", licensed=("sleeveless",)),
                 COVERED + ", sleeveless")
    assert ok["verdict"] == "COVERED"
    assert not hasattr(C, "SLEEVE")


def test_the_singular_still_fires():
    with pytest.raises(GateCanon,
                       match=r"\[CANON\] forward cover failed: forbidden words present"):
        C.cover(_forbidden_doc("sleeve", licensed=("a sleeve",)), COVERED + ", a sleeve")


def test_a_forbidden_word_does_not_fire_inside_a_longer_word():
    """The direction the plural stem must not break: 'light' is not 'lighting', and
    'even lighting' is a licensed clause of the probe fixture."""
    assert C.cover(_forbidden_doc("light"), COVERED)["verdict"] == "COVERED"


# =====================================================================================
# W6 amend — the forbidden clause, both inflections and every surface
# =====================================================================================


@pytest.mark.parametrize("canon_word,prompt_word", [
    ("gauntlet", "gauntlets"),      # singular canon, plural prompt — closed in W3
    ("gauntlets", "gauntlet"),      # plural canon, singular prompt — the open half
    ("gauntlets", "gauntlets"),
    ("gauntlet", "gauntlet"),
    ("boots", "boot"),
    ("greaves", "greave"),
    ("gloves", "glove"),
])
def test_a_forbidden_word_fires_in_both_inflections(canon_word, prompt_word):
    """Measured 2026-09-03: forbidden 'gauntlet' fired on "wearing gauntlets" (True) and
    forbidden 'gauntlets' did NOT fire on "wearing a gauntlet" (False). The plural is the
    natural form a canon author writes for gauntlets, boots, gloves, greaves and
    pauldrons, so the refusal list that reads most naturally was the one that passed."""
    doc = _forbidden_doc(canon_word, licensed=(prompt_word,))
    with pytest.raises(GateCanon) as exc:
        C.cover(doc, COVERED + ", " + prompt_word)
    assert exc.value.evidence["forbidden"][0]["word"] == canon_word


@pytest.mark.parametrize("canon_word,prompt", [
    ("light", "even lighting"),          # not a stem of a longer word
    ("sleeve", "sleeveless"),            # the boundary still holds
    ("cape", "a caped figure"),
])
def test_the_stem_normalisation_does_not_reach_inside_a_longer_word(canon_word, prompt):
    doc = _forbidden_doc(canon_word, licensed=(prompt,))
    assert C.cover(doc, COVERED + ", " + prompt)["verdict"] == "COVERED"


def test_a_word_that_genuinely_ends_in_s_keeps_its_plural():
    """Normalising the canon side must not cost the prompt side: 'dress' -> 'dresses'."""
    doc = _forbidden_doc("dress", licensed=("two dresses",))
    with pytest.raises(GateCanon,
                       match=r"\[CANON\] forward cover failed: forbidden words present"):
        C.cover(doc, COVERED + ", two dresses")


def _mixed_ratification_doc(word="gauntlet"):
    """A ratified torso occupant and an UNRATIFIED hand occupant carrying a refusal."""
    doc = load_probe()
    hole = next(s for s in doc["surfaces"] if s["id"] == "hand_L")
    hole["occupant"] = {"kind": "bare", "forbidden": [word], "ratified": False}
    doc["legal_clauses"].append({"id": "LX9", "phrase": word, "class": "style"})
    return doc


def test_a_refusal_on_an_unratified_occupant_is_still_read():
    """Measured 2026-09-03: with a ratified torso occupant and an unratified hands
    occupant carrying forbidden ['gauntlet'], cover(doc, "... gauntlet") returned COVERED
    with forbidden []; flipping only that occupant's ratified flag made the same prompt
    raise. `blocked_additions`, the doc-level refusal list, is checked regardless of any
    ratification, so the two refusal mechanisms disagreed with each other."""
    doc = _mixed_ratification_doc()
    with pytest.raises(GateCanon) as exc:
        C.cover(doc, COVERED + ", gauntlet")
    hit = exc.value.evidence["forbidden"][0]
    assert hit["word"] == "gauntlet"
    assert hit["surface"] == "hand_L"
    assert hit["ratified"] is False


def test_a_ratified_refusal_still_records_which_side_of_the_line_it_came_from():
    doc = _forbidden_doc("gauntlet", licensed=("gauntlet",))
    with pytest.raises(GateCanon) as exc:
        C.cover(doc, COVERED + ", gauntlet")
    assert exc.value.evidence["forbidden"][0]["ratified"] is True


def test_a_phrase_on_an_unratified_occupant_is_still_NOT_demanded():
    """The other side of the line, so the fix does not turn ratification off: a PHRASE is
    a claim about the occupant and stays behind ratification; a refusal is a claim about
    the prompt and does not."""
    doc = load_probe()
    hole = next(s for s in doc["surfaces"] if s["id"] == "hand_L")
    hole["occupant"] = {"kind": "prompt", "phrase": "a brass ring", "ratified": False}
    assert C.cover(doc, COVERED)["verdict"] == "COVERED"
