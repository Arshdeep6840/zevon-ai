import { useEffect, useState } from 'react'
import { api, getServer, getToken, setServer, setToken, urlB64ToUint8 } from '../api.js'
import { isAndroid, isDesktopApp, notifyLocal, registerAndroidPush } from '../native.js'

export default function Settings() {
  const [server, setS] = useState(getServer())
  const [token, setT] = useState(getToken())
  const [caps, setCaps] = useState(null)
  const [msg, setMsg] = useState('')

  const check = () => api('/capabilities').then((c) => { setCaps(c); setMsg('Connected ✔') }).catch((e) => { setCaps(null); setMsg(e.status === 401 ? 'Server reached, but the token is wrong.' : 'Cannot reach server.') })
  useEffect(() => { check() }, [])
  function save(e) { e.preventDefault(); setServer(server); setToken(token); check() }

  async function enableWebPush() {
    try {
      const reg = await navigator.serviceWorker.ready
      const { key } = await api('/push/public-key')
      if ((await Notification.requestPermission()) !== 'granted') return setMsg('Notification permission denied.')
      const sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: urlB64ToUint8(key) })
      await api('/push/subscribe', { method: 'POST', body: sub.toJSON() })
      setMsg('Push notifications enabled on this device ✔')
    } catch (e) { setMsg(e.status === 501 ? 'Server needs: pip install pywebpush' : 'Push failed (needs HTTPS): ' + e.message) }
  }

  async function enableAndroidPush() {
    try {
      const r = await registerAndroidPush((token) => api('/push/fcm', { method: 'POST', body: { token } }))
      setMsg(r === 'ok' ? 'Android push registered ✔ (server needs ZEVON_FCM_SERVICE_ACCOUNT)' : 'Notification permission denied.')
    } catch (e) { setMsg('Android push failed: ' + e.message + ' (needs google-services.json in the app, see docs/deployment.md)') }
  }

  async function enableDesktopNotify() {
    if (isDesktopApp()) { await notifyLocal('Zevon', 'Notifications enabled'); setMsg('Desktop notifications enabled ✔') }
    else setMsg((await Notification.requestPermission()) === 'granted' ? 'Browser notifications enabled while the app is open ✔' : 'Permission denied.')
  }

  const yes = (b) => (b ? '✔' : '✖')
  return (
    <div className="list">
      <form className="card form" onSubmit={save}>
        <b>Connection</b>
        <input placeholder="Server URL, e.g. http://100.x.y.z:8000 (empty = same origin)" value={server} onChange={(e) => setS(e.target.value)} />
        <input type="password" placeholder="API token (ZEVON_API_TOKEN)" value={token} onChange={(e) => setT(e.target.value)} />
        <button>Save &amp; test</button>
        {msg && <div className="banner ok">{msg}</div>}
      </form>
      {caps && (
        <div className="card">
          <b>Zevon Core status</b>
          <div>Model: {caps.model} · {caps.provider} {caps.local_model ? <span className="pill ok">local</span> : <span className="pill warn">cloud: prompts leave your machine</span>}</div>
          <div>Tools: {caps.tools} · Planning: {caps.planning} · Terminal ask-mode {yes(caps.terminal_ask)} · Browser control {yes(caps.playwright)}</div>
          <div>Voice in {yes(caps.voice_stt)} · Voice out {yes(caps.voice_tts)} · Semantic memory {yes(caps.vector_memory)}</div>
          <div>Google {yes(caps.google)} · Web Push {yes(caps.push)} · Android push {yes(caps.fcm)} · MCP tools {caps.mcp_tools} · Extensions {caps.extensions.length}</div>
          <div>
            {isAndroid() && <button onClick={enableAndroidPush}>Enable Android push</button>}{' '}
            {!isAndroid() && caps.push && !isDesktopApp() && <button onClick={enableWebPush}>Enable web push</button>}{' '}
            {!isAndroid() && <button onClick={enableDesktopNotify}>Enable desktop alerts</button>}
          </div>
        </div>
      )}
    </div>
  )
}
