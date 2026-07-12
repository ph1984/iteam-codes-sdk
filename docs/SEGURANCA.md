# Segurança — o que é protegido e como

## Regra de ouro: **protegido por padrão**
Toda API (`service`) e tela (`app`/artefato) nasce **privada**: só quem tem **acesso ao projeto** no iTeam
(logado) consegue abrir. Você escolhe deixar público marcando `public: true`.

```
   Requisição chega no gateway (svc.iteam.works)
        │
        ├─ é público?  ──sim──►  passa direto
        │
        └─ é protegido? ──►  o gateway pergunta ao iTeam: "esse usuário é do projeto?"
                             ├─ sim → passa (200)
                             └─ não → manda pro login / bloqueia (401)
```

## Quem é "membro do projeto"
Passa quem é **owner/admin da empresa**, o **dono do projeto**, ou quem está no **compartilhamento** do projeto.
Um usuário de outra empresa **nunca** acessa.

## 3 formas de autenticar numa API/tela protegida
1. **No navegador (pessoa):** ao abrir o link, se não estiver logado, vai pro login do iTeam; depois entra e um
   cookie mantém a sessão.
2. **De fora / sistema (programático):** manda o **token do usuário iTeam** no header `X-Iteam-Token`:
   ```bash
   curl https://svc.iteam.works/s/<projeto>/minha-api/ -H "X-Iteam-Token: <JWT_DO_USUARIO>"
   ```
3. **Agente do projeto:** chama automaticamente (o iTeam anexa a identidade do agente) — sem você fazer nada.

## O que NUNCA vai pro código nem pro git
- A **chave do projeto** (`pct_...`) fica só no `.env` (gitignored). É ela que autoriza criar/deployar.
- **Segredos dos recursos** (senha de banco, chave de MCP/API dos agentes) ficam **no cofre do servidor** —
  o seu código usa os recursos sem nunca ver a credencial.

## Camadas de isolamento
- Cada projeto tem seus dados/recursos **isolados**.
- A **Service Farm** roda seus apps em **containers separados**, em **máquinas dedicadas** (fora do core do iTeam).
- O acesso administrativo à farm (porta do agente) é **fechado por firewall** só pro backend do iTeam.

## Boas práticas
- Deixe **privado** salvo se realmente precisar público.
- Ligue **testes** (`testCommand`) — deploy só sobe se passarem.
- Desligue endpoints que não usa (toggle na aba Codes) — some do gateway.
