import { useEffect, useState } from 'react'
import { api } from '../api.js'

export default function Inbox({ onChange }) {
  const [items, setItems] = useState([])
  const load = () => api('/notifications').then(setItems).catch(() => {})
  useEffect(() => { load() }, [])
  async function readAll() { await api('/notifications/read', { method: 'POST' }); load(); onChange?.() }
  return (
    <div className="list">
      <button onClick={readAll}>Mark all read</button>
      {items.length === 0 && <p className="muted">No notifications yet. Scheduled briefings and email rules show up here.</p>}
      {items.map((n) => (
        <div className={'card' + (n.read ? '' : ' unread')} key={n.id}>
          <b>{n.title}</b><div className="pre">{n.body}</div>
          <small>{new Date(n.ts * 1000).toLocaleString()}</small>
        </div>
      ))}
    </div>
  )
}
