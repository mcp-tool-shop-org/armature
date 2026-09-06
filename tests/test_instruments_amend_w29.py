"""Wave 29, the instruments domain: three approved Stage D findings.

F-136d6860 — constant-string refusals that drop measured quantities already in
their evidence dicts. F-2e888f20 — the same shape on rig_bake's four ordinary-use
refusals. F-ab1018ff — wait/progress lines on stderr during remesh/bake, and
`elapsed_s` in those two tools' manifests.

Each check is a PROPERTY over a DERIVED population (clause word / print site /
manifest key), never a list of remembered line numbers. Helpers under `tests/`
raise; they never `assert` outside a test function.
"""

import ast
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

TESTS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TESTS)
TOOLS = os.path.join(REPO, "tools")


def source(rel):
    with open(os.path.join(TOOLS, rel), encoding="utf-8") as fh:
        return fh.read()


def tree(rel):
    return ast.parse(source(rel))


def refusals_by_clause(rel):
    """`{clause word: (message node, {evidence keys})}` for every `raise` whose
    second argument is an evidence dict literal carrying `clause`."""
    out = {}
    for node in ast.walk(tree(rel)):
        if not (isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call)):
            continue
        args = node.exc.args
        if len(args) < 2 or not isinstance(args[1], ast.Dict):
            continue
        keys = {k.value: v for k, v in zip(args[1].keys, args[1].values)
                if isinstance(k, ast.Constant) and isinstance(k.value, str)}
        clause = keys.get("clause")
        if isinstance(clause, ast.Constant) and isinstance(clause.value, str):
            out[clause.value] = (args[0], set(keys))
    return out


def message_names_number(msg):
    """True when the raise message is an f-string (JoinedStr) — i.e. it
    interpolates at least one operand rather than stating a constant sentence."""
    return isinstance(msg, ast.JoinedStr)


# =======================================================================================
# F-136d6860 — domain-wide constant-message half at the six named sites
# =======================================================================================

#: `(module, clause word, evidence key that must ride beside the interpolated value)`.
CONSTANT_MESSAGE_SITES = (
    ("rig_repair.py", "still_not_manifold_after_repair", "final"),
    ("rig_repair.py", "repair_removed_too_much", "faces_removed"),
    ("rig_retopo.py", "quadriflow_declined", "target_faces"),
    ("rig_retopo.py", "no_retopo_route_produced_a_mesh", "results"),
    ("author_walk.py", "keying_produced_no_action", "n_frames"),
    ("lift_solve.py", "keying_produced_no_action", "n_frames"),
)


@pytest.mark.parametrize("rel,clause,ev_key", CONSTANT_MESSAGE_SITES)
def test_the_named_constant_message_sites_interpolate_their_evidence(rel, clause, ev_key):
    """F-136d6860. Message is JoinedStr; evidence still carries the operand."""
    found = refusals_by_clause(rel)
    assert clause in found, f"{rel} has no raise with clause {clause!r}"
    msg, keys = found[clause]
    assert message_names_number(msg), (
        f"{rel}:{clause} still states a constant string; measured value never reaches "
        f"the sentence an operator reads")
    assert ev_key in keys, (
        f"{rel}:{clause} evidence does not carry {ev_key!r}; keys={sorted(keys)}")


def test_no_retopo_quotes_both_arm_failure_strings():
    """F-136d6860 at rig_retopo's both-arms-failed site: the sentence names A and B."""
    src = source("rig_retopo.py")
    assert "A_quadriflow_direct=" in src and "B_voxel_then_quadriflow=" in src, src
    found = refusals_by_clause("rig_retopo.py")
    msg, keys = found["no_retopo_route_produced_a_mesh"]
    assert message_names_number(msg)
    assert {"A_FAILED", "B_FAILED"} <= keys, sorted(keys)


def test_the_predicate_reports_a_constant_message_beside_populated_evidence(tmp_path):
    """REVERTED-RED for F-136d6860: the pre-fix shape through the same walk."""
    p = tmp_path / "probe_constant.py"
    p.write_text(
        "class G(Exception):\n"
        "    def __init__(self, msg, ev):\n"
        "        super().__init__(msg)\n"
        "        self.evidence = ev\n"
        "def f(removed, of, budget):\n"
        "    raise G('repair removed more of the character than a stitch-fixing "
        "pass should',\n"
        "            {'clause': 'repair_removed_too_much',\n"
        "             'faces_removed': removed, 'of': of,\n"
        "             'budget_fraction': budget})\n", encoding="utf-8")
    t = ast.parse(p.read_text(encoding="utf-8"))
    msgs = [n.exc.args[0] for n in ast.walk(t)
            if isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call)
            and len(n.exc.args) >= 2]
    assert len(msgs) == 1
    assert isinstance(msgs[0], ast.Constant)
    assert not isinstance(msgs[0], ast.JoinedStr)


# =======================================================================================
# F-2e888f20 — rig_bake's four ordinary-use refusals
# =======================================================================================

BAKE_REFUSALS = (
    ("unwrap produced UV area fraction", "uv_area_fraction"),  # UnwrapFailed; rec dict
    ("no_image_texture_node_to_bake_into", "materials"),
    ("bake_operator_declined", "returned"),
    ("baked_atlas_is_mostly_empty", "non_black_fraction"),
)


def test_rig_bake_unwrap_refusal_names_the_fraction_and_the_floor():
    """F-2e888f20 site 1. UnwrapFailed message interpolates area and UV_AREA_FLOOR."""
    src = source("rig_bake.py")
    assert "UV_AREA_FLOOR" in src
    # The raise is built from a JoinedStr; walk the unwrap function.
    fn = next(n for n in tree("rig_bake.py").body
              if isinstance(n, ast.FunctionDef) and n.name == "unwrap")
    raises = [n for n in ast.walk(fn)
              if isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call)]
    assert raises, "unwrap has no raise"
    assert isinstance(raises[0].exc.args[0], ast.JoinedStr), (
        "unwrap still states a constant UV-area sentence")
    assert "against a floor of" in src


def test_rig_bake_four_refusals_name_measured_value_threshold_and_lever():
    """F-2e888f20. The three BakeEmpty clauses plus the unwrap sentence."""
    found = refusals_by_clause("rig_bake.py")
    offenders = {}
    for clause, ev_key in BAKE_REFUSALS[1:]:
        if clause not in found:
            offenders[clause] = "no raise carries this clause"
            continue
        msg, keys = found[clause]
        if not message_names_number(msg):
            offenders[clause] = "the message is a constant string"
        elif ev_key not in keys:
            offenders[clause] = f"evidence does not carry {ev_key!r}"
    assert offenders == {}, offenders
    src = source("rig_bake.py")
    assert "--max-deviation=" in src, (
        "mostly-empty / declined bake sentences must name the operator's cage lever")
    assert "ATLAS_LIT_FLOOR" in src


def test_rig_bake_mostly_empty_names_frac_floor_cage_and_flag():
    """The worst ordinary-use halt: lit fraction, floor, cage, --max-deviation."""
    src = source("rig_bake.py")
    assert "lit against a floor of" in src
    assert "derived from --max-deviation=" in src
    found = refusals_by_clause("rig_bake.py")
    msg, keys = found["baked_atlas_is_mostly_empty"]
    assert message_names_number(msg)
    assert {"non_black_fraction", "floor", "cage", "max_deviation"} <= keys, sorted(keys)


# =======================================================================================
# F-ab1018ff — progress on stderr during remesh/bake; elapsed_s in manifests
# =======================================================================================


def stderr_progress_prints(rel):
    """`print(..., file=sys.stderr, flush=True)` call nodes in `rel`."""
    out = []
    for node in ast.walk(tree(rel)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Name) and func.id == "print"):
            continue
        kwargs = {kw.arg: kw.value for kw in node.keywords if kw.arg}
        file_kw = kwargs.get("file")
        flush_kw = kwargs.get("flush")
        if file_kw is None or flush_kw is None:
            continue
        if not (isinstance(file_kw, ast.Attribute)
                and isinstance(file_kw.value, ast.Name)
                and file_kw.value.id == "sys" and file_kw.attr == "stderr"):
            continue
        if not (isinstance(flush_kw, ast.Constant) and flush_kw.value is True):
            continue
        out.append(node)
    return out


def test_rig_retopo_and_bake_print_lowercase_progress_before_heavy_ops():
    """F-ab1018ff. One stderr progress line before each unbounded Blender operator."""
    retopo = source("rig_retopo.py")
    bake = source("rig_bake.py")
    assert "rig_retopo voxel_remesh on" in retopo
    assert "rig_retopo quadriflow on" in retopo
    assert "rig_retopo panel" in retopo
    assert "rig_bake unwrap on" in bake
    assert "rig_bake bake selected-to-active on" in bake
    for rel in ("rig_retopo.py", "rig_bake.py"):
        prints = stderr_progress_prints(rel)
        assert prints, f"{rel} has no stderr flush=True progress print"
        # None of the progress formats may lead with an uppercase token that would
        # join the success-sentinel census.
        for node in prints:
            # First positional arg is the f-string / constant; if Constant, must be lower.
            if node.args and isinstance(node.args[0], ast.Constant):
                assert isinstance(node.args[0].value, str)
                assert node.args[0].value[:1].islower(), node.args[0].value


def test_rig_retopo_and_bake_manifests_record_elapsed_s():
    """F-ab1018ff. Total wall time rides the manifest, matching render_turnaround."""
    for rel in ("rig_retopo.py", "rig_bake.py"):
        src = source(rel)
        assert '"elapsed_s"' in src or "'elapsed_s'" in src, rel
        # Bound to time.time() - t0, not a hardcoded number.
        assert "time.time() - t0" in src, rel


def test_progress_lines_are_not_sentinels():
    """A progress line that looks like RIG_BAKE_OK takes the pairing census red."""
    import test_instruments_amend_w10 as W10
    assert sorted(W10.success_tokens("rig_bake.py")) == ["RIG_BAKE_OK"]
    assert sorted(W10.success_tokens("rig_retopo.py")) == ["RIG_RETOPO_OK"]


def test_the_pre_fix_shape_has_no_stderr_progress(tmp_path):
    """REVERTED-RED for F-ab1018ff: a module that only prints the sentinel."""
    p = tmp_path / "probe_silent.py"
    p.write_text(
        "import sys\n"
        "def main():\n"
        "    print('RIG_PROBE_OK {}')\n", encoding="utf-8")
    t = ast.parse(p.read_text(encoding="utf-8"))
    prints = [n for n in ast.walk(t)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
              and n.func.id == "print"]
    assert len(prints) == 1
    assert not any(kw.arg == "file" for kw in prints[0].keywords)
