# Exemplo 2 — SERVICE: uma API HTTP que fica no ar

**O que é:** um backend **persistente** (fica no ar 24/7) com **um ou vários endpoints**
(GET/POST/PUT/DELETE), atrás de um domínio seguro. Escute em `process.env.PORT`.

**O que este faz:** uma API de tarefas com `GET /health`, `GET /tarefas`, `POST /tarefas`,
`GET /tarefas/:id`. Tem **teste** (`test.js`) que roda no deploy — se falhar, **não publica**.

## Como um leigo pede isso ao Claude
> "Crie uma **API** de tarefas: listar, criar e buscar por id. Documente os endpoints."

## Como publicar (a IA faz por você)
```bash
curl -X POST $ITEAM_API/api/project/codes -H "Authorization: Bearer $ITEAM_PROJECT_TOKEN" \
  -H "Content-Type: application/json" -d '{
    "name":"Tarefas API","slug":"tarefas-api","language":"node","kind":"service",
    "public": false,                          // padrao: protegido (so membros do projeto)
    "code":"<conteudo de server.js>",
    "files":[{"path":"test.js","content":"<conteudo de test.js>"}],
    "endpoints":[
      {"method":"GET","path":"/health","summary":"status"},
      {"method":"GET","path":"/tarefas","summary":"lista (paginada)",
        "inputSchema":{"type":"object","properties":{"limit":{"type":"number"},"offset":{"type":"number"}}}},
      {"method":"POST","path":"/tarefas","summary":"cria",
        "inputSchema":{"type":"object","properties":{"titulo":{"type":"string"}},"required":["titulo"]}},
      {"method":"GET","path":"/tarefas/:id","summary":"por id"}
    ],
    "testCommand":"node test.js"
  }'

# publica (build + testes + sobe container) → devolve a URL
curl -X POST $ITEAM_API/api/project/codes/<CODE_ID>/deploy -H "Authorization: Bearer $ITEAM_PROJECT_TOKEN"
# → https://svc.iteam.works/s/<projectId>/tarefas-api/
```

## Pontos-chave
- **Escute em `process.env.PORT`** (o iTeam define a porta).
- `endpoints` alimenta o **viewer estilo Swagger** (com "try it") e faz os **agentes** saberem chamar.
- `public:false` (padrão) = protegido; quem não é do projeto recebe login. Externos usam header `X-Iteam-Token`.
- `testCommand` roda **antes** de subir — deploy aborta se os testes falharem.
- Dá pra ligar/desligar endpoints individuais depois, na aba Codes.
