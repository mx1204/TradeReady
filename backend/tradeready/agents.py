from __future__ import annotations

from .evidence import find_category_classification, find_rule
from .models import (
    AutoFilledFields,
    ClassificationResult,
    CriticResult,
    DocumentRequirement,
    DutyTaxResult,
    ProductFacts,
    RestrictedGoodsResult,
    ShipmentDetails,
    TaxLine,
)


def classification_agent(product_facts: ProductFacts, destination_country: str) -> ClassificationResult:
    item = find_category_classification(product_facts.category)
    if not item:
        return ClassificationResult(
            hs6="UNKNOWN",
            local_code="UNKNOWN",
            description="No cached classification rule found.",
            rationale="The product category is outside the MVP electronics dataset.",
            confidence=0.0,
            source_ids=[],
        )

    local_key = "local_code_malaysia" if destination_country == "Malaysia" else "local_code_singapore"
    return ClassificationResult(
        hs6=item.data["hs6"],
        local_code=item.data[local_key],
        description=item.data["description"],
        rationale=(
            f"{product_facts.label or product_facts.category} maps to the cached "
            f"demo HS heading for {item.data['description'].lower()}"
        ),
        confidence=min(product_facts.confidence, 0.9),
        source_ids=[item.id],
    )


def duty_tax_agent(shipment: ShipmentDetails, destination_country: str) -> DutyTaxResult:
    tax_rule = find_rule(destination_country, "tax")
    if not tax_rule:
        zero = TaxLine(
            name="Import duty",
            rate=0.0,
            base_amount=0.0,
            amount=0.0,
            currency=shipment.currency,
            source_ids=[],
        )
        return DutyTaxResult(
            customs_value=0.0,
            import_duty=zero,
            taxes=[],
            landed_cost_estimate=0.0,
            currency=shipment.currency,
            source_ids=[],
            notes=["No tax rule found for destination."],
        )

    customs_value = round((shipment.quantity or 0) * (shipment.unit_value or 0.0), 2)
    duty_rate = float(tax_rule.data["import_duty_rate"])
    duty_amount = round(customs_value * duty_rate, 2)
    import_duty = TaxLine(
        name="Import duty",
        rate=duty_rate,
        base_amount=customs_value,
        amount=duty_amount,
        currency=shipment.currency,
        source_ids=[tax_rule.id],
    )

    tax_rate = float(tax_rule.data["tax_rate"])
    tax_base = customs_value + duty_amount
    tax_amount = round(tax_base * tax_rate, 2)
    tax_line = TaxLine(
        name=tax_rule.data["tax_name"],
        rate=tax_rate,
        base_amount=round(tax_base, 2),
        amount=tax_amount,
        currency=shipment.currency,
        source_ids=[tax_rule.id],
    )

    landed = round(customs_value + duty_amount + tax_amount, 2)
    return DutyTaxResult(
        customs_value=customs_value,
        import_duty=import_duty,
        taxes=[tax_line],
        landed_cost_estimate=landed,
        currency=shipment.currency,
        source_ids=[tax_rule.id],
        notes=[
            "Demo calculation uses cached MVP electronics rates; verify official tariff line before real use."
        ],
    )


def restriction_agent(product_facts: ProductFacts, destination_country: str) -> RestrictedGoodsResult:
    if destination_country == "Malaysia":
        if product_facts.wireless:
            return _restriction_from_rule(find_rule("Malaysia", "restriction", "wireless"))
        if product_facts.mains_powered:
            return _restriction_from_rule(find_rule("Malaysia", "restriction", "electrical"))
        return _restriction_from_rule(find_rule("Malaysia", "restriction", "electrical"), status="unrestricted")

    if product_facts.wireless:
        return _restriction_from_rule(find_rule("Singapore", "restriction", "wireless"))
    return _restriction_from_rule(find_rule("Singapore", "restriction", "controlled_goods"))


def document_agent(
    product_facts: ProductFacts,
    shipment: ShipmentDetails,
    classification: ClassificationResult,
    duty_tax: DutyTaxResult,
    restriction: RestrictedGoodsResult,
    run_id: str,
) -> tuple[list[DocumentRequirement], AutoFilledFields]:
    doc_rule = find_rule(shipment.destination_country, "documents")
    source_ids = [doc_rule.id] if doc_rule else []
    docs = [
        DocumentRequirement(
            name=doc["name"],
            purpose=doc["purpose"],
            required=True,
            source_ids=source_ids,
        )
        for doc in (doc_rule.data.get("documents", []) if doc_rule else [])
    ]

    declaration_type = (
        doc_rule.data.get("declaration_type", "Import declaration data")
        if doc_rule
        else "Import declaration data"
    )
    fields = {
        "invoice_number": shipment.invoice_number or f"TR-{run_id[:8].upper()}",
        "product_description": product_facts.label or product_facts.category,
        "hs6": classification.hs6,
        "local_tariff_code": classification.local_code,
        "origin_country": shipment.origin_country,
        "destination_country": shipment.destination_country,
        "quantity": shipment.quantity,
        "unit_value": shipment.unit_value,
        "currency": shipment.currency,
        "customs_value": duty_tax.customs_value,
        "import_duty_amount": duty_tax.import_duty.amount,
        "tax_amount": sum(line.amount for line in duty_tax.taxes),
        "landed_cost_estimate": duty_tax.landed_cost_estimate,
        "restriction_status": restriction.status,
        "certification_bodies": restriction.certification_bodies,
    }
    return docs, AutoFilledFields(
        declaration_type=declaration_type,
        fields=fields,
        source_ids=source_ids,
    )


def critic_agent(
    product_facts: ProductFacts,
    product_confirmed: bool,
    shipment: ShipmentDetails,
    classification: ClassificationResult,
    duty_tax: DutyTaxResult,
    restriction: RestrictedGoodsResult,
    documents: list[DocumentRequirement],
    auto_filled_fields: AutoFilledFields,
) -> CriticResult:
    issues: list[str] = []
    checks: list[str] = []

    if not product_confirmed:
        issues.append("Product identification has not been confirmed by the user.")
    else:
        checks.append("Product identity was user-confirmed.")

    if not classification.source_ids or classification.hs6 == "UNKNOWN":
        issues.append("HS classification has no supporting evidence.")
    else:
        checks.append("HS classification has cached source evidence.")

    expected_customs_value = round((shipment.quantity or 0) * (shipment.unit_value or 0.0), 2)
    expected_tax = round(
        (expected_customs_value + duty_tax.import_duty.amount)
        * (duty_tax.taxes[0].rate if duty_tax.taxes else 0),
        2,
    )
    if abs(expected_customs_value - duty_tax.customs_value) > 0.01:
        issues.append("Customs value does not match quantity multiplied by unit value.")
    elif duty_tax.taxes and abs(expected_tax - duty_tax.taxes[0].amount) > 0.01:
        issues.append("Tax amount does not match deterministic recomputation.")
    else:
        checks.append("Duty and tax math was recomputed successfully.")

    if not duty_tax.source_ids:
        issues.append("Duty/tax computation has no supporting evidence.")
    else:
        checks.append("Duty/tax rates have cached source evidence.")

    if product_facts.wireless and not restriction.source_ids:
        issues.append("Wireless product detected but no telecom/certification source was found.")
    elif product_facts.wireless and not restriction.certification_bodies:
        issues.append("Wireless product detected but no certification body was listed.")
    elif product_facts.wireless:
        checks.append("Wireless product triggered telecom/certification checks.")

    if not documents or not all(doc.source_ids for doc in documents):
        issues.append("Required document list is missing source evidence.")
    else:
        checks.append("Required documents have cached source evidence.")

    required_auto_fields = [
        "product_description",
        "hs6",
        "local_tariff_code",
        "origin_country",
        "destination_country",
        "quantity",
        "unit_value",
        "customs_value",
    ]
    missing_auto_fields = [
        field for field in required_auto_fields if auto_filled_fields.fields.get(field) in (None, "")
    ]
    if missing_auto_fields:
        issues.append(f"Auto-filled declaration fields are missing: {', '.join(missing_auto_fields)}.")
    else:
        checks.append("Required auto-filled declaration fields are present.")

    return CriticResult(
        status="human_review_required" if issues else "pass",
        issues=issues,
        checks=checks,
    )


def _restriction_from_rule(rule, status: str | None = None) -> RestrictedGoodsResult:
    if not rule:
        return RestrictedGoodsResult(
            status="unknown",
            requirements=[],
            certification_bodies=[],
            source_ids=[],
            notes=["No restriction evidence found."],
        )
    data_status = status or rule.data.get("status", "conditional")
    return RestrictedGoodsResult(
        status=data_status,
        requirements=rule.data.get("requirements", []),
        certification_bodies=rule.data.get("certification_bodies", []),
        source_ids=[rule.id],
    )
