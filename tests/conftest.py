import copy
import importlib.util
import os
import sys
import types
from unittest import mock

import pytest

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLENDER = os.environ.get(
    "ARMATURE_BLENDER", r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
)


@pytest.fixture(scope="module")
def rt():
    """`render_turnaround`, imported with Blender stubbed out.

    Written for S04's ortho tests and moved here when S05's pin tests needed the same
    stub — one copy, not two that can drift apart. The module does `import bpy` at the
    top, so the suite cannot import it the ordinary way. The repo's older idiom
    (`test_turnaround.py`, `test_framing.py`) regexes one function out of the source text
    and execs it, which works and silently stops covering anything the regex does not
    reach. Stubbing the two modules Blender owns and importing the real file covers
    `parse_args`, both solves, the manifest's scale record and the module constants at
    once, and it fails loudly if the import surface changes.
    """
    saved = {k: sys.modules.get(k) for k in ("bpy", "mathutils")}
    sys.modules["bpy"] = mock.MagicMock(name="bpy")
    mathutils = types.ModuleType("mathutils")
    mathutils.Vector = lambda v: v
    mathutils.Matrix = mock.MagicMock(name="Matrix")
    sys.modules["mathutils"] = mathutils
    try:
        path = os.path.join(TOOLS, "render_turnaround.py")
        spec = importlib.util.spec_from_file_location("_rt_under_test", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        yield mod
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


# --------------------------------------------------------------- repo-anchored resources

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
UPLOAD_FIXTURES = os.path.join(FIXTURES, "uploads")

#: The upload name maps `build_payload.EXPERIMENTS` names as `outputs/E0x/uploads_*.json`.
#: They are content-addressed server filenames and nothing else — no pixels, ~2.7 KB each —
#: so committing them lets the E02 byte pin and E03's arm comparisons ride every run.
#: Measured 2026-09-03: `bp.build` reads ONLY these maps (the 480x832 control PNGs are read
#: by `_distinct_source_frames`, which returns None when the directory is absent), and both
#: pinned E02 payload hashes reproduce from the maps alone.
UPLOAD_RECORDS = (
    "outputs/E02/uploads_depth_pershot.json",
    "outputs/E02/uploads_depth_pershot_inverted.json",
    "outputs/E02/uploads_reference.json",
    "outputs/E03/uploads_posearc.json",
    "outputs/E03/uploads_static.json",
)


def repo_file(relpath):
    """An absolute path under the repo root for a `outputs/...`-style relative path.

    Skip guards and fixture reads anchor here, never on `os.getcwd()`. A bare relative
    path resolves against whatever directory pytest was invoked from: measured both
    directions on 2026-09-03 — from the repo root a guard read False, and from an
    unrelated scratch directory seeded with the same file name it read True. Thirty-two
    tests, including the whole through-the-builder half of Gate S, were decided by four
    such guards, and the skip reason read as though the repo simply had no run in it.
    """
    return os.path.join(REPO, *str(relpath).split("/"))


def upload_record(relpath):
    """Resolve one upload name map: the real run if this rig has one, else the fixture.

    `outputs/` is gitignored, so on CI and on any clone the fallback is what exists. The
    fixture is a byte copy of the record the run actually submitted, which is why the
    pinned payload hashes still bind against it.
    """
    live = repo_file(relpath)
    if os.path.isfile(live):
        return live
    fixture = os.path.join(UPLOAD_FIXTURES, *str(relpath).split("/")[1:])
    if os.path.isfile(fixture):
        return fixture
    # Neither: hand back the path the caller asked for so its own error names it.
    return live


@pytest.fixture(scope="session", autouse=True)
def _upload_records_are_resolved():
    """Point `build_payload`'s upload paths at a file that exists, wherever pytest ran.

    The builder names them `outputs/E0x/uploads_*.json`, relative to the caller's working
    directory, and `outputs/` is gitignored — so the E02 byte pin, E03's arm comparisons
    and the through-the-builder half of Gate S all skipped on every clone and every CI
    run. They are the tests that stop a refactor silently re-topologising an experiment
    that has already been run and reported, which is precisely the thing that must not
    depend on who happens to have `outputs/` on their rig.

    This rewrites the paths and nothing else: same bytes, same maps, same hashes.
    """
    try:
        import build_payload as bp
    except Exception:  # pragma: no cover - the builder is always importable in this repo
        yield
        return

    saved_map = dict(bp.UPLOAD_MAP)
    saved_experiments = copy.deepcopy(bp.EXPERIMENTS)

    for arm, path in list(bp.UPLOAD_MAP.items()):
        bp.UPLOAD_MAP[arm] = upload_record(path)
    for cfg in bp.EXPERIMENTS.values():
        ref = cfg.get("reference")
        if ref:
            cfg["reference"] = (upload_record(ref[0]), ref[1])
        for arm_cfg in cfg["arms"].values():
            if isinstance(arm_cfg, dict) and arm_cfg.get("uploads"):
                arm_cfg["uploads"] = upload_record(arm_cfg["uploads"])
    try:
        yield
    finally:
        bp.UPLOAD_MAP.clear()
        bp.UPLOAD_MAP.update(saved_map)
        bp.EXPERIMENTS.clear()
        bp.EXPERIMENTS.update(saved_experiments)


# ------------------------------------------------------------------- gate assertions

def gate_failure_subclasses():
    """Every concrete `GateFailure` subclass, however deeply nested.

    Enumerated rather than listed, so a gate added later joins the checks automatically —
    the whole point of the class-wide invariant is that no new andon can opt out of it.
    """
    from armature_core.errors import GateFailure

    seen, out = set(), []
    stack = [GateFailure]
    while stack:
        for sub in stack.pop().__subclasses__():
            if sub in seen:
                continue
            seen.add(sub)
            out.append(sub)
            stack.append(sub)
    return sorted(out, key=lambda c: c.__name__)


def assert_gate(exc, gate_id, **expected_evidence):
    """A raised gate names its andon AND carries the measurement that fired it.

    `armature_core.errors.GateFailure.__init__` is `self.evidence = evidence or {}`, so a
    gate raised with no evidence at all is a well-formed, silent object: the report the
    Director reads names an andon with nothing behind it, and a test asserting on the
    message string stays green through it. Across `tests/` there are hundreds of
    `pytest.raises` sites on gate types and only a handful assert on `.evidence`; this is
    the shared shape that makes emptiness fail loudly.

    Accepts pytest's `ExceptionInfo` or the exception itself. `expected_evidence` is
    checked by containment, never by equality — a gate is free to report MORE than a
    caller asked about (P1 adds `unexpected` beside G2's `missing`), and a test that
    demanded an exact key set would fail on a gate that got better.
    """
    err = getattr(exc, "value", exc)
    assert isinstance(err, Exception), err
    assert err.gate == gate_id, f"raised {type(err).__name__} with gate {err.gate!r}"
    assert isinstance(err.evidence, dict), type(err.evidence)
    assert err.evidence, (
        f"[{gate_id}] {err} carries an EMPTY evidence dict. A gate that reaches a report "
        f"with nothing behind it names an andon and proves nothing; the measurement that "
        f"fired it is the payload."
    )
    for key, want in expected_evidence.items():
        assert key in err.evidence, (
            f"[{gate_id}] evidence has {sorted(err.evidence)}, no {key!r}")
        if want is not ...:
            assert err.evidence[key] == want, (
                f"[{gate_id}] evidence[{key!r}] is {err.evidence[key]!r}, expected {want!r}")
    return err.evidence
