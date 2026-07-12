// SERVICE de exemplo: API de tarefas. Escute SEMPRE em process.env.PORT.
const http = require('http');
const PORT = process.env.PORT || 3000;
let tarefas = [{ id: 1, titulo: 'Configurar farm', feito: true }, { id: 2, titulo: 'Publicar API', feito: false }];

function send(res, code, obj) { res.writeHead(code, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(obj)); }

const server = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://x');
  const p = url.pathname;
  if (p === '/' || p === '/health') return send(res, 200, { ok: true, service: 'Tarefas API' });
  if (p === '/tarefas' && req.method === 'GET') return send(res, 200, { tarefas });
  if (p === '/tarefas' && req.method === 'POST') {
    let body = ''; req.on('data', c => body += c);
    req.on('end', () => {
      try { const t = JSON.parse(body || '{}'); const nova = { id: tarefas.length + 1, titulo: t.titulo || 'sem titulo', feito: false }; tarefas.push(nova); send(res, 201, nova); }
      catch { send(res, 400, { erro: 'json invalido' }); }
    });
    return;
  }
  const m = p.match(/^\/tarefas\/(\d+)$/);
  if (m) { const t = tarefas.find(x => x.id == m[1]); return t ? send(res, 200, t) : send(res, 404, { erro: 'nao encontrada' }); }
  send(res, 404, { erro: 'rota nao encontrada' });
});
server.listen(PORT, () => console.log('Tarefas API on ' + PORT));
module.exports = server;
