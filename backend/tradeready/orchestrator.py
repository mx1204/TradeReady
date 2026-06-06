from __future__ import annotations

from uuid import uuid4

from .agents import (
    classification_agent,
    critic_agent,
    document_agent,
    duty_tax_agent,
    restriction_agent,
)
from .evidence import evidence_by_id
from .models import (
    CompliancePackage,
    ComplianceRunRequest,
    CriticResult,
    NeedsInputResult,
    ShipmentDetails,
)
from .parser import merge_shipment_details, missing_required_shipment_fields, normalize_country


RUNS: dict[str, CompliancePackage] = {}


def create_compliance_run(request: ComplianceRunRequest) -> CompliancePackage | NeedsInputResult:
    run_id = str(uuid4())
    result = build_compliance_package(request, run_id=run_id)
    if isinstance(result, CompliancePackage):
        RUNS[run_id] = result
    return result


def switch_destination(run_id: str, new_destination_country: str) -> CompliancePackage | None:
    previous = RUNS.get(run_id)
    if not previous:
        return None

    shipment = previous.shipment.model_copy(
        update={"destination_country": normalize_country(new_destination_country) or new_destination_country}
    )
    request = ComplianceRunRequest(
        product_facts=previous.product_facts,
        product_confirmed=True,
        destination_country=shipment.destination_country,
        shipment=shipment,
    )
    result = build_compliance_package(request, run_id=run_id)
    if not isinstance(result, CompliancePackage):
        return None
    result.jurisdiction_diff = build_jurisdiction_diff(previous, result)
    RUNS[run_id] = result
    return result


def get_run(run_id: str) -> CompliancePackage | None:
    return RUNS.get(run_id)


def build_compliance_package(
    request: ComplianceRunRequest,
    run_id: str | None = None,
) -> CompliancePackage | NeedsInputResult:
    normalized_destination = normalize_country(request.destination_country) or request.destination_country
    shipment = merge_shipment_details(request.shipment_text, normalized_destination, request.shipment)
    if normalize_country(shipment.destination_country):
        shipment.destination_country = normalize_country(shipment.destination_country) or shipment.destination_country

    product_confirmed = request.product_confirmed or request.product_facts.confirmed
    product_facts = request.product_facts.model_copy(update={"confirmed": product_confirmed})

    missing = missing_required_shipment_fields(shipment)
    if not product_confirmed:
        missing = ["product_confirmation", *missing]
    if missing:
        return NeedsInputResult(
            missing_fields=missing,
            message="Additional user input is required before compliance documents can be prepared.",
            product_facts=product_facts,
            shipment=shipment,
            critic=CriticResult(
                status="needs_user_input",
                issues=[f"Missing required field: {field}" for field in missing],
                checks=[],
            ),
        )

    run_id = run_id or str(uuid4())
    classification = classification_agent(product_facts, shipment.destination_country)
    duty_tax = duty_tax_agent(shipment, shipment.destination_country)
    restriction = restriction_agent(product_facts, shipment.destination_country)
    documents, auto_fields = document_agent(
        product_facts,
        shipment,
        classification,
        duty_tax,
        restriction,
        run_id,
    )
    critic = critic_agent(
        product_facts,
        product_confirmed,
        shipment,
        classification,
        duty_tax,
        restriction,
        documents,
        auto_fields,
    )

    evidence_ids: set[str] = set()
    evidence_ids.update(classification.source_ids)
    evidence_ids.update(duty_tax.source_ids)
    evidence_ids.update(restriction.source_ids)
    evidence_ids.update(auto_fields.source_ids)
    for doc in documents:
        evidence_ids.update(doc.source_ids)

    return CompliancePackage(
        workflow_status="human_review_required"
        if critic.status == "human_review_required"
        else "ready",
        run_id=run_id,
        product_facts=product_facts,
        shipment=shipment,
        classification=classification,
        duty_tax=duty_tax,
        restricted_goods=restriction,
        documents_required=documents,
        auto_filled_fields=auto_fields,
        evidence_pack=evidence_by_id(evidence_ids),
        critic=critic,
    )


def build_jurisdiction_diff(
    previous: CompliancePackage,
    current: CompliancePackage,
) -> dict[str, object]:
    return {
        "from": previous.shipment.destination_country,
        "to": current.shipment.destination_country,
        "classification": {
            "old_local_code": previous.classification.local_code,
            "new_local_code": current.classification.local_code,
            "hs6_changed": previous.classification.hs6 != current.classification.hs6,
        },
        "duty_tax": {
            "old_tax": [line.model_dump() for line in previous.duty_tax.taxes],
            "new_tax": [line.model_dump() for line in current.duty_tax.taxes],
            "old_landed_cost": previous.duty_tax.landed_cost_estimate,
            "new_landed_cost": current.duty_tax.landed_cost_estimate,
        },
        "restricted_goods": {
            "old_status": previous.restricted_goods.status,
            "new_status": current.restricted_goods.status,
            "old_certification_bodies": previous.restricted_goods.certification_bodies,
            "new_certification_bodies": current.restricted_goods.certification_bodies,
        },
        "documents": {
            "old": [doc.name for doc in previous.documents_required],
            "new": [doc.name for doc in current.documents_required],
        },
    }
