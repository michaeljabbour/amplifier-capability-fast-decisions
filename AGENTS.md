# AGENTS.md

**Read `docs/GOAL.md` first: it states what this project must achieve and how success is measured.**

Coding-agent instructions for this repo live in `docs/AGENT-HANDOFF.md` --
read that file before making changes here.

Quick pointers:
- Layout: shared package in `src/amplifier_fast_decisions/`; thin module shims in `modules/*`; bundle composition in `bundle.md`, `behaviors/`, `bundles/`.
- Setup: `uv pip install -e '.[test]'` (or prefix commands with `PYTHONPATH=src`).
- Test command: `python3 -m unittest discover -s tests -v` (or `scripts/smoke_test.sh`, which sets the path for you)
- Health check: `python3 -m amplifier_fast_decisions doctor`
- Bench (offline telemetry analysis + synthetic suite): `afast bench replay <events-dir-or-jsonl> --json`, `afast bench suite [suites/v1.jsonl] --json` -- see `docs/BENCH.md`
- Auto-observatory (session-start viewer bootstrap): stop a running one with `afast serve --stop` (reads `~/.amplifier/fast-decisions/serve.json` by default; `--state-file` to override) -- do this before a manual `afast serve` in the same events dir/port to avoid two servers
- Preview root build/cache artifacts with `git clean -ndX -- build/ dist/ .ruff_cache/`; when cleanup is requested, remove only those named disposable paths with `git clean -fdX -- build/ dist/ .ruff_cache/`. For `__pycache__`, egg-info or `.DS_Store` elsewhere, name each exact disposable path. Never run unscoped `git clean -fdX`: it also deletes ignored `.research/market/`, local environments and other user data. Preserve `.research/` and unrelated ignored/untracked work.
- Key docs: `README.md`, `docs/COMPATIBILITY.md`, `docs/PRIVACY.md`, `docs/ARCHITECTURE.md`

## Project Jev advice (Codex)

Before substantial research, repeating a failed approach, loading several tools or
skills, spawning agents, choosing between materially different execution routes,
or proposing a consequential action, consider whether a small bounded Jev decision
would change the next step. If yes, build a compact state with no secrets, call the
installed router, interpret its action, and continue the original task. Skip Jev
for simple answers, deterministic calculations, routine file edits, and situations
where the call adds no useful decision. Respect `bypass jev`. Keep irreversible
actions behind human confirmation; an existing explicit authorization still applies.

Use `scripts/jev-route --input -` with JSON containing `task`, `context`, and
`options` (two to six named, bounded alternatives). Start in **shadow** mode: this
command gives advice, never executes actions, and never overrides native permission
checks. Independently review the result, do the authorized next step, then record
the host's choice with `--record-outcome ID --action OPTION --evidence REFERENCE`.
For simple tasks, answer directly without invoking any router process; `--skip
simple` exists for auditing that path during setup. On unavailable/uncertain advice,
continue ordinary reasoning; do not retry automatically. No setup calls enter the
SWE-bench arms. Read [docs/CODEX-JEV.md](docs/CODEX-JEV.md) for setup, schema, logs,
privacy and the conditions for considering active integration. The official
TypeSafe skill is installed at `.agents/skills/typesafe-ai/SKILL.md`.

## Market research upkeep

Local-only market research lives in `.research/market/` (gitignored; never commit it).

At session start, check `.research/market/last_updated`:
- If the file is missing, seed it from this repository's README and capability source/provenance links, using cited primary sources and local retrieval dates.
- If it is older than 30 days, or before any positioning, launch or naming work, refresh it with cited primary sources (URL + retrieved date).
- Keep it local. Never commit it and never copy private research into public docs.
- Log every change in `.research/market/CHANGELOG.md`.

## Capability identity

Public capability identity: `amplifier-capability-fast-decisions`. Preserve the existing portable method folder, native interfaces and legacy installation routes across the approved repository rename.
