"""Background job dispatch. Celery in production; inline (FastAPI BackgroundTasks) in dev/test."""
from __future__ import annotations

import uuid

from celery import Celery

from app.core.config import get_settings

_settings = get_settings()
celery_app = Celery("learndna", broker=_settings.redis_url, backend=_settings.redis_url)
celery_app.conf.update(task_acks_late=True, worker_prefetch_multiplier=1, task_default_queue="documents")


@celery_app.task(name="process_submission", bind=True, max_retries=0)
def process_submission_task(self, submission_id: str) -> str:
    from app.core.db import SessionLocal
    from app.services.pipeline import process_submission

    with SessionLocal() as db:
        return process_submission(db, uuid.UUID(submission_id)).value


def dispatch_processing(submission_id: uuid.UUID, background_tasks=None) -> None:
    if _settings.task_backend == "celery":
        process_submission_task.delay(str(submission_id))
        return

    def _run() -> None:
        from app.core.db import SessionLocal
        from app.services.pipeline import process_submission

        with SessionLocal() as db:
            process_submission(db, submission_id)

    if background_tasks is not None:
        background_tasks.add_task(_run)
    else:
        _run()
