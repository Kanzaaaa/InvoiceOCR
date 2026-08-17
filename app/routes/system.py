from flask import Blueprint, jsonify

from app.db import get_conn

system_bp = Blueprint("system", __name__)


@system_bp.post("/database/schema")
def ensure_database_schema():
    with get_conn() as conn:
        table_names = conn.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name IN (
                'clients',
                'documents',
                'invoices',
                'invoice_pos',
                'extraction_runs',
                'validation_results'
              )
            ORDER BY table_name
            """
        ).fetchall()

    return jsonify(
        {
            "status": "ok",
            "message": "Database schema is available",
            "tables": [row["table_name"] for row in table_names],
        }
    )


@system_bp.delete("/database/data")
def clear_database_data():
    with get_conn() as conn:
        conn.execute(
            """
            TRUNCATE TABLE
                validation_results,
                extraction_runs,
                invoice_pos,
                invoices,
                clients,
                documents
            RESTART IDENTITY CASCADE
            """
        )

    return jsonify(
        {
            "status": "ok",
            "message": "Extracted invoice data was deleted",
            "tables": [
                "validation_results",
                "extraction_runs",
                "invoice_pos",
                "invoices",
                "clients",
                "documents",
            ],
        }
    )
