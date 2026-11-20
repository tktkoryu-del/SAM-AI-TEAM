import ast
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "services" / "runtime"
EXPECTED = {
    "ceo", "coo", "research", "strategy", "cto", "design",
    "video", "content", "marketing", "platforms", "finance", "quality",
}

class RepositoryAcceptanceTests(unittest.TestCase):
    def test_role_catalog_has_twelve_unique_roles(self):
        path = RUNTIME / "services.json"
        self.assertTrue(path.exists(), "services/runtime/services.json is missing")
        data = json.loads(path.read_text(encoding="utf-8"))
        keys = {item.get("key") for item in data}
        self.assertEqual(keys, EXPECTED)
        self.assertEqual(len(data), 12)

    def test_role_prompts_are_not_empty(self):
        path = RUNTIME / "service.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        prompts = None
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "SYSTEM_PROMPTS"
                for target in node.targets
            ):
                prompts = ast.literal_eval(node.value)
                break
        self.assertIsNotNone(prompts, "SYSTEM_PROMPTS dictionary is missing")
        self.assertEqual(set(prompts), EXPECTED)
        for role, prompt in prompts.items():
            self.assertTrue(prompt.strip(), f"empty role prompt: {role}")

    def test_runtime_contains_coordinator_and_worker(self):
        self.assertTrue((RUNTIME / "coordinator.py").exists())
        self.assertTrue((RUNTIME / "service.py").exists())

    def test_deployment_compose_declares_services(self):
        compose = RUNTIME / "docker-compose.yml"
        self.assertTrue(compose.exists())
        content = compose.read_text(encoding="utf-8")
        for role in sorted(EXPECTED):
            self.assertIn(role, content, f"compose missing {role}")

    def test_example_config_has_no_real_secrets(self):
        path = RUNTIME / ".env.example"
        self.assertTrue(path.exists(), "runtime .env.example is missing")
        content = path.read_text(encoding="utf-8")
        forbidden = ("sk-proj-", "ghp_", "github_pat_", "-----BEGIN PRIVATE KEY-----")
        for marker in forbidden:
            self.assertNotIn(marker, content)

    def test_user_startup_launcher_is_packaged(self):
        self.assertTrue((RUNTIME / "startup-launch.ps1").exists())
        self.assertTrue((RUNTIME / "install-startup.ps1").exists())

    def test_cloud_container_entrypoint_and_blueprint_exist(self):
        self.assertTrue((RUNTIME / "cloud-entrypoint.sh").exists())
        dockerfile = (RUNTIME / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("cloud-entrypoint.sh", dockerfile)
        blueprint = (ROOT / "render.yaml").read_text(encoding="utf-8")
        for marker in ("runtime: docker", "plan: free", "autoDeployTrigger: off",
                       "sync: false", "generateValue: true"):
            self.assertIn(marker, blueprint)

if __name__ == "__main__":
    unittest.main()
