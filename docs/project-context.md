# Project Context

## Project Goal

- Main objective: Build and present the TradeReady hackathon idea for the Sea & OpenAI Hackathon.
- Current status: The group idea is already written in the source report PDFs listed below; local markdown context is being created so Codex can reuse it across future tasks.
- Important deadlines:

## User Preferences

- Communication style: Ask clarification questions when an important point in the prompt is vague or unclear.
- Formatting preferences:
- Level of detail:
- When to ask clarification questions:

## Important Background

- Key decisions already made: The project is a group hackathon project with role allocation split across backend, frontend, admin/writeup/testing/video, and research/pitch/PPT.
- Constraints:
- Assumptions: The PDFs are canonical source reports for the group idea, but their contents have not yet been ingested into these markdown files.

## Core Multi-Agent Idea

TradeReady should use multi-agent cross-checking to make generated compliance outputs more reliable.

The system should not rely only on model training data. It should use RAG to retrieve current compliance rules directly from official government customs portals when the seller makes a request. Example source portals include `customs.gov.sg` for Singapore rules and `beacukai.go.id` for Indonesian rules. Retrieved source material is injected as verified context for the generator agent.

The generator agent creates the compliance output, such as a compliance script, classification explanation, or seller guidance, grounded in the retrieved official context.

A separate critic or supervisor agent then compares the generated output against the retrieved evidence. The critic is not just asking the same model to check itself; it independently verifies whether the generated answer matches the official source context. For example, if the generator classifies a product as HS 8518.30 but the retrieved Indonesian customs source indicates HS 8518.21 for that product category, the critic should flag the mismatch.

After the compliance output is verified, TradeReady should use the verified information to fill relevant platform or compliance forms on behalf of the seller. Auto-filled fields must be traceable to verified seller input or retrieved official evidence. If a required field cannot be filled confidently, the system should flag that field to the user and ask for the missing information instead of guessing.

When the critic detects a mismatch or low confidence, the system should escalate only that case to a human compliance reviewer with a clear conflict report. High-confidence cases can continue automatically. This is a human-on-the-loop design: the human reviewer is a safety net for edge cases, not a bottleneck for every transaction.

For the hackathon pitch, this reliability layer is important because customs compliance is high-stakes and judges should see that TradeReady includes safeguards beyond ordinary chatbot generation.

## Team Task Allocation

- Jason: Backend PRD and additional Platform Manager Agent. The Platform Manager Agent should auto-fill platform details and converse with the user about platform choices.
- CK: Frontend UI, including the Shopee page to our platform flow and our platform UI.
- Nora: Admin, deliverables and time tracking, project writeup, test cases, and demo video.
- MingXuan: Problem statement research, pitch, and Vite PPT.

## Reference Files

- `docs/multi-agent-reliability-approach.md`
- `docs/output-requirements.md`
- `docs/source-reports.md`
- `C:\Users\User\OneDrive - SIM - Singapore Institute of Management\Documents\Sea X OpenAI\TradeReady_PRD.pdf`
- `C:\Users\User\Downloads\Sea & OpenAI Hackathon.pdf`

## Prior Chat Summaries

Add short summaries of useful prior chats here. Include the date, thread topic, and decisions that should carry forward.
