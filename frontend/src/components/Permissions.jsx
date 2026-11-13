import { useEffect, useState } from 'react'
import { api } from '../api.js'

const LABEL = { allow: 'Run automatically', approve: 'Ask me first', deny: 'Never allow' }

export default function Permissions() {
  const [rows, setRows] = useState([])
  const [q, setQ] = useState('')
  const [msg, setMsg] = useState('')
  const load = () => api('/policies').then(setRows).catch(() => {})
  useEffect(() => { load() }, [])

  async function set(tool, decision, risk) {
    if (decision === 'allow' && risk === 'sensitive' && !confirm(`"${tool}" can change or send things. Let Zevon run it without asking you?`)) return
    await api('/policies/' + tool, { method: 'PUT', body: { decision } })
    setMsg(`Saved: ${tool}`); load()
  }

  const shown = rows.filter((r) => r.name.includes(q.toLowerCase()))
  return (
    <div className="list">
      <p className="muted">Choose what Zevon may do on its own, what needs your approval, and what is blocked. Only you can change this; Zevon cannot.</p>
      <input placeholder="Filter tools…" value={q} onChange={(e) => setQ(e.target.value)} />
      {msg && <div className="banner ok">{msg}</div>}
      {shown.map((r) => (
        <div className="card" key={r.name}>
          <div><b>{r.name}</b> <small className={'risk ' + r.risk}>{r.risk}</small> {r.override && <small className="pill">customized</small>}</div>
          <div className="muted">{r.description}</div>
          <select value={r.effective} onChange={(e) => set(r.name, e.target.value, r.risk)}>
            {Object.entries(LABEL).map(([k, v]) => <option key={k} value={k}>{v}{k === r.default ? ' (default)' : ''}</option>)}
          </select>
          {r.override && <button onClick={() => set(r.name, 'default', r.risk)}>Reset to default</button>}
        </div>
      ))}
    </div>
  )
}
