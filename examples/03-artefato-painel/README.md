# Exemplo 3 — ARTEFATO: telas (React) que consomem a sua API

**O que é:** um ou vários **telas** (front-end **React + Vite**, com o **design system do iTeam**)
num único deploy. Fica no ar em `svc.iteam.works/a/...`, **protegido por login iTeam por padrão**.

**O que este faz:** um painel com 3 telas (Home, Tarefas, Sobre). A tela **Tarefas** consome a
**API do exemplo 2** (`tarefas-api`) do mesmo projeto — lista e cria tarefas.

## Como um leigo pede isso ao Claude
> "Crie um **painel** bonito com as telas Home, Tarefas e Sobre. Na Tarefas, liste e crie tarefas
> usando a minha API `tarefas-api`."

## Estrutura
```
package.json      vite.config.js   index.html
src/main.jsx      src/App.jsx      src/theme.css   ← design system iTeam (troque as cores aqui)
serve.js          Dockerfile       ← build Vite + serve estatico
```

## Como conecta na API (mesmo domínio, sem CORS)
A tela descobre o `projectId` pela própria URL e chama a API irmã:
```js
const pid = (location.pathname.match(/^\/a\/([^/]+)\//) || [])[1];
fetch(`/s/${pid}/tarefas-api/tarefas`)   // → sua API, mesmo domínio svc.iteam.works
```

## Como publicar (a IA faz por você)
```bash
curl -X POST $ITEAM_API/api/project/codes -H "Authorization: Bearer $ITEAM_PROJECT_TOKEN" \
  -H "Content-Type: application/json" -d '{
    "name":"Painel","slug":"painel","language":"node","kind":"app",
    "code":"// via Dockerfile", "files":[ ...todos os arquivos... ],
    "screens":[{"title":"Home","path":"/"},{"title":"Tarefas","path":"/tarefas"},{"title":"Sobre","path":"/sobre"}]
  }'
curl -X POST $ITEAM_API/api/project/codes/<CODE_ID>/deploy -H "Authorization: Bearer $ITEAM_PROJECT_TOKEN"
# → https://svc.iteam.works/a/<projectId>/painel/
```

## Pontos-chave
- **`vite.config.js` com `base:"./"`** (assets relativos — a tela roda numa sub-rota `/a/<id>/<slug>/`).
- **Design system** em `src/theme.css` (variáveis CSS) — mude cores/tipografia à vontade.
- **Protegido por padrão**: só membros do projeto abrem (senão vão pro login). Marque `public:true` p/ abrir a todos.
- O **Dockerfile** faz `vite build` e serve o `dist/` — a farm builda pra você.
