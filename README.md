# iTeam Codes SDK

SDK oficial dos **Codes** do iTeam — scripts Python/Node que você escreve na sua
IDE favorita (Claude Code, Cursor, VS Code, …), versiona no Git e faz **deploy via
API** para rodar em sandbox efêmero isolado, com **agendamento** e **recursos
escopados por projeto** (cache/KV, Data Store) — **sem nunca colocar credenciais no código**.

## Como usar na sua IDE (Claude Code / Cursor / VS Code)

1. Peça para a IA clonar este SDK e ler a documentação:
   > "Clone https://github.com/ph1984/iteam-codes-sdk e crie um Code que
   >  soma os pedidos de ontem no Data Store e salva o total no kv."
2. Escreva seu script (`main.py` ou `main.js`) importando o SDK:
   ```python
   from iteam import kv, datastore
   rows = datastore.query("SELECT count() AS n FROM pedidos WHERE dia = today()-1")
   kv.set("pedidos_ontem", rows[0]["n"], ttl=86400)
   print({"ok": True, "n": rows[0]["n"]})   # última linha JSON vira o "result" do run
   ```
3. Coloque segredos SÓ no `.env` (nunca no código, nunca no Git — já está no `.gitignore`).

## Deploy (via API, com o token do projeto)

O token (`pct_...`) fica na aba **Codes** do seu projeto no iTeam. Ele identifica o
projeto — todo Code que você deploya com ele pertence a esse projeto.

```bash
# cria OU atualiza um Code (idempotente por slug — reenviar NÃO duplica)
curl -X POST https://api.iteam.works/api/project/codes \
  -H "Authorization: Bearer pct_SEU_TOKEN" -H "Content-Type: application/json" \
  -d '{ "name": "Resumo diário", "language": "python",
        "code": "from iteam import kv\nprint({\"ok\":True})",
        "schedule": "0 6 * * *" }'      # cron opcional → roda sozinho
# resposta: { "codeId": "...", "slug": "resumo-diario", "name": "..." }
# GUARDE o codeId/slug: reenviar com o mesmo slug ATUALIZA o mesmo Code.

curl -X POST https://api.iteam.works/api/project/codes/CODE_ID/run \
  -H "Authorization: Bearer pct_SEU_TOKEN"          # dispara → { runId }

curl https://api.iteam.works/api/project/codes/CODE_ID/runs/RUN_ID \
  -H "Authorization: Bearer pct_SEU_TOKEN"          # status + stdout + result
```

## Recursos escopados (sem credencial no código)

| API | O que é |
|-----|---------|
| `kv.get/set/delete/incr/keys` | Cache/estado chave-valor **isolado por projeto** (Redis no servidor) |
| `datastore.query/tables/columns` | **Data Store** analítico do projeto (ClickHouse) — **read+write** quando alocado |
| `db.query/execute/tables/columns` | **Postgres** relacional do projeto (read+write, quando alocado) |
| `resources()` | Recursos de dados alocados no projeto (kv/datastore/db) |
| `agent_tools()` | Catálogo das tools dos **agentes** do projeto (nome + schema) — some se tirar o agente |
| `iteam_call(tool, **args)` / `iteam_query(...)` | Executa uma tool de agente/projeto (MCP, HTTP, APIs aprendidas) |

O iTeam injeta um token de projeto **assinado e efêmero** no sandbox em cada run;
o SDK usa esse token. Suas credenciais nunca entram no sandbox nem no Git.

## Agendamento

Defina `schedule` (cron) no Code — ele roda sozinho, como uma tarefa agendada.
Ex.: `*/15 * * * *` (a cada 15min), `0 6 * * *` (todo dia 6h).

## Persistência de trabalho

Cada run tem um SQLite efêmero (`scratch.sqlite`, via `CODE_SCRATCH_DB`) para
trabalho local — descartado ao fim do run. Para estado durável, use `kv`.
