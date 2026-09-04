"""Every seed registration carries a machine-readable ceiling.

Wave 3, F-dbc4ed63. Six of the eight `specs/*seeds.json` files carried a `ceiling` key
(E08, E10, E11, E12, E13, E14) and `specs/E09-seeds.json` and `specs/E09-A3-seeds.json`
carried none. Where present the value was free prose ("SIX submissions total, amended
4 -> 6 by ..."), and no tool under `tools/` read the key — while `seeds` and `allocation`,
its machine-readable siblings, are both consumed and gated. CLAUDE.md makes the credit
ceiling a per-spec obligation and records that spent credits have no compensator, so the
one unrecoverable resource in this repo was bounded by a string nothing could parse.

The prose is not deleted. It moves into `ceiling.note` verbatim, and the number a
submission step can count against sits beside it in `ceiling.submissions`.
"""

import glob
import json
import os

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED_SPECS = sorted(glob.glob(os.path.join(REPO, "specs", "*seeds.json")))


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def test_the_seed_specs_are_found_at_all():
    """A glob that matches nothing would make every check below vacuously green."""
    assert len(SEED_SPECS) >= 8


@pytest.mark.parametrize("path", SEED_SPECS, ids=os.path.basename)
def test_every_seed_spec_carries_seeds_allocation_and_a_numeric_ceiling(path):
    doc = _load(path)
    assert isinstance(doc.get("seeds"), list) and doc["seeds"], "no seeds"
    assert isinstance(doc.get("allocation"), dict) and doc["allocation"], "no allocation"
    ceiling = doc.get("ceiling")
    assert isinstance(ceiling, dict), "ceiling is not machine-readable"
    assert isinstance(ceiling.get("submissions"), int), "ceiling.submissions is not an int"
    assert ceiling["submissions"] > 0
    assert isinstance(ceiling.get("note"), str) and ceiling["note"].strip(), (
        "the prose that used to BE the ceiling must survive in ceiling.note")


@pytest.mark.parametrize("path", SEED_SPECS, ids=os.path.basename)
def test_the_ceiling_is_at_least_the_number_of_seeds_it_registers(path):
    """A ceiling below the list it governs would be a bound the spec's own allocation
    breaks on its first pass. E12 and E13 deliberately run each seed on more than one arm,
    so the relation is >=, not ==."""
    doc = _load(path)
    assert doc["ceiling"]["submissions"] >= len(doc["seeds"]), (
        f"{os.path.basename(path)} registers {len(doc['seeds'])} seed(s) under a ceiling "
        f"of {doc['ceiling']['submissions']}")


@pytest.mark.parametrize("path", SEED_SPECS, ids=os.path.basename)
def test_every_registered_seed_has_an_allocation_row(path):
    doc = _load(path)
    missing = [s for s in doc["seeds"] if str(s) not in doc["allocation"]]
    assert missing == [], f"seeds with no allocation row: {missing}"
