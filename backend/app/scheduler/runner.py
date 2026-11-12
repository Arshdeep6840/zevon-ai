"""Runs scheduled instructions (cron syntax, e.g. '0 8 * * *') through the agent."""


class ZevonScheduler:
    def __init__(self, engine, store):
        from apscheduler.schedulers.background import BackgroundScheduler
        self.engine, self.store = engine, store
        self.sched = BackgroundScheduler()

    def start(self):
        self.reload()
        self.sched.start()

    def stop(self):
        if self.sched.running:
            self.sched.shutdown(wait=False)

    def reload(self):
        from apscheduler.triggers.cron import CronTrigger
        for job in self.sched.get_jobs():
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
        self.engine.run(session=f"scheduled-{ins['id']}", text=ins["text"])
