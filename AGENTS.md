# Guia do Agente — iTeam Codes

Você (IA em Claude Code / Cursor / VS Code / Copilot) está ajudando a criar e manter
**Codes do iTeam**: scripts Python/Node que rodam num sandbox efêmero isolado, com
recursos escopados por projeto e agendamento. Leia este guia inteiro antes de agir.

## ⚠️ ANTES DE COMEÇAR — pergunte o PROJETO e faça PULL (não comece do zero)
1. Pergunte ao usuário o **ID do projeto** e o **token do projeto** (`pct_...`, aba Codes). Coloque o token no `.env` (`ITEAM_PROJECT_TOKEN`), NUNCA no git.
2. Descubra onde você está e o que já existe:
   ```bash
   curl -s $ITEAM_API/api/project/codes/context -H "Authorization: Bearer $ITEAM_PROJECT_TOKEN"   # → { projectId }
   curl -s $ITEAM_API/api/project/codes         -H "Authorization: Bearer $ITEAM_PROJECT_TOKEN"   # lista os Codes (slug, contrato I/O)
   ```
3. Se vai MEXER num Code existente, faça **PULL** primeiro (continua de onde parou, não recria do zero):
   ```bash
   curl -s $ITEAM_API/api/project/codes/CODE_ID/pull -H "Authorization: Bearer $ITEAM_PROJECT_TOKEN"
   # → { name, slug, language, code, files[], inputSchema, outputSchema, envKeys, ... }  (o .env NÃO vem — só as chaves)
   ```
   Grave `code` em `main.py` e cada `files[].content` no `files[].path`. Edite. Depois faça deploy com o MESMO slug (atualiza, não duplica).

`$ITEAM_API` = https://api.iteam.works (prod) ou https://stg.api.iteam.works (hom).

## O que é um Code
- Um entrypoint (`main.py` ou `main.js`) + arquivos extras opcionais — pode ser um **mini-serviço** parametrizável.
- Roda isolado (cria→roda→destrói). Sem estado entre runs, EXCETO o que você salvar no `kv`.
- Recebe um token de projeto assinado via ambiente — **você nunca escreve credenciais no código**.
- **Parametrizável (entrada/saída)**: `input = get_input()` lê os parâmetros de quem chamou; `result({...})` devolve a saída. Declare o contrato no deploy (`inputSchema` / `outputSchema`) — é isso que os **agentes** e os endpoints usam pra saber como chamar e o que esperam.
- **Chamável pelos agentes do projeto**: se `published: true` (default), os agentes do projeto executam o Code via `proj_run_code(slug, input)` e recebem o `result` — a base dos microserviços.

## SDK (importe e use)
```python
from iteam import kv, datastore, iteam_call, iteam_query, iteam_tools, result
```
- `kv.set/get/delete/incr/keys` — cache/estado chave-valor **isolado por projeto** (Redis no servidor).
- `datastore.query(sql)` — **Data Store** analítico do projeto (ClickHouse). Se o projeto ALOCOU um Data Store,
  é **read+WRITE** (crie tabelas, insira, agregue). Sem Data Store alocado, só há leitura no compartilhado —
  para gravar, o usuário precisa **Ativar** o Data Store na aba Codes.
- `db.query/execute/tables/columns` — **Postgres** relacional do projeto (read+write, se alocado).
- `agent_tools()` — catálogo das tools dos AGENTES do projeto (nome + schema). Chame por `iteam_call`/`iteam_query`.
- `resources()` — recursos de dados alocados no projeto (kv/datastore/db).
- `iteam_call(tool, **args)` / `iteam_query(...)` — executa uma tool de agente/projeto (MCP, HTTP, APIs aprendidas).
- `result({...})` — **SEMPRE** retorne o resultado estruturado com isto (vira `run.result`). NÃO confie em "última linha".

## Descobrir os recursos disponíveis (BATA AQUI PRIMEIRO)
Antes de escrever qualquer lógica, faça DUAS chamadas para saber o que o projeto oferece e como usar cada coisa:
```python
from iteam import resources, agent_tools
resources()      # → recursos de DADOS do projeto: [{uuid, type: 'clickhouse'|'postgres', namespace, sdk}]
agent_tools()    # → ferramentas dos AGENTES do projeto: [{name, description, parameters(schema), source, agentId}]
```
`agent_tools()` traz o **schema de cada ferramenta** (parâmetros) — é assim que você (IDE/IA) sabe exatamente
como chamar cada uma sem adivinhar. Some naturalmente o Atlas/descrição do recurso quando disponível.

## Regras de ouro (NÃO viole)
1. **Segredos só no `.env`** (já está no `.gitignore`). Nunca no código, nunca no Git, nunca em `print`.
2. **Retorne com `result({...})`** no fim — é o jeito determinístico. `print()` é só log.
3. **Idempotência**: cada Code tem um `slug` estável (derivado do nome) e um `id`. Reenviar o
   deploy com o **mesmo nome/slug ATUALIZA** o mesmo Code — não crie nomes novos a cada versão,
   senão vira 1000 cópias. Guarde o `codeId` retornado e reuse.
4. **Nada de credencial de banco/API no código** — use `kv`, `datastore`, `iteam_call`.
5. Trabalho temporário: use o SQLite efêmero em `os.environ["CODE_SCRATCH_DB"]` (some ao fim do run).

## Fluxo de trabalho
1. Clone/leia este repo (SDK + este guia).
2. Escreva `main.py` (+ arquivos extras). Use o SDK. Termine com `result({...})`.
3. Coloque segredos no `.env` (copie de `.env.example`).
4. Deploy com o token do projeto (`pct_...`, fica na aba **Codes** do projeto no iTeam):
   ```bash
   curl -X POST $ITEAM_API/api/project/codes \
     -H "Authorization: Bearer pct_TOKEN" -H "Content-Type: application/json" \
     -d '{"name":"NOME ESTÁVEL","language":"python","code":"<conteúdo de main.py>",
          "files":[{"path":"lib/util.py","content":"..."}],
          "schedule":"0 6 * * *", "env":{"X":"y"},
          "published": true,
          "inputSchema": {"type":"object","properties":{"segment":{"type":"string"},"limit":{"type":"integer"}},"required":["segment"]},
          "outputSchema": {"type":"object","properties":{"rows":{"type":"array"}}}}'
   # → { "codeId": "...", "slug": "...", "name": "..." }  ← guarde codeId/slug p/ atualizar
   ```
   `$ITEAM_API` = https://api.iteam.works (prod) ou https://stg.api.iteam.works (hom).
   `inputSchema`/`outputSchema` = contrato do mini-serviço (o que agentes/endpoints veem). `published:true` = chamável pelos agentes.
5. Rodar: `POST $ITEAM_API/api/project/codes/CODE_ID/run` com body `{"input": {...}}` → `{ runId }`.
6. Ver resultado: `GET $ITEAM_API/api/project/codes/CODE_ID/runs/RUN_ID` → status/stdout/**result**.

## Multi-arquivo
Passe extras em `files: [{ "path": "lib/util.py", "content": "..." }]`. Eles são gravados
junto do `main.py`; importe normalmente (`from lib.util import x`). O entrypoint é sempre o `code`.

## Agendamento
`schedule` = cron (ex.: `*/15 * * * *`, `0 6 * * *`). Roda sozinho, como uma tarefa.

## Exemplo completo (main.py)
```python
from iteam import kv, datastore, result
rows = datastore.query("SELECT count() AS n FROM eventos WHERE dia = today()-1")
n = rows[0]["n"] if rows else 0
prev = kv.get("ontem") or 0
kv.set("ontem", n, ttl=7*24*3600)
result({"ok": True, "hoje": n, "delta": n - prev})
```

## Exemplo PARAMETRIZADO (mini-serviço chamável por agente)
```python
from iteam import get_input, datastore, result
inp = get_input()                       # ex.: {"segment": "Campeoes", "limit": 20}
seg = inp.get("segment"); lim = int(inp.get("limit", 50))
rows = datastore.query(
    f"SELECT user_id, monetary FROM rfm_daily WHERE segment = '{seg}' ORDER BY monetary DESC LIMIT {lim}")
result({"segment": seg, "count": len(rows), "rows": rows})
# Deploy com inputSchema/outputSchema + published:true → um agente do projeto chama:
#   proj_run_code(slug="rfm-por-segmento", input={"segment":"Campeoes","limit":10})
```

## Recursos de dados do projeto (farm_resources) — PEGUE PRIMEIRO
Ao começar, descubra o que o projeto tem alocado:
```python
from iteam import resources, datastore, db
res = resources()   # [{uuid, type, namespace, sdk}, ...]
```
- **datastore** (ClickHouse do projeto, se alocado) — analítico, colunar: `datastore.query("SELECT ...")`.
- **db** (Postgres isolado do projeto, se alocado) — relacional read+write: `db.execute("CREATE TABLE ...")`, `db.query("SELECT ...")`.
- Recursos são ATIVADOS pelo usuário na aba Codes (não automático). Se `resources()` não trouxer o tipo, peça pro usuário ativar. Nunca há credencial no código — o iTeam resolve pelo token do projeto e isola (um projeto nunca acessa o recurso de outro). Cada objeto que você criar fica nesse espaço isolado do projeto.

## Conhecer o schema ANTES de escrever SQL (evita erro)
```python
datastore.tables()            # tabelas do ClickHouse do projeto (com rows/bytes)
datastore.columns("eventos")  # colunas + tipos
db.tables()                   # tabelas do Postgres do projeto
db.columns("clientes")        # colunas + tipos + nullable
```
Fluxo recomendado: `resources()` → `db.tables()/datastore.tables()` → `columns(tabela)` → então escreva o SELECT/INSERT certo.

## Onde vive a infra dos recursos (para operadores)
- **ClickHouse** = cluster analytics do iTrack (gerenciado). DB isolado por projeto (`proj_<id>`).
- **Postgres** = node dedicado do `farm_resources` (hoje `pg-hom4`, container `resource-pg` em hom-4), backup S3 (Contabo) a cada 6h. DB + role isolados por projeto; o runtime conecta como a role escopada (o Code nunca vê credencial). Novos nodes entram no farm e cada recurso guarda em qual node vive.

## Testar LOCAL (na IDE) sem deploy e sem segredo
```bash
export ITEAM_API_URL=https://api.iteam.works      # stg.api.iteam.works p/ homolog
export ITEAM_PROJECT_TOKEN=pct_...                # token do projeto (aba Codes); no .env, NUNCA no git
python main.py                                    # o SDK usa o token do projeto contra /api/project/codes/call
```
O mesmo `main.py` roda idêntico no deploy (o iTeam injeta o acesso no sandbox). Você nunca manuseia segredo.

## Recursos dos AGENTES do projeto (MCP, HTTP tools, learned APIs, datasources)
Se há agentes no projeto, as tools deles viram catálogo:
```python
from iteam import agent_tools, iteam_call, iteam_query
for t in agent_tools():            # nome + descrição + schema
    print(t["name"], t.get("description"))
rows = iteam_query("ch_query", sql="SELECT ...")   # ex.: MCP ClickHouse de um agente
res  = iteam_call("alguma_tool", **args)           # HTTP tool / learned API / MCP
```
O backend acha QUAL agente do projeto tem a tool e executa com a credencial dele (cofre) — o segredo nunca chega ao seu código. Tirou o agente do projeto → a tool some do catálogo e para de funcionar.

## Tipos de Code: job · service · app (service_farm)
Todo Code tem **`kind`** (default `job`) + **título** (`name`) + **descrição**:
- **`job`** — roda e termina (o clássico; efêmero no Daytona). Usa `get_input()`/`result()`.
- **`service`** — **API HTTP persistente** (vários endpoints, vários arquivos) rodando na *service-farm*, atrás do gateway (`https://svc.iteam.works/s/<projectId>/<slug>/…`). Escute em `process.env.PORT`.
- **`app`** — **microfront** (várias telas num deploy) servido pela farm (`/a/<projectId>/<slug>/…`), protegido por login iTeam (ou público).

**Documente o contrato** (os AGENTES do projeto leem isto pra saber o que existe e como usar):
- service → `endpoints`: `[{ "method":"GET", "path":"/hello", "summary":"diz oi", "inputSchema":{…}, "outputSchema":{…} }]`
- app → `screens`: `[{ "title":"Home", "path":"/" }, { "title":"Vendas", "path":"/vendas", "description":"…" }]`

**Robustez — TESTES:** defina `testCommand` (ex.: `"npm test"`, `"pytest -q"`). No deploy, os testes rodam dentro da imagem buildada **antes** de subir o container; **se falharem, o deploy é abortado** (nada quebrado no ar). O resultado fica visível na tela do Code.

### Pull → evoluir → deploy (via token do projeto)
```bash
# 1) PULL: entende o que é o Code (kind, endpoints/screens, testCommand, deploy.url) e continua de onde parou
curl -H "Authorization: Bearer $ITEAM_PROJECT_TOKEN" $ITEAM_API_URL/api/project/codes/<id>/pull
# 2) evolua os arquivos e re-suba com o MESMO slug (atualiza, não duplica)
curl -X POST -H "Authorization: Bearer $ITEAM_PROJECT_TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"Minha API","slug":"minha-api","language":"node","kind":"service","public":false,
       "code":"…server.js…","files":[…],"endpoints":[{"method":"GET","path":"/hello"}],
       "testCommand":"npm test"}' \
  $ITEAM_API_URL/api/project/codes
# 3) DEPLOY (build + testes + run na farm) — devolve a URL pública
curl -X POST -H "Authorization: Bearer $ITEAM_PROJECT_TOKEN" $ITEAM_API_URL/api/project/codes/<id>/deploy
# status/URL
curl -H "Authorization: Bearer $ITEAM_PROJECT_TOKEN" $ITEAM_API_URL/api/project/codes/<id>/deploy-status
```

### Os AGENTES do projeto conhecem e usam as APIs/telas
Um agente que está no projeto ganha tools nativas:
- **`proj_list_services`** — lista os services (APIs) e apps (telas) do projeto, com título, descrição, endpoints e telas.
- **`proj_call_service`** — chama um endpoint de um service que está NO AR (`slug` + `path` + `method`/`body`). Para services protegidos, o backend autentica o agente automaticamente (sem segredo no código).

Ou seja: o agente descobre as APIs do próprio projeto e as usa — do mesmo jeito que chama os Codes (`proj_list_codes`/`proj_run_code`).
