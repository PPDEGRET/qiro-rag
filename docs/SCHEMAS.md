# Schemas

The Python source of truth is `src/qiro_rag/schemas.py`.

## Step 2 finding input

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

## Issue frame

```json
{
  "claimId": "claim-carbon-neutral-delivery",
  "claimText": "Our delivery is carbon neutral.",
  "critique": "Absolute climate claim lacks clear basis, scope, and compensation disclosure.",
  "ruleRefs": ["EmpCo climate-related environmental claims"],
  "whatWouldHelp": ["delivery emissions boundary", "calculation method"],
  "whatWouldNotBeEnough": ["generic sustainability pledge"]
}
```

## Step 3 assessment output

```json
{
  "claimId": "claim-carbon-neutral-delivery",
  "status": "partially_supported",
  "summary": "Offset evidence was found, but no calculation boundary or reduction split was found.",
  "supportingEvidence": [
    {
      "docId": "DOC-0042",
      "path": "raw/offset-certificate.pdf",
      "page": 2,
      "quote": "Certificate covers 120 tCO2e retired for 2025 parcel delivery operations.",
      "relevance": "May support compensation volume for the stated period.",
      "verified": true
    }
  ],
  "contradictingEvidence": [],
  "missingEvidence": ["calculation methodology", "reduction versus offset split"],
  "humanReviewRecommended": true
}
```

## Status values

- `supported`
- `partially_supported`
- `contradicted`
- `insufficient_evidence`
- `unclear`
- `not_applicable`
