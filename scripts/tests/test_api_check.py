from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "api-check.sh"


class ApiCheckTests(unittest.TestCase):
    def run_gate(self, action: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "scripts").mkdir()
            (root / "scripts" / "api-check.sh").write_bytes(SCRIPT.read_bytes())
            (root / "openapi").mkdir()
            (root / "openapi" / "openapi.yaml").write_text("openapi: baseline\n")
            generated = root / "packages" / "api-client" / "src" / "generated"
            generated.mkdir(parents=True)
            (generated / "api.ts").write_text("export const baseline = true;\n")
            (generated / "kept.ts").write_text("export const kept = true;\n")
            make = root / "bin" / "make"
            make.parent.mkdir()
            make.write_text(
                "#!/bin/sh\n"
                'case "$1" in\n'
                "  api-schema)\n" + action + "    ;;\n"
                "  api-client)\n    exit 0\n    ;;\n"
                "esac\n"
            )
            make.chmod(0o755)
            env = dict(os.environ, PATH=f"{make.parent}:{os.environ['PATH']}")
            return subprocess.run(  # noqa: S603 - runs a repo-owned script in an isolated fixture
                ["/bin/bash", "scripts/api-check.sh"],
                cwd=root,
                env=env,
                text=True,
                capture_output=True,
            )

    def test_generation_error_fails_canonical_check(self) -> None:
        self.assertNotEqual(self.run_gate("    exit 9\n").returncode, 0)

    def test_schema_drift_fails_canonical_check(self) -> None:
        result = self.run_gate("    printf 'openapi: stale\\n' > openapi/openapi.yaml\n")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("openapi.yaml", result.stdout)

    def test_generated_additions_changes_and_removals_fail_canonical_check(
        self,
    ) -> None:
        actions = [
            "    printf 'export const changed = true;\\n' "
            "> packages/api-client/src/generated/api.ts\n",
            "    printf 'export const added = true;\\n' "
            "> packages/api-client/src/generated/added.ts\n",
            "    rm packages/api-client/src/generated/kept.ts\n",
        ]
        for action in actions:
            with self.subTest(action=action):
                result = self.run_gate(action)
                self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
