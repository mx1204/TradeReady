from __future__ import annotations

from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .models import ComplianceRunRequest, SwitchDestinationRequest
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
):
    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=422, detail="Uploaded image is empty.")
    return await identify_product(
        image_bytes=image_bytes,
        content_type=image.content_type,
        filename=image.filename,
        hint=hint,
    )


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
