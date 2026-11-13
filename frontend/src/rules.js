export const TRIGGER_TYPES = [
  { id: 'email', label: 'A new email arrives' },
  { id: 'calendar', label: 'A calendar event starts soon' },
  { id: 'file', label: 'A new file appears in a folder' },
  { id: 'slack', label: 'A new Slack message arrives' },
  { id: 'time', label: 'Time condition (recurring)' },
]

const num = (v, d) => { const n = parseInt(v, 10); return Number.isFinite(n) && n > 0 ? n : d }

// Builds the backend trigger string (see backend/app/triggers/__init__.py PATTERNS).
export function buildSchedule(type, f = {}) {
  switch (type) {
    case 'email': return 'email:new'
    case 'calendar': return `calendar:soon:${num(f.minutes, 15)}`
    case 'file': return `file:new:${(f.folder || '').trim()}`
    case 'slack': return `slack:new:${(f.channel || '').trim()}`
    case 'time': {
      const win = f.from && f.to ? `@${f.from}-${f.to}` : ''
      return `time:every:${num(f.every, 30)}${f.unit === 'h' ? 'h' : 'm'}${win}`
    }
    default: return ''
  }
}

export function describeSchedule(s = '') {
  if (s === 'email:new') return 'when a new email arrives'
  if (s.startsWith('calendar:soon')) return `when an event starts within ${s.split(':')[2] || 15} min`
  if (s.startsWith('file:new:')) return `when a new file appears in ${s.slice(9)}`
  if (s.startsWith('slack:new:')) return `when Slack channel ${s.slice(10)} gets a message`
  if (s.startsWith('time:every:')) return `every ${s.slice(11).replace('@', ', only ')}`
  return s
}
