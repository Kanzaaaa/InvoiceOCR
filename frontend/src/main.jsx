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
const AUTH_STORAGE_KEY = "invoiceocr_authenticated";
const LANGUAGE_STORAGE_KEY = "invoiceocr_language";
const LOGIN_USERNAME = import.meta.env.VITE_APP_USERNAME || "admin";
const LOGIN_PASSWORD = import.meta.env.VITE_APP_PASSWORD || "invoiceocr2026";

const COPY = {
  en: {
    appTitle: "HEDSOFT - Dashboard - Invoice OCR Extraction",
    appSubtitle:
      "Upload scanned invoice PDFs, extract accounting fields with OCR, review validation results, and export Lexware-ready invoice and position tables.",
    loginTitle: "Invoice OCR Access",
    loginSubtitle: "Sign in to upload invoices, review extracted records, and export the Lexware-ready workbook.",
    username: "Username",
    password: "Password",
    signIn: "Sign in",
    logout: "Log out",
    invalidLogin: "Invalid username or password.",
    overview: "Overview",
    invoices: "Invoices",
    positions: "Positions",
    clients: "Clients",
    validationIssues: "Validation Issues",
    howToTitle: "How to use this dashboard",
    howToText:
      "Upload up to three scanned PDF invoices, wait for OCR extraction to finish, review the invoice and position tables, check validation issues when the warning icon appears, then export the Lexware-ready Excel file.",
    uploadStep: "Upload",
    extractStep: "Extract",
    reviewStep: "Review",
    exportStep: "Export",
    uploadTitle: "Invoice Upload",
    uploadSubtitle: "Upload up to 3 scanned PDF invoices.",
    uploadInfo:
      "This is Kenza's test API. It currently supports up to three PDF files per upload, but it can later be expanded to handle more files. If the API key or service access expires, OCR extraction will stop working until the credentials are renewed.",
    pdfSlot: "PDF",
    choosePdf: "Choose PDF",
    dragPdf: "or drag a PDF here",
    replacePdf: "Drag another PDF here to replace it",
    startUpload: "Start Upload",
    onlyPdf: "Only PDF files can be uploaded.",
    uploadFailed: "Upload failed.",
    queued: "queued for extraction.",
    processingStart: "Processing",
    processingInvoices: "Processing invoices",
    processingProgress: "Processing invoices...",
    processingWait: "Your request is being processed. Please wait until extraction finishes.",
    extractionFinished: "Extraction finished. Tables are updated.",
    processingStill: "Processing is still running. The tables will update after the next completed extraction.",
    loadError: "Unable to load table data. Check that the Flask API and database are running.",
    tableRequestFailed: "Table request failed.",
    unableToLoadValidation: "Unable to load validation results.",
    allClients: "All clients",
    invoiceTableTitle: "Invoice",
    positionTableTitle: "Invoice POS",
    showTables: "Show tables",
    hideTables: "Hide tables",
    exportExcel: "Export combined invoice review Excel",
    rows: "rows",
    noRows: "No rows to display",
    loadingData: "Loading data",
    page: "Page",
    of: "of",
    previous: "Previous",
    next: "Next",
    finished: "finished",
    validationIssue: "validation issue",
    validationIssuesLower: "validation issues",
    validationLoading: "Loading validation details...",
    validationHoverAgain: "Hover again to load validation details.",
    more: "more",
    check: "Check",
    expected: "Expected",
    actual: "Actual",
    resetTitle: "Reset Process",
    resetText: "Delete all extracted database rows before starting a new test run.",
    deleteTablesTitle: "Delete extracted tables?",
    deleteTablesText: "Are you sure you want to repeat the process again and delete the tables?",
    no: "No",
    yesDelete: "Yes, delete",
    deleteSuccess: "Extracted tables were deleted. You can start the process again.",
    deleteError: "Unable to delete extracted tables.",
    noDataTitle: "No extracted data yet",
    noDataText: "Upload at least one PDF invoice to display the invoice and position tables.",
  },
  de: {
    appTitle: "HEDSOFT - Dashboard - Rechnung OCR Extraktion",
    appSubtitle:
      "Lade gescannte Rechnungs-PDFs hoch, extrahiere Buchhaltungsfelder per OCR, pruefe Validierungsergebnisse und exportiere eine Lexware-fertige Arbeitsmappe.",
    loginTitle: "Zugang zur Rechnung OCR",
    loginSubtitle: "Melde dich an, um Rechnungen hochzuladen, extrahierte Datensaetze zu pruefen und die Lexware-Datei zu exportieren.",
    username: "Benutzername",
    password: "Passwort",
    signIn: "Anmelden",
    logout: "Abmelden",
    invalidLogin: "Benutzername oder Passwort ist falsch.",
    overview: "Ueberblick",
    invoices: "Rechnungen",
    positions: "Positionen",
    clients: "Kunden",
    validationIssues: "Validierungsfehler",
    howToTitle: "So verwendest du dieses Dashboard",
    howToText:
      "Lade bis zu drei gescannte Rechnungs-PDFs hoch, warte bis die OCR-Extraktion beendet ist, pruefe Rechnungs- und Positionstabellen, kontrolliere Validierungsfehler beim Warnsymbol und exportiere danach die Lexware-fertige Excel-Datei.",
    uploadStep: "Hochladen",
    extractStep: "Extrahieren",
    reviewStep: "Pruefen",
    exportStep: "Exportieren",
    uploadTitle: "Rechnungen hochladen",
    uploadSubtitle: "Bis zu 3 gescannte Rechnungs-PDFs hochladen.",
    uploadInfo:
      "Dies ist Kenzas Test-API. Aktuell unterstuetzt sie bis zu drei PDF-Dateien pro Upload, kann spaeter aber erweitert werden. Wenn der API-Schluessel oder der Servicezugang ablaeuft, funktioniert die OCR-Extraktion erst wieder nach Erneuerung der Zugangsdaten.",
    pdfSlot: "PDF",
    choosePdf: "PDF auswaehlen",
    dragPdf: "oder PDF hierher ziehen",
    replacePdf: "Ein anderes PDF hierher ziehen, um es zu ersetzen",
    startUpload: "Upload starten",
    onlyPdf: "Es koennen nur PDF-Dateien hochgeladen werden.",
    uploadFailed: "Upload fehlgeschlagen.",
    queued: "zur Extraktion eingereiht.",
    processingStart: "Verarbeite",
    processingInvoices: "Rechnungen werden verarbeitet",
    processingProgress: "Rechnungen werden verarbeitet...",
    processingWait: "Die Anfrage wird verarbeitet. Bitte warte, bis die Extraktion abgeschlossen ist.",
    extractionFinished: "Extraktion abgeschlossen. Die Tabellen wurden aktualisiert.",
    processingStill: "Die Verarbeitung laeuft noch. Die Tabellen werden nach der naechsten abgeschlossenen Extraktion aktualisiert.",
    loadError: "Tabellendaten konnten nicht geladen werden. Pruefe, ob Flask API und Datenbank laufen.",
    tableRequestFailed: "Tabellenabfrage fehlgeschlagen.",
    unableToLoadValidation: "Validierungsergebnisse konnten nicht geladen werden.",
    allClients: "Alle Kunden",
    invoiceTableTitle: "Rechnung",
    positionTableTitle: "Rechnungspositionen",
    showTables: "Tabellen anzeigen",
    hideTables: "Tabellen ausblenden",
    exportExcel: "Kombinierte Rechnungspruefung als Excel exportieren",
    rows: "Zeilen",
    noRows: "Keine Zeilen vorhanden",
    loadingData: "Daten werden geladen",
    page: "Seite",
    of: "von",
    previous: "Zurueck",
    next: "Weiter",
    finished: "abgeschlossen",
    validationIssue: "Validierungsfehler",
    validationIssuesLower: "Validierungsfehler",
    validationLoading: "Validierungsdetails werden geladen...",
    validationHoverAgain: "Erneut darueberfahren, um Validierungsdetails zu laden.",
    more: "weitere",
    check: "Pruefung",
    expected: "Erwartet",
    actual: "Tatsaechlich",
    resetTitle: "Prozess zuruecksetzen",
    resetText: "Alle extrahierten Datenbankzeilen loeschen, bevor ein neuer Testlauf gestartet wird.",
    deleteTablesTitle: "Extrahierte Tabellen loeschen?",
    deleteTablesText: "Bist du sicher, dass du den Prozess neu starten und die Tabellen loeschen moechtest?",
    no: "Nein",
    yesDelete: "Ja, loeschen",
    deleteSuccess: "Extrahierte Tabellen wurden geloescht. Du kannst den Prozess neu starten.",
    deleteError: "Extrahierte Tabellen konnten nicht geloescht werden.",
    noDataTitle: "Noch keine extrahierten Daten",
    noDataText: "Lade mindestens eine PDF-Rechnung hoch, um die Rechnungs- und Positionstabellen anzuzeigen.",
  },
};

function createUploadSlots() {
  return Array.from({ length: MAX_UPLOAD_FILES }, () => ({ id: crypto.randomUUID(), file: null }));
}

const invoiceColumns = [
  { key: "id", label: "Rechnungs-ID", align: "center", width: 140, minWidth: 115 },
  { key: "invoice_number", label: "Rechnungsnummer", width: 190, minWidth: 150 },
  { key: "document_file_name", label: "Dateiname", width: 470, minWidth: 220 },
  { key: "client_name", label: "Kunde/Lieferant", width: 560, minWidth: 240 },
  { key: "client_street", label: "Strasse", width: 190, minWidth: 140 },
  { key: "client_house_number", label: "Hausnummer", width: 150, minWidth: 120 },
  { key: "client_postal_code", label: "PLZ", width: 120, minWidth: 95 },
  { key: "client_city", label: "Stadt", width: 170, minWidth: 125 },
  { key: "invoice_type", label: "Dokumenttyp", width: 190, minWidth: 150 },
  { key: "invoice_date", label: "Belegdatum", width: 150, minWidth: 125 },
  { key: "gesamt_netto", label: "Netto", align: "right", type: "amount", width: 140, minWidth: 110 },
  { key: "tva", label: "USt", align: "right", type: "amount", width: 120, minWidth: 95 },
  { key: "gesamtbetrag", label: "Brutto", align: "right", type: "amount", width: 140, minWidth: 110 },
  { key: "validation_failed", label: "Validierungsfehler", align: "center", type: "validation", width: 170, minWidth: 140 },
];

const posColumns = [
  { key: "invoice_id", label: "Rechnungs-ID", align: "center", width: 140, minWidth: 115 },
  { key: "invoice_number", label: "Rechnungsnummer", width: 190, minWidth: 150 },
  { key: "client_name", label: "Kunde/Lieferant", width: 430, minWidth: 220 },
  { key: "invoice_date", label: "Belegdatum", width: 150, minWidth: 125 },
  { key: "pos_number", label: "Position", align: "center", width: 130, minWidth: 100 },
  { key: "gesamt_netto", label: "Positions-Netto", align: "right", type: "amount", width: 170, minWidth: 135 },
  { key: "gesamtpreis", label: "Positions-Brutto", align: "right", type: "amount", width: 180, minWidth: 145 },
];

function App() {
  const [language, setLanguage] = useState(() => localStorage.getItem(LANGUAGE_STORAGE_KEY) || "en");
  const [authenticated, setAuthenticated] = useState(() => localStorage.getItem(AUTH_STORAGE_KEY) === "true");
  const [loginValues, setLoginValues] = useState({ username: "", password: "" });
  const [loginError, setLoginError] = useState("");
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
  const t = COPY[language] || COPY.en;

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
    if (authenticated) {
      loadTables({ initial: true });
      return;
    }
    setLoading(false);
  }, [authenticated]);

  useEffect(() => {
    localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
  }, [language]);

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
        throw new Error(t.loadError);
      }

      const invoiceRows = invoiceResult.status === "fulfilled" ? invoiceResult.value : [];
      const positionRows = positionResult.status === "fulfilled" ? positionResult.value : [];
      setInvoices(invoiceRows);
      setPositions(positionRows);
    } catch (err) {
      setError(err.message || t.loadError);
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
        throw new Error(t.tableRequestFailed);
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
      setError(t.onlyPdf);
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
      setError(t.onlyPdf);
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
        throw new Error(payload.error || t.uploadFailed);
      }

      const count = files.length === 1 ? 1 : payload.count;
      const documentIds = files.length === 1
        ? [payload.document.id]
        : payload.documents.map((document) => document.id);
      setUploadSlots(createUploadSlots());
      setProcessingIds(documentIds);
      setProcessingMessage(`${t.processingStart} ${count} ${t.invoices.toLowerCase()}...`);
      setNotice(`${count} ${t.invoices.toLowerCase()} ${t.queued}`);
      await loadTables();
      await pollProcessing(documentIds);
    } catch (err) {
      setError(err.message || t.uploadFailed);
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
      setProcessingMessage(`${t.processingProgress} ${finishedCount}/${documentIds.length} ${t.finished}`);

      if (resolvedStatuses.length === documentIds.length && finishedCount === documentIds.length) {
        await loadTables();
        setProcessingIds([]);
        setProcessingMessage("");
        setNotice(t.extractionFinished);
        return;
      }

      if (attempt % 3 === 2) {
        await loadTables();
      }
    }

    setProcessingIds([]);
    setProcessingMessage("");
    setNotice(t.processingStill);
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
        throw new Error(payload.error || t.unableToLoadValidation);
      }
      setValidationDetailsByInvoiceId((details) => ({
        ...details,
        [cacheKey]: { loading: false, loaded: true, error: "", items: payload },
      }));
    } catch (err) {
      setValidationDetailsByInvoiceId((details) => ({
        ...details,
        [cacheKey]: { loading: false, loaded: false, error: err.message || t.unableToLoadValidation, items: [] },
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
        throw new Error(payload.error || t.deleteError);
      }

      setInvoices([]);
      setPositions([]);
      setSelectedClientId("all");
      setInvoicePage(1);
      setPositionPage(1);
      setTablesExpanded(false);
      setResetModalOpen(false);
      setNotice(t.deleteSuccess);
    } catch (err) {
      setError(err.message || t.deleteError);
    } finally {
      setResetting(false);
    }
  }

  function handleLogin(event) {
    event.preventDefault();
    if (loginValues.username === LOGIN_USERNAME && loginValues.password === LOGIN_PASSWORD) {
      localStorage.setItem(AUTH_STORAGE_KEY, "true");
      setAuthenticated(true);
      setLoginError("");
      return;
    }
    setLoginError(t.invalidLogin);
  }

  function handleLogout() {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    setAuthenticated(false);
  }

  if (!authenticated) {
    return (
      <LoginPage
        copy={t}
        language={language}
        onLanguageChange={setLanguage}
        values={loginValues}
        error={loginError}
        onChange={setLoginValues}
        onSubmit={handleLogin}
      />
    );
  }

  return (
    <main className="app-shell">
      <section className="page-header">
        <div>
          <h1>
            <span>HEDSOFT</span> - {t.appTitle.replace("HEDSOFT - ", "")}
          </h1>
          <p>{t.appSubtitle}</p>
        </div>
        <div className="header-actions">
          <LanguageSwitch language={language} onChange={setLanguage} />
          <button className="logout-button" type="button" onClick={handleLogout}>
            {t.logout}
          </button>
        </div>
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

      <section className="overview-card" aria-label={t.overview}>
        <h2>{t.overview}</h2>
        <div className="summary-row">
          <SummaryTile label={t.invoices} value={filteredInvoices.length} />
          <SummaryTile label={t.positions} value={filteredPositions.length} />
          <SummaryTile label={t.clients} value={selectedClientId === "all" ? clients.length : 1} />
          <SummaryTile label={t.validationIssues} value={failedInvoices} tone={failedInvoices > 0 ? "warning" : "ok"} />
        </div>
        <div className="overview-divider" />
        <div className="overview-body">
          <div>
            <h3>{t.howToTitle}</h3>
            <p>{t.howToText}</p>
          </div>
          <div className="overview-steps" aria-label="Workflow steps">
            <span>{t.uploadStep}</span>
            <span>{t.extractStep}</span>
            <span>{t.reviewStep}</span>
            <span>{t.exportStep}</span>
          </div>
        </div>
      </section>

      <section className="upload-panel">
        <div className="panel-heading">
          <div>
            <div className="title-with-info">
              <h2>{t.uploadTitle}</h2>
              <span className="info-tooltip">
                <button type="button" aria-label="Invoice upload information">
                  <Info size={15} />
                </button>
                <span role="tooltip">{t.uploadInfo}</span>
              </span>
            </div>
            <p>{t.uploadSubtitle}</p>
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
                  <strong>{slot.file ? slot.file.name : `${t.pdfSlot} ${index + 1}`}</strong>
                  <span>{slot.file ? t.replacePdf : `${t.choosePdf} ${t.dragPdf}`}</span>
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
            <span>{t.startUpload}</span>
          </button>
        </div>
      </section>

      {!hasExtractedData && !loading && (
        <section className="empty-dashboard-note">
          <h2>{t.noDataTitle}</h2>
          <p>{t.noDataText}</p>
        </section>
      )}

      {hasExtractedData && (
      <section className={tablesExpanded ? "hierarchy-panel expanded" : "hierarchy-panel"}>
        <div className="hierarchy-header">
          <div className="hierarchy-level client-level">
            <button
              className="client-disclosure"
              type="button"
              aria-expanded={tablesExpanded}
              aria-label={tablesExpanded ? t.hideTables : t.showTables}
              onClick={() => setTablesExpanded((expanded) => !expanded)}
              title={tablesExpanded ? t.hideTables : t.showTables}
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
                  <option value="all">{t.allClients}</option>
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
            <span>{filteredInvoices.length} {t.invoices.toLowerCase()}</span>
            <span>{filteredPositions.length} {t.positions.toLowerCase()}</span>
          </div>
        </div>

        <div className={tablesExpanded ? "tables-collapse open" : "tables-collapse"} aria-hidden={!tablesExpanded}>
          <div className="tables-collapse-inner">
            <DataSection
              title={t.invoiceTableTitle}
              rows={filteredInvoices}
              columns={invoiceColumns}
              loading={loading}
              exportVisible={exportAllowed}
              onExport={() => downloadExport("/api/exports/lexware_invoice_review.xlsx")}
              exportTitle={t.exportExcel}
              page={invoicePage}
              onPageChange={setInvoicePage}
              pageSize={INVOICE_TABLE_PAGE_SIZE}
              validationDetailsByInvoiceId={validationDetailsByInvoiceId}
              onLoadValidationDetails={loadValidationDetails}
              copy={t}
            />

            <DataSection
              title={t.positionTableTitle}
              rows={filteredPositions}
              columns={posColumns}
              loading={loading}
              exportVisible={false}
              page={positionPage}
              onPageChange={setPositionPage}
              pageSize={POSITION_TABLE_PAGE_SIZE}
              compact
              copy={t}
            />
          </div>
        </div>
      </section>
      )}

      {hasExtractedData && (
      <section className="reset-section" aria-label={t.resetTitle}>
        <div>
          <h2>{t.resetTitle}</h2>
          <p>{t.resetText}</p>
        </div>
        <button
          className="danger-icon-button"
          type="button"
          onClick={() => setResetModalOpen(true)}
          disabled={!hasExtractedData || uploading || processingIds.length > 0 || resetting}
          title={t.deleteTablesTitle}
        >
          <Trash2 size={20} />
        </button>
      </section>
      )}

      {resetModalOpen && (
        <div className="modal-backdrop" role="presentation">
          <section className="confirm-modal" role="dialog" aria-modal="true" aria-labelledby="reset-title">
            <div className="modal-icon">
              <Trash2 size={22} />
            </div>
            <h2 id="reset-title">{t.deleteTablesTitle}</h2>
            <p>{t.deleteTablesText}</p>
            <div className="modal-actions">
              <button className="modal-secondary" type="button" onClick={() => setResetModalOpen(false)} disabled={resetting}>
                {t.no}
              </button>
              <button className="modal-danger" type="button" onClick={resetExtractedTables} disabled={resetting}>
                {resetting ? <Loader2 size={16} className="spin" /> : <Trash2 size={16} />}
                <span>{t.yesDelete}</span>
              </button>
            </div>
          </section>
        </div>
      )}

      {(uploading || processingIds.length > 0) && (
        <div className="processing-screen" role="alert" aria-live="assertive" aria-busy="true">
          <section className="processing-card" aria-label={t.processingInvoices}>
            <div className="processing-spinner">
              <Loader2 size={42} className="spin" />
            </div>
            <h2>{t.processingInvoices}</h2>
            <p>{processingMessage || t.processingWait}</p>
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

function LoginPage({ copy, language, onLanguageChange, values, error, onChange, onSubmit }) {
  return (
    <main className="login-shell">
      <section className="login-card">
        <div className="login-topbar">
          <span className="brand-mark">HEDSOFT</span>
          <LanguageSwitch language={language} onChange={onLanguageChange} />
        </div>
        <div className="login-copy">
          <h1>{copy.loginTitle}</h1>
          <p>{copy.loginSubtitle}</p>
        </div>
        <form className="login-form" onSubmit={onSubmit}>
          <label>
            <span>{copy.username}</span>
            <input
              type="text"
              value={values.username}
              onChange={(event) => onChange({ ...values, username: event.target.value })}
              autoComplete="username"
            />
          </label>
          <label>
            <span>{copy.password}</span>
            <input
              type="password"
              value={values.password}
              onChange={(event) => onChange({ ...values, password: event.target.value })}
              autoComplete="current-password"
            />
          </label>
          {error && (
            <p className="login-error" role="alert">
              {error}
            </p>
          )}
          <button className="primary-button" type="submit">
            {copy.signIn}
          </button>
        </form>
      </section>
    </main>
  );
}

function LanguageSwitch({ language, onChange }) {
  return (
    <div className="language-switch" aria-label="Language selection">
      <button
        type="button"
        className={language === "en" ? "active" : ""}
        onClick={() => onChange("en")}
        aria-label="Show interface in English"
        title="English"
      >
        <span aria-hidden="true">🇬🇧</span>
      </button>
      <button
        type="button"
        className={language === "de" ? "active" : ""}
        onClick={() => onChange("de")}
        aria-label="Benutzeroberflaeche auf Deutsch anzeigen"
        title="Deutsch"
      >
        <span aria-hidden="true">🇩🇪</span>
      </button>
    </div>
  );
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
  copy,
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
                  {copy.loadingData}
                </td>
              </tr>
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="empty-cell">
                  {copy.noRows}
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
                          copy={copy}
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
        copy={copy}
      />
    </section>
  );
}

function Pagination({ page, totalPages, totalRows, onPageChange, copy }) {
  const pages = paginationRange(page, totalPages);
  const canGoBack = page > 1;
  const canGoForward = page < totalPages;

  return (
    <div className="pagination-bar">
      <span>
        {copy.page} {page} {copy.of} {totalPages} · {totalRows} {copy.rows}
      </span>
      <div className="pagination-actions">
        <button type="button" onClick={() => onPageChange(page - 1)} disabled={!canGoBack}>
          {copy.previous}
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
          {copy.next}
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

function ValidationIssuesCell({ count, details, invoiceId, onLoad, copy }) {
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
        <strong>{count === 1 ? `1 ${copy.validationIssue}` : `${count} ${copy.validationIssuesLower}`}</strong>
        {details?.loading ? (
          <span className="validation-tooltip-message">{copy.validationLoading}</span>
        ) : details?.error ? (
          <span className="validation-tooltip-message error">{details.error}</span>
        ) : visibleErrors.length ? (
          <span className="validation-tooltip-table">
            <span>{copy.check}</span>
            <span>{copy.expected}</span>
            <span>{copy.actual}</span>
            {visibleErrors.map((error, index) => (
              <React.Fragment key={`${error.check_name}-${index}`}>
                <span>{formatCheckName(error.check_name)}</span>
                <span>{emptyText(error.expected_value)}</span>
                <span>{emptyText(error.actual_value)}</span>
              </React.Fragment>
            ))}
          </span>
        ) : (
          <span className="validation-tooltip-message">{copy.validationHoverAgain}</span>
        )}
        {hiddenCount > 0 && <em>+ {hiddenCount} {copy.more}</em>}
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
