"""
iTeam Codes SDK — helper injetado automaticamente em todo run de um "Code".
Você NÃO precisa instalar credenciais: o iTeam injeta um token de projeto
assinado e escopado no sandbox. Este arquivo existe aqui só para você
desenvolver/testar localmente com autocompletar e ler a documentação.

Recursos disponíveis dentro de um Code:
  from iteam import kv, datastore, iteam_call, iteam_query, iteam_tools

  kv.set("chave", {"qualquer": "json"}, ttl=3600)   # cache/estado por PROJETO
  kv.get("chave"); kv.incr("contador"); kv.keys("*"); kv.delete("chave")

  rows = datastore.query("SELECT ... ")             # Data Store (ClickHouse) read-only

  # tools do agente/projeto (MCP, HTTP, learned, nativas) — sem credenciais no código:
  res  = iteam_call("nome_da_tool", **args)
  rows = iteam_query("ch_query", sql="SELECT ...")
  tools = iteam_tools("clickhouse")                 # descobre tools disponíveis
"""
import os, json, urllib.request

def _post(path, payload):
    url = os.environ["ITEAM_INTERNAL_URL"].rstrip("/") + path
    headers = {"Content-Type": "application/json"}
    tok = os.environ.get("ITEAM_CALL_TOKEN")
    if tok: headers["X-Internal-Token"] = tok
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read().decode())
    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(data["error"])
    return data.get("result") if isinstance(data, dict) else data

def iteam_call(tool, **args): return _post("/internal/code-agent/tool", {"tool": tool, "args": args})
def iteam_query(tool, **args):
    res = iteam_call(tool, **args)
    if isinstance(res, dict):
        for k in ("rows", "data", "records", "items", "result"):
            if isinstance(res.get(k), list): return res[k]
    return res
def iteam_tools(contains=None):
    cat = iteam_call("__list_tools"); tools = cat.get("tools", []) if isinstance(cat, dict) else cat
    if contains: tools = [t for t in tools if contains.lower() in (t.get("name","")+t.get("description","")).lower()]
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
datastore = _DataStore()

def result(value):
    """Retorna o RESULTADO ESTRUTURADO do run (vira run.result no iTeam).
    Chame no fim do Code: result({"ok": True, "total": 42}). Determinístico:
    NÃO dependa de 'última linha do stdout' — sempre use result()."""
    print("__ITEAM_RESULT__" + json.dumps(value, default=str))

class _DB:
    """Postgres ISOLADO do projeto (recurso alocado). read+write no seu próprio banco."""
    def query(self, sql):   return iteam_query("db_query", sql=sql)
    def execute(self, sql): return iteam_call("db_execute", sql=sql)
db = _DB()

def resources():
    """Lista os RECURSOS de dados alocados no projeto (uuid, tipo, namespace).
    Chame PRIMEIRO pra saber o que dá pra usar (datastore=ClickHouse, db=Postgres)."""
    r = iteam_call("resources_list")
    return (r or {}).get("resources", r)
