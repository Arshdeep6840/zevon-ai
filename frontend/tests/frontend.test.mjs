import test from 'node:test'
import assert from 'node:assert/strict'
import { matchWake, Segmenter } from '../src/voice.js'
import { parseSSE } from '../src/sse.js'
import { buildSchedule, describeSchedule } from '../src/rules.js'

test('wake word detection', () => {
  assert.deepEqual(matchWake('Hey Zevon, what is on my calendar?'), { woke: true, command: 'what is on my calendar?' })
  assert.deepEqual(matchWake('Zevon check my email'), { woke: true, command: 'check my email' })
  assert.deepEqual(matchWake('ok zeven summarize this'), { woke: true, command: 'summarize this' })
  assert.deepEqual(matchWake('hey Zevon'), { woke: true, command: '' })
  assert.equal(matchWake('I had seven apples').woke, false)
  assert.equal(matchWake('hey there how are you').woke, false)
  assert.equal(matchWake('').woke, false)
})

test('segmenter: speech then silence ends a segment', () => {
  const s = new Segmenter()
  assert.equal(s.feed(0.001, 0), null)
  assert.equal(s.feed(0.2, 100), 'start')
  for (let t = 150; t <= 900; t += 50) assert.equal(s.feed(0.2, t), null)
  assert.equal(s.feed(0.001, 1500), null)
  assert.equal(s.feed(0.001, 2200), 'end')
  assert.equal(s.state, 'idle')
})

test('segmenter: short blip is discarded; long speech is capped', () => {
  const s = new Segmenter()
  s.feed(0.5, 0)
  assert.equal(s.feed(0.0, 1300), 'discard')
  const t = new Segmenter({ maxMs: 3000 })
  t.feed(0.5, 0)
  for (let now = 100; now < 3000; now += 100) assert.equal(t.feed(0.5, now), null)
  assert.equal(t.feed(0.5, 3000), 'end')
})

test('SSE parser handles split chunks and bad events', () => {
  let { events, rest } = parseSSE('data: {"type":"token","text":"He"}\n\ndata: {"type":"to')
  assert.deepEqual(events, [{ type: 'token', text: 'He' }])
  ;({ events, rest } = parseSSE(rest + 'ken","text":"llo"}\n\ndata: not-json\n\n'))
  assert.deepEqual(events, [{ type: 'token', text: 'llo' }])
  assert.equal(rest, '')
})

// must stay in sync with backend/app/triggers/__init__.py
const PATTERNS = [/^email:new$/, /^calendar:soon(:\d{1,3})?$/, /^file:new:.+$/, /^slack:new:[A-Za-z0-9]+$/, /^time:every:\d{1,3}[mh](@\d{2}:\d{2}-\d{2}:\d{2})?$/]
test('rule schedules match the backend trigger patterns', () => {
  const cases = [
    ['email', {}, 'email:new'], ['calendar', { minutes: '30' }, 'calendar:soon:30'], ['calendar', {}, 'calendar:soon:15'],
    ['file', { folder: ' /home/me/Downloads ' }, 'file:new:/home/me/Downloads'], ['slack', { channel: 'C123' }, 'slack:new:C123'],
    ['time', { every: '2', unit: 'h', from: '09:00', to: '18:00' }, 'time:every:2h@09:00-18:00'], ['time', {}, 'time:every:30m'],
  ]
  for (const [type, f, want] of cases) {
    const got = buildSchedule(type, f)
    assert.equal(got, want)
    assert.ok(PATTERNS.some((p) => p.test(got)), got)
  }
  assert.match(describeSchedule('time:every:2h@09:00-18:00'), /every 2h, only 09:00-18:00/)
})
