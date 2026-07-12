"""
iTeam Codes SDK — DUAL-MODE (roda igual local na sua IDE e no sandbox do iTeam).

Local (Claude Code / Cursor / VS Code), pra TESTAR sem deploy e sem segredo:
  export ITEAM_API_URL=https://api.iteam.works        # (ou https://stg.api.iteam.works)
  export ITEAM_PROJECT_TOKEN=pct_...                  # token do projeto (aba Codes) — no .env, NUNCA no git
  python main.py
No sandbox (deploy) o iTeam injeta o acesso automaticamente — você não muda nada.

Você NUNCA coloca credencial de recurso/agente: o backend resolve pelo token do projeto e
executa server-side (secrets ficam no cofre). Recursos:
  from iteam import resources, agent_tools, iteam_call, iteam_query, kv, datastore, db, get_input, result
  resources()            # recursos de dados alocados (kv/datastore/db)
  agent_tools()          # tools dos AGENTES do projeto (MCP/HTTP/learned) — chame por iteam_call
  kv.set/get/...         # cache/estado do projeto
  db.query/execute/tables/columns          # Postgres isolado do projeto
  datastore.query/tables/columns           # ClickHouse do projeto
  iteam_call("nome_tool", **args)          # chama uma tool de um agente do projeto
  result({...})          # resultado estruturado do run
"""
import os, json, urllib.request

def _endpoint():
    call_tok = os.environ.get("ITEAM_CALL_TOKEN")
    internal = os.environ.get("ITEAM_INTERNAL_URL")
    if call_tok and internal:  # dentro do sandbox
        return internal.rstrip("/") + "/internal/code-agent/tool", {"X-Internal-Token": call_tok}, "wrap"
    api = os.environ.get("ITEAM_API_URL"); pct = os.environ.get("ITEAM_PROJECT_TOKEN")
    if api and pct:            # local (IDE)
        return api.rstrip("/") + "/api/project/codes/call", {"Authorization": "Bearer " + pct}, "wrap"
    raise RuntimeError("Configure ITEAM_API_URL + ITEAM_PROJECT_TOKEN (local) ou rode no sandbox do iTeam.")

def iteam_call(tool, **args):
    url, auth, _ = _endpoint()
    payload = json.dumps({"tool": tool, "args": args}).encode()
    headers = {"Content-Type": "application/json", **auth}
    req = urllib.request.Request(url, data=payload, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read().decode())
    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(data["error"])
    return data.get("result") if isinstance(data, dict) else data

def iteam_query(tool, **args):
    res = iteam_call(tool, **args)
    if isinstance(res, dict):
        for k in ("rows", "data", "records", "items", "result"):
            if isinstance(res.get(k), list): return res[k]
    return res

def resources():        return iteam_call("resources_list")
def agent_tools(contains=None):
    cat = iteam_call("agent_tools"); tools = cat.get("tools", []) if isinstance(cat, dict) else (cat or [])
    if contains:
        c = str(contains).lower(); tools = [t for t in tools if c in (str(t.get("name",""))+str(t.get("description",""))).lower()]
    return tools

class _KV:
    def get(self, key): return iteam_call("kv_get", key=key)
    def set(self, key, value, ttl=None): return iteam_call("kv_set", key=key, value=value, ttl=ttl)
    def delete(self, key): return iteam_call("kv_del", key=key)
    def incr(self, key, by=1): return iteam_call("kv_incr", key=key, by=by)
    def keys(self, pattern="*"): return iteam_call("kv_keys", pattern=pattern)
kv = _KV()

class _DataStore:
    def query(self, sql): return iteam_query("datastore_query", sql=sql)
    def tables(self): return iteam_call("datastore_tables")
    def columns(self, table): return iteam_call("datastore_columns", table=table)
datastore = _DataStore()

class _DB:
    def query(self, sql): return iteam_query("db_query", sql=sql)
    def execute(self, sql): return iteam_call("db_execute", sql=sql)
    def tables(self): return iteam_call("db_tables")
    def columns(self, table): return iteam_call("db_columns", table=table)
db = _DB()

def get_input():
    """Parâmetros de ENTRADA deste run (dict). Vêm de quem chamou o Code — agente (proj_run_code),
    endpoint HTTP (POST .../run {input}) ou UI. Declare o contrato no manifest.inputSchema."""
    try:
        return json.loads(os.environ.get("ITEAM_INPUT") or "{}")
    except Exception:
        return {}

def result(value):
    """Saída ESTRUTURADA do Code (é o que o chamador recebe). Declare o formato em manifest.outputSchema."""
    print("__ITEAM_RESULT__" + json.dumps(value, default=str))
