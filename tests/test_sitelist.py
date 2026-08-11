"""The registered site list is what it says it is, and it still matches E01's instrument.

The registration (`docs/experiments/E07-site-list.md`) and `armature_core/sitelist.py` are
the same document in two forms. Drift between them is silent — the rig would build, every
gate would pass, and the list governing it would no longer be the one that was committed
before the first bone. These tests are what makes that drift fail instead.
"""

import ast
import os

import pytest

from conftest import TOOLS

from armature_core import sitelist


def _probe_glb_sites():
    """E01's own 18, parsed out of `probe_glb.py` without importing it.

    Parsed rather than imported because that module imports bpy at module scope, and a
    test that can only run inside Blender is a test that does not run.
    """
    src = open(os.path.join(TOOLS, "probe_glb.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            getattr(t, "id", None) == "SITES" for t in node.targets
        ):
            return [ast.literal_eval(k) for k in node.value.keys]
    raise AssertionError("probe_glb.py no longer defines a SITES dict")


def test_registration_is_internally_consistent():
    assert sitelist.validate() is True


def test_the_registered_list_is_22_bones_18_sites_4_structural():
    assert len(sitelist.BONES) == 22
    assert len(sitelist.ALL_NAMES) == 22
    assert len(set(sitelist.ALL_NAMES)) == 22
    assert len(sitelist.E01_SITES) == 18
    assert len(sitelist.STRUCTURAL) == 4


def test_e01_sites_are_exactly_the_sites_e01_measured_against():
    """The load-bearing one. E01's `0 / 18` was computed against `probe_glb.py::SITES`;
    if E07 registers a different 18 then closing "the gap" closes a different gap."""
    assert sorted(sitelist.E01_SITES) == sorted(_probe_glb_sites())


def test_every_e01_site_names_a_bone_whose_head_is_a_landmark():
    by = sitelist.by_name()
    for site in sitelist.E01_SITES:
        assert site in by, f"registered E01 site {site!r} names no bone"
        assert by[site].head, f"{site!r} has no head landmark"


def test_the_five_facial_markers_do_not_deform():
    """The spec puts face bones out of scope. They exist to close the naming gap under
    E01's own instrument; if one ever acquires `use_deform` it is rigging a face."""
    by = sitelist.by_name()
    for name in ("nose", "eye.L", "eye.R", "ear.L", "ear.R"):
        assert by[name].deform is False, f"{name} deforms; the face is out of scope"
    for name in sitelist.ALL_NAMES:
        if name not in ("nose", "eye.L", "eye.R", "ear.L", "ear.R"):
            assert by[name].deform is True, f"{name} does not deform but should"


def test_parents_precede_children_because_the_build_never_looks_ahead():
    seen = set()
    for b in sitelist.BONES:
        if b.parent is not None:
            assert b.parent in seen, f"{b.name} names parent {b.parent} defined after it"
        seen.add(b.name)


def test_hierarchy_is_a_single_tree_rooted_at_hips():
    roots = [b.name for b in sitelist.BONES if b.parent is None]
    assert roots == ["hips"]


# --- what a broken registration looks like ------------------------------------------


def _mutated(**changes):
    """A copy of BONES with one field changed, so validate() can be shown to fire."""
    bones = [sitelist.Bone(b.name, b.parent, b.head, b.tail, b.deform, b.site)
             for b in sitelist.BONES]
    return bones, changes


def _run_validate_with(bones):
    original = sitelist.BONES
    sitelist.BONES = tuple(bones)
    try:
        return sitelist.validate()
    finally:
        sitelist.BONES = original


def test_validate_fires_on_a_duplicate_name():
    bones, _ = _mutated()
    bones[3].name = bones[2].name          # 'neck' becomes a second 'chest'
    with pytest.raises(ValueError) as exc:
        _run_validate_with(bones)
    assert "duplicate" in str(exc.value) or "no bone" in str(exc.value)


def test_validate_fires_when_a_registered_site_loses_its_bone():
    """The E07-specific way this goes wrong: a rename that quietly drops a site."""
    bones, _ = _mutated()
    for b in bones:
        if b.name == "ear.R":
            b.name = "ear_right"
    with pytest.raises(ValueError) as exc:
        _run_validate_with(bones)
    assert "ear.R" in str(exc.value)


def test_validate_fires_on_a_forward_parent_reference():
    bones, _ = _mutated()
    for b in bones:
        if b.name == "hips":
            b.parent = "ankle.R"           # defined last; the build would KeyError
    with pytest.raises(ValueError) as exc:
        _run_validate_with(bones)
    assert "does not precede" in str(exc.value)


def test_validate_fires_on_a_bone_no_list_registered():
    bones, _ = _mutated()
    bones.append(sitelist.Bone("thumb.L", "wrist.L", "wrist_L", "hand_end_L", True, False))
    with pytest.raises(ValueError) as exc:
        _run_validate_with(bones)
    assert "thumb.L" in str(exc.value)
