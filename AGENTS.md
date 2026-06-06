# AGENTS.md

## Project Memory

For TradeReady or Sea & OpenAI Hackathon tasks, read these files before producing substantive work:

- `docs/project-context.md`
- `docs/multi-agent-reliability-approach.md`
- `docs/output-requirements.md`
- `docs/source-reports.md`

## Working Agreement

- Ask a clarification question when an important point in the prompt is vague or unclear.
- Treat the source reports and ingested markdown summaries as canonical project context.
- Do not invent details from PDFs that have not been read or summarized.

## TradeReady Reliability Principle

TradeReady's core reliability idea is multi-agent cross-checking for generated compliance output:

- RAG retrieves current customs rules from official government customs portals.
- A generator agent creates the compliance output using retrieved evidence.
- A critic or supervisor agent compares the generated output against the retrieved evidence.
- Verified information can be used to auto-fill platform or compliance forms on behalf of the user.
- Required fields that cannot be filled confidently must be flagged to the user instead of guessed.
- Mismatches, unsupported claims, and low-confidence cases are escalated to a human compliance reviewer.
- High-confidence cases continue automatically.

Frame this as a human-on-the-loop safeguard for high-stakes customs compliance, not as a generic chatbot workflow.
