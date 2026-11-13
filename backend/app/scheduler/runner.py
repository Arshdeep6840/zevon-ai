"""Runs scheduled instructions (cron syntax, e.g. '0 8 * * *') and interval jobs (email trigger polling)."""


class ZevonScheduler:
    def __init__(self, engine, store, notifier=None):
        from apscheduler.schedulers.background import BackgroundScheduler
        self.engine, self.store, self.notifier = engine, store, notifier
        self.sched = BackgroundScheduler()

    def start(self):
        self.reload()
        self.sched.start()

    def stop(self):
        if self.sched.running:
            self.sched.shutdown(wait=False)

    def add_interval(self, func, minutes: int, job_id: str):
        self.sched.add_job(func, "interval", minutes=max(1, minutes), id=job_id, replace_existing=True)

    def reload(self):
        from apscheduler.triggers.cron import CronTrigger
        for job in self.sched.get_jobs():
            if job.id.startswith("ins-"):
                job.remove()
        for ins in self.store.instructions(kind="scheduled", enabled_only=True):
            try:
                trigger = CronTrigger.from_crontab(ins["schedule"])
            except ValueError:
                self.store.audit("scheduler", ins["name"], f"bad cron: {ins['schedule']}", "skipped")
                continue
            self.sched.add_job(self._run, trigger, args=[ins], id=f"ins-{ins['id']}")

    def _run(self, ins):
        self.store.audit("scheduler", ins["name"], ins["text"], "started")
        reply = self.engine.run(session=f"scheduled-{ins['id']}", text=ins["text"])["reply"]
        if self.notifier:
            self.notifier.notify(ins["name"], reply)
