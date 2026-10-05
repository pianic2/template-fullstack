"""Load and validate the local skill registry without network access."""

from __future__ import annotations

import fnmatch
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


class RegistryError(ValueError):
    """Raised when the catalog or routing registry is invalid."""


@dataclass(frozen=True)
class Skill:
    id: str
    path: str
    priority: int
    path_globs: tuple[str, ...]
    keywords: tuple[str, ...]
    regexes: tuple[str, ...]
    labels: tuple[str, ...]
    requires: tuple[str, ...]
    implies: tuple[str, ...]


@dataclass(frozen=True)
class Registry:
    root: Path
    skills: dict[str, Skill]
    max_skills: int
    minimum_score: int


def _string_list(value: object, where: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise RegistryError(f"{where} must be an array of non-empty strings")
    return tuple(value)


def _safe_glob(pattern: str) -> bool:
    if not pattern or "\\" in pattern or pattern.startswith("/"):
        return False
    if not all(part != ".." for part in PurePosixPath(pattern).parts):
        return False
    offset = 0
    while "[" in pattern[offset:]:
        start = pattern.index("[", offset)
        end = pattern.find("]", start + 1)
        if end < 0:
            return False
        offset = end + 1
    return "]" not in pattern[offset:]


def _parse_frontmatter(raw: str, skill_id: str) -> dict[str, str]:
    match = re.match(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", raw, re.S)
    if not match:
        raise RegistryError(f"{skill_id}: invalid SKILL.md frontmatter")
    values: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, separator, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if not separator or not re.fullmatch(r"[A-Za-z0-9_-]+", key) or not value or key in values:
            raise RegistryError(f"{skill_id}: invalid SKILL.md frontmatter line {line!r}")
        if value[:1] in {"'", '"'}:
            quote = value[0]
            if len(value) < 2 or value[-1] != quote:
                raise RegistryError(f"{skill_id}: invalid quoted frontmatter value")
            value = value[1:-1]
        values[key] = value
    if not values.get("name") or not values.get("description"):
        raise RegistryError(f"{skill_id}: frontmatter requires name and description")
    return values


def load_registry(repo_root: Path) -> Registry:
    catalog = (repo_root / ".agent-system").resolve()
    registry_path = catalog / "registry.toml"
    try:
        raw = tomllib.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise RegistryError(f"cannot load {registry_path}: {error}") from error
    settings = raw.get("settings", {})
    if not isinstance(settings, dict):
        raise RegistryError("settings must be a table")
    max_skills = settings.get("max_skills", 5)
    if not isinstance(max_skills, int) or isinstance(max_skills, bool) or max_skills < 1:
        raise RegistryError("settings.max_skills must be a positive integer")
    minimum_score = settings.get("minimum_score", 1)
    if not isinstance(minimum_score, int) or isinstance(minimum_score, bool) or minimum_score < 1:
        raise RegistryError("settings.minimum_score must be a positive integer")
    if settings.get("scoring_version", 1) != 1:
        raise RegistryError("settings.scoring_version must be 1")
    entries = raw.get("skills")
    if not isinstance(entries, list):
        raise RegistryError("registry must contain [[skills]] entries")
    skills: dict[str, Skill] = {}
    for index, item in enumerate(entries):
        where = f"skills[{index}]"
        if not isinstance(item, dict):
            raise RegistryError(f"{where} must be a table")
        skill_id = item.get("id")
        skill_path = item.get("path")
        priority = item.get("priority")
        if not isinstance(skill_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", skill_id):
            raise RegistryError(f"{where}.id is invalid")
        if skill_id in skills:
            raise RegistryError(f"duplicate registry id: {skill_id}")
        if not isinstance(skill_path, str):
            raise RegistryError(f"{where}.path must be a string")
        resolved = (catalog / skill_path).resolve()
        if resolved.parent != (catalog / "skills").resolve() or not resolved.is_dir():
            raise RegistryError(f"{skill_id}: path escapes or is missing from canonical catalog")
        if not isinstance(priority, int) or isinstance(priority, bool):
            raise RegistryError(f"{skill_id}: priority must be an integer")
        if priority < 0:
            raise RegistryError(f"{skill_id}: priority must be non-negative")
        globs = _string_list(item.get("path_globs", []), f"{skill_id}.path_globs")
        if any(
            not _safe_glob(pattern) or pattern.count("[") != pattern.count("]") for pattern in globs
        ):
            raise RegistryError(f"{skill_id}: invalid path pattern")
        keywords = _string_list(item.get("keywords", []), f"{skill_id}.keywords")
        regexes = _string_list(item.get("regexes", []), f"{skill_id}.regexes")
        for expression in regexes:
            try:
                re.compile(expression, re.IGNORECASE)
            except re.error as error:
                raise RegistryError(f"{skill_id}: invalid regex {expression!r}: {error}") from error
        labels = _string_list(item.get("labels", []), f"{skill_id}.labels")
        requires = _string_list(item.get("requires", []), f"{skill_id}.requires")
        implies = _string_list(item.get("implies", []), f"{skill_id}.implies")
        metadata = resolved / "SKILL.md"
        if not metadata.is_file():
            raise RegistryError(f"{skill_id}: missing SKILL.md")
        front = _parse_frontmatter(metadata.read_text(encoding="utf-8"), skill_id)
        if front["name"] != skill_id or resolved.name != skill_id:
            raise RegistryError(f"{skill_id}: registry/directory/frontmatter name mismatch")
        if any(path.is_symlink() for path in resolved.rglob("*")):
            raise RegistryError(f"{skill_id}: symlinks are not allowed in canonical skill content")
        skills[skill_id] = Skill(
            skill_id,
            skill_path,
            priority,
            globs,
            keywords,
            regexes,
            labels,
            requires,
            implies,
        )
    for skill in skills.values():
        for dependency in (*skill.requires, *skill.implies):
            if dependency not in skills:
                raise RegistryError(f"{skill.id}: unresolved dependency {dependency}")
            if dependency == skill.id:
                raise RegistryError(f"{skill.id}: self dependency")
    _check_cycles(skills)
    return Registry(catalog, skills, max_skills, minimum_score)


def _check_cycles(skills: dict[str, Skill]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(skill_id: str) -> None:
        if skill_id in visiting:
            raise RegistryError(f"requires/implies cycle includes {skill_id}")
        if skill_id in visited:
            return
        visiting.add(skill_id)
        skill = skills[skill_id]
        for dependency in sorted((*skill.requires, *skill.implies)):
            visit(dependency)
        visiting.remove(skill_id)
        visited.add(skill_id)

    for skill_id in sorted(skills):
        visit(skill_id)


def matches_glob(path: str, pattern: str) -> bool:
    """Match repository-relative POSIX paths with ** support."""
    return fnmatch.fnmatchcase(path, pattern) or (
        pattern.startswith("**/") and fnmatch.fnmatchcase(path, pattern[3:])
    )
