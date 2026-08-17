from openai import APIConnectionError, APITimeoutError, InternalServerError, RateLimitError

from app.celery_app import celery
from app.services.workflow import process_document_by_id


@celery.task(
    bind=True,
    autoretry_for=(APIConnectionError, APITimeoutError, RateLimitError, InternalServerError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def process_document_task(self, document_id: int) -> dict:
    result = process_document_by_id(document_id)
    return {
        "document_id": document_id,
        "processing_status": result["document"]["processing_status"],
    }
