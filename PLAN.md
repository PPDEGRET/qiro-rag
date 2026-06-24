# Qiro Step 3 implementation plan

The full product plan lives in [`docs/STEP3_PRODUCT_BRIEF.md`](docs/STEP3_PRODUCT_BRIEF.md).

Shortest path:

1. Define Step 2 -> Step 3 -> Step 4 schemas.
2. Build evidence-pack ingestion for `md`, `txt`, `pdf`, `docx`, `xlsx`, `csv` with Docling.
3. Store parsed chunks, tables, metadata, hashes, and citations locally.
4. Add hybrid retrieval: keyword + optional local semantic embeddings + metadata filters.
5. Keep the assessment workflow in typed Qiro functions; optional LangGraph orchestration adds real nodes/tracing without becoming the default.
6. Judge each Step 2 issue as claim X + critique/law issue Y + possible evidence Z.
7. Verify cited quotes exist in source text.
8. Emit `step3_evidence.json` for Step 4 reporting.
9. Capture human feedback in `review_decisions.csv`.
10. Add optional `learn` command that proposes, but does not apply, playbook updates.

Non-goals for v0.1:

- hosted enterprise connectors;
- autonomous self-changing compliance memory;
- legal verdicts;
- multilingual review beyond schema readiness;
- graph database;
- OCR-heavy scanned document support unless Docling makes it cheap.
