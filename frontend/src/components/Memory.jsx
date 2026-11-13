import { useEffect, useState } from 'react'
import { api } from '../api.js'

export default function Memory() {
  const [items, setItems] = useState([])
  const [q, setQ] = useState('')
  const [draft, setDraft] = useState('')
  const [edit, setEdit] = useState(null)   // {id, text}
  const load = () => api('/memories' + (q ? '?q=' + encodeURIComponent(q) : '')).then(setItems).catch(() => {})
  useEffect(() => { load() }, [q])

  async function add(e) { e.preventDefault(); if (!draft.trim()) return; await api('/memories', { method: 'POST', body: { text: draft } }); setDraft(''); load() }
  async function save() { await api('/memories/' + edit.id, { method: 'PUT', body: { text: edit.text } }); setEdit(null); load() }

  return (
    <div className="list">
      <p className="muted">What Zevon remembers about you. Edit or delete anything; it is used in future chats.</p>
      <input placeholder="Search memories…" value={q} onChange={(e) => setQ(e.target.value)} />
      <form className="card form" onSubmit={add}>
        <input placeholder="Add a memory, e.g. I prefer short answers" value={draft} onChange={(e) => setDraft(e.target.value)} />
        <button>Add</button>
      </form>
      {items.length === 0 && <p className="muted">No memories yet.</p>}
      {items.map((m) => (
        <div className="card" key={m.id}>
          {edit?.id === m.id ? (
            <>
              <textarea value={edit.text} onChange={(e) => setEdit({ ...edit, text: e.target.value })} />
              <div><button onClick={save}>Save</button> <button onClick={() => setEdit(null)}>Cancel</button></div>
            </>
          ) : (
            <>
              <div className="pre">{m.text}</div>
              <small>{new Date(m.ts * 1000).toLocaleString()}</small>
              <div>
                <button onClick={() => setEdit({ id: m.id, text: m.text })}>Edit</button>{' '}
                <button className="danger" onClick={async () => { await api('/memories/' + m.id, { method: 'DELETE' }); load() }}>Delete</button>
              </div>
            </>
          )}
        </div>
      ))}
    </div>
  )
}
