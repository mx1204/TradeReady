# Backend API Contract

## Product Identification

`POST /api/product-identification`

Multipart form fields:

- `image`: required product image.
- `hint`: optional text fallback such as `wireless earbuds`.

Returns product facts and `confirmation_required: true`. The frontend must ask the user to confirm the product before calling compliance generation.

## Compliance Run

`POST /api/compliance-runs`

Required JSON fields:

- `product_confirmed`: must be `true`.
- `product_facts`: confirmed product facts from the identification step.
- `destination_country`: `Malaysia` or `Singapore`.
- `shipment_text` or `shipment`: user-provided quantity, unit value, currency, origin, destination, and optional invoice/seller/consignee details.

If required details are missing, the backend returns `workflow_status: "needs_user_input"` instead of fabricating commercial fields.

## Switch Destination

`POST /api/compliance-runs/{run_id}/switch-destination`

Required JSON field:

- `new_destination_country`: `Malaysia` or `Singapore`.

Returns a regenerated compliance package plus `jurisdiction_diff`.

## Supported MVP Categories

- `wireless_earbuds`
- `bluetooth_speaker`
- `smartwatch`
- `phone_charger`

## Critic Status

- `pass`: all MVP checks passed.
- `needs_user_input`: required user-supplied fields or product confirmation are missing.
- `human_review_required`: compliance output was generated but failed validation or lacks source support.
