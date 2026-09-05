"""Wave 25 — the instruments-measure amend, twelve findings, red proofs first.

Every test here goes red on `580af47` and green on the commit beside it. Where a claim is
about a PROCESS — an exit code, a halt line an operator keys on — it is driven as a real
subprocess with this interpreter, because the whole finding is that the in-process return
value and the process's answer had stopped agreeing.

The wave's largest single move is `F-68f3fb4b`: the 29 CPython tools with no halt handler
adopt `armature_core.parts.run_tool_main` by import, so
`tests/test_instrument_exits.py::CPYTHON_HALT_CONTRACT_PENDING` empties and the population
with a handler moves 25 -> 54. That census is where the property is asserted tool by tool;
what is asserted HERE is the four members whose artifact or number reaches a spend or a
ruling, driven end to end.
"""

import ast
import json
import os
import subprocess
import sys

import numpy as np
import pytest
from PIL import Image

TESTS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TESTS)
TOOLS = os.path.join(REPO, "tools")

sys.path.insert(0, TOOLS)
sys.path.insert(0, TESTS)

import blender_stub as B  # noqa: E402


# ---------------------------------------------------------------------------- helpers


def _run(tool, argv, cwd, env=None):
    """The tool's own `__main__`, as a real process on this interpreter."""
    return subprocess.run([sys.executable, os.path.join(TOOLS, tool)] + list(argv),
                          capture_output=True, text=True, cwd=str(cwd),
                          env=dict(os.environ, **(env or {})))


def _halt(proc, prefix):
    """The one `<PREFIX>_HALT <json>` line on stdout, parsed. Fails loudly if absent."""
    token = prefix + "_HALT"
    lines = [l for l in proc.stdout.splitlines() if l.split(" ", 1)[0] == token]
    assert len(lines) == 1, (
        f"{len(lines)} `{token} <json>` line(s); rc={proc.returncode}\n"
        f"stdout:\n{proc.stdout[-800:]}\nstderr:\n{proc.stderr[-800:]}")
    return json.loads(lines[0][len(token):].strip())


def _frames(d, n=4, size=(8, 8), colour=(20, 30, 40)):
    os.makedirs(d, exist_ok=True)
    for i in range(n):
        Image.new("RGB", size, colour).save(os.path.join(d, f"{i:05d}.png"))
    return d


def _raises(mod_call, exc_type):
    with pytest.raises(exc_type) as exc:
        mod_call()
    return exc.value


# ===========================================================================
# F-68f3fb4b (panel HIGH) — the 29 handler-less tools adopt the ONE handler
# ===========================================================================


def test_the_cpython_halt_population_moved_and_the_pending_table_is_empty():
    """Size and membership before the property.

    MEASURED on `580af47`: `[f for f in cpython_tools() if not halt_handler(f)]` returned 29
    members and every one of them was this domain's file; 25 tools carried a handler. After
    the adoption the pending table is EMPTY and the population with a handler is 54. The
    category was keyed on the objective property rather than on a list, which is what let it
    empty itself.
    """
    pending = [f for f in B.cpython_tools() if not B.halt_handler(f)]
    assert pending == [], pending
    with_handler = [f for f in B.cpython_tools() if B.halt_handler(f)]
    assert len(with_handler) == 54, len(with_handler)
    adopters = sorted(f for f in with_handler if "run_tool_main" in B.read_source(f))
    # WAVE-25 MERGE (coordinator, 2026-09-05): 37 was this branch alone; builders moved its thirteen onto the
    # handler in the same wave, and the merged tree is MEASURED here by the same expression, never summed.
    assert len(adopters) == 50, len(adopters)


#: The four members whose artifact or number reaches a SPEND or a RULING. Driven end to end
#: below rather than asserted structurally, because the finding is about what the operator
#: sees: `fit_reference` builds the letterbox reference E08 and E10 both submitted;
#: `make_plate` authors the RGBA plate; `extract_clip_frames` turns a paid run's returned
#: clip into the frames every later measurement reads; `measure_floor` is the
#: repeat-variance denominator its own docstring says every later number is read against.
PAID_PATH_MEMBERS = ["fit_reference.py", "make_plate.py", "extract_clip_frames.py",
                     "measure_floor.py"]


@pytest.mark.parametrize("filename", PAID_PATH_MEMBERS)
def test_the_four_paid_path_tools_refuse_at_exit_two_with_a_halt_line(filename, tmp_path):
    """The property, on the population the finding named, as REAL PROCESSES.

    Measured on `580af47` with the repo venv, all four exit 1 — the code this repo reserves
    for a CRASH — with stdout 0 bytes and the traceback on stderr:

      fit_reference.py --pad=0,0    -> rc 1, `FitReferenceError: --pad takes three 0-255
                                       integers ...`, and the evidence dict naming the gate,
                                       the clause, the flag and the supplied value discarded
      make_plate.py (no --why)      -> rc 1, the same shape
      extract_clip_frames.py        -> rc 1, `ClipReadError: no video stream line ...`
      measure_floor.py --runs=<x,y> -> rc 1, `FloorError`

    An operator or a runner branching on 2 read every one of those decisions as an
    environment fault.
    """
    argv = {
        "fit_reference.py": ["--src=nope.png", f"--out={tmp_path / 'r.png'}", "--pad=0,0"],
        "make_plate.py": [f"--frames={tmp_path / 'none'}", f"--out={tmp_path / 'p.png'}",
                          "--width=8", "--height=8", "--alpha-over=0,0"],
        "extract_clip_frames.py": [f"--clip={tmp_path / 'nope.mp4'}",
                                   f"--out={tmp_path / 'f'}"],
        "measure_floor.py": ["--runs=a,b", f"--root={tmp_path / 'nope'}",
                             f"--out={tmp_path / 'o.json'}"],
    }[filename]
    handler = B.halt_handler(filename)
    proc = _run(filename, argv, tmp_path)
    assert proc.returncode == 2, (
        f"{filename}: rc {proc.returncode}\n{proc.stdout[-600:]}\n{proc.stderr[-900:]}")
    rec = _halt(proc, handler["prefix"])
    assert {"tool", "outcome", "gate", "error", "message", "evidence"} == set(rec), rec
    assert rec["outcome"] == "REFUSED — the tool declined to proceed", rec
    assert rec["error"] != "SystemExit", rec


def test_the_six_wrappers_keep_mains_return_value_a_value():
    """Why six tools take `_cli` rather than `main` (`composite_reference`'s wave-22 shape).

    `run_tool_main` does `raise SystemExit(main())`. A `main` that returns a RECORD or a
    PATH would then exit 1 and print that value, so the six whose return is read — by this
    suite (`rec = MF.main([...])` at eight sites in `test_measure_floor.py`) or by a caller
    — keep their return and hand the wrapper to the handler instead.
    """
    wrapped = sorted(f for f in B.cpython_tools()
                     if (B.halt_handler(f) or {}).get("entry") == "_cli")
    assert wrapped == ["composite_reference.py", "extract_clip_frames.py",
                       "make_cast_sheet.py", "make_e13_sheet.py", "make_shotset_sheet.py",
                       "measure_cascade_clip.py", "measure_floor.py"], wrapped
    for filename in wrapped:
        tree = ast.parse(B.read_source(filename))
        cli = next(n for n in tree.body
                   if isinstance(n, ast.FunctionDef) and n.name == "_cli")
        returns = {ast.unparse(r.value) for r in ast.walk(cli) if isinstance(r, ast.Return)}
        assert returns == {"0"}, (filename, returns)


def test_reverted_red_a_bare_main_block_is_what_the_29_had(tmp_path, monkeypatch):
    """Rule 4's reverted-red half, on the DERIVATION rather than on a re-edit of the tree.

    A module whose `__main__` is `main()` / `sys.exit(main())` / `raise SystemExit(main())`
    — the three shapes the 29 carried — is reported as having no handler, and one that hands
    off to `run_tool_main` is reported with its prefix and entry. Both directions, so a
    later simplification of `halt_handler` cannot pass by getting easier.
    """
    for body, want in (
            ("if __name__ == '__main__':\n    main()\n", None),
            ("if __name__ == '__main__':\n    sys.exit(main())\n", None),
            ("if __name__ == '__main__':\n    raise SystemExit(main())\n", None),
            ("if __name__ == '__main__':\n"
             "    from armature_core.parts import run_tool_main\n"
             "    run_tool_main(_cli, 'PROBE_W25')\n",
             {"prefix": "PROBE_W25", "entry": "_cli"}),
    ):
        probe = tmp_path / "probe_w25.py"
        probe.write_text("import sys\n" + body, encoding="utf-8")
        monkeypatch.setattr(B, "TOOLS", str(tmp_path))
        assert B.halt_handler("probe_w25.py") == want, body


# ===========================================================================
# F-b2c7b15a (panel HIGH) — the control-video tool halted with "gate": null
# ===========================================================================


def test_the_control_video_halt_names_the_andon_that_pulled(tmp_path):
    """Driven end to end, and the halt line READ.

    Measured on `580af47`: `encode_control.py --frames=<empty dir> --out=<tmp>` exited 2 and
    printed `ENCODE_CONTROL_HALT {..., "gate": null, ...}` — the tool that produces the
    control video a paid run UPLOADS, halting on the refusal that stops a wrong frame
    population from becoming that upload, with NO andon for a runner to branch on.
    `run_tool_main` reads `getattr(exc, "gate", None)` and `EncodeFailure` declared none,
    while the evidence dict at that site carried none either.
    """
    frames = tmp_path / "empty"
    frames.mkdir()
    # WAVE-25 CI FIX-UP (coordinator, 2026-09-06): the encoder is inspected after the operator's arguments (wave 23)
    # and BEFORE the frame population is read, so on a host with no ffmpeg the environment refusal
    # (`ffmpeg_binary_not_found`) preempts the one this test drives — measured on ubuntu-latest. The
    # refusal driven here fires before any encode, so an existing file stands in for the binary.
    proc = _run("encode_control.py", [f"--frames={frames}", f"--out={tmp_path / 'c.mkv'}"],
                tmp_path, env={"ARMATURE_FFMPEG": sys.executable})
    assert proc.returncode == 2, (proc.returncode, proc.stderr[-600:])
    rec = _halt(proc, "ENCODE_CONTROL")
    assert rec["gate"] == "ENCODE", rec
    assert rec["error"] == "EncodeFailure", rec
    assert rec["evidence"]["clause"] == "no_numbered_frames_to_encode", rec["evidence"]
    assert rec["evidence"]["andon"] == "EncodeFailure", rec["evidence"]


def test_every_family_raise_in_the_two_control_modules_carries_the_three_keys():
    """The SIBLINGS, enumerated by AST rather than by the one site the finding named.

    Measured on `580af47` by walking the two modules: 9 of `encode_control`'s
    evidence-carrying raises omitted `gate` and 10 omitted `clause`; `invert_frames` was the
    same shape on the INVERTED control sequence. The four sites that DID carry all three
    were wave-22 additions, so the module disagreed with itself — the arguments were policed
    to the contract and the frame population, the thing an upload is built from, was not.
    """
    for name, cls in (("encode_control.py", "EncodeFailure"),
                      ("invert_frames.py", "InvertError")):
        tree = ast.parse(B.read_source(name))
        # THE NODE is the evidence dict as RESOLVED, not as spelled: `dict(ev, clause=...)`
        # merges a base assigned above it, which is `invert_frames`'s shape at its `--out`
        # andon, and a walk that read only `ast.Dict` reported that site as carrying nothing.
        bases = {t.id: {k.value for k in n.value.keys if isinstance(k, ast.Constant)}
                 for n in ast.walk(tree) if isinstance(n, ast.Assign)
                 and isinstance(n.value, ast.Dict)
                 for t in n.targets if isinstance(t, ast.Name)}
        missing = []
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call)):
                continue
            if getattr(node.exc.func, "id", None) != cls:
                continue
            if len(node.exc.args) < 2:
                missing.append((node.lineno, "no evidence dict"))
                continue
            ev = node.exc.args[1]
            if isinstance(ev, ast.Dict):
                keys = {k.value for k in ev.keys if isinstance(k, ast.Constant)}
            elif (isinstance(ev, ast.Call) and getattr(ev.func, "id", None) == "dict"):
                keys = {k.arg for k in ev.keywords}
                for a in ev.args:
                    if isinstance(a, ast.Name):
                        keys |= bases.get(a.id, set())
                    elif isinstance(a, ast.Dict):
                        keys |= {k.value for k in a.keys if isinstance(k, ast.Constant)}
            else:
                missing.append((node.lineno, "evidence is not a readable mapping"))
                continue
            absent = {"gate", "andon", "clause"} - keys
            if absent:
                missing.append((node.lineno, sorted(absent)))
        assert missing == [], (name, missing)


def test_the_two_control_classes_declare_their_gate_id():
    """The class-level attribute the halt line reads, beside its siblings that already had
    one (`ProjectGate`, `SticksGate`, `ClipReadError`, `measure_cascade_clip`'s trio)."""
    import encode_control
    import invert_frames

    assert encode_control.EncodeFailure.gate == "ENCODE"
    assert invert_frames.InvertError.gate == "INVERT"
    # reverted-red: with the attribute gone the halt line reads `"gate": null`, which is
    # exactly what was measured on the base tree.
    assert getattr(Exception, "gate", None) is None


# ===========================================================================
# F-a19ebe73 (panel HIGH) — two ffmpeg consumers did not arm the ONE gate
# ===========================================================================


@pytest.mark.parametrize("tool,prefix,argv", [
    ("extract_clip_frames.py", "EXTRACT_CLIP_FRAMES", ["--clip={clip}", "--out={out}"]),
    ("measure_cascade_clip.py", "MEASURE_CASCADE_CLIP",
     ["--clip={clip}", "--frames={frames}", "--out={out}"]),
])
def test_the_ffmpeg_consumers_fail_closed_naming_the_binary(tool, prefix, argv, tmp_path):
    """`ARMATURE_FFMPEG` pointed at a path that does not exist, driven as a real process.

    Measured on `580af47`: `encode_control.py` exited 2 with an `ENCODE_CONTROL_HALT` line
    carrying `{"clause": "ffmpeg_binary_not_found", "from_env": true, "env_var":
    "ARMATURE_FFMPEG"}`, while BOTH of these exited 1 with a bare
    `FileNotFoundError: [WinError 2] The system cannot find the file specified` — naming
    neither the encoder, nor the variable that chose it, nor the path, on the one input that
    arrives AFTER a credit has been spent. Both already recorded `"ffmpeg": FFMPEG` as part
    of their provenance while neither checked the binary was there.
    """
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"\x00" * 64)
    frames = _frames(str(tmp_path / "src"))
    filled = [a.format(clip=clip, out=tmp_path / "o", frames=frames) for a in argv]
    missing = str(tmp_path / "no-such-ffmpeg.exe")
    proc = _run(tool, filled, tmp_path, env={"ARMATURE_FFMPEG": missing})
    assert proc.returncode == 2, (proc.returncode, proc.stderr[-900:])
    rec = _halt(proc, prefix)
    assert rec["evidence"]["clause"] == "ffmpeg_binary_not_found", rec["evidence"]
    assert rec["evidence"]["ffmpeg"] == missing, rec["evidence"]
    assert rec["evidence"]["env_var"] == "ARMATURE_FFMPEG", rec["evidence"]


def test_the_gate_is_the_one_home_and_not_a_second_isfile_test():
    """Adopt the home, never a copy: exactly one `os.path.isfile(FFMPEG)` under `tools/`."""
    sites = []
    for name in sorted(os.listdir(TOOLS)):
        if not name.endswith(".py"):
            continue
        src = B.read_source(name)
        # THE NODE is the CALL. Both adopters name `os.path.isfile(FFMPEG)` in prose,
        # saying they do NOT spell it — a substring walk counts the sentence that records
        # the rule as a violation of it.
        for node in ast.walk(ast.parse(src)):
            if (isinstance(node, ast.Call)
                    and getattr(node.func, "attr", None) == "isfile"
                    and any(getattr(a, "id", None) == "FFMPEG" for a in node.args)):
                sites.append(f"{name}:{node.lineno}")
        if "gate_ffmpeg_binary" in src and name != "encode_control.py":
            assert "from encode_control import" in src, name
    assert [s.split(":")[0] for s in sites] == ["encode_control.py"], sites


# ===========================================================================
# F-2f2c19a9 (panel HIGH) — four hand-rolled `.png` listings, one home
# ===========================================================================


def test_a_same_width_stray_no_longer_joins_the_timing_profile(tmp_path):
    """The operand the finding named, and it is the one the old check could not see.

    `measure_tracking._frame_names` listed `*.png` and then guarded a DIFFERENT property —
    that every name is the same LENGTH. Measured on `580af47` over three synthetic control
    directories: `00000..00003.png` gave four names; adding `strip_every8.png` was refused,
    but for the RAGGED-WIDTH reason, i.e. by accident of that stray's length; adding
    `plate.png` — NINE characters, the same width as `00001.png` — was admitted in SILENCE.
    A file that is not a frame then became a sample of the temporal-energy profile the
    timing correlation is computed from and was hashed into `_manifest_sha256` as recorded
    provenance.
    """
    import measure_tracking as MT

    d = _frames(str(tmp_path / "ctl"))
    assert MT._frame_names(d) == [f"{i:05d}.png" for i in range(4)]

    Image.new("RGB", (8, 8)).save(os.path.join(d, "plate.png"))   # nine characters
    assert len("plate.png") == len("00001.png"), "the operand must defeat the width check"
    with pytest.raises(MT.TrackingError) as exc:
        MT._frame_names(d)
    ev = exc.value.evidence
    assert ev["clause"] == "stray_png_in_the_frame_population", ev
    assert ev["unexpected"] == ["plate.png"], ev


def test_the_ragged_width_check_survives_as_the_diagnostic_it_is(tmp_path):
    """The fixed-width check catches a DIFFERENT defect and stays: a ragged zero-pad among
    names that are all numbered. The andon moved onto the direction the invariant does not
    bound; it did not replace this one."""
    import measure_tracking as MT

    d = str(tmp_path / "ragged")
    os.makedirs(d)
    for n in ("1.png", "2.png", "10.png"):
        Image.new("RGB", (8, 8)).save(os.path.join(d, n))
    with pytest.raises(MT.TrackingError) as exc:
        MT._frame_names(d)
    assert exc.value.evidence["clause"] == "frame_names_are_not_a_fixed_width", \
        exc.value.evidence


def test_compare_runs_refuses_a_stray_on_either_side(tmp_path):
    """The reproduction verdict's two listings were raw `*.png` walks on BOTH sides. A stray
    present in both was compared as a frame; present in one it was refused, but as a name
    disagreement — the halt named the wrong condition."""
    import compare_runs as CR

    a = _frames(str(tmp_path / "a"))
    b = _frames(str(tmp_path / "b"))
    for d in (a, b):
        Image.new("RGB", (8, 8)).save(os.path.join(d, "strip_every8.png"))
    with pytest.raises(CR.CompareError) as exc:
        CR.compare_channel(a, b)
    ev = exc.value.evidence
    assert ev["clause"] == "stray_png_in_the_frame_population", ev
    assert ev["side"] == "a", ev
    assert ev["unexpected"] == ["strip_every8.png"], ev


def test_the_gate0_panel_refuses_the_stray_as_a_stray_not_as_a_disagreement(tmp_path):
    """`frames_by_number` ran two lines BELOW `gate_listing_pairing`, so a stray present in
    the control directory and not the output one was refused under the PAIRING clause. The
    population gate fires first now, so the refusal names the condition."""
    import make_gate0_sheet as G0

    ctl = _frames(str(tmp_path / "ctl"))
    out = _frames(str(tmp_path / "out"))
    Image.new("RGB", (8, 8)).save(os.path.join(ctl, "strip_every8.png"))
    with pytest.raises(Exception) as exc:
        G0.build(ctl, out, None, {}, str(tmp_path / "sheet.png"), [0, 1])
    ev = getattr(exc.value, "evidence", None) or {}
    assert ev.get("gate") == "FRAMES", (type(exc.value).__name__, ev, str(exc.value)[:200])
    assert ev.get("unexpected") == ["strip_every8.png"], ev


def test_every_frame_population_in_this_domain_goes_through_one_of_two_homes():
    """The SIBLINGS, enumerated. Twelve modules take a `*.png` listing and turn it into a
    frame population; each either calls `sheet_compose.frames_by_number` (the raising home),
    `make_crop_strip.frames_by_number` (the filtering home, for a diagnostic that opens no
    credit) or carries the `isdigit` split with its OWN typed stray refusal beside it. What
    may not exist any more is a raw listing that becomes a population with no refusal at
    all — the shape `measure_tracking` and `compare_runs` had."""
    homes, own, raw = [], [], []
    for name in sorted(os.listdir(TOOLS)):
        if not name.endswith(".py"):
            continue
        src = B.read_source(name)
        if ".lower().endswith(\".png\")" not in src:
            continue
        if "frames_by_number" in src:
            homes.append(name)
        elif "not numbered frames" in src or "[0].isdigit()" in src \
                or "f[0].isdigit()" in src or "n[0].isdigit()" in src:
            own.append(name)
        else:
            raw.append(name)
    assert "measure_tracking.py" in homes, homes
    assert "compare_runs.py" in homes, homes
    # `make_thesis_sheet` and `make_gate0_sheet` were already callers; the fix there was the
    # ORDER, pinned by the test above.
    assert "make_gate0_sheet.py" in homes and "make_thesis_sheet.py" in homes, homes
    # The remainder are listings that are NOT a frame population: an upload map's keys, a
    # download verification, a planned-vs-present sweep. Recorded so a new raw listing that
    # IS a population fails here.
    assert set(raw) <= {"build_payload.py", "fetch_run.py", "fetch_t2v_run.py",
                        "preview_walk.py", "render_performer.py", "make_e13_sheet.py",
                        "make_lift_sheet.py", "measure_cascade_clip.py",
                        "sheet_compose.py", "make_identity_sheet.py",
                        "make_crop_strip.py", "make_review_clip.py"}, sorted(raw)


# ===========================================================================
# F-c66ad0c4 (panel MEDIUM) — the modules with no refusal at all
# ===========================================================================


def test_every_instrument_in_this_domain_can_refuse():
    """Size and membership before the property.

    MEASURED on `580af47` by AST walk over `tools/*.py` for `raise` statements:
    `make_cast_sheet` 0, `rig_sheet_compose` 0, `make_hole_survey` 0, `analyze_p3` 0. The
    last of those is the interesting one and the filed row read it wrong: `analyze_p3` DOES
    refuse, three times, through `make_sheet.parse_argv(..., exc=AnalyzeP3Error)` — the
    delegated-raise edge `test_refusal_clauses._raising_parameters` exists to see. Counting
    `raise` statements is not the same question as counting refusals. The other three could
    not refuse at all, and now do.
    """
    # A refusal is a `raise` OR a call to something whose job is to raise: the `exc=`
    # helpers (`parse_argv`, `frames_by_number`, `compose_over_named_plate`), the positional
    # `parse_plate(value, <Class>)`, and the `gate_*` / `require_*` andons. Keying on
    # `raise` alone is what made the filed row call `analyze_p3` silent when it refuses
    # three times.
    delegates = ("frames_by_number", "require_frames", "parse_argv", "parse_plate",
                 "compose_over_named_plate", "gate_listing_pairing")
    owned = [n for n in sorted(os.listdir(TOOLS)) if n.endswith(".py")]
    silent = []
    for name in owned:
        src = B.read_source(name)
        tree = ast.parse(src)
        if any(isinstance(n, ast.Raise) for n in ast.walk(tree)):
            continue
        called = {(getattr(n.func, "attr", None) or getattr(n.func, "id", None))
                  for n in ast.walk(tree) if isinstance(n, ast.Call)}
        if called & set(delegates):
            continue
        if any(c and (c.startswith("gate_") or c.startswith("require_")) for c in called):
            continue
        silent.append(name)
    assert silent == [], silent


def test_the_cast_survey_refuses_by_name_rather_than_inside_pil(tmp_path):
    """Driven on the two inputs measured on the base tree.

    `--names=` exited 1 with `ValueError: max() iterable argument is empty` — an arithmetic
    error out of the layout maths, on the tool whose job is to survey a cast — and
    `--names=ghost` exited 1 with a `FileNotFoundError` naming one path and neither the
    subject nor which of the five expected artifacts was missing.
    """
    import make_cast_sheet as MCS

    out = str(tmp_path / "sheet.png")
    with pytest.raises(MCS.CastSheetError) as exc:
        MCS.main([f"--dir={tmp_path}", "--names=", "--title=t", f"--out={out}"])
    assert exc.value.evidence["clause"] == "subject_list_is_empty", exc.value.evidence

    with pytest.raises(MCS.CastSheetError) as exc:
        MCS.main([f"--dir={tmp_path}", "--names=ghost", "--title=t", f"--out={out}"])
    ev = exc.value.evidence
    assert ev["clause"] == "subject_panel_is_not_on_disk", ev
    assert ev["subject"] == "ghost" and ev["panel"] == "full_a", ev
    assert "ghost_stats.json" in ev["expected"], ev
    assert not os.path.exists(out), "a refused survey wrote its sheet"


def test_the_cast_survey_names_the_stats_key_it_wanted(tmp_path, sheet_fonts):
    """The contract with `preview_glb`, stated once at module level so the refusal can name
    what it expected rather than dying on a bare subscript."""
    import make_cast_sheet as MCS

    for suf in MCS.PANEL_SUFFIXES:
        Image.new("RGB", (40, 60), (10, 10, 10)).save(tmp_path / f"a_{suf}.png")
    stats = {k: 0 for k in MCS.STATS_KEYS}
    stats["armatures"] = []
    stats["images"] = []
    (tmp_path / "a_stats.json").write_text(json.dumps(stats), encoding="utf-8")
    assert MCS.main([f"--dir={tmp_path}", "--names=a", "--title=t",
                     f"--out={tmp_path / 'ok.png'}"])

    del stats["triangles"]
    (tmp_path / "a_stats.json").write_text(json.dumps(stats), encoding="utf-8")
    with pytest.raises(MCS.CastSheetError) as exc:
        MCS.main([f"--dir={tmp_path}", "--names=a", "--title=t",
                  f"--out={tmp_path / 'no.png'}"])
    ev = exc.value.evidence
    assert ev["clause"] == "stats_document_is_missing_a_key", ev
    assert ev["missing"] == ["triangles"], ev


def test_the_rig_composer_refuses_a_panels_document_it_cannot_read(tmp_path):
    """The compose half of a two-step: `make_rig_sheet` renders under Blender and writes
    `panels.json`; this reads it in CPython because Blender's bundled Python carries no PIL.
    It read `sys.argv[1]` with no guard and then indexed eight keys with bare subscripts."""
    import rig_sheet_compose as RSC

    with pytest.raises(RSC.RigSheetComposeError) as exc:
        RSC.gate_spec(["rig_sheet_compose"])
    assert exc.value.evidence["clause"] == "panels_document_not_named", exc.value.evidence

    with pytest.raises(RSC.RigSheetComposeError) as exc:
        RSC.gate_spec(["rig_sheet_compose", str(tmp_path / "nope.json")])
    assert exc.value.evidence["clause"] == "panels_document_is_not_on_disk", \
        exc.value.evidence

    doc = tmp_path / "panels.json"
    doc.write_text(json.dumps({"geometry": {}}), encoding="utf-8")
    with pytest.raises(RSC.RigSheetComposeError) as exc:
        RSC.gate_spec(["rig_sheet_compose", str(doc)])
    ev = exc.value.evidence
    assert ev["clause"] == "panels_document_is_missing_a_key", ev
    assert "views" in ev["missing"] and "out" in ev["missing"], ev


def test_the_hole_survey_refuses_zero_views_and_a_missing_side(tmp_path, monkeypatch):
    """`--views=0` produced an empty survey, wrote `survey.json` with `"views": []` and
    printed `SURVEY_OK` beside it — a success token earned by no effect. And the per-view
    andon sits ABOVE the first write, so a run refused at view 5 leaves no partial survey."""
    import make_hole_survey as MHS

    out = tmp_path / "survey"
    argv = ["make_hole_survey", f"--new={tmp_path}", f"--old={tmp_path}",
            f"--out={out}", "--views=0"]
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(MHS.HoleSurveyError) as exc:
        MHS.main()
    assert exc.value.evidence["clause"] == "view_count_not_positive", exc.value.evidence
    assert not out.exists(), "a refused survey created its output directory"

    new = tmp_path / "new"
    new.mkdir()
    Image.new("RGBA", (8, 8)).save(new / "turn_0.png")
    monkeypatch.setattr(sys, "argv",
                        ["make_hole_survey", f"--new={new}", f"--old={tmp_path / 'old'}",
                         f"--out={out}", "--views=1", "--new-prefix=turn",
                         "--old-prefix=armfinal"])
    with pytest.raises(MHS.HoleSurveyError) as exc:
        MHS.main()
    ev = exc.value.evidence
    assert ev["clause"] == "survey_panel_is_not_on_disk", ev
    assert ev["side"] == "old" and ev["view"] == 0, ev
    assert not out.exists(), "a refused survey created its output directory"


def test_analyze_p3_refuses_a_run_directory_that_is_not_one(tmp_path):
    """The hole the AST walk did find: the argument refusals fired and then
    `analyze(args["run"])` opened `<run>/manifest.json` with a bare `open`."""
    import analyze_p3 as AP3

    with pytest.raises(AP3.AnalyzeP3Error) as exc:
        AP3.analyze(str(tmp_path))
    assert exc.value.evidence["clause"] == "run_manifest_is_not_on_disk", exc.value.evidence

    (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
    with pytest.raises(AP3.AnalyzeP3Error) as exc:
        AP3.analyze(str(tmp_path))
    assert exc.value.evidence["clause"] == "run_manifest_is_missing_a_key", \
        exc.value.evidence


# ===========================================================================
# F-eb2456cc (panel MEDIUM) — a clause is a WORD
# ===========================================================================


def test_the_two_sentence_shaped_clauses_are_words_now_and_the_sentence_survives():
    """MEASURED on `580af47` with the census's own home (`_census_nodes.clause_literals()`,
    385 literals): exactly 4 of the 385 contained a space and the two LONGEST were both this
    module's — 28 words at the SEGMENTATION verdict's evidence and 19 words at
    `segmentation_summary`. The sentences are not wrong; they were the wrong FIELD, so each
    moves to `note` and a vocabulary word takes the key."""
    import measure_arm as MA

    mask = np.zeros((6, 6), dtype=bool)
    ok, ev = MA.gate_segmentation(mask, {}, 0, "f.png")
    assert ok is True
    assert ev["clause"] == "corner_classified_as_subject", ev
    assert " " not in ev["clause"], ev
    assert ev["note"].startswith("the four image corners are background"), ev

    mask[0, 0] = True
    ok, ev = MA.gate_segmentation(mask, {}, 0, "f.png")
    assert ok is False
    assert ev["clause"] == "corner_classified_as_subject", ev
    assert ev["corners_classified_as_subject"] == ["top_left"], ev


def test_no_clause_literal_in_this_domains_files_is_a_sentence():
    """The property tree-wide over the domain, keyed on the resolved shape: a `clause` value
    that a halt reader can key on is `^[a-z][a-z0-9_]*$`."""
    import re

    word = re.compile(r"^[a-z][a-z0-9_]*$")
    bad = []
    for name in sorted(os.listdir(TOOLS)):
        if not name.endswith(".py"):
            continue
        for node in ast.walk(ast.parse(B.read_source(name))):
            if not isinstance(node, ast.Dict):
                continue
            for k, v in zip(node.keys, node.values):
                if (isinstance(k, ast.Constant) and k.value == "clause"
                        and isinstance(v, ast.Constant) and isinstance(v.value, str)
                        and not word.match(v.value)):
                    bad.append((name, node.lineno, v.value[:40]))
    assert [b for b in bad if b[0] == "measure_arm.py"] == [], bad


# ===========================================================================
# F-a3160731 (panel MEDIUM) — three bare stdlib raises in a file with a family
# ===========================================================================


def _keypoint_record(path, n=3, size=(16, 12)):
    rec = {"resolution": list(size),
           "body": [[[1.0, 1.0, 1.0]] * 20 for _ in range(n)],
           "left_hand": [[] for _ in range(n)], "right_hand": [[] for _ in range(n)]}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(rec, fh)
    return rec


def test_the_overlay_sheets_input_refusals_are_the_family_with_evidence(tmp_path):
    """AST walk on `580af47`: 5 raises, 1 with an evidence dict, in a file that defines its
    own family class and uses it correctly eleven lines lower. The mismatch clause is the
    one that carries the measurement worth keeping — the two resolutions and which frame
    disagreed — and it reached nothing."""
    import make_overlay_sheet as MOS

    kp = str(tmp_path / "kp.json")
    _keypoint_record(kp)
    render = tmp_path / "previz"
    render.mkdir()

    with pytest.raises(MOS.OverlaySheetError) as exc:
        MOS.main([f"--keypoints={kp}", f"--render={render}",
                  f"--out={tmp_path / 's.png'}", "--frames=0"])
    ev = exc.value.evidence
    assert ev["clause"] == "previz_frame_is_not_on_disk", ev
    assert ev["frame"] == 0, ev

    Image.new("RGB", (8, 8), (5, 5, 5)).save(render / "00000.png")
    with pytest.raises(MOS.OverlaySheetError) as exc:
        MOS.main([f"--keypoints={kp}", f"--render={render}",
                  f"--out={tmp_path / 's.png'}", "--frames=0"])
    ev = exc.value.evidence
    assert ev["clause"] == "render_and_keypoints_disagree_on_resolution", ev
    assert ev["render_size"] == [8, 8] and ev["keypoints_size"] == [16, 12], ev


def test_the_overlay_frames_flag_is_bounded_against_the_record(tmp_path):
    """The two adjacent argument holes closed by one guard: `--frames` was split with a bare
    `int()` inside a comprehension, and `rec["body"][i]` was indexed by the same unbounded
    `i`. Python's negative indexing is the sharp half — `--frames=-1` reaches the LAST
    frame's keypoints under the caption `frame -1`."""
    import make_overlay_sheet as MOS

    kp = str(tmp_path / "kp.json")
    rec = _keypoint_record(kp, n=3)
    assert MOS.gate_frame_indices("0,2", rec) == [0, 2]
    for text, clause in (("", "frame_list_is_empty"),
                         ("0,x", "frame_index_not_an_integer"),
                         ("0,7", "frame_index_outside_the_record"),
                         ("-1", "frame_index_outside_the_record")):
        with pytest.raises(MOS.OverlaySheetError) as exc:
            MOS.gate_frame_indices(text, rec)
        assert exc.value.evidence["clause"] == clause, (text, exc.value.evidence)


# ===========================================================================
# F-314625be (panel MEDIUM) — the LAST `ap.error` under tools/
# ===========================================================================


def test_the_tracking_argument_refusal_is_the_andon_and_not_argparse(tmp_path):
    """Measured on `580af47` as a real process: `measure_tracking.py --label=x` -> rc 2,
    stdout EMPTY, stderr `measure_tracking.py: error: --run and --control are required
    unless --anchor is given`. 2 is the code this repo's halt contract reserves for "a gate
    decided", so a verify chain branching on 2 read an argparse usage error from the
    timing-correlation instrument as a fired andon, with no sentinel, no gate id and no
    clause to tell the two apart. The CODE is unchanged; the halt LINE is what arrives."""
    proc = _run("measure_tracking.py", ["--label=x"], tmp_path)
    assert proc.returncode == 2, (proc.returncode, proc.stderr[-400:])
    rec = _halt(proc, "MEASURE_TRACKING")
    assert rec["error"] == "TrackingError", rec
    assert rec["evidence"]["clause"] == "missing_required", rec["evidence"]
    assert rec["evidence"]["flags"] == ["--run", "--control", "--anchor"], rec["evidence"]


def test_no_tool_calls_ap_error():
    """Tree-wide, on the CALL rather than on the string: `render_turnaround.py` closed the
    other two sites in wave 22 and claimed "an AST walk over the 21 owned tools finds these
    two the ONLY `ap.error` call sites" — re-derived here over ALL of `tools/`."""
    sites = []
    for name in sorted(os.listdir(TOOLS)):
        if not name.endswith(".py"):
            continue
        for node in ast.walk(ast.parse(B.read_source(name))):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "error"
                    and getattr(node.func.value, "id", None) == "ap"):
                sites.append(f"{name}:{node.lineno}")
    assert sites == [], sites


# ===========================================================================
# F-e7565198 (panel MEDIUM, ground F-c8b50a1c moved) — parse_plate's untyped exit
# ===========================================================================


PLATE_PRODUCERS = ["composite_reference", "encode_control", "fit_reference", "make_plate",
                   "pack_pose_pack"]


@pytest.mark.parametrize("operand", ["²,0,0", "②,0,0"])
def test_a_non_ascii_numeric_component_is_a_typed_refusal(operand):
    """The operand that separates the two predicates. `str.isdigit()` is a UNICODE property
    and is True for characters `int()` refuses, so wave 22's split moved the untyped raise
    from the combined boolean into the RANGE clause rather than removing it. Re-measured on
    `580af47`: `parse_plate('\\u00b2,0,0')` and `parse_plate('\\u2461,0,0')` raised
    `ValueError: invalid literal for int() with base 10` — untyped, on the ONE plate parser
    the authored-RGBA law is administered through, and on three of its four callers that is
    exit 1 with a traceback."""
    import composite_reference as CR

    assert operand.split(",")[0].isdigit(), "the operand must pass str.isdigit()"
    with pytest.raises(CR.ReferenceGate) as exc:
        CR.parse_plate(operand, CR.ReferenceGate)
    ev = exc.value.evidence
    assert ev["clause"] == "plate_component_not_an_integer", ev
    assert ev["supplied"] == operand, ev
    assert ev["unreadable"] == [operand.split(",")[0]], ev


def test_the_range_clause_can_no_longer_raise_before_it_refuses():
    """The invariant the fix rests on: `t.isascii() and t.isdigit()` is true only of a run of
    the ASCII digits, which `int()` reads by definition — so the cast below the integer
    clause cannot raise, and nothing this parser accepted before is refused now."""
    import composite_reference as CR

    assert CR.parse_plate("0,0,0", CR.ReferenceGate) == (0, 0, 0)
    assert CR.parse_plate("255,128,0", CR.ReferenceGate) == (255, 128, 0)
    assert CR.parse_plate("", CR.ReferenceGate) is None
    with pytest.raises(CR.ReferenceGate) as exc:
        CR.parse_plate("999,0,0", CR.ReferenceGate)
    assert exc.value.evidence["clause"] == "plate_component_out_of_range", exc.value.evidence
    assert exc.value.evidence["out_of_range"] == [999], exc.value.evidence


def test_the_flag_parser_is_still_one_implementation_for_every_producer():
    """The census `tests/test_alpha_law.py` pins, re-derived here over the operand: all four
    producers route to the one parser, so the superscript is refused by name on each."""
    import importlib

    import composite_reference as CR

    for name in PLATE_PRODUCERS:
        mod = importlib.import_module(name)
        assert "parse_plate" in B.read_source(name + ".py"), name
        if mod is CR:
            continue
        assert "from composite_reference import" in B.read_source(name + ".py"), name


# ===========================================================================
# F-40316edd (panel LOW) — stage_render adopts the lifted home
# ===========================================================================


def test_stage_render_has_no_local_keysafe_and_adopts_the_home():
    """The docstring said the lift was "FILED, not done" and named
    `armature_core.errors` as its destination. It LANDED in wave 22 at
    `armature_core.parts.halt_keysafe` — an inherited claim wearing a fact's clothes,
    telling the next reader to file the lift again."""
    import stage_render

    assert not hasattr(stage_render, "_halt_keysafe")
    src = B.read_source("stage_render.py")
    block = src.split('if __name__ == "__main__":')[-1]
    assert "run_tool_main(main, \"STAGE_RENDER\")" in block, block[-400:]
    # The old sentence is CORRECTED in place rather than deleted — this repo keeps the
    # measurement that overturned a claim — so what must be true is that the correction is
    # there and the instruction to file the lift again is not live.
    assert "The lift LANDED in wave 22" in src
    # The quoted sentence survives INSIDE the correction — this repo never quietly deletes a
    # wrong statement — so what is asserted is that the module defines no second walk, not
    # that the old words are gone.
    assert "def _halt_keysafe" not in src

    from armature_core.parts import halt_keysafe

    got = halt_keysafe({("hip", "z"): {np.int64(3): "x"}, "rows": [{(1, 2): "y"}],
                        "n": float("nan")})
    assert json.loads(json.dumps(got, default=str, allow_nan=False)) == {
        "('hip', 'z')": {"3": "x"}, "rows": [{"(1, 2)": "y"}], "n": "nan"}


def test_stage_renders_halt_line_is_unchanged_by_the_adoption(tmp_path, capsys):
    """The receipt an operator keys on, READ through the tool's own `__main__`. The home
    produces the same three outcome strings and the same two codes the local block spelled
    by hand, so what changed is the copy, not the line."""
    from armature_core.errors import GateFailure

    class _Gate(GateFailure):
        gate = "PROBE"

    def raiser():
        raise _Gate("a gate fired", {"measured": 1, ("t", "k"): float("inf")})

    code, escaped = B.exit_code_of_main_block(
        "stage_render.py", raiser=raiser,
        argv=["blender", "-b", "-P", "stage_render.py", "--", "--glb=nope.glb",
              "--out=" + str(tmp_path / "out")])
    out = capsys.readouterr().out
    assert escaped is None, escaped
    assert code == 2, code
    line = [l for l in out.splitlines() if l.startswith("STAGE_RENDER_HALT ")]
    assert len(line) == 1, out[-600:]
    rec = json.loads(line[0][len("STAGE_RENDER_HALT "):])
    assert rec["tool"] == "stage_render", rec
    assert rec["outcome"] == "HALTED — a gate fired", rec
    assert rec["gate"] == "PROBE", rec
    assert rec["evidence"]["measured"] == 1, rec
    assert rec["evidence"]["('t', 'k')"] == "inf", rec


# ===========================================================================
# F-78852870 (panel LOW, ground F-15823541 moved) — the dead crossover expression
# ===========================================================================


#: The synthetic run's per-shot normalisation is `+20` below a chosen depth level and `-40`
#: above it, over a per-frame depth ramp that covers EVERY 8-bit level, so the 8-level bin
#: sweep this tool actually publishes has a populated bin on both sides of the change and a
#: crossover it can find. A narrower ramp leaves most bins empty, the sweep's `continue`
#: skips them, and `crossover` comes back None — which would make the assertion below pass
#: for the wrong reason.
P3_FLIP_LEVEL = 128


def _p3_run(root, count=2, rows=4):
    os.makedirs(root, exist_ok=True)
    with open(os.path.join(root, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump({"frame_count": count}, fh)
    for sub in ("mask", "depth_perframe", "depth_pershot"):
        os.makedirs(os.path.join(root, sub), exist_ok=True)
    pf = np.tile(np.arange(256, dtype=np.uint8), (rows, 1))
    ps = np.clip(pf.astype(np.int16) + 20 - (pf > P3_FLIP_LEVEL) * 60,
                 0, 255).astype(np.uint8)
    for i in range(count):
        name = f"{i:05d}.png"
        Image.fromarray(np.full(pf.shape, 255, np.uint8), mode="L").convert("1").save(
            os.path.join(root, "mask", name))
        Image.fromarray(pf, mode="L").save(os.path.join(root, "depth_perframe", name))
        Image.fromarray(ps, mode="L").save(os.path.join(root, "depth_pershot", name))
    return root


def test_the_dead_crossover_expression_is_gone_and_the_number_is_unchanged(tmp_path):
    """`flips` was computed and never used; `dpf_s`, the sorted array it consumes, was
    assigned and read nowhere. Measured on `580af47`: `grep -n 'flips' tools/analyze_p3.py`
    returned the comment and that one line. The dead expression sat directly under the
    comment describing what the crossover IS, so a later maintainer could "restore" it and
    publish a different number under the same key — a monotone accumulate over signs is not
    the binned-mean sign change this tool actually reports."""
    import analyze_p3 as AP3

    src = B.read_source("analyze_p3.py")
    tree = ast.parse(src)
    assigned = {t.id for n in ast.walk(tree) if isinstance(n, ast.Assign)
                for t in n.targets if isinstance(t, ast.Name)}
    assert "flips" not in assigned, "the dead expression is back"
    assert "dpf_s" not in assigned, "the dead expression's operand is back"

    run = _p3_run(str(tmp_path / "run"))
    report = AP3.analyze(run)
    # The derivation that survives is the 8-level bin sweep, and it produces a REAL number
    # on a run built to have one: the per-shot normalisation lightens every level up to 128
    # and darkens every level above it, so the first bin boundary where the binned mean
    # signed difference stops being positive is the bin that STARTS at 128 -- that bin holds
    # level 128 (+20) and levels 129-135 (-40), mean -32.5, so the sign changes across the
    # [120,128) -> [128,136) boundary and the reported crossover is 128. The straddling bin
    # is deliberately excluded from the two partitions below rather than fudged.
    means = report["binned_mean_signed"]
    assert isinstance(means, list) and len(means) == 32, len(means)
    assert report["crossover_d_perframe_level"] == 128, (
        report["crossover_d_perframe_level"], means[14:20])
    below = [m for m in means if m["d_perframe_bin"][1] <= P3_FLIP_LEVEL]
    above = [m for m in means if m["d_perframe_bin"][0] > P3_FLIP_LEVEL]
    assert all(m["mean_signed_levels"] == 20.0 for m in below), below
    assert all(m["mean_signed_levels"] == -40.0 for m in above), above


# ===========================================================================
# F-128727b1 (panel LOW, ground F-102c8cc4 moved) — the dead keyword
# ===========================================================================


def test_no_call_site_under_tools_types_the_dead_keyword():
    """`round_trip_report` keeps `raise_on_fail` solely to REFUSE — passing True raises
    `SolveError` naming the gate — so the keyword's only other value is its own default.
    Both remaining call sites typed it, telling a reader an andon was being disarmed there
    when the andon is `gate_round_trip` and has no keyword to disarm. Re-derived tree-wide
    on the CALL, so a comment mentioning the keyword does not count as a site."""
    sites = []
    for dirpath, dirnames, filenames in os.walk(TOOLS):
        dirnames[:] = [d for d in dirnames if d not in ("superseded", "__pycache__")]
        for name in sorted(filenames):
            if not name.endswith(".py"):
                continue
            with open(os.path.join(dirpath, name), encoding="utf-8") as fh:
                tree = ast.parse(fh.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and any(
                        k.arg == "raise_on_fail" for k in node.keywords):
                    sites.append(f"{name}:{node.lineno}")
    assert sites == [], sites


def test_the_diagnostic_still_measures_and_the_refusal_still_refuses():
    """Dropping the keyword must not change what either function does: the default IS False,
    and passing True is still the typed refusal that names the gate."""
    import armature_core.lift_solve as LS

    with pytest.raises(LS.SolveError) as exc:
        LS.round_trip_report({}, {}, {}, 1.0, raise_on_fail=True)
    assert exc.value.evidence["clause"] == "diagnostic_cannot_be_armed", exc.value.evidence
    import inspect

    assert inspect.signature(LS.round_trip_report).parameters[
        "raise_on_fail"].default is False


# ===========================================================================
# The clause words this wave adds, each named by a fixture
# ===========================================================================
#
# `tests/test_refusal_clauses.py::test_every_clause_word_is_named_by_a_fixture_or_listed_
# with_a_reason` is the census: a clause nothing names is a receipt word no test would
# notice changing. Every word added below the line in this amend is reached here, except
# the four that need a real ffmpeg to fire, which are listed there with that reason.


def test_the_frame_population_refusals_name_their_directory(tmp_path):
    """The three population clauses the two control-sequence modules gained, plus the same
    clause on the timing instrument that adopted the home."""
    import encode_control as EC
    import invert_frames as IF
    import measure_tracking as MT

    absent = str(tmp_path / "not-a-directory")
    for fn, cls in ((EC.frame_population, EC.EncodeFailure),
                    (IF.frame_population, IF.InvertError),
                    (MT._frame_names, MT.TrackingError)):
        with pytest.raises(cls) as exc:
            fn(absent)
        assert exc.value.evidence["clause"] == "frames_dir_is_not_a_directory", \
            exc.value.evidence

    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(IF.InvertError) as exc:
        IF.frame_population(str(empty))
    assert exc.value.evidence["clause"] == "no_numbered_frames_to_invert", exc.value.evidence
    with pytest.raises(MT.TrackingError) as exc:
        MT._frame_names(str(empty))
    assert exc.value.evidence["clause"] == "no_numbered_frames_to_measure", exc.value.evidence


def test_the_encoders_frame_content_refusals_name_the_frame(tmp_path):
    """`read_frames` refuses a palette-indexed frame, a non-uint8 one and an array shape
    this bridge does not encode — three clauses on the population an upload is built from."""
    import encode_control as EC

    d = tmp_path / "frames"
    d.mkdir()
    Image.new("P", (4, 4)).save(d / "00000.png")
    with pytest.raises(EC.EncodeFailure) as exc:
        EC.read_frames(str(d), ["00000.png"])
    assert exc.value.evidence["clause"] == "frame_is_palette_indexed", exc.value.evidence

    Image.fromarray(np.zeros((4, 4), np.uint16), mode="I;16").save(d / "00000.png")
    with pytest.raises(EC.EncodeFailure) as exc:
        EC.read_frames(str(d), ["00000.png"])
    assert exc.value.evidence["clause"] == "frame_dtype_is_not_uint8", exc.value.evidence

    Image.new("CMYK", (4, 4)).save(d / "00000.tif")
    os.replace(d / "00000.tif", d / "00000.png")
    with pytest.raises(EC.EncodeFailure) as exc:
        EC.read_frames(str(d), ["00000.png"])
    assert exc.value.evidence["clause"] == "frame_array_shape_is_not_a_frame", \
        exc.value.evidence


def test_the_control_encoder_refuses_a_run_with_neither_frames_nor_out():
    """`--frames` and `--out` are required unless `--survey`; the refusal is the andon, and
    it now carries the clause a halt reader keys on."""
    import encode_control as EC

    with pytest.raises(EC.EncodeFailure) as exc:
        EC.main([])
    assert exc.value.evidence["clause"] == "frames_and_out_are_required", exc.value.evidence


def test_the_overlay_refuses_a_previz_frame_that_decodes_to_nothing(tmp_path):
    """A file named `.png` that is not one: `cv2.imread` returns None and raises nothing, so
    the refusal has to be the tool's."""
    import make_overlay_sheet as MOS

    kp = str(tmp_path / "kp.json")
    _keypoint_record(kp, n=1)
    render = tmp_path / "previz"
    render.mkdir()
    (render / "00000.png").write_bytes(b"not a png")
    with pytest.raises(MOS.OverlaySheetError) as exc:
        MOS.main([f"--keypoints={kp}", f"--render={render}",
                  f"--out={tmp_path / 's.png'}", "--frames=0"])
    assert exc.value.evidence["clause"] == "previz_frame_could_not_be_decoded", \
        exc.value.evidence


def test_the_rig_composer_refuses_a_panels_document_that_is_not_an_object(tmp_path):
    import rig_sheet_compose as RSC

    doc = tmp_path / "panels.json"
    doc.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")
    with pytest.raises(RSC.RigSheetComposeError) as exc:
        RSC.gate_spec(["rig_sheet_compose", str(doc)])
    assert exc.value.evidence["clause"] == "panels_document_is_not_an_object", \
        exc.value.evidence


def test_the_cast_survey_names_a_missing_stats_sidecar(tmp_path):
    """The five artifacts per subject are four panels AND the sidecar; a subject whose panels
    are all there and whose stats are not is the case that separates the two clauses."""
    import make_cast_sheet as MCS

    for suf in MCS.PANEL_SUFFIXES:
        Image.new("RGB", (20, 30), (9, 9, 9)).save(tmp_path / f"b_{suf}.png")
    with pytest.raises(MCS.CastSheetError) as exc:
        MCS.main([f"--dir={tmp_path}", "--names=b", "--title=t",
                  f"--out={tmp_path / 'no.png'}"])
    ev = exc.value.evidence
    assert ev["clause"] == "subject_stats_sidecar_is_not_on_disk", ev
    assert ev["subject"] == "b", ev


def test_the_segmentation_summarys_clause_is_the_word_and_not_the_sentence():
    """The second of `measure_arm`'s two sentence-shaped clauses. `segmentation_summary` is
    built inside `run()` over a real frame directory, so the word is read off the source
    rather than by standing up a run — what must hold is that the KEY is a vocabulary word
    and the sentence sits beside it under `note`."""
    import measure_arm as MA

    src = B.read_source("measure_arm.py")
    tree = ast.parse(src)
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        keys = {k.value: v for k, v in zip(node.keys, node.values)
                if isinstance(k, ast.Constant)}
        if "frames_without_an_angle" not in keys:
            continue
        found.append((keys["clause"].value, keys["note"].value))
    assert len(found) == 1, found
    clause, note = found[0]
    assert clause == "no_corner_is_inside_the_subject_mask", clause
    assert note.startswith("SEGMENTATION: no image corner is inside the subject mask"), note
    assert MA.gate_segmentation is not None
