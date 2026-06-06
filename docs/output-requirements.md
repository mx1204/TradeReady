# Output Requirements

## Output Type

- Format:
- Length:
- Tone:
- Structure:

## Quality Bar

- Must be accurate about: The TradeReady project idea, hackathon requirements, source report content, team task allocation, and the multi-agent RAG cross-checking reliability design.
- Must include: Clear connection to the source reports when producing project writeups, pitch material, test cases, demo scripts, or implementation plans. For compliance reliability outputs, include the RAG retrieval, critic cross-checking, and human-on-the-loop escalation flow.
- Must avoid: Inventing project details that are not in the source reports or confirmed by the user. Do not present training-data-only compliance answers as reliable.

## Verification Checklist

- Check facts against provided sources.
- Resolve contradictions between sources.
- Keep unsupported claims out of the final answer.
- Ask a clarification question when an important requirement is vague.
- For TradeReady compliance logic, distinguish between retrieved official customs evidence, generator output, critic findings, and human reviewer decisions.
- Escalate low-confidence or contradictory compliance cases instead of forcing an automatic answer.

## Source Rules

- Required source files: `docs/project-context.md`, `docs/source-reports.md`, and any ingested summaries from the source PDFs.
- Optional source files: `docs/multi-agent-reliability-approach.md`, `docs/output-requirements.md`.
- External sources allowed: Ask first if current web research is needed. Use the provided source reports as the primary project reference. For actual compliance claims, prefer official government customs portals such as `customs.gov.sg` and `beacukai.go.id`.

## Final Answer Rules

- Preferred format:
- Citation or file-reference style:
- Examples of good output:
- Examples of bad output:
