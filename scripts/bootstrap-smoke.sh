#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp_dir="$(mktemp -d)"
project_dir="$tmp_dir/generated-project"
server_pid=""
cleanup() {
  if [[ -n "$server_pid" ]]; then
    kill "$server_pid" 2>/dev/null || true
    wait "$server_pid" 2>/dev/null || true
  fi
  rm -rf "$tmp_dir"
}
trap cleanup EXIT
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
env = (root / ".env.example").read_text()
assert "DJANGO_CORS_ALLOWED_ORIGINS=http://localhost:15173" in env
assert "DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:15173" in env
assert "API_BASE_URL=http://localhost:18000/api/v1" in env
assert "EXPO_PUBLIC_API_URL=http://localhost:18000/api/v1" in env
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
docker compose -f "$project_dir/compose.yaml" config --format json | python3 -c '
import json, sys
services = json.load(sys.stdin)["services"]
assert services["web"]["environment"]["VITE_API_BASE_URL"] == "http://localhost:18000/api/v1"
assert services["backend"]["ports"][0]["published"] == "18000"
assert services["web"]["ports"][0]["published"] == "15173"
'

(cd "$project_dir/apps/backend" && uv sync --locked --all-groups)
(cd "$project_dir/apps/backend" && uv run python manage.py check)
(cd "$project_dir" && corepack pnpm install --frozen-lockfile)
(cd "$project_dir" && make lint typecheck test)
(cd "$project_dir/apps/backend" && uv run python manage.py migrate --noinput)
python3 - <<'PY'
import socket

with socket.socket() as probe:
    probe.bind(("127.0.0.1", 18000))
PY
(cd "$project_dir/apps/backend" && DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1 exec .venv/bin/python manage.py runserver 127.0.0.1:18000 --noreload) >"$tmp_dir/backend.log" 2>&1 &
server_pid=$!
python3 - "$server_pid" "$tmp_dir/backend.log" <<'PY'
import json
import os
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

server_pid = int(sys.argv[1])
for attempt in range(30):
    try:
        os.kill(server_pid, 0)
    except ProcessLookupError:
        raise SystemExit(f"Generated API exited before readiness:\n{open(sys.argv[2]).read()}")
    try:
        with urlopen("http://127.0.0.1:18000/api/v1/health/ready", timeout=2) as response:
            assert response.status == 200
            assert json.load(response)["dependencies"]["database"] == "ok"
        print("Generated API readiness returned HTTP 200 with database ok.")
        break
    except (URLError, TimeoutError):
        time.sleep(1)
else:
    raise SystemExit(f"Generated API did not become ready:\n{open(sys.argv[2]).read()}")
PY
kill "$server_pid" 2>/dev/null || true
wait "$server_pid" 2>/dev/null || true
server_pid=""
(cd "$project_dir" && corepack pnpm --filter @template/web build)
test -f "$project_dir/apps/web/dist/index.html"
grep -q '<title>Acme Video</title>' "$project_dir/apps/web/dist/index.html"
(cd "$project_dir" && EXPO_PUBLIC_API_URL=https://api.example.com/api/v1 corepack pnpm --filter @template/mobile exec expo export --platform android)
echo "Generated-project bootstrap smoke checks passed."
