# TradeReady Project Context

## Project

TradeReady is a Sea x OpenAI Codex Hackathon prototype for Shopee-style cross-border seller compliance.

The current focus is interface-first. Backend integration will come later.

## Product Direction

The product should feel like a real seller-facing tool, not a static pitch page.

Core journey:

1. Seller chooses a destination country.
2. After selection, only a collapsed summary appears.
3. Seller clicks `Show details` to review market attributes such as population, tax, duty, certificate, processing time, and landed cost.
4. Seller clicks Next.
5. A full-page animated transition plays.
6. AI checks certificate and requirement needs.
7. AI fills certificate registration forms.
8. AI brings required submission documents into the program.
9. Seller can download a PDF pack.

## UI Style

- Clean Shopee-like style.
- White background.
- Shopee orange primary action.
- Minimal containers.
- Step-by-step screens.
- Do not show all future steps upfront.
- First screen should only show country choices at initial load.
- After country click, show a short collapsed summary and Next.
- Full details appear only after clicking `Show details`.

## Country Selection

Initial screen:

- Singapore
- Malaysia
- Indonesia
- Thailand
- Vietnam

Each country button should show a visible flag and country name only at first.

After clicking a country, show only a collapsed summary first.

After clicking `Show details`, show:

- Population
- Import duty
- GST/SST/PPN/VAT
- Certificate requirement
- Processing time
- Landed cost estimate

Details can be collapsed back into a short summary.

## AI Chatbot Mascot

The chatbot mascot should be a colorful 3D-style dolphin inspired by the supplied prototype image.

Requirements:

- Not a childish cartoon.
- More polished 3D mascot feel.
- Color bands: red, orange, green, cyan, blue.
- Fixed in the lower screen area so it does not block users.
- Currently changed to stay in place and rotate/float gently.
- Can be dragged.
- Can be paused/resumed.
- Clicking dolphin opens chatbot.

## Mascot Controls

- A visible Pause button appears near the dolphin.
- Pause stops mascot movement/animation state.
- Resume restarts gentle in-place motion.
- Dolphin can be dragged, then remains where dropped.

## Transition Animation

On Next:

- Full-page transition, not trapped inside a container.
- Dolphin/fish starts from the left side.
- Wave line appears in the middle, like:

```text
fish ~~~~~~~~~~~~~ flag
```

- Destination country flag appears on the right.
- Dolphin should swim to the flag before transition ends.
- Current duration: 2.4s.

## Current Files

- `index.html` - runnable UI prototype.
- `start-demo.ps1` - starts local server.
- `README.md` - simple run instructions.
- `PROJECT_CONTEXT.md` - this project context file.

## Run

```powershell
.\start-demo.ps1
```

Open:

```text
http://127.0.0.1:4174
```

## Current Scope

This is frontend-only.

Backend later:

- Real tax data retrieval.
- Real certificate requirement lookup.
- Real AI chatbot reasoning.
- Real form filling.
- Real PDF generation.
- Real source citations.
