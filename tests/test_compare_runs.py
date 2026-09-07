"""G3's instrument: what "zero difference" is allowed to mean, and what a pixel is.

Two defects, both of which produced the exact output of a run that genuinely reproduced.

**A clean report over nothing.** `compare_channel` initialised `max_abs_diff: 0` and never
distinguished "compared and equal" from "compared nothing". Measured: two runs whose channel
directories exist but hold zero PNGs printed
`{"max_abs_diff_any_channel": 0, "channels_with_any_pixel_difference": []}` and exited 0 —
byte for byte what a reproducing render prints. Two runs with no channel in common printed
the same line with a null max and exited 0 as well. A mistyped `--a`, a run whose channels
were written under other names, or an aborted render all land there.

**A pixel counted once per channel.** `n_differing_px = int((d > 0).sum())` sums over an
(H, W, C) array, so one differing RGB pixel counted 3. That is the unit/population/object
class this repo has missed nine arcs running, in the one number that says *where* a
difference lives.

The module still reports rather than halting on a nonzero difference — that is G3's whole
design. What raises is having compared nothing, which is not a measurement at all.
"""

import json
import os
import sys

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

from conftest import load_ok_payload  # noqa: E402
import compare_runs as CR  # noqa: E402


def _png(path, arr):
    Image.fromarray(np.asarray(arr, dtype=np.uint8)).save(path)


def _run(root, name, chan="lossless", frames=1, mutate=None, h=4, w=4):
    d = os.path.join(str(root), name, chan)
    os.makedirs(d, exist_ok=True)
    for i in range(frames):
        a = np.full((h, w, 3), 100, dtype=np.uint8)
        if mutate is not None:
            a = mutate(a, i)
        _png(os.path.join(d, f"{i:05d}.png"), a)
    return os.path.join(str(root), name)


# ------------------------------------------------------------------- what a pixel is


def test_one_differing_rgb_pixel_counts_as_one_pixel(tmp_path):
    """THE fixture: a single pixel differing in all three channels. Counted over the
    (H, W, C) array it reads 3, and there is nothing beside it saying so."""
    def bump(a, i):
        a[0, 0] = (110, 110, 110)
        return a

    a = _run(tmp_path, "a")
    b = _run(tmp_path, "b", mutate=bump)
    rec = CR.compare_channel(os.path.join(a, "lossless"), os.path.join(b, "lossless"))

    assert rec["worst_frame"]["n_differing_px"] == 1
    assert rec["worst_frame"]["n_differing_samples"] == 3
    assert rec["worst_frame"]["samples_per_pixel"] == 3


def test_a_pixel_differing_in_one_channel_still_counts_once(tmp_path):
    def bump(a, i):
        a[2, 3, 1] = 250
        return a

    a = _run(tmp_path, "a")
    b = _run(tmp_path, "b", mutate=bump)
    rec = CR.compare_channel(os.path.join(a, "lossless"), os.path.join(b, "lossless"))
    assert rec["worst_frame"]["n_differing_px"] == 1
    assert rec["worst_frame"]["n_differing_samples"] == 1


def test_the_mean_is_named_after_the_thing_it_averages(tmp_path):
    a = _run(tmp_path, "a")
    b = _run(tmp_path, "b")
    rec = CR.compare_channel(os.path.join(a, "lossless"), os.path.join(b, "lossless"))
    assert rec["mean_abs_diff_per_sample"] == 0.0
    assert rec["samples_per_pixel"] == 3


# --------------------------------------------------------- a report over nothing


def test_a_channel_with_no_frames_raises_rather_than_reporting_zero(tmp_path):
    a = _run(tmp_path, "a", frames=0)
    b = _run(tmp_path, "b", frames=0)
    with pytest.raises(CR.CompareError) as e:
        CR.compare_channel(os.path.join(a, "lossless"), os.path.join(b, "lossless"))
    assert e.value.evidence["frames_compared"] == 0
    assert e.value.evidence["names_a"] == []


def test_channels_whose_frames_are_all_shape_mismatched_raise(tmp_path):
    """The other way to compare nothing: every shared name exists on both sides and none
    of them is comparable. `continue` used to leave the record at its zero initialiser."""
    a = _run(tmp_path, "a", h=4, w=4)
    b = _run(tmp_path, "b", h=8, w=8)
    with pytest.raises(CR.CompareError) as e:
        CR.compare_channel(os.path.join(a, "lossless"), os.path.join(b, "lossless"))
    assert e.value.evidence["shape_mismatch"]


def test_runs_with_no_channel_in_common_raise(tmp_path):
    a = _run(tmp_path, "a", chan="lossless")
    b = _run(tmp_path, "b", chan="depth_perframe")
    with pytest.raises(CR.CompareError) as e:
        CR.compare_runs(a, b)
    assert e.value.evidence["channels_a"] == ["lossless"]
    assert e.value.evidence["channels_b"] == ["depth_perframe"]


def test_a_master_only_pair_is_not_a_comparison(tmp_path):
    """`master` is excluded by design, so two runs sharing only `master` share nothing."""
    a = _run(tmp_path, "a", chan="master")
    b = _run(tmp_path, "b", chan="master")
    with pytest.raises(CR.CompareError,
                       match=r"share no comparable channel directory \(master is excluded"):
        CR.compare_runs(a, b)


def test_the_printed_line_carries_how_many_frames_were_opened(tmp_path):
    """So a clean verdict cannot be read without the size of the population behind it."""
    a = _run(tmp_path, "a", frames=3)
    b = _run(tmp_path, "b", frames=3)
    report = CR.compare_runs(a, b)
    assert report["verdict_inputs"]["frames_compared"] == 3
    assert report["verdict_inputs"]["max_abs_diff_any_channel"] == 0


def test_a_real_difference_still_reports_rather_than_halting(tmp_path):
    """G3's design, pinned: a nonzero difference is a measurement, not an andon."""
    def bump(a, i):
        a[1, 1] = (200, 0, 0)
        return a

    a = _run(tmp_path, "a", frames=2)
    b = _run(tmp_path, "b", frames=2, mutate=bump)
    report = CR.compare_runs(a, b)
    assert report["verdict_inputs"]["max_abs_diff_any_channel"] == 100
    assert report["verdict_inputs"]["channels_with_any_pixel_difference"] == ["lossless"]


# ------------------------------------------------- a report over SOME of the population
#
# Wave 3's two andons refuse only a TOTAL absence of comparison. A PARTIAL one still read
# as a clean reproduction, with the evidence that contradicts it sitting in the JSON and
# absent from the verdict. Both measured 2026-09-03.


def test_a_six_frame_run_against_a_three_frame_one_is_not_a_reproduction(tmp_path):
    """An aborted render: A holds 6 frames, B holds the first 3, byte-identical. The old
    line read `frames_compared: 3, max_abs_diff_any_channel: 0` and exited 0, with
    `only_in_a: [00003,00004,00005]` unread in the per-channel record."""
    a = _run(tmp_path, "a", frames=6)
    b = _run(tmp_path, "b", frames=3)
    with pytest.raises(CR.CompareError) as e:
        CR.compare_runs(a, b)
    ev = e.value.evidence
    assert ev["frames_a"] == 6 and ev["frames_b"] == 3
    assert ev["only_in_a"] == ["00003.png", "00004.png", "00005.png"]


def test_some_shared_names_shape_mismatched_is_not_a_reproduction(tmp_path):
    """Four names on both sides, three of them rendered at another size with wholly
    different content: the pixel verdict said the render reproduced over one of four."""
    a = _run(tmp_path, "a", frames=4, h=8, w=8)
    b = os.path.join(str(tmp_path), "b")
    d = os.path.join(b, "lossless")
    os.makedirs(d, exist_ok=True)
    for i in range(4):
        side = 8 if i == 0 else 16
        _png(os.path.join(d, f"{i:05d}.png"), np.full((side, side, 3), 100, np.uint8))
    with pytest.raises(CR.CompareError) as e:
        CR.compare_runs(a, b)
    ev = e.value.evidence
    assert len(ev["shape_mismatch"]) == 3
    assert ev["frames_compared"] == 1


def test_the_printed_verdict_carries_the_two_populations_and_the_mismatch_counts(tmp_path):
    """A clean verdict may not be readable without the population behind it.

    The population half is unchanged. The two mismatch COUNTS this used to assert were
    removed in wave 8 and the reason is the block appended at the end of this file: they
    were structurally unreachable above zero, so asserting `== 0` was asserting a
    constant. What replaces them is the policy statement, which is what is true.
    """
    a = _run(tmp_path, "a", frames=3)
    b = _run(tmp_path, "b", frames=3)
    vi = CR.compare_runs(a, b)["verdict_inputs"]
    assert vi["frames_a"] == 3 and vi["frames_b"] == 3
    assert "refused, never reported" in vi["name_mismatch_policy"]
    assert "refused, never reported" in vi["shape_mismatch_policy"]


def test_the_partial_andon_survives_python_optimize(tmp_path):
    """It raises; it is not an `assert`. `-O` deletes an assert and this must survive."""
    import subprocess
    import sys as _sys

    a = _run(tmp_path, "a", frames=4)
    b = _run(tmp_path, "b", frames=2)
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    code = (
        "import sys; sys.path.insert(0, r'%s')\n"
        "import compare_runs as CR\n"
        "try:\n"
        "    CR.compare_runs(r'%s', r'%s')\n"
        "except CR.CompareError:\n"
        "    print('RAISED')\n"
    ) % (os.path.join(repo, "tools"), a, b)
    out = subprocess.run([_sys.executable, "-O", "-c", code], capture_output=True, text=True)
    assert "RAISED" in out.stdout, out.stderr


# ------------------------- a field with one reachable value is not a measurement
#
# `verdict_inputs` reported `n_name_mismatch` (summed from each channel's `name_mismatch`
# key) and `n_shape_mismatch` (summed from each channel's `shape_mismatch` list). Both were
# structurally unreachable above zero on the merged tree: `compare_channel` RAISES on any
# name disagreement before `rec` can be returned — so the `rec["name_mismatch"]` assignment
# one line above that raise was dead — and RAISES on any shape disagreement before the same.
#
# Measured 2026-09-04: a matched pair returned `n_name_mismatch 0`, `n_shape_mismatch 0`,
# and the returned channel record did not even carry a `name_mismatch` key; a 3-vs-4-frame
# pair and an 8px-vs-16px pair each raised `CompareError` instead of returning a report. The
# only two values those fields could ever take were 0 and 0 — sitting beside
# `frames_compared: N` and reading as a measurement that the two runs named the same frames
# and had comparable shapes. CLAUDE.md names the class twice over: a report may not contain
# a placeholder shaped like evidence, and a check that cannot fail is not a check.


def test_no_returned_report_can_carry_a_mismatch_count(tmp_path):
    """The fields are gone; nothing downstream can read a constant as a measurement."""
    a = _run(tmp_path, "a", frames=3)
    b = _run(tmp_path, "b", frames=3)
    report = CR.compare_runs(a, b)
    assert "n_name_mismatch" not in report["verdict_inputs"]
    assert "n_shape_mismatch" not in report["verdict_inputs"]
    for rec in report["channels"].values():
        assert "name_mismatch" not in rec, rec


def test_the_policy_the_report_states_is_the_one_the_code_enforces(tmp_path):
    """Both halves of the claim, exercised: a name disagreement raises, and a shape
    disagreement raises — so "refused, never reported" is a statement about behaviour."""
    a = _run(tmp_path, "a", frames=3)
    b = _run(tmp_path, "b", frames=4)
    with pytest.raises(CR.CompareError, match=r"do not name the same frames"):
        CR.compare_runs(a, b)

    c = _run(tmp_path, "c", frames=2)
    d = _run(tmp_path, "d", frames=2, h=16, w=16)
    with pytest.raises(CR.CompareError, match=r"differ in SHAPE"):
        CR.compare_runs(c, d)


def test_the_dead_assignment_is_gone_from_the_source():
    """Read off the AST: the `rec["name_mismatch"] = ...` statement sat one line above the
    raise that made it unreachable. A comment recording the defect must not satisfy this."""
    import ast

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tree = ast.parse(open(os.path.join(root, "tools", "compare_runs.py"),
                          encoding="utf-8").read())
    subscripts = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant)
                and t.slice.value == "name_mismatch" for t in node.targets)]
    assert subscripts == [], [ast.dump(s) for s in subscripts]


def test_the_png_listing_is_case_insensitive_like_the_fetchers(tmp_path):
    """`fetch_run.verify_downloads` counts `00099.PNG` as a downloaded frame; a comparison
    that cannot see it would report a reproduction over fewer frames than were fetched."""
    a = _run(tmp_path, "a", frames=2)
    b = _run(tmp_path, "b", frames=2)
    for run in (a, b):
        chan = os.path.join(run, "lossless")
        src = os.path.join(chan, sorted(os.listdir(chan))[0])
        Image.open(src).save(os.path.join(chan, "00009.PNG"))
    report = CR.compare_runs(a, b)
    # two numbered frames per run plus the upper-case one: three compared.
    assert report["verdict_inputs"]["frames_compared"] == 3


# ------------------------------ the CLI, and the field whose only reachable value was []
#
# **The hand-rolled parser.** `main` read `for token in argv: key, _, value =
# token[2:].partition("=")` — every token has its first two characters removed regardless of
# shape, unknown keys are accepted in silence, and the report is written only `if "out" in
# args`. Three measurements 2026-09-04 against the rig's real outputs/E02/runs A0r1 / A0r2
# (read-only):
#
#   1. `--outt=<path>` printed `COMPARE {...frames_compared: 99...}`, exited 0, and wrote no
#      file at that path — G3's comparison reporting a clean verdict and leaving no report,
#      because the operator mistyped the flag that names the report;
#   2. `--help` died with `KeyError: 'a'` — the tool could not answer for its own usage,
#      while every sibling in this domain uses argparse;
#   3. the space-separated `--a <path> --b <path>` form the siblings accept produced
#      `run_a = ''` and `FileNotFoundError: [WinError 3] ... ''`, naming no flag.
#
# **And `shape_mismatch` was a placeholder shaped like evidence.** `rec["shape_mismatch"]`
# was initialised to `[]`, appended to, and then RAISED on whenever it was non-empty — so
# every record a caller can read carries the empty list and no other value is reachable.
# That is the defect the wave-8 correction removed from `verdict_inputs` and left one level
# down: the module docstring says the counts "are gone; in their place `verdict_inputs`
# states the POLICY", and the per-channel record was not swept with it. Read on the rig's
# real A0r1 vs A0r2 (read-only): all three channels returned `shape_mismatch: []` beside
# `frames_compared: 33`.

import json  # noqa: E402
import subprocess  # noqa: E402


def test_no_returned_channel_record_carries_a_field_with_one_reachable_value(tmp_path):
    """The census, keyed on the RETURNED record rather than on the source text: a key whose
    only reachable value is its initial one is not a measurement, and a reader beside
    `frames_compared: N` reads it as a check that ran and found nothing."""
    a = _run(tmp_path, "a", frames=3)
    b = _run(tmp_path, "b", frames=3)
    report = CR.compare_runs(a, b)
    for name, rec in report["channels"].items():
        assert "shape_mismatch" not in rec, (name, sorted(rec))
    # the policy is stated where the wave-8 correction put the other two
    assert "shape_mismatch_policy" in report["verdict_inputs"]


def test_the_shape_refusal_still_carries_the_mismatch_in_its_evidence(tmp_path):
    """The guard the other way: removing the record key must not remove the measurement.
    The evidence dict on the refusal is where it belongs — it is read when it exists."""
    a = _run(tmp_path, "a", frames=2)
    b = _run(tmp_path, "b", frames=2, h=16, w=16)
    with pytest.raises(CR.CompareError, match=r"differ in SHAPE") as e:
        CR.compare_runs(a, b)
    assert e.value.evidence["n_shape_mismatch"] == 2
    assert e.value.evidence["shape_mismatch"][0]["a"] == [4, 4, 3]


def test_an_unknown_flag_is_refused_rather_than_accepted_in_silence(tmp_path):
    """THE fixture: the plausible typo in the flag that names the report."""
    a = _run(tmp_path, "a", frames=2)
    b = _run(tmp_path, "b", frames=2)
    out = tmp_path / "report.json"
    with pytest.raises(SystemExit) as e:
        CR.main([f"--a={a}", f"--b={b}", f"--outt={out}"])
    assert e.value.code == 2
    assert not out.exists()


@pytest.mark.parametrize("form", ["equals", "space"])
def test_out_written_in_either_form_leaves_a_file_on_disk(tmp_path, form, capsys):
    """`--a <path>` is the form every sibling accepts and this tool silently read as ''."""
    a = _run(tmp_path, "a", frames=2)
    b = _run(tmp_path, "b", frames=2)
    out = tmp_path / "report.json"
    argv = ([f"--a={a}", f"--b={b}", f"--out={out}"] if form == "equals"
            else ["--a", str(a), "--b", str(b), "--out", str(out)])
    assert CR.main(argv) == 0
    assert out.exists()
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["verdict_inputs"]["frames_compared"] == 2
    printed = capsys.readouterr().out
    # SUCCESS convention: exit 0 AND a line naming the artifact the run produced.
    line = load_ok_payload(printed, "COMPARE_RUNS_OK")
    assert os.path.abspath(line["report"]) == os.path.abspath(str(out))


def test_a_run_with_no_out_says_so_rather_than_implying_a_report(tmp_path, capsys):
    """`--out` stays optional, and the line says explicitly that no report was written."""
    a = _run(tmp_path, "a", frames=2)
    b = _run(tmp_path, "b", frames=2)
    assert CR.main([f"--a={a}", f"--b={b}"]) == 0
    printed = capsys.readouterr().out
    assert "COMPARE_RUNS_OK " in printed
    assert "no report written" in printed


def test_the_tool_can_answer_for_its_own_usage():
    """`--help` died with `KeyError: 'a'`."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    res = subprocess.run(
        [sys.executable, os.path.join(root, "tools", "compare_runs.py"), "--help"],
        capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    for flag in ("--a", "--b", "--out"):
        assert flag in res.stdout, res.stdout


def test_a_missing_required_flag_is_named(tmp_path):
    a = _run(tmp_path, "a", frames=2)
    with pytest.raises(SystemExit) as e:
        CR.main([f"--a={a}"])
    assert e.value.code == 2
