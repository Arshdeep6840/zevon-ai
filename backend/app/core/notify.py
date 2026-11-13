"""Notifications: always stored in-app; also sent as Web Push to subscribed devices (needs pywebpush + HTTPS)."""
import base64
import json
from pathlib import Path


class Notifier:
    def __init__(self, store, cfg):
        self.store, self.cfg = store, cfg

    def push_available(self) -> bool:
        try:
            import pywebpush  # noqa: F401
            return True
        except ImportError:
            return False

    def _vapid(self):
        from py_vapid import Vapid
        path = Path(self.cfg.vapid_key_file)
        if path.exists():
            return Vapid.from_file(str(path))
        path.parent.mkdir(parents=True, exist_ok=True)
        v = Vapid()
        v.generate_keys()
        v.save_key(str(path))
        return v

    def public_key(self) -> str:
        from cryptography.hazmat.primitives import serialization as ser
        raw = self._vapid().public_key.public_bytes(ser.Encoding.X962, ser.PublicFormat.UncompressedPoint)
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    def notify(self, title: str, body: str):
        self.store.add_notification(title, body)
        if not self.push_available():
            return
        from pywebpush import WebPushException, webpush
        self._vapid()  # ensure key file exists
        payload = json.dumps({"title": title, "body": str(body)[:200]})
        for sub in self.store.push_subs():
            try:
                webpush(subscription_info=sub, data=payload, vapid_private_key=self.cfg.vapid_key_file,
                        vapid_claims={"sub": self.cfg.vapid_subject})
            except WebPushException as e:
                code = getattr(getattr(e, "response", None), "status_code", None)
                if code in (404, 410):
                    self.store.remove_push_sub(sub.get("endpoint", ""))
                self.store.audit("push", "send", str(e)[:200], "failed")
            except Exception as e:  # never let push break the agent
                self.store.audit("push", "send", str(e)[:200], "failed")
