import base64
import json
from pathlib import Path
from typing import Any

from flask import current_app
from openai import OpenAI


OPENAI_RESPONSE_FORMAT: dict[str, Any] = {
    "type": "json_schema",
    "name": "document_invoice_extraction",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "client": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": ["string", "null"]},
                    "street": {"type": ["string", "null"]},
                    "house_number": {"type": ["string", "null"]},
                    "postal_code": {"type": ["string", "null"]},
                    "city": {"type": ["string", "null"]},
                },
                "required": ["name", "street", "house_number", "postal_code", "city"],
            },
            "invoice": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "invoice_number": {"type": ["string", "null"]},
                    "invoice_date": {"type": ["string", "null"]},
                    "invoice_type": {
                        "type": ["string", "null"],
                        "enum": [
                            "invoice",
                            "receipt",
                            "contract",
                            "commission_settlement",
                            "credit_note",
                            "unknown",
                            None,
                        ],
                    },
                    "gesamt_netto": {"type": ["number", "string", "null"]},
                    "tva": {"type": ["number", "string", "null"]},
                    "gesamtbetrag": {"type": ["number", "string", "null"]},
                },
                "required": [
                    "invoice_number",
                    "invoice_date",
                    "invoice_type",
                    "gesamt_netto",
                    "tva",
                    "gesamtbetrag",
                ],
            },
            "invoice_pos": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "gesamt_netto": {"type": ["number", "string", "null"]},
                        "gesamtpreis": {"type": ["number", "string", "null"]},
                    },
                    "required": ["gesamt_netto", "gesamtpreis"],
                },
            },
        },
        "required": ["client", "invoice", "invoice_pos"],
    },
}


EXTRACTION_PROMPT = """
Extract structured accounting data from the scanned business document.

Documents can be invoices, receipts, contracts, commission settlements, credit notes, or unknown financial documents.
Read all visible pages carefully, including headers, logos, invoice metadata blocks, totals sections, tax summaries, and line-item tables.

Return only the JSON object matching the provided schema. Do not include SQL, Markdown, comments, explanations, or extra fields.

General Field rules:

- client.name: extract the main document issuer/client/vendor name from the title/header/logo/address area. Prefer the business name most associated with the document title or issuer.

- client.street, client.house_number, client.postal_code, client.city: extract the address parts for the same main document issuer/client/vendor used for client.name. Split the street name and house number when possible. If an address part is not visible or cannot be extracted reliably, return null for that field.

- invoice.invoice_number: extract the document's invoice/receipt/settlement number. It may be labeled Rechnung, Rechnungsnummer, Beleg, Belegnummer, Bon, Quittung, Invoice No, Nr., Document No, Abrechnung, or similar. This value is expected to exist. If truly unreadable, return null.

- invoice.invoice_date: extract the document date and normalize it to ISO YYYY-MM-DD. Convert German and European dates like 31.12.2025 to 2025-12-31. If the date is unreadable or ambiguous, return null.

- invoice.invoice_type: classify as exactly one of invoice, receipt, contract, commission_settlement, credit_note, unknown. Use commission_settlement when amounts are settlement/commission/payment balances even if shown as negative. Use credit_note for credit notes/storno/gutschrift documents.

- invoice.gesamt_netto: extract the total net amount before VAT/tax only when it is visible or clearly stated. If the document only shows a final gross total and does not show the net total, return null.

- invoice.tva: extract the total VAT/tax amount only when it is visible or clearly stated. If the document explicitly says VAT/tax is 0, return 0. If VAT/tax is not shown, return null.

- invoice.gesamtbetrag: extract the final gross total/payable/settlement amount when it is visible or clearly stated.

- Do not calculate or derive invoice.gesamt_netto, invoice.tva, or invoice.gesamtbetrag from other totals unless explicitly instructed. Arithmetic may be used only to determine whether otherwise-unlabeled line totals correspond to a visible invoice-level net or gross total.

- invoice_pos: extract one object for each visible invoice position or line item that has a reliable line/position total. Preserve the visual order. Do not invent, merge, or split positions unless the document structure clearly requires it. Do not treat subtotal, tax-summary, or final-total rows as invoice positions unless explicitly instructed.


Rules for deciding whether a position amount is net or gross, in priority order:

1. If the column or row is explicitly labeled Netto/net/net amount:
   - store the amount in invoice_pos[].gesamt_netto
   - set invoice_pos[].gesamtpreis to null unless a separate gross amount is explicitly shown.

2. If the column or row is explicitly labeled Brutto/gross/gross amount,
   or clearly indicates that VAT/tax is included:
   - store the amount in invoice_pos[].gesamtpreis
   - set invoice_pos[].gesamt_netto to null unless a separate net amount is explicitly shown.

   A label such as Gesamtpreis, Total, Amount, Betrag, or line total alone
   does not prove that the amount is gross. Determine net/gross from the
   surrounding table headers, VAT context, and invoice totals.

3. If both net and gross amounts are explicitly shown for the same position:
   - populate both fields with their corresponding values.


4. Never copy or derive one position amount from the other using VAT.
   Never put the same visible amount into both invoice_pos[].gesamt_netto
   and invoice_pos[].gesamtpreis merely because only one value is available.
   Populate both only when separate net and gross values for that position
   are explicitly visible or clearly identified in the document.

Number rules:
- Return numbers as plain decimals without currency symbols.
- Normalize thousands and decimal separators, for example 86.245,68 -> 86245.68 and 1,234.50 -> 1234.50.
- If a value is shown as negative, return it as a negative number.
- If a value cannot be extracted, use null.

Accuracy rules:
- Do not guess values that are not visible.
- Prefer totals sections over OCR noise in body text.
- For conflicting totals, choose the value explicitly labeled total/gross/final amount.
- Keep line items in page order and row order.
""".strip()


def extract_invoice_data(pdf_path: Path) -> dict[str, Any]:
    if not current_app.config.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not configured")

    model_name = current_app.config["OPENAI_MODEL"]
    file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
    current_app.logger.info(
        "Sending document to OpenAI OCR: file=%s size_mb=%.2f model=%s",
        pdf_path.name,
        file_size_mb,
        model_name,
    )

    client = OpenAI(api_key=current_app.config["OPENAI_API_KEY"])
    encoded = base64.b64encode(pdf_path.read_bytes()).decode("utf-8")
    content: list[dict[str, Any]] = [
        {"type": "input_text", "text": EXTRACTION_PROMPT},
        {
            "type": "input_file",
            "filename": pdf_path.name,
            "file_data": f"data:application/pdf;base64,{encoded}",
            "detail": current_app.config["OPENAI_FILE_DETAIL"],
        },
    ]

    response = client.responses.create(
        model=model_name,
        input=[{"role": "user", "content": content}],
        text={"format": OPENAI_RESPONSE_FORMAT},
    )

    current_app.logger.info(
        "OpenAI OCR response received: file=%s model=%s response_id=%s",
        pdf_path.name,
        model_name,
        getattr(response, "id", None),
    )
    return json.loads(response.output_text)
