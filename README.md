# iTeam Codes SDK — construa **jobs, APIs e telas** no seu projeto iTeam

> **Você não precisa saber programar.** Abra este projeto no **Claude Code / Cursor / VS Code (Copilot)**,
> descreva em português o que você quer, e a IA escreve o código, cria e publica pra você — usando os
> recursos do seu projeto (bancos, APIs, MCPs) **sem você mexer em senha nenhuma**.

---

## 🧭 O que dá pra criar (3 tipos)

```
                          ┌───────────────────────────────────────────────┐
                          │            SEU PROJETO no iTeam                 │
                          │   (dados, APIs, MCPs, agentes — já conectados)  │
                          └───────────────────────────────────────────────┘
                                            │  (a IA usa tudo isso sem senha)
             ┌──────────────────────────────┼──────────────────────────────┐
             ▼                              ▼                               ▼
   ┌───────────────────┐         ┌────────────────────┐          ┌─────────────────────┐
   │   1) JOB           │         │   2) SERVICE (API) │          │  3) ARTEFATO (telas) │
   │  roda e termina    │         │  fica no ar 24/7   │          │  1+ telas (React)    │
   │  (relatório, ETL,  │         │  1+ endpoints HTTP │          │  bonitas, DS iTeam   │
   │  classificação…)   │         │  GET/POST/…        │          │  podem usar a API    │
   │  pode ser agendado │         │  svc.iteam.works/s │          │  svc.iteam.works/a   │
   └───────────────────┘         └────────────────────┘          └─────────────────────┘
         "todo dia 9h              "uma API de tarefas             "um painel com Home,
          gera o relatório"         com GET/POST /tarefas"          Vendas e Relatórios"
```

| Tipo | O que é | Quando usar | Exemplo |
|------|---------|-------------|---------|
| **Job** | Um código que **roda e termina** | tarefa pontual ou agendada | [examples/01-job-relatorio](examples/01-job-relatorio) |
| **Service** | Uma **API HTTP** que fica no ar | expor dados/ações via endpoints | [examples/02-service-api](examples/02-service-api) |
| **Artefato** | **Telas** (React) que ficam no ar | um painel/app pro usuário ver e usar | [examples/03-artefato-painel](examples/03-artefato-painel) |

> **Dica:** "quero um sisteminha de X" quase sempre = **um Service (a API) + um Artefato (as telas)**. Crie os dois.

---

## 🚀 Começando em 3 passos (pro leigo)

1. **Pegue seu projeto e a chave.** No iTeam, entre no seu projeto → aba **Codes** → botão **"Copiar prompt pro Claude"**.
   Ele copia um texto que já vem com o **ID do projeto e a chave (`pct_...`)**.
2. **Cole no Claude Code** (ou Cursor/VS Code) dentro desta pasta. A IA vai ler o [AGENTS.md](AGENTS.md), se conectar
   ao seu projeto e te perguntar o que você quer criar.
3. **Descreva em português.** Ex.: *"Quero uma API de tarefas e um painel bonito pra ver e criar tarefas."*
   A IA escreve, testa, publica e te devolve o **link** (https://svc.iteam.works/...).

Nada de senha no código: a chave fica só no `.env` (que **nunca** vai pro git). Tudo roda **isolado no seu projeto**.

---

## 🔒 Seguro por padrão

- **Telas e APIs nascem protegidas**: só **quem tem acesso ao projeto** (logado no iTeam) abre. Você pode marcar como
  público se quiser.
- **Acesso externo por token**: sistemas de fora chamam sua API mandando o **token do usuário** no header `X-Iteam-Token`.
- **Nada de credencial no código**: os recursos do projeto são resolvidos no servidor. A chave do projeto (`pct_`)
  fica no `.env`, fora do git.
- Detalhes: [docs/SEGURANCA.md](docs/SEGURANCA.md).

---

## 🗺️ Como funciona por dentro (sem jargão)

```
  Você (Claude/Cursor)  ──①──►  API do iTeam  ──②──►  Service Farm (máquina dedicada)
   escreve o código            recebe o deploy         builda + roda seu código
        ▲                            │                      │
        │                            │                  ┌───┴────────────┐
        └──────④ link ───────────────┘                  │  seu container │  → svc.iteam.works
                                                         └────────────────┘   (com TLS + login)
   ③ se for API, roda testes antes de subir — se falhar, NÃO publica (nada quebrado no ar).
```

1. A IA manda seu código pra API do iTeam (com a chave `pct_`).
2. A **Service Farm** (isolada, não sobrecarrega o iTeam) faz o *build* e sobe seu container.
3. Se você definiu **testes**, eles rodam antes — deploy só acontece se passarem.
4. Você recebe o **link** pronto (domínio + HTTPS + login do iTeam).

Mais diagramas e detalhes: [docs/ARQUITETURA.md](docs/ARQUITETURA.md).

---

## 📚 Índice
- **[AGENTS.md](AGENTS.md)** — o guia que a IA lê (fluxo pull→editar→deploy, SDK, contratos).
- **[examples/](examples)** — exemplos prontos dos 3 tipos, cada um com seu README explicando.
- **[docs/ARQUITETURA.md](docs/ARQUITETURA.md)** — como tudo se encaixa (diagramas).
- **[docs/SEGURANCA.md](docs/SEGURANCA.md)** — proteção, tokens, o que é público/privado.
- **[docs/FAQ.md](docs/FAQ.md)** — perguntas comuns do usuário leigo.

---

## 🧰 SDK (quando a IA escreve código Python/Node)
```python
from iteam import kv, datastore, db, agent_tools, iteam_call, iteam_query, get_input, result
```
- `kv` — cache/estado chave-valor isolado por projeto (Redis).
- `datastore.query(sql)` — Data Store analítico (ClickHouse) do projeto.
- `db` — Postgres relacional do projeto.
- `agent_tools()` / `iteam_call` / `iteam_query` — usa as ferramentas dos **agentes** do projeto (MCP/APIs) sem senha.
- `get_input()` / `result()` — entrada/saída de um **job** parametrizável.

O mesmo código roda **local** (na sua IDE, com o token do projeto) e **no deploy** (o iTeam injeta o acesso).
Você nunca manuseia segredo.
