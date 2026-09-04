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
