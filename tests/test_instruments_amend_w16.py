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
import types

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import blender_stub                                                     # noqa: E402
from blender_stub import (FakeCollection, FakeObject, blender_stubbed,  # noqa: E402
                          load_tool, read_source)
# ONE implementation of the fake armature, not a second copy: `test_sheet_sides` built it
# for `articulated_side` and this file drives the same function with a NaN in it.
from test_sheet_sides import _Arm, _Scene                               # noqa: E402

TOOLS = blender_stub.TOOLS

SIDE_PROBE_BONES = tuple(f"{j}.{s}" for j in ("shoulder", "elbow", "wrist")
                         for s in ("L", "R"))


# WAVE 26, F-f893634d — `_fn_source` was this walk written out, byte-identical with the
# copy in the sibling amend file. ONE home now, in `blender_stub` beside the
# `read_source` both copies already called.
_fn_source = blender_stub.fn_source


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


def _views_carrying_pixels(ev):
    """How many view records Gate TURN found a plane on, under EITHER key name.

    THE SEAM, and it is read rather than assumed: core-solvers renamed
    `n_views_compared_in_pixels` to `n_views_carrying_pixels` in the same wave (SEAM 8),
    because the old name claimed COMPARISONS while the number counted RECORDS — and the
    two domains land in separate worktrees, so this file must be green on the tree it was
    written in and on the merged one. It reads whichever key the core provides and refuses
    to guess if neither is there; when the merge has landed, the fallback comes out.
    """
    for key in ("n_views_carrying_pixels", "n_views_compared_in_pixels"):
        if key in ev:
            return ev[key]
    raise KeyError(f"Gate TURN's evidence names no plane count: {sorted(ev)}")


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
    assert _views_carrying_pixels(ev) == 2
    assert ev["min_adjacent_pixel_distance"] == 0.0
    assert ev["n_pairs_identical_in_pixels"] == 1
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
    assert _views_carrying_pixels(ev) == 8
    assert ev["min_adjacent_pixel_distance"] > 0.0
    assert "distinct in PIXELS" in ev["verdict"], ev["verdict"]
    assert "NOT compared" not in ev["verdict"], ev["verdict"]


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


# ============================== F-4dc96644 + F-8958f574 — the NaN family, fourth sweep
#
# THE POPULATION: the FOUR instrument sites that compare a MEASURED displacement, named in
# full because three sweeps closed the family elsewhere and left these open —
#
#   1. `make_parts_sheet.articulated_side`   (the ONE implementation of which arm the arc
#      moves; imported by `make_binding_sheet` and `make_rig_sheet`)
#   2. `make_parts_sheet` main's liveness andon        (was `moved <= 1e-6`)
#   3. `make_binding_sheet.render_arm`'s liveness andon (was `moved <= 1e-6`)
#   4. `make_rig_sheet`'s liveness andon                (was `moved <= 1e-4 * diagonal`)
#
# Sites 2–4 were three copies of one clause and are now ONE implementation,
# `make_parts_sheet.gate_arc_survived`, with three callers — so the operand is reachable at
# every site rather than at the one a fixture happened to be written for.
#
# The member OUTSIDE the old walk, for each: the POSED array. `subject_scale` (wave 14) is
# taken on `at_rest`, and `make_rig_sheet`'s own comment says it guards a NaN DIAGONAL —
# so the frame the arc is measured AT was examined by no clause in any of the four.
#
# THE FLOOR (F-8958f574) rides the same fixtures: two of the three copies bounded a metre
# where the third bounded a fraction of the subject's own size.


@pytest.fixture(scope="module")
def mps16():
    return load_tool("make_parts_sheet.py")


def _nan_arm(moving="L"):
    """`test_sheet_sides._Arm` with a NaN in the posed head of every side-probe bone.

    Both sides, which is the shape the finding measured: `disp = {'L': nan, 'R': nan}`.
    """
    arm = _Arm(moving)
    for name in SIDE_PROBE_BONES:
        x = arm.bones[name]._heads[33][0]
        arm.bones[name]._heads[33] = (x, float("nan"), 0.0)
    return arm


def test_articulated_side_refuses_a_nan_displacement_instead_of_answering_R(mps16):
    """RED on the operand the finding named, at the site it named.

    Reverted-red: yes. Measured on the base tree with `disp = {'L': nan, 'R': nan}`:
    `nan >= nan` is False so `hi` became 'R'; `nan <= 0.0` is False so the no-arm-moved
    clause did not fire; `nan > 0.5 * nan` is False so the both-arms clause did not fire —
    and the function RETURNED `{'side': 'R', 'side_word': 'RIGHT', ...}`, which captions
    four 1:1 insets about a limb it never measured. That is the harm its own docstring says
    it was written to end.
    """
    arm = _nan_arm()
    with blender_stubbed():
        with pytest.raises(mps16.ArmatureError) as exc:
            mps16.articulated_side(arm, _Scene(arm), 1, 33)
    assert "not a finite" in str(exc.value)
    ev = exc.value.evidence
    assert ev is not None, "the refusal carries the receipt require_finite wrote into"
    assert [k for k in ev if k.startswith("displacement[")], sorted(ev)


def test_articulated_side_still_answers_a_subject_that_moves(mps16):
    """A gate that refuses everything is not a gate. The bounded path is unchanged."""
    arm = _Arm("R")
    with blender_stubbed():
        rec = mps16.articulated_side(arm, _Scene(arm), 1, 33)
    assert rec["side"] == "R"
    assert math.isfinite(rec["displacement"]["L"])
    assert math.isfinite(rec["displacement"]["R"])


def _cube(scale=1.0):
    """Eight corners of a cube — a subject with a real, finite bbox diagonal."""
    return np.array([[x, y, z] for x in (0.0, scale) for y in (0.0, scale)
                     for z in (0.0, scale)], dtype=np.float64)


def test_the_liveness_measurement_refuses_a_non_finite_displacement(mps16):
    """RED on the operand for sites 2, 3 and 4 at once: the measured displacement.

    `at_rest` is finite, so `subject_scale`'s clause — the ONLY finiteness refusal these
    three sites had — passes; the NaN is in the POSED frame, which is the population none
    of the three examined.

    Reverted-red: yes. On the base tree each of the three clauses is `if moved <= <floor>`
    with `moved = nan`, `nan <= x` is False, the run proceeds, and the sheet's spec and its
    `*_OK` sentinel publish `max_displacement` / `max_vertex_motion` as NaN.
    """
    for bad in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(mps16.ArmatureError) as exc:
            mps16.arc_liveness(bad, "max_vertex_motion", _cube(), "make_rig_sheet")
        assert "not a finite" in str(exc.value), bad
        assert exc.value.evidence["where"] == "make_rig_sheet"


def test_the_liveness_floor_is_a_fraction_of_the_subject_and_not_a_metre(mps16):
    """F-8958f574, on the direction the constant did not bound.

    A subject a thousand times smaller has a floor a thousand times smaller. A real arc of
    5e-7 m on a 1e-3 m cube (diagonal 1.73e-3, floor 1.73e-7) is LIVE, where the old
    `moved <= 1e-6` refused it and the sheet never got built; float round-trip noise of
    5e-6 m on a 1000 m cube (diagonal 1.73e3, floor 0.173) is DEAD, where the old
    `moved <= 1e-6` accepted it and the sheet read as an arc that survived.

    Reverted-red: yes, both halves, at `make_parts_sheet` and `make_binding_sheet` — the
    two copies that bounded metres. `make_rig_sheet` already bounded a fraction and is
    green on both trees, which is why the finding named it as the shape to carry.
    """
    alive, _d, _lo, _hi = mps16.arc_liveness(
        5e-7, "max_displacement", _cube(1e-3), "make_parts_sheet")
    assert alive["floor"] < 5e-7 < 1e-6, alive["floor"]
    assert alive["survived"] is True
    dead, _d, _lo, _hi = mps16.arc_liveness(
        5e-6, "max_displacement", _cube(1000.0), "make_parts_sheet")
    assert dead["floor"] > 5e-6 > 1e-6, dead["floor"]
    assert dead["survived"] is False


def test_the_liveness_record_reads_as_a_fraction_and_names_its_floor(mps16):
    """The record the Director reads: a ratio and the subject's own size, not a metre."""
    rec, diagonal, lo, hi = mps16.arc_liveness(
        0.0, "max_displacement", _cube(2.0), "make_parts_sheet")
    assert rec["clause"] == "arc_did_not_survive"
    assert rec["where"] == "make_parts_sheet"
    assert rec["floor_fraction"] == mps16.ARC_FLOOR_FRACTION
    assert rec["floor"] == pytest.approx(mps16.ARC_FLOOR_FRACTION * rec["bbox_diagonal"])
    assert rec["displacement_over_diagonal"] == 0.0
    assert rec["survived"] is False
    assert diagonal == pytest.approx(2.0 * 3 ** 0.5)
    assert list(lo) == [0.0, 0.0, 0.0] and list(hi) == [2.0, 2.0, 2.0]


def test_a_non_finite_rest_frame_is_still_gate_scale_and_not_this_clause(mps16):
    """The two refusals stay distinguishable: a NaN in the REST array is Gate SCALE's
    (`GateSubjectDegenerate`), a NaN in the measured displacement is this clause's. Two
    andons never share one id, and a session sent to the wrong one loses the afternoon."""
    bad_rest = _cube(1.0)
    bad_rest[3][1] = float("nan")
    with pytest.raises(mps16.rig_character.GateSubjectDegenerate) as exc:
        mps16.arc_liveness(0.30, "max_displacement", bad_rest, "make_parts_sheet")
    assert exc.value.gate == "SCALE"


#: The four sites of this sweep, named — the `family:` line as data. Sites 2-4 are the
#: three callers of the one measurement; each keeps its OWN refusal, in its own words, at
#: the line where its own arc died.
NAN_SWEEP_SITES = {
    "make_parts_sheet.py": ("articulated_side", "arc_liveness"),
    "make_binding_sheet.py": ("arc_liveness",),
    "make_rig_sheet.py": ("arc_liveness",),
}


def test_every_one_of_the_four_sites_bounds_its_measurement_before_comparing_it():
    """THE POPULATION, read off the tree: no dailies sheet compares a displacement it has
    not bounded, no copy of the measurement has been reintroduced, and every floor
    comparison is against `arc["floor"]` rather than a literal length.

    Reverted-red: yes — the base tree carries `moved <= 1e-6` twice and
    `moved <= 1e-4 * diagonal` once, none of them behind `require_finite`.
    """
    for filename, expected in NAN_SWEEP_SITES.items():
        src = read_source(filename)
        for token in expected:
            assert f"{token}(" in src, (filename, token)
        # AST, not a grep: a comment that RECORDS the old constant is the correction the
        # repo asks for, and a text scan cannot tell it from the constant itself.
        bare = []
        for node in ast.walk(ast.parse(src)):
            if not isinstance(node, ast.Compare):
                continue
            for op, right in zip(node.ops, node.comparators):
                # `<= 0.0` is exempt and is not a tolerance: zero displacement is the
                # exact boundary "nothing moved at all", which needs no scale to state
                # (`articulated_side`'s neither-arm-moved clause).
                if (isinstance(op, (ast.LtE, ast.Lt))
                        and isinstance(right, ast.Constant)
                        and isinstance(right.value, float) and right.value != 0.0):
                    bare.append((node.lineno, ast.unparse(node)))
        assert bare == [], (
            f"{filename} compares against a bare float again; a global constant must not "
            f"govern a local feature: {bare}")
        assert 'arc["floor"]' in src or "arc['floor']" in src, filename
    # The measurement and the bound exist ONCE. A fourth copy is the defect this
    # consolidation removed; the three RAISES are deliberately not consolidated.
    bodies = [f for f in os.listdir(TOOLS)
              if f.endswith(".py") and "def arc_liveness(" in read_source(f)]
    assert bodies == ["make_parts_sheet.py"], bodies


def test_each_sheet_keeps_its_own_refusal_at_its_own_site():
    """The raise is NOT consolidated, on purpose: an andon lives inside the tool performing
    the step (CLAUDE.md), and `make_binding_sheet.render_arm` is a refusing function in the
    write-ordering census only while it raises in its own body."""
    for filename, fn in (("make_parts_sheet.py", "main"),
                         ("make_binding_sheet.py", "render_arm"),
                         ("make_rig_sheet.py", "main")):
        tree = ast.parse(read_source(filename))
        target = next((n for n in ast.walk(tree)
                       if isinstance(n, ast.FunctionDef) and n.name == fn), None)
        assert target is not None, (filename, fn)
        raises = [n for n in ast.walk(target) if isinstance(n, ast.Raise)]
        own = [r for r in raises if "did not survive the round" in ast.unparse(r)]
        assert own, f"{filename}:{fn} no longer raises its own liveness refusal"
        # And it names its own andon rather than the family: `errors.py` rules that a site
        # raising the bare `ArmatureError` "names nothing about which andon pulled", and
        # these three raises now carry a receipt a reader has to be able to attribute.
        assert all("ArcDidNotSurvive" in ast.unparse(r) for r in own), [
            ast.unparse(r) for r in own]


def test_the_helper_is_reached_through_require_finite_and_not_a_second_isfinite():
    """`parts.require_finite` is the ONE non-finite helper (wave 10's rule 4). A hand-rolled
    `math.isnan` beside it is a second implementation with a different message."""
    body = _fn_source("make_parts_sheet.py", "arc_liveness")
    assert "parts.require_finite(" in body
    for hand_rolled in ("math.isnan", "math.isinf", "np.isnan", "np.isfinite"):
        assert hand_rolled not in body, hand_rolled


# ================================== F-94a7d14d — one question, two implementations
#
# THE POPULATION: every andon in this domain that decides RENDER VISIBILITY. There are
# two — `rig_character.gate_objects_registered` (Gate OBJ, guarding the central export,
# also called by `lift_solve`) and `rig_retopo.isolate_subject` (Gate ISOLATE, between
# panels) — and both computed it with a ONE-LEVEL predicate,
# `ob.hide_render or any(c.hide_render for c in ob.users_collection)`, while
# `blender_scene.render_visible_meshes` answers the same question through
# `collection_render_flags`, which walks the LAYER-collection tree.
#
# The member OUTSIDE the old walk: a mesh one collection DEEPER than the level the
# predicate reads — parked under a `hide_render=True` parent — and a mesh in a collection
# the view layer EXCLUDES, which plain collection flags do not carry at all
# (`blender_scene.py:169-171` says so in its own words). Both read as VISIBLE to the old
# expression and as invisible to the renderer, so a decoy one level deeper than the glTF
# importer's own `glTF_not_exported` halted the two most expensive tools in the tree on a
# scene that would have rendered correctly.


class _LayerScene:
    """`scene.objects` and `scene.view_layers[0].layer_collection` — the whole surface both
    andons and `blender_scene.collection_render_flags` read."""

    def __init__(self, root, objects=()):
        self.objects = list(objects)
        self.view_layers = [self]
        self.layer_collection = root


def _nested_scene():
    """`Scene Collection > Props(hide_render) > Debris`, with a mesh in `Debris`.

    The decoy is one collection DEEPER than the level the old predicate read: its own
    collection carries `hide_render=False`, and its parent carries True.
    """
    root = FakeCollection("Scene Collection")
    props = FakeCollection("Props", hide_render=True)
    debris = FakeCollection("Debris")
    props.children = [debris]
    root.children = [props]
    subject = FakeObject("hero", collection=root)
    arm = FakeObject("hero_rig", kind="ARMATURE", collection=root)
    decoy = FakeObject("Icosphere", collection=debris)
    return _LayerScene(root, [subject, arm, decoy]), subject, arm, decoy


def _excluded_scene():
    """A mesh in a collection the VIEW LAYER excludes — a flag plain collections do not
    carry, so no reading of `users_collection[i].hide_render` can ever see it."""
    root = FakeCollection("Scene Collection")
    gone = FakeCollection("glTF_not_exported", exclude=True)
    root.children = [gone]
    subject = FakeObject("hero", collection=root)
    arm = FakeObject("hero_rig", kind="ARMATURE", collection=root)
    decoy = FakeObject("Icosphere", collection=gone)
    return _LayerScene(root, [subject, arm, decoy]), subject, arm, decoy


def _visible_scene():
    """The control: a decoy in a plainly visible collection. The andons must still fire."""
    root = FakeCollection("Scene Collection")
    props = FakeCollection("Props")
    root.children = [props]
    subject = FakeObject("hero", collection=root)
    arm = FakeObject("hero_rig", kind="ARMATURE", collection=root)
    decoy = FakeObject("Icosphere", collection=props)
    return _LayerScene(root, [subject, arm, decoy]), subject, arm, decoy


@pytest.fixture(scope="module")
def retopo16():
    return load_tool("rig_retopo.py")


@pytest.mark.parametrize("build", [_nested_scene, _excluded_scene],
                         ids=["nested-under-a-hidden-parent", "excluded-from-the-layer"])
def test_gate_obj_does_not_call_an_undrawable_decoy_a_stray(rigchar, build):
    """RED on the operand: a decoy the RENDERER will not draw and the old predicate called
    visible, at the export boundary where a halt is most expensive.

    Reverted-red: yes. With `hidden = ob.hide_render or any(c.hide_render for c in
    ob.users_collection)` restored, both scenes report `effectively_hidden: False` for the
    decoy and Gate OBJ raises `GateObjects` — halting `rig_character` on a scene
    `blender_scene.render_visible_meshes` returns `[]` for.
    """
    scene, subject, arm, decoy = build()
    with blender_stubbed():
        rec = rigchar.gate_objects_registered(scene, subject, arm)
        drawn = rigchar.blender_scene.render_visible_meshes(scene, scene.objects)
    assert rec["strays"] == [], rec["strays"]
    assert decoy.name not in [o.name for o in drawn], "the renderer agrees it is invisible"
    seen = {o["name"]: o for o in rec["objects"]}
    assert seen[decoy.name]["effectively_hidden"] is True


def test_gate_obj_still_refuses_a_decoy_the_renderer_would_draw(rigchar):
    """A gate that refuses nothing is not a gate: the control scene still halts."""
    scene, subject, arm, decoy = _visible_scene()
    with blender_stubbed():
        with pytest.raises(rigchar.GateObjects) as exc:
            rigchar.gate_objects_registered(scene, subject, arm)
    assert [o["name"] for o in exc.value.evidence["strays"]] == [decoy.name]


def test_gate_obj_states_which_visibility_notion_it_ruled_on(rigchar):
    """The other half of the finding: `export_rigged`'s operator arguments name
    `use_selection=False` and no visibility key at all, so the exemption was being made on
    a property the call it guards never mentions. The record now says which one it read."""
    scene, subject, arm, _decoy = _nested_scene()
    with blender_stubbed():
        rec = rigchar.gate_objects_registered(scene, subject, arm)
    assert "collection_render_flags" in rec["visibility"]
    assert "exclude" in rec["visibility"]
    assert rec["collections_hidden"] == ["Debris", "Props"], rec["collections_hidden"]
    assert "Scene Collection" in rec["collections_reachable"]


@pytest.mark.parametrize("build", [_nested_scene, _excluded_scene],
                         ids=["nested-under-a-hidden-parent", "excluded-from-the-layer"])
def test_isolate_subject_does_not_halt_on_an_undrawable_decoy(retopo16, build):
    """The same operand at the second site. `isolate_subject`'s loop hides the objects it
    was HANDED; the decoy is not among them, and the old predicate read it as still drawn.

    Reverted-red: yes — both scenes raise `ComparisonNotIsolated` with the decoy in
    `still_visible` on the one-level expression.
    """
    scene, subject, _arm, decoy = build()
    with blender_stubbed():
        hidden = retopo16.isolate_subject(scene, [subject], subject)
    assert decoy.name not in hidden


def test_isolate_subject_still_refuses_a_decoy_the_renderer_would_draw(retopo16):
    scene, subject, _arm, decoy = _visible_scene()
    with blender_stubbed():
        with pytest.raises(retopo16.ComparisonNotIsolated) as exc:
            retopo16.isolate_subject(scene, [subject], subject)
    ev = exc.value.evidence
    assert ev["still_visible"] == [decoy.name]
    assert "collection_render_flags" in ev["visibility"]


#: The two andons that answer render visibility, and the function each answers it in.
#: The FUNCTION is named because the property is "this andon consults the one walk", and a
#: call anywhere else in the module does not give it to this one.
VISIBILITY_ANDONS = [
    ("rig_character.py", "gate_objects_registered"),
    ("rig_retopo.py", "isolate_subject"),
]

ONE_WALK = "collection_render_flags"


def _calls_the_walk(tree, function_name):
    """Line numbers where `function_name` CALLS the one walk — an `ast.Call` whose callee
    resolves to it, never a substring of the file."""
    fns = [n for n in ast.walk(tree)
           if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
           and n.name == function_name]
    assert len(fns) == 1, (function_name, [n.lineno for n in fns])
    out = []
    for node in ast.walk(fns[0]):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        called = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        if called == ONE_WALK:
            out.append(node.lineno)
    return sorted(out)


@pytest.mark.parametrize("filename,function_name", VISIBILITY_ANDONS,
                         ids=[f"{f}::{n}" for f, n in VISIBILITY_ANDONS])
def test_each_visibility_andon_CALLS_the_one_walk(filename, function_name):
    """WAVE 23, F-73402474 — keyed on an `ast.Call` inside the andon's own function.

    This was `assert "collection_render_flags(" in src`, which reads the RAW SOURCE TEXT of
    the module, so a comment or a docstring naming the walk satisfies it — the shape wave 6
    removed from `tests/test_canon_spend.py` and wave 15 closed as `F-09a56210` at a
    different site, recurring here at a new one. Both modules mention the name in prose
    beside the call (`rig_character.py:785`, `:813`; `rig_retopo.py:331`, `:356`), so the
    substring survives deleting the call.

    Measured 2026-09-05 by running BOTH clauses of the old test over a three-line source
    whose only mention of the walk is a comment and which returns `ob.hide_render`: both
    passed. `test_a_comment_naming_the_walk_does_not_satisfy_the_clause` below is that decoy,
    kept in the tree.
    """
    tree = ast.parse(read_source(filename))
    sites = _calls_the_walk(tree, function_name)
    assert sites, (
        f"{filename}::{function_name} does not CALL `{ONE_WALK}`. The prose beside it may "
        f"still name the walk; a substring check reads that as compliance.")


@pytest.mark.parametrize("filename,function_name", VISIBILITY_ANDONS,
                         ids=[f"{f}::{n}" for f, n in VISIBILITY_ANDONS])
def test_no_visibility_andon_carries_its_own_one_level_predicate(filename, function_name):
    """The other clause, unchanged in intent and narrowed to the andon's own function.

    `any(c.hide_render for c in ...)` is the shape that was wrong twice. On its own this
    clause is satisfied by code that consults NO collection visibility at all — which is why
    it now sits beside the CALL check rather than instead of one.

    Reverted-red: the base tree carried that comprehension in
    `rig_character.py::gate_objects_registered` and `rig_retopo.py::isolate_subject`.
    RE-ANCHORED 2026-09-05 (wave 25, instruments) on the SYMBOLS: both were bare line
    citations, and the clause words this wave added pushed the `rig_retopo` one onto a
    blank line. A line citation does not survive an edit above it; a symbol does.
    """
    tree = ast.parse(read_source(filename))
    for node in ast.walk(tree):
        if not isinstance(node, ast.GeneratorExp):
            continue
        text = ast.unparse(node)
        assert "hide_render" not in text or "users_collection" not in text, (
            f"{filename}:{node.lineno} answers render visibility one level deep "
            f"again: {text}")


def test_a_comment_naming_the_walk_does_not_satisfy_the_clause():
    """The decoy, kept in the tree: the exact substitution that used to pass.

    A module whose only mention of `collection_render_flags` is a comment, and which returns
    `ob.hide_render` — one level deep, the twice-wrong shape. The substring predicate says
    yes; the AST predicate says no. Both directions asserted, so the decoy proves the
    difference rather than only the new answer.
    """
    decoy = "\n".join([
        "def gate_objects_registered(scene, obs):",
        "    # visibility comes from blender_scene.collection_render_flags(scene)",
        "    return [ob for ob in obs if not ob.hide_render]",
    ])
    assert ONE_WALK + "(" in decoy, "the decoy does not carry the substring it must"
    assert _calls_the_walk(ast.parse(decoy), "gate_objects_registered") == []

    real = "\n".join([
        "def gate_objects_registered(scene, obs):",
        "    reachable, hidden = blender_scene.collection_render_flags(scene)",
        "    return reachable",
    ])
    assert _calls_the_walk(ast.parse(real), "gate_objects_registered") == [2]


# ================================== F-26ee2b03 — the flag that shapes the ground truth
#
# THE POPULATION: every argument of `make_test_armature` that shapes the synthetic subject
# — `--frames`, `--fps`, `--segments`, `--thickness`, `--joint-scale`. Not `--frames`
# alone: the finding names the other four in the same breath, and a fix that bounds one
# number of five is the wave-14 shape this wave exists to stop.
#
# The member OUTSIDE the old walk: `posearc.arc_readout`, the ONE refusal that ran before
# geometry, does not examine the frame count at all — measured, `arc_readout(arc, 0, ...)`
# and `arc_readout(arc, -5, ...)` both return normally. So every clause upstream of the
# export was blind to it, and the first thing that noticed was `side["frames"][0]`, an
# IndexError at exit 1, AFTER the GLB and the `.joints.json` were both on disk.


@pytest.fixture(scope="module")
def mta16():
    return load_tool("make_test_armature.py")


def _args(**over):
    ns = types.SimpleNamespace(
        thickness=0.030, joint_scale=1.55, segments=16, pose_arc="probe_arm",
        frames=33, fps=16, arc_start_deg=0.0, arc_end_deg=90.0, out="x.glb")
    for k, v in over.items():
        setattr(ns, k, v)
    return ns


@pytest.mark.parametrize("frames", [0, -5, 1])
def test_a_frame_count_that_cannot_carry_a_performance_is_refused_by_name(mta16, frames):
    """RED on the operand the finding named.

    Reverted-red: yes. On the base tree nothing above the export examined `--frames`:
    `build`'s keying loop is `for i in range(frames)` so no keyframe is inserted, the
    LINEAR pass is skipped, `scene.frame_end` is set to 0 or a negative, the GLB is
    exported and PASSES Gate GLB, the `.joints.json` is written with `frames: []`, and only
    then does `side["frames"][0]` raise IndexError — recorded as
    `MAKE_TEST_ARMATURE_HALT {"outcome": "FAILED - an unhandled error"}` at exit 1, naming
    a dict index rather than the flag.
    """
    with pytest.raises(mta16.SubjectArgError) as exc:
        mta16.require_subject_args(_args(frames=frames))
    ev = exc.value.evidence
    assert ev["clause"] == "subject_args"
    assert ev["frames"] == frames
    assert any("--frames" in line for line in ev["offending"]), ev["offending"]


def test_the_frame_count_is_only_bounded_where_it_is_read(mta16):
    """Grade the clause only on what it governs. Without `--pose-arc` this tool builds the
    static bind pose, `scene.frame_end` is pinned to 1 and `--frames` is never read — so
    refusing it there would refuse a flag the run does not use."""
    assert mta16.require_subject_args(_args(pose_arc=None, frames=0)) is not None


@pytest.mark.parametrize("flag,value", [
    ("fps", 0), ("fps", -16),
    ("segments", 2), ("segments", 0),
    ("thickness", 0.0), ("thickness", -0.03), ("thickness", float("nan")),
    ("joint_scale", 0.0), ("joint_scale", float("inf")),
])
def test_the_other_four_shaping_flags_are_bounded_too(mta16, flag, value):
    """THE POPULATION, not the one flag the title of the finding names. `--fps` divides
    into seconds in the glTF key times; `--segments` under three gives a limb no
    cross-section; the two radii are lengths.

    Reverted-red: yes — every one of these returned normally from `parse_args` and reached
    geometry on the base tree.
    """
    with pytest.raises(mta16.SubjectArgError) as exc:
        mta16.require_subject_args(_args(**{flag: value}))
    assert any(flag.replace("_", "-") in line for line in exc.value.evidence["offending"])


def test_a_well_formed_invocation_is_not_refused(mta16):
    """A gate that refuses everything is not a gate."""
    ok = _args()
    assert mta16.require_subject_args(ok) is ok
    assert mta16.require_subject_args(_args(frames=2)) is not None


def test_the_refusal_runs_above_resolve_arc_and_above_every_write():
    """The ORDER is the property: nothing exists when it fires — no geometry, no output
    directory, no GLB, no sidecar. Read off `main`'s own statement order.

    Reverted-red: yes, trivially — the call did not exist.
    """
    tree = ast.parse(read_source("make_test_armature.py"))
    main = next(n for n in tree.body
                if isinstance(n, ast.FunctionDef) and n.name == "main")
    lines = {}
    for node in ast.walk(main):
        if isinstance(node, ast.Call):
            name = (node.func.attr if isinstance(node.func, ast.Attribute)
                    else getattr(node.func, "id", None))
            if name in ("require_subject_args", "resolve_arc", "arc_readout", "build",
                        "makedirs"):
                lines.setdefault(name, node.lineno)
    for later in ("resolve_arc", "arc_readout", "build", "makedirs"):
        assert lines["require_subject_args"] < lines[later], (later, lines)


def test_the_subject_arg_refusal_is_in_the_family_so_the_halt_is_refused_not_failed(mta16):
    """Exit 2 and REFUSED, where the IndexError was exit 1 and "FAILED - an unhandled
    error". `SpecError` is an `ArmatureError`; it is deliberately NOT a `GateFailure`,
    because no gate ran — this is an argument that never should have reached geometry."""
    from armature_core.errors import ArmatureError, GateFailure

    assert issubclass(mta16.SubjectArgError, ArmatureError)
    assert not issubclass(mta16.SubjectArgError, GateFailure)

    def raiser():
        raise mta16.SubjectArgError("bad --frames", {"clause": "subject_args"})

    code, escaped = blender_stub.exit_code_of_main_block("make_test_armature.py",
                                                         raiser=raiser)
    assert escaped is None, escaped
    assert code == 2, code


# ============================ F-39381793 — the copy the family was carried FROM drifted
#
# THE POPULATION: every definition of `select_engine` under `tools/` and
# `tools/superseded/` — seven today, derived by AST rather than typed. `_render_status` is
# held identical across its nine copies by a census
# (`test_instruments_amend_w14.py::test_the_render_status_helper_is_one_implementation_in_every_copy`
# -- RE-ANCHORED ON THE SYMBOL in wave 26, F-f893634d: that file's `_fn_source` became an
# alias of `blender_stub.fn_source` and the eight lines it lost moved the cited line onto a
# docstring, so `TESTS_STALE_ANCHORS_RECORDED`'s row for it stopped being stale. A name
# survives an edit above it; a line number does not);
# this function had none, and the copy every other one was carried FROM is the copy that
# lost the `"clause": "engine"` key the halt line is told apart by.
#
# The census normalises the docstring, the gate CLASS and the MESSAGE — a bake is not a
# render and `preview_glb` draws a preview, so the sentence each tool prints is properly
# its own — and then requires one structure and one set of evidence keys. That is the
# property that drifted; byte identity would force `rig_bake` to say it renders.


def _select_engine_defs(sources):
    """`{where: the ast.FunctionDef}` for every `select_engine` in `sources`.

    `sources` is `(where, source text)` pairs so the census can be pointed at a SCRATCH
    tree carrying a defective member — rule 2's shape.
    """
    out = {}
    for where, src in sources:
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.FunctionDef) and node.name == "select_engine":
                out[where] = node
    return out


def _normalised(fn):
    """The body with the docstring, the gate class and the message string replaced.

    What is left is the loop, the return, and the evidence dict — the structure that must
    not differ between copies.
    """
    body = list(fn.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        body = body[1:]
    module = ast.Module(body=body, type_ignores=[])

    class _Blank(ast.NodeTransformer):
        def visit_Raise(self, node):
            self.generic_visit(node)
            if isinstance(node.exc, ast.Call):
                node.exc.func = ast.Name(id="GATE", ctx=ast.Load())
                if node.exc.args:
                    node.exc.args[0] = ast.Constant(value="MESSAGE")
            return node

    module = _Blank().visit(module)
    ast.fix_missing_locations(module)
    return ast.unparse(module)


def _engine_evidence_keys(fn):
    """The keys of the evidence dict this copy raises with, in order."""
    for node in ast.walk(fn):
        if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
            for arg in node.exc.args:
                if isinstance(arg, ast.Dict):
                    return [k.value for k in arg.keys if isinstance(k, ast.Constant)]
    return None


def _all_tool_sources():
    out = [(fn, read_source(fn)) for fn in sorted(os.listdir(TOOLS)) if fn.endswith(".py")]
    sup = os.path.join(TOOLS, "superseded")
    for fn in sorted(os.listdir(sup)):
        if fn.endswith(".py"):
            with open(os.path.join(sup, fn), encoding="utf-8") as fh:
                out.append((f"superseded/{fn}", fh.read()))
    return out


def test_every_copy_of_select_engine_has_one_structure():
    """The census `_render_status` has and this function did not.

    Reverted-red: yes — on the base tree `preview_glb.py`'s copy normalises to a body whose
    evidence dict is `{'candidates': ..., 'blender': ...}` while the other six normalise to
    one carrying `'clause'` first, so this returns two distinct bodies.
    """
    defs = _select_engine_defs(_all_tool_sources())
    assert len(defs) >= 6, sorted(defs)
    shapes = {}
    for where, fn in defs.items():
        shapes.setdefault(_normalised(fn), []).append(where)
    assert len(shapes) == 1, {k[:120]: v for k, v in shapes.items()}


def test_every_copy_of_select_engine_names_the_engine_clause():
    """The FIELD the halt line is told apart by, over the whole population.

    Reverted-red: yes — `preview_glb.py` returned `['candidates', 'blender']`.
    """
    for where, fn in _select_engine_defs(_all_tool_sources()).items():
        keys = _engine_evidence_keys(fn)
        assert keys == ["clause", "candidates", "blender"], (where, keys)
        raises = [n for n in ast.walk(fn) if isinstance(n, ast.Raise)]
        assert len(raises) == 1, where
        assert '"clause": "engine"' in ast.unparse(raises[0]) or \
               "'clause': 'engine'" in ast.unparse(raises[0]), where


def test_the_select_engine_census_reaches_a_member_outside_the_tree_it_walks():
    """RULE 2 — proven RED on a member outside the subset it walks: a scratch copy that
    drops the clause key, which is exactly the drift measured on `preview_glb`."""
    good = read_source("preview_walk.py")
    drifted = good.replace('{"clause": "engine", "candidates": list(candidates),\n'
                           '         "blender": bpy.app.version_string})',
                           '{"candidates": list(candidates),\n'
                           '         "blender": bpy.app.version_string})', 1)
    assert drifted != good, "the mutation did not apply; this fixture proves nothing"
    sources = _all_tool_sources() + [("scratch_drifted.py", drifted)]
    defs = _select_engine_defs(sources)
    shapes = {}
    for where, fn in defs.items():
        shapes.setdefault(_normalised(fn), []).append(where)
    assert len(shapes) == 2, sorted(shapes.values())
    assert _engine_evidence_keys(defs["scratch_drifted.py"]) == ["candidates", "blender"]


def test_every_preview_glb_refusal_names_a_clause():
    """The other half of the finding: `preview_glb` had four `PreviewGlbGate` raise sites
    and one clause between them, so a `PREVIEW_GLB_HALT` line could not be told from its
    siblings by the field every other refusal in this family uses for exactly that.

    Reverted-red: yes — three of the four carried no `clause` key.
    """
    tree = ast.parse(read_source("preview_glb.py"))
    sites = [n for n in ast.walk(tree)
             if isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call)
             and getattr(n.exc.func, "id", None) == "PreviewGlbGate"]
    assert len(sites) == 4, len(sites)
    clauses = []
    for node in sites:
        ev = next((a for a in node.exc.args if isinstance(a, ast.Dict)), None)
        assert ev is not None, ast.unparse(node)
        found = [v.value for k, v in zip(ev.keys, ev.values)
                 if isinstance(k, ast.Constant) and k.value == "clause"
                 and isinstance(v, ast.Constant)]
        assert found, ast.unparse(node)
        clauses.append(found[0])
    assert sorted(clauses) == ["engine", "missing_or_empty", "no_render_visible_mesh",
                               "operator_status"], sorted(clauses)
