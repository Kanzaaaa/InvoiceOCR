import unittest
from decimal import Decimal

from app.services.normalization import (
    normalize_amount,
    normalize_client_name,
    normalize_extraction,
    normalize_invoice_date,
    normalize_invoice_type,
)
from app.services.validation import build_validation_results


VALID_TYPES = {"invoice", "receipt", "contract", "commission_settlement", "credit_note", "unknown"}


class NormalizationTests(unittest.TestCase):
    def test_german_decimal_and_negative_amounts_are_preserved(self):
        self.assertEqual(normalize_amount("86.245,68 EUR"), Decimal("86245.68"))
        self.assertEqual(normalize_amount("-86.245,68 EUR"), Decimal("-86245.68"))
        self.assertEqual(normalize_amount("(1,234.50)"), Decimal("-1234.50"))

    def test_invoice_date_is_normalized_to_iso(self):
        self.assertEqual(normalize_invoice_date("31.12.2025"), "2025-12-31")

    def test_null_invoice_type_stays_null_for_validation(self):
        self.assertIsNone(normalize_invoice_type(None, VALID_TYPES))

    def test_client_name_is_normalized_for_matching(self):
        self.assertEqual(normalize_client_name("Bauhaus GmbH & Co. KG"), "bauhaus gmbh co kg")
        self.assertEqual(normalize_client_name("Müller GmbH & Co. KG"), "muller gmbh co kg")

    def test_invoice_pos_net_and_gross_are_normalized(self):
        normalized = normalize_extraction(
            {
                "client": {
                    "name": "ACME GmbH",
                    "street": "Mainstr.",
                    "house_number": "10",
                    "postal_code": "60386",
                    "city": "Frankfurt",
                },
                "invoice": {
                    "invoice_number": "R-100",
                    "invoice_date": "01.01.2026",
                    "invoice_type": "invoice",
                    "gesamt_netto": "100,00",
                    "tva": "19,00",
                    "gesamtbetrag": "119,00",
                },
                "invoice_pos": [{"gesamt_netto": "100,00", "gesamtpreis": "119,00"}],
            },
            VALID_TYPES,
        )

        self.assertEqual(normalized["invoice_pos"][0]["gesamt_netto"], Decimal("100.00"))
        self.assertEqual(normalized["invoice_pos"][0]["gesamtpreis"], Decimal("119.00"))
        self.assertEqual(normalized["client"]["street"], "Mainstr.")
        self.assertEqual(normalized["client"]["house_number"], "10")
        self.assertEqual(normalized["client"]["postal_code"], "60386")
        self.assertEqual(normalized["client"]["city"], "Frankfurt")


class ValidationTests(unittest.TestCase):
    def test_commission_settlement_with_zero_tax_and_duplicate_flag(self):
        normalized = {
            "client": {"name_original": "ACME GmbH", "name_normalized": "acme"},
            "invoice": {
                "invoice_number": "R-100",
                "invoice_date": "2026-01-10",
                "invoice_type": "commission_settlement",
                "gesamt_netto": Decimal("100.00"),
                "tva": Decimal("0.00"),
                "gesamtbetrag": Decimal("100.00"),
            },
            "invoice_pos": [
                {"pos_number": 1, "gesamt_netto": Decimal("40.00"), "gesamtpreis": Decimal("40.00")},
                {"pos_number": 2, "gesamt_netto": Decimal("60.00"), "gesamtpreis": Decimal("60.00")},
            ],
        }

        results = build_validation_results(
            document_id=1,
            invoice_id=2,
            normalized=normalized,
            duplicate_count=1,
            valid_invoice_types=VALID_TYPES,
        )
        checks = {row["check_name"]: row["passed"] for row in results}

        self.assertTrue(checks["net_plus_tax_equals_total"])
        self.assertTrue(checks["pos_sum_matches_gross_total"])
        self.assertTrue(checks["pos_net_sum_matches_invoice_net"])
        self.assertFalse(checks["duplicate_invoice_number_for_client"])
        self.assertNotIn("gross_greater_equal_net", checks)
        self.assertNotIn("tax_not_greater_than_total", checks)
        self.assertNotIn("tva_requires_net_and_gross", checks)

    def test_validation_handles_null_amounts(self):
        normalized = {
            "client": {"name_original": "ACME GmbH", "name_normalized": "acme"},
            "invoice": {
                "invoice_number": "R-101",
                "invoice_date": "2026-01-10",
                "invoice_type": "invoice",
                "gesamt_netto": None,
                "tva": Decimal("0.00"),
                "gesamtbetrag": Decimal("100.00"),
            },
            "invoice_pos": [{"pos_number": 1, "gesamt_netto": None, "gesamtpreis": None}],
        }

        results = build_validation_results(
            document_id=1,
            invoice_id=2,
            normalized=normalized,
            duplicate_count=0,
            valid_invoice_types=VALID_TYPES,
        )
        checks = {row["check_name"]: row for row in results}

        self.assertNotIn("null_gesamt_netto", checks)
        self.assertNotIn("null_tva", checks)
        self.assertFalse(checks["pos_amount_present_1"]["passed"])
        self.assertNotIn("tva_requires_net_and_gross", checks)
        self.assertEqual(checks["amounts_are_valid_decimals"]["actual_value"], "null, 0.00, 100.00, null, null")

    def test_missing_net_and_tax_is_valid_when_gross_exists(self):
        normalized = {
            "client": {"name_original": "Bauhaus GmbH & Co. KG", "name_normalized": "bauhaus gmbh co kg"},
            "invoice": {
                "invoice_number": "9378",
                "invoice_date": "2026-08-07",
                "invoice_type": "receipt",
                "gesamt_netto": None,
                "tva": None,
                "gesamtbetrag": Decimal("38.39"),
            },
            "invoice_pos": [],
        }

        results = build_validation_results(
            document_id=1,
            invoice_id=2,
            normalized=normalized,
            duplicate_count=0,
            valid_invoice_types=VALID_TYPES,
        )
        checks = {row["check_name"]: row for row in results}

        self.assertNotIn("null_gesamt_netto", checks)
        self.assertNotIn("null_tva", checks)
        self.assertTrue(checks["null_gesamtbetrag"]["passed"])
        self.assertTrue(checks["required_invoice_fields_complete"]["passed"])
        self.assertNotIn("tva_requires_net_and_gross", checks)

    def test_pos_sum_must_match_gross_total(self):
        normalized = {
            "client": {"name_original": "Bauhaus GmbH & Co. KG", "name_normalized": "bauhaus gmbh co kg"},
            "invoice": {
                "invoice_number": "9378",
                "invoice_date": "2026-08-07",
                "invoice_type": "receipt",
                "gesamt_netto": None,
                "tva": None,
                "gesamtbetrag": Decimal("38.39"),
            },
            "invoice_pos": [
                {"pos_number": 1, "gesamt_netto": None, "gesamtpreis": Decimal("10.00")},
                {"pos_number": 2, "gesamt_netto": None, "gesamtpreis": Decimal("28.39")},
            ],
        }

        results = build_validation_results(
            document_id=1,
            invoice_id=2,
            normalized=normalized,
            duplicate_count=0,
            valid_invoice_types=VALID_TYPES,
        )
        checks = {row["check_name"]: row for row in results}

        self.assertTrue(checks["pos_sum_matches_gross_total"]["passed"])
        self.assertTrue(checks["pos_net_sum_matches_invoice_net"]["passed"])

    def test_pos_net_sum_must_match_invoice_net(self):
        normalized = {
            "client": {"name_original": "ACME GmbH", "name_normalized": "acme"},
            "invoice": {
                "invoice_number": "R-200",
                "invoice_date": "2026-08-07",
                "invoice_type": "invoice",
                "gesamt_netto": Decimal("100.00"),
                "tva": Decimal("19.00"),
                "gesamtbetrag": Decimal("119.00"),
            },
            "invoice_pos": [
                {"pos_number": 1, "gesamt_netto": Decimal("45.00"), "gesamtpreis": None},
                {"pos_number": 2, "gesamt_netto": Decimal("55.00"), "gesamtpreis": None},
            ],
        }

        results = build_validation_results(
            document_id=1,
            invoice_id=2,
            normalized=normalized,
            duplicate_count=0,
            valid_invoice_types=VALID_TYPES,
        )
        checks = {row["check_name"]: row for row in results}

        self.assertTrue(checks["pos_net_sum_matches_invoice_net"]["passed"])
        self.assertTrue(checks["pos_sum_matches_gross_total"]["passed"])


if __name__ == "__main__":
    unittest.main()
