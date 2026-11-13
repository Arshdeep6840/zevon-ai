import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { TRIGGER_TYPES, buildSchedule, describeSchedule } from '../rules.js'

const HINT = {
  permanent: 'A rule that always applies, e.g. "Never send an email without my approval."',
  scheduled: 'Runs at fixed times (cron, e.g. 0 8 * * * = every day 8:00), e.g. "Summarize my unread emails and calendar."',
  conditional: 'Runs when something happens, e.g. "If it is from my boss, summarize it and tell me what to reply."',
}

export default function Rules() {
  const [items, setItems] = useState([])
  const [f, setF] = useState({ name: '', kind: 'permanent', cron: '0 8 * * *', text: '', trig: 'email', minutes: 15, folder: '', channel: '', every: 30, unit: 'm', from: '', to: '' })
  const [err, setErr] = useState('')
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const load = () => api('/instructions').then(setItems).catch(() => {})
  useEffect(() => { load() }, [])

  async function add(e) {
    e.preventDefault(); setErr('')
    const schedule = f.kind === 'scheduled' ? f.cron : f.kind === 'conditional' ? buildSchedule(f.trig, f) : ''
    try { await api('/instructions', { method: 'POST', body: { name: f.name, kind: f.kind, text: f.text, schedule } }); setF({ ...f, name: '', text: '' }); load() }
    catch (x) { setErr(x.message) }
  }

  return (
    <div className="list">
      <form className="card form" onSubmit={add}>
        <input placeholder="Name" value={f.name} onChange={set('name')} required />
        <select value={f.kind} onChange={set('kind')}>
          <option value="permanent">Permanent rule</option><option value="scheduled">Scheduled task</option><option value="conditional">When something happens</option>
        </select>
        {f.kind === 'scheduled' && <input placeholder="cron, e.g. 0 8 * * *" value={f.cron} onChange={set('cron')} />}
        {f.kind === 'conditional' && (
          <>
            <select value={f.trig} onChange={set('trig')}>{TRIGGER_TYPES.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}</select>
            {f.trig === 'calendar' && <input type="number" min="1" max="999" placeholder="Minutes before start" value={f.minutes} onChange={set('minutes')} />}
            {f.trig === 'file' && <input placeholder="Folder (must be an authorized folder)" value={f.folder} onChange={set('folder')} required />}
            {f.trig === 'slack' && <input placeholder="Slack channel id, e.g. C0123ABC" value={f.channel} onChange={set('channel')} required />}
            {f.trig === 'time' && (
              <div className="row">
                <span>every</span><input type="number" min="1" max="999" value={f.every} onChange={set('every')} />
                <select value={f.unit} onChange={set('unit')}><option value="m">minutes</option><option value="h">hours</option></select>
                <span>between</span><input type="time" value={f.from} onChange={set('from')} /><span>and</span><input type="time" value={f.to} onChange={set('to')} />
              </div>
            )}
          </>
        )}
        <textarea placeholder="Instruction" value={f.text} onChange={set('text')} required />
        <small className="muted">{HINT[f.kind]}</small>
        {err && <div className="banner">{err}</div>}
        <button>Add</button>
      </form>
      {items.map((i) => (
        <div className={'card' + (i.enabled ? '' : ' off')} key={i.id}>
          <div><b>{i.name}</b> <small>{i.kind}{i.kind === 'scheduled' ? ` · ${i.schedule}` : ''}{i.kind === 'conditional' ? ` · ${describeSchedule(i.schedule)}` : ''}</small></div>
          <div className="pre">{i.text}</div>
          <div>
            <button className={i.enabled ? 'on' : ''} onClick={async () => { await api('/instructions/' + i.id, { method: 'PATCH', body: { enabled: !i.enabled } }); load() }}>{i.enabled ? 'Enabled' : 'Disabled'}</button>{' '}
            <button className="danger" onClick={async () => { await api('/instructions/' + i.id, { method: 'DELETE' }); load() }}>Delete</button>
          </div>
        </div>
      ))}
    </div>
  )
}
