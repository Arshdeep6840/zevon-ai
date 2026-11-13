import { useEffect, useState } from 'react'
import { api } from '../api.js'

export default function Approvals({ onChange }) {
  const [items, setItems] = useState([])
  const [msg, setMsg] = useState('')
  const load = () => api('/approvals').then(setItems).catch(() => {})
  useEffect(() => { load() }, [])
  async function act(id, kind) {
    try { const r = await api(`/approvals/${id}/${kind}`, { method: 'POST' }); setMsg(kind === 'approve' ? 'Done: ' + (r.result || '') : 'Denied.') }
    catch (e) { setMsg('Failed: ' + e.message) }
    load(); onChange?.()
  }
  return (
    <div className="list">
      {msg && <div className="banner ok">{msg}</div>}
      {items.length === 0 && <p className="muted">Nothing waiting for approval.</p>}
      {items.map((x) => (
        <div className="card" key={x.id}>
          <b>#{x.id} {x.tool}</b>
          <code>{JSON.stringify(x.args, null, 1)}</code>
          <button onClick={() => act(x.id, 'approve')}>Approve</button>{' '}
          <button className="danger" onClick={() => act(x.id, 'deny')}>Deny</button>
        </div>
      ))}
    </div>
  )
}
