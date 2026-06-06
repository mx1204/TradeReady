# Multi-Agent Reliability Approach

## Purpose

Use this file to store the workflow for using multiple agents to improve output reliability in TradeReady.

The core idea is: retrieve official customs rules with RAG, generate an answer grounded in that retrieved context, then use a separate critic agent to cross-check the generated answer against the retrieved evidence before deciding whether to auto-approve, auto-fill platform/compliance forms, flag missing fields to the user, or escalate to a human reviewer.

## Target Output

- Output type: Customs compliance guidance, HS code classification support, platform-specific seller guidance, compliance scripts, verified form filling, missing-field prompts, test cases, pitch material, and PRD details.
- Audience: Cross-border sellers, hackathon judges, developers, and human compliance reviewers.
- Reliability goal: Ground outputs in official customs sources and catch mismatches before seller-facing guidance is treated as reliable.
- Common failure modes to avoid: Hallucinated rules, outdated model-memory answers, unsupported HS code classification, misread RAG evidence, false confidence, guessing unknown form fields, and fully blocking the workflow for every edge case.

## Agent Roles

### RAG Retriever Agent

- Responsibility: Fetch current compliance rules from official government customs portals at request time.
- Inputs: Seller request, destination country, product category, platform details, and required compliance question.
- Expected output: Retrieved official source excerpts, metadata, source URLs, retrieval timestamp, and confidence notes.

### Generator Agent

- Responsibility: Produce the main output for the requested task.
- Inputs: User prompt, seller/product details, platform details, retrieved official customs context, source reports or their ingested summaries, and relevant repo files.
- Expected output: A seller-facing or reviewer-facing compliance output grounded in retrieved source context.

### Platform Manager Agent

- Responsibility: Support Jason's backend scope by identifying the relevant platform flow, mapping platform-specific required fields, and conversing with the user about platform choices.
- Inputs: PRD details, user platform requirements, marketplace/platform constraints, form schema, and project context.
- Expected output: Clarified platform requirements, required-field list, suggested auto-fill behavior, missing-field questions, and implementation notes for backend integration.

### Form Completion Agent

- Responsibility: Fill platform or compliance forms on behalf of the seller using only verified seller input, verified generated compliance output, and retrieved official evidence.
- Inputs: Verified compliance output, seller-provided data, platform field schema, required-field list, evidence references, and critic pass/warn status.
- Expected output: Completed form fields with source traceability, plus a list of unfilled or low-confidence fields that must be flagged to the user.

### Missing Field Flagging Agent

- Responsibility: Detect required fields that cannot be filled confidently and convert them into clear user questions.
- Inputs: Form Completion Agent output, platform field schema, required-field list, validation errors, and confidence notes.
- Expected output: User-facing missing-field prompts that identify exactly what information is needed and why.

### Critic Agent

- Responsibility: Compare the generator output against the RAG-retrieved official evidence and flag mismatches, unsupported claims, or low-confidence reasoning.
- Inputs: Generator output, retrieved official source excerpts, source URLs, retrieval metadata, and expected output schema.
- Expected output: Pass, warn, or escalate decision with exact mismatches and evidence references.

### Fact-Check Agent

- Responsibility: Validate factual claims in project deliverables, pitch material, and compliance explanations against provided reports and retrieved official sources.
- Inputs: Draft output, source reports, source summaries, official customs source excerpts, and user-provided facts.
- Expected output: Claim-by-claim verification notes, unsupported claims, and recommended corrections.

### Synthesis Agent

- Responsibility: Merge the generator output, critic findings, fact-check notes, and human reviewer decisions into the final response or system output.
- Inputs: Generator output, critic report, form completion results, missing-field prompts, fact-check notes, human reviewer resolution if applicable, and requested final format.
- Expected output: Final answer that keeps verified content, removes or labels uncertain content, preserves clear source traceability, and clearly separates completed fields from fields needing user input.

### Human Compliance Reviewer

- Responsibility: Resolve cases where the critic finds mismatches, missing evidence, or low confidence.
- Inputs: Escalation report, conflicting generated claim, retrieved official source evidence, product details, and platform context.
- Expected output: Final decision, correction, and optional feedback for improving retrieval or prompting.

## Workflow

1. Seller asks a compliance question or submits product/platform details.
2. Platform Manager Agent clarifies or auto-fills platform-specific details when needed.
3. RAG Retriever Agent pulls current rules from official customs portals such as `customs.gov.sg` or `beacukai.go.id`.
4. Generator Agent creates the compliance output using the retrieved official context.
5. Critic Agent compares the generated output against the retrieved evidence.
6. If the critic passes the output, Form Completion Agent fills eligible platform or compliance form fields using verified data only.
7. Missing Field Flagging Agent flags required fields that are incomplete or low confidence and asks the seller for those details.
8. If the critic detects a mismatch or low confidence in compliance logic, only that case is escalated to a human compliance reviewer.
9. Synthesis Agent returns the verified final output, completed fields, missing-field questions, or the human-reviewed correction.

## Comparison Method

- Criteria for comparing agent outputs: Evidence support, HS code consistency, country-specific rule consistency, platform-specific requirement consistency, form-field source traceability, required-field completeness, confidence level, and clarity of source traceability.
- How disagreements should be resolved: Prefer the retrieved official customs evidence over model-memory claims. Escalate unresolved contradictions to a human compliance reviewer.
- What must be verified before final output: The output must be grounded in retrieved source context, key compliance claims must map to evidence, auto-filled form fields must map to verified data, and unsupported or missing fields must be removed or flagged to the user.

## Final Decision Rules

- Prefer: Official government customs sources, source-grounded outputs, verified auto-fill, explicit uncertainty, and narrow human escalation for edge cases.
- Reject: Unsupported HS code claims, outdated training-data-only answers, vague compliance guarantees, generated outputs that contradict retrieved official evidence, and guessed values for required form fields.
- Ask the user when: Product details, destination market, source jurisdiction, platform, or intended output format is unclear.

## Pitch Framing

This is a reliability safeguard for a high-stakes domain. The system is not just a chatbot that gives compliance advice. It retrieves official rules, generates an answer, independently checks the answer against those rules, uses verified information to auto-fill forms, flags missing fields to the seller, and escalates only uncertain compliance cases to a human reviewer.

## Notes From Prior Chats

- Jason proposed multi-agent cross-checking as the core reliability layer: RAG retrieves official customs rules, a generator produces the compliance output, a critic compares the output against retrieved evidence, and low-confidence or mismatched cases go to a human compliance reviewer.
- The group wants TradeReady to use verified information to fill forms on behalf of the user. Required fields that cannot be filled confidently must be flagged to the user instead of guessed.
