"""Emit a CycloneDX 1.5 SBOM JSON from a venv's `pip freeze` (stdlib only).

Called by `.github/actions/clean-room/action.yml` after the wheel room is probed, so the
bill of materials matches the resolved set the clean install actually ran. Output lands
under `sbom/` (not `dist/`) — classifier_gate refuses unreadable non-wheel/sdist files in
`dist/`, and pypi-publish must not see the SBOM as a distribution.

Usage: python sbom_emit.py <venv-python> <out-json> --name NAME --version VERSION
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys


def _freeze_components(venv_python: str) -> list[dict]:
    raw = subprocess.check_output(
        [venv_python, "-m", "pip", "freeze"],
        text=True,
        stderr=subprocess.STDOUT,
    )
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
    args = parser.parse_args(argv)

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
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(f"sbom_emit: pip freeze failed: {exc}\n")
        if exc.output:
            sys.stderr.write(str(exc.output) + "\n")
        raise SystemExit(1) from exc
