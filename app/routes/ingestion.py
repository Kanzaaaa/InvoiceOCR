from flask import Blueprint, current_app, jsonify, request
from werkzeug.datastructures import FileStorage

from app.db import get_conn
from app.services.file_storage import allowed_file, save_upload
from app.services.jobs import get_document_job_status, start_document_processing
from app.services.repositories import create_document, decimal_to_float
from app.services.workflow import get_document_result

ingestion_bp = Blueprint("ingestion", __name__)


@ingestion_bp.post("/documents")
def upload_document():
    if "file" not in request.files:
        return jsonify({"error": "Missing multipart file field named 'file'"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No selected file"}), 400

    if not allowed_file(file.filename, current_app.config["ALLOWED_EXTENSIONS"]):
        return jsonify({"error": "Only PDF files are supported"}), 400

    document = _create_document_from_upload(file)

    auto_process = request.args.get("auto_process", "true").lower() not in {"0", "false", "no"}
    job = {"document_id": document["id"], "job_status": "not_started"}
    if auto_process:
        job = start_document_processing(current_app._get_current_object(), document["id"])

    return jsonify(
        {
            "document": decimal_to_float(document),
            "job": job,
            "links": {
                "document": f"/api/documents/{document['id']}",
                "process": f"/api/documents/{document['id']}/process",
                "validation_results": f"/api/documents/{document['id']}/validation-results",
            },
        }
    ), 202 if auto_process else 201


@ingestion_bp.post("/documents/bulk")
def upload_documents_bulk():
    files = request.files.getlist("files")
    if not files:
        files = request.files.getlist("file")
    if not files:
        return jsonify({"error": "Missing multipart file fields named 'files'"}), 400

    max_files = current_app.config["BULK_UPLOAD_MAX_FILES"]
    if len(files) > max_files:
        return jsonify({"error": f"Bulk upload accepts at most {max_files} files per request"}), 400

    invalid_files = [
        file.filename or "<empty filename>"
        for file in files
        if not file.filename or not allowed_file(file.filename, current_app.config["ALLOWED_EXTENSIONS"])
    ]
    if invalid_files:
        return jsonify({"error": "Only PDF files are supported", "invalid_files": invalid_files}), 400

    auto_process = request.args.get("auto_process", "true").lower() not in {"0", "false", "no"}
    created_documents = []
    jobs = []
    for file in files:
        document = _create_document_from_upload(file)
        created_documents.append(decimal_to_float(document))
        if auto_process:
            jobs.append(start_document_processing(current_app._get_current_object(), document["id"]))
        else:
            jobs.append({"document_id": document["id"], "job_status": "not_started"})

    return jsonify(
        {
            "documents": created_documents,
            "jobs": jobs,
            "count": len(created_documents),
            "links": {
                "documents": "/api/documents",
                "invoices": "/api/invoices",
                "invoice_pos": "/api/invoice-pos",
                "lexware_invoice_review_export": "/api/exports/lexware_invoice_review.xlsx",
            },
        }
    ), 202 if auto_process else 201


@ingestion_bp.post("/documents/<int:document_id>/process")
def process_existing_document(document_id: int):
    document = get_document_result(document_id)["document"]
    job = start_document_processing(current_app._get_current_object(), document_id)
    return jsonify({"job": job, "document": document}), 202


@ingestion_bp.get("/documents/<int:document_id>")
def get_document(document_id: int):
    response = get_document_result(document_id)
    response["job"] = get_document_job_status(document_id)
    return jsonify(response)


@ingestion_bp.get("/documents/<int:document_id>/debug")
def get_document_debug(document_id: int):
    return jsonify(get_document_result(document_id, include_debug=True))


def _create_document_from_upload(file: FileStorage) -> dict:
    saved_path, file_hash = save_upload(file, current_app.config["UPLOAD_FOLDER"])
    with get_conn() as conn:
        return create_document(
            conn,
            file_name=saved_path.name,
            file_path=saved_path,
            file_hash=file_hash,
            document_type=None,
            processing_status="pending",
            error_message=None,
        )
