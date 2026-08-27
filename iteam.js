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

// Versão deste SDK (YYYY.MM.DD[.n] — o sufixo distingue duas releases no mesmo dia; comparável lexicograficamente). check_update() compara com o servidor.
const SDK_VERSION = '2026.08.27.1';
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
// injeta 3 headers CONFIÁVEIS na requisição que chega ao seu container. O browser não
// consegue forjá-los por DOIS motivos que só juntos bastam: (a) o container não publica
// porta no host — quem fala com ele é só o gateway; e (b) o gateway APAGA
// X-Iteam-User/Role/Project-Role vindos do cliente ANTES da auth, e só então injeta os
// valores que o backend afirmou. Em deploy PÚBLICO (public=true) não há login: os três
// chegam VAZIOS (anônimo) — nunca leia papel de header em rota pública.
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

// ─────────────────────────────────────────────────────────────────────────────
// CONCORRÊNCIA — duas pessoas mexendo no MESMO Code ao mesmo tempo.
//
// O deploy SUBSTITUI `code` e `files` inteiros. Sem controle, quem salva por último apaga o outro
// em SILÊNCIO — e como a lista de arquivos é trocada, some ARQUIVO, não linha.
//
// O SDK não se limita a avisar: ele JUNTA as duas versões. O `code_pull` guarda a BASE (o
// conteúdo exato de onde você partiu) em `.iteam-code.json`. No `code_push`, se o servidor recusar
// (409), o SDK puxa a versão nova e faz merge de 3 vias — base × sua × do servidor:
//   • só VOCÊ mexeu no arquivo    → fica o seu
//   • só O OUTRO mexeu            → fica o dele (você não o perde por não ter tocado nele)
//   • os dois, em trechos diferentes do mesmo arquivo → junta os dois
//   • os dois no MESMO trecho     → ninguém pode decidir por você: PERGUNTA (ou lança
//     ConflitoDeRevisao com o texto marcado, quando não há terminal)
// Depois reenvia sozinho com a revisão nova. `.iteam-code.json` é local (ponha no .gitignore).
const fs = require('fs');
const path = require('path');
const REV_FILE = '.iteam-code.json';

class ConflitoDeRevisao extends Error {
  constructor(detalhes, arquivosEmConflito, merge) {
    super((detalhes && detalhes.message) || 'conflito de revisão');
    this.name = 'ConflitoDeRevisao';
    this.detalhes = detalhes || {};
    this.arquivosEmConflito = arquivosEmConflito || [];
    this.merge = merge || {};
  }
}

function _codesApi(rota, method = 'GET', body) {
  const api = process.env.ITEAM_API_URL;
  const pct = process.env.ITEAM_PROJECT_TOKEN;
  if (!api || !pct) return Promise.reject(new Error('Configure ITEAM_API_URL + ITEAM_PROJECT_TOKEN (token do projeto, aba Codes).'));
  const u = new URL(api.replace(/\/$/, '') + rota);
  const lib = u.protocol === 'https:' ? https : http;
  const payload = body === undefined ? null : JSON.stringify(body);
  return new Promise((resolve, reject) => {
    const req = lib.request(u, {
      method,
      headers: {
        'Content-Type': 'application/json', Authorization: 'Bearer ' + pct,
        ...(payload ? { 'Content-Length': Buffer.byteLength(payload) } : {}),
      },
    }, (r) => {
      let c = '';
      r.on('data', (d) => { c += d; });
      r.on('end', () => {
        let j; try { j = JSON.parse(c); } catch { j = {}; }
        if (r.statusCode === 409) return reject(new ConflitoDeRevisao(j));
        if (r.statusCode >= 400) return reject(new Error(`${r.statusCode} ${rota}: ${j.message || j.error || c.slice(0, 200)}`));
        resolve(j);
      });
    });
    req.on('error', reject);
    if (payload) req.write(payload);
    req.end();
  });
}

// ── diff por linha (o Node não tem difflib) ──────────────────────────────────────────────────
// Corta prefixo/sufixo comuns e roda LCS só no miolo — em arquivo de código o miolo é pequeno.
// Miolo gigante cai num bloco único de alteração: pior caso vira uma pergunta, nunca um merge errado.
const _LIMITE_DP = 1200;

function _lcsOpcodes(a, b, oa, ob) {
  if (!a.length && !b.length) return [];
  if (!a.length) return [['insert', oa, oa, ob, ob + b.length]];
  if (!b.length) return [['delete', oa, oa + a.length, ob, ob]];
  if (a.length > _LIMITE_DP || b.length > _LIMITE_DP) {
    return [['replace', oa, oa + a.length, ob, ob + b.length]];
  }
  const n = a.length, m = b.length;
  const dp = new Uint32Array((n + 1) * (m + 1));
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      dp[i * (m + 1) + j] = a[i] === b[j]
        ? dp[(i + 1) * (m + 1) + (j + 1)] + 1
        : Math.max(dp[(i + 1) * (m + 1) + j], dp[i * (m + 1) + (j + 1)]);
    }
  }
  const ops = [];
  const empurra = (tag, i1, i2, j1, j2) => {
    if (i1 === i2 && j1 === j2) return;
    const ult = ops[ops.length - 1];
    if (ult && ult[0] === tag) { ult[2] = i2; ult[4] = j2; } else ops.push([tag, i1, i2, j1, j2]);
  };
  let i = 0, j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) { empurra('equal', oa + i, oa + i + 1, ob + j, ob + j + 1); i++; j++; }
    else if (dp[(i + 1) * (m + 1) + j] >= dp[i * (m + 1) + (j + 1)]) { empurra('delete', oa + i, oa + i + 1, ob + j, ob + j); i++; }
    else { empurra('insert', oa + i, oa + i, ob + j, ob + j + 1); j++; }
  }
  if (i < n) empurra('delete', oa + i, oa + n, ob + j, ob + j);
  if (j < m) empurra('insert', oa + n, oa + n, ob + j, ob + m);
  return ops;
}

function _opcodes(a, b) {
  let p = 0;
  while (p < a.length && p < b.length && a[p] === b[p]) p++;
  let s = 0;
  while (s < a.length - p && s < b.length - p && a[a.length - 1 - s] === b[b.length - 1 - s]) s++;
  const ops = [];
  if (p) ops.push(['equal', 0, p, 0, p]);
  ops.push(..._lcsOpcodes(a.slice(p, a.length - s), b.slice(p, b.length - s), p, p));
  if (s) ops.push(['equal', a.length - s, a.length, b.length - s, b.length]);
  return ops;
}

function _linhas(t) { return String(t == null ? '' : t).split(/(?<=\n)/).filter((x) => x !== ''); }

/** Texto do lado `seq` correspondente ao intervalo [a,z) da base. */
function _mapear(ops, seq, a, z) {
  const out = [];
  for (const [tag, i1, i2, j1, j2] of ops) {
    /* Inserção pura tem LARGURA ZERO na base (i1 === i2): ela não ocupa linha nenhuma do
       original, só marca a posição onde entrou. O recorte normal (`i2 <= a`) a descartava, e as
       linhas inseridas sumiam do merge — silenciosamente, que é o pior jeito de errar aqui.
       Por isso ela é tratada por contenção de POSIÇÃO, incluindo as bordas do bloco. */
    if (i1 === i2) {
      if (i1 >= a && i1 <= z) out.push(...seq.slice(j1, j2));
      continue;
    }
    if (i2 <= a || i1 >= z) continue;
    if (tag === 'equal') out.push(...seq.slice(j1 + (Math.max(i1, a) - i1), j1 + (Math.min(i2, z) - i1)));
    else out.push(...seq.slice(j1, j2));
  }
  return out;
}

/** Junta duas edições feitas sobre a mesma base. -> { texto, conflito } */
function merge3(base, meu, deles, rotuloMeu = 'seu', rotuloDeles = 'servidor') {
  if (meu === deles) return { texto: meu, conflito: false };
  if (base === meu) return { texto: deles, conflito: false };
  if (base === deles) return { texto: meu, conflito: false };

  const b = _linhas(base), m = _linhas(meu), d = _linhas(deles);
  const om = _opcodes(b, m), od = _opcodes(b, d);
  const alterados = [...om, ...od].filter((o) => o[0] !== 'equal').map((o) => [o[1], o[2]]).sort((x, y) => x[0] - y[0]);

  // Blocos sobrepostos viram UM: senão a alteração de um lado sairia partida ao meio.
  const blocos = [];
  for (const [i1, i2] of alterados) {
    const ult = blocos[blocos.length - 1];
    if (ult && i1 <= ult[1]) ult[1] = Math.max(ult[1], i2);
    else blocos.push([i1, i2]);
  }

  const saida = []; let conflito = false; let pos = 0;
  const igual = (x, y) => x.length === y.length && x.every((v, k) => v === y[k]);
  for (const [i1, i2] of blocos) {
    saida.push(...b.slice(pos, i1));
    const tm = _mapear(om, m, i1, i2);
    const td = _mapear(od, d, i1, i2);
    const orig = b.slice(i1, i2);
    if (igual(tm, td)) saida.push(...tm);
    else if (igual(tm, orig)) saida.push(...td);
    else if (igual(td, orig)) saida.push(...tm);
    else {
      conflito = true;
      saida.push(`<<<<<<< ${rotuloMeu}\n`, ...tm, '=======\n', ...td, `>>>>>>> ${rotuloDeles}\n`);
    }
    pos = i2;
  }
  saida.push(...b.slice(pos));
  return { texto: saida.join(''), conflito };
}

// ── estado local (base + revisão) ────────────────────────────────────────────────────────────
function _revPath(pasta) { return path.join(pasta, REV_FILE); }
function _leEstado(pasta = '.') {
  try { return JSON.parse(fs.readFileSync(_revPath(pasta), 'utf8')); } catch { return {}; }
}
function code_revision(pasta = '.') { return _leEstado(pasta).revision; }

/** Guarda revisão + BASE. Sem a base dá para saber QUE mudou, nunca O QUE cada lado mudou. */
function _gravaEstado(pasta, d) {
  try {
    const files = {};
    for (const f of (d.files || [])) if (f && f.path) files[f.path] = f.content || '';
    fs.writeFileSync(_revPath(pasta), JSON.stringify({
      codeId: d.codeId, slug: d.slug, revision: d.revision, base: { code: d.code || '', files },
    }, null, 1));
  } catch { /* sem permissao de escrita: o push segue, so sem merge automatico */ }
}

async function code_pull(codeId, pasta = '.') {
  const d = await _codesApi(`/api/project/codes/${codeId}/pull`);
  _gravaEstado(pasta, d);
  return d;
}

// ── push com detecção e resolução ────────────────────────────────────────────────────────────
function _comoDict(files) {
  const o = {};
  for (const f of (files || [])) if (f && f.path) o[f.path] = f.content || '';
  return o;
}
function _comoLista(dic) { return Object.keys(dic).sort().map((k) => ({ path: k, content: dic[k] })); }

function _perguntar(caminho, textoMarcado, interativo) {
  if (!interativo) return Promise.resolve(null);
  console.log(`\n[!] Conflito em ${caminho} — voces dois mexeram no mesmo trecho:\n`);
  console.log(textoMarcado.slice(0, 2000));
  console.log('\n  [s] fica o SEU   [o] fica o do OUTRO   [m] gravar com marcadores e revisar');
  return new Promise((resolve) => {
    process.stdout.write('  escolha [s/o/m]: ');
    const aoLer = (d) => { process.stdin.pause(); process.stdin.off('data', aoLer); resolve(String(d).trim().toLowerCase()[0] || null); };
    process.stdin.resume(); process.stdin.once('data', aoLer);
  });
}

/**
 * Grava o Code. Se alguém gravou desde o seu pull, NÃO sobrescreve: puxa a versão nova, junta as
 * duas (merge de 3 vias) e reenvia. Só para se os dois mexeram no mesmo trecho.
 * aoConflitar: 'perguntar' (padrão) | 'meu' | 'deles' | 'abortar'.
 * forcar=true pula tudo e sobrescreve — a versão do servidor SOME.
 */
async function code_push(payload, pasta = '.', { forcar = false, aoConflitar = 'perguntar', permitirRemocao = false } = {}) {
  const estado = _leEstado(pasta);
  const corpo = { ...(payload || {}) };

  /* TRAVA DA PASTA INCOMPLETA — a lista `files` SUBSTITUI a do servidor. Mandar só o arquivo que
     você mexeu não é "atualizar um arquivo": é dizer que o Code passou a ter só aquele. Some o
     resto. É o erro mais fácil de cometer aqui, e some ARQUIVO, não linha — por isso é erro
     explícito, não aviso. Para apagar de verdade, passe permitirRemocao: true. */
  const baseIni = (estado.base || {}).files || {};
  if (corpo.files !== undefined && Object.keys(baseIni).length && !permitirRemocao) {
    const enviados = _comoDict(corpo.files);
    const sumiriam = Object.keys(baseIni).filter((k) => !(k in enviados)).sort();
    if (sumiriam.length) {
      throw new Error(`code_push apagaria ${sumiriam.length} arquivo(s) que existem no Code: `
        + `${sumiriam.slice(0, 8).join(', ')}. Mande a PASTA INTEIRA (a lista \`files\` substitui a do `
        + 'servidor). Se a remoção é intencional, chame com { permitirRemocao: true }.');
    }
  }

  if (!forcar && estado.revision !== undefined) corpo.baseRevision = estado.revision;
  try {
    const r = await _codesApi('/api/project/codes', 'POST', corpo);
    _gravaEstado(pasta, { ...r, code: corpo.code, files: corpo.files });
    return r;
  } catch (e) {
    if (!(e instanceof ConflitoDeRevisao)) throw e;
    const base = estado.base;
    if (!base) {
      e.detalhes.dica = 'Rode code_pull() antes de editar — sem a base o SDK nao pode fundir.';
      throw e;
    }
    const codeId = e.detalhes.codeId || estado.codeId || corpo.codeId;
    if (!codeId) throw e;
    const atual = await _codesApi(`/api/project/codes/${codeId}/pull`);

    const meus = _comoDict(corpo.files), deles = _comoDict(atual.files), baseFiles = base.files || {};
    const interativo = aoConflitar === 'perguntar' && process.stdin.isTTY;
    const juntos = {}; const emConflito = [];
    const decidir = async (caminho, texto, meuTexto, deleTexto) => {
      const escolha = aoConflitar === 'perguntar' ? await _perguntar(caminho, texto, interativo)
        : (aoConflitar === 'meu' ? 's' : aoConflitar === 'deles' ? 'o' : null);
      if (escolha === 's') return meuTexto;
      if (escolha === 'o') return deleTexto;
      emConflito.push(caminho);
      return texto;
    };

    for (const caminho of [...new Set([...Object.keys(meus), ...Object.keys(deles), ...Object.keys(baseFiles)])].sort()) {
      const b = baseFiles[caminho], mm = meus[caminho], dd = deles[caminho];
      if (mm === undefined && dd !== undefined) {
        if (b !== undefined && dd === b) continue;      // você apagou, ele não mexeu
        if (b === undefined) { juntos[caminho] = dd; continue; }
      }
      if (dd === undefined && mm !== undefined) {
        if (b !== undefined && mm === b) continue;      // ele apagou, você não mexeu
        juntos[caminho] = mm; continue;
      }
      if (mm === undefined && dd === undefined) continue;
      const { texto, conflito } = merge3(b === undefined ? '' : b, mm, dd);
      juntos[caminho] = conflito ? await decidir(caminho, texto, mm, dd) : texto;
    }

    const rc = merge3(base.code || '', corpo.code || atual.code || '', atual.code || '');
    let codigo = rc.texto;
    if (rc.conflito) codigo = await decidir('(arquivo de entrada)', rc.texto, corpo.code || '', atual.code || '');

    if (emConflito.length) {
      e.detalhes.message = `Voces dois mexeram no MESMO trecho de: ${emConflito.join(', ')}. `
        + 'O resto ja foi juntado automaticamente. Abra o texto marcado (<<<<<<< seu / >>>>>>> servidor), '
        + 'decida os trechos e chame code_push de novo.';
      throw new ConflitoDeRevisao(e.detalhes, emConflito, { ...juntos, '(arquivo de entrada)': codigo });
    }

    corpo.files = _comoLista(juntos);
    if (corpo.code !== undefined || codigo) corpo.code = codigo;
    corpo.baseRevision = atual.revision;
    const r = await _codesApi('/api/project/codes', 'POST', corpo);
    r.merge = { juntado_com: e.detalhes.alteradoPor, arquivos: Object.keys(juntos).sort() };
    _gravaEstado(pasta, { ...r, code: corpo.code, files: corpo.files });
    console.log(`[merge] juntei suas mudancas com as de ${e.detalhes.alteradoPor || 'outra pessoa'} e gravei (revisao ${r.revision}).`);
    return r;
  }
}

module.exports = {
  iteam_call, iteam_query, kv, datastore, db, resources, agent_tools, get_input, result,
  user, can, require_role, requireRole, menu,
  code_pull, code_push, code_revision, merge3, ConflitoDeRevisao,
  SDK_VERSION, version, check_update,
};
