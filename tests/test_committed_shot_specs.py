"""Every committed shot spec still loads under the contract `shotspec` actually enforces.

Wave 3, coordinator relay from the core-gates domain. `normalise_spec` is being taught to
(a) REFUSE any `spec['gates']` key — the G4 tolerance moves out of the spec and into
`gates.G4_TOLERANCE_PX`, because a spec must not be able to widen the tolerance that judges
it — and (b) REQUIRE `asset.sha256`, because a recipe that does not name the bytes it ran on
is not a recipe.

Five committed specs carried `"gates": {"g4_tolerance_px": 2}`. Every one of them was the
DEFAULT value (`shotspec.DEFAULTS["gates"]["g4_tolerance_px"]` is 2), so deleting the row
changes nothing about what those experiments ran — the check below pins that the rows are
gone rather than that the number moved.

Nothing here type-checks a spec by hand: the shot specs are selected from `specs/*.json` by
the presence of `spec_version`, so a spec added later joins these checks or fails the first
one.
"""

import glob
import json
import os

import pytest

from conftest import TOOLS  # noqa: F401
from armature_core import shotspec

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALL_SPECS = sorted(glob.glob(os.path.join(REPO, "specs", "*.json")))


def _raw(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


SHOT_SPECS = [p for p in ALL_SPECS
              if isinstance(_raw(p), dict) and "spec_version" in _raw(p)]


def test_the_shot_specs_are_found_at_all():
    """A selector that matched nothing would make every check below vacuously green."""
    assert [os.path.basename(p) for p in SHOT_SPECS] == [
        "E01-anchor-blackguard.json", "E01-anchor.json", "E02-control-blackguard.json",
        "E03-posearc.json", "E03-static.json"]


@pytest.mark.parametrize("path", SHOT_SPECS, ids=os.path.basename)
def test_no_committed_shot_spec_carries_a_gates_row(path):
    """The tolerance that judges a shot may not be a value the shot supplies. All five
    rows were the default, so their deletion moved no number."""
    assert "gates" not in _raw(path), (
        f"{os.path.basename(path)} still carries a gates row; the G4 tolerance lives in "
        f"armature_core.gates, not in the spec it judges")


@pytest.mark.parametrize("path", SHOT_SPECS, ids=os.path.basename)
def test_every_committed_shot_spec_loads(path):
    """The contract check itself. It is what keeps the committed specs and the loader from
    drifting apart silently — the drift this relay exists to close."""
    spec = shotspec.normalise_spec(_raw(path), spec_path=path)
    assert spec["name"]
    assert spec["asset"]["path"]


def _unhashable(path):
    """True when a spec pins no sha256 AND the file it names is not on this rig.

    Derived from the data rather than a typed list of names: the moment a spec's path is
    corrected to something that resolves, the xfail below disappears on its own and the
    check binds.
    """
    asset = _raw(path).get("asset") or {}
    return not asset.get("sha256") and not os.path.isfile(asset.get("path") or "")


PINNING_PENDING = pytest.mark.xfail(
    strict=True,
    reason=("no sha256 committed and the asset path does not resolve on this rig. The "
            "hash is deliberately NOT invented — see the docstring below. Marked strict "
            "so pinning it turns this into a failure and forces the marker out"))

_PIN_CASES = [pytest.param(p, marks=[PINNING_PENDING] if _unhashable(p) else [],
                           id=os.path.basename(p))
              for p in SHOT_SPECS]


@pytest.mark.parametrize("path", _PIN_CASES)
def test_every_committed_shot_spec_pins_its_assets_bytes(path):
    """A recipe that does not name the bytes it ran on is not a recipe.

    `E03-posearc.json` and `E03-static.json` name an asset at
    `E:\\AI\\armature-E03\\outputs\\E03\\subject\\wire_t030_armraise.glb`, a path that does
    not exist on this rig — the repo moved and the spec's path did not. A same-named file
    sits at `outputs/E03/subject/wire_t030_armraise.glb` inside this repo, but `outputs/`
    is gitignored and nothing establishes it is the artifact those runs used, so no hash is
    written here. Pinning one would be inventing a fact about a file the spec does not
    name. The path and the hash are one decision and it is the Director's; until he makes
    it, those two specs are refused at load by the tightened contract and this check says
    so out loud rather than passing.

    The three specs that DO pin a hash are checked against the actual bytes below, so this
    is not a check that the key merely exists.
    """
    raw = _raw(path)
    asset = raw.get("asset") or {}
    sha = asset.get("sha256")
    assert isinstance(sha, str) and len(sha) == 64, (
        f"{os.path.basename(path)} does not pin its asset's sha256")
    if os.path.isfile(asset["path"]):
        assert shotspec.sha256_file(asset["path"]) == sha, (
            f"{os.path.basename(path)} pins a sha256 the named file does not have")
