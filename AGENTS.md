# Guia do Agente — iTeam Codes

Você (IA em Claude Code / Cursor / VS Code / Copilot) está ajudando a criar e manter
**Codes do iTeam**: scripts Python/Node que rodam num sandbox efêmero isolado, com
recursos escopados por projeto e agendamento. Leia este guia inteiro antes de agir.

## O que é um Code
- Um entrypoint (`main.py` ou `main.js`) + arquivos extras opcionais.
- Roda isolado (cria→roda→destrói). Sem estado entre runs, EXCETO o que você salvar no `kv`.
- Recebe um token de projeto assinado via ambiente — **você nunca escreve credenciais no código**.

## SDK (importe e use)
```python
from iteam import kv, datastore, iteam_call, iteam_query, iteam_tools, result
```
- `kv.set/get/delete/incr/keys` — cache/estado chave-valor **isolado por projeto** (Redis no servidor).
- `datastore.query(sql)` — **Data Store** analítico (ClickHouse), **somente leitura**.
- `iteam_call(tool, **args)` / `iteam_query(...)` — tools do agente/projeto (MCP, HTTP, APIs aprendidas).
- `iteam_tools("filtro")` — descobre as tools disponíveis (nomes + schema).
- `result({...})` — **SEMPRE** retorne o resultado estruturado com isto (vira `run.result`). NÃO confie em "última linha".

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
          "schedule":"0 6 * * *", "env":{"X":"y"}}'
   # → { "codeId": "...", "slug": "...", "name": "..." }  ← guarde codeId/slug p/ atualizar
   ```
   `$ITEAM_API` = https://api.iteam.works (prod) ou https://stg.api.iteam.works (hom).
5. Rodar: `POST $ITEAM_API/api/project/codes/CODE_ID/run` → `{ runId }`.
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
