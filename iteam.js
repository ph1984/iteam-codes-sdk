/**
 * iTeam Codes SDK (Node) — DUAL-MODE (roda igual local na sua IDE e no sandbox/farm do iTeam).
 *
 * Local (Claude Code / Cursor / VS Code), pra TESTAR sem deploy e sem segredo:
 *   export ITEAM_API_URL=https://api.iteam.works        // (ou https://stg.api.iteam.works)
 *   export ITEAM_PROJECT_TOKEN=pct_...                  // token do projeto (aba Codes) — no .env, NUNCA no git
 *   node server.js
 * No sandbox/farm (deploy) o iTeam injeta o acesso automaticamente — você não muda nada.
 *
 * Você NUNCA coloca credencial de recurso/agente: o backend resolve pelo token do projeto e
 * executa server-side (secrets ficam no cofre). Uso:
 *   const { kv, db, datastore, iteam_call, iteam_query, resources, agent_tools, get_input, result,
 *           user, can, require_role, menu } = require('./iteam');
 */
const http = require('http');
const https = require('https');
const { URL } = require('url');

// Versão deste SDK (YYYY.MM.DD, comparável lexicograficamente). check_update() compara com o servidor.
const SDK_VERSION = '2026.07.17';
function version() { return SDK_VERSION; }

/** Avisa se o SDK local está ATRÁS do publicado. RODE ANTES DE CODAR (na IDE):
 *    node -e "require('./iteam').check_update()"
 * Se disser DESATUALIZADO, dê `git pull` no iteam-codes-sdk e releia o AGENTS.md. */
function check_update() {
  const api = process.env.ITEAM_API_URL;
  if (!api) {
    const msg = 'check_update: defina ITEAM_API_URL (ex.: https://api.iteam.works) para comparar.';
    console.log(msg); return Promise.resolve({ local: SDK_VERSION, latest: null, upToDate: null, message: msg });
  }
  const u = new URL(api.replace(/\/$/, '') + '/api/project/codes/sdk-version');
  const lib = u.protocol === 'https:' ? https : http;
  return new Promise((resolve) => {
    const req = lib.get(u, (r) => {
      let c = ''; r.on('data', d => c += d); r.on('end', () => {
        try {
          const info = JSON.parse(c); const latest = String(info.version || '');
          const up = !latest || SDK_VERSION >= latest;
          const msg = up ? `[OK] SDK atualizado (local ${SDK_VERSION})`
            : `[!] SDK DESATUALIZADO: local ${SDK_VERSION} < publicado ${latest}. Rode \`git pull\` em ${info.repo || 'iteam-codes-sdk'} e releia o AGENTS.md antes de codar.`;
          console.log(msg);
          resolve({ local: SDK_VERSION, latest: latest || null, upToDate: up, message: msg });
        } catch (e) { const m = 'check_update: resposta invalida. Na duvida, de git pull no SDK.'; console.log(m); resolve({ local: SDK_VERSION, latest: null, upToDate: null, message: m }); }
      });
    });
    req.on('error', (e) => { const m = `check_update: não consegui checar (${e.message}). Na dúvida, dê git pull no SDK.`; console.log(m); resolve({ local: SDK_VERSION, latest: null, upToDate: null, message: m }); });
  });
}

function _endpoint() {
  const callTok = process.env.ITEAM_CALL_TOKEN;
  const internal = process.env.ITEAM_INTERNAL_URL;
  if (callTok && internal) {           // dentro do sandbox
    return { url: internal.replace(/\/$/, '') + '/internal/code-agent/tool', headers: { 'X-Internal-Token': callTok } };
  }
  const api = process.env.ITEAM_API_URL;
  const pct = process.env.ITEAM_PROJECT_TOKEN;
  if (api && pct) {                    // local (IDE)
    return { url: api.replace(/\/$/, '') + '/api/project/codes/call', headers: { Authorization: 'Bearer ' + pct } };
  }
  throw new Error('Configure ITEAM_API_URL + ITEAM_PROJECT_TOKEN (local) ou rode no sandbox do iTeam.');
}

function iteam_call(tool, args = {}) {
  const { url, headers } = _endpoint();
  const u = new URL(url);
  const body = JSON.stringify({ tool, args });
  const lib = u.protocol === 'https:' ? https : http;
  return new Promise((resolve, reject) => {
    const req = lib.request(u, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...headers, 'Content-Length': Buffer.byteLength(body) },
    }, (r) => {
      let c = '';
      r.on('data', (d) => { c += d; });
      r.on('end', () => {
        let j; try { j = JSON.parse(c); } catch { j = c; }
        if (j && typeof j === 'object' && j.error) return reject(new Error(j.error));
        resolve(j && typeof j === 'object' ? j.result : j);
      });
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

async function iteam_query(tool, args = {}) {
  const r = await iteam_call(tool, args);
  if (r && typeof r === 'object') {
    for (const k of ['rows', 'data', 'records', 'items', 'result']) if (Array.isArray(r[k])) return r[k];
  }
  return r;
}

const kv = {
  get: (key) => iteam_call('kv_get', { key }),
  set: (key, value, ttl) => iteam_call('kv_set', { key, value, ttl }),
  delete: (key) => iteam_call('kv_del', { key }),
  incr: (key, by = 1) => iteam_call('kv_incr', { key, by }),
  keys: (pattern = '*') => iteam_call('kv_keys', { pattern }),
};
const datastore = {
  query: (sql) => iteam_query('datastore_query', { sql }),
  tables: () => iteam_call('datastore_tables'),
  columns: (table) => iteam_call('datastore_columns', { table }),
};
const db = {
  query: (sql) => iteam_query('db_query', { sql }),
  execute: (sql) => iteam_call('db_execute', { sql }),
  tables: () => iteam_call('db_tables'),
  columns: (table) => iteam_call('db_columns', { table }),
};
function resources() { return iteam_call('resources_list'); }
async function agent_tools(contains) {
  const cat = await iteam_call('agent_tools');
  let tools = (cat && cat.tools) || cat || [];
  if (contains) {
    const c = String(contains).toLowerCase();
    tools = tools.filter((t) => ((t.name || '') + (t.description || '')).toLowerCase().includes(c));
  }
  return tools;
}
function get_input() { try { return JSON.parse(process.env.ITEAM_INPUT || '{}'); } catch { return {}; } }
function result(value) { console.log('__ITEAM_RESULT__' + JSON.stringify(value)); }

// ─────────────────────────────────────────────────────────────────────────────
// RBAC (opt-in) — QUEM está logado e o que PODE ver/chamar.
//
// Para services/apps PROTEGIDOS (public=false), o gateway do iTeam valida o login e
// injeta 3 headers CONFIÁVEIS na requisição que chega ao seu container (o browser não
// consegue forjá-los — quem fala com o container é só o gateway, que os sobrescreve):
//   X-Iteam-User          → id do usuário logado
//   X-Iteam-Role          → papel dele NA EMPRESA  (owner/admin/manager/member/viewer)
//   X-Iteam-Project-Role  → papel dele NESTE PROJETO (owner/admin/manager/member/viewer)
// Em job/local/rota pública não há login → tudo vem vazio (trate como anônimo).
// owner/admin da EMPRESA e o dono do PROJETO (owner) SEMPRE podem tudo.
//
// Tudo opt-in: sem chamar nada disto, todo membro do projeto vê tudo (nada quebra).
// Regra de ouro: esconder a tela é só UX; proteja SEMPRE a rota/dados com require_role().
const _SUPER_ROLES = ['owner', 'admin'];

function _hget(reqOrHeaders, name) {
  if (!reqOrHeaders) return '';
  const lname = name.toLowerCase();
  const h = reqOrHeaders.headers ? reqOrHeaders.headers : reqOrHeaders; // aceita `req` OU `headers`
  if (!h) return '';
  if (typeof h.get === 'function') { const v = h.get(name) || h.get(lname); if (v) return String(v); }
  for (const k of Object.keys(h)) { if (k.toLowerCase() === lname && h[k] != null) return String(h[k]); }
  return '';
}

function user(reqOrHeaders) {
  // Passe o `req` do Node/Express OU um objeto de headers.
  return {
    userId: _hget(reqOrHeaders, 'X-Iteam-User'),
    role: _hget(reqOrHeaders, 'X-Iteam-Role'),
    projectRole: _hget(reqOrHeaders, 'X-Iteam-Project-Role'),
  };
}

function _who(who) {
  return (who && typeof who === 'object' && 'projectRole' in who) ? who : user(who);
}

function can(who, ...roles) {
  const u = _who(who);
  if (_SUPER_ROLES.includes(u.role) || _SUPER_ROLES.includes(u.projectRole)) return true;
  const allowed = new Set(roles.filter(Boolean).map((r) => String(r).trim().toLowerCase()));
  if (!allowed.size) return !!u.userId;
  return [u.role, u.projectRole].some((x) => allowed.has(String(x || '').toLowerCase()));
}

function require_role(who, ...roles) {
  if (can(who, ...roles)) return null;
  const u = _who(who);
  return {
    __forbidden__: true,
    status: 403,
    body: {
      error: 'forbidden',
      message: 'Você não tem permissão para acessar isto.',
      need: roles.map(String),
      have: u.projectRole || u.role || null,
    },
  };
}
const requireRole = require_role;

function menu(items, who) {
  return (items || []).filter((it) => {
    const roles = (it && it.roles) || [];
    return !roles.length || can(who, ...roles);
  });
}

module.exports = {
  iteam_call, iteam_query, kv, datastore, db, resources, agent_tools, get_input, result,
  user, can, require_role, requireRole, menu,
  SDK_VERSION, version, check_update,
};
