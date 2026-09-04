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
    twenty-seven constructors and `_CarriesEvidence` itself, so the population that remains
    is TWENTY-NINE classes, every one of them inheriting the base's contract.
    """
    live = _plain_refusal_classes()
    assert len(live) == 29, sorted(live)
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
