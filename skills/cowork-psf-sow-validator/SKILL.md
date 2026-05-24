---
name: cowork-psf-sow-validator
description: >
  Validates Google PSF (Partner Services Fund) funded partner Statements of
  Work against submission rules. Accepts uploaded files, Google Drive URLs, or
  pasted content. Produces a structured compliance report identifying every
  violation with the relevant excerpt, rationale, and suggested fix. Use when
  the user says "validate this SOW", "check PSF compliance", "review the
  statement of work for PSF", or "is this SOW ready to submit to Google?".
platform: cowork
connectors:
  required: []
  optional: [google-drive]
triggers:
  - "validate this SOW for PSF"
  - "check PSF compliance on this statement of work"
  - "is this SOW ready to submit to Google?"
  - "review the statement of work for PSF funding"
  - "PSF SOW check"
---

# PSF Statement of Work Validator

Validates Statements of Work (SoW) for Google Partner Services Fund (PSF)
submissions against Google's compliance requirements. Produces a detailed
report identifying every violation with excerpt, rationale, and remediation.

---

## Connector guard

Google Drive is optional — only needed if the user provides a Drive URL. No
other connectors are required; the validation logic runs entirely on document
text that Claude reads natively.

---

## Step 1 — Ingest the document

Obtain the SoW content via the first available route:

1. **Uploaded file** — if the user has attached a PDF or DOCX, read it
   directly. PDFs are readable natively; for DOCX use the `Read` tool on the
   file path provided in the conversation.
2. **Google Drive URL** — if the user provides a Drive link, use
   `GoogleDrive:read_file_content` with the file ID extracted from the URL.
3. **Pasted text** — if the user has pasted the SoW content into the
   conversation, proceed with that text.

If none of these yields content, ask the user to attach the document, share a
Drive link, or paste the relevant sections.

---

## Step 2 — Load validation rules

Read the complete validation rules from `references/psf_rules.md` to ensure
all current rules are applied before beginning the check.

---

## Step 3 — Systematic validation

Check the SoW against each rule category in this order:

1. **Document Identification** — partner name, customer name, engagement type
2. **Dates and Timeline** — effective date, project start/end, timeline structure
3. **Business Alignment** — business values, client requirements
4. **Technical Outcomes** — defined outcomes, measurable criteria, deliverable linkage
5. **Activities and Phases** — activity structure, logical flow, milestones
6. **Deliverables** — specificity, measurability, approval process, partner-built requirement
7. **Google Products** — GCP workload identification, project deployment location
8. **Roles and Responsibilities** — partner/customer roles, Google accountability exclusion, delivery location
9. **Scope Management** — assumptions/dependencies, out-of-scope sections
10. **Success Criteria** — alignment, measurability, consistency
11. **Pricing and Payment** — PSF approval language, currency, taxes, payment obligations
12. **Costs** — total price, Google funding amount, partner investment, net cost to customer
13. **Signature Block** — presence and completeness

---

## Step 4 — Generate the validation report

For each violation found, document:

| Field | Description |
|-------|-------------|
| Rule Category | The category of the violated rule |
| Excerpt | Relevant text from the SoW (or "Not found" if the section is missing) |
| Validation Result | "INCOMPLETE" for violations |
| Rationale | Clear explanation of why the rule is not met |
| Remediation | Suggested fix to achieve compliance |

---

## Step 5 — Output format

```markdown
# PSF SoW Validation Report

## Summary
- **Document**: [Document name or identifier]
- **Validation Date**: [Today's date]
- **Total Rules Checked**: [Number]
- **Violations Found**: [Number]
- **Compliance Status**: PASS / FAIL

## Violations

### 1. [Rule Category]: [Brief issue]
- **Rule**: [Full rule text]
- **Excerpt**: "[Relevant SoW text, or 'Not found']"
- **Result**: INCOMPLETE
- **Rationale**: [Why this fails the rule]
- **Remediation**: [How to fix]

[Repeat for each violation]

## Recommendations
[Priority-ordered list of fixes required before submission]
```

---

## Critical rules (most commonly missed)

**Payment and approval language**
- Must include: "Payment is contingent upon formal PSF approval by Google Cloud"
- Must NOT include language obligating the customer to pay if Google withholds payment for lack of POE

**Deliverable approval**
- Must specify a written sign-off process for each deliverable
- Approval must be explicitly contingent on written customer sign-off

**GCP deployment**
- GCP project must be deployed in the customer's tenant environment, not the partner's

**Roles and responsibilities**
- Must include defined roles for both partner AND customer
- Google must NOT be accountable for any deliverables or activities

**Pricing requirements**
- Must be in USD
- Must state that price includes all applicable taxes
- Must specify a fixed total price for professional services

---

## Validation tips

- Search for exact required phrases — many rules mandate specific language
- Check for omissions — missing sections are as important as incorrect content
- Verify consistency — success criteria must align with deliverables; deliverables must link to outcomes
- Flag ambiguity — vague language often fails measurability requirements
- Check cross-references — technical outcomes must link to deliverables; deliverables must link to phases

---

## Reference files

- `references/psf_rules.md` — complete list of all validation rules with details
