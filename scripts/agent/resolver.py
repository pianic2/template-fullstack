"""Stable zero-inference skill resolution."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from agent.registry import Registry

RULES_VERSION = 1


@dataclass(frozen=True)
class ResolutionInput:
    task_text: str = ""
    target_paths: tuple[str, ...] = ()
    changed_paths: tuple[str, ...] = ()
    branch: str = ""
    labels: tuple[str, ...] = ()
    max_skills: int | None = None


class ResolutionError(ValueError):
    """Raised when valid selection cannot fit the configured cap."""


def normalize_path(path: str) -> str:
    return path.replace("\\", "/").removeprefix("./").strip("/")


def resolve(registry: Registry, inputs: ResolutionInput) -> dict[str, object]:
    text = " ".join((inputs.task_text, inputs.branch)).casefold()
    paths = sorted(
        {
            normalize_path(path)
            for path in (*inputs.target_paths, *inputs.changed_paths)
            if normalize_path(path)
        }
    )
    labels = {label.casefold() for label in inputs.labels}
    scores: dict[str, int] = {}
    reasons: dict[str, list[str]] = {}
    for skill_id in sorted(registry.skills):
        skill = registry.skills[skill_id]
        score = 0
        evidence: list[str] = []
        for path in paths:
            if any(fnmatch_path(path, pattern) for pattern in skill.path_globs):
                score += 250
                evidence.append(f"path:{path}")
        for keyword in sorted(skill.keywords):
            if re.search(rf"(?<![\w]){re.escape(keyword.casefold())}(?![\w])", text):
                score += 40
                evidence.append(f"keyword:{keyword.casefold()}")
        for expression in sorted(skill.regexes):
            if re.search(expression, text, re.IGNORECASE):
                score += 50
                evidence.append(f"regex:{expression}")
        for label in sorted(labels.intersection(skill.labels)):
            score += 80
            evidence.append(f"label:{label}")
        if score >= registry.minimum_score:
            scores[skill_id] = score
            reasons[skill_id] = sorted(evidence)

    selected_by: dict[str, str | None] = {skill_id: None for skill_id in scores}
    queue = sorted(scores)
    while queue:
        parent_id = queue.pop(0)
        parent = registry.skills[parent_id]
        dependencies = [(dependency, "required") for dependency in parent.requires]
        dependencies += [(dependency, "implied") for dependency in parent.implies]
        for dependency, reason_prefix in dependencies:
            if dependency not in selected_by:
                selected_by[dependency] = f"{reason_prefix}:{parent_id}"
                queue.append(dependency)
                queue.sort()

    maximum = inputs.max_skills if inputs.max_skills is not None else registry.max_skills
    if maximum < 1:
        raise ResolutionError("max_skills must be positive")
    if len(selected_by) > maximum:
        closure = ", ".join(sorted(selected_by))
        raise ResolutionError(
            "selection closure has "
            f"{len(selected_by)} skills, exceeding max_skills={maximum}: {closure}"
        )
    ordered = sorted(
        selected_by,
        key=lambda skill_id: (
            -scores.get(skill_id, 0),
            -registry.skills[skill_id].priority,
            skill_id,
        ),
    )
    selected: list[dict[str, object]] = []
    for skill_id in ordered:
        row: dict[str, object] = {"id": skill_id}
        if selected_by[skill_id] is None:
            row["score"] = scores[skill_id]
            row["reasons"] = reasons[skill_id]
        else:
            row["selected_by"] = selected_by[skill_id]
        selected.append(row)
    return {
        "version": 1,
        "rules_version": RULES_VERSION,
        "max_skills": maximum,
        "selected": selected,
    }


def fnmatch_path(path: str, pattern: str) -> bool:
    import fnmatch

    return fnmatch.fnmatchcase(path, pattern) or (
        pattern.startswith("**/") and fnmatch.fnmatchcase(path, pattern[3:])
    )


def manifest_bytes(manifest: dict[str, object]) -> bytes:
    return (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def git_signals(repo_root: Path) -> tuple[tuple[str, ...], str]:
    git_path = shutil.which("git")
    if git_path is None:
        return (), ""
    try:
        result = subprocess.run(  # noqa: S603 - fixed Git subcommands and arguments
            [
                git_path,
                "-C",
                str(repo_root),
                "status",
                "--short",
                "--untracked-files=all",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        branch = subprocess.run(  # noqa: S603 - fixed Git subcommands and arguments
            [git_path, "-C", str(repo_root), "branch", "--show-current"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return (), ""
    paths = []
    for line in result.stdout.splitlines():
        raw = line[3:] if len(line) > 3 else ""
        if " -> " in raw:
            raw = raw.split(" -> ", 1)[1]
        paths.append(raw.strip(' "'))
    return tuple(sorted(set(paths))), branch
