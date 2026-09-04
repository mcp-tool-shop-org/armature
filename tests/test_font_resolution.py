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


def test_this_machine_resolves_a_face_and_says_where_it_came_from():
    """Not skipped on a directory's existence — attempted, and skipped only if this machine
    genuinely has none of the permitted faces, which is itself the thing worth reporting."""
    try:
        path = SC.resolve_font_path("arial.ttf")
    except SC.FontError as e:
        pytest.skip(f"no permitted face on this machine: {e}")
    assert os.path.isfile(path)
    assert SC.font(("arial.ttf"), 26).path == path


def test_font_dir_is_no_longer_consulted_at_all(monkeypatch):
    """The tests domain's contract for P7: with `FONT_DIR` pointed at a directory that does
    not exist, `_font` must still resolve — because the constant is not what resolution
    reads. It is kept only as a name for callers that still reference it."""
    monkeypatch.setattr(SC, "FONT_DIR", os.path.join("Z:", "nowhere", "Fonts"))
    monkeypatch.delenv(SC.FONT_ENV, raising=False)
    try:
        f = SC._font("arial.ttf", 26)
    except SC.FontError as e:
        pytest.skip(f"no permitted face on this machine: {e}")
    assert os.path.isfile(f.path)
    assert "nowhere" not in f.path


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
