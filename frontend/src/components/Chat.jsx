import { useCallback, useEffect, useRef, useState } from 'react'
import { api, streamChat } from '../api.js'
import { startHandsFree } from '../handsfree.js'
import { matchWake } from '../voice.js'

const newId = () => 'chat-' + Math.random().toString(36).slice(2, 8)
const AWAKE_MS = 25000   // after "Hey Zevon", follow-ups don't need the wake word for this long

export default function Chat() {
  const [session, setSession] = useState(localStorage.getItem('zevon_session') || 'default')
  const [sessions, setSessions] = useState([])
  const [msgs, setMsgs] = useState([])
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [rec, setRec] = useState(null)
  const [speak, setSpeak] = useState(localStorage.getItem('zevon_speak') === '1')
  const [hf, setHf] = useState(false)
  const [requireWake, setRequireWake] = useState(localStorage.getItem('zevon_wake') !== '0')
  const [err, setErr] = useState('')
  const end = useRef(null)
  const stopHf = useRef(null)
  const awakeUntil = useRef(0)
  const speaking = useRef(false)
  const live = useRef({})
  live.current = { session, busy, speak, hf, requireWake }

  const loadSessions = useCallback(() => api('/sessions').then(setSessions).catch(() => {}), [])
  useEffect(() => { loadSessions() }, [loadSessions])
  useEffect(() => {
    localStorage.setItem('zevon_session', session)
    api('/history?session=' + encodeURIComponent(session)).then((h) => setMsgs(h.map((m) => ({ role: m.role, text: m.content })))).catch(() => setMsgs([]))
  }, [session])
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs])
  useEffect(() => () => stopHf.current?.(), [])

  async function say(reply) {
    speaking.current = true
    try {
      const wav = await api('/voice/speak', { method: 'POST', body: { text: reply } })
      await new Promise((res) => { const a = new Audio(URL.createObjectURL(wav)); a.onended = res; a.onerror = res; a.play().catch(res) })
    } catch {   // Piper not installed: browser speech fallback
      await new Promise((res) => {
        if (!('speechSynthesis' in window)) return res()
        const u = new SpeechSynthesisUtterance(reply); u.onend = res; u.onerror = res; speechSynthesis.speak(u)
      })
    } finally { speaking.current = false }
  }

  async function send(message, voice = false) {
    const t = (message ?? text).trim()
    if (!t || live.current.busy) return
    setText(''); setErr(''); setBusy(true)
    setMsgs((m) => [...m, { role: 'user', text: t }, { role: 'assistant', text: '', steps: [], plan: [], live: true }])
    const patch = (fn) => setMsgs((m) => { const c = m.slice(); c[c.length - 1] = fn(c[c.length - 1]); return c })
    let reply = ''
    try {
      await streamChat(live.current.session, t, (ev) => {
        if (ev.type === 'token') patch((a) => ({ ...a, text: a.text + ev.text }))
        else if (ev.type === 'plan') patch((a) => ({ ...a, plan: ev.steps }))
        else if (ev.type === 'tool') patch((a) => ({ ...a, steps: [...a.steps.filter((s) => !(s.tool === ev.name && s.status === 'running')), { tool: ev.name, status: ev.status }] }))
        else if (ev.type === 'done') { reply = ev.reply; patch((a) => ({ ...a, text: ev.reply || a.text, live: false })) }
        else if (ev.type === 'error') setErr(ev.message)
      })
    } catch (e) {
      setErr(e.status === 401 ? 'Wrong or missing token (Settings).' : 'Request failed: ' + e.message)
      patch((a) => ({ ...a, live: false }))
    }
    setBusy(false); loadSessions()
    if (reply && (live.current.speak || voice)) await say(reply)
  }

  // push-to-talk
  async function toggleMic() {
    if (rec) { rec.stop(); return }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const chunks = []
      const mr = new MediaRecorder(stream)
      mr.ondataavailable = (e) => chunks.push(e.data)
      mr.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop()); setRec(null)
        try {
          const r = await api('/voice/transcribe', { method: 'POST', body: new Blob(chunks, { type: mr.mimeType }), raw: true })
          if (r.text) send(r.text)
        } catch (e) { setErr(e.status === 501 ? 'Speech-to-text is not installed on the server.' : 'Voice failed: ' + e.message) }
      }
      mr.start(); setRec(mr)
    } catch { setErr('Microphone unavailable (HTTPS or localhost required, and permission granted).') }
  }

  // hands-free: continuous listening, optional "Hey Zevon" wake word, spoken replies
  async function handleSpoken(t) {
    const wake = matchWake(t)
    const awake = Date.now() < awakeUntil.current
    if (live.current.requireWake && !awake && !wake.woke) return          // ignore room chatter
    const cmd = wake.woke ? wake.command : t
    awakeUntil.current = Date.now() + AWAKE_MS
    if (!cmd) { await say('Yes?'); awakeUntil.current = Date.now() + AWAKE_MS; return }
    await send(cmd, true)
    awakeUntil.current = Date.now() + AWAKE_MS
  }

  async function toggleHf() {
    if (live.current.hf) { stopHf.current?.(); stopHf.current = null; setHf(false); return }
    try {
      stopHf.current = await startHandsFree({
        shouldListen: () => !speaking.current && !live.current.busy,
        onText: handleSpoken,
        onError: (e) => setErr(e.status === 501 ? 'Speech-to-text is not installed on the server.' : 'Voice error: ' + e.message),
      })
      setHf(true); setErr('')
    } catch { setErr('Microphone unavailable (HTTPS or localhost required, and permission granted).') }
  }

  const all = sessions.some((s) => s.session === session) ? sessions : [{ session, title: 'New chat', kind: 'chat' }, ...sessions]

  return (
    <div className="chat">
      <div className="toolbar">
        <select value={session} onChange={(e) => setSession(e.target.value)}>
          {all.map((s) => <option key={s.session} value={s.session}>{(s.kind === 'automation' ? '⚙ ' : '') + (s.title || s.session)}</option>)}
        </select>
        <button onClick={() => setSession(newId())}>New</button>
        <button className="danger" onClick={async () => { await api('/sessions/' + encodeURIComponent(session), { method: 'DELETE' }); setSession('default'); loadSessions() }}>Delete</button>
        <button className={hf ? 'on' : ''} onClick={toggleHf} title="Hands-free conversation">🎧 {hf ? 'Listening' : 'Hands-free'}</button>
        {hf && <label className="chk"><input type="checkbox" checked={requireWake} onChange={(e) => { localStorage.setItem('zevon_wake', e.target.checked ? '1' : '0'); setRequireWake(e.target.checked) }} /> say "Hey Zevon"</label>}
      </div>
      <div className="msgs">
        {msgs.length === 0 && <p className="muted">Ask Zevon anything. Try: "Check my unread email, then summarize it and add a task".</p>}
        {msgs.map((m, i) => (
          <div key={i}>
            {m.plan?.length > 0 && <div className="plan"><b>Plan</b><ol>{m.plan.map((s, j) => <li key={j}>{s}</li>)}</ol></div>}
            {(m.role === 'user' || m.text || m.live) && <div className={'msg ' + (m.role === 'user' ? 'me' : '')}>{m.text || '…'}{m.live && m.text ? ' ▍' : ''}</div>}
            {(m.steps || []).map((s, j) => <div key={j} className="step">🔧 {s.tool} → {s.status}</div>)}
          </div>
        ))}
        <div ref={end} />
      </div>
      {err && <div className="banner">{err}</div>}
      <form onSubmit={(e) => { e.preventDefault(); send() }}>
        <button type="button" className={rec ? 'danger' : ''} onClick={toggleMic} title="Push to talk">{rec ? '■' : '🎤'}</button>
        <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Ask Zevon…" />
        <button type="button" className={speak ? 'on' : ''} title="Speak replies"
          onClick={() => { localStorage.setItem('zevon_speak', speak ? '0' : '1'); setSpeak(!speak) }}>🔊</button>
        <button disabled={busy}>Send</button>
      </form>
    </div>
  )
}
