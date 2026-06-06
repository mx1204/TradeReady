from __future__ import annotations

import re

from .models import ShipmentDetails


COUNTRY_ALIASES = {
    "sg": "Singapore",
    "singapore": "Singapore",
    "my": "Malaysia",
    "malaysia": "Malaysia",
}

CURRENCY_ALIASES = {
    "S$": "SGD",
    "$": "SGD",
    "SGD": "SGD",
    "RM": "MYR",
    "MYR": "MYR",
    "USD": "USD",
}


def normalize_country(value: str | None) -> str | None:
    if not value:
        return None
    return COUNTRY_ALIASES.get(value.strip().lower())


def normalize_currency(value: str | None) -> str:
    if not value:
        return "SGD"
    return CURRENCY_ALIASES.get(value.strip().upper(), value.strip().upper())


def parse_shipment_text(text: str | None, destination_country: str | None = None) -> ShipmentDetails:
    body = text or ""
    lower = body.lower()

    quantity = _parse_quantity(lower)
    unit_value, currency = _parse_unit_value(body)
    origin, destination = _parse_route(lower)
    explicit_destination = normalize_country(destination_country)
    destination = explicit_destination or destination

    invoice = _parse_named_value(body, ["invoice", "invoice number", "inv"])
    seller = _parse_named_value(body, ["seller", "shipper"])
    consignee = _parse_named_value(body, ["consignee", "buyer", "recipient"])

    return ShipmentDetails(
        origin_country=origin,
        destination_country=destination or destination_country or "",
        quantity=quantity,
        unit_value=unit_value,
        currency=currency,
        seller_name=seller,
        consignee_name=consignee,
        invoice_number=invoice,
    )


def merge_shipment_details(
    text: str | None,
    destination_country: str,
    explicit: ShipmentDetails | None,
) -> ShipmentDetails:
    parsed = parse_shipment_text(text, destination_country)
    if not explicit:
        return parsed

    return ShipmentDetails(
        origin_country=explicit.origin_country or parsed.origin_country,
        destination_country=explicit.destination_country or parsed.destination_country,
        quantity=explicit.quantity or parsed.quantity,
        unit_value=explicit.unit_value if explicit.unit_value is not None else parsed.unit_value,
        currency=explicit.currency or parsed.currency,
        seller_name=explicit.seller_name or parsed.seller_name,
        consignee_name=explicit.consignee_name or parsed.consignee_name,
        invoice_number=explicit.invoice_number or parsed.invoice_number,
    )


def missing_required_shipment_fields(shipment: ShipmentDetails) -> list[str]:
    missing: list[str] = []
    if not shipment.origin_country:
        missing.append("origin_country")
    if not normalize_country(shipment.destination_country):
        missing.append("destination_country")
    if shipment.quantity is None:
        missing.append("quantity")
    if shipment.unit_value is None:
        missing.append("unit_value")
    if not shipment.currency:
        missing.append("currency")
    return missing


def _parse_quantity(lower: str) -> int | None:
    patterns = [
        r"\bquantity\s*[:=]\s*(\d+)\b",
        r"\b(\d+)\s*(?:units|unit|pcs|pieces|piece|x)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, lower)
        if match:
            return int(match.group(1))
    return None


def _parse_unit_value(text: str) -> tuple[float | None, str]:
    patterns = [
        r"\b(SGD|MYR|USD|RM|S\$|\$)\s*(\d+(?:\.\d+)?)\s*(?:each|per unit|\/unit|unit price)?\b",
        r"\b(?:unit value|unit price|price)\s*[:=]?\s*(SGD|MYR|USD|RM|S\$|\$)?\s*(\d+(?:\.\d+)?)\b",
        r"\b(\d+(?:\.\d+)?)\s*(SGD|MYR|USD)\s*(?:each|per unit|\/unit)?\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        groups = match.groups()
        if len(groups) == 2 and re.match(r"^\d", groups[0]):
            value = float(groups[0])
            currency = normalize_currency(groups[1])
        else:
            currency = normalize_currency(groups[0])
            value = float(groups[1])
        return value, currency
    return None, "SGD"


def _parse_route(lower: str) -> tuple[str | None, str | None]:
    countries = {
        key: value
        for key, value in COUNTRY_ALIASES.items()
        if re.search(rf"\b{re.escape(key)}\b", lower)
    }
    if "from" in lower and "to" in lower:
        match = re.search(r"from\s+([a-z]+)\s+to\s+([a-z]+)", lower)
        if match:
            return normalize_country(match.group(1)), normalize_country(match.group(2))
    arrow_match = re.search(r"\b(singapore|sg|malaysia|my)\s*(?:->|to)\s*(singapore|sg|malaysia|my)\b", lower)
    if arrow_match:
        return normalize_country(arrow_match.group(1)), normalize_country(arrow_match.group(2))
    if len(set(countries.values())) == 2:
        ordered = sorted(countries.items(), key=lambda kv: lower.index(kv[0]))
        return ordered[0][1], ordered[-1][1]
    return None, None


def _parse_named_value(text: str, labels: list[str]) -> str | None:
    for label in labels:
        match = re.search(rf"\b{re.escape(label)}\s*[:=]\s*([^,;\n]+)", text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
        bare_match = re.search(
            rf"\b{re.escape(label)}\s+([A-Z0-9][A-Z0-9_/-]+)",
            text,
            flags=re.IGNORECASE,
        )
        if bare_match:
            return bare_match.group(1).strip()
    return None
