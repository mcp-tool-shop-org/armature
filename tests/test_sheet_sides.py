"""The dailies sheets must show the arm the arc actually moves.

F-b5483ebc. Three of the four dailies sheets hard-coded the LEFT side for their joint
insets while the arc they illustrate CHOOSES its side by measurement:
`rig_character.author_probe` computes

    left_sign = ctx["landmarks"]["facing"]["left_x_sign"]
    side      = "L" if left_sign * sitelist.PROBE_ARC_SIDE_X_SIGN > 0 else "R"

and poses `shoulder.{side}` — its docstring stressing that `_r` in the generator is a label
on a planar wire figure, not anatomy, and that which arm lies on +X is measured.
`make_parts_sheet.py::INSET_JOINTS`, `make_binding_sheet.py::INSET_JOINTS` and
`make_rig_sheet.py::import_reference` each
pinned `shoulder.L / elbow.L / wrist.L / hip.L` and then wrote a subtitle asserting the arc
is "the character's LEFT arm". `make_skeleton_sheet.py:199` already derived its side and is
the pattern the other three now follow.

Nothing raised when the two disagreed: each sheet's liveness andon still passed, because
the OTHER arm moved. On a subject whose +X arm is the right one, four 1:1 insets showed the
joints that did NOT move under a caption calling them "the joints under articulation".

The derivation lives ONCE, in `make_parts_sheet` — the module `make_rig_sheet` and
`rig_retopo` already import `light_the_scene` / `ortho_camera` / `shoot` from — rather than
copied a fourth time.
"""

import ast

import pytest

from blender_stub import blender_stubbed, load_tool, read_source

SHEETS = ("make_parts_sheet.py", "make_binding_sheet.py", "make_rig_sheet.py")


class _Vec(tuple):
    """Enough of `mathutils.Vector` for a displacement measurement."""

    def __sub__(self, other):
        return _Vec(a - b for a, b in zip(self, other))

    def __rmatmul__(self, other):
        return self

    @property
    def length(self):
        return sum(v * v for v in self) ** 0.5

    def copy(self):
        return self


class _PoseBone:
    def __init__(self, heads):
        self._heads = heads
        self.frame = [1]

    @property
    def head(self):
        return _Vec(self._heads[self.frame[0]])


class _Arm:
    """An armature whose pose bones move on ONE side across the arc."""

    def __init__(self, moving_side):
        self.matrix_world = object()
        self._frame = [1]
        self.pose = self
        rest = {"shoulder": (0.1, 0, 1.4), "elbow": (0.2, 0, 1.1),
                "wrist": (0.25, 0, 0.9), "hip": (0.08, 0, 0.9)}
        self.bones = {}
        for joint, p in rest.items():
            for side in ("L", "R"):
                x = p[0] if side == "L" else -p[0]
                moved = (x, 0.0, p[2] + 0.30) if side == moving_side else (x, 0.0, p[2])
                pb = _PoseBone({1: (x, 0.0, p[2]), 33: moved})
                pb.frame = self._frame
                self.bones[f"{joint}.{side}"] = pb

    def __contains__(self, name):
        return name in self.bones

    def __getitem__(self, name):
        return self.bones[name]


class _Scene:
    def __init__(self, arm):
        self._arm = arm

    def frame_set(self, frame):
        self._arm._frame[0] = frame


@pytest.fixture(scope="module")
def mps():
    return load_tool("make_parts_sheet.py")


@pytest.mark.parametrize("moving", ["L", "R"])
def test_the_side_is_measured_from_which_arm_actually_moves(mps, moving):
    arm = _Arm(moving)
    with blender_stubbed():
        rec = mps.articulated_side(arm, _Scene(arm), 1, 33)
    assert rec["side"] == moving
    assert rec["displacement"][moving] > rec["displacement"]["R" if moving == "L" else "L"]


def test_a_subject_whose_right_arm_moves_is_not_captioned_LEFT(mps):
    """The measured consequence, in the words the sheets print."""
    arm = _Arm("R")
    with blender_stubbed():
        rec = mps.articulated_side(arm, _Scene(arm), 1, 33)
    assert mps.side_word(rec["side"]) == "RIGHT"
    assert mps.side_word("L") == "LEFT"


def test_a_rig_in_which_neither_arm_moved_raises(mps):
    """The liveness andons in these sheets pass when the OTHER arm moved, so this is the
    direction none of them bounds. Gates raise; no `assert`, no skip flag."""
    arm = _Arm(None)
    with blender_stubbed():
        with pytest.raises(mps.ArmatureError) as exc:
            mps.articulated_side(arm, _Scene(arm), 1, 33)
    assert "neither" in str(exc.value).lower() or "no arm" in str(exc.value).lower()


def test_two_arms_moving_together_is_refused_rather_than_guessed(mps):
    """A both-arms arc has no single articulated side, and picking one silently is how a
    caption stops describing the picture."""
    arm = _Arm("L")
    arm.bones["shoulder.R"]._heads[33] = (-0.1, 0.0, 1.4 + 0.30)
    arm.bones["elbow.R"]._heads[33] = (-0.2, 0.0, 1.1 + 0.30)
    arm.bones["wrist.R"]._heads[33] = (-0.25, 0.0, 0.9 + 0.30)
    with blender_stubbed():
        with pytest.raises(mps.ArmatureError, match="both arms move"):
            mps.articulated_side(arm, _Scene(arm), 1, 33)


@pytest.mark.parametrize("filename", SHEETS)
def test_no_sheet_pins_a_side_in_a_bone_name(filename):
    src = read_source(filename)
    for pinned in ('"shoulder.L"', "'shoulder.L'", '"elbow.L"', '"wrist.L"', '"hip.L"',
                   '"shoulder.R"', '"elbow.R"', '"wrist.R"', '"hip.R"'):
        assert pinned not in src, f"{filename} still pins {pinned}"


def _emitted_strings(filename):
    """Every string literal a sheet can print, EXCLUDING docstrings.

    A docstring recording what the superseded caption said is the repo's method -- "correct
    in place, with the measurement that overturned the claim" -- and must not be what this
    check fires on. What matters is whether a literal side can reach `panels.json`.
    """
    tree = ast.parse(read_source(filename))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            body = getattr(node, "body", [])
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                docstrings.add(id(body[0].value))
    return [n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and id(n) not in docstrings]


@pytest.mark.parametrize("filename", SHEETS)
def test_no_sheet_captions_a_side_it_did_not_measure(filename):
    for text in _emitted_strings(filename):
        assert "character's LEFT arm" not in text, (
            f"{filename} can emit {text!r}: the character's LEFT arm as a literal, while "
            f"the arc chooses its side by measurement")
        assert "character's RIGHT arm" not in text, (filename, text)


def test_the_emitted_string_scan_would_catch_the_caption_it_was_written_for(tmp_path):
    """The red direction: the superseded line, in a file of its own, must be found."""
    probe = tmp_path / "probe_sheet.py"
    caption = "the arc is E03s: the character's LEFT arm, 0 to 90 about +Y"
    quote = chr(34) * 3
    lines = [quote + "A docstring recording the superseded caption: " + caption + quote,
             "SUB = " + repr(caption),
             ""]
    probe.write_text(chr(10).join(lines), encoding="utf-8")
    tree = ast.parse(probe.read_text(encoding="utf-8"))
    doc = id(tree.body[0].value)
    hits = [n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) != doc
            and "character's LEFT arm" in n.value]
    assert len(hits) == 1, hits


@pytest.mark.parametrize("filename", SHEETS)
def test_every_sheet_derives_the_side_from_the_one_implementation(filename):
    """`make_skeleton_sheet` derives its own from the landmark dict it already holds; these
    three read the rig, and they read it through ONE function."""
    src = read_source(filename)
    assert "articulated_side" in src, filename
    if filename != "make_parts_sheet.py":
        tree = ast.parse(src)
        imports_it = any(
            isinstance(n, ast.ImportFrom) and n.module == "make_parts_sheet"
            and any(a.name == "articulated_side" for a in n.names)
            for n in ast.walk(tree))
        assert imports_it, (
            f"{filename} must import articulated_side from make_parts_sheet, not carry a "
            f"second implementation")


def test_the_fourth_sheet_still_derives_its_own_side():
    """make_skeleton_sheet was already correct and must stay that way."""
    src = read_source("make_skeleton_sheet.py")
    assert 'left_x_sign' in src
    assert 'sheet_subtitle(table, side)' in src
