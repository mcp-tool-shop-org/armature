#!/usr/bin/env node
/**
 * armature — the Node launcher for the `armature-studio` Python toolkit.
 *
 * WHY A LAUNCHER AND NOT A PORT. armature's measured pieces are Python: the gates, the
 * framing solves, the channel maths. Re-implementing any of them in Node would create a
 * second copy of a threshold, which is how a threshold drifts — the exact failure the
 * repository's own record was written to prevent. So this package installs a command and
 * forwards it, verbatim, to the Python that holds the truth.
 *
 * WHAT IT WILL NOT DO. It does not install Python, does not pip-install anything behind
 * your back, and does not guess at a substitute when the toolkit is absent. A launcher
 * that silently installed things would make `npx` a package manager pointed at your
 * machine. When the toolkit is missing it says so, prints the one command that fixes it,
 * and exits non-zero.
 */
import { spawn, spawnSync } from "node:child_process";
import { constants } from "node:os";
import process from "node:process";

const PYPI = "armature-studio";
const DOCS = "https://mcp-tool-shop-org.github.io/armature/";

/**
 * Interpreter candidates, in the order worth trying on each platform.
 *
 * ARMATURE_PYTHON SUBSTITUTES FOR THIS LIST; IT DOES NOT JOIN IT. It used to be prepended
 * — `[pinned, "python", "py", "python3"]` — and `locate()` kept walking until something
 * imported the toolkit. Measured: with the pin on an interpreter that could not import
 * `armature_core` and a different one first on PATH that could, `armature --version` printed
 * the version and exited 0, byte-identical to the run with the variable unset. The failure
 * message below tells the user to point at a specific interpreter with this variable, so a
 * pin the code walks past is worse than no pin at all: the user gets the OTHER install's
 * version and behaviour with nothing on screen saying so, which is the repo's "success while
 * doing something else" class. A pin that cannot run the toolkit is now a refusal that names
 * the pin, not a fall-through.
 */
function candidates() {
  const pinned = process.env.ARMATURE_PYTHON;
  if (pinned) return [pinned];
  // `py -3` is the Windows launcher and resolves when `python3` is only the Store stub.
  return process.platform === "win32"
    ? ["python", "py", "python3"]
    : ["python3", "python"];
}

/** Args that turn a bare candidate into a working interpreter invocation. */
function argsFor(exe) {
  return exe === "py" ? ["-3"] : [];
}

/**
 * A program only a Python can run, and a token only a Python running it can print.
 *
 * WHY A SENTINEL AND NOT `--version`. This string decides which sentence the user is told, so
 * it has to be a fact this launcher established rather than one it recognised. A `-V` banner
 * is text an unrelated program can also emit; a token this file chose, printed with the
 * running interpreter's own `sys.version_info`, is not. The version rides along because the
 * answer to "is this a Python" is worth reporting as "which Python".
 */
const IDENT = "armature-python";
const IDENT_PROGRAM =
  'import sys;sys.stdout.write("' + IDENT + ' %d.%d.%d" % sys.version_info[:3])';
const IDENT_SHAPE = new RegExp("(?:^|\\n)" + IDENT + " (\\d+\\.\\d+\\.\\d+)");

/**
 * QUESTION ONE: is this candidate a Python at all?
 *
 * Returns `{ version }` on success, or `{ reason }` where reason is one of:
 *   `not-found`   — spawn errored (not on PATH at all)
 *   `not-a-python` — it started and exited non-zero (Store stub, renamed where.exe, node)
 *   `no-sentinel` — exited 0 without printing the IDENT token
 *
 * Collapsing the three into `null` made `fail()` assert "could not run" about a pin that
 * ran perfectly and simply is not a Python — the Store App Execution Alias's install notice
 * contradicted by the launcher's next line.
 *
 * WHAT THIS REPLACES. `locate()` set `sawInterpreter = true` for any candidate whose spawn did
 * not `error` — `if (probe.error) continue; sawInterpreter = true;` — so "this thing is a
 * Python" was decided by "this thing could be started". Measured on a Windows rig with the
 * file as shipped: a copy of `where.exe` renamed `python.exe`, alone on PATH beside node, made
 * `armature --version` print "Python is installed, but the armature-studio toolkit is not
 * importable from it." and tell the user to `pip install armature-studio` — on a machine with
 * no Python and no pip anywhere. `ARMATURE_PYTHON` pointed at the same file said the same
 * thing about the pin.
 *
 * That shape is not hypothetical, and the comment on `candidates()` above already names it:
 * the Windows Store App Execution Alias IS an executable called `python.exe` that starts,
 * prints an install notice and exits non-zero. It is the most common state a Windows machine
 * with no Python is in, and it is exactly the state this check exists to report correctly.
 *
 * A non-zero exit is "not an interpreter", not "a broken interpreter": nothing that can run
 * Python fails to run a `write`. The stdout is matched against the sentinel as well, because
 * an exit code of 0 is also something an unrelated program can produce.
 */
function pythonVersion(exe, pre) {
  const probe = spawnSync(exe, [...pre, "-c", IDENT_PROGRAM], {
    encoding: "utf8",
    shell: false,
  });
  if (probe.error) return { reason: "not-found" };
  if (probe.status !== 0) return { reason: "not-a-python" };
  const match = `${probe.stdout ?? ""}`.match(IDENT_SHAPE);
  return match ? { version: match[1] } : { reason: "no-sentinel" };
}

/**
 * Find an interpreter that can actually import the toolkit.
 *
 * Deliberately two questions, not one: an interpreter that exists but lacks the package
 * is a DIFFERENT problem from no interpreter at all, and telling them apart is the whole
 * value of this check. Reporting "python not found" to someone who has three Pythons and
 * no package would send them fixing the wrong thing.
 *
 * The two questions are now asked with two probes, in that order, because a single
 * `import armature_core` spawn could only ever answer the second one — see `pythonVersion`
 * above for what it was reading as "Python is installed".
 */
function locate() {
  let sawInterpreter = false;
  let probeReason = null;
  for (const exe of candidates()) {
    const pre = argsFor(exe);
    // QUESTION ONE. A candidate that is not a Python leaves `sawInterpreter` alone, so the
    // refusal below stays "no interpreter was found" rather than becoming a claim about a
    // toolkit missing from something that could never have imported it. The reason rides
    // so `fail()` can distinguish "not on PATH" from "ran, and is not a Python".
    const identity = pythonVersion(exe, pre);
    if (!identity.version) {
      probeReason = identity.reason;
      continue;
    }
    sawInterpreter = true;
    probeReason = null;
    // QUESTION TWO.
    const probe = spawnSync(exe, [...pre, "-c", "import armature_core"], {
      stdio: "ignore",
      shell: false,
    });
    // `sawInterpreter` rides the SUCCESS shape too. It used to be on the failure shape only,
    // and `fail()` branches on it: handed a success object, `found.sawInterpreter` was
    // undefined and the launcher reported "No Python interpreter was found on PATH" about an
    // interpreter it had just imported the toolkit with. A caller cannot read a fact off a
    // shape that only carries it when the answer is no.
    if (!probe.error && probe.status === 0) {
      return { exe, pre, sawInterpreter: true, reason: null };
    }
  }
  return { exe: null, pre: null, sawInterpreter, reason: probeReason };
}

/**
 * The refusal. `err` is present only when an interpreter was FOUND and then would not start.
 *
 * That distinction is the whole point of the two-question probe above: telling someone whose
 * Python is fine, and whose toolkit is installed, to `pip install` the toolkit sends them
 * fixing the one thing that is not broken — and reinstalling changes nothing. The spawn fails
 * after a successful probe for reasons that have nothing to do with either: EACCES/EPERM from
 * an AV or policy hook, the interpreter renamed or unmounted between the two calls, EMFILE.
 */
function fail(found, err) {
  const pinned = process.env.ARMATURE_PYTHON;
  if (err) {
    process.stderr.write(
      `armature: could not start ${found.exe}: ${err.code ?? err.message}\n\n` +
        `  That interpreter WAS found and it imports the ${PYPI} toolkit — the probe ran and\n` +
        `  succeeded. Something stopped this process from launching it: a security or policy\n` +
        `  hook, a file that moved between the probe and the launch, or a process limit.\n` +
        `  Reinstalling ${PYPI} will not change this.\n\n` +
        `  Docs: ${DOCS}\n`
    );
    process.exit(127);
  }
  // A pinned run and an unpinned one fail for different reasons, and saying "no Python was
  // found on PATH" to someone who pinned one would send them fixing the wrong thing — the
  // same distinction `locate()` draws between "no interpreter" and "no package". A pin that
  // RAN and is not a Python is a third sentence: "could not run" is the opposite of what
  // happened for the Store stub and for `ARMATURE_PYTHON` pointed at node.
  const ranButNotPython =
    !found.sawInterpreter &&
    (found.reason === "not-a-python" || found.reason === "no-sentinel");
  const what = pinned
    ? found.sawInterpreter
      ? `ARMATURE_PYTHON is set to ${pinned}, and the ${PYPI} toolkit is not importable from it.`
      : ranButNotPython
        ? `ARMATURE_PYTHON is set to ${pinned}; it ran, and it is not a Python interpreter.`
        : `ARMATURE_PYTHON is set to ${pinned}, which this shell could not run.`
    : found.sawInterpreter
      ? `Python is installed, but the ${PYPI} toolkit is not importable from it.`
      : "No Python interpreter was found on PATH.";
  // Branch the REMEDY the way the headline already branches: pip ships with Python, so the
  // one machine state with no interpreter is the one where `pip install` cannot run.
  const remedy = found.sawInterpreter
    ? `  This package is a launcher. The toolkit itself is Python:\n\n` +
      `      pip install ${PYPI}\n\n`
    : `  This package is a launcher. Install Python 3.11 or newer first\n` +
      `  (https://www.python.org/downloads/), then:\n\n` +
      `      pip install ${PYPI}\n\n`;
  const hint = pinned
    ? `  That pin is the ONLY interpreter tried — PATH is not searched while it is set.\n` +
      `  Install the toolkit into it, or unset ARMATURE_PYTHON to search PATH again.\n`
    : `  Point at a specific interpreter with ARMATURE_PYTHON if you use one.\n`;
  process.stderr.write(
    `armature: ${what}\n\n` +
      remedy +
      hint +
      `  What this launcher tried: armature --node-selftest\n` +
      `  Docs: ${DOCS}\n`
  );
  process.exit(127);
}

/**
 * The exit code a caller should see for a child that ended with `code` / `signal`.
 *
 * THE COLLAPSE THIS REPLACES. The handler was `signal ? 1 : code ?? 0`, so every signal
 * death arrived at the caller as 1 — byte-identical to an ordinary Python traceback. The
 * rest of this repository spends real effort on that distinction: 2 is a refusal, 1 is a
 * crash (`tests/test_packaging.py` pins that convention on the CPU tools), and the realistic
 * signal here is the OOM killer taking the Python process during a frame or GLB pass. A
 * wrapper that retries a crash and halts on a kill could not tell them apart, so an
 * OOM-killed run was retried into the same wall with nothing naming the signal.
 *
 * 128 + N is the shell convention, which is what a caller already knows how to read — a
 * shell reports exactly this for its own killed children. A signal Node names but this
 * platform does not number falls back to 1 rather than inventing a code.
 */
function exitCodeFor(code, signal) {
  const number = signal ? constants.signals[signal] : undefined;
  if (signal) return number ? 128 + number : 1;
  return code ?? 0;
}

/** Say which signal ended the run, because the exit code alone is a number to look up. */
function reportSignal(signal) {
  process.stderr.write(
    `armature: the ${PYPI} process was killed by ${signal} ` +
      `(exit ${exitCodeFor(null, signal)}).\n\n` +
      `  Nothing in Python refused: the process was terminated from outside. On a long\n` +
      `  frame or GLB pass the usual cause is the OOM killer. Retrying without changing\n` +
      `  anything will meet the same limit.\n\n` +
      `  Docs: ${DOCS}\n`
  );
}

const argv = process.argv.slice(2);

// A self-test that does not need Python present: it proves this file parses, resolves its
// candidate list and reports honestly. `npm test` runs it in CI where Python may be absent.
if (argv[0] === "--node-selftest") {
  const list = candidates();
  if (!Array.isArray(list) || list.length === 0) {
    process.stderr.write("selftest: no interpreter candidates\n");
    process.exit(1);
  }
  if (argsFor("py")[0] !== "-3") {
    process.stderr.write("selftest: the Windows launcher lost its -3\n");
    process.exit(1);
  }
  // The pin is checked here because `npm test` is the launcher's only coverage in CI, and
  // the pin was prepended to the PATH walk rather than replacing it — a run that honours
  // the variable and a run that ignores it are indistinguishable from the outside unless
  // something asserts the candidate list itself.
  const saved = process.env.ARMATURE_PYTHON;
  try {
    process.env.ARMATURE_PYTHON = "/armature/selftest/pinned-python";
    const pinnedList = candidates();
    if (pinnedList.length !== 1 || pinnedList[0] !== "/armature/selftest/pinned-python") {
      process.stderr.write(
        `selftest: ARMATURE_PYTHON did not substitute for the search order — ` +
          `candidates were: ${pinnedList.join(", ")}\n`
      );
      process.exit(1);
    }
  } finally {
    if (saved === undefined) delete process.env.ARMATURE_PYTHON;
    else process.env.ARMATURE_PYTHON = saved;
  }
  // THE TWO-QUESTION PROBE, exercised where there is no Python to exercise it with. `node`
  // itself is an executable that starts and exits non-zero for the sentinel program (`-c` is
  // `--check` and wants a file), which is precisely the shape that used to be read as "Python
  // is installed": the Store stub, a `where.exe` renamed `python.exe`, anything on PATH under
  // that name. Driven through `locate()` rather than through the probe alone, because
  // `sawInterpreter` is the operand `fail()` branches on, and the pin substitutes for the
  // whole candidate list — so this asks the real question of the real function.
  const pinSaved = process.env.ARMATURE_PYTHON;
  try {
    process.env.ARMATURE_PYTHON = process.execPath;
    const probed = locate();
    if (
      probed.exe !== null ||
      probed.sawInterpreter !== false ||
      (probed.reason !== "not-a-python" && probed.reason !== "no-sentinel")
    ) {
      process.stderr.write(
        `selftest: a non-Python executable (${process.execPath}) was read as an interpreter ` +
          `— exe=${probed.exe}, sawInterpreter=${probed.sawInterpreter}, ` +
          `reason=${probed.reason}.\n` +
          `  Someone with no Python at all would be told to pip install the toolkit, with no\n` +
          `  pip to run it with.\n`
      );
      process.exit(1);
    }
    // Drive fail()'s four operand pairs (pinned × sawInterpreter) and assert: every
    // refusal names --node-selftest; the no-interpreter body names a Python install;
    // a pin that ran and is not a Python gets the third headline.
    const captured = [];
    const realWrite = process.stderr.write.bind(process.stderr);
    const realExit = process.exit.bind(process);
    process.stderr.write = (chunk) => {
      captured.push(String(chunk));
      return true;
    };
    process.exit = () => {};
    try {
      const pairs = [
        { pin: "/armature/selftest/pinned-python", sawInterpreter: false, reason: "not-found" },
        {
          pin: "/armature/selftest/pinned-python",
          sawInterpreter: false,
          reason: "not-a-python",
        },
        { pin: "/armature/selftest/pinned-python", sawInterpreter: true, reason: null },
        { pin: undefined, sawInterpreter: false, reason: "not-found" },
        { pin: undefined, sawInterpreter: true, reason: null },
      ];
      for (const shape of pairs) {
        if (shape.pin === undefined) delete process.env.ARMATURE_PYTHON;
        else process.env.ARMATURE_PYTHON = shape.pin;
        captured.length = 0;
        fail({
          exe: null,
          pre: null,
          sawInterpreter: shape.sawInterpreter,
          reason: shape.reason,
        });
        const body = captured.join("");
        if (!body.includes("--node-selftest")) {
          throw new Error("fail() no longer names --node-selftest in the refusal");
        }
        if (!shape.sawInterpreter && !/python\.org\/downloads/i.test(body)) {
          throw new Error("no-interpreter refusal does not name a Python install");
        }
        if (shape.sawInterpreter && /python\.org\/downloads/i.test(body)) {
          throw new Error("interpreter-found refusal still points at python.org");
        }
        if (
          shape.reason === "not-a-python" &&
          !body.includes("it ran, and it is not a Python interpreter")
        ) {
          throw new Error(
            "not-a-python pin no longer gets the ran-but-not-Python sentence"
          );
        }
      }
    } catch (e) {
      process.stderr.write = realWrite;
      process.exit = realExit;
      process.stderr.write(`selftest: ${e.message}\n`);
      process.exit(1);
    } finally {
      process.stderr.write = realWrite;
      process.exit = realExit;
      process.env.ARMATURE_PYTHON = process.execPath;
    }
  } finally {
    if (pinSaved === undefined) delete process.env.ARMATURE_PYTHON;
    else process.env.ARMATURE_PYTHON = pinSaved;
  }
  // The signal mapping, checked here because `npm test` is the launcher's only coverage in
  // CI and there is no Python to kill on a runner. A launcher that honours the convention
  // and one that collapses every signal into 1 are indistinguishable from outside unless
  // something asserts the mapping itself — the same reason the pin is checked above.
  const mapping = [
    ["SIGKILL", 137],
    ["SIGTERM", 143],
    ["SIGINT", 130],
  ];
  for (const [name, expected] of mapping) {
    const got = exitCodeFor(null, name);
    if (got !== expected) {
      process.stderr.write(`selftest: ${name} maps to ${got}, not ${expected}\n`);
      process.exit(1);
    }
  }
  // The half that must not move while the half above is added: the child's own exit code
  // still reaches the caller, and a refusal (2) is still distinct from a crash (1).
  if (exitCodeFor(0, null) !== 0 || exitCodeFor(2, null) !== 2 || exitCodeFor(1, null) !== 1) {
    process.stderr.write("selftest: the child's exit code no longer reaches the caller\n");
    process.exit(1);
  }
  const reported = mapping.map(([name, code]) => `${name}=${code}`).join(", ");
  process.stdout.write(
    `armature launcher ok — candidates: ${list.join(", ")}; signal exits: ${reported}\n`
  );
  process.exit(0);
}

const found = locate();
if (!found.exe) fail(found);

// Forward everything verbatim and inherit the child's exit code, so a gate that raises in
// Python still fails the shell that called this launcher. A child that did not exit on its
// own has no exit code to inherit, so its signal is named and reported as 128 + N rather
// than erased into the crash code — see `exitCodeFor` above.
const child = spawn(found.exe, [...found.pre, "-m", "armature_core.cli", ...argv], {
  stdio: "inherit",
  shell: false,
});
child.on("exit", (code, signal) => {
  if (signal) reportSignal(signal);
  process.exit(exitCodeFor(code, signal));
});
// The error is carried in, not dropped: `fail(found)` with no error reports "no interpreter",
// which is a claim about a probe that had already succeeded.
child.on("error", (e) => fail(found, e));
