import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for relative in [
            "product-template.json",
            "package.json",
            "compose.yaml",
            ".env.example",
            "apps/backend/pyproject.toml",
            "apps/web/index.html",
            "apps/web/src/routes/App.tsx",
            "apps/mobile/app.json",
            "apps/mobile/package.json",
        ]:
            source = ROOT / relative
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(source, target)

    def tearDown(self):
        self.temp.cleanup()

    def run_bootstrap(self, *extra):
        return subprocess.run(
            ["python3", str(ROOT / "scripts/bootstrap.py"), "--root", str(self.root), *extra],
            capture_output=True,
            text=True,
        )

    def test_renames_scoped_identity_and_preserves_external_library(self):
        result = self.run_bootstrap(
            "--name",
            "Acme Video",
            "--slug",
            "acme-video",
            "--python-package",
            "acme_video",
            "--bundle-id",
            "com.acme.video",
            "--non-interactive",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        app = json.loads((self.root / "apps/mobile/app.json").read_text())["expo"]
        mobile = json.loads((self.root / "apps/mobile/package.json").read_text())
        config = json.loads((self.root / "product-template.json").read_text())
        self.assertEqual(app["ios"]["bundleIdentifier"], "com.acme.video")
        self.assertEqual(app["android"]["package"], "com.acme.video")
        self.assertEqual(config["pythonPackage"], "acme_video")
        self.assertEqual(
            mobile["dependencies"]["@personal-library/react-native-components"], "0.1.0-rc.2"
        )
        self.assertTrue((self.root / ".template-initialized.json").exists())

    def test_second_run_refuses_to_mutate_project(self):
        first = self.run_bootstrap("--name", "Acme", "--non-interactive")
        self.assertEqual(first.returncode, 0, first.stderr)
        second = self.run_bootstrap("--name", "Another", "--non-interactive")
        self.assertEqual(second.returncode, 2)
        self.assertIn("already initialized", second.stderr)

    def test_rejects_invalid_python_package(self):
        result = self.run_bootstrap(
            "--name", "Acme", "--python-package", "not-valid", "--non-interactive"
        )
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
