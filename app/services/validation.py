from datetime import date
from decimal import Decimal
from typing import Any


TOLERANCE = Decimal("0.02")


def build_validation_results(
    document_id: int,
    invoice_id: int | None,
    normalized: dict[str, Any],
    duplicate_count: int,
    valid_invoice_types: set[str],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    client = normalized["client"]
    invoice = normalized["invoice"]
    positions = normalized["invoice_pos"]

    _add_null_check(results, document_id, invoice_id, "null_client_name", "client.name", client["name_original"])
    _add_null_check(results, document_id, invoice_id, "null_invoice_number", "invoice.invoice_number", invoice["invoice_number"])
    _add_null_check(results, document_id, invoice_id, "null_invoice_date", "invoice.invoice_date", invoice["invoice_date"])
    _add_null_check(results, document_id, invoice_id, "null_invoice_type", "invoice.invoice_type", invoice["invoice_type"])
    _add_null_check(results, document_id, invoice_id, "null_gesamtbetrag", "invoice.gesamtbetrag", invoice["gesamtbetrag"])

    for pos in positions:
        _add_result(
            results,
            document_id,
            invoice_id,
            f"pos_amount_present_{pos['pos_number']}",
            pos["gesamt_netto"] is not None or pos["gesamtpreis"] is not None,
            f"invoice_pos[{pos['pos_number']}] has gesamt_netto or gesamtpreis",
            f"net={_to_display_text(pos['gesamt_netto'])}, gross={_to_display_text(pos['gesamtpreis'])}",
        )

    required_missing = [
        name
        for name, value in {
            "client.name": client["name_original"],
            "invoice.invoice_number": invoice["invoice_number"],
            "invoice.invoice_date": invoice["invoice_date"],
            "invoice.invoice_type": invoice["invoice_type"],
            "invoice.gesamtbetrag": invoice["gesamtbetrag"],
        }.items()
        if value is None or value == ""
    ]
    _add_result(
        results,
        document_id,
        invoice_id,
        "required_invoice_fields_complete",
        not required_missing,
        "all required invoice fields present",
        ", ".join(required_missing) if required_missing else "complete",
    )

    _add_result(
        results,
        document_id,
        invoice_id,
        "invoice_date_valid_iso",
        invoice["invoice_date"] is not None,
        "valid ISO date YYYY-MM-DD",
        invoice["invoice_date"],
    )

    parsed_date = date.fromisoformat(invoice["invoice_date"]) if invoice["invoice_date"] else None
    _add_result(
        results,
        document_id,
        invoice_id,
        "invoice_date_not_future",
        parsed_date is None or parsed_date <= date.today(),
        "date today or earlier",
        invoice["invoice_date"],
    )

    _add_result(
        results,
        document_id,
        invoice_id,
        "invoice_type_valid",
        invoice["invoice_type"] in valid_invoice_types,
        ", ".join(sorted(valid_invoice_types)),
        invoice["invoice_type"],
    )

    all_amounts = [invoice["gesamt_netto"], invoice["tva"], invoice["gesamtbetrag"]]
    all_amounts.extend(pos["gesamt_netto"] for pos in positions)
    all_amounts.extend(pos["gesamtpreis"] for pos in positions)
    _add_result(
        results,
        document_id,
        invoice_id,
        "amounts_are_valid_decimals",
        all(amount is None or isinstance(amount, Decimal) for amount in all_amounts),
        "all extracted amounts are stored as signed decimals",
        ", ".join(_to_display_text(amount) for amount in all_amounts),
    )

    net = invoice["gesamt_netto"]
    tax = invoice["tva"]
    gross = invoice["gesamtbetrag"]
    if net is not None and tax is not None and gross is not None:
        _add_result(
            results,
            document_id,
            invoice_id,
            "net_plus_tax_equals_total",
            abs((net + tax) - gross) <= TOLERANCE,
            _to_text(gross),
            _to_text(net + tax),
        )

    non_null_prices = [pos["gesamtpreis"] for pos in positions if pos["gesamtpreis"] is not None]
    if positions and len(non_null_prices) == len(positions) and gross is not None:
        pos_sum = sum(non_null_prices, Decimal("0.00"))
        _add_result(
            results,
            document_id,
            invoice_id,
            "pos_sum_matches_gross_total",
            abs(pos_sum - gross) <= TOLERANCE,
            _to_text(gross),
            _to_text(pos_sum),
        )
    else:
        _add_result(
            results,
            document_id,
            invoice_id,
            "pos_sum_matches_gross_total",
            True,
            "no complete POS sum available",
            "not applicable",
        )

    non_null_net_prices = [pos["gesamt_netto"] for pos in positions if pos["gesamt_netto"] is not None]
    if positions and len(non_null_net_prices) == len(positions) and net is not None:
        pos_net_sum = sum(non_null_net_prices, Decimal("0.00"))
        _add_result(
            results,
            document_id,
            invoice_id,
            "pos_net_sum_matches_invoice_net",
            abs(pos_net_sum - net) <= TOLERANCE,
            _to_text(net),
            _to_text(pos_net_sum),
        )
    else:
        _add_result(
            results,
            document_id,
            invoice_id,
            "pos_net_sum_matches_invoice_net",
            True,
            "no complete POS net sum available",
            "not applicable",
        )

    _add_result(
        results,
        document_id,
        invoice_id,
        "duplicate_invoice_number_for_client",
        duplicate_count == 0,
        "no previous invoice exists for same client and invoice number",
        str(duplicate_count),
    )

    _add_result(
        results,
        document_id,
        invoice_id,
        "client_name_present",
        bool(client["name_original"]),
        "non-empty client name",
        client["name_original"],
    )
    _add_result(
        results,
        document_id,
        invoice_id,
        "client_name_normalized",
        bool(client["name_normalized"]),
        "non-empty normalized client name",
        client["name_normalized"],
    )

    return results


def _add_null_check(
    results: list[dict[str, Any]],
    document_id: int,
    invoice_id: int | None,
    check_name: str,
    expected_field: str,
    actual_value: Any,
) -> None:
    _add_result(
        results,
        document_id,
        invoice_id,
        check_name,
        actual_value is not None and actual_value != "",
        f"non-null {expected_field}",
        actual_value,
    )


def _add_result(
    results: list[dict[str, Any]],
    document_id: int,
    invoice_id: int | None,
    check_name: str,
    passed: bool,
    expected_value: Any,
    actual_value: Any,
) -> None:
    results.append(
        {
            "document_id": document_id,
            "invoice_id": invoice_id,
            "check_name": check_name,
            "passed": passed,
            "expected_value": _to_text(expected_value),
            "actual_value": _to_text(actual_value),
        }
    )


def _to_text(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _to_display_text(value: Any) -> str:
    if value is None:
        return "null"
    return str(value)
