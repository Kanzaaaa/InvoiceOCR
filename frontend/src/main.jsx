import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  FileSpreadsheet,
  Filter,
  Info,
  Loader2,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import "./styles.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000";
const API_PAGE_SIZE = 100;
const INVOICE_TABLE_PAGE_SIZE = 8;
const POSITION_TABLE_PAGE_SIZE = 5;
const MAX_UPLOAD_FILES = 3;
const PROCESSING_POLL_MS = 2000;
const PROCESSING_MAX_POLLS = 90;

function createUploadSlots() {
  return Array.from({ length: MAX_UPLOAD_FILES }, () => ({ id: crypto.randomUUID(), file: null }));
}

const invoiceColumns = [
  { key: "id", label: "invoice_id", align: "center", width: 120, minWidth: 95 },
  { key: "invoice_number", label: "invoice_number", width: 170, minWidth: 130 },
  { key: "document_file_name", label: "Dateiname", width: 470, minWidth: 220 },
  { key: "client_name", label: "Kunde/Lieferant", width: 560, minWidth: 240 },
  { key: "client_street", label: "street", width: 190, minWidth: 140 },
  { key: "client_house_number", label: "house_number", width: 150, minWidth: 120 },
  { key: "client_postal_code", label: "postal_code", width: 140, minWidth: 115 },
  { key: "client_city", label: "city", width: 170, minWidth: 125 },
  { key: "invoice_type", label: "Dokumenttyp", width: 190, minWidth: 150 },
  { key: "invoice_date", label: "Belegdatum", width: 150, minWidth: 125 },
  { key: "gesamt_netto", label: "Netto", align: "right", type: "amount", width: 140, minWidth: 110 },
  { key: "tva", label: "USt", align: "right", type: "amount", width: 120, minWidth: 95 },
  { key: "gesamtbetrag", label: "Brutto", align: "right", type: "amount", width: 140, minWidth: 110 },
  { key: "validation_failed", label: "Validierungsfehler", align: "center", type: "validation", width: 170, minWidth: 140 },
];

const posColumns = [
  { key: "invoice_id", label: "invoice_id", align: "center", width: 120, minWidth: 95 },
  { key: "invoice_number", label: "invoice_number", width: 170, minWidth: 130 },
  { key: "client_name", label: "Kunde/Lieferant", width: 430, minWidth: 220 },
  { key: "invoice_date", label: "Belegdatum", width: 150, minWidth: 125 },
  { key: "pos_number", label: "Position", align: "center", width: 130, minWidth: 100 },
  { key: "gesamt_netto", label: "Positions-Netto", align: "right", type: "amount", width: 170, minWidth: 135 },
  { key: "gesamtpreis", label: "Positions-Brutto", align: "right", type: "amount", width: 180, minWidth: 145 },
];

function App() {
  const [invoices, setInvoices] = useState([]);
  const [positions, setPositions] = useState([]);
  const [selectedClientId, setSelectedClientId] = useState("all");
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [invoicePage, setInvoicePage] = useState(1);
  const [positionPage, setPositionPage] = useState(1);
  const [uploadSlots, setUploadSlots] = useState(() => createUploadSlots());
  const [processingMessage, setProcessingMessage] = useState("");
  const [processingIds, setProcessingIds] = useState([]);
  const [dragActiveSlotId, setDragActiveSlotId] = useState("");
  const [tablesExpanded, setTablesExpanded] = useState(false);
  const [resetModalOpen, setResetModalOpen] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [validationDetailsByInvoiceId, setValidationDetailsByInvoiceId] = useState({});

  const clients = useMemo(() => {
    const byId = new Map();
    for (const invoice of invoices) {
      byId.set(String(invoice.client_id), invoice.client_name);
    }
    return Array.from(byId, ([id, name]) => ({ id, name })).sort((a, b) => a.name.localeCompare(b.name));
  }, [invoices]);

  const filteredInvoices = useMemo(() => {
    if (selectedClientId === "all") {
      return invoices;
    }
    return invoices.filter((invoice) => String(invoice.client_id) === selectedClientId);
  }, [invoices, selectedClientId]);

  const filteredPositions = useMemo(() => {
    if (selectedClientId === "all") {
      return positions;
    }
    return positions.filter((position) => String(position.client_id) === selectedClientId);
  }, [positions, selectedClientId]);

  const exportAllowed = selectedClientId === "all" || clients.length <= 1;
  const failedInvoices = filteredInvoices.filter((invoice) => invoice.has_validation_errors).length;
  const selectedFiles = uploadSlots.map((slot) => slot.file).filter(Boolean);
  const uploadDisabled = selectedFiles.length === 0 || uploading || processingIds.length > 0;
  const hasExtractedData = invoices.length > 0 || positions.length > 0 || clients.length > 0;

  useEffect(() => {
    loadTables({ initial: true });
  }, []);

  useEffect(() => {
    setInvoicePage(1);
    setPositionPage(1);
  }, [selectedClientId]);

  async function loadTables({ initial = false } = {}) {
    setError("");
    if (initial) {
      setLoading(true);
    }

    const [invoiceResult, positionResult] = await Promise.allSettled([
      fetchAllPages("/api/invoices"),
      fetchAllPages("/api/invoice-pos"),
    ]);

    try {
      if (invoiceResult.status === "rejected" && positionResult.status === "rejected") {
        throw new Error("Unable to load table data. Check that the Flask API and database are running.");
      }

      const invoiceRows = invoiceResult.status === "fulfilled" ? invoiceResult.value : [];
      const positionRows = positionResult.status === "fulfilled" ? positionResult.value : [];
      setInvoices(invoiceRows);
      setPositions(positionRows);
    } catch (err) {
      setError(err.message || "Unable to load invoice data.");
    } finally {
      setLoading(false);
    }
  }

  async function fetchAllPages(path) {
    const items = [];
    let page = 1;

    while (true) {
      const response = await fetch(`${API_BASE_URL}${path}?page=${page}&page_size=${API_PAGE_SIZE}`);
      if (!response.ok) {
        throw new Error("Table request failed.");
      }
      const payload = await response.json();
      items.push(...payload.items);
      if (payload.pagination.returned < API_PAGE_SIZE) {
        break;
      }
      page += 1;
    }

    return items;
  }

  function updateUploadSlot(slotId, file) {
    setUploadSlots((slots) => slots.map((slot) => (slot.id === slotId ? { ...slot, file } : slot)));
  }

  function validPdfFiles(fileList) {
    return Array.from(fileList || []).filter((file) => {
      const name = file.name.toLowerCase();
      return file.type === "application/pdf" || name.endsWith(".pdf");
    });
  }

  function appendUploadFiles(fileList) {
    const pdfFiles = validPdfFiles(fileList);

    if (pdfFiles.length === 0) {
      setError("Only PDF files can be uploaded.");
      return;
    }

    setError("");
    setUploadSlots((slots) => {
      const nextSlots = slots.map((slot) => ({ ...slot }));
      let fileIndex = 0;

      for (const slot of nextSlots) {
        if (!slot.file && fileIndex < pdfFiles.length) {
          slot.file = pdfFiles[fileIndex];
          fileIndex += 1;
        }
      }

      for (const slot of nextSlots) {
        if (fileIndex >= pdfFiles.length) {
          break;
        }
        slot.file = pdfFiles[fileIndex];
        fileIndex += 1;
      }

      return nextSlots;
    });
  }

  function clearUploadSlot(slotId) {
    updateUploadSlot(slotId, null);
  }

  function handleUploadDragOver(event) {
    event.preventDefault();
    event.stopPropagation();
    if (uploading || processingIds.length > 0) {
      return;
    }
  }

  function handleUploadDragLeave(event) {
    event.preventDefault();
    event.stopPropagation();
    setDragActiveSlotId("");
  }

  function handleUploadDrop(event) {
    event.preventDefault();
    event.stopPropagation();
    setDragActiveSlotId("");
    if (uploading || processingIds.length > 0) {
      return;
    }
    appendUploadFiles(event.dataTransfer.files);
  }

  function handleSlotDragOver(event, slotId) {
    event.preventDefault();
    event.stopPropagation();
    if (uploading || processingIds.length > 0) {
      return;
    }
    setDragActiveSlotId(slotId);
  }

  function handleSlotDrop(event, slotId) {
    event.preventDefault();
    event.stopPropagation();
    setDragActiveSlotId("");
    if (uploading || processingIds.length > 0) {
      return;
    }

    const [file] = validPdfFiles(event.dataTransfer.files);
    if (!file) {
      setError("Only PDF files can be uploaded.");
      return;
    }

    setError("");
    updateUploadSlot(slotId, file);
  }

  async function uploadSelectedFiles() {
    const files = selectedFiles;
    if (files.length === 0) {
      return;
    }

    setUploading(true);
    setNotice("");
    setError("");

    try {
      const formData = new FormData();
      const endpoint = files.length === 1 ? "/api/documents" : "/api/documents/bulk";
      const key = files.length === 1 ? "file" : "files";
      for (const file of files) {
        formData.append(key, file);
      }

      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "POST",
        body: formData,
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error || "Upload failed.");
      }

      const count = files.length === 1 ? 1 : payload.count;
      const documentIds = files.length === 1
        ? [payload.document.id]
        : payload.documents.map((document) => document.id);
      setUploadSlots(createUploadSlots());
      setProcessingIds(documentIds);
      setProcessingMessage(`Processing ${count} invoice${count === 1 ? "" : "s"}...`);
      setNotice(`${count} invoice${count === 1 ? "" : "s"} queued for extraction.`);
      await loadTables();
      await pollProcessing(documentIds);
    } catch (err) {
      setError(err.message || "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  async function pollProcessing(documentIds) {
    for (let attempt = 0; attempt < PROCESSING_MAX_POLLS; attempt += 1) {
      await wait(PROCESSING_POLL_MS);

      const statuses = await Promise.allSettled(
        documentIds.map(async (documentId) => {
          const response = await fetch(`${API_BASE_URL}/api/documents/${documentId}`);
          if (!response.ok) {
            throw new Error("Document status request failed.");
          }
          const payload = await response.json();
          return payload.document.processing_status;
        }),
      );

      const resolvedStatuses = statuses
        .filter((status) => status.status === "fulfilled")
        .map((status) => status.value);
      const finishedCount = resolvedStatuses.filter((status) => status === "completed" || status === "failed").length;
      setProcessingMessage(`Processing invoices... ${finishedCount}/${documentIds.length} finished`);

      if (resolvedStatuses.length === documentIds.length && finishedCount === documentIds.length) {
        await loadTables();
        setProcessingIds([]);
        setProcessingMessage("");
        setNotice("Extraction finished. Tables are updated.");
        return;
      }

      if (attempt % 3 === 2) {
        await loadTables();
      }
    }

    setProcessingIds([]);
    setProcessingMessage("");
    setNotice("Processing is still running. The tables will update after the next completed extraction.");
  }

  function downloadExport(path) {
    window.location.href = `${API_BASE_URL}${path}`;
  }

  async function loadValidationDetails(invoiceId) {
    if (!invoiceId) {
      return;
    }
    const cacheKey = String(invoiceId);
    const current = validationDetailsByInvoiceId[cacheKey];
    if (current?.loading || current?.loaded) {
      return;
    }

    setValidationDetailsByInvoiceId((details) => ({
      ...details,
      [cacheKey]: { loading: true, loaded: false, error: "", items: [] },
    }));

    try {
      const response = await fetch(`${API_BASE_URL}/api/invoices/${invoiceId}/validation-results`);
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error || "Unable to load validation results.");
      }
      setValidationDetailsByInvoiceId((details) => ({
        ...details,
        [cacheKey]: { loading: false, loaded: true, error: "", items: payload },
      }));
    } catch (err) {
      setValidationDetailsByInvoiceId((details) => ({
        ...details,
        [cacheKey]: { loading: false, loaded: false, error: err.message || "Unable to load validation results.", items: [] },
      }));
    }
  }

  async function resetExtractedTables() {
    setResetting(true);
    setError("");
    setNotice("");

    try {
      const response = await fetch(`${API_BASE_URL}/api/database/data`, {
        method: "DELETE",
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error || "Unable to delete extracted tables.");
      }

      setInvoices([]);
      setPositions([]);
      setSelectedClientId("all");
      setInvoicePage(1);
      setPositionPage(1);
      setTablesExpanded(false);
      setResetModalOpen(false);
      setNotice("Extracted tables were deleted. You can start the process again.");
    } catch (err) {
      setError(err.message || "Unable to delete extracted tables.");
    } finally {
      setResetting(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="page-header">
        <h1>
          <span>HEDSOFT</span> - Dashboard - Invoice OCR Extraction
        </h1>
        <p>
          Upload scanned invoice PDFs, extract accounting fields with OCR, review validation results, and export
          Lexware-ready invoice and position tables.
        </p>
      </section>

      {(error || notice) && (
        <section className={`status-strip ${error ? "error" : "success"}`}>
          {error ? <AlertCircle size={18} /> : <CheckCircle2 size={18} />}
          <span>{error || notice}</span>
          <button type="button" onClick={() => (error ? setError("") : setNotice(""))} aria-label="Dismiss">
            <X size={16} />
          </button>
        </section>
      )}

      <section className="overview-card" aria-label="Application overview">
        <h2>Overview</h2>
        <div className="summary-row">
          <SummaryTile label="Invoices" value={filteredInvoices.length} />
          <SummaryTile label="Positions" value={filteredPositions.length} />
          <SummaryTile label="Clients" value={selectedClientId === "all" ? clients.length : 1} />
          <SummaryTile label="Validation Issues" value={failedInvoices} tone={failedInvoices > 0 ? "warning" : "ok"} />
        </div>
        <div className="overview-divider" />
        <div className="overview-body">
          <div>
            <h3>How to use this dashboard</h3>
            <p>
              Upload up to three scanned PDF invoices, wait for OCR extraction to finish, review the invoice and
              position tables, check validation issues when the warning icon appears, then export the Lexware-ready
              Excel files.
            </p>
          </div>
          <div className="overview-steps" aria-label="Workflow steps">
            <span>Upload</span>
            <span>Extract</span>
            <span>Review</span>
            <span>Export</span>
          </div>
        </div>
      </section>

      <section className="upload-panel">
        <div className="panel-heading">
          <div>
            <h2>Invoice Upload</h2>
            <p>Upload up to 3 scanned PDF invoices.</p>
          </div>
        </div>

        <div
          className={dragActiveSlotId ? "upload-dropzone drag-active" : "upload-dropzone"}
          onDragOver={handleUploadDragOver}
          onDragEnter={handleUploadDragOver}
          onDragLeave={handleUploadDragLeave}
          onDrop={handleUploadDrop}
        >
          <div className="upload-slots">
            {uploadSlots.map((slot, index) => (
              <div
                className={dragActiveSlotId === slot.id ? "file-slot slot-drag-active" : "file-slot"}
                key={slot.id}
                onDragOver={(event) => handleSlotDragOver(event, slot.id)}
                onDragEnter={(event) => handleSlotDragOver(event, slot.id)}
                onDragLeave={handleUploadDragLeave}
                onDrop={(event) => handleSlotDrop(event, slot.id)}
              >
                <Upload size={24} />
                <label htmlFor={`invoice-file-${slot.id}`}>
                  <strong>{slot.file ? slot.file.name : `PDF ${index + 1}`}</strong>
                  <span>{slot.file ? "Drag another PDF here to replace it" : "PDF hereher ziehen oder klicken"}</span>
                </label>
                <input
                  id={`invoice-file-${slot.id}`}
                  type="file"
                  accept="application/pdf,.pdf"
                  onChange={(event) => updateUploadSlot(slot.id, event.target.files?.[0] || null)}
                  disabled={uploading || processingIds.length > 0}
                />
                {slot.file && (
                  <button type="button" className="slot-remove" onClick={() => clearUploadSlot(slot.id)} aria-label="Clear upload field">
                    <X size={15} />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="upload-actions">
          <button className="primary-button" type="button" onClick={uploadSelectedFiles} disabled={uploadDisabled}>
            {uploading || processingIds.length > 0 ? <Loader2 size={18} className="spin" /> : <Upload size={18} />}
            <span>Start Upload</span>
          </button>
        </div>
      </section>

      <section className={tablesExpanded ? "hierarchy-panel expanded" : "hierarchy-panel"}>
        <div className="hierarchy-header">
          <div className="hierarchy-level client-level">
            <button
              className="client-disclosure"
              type="button"
              aria-expanded={tablesExpanded}
              aria-label={tablesExpanded ? "Hide invoice tables" : "Show invoice tables"}
              onClick={() => setTablesExpanded((expanded) => !expanded)}
              title={tablesExpanded ? "Hide tables" : "Show tables"}
            >
              <ChevronDown size={19} className={tablesExpanded ? "disclosure-icon open" : "disclosure-icon"} />
            </button>
            <div className="client-filter">
              <div className="select-wrap">
                <Filter size={16} className="select-filter-icon" />
                <select
                  id="client-filter"
                  aria-label="Filter invoices by client"
                  value={selectedClientId}
                  onChange={(event) => setSelectedClientId(event.target.value)}
                >
                  <option value="all">All clients</option>
                  {clients.map((client) => (
                    <option key={client.id} value={client.id}>
                      {client.name}
                    </option>
                  ))}
                </select>
                <ChevronDown size={17} className="select-chevron" />
              </div>
            </div>
          </div>

          <div className="hierarchy-summary">
            <span>{filteredInvoices.length} invoices</span>
            <span>{filteredPositions.length} positions</span>
          </div>
        </div>

        <div className={tablesExpanded ? "tables-collapse open" : "tables-collapse"} aria-hidden={!tablesExpanded}>
          <div className="tables-collapse-inner">
            <DataSection
              title="Invoice"
              rows={filteredInvoices}
              columns={invoiceColumns}
              loading={loading}
              exportVisible={exportAllowed}
              onExport={() => downloadExport("/api/exports/lexware_invoice_review.xlsx")}
              exportTitle="combined invoice review"
              page={invoicePage}
              onPageChange={setInvoicePage}
              pageSize={INVOICE_TABLE_PAGE_SIZE}
              validationDetailsByInvoiceId={validationDetailsByInvoiceId}
              onLoadValidationDetails={loadValidationDetails}
            />

            <DataSection
              title="Invoice POS"
              rows={filteredPositions}
              columns={posColumns}
              loading={loading}
              exportVisible={false}
              page={positionPage}
              onPageChange={setPositionPage}
              pageSize={POSITION_TABLE_PAGE_SIZE}
              compact
            />
          </div>
        </div>
      </section>

      <section className="reset-section" aria-label="Reset extracted tables">
        <div>
          <h2>Reset Process</h2>
          <p>Delete all extracted database rows before starting a new test run.</p>
        </div>
        <button
          className="danger-icon-button"
          type="button"
          onClick={() => setResetModalOpen(true)}
          disabled={!hasExtractedData || uploading || processingIds.length > 0 || resetting}
          title={hasExtractedData ? "Delete extracted tables" : "No extracted data to delete"}
        >
          <Trash2 size={20} />
        </button>
      </section>

      {resetModalOpen && (
        <div className="modal-backdrop" role="presentation">
          <section className="confirm-modal" role="dialog" aria-modal="true" aria-labelledby="reset-title">
            <div className="modal-icon">
              <Trash2 size={22} />
            </div>
            <h2 id="reset-title">Delete extracted tables?</h2>
            <p>Are you sure you want to repeat the process again and delete the tables?</p>
            <div className="modal-actions">
              <button className="modal-secondary" type="button" onClick={() => setResetModalOpen(false)} disabled={resetting}>
                No
              </button>
              <button className="modal-danger" type="button" onClick={resetExtractedTables} disabled={resetting}>
                {resetting ? <Loader2 size={16} className="spin" /> : <Trash2 size={16} />}
                <span>Yes, delete</span>
              </button>
            </div>
          </section>
        </div>
      )}

      {(uploading || processingIds.length > 0) && (
        <div className="processing-screen" role="alert" aria-live="assertive" aria-busy="true">
          <section className="processing-card" aria-label="Invoice processing">
            <div className="processing-spinner">
              <Loader2 size={42} className="spin" />
            </div>
            <h2>Processing invoices</h2>
            <p>{processingMessage || "Your request is being processed. Please wait until extraction finishes."}</p>
          </section>
        </div>
      )}
    </main>
  );
}

function wait(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function SummaryTile({ label, value, tone }) {
  return (
    <div className={`summary-tile ${tone || ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function DataSection({
  title,
  rows,
  columns,
  loading,
  exportVisible,
  onExport,
  exportTitle,
  page,
  onPageChange,
  pageSize,
  compact = false,
  validationDetailsByInvoiceId = {},
  onLoadValidationDetails,
}) {
  const [columnWidths, setColumnWidths] = useState(() =>
    Object.fromEntries(columns.map((column) => [column.key, column.width || 160])),
  );
  const totalPages = Math.max(Math.ceil(rows.length / pageSize), 1);
  const safePage = Math.min(page, totalPages);
  const startIndex = (safePage - 1) * pageSize;
  const visibleRows = rows.slice(startIndex, startIndex + pageSize);
  const tableWidth = columns.reduce((total, column) => total + (columnWidths[column.key] || column.width || 160), 0);

  function startColumnResize(event, column) {
    event.preventDefault();
    event.stopPropagation();

    const startX = event.clientX;
    const startWidth = columnWidths[column.key] || column.width || 160;
    const minWidth = column.minWidth || 90;

    document.body.classList.add("is-resizing-column");

    function handlePointerMove(moveEvent) {
      const nextWidth = Math.max(minWidth, startWidth + moveEvent.clientX - startX);
      setColumnWidths((current) => ({
        ...current,
        [column.key]: nextWidth,
      }));
    }

    function stopColumnResize() {
      document.body.classList.remove("is-resizing-column");
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", stopColumnResize);
    }

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", stopColumnResize);
  }

  return (
    <section className={`table-section ${compact ? "compact-section" : ""}`}>
      <div className="table-titlebar">
        <div>
          <h2>{title}</h2>
          <p>{rows.length} rows</p>
        </div>
        <div className="settings-area">
          {exportVisible && (
            <button
              className="table-action"
              type="button"
              onClick={onExport}
              title={`Export ${exportTitle || title} Excel`}
              aria-label={`Export ${exportTitle || title} Excel`}
            >
              <FileSpreadsheet size={18} />
            </button>
          )}
        </div>
      </div>

      <div className="table-shell">
        <table style={{ width: `${tableWidth}px` }}>
          <colgroup>
            {columns.map((column) => (
              <col key={column.key} style={{ width: `${columnWidths[column.key] || column.width || 160}px` }} />
            ))}
          </colgroup>
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column.key} className="resizable-column">
                  <span>{column.label}</span>
                  <button
                    className="column-resizer"
                    type="button"
                    aria-label={`Resize ${column.label} column`}
                    onPointerDown={(event) => startColumnResize(event, column)}
                  />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={columns.length} className="empty-cell">
                  <Loader2 size={18} className="spin" />
                  Loading data
                </td>
              </tr>
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="empty-cell">
                  No rows to display
                </td>
              </tr>
            ) : (
              visibleRows.map((row) => (
                <tr key={`${title}-${row.id || row.invoice_id}-${row.pos_number || ""}`}>
                  {columns.map((column) => (
                    <td key={column.key} className={column.type === "validation" ? "validation-cell" : ""}>
                      {column.type === "validation" ? (
                        <ValidationIssuesCell
                          count={Number(row[column.key]) || 0}
                          details={validationDetailsByInvoiceId[String(row.id)]}
                          invoiceId={row.id}
                          onLoad={onLoadValidationDetails}
                        />
                      ) : (
                        formatCell(row[column.key], column, row)
                      )}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <Pagination
        page={safePage}
        totalPages={totalPages}
        totalRows={rows.length}
        onPageChange={onPageChange}
      />
    </section>
  );
}

function Pagination({ page, totalPages, totalRows, onPageChange }) {
  const pages = paginationRange(page, totalPages);
  const canGoBack = page > 1;
  const canGoForward = page < totalPages;

  return (
    <div className="pagination-bar">
      <span>
        Page {page} of {totalPages} · {totalRows} rows
      </span>
      <div className="pagination-actions">
        <button type="button" onClick={() => onPageChange(page - 1)} disabled={!canGoBack}>
          Previous
        </button>
        {pages.map((item, index) =>
          item === "ellipsis" ? (
            <span key={`${item}-${index}`} className="ellipsis">
              ...
            </span>
          ) : (
            <button
              key={item}
              type="button"
              className={item === page ? "active" : ""}
              onClick={() => onPageChange(item)}
            >
              {item}
            </button>
          ),
        )}
        <button type="button" onClick={() => onPageChange(page + 1)} disabled={!canGoForward}>
          Next
        </button>
      </div>
    </div>
  );
}

function paginationRange(page, totalPages) {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, index) => index + 1);
  }

  const pages = [1];
  const start = Math.max(2, page - 1);
  const end = Math.min(totalPages - 1, page + 1);

  if (start > 2) {
    pages.push("ellipsis");
  }
  for (let current = start; current <= end; current += 1) {
    pages.push(current);
  }
  if (end < totalPages - 1) {
    pages.push("ellipsis");
  }
  pages.push(totalPages);
  return pages;
}

function formatCell(value, column, row = {}) {
  if (value === null || value === undefined || value === "") {
    return "";
  }
  if (column.type === "amount") {
    return Number(value).toLocaleString("de-DE", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }
  if (column.key === "invoice_date") {
    const date = new Date(`${value}T00:00:00`);
    if (!Number.isNaN(date.getTime())) {
      return date.toLocaleDateString("de-DE");
    }
  }
  return String(value);
}

function ValidationIssuesCell({ count, details, invoiceId, onLoad }) {
  if (!count) {
    return <span className="validation-empty" aria-label="No validation errors">-</span>;
  }

  const failedRows = (details?.items || []).filter((item) => !item.passed);
  const visibleErrors = failedRows.slice(0, 8);
  const hiddenCount = Math.max(failedRows.length - visibleErrors.length, 0);

  function requestDetails() {
    onLoad?.(invoiceId);
  }

  return (
    <span className="validation-issue">
      <button
        className="validation-trigger"
        type="button"
        aria-label={`${count} validation errors`}
        onMouseEnter={requestDetails}
        onFocus={requestDetails}
      >
        <Info size={16} />
        <span>{count}</span>
      </button>
      <span className="validation-tooltip" role="tooltip">
        <strong>{count === 1 ? "1 validation issue" : `${count} validation issues`}</strong>
        {details?.loading ? (
          <span className="validation-tooltip-message">Loading validation details...</span>
        ) : details?.error ? (
          <span className="validation-tooltip-message error">{details.error}</span>
        ) : visibleErrors.length ? (
          <span className="validation-tooltip-table">
            <span>Check</span>
            <span>Expected</span>
            <span>Actual</span>
            {visibleErrors.map((error, index) => (
              <React.Fragment key={`${error.check_name}-${index}`}>
                <span>{formatCheckName(error.check_name)}</span>
                <span>{emptyText(error.expected_value)}</span>
                <span>{emptyText(error.actual_value)}</span>
              </React.Fragment>
            ))}
          </span>
        ) : (
          <span className="validation-tooltip-message">Hover again to load validation details.</span>
        )}
        {hiddenCount > 0 && <em>+ {hiddenCount} more</em>}
      </span>
    </span>
  );
}

function formatCheckName(value) {
  return String(value || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function emptyText(value) {
  if (value === null || value === undefined || value === "") {
    return "null";
  }
  return String(value);
}

createRoot(document.getElementById("root")).render(<App />);
