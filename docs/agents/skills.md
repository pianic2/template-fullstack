# Deterministic Codex skill discovery

## Purpose and lifecycle

The skill router selects repository workflows from explicit prompt text, target paths, local changed paths, branch name, and optional labels. Routing is deterministic Python code: it makes no model calls, embedding requests, Jira/GitHub queries, or external HTTP requests.

`.agent-system/skills/` is the canonical catalog. `.agent-system/registry.toml` contains routing metadata only. `.agents/skills/` is generated output containing exactly the active subset, and `.agents/selection.json` records deterministic evidence. Never edit generated active copies; edit the canonical skill and resolve again.

In Codex, the trusted `UserPromptSubmit` hook reads the prompt before sending it to the model, collects local Git signals, validates the registry, resolves scores and dependency closure, writes the manifest, and materializes the selected skills. It returns only the selected `SKILL.md` content and manifest evidence through Codex `additionalContext`. Supporting references, scripts, and assets remain on disk and are opened by selected workflows as needed. Codex project hooks require reviewing and trusting the hook definition (use `/hooks`); the resolver itself has no network access.

```text
Codex prompt → local signals → deterministic score → requires/implies closure
             → stable order → max_skills gate → manifest → active subset + selected context
```

## Registry and routing rules

Every `[[skills]]` entry has `id`, canonical `path`, integer `priority`, and optional `path_globs`, `keywords`, `regexes`, `labels`, `requires`, and `implies`. The ID, directory name, and `SKILL.md` frontmatter `name` must match. Human-facing descriptions live only in `SKILL.md`.

Scoring version 1 adds:

- 250 for each matching repository-relative path (a path is counted once per skill);
- 40 for each matching whole-word/phrase keyword;
- 50 for each matching regex rule;
- 80 for each matching label.

The default minimum selection score is 1. Direct candidates are ordered by score descending, priority descending, then skill ID ascending. Dependency-only skills follow with score zero using the same priority and ID tie-breaks. Reasons are sorted before they enter the manifest. Filesystem iteration order does not affect resolution.

`requires` adds a structural prerequisite to the selection closure; the selected skill is unusable without it. `implies` adds a skill because the selected workflow calls for it. Both closures are resolved before the cap is checked. Any unresolved dependency or cycle is a validation error. A closure larger than `max_skills` (default 5) fails explicitly and is never truncated. Empty selection is valid.

## Developer interface

There is one public Make target:

```sh
make agent-skills ARGS="--resolve --check --task 'JWT authentication in Django'"
make agent-skills ARGS="--resolve --activate --check --task 'JWT authentication in Django'"
make agent-skills ARGS="--validate"
```

The CLI always validates first, resolves if `--resolve` or `--activate` was requested, writes evidence, activates if requested, then checks generated output. Flag order does not change phase order.

Supported flags:

- `--validate`: validate registry, catalog, metadata, patterns, and dependency graph.
- `--resolve`: resolve task text and local Git state without activating skills.
- `--activate`: resolve and materialize the exact active subset.
- `--check`: verify the existing manifest and active copies match.
- `--task TEXT`: provide explicit local task text.
- `--target-path PATH`: add a target path; repeat to provide more paths.
- `--label LABEL`: add a label; repeat to provide more labels.
- `--max-skills N`: override the registry cap for this run.
- `--manifest PATH`: choose the deterministic JSON evidence file (default `.agents/selection.json`).
- `--destination PATH`: specify activation destination; safe activation is restricted to `.agents/skills`.
- `--json`: print the manifest as JSON as well as writing it to disk.
- `--help`: show CLI usage.

The manifest has no timestamps. Direct selections include `score` and `reasons`; closure selections include `selected_by`, for example `implied:expo-mobile`. Human output reports the same selection IDs and evidence.

## Validation and tests

Validation is standard-library Python and works offline. It rejects duplicate IDs, missing/unregistered skill folders or `SKILL.md`, invalid frontmatter and mismatched names, paths outside the catalog, malformed path/regex rules, invalid priorities/configuration, unresolved/self dependencies, dependency cycles, skill-content symlinks, unsafe activation destinations, tracked generated active files, and stale active output.

Run the focused suite and canonical checks with:

```sh
python3 -m unittest discover -s scripts/tests -p test_agent_skills.py -v
make agent-skills ARGS="--validate --check"
make agent-skills ARGS="--resolve --activate --check"
```

`make test` includes the complete `scripts/tests` suite and registry validation. `make check` includes `make test`. CI has a separate lightweight skill job that needs only Python 3.13; it runs the canonical registry check and focused test suite.

## Adding a new skill

A normal skill addition changes only the canonical skill and registry data, plus its routing fixtures. Resolver, activation, Codex hook, CLI, and Makefile implementations stay unchanged.

1. Create `.agent-system/skills/example-workflow/SKILL.md` and put detailed instructions there:

   ```markdown
   ---
   name: example-workflow
   description: Apply the example workflow when editing the billing export pipeline.
   ---

   # Example workflow

   Inspect the billing export contract before changing its implementation.
   ```

2. Add its routing metadata to `.agent-system/registry.toml`:

   ```toml
   [[skills]]
   id = "example-workflow"
   path = "skills/example-workflow"
   priority = 70
   path_globs = ["apps/backend/apps/billing/exports/**"]
   keywords = ["billing export", "invoice export"]
   regexes = ["\\b(export|invoice)\\s+format\\b"]
   labels = ["billing"]
   requires = ["django-backend"]
   implies = ["testing"]
   ```

   Choose a discriminating path or task signal. Add only dependencies the workflow needs; `requires` means structural prerequisite and `implies` means co-selection.

3. Add a positive routing fixture asserting that a billing export task selects `example-workflow` and the expected closure. Add a negative assertion that a web-only task does not select it. This verifies both intended routing and non-leakage.

4. Validate and inspect selection evidence:

   ```sh
   make agent-skills ARGS="--validate"
   make agent-skills ARGS="--resolve --task 'Change the billing export format' --json"
   ```

   Confirm the manifest shows the expected direct `path:`, `keyword:`, or `regex:` reason and the appropriate `selected_by` entries. Run the focused tests before submitting.

## Troubleshooting

- **A skill does not route:** check whole-word spelling, case-insensitive keywords, path globs, optional label input, and the recorded reasons in `.agents/selection.json`.
- **Too many skills:** narrow broad path/keyword rules or raise `settings.max_skills` deliberately; do not truncate the dependency closure.
- **Hook does not run:** confirm the repository `.codex/` layer is trusted and use Codex `/hooks` to review/trust the current definition. Verify Python 3.13+ is available as `python3`.
- **Active output is stale:** run `make agent-skills ARGS="--resolve --activate --check"`.
- **Catalog validation fails:** fix the stated registry, frontmatter, path, or dependency mismatch in canonical source files, then rerun `--validate`.
