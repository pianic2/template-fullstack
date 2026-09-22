#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def version(command: list[str]) -> str:
    try:
        return (
            subprocess.check_output(command, text=True, stderr=subprocess.STDOUT)
            .strip()
            .splitlines()[0]
        )
    except (OSError, subprocess.CalledProcessError):
        return "not installed"


def main() -> int:
    checks = {
        "git": version(["git", "--version"]),
        "Docker Compose": version(["docker", "compose", "version", "--short"]),
        "Node": version(["node", "--version"]),
        "pnpm": version(["corepack", "pnpm", "--version"]),
        "Python 3.13": version(
            ["uv", "run", "--directory", str(ROOT / "apps/backend"), "python", "--version"]
        ),
        "uv": version(["uv", "--version"]),
    }
    for tool, value in checks.items():
        print(f"{tool:16} {value}")
    if not shutil.which("docker"):
        print("Docker is required for local PostgreSQL, Compose and production-image checks.")

    package_file = (
        ROOT / "apps/mobile/node_modules/@personal-library/react-native-components/package.json"
    )
    if not package_file.exists():
        package_file = ROOT / "node_modules/@personal-library/react-native-components/package.json"
    if package_file.exists():
        package = json.loads(package_file.read_text())
        peers = package.get("peerDependencies", {})
        react_peer = peers.get("react")
        react_native_peer = peers.get("react-native")
        print(f"Mobile library   {package['version']} (React {react_peer}, RN {react_native_peer})")
    else:
        print("Mobile library   not installed yet; run make setup")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
