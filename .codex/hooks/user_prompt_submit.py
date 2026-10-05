"""Resolve and inject only locally selected skill context for Codex prompts."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from agent.activation import activate  # noqa: E402
from agent.registry import load_registry  # noqa: E402
from agent.resolver import ResolutionInput, git_signals, manifest_bytes, resolve  # noqa: E402
from agent.validation import validate_catalog  # noqa: E402


def main() -> int:
    event = json.load(sys.stdin)
    prompt = event.get("prompt", "")
    if not isinstance(prompt, str):
        prompt = ""
    paths = tuple(sorted(set(re.findall(r"(?:^|\s)([A-Za-z0-9_.-]+/[A-Za-z0-9_./*-]+)", prompt))))
    changed, branch = git_signals(ROOT)
    registry = load_registry(ROOT)
    validate_catalog(registry)
    manifest = resolve(registry, ResolutionInput(prompt, paths, changed, branch))
    manifest_path = ROOT / ".agents" / "selection.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_bytes(manifest_bytes(manifest))
    active_dir = ROOT / ".agents" / "skills"
    activate(registry, ROOT, manifest, active_dir)
    snippets = []
    evidence = []
    for selected in manifest["selected"]:
        skill_id = selected["id"]
        content = (active_dir / skill_id / "SKILL.md").read_text(encoding="utf-8")
        snippets.append(f"--- Selected skill: {skill_id} ---\n{content}")
        if "reasons" in selected:
            reasons = selected["reasons"][:3]
            evidence.append(f"{skill_id}: {', '.join(reasons)}")
        else:
            evidence.append(f"{skill_id}: {selected['selected_by']}")
    context = "\n\n".join(
        [
            f"Deterministic skill selection (rules v{manifest['rules_version']}). "
            "Full catalog was not loaded.",
            f"Manifest: {manifest_path}",
            "Selected: " + (", ".join(item["id"] for item in manifest["selected"]) or "(empty)"),
            "Evidence: " + ("; ".join(evidence) or "no deterministic routing match"),
            "Full unabridged evidence is in the manifest.",
            *snippets,
        ]
    )
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": context,
                }
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
