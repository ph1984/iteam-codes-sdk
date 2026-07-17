// Teste do SERVICE. Roda no deploy (testCommand: "node test.js").
// Se sair com codigo != 0, o deploy e ABORTADO (nada quebrado no ar).
const assert = require('assert');

// Logica pura testavel (sem subir servidor):
function prioridade(t) { return t.feito ? 'concluida' : 'pendente'; }

assert.strictEqual(prioridade({ feito: true }), 'concluida');
assert.strictEqual(prioridade({ feito: false }), 'pendente');

// RBAC: a rota DELETE so passa pra admin/manager (default-deny pro resto).
const { can, require_role } = require('../../iteam');
const asManager = { headers: { 'x-iteam-user': 'u1', 'x-iteam-project-role': 'manager' } };
const asMember = { headers: { 'x-iteam-user': 'u2', 'x-iteam-project-role': 'member' } };
assert.strictEqual(require_role(asManager, 'admin', 'manager'), null);      // manager passa
assert.strictEqual(require_role(asMember, 'admin', 'manager').status, 403); // member barra
assert.strictEqual(can({ headers: { 'x-iteam-role': 'owner' } }, 'admin'), true); // dono da empresa sempre
console.log('OK: 5 testes passaram');
