"""sheet_compose — assemble rendered panels into a dailies sheet.

    <venv-python> tools\\sheet_compose.py <out-dir>/panels.json

Separate from the renderers because Blender's bundled Python carries no PIL. A renderer
writes `panels.json`; this reads it and composites. Nothing irreversible waits on this step,
which is why a two-step is acceptable here and would not be for a gate.

**Panels are pasted at their rendered size and never resampled.** Every camera in a row
shares one orthographic scale, so a millimetre of character is the same number of pixels in
every panel of that row and the joint insets are true 1:1. Resizing here to make a row fit
would silently destroy both properties, so a row that is too wide makes the sheet wider
rather than making the panels smaller.

The spec is generic: a title, a subtitle, and a list of rows, each row a title and a list of
panels. A panel names a body render and optionally an overlay to composite over it.

--------------------------------------------------------------------------------
The typeface is resolved here, and stated on the output line

`_font` used to be `ImageFont.truetype(os.path.join(r'C:\\Windows\\Fonts', name), size)`.
Pillow catches its own OSError, takes the BASENAME, and walks the platform's font
directories for a file of that name — measured on this rig with Pillow 12.3.0, a font
requested from a nonexistent directory came back with `.path` of `C:\\WINDOWS\\fonts\\arial.ttf`.
So the constant's value was never load-bearing; only its basename was. On a POSIX runner
`posixpath.join(r'C:\\Windows\\Fonts', 'arial.ttf')` is a RELATIVE string, so the intended
directory is never consulted at all: the sheet is typeset from whatever the basename walk
finds, with nothing said, or dies with `OSError: cannot open resource` naming neither the
directory nor the file.

`resolve_font_path` replaces both outcomes with an explicit ordered search — the
`ARMATURE_FONT_DIR` override, then the platform's own font directories, walked — and a
`FontError` naming every directory and every face tried when none resolves. The resolved
path is printed on the sheet's own `SHEET_COMPOSE_OK` line, so a substituted typeface is
stated
rather than silent.

**Which faces, and their licences.** The requested face first (a system font already on
the machine; using one is not redistributing it), then `LiberationSans` (SIL OFL 1.1) and
`NotoSans` (SIL OFL 1.1). DejaVu is deliberately NOT in that list: it is present on most
Linux boxes, but its licence document could not be fetched from the seat that wrote this,
and this repo treats a licence it cannot retrieve as NO. It is named in the refusal instead
of quietly substituted. No font binary is committed here — that would need a licence-map row
of its own, and big binaries stay out of git.
"""

import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core.errors import ArmatureError  # noqa: E402

class SheetPopulationError(ArmatureError):
    """A panel cannot show what it was asked to show, and would not have said so.

    `if fi >= len(names): continue` dropped every requested index past the end of a
    listing. Measured 2026-09-03 on `make_gate0_sheet`: a 3-frame control and a 3-frame
    output asked for `--frames=0,8,16,24` saved a ONE-column sheet, exit 0, with nothing
    on the panel or in the record saying three of the four requested frames were absent —
    and when EVERY requested index was dropped it died instead at `cols[0][1].width` with
    a bare `IndexError` naming nothing.

    `make_identity_sheet` was given this refusal in wave 3, because dropping one silently
    shows the Director fewer angles than were asked for on the panel where identity is
    judged. Four siblings kept the `continue`; `require_frames` is that one refusal, in
    one place, for all of them.
    """

    def __init__(self, message, evidence=None):
        super().__init__(message)
        self.evidence = evidence or {}


#: The RGB plate a sheet composites an RGBA tile over before drawing it.
#:
#: Black, which is what all five composing sheets used — hard-coded, in five copies, and
#: recorded nowhere. The Director's authored-RGBA ruling is that "the RGB composite each
#: route actually submits is a deliberate, recorded choice", and `composite_reference`
#: records exactly that for the submitted plates (`plate_rgb_srgb` + `plate_why`), with
#: `SURVEY_PLATE = (154, 154, 157)` as the value his eye passed on the S03 kit. So a
#: reference could be composited over black on the panel while the route composited the
#: same master over mid-grey, and the panel said nothing — the difference then reads as a
#: difference in the OUTPUT. The plate is a parameter here, and every sheet prints it.
SHEET_PLATE = (0, 0, 0)


def load_rgb_over_plate(path, plate=SHEET_PLATE):
    """One RGB tile for a sheet, and the record of how its alpha was disposed of.

    Deliberately not `Image.convert("RGB")`, which drops alpha silently onto whatever RGB
    the author made invisible. This composites through the alpha, like the five copies it
    replaces — the difference is that the plate is named, returned, and printable.
    """
    im = Image.open(path)
    if im.mode == "1":
        # A bilevel mask. `make_sheet` special-cased this before routing here.
        im = im.convert("L")
    if im.mode in ("RGBA", "LA", "PA") or "transparency" in im.info:
        src = im.convert("RGBA")
        flat = Image.new("RGB", src.size, tuple(int(v) for v in plate))
        flat.paste(src, mask=src.split()[3])
        return flat, {
            "plate_rgb_srgb": [int(v) for v in plate],
            "alpha_disposition": (f"composited over the named sheet plate "
                                  f"{tuple(int(v) for v in plate)}"),
        }
    return im.convert("RGB"), {
        "plate_rgb_srgb": None,
        "alpha_disposition": "no alpha channel in the source",
    }


def frames_by_number(names, *, where, what="frame(s)", exc=SheetPopulationError,
                     evidence=None):
    """`{frame NUMBER: name}` off a listing, or raise naming the stray.

    The `make_crop_strip.frames_by_number` shape, lifted here as ONE implementation for
    the eight `require_frames` call sites rather than a copy per sheet — wave 12,
    F-e96ed69b. (All eight pass `numbers=` derived from this function: `make_gate0_sheet`
    :177/:179, `make_identity_sheet` :128, `make_lift_sheet` :228/:230/:232,
    `make_review_clip` :161, `make_startframe_sheet` :140.)

    **The two functions differ in more than directory-versus-listing, and the difference is
    the load-bearing one** (F-90c26d7b, wave 14 — this paragraph used to say the only
    difference was the argument type). `make_crop_strip.frames_by_number` takes a DIRECTORY
    and returns paths; it also FILTERS a non-numbered PNG out of the listing and refuses
    only when nothing numbered survives. This one RAISES on a stray. Both behaviours are
    deliberate and neither is the other's bug:

    * here, the stray would be pasted into a sheet and shown to the Director as a frame of
      this run, under a caption naming a frame number it does not have;
    * there, the population is a frames directory this repo's own tools write contact
      strips into (`render_pose_sticks` writes `strip_every<N>.png` beside its frames), so
      raising would refuse the ordinary input — and since wave 14 the strays it drops are
      RECORDED in the sidecar and printed on the tool's own line, rather than silently
      narrowing a population whose whole product is provenance a later reader can re-cut
      from.

    `make_identity_sheet._numbered_population` carried this refusal alone; it now delegates
    here.
    """
    names = list(names)
    numbered = [n for n in names if os.path.splitext(str(n))[0].isdigit()]
    unexpected = [n for n in names if n not in set(numbered)]
    if unexpected:
        raise exc(
            f"{where} holds {len(unexpected)} PNG(s) that are not numbered {what} "
            f"({', '.join(str(u) for u in unexpected[:8])}); a stray sorts into the "
            f"population and is drawn as a tile of the run under a caption naming a frame",
            dict(evidence or {}, gate="FRAMES", where=str(where),
                 unexpected=[str(u) for u in unexpected],
                 frames=sorted(str(n) for n in numbered)))
    return {int(os.path.splitext(str(n))[0]): n for n in numbered}


def require_frames(requested, population, *, what, where, exc=SheetPopulationError,
                   numbers=None):
    """Every requested index EXISTS in `population`, or raise naming the shortfall.

    Returns the evidence dict when it holds — a gate whose passing verdict is never
    written down is a gate nobody can read.

    `numbers` switches the bound from POSITION to the frames' own NUMBERS — one
    implementation with two modes rather than a second copy of the refusal, because the
    two questions differ only in what "exists" means. A run numbered 00001..00003 holds
    no frame 0, and the positional bound (`0 <= i < n`) admits it: measured 2026-09-04,
    `make_identity_sheet` drew that run's FIRST file under the caption `f000`. Pass the
    population's frame numbers and the same evidence dict carries `frame_numbers` beside
    `missing_indices`.
    """
    requested = list(requested)
    n = len(population)
    if numbers is None:
        missing = [i for i in requested if i < 0 or i >= n]
    else:
        available = set(int(v) for v in numbers)
        missing = [i for i in requested if i not in available]
    ev = {"gate": "FRAMES", "what": what, "where": str(where), "n_frames": n,
          "requested": requested, "missing_indices": missing}
    if numbers is not None:
        ev["frame_numbers"] = sorted(int(v) for v in numbers)[:64]
    if missing or not n or not requested:
        raise exc(
            f"{where} holds {n} {what} and frame(s) {missing} of the requested "
            f"{requested} are not among them; a panel built from whichever of them happen "
            f"to exist shows fewer than were asked for and says nothing about it", ev)
    ev["verdict"] = (f"all {len(requested)} requested "
                     f"{'frame numbers' if numbers is not None else 'indices'} exist "
                     f"in {n} {what}")
    return ev


BG, INK, SUB = (22, 22, 24), (238, 238, 240), (166, 166, 172)
PAD, LABEL_H, ROW_TITLE_H, TITLE_H = 26, 54, 46, 150

#: os.pathsep-separated directories searched BEFORE the platform's own. Read at call time,
#: so a run can be pinned to a known face without editing the module.
FONT_ENV = "ARMATURE_FONT_DIR"

#: The faces this repo may typeset with, per requested name, in preference order.
FONT_ALIASES = {
    "arial.ttf": ("arial.ttf", "LiberationSans-Regular.ttf", "NotoSans-Regular.ttf"),
    "arialbd.ttf": ("arialbd.ttf", "LiberationSans-Bold.ttf", "NotoSans-Bold.ttf"),
}

#: Faces that exist on many machines and that this repo will NOT use: their licence
#: documents have not been fetched into `docs/license-map.md`, and an unretrieved licence
#: is treated as NO. Named in the refusal so the operator knows why the sheet stopped.
LICENCE_UNVERIFIED_FACES = ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf",
                            "DejaVuSansMono.ttf", "FreeSans.ttf")

_FONT_EXTS = (".ttf", ".otf", ".ttc")
_FONT_INDEX_CACHE = {}

#: Kept as a NAME only, for callers that still reference it. It is no longer consulted:
#: `platform_font_dirs()` derives the Windows directory from %WINDIR%.
FONT_DIR = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")


class FontError(ArmatureError):
    """No permitted typeface could be found. Names every path and face that was tried."""

    def __init__(self, message, evidence=None):
        super().__init__(message)
        self.evidence = evidence or {}


def platform_font_dirs():
    """Where this operating system keeps its fonts. No repo constant decides this."""
    home = os.path.expanduser("~")
    if sys.platform == "win32":
        windir = os.environ.get("WINDIR", r"C:\Windows")
        local = os.environ.get("LOCALAPPDATA", os.path.join(home, "AppData", "Local"))
        return [os.path.join(windir, "Fonts"),
                os.path.join(local, "Microsoft", "Windows", "Fonts")]
    if sys.platform == "darwin":
        return ["/System/Library/Fonts", "/Library/Fonts",
                os.path.join(home, "Library", "Fonts")]
    xdg = os.environ.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share")
    return [os.path.join(xdg, "fonts"), "/usr/local/share/fonts", "/usr/share/fonts",
            os.path.join(home, ".fonts")]


def font_search_paths():
    """The override, then the platform. Order is the preference."""
    dirs = [d for d in os.environ.get(FONT_ENV, "").split(os.pathsep) if d.strip()]
    return dirs + list(platform_font_dirs())


def clear_font_index():
    """Forget what was found. The index is a cache, not state."""
    _FONT_INDEX_CACHE.clear()


def _font_index(dirs):
    key = tuple(dirs)
    if key in _FONT_INDEX_CACHE:
        return _FONT_INDEX_CACHE[key]
    index = {}
    for d in dirs:
        if not os.path.isdir(d):
            continue
        # Walked, not joined: Linux nests its fonts (/usr/share/fonts/truetype/<family>/),
        # so a flat join finds nothing there even when the face is installed.
        for root, _sub, files in os.walk(d):
            for f in files:
                if f.lower().endswith(_FONT_EXTS):
                    index.setdefault(f.lower(), os.path.join(root, f))
    _FONT_INDEX_CACHE[key] = index
    return index


def resolve_font_path(name):
    """The absolute path of the face to typeset `name` with, or raise naming what was tried.

    Always an absolute path this function found itself — never a bare basename handed to
    Pillow, which would let its own platform walk decide the typeface from a directory
    nobody named.
    """
    dirs = font_search_paths()
    index = _font_index(dirs)
    faces = FONT_ALIASES.get(name, (name,))
    for face in faces:
        hit = index.get(face.lower())
        if hit:
            return hit
    seen_unverified = [f for f in LICENCE_UNVERIFIED_FACES if f.lower() in index]
    note = ""
    if seen_unverified:
        note = (f" Found but NOT used: {', '.join(seen_unverified)} — no licence row in "
                f"docs/license-map.md, and an unretrieved licence is treated as NO.")
    raise FontError(
        f"no permitted typeface for {name!r}. Tried {', '.join(faces)} under "
        f"{', '.join(dirs) or '(no directories)'}.{note} Set {FONT_ENV} to a directory "
        f"holding one of them, or install an SIL OFL face (Liberation, Noto)",
        {"requested": name, "faces_tried": list(faces), "directories": list(dirs),
         "found_but_licence_unverified": seen_unverified},
    )


def font(name, size):
    """A loaded face, from a path this module resolved. Raises rather than substituting."""
    return ImageFont.truetype(resolve_font_path(name), size)


def _font(name, size):
    return font(name, size)


def max_text_width(pairs):
    """The widest rendered string among `(text, font)` pairs, in pixels.

    Shared with `rig_sheet_compose` and `make_cast_sheet`, which sized themselves to their
    panels alone and cropped their own parameter lines.
    """
    ruler = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    widths = [ruler.textlength(t, font=f) for t, f in pairs if t]
    return max(widths) if widths else 0.0


def _panel(spec):
    im = Image.open(spec["body"]).convert("RGBA")
    if spec.get("overlay"):
        ov = Image.open(spec["overlay"]).convert("RGBA")
        alpha = float(spec.get("overlay_alpha", 0.92))
        ov.putalpha(ov.getchannel("A").point(lambda v: int(v * alpha)))
        im = Image.alpha_composite(im, ov)
    return im.convert("RGB")


def main():
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    f_title, f_row, f_lab = (_font("arialbd.ttf", 44), _font("arialbd.ttf", 30),
                             _font("arial.ttf", 26))

    rows = [(r["title"], [(_panel(p), p.get("label", "")) for p in r["panels"]])
            for r in spec["rows"]]

    # The sheet is as wide as its widest ROW **or its longest line of text**. Sizing to the
    # panels alone silently crops every title and label that overruns them, which on a sheet
    # whose whole job is carrying gate numbers to a human means the numbers are the first
    # thing to disappear — and a cropped sheet still saves, still opens, and looks fine.
    text_w = max_text_width(
        [(spec["title"], f_title), (spec.get("subtitle", ""), f_lab)]
        + [(t, f_row) for t, _ in rows]
        + [(lab, f_lab) for _, panels in rows for _, lab in panels])
    width = max(
        max(PAD + sum(im.width + PAD for im, _ in panels) for _, panels in rows),
        int(PAD + text_w + PAD) + 6)
    # A ROW is as tall as its tallest panel, not as its first. Panels are pasted at their
    # rendered size and never resampled (the rule this module exists for), so a row whose
    # later panels are taller than its first used to overflow into the next row and off the
    # bottom of the sheet — cropped in silence, with the success sentinel printed.
    row_heights = [max(im.height for im, _ in panels) for _, panels in rows]
    height = TITLE_H + sum(ROW_TITLE_H + rh + LABEL_H + PAD for rh in row_heights) + PAD
    sheet = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(sheet)

    d.text((PAD, 30), spec["title"], font=f_title, fill=INK)
    d.text((PAD, 88), spec.get("subtitle", ""), font=f_lab, fill=SUB)

    y = TITLE_H
    for (title, panels), row_h in zip(rows, row_heights):
        d.text((PAD, y), title, font=f_row, fill=INK)
        y += ROW_TITLE_H
        x = PAD
        for im, label in panels:
            sheet.paste(im, (x, y))
            if label:
                d.text((x + 6, y + row_h + 12), label, font=f_lab, fill=SUB)
            x += im.width + PAD
        y += row_h + LABEL_H + PAD

    # Scripts create their own output directories — two facet runs died on this, and a
    # compose step should not depend on whichever renderer happened to run first.
    out_dir = spec["out"]
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, spec.get("filename", "sheet.png"))
    sheet.save(path)
    # Its OWN token -- see make_cast_sheet for the four-way collision this retires.
    print(f"SHEET_COMPOSE_OK {path} font={f_lab.path}")


if __name__ == "__main__":
    main()
