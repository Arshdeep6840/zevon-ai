"""Conditional rules: when a new email arrives, run each enabled conditional instruction with trigger 'email:new'.
The email body is never put in the prompt directly; the agent reads it with a tool, so it stays marked as untrusted."""
from ..integrations.google import auth, gmail

TRIGGER = "email:new"
QUERY = "is:unread in:inbox newer_than:1d"


class EmailTrigger:
    def __init__(self, engine, store, notifier):
        self.engine, self.store, self.notifier = engine, store, notifier

    def poll(self):
        if self.engine.policy.kill_switch or not auth.configured():
            return
        rules = [r for r in self.store.instructions(kind="conditional", enabled_only=True) if r["schedule"] == TRIGGER]
        if not rules:
            return
        first_run = self.store.seen_count("email:") == 0
        try:
            ids = gmail.list_message_ids(QUERY, 10)
        except Exception as e:
            self.store.audit("trigger", "email poll", str(e)[:200], "failed")
            return
        for mid in ids:
            if self.store.is_seen(f"email:{mid}"):
                continue
            self.store.mark_seen(f"email:{mid}")
            if first_run:      # baseline: don't fire on the existing backlog
                continue
            for r in rules:
                self.handle(r, mid)

    def handle(self, rule, mid):
        prompt = (f"A new email arrived (id {mid}). Read it with gmail_read_email, then apply this rule:\n"
                  f"{rule['text']}\nIf the rule's condition does not apply, reply with exactly IGNORE. "
                  f"Otherwise do what the rule says and reply with a short note for the user.")
        reply = self.engine.run(session=f"rule-{rule['id']}", text=prompt)["reply"].strip()
        self.store.audit("trigger", rule["name"], f"email {mid}", "ignored" if reply.upper().startswith("IGNORE") else "fired")
        if not reply.upper().startswith("IGNORE"):
            self.notifier.notify(rule["name"], reply)
