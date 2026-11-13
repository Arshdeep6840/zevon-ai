// Zevon Mobile service worker: Web Push notifications (needs HTTPS, e.g. `tailscale serve`).
self.addEventListener('install', () => self.skipWaiting())
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()))
self.addEventListener('push', (event) => {
  let data = { title: 'Zevon', body: '' }
  try { data = event.data.json() } catch (e) { /* keep defaults */ }
  event.waitUntil(self.registration.showNotification(data.title, { body: data.body, icon: 'icon.svg', badge: 'icon.svg' }))
})
self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  event.waitUntil(self.clients.matchAll({ type: 'window' }).then((cs) => (cs[0] ? cs[0].focus() : self.clients.openWindow('./'))))
})
