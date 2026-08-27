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

RBAC (opt-in, só pra service/app protegido) — quem está logado e o que pode:
  from iteam import user, can, require_role, menu
  me = user(request.headers)               # {"userId","role","projectRole"} (injetado pelo gateway)
  if not can(me, "admin"): ...             # bool, default-deny (owner/admin/dono sempre podem)
  deny = require_role(request.headers, "admin"); # guarda de rota → 403 pronto (ou None)
  telas = menu([{ "title": "X", "path": "/x", "roles": ["admin"] }], me)  # filtra o menu
"""
import os, json, urllib.request

# Versão deste SDK (YYYY.MM.DD, comparável lexicograficamente). check_update() compara com o servidor.
SDK_VERSION = "2026.08.27"

def version():
    """Versão do SDK LOCAL (a que você tem clonada)."""
    return SDK_VERSION

def _safe_print(s):
    # Robusto em consoles não-UTF8 (Windows/cp1252): nunca deixa o print derrubar o check.
    try:
        print(s)
    except Exception:
        try: print(str(s).encode("ascii", "replace").decode("ascii"))
        except Exception: pass

def check_update():
    """Avisa se o seu SDK local está ATRÁS do publicado. RODE ANTES DE CODAR (na IDE):
        python -c "import iteam; iteam.check_update()"
    Se disser DESATUALIZADO, dê `git pull` no iteam-codes-sdk e releia o AGENTS.md.
    Imprime o aviso e retorna {"local","latest","upToDate","message"}."""
    api = os.environ.get("ITEAM_API_URL")
    if not api:
        result = {"local": SDK_VERSION, "latest": None, "upToDate": None,
                  "message": "check_update: defina ITEAM_API_URL (ex.: https://api.iteam.works) para comparar."}
    else:
        try:
            with urllib.request.urlopen(api.rstrip("/") + "/api/project/codes/sdk-version", timeout=10) as r:
                info = json.loads(r.read().decode())
            latest = str(info.get("version") or "")
            up = (not latest) or (SDK_VERSION >= latest)
            if up:
                msg = "[OK] SDK atualizado (local %s)" % SDK_VERSION
            else:
                msg = ("[!] SDK DESATUALIZADO: local %s < publicado %s. Rode `git pull` em %s e releia o AGENTS.md antes de codar."
                       % (SDK_VERSION, latest, info.get("repo", "iteam-codes-sdk")))
            result = {"local": SDK_VERSION, "latest": latest or None, "upToDate": up, "message": msg}
        except Exception as e:
            result = {"local": SDK_VERSION, "latest": None, "upToDate": None,
                      "message": "check_update: nao consegui checar (%s). Na duvida, de `git pull` no SDK." % e}
    _safe_print(result["message"])
    return result

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


# ─────────────────────────────────────────────────────────────────────────────
# RBAC (opt-in) — QUEM está logado e o que PODE ver/chamar.
#
# Para services/apps PROTEGIDOS (public=false), o gateway do iTeam valida o login
# e injeta 3 headers CONFIÁVEIS na requisição que chega ao seu container. O browser
# NÃO consegue forjá-los, por DOIS motivos que só juntos bastam: (a) o container não
# publica porta no host — quem fala com ele é só o gateway; e (b) o gateway APAGA
# X-Iteam-User/Role/Project-Role que venham do cliente ANTES de consultar a auth, e
# só então injeta os valores que o backend afirmou.
# ATENÇÃO no deploy PÚBLICO (public=true): não há login, então os três headers chegam
# VAZIOS — trate como anônimo. Nunca leia papel de um header em rota pública achando
# que "veio do gateway": lá não veio de ninguém.
#   X-Iteam-User          → id do usuário logado
#   X-Iteam-Role          → papel dele NA EMPRESA  (owner/admin/manager/member/viewer)
#   X-Iteam-Project-Role  → papel dele NESTE PROJETO (owner/admin/manager/member/viewer)
# Em job/local/rota pública não há login → tudo vem vazio (trate como anônimo).
# owner/admin da EMPRESA e o dono do PROJETO (owner) SEMPRE podem tudo.
#
# É tudo opt-in: se você não chamar nada disto, todo membro do projeto vê tudo
# (comportamento padrão — nada quebra). Regra de ouro: esconder a tela é só UX;
# proteja SEMPRE a rota/dados no service com require_role() também.
_SUPER_ROLES = ("owner", "admin")

def _hget(headers, name):
    """Lê um header sem se importar com maiúsc/minúsc. Aceita: dict, objeto tipo
    Headers do Flask/FastAPI (.get), ou uma lista de tuplas (k, v)."""
    if not headers:
        return ""
    lname = name.lower()
    getter = getattr(headers, "get", None)
    if callable(getter):
        try:
            v = getter(name)
            if v is None:
                v = getter(lname)
            if v:
                return str(v)
        except Exception:
            pass
    try:
        items = headers.items() if hasattr(headers, "items") else headers
        for k, v in items:
            if str(k).lower() == lname:
                return str(v)
    except Exception:
        pass
    return ""

def user(headers=None):
    """Quem está logado NESTA requisição (papel injetado pelo gateway). Passe os
    headers da requisição do seu framework:
        me = iteam.user(request.headers)          # Flask / FastAPI / Starlette
    → {"userId", "role", "projectRole"}. Tudo vazio = anônimo (job/local/rota pública)."""
    return {
        "userId": _hget(headers, "X-Iteam-User"),
        "role": _hget(headers, "X-Iteam-Role"),
        "projectRole": _hget(headers, "X-Iteam-Project-Role"),
    }

def _who(who):
    """Aceita o dict devolvido por user() OU um objeto/dict de headers (chama user())."""
    if isinstance(who, dict) and "projectRole" in who:
        return who
    return user(who)

def can(who, *roles):
    """True se o usuário PODE (papel dele está entre `roles`). DEFAULT-DENY: papel não
    reconhecido → False. owner/admin da empresa e o dono do projeto SEMPRE podem.
    Sem `roles` informados = qualquer MEMBRO logado pode (mas anônimo não).
        me = iteam.user(request.headers)
        if iteam.can(me, "admin", "manager"): ...
    Pode passar os headers direto também: iteam.can(request.headers, "admin")."""
    u = _who(who)
    if u.get("role") in _SUPER_ROLES or u.get("projectRole") in _SUPER_ROLES:
        return True
    allowed = {str(r).strip().lower() for r in roles if r}
    if not allowed:
        return bool(u.get("userId"))
    have = {str(u.get("role", "")).lower(), str(u.get("projectRole", "")).lower()}
    return bool(have & allowed)

def require_role(who, *roles):
    """GUARDA de rota (service). Retorna None se PODE passar; senão devolve um objeto de
    resposta 403 PRONTO (não estoura exceção). Padrão framework-agnóstico:
        deny = iteam.require_role(request.headers, "admin")
        if deny:
            return jsonify(deny["body"]), deny["status"]     # Flask
    O objeto: {"__forbidden__": True, "status": 403, "body": {"error","message","need","have"}}."""
    if can(who, *roles):
        return None
    u = _who(who)
    return {
        "__forbidden__": True,
        "status": 403,
        "body": {
            "error": "forbidden",
            "message": "Você não tem permissão para acessar isto.",
            "need": [str(r) for r in roles],
            "have": u.get("projectRole") or u.get("role") or None,
        },
    }

def menu(items, who=None):
    """Filtra uma lista de TELAS/itens de menu pelo papel do usuário (pra montar o menu do
    app sem os itens que a pessoa não pode ver). Cada item pode ter a chave `roles` (lista):
    quem não tem o papel não vê o item; item SEM `roles` aparece pra todos.
        telas = iteam.menu([
            {"title": "Início",   "path": "/"},
            {"title": "Vendas",   "path": "/vendas",  "roles": ["admin", "manager"]},
            {"title": "Config",   "path": "/config",  "roles": ["admin"]},
        ], iteam.user(request.headers))
    Esconder é só UX — proteja a rota/dados no service com require_role() também."""
    out = []
    for it in (items or []):
        roles = (it.get("roles") if isinstance(it, dict) else None) or []
        if not roles or can(who, *roles):
            out.append(it)
    return out
