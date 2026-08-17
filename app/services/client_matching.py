from typing import Any

from psycopg import Connection
from rapidfuzz import fuzz, process

from app.services.normalization import normalize_client_name


def get_or_create_client(
    conn: Connection,
    name_original: str | None,
    name_normalized: str | None,
    address: dict[str, Any] | None,
    threshold: int,
) -> dict[str, Any]:
    fallback_original = name_original or "Unknown Client"
    fallback_normalized = name_normalized or "unknown_client"
    address = address or {}
    fingerprint = build_name_address_fingerprint(fallback_normalized, address)

    with conn.cursor() as cur:
        if fingerprint:
            cur.execute("SELECT * FROM clients WHERE name_address_fingerprint = %s", (fingerprint,))
            existing = cur.fetchone()
            if existing:
                return _update_missing_address_fields(cur, existing, address, fingerprint)

        cur.execute("SELECT * FROM clients WHERE name_normalized = %s", (fallback_normalized,))
        existing = cur.fetchone()
        if existing:
            return _update_missing_address_fields(cur, existing, address, fingerprint)

        cur.execute("SELECT * FROM clients")
        clients = cur.fetchall()
        choices = {client["name_normalized"]: client for client in clients}
        match = process.extractOne(fallback_normalized, choices.keys(), scorer=fuzz.token_sort_ratio)

        if match and match[1] >= threshold:
            matched_client = choices[match[0]]
            if _address_compatible(matched_client, address):
                return _update_missing_address_fields(cur, matched_client, address, fingerprint)

        cur.execute(
            """
            INSERT INTO clients (
                name_original, name_normalized, street, house_number, postal_code, city,
                name_address_fingerprint
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                fallback_original,
                fallback_normalized,
                address.get("street"),
                address.get("house_number"),
                address.get("postal_code"),
                address.get("city"),
                fingerprint,
            ),
        )
        return cur.fetchone()


def build_name_address_fingerprint(name_normalized: str | None, address: dict[str, Any] | None) -> str | None:
    if not name_normalized:
        return None
    address = address or {}
    postal_code = _normalize_address_part(address.get("postal_code"))
    city = _normalize_address_part(address.get("city"))

    if not postal_code or not city:
        return None

    street = _normalize_address_part(address.get("street"))
    house_number = _normalize_house_number(address.get("house_number"))
    return "|".join([name_normalized, postal_code, city, street or "", house_number or ""])


def _update_missing_address_fields(
    cur,
    client: dict[str, Any],
    address: dict[str, Any],
    fingerprint: str | None,
) -> dict[str, Any]:
    next_values = {
        "street": client.get("street") or address.get("street"),
        "house_number": client.get("house_number") or address.get("house_number"),
        "postal_code": client.get("postal_code") or address.get("postal_code"),
        "city": client.get("city") or address.get("city"),
        "name_address_fingerprint": client.get("name_address_fingerprint") or fingerprint,
    }
    if all(client.get(key) == value for key, value in next_values.items()):
        return client

    cur.execute(
        """
        UPDATE clients
        SET street = %s,
            house_number = %s,
            postal_code = %s,
            city = %s,
            name_address_fingerprint = %s
        WHERE id = %s
        RETURNING *
        """,
        (
            next_values["street"],
            next_values["house_number"],
            next_values["postal_code"],
            next_values["city"],
            next_values["name_address_fingerprint"],
            client["id"],
        ),
    )
    return cur.fetchone()


def _address_compatible(client: dict[str, Any], address: dict[str, Any]) -> bool:
    extracted_values = {key: address.get(key) for key in ("street", "house_number", "postal_code", "city")}
    if not any(extracted_values.values()):
        return True

    for key, extracted_value in extracted_values.items():
        stored_value = client.get(key)
        if not stored_value or not extracted_value:
            continue
        if key == "house_number":
            if _normalize_house_number(stored_value) != _normalize_house_number(extracted_value):
                return False
            continue
        if _normalize_address_part(stored_value) != _normalize_address_part(extracted_value):
            return False

    return True


def _normalize_address_part(value: Any) -> str | None:
    return normalize_client_name(value)


def _normalize_house_number(value: Any) -> str | None:
    normalized = normalize_client_name(value)
    if normalized is None:
        return None
    return normalized.replace(" ", "")
