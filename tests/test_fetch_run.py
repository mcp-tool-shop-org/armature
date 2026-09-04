"""Tests for the run fetcher's node map.

The map was a module constant naming E02's tap node ids, which meant pointing the tool at
any later experiment's dump sorted every frame into the fallback branch and printed a
plausible count. E10's closing lesson names the shape — *a tool that names an experiment
in a literal is a tool that will lie the first time it is reused* — and these fixtures
hold the flag that replaced it.
"""

import json
import os
import subprocess

import pytest

from conftest import TOOLS  # noqa: F401
import fetch_run as F


def test_no_map_keeps_the_default_taps():
    """E02, E08 and E10 all call this tool without the flag; their behaviour must not
    move because a later experiment needed a different mapping."""
    assert F.parse_node_map(None) == F.NODE_DIR
    assert F.parse_node_map("") == F.NODE_DIR
    assert F.parse_node_map(None) is not F.NODE_DIR, "callers must not mutate the default"


def test_a_map_replaces_the_taps_it_names():
    assert F.parse_node_map("41=startprobe,71=lossless") == {
        "41": "startprobe", "71": "lossless"}


def test_whitespace_and_trailing_commas_are_tolerated():
    assert F.parse_node_map(" 41 = startprobe , 71 = lossless , ") == {
        "41": "startprobe", "71": "lossless"}


@pytest.mark.parametrize("bad", ["41", "41=a=b", "=lossless", "71=", ","])
def test_a_malformed_map_halts_rather_than_falling_back_to_the_default(bad):
    """The dangerous outcome is not a crash. It is E02's mapping applied silently to
    another experiment's graph: every frame lands in the video branch, the files are
    named after the run, and the printed count looks entirely reasonable.

    Typed as `FetchHalt` in wave 10 (F-af78df0f). It was `SystemExit(<str>)`, which is
    exit code 1 with no sentinel and no evidence dict - the shape this tool reserves for a
    crash - while the identical class of refusal in `plan` raised a typed halt."""
    with pytest.raises(F.FetchHalt) as exc:
        F.parse_node_map(bad)
    assert exc.value.evidence["clause"].startswith("node_map")


# ------------------------------------------------------------------ the fallback branch
#
# Wave 3, F-183c8222 / F-61771e61 / F-dc669dd4. Three defects sat in one place: every
# result whose source node the map does not name was written to ONE path named after the
# run, the downloader's exit code was never inspected, and the manifest path was
# interpolated into a single-quoted PowerShell string.


def _dump(tmp_path, results):
    p = tmp_path / "get_output.json"
    p.write_text(json.dumps({"results": results}), encoding="utf-8")
    return str(p)


def _result(nid, i, ext=".png"):
    return {"source_node_id": nid, "filename": f"{i:064x}{ext}",
            "url": f"https://example.invalid/{i}{ext}"}


@pytest.fixture()
def stub_download(monkeypatch):
    """A downloader that writes one byte per planned output, and records its call."""
    calls = []

    def fake_run(cmd, **kw):
        calls.append({"cmd": list(cmd), "kw": kw})
        env = kw.get("env") or {}
        manifest = env.get("ARMATURE_FETCH_MANIFEST")
        if manifest and os.path.isfile(manifest):
            with open(manifest, encoding="utf-8") as fh:
                for job in json.load(fh):
                    os.makedirs(os.path.dirname(job["out"]), exist_ok=True)
                    with open(job["out"], "wb") as out:
                        out.write(b"\x89PNG")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(F.subprocess, "run", fake_run)
    return calls


def test_no_two_planned_results_ever_share_an_output_path():
    """The measured defect: a 5-frame dump from a graph whose tap is node 71, run without
    --node-map, printed by_node {"71": 5} and left one file. The printed count was the
    PLANNED count; the files had overwritten each other. `plan` is where that is decided,
    so the distinctness is pinned there, on every branch it can take."""
    results = ([_result("302", i) for i in range(3)]
               + [_result("114", i, ".mp4") for i in range(2)])
    jobs, counts = F.plan(results, "base", "r", F.NODE_DIR, F.VIDEO_NODES)
    outs = [o for _, o in jobs]
    assert len(set(outs)) == len(outs) == 5, outs
    assert counts == {"302": 3, "114": 2}


def test_an_unmapped_source_node_raises_fetchhalt_naming_the_node(tmp_path, stub_download):
    dump = _dump(tmp_path, [_result("71", 0)])
    with pytest.raises(F.FetchHalt) as exc:
        F.main([f"--dump={dump}", "--run=r", f"--root={tmp_path / 'runs'}"])
    assert "71" in str(exc.value)
    assert exc.value.evidence["unmapped"] == ["71"]
    assert not (tmp_path / "runs" / "r").exists(), "a halt must leave no run directory"


def test_the_same_dump_passes_once_the_map_names_the_node(tmp_path, stub_download):
    """The mutation that turns the gate green again — proof it is not always-on."""
    dump = _dump(tmp_path, [_result("71", 0), _result("71", 1)])
    root = tmp_path / "runs"
    F.main([f"--dump={dump}", "--run=r", f"--root={root}", "--node-map=71=lossless"])
    got = sorted(os.listdir(root / "r" / "lossless"))
    assert got == ["00000.png", "00001.png"]


def test_the_video_tap_is_indexed_so_two_videos_cannot_overwrite(tmp_path, stub_download):
    dump = _dump(tmp_path, [_result("114", 0, ".mp4"), _result("114", 1, ".mp4")])
    root = tmp_path / "runs"
    F.main([f"--dump={dump}", "--run=r", f"--root={root}"])
    vids = sorted(n for n in os.listdir(root / "r") if n.endswith(".mp4"))
    assert vids == ["r_00000.mp4", "r_00001.mp4"]


def test_a_downloader_that_fails_halts_instead_of_printing_fetch_run(tmp_path, monkeypatch,
                                                                    capsys):
    """Measured on today's tree with subprocess.run stubbed to returncode 1: the tool
    printed FETCH_RUN_OK {"by_node": {...}, "downloaded": {"lossless": 0}} and returned None,
    i.e. exit 0. The planned count was never compared to what landed."""
    monkeypatch.setattr(F.subprocess, "run",
                        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 1, "", "boom"))
    dump = _dump(tmp_path, [_result("302", 0)])
    with pytest.raises(F.FetchHalt) as exc:
        F.main([f"--dump={dump}", "--run=r", f"--root={tmp_path / 'runs'}"])
    assert exc.value.evidence["returncode"] == 1
    assert "FETCH_RUN" not in capsys.readouterr().out


def test_a_download_that_lands_nothing_halts(tmp_path, monkeypatch, capsys):
    """curl runs with --fail-with-body, so an error body lands at the -o path and counts.
    A silent no-op is the other half, and it exits 0 today."""
    monkeypatch.setattr(F.subprocess, "run",
                        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, "", ""))
    dump = _dump(tmp_path, [_result("302", 0), _result("302", 1)])
    with pytest.raises(F.FetchHalt) as exc:
        F.main([f"--dump={dump}", "--run=r", f"--root={tmp_path / 'runs'}"])
    assert exc.value.evidence["planned"] == 2
    assert len(exc.value.evidence["missing"]) == 2
    assert "FETCH_RUN" not in capsys.readouterr().out


def test_a_zero_length_file_halts_even_though_the_count_matches(tmp_path, monkeypatch):
    def fake_run(cmd, **kw):
        env = kw.get("env") or {}
        with open(env["ARMATURE_FETCH_MANIFEST"], encoding="utf-8") as fh:
            for job in json.load(fh):
                os.makedirs(os.path.dirname(job["out"]), exist_ok=True)
                open(job["out"], "wb").close()
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(F.subprocess, "run", fake_run)
    dump = _dump(tmp_path, [_result("302", 0)])
    with pytest.raises(F.FetchHalt) as exc:
        F.main([f"--dump={dump}", "--run=r", f"--root={tmp_path / 'runs'}"])
    assert len(exc.value.evidence["empty"]) == 1


@pytest.mark.parametrize("run_name", ["plain", "r'; echo INJECTED; #", "a b'c"])
def test_the_command_shape_does_not_move_with_the_run_name(tmp_path, stub_download,
                                                           run_name):
    """Measured: --run=\"r'; echo INJECTED; #\" closed the single-quoted literal and the
    remainder became separate PowerShell statements. The manifest path now travels in the
    environment, so the command string is a constant no operator input can reach."""
    dump = _dump(tmp_path, [_result("302", 0)])
    F.main([f"--dump={dump}", f"--run={run_name}", f"--root={tmp_path / 'runs'}"])
    cmd = stub_download[-1]["cmd"]
    assert run_name not in " ".join(cmd)
    assert "ARMATURE_FETCH_MANIFEST" in cmd[-1]
    assert stub_download[-1]["kw"]["env"]["ARMATURE_FETCH_MANIFEST"].endswith("urls.json")


def test_every_command_shape_is_byte_identical_across_run_names(tmp_path, stub_download):
    for name in ("plain", "r'; echo INJECTED; #"):
        dump = _dump(tmp_path, [_result("302", 0)])
        F.main([f"--dump={dump}", f"--run={name}", f"--root={tmp_path / 'runs'}"])
    assert stub_download[0]["cmd"] == stub_download[1]["cmd"]


# ------------------------------------------- the stray-file direction (wave 6, F-28661db4)


def test_a_stale_frame_in_a_mapped_directory_halts_rather_than_being_counted(
        tmp_path, stub_download, capsys):
    """`got[sub] = len(os.listdir(d))` counted the DIRECTORY while `counts` counted the
    PLAN, and nothing compared them. Measured on today's tree: a 3-frame dump fetched into
    a run directory whose `lossless/` already held one stale `00099.png` printed
    FETCH_RUN_OK {"by_node": {"302": 3}, "downloaded": {"lossless": 4}, "gate_FETCH": "3
    planned file(s), all present and non-empty"} — two counts that disagree, side by side,
    in a green receipt. `encode_control` and `invert_frames` build their frame populations
    with a bare listdir over exactly this directory."""
    root = tmp_path / "runs"
    (root / "r" / "lossless").mkdir(parents=True)
    (root / "r" / "lossless" / "00099.png").write_bytes(b"\x89PNG")
    dump = _dump(tmp_path, [_result("302", i) for i in range(3)])
    with pytest.raises(F.FetchHalt) as exc:
        F.main([f"--dump={dump}", "--run=r", f"--root={root}"])
    ev = exc.value.evidence
    assert ev["planned"] == 3
    assert [os.path.basename(p) for p in ev["extra"]] == ["00099.png"]
    assert "FETCH_RUN" not in capsys.readouterr().out


def test_the_printed_download_counts_come_from_the_plan_not_from_the_directory(
        tmp_path, stub_download, capsys):
    """The two numbers in the receipt can no longer disagree, because there is only one."""
    dump = _dump(tmp_path, [_result("302", i) for i in range(3)]
                 + [_result("301", i) for i in range(2)])
    F.main([f"--dump={dump}", "--run=r", f"--root={tmp_path / 'runs'}"])
    line = json.loads(capsys.readouterr().out.split("FETCH_RUN_OK ", 1)[1])
    assert line["by_node"] == {"302": 3, "301": 2}
    assert line["downloaded"] == {"lossless": 3, "batchprobe": 2}


def test_a_clean_run_still_passes_the_stray_clause(tmp_path, stub_download):
    """The mutation that must NOT fire it: nothing in the directory but the plan."""
    dump = _dump(tmp_path, [_result("302", i) for i in range(2)])
    assert F.main([f"--dump={dump}", "--run=r", f"--root={tmp_path / 'runs'}"]) == 0


# ---- the sweep reaches the run ROOT, and matches the way its consumers do (wave 8, F-d85dafd9)


def test_a_stale_video_in_the_run_root_halts(tmp_path, stub_download, capsys):
    """The EXTRA direction swept only the MAPPED subdirectories, and the video tap lands in
    the run ROOT as `<run>_<index><ext>` — the one population this tool still read from the
    directory rather than from the plan. Measured 2026-09-04 by replaying every committed
    `urls.json` plan through `verify_downloads` on this rig's real run directories: all 20
    non-recovered runs under `outputs/**` PASS a re-fetch of their own plan, and three of
    them (`outputs/E02/runs/A0r1`, `.../A1b`, `.../A2`) hold an unplanned
    `*_review_8fps.mp4` in the run root that `main` would print as THIS run's `video` under
    a green gate_FETCH."""
    root = tmp_path / "runs"
    (root / "r").mkdir(parents=True)
    (root / "r" / "someone_elses_review_8fps.mp4").write_bytes(b"\x00\x00\x00 ftyp")
    dump = _dump(tmp_path, [_result("302", i) for i in range(2)])
    with pytest.raises(F.FetchHalt) as exc:
        F.main([f"--dump={dump}", "--run=r", f"--root={root}"])
    ev = exc.value.evidence
    assert [os.path.basename(p) for p in ev["extra"]] == ["someone_elses_review_8fps.mp4"]
    assert "FETCH_RUN" not in capsys.readouterr().out


def test_a_stale_differently_cased_png_in_a_mapped_directory_halts(
        tmp_path, stub_download, capsys):
    """The suffix test was `os.path.splitext(name)[1] not in suffixes` — case SENSITIVE —
    while both frame consumers match case-insensitively (`encode_control.py:126` and
    `invert_frames.py:70` both use `n.lower().endswith('.png')`). Measured with a stubbed
    run directory: a stale `00099.PNG` beside two planned frames gave `extra=[]` and the
    verdict "no unplanned file in 1 swept directory(s)", while the consumers' population
    read `['00000.png', '00001.png', '00099.PNG']`. The andon and its consumers now share
    ONE population rule."""
    root = tmp_path / "runs"
    (root / "r" / "lossless").mkdir(parents=True)
    (root / "r" / "lossless" / "00099.PNG").write_bytes(b"\x89PNG")
    dump = _dump(tmp_path, [_result("302", i) for i in range(2)])
    with pytest.raises(F.FetchHalt) as exc:
        F.main([f"--dump={dump}", "--run=r", f"--root={root}"])
    assert [os.path.basename(p) for p in exc.value.evidence["extra"]] == ["00099.PNG"]
    assert "FETCH_RUN" not in capsys.readouterr().out


def test_the_printed_video_list_comes_from_the_plan_not_from_a_listdir(
        tmp_path, stub_download, capsys):
    """`vids` was a bare `os.listdir(base)` filtered to .mp4/.webm/.mkv — the last
    population in this tool read from the directory instead of the plan, and the reason a
    prior run's video could be reported as this one's."""
    dump = _dump(tmp_path, [_result("302", i) for i in range(2)]
                 + [_result("114", 0, ext=".mp4")])
    F.main([f"--dump={dump}", "--run=r", f"--root={tmp_path / 'runs'}"])
    line = json.loads(capsys.readouterr().out.split("FETCH_RUN_OK ", 1)[1])
    assert line["video"] == ["r_00000.mp4"]


def test_a_clean_run_with_a_video_and_a_manifest_still_passes(tmp_path, stub_download):
    """The mutation that must NOT fire it: the run root carries the PLANNED video and the
    tool's own `urls.json`, and neither is a stray."""
    dump = _dump(tmp_path, [_result("302", i) for i in range(2)]
                 + [_result("114", 0, ext=".mp4")])
    assert F.main([f"--dump={dump}", "--run=r", f"--root={tmp_path / 'runs'}"]) == 0


def test_the_extension_match_is_case_insensitive_at_the_function_level(tmp_path):
    """The unit form of the same clause, so the rule is pinned where it lives."""
    d = tmp_path / "lossless"
    d.mkdir()
    planned = d / "00000.png"
    planned.write_bytes(b"\x89PNG")
    (d / "00099.PNG").write_bytes(b"\x89PNG")
    with pytest.raises(F.FetchHalt) as exc:
        F.verify_downloads([("u", str(planned))], directories=[str(d)])
    assert [os.path.basename(p) for p in exc.value.evidence["extra"]] == ["00099.PNG"]


# =======================================================================================
# wave 10 — the four bare SystemExits (F-af78df0f) and the root sweep's first real inputs
# (F-eff94830)
# =======================================================================================

import subprocess as _subprocess  # noqa: E402
import sys as _sys  # noqa: E402


def _bare_systemexit_sites(path):
    """Every `raise SystemExit(<something that is not a call to main>)` in one module.

    The node this census keys on is the RAISE, not a name pattern: a deliberate refusal
    spelled `SystemExit` is rendered by CPython as a stderr line and exit code 1, which is
    this tool's code for "crashed", and `except SystemExit: raise` in the `__main__` block
    carries it past the handler so no `FETCH_RUN_HALT` line is printed at all.
    `raise SystemExit(main())` is the convention itself and is not a refusal.
    """
    import ast

    out = []
    for node in ast.walk(ast.parse(open(path, encoding="utf-8").read())):
        if not (isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call)
                and isinstance(node.exc.func, ast.Name)
                and node.exc.func.id == "SystemExit"):
            continue
        arg = node.exc.args[0] if node.exc.args else None
        if (isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name)
                and arg.func.id == "main"):
            continue
        out.append(node.lineno)
    return sorted(out)


def test_this_tool_raises_no_bare_SystemExit_as_a_refusal():
    """Four sites (`parse_node_map` x3, `parse_video_nodes` x1) were deliberate halts that
    reached the operator as exit 1 with no sentinel and no evidence, while `plan`'s
    unmapped-node clause in the same file raised `FetchHalt` and reached them as exit 2
    plus `FETCH_RUN_HALT`. The docstrings called all of them halts."""
    assert _bare_systemexit_sites(os.path.join(TOOLS, "fetch_run.py")) == []


def test_the_bare_SystemExit_census_goes_RED_on_a_module_that_has_one(tmp_path):
    fake = tmp_path / "f.py"
    fake.write_text('def g():\n    raise SystemExit("no")\n'
                    'if __name__ == "__main__":\n    raise SystemExit(main())\n',
                    encoding="utf-8")
    assert _bare_systemexit_sites(str(fake)) == [2]


@pytest.mark.parametrize("text,clause", [
    ("bogus", "node_map_entry_shape"),
    ("41=a=b", "node_map_entry_shape"),
    ("=lossless", "node_map_entry_empty_side"),
    (",,", "node_map_empty"),
])
def test_a_malformed_node_map_raises_FetchHalt_with_the_entry_that_broke_it(text, clause):
    with pytest.raises(F.FetchHalt) as exc:
        F.parse_node_map(text)
    assert exc.value.evidence["clause"] == clause
    assert exc.value.evidence["text"] == text
    assert exc.value.evidence, "a refusal with no evidence dict is not a receipt"


def test_an_empty_video_node_list_raises_FetchHalt_with_evidence():
    with pytest.raises(F.FetchHalt) as exc:
        F.parse_video_nodes(",")
    assert exc.value.evidence["clause"] == "video_nodes_empty"


def test_a_wellformed_map_and_node_list_still_parse():
    """The mutation that must NOT fire the clauses."""
    assert F.parse_node_map("41=startprobe,71=lossless") == {
        "41": "startprobe", "71": "lossless"}
    assert F.parse_video_nodes("114,115") == ("114", "115")
    assert F.parse_video_nodes("none") == ()


def test_a_malformed_map_exits_2_with_exactly_one_FETCH_RUN_HALT_line(tmp_path):
    """The behavioural half. Measured before the fix: `--node-map=bogus` printed the
    refusal sentence on stderr and exited **1**, with no sentinel anywhere."""
    repo = os.path.dirname(TOOLS)
    env = dict(os.environ, PYTHONPATH=TOOLS)
    proc = _subprocess.run(
        [_sys.executable, os.path.join(TOOLS, "fetch_run.py"),
         f"--dump={tmp_path / 'nothing.json'}", "--run=r", "--node-map=bogus",
         f"--root={tmp_path / 'runs'}"],
        capture_output=True, text=True, env=env, cwd=repo)
    assert proc.returncode == 2, proc.stdout + proc.stderr
    halts = [ln for ln in proc.stdout.splitlines() if ln.startswith("FETCH_RUN_HALT ")]
    assert len(halts) == 1, proc.stdout
    payload = json.loads(halts[0][len("FETCH_RUN_HALT "):])
    assert payload["error"] == "FetchHalt"
    assert payload["evidence"]["clause"] == "node_map_entry_shape"
    assert not (tmp_path / "runs").exists()


# ---- the root sweep's exemption (F-eff94830)


def _landed_run(tmp_path, run="A0r1", extra_root_files=()):
    """A run directory holding exactly what a two-frame plan planned, plus strays."""
    base = tmp_path / run
    (base / "lossless").mkdir(parents=True)
    jobs = []
    for i in range(2):
        out = base / "lossless" / f"{i:05d}.png"
        out.write_bytes(b"png")
        jobs.append((f"http://x/{i}", str(out)))
    vid = base / f"{run}_00000.mp4"
    vid.write_bytes(b"mp4")
    jobs.append((f"http://x/v", str(vid)))
    for name in extra_root_files:
        (base / name).write_bytes(b"stray")
    return base, jobs


def test_a_derived_review_clip_of_THIS_run_does_not_halt_the_root_sweep(tmp_path):
    """Wave 8's root sweep refuses runs whose only unplanned root file is an artifact this
    pipeline itself produced. Measured read-only against the rig's real run directories by
    replaying each committed `urls.json` plan: 17 of 20 non-recovered runs PASS and three
    raise with missing=0, empty=0 and extra=['<run>_review_8fps.mp4']. The documented way
    past that andon is deleting a derived file, which is how an operator learns to work
    around an andon."""
    base, jobs = _landed_run(tmp_path, extra_root_files=("A0r1_review_8fps.mp4",))
    ev = F.verify_downloads(
        jobs, directories=[str(base / "lossless")], root=str(base),
        root_exempt=F.derived_root_artifacts("A0r1"))
    assert ev["extra"] == []
    assert [os.path.basename(p) for p in ev["root_exempt_matched"]] == [
        "A0r1_review_8fps.mp4"], ev["root_exempt_matched"]
    assert "tolerated by name" in ev["verdict"], ev["verdict"]


def test_the_current_canonical_review_clip_name_is_also_tolerated(tmp_path):
    """`make_review_clip.clip_name` writes `review_<rate>x_<fps>fps.webp`. It is a `.webp`
    and so never reaches a sweep for VIDEO_SUFFIXES today — the pattern is carried so the
    exemption survives a change of suffix rather than depending on one."""
    import make_review_clip

    name = make_review_clip.clip_name(8, 16)
    assert name == "review_0.50x_8fps.webp"
    patterns = F.derived_root_artifacts("A0r1")
    assert any(rx.match(name) for rx in patterns), name


def test_a_FOREIGN_video_in_the_run_root_still_halts(tmp_path):
    """The mutation that must NOT be tolerated: a file about a generation this fetch is not
    retrieving. The exemption is bound to the run name for exactly this."""
    base, jobs = _landed_run(tmp_path, extra_root_files=("other_run.mp4",))
    with pytest.raises(F.FetchHalt) as exc:
        F.verify_downloads(
            jobs, directories=[str(base / "lossless")], root=str(base),
            root_exempt=F.derived_root_artifacts("A0r1"))
    assert [os.path.basename(p) for p in exc.value.evidence["extra"]] == ["other_run.mp4"]


def test_ANOTHER_runs_review_clip_still_halts(tmp_path):
    """`A2_review_8fps.mp4` sitting in A0r1's directory is not A0r1's derived artifact."""
    base, jobs = _landed_run(tmp_path, extra_root_files=("A2_review_8fps.mp4",))
    with pytest.raises(F.FetchHalt, match="planned by no job") as exc:
        F.verify_downloads(
            jobs, directories=[str(base / "lossless")], root=str(base),
            root_exempt=F.derived_root_artifacts("A0r1"))
    assert [os.path.basename(x) for x in exc.value.evidence["extra"]] == [
        "A2_review_8fps.mp4"]


def test_the_exemption_does_not_reach_the_mapped_frame_directories(tmp_path):
    """It is a ROOT exemption. A stray in `lossless/` named like a review clip is still a
    stray, because that directory is the population `encode_control` and `invert_frames`
    read with a bare listdir."""
    base, jobs = _landed_run(tmp_path)
    (base / "lossless" / "A0r1_review_8fps.png").write_bytes(b"stray")
    with pytest.raises(F.FetchHalt, match="planned by no job") as exc:
        F.verify_downloads(
            jobs, directories=[str(base / "lossless")], root=str(base),
            root_exempt=F.derived_root_artifacts("A0r1"))
    assert [os.path.basename(x) for x in exc.value.evidence["extra"]] == [
        "A0r1_review_8fps.png"]


def test_the_exemption_is_empty_by_default_so_a_caller_opts_in(tmp_path):
    """`root_exempt` defaults to (), so a caller that does not name the artifacts it
    tolerates gets the wave-8 behaviour unchanged."""
    base, jobs = _landed_run(tmp_path, extra_root_files=("A0r1_review_8fps.mp4",))
    with pytest.raises(F.FetchHalt, match="planned by no job") as exc:
        F.verify_downloads(jobs, directories=[str(base / "lossless")], root=str(base))
    assert [os.path.basename(x) for x in exc.value.evidence["extra"]] == [
        "A0r1_review_8fps.mp4"]
