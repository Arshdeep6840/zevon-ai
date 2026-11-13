// Native-shell helpers (Capacitor Android / Tauri desktop). Everything degrades to a no-op in a normal browser.
export const isAndroid = () => !!window.Capacitor?.isNativePlatform?.()
export const isDesktopApp = () => !!(window.__TAURI_INTERNALS__ || window.__TAURI__)

// Android: register for Firebase Cloud Messaging and hand the token to the backend.
export async function registerAndroidPush(sendToken) {
  if (!isAndroid()) return 'not-native'
  const { PushNotifications } = await import('@capacitor/push-notifications')
  const perm = await PushNotifications.requestPermissions()
  if (perm.receive !== 'granted') return 'denied'
  await PushNotifications.addListener('registration', (t) => sendToken(t.value))
  await PushNotifications.addListener('registrationError', (e) => console.warn('FCM registration error', e))
  await PushNotifications.register()
  return 'ok'
}

// Desktop (Tauri) and browser: show a system notification for a new inbox item while the app is running.
export async function notifyLocal(title, body) {
  try {
    if (isDesktopApp()) {
      const n = await import('@tauri-apps/plugin-notification')
      let ok = await n.isPermissionGranted()
      if (!ok) ok = (await n.requestPermission()) === 'granted'
      if (ok) n.sendNotification({ title, body })
    } else if ('Notification' in window && Notification.permission === 'granted') {
      new Notification(title, { body })
    }
  } catch { /* notifications are best-effort */ }
}
