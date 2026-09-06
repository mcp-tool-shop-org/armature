"""WAVE-28 MERGE FIX-UP (coordinator, 2026-09-06) — the two halves that could only land on the merged tree.

1. `channels.*` `extra=` (core-solvers, F-98b9b966) is adopted by `stage_render.run_export` (instruments-measure's
   half, F-3dc24905 / the seed's neighbour): every `ch.<fn>(...)` call inside `run_export` passes
   `extra={"frame": i, ...}` with a `channel` key, and every one that writes a file names its `path`. instruments-measure
   could not land this on its base — the signature lived on core-solvers' branch (SEAM 15 §A) — so the coordinator applied
   the call-site table after the merge. This census reads the CALLS by AST, so a call added without `extra=` fails here by
   name rather than reaching an operator as a refusal with no frame.
2. The wait shape has ONE spelling on the merged tree (coordinator SEAM 8): builders' fetch lines and clause word were
   aligned to instruments-measure's in the fix-up; the census below reads both tools' clause words and refuses a second
   spelling of the same mechanism.
"""
import ast
import os
import re

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(HERE, "..", "tools")


def _source(name):
    with open(os.path.join(TOOLS, name), encoding="utf-8") as fh:
        return fh.read()


def _run_export_channel_calls(src):
    """Every `ch.<fn>(...)` Call node inside `run_export`, with the keyword names it passes."""
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "run_export")
    calls = []
    for node in ast.walk(fn):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "ch"):
            kws = {k.arg: k.value for k in node.keywords}
            calls.append((node.func.attr, node.lineno, kws))
    return calls


CHANNEL_FUNCTIONS_THAT_REFUSE = {"depth_extent", "normalize_depth", "encode_u8", "encode_normal", "derive_edge"}


def _extra_keys(value):
    assert isinstance(value, ast.Dict), ast.dump(value)
    return {k.value for k in value.keys if isinstance(k, ast.Constant)}


def test_every_channel_call_in_run_export_hands_the_refusal_its_frame_and_channel():
    calls = [c for c in _run_export_channel_calls(_source("stage_render.py"))
             if c[0] in CHANNEL_FUNCTIONS_THAT_REFUSE]
    assert len(calls) >= 8, [(f, ln) for f, ln, _ in calls]      # measured 8 on the merged tree; more is fine
    missing = [(f, ln) for f, ln, kws in calls if "extra" not in kws]
    assert missing == [], missing
    for f, ln, kws in calls:
        keys = _extra_keys(kws["extra"])
        assert {"frame", "channel"} <= keys, (f, ln, keys)
        if f != "depth_extent":                                   # the one call that writes nothing names no path
            assert "path" in keys, (f, ln, keys)


def test_the_channel_call_census_goes_red_on_a_call_without_extra():
    src = _source("stage_render.py")
    stripped = re.sub(r'ch\.encode_u8\(d_pf, extra=\{[^}]*\}\)', 'ch.encode_u8(d_pf)', src, count=1)
    assert stripped != src
    calls = [c for c in _run_export_channel_calls(stripped) if c[0] in CHANNEL_FUNCTIONS_THAT_REFUSE]
    assert any("extra" not in kws for _, _, kws in calls)


def test_the_channel_refusal_carries_the_callers_frame_path_and_channel():
    """The runtime half: a refusal raised through the adopted signature carries the caller's keys in evidence."""
    import numpy as np
    import armature_core.channels as ch
    bad = np.array([[np.nan]], dtype=np.float32)       # non-finite input — the shape `encode_u8` refuses (`non_finite_encoder_input`)
    with pytest.raises(Exception) as excinfo:
        ch.encode_u8(bad, extra={"frame": 12, "path": "out/depth_perframe/0012.png", "channel": "depth_perframe"})
    ev = getattr(excinfo.value, "evidence", None)
    assert isinstance(ev, dict), excinfo.value
    assert ev.get("frame") == 12 and ev.get("channel") == "depth_perframe", ev
    assert ev.get("path") == "out/depth_perframe/0012.png", ev
    assert "[frame=12" in str(excinfo.value), str(excinfo.value)


TIME_BOUND_CLAUSES = {"fetch_run.py": "downloader_exceeded_the_time_bound",
                      "encode_control.py": "ffmpeg_exceeded_the_time_bound"}


def test_the_wait_shape_has_one_clause_family_across_both_domains():
    for name, clause in TIME_BOUND_CLAUSES.items():
        src = _source(name)
        assert clause in src, (name, clause)
        assert "_timed_out" not in src, (name, "a second spelling of the time-bound clause")
    words = set()
    for name in ("fetch_run.py", "encode_control.py", "extract_clip_frames.py", "stage_render.py"):
        words |= set(re.findall(r'"([a-z_]+_exceeded_the_time_bound)"', _source(name)))
    assert words == {"downloader_exceeded_the_time_bound", "ffmpeg_exceeded_the_time_bound"}, words


OVERWRITE_SENTENCE = "on disk from an earlier run; this run would replace what is there. "
OVERWRITE_SENTENCE_HOMES = ("build_assembly_payload.py", "render_turnaround.py", "render_start_frame.py", "preview_glb.py")


def test_the_overwrite_refusal_has_one_sentence_across_both_domains():
    """SEAM 11's colon form is the one string (SEAM 12); builders' first wording was aligned after the jury."""
    for name in OVERWRITE_SENTENCE_HOMES:
        src = _source(name)
        assert OVERWRITE_SENTENCE in src, name
        assert "already exists from an earlier run" not in src, (name, "a second spelling of the overwrite sentence")


def test_the_fetch_progress_line_is_the_lowercase_stderr_form():
    src = _source("fetch_run.py")
    assert "fetch_run download 0/" in src and "fetch_run download {len(planned)}/{len(planned)}" in src
    assert "[fetch]" not in src
