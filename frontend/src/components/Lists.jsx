import { useEffect, useState } from 'react'
import { api } from '../api.js'

function useList(path) {
  const [items, setItems] = useState([])
  useEffect(() => { api(path).then(setItems).catch(() => {}) }, [path])
  return items
}

export function Audit() {
  return (
    <div className="list">
      {useList('/audit').map((x) => (
        <div className="card" key={x.id}>
          <b>{x.actor}: {x.action}</b><code>{x.detail}</code>
          <small>{new Date(x.ts * 1000).toLocaleString()} — {x.outcome}</small>
        </div>
      ))}
    </div>
  )
}

export function Tools() {
  return (
    <div className="list">
      {useList('/tools').map((x) => (
        <div className="card" key={x.name}><b>{x.name}</b> <small className={'risk ' + x.risk}>{x.risk}</small><div className="muted">{x.description}</div></div>
      ))}
    </div>
  )
}
