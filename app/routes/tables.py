from flask import Blueprint, jsonify, request

from app.db import get_conn
from app.services.repositories import decimal_to_float

tables_bp = Blueprint("tables", __name__)


@tables_bp.get("/invoices")
def list_invoices():
    page, page_size, offset = _pagination()
    filters = []
    params = []

    if request.args.get("client_id"):
        filters.append("i.client_id = %s")
        params.append(int(request.args["client_id"]))
    if request.args.get("invoice_type"):
        filters.append("i.invoice_type = %s")
        params.append(request.args["invoice_type"])
    if request.args.get("has_validation_errors") in {"true", "1", "yes"}:
        filters.append("COALESCE(v.failed_count, 0) > 0")
    elif request.args.get("has_validation_errors") in {"false", "0", "no"}:
        filters.append("COALESCE(v.failed_count, 0) = 0")

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT
                i.id,
                i.client_id,
                c.name_original AS client_name,
                c.name_normalized AS client_name_normalized,
                c.street AS client_street,
                c.house_number AS client_house_number,
                c.postal_code AS client_postal_code,
                c.city AS client_city,
                i.document_id,
                d.file_name AS document_file_name,
                i.invoice_number,
                i.invoice_date,
                i.invoice_type,
                i.gesamt_netto,
                i.tva,
                i.gesamtbetrag,
                COALESCE(v.total_count, 0) AS validation_total,
                COALESCE(v.passed_count, 0) AS validation_passed,
                COALESCE(v.failed_count, 0) AS validation_failed,
                COALESCE(v.failed_count, 0) > 0 AS has_validation_errors,
                COALESCE(vf.validation_errors, '[]'::jsonb) AS validation_errors
            FROM invoices i
            JOIN clients c ON c.id = i.client_id
            JOIN documents d ON d.id = i.document_id
            LEFT JOIN (
                SELECT
                    invoice_id,
                    COUNT(*) AS total_count,
                    COUNT(*) FILTER (WHERE passed) AS passed_count,
                    COUNT(*) FILTER (WHERE NOT passed) AS failed_count
                FROM validation_results
                GROUP BY invoice_id
            ) v ON v.invoice_id = i.id
            LEFT JOIN LATERAL (
                SELECT jsonb_agg(
                    jsonb_build_object(
                        'check_name', vr.check_name,
                        'expected_value', vr.expected_value,
                        'actual_value', vr.actual_value
                    )
                    ORDER BY vr.id
                ) AS validation_errors
                FROM validation_results vr
                WHERE vr.invoice_id = i.id AND NOT vr.passed
            ) vf ON TRUE
            {where_clause}
            ORDER BY i.id
            LIMIT %s OFFSET %s
            """,
            (*params, page_size, offset),
        ).fetchall()
    return jsonify(_page_response([decimal_to_float(row) for row in rows], page, page_size))


@tables_bp.get("/invoice-pos")
def list_invoice_pos():
    page, page_size, offset = _pagination()
    filters = []
    params = []

    if request.args.get("invoice_id"):
        filters.append("p.invoice_id = %s")
        params.append(int(request.args["invoice_id"]))
    if request.args.get("client_id"):
        filters.append("i.client_id = %s")
        params.append(int(request.args["client_id"]))

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT
                p.id,
                p.invoice_id,
                i.client_id,
                i.invoice_number,
                c.name_original AS client_name,
                i.invoice_date,
                p.pos_number,
                p.gesamt_netto,
                p.gesamtpreis
            FROM invoice_pos p
            JOIN invoices i ON i.id = p.invoice_id
            JOIN clients c ON c.id = i.client_id
            {where_clause}
            ORDER BY p.invoice_id, p.pos_number
            LIMIT %s OFFSET %s
            """,
            (*params, page_size, offset),
        ).fetchall()
    return jsonify(_page_response([decimal_to_float(row) for row in rows], page, page_size))


@tables_bp.get("/documents")
def list_documents():
    page, page_size, offset = _pagination()
    filters = []
    params = []

    if request.args.get("processing_status"):
        filters.append("d.processing_status = %s")
        params.append(request.args["processing_status"])
    if request.args.get("document_type"):
        filters.append("d.document_type = %s")
        params.append(request.args["document_type"])

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT
                d.*,
                i.id AS invoice_id,
                i.invoice_number,
                r.model_name AS latest_extraction_model,
                COALESCE(v.total_count, 0) AS validation_total,
                COALESCE(v.passed_count, 0) AS validation_passed,
                COALESCE(v.failed_count, 0) AS validation_failed,
                COALESCE(v.failed_count, 0) > 0 AS has_validation_errors
            FROM documents d
            LEFT JOIN LATERAL (
                SELECT *
                FROM invoices
                WHERE document_id = d.id
                ORDER BY id DESC
                LIMIT 1
            ) i ON TRUE
            LEFT JOIN LATERAL (
                SELECT model_name
                FROM extraction_runs
                WHERE document_id = d.id
                ORDER BY id DESC
                LIMIT 1
            ) r ON TRUE
            LEFT JOIN (
                SELECT
                    document_id,
                    COUNT(*) AS total_count,
                    COUNT(*) FILTER (WHERE passed) AS passed_count,
                    COUNT(*) FILTER (WHERE NOT passed) AS failed_count
                FROM validation_results
                GROUP BY document_id
            ) v ON v.document_id = d.id
            {where_clause}
            ORDER BY d.id DESC
            LIMIT %s OFFSET %s
            """,
            (*params, page_size, offset),
        ).fetchall()
    return jsonify(_page_response([decimal_to_float(row) for row in rows], page, page_size))


@tables_bp.get("/documents/<int:document_id>/validation-results")
def list_document_validation_results(document_id: int):
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM validation_results
            WHERE document_id = %s
            ORDER BY id
            """,
            (document_id,),
        ).fetchall()
    return jsonify(rows)


@tables_bp.get("/invoices/<int:invoice_id>/validation-results")
def list_invoice_validation_results(invoice_id: int):
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM validation_results
            WHERE invoice_id = %s
            ORDER BY id
            """,
            (invoice_id,),
        ).fetchall()
    return jsonify(rows)


def _pagination() -> tuple[int, int, int]:
    page = max(int(request.args.get("page", 1)), 1)
    page_size = min(max(int(request.args.get("page_size", 25)), 1), 100)
    return page, page_size, (page - 1) * page_size


def _page_response(items: list[dict], page: int, page_size: int) -> dict:
    return {
        "items": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "returned": len(items),
        },
    }
