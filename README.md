# Invoices OCR

Flask + React application for extracting scanned invoices, receipts, contracts, commission settlements, and credit notes into PostgreSQL using OpenAI vision extraction. Background extraction is handled with Celery and Redis.

## Local Setup

### 1. Requirements

Install these locally before running the app:

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- Redis
- OpenAI API key

On macOS with Homebrew:

```bash
brew install postgresql@14 redis node
```

Start PostgreSQL and Redis services if you installed them with Homebrew:

```bash
brew services start postgresql@14
brew services start redis
```

You can also run Redis manually in a terminal:

```bash
redis-server
```

### 2. Create The PostgreSQL Database

The application creates the database tables automatically, but the database itself must exist first.

Log into PostgreSQL:

```bash
psql postgres
```

Create a database and user. Change the password if needed:

```sql
CREATE DATABASE invoices_ocr;
CREATE USER invoices_user WITH PASSWORD 'change-me';
GRANT ALL PRIVILEGES ON DATABASE invoices_ocr TO invoices_user;
```

Connect to the new database and grant schema permissions:

```sql
\c invoices_ocr
GRANT ALL ON SCHEMA public TO invoices_user;
ALTER SCHEMA public OWNER TO invoices_user;
```

Exit PostgreSQL:

```sql
\q
```

If you prefer to use the default `postgres` user, you can skip creating `invoices_user` and configure `.env` with `POSTGRES_USER=postgres`.

### 3. Create The Backend Environment File

Copy the example file:

```bash
cp .env.example .env
```

Edit `.env` and set at least these values:

```ini
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_MODEL=gpt-5.6-sol
OPENAI_FILE_DETAIL=high

APP_USERNAME=admin
APP_PASSWORD=xciteinvoiceocr2026
SECRET_KEY=replace-with-a-long-random-value

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=invoices_ocr
POSTGRES_USER=invoices_user
POSTGRES_PASSWORD=change-me

CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### 4. Install Backend Dependencies

From the project root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 5. Verify Database Connectivity And Create Tables

Start Flask once:

```bash
source .venv/bin/activate
python run.py
```

In another terminal, ask the app to create/verify the schema:

```bash
curl -X POST http://localhost:5000/api/database/schema
```

The app also creates tables automatically before database operations, including extraction and insertion.

Stop Flask with `Ctrl+C` if you want to restart it in the next step.

### 6. Run The Backend Services

For normal local development, keep these three backend processes running in separate terminals.

Terminal 1, Flask API:

```bash
source .venv/bin/activate
python run.py
```

Flask runs at:

```text
http://localhost:5000
```

If port `5000` is busy:

```bash
flask --app run:app run --host 0.0.0.0 --port 6001
```

Terminal 2, Redis:

```bash
redis-server
```

If Redis is already running as a service, you do not need this terminal.

Terminal 3, Celery worker:

```bash
source .venv/bin/activate
celery -A celery_worker.celery worker --loglevel=INFO --concurrency=3
```

With `--concurrency=3`, up to three documents can be processed at the same time, subject to OpenAI rate limits.

### 7. Install And Run The React Frontend

Open a fourth terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at:

```text
http://localhost:5173
```

If Flask is not running on `http://localhost:5000`, create `frontend/.env`:

```ini
VITE_API_BASE_URL=http://localhost:6001
```

The local login defaults are controlled by the Flask backend:

```ini
APP_USERNAME=admin
APP_PASSWORD=xciteinvoiceocr2026
```

Then restart the frontend dev server.

### 8. Test The Local App

Open the frontend:

```text
http://localhost:5173
```

Use the UI to:

1. Upload one to three scanned PDF invoices.
2. Wait for extraction to finish.
3. Expand the tables.
4. Review invoice and invoice position rows.
5. Hover validation warnings to inspect failed checks.
6. Export the Excel files.

You can also check the backend directly:

```bash
curl http://localhost:5000/health
curl "http://localhost:5000/api/invoices?page=1&page_size=25"
curl "http://localhost:5000/api/invoice-pos?page=1&page_size=25"
```

## What Runs Where

- Flask API: accepts uploads, serves tables, exports Excel files, and exposes reset/debug endpoints.
- PostgreSQL: stores clients, documents, invoices, invoice positions, extraction runs, and validation results.
- Redis: message broker used by Celery.
- Celery worker: performs background OCR extraction and database insertion.
- React frontend: dashboard UI for login, upload, review, validation display, reset, language switching, and Excel export.

## API

Login and create a Flask session cookie:

```bash
curl -c cookies.txt \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"xciteinvoiceocr2026"}' \
  http://localhost:5000/api/auth/login
```

Use `-b cookies.txt` for protected API calls when testing with `curl`:

```bash
curl -b cookies.txt "http://localhost:5000/api/invoices?page=1&page_size=25"
```

Logout:

```bash
curl -b cookies.txt -X POST http://localhost:5000/api/auth/logout
```

Upload a scanned PDF and start background processing:

```bash
curl -X POST http://localhost:5000/api/documents \
  -F "file=@/path/to/invoice.pdf"
```

The response returns immediately with `202 Accepted`, a `document.id`, and links for polling.

Upload without starting processing:

```bash
curl -X POST "http://localhost:5000/api/documents?auto_process=false" \
  -F "file=@/path/to/invoice.pdf"
```

Upload multiple PDFs and queue all of them:

```bash
curl -X POST http://localhost:5000/api/documents/bulk \
  -F "files=@/path/to/invoice-1.pdf" \
  -F "files=@/path/to/invoice-2.pdf" \
  -F "files=@/path/to/invoice-3.pdf"
```

Start or restart processing for an uploaded document:

```bash
curl -X POST http://localhost:5000/api/documents/1/process
```

Poll document status/results:

```bash
curl http://localhost:5000/api/documents/1
```

View tables as JSON:

```bash
curl "http://localhost:5000/api/documents?page=1&page_size=25"
curl "http://localhost:5000/api/invoices?page=1&page_size=25"
curl "http://localhost:5000/api/invoice-pos?page=1&page_size=25"
```

Useful invoice filters:

```bash
curl "http://localhost:5000/api/invoices?invoice_type=commission_settlement"
curl "http://localhost:5000/api/invoices?has_validation_errors=true"
curl "http://localhost:5000/api/invoices?client_id=1"
```

Verify/create the database schema without uploading a document:

```bash
curl -X POST http://localhost:5000/api/database/schema
```

Export the combined Lexware-oriented review/import file:

```bash
curl -o lexware_invoice_review.xlsx http://localhost:5000/api/exports/lexware_invoice_review.xlsx
```

The combined export contains each invoice row followed by its nested invoice position header and position rows. It includes German headers such as `Rechnungs-ID` and `Rechnungsnummer` so repeated extractions of the same client/invoice number can still be distinguished.

View validation results:

```bash
curl http://localhost:5000/api/documents/1/validation-results
curl http://localhost:5000/api/invoices/1/validation-results
```

Debug latest raw/normalized extraction response:

```bash
curl http://localhost:5000/api/documents/1/debug
```

## Frontend Notes

The backend is prepared for a React frontend running on Vite or Create React App defaults:

```text
http://localhost:5173
http://localhost:3000
```

Configure allowed origins with `CORS_ORIGINS` in `.env`.

Recommended React flow:

```text
POST /api/auth/login
-> browser receives Flask session cookie
POST /api/documents
-> read document.id
-> poll GET /api/documents/:id until document.processing_status is completed or failed
-> load GET /api/invoices and GET /api/invoice-pos for table views
-> use /api/exports/lexware_invoice_review.xlsx for the combined Excel download
```
