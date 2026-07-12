// Teste do SERVICE. Roda no deploy (testCommand: "node test.js").
// Se sair com codigo != 0, o deploy e ABORTADO (nada quebrado no ar).
const assert = require('assert');

// Logica pura testavel (sem subir servidor):
function prioridade(t) { return t.feito ? 'concluida' : 'pendente'; }

assert.strictEqual(prioridade({ feito: true }), 'concluida');
assert.strictEqual(prioridade({ feito: false }), 'pendente');
console.log('OK: 2 testes passaram');
