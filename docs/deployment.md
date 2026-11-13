# Deployment, phone, desktop, voice, push
## Phone access (Tailscale)
Install Tailscale on PC and phone. For HTTPS (needed for microphone and push on phones): `tailscale serve --bg 8000`, then open the `https://<pc>.<tailnet>.ts.net` URL. Set `ZEVON_API_TOKEN` first.
## Always-on (so your phone works without starting anything)
Zevon runs on a computer, so that computer must be on and reachable. Options: (1) run it on an always-on machine (mini PC, home server, Raspberry Pi 5 for small models), (2) `python scripts/install_service.py --install` to start it automatically at login/boot (systemd / launchd / Task Scheduler), (3) `docker compose up -d` with `restart: unless-stopped`. It cannot work while the machine is asleep or off; use OS power settings to keep it awake. The local LLM needs enough RAM/VRAM on that machine, or point `ZEVON_LLM_PROVIDER` at a cloud model (prompts then leave your machine).
## Models
`ollama` (default, local). `openai` = any OpenAI-compatible server: **llama.cpp** (`llama-server -m model.gguf --jinja`, base URL `http://localhost:8080/v1`), **vLLM** (`vllm serve <model> --enable-auto-tool-choice --tool-call-parser hermes`), LM Studio, or cloud (OpenAI, OpenRouter, Groq...). `anthropic` = Claude API. Tool calling quality depends on the model. Settings -> Zevon Core status shows whether the current model is local or cloud.
## Hands-free voice and "Hey Zevon"
Chat -> Hands-free. Zevon listens through the mic, detects when you stop speaking, transcribes locally with Whisper, and (if "say Hey Zevon" is ticked) only reacts when the transcript starts with the wake word; follow-ups within 25 s need no wake word. The wake word is detected on the Whisper transcript, not a dedicated wake-word engine, so it uses more CPU than one and may mishear the name. Needs HTTPS or localhost and the server-side voice packages.
## Android push (Firebase)
1. Create a Firebase project; add an Android app with id `ai.zevon.mobile`; download `google-services.json` into `frontend/android/app/`. 2. Firebase console -> Project settings -> Service accounts -> generate a key; save the JSON on the server and set `ZEVON_FCM_SERVICE_ACCOUNT=/path/key.json`. 3. `pip install -r backend/requirements-google.txt`. 4. Rebuild the app (`npm run android:sync`, then Android Studio). The app registers its token automatically; scheduled briefings and rules then push to the phone even when the app is closed.
## Desktop alerts
The Tauri app shows system notifications (tauri-plugin-notification) when new inbox items arrive while it is running.
## Rules and triggers
Rules tab -> "When something happens": new email, calendar event starting soon, new file in a folder (must be an authorized folder), new Slack message, or a recurring time condition (e.g. every 30 min between 09:00 and 18:00). Triggers are polled (default every minute; email every 5). First poll only records what already exists. Event details are read by the agent through tools, never pasted into the prompt.
## Terminal ask-mode and browser control
`ZEVON_TERMINAL_ASK=on` lets Zevon request any single command; the Approvals tab shows the exact command. `browser_interact` (click/fill/press) needs `pip install playwright && playwright install chromium` and always needs approval.
`pip install -r backend/requirements-voice.txt`. Download a Piper voice (.onnx + .json) and set `ZEVON_PIPER_MODEL`. Without Piper, replies are spoken by the browser's built-in speech. Microphone needs HTTPS or localhost.
## Push notifications
`pip install pywebpush`, serve over HTTPS, then Settings → Enable push notifications on each device. Scheduled briefings and email rules send a push. In the Android app use Android push (below); desktop uses native notifications.
## Zevon Mobile for Android (Capacitor)
Needs Android Studio (SDK) and JDK 17+.
```bash
cd frontend && npm install && npm run android:sync && npm run android:open
```
Build/run from Android Studio. In the app: Settings → Server URL `http://<tailscale-ip>:8000` + token. The project is generated (icons, push plugin, microphone and cleartext-HTTP settings included) but has not been built on a device by the author.
## Zevon Desktop (Tauri v2)
Needs Rust (rustup) and OS deps from tauri.app/start/prerequisites.
```bash
cd frontend && npm install && npx tauri icon public/icon.svg && npm run tauri:build
```
First launch: Settings → Server URL. Not yet built by the author.
## Docker
`docker compose up` (Ollama + Zevon). Then `docker compose exec ollama ollama pull qwen3:8b`.
