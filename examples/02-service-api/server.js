// SERVICE de exemplo: API de tarefas. Escute SEMPRE em process.env.PORT.
const http = require('http');
const { user, require_role } = require('../../iteam'); // RBAC (opt-in) — quem está logado + guarda de rota
const PORT = process.env.PORT || 3000;
let tarefas = [{ id: 1, titulo: 'Configurar farm', feito: true }, { id: 2, titulo: 'Publicar API', feito: false }];

function send(res, code, obj) { res.writeHead(code, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(obj)); }

const server = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://x');
  const p = url.pathname;
  if (p === '/' || p === '/health') return send(res, 200, { ok: true, service: 'Tarefas API' });
  // /whoami: devolve QUEM está logado (o gateway injeta o papel). Um app (telas React) chama
  // isto pra montar o menu conforme o papel — o front não enxerga os headers sozinho.
  if (p === '/whoami') return send(res, 200, user(req));
  if (p === '/tarefas' && req.method === 'GET') {
    // SEMPRE pagine: limit (default 50, teto 200) + offset. Nunca devolva "tudo".
    const limit = Math.min(parseInt(url.searchParams.get('limit') || '50', 10) || 50, 200);
    const offset = parseInt(url.searchParams.get('offset') || '0', 10) || 0;
    return send(res, 200, { items: tarefas.slice(offset, offset + limit), total: tarefas.length, limit, offset });
  }
  if (p === '/tarefas' && req.method === 'POST') {
    let body = ''; req.on('data', c => body += c);
    req.on('end', () => {
      try { const t = JSON.parse(body || '{}'); const nova = { id: tarefas.length + 1, titulo: t.titulo || 'sem titulo', feito: false }; tarefas.push(nova); send(res, 201, nova); }
      catch { send(res, 400, { erro: 'json invalido' }); }
    });
    return;
  }
  const m = p.match(/^\/tarefas\/(\d+)$/);
  if (m && req.method === 'GET') { const t = tarefas.find(x => x.id == m[1]); return t ? send(res, 200, t) : send(res, 404, { erro: 'nao encontrada' }); }
  if (m && req.method === 'DELETE') {
    // ROTA PROTEGIDA: só admin/manager apagam. require_role devolve None (segue) ou o 403 pronto.
    const deny = require_role(req, 'admin', 'manager');
    if (deny) return send(res, deny.status, deny.body);
    tarefas = tarefas.filter(x => x.id != m[1]);
    return send(res, 200, { ok: true, apagada: Number(m[1]) });
  }
  send(res, 404, { erro: 'rota nao encontrada' });
});
server.listen(PORT, () => console.log('Tarefas API on ' + PORT));
module.exports = server;
