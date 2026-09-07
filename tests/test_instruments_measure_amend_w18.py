"""Wave 18, instruments-measure: the two flags the UPLOADED pack is written from.

Three findings, one family and one bound:

* **F-6bb38028** — `pack_pose_pack --fps` divides in `write_pack` and in the manifest, and
  was unbounded. On the base tree `--fps=0` died with a bare `ZeroDivisionError` and
  `--fps=-16` with a bare `struct.error` / `RuntimeError`, in all four cases AFTER
  `os.makedirs` had created `--out` and left it behind empty.
* **F-62dec63b** — `pack_pose_pack --name` was pasted into the output path with no check
  that it names one path component. `--name=../escaped` printed `PACK_POSE_PACK_OK` with
  `"gate_R": "identical"`, exited 0, and put the pack one directory ABOVE the manifest that
  certifies it.
* **F-db1de39d** — `resample_motion --name`, the same paste, the same escape.

**The rule this file is written to (wave-18 brief, rule 2): a fix's red proof runs against
its SIBLINGS.** So the operand each finding named is proven red, and so is every neighbour
of it in the same parser and the same family: both pack formats, both signs of the rate,
both path separators on either platform, the two dot names, an absolute path, an empty
name — and the ONE spelling that must stay legal, `resample_motion --name=` falling back to
its derived stem. The population these two tools sit in (every `--name`/`--out`/rate flag
pasted into a path or divided by, across the domain's 42 instruments) is enumerated in the
wave-18 seams inbox, SEAM 10; three of it are fixed, `make_review_clip --run` and
`make_ab_clip --a-fps/--b-fps` are DEFERRED Stage B items and are deliberately untouched.

Everything here drives the tools the way a caller does — `main(argv)` in-process for the
refusals, a real subprocess for the halt records — because the property under test is what
lands on disk and what the operator reads, not what a function returns.
"""

import ast
import json
import os
import subprocess
import sys

import numpy as np
import pytest
from PIL import Image

from conftest import REPO, TOOLS  # noqa: F401

import pack_pose_pack as PP
import resample_motion as RM
from armature_core import sitelist


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


def motion_record(path, n=4):
    """A record that passes every gate above the write, so only the flag can refuse it.

    Every registered bone carries a rotation, because `lift_solve.validate_motion_record`
    refuses a frame that leaves one out — and a fixture that dies on THAT andon would prove
    nothing about the flag this file is here for.
    """
    def rot(t):
        import math
        c, s = math.cos(t), math.sin(t)
        return [[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]]

    frames = [{"frame": i,
               "local": {b: rot((i + k) * 0.01) for k, b in enumerate(sitelist.ALL_NAMES)},
               "root": [0.0, 0.0, float(i) * 0.01]}
              for i in range(n)]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"tool": "fixture", "tool_version": "w18", "frames": frames,
                   "source": "fixture", "ema_alpha": None}, fh)
    return path


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
    src = open(os.path.join(TOOLS, "pack_pose_pack.py"), encoding="utf-8").read()
    lines = src.splitlines()
    tree = ast.parse(src)
    main_fn = next(n for n in tree.body
                   if isinstance(n, ast.FunctionDef) and n.name == "main")

    def line_of(needle):
        hits = [i for i, ln in enumerate(lines) if needle in ln]
        assert len(hits) == 1, (needle, hits)
        return hits[0]

    # WAVE 37: from_motion_pipeline also makedirs out_dir (helper HELPER_BOTH). The
    # andons this pin guards live in main and must sit above main's makedirs.
    main_makedirs = sorted(
        n.lineno - 1 for n in ast.walk(main_fn)
        if isinstance(n, ast.Call) and ast.unparse(n.func) == "os.makedirs")
    assert len(main_makedirs) == 1, main_makedirs
    makedirs = main_makedirs[0]
    assert line_of("if a.fps <= MIN_FPS_EXCLUSIVE:") < makedirs
    assert line_of('single_path_segment(a.name, "--name", PosePackError,') < makedirs


# ===========================================================================
# F-db1de39d — `resample_motion --name` is a NAME
# ===========================================================================


def test_a_resample_name_that_escapes_out_refuses_and_writes_nothing(tmp_path):
    """THE OPERAND the finding named.

    On the base tree this call printed `RESAMPLE_MOTION_OK` with
    `"out": "<out>/inner/../escaped.motion.json"`, returned 0, and left the record one
    directory above the `--out` `os.makedirs` had just created and left empty. `_sha256`
    still hashed the file that was written, so the receipt was right about the bytes and
    wrong about the place.
    """
    motion = motion_record(str(tmp_path / "src" / "motion.json"))
    root = tmp_path / "o"
    with pytest.raises(RM.ResampleArgError) as exc:
        RM.main([f"--motion={motion}", f"--out={root / 'inner'}", "--frames=6",
                 "--name=../escaped"])
    ev = exc.value.evidence
    assert ev["clause"] == "output_name_is_not_a_name"
    assert ev["gate"] == "ARGS" and ev["andon"] == "ResampleArgError"
    assert ev["flag"] == "--name" and ev["name"] == "../escaped"
    assert tree_under(str(root)) == []


@pytest.mark.parametrize("name", [n for n in NOT_A_NAME if n.strip()])
def test_every_sibling_spelling_refuses_in_resample_too(tmp_path, name):
    """The same family answering with the same word in the second tool.

    The empty and whitespace-only spellings are excluded HERE and only here, because the
    write site reads `a.name or (derived)`: a falsy `--name` never reaches the join, and
    the test below pins that it still resolves to the derived stem.
    """
    motion = motion_record(str(tmp_path / "src" / "motion.json"))
    out = tmp_path / "o" / "inner"
    with pytest.raises(RM.ResampleArgError) as exc:
        RM.main([f"--motion={motion}", f"--out={out}", "--frames=6", f"--name={name}"])
    assert exc.value.evidence["clause"] == "output_name_is_not_a_name"
    assert tree_under(str(tmp_path / "o")) == []


def test_an_absent_or_empty_resample_name_still_falls_back_to_the_derived_stem(tmp_path):
    """The bound is drawn where the value is READ, so a falsy `--name` stays legal.

    Measured on the base tree: `--name=` wrote `motion.6.motion.json`, the derived default.
    Refusing it here would refuse an input this tool accepts, which is how a bound that was
    supposed to catch an escape ends up catching a caller.
    """
    motion = motion_record(str(tmp_path / "src" / "motion.json"))
    for argv_tail, out_name in ((["--name="], "o_empty"), ([], "o_absent")):
        out = tmp_path / out_name
        assert RM.main([f"--motion={motion}", f"--out={out}", "--frames=6"] + argv_tail) == 0
        assert tree_under(str(out)) == ["motion.6.motion.json"]


# ===========================================================================
# The halt records, READ (wave-18 brief, rule 4)
# ===========================================================================


def _run_tool(tool, argv, tmp_path):
    return subprocess.run([sys.executable, os.path.join(TOOLS, tool)] + argv,
                          capture_output=True, text=True, cwd=str(tmp_path))


def test_the_resample_halt_record_names_the_class_the_clause_and_the_operand(tmp_path):
    """Driven through `__main__`, and the printed record is READ, not assumed.

    `resample_motion` has a halt printer, so the whole receipt reaches the operator. On the
    base tree the neighbouring spelling `--name=a/b` printed
    `{"error": "FileNotFoundError", ..., "evidence": null}` — a refused run that read as a
    crash — which is the shape this assertion locks out.
    """
    motion = motion_record(str(tmp_path / "src" / "motion.json"))
    proc = _run_tool("resample_motion.py",
                     [f"--motion={motion}", f"--out={tmp_path / 'o'}", "--frames=6",
                      "--name=a/b"], tmp_path)
    line = [ln for ln in proc.stdout.splitlines() if ln.startswith("RESAMPLE_MOTION_HALT")]
    assert len(line) == 1, proc.stdout
    rec = json.loads(line[0][len("RESAMPLE_MOTION_HALT "):])
    assert rec["error"] == "ResampleArgError"
    assert rec["evidence"]["clause"] == "output_name_is_not_a_name"
    assert rec["evidence"]["flag"] == "--name" and rec["evidence"]["name"] == "a/b"
    assert set(rec["evidence"]) >= {"gate", "andon", "clause", "flag", "name", "tool", "out"}
    assert proc.returncode == 2, "a deliberate refusal is exit 2 under this tool's handler"
    assert tree_under(str(tmp_path / "o")) == []


def test_the_pack_refusal_reaches_the_operator_and_records_what_it_cannot_say(tmp_path):
    """RE-DERIVED WAVE 22 (F-af7f5c42): the Stage B item this test pinned is closed.

    What it asserted until now — and what was true on `e8263a3` — was the ABSENCE of a halt
    printer: `pack_pose_pack.__main__` was a bare `raise SystemExit(main())`, so the record
    an operator saw was a traceback, the evidence dict (and therefore the `clause`) reached
    nothing, and the exit code was 1 ("an unhandled error") rather than the 2 a deliberate
    refusal earns. The test was written to fail on the day the handler landed, and it did.
    This is that re-derivation, asserting the other side of the same property:
    `pack_pose_pack` adopts `armature_core.parts.run_tool_main` (wave-22 SEAM 1, the ONE
    handler with ONE home), so the same refusal now prints one `PACK_POSE_PACK_HALT` line
    carrying the clause and exits 2.
    """
    frames = stick_frames(str(tmp_path / "frames"))
    proc = _run_tool("pack_pose_pack.py",
                     [f"--frames={frames}", f"--out={tmp_path / 'o'}", "--fps=-16"],
                     tmp_path)
    assert proc.returncode == 2, (proc.returncode, proc.stdout[-400:], proc.stderr[-400:])
    assert "PACK_POSE_PACK_OK" not in proc.stdout
    assert not os.path.exists(str(tmp_path / "o"))

    halt = [l for l in proc.stdout.splitlines() if l.startswith("PACK_POSE_PACK_HALT ")]
    assert len(halt) == 1, proc.stdout[-600:]
    rec = json.loads(halt[0][len("PACK_POSE_PACK_HALT "):])
    assert rec["tool"] == "pack_pose_pack", rec
    assert rec["error"] == "PosePackError", rec
    assert "--fps=-16 is not a rate" in rec["message"], rec
    assert rec["evidence"]["clause"] == "pack_rate_not_positive", rec
    assert rec["evidence"]["flag"] == "--fps" and rec["evidence"]["value"] == -16, rec
    assert "REFUSED" in rec["outcome"] or "HALTED" in rec["outcome"], rec


# ===========================================================================
# The gate legs under -O: an `assert` would be gone, a `raise` is not
# ===========================================================================


def test_all_three_refusals_survive_python_optimize(tmp_path):
    """`PYTHONOPTIMIZE=1` in the ENVIRONMENT, because a child inherits that and not `-O`."""
    frames = stick_frames(str(tmp_path / "frames"))
    motion = motion_record(str(tmp_path / "src" / "motion.json"))
    script = r"""
import json, os, sys
sys.path.insert(0, os.path.join(os.environ["ARMATURE_REPO"], "tools"))
if __debug__:
    raise SystemExit("PYTHONOPTIMIZE did not reach this interpreter")
import pack_pose_pack, resample_motion
frames, motion, out = sys.argv[1], sys.argv[2], sys.argv[3]
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
try:
    resample_motion.main([f"--motion={motion}", f"--out={out}3", "--frames=6",
                          "--name=../x"])
except resample_motion.ResampleArgError as exc:
    fired.append(("resample_name", exc.evidence["clause"], os.path.exists(out + "3")))
print(json.dumps(fired))
"""
    env = dict(os.environ, PYTHONOPTIMIZE="1", ARMATURE_REPO=REPO)
    proc = subprocess.run(
        [sys.executable, "-c", script, frames, motion, str(tmp_path / "opt")],
        capture_output=True, text=True, env=env)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout.strip().splitlines()[-1]) == [
        ["pack_rate", "pack_rate_not_positive", False],
        ["pack_name", "output_name_is_not_a_name", False],
        ["resample_name", "output_name_is_not_a_name", False],
    ]


def test_neither_andon_is_an_assert_or_carries_a_skip_flag():
    """Gates raise; they never `assert`, and nothing may disarm one from outside.

    Keyed on the RESOLVED shape rather than on a spelling: every andon added this wave is
    reached from a `raise` statement, and neither file grew an environment read or a
    `--no-*` / `--skip-*` / `--force` flag alongside them.
    """
    for name in ("pack_pose_pack.py", "resample_motion.py"):
        src = open(os.path.join(TOOLS, name), encoding="utf-8").read()
        assert "assert " not in src, name
        for escape in ("os.environ", "getenv", "--skip", "--no-check", "--force"):
            assert escape not in src, (name, escape)


def test_the_two_copies_of_the_name_check_are_one_rule_with_one_word():
    """RE-DERIVED WAVE 22 (SEAM 1): there are no longer two copies, and that is the fix.

    What this test asserted until now was that the two byte-identical spellings of
    `single_path_segment` — one in `pack_pose_pack`, one in `resample_motion` — had not
    DRIFTED: it compared their executable source with every string constant blanked, because
    the single home for the helper is `armature_core`, which was another domain's tree in
    the frozen map, so "the helper lives beside its callers the way `parts.require_finite`
    does" was the best available answer and the drift check was its price.

    Wave 22's SEAM 1 removed the reason: core-solvers put the helper in
    `armature_core.parts` with the same signature, the same argument order, the same clause
    word and the same evidence keys, and this domain DELETED both copies and imports it.
    Two spellings that cannot drift because there is only one is a stronger property than
    two spellings measured not to have drifted, so this test now asserts the stronger one —
    and keeps the clause-word fingerprint, which is what a census reads the family by.

    The MESSAGES the two tools produce are now one message, which is the visible cost of
    the merge: it says the artifact lands away from the manifest that certifies it, in the
    general terms both callers share. The per-tool detail moved into the `extra` evidence
    each call site passes (`tool`, `out`), which is machine-readable where the prose was not.
    """
    import ast

    from armature_core import parts as PARTS

    # There is ONE definition, and it is not in either tool.
    for mod in (PP, RM):
        tree = ast.parse(open(mod.__file__, encoding="utf-8").read())
        assert not [n for n in ast.walk(tree)
                    if isinstance(n, ast.FunctionDef)
                    and n.name == "single_path_segment"], (
            f"{mod.__name__} spells the name check again; SEAM 1's home is "
            f"armature_core.parts")

    # Both tools reach that one definition, and the clause word and evidence keys — the
    # fingerprint a census reads the family by — are unchanged from wave 18.
    for cls in (PP.PosePackError, RM.ResampleArgError):
        with pytest.raises(cls) as exc:
            PARTS.single_path_segment("../x", "--name", cls)
        assert exc.value.evidence == {"gate": "ARGS", "andon": cls.__name__,
                                      "clause": "output_name_is_not_a_name",
                                      "flag": "--name", "name": "../x"}
        assert "--name='../x'" in str(exc.value)


# ===========================================================================
# WAVE 23, F-54179a94 — the pasted-name family, DERIVED rather than typed
# ===========================================================================
#
# This file's own header records the family as a typed three ("three of it are fixed,
# `make_review_clip --run` and `make_ab_clip --a-fps/--b-fps` are DEFERRED"), enumerated
# over one domain's tools. The spend builders carried four more and no test held the
# property for them: measured on `e8263a3`, `build_animate_payload.py:517` joined
# `f"{a.experiment}-probe-animate.api.json"` onto the output directory with `--experiment`
# declared at `:211` with no bound, and `build_camera_i2v_payload`, `build_i2v_payload` and
# `build_t2v_payload` (whose `--tag` help string reads "goes in the written filenames") did
# the same. Wave 22 bounded those four; what was missing is the CENSUS that finds the next
# one — an operator's `--experiment` or `--tag` carrying a separator or `..` writes the
# payload outside the run directory its own record names, so the spend record's `graph.path`
# and the file that exists disagree, or a second run overwrites the first's payload.
#
# The walk has ONE home, `_census_nodes.pasted_name_flags`, and keys on the RESOLVED shape:
# every argparse STRING option whose value reaches a filename composed under the tool's own
# `--out`, unioned with every flag already routed through `single_path_segment` (three
# members are visible only that way). See that function's block comment for the derivation.

import ast                                                          # noqa: E402

from _census_nodes import pasted_name_flags                          # noqa: E402
from blender_stub import load_tool                                   # noqa: E402

#: DERIVED 2026-09-05 on this branch by `pasted_name_flags()`. Equality, so a tenth builder
#: that pastes a flag into its output filename joins this census in the commit that adds it
#: — which is the mechanism wave 18's typed three did not have.
#:
#: Re-derive with the suite interpreter (tests/conftest.py module docstring):
#:     .venv/Scripts/python.exe -c "import sys,json;sys.path.insert(0,'tests');import _census_nodes as C;
#:     print(json.dumps(C.pasted_name_flags(),indent=1))"
RECORDED_PASTED_NAME_FAMILY = {
    "build_animate_payload": {"--experiment": "single_path_segment"},
    "build_camera_i2v_payload": {"--experiment": "single_path_segment"},
    "build_i2v_payload": {"--experiment": "single_path_segment"},
    "build_lora_arm_payload": {"--arm": "choices"},
    "build_r2v_payload": {"--arm": "choices"},
    "build_t2v_payload": {"--tag": "single_path_segment"},
    "fetch_run": {"--run": "single_path_segment"},
    "make_review_clip": {"--run": "single_path_segment"},
    "pack_pose_pack": {"--name": "single_path_segment"},
    "preview_glb": {"--name": "single_path_segment"},
    "render_turnaround": {"--prefix": "single_path_segment"},
    "resample_motion": {"--name": "single_path_segment"},
}


def _family_rows():
    """`[(tool, flag, how it is bounded)]`, flattened, in a stable order."""
    return [(tool, flag, row["bound"])
            for tool, flags in sorted(pasted_name_flags().items())
            for flag, row in sorted(flags.items())]


def test_the_pasted_name_family_is_derived_and_has_not_grown_silently():
    got = {tool: {flag: row["bound"] for flag, row in sorted(flags.items())}
           for tool, flags in sorted(pasted_name_flags().items())}
    assert got == RECORDED_PASTED_NAME_FAMILY, {
        "appeared": sorted(set(got) - set(RECORDED_PASTED_NAME_FAMILY)),
        "vanished": sorted(set(RECORDED_PASTED_NAME_FAMILY) - set(got)),
        "changed": {t: (RECORDED_PASTED_NAME_FAMILY.get(t), got[t])
                    for t in got if RECORDED_PASTED_NAME_FAMILY.get(t) != got[t]},
    }


def test_no_member_of_the_pasted_name_family_is_unbounded():
    """The property, stated separately from the membership.

    The map above could be updated to record a new OPEN member and stay green; this cannot.
    A `None` here is a flag an operator can paste `../..` into.
    """
    open_flags = [(tool, flag) for tool, flag, bound in _family_rows() if bound is None]
    assert open_flags == [], (
        f"these flags are pasted into an output filename with no bound: {open_flags}. "
        f"Route each through `armature_core.parts.single_path_segment`, or declare a "
        f"`choices=` set none of whose members can carry a separator.")


def test_the_walk_finds_a_paste_a_typed_family_list_could_not():
    """The red proof, kept in the tree: a synthetic tool with an unbounded paste.

    Wave 18's rule 2 asks what this looks like if the walk were wrong in the specific way
    it exists to catch — a census that reports a clean tree because it stopped looking. So
    the walk is driven over a module the real tree does not contain, whose `--tag` is
    joined onto its own `--out`, and it must come back OPEN. The sibling beside it pastes
    an INPUT-rooted path and must NOT be reported, because a census that refuses
    everything is not a census.
    """
    offender = ast.parse(
        "import argparse, os\n"
        "def main(argv=None):\n"
        "    ap = argparse.ArgumentParser()\n"
        "    ap.add_argument('--out', required=True)\n"
        "    ap.add_argument('--tag', default='A3')\n"
        "    a = ap.parse_args(argv)\n"
        "    out_dir = os.path.abspath(a.out)\n"
        "    return os.path.join(out_dir, f'{a.tag}.api.json')\n")
    innocent = ast.parse(
        "import argparse, os\n"
        "def main(argv=None):\n"
        "    ap = argparse.ArgumentParser()\n"
        "    ap.add_argument('--out', required=True)\n"
        "    ap.add_argument('--uploads', required=True)\n"
        "    a = ap.parse_args(argv)\n"
        "    return os.path.join(os.path.dirname(a.uploads), 'sibling.json')\n")

    got = pasted_name_flags({"_synthetic_offender": offender,
                             "_synthetic_innocent": innocent})
    assert got == {"_synthetic_offender": {
        "--tag": {"dest": "tag", "lines": [8], "bound": None}}}, got


def _andon_of(tool, flag):
    """The exception class `tool` hands `single_path_segment` for `flag`.

    Read by AST and then RESOLVED in the module's own namespace, so the census exercises
    the object the tool would actually raise rather than a name that happens to match.
    """
    tree = ast.parse(open(os.path.join(TOOLS, f"{tool}.py"), encoding="utf-8").read())
    named = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and len(node.args) >= 3):
            continue
        func = node.func
        called = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        if called != "single_path_segment":
            continue
        if not (isinstance(node.args[1], ast.Constant) and node.args[1].value == flag):
            continue
        named.append(ast.unparse(node.args[2]).split(".")[-1])
    assert len(named) == 1, (tool, flag, named)
    mod = load_tool(f"{tool}.py")
    cls = getattr(mod, named[0], None)
    assert cls is not None and issubclass(cls, Exception), (tool, flag, named[0])
    return cls


HELPER_BOUND = [(t, f) for t, f, b in _family_rows() if b == "single_path_segment"]
CHOICES_BOUND = [(t, f) for t, f, b in _family_rows() if b == "choices"]

#: Both separators, the drive-relative spelling, the two dot names and an absent name —
#: the set `armature_core.parts.single_path_segment`'s own docstring enumerates.
NOT_A_NAME = ["../x", "a/b", "a" + chr(92) + "b", "C:/elsewhere/x", ".", "..", ""]


@pytest.mark.parametrize("bad", NOT_A_NAME)
@pytest.mark.parametrize("tool,flag", HELPER_BOUND,
                         ids=[f"{t}{f}" for t, f in HELPER_BOUND])
def test_single_path_segment_refuses_for_every_member_it_bounds(tool, flag, bad):
    """`single_path_segment` parametrized over the FAMILY's members, not over the two the
    wave-18 fix happened to touch. Each member's own andon class, the one clause word, and
    the flag the operator has to retype, in the evidence."""
    from armature_core.parts import single_path_segment

    cls = _andon_of(tool, flag)
    with pytest.raises(cls) as exc:
        single_path_segment(bad, flag, cls)
    ev = exc.value.evidence
    assert ev["clause"] == "output_name_is_not_a_name", (tool, flag, ev)
    assert ev["flag"] == flag, (tool, flag, ev)
    assert ev["name"] == bad, (tool, flag, ev)
    assert flag in str(exc.value), (tool, flag, str(exc.value))


@pytest.mark.parametrize("tool,flag", CHOICES_BOUND,
                         ids=[f"{t}{f}" for t, f in CHOICES_BOUND])
def test_a_choices_bound_member_declares_only_names(tool, flag):
    """The other bound, checked rather than trusted: `choices=` bounds a pasted name only
    while every literal in it is itself one path component. `--arm` is `('A1', 'A2')` on
    both members today, and a `choices` set that grew a `"a/b"` would be a bound in name
    only."""
    from armature_core.errors import ArmatureError
    from armature_core.parts import single_path_segment

    tree = ast.parse(open(os.path.join(TOOLS, f"{tool}.py"), encoding="utf-8").read())
    declared = None
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call)
                and getattr(node.func, "attr", "") == "add_argument"):
            continue
        if not any(isinstance(a, ast.Constant) and a.value == flag for a in node.args):
            continue
        for kw in node.keywords:
            if kw.arg == "choices":
                try:
                    declared = ast.literal_eval(kw.value)
                except ValueError:                       # a name, e.g. `sorted(ARMS)`
                    mod = load_tool(f"{tool}.py")
                    declared = sorted(eval(ast.unparse(kw.value), vars(mod)))  # noqa: S307
    assert declared, (tool, flag, "no readable `choices=` beside the flag")
    for choice in declared:
        assert single_path_segment(str(choice), flag, ArmatureError) == str(choice), (
            tool, flag, choice)
