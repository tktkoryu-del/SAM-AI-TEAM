import json, os, sys, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime, timezone
ROOT=os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(ROOT,"services.json"),encoding="utf-8") as f: CONFIG=json.load(f)
KEY=sys.argv[1] if len(sys.argv)>1 else "research"
SPEC=next((x for x in CONFIG if x["key"]==KEY),None)
if SPEC is None: raise SystemExit("Unknown service key")
ROLE=SPEC["name"]
PROVIDER=os.getenv("SAM_LLM_PROVIDER","auto").lower()
OPENAI_KEY=os.getenv("OPENAI_API_KEY","").strip()
OLLAMA_URL=os.getenv("OLLAMA_BASE_URL","http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL=os.getenv("SAM_OLLAMA_MODEL","qwen2.5:3b")
OPENAI_MODEL=os.getenv("SAM_OPENAI_MODEL","gpt-4.1-mini")
SYSTEM_PROMPTS={
"ceo":"You are CEO. Produce a decision brief with: one prioritized outcome, a measurable success metric, the owner, the key trade-off, and a go/no-go decision. Never return a generic checklist.",
"coo":"You are COO. Produce an executable work order with numbered steps, named role owners, concrete inputs/outputs, and a completion condition. Do not merely describe process categories.",
"research":"You are Research & Intelligence. Produce an evidence table with claim, source or evidence supplied, confidence, and unknowns. Never invent citations or pretend to browse; if no sources are available, state that and produce a precise research question/evidence checklist.",
"strategy":"You are Strategy & Growth. Produce one specific positioning statement, target audience, differentiator, one testable growth experiment, KPI, and decision threshold. Avoid hypothetical filler.",
"cto":"You are CTO. Produce working code or a concrete technical specification with file paths, interfaces, edge cases, and a runnable validation command. Never claim code was executed unless you executed it.",
"design":"You are Design Lead. Produce a concrete design spec: layout hierarchy, exact copy, component states, spacing/color tokens, responsive behavior, and accessibility checks. Avoid vague mood-board language.",
"video":"You are Video Producer. Produce a ready-to-edit timeline with timestamps, shot/action, spoken line, on-screen text, sound cue, and export settings. Include exact duration and aspect ratio.",
"content":"You are Content Lead. Write the finished publish-ready Arabic copy/script itself, not advice about writing it. Include hook, body, CTA, title, description, and hashtags when relevant.",
"marketing":"You are CMO. Produce one campaign unit: audience, offer/angle, finished ad copy, channel, budget assumption, KPI, and stop/scale threshold. Label estimates.",
"platforms":"You are Platform Operations Lead. Produce platform-specific ready-to-use metadata and publishing checklist for YouTube, TikTok, Instagram, and Facebook; distinguish platform constraints and never claim publication.",
"finance":"You are Finance Lead. Produce a numeric budget with line items, totals, assumptions, currency, best/base/worst case where useful, and a clear financial recommendation. Never invent supplier quotes.",
"quality":"You are the final independent QA/Security gate. The context may contain JSON outputs from every other specialist. Audit those actual outputs one by one against the original task. Report missing roles, generic plans, promises instead of artifacts, fabricated external execution, unsupported facts, and concrete defects with severity and evidence. Do not issue a generic checklist. End with exactly one final machine-readable line: VERDICT: PASS or VERDICT: FAIL. PASS only when every requested role delivered a concrete, relevant, usable artifact and no unsupported execution claim exists."
}
def active_provider():
    if PROVIDER=="auto": return "openai" if OPENAI_KEY else "ollama"
    return PROVIDER
def ask_model(task,context):
    provider=active_provider()
    messages=[
      {"role":"system","content":SYSTEM_PROMPTS.get(KEY,"Act as a specialist.")+" Reply in the same language as the task. Be specific and honest about limitations. The DELIVERABLE must contain the actual artifact itself, not a promise, plan to create it, or description of what you would do. Do not use phrases such as 'I would create', 'will be conducted', or 'the next step is' as substitutes for the artifact. If inputs are missing, state assumptions and still provide the most useful bounded artifact possible. Keep the response concise and concrete."},
      {"role":"user","content":"TASK:\n"+task+"\n\nCONTEXT:\n"+str(context)}
    ]
    try:
      if provider=="ollama":
        payload={"model":OLLAMA_MODEL,"messages":messages,"stream":False,"keep_alive":"10m"}
        req=urllib.request.Request(OLLAMA_URL+"/api/chat",data=json.dumps(payload,ensure_ascii=False).encode("utf-8"),headers={"Content-Type":"application/json"},method="POST")
        with urllib.request.urlopen(req,timeout=180) as resp: result=json.loads(resp.read())
        answer=result.get("message",{}).get("content","")
        model=OLLAMA_MODEL
      elif provider=="openai":
        if not OPENAI_KEY: return {"ok":False,"service":KEY,"status":"provider_not_configured","error":"OPENAI_API_KEY is missing"}
        payload={"model":OPENAI_MODEL,"temperature":0.2,"messages":messages}
        req=urllib.request.Request("https://api.openai.com/v1/chat/completions",data=json.dumps(payload,ensure_ascii=False).encode("utf-8"),headers={"Authorization":"Bearer "+OPENAI_KEY,"Content-Type":"application/json"},method="POST")
        with urllib.request.urlopen(req,timeout=120) as resp: result=json.loads(resp.read())
        answer=result["choices"][0]["message"]["content"]; model=OPENAI_MODEL
      else:return {"ok":False,"service":KEY,"status":"provider_not_supported","error":provider}
      if not answer:return {"ok":False,"service":KEY,"status":"empty_model_response","model":model}
      return {"ok":True,"service":KEY,"role":ROLE,"provider":provider,"model":model,"status":"completed","output":answer,"timestamp":datetime.now(timezone.utc).isoformat()}
    except urllib.error.HTTPError as e:
      detail=e.read().decode("utf-8","replace")[:2000]
      return {"ok":False,"service":KEY,"status":"provider_error","http_status":e.code,"error":detail}
    except Exception as e:return {"ok":False,"service":KEY,"status":"provider_error","error":str(e)}
class Handler(BaseHTTPRequestHandler):
    def send_json(self,code,data):
      raw=json.dumps(data,ensure_ascii=False).encode("utf-8")
      self.send_response(code);self.send_header("Content-Type","application/json; charset=utf-8");self.send_header("Content-Length",str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
      if self.path!="/health":return self.send_json(404,{"error":"not_found"})
      self.send_json(200,{"ok":True,"service":KEY,"role":ROLE,"status":"online","provider":active_provider(),"model":OLLAMA_MODEL if active_provider()=="ollama" else OPENAI_MODEL,"provider_configured":bool(active_provider()=="ollama" or OPENAI_KEY)})
    def do_POST(self):
      if self.path!="/run":return self.send_json(404,{"error":"not_found"})
      try:
        n=int(self.headers.get("Content-Length","0"))
        if n>1024*1024:return self.send_json(413,{"error":"payload_too_large"})
        data=json.loads(self.rfile.read(n) or b"{}")
      except Exception:return self.send_json(400,{"error":"invalid_json"})
      task=str(data.get("task","")).strip()
      if not task:return self.send_json(400,{"error":"task_required"})
      result=ask_model(task,data.get("context",""))
      return self.send_json(200 if result.get("ok") else 503,result)
    def log_message(self,*a):pass
BIND=os.getenv("SAM_WORKER_BIND_HOST",os.getenv("SAM_BIND_HOST","127.0.0.1"))
ThreadingHTTPServer((BIND,SPEC["port"]),Handler).serve_forever()