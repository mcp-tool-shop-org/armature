"""Cast-survey sheet: one row per subject — full 3/4 front, full back, head front,
head back, and a stats label. Consumes preview_glb.py output.

python make_cast_sheet.py --dir <preview_out> --names a,b,c --title "..." --out sheet.png

Diagnostic presentation tool, not a pipeline gate. Dailies standard: uniform panel
scale across rows, labels readable at review distance, no internal gate states.

Two things carried across from `sheet_compose`, which had already paid for both: the sheet
is as wide as its longest LABEL as well as its widest row (the stats line is the whole
point of this sheet and was the first thing cropped), and the typeface is resolved through
an explicit search that raises when nothing is found rather than through two absolute
`C:\\Windows\\Fonts` literals that a POSIX runner turns into relative strings.
Halt contract: exit 0 on success, 2 on a deliberate refusal (one <TOOL>_HALT JSON line; evidence.clause is the branch word), 1 on a crash. See README §"Reading a halt" and armature_core.parts.run_tool_main.
"""
import argparse
import json
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from armature_core.errors import ArmatureError  # noqa: E402

#: The four panels `preview_glb` writes per subject, and the six keys its `<name>_stats.json`
#: sidecar carries that this label reads. Stated ONCE, at module level, because they are the
#: contract with `preview_glb` and a refusal that cannot name what it expected is not much of
#: a refusal. F-c66ad0c4, wave 25.
PANEL_SUFFIXES = ("full_a", "full_b", "head_a", "head_b")
STATS_KEYS = ("armatures", "triangles", "mesh_objects", "materials", "empties", "images")



HALT_EPILOG = 'Halt contract: exit 0 on success, 2 on a deliberate refusal (one <TOOL>_HALT JSON line; evidence.clause is the branch word), 1 on a crash. See README §"Reading a halt".'

class CastSheetError(ArmatureError):
    """This cast survey cannot be produced as asked. One typed refusal for this tool.

    Measured on `580af47` by AST walk over `tools/*.py`: this module held ZERO `raise`
    statements, in a domain where fourteen sibling sheets each define a family class. `main`
    split `--names` unvalidated, opened four panel files per subject with a bare
    `Image.open`, read six keys off a `<name>_stats.json` sidecar with bare subscripts and
    indexed into their contents, then computed `max(...)` over `rows` with no emptiness
    guard. Driven as real processes with the repo venv: `--names=` exited 1 with
    `ValueError: max() iterable argument is empty` - an arithmetic error out of PIL's layout
    maths, on the tool whose job is to survey a cast - and `--names=ghost` exited 1 with
    `FileNotFoundError: [Errno 2] No such file or directory: '<dir>/ghost_full_a.png'`,
    naming one path and neither the subject nor which of the five expected artifacts was
    missing.
    """

def _font(name, size):
    """The face, resolved at CALL time through `sheet_compose`'s one implementation —
    `from sheet_compose import font as _font` bound the function OBJECT at import, so this
    module held a different callable from the one `sheet_compose` itself calls."""
    import sheet_compose

    return sheet_compose._font(name, size)

from sheet_compose import max_text_width  # noqa: E402

FULL_H = 440
HEAD_H = 440
PAD = 14
LABEL_H = 56
BG = (238, 238, 240)
INK = (20, 20, 24)
SUB = (90, 90, 100)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="the cast survey the Director compares subjects on: one row per "
                    "subject, four preview_glb panels and a stats label",
        epilog=HALT_EPILOG)
    ap.add_argument("--dir", required=True,
                    help="the directory holding each subject's preview_glb panels and "
                         "<name>_stats.json sidecar")
    ap.add_argument("--names", required=True, help="comma-separated subject names, row order")
    ap.add_argument("--title", required=True, help="the title drawn at the top of the sheet")
    ap.add_argument("--out", required=True, help="the sheet image to write")
    args = ap.parse_args(argv)

    font_b = _font("arialbd.ttf", 30)
    font_r = _font("arial.ttf", 24)

    subjects = [n.strip() for n in args.names.split(",") if n.strip()]
    # ---- ANDON, before a file is opened: a survey of no subjects is not a survey, and the
    #      empty list reached `max(...)` over `rows` as an arithmetic error instead.
    if not subjects:
        raise CastSheetError(
            f"--names={args.names!r} names no subject; a cast survey of nothing is not a "
            f"sheet, and the empty row list reaches the layout maths as "
            f"`max() iterable argument is empty`",
            {"gate": "ARGS", "andon": "CastSheetError", "clause": "subject_list_is_empty",
             "flag": "--names", "supplied": args.names})

    rows = []
    for name in subjects:
        panels = []
        for suf in PANEL_SUFFIXES:
            path = os.path.join(args.dir, f"{name}_{suf}.png")
            # ---- ANDON naming the SUBJECT and which of its five artifacts is absent.
            if not os.path.isfile(path):
                raise CastSheetError(
                    f"subject {name!r} has no {suf} panel at {path}; this sheet is a "
                    f"comparison ACROSS subjects, so a row built from three panels of four "
                    f"would be read beside complete rows as a difference in the subject",
                    {"gate": "INPUT", "andon": "CastSheetError",
                     "clause": "subject_panel_is_not_on_disk",
                     "subject": name, "panel": suf, "file": path, "dir": args.dir,
                     "expected": [f"{name}_{p}.png" for p in PANEL_SUFFIXES]
                                 + [f"{name}_stats.json"],
                     "subjects": subjects})
            im = Image.open(path).convert("RGB")
            h = FULL_H if suf.startswith("full") else HEAD_H
            panels.append(im.resize((round(im.width * h / im.height), h), Image.LANCZOS))
        stats_path = os.path.join(args.dir, f"{name}_stats.json")
        if not os.path.isfile(stats_path):
            raise CastSheetError(
                f"subject {name!r} has no stats sidecar at {stats_path}; the stats line is "
                f"this sheet's whole payload",
                {"gate": "INPUT", "andon": "CastSheetError",
                 "clause": "subject_stats_sidecar_is_not_on_disk",
                 "subject": name, "file": stats_path, "dir": args.dir,
                 "expected": [f"{name}_{p}.png" for p in PANEL_SUFFIXES]
                             + [f"{name}_stats.json"],
                 "subjects": subjects})
        with open(stats_path, encoding="utf-8") as f:
            st = json.load(f)
        # ---- ANDON on the CONTRACT with `preview_glb`: the six keys the label reads.
        absent = [k for k in STATS_KEYS if k not in st]
        if absent:
            raise CastSheetError(
                f"{stats_path} carries no {', '.join(absent)}; the label this sheet exists "
                f"to show is read off those keys, and a bare subscript would name one word "
                f"and neither the subject nor the document",
                {"gate": "INPUT", "andon": "CastSheetError",
                 "clause": "stats_document_is_missing_a_key",
                 "subject": name, "file": stats_path, "missing": absent,
                 "expected_keys": list(STATS_KEYS), "given": sorted(st)})
        arm_txt = "no armature" if not st["armatures"] else \
            f"armature: {st['armatures'][0][1]} bones ({', '.join(st['armatures'][0][2][:3])}...)"
        tex = [i for i in st["images"] if i[1][0] > 0]
        label = (f"{name}   -   {st['triangles']:,} tris, {st['mesh_objects']} mesh obj, "
                 f"{st['materials']} mats, {len(tex)} tex ({', '.join(str(t[1][0]) for t in tex[:3])} px), "
                 f"{st['empties']} empties, {arm_txt}")
        rows.append((panels, label))

    # As wide as the widest row **or the longest string drawn on it** — the stats label is
    # this sheet's whole payload and was cropped from the right, which is where the numbers
    # sit. sheet_compose.max_text_width is the one implementation.
    text_w = max_text_width([(args.title, font_b)] + [(lab, font_r) for _, lab in rows])
    row_w = max(max(sum(p.width for p in panels) + PAD * 5 for panels, _ in rows),
                int(PAD + text_w + PAD))
    title_h = 74
    sheet = Image.new("RGB", (row_w, title_h + sum(FULL_H + LABEL_H + PAD * 2 for _ in rows)), BG)
    d = ImageDraw.Draw(sheet)
    d.text((PAD, 18), args.title, font=font_b, fill=INK)
    y = title_h
    for panels, label in rows:
        x = PAD
        for p in panels:
            sheet.paste(p, (x, y))
            x += p.width + PAD
        d.text((PAD, y + FULL_H + 10), label, font=font_r, fill=SUB)
        y += FULL_H + LABEL_H + PAD * 2
    out_dir = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_dir, exist_ok=True)  # scripts create their own output directories
    sheet.save(args.out)
    # Its OWN token. `SHEET_OK` was printed by four tools -- this one, make_e13_sheet,
    # rig_sheet_compose and sheet_compose -- and it was the only shared success sentinel in
    # the tree, so a caller grepping a log for it could not say which panel was produced.
    # E07-the-skeleton.md:202-205 names SHEET_OK in the list of tokens the pipeline keys on.
    print("CAST_SHEET_OK", args.out, sheet.size, f"font={font_r.path}")
    return args.out


def _cli(argv=None):
    """The process entry point: an exit code, beside the sheet path `main` returns.

    WAVE 25, F-68f3fb4b — the shape `composite_reference._cli` took in wave 22, for the
    same reason.

    `main` returns the sheet's path, not an exit code, and this module ended in a bare
    `main()`. Handing that string to `raise SystemExit(...)` would print the path and exit
    1, so the wrapper is what keeps `main`'s return value a value.

    `main` keeps returning the sheet path; this wrapper is what `run_tool_main` runs, so the
    process gets 0 on success, 2 on a typed refusal and 1 on a crash.
    """
    main(argv)
    return 0


if __name__ == "__main__":
    # WAVE 25 (F-68f3fb4b): the ONE `__main__` halt handler, adopted BY IMPORT from
    # `armature_core.parts` (wave 22, SEAM 1 — core-solvers' file). This tool was one of
    # the 29 in `tests/test_instrument_exits.py::CPYTHON_HALT_CONTRACT_PENDING`: its
    # typed refusals reached the operator as a stdlib traceback at exit 1 — the code this
    # repo reserves for a crash — and the evidence dict naming the clause reached nothing.
    # Never copied; the point of the seam is that this block is one function with one home.
    from armature_core.parts import run_tool_main  # noqa: E402

    run_tool_main(_cli, "MAKE_CAST_SHEET")
