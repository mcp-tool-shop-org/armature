"""Wave-16 instruments amend — the POPULATION around each operand, pinned.

The wave-16 rule, in one line: **wave 14's fixes were right one level down and blind one
level up.** A fix that covers the operand and not the population around it is a fix that
the next member of the family walks past. So every fixture here names the whole population
the property must hold over, walks it by derivation rather than by a typed list, and is
proven RED on a member OUTSIDE the subset the old check reached.

Three shapes recur, and each has its own section below:

* **a default that disarms a clause** — `gate_glb_written(before=None)` skipped the
  stale-target clause without a word; `None` / `{}` / a missing key is now a refusal with
  its own clause, and the gate keys on the VALUE, never on the presence of the argument;
* **a clause with no caller** — Gate TURN's pixel clause was armed only by a caller that
  attaches `pixels`, and its only caller attached none;
* **`nan >= nan is False`, fourth sweep** — four instrument sites still compared a
  measured displacement without routing it through the repo's one finiteness helper.

Every fixture was run once with its fix reverted and records `reverted-red: yes/no` in its
own docstring; where a fixture is green with the fix reverted it says so rather than
claiming a proof it does not have.

Helpers in this file **raise**; they never `assert` outside a test body
(`test_gate_survives_optimize.py` polices that, and `ci.yml` runs an `-O` leg).
"""

import ast
import json
import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import blender_stub                                                     # noqa: E402
from blender_stub import blender_stubbed, load_tool, read_source        # noqa: E402
# ONE implementation of the fake armature, not a second copy: `test_sheet_sides` built it
# for `articulated_side` and this file drives the same function with a NaN in it.
from test_sheet_sides import _Arm, _Scene                               # noqa: E402

TOOLS = blender_stub.TOOLS

SIDE_PROBE_BONES = tuple(f"{j}.{s}" for j in ("shoulder", "elbow", "wrist")
                         for s in ("L", "R"))


def _fn_source(filename, name):
    """The source of one top-level function, for a census that must reach a scratch tree."""
    src = read_source(filename)
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(src, node)
    raise LookupError(f"{filename} has no top-level function {name!r}")


# ===================================================== F-8548f859 — the disarming default
#
# THE POPULATION: every call of `rig_character.gate_glb_written`, which is the ONE
# implementation of Gate GLB and is called at nine export sites across seven tools. The
# property is that no argument a caller can get wrong turns a CLAUSE off silently. Wave 14
# removed the keyword DEFAULTS and stopped there; `before` was still read as
# `if (before and before.get("existed") and ...)`, so `None`, `{}` and `{"existed": False}`
# each skipped the stale-target clause and the gate returned a PASS record carrying a byte
# count and a sha256 for a file the process never wrote.
#
# The member OUTSIDE the old walk: the two wave-14 censuses read the SIGNATURE
# (`test_gate_glb_takes_no_default_for_result_or_before`) and the export call's return
# value (`test_every_glb_export_site_captures_the_operator_status_set`), and neither reads
# the `before=` ARGUMENT at any call site. The census below does.


@pytest.fixture(scope="module")
def rigchar():
    return load_tool("rig_character.py")


@pytest.mark.parametrize("before", [None, {}, {"bytes": 4004, "mtime_ns": 1}])
def test_gate_glb_refuses_a_falsy_or_unsnapshotted_before(rigchar, tmp_path, before):
    """RED on the operand: the file this process never wrote.

    Reverted-red: yes. On the wave-14 gate `before=None` and `before={}` each returned
    `{'bytes': 4004, 'sha256': '683d11b6...', 'status': ['FINISHED'], 'verdict': 'the
    rigged GLB is 4,004 bytes on disk'}` over a file written with plain Python in a process
    that had exported nothing. The third arm is a dict that carries the OTHER two snapshot
    fields and not `existed`, which took the same branch for the same reason.

    `{"existed": False, ...}` is deliberately NOT in this list: that is what
    `export_target_snapshot` honestly returns for a path nothing was at, and clause 4 is
    correctly silent on it. The disarm was the absent measurement, not the absent file.
    """
    p = tmp_path / "hero.glb"
    p.write_bytes(b"g" * 4004)
    with pytest.raises(rigchar.GateGlbWritten) as exc:
        rigchar.gate_glb_written(str(p), result={"FINISHED"}, before=before,
                                 what="the rigged GLB")
    assert exc.value.gate == "GLB"
    assert exc.value.evidence["clause"] == "no_pre_export_snapshot"


def test_gate_glb_keys_on_the_value_of_existed_not_on_its_presence(rigchar, tmp_path):
    """The wave-16 rule 3 clause: a key that is PRESENT and not a bool is not a snapshot.

    Reverted-red: yes — `{'existed': None}` was falsy on the wave-14 gate and returned a
    PASS record for the pre-existing file.
    """
    p = tmp_path / "hero.glb"
    p.write_bytes(b"g" * 4004)
    with pytest.raises(rigchar.GateGlbWritten) as exc:
        rigchar.gate_glb_written(str(p), result={"FINISHED"},
                                 before={"existed": None, "bytes": 4004})
    assert exc.value.evidence["clause"] == "no_pre_export_snapshot"


def test_gate_glb_still_passes_a_real_snapshot_of_a_file_this_run_wrote(rigchar, tmp_path):
    """A gate that refuses everything is not a gate. `export_target_snapshot` of an absent
    path is the honest 'nothing was here' record and it still passes."""
    p = tmp_path / "fresh.glb"
    before = rigchar.export_target_snapshot(str(p))
    p.write_bytes(b"glTF" * 3)
    rec = rigchar.gate_glb_written(str(p), result={"FINISHED"}, before=before)
    assert rec["bytes"] == 12
    assert rec["status"] == ["FINISHED"]


def test_the_stale_target_clause_still_fires_and_now_names_itself(rigchar, tmp_path):
    """Clause 4 with a REAL snapshot, which is the population clause 0 protects."""
    p = tmp_path / "hero.glb"
    p.write_bytes(b"glTF" * 100)
    before = rigchar.export_target_snapshot(str(p))
    with pytest.raises(rigchar.GateGlbWritten) as exc:
        rigchar.gate_glb_written(str(p), result={"FINISHED"}, before=before)
    assert exc.value.evidence["clause"] == "stale_target"
    assert "already there" in str(exc.value)


def _glb_gate_call_sites():
    """Every `gate_glb_written(...)` CALL under `tools/`, by AST — the population.

    Derived, never typed: an export site added tomorrow joins this census the day it lands.
    Returns `(filename, lineno, keywords)` per call.
    """
    out = []
    for fn in sorted(os.listdir(TOOLS)):
        if not fn.endswith(".py"):
            continue
        src = read_source(fn)
        for node in ast.walk(ast.parse(src)):
            if not isinstance(node, ast.Call):
                continue
            f = node.func
            name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
            if name != "gate_glb_written":
                continue
            out.append((fn, node.lineno, {kw.arg for kw in node.keywords if kw.arg}))
    return out


def test_every_gate_glb_call_site_passes_a_pre_export_snapshot():
    """The POPULATION, one level up from the signature the wave-14 census read.

    Reverted-red: n/a — this census is green on the base tree too (no live caller passes a
    falsy `before`), and it says so rather than claiming a proof it does not have. Its job
    is the tenth export site: the finding was filed before that site is written, and this
    is the check that refuses it on the day it lands.
    """
    sites = _glb_gate_call_sites()
    assert len(sites) >= 9, sites
    missing = [(fn, ln) for fn, ln, kws in sites if "before" not in kws or "result" not in kws]
    assert missing == [], missing


def test_the_stale_target_guard_does_not_test_before_for_truthiness():
    """The hidden spelling, read out of the source: `if before and before.get(...)` is the
    defect itself, and a fix that leaves it in place has not moved the population.

    Reverted-red: yes — the wave-14 source carries `if (before and before.get("existed")`.
    """
    src = read_source("rig_character.py")
    tree = ast.parse(src)
    fn = next(n for n in tree.body
              if isinstance(n, ast.FunctionDef) and n.name == "gate_glb_written")
    for node in ast.walk(fn):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And):
            names = [v.id for v in node.values if isinstance(v, ast.Name)]
            assert "before" not in names, (
                "`before` is tested for truthiness inside a boolean guard again; a falsy "
                "snapshot must reach its own refusal, not skip a clause")


# ===================================================== rule 5 — the tool-local constructor


def _refusal_classes(sources):
    """`where:line:name` for every REFUSAL class in `sources` that defines an `__init__`.

    `sources` is `(where, source text)` pairs, so the same derivation can be pointed at a
    SCRATCH tree carrying a defective member — the shape wave 12 asked for the hidden
    spelling, applied to the hidden member.

    The population is not "every class in the file": `stage_render.BlenderBackend` is a
    backend and `sheet_compose._UnreadablePath` is a sentinel, and neither is in the
    `ArmatureError` family. Membership resolves through the file's OWN class table seeded
    with `armature_core.errors`' names, so a class two hops down a local chain is still
    found — and the `GateFailure` subtree is excluded, because `GateFailure` is the
    contract's one exemption (its clauses index into `ev` while they measure).
    """
    for where, src in sources:
        gate_rooted = {"GateFailure"}
        family = {"ArmatureError", "SpecError", "SubjectExtentError", "LandmarkError",
                  "NotInsideBlender"}
        table = {n.name: n for n in ast.walk(ast.parse(src))
                 if isinstance(n, ast.ClassDef)}
        for _ in range(4):          # settle chains defined out of order
            for name, node in table.items():
                bases = [ast.unparse(b).split(".")[-1] for b in node.bases]
                if any(b in gate_rooted for b in bases):
                    gate_rooted.add(name)
                elif any(b in family for b in bases):
                    family.add(name)
        for name, node in table.items():
            if name in gate_rooted or name not in family:
                continue
            for body in node.body:
                if isinstance(body, ast.FunctionDef) and body.name == "__init__":
                    yield f"{where}:{node.lineno}:{name}"


#: The ONE Blender-side tool under `tools/` that this domain does not own, with its owner
#: and the finding that closes it there. Named rather than silently unwalked: an exclusion
#: a reader cannot see is how a population shrinks without anyone deciding it should.
#: Dated 2026-09-04 (wave 16). Delete an entry when its owner's deletion lands and the
#: tree-wide census in `tests` takes over.
NOT_THIS_DOMAINS_TOOLS = {
    "stage_render.py": "instruments-measure (rule 5, its 30 constructors — SEAM 0)",
}


def _owned_sources():
    """This domain's Blender-side `tools/*.py` plus all of `tools/superseded/`.

    Read from disk through `blender_stub.blender_reach` rather than typed, so a tool that
    joins the domain joins the census the day it lands; the one file another domain owns
    is subtracted BY NAME through `NOT_THIS_DOMAINS_TOOLS`, so the hole is visible.
    """
    out = [(fn, read_source(fn)) for fn in sorted(os.listdir(TOOLS))
           if fn.endswith(".py") and blender_stub.blender_reach(fn)
           and fn not in NOT_THIS_DOMAINS_TOOLS]
    sup = os.path.join(TOOLS, "superseded")
    for fn in sorted(os.listdir(sup)):
        if fn.endswith(".py"):
            with open(os.path.join(sup, fn), encoding="utf-8") as fh:
                out.append((f"superseded/{fn}", fh.read()))
    return out


def test_the_rule_5_census_reaches_a_member_outside_the_files_it_walks():
    """RULE 2 — the census is proven on a member OUTSIDE the subset it walks.

    A scratch source no file in the tree contains, carrying a normalising subclass two
    hops down a local chain (the shape a one-level base-name check misses) beside an
    exempt `GateFailure` subclass that must NOT be reported.
    """
    scratch = (
        "from armature_core.errors import ArmatureError, GateFailure\n"
        "class LocalRefusal(ArmatureError):\n    pass\n"
        "class DeeperRefusal(LocalRefusal):\n"
        "    def __init__(self, message, evidence=None):\n"
        "        super().__init__(message)\n"
        "        self.evidence = evidence or {}\n"
        "class AGate(GateFailure):\n"
        "    def __init__(self, message, evidence=None):\n"
        "        super().__init__(message, evidence or {})\n"
        "class NotARefusal:\n"
        "    def __init__(self):\n        pass\n"
    )
    found = list(_refusal_classes([("scratch.py", scratch)]))
    assert [f.rsplit(":", 1)[-1] for f in found] == ["DeeperRefusal"], found


def test_no_tool_local_refusal_class_normalises_its_evidence():
    """RULE 5, the instruments share (SEAM 1). The population is every refusal class in
    this domain's Blender-side tools and in `tools/superseded/` — not the one class the
    finding happened to name.

    Reverted-red: yes — `rig_character.py:176:SiteListInvalid` defined
    `self.evidence = evidence or {}` and this census named it.
    """
    offenders = list(_refusal_classes(_owned_sources()))
    assert offenders == [], (
        "a tool-local refusal class defines its own __init__; the base "
        "`ArmatureError.__init__` stores what it is passed and `GateFailure` is the one "
        f"exemption that normalises: {offenders}")


def test_the_one_blender_side_tool_this_domain_does_not_own_is_named_not_hidden():
    """The exclusion above is a MEASUREMENT, not a convenience: every Blender-side tool is
    either walked by this domain's census or named with the domain that owns it.

    `blender_tools()` is the derivation both halves come from, so the two cannot drift.
    """
    all_blender = set(blender_stub.blender_tools())
    walked = {w for w, _ in _owned_sources() if not w.startswith("superseded/")}
    assert all_blender - walked == set(NOT_THIS_DOMAINS_TOOLS), (
        all_blender - walked, set(NOT_THIS_DOMAINS_TOOLS))
    for fn, owner in NOT_THIS_DOMAINS_TOOLS.items():
        assert owner.strip(), fn


def test_a_bare_message_refusal_from_a_tool_local_class_carries_a_null_receipt(rigchar):
    """The halt-line consequence of rule 5, measured rather than asserted in prose."""
    exc = rigchar.SiteListInvalid("the site registration is inconsistent")
    assert exc.evidence is None
    receipt = {"gate": None, "andon": "SiteListInvalid", "evidence": exc.evidence}
    assert json.loads(json.dumps(receipt))["evidence"] is None


def test_a_receipt_bearing_refusal_keeps_the_dict_it_was_handed(rigchar):
    """Clause 2 of the contract: IDENTITY, not equality."""
    d = {"clause": "site_registration_invalid"}
    assert rigchar.SiteListInvalid("x", d).evidence is d



# ================================================ F-1e564267 — a clause with no caller
#
# THE POPULATION: every view record `render_turnaround.run` builds — N per run, N being
# `--views`, eight in the pinned shot set. `turnaround.gate_set_distinct`'s pixel clause
# (core-solvers, wave 14) is armed only by a caller that attaches `pixels`, and this file
# is its ONLY caller and attached none: measured on the base tree, a grep for the key
# returned zero hits and the gate took its `else` branch every run
# (`n_views_compared_in_pixels: 0`, a verdict ruling on the bytes alone).
#
# The member OUTSIDE the old walk: a PAIR of views that are byte-different and identical in
# pixels. The byte-hash clause provably cannot see it — that is the whole reason the pixel
# clause exists — so no fixture keyed on digests reaches it.


class _FakeImage:
    """`bpy.data.images.load(path)`'s return, for the two calls `_alpha_stats` makes."""

    def __init__(self, flat):
        self._flat = flat
        self.pixels = self

    def foreach_get(self, buf):
        buf[:] = self._flat


class _FakeImages:
    """`bpy.data.images` — a loader keyed on the basename, and a remover that records."""

    def __init__(self, buffers):
        self._buffers = buffers
        self.removed = []

    def load(self, path):
        return _FakeImage(self._buffers[os.path.basename(path)])

    def remove(self, img):
        self.removed.append(img)


def _rgba_flat(height, width, fill):
    """A bottom-up RGBA buffer as Blender hands one to `foreach_get`."""
    a = np.zeros((height, width, 4), dtype=np.float32)
    a[..., 3] = 1.0
    a[..., 0] = fill
    return a.reshape(-1)


@pytest.fixture(scope="module")
def rt16():
    return load_tool("render_turnaround.py")


def test_alpha_stats_hands_back_the_plane_it_already_loaded(rt16, monkeypatch, tmp_path):
    """RED on the operand: the (H, W, 4) buffer this function read and discarded.

    Reverted-red: yes — on the base tree `_alpha_stats` returns a bare dict, so the tuple
    unpacking below raises `ValueError: too many values to unpack`.
    """
    h, w = 6, 4
    flat = _rgba_flat(h, w, 0.25)
    monkeypatch.setattr(rt16.bpy.data, "images", _FakeImages({"v.png": flat}))
    stats, plane = rt16._alpha_stats(str(tmp_path / "v.png"), w, h)
    assert plane.dtype == np.float32
    assert plane.shape == (h, w, 4)
    # The alpha measurement is UNCHANGED by the second return value.
    assert stats["alpha_min"] == 255 and stats["alpha_max"] == 255
    assert stats["transparent_fraction"] == 0.0
    # Top-down: the plane is the bottom-up buffer flipped, which is how the PNG reads.
    assert np.array_equal(plane, flat.reshape(h, w, 4)[::-1])


def test_the_pixel_clause_refuses_two_byte_different_views_with_identical_pixels(
        rt16, monkeypatch, tmp_path):
    """THE OPERAND, end to end: two renders whose PNGs differ in bytes and agree
    pixel-for-pixel. The byte-hash clause cannot see this pair by construction.

    Reverted-red: yes — with `attach_pixels` gone the records carry no plane,
    `gate_set_distinct` returns its `else` branch with `n_views_compared_in_pixels: 0` and
    a verdict reading "... this verdict rules on the bytes only", and nothing is raised.
    """
    h, w = 8, 8
    flat = _rgba_flat(h, w, 0.5)
    monkeypatch.setattr(rt16.bpy.data, "images",
                        _FakeImages({"a.png": flat, "b.png": flat.copy()}))
    views = []
    for i, (name, digest) in enumerate((("a.png", "a" * 64), ("b.png", "b" * 64))):
        _stats, plane = rt16._alpha_stats(str(tmp_path / name), w, h)
        views.append(rt16.attach_pixels(
            {"view": i, "azimuth_deg": i * 45.0, "path": name,
             "bytes": 100 + i, "sha256": digest}, plane))
    with pytest.raises(rt16.TA.TurnaroundGate) as exc:
        rt16.TA.gate_set_distinct(views, 2)
    ev = exc.value.evidence
    assert ev["clause"] == "views_identical_in_pixels"
    assert ev["n_views_compared_in_pixels"] == 2
    assert ev["min_adjacent_pixel_distance"] == 0.0
    assert ev["distinct_sha256"] == 2, "the byte clause passed this set, as it must"


def test_a_real_eight_view_set_reports_all_eight_compared_in_pixels(rt16, monkeypatch,
                                                                    tmp_path):
    """The other half the finding asks for: the gate's verdict names the population it
    actually compared, and it is the whole set rather than none of it.

    Reverted-red: yes — `n_views_compared_in_pixels` was 0 and the verdict said the pixel
    comparison did not happen.
    """
    h, w = 8, 8
    buffers = {f"v{i}.png": _rgba_flat(h, w, 0.1 * i) for i in range(8)}
    monkeypatch.setattr(rt16.bpy.data, "images", _FakeImages(buffers))
    views = []
    for i in range(8):
        _stats, plane = rt16._alpha_stats(str(tmp_path / f"v{i}.png"), w, h)
        views.append(rt16.attach_pixels(
            {"view": i, "azimuth_deg": i * 45.0, "path": f"v{i}.png",
             "bytes": 100 + i, "sha256": f"{i}" * 64}, plane))
    ev = rt16.TA.gate_set_distinct(views, 8)
    assert ev["n_views_compared_in_pixels"] == 8
    assert ev["min_adjacent_pixel_distance"] > 0.0
    assert "distinct in PIXELS over 8 of 8" in ev["verdict"]


def test_the_manifest_drops_the_planes_and_records_what_was_compared(rt16):
    """A `numpy` array cannot ride a `json.dump`ed manifest, and eight full RGBA planes
    have no business on disk beside the eight PNGs that hold them. `manifest_views` drops
    them; `PIXEL_PLANE` says what the gate compared instead."""
    plane = np.zeros((4, 4, 4), dtype=np.float32)
    views = [rt16.attach_pixels({"view": 0, "sha256": "a" * 64}, plane)]
    with pytest.raises(TypeError):
        json.dumps(views)
    stripped = rt16.manifest_views(views)
    assert "pixels" not in stripped[0]
    assert views[0]["pixels"] is plane, "the gate's own list is not mutated"
    assert json.loads(json.dumps(stripped))[0]["sha256"] == "a" * 64
    assert rt16.PIXEL_PLANE["dtype"] == "float32"
    assert rt16.PIXEL_PLANE["compare_stride"] == rt16.TA.PIXEL_COMPARE_STRIDE


def _run_body():
    """`render_turnaround.main` — the function that renders the set and writes the manifest."""
    tree = ast.parse(read_source("render_turnaround.py"))
    return next(n for n in tree.body
                if isinstance(n, ast.FunctionDef) and n.name == "main")


def test_every_view_record_the_run_loop_appends_carries_a_plane():
    """THE POPULATION, not the sample: the clause is armed for EVERY view the loop builds,
    read off the one `views.append(...)` in `main` rather than off a fixture's two records.

    Reverted-red: yes — the base tree's statement is `views.append(rec)`.
    """
    appends = [n for n in ast.walk(_run_body())
               if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
               and n.func.attr == "append"
               and isinstance(n.func.value, ast.Name) and n.func.value.id == "views"]
    assert len(appends) == 1, [ast.unparse(a) for a in appends]
    arg = appends[0].args[0]
    assert isinstance(arg, ast.Call) and getattr(arg.func, "id", None) == "attach_pixels", (
        ast.unparse(appends[0]))


def test_the_gate_sees_the_planes_and_the_manifest_does_not():
    """The ORDER is the property: `gate_set_distinct` is handed the live `views` list, and
    the manifest is handed `manifest_views(views)`. Either half alone is a defect — the
    gate reading stripped records is the disarmed clause again, and the manifest carrying
    planes is a `TypeError` inside `json.dump` after eight renders have been paid for."""
    body = _run_body()
    gate_calls = [n for n in ast.walk(body)
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                  and n.func.attr == "gate_set_distinct"]
    assert len(gate_calls) == 1
    assert getattr(gate_calls[0].args[0], "id", None) == "views", ast.unparse(gate_calls[0])
    manifest = next(n for n in ast.walk(body)
                    if isinstance(n, ast.Assign)
                    and any(getattr(t, "id", None) == "manifest" for t in n.targets))
    views_value = next(v for k, v in zip(manifest.value.keys, manifest.value.values)
                       if isinstance(k, ast.Constant) and k.value == "views")
    assert (isinstance(views_value, ast.Call)
            and getattr(views_value.func, "id", None) == "manifest_views"), (
        ast.unparse(views_value))
