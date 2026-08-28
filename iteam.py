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
import os, json, urllib.request, urllib.error

# Versão deste SDK (YYYY.MM.DD[.n] — o sufixo distingue duas releases no mesmo dia; comparável lexicograficamente). check_update() compara com o servidor.
SDK_VERSION = "2026.08.28"

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
                      "message": (_AJUDA_REDE if _rede_bloqueada(e)
                                  else "check_update: nao consegui checar (%s). Na duvida, de `git pull` no SDK." % e)}
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


# ─────────────────────────────────────────────────────────────────────────────
# CONCORRÊNCIA — duas pessoas mexendo no MESMO Code ao mesmo tempo.
#
# O deploy SUBSTITUI `code` e `files` inteiros. Sem controle, quem salva por último apaga o outro
# em SILÊNCIO — e como a lista de arquivos é trocada, some ARQUIVO, não linha.
#
# O SDK não se limita a avisar: ele **junta** as duas versões. Para isso o `code_pull` guarda a
# BASE (o conteúdo exato de onde você partiu) em `.iteam-code.json`. No `code_push`, se o servidor
# recusar (409), o SDK puxa a versão nova e faz um merge de 3 vias — base × sua × do servidor:
#
#   • arquivo que só VOCÊ mexeu      → fica o seu
#   • arquivo que só O OUTRO mexeu   → fica o dele (você não o perde por não ter tocado nele)
#   • os dois mexeram, em trechos diferentes do arquivo → junta os dois trechos
#   • os dois mexeram no MESMO trecho → aí ninguém pode decidir por você: PERGUNTA (ou levanta
#     ConflitoDeRevisao com o texto marcado, quando não há terminal)
#
# Depois do merge ele reenvia sozinho com a revisão nova. Nada é sobrescrito sem decisão.
# `.iteam-code.json` é local (ponha no .gitignore) — não sobe no deploy.
import difflib, sys

_REV_FILE = ".iteam-code.json"

class ConflitoDeRevisao(Exception):
    """Sobrou conflito que o SDK não pode decidir sozinho.
    `.detalhes` traz quem gravou e quando; `.arquivos_em_conflito` traz os caminhos;
    `.merge` traz o conteúdo já fundido, com marcadores nos trechos disputados."""
    def __init__(self, detalhes, arquivos_em_conflito=None, merge=None):
        self.detalhes = detalhes or {}
        self.arquivos_em_conflito = arquivos_em_conflito or []
        self.merge = merge or {}
        super().__init__(self.detalhes.get("message") or "conflito de revisão")

def _rede_bloqueada(msg):
    """Sandbox na nuvem cortou a saída? A mensagem do proxy é reconhecível e o remédio não é óbvio
    para quem só vê 'falhou' — sem isto, o agente fica tentando token e projeto, que estão certos."""
    t = str(msg or "").lower()
    return ("not in allowlist" in t or "egress" in t
            or ("proxy" in t and "block" in t)
            or "name or service not known" in t or "getaddrinfo" in t)

_AJUDA_REDE = (
    "A rede deste ambiente bloqueou a saida para o iTeam (allowlist de egress) — nao e token nem "
    "projeto errado: a requisicao nem chegou la. Peca a um admin do ambiente para liberar "
    "'api.iteam.works' (ou 'stg.api.iteam.works' em homologacao). Enquanto isso da para escrever o "
    "codigo normalmente e deixar o deploy para depois."
)

def _codes_api(path, method="GET", body=None):
    api = os.environ.get("ITEAM_API_URL")
    pct = os.environ.get("ITEAM_PROJECT_TOKEN")
    if not api or not pct:
        raise RuntimeError("Configure ITEAM_API_URL + ITEAM_PROJECT_TOKEN (token do projeto, aba Codes).")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(api.rstrip("/") + path, data=data, method=method, headers={
        "Content-Type": "application/json", "Authorization": "Bearer " + pct})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        corpo = {}
        try: corpo = json.loads(e.read().decode())
        except Exception: pass
        if e.code == 409:
            raise ConflitoDeRevisao(corpo)
        detalhe = corpo.get("message") or corpo.get("error") or e.reason
        if _rede_bloqueada(detalhe):
            raise RuntimeError(_AJUDA_REDE)
        raise RuntimeError("%s %s: %s" % (e.code, path, detalhe))
    except urllib.error.URLError as e:
        # Nem chegou a haver resposta HTTP: DNS/proxy barrou antes.
        if _rede_bloqueada(getattr(e, "reason", "")):
            raise RuntimeError(_AJUDA_REDE)
        raise


# ── merge de 3 vias, por linha ───────────────────────────────────────────────────────────────
def _blocos_alterados(ops):
    """Trechos NÃO-iguais de um diff, em coordenadas da BASE."""
    return [(i1, i2) for tag, i1, i2, _j1, _j2 in ops if tag != "equal"]

def _mapear(ops, seq, a, z):
    """Texto do lado `seq` correspondente ao intervalo [a,z) da base.
    Em trecho igual a correspondência é linha a linha; em trecho alterado entra o bloco inteiro
    (por isso os blocos são fundidos antes: nunca cortamos uma alteração ao meio)."""
    out = []
    for tag, i1, i2, j1, j2 in ops:
        # Inserção pura tem LARGURA ZERO na base (i1 == i2): não ocupa linha do original, só marca
        # onde entrou. O recorte normal a descartava e as linhas inseridas sumiam do merge — em
        # silêncio, que é o pior jeito de errar aqui. Vai por contenção de POSIÇÃO, com as bordas.
        if i1 == i2:
            if a <= i1 <= z:
                out.extend(seq[j1:j2])
            continue
        if i2 <= a or i1 >= z:
            continue
        if tag == "equal":
            ini = j1 + (max(i1, a) - i1)
            fim = j1 + (min(i2, z) - i1)
            out.extend(seq[ini:fim])
        else:
            out.extend(seq[j1:j2])
    return out

def merge3(base, meu, deles, rotulo_meu="seu", rotulo_deles="servidor"):
    """Junta duas edições feitas sobre a mesma base. Devolve (texto, houve_conflito).
    Trechos disputados pelos dois lados saem com marcadores no estilo do git."""
    if meu == deles: return meu, False
    if base == meu:  return deles, False   # você não mexeu neste arquivo
    if base == deles: return meu, False    # o outro não mexeu neste arquivo

    b = base.splitlines(True); m = meu.splitlines(True); d = deles.splitlines(True)
    om = difflib.SequenceMatcher(None, b, m).get_opcodes()
    od = difflib.SequenceMatcher(None, b, d).get_opcodes()

    # Blocos que se sobrepõem viram UM bloco: senão um lado teria a alteração partida ao meio.
    brutos = sorted(_blocos_alterados(om) + _blocos_alterados(od))
    blocos = []
    for i1, i2 in brutos:
        if blocos and i1 <= blocos[-1][1]:
            blocos[-1][1] = max(blocos[-1][1], i2)
        else:
            blocos.append([i1, i2])

    saida = []; conflito = False; pos = 0
    for i1, i2 in blocos:
        saida.extend(b[pos:i1])                 # trecho intocado pelos dois
        tm = _mapear(om, m, i1, i2)
        td = _mapear(od, d, i1, i2)
        orig = b[i1:i2]
        if tm == td:      saida.extend(tm)      # os dois chegaram no mesmo texto
        elif tm == orig:  saida.extend(td)      # só o outro mexeu aqui
        elif td == orig:  saida.extend(tm)      # só você mexeu aqui
        else:
            conflito = True
            saida.append("<<<<<<< %s\n" % rotulo_meu)
            saida.extend(tm)
            saida.append("=======\n")
            saida.extend(td)
            saida.append(">>>>>>> %s\n" % rotulo_deles)
        pos = i2
    saida.extend(b[pos:])
    return "".join(saida), conflito


# ── estado local (base + revisão) ────────────────────────────────────────────────────────────
def _rev_path(pasta="."): return os.path.join(pasta, _REV_FILE)

def _le_estado(pasta="."):
    try:
        with open(_rev_path(pasta), "r", encoding="utf-8") as f: return json.load(f)
    except Exception:
        return {}

def code_revision(pasta="."):
    """Revisão registrada no último pull/push desta pasta (None se nunca puxou)."""
    return _le_estado(pasta).get("revision")

def _grava_estado(pasta, d):
    """Guarda revisão + BASE (conteúdo de onde você partiu). Sem a base não há merge possível —
    dá para saber QUE mudou, nunca O QUE cada lado mudou."""
    try:
        with open(_rev_path(pasta), "w", encoding="utf-8") as f:
            json.dump({
                "codeId": d.get("codeId"), "slug": d.get("slug"), "revision": d.get("revision"),
                "base": {"code": d.get("code") or "",
                         "files": {f_["path"]: f_.get("content", "") for f_ in (d.get("files") or []) if f_.get("path")}},
            }, f, indent=1)
    except Exception:
        pass  # sem permissão de escrita: o push ainda funciona, só sem merge automático

def code_pull(code_id, pasta="."):
    """Baixa o Code e registra revisão + base para o próximo push. Devolve o dict do pull."""
    d = _codes_api("/api/project/codes/%s/pull" % code_id)
    _grava_estado(pasta, d)
    return d


# ── push com detecção e resolução ────────────────────────────────────────────────────────────
def _como_dict(files): return {f["path"]: f.get("content", "") for f in (files or []) if f.get("path")}
def _como_lista(dic):  return [{"path": k, "content": v} for k, v in sorted(dic.items())]

def _perguntar(caminho, texto_marcado, interativo):
    """Só pergunta o que ninguém pode decidir por você: os dois mexeram no MESMO trecho."""
    if not interativo:
        return None
    _safe_print("\n[!] Conflito em %s — voces dois mexeram no mesmo trecho:\n" % caminho)
    _safe_print(texto_marcado[:2000])
    _safe_print("\n  [s] fica o SEU   [o] fica o do OUTRO   [m] gravar com os marcadores e revisar")
    try:
        return (input("  escolha [s/o/m]: ") or "").strip().lower()[:1]
    except Exception:
        return None

def code_push(payload, pasta=".", forcar=False, ao_conflitar="perguntar", permitir_remocao=False):
    """Grava o Code. Se alguém gravou desde o seu pull, o SDK NÃO sobrescreve: puxa a versão nova,
    junta as duas (merge de 3 vias) e reenvia. Só para se os dois mexeram no mesmo trecho.

    ao_conflitar: "perguntar" (pergunta no terminal; sem terminal, levanta),
                  "meu" / "deles" (decide sempre para um lado no trecho disputado),
                  "abortar" (levanta ConflitoDeRevisao com o texto já fundido e marcado).
    forcar=True pula tudo e sobrescreve — a versão do servidor SOME. Use só com certeza.

        iteam.code_pull("<codeId>")
        iteam.code_push({"name": "Minha API", "slug": "minha-api", "files": [...]})
    """
    estado = _le_estado(pasta)
    corpo = dict(payload or {})

    # TRAVA DA PASTA INCOMPLETA — a lista `files` SUBSTITUI a do servidor. Mandar só o arquivo que
    # você mexeu não é "atualizar um arquivo": é dizer que o Code passou a ter só aquele. Some o
    # resto. É o erro mais fácil de cometer aqui, e some ARQUIVO, não linha — por isso é um erro
    # explícito, não um aviso. Para apagar de verdade, passe permitir_remocao=True.
    base_ini = (estado.get("base") or {}).get("files") or {}
    if corpo.get("files") is not None and base_ini and not permitir_remocao:
        sumiriam = sorted(set(base_ini) - set(_como_dict(corpo.get("files"))))
        if sumiriam:
            raise RuntimeError(
                "code_push apagaria %d arquivo(s) que existem no Code: %s. "
                "Mande a PASTA INTEIRA (a lista `files` substitui a do servidor). "
                "Se a remoção é intencional, chame com permitir_remocao=True."
                % (len(sumiriam), ", ".join(sumiriam[:8])))

    if not forcar and estado.get("revision") is not None:
        corpo["baseRevision"] = estado["revision"]
    try:
        r = _codes_api("/api/project/codes", method="POST", body=corpo)
        _grava_estado(pasta, {"codeId": r.get("codeId"), "slug": r.get("slug"), "revision": r.get("revision"),
                              "code": corpo.get("code"), "files": corpo.get("files")})
        return r
    except ConflitoDeRevisao as c:
        base = estado.get("base") or {}
        if not base:
            # Nunca houve pull nesta pasta: sem base não dá para saber o que CADA lado mudou.
            c.detalhes.setdefault("dica", "Rode code_pull() antes de editar — sem a base o SDK nao pode fundir.")
            raise

        code_id = c.detalhes.get("codeId") or estado.get("codeId") or corpo.get("codeId")
        if not code_id:
            raise
        atual = _codes_api("/api/project/codes/%s/pull" % code_id)

        meus = _como_dict(corpo.get("files"))
        deles = _como_dict(atual.get("files"))
        base_files = base.get("files") or {}
        interativo = (ao_conflitar == "perguntar") and sys.stdin is not None and sys.stdin.isatty()

        juntos = {}; em_conflito = []
        for caminho in sorted(set(meus) | set(deles) | set(base_files)):
            b = base_files.get(caminho); mm = meus.get(caminho); dd = deles.get(caminho)
            # apagado por um lado e intocado pelo outro: respeita quem apagou
            if mm is None and dd is not None:
                if b is not None and dd == b: continue          # você apagou, ele não mexeu
                if b is None: juntos[caminho] = dd; continue    # arquivo novo dele
            if dd is None and mm is not None:
                if b is not None and mm == b: continue          # ele apagou, você não mexeu
                juntos[caminho] = mm; continue                  # arquivo novo seu (ou você editou)
            if mm is None and dd is None: continue
            texto, houve = merge3(b if b is not None else "", mm, dd)
            if houve:
                escolha = _perguntar(caminho, texto, interativo) if ao_conflitar == "perguntar" else \
                          ("s" if ao_conflitar == "meu" else "o" if ao_conflitar == "deles" else None)
                if escolha == "s":   texto = mm
                elif escolha == "o": texto = dd
                else:                em_conflito.append(caminho)
            juntos[caminho] = texto

        codigo, houve_code = merge3(base.get("code") or "", corpo.get("code") or atual.get("code") or "",
                                    atual.get("code") or "")
        if houve_code:
            escolha = _perguntar("(arquivo de entrada)", codigo, interativo) if ao_conflitar == "perguntar" else \
                      ("s" if ao_conflitar == "meu" else "o" if ao_conflitar == "deles" else None)
            if escolha == "s":   codigo = corpo.get("code") or ""
            elif escolha == "o": codigo = atual.get("code") or ""
            else:                em_conflito.append("(arquivo de entrada)")

        if em_conflito:
            merge_parcial = dict(juntos); merge_parcial["(arquivo de entrada)"] = codigo
            c.detalhes["message"] = (
                "Voces dois mexeram no MESMO trecho de: %s. O resto ja foi juntado automaticamente. "
                "Abra o texto marcado (<<<<<<< seu / >>>>>>> servidor), decida os trechos e chame "
                "code_push de novo." % ", ".join(em_conflito))
            raise ConflitoDeRevisao(c.detalhes, em_conflito, merge_parcial)

        # Tudo resolvido: reenvia sobre a revisão nova.
        corpo["files"] = _como_lista(juntos)
        if corpo.get("code") is not None or codigo: corpo["code"] = codigo
        corpo["baseRevision"] = atual.get("revision")
        r = _codes_api("/api/project/codes", method="POST", body=corpo)
        r["merge"] = {"juntado_com": c.detalhes.get("alteradoPor"), "arquivos": sorted(juntos.keys())}
        _grava_estado(pasta, {"codeId": r.get("codeId"), "slug": r.get("slug"), "revision": r.get("revision"),
                              "code": corpo.get("code"), "files": corpo.get("files")})
        _safe_print("[merge] juntei suas mudancas com as de %s e gravei (revisao %s)."
                    % (c.detalhes.get("alteradoPor") or "outra pessoa", r.get("revision")))
        return r
