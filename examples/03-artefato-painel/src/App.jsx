import React, { useState, useEffect } from 'react';
import './theme.css';

// Descobre o projeto pela URL e monta a base da API irmã (mesmo domínio, sem CORS).
const pid = (location.pathname.match(/^\/a\/([^/]+)\//) || [])[1] || '';
const API = `/s/${pid}/tarefas-api`;

function Home() {
  return <div className="card"><h1>Painel <span className="badge">design system iTeam</span></h1>
    <p>Artefato React (Vite) servido pela service-farm. Consome a API <b>tarefas-api</b> do mesmo projeto.</p></div>;
}
function Sobre() {
  return <div className="card"><h1>Sobre</h1><p>Multi-tela, multi-arquivo, build Vite. Cores em <code>theme.css</code>.</p></div>;
}
function Tarefas() {
  const [t, setT] = useState([]); const [nv, setNv] = useState(''); const [err, setErr] = useState('');
  const load = () => fetch(`${API}/tarefas`).then(r => r.json()).then(d => setT(d.tarefas || [])).catch(e => setErr(String(e)));
  useEffect(() => { load(); }, []);
  const add = () => { if (!nv) return; fetch(`${API}/tarefas`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ titulo: nv }) }).then(() => { setNv(''); load(); }); };
  return <div className="card"><h1>Tarefas <span className="badge">via API</span></h1>
    {err && <p style={{ color: '#f88' }}>Erro: {err}</p>}
    <div style={{ display: 'flex', gap: '.5rem', marginBottom: '1rem' }}>
      <input value={nv} onChange={e => setNv(e.target.value)} placeholder="Nova tarefa..." />
      <button className="btn" onClick={add}>Adicionar</button>
    </div>
    {t.map(x => <div key={x.id} className={'task' + (x.feito ? ' done' : '')}><span>{x.feito ? 'OK' : '...'} {x.titulo}</span></div>)}
  </div>;
}
export default function App() {
  const [tab, setTab] = useState('home');
  return <div>
    <div className="nav"><b>Painel iTeam</b>
      {['home', 'tarefas', 'sobre'].map(k => <button key={k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>{k[0].toUpperCase() + k.slice(1)}</button>)}
    </div>
    <main>{tab === 'home' ? <Home /> : tab === 'tarefas' ? <Tarefas /> : <Sobre />}</main>
  </div>;
}
