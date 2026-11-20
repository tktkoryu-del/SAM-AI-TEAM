[Reading 59 lines from start (total: 59 lines, 0 remaining)]

import json, os, threading, urllib.request, urllib.error, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime, timezone
ROOT=os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(ROOT,"services.json"),encoding="utf-8") as f: SERVICES=json.load(f)
BIND=os.getenv("SAM_BIND_HOST","127.0.0.1"); PORT=int(os.getenv("SAM_COORDINATOR_PORT","8787"))
TOKEN=os.getenv("SAM_API_TOKEN","").strip(); DOCKER=os.getenv("SAM_DOCKER_NETWORK","0")=="1"
if BIND not in ("127.0.0.1","localhost","::1") and not TOKEN:raise SystemExit("Refusing non-local bind without SAM_API_TOKEN")
LOCK=threading.Lock(); TASKS={}
def service_host(s):return (s.get("host") or s["key"]) if DOCKER else "127.0.0.1"
def get_json(url):
  with urllib.request.urlopen(url,timeout=5) as r:return json.loads(r.read())
def post(url,payload):
  req=urllib.request.Request(url,data=json.dumps(payload,ensure_ascii=False).encode("utf-8"),headers={"Content-Type":"application/json"},method="POST")
  with urllib.request.urlopen(req,timeout=190) as r:return json.loads(r.read())
def health(s):
  try:return get_json(f"http://{service_host(s)}:{s['port']}/health")
  except Exception as e:return {"ok":False,"service":s["key"],"status":"offline","error":str(e)}
class Handler(BaseHTTPRequestHandler):
  def send_json(self,code,data):
    raw=json.dumps(data,ensure_ascii=False).encode("utf-8");self.send_response(code);self.send_header("Content-Type","application/json; charset=utf-8");self.send_header("Content-Length",str(len(raw)));self.end_headers();self.wfile.write(raw)
  def authorized(self):return not TOKEN or self.headers.get("Authorization","")==("Bearer "+TOKEN)
  def do_GET(self):
    if self.path=="/health":
      states=[health(s) for s in SERVICES]
      return self.send_json(200,{"ok":True,"coordinator":"online","online":sum(x.get("ok",False) for x in states),"total":len(states),"ai_ready":sum(x.get("provider_configured",False) for x in states),"services":states})
    if not self.authorized():return self.send_json(401,{"error":"unauthorized"})
    if self.path=="/services":return self.send_json(200,{"services":SERVICES})
    if self.path.startswith("/tasks/"):
      tid=self.path.split("/")[-1]
      with LOCK:item=TASKS.get(tid)
      return self.send_json(200 if item else 404,item or {"error":"task_not_found"})
    return self.send_json(404,{"error":"not_found"})
  def do_POST(self):
    if not self.authorized():return self.send_json(401,{"error":"unauthorized"})
    if self.path!="/tasks":return self.send_json(404,{"error":"not_found"})
    try:
      n=int(self.headers.get("Content-Length","0"))
      if n>1024*1024:return self.send_json(413,{"error":"payload_too_large"})
      data=json.loads(self.rfile.read(n) or b"{}")
    except Exception:return self.send_json(400,{"error":"invalid_json"})
    task=str(data.get("task","")).strip()
    if not task:return self.send_json(400,{"error":"task_required"})
    requested=data.get("services") or [s["key"] for s in SERVICES];chosen=[s for s in SERVICES if s["key"] in requested]
    if not chosen:return self.send_json(400,{"error":"no_valid_services"})
    tid=str(uuid.uuid4());results=[]
    for s in chosen:
      try:results.append(post(f"http://{service_host(s)}:{s['port']}/run",{"task":task,"context":data.get("context","")}))
      except urllib.error.HTTPError as e:
        detail=e.read().decode("utf-8","replace")[:1500]
        try:results.append(json.loads(detail))
        except Exception:results.append({"ok":False,"service":s["key"],"error":detail,"http_status":e.code})
      except Exception as e:results.append({"ok":False,"service":s["key"],"error":str(e)})
    good=sum(x.get("ok",False) for x in results)
    item={"id":tid,"task":task,"status":"completed" if good==len(results) else ("partial" if good else "blocked"),"successful":good,"requested":len(results),"results":results,"created_at":datetime.now(timezone.utc).isoformat(),"approval_required_for":["publish","send","purchase","payment","delete","account_permission_change"]}
    with LOCK:TASKS[tid]=item
    return self.send_json(201,item)
  def log_message(self,*a):pass
ThreadingHTTPServer((BIND,PORT),Handler).serve_forever()

[executed on device: DESKTOP-4TO4FH0 (d7bace59-fb6d-4712-bd95-f7d26e466ad4)]