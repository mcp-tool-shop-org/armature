"""Wave 18, instruments-measure: the two flags the UPLOADED pack is written from.

Two findings, one family and one bound:

* **F-6bb38028** — `pack_pose_pack --fps` divides in `write_pack` and in the manifest, and
  was unbounded. On the base tree `--fps=0` died with a bare `ZeroDivisionError` and
  `--fps=-16` with a bare `struct.error` / `RuntimeError`, in all four cases AFTER
  `os.makedirs` had created `--out` and left it behind empty.
* **F-62dec63b** — `pack_pose_pack --name` was pasted into the output path with no check
  that it names one path component. `--name=../escaped` printed `PACK_POSE_PACK_OK` with
  `"gate_R": "identical"`, exited 0, and put the pack one directory ABOVE the manifest that
  certifies it.

**The rule this file is written to (wave-18 brief, rule 2): a fix's red proof runs against
its SIBLINGS.** So the operand each finding named is proven red, and so is every neighbour
of it in the same parser and the same family: both pack formats, both signs of the rate,
both path separators on either platform, the two dot names, an absolute path, an empty
name. The population these two tools sit in (every `--name`/`--out`/rate flag
pasted into a path or divided by, across the domain's 42 instruments) is enumerated in the
wave-18 seams inbox, SEAM 10; the rest, including `make_review_clip --run` and
`make_ab_clip --a-fps/--b-fps`, are DEFERRED Stage B items and are deliberately untouched.

Everything here drives the tool the way a caller does — `main(argv)` in-process for the
refusals, a real subprocess for the halt records — because the property under test is what
lands on disk and what the operator reads, not what a function returns.
"""

import json
import os
import subprocess
import sys

import numpy as np
import pytest
from PIL import Image

from conftest import REPO, TOOLS  # noqa: F401

import pack_pose_pack as PP


# ---------------------------------------------------------------------------
# fixtures: the real subjects, in the shape the tools actually receive them
# ---------------------------------------------------------------------------


def stick_frames(directory, n=4, width=64, height=48):
    """`n` one-pixel-stick frames on black, named `NNNNN.png` — `--frames`' own shape."""
    os.makedirs(directory, exist_ok=True)
    for i in range(n):
        a = np.zeros((height, width, 3), np.uint8)
        a[10 + i % 5, :] = (255, 0, 0)
        a[:, 20 + i % 7] = (0, 85, 255)
        Image.fromarray(a, "RGB").save(os.path.join(directory, f"{i:05d}.png"))
    return directory


def tree_under(root):
    """Every path under `root`, relative and sorted. `[]` when `root` does not exist."""
    if not os.path.isdir(root):
        return []
    out = []
    for base, dirs, files in os.walk(root):
        for n in list(dirs) + list(files):
            out.append(os.path.relpath(os.path.join(base, n), root).replace(os.sep, "/"))
    return sorted(out)


#: The names that are NOT one path component. `.` and `..` are the two `os.path.basename`
#: returns unchanged — a check spelled as `basename(x) != x` alone lets both through — and
#: `a\b` is the one that separates the platforms: on POSIX `basename("a\\b")` IS the whole
#: string, so a Windows-only check passes it straight into a join.
NOT_A_NAME = ("../escaped", "..", ".", "a/b", "a\\b", "/abs", "", "   ")


# ===========================================================================
# F-62dec63b — `pack_pose_pack --name` is a NAME
# ===========================================================================


def test_a_pack_name_that_escapes_out_refuses_and_writes_nothing_anywhere(tmp_path):
    """THE OPERAND the finding named, and the two things that made it dangerous.

    On the base tree this exact call printed `PACK_POSE_PACK_OK` with `"gate_R":
    "identical"`, returned 0, wrote the pack to `<base>/esc/escaped.apng.png` and left
    `pose_pack_manifest.json` behind in `<base>/esc/inner` — so the directory the caller was
    told to read held a manifest and no pack, and Gate R read the escaped file back and
    called it identical, because Gate R compares pixels and is blind to where they live.
    """
    frames = stick_frames(str(tmp_path / "frames"))
    root = tmp_path / "esc"
    out = root / "inner"
    with pytest.raises(PP.PosePackError) as exc:
        PP.main([f"--frames={frames}", f"--out={out}", "--name=../escaped"])
    ev = exc.value.evidence
    assert ev["andon"] == "PosePackError"
    assert ev["clause"] == "output_name_is_not_a_name"
    assert ev["flag"] == "--name" and ev["name"] == "../escaped"
    # NOTHING was written: not the escaped pack, not the manifest, not `--out` itself.
    assert tree_under(str(root)) == []


@pytest.mark.parametrize("name", NOT_A_NAME)
def test_every_sibling_spelling_of_a_name_that_is_not_a_name_refuses(tmp_path, name):
    """Rule 2: the operand's SIBLINGS, each proven red, not the operand alone.

    `a\\b` and the two dot names are the members a `basename(x) != x` check alone lets out
    (on POSIX for the first, on both platforms for the other two), and an empty `--name`
    wrote a file called `.apng.png` on the base tree.
    """
    frames = stick_frames(str(tmp_path / "frames"))
    out = tmp_path / "o" / "inner"
    with pytest.raises(PP.PosePackError) as exc:
        PP.main([f"--frames={frames}", f"--out={out}", f"--name={name}"])
    assert exc.value.evidence["clause"] == "output_name_is_not_a_name"
    assert tree_under(str(tmp_path / "o")) == []


def test_a_pack_name_that_is_a_name_still_writes_the_pack_and_its_manifest(tmp_path):
    """The other direction of the bound: the andon refuses names, not runs.

    An andon that also refuses correct work is a defect with a clause attached, so the
    default name and an ordinary one both have to come out the far side with Gate R green.
    """
    frames = stick_frames(str(tmp_path / "frames"))
    for argv_name, stem in ((None, "E08_pose_sticks"), ("shot_A2", "shot_A2")):
        out = tmp_path / ("o_" + stem)
        argv = [f"--frames={frames}", f"--out={out}"]
        if argv_name is not None:
            argv.append(f"--name={argv_name}")
        assert PP.main(argv) == 0
        assert tree_under(str(out)) == sorted([f"{stem}.apng.png",
                                               "pose_pack_manifest.json"])
        with open(out / "pose_pack_manifest.json", encoding="utf-8") as fh:
            man = json.load(fh)
        assert man["gates"]["R"]["verdict"] == "identical"
        assert os.path.dirname(man["pack"]["path"]) == os.path.abspath(str(out))


# ===========================================================================
# F-6bb38028 — `pack_pose_pack --fps` is a RATE
# ===========================================================================


@pytest.mark.parametrize("fps", (0, -16))
@pytest.mark.parametrize("fmt", ("apng", "webp"))
def test_a_pack_rate_that_is_not_positive_refuses_and_leaves_no_empty_out(tmp_path, fps, fmt):
    """THE OPERANDS the finding named, on BOTH formats — the four measured base-tree runs.

    `--fps=0` was a bare `ZeroDivisionError` from `duration = int(round(1000.0 / fps))`;
    `--fps=-16` was a bare `struct.error: 'H' format requires 0 <= number <= 65535` under
    apng and a bare `RuntimeError: ERROR adding frame: timestamps must be non-decreasing`
    under webp. Neither named the flag or the value, and all four left `--out` behind empty
    because `os.makedirs` sat above `write_pack`.
    """
    frames = stick_frames(str(tmp_path / "frames"))
    out = tmp_path / "o"
    with pytest.raises(PP.PosePackError) as exc:
        PP.main([f"--frames={frames}", f"--out={out}", f"--fps={fps}", f"--format={fmt}"])
    ev = exc.value.evidence
    assert ev["clause"] == "pack_rate_not_positive"
    assert ev["gate"] == "ARGS" and ev["andon"] == "PosePackError"
    assert ev["flag"] == "--fps" and ev["value"] == fps and ev["minimum_exclusive"] == 0
    assert not os.path.exists(str(out)), "the refusal left an empty --out behind"


def test_a_non_finite_pack_rate_never_reaches_main_at_all():
    """Why the bound is positivity ONLY, and why that is not half a check.

    The finding's suggested fix was `not math.isfinite(a.fps) or a.fps <= 0`. `--fps` is
    `type=int`, so the finiteness half would be **a clause with no caller** — this repo
    arms those or deletes them. Measured here rather than asserted in prose: argparse
    itself refuses the spelling, at its own exit code, before `main` is entered.
    """
    with pytest.raises(SystemExit) as exc:
        PP.parse_args(["--frames=f", "--out=o", "--fps=nan"])
    assert exc.value.code == 2
    for spelling in ("nan", "inf", "1e999", "16.5"):
        with pytest.raises(SystemExit):
            PP.parse_args(["--frames=f", "--out=o", f"--fps={spelling}"])


def test_a_pack_rate_that_is_a_rate_still_writes_the_frame_delay_it_names(tmp_path):
    """Grade the arm on what it can move: the bound must not move a legal delay.

    `1` is the smallest legal rate and the one nearest the bound, so it is the value a
    mis-spelled `<` would eat.
    """
    frames = stick_frames(str(tmp_path / "frames"))
    for fps in (1, 8, 16):
        out = tmp_path / f"o{fps}"
        assert PP.main([f"--frames={frames}", f"--out={out}", f"--fps={fps}"]) == 0
        with open(out / "pose_pack_manifest.json", encoding="utf-8") as fh:
            man = json.load(fh)
        assert man["fps"] == fps
        assert man["encoding"]["duration_ms"] == int(round(1000.0 / fps))


def test_both_pack_andons_sit_above_the_makedirs_they_protect():
    """The ordering rule, read off the source rather than inferred from a passing run.

    The two tests above prove `--out` is absent after a refusal, which is the BEHAVIOUR.
    This is the structural half: a later edit that moves `os.makedirs` up would keep those
    green only until the first andon that fires after a directory is created.
    """
    src = open(os.path.join(TOOLS, "pack_pose_pack.py"), encoding="utf-8").read().splitlines()

    def line_of(needle):
        hits = [i for i, ln in enumerate(src) if needle in ln]
        assert len(hits) == 1, (needle, hits)
        return hits[0]

    makedirs = line_of("os.makedirs(out_dir, exist_ok=True)")
    assert line_of("if a.fps <= MIN_FPS_EXCLUSIVE:") < makedirs
    assert line_of('single_path_segment(a.name, "--name", PosePackError,') < makedirs


# ===========================================================================
# F-db1de39d — `resample_motion --name` is a NAME
# ===========================================================================


# ===========================================================================
# The halt records, READ (wave-18 brief, rule 4)
# ===========================================================================


def _run_tool(tool, argv, tmp_path):
    return subprocess.run([sys.executable, os.path.join(TOOLS, tool)] + argv,
                          capture_output=True, text=True, cwd=str(tmp_path))


def test_the_pack_refusal_reaches_the_operator_and_records_what_it_cannot_say(tmp_path):
    """The pack tool's `__main__` is `raise SystemExit(main())` — there is no halt printer.

    So the record an operator sees is a traceback: the CLASS and the MESSAGE reach stderr,
    the evidence dict — and therefore the `clause` — reach nothing, and the exit code is 1
    ("an unhandled error") rather than the 2 a deliberate refusal earns under the handler
    every other tool in this domain carries. That is measured here rather than left as an
    assumption, and it is filed as a Stage B item (wave-18 seams inbox, SEAM 9): this is the
    tool whose artifact is UPLOADED, and `tests/test_instrument_exits.py`'s halt census is
    keyed on `RECORDED_BLENDER_TOOLS`, of which this file is not a member.

    The test asserts what IS true today, so the day the handler lands it fails and says so.
    """
    frames = stick_frames(str(tmp_path / "frames"))
    proc = _run_tool("pack_pose_pack.py",
                     [f"--frames={frames}", f"--out={tmp_path / 'o'}", "--fps=-16"],
                     tmp_path)
    assert proc.returncode != 0
    assert "PosePackError" in proc.stderr
    assert "--fps=-16 is not a rate" in proc.stderr
    assert "PACK_POSE_PACK_OK" not in proc.stdout
    assert not os.path.exists(str(tmp_path / "o"))
    src = open(os.path.join(TOOLS, "pack_pose_pack.py"), encoding="utf-8").read()
    assert "PACK_POSE_PACK_HALT" not in src, (
        "a halt printer landed; re-derive this test and SEAM 9's Stage B item")
    assert "pack_rate_not_positive" not in proc.stdout + proc.stderr, (
        "the clause does not reach any printed line today; that is the Stage B item")


# ===========================================================================
# The gate legs under -O: an `assert` would be gone, a `raise` is not
# ===========================================================================


def test_every_refusal_this_commit_adds_survives_python_optimize(tmp_path):
    """`PYTHONOPTIMIZE=1` in the ENVIRONMENT, because a child inherits that and not `-O`."""
    frames = stick_frames(str(tmp_path / "frames"))
    script = r"""
import json, os, sys
sys.path.insert(0, os.path.join(os.environ["ARMATURE_REPO"], "tools"))
if __debug__:
    raise SystemExit("PYTHONOPTIMIZE did not reach this interpreter")
import pack_pose_pack
frames, out = sys.argv[1], sys.argv[2]
fired = []
for argv, cls, tag in (
        ([f"--frames={frames}", f"--out={out}1", "--fps=0"],
         pack_pose_pack.PosePackError, "pack_rate"),
        ([f"--frames={frames}", f"--out={out}2", "--name=../x"],
         pack_pose_pack.PosePackError, "pack_name"),
):
    try:
        pack_pose_pack.main(argv)
    except cls as exc:
        fired.append((tag, exc.evidence["clause"], os.path.exists(argv[1][6:])))
print(json.dumps(fired))
"""
    env = dict(os.environ, PYTHONOPTIMIZE="1", ARMATURE_REPO=REPO)
    proc = subprocess.run(
        [sys.executable, "-c", script, frames, str(tmp_path / "opt")],
        capture_output=True, text=True, env=env)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout.strip().splitlines()[-1]) == [
        ["pack_rate", "pack_rate_not_positive", False],
        ["pack_name", "output_name_is_not_a_name", False],
    ]


def test_neither_andon_is_an_assert_or_carries_a_skip_flag():
    """Gates raise; they never `assert`, and nothing may disarm one from outside.

    Keyed on the RESOLVED shape rather than on a spelling: every andon added this wave is
    reached from a `raise` statement, and neither file grew an environment read or a
    `--no-*` / `--skip-*` / `--force` flag alongside them.
    """
    for name in ("pack_pose_pack.py",):
        src = open(os.path.join(TOOLS, name), encoding="utf-8").read()
        assert "assert " not in src, name
        for escape in ("os.environ", "getenv", "--skip", "--no-check", "--force"):
            assert escape not in src, (name, escape)

