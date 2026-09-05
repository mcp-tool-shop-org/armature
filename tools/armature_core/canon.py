"""Surface-keyed character statement, both-direction router, fail-closed spend.

WHY THIS EXISTS. Identity is the product and no metric approximates it. What
this module can do is refuse a spend that has no machine-readable statement
of what the character IS, or whose text fails to cover that statement — and
refuse the reverse: text that names something the statement does not license.

ELEMENT is the wrong primary key. A list of named things cannot show the
thing it omitted. SURFACE is the row; occupant None is a hole.

SPATIAL. Facet's mesh is one PBR material; surfaces there cannot come from
geometry. This tree already has a registered bone list (sitelist.ALL_NAMES)
and a face→bone partition (parts.assign_faces). A surface may name a bone,
a GLB material, or a rendered region. Naming a bone that the sitelist does
not carry raises. An absent spatial field is honest: the nameable half
works; the pixel half is unbound.

WHAT THIS DOES NOT DO. It does not decide whether the figure on screen is
the same character. Coverage numbers ride evidence and gate nothing.
Pixel-blocking bind is fenced until the Director rules the contract-atom
vs identity distinction.

FAIL-CLOSED. require_canon is the spend helper. Silence is dead: no
subject, unknown subject, identity-only subject without the escape, a
surfaces file with zero ratified prompt phrases — all refuse, and none
of them create an output directory. The escape is census-backed
``no_canon=True`` on a subject whose surfaces path is None.
``no_canon=True`` on a subject that HAS surfaces is refused.

Both directions. Forward: every ratified occupant phrase occurs in the
prompt, un-negated, and no forbidden word or blocked addition occurs. A
forbidden word is read from EVERY surface's occupant, ratified or not - a
refusal is a claim about the prompt, not about the occupant - while a
phrase is a claim about the occupant and so stays behind ratification.
Reverse: armed whenever legal_clauses is declared (schema 1 requires the
key). Residue after licensed spans refuses.

``blocked_additions`` is a REFUSAL list, not a licence. Until 2026-09-03 its
only behaviour was the opposite: its phrases were collected into
``licensed_phrases`` and stripped from the prompt before the reverse
direction looked for leftovers, so the field permitted exactly the text its
name says is blocked. It occurred in no other module, test, doc or data
file, so nothing settled the reading and the name decides it.

An empty prompt is refused for the same reason ``None`` is: both directions
pass on one having examined zero characters.
"""

from __future__ import annotations

import functools
import json
import os
import re

from . import canon_census
from .errors import GateCanon
from .sitelist import ALL_NAMES

TOOL_VERSION = "1.0.0"
SCHEMA_MIN = 1
SCHEMA_MAX = 1
NEG_WINDOW = 24
SPATIAL_KINDS = ("bone", "material", "region")
OCCUPANT_KINDS = ("prompt", "bare", "mesh")
CLAUSE_CLASSES = ("style", "framing")
NEGATION = re.compile(r"\b(no|not|without|lacking)\b", re.I)
STOP = re.compile(
    r"\b(a|an|the|with|and|or|of|on|in|at|to|for|from|by|as|"
    r"his|her|its|their|this|that|each)\b",
    re.I,
)
WORD = re.compile(r"[a-z0-9']+")

DEFAULT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "canon")
REGISTERED_BONES = frozenset(ALL_NAMES)


def _raise(message, evidence=None):
    """The module's one andon. Every refusal in this file goes through it.

    The evidence names its own gate and andon here rather than at forty call sites: a
    reader holding only the JSON half of a halt record had no id at all — and ids are
    shared across andon families, so the prose half is not enough either. One injection,
    not forty copies that can drift.

    ⚠ **Citation corrected 2026-09-04 (wave 14).** This paragraph read "`stage_render`
    prints `GATE_FAILURE <exc.gate>` and `GATE_EVIDENCE <json>` as two separate lines".
    Those two lines were DELETED at the wave-12 merge: every tool now emits one six-key
    `<TOOL>_HALT` line carrying `tool`, `outcome`, `gate`, `error`, `evidence` and the
    run, and a second uppercase token per tool failed the success/halt pairing census.
    The argument is unchanged and stronger — the id and the evidence ride ONE line now,
    and it is this injection that puts the id on it.
    """
    ev = dict(evidence or {})
    ev["gate"] = GateCanon.gate
    ev["andon"] = "GateCanon"
    raise GateCanon(message, ev)


def add_spend_flags(parser):
    """Flags every spend-authoring builder carries.

    --subject is optional at argparse so a missing flag is a GateCanon,
    not an argparse error — the same defect as ``if args.canon``.
    """
    parser.add_argument(
        "--subject",
        default=None,
        help="census id this payload is of. Silence is a refuse.",
    )
    parser.add_argument(
        "--no-canon",
        dest="no_canon",
        action="store_true",
        help="census-backed escape: only a subject whose surfaces path is None",
    )
    parser.add_argument(
        "--canon-prompt",
        default=None,
        help="text the router checks; default is the payload's positive",
    )
    return parser


def load(path):
    """A surfaces file, or raise. Schema above SCHEMA_MAX is a stale consumer."""
    if not os.path.isfile(path):
        _raise(f"no canon file {path}", {"path": path, "clause": "missing_file"})
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, json.JSONDecodeError) as err:
        _raise(f"could not read canon {path}: {err}",
               {"path": path, "clause": "unreadable"})
    if not isinstance(doc, dict):
        _raise("canon must be an object", {"path": path, "clause": "not_object"})
    try:
        ver = int(doc.get("schema", -1))
    except (TypeError, ValueError):
        ver = -1
    if ver < SCHEMA_MIN:
        _raise(f"canon schema {doc.get('schema')!r} is not >= {SCHEMA_MIN}",
               {"path": path, "schema": doc.get("schema"), "clause": "schema"})
    if ver > SCHEMA_MAX:
        _raise(f"stale consumer: canon schema {ver} > {SCHEMA_MAX}",
               {"path": path, "schema": ver, "clause": "stale_consumer"})
    if "surfaces" not in doc or not isinstance(doc["surfaces"], list):
        _raise("canon needs a surfaces list", {"path": path, "clause": "no_surfaces"})
    if "legal_clauses" not in doc or not isinstance(doc["legal_clauses"], list):
        _raise(
            "canon needs a legal_clauses list (reverse is unarmed without it, "
            "and an unarmed reverse is no answer)",
            {"path": path, "clause": "no_legal_clauses"},
        )
    ids = []
    for i, s in enumerate(doc["surfaces"]):
        if not isinstance(s, dict) or "id" not in s:
            _raise(f"surface {i} needs id", {"path": path, "index": i})
        if s["id"] in ids:
            _raise(f"duplicate surface id {s['id']}", {"path": path, "id": s["id"]})
        ids.append(s["id"])
        occ = s.get("occupant")
        if occ is not None and not isinstance(occ, dict):
            _raise(f"surface {s['id']} occupant must be object or null",
                   {"path": path, "id": s["id"]})
        if occ is not None:
            kind = occ.get("kind", "prompt")
            if kind not in OCCUPANT_KINDS:
                _raise(f"surface {s['id']} occupant.kind {kind!r} is not "
                       f"{OCCUPANT_KINDS}",
                       {"path": path, "id": s["id"], "kind": kind})
            _check_forbidden(s["id"], occ, path)
        spatial = s.get("spatial")
        if spatial is not None:
            _check_spatial(s["id"], spatial, path)
    for j in doc.get("joints") or []:
        if not isinstance(j, dict):
            _raise("joint must be an object", {"path": path})
        if j.get("a") not in ids or j.get("b") not in ids:
            _raise(f"joint {j.get('id')} names unknown surfaces",
                   {"path": path, "joint": j})
    cids = []
    for i, c in enumerate(doc["legal_clauses"]):
        if not isinstance(c, dict) or "id" not in c or "phrase" not in c:
            _raise(f"legal_clause {i} needs id and phrase",
                   {"path": path, "index": i})
        if c["id"] in cids:
            _raise(f"duplicate legal_clause id {c['id']}",
                   {"path": path, "id": c["id"]})
        cids.append(c["id"])
        cls = c.get("class", "style")
        if cls not in CLAUSE_CLASSES:
            _raise(f"legal_clause {c['id']} class {cls!r} is not "
                   f"{CLAUSE_CLASSES}",
                   {"path": path, "id": c["id"]})
    _check_blocked_additions(doc, path)
    return doc


def _check_blocked_additions(doc, path):
    """The doc-level REFUSAL list is validated with the same rigour as the obliging ones.

    ⚠ **`load` validated the two fields that OBLIGE and neither field that REFUSES**, so a
    malformed refusal row was dropped in silence. Surfaces get an id check, a duplicate-id
    check, an occupant-object check, an `occupant.kind` enum check and a full spatial check;
    `legal_clauses` get an id-and-phrase check, a duplicate check and a class enum check.
    `blocked_additions` and `occupant.forbidden` got nothing at all — neither was mentioned
    anywhere in `load` — and `blocked_additions()` keeps only dicts carrying a truthy
    `phrase` (or non-empty strings) and drops everything else without a word.

    Measured 2026-09-04: a doc whose `blocked_additions` is
    `[{'id': 'b1', 'text': 'glowing red halo'}]` — the phrase under the wrong key — loaded
    clean and `blocked_additions(doc)` returned `[]`, so the field this module's header
    calls "a REFUSAL list, not a licence" declared a refusal that does not exist.

    Bounded honestly: for that measured case the reverse direction still refused the prompt
    on unlicensed residue, because `residue` refuses any word no licensed span covers — so
    the silent drop is masked wherever the blocked phrase is not itself licensed. It is NOT
    masked where this field earns its existence: a phrase a broad `legal_clauses` style row
    already licenses, which is the only case the field can change. There, a surfaces file
    declares a refusal, the loader accepts it, and Gate CANON reports ARMED on a payload
    carrying exactly the text the canon refuses.
    """
    adds = doc.get("blocked_additions")
    if adds is None:
        return
    if not isinstance(adds, list):
        _raise(f"blocked_additions must be a list, got {type(adds).__name__}",
               {"path": path, "clause": "blocked_additions_not_a_list",
                "type": type(adds).__name__})
    for i, add in enumerate(adds):
        if isinstance(add, str):
            if not add.strip():
                _raise(f"blocked_additions[{i}] is an empty string, which blocks nothing",
                       {"path": path, "clause": "blocked_addition_empty", "index": i})
            continue
        if not isinstance(add, dict):
            _raise(f"blocked_additions[{i}] must be a string or an object carrying a "
                   f"phrase, got {type(add).__name__}",
                   {"path": path, "clause": "blocked_addition_shape", "index": i,
                    "type": type(add).__name__})
        phrase = add.get("phrase")
        if not isinstance(phrase, str) or not phrase.strip():
            _raise(
                f"blocked_additions[{i}] (id {add.get('id')!r}) carries no string "
                f"`phrase`: keys {sorted(add)}. A refusal row the reader drops is a "
                f"refusal the file declares and the gate never makes — this list is a "
                f"REFUSAL list, and it is validated the way the obliging fields are",
                {"path": path, "clause": "blocked_addition_phrase", "index": i,
                 "id": add.get("id"), "keys": sorted(add)})


def _check_forbidden(sid, occ, path):
    """`occupant.forbidden` is a list of non-empty strings, or the load refuses.

    ⚠ It was read as `for word in occ.get('forbidden') or []` with **no type check**, so a
    string written where a list belongs iterates as SINGLE CHARACTERS — every letter of it
    becomes a forbidden word, and `_forbidden_hit` then matches almost any prompt. The
    other direction (a number, an object) raises a `TypeError` out of `cover`, which is not
    an `ArmatureError` and so does not reach the halt contract's typed receipt.
    """
    if "forbidden" not in occ or occ["forbidden"] is None:
        return
    words = occ["forbidden"]
    if isinstance(words, str) or not isinstance(words, (list, tuple)):
        _raise(
            f"surface {sid} occupant.forbidden must be a list of words, got "
            f"{type(words).__name__} ({words!r}). A bare string iterates as single "
            f"CHARACTERS, so every letter of it becomes a forbidden word",
            {"path": path, "id": sid, "clause": "forbidden_not_a_list",
             "type": type(words).__name__})
    for i, w in enumerate(words):
        if not isinstance(w, str) or not w.strip():
            _raise(
                f"surface {sid} occupant.forbidden[{i}] is {w!r}, not a word; a refusal "
                f"nothing can match is a refusal the file declares and the gate never makes",
                {"path": path, "id": sid, "clause": "forbidden_word", "index": i,
                 "value": repr(w)})


def _check_spatial(sid, spatial, path):
    if not isinstance(spatial, dict):
        _raise(f"surface {sid} spatial must be an object",
               {"path": path, "id": sid})
    kind = spatial.get("kind")
    ref = spatial.get("ref")
    if kind not in SPATIAL_KINDS:
        _raise(f"surface {sid} spatial.kind {kind!r} is not {SPATIAL_KINDS}",
               {"path": path, "id": sid, "kind": kind})
    if not ref or not isinstance(ref, str):
        _raise(f"surface {sid} spatial needs a string ref",
               {"path": path, "id": sid})
    if kind == "bone" and ref not in REGISTERED_BONES:
        _raise(
            f"surface {sid} names bone {ref!r} which is not in sitelist.ALL_NAMES",
            {"path": path, "id": sid, "ref": ref, "clause": "unknown_bone"},
        )


def resolve(subject, *, census=None, search_roots=None):
    """subject id -> loaded canon, or raise. No default subject."""
    if not subject:
        _raise(
            "no subject: a spend with no census id has no answer",
            {"clause": "missing_subject"},
        )
    # · ANDON — the table BEFORE any row is read off it. `canon_census.gate_census_table`
    # is the one implementation; see its docstring for the three readings measured on
    # `e8263a3`, one of which raised a bare `AttributeError` out of this very function.
    table = canon_census.gate_census_table(census)
    if subject not in table:
        _raise(
            f"unknown subject {subject!r} (census has {sorted(table)})",
            {"subject": subject, "known": sorted(table), "clause": "unknown_subject"},
        )
    rec = table[subject]
    rel = rec.get("surfaces")
    if rel is None:
        _raise(
            f"subject {subject!r} has identity and no surfaces file"
            + (f" ({rec['reason']})" if rec.get("reason") else "")
            + ". --no-canon --subject "
            + str(subject)
            + " is the escape; wearing it on a subject that HAS surfaces is refused",
            {
                "subject": subject,
                "reason": rec.get("reason"),
                "clause": "identity_only",
            },
        )
    roots = list(search_roots) if search_roots is not None else [DEFAULT_ROOT]
    tried = []
    for root in roots:
        path = rel if os.path.isabs(rel) else os.path.join(root, rel)
        tried.append(path)
        if os.path.isfile(path):
            doc = load(path)
            doc["_path"] = os.path.abspath(path)
            doc["_subject"] = subject
            return doc
    _raise(
        f"subject {subject!r} names {rel!r} but no search root has that file",
        {"subject": subject, "rel": rel, "tried": tried, "clause": "missing_file"},
    )


def prompt_surfaces(doc):
    """Surfaces that belong in the coverage denominator.

    Holes (occupant None) sit here so they are visible. Occupants of
    kind mesh are spatial-only and stay out — they are numbers, not
    prompt phrases. kind=bare is named without a phrase.
    """
    out = []
    for s in doc["surfaces"]:
        occ = s.get("occupant")
        if occ is None:
            out.append(s)
            continue
        if occ.get("kind", "prompt") == "mesh":
            continue
        out.append(s)
    return out


def is_named(s):
    occ = s.get("occupant")
    if occ is None:
        return False
    if occ.get("phrase"):
        return True
    return occ.get("kind") == "bare"


def is_ratified(s):
    occ = s.get("occupant") or {}
    return bool(occ.get("ratified"))


def has_phrase(s):
    """Does this surface's occupant carry text the router can actually check?"""
    occ = s.get("occupant") or {}
    return bool(occ.get("phrase"))


def coverage(doc):
    """Occupancy and ratification as numbers. Diagnostics. They gate nothing.

    `ratified` counts only occupants that carry a PHRASE. `is_named` is True for an
    occupant of kind 'bare', which carries nothing checkable, so a doc whose ratified
    occupants were all bare satisfied `require_canon`'s tripwire — "zero ratified
    prompt occupants: a check that cannot fail is not a check" — while giving the
    forward direction nothing to look for. The bare ones are still counted, beside it,
    under `ratified_bare`: they are a real state of the file and dropping them from the
    numbers would hide them rather than classify them.
    """
    ps = prompt_surfaces(doc)
    named = [s for s in ps if is_named(s)]
    ratified = [s for s in ps if is_ratified(s) and has_phrase(s)]
    bare = [s for s in ps if is_ratified(s) and is_named(s) and not has_phrase(s)]
    n = len(ps)
    return {
        "prompt_surfaces": n,
        "named": len(named),
        "ratified": len(ratified),
        "ratified_bare": len(bare),
        "ratified_bare_ids": [s["id"] for s in bare],
        "holes": [s["id"] for s in ps if s.get("occupant") is None],
        "unratified_ids": [s["id"] for s in named if not is_ratified(s)],
        "named_coverage": (len(named) / n) if n else None,
        "ratified_coverage": (len(ratified) / n) if n else None,
    }


@functools.lru_cache(maxsize=512)
def _phrase_re(phrase):
    """The ONE matcher both directions use for a phrase. Word boundaries, like
    `_forbidden_hit`.

    ⚠ **The phrase clause used to be `haystack.find(phrase.lower())`** — a bare
    substring test with no boundary — while the refusal clause two screens down
    (`_forbidden_hit`) argues at length that a claim about text needs `\b` and that
    'sleeveless' must not satisfy 'sleeve'. The phrase clause on the same page did not
    get that discipline, and it decides BOTH directions: the forward loop's "does this
    ratified phrase occur in the prompt" and `residue`'s licensed-span strip.

    Measured 2026-09-04 on a doc whose only ratified occupant phrase is 'cape':
    `cover(doc, 'wide landscape shot')` (legal_clause 'wide landscape shot') returned
    verdict COVERED with missing [] — the surface is named nowhere in that prompt, and
    Gate CANON would report ARMED on a payload whose text does not carry the ratified
    statement. The mirror defect is in the reverse direction: with the same doc,
    `residue('a landscape')` returned ['lands'] and `cover` raised "unlicensed residue
    ['lands']", a refusal quoting a token that is not a word. Short single-word phrases
    — cape, helm, arm, hood, mask — are exactly the form a surfaces file names an
    occupant with.

    The boundary is applied only where the phrase's own edge is a word character, so a
    phrase written with leading or trailing punctuation still matches: `\b` between two
    non-word characters never holds, and a matcher that cannot fire is not a matcher.
    """
    low = str(phrase).lower()
    pat = re.escape(low)
    if low[:1].isalnum() or low[:1] == "_":
        pat = r"\b" + pat
    if low[-1:].isalnum() or low[-1:] == "_":
        pat = pat + r"\b"
    return re.compile(pat)


def _find_phrase(haystack, phrase):
    """Lowest index of phrase in haystack (both already lowercased), or -1.

    Word-boundary matched through `_phrase_re` — the same object `residue` strips with,
    so the two directions cannot drift apart.
    """
    if not phrase:
        return -1
    m = _phrase_re(phrase).search(haystack)
    return m.start() if m else -1


def _negated_at(haystack, index):
    window = haystack[max(0, index - NEG_WINDOW):index]
    return bool(NEGATION.search(window))


def blocked_additions(doc):
    """Phrases the doc REFUSES — checked in `cover`, never licensed.

    ⚠ **The field used to do the opposite of its name.** `licensed_phrases` collected
    every `blocked_additions[*].phrase` and `residue` stripped them from the prompt
    before the reverse direction looked for leftovers, so the field's only behaviour in
    the whole repo was to permit exactly the text it says is blocked. Measured
    2026-09-03 on a doc with `blocked_additions=[{'phrase': 'glowing red halo'}]`:
    `licensed_phrases` returned that phrase and `cover(doc, 'black plate glowing red
    halo')` returned COVERED with residue []. The field appears in no other module, no
    test, no doc and no data file, so nothing settled which reading was intended and the
    name decides it: blocked means blocked.
    """
    out = []
    for add in doc.get("blocked_additions") or []:
        if isinstance(add, dict) and add.get("phrase"):
            out.append({"id": add.get("id"), "phrase": add["phrase"]})
        elif isinstance(add, str) and add.strip():
            out.append({"id": None, "phrase": add})
    return out


def licensed_phrases(doc):
    """Spans the reverse direction treats as licensed.

    ⚠ **An occupant phrase licenses only when the occupant is RATIFIED.** This walked
    every surface with no ratification test, while `cover`'s forward direction
    deliberately keeps phrase clauses behind ratification and says why: "a refusal is not
    a claim about the occupant; a phrase IS a claim about the occupant". So the same
    claim was honoured on one side of the router and ignored on the other, and an
    UNRATIFIED row acted as a licence.

    Measured 2026-09-04 before the fix: a doc with a ratified 'black plate' torso and an
    UNRATIFIED 'glowing red halo' surface returned `cover(doc, 'black plate glowing red
    halo')` -> COVERED, residue []; deleting only the unratified surface made the same
    prompt raise "reverse cover failed: unlicensed residue ['glowing', 'red', 'halo']".
    Text the Director has not ratified passed the reverse direction because an
    unratified row in the same file named it — and refusing text the statement does not
    license is that direction's whole job.

    The asymmetry is resolved in the direction the forward clause already took: a
    ratified phrase both licenses and obliges; an unratified one does neither.
    `legal_clauses` rows are a different object — they carry no ratification flag at all
    and are the declared licence surface — so they are unaffected.

    ⚠ **The population is `prompt_surfaces`, not `doc['surfaces']`** (2026-09-04). A
    mesh-kind occupant is spatial-only — `prompt_surfaces`' own docstring: "they are
    numbers, not prompt phrases" — so its phrase neither obliges the prompt (see `cover`)
    nor licenses residue here. Reading two different populations on the two sides of the
    router is what made a prompt covering 1 of 1 prompt surfaces refuse.
    """
    out = []
    for s in prompt_surfaces(doc):
        if not is_ratified(s):
            continue
        occ = s.get("occupant") or {}
        phrase = occ.get("phrase")
        if phrase:
            out.append(phrase)
    for c in doc["legal_clauses"]:
        if c.get("phrase"):
            out.append(c["phrase"])
    # unique, longest first so a longer license consumes a shorter one
    seen = []
    for p in out:
        low = p.lower()
        if low not in seen:
            seen.append(low)
    seen.sort(key=len, reverse=True)
    return seen


def residue(prompt, doc):
    """Word tokens left after licensed spans and stopwords are stripped.

    The strip goes through `_phrase_re`, the same matcher the forward direction uses,
    so a licence for 'cape' cannot fragment 'landscape' into a residue token 'lands'
    that no reader could act on. See `_phrase_re` for the measurement.
    """
    text = prompt.lower()
    for phrase in licensed_phrases(doc):
        text = _phrase_re(phrase).sub(" ", text)
    text = STOP.sub(" ", text)
    return WORD.findall(text)


def _forbidden_forms(word):
    """The canon word plus its de-pluralised stem(s) - both sides of the pair.

    The 2026-09-03 fix appended `(?:e?s)?` to the CANON word, which closes the
    singular-canon / plural-prompt direction only. Measured 2026-09-03, one inflection
    over: forbidden 'gauntlet' fires on "wearing gauntlets" (True) and forbidden
    'gauntlets' does NOT fire on "wearing a gauntlet" (False). The plural is the natural
    form a canon author writes for gauntlets, boots, gloves, greaves and pauldrons, so the
    refusal list that reads most naturally was the one that passed the singular, and Gate
    CANON reported COVERED on it.

    Normalising BOTH sides means stripping a trailing s/es from the canon word as well as
    allowing one on the prompt. A stem is only added when it is long enough to be a word,
    so a two-letter alternative cannot start matching bare articles; and every form still
    carries the optional plural suffix, so a word that genuinely ends in s ('dress' ->
    'dresses') keeps the behaviour it already had.
    """
    w = str(word).lower()
    forms = {w}
    if w.endswith("es") and len(w) >= 5:
        forms.add(w[:-2])
        forms.add(w[:-1])
    elif w.endswith("s") and len(w) >= 4:
        forms.add(w[:-1])
    return sorted(forms, key=len, reverse=True)


def _forbidden_hit(word, hay):
    """A forbidden word, matched as a stem with an optional plural, in BOTH directions.

    A bare word-boundary pattern fires on 'gauntlet' and NOT on 'gauntlets', so a canon
    that forbids a garment feature passed any prompt naming it in the plural and Gate
    CANON reported COVERED (measured 2026-09-03). The optional `(?:e?s)?` before the
    closing boundary catches both plural forms and still cannot match inside a longer
    word: 'sleeveless' fails the trailing boundary exactly as it did before, which is why
    the hand-written sleeve/sleeveless special case was inert - the boundary was already
    doing that work - and is deleted rather than kept as a second mechanism.

    That fix closed ONE direction of the pair. The canon side is normalised too - see
    `_forbidden_forms` - so a plural canon word fires on a singular prompt as well.
    """
    stems = "|".join(re.escape(f) for f in _forbidden_forms(word))
    return re.search(r"\b(?:" + stems + r")(?:e?s)?\b", hay) is not None


def cover(doc, prompt):
    """Both directions. Raises. Evidence always carries coverage numbers."""
    if prompt is None:
        _raise("no prompt: the router has nothing to cover",
               {"clause": "missing_prompt", **coverage(doc)})
    if not str(prompt).strip():
        # An empty prompt is no prompt — the argument the None clause above already
        # makes. Both directions pass vacuously on one: the forward loop finds every
        # phrase absent only if a phrase exists to look for, and `residue('')` is []
        # for ANY doc, so the reverse direction examines zero characters.
        _raise("empty prompt: the router has nothing to cover, and both directions "
               "would pass having examined zero characters",
               {"clause": "empty_prompt", "prompt": prompt, **coverage(doc)})
    hay = prompt.lower()
    ev = coverage(doc)
    ev["prompt"] = prompt
    # The one population every forward PHRASE clause and every denominator is read over.
    prompt_pop_ids = {s["id"] for s in prompt_surfaces(doc)}
    missing = []
    negated = []
    forbidden = []
    for s in doc["surfaces"]:
        occ = s.get("occupant") or {}
        # A refusal is read from EVERY surface, ratified or not.
        #
        # The forbidden loop used to sit below the ratification `continue`, so a
        # forbidden list on an unratified occupant was never read. Measured 2026-09-03 on
        # a doc with a ratified torso occupant and an unratified hands occupant carrying
        # forbidden ["gauntlet"]: `cover(doc, "black plate wearing gauntlet")` returned
        # COVERED with forbidden []; flipping only that occupant's ratified flag made the
        # same prompt raise. `blocked_additions`, the doc-level refusal list, is checked
        # regardless of any ratification, so the two refusal mechanisms disagreed about
        # whether ratification gates a refusal — and `require_canon`'s tripwire only
        # refuses a doc with ZERO ratified phrase-carrying occupants, so a MIXED doc
        # reaches here normally with every unratified surface's list inert.
        #
        # A refusal is not a claim about the occupant; it is a claim about the prompt. A
        # phrase, by contrast, IS a claim about the occupant — "this surface reads like
        # this" — so the forward phrase clauses stay behind ratification. The record says
        # which side of the line each hit came from.
        for word in occ.get("forbidden") or []:
            if _forbidden_hit(word, hay):
                forbidden.append({"surface": s["id"], "word": word,
                                  "ratified": is_ratified(s)})
        if not is_ratified(s):
            continue
        # ⚠ **The phrase half reads the PROMPT population, not every surface.** Two
        # populations of surfaces exist in this module and this loop read the wrong one:
        # `prompt_surfaces` excludes `occupant.kind == 'mesh'` with the reason on its own
        # docstring — "Occupants of kind mesh are spatial-only and stay out — they are
        # numbers, not prompt phrases" — and `coverage` builds every denominator from it,
        # while this loop iterated `doc['surfaces']` directly and demanded a phrase from
        # every ratified occupant, mesh included. Measured 2026-09-04 on a doc with a
        # ratified prompt occupant 'black plate' (torso) and a ratified MESH occupant
        # 'weathered bronze' (skin): `coverage` reported `prompt_surfaces: 1, ratified: 1`
        # and `cover(doc, 'black plate')` raised "forward cover failed: ratified phrases
        # absent: weathered bronze" — a refusal of a prompt that covers 1 of 1 prompt
        # surfaces, quoting a phrase the same module says is not a prompt phrase.
        # `licensed_phrases` read the same wrong population and so a mesh phrase also
        # LICENSED residue; both now read `prompt_surfaces`, so ONE population answers
        # what the prompt must name, what it may name, and what the numbers are counted
        # over. The forbidden/blocked loops above deliberately keep reading EVERY surface:
        # a refusal is a claim about the prompt, not about the occupant.
        #
        # No live instance exists today (no `canon/` directory in the tree; every
        # `canon_census.CENSUS` row carries `surfaces: None`), so this is the schema the
        # module offers the first author who records a mesh-measured surface — for whom
        # the old reading made every spend of that subject refuse until they deleted the
        # row or padded the prompt with a phrase that is not supposed to be in it. An
        # andon that fires on correct work is the andon nobody keeps.
        if s["id"] not in prompt_pop_ids:
            continue
        phrase = occ.get("phrase")
        if phrase:
            idx = _find_phrase(hay, phrase)
            if idx < 0:
                missing.append({"surface": s["id"], "phrase": phrase})
            elif _negated_at(hay, idx):
                negated.append({"surface": s["id"], "phrase": phrase})
    blocked = [b for b in blocked_additions(doc) if _find_phrase(hay, b["phrase"]) >= 0]
    ev["missing"] = missing
    ev["negated"] = negated
    ev["forbidden"] = forbidden
    ev["blocked"] = blocked
    leftover = residue(prompt, doc)
    ev["residue"] = leftover
    ev["clause"] = "cover"
    if missing:
        _raise(
            "forward cover failed: ratified phrases absent: "
            + ", ".join(m["phrase"] for m in missing),
            ev,
        )
    if negated:
        _raise(
            "forward cover failed: ratified phrases negated: "
            + ", ".join(m["phrase"] for m in negated),
            ev,
        )
    if forbidden:
        _raise(
            "forward cover failed: forbidden words present: "
            + ", ".join(f["word"] for f in forbidden),
            ev,
        )
    if blocked:
        ev["clause"] = "blocked_addition"
        _raise(
            "forward cover failed: blocked additions present: "
            + ", ".join(repr(b["phrase"]) for b in blocked)
            + ". blocked_additions names text this canon refuses; it is not a licence",
            ev,
        )
    if leftover:
        _raise(
            "reverse cover failed: unlicensed residue "
            + repr(leftover),
            ev,
        )
    ev["verdict"] = "COVERED"
    return ev


def _gate_out_dir(out_dir):
    """Gate CANON's refusal for a spend directory that is already occupied.

    `None` is "the caller is not telling this gate where the spend lands", which is the
    shape every in-package test uses and is not a defect. A path that does not exist is the
    shape `canon_gate.py` uses: the builder mkdirs AFTER the gate returns, and this
    function creating it would be the exact thing `require_canon`'s docstring promises it
    never does.
    """
    if out_dir is None:
        return None
    path = str(out_dir)
    if not os.path.exists(path):
        return path
    if not os.path.isdir(path):
        _raise(
            f"--out {path!r} exists and is not a directory, so the spend cannot land "
            f"there and `os.listdir` on it raises `NotADirectoryError` — not an "
            f"`ArmatureError`, so the halt contract's exit-2 receipt branch would be "
            f"bypassed",
            {"clause": "out_dir_is_not_a_directory", "out_dir": path,
             "entries": None},
        )
    entries = sorted(os.listdir(path))
    if entries:
        _raise(
            f"--out {path!r} already holds {len(entries)} entr"
            f"{'y' if len(entries) == 1 else 'ies'} ({entries[:8]}). A spend writes its "
            f"payload, its record and its gate receipts into this directory, and a re-run "
            f"over a half-finished one leaves a mixture no later reader can attribute to "
            f"either run. Point --out at a fresh directory, or move the existing one aside",
            {"clause": "out_dir_not_empty", "out_dir": path, "entries": entries},
        )
    return path


def require_canon(
    subject,
    prompt,
    *,
    no_canon=False,
    out_dir=None,
    census=None,
    search_roots=None,
):
    """Fail-closed spend helper. Never creates out_dir. Raises or returns evidence.

    ⚠ **`out_dir` was a parameter both helpers declared, forwarded between them, and
    neither body READ.** Measured on `e8263a3` by grep across this module: four lines
    mentioned it — this signature, the docstring sentence above, `gate_write`'s signature
    and `gate_write`'s forward — and no statement anywhere looked at the value, while
    `tools/canon_gate.py:75` hands it a real directory. The docstring's negative was true
    (nothing here creates a directory) and it was the whole of the contract; a reader of
    that call site had no way to tell that the gate is handed the path it must protect and
    ignores it, and the next edit that added an `out_dir`-dependent clause — or the next
    caller that stopped passing it — would have been invisible at every existing call site.

    It is a check now rather than a deleted parameter, because deleting it would have
    broken `canon_gate.py`'s call and because there IS a real question to ask of the path:
    **a re-run may not write into a half-finished spend.** The directory is refused when it
    exists and holds anything, and when something that is not a directory stands there.
    `out_dir=None` and a path that does not exist yet are the ordinary spellings and are
    unchanged — and the sentence above still holds, because refusing is not creating.
    """
    # · ANDON — the table, before the escape below reads `surfaces` and `reason` off a
    # row with `.get`. A misspelled `surface:` key made the `clause: "checkbox"` refusal
    # inoperative and returned UNGATED for a subject that HAS a ratified surfaces file;
    # `.get` cannot tell an absent key from a misspelled one. One implementation, called
    # here and from `resolve`, so a table supplied through `census=` or mutated at run
    # time meets the same clause the import-time call meets.
    table = canon_census.gate_census_table(census)
    if no_canon:
        if not subject:
            _raise(
                "--no-canon with no subject is a skip flag; name the identity-only subject",
                {"clause": "escape_no_subject"},
            )
        rec = table.get(subject)
        if rec is None:
            _raise(
                f"--no-canon --subject {subject!r} but {subject!r} is not in the census",
                {"subject": subject, "clause": "escape_unknown"},
            )
        if rec.get("surfaces") is not None:
            _raise(
                f"--no-canon --subject {subject!r} refused: that subject HAS a surfaces "
                f"file ({rec['surfaces']}). The escape is only for a subject whose "
                f"surfaces path is None",
                {"subject": subject, "surfaces": rec.get("surfaces"),
                 "clause": "checkbox"},
            )
        # · ANDON — the destination, checked at the point the spend PROCEEDS rather than
        # at the top of the function: an identity refusal stays the headline, and a
        # caller whose subject is wrong should read about the subject.
        _gate_out_dir(out_dir)
        return {
            "verdict": "UNGATED",
            "subject": subject,
            "reason": rec.get("reason"),
            "clause": "escape",
            "announcement": f"[canon] UNGATED: {subject}",
        }

    doc = resolve(subject, census=census, search_roots=search_roots)
    ev = coverage(doc)
    if ev["ratified"] == 0:
        _raise(
            f"subject {subject!r} has a surfaces file and zero ratified prompt "
            f"occupants CARRYING A PHRASE"
            + (f" ({ev['ratified_bare']} ratified occupant(s) are kind='bare' and carry "
               f"nothing the router can check: {ev['ratified_bare_ids']})"
               if ev["ratified_bare"] else "")
            + " — a check that cannot fail is not a check",
            {"subject": subject, "path": doc.get("_path"),
             "clause": "unratified_only", **ev},
        )
    covered = cover(doc, prompt)
    # · ANDON — the destination, on the other path the spend proceeds down. See the
    # sibling call in the `--no-canon` branch above.
    _gate_out_dir(out_dir)
    covered["subject"] = subject
    covered["path"] = doc.get("_path")
    covered["verdict"] = "ARMED"
    return covered


#: Wrapper keys a graph can arrive under. `route_gates.normalise_graph` — THE loader, which
#: `route_gates.load_graph` returns through — unwraps ALL THREE, and this tuple is the
#: single list both it and `canon.texts_from_api_graph` read, so the two cannot drift apart.
#: A document declaring more than one of them refuses (`multiple_graph_declarations`).
#:
#: ⚠ **This comment used to say that `route_gates.load_graph` unwraps only the first TWO of
#: these keys, and that `prompt` is merely the standard submission envelope.** That was true
#: before wave 6 and was then
#: contradicted by the code it annotates: `load_graph` returns `normalise_graph(doc)`, whose
#: unwrap loop reads this whole tuple, and `route_gates.load_graph`'s own docstring records
#: the fix explicitly ("This function used to unwrap `workflow_json` and `workflow` and NOT
#: `prompt`"). A reader taking the comment as the contract would believe a `{"prompt": ...}`
#: envelope still reaches the gates wrapped — the exact false belief the wave-6 fix removed,
#: and the one under which every clause of `verify` reported its zero-population verdict as
#: a pass. Corrected in place 2026-09-05; the behavioural pin is
#: `tests/test_route_gates.py`'s wrapper-unwrap cases.
GRAPH_WRAPPER_KEYS = ("prompt", "workflow_json", "workflow")


def texts_from_api_graph(graph):
    """String inputs named text/prompt/positive on an API-format graph.

    Used when a builder inherits its prompt from a baseline graph (E14)
    and has no local constant. Negative prompts tend to be shorter
    quality lists; callers that need one string take the longest.

    ⚠ **"No text here" and "I did not recognise this shape" are different answers.**
    The guard used to be `graph.values() if all(isinstance(v, dict) for v in
    graph.values()) else []`, so ONE non-dict top-level key emptied the result:
    measured 2026-09-03, a bare API graph returned its prompt, the same graph plus
    `last_node_id=12` returned [], and the standard `{'prompt': <graph>}` wrapper
    returned []. A caller could not tell the two apart, and the prompt it then hands
    Gate CANON is what the whole check is about. Known wrappers are unwrapped, non-dict
    siblings are skipped rather than fatal, and a shape carrying no node-like value at
    all raises instead of reporting an empty prompt.
    """
    # The unwrap is `route_gates.normalise_graph` — THE loader, whose own docstring
    # says "every gate in this module reads its graph through this one function" and
    # which wave 6 made one implementation precisely so two unwrap rules could not
    # drift. This module carried a second one: it unwrapped exactly one level, only
    # when the inner mapping already held node-shaped values, and did not recognise
    # save format at all. Measured 2026-09-04: a save-format graph and a doubly-wrapped
    # {'prompt': {'prompt': <api>}} both raised `unrecognised_graph` — fail-closed
    # either way, so the exposure was a refusal rather than a false pass, and the cost
    # was the one the wave-6 consolidation was paying down.
    #
    # Imported inside the function because `route_gates` imports `GRAPH_WRAPPER_KEYS`
    # from this module at import time; a top-level import here would be a cycle. The
    # node-shaped-value clause below stays this module's own.
    from . import route_gates

    try:
        doc = route_gates.normalise_graph(graph)
    except route_gates.RouteGate as exc:
        _raise(
            f"{exc}; an unrecognised shape is not an empty prompt",
            dict(exc.evidence or {}, clause="unrecognised_graph",
                 type=type(graph).__name__),
        )
    if not route_gates.is_api_format(doc):
        _raise(
            "this is a SAVE-format graph (a `nodes` list); this reader walks API format "
            "(node-id keyed values carrying `class_type`) and would report no text at "
            "all on it, which is not the same answer as a graph carrying none",
            {"clause": "not_api_format", "type": type(graph).__name__},
        )
    # The "no node-shaped value here" clause that used to stand below is GONE, and its
    # deletion is the point of reading through the one loader rather than a second
    # copy. `normalise_graph` returns an API-format doc only when some value is a dict
    # carrying `class_type` — which is a node under the predicate below — so the clause
    # could no longer fire on any input at all. A check that cannot fail is not a check;
    # the question it asked is now answered above, once, by the loader every gate in
    # `route_gates` reads through, and the two answers it separates ("no text here" and
    # "I did not recognise this shape") are still separate.
    nodes = [v for v in doc.values()
             if isinstance(v, dict) and ("inputs" in v or "class_type" in v)]
    out = []
    for node in nodes:
        inputs = node.get("inputs") or {}
        if not isinstance(inputs, dict):
            continue
        for key in ("text", "prompt", "positive"):
            val = inputs.get(key)
            if isinstance(val, str) and val.strip():
                out.append(val)
    return out


def gate_write(subject, prompt, *, no_canon=False, out_dir=None,
               census=None, search_roots=None):
    """The call every spend builder makes before mkdir.

    Named separately from require_canon so a builder's main is one line
    and a test can pin that mkdir is not this function's job.
    """
    return require_canon(
        subject,
        prompt,
        no_canon=no_canon,
        out_dir=out_dir,
        census=census,
        search_roots=search_roots,
    )
