"""Generic polling trigger: subclasses return (unique_key, context) events; each new event runs the matching rules."""
from ..integrations.system import filesystem  # noqa: F401  (ensures sandbox settings are shared)


class RuleTrigger:
    name = "base"
    prefix = ""           # rule["schedule"].startswith(prefix)
    baseline = True       # first poll only records what already exists (no firing on backlog)

    def __init__(self, engine, store, notifier):
        self.engine, self.store, self.notifier = engine, store, notifier

    def available(self) -> bool:
        return True

    def events(self, rule) -> list[tuple[str, str]]:
        raise NotImplementedError

    def poll(self):
        if self.engine.policy.kill_switch or not self.available():
            return
        rules = [r for r in self.store.instructions(kind="conditional", enabled_only=True) if r["schedule"].startswith(self.prefix)]
        for rule in rules:
            tag = f"rt:{self.name}:{rule['id']}"
            try:
                evs = self.events(rule)
            except Exception as e:
                self.store.audit("trigger", rule["name"], str(e)[:200], "poll failed")
                continue
            first = self.baseline and not self.store.is_seen(f"{tag}:__baseline__")
            self.store.mark_seen(f"{tag}:__baseline__")
            for key, context in evs:
                k = f"{tag}:{key}"
                if self.store.is_seen(k):
                    continue
                self.store.mark_seen(k)
                if not first:
                    self.fire(rule, context)

    def fire(self, rule, context: str):
        prompt = (f"{context}\nApply this rule:\n{rule['text']}\n"
                  "If the rule's condition does not apply, reply with exactly IGNORE. "
                  "Otherwise do what the rule says and reply with a short note for the user.")
        reply = self.engine.run(session=f"rule-{rule['id']}", text=prompt)["reply"].strip()
        ignored = reply.upper().startswith("IGNORE")
        self.store.audit("trigger", rule["name"], context[:120], "ignored" if ignored else "fired")
        if not ignored:
            self.notifier.notify(rule["name"], reply)
