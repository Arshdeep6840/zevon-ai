import { useEffect, useState } from 'react'
import { api } from '../api.js'

const HINT = {
  permanent: 'A rule that always applies, e.g. "Never send an email without my approval."',
  scheduled: 'Runs on a cron schedule (e.g. 0 8 * * *), e.g. "Summarize my unread emails and calendar."',
  conditional: 'Runs when a new email arrives, e.g. "If it is from my boss, summarize it and tell me what to reply."',
}

export default function Rules() {
  const [items, setItems] = useState([])
  const [f, setF] = useState({ name: '', kind: 'permanent', schedule: '0 8 * * *', text: '' })
  const [err, setErr] = useState('')
  const load = () => api('/instructions').then(setItems).catch(() => {})
  useEffect(() => { load() }, [])
  async function add(e) {
    e.preventDefault(); setErr('')
    const schedule = f.kind === 'scheduled' ? f.schedule : f.kind === 'conditional' ? 'email:new' : ''
    try { await api('/instructions', { method: 'POST', body: { name: f.name, kind: f.kind, text: f.text, schedule } }); setF({ ...f, name: '', text: '' }); load() }
    catch (x) { setErr(x.message) }
  }
  return (
    <div className="list">
      <form className="card form" onSubmit={add}>
        <input placeholder="Name" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} required />
        <select value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value })}>
          <option value="permanent">Permanent rule</option><option value="scheduled">Scheduled task</option><option value="conditional">When a new email arrives</option>
        </select>
        {f.kind === 'scheduled' && <input placeholder="cron, e.g. 0 8 * * *" value={f.schedule} onChange={(e) => setF({ ...f, schedule: e.target.value })} />}
        <textarea placeholder="Instruction" value={f.text} onChange={(e) => setF({ ...f, text: e.target.value })} required />
        <small className="muted">{HINT[f.kind]}</small>
        {err && <div className="banner">{err}</div>}
        <button>Add</button>
      </form>
      {items.map((i) => (
        <div className="card" key={i.id}>
          <b>{i.name}</b> <small>{i.kind}{i.schedule ? ` · ${i.schedule}` : ''}</small>
          <div className="pre">{i.text}</div>
          <button className="danger" onClick={async () => { await api('/instructions/' + i.id, { method: 'DELETE' }); load() }}>Delete</button>
        </div>
      ))}
    </div>
  )
}
