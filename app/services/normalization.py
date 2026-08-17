import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any


def normalize_client_name(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.lower()
    text = text.replace("&", " ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def normalize_invoice_type(value: Any, valid_types: set[str]) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    if not text:
        return None
    return text if text in valid_types else "unknown"


def normalize_invoice_date(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    formats = [
        "%Y-%m-%d",
        "%d.%m.%Y",
        "%d.%m.%y",
        "%d/%m/%Y",
        "%d/%m/%y",
        "%d-%m-%Y",
        "%d-%m-%y",
        "%Y/%m/%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def normalize_amount(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, (int, float, Decimal)):
        return _to_decimal(str(value))

    text = str(value).strip()
    if not text:
        return None

    negative = text.startswith("-") or text.startswith("−") or (text.startswith("(") and text.endswith(")"))
    text = text.replace("−", "-")
    text = re.sub(r"[^\d,.\-]", "", text)
    text = text.replace("-", "")

    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        parts = text.split(",")
        if len(parts[-1]) in {1, 2}:
            text = "".join(parts[:-1]) + "." + parts[-1]
        else:
            text = text.replace(",", "")
    elif text.count(".") > 1:
        parts = text.split(".")
        if len(parts[-1]) in {1, 2}:
            text = "".join(parts[:-1]) + "." + parts[-1]
        else:
            text = "".join(parts)

    if negative:
        text = f"-{text}"
    return _to_decimal(text)


def _to_decimal(value: str) -> Decimal | None:
    try:
        amount = Decimal(value)
    except (InvalidOperation, ValueError):
        return None
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def normalize_extraction(raw: dict[str, Any], valid_invoice_types: set[str]) -> dict[str, Any]:
    client = raw.get("client") or {}
    invoice = raw.get("invoice") or {}
    positions = raw.get("invoice_pos") or []

    return {
        "client": {
            "name_original": _clean_string(client.get("name")),
            "name_normalized": normalize_client_name(client.get("name")),
            "street": _clean_string(client.get("street")),
            "house_number": _clean_string(client.get("house_number")),
            "postal_code": _clean_string(client.get("postal_code")),
            "city": _clean_string(client.get("city")),
        },
        "invoice": {
            "invoice_number": _clean_string(invoice.get("invoice_number")),
            "invoice_date": normalize_invoice_date(invoice.get("invoice_date")),
            "invoice_type": normalize_invoice_type(invoice.get("invoice_type"), valid_invoice_types),
            "gesamt_netto": normalize_amount(invoice.get("gesamt_netto")),
            "tva": normalize_amount(invoice.get("tva")),
            "gesamtbetrag": normalize_amount(invoice.get("gesamtbetrag")),
        },
        "invoice_pos": [
            {
                "pos_number": index,
                "gesamt_netto": normalize_amount(item.get("gesamt_netto")),
                "gesamtpreis": normalize_amount(item.get("gesamtpreis")),
            }
            for index, item in enumerate(positions, start=1)
        ],
    }


def serialize_normalized(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: serialize_normalized(item) for key, item in value.items()}
    if isinstance(value, list):
        return [serialize_normalized(item) for item in value]
    return value


def _clean_string(value: Any) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text or None
