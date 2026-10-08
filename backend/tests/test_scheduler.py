import os

from backend.app.scheduler import (
    JOB_DAILY,
    JOB_POINTS_SETTLEMENT,
    JOB_REMINDERS,
    JOB_WEEKLY,
    start_scheduler,
)


def test_start_scheduler_registers_report_and_settlement_jobs(monkeypatch):
    monkeypatch.delenv("DISABLE_SCHEDULER", raising=False)
    started = []

    class _Sched:
        def add_job(self, *a, **kw):
            self._jobs = getattr(self, "_jobs", [])
            self._jobs.append(kw.get("id"))

        def start(self):
            started.append(True)

    monkeypatch.setattr(
        "backend.app.scheduler.BackgroundScheduler",
        lambda **kw: _Sched(),
    )
    sched = start_scheduler()
    assert sched is not None
    assert started
    assert set(sched._jobs) == {JOB_DAILY, JOB_WEEKLY, JOB_REMINDERS, JOB_POINTS_SETTLEMENT}
    os.environ["DISABLE_SCHEDULER"] = "1"
