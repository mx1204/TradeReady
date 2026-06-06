# TradeReady Backend MVP

FastAPI backend for the Malaysia <-> Singapore electronics compliance demo.

## What It Implements

- `POST /api/product-identification`
  - Accepts a product image.
  - Uses OpenAI vision when `OPENAI_API_KEY` and the `openai` package are available.
  - Falls back to filename or optional `hint` matching for hackathon demo reliability.
  - Returns product facts and asks the frontend to confirm the detected product.

- `POST /api/compliance-runs`
  - Accepts confirmed product facts, destination country, and shipment text/fields.
  - Produces HS/local code, duty/tax estimate, restriction checks, required documents, auto-filled declaration fields, evidence citations, and critic status.

- `POST /api/compliance-runs/{id}/switch-destination`
  - Regenerates the compliance package for Malaysia or Singapore.
  - Returns a jurisdiction diff.

## Run Locally

**1. Clone the repo**
```powershell
git clone https://github.com/mx1204/TradeReady.git
cd TradeReady
```

**2. Create a virtual environment and install dependencies**
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**3. Set up your `.env` file** (see next section for details)

**4. Start the app**
```powershell
.\start-tradeready.ps1
```

Then open `http://127.0.0.1:4174` in your browser.

## OpenAI API Key For Photo Analysis

The API key belongs on the backend only. Do not paste it into `index.html` or any frontend JavaScript.

Recommended setup:

1. Copy `.env.example` to `.env`.
2. Open `.env`.
3. Replace the placeholder:

```text
OPENAI_API_KEY=sk-your-real-key-here
OPENAI_VISION_MODEL=gpt-4.1-mini
```

4. Start the merged demo:

```powershell
.\start-tradeready.ps1
```

The launcher automatically loads `.env` into the FastAPI backend. When you upload a product photo, the frontend sends the image to:

```text
POST /api/product-identification
```

Then the backend uses `OPENAI_API_KEY` to call OpenAI vision. If `.env` is missing or the key is invalid, the app still runs and falls back to the product description/hint path for demo reliability.

For the merged UI + backend demo:

```powershell
.\start-tradeready.ps1
```

Then open:

```text
http://127.0.0.1:4174
```

For backend only:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:OPENAI_API_KEY="sk-..."
python -m uvicorn backend.tradeready.main:app --reload --port 8000
```

The backend works without `OPENAI_API_KEY`; product identification then uses the uploaded filename or `hint` form field.

## Demo Request

See [docs/backend-api-contract.md](docs/backend-api-contract.md) for the frontend contract and [examples/compliance-request.json](examples/compliance-request.json) for a ready request body.

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/compliance-runs `
  -ContentType "application/json" `
  -Body '{
    "product_confirmed": true,
    "product_facts": {
      "category": "wireless_earbuds",
      "label": "Wireless earbuds",
      "wireless": true,
      "battery": true,
      "mains_powered": false,
      "confidence": 0.91
    },
    "destination_country": "Malaysia",
    "shipment_text": "200 units wireless earbuds, SGD 45 each, shipping Singapore to Malaysia, invoice TR-001"
  }'
```

## Submission Summary

TradeReady uses OpenAI vision to identify product facts from a user photo, confirms the result with the user, then runs a source-grounded compliance workflow. Shipment details are supplied by the user through text or frontend voice capture. The backend retrieves Malaysia/Singapore electronics rules from a cached evidence store, computes duties and document requirements, and uses a critic agent to verify that every output is supported by evidence. Unsupported or conflicting outputs are flagged for human review instead of being returned as confident answers.

## Known Limits

- Cached evidence is a demo dataset, not a production customs database.
- HS/local tariff codes and rates must be verified against official portals before real declarations.
- Commercial fields that cannot be inferred from the photo must come from the user.
- Uploaded photos are used only for product identification; they do not establish quantity, value, origin, seller, or consignee details.
