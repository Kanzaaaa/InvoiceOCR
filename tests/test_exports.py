import unittest
from unittest.mock import patch

from openpyxl import load_workbook

from app.services.exporter import export_invoice_review_to_excel


class ExportQueryTests(unittest.TestCase):
    def test_combined_invoice_review_export_nests_positions_under_invoice(self):
        invoices = [
            {
                "Rechnungs-ID": 1,
                "Rechnungsnummer": "R-100",
                "Dateiname": "invoice.pdf",
                "Kunde/Lieferant": "ACME GmbH",
                "Strasse": "Mainstr.",
                "Hausnummer": "10",
                "PLZ": "60386",
                "Stadt": "Frankfurt",
                "Dokumenttyp": "invoice",
                "Belegdatum": "2026-08-01",
                "Netto": "100.00",
                "USt": "19.00",
                "Brutto": "119.00",
                "Validierungsstatus": "ok",
                "Validierungsfehler": 0,
            },
            {
                "Rechnungs-ID": 2,
                "Rechnungsnummer": "R-200",
                "Dateiname": "invoice-2.pdf",
                "Kunde/Lieferant": "Bauhaus GmbH",
                "Strasse": None,
                "Hausnummer": None,
                "PLZ": "60386",
                "Stadt": "Frankfurt",
                "Dokumenttyp": "receipt",
                "Belegdatum": "2026-08-02",
                "Netto": None,
                "USt": None,
                "Brutto": "38.39",
                "Validierungsstatus": "ok",
                "Validierungsfehler": 0,
            }
        ]
        positions = [
            {
                "Rechnungs-ID": 1,
                "Rechnungsnummer": "R-100",
                "Kunde/Lieferant": "ACME GmbH",
                "Belegdatum": "2026-08-01",
                "Position": 1,
                "Positions-Netto": "100.00",
                "Positions-Brutto": "119.00",
            }
        ]

        with patch("app.services.exporter.get_conn", return_value=FakeConnection([invoices, positions])):
            workbook_file = export_invoice_review_to_excel()

        workbook = load_workbook(workbook_file)
        worksheet = workbook["invoice_review"]

        self.assertEqual(worksheet["A1"].value, "Rechnungs-ID")
        self.assertEqual(worksheet["B1"].value, "Rechnungsnummer")
        self.assertEqual(worksheet["E1"].value, "Strasse")
        self.assertEqual(worksheet["F1"].value, "Hausnummer")
        self.assertEqual(worksheet["G1"].value, "PLZ")
        self.assertEqual(worksheet["H1"].value, "Stadt")
        self.assertEqual(worksheet["A2"].value, 1)
        self.assertEqual(worksheet["E2"].value, "Mainstr.")
        self.assertEqual(worksheet["F2"].value, "10")
        self.assertEqual(worksheet["G2"].value, "60386")
        self.assertEqual(worksheet["H2"].value, "Frankfurt")
        self.assertEqual(worksheet["B3"].value, "Rechnungs-ID")
        self.assertEqual(worksheet["C3"].value, "Rechnungsnummer")
        self.assertEqual(worksheet["F3"].value, "Position")
        self.assertEqual(worksheet["B4"].value, 1)
        self.assertEqual(worksheet["F4"].value, 1)
        self.assertEqual(worksheet["A5"].value, 2)
        self.assertEqual(worksheet["B5"].value, "R-200")
        self.assertEqual(worksheet["A2"].fill.fgColor.rgb, "00FFFF00")
        self.assertEqual(worksheet["A5"].fill.fgColor.rgb, "00FFFF00")


class FakeConnection:
    def __init__(self, results):
        self.results = results
        self.index = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, query):
        result = self.results[self.index]
        self.index += 1
        return FakeCursor(result)


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows


if __name__ == "__main__":
    unittest.main()
