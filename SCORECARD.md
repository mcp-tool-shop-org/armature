# Scorecard

> Score a repo before remediation. Fill this out first, then use SHIP_GATE.md to fix.

**Repo:** `mcp-tool-shop-org/armature`
**Date:** 2026-08-13 (the v0.1.0 treatment)
**Type tags:** `[all]` — nothing is published to any registry

The scores below are the actual state of the tree, not estimates. Every "after" number is
backed by the corresponding evidence line in [SHIP_GATE.md](SHIP_GATE.md).

## Pre-Remediation Assessment

| Category | Score | Notes |
|----------|-------|-------|
| A. Security | 4/10 | The *posture* was already right and measurable — no credentials anywhere in the tree, no telemetry, no networking library imported by any tool — but none of it was written down. No SECURITY.md, no threat-model section in the README |
| B. Error Handling | 6/10 | A real typed hierarchy with gate ids and evidence dicts, and gates that `raise` rather than `assert` (proven by running the suite under `-O`). Not the Structured Error Shape, because there is no consumer for one |
| C. Operator Docs | 7/10 | README, roadmap, licence map, a five-page handbook and a complete experiment record — but no CHANGELOG, and the README stated no platform or runtime versions |
| D. Shipping Hygiene | 4/10 | 1005 tests green under CI and under `-O`, lockfile committed, `npm ci` everywhere. No single `verify` command, and no dependency scanning on the one manifest that exists |
| E. Identity (soft) | 7/10 | Logo, landing page, handbook and full GitHub metadata all present and current. Translations not run |
| **Overall** | **28/50** | A repo with an unusually strong *record* and unusually thin *shipping surface* — the inverse of the usual shape |

## Key Gaps

1. **No SECURITY.md and no threat-model section** — the two hardest security lines were
   unwritable without them, on a repo whose actual posture was already clean.
2. **No CHANGELOG** — twelve closed experiments and no version-shaped statement of what the
   record contains and what it deliberately does not claim.
3. **No `verify` script** — the legs existed in CI and could be run by hand; there was no
   one command that ran them and refused on any of them.
4. **No dependency scanning** — `site/` is the repo's only manifest and nothing looked at it.
5. **README stated no platforms or runtime versions** — the half of C1 that a reader needs
   before they can run anything.

## Remediation Priority

| Priority | Item | Estimated effort |
|----------|------|-----------------|
| 1 | SECURITY.md + README trust section, both measured against the tree | 1 session |
| 2 | CHANGELOG v0.1.0 — what it marks, what it does not | 1 session |
| 3 | `verify.ps1` — tests, tests under `-O`, site build, refuse on any leg | 1 session |
| 4 | `npm audit` in CI on the one manifest that exists | minutes |
| 5 | README **Running it** — platforms, runtimes, invocation shapes | minutes |

## Post-Remediation

| Category | Before | After |
|----------|--------|-------|
| A. Security | 4/10 | 10/10 |
| B. Error Handling | 6/10 | 6/10 — unchanged by design; the shape is skipped on merits, not bought |
| C. Operator Docs | 7/10 | 10/10 |
| D. Shipping Hygiene | 4/10 | 8/10 — no manifest exists to version-match, and dependency updates stay manual by the org's rule |
| E. Identity (soft) | 7/10 | 9/10 — translations outstanding, and they are the last thing before the tag |
| **Overall** | 28/50 | **43/50** |

**Hard gates A–D: every line checked with its evidence or skipped with the reason on its
merits.** The soft-gate residual is one item: translations, which run before the release tag
is cut because the tag is immutable.
