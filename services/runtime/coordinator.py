import json
import os
import random
import re
import sqlite3
import threading
import time
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.join(ROOT, "tasks")
DB_PATH = os.getenv("SAM_TASK_DB", os.path.join(ROOT, "sam_tasks.sqlite3"))
os.makedirs(TASK_DIR, exist_ok=True)
with open(os.path.join(ROOT, "services.json"), encoding="utf-8") as stream:
    SERVICES = json.load(stream)
SERVICE_MAP = {item["key"]: item for item in SERVICES}

BIND = os.getenv("SAM_BIND_HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", os.getenv("SAM_COORDINATOR_PORT", "8787")))
API_TOKEN = os.getenv("SAM_API_TOKEN", "").strip()
WORKER_TOKEN = os.getenv("SAM_WORKER_TOKEN", "").strip()
DOCKER_NETWORK = os.getenv("SAM_DOCKER_NETWORK", "0") == "1"
MAX_PARALLEL = max(1, min(int(os.getenv("SAM_MAX_PARALLEL", "3")), 6))
WORKER_TIMEOUT = max(30, min(int(os.getenv("SAM_WORKER_TIMEOUT", "150")), 240))
WORKER_RETRIES = max(0, min(int(os.getenv("SAM_WORKER_RETRIES", "2")), 4))
MAX_BODY_BYTES = 1024 * 1024

if BIND not in ("127.0.0.1", "localhost", "::1") and not API_TOKEN:
    raise SystemExit("Refusing non-local bind without SAM_API_TOKEN")

POOL = ThreadPoolExecutor(max_workers=MAX_PARALLEL, thread_name_prefix="sam-worker")
DB_LOCK = threading.RLock()
ACTIVE_LOCK = threading.RLock()
ACTIVE_TASKS = set()


def now():
    return datetime.now(timezone.utc).isoformat()


def connect_db():
    connection = sqlite3.connect(DB_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with connect_db() as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute(
            """CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )"""
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_tasks_status_created "
            "ON tasks(status, created_at)"
        )


def task_file(task_id):
    return os.path.join(TASK_DIR, task_id + ".json")


def save_task(item):
    item["updated_at"] = now()
    serialized = json.dumps(item, ensure_ascii=False)
    with DB_LOCK, connect_db() as connection:
        connection.execute(
            """INSERT INTO tasks(id,payload,status,created_at,updated_at)
               VALUES(?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET
                 payload=excluded.payload,
                 status=excluded.status,
                 updated_at=excluded.updated_at""",
            (
                item["id"],
                serialized,
                item["status"],
                item.get("created_at", now()),
                item["updated_at"],
            ),
        )
    target = task_file(item["id"])
    temporary = target + ".tmp"
    with open(temporary, "w", encoding="utf-8") as stream:
        stream.write(serialized)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, target)


def load_task(task_id):
    with connect_db() as connection:
        row = connection.execute(
            "SELECT payload FROM tasks WHERE id=?", (task_id,)
        ).fetchone()
    if row:
        return json.loads(row["payload"])
    path = task_file(task_id)
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as stream:
            return json.load(stream)
    return None


def service_host(service):
    if DOCKER_NETWORK:
        return service.get("host") or service["key"]
    return "127.0.0.1"


def get_json(url, timeout=4):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read())


def post_json(url, payload, timeout):
    headers = {"Content-Type": "application/json"}
    if WORKER_TOKEN:
        headers["Authorization"] = "Bearer " + WORKER_TOKEN
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


def worker_health(service):
    try:
        return get_json(
            "http://{}:{}/health".format(service_host(service), service["port"])
        )
    except Exception as error:
        return {
            "ok": False,
            "service": service["key"],
            "status": "offline",
            "error": str(error),
        }


def run_one(service, task, context):
    guardrails = (
        "\n\nOUTPUT AND EVIDENCE RULES:\n"
        "- Return the actual role-specific written artifact, not a plan or promise.\n"
        "- Never invent a filename, generated image/video/audio, export, test run, or external change.\n"
        "- A script, storyboard, design specification, or caption is not a rendered media file.\n"
        "- If asked for media bytes that this worker cannot render, state NOT_PRODUCED and provide the best usable script/spec.\n"
        "- Clearly separate verified facts, assumptions, and limitations.\n"
        "- Use the headings DELIVERABLE, VALIDATION, LIMITATIONS, NEXT_DEPENDENCY.\n"
    )
    last_error = None
    endpoint = "http://{}:{}/run".format(service_host(service), service["port"])
    for attempt in range(WORKER_RETRIES + 1):
        try:
            result = post_json(
                endpoint,
                {"task": task + guardrails, "context": context},
                WORKER_TIMEOUT,
            )
            result["requested_role"] = service["key"]
            result["attempts"] = attempt + 1
            if result.get("ok") and str(result.get("output", "")).strip():
                return result
            last_error = {
                "ok": False,
                "service": service["key"],
                "status": result.get("status", "invalid_worker_response"),
                "error": result.get("error", "empty or unsuccessful worker response"),
                "attempts": attempt + 1,
            }
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", "replace")[:1200]
            last_error = {
                "ok": False,
                "service": service["key"],
                "status": "http_error",
                "http_status": error.code,
                "error": detail,
                "attempts": attempt + 1,
            }
            if error.code not in (408, 425, 429, 500, 502, 503, 504):
                break
        except Exception as error:
            last_error = {
                "ok": False,
                "service": service["key"],
                "status": "timeout_or_transport_error",
                "error": str(error),
                "attempts": attempt + 1,
            }
        if attempt < WORKER_RETRIES:
            time.sleep(min((2 ** attempt) + random.random(), 6))
    return last_error or {
        "ok": False,
        "service": service["key"],
        "status": "failed",
        "error": "worker returned no result",
    }


def looks_like_unverified_media_claim(output):
    extensions = r"\.(?:mp4|mov|webm|png|jpe?g|wav|mp3|m4a)\b"
    if not re.search(extensions, output, flags=re.IGNORECASE):
        return False
    evidence_markers = (
        "evidence_path",
        "verified_file",
        "artifact_sha256",
        "file_exists=true",
    )
    return not any(marker in output.lower() for marker in evidence_markers)


def deterministic_quality(results, requested_roles, task_text):
    missing = []
    unverified_media = []
    thin_outputs = []
    media_requested = bool(
        re.search(r"\b(video|image|photo|audio|mp4|png|wav|صورة|فيديو|صوت)\b",
                  task_text, flags=re.IGNORECASE)
    )
    for role in requested_roles:
        if role == "quality":
            continue
        result = next(
            (
                entry
                for entry in results
                if entry.get("service") == role
                and entry.get("ok")
                and str(entry.get("output", "")).strip()
            ),
            None,
        )
        if result is None:
            missing.append(role)
            continue
        output = str(result.get("output", ""))
        if len(output.strip()) < 80 or "DELIVERABLE" not in output.upper():
            thin_outputs.append(role)
        if looks_like_unverified_media_claim(output):
            unverified_media.append(role)
        if media_requested and role == "video" and re.search(
            r"\bNOT_PRODUCED\b", output, flags=re.IGNORECASE
        ):
            missing.append(role + " (media bytes not produced)")
    if missing or unverified_media or thin_outputs:
        detail = [
            "DELIVERABLE:",
            "القبول مرفوض وفق فحوص الأدلة الآلية.",
            "الأدوار المفقودة أو غير المنتجة: " + (", ".join(sorted(set(missing))) or "لا يوجد"),
            "ادعاءات ملفات وسائط دون دليل: " + (", ".join(sorted(set(unverified_media))) or "لا يوجد"),
            "المخرجات القصيرة أو دون قسم DELIVERABLE: " + (", ".join(sorted(set(thin_outputs))) or "لا يوجد"),
            "VALIDATION: تم فحص حالة الدور، طول المخرج، قسم التسليم، وادعاءات امتدادات الوسائط.",
            "LIMITATIONS: الفحص آلي بنيوي ولا يغني عن مراجعة المحتوى أو اختبار ملفات الوسائط.",
            "VERDICT: FAIL",
        ]
        return {
            "ok": True,
            "service": "quality",
            "role": "Deterministic acceptance gate",
            "provider": "local_rules",
            "model": "sam-acceptance-v1",
            "status": "rejected",
            "output": "\n".join(detail),
            "requested_role": "quality",
        }
    return None


def get_completed_role_keys(results):
    completed = set()
    for result in results:
        if result.get("ok") and str(result.get("output", "")).strip():
            key = result.get("service")
            if key:
                completed.add(key)
    return completed


def execute_task(task_id):
    with ACTIVE_LOCK:
        if task_id in ACTIVE_TASKS:
            return
        ACTIVE_TASKS.add(task_id)
    try:
        item = load_task(task_id)
        if not item:
            return
        item["status"] = "running"
        item.setdefault("started_at", now())
        save_task(item)

        requested_roles = item["services"]
        quality_requested = "quality" in requested_roles
        parallel_roles = [key for key in requested_roles if key != "quality"]
        results = list(item.get("results", []))
        already_done = get_completed_role_keys(results)
        todo = [key for key in parallel_roles if key not in already_done]

        futures = {
            POOL.submit(
                run_one,
                SERVICE_MAP[key],
                item["task"],
                item.get("context", ""),
            ): key
            for key in todo
        }
        for future in as_completed(futures):
            role = futures[future]
            try:
                result = future.result()
            except Exception as error:
                result = {
                    "ok": False,
                    "service": role,
                    "status": "coordinator_error",
                    "error": str(error),
                }
            results = [entry for entry in results if entry.get("service") != role]
            results.append(result)
            item["results"] = results[:]
            item["finished_workers"] = len(
                {entry.get("service") for entry in results if entry.get("service")}
            )
            item["successful"] = len(get_completed_role_keys(results))
            save_task(item)

        if quality_requested:
            results = [entry for entry in results if entry.get("service") != "quality"]
            deterministic = deterministic_quality(
                results, requested_roles, item.get("task", "")
            )
            if deterministic:
                qa_result = deterministic
            else:
                compact = [
                    {
                        "service": entry.get("service"),
                        "ok": bool(entry.get("ok") and entry.get("output")),
                        "error": entry.get("error"),
                        "output": str(entry.get("output", ""))[:1800],
                    }
                    for entry in results
                ]
                qa_task = (
                    item["task"]
                    + "\n\nFINAL INDEPENDENT QUALITY REVIEW: Audit each actual role output "
                    "included in context against the original task. Identify specific defects, "
                    "generic plans, missing outputs, unsupported claims, and role mismatch. "
                    "Do not issue a generic checklist. PASS only when every requested role "
                    "produced a concrete, relevant, usable artifact. End with exactly one "
                    "machine-readable final line: VERDICT: PASS or VERDICT: FAIL."
                )
                qa_context = (
                    item.get("context", "")
                    + "\n\nROLE_OUTPUTS_JSON:\n"
                    + json.dumps(compact, ensure_ascii=False)
                )
                qa_result = run_one(SERVICE_MAP["quality"], qa_task, qa_context)
            results.append(qa_result)

        item["results"] = results
        item["requested"] = len(requested_roles)
        item["finished_workers"] = len(
            {entry.get("service") for entry in results if entry.get("service")}
        )
        item["successful"] = len(get_completed_role_keys(results))
        quality_result = next(
            (entry for entry in results if entry.get("service") == "quality"),
            None,
        )
        quality_output = str((quality_result or {}).get("output", ""))
        quality_passed = any(
            line.strip() == "VERDICT: PASS" for line in quality_output.splitlines()
        )
        all_roles_ok = all(
            role in get_completed_role_keys(results) for role in parallel_roles
        )
        item["quality_gate"] = {
            "requested": quality_requested,
            "reviewed": bool(quality_result and quality_output.strip()),
            "passed": quality_passed,
            "reviewer": "quality" if quality_requested else None,
        }
        item["acceptance_pass"] = all_roles_ok and (
            quality_passed if quality_requested else True
        )
        item["status"] = (
            "completed"
            if item["acceptance_pass"]
            else ("rejected" if quality_requested and quality_result else "partial")
        )
        item["completed_at"] = now()
        item["evidence"] = item.get("evidence", [])
        item["evidence_note"] = (
            "Text from a model is not proof of external execution. Media artifacts "
            "must exist, have a verified path and SHA-256, and pass file inspection."
        )
        save_task(item)
    except Exception as error:
        failed = load_task(task_id)
        if failed:
            failed["status"] = "blocked"
            failed["fatal_error"] = str(error)
            failed["completed_at"] = now()
            save_task(failed)
    finally:
        with ACTIVE_LOCK:
            ACTIVE_TASKS.discard(task_id)


def schedule_task(task_id):
    with ACTIVE_LOCK:
        if task_id in ACTIVE_TASKS:
            return False
        ACTIVE_TASKS.add(task_id)
        ACTIVE_TASKS.discard(task_id)
    threading.Thread(
        target=execute_task,
        args=(task_id,),
        name="sam-task-" + task_id[:8],
        daemon=True,
    ).start()
    return True


def recover_interrupted_tasks():
    with connect_db() as connection:
        rows = connection.execute(
            "SELECT id,payload FROM tasks WHERE status IN ('queued','running','partial')"
        ).fetchall()
    recovered = []
    for row in rows:
        item = json.loads(row["payload"])
        item["recovered_after_restart"] = True
        item["status"] = "queued"
        save_task(item)
        schedule_task(item["id"])
        recovered.append(item["id"])
    return recovered


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, data):
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def authorized(self):
        return not API_TOKEN or self.headers.get("Authorization", "") == (
            "Bearer " + API_TOKEN
        )

    def do_GET(self):
        if self.path == "/health":
            states = [worker_health(service) for service in SERVICES]
            with connect_db() as connection:
                counts = {
                    row["status"]: row["count"]
                    for row in connection.execute(
                        "SELECT status,COUNT(*) AS count FROM tasks GROUP BY status"
                    )
                }
            online = sum(bool(state.get("ok")) for state in states)
            return self.send_json(
                200,
                {
                    "ok": online == len(SERVICES),
                    "coordinator": "online",
                    "online": online,
                    "total": len(SERVICES),
                    "ai_ready": sum(
                        bool(state.get("provider_configured")) for state in states
                    ),
                    "max_parallel": MAX_PARALLEL,
                    "worker_retries": WORKER_RETRIES,
                    "worker_timeout_seconds": WORKER_TIMEOUT,
                    "task_storage": "sqlite_wal_plus_json_archive",
                    "task_counts": counts,
                    "services": states,
                },
            )
        if not self.authorized():
            return self.send_json(401, {"error": "unauthorized"})
        if self.path == "/services":
            return self.send_json(200, {"services": SERVICES})
        if self.path.startswith("/tasks/"):
            item = load_task(self.path.rsplit("/", 1)[-1])
            return self.send_json(200 if item else 404, item or {"error": "task_not_found"})
        return self.send_json(404, {"error": "not_found"})

    def do_POST(self):
        if not self.authorized():
            return self.send_json(401, {"error": "unauthorized"})
        if self.path != "/tasks":
            return self.send_json(404, {"error": "not_found"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > MAX_BODY_BYTES:
                return self.send_json(413, {"error": "payload_too_large"})
            data = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            return self.send_json(400, {"error": "invalid_json"})
        task = str(data.get("task", "")).strip()
        if not task:
            return self.send_json(400, {"error": "task_required"})
        requested = data.get("services") or list(SERVICE_MAP)
        if not isinstance(requested, list):
            return self.send_json(400, {"error": "services_must_be_array"})
        chosen = [key for key in dict.fromkeys(requested) if key in SERVICE_MAP]
        if not chosen:
            return self.send_json(400, {"error": "no_valid_services"})
        task_id = str(uuid.uuid4())
        item = {
            "id": task_id,
            "task": task,
            "context": str(data.get("context", "")),
            "services": chosen,
            "status": "queued",
            "successful": 0,
            "requested": len(chosen),
            "finished_workers": 0,
            "results": [],
            "created_at": now(),
            "approval_required_for": [
                "publish",
                "send",
                "purchase",
                "payment",
                "delete",
                "account_permission_change",
            ],
        }
        save_task(item)
        schedule_task(task_id)
        return self.send_json(202, item)

    def log_message(self, *_args):
        return


if __name__ == "__main__":
    init_db()
    recover_interrupted_tasks()
    ThreadingHTTPServer((BIND, PORT), Handler).serve_forever()
