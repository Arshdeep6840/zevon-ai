# HTTP API (all under /api, bearer token if ZEVON_API_TOKEN is set)
GET /health · /capabilities · /tools · /history?session= · /audit · /notifications · /instructions · /approvals
POST /chat {message, session} · /kill {active} · /instructions {name, kind, text, schedule} · /approvals/{id}/approve|deny · /notifications/read
POST /voice/transcribe (raw audio body) · /voice/speak {text} → audio/wav · /push/subscribe · GET /push/public-key · DELETE /instructions/{id}
