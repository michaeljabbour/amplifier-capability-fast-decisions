# Changelog

## 2026-10-30 — install recipe data boundary

- Keep all twelve Bash commands static and pass recipe inputs through official `step.env`, including pre-approval machine review.
- Restrict local judge probes to loopback HTTP(S), serialize model and evidence values as JSON data, and preserve the default-deny installation gate.
- Add offline command-injection, literal-argument, endpoint and read-only preflight regressions using fictional values and fake tools.

## 2026-10-30 — Reinstall identity

- Use the actual declared public distribution name consistently in both parts of the doctor reinstall hint, with the current public Git repository. Keep repository branding separate from package identity.

## 2026-10-28 — Film

- Add a 67-second film to the site, with captions, a transcript, a poster and a 15-second cut. The example in it is fictional, and it reports no results.

## 2026-10-28 — Public site and first-use guide

- Lead with the intended user, concrete benefits, a fictional output preview and a first task.
- Document canonical public clone/install steps, optional runtime requirements and the boundary of existing verification.
- Preserve native interfaces, source history and the retained integration guide.

## 0.3.0 - 2026-10-06

Ships the preregistered S1 decisions (holdout-v3: 60 scenarios no agent had run, 2 repetitions, Fable 5.1 and Opus 5.5;
`docs/evidence/2026-10-06-holdout-v3/` and `evals/paired/PREREGISTRATION-holdout-v3.md` on branch `v3/program`).

### Changed defaults

* **Session-start decider is the rule R\*, not Jev (H2).** `model_routing.start_policy: rules` with
  `complex_min_prompt_chars: null`: route every session to the cheap model unless the price gate, the scope gate
  (more than 300 files) or `keep_on_host` keeps it on the host. No model call, no consent: `allow_external_state` is now
  `false`. Jev and R\* were equivalent on Fable (cost 1.008x, 90% CI 1.000-1.019; turn-pass -0.003); the preregistered rule
  ships the simpler decider. Jev is an opt-in: `model_routing.start_policy: judge` + `allow_external_state: true`.
  `decide` reports `decider: rules`, `judge.status: not_used`.
* **Fable 5.1 gets the preregistered C\*_F (H1: 0.581x plain Fable, turn-pass -0.013).** New
  `effort_routing.by_host`; shipped `{claude-fable-5-1: {strong: medium}}` (host effort `medium`). Not the
  holdout-selected configuration (0.528x), which must replicate in S2 first.
* **`keep_on_host: {task_types: [review, explain]}` on by default (H7: lower bound -0.063 < -0.05).** Under `rules` the task
  type is a keyword proxy (`intent-kw-v1`): question-shaped first prompts stay on the host.
* **Opus 5.5 unchanged:** the price gate never routes, effort is the provider default (no candidate beat plain Opus;
  H4 not supported: plain medium 0.992x, upper bound 1.009).

### Added

* `effort_routing.by_host` (per-host override of `by_tier`, longest model-id prefix wins) and `effort.effort_by_tier`.
* `complex_min_prompt_chars: null` = no prompt-length rule under `rules` (an absent key still means 2000).
* `keep_on_host` is accepted under `start_policy: rules` (keyword classifier `rules.py`, identical to the frozen `intent-kw-v1`).
* `decide`: default decider follows the configured policy; `--decider <judge>` switches that one decision to
  `start_policy: judge`. `afast configure --mode active` writes `start_policy: judge`; `bundles/active-mlx.yaml` keeps its local judge.
* `afast doctor` / `diagnose` report the decider and the effort per host, and warn about an external judge only when one is in use.

### Compatibility

Existing configs that set `start_policy`, `by_tier` or `keep_on_host` explicitly behave as before (a user overlay is
deep-merged over the new defaults: set `start_policy: judge` to keep Jev). `keep_on_host` under `rules` is new.
