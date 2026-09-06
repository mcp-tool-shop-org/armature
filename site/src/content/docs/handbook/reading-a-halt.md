---
title: Reading a halt
description: What every armature instrument prints when it refuses, waits or finishes — the exit codes, the halt line, the clause vocabulary, and how to run the suite that holds them.
sidebar:
  order: 4
---

Every instrument under `tools/` is a script an operator runs, and the whole of what it says to that
operator was measured and rewritten in the health run of 2026-09-03 to 09-06. This page is the
contract as it stands at v0.4.0. It is the same contract on the rig, on a CI runner, and inside
Blender's own interpreter; the suite holds every sentence of it as a census, so a tool that drifts
from it fails a test by name.

## Exit codes

| exit | meaning | what you see |
|---|---|---|
| **0** | the tool did what it says | one success sentinel earned by an effect — `BUILD_PAYLOAD_OK`, `RIG_OK`, `ENCODE_OK`, … — on stdout |
| **2** | a deliberate refusal: a gate fired, a premise failed, an argument was refused | one `<TOOL>_HALT {json}` line on stdout, nothing written that the refusal guards |
| **1** | a crash: an error the tool did not anticipate | one `<TOOL>_HALT {json}` line, a traceback on stderr |

Never key on the exit code alone under `blender -b -P`: Blender exits 0 when a script's exception
propagates, which is why the 21 Blender-side tools print the same halt line through a local handler and
five of the rig tools also write a `halt.json` beside the outputs they did not produce.

## The halt line

A refusal or a crash prints exactly one line of the form `<TOOL>_HALT {json}`. The record carries six
keys:

```json
{"tool": "encode_control", "outcome": "REFUSED — the tool declined to proceed", "gate": "ENCODE",
 "error": "EncodeRefusal", "message": "…what was measured, which clause fired, what to change…",
 "evidence": {"clause": "ffmpeg_exceeded_the_time_bound", "bound_s": 220.0, "elapsed_s": 220.4,
              "binary": "ffmpeg", "input": "out/depth", "partial": ["out/c.mkv (1.2 MB)"]}}
```

- `outcome` is one of three sentences: `HALTED — a gate fired`, `REFUSED — the tool declined to proceed`,
  `FAILED — an unhandled error`.
- `message` is the refusal's own prose, written for a person: what was measured (the value, the path,
  the frame, the file), which clause fired, and what to change (a flag, a file, a value).
- `evidence.clause` is the machine-readable word a caller branches on. The vocabulary — 698 words at
  v0.4.0 — is held by `tests/test_refusal_clauses.py`; a clause that is not in it fails the suite.
- The record is strict JSON with the tool's prose left as prose; where the terminal's encoding cannot
  carry a character, that character falls back to a `\uXXXX` escape rather than the line failing to
  print, and the exit code is unaffected either way.

The one implementation of the CPython contract is `armature_core.parts.run_tool_main`; its docstring
is the specification, and 50 of the 54 CPython instruments adopt it by import. The recorded exceptions
are the Blender-side handlers above and the clean-room classifier gate, which runs where the package
cannot be imported.

## Three refusals you will meet

**A tool that would write over an earlier run's artefacts** — a build's graph and record, a render's
frames — refuses with the clause `output_already_exists` and names them; a build names both files and
both digests. `--overwrite` replaces them, and the success record then carries `out_dir_pre_existed`
and `overwrote`. The one spend builder that sits under Gate CANON's `out_dir_not_empty` refuses a
non-empty `--out` one gate earlier and takes no flag.

**A tool that waits** — an encode, a decode, a render, a download — prints a lowercase progress line
to stderr before and after the wait, and per item where the work is countable:

```
stage_render frames 7/81  elapsed 12.3s  bound none
fetch_run download 0/12  elapsed 0.0s  bound 660s -> outputs/E13/runs/A1
```

stdout still carries only the one success or halt line, so a wrapper that keys on stdout sees
nothing new. Every subprocess carries a bound derived from the work — an encode from its frame count,
a decode from the file's bytes, a download from its job count and throttle — and a bound that is
reached is a refusal by name (`ffmpeg_exceeded_the_time_bound`, `downloader_exceeded_the_time_bound`)
that names the partial work on disk and never retries: on the paid path a retry spends credits that
have no compensator.

**A gate that fires after the output directory exists** says so: the refusal names the directory,
says it holds partial work and is not a result, and says the supported next step. The control-sequence
exporter distinguishes a write failure inside the run (`control_sequence_write_failed`, with the errno,
the path, the frame reached and the total) from an unreadable spec or asset
(`spec_or_asset_path_unreadable`).

## `--help`

Every CPython instrument answers `python tools/<name>.py --help` with one sentence saying what it does
and to whom, text on every flag that reaches an operator, `choices=` where a value set exists, and the
default named where a default matters. The four tools that spend or gate a spend — `build_r2v_payload`,
`build_lora_arm_payload`, `gate_saved_graph`, `canon_gate` — carry an epilogue naming the route and
what a refusal costs. Five instruments parse `--key=value` by hand rather than through argparse —
`stage_render`, `make_sheet`, `analyze_p3`, `rig_sheet_compose`, `sheet_compose` — so `--help` is not
a route they serve; each refuses an unknown token by name and prints its own flag set in the refusal.
The 21 Blender-side tools run only as `blender -b -P tools/<name>.py -- <args>`; `python tools/<name>.py`
on one of those fails with `No module named 'bpy'`. The full list, by how each tool runs, is
[docs/tools.md](https://github.com/mcp-tool-shop-org/armature/blob/main/docs/tools.md), generated
from the docstrings.

## Running the suite

```
python -m pytest -q          # from the repo root, on the repo venv — never a system Python
```

Three environment levers, all optional: `PYTHONPATH` pointing at the sibling `record-index` working
copy (the index tests skip by name without it), `ARMATURE_BLENDER` (the Blender executable the
Blender-driving fixtures run; without it those tests skip visibly), and `ARMATURE_GIT` (the git the
packaging test invokes). CI's exact recipe is the `python-tests` job in `.github/workflows/ci.yml`,
on Python 3.11 and 3.13; `verify.ps1` runs the suite twice (once under `-O`, because a gate that an
optimiser flag can delete is not a gate) and then builds the package and installs it into two clean
rooms. At v0.4.0 the suite reads 7,538 passed and 64 skipped on the rig, identical under `-O`.

Two things the suite holds that are easy to break from outside: every `<TOOL>_HALT` line must be
strict JSON, and a tool's success token must be the one its halt token pairs with — a second all-caps
token printed outside the handler (a progress line spelled `STAGE_RENDER_PROGRESS`, say) reads as a
second sentinel and fails the pairing census. That is why progress goes to stderr in lowercase.
