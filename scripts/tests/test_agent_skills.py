from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from agent.activation import activate, check_activation  # noqa: E402
from agent.registry import RegistryError, load_registry  # noqa: E402
from agent.resolver import ResolutionError, ResolutionInput, manifest_bytes, resolve  # noqa: E402
from agent.validation import validate_catalog  # noqa: E402


class AgentSkillsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = load_registry(ROOT)
        validate_catalog(cls.registry)

    def selected(self, manifest: dict[str, object]) -> list[str]:
        return [item["id"] for item in manifest["selected"]]

    def test_auth_01_selects_backend_security_testing_without_platform_leakage(
        self,
    ) -> None:
        result = resolve(
            self.registry,
            ResolutionInput(task_text="Implement JWT authentication in Django"),
        )
        self.assertEqual(
            set(self.selected(result)), {"django-backend", "security-review", "testing"}
        )
        self.assertNotIn("react-web", self.selected(result))
        self.assertNotIn("expo-mobile", self.selected(result))

    def test_api_01_contract_includes_configured_closure(self) -> None:
        result = resolve(self.registry, ResolutionInput(task_text="Change OpenAPI contract"))
        self.assertEqual(set(self.selected(result)), {"api-contract", "testing"})
        self.assertEqual(
            next(item for item in result["selected"] if item["id"] == "testing")["selected_by"],
            "implied:api-contract",
        )

    def test_web_01_has_no_backend_or_mobile_leakage(self) -> None:
        result = resolve(self.registry, ResolutionInput(target_paths=("apps/web/src/App.tsx",)))
        self.assertEqual(set(self.selected(result)), {"react-web", "testing"})
        self.assertNotIn("django-backend", self.selected(result))
        self.assertNotIn("expo-mobile", self.selected(result))

    def test_mobile_01_includes_component_library_and_testing(self) -> None:
        result = resolve(
            self.registry, ResolutionInput(target_paths=("apps/mobile/app/index.tsx",))
        )
        self.assertEqual(
            set(self.selected(result)),
            {"expo-mobile", "mobile-component-library", "testing"},
        )

    def test_docker_01_selects_docker_development(self) -> None:
        result = resolve(
            self.registry, ResolutionInput(task_text="Update Docker Compose containers")
        )
        self.assertIn("docker-development", self.selected(result))

    def test_none_01_is_a_valid_empty_selection(self) -> None:
        self.assertEqual(
            resolve(self.registry, ResolutionInput()),
            {"version": 1, "rules_version": 1, "max_skills": 5, "selected": []},
        )

    def test_determinism_01_order_and_manifest_bytes_are_stable(self) -> None:
        signals = ResolutionInput(
            task_text="JWT authentication",
            target_paths=("apps/backend/apps/accounts/views.py",),
        )
        first = resolve(self.registry, signals)
        second = resolve(self.registry, signals)
        self.assertEqual(first, second)
        self.assertEqual(manifest_bytes(first), manifest_bytes(second))

    def test_cap_01_refuses_to_truncate_closure(self) -> None:
        with self.assertRaisesRegex(ResolutionError, "exceeding max_skills=2"):
            resolve(
                self.registry,
                ResolutionInput(task_text="JWT authentication in Django", max_skills=2),
            )

    def test_requires_closure_is_complete_and_fails_instead_of_truncating(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            catalog = root / ".agent-system"
            lines = ["[settings]", "max_skills = 3"]
            dependencies = {"a": "b", "b": "c", "c": "d", "d": None}
            for skill_id, dependency in dependencies.items():
                folder = catalog / "skills" / skill_id
                folder.mkdir(parents=True)
                (folder / "SKILL.md").write_text(
                    f"---\nname: {skill_id}\ndescription: Test skill {skill_id}\n---\n"
                )
                lines.extend(
                    [
                        "",
                        "[[skills]]",
                        f'id = "{skill_id}"',
                        f'path = "skills/{skill_id}"',
                        "priority = 1",
                    ]
                )
                if skill_id == "a":
                    lines.append('keywords = ["root-task"]')
                if dependency:
                    lines.append(f'requires = ["{dependency}"]')
            (catalog / "registry.toml").write_text("\n".join(lines) + "\n")
            registry = load_registry(root)
            with self.assertRaisesRegex(ResolutionError, "exceeding max_skills=3"):
                resolve(registry, ResolutionInput(task_text="root-task"))

    def test_precedence_and_tie_breaking_are_stable(self) -> None:
        result = resolve(
            self.registry,
            ResolutionInput(target_paths=("README.md", "apps/web/src/main.tsx")),
        )
        ids = self.selected(result)
        self.assertEqual(ids[:2], ["react-web", "repo-readme"])
        self.assertEqual(
            ids,
            sorted(
                ids,
                key=lambda item: (
                    -next(
                        (x.get("score", 0) for x in result["selected"] if x["id"] == item),
                        0,
                    ),
                    -self.registry.skills[item].priority,
                    item,
                ),
            ),
        )

    def test_equal_score_and_priority_tie_breaks_by_skill_id(self) -> None:
        skills = dict(self.registry.skills)
        skills["react-web"] = replace(skills["react-web"], priority=70)
        skills["repo-readme"] = replace(skills["repo-readme"], priority=70)
        registry = replace(self.registry, skills=skills)
        result = resolve(
            registry,
            ResolutionInput(target_paths=("README.md", "apps/web/src/main.tsx")),
        )
        self.assertEqual(self.selected(result)[:2], ["react-web", "repo-readme"])

    def test_activation_removes_stale_skills_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".agents" / "skills" / "stale").mkdir(parents=True)
            (root / ".agents" / "skills" / "stale" / "SKILL.md").write_text("stale")
            (root / ".agent-system").mkdir()
            # Use the production canonical catalog and a temporary repository destination.
            registry = self.registry
            manifest = resolve(registry, ResolutionInput(task_text="OpenAPI contract"))
            target = activate(registry, root, manifest, Path(".agents/skills"))
            snapshot = sorted(
                (p.relative_to(target).as_posix(), p.read_bytes())
                for p in target.rglob("*")
                if p.is_file()
            )
            activate(registry, root, manifest, Path(".agents/skills"))
            actual = sorted(
                (p.relative_to(target).as_posix(), p.read_bytes())
                for p in target.rglob("*")
                if p.is_file()
            )
            self.assertEqual(snapshot, actual)
            self.assertFalse((target / "stale").exists())

    def test_check_detects_stale_active_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".agent-system").mkdir()
            manifest = resolve(self.registry, ResolutionInput(task_text="OpenAPI contract"))
            manifest_path = root / ".agents" / "selection.json"
            manifest_path.parent.mkdir()
            manifest_path.write_bytes(manifest_bytes(manifest))
            with self.assertRaisesRegex(ValueError, "active skills differ"):
                check_activation(self.registry, root, manifest_path, Path(".agents/skills"))

    def test_check_rejects_tracked_generated_active_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            git_path = shutil.which("git")
            self.assertIsNotNone(git_path)
            subprocess.run(  # noqa: S603 - fixed local Git subcommands
                [git_path, "init", "--quiet", str(root)], check=True
            )
            generated = root / ".agents" / "skills" / "example"
            generated.mkdir(parents=True)
            (generated / "SKILL.md").write_text("generated")
            subprocess.run(  # noqa: S603 - fixed local Git subcommands
                [git_path, "-C", str(root), "add", ".agents/skills"], check=True
            )
            with self.assertRaisesRegex(ValueError, "must not be tracked"):
                check_activation(
                    self.registry,
                    root,
                    root / ".agents" / "selection.json",
                    Path(".agents/skills"),
                )

    def test_invalid_registry_entries_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".agent-system" / "skills" / "demo").mkdir(parents=True)
            (root / ".agent-system" / "skills" / "demo" / "SKILL.md").write_text(
                "---\nname: other\ndescription: Demo\n---\n"
            )
            (root / ".agent-system" / "registry.toml").write_text("[settings]\nmax_skills=0\n")
            with self.assertRaisesRegex(RegistryError, "max_skills"):
                load_registry(root)

    def test_duplicate_ids_missing_skill_and_invalid_frontmatter_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            catalog = root / ".agent-system"
            skill = catalog / "skills" / "demo"
            skill.mkdir(parents=True)
            registry_path = catalog / "registry.toml"
            entry = '[[skills]]\nid="demo"\npath="skills/demo"\npriority=1\n'
            valid = "[settings]\nmax_skills=5\n" + entry
            (skill / "SKILL.md").write_text("---\nname: demo\ndescription: Demo skill\n---\n")
            registry_path.write_text(valid + entry)
            with self.assertRaisesRegex(RegistryError, "duplicate registry id"):
                load_registry(root)
            registry_path.write_text(valid.replace('path="skills/demo"', 'path="skills/missing"'))
            with self.assertRaisesRegex(RegistryError, "missing"):
                load_registry(root)
            registry_path.write_text(valid)
            (skill / "SKILL.md").write_text("---\nname demo\ndescription: broken\n---\n")
            with self.assertRaisesRegex(RegistryError, "frontmatter"):
                load_registry(root)

    def test_dependency_failure_cycle_and_path_escape_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            skills = root / ".agent-system" / "skills"
            for name in ("a", "b"):
                folder = skills / name
                folder.mkdir(parents=True)
                (folder / "SKILL.md").write_text(f"---\nname: {name}\ndescription: Demo\n---\n")
            registry_text = (
                "[settings]\nmax_skills=5\n"
                '[[skills]]\nid="a"\npath="skills/a"\npriority=1\nimplies=["b"]\n'
                '[[skills]]\nid="b"\npath="skills/b"\npriority=1\nrequires=["a"]\n'
            )
            (root / ".agent-system" / "registry.toml").write_text(registry_text)
            with self.assertRaisesRegex(RegistryError, "cycle"):
                load_registry(root)
            (root / ".agent-system" / "registry.toml").write_text(
                registry_text.replace('path="skills/a"', 'path="../../outside"')
            )
            with self.assertRaisesRegex(RegistryError, "escapes"):
                load_registry(root)

    def test_unresolved_dependency_and_invalid_path_pattern_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / ".agent-system" / "skills" / "demo"
            folder.mkdir(parents=True)
            (folder / "SKILL.md").write_text("---\nname: demo\ndescription: Demo\n---\n")
            registry_path = root / ".agent-system" / "registry.toml"
            base = (
                '[settings]\nmax_skills=5\n[[skills]]\nid="demo"\npath="skills/demo"\npriority=1\n'
            )
            registry_path.write_text(base + 'implies=["missing"]\n')
            with self.assertRaisesRegex(RegistryError, "unresolved dependency"):
                load_registry(root)
            registry_path.write_text(base + 'path_globs=["apps/[web/**"]\n')
            with self.assertRaisesRegex(RegistryError, "invalid path pattern"):
                load_registry(root)

    def test_unsafe_activation_destination_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = resolve(self.registry, ResolutionInput())
            with self.assertRaisesRegex(ValueError, "unsafe activation destination"):
                activate(self.registry, root, manifest, Path("outside/skills"))

    def test_cli_has_fixed_phase_order_independent_of_flag_order(self) -> None:
        commands = [
            [
                sys.executable,
                "scripts/agent/cli.py",
                "--activate",
                "--resolve",
                "--validate",
                "--check",
                "--task",
                "",
            ],
            [
                sys.executable,
                "scripts/agent/cli.py",
                "--check",
                "--validate",
                "--resolve",
                "--activate",
                "--task",
                "",
            ],
        ]
        outputs = [
            subprocess.run(  # noqa: S603 - fixed Python executable and repo-owned script
                command, cwd=ROOT, check=True, capture_output=True
            ).stdout
            for command in commands
        ]
        self.assertEqual(outputs[0], outputs[1])

    def test_codex_prompt_hook_injects_only_selected_skill_context(self) -> None:
        event = json.dumps({"prompt": "Update the OpenAPI contract"})
        result = subprocess.run(  # noqa: S603 - fixed Python executable and repo-owned hook
            [sys.executable, ".codex/hooks/user_prompt_submit.py"],
            cwd=ROOT,
            input=event,
            text=True,
            check=True,
            capture_output=True,
        )
        context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Selected skill: api-contract", context)
        self.assertIn("Selected skill: testing", context)
        self.assertNotIn("Selected skill: django-backend", context)
        self.assertNotIn("Selected skill: expo-mobile", context)
        self.assertIn("Full unabridged evidence is in the manifest.", context)
        self.assertNotIn('"reasons":', context)
        self.assertEqual(
            sorted(path.name for path in (ROOT / ".agents/skills").iterdir()),
            ["api-contract", "testing"],
        )


if __name__ == "__main__":
    unittest.main()
