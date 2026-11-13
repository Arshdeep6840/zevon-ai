"""Android push via Firebase Cloud Messaging (HTTP v1). Needs a Firebase service-account JSON (ZEVON_FCM_SERVICE_ACCOUNT)."""
import httpx


def _access_token(path: str) -> tuple[str, str]:
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account
    creds = service_account.Credentials.from_service_account_file(
        path, scopes=["https://www.googleapis.com/auth/firebase.messaging"])
    creds.refresh(Request())
    return creds.token, creds.project_id


def send_fcm(service_account_path: str, tokens: list[str], title: str, body: str) -> list[str]:
    """Send to each device token. Returns tokens FCM says are no longer valid (so they can be removed)."""
    if not (service_account_path and tokens):
        return []
    access, project = _access_token(service_account_path)
    dead = []
    for t in tokens:
        r = httpx.post(f"https://fcm.googleapis.com/v1/projects/{project}/messages:send",
                       headers={"Authorization": f"Bearer {access}"}, timeout=15,
                       json={"message": {"token": t, "notification": {"title": title, "body": body[:200]}}})
        if r.status_code in (400, 404) and ("UNREGISTERED" in r.text or "INVALID_ARGUMENT" in r.text or r.status_code == 404):
            dead.append(t)
    return dead
