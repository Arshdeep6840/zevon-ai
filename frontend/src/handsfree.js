// Hands-free listening: continuous mic monitoring with voice-activity detection. Each spoken segment is sent to
// the server's local Whisper (/api/voice/transcribe). Needs HTTPS or localhost + microphone permission.
import { api } from './api.js'
import { Segmenter } from './voice.js'

const MAX_IDLE_MS = 8000   // pre-roll kept while idle so the first word is never clipped

export async function startHandsFree({ shouldListen, onText, onError, onLevel }) {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  const ctx = new (window.AudioContext || window.webkitAudioContext)()
  const analyser = ctx.createAnalyser()
  analyser.fftSize = 1024
  ctx.createMediaStreamSource(stream).connect(analyser)
  const buf = new Uint8Array(analyser.fftSize)
  let seg = new Segmenter()
  let cur = null
  let stopped = false
  let wasListening = true

  function startRec() {
    const chunks = []
    const r = new MediaRecorder(stream)
    r.ondataavailable = (e) => e.data.size && chunks.push(e.data)
    r.start()
    cur = { r, chunks, start: Date.now() }
  }

  function finish(send) {
    const { r, chunks } = cur
    r.onstop = async () => {
      if (!send || stopped) return
      try {
        const out = await api('/voice/transcribe', { method: 'POST', body: new Blob(chunks, { type: r.mimeType }), raw: true })
        if (out.text && out.text.trim()) onText(out.text.trim())
      } catch (e) { onError?.(e) }
    }
    r.stop()
    if (!stopped) startRec()
  }

  startRec()
  const timer = setInterval(() => {
    analyser.getByteTimeDomainData(buf)
    let sum = 0
    for (const v of buf) { const x = (v - 128) / 128; sum += x * x }
    const level = Math.sqrt(sum / buf.length)
    onLevel?.(level)
    const listening = shouldListen()
    if (!listening) {                       // Zevon is speaking/thinking: don't record itself
      seg = new Segmenter()
      wasListening = false
      return
    }
    if (!wasListening) { wasListening = true; finish(false); return }   // restart a clean recording
    const ev = seg.feed(level, Date.now())
    if (ev === 'end') finish(true)
    else if (ev === 'discard') finish(false)
    else if (ev === null && seg.state === 'idle' && Date.now() - cur.start > MAX_IDLE_MS) finish(false)
  }, 50)

  return function stop() {
    stopped = true
    clearInterval(timer)
    try { cur.r.stop() } catch { /* already stopped */ }
    stream.getTracks().forEach((t) => t.stop())
    ctx.close().catch(() => {})
  }
}
