from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


SUPPORTED_CATEGORIES = {
    "wireless_earbuds",
    "bluetooth_speaker",
    "smartwatch",
    "phone_charger",
    "smartphone",
}

SUPPORTED_JURISDICTIONS = {"Malaysia", "Singapore"}


class ProductFacts(BaseModel):
    model_config = ConfigDict(extra="allow")

    category: str
    label: str | None = None
    wireless: bool = False
    battery: bool = False
    mains_powered: bool = False
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    source: str = "vision"
    confirmed: bool = False


class ProductAlternative(BaseModel):
    category: str
    label: str
    confidence: float = Field(ge=0.0, le=1.0)


class ProductIdentificationResponse(BaseModel):
    detected_category: str
    product_facts: ProductFacts
    alternatives: list[ProductAlternative] = Field(default_factory=list)
    confirmation_required: bool = True
    confirmation_prompt: str = "Is this product correct?"
    notes: list[str] = Field(default_factory=list)


class ShipmentDetails(BaseModel):
    origin_country: str | None = None
    destination_country: str
    quantity: int | None = Field(default=None, ge=1)
    unit_value: float | None = Field(default=None, ge=0)
    currency: str | None = None
    seller_name: str | None = None
    consignee_name: str | None = None
    invoice_number: str | None = None


class ComplianceRunRequest(BaseModel):
    product_facts: ProductFacts
    product_confirmed: bool = False
    destination_country: str
    shipment_text: str | None = None
    shipment: ShipmentDetails | None = None


class SwitchDestinationRequest(BaseModel):
    new_destination_country: str


class EvidenceItem(BaseModel):
    id: str
    jurisdiction: str
    rule_type: str
    source_name: str
    source_url: str
    retrieved_at: str
    summary: str
    data: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class ClassificationResult(BaseModel):
    hs6: str
    local_code: str
    description: str
    rationale: str
    confidence: float = Field(ge=0.0, le=1.0)
    source_ids: list[str] = Field(default_factory=list)
    alternatives: list[dict[str, Any]] = Field(default_factory=list)


class TaxLine(BaseModel):
    name: str
    rate: float
    base_amount: float
    amount: float
    currency: str
    source_ids: list[str] = Field(default_factory=list)


class DutyTaxResult(BaseModel):
    customs_value: float
    import_duty: TaxLine
    taxes: list[TaxLine]
    landed_cost_estimate: float
    currency: str
    source_ids: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class RestrictedGoodsResult(BaseModel):
    status: Literal["unrestricted", "conditional", "restricted", "prohibited", "unknown"]
    requirements: list[str] = Field(default_factory=list)
    certification_bodies: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class DocumentRequirement(BaseModel):
    name: str
    purpose: str
    required: bool = True
    source_ids: list[str] = Field(default_factory=list)


class AutoFilledFields(BaseModel):
    declaration_type: str
    fields: dict[str, Any]
    source_ids: list[str] = Field(default_factory=list)


class CriticResult(BaseModel):
    status: Literal["pass", "flagged", "human_review_required", "needs_user_input"]
    issues: list[str] = Field(default_factory=list)
    checks: list[str] = Field(default_factory=list)


class NeedsInputResult(BaseModel):
    workflow_status: Literal["needs_user_input"] = "needs_user_input"
    missing_fields: list[str]
    message: str
    product_facts: ProductFacts | None = None
    shipment: ShipmentDetails | None = None
    critic: CriticResult


class CompliancePackage(BaseModel):
    workflow_status: Literal["ready", "human_review_required"] = "ready"
    run_id: str
    product_facts: ProductFacts
    shipment: ShipmentDetails
    classification: ClassificationResult
    duty_tax: DutyTaxResult
    restricted_goods: RestrictedGoodsResult
    documents_required: list[DocumentRequirement]
    auto_filled_fields: AutoFilledFields
    evidence_pack: list[EvidenceItem]
    critic: CriticResult
    jurisdiction_diff: dict[str, Any] | None = None
    disclaimer: str = (
        "Proof-of-concept output. Verify all classifications, rates, permits, "
        "and declaration fields against official customs sources before use."
    )
