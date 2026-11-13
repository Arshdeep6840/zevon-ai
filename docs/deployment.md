# Deployment, phone, desktop, voice, push
## Phone access (Tailscale)
Install Tailscale on PC and phone. For HTTPS (needed for microphone and push on phones): `tailscale serve --bg 8000`, then open the `https://<pc>.<tailnet>.ts.net` URL. Set `ZEVON_API_TOKEN` first.
## Voice
`pip install -r backend/requirements-voice.txt`. Download a Piper voice (.onnx + .json) and set `ZEVON_PIPER_MODEL`. Without Piper, replies are spoken by the browser's built-in speech. Microphone needs HTTPS or localhost.
## Push notifications
`pip install pywebpush`, serve over HTTPS, then Settings → Enable push notifications on each device. Scheduled briefings and email rules send a push. (Not available inside the Android/Tauri wrappers; use the in-app Inbox there, or install the PWA.)
## Zevon Mobile for Android (Capacitor)
Needs Android Studio (SDK) and JDK 17+.
```bash
cd frontend && npm install && npm run android:sync && npm run android:open
```
Build/run from Android Studio. In the app: Settings → Server URL `http://<tailscale-ip>:8000` + token. The project is generated but has not been built on a device by the author.
## Zevon Desktop (Tauri v2)
Needs Rust (rustup) and OS deps from tauri.app/start/prerequisites.
```bash
cd frontend && npm install && npx tauri icon public/icon.svg && npm run tauri:build
```
First launch: Settings → Server URL. Not yet built by the author.
## Docker
`docker compose up` (Ollama + Zevon). Then `docker compose exec ollama ollama pull qwen3:8b`.
