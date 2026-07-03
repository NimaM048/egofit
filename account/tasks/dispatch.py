from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


def _uses_sync_celery_fallback(task: Callable[..., Any]) -> bool:
    delay = getattr(task, "delay", None)
    return delay is not None and delay is task


def dispatch_task(task: Callable[..., Any], /, *args: Any, **kwargs: Any) -> None:
    if _uses_sync_celery_fallback(task):
        thread = threading.Thread(
            target=_run_task_safely,
            args=(task, *args),
            kwargs=kwargs,
            daemon=True,
        )
        thread.start()
        return

    task.delay(*args, **kwargs)


def _run_task_safely(task: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    try:
        task(*args, **kwargs)
    except Exception:
        logger.exception("Background task %s failed.", getattr(task, "__name__", task))
