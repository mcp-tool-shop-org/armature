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
prompt, un-negated, and no forbidden word or blocked addition occurs.
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
    raise GateCanon(message, evidence or {})


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
    return doc


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
    table = canon_census.CENSUS if census is None else census
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


def _find_phrase(haystack, phrase):
    """Lowest index of phrase in haystack (both already lowercased), or -1."""
    if not phrase:
        return -1
    return haystack.find(phrase.lower())


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
    """Spans the reverse direction treats as licensed."""
    out = []
    for s in doc["surfaces"]:
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
    """Word tokens left after licensed spans and stopwords are stripped."""
    text = prompt.lower()
    for phrase in licensed_phrases(doc):
        text = text.replace(phrase, " ")
    text = STOP.sub(" ", text)
    return WORD.findall(text)


def _forbidden_hit(word, hay):
    """A forbidden word, matched as a stem with an optional plural.

    ⚠ A bare `\\b<word>\\b` fires on 'gauntlet' and NOT on 'gauntlets', so a canon that
    forbids a garment feature passed any prompt naming it in the plural and Gate CANON
    reported COVERED (measured 2026-09-03). `(?:e?s)?` before the closing boundary
    catches both plural forms and still cannot match inside a longer word: 'sleeveless'
    fails the trailing boundary exactly as it did before, which is why the hand-written
    `SLEEVE = \\bsleeve(?!less)\\b` special case was inert — the boundary was already
    doing that work — and is now deleted rather than kept as a second mechanism.
    """
    return re.search(r"\b" + re.escape(word.lower()) + r"(?:e?s)?\b", hay) is not None


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
    missing = []
    negated = []
    forbidden = []
    for s in doc["surfaces"]:
        occ = s.get("occupant") or {}
        if not is_ratified(s):
            continue
        phrase = occ.get("phrase")
        if phrase:
            idx = _find_phrase(hay, phrase)
            if idx < 0:
                missing.append({"surface": s["id"], "phrase": phrase})
            elif _negated_at(hay, idx):
                negated.append({"surface": s["id"], "phrase": phrase})
        for word in occ.get("forbidden") or []:
            if _forbidden_hit(word, hay):
                forbidden.append({"surface": s["id"], "word": word})
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


def require_canon(
    subject,
    prompt,
    *,
    no_canon=False,
    out_dir=None,
    census=None,
    search_roots=None,
):
    """Fail-closed spend helper. Never creates out_dir. Raises or returns evidence."""
    table = canon_census.CENSUS if census is None else census
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
    covered["subject"] = subject
    covered["path"] = doc.get("_path")
    covered["verdict"] = "ARMED"
    return covered


#: Wrapper keys a graph can arrive under. `route_gates.load_graph` unwraps the first
#: two; `prompt` is the standard submission envelope.
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
    doc = graph
    if isinstance(doc, dict):
        for key in GRAPH_WRAPPER_KEYS:
            inner = doc.get(key)
            if isinstance(inner, dict) and any(
                    isinstance(v, dict) and ("inputs" in v or "class_type" in v)
                    for v in inner.values()):
                doc = inner
                break
    if not isinstance(doc, dict):
        _raise(
            f"a graph must be an object, got {type(graph).__name__}; an unrecognised "
            f"shape is not an empty prompt",
            {"clause": "unrecognised_graph", "type": type(graph).__name__},
        )
    nodes = [v for v in doc.values()
             if isinstance(v, dict) and ("inputs" in v or "class_type" in v)]
    if not nodes:
        _raise(
            "no node-shaped value in this graph, so no prompt could be read from it. "
            "That is not the same as a graph carrying no text, and a spend must not "
            "proceed on the difference",
            {"clause": "unrecognised_graph", "top_level_keys": sorted(map(str, doc))},
        )
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
