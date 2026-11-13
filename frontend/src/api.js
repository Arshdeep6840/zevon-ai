// Backend connection. Server URL + token live in localStorage so Zevon Mobile (Android) and the
// desktop app can point at your PC over Tailscale. In the browser served by the backend, URL stays empty.
export const getServer = () => (localStorage.getItem('zevon_server') || '').replace(/\/+$/, '')
export const setServer = (v) => localStorage.setItem('zevon_server', v.trim())
export const getToken = () => localStorage.getItem('zevon_token') || ''
export const setToken = (v) => localStorage.setItem('zevon_token', v.trim())
export const isNative = () =>
  !!(window.Capacitor?.isNativePlatform?.() || window.__TAURI_INTERNALS__ || window.__TAURI__)

export async function api(path, { method = 'GET', body, raw = false } = {}) {
  const headers = { Authorization: 'Bearer ' + getToken() }
  let payload = body
  if (body !== undefined && !raw) {
    headers['Content-Type'] = 'application/json'
    payload = JSON.stringify(body)
  }
  const r = await fetch(getServer() + '/api' + path, { method, headers, body: payload })
  if (!r.ok) {
    let detail = r.statusText
    try { detail = (await r.json()).detail || detail } catch { /* not json */ }
    const e = new Error(detail)
    e.status = r.status
    throw e
  }
  return (r.headers.get('content-type') || '').includes('json') ? r.json() : r.blob()
}

export function urlB64ToUint8(b64) {
  const pad = '='.repeat((4 - (b64.length % 4)) % 4)
  const raw = atob((b64 + pad).replace(/-/g, '+').replace(/_/g, '/'))
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)))
}
