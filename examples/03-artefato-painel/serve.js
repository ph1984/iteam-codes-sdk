// Serve o build (dist/) — escuta em process.env.PORT. SPA fallback pro index.html.
const http = require('http'), fs = require('fs'), path = require('path');
const PORT = process.env.PORT || 3000, DIR = path.join(__dirname, 'dist');
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.json': 'application/json', '.ico': 'image/x-icon' };
http.createServer((req, res) => {
  let p = decodeURIComponent(req.url.split('?')[0]); let f = path.join(DIR, p);
  if (!f.startsWith(DIR) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) f = path.join(DIR, 'index.html');
  fs.readFile(f, (e, b) => { if (e) { res.writeHead(404); return res.end('nf'); } res.writeHead(200, { 'Content-Type': MIME[path.extname(f)] || 'application/octet-stream' }); res.end(b); });
}).listen(PORT, () => console.log('painel on ' + PORT));
