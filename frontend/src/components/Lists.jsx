import { useEffect, useState } from 'react'
import { api } from '../api.js'

export function Audit() {
  const [items, setItems] = useState([])
  useEffect(() => { api('/audit').then(setItems).catch(() => {}) }, [])
  return (
    <div className="list">
      {items.map((x) => (
        <div className="card" key={x.id}>
          <b>{x.actor}: {x.action}</b><code>{x.detail}</code>
          <small>{new Date(x.ts * 1000).toLocaleString()} — {x.outcome}</small>
        </div>
      ))}
    </div>
  )
}
