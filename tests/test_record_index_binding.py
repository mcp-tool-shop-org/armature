"""`tools/armature_index.py` - the two verbs this repo's binding implements itself.

SEPARATE FILE, AND THAT IS THE POINT. These need `record_index`, which is a sibling
working copy at `E:\\AI\\record-index` and not a dependency of this venv, so the
module-level skip below takes the whole file when it is absent. The checks that must
never skip - the committed index and its certificate - live in `test_record_index.py`
and read those two files with the standard library alone.

Run this half with ARMATURE_RECORD_INDEX set (or the default sibling present):

    ARMATURE_RECORD_INDEX=E:/AI/record-index .venv/Scripts/python.exe -m pytest tests/test_record_index_binding.py

conftest prepends that lever (or `E:/AI/record-index` when it exists) before collection.
"""

import hashlib
import importlib.util
import io
import json
import os
import re

import pytest

pytest.importorskip(
    "record_index",
    reason="record_index is a sibling working copy, not a dependency of this venv; "
           "set ARMATURE_RECORD_INDEX to your record-index checkout "
           "(default E:/AI/record-index when present) to cover the binding")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@pytest.fixture(scope="module")
def mod():
    """The adapter, imported from its path.

    `tools/` is on the suite's path already, but this file is also a console script
    with a `__main__` guard; loading it by location keeps the import independent of
    whatever else has claimed the name.
    """
    path = os.path.join(REPO, "tools", "armature_index.py")
    spec = importlib.util.spec_from_file_location("_armature_index_under_test", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ------------------------------------------------------------------ build certifies

def test_build_writes_a_certificate_beside_the_index_it_builds(mod, tmp_path):
    """The regression test for routing `build` through `build_and_certify`.

    Measured on 2026-08-18, before the change: `build` into an empty directory
    produced `fresh.db` and no `fresh.db.cert.json` at all, while the certificate
    module's own docstring states there is no path that writes a db without writing
    a certificate for it. If someone routes this verb back at the shared builder,
    this is exactly what it looks like - a fresh index with nothing beside it
    recording what verify made of it.
    """
    db = str(tmp_path / "probe.db")
    rc = mod.main(["build", "--db", db])
    assert os.path.exists(db)
    assert os.path.exists(db + ".cert.json"), "build wrote an index and no certificate"
    with io.open(db + ".cert.json", encoding="utf-8") as fh:
        doc = json.load(fh)
    assert doc["db"]["sha256"] == _sha256(db)
    assert doc["corpus"]["files"] > 0
    assert rc == (0 if doc["verify_exit_code"] == 0 else 4)


def test_a_build_whose_verify_refused_does_not_report_success(mod, tmp_path, monkeypatch):
    """The shared `build` verb returns EXIT_OK whatever its verify found, leaving a
    refusal visible only to whoever reads the transcript. A build that refused and
    exited 0 is what this branch exists to prevent."""
    monkeypatch.setattr(mod._cert, "build_and_certify", lambda *a, **k: {
        "state": "FAILED", "verify_exit_code": 4,
        "db": {"bytes": 0, "sha256": "0" * 64},
        "corpus": {"files": 0, "id": "0" * 64},
    })
    assert mod._build_and_certify(str(tmp_path / "x.db")) == 4


# ------------------------------------------------------------------- health's ruling

def test_stale_serves_and_the_refusals_do_not(mod, tmp_path, monkeypatch):
    """The exit codes `health` hands back, which encode a ruling rather than a taste.

    STALE must exit 0: the library rules bounded staleness the normal state of a
    record whose db commits at session boundaries, so refusing there would fire on
    correct work. The three refusals must exit 4 - "the tool ran correctly and is
    telling you not to proceed" - and never 1, which means the operator mistyped.
    """
    db = str(tmp_path / "y.db")
    seen = {}
    monkeypatch.setattr(mod._cert, "health", lambda b, p: seen["h"])

    seen["h"] = {"state": "STALE", "serving": True,
                 "why": "the corpus moved since this index was built",
                 "moved": ["HANDOFF.md"], "moved_total": 1}
    assert mod._health(db) == 0

    for state in ("INDEX_MISSING", "INDEX_NEVER_VERIFIED", "INDEX_VERIFY_FAILED"):
        seen["h"] = {"state": state, "serving": False, "why": "because"}
        assert mod._health(db) == 4, "%s should refuse, not serve" % state


def test_health_names_the_files_that_moved(mod, tmp_path, monkeypatch, capsys):
    """A warning a session cannot act on is a warning it learns to ignore. STALE
    without the file list is "something changed"; with it, it is the rebuild you
    now know you owe."""
    monkeypatch.setattr(mod._cert, "health", lambda b, p: {
        "state": "STALE", "serving": True, "why": "moved",
        "moved": ["HANDOFF.md", "README.md"], "moved_total": 112})
    mod._health(str(tmp_path / "z.db"))
    out = capsys.readouterr().out
    assert "STALE" in out and "112" in out
    assert "HANDOFF.md" in out and "README.md" in out


# ---------------------------------------------------------------- the verb surface

def _shared_verbs(mod):
    """The shared CLI's own choices, read from its behaviour rather than copied.

    Handing it an unknown verb makes argparse name every choice it accepts. Read
    this way the list cannot drift out of agreement with the parser that enforces it.
    """
    import contextlib
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        with pytest.raises(SystemExit):
            mod._cli.main(mod.BINDING, ["__no_such_verb__"])
    m = re.search(r"choose from ([^)]*)\)", err.getvalue())
    assert m, "the shared CLI no longer names its choices: %r" % err.getvalue()
    return tuple(v.strip().strip("'\"") for v in m.group(1).split(","))


def test_this_binding_offers_every_verb_the_shared_cli_offers(mod):
    """A verb added upstream should fail here rather than go quietly unoffered.

    This file dispatches on its own list and hands the rest to the shared CLI, so
    the two have to agree. If the code were wrong in the specific way this catches,
    `armature_index.py <new-verb>` would report an invalid choice for a verb the
    library implements - and the only symptom would be that nobody used it.
    """
    shared = _shared_verbs(mod)
    assert set(shared) <= set(mod.VERBS), (
        "the shared CLI offers verbs this binding does not: %s"
        % sorted(set(shared) - set(mod.VERBS)))
    assert set(mod.DELEGATED_VERBS) <= set(shared)
    assert set(mod.DELEGATED_VERBS).isdisjoint(mod.OWNED_VERBS)
    assert set(mod.VERBS) == set(mod.DELEGATED_VERBS) | set(mod.OWNED_VERBS)
    # `build` is owned BECAUSE it is also upstream - this binding replaces it so it
    # certifies. `health` is owned because upstream has no such verb. If either of
    # those stops being true the override is no longer the thing it was written as.
    assert set(mod.OWNED_VERBS) & set(shared) == {"build"}, (
        "the owned verbs no longer stand in the relation to upstream they were "
        "written for: owned=%s shared=%s" % (sorted(mod.OWNED_VERBS), sorted(shared)))


def test_an_unknown_verb_is_offered_all_five(mod, capsys):
    """The shared parser's error message lists four verbs, because its `choices` do
    not carry this binding's two. Delegating an unknown verb to it therefore advised
    the operator of four of the five that work."""
    rc = mod.main(["__nope__"])
    assert rc == 1
    err = capsys.readouterr().err
    for verb in mod.VERBS:
        assert verb in err, "%r missing from the invalid-choice message" % verb


def test_help_lists_every_verb_the_binding_dispatches(mod, capsys):
    """`--help` is the only place an operator learns a verb exists."""
    assert mod.main(["--help"]) == 0
    out = capsys.readouterr().out
    for verb in mod.VERBS:
        assert verb in out


# ------------------------------------------------------------------ db resolution

def test_db_resolution_follows_the_shared_precedence(mod, tmp_path, monkeypatch):
    """`--db` over `$ARMATURE_INDEX_DB` over the record's tracked index. The owned
    verbs resolve this themselves, so a drift from the shared rule would point
    `build` at one index while `verify` read another."""
    monkeypatch.setenv("ARMATURE_INDEX_DB", str(tmp_path / "from_env.db"))
    assert mod._resolve_db(str(tmp_path / "explicit.db")).endswith("explicit.db")
    assert mod._resolve_db(None).endswith("from_env.db")
    monkeypatch.delenv("ARMATURE_INDEX_DB")
    assert mod._resolve_db(None) == mod.BINDING.db_default()


# -------------------------------------- the usage line and the dispatcher say the same thing
#
# `_print_help` printed `usage: armature_index.py {build,verify,q,claims,health} [term]
# [--db PATH] ...`, advertising the SPACE-separated form; `_peek_verb` returned the first
# token not starting with `-`, so in `--db PATH health` that token is the PATH. Measured
# 2026-09-04 in this worktree:
#
#   `armature_index.py --db C:/tmp/nonexistent.db health`
#       -> error: invalid choice: 'C:/tmp/nonexistent.db'
#          (choose from 'build','verify','q','claims','health')
#          hint: armature_index.py --help                                   exit 1
#   `armature_index.py --db=C:/tmp/nonexistent.db health`
#       -> state INDEX_MISSING / serving no / why no index at ...           exit 4
#
# The refusal that names the verb was written to stop exactly this class of unhelpful
# message, and it produced one: an operator following the tool's own usage line was told
# their database path is an invalid verb.


def test_the_two_db_forms_reach_the_same_verb(mod, tmp_path):
    """THE fixture: the same command, written the two ways the tool advertises."""
    missing = str(tmp_path / "nonexistent.db")
    assert mod._peek_verb(["--db", missing, "health"]) == "health"
    assert mod._peek_verb(["--db=" + missing, "health"]) == "health"
    assert mod.main(["--db", missing, "health"]) == \
        mod.main(["--db=" + missing, "health"])


def test_every_value_taking_flag_is_derived_from_the_parsers_that_declare_it(mod):
    """The node this census keys on is the `add_argument` call — this binding's own
    parser and the shared CLI's, read by AST — not a list typed beside the dispatcher.

    A `store_true` flag consumes nothing after it and must NOT be in the set, or
    `--debug health` would swallow the verb.
    """
    flags = mod._value_flags()
    assert "--db" in flags
    assert "--limit" in flags and "--table" in flags, sorted(flags)
    assert "--debug" not in flags, sorted(flags)
    assert mod._peek_verb(["--debug", "health"]) == "health"


def test_the_usage_line_advertises_a_form_the_dispatcher_accepts(mod, capsys):
    """A usage line naming a form the dispatcher rejects is the defect, whichever half
    is changed to close it. Both halves are asserted, so neither can drift alone."""
    mod._print_help()
    usage = capsys.readouterr().out.splitlines()[0]
    for flag in re.findall(r"--[a-z-]+", usage):
        if flag in mod._value_flags():
            assert flag + "=" in usage, (flag, usage)


def test_a_term_after_a_query_verb_is_not_mistaken_for_the_verb(mod):
    """The guard the other way: `q armature` must still dispatch on `q`, and a term that
    happens to follow a value flag must not become the verb."""
    assert mod._peek_verb(["q", "armature"]) == "q"
    assert mod._peek_verb(["--limit", "5", "q", "armature"]) == "q"
    assert mod._peek_verb([]) is None
