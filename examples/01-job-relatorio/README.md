# Exemplo 1 — JOB: relatório diário

**O que é:** um código que **roda e termina**. Ideal pra tarefa pontual ou agendada
(relatório, importação, limpeza, classificação, envio de e-mail…).

**O que este faz:** lê parâmetros de entrada (`dias`), consulta o Data Store do projeto,
monta um resumo e devolve como resultado. Pode ser **agendado** (ex.: todo dia às 9h).

## Como um leigo pede isso ao Claude
> "Crie um **job** que todo dia às 9h resume os pedidos dos últimos 7 dias e salva o total no kv."

## Como publicar (a IA faz por você)
```bash
# cria/atualiza o job (kind=job, published=true → agentes podem chamar)
curl -X POST $ITEAM_API/api/project/codes -H "Authorization: Bearer $ITEAM_PROJECT_TOKEN" \
  -H "Content-Type: application/json" -d '{
    "name":"Relatorio Diario","slug":"relatorio-diario","language":"python","kind":"job",
    "published":true,
    "code":"<conteudo de main.py>",
    "inputSchema":{"type":"object","properties":{"dias":{"type":"number"}}},
    "schedule":"0 9 * * *"
  }'

# rodar agora (assíncrono → devolve runId; consulte o status depois)
curl -X POST $ITEAM_API/api/project/codes/<CODE_ID>/run -H "Authorization: Bearer $ITEAM_PROJECT_TOKEN" \
  -H "Content-Type: application/json" -d '{"input":{"dias":7}}'
```

## Pontos-chave
- `get_input()` lê os parâmetros; `result({...})` devolve a saída (aparece no histórico de runs).
- `kv` / `datastore` / `db` são do **seu projeto**, sem senha no código.
- `published:true` faz os **agentes** do projeto poderem chamar via `proj_run_code`.
