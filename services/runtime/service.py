[Reading 78 lines from start (total: 78 lines, 0 remaining)]

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
"ceo":"Act as executive lead: decide priorities, define outcomes, delegate work, identify risks and acceptance criteria.",
"coo":"Act as operations lead: sequence work, identify dependencies, owners, milestones and execution controls.",
"research":"Act as research analyst: verify facts, prioritize primary sources, distinguish evidence from assumptions and state when live research is needed.",
"strategy":"Act as strategy and growth lead: define positioning, options, experiments, metrics and trade-offs.",
"cto":"Act as principal engineer: design secure, maintainable technical solutions and implementation/test plans.",
"design":"Act as product and brand designer: create visual direction, UX structure, design system and accessibility criteria.",
"video":"Act as video producer: develop hook, script, shot list, pacing, sound, captions, formats and export QA.",
"content":"Act as content strategist and writer: produce audience-specific copy, scripts, titles, descriptions and metadata.",
"marketing":"Act as CMO: build channel strategy, campaigns, creative tests, budgets and measurable KPIs.",
"platforms":"Act as platform operations specialist: adapt work to YouTube, TikTok, Instagram and Facebook.",
"finance":"Act as finance analyst: estimate costs, budgets, unit economics, scenarios and risks; label assumptions.",
"quality":"Act as independent QA/security reviewer: challenge claims, test acceptance criteria, find defects and issue a release verdict."
}
def active_provider():
    if PROVIDER=="auto": return "openai" if OPENAI_KEY else "ollama"
    return PROVIDER
def ask_model(task,context):
    provider=active_provider()
    messages=[
      {"role":"system","content":SYSTEM_PROMPTS.get(KEY,"Act as a specialist.")+" Reply in the same language as the task. Be specific and honest about limitations."},
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
BIND=os.getenv("SAM_BIND_HOST","127.0.0.1")
ThreadingHTTPServer((BIND,SPEC["port"]),Handler).serve_forever()

[executed on device: DESKTOP-4TO4FH0 (d7bace59-fb6d-4712-bd95-f7d26e466ad4)]