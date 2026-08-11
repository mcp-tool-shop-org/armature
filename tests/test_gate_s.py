"""Gate S — the seed pre-registration andon.

Gate S guards a defect with **no technical symptom**. Every other check passes on a
seed-shopped run: the frame is legal, the batch is intact, the topology verifies, the
lossless tap is wired, the video comes back looking fine. What is destroyed is the
meaning of the number computed from it — E04 exists to measure how much the tracking
statistic moves when only the seed changes, and a seed chosen after seeing a result
measures selection instead.

So the fixtures here are not about malformed input. They ask: *what would this look like
if the gate were wrong in the specific way that lets a seed through?*

* the gate is checked but only where a registry exists → an experiment that registered
  nothing becomes freely shoppable the moment `--seed` exists (`test_..._no_registry_...`);
* the gate is checked after the uploads are read → a typo'd path raises first and the
  seed is never examined (`test_gate_S_fires_before_anything_is_read_from_disk`);
* the gate is an `assert` → `-O` deletes it and the tool still emits a payload
  (`test_gate_S_survives_optimization`);
* the registry drifts from the spec → the gate binds to a list nobody committed to
  (`test_the_registry_matches_the_seeds_committed_in_the_spec`).
"""

import json
import os
import re
import subprocess
import sys
import textwrap

import pytest

from conftest import REPO, TOOLS

sys.path.insert(0, TOOLS)

import build_payload as bp  # noqa: E402
from armature_core import gates  # noqa: E402
from armature_core.errors import GateSSeedRegistration  # noqa: E402

SPEC = os.path.join(REPO, "docs", "experiments", "E04-the-between-generation-floor.md")
HAVE_E02_UPLOADS = os.path.isfile("outputs/E02/uploads_depth_pershot.json")

# The bases E04's two conditions re-run. C-bright's is A0.json, NOT A1a.json: A1a ran
# before the lossless tap existed and carries no node 302.
E04_BASE = {"C-bright": "A0", "C-dark": "A1b"}
HAVE_E02_PAYLOADS = all(
    os.path.isfile(f"outputs/E02/payloads/{b}.json") for b in E04_BASE.values())


# ------------------------------------------------------- the gate function, in isolation

@pytest.mark.parametrize("seed", bp.E04_SEEDS)
def test_every_pre_registered_seed_passes(seed):
    ev = gates.gate_s_seed_registration(seed, bp.E04_SEEDS, "E04", seed_was_explicit=True)
    assert ev["verdict"] == "seed is pre-registered"
    assert ev["gate"] == "S"


@pytest.mark.parametrize("seed", [
    654654950714626,   # one past a registered seed — the near miss a typo produces
    654654950714623,   # one before
    0,
    -1,
    123456789,
])
def test_an_unregistered_seed_raises(seed):
    with pytest.raises(GateSSeedRegistration, match="not in E04's pre-registered list"):
        gates.gate_s_seed_registration(seed, bp.E04_SEEDS, "E04", seed_was_explicit=True)


def test_an_experiment_with_no_registry_may_not_vary_its_seed():
    """The second direction, and the one that is easy to miss.

    A gate that only checked registered experiments would have opened the door it exists
    to close: E02 and E03 ran on a pinned constant no flag could move, and adding `--seed`
    must not silently make them shoppable.
    """
    with pytest.raises(GateSSeedRegistration, match="may not be varied"):
        gates.gate_s_seed_registration(999, None, "E02", seed_was_explicit=True)


def test_an_experiment_with_no_registry_that_does_not_vary_its_seed_is_NA():
    ev = gates.gate_s_seed_registration(bp.SEED, None, "E02", seed_was_explicit=False)
    assert ev["verdict"].startswith("N/A")


@pytest.mark.parametrize("bad", ["654654950714624", 654654950714624.0, None, True])
def test_a_seed_that_is_not_an_int_raises(bad):
    """`True` is in this list on purpose: `isinstance(True, int)` is True in Python, so a
    bool would otherwise be compared against the registry and reported as an ordinary
    unregistered seed rather than as the type confusion it is."""
    with pytest.raises(GateSSeedRegistration, match="must be an int"):
        gates.gate_s_seed_registration(bad, bp.E04_SEEDS, "E04", seed_was_explicit=True)


# ----------------------------------------------------------------- the gate, in the tool

@pytest.mark.skipif(not HAVE_E02_UPLOADS, reason="E02 upload records are gitignored output")
def test_build_refuses_an_unregistered_seed():
    with pytest.raises(GateSSeedRegistration):
        bp.build("C-bright", "E04", seed=654654950714626)


def test_gate_S_fires_before_anything_is_read_from_disk(monkeypatch):
    """Ordering, and it is a claim only a broken-input fixture can falsify.

    The uploads path is pointed at a file that does not exist. If Gate S ran after the
    uploads were loaded, this would raise `FileNotFoundError` and the seed would never be
    examined — the gate would still 'pass its tests' while guarding nothing on the real
    path, because in practice the payload build always reads disk.
    """
    cfg = dict(bp.EXPERIMENTS["E04"])
    arms = dict(cfg["arms"])
    arms["C-bright"] = dict(arms["C-bright"], uploads="no/such/file.json")
    monkeypatch.setitem(bp.EXPERIMENTS, "E04", dict(cfg, arms=arms))

    with pytest.raises(GateSSeedRegistration):
        bp.build("C-bright", "E04", seed=111)


@pytest.mark.skipif(not HAVE_E02_UPLOADS, reason="E02 upload records are gitignored output")
def test_the_seed_reaches_the_payload_and_the_meta_records_the_verdict():
    """A gate whose verdict is not written down cannot be audited after the fact."""
    seed = bp.E04_SEEDS[3]
    wf, meta = bp.build("C-dark", "E04", seed=seed)
    assert wf["3"]["inputs"]["seed"] == seed
    assert meta["seed"] == seed
    assert meta["gate_S"]["verdict"] == "seed is pre-registered"
    assert meta["gate_S"]["registry_index"] == 3


@pytest.mark.skipif(not HAVE_E02_UPLOADS, reason="E02 upload records are gitignored output")
def test_each_seed_writes_to_its_own_output_names():
    """Six submissions of one arm must not overwrite each other on the server."""
    prefixes = set()
    for seed in bp.E04_SEEDS:
        wf, _ = bp.build("C-bright", "E04", seed=seed)
        prefixes.add(wf["302"]["inputs"]["filename_prefix"])
    assert len(prefixes) == len(bp.E04_SEEDS)


# ------------------------------------------------- E04 really is E02's conditions re-run

@pytest.mark.skipif(not (HAVE_E02_UPLOADS and HAVE_E02_PAYLOADS),
                    reason="E02 payloads are gitignored output")
@pytest.mark.parametrize("arm", sorted(E04_BASE))
@pytest.mark.parametrize("seed", bp.E04_SEEDS)
def test_an_E04_payload_differs_from_its_E02_base_ONLY_in_the_seed(arm, seed):
    """The load-bearing test of the whole experiment.

    A floor measured under conditions that drifted from E02's is not a floor under E02's
    numbers. This compares every node of every submission against the payload actually
    submitted in E02 and permits exactly two kinds of difference: node 3's seed, and the
    three output-name strings that have to differ or the runs would collide.
    """
    wf, _ = bp.build(arm, "E04", seed=seed)
    with open(f"outputs/E02/payloads/{E04_BASE[arm]}.json", encoding="utf-8") as fh:
        base = json.load(fh)

    assert set(wf) == set(base), "E04 changed the graph shape"

    differing = {k for k in wf if wf[k] != base[k]}
    assert differing <= {"3", "114", "301", "302"}, (
        f"E04 {arm} differs from {E04_BASE[arm]} at nodes {sorted(differing)}; only the "
        f"KSampler seed and the three output prefixes may differ")

    # node 3: the seed, and nothing else in it
    assert wf["3"]["inputs"]["seed"] == seed
    assert {k: v for k, v in wf["3"]["inputs"].items() if k != "seed"} == \
           {k: v for k, v in base["3"]["inputs"].items() if k != "seed"}

    # the three name nodes: the prefix, and nothing else in them
    for nid in ("114", "301", "302"):
        assert {k: v for k, v in wf[nid]["inputs"].items() if k != "filename_prefix"} == \
               {k: v for k, v in base[nid]["inputs"].items() if k != "filename_prefix"}


@pytest.mark.skipif(not HAVE_E02_UPLOADS, reason="E02 upload records are gitignored output")
def test_the_two_conditions_differ_ONLY_in_which_control_they_carry():
    """At one seed, C-bright and C-dark must differ by the control and nothing else."""
    seed = bp.E04_SEEDS[1]
    bright, mb = bp.build("C-bright", "E04", seed=seed)
    dark, md = bp.build("C-dark", "E04", seed=seed)

    assert mb["seed"] == md["seed"] == seed
    assert mb["positive"] == md["positive"] and mb["negative"] == md["negative"]
    assert mb["reference_image"] == md["reference_image"]
    assert mb["models"] == md["models"]

    differing = {k for k in bright if bright[k] != dark[k]}
    assert differing <= ({str(200 + i) for i in range(33)} | {"114", "301", "302"})
    assert mb["control"]["distinct_images"] == md["control"]["distinct_images"] == 33


# -------------------------------------------------------- the registry is the committed list

def test_the_registry_matches_the_seeds_committed_in_the_spec():
    """`E04_SEEDS` must be the list in the spec, or Gate S binds to something nobody
    committed to and the pre-registration is decoration."""
    with open(SPEC, encoding="utf-8") as fh:
        text = fh.read()
    block = re.search(r"### Pre-registered seeds.*?```(.*?)```", text, re.S)
    assert block, "the spec no longer carries a fenced pre-registered seed block"
    committed = [int(m) for m in re.findall(r"^\s*(\d{10,})", block.group(1), re.M)]
    assert committed == list(bp.E04_SEEDS), (
        f"the spec commits {committed} but Gate S enforces {list(bp.E04_SEEDS)}")


def test_the_registry_has_no_duplicates_and_holds_six_seeds():
    assert len(set(bp.E04_SEEDS)) == len(bp.E04_SEEDS) == 6
    assert bp.SEED == bp.E04_SEEDS[0], (
        "seed 1 of both conditions is E02's pinned seed; A0 and A1b join E04 on it")


# ------------------------------------------------------------------ it survives -O

PROBE = textwrap.dedent(
    """
    import json, sys
    sys.path.insert(0, sys.argv[1])
    import build_payload as bp
    from armature_core.errors import GateSSeedRegistration

    result = {"optimize_flag": sys.flags.optimize, "asserts_active": __debug__}
    try:
        bp.build("C-bright", "E04", seed=int(sys.argv[2]))
        result["outcome"] = "NO_RAISE"
    except GateSSeedRegistration:
        result["outcome"] = "GATE_S_RAISED"
    except BaseException as exc:
        result["outcome"] = "WRONG_ERROR"
        result["message"] = f"{type(exc).__name__}: {exc}"
    print("RESULT " + json.dumps(result))
    """
)


def _run(tmp_path, seed, *, flag=False, env_var=False):
    script = tmp_path / "probe_s.py"
    script.write_text(PROBE, encoding="utf-8")
    env = dict(os.environ)
    env.pop("PYTHONOPTIMIZE", None)
    if env_var:
        env["PYTHONOPTIMIZE"] = "1"
    cmd = [sys.executable] + (["-O"] if flag else []) + [str(script), TOOLS, str(seed)]
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=180,
                          cwd=REPO)
    assert proc.returncode == 0, proc.stderr
    line = [l for l in proc.stdout.splitlines() if l.startswith("RESULT ")]
    assert line, proc.stdout + proc.stderr
    return json.loads(line[-1][len("RESULT "):])


@pytest.mark.parametrize("flag,env_var,label", [
    (False, False, "plain"), (True, False, "-O"), (False, True, "PYTHONOPTIMIZE=1")])
def test_gate_S_survives_optimization(tmp_path, flag, env_var, label):
    """87 of facet's ANDONs turned out to be removable by an environment variable. This
    is the test that says do not add the 88th."""
    res = _run(tmp_path, 654654950714626, flag=flag, env_var=env_var)
    assert res["outcome"] == "GATE_S_RAISED", f"{label}: {res}"


def test_the_optimization_actually_took_effect(tmp_path):
    """A green result that proves nothing because -O never applied is not a result."""
    plain = _run(tmp_path, 654654950714626, flag=False, env_var=False)
    flagged = _run(tmp_path, 654654950714626, flag=True, env_var=False)
    env = _run(tmp_path, 654654950714626, flag=False, env_var=True)
    assert plain["asserts_active"] is True and plain["optimize_flag"] == 0
    assert flagged["asserts_active"] is False and flagged["optimize_flag"] >= 1
    assert env["asserts_active"] is False and env["optimize_flag"] >= 1
