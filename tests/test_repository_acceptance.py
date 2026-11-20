import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "ceo", "coo", "research", "strategy", "cto", "design",
    "video", "content", "marketing", "platforms", "finance", "quality",
}

class RepositoryAcceptanceTests(unittest.TestCase):
    def test_role_catalog_has_twelve_unique_roles(self):
        path = ROOT / "services" / "runtime" / "services.json"
        self.assertTrue(path.exists(), "services/runtime/services.json is missing")
        data = json.loads(path.read_text(encoding="utf-8"))
        entries = data.get("services", data)
        if isinstance(entries, dict):
            keys = set(entries)
            values = list(entries.values())
        else:
            values = entries
            keys = {item.get("id") or item.get("name") for item in values}
        self.assertEqual(keys, EXPECTED)
        self.assertEqual(len(values), 12)

    def test_role_prompts_are_not_empty(self):
        path = ROOT / "services" / "runtime" / "services.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        entries = data.get("services", data)
        values = entries.values() if isinstance(entries, dict) else entries
        for item in values:
            prompt = item.get("system_prompt") or item.get("prompt") or item.get("description")
            self.assertTrue(prompt and str(prompt).strip(), f"empty role prompt: {item}")

    def test_runtime_contains_coordinator_and_worker(self):
        self.assertTrue((ROOT / "services/runtime/coordinator.py").exists())
        self.assertTrue((ROOT / "services/runtime/service.py").exists())

    def test_deployment_compose_declares_services(self):
        compose = ROOT / "services/runtime/docker-compose.yml"
        self.assertTrue(compose.exists())
        content = compose.read_text(encoding="utf-8")
        for role in sorted(EXPECTED):
            self.assertIn(role, content, f"compose missing {role}")

    def test_example_config_has_no_real_secrets(self):
        candidates = [
            ROOT / "services/runtime/.env.example",
            ROOT / "services/runtime/.env.sample",
        ]
        existing = [p for p in candidates if p.exists()]
        self.assertTrue(existing, "example environment file missing")
        forbidden = ("sk-proj-", "ghp_", "github_pat_", "-----BEGIN PRIVATE KEY-----")
        for path in existing:
            text = path.read_text(encoding="utf-8")
            for marker in forbidden:
                self.assertNotIn(marker, text)

if __name__ == "__main__":
    unittest.main()
