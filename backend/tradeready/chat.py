from __future__ import annotations

import os
import re

from .models import ChatRequest, ChatResponse


SYSTEM_PROMPT = """
You are TradeReady's dolphin assistant for a SEA x OpenAI hackathon demo.
You help SMEs with Malaysia and Singapore electronics customs preparation.
Answer concisely and practically.
Use only the context provided by the app when discussing HS codes, tax, evidence,
critic status, or generated documents.
If a field is missing or uncertain, say it needs user input or human review.
Do not claim the output is official government advice.
""".strip()


def chatbot_reply(request: ChatRequest) -> ChatResponse:
    suggested_fields = _extract_form_fields(request.message)
    if os.getenv("OPENAI_API_KEY"):
        reply = _reply_with_openai(request)
        if reply:
            if suggested_fields:
                reply += "\n\nI found form details in your message. Please confirm before I fill them into the form."
            return ChatResponse(reply=reply, source="openai", suggested_fields=suggested_fields)
    return ChatResponse(
        reply=_local_reply(request, suggested_fields),
        source="local_fallback",
        suggested_fields=suggested_fields,
    )


def _reply_with_openai(request: ChatRequest) -> str | None:
    try:
        from openai import OpenAI
    except Exception:
        return None

    client = OpenAI()
    try:
        response = client.responses.create(
            model=os.getenv("OPENAI_CHAT_MODEL", os.getenv("OPENAI_VISION_MODEL", "gpt-5-mini")),
            instructions=SYSTEM_PROMPT,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": _build_context_prompt(request),
                        }
                    ],
                },
            ],
        )
    except Exception:
        return None

    text = getattr(response, "output_text", "") or ""
    return text.strip() or None


def _build_context_prompt(request: ChatRequest) -> str:
    product = request.product_facts.model_dump() if request.product_facts else {}
    evidence = [
        {
            "id": item.id,
            "source_name": item.source_name,
            "jurisdiction": item.jurisdiction,
            "rule_type": item.rule_type,
            "summary": item.summary,
        }
        for item in request.evidence_pack[:8]
    ]
    return (
        "Current app context:\n"
        f"- destination_country: {request.destination_country or 'not selected'}\n"
        f"- current_step: {request.current_step}\n"
        f"- product_facts: {product}\n"
        f"- classification: {request.classification or {}}\n"
        f"- critic: {request.critic or {}}\n"
        f"- evidence_summaries: {evidence}\n\n"
        f"User message: {request.message}"
    )


def _local_reply(request: ChatRequest, suggested_fields: dict[str, object] | None = None) -> str:
    text = request.message.lower()
    destination = request.destination_country or "the selected destination"
    product_label = request.product_facts.label if request.product_facts else None
    classification = request.classification or {}
    critic = request.critic or {}
    hs_code = classification.get("hs6") or classification.get("hs_code")
    local_code = classification.get("local_code") or classification.get("local_tariff_code")
    fill_note = ""
    if suggested_fields:
        labels = ", ".join(_FIELD_LABELS.get(key, key) for key in suggested_fields)
        fill_note = f" I also found form details: {labels}. Please confirm before I fill them into the form."

    if any(word in text for word in ["hs", "code", "tariff", "classification"]):
        if hs_code:
            return (
                f"For {product_label or 'this product'}, TradeReady currently has HS code {hs_code}"
                f"{f' and local tariff code {local_code}' if local_code else ''}. "
                "The critic still checks that this classification has cached evidence before it is trusted."
                f"{fill_note}"
            )
        return f"I need a confirmed product photo result before I can show the HS code.{fill_note}"

    if any(word in text for word in ["critic", "verify", "check", "confidence"]):
        status = critic.get("status")
        issues = critic.get("issues") or []
        if status:
            return (
                f"The critic status is {status}. "
                f"Issues: {'; '.join(issues) if issues else 'none returned'}. "
                "Low confidence, missing evidence, or missing required fields will be sent for human review."
                f"{fill_note}"
            )
        return f"The critic runs after product detection/classification. It checks evidence, confidence, tax math, wireless requirements, and missing fields.{fill_note}"

    if any(word in text for word in ["document", "invoice", "packing", "tradenet", "imda", "submit"]):
        return (
            "I can prepare a commercial invoice, packing list, transport document, "
            "telecom requirement worksheet, and customs declaration worksheet. "
            "Known fields are auto-filled; blank fields must be completed before submission."
            f"{fill_note}"
        )

    if any(phrase in text for phrase in ["fill form", "fill the form", "fill up the form", "complete form", "complete the form"]):
        return (
            "I can fill the form after you give me the field values. "
            "For example: quantity is 200, unit value is 1600 SGD, origin is Malaysia, "
            "seller is Jason, buyer is Nora, invoice is TR-001."
            f"{fill_note}"
        )

    if any(word in text for word in ["tax", "gst", "sst", "duty", "cost"]):
        return (
            f"For {destination}, the compliance run calculates customs value from quantity and unit value, "
            "then recomputes duty and tax deterministically. Run the AI compliance check to get the exact demo breakdown."
            f"{fill_note}"
        )

    if not request.product_facts:
        return f"Please choose a destination country, enter a short product description, and upload a product photo. I can then identify the product and help fill the customs fields.{fill_note}"

    return (
        f"I can help with {product_label or 'this product'} going to {destination}. "
        "Ask me about HS code, tax, certificates, documents, or critic verification."
        f"{fill_note}"
    )


_FIELD_LABELS = {
    "productDescriptionInput": "product description",
    "quantity": "quantity",
    "unitValue": "unit value",
    "currency": "currency",
    "originCountry": "origin country",
    "invoiceNumber": "invoice number",
    "sellerName": "seller / shipper",
    "consigneeName": "consignee / buyer",
}


def _extract_form_fields(message: str) -> dict[str, object]:
    text = message.strip()
    fields: dict[str, object] = {}

    quantity_match = re.search(
        r"\b(?:quantity\s*(?:is|:)?\s*)?(\d{1,7})\s*(?:units?|pcs|pieces?|iphones?|phones?|earbuds?|chargers?|speakers?|watches?)\b"
        r"|\bquantity\s*(?:is|:)?\s*(\d{1,7})\b",
        text,
        re.I,
    )
    if quantity_match:
        fields["quantity"] = int(quantity_match.group(1) or quantity_match.group(2))

    value_match = re.search(
        r"\b(?:unit\s+value|unit\s+price|price)\s*(?:is|:)?\s*(?:SGD|MYR|USD)?\s*([0-9]+(?:\.[0-9]{1,2})?)\s*(SGD|MYR|USD)?\b"
        r"|\b(SGD|MYR|USD)\s*([0-9]+(?:\.[0-9]{1,2})?)\s*(?:each|per\s+unit|/unit)?\b",
        text,
        re.I,
    )
    if value_match:
        if value_match.group(4):
            fields["currency"] = value_match.group(3).upper()
            fields["unitValue"] = float(value_match.group(4))
        else:
            if value_match.group(2):
                fields["currency"] = value_match.group(2).upper()
            fields["unitValue"] = float(value_match.group(1))

    currency_match = re.search(r"\bcurrency\s*(?:is|:)?\s*(SGD|MYR|USD)\b", text, re.I)
    if currency_match:
        fields["currency"] = currency_match.group(1).upper()

    route_match = re.search(r"\b(?:from|shipping\s+from|ship(?:ping)?|export(?:ing)?\s+from)\s+(Singapore|Malaysia)\s+(?:to|->)\s+(Singapore|Malaysia)\b", text, re.I)
    if route_match:
        fields["originCountry"] = _country_name(route_match.group(1))

    origin_match = re.search(r"\b(?:origin|country\s+of\s+origin|export\s+country)\s*(?:is|:)?\s*(Singapore|Malaysia)\b", text, re.I)
    if origin_match:
        fields["originCountry"] = _country_name(origin_match.group(1))

    invoice_match = re.search(
        r"\b(?:invoice\s*(?:number|no\.?)?|inv)\s*(?:is|:|#)?\s*([A-Z0-9][A-Z0-9._/-]{1,40})\b",
        text,
        re.I,
    )
    if invoice_match:
        fields["invoiceNumber"] = invoice_match.group(1)

    seller_match = re.search(
        r"\b(?:seller|shipper|exporter)\s*(?:is|:)?\s*([^,.;\n]+?)"
        r"(?=\s+\b(?:buyer|consignee|importer|invoice|origin|country|quantity|unit|price|currency)\b|[,.;\n]|$)",
        text,
        re.I,
    )
    if seller_match:
        fields["sellerName"] = _clean_party_name(seller_match.group(1))

    buyer_match = re.search(
        r"\b(?:buyer|consignee|importer)\s*(?:is|:)?\s*([^,.;\n]+?)"
        r"(?=\s+\b(?:seller|shipper|exporter|invoice|origin|country|quantity|unit|price|currency)\b|[,.;\n]|$)",
        text,
        re.I,
    )
    if buyer_match:
        fields["consigneeName"] = _clean_party_name(buyer_match.group(1))

    description_match = re.search(r"\b(?:product|description|item)\s*(?:is|:)\s*([^.;\n]+)", text, re.I)
    if description_match:
        description = description_match.group(1).strip()
        if not re.fullmatch(r"\d+", description):
            fields["productDescriptionInput"] = description

    return fields


def _country_name(value: str) -> str:
    return "Singapore" if value.lower().startswith("sing") else "Malaysia"


def _clean_party_name(value: str) -> str:
    return value.strip().strip("\"'")
