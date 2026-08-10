"""G1 must survive `-O` and `PYTHONOPTIMIZE=1`.

87 of facet's ANDONs turned out to be removable by an environment variable. This is
the test that says do not add the 88th. It drives **the real write path**
(`stage_render.run_export`), not the gate function in isolation — a gate that raises
correctly but is never reached is not a gate.

It also checks that the output directory does not exist afterwards: G1 promises to
raise *before any frame is written*, and "before" is a claim about ordering that only
an on-disk check can falsify.
"""

import os
import subprocess
import sys
import textwrap

import pytest

from conftest import TOOLS

PROBE = textwrap.dedent(
    """
    import json, os, sys
    sys.path.insert(0, sys.argv[1])
    out_dir = sys.argv[2]
    case = sys.argv[3]

    import stage_render
    from armature_core.errors import G1GeneratorLegality

    asset = os.path.join(out_dir + "_asset.glb")
    with open(asset, "wb") as fh:
        fh.write(b"not-a-real-glb")

    bad = {
        "width":  dict(width=1020, height=768, count=33),
        "frames": dict(width=512,  height=768, count=80),
        "unknown_generator": dict(width=512, height=768, count=33),
    }[case]

    spec = {
        "spec_version": 1,
        "name": "optimize-probe",
        "generator": "nobody-filed-this" if case == "unknown_generator" else "wan-vace",
        "asset": {"path": asset},
        "resolution": {"width": bad["width"], "height": bad["height"]},
        "frames": {"count": bad["count"], "fps": 16},
        "channels": ["mask"],
    }
    from armature_core import shotspec
    spec = shotspec.normalise_spec(spec)

    result = {"optimize_flag": sys.flags.optimize,
              "asserts_active": __debug__}
    try:
        stage_render.run_export(spec, out_dir)
        result["outcome"] = "NO_RAISE"
    except G1GeneratorLegality as exc:
        result["outcome"] = "G1_RAISED"
        result["message"] = str(exc)
    except BaseException as exc:
        result["outcome"] = "WRONG_ERROR"
        result["message"] = f"{type(exc).__name__}: {exc}"
    result["out_dir_exists"] = os.path.exists(out_dir)
    print("RESULT " + json.dumps(result))
    """
)


def _run(tmp_path, case, *, flag=False, env_var=False):
    script = tmp_path / "probe.py"
    script.write_text(PROBE, encoding="utf-8")
    out_dir = str(tmp_path / f"run_{case}_{int(flag)}_{int(env_var)}")

    env = dict(os.environ)
    env.pop("PYTHONOPTIMIZE", None)
    if env_var:
        env["PYTHONOPTIMIZE"] = "1"

    cmd = [sys.executable]
    if flag:
        cmd.append("-O")
    cmd += [str(script), TOOLS, out_dir, case]

    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=180)
    assert proc.returncode == 0, proc.stderr
    line = [l for l in proc.stdout.splitlines() if l.startswith("RESULT ")]
    assert line, proc.stdout + proc.stderr
    import json

    return json.loads(line[-1][len("RESULT "):])


@pytest.mark.parametrize("case", ["width", "frames", "unknown_generator"])
@pytest.mark.parametrize(
    "flag,env_var,label",
    [(False, False, "plain"), (True, False, "-O"), (False, True, "PYTHONOPTIMIZE=1")],
)
def test_g1_raises_under_optimization(tmp_path, case, flag, env_var, label):
    res = _run(tmp_path, case, flag=flag, env_var=env_var)
    assert res["outcome"] == "G1_RAISED", f"{label}/{case}: {res}"
    assert res["out_dir_exists"] is False, (
        f"{label}/{case}: G1 promises to raise before any frame is written, but the "
        f"output directory exists"
    )


def test_the_optimization_actually_took_effect(tmp_path):
    """Guard against a green result that proves nothing because -O never applied —
    a check that cannot fail is not a check."""
    plain = _run(tmp_path, "width", flag=False, env_var=False)
    flagged = _run(tmp_path, "width", flag=True, env_var=False)
    env = _run(tmp_path, "width", flag=False, env_var=True)

    assert plain["asserts_active"] is True and plain["optimize_flag"] == 0
    assert flagged["asserts_active"] is False and flagged["optimize_flag"] >= 1
    assert env["asserts_active"] is False and env["optimize_flag"] >= 1
