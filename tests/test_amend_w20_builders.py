"""Wave 20 · builders — F-dba1bcd8, the one approved paid-path CRITICAL.

**The defect, as the auditor measured it.** `gate_saved_graph.payload_digests` reads exactly
one key name, `payload_sha256`, at full 64-hex length, and `route_facts` compares what it
finds against `sha256(json.dumps(api_graph, sort_keys=True, separators=(',',':')))`. FOUR of
the nine builders wrote that digest; FIVE did not — `build_r2v_payload` (the hosted partner
tier that bills per submission), `build_lora_arm_payload` (the one arm whose graph loads a
CONDITIONAL licence component), `build_t2v_payload`, `build_assembly_payload` and
`build_cascade_payload`. With none present, `route_facts` records `payload_sha256: null`,
`source` reads "the facts below are NOT tied to the graph being admitted", and the wave-18
tie clause `record_describes_a_different_graph` CANNOT FIRE. Two of the five wrote a
different digest under a different key (`build_t2v_payload`'s `graph.sha256`,
`build_lora_arm_payload`'s `graph_sha256`) — both over the pretty-printed FILE, measured not
equal to the canonical digest, so renaming them would not have closed it.

**Wave 18's five rules, applied here.**

1. *A census keys on the RESOLVED shape, never the spelled one.* The census below does not
   look for the string `payload_sha256` in a builder's source. It DRIVES each builder's
   `main()`, reads the record it wrote beside the graph it wrote, and asserts
   `payload_digests(record) == [canonical_payload_digest(graph)]` — the resolved output. The
   static half asserts the resolved CALL: every computed `payload_sha256` entry in every
   builder is a call whose name resolves, in that module's own namespace, to the ONE
   function object, and no builder spells the canonical digest inline a second time.
2. *A fix's red proof runs against its SIBLINGS.* Every test here is parametrized over the
   whole `build_*payload*.py` family enumerated by glob — all nine, not the one the finding
   names. Pre-fix, five of the nine go red on the operand and four pass.
3. *A refusal names the andon that pulled.* The tie clause is asserted by name
   (`record_describes_a_different_graph`), on the class `RouteGate`, with its evidence keys.
4. *Reverted-red, and the halt line READ.* `test_the_halt_line_reads_the_tie_clause` drives
   `gate_saved_graph.py`'s own `__main__` in a subprocess and reads the printed
   `SAVED_ADMISSION_HALT` record.
5. The `family:` line is in the wave-20 output entry.

Every module under test is imported through `conftest`'s `tools/` path insert, so the code
exercised is THIS worktree's.
"""

import ast
import glob
import importlib
import json
import os

import pytest

from armature_core import route_gates as RG

import build_assembly_payload as BAP
import gate_saved_graph as GSG

from conftest import upload_record
from test_amend_w18_builders import _gsg_halt
from test_canon_spend import ESCAPE, STUB_IDENTITY, _authored_png, _banked_negative

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
REPO = os.path.dirname(TOOLS)
SPECS = os.path.join(REPO, "specs")

BUILDER_GLOB = "build_*payload*.py"


def _builder_names():
    """The population, enumerated from the tree — never typed.

    Rule 2's population: a builder added later joins these checks whether or not anyone
    remembers to add it, and a builder that stops writing the digest fails here.
    """
    names = sorted(os.path.basename(p)[:-3]
                   for p in glob.glob(os.path.join(TOOLS, BUILDER_GLOB)))
    assert len(names) >= 9, f"the glob found only {names}; it is not reaching tools/"
    return names


BUILDERS = _builder_names()


def test_the_population_is_the_nine_builders_the_finding_names():
    assert BUILDERS == [
        "build_animate_payload", "build_assembly_payload", "build_camera_i2v_payload",
        "build_cascade_payload", "build_i2v_payload", "build_lora_arm_payload",
        "build_payload", "build_r2v_payload", "build_t2v_payload"]


# ======================================================== driving each builder to its record
#
# One recipe per builder, returning `(record_path, graph_path)` — the two files a paid
# submission is assembled from. The fixture shapes are `tests/test_canon_spend.py`'s, reused
# rather than re-spelled: the identity clause is read from an absolute path into a sibling
# repo and is stubbed exactly as that file stubs it; everything else in each `main()` is the
# real code path.


def _out_pair(out_dir):
    """The record and the api graph a builder wrote into its own output directory."""
    records = sorted(glob.glob(os.path.join(str(out_dir), "*payload-record.json")))
    graphs = sorted(glob.glob(os.path.join(str(out_dir), "*.api.json")))
    assert len(records) == 1, records
    assert len(graphs) == 1, graphs
    return records[0], graphs[0]


def _drive_build_payload(tmp_path, monkeypatch):
    import build_payload as bp

    out = tmp_path / "run" / "B2.json"
    bp.main(["--experiment", "E03", "--arm", "B2", "--out", str(out), *ESCAPE])
    return str(out.parent / "B2.meta.json"), str(out)


def _drive_build_t2v_payload(tmp_path, monkeypatch):
    import build_t2v_payload as bt

    seeds = tmp_path / "seeds.json"
    seeds.write_text(json.dumps({"seeds": [2026081201]}), encoding="utf-8")
    out = tmp_path / "t2v"
    bt.main([f"--seeds={seeds}", f"--out={out}", *ESCAPE])
    return _out_pair(out)


def _drive_build_lora_arm_payload(tmp_path, monkeypatch):
    import build_lora_arm_payload as bl

    base = os.path.join(REPO, "tests", "fixtures", "E12-w3-camera-i2v.api.json")
    out = tmp_path / "e14"
    bl.main([f"--base={base}", "--arm=T", f"--out={out}",
             f"--seeds-registry={os.path.join(SPECS, 'E14-seeds.json')}",
             "--seed=2026081233", *ESCAPE])
    return _out_pair(out)


def _drive_build_animate_payload(tmp_path, monkeypatch):
    import build_animate_payload as BAP_ANIM

    neg = _banked_negative(tmp_path)
    up = tmp_path / "uploads.json"
    up.write_text(json.dumps({"reference": "r.png", "pose_pack": "p.png",
                              "pose_frames": 65}), encoding="utf-8")
    monkeypatch.setattr(BAP_ANIM, "identity_clause",
                        lambda *a, **k: (STUB_IDENTITY, "orig", []))
    out = tmp_path / "e08"
    BAP_ANIM.main([f"--uploads={up}", f"--out={out}", f"--negative-source={neg}",
                   "--seed=2026081211",
                   f"--seeds-registry={os.path.join(SPECS, 'E08-seeds.json')}", *ESCAPE])
    return _out_pair(out)


def _drive_build_i2v_payload(tmp_path, monkeypatch):
    import build_animate_payload as E08
    import build_i2v_payload as bi

    monkeypatch.setattr(E08, "identity_clause", lambda *a, **k: (STUB_IDENTITY, "orig", []))
    neg = _banked_negative(tmp_path)
    up = tmp_path / "uploads.json"
    up.write_text(json.dumps({"start_frame": "start.png"}), encoding="utf-8")
    e08 = tmp_path / "E08-record.json"
    e08.write_text(json.dumps({
        "experiment": "E08", "seed": 2026081211,
        "positive": STUB_IDENTITY + ". " + E08.SCENE_CLAUSE,
        "negative": E08.read_negative(str(neg))}), encoding="utf-8")
    out = tmp_path / "e11"
    start = tmp_path / "start.png"
    _authored_png(start, (bi.WIDTH, bi.HEIGHT))
    bi.main([f"--uploads={up}", f"--out={out}", f"--negative-source={neg}",
             f"--e08-record={e08}", f"--start-frame={start}",
             f"--seeds-registry={os.path.join(SPECS, 'E11-seeds.json')}", *ESCAPE])
    return _out_pair(out)


def _drive_build_camera_i2v_payload(tmp_path, monkeypatch):
    import build_animate_payload as E08
    import build_camera_i2v_payload as bc
    from test_build_camera_i2v_payload import w1_record

    monkeypatch.setattr(E08, "identity_clause", lambda *a, **k: (STUB_IDENTITY, "orig", []))
    neg = _banked_negative(tmp_path)
    up = tmp_path / "uploads.json"
    up.write_text(json.dumps({"start_frame": "w3_start.png"}), encoding="utf-8")
    w1 = tmp_path / "E11-probe-payload-record.json"
    w1.write_text(json.dumps(w1_record()), encoding="utf-8")
    start = tmp_path / "w3_start.png"
    _authored_png(start, (bc.WIDTH, bc.HEIGHT))
    out = tmp_path / "e12"
    bc.main([f"--uploads={up}", f"--out={out}", f"--negative-source={neg}",
             f"--w1-record={w1}", f"--start-frame={start}",
             f"--seeds-registry={os.path.join(SPECS, 'E12-seeds.json')}", *ESCAPE])
    return _out_pair(out)


def _drive_build_r2v_payload(tmp_path, monkeypatch):
    import build_r2v_payload as br
    from test_r2v_payload import NEG, PROMPT, REFS, SEEDS

    seeds = tmp_path / "seeds.json"
    seeds.write_text(json.dumps({"seeds": SEEDS}), encoding="utf-8")
    prompt = tmp_path / "prompt.json"
    prompt.write_text(json.dumps({"prompt": PROMPT, "negative_prompt": NEG}),
                      encoding="utf-8")
    refs = tmp_path / "refs.json"
    refs.write_text(json.dumps({"views": [
        {"slot": f"image{i + 1}", "view": f"turn_{i}", "upload_name": REFS[i]}
        for i in range(4)]}), encoding="utf-8")
    out = tmp_path / "e13"
    br.main(["--arm=A1", f"--seed={SEEDS[0]}", f"--seeds={seeds}",
             f"--prompt-file={prompt}", f"--refs={refs}", f"--out={out}", *ESCAPE])
    return _out_pair(out)


def _drive_build_assembly_payload(tmp_path, monkeypatch):
    import build_assembly_payload as ba

    small = tmp_path / "uploads_small.json"
    small.write_text(json.dumps({f"{i:05d}": f"srv_{i:05d}.png" for i in range(5)}),
                     encoding="utf-8")
    out = tmp_path / "assembled"
    ba.main(["--uploads", str(small), "--out", str(out)])
    return _out_pair(out)


def _drive_build_cascade_payload(tmp_path, monkeypatch):
    import build_cascade_payload as bcas

    out = tmp_path / "cascaded"
    bcas.main(["--uploads", upload_record("outputs/E02/uploads_depth_pershot.json"),
               "--out", str(out)])
    return _out_pair(out)


#: builder module -> the recipe that drives its `main()` and hands back the record and the
#: graph it wrote. The census below is the family assertion: a builder with no behavioural
#: drive here would be a builder whose record nothing in this file ever reads.
DRIVES = {
    "build_animate_payload": _drive_build_animate_payload,
    "build_assembly_payload": _drive_build_assembly_payload,
    "build_camera_i2v_payload": _drive_build_camera_i2v_payload,
    "build_cascade_payload": _drive_build_cascade_payload,
    "build_i2v_payload": _drive_build_i2v_payload,
    "build_lora_arm_payload": _drive_build_lora_arm_payload,
    "build_payload": _drive_build_payload,
    "build_r2v_payload": _drive_build_r2v_payload,
    "build_t2v_payload": _drive_build_t2v_payload,
}


def test_every_builder_in_the_population_has_a_behavioural_drive():
    """The census, not a spot check: the nine enumerated by glob and the nine driven here
    are the same set, so a builder cannot join the family and skip the digest check."""
    assert sorted(DRIVES) == BUILDERS, sorted(set(DRIVES) ^ set(BUILDERS))


# ==================================================== the resolved output: one digest, tied


@pytest.mark.parametrize("name", BUILDERS)
def test_every_builder_record_carries_the_canonical_digest_of_its_own_graph(
        name, tmp_path, monkeypatch):
    """Rule 1, the resolved shape: the record is READ, not the source text.

    What this looks like if the code were wrong in the specific way F-dba1bcd8 measured:
    `payload_digests` finds nothing in the record, `route_facts` reports `payload_sha256:
    null`, and the two facts that admit a paid submission are tied to no graph at all.
    """
    record_path, graph_path = DRIVES[name](tmp_path, monkeypatch)
    with open(record_path, encoding="utf-8") as fh:
        doc = json.load(fh)
    with open(graph_path, encoding="utf-8") as fh:
        wf = json.load(fh)

    canonical = BAP.canonical_payload_digest(wf)
    assert GSG.payload_digests(doc) == [canonical], (
        f"{name} wrote {GSG.payload_digests(doc)}; the graph it wrote beside it hashes to "
        f"{canonical}")

    facts = GSG.route_facts(record_path, wf)
    assert facts["payload_sha256"] == canonical
    assert facts["api_payload_sha256"] == canonical
    assert facts["source"].endswith(
        f"tied: the record's `payload_sha256` {canonical} is the digest of the api graph "
        f"this admission vouches for")


@pytest.mark.parametrize("name", BUILDERS)
def test_the_tie_clause_fires_on_every_builder_record_against_a_different_graph(
        name, tmp_path, monkeypatch):
    """The direction that could not fire: the record paired with a graph it does not
    describe. Rule 3 — the refusal is asserted by the andon that pulled and the clause that
    matches its message, not by the bare base."""
    record_path, graph_path = DRIVES[name](tmp_path, monkeypatch)
    with open(graph_path, encoding="utf-8") as fh:
        wf = json.load(fh)
    other = dict(wf)
    other["999999"] = {"class_type": "PreviewImage", "inputs": {"images": ["1", 0]}}

    with pytest.raises(RG.RouteGate) as exc:
        GSG.route_facts(record_path, other)
    ev = exc.value.evidence
    assert ev["clause"] == "record_describes_a_different_graph", ev
    assert ev["declared_payload_sha256"] == BAP.canonical_payload_digest(wf)
    assert ev["api_payload_sha256"] == BAP.canonical_payload_digest(other)
    assert ev["declared_payload_sha256"] != ev["api_payload_sha256"]


# ============================================================== the ONE function, resolved


def test_every_builder_and_the_gate_resolve_the_same_digest_function_object():
    """Rule 1's static half: not "each spells the same expression" but "there is ONE
    function", reached by identity of the object each module's namespace resolves.

    The auditor measured the cost of the other shape: two builders hashed the
    pretty-printed FILE under their own key names, which reads as a digest and compares
    equal to nothing this gate computes.
    """
    one = BAP.canonical_payload_digest
    for name in BUILDERS:
        mod = importlib.import_module(name)
        assert getattr(mod, "canonical_payload_digest", None) is one, (
            f"{name} does not resolve the one digest function")
    assert GSG.canonical_payload_digest is one, (
        "gate_saved_graph compares against a digest it spells itself; the record's digest "
        "and the gate's comparison must be the same function")


def _payload_sha256_values(tree):
    """Every dict-literal value keyed `payload_sha256`, in source order."""
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key, value in zip(node.keys, node.values):
            if isinstance(key, ast.Constant) and key.value == "payload_sha256":
                out.append(value)
    return out


def _called_name(func):
    return func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")


@pytest.mark.parametrize("name", BUILDERS)
def test_every_computed_payload_sha256_is_the_one_resolved_call(name):
    """The census keys on the RESOLVED CALL, not the key name.

    A builder could carry the key and fill it from anything — the pretty-printed file
    digest, a truncated copy, a constant. What is asserted is that every `payload_sha256`
    entry built by a CALL calls the one function object, and that at least one such entry
    exists.
    """
    with open(os.path.join(TOOLS, name + ".py"), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    mod = importlib.import_module(name)

    values = _payload_sha256_values(tree)
    calls = [v for v in values if isinstance(v, ast.Call)]
    assert calls, f"{name} computes no `payload_sha256` at all; values were {values}"
    for call in calls:
        called = _called_name(call.func)
        assert called == "canonical_payload_digest", (
            f"{name}:{call.lineno} fills `payload_sha256` from {called!r}")
        assert getattr(mod, called, None) is BAP.canonical_payload_digest, (
            f"{name}:{call.lineno} resolves {called!r} to something else")


def _inline_canonical_digest_sites(path):
    """`hashlib.sha256(json.dumps(..., separators=...))` — the canonical digest, spelled.

    Returned as `(lineno, enclosing function name)`. `separators` is what discriminates the
    canonical derivation from the other json hashes in this family — `build_r2v_payload`'s
    `prompt_sha256` hashes a prompt spec with `sort_keys` only and is not a graph digest at
    all, so a census keyed on `sha256(json.dumps(...))` alone would count it.
    """
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    enclosing = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for child in ast.walk(node):
                enclosing.setdefault(id(child), node.name)
    sites = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and _called_name(node.func) == "sha256"):
            continue
        for inner in ast.walk(node):
            if (isinstance(inner, ast.Call) and _called_name(inner.func) == "dumps"
                    and any(k.arg == "separators" for k in inner.keywords)):
                sites.append((node.lineno, enclosing.get(id(node), "<module>")))
    return sites


#: The one place the derivation is allowed to be spelled: the body of the one function.
THE_ONE_HOME = ("build_assembly_payload", "canonical_payload_digest")


@pytest.mark.parametrize("name", BUILDERS + ["gate_saved_graph"])
def test_the_canonical_digest_is_spelled_in_exactly_one_place(name):
    """"Reuse it, never a second spelling." The four builders that already wrote the digest
    each carried their own copy of the expression and `route_facts` carried a fifth — five
    places for the derivation to drift from the one the gate compares against. What is
    asserted is not "nobody spells it" but "it is spelled once, inside the function every
    other site calls"."""
    sites = _inline_canonical_digest_sites(os.path.join(TOOLS, name + ".py"))
    allowed = [(ln, fn) for ln, fn in sites
               if name == THE_ONE_HOME[0] and fn == THE_ONE_HOME[1]]
    assert sites == allowed, (
        f"{name} spells `hashlib.sha256(json.dumps(..., separators=...))` inline at "
        f"{sites}; the derivation has one home, {THE_ONE_HOME[0]}.{THE_ONE_HOME[1]}")
    if name == THE_ONE_HOME[0]:
        assert len(allowed) == 1, (
            f"the one home spells the derivation {len(allowed)} times: {allowed}")


def test_the_one_home_is_where_the_derivation_actually_lives():
    """The census above is vacuous if the allowlist names a function that does not spell it:
    a deleted derivation and a moved one would read the same."""
    sites = _inline_canonical_digest_sites(
        os.path.join(TOOLS, THE_ONE_HOME[0] + ".py"))
    assert [fn for _ln, fn in sites] == [THE_ONE_HOME[1]], sites


# ================================================================== the halt line, READ


def test_the_halt_line_reads_the_tie_clause(tmp_path, monkeypatch):
    """Rule 4. The tool's own `__main__`, in a subprocess, with an r2v record — the hosted
    partner tier that bills per submission — handed a graph it does not describe."""
    built = tmp_path / "built"
    built.mkdir(parents=True, exist_ok=True)
    record_path, _ = DRIVES["build_r2v_payload"](built, monkeypatch)
    code, halt = _gsg_halt(tmp_path, [f"--record={record_path}"])
    assert code == 2, halt
    assert halt["error"] == "RouteGate", halt
    assert halt["evidence"]["clause"] == "record_describes_a_different_graph", halt
    assert halt["evidence"]["gate"] == "ROUTE"
    assert halt["evidence"]["andon"] == "RouteGate"
    assert len(halt["evidence"]["declared_payload_sha256"]) == 64
    assert (halt["evidence"]["declared_payload_sha256"]
            != halt["evidence"]["api_payload_sha256"])


# ===========================================================================
# WAVE 23, F-bacc3961 — the builders' halt line and exit code, as REAL PROCESSES
# ===========================================================================
#
# Seven of the nine builders never executed their own `__main__` block anywhere in the
# suite. Measured on `e8263a3` by AST over every `subprocess.run` in `tests/*.py`: exactly
# two builders were ever run as a real process — `build_payload.py`
# (`test_packaging.py:1081`) and `build_t2v_payload.py` (`test_amend_w16_builders.py:215`).
# The other seven were driven only in-process through `main([...])` — `DRIVES` above is
# that shape — which cannot reach the `try`/`except` that prints the sentinel and picks the
# exit code. Of the 42 tools carrying a halt token, 17 carried one no test in `tests/`
# named, five of them these builders: BUILD_ANIMATE, BUILD_CAMERA_I2V, BUILD_CASCADE,
# BUILD_I2V, BUILD_LORA_ARM.
#
# The mechanism does work today — which is exactly what nothing asserted. So: one refusal
# per builder, run as the operator runs it, asserting the three things a caller reads.
#
# THE PREFIX IS DERIVED, not typed: `blender_stub.halt_handler` reads it off the
# `__main__` block, because seven of these nine print a prefix that is NOT the module stem
# (`build_animate_payload.py` prints `BUILD_ANIMATE_HALT`). One home for that derivation,
# shared with `test_instrument_exits.py`'s CPython census.

import subprocess                                                   # noqa: E402
import sys                                                          # noqa: E402

from blender_stub import halt_handler                                # noqa: E402


def _json_file(tmp_path, name, doc):
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")
    return str(path)


#: One TYPED REFUSAL per builder, each reached before any credit-adjacent work: the argv,
#: and the clause word its own andon carries. Chosen so every member refuses through a
#: named gate rather than through argparse (`ap.error` exits 2 with a usage line no halt
#: reader can key on — the wave-22 rule) and so no two members share a recipe by accident.
def _refusal_animate(tmp_path):
    return ([f"--uploads={_json_file(tmp_path, 'uploads.json', {})}",
             f"--out={tmp_path / 'o'}"], "missing_upload_key")


def _refusal_assembly(tmp_path):
    return ([f"--uploads={_json_file(tmp_path, 'uploads.json', {})}",
             f"--out={tmp_path / 'o'}"], "no_frames_to_gate")


def _refusal_camera_i2v(tmp_path):
    empty = _json_file(tmp_path, "uploads.json", {})
    return ([f"--uploads={empty}", f"--w1-record={empty}", f"--out={tmp_path / 'o'}",
             "--experiment=../escaped"], "output_name_is_not_a_name")


def _refusal_cascade(tmp_path):
    return ([f"--uploads={_json_file(tmp_path, 'uploads.json', {})}",
             f"--out={tmp_path / 'o'}"], "no_frames_to_gate")


def _refusal_i2v(tmp_path):
    empty = _json_file(tmp_path, "uploads.json", {})
    return ([f"--uploads={empty}", f"--e08-record={empty}", f"--out={tmp_path / 'o'}",
             "--experiment=../escaped"], "output_name_is_not_a_name")


def _refusal_lora_arm(tmp_path):
    base = os.path.join(REPO, "tests", "fixtures", "E12-w3-camera-i2v.api.json")
    seeds = _json_file(tmp_path, "seeds.json", {"seeds": [2026081233]})
    return ([f"--base={base}", "--arm=T", f"--out={tmp_path / 'o'}",
             f"--seeds-registry={seeds}", "--seed=2026081233"], "missing_subject")


def _refusal_payload(tmp_path):
    return (["--experiment=E03", "--arm=B2", f"--out={tmp_path / 'o' / 'B2.json'}"],
            "missing_subject")


def _refusal_r2v(tmp_path):
    seeds = _json_file(tmp_path, "seeds.json", {"seeds": [2026081301]})
    prompt = _json_file(tmp_path, "prompt.json",
                        {"prompt": "a figure", "negative_prompt": "blur"})
    return (["--arm=A1", "--seed=2026081301", f"--seeds={seeds}",
             f"--prompt-file={prompt}", f"--out={tmp_path / 'o'}"], "missing_arm_input")


def _refusal_t2v(tmp_path):
    seeds = _json_file(tmp_path, "seeds.json", {"seeds": [2026081201]})
    return ([f"--seeds={seeds}", f"--out={tmp_path / 'o'}", "--seed=2026081201"],
            "missing_subject")


REFUSALS = {
    "build_animate_payload": _refusal_animate,
    "build_assembly_payload": _refusal_assembly,
    "build_camera_i2v_payload": _refusal_camera_i2v,
    "build_cascade_payload": _refusal_cascade,
    "build_i2v_payload": _refusal_i2v,
    "build_lora_arm_payload": _refusal_lora_arm,
    "build_payload": _refusal_payload,
    "build_r2v_payload": _refusal_r2v,
    "build_t2v_payload": _refusal_t2v,
}


def test_every_builder_in_the_population_has_a_subprocess_refusal():
    """The census, in the shape `test_every_builder_in_the_population_has_a_behavioural_
    drive` already uses: the nine enumerated by glob and the nine refused here are the same
    set, so a builder cannot join the family and skip its own halt contract."""
    assert sorted(REFUSALS) == BUILDERS, sorted(set(REFUSALS) ^ set(BUILDERS))


def _run_builder(name, argv):
    return subprocess.run([sys.executable, os.path.join(TOOLS, f"{name}.py"), *argv],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=REPO)


@pytest.mark.parametrize("name", BUILDERS)
def test_every_builder_refuses_through_its_own_main_block_with_the_halt_contract(
        name, tmp_path):
    """The three things a caller reads, over the whole family, as real processes.

    What this looks like if the code were wrong in the specific way it exists to catch: a
    builder's `__main__` loses its handler, is reordered so the print follows `sys.exit`,
    or starts answering 1 for a typed refusal — and the paid path's halt line goes silent
    with the whole suite green, because seven of these nine were driven only through
    `main([...])` in-process.
    """
    argv, clause = REFUSALS[name](tmp_path)
    handler = halt_handler(f"{name}.py")
    assert handler, (
        f"{name} carries no `__main__` halt handler at all: its block prints no "
        f"`<PREFIX>_HALT` line and names no `run_tool_main` prefix, so a typed "
        f"refusal reaches the operator as a traceback at the exit code this repo "
        f"reserves for a crash")
    prefix = handler["prefix"]
    proc = _run_builder(name, argv)

    assert proc.returncode == 2, (
        f"{name}: exit {proc.returncode}; 2 is a deliberate refusal and 1 is a crash\n"
        f"{proc.stdout[-800:]}\n{proc.stderr[-800:]}")
    token = f"{prefix}_HALT"
    lines = [l for l in proc.stdout.splitlines() if l.split(" ", 1)[0] == token]
    assert len(lines) == 1, (
        f"{name}: {len(lines)} `{token} <json>` line(s) on stdout, want exactly 1\n"
        f"{proc.stdout[-800:]}")
    rec = json.loads(lines[0][len(token):].strip())
    assert {"error", "message", "evidence"} <= set(rec), (name, sorted(rec))
    ev = rec["evidence"]
    assert isinstance(ev, dict), (name, rec)
    assert ev.get("clause") == clause, (name, ev)
    assert rec["message"], (name, rec)


#: MEASURED 2026-09-05 by driving all nine refusals below: eight name the gate and the
#: andon in their evidence and ONE does not. `build_animate_payload`'s `missing_upload_key`
#: prints `{"clause": ..., "key": ..., "source": ..., "present": []}` — the clause and the
#: operand, and nothing that names the check that pulled. A halt reader keyed on
#: `evidence["gate"]` (the shape the other eight and every Blender-side handler carry) reads
#: `None` on the E08 builder's uploads refusal.
#:
#: The gap is in `tools/build_animate_payload.py`, which is the builders domain's file, so
#: it is COUNTED here rather than fixed here (wave 12, rule 3: a walk that cannot judge a
#: site reports it in its own category) and posted to the wave-23 seams inbox. This table
#: may not grow: a tenth builder, or a second refusal, arriving without the two keys fails
#: below rather than joining it.
EVIDENCE_WITHOUT_A_GATE_KEY = {
    "build_animate_payload": "missing_upload_key",
}


@pytest.mark.parametrize("name", BUILDERS)
def test_a_builder_refusal_names_the_gate_and_the_andon_that_pulled(name, tmp_path):
    """Wave 18, rule 3: a refusal names the andon that pulled, in the record an operator
    actually reads — not only in the exception a test caught in-process."""
    argv, clause = REFUSALS[name](tmp_path)
    handler = halt_handler(f"{name}.py")
    assert handler, (
        f"{name} carries no `__main__` halt handler at all: its block prints no "
        f"`<PREFIX>_HALT` line and names no `run_tool_main` prefix, so a typed "
        f"refusal reaches the operator as a traceback at the exit code this repo "
        f"reserves for a crash")
    prefix = handler["prefix"]
    proc = _run_builder(name, argv)
    token = f"{prefix}_HALT"
    line = [l for l in proc.stdout.splitlines() if l.split(" ", 1)[0] == token]
    assert line, (name, proc.stdout[-600:])
    ev = json.loads(line[0][len(token):].strip())["evidence"]

    if EVIDENCE_WITHOUT_A_GATE_KEY.get(name) == clause:
        assert not (ev.get("gate") or ev.get("andon")), (
            f"{name} now names the gate on `{clause}`; delete its row from "
            f"EVIDENCE_WITHOUT_A_GATE_KEY in the same commit")
        return
    assert ev.get("gate"), (
        f"{name}: the halt line names no gate, so the refusal cannot be read back to the "
        f"check that pulled it: {ev}")
    assert ev.get("andon"), (name, ev)


@pytest.mark.parametrize("name", BUILDERS)
def test_a_builder_refusal_writes_no_output_directory(name, tmp_path):
    """The effect beside the code: a refused build leaves nothing behind for a later step
    to read as a build that happened. `build_payload` writes a FILE at `--out`, so the
    directory it names is checked instead."""
    argv, _clause = REFUSALS[name](tmp_path)
    _run_builder(name, argv)
    out = [a[len("--out="):] for a in argv if a.startswith("--out=")]
    assert len(out) == 1, argv
    assert not os.path.exists(out[0]), f"{name}: a refusal left {out[0]}"


# The CRASH side of the divergence (an ordinary failure answers 1, never 2) is held for
# these same nine by `tests/test_instrument_exits.py::
# test_a_cpython_refusal_and_crash_do_not_answer_with_the_same_code`, which drives every
# builder's `__main__` block with a raiser rather than needing a per-builder broken input —
# `build_payload` takes no file argument at all, so there is no uniform crash operand here.
# Stated rather than duplicated, so the pair is findable from either side.
