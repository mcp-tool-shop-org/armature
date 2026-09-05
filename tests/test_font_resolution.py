"""Which typeface a dailies sheet is set in, and what happens when there is none.

`_font` called `ImageFont.truetype(os.path.join(FONT_DIR, name), size)` with no try/except
and no fallback of its own, `FONT_DIR` being the literal `C:\\Windows\\Fonts`. Measured on
this rig with Pillow 12.3.0: `truetype` catches its own OSError, takes
`os.path.basename(font)`, and walks the PLATFORM's font directories for a file of that name —
`ImageFont.truetype('<nonexistent-dir>/arial.ttf', 26)` returned a font whose `.path` is
`C:\\WINDOWS\\fonts\\arial.ttf`, from a directory nobody named. So the constant's VALUE was
never load-bearing; only its basename was, which is why the hard-coded path was never noticed.

On a POSIX runner it is worse than unused: `posixpath.join(r'C:\\Windows\\Fonts',
'arial.ttf')` yields the RELATIVE string `'C:\\Windows\\Fonts/arial.ttf'`, so the intended
directory is never consulted and Pillow's basename walk decides the typeface — silently where
it finds `arial.ttf`, and with `OSError: cannot open resource` (naming neither the directory
nor the file) where it does not.

Both outcomes are refused here. The resolution is an explicit, ordered search this repo
performs itself, the resolved path is reported on the sheet's own output line, and when
nothing resolves the error names every directory and every face it tried.

**Which faces, and their licences.** The requested face is tried first (a system font already
installed on the machine — using one is not redistributing it). The fallbacks are
`LiberationSans` (SIL OFL 1.1) and `NotoSans` (SIL OFL 1.1), and nothing else: DejaVu is
present on most Linux boxes but its licence document could not be fetched from this seat, and
under this repo's licence gate a licence that cannot be retrieved is treated as NO. It is
therefore named in the refusal rather than quietly used. No font binary is committed to the
repo — big binaries stay out of git, and a bundled face would need a licence-map row of its
own first.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import sheet_compose as SC  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_cache():
    SC.clear_font_index()
    yield
    SC.clear_font_index()


def test_an_empty_search_list_raises_naming_every_path_it_tried(tmp_path, monkeypatch):
    """THE fixture: no font anywhere the tool is allowed to look. Pillow's own basename
    walk must not get a chance to answer, and the message must name what was tried."""
    empty = tmp_path / "fonts"
    empty.mkdir()
    monkeypatch.setenv(SC.FONT_ENV, str(empty))
    monkeypatch.setattr(SC, "platform_font_dirs", lambda: [])

    with pytest.raises(SC.FontError) as e:
        SC.resolve_font_path("arial.ttf")
    msg = str(e.value)
    assert str(empty) in msg
    assert "arial.ttf" in msg and "LiberationSans-Regular.ttf" in msg
    assert e.value.evidence["directories"] == [str(empty)]
    assert "arial.ttf" in e.value.evidence["faces_tried"]


def test_the_refusal_names_a_face_it_found_but_may_not_use(tmp_path, monkeypatch):
    """A licence that cannot be retrieved is treated as NO. DejaVu is on most Linux boxes;
    it is named in the refusal rather than substituted in silence."""
    d = tmp_path / "fonts"
    d.mkdir()
    (d / "DejaVuSans.ttf").write_bytes(b"not a real font, and not used either")
    monkeypatch.setenv(SC.FONT_ENV, str(d))
    monkeypatch.setattr(SC, "platform_font_dirs", lambda: [])

    with pytest.raises(SC.FontError) as e:
        SC.resolve_font_path("arial.ttf")
    assert "DejaVuSans.ttf" in str(e.value)
    assert e.value.evidence["found_but_licence_unverified"] == ["DejaVuSans.ttf"]


def test_the_env_override_is_searched_before_the_platform(tmp_path, monkeypatch):
    d = tmp_path / "fonts"
    d.mkdir()
    target = d / "LiberationSans-Regular.ttf"
    target.write_bytes(b"stand-in")
    monkeypatch.setenv(SC.FONT_ENV, str(d))
    monkeypatch.setattr(SC, "platform_font_dirs", lambda: [])

    assert SC.resolve_font_path("arial.ttf") == str(target)


def test_a_nested_directory_is_searched_because_linux_nests_its_fonts(tmp_path, monkeypatch):
    """`/usr/share/fonts/truetype/liberation/…` — a flat join would miss every one."""
    nested = tmp_path / "fonts" / "truetype" / "liberation"
    nested.mkdir(parents=True)
    target = nested / "LiberationSans-Bold.ttf"
    target.write_bytes(b"stand-in")
    monkeypatch.setenv(SC.FONT_ENV, str(tmp_path / "fonts"))
    monkeypatch.setattr(SC, "platform_font_dirs", lambda: [])

    assert SC.resolve_font_path("arialbd.ttf") == str(target)


def test_resolution_never_returns_a_path_outside_the_search_list(tmp_path, monkeypatch):
    """The defect restated as a property: whatever Pillow would have found on its own, the
    answer must come from a directory this repo named."""
    d = tmp_path / "fonts"
    d.mkdir()
    (d / "arial.ttf").write_bytes(b"stand-in")
    monkeypatch.setenv(SC.FONT_ENV, str(d))
    monkeypatch.setattr(SC, "platform_font_dirs", lambda: [])

    got = SC.resolve_font_path("arial.ttf")
    assert os.path.dirname(got) == str(d)


def test_the_faces_this_repo_will_use_are_stated_rather_than_implied():
    """A list, not a wildcard: the fallbacks are OFL faces and the excluded one is named."""
    assert SC.FONT_ALIASES["arial.ttf"] == (
        "arial.ttf", "LiberationSans-Regular.ttf", "NotoSans-Regular.ttf")
    assert SC.FONT_ALIASES["arialbd.ttf"] == (
        "arialbd.ttf", "LiberationSans-Bold.ttf", "NotoSans-Bold.ttf")
    assert "DejaVuSans.ttf" in SC.LICENCE_UNVERIFIED_FACES


# -------------------------------------------- the machine condition, split from the contract
#
# Wave 6, F-bb57fe5b. Both tests below stated the P7 contract and then converted their own
# failure into a SKIP: `except SC.FontError as e: pytest.skip(f"no permitted face on this
# machine: {e}")`. Measured in a scratch copy by reverting the fix — `font_search_paths()`
# -> `[FONT_DIR]`, the pre-P7 behaviour — the contract test SKIPPED, with the reason "no
# permitted face on this machine", a statement that is false on a rig holding
# C:\WINDOWS\Fonts\arial.ttf, while five siblings in the same file failed. The regression
# each exists to catch turned it green and put an untrue sentence in the skip reason.
#
# The two conditions are different objects and are now measured separately: whether THIS
# MACHINE has a permitted face is decided once, at import, through the module's own
# resolver on its own directories; whether the CONTRACT holds is decided inside the test,
# where a FontError is a failure and says so.


def _machine_has_a_permitted_face():
    """One measurement, at import, before any test has patched anything."""
    saved = os.environ.pop(SC.FONT_ENV, None)
    try:
        SC.clear_font_index()
        SC.resolve_font_path("arial.ttf")
        return True
    except SC.FontError:
        return False
    finally:
        if saved is not None:
            os.environ[SC.FONT_ENV] = saved
        SC.clear_font_index()


HAS_A_PERMITTED_FACE = _machine_has_a_permitted_face()

#: The machine condition, and nothing else. A regression in `sheet_compose` cannot reach
#: this mark: it is evaluated once at import against the unpatched module.
requires_a_permitted_face = pytest.mark.skipif(
    not HAS_A_PERMITTED_FACE,
    reason=("this machine has none of the permitted faces (arial / LiberationSans / "
            "NotoSans) in ARMATURE_FONT_DIR or any platform font directory"))


@requires_a_permitted_face
def test_this_machine_resolves_a_face_and_says_where_it_came_from():
    """Attempted, never skipped from inside: on a machine that HAS a face, a FontError
    here is the regression this test exists to catch and must be a failure."""
    path = SC.resolve_font_path("arial.ttf")
    assert os.path.isfile(path)
    assert SC.font(("arial.ttf"), 26).path == path


@requires_a_permitted_face
def test_font_dir_is_no_longer_consulted_at_all(monkeypatch):
    """The tests domain's contract for P7: with `FONT_DIR` pointed at a directory that does
    not exist, `_font` must still resolve — because the constant is not what resolution
    reads. It is kept only as a name for callers that still reference it.

    The FontError is deliberately NOT caught. Reverting `font_search_paths()` to
    `[FONT_DIR]` makes this test fail, where it used to skip with a false reason."""
    monkeypatch.setattr(SC, "FONT_DIR", os.path.join("Z:", "nowhere", "Fonts"))
    monkeypatch.delenv(SC.FONT_ENV, raising=False)
    f = SC._font("arial.ttf", 26)
    assert os.path.isfile(f.path)
    assert "nowhere" not in f.path


def test_the_skip_reason_is_a_machine_fact_this_file_measured():
    """A skip reason is a claim. This one is the return of `_machine_has_a_permitted_face`,
    measured through the module's own resolver — not an exception caught from a test whose
    subject is the resolver itself."""
    assert HAS_A_PERMITTED_FACE == _machine_has_a_permitted_face()
    if HAS_A_PERMITTED_FACE:
        assert os.path.isfile(SC.resolve_font_path("arial.ttf"))


def test_the_private_font_helper_keeps_its_signature():
    """`sheet_compose._font(name, size)` is the entry point the sheet tests resolve
    through; the search moved underneath it, the call shape did not."""
    import inspect

    assert list(inspect.signature(SC._font).parameters) == ["name", "size"]
    assert list(inspect.signature(SC.font).parameters) == ["name", "size"]


def test_all_three_composers_resolve_through_the_one_implementation():
    """P7 is 'fix the family, not the instance': rig_sheet_compose carried the same
    constant and make_cast_sheet inlined two absolute paths with no constant at all, so
    the FONT_DIR guard could not even reach it."""
    import make_cast_sheet
    import rig_sheet_compose

    # Identity was the wrong assertion, and wave 5 found the reason: `from sheet_compose
    # import font as _font` binds the function OBJECT at import, so a substitution
    # installed on `sheet_compose` reached `sheet_compose` and NEITHER composer. Each now
    # delegates at CALL time, which is what "the one implementation" has to mean.
    seen = []
    saved = SC._font
    SC._font = lambda name, size: seen.append((name, size)) or saved(name, size)
    try:
        rig_sheet_compose._font("arial.ttf", 26)
        make_cast_sheet._font("arial.ttf", 26)
    finally:
        SC._font = saved
    assert seen == [("arial.ttf", 26), ("arial.ttf", 26)], seen
    for mod in (rig_sheet_compose, make_cast_sheet):
        src = open(mod.__file__, encoding="utf-8").read()
        body = src.split('"""', 2)[-1]
        assert "Windows" not in body or "Fonts" not in body


# ------------------------------------------ the fixture that names three and reached one
#
# Wave 6, F-c707995d. `conftest.sheet_fonts` said it let "the sheet composers" run on a
# machine with no platform fonts, and monkeypatched `sheet_compose._font` alone. The two
# tests above record why that cannot work: `rig_sheet_compose._font` and
# `make_cast_sheet._font` ARE `sheet_compose.font`, a different object bound at import, so
# the patch never reached either. Measured by simulating a fontless runner and running the
# whole suite: exactly two tests failed, both layout-width fixtures, both raising through
# `rig_sheet_compose.py::_font` and `make_cast_sheet.py::_font` — under the module-wide
# `usefixtures("sheet_fonts")` that was added to stop precisely that.


def _modules_binding_the_shared_resolver():
    """Enumerated from `tools/`, not typed: every module other than `sheet_compose` that
    carries a `_font` of its own.

    Deliberately shape-independent. A composer may reach the shared resolver by
    `from sheet_compose import font as _font` (a reference bound at import — the shape that
    made the fixture miss two of three) or by a wrapper that calls
    `sheet_compose._font(name, size)` at call time. Both are `_font` in the module, and
    which one is in the tree is not this census's question: the census is WHICH MODULES the
    fixture has to reach.
    """
    import glob

    tools = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "tools")
    found = []
    for path in sorted(glob.glob(os.path.join(tools, "*.py"))):
        stem = os.path.basename(path)[:-3]
        if stem == "sheet_compose":
            continue
        with open(path, encoding="utf-8") as fh:
            if "_font" in fh.read():
                found.append(stem)
    return found


def test_the_fixtures_composer_list_is_the_composers_the_tree_has():
    """The census. A fourth sheet module that binds the shared resolver joins the fixture
    here rather than discovering on a fontless runner that nobody patched it."""
    import conftest

    assert sorted(conftest.SHEET_COMPOSERS) == sorted(
        ["sheet_compose"] + _modules_binding_the_shared_resolver())


def test_the_sheet_fonts_fallback_reaches_every_composer(monkeypatch):
    """The fixture's own claim, exercised on a machine that HAS fonts.

    The fontless runner is simulated first — no env override, no platform directories, the
    index cleared — and each composer is shown raising before the fallback is installed and
    resolving after. Without the simulation this test would be vacuous on any rig with a
    font, which is how the defect survived.
    """
    import conftest
    import make_cast_sheet
    import rig_sheet_compose

    composers = {"sheet_compose": SC, "rig_sheet_compose": rig_sheet_compose,
                 "make_cast_sheet": make_cast_sheet}
    assert set(composers) == set(conftest.SHEET_COMPOSERS)

    monkeypatch.delenv(SC.FONT_ENV, raising=False)
    monkeypatch.setattr(SC, "platform_font_dirs", lambda: [])
    SC.clear_font_index()
    for name, mod in composers.items():
        with pytest.raises(SC.FontError):
            mod._font("arialbd.ttf", 30)

    conftest.install_sheet_font_fallback(monkeypatch)

    for name, mod in composers.items():
        f = mod._font("arialbd.ttf", 30)
        assert f is not None, f"{name} still cannot resolve a face"
        assert f.size == 30, f"{name}'s fallback ignores the requested size"


def test_every_composer_answers_with_whatever_sheet_compose_would_answer(monkeypatch):
    """The property the fixture depends on, stated without naming a binding shape.

    A composer may hold its own reference bound at import, or delegate at call time; what
    the sheet fixture needs either way is that no composer resolves a face
    `sheet_compose` would not. Asserted by making the shared resolver answer with a
    sentinel and requiring every composer to return it — the patch reaches a delegating
    wrapper directly and a bound reference through `install_sheet_font_fallback`.
    """
    import conftest
    import make_cast_sheet
    import rig_sheet_compose

    sentinel = object()
    monkeypatch.setattr(SC, "_font", lambda name, size: sentinel)
    monkeypatch.setattr(SC, "font", lambda name, size: sentinel)
    for mod in (rig_sheet_compose, make_cast_sheet):
        if mod._font("arial.ttf", 26) is sentinel:
            continue
        # A reference bound at import cannot see the patch above; the fixture's own
        # installer is what reaches it, and that is exactly why the census exists.
        assert mod.__name__ in conftest.SHEET_COMPOSERS, (
            f"{mod.__name__} holds its own resolver reference and is not in "
            f"conftest.SHEET_COMPOSERS, so the sheet_fonts fixture cannot reach it")
