"""Which subjects have a surfaces file, as DATA.

A subject absent from this table has no answer. A subject whose
``surfaces`` is None has identity and no file — the escape
``--no-canon --subject NAME`` is the only way a spend of that name
proceeds, and it announces itself. ``--no-canon`` on a subject that
HAS a surfaces path is refused: that is the checkbox trap facet
measured.

Adding a subject is a data change here. The file a path names is
loaded from the search roots ``canon.resolve`` is given; the default
root is ``tools/armature_core/canon/``.

No row here is a verdict that a figure is the right character.

⚠ **Every sentence above states a contract, and until 2026-09-05 no clause anywhere
checked a row against one.** ``canon.require_canon`` read ``rec.get("surfaces")`` and
``rec.get("reason")`` straight off the table, and ``.get`` answers ``None`` to every
question a malformed row is asked. Three readings measured on ``e8263a3`` through
``require_canon``'s own ``census=`` parameter:

  1. a row whose key is MISSPELLED — ``{"NEWCHAR": {"surface": "newchar.json",
     "reason": "typo"}}``, a subject that HAS a ratified surfaces file — returned
     ``{"verdict": "UNGATED", "clause": "escape",
     "announcement": "[canon] UNGATED: NEWCHAR"}`` from ``--no-canon``, and ``gate_write``
     returned UNGATED on it too: the ``clause: "checkbox"`` refusal is inoperative because
     ``surfaces`` reads ``None``. That refusal is the checkbox trap facet measured, and one
     letter deleted it;
  2. an identity-only row with NO ``reason`` returned the same UNGATED record with
     ``"reason": None``, so neither the announcement nor the spend record can say why the
     escape applied — "a hole is a row" was not enforced;
  3. a row that is not a mapping at all (``{"NEWCHAR": "newchar.json"}``) raised a bare
     ``AttributeError: 'str' object has no attribute 'get'`` from BOTH ``require_canon``
     and ``resolve``. ``AttributeError`` is not an ``ArmatureError``, so the halt
     contract's exit-2 six-key ``<TOOL>_HALT`` branch is bypassed and a malformed census
     reads as an unhandled crash rather than as Gate CANON refusing a table it cannot
     read.

The three rows in the tree today are well formed, so this was the guard direction
unbounded rather than a live escape; the input class is the one the paragraph above names
— "adding a subject is a data change here" — plus any caller passing its own ``census=``.

The shape of the fix is one file over: ``route_gates.gate_alias_table()`` runs at IMPORT
and again inside ``verify``, on the stated ground that a table mirroring a document loses
rows when the document is re-fetched. ``gate_census_table`` runs at import (bottom of this
module) and again from ``canon.resolve`` / ``canon.require_canon``, so a table mutated at
run time — or supplied by a caller — is refused too.
"""

from .errors import GateCanon

#: The only keys a census row may carry. A row is DATA and this is its schema; a key
#: outside this set is a misspelling or a field nothing reads, and both are refused by
#: name rather than answered `None` by `.get`.
ROW_KEYS = ("surfaces", "reason")

# Frozen builders/core-gates globs do not include armature_core/canon/*.json.
# The BLACKGUARD surfaces live here so Gate CANON ARMED is reachable without an
# unassigned file. `canon.load` reads EMBEDDED_SURFACES by basename before disk.
EMBEDDED_SURFACES = {
    "blackguard.surfaces.json": {
        "schema": 1,
        "subject": "BLACKGUARD",
        "kind": "humanoid",
        "note": (
            "E01/E02 armored warrior. Occupants from the Director identity-sheet "
            "ruling (horned helm, tattered cape, segmented pauldrons)."
        ),
        "surfaces": [
            {"id": "helm", "name": "helm",
             "spatial": {"kind": "bone", "ref": "head"},
             "occupant": {"id": "P1", "phrase": "horned helm", "kind": "prompt", "ratified": True}},
            {"id": "cape", "name": "cape",
             "spatial": {"kind": "bone", "ref": "spine"},
             "occupant": {"id": "P2", "phrase": "tattered cape", "kind": "prompt", "ratified": True}},
            {"id": "pauldron", "name": "pauldrons",
             "spatial": {"kind": "bone", "ref": "shoulder.L"},
             "occupant": {"id": "P3", "phrase": "segmented pauldrons", "kind": "prompt", "ratified": True}},
        ],
        "legal_clauses": [
            {"id": "L1", "phrase": "studio", "class": "framing"},
            {"id": "L2", "phrase": "even lighting", "class": "style"},
            {"id": "L3", "phrase": "full body in frame", "class": "framing"},
            {"id": "L4", "phrase": "plain grey seamless background", "class": "framing"},
            {"id": "L5", "phrase": "neutral studio background", "class": "framing"},
            {"id": "L6", "phrase": "stands in place", "class": "framing"},
            {"id": "L7", "phrase": "turns slowly on the spot", "class": "framing"},
            {"id": "L8", "phrase": "lone armored warrior", "class": "style"},
            {"id": "L9", "phrase": "dark plate armor", "class": "style"},
            {"id": "L10", "phrase": "heavy cloak", "class": "style"},
            {"id": "L11", "phrase": "the blackguard", "class": "style"},
        ],
    },
}

# surfaces: relative path under a search root, or None (identity-only).
# reason: why a None row is None — recorded so a hole is a row.
CENSUS = {
    "PERFORMER": {
        "surfaces": None,
        "reason": (
            "the live staged figure; identity exists; no ratified surfaces "
            "file. A Director ratifies occupants, this seat does not."
        ),
    },
    "BLACKGUARD": {
        # Package-data path under armature_core/canon/ (DEFAULT_ROOT). Director
        # identity-sheet occupants: horned helm, tattered cape, segmented pauldrons.
        "surfaces": "blackguard.surfaces.json",
        "reason": (
            "E01/E02 armored warrior. Surfaces ratified from the Director's "
            "identity-sheet ruling; --no-canon on this subject is the checkbox refuse."
        ),
    },
    "WIRE": {
        "surfaces": None,
        "reason": (
            "E03 procedural wire figure. The E03 prompt names no material "
            "and no costume on purpose."
        ),
    },
}


def _refuse(message, evidence):
    """Gate CANON's refusal for a malformed census, with the gate ids injected once.

    `canon._raise` does the same job for that module; this one lives here because the
    table lives here and importing `canon` from this module would be a cycle (`canon`
    imports `canon_census` at module scope).
    """
    raise GateCanon(message, dict(evidence, gate="CANON", andon="GateCanon"))


def gate_census_table(census=None):
    """ANDON — every row in `census` matches the contract this module's docstring states.

    Returns the table it was given (so a caller can write
    `table = gate_census_table(table)`), or raises `GateCanon` naming the subject, the
    clause and the offending value. Six clauses, one per shape the table can arrive in:

      `census_is_not_a_mapping`   the table itself; `.get`/`in` on a list answers about
                                  the wrong thing rather than raising
      `subject_is_not_a_name`     a key that is not a non-empty string; `--subject` is a
                                  command-line word and an int key can never be typed
      `row_is_not_a_mapping`      the auditor's reading (3)
      `unknown_census_key`        the auditor's reading (1) — the misspelling
      `surfaces_is_not_a_path`    a `surfaces` that is neither `None` nor a non-empty
                                  string; `os.path.join(root, 7)` is a `TypeError` from
                                  inside `resolve`'s search loop
      `hole_without_a_reason`     the auditor's reading (2) — "a hole is a row"

    It is a GATE and not a diagnostic: it raises, it is on the direction the spend helpers
    do not bound, and it has no skip flag. `--no-canon` is the escape this table governs,
    so a table that cannot be read is a table whose escape cannot be judged.
    """
    table = CENSUS if census is None else census
    if not isinstance(table, dict):
        _refuse(
            f"the canon census is a {type(table).__name__} ({table!r}), which is not the "
            f"subject-keyed mapping every spend helper reads with `.get`. A table that is "
            f"not a mapping answers None to every question rather than refusing",
            {"clause": "census_is_not_a_mapping", "subject": None,
             "census_type": type(table).__name__})
    for subject, rec in table.items():
        base = {"subject": subject, "known_keys": list(ROW_KEYS)}
        if not isinstance(subject, str) or not subject.strip():
            _refuse(
                f"the canon census carries the key {subject!r} "
                f"({type(subject).__name__}), which is not a subject name. A subject is "
                f"the word an operator types after `--subject`, so a key that cannot be "
                f"typed can never be matched and the row it guards is unreachable",
                dict(base, clause="subject_is_not_a_name",
                     key_type=type(subject).__name__))
        if not isinstance(rec, dict):
            _refuse(
                f"census row {subject!r} is a {type(rec).__name__} ({rec!r}), not a "
                f"mapping. Every reader of this table calls `.get` on the row, so a "
                f"string row raises `AttributeError` — not an `ArmatureError`, so the "
                f"halt contract's exit-2 receipt branch is bypassed and a malformed "
                f"census reads as an unhandled crash",
                dict(base, clause="row_is_not_a_mapping",
                     row_type=type(rec).__name__, row=repr(rec)))
        unknown = sorted(k for k in rec if k not in ROW_KEYS)
        if unknown:
            _refuse(
                f"census row {subject!r} carries {unknown!r}, which this table has no "
                f"reader for; the keys are {list(ROW_KEYS)}. A misspelled `surfaces` is "
                f"not a row with an extra field — it is a subject whose surfaces path is "
                f"invisible, and `--no-canon` on it then returns UNGATED because "
                f"`rec.get('surfaces')` reads None. That is the checkbox trap the "
                f"`clause: checkbox` refusal exists to close",
                dict(base, clause="unknown_census_key", key=unknown[0],
                     unknown_keys=unknown, row_keys=sorted(map(str, rec))))
        surfaces = rec.get("surfaces")
        if surfaces is not None and (not isinstance(surfaces, str)
                                     or not surfaces.strip()):
            _refuse(
                f"census row {subject!r} declares surfaces {surfaces!r} "
                f"({type(surfaces).__name__}), which is neither None nor a path. "
                f"`canon.resolve` joins this value onto each search root, so a non-string "
                f"raises `TypeError` from inside the search loop and an empty string "
                f"resolves to the root directory itself",
                dict(base, clause="surfaces_is_not_a_path", surfaces=repr(surfaces),
                     surfaces_type=type(surfaces).__name__))
        reason = rec.get("reason")
        if surfaces is None and (not isinstance(reason, str) or not reason.strip()):
            _refuse(
                f"census row {subject!r} has no surfaces file and no reason. The reason "
                f"is what makes a hole a ROW: it is quoted in `require_canon`'s UNGATED "
                f"record and in the spend it announces, so without it neither the "
                f"announcement nor the record can say why the escape applied",
                dict(base, clause="hole_without_a_reason", reason=repr(reason),
                     reason_type=type(reason).__name__))
    return table


def row(subject, census=None):
    """The census row for `subject`, or None if the name is unknown."""
    table = gate_census_table(census)
    return table.get(subject)


# · ANDON at IMPORT — the half a run-time-only check does not have, and the shape
# `route_gates.gate_alias_table()` already uses one file over: a hand-edited table that
# mirrors a ratification decision drifts when the decision is re-taken, and the cheapest
# moment to say so is the moment the module is read.
gate_census_table()
