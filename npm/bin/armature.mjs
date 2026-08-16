#!/usr/bin/env node
/**
 * armature — the Node launcher for the `armature-previz` Python toolkit.
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
import process from "node:process";

const PYPI = "armature-previz";
const DOCS = "https://mcp-tool-shop-org.github.io/armature/";

/** Interpreter candidates, in the order worth trying on each platform. */
function candidates() {
  const fromEnv = process.env.ARMATURE_PYTHON;
  const list = fromEnv ? [fromEnv] : [];
  // `py -3` is the Windows launcher and resolves when `python3` is only the Store stub.
  return process.platform === "win32"
    ? [...list, "python", "py", "python3"]
    : [...list, "python3", "python"];
}

/** Args that turn a bare candidate into a working interpreter invocation. */
function argsFor(exe) {
  return exe === "py" ? ["-3"] : [];
}

/**
 * Find an interpreter that can actually import the toolkit.
 *
 * Deliberately two questions, not one: an interpreter that exists but lacks the package
 * is a DIFFERENT problem from no interpreter at all, and telling them apart is the whole
 * value of this check. Reporting "python not found" to someone who has three Pythons and
 * no package would send them fixing the wrong thing.
 */
function locate() {
  let sawInterpreter = false;
  for (const exe of candidates()) {
    const pre = argsFor(exe);
    const probe = spawnSync(exe, [...pre, "-c", "import armature_core"], {
      stdio: "ignore",
      shell: false,
    });
    if (probe.error) continue; // this candidate is not on PATH at all
    sawInterpreter = true;
    if (probe.status === 0) return { exe, pre };
  }
  return { exe: null, pre: null, sawInterpreter };
}

function fail(found) {
  const what = found.sawInterpreter
    ? `Python is installed, but the ${PYPI} toolkit is not importable from it.`
    : "No Python interpreter was found on PATH.";
  process.stderr.write(
    `armature: ${what}\n\n` +
      `  This package is a launcher. The toolkit itself is Python:\n\n` +
      `      pip install ${PYPI}\n\n` +
      `  Point at a specific interpreter with ARMATURE_PYTHON if you use one.\n` +
      `  Docs: ${DOCS}\n`
  );
  process.exit(127);
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
  process.stdout.write(`armature launcher ok — candidates: ${list.join(", ")}\n`);
  process.exit(0);
}

const found = locate();
if (!found.exe) fail(found);

// Forward everything verbatim and inherit the child's exit code, so a gate that raises in
// Python still fails the shell that called this launcher.
const child = spawn(found.exe, [...found.pre, "-m", "armature_core.cli", ...argv], {
  stdio: "inherit",
  shell: false,
});
child.on("exit", (code, signal) => process.exit(signal ? 1 : code ?? 0));
child.on("error", () => fail(found));
