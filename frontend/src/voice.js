// Pure voice logic (no browser APIs) so it can be unit-tested with `node --test`.
const NAMES = '(?:zevon|zeven|zevin|zevan|sevon)'
const WITH_GREETING = new RegExp(`^\\W*(?:hey|hi|ok|okay|hello)\\W+(?:${NAMES}|seven)\\b\\W*`, 'i')
const BARE = new RegExp(`^\\W*${NAMES}\\b\\W*`, 'i')

// Wake word is detected on the *transcript* (local Whisper), so it tolerates a few common mis-hearings.
export function matchWake(text) {
  const t = (text || '').trim()
  const m = t.match(WITH_GREETING) || t.match(BARE)
  return m ? { woke: true, command: t.slice(m[0].length).trim() } : { woke: false, command: t }
}

// Energy-based voice activity detection. feed(level 0..1, nowMs) -> 'start' | 'end' | 'discard' | null
export class Segmenter {
  constructor({ threshold = 0.02, silenceMs = 1200, minSpeechMs = 400, maxMs = 15000 } = {}) {
    Object.assign(this, { threshold, silenceMs, minSpeechMs, maxMs })
    this.state = 'idle'
    this.start = 0
    this.lastLoud = 0
  }

  feed(level, now) {
    if (this.state === 'idle') {
      if (level >= this.threshold) {
        this.state = 'speaking'
        this.start = this.lastLoud = now
        return 'start'
      }
      return null
    }
    if (level >= this.threshold) this.lastLoud = now
    const total = now - this.start
    if (now - this.lastLoud >= this.silenceMs || total >= this.maxMs) {
      this.state = 'idle'
      return this.lastLoud - this.start >= this.minSpeechMs ? 'end' : 'discard'
    }
    return null
  }
}
