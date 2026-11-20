import ast
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "services" / "runtime"
sys.path.insert(0, str(RUNTIME))
from acceptance import validate_role_outputs

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

    def test_runtime_contains_coordinator_worker_and_acceptance_module(self):
        self.assertTrue((RUNTIME / "coordinator.py").exists())
        self.assertTrue((RUNTIME / "service.py").exists())
        self.assertTrue((RUNTIME / "acceptance.py").exists())

    def test_worker_health_checks_real_model_readiness(self):
        source = (RUNTIME / "service.py").read_text(encoding="utf-8")
        self.assertIn("def provider_health():", source)
        self.assertIn("/api/tags", source)
        self.assertIn("/v1/models", source)
        self.assertIn('"provider_ready": ready', source)
        self.assertIn('"reachable": True', source)

    def test_coordinator_health_requires_all_models_ready(self):
        source = (RUNTIME / "coordinator.py").read_text(encoding="utf-8")
        self.assertIn('ai_ready = sum(bool(state.get("provider_ready")) for state in states)', source)
        self.assertIn('"ok": online == len(SERVICES) and ai_ready == len(SERVICES)', source)

    def test_task_id_validation_rejects_path_traversal(self):
        source = (RUNTIME / "coordinator.py").read_text(encoding="utf-8")
        self.assertIn("def valid_task_id(value):", source)
        self.assertIn('"invalid_task_id"', source)
        self.assertIn('"task_is_running"', source)
        self.assertIn('if "/" in task_id or not valid_task_id(task_id):', source)

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

    def test_coordinator_has_durable_queue_retries_and_recovery(self):
        source = (RUNTIME / "coordinator.py").read_text(encoding="utf-8")
        for marker in (
            "journal_mode=WAL",
            "WORKER_RETRIES",
            "WORKER_TIMEOUT",
            "recover_interrupted_tasks",
            "SAM_WORKER_TOKEN",
            "/evidence",
            "sha256",
            "ffprobe",
        ):
            self.assertIn(marker, source)

    def test_unverified_media_filename_and_missing_file_are_rejected(self):
        output = (
            "DELIVERABLE:\nA usable production export is ready: SAM_short.mp4\n"
            "The video is vertical and runs for 15 seconds. This line is intentionally "
            "long enough to exceed the minimum output threshold used by the acceptance gate.\n"
            "VALIDATION: checked the storyboard and timeline.\n"
        )
        violations = validate_role_outputs(
            [{"service": "video", "ok": True, "output": output}],
            ["video", "quality"],
            "Rendered MP4 video file, 15 seconds, vertical 9:16",
            [],
        )
        self.assertTrue(any("Required media files not evidenced" in item for item in violations))
        self.assertTrue(any("Unverified media filenames" in item for item in violations))

    def test_verified_vertical_video_with_matching_sha_passes_media_checks(self):
        output = (
            "DELIVERABLE:\nThe exported file SAM_short.mp4 is ready for review. "
            "This role output is deliberately more than eighty characters and includes "
            "the actual media deliverable reference.\n"
            "VALIDATION: media metadata and hash are attached to the task evidence.\n"
        )
        evidence = [{
            "verified": True,
            "sha256": "a" * 64,
            "size_bytes": 2400000,
            "type": "video",
            "path": "SAM_short.mp4",
            "media_probe": {
                "stream_type": "video",
                "width": 1080,
                "height": 1920,
                "duration_seconds": 15.0,
            },
        }]
        violations = validate_role_outputs(
            [{"service": "video", "ok": True, "output": output}],
            ["video", "quality"],
            "Rendered MP4 video file, 15 seconds, vertical 9:16",
            evidence,
        )
        self.assertEqual(violations, [])

    def test_horizontal_video_fails_vertical_task(self):
        evidence = [{
            "verified": True,
            "sha256": "b" * 64,
            "size_bytes": 1000000,
            "type": "video",
            "path": "wide.mp4",
            "media_probe": {
                "stream_type": "video",
                "width": 1920,
                "height": 1080,
                "duration_seconds": 15.0,
            },
        }]
        violations = validate_role_outputs(
            [{"service": "video", "ok": True, "output": "DELIVERABLE:\n" + ("usable timeline " * 12)}],
            ["video", "quality"],
            "Actual rendered MP4 video file, 15 seconds, vertical 9:16",
            evidence,
        )
        self.assertTrue(any("not portrait/vertical" in item for item in violations))


if __name__ == "__main__":
    unittest.main()
