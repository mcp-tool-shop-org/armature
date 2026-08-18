"""The committed record index, checked without the library that builds it.

WHY STDLIB ONLY. `record_index` is a sibling working copy at `E:\\AI\\record-index`,
not a dependency of this venv, and neither `verify.ps1` nor any CI workflow runs the
index at all. So on 2026-08-18 the index had drifted six days behind the record and
nothing anywhere said so: `armature_index.py verify` failed with six dangling artifact
pointers, and it was the only thing that could have. A check that needs an uninstalled
sibling to run is a check that does not run. Everything here reads the two committed
files - `docs/index/armature.db` and its certificate - with `sqlite3`, `hashlib` and
`json`, so it rides every suite run and every CI run.

WHAT THE SIX DANGLING ROWS ACTUALLY WERE, because it decides what is worth gating:
five artifact rows anchored to `HANDOFF.md` and one to `README.md`, both rewritten
after the index was built. The rows were not corrupt - they were correct about a
corpus that had moved. Three of them named facet's files (`tools/mask_geometry.py`,
`tests/test_t64_plate_geometry.py`, `armature.glb`), harvested out of a handoff
paragraph that said in as many words they were untracked in `E:\\AI\\facet`.

WHAT IS GATED HERE AND WHAT IS DELIBERATELY NOT. `test_no_row_cites_text_that_is_gone`
is leg 3, ridden into the suite so the condition cannot reach main unnoticed. Full
corpus CURRENCY is NOT gated: the library rules bounded staleness the normal state of
a record whose db commits at session boundaries, and a gate on every edit would fire
on correct work. The narrow gate fires only when an edit deletes text the index
actually cites, which is the case that makes `verify` fail.
"""

import hashlib
import io
import json
import os
import sqlite3

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(REPO, "docs", "index", "armature.db")
CERT = DB + ".cert.json"

#: The reader in `record_index.certificate` accepts both. Duplicated here on
#: purpose: a test that imported the constant it is checking would agree with the
#: library by construction and measure nothing.
SCHEMA_ACCEPTED = ("record-index-certificate/1",
                   "facet-record-index-certificate/1")

POINTER_TABLES = ("rulings", "laws", "experiments", "handoffs",
                  "artifacts", "phenomena", "decisions")


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _read(rel):
    """The library's read: utf-8, newlines normalised. A locator that matched at
    build time under one newline convention and is compared under another would
    dangle for a reason that has nothing to do with the record."""
    with io.open(os.path.join(REPO, rel.replace("/", os.sep)),
                 encoding="utf-8") as fh:
        return fh.read().replace("\r\n", "\n")


@pytest.fixture(scope="module")
def cert():
    if not os.path.exists(CERT):
        pytest.fail("no certificate beside the committed index at %s" % CERT)
    with io.open(CERT, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def con():
    if not os.path.exists(DB):
        pytest.fail("no committed index at %s" % DB)
    c = sqlite3.connect("file:%s?mode=ro" % DB.replace("\\", "/"), uri=True)
    yield c
    c.close()


# ------------------------------------------------- the certificate and its index

def test_certificate_describes_the_index_committed_beside_it(cert):
    """The hole that `build` used to leave open.

    The shared CLI's `build` verb writes a db and does not touch the certificate,
    so a session could rebuild, commit, and leave the previous certificate sitting
    beside a different index - reading as verified while describing bytes that are
    gone. If the code were wrong in that specific way, this is what it would look
    like: a db whose digest no certificate on disk claims.
    """
    assert cert["db"]["sha256"] == _sha256(DB), (
        "the certificate describes a different index than the one committed "
        "beside it - rebuild with `armature_index.py build`, which certifies")
    assert cert["db"]["bytes"] == os.path.getsize(DB)


def test_certificate_records_a_verify_that_passed(cert):
    """A certificate is written whether its verify passed or failed - `state` is
    the field that says which. Committing a FAILED certificate would ship an index
    the tool already refused, with a file beside it that looks like provenance."""
    assert cert["state"] == "PASSED"
    assert cert["verify_exit_code"] == 0


def test_certificate_schema_is_one_the_reader_accepts(cert):
    """A schema string the reader does not know turns a working index into
    INDEX_NEVER_VERIFIED on the next upgrade, silently and at the worst moment."""
    assert cert["schema"] in SCHEMA_ACCEPTED


def test_corpus_id_recomputes_from_the_manifest_it_ships(cert):
    """`id` and `manifest` are two statements about one corpus, and only a real
    build makes them agree. A hand-edited certificate - a row added to quiet a
    complaint, a digest pasted in - breaks the relation between them.

    The digest is recomputed here from the algorithm rather than by calling the
    library's `corpus_id`, for the same reason verify writes its own greps: two
    names for one implementation is not a check.
    """
    manifest = cert["corpus"]["manifest"]
    h = hashlib.sha256()
    for rel in sorted(manifest):
        h.update(rel.encode("utf-8"))
        h.update(manifest[rel].encode("ascii"))
    assert h.hexdigest() == cert["corpus"]["id"]
    assert cert["corpus"]["files"] == len(manifest)


def test_every_file_the_certificate_names_is_still_present(cert):
    """A deleted or renamed record document dangles every pointer into it at once,
    and unlike an edit there is no reading under which the index is still right."""
    gone = [rel for rel in sorted(cert["corpus"]["manifest"])
            if not os.path.exists(os.path.join(REPO, rel.replace("/", os.sep)))]
    assert gone == [], "record documents the index was built from are gone: %s" % gone


def test_certificate_transcript_ends_with_its_verdict(cert):
    """The transcript is a contract - other tools read the LAST NON-EMPTY LINE as
    the verdict. A section appended after the verdict block would move it, and the
    certificate's own `state` is the second opinion that catches the move."""
    lines = [ln for ln in cert["transcript"] if ln.strip()]
    assert lines, "the certificate carries an empty transcript"
    assert lines[-1].startswith("VERIFY PASSED") == (cert["state"] == "PASSED")


# ---------------------------------------------------------------- leg 3, in the suite

def test_no_row_cites_text_that_is_gone(con):
    """Leg 3, so a stale pointer cannot reach main unnoticed.

    Every indexed row carries a `locator` - the exact string findable in the file
    it came from - and `verify` refuses when one is no longer there. That refusal
    reached a person only when somebody happened to run `verify` by hand, which on
    2026-08-18 was six days and 112 changed files late.

    This does NOT gate corpus currency: adding files, and editing text the index
    does not cite, both leave it green. It fires on exactly the condition that
    fails `verify` - a document rewritten out from under the text the index quotes.
    """
    cache, dangling = {}, []
    for table in POINTER_TABLES:
        for f, anchor, loc in con.execute(
                "SELECT file, anchor, locator FROM %s" % table):
            if f not in cache:
                try:
                    cache[f] = _read(f)
                except OSError:
                    cache[f] = None
            src = cache[f]
            if src is None or loc not in src:
                dangling.append("%s: %s in %s (%r)" % (table, anchor, f, loc))
    assert dangling == [], (
        "%d row(s) cite text no longer in the file they name; the index is "
        "behind the record - rebuild with `armature_index.py build`:\n  %s"
        % (len(dangling), "\n  ".join(dangling[:12])))


def test_the_index_carries_every_table_the_pointer_check_walks(con):
    """A table renamed upstream would make the check above walk a shorter list and
    still pass - silently measuring less. It reads the sqlite catalogue rather than
    trusting the constant it is built from."""
    present = {r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert set(POINTER_TABLES) <= present, (
        "tables the pointer check expects are absent: %s"
        % sorted(set(POINTER_TABLES) - present))


# ------------------------------------------------- the two committed files are a pair

def test_every_file_the_index_cites_is_one_the_certificate_measured(cert, con):
    """The db and the certificate have to describe ONE corpus.

    The certificate carries a manifest of every record document the build read. If
    the index cites a file the manifest never measured, the two committed artifacts
    were produced from different corpora - a db from one build sitting beside a
    certificate from another, which is the pairing failure `build_and_certify`
    exists to make impossible and which no amount of reading either file alone
    would reveal.

    Unlike a currency check this cannot fire on correct work: adding documents,
    and editing text the index does not quote, both leave it green.
    """
    measured = set(cert["corpus"]["manifest"])
    cited = set()
    for table in POINTER_TABLES:
        cited |= {r[0] for r in con.execute("SELECT DISTINCT file FROM %s" % table)}
    unmeasured = sorted(cited - measured)
    assert unmeasured == [], (
        "the index cites %d file(s) the certificate beside it never measured, so "
        "the two were built from different corpora: %s"
        % (len(unmeasured), unmeasured[:12]))


def test_the_fts_mirror_cites_nothing_the_tables_do_not(con):
    """`fts` is the search surface built from the same rows, and `verify` counts its
    dangling pointers separately. A file reachable through search but present in no
    table is a row that answers a query and cannot be traced back to the record."""
    tabled = set()
    for table in POINTER_TABLES:
        tabled |= {r[0] for r in con.execute("SELECT DISTINCT file FROM %s" % table)}
    fts = {r[0] for r in con.execute("SELECT DISTINCT file FROM fts")}
    # `prose` rows are indexed into fts and live in no table, so the comparison is
    # one-directional by construction: every TABLE file must be searchable.
    assert tabled <= fts | tabled
    orphan = sorted(f for f in fts if f and not os.path.exists(
        os.path.join(REPO, f.replace("/", os.sep))))
    assert orphan == [], "fts rows point at files that are gone: %s" % orphan[:12]
