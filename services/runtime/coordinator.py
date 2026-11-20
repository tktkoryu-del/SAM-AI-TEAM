import json, os, threading, urllib.request, urllib.error, uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime, timezone

ROOT=os.path.dirname(os.path.abspath(__file__))
TASK_DIR=os.path.join(ROOT,"tasks")
os.makedirs(TASK_DIR,exist_ok=True)
with open(os.path.join(ROOT,"services.json"),encoding="utf-8") as f: SERVICES=json.load(f)
SERVICE_MAP={s["key"]:s for s in SERVICES}
BIND=os.getenv("SAM_BIND_HOST","127.0.0.1")
PORT=int(os.getenv("PORT",os.getenv("SAM_COORDINATOR_PORT","8787")))
TOKEN=os.getenv("SAM_API_TOKEN","").strip()
DOCKER=os.getenv("SAM_DOCKER_NETWORK","0")=="1"
MAX_PARALLEL=max(1,min(int(os.getenv("SAM_MAX_PARALLEL","3")),6))
if BIND not in ("127.0.0.1","localhost","::1") and not TOKEN:
    raise SystemExit("Refusing non-local bind without SAM_API_TOKEN")
LOCK=threading.Lock()
POOL=ThreadPoolExecutor(max_workers=MAX_PARALLEL)

def now(): return datetime.now(timezone.utc).isoformat()
def task_path(tid): return os.path.join(TASK_DIR,tid+".json")
def save_task(item):
    path=task_path(item["id"]); temp=path+".tmp"
    with open(temp,"w",encoding="utf-8") as f: json.dump(item,f,ensure_ascii=False,indent=2)
    os.replace(temp,path)
def load_task(tid):
    path=task_path(tid)
    if not os.path.isfile(path): return None
    with open(path,encoding="utf-8") as f: return json.load(f)
def service_host(s): return (s.get("host") or s["key"]) if DOCKER else "127.0.0.1"
def get_json(url):
    with urllib.request.urlopen(url,timeout=5) as r: return json.loads(r.read())
def post(url,payload):
    req=urllib.request.Request(url,data=json.dumps(payload,ensure_ascii=False).encode("utf-8"),headers={"Content-Type":"application/json"},method="POST")
    with urllib.request.urlopen(req,timeout=190) as r: return json.loads(r.read())
def health(s):
    try: return get_json(f"http://{service_host(s)}:{s['port']}/health")
    except Exception as e: return {"ok":False,"service":s["key"],"status":"offline","error":str(e)}
def run_one(s,task,context):
    brief=("\n\nDELIVERY STANDARD: Return a concrete work product, not a plan or generic advice. "
           "Use headings: DELIVERABLE, VALIDATION, LIMITATIONS, NEXT_DEPENDENCY. "
           "Do not claim files were created, code was run, websites were changed, or anything was published unless this worker actually did it. "
           "If your role cannot execute an external action, state that clearly and provide the usable output you can produce.")
    try:
        result=post(f"http://{service_host(s)}:{s['port']}/run",{"task":task+brief,"context":context})
        result["requested_role"]=s["key"]
        return result
    except urllib.error.HTTPError as e:
        detail=e.read().decode("utf-8","replace")[:1500]
        try: return json.loads(detail)
        except Exception: return {"ok":False,"service":s["key"],"error":detail,"http_status":e.code}
    except Exception as e: return {"ok":False,"service":s["key"],"error":str(e)}
def execute_task(tid):
    with LOCK: item=load_task(tid)
    if not item: return
    item["status"]="running"; item["started_at"]=now(); save_task(item)
    results=[]
    quality_requested="quality" in item["services"]
    parallel_keys=[k for k in item["services"] if k!="quality"] if quality_requested else item["services"]
    futures={POOL.submit(run_one,SERVICE_MAP[k],item["task"],item.get("context","")):k for k in parallel_keys}
    for future in as_completed(futures):
        key=futures[future]
        try: results.append(future.result())
        except Exception as e: results.append({"ok":False,"service":key,"error":str(e)})
        with LOCK:
            item["results"]=results[:]
            item["successful"]=sum(1 for x in results if x.get("ok") and x.get("output"))
            item["finished_workers"]=len(results)
            item["updated_at"]=now()
            save_task(item)
    if quality_requested:
        compact=[]
        for result in results:
            compact.append({
                "service":result.get("service"),
                "ok":bool(result.get("ok") and result.get("output")),
                "error":result.get("error"),
                "output":str(result.get("output",""))[:1800]
            })
        qa_task=item["task"]+"\n\nFINAL INDEPENDENT QA: Audit the actual outputs from all other roles included in context. Identify missing, generic, fabricated, or unusable deliverables. Do not give a generic checklist. End with exactly one machine-readable final line: VERDICT: PASS or VERDICT: FAIL. PASS is allowed only if every requested role produced a concrete, task-relevant deliverable and no unsupported external-execution claim is present."
        qa_context=item.get("context","")+"\n\nOTHER_ROLE_RESULTS_JSON:\n"+json.dumps(compact,ensure_ascii=False)
        try: qa_result=run_one(SERVICE_MAP["quality"],qa_task,qa_context)
        except Exception as e: qa_result={"ok":False,"service":"quality","error":str(e)}
        results.append(qa_result)
        with LOCK:
            item["results"]=results[:]
            item["successful"]=sum(1 for x in results if x.get("ok") and x.get("output"))
            item["finished_workers"]=len(results)
            item["updated_at"]=now()
            save_task(item)
    good=sum(1 for x in results if x.get("ok") and x.get("output"))
    item["successful"]=good
    item["requested"]=len(item["services"])
    qa=next((x for x in results if x.get("service")=="quality"),None) if quality_requested else None
    qa_output=str((qa or {}).get("output",""))
    qa_passed=any(line.strip()=="VERDICT: PASS" for line in qa_output.splitlines())
    item["quality_gate"]={"requested":quality_requested,"reviewed":bool(qa and qa.get("ok") and qa_output),"passed":qa_passed,"reviewer":"quality"}
    item["acceptance_pass"]=good==len(item["services"]) and (not quality_requested or qa_passed)
    item["status"]="completed" if good==len(item["services"]) else ("partial" if good else "blocked")
    item["completed_at"]=now()
    item["evidence"]=[]
    item["evidence_note"]="Model responses are not proof of external execution. Attach files, test logs, or verified URLs before marking a real-world deliverable complete."
    save_task(item)

class Handler(BaseHTTPRequestHandler):
    def send_json(self,code,data):
        raw=json.dumps(data,ensure_ascii=False).encode("utf-8")
        self.send_response(code); self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def authorized(self): return not TOKEN or self.headers.get("Authorization","")==("Bearer "+TOKEN)
    def do_GET(self):
        if self.path=="/health":
            states=[health(s) for s in SERVICES]
            return self.send_json(200,{"ok":True,"coordinator":"online","online":sum(x.get("ok",False) for x in states),"total":len(states),"ai_ready":sum(x.get("provider_configured",False) for x in states),"max_parallel":MAX_PARALLEL,"task_storage":"disk","services":states})
        if not self.authorized(): return self.send_json(401,{"error":"unauthorized"})
        if self.path=="/services": return self.send_json(200,{"services":SERVICES})
        if self.path.startswith("/tasks/"):
            tid=self.path.rsplit("/",1)[-1]
            item=load_task(tid)
            return self.send_json(200 if item else 404,item or {"error":"task_not_found"})
        return self.send_json(404,{"error":"not_found"})
    def do_POST(self):
        if not self.authorized(): return self.send_json(401,{"error":"unauthorized"})
        if self.path!="/tasks": return self.send_json(404,{"error":"not_found"})
        try:
            n=int(self.headers.get("Content-Length","0"))
            if n>1024*1024: return self.send_json(413,{"error":"payload_too_large"})
            data=json.loads(self.rfile.read(n) or b"{}")
        except Exception: return self.send_json(400,{"error":"invalid_json"})
        task=str(data.get("task","")).strip()
        if not task: return self.send_json(400,{"error":"task_required"})
        requested=data.get("services") or list(SERVICE_MAP)
        if not isinstance(requested,list): return self.send_json(400,{"error":"services_must_be_array"})
        chosen=[k for k in dict.fromkeys(requested) if k in SERVICE_MAP]
        if not chosen: return self.send_json(400,{"error":"no_valid_services"})
        tid=str(uuid.uuid4())
        item={"id":tid,"task":task,"context":str(data.get("context","")),"services":chosen,
              "status":"queued","successful":0,"requested":len(chosen),"finished_workers":0,
              "results":[],"created_at":now(),
              "approval_required_for":["publish","send","purchase","payment","delete","account_permission_change"]}
        save_task(item)
        threading.Thread(target=execute_task,args=(tid,),daemon=True).start()
        return self.send_json(202,item)
    def log_message(self,*a): pass

ThreadingHTTPServer((BIND,PORT),Handler).serve_forever()