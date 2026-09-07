"""Emit a CycloneDX 1.5 SBOM JSON from a venv's `pip freeze` (stdlib only).

Called by `.github/actions/clean-room/action.yml` after the wheel room is probed, so the
bill of materials matches the resolved set the clean install actually ran. Output lands
under `sbom/` (not `dist/`) — classifier_gate refuses unreadable non-wheel/sdist files in
`dist/`, and pypi-publish must not see the SBOM as a distribution.

THE HALT CONTRACT IS IMPORTED, NOT SPELLED A THIRD TIME. WAVE 37 pin-fix: this file
joined `.github/actions/**` without a local andon, so
`tests/test_ci_workflows.py::test_the_classifier_gate_refuses_by_a_named_andon_and_never_by_a_bare_exit`
went red on the directory census. Same recorded exception as `lazy_import_probe.py`:
`armature_core.parts.run_tool_main` is not importable in the clean room, so this file
imports `run_gate_main` from `classifier_gate` beside it and passes its own tokens.

Usage: python sbom_emit.py <venv-python> <out-json> --name NAME --version VERSION
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

from classifier_gate import run_gate_main

#: The andon's name, carried in every halt record's `gate` field.
GATE = "SBOM_EMIT"

#: The tool name, the stem, so a reader keying on the printed prefix and a reader keying on
#: the file agree — `classifier_gate.py`'s rule, applied here.
TOOL = "sbom_emit"

#: The printed tokens. An operator keys on these, never on prose.
HALT = "SBOM_EMIT_HALT "
OK = "SBOM_EMIT_OK "


class SbomEmitFailure(Exception):
    """A refusal this emitter is responsible for. · ANDON

    The shape `ClassifierGateFailure` / `LazyImportProbeFailure` beside this file have:
    carries the clause that fired and the evidence it fired on, so the halt record names
    WHICH check refused and on WHAT.
    """

    def __init__(self, message, clause, evidence=None):
        super().__init__(message)
        self.gate = GATE
        self.clause = clause
        self.evidence = dict(evidence or {})
        self.evidence["clause"] = clause


def _freeze_components(venv_python: str) -> list[dict]:
    try:
        raw = subprocess.check_output(
            [venv_python, "-m", "pip", "freeze"],
            text=True,
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as exc:
        raise SbomEmitFailure(
            "pip freeze failed under the clean-room interpreter; the SBOM would not "
            "match the resolved set the wheel room actually ran",
            "pip-freeze-failed",
            {
                "venv_python": venv_python,
                "returncode": exc.returncode,
                "output": (exc.output or "")[-2000:],
            },
        ) from exc
    components: list[dict] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or " @ " in line:
            continue
        if "==" not in line:
            continue
        name, version = line.split("==", 1)
        name = name.strip()
        version = version.strip()
        if not name or not version:
            continue
        purl = f"pkg:pypi/{name}@{version}"
        components.append(
            {
                "type": "library",
                "name": name,
                "version": version,
                "bom-ref": purl,
                "purl": purl,
            }
        )
    components.sort(key=lambda c: c["name"].lower())
    return components


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("venv_python", help="Interpreter inside the clean wheel room")
    parser.add_argument("out_json", help="Destination CycloneDX JSON path")
    parser.add_argument("--name", required=True, help="Root component name (dist name)")
    parser.add_argument("--version", required=True, help="Root component version")
    # `run_gate_main` passes full `sys.argv` (script name included); argparse wants the
    # tail. A direct `main()` call with no argv still reads `sys.argv[1:]`.
    args = parser.parse_args(None if argv is None else argv[1:])

    root_purl = f"pkg:pypi/{args.name}@{args.version}"
    bom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "component": {
                "type": "library",
                "name": args.name,
                "version": args.version,
                "bom-ref": root_purl,
                "purl": root_purl,
            }
        },
        "components": _freeze_components(args.venv_python),
    }
    with open(args.out_json, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(bom, fh, indent=2, sort_keys=False)
        fh.write("\n")
    print(f"sbom: wrote {args.out_json} ({len(bom['components'])} components)")
    print(OK + json.dumps({
        "tool": TOOL, "gate": GATE, "out_json": args.out_json,
        "components": len(bom["components"]),
    }))
    return 0


if __name__ == "__main__":
    run_gate_main(main, sys.argv, tool=TOOL, gate=GATE, halt=HALT,
                  refusal_class=SbomEmitFailure)
