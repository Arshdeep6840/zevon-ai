import { useEffect, useRef, useState } from 'react'
import { api } from '../api.js'

export default function Chat() {
  const [msgs, setMsgs] = useState([])
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [rec, setRec] = useState(null)
  const [speak, setSpeak] = useState(localStorage.getItem('zevon_speak') === '1')
  const [err, setErr] = useState('')
  const end = useRef(null)

  useEffect(() => {
    api('/history').then((h) => setMsgs(h.map((m) => ({ role: m.role, text: m.content })))).catch(() => {})
  }, [])
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs])

  async function say(reply) {
    try {
      const wav = await api('/voice/speak', { method: 'POST', body: { text: reply } })
      new Audio(URL.createObjectURL(wav)).play()
    } catch {
      if ('speechSynthesis' in window) speechSynthesis.speak(new SpeechSynthesisUtterance(reply)) // browser fallback
    }
  }

  async function send(message) {
    const t = (message ?? text).trim()
    if (!t || busy) return
    setText(''); setErr(''); setBusy(true)
    setMsgs((m) => [...m, { role: 'user', text: t }])
    try {
      const r = await api('/chat', { method: 'POST', body: { message: t } })
      setMsgs((m) => [...m, { role: 'assistant', text: r.reply || '(no reply)', steps: r.steps }])
      if (speak && r.reply) say(r.reply)
    } catch (e) { setErr(e.status === 401 ? 'Wrong or missing token (Settings).' : 'Request failed: ' + e.message) }
    setBusy(false)
  }

  async function toggleMic() {
    if (rec) { rec.stop(); return }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true }) // needs HTTPS or localhost
      const chunks = []
      const mr = new MediaRecorder(stream)
      mr.ondataavailable = (e) => chunks.push(e.data)
      mr.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop())
        setRec(null)
        try {
          const r = await api('/voice/transcribe', { method: 'POST', body: new Blob(chunks, { type: mr.mimeType }), raw: true })
          if (r.text) send(r.text)
        } catch (e) { setErr(e.status === 501 ? 'Speech-to-text is not installed on the server.' : 'Voice failed: ' + e.message) }
      }
      mr.start(); setRec(mr)
    } catch { setErr('Microphone unavailable (HTTPS or localhost required, and permission granted).') }
  }

  return (
    <div className="chat">
      <div className="msgs">
        {msgs.length === 0 && <p className="muted">Ask Zevon anything. Try: "What's on my calendar this week?"</p>}
        {msgs.map((m, i) => (
          <div key={i}>
            <div className={'msg ' + (m.role === 'user' ? 'me' : '')}>{m.text}</div>
            {(m.steps || []).map((s, j) => <div key={j} className="step">🔧 {s.tool} → {s.status}</div>)}
          </div>
        ))}
        {busy && <div className="msg">Thinking…</div>}
        <div ref={end} />
      </div>
      {err && <div className="banner">{err}</div>}
      <form onSubmit={(e) => { e.preventDefault(); send() }}>
        <button type="button" className={rec ? 'danger' : ''} onClick={toggleMic} title="Voice input">{rec ? '■' : '🎤'}</button>
        <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Ask Zevon…" />
        <button type="button" className={speak ? 'on' : ''} title="Speak replies"
          onClick={() => { localStorage.setItem('zevon_speak', speak ? '0' : '1'); setSpeak(!speak) }}>🔊</button>
        <button disabled={busy}>Send</button>
      </form>
    </div>
  )
}
