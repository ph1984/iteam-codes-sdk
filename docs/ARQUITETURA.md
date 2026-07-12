# Arquitetura — explicada pra quem não é técnico

## Onde cada coisa mora

```
   VOCÊ na sua IDE                    iTeam (control-plane)              Service Farm (data-plane)
   (Claude/Cursor)                    api.iteam.works                    máquinas dedicadas, isoladas
   ────────────────                   ──────────────────                 ───────────────────────────
   escreve código      ── deploy ──►  recebe, valida o token   ── manda ──►  builda + roda seu código
   (com a chave pct_)                 guarda o registro do Code             em containers separados
        ▲                                     │                                   │
        │                                     │                             ┌─────┴──────────┐
        └───────────── link (URL) ────────────┘                             │ gateway (Caddy)│──► svc.iteam.works
                                                                            │  + login iTeam │     (HTTPS)
                                                                            └────────────────┘
```

- **iTeam (control-plane):** onde você já usa agentes, projetos, dados. Recebe o deploy e guarda o registro.
- **Service Farm (data-plane):** máquinas **separadas** só pra rodar o que você cria — assim seus apps **não
  sobrecarregam** o iTeam e ficam **isolados**. Dá pra adicionar mais máquinas conforme cresce.
- **Gateway (Caddy):** a "portaria" da farm. Dá o domínio bonito (`svc.iteam.works`), o **cadeado (HTTPS)** e
  o **login** (só quem é do projeto entra, se for privado).

## O que acontece num deploy de uma API/artefato

```
  1. IA envia arquivos + kind (service/app)  ─────────────►  farm-agent (na máquina da farm)
  2. farm-agent faz o BUILD (imagem do seu código)
  3. se você definiu testes: RODA OS TESTES ───► falhou? ✗ ABORTA (nada quebrado no ar)
                                              └─► passou? ✓ segue
  4. sobe o CONTAINER (seu app rodando) na rede isolada da farm
  5. registra a ROTA no gateway  ──►  https://svc.iteam.works/s|a/<projeto>/<nome>/
  6. devolve a URL pra você
```

## Como as telas conversam com a sua API
Tela (artefato) e API (service) ficam no **mesmo domínio** (`svc.iteam.works`), então a tela chama a API
**sem CORS**, por um caminho relativo:

```
  https://svc.iteam.works/a/<projeto>/painel/        (as telas)
                              │  fetch('/s/<projeto>/tarefas-api/tarefas')
                              ▼
  https://svc.iteam.works/s/<projeto>/tarefas-api/   (a API)
```

## Tipos (kind) x onde rodam
```
   JOB      → sandbox efêmero (cria → roda → destrói).  Não fica no ar.
   SERVICE  → container persistente na farm.            Fica no ar (API).
   ARTEFATO → container persistente na farm.            Fica no ar (telas).
```
