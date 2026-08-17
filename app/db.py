from contextlib import contextmanager
from threading import Lock
from typing import Iterator

import psycopg
from flask import Flask, current_app
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row

_schema_lock = Lock()
_schema_ready = False
_SCHEMA_LOCK_ID = 482913047126


def init_pool(app: Flask) -> None:
    app.extensions["db_pool"] = ConnectionPool(
        conninfo=app.config["POSTGRES_DSN"],
        min_size=app.config["POSTGRES_POOL_MIN_SIZE"],
        max_size=app.config["POSTGRES_POOL_MAX_SIZE"],
        kwargs={"row_factory": dict_row},
        open=False,
    )


@contextmanager
def get_conn() -> Iterator[psycopg.Connection]:
    pool: ConnectionPool = current_app.extensions["db_pool"]
    if pool.closed:
        pool.open(wait=False)

    conn_context = pool.connection()
    conn = conn_context.__enter__()
    try:
        ensure_schema_once(conn)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn_context.__exit__(None, None, None)


def ensure_schema_once(conn: psycopg.Connection) -> None:
    global _schema_ready
    with _schema_lock:
        if not _schema_ready or not _schema_exists(conn):
            _ensure_schema_with_advisory_lock(conn)
            _schema_ready = True


def _ensure_schema_with_advisory_lock(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT pg_advisory_lock(%s)", (_SCHEMA_LOCK_ID,))
    try:
        ensure_schema(conn)
    finally:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_unlock(%s)", (_SCHEMA_LOCK_ID,))


def _schema_exists(conn: psycopg.Connection) -> bool:
    required_tables = (
        "clients",
        "documents",
        "invoices",
        "invoice_pos",
        "extraction_runs",
        "validation_results",
    )
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) AS existing_count
            FROM unnest(%s::text[]) AS table_name
            WHERE to_regclass('public.' || table_name) IS NOT NULL
            """,
            (list(required_tables),),
        )
        return int(cur.fetchone()["existing_count"]) == len(required_tables)


def ensure_schema(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS clients (
                id BIGSERIAL PRIMARY KEY,
                name_original TEXT NOT NULL,
                name_normalized TEXT NOT NULL UNIQUE,
                street TEXT,
                house_number TEXT,
                postal_code TEXT,
                city TEXT,
                name_address_fingerprint TEXT
            );

            ALTER TABLE clients
            ADD COLUMN IF NOT EXISTS street TEXT;

            ALTER TABLE clients
            ADD COLUMN IF NOT EXISTS house_number TEXT;

            ALTER TABLE clients
            ADD COLUMN IF NOT EXISTS postal_code TEXT;

            ALTER TABLE clients
            ADD COLUMN IF NOT EXISTS city TEXT;

            ALTER TABLE clients
            ADD COLUMN IF NOT EXISTS name_address_fingerprint TEXT;

            CREATE INDEX IF NOT EXISTS idx_clients_name_address_fingerprint
            ON clients (name_address_fingerprint)
            WHERE name_address_fingerprint IS NOT NULL;

            CREATE TABLE IF NOT EXISTS documents (
                id BIGSERIAL PRIMARY KEY,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                document_type TEXT,
                processing_status TEXT NOT NULL DEFAULT 'pending',
                error_message TEXT
            );

            ALTER TABLE documents
            DROP CONSTRAINT IF EXISTS documents_file_hash_key;

            DROP TABLE IF EXISTS document_pages;

            ALTER TABLE documents
            DROP COLUMN IF EXISTS preprocessed_file_path;

            ALTER TABLE documents
            DROP COLUMN IF EXISTS page_count;

            ALTER TABLE documents
            ADD COLUMN IF NOT EXISTS processing_status TEXT NOT NULL DEFAULT 'pending';

            ALTER TABLE documents
            ADD COLUMN IF NOT EXISTS error_message TEXT;

            CREATE INDEX IF NOT EXISTS idx_documents_file_hash
            ON documents (file_hash);

            CREATE TABLE IF NOT EXISTS invoices (
                id BIGSERIAL PRIMARY KEY,
                client_id BIGINT NOT NULL REFERENCES clients(id),
                document_id BIGINT NOT NULL REFERENCES documents(id),
                invoice_number TEXT NOT NULL,
                invoice_date DATE,
                invoice_type TEXT,
                gesamt_netto NUMERIC(14, 2),
                tva NUMERIC(14, 2),
                gesamtbetrag NUMERIC(14, 2)
            );

            ALTER TABLE invoices
            DROP CONSTRAINT IF EXISTS invoices_client_id_invoice_number_key;

            CREATE INDEX IF NOT EXISTS idx_invoices_client_invoice_number
            ON invoices (client_id, invoice_number);

            CREATE TABLE IF NOT EXISTS invoice_pos (
                id BIGSERIAL PRIMARY KEY,
                invoice_id BIGINT NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
                pos_number INTEGER NOT NULL,
                gesamt_netto NUMERIC(14, 2),
                gesamtpreis NUMERIC(14, 2),
                UNIQUE (invoice_id, pos_number)
            );

            ALTER TABLE invoice_pos
            ADD COLUMN IF NOT EXISTS gesamt_netto NUMERIC(14, 2);

            CREATE TABLE IF NOT EXISTS extraction_runs (
                id BIGSERIAL PRIMARY KEY,
                document_id BIGINT NOT NULL REFERENCES documents(id),
                model_name TEXT NOT NULL,
                raw_response_json JSONB,
                normalized_response_json JSONB,
                error_message TEXT
            );

            CREATE TABLE IF NOT EXISTS validation_results (
                id BIGSERIAL PRIMARY KEY,
                document_id BIGINT NOT NULL REFERENCES documents(id),
                invoice_id BIGINT REFERENCES invoices(id) ON DELETE CASCADE,
                check_name TEXT NOT NULL,
                passed BOOLEAN NOT NULL,
                expected_value TEXT,
                actual_value TEXT
            );
            """
        )
