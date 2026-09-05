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
    """One family, one clause word, two spellings — and the LOGIC must not drift.

    `armature_core` is the single home this helper belongs in and is another domain's tree
    in the frozen map, so it lives beside its callers the way `parts.require_finite` does.
    That is only defensible while the two are the same rule, so this compares the executable
    source with every string constant blanked: the predicate, the evidence dict's keys and
    the control flow must match exactly.

    The MESSAGES deliberately differ — one says the pack lands away from the manifest that
    certifies it, the other says the record lands away from the sentinel line and sha256
    that describe it — because a refusal's job is to tell THIS operator what THIS tool was
    about to do. A comparison that demanded identical prose would be pressure to make both
    messages vaguer, which is the opposite of the point.
    """
    import ast
    import inspect

    class _Blank(ast.NodeTransformer):
        def visit_Constant(self, node):
            if isinstance(node.value, str):
                return ast.copy_location(ast.Constant(value="<str>"), node)
            return node

    def logic(fn):
        node = ast.parse(inspect.getsource(fn).strip()).body[0]
        if (node.body and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)):
            node.body = node.body[1:]
        return ast.dump(ast.fix_missing_locations(_Blank().visit(node)))

    assert logic(PP.single_path_segment) == logic(RM.single_path_segment)

    # The one string that MUST be identical is the clause word, and the evidence keys with
    # it -- that is the fingerprint a census reads the family by.
    for mod, cls in ((PP, PP.PosePackError), (RM, RM.ResampleArgError)):
        with pytest.raises(cls) as exc:
            mod.single_path_segment("../x", "--name", cls)
        assert exc.value.evidence == {"gate": "ARGS", "andon": cls.__name__,
                                      "clause": "output_name_is_not_a_name",
                                      "flag": "--name", "name": "../x"}
        assert "--name='../x'" in str(exc.value)
