from pathlib import Path
from typing import Any

from flask import current_app
from werkzeug.exceptions import NotFound

from app.db import get_conn
from app.services.client_matching import get_or_create_client
from app.services.normalization import normalize_extraction, serialize_normalized
from app.services.openai_extractor import extract_invoice_data
from app.services.repositories import (
    count_duplicate_invoice,
    create_extraction_run,
    create_invoice,
    delete_invoices_for_document,
    decimal_to_float,
    get_document,
    get_invoice_for_document,
    get_validation_summary,
    replace_invoice_positions,
    replace_validation_results,
    update_document_status,
    update_document_type,
)
from app.services.validation import build_validation_results


def process_document_by_id(document_id: int) -> dict[str, Any]:
    model_name = current_app.config["OPENAI_MODEL"]
    with get_conn() as conn:
        document = get_document(conn, document_id)
        if not document:
            raise NotFound(f"Document {document_id} does not exist")
        update_document_status(conn, document_id, "extracting")

    file_path = Path(document["file_path"])
    raw_response: dict[str, Any] | None = None
    normalized: dict[str, Any] | None = None

    current_app.logger.info(
        "Document extraction started: document_id=%s file=%s model=%s",
        document_id,
        document["file_name"],
        model_name,
    )

    try:
        raw_response = extract_invoice_data(file_path)
        normalized = normalize_extraction(raw_response, current_app.config["VALID_INVOICE_TYPES"])
        current_app.logger.info(
            "Document extraction normalized: document_id=%s client=%s invoice_number=%s invoice_type=%s pos_count=%s",
            document_id,
            normalized["client"]["name_original"],
            normalized["invoice"]["invoice_number"],
            normalized["invoice"]["invoice_type"],
            len(normalized["invoice_pos"]),
        )
    except Exception as exc:
        current_app.logger.exception("Document extraction failed before storage: document_id=%s", document_id)
        with get_conn() as conn:
            update_document_status(conn, document_id, "failed", str(exc))
            create_extraction_run(
                conn,
                document_id=document_id,
                model_name=model_name,
                raw_response=raw_response,
                normalized_response=normalized,
                error_message=str(exc),
            )
        raise

    try:
        with get_conn() as conn:
            update_document_status(conn, document_id, "storing")
            document_type = normalized["invoice"]["invoice_type"]
            update_document_type(conn, document_id, document_type)
            client = get_or_create_client(
                conn,
                normalized["client"]["name_original"],
                normalized["client"]["name_normalized"],
                {
                    "street": normalized["client"]["street"],
                    "house_number": normalized["client"]["house_number"],
                    "postal_code": normalized["client"]["postal_code"],
                    "city": normalized["client"]["city"],
                },
                current_app.config["CLIENT_MATCH_THRESHOLD"],
            )
            duplicate_count = count_duplicate_invoice(
                conn,
                client["id"],
                normalized["invoice"]["invoice_number"],
                exclude_document_id=document_id,
            )
            delete_invoices_for_document(conn, document_id)
            invoice = create_invoice(conn, client["id"], document_id, normalized["invoice"])
            positions = replace_invoice_positions(conn, invoice["id"], normalized["invoice_pos"])

            create_extraction_run(
                conn,
                document_id=document_id,
                model_name=model_name,
                raw_response=raw_response,
                normalized_response=normalized,
                error_message=None,
            )

            validation_results = build_validation_results(
                document_id=document_id,
                invoice_id=invoice["id"],
                normalized=normalized,
                duplicate_count=duplicate_count,
                valid_invoice_types=current_app.config["VALID_INVOICE_TYPES"],
            )
            stored_validations = replace_validation_results(conn, document_id, invoice["id"], validation_results)
            document = update_document_status(conn, document_id, "completed")
            validation_summary = get_validation_summary(conn, document_id)
            current_app.logger.info(
                "Document extraction completed: document_id=%s invoice_id=%s invoice_number=%s pos_count=%s validation_failed=%s",
                document_id,
                invoice["id"],
                invoice["invoice_number"],
                len(positions),
                validation_summary["failed"],
            )
    except Exception as exc:
        current_app.logger.exception("Document storage or validation failed: document_id=%s", document_id)
        with get_conn() as conn:
            update_document_status(conn, document_id, "failed", str(exc))
            create_extraction_run(
                conn,
                document_id=document_id,
                model_name=model_name,
                raw_response=raw_response,
                normalized_response=normalized,
                error_message=str(exc),
            )
        raise

    return {
        "document": decimal_to_float(document),
        "client": client,
        "invoice": decimal_to_float(invoice),
        "invoice_pos": [decimal_to_float(row) for row in positions],
        "validation_summary": validation_summary,
        "validation_results": [decimal_to_float(row) for row in stored_validations],
        "normalized_response": serialize_normalized(normalized),
    }


def get_document_result(document_id: int, include_debug: bool = False) -> dict[str, Any]:
    with get_conn() as conn:
        document = get_document(conn, document_id)
        if not document:
            raise NotFound(f"Document {document_id} does not exist")

        invoice = get_invoice_for_document(conn, document_id)
        validation_summary = get_validation_summary(conn, document_id)
        latest_run_summary = conn.execute(
            """
            SELECT model_name, error_message
            FROM extraction_runs
            WHERE document_id = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (document_id,),
        ).fetchone()
        response: dict[str, Any] = {
            "document": decimal_to_float(document),
            "invoice": decimal_to_float(invoice) if invoice else None,
            "latest_extraction_run_summary": latest_run_summary,
            "validation_summary": validation_summary,
        }

        if include_debug:
            raw = conn.execute(
                """
                SELECT model_name, raw_response_json, normalized_response_json, error_message
                FROM extraction_runs
                WHERE document_id = %s
                ORDER BY id DESC
                LIMIT 1
                """,
                (document_id,),
            ).fetchone()
            response["latest_extraction_run"] = raw

        return response
