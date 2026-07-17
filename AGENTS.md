# Guia do Agente — iTeam Codes

Você (IA em Claude Code / Cursor / VS Code / Copilot) está ajudando alguém a **construir algo dentro
de um projeto iTeam** — mesmo que a pessoa não saiba programar. Ela descreve em português o que quer;
**você escolhe o tipo, escreve o código e faz o deploy**. Tudo roda isolado por projeto, com recursos
(bancos, APIs, MCPs) já disponíveis **sem senha no código**. Leia este guia inteiro antes de agir.

## 🧩 O que dá pra criar aqui (escolha 1 tipo — o campo `kind`)
Pergunte ao usuário o que ele quer e escolha o tipo. Dá pra **combinar** (uma API + as telas dela).

### 1. `job` — um código que **roda e termina** (padrão)
Um script (Python/Node) que faz uma tarefa e acaba: relatório, ETL, classificação, envio, importação.
Pode receber parâmetros (`get_input()`) e devolver resultado (`result({...})`), e ser **agendado**.
Roda isolado, **sem servidor no ar**.
→ *"Todo dia 9h, classifique os clientes e grave no Data Store."*

### 2. `service` — uma **API HTTP** (uma ou várias rotas)
Um backend que **fica no ar** (persistente), com um ou vários endpoints (GET/POST/PUT/DELETE), atrás de
um domínio seguro (`https://svc.iteam.works/...`). Escute em `process.env.PORT`. Liste as rotas em `endpoints`
(vira um viewer estilo Swagger + os agentes do projeto passam a saber chamar).
→ *"Uma API de tarefas: GET /tarefas, POST /tarefas."*

### 3. `app` — **TELAS** (um "Artefato": uma ou várias telas) — inclusive **pra uma API**
Uma ou várias telas (front-end **React com o design system do iTeam**) num único deploy — por exemplo,
**um painel que consome a sua própria API (`service`)**. Fica no ar em `https://svc.iteam.works/...`,
**protegido por login iTeam por padrão** (ou público, se você marcar). Liste as telas em `screens`.
O agente do projeto pode até abrir o artefato.
→ *"Um painel com as telas Home, Tarefas e Relatórios mostrando os dados da minha API."*

> **Dica pro caso comum (leigo):** "quero um sisteminha de X" normalmente = **um `service` (a API/dados)
> + um `app` (as telas)**. Crie os dois, com o mesmo nome-base, e conecte as telas na API por
> `fetch('/s/<projectId>/<slug-da-api>/...')` (mesmo domínio, sem CORS). Veja a seção **service/app** no fim.

## ⚠️ ANTES DE COMEÇAR — pergunte o PROJETO e faça PULL (não comece do zero)

> **0. ATUALIZE O SDK PRIMEIRO (sempre, antes de escrever qualquer linha).** Este repo evolui e ganha
> recursos novos com o tempo (ex.: o RBAC `user/can/require_role/menu` só existe a partir de julho/2026).
> Se você — ou o projeto — já clonou isto antes, **quem tem uma cópia antiga NÃO enxerga o que veio depois**
> e vai ou reimplementar coisa na mão ou usar algo que não bate com o servidor. Então:
> ```bash
> git -C iteam-codes-sdk pull        # se já tem o repo
> # ou, se ainda não tem:
> git clone https://github.com/ph1984/iteam-codes-sdk
> ```
> Depois do `pull`, **releia este AGENTS.md** (ele também é atualizado) e confira o `iteam.py`/`iteam.js`.
> O SDK é mantido **retrocompatível** — as mudanças são **aditivas/opt-in**, então Codes existentes seguem
> funcionando e atualizar é seguro; qualquer quebra intencional vem anotada aqui em destaque. Na dúvida,
> atualize: o custo é zero e evita usar uma API que já mudou.

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
- `user/can/require_role/menu` — **RBAC** (quem está logado + o que cada papel pode ver/chamar). Opt-in. Veja **🔐 Acesso por papel (RBAC)** no fim.

## ⚡ Regras que evitam dor de cabeça (leia antes de mexer com dados)

### A) Recurso inativo? PARE e guie o usuário a ativar
Antes de usar **Data Store (ClickHouse)** ou **banco (Postgres)**, cheque `resources()`. Se o recurso que
você precisa **não estiver ativo** (não aparece na lista), **NÃO invente outro caminho** — explique ao usuário,
em português, que ele precisa ativar (é 1 clique, sem custo de configuração):

> "Pra guardar/consultar dados eu preciso do **Data Store** ativo. No iTeam, abra seu projeto → aba **Codes** →
> card **Data Store (ClickHouse)** → botão **Ativar recurso**. Depois disso ele fica **read+write isolado** do seu
> projeto e eu consigo criar tabelas e gravar. Me avisa quando ativar que eu sigo."

O mesmo vale pro **Postgres** (card "Banco de dados"). Só prossiga com a gravação **depois** de o recurso aparecer
em `resources()`. (Sem Data Store ativo, `datastore.query` só lê o compartilhado — não grava.)

### B) SEMPRE pagine — nunca retorne/consulte "tudo" (senão estoura)
- Em **endpoints de lista** (service), aceite `?limit=` e `?offset=` (ou cursor). **Default `limit=50`, teto `200`.**
  Devolva `{ items, total, limit, offset }`. Nunca faça `SELECT *` sem `LIMIT`.
- Em **queries** no Data Store/DB, sempre ponha `LIMIT` (e `WHERE`/período). Pra somar/contar, **agregue no SQL**
  (`count()`, `sum()`, `group by`) em vez de trazer linhas e somar no código.
- Em **telas (artefato)** que listam, busque paginado (`?limit=&offset=`) e carregue mais sob demanda.
- Documente os parâmetros no `inputSchema` de cada endpoint — assim o "try it" da tela vira **campos** (o leigo
  não digita JSON) e os agentes sabem chamar.
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

## 🔐 Acesso por papel (RBAC) — quem vê/pode o quê (opt-in)
Um `service`/`app` protegido (`public:false`, o padrão) só é acessível por **membros do projeto**. Às
vezes isso não basta: dentro do mesmo app você quer que **só o gestor** veja a tela de configuração, ou
que **só admin/manager** possa apagar. O iTeam já sabe **quem é** cada pessoa e **qual o papel dela** —
você só decide o que cada papel pode. **É tudo opt-in: se você não fizer nada, todo membro vê tudo (o
comportamento de hoje — não quebra nada).**

### Como funciona (você não faz login, não vê senha)
Quando alguém acessa seu deploy protegido, o **gateway do iTeam valida o login** e injeta 3 headers
**confiáveis** na requisição que chega ao seu container (o navegador **não** consegue forjá-los — quem
fala com o container é só o gateway, que sobrescreve esses headers):

| Header | O que é | Valores possíveis |
|---|---|---|
| `X-Iteam-User` | id do usuário logado | (id) |
| `X-Iteam-Role` | papel dele **na empresa** | `owner`, `admin`, `manager`, `member`, `viewer` |
| `X-Iteam-Project-Role` | papel dele **neste projeto** | `owner` (criou o projeto), `admin` (é owner/admin da empresa), `editor` ou `viewer` (foi compartilhado nesse nível) |

`owner`/`admin` da empresa e o **dono do projeto** (`owner`) **sempre podem tudo**. Em `job`/local/rota
pública não há login → os headers vêm vazios (o SDK trata como anônimo). O `can()` casa o papel contra
**os dois** headers (empresa e projeto), então tanto `can(me, "manager")` (papel de empresa) quanto
`can(me, "editor")` (papel de projeto compartilhado) funcionam.

### O SDK faz o trabalho pesado (Python **e** Node)
```python
from iteam import user, can, require_role, menu
me = user(request.headers)          # {"userId","role","projectRole"}  (Flask/FastAPI)
can(me, "admin", "manager")         # → bool. DEFAULT-DENY. owner/admin/dono sempre True.
require_role(request.headers, "admin")   # guarda de ROTA: None (segue) ou um 403 pronto
menu(telas, me)                     # filtra a lista de telas pelo papel (pro app montar o menu)
```
```js
const { user, can, require_role, menu } = require('./iteam');   // mesma API em Node
const me = user(req);                       // passe o `req` do Node/Express OU os headers
if (!can(me, 'admin')) { /* ... */ }
```

### Regra de ouro (NÃO viole): esconder a tela é só UX
Esconder um item de menu **não protege o dado**. Uma tela censurada **exige** que a rota/dados por
trás também sejam censurados no `service` — senão a pessoa acessa a URL/API na mão. **Sempre** proteja
a rota no backend com `require_role()`; o `menu()` no front é só pra não mostrar o que a pessoa não usa.

### 1) `service` — proteja a ROTA (autoritativo)
```js
// só admin/editor apagam; qualquer outro papel toma 403 (não estoura, você devolve a resposta)
if (m && req.method === 'DELETE') {
  const deny = require_role(req, 'admin', 'editor');
  if (deny) return send(res, deny.status, deny.body);   // { error, message, need, have }
  // ... apaga ...
}
```

### 2) `app` (telas React) — o front descobre o papel via `/whoami`
O front **estático não enxerga os headers** — quem os recebe é o container. Então o app pergunta ao seu
`service` companheiro "quem sou eu?" e monta o menu conforme o papel. No `service`, exponha:
```js
if (p === '/whoami') return send(res, 200, user(req));   // { userId, role, projectRole }
```
No React, busque isso e filtre o menu (peça ao `service`, não confie só no cliente):
```jsx
const [me, setMe] = useState(null);
useEffect(() => { fetch('/s/<projectId>/<slug-da-api>/whoami').then(r => r.json()).then(setMe); }, []);
const telas = [
  { title: 'Início', path: '/' },
  { title: 'Vendas', path: '/vendas', roles: ['admin', 'editor'] },
  { title: 'Configuração', path: '/config', roles: ['admin'] },
].filter(t => !t.roles || (me && [me.role, me.projectRole].some(r => t.roles.includes(r))) || me?.role === 'owner' || me?.role === 'admin');
```

### Quais papéis usar
Os papéis vêm do iTeam (você não cria login). Na prática, o **papel de PROJETO** (`X-Iteam-Project-Role`)
que chega é um destes: `owner` (quem criou o projeto), `admin` (owner/admin da empresa), `editor` ou
`viewer` (quem foi compartilhado nesse nível na tela do projeto). Além disso existe o **papel de EMPRESA**
(`X-Iteam-Role`): `owner`/`admin`/`manager`/`member`/`viewer`. O `can()` casa contra os dois, então prefira
declarar em cima de `owner/admin/editor/viewer` (papel de projeto) e use os de empresa (`manager`/`member`)
só se fizer sentido pro caso. Se o usuário descrever papéis próprios ("caixa", "supervisor"), mapeie pro
mais próximo — NÃO invente um esquema paralelo. Pergunte SEMPRE, em português, **quem deve ver/poder cada
tela e cada rota** antes de assumir que é tudo liberado.
