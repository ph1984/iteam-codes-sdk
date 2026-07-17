# Instruções para a IA

Este projeto usa o **iTeam Codes SDK**.

**ANTES DE CODAR, ATUALIZE O SDK:** `git pull` (ou clone https://github.com/ph1984/iteam-codes-sdk).
O SDK evolui e ganha recursos novos (ex.: RBAC user/can/require_role/menu); uma cópia antiga não os
tem. As mudanças são aditivas/retrocompatíveis, então atualizar é seguro. Depois, releia `AGENTS.md`.

Leia `AGENTS.md` — ele explica como criar, testar e fazer deploy de Codes (SDK kv/datastore,
result(), idempotência por slug, .env nunca no Git, agendamento cron, RBAC por papel).
