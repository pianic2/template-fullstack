#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp_dir="$(mktemp -d)"
project_dir="$tmp_dir/generated-project"
trap 'rm -rf "$tmp_dir"' EXIT
export UV_CACHE_DIR="${UV_CACHE_DIR:-$tmp_dir/uv-cache}"
export COREPACK_HOME="${COREPACK_HOME:-$tmp_dir/corepack}"
mkdir -p "$project_dir"

# Copy the current worktree, including staged and unstaged tracked edits, without
# copying local environments, build output, or the Git metadata.
(cd "$repo_root" && git ls-files --cached --others --exclude-standard -z \
  | tar --create --file=- --null --files-from=-) \
  | tar --extract --file=- --directory="$project_dir"

python3 "$project_dir/scripts/bootstrap.py" \
  --root "$project_dir" \
  --name "Acme Video" \
  --slug "acme-video" \
  --python-package "acme_video" \
  --bundle-id "com.acme.video" \
  --web-port 15173 \
  --api-port 18000 \
  --non-interactive

python3 - "$project_dir" <<'PY'
import json
import sys
import tomllib
from pathlib import Path

root = Path(sys.argv[1])
package = json.loads((root / "package.json").read_text())
mobile = json.loads((root / "apps/mobile/app.json").read_text())["expo"]
template = json.loads((root / "product-template.json").read_text())
backend = tomllib.loads((root / "apps/backend/pyproject.toml").read_text())

assert package["name"] == "acme-video"
assert package["packageManager"] == "pnpm@12.5.1"
assert template["initialized"] is True
assert template["name"] == "Acme Video"
assert template["slug"] == "acme-video"
assert template["pythonPackage"] == "acme_video"
assert template["bundleId"] == "com.acme.video"
assert backend["project"]["name"] == "acme-video-backend"
assert mobile["name"] == "Acme Video"
assert mobile["slug"] == "acme-video"
assert mobile["scheme"] == "acme-video"
assert mobile["ios"]["bundleIdentifier"] == "com.acme.video"
assert mobile["android"]["package"] == "com.acme.video"
assert (root / ".template-initialized.json").is_file()
assert "template-fullstack" not in (root / "compose.yaml").read_text()
assert "@personal-library/react-native-components" in (
    root / "apps/mobile/package.json"
).read_text()

# Ensure every application and package remains a structurally valid pnpm workspace.
package_files = [*root.glob("apps/*/package.json"), *root.glob("packages/*/package.json")]
assert package_files
for package_file in package_files:
    workspace_package = json.loads(package_file.read_text())
    assert workspace_package["name"]
PY

cp "$project_dir/.env.example" "$project_dir/.env"
docker compose -f "$project_dir/compose.yaml" config --quiet

(cd "$project_dir/apps/backend" && uv sync --locked --all-groups)
(cd "$project_dir/apps/backend" && uv run python manage.py check)
(cd "$project_dir" && corepack pnpm install --frozen-lockfile)
(cd "$project_dir" && make lint typecheck test)
echo "Generated-project bootstrap smoke checks passed."
