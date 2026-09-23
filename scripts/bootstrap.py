#!/usr/bin/env python3
"""Initialize a clone by changing only explicitly owned identity/config files."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

SLUG = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
PYTHON_PACKAGE = re.compile(r"^[a-z][a-z0-9_]*$")
BUNDLE_ID = re.compile(r"^[A-Za-z][A-Za-z0-9-]*(?:\.[A-Za-z0-9-]+)+$")


def slugify(name: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return value


def collect(args: argparse.Namespace, root: Path) -> dict:
    name = args.name or input("Product name [Acme Product]: ").strip() or "Acme Product"
    slug = args.slug or slugify(name)
    python_package = args.python_package or slug.replace("-", "_")
    bundle_id = args.bundle_id or f"com.example.{slug.replace('-', '.')}"
    if not SLUG.fullmatch(slug):
        raise ValueError("--slug must use lowercase letters, digits and single hyphens")
    if not PYTHON_PACKAGE.fullmatch(python_package):
        raise ValueError("--python-package must be a lowercase Python identifier")
    if not BUNDLE_ID.fullmatch(bundle_id):
        raise ValueError("--bundle-id must be a dotted native bundle identifier")
    web_port = args.web_port or 5173
    api_port = args.api_port or 8000
    if web_port == api_port or not (1024 <= web_port <= 65535 and 1024 <= api_port <= 65535):
        raise ValueError("Ports must be unique unprivileged TCP ports")
    return {
        "initialized": True,
        "name": name,
        "slug": slug,
        "pythonPackage": python_package,
        "bundleId": bundle_id,
        "ports": {"web": web_port, "api": api_port},
    }


def bootstrap(root: Path, config: dict) -> None:
    config_path = root / "product-template.json"
    marker_path = root / ".template-initialized.json"
    current = json.loads(config_path.read_text(encoding="utf-8"))
    if current.get("initialized") or marker_path.exists():
        raise ValueError("This clone is already initialized; refusing to rename it again")

    name, slug, bundle = config["name"], config["slug"], config["bundleId"]
    web_port, api_port = config["ports"]["web"], config["ports"]["api"]
    replacements = {
        "package.json": [('"name": "template-fullstack"', f'"name": "{slug}"')],
        "compose.yaml": [("template-fullstack", slug)],
        ".env.example": [
            ("template-fullstack", slug),
            ("WEB_PORT=5173", f"WEB_PORT={web_port}"),
            ("API_PORT=8000", f"API_PORT={api_port}"),
            (
                "DJANGO_CORS_ALLOWED_ORIGINS=http://localhost:5173",
                f"DJANGO_CORS_ALLOWED_ORIGINS=http://localhost:{web_port}",
            ),
            (
                "DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:5173",
                f"DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:{web_port}",
            ),
            (
                "API_BASE_URL=http://localhost:8000/api/v1",
                f"API_BASE_URL=http://localhost:{api_port}/api/v1",
            ),
            (
                "EXPO_PUBLIC_API_URL=http://localhost:8000/api/v1",
                f"EXPO_PUBLIC_API_URL=http://localhost:{api_port}/api/v1",
            ),
        ],
        "apps/backend/pyproject.toml": [('name = "template-backend"', f'name = "{slug}-backend"')],
        "apps/backend/uv.lock": [('name = "template-backend"', f'name = "{slug}-backend"')],
        "apps/web/index.html": [("<title>Product</title>", f"<title>{html.escape(name)}</title>")],
        "apps/web/src/routes/App.tsx": [
            ("<strong>Product</strong>", f"<strong>{{{json.dumps(name)}}}</strong>")
        ],
        "apps/mobile/app.json": [
            ('"name": "Product"', f'"name": {json.dumps(name)}'),
            ('"slug": "product"', f'"slug": {json.dumps(slug)}'),
            ('"scheme": "product"', f'"scheme": {json.dumps(slug)}'),
            (
                '"bundleIdentifier": "com.example.product"',
                f'"bundleIdentifier": {json.dumps(bundle)}',
            ),
            ('"package": "com.example.product"', f'"package": {json.dumps(bundle)}'),
        ],
    }
    updates: dict[Path, str] = {}
    for relative, pairs in replacements.items():
        target = root / relative
        contents = target.read_text(encoding="utf-8")
        for before, after in pairs:
            if before not in contents:
                raise ValueError(f"Expected template identity not found in {target}")
            contents = contents.replace(before, after)
        updates[target] = contents
    for target, contents in updates.items():
        target.write_text(contents, encoding="utf-8")
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    marker_path.write_text(
        json.dumps({"slug": slug, "initialized": True}, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name")
    parser.add_argument("--slug")
    parser.add_argument("--python-package")
    parser.add_argument("--bundle-id")
    parser.add_argument("--web-port", type=int)
    parser.add_argument("--api-port", type=int)
    parser.add_argument("--non-interactive", action="store_true")
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1], help=argparse.SUPPRESS
    )
    args = parser.parse_args()
    if args.non_interactive and not args.name:
        parser.error("--name is required with --non-interactive")
    try:
        config = collect(args, args.root)
        bootstrap(args.root, config)
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"Bootstrap stopped: {exc}", file=sys.stderr)
        return 2
    print(
        f"Initialized {config['name']} ({config['slug']}). Personal mobile UI dependency preserved."
    )
    print("Next: copy .env.example to .env, run make setup, then make dev.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
