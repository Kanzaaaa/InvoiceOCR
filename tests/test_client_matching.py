import unittest

from app.services.client_matching import build_name_address_fingerprint


class ClientMatchingTests(unittest.TestCase):
    def test_name_address_fingerprint_normalizes_address_parts(self):
        fingerprint = build_name_address_fingerprint(
            "x cite promotion event gmbh",
            {
                "street": "Cassellastr.",
                "house_number": "30-32",
                "postal_code": "60386",
                "city": "Frankfurt am Main",
            },
        )

        self.assertEqual(
            fingerprint,
            "x cite promotion event gmbh|60386|frankfurt am main|cassellastr|3032",
        )

    def test_name_address_fingerprint_requires_postal_code_and_city(self):
        self.assertIsNone(
            build_name_address_fingerprint(
                "bauhaus gmbh co kg",
                {"street": "Hanauer Landstrasse", "house_number": "517-543"},
            )
        )


if __name__ == "__main__":
    unittest.main()
