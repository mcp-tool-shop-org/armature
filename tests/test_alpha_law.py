"""The authored-RGBA law, over every tool that produces an image a route SUBMITS.

The Director's ruling, 2026-08-12: every reference or start-frame render of the character
is authored RGBA with a real alpha channel, and **the RGB composite each route actually
submits is a deliberate, recorded choice** — because video VAEs are RGB and raw transparency
cannot reach the model. A grey previz void is never again an accidental part of a submitted
input.

Two tools carried that law after wave 3 (`composite_reference.gate_alpha` +
`composite_over`, and `encode_control.read_frames`'s `--alpha-over` refusal) and three did
not. Measured 2026-09-03 on `fit_reference`: a 128x256 RGBA master with alpha extrema
(0, 255) over a hidden RGB of (128, 128, 128) produced an RGB fit whose pad pixel was
(128, 128, 128), with `"pad_source": "median of the source's own outer 4% border"` in the
provenance and the word `alpha` nowhere in the record. The pad was read out from behind
transparency — the part the author made invisible — and `fit_reference` output is the
reference image E08 and E10 both submitted.

This file is the FAMILY test: every producer of a submitted image input refuses a 4-channel
source with no plate named, and composites over the named plate when there is one. It is
parametrized rather than written four times so a new producer joins it by being listed.
"""

import json
import os
import sys

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "tools"))

import composite_reference as CREF  # noqa: E402
import encode_control as EC  # noqa: E402
import fit_reference as FR  # noqa: E402
import make_plate as MP  # noqa: E402
import pack_pose_pack as PPP  # noqa: E402

#: The RGB hiding under alpha=0 in every fixture below. If it reaches an output, the tool
#: read the part the author made invisible.
HIDDEN = (128, 128, 128)
PLATE = (10, 20, 30)


def _rgba(path, w=32, h=48, figure=(200, 40, 40)):
    """An opaque figure on a fully transparent field whose hidden RGB is HIDDEN."""
    a = np.zeros((h, w, 4), dtype=np.uint8)
    a[..., :3] = HIDDEN
    a[h // 4:3 * h // 4, w // 4:3 * w // 4, :3] = figure
    a[h // 4:3 * h // 4, w // 4:3 * w // 4, 3] = 255
    Image.fromarray(a, mode="RGBA").save(path)
    return path


# ------------------------------------------------------------------ the family, refusing


def _fit_reference(tmp, alpha_over):
    src = _rgba(str(tmp / "twin.png"))
    argv = [f"--src={src}", f"--out={tmp / 'out'}", "--width=64", "--height=64"]
    if alpha_over:
        argv.append("--alpha-over=%d,%d,%d" % alpha_over)
    return FR.main(argv)


def _make_plate(tmp, alpha_over):
    src = _rgba(str(tmp / "still.png"))
    argv = [f"--src={src}", f"--out={tmp / 'out'}", "--width=64", "--height=64",
            "--why=the family test"]
    if alpha_over:
        argv.append("--alpha-over=%d,%d,%d" % alpha_over)
    return MP.main(argv)


def _pack_pose_pack(tmp, alpha_over):
    d = tmp / "sticks"
    d.mkdir()
    for i in range(2):
        # distinct per frame: an APNG writer drops a frame identical to its predecessor,
        # and Gate R would then fire on the pack rather than on the alpha law
        _rgba(str(d / f"{i:05d}.png"), figure=(200, 40 + 60 * i, 40))
    argv = [f"--frames={d}", f"--out={tmp / 'out'}"]
    if alpha_over:
        argv.append("--alpha-over=%d,%d,%d" % alpha_over)
    return PPP.main(argv)


def _encode_control(tmp, alpha_over):
    """The sibling that already carried the law — in the family test so it stays carried."""
    d = tmp / "frames"
    d.mkdir()
    _rgba(str(d / "00000.png"))
    return EC.load_frames(str(d), alpha_over=alpha_over)


PRODUCERS = {
    "fit_reference": (_fit_reference, FR.FitReferenceError),
    "make_plate": (_make_plate, MP.PlateError),
    "pack_pose_pack": (_pack_pose_pack, PPP.PosePackError),
    "encode_control": (_encode_control, EC.EncodeFailure),
}


@pytest.mark.parametrize("name", sorted(PRODUCERS))
def test_every_producer_of_a_submitted_input_refuses_alpha_with_no_plate_named(
        name, tmp_path):
    run, exc = PRODUCERS[name]
    with pytest.raises(exc) as e:
        run(tmp_path, None)
    ev = e.value.evidence
    assert ev.get("alpha_present") is True, ev
    assert ev.get("alpha_max") == 255 and ev.get("alpha_min") == 0, ev


@pytest.mark.parametrize("name", sorted(PRODUCERS))
def test_a_named_plate_makes_the_composite_the_choice_it_records(name, tmp_path):
    """The other half of the law: the drop is allowed once the plate is NAMED."""
    run, _ = PRODUCERS[name]
    run(tmp_path, PLATE)


def test_no_producer_of_a_submitted_input_decodes_with_imread_color(tmp_path):
    """The census. `cv2.IMREAD_COLOR` returns 3-channel BGR and drops the 4th silently —
    the exact mechanism, and it may not come back into any of these files."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    offenders = []
    for mod in ("fit_reference", "make_plate", "composite_reference", "encode_control",
                "pack_pose_pack"):
        src = open(os.path.join(root, "tools", f"{mod}.py"), encoding="utf-8").read()
        # named in a comment or docstring is how the defect is RECORDED; called is the bug
        for line in src.splitlines():
            stripped = line.strip()
            # naming it in prose is how the defect is RECORDED; DECODING with it is the bug
            if "cv2.imread(" in stripped and "IMREAD_COLOR" in stripped:
                offenders.append(f"{mod}: {stripped}")
    assert offenders == [], offenders


# --------------------------------------------------------------- fit_reference, in detail


def test_the_pad_is_the_named_plate_and_never_the_rgb_behind_alpha(tmp_path):
    """THE measured defect: the letterbox pad was the median of the source's outer border,
    which on an authored master is the RGB sitting under alpha=0."""
    import cv2

    _fit_reference(tmp_path, PLATE)
    dst = tmp_path / "out" / "twin_fit_64x64.png"
    out = cv2.imread(str(dst), cv2.IMREAD_UNCHANGED)
    assert out is not None and out.shape[2] == 3
    corner = tuple(int(v) for v in out[1, 1])
    assert corner == PLATE[::-1], corner            # cv2 writes BGR
    assert corner != HIDDEN


def test_the_provenance_says_what_happened_to_the_alpha(tmp_path):
    _fit_reference(tmp_path, PLATE)
    rec = json.loads((tmp_path / "out" / "twin_fit_provenance.json").read_text(
        encoding="utf-8"))
    src = rec["source"]
    assert src["alpha_present"] is True
    assert [src["alpha_min"], src["alpha_max"]] == [0, 255]
    assert "composited" in rec["transform"]["alpha_disposition"]
    assert rec["transform"]["pad_source"].startswith("the named plate")


def test_pad_auto_on_an_rgba_source_never_samples_the_hidden_border(tmp_path):
    """`--pad=auto` is the DEFAULT, and the border it samples on an RGBA master is by
    definition the part the author made invisible."""
    _fit_reference(tmp_path, PLATE)
    rec = json.loads((tmp_path / "out" / "twin_fit_provenance.json").read_text(
        encoding="utf-8"))
    assert rec["transform"]["pad_bgr"] == list(PLATE[::-1])
    assert "median of the source" not in rec["transform"]["pad_source"]
    assert rec["transform"]["pad_source"].startswith("the named plate")


def test_an_opaque_rgb_source_is_untouched_by_the_law(tmp_path):
    """The guard the other way: a 3-channel source still letterboxes on its own border."""
    import cv2

    src = str(tmp_path / "rgb.png")
    img = np.full((48, 32, 3), 77, np.uint8)
    img[12:36, 8:24] = (200, 40, 40)
    cv2.imwrite(src, img)
    FR.main([f"--src={src}", f"--out={tmp_path / 'o'}", "--width=64", "--height=64"])
    rec = json.loads((tmp_path / "o" / "rgb_fit_provenance.json").read_text(
        encoding="utf-8"))
    assert rec["source"]["alpha_present"] is False
    assert rec["transform"]["pad_bgr"] == [77, 77, 77]
    assert "border" in rec["transform"]["pad_source"]


def test_the_law_survives_python_optimize(tmp_path):
    """It raises; it is not an `assert`. `-O` deletes an assert and this must survive."""
    import subprocess

    src = _rgba(str(tmp_path / "twin.png"))
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    code = (
        "import sys; sys.path.insert(0, r'%s')\n"
        "import fit_reference as FR\n"
        "try:\n"
        "    FR.main([r'--src=%s', r'--out=%s', '--width=64', '--height=64'])\n"
        "except FR.FitReferenceError:\n"
        "    print('RAISED')\n"
    ) % (os.path.join(root, "tools"), src, tmp_path / "o2")
    out = subprocess.run([sys.executable, "-O", "-c", code], capture_output=True, text=True)
    assert "RAISED" in out.stdout, out.stderr


def test_the_shared_law_is_one_implementation(tmp_path):
    """Not four copies: the three tools that lacked it call the module that had it."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for mod in ("fit_reference", "make_plate", "pack_pose_pack", "encode_control"):
        src = open(os.path.join(root, "tools", f"{mod}.py"), encoding="utf-8").read()
        assert "compose_over_named_plate" in src, mod
    assert callable(CREF.compose_over_named_plate)


# --------------------------------------- one flag parser, not three, for --alpha-over
#
# `compose_over_named_plate`'s docstring states the contract the wave-6 sweep delivered:
# "there is one refusal, one composite and one record shape". The COMPOSITE and the RECORD
# were one implementation; the FLAG PARSER was three. `fit_reference`, `make_plate` and
# `pack_pose_pack` all called `composite_reference.parse_plate` and got a typed error with
# an evidence dict; `encode_control.main` reimplemented the same three-integer check inline
# and raised `SystemExit("--alpha-over takes three 0-255 integers, ...")` — a bare string
# with no evidence dict and no `EncodeFailure`, in the one tool of the four whose output is
# UPLOADED. And `composite_reference.main` was a third variant with no range check at all.
#
# `test_the_shared_law_is_one_implementation` above asserts only that the string
# `compose_over_named_plate` appears in each of the four sources, so the divergent flag
# parsers were invisible to it.

PLATE_PRODUCERS = ("fit_reference", "make_plate", "pack_pose_pack", "encode_control")


def _drive_with_bad_plate(mod_name, tmp_path):
    """Each producer's `main`, given VALID inputs and an invalid `--alpha-over`.

    Valid inputs on purpose: three of the four parse the flag only after reading their
    source image, so a fake path would be refused by a different andon and the test would
    pass without ever reaching the parser it exists for.
    """
    import importlib

    mod = importlib.import_module(mod_name)
    out = str(tmp_path / mod_name)
    src = str(tmp_path / "src.png")
    Image.fromarray(np.zeros((8, 8, 3), dtype=np.uint8)).save(src)
    frames = tmp_path / "frames"
    frames.mkdir(exist_ok=True)
    Image.fromarray(np.zeros((8, 8, 3), dtype=np.uint8)).save(frames / "00000.png")
    argv = {
        "fit_reference": [f"--src={src}", f"--out={out}", "--width=8", "--height=8"],
        "make_plate": [f"--src={src}", f"--out={out}", "--width=8", "--height=8",
                       "--why=a reason"],
        "pack_pose_pack": [f"--frames={frames}", f"--out={out}"],
        "encode_control": [f"--frames={frames}", f"--out={out}/v.mkv"],
    }[mod_name] + ["--alpha-over=1,2"]
    return mod, argv


@pytest.mark.parametrize("mod_name", PLATE_PRODUCERS)
def test_every_producer_refuses_a_malformed_alpha_over_through_the_one_parser(
        mod_name, tmp_path):
    """The refusal is the TOOL's own typed error carrying `supplied` — never a bare
    `SystemExit` string, and never a different shape in the tool that uploads."""
    import armature_core.errors as errors

    mod, argv = _drive_with_bad_plate(mod_name, tmp_path)
    with pytest.raises(errors.ArmatureError) as e:
        mod.main(argv)
    assert e.value.evidence["supplied"] == "1,2", (mod_name, e.value.evidence)
    assert "--alpha-over" in str(e.value), mod_name


def test_the_flag_parser_is_one_implementation_read_off_the_ast():
    """The census `test_the_shared_law_is_one_implementation` could not see: every producer
    CALLS `parse_plate`, and none of them splits the flag itself. Read off the AST so a
    comment recording the defect cannot satisfy it."""
    import ast

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for mod in PLATE_PRODUCERS + ("composite_reference",):
        tree = ast.parse(open(os.path.join(root, "tools", f"{mod}.py"),
                              encoding="utf-8").read())
        calls, splits = set(), []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                f = node.func
                name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
                calls.add(name)
                if (name == "split" and isinstance(f, ast.Attribute)
                        and isinstance(f.value, ast.Attribute)
                        and f.value.attr in ("alpha_over", "plate")):
                    splits.append(mod)
        assert "parse_plate" in calls, mod
        assert splits == [], splits
