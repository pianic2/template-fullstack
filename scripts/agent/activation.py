"""Safe, idempotent materialization of selected canonical skills."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from agent.registry import Registry


def _safe_destination(repo_root: Path, destination: Path) -> Path:
    root = repo_root.resolve()
    lexical = destination if destination.is_absolute() else root / destination
    lexical = Path(os.path.abspath(lexical))
    target = root / ".agents" / "skills"
    if lexical != target:
        raise ValueError(f"unsafe activation destination: {target}")
    if any(path.is_symlink() for path in (root / ".agents", target)):
        raise ValueError(f"activation destination must not be a symlink: {target}")
    return target


def activate(
    registry: Registry, repo_root: Path, manifest: dict[str, object], destination: Path
) -> Path:
    target = _safe_destination(repo_root, destination)
    catalog = registry.root.resolve()
    selected = manifest.get("selected")
    if not isinstance(selected, list):
        raise ValueError("manifest selected must be an array")
    names = [item.get("id") for item in selected if isinstance(item, dict)]
    if len(names) != len(selected) or len(names) != len(set(names)):
        raise ValueError("manifest contains malformed or duplicate skill entries")
    for name in names:
        if name not in registry.skills:
            raise ValueError(f"manifest references unknown skill: {name}")
        source = (catalog / registry.skills[name].path).resolve()
        if source.parent != (catalog / "skills").resolve() or not source.is_dir():
            raise ValueError(f"unsafe canonical skill path: {name}")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.parent / f".{target.name}.staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir()
    try:
        for name in sorted(names):
            shutil.copytree(catalog / registry.skills[name].path, staging / name)
        if target.exists():
            shutil.rmtree(target)
        staging.rename(target)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return target


def check_activation(
    registry: Registry, repo_root: Path, manifest_path: Path, destination: Path
) -> None:
    target = _safe_destination(repo_root, destination)
    git_path = shutil.which("git")
    if git_path:
        try:
            tracked = subprocess.run(  # noqa: S603 - fixed local Git query
                [git_path, "-C", str(repo_root), "ls-files", "--", ".agents/skills"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        except subprocess.CalledProcessError:
            tracked = ""
        if tracked:
            raise ValueError("generated active skills must not be tracked in Git")
    if not target.exists() and not manifest_path.exists():
        return
    if not manifest_path.is_file():
        raise ValueError("selection manifest is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    selected = manifest.get("selected", [])
    if not isinstance(selected, list) or any(
        not isinstance(item, dict) or item.get("id") not in registry.skills for item in selected
    ):
        raise ValueError("selection manifest contains an unknown or malformed skill")
    expected = sorted(item["id"] for item in selected)
    if len(expected) != len(set(expected)):
        raise ValueError("selection manifest contains duplicate skills")
    actual = sorted(path.name for path in target.iterdir()) if target.exists() else []
    if actual != expected:
        raise ValueError(f"active skills differ from manifest: expected {expected}, found {actual}")
    for skill_id in expected:
        canonical = (registry.root / registry.skills[skill_id].path).resolve()
        canonical_files = {
            file.relative_to(canonical).as_posix(): file
            for file in canonical.rglob("*")
            if file.is_file()
        }
        active_root = target / skill_id
        active_files = {
            file.relative_to(active_root).as_posix(): file
            for file in active_root.rglob("*")
            if file.is_file()
        }
        if set(canonical_files) != set(active_files):
            raise ValueError(f"active skill files differ from canonical source: {skill_id}")
        for relative, source in canonical_files.items():
            if source.read_bytes() != active_files[relative].read_bytes():
                raise ValueError(f"active skill is stale: {skill_id}/{relative}")
