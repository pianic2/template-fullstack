"""Catalog-level validation checks beyond registry parsing."""

from agent.registry import Registry, RegistryError


def validate_catalog(registry: Registry) -> None:
    directory = registry.root / "skills"
    actual = sorted(path.name for path in directory.iterdir() if path.is_dir())
    expected = sorted(registry.skills)
    if actual != expected:
        missing = sorted(set(expected) - set(actual))
        unregistered = sorted(set(actual) - set(expected))
        raise RegistryError(
            f"catalog and registry differ; missing={missing}, unregistered={unregistered}"
        )
