from __future__ import annotations

import base64
import json
import os
import re
from typing import Any

from .models import ProductAlternative, ProductFacts, ProductIdentificationResponse


CATEGORY_FACTS: dict[str, dict[str, Any]] = {
    "wireless_earbuds": {
        "label": "Wireless earbuds",
        "wireless": True,
        "battery": True,
        "mains_powered": False,
        "keywords": ["earbud", "earbuds", "earphone", "earphones", "headphone", "airpods"],
    },
    "bluetooth_speaker": {
        "label": "Bluetooth speaker",
        "wireless": True,
        "battery": True,
        "mains_powered": False,
        "keywords": ["bluetooth speaker", "speaker", "portable speaker"],
    },
    "smartwatch": {
        "label": "Smartwatch",
        "wireless": True,
        "battery": True,
        "mains_powered": False,
        "keywords": ["smartwatch", "smart watch", "fitness tracker", "watch"],
    },
    "phone_charger": {
        "label": "Phone charger",
        "wireless": False,
        "battery": False,
        "mains_powered": True,
        "keywords": ["charger", "adapter", "usb-c", "power adapter", "phone charger"],
    },
}


async def identify_product(
    image_bytes: bytes,
    content_type: str | None = None,
    filename: str | None = None,
    hint: str | None = None,
    require_vision: bool = False,
) -> ProductIdentificationResponse | None:
    if os.getenv("OPENAI_API_KEY"):
        response = await _identify_with_openai(image_bytes, content_type)
        if response:
            return response
    if require_vision:
        return None
    return identify_from_text(" ".join(filter(None, [filename, hint])))


def identify_from_text(text: str | None) -> ProductIdentificationResponse:
    category = _match_category(text or "") or "wireless_earbuds"
    facts = _facts_for_category(category, confidence=0.78 if text else 0.55, source="fallback")
    notes = []
    if not text:
        notes.append("Fallback path used because no OpenAI vision result or filename hint was available.")
    return ProductIdentificationResponse(
        detected_category=category,
        product_facts=facts,
        alternatives=_alternatives(category),
        notes=notes,
    )


async def _identify_with_openai(
    image_bytes: bytes,
    content_type: str | None,
) -> ProductIdentificationResponse | None:
    try:
        from openai import OpenAI
    except Exception:
        return None

    mime_type = content_type or "image/jpeg"
    encoded = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:{mime_type};base64,{encoded}"
    client = OpenAI()
    prompt = (
        "Identify this product for a customs compliance workflow. "
        "Choose exactly one category from: wireless_earbuds, bluetooth_speaker, "
        "smartwatch, phone_charger. Return only JSON with keys: category, label, "
        "wireless, battery, mains_powered, confidence, alternatives."
    )
    try:
        response = client.responses.create(
            model=os.getenv("OPENAI_VISION_MODEL", "gpt-4.1-mini"),
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {
                            "type": "input_image",
                            "image_url": data_url,
                            "detail": "low",
                        },
                    ],
                }
            ],
        )
    except Exception:
        return None

    output_text = getattr(response, "output_text", "") or ""
    payload = _parse_json_object(output_text)
    category = _match_category(str(payload.get("category", ""))) if payload else None
    if not category:
        category = _match_category(output_text)
    if not category:
        return None

    facts = _facts_for_category(
        category,
        confidence=float(payload.get("confidence", 0.86)) if payload else 0.86,
        source="openai_vision",
    )
    if payload:
        facts.label = payload.get("label") or facts.label
        facts.wireless = bool(payload.get("wireless", facts.wireless))
        facts.battery = bool(payload.get("battery", facts.battery))
        facts.mains_powered = bool(payload.get("mains_powered", facts.mains_powered))

    return ProductIdentificationResponse(
        detected_category=category,
        product_facts=facts,
        alternatives=_alternatives(category),
        notes=["OpenAI vision path used."],
    )


def _match_category(text: str) -> str | None:
    lower = text.lower()
    for category, info in CATEGORY_FACTS.items():
        if category in lower:
            return category
        if any(keyword in lower for keyword in info["keywords"]):
            return category
    return None


def _facts_for_category(category: str, confidence: float, source: str) -> ProductFacts:
    info = CATEGORY_FACTS[category]
    return ProductFacts(
        category=category,
        label=info["label"],
        wireless=info["wireless"],
        battery=info["battery"],
        mains_powered=info["mains_powered"],
        confidence=max(0.0, min(confidence, 1.0)),
        source=source,
        confirmed=False,
    )


def _alternatives(primary: str) -> list[ProductAlternative]:
    alternatives = []
    for category, info in CATEGORY_FACTS.items():
        if category == primary:
            continue
        alternatives.append(
            ProductAlternative(category=category, label=info["label"], confidence=0.12)
        )
    return alternatives[:3]


def _parse_json_object(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
