// Incremental Server-Sent-Events parser: feed it text, get complete events back plus the unfinished rest.
export function parseSSE(buffer) {
  const events = []
  let rest = buffer
  let i
  while ((i = rest.indexOf('\n\n')) >= 0) {
    const block = rest.slice(0, i)
    rest = rest.slice(i + 2)
    const line = block.split('\n').find((l) => l.startsWith('data: '))
    if (line) {
      try { events.push(JSON.parse(line.slice(6))) } catch { /* ignore malformed event */ }
    }
  }
  return { events, rest }
}
