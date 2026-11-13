# HTTP API (all under /api, bearer token if ZEVON_API_TOKEN is set)
**Chat:** POST /chat {message, session} · POST /chat/stream (Server-Sent Events: token | tool | plan | done | error) · GET /history?session= · GET /sessions · DELETE /sessions/{id}
**Approvals:** GET /approvals · POST /approvals/{id}/approve|deny · POST /kill {active}
**Rules:** GET/POST /instructions · PATCH /instructions/{id} {enabled} · DELETE /instructions/{id} · GET /triggers
**Memory:** GET /memories?q= · POST /memories {text} · PUT /memories/{id} · DELETE /memories/{id}
**Permissions:** GET /policies · PUT /policies/{tool} {decision: allow|approve|deny|default}
**Status:** GET /health · /capabilities · /tools · /audit · /notifications · POST /notifications/read
**Voice:** POST /voice/transcribe (raw audio body) · POST /voice/speak {text} -> audio/wav
**Push:** GET /push/public-key · POST /push/subscribe (Web Push) · POST /push/fcm {token} (Android)
**Files:** GET /screenshots/{name}.png
