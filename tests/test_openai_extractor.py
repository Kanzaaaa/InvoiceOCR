import unittest

from app.services.openai_extractor import OPENAI_RESPONSE_FORMAT


class OpenAIExtractorTests(unittest.TestCase):
    def test_openai_response_format_matches_downstream_schema(self):
        schema = OPENAI_RESPONSE_FORMAT["schema"]

        self.assertEqual(OPENAI_RESPONSE_FORMAT["type"], "json_schema")
        self.assertTrue(OPENAI_RESPONSE_FORMAT["strict"])
        self.assertEqual(schema["required"], ["client", "invoice", "invoice_pos"])
        self.assertEqual(
            schema["properties"]["client"]["required"],
            ["name", "street", "house_number", "postal_code", "city"],
        )
        self.assertEqual(
            schema["properties"]["invoice"]["required"],
            ["invoice_number", "invoice_date", "invoice_type", "gesamt_netto", "tva", "gesamtbetrag"],
        )
        self.assertEqual(
            schema["properties"]["invoice_pos"]["items"]["required"],
            ["gesamt_netto", "gesamtpreis"],
        )


if __name__ == "__main__":
    unittest.main()
