from __future__ import annotations

try:
    from celery import shared_task
except Exception:  # pragma: no cover - fallback when Celery is unavailable
    def shared_task(*task_args, **task_kwargs):
        def decorator(func):
            func.delay = func
            return func

        return decorator

from home.repositories.series_repository import SeriesRepository


@shared_task(name="home.send_series_notifications")
def send_series_notifications(title: str, message: str) -> int:
    return SeriesRepository().bulk_notify_users(title=title, message=message)
