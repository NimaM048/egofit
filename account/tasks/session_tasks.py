from __future__ import annotations

try:
    from celery import shared_task
except Exception:  # pragma: no cover - fallback when Celery is unavailable
    def shared_task(*task_args, **task_kwargs):
        def decorator(func):
            func.delay = func
            return func

        return decorator

from account.models import User
from account.repositories.session_repository import SessionRepository


@shared_task(name="account.log_user_session")
def log_user_session(user_id: int, session_key: str, ip_address: str, user_agent: str):
    user = User.objects.get(pk=user_id)
    return SessionRepository().upsert_login_session(
        user=user,
        session_key=session_key,
        ip_address=ip_address,
        user_agent=user_agent,
    )

