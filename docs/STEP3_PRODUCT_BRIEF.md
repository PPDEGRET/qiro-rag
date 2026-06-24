# Step 3 product brief: Qiro RAG / substantiation

## One-line purpose

Qiro Step 3 checks whether a company-provided evidence corpus contains support, limitations, contradictions, or gaps for the environmental marketing claims flagged in Step 2.

This is a substantiation review aid, not legal advice and not a definitive compliance determination.

## Core framing

Step 3 is not generic document chat. It is issue-driven evidence review:

```text
Claim X was flagged because of critique / law issue Y.
Does the supplied evidence contain Z that makes Y less problematic,
still problematic, contradicted, or only fixable by rewriting the claim?
```

Example:

```text
X: "Our delivery is carbon neutral."
Y: Potential issue: absolute climate claim with unclear boundary, method, and offset basis.
Z that may matter:
- delivery emissions boundary;
- calculation method;
- reduction versus compensation split;
- offset certificates;
- timeframe;
- consumer-facing disclosure text.
```

Important: evidence can reduce a substantiation gap without fixing the claim wording. Step 3 must be allowed to say:

```text
Evidence supports part of the factual basis, but the consumer-facing claim may still be too broad.
```

## Product boundary

### In scope

- ingest messy company document folders;
- parse `md`, `txt`, `pdf`, `docx`, `xlsx`, and `csv`;
- auto-tag likely document roles without moving files by default;
- build local indexes;
- retrieve evidence linked to Step 2 findings;
- assess support, partial support, contradiction, and gaps;
- verify citations against source quotes;
- write a Step 3 JSON artifact for Step 4 reports;
- collect reviewer decisions as auditable memory.

### Out of scope for v0.1

- legal verdicts;
- public web truth discovery;
- autonomous compliance decisions;
- silent self-improvement;
- hosted SharePoint/Drive/S3 connectors;
- full multilingual legal review;
- heavyweight knowledge graph.

## Evidence-pack UX

The user can dump a messy folder:

```bash
qiro-rag ingest ./company-docs
```

Qiro should create or update a local evidence pack:

```text
evidence-pack/
  raw/                   # optional managed copy of source files
  manifest.csv           # document inventory + auto-tags + human corrections
  review_decisions.csv   # reviewer feedback memory
  index/                 # local generated index, ignored by git
  ingestion_report.md    # parser warnings, unsupported files, review needs
```

Users should not have to pre-sort files. Qiro may tag documents as:

- product specification;
- certificate;
- supplier declaration;
- lab test;
- LCA / EPD;
- GHG inventory;
- offset documentation;
- recycling guidance;
- packaging bill of materials;
- marketing approval note;
- policy / pledge / transition plan;
- sustainability report;
- unknown.

Auto-sort means **tag**, not secretly move. A managed-copy mode may copy source files into `raw/` with hashes for auditability.

## Local-first privacy model

Default behavior:

- no cloud model calls;
- no cloud embeddings;
- no telemetry;
- no raw documents leave the machine;
- all generated indexes are local.

Optional behavior must be explicit:

```bash
qiro-rag ingest ./docs --cloud-assisted
qiro-rag assess finding.json --pack evidence-pack --out step3.json --profile hosted-flash
```

Enterprise trust depends on this boundary.

## Retrieval model

Retrieval should be hybrid:

1. **Keyword retrieval** for SKUs, percentages, standards, dates, legal terms, and exact product names.
2. **Semantic retrieval** for paraphrases and conceptual links.
3. **Metadata filters** for product, market, date, document type, supplier, and version.

Default target:

```text
hybrid = keyword + local semantic + metadata filters
```

Keyword-only mode must remain available for offline deterministic review.

## Assessment model

Step 3 should avoid rigid legal math. Playbooks are lenses, not rules.

For each Step 2 finding, the assessor creates an issue frame:

```json
{
  "claim": "Our mailer is 100% recyclable.",
  "critique": "The claim may be too broad if recyclability depends on components, market collection systems, or conditions not disclosed.",
  "ruleRefs": ["EmpCo generic environmental claims", "EmpCo substantiation requirements"],
  "whatWouldHelp": [
    "product-specific material specification",
    "recycling compatibility evidence",
    "market-specific collection/sorting evidence",
    "clear disclosure of exclusions or conditions"
  ],
  "whatWouldNotBeEnough": [
    "generic sustainability policy",
    "supplier aspiration without product-specific facts"
  ]
}
```

The model may add questions when a claim does not fit a predefined bucket.

## Evidence statuses

Use cautious statuses:

- `supported` — evidence appears to directly support the relevant issue.
- `partially_supported` — evidence supports some elements but leaves material gaps.
- `contradicted` — evidence appears inconsistent with the claim or implied impression.
- `insufficient_evidence` — no meaningful support found in the supplied corpus.
- `unclear` — retrieved material is ambiguous or needs expert review.
- `not_applicable` — Step 3 cannot evaluate this issue with evidence documents.

Every non-trivial result should include `humanReviewRecommended`.

## Quote-backed citations

Semantic RAG can find candidates, but citations must be grounded:

1. retriever finds candidate chunks/tables;
2. model judges whether they support/limit/contradict the Step 2 issue;
3. model returns exact quotes;
4. Qiro verifies each quote exists in the parsed source;
5. unverified quotes are removed or downgraded.

No exact quote means no cited support.

This is not grep-only. It is RAG with an anti-hallucination rail.

## Step 2 -> Step 3 -> Step 4 contract

### Step 2 input

Step 3 consumes Step 2 findings such as:

```json
{
  "claimId": "claim-carbon-neutral-delivery",
  "claimText": "Our delivery is carbon neutral.",
  "consumerImpression": "The service has no net climate impact.",
  "critique": "Absolute climate claim lacks clear basis, scope, and compensation disclosure.",
  "ruleRefs": ["EmpCo climate-related environmental claims"],
  "needsEvidenceCheck": true
}
```

### Step 3 output

```json
{
  "claimId": "claim-carbon-neutral-delivery",
  "status": "partially_supported",
  "summary": "The supplied offset certificate may support compensation for a defined shipment period, but no evidence was found for delivery-emissions calculation boundaries or reduction versus compensation split.",
  "supportingEvidence": [
    {
      "docId": "DOC-0042",
      "path": "raw/offset-certificate.pdf",
      "page": 2,
      "quote": "Certificate covers 120 tCO2e retired for 2025 parcel delivery operations.",
      "relevance": "May support compensation volume for the stated period."
    }
  ],
  "missingEvidence": [
    "delivery emissions boundary",
    "calculation methodology",
    "reduction versus offset split",
    "consumer disclosure basis"
  ],
  "humanReviewRecommended": true
}
```

### Step 4 use

Step 4 should show:

- the original claim;
- Step 2 issue;
- evidence status;
- supporting and contradicting quotes;
- missing evidence checklist;
- suggested safer rewrite when appropriate;
- clear reviewer action.

## Memory and improvement

Use `review_decisions.csv` as the first memory layer.

Example:

```csv
claim_id,doc_id,quote,status,human_decision,reason,created_at
C-001,DOC-042,"contains 82% post-consumer recycled PET",supports,accepted,"Product-specific supplier certificate",2026-06-23
```

Later command:

```bash
qiro-rag learn --from review_decisions.csv --propose playbook.patch.yaml
```

The learn command may propose:

- new synonyms;
- new document tags;
- better evidence questions;
- false-positive patterns;
- prompt examples;
- regression tests.

It must not silently change behavior. Human approval is required.

This borrows the useful part of self-improving agent systems: reflection from experience. It avoids hidden, unauditable compliance drift.

## Edge-case process

When the model cannot map a claim to known evidence lenses, it should create an edge-case item:

```json
{
  "claimId": "C-101",
  "edgeCaseType": "unmapped_claim_logic",
  "why": "Claim combines biodiversity, circularity, and climate positivity in one sentence.",
  "proposedEvidenceQuestions": [
    "What impact category does 'positive' refer to?",
    "Is there a baseline comparison?",
    "Is the biodiversity claim site-specific or product-level?"
  ],
  "reviewRecommended": true
}
```

Approved edge cases can later become playbook examples.

## Language plan

English-only first.

Design now for later languages by storing:

- source language;
- original quote;
- optional English normalized summary;
- market/jurisdiction metadata;
- regulation-pack language.

Multilingual expansion is technically manageable with multilingual embeddings and language-specific prompts. The hard part is legal/compliance nuance, so each language/market needs review examples.

## First implementation milestone

1. Evidence pack initializer.
2. Schemas for Step 2 finding, issue frame, evidence citation, Step 3 assessment, and review decision.
3. Docling ingestion prototype for the required file types.
4. SQLite chunk/table metadata store.
5. Keyword retrieval.
6. Optional local embedding retrieval.
7. Typed assessment flow for one Step 2 finding.
8. Quote verifier.
9. `step3_evidence.json` writer.
10. `review_decisions.csv` capture.

Keep the first demo synthetic and fictional.
