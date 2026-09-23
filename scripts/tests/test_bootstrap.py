import json
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        fixtures = {
            "product-template.json": '{"initialized": false}\n',
            "package.json": '{"name": "template-fullstack"}\n',
            "compose.yaml": "name: ${COMPOSE_PROJECT_NAME:-template-fullstack}\n",
            ".env.example": (
                "COMPOSE_PROJECT_NAME=template-fullstack\nWEB_PORT=5173\nAPI_PORT=8000\n"
            ),
            "apps/backend/pyproject.toml": '[project]\nname = "template-backend"\n',
            "apps/backend/uv.lock": (
                'version = 1\nrequires-python = ">=3.13,<3.14"\n\n'
                '[[package]]\nname = "template-backend"\nversion = "0.1.0"\n'
                'source = { virtual = "." }\n'
            ),
            "apps/web/index.html": "<title>Product</title>\n",
            "apps/web/src/routes/App.tsx": "<strong>Product</strong>\n",
            "apps/mobile/app.json": json.dumps(
                {
                    "expo": {
                        "name": "Product",
                        "slug": "product",
                        "scheme": "product",
                        "ios": {"bundleIdentifier": "com.example.product"},
                        "android": {"package": "com.example.product"},
                    }
                }
            )
            + "\n",
            "apps/mobile/package.json": json.dumps(
                {"dependencies": {"@personal-library/react-native-components": "0.1.0-rc.2"}}
            )
            + "\n",
        }
        for relative, contents in fixtures.items():
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(contents)

    def tearDown(self):
        self.temp.cleanup()

    def run_bootstrap(self, *extra):
        return subprocess.run(
            [
                "python3",
                str(Path(__file__).resolve().parents[1] / "bootstrap.py"),
                "--root",
                str(self.root),
                *extra,
            ],
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
        backend = tomllib.loads((self.root / "apps/backend/pyproject.toml").read_text())
        lock = tomllib.loads((self.root / "apps/backend/uv.lock").read_text())
        locked_project = next(
            package for package in lock["package"] if package.get("source") == {"virtual": "."}
        )
        self.assertEqual(app["ios"]["bundleIdentifier"], "com.acme.video")
        self.assertEqual(app["android"]["package"], "com.acme.video")
        self.assertEqual(config["pythonPackage"], "acme_video")
        self.assertEqual(backend["project"]["name"], "acme-video-backend")
        self.assertEqual(locked_project["name"], backend["project"]["name"])
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
