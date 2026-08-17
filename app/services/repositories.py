import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from psycopg import Connection

from app.services.normalization import serialize_normalized


def create_document(
    conn: Connection,
    file_name: str,
    file_path: Path,
    file_hash: str,
    document_type: str | None,
    processing_status: str = "pending",
    error_message: str | None = None,
) -> dict[str, Any]:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO documents (
                file_name, file_path, file_hash, document_type, processing_status, error_message
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                file_name,
                str(file_path),
                file_hash,
                document_type,
                processing_status,
                error_message,
            ),
        )
        return cur.fetchone()


def create_extraction_run(
    conn: Connection,
    document_id: int,
    model_name: str,
    raw_response: dict[str, Any] | None,
    normalized_response: dict[str, Any] | None,
    error_message: str | None,
) -> dict[str, Any]:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO extraction_runs (
                document_id, model_name, raw_response_json, normalized_response_json, error_message
            )
            VALUES (%s, %s, %s::jsonb, %s::jsonb, %s)
            RETURNING *
            """,
            (
                document_id,
                model_name,
                json.dumps(raw_response) if raw_response is not None else None,
                json.dumps(serialize_normalized(normalized_response)) if normalized_response is not None else None,
                error_message,
            ),
        )
        return cur.fetchone()


def get_document(conn: Connection, document_id: int) -> dict[str, Any] | None:
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM documents WHERE id = %s", (document_id,))
        return cur.fetchone()


def update_document_status(
    conn: Connection,
    document_id: int,
    processing_status: str,
    error_message: str | None = None,
) -> dict[str, Any]:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE documents
            SET processing_status = %s,
                error_message = %s
            WHERE id = %s
            RETURNING *
            """,
            (processing_status, error_message, document_id),
        )
        return cur.fetchone()


def update_document_type(conn: Connection, document_id: int, document_type: str | None) -> dict[str, Any]:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE documents
            SET document_type = %s
            WHERE id = %s
            RETURNING *
            """,
            (document_type, document_id),
        )
        return cur.fetchone()


def count_duplicate_invoice(
    conn: Connection,
    client_id: int,
    invoice_number: str | None,
    exclude_document_id: int | None = None,
) -> int:
    if not invoice_number:
        return 0
    with conn.cursor() as cur:
        extra_filter = "AND document_id <> %s" if exclude_document_id is not None else ""
        params = [client_id, invoice_number]
        if exclude_document_id is not None:
            params.append(exclude_document_id)
        cur.execute(
            f"""
            SELECT COUNT(*) AS count
            FROM invoices
            WHERE client_id = %s AND invoice_number = %s
            {extra_filter}
            """,
            params,
        )
        return int(cur.fetchone()["count"])


def delete_invoices_for_document(conn: Connection, document_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM invoices WHERE document_id = %s", (document_id,))


def create_invoice(conn: Connection, client_id: int, document_id: int, invoice: dict[str, Any]) -> dict[str, Any]:
    invoice_number = invoice["invoice_number"] or f"UNREADABLE-{document_id}"
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO invoices (
                client_id, document_id, invoice_number, invoice_date, invoice_type,
                gesamt_netto, tva, gesamtbetrag
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                client_id,
                document_id,
                invoice_number,
                invoice["invoice_date"],
                invoice["invoice_type"],
                invoice["gesamt_netto"],
                invoice["tva"],
                invoice["gesamtbetrag"],
            ),
        )
        return cur.fetchone()


def replace_invoice_positions(conn: Connection, invoice_id: int, positions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM invoice_pos WHERE invoice_id = %s", (invoice_id,))
        inserted = []
        for pos in positions:
            cur.execute(
                """
                INSERT INTO invoice_pos (invoice_id, pos_number, gesamt_netto, gesamtpreis)
                VALUES (%s, %s, %s, %s)
                RETURNING *
                """,
                (invoice_id, pos["pos_number"], pos["gesamt_netto"], pos["gesamtpreis"]),
            )
            inserted.append(cur.fetchone())
        return inserted


def replace_validation_results(
    conn: Connection,
    document_id: int,
    invoice_id: int | None,
    results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM validation_results WHERE document_id = %s", (document_id,))
        inserted = []
        for result in results:
            cur.execute(
                """
                INSERT INTO validation_results (
                    document_id, invoice_id, check_name, passed, expected_value, actual_value
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    result["document_id"],
                    result["invoice_id"],
                    result["check_name"],
                    result["passed"],
                    result["expected_value"],
                    result["actual_value"],
                ),
            )
            inserted.append(cur.fetchone())
        return inserted


def get_validation_summary(conn: Connection, document_id: int) -> dict[str, int | bool]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE passed) AS passed,
                COUNT(*) FILTER (WHERE NOT passed) AS failed
            FROM validation_results
            WHERE document_id = %s
            """,
            (document_id,),
        )
        row = cur.fetchone()
        failed = int(row["failed"] or 0)
        return {
            "total": int(row["total"] or 0),
            "passed": int(row["passed"] or 0),
            "failed": failed,
            "has_validation_errors": failed > 0,
        }


def get_invoice_for_document(conn: Connection, document_id: int) -> dict[str, Any] | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT *
            FROM invoices
            WHERE document_id = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (document_id,),
        )
        return cur.fetchone()


def decimal_to_float(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: _json_value(value)
        for key, value in row.items()
    }


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, date):
        return value.isoformat()
    return value
