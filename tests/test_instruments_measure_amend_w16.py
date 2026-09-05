"""Wave 16, instruments-measure: the population around each operand, not the operand alone.

Every test here names the POPULATION its property must hold over and is proven red on a
member OUTSIDE the walk the previous wave's check used. The wave-14 evidence probe walked
three classes (`extract_clip_frames.ClipReadError`, `measure_tracking.TrackingError`,
`measure_tracking.AnchorMismatch`); the census below walks all thirty plain-refusal classes
this domain's 42 files define, and its red proof is a member none of those three names.
"""

import ast
import json
import os

import pytest
from PIL import Image

from conftest import TOOLS  # noqa: F401
from armature_core.errors import ArmatureError, GateFailure


# ---------------------------------------------------------------------------
# the domain's own population, derived — never typed
# ---------------------------------------------------------------------------

#: The 42 CPython instruments this domain owns, RECORDED from the run's frozen domain map
#: (wave-16 snapshot `b3a82d889dc918f6`). The split between `instruments-measure`,
#: `instruments` and `builders` is a fact about the RUN and not about the tree, so it is the
#: one thing here that is written down rather than derived — and it is checked against the
#: tree below, so a name that stops being a file, or starts importing bpy (which would move
#: it to `instruments`), fails loudly.
OWNED = (
    "analyze_p3", "armature_index", "compare_runs", "composite_reference", "encode_control",
    "extract_clip_frames", "fit_reference", "gate_b_frames", "invert_frames", "lift_clip",
    "make_ab_clip", "make_cast_sheet", "make_crop_strip", "make_e08_sheet", "make_e13_sheet",
    "make_gate0_sheet", "make_hole_survey", "make_identity_sheet", "make_lift_sheet",
    "make_overlay_sheet", "make_pick_sheet", "make_plate", "make_review_clip", "make_sheet",
    "make_shotset_sheet", "make_startframe_sheet", "make_thesis_sheet", "make_zoom_sheet",
    "measure_arm", "measure_cascade_clip", "measure_clip", "measure_floor", "measure_lift",
    "measure_smoothness", "measure_tracking", "pack_pose_pack", "project_pose_keypoints",
    "render_pose_sticks", "resample_motion", "rig_sheet_compose", "sheet_compose",
    "stage_render",
)


def _owned_modules():
    return list(OWNED)


def test_the_owned_population_is_forty_two_cpython_instruments_that_all_exist():
    """The denominator, before anything is counted against it."""
    assert len(OWNED) == 42 == len(set(OWNED))
    for name in OWNED:
        path = os.path.join(TOOLS, name + ".py")
        assert os.path.exists(path), path
        src = open(path, encoding="utf-8").read()
        assert "import bpy" not in src, (
            f"{name} imports bpy; it belongs to `instruments`, not to this domain")


def _family_classes(module_name):
    """`[(class name, has its own __init__)]` for every class this module defines whose
    bases name an `ArmatureError`-family class, read off the AST."""
    path = os.path.join(TOOLS, module_name + ".py")
    tree = ast.parse(open(path, encoding="utf-8").read())
    out = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
        if not bases:
            continue
        out.append((node.name, bases,
                    any(isinstance(x, ast.FunctionDef) and x.name == "__init__"
                        for x in node.body)))
    return out


def _plain_refusal_classes():
    """`{qualified name: class}` — every live class in this domain that is an
    `ArmatureError` and NOT a `GateFailure`. The `GateFailure` subtree is the contract's
    one exemption (`armature_core/errors.py`), because a gate's clauses index into `ev`.
    """
    live = {}
    for module_name in _owned_modules():
        try:
            mod = __import__(module_name)
        except Exception:                                            # noqa: BLE001
            continue
        for name, _bases, _own in _family_classes(module_name):
            cls = getattr(mod, name, None)
            if (isinstance(cls, type) and issubclass(cls, ArmatureError)
                    and not issubclass(cls, GateFailure)):
                live[f"{module_name}.{name}"] = cls
    return live


def test_the_plain_refusal_population_is_the_thirty_this_wave_names():
    """Size and membership BEFORE the property (wave-8 rule 2, wave-16 rule 1).

    THIRTY classes on the base tree `041027c`, measured by a constructor probe over the 42
    files, and all thirty normalised a bare refusal's receipt to `{}`. Twenty-eight declared
    their own `__init__`; two more (`measure_tracking.TrackingError`, `.AnchorMismatch`)
    inherited one from `_CarriesEvidence`, a base with ZERO raise sites. This wave deletes
    twenty-seven constructors and `_CarriesEvidence` itself (30 - 1 = 29) and adds two NEW
    named andons — `make_pick_sheet.PickSheetError` (F-9b7cc1de) and
    `make_e13_sheet.E13SheetError` (F-9297b54f) — each replacing a refusal that named the
    wrong fault or was no refusal at all. 29 + 2 = 31, written as arithmetic rather than
    replaced, so a class appearing or vanishing fails HERE on the day it lands.
    """
    live = _plain_refusal_classes()
    assert len(live) == 31, sorted(live)
    assert "make_pick_sheet.PickSheetError" in live
    assert "make_e13_sheet.E13SheetError" in live
    # the three the wave-14 probe walked ...
    for q in ("extract_clip_frames.ClipReadError", "measure_tracking.TrackingError",
              "measure_tracking.AnchorMismatch"):
        assert q in live, sorted(live)
    # ... and members outside it, which is where this census is proven
    for q in ("analyze_p3.AnalyzeP3Error", "sheet_compose.FontError",
              "stage_render._UnreadablePath", "make_ab_clip.ABClipError"):
        assert q in live, sorted(live)


@pytest.mark.parametrize("qualified", sorted(_plain_refusal_classes()))
def test_no_plain_refusal_class_in_this_domain_normalises_its_evidence(qualified):
    """RULE 5, the whole population. RED on the base tree for all thirty.

    The base stores what it is passed: `E("m").evidence is None`, `E("m", d).evidence is d`
    — IDENTITY, not equality. `errors.py:27-33` rules the null the honest record for a bare
    message, and thirty subclasses each overrode it back to `{}`, so the base's plain-refusal
    contract held nowhere in this domain and the wave-14 root fix was inert here.

    Red on `analyze_p3.AnalyzeP3Error` — a member no wave-14 check named.
    """
    cls = _plain_refusal_classes()[qualified]
    assert cls("a bare message").evidence is None, (
        f"{qualified} normalises a bare refusal's receipt to {cls('m').evidence!r}; the "
        f"honest halt record is `\"evidence\": null` beside `\"gate\": null`")
    sentinel = {"measured": 1}
    assert cls("a message", sentinel).evidence is sentinel, qualified


def test_no_class_in_this_domain_defines_a_normalising_constructor_at_all():
    """The AST half: inheritance already gives every subclass the two-argument shape, so a
    plain-refusal class outside the `GateFailure` subtree defines no `__init__`.

    Keyed on the SOURCE and not on the behaviour, because a constructor that happens to be
    correct today is the shape that drifts back tomorrow.
    """
    offenders = []
    for module_name in _owned_modules():
        for name, bases, own_init in _family_classes(module_name):
            if not own_init or name == "BlenderBackend":
                continue
            cls = getattr(__import__(module_name), name, None)
            if (isinstance(cls, type) and issubclass(cls, ArmatureError)
                    and not issubclass(cls, GateFailure)):
                offenders.append(f"{module_name}.{name}")
    assert offenders == [], {
        "defines its own __init__ outside the GateFailure subtree": offenders}


def test_the_zero_raise_site_base_is_gone():
    """`_CarriesEvidence` existed to give two classes a constructor the base already has,
    and was raised from nowhere: an AST walk for `raise _CarriesEvidence(` over `tools/*.py`
    returned 0 sites."""
    import measure_tracking as MT

    assert not hasattr(MT, "_CarriesEvidence")
    assert MT.TrackingError.__bases__ == (ArmatureError,)
    assert MT.AnchorMismatch.__bases__ == (ArmatureError,)


# ===========================================================================
# F-f98407d9 — the three `SpecError` refusals carry evidence NOW
# ===========================================================================


def test_the_stage_render_halt_line_carries_the_flag_of_a_mistyped_token(capsys, tmp_path):
    """THE OPERAND: the PRINTED `STAGE_RENDER_HALT` line for `--sepc=`, parsed back.

    Measured on the base tree: `stage_render.main(['--sepc=x','--out=y'])` raised
    `SpecError` with `evidence: None`, so the halt line printed `"evidence": null` for a
    mistyped flag on a spend-adjacent tool and a CI or PowerShell chain routing the failure
    had to regex the prose to learn which flag was rejected and what the known set was. The
    docstring beside the raises asserted a blocker — "until `ArmatureError` gains the
    `(message, evidence=None)` constructor" — that the wave-14 merge had already removed.

    The population is the parser's THREE refusals, not this one: `not_a_flag`,
    `unknown_flag` and `missing_required` are each driven below.
    """
    from blender_stub import exit_code_of_main_block

    out = str(tmp_path / "run")

    def raiser():
        import stage_render
        return stage_render.main(["--sepc=x", f"--out={out}"])

    code, escaped = exit_code_of_main_block(
        "stage_render.py", raiser=raiser,
        argv=["blender", "-b", "-P", "stage_render.py", "--", "--sepc=x", f"--out={out}"])
    assert escaped is None, escaped
    assert code == 2, code

    printed = capsys.readouterr().out
    lines = [l for l in printed.splitlines()
             if l.split(" ", 1)[0] == "STAGE_RENDER_HALT"]
    assert len(lines) == 1, printed
    rec = json.loads(lines[0][len("STAGE_RENDER_HALT"):].strip())

    assert rec["evidence"] is not None, rec
    ev = rec["evidence"]
    assert ev["clause"] == "unknown_flag", ev
    assert ev["andon"] == "SpecError" and ev["gate"] is None, ev
    assert ev["key"] == "sepc" and ev["token"] == "--sepc=x", ev
    assert "spec" in ev["known"] and "asset" in ev["known"], ev
    assert rec["outcome"].startswith("REFUSED"), rec
    assert not rec["message"].startswith("("), rec["message"]


@pytest.mark.parametrize("argv,clause,key,token", [
    (["not-a-flag", "--out=x"], "not_a_flag", None, "not-a-flag"),
    (["--sepc=x", "--out=y"], "unknown_flag", "sepc", "--sepc=x"),
    (["--out=y"], "missing_required", "spec", None),
])
def test_each_of_the_parsers_three_refusals_names_its_clause(argv, clause, key, token):
    """The POPULATION: all three sites of `_parse_argv`, not the one the finding drove.

    Red on `not_a_flag` and `missing_required` too — neither is the site the halt-line
    fixture above exercises, and both carried `evidence: None` on the base tree.
    """
    import stage_render
    from armature_core.errors import SpecError

    with pytest.raises(SpecError, match=r"stage_render takes") as exc:
        stage_render._parse_argv(argv)
    ev = exc.value.evidence
    assert ev is not None, "the refusal carries no receipt"
    assert ev["clause"] == clause, ev
    assert ev["andon"] == "SpecError" and ev["gate"] is None, ev
    assert ev["key"] == key and ev["token"] == token, ev
    assert set(ev["known"]) == set(stage_render.KNOWN_FLAGS), ev
    # the message keeps saying it too — a human reads the line as well
    assert "stage_render takes" in str(exc.value)


# ===========================================================================
# F-981fe49d — the OTHER divisor in the same block: `--fps-src`
# ===========================================================================


def _motion(n=4):
    """A motion record `lift_solve.validate_motion_record` accepts — every bone in
    `sitelist.ALL_NAMES` present at identity. Same shape as the wave-14 fixture."""
    from armature_core import sitelist

    frames = []
    for i in range(n):
        frames.append({"frame": i, "root": [0.0, 0.0, float(i)],
                       "local": {b: [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
                                 for b in sitelist.ALL_NAMES}})
    return {"tool": "test", "frames": frames}


@pytest.mark.parametrize("fps_src", ["0", "-16", "0.0", "-0.5"])
def test_a_source_rate_that_is_not_positive_is_refused_by_name(tmp_path, fps_src):
    """THE OPERAND, and the population: wave 14 gated `--frames` because `positions` and
    `sample_interval_ratio` divide by `n_dst - 1`, and left `--fps-src` — the OTHER divisor
    in the same `resample` block — ungated.

    Measured on the base tree, on a 4-frame record that passes every gate:
    `--fps-src=0` raised a bare `ZeroDivisionError` at `(n_src - 1) / a.fps_src`, untyped,
    so the `__main__` handler classified it exit 1 ("an unhandled error") rather than the
    exit 2 a deliberate refusal earns, and the message named neither the flag nor the value.
    `--fps-src=-16` ran to completion, printed `RESAMPLE_MOTION_OK` and WROTE the record
    with `fps_dst_true_tempo: -37.333`, `span_s_first_to_last_sample: -0.1875` and
    `clip_s_src_frames_over_fps: -0.25` — a library-ready motion record carrying a negative
    true-tempo rate under a green success line, on the one field whose stated purpose is to
    pick the generator's frame rate.

    Red on `-16` and on `-0.5`, which are OUTSIDE the zero the naive guard would catch.
    """
    import resample_motion as RM

    src = tmp_path / "m.json"
    src.write_text(json.dumps(_motion(4)), encoding="utf-8")
    out = tmp_path / ("resampled_" + fps_src.replace(".", "p").replace("-", "neg"))
    with pytest.raises(RM.ResampleArgError, match=r"--fps-src") as exc:
        RM.main([f"--motion={src}", "--frames=8", f"--out={out}", f"--fps-src={fps_src}"])
    ev = exc.value.evidence
    assert ev is not None, "the refusal carries no receipt"
    assert ev["clause"] == "source_rate_not_positive", ev
    assert ev["gate"] == "ARGS" and ev["andon"] == "ResampleArgError", ev
    assert ev["fps_src"] == float(fps_src), ev
    # and NOTHING was written: the andon sits in the same block as `--frames`, above the read
    assert not out.exists(), "a refused run left its output directory behind"


def test_a_non_finite_source_rate_is_refused_too(tmp_path):
    """`nan` and `inf` are the shapes a `> 0` comparison does not bound the same way:
    `float('nan') > 0` is False (so nan is caught by the same clause) but `inf > 0` is True
    and would pass a positivity test while making every derived duration zero."""
    import resample_motion as RM

    src = tmp_path / "m.json"
    src.write_text(json.dumps(_motion(4)), encoding="utf-8")
    for spelling in ("nan", "inf"):
        out = tmp_path / ("r_" + spelling)
        with pytest.raises(RM.ResampleArgError, match=r"--fps-src") as exc:
            RM.main([f"--motion={src}", "--frames=8", f"--out={out}",
                     f"--fps-src={spelling}"])
        assert exc.value.evidence["clause"] in (
            "source_rate_not_positive", "source_rate_not_finite"), exc.value.evidence
        assert not out.exists()


def test_a_positive_source_rate_still_resamples(tmp_path, capsys):
    """Grade the arm only on what it can move: the gate must not refuse a legal rate."""
    import resample_motion as RM

    src = tmp_path / "m.json"
    src.write_text(json.dumps(_motion(4)), encoding="utf-8")
    out = tmp_path / "ok"
    assert RM.main([f"--motion={src}", "--frames=8", f"--out={out}",
                    "--fps-src=20"]) == 0
    assert "RESAMPLE_MOTION_OK" in capsys.readouterr().out
    rec = json.loads((out / "m.8.motion.json").read_text(encoding="utf-8"))
    assert rec["resample"]["fps_src"] == 20.0
    assert rec["resample"]["fps_dst_true_tempo"] > 0
    assert rec["resample"]["span_s_first_to_last_sample"] > 0


# ===========================================================================
# F-b1949407 — the A/B time axis was built from LISTING POSITIONS
# ===========================================================================


def _arm(tmp, name, numbers, colour=(10, 20, 30)):
    """A frames directory whose files carry exactly `numbers` — the lever."""
    d = tmp / name
    d.mkdir(parents=True, exist_ok=True)
    for i in numbers:
        Image.new("RGB", (8, 8), colour).save(d / f"{i:05d}.png")
    return str(d)


def test_a_gap_in_an_arms_numbering_is_refused_before_the_timeline_is_built(tmp_path):
    """THE OPERAND: `00000, 00001, 00003, 00004` against a contiguous arm at 16 fps.

    Measured on the base tree: `event_timeline` takes `{k / fps for k in range(n)}` — the
    LISTING POSITIONS — while the banner burned into every frame was corrected in wave 14 to
    read the file's own NUMBER. On that input the composite placed `f00003` at t=0.1250 s
    and `f00004` at t=0.1875 s, the instants of frames 2 and 3, so every frame after the gap
    was shown one frame-time (62.5 ms) early for the rest of the clip while the banner
    correctly read `f00003`. The module docstring's central claim ("Every frame of both arms
    is shown, once, for exactly its own duration") and the manifest's own `composite.rule`
    ("NEITHER arm is resampled or retimed") were both false on that input.

    The Director then watches an A/B whose two arms are out of step by one frame-time and
    reads the desynchronisation as a difference between the arms — the exact corruption the
    tool exists to prevent.
    """
    import make_ab_clip as AB

    a = _arm(tmp_path, "a", [0, 1, 3, 4])
    b = _arm(tmp_path, "b", [0, 1, 2, 3])
    out = tmp_path / "ab.webp"
    with pytest.raises(AB.ABClipError, match=r"contiguous|gap") as exc:
        AB.main([f"--a={a}", "--a-fps=16", f"--b={b}", "--b-fps=16", f"--out={out}"])
    ev = exc.value.evidence
    assert ev is not None, "the refusal carries no receipt"
    assert ev["gate"] == "TIMELINE", ev
    assert ev["arm"] == "--a", ev
    assert ev["numbers"] == [0, 1, 3, 4], ev
    assert ev["first_gap"] == [1, 3], ev
    assert not out.exists(), "a refused run wrote a composite anyway"


def test_the_second_arm_is_walked_too(tmp_path):
    """The POPULATION is BOTH arms, not the first one the loop happens to reach.

    Red on an arm numbered 0/1/3/4 in the `--b` position with a contiguous `--a` — a member
    outside any check that only guards the arm it read first.
    """
    import make_ab_clip as AB

    a = _arm(tmp_path, "a2", [0, 1, 2, 3])
    b = _arm(tmp_path, "b2", [0, 1, 3, 4])
    out = tmp_path / "ab2.webp"
    with pytest.raises(AB.ABClipError, match=r"contiguous|gap") as exc:
        AB.main([f"--a={a}", "--a-fps=16", f"--b={b}", "--b-fps=16", f"--out={out}"])
    assert exc.value.evidence["arm"] == "--b", exc.value.evidence


def test_an_arm_that_is_merely_OFFSET_still_builds(tmp_path):
    """Grade the arm only on what it can move. An OFFSET is not the defect — wave 14
    measured real arms numbered `00005, 00006, 00007` and the banner fix is what that
    earned. A gate that refused an offset would fail on correct work."""
    import make_ab_clip as AB

    a = _arm(tmp_path, "a3", [5, 6, 7, 8])
    b = _arm(tmp_path, "b3", [0, 1, 2, 3])
    out = tmp_path / "ab3.webp"
    assert AB.main([f"--a={a}", "--a-fps=16", f"--b={b}", "--b-fps=16",
                    f"--out={out}"]) == 0
    assert out.exists()
    side = json.loads((tmp_path / "ab3_manifest.json").read_text(encoding="utf-8"))
    assert side["a"]["frame_numbers"] == [5, 6, 7, 8]
    assert side["composite"]["numbering"]["a"] == "contiguous from 5"


def test_a_single_frame_arm_is_contiguous_by_construction(tmp_path):
    """The degenerate end of the population: one frame has no gap, and the gate must not
    invent one."""
    import make_ab_clip as AB

    # Wave 22, F-070bfff3: the gate now TAKES the arm's rate, because the shift its
    # refusal quotes is a frame time (1000/fps) and not 1000/n_frames. The arity change is
    # this domain's own contract; these two fixture call sites move with it.
    assert AB.gate_contiguous_numbering([7], "--a", 16.0)["verdict"].startswith("4 frame") is False
    ev = AB.gate_contiguous_numbering([7], "--a", 16.0)
    assert ev["numbers"] == [7] and ev["first_gap"] is None


# ===========================================================================
# make_pick_sheet — the two Gate PLATE findings
# ===========================================================================


def _pick_clip(tmp_path, n=6):
    import numpy as np

    d = tmp_path / "lossless"
    d.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(3)
    for i in range(n):
        a = rng.integers(0, 256, size=(48, 64, 3), dtype="uint8")
        Image.fromarray(a, mode="RGB").save(d / f"{i:05d}.png")
    return str(d)


# ---- F-da27f9de: a RECORDED null is not a missing key ---------------------


@pytest.mark.parametrize("field,line", [
    ("seed", "source seed"),
    ("prompt_id", "source run"),
])
def test_a_null_field_in_the_payload_record_prints_not_recorded(tmp_path, field, line):
    """THE OPERAND is the printed LINE, not `source_run`'s dict — the line is the surface
    the Director reads.

    Measured on the base tree: `prompt_id` was normalised with `or MISSING` and `seed` with
    `rec.get('seed', MISSING)` — a DEFAULT, not a null check — so a payload record carrying
    `"seed": null` yielded `{'seed': None}` and `provenance_lines` emitted the literal line
    `source seed    None`. That contradicts this module's own rule ("A value the inputs do
    not carry prints `NOT RECORDED` rather than a plausible default") on the one artifact
    whose whole purpose is that its labels are derived and not typed: a reader
    reconstructing the pick later cannot tell an unrecorded seed from a recorded null.

    RULE 3 of this wave: the clause keys on the VALUE, never on the presence of the key.
    Red on `seed: null` — a member outside the walk `prompt_id`'s `or MISSING` covered.
    """
    import make_pick_sheet as MPS

    payload = {"prompt_id": "abc", "seed": 2026081231, "resolution": "720P", "length": 5}
    payload[field] = None
    rec_path = tmp_path / "payload.json"
    rec_path.write_text(json.dumps(payload), encoding="utf-8")

    run = MPS.source_run(str(rec_path))
    assert run[field] == MPS.MISSING, run
    rec = {"frames_dir": "d", "n_frames": 3, "source_size": [832, 480],
           "cover_fit": {"target_size": [1024, 576], "scale": 1.2,
                         "resized_size": [1024, 591], "crop_box": [0, 7, 1024, 583],
                         "dropped_px_resized": {"x": 0, "y": 15},
                         "kept_fraction_of_source_area": 0.97},
           "visible_rows_target": [0, 182], "visible_rows_source": [5.7, 153.6],
           "band_fraction_of_target": 0.316, "source_run": run}
    lines = MPS.provenance_lines(rec)
    assert any(l.startswith(line) and MPS.MISSING in l for l in lines), lines
    assert not any(l.startswith(line) and "None" in l for l in lines), lines


def test_no_python_none_reaches_any_provenance_line(tmp_path):
    """The POPULATION: all four fields `source_run` reads, not the two that are printed
    today. `resolution` and `length` carry the same `.get(k, MISSING)` shape and nothing
    prints them yet — which is exactly how a defect waits for a caller."""
    import make_pick_sheet as MPS

    rec_path = tmp_path / "null.json"
    rec_path.write_text(json.dumps(
        {"prompt_id": None, "seed": None, "resolution": None, "length": None}),
        encoding="utf-8")
    run = MPS.source_run(str(rec_path))
    assert set(run) == {"prompt_id", "seed", "resolution", "length", "record"}
    for key, value in run.items():
        assert value is not None, (key, run)
        if key != "record":
            assert value == MPS.MISSING, (key, run)


# ---- F-9b7cc1de: an empty `--at` named a fault that did not exist --------


@pytest.mark.parametrize("at", ["", ",,", "  ", ", ,"])
def test_an_empty_at_list_is_refused_as_a_candidate_set(tmp_path, at):
    """THE OPERAND: `--at=` on a directory whose frames ARE all one size.

    Measured on the base tree, on a 6-frame directory: `indices` is `[]`, `measure` walks
    nothing, `sizes` is `{}`, `distinct` is `[]`, and the SIZE andon fires because
    `len([]) != 1` — raising "the frames are not all one size ([]); one cover fit cannot
    describe all of them and the marked bands would be wrong on some tiles". The refusal is
    correct that it must not proceed (`main` would die at `cands[0]` on the next line) and
    names a fault that does not exist: the frames are all one size; the CANDIDATE SET is
    empty. An operator whose `--at` list was eaten by a shell then spends the next step
    inspecting frame dimensions, because that is what the tool told him was wrong.

    Red on `--at=,,` and `--at=, ,` too — spellings that reach `[]` through the
    `if v.strip()` filter rather than through an empty string.
    """
    import make_pick_sheet as MPS

    clip = _pick_clip(tmp_path)
    out = tmp_path / "sheet.png"
    with pytest.raises(MPS.PickSheetError, match=r"candidate") as exc:
        MPS.main([f"--frames={clip}", f"--at={at}", "--target=1024x576",
                  "--visible-rows=0,182", f"--out={out}"])
    ev = exc.value.evidence
    assert ev is not None, "the refusal carries no receipt"
    assert ev["clause"] == "no_candidate_frames", ev
    assert ev["at"] == at, ev
    assert ev["frames_present"] == 6, ev
    assert "one size" not in str(exc.value), str(exc.value)
    assert not out.exists()


def test_the_size_refusal_still_fires_on_a_genuinely_mixed_directory(tmp_path):
    """Grade the arm only on what it can move: the size andon must still name the size
    fault when the size fault is the one that exists."""
    import numpy as np
    import make_pick_sheet as MPS
    from armature_core.errors import ArmatureError as AE

    clip = _pick_clip(tmp_path, n=3)
    rng = np.random.default_rng(5)
    Image.fromarray(rng.integers(0, 256, size=(24, 32, 3), dtype="uint8"),
                    mode="RGB").save(os.path.join(clip, "00003.png"))
    out = tmp_path / "mixed.png"
    with pytest.raises(AE, match=r"not all one size"):
        MPS.main([f"--frames={clip}", "--at=2,3", "--target=1024x576",
                  "--visible-rows=0,182", f"--out={out}"])


def test_a_seed_of_zero_is_a_recorded_value_and_survives(tmp_path):
    """The direction the naive fix breaks. `or MISSING` reads as a null check and is a
    truthiness test: a seed of 0 and a length of 0 are values a payload record can carry,
    and `or` erases both into `NOT RECORDED` — a different lie in the same place."""
    import make_pick_sheet as MPS

    rec_path = tmp_path / "zero.json"
    rec_path.write_text(json.dumps({"prompt_id": "abc", "seed": 0, "length": 0}),
                        encoding="utf-8")
    run = MPS.source_run(str(rec_path))
    assert run["seed"] == 0, run
    assert run["length"] == 0, run
    assert run["seed"] != MPS.MISSING


# ===========================================================================
# F-9297b54f — the `--ref-frames` listing was indexed without being checked
# ===========================================================================


def _e13_inputs(tmp_path, n_out=5):
    """The two records `make_e13_sheet.main` reads before it reaches `--ref-frames`."""
    frames = tmp_path / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    for i in range(n_out):
        Image.new("RGB", (32, 18), (30, 30, 34)).save(frames / f"{i:05d}.png")
    (frames / "frames.json").write_text(json.dumps({
        "stream": {"width": 32, "height": 18, "fps": 16, "line": "Video: h264 32x18"},
        "n_frames": n_out, "distinct_frames": n_out, "clip_bytes": 1234,
        "clip_sha256": "c" * 64}), encoding="utf-8")
    payload = tmp_path / "payload.json"
    payload.write_text(json.dumps({
        "experiment": "E13", "arm": "A2", "tier": "wan2.7-t2v", "seed": 1,
        "payload": {}, "slot_order": [], "gates": {}}), encoding="utf-8")
    return str(frames), str(payload)


def test_an_empty_ref_frames_directory_is_refused_by_name_and_leaves_no_sheet(tmp_path):
    """THE OPERAND: `--ref-frames` at a directory holding no PNGs.

    Measured on the base tree: `paths = sorted(glob(...*.png))` then
    `picks = [0, len//3, 2*len//3, len-1]`, indexed with no emptiness check — so `paths[0]`
    raised a bare `IndexError` naming nothing, AFTER `os.makedirs` at the top of `main` had
    already created the sheet's directory. On the tool whose product is the
    `control | output | reference | provenance` panel a spend is judged from.
    """
    import make_e13_sheet as S

    frames, payload = _e13_inputs(tmp_path)
    refs = tmp_path / "refclip"
    refs.mkdir()
    (refs / "notes.txt").write_text("not a frame", encoding="utf-8")
    out = tmp_path / "sheets" / "e13.png"
    with pytest.raises(S.E13SheetError, match=r"--ref-frames") as exc:
        S.main(["--arm=A2", "--seed=1", f"--frames={frames}", f"--payload={payload}",
                f"--ref-frames={refs}", f"--out={out}"])
    ev = exc.value.evidence
    assert ev is not None, "the refusal carries no receipt"
    assert ev["clause"] == "reference_clip_has_no_frames", ev
    assert ev["ref_frames"] == os.path.abspath(str(refs)), ev
    assert ev["png_files"] == [], ev
    assert not out.exists()
    assert not out.parent.exists(), (
        "a refused run left its output directory behind; `os.makedirs` must sit below "
        "the last pre-write refusal")


@pytest.mark.parametrize("n_ref,expected", [(1, 1), (2, 2), (3, 3), (4, 4), (9, 4)])
def test_the_reference_band_shows_one_panel_per_distinct_sample(tmp_path, n_ref, expected):
    """The POPULATION is every short reference clip, not the empty one.

    Measured on the base tree: for `len(paths)` of 1, 2 and 3 the picks are `[0,0,0,0]`,
    `[0,0,1,1]` and `[0,1,2,2]`, so the REFERENCES band showed 4, 2 and 3 distinct panels
    under four headings — four slots that are not four samples. Red on 1, 2 and 3, each a
    member outside the emptiness check the finding's first half asks for.
    """
    import make_e13_sheet as S

    frames, payload = _e13_inputs(tmp_path)
    refs = tmp_path / f"refclip{n_ref}"
    refs.mkdir()
    for i in range(n_ref):
        Image.new("RGB", (16, 9), (i * 20 % 255, 40, 50)).save(refs / f"{i:05d}.png")
    out = tmp_path / "sheets" / f"e13_{n_ref}.png"
    assert S.main(["--arm=A2", "--seed=1", f"--frames={frames}", f"--payload={payload}",
                   f"--ref-frames={refs}", f"--out={out}", "--sample=0,1"]) == str(out)
    assert out.exists()
    picks = S.reference_picks(n_ref)
    assert len(picks) == expected, picks
    assert len(set(picks)) == len(picks), picks
    assert picks == sorted(picks) and picks[0] == 0 and picks[-1] == n_ref - 1, picks


# ===========================================================================
# F-c961d99a — a count with no denominator, on the diagnostic that caught the
#              superseded GLB-tail route
# ===========================================================================


def _body(n_frames, *, leg=10.0, foot=4.0):
    """`body_px` frames of 20 keypoints. `leg` is the hip(8)->ankle(10) pixel distance and
    `foot` the ankle(10)->toe(19) one; `leg=0` is the degenerate framing."""
    out = []
    for k in range(n_frames):
        f = [[float(j), float(k)] for j in range(20)]
        f[8] = [0.0, 0.0]
        f[10] = [0.0, float(leg)]
        f[19] = [0.0, float(leg) + float(foot)]
        out.append(f)
    return out


def test_the_ratio_diagnostic_reports_the_population_it_was_computed_over():
    """THE OPERAND: the loop `if leg > 0: ratios.append(foot / leg)` DROPPED frames
    silently, and the record then reported `min`, `median` and `max` with no count of how
    many frames contributed. This is the repo's count-without-a-denominator shape, on the
    one number whose stated job is to catch the superseded GLB-tail route.
    """
    import project_pose_keypoints as PPK

    good = _body(4, leg=10.0, foot=4.0)
    degenerate = _body(2, leg=0.0, foot=4.0)
    mixed = good + degenerate
    stats = PPK.ankle_to_toe_ratios(mixed)
    assert stats["n_frames"] == 6, stats
    assert stats["n_frames_contributing"] == 4, stats
    assert stats["n_frames_dropped_zero_leg"] == 2, stats
    assert stats["dropped_frame_indices"] == [4, 5], stats
    assert stats["median"] == pytest.approx(0.4), stats
    assert stats["min"] == pytest.approx(0.4) and stats["max"] == pytest.approx(0.4)


def test_a_degenerate_framing_refuses_by_name_rather_than_min_of_an_empty_sequence():
    """Measured statically on the base tree: if every frame projects hip and ankle to the
    same pixel, `ratios` is `[]` and `min([])` raises
    `ValueError: min() arg is an empty sequence` — untyped, after all four gates have passed
    and before `os.makedirs`, so the halt reports a crash rather than a refusal."""
    import project_pose_keypoints as PPK

    with pytest.raises(PPK.ProjectGate, match=r"leg") as exc:
        PPK.ankle_to_toe_ratios(_body(3, leg=0.0))
    ev = exc.value.evidence
    assert ev["clause"] == "no_frame_carries_a_measurable_leg", ev
    assert ev["n_frames"] == 3 and ev["n_frames_contributing"] == 0, ev
    assert ev["dropped_frame_indices"] == [0, 1, 2], ev


def test_span_stats_refuses_an_empty_population_rather_than_min_of_nothing():
    """The SAME empty-population shape one screen up, which the finding names: `span_stats`
    calls `min(per)` / `max(per)` over a per-frame list built by a loop.

    Red on a member outside the ratio walk entirely — this is the second site of the family,
    not the one the finding's headline named.
    """
    import project_pose_keypoints as PPK

    assert PPK.span_stats(_body(2))["min"] > 0
    with pytest.raises(PPK.ProjectGate, match=r"no frames|empty") as exc:
        PPK.span_stats([])
    assert exc.value.evidence["clause"] == "empty_keypoint_population", exc.value.evidence


def test_the_front_gates_point_count_is_derived_and_not_the_literal_sixty_two():
    """`gates.FRONT.detail` spelled the count as the literal `n_frames * 62` in a file whose
    stated rule is that nothing is a literal. Derived from what was actually projected:
    twenty body landmarks plus twenty-one points per mitten hand."""
    import project_pose_keypoints as PPK
    from armature_core import aapose

    body = _body(3)
    hands = [[[0.0, 0.0]] * 21 for _ in range(3)]
    detail = PPK.front_gate_detail(body, hands, hands)
    assert "62" not in detail or "186" in detail, detail
    assert str(3 * (len(aapose.LANDMARK_SITES) + 42)) in detail, detail
    assert "literal" not in detail
    # and it MOVES with the population, which a literal cannot
    other = PPK.front_gate_detail(_body(5), [[[0.0, 0.0]] * 21 for _ in range(5)],
                                  [[[0.0, 0.0]] * 21 for _ in range(5)])
    assert str(5 * 62) in other, other


# ===========================================================================
# make_review_clip — the rate bound above `makedirs`, and the run token
# ===========================================================================


def _review_frames(tmp, n=5, run="A2", sub="lossless"):
    """The canonical `<run>/lossless/` layout the review pass is pointed at."""
    d = tmp / run / sub
    d.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        Image.new("RGB", (16, 16), (10 + i, 20, 30)).save(d / f"{i:05d}.png")
    return str(d)


# ---- F-e924157e: `--fps` / `--source-fps` bounded ABOVE `makedirs` --------


@pytest.mark.parametrize("flag,value", [
    ("--fps", "0"), ("--fps", "-8"), ("--source-fps", "0"), ("--source-fps", "-16"),
])
def test_a_playback_rate_that_is_not_positive_is_refused_above_makedirs(tmp_path, flag,
                                                                        value):
    """THE OPERAND: `--fps=0` on `make_review_clip`, ABOVE `os.makedirs`.

    Measured on the base tree: `--fps=0` reached `duration=int(round(1000.0 / a.fps))`
    inside `ims[0].save(...)` and died with a bare `ZeroDivisionError` — untyped, and AFTER
    `os.makedirs(a.out)` had created the review directory, so a refused run left an empty
    directory a later reader takes for an attempt that produced nothing.
    `--source-fps=0` dies one line later, in the manifest's `a.fps / float(a.source_fps)`
    and in `clip_name`, which is the FILENAME the Director opens.

    Both are the same clause as `resample_motion`'s `--fps-src`, one tool over.
    """
    import make_review_clip as MRC

    frames = _review_frames(tmp_path)
    out = tmp_path / "review"
    with pytest.raises(MRC.ReviewClipError, match=r"--fps|--source-fps") as exc:
        MRC.main([f"--frames={frames}", f"--out={out}", "--stills=0,4", "--crop=8",
                  f"{flag}={value}"])
    ev = exc.value.evidence
    assert ev is not None, "the refusal carries no receipt"
    assert ev["clause"] == "playback_rate_not_positive", ev
    assert ev["gate"] == "ARGS" and ev["andon"] == "ReviewClipError", ev
    assert ev["flag"] == flag and ev["value"] == int(value), ev
    assert not out.exists(), (
        "a refused run left its output directory behind; the bound must sit above "
        "`os.makedirs`")


# ---- F-78f49c7c: the review clip's name carries the run token -------------


def test_the_clip_name_carries_the_run_token_when_one_is_known():
    r"""THE OPERAND: `clip_name`, which returned `review_{rate:.2f}x_{fps}fps.webp` with no
    run token at all.

    `fetch_run.derived_root_artifacts(run)` returns two patterns and the second —
    `^review_[0-9.]+x_[0-9]+fps\.[a-z0-9]+$` — cannot be bound to the run, because the name
    carries no identity. That module's own CORRECTION block measures it and names
    instruments-measure as the owner of the fix. Today the live consequence is nil (the
    canonical suffix is `.webp` and `VIDEO_SUFFIXES` is .mp4/.webm/.mkv), but the pattern
    exists to survive a change of suffix, and on that day a PREVIOUS run's review clip left
    in a re-used run root is EXEMPTED rather than raised — the exact stray class the sweep
    was added for.
    """
    import make_review_clip as MRC

    assert MRC.clip_name(8, 16) == "review_0.50x_8fps.webp"
    assert MRC.clip_name(8, 16, run="A2") == "A2_review_0.50x_8fps.webp"
    assert MRC.clip_name(8, 20, run="A0r1") == "A0r1_review_0.40x_8fps.webp"
    # a token that is not a run name is not silently pasted on
    assert MRC.clip_name(8, 16, run="") == "review_0.50x_8fps.webp"
    assert MRC.clip_name(8, 16, run=None) == "review_0.50x_8fps.webp"


def test_the_run_token_is_derived_from_the_frames_run_root(tmp_path, capsys):
    """The canonical layout is `<run>/lossless/`, so the run is the frames directory's
    parent. `--out` cannot supply it: `gate_out_directory` REFUSES an `--out` that is the
    frames directory or that holds a numbered frame population, so `--out` is by
    construction a review directory and its parent is not run-shaped."""
    import make_review_clip as MRC

    frames = _review_frames(tmp_path, run="A2")
    out = tmp_path / "E09" / "review"
    assert MRC.main([f"--frames={frames}", f"--out={out}", "--stills=0,4",
                     "--crop=8"]) == 0
    names = sorted(os.listdir(out))
    assert "A2_review_0.50x_8fps.webp" in names, names
    rec = json.loads((out / "review_manifest.json").read_text(encoding="utf-8"))
    assert rec["run_token"] == "A2", rec
    assert rec["run_token_source"] == "frames_parent", rec
    assert "A2_review" in capsys.readouterr().out


def test_an_explicit_run_flag_overrides_the_derivation(tmp_path):
    import make_review_clip as MRC

    frames = _review_frames(tmp_path, run="A2")
    out = tmp_path / "r2"
    assert MRC.main([f"--frames={frames}", f"--out={out}", "--stills=0", "--crop=8",
                     "--run=A1b"]) == 0
    assert "A1b_review_0.50x_8fps.webp" in os.listdir(out)
    rec = json.loads((out / "review_manifest.json").read_text(encoding="utf-8"))
    assert rec["run_token"] == "A1b" and rec["run_token_source"] == "--run"


def test_a_frames_directory_with_no_run_root_records_that_it_derived_nothing(tmp_path):
    """The direction the derivation does NOT bound: a frames directory whose parent is not
    a run (here, the pytest tmp root). The record says `NOT DERIVED` rather than pasting a
    plausible token onto the filename — a label on an artifact the Director opens is
    evidence, and it may not be a placeholder."""
    import make_review_clip as MRC

    d = tmp_path / "00000frames"
    d.mkdir()
    for i in range(2):
        Image.new("RGB", (16, 16), (9, 9, 9)).save(d / f"{i:05d}.png")
    out = tmp_path / "r3"
    assert MRC.main([f"--frames={d}", f"--out={out}", "--stills=0", "--crop=8"]) == 0
    rec = json.loads((out / "review_manifest.json").read_text(encoding="utf-8"))
    assert rec["run_token"] == MRC.NO_RUN_TOKEN, rec
    assert rec["run_token_source"] == "NOT DERIVED", rec
    assert "review_0.50x_8fps.webp" in os.listdir(out)
