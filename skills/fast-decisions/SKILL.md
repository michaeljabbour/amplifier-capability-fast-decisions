---
name: fast-decisions
description: "Measure small agent decisions and use a bounded fast path only where its outcome can be checked. Use when asked to select a read/list candidate, diagnose routing, or compare observed execution."
---

# Fast Decisions

Use the actual amplifier-fast-decisions CLI or amplifier_fast_decisions library. This is a Smart Tool with deterministic manifest/describe/diagnose/measure/compare operations; it is not a request to let a prompt execute arbitrary tools. Start with amplifier-fast-decisions --help and <capability> --help for the installed version.

Start a session: use `doctor` for a deterministic setup check, then `decide` once before a session begins. The shipped rule decider uses the native scope and price gates without a model call. A predicted saving is a prediction, not an observed invoice result. `launch --harness claude|codex|copilot --dry-run` shows the proposed startup command without starting that host; actual launch starts a process only within the user's authorized task. Avoid mid-session model switches. Opt-in judges require the documented credential and external-state consent before task text leaves the machine.

Inspect: run manifest, describe and diagnose --offline when a live service probe is unnecessary. Keep optional Jev/Laya/local providers separate from deterministic installation. A missing scorer is a setup finding, not a zero-quality result.

Select: supply only eligible relative read/list candidates and a bounded task. Selection is advisory; the host validates the returned offered ID, state freshness and its own approval boundary before executing anything. An abstention returns control to normal reasoning. Search may read bounded eligible sources; CUA only proposes an action.

Compare: use measure and compare on recorded matched runs with explicit task outcomes. Distinguish predicted savings from observed executions and invoiced cost. Local scores are not calibrated correctness. Read references/PRIVACY.md before enabling external scoring; existing user authorization governs whether particular data may leave the machine.

The retained native orchestrator, policies, receipts, observatory, benchmark records and CLI aliases remain available. Do not activate a host hook or stop an existing viewer as a side effect of installing the portable skill. Goal numbers in historical source records are targets, not results for this consolidation.
