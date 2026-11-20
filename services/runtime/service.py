import json
import os
import sys
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(ROOT, "services.json"), encoding="utf-8") as stream:
    CONFIG = json.load(stream)
KEY = sys.argv[1] if len(sys.argv) > 1 else "research"
SPEC = next((item for item in CONFIG if item["key"] == KEY), None)
if SPEC is None:
    raise SystemExit("Unknown service key")

ROLE = SPEC["name"]
PROVIDER = os.getenv("SAM_LLM_PROVIDER", "auto").lower()
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("SAM_OLLAMA_MODEL", "qwen2.5:3b")
OPENAI_MODEL = os.getenv("SAM_OPENAI_MODEL", "gpt-4.1-mini")
OLLAMA_TIMEOUT = max(30, min(int(os.getenv("SAM_OLLAMA_TIMEOUT", "180")), 240))
WORKER_TOKEN = os.getenv("SAM_WORKER_TOKEN", "").strip()
BIND = os.getenv("SAM_WORKER_BIND_HOST", os.getenv("SAM_BIND_HOST", "127.0.0.1"))
MAX_BODY_BYTES = 1024 * 1024

if BIND not in ("127.0.0.1", "localhost", "::1") and not WORKER_TOKEN:
    raise SystemExit("Refusing non-local worker bind without SAM_WORKER_TOKEN")

SYSTEM_PROMPTS = {
    "ceo": "You are CEO. Produce a decision brief with one prioritized outcome, measurable success metric, accountable owner, key trade-off, and go/no-go decision. Never return a generic checklist.",
    "coo": "You are COO. Produce an executable work order with numbered steps, named role owners, concrete inputs/outputs, and a completion condition. Do not merely describe process categories.",
    "research": "You are Research & Intelligence. Produce an evidence table with claim, source or supplied evidence, confidence, and unknowns. Never invent citations or pretend to browse; if no sources are available, state that and produce a precise research question/evidence checklist.",
    "strategy": "You are Strategy & Growth. Produce a specific positioning statement, target audience, differentiator, testable growth experiment, KPI, and decision threshold. Avoid hypothetical filler.",
    "cto": "You are CTO. Produce working code or a concrete technical specification with file paths, interfaces, edge cases, and a runnable validation command. Never claim code was executed unless it was.",
    "design": "You are Design Lead. Produce a concrete design spec: layout hierarchy, exact copy, component states, spacing/color tokens, responsive behavior, and accessibility checks. Avoid vague mood-board language.",
    "video": "You are Video Producer. Produce the actual video only when a rendering tool is provided and used. Otherwise return an editable timeline with timestamps, shot/action, spoken line, on-screen text, sound cue, and export settings, and explicitly say NOT_PRODUCED for the media file. Never invent an MP4 filename or claim a render exists.",
    "content": "You are Content Lead. Write the finished publish-ready Arabic copy/script itself, not advice about writing it. Include hook, body, CTA, title, description, and hashtags when relevant.",
    "marketing": "You are CMO. Produce one campaign unit: audience, offer/angle, finished ad copy, channel, budget assumption, KPI, and stop/scale threshold. Label estimates.",
    "platforms": "You are Platform Operations Lead. Produce platform-specific ready-to-use metadata and publishing checklist for YouTube, TikTok, Instagram, and Facebook; distinguish platform constraints and never claim publication.",
    "finance": "You are Finance Lead. Produce a numeric budget with line items, totals, assumptions, currency, scenario analysis where useful, and a clear financial recommendation. Never invent supplier quotes.",
    "quality": "You are the final independent QA/Security gate. Audit the actual outputs of all other roles one by one against the original task. Report missing roles, generic plans, promises instead of artifacts, fabricated external execution, unsupported facts, and concrete defects with severity and evidence. Do not issue a generic checklist. End with exactly one final machine-readable line: VERDICT: PASS or VERDICT: FAIL. PASS only when every requested role delivered a concrete, relevant, usable artifact and all required media evidence is verified."
}


def active_provider():
    if PROVIDER == "auto":
        return "openai" if OPENAI_KEY else "ollama"
    return PROVIDER


def provider_health():
    """Read-only readiness check; never performs a billable model generation."""
    provider = active_provider()
    try:
        if provider == "ollama":
            request = urllib.request.Request(OLLAMA_URL + "/api/tags", method="GET")
            with urllib.request.urlopen(request, timeout=4) as response:
                payload = json.loads(response.read() or b"{}")
            models = payload.get("models", [])
            available = any(
                item.get("name") == OLLAMA_MODEL or item.get("model") == OLLAMA_MODEL
                for item in models
            )
            return {
                "provider_ready": bool(available),
                "provider_error": None if available else "configured Ollama model is not installed",
            }
        if provider == "openai":
            if not OPENAI_KEY:
                return {"provider_ready": False, "provider_error": "OPENAI_API_KEY is missing"}
            request = urllib.request.Request(
                "https://api.openai.com/v1/models",
                headers={"Authorization": "Bearer " + OPENAI_KEY},
                method="GET",
            )
            with urllib.request.urlopen(request, timeout=6) as response:
                payload = json.loads(response.read() or b"{}")
            available = any(item.get("id") == OPENAI_MODEL for item in payload.get("data", []))
            return {
                "provider_ready": bool(available),
                "provider_error": None if available else "configured OpenAI model is not available to this key",
            }
        return {"provider_ready": False, "provider_error": "unsupported provider: " + provider}
    except Exception as error:
        return {"provider_ready": False, "provider_error": str(error)[:500]}


def ask_model(task, context):
    provider = active_provider()
    system_text = (
        SYSTEM_PROMPTS.get(KEY, "Act as a specialist.")
        + " Reply in the same language as the task. Be specific and honest about limitations. "
        + "The DELIVERABLE section must contain the actual artifact itself, not a promise, "
        + "plan to create it, or description of what you would do. Do not invent filenames, "
        + "rendered media, source citations, test results, or external actions. A storyboard "
        + "is not a video file; a design spec is not a rendered image. Clearly separate "
        + "verified facts, assumptions, and limitations. If inputs are missing, state "
        + "assumptions and still provide the most useful bounded artifact."
    )
    messages = [
        {"role": "system", "content": system_text},
        {
            "role": "user",
            "content": "TASK:\n" + task + "\n\nCONTEXT:\n" + str(context),
        },
    ]
    try:
        if provider == "ollama":
            payload = {
                "model": OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
                "keep_alive": "10m",
                "options": {
                    "temperature": 0.15,
                    "top_p": 0.9,
                    "num_ctx": 4096,
                    "num_predict": 1400,
                },
            }
            request = urllib.request.Request(
                OLLAMA_URL + "/api/chat",
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=OLLAMA_TIMEOUT) as response:
                result = json.loads(response.read())
            answer = result.get("message", {}).get("content", "")
            model = OLLAMA_MODEL
        elif provider == "openai":
            if not OPENAI_KEY:
                return {
                    "ok": False,
                    "service": KEY,
                    "status": "provider_not_configured",
                    "error": "OPENAI_API_KEY is missing",
                }
            payload = {
                "model": OPENAI_MODEL,
                "temperature": 0.2,
                "messages": messages,
            }
            request = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={
                    "Authorization": "Bearer " + OPENAI_KEY,
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=120) as response:
                result = json.loads(response.read())
            answer = result["choices"][0]["message"]["content"]
            model = OPENAI_MODEL
        else:
            return {
                "ok": False,
                "service": KEY,
                "status": "provider_not_supported",
                "error": provider,
            }
        if not answer:
            return {
                "ok": False,
                "service": KEY,
                "status": "empty_model_response",
                "model": model,
            }
        return {
            "ok": True,
            "service": KEY,
            "role": ROLE,
            "provider": provider,
            "model": model,
            "status": "completed",
            "output": answer,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:2000]
        return {
            "ok": False,
            "service": KEY,
            "status": "provider_error",
            "http_status": error.code,
            "error": detail,
        }
    except Exception as error:
        return {
            "ok": False,
            "service": KEY,
            "status": "provider_error",
            "error": str(error),
        }


class Handler(BaseHTTPRequestHandler):
    def send_json(self, code, data):
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def authorized(self):
        return not WORKER_TOKEN or self.headers.get("Authorization", "") == (
            "Bearer " + WORKER_TOKEN
        )

    def do_GET(self):
        if self.path != "/health":
            return self.send_json(404, {"error": "not_found"})
        provider = active_provider()
        readiness = provider_health()
        ready = bool(readiness.get("provider_ready"))
        self.send_json(
            200,
            {
                "ok": ready,
                "reachable": True,
                "service": KEY,
                "role": ROLE,
                "status": "ready" if ready else "degraded",
                "provider": provider,
                "model": OLLAMA_MODEL if provider == "ollama" else OPENAI_MODEL,
                "provider_configured": bool(provider == "ollama" or OPENAI_KEY),
                "provider_ready": ready,
                "provider_error": readiness.get("provider_error"),
                "token_auth_enabled": bool(WORKER_TOKEN),
            },
        )

    def do_POST(self):
        if not self.authorized():
            return self.send_json(401, {"error": "unauthorized"})
        if self.path != "/run":
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
        result = ask_model(task, data.get("context", ""))
        return self.send_json(200 if result.get("ok") else 503, result)

    def log_message(self, *_args):
        return


if __name__ == "__main__":
    ThreadingHTTPServer((BIND, SPEC["port"]), Handler).serve_forever()
