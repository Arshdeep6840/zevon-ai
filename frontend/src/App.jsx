import { useCallback, useEffect, useRef, useState } from 'react'
import { api, getServer } from './api.js'
import { isAndroid, isDesktopApp, notifyLocal, registerAndroidPush } from './native.js'
import Chat from './components/Chat.jsx'
import Approvals from './components/Approvals.jsx'
import Inbox from './components/Inbox.jsx'
import Rules from './components/Rules.jsx'
import Memory from './components/Memory.jsx'
import Permissions from './components/Permissions.jsx'
import { Audit } from './components/Lists.jsx'
import Settings from './components/Settings.jsx'

const TABS = ['Chat', 'Approvals', 'Inbox', 'Rules', 'Memory', 'Permissions', 'Audit', 'Settings']

export default function App() {
  const native = isAndroid() || isDesktopApp()
  const [tab, setTab] = useState(native && !getServer() ? 'Settings' : 'Chat')
  const [badges, setBadges] = useState({ Approvals: 0, Inbox: 0 })
  const [killed, setKilled] = useState(false)
  const [offline, setOffline] = useState(false)
  const lastUnread = useRef(null)

  const refresh = useCallback(async () => {
    try {
      const [a, n, h] = await Promise.all([api('/approvals'), api('/notifications?unread=true'), api('/health')])
      setBadges({ Approvals: a.length, Inbox: n.length })
      setKilled(h.kill_switch)
      setOffline(false)
      if (lastUnread.current !== null && n.length > lastUnread.current) notifyLocal(n[0].title, n[0].body)   // new inbox item
      lastUnread.current = n.length
    } catch (e) { setOffline(e.status !== 401) }
  }, [])

  useEffect(() => {
    refresh()
    const t = setInterval(refresh, 15000)
    return () => clearInterval(t)
  }, [refresh, tab])

  // Android: register for push automatically once a server is configured (needs Firebase set up, see docs)
  useEffect(() => {
    if (isAndroid() && getServer()) registerAndroidPush((token) => api('/push/fcm', { method: 'POST', body: { token } })).catch(() => {})
  }, [])

  async function toggleKill() {
    const r = await api('/kill', { method: 'POST', body: { active: !killed } })
    setKilled(r.kill_switch)
  }

  return (
    <div className="app">
      <header>
        <h1>Zevon AI <small>Your AI. Your Rules.</small></h1>
        <button className={killed ? 'danger' : ''} onClick={toggleKill}>{killed ? 'Kill switch ON' : 'Kill switch'}</button>
      </header>
      {offline && <div className="banner">Can't reach your Zevon server. Check Settings → Server URL, and that your PC is on.</div>}
      <nav>
        {TABS.map((t) => (
          <button key={t} className={t === tab ? 'on' : ''} onClick={() => setTab(t)}>
            {t}{badges[t] ? <span className="badge">{badges[t]}</span> : null}
          </button>
        ))}
      </nav>
      <main>
        {tab === 'Chat' && <Chat />}
        {tab === 'Approvals' && <Approvals onChange={refresh} />}
        {tab === 'Inbox' && <Inbox onChange={refresh} />}
        {tab === 'Rules' && <Rules />}
        {tab === 'Memory' && <Memory />}
        {tab === 'Permissions' && <Permissions />}
        {tab === 'Audit' && <Audit />}
        {tab === 'Settings' && <Settings />}
      </main>
    </div>
  )
}
