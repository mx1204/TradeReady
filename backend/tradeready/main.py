from __future__ import annotations

from typing import Annotated

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .agents import classification_agent, classification_preview_critic_agent, restriction_agent
from .chat import chatbot_reply
from .evidence import evidence_by_id
from .models import ChatRequest, ClassificationPreviewRequest, ClassificationPreviewResult, ComplianceRunRequest, SwitchDestinationRequest
from .orchestrator import create_compliance_run, get_run, switch_destination
from .vision import identify_product


app = FastAPI(title="TradeReady Backend MVP", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/product-identification")
async def product_identification(
    image: Annotated[UploadFile, File(...)],
    hint: Annotated[str | None, Form()] = None,
    require_vision: Annotated[bool, Form()] = False,
):
    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=422, detail="Uploaded image is empty.")
    result = await identify_product(
        image_bytes=image_bytes,
        content_type=image.content_type,
        filename=image.filename,
        hint=hint,
        require_vision=require_vision,
    )
    if result is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "OpenAI vision did not return a usable product detection. "
                "Check OPENAI_API_KEY and OPENAI_VISION_MODEL, then retry with a product photo."
            ),
        )
    return result


@app.post("/api/classification-preview")
def classification_preview(request: ClassificationPreviewRequest):
    product_confirmed = request.product_confirmed or request.product_facts.confirmed
    product_facts = request.product_facts.model_copy(update={"confirmed": product_confirmed})
    classification = classification_agent(product_facts, request.destination_country)
    restriction = restriction_agent(product_facts, request.destination_country)
    critic = classification_preview_critic_agent(
        product_facts,
        product_confirmed,
        classification,
        restriction,
    )
    evidence_ids: set[str] = set()
    evidence_ids.update(classification.source_ids)
    evidence_ids.update(restriction.source_ids)
    return ClassificationPreviewResult(
        workflow_status="human_review_required" if critic.status == "human_review_required" else "ready",
        product_facts=product_facts,
        classification=classification,
        restricted_goods=restriction,
        evidence_pack=evidence_by_id(evidence_ids),
        critic=critic,
    )


@app.post("/api/chat")
def chat(request: ChatRequest):
    return chatbot_reply(request)


@app.post("/api/compliance-runs")
def compliance_runs(request: ComplianceRunRequest):
    return create_compliance_run(request)


@app.get("/api/compliance-runs/{run_id}")
def compliance_run(run_id: str):
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Compliance run not found.")
    return run


@app.post("/api/compliance-runs/{run_id}/switch-destination")
def switch_compliance_destination(run_id: str, request: SwitchDestinationRequest):
    run = switch_destination(run_id, request.new_destination_country)
    if not run:
        raise HTTPException(status_code=404, detail="Compliance run not found or cannot be switched.")
    return run
