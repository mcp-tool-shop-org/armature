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


def _body_for(path):
    """Bytes that satisfy `fetch_run.CONTENT_SIGNATURES` for this path's suffix.

    Wave 18 (F-0124c714). The content clause reaches every planned suffix now, so a fixture
    landing a PNG signature in a `.mp4` is landing something no downloader produces.
    """
    suffix = os.path.splitext(path)[1].lower()
    rules = F.CONTENT_SIGNATURES.get(suffix)
    if rules is None:
        return b"\x00\x01\x02\x03 arbitrary bytes for a suffix with no signature"
    body = bytearray(b"\x00" * 32)
    for offset, magic, _name in rules:
        body[offset:offset + len(magic)] = magic
    return bytes(body)


@pytest.fixture()
def stub_download(monkeypatch):
    """A downloader that lands every planned output, and records its call.

    Wave 12 (F-ef81516f): it writes the full PNG signature rather than four bytes of it,
    and it writes the per-job exit record the real command string now produces. Both are
    corrections to a stand-in that was less honest than the thing it stands in for: the
    real `-Parallel` block cannot report a failed curl through the process code, so the
    record IS the observation, and `--fail-with-body` means the bytes on disk are the
    difference between a frame and an HTTP refusal.

    Wave 18 (F-0124c714), the same correction one suffix further: it wrote `PNG_SIGNATURE`
    into EVERY planned output, `.mp4` taps included, because the content clause read only
    `.png`. The clause reaches the video tap now, so the stand-in lands bytes that match the
    suffix it is landing — a stub that writes a PNG into a `.mp4` was standing in for a
    downloader that never does.
    """
    calls = []

    def fake_run(cmd, **kw):
        calls.append({"cmd": list(cmd), "kw": kw})
        env = kw.get("env") or {}
        manifest = env.get(F.MANIFEST_ENV)
        rows = []
        if manifest and os.path.isfile(manifest):
            with open(manifest, encoding="utf-8") as fh:
                for job in json.load(fh):
                    os.makedirs(os.path.dirname(job["out"]), exist_ok=True)
                    with open(job["out"], "wb") as out:
                        out.write(_body_for(job["out"]))
                    rows.append({"out": job["out"], "url": job["url"], "code": 0,
                                 "message": ""})
        exits = env.get(F.EXITS_ENV)
        if exits:
            with open(exits, "w", encoding="utf-8") as fh:
                json.dump(rows, fh)
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


def _stub_run_claiming_success(landed):
    """A downloader that reports every job as exit 0 and lands `landed(job)` on disk.

    Wave 12 (F-ef81516f): the per-job exit record is now the observation `-Parallel`
    cannot give the process, so a stub that writes NO record halts on that clause and never
    reaches the plan-to-disk one. These two tests are about the plan-to-disk clause, so
    their downloader claims success — which is exactly the case `verify_downloads` exists
    for: curl says 0 and the frames are not there.
    """
    def fake_run(cmd, **kw):
        env = kw.get("env") or {}
        with open(env[F.MANIFEST_ENV], encoding="utf-8") as fh:
            jobs = json.load(fh)
        rows = []
        for job in jobs:
            landed(job)
            rows.append({"out": job["out"], "url": job["url"], "code": 0, "message": ""})
        with open(env[F.EXITS_ENV], "w", encoding="utf-8") as fh:
            json.dump(rows, fh)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    return fake_run


def test_a_download_that_lands_nothing_halts(tmp_path, monkeypatch, capsys):
    """curl runs with --fail-with-body, so an error body lands at the -o path and counts.
    A silent no-op is the other half, and it exits 0 today."""
    monkeypatch.setattr(F.subprocess, "run",
                        _stub_run_claiming_success(lambda job: None))
    dump = _dump(tmp_path, [_result("302", 0), _result("302", 1)])
    with pytest.raises(F.FetchHalt) as exc:
        F.main([f"--dump={dump}", "--run=r", f"--root={tmp_path / 'runs'}"])
    assert exc.value.evidence["planned"] == 2
    assert len(exc.value.evidence["missing"]) == 2
    assert "FETCH_RUN" not in capsys.readouterr().out


def _touch_empty(job):
    os.makedirs(os.path.dirname(job["out"]), exist_ok=True)
    open(job["out"], "wb").close()


def test_a_zero_length_file_halts_even_though_the_count_matches(tmp_path, monkeypatch):
    monkeypatch.setattr(F.subprocess, "run",
                        _stub_run_claiming_success(_touch_empty))
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
        out.write_bytes(F.PNG_SIGNATURE)   # wave 12: a planned .png must BE one
        jobs.append((f"http://x/{i}", str(out)))
    vid = base / f"{run}_00000.mp4"
    # wave 18 (F-0124c714): a planned `.mp4` must BE one, for the same reason the line
    # above says a planned `.png` must — the content clause reaches the video tap now.
    vid.write_bytes(_body_for(str(vid)))
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


# ============================================================ wave 12, F-ef81516f
# **The gate that could not fire.** `download` built
# `$j | ForEach-Object -Parallel { curl.exe … } -ThrottleLimit 12` and then refused on
# `proc.returncode != 0`. A native non-zero exit inside a `-Parallel` runspace does not
# reach the pwsh process code. MEASURED ON THIS RIG, 2026-09-04, not inherited:
#
#     pwsh -NoProfile -Command '$j = @(1,2); $j | ForEach-Object -Parallel
#         { cmd.exe /c "exit 22" } -ThrottleLimit 12'      -> process exit 0
#
# while the sibling `fetch_t2v_run.py`'s `foreach ($x in $j) { … }` shape exits 1 on the
# identical inner command — so the two fetchers' identically-worded gates disagreed about
# whether they could fire at all. This is NOT the closed F-61771e61 ("the returncode is
# never inspected"): the inspection existed and was structurally unreachable.
#
# The backstop did not cover the gap. curl runs with `--fail-with-body`, which WRITES the
# HTTP error body to the `-o` path, and `verify_downloads` bound only presence, zero length
# and unplanned extras: three planned frames replaced by 35-byte
# `{"error":"AccessDenied","code":403}` bodies returned missing=[], empty=[], extra=[] and
# the verdict "3 planned file(s), all present and non-empty". A measurement taken from that
# directory is a measurement of a paid generation that was never retrieved.
#
# The fix makes the failure OBSERVABLE rather than hoping it propagates: each job records
# its own `$LASTEXITCODE` (and curl's message) into a JSON record, and Gate FETCH refuses
# any non-zero — plus refuses a record that does not cover the plan, because a gate whose
# evidence is missing has not run. Measured on this rig with the new shape and
# `cmd.exe /c "exit 22"` in curl's place: process exit 0, exits record
# `[{"out":"a","url":"u1","code":22,"message":"boom"}]`.
#
# family: keyed on BEHAVIOUR — "a downloader whose per-job failure the parent process can
# observe" — via a read of both fetchers' pwsh command strings, not on the word `curl`
# -> 2 sites: fetch_run.download (-Parallel, unobservable) and fetch_t2v_run.download
# (foreach, observable, measured). The second is left as it is and the census below pins
# WHY, so a later switch to -Parallel there cannot be silent.


def _exits_path(base):
    return os.path.join(base, F.EXITS_NAME)


@pytest.fixture()
def stub_parallel_download(monkeypatch):
    """A downloader that behaves the way the measured `-Parallel` shape does.

    Every job fails, every job's exit is recorded, an HTTP error body is written to each
    `-o` path by `--fail-with-body`, and the pwsh process still exits 0.
    """
    def fake_run(cmd, **kw):
        env = kw.get("env") or {}
        with open(env["ARMATURE_FETCH_MANIFEST"], encoding="utf-8") as fh:
            jobs = json.load(fh)
        rows = []
        for job in jobs:
            os.makedirs(os.path.dirname(job["out"]), exist_ok=True)
            with open(job["out"], "wb") as out:
                out.write(b'{"error":"AccessDenied","code":403}')
            rows.append({"out": job["out"], "url": job["url"], "code": 22,
                         "message": "curl: (22) The requested URL returned error: 403"})
        with open(env["ARMATURE_FETCH_EXITS"], "w", encoding="utf-8") as fh:
            json.dump(rows, fh)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(F.subprocess, "run", fake_run)


def test_a_curl_that_failed_inside_the_parallel_block_HALTS(tmp_path, stub_parallel_download):
    """The whole point: every download fails, the process exits 0, and the tool refuses."""
    dump = _dump(tmp_path, [_result("302", i) for i in range(3)])
    with pytest.raises(F.FetchHalt, match=r"exited non-zero") as exc:
        F.main(["--dump", dump, "--run", "r", "--root", str(tmp_path / "runs")])
    ev = exc.value.evidence
    assert ev["clause"] == "downloader_job_exit_nonzero"
    assert [row["code"] for row in ev["failed"]] == [22, 22, 22]
    assert ev["process_returncode"] == 0, (
        "the halt must say that the PROCESS said nothing was wrong")


def test_an_exit_record_that_does_not_cover_the_plan_HALTS(tmp_path, monkeypatch):
    """A gate whose evidence is absent has not run. The old shape's whole failure was that
    nothing observed the jobs, so 'no observation' may not read as success."""
    def fake_run(cmd, **kw):
        env = kw.get("env") or {}
        with open(env["ARMATURE_FETCH_MANIFEST"], encoding="utf-8") as fh:
            jobs = json.load(fh)
        for job in jobs:
            os.makedirs(os.path.dirname(job["out"]), exist_ok=True)
            with open(job["out"], "wb") as out:
                out.write(F.PNG_SIGNATURE)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(F.subprocess, "run", fake_run)
    dump = _dump(tmp_path, [_result("302", i) for i in range(2)])
    with pytest.raises(F.FetchHalt, match=r"recorded no per-job exit") as exc:
        F.main(["--dump", dump, "--run", "r", "--root", str(tmp_path / "runs")])
    assert exc.value.evidence["clause"] == "downloader_exits_unobserved"


def test_an_exit_record_short_of_the_plan_HALTS(tmp_path, monkeypatch):
    """One row per planned job, or the record is not evidence about the plan."""
    def fake_run(cmd, **kw):
        env = kw.get("env") or {}
        with open(env["ARMATURE_FETCH_MANIFEST"], encoding="utf-8") as fh:
            jobs = json.load(fh)
        for job in jobs:
            os.makedirs(os.path.dirname(job["out"]), exist_ok=True)
            with open(job["out"], "wb") as out:
                out.write(F.PNG_SIGNATURE)
        with open(env["ARMATURE_FETCH_EXITS"], "w", encoding="utf-8") as fh:
            json.dump([{"out": jobs[0]["out"], "url": jobs[0]["url"], "code": 0}], fh)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(F.subprocess, "run", fake_run)
    dump = _dump(tmp_path, [_result("302", i) for i in range(3)])
    with pytest.raises(F.FetchHalt, match=r"recorded 1 job exit\(s\) for 3 planned") as exc:
        F.main(["--dump", dump, "--run", "r", "--root", str(tmp_path / "runs")])
    assert exc.value.evidence["clause"] == "downloader_exits_incomplete"


def test_the_downloader_command_asks_each_job_for_its_own_exit(tmp_path, stub_download):
    """The command shape's contract, pinned. Measured on this rig: a native non-zero exit
    inside a `-Parallel` runspace leaves the pwsh process code at 0, so the only way the
    parent can see a failed curl is if each runspace records `$LASTEXITCODE` itself."""
    dump = _dump(tmp_path, [_result("302", 0)])
    F.main(["--dump", dump, "--run", "r", "--root", str(tmp_path / "runs")])
    cmd = stub_download[-1]["cmd"]
    ps = cmd[-1]
    assert "-Parallel" in ps
    assert "$LASTEXITCODE" in ps, (
        "no per-job exit is captured, so a failed curl is invisible to this process")
    assert f"$env:{F.EXITS_ENV}" in ps, "the exits record has nowhere to land"
    assert stub_download[-1]["kw"]["env"][F.EXITS_ENV].endswith(F.EXITS_NAME)


def test_there_is_exactly_ONE_downloader_across_the_two_fetchers():
    """The family census, keyed on WHO BUILDS a downloader command rather than on the word
    `curl`.

    **CORRECTION, wave 14 (F-a3ba416b).** This test used to be
    `test_the_two_fetchers_disagree_about_the_shell_shape_and_the_record_says_why`, and it
    pinned the disagreement on the stated ground that "`fetch_t2v_run`'s `foreach` shape
    DOES propagate a native non-zero exit (measured)". That measurement was of a
    single-job loop. RE-MEASURED ON THIS RIG 2026-09-04 with three jobs: a failure on the
    FIRST leaves the pwsh process at exit 0; the same loop with the failure on the LAST
    exits 1 — a `foreach` loop's process code reflects only the last native command. So the
    sibling's gate could not fire on a mid-loop failure either, and this test was pinning
    the reason the sibling had been left without a per-job record.

    There is one downloader now. The census asserts that only `fetch_run` builds a pwsh
    command at all, and that the interpreter, the `--` terminator and the per-job
    `$LASTEXITCODE` all live in it.
    """
    import ast

    import fetch_t2v_run as T

    builders = {}
    for mod in (F, T):
        src = open(os.path.join(TOOLS, f"{mod.__name__}.py"), encoding="utf-8").read()
        tree = ast.parse(src)
        # every string literal in the module EXCEPT docstrings — a docstring recording the
        # measurement that retired a shape is evidence, not a shape.
        docstrings = {ast.get_docstring(n, clean=False) for n in ast.walk(tree)
                      if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef,
                                        ast.AsyncFunctionDef))}
        literals = [n.value for n in ast.walk(tree)
                    if isinstance(n, ast.Constant) and isinstance(n.value, str)
                    and n.value not in docstrings]
        builders[mod.__name__] = [v for v in literals if "curl.exe" in v]

    assert builders["fetch_t2v_run"] == [], (
        "fetch_t2v_run builds a downloader command again; there is one implementation and "
        "it is fetch_run.download")
    assert builders["fetch_run"], "fetch_run stopped building the downloader command"
    joined = " ".join(builders["fetch_run"])
    assert "-Parallel" in joined
    assert "-- $_.url" in joined, "a url in option position is read by curl as a flag"
    assert "$LASTEXITCODE" in joined, (
        "curl runs in a -Parallel runspace, whose native non-zero exit does not reach the "
        "process code, and no per-job exit is recorded")
    assert T.fetch_download is F.download, "one downloader, not two"


# ------------------------------------------------ the backstop: a body is not a frame


def test_a_planned_png_whose_bytes_are_an_error_body_HALTS(tmp_path, monkeypatch):
    """`--fail-with-body` writes the HTTP error body to the `-o` path, so 'present and
    non-empty' is satisfied by a 35-byte JSON refusal. Measured before this clause:
    missing=[], empty=[], extra=[] and a green verdict."""
    d = tmp_path / "lossless"
    d.mkdir(parents=True)
    jobs = []
    for i in range(3):
        p = d / f"{i:05d}.png"
        p.write_bytes(b'{"error":"AccessDenied","code":403}')
        jobs.append(("https://example.invalid/x", str(p)))
    with pytest.raises(F.FetchHalt, match=r"not the content type the plan asked for") as exc:
        F.verify_downloads(jobs, directories=[str(d)])
    ev = exc.value.evidence
    assert len(ev["wrong_type"]) == 3
    assert ev["wrong_type"][0]["expected"] == "png"
    assert ev["wrong_type"][0]["first_8_bytes"] == b'{"error"'.hex()


def test_a_planned_png_that_IS_a_png_passes_the_content_clause(tmp_path):
    """The mutation that must not fire it."""
    d = tmp_path / "lossless"
    d.mkdir(parents=True)
    jobs = []
    for i in range(2):
        p = d / f"{i:05d}.png"
        p.write_bytes(F.PNG_SIGNATURE + b"IHDR-and-the-rest")
        jobs.append(("https://example.invalid/x", str(p)))
    ev = F.verify_downloads(jobs, directories=[str(d)])
    assert ev["wrong_type"] == []
    assert "all present and non-empty" in ev["verdict"]


def test_the_content_clause_reaches_the_VIDEO_tap_too(tmp_path):
    """⚠ **This test pinned the defect.** Until wave 18 it read
    `test_the_content_clause_only_binds_what_the_plan_NAMED` and asserted that a `.mp4`
    holding `b"not really an mp4 either"` gave `wrong_type == []` and
    `content_checked == {"png": 0}` — "the clause says nothing about suffixes it has no
    signature for". F-0124c714 measured what that bought: a two-job plan whose `.png` was a
    real PNG and whose `E13_00000.mp4` held a 35-byte `--fail-with-body` error body returned
    a full PASS, on the tap that carries the whole product of the generation.

    `fetch_run.CONTENT_SIGNATURES` has a row for `.mp4` now (an `ftyp` box at offset 4), so
    the assertion is inverted rather than deleted, and the receipt states per suffix what it
    checked and what it could not."""
    p = tmp_path / "r_00000.mp4"
    p.write_bytes(b"not really an mp4 either")
    with pytest.raises(F.FetchHalt) as exc:
        F.verify_downloads([("https://example.invalid/x", str(p))], directories=[])
    ev = exc.value.evidence
    assert ev["clause"] == "downloaded_body_is_not_the_planned_type", ev
    assert ev["wrong_type"][0]["expected"] == "mp4", ev
    assert ev["content_checked"][".mp4"] == {"checked": 1, "unjudged": 0}, ev

    good = tmp_path / "r_00001.mp4"
    good.write_bytes(b"\x00\x00\x00\x20ftypisom" + b"\x00" * 16)
    ok = F.verify_downloads([("https://example.invalid/x", str(good))], directories=[])
    assert ok["wrong_type"] == []


# ============================================================ wave 12, F-a72178c2
# `out[nid] = sub` was a last-write-wins assignment with no duplicate clause, in a function
# whose own docstring states the law: "A malformed map must not fall back to the default:
# the caller would get E02's mapping applied to somebody else's graph ... and the only
# symptom would be a directory of files with the wrong names." Measured in this worktree:
# `parse_node_map("301=batchprobe,301=lossless")` returned `{"301": "lossless"}` with no
# halt — the batchprobe half discarded unexamined, a clip's frames landing in a directory
# named for another tap, and every count in the receipt reading right because `got` and
# `vids` are both derived from the plan. The same shape one door over IS refused:
# `gate_saved_graph.link_table` raises on a link id declared twice with different origins,
# on the reasoning that "which one a socket resolves to is an accident of array order".


def test_a_repeated_node_id_in_the_map_HALTS(tmp_path):
    with pytest.raises(F.FetchHalt, match=r"names node 301 twice") as exc:
        F.parse_node_map("301=batchprobe,301=lossless")
    ev = exc.value.evidence
    assert ev["clause"] == "node_map_duplicate_id"
    assert ev["duplicates"] == {"301": ["batchprobe", "lossless"]}


def test_a_node_id_repeated_with_the_SAME_directory_also_HALTS():
    """Idempotence is not the question. The map is an operator's statement about a graph,
    and a statement made twice is a statement one of whose halves was not read."""
    with pytest.raises(F.FetchHalt, match=r"names node 71 twice"):
        F.parse_node_map("41=startprobe,71=lossless,71=lossless")


def test_a_map_naming_each_node_ONCE_still_parses():
    """The mutation that must not fire it."""
    assert F.parse_node_map("41=startprobe,71=lossless") == {
        "41": "startprobe", "71": "lossless"}


def test_the_sibling_clause_this_one_was_derived_from_still_refuses(tmp_path):
    """family: keyed on BEHAVIOUR — a mapping built by assignment in a loop, where a
    repeated key silently keeps the last spelling — across this domain's parsers. Two
    sites: `fetch_run.parse_node_map` (this fix) and `gate_saved_graph.link_table`, which
    already refuses. `fetch_run.parse_video_nodes` builds a SET, where a repeat cannot
    discard anything, so it is not a member."""
    import gate_saved_graph as G
    from armature_core import route_gates as RG

    with pytest.raises(RG.RouteGate, match=r"declares link .* TWICE with different"):
        G.link_table({"links": [[1, "10", 0, "20", 0, "IMAGE"],
                                [1, "11", 0, "20", 0, "IMAGE"]]})


# ============================================================ wave 12, F-4421d98f (this fetcher's half)


def test_an_empty_results_array_is_REFUSED_BY_NAME_here_too(tmp_path):
    """The sibling's clause, one wording, both planners. `fetch_run` reached
    `FileNotFoundError` on `urls.json` one step later than `fetch_t2v_run` reached its
    `IndexError`, for the same reason: the loop that creates the directories never ran."""
    with pytest.raises(F.FetchHalt, match=r"carries no results") as exc:
        F.plan([], str(tmp_path / "runs" / "r"), "r", F.NODE_DIR, F.VIDEO_NODES)
    assert exc.value.evidence["clause"] == "empty_results"


def test_an_empty_dump_leaves_no_run_directory_here_either(tmp_path):
    dump = _dump(tmp_path, [])
    run_root = tmp_path / "runs"
    with pytest.raises(F.FetchHalt, match=r"carries no results"):
        F.main([f"--dump={dump}", "--run=r", f"--root={run_root}"])
    assert not (run_root / "r").exists()
