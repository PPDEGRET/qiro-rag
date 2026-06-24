# Qiro RAG / Substantiation

Local-first evidence substantiation for Qiro environmental marketing claim review.

This repo owns **Step 3**:

```text
Step 1   extract claim signals
Step 1.5 group/protect claims
Step 2   assess potential regulatory issues
Step 3   check company evidence for support, limits, contradictions, and gaps
Step 4   produce a human-review report
```

Step 3 is not a verdict engine. It asks:

```text
Claim X was flagged because of critique / law issue Y.
Does the supplied evidence contain Z that makes Y less problematic,
still problematic, contradicted, or only fixable by rewriting the claim?
```

## Current status

Working local Step 3 prototype:

- evidence-pack initialization;
- ingestion for `md`, `txt`, `pdf`, `docx`, `xlsx`, `csv`, and optional OCR images/scanned PDFs;
- managed-copy or reference storage;
- local manifest auto-tagging;
- SQLite chunk/table index;
- keyword + persisted local embedding retrieval;
- issue-frame generation from Step 2 findings;
- quote-backed heuristic or opt-in OpenAI-compatible/Ollama LLM evidence assessment;
- review memory in `review_decisions.csv`;
- optional playbook patch proposals from reviewer decisions;
- connector staging for local folders and CSV manifests;
- model profiles + onboarding recommender for heuristic, local Ollama, and OpenAI-compatible judges.

```bash
uv run qiro-rag init-pack examples/evidence-pack
uv run qiro-rag pull ./company-docs --target ./staged-docs
uv run qiro-rag ingest ./staged-docs --pack ./evidence-pack --reset
uv run qiro-rag embed --pack ./evidence-pack
uv run qiro-rag assess examples/step2/finding.json --pack ./evidence-pack --out step3_evidence.json
uv run qiro-rag models
uv run qiro-rag onboard
uv run qiro-rag assess examples/step2/finding.json --pack ./evidence-pack --out step3_evidence.json --profile ollama-private-small
uv run qiro-rag learn --pack ./evidence-pack --propose playbook.patch.yaml
uv run pytest
```

## Product boundary

Qiro RAG is a **risk-review aid** for substantiation. It does not provide legal advice, determine illegality, or replace review by qualified counsel/compliance experts.

## First principles

- Local-first by default: no raw docs, embeddings, or telemetry leave the machine unless explicitly enabled.
- Messy folders are allowed: Qiro tags documents; it should not require users to pre-sort them.
- Docling is attempted when installed; lightweight local parsers cover `md`, `txt`, `pdf`, `docx`, `xlsx`, and `csv` by default; OCR is optional/local.
- Framework orchestration can be added later, but Qiro schemas and audit trails stay in this repo.
- RAG can retrieve semantically, but every cited support must include a source quote that exists in the parsed document.
- Human review decisions are memory: `review_decisions.csv` first, optional approved playbook updates later.

## Docs

- [Step 3 product brief](docs/STEP3_PRODUCT_BRIEF.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Evidence packs](docs/EVIDENCE_PACKS.md)
- [Schemas](docs/SCHEMAS.md)
- [Privacy](docs/PRIVACY.md)
- [Model profiles](docs/MODEL_PROFILES.md)
- [Future LangChain/LangGraph prompt](docs/FUTURE_LANGCHAIN_PROMPT.md)
- [Roadmap](docs/ROADMAP.md)
