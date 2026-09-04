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

import ast
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


# WAVE 8, F-be95e51f — the two censuses in this file typed their populations and read
# their property as a substring. `'compose_over_named_plate' in src` is satisfied by the
# comment that explains the call: measured 2026-09-04, fit_reference, make_plate,
# pack_pose_pack and encode_control each carry the token two or three times and each has
# exactly ONE real call site (fit_reference:186, make_plate:211, pack_pose_pack:115,
# encode_control:209), so deleting the call and leaving the prose kept the test green. The
# sibling census iterated a typed five-module tuple rather than deriving which tools take
# part in the law at all.

ALPHA_HELPER = "compose_over_named_plate"
TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(TOOLS, "tools")


def _calls(tree, name):
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            called = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if called == name:
                out.append(node.lineno)
    return sorted(out)


def _defines(tree, name):
    return any(isinstance(n, ast.FunctionDef) and n.name == name for n in ast.walk(tree))


def _imports(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and any(a.name == name for a in node.names):
            return True
        if isinstance(node, ast.Import) and any(a.name == name for a in node.names):
            return True
    return False


def alpha_law_tools():
    """THE DERIVATION: every tool that takes part in the alpha law.

    Two ways in, both read off the tree rather than typed: a module that IMPORTS (or
    defines) `compose_over_named_plate`, and a module that decodes an image
    alpha-aware — `cv2.IMREAD_UNCHANGED` is the only way a fourth channel enters at all,
    so a producer that reads that way is one this law governs whether or not it has
    adopted the helper yet.
    """
    out = []
    for name in sorted(os.listdir(TOOLS)):
        if not name.endswith(".py"):
            continue
        with open(os.path.join(TOOLS, name), encoding="utf-8") as fh:
            src = fh.read()
        tree = ast.parse(src)
        if _imports(tree, ALPHA_HELPER) or _defines(tree, ALPHA_HELPER) \
                or "IMREAD_UNCHANGED" in src:
            out.append(name[:-3])
    return out


#: Derived 2026-09-04. Equality, so a fifth producer joins the law's census the day it
#: imports the helper or reads a fourth channel.
RECORDED_ALPHA_TOOLS = ["composite_reference", "encode_control", "fit_reference",
                        "make_plate", "pack_pose_pack"]


def test_the_alpha_law_population_is_derived_and_has_not_grown_silently():
    pop = alpha_law_tools()
    assert pop == RECORDED_ALPHA_TOOLS, {
        "appeared": sorted(set(pop) - set(RECORDED_ALPHA_TOOLS)),
        "vanished": sorted(set(RECORDED_ALPHA_TOOLS) - set(pop)),
    }


def test_no_producer_of_a_submitted_input_decodes_with_imread_color():
    """The census. `cv2.IMREAD_COLOR` returns 3-channel BGR and drops the 4th silently —
    the exact mechanism, and it may not come back into any of these files. Over the
    DERIVED population now, not the five names that used to be typed here."""
    offenders = []
    for mod in alpha_law_tools():
        with open(os.path.join(TOOLS, f"{mod}.py"), encoding="utf-8") as fh:
            src = fh.read()
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


def test_the_shared_law_is_one_implementation():
    """Not four copies: the tools that lacked it CALL the module that had it.

    Asserted as an `ast.Call`, over the derived population. `'compose_over_named_plate'
    in src` was satisfied by the comment above the call — and a producer that reverted to
    parsing its own `--alpha-over` while keeping the name in prose satisfied it too. One
    module is exempt and the exemption is checked, not stated: `composite_reference`
    DEFINES the helper, and a definition is not a call.
    """
    without = {}
    for mod in alpha_law_tools():
        with open(os.path.join(TOOLS, f"{mod}.py"), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        if _defines(tree, ALPHA_HELPER):
            assert not _calls(tree, ALPHA_HELPER) or mod == "composite_reference"
            continue
        sites = _calls(tree, ALPHA_HELPER)
        if not sites:
            without[mod] = "names it, never calls it" if _imports(tree, ALPHA_HELPER) \
                else "reads a fourth channel and never goes through the law"
    assert without == {}, (
        f"these producers do not CALL {ALPHA_HELPER}: {without}. The alpha ruling is that "
        f"an authored input carries alpha and the RGB composite is a RECORDED choice; a "
        f"producer that drops the fourth channel silently is the thing the law forbids.")
    assert callable(CREF.compose_over_named_plate)
    assert _defines(ast.parse(open(os.path.join(TOOLS, "composite_reference.py"),
                                   encoding="utf-8").read()), ALPHA_HELPER)


def test_the_call_site_check_is_not_satisfied_by_the_comment_above_the_call():
    """Rule 3, on the exact substitution that used to pass: a module naming the helper in
    a docstring and a comment, and calling nothing."""
    prose_only = ast.parse(
        '"""Composites through compose_over_named_plate, as the law requires."""\n'
        "from composite_reference import compose_over_named_plate\n"
        "def main(arr):\n"
        "    # compose_over_named_plate(arr, plate, label='x')\n"
        "    return arr[:, :, :3]\n")
    real = ast.parse(
        "from composite_reference import compose_over_named_plate\n"
        "def main(arr):\n"
        "    return compose_over_named_plate(arr, 'plate', label='x')\n")
    assert _imports(prose_only, ALPHA_HELPER) and _calls(prose_only, ALPHA_HELPER) == []
    assert _calls(real, ALPHA_HELPER) == [3]
