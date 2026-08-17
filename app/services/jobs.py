from typing import Any

from flask import Flask
from werkzeug.exceptions import NotFound

from app.db import get_conn
from app.services.repositories import get_document, update_document_status


def start_document_processing(app: Flask, document_id: int) -> dict[str, Any]:
    del app
    with get_conn() as conn:
        document = get_document(conn, document_id)
        if not document:
            raise NotFound(f"Document {document_id} does not exist")
        if document["processing_status"] in {"queued", "extracting", "storing"}:
            return {"document_id": document_id, "job_status": "already_running"}
        update_document_status(conn, document_id, "queued")

    try:
        from app.tasks import process_document_task

        task = process_document_task.delay(document_id)
    except Exception as exc:
        with get_conn() as conn:
            update_document_status(conn, document_id, "failed", str(exc))
        raise

    return {"document_id": document_id, "job_status": "queued", "task_id": task.id}


def get_document_job_status(document_id: int) -> dict[str, Any]:
    with get_conn() as conn:
        document = get_document(conn, document_id)

    if not document:
        raise NotFound(f"Document {document_id} does not exist")

    status = document["processing_status"]
    job_status_by_document_status = {
        "pending": "not_started",
        "queued": "queued",
        "extracting": "running",
        "storing": "running",
        "completed": "completed",
        "failed": "failed",
    }
    response: dict[str, Any] = {
        "document_id": document_id,
        "job_status": job_status_by_document_status.get(status, status),
    }
    if document["error_message"]:
        response["error"] = document["error_message"]
    return response
