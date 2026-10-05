# Agent workflow

Start with root and scoped `AGENTS.md`. Repository skills are defined in `.agent-system/skills/` and routed by the local registry. See [Skill discovery](skills.md) for the Codex prompt hook and the generated active subset. OpenAPI, Django migrations and generated files have explicit ownership. One writer owns shared manifests/schema outputs at a time. Reviewer and architect roles are read-heavy; implementation agents return tests and exact evidence.

Delegate independent exploration, compatibility research or review when worthwhile; avoid splitting changes that touch the same contract, lockfile or generated output. Keep delegation optional and scoped to the task.
