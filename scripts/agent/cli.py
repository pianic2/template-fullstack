"""Single public CLI for validation, deterministic resolution, and activation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.activation import activate, check_activation
from agent.registry import RegistryError, load_registry
from agent.resolver import (
    ResolutionError,
    ResolutionInput,
    git_signals,
    manifest_bytes,
    resolve,
)
from agent.validation import validate_catalog


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument(
        "--validate",
        action="store_true",
        help="validate registry, catalog, paths and dependency graph",
    )
    result.add_argument(
        "--resolve",
        action="store_true",
        help="resolve deterministic local routing signals",
    )
    result.add_argument(
        "--activate",
        action="store_true",
        help="materialize exactly the resolved skills",
    )
    result.add_argument(
        "--check",
        action="store_true",
        help="check any existing manifest and active subset",
    )
    result.add_argument("--task", default="", help="explicit task text signal")
    result.add_argument(
        "--target-path",
        action="append",
        default=[],
        help="explicit repository-relative target path (repeatable)",
    )
    result.add_argument(
        "--label",
        action="append",
        default=[],
        help="explicit label signal (repeatable)",
    )
    result.add_argument("--max-skills", type=int, help="override registry max_skills")
    result.add_argument(
        "--manifest",
        type=Path,
        default=Path(".agents/selection.json"),
        help="machine-readable manifest destination",
    )
    result.add_argument(
        "--destination",
        type=Path,
        default=Path(".agents/skills"),
        help="active skills directory",
    )
    result.add_argument(
        "--json", action="store_true", help="print machine-readable selection evidence"
    )
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = Path.cwd().resolve()
    try:
        registry = load_registry(root)
        validate_catalog(registry)
        if args.validate:
            print(
                f"Validated {len(registry.skills)} canonical skills (routing rules v1).",
                file=sys.stderr if args.json else sys.stdout,
            )
        manifest = None
        if args.resolve or args.activate:
            changed_paths, branch = git_signals(root)
            manifest = resolve(
                registry,
                ResolutionInput(
                    args.task,
                    tuple(args.target_path),
                    changed_paths,
                    branch,
                    tuple(args.label),
                    args.max_skills,
                ),
            )
            manifest_path = args.manifest if args.manifest.is_absolute() else root / args.manifest
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_bytes(manifest_bytes(manifest))
            if args.activate:
                activate(registry, root, manifest, args.destination)
            if args.json:
                print(manifest_bytes(manifest).decode(), end="")
            else:
                print("Selection:")
                for item in manifest["selected"]:
                    evidence = item.get("reasons", [item.get("selected_by")])
                    print(f"- {item['id']}: {', '.join(evidence)}")
                if not manifest["selected"]:
                    print("- (empty)")
                display_path = (
                    manifest_path.relative_to(root)
                    if root in manifest_path.parents
                    else manifest_path
                )
                print(f"Manifest: {display_path}")
                if args.activate:
                    print(f"Activated {len(manifest['selected'])} skill(s).")
        if args.check:
            manifest_path = args.manifest if args.manifest.is_absolute() else root / args.manifest
            check_activation(registry, root, manifest_path, args.destination)
            print(
                "Active skill output is consistent.",
                file=sys.stderr if args.json else sys.stdout,
            )
        return 0
    except (
        RegistryError,
        ResolutionError,
        ValueError,
        OSError,
        json.JSONDecodeError,
    ) as error:
        print(f"agent-skills: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
